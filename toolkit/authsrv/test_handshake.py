"""Prove the Stage B handshake works, end to end, without the game client.

This is a calibration test, in the sense HANDOFF.md §8 means it: an instrument
that cannot reproduce the lifecycle cannot falsify a bug in it. So the test client
here does not use the key file's parameters directly. It reads (g, p, B) **out of
the patched executable**, exactly as the real client does, and only the server
side is allowed to know the private exponent.

That makes the whole chain load-bearing:

    make_custom_client.py  ->  patched Gw.exe  ->  this client reads (g,p,B)
                                                        |
    vault/keys/*.json  ->  authsrv.py  ->  server holds b
                                                        |
                            both must derive the same ARC4 key

If the patcher wrote to the wrong offsets, if endianness is flipped anywhere, or
if arc4_hash is subtly wrong, the derived keys differ and the final check fails.
A green result here means the real client should key up too.
"""

import json
import os
import re
import socket
import struct
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from gwcrypto import ARC4, arc4_hash, recover_master_secret  # noqa: E402
from gwpe import PE  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'schema'))
from codec import Codec  # noqa: E402
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "portal"))
from sessionstore import SessionStore, uuid_to_wire  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

SELFTEST_VAULT = r"C:\gd\Rurik\vault\captures\selftest"
SELFTEST_SESSIONS = r"C:\gd\Rurik\vault\state\selftest-sessions.json"

codec = Codec()

SIG_KEYS = bytes.fromhex("8B4508C70088000000B8")
PORT = 6112
BUILD = 38797

# Reuses the real UUIDs observed on the wire, so the encoding stays exercised.
TEST_EMAIL = "selftest@rurik.local"
TEST_USER_ID = "E696B44C-04FC-DF92-9EE1-B0CC329B424A"
TEST_TOKEN = "233B382E-3CD2-E5B6-7018-7F547D2760A7"


def read_client_params(exe):
    """Read (g, p, B) from a client binary the way the client itself would."""
    pe = PE(exe)
    hits = pe.find(SIG_KEYS, ".text")
    if not hits:
        raise SystemExit(f"{exe}: DH accessor signature not found")
    va = struct.unpack_from("<I", pe.data, hits[0] + 0x0A)[0]
    off = pe.rva_to_off(va - pe.image_base)
    g = int.from_bytes(pe.data[off + 4:off + 8], "little")
    p = int.from_bytes(pe.data[off + 8:off + 72], "little")
    B = int.from_bytes(pe.data[off + 72:off + 136], "little")
    return g, p, B


def server_keys():
    """The key file `authsrv.py` will load, chosen the way it chooses it.

    Mirrors `authsrv.load_keys(None)` rather than importing it, because importing
    the server to ask it a question starts a server. If the two ever diverge the
    final check in section 5 still catches it: that one compares the key both ends
    actually derived, and it cannot be satisfied by agreeing about the wrong file.
    """
    kd = vaultpath.require_dir("keys", why="the DH parameters both ends must share")
    cands = sorted(f for f in os.listdir(kd) if f.startswith("rurik_dh_"))
    if not cands:
        raise SystemExit("no rurik_dh_*.json in vault/keys — "
                         "run toolkit/clientpatch/make_custom_client.py first")
    return json.load(open(os.path.join(kd, cands[-1]), encoding="utf-8"))


