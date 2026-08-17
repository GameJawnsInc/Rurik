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

WHICH executable, and why that is asked of the bytes. This used to take
`sorted(exes)[-1]` out of `vault/client-patched/`. On 2026-08-06 a live-capture
build -- ArenaNet's stock DH, correct and wanted, PLAN.md §6.2 item 1 -- was
written into that directory as `Gw.live.<tag>.exe`, and `l` sorts after `c`. The
test silently switched to a binary that keys against ArenaNet and reported four
failures and a short check count, every one of which reads as a crypto
regression in code that had not been touched.

That directory is shared by every worktree on this machine -- `vaultpath`
resolves to the main working tree, so a branch has code of its own but never a
vault of its own -- which is why no amount of care on one branch could have
prevented it, and why the fix has to be in what the code asks rather than in
what anyone remembers. Selection goes through `clientpatch/dhbuild.py`: it reads
the DH struct and requires the exe's prime and server public value to be the
ones in the key file `authsrv` will load. `g` is deliberately not compared --
generator 4 is ArenaNet's too, so every candidate agrees on it and it
discriminates nothing. Candidates that are passed over are named and so is the
reason. A wrong or missing artifact is refused BEFORE the server is spawned,
with a message that says ARTIFACT rather than leaving four key-mismatch FAILs to
be misread.

