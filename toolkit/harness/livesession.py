"""Drive one authorized live-capture session, and turn its wire bytes into an artifact.

    (ELEVATED)  python toolkit/harness/livesession.py --account capture \
                    --exe <vault>/run-live/<build>/Gw.exe --confirm

This is the R0b driver: it ties together the parts each proven on their own -- the launch
gate (`cage.assert_launch_safe`, stock->live), the account selector (`accounts.for_automation`,
refuses the primary), the key-tap (`keytap.py` reads what the code cave stashed), the
off-wire capture (`wirecapture.py`), the decryptor (`replay.py`/`gwcrypto`), the origin
stamp (`origin.py`), and the scrub (`scrub_captures.py`). It launches the stock-DH live
client at the real service, sniffs the ciphertext, reads the session key out of the client,
and assembles a decrypted capture stamped `origin: live` and byte-replayable from disk.

TWO HALVES, and only one is testable without a live account:

  * ASSEMBLE (offline, pure) -- reassembled wire streams + the tapped keys -> decrypted
    captures. The DH handshake is plaintext on the wire (ARC4 starts only after the key is
    derived), so this splits VERSION/CLIENT_SEED/SERVER_SEED off the front of each
    direction and decrypts the rest. Verified against real captured bytes in
    test_livesession.py.
  * RUN (live) -- launch, sniff, tap, hold, stop, assemble, scrub. Needs WinDivert, an
    elevated shell, and the secondary account, and it never runs except behind --confirm.

TWO WAYS A LIVE SESSION IS NOT THE LOOPBACK DRY-RUN, both of which shape the code below:

  1. **Several connections, unknown addresses.** Login is three stages (PLAN §1.6), and two
     of them are capturable: the auth channel, then the game server on a DIFFERENT
     address, both on 6112 (see LIVE_PORTS for why Stage A is not). Nobody knows those
     addresses until the client connects -- Stage C's arrives inside the encrypted
     AUTH_SMSG_GAME_SERVER_INFO -- and by then the plaintext handshake has already crossed
     the wire. So the sniff filters by PORT, on any host, and starts before the launch.
     Each connection is reassembled on its own sequence space
     (wirecapture.load_connections); merging them would interleave two sequence spaces into
     a byte string that looks like a stream and decrypts to nothing.
  2. **Several keys.** Each DH-keyed channel derives its own master_secret through the same
     code, so the single tap slot is OVERWRITTEN at every handshake. The driver keeps a
     keyring -- every distinct value the slot ever held -- and assemble_live pairs keys to
     connections by a criterion the artifact can refute (FIRST_C2S_OPCODE).

AND THE DRIVER DOES NOT PLAY THE GAME. No scripted keystrokes, no clicks. See run().

BEHAVIOURAL GUARDS, the controls PLAN §6.1 says actually protect an account: exactly one
live client (a second is refused), a session-length ceiling, and an explicit --confirm --
because what closes accounts is a traffic pattern no person produces, and the cheap
structural parts of "human cadence, one client" are worth enforcing even though the
judgement itself stays with the operator.

standard library only (the WinDivert dependency lives in wirecapture.py).
"""
import argparse
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientpatch"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
import accounts  # noqa: E402
import origin  # noqa: E402
import vaultpath  # noqa: E402
import wirecapture as wc  # noqa: E402
from gwcrypto import ARC4  # noqa: E402

# Handshake framing, plaintext on the wire, from authsrv.py's own reader:
#   c2s: VERSION (u32 header 0x000C0400 + 12-byte body) then CLIENT_SEED (u16 0x4200 + 64B A)
#   s2c: SERVER_SEED (u16 0x1601 + 20B)
AUTH_VERSION_HEADER = 0x000C0400
CLIENT_SEED_HEADER = 0x4200
SERVER_SEED_HEADER = 0x1601
VERSION_LEN = 4 + 12
CLIENT_SEED_LEN = 2 + 64
SERVER_SEED_LEN = 2 + 20

