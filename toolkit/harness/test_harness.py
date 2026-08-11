"""Tests for the harness itself: the safety gate, the live capture tail, and
the one-command stack. No client is launched and no real port is touched --
the stack test runs on offset ports (16601, and 16112 at both loopback
aliases, mirroring the shared-port production shape) with captures sent to a
temp dir, so it can run while a real session is up.

A red line here names the broken thing before a game run turns it into thirty
silent seconds and a Code=058.

    python toolkit/harness/test_harness.py
"""

import inspect
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
import checks  # noqa: E402

# MEASURED 2026-08-06: 36, from a green run that really did start the stack. The
# previous note here said the count had been reached by READING the code (30, floored
# conservatively at 26) because the agent that added the ledger could not launch a
# server, and asked for it to be tightened at the first real green run. This is that
# run: 13 gate + 5 tail + 7 pre-flight + 4 game-args + 7 stack. No section here
# declares a skip, so the total is deterministic and the floor is the total -- a
# section that quietly stops running now reddens the run instead of shrinking it.
#
# Worth recording why it was not measured sooner: this file could not be imported at
# all from 2026-08-06 until the same day, because drive_client.py did `import cage`
# without clientpatch on sys.path. It is named in CLAUDE.md's suite list and was not
# among the tests run when that suite was last reported green.
# 2026-08-11: 50 -> 59, +9 for hold_key and --walk (sections 9 and 10); then
# 59 -> 66, +7 for the camera verbs (section 11). Each landed with the rung that
# needed it. hold_key earned its own section the hard way -- see the comment in
# it -- and the camera floor was declared as 67 from a miscount and reddened the
# run at 65 until it was measured, which is what the floor is for.
LEDGER = checks.Ledger("harness", floor=66)
check = checks.adopt_named(LEDGER)


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

    # --- and the live-capture configuration, added 2026-08-06 -------------------
    # The gate used to answer one question ("is every flag loopback?"), which could
    # not express the authorized run at all. It now answers "where does this argv
    # point?" and hands that to cage.assert_launch_safe, which reads the binary. So
    # these check the ARGV half only; test_cage.py checks the bytes half.
    live = os.path.join(vault_path("run-live"), "some_build", "Gw.exe")
    check("gate accepts a path under vault/run-live",
          not refused(dc.assert_safe, live, ["-authsrv", "1.2.3.4"]))
    check("an argv with no server flags at all resolves to the REAL service",
          dc.intended_target([]) == dc.ARENANET_DEFAULT)
    check("...which is the point: a missing -portal is not neutral",
          not dc.is_loopback(dc.ARENANET_DEFAULT))
    check("gate refuses an argv that names both sides at once",
          refused(dc.assert_safe, good,
                  ["-authsrv", "127.0.0.1", "-portal", "gwportal.arenanetworks.com"]))
    check("a fully routable argv passes the ARGV gate and reports its host",
          dc.assert_safe(live, ["-authsrv", "1.2.3.4", "-portal", "1.2.3.4"])
          == "1.2.3.4")
    check("and a loopback argv reports the loopback host it named",
          dc.assert_safe(good, ["-authsrv", "127.0.0.2", "-portal", "127.0.0.1"])
          == "127.0.0.2")


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

    # --- --game-args must survive a Windows path ------------------------------
    # shlex.split defaults to posix=True, where backslash is an ESCAPE, so it
    # turned a tape path into "C:gdRurikvault" and killed a run on 2026-08-10.
    # Every --probe and --tape invocation goes through this one function.
    print("\n7. --game-args survives Windows paths")
    import session as _sess
    tape_path = "C:" + "\\" + "gd" + "\\" + "Rurik" + "\\" + "vault"
    got = _sess.split_args("--tape " + tape_path)
    LEDGER.ok(got == ["--tape", tape_path],
              "--game-args keeps Windows backslashes intact",
              repr(got) + " -- posix=True shlex would give C:gdRurikvault")
    quoted = '--tape "' + "C:" + "\\" + "two words" + '" --tape-speed 2'
    spaced = _sess.split_args(quoted)
    LEDGER.ok(spaced == ["--tape", "C:" + "\\" + "two words", "--tape-speed", "2"],
              "and a quoted path with spaces stays ONE argument", repr(spaced))
    LEDGER.ok(_sess.split_args("") == [] and _sess.split_args(None) == [],
              "and an empty --game-args yields no arguments at all")

    # --- --labelrun prompts must reach the operator's screen ---------------------
    # The gamesrv is a CHILD process whose stdout session.py normally sends only to
    # gamesrv.log. --labelrun prompts a human through that stdout, so with the flag
    # set and no echo the operator sees nothing but this process's own "holding"
    # line -- which is what happened on 2026-08-10. The run was unusable: a client
    # session burned, and a capture whose steps nobody performed.
    print("\n8. --labelrun routes the gamesrv to the operator's screen")
    stack_all = _sess.Stack([], logdir=".", echo=True)
    stack_off = _sess.Stack([], logdir=".", echo=False)
    stack_lbl = _sess.Stack([], logdir=".", echo={"gamesrv"})
    LEDGER.ok(stack_off._echoes("gamesrv") is False,
              "by default nothing is echoed -- the ordinary loop stays quiet")
    LEDGER.ok(stack_lbl._echoes("gamesrv") and not stack_lbl._echoes("webgate")
              and not stack_lbl._echoes("authsrv"),
              "a name filter echoes the GAMESRV and nothing else",
              "echoing all three would bury a prompt banner in webgate and authsrv "
              "chatter")
    LEDGER.ok(all(stack_all._echoes(n) for n in ("webgate", "authsrv", "gamesrv")),
              "and --serve still echoes every server, as it always did")

    # ---- a chained tape run must outlive its own verdict ------------------------
    print("\n- the tape chain (R1.5 0b)")
    import vaultpath as _vp
    try:
        cap = _vp.vault_path("captures", "live", "20260807T143055")
        have_cap = os.path.isdir(cap)
    except Exception:
        have_cap = False
    if not have_cap:
        LEDGER.skip("tape chain", "no live capture 20260807T143055 in this vault")
    else:
        g1, hops, order, hosts = _sess.chain_specs(cap)
        LEDGER.ok(len(hops) == 3 and len(order) == 4
                  and hosts == ["127.0.0.3", "127.0.0.4", "127.0.0.5", "127.0.0.6"],
                  "a chain becomes one gamesrv per hop, each on its own 127.x alias",
                  f"{hosts} -- the client dials <host>:6112 and the advertised port "
                  "may be decorative, so hops cannot be separated by port")
        LEDGER.ok("--tape-rewrite-next" in g1
                  and all("--tape-rewrite-next" in argv for _h, argv in hops[:-1])
                  and "--tape-no-transfer" in hops[-1][1],
                  "every hop but the last repoints its handoff; the last truncates",
                  "an un-rewritten handoff on the final hop would dial ArenaNet")

        specs = _sess.server_specs(game_args=g1, hops=hops)
        names = [n for n, _h, _p, _a in specs]
        vaults = [a[a.index("--vault") + 1] for _n, _h, _p, a in specs
                  if _n.startswith("gamesrv")]
        LEDGER.ok(len(set(vaults)) == len(vaults),
                  "and every hop captures to its OWN directory",
                  "each instance names files authsrv-<stamp>-c1.jsonl with a conn_id "
                  "restarting at 1, so two hops starting in the same second would "
                  "overwrite each other and the run would still look fine")

        # THE ONE THAT MATTERS. The first chain run printed RUN VERDICT: PASS and tore
        # the stack down 1.7s into a 396-second chain, because the verdict target
        # ("body is in the map") is reached almost immediately under a tape. Every
        # symptom read as crash-on-map-load; the client was fine.
        hold, total = _sess.chain_hold(cap, order)
        LEDGER.ok(hold > total > 390 and hold >= total + 60,
                  "a chained run holds LONGER than the tape it is playing",
                  f"{hold:.0f}s hold for {total:.0f}s of tape -- the verdict says "
                  "'body is in the map', which under a tape is true in ~5s and says "
                  "nothing about the six minutes that ARE the experiment")
        LEDGER.ok(all(_sess.Stack(specs, logdir=".",
                                  echo={s[0] for s in specs
                                        if s[0].startswith("gamesrv")})._echoes(n)
                      for n in names if n.startswith("gamesrv")),
                  "and every hop echoes, not just the first",
                  "hops 2..N are separate processes; echoing only 'gamesrv' would show "
                  "hop 1 and then go silent for six minutes while the run worked")



