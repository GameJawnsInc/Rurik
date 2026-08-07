"""Drive one authorized live-capture session, and turn its wire bytes into an artifact.

    python toolkit/harness/livesession.py --account capture --confirm    # the live run

This is the R0b driver: it ties together the parts each proven on their own -- the launch
gate (`cage.assert_launch_safe`, stock->live), the account selector (`accounts.for_automation`,
refuses the primary), the key-tap (`keytap.py` reads what the code cave stashed), the
off-wire capture (`wirecapture.py`), the decryptor (`replay.py`/`gwcrypto`), the origin
stamp (`origin.py`), and the scrub (`scrub_captures.py`). It launches the stock-DH live
client at the real service, sniffs the ciphertext, reads the session key out of the client,
and assembles a decrypted capture stamped `origin: live` and byte-replayable from disk.

TWO HALVES, and only one is testable without a live account:

  * ASSEMBLE (offline, pure) -- reassembled wire streams + the tapped key -> a decrypted
    capture. The DH handshake is plaintext on the wire (ARC4 starts only after the key is
    derived), so this splits VERSION/CLIENT_SEED/SERVER_SEED off the front of each
    direction and decrypts the rest. Verified against real captured bytes in
    test_livesession.py.
  * RUN (live) -- launch, sniff, read the key, stop. Needs WinDivert, an elevated shell,
    and the secondary account, and it never runs except behind --confirm. It is the
    human-driven step PLAN.md §6.2 describes; the code here refuses to start it any other
    way.

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
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientpatch"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
import accounts  # noqa: E402
import origin  # noqa: E402
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


def run(account_label, exe, live_host, live_ports, minutes, confirm):
    """The live orchestration. Refuses without --confirm; needs WinDivert and the account.

    Structured, not yet exercised end to end -- the live launch and the sniff are the
    elevated, human-driven step. The offline half it feeds (assemble) is what the tests
    cover.
    """
    if not confirm:
        raise LiveError("a live run points a client at ArenaNet's real service. Re-run with "
                        "--confirm once you have read PLAN §6.2 and are at the keyboard: "
                        "human cadence, human hours, one client, never competitive.")
    plan = preflight(account_label, exe, live_host)
    ceiling = time.monotonic() + minutes * 60
    # From here: launch the client (drive_client, redacted argv), start wirecapture on its
    # pid + live_host, poll keytap until the slot is non-zero (the cave ran => key ready),
    # read the key, hold to the ceiling under operator control, stop, then assemble+scrub.
    # Each of those calls a part proven elsewhere; the sequencing is the only new logic and
    # it cannot be exercised without a live account, so it is left to the guided run.
    raise LiveError("live orchestration is staged but not wired to launch in this build -- "
                    f"preflight passed for {plan['account']} against {live_host}. The launch "
                    f"step is the guided one; see studies/livekey/ for the sequence.")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--account", required=True, help="automation-flagged label in accounts.json")
    ap.add_argument("--exe", default=None, help="the stock-DH, key-tapped live build")
    ap.add_argument("--host", default=None, help="live auth server ip (resolved only on a real run)")
    ap.add_argument("--ports", default="6112,6601")
    ap.add_argument("--minutes", type=int, default=20, help="session-length ceiling")
    ap.add_argument("--confirm", action="store_true", help="required for a real live run")
    a = ap.parse_args()
    if not a.exe or not a.host:
        raise LiveError("a live run needs --exe (the run-live build) and --host explicitly; "
                        "nothing here resolves an ArenaNet address on its own.")
    ports = {int(p) for p in a.ports.split(",") if p.strip()}
    run(a.account, a.exe, a.host, ports, a.minutes, a.confirm)
    return 0


if __name__ == "__main__":
    sys.exit(main())