# The ports a LIVE login puts capturable bytes on. 6112 twice over: Stage B (auth) and
# Stage C (game), on two different ArenaNet addresses, which is why the sniff is per-port
# and per-connection rather than per-host.
#
# 6601 is deliberately NOT here, and the reason is a trap worth naming. Our own portal
# listens on 6601 and every capture in the vault says "portal = 6601" -- but that is a
# consequence of `-portal` being SET: OBSERVED (studies/handshake/PLAN.md 0.1, 192-195)
# the flag makes the client switch to port 6601, prefix paths with /Spawned/WebGate, and
# set its TLS flag to zero. A live run passes no `-portal`, so Stage A is HTTPS with
# certificate validation to account.arena.net -- port 443, encrypted under a key we do not
# hold and are not trying to get. Sniffing 6601 live would record nothing while looking
# like coverage; sniffing 443 would record the machine's entire web traffic and still
# decrypt to nothing. Stage A is out of scope for R0b, and saying so beats a filter that
# implies otherwise.
LIVE_PORTS = (6112,)

# OBSERVED, measured 2026-08-07 over the vault's 401 captures that carry both a channel
# marker and a first c2s frame: the first CLIENT->server message after the handshake is
# opcode 0x8001 on the auth channel (271 of 276; the other 5 are the 2026-08-04 synthetic
# RURIK-HANDSHAKE markers) and 0x808a on the game channel (42 of 42).
#
# Why this is usable as a LIVE acceptance test and not just a loopback artefact: that
# message is emitted by the CLIENT, and the client is the same binary in both places. Our
# server never influences it. So "the decrypted stream starts with the opcode the client
# always sends" is a property a WRONG key cannot produce -- ARC4 with the wrong key gives
# 65535/65536 odds against those two bytes -- which makes it a check that can fail, per
# CLAUDE.md. It is not proof of the whole stream, and assemble_live says so in its report.
FIRST_C2S_OPCODE = {"auth": 0x8001, "game": 0x808a}


class LiveError(SystemExit):
    """A live run was refused. The whole point is that it stops before the account is used."""


class SplitError(Exception):
    """A captured stream did not begin with the handshake we require. Never guessed past."""


# ------------------------------------------------------- the offline assembly --
def split_c2s(stream):
    """(A, ciphertext) from a client->server stream that starts with the handshake.

    Parses rather than trusts a fixed offset, so a stream that is not the handshake is a
    loud SplitError instead of 82 bytes of something else fed to the decryptor.
    """
    if len(stream) < VERSION_LEN + CLIENT_SEED_LEN:
        raise SplitError(f"c2s stream is {len(stream)} bytes, too short for the handshake")
    header = int.from_bytes(stream[0:4], "little")
    if header != AUTH_VERSION_HEADER:
        raise SplitError(f"c2s does not start with VERSION (got header 0x{header:08x})")
    seed_hdr = int.from_bytes(stream[VERSION_LEN:VERSION_LEN + 2], "little")
    if seed_hdr != CLIENT_SEED_HEADER:
        raise SplitError(f"CLIENT_SEED header is 0x{seed_hdr:04x}, expected 0x4200")
    a_off = VERSION_LEN + 2
    A = stream[a_off:a_off + 64]
    return A, stream[VERSION_LEN + CLIENT_SEED_LEN:]


def split_s2c(stream):
    """(server_seed, ciphertext) from a server->client stream starting with SERVER_SEED."""
    if len(stream) < SERVER_SEED_LEN:
        raise SplitError(f"s2c stream is {len(stream)} bytes, too short for SERVER_SEED")
    header = int.from_bytes(stream[0:2], "little")
    if header != SERVER_SEED_HEADER:
        raise SplitError(f"s2c does not start with SERVER_SEED (got 0x{header:04x})")
    seed = stream[2:2 + 20]
    return seed, stream[SERVER_SEED_LEN:]


def decrypt_stream(cipher, key):
    """Plaintext for one direction: ARC4(key) run continuously over the ciphertext."""
    return ARC4(key).crypt(cipher)


