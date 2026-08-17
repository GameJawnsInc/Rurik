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

THE PRE-REGISTRATION SEAL, and WHY IT IS TAKEN WHERE IT IS. `--plan` names the
operator-mark plan that `toolkit/harness/marks.py` will read in a SECOND SHELL (F9
advance / F10 repeat / F11 note). The plan IS the pre-registered prediction, so its
sha256 belongs in `manifest.json` -- studies/reconstruction/FINDINGS.md §10.5.1 -- and
the ONE thing that makes that hash worth anything is WHEN it was taken. `manifest.json`
is written at the END of the run, after assembly; hashing there would seal whatever the
plan said AFTERWARDS, so an operator who edited it mid-session would get a manifest
certifying the edited prediction and the seal would be worse than nothing (it would look
like evidence). So `seal_plan` runs at the TOP of `run()` -- before `preflight`, before
the account is resolved, before the sniffer subprocess, and long before
`subprocess.Popen([exe] + args)` -- and the manifest is written from that CARRIED value.
`test_livesession.py` asks the syntax tree about that ordering, because "the hash is
before the launch" and "the hash is after it" are invisible to a grep and the ordering is
the whole feature.

`--plan` IS OPTIONAL, AND THAT IS A JUDGEMENT, not an oversight. `--mode` is refused when
absent because a wrong or missing mode POISONS the data unrecoverably -- every health
number in the capture becomes base-or-base*0.8 forever. A missing plan poisons nothing:
it produces an UNLABELLED capture, which is exactly what every live capture before
2026-08-13 is, and those are the corpus. Refusing would convert "the operator forgot to
pre-register" into "the one authorized live session did not happen", which is the more
expensive error. So this follows D9(a)'s shape instead: make the drop VISIBLE rather than
refused -- a loud console block before the operator logs in, and `"plan_sealed": false`
written into the manifest EXPLICITLY. An omitted key and a false one read the same only
if nothing distinguishes them, and here they are different facts: a manifest with no
`plan_sealed` key at all predates this flag, while `plan_sealed: false` is an operator who
had it and did not use it.

THE SECOND WITNESS IS FREE, AND IT IS NOW SPENT ON THE LIVE PATH. `marks.py` writes its
OWN `plan_sha256` into `marks_meta`, from its own read of the file, in a different process
at a later moment. Two independent seals of one file is a claim the artifact can refute --
if they disagree, the plan changed between the driver's read and the marker's, or the
operator typed a different file into the second shell. `marks.bind()` cannot see either:
it compares `marks_meta` against the plan file AS IT IS NOW, so an edit made before the
marker started is invisible to both of its reads. `compare_plan_seals()` below is the
missing leg, three-valued for the same reason `origin.py` is -- "no marker was run" is not
"the seals agree".

This module argued for a whole day that `run()` could not make that comparison, on the
grounds that `plan_marks.jsonl` might not exist when the manifest is written and a check
that skips in every real run cannot fail. Two rounds of adversarial review took that apart
on 2026-08-13 and they were right twice over. It is not a check, it is a RECORDED
THREE-VALUED FIELD, and `UNCHECKED` is a value rather than a skip. And the timing does not
bite: the driver prints `--pid <client.pid>`, `marks.run` ends on that pid, and the
manifest is written after teardown, pruning, assembly and the scrub. Meanwhile the verdict
was reachable only from `--assemble`, where it was PRINTED and reached no artifact -- so an
operator could seal `plan_A.txt`, mark against `plan_B.txt`, and get a manifest reading
`plan_sealed: true, plan_A.txt` with nothing anywhere contradicting it. `run()` records the
verdict now and `reassemble()` recomputes and rewrites it.

AND THE DRIVER IS CHECKED AGAINST ITSELF. `manifest.json` and `plan_seal.json` are
rendered from ONE `PlanSeal`, so they cannot legitimately disagree; `internal_seal_conflict`
says so out loud. That exists because the sabotage that beat the first round of checks --
a manifest re-hashing the plan at the end via this module's own `sha256()` helper -- left
its own evidence in the capture directory, in two files, with nothing reading the second.

WHAT IS STILL MISSING, so the next session does not have to rediscover it: `marks.py` is
handed the capture directory that already holds `plan_seal.json` and never opens it. A
refusal THERE -- the marker declining to start against a capture whose sealed sha does not
match the plan it was given -- costs the operator one retype before they log in, where
everything here can only report the mismatch afterwards. That is a change to `marks.py`
and is not in this file's remit.

BEHAVIOURAL GUARDS, the controls PLAN §6.1 says actually protect an account: exactly one
live client (a second is refused), a session-length ceiling, and an explicit --confirm --
because what closes accounts is a traffic pattern no person produces, and the cheap
structural parts of "human cadence, one client" are worth enforcing even though the
judgement itself stays with the operator.

standard library only (the WinDivert dependency lives in wirecapture.py).
"""
import argparse
import collections
import hashlib
import json
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
import marks  # noqa: E402
import origin  # noqa: E402
import vaultpath  # noqa: E402
import wirecapture as wc  # noqa: E402
from gwcrypto import ARC4  # noqa: E402

# Handshake framing, plaintext on the wire, from authsrv.py's own reader:
#   c2s: VERSION (u32 header + body) then CLIENT_SEED (u16 0x4200 + 64B A)
#   s2c: SERVER_SEED (u16 0x1601 + 20B)
#
# THE VERSION MESSAGE HAS TWO SHAPES, and we only knew one until a live session showed the
# other. OBSERVED 2026-08-07 from the first live capture (7 connections to ArenaNet, build
# 38797 on the wire in every one):
#
#   auth  header 0x000C0400, 12-byte body: <u32 build> <u32 1> <u32 4>
#   game  header 0x000C0500, 60-byte body: <u32 build> <u32 1> <u32 id> <u32 n> <u32 n>
#                                          <16B account uuid> <16B character uuid> <8B 0>
#
# so CLIENT_SEED sits at offset 16 on auth and offset 64 on game. MEASURED: `00 42` occurs
# exactly once in the first 200 bytes of every one of the seven streams, at 16 for the auth
# connection and at 64 for all six game connections -- there is no ambiguity to resolve.
# The two 16-byte fields read as uuids because they are CONSTANT across connections in the
# way uuids would be: the first is identical in all six, and the second is identical in five
# and ZERO in the earliest one -- which is the connection made before the new character
# existed. That reading is RECONSTRUCTION; the offsets are OBSERVED and are all this code
# depends on.
#
# Our own server only ever speaks the auth shape, so no loopback capture could have shown
# this. The first live run decrypted 1 of 7 connections because of it.
AUTH_VERSION_HEADER = 0x000C0400
GAME_VERSION_HEADER = 0x000C0500
VERSION_BODY_LEN = {AUTH_VERSION_HEADER: 12, GAME_VERSION_HEADER: 60}
CLIENT_SEED_HEADER = 0x4200
SERVER_SEED_HEADER = 0x1601
VERSION_LEN = 4 + VERSION_BODY_LEN[AUTH_VERSION_HEADER]   # the auth shape, for callers
CLIENT_SEED_LEN = 2 + 64
SERVER_SEED_LEN = 2 + 20

# The ports a LIVE session may put capturable bytes on.
#
# THIS WAS `(6112,)` AND IT COST A SESSION. Runs one and two captured fine on 6112, so the
# third was run with the same narrow filter; it recorded ZERO bytes across ten minutes
# while nine keys were tapped, and a WinDivert smoke test on port 443 immediately
# afterwards returned recv=238 parsed=238 recorded=137 -- so the driver, the parser and the
# direction logic were all healthy and the filter was simply not where the traffic was.
# The difference from runs one and two is that the client now has its updater enabled, so
# it streams content; the key tap fires on every DH-keyed MsgConn connection, and nothing
# says those all live on 6112.
#
# THE COSTS ARE WILDLY ASYMMETRIC, which is the whole argument. A port in this list that
# carries nothing costs a few bytes of filter. A port MISSING from it costs an authorized
# live session, unrecoverably, because the ciphertext is never recorded and the keys that
# were tapped decrypt nothing. So the list is now GW's whole known port range, taken from
# this repo's own probe design (studies/handshake/PLAN.md: the probe binds 6601, 6112,
# 6600, 6113, 80, 443, 6111 and 6114 precisely because those are the ports the client might
# dial), minus 80/443 -- Stage A is TLS to account.arena.net under a key we do not hold,
# and sniffing 443 would record the machine's entire web traffic to no purpose.
#
# The previous comment argued 6601 should be excluded because it is only used when
# `-portal` is SET. That reasoning is still correct and is now irrelevant: being right
# about a port that carries nothing saves nothing, and being wrong about one loses a
# session. `_hold` samples the client's own connections and the capture's watchdog reports
# per-stage counters, so what actually carried traffic is now MEASURED per run rather than
# assumed here.
#
# AND 80, WHICH IS WHERE IT ACTUALLY WAS. Run four (2026-08-07 14:17) tapped six keys and
# captured nothing on the whole 6111-6601 range, while the driver's new connection sampler
# named the client's real peers: `52.3.40.244:80` and `52.55.104.238:80`. Those are the
# SAME two ArenaNet addresses that carried 6112 in runs one and two -- same servers,
# different port. Guild Wars can run its channels over 80 (the firewall-friendly path), and
# on this machine it now does. That is the whole reason three sessions recorded zero bytes.
#
# 443 is still excluded: the portal is TLS under a key we do not hold, and 443 is where a
# machine's other traffic lives. Port 80 is comparatively quiet now that the web is HTTPS,
# and `prune_wire` drops every captured connection that carries no GW handshake, so
# unrelated HTTP does not survive into the artifact.
LIVE_PORTS = (80, 6111, 6112, 6113, 6114, 6600, 6601)

# WHICH CHANNEL a connection is comes from its VERSION header, which is the field that
# actually carries it -- not from guessing at an opcode.
VERSION_CHANNEL = {AUTH_VERSION_HEADER: "auth", GAME_VERSION_HEADER: "game"}

# WHETHER A KEY IS RIGHT is a separate question, and this is the test.
#
# The first version of this listed literal opcodes -- auth 0x8001, game 0x808a -- taken
# from our own captures. It was wrong, and the live capture of 2026-08-07 proved it: the
# real service's game channels opened with 0x800a and 0x8091, so two connections whose keys
# we HAD were reported undecryptable. A criterion derived from one server's flow does not
# generalise to another's, and the fix is to test a structural property instead of a value.
#
# MEASURED over 534 captures (loopback plus both live ones): the first client->server u16
# has bit 15 SET in 400 of 409 -- the nine exceptions are the 2026-08-04 synthetic
# RURIK-HANDSHAKE markers, not real traffic -- while server->client never sets it. So bit
# 15 is a direction flag, and the remaining 15 bits are an opcode: strip it from every
# observed first message (0x8001, 0x800a, 0x8091, 0x808a -> 1, 10, 145, 138) and all of
# them land inside schema/messages.json's own range, which spans 0x0000-0x01E6 across 777
# entries.
#
# So a candidate key is accepted only if its plaintext starts with the direction bit set
# AND an opcode the catalog could hold. That is 487 of 65536 values, ~1 in 135 for a wrong
# key -- weaker per-trial than a literal match but it accepts the traffic that exists, and
# on the live capture it picks exactly one key per connection, right every time, out of
# three candidates each. Still a check that CAN fail, which is the requirement.
CMSG_DIRECTION_BIT = 0x8000
MAX_CATALOG_OPCODE = 0x01E6


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
    if len(stream) < 4:
        raise SplitError(f"c2s stream is {len(stream)} bytes, too short for a header")
    header = int.from_bytes(stream[0:4], "little")
    if header not in VERSION_BODY_LEN:
        raise SplitError(f"c2s does not start with VERSION (got header 0x{header:08x}; "
                         f"known: " +
                         ", ".join(f"0x{h:08x}" for h in sorted(VERSION_BODY_LEN)) + ")")
    version_len = 4 + VERSION_BODY_LEN[header]
    if len(stream) < version_len + CLIENT_SEED_LEN:
        raise SplitError(f"c2s stream is {len(stream)} bytes, too short for the handshake")
    seed_hdr = int.from_bytes(stream[version_len:version_len + 2], "little")
    if seed_hdr != CLIENT_SEED_HEADER:
        raise SplitError(f"CLIENT_SEED header is 0x{seed_hdr:04x} at offset {version_len}, "
                         f"expected 0x4200")
    a_off = version_len + 2
    A = stream[a_off:a_off + 64]
    return A, stream[version_len + CLIENT_SEED_LEN:]


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

    # DERIVE the stamp, and RECORD what it was derived from. This site hardcoded LIVE and
    # wrote no address at all, which is the worst of both: dryrun_keycapture.py drives it
    # against 127.0.0.1, so vault/dryrun/dryrun_decrypted.jsonl claimed to be live traffic,
    # and because it named no endpoint the contradiction check had nothing to catch it
    # with. Deriving without recording would have left it merely unfalsifiable; the
    # `endpoints` record below is what lets a reader disagree with the stamp.
    endpoints = [str(meta.get("client", "")), str(meta.get("server", ""))] if meta else []
    addrs = [e for e in endpoints if origin.is_address(e)]
    who = origin.OURS if addrs and all(origin.is_loopback(a) for a in addrs) else origin.LIVE
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(origin.record("toolkit/harness/livesession.py", who,
                                          note="decrypted from an off-wire capture")) + "\n")
        fh.write(json.dumps({"kind": "endpoints", "client": endpoints[0] if endpoints else "",
                             "server": endpoints[1] if len(endpoints) > 1 else ""}) + "\n")
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


def key_fits(plain):
    """Does this decrypted c2s stream look like real client traffic? See CMSG_DIRECTION_BIT.

    Two bytes decide it: the direction bit must be set and the opcode must be one the
    catalog could hold. Deliberately NOT a channel verdict -- the channel comes from the
    VERSION header, which is the field that carries it.
    """
    if len(plain) < 2:
        return False
    op = int.from_bytes(plain[:2], "little")
    return bool(op & CMSG_DIRECTION_BIT) and (op & ~CMSG_DIRECTION_BIT) <= MAX_CATALOG_OPCODE


def channel_of_stream(c2s_stream):
    """'auth' / 'game' from a c2s stream's VERSION header, or None if it has none."""
    if len(c2s_stream) < 4:
        return None
    return VERSION_CHANNEL.get(int.from_bytes(c2s_stream[0:4], "little"))