def section_error_dialog():
    """The crash-dialog capture, which is the only evidence a client assert leaves.

    Gw.log does not record asserts, no dump file is written anywhere findable,
    and a ConnectionResetError in the gamesrv log appears on clean teardowns
    too. So if this path breaks, a crashing client becomes indistinguishable
    from a tidy exit -- which is precisely what happened on 2026-08-11 and cost
    an evening. The dialog is faked here so the extraction is checked without
    needing to crash a client.
    """
    import tempfile
    import types

    import ast
    import textwrap

    # BOTH EXITS, and a substring test cannot say that. This asserted
    # `"capture_error_dialog" in src` until 2026-08-11, which was already true when
    # hold_open called it from ONE branch -- so the guard passed identically before
    # and after the fix it was supposed to be protecting, and the run that crashed a
    # client still printed PASS. A check that cannot tell the defect from the fix is
    # not a check. This walks the function instead and requires a call on the
    # process-exited path AND on the hold-expired path, because a Guild Wars assert
    # keeps the process ALIVE behind a modal dialog and only the second path sees it.
    tree = ast.parse(textwrap.dedent(inspect.getsource(session.hold_open)))

    def calls_capture(nodes):
        return any(isinstance(n, ast.Call) and getattr(n.func, "id", None) ==
                   "capture_error_dialog"
                   for stmt in nodes for n in ast.walk(stmt))

    branches = [(calls_capture(n.body), calls_capture(n.orelse))
                for n in ast.walk(tree) if isinstance(n, ast.If) and n.orelse
                and "poll" in ast.dump(n.test)]
    LEDGER.ok(any(a and b for a, b in branches),
              "hold_open captures the dialog on BOTH exits, not just on client exit",
              f"poll()-guarded if/else branches (exited, expired): {branches} -- a GW "
              "assert leaves the process alive, so the timer path is the one that sees "
              "a real crash. The old substring form of this check passed either way")

    real = sys.modules.get("read_error_dialog")
    try:
        fake = types.ModuleType("read_error_dialog")
        fake.gw_pids = lambda: set()
        fake.dump = lambda pids: []
        sys.modules["read_error_dialog"] = fake
        with tempfile.TemporaryDirectory() as d:
            got = session.capture_error_dialog(d, wait=0.2)
            LEDGER.ok(got is None and not os.listdir(d),
                      "no dialog present -> reports a CLEAN exit and writes nothing",
                      f"returned {got!r}, wrote {os.listdir(d)}; inventing a "
                      f"crash file when there was no crash would be worse than "
                      f"silence")

        body = "\n".join([
            "*--> Crash <--*",
            "Assertion: !(m_flags & INTERNAL_FLAG_MOVEMENT_STALE)",
            r"P:\Code\Engine\Agent\AgAgent.cpp(1198)",
            "App: Gw.exe",
        ])
        fake.gw_pids = lambda: {4321}
        fake.dump = lambda pids: [(0x1234, "Gw.exe", [("Static", body)])]
        with tempfile.TemporaryDirectory() as d:
            got = session.capture_error_dialog(d, wait=0.2)
            wrote = os.path.isfile(os.path.join(d, "crash-dialog.txt"))
            text = open(os.path.join(d, "crash-dialog.txt"), encoding="utf-8").read() if wrote else ""
            LEDGER.ok(got is not None and wrote and "AgAgent.cpp(1198)" in text,
                      "a dialog IS captured whole, source file and line included",
                      f"wrote={wrote}, has the source line={'AgAgent.cpp(1198)' in text}. "
                      f"The line naming the fault sits at the TOP of a scrolled "
                      f"control, which is the part a screenshot always misses")
    finally:
        if real is not None:
            sys.modules["read_error_dialog"] = real
        else:
            sys.modules.pop("read_error_dialog", None)