def assemble(wire_path, key, out_path):
    """Turn a wire capture + the tapped key into a decrypted, replayable, LIVE capture.

    Returns a dict of what it produced. Raises SplitError if either direction does not
    carry the handshake it must. The output mirrors the server's own capture shape so
    replay.py and the scrub both already understand it, and it records A / server_seed /
    arc4_key under the field names scrub_captures.py already treats as secret.
    """
    import json
    meta, streams, gaps = wc.load_wire(wire_path)
    A, c2s_cipher = split_c2s(streams[wc.C2S])
    seed, s2c_cipher = split_s2c(streams[wc.S2C])
    c2s_plain = decrypt_stream(c2s_cipher, key)
    s2c_plain = decrypt_stream(s2c_cipher, key)

    # There is deliberately NO "re-encrypt and compare" self-check here: ARC4 is symmetric,
    # so decrypt(decrypt(cipher)) == cipher for EVERY key, right or wrong -- it would be a
    # check that cannot fail. Validating the key needs an independent oracle: on loopback,
    # our server's own logged plaintext (dryrun_keycapture.py); on a live capture there is
    # none, so the key's correctness rests on the keytap having been proven on loopback and
    # on the decrypted stream framing cleanly downstream, not on anything provable here.

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(origin.record("toolkit/harness/livesession.py", origin.LIVE,
                                          note="decrypted from an off-wire capture")) + "\n")
        fh.write(json.dumps({"kind": "session_key", "arc4_key": key.hex()}) + "\n")
        fh.write(json.dumps({"kind": "client_seed", "a": A.hex()}) + "\n")
        fh.write(json.dumps({"kind": "server_seed", "sent": seed.hex()}) + "\n")
        fh.write(json.dumps({"kind": "frame", "direction": "c2s",
                             "plain": c2s_plain.hex()}) + "\n")
        fh.write(json.dumps({"kind": "frame", "direction": "s2c",
                             "plain": s2c_plain.hex()}) + "\n")
    return {"out": out_path, "c2s_bytes": len(c2s_plain), "s2c_bytes": len(s2c_plain),
            "gaps": {k: gaps[k] for k in gaps if gaps[k]},
            "A": A.hex(), "server_seed": seed.hex()}


def channel_of(plain):
    """Which channel a decrypted c2s stream looks like, or None if no key fits.

    The whole verdict is two bytes -- see FIRST_C2S_OPCODE for why those two bytes are
    load-bearing and why a wrong key does not produce them.
    """
    if len(plain) < 2:
        return None
    op = int.from_bytes(plain[:2], "little")
    for channel, want in FIRST_C2S_OPCODE.items():
        if op == want:
            return channel
    return None