def build_for(wire_path, connection):
    """The client build for one connection, or None. NEVER a guess.

    Closes the asymmetry `tape.client_version`'s own docstring records: the
    decrypted `game-*.jsonl` did not carry the build, so `origin.build_of` had
    nothing to infer from and every live capture in the vault classifies as
    build-unknown. The number is the CLIENT's, parsed from its own VERSION frame
    in `wire.jsonl` -- not from anything we wrote, and not from `pinned.BUILD`,
    which would be us telling ourselves what we already assumed.

    Any failure returns None and the field is omitted. An unstamped capture is a
    known gap; a wrongly stamped one is a fact nobody can refute later.
    """
    try:
        import tape                                          # noqa: PLC0415
        return tape.client_version(os.path.dirname(wire_path), connection)["build"]
    except Exception:                                        # noqa: BLE001
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
        # The channel is read from the VERSION header -- the field that carries it -- not
        # inferred from whatever the first opcode happens to be.
        channel = channel_of_stream(entry[wc.C2S]) or "unknown"
        row["channel"] = channel

        fits = [(label, key) for label, key in keys
                if key_fits(decrypt_stream(c2s_cipher, key))]
        if not fits:
            row.update({"decrypted": False,
                        "why": f"none of the {len(keys)} tapped key(s) decrypt this "
                               f"connection to a plausible client opcode"})
            results.append(row)
            continue
        # Dedup on the KEY BYTES, not the label. This tested `{f[0] for f in fits}` -- the
        # label -- and labels are `tap@{t}s` with t rounded to 2dp, so two genuinely
        # different keys sharing a rounded timestamp (or any entry whose `t` is missing,
        # which load_keyring labels "tap@?s") collapsed to one and the refusal silently
        # became "take fits[0]". Found by adversarial review 2026-08-07; not triggered by
        # any real capture yet, and it is the one guard this module advertises as a check
        # that can fail.
        if len({f[1] for f in fits}) > 1:
            # More than one key passing means the criterion is not discriminating here, not
            # that either is right. Refuse rather than pick -- a wrong key writes a file
            # full of noise that reads like a capture.
            row.update({"decrypted": False,
                        "why": f"{len(fits)} different keys all fit; refusing to choose"})
            results.append(row)
            continue
        label, key = fits[0]
        safe = str(key_name).replace(":", "_").replace("->", "-to-")
        out_path = os.path.join(out_dir, f"{channel}-{safe}.jsonl")
        c2s_plain = decrypt_stream(c2s_cipher, key)
        s2c_plain = decrypt_stream(s2c_cipher, key)
        # DERIVE the stamp from the endpoints this connection actually had, rather than
        # asserting LIVE because this file is called livesession.py. The dry-run drives the
        # very same code against 127.0.0.1, so an asserted LIVE is wrong every time it runs
        # -- and origin.py now REFUSES a live stamp on an all-loopback file, so asserting it
        # here would produce artifacts that classify UNKNOWN and look like a defect.
        who = origin.OURS if all(origin.is_loopback(h) for h in str(key_name).split("->")
                                 if origin.is_address(h)) else origin.LIVE
        build = build_for(wire_path, key_name)
        stamp = {} if build is None else {"build": build}
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(origin.record("toolkit/harness/livesession.py", who,
                                              note=f"decrypted from an off-wire capture of "
                                                   f"{key_name}", **stamp)) + "\n")
            fh.write(json.dumps({"kind": "version", "channel": channel,
                                 "connection": key_name, "key_from": label,
                                 **stamp}) + "\n")
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
    # Clear channel files this run did NOT write. Without this, a re-assemble that decrypts
    # fewer connections leaves the previous run's files sitting beside the new report --
    # MEASURED by adversarial review: re-assembling with 1 of 6 keys prints "1/6" while all
    # six decrypted files are still on disk. Anyone checking replayability by "the six
    # files are there" gets a false pass. That is exactly R0a's failure shape, where a row
    # stood on artifacts that were not the thing being claimed. Deleted only AFTER the new
    # files are written, so a failed assembly cannot destroy a good one.
    written = {os.path.basename(r["out"]) for r in results if r.get("out")}
    stale = sorted(f for f in os.listdir(out_dir)
                   if f.endswith(".jsonl") and f.split("-")[0] in VERSION_CHANNEL.values()
                   and f not in written)
    removed, kept = [], []
    if written and stale:
        # This run produced a real result, so its file set is the truth and leftovers from
        # a previous one must go.
        for f in stale:
            os.remove(os.path.join(out_dir, f))
        removed = stale
    elif stale:
        # This run produced NOTHING. Deleting here would let a failed check destroy a good
        # decryption -- the verification step must not be the risk. Keep them and say
        # loudly that they do not belong to this report.
        kept = stale
        print(f"  WARNING: this assembly decrypted nothing, and {len(kept)} channel file(s)"
              f" from an EARLIER run are still here.\n"
              f"           They are NOT this report's output: {', '.join(kept)}",
              flush=True)
    return {"wire": wire_path, "meta": meta, "connections": results,
            "decrypted": sum(1 for r in results if r.get("decrypted")),
            "total": len(results), "stale_removed": removed, "stale_kept": kept}


# ------------------------------------------------- the pre-registration seal --
# `path` is absolute, `sha256` is over the RAW BYTES (marks.plan_sha256's rule: a changed
# line ending is a different plan and should read as one), `steps` is the parsed step
# count and exists to be compared against `marks_meta`'s own, `sealed_utc` records WHEN --
# which is the only claim this whole object makes that the manifest could not have made
# for itself at the end of the run -- and `body` is the plan's own text, carried so the
# capture can ARCHIVE the prediction rather than only a hash of it (see write_seal_file).
PlanSeal = collections.namedtuple("PlanSeal", "path sha256 steps sealed_utc body")