section_error_dialog()


# ------------------------------------------------------------ held keys ----

class FakeUser32:
    """Records what would have gone to the keyboard, and who owns the foreground.

    `owner` is the pid the foreground window belongs to. Setting it to something
    else mid-run is how the "operator alt-tabbed away" case is reproduced without
    an operator.
    """

    def __init__(self, owner=4321, scan=0x11):
        self.owner, self.scan, self.events = owner, scan, []
        self.wheel, self.buttons, self.cursor = [], [], []
        self.raise_on_nth = None

    # -- the parts scroll() and orbit() use
    def GetWindowRect(self, hwnd, out):
        out._obj.left, out._obj.top = 0, 0
        out._obj.right, out._obj.bottom = 1920, 1080
        return 1

    def SetCursorPos(self, x, y):
        self.cursor.append((x, y))
        return 1

    def mouse_event(self, flags, dx, dy, data, extra):
        if flags == 0x0800:                       # MOUSEEVENTF_WHEEL
            self.wheel.append(data)
        else:
            self.buttons.append(flags)
        if self.raise_on_nth is not None \
                and len(self.buttons) + len(self.wheel) == self.raise_on_nth:
            raise RuntimeError("something blew up mid-drag")

    # -- the parts hold_key uses
    def SetForegroundWindow(self, hwnd):
        return 1

    def GetForegroundWindow(self):
        return 99

    def GetWindowThreadProcessId(self, hwnd, out):
        out._obj.value = self.owner
        return 1

    def MapVirtualKeyW(self, vk, kind):
        return self.scan

    def keybd_event(self, vk, scan, flags, extra):
        self.events.append((vk, scan, flags))
        if self.raise_on_nth is not None and len(self.events) == self.raise_on_nth:
            raise RuntimeError("something blew up mid-hold")