def assemble_live(wire_path, keyring, out_dir):
    """Turn ONE live wire capture (several connections) + a keyring into decrypted files.

    A real session is not the dry-run's single loopback socket. The client opens the portal
    (Stage A), then the auth channel, then the game server on a different address (PLAN
    §1.6) -- and each DH-keyed channel derives its OWN master_secret, so the single tap slot
    holds a DIFFERENT value at different moments. That is why run() records a keyring (every
    distinct value the slot took, in order) rather than one key: a run that reaches the world
    has already overwritten the auth channel's secret by the time it stops.

    Pairing keys to connections is therefore a search, not a lookup, and it is settled by a
    criterion the artifact can refute: try every key against every connection and accept the
    pair only when the decrypted c2s stream starts with the opcode the client always sends.
    A connection nothing decrypts is reported as undecrypted and its raw bytes are KEPT --
    never dropped, and never written out under a key that did not fit.

    Returns a report dict. Writes one file per decrypted connection into out_dir.
    """
    import json
    meta, conns = wc.load_connections(wire_path)
    keys = [(label, k) for label, k in keyring if k]
    results = []
    for key_name, entry in sorted(conns.items(), key=lambda kv: str(kv[0])):
        row = {"connection": key_name,
               "c2s_wire_bytes": len(entry[wc.C2S]), "s2c_wire_bytes": len(entry[wc.S2C]),
               "gaps": {d: entry["gaps"][d] for d in entry["gaps"] if entry["gaps"][d]}}
        try:
            A, c2s_cipher = split_c2s(entry[wc.C2S])
            seed, s2c_cipher = split_s2c(entry[wc.S2C])
        except SplitError as exc:
            # Expected for the portal connection: Stage A is not a DH-keyed channel at all.
            row.update({"decrypted": False, "why": f"no GW handshake on this connection: {exc}"})
            results.append(row)
            continue
        row["A"] = A.hex()
        row["server_seed"] = seed.hex()

        fits = []
        for label, key in keys:
            channel = channel_of(decrypt_stream(c2s_cipher, key))
            if channel:
                fits.append((label, key, channel))
        if not fits:
            row.update({"decrypted": False,
                        "why": f"none of the {len(keys)} tapped key(s) decrypt this "
                               f"connection to a known first opcode"})
            results.append(row)
            continue
        if len({f[0] for f in fits}) > 1:
            # Two different keys both producing a valid first opcode is a 1-in-4 billion
            # coincidence, so it means something is wrong with the keyring, not that either
            # is right. Refuse rather than pick.
            row.update({"decrypted": False,
                        "why": f"{len(fits)} different keys all fit; refusing to choose"})
            results.append(row)
            continue
        label, key, channel = fits[0]
        safe = str(key_name).replace(":", "_").replace("->", "-to-")
        out_path = os.path.join(out_dir, f"{channel}-{safe}.jsonl")
        c2s_plain = decrypt_stream(c2s_cipher, key)
        s2c_plain = decrypt_stream(s2c_cipher, key)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(origin.record("toolkit/harness/livesession.py", origin.LIVE,
                                              note="decrypted from an off-wire live capture")) + "\n")
            fh.write(json.dumps({"kind": "version", "channel": channel,
                                 "connection": key_name, "key_from": label}) + "\n")
            fh.write(json.dumps({"kind": "session_key", "arc4_key": key.hex()}) + "\n")
            fh.write(json.dumps({"kind": "client_seed", "a": A.hex()}) + "\n")
            fh.write(json.dumps({"kind": "server_seed", "sent": seed.hex()}) + "\n")
            fh.write(json.dumps({"kind": "frame", "direction": "c2s",
                                 "plain": c2s_plain.hex()}) + "\n")
            fh.write(json.dumps({"kind": "frame", "direction": "s2c",
                                 "plain": s2c_plain.hex()}) + "\n")
        row.update({"decrypted": True, "channel": channel, "key_from": label,
                    "out": out_path, "c2s_bytes": len(c2s_plain), "s2c_bytes": len(s2c_plain)})
        results.append(row)
    return {"wire": wire_path, "meta": meta, "connections": results,
            "decrypted": sum(1 for r in results if r.get("decrypted")),
            "total": len(results)}