The DH math below still reads (g, p, B) out of the executable, not out of the
key file. Selection proves the two agree; the handshake still has to derive from
what the binary actually carries, or the chain above stops being load-bearing.
"""

import json
import os
import re
import socket
import struct
import subprocess
import sys
import time
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clientpatch"))
from gwcrypto import ARC4, arc4_hash, recover_master_secret  # noqa: E402
import dhbuild  # noqa: E402
import vaultpath  # noqa: E402
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'clientscan'))
import buildid  # noqa: E402
import pinned  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'schema'))
from codec import Codec  # noqa: E402
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "portal"))
from sessionstore import SessionStore, uuid_to_wire  # noqa: E402
import checks  # noqa: E402

SELFTEST_VAULT = r"C:\gd\Rurik\vault\captures\selftest"
SELFTEST_SESSIONS = r"C:\gd\Rurik\vault\state\selftest-sessions.json"

codec = Codec()

PORT = 6112

# The build this synthetic client ANNOUNCES in its version frame. It is derived
# from the exe whose DH parameters the client is about to use, never typed in.
#
# WHY, and it is a defect this file carried from 2026-08-06 to 2026-08-14. This
# was `BUILD = 38797`, a constant, while the exe came from `dhbuild.select(...
# match=server_keys())` -- "whichever build the newest key file belongs to". The
# two were independent, so the moment a second build was patched (38833, on
# 2026-08-14) the test drove a 38833 client while announcing 38797: a client
# claiming a build it is not. Nothing noticed, because nothing on either side
# read the announced build.
#
# `authsrv` now DOES read it -- it binds the DH key to the announced build, so
# that a session running one build against another build's key is refused by
# name instead of dying as `Code=058` (studies/crossbuild/FINDINGS.md §7.7). That
# turned this latent inconsistency into an aborted connection, which is the guard
# working on the first thing it was pointed at. Derived below, after the exe is
# chosen, so the two can never drift apart again.
BUILD = None

# Reuses the real UUIDs observed on the wire, so the encoding stays exercised.
TEST_EMAIL = "selftest@rurik.local"
TEST_USER_ID = "E696B44C-04FC-DF92-9EE1-B0CC329B424A"
TEST_TOKEN = "233B382E-3CD2-E5B6-7018-7F547D2760A7"


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


def _build_of_keyfile(keys):
    """The client build a `rurik_dh_*.json` was cut for, via pinned.BUILDS."""
    for b in pinned.BUILDS:
        if b.stamp == keys.get("build_tag"):
            return b.number
    return None


def drain_server(srv, timeout=20):
    """The server's log as a string, plus a reason it is short. Never None.

    WHY THIS IS A FUNCTION and not the `srv.communicate(timeout=20)[0]` it was
    until 2026-08-17, when it crashed the run with

        AttributeError: 'NoneType' object has no attribute 'splitlines'

    after a green handshake -- every check through CHARACTER_INFO had passed, and
    the traceback landed before `LEDGER.verdict()`, so the suite's most important
    test reported NOTHING. Not a FAIL: nothing. No banner, no count, no name.

    `communicate()` on a `stdout=PIPE` child is assumed by every reader to hand
    back the stream, and it can instead hand back **None, silently, with
    returncode 0**. CPython's Windows implementation reads the pipe on a helper
    thread -- `Lib/subprocess.py:_readerthread`, `buffer.append(fh.read())` -- and
    if that read raises, the thread dies, the buffer stays empty, and the
    collector's last line is `stdout = stdout[0] if stdout else None`. An empty
    list is falsy, so the failure is laundered into None instead of propagating.
    The thread's own traceback goes to stderr ahead of ours, where it reads as
    noise out of the server rather than as the parent having lost the log.

    The read that raises is a DECODE. `text=True` decodes with the PARENT's locale
    codec (cp1252 on this machine) and errors='strict', while the child encodes
    with whatever its own stdout is set to -- so an environment carrying
    PYTHONIOENCODING=utf-8 has authsrv writing UTF-8 into a cp1252 decoder. Most
    of what it prints survives that as mojibake, which is what the ARC4-key regex
    below has always been working around; but cp1252 leaves five bytes UNDEFINED
    -- 0x81 0x8D 0x8F 0x90 0x9D -- and any one of them raises instead. A single
    such byte anywhere in the log loses the whole log.

    That is now fixed at the source: the Popen pins the codec at BOTH ends, so the
    decode cannot raise. This function is the belt to that braces, and it earns
    its keep on the one failure the pinning does not cover -- a `--once` server
    that never exits. Either way the caller gets a string and a reason, so a
    teardown problem is a named FAIL under the banner rather than a traceback
    thrown before the banner exists.

    `checks.py`'s own docstring closes on the mirror image of this bug: a test
    killed by printing the bytes it read. This one was killed READING them.
    """
    try:
        out, _ = srv.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # The `--once` server should exit after one connection. If it has not,
        # the log so far is still worth having -- kill it and take what it wrote.
        srv.kill()
        try:
            out, _ = srv.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            out = ""
        return out or "", (f"the --once server had not exited {timeout}s after the "
                           f"session ended; killed it and read what it had written")
    if out is None:
        return "", ("the server's stdout pipe decoded to None -- subprocess's "
                    "reader thread raised while reading it (its traceback is "
                    "above, ahead of this line) and the log is unrecoverable")
    return out, ""


# The floor is what a completed handshake session executes. MEASURED 2026-08-06:
# a green run spawns its authsrv on 6112, completes the lifecycle and prints 17,
# which is every check() site in the file. 16 of those are mandatory; the 17th is
# the unpatched-client negative control, which declares a skip when the vault holds
# no stock build with different parameters. So the floor is 16, the mandatory core.
#
# It was 13 until that run -- the core minus a deliberate margin, because the
# agent that added the ledger could not start a server and would not guess high.
# The margin is what the comment asked to have removed once someone had a real
# total, and it cost more than it bought twice over. 13 was three checks of slack
# in the test that proves the whole channel: a run that lost the entire login burst
# would still have cleared it. And when the wrong artifact WAS selected, the banner
# read "ONLY 8 OF A DECLARED FLOOR OF 13", understating the damage -- eight of the
# SIXTEEN mandatory checks had not run.
# 16 -> 17 on 2026-08-14: the mandatory core gained the check that the exe's
# build matches the key file the server will load. A green run now prints 18
# (17 mandatory + the negative control).
# 17 -> 21 on 2026-08-17: section 0's four vault-free checks, the regression
# guard for the game channel's missing key binding. They need no server and no
# vault, so they are mandatory on any machine -- see section_key_binding().
# 21 -> 22 on 2026-08-17, MEASURED against a green run that printed 23 (22
# mandatory + the negative control): teardown now asserts that the server's log
# was actually captured. That is a real check and not a formality -- the run it
# was written for reached this point with every earlier check green and then
# died, and the three checks after it read `out`, so before it existed a lost
# log could only surface as a traceback or as three FAILs blaming the server.
#
# Note what the count did NOT do here. The swapped-argument check below (the
# exe/key-file build match) was counted in the 21 while asserting nothing, so
# 21 was never 21 real checks; fixing it changed the count by zero and the floor
# by zero, which is exactly why a floor cannot be the only guard. It counts
# checks, and it cannot tell a check from a check-shaped no-op.
LEDGER = checks.Ledger("handshake", floor=22)
check = checks.adopt_named(LEDGER)


def section_key_binding(check):
    """The key must bind to the ANNOUNCED build on BOTH channels.

    This section is vault-free on purpose: it is the regression guard for
    2026-08-17, when a 38797 client was handed 38833's key on the GAME
    channel because the 2026-08-14 fix lived inline in the AUTH branch and
    the game branch never got it. The handshake completed, the ARC4 stream
    was noise, and the client dropped with Code=007 and no assert -- a
    symptom that named nothing and cost two client runs to attribute.

    The last check is the one that matters: it asserts the STRUCTURE that
    was wrong, not just the behaviour of the helper. A future edit that
    tucks the call back inside one channel's branch turns it red.
    """
    print("\n== 0. the DH key binds to the announced build (no vault) ==")
    import ast
    import authsrv

    class _Rec:
        def __init__(self):
            self.events = []

        def event(self, name, **kw):
            self.events.append((name, kw))

    # REAL stamps from pinned.BUILDS, not invented ones: the refusal arm
    # only fires when the loaded key belongs to a KNOWN different build, so
    # a fixture with made-up tags cannot reach it. The first version of this
    # section used fake tags, and the refusal check failed for that reason
    # -- the check catching its own fixture, which is what a check that can
    # fail is for.
    A = {"build_tag": pinned.BUILDS[1].stamp, "generator": 4}   # 38797
    B = {"build_tag": pinned.BUILDS[2].stamp, "generator": 4}   # 38833
    saved = authsrv.KEYS_BY_BUILD
    try:
        authsrv.KEYS_BY_BUILD = {38797: A, 38833: B}
        # loaded the newest (B) and a 38797 client speaks: must swap to A.
        rec = _Rec()
        got, ok = authsrv.bind_key_to_build(B, 38797, 1, rec)
        check("a 38797 client on a server holding 38833's key RE-SELECTS "
              "-- the exact case that produced Code=007 on the game channel",
              ok and got is A and rec.events
              and rec.events[0][0] == "keys_reselected",
              f"got {got.get('build_tag')}")
        # already correct: no swap, and no log line claiming one.
        rec = _Rec()
        got, ok = authsrv.bind_key_to_build(A, 38797, 1, rec)
        check("a matching key is left alone and reports no swap",
              ok and got is A and not rec.events)
        # unknown build, loaded key belongs to a different known build: refuse.
        rec = _Rec()
        got, ok = authsrv.bind_key_to_build(A, 99999, 1, rec)
        check("an unknown build is REFUSED by name rather than handed a "
              "key that cannot decrypt it",
              not ok and rec.events
              and rec.events[0][0] == "key_build_mismatch")
    finally:
        authsrv.KEYS_BY_BUILD = saved

    # STRUCTURAL: both channels must reach the binding. The bug was not that
    # the logic was wrong -- it was correct, and unreachable from `game`.
    src = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    fn = next(n for n in ast.walk(src)
              if isinstance(n, ast.FunctionDef) and n.name == "handle")
    calls_in = []                       # (call node, inside the kind=='auth' If?)
    kind_ifs = [n for n in ast.walk(fn) if isinstance(n, ast.If)
                and any(isinstance(c, ast.Constant) and c.value == "auth"
                        for c in ast.walk(n.test))]
    inside = {id(c) for k in kind_ifs for c in ast.walk(k)}
    for n in ast.walk(fn):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == "bind_key_to_build"):
            calls_in.append(id(n) in inside)
    check("handle() binds the key at ONE site OUTSIDE the kind=='auth' "
          "branch, so the game channel cannot miss it -- the structural "
          "fact whose absence was the 2026-08-17 bug",
          len(calls_in) == 1 and not calls_in[0],
          f"{len(calls_in)} call site(s), inside-auth-branch={calls_in}")


def main():
    """Run the session, and make sure the ledger gets to rule on it either way.

    An exception escaping `_run` used to end the process with a traceback and no
    banner -- exit 1, but exit 1 with no count, no failure name and no record of
    the twenty checks that HAD passed. That is the failure `checks.py` was written
    to refuse, arriving by the one route a ledger cannot see: not a check quietly
    not running, but the run dying before the verdict. So the traceback is still
    printed (it is the diagnosis), and then it is also recorded as a named FAIL so
    the banner prints and the exit code comes from the ledger like every other run.
    """
    try:
        return _run()
    except Exception:                                        # noqa: BLE001
        traceback.print_exc()
        LEDGER.ok(False, "the run finished without an unhandled exception",
                  "traceback above")
        return LEDGER.verdict() or 1


def _run():
    section_key_binding(check)

    # By parameters, never by name -- and by the parameters the SERVER will load rather
    # than merely "some key file of ours". `classify` alone answers `ours` for a build
    # matching ANY rurik_dh_*.json, and with two in the vault the wrong one still derives
    # a key authsrv cannot match; passing `match` requires agreement instead of assuming
    # it. dhbuild prints every candidate it passes over and, if none qualifies, raises
    # with the artifact listing BEFORE a server is spawned.
    srv = server_keys()
    exe = dhbuild.select(dhbuild.OURS,
                         why="the Stage B handshake can only be verified against a "
                             "client keyed to this server",
                         match=(srv["prime"], srv["server_public"]))
    kind, detail = dhbuild.classify(exe)
    print(f"patched client : {os.path.basename(exe)}")
    print(f"                 {kind} -- {detail}")

    g, p, B = dhbuild.read_params(exe)
    print(f"read from exe  : g={g}, prime {p.bit_length()} bits, B {B.bit_length()} bits")

    # The announced build comes from THIS exe, so the client cannot claim to be a
    # build it is not. See the note on BUILD above for what that cost.
    global BUILD                                             # noqa: PLW0603
    BUILD = buildid.read(exe)[0]
    print(f"announcing     : build {BUILD}, read out of that same exe")
    # `check` is adopt_named: (name, cond, detail). These two were swapped from
    # the day the check was added (2026-08-14) until 2026-08-17, which made the
    # condition the message string -- always truthy -- and the label the boolean.
    # It printed `[PASS] True` on every run, including runs where the builds did
    # NOT agree, and it counted toward the floor while asserting nothing: a check
    # that cannot fail, holding a place in the count that says one did.
    check("the exe's build matches the key file the server will load",
          BUILD == _build_of_keyfile(srv),
          f"exe says {BUILD}, key file is {srv.get('build_tag')} -- these must "
          f"agree or the handshake is testing two different builds against "
          f"each other")

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

    # BOTH ends of this pipe are pinned to one codec, and that is not tidiness.
    # `text=True` alone decodes with the PARENT's locale codec while the child
    # encodes with whatever ITS stdout is set to; where those differ the parent's
    # decode can raise, and subprocess turns that into a silent None rather than
    # an error -- see drain_server() for the crash that cost this file its banner.
    # PYTHONIOENCODING fixes what authsrv writes, encoding=/errors= fixes what we
    # read, and "replace" means a surprising byte costs one glyph, never the run.
    srv = subprocess.Popen([sys.executable, "toolkit/authsrv/authsrv.py", "--once",
                            "--vault", SELFTEST_VAULT,
                            "--sessions", SELFTEST_SESSIONS],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                           text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    ok = True
    try:
        for _ in range(60):
            try:
                s = socket.create_connection(("127.0.0.1", PORT), timeout=0.3)
                break
            except OSError:
                time.sleep(0.1)
        else:
            # Through the ledger, not `print` + `return 1`. Section 0 has already
            # recorded four checks by this point, and a bare return threw them
            # away along with the banner -- exit 1 with nothing named, which is
            # indistinguishable from the crash this file was fixed for.
            check("authsrv came up on 6112 within 6s", False,
                  "the subprocess never accepted a connection; its log is the "
                  "next thing to read")
            return LEDGER.verdict()

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
            # The FAIL above is already recorded; let the ledger print it and own
            # the exit code, rather than returning a bare 1 over its head.
            return LEDGER.verdict()
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

        out, short = drain_server(srv)
        ok &= check("captured the server's log, which the next three checks read",
                    not short, short)
        srv_key = ""
        for line in out.splitlines():
            if "ARC4 key" in line:
                # The server ends this line with a Unicode ellipsis. Pinning the
                # pipe's codec means that now arrives as the ellipsis rather than
                # as the three mojibake characters `rstrip("…")` could not see --
                # but keep parsing forward rather than trimming from the end,
                # because errors="replace" can still put a U+FFFD in a line and
                # the comparison below should fail on the KEY, never on a glyph.
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
        cdir = vaultpath.vault_path("client")
        for build in sorted(os.listdir(cdir) if os.path.isdir(cdir) else [], reverse=True):
            cand = os.path.join(cdir, build, "Gw.exe")
            if os.path.exists(cand):
                try:
                    sg, sp, sB = dhbuild.read_params(cand)
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