def _plan_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def seal_plan(plan_path):
    """Parse and hash the operator-mark plan. Call this BEFORE anything launches.

    The parse and the hash both go through `marks.py` rather than being re-implemented
    here: two parsers for one format is how they drift, and `marks.load_plan` is the one
    that will actually read this file in the second shell. So a plan this driver accepts
    is a plan the marker can run, by construction and not by agreement.

    THE HASHED BYTES MUST BE THE PARSED BYTES, and the first version of this function did
    not guarantee that. It called `marks.load_plan(path)` and then `marks.plan_sha256(path)`
    -- two independent reads with a window between them -- and adversarial review 2026-08-13
    drove a rewrite into that window: `steps` came from read #1 and `sha256` from read #2,
    so the manifest recorded a hash of bytes that were never parsed and never passed a
    refusal, beside a step count describing a different file. The consequence was worse than
    the window: `compare_plan_seals` would then hit its step-skew branch and report "the two
    parsers disagree, not the file moved", which is a confident WRONG diagnosis.
    The atomic fix -- read once, hash that buffer, parse that buffer -- is not available
    without a second parser, because `marks.load_plan` takes a PATH and owns the format.
    So the seal buys atomicity with a RE-HASH instead: hash, parse, hash again, and refuse
    if the two hashes differ. What that certifies is exact -- these bytes were on disk both
    before and after the parse -- and it is checkable, which "there is a small window" is
    not.

    Every refusal is re-raised as a `LiveError`, which is what the rest of this module's
    pre-launch gates are, so `main()`'s exit path and `--confirm`/`--mode` all behave the
    same way. `marks.MarksError` is deliberately an `Exception` rather than a `SystemExit`
    over there (see its header); here it must be a refusal that stops the run, and the
    translation is this function's job rather than the caller's.

    THE `except` CLAUSE USED TO NAME ONLY `marks.MarksError`, and two whole classes of
    unreadable plan escaped it as bare tracebacks with no mention of `--plan`: a file saved
    as UTF-16 or cp1252 by a human's text editor (`marks.load_plan` opens `encoding="utf-8"`
    and wraps nothing, so a smart quote raises `UnicodeDecodeError`), and a file that is
    locked or on a network path that drops (`PermissionError`/`OSError` -- and note the
    asymmetry inside marks.py, where `plan_sha256` DOES wrap `OSError` into `PlanError` and
    `load_plan` does not, so which of the two read first decided whether the operator got a
    refusal or a traceback). Both land before the launch, so neither ever cost a session --
    this is the refusal contract breaking, not the seal. The encoding case gets its own
    message because the remedy the generic one offers (`--check-plan`) reads the file with
    the same loader and fails on the same bytes.
    """
    try:
        if not plan_path or not os.path.isfile(plan_path):
            # Delegate these two to marks.py, whose messages are the right ones: "no plan
            # file. An unlabelled run must not be reachable by accident" is the exact
            # sentence for the `--plan ""` an unset shell variable produces.
            marks.load_plan(plan_path)
        raw = _plan_bytes(plan_path)
    except (marks.MarksError, OSError) as exc:
        raise LiveError(_plan_refusal(plan_path, exc)) from exc
    try:
        body = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LiveError(
            f"--plan {plan_path!r} is not UTF-8 text: {exc}\n"
            f"  This is what a text editor's \"Unicode\" (UTF-16) save looks like, or a\n"
            f"  smart quote pasted in as cp1252. The marker reads it as UTF-8 too, so\n"
            f"  --check-plan would fail on the same bytes: re-save the file as UTF-8.\n"
            f"  Nothing has launched -- this costs a re-save, not a session.") from exc
    sha = hashlib.sha256(raw).hexdigest()
    try:
        steps = marks.load_plan(plan_path)        # empty / malformed refuse here
        again = hashlib.sha256(_plan_bytes(plan_path)).hexdigest()
    except (marks.MarksError, OSError) as exc:
        raise LiveError(_plan_refusal(plan_path, exc)) from exc
    if again != sha:
        raise LiveError(
            f"--plan {plan_path!r} CHANGED WHILE IT WAS BEING SEALED: {sha} before the\n"
            f"  parse and {again} after it. The seal would certify bytes that were never\n"
            f"  parsed. Close whatever is writing the file and re-run -- nothing has\n"
            f"  launched.")
    return PlanSeal(os.path.abspath(plan_path), sha, len(steps),
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), body)


def _plan_refusal(plan_path, exc):
    return (f"--plan {plan_path!r} is refused: {exc}\n"
            f"  The plan is the PRE-REGISTERED prediction and it is read BEFORE the client\n"
            f"  launches, so this costs you nothing but a retype. Check it first with:\n"
            f"      python toolkit/harness/marks.py --check-plan \"{plan_path}\"")


def plan_manifest(seal):
    """The manifest's plan block, for a seal or for the explicit absence of one.

    THE ABSENT CASE WRITES THE KEYS, and that is the design rather than tidiness. A
    consumer reading a manifest has to be able to tell three states apart: this run sealed
    a plan; this run had the flag and did not use it; this manifest was written before the
    flag existed. The first two are `plan_sealed` true/false and the third is the key not
    being there at all -- so omitting the key on an unsealed run would collapse "the
    operator chose not to" into "the tool could not", which is the same shape as
    `origin.py` refusing to let UNKNOWN and OURS share a value.

    BOTH BRANCHES CARRY THE SAME SEVEN KEYS, which they did not at first: `plan_sealed_utc`
    was on the sealed branch only and `plan_unsealed_reason` on the unsealed one only, so a
    consumer reading either by name got a `KeyError` on the other half of the corpus. That
    is the same defect this docstring's first paragraph is about, one level down -- an
    omitted key is not a null one -- so the branch-specific fields are written as `None`
    rather than left out, and `plan_sealed` stays the single discriminator.

    The path is written UNREDACTED and the reason is worth stating, because `args` two
    lines below it is not: `accounts.redact_for_file` blanks the VALUE following a secret
    FLAG (`-password`, `-email`) in an argv list, and a plan path is neither of those. The
    protection this field relies on is the same one `exe` and `gw_log` already rely on --
    `manifest.json` is not a `.jsonl`, so `scrub_captures.scrub_tree` never copies it, and
    it stays in the vault with the rest of the capture. MEASURED 2026-08-13 by adversarial
    review, which ran `scrub_tree` over a capture whose plan path was
    `C:\\Users\\<a real name>\\Documents\\gw plan.txt` and confirmed the scrubbed output held
    `SCRUB-MANIFEST.json` and `wire.jsonl` and nothing else. Worth recording rather than
    assuming next time: `plan_path` is the FIRST manifest field that is an arbitrary
    OPERATOR-chosen path from outside the vault (`exe` is under `vault/run-live`, `gw_log`
    sits beside it), and `C:\\Users\\<name>\\Documents` is exactly where a person writes a
    text file on Windows.
    """
    if seal is None:
        return {"plan_sealed": False, "plan": None, "plan_path": None,
                "plan_sha256": None, "plan_steps": None, "plan_sealed_utc": None,
                "plan_unsealed_reason":
                    "no --plan was passed: this session carries no pre-registered "
                    "operator-mark plan, so its marks (if any) are labels written after "
                    "the fact rather than a prediction stated first"}
    return {"plan_sealed": True,
            # The BASENAME under `plan`, matching what `marks_meta` records under the same
            # key, so a reader of either artifact sees the same name. It is deliberately
            # NOT what `compare_plan_seals` decides on -- an earlier comment here claimed
            # the two seals "compare field-for-field", and adversarial review 2026-08-13
            # pointed out that no comparison of the names exists or should: the seal is
            # over CONTENT, so two files with identical bytes are the same prediction
            # whatever they are called, and the manifest stores an absolute path while
            # `marks_meta` stores a basename, which is not a comparison at all. The names
            # are carried into the verdict MESSAGE instead, where a reader can use them.
            # The absolute path is beside it because that is what re-binding needs months
            # later.
            "plan": os.path.basename(seal.path), "plan_path": seal.path,
            "plan_sha256": seal.sha256, "plan_steps": seal.steps,
            "plan_sealed_utc": seal.sealed_utc, "plan_unsealed_reason": None}


def write_seal_file(outdir, seal):
    """Put the seal on disk the moment the capture directory exists. Returns the path.

    The manifest is written at the END of the run and a live run does not always reach its
    end -- a Ctrl-C inside cleanup already cost this project a whole session's manifest
    once (see `_install_sigint`). The seal is the one field whose value depends on WHEN it
    was taken, so re-deriving it afterwards is exactly what it exists to prevent: a run
    that died would leave `marks_meta`'s post-launch hash as the only surviving seal. Same
    lesson as `KeyRing._persist`, one artifact over.

    Both this file and the manifest are rendered from the SAME `PlanSeal`, so they cannot
    disagree; this one is just earlier. It is written for an UNSEALED run too, carrying
    `plan_sealed: false` -- the absence is recorded for the same reason the manifest
    records it, and a directory with no `plan_seal.json` at all then means a run whose
    driver predates the flag.

    THIS FILE, AND NOT THE MANIFEST, ARCHIVES THE PLAN'S TEXT. Until 2026-08-13 the capture
    held a hash of a file living somewhere else entirely, so an operator who deleted or
    rewrote the plan afterwards left a pre-registration that could only ever be FAILED
    against and never READ -- which is half of what a pre-registration is for. `plan_body`
    is the plan verbatim, and it is self-checking rather than decorative: it is the same
    buffer the seal was taken over, so `sha256(plan_body.encode("utf-8"))` must equal
    `plan_sha256`, and a reader who finds it does not can say which of the two is wrong.
    It goes here rather than in the manifest because the manifest is the file a census
    walks over hundreds of captures, and a multi-line body belongs beside the capture
    rather than in the index.

    Because two rounds of adversarial review both got here: the CALL SITE in `run()` is
    what makes any of this true, and deleting that one line left the whole suite green.
    The syntax-tree and runtime checks in `test_livesession.py` §5a/§5f pin it now.
    """
    path = os.path.join(outdir, "plan_seal.json")
    rec = plan_manifest(seal)
    if seal is not None:
        rec["plan_body"] = seal.body
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    return path