def pick_our_client(patched_dir, keys):
    """The patched client keyed to OUR server. Anything else stops the run.

    WHY THIS IS NOT A FILENAME SORT, which is what it was until 2026-08-06.
    `sorted(exes)[-1]` picks by spelling, and `vault/client-patched/` is shared by
    every worktree on this machine -- `vaultpath` resolves to the main working
    tree, so a branch has code of its own but never a vault of its own. The moment
    A1's unpatched-DH build landed beside ours as `Gw.live.*`, "live" sorted after
    "custom", and this test read ArenaNet's modulus out of it, derived a key our
    server could never match, and printed four unrelated FAILs and two mismatched
    hex strings. That reads exactly like a handshake regression in our own code.
    It was not: it was the wrong binary, and the test had no way to say so.

    So the choice is made on the property that has to hold anyway -- the exe's
    prime and server public value are the ones in the key file authsrv will load.
    `g` is deliberately not part of it: generator 4 is ArenaNet's too, so every
    candidate on this machine agrees on it and it discriminates nothing.

    This will keep mattering. A1's first commit is an unpatched-DH build, so that
    directory is expected to hold a client this test must refuse.
    """
    cands = sorted(f for f in os.listdir(patched_dir) if f.endswith(".exe"))
    if not cands:
        raise SystemExit("no patched client in vault/client-patched — "
                         "run toolkit/clientpatch/make_custom_client.py")

    ours, rejected = [], []
    for name in cands:
        try:
            g, p, B = read_client_params(os.path.join(patched_dir, name))
        except SystemExit as exc:
            rejected.append((name, f"no DH accessor signature ({exc})"))
            continue
        if p == keys["prime"] and B == keys["server_public"]:
            ours.append(name)
        else:
            which = []
            if p != keys["prime"]:
                which.append("prime")
            if B != keys["server_public"]:
                which.append("server public value")
            rejected.append((name, "carries a DH " + " and ".join(which) +
                             " that is not ours — an unpatched-DH build keys to "
                             "ArenaNet, and this server cannot read it"))

    for name, why in rejected:
        print(f"  skipped      : {name}\n                 {why}")
    if not ours:
        raise SystemExit(
            f"\nno client in {patched_dir} is keyed to our server.\n"
            f"  {len(cands)} candidate(s) read, none matching "
            f"vault/keys/rurik_dh_*.json.\n"
            f"  Re-run toolkit/clientpatch/make_custom_client.py, which writes the\n"
            f"  exe and the key file as a pair. NOTHING WAS TESTED.")
    return os.path.join(patched_dir, ours[-1])


# The floor is what a completed handshake session executes. MEASURED 2026-08-06:
# a green run spawns its authsrv on 6112, completes the lifecycle and prints 17.
# 16 of those are mandatory; the 17th is the unpatched-client negative control,
# which declares a skip when the vault holds no stock build with different
# parameters. So the floor is 16.
#
# It was 13 until that run -- the core minus a deliberate margin, because the
# agent that added the ledger could not start a server and would not guess high.
# The margin is what the comment asked to have removed once someone had a real
# total, and 13 was three checks of slack in the test that proves the whole
# channel: a run that lost the entire login burst would still have cleared it.
LEDGER = checks.Ledger("handshake", floor=16)
check = checks.adopt_named(LEDGER)