# --------------------------------------------------------------- the guards ----
def one_live_client():
    """Refuse if any Gw.exe is already running: a live run must be ONE client (PLAN §6.1).

    Returns the count for a caller that wants to log it. On a non-Windows box or if the
    query fails, returns None -- and run() treats None as 'cannot confirm', which is a
    refusal, not permission.
    """
    if sys.platform != "win32":
        return None
    import subprocess
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"Name='Gw.exe'\" | Measure-Object).Count"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    try:
        return int(out.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def preflight(account_label, exe, live_host, want_windivert=True):
    """Everything that must be true before a client is launched at the real service.

    Returns a plan dict on success; raises LiveError naming the first failure. This runs
    the real gates -- it is not a rehearsal -- so a test drives it with a loopback exe and
    expects the stock->live check to refuse, which is the correct answer for our build.
    """
    import cage
    acct = accounts.for_automation(account_label)   # refuses the primary / unflagged

    # The launch gate, from the bytes: a live run needs a STOCK-DH client aimed at the real
    # service, and it must NOT be caged. assert_launch_safe raises on any other cell.
    kind = cage.assert_launch_safe(exe, live_host)
    if kind.get("dh") != "stock":
        raise LiveError(f"the launch client is {kind.get('dh')}, not stock -- a live run "
                        f"needs the unpatched-DH build under vault/run-live")
    if not kind.get("patches", {}).get("key_tapped"):
        raise LiveError("the live build is not key-tapped: without the cave there is no key "
                        "to read, and the ciphertext cannot be decrypted. Rebuild with "
                        "make_custom_client.py --no-dh-patch --key-tap")

    running = one_live_client()
    if running is None:
        raise LiveError("could not confirm how many clients are running; refusing rather "
                        "than risk a second live client")
    if running != 0:
        raise LiveError(f"{running} Gw.exe already running -- a live run is ONE client. "
                        f"Close them first (PLAN §6.1: one client, human cadence).")

    if want_windivert:
        wc._load_windivert()      # raises WinDivertError (a LiveError) if absent/unelevated

    return {"account": acct["label"], "exe": exe, "host": live_host, "dh": kind["dh"]}


def slot_rva(exe):
    """Where the key-tap cave stashes master_secret in this binary. Raises if untapped."""
    import keytap_patch          # toolkit/clientpatch, already on sys.path above
    from gwpe import PE          # toolkit/gwpe.py
    pe = PE(exe)
    try:
        rva, _ = keytap_patch.locate_slot(pe.data, pe)
    except keytap_patch.KeyTapError as exc:
        # preflight already refuses an untapped build, so reaching here means the binary
        # changed under us. Re-raise as a LiveError rather than a bare traceback.
        raise LiveError(f"cannot locate the key-tap slot in {exe}: {exc}\n"
                        f"  Rebuild: make_custom_client.py --no-dh-patch --key-tap, then "
                        f"make_run_dir.py --live") from exc
    return rva


class KeyRing(threading.Thread):
    """Poll the tap slot and keep EVERY distinct value it holds, in order, with timestamps.

    Not "read the key once". Each DH-keyed channel derives its own master_secret through the
    same code, so the one slot is overwritten at every handshake: a session that reaches the
    world has replaced the auth channel's secret with the game channel's before it ends.
    Reading once yields whichever handshake happened last and silently loses the other, and
    an off-wire capture of a channel whose key we threw away is unrecoverable -- there is no
    second chance at a live session.

    Read-only throughout (keytap holds PROCESS_VM_READ and nothing else), and a failed read
    is a retry, never a crash: the slot is legitimately all-zero until the first handshake.
    """

    def __init__(self, pid, rva, module="Gw.exe", interval=0.25):
        super().__init__(daemon=True)
        self.pid, self.rva, self.module, self.interval = pid, rva, module, interval
        self.values = []          # [(t, master_secret_bytes)] -- distinct, in order
        self.errors = 0
        self._seen = set()
        self._stop = threading.Event()
        self.t0 = time.monotonic()

    def run(self):
        import keytap
        # Resolve the base and open the handle ONCE. keytap.read_rva re-snapshots the
        # toolhelp module list and re-opens the process on every call, which is right for
        # a one-shot read and wrong four times a second for twenty minutes -- that is
        # ~4800 OpenProcess calls against the one client we are trying not to perturb.
        # ASLR rebases per LAUNCH, not during a process's life, so caching inside a thread
        # that is bound to one pid keeps the property keytap's docstring is protecting.
        handle = base = None
        while not self._stop.is_set():
            got = None
            try:
                if handle is None:
                    base = keytap.module_base(self.pid, self.module)
                    handle = keytap.open_read(self.pid)
                got = keytap.read_handle(handle, base + self.rva, 20)
            except keytap.TapError:
                # The process is gone, or the module is not mapped yet. Both are
                # transient-or-terminal and the caller decides which by watching the
                # client, not by us guessing. Drop the handle so the next tick re-resolves.
                self.errors += 1
                handle = base = None
            if got and any(got) and got not in self._seen:
                self._seen.add(got)
                self.values.append((round(time.monotonic() - self.t0, 2), got))
            self._stop.wait(self.interval)
        if handle is not None:
            keytap.kernel32.CloseHandle(handle)

    def stop(self):
        self._stop.set()

    def keyring(self):
        """[(label, arc4_key)] -- the ARC4 keys, derived from each tapped master_secret.

        The cave taps master_secret BEFORE the key schedule, so the ARC4 key is
        arc4_hash(master_secret). Proven on loopback by dryrun_keycapture.py, which required
        the tapped value to equal the master_secret our own server independently derived.
        """
        from gwcrypto import arc4_hash
        return [(f"tap@{t}s", arc4_hash(v)) for t, v in self.values]


def run(account_label, exe, live_host, live_ports, minutes, confirm, out_root=None):
    """The live orchestration: launch, sniff, tap, hold, stop, assemble, scrub.

    Refuses without --confirm; needs WinDivert, an elevated shell and the secondary account.

    THIS DRIVER DOES NOT PLAY THE GAME. It launches the client with the account's
    credentials pre-filled and then gets out of the way -- no scripted keystrokes, no
    clicks, no timed actions. That is not an omission. PLAN §6.1 is explicit that what
    closes an account is a traffic pattern no person could produce, and the loopback
    harness's three-Enters-and-a-Play-click is exactly such a pattern. The operator logs in
    and plays; the driver only instruments. The session ceiling is the one thing it does
    enforce, because an unattended client that outlives the operator is the same hazard.
    """
    if not confirm:
        raise LiveError("a live run points a client at ArenaNet's real service. Re-run with "
                        "--confirm once you have read PLAN §6.2 and are at the keyboard: "
                        "human cadence, human hours, one client, never competitive.")
    preflight(account_label, exe, live_host)
    acct = accounts.for_automation(account_label)
    rva = slot_rva(exe)                      # raises if the live build is not key-tapped

    import subprocess
    import drive_client                     # imported here: it opens user32 at import time
    import cage

    stamp = time.strftime("%Y%m%dT%H%M%S")
    root = out_root or vaultpath.vault_path("captures", "live")
    outdir = os.path.join(root, stamp)
    os.makedirs(outdir, exist_ok=True)
    wire = os.path.join(outdir, "wire.jsonl")

    ports = sorted(set(live_ports))
    print(f"live capture {stamp}")
    print(f"  account : {accounts.describe(acct)}")
    print(f"  client  : {exe}")
    print(f"  tap slot: Gw.exe+0x{rva:x}")
    print(f"  sniffing: ports {','.join(map(str, ports))} on any host")
    print(f"  ceiling : {minutes} min")
    print(f"  output  : {outdir}")

    procs, ring, client = [], None, None
    args = []                       # bound in the try; the manifest below reads it either way
    log_path = os.path.join(os.path.dirname(exe), "Gw.log")
    cap_log = open(os.path.join(outdir, "wirecapture.log"), "w")
    try:
        # --- 1. the sniff starts FIRST, always. The DH handshake is the first thing on the
        # wire and it is the plaintext half; a capture started after the connect has already
        # lost A and the server seed, and no key can recover them. Same rule as
        # drive_client's sampler: an instrument that was not yet running produces absence of
        # evidence, never evidence of absence.
        #
        # And it filters by PORT ONLY -- there is deliberately no way to pin it to an
        # address. Pinning looks like a harmless refinement and silently costs the run its
        # point: Stage A's portal is on a different host, and Stage C's game-server address
        # arrives INSIDE the ARC4-encrypted AUTH_SMSG_GAME_SERVER_INFO, so it cannot be
        # known when the filter is opened and can never be added later. A pinned run
        # captures the auth channel, reports "1/1 connection(s) decrypted", exits 0, and
        # spends the one authorized live session on the one channel our loopback stack
        # already reproduces.
        cmd = [sys.executable, os.path.join(HERE, "wirecapture.py"),
               "--ports", ",".join(map(str, ports)),
               "--seconds", str(minutes * 60 + 120), "--out", wire]
        cap = subprocess.Popen(cmd, stdout=cap_log, stderr=subprocess.STDOUT, text=True)
        procs.append(cap)
        if not _wait_for_sniff(cap, wire):
            raise LiveError("the off-wire capture never opened -- see "
                            f"{os.path.join(outdir, 'wirecapture.log')} (elevated?). "
                            "Nothing was launched.")
        print("  [ok] the off-wire capture is live and sniffing")

        # --- 2. launch, with NO -portal and NO -authsrv: the client uses its own compiled-in
        # ArenaNet endpoints, which is the entire point of the run. drive_client.assert_safe
        # resolves that absence to the live target (an absent flag is not a neutral one) and
        # cage.assert_launch_safe then decides from the BYTES whether this binary may be
        # aimed there -- stock DH, uncaged. An ours-DH build never gets past that line.
        args = ["-windowed", "-log"] + accounts.login_args(acct)
        host = drive_client.assert_safe(exe, args)
        kind = cage.assert_launch_safe(exe, host)
        print(f"  [ok] cage: {kind['dh']} build, cleared for {host}")
        if os.path.exists(log_path):
            os.remove(log_path)
        client = subprocess.Popen([exe] + args, cwd=os.path.dirname(exe))
        procs.append(client)
        print(f"  [ok] launched pid {client.pid}: "
              f"{os.path.basename(exe)} {' '.join(accounts.redact(args))}")

        # --- 3. the keyring polls from now until the client stops.
        ring = KeyRing(client.pid, rva)
        ring.start()

        print("\n  YOU drive from here: log in and play at human cadence. Ctrl-C to stop "
              "early.\n")
        _hold(client, ring, wire, minutes)
    except KeyboardInterrupt:
        print("\n  stopping on Ctrl-C")
    finally:
        if ring:
            ring.stop()
        if client and client.poll() is None:
            drive_client.close_client(client)     # WM_CLOSE, so Gw.log flushes
        for p in procs:
            if p.poll() is None:
                try:
                    p.terminate()
                    p.wait(timeout=15)
                except (OSError, subprocess.SubprocessError):
                    pass
        cap_log.close()
        time.sleep(1)

    # --- 4. offline: assemble what the wire and the keyring hold, then scrub.
    keys = ring.keyring() if ring else []
    print(f"\n  keyring: {len(keys)} distinct session key(s) tapped")
    if not keys:
        print("  NOTE: no key was ever tapped. The wire capture is kept -- it is still the "
              "only recording of a real session -- but nothing can decrypt it.")
    report = assemble_live(wire, keys, outdir)
    for row in report["connections"]:
        if row.get("decrypted"):
            print(f"  [ok] {row['connection']}  {row['channel']}  "
                  f"c2s {row['c2s_bytes']}B / s2c {row['s2c_bytes']}B  ({row['key_from']})")
        else:
            print(f"  [--] {row['connection']}  {row.get('why', 'undecrypted')}")
        if row.get("gaps"):
            print(f"       GAPS in the wire capture: {row['gaps']} -- the keystream "
                  f"desyncs at each one")

    # A SIBLING of outdir, never a child: scrub_tree walks its source, and an output
    # directory inside that source is a directory the walk can descend into and re-scrub.
    scrubbed = outdir + "-scrubbed"
    import scrub_captures
    files, records, stats, distinct, _un = scrub_captures.scrub_tree(outdir, scrubbed)
    print(f"  scrub: {files} file(s), {records} records, {distinct} distinct secrets "
          f"replaced -> {scrubbed}")
    if stats.get(scrub_captures.OPAQUE_STAT):
        print(f"  scrub: {stats[scrub_captures.OPAQUE_STAT]} `plain` frame payload(s) "
              f"could NOT be cleaned and were copied through.")
        print("         The auth channel's first client message carries the account email "
              "as UTF-16")
        print("         inside that blob. This capture is vault-only -- not shareable, "
              "scrubbed or not.")

    import json
    manifest = {"stamp": stamp, "exe": exe, "account": acct["label"],
                "args": accounts.redact_for_file(args), "ports": ports,
                "keys_tapped": len(keys), "report": report,
                "gw_log": open(log_path, encoding="utf-8", errors="replace").read().splitlines()
                          if os.path.exists(log_path) else []}
    with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    print(f"\n  {report['decrypted']}/{report['total']} connection(s) decrypted -> {outdir}")
    return 0 if report["decrypted"] else 1


def _wait_for_sniff(cap, wire, timeout=25):
    """Wait for a real readiness signal, never a fixed sleep.

    open_capture writes the wire_meta line only AFTER WinDivertOpen succeeds, so its
    presence proves the sniff is live before the client is allowed to connect. A dead
    subprocess is caught too, which is the elevated-shell case.
    """
    end = time.time() + timeout
    while time.time() < end:
        if cap.poll() is not None:
            return False
        try:
            if os.path.exists(wire) and '"wire_meta"' in open(
                    wire, encoding="utf-8", errors="replace").read():
                return True
        except OSError:
            pass
        time.sleep(0.3)
    return False


def _hold(client, ring, wire, minutes):
    """Hold the session until the ceiling, the client exiting, or Ctrl-C."""
    ceiling = time.monotonic() + minutes * 60
    while time.monotonic() < ceiling:
        if client.poll() is not None:
            print("\n  the client exited")
            return
        left = int(ceiling - time.monotonic())
        size = os.path.getsize(wire) if os.path.exists(wire) else 0
        print(f"\r  t-{left // 60:02d}:{left % 60:02d}  keys tapped: {len(ring.values)}  "
              f"wire: {size / 1024:.0f} KiB   ", end="", flush=True)
        time.sleep(5)
    print("\n  session ceiling reached -- closing the client")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--account", required=True, help="automation-flagged label in accounts.json")
    ap.add_argument("--exe", default=None, help="the stock-DH, key-tapped live build")
    # --host is accepted only to REFUSE it by name. RUNBOOK documented `--host <auth ip>`
    # as the live command for a day, and an operator working from a printed or remembered
    # copy of that line would otherwise get an argparse error that reads like a typo. What
    # it actually asked for is the one setting that quietly ruins the run -- see the
    # comment on the wirecapture launch in run().
    ap.add_argument("--host", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--ports", default=",".join(map(str, LIVE_PORTS)))
    ap.add_argument("--minutes", type=int, default=20, help="session-length ceiling")
    ap.add_argument("--confirm", action="store_true", help="required for a real live run")
    a = ap.parse_args()
    if not a.exe:
        raise LiveError("a live run needs --exe: the key-tapped, stock-DH build under "
                        "vault/run-live. Nothing here picks a client for you -- on "
                        "2026-08-06 two tools picked the wrong one by filename order.")
    if a.host:
        raise LiveError(
            f"--host {a.host} is refused, and this is not a naming quibble.\n"
            f"  It used to pin the sniff to one address. A live login is THREE stages on\n"
            f"  three endpoints: the portal (Stage A) is a different host, and the game\n"
            f"  server's address (Stage C) arrives inside the ARC4-encrypted\n"
            f"  AUTH_SMSG_GAME_SERVER_INFO -- so it is not knowable when the filter opens\n"
            f"  and cannot be added afterwards. A pinned run records the auth channel,\n"
            f"  prints '1/1 connection(s) decrypted', exits 0, and spends the one\n"
            f"  authorized live session on the only channel loopback already reproduces.\n"
            f"  Drop the flag: the sniff filters by port on any host, which is what the\n"
            f"  multi-connection reader exists for.")
    ports = {int(p) for p in a.ports.split(",") if p.strip()}
    return run(a.account, a.exe, drive_client_default(), ports, a.minutes, a.confirm)


def drive_client_default():
    """The symbolic 'wherever the client's own build points' target: ArenaNet.

    A live run passes no -portal and no -authsrv, so there is no address to name. This is
    the string the launch gate reasons about, and it is deliberately not loopback-shaped.
    """
    sys.path.insert(0, HERE)
    import drive_client
    return drive_client.ARENANET_DEFAULT


if __name__ == "__main__":
    sys.exit(main())