MARKS_BANNER = "*** THIS RUN HAS NO PRE-REGISTERED PLAN ***"


def marks_instructions(seal, outdir, pid=None):
    """The console block for the second shell: the command, or the loud absence of one.

    Returns a list of lines rather than printing, so the one thing that MUST differ
    between a sealed run and an unsealed one is a value a test can assert on. That is not
    style: `test_harness.py` earned the same shape on `--enemy`, where a warning that
    fires either way is noise and a warning that fires neither way is silence, and only a
    check on both branches separates them.

    The capture directory is spelled RESOLVED and in quotes because the operator has to
    type it into a different shell while a client is coming up -- the same reason the STOP
    and MARK lines beside it are absolute.

    The unsealed branch deliberately prints NO runnable marks.py command. An operator who
    started the marker now would be writing a plan AFTER the client launched, which is a
    label and not a pre-registration, and offering the command would invite exactly that.
    """
    if seal is None:
        return [
            f"  {MARKS_BANNER}",
            "  --plan was not passed, so nothing seals what you are about to do before you",
            "  do it. The capture is still worth taking -- it is UNLABELLED, not spoiled --",
            "  and the manifest records that as \"plan_sealed\": false rather than by",
            "  leaving the key out.",
            "  Do NOT start marks.py now: a plan written after the client launched is a",
            "  label, not a prediction. Next run, write the plan first, check it with",
            "    python toolkit/harness/marks.py --check-plan <plan.txt>",
            "  and pass --plan to this driver.",
        ]
    cmd = (f"python \"{os.path.join(HERE, 'marks.py')}\" "
           f"--plan \"{seal.path}\" --capture \"{os.path.abspath(outdir)}\"")
    if pid:
        cmd += f" --pid {pid}"
    return [
        "  A SECOND SHELL, FOR THE PRE-REGISTERED MARKS (F9 advance / F10 repeat / F11 note):",
        f"    {cmd}",
        f"  plan {os.path.basename(seal.path)}: {seal.steps} step(s), "
        f"sha256 {seal.sha256[:16]}...",
        "  That hash was taken BEFORE this client launched and is already in the manifest.",
        "  marks.py prints its own on startup, from its own read -- if the two differ, the",
        "  plan changed in between and neither run is a pre-registration any more.",
        # The one failure this driver can warn about and cannot prevent: marks.py is handed
        # the capture directory that already holds plan_seal.json and does not read it, so
        # a RETYPED --plan naming a different file starts cleanly and is only contradicted
        # afterwards, in the manifest's plan_seals field. Adversarial review 2026-08-13
        # built exactly that (seal plan_A, mark against plan_B) and got a manifest reading
        # plan_sealed true with nothing in it disagreeing. Copying the line is the fix an
        # operator can apply today; a refusal inside marks.py is the one that belongs.
        "  COPY the line above -- do not retype it. A different file with the same name",
        "  seals nothing, and marks.py cannot tell: the mismatch is only reported after",
        "  the run, in manifest.json's plan_seals field.",
        "  Start it before you log in. Its keys are SWALLOWED and never reach the client.",
    ]


# ---------------------------------------- the second witness, on the way back --
SEAL_AGREE, SEAL_DISAGREE, SEAL_UNCHECKED = "agree", "disagree", "unchecked"


SEAL_FILES = ("manifest.json", "plan_seal.json")


def seal_records(outdir):
    """({filename: record}, {filename: why-not}) over `manifest.json` and `plan_seal.json`.

    Split out of `recorded_seal` so the two seals this DRIVER writes can be compared
    against each other, which is a claim nobody was making. Both are rendered from one
    `PlanSeal` minutes apart, so they cannot legitimately disagree -- and adversarial
    review 2026-08-13 built the version that makes them: a `run()` whose manifest re-hashes
    the plan at the end wrote a manifest certifying the EDITED plan while `plan_seal.json`
    sat in the same directory still holding the original. The evidence was on disk, in two
    files, and nothing read the second one. See `compare_plan_seals`.

    THE SECOND DICT IS NOT TIDINESS. "No seal here" has three causes and they are three
    different facts about a capture: the file is absent, the file is UNREADABLE, or the
    file is a manifest written before `--plan` existed. The first draft of this split
    collapsed the middle one into the last and would have reported a truncated manifest as
    "written before --plan existed" -- a confident wrong statement about provenance, which
    is the same defect as the DISAGREE message that asserted one cause of two.
    """
    out, notes = {}, {}
    for name in SEAL_FILES:
        path = os.path.join(outdir, name)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                rec = json.load(fh)
        except (OSError, ValueError) as exc:
            notes[name] = f"{name} cannot be read as JSON ({exc}), so it answers nothing"
            continue
        if not isinstance(rec, dict):
            notes[name] = f"{name} is not a JSON object, so it answers nothing"
        elif "plan_sealed" not in rec:
            notes[name] = (f"{name} carries no plan_sealed key, so it was written "
                           f"before --plan existed -- unsealed by construction, not "
                           f"by choice")
        else:
            out[name] = rec
    return out, notes


def recorded_seal(outdir):
    """(seal dict, source-or-reason) as this driver recorded it, or (None, reason).

    Prefers `manifest.json` and falls back to `plan_seal.json`, because a run that died
    before assembly has the second and not the first -- which is the whole reason
    `write_seal_file` exists. The second element NAMES the file the seal came from on
    success, and the caller carries that into its verdict: "the seals agree" is a
    different claim depending on which artifact was read, and a fallback that is invisible
    in the report is a fallback nobody can tell fired.

    A file with no `plan_sealed` key at all does NOT stop the search -- it is a driver
    older than the flag rather than an answer -- so the older reason is remembered and
    only returned if nothing better turns up.
    """
    recs, notes = seal_records(outdir)
    for name in SEAL_FILES:
        if name not in recs:
            continue
        rec = recs[name]
        if not rec.get("plan_sealed"):
            return None, (f"{name} records plan_sealed false: this run was driven without "
                          f"--plan and there is no pre-launch seal to compare")
        return rec, name
    # Nothing carried a seal. Say WHICH of the three reasons, in file order -- a capture
    # from a driver older than --plan and one whose manifest is truncated are not the same
    # finding, and the second must not be reported as the first.
    for name in SEAL_FILES:
        if name in notes:
            return None, notes[name]
    return None, f"no manifest.json and no plan_seal.json in {outdir}"


def internal_seal_conflict(outdir):
    """(True, why) when this driver's OWN two seal records disagree, else (False, why-not).

    `manifest.json` and `plan_seal.json` are rendered from the same `PlanSeal` at two
    moments in one run, so a disagreement is not a fact about the operator's plan at all
    -- it is a fact about the DRIVER, and it means something between the two writes
    re-derived a value that was supposed to be carried. That is exactly the sabotage that
    got through two rounds of checks on 2026-08-13 (`manifest = {..., "plan_sha256":
    sha256(seal.path)}` using this module's own file hasher), and its evidence was sitting
    in the capture directory the whole time.

    Checked BEFORE the marker comparison, because the marker cannot arbitrate it: if the
    driver contradicts itself, "which of the two does marks.py agree with" is the wrong
    question and answering it would launder a broken driver into an AGREE.
    """
    recs = {n: r for n, r in seal_records(outdir)[0].items() if r.get("plan_sealed")}
    if len(recs) < 2:
        return False, (f"only {len(recs)} sealed record here, so there is nothing for this "
                       f"driver to contradict itself with")
    shas = {n: r.get("plan_sha256") for n, r in recs.items()}
    if len(set(shas.values())) == 1:
        return False, "this driver's own two seal records agree"
    return True, (
        "THIS DRIVER CONTRADICTS ITSELF. " + ", ".join(
            f"{n} says {s}" for n, s in sorted(shas.items())) +
        ". Both are rendered from ONE PlanSeal taken before the launch, so they cannot "
        "legitimately differ: something between the two writes re-read the plan file "
        "instead of using the carried value, which means the later of the two is a hash "
        "of the plan as it stood AFTER the session. Trust neither, and read plan_seal.json "
        "-- it is written when the capture directory appears and is the earlier of the two.")