def main():
    patched_dir = r"C:\gd\Rurik\vault\client-patched"
    exe = pick_our_client(patched_dir, server_keys())
    print(f"patched client : {os.path.basename(exe)}")

    g, p, B = read_client_params(exe)
    print(f"read from exe  : g={g}, prime {p.bit_length()} bits, B {B.bit_length()} bits")

    # Keep the self-test's output out of the ground-truth vault. These used to
    # share vault/captures/authsrv/ and vault/state/sessions.json with real
    # client sessions: the files were indistinguishable in a listing, and a test
    # run overwrote the live token record. That mixing produced a false timeline
    # during a real debugging session — two self-test captures were read as
    # evidence of successful client logins that never happened.
    # Is the port already taken? This has to be checked BEFORE spawning, and it
    # is not cosmetic. If another authsrv is already listening, our subprocess
    # fails to bind and dies -- but the connect below then SUCCEEDS against the
    # other server, so the whole run silently measures the wrong process. What
    # that looks like from the output is three unrelated FAILs and an empty
    # server key, which reads exactly like a real handshake regression. It cost
    # two debugging detours in one session before anyone read the last line of
    # the server log.
    probe = socket.socket()
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 0)
    try:
        probe.bind(("127.0.0.1", PORT))
    except OSError:
        probe.close()
        print(f"\n[BLOCKED] 127.0.0.1:{PORT} is already in use.\n"
              f"  Something else -- almost certainly an authsrv you are running\n"
              f"  for a client session -- holds the port. This test starts its\n"
              f"  own server, so it cannot run alongside one, and if it tried it\n"
              f"  would connect to yours and report nonsense about it.\n"
              f"\n"
              f"  Find it:  netstat -ano | findstr :{PORT}\n"
              f"  Then stop it and re-run. NOTHING WAS TESTED.")
        return 2
    probe.close()

    srv = subprocess.Popen([sys.executable, "toolkit/authsrv/authsrv.py", "--once",
                            "--vault", SELFTEST_VAULT,
                            "--sessions", SELFTEST_SESSIONS],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    ok = True
    try:
        for _ in range(60):
            try:
                s = socket.create_connection(("127.0.0.1", PORT), timeout=0.3)
                break
            except OSError:
                time.sleep(0.1)
        else:
            print("authsrv never came up")
            return 1

        # ---- client side of the handshake -------------------------------
        print("\n1. version")
        s.sendall(struct.pack("<4I", 0x000C0400, BUILD, 1, g))

        print("2. client seed")
        import secrets
        a_priv = secrets.randbits(512) % (p - 2) + 1
        A = pow(g, a_priv, p)
        s.sendall(struct.pack("<H", 0x4200) + A.to_bytes(64, "little"))

        print("3. server seed")
        s.settimeout(10)
        resp = b""
        while len(resp) < 22:
            chunk = s.recv(22 - len(resp))
            if not chunk:
                break
            resp += chunk
        ok &= check("server replied 22 bytes", len(resp) == 22, f"{len(resp)}")
        if len(resp) < 22:
            return 1
        hdr = struct.unpack("<H", resp[:2])[0]
        ok &= check("header is 0x1601", hdr == 0x1601, hex(hdr))

        # ---- derive, exactly as the client does -------------------------
        shared = pow(B, a_priv, p).to_bytes(64, "little")
        master = recover_master_secret(resp[2:], shared)
        derived = arc4_hash(master)
        print(f"   client-derived ARC4 key: {derived.hex()[:16]}…")

        print("\n4. speak real protocol and require the right answer back")
        # The same two messages the real client sends, built through our own
        # codec, so this exercises encode, decrypt, decode and dispatch together.
        c2s = ARC4(derived)
        s2c = ARC4(derived)
        info = codec.encode("AUTH_CMSG", 0x0001, ["selftest", "SELFTESTPC"],
                            header_value=0x8001)
        hsh = codec.encode("AUTH_CMSG", 0x0002, [BUILD, bytes(range(16))],
                           header_value=0x8002)
        # Deliberately sent as ONE write containing TWO messages, and then split
        # across writes below, because the real client does both and a decoder
        # that assumes one-message-per-read works right up until it doesn't.
        s.sendall(c2s.crypt(info + hsh))

        s.settimeout(10)
        reply = b""
        try:
            while len(reply) < 10:
                chunk = s.recv(4096)
                if not chunk:
                    break
                reply += chunk
        except socket.timeout:
            pass
        ok &= check("server answered SEND_COMPUTER_HASH", len(reply) >= 10,
                    f"{len(reply)} bytes")
        if len(reply) >= 10:
            msgs, consumed, err = codec.decode_stream("AUTH_SMSG", s2c.crypt(reply))
            ok &= check("reply decodes cleanly", err is None and consumed == len(reply),
                        err or f"consumed {consumed}/{len(reply)}")
            ok &= check("reply is AUTH_SMSG_SESSION_INFO (0x0001)",
                        bool(msgs) and msgs[0][0] == 0x0001,
                        f"0x{msgs[0][0]:04x}" if msgs else "none")
            if msgs:
                print(f"   session salt: 0x{msgs[0][1][1]:08x}")

        print("\n5. log in and require the character-select burst")
        # Issue a session exactly as the portal would, so AuthSrv can validate it.
        store = SessionStore(SELFTEST_SESSIONS)
        store.issue(TEST_EMAIL, TEST_USER_ID, TEST_TOKEN)
        login = codec.encode("AUTH_CMSG", 0x0038, [
            1,                                    # req_id
            uuid_to_wire(TEST_USER_ID),
            uuid_to_wire(TEST_TOKEN),
            "", "Portal",
        ], header_value=0x8038)
        s.sendall(c2s.crypt(login))

        s.settimeout(10)
        burst = b""
        deadline = time.time() + 8
        while time.time() < deadline:
            try:
                chunk = s.recv(65536)
            except socket.timeout:
                break
            if not chunk:
                break
            burst += chunk
            if len(burst) > 150:      # the whole burst is ~200 bytes
                time.sleep(0.3)
                s.setblocking(False)
                try:
                    burst += s.recv(65536)
                except (BlockingIOError, OSError):
                    pass
                s.setblocking(True)
                break
        ok &= check("server sent a login burst", len(burst) > 0, f"{len(burst)} bytes")
        if burst:
            msgs, consumed, err = codec.decode_stream("AUTH_SMSG", s2c.crypt(burst))
            got = [m[0] for m in msgs]
            names = {0x0007: "CHARACTER_INFO", 0x0016: "ACCOUNT_SETTINGS",
                     0x0014: "FRIEND_STREAM_END", 0x0011: "ACCOUNT_INFO",
                     0x0003: "REQUEST_RESPONSE"}
            print("   " + " -> ".join(names.get(o, f"0x{o:04x}") for o in got))
            ok &= check("burst decodes cleanly", err is None and consumed == len(burst),
                        err or f"consumed {consumed}/{len(burst)}")
            ok &= check("contains a CHARACTER_INFO", 0x0007 in got)
            ok &= check("contains ACCOUNT_INFO", 0x0011 in got)
            ok &= check("REQUEST_RESPONSE is LAST", got and got[-1] == 0x0003,
                        f"last is 0x{got[-1]:04x}" if got else "empty")
            ok &= check("every CHARACTER_INFO precedes REQUEST_RESPONSE",
                        all(i < got.index(0x0003) for i, o in enumerate(got)
                            if o == 0x0007) if 0x0003 in got else False)
            # NOT `resp` — that name holds the 22-byte server seed from step 3 and
            # the negative control still needs it.
            rr = [m for m in msgs if m[0] == 0x0003]
            ok &= check("REQUEST_RESPONSE reports success (status 0)",
                        bool(rr) and rr[-1][1][2] == 0,
                        f"status {rr[-1][1][2]}" if rr else "absent")
            ch = [m for m in msgs if m[0] == 0x0007]
            if ch:
                ok &= check("character is named", ch[0][1][4] == "Test Warrior",
                            repr(ch[0][1][4]))
        s.close()

        out, _ = srv.communicate(timeout=20)
        srv_key = ""
        for line in out.splitlines():
            if "ARC4 key" in line:
                # The server ends this line with a Unicode ellipsis, and what
                # that glyph arrives as depends on the codepage the pipe was
                # decoded with -- under cp1252 it is three mojibake characters
                # that rstrip("…") cannot see, and the comparison below then
                # fails on display garbage rather than on the key. Keep the
                # leading hex run and nothing else.
                m = re.match(r"[0-9a-f]+", line.split("ARC4 key")[1].strip())
                srv_key = m.group(0) if m else ""
        ok &= check("server completed key exchange", "key exchange OK" in out)
        ok &= check("server and client derived the SAME key",
                    bool(srv_key) and derived.hex().startswith(srv_key),
                    f"server {srv_key} vs client {derived.hex()[:16]}")
        ok &= check("server framed BOTH messages out of one TCP read",
                    "SEND_COMPUTER_INFO" in out and "SEND_COMPUTER_HASH" in out)

        # ---- negative control -------------------------------------------
        # A test that only ever goes green proves nothing. An UNPATCHED client
        # keys against ArenaNet's compiled-in B, so its shared secret — and
        # therefore its ARC4 key — must NOT match ours. If this comes out equal,
        # the test is measuring something other than what it claims to.
        print("\n5. negative control: an unpatched client must NOT match")
        stock = None
        cdir = r"C:\gd\Rurik\vault\client"
        for build in sorted(os.listdir(cdir), reverse=True):
            cand = os.path.join(cdir, build, "Gw.exe")
            if os.path.exists(cand):
                try:
                    sg, sp, sB = read_client_params(cand)
                except SystemExit:
                    continue
                if sB != B:
                    stock = (build, sg, sp, sB)
                    break
        if stock is None:
            LEDGER.skip("negative control",
                        "no unpatched client with different parameters in the vault")
        else:
            build, sg, sp, sB = stock
            stock_shared = pow(sB, a_priv, sp).to_bytes(64, "little")
            stock_key = arc4_hash(recover_master_secret(resp[2:], stock_shared))
            ok &= check("stock client derives a DIFFERENT key",
                        stock_key != derived,
                        f"stock {stock_key.hex()[:16]} vs patched {derived.hex()[:16]}")
            print(f"         (control build: {build})")

        print("\n--- server log ---")
        for line in out.splitlines():
            if line.strip():
                print("   ", line)
        # The ledger owns the banner now: a session that fell short of its floor
        # did not verify the handshake, however green each printed line looked.
        code = LEDGER.verdict()
        if code == 0:
            print("HANDSHAKE VERIFIED — the real client should key up too")
        return code
    finally:
        if srv.poll() is None:
            srv.kill()


if __name__ == "__main__":
    sys.exit(main())