def section_hold_key():
    print("\n9. hold_key: a real hold, always released, and it carries a scan code")
    real_u32, real_fg = dc.user32, dc._force_foreground
    try:
        # THE DEFECT THIS SECTION EXISTS FOR. MEASURED 2026-08-11: the first
        # version passed bScan=0, held W for 8 s into a foregrounded client that
        # was fully in the world, and the client sent NOTHING -- no movement, no
        # turn, not even a character into the open chat box. A DirectX client
        # reads the raw input path, which carries the hardware scan code; an
        # event with bScan=0 carries no key at all as far as that path is
        # concerned. The harness reported `held 8.0s of 8.0s` either way, so
        # nothing short of the capture could tell a working run from a dead one.
        fake = FakeUser32(scan=0x11)
        dc.user32 = fake
        dc._force_foreground = lambda hwnd: True
        held = dc.hold_key(1, 4321, ord("W"), 0.3, check_every=0.1)
        downs = [e for e in fake.events if not e[2] & dc.KEYEVENTF_KEYUP]
        ups = [e for e in fake.events if e[2] & dc.KEYEVENTF_KEYUP]
        LEDGER.ok(downs and all(e[1] != 0 for e in fake.events),
                  "every key event carries a NON-ZERO scan code",
                  f"events {fake.events} -- bScan=0 is what a UI reader accepts "
                  f"and the raw input path silently drops")
        LEDGER.ok(len(downs) == 1 and len(ups) == 1
                  and downs[0][0] == ups[0][0] == ord("W"),
                  "one keydown, one keyup, same key",
                  f"{len(downs)} down / {len(ups)} up")
        LEDGER.ok(0.3 <= held < 0.9, "it holds for as long as it was asked",
                  f"{held:.2f}s for 0.3s -- a tap is not a hold, and GW moves "
                  f"the character only while the key is down")

        # The key is released even when the hold dies mid-flight. keybd_event
        # sets GLOBAL keyboard state: an unpaired keydown is a physically stuck
        # key for the whole desktop, and it outlives this process.
        fake = FakeUser32(scan=0x11)
        fake.raise_on_nth = 1                   # blow up ON the keydown's return
        dc.user32 = fake
        try:
            dc.hold_key(1, 4321, ord("S"), 0.2, check_every=0.05)
            blew = False
        except RuntimeError:
            blew = True
        LEDGER.ok(blew and any(e[2] & dc.KEYEVENTF_KEYUP for e in fake.events),
                  "an exception mid-hold still releases the key",
                  f"raised={blew}, events {fake.events}")

        # Focus is re-checked DURING the hold, not only at the start.
        fake = FakeUser32(scan=0x11)
        dc.user32 = fake
        alt_tabbed = {"n": 0}
        real_get = fake.GetWindowThreadProcessId

        def steal(hwnd, out):
            alt_tabbed["n"] += 1
            real_get(hwnd, out)
            if alt_tabbed["n"] >= 2:            # the first call is the entry check
                out._obj.value = 9999
            return 1
        fake.GetWindowThreadProcessId = steal
        held = dc.hold_key(1, 4321, ord("D"), 5.0, check_every=0.05)
        LEDGER.ok(held < 1.0, "losing the foreground cuts the leg short",
                  f"{held:.2f}s of 5.0s -- otherwise five seconds of 'D' go into "
                  f"whatever the operator switched to")
        LEDGER.ok(any(e[2] & dc.KEYEVENTF_KEYUP for e in fake.events),
                  "and the key is released on that path too")

        # And it sends NOTHING at all when the client never had focus.
        fake = FakeUser32(owner=1111, scan=0x11)
        dc.user32 = fake
        held = dc.hold_key(1, 4321, ord("W"), 1.0)
        LEDGER.ok(held == 0.0 and not fake.events,
                  "a client that does not own the foreground gets no key at all",
                  f"{len(fake.events)} event(s) -- never send blind")
    finally:
        dc.user32, dc._force_foreground = real_u32, real_fg

    print("\n11. the camera verbs, which nothing could reach until 2026-08-11")
    real_u32, real_fg = dc.user32, dc._force_foreground
    try:
        fake = FakeUser32(scan=0x11)
        dc.user32 = fake
        dc._force_foreground = lambda hwnd: True
        ok = dc.scroll(1, 4321, -3)
        LEDGER.ok(ok and len(fake.wheel) == 3 and all(d < 0 for d in fake.wheel),
                  "zoom out sends one wheel event PER NOTCH, all negative",
                  f"{fake.wheel} -- a single 3-notch event is legal and the "
                  f"client coalesces it into one jump; a hand does not")

        fake = FakeUser32(scan=0x11)
        dc.user32 = fake
        ok = dc.orbit(1, 4321, 0, -300, steps=6)
        downs = [f for f in fake.buttons if f == dc.MOUSEEVENTF_RIGHTDOWN]
        ups = [f for f in fake.buttons if f == dc.MOUSEEVENTF_RIGHTUP]
        LEDGER.ok(ok and len(downs) == 1 and len(ups) == 1,
                  "an orbit presses the right button once and RELEASES it",
                  f"{len(downs)} down / {len(ups)} up -- a button left down is "
                  f"stuck for the whole desktop and outlives this process")
        moves = [f for f in fake.buttons if f == dc.MOUSEEVENTF_MOVE]
        LEDGER.ok(len(moves) >= 6,
                  "the drag MOVES through mouse_event, in steps",
                  f"{len(moves)} relative move events -- the first version used "
                  f"SetCursorPos, which WARPS the pointer and synthesises no "
                  f"input event at all, so a client on the raw input path saw "
                  f"nothing. Measured: terrain 78.8%% before the pitch step and "
                  f"79.1%% after. This check pins the API; only a client can say "
                  f"the view turned")
        LEDGER.ok(len(fake.cursor) == 1,
                  "and SetCursorPos is used ONCE, only to place the drag",
                  f"{len(fake.cursor)} call(s)")

        fake = FakeUser32(scan=0x11)
        fake.raise_on_nth = 2
        dc.user32 = fake
        try:
            dc.orbit(1, 4321, 0, -300, steps=6)
            blew = False
        except RuntimeError:
            blew = True
        LEDGER.ok(blew and dc.MOUSEEVENTF_RIGHTUP in fake.buttons,
                  "a failure mid-drag still releases the button",
                  f"raised={blew}, buttons={fake.buttons}")

        for verb, args in (("scroll", (1, 4321, -3)), ("orbit", (1, 4321, 0, -300))):
            fake = FakeUser32(owner=1111, scan=0x11)
            dc.user32 = fake
            got = getattr(dc, verb)(*args)
            LEDGER.ok(got is False and not fake.wheel and not fake.buttons,
                      f"{verb} sends NOTHING when the client lacks focus",
                      f"wheel={fake.wheel} buttons={fake.buttons}")
    finally:
        dc.user32, dc._force_foreground = real_u32, real_fg

    print("\n10. --walk parses movement AND camera, and refuses the rest")
    LEDGER.ok(session.parse_walk("zoom:-14 pitch:300 S:8 wait:5")
              == [("zoom", "", -14.0), ("pitch", "", 300.0),
                  ("key", "S", 8.0), ("wait", "", 5.0)],
              "one ordered plan of typed steps",
              "zoom out, THEN pitch up, THEN back into a corner -- two flags "
              "could not express that sequence, and FINDINGS 25.5 needs it")
    LEDGER.ok(all(refused(session.parse_walk, bad)
                  for bad in ("W", "WW:3", "W:0", "W:-1", "zoom:0", "wait:0",
                              "wibble:3", "W:x")),
              "no argument, a two-character key, a non-positive hold, a camera "
              "move of zero, an unknown verb and a non-number all refuse",
              "a typo would otherwise be found after the map has loaded, which "
              "costs the whole run and a client session")


section_hold_key()
sys.exit(LEDGER.verdict())