def compare_plan_seals(outdir):
    """(verdict, why) -- the driver's PRE-LAUNCH seal against marks.py's own.

    THREE-VALUED, never two. `SEAL_UNCHECKED` is not a pass: the operator may legitimately
    never have run the marker, and folding that into `agree` would turn the one comparison
    this pair of tools makes possible into a field that reads green whenever it is absent.
    Same rule `origin.py` applies to ours/live/unknown.

    WHAT IT CATCHES THAT `marks.bind()` CANNOT. `bind` hashes the plan as it is NOW and
    refuses if that disagrees with `marks_meta` -- which catches an edit made after the
    marker started, and is blind to one made BETWEEN the client launching and the marker
    starting, since both of its reads would then see the edited file. Only the driver's
    pre-launch hash can refute that, and only here are all three artifacts on disk.

    The step counts are compared too, and they are not redundant with the hash: they are
    two different readings of the same file by two processes, so a disagreement in counts
    with matching hashes would mean the two parsers disagree rather than the file moved.

    WHERE THIS IS CALLED FROM CHANGED ON 2026-08-13, and the argument that kept it off the
    live path was wrong on its own terms. It used to run only from `reassemble()`, i.e.
    only under `--assemble`, on the reasoning that `plan_marks.jsonl` might not exist when
    the manifest is written and a check that skips in every real run is a check that cannot
    fail. Two things were being conflated. This is not a check -- it is a THREE-VALUED
    RECORDED FIELD, the same shape `origin.py` uses, and `UNCHECKED` is a legitimate value
    for it rather than a skip. And the timing does not bite anyway: the driver prints
    `--pid <client.pid>` in the marks command, `marks.run` ends on that pid, and the
    manifest is written after client teardown, pruning, assembly and the scrub, so a marker
    the operator actually ran has long since closed its file. So `run()` records the verdict
    at manifest time and `reassemble()` recomputes and rewrites it -- because until then the
    one comparison this pair of tools makes possible existed only in console scrollback,
    and a verdict that never reaches an artifact is a verdict nobody can act on months
    later.

    THE DISAGREE MESSAGE NAMES BOTH CAUSES, which it did not at first. A sha mismatch has
    two: the file changed between the two reads, or the operator typed a DIFFERENT file
    into the second shell. The first version asserted the first cause in capitals, and
    adversarial review 2026-08-13 produced the second by sealing `plan_A.txt` and marking
    against `plan_B.txt` -- the message then said "THE PLAN CHANGED" about two files that
    were both untouched and both still on disk. The two names are reported because a reader
    can use them (different basenames make cause two likely), and they are deliberately NOT
    part of the verdict: the seal is over CONTENT, so two paths holding identical bytes are
    the same prediction, and a name comparison would manufacture a DISAGREE out of a file
    that was merely copied.
    """
    conflict, why = internal_seal_conflict(outdir)
    if conflict:
        return SEAL_DISAGREE, why
    ours, source = recorded_seal(outdir)
    if ours is None:
        return SEAL_UNCHECKED, source
    mpath = os.path.join(outdir, marks.PLAN_MARKS_NAME)
    if not os.path.isfile(mpath):
        return SEAL_UNCHECKED, (
            f"a plan was sealed ({ours.get('plan')}, sha256 "
            f"{str(ours.get('plan_sha256'))[:16]}...) but there is no "
            f"{marks.PLAN_MARKS_NAME} here, so the marker was never run or wrote elsewhere")
    try:
        meta, _rows = marks.read(mpath)
    except marks.MarksError as exc:
        return SEAL_UNCHECKED, f"{marks.PLAN_MARKS_NAME} cannot be read: {exc}"
    theirs = meta.get("plan_sha256")
    if not theirs:
        return SEAL_UNCHECKED, f"{marks.PLAN_MARKS_NAME}'s marks_meta carries no plan_sha256"
    if theirs != ours.get("plan_sha256"):
        return SEAL_DISAGREE, (
            f"THE TWO SEALS ARE OF DIFFERENT BYTES. Per {source}, this driver hashed "
            f"{ours.get('plan_sha256')} before the client launched (plan "
            f"{ours.get('plan')}); marks.py hashed {theirs} when the marker started (plan "
            f"{meta.get('plan')}). TWO CAUSES produce this and the artifact cannot tell "
            f"them apart on its own: the plan file was EDITED between the launch and the "
            f"marker, or the operator pointed the second shell at a DIFFERENT file -- "
            f"compare the two names above, and read plan_seal.json's plan_body, which is "
            f"the prediction as it stood before the launch. Either way the marks in this "
            f"capture are labels against a plan that is not the one that was "
            f"pre-registered, and marks.bind() cannot see this -- it compares the marker's "
            f"hash against the file as it stands now, and under the first cause both of "
            f"those are the edited version.")
    if meta.get("steps") is not None and ours.get("plan_steps") is not None \
            and meta["steps"] != ours["plan_steps"]:
        return SEAL_DISAGREE, (
            f"the two seals agree on the bytes and disagree on the STEPS: this driver "
            f"parsed {ours['plan_steps']} and marks.py parsed {meta['steps']} out of the "
            f"same sha256. That is the two parsers disagreeing, not the file moving.")
    # The names are REPORTED and not decided on -- see the docstring. `marks_meta` stores a
    # basename and the manifest an absolute path, so they are quoted separately rather than
    # compared: a reader who sees two different names beside one sha knows the plan was
    # copied or renamed, which is a fact worth having and not a disagreement.
    return SEAL_AGREE, (
        f"two independent seals agree: sha256 {theirs[:16]}..., "
        f"{ours.get('plan_steps')} step(s), taken in different processes at different "
        f"moments -- one before the client launched (per {source}, plan "
        f"{ours.get('plan')}), one when the marker started (plan {meta.get('plan')})")


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


# The owner's own install, which is the ONLY thing in reach that knows what build
# ArenaNet is serving today. Read-only, always: CLAUDE.md's rule is that this
# directory is never patched and never launched, and reading its bytes is allowed.
LIVE_INSTALL_EXE = r"C:\gw\Gw.exe"


def service_build():
    """(build, why) for the build the live service is currently serving.

    Derived from the owner's auto-updating install rather than from any pin --
    `buildid.of_image` names that install as a case it exists to handle. A pin
    cannot answer this question by construction: the pin is what we last chose,
    the service serves whatever it shipped this morning.
    """
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
    import buildid                                   # stdlib + gwpe only
    if not os.path.isfile(LIVE_INSTALL_EXE):
        return None, f"no install at {LIVE_INSTALL_EXE}"
    return buildid.of_image(LIVE_INSTALL_EXE)


def _run_live_builds():
    """{build number: [directory, ...]} for every staged live build. Read from bytes."""
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
    import buildid
    out = {}
    try:
        root = vaultpath.require_dir("run-live", why="naming the build that would work")
    except Exception:                                          # noqa: BLE001
        return out
    for name in sorted(os.listdir(root)):
        exe = os.path.join(root, name, "Gw.exe")
        if os.path.isfile(exe):
            n, _ = buildid.of_image(exe)
            out.setdefault(n, []).append(name)
    return out


def check_build_matches_service(exe):
    """Refuse a live launch whose build is not the one the service is serving.

    WHY THIS IS A REFUSAL AND NOT A WARNING. The updater is LIVE on every
    `run-live/` build by design -- the live client must fetch content during a
    real session -- so an exe older than the service does not fail politely: it
    UPDATES ITSELF, and the key-tap cave is patched at a build-specific address,
    so the tap is gone in the copy that then runs. What that costs is the one
    thing this project rations: an authorized session against the real service,
    spent producing ciphertext with no key. The downstream refusals catch it
    (`slot_rva` re-reads the slot and raises), but they catch it AFTER the login.

    ADDED 2026-08-17, from a question rather than a failure. Asked which build
    to launch, a session hedged -- "whichever matches what ArenaNet serves
    today" -- when the answer was two commands away and doubly determined: the
    owner's install reads 38833 through its own build getter, and `run-live/`
    names its directories `<PE date>_<source sha256[:12]>`, so the directory
    `2026-08-13_64fae3b1369b` is literally named for the sha of the install it
    was patched from. Both witnesses agreed. A question the tools could answer
    and a human could not is exactly the shape that belongs in a preflight.

    SKIPS, LOUDLY, when the owner's install is not on this machine -- the
    checkable thing is absent, which is not the same as checked and fine.
    """
    import sys as _sys
    _sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
    import buildid
    want, want_why = service_build()
    have, have_why = buildid.of_image(exe)
    if want is None:
        print(f"  [skip] cannot check the launch build against the service: {want_why}.\n"
              f"         The exe reads build {have}. Nothing verified this is the build "
              f"the service serves.", flush=True)
        return {"checked": False, "why": want_why, "launch_build": have}
    if have is None:
        raise LiveError(
            f"cannot read a build number out of the launch client ({have_why}), while the "
            f"service is serving {want}. Refusing rather than launching an unidentified "
            f"binary at the real service.")
    if have != want:
        staged = _run_live_builds()
        fix = (f"  vault/run-live/{staged[want][0]} is build {want} -- launch that one."
               if staged.get(want) else
               f"  NO staged live build is {want}. Rebuild:\n"
               f"    python toolkit/clientpatch/make_custom_client.py "
               f"--no-dh-patch --key-tap\n"
               f"    python toolkit/clientpatch/make_run_dir.py --live")
        raise LiveError(
            f"the launch client is build {have}; the live service is serving {want}.\n"
            f"  A stale live build does not fail politely -- its updater is LIVE by design, "
            f"so it updates ITSELF and the key-tap cave (a build-specific address) is lost "
            f"in the copy that runs. The session would spend the authorized login producing "
            f"ciphertext with no key.\n{fix}\n"
            f"  service: {want_why}\n  launch:  {have_why}")
    print(f"  [ok] launch build {have} matches the service ({want}).", flush=True)
    return {"checked": True, "launch_build": have, "service_build": want}


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

    check_build_matches_service(exe)

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

    def __init__(self, pid, rva, module="Gw.exe", interval=0.25, path=None):
        super().__init__(daemon=True)
        self.pid, self.rva, self.module, self.interval = pid, rva, module, interval
        self.values = []          # [(t, master_secret_bytes)] -- distinct, in order
        self.errors = 0
        self.path = path          # persist here the INSTANT a key appears -- see _persist
        self._seen = set()
        self._stop = threading.Event()
        self.t0 = time.monotonic()
        if self.path:
            with open(self.path, "w", encoding="utf-8") as fh:
                fh.write(json.dumps(origin.record("toolkit/harness/livesession.py",
                                                  origin.LIVE,
                                                  note="tapped session keys, one per "
                                                       "DH-keyed channel")) + "\n")

    def _persist(self, t, master, key):
        """Append one key to disk and FLUSH, the moment it is read.

        This exists because the first live run lost six of seven keys. The keyring was held
        in memory and only the keys that survived assembly reached disk, so six connections
        of real ArenaNet ciphertext -- already captured, gap-free -- became permanently
        undecryptable the moment the process exited. There is no recovering them: the key
        derives from ArenaNet's private exponent.

        So: written per key, not per run, and flushed rather than buffered. A crash, a
        Ctrl-C, a power cut or an exception anywhere downstream now costs at most the key
        being read at that instant, and never a key already seen. Recorded under the field
        names scrub_captures.py treats as secret.
        """
        if not self.path:
            return
        try:
            with open(self.path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"kind": "session_key", "t": t,
                                     "master_secret": master.hex(),
                                     "arc4_key": key.hex()}) + "\n")
                fh.flush()
        except OSError:
            # Never let a disk problem kill the poller: an in-memory key is still better
            # than no key, and the caller's report says how many were persisted.
            self.errors += 1

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
                from gwcrypto import arc4_hash
                self._seen.add(got)
                t = round(time.monotonic() - self.t0, 2)
                self.values.append((t, got))
                self._persist(t, got, arc4_hash(got))
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


