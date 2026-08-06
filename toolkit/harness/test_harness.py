"""Tests for the harness itself: the safety gate, the live capture tail, and
the one-command stack. No client is launched and no real port is touched --
the stack test runs on offset ports (16601, and 16112 at both loopback
aliases, mirroring the shared-port production shape) with captures sent to a
temp dir, so it can run while a real session is up.

A red line here names the broken thing before a game run turns it into thirty
silent seconds and a Code=058.

    python toolkit/harness/test_harness.py
"""

import os
import socket
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import drive_client as dc  # noqa: E402
import session  # noqa: E402
from livecapture import CaptureTail, by  # noqa: E402
from vaultpath import vault_path  # noqa: E402

FAILURES = []


def check(desc, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {desc}" + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        FAILURES.append(desc)


def refused(fn, *args):
    """True if fn exited loudly. The gate must never merely warn."""
    try:
        fn(*args)
        return False
    except SystemExit:
        return True


# ------------------------------------------------------------ safety gate ----

def test_assert_safe():
    good = os.path.join(vault_path("run"), "some_build", "Gw.exe")
    flags = ["-authsrv", "127.0.0.1", "-portal", "127.0.0.1"]

    check("gate refuses C:\\gw",
          refused(dc.assert_safe, r"C:\gw\Gw.exe", flags))
    check("gate refuses a path outside vault/run",
          refused(dc.assert_safe, r"C:\somewhere\Gw.exe", flags))
    check("gate refuses a missing -authsrv flag",
          refused(dc.assert_safe, good, ["-portal", "127.0.0.1"]))
    check("gate refuses a non-loopback authsrv",
          refused(dc.assert_safe, good,
                  ["-authsrv", "8.8.8.8", "-portal", "127.0.0.1"]))
    check("gate accepts a vault/run path with loopback flags",
          not refused(dc.assert_safe, good, flags))
    check("gate accepts a 127/8 alias for -authsrv (the handoff probe needs one)",
          not refused(dc.assert_safe, good,
                      ["-authsrv", "127.0.0.2", "-portal", "127.0.0.1"]))
    check("gate still refuses a dotted non-loopback that starts plausibly",
          refused(dc.assert_safe, good,
                  ["-authsrv", "128.0.0.1", "-portal", "127.0.0.1"]))


# ------------------------------------------------------------ live tail ----

def test_capture_tail():
    with tempfile.TemporaryDirectory() as d:
        stale = os.path.join(d, "authsrv-old-c1.jsonl")
        with open(stale, "w", encoding="utf-8") as f:
            f.write('{"kind": "login_ok", "t": 0.1}\n')

        tail = CaptureTail(d)

        # A file that predates the tail must never satisfy an assertion, even
        # if it grows -- last week's login is not evidence about this run.
        with open(stale, "a", encoding="utf-8") as f:
            f.write('{"kind": "login_ok", "t": 0.2}\n')
        ev, _ = tail.wait_for(by(kind="login_ok"), timeout=0.3)
        check("tail ignores files that existed before it started", ev is None)

        live = os.path.join(d, "authsrv-new-c1.jsonl")
        with open(live, "w", encoding="utf-8") as f:
            f.write('{"kind": "version", "channel": "auth", "t": 0.5}\n')
        ev, idx = tail.wait_for(by(kind="version"), timeout=2)
        check("tail sees a file that appears after it started", ev is not None)
        check("event fields survive the round trip",
              bool(ev) and ev.get("channel") == "auth")

        # Half a line is not an event; the completed line is exactly one.
        with open(live, "a", encoding="utf-8") as f:
            f.write('{"kind": "login')
        tail.poll()
        n_before = len(tail.events)
        with open(live, "a", encoding="utf-8") as f:
            f.write('_ok", "t": 1.0}\n')
        ev, idx2 = tail.wait_for(by(kind="login_ok"), timeout=2, since=idx)
        check("a line split across polls decodes once, intact",
              ev is not None and len(tail.events) == n_before + 1)

        # The cursor enforces order: an event from before the previous match
        # cannot satisfy the next checkpoint.
        ev, _ = tail.wait_for(by(kind="version"), timeout=0.3, since=idx2)
        check("cursor refuses to match backwards", ev is None)


# ------------------------------------------------------------- pre-flight ----

def test_preflight_helpers():
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    probe.listen(1)
    port = probe.getsockname()[1]
    try:
        rows = session.listeners_on(port)
        check("listeners_on finds our own listener",
              any(r["pid"] == os.getpid() for r in rows))
        # Host-aware matching: the same port at another loopback alias is a
        # DIFFERENT endpoint (auth and game both live on 6112 in production).
        check("listeners_on with the bound host still finds it",
              any(r["pid"] == os.getpid()
                  for r in session.listeners_on(port, "127.0.0.1")))
        check("listeners_on with another alias does not",
              not session.listeners_on(port, "127.0.0.3"))
        img = session.image_name(os.getpid())
        check("image_name resolves our own pid to python",
              "python" in os.path.basename(img).lower(), img)
        specs = [("probe", "127.0.0.1", port, ["unused"])]
        check("preflight refuses an occupied endpoint without --replace",
              refused(session.preflight, specs))
        check("preflight passes the same port at a free alias",
              not refused(session.preflight,
                          [("probe", "127.0.0.3", port, ["unused"])]))
    finally:
        probe.close()
    time.sleep(0.2)
    check("preflight passes once the port is free",
          not refused(session.preflight,
                      [("probe", "127.0.0.1", port, ["unused"])]))


# ------------------------------------------------------------- game args ----

def test_game_args():
    """--game-args reaches the gamesrv and NOTHING else.

    The asymmetry is the whole point and it is invisible from the outside: a
    probe handed to both listeners arms a second idle copy of the experiment,
    and a probe handed to the authsrv alone never runs, because the instance
    loads on the game channel. Both failures look like "the probe did nothing".
    """
    specs = dict((name, argv) for name, _h, _p, argv in
                 session.server_specs(game_args=["--probe", "attack_anim",
                                                 "--map", "146"]))
    check("gamesrv gets the extra flags",
          specs["gamesrv"][-4:] == ["--probe", "attack_anim", "--map", "146"])
    check("authsrv gets none of them",
          "--probe" not in specs["authsrv"] and "--map" not in specs["authsrv"])
    check("webgate gets none of them",
          "--probe" not in specs["webgate"] and "--map" not in specs["webgate"])
    # The default must stay byte-identical, or every run before this flag
    # existed stops being comparable with every run after it.
    plain = dict((n, a) for n, _h, _p, a in session.server_specs())
    check("no --game-args leaves all three command lines unchanged",
          all(plain[n] == specs[n][:len(plain[n])] for n in plain)
          and plain["gamesrv"] == specs["gamesrv"][:-4])


# ------------------------------------------------------------------ stack ----

def test_stack():
    with tempfile.TemporaryDirectory() as d:
        # Same shape as production: auth and game share ONE port at different
        # loopback aliases, so this exercises the host-aware pre-flight and
        # the per-pid listen proof against the endpoint pair that matters.
        specs = session.server_specs(portal_port=16601, auth_port=16112,
                                     game_port=16112, capture_root=d)
        stack = session.Stack(specs, logdir=os.path.join(d, "logs"))
        try:
            stack.start(timeout=30)
            for name, host, port, _ in specs:
                owned = any(r["pid"] == stack.procs[name].pid
                            for r in session.listeners_on(port, host))
                check(f"{name} owns {host}:{port}", owned)
            check("auth and game hold the same port at different hosts",
                  stack.procs["authsrv"].pid != stack.procs["gamesrv"].pid)

            body = urllib.request.urlopen(
                "http://127.0.0.1:16601/Spawned/WebGate/session/create.xml",
                timeout=5).read().decode()
            check("webgate answers session/create.xml", "<Session>" in body)

            check("preflight names the stack's own listeners as in the way",
                  refused(session.preflight, specs))

            # --replace may stop these listeners: they are python. This is the
            # kill path exercised against processes this test owns.
            session.preflight(specs, replace=True)
            check("--replace freed every endpoint",
                  not any(session.listeners_on(p, h) for _, h, p, _ in specs))
        finally:
            stack.stop()


if __name__ == "__main__":
    test_assert_safe()
    test_capture_tail()
    test_preflight_helpers()
    test_game_args()
    test_stack()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} FAILURE(S):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("ALL CHECKS PASSED")