def load_keyring(path):
    """[(label, arc4_key)] read back from a persisted keyring.jsonl.

    This is what makes a capture re-assemblable from disk without a second live session --
    the property R0b's criterion asks for and the first run did not have.
    """
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                r = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(r, dict) and r.get("kind") == "session_key" and r.get("arc4_key"):
                out.append((f"tap@{r.get('t', '?')}s", bytes.fromhex(r["arc4_key"])))
    return out


GAME_MODES = ("base", "reforged")


def run(account_label, exe, live_host, live_ports, minutes, confirm, mode=None,
        out_root=None, plan=None):
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
    # --mode is required and has NO DEFAULT, deliberately, and it is the same shape as
    # --confirm one line above: a value the operator must state, refused rather than
    # guessed. See GAME_MODES and the manifest key below for why a default would be worse
    # than useless here.
    if mode not in GAME_MODES:
        raise LiveError(
            f"--mode is required and must be one of {'|'.join(GAME_MODES)} "
            f"(got {mode!r}).\n"
            f"  Reforged Mode changes enemy health and armour by roughly 20%, and NOTHING\n"
            f"  in the recorded stream says which mode produced it. It is not recoverable\n"
            f"  afterwards: every health number from an unstamped capture is base or\n"
            f"  base x 0.8 with nothing on this machine able to say which, forever.\n"
            f"  ~20% is the dangerous size -- it looks like a plausible base value rather\n"
            f"  than an obvious error, so a contaminated number is used rather than caught.\n"
            f"  This is asked BEFORE the client launches because it cannot be asked after,\n"
            f"  and a wrong answer is worse than a refusal: say what the account is\n"
            f"  actually set to, not what you intend it to be.\n"
            f"  The three monster health readings already in the vault (definition slots\n"
            f"  1346=96, 1434=8, 1442=40) predate this flag and are stamped\n"
            f"  mode='unrecorded' -- kept, never promoted. They are the reason this exists.")
    # THE SEAL, AND THIS LINE IS THE FEATURE. Not the hash -- the hash is six lines of
    # hashlib -- but the fact that it is taken HERE: above `preflight`, so before the
    # account is resolved, before `one_live_client` shells out, before the sniffer
    # subprocess and roughly a hundred lines before `subprocess.Popen([exe] + args)`. A
    # seal taken at manifest time (the end of the run, after assembly) would certify
    # whatever the plan said AFTERWARDS, which is not a pre-registration; it is a
    # signature on the answer sheet. Everything downstream reads this carried value and
    # nothing re-hashes the file. See the module header, and the syntax-tree check in
    # test_livesession.py that pins the ordering -- a grep cannot see it.
    #
    # It is also where the refusals land, for the same reason: a malformed plan costs a
    # retype here and an unrepeatable session anywhere later.
    #
    # `is not None`, NOT truthiness, and the difference is the whole unlabelled-by-accident
    # case. `--plan "$PLAN"` with the variable unset hands this an EMPTY STRING, which a
    # truthiness guard routes straight past `marks.load_plan`'s own refusal for exactly
    # that input ("no plan file. An unlabelled run must not be reachable by accident") and
    # into an unsealed run whose manifest then states the FALSE reason "no --plan was
    # passed" -- the operator did pass it. The one distinction this design is built on,
    # "had the flag and did not use it" versus "the tool could not", was silently miscoded
    # by one word. Found by adversarial review 2026-08-13; argparse's own default is None,
    # so absence and emptiness are already distinguishable at this line.
    seal = seal_plan(plan) if plan is not None else None
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
    # On disk NOW, not only in the manifest an hour from now -- see write_seal_file.
    write_seal_file(outdir, seal)
    if seal:
        print(f"  plan    : {os.path.basename(seal.path)} -- {seal.steps} step(s), "
              f"sha256 {seal.sha256[:16]}... SEALED BEFORE LAUNCH")
    else:
        print("  plan    : NONE -- this run will be unlabelled (see the block below)")

    # The live build carries a LIVE auto-updater (owner's decision 2026-08-07 -- the kill
    # switch also disables map streaming and crashed a run on Map.cpp's `found` assert).
    # So the client can now patch ITSELF mid-session, which would replace the binary the
    # frames came from and take the key-tap cave with it. Hash before and after: the
    # question "which build produced these frames" then has an answer on the artifact
    # rather than a rule that used to forbid the situation.
    exe_sha_before = sha256(exe)
    print(f"  build   : sha256 {exe_sha_before[:16] if exe_sha_before else '??'}... "
          f"(re-checked after the run)")

    procs, ring, client, endpoints = [], None, None, set()
    args = []                       # bound in the try; the manifest below reads it either way
    marks_fh = None                 # same: the finally closes it either way
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

        # --- 3. the keyring polls from now until the client stops, writing each key to
        # disk as it appears. See KeyRing._persist for why that is not an optimisation.
        ring = KeyRing(client.pid, rva, path=os.path.join(outdir, "keyring.jsonl"))
        ring.start()

        stop_file = os.path.join(outdir, "STOP")
        mark_file = os.path.join(outdir, "MARK")
        marks_fh = open(os.path.join(outdir, wc.MARKS_NAME), "w",
                        encoding="utf-8")
        print("\n  YOU drive from here: log in and play at human cadence.")
        print("  TO MARK A MOMENT (what you are about to do), from any shell:")
        print(f"    echo approach > \"{mark_file}\"")
        print("  The text becomes the label. Marks bind your narration to the capture's")
        print("  own clock; without them a session can only be aligned to within seconds")
        print("  after the fact. session_start and session_end are taken automatically.")
        # Two mark channels now reach the operator's eyes at once, so name the difference
        # here rather than leaving them to work it out mid-session. Owner's ruling
        # 2026-08-13: they stay SEPARATE, because free text typed during a run and an
        # ordinal into a plan sealed before launch are different kinds of evidence, and
        # merging them would put both under one "kind" where no consumer could split them.
        print("  That is the DRIVER's channel (marks.jsonl): free text, no prediction. The")
        print("  PRE-REGISTERED channel is the second shell below, and the two stay apart.")
        print("  THREE WAYS TO STOP, and the first only works if THIS WINDOW has focus:")
        print("    1. one Ctrl-C here (the shutdown takes ~30s; pressing again is absorbed)")
        print("    2. just close the Guild Wars window -- same clean path")
        print(f"    3. from any shell:  echo. > \"{stop_file}\"")
        print("  Nothing is lost by killing this process either: the keyring and the wire")
        print("  capture are flushed as they go, and `--assemble` rebuilds the rest.")
        # Printed HERE, with the pid bound and the directory resolved, because this is the
        # block the operator is actually reading before they log in -- not at the top,
        # where it scrolls past behind the launch. The two branches differ in exactly one
        # thing and marks_instructions is where that difference is asserted.
        print("")
        for line in marks_instructions(seal, outdir, pid=client.pid):
            print(line)
        print("")
        _install_sigint()
        endpoints = _hold(client, ring, wire, minutes, cap=cap,
                          stop_file=stop_file, marks_fh=marks_fh,
                          mark_file=mark_file)
    except KeyboardInterrupt:
        print("\n  stopping on Ctrl-C")
    finally:
        # Narrate every step. This phase used to print nothing at all for up to half a
        # minute, which is what made an operator press Ctrl-C again and lose the run.
        if ring:
            ring.stop()
        if client and client.poll() is None:
            print("  closing the client (WM_CLOSE, up to 20s, so Gw.log survives)...",
                  flush=True)
            drive_client.close_client(client)
        print("  stopping the off-wire capture...", flush=True)
        for p in procs:
            if p.poll() is None:
                try:
                    p.terminate()
                    p.wait(timeout=15)
                except (OSError, subprocess.SubprocessError):
                    pass
        if marks_fh:
            marks_fh.close()
        cap_log.close()
        time.sleep(1)
        if os.path.exists(wire):
            print(f"  wire capture: {os.path.getsize(wire) / 1e6:.1f} MB", flush=True)

    # --- 4. offline: assemble what the wire and the keyring hold, then scrub.
    # Prune BEFORE assembling: the filter has to be wide enough to catch GW on port 80, and
    # everything else it caught is the owner's own traffic rather than evidence.
    pruned_records = 0
    if os.path.exists(wire):
        print("  pruning non-GW connections...", flush=True)
        kept, dropped = prune_wire(wire)
        pruned_records = dropped
        print(f"  pruned: {dropped} record(s) from non-GW connections dropped; "
              f"{kept} GW connection(s) kept", flush=True)

    keys = ring.keyring() if ring else []
    print(f"\n  keyring: {len(keys)} distinct session key(s) tapped")
    if not keys:
        print("  NOTE: no key was ever tapped. The wire capture is kept -- it is still the "
              "only recording of a real session -- but nothing can decrypt it.")
    print("  assembling and decrypting...", flush=True)
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

    # Outside the capture tree entirely, under the canonical scrubbed root. Not a child of
    # outdir (scrub_tree walks its source, and an output inside that source is a directory
    # the walk descends into), and not a sibling either -- a sibling lands in
    # vault/captures/, where the TREE-WIDE scrub and every capture census then walk it as
    # if it were more evidence. `captures-scrubbed` is already on the skip list everything
    # else uses, so putting it there makes one rule cover both.
    import scrub_captures
    scrubbed = os.path.join(vaultpath.vault_path("captures-scrubbed"),
                            "live-" + stamp)
    files, records, stats, distinct, _un = scrub_captures.scrub_tree(outdir, scrubbed)
    print(f"  scrub: {files} file(s), {records} records, {distinct} distinct secrets "
          f"replaced -> {scrubbed}")
    if stats.get(scrub_captures.OPAQUE_STAT):
        n_opaque = stats[scrub_captures.OPAQUE_STAT]
        print(f"  scrub: {n_opaque} `plain` frame payload(s) could NOT be cleaned and were "
              f"copied through.")
        print("         The auth channel's first client message carries the account email "
              "as UTF-16")
        print("         inside that blob. This capture is vault-only -- not shareable, "
              "scrubbed or not.")
        # And say so where a person copying the TREE will see it. The per-session manifest
        # records this correctly and nobody copying a directory reads one level down; the
        # root manifest was giving an all-clear written before live captures existed.
        marker = scrub_captures.mark_tree_unsafe(
            os.path.dirname(scrubbed), stamp, [f for f in os.listdir(outdir)
                                               if f.endswith(".jsonl")], n_opaque)
        print(f"         Recorded at {marker}")

    exe_sha_after = sha256(exe)
    if exe_sha_before and exe_sha_after and exe_sha_before != exe_sha_after:
        print("\n  *** THE CLIENT BINARY CHANGED DURING THIS RUN ***")
        print(f"      before {exe_sha_before}")
        print(f"      after  {exe_sha_after}")
        print("      The auto-updater is live on this build (it has to be, for map")
        print("      streaming), so ArenaNet patched the client mid-session. The frames")
        print("      above did NOT all come from one binary, and the key-tap cave is gone")
        print("      from the new one -- rebuild before the next run:")
        print("        make_custom_client.py --no-dh-patch --key-tap --no-updater-patch")
        print("        make_run_dir.py --live")

    # Taken from the DIRECTORY, one statement above the manifest literal, so the literal
    # itself holds no logic. At this moment manifest.json does not exist, so `recorded_seal`
    # falls back to plan_seal.json -- the fallback `write_seal_file` was built for, now
    # exercised on the live path rather than only by a test fixture.
    seal_verdict, seal_verdict_why = compare_plan_seals(outdir)
    print(f"  plan seal: {seal_verdict.upper()} -- {seal_verdict_why}")

    manifest = {"stamp": stamp, "exe": exe, "account": acct["label"],
                # An OPERATOR DECLARATION, and labelled as one on purpose. Every other
                # field here is derived from an artifact; this one cannot be. Reforged
                # Mode leaves no mark on the wire that we have measured, so nothing can
                # check it and nothing should pretend to -- `origin.py`'s design rule is
                # derive-from-the-endpoint-never-self-declare, and mode has no endpoint,
                # so it must not be taught to infer this.
                #
                # THE COROBBORATION THAT WOULD MAKE IT REFUTABLE IS NOT BUILT, and is not
                # faked: a Reforged-only map id appearing on the wire would CONTRADICT a
                # `base` declaration, the same one-directional shape as `origin_of`
                # refusing a `live` stamp on an all-loopback file. It needs a measured
                # list of Reforged-only map ids, which this project does not have -- the
                # 12 decrypted connections load map ids 0, 146, 148 and 164 and none of
                # them is Reforged-only. Writing the check against a guessed list would
                # be a check that cannot fail in the direction that matters.
                "game_mode": mode, "game_mode_source": "operator-declared",
                # The pre-registration seal, rendered from the value CARRIED down from
                # before the launch. `plan_manifest` takes the seal and never a path, so
                # there is no file for this site to re-read: a hash taken here would be a
                # hash of the plan as it stands after the session, which is the one thing
                # the seal exists to rule out. FINDINGS §10.5.1 asks for the sha256; the
                # step count is beside it because `marks_meta` records its own and two
                # readings of one file are a claim rather than a note.
                #
                # NOTHING BELOW MAY MENTION `seal.path` OR `plan`. That is not a style
                # rule: re-deriving the seal needs the PATH, and every sabotage that beat
                # the first round of checks did it by reaching for one -- including
                # `sha256(seal.path)`, using this module's own file hasher, three lines
                # from here. §5a asks the syntax tree for exactly that and nothing else in
                # this function violates it.
                **plan_manifest(seal),
                # The second witness, SPENT, and recorded as a value rather than printed.
                # `compare_plan_seals` reads only artifacts -- this capture's own
                # plan_seal.json (manifest.json does not exist yet, so the fallback fires
                # here on the live path) against marks.py's marks_meta -- and never the
                # plan file, which is what lets it sit after the launch at all. Three
                # valued like `origin.py`: UNCHECKED is "the operator did not mark", which
                # is legitimate and is not agreement.
                "plan_seals": seal_verdict, "plan_seals_why": seal_verdict_why,
                "exe_sha256_before": exe_sha_before, "exe_sha256_after": exe_sha_after,
                "exe_unchanged": bool(exe_sha_before and exe_sha_before == exe_sha_after),
                "args": accounts.redact_for_file(args), "ports": ports,
                "client_endpoints": sorted(endpoints),
                # Bind the artifact to the bytes it came from. Without these, deleting a
                # single record from wire.jsonl still reports 6/6 and silently yields a
                # shorter stream -- MEASURED by adversarial review 2026-08-07. A capture
                # that cannot detect its own truncation is not replayable evidence, it is
                # a file that happens to parse.
                "wire_sha256": sha256(wire),
                "wire_bytes": os.path.getsize(wire) if os.path.exists(wire) else 0,
                "keyring_sha256": sha256(os.path.join(outdir, "keyring.jsonl")),
                "pruned_records": pruned_records,
                "keys_tapped": len(keys), "report": report,
                "gw_log": open(log_path, encoding="utf-8", errors="replace").read().splitlines()
                          if os.path.exists(log_path) else []}
    with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    print(f"\n  {report['decrypted']}/{report['total']} connection(s) decrypted -> {outdir}")
    return 0 if report["decrypted"] else 1


def prune_wire(wire_path):
    """Drop every captured connection that carries no GW handshake. Returns (kept, dropped).

    Sniffing port 80 is what finally caught the live channels, and port 80 also carries
    whatever else the machine is doing. Those connections are not evidence of anything this
    project wants, they are the owner's own browsing, and they should not sit in the vault
    because a filter had to be wide enough to work.

    The test is the same one assemble_live uses -- does the c2s stream begin with a VERSION
    header we recognise -- so a GW connection is kept even when no key decrypts it. The raw
    bytes of a channel we could not open are still the only recording of a real session.
    """
    meta, conns = wc.load_connections(wire_path)
    keep = {k for k, e in conns.items() if channel_of_stream(e[wc.C2S])}
    if len(keep) == len(conns):
        return len(keep), 0
    tmp = wire_path + ".pruned"
    dropped = 0
    with open(wire_path, encoding="utf-8", errors="replace") as src, \
            open(tmp, "w", encoding="utf-8") as dst:
        for line in src:
            try:
                r = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue
            if r.get("kind") == "wire":
                if wc.conn_key(r) not in keep:
                    dropped += 1
                    continue
            dst.write(line if line.endswith("\n") else line + "\n")
    os.replace(tmp, wire_path)
    return len(keep), dropped


def sha256(path):
    """SHA-256 of a file, or None if it cannot be read."""
    import hashlib
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(block)
    except OSError:
        return None
    return h.hexdigest()


_STOPPING = threading.Event()


def _install_sigint():
    """First Ctrl-C asks the hold loop to stop; every later one is ABSORBED.

    Because the obvious thing happened: the first Ctrl-C was caught, cleanup began, and
    `close_client` sat in a silent 20-second `proc.wait` waiting for the game to shut down.
    With nothing on screen the operator pressed Ctrl-C twice more, the second one landed
    INSIDE that wait, and the process died before it assembled or wrote a manifest -- so a
    ten-minute live session produced no artifact at all. The keyring survived only because
    it is written per key.

    Cleanup and assembly must not be interruptible by an impatient second press. They are
    the part that turns a session into a capture.
    """
    import signal
    def handler(_signum, _frame):
        if _STOPPING.is_set():
            print("\n  ...already stopping. Closing the client and assembling -- this takes"
                  "\n     up to ~30s. Ctrl-C again will THROW AWAY the capture; the keys are"
                  "\n     already safe on disk either way.", flush=True)
            return
        _STOPPING.set()
        print("\n  stopping: closing the client cleanly (up to ~20s), then assembling."
              "\n  Please wait -- do not press Ctrl-C again.", flush=True)
    try:
        signal.signal(signal.SIGINT, handler)
    except (ValueError, OSError):
        pass          # not the main thread, or no console; the old behaviour still applies


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


def _take_mark(marks_fh, wire, n, label, at_wall=None, at_perf=None):
    """Write one operator mark, binding this instant to the capture's own clock.

    Reads the capture for its last segment `t` rather than sharing state with the
    sniffer, because the sniffer is a SUBPROCESS and there is no shared state to have.
    Cheap at human cadence: a mark is once per narration step, not once per packet.
    """
    if marks_fh is None:
        return
    wc.write_mark(marks_fh, n, label, wc.last_wire_t(wire),
                  at_wall=at_wall, at_perf=at_perf)


def _hold(client, ring, wire, minutes, cap=None, stop_file=None,
          marks_fh=None, mark_file=None):
    """Hold the session until the ceiling, the client exiting, or Ctrl-C.

    AND WATCH THE INSTRUMENTS, which this used to not do. A ten-minute live session
    reported `wire: 0 KiB` from the first tick to the last while nine keys were tapped,
    and nothing said why -- the sniff could have died, or been filtering a port the client
    was not using, and the status line looked the same either way. drive_client learned
    this in 2026-08-05 ("an instrument that was not yet running produces absence of
    evidence, never evidence of absence") and the live driver did not inherit it.

    So: sample the client's OWN connections and show what it is really talking to, notice
    a dead sniffer, and say something when bytes are not arriving instead of printing a
    zero forever. Returns the set of remote endpoints observed, for the manifest.
    """
    import tcptable
    ceiling = time.monotonic() + minutes * 60
    started = time.monotonic()
    seen, warned = set(), False
    # TWO ANCHORS EVEN IF THE OPERATOR NEVER MARKS. A session with zero marks is a
    # session nothing can bind, and the operator has a game to play; these cost nothing
    # and mean every capture is at least bracketed.
    marks = 1
    _take_mark(marks_fh, wire, marks, "session_start")
    while time.monotonic() < ceiling and not _STOPPING.is_set():
        if client.poll() is not None:
            print("\n  the client exited")
            break
        # A stop that does not depend on console focus. Ctrl-C only reaches Python when the
        # CONSOLE has focus, and the operator is by definition looking at the game window
        # -- so "Ctrl-C once to stop" is advice that fails exactly when it is needed. Any
        # shell, elevated or not, can now end the session:  echo. > <outdir>\STOP
        if stop_file and os.path.exists(stop_file):
            print("\n  STOP file seen -- ending the session")
            break
        # A NARRATION MARK, by the same file mechanism and for the same reason: the
        # operator is looking at the game window, so anything needing console focus is
        # advice that fails exactly when it is needed. `echo approach > <outdir>\MARK`
        # from any shell stamps this instant into marks.jsonl, and the file's contents
        # become the label. Deleted after reading so the next one is a fresh edge.
        if mark_file and os.path.exists(mark_file):
            label, at_wall, at_perf = "mark", None, None
            try:
                with open(mark_file, encoding="utf-8", errors="replace") as fh:
                    parts = fh.read().splitlines()
                label = (parts[0].strip() or "mark")
                # THE INSTANT THE OPERATOR ACTED, not the instant we noticed. This loop
                # polls every 5 s, so stamping at pickup is late by up to that much --
                # coarser than the binding is for. narrate() writes both clocks into the
                # file; a hand-written `echo label > MARK` has neither and falls back.
                if len(parts) >= 3:
                    at_wall, at_perf = float(parts[1]), float(parts[2])
            except (OSError, ValueError, IndexError):
                pass
            try:
                os.remove(mark_file)
            except OSError:
                pass
            marks += 1
            _take_mark(marks_fh, wire, marks, label,
                       at_wall=at_wall, at_perf=at_perf)
            print(f"\n  mark {marks}: {label}", flush=True)
        if cap is not None and cap.poll() is not None:
            print(f"\n  *** THE OFF-WIRE CAPTURE DIED (exit {cap.poll()}) -- nothing is "
                  f"being recorded.\n      See wirecapture.log. Keys are still being "
                  f"tapped and are safe on disk.", flush=True)
            cap = None                      # say it once, keep the session going
        try:
            for c in tcptable.connections(client.pid):
                if c["remote"] != "0.0.0.0:0":
                    seen.add(c["remote"])
        except Exception:
            pass
        left = int(ceiling - time.monotonic())
        size = os.path.getsize(wire) if os.path.exists(wire) else 0
        ports = sorted({int(r.rsplit(":", 1)[1]) for r in seen if ":" in r})
        print(f"\r  t-{left // 60:02d}:{left % 60:02d}  keys: {len(ring.values)}  "
              f"wire: {size / 1024:.0f} KiB  client ports: "
              f"{','.join(map(str, ports)) or 'none seen'}   ", end="", flush=True)
        # Bytes should arrive within seconds of the first handshake. If they have not
        # after a minute, the run is producing nothing and the operator should know while
        # there is still time to stop rather than at the end.
        if not warned and size < 1024 and time.monotonic() - started > 60:
            warned = True
            unmonitored = sorted(set(ports) - set(LIVE_PORTS))
            print(f"\n  *** NO WIRE BYTES after 60s, while {len(ring.values)} key(s) have "
                  f"been tapped.\n      Sniffing {sorted(LIVE_PORTS)} on IPv4. The client's "
                  f"own connections:\n      "
                  f"{', '.join(sorted(seen)) or 'NONE VISIBLE -- tcptable is IPv4-only, so '
                              'an IPv6 connection would look like this'}", flush=True)
            if unmonitored:
                # This is the whole diagnosis, so say it as one sentence rather than
                # leaving it to be read off two lists.
                print(f"      >>> THE CLIENT IS ON PORT(S) {unmonitored}, WHICH ARE NOT "
                      f"BEING SNIFFED. <<<\n      Add them to LIVE_PORTS and re-run; this "
                      f"capture will have no ciphertext.", flush=True)
            print("      Ctrl-C once to stop.", flush=True)
        _STOPPING.wait(5)
    else:
        if not _STOPPING.is_set():
            print("\n  session ceiling reached -- closing the client")
    _take_mark(marks_fh, wire, marks + 1, "session_end")
    return seen


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--assemble", default=None, metavar="DIR",
                    help="re-assemble an existing capture directory from its own "
                         "wire.jsonl + keyring.jsonl and exit. No client, no network, no "
                         "account -- this is the offline half, and it is why the keyring "
                         "is persisted")
    ap.add_argument("--account", default=None, help="automation-flagged label in accounts.json")
    ap.add_argument("--exe", default=None, help="the stock-DH, key-tapped live build")
    # --host is accepted only to REFUSE it by name. RUNBOOK documented `--host <auth ip>`
    # as the live command for a day, and an operator working from a printed or remembered
    # copy of that line would otherwise get an argparse error that reads like a typo. What
    # it actually asked for is the one setting that quietly ruins the run -- see the
    # comment on the wirecapture launch in run().
    ap.add_argument("--host", default=None, help=argparse.SUPPRESS)
    ap.add_argument("--ports", default=",".join(map(str, LIVE_PORTS)))
    ap.add_argument("--minutes", type=int, default=10,
                    help="session-length CEILING, not a duration -- Ctrl-C ends the run at "
                         "any point and still assembles and scrubs in full (default: 10)")
    ap.add_argument("--confirm", action="store_true", help="required for a real live run")
    # OPTIONAL, unlike --mode, and the module header argues why at length: a missing mode
    # poisons every number in the capture forever, a missing plan only leaves it
    # unlabelled. So this one is VISIBLE-when-absent rather than refused (D9(a)'s shape),
    # and the manifest says so in a key rather than by omitting one.
    ap.add_argument("--plan", default=None, metavar="PATH",
                    help="the PRE-REGISTERED operator-mark plan (kind<TAB>text per line) "
                         "that marks.py will read in a second shell. Hashed BEFORE the "
                         "client launches and the hash written to manifest.json; without "
                         "it the run is unlabelled and says so loudly")
    # No `default=`, and `choices` rather than a free string. argparse's own error is the
    # first refusal an operator meets; run()'s longer one explains why. Both exist because
    # a default here would be silently wrong on every run that did not think about it,
    # which is the entire failure this flag prevents.
    ap.add_argument("--mode", default=None, choices=GAME_MODES,
                    help="REQUIRED: the account's game mode, base or reforged. Reforged "
                         "changes enemy health and armour ~20%% and is UNRECOVERABLE "
                         "afterwards -- an unstamped capture's stats can never be graded")
    a = ap.parse_args()
    if a.assemble:
        return reassemble(a.assemble)
    if not a.account:
        raise LiveError("--account is required for a live run (or use --assemble DIR)")
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
    return run(a.account, a.exe, drive_client_default(), ports, a.minutes, a.confirm,
               mode=a.mode, plan=a.plan)


def reassemble(outdir):
    """Re-run the offline half over a capture directory that already exists.

    The point of persisting the keyring: a capture is a THING ON DISK that can be decoded
    again -- after a framing fix, after a new opcode is understood, months later -- without
    a second live session. R0b's criterion says "byte-replayable from disk" and this is the
    function that makes that true rather than aspirational.
    """
    wire = os.path.join(outdir, "wire.jsonl")
    kr = os.path.join(outdir, "keyring.jsonl")
    if not os.path.isfile(wire):
        raise LiveError(f"no wire.jsonl in {outdir}")
    if not os.path.isfile(kr):
        raise LiveError(
            f"no keyring.jsonl in {outdir}.\n"
            f"  Captures written before 2026-08-07 held their keys in memory only, and\n"
            f"  whatever did not decrypt at the time cannot be decrypted now -- the key\n"
            f"  derives from ArenaNet's private exponent. The wire bytes are still there\n"
            f"  and still worth keeping; they just have no key.")
    keys = load_keyring(kr)
    print(f"re-assembling {outdir}\n  keyring: {len(keys)} key(s)")
    # The second witness, RECOMPUTED here and written back. A report and never a refusal:
    # a disagreement is a fact about the labels, not about the ciphertext, and refusing to
    # decode a real live capture over it would destroy the more valuable half to protect
    # the cheaper one.
    #
    # Recomputed rather than read, because this is the one place the answer can CHANGE
    # after the run: `run()` records it at manifest time, and a marker started late, a
    # plan_marks.jsonl copied in afterwards, or a capture assembled months later all move
    # it. Written back for the reason the whole comparison moved out of `reassemble()` in
    # the first place -- until 2026-08-13 this function only PRINTED the verdict, so the
    # single comparison this pair of tools makes possible lived in console scrollback and
    # reached no artifact at all.
    verdict, why = compare_plan_seals(outdir)
    print(f"  plan seal: {verdict.upper()} -- {why}")
    update_manifest(outdir, {"plan_seals": verdict, "plan_seals_why": why})
    report = assemble_live(wire, keys, outdir)
    for row in report["connections"]:
        if row.get("decrypted"):
            print(f"  [ok] {row['connection']}  {row['channel']}  "
                  f"c2s {row['c2s_bytes']}B / s2c {row['s2c_bytes']}B  ({row['key_from']})")
        else:
            print(f"  [--] {row['connection']}  {row.get('why', 'undecrypted')}")
    print(f"\n  {report['decrypted']}/{report['total']} connection(s) decrypted")
    return 0 if report["decrypted"] else 1


def update_manifest(outdir, fields):
    """Merge `fields` into an existing manifest.json. Returns True if it was rewritten.

    NARROW ON PURPOSE, because this is the only code in the project that edits the primary
    artifact of a run that cannot be repeated. It refuses to CREATE a manifest (a capture
    with none is a run that died before assembly, and `plan_seal.json` is that run's record
    -- inventing a manifest here would fabricate one), it refuses anything that does not
    already parse as a JSON object rather than truncating it, and it writes through a
    temporary file in the same directory plus `os.replace`, so a crash mid-write leaves the
    original whole. Every key it does not name survives untouched, which the test asserts
    field-for-field rather than trusting the `update` call.
    """
    path = os.path.join(outdir, "manifest.json")
    if not os.path.isfile(path):
        return False
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            rec = json.load(fh)
    except (OSError, ValueError):
        return False
    if not isinstance(rec, dict):
        return False
    rec.update(fields)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=1)
    os.replace(tmp, path)
    return True


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
