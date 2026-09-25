"""Tests for the harness itself: the safety gate, the live capture tail, and
the one-command stack. No client is launched and no real port is touched --
the stack test runs on offset ports (16601, and 16112 at both loopback
aliases, mirroring the shared-port production shape) with captures sent to a
temp dir, so it can run while a real session is up.

A red line here names the broken thing before a game run turns it into thirty
silent seconds and a Code=058.

    python toolkit/harness/test_harness.py
"""

import ast
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
# 2026-08-14: 94 -> 99, +5 for section 9a. press_key had carried the exact
# bScan=0 defect section 9 exists for, for three days, in NO test at all --
# the fix had landed on hold_key and press_vk and missed the third copy of
# the same send. MEASURED from a green run, not derived.
# 2026-08-14: 99 -> 108, for the client-selection section. A real green run
# MEASURES 110; the floor sits two below it for the two checks that can
# legitimately skip -- the tape chain when this vault has no 20260807T143055
# capture, and the real-run-directory check when there is no vault/run. It is
# NOT set to 110 for the reason the camera floor already taught this file: a
# floor above what a healthy run produces reddens the run and says nothing.
# Note this test cannot run vault-LESS at all -- pinned.find() refuses first --
# so unlike test_origin.py there is no empty-vault figure to measure against.
# 2026-08-17: 108 -> 136, MEASURED 138 from a green run. The floor had sat at
# 108 through five commits that added checks (--probe echo, the roster, the
# skills-panel burst, client pre-flight scoping, interact:) plus this one's
# --hold section (+4): 26 checks could have vanished behind a passing floor,
# which is exactly the drift this ledger exists to catch. Still two below the
# measure, for the same two vault-dependent skips as before.
# FLOOR: 141, MEASURED from a green run 2026-08-17 after section 10 gained
# the camera-verb checks -- set from the run's own count, never arithmetic.
# 2026-09-24: 174 -> 181, MEASURED from a green run: +7 for the verdict leak on
# the hold's timer branch and at teardown (3 truth-table rows, the real
# hold_open timer path and its control, the finally's fold and its control).
# 2026-09-25: 181 -> 201, MEASURED from a green run: +20 for drag() and
# double_click() (sections 11b, 11c and 10b) -- the event shapes, the absolute
# normalisation on a desk with a negative origin, the landing read-back and
# its correction, the release on failure, the double-click gap read from
# GetDoubleClickTime, and both verbs' parses and refusals. None of the twenty
# can skip: the fake supplies the desk, the clock and the pointer, so the
# count is deterministic and the floor is the total. Every one of eleven
# sabotages reddened at least one of them before the floor moved (the commit
# message lists which).
LEDGER = checks.Ledger("harness", floor=201)   # 1z-cw: +2, the steer verb; 2026-09-14: +6, test_client_build; +5, the skill slot; 2026-09-15: +4, dashed values; 2026-09-25: +20, drag and double_click
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


# ------------------------------------------------------------- no enemy ----

def test_enemy_default():
    """The harness defaults to a world with no hostile in it.

    Added 2026-08-12, after the standing hostile disrupted a SECOND unrelated
    test. The chase gate is a real distance test against AGGRO_RANGE (1200 then,
    1012 since 2026-09-15 -- studies/monsterai 11), but
    content/world.toml puts the enemy 300 units from the player's arrival point
    with enabled = true, so it engages on every session in every map -- which is
    behaviourally a hard-coded attack even though the mechanism is not.

    The checks that earn this section are the last three: defaulting the enemy
    off silently turns every combat probe into a run against an empty world,
    which is precisely the "the probe did nothing" failure the section above
    exists for. So the warning must fire, and must NOT fire when the enemy is
    on -- a warning that appears either way is noise and gets ignored.
    """
    check("default appends --no-enemy",
          session.resolve_enemy([]) == ["--no-enemy"])
    check("and it survives alongside the caller's own flags, at the end",
          session.resolve_enemy(["--map", "143"])
          == ["--map", "143", "--no-enemy"])
    check("--enemy opts back in and adds nothing",
          session.resolve_enemy(["--map", "143"], enemy=True)
          == ["--map", "143"])
    # Explicit beats implicit and must not be doubled: authsrv parses store_true
    # so a duplicate is harmless, but a command line that says the same thing
    # twice is one nobody can read.
    once = session.resolve_enemy(["--no-enemy", "--map", "143"])
    check("an explicit --no-enemy is not duplicated",
          once.count("--no-enemy") == 1)
    conflict = False
    try:
        session.resolve_enemy(["--no-enemy"], enemy=True)
    except SystemExit:
        conflict = True
    check("--enemy against an explicit --no-enemy is REFUSED, not resolved",
          conflict)

    # End to end: the decision has to reach the gamesrv's real argv, and the
    # asymmetry the section above pins must survive it.
    specs = dict((n, a) for n, _h, _p, a in session.server_specs(
        game_args=session.resolve_enemy(["--map", "143"])))
    check("--no-enemy reaches the GAMESRV argv",
          "--no-enemy" in specs["gamesrv"])


# ---------------------------------------------------------- client build ----

def test_dashed_values():
    """A single dashed flag reaches --game-args / --client-arg in the SPACE form.

    2026-09-15: the owner ran the runbook's own example, `--game-args
    "--explorable"`, and argparse died with 'expected one argument' -- a value
    beginning with '-' is read as another option unless it contains a space, so
    the two-flag string in every other example happened to work and the one-flag
    string never had. The help text documented the = form; a documented trap is
    still a trap. `dashed_values` rewrites the space form to the = form before
    parsing, for exactly the options named and nothing else.
    """
    dv = session.dashed_values
    opts = ("--game-args", "--client-arg")
    check("a lone dashed value is joined to its option with =",
          dv(["--enemy", "--game-args", "--explorable", "--keep-open"], opts)
          == ["--enemy", "--game-args=--explorable", "--keep-open"])
    check("a two-flag string and a client -perf are joined the same way",
          dv(["--game-args", "--explorable --map 146", "--client-arg", "-perf"], opts)
          == ["--game-args=--explorable --map 146", "--client-arg=-perf"])
    check("a value that does not start with a dash is left alone",
          dv(["--game-args", "probe", "--map"], opts) == ["--game-args", "probe", "--map"])
    check("an option with nothing after it, and options not named, are untouched",
          dv(["--game-args"], opts) == ["--game-args"]
          and dv(["--account", "-x"], opts) == ["--account", "-x"])


def test_client_build():
    """The gamesrv is told which client build it serves, from the exe's bytes.

    Added 2026-09-14 after harness runs 20260914T111021 and T111122: the
    server's manifest sentinel is per build (897 on 38888, 888 before), the
    wire does not carry the build before the burst, and the harness reads the
    build out of the exe anyway -- so it says so. The mismatch is a fidelity
    defect, not a crash (the 38797 client served 897 reached the map, warning
    logged), which is why an explicit flag WINS instead of being refused: the
    known-bad arm is a run someone may want again.
    """
    check("the measured build is appended as --client-build N",
          session.resolve_client_build([], 38797) == ["--client-build", "38797"])
    check("and it survives alongside the caller's own flags, at the end",
          session.resolve_client_build(["--map", "143", "--no-enemy"], 38888)
          == ["--map", "143", "--no-enemy", "--client-build", "38888"])
    check("an explicit --client-build wins and is not doubled (the known-bad arm)",
          session.resolve_client_build(["--client-build", "38797"], 38888)
          == ["--client-build", "38797"])
    check("the = spelling counts as explicit too",
          session.resolve_client_build(["--client-build=38797"], 38888)
          == ["--client-build=38797"])
    check("no build (--serve, no exe) adds nothing and leaves the server's default",
          session.resolve_client_build(["--map", "143"], None) == ["--map", "143"])
    specs = dict((n, a) for n, _h, _p, a in session.server_specs(
        game_args=session.resolve_client_build([], 38797)))
    check("--client-build reaches the GAMESRV argv and no other",
          specs["gamesrv"][-2:] == ["--client-build", "38797"]
          and "--client-build" not in specs["authsrv"]
          and "--client-build" not in specs["webgate"])
    check("and neither the authsrv nor the webgate gets it",
          "--no-enemy" not in specs["authsrv"]
          and "--no-enemy" not in specs["webgate"])

    warn = session.warn_probe_without_enemy(["--probe", "attack_anim"])
    check("a probe with no hostile WARNS", bool(warn) and "NO HOSTILE" in warn)
    check("CONTROL: the same probe with --enemy does not",
          session.warn_probe_without_enemy(["--probe", "attack_anim"],
                                           enemy=True) is None)
    check("CONTROL: and a non-probe run is silent either way",
          session.warn_probe_without_enemy(["--map", "143"]) is None)


# ------------------------------------------------------- crash on every path ----

def test_served_maps():
    """Which map a run pins -- and, far more importantly, when we cannot say.

    This feeds `contentids.preflight(served=...)`, which narrows what the
    content-id pre-flight will REFUSE over. So every check below that expects
    None is a check that the guard keeps its full width: None means "check every
    content row". Getting a False positive here costs a blocked run; getting a
    False NEGATIVE here means a client loads a map whose geometry the server is
    not pathing against, and the run "looks like it worked" -- which is the
    failure contentids.py was written for.
    """
    check("no --map means the gamesrv picks its own, so we do not guess",
          session.served_maps([]) is None)
    check("--map 449 pins one map",
          session.served_maps(["--map", "449"]) == {449})
    check("and the = spelling parses the same",
          session.served_maps(["--map=449"]) == {449})
    check("a hex map id parses, because argparse would take one",
          session.served_maps(["--map", "0x1C1"]) == {449})
    # The travelling cases. A tape decides its own map from the recording's
    # 0x0195 and a chain deliberately hops between maps, so a --map alongside
    # them does NOT describe where the client ends up.
    check("--tape wins over a --map that is also present",
          session.served_maps(["--tape", "cap", "--map", "449"]) is None)
    check("--tape-chain likewise -- a chain moves between maps by design",
          session.served_maps(["--tape-chain", "cap", "--map", "449"]) is None)
    check("--labelrun likewise",
          session.served_maps(["--labelrun", "--map", "449"]) is None)
    # A malformed value must widen the guard, never disarm it.
    check("a non-numeric --map returns None rather than an empty set",
          session.served_maps(["--map", "kamadan"]) is None)
    check("and a trailing --map with no value does too",
          session.served_maps(["--map"]) is None)
    # The empty set is the shape that would clear the whole table if
    # contentids.preflight treated it as a scope. Nothing here may produce one.
    for argv in ([], ["--map"], ["--map", "x"], ["--tape", "c"],
                 ["--probe", "quest_name"]):
        got = session.served_maps(argv)
        check(f"served_maps({argv!r}) never returns an empty set",
              got is None or got)


def test_interact_control():
    """The one-slot mailbox behind the `interact:` action verb.

    It exists because the harness cannot aim: projecting an agent's world
    position to a screen pixel needs a camera yaw nothing tracks, and a blind
    click failed three runs running without producing one interaction. So the
    verb asks the SERVER to run its own interact arm. Everything downstream is
    real; the click is what did not happen, and both halves say so out loud.
    """
    import control
    control.clear()
    check("an empty slot reads as None", control.take_interact() is None)

    control.request_interact(99)
    check("a request round-trips", control.take_interact() == 99)
    check("and the slot is EMPTY afterwards -- read-and-clear",
          control.take_interact() is None)

    # Last write wins. A queue would let an action script get ahead of a server
    # that is mid-dialog and deliver a burst with no relation to the screen.
    control.request_interact(1)
    control.request_interact(2)
    check("two requests before a read leave the LAST one, not a queue",
          control.take_interact() == 2)
    check("and nothing behind it", control.take_interact() is None)

    # 2026-09-14: the skill slot, same contract, a (skill, target) pair.
    check("the skill slot reads empty", control.take_skill() is None)
    control.request_skill(346)
    check("a skill press round-trips with target 0 by default",
          control.take_skill() == (346, 0))
    control.request_skill(322, 90)
    check("and carries a target when given one",
          control.take_skill() == (322, 90))
    check("and is read-and-clear", control.take_skill() is None)
    control.request_skill(1)
    control.clear()
    check("clear() drops a pending skill press too",
          control.take_skill() is None)

    control.request_interact(7)
    control.clear()
    check("clear() drops a pending request",
          control.take_interact() is None,
          "a slot left by a killed run would otherwise fire into the next "
          "session's first seconds and get blamed on the protocol")

    # The verb has to be REACHABLE, not merely implemented: an action kind the
    # dispatcher does not know is silently skipped, which is the same shape of
    # failure as the blind click this replaces.
    here = os.path.dirname(os.path.abspath(__file__))
    src = open(os.path.join(here, "drive_client.py"),
               encoding="utf-8").read()
    check('kind == "interact"' in src,
          "drive_client dispatches the `interact` kind")
    check("interact:<agent_id>" in src,
          "and --actions' own help lists it",
          "a verb nobody can discover is one nobody uses")
    srv = open(os.path.join(os.path.dirname(here), "authsrv",
                            "authsrv.py"), encoding="utf-8").read()
    check("control.take_interact()" in srv and "_handle_interact" in srv,
          "and the gamesrv polls the slot into its real interact arm",
          "the same function the wire path calls, so a harness-driven run "
          "exercises exactly the code a click does")
    check("NOT by " in srv or "NOT a click" in srv or "not by a client" in srv.lower(),
          "and says on every fire that no click happened",
          "the upstream half is synthetic and a run that forgets to say so is "
          "evidence with a missing caveat")
    control.clear()


def test_crash_capture_always():
    """The crash dialog is read on EVERY run, not just --keep-open ones.

    MEASURED 2026-08-12: `capture_error_dialog` was reachable only from
    `hold_open()`, which `run_client` calls under `if a.keep_open:`. So an
    ordinary `--hold N` run captured nothing, and rung E10a's two client asserts
    (`deps` at TrnCreate:242, `state->zones` at MapData:660) survived only
    because the owner read them off the screen. The extraction was never broken
    -- the same crash under --keep-open wrote a crash-dialog.txt holding both
    lines -- so this was a missing CALL SITE.

    Asserted on the SYNTAX TREE, because the two things that matter here are
    invisible to a grep: that the call is in `run_client`'s `finally` at all,
    and that it comes BEFORE `dc.close_client`, which destroys the dialog.
    A file containing both names in the wrong order greps identically.
    """
    src = inspect.getsource(session)
    tree = ast.parse(src)
    fn = next((n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "run_client"),
              None)
    check("run_client is there to inspect", fn is not None)
    tries = [n for n in ast.walk(fn) if isinstance(n, ast.Try) and n.finalbody]
    check("run_client has a try/finally", bool(tries))

    def called_names(nodes):
        out = []
        for st in nodes:
            for n in ast.walk(st):
                if isinstance(n, ast.Call):
                    f = n.func
                    if isinstance(f, ast.Name):
                        out.append(f.id)
                    elif isinstance(f, ast.Attribute):
                        out.append(f.attr)
        return out

    final = [c for t in tries for c in called_names(t.finalbody)]
    check("the finally captures the error dialog",
          "capture_error_dialog" in final)
    check("and closes the client", "close_client" in final)
    if "capture_error_dialog" in final and "close_client" in final:
        check("CAPTURE COMES FIRST -- close_client destroys the dialog",
              final.index("capture_error_dialog") < final.index("close_client"))

    # The negative control. Reversing the order must be DETECTABLE by the check
    # above, or that check is decoration -- both names are present either way.
    reversed_final = list(final)
    i, j = (reversed_final.index("capture_error_dialog"),
            reversed_final.index("close_client"))
    reversed_final[i], reversed_final[j] = reversed_final[j], reversed_final[i]
    check("CONTROL: the ordering check fails on a reversed finally",
          not (reversed_final.index("capture_error_dialog")
               < reversed_final.index("close_client")))

    # And the first capture must win: a --keep-open run calls this twice, the
    # second time with a shorter wait, and a short look must not overwrite a
    # long one's result.
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "crash-dialog.txt")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("FIRST CAPTURE")
        got = session.capture_error_dialog(d, wait=0.1, quiet=True)
        check("an existing capture is not overwritten by a later, shorter look",
              got == path)
        with open(path, encoding="utf-8") as fh:
            check("and its contents survive", fh.read() == "FIRST CAPTURE")


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


def test_select_run_exe():
    """Which client the harness launches -- by BUILD and NAME, never by mtime.

    THE REGRESSION THIS PINS, 2026-08-14. `newest_run_exe` was
    `max(glob(vault/run/*/Gw.exe), key=os.path.getmtime)`. Build 38833 was
    snapshotted and assembled that afternoon, became "newest", and the harness
    silently changed which client it launches -- to a run directory whose
    Gw.dat never had the maps 146/148 replacement installed. Nothing failed at
    the exe; it would have failed later and elsewhere.

    Filtering by build alone was NOT enough and the second half is easy to
    miss: with 38833 excluded the newest 38797 copy is `reskin-roster`, an
    experiment copy, still beating the canonical directory. Both halves are
    checked here.

    `buildid.read` is stubbed because these cases need a client of a stated
    build, not a real PE. What it returns is the only thing the selector is
    entitled to know, and the real instrument is exercised against the real
    vault at the end of this section.
    """
    print("\nselecting the client to launch")
    real_read, real_vault_path = dc.buildid.read, dc.vault_path
    stamp = dc.pinned.PINNED.stamp
    try:
        def build_vault(dirs):
            """dirs: {name: build or None-for-unreadable}, made newest-last."""
            tmp = tempfile.mkdtemp()
            dc.vault_path = lambda *p: os.path.join(tmp, *p)
            says = {}
            for i, (name, number) in enumerate(dirs.items()):
                d = os.path.join(tmp, "run", name)
                os.makedirs(d)
                exe = os.path.join(d, "Gw.exe")
                open(exe, "wb").close()
                os.utime(exe, (1_700_000_000 + i * 60, 1_700_000_000 + i * 60))
                says[os.path.normcase(exe)] = number

            def fake_read(path):
                n = says.get(os.path.normcase(path))
                if n is None:
                    raise dc.buildid.NoBuildId(f"{path}: stubbed unreadable")
                return n, 0x004729E0, 16
            dc.buildid.read = fake_read
            return tmp

        # The exact shape on disk on 2026-08-14, canonical dir OLDEST.
        build_vault({stamp: dc.pinned.BUILD,
                     f"{stamp}-probe": dc.pinned.BUILD,
                     "reskin-roster": dc.pinned.BUILD,
                     "2026-08-13_64fae3b1369b": 38833})
        got, why = dc.select_run_exe()
        check("a newer build does NOT become the default client",
              got is not None and "2026-08-13" not in got, why)
        check("and neither does a newer VARIANT copy of the right build",
              got is not None and os.path.basename(os.path.dirname(got)) == stamp,
              why)
        check("the reason names the build and says it was not chosen by mtime",
              str(dc.pinned.BUILD) in why and "mtime" in why, why)

        # No canonical directory: a variant is usable but must be announced,
        # because an experiment copy carries whatever that experiment changed.
        build_vault({"reskin-roster": dc.pinned.BUILD,
                     "2026-08-13_64fae3b1369b": 38833})
        got, why = dc.select_run_exe()
        check("with no canonical directory a variant is used but SAID to be one",
              got is not None and "VARIANT" in why, why)

        # Only the wrong build present -- refuse with a diagnosis, not None.
        build_vault({"2026-08-13_64fae3b1369b": 38833})
        got, why = dc.select_run_exe()
        check("a vault holding only another build yields no client",
              got is None, why)
        check("and the refusal names what it found and what it wanted",
              "38833" in why and str(dc.pinned.BUILD) in why, why)

        # An unreadable candidate is skipped and REPORTED. "We could not look"
        # must never quietly narrow the field the way "wrong build" does.
        build_vault({"broken": None, stamp: dc.pinned.BUILD})
        got, why = dc.select_run_exe()
        check("an unreadable candidate does not stop the selection",
              got is not None and os.path.basename(os.path.dirname(got)) == stamp)
        check("and it is named rather than silently dropped",
              "broken" in why, why)

        build_vault({})
        got, why = dc.select_run_exe()
        check("an empty run root still points at make_run_dir.py",
              got is None and "make_run_dir" in why, why)

        # POSITIVE CONTROL. Every check above would also pass against a
        # function that refused everything or returned a constant, so ask for a
        # build that IS there and confirm it comes back.
        build_vault({"2026-08-13_64fae3b1369b": 38833})
        got, why = dc.select_run_exe(38833)
        check("while a build that IS present is returned when asked for",
              got is not None and "2026-08-13" in got, why)
    finally:
        dc.buildid.read, dc.vault_path = real_read, real_vault_path

    # --- and the real vault, with the real instrument -------------------------
    run_root = dc.vault_path("run")
    if not os.path.isdir(run_root):
        LEDGER.skip("the real run directories", "no vault/run in this vault")
    else:
        got, why = dc.select_run_exe()
        if got is None:
            LEDGER.skip("the real run directories", why.splitlines()[0])
        else:
            check("the client this vault would launch really is the pinned build",
                  dc.buildid.read(got)[0] == dc.pinned.BUILD, why)


if __name__ == "__main__":
    test_assert_safe()
    test_capture_tail()
    test_preflight_helpers()
    test_game_args()
    test_enemy_default()
    test_dashed_values()
    test_client_build()
    test_served_maps()
    test_interact_control()
    test_crash_capture_always()
    test_stack()
    test_select_run_exe()

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
    # PowerShell 5.1 collapses a trailing `""` inside single quotes into ONE
    # double quote, so the harness receives an unbalanced quote. Measured
    # 2026-08-12: it burned a run as a bare shlex ValueError traceback that
    # pointed at session.py rather than at the shell.
    refusal = None
    try:
        _sess.split_args('--probe profession_spawn --skills "')
    except SystemExit as ex:
        refusal = str(ex)
    LEDGER.ok(refusal is not None and "--skills 0" in refusal,
              "an unbalanced quote is REFUSED naming the PowerShell trap "
              "and what to type instead",
              f"{refusal!r} -- a bare shlex ValueError blames this module "
              f"for the shell's rewrite and says nothing actionable")

    # --- the roster and the avatar must agree about who you are -----------------
    # The character-select ROSTER is served on the AUTH channel from the
    # character blob; the in-world avatar is served on the GAME channel. With
    # --spawn-profession reaching only the gamesrv, the roster read "Warrior"
    # for a character that was profession 8 everywhere else (OBSERVED
    # 2026-08-13). It is the ONE game flag the authsrv also needs.
    print("\n8b. --spawn-profession reaches the authsrv, and nothing else does")
    LEDGER.ok(_sess.spawn_profession_args(["--probe", "x", "--spawn-profession", "8"])
              == ["--spawn-profession", "8"]
              and _sess.spawn_profession_args(["--spawn-profession=8"])
              == ["--spawn-profession=8"],
              "the flag is extracted in both spellings",
              "argparse accepts --flag N and --flag=N; a forwarder that knew "
              "one would silently drop the other")
    LEDGER.ok(_sess.spawn_profession_args(["--probe", "x", "--unlocks", "bar"]) == [],
              "and nothing is forwarded when it is absent")
    _specs = _sess.server_specs(game_args=["--spawn-profession", "8",
                                           "--unlocks", "bar", "--probe", "p"])
    _auth = [s for s in _specs if s[0] == "authsrv"][0][3]
    _game = [s for s in _specs if s[0] == "gamesrv"][0][3]
    LEDGER.ok("--spawn-profession" in _auth and "8" in _auth,
              "the authsrv spec carries it",
              "otherwise the roster and the avatar disagree")
    LEDGER.ok("--unlocks" not in _auth and "--probe" not in _auth,
              "while the GAME-channel flags do NOT leak to the authsrv",
              "handing it the whole list would arm a second, idle copy of the "
              "same experiment -- the asymmetry server_specs documents")
    LEDGER.ok(all(f in _game for f in ("--spawn-profession", "--unlocks", "--probe")),
              "and the gamesrv still gets everything")

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

    # --- and --probe prompts the operator the same way (2026-08-12) --------------
    # probes.py prints the question, the prediction and every step's watch line
    # through the same gamesrv stdout, and the watch lines ARE the experiment
    # ("NOW open the skills menu"). Until this date only --labelrun earned the
    # echo, so the first profession_skillbar attempt sat at a silent terminal
    # while its prompts went to gamesrv.log alone -- the 2026-08-10 labelrun
    # failure again, on the other flag that prompts a human.
    import argparse as _argparse

    def _flags(ga):
        return _argparse.Namespace(game_args=ga)

    LEDGER.ok(_sess.is_probing(_flags("--probe profession_skillbar"))
              and _sess.prompts_operator(_flags("--probe profession_skillbar")),
              "--probe counts as prompting the operator",
              "a probe run's step prompts go only to gamesrv.log otherwise, and "
              "the operator cannot know when to open the panel")
    LEDGER.ok(_sess.prompts_operator(_flags("--labelrun"))
              and not _sess.is_probing(_flags("--labelrun")),
              "--labelrun still prompts, and the two flags stay distinguishable",
              "the banner names the flag the operator actually passed")
    LEDGER.ok(not _sess.prompts_operator(_flags(""))
              and not _sess.prompts_operator(_flags("--enemy --tape-speed 2")),
              "an ordinary run still echoes nothing -- the default loop stays quiet",
              "an echo that fires on every run would bury the prompt banner in "
              "gamesrv chatter, which is the failure section 8 exists to prevent")
    import ast as _ast
    with open(_sess.__file__, encoding="utf-8") as f:
        _tree = _ast.parse(f.read())
    _fns = {fn.name: fn for fn in _tree.body if isinstance(fn, _ast.FunctionDef)}

    def _names(fn):
        return {n.id for n in _ast.walk(fn) if isinstance(n, _ast.Name)}

    LEDGER.ok("prompts_operator" in _names(_fns["main"])
              and "prompts_operator" in _names(_fns["run_client"]),
              "and BOTH consumers read the shared predicate (syntax tree)",
              "main() routes the echo and run_client() silences the hold's "
              "progress line; a revert to is_labelling in either restores the "
              "silent terminal for --probe runs")

    # ---- --hold N without --keep-open must hold, never silently skip ------------
    # run_client() gates the hold on a.keep_open alone, so `--hold 60` on its
    # own used to be inert: teardown at the verdict, and the healthy client's
    # orderly exit (game 0x0008, auth 0x0009, Offline, RST) reads exactly like
    # a client-side death. OBSERVED 2026-08-16: fourteen launches misdiagnosed
    # before the missing flag was noticed (studies/isle/FINDINGS.md "Rung 4").
    print("\n- --hold implies --keep-open (2026-08-16)")
    LEDGER.ok(_sess.hold_implies_keep_open(
                  _argparse.Namespace(hold=60.0, keep_open=False)).keep_open,
              "--hold 60 without --keep-open holds anyway",
              "an inert --hold closes a healthy client at the verdict, and its "
              "orderly exit telemetry is indistinguishable from a crash")
    LEDGER.ok(not _sess.hold_implies_keep_open(
                  _argparse.Namespace(hold=0.0, keep_open=False)).keep_open,
              "no --hold, no --keep-open: the ordinary run still tears down "
              "at the verdict")
    LEDGER.ok(_sess.hold_implies_keep_open(
                  _argparse.Namespace(hold=0.0, keep_open=True)).keep_open,
              "--keep-open alone is untouched -- it holds until the client "
              "exits")
    LEDGER.ok("hold_implies_keep_open" in _names(_fns["main"]),
              "and main() actually calls it (syntax tree)",
              "the 2026-08-12 crash-dialog gap was a correct function with a "
              "call site missing; this is the same trap")

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

    # AND CAPTURING THE DIALOG IS NOT RETRACTING THE VERDICT -- 2026-08-18.
    # `hold_open` returns "exited" for a client that died during the hold, and
    # session.py's own comment at that `return` says "a corpse afterwards unmakes
    # it". It did not. The value went into NOTHING: the call site was a bare
    # expression statement, `ok` was never reassigned after it, and a run whose
    # client asserted during the hold still printed RUN VERDICT: PASS and exited 0.
    # `customarea/FINDINGS.md` 31.4 recorded this defect as FIXED and the `return`
    # landed in the same commit as the portal (97f681a) -- the statement shipped and
    # the wiring did not, which is the failure mode this repo keeps naming: a rule
    # nothing checks is a wish. The walk path immediately above it retracts
    # correctly, and that similarity is what made the gap easy to read past.
    #
    # Two checks, because either alone is weak. The BEHAVIOURAL one pins what the
    # rule means; the STRUCTURAL one pins that the call site actually calls it --
    # a correct helper nobody invokes is exactly the defect being fixed here.
    fn = getattr(session, "verdict_after_hold", None)
    LEDGER.ok(callable(fn),
              "session.verdict_after_hold exists to fold the hold into the verdict",
              "a corpse during the hold has to be able to unmake a PASS somewhere; "
              "this is that somewhere, and it is a pure function so it can be "
              "exercised without a client")
    if callable(fn):
        LEDGER.ok(fn(True, "exited") is False,
                  "a client that DIED during the hold retracts a passing verdict",
                  "the run reached the map and then asserted -- PASS is the wrong "
                  "word for it, and this is the case that was broken")
        LEDGER.ok(fn(True, "expired") is True,
                  "and a hold that merely RAN OUT does not",
                  "otherwise every healthy --keep-open run fails and the retraction "
                  "gets switched off within a day")
        LEDGER.ok(fn(False, "expired") is False,
                  "and it never PROMOTES a failed run to a pass",
                  "it may only ever take the verdict away")
        # "crashed", 2026-09-24: the hold ran out on a client sitting behind its
        # crash dialog. A GW assert keeps the process alive, so this -- not
        # "exited" -- is the usual crash, and the rule used to see only "exited".
        LEDGER.ok(fn(True, "crashed") is False,
                  "a hold that ran out on a client BEHIND ITS CRASH DIALOG retracts too",
                  "the common crash, not the rare one: 177 of the 184 harness runs "
                  "with a captured dialog and a report said PASS")
        LEDGER.ok(fn(True, None) is True,
                  "and the value a healthy timer path really returns (None) keeps it",
                  "'expired' above is a stand-in hold_open never returns; this is "
                  "the one it does")
        LEDGER.ok(fn(False, "crashed") is False,
                  "and a crash never promotes a failed run either",
                  "retraction only, for the new token as for the old")
    else:
        LEDGER.skip("the hold-retraction truth table",
                    "verdict_after_hold does not exist yet")

    def consumes_hold_open(src):
        """True if no `hold_open(...)` call is left as a bare expression statement.

        A bare call discards the return, which is the whole defect: the value
        that is supposed to unmake the verdict is computed and dropped.
        """
        t = ast.parse(textwrap.dedent(src))
        calls = [n for n in ast.walk(t) if isinstance(n, ast.Call)
                 and getattr(n.func, "id", None) == "hold_open"]
        bare = [n for n in ast.walk(t) if isinstance(n, ast.Expr)
                and isinstance(n.value, ast.Call)
                and getattr(n.value.func, "id", None) == "hold_open"]
        return bool(calls) and not bare

    LEDGER.ok(consumes_hold_open(inspect.getsource(session.run_client)),
              "and run_client CONSUMES hold_open's return rather than dropping it",
              "this is the check that was red when the defect was found: the call "
              "site read `hold_open(...)` as a statement, so the retraction could "
              "not reach `ok` no matter how right the function was")
    LEDGER.ok(not consumes_hold_open(
        "def f():\n    if a.keep_open:\n        hold_open(proc, a.hold)\n"),
              "and that detector reports the PRE-FIX shape as broken",
              "the defect as it actually stood, verbatim -- a checker that cannot "
              "tell the bug from the fix is what let the substring form of the "
              "check above sit green through the 2026-08-11 crash")

    # THE TEARDOWN LOOK IS A VERDICT TOO -- 2026-09-24. `run_client`'s `finally`
    # reads the dialog on every run (test_crash_capture_always pins that it does,
    # and before close_client), and until this date it dropped the answer the way
    # hold_open's timer branch did: on a run without --keep-open, a client that
    # asserted during the walk or after the verdict is still RUNNING, so the
    # walk's "client exited" test never fires, the teardown finds the dialog, and
    # the run said PASS over it.
    def folds_teardown_dialog(src):
        """True if a `finally` KEEPS capture_error_dialog's answer AND that name
        reaches verdict_after_hold. Both conjuncts: a kept value nothing reads
        is the same dropped return with an extra line."""
        t = ast.parse(textwrap.dedent(src))
        kept = set()
        for tr in (n for n in ast.walk(t) if isinstance(n, ast.Try) and n.finalbody):
            for n in (m for st in tr.finalbody for m in ast.walk(st)):
                if (isinstance(n, ast.Assign) and isinstance(n.value, ast.Call)
                        and getattr(n.value.func, "id", None) == "capture_error_dialog"):
                    kept |= {g.id for g in n.targets if isinstance(g, ast.Name)}
        folded = any(isinstance(n, ast.Call)
                     and getattr(n.func, "id", None) == "verdict_after_hold"
                     and any(isinstance(x, ast.Name) and x.id in kept
                             for arg in n.args for x in ast.walk(arg))
                     for n in ast.walk(t))
        return bool(kept) and folded

    LEDGER.ok(folds_teardown_dialog(inspect.getsource(session.run_client)),
              "run_client's finally KEEPS the teardown dialog and folds it into the verdict",
              "a dialog up at close is a client that asserted; printing its assert "
              "and then RUN VERDICT: PASS is the leak this closes")
    LEDGER.ok(not folds_teardown_dialog(
        "def f():\n    try:\n        pass\n    finally:\n"
        "        capture_error_dialog(outdir, wait=2.0, quiet=True)\n"
        "        dc.close_client(proc)\n")
              and not folds_teardown_dialog(
        "def f():\n    try:\n        pass\n    finally:\n"
        "        d = capture_error_dialog(outdir, wait=2.0, quiet=True)\n"
        "    ok = verdict_after_hold(ok, held)\n"),
              "CONTROL: that detector reports the pre-fix bare call AND a kept-but-unread "
              "value as broken",
              "the first is the finally as it stood verbatim; the second is the "
              "half-fix that assigns the path and never lets it reach the verdict")

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

        # THE TIMER PATH ITSELF, through the real hold_open -- 2026-09-24. The
        # truth table above cannot see this defect: the branch captured the
        # dialog, printed its `>>> Assertion:` line and returned None, and
        # verdict_after_hold read None correctly as "keep the PASS". A right rule
        # handed the wrong value. So the value comes from hold_open, with a
        # client that never exits (poll() stays None, as behind a GW assert) and
        # a hold that runs out on its timer.
        class LiveClient:
            pid, returncode = 4321, None

            def poll(self):
                return None

        def timer_hold(dialog):
            fake.gw_pids = lambda: {4321}
            fake.dump = lambda pids: ([(0x1234, "Gw.exe", [("Static", body)])]
                                      if dialog else [])
            with tempfile.TemporaryDirectory() as d:
                held = session.hold_open(LiveClient(), 0.1, {}, d, quiet=True)
                return held, os.path.isfile(os.path.join(d, "crash-dialog.txt"))

        held, wrote = timer_hold(dialog=True)
        LEDGER.ok(wrote and session.verdict_after_hold(True, held) is False,
                  "a dialog found when the hold RUNS OUT retracts the pass",
                  f"hold_open returned {held!r}, crash-dialog.txt written={wrote}. "
                  f"Until 2026-09-24 this path wrote the file, printed the assert "
                  f"and returned None -- RUN VERDICT: PASS, exit 0")
        held, wrote = timer_hold(dialog=False)
        LEDGER.ok(not wrote and session.verdict_after_hold(True, held) is True,
                  "CONTROL: no dialog when the hold runs out keeps the pass",
                  f"hold_open returned {held!r}. Most holds end this way; a "
                  f"retraction that fired on them would be switched off in a day")
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

    2026-09-25, for drag() and double_click(): the fake also keeps a POINTER,
    moved by SetCursorPos and by every move event -- an ABSOLUTE one is mapped
    back to a pixel over `desk` (the virtual desktop as GetSystemMetrics would
    report it: left, top, width, height), a relative one is added -- and
    GetCursorPos answers with it. So the landing check in drag() is exercised
    against what the moves IMPLY, not against a constant, and a desk whose
    origin is not (0, 0) is one constructor argument away. `timeline` holds
    every mouse event AND every recorded sleep (FakeClock) in order, which is
    how a gap between two presses is measured without sleeping it.
    """

    def __init__(self, owner=4321, scan=0x11, desk=(0, 0, 1920, 1080),
                 dclick_ms=500):
        self.owner, self.scan, self.events = owner, scan, []
        self.wheel, self.buttons, self.cursor = [], [], []
        self.raise_on_nth = None
        self.desk, self.dclick_ms = desk, dclick_ms
        self.pointer, self.pos_reads, self.timeline = (0, 0), 0, []

    # -- the parts scroll() and orbit() use
    def GetWindowRect(self, hwnd, out):
        out._obj.left, out._obj.top = 0, 0
        out._obj.right, out._obj.bottom = 1920, 1080
        return 1

    def SetCursorPos(self, x, y):
        self.cursor.append((x, y))
        self.pointer = (x, y)
        return 1

    def mouse_event(self, flags, dx, dy, data, extra):
        self.timeline.append(("mouse", flags, dx, dy))
        if flags & 0x0001:                        # MOUSEEVENTF_MOVE
            if flags & 0x8000:                    # ...ABSOLUTE: 0..65535 over the desk
                vx, vy, cx, cy = self.desk
                self.pointer = (vx + dx * cx // 65536, vy + dy * cy // 65536)
            else:                                 # relative: a delta
                self.pointer = (self.pointer[0] + dx, self.pointer[1] + dy)
        if flags == 0x0800:                       # MOUSEEVENTF_WHEEL
            self.wheel.append(data)
        else:
            self.buttons.append(flags)
        if self.raise_on_nth is not None \
                and len(self.buttons) + len(self.wheel) == self.raise_on_nth:
            raise RuntimeError("something blew up mid-drag")

    # -- the parts drag() and double_click() use
    def GetSystemMetrics(self, index):
        vx, vy, cx, cy = self.desk
        # 76..79 the virtual desktop; 36/37 the double-click rectangle, at
        # Windows' default of 4 px.
        return {76: vx, 77: vy, 78: cx, 79: cy, 36: 4, 37: 4}.get(index, 0)

    def GetDoubleClickTime(self):
        return self.dclick_ms

    def GetCursorPos(self, out):
        self.pos_reads += 1
        out._obj.x, out._obj.y = self.pointer
        return 1

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


_real_time = time


class FakeClock:
    """Stands in for dc.time while a drag or a double-click runs.

    Sleeps are RECORDED on the fake's timeline, in order with its mouse
    events, and never slept: the gap between two presses is then the sum of
    the sleeps between them, measured rather than timed, and the suite does
    not wait 0.6 s per drag. Everything else defers to the real module.
    """

    def __init__(self, timeline):
        self.timeline = timeline

    def sleep(self, seconds):
        self.timeline.append(("sleep", seconds))

    # Through the alias: the class body rebinds `time` on the line below,
    # so `time.strftime` after it would read the staticmethod, not the module.
    perf_counter = staticmethod(_real_time.perf_counter)
    time = staticmethod(_real_time.time)
    strftime = staticmethod(_real_time.strftime)
    gmtime = staticmethod(_real_time.gmtime)


def section_press_key():
    print("\n9a. press_key: the sibling the scan-code fix MISSED")
    # MEASURED 2026-08-14. Section 9 below has pinned hold_key's non-zero scan
    # code since 2026-08-11, and `press_vk` was written correct. `press_key` --
    # the one every `key:` action in every action script goes through, including
    # skill slots 1..8 -- kept `keybd_event(vk, 0, 0, 0)` and was in NO test at
    # all. So the trap that section 9 exists for was live in a second function
    # for three days, under a check that could never see it: a symbol appearing
    # in a test file is not a check, and neither is a fix applied to two of three
    # copies of the same send.
    #
    # It surfaced as `action 18:key:K: sent` with the Skills panel never opening.
    # The owner pressed K by hand and it opened at once.
    real_u32, real_fg = dc.user32, dc._force_foreground
    try:
        fake = FakeUser32(scan=0x25)
        dc.user32 = fake
        dc._force_foreground = lambda hwnd: True
        ok = dc.press_key(1, 4321, ord("K"))
        downs = [e for e in fake.events if not e[2] & dc.KEYEVENTF_KEYUP]
        ups = [e for e in fake.events if e[2] & dc.KEYEVENTF_KEYUP]
        LEDGER.ok(bool(ok) and len(downs) == 1 and len(ups) == 1,
                  "press_key sends one keydown and one keyup",
                  f"{len(downs)} down / {len(ups)} up, returned {ok!r}")
        LEDGER.ok(fake.events and all(e[1] != 0 for e in fake.events),
                  "and EVERY event carries a NON-ZERO scan code",
                  f"events {fake.events} -- this is the check that was missing; "
                  f"before the fix every entry here was (vk, 0, flags)")
        LEDGER.ok(all(e[1] == fake.scan for e in fake.events),
                  "and the scan code is the LAYOUT's answer, not a constant",
                  f"MapVirtualKeyW said {fake.scan:#04x}")
        # A layout with no scan code for the key must REFUSE rather than fall
        # back to zero -- that fallback is the original defect wearing a guard.
        fake = FakeUser32(scan=0)
        dc.user32 = fake
        got = dc.press_key(1, 4321, ord("K"))
        LEDGER.ok(not got and not fake.events,
                  "a key with NO scan code on this layout sends NOTHING",
                  f"returned {got!r}, {len(fake.events)} event(s) -- silently "
                  f"sending bScan=0 here would restore the defect exactly")
        # Focus is still respected: someone else owning the foreground sends
        # nothing, because keybd_event is GLOBAL and would land in their window.
        fake = FakeUser32(owner=1111, scan=0x25)
        dc.user32 = fake
        got = dc.press_key(1, 4321, ord("K"))
        LEDGER.ok(not got and not fake.events,
                  "and a client that does NOT own the foreground gets nothing",
                  f"returned {got!r}, {len(fake.events)} event(s)")
    finally:
        dc.user32, dc._force_foreground = real_u32, real_fg


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
    LEDGER.ok(session.parse_walk("yaw:400 alt:4 left:2 shot:1")
              == [("yaw", "", 400.0), ("key", "alt", 4.0),
                  ("key", "left", 2.0), ("shot", "", 1.0)],
              "the 2026-08-17 camera verbs parse: yaw, a named-key hold, and "
              "a scripted shot",
              "these four retire 'the harness cannot aim' for everything but "
              "a world-anchored click -- zoom, yaw, ALT and read the labels")
    LEDGER.ok(all(refused(session.parse_walk, bad)
                  for bad in ("yaw:0", "alt:0", "alt:x", "lefty:2")),
              "a yaw of zero, a zero-length ALT, a non-number and a "
              "near-miss key name all refuse",
              "'lefty' must not silently become the L key")
    LEDGER.ok(session.parse_walk("hover:0.044,0.054,38")
              == [("hover", "0.044,0.054", 38.0)],
              "the 2026-08-19 hover verb parses: window-relative point plus "
              "a duration, no click",
              "a HUD tooltip is the only readable surface for the buff "
              "family's contested field (skillcast 14.4), and reading one "
              "unattended needs a cursor park that never presses a button")
    LEDGER.ok(session.parse_walk("wait:3 attack:10 wait:55")
              == [("wait", "", 3.0), ("attack", "10", 0.0),
                  ("wait", "", 55.0)]
              and all(refused(session.parse_walk, bad)
                      for bad in ("attack:", "attack:x")),
              "the 2026-08-20 attack verb parses, and refuses a non-id",
              "it is a WALK step as well as an action because actions all "
              "fire before the walk and the hold, while --shots photographs "
              "only the walk and the hold -- so an attack ordered from the "
              "action script can have its entire fight finish unphotographed. "
              "That is not hypothetical: on 2026-08-20 a critical landed at "
              "20:11:39 and the first hold frame was stamped 20:13:58, 139 s "
              "later. As a walk step the fight and its frames overlap by "
              "construction")
    LEDGER.ok(session.parse_walk("steer:w,300,3 steer:S,-200,1.5")
              == [("steer", "W,300", 3.0), ("steer", "S,-200", 1.5)],
              "the 2026-09-09 steer verb parses: a key held WHILE the view turns, "
              "key upper-cased, pixels signed, seconds the hold",
              "RUN-1zCW pair 1: every single-step plan ends each leg in a stop, "
              "so no heading report ever arrived inside the old 0.5 s grant "
              "floor and the A/B measured nothing -- the operator steers while "
              "moving, and this is the only step that does")
    LEDGER.ok(all(refused(session.parse_walk, bad)
                  for bad in ("steer:W,300", "steer:W,0,3", "steer:W,300,0",
                              "steer:WW,300,3", "steer:W,x,3"))
              and callable(getattr(session, "steer", None)),
              "steer refuses two fields, a zero turn, a zero hold, a two-letter "
              "key and a non-number; and the executor exists",
              "a steer that parsed to nothing would run as a plain hold and "
              "the run would look like the control arm")
    LEDGER.ok(session.parse_walk("click:0.411,0.561")
              == [("click", "0.411,0.561", 1.0)],
              "the click verb parses: a window-relative point, no duration",
              "it exists to press a PANEL BUTTON at a fixed fraction -- the "
              "attribute panel's + arrow -- which is the aiming case the "
              "harness could not reach; a world target still needs a person")
    LEDGER.ok(all(refused(session.parse_walk, bad)
                  for bad in ("click:0.5", "click:0.5,0.5,0.5", "click:1.5,0.5",
                              "click:0,0.5", "click:a,b")),
              "click refuses one number, three numbers, and fractions on or "
              "outside the window edge",
              "a click at a wrong literal presses whatever happens to be "
              "there, which is worse than a refusal because it looks like a run")
    LEDGER.ok(all(refused(session.parse_walk, bad)
                  for bad in ("hover:0.5,0.5", "hover:0.5,0.5,0",
                              "hover:1.5,0.5,3", "hover:0,0.5,3",
                              "hover:a,0.5,3")),
              "hover refuses two numbers, a zero duration, fractions on or "
              "outside the window edge, and a non-number",
              "a cursor parked at a wrong literal would read as 'no tooltip' "
              "-- the probe's null result -- so the parse must fail loudly "
              "instead")
    LEDGER.ok(dc.NAMED_KEYS["alt"] == 0x12 and dc.NAMED_KEYS["left"] == 0x25
              and dc.NAMED_KEYS["right"] == 0x27 and dc.NAMED_KEYS["up"] == 0x26
              and dc.NAMED_KEYS["down"] == 0x28
              and dc.NAMED_KEYS["space"] == 0x20,
              "the named-key VKs are Windows' own, asserted against LITERALS",
              "the bounded-search lesson: a table checked against itself "
              "cannot fail")


def section_drag_dclick():
    """drag() and double_click(), 2026-09-25, for the town armour runsheet.

    What a unit test CAN pin here is the event shape -- one press, absolute
    moves, one release, the landing read back; two presses at one point
    inside the system time -- and what it cannot is whether the Guild Wars
    client reads that shape as a drag or a double-click. That is UNVERIFIED
    until a client run, exactly as orbit() was on 2026-08-11, when a version
    whose test passed moved the pointer and not the camera. The lesson from
    that day is the load-bearing check below: every move is a real input
    event, and for a DROP it is an ABSOLUTE one.
    """
    print("\n11b. drag: a LEFT drag through ABSOLUTE move events, landing read back")
    real_u32, real_fg, real_time = dc.user32, dc._force_foreground, dc.time
    ABS = 0x0001 | 0x4000 | 0x8000      # MOVE | VIRTUALDESK | ABSOLUTE, as literals
    try:
        dc._force_foreground = lambda hwnd: True

        def run(fn, fake, *args, **kw):
            dc.user32, dc.time = fake, FakeClock(fake.timeline)
            return fn(*args, **kw)

        def mouse(fake):
            return [e for e in fake.timeline if e[0] == "mouse"]

        # THE PLAIN CASE, hand-computed. (0.25, 0.5) -> (0.75, 0.5) in the
        # fake's 1920x1080 window on a 1920x1080 desk at the origin: start
        # pixel (480, 540), target (1440, 540). A correct absolute move for
        # the target maps BACK to it as dx * 1920 // 65536 == 1440 and
        # dy * 1080 // 65536 == 540; the naive figure 1440 * 65535 // 1920
        # = 49151 maps back to 1439, one cell's edge over.
        fake = FakeUser32()
        rep = run(dc.drag, fake, 1, 4321, 0.25, 0.5, 0.75, 0.5, seconds=0.6)
        ev = mouse(fake)
        downs = [i for i, e in enumerate(ev) if e[1] == dc.MOUSEEVENTF_LEFTDOWN]
        ups = [i for i, e in enumerate(ev) if e[1] == dc.MOUSEEVENTF_LEFTUP]
        moves = [i for i, e in enumerate(ev) if e[1] & dc.MOUSEEVENTF_MOVE]
        steps = [m for m in moves if downs and m > downs[0]]
        LEDGER.ok(bool(rep) and len(downs) == 1 and len(ups) == 1 and steps
                  and downs[0] < steps[0] and ups[0] > moves[-1]
                  and ups[0] == len(ev) - 1,
                  "a drag presses LEFTDOWN once and LEFTUP once: the down "
                  "before the first drag step, the up after the last move",
                  f"{len(downs)} down at {downs}, {len(ups)} up at {ups}, "
                  f"moves at {moves} of {len(ev)} events")
        LEDGER.ok(len(steps) >= 2 and all(ev[m][1] == ABS for m in steps),
                  "and EVERY drag step is an ABSOLUTE|VIRTUALDESK move event",
                  f"{len(steps)} step(s), flags "
                  f"{sorted({hex(ev[m][1]) for m in steps})} -- a relative "
                  f"delta is scaled by pointer speed and acceleration before "
                  f"the pointer moves, so a relative drag drops the item "
                  f"wherever the mouse settings say; 0xc001 is the literal")
        last = ev[steps[-1]] if steps else ("mouse", 0, -1, -1)
        first = ev[steps[0]] if steps else ("mouse", 0, -1, -1)
        placed = ev[moves[0]] if moves else ("mouse", 0, -1, -1)
        LEDGER.ok(abs(last[2] * 1920 // 65536 - 1440) <= 1
                  and abs(last[3] * 1080 // 65536 - 540) <= 1
                  and 0 <= last[2] <= 65535 and 0 <= last[3] <= 65535
                  and (first[2], first[3]) != (placed[2], placed[3]),
                  "the last step maps back to the target pixel (1440, 540) "
                  "within 1 px, and the first step really MOVES",
                  f"last normalised ({last[2]}, {last[3]}) -> "
                  f"({last[2] * 1920 // 65536}, {last[3] * 1080 // 65536}); "
                  f"placed at ({placed[2]}, {placed[3]}), first step "
                  f"({first[2]}, {first[3]}) -- the client decides a drag "
                  f"has begun only once the pointer moves with the button down")
        LEDGER.ok(rep and rep["start"] == (480, 540)
                  and rep["target"] == (1440, 540)
                  and rep["landed"] == (1440, 540) and rep["corrected"] is False
                  and fake.pos_reads >= 1 and len(fake.cursor) == 1,
                  "the landing is READ BACK (GetCursorPos) and reported: on "
                  "target, nothing corrected, one SetCursorPos to place",
                  f"{rep!r}, GetCursorPos read {fake.pos_reads} time(s), "
                  f"SetCursorPos {fake.cursor}")

        # A DESK WHOSE ORIGIN IS NOT (0, 0): a second monitor to the LEFT of
        # the primary, so the virtual desktop is 3840 wide and starts at
        # x = -1920. Hand-computed: target (960, 540); a correct normalised x
        # maps back as -1920 + dx * 3840 // 65536 == 960. The figure that
        # ignores the origin -- 960 * 65536 // 1920 + 1 = 32769 -- maps back
        # to -1920 + 1920 = 0: the far edge of the OTHER monitor.
        fake = FakeUser32(desk=(-1920, 0, 3840, 1080))
        rep = run(dc.drag, fake, 1, 4321, 0.25, 0.5, 0.5, 0.5, seconds=0.6)
        ev = mouse(fake)
        downs = [i for i, e in enumerate(ev) if e[1] == dc.MOUSEEVENTF_LEFTDOWN]
        steps = [i for i, e in enumerate(ev)
                 if e[1] & dc.MOUSEEVENTF_MOVE and downs and i > downs[0]]
        last = ev[steps[-1]] if steps else ("mouse", 0, -1, -1)
        LEDGER.ok(abs(-1920 + last[2] * 3840 // 65536 - 960) <= 1
                  and abs(last[3] * 1080 // 65536 - 540) <= 1
                  and last[2] != 32769
                  and rep and rep["landed"] == (960, 540) and not rep["corrected"],
                  "on a desk whose origin is (-1920, 0) the target still maps "
                  "back to (960, 540), and the landing agrees",
                  f"normalised x {last[2]} -> {-1920 + last[2] * 3840 // 65536}; "
                  f"32769 would be the origin-blind answer and lands at x=0, "
                  f"a monitor away; {rep!r}")

        # A LANDING THAT IS OFF: GetCursorPos lies by 5 px on its first read
        # (an operator's hand on the mouse). The drag must correct it BEFORE
        # the release -- SetCursorPos + one more absolute move -- and SAY so.
        fake = FakeUser32()
        truth, lies = fake.GetCursorPos, {"n": 0}

        def nudged(out):
            lies["n"] += 1
            truth(out)
            if lies["n"] == 1:
                out._obj.x += 5
            return 1
        fake.GetCursorPos = nudged
        rep = run(dc.drag, fake, 1, 4321, 0.25, 0.5, 0.75, 0.5, seconds=0.6)
        ev = mouse(fake)
        ups = [i for i, e in enumerate(ev) if e[1] == dc.MOUSEEVENTF_LEFTUP]
        moves = [i for i, e in enumerate(ev) if e[1] & dc.MOUSEEVENTF_MOVE]
        fixup = ev[moves[-1]] if moves else ("mouse", 0, -1, -1)
        LEDGER.ok(rep and rep["corrected"] is True and rep["landed"] == (1440, 540)
                  and fake.cursor == [(480, 540), (1440, 540)]
                  and ups and moves[-1] < ups[0] and fixup[1] == ABS
                  and fixup[2] * 1920 // 65536 == 1440,
                  "a pointer found 5 px off after the last move is corrected "
                  "before the release -- SetCursorPos, one more ABSOLUTE move "
                  "-- and the return says corrected",
                  f"{rep!r}, SetCursorPos {fake.cursor}, last move "
                  f"{fixup[1]:#x} -> x {fixup[2] * 1920 // 65536}, up at "
                  f"{ups} -- a drop at the wrong cell must not look clean")

        # A FAILURE MID-DRAG STILL RELEASES. raise_on_nth counts non-wheel
        # events: the placement move (1), LEFTDOWN (2), the first step (3).
        fake = FakeUser32()
        fake.raise_on_nth = 3
        try:
            run(dc.drag, fake, 1, 4321, 0.25, 0.5, 0.75, 0.5)
            blew = False
        except RuntimeError:
            blew = True
        LEDGER.ok(blew and fake.buttons and fake.buttons[-1] == dc.MOUSEEVENTF_LEFTUP
                  and fake.buttons.count(dc.MOUSEEVENTF_LEFTDOWN) == 1,
                  "a failure on the first drag step still releases the LEFT button",
                  f"raised={blew}, buttons={[hex(b) for b in fake.buttons]} "
                  f"-- a button left down is stuck for the whole desktop")

        # NOTHING WITHOUT FOCUS: not a press, not a move, not even the warp.
        fake = FakeUser32(owner=1111)
        rep = run(dc.drag, fake, 1, 4321, 0.25, 0.5, 0.75, 0.5)
        LEDGER.ok(rep is False and not mouse(fake) and not fake.cursor,
                  "a client that does not own the foreground gets no drag at all",
                  f"returned {rep!r}, {len(mouse(fake))} mouse event(s), "
                  f"SetCursorPos {fake.cursor}")

        # A DRAG THAT ROUNDS TO ZERO PIXELS is refused before the press:
        # 0.5 and 0.5001 are both pixel 960 in a 1920-wide window, and a
        # press-and-release on one cell is a click, not a drag.
        fake = FakeUser32()
        rep = run(dc.drag, fake, 1, 4321, 0.5, 0.5, 0.5001, 0.5)
        LEDGER.ok(rep is False and not fake.buttons and not fake.cursor,
                  "a drag whose start and end round to one pixel sends nothing",
                  f"returned {rep!r}, buttons={fake.buttons}")

        LEDGER.ok(dc.MOUSEEVENTF_ABSOLUTE == 0x8000
                  and dc.MOUSEEVENTF_VIRTUALDESK == 0x4000
                  and dc.MOUSEEVENTF_MOVE == 0x0001
                  and (dc.SM_XVIRTUALSCREEN, dc.SM_YVIRTUALSCREEN,
                       dc.SM_CXVIRTUALSCREEN, dc.SM_CYVIRTUALSCREEN) == (76, 77, 78, 79)
                  and (dc.SM_CXDOUBLECLK, dc.SM_CYDOUBLECLK) == (36, 37),
                  "the mouse_event flags and GetSystemMetrics indices are "
                  "Windows' own, asserted against LITERALS",
                  "the fake maps 0x8000 and 76..79 the way the OS does; a "
                  "constant that drifted would pass every check above")

        print("\n11c. double_click: two presses at ONE point, inside the system time")
        # The fake's double-click time is 80 ms, NOT the 500 ms default: a
        # double_click that assumed 500 and paced its pair at 100 ms would
        # go red here, which is the point -- the bound is READ, not assumed.
        fake = FakeUser32(dclick_ms=80)
        ok = run(dc.double_click, fake, 1, 4321, 0.5, 0.5)
        ev = mouse(fake)
        presses = [e[1] for e in ev
                   if e[1] in (dc.MOUSEEVENTF_LEFTDOWN, dc.MOUSEEVENTF_LEFTUP)]
        downs = [i for i, e in enumerate(ev) if e[1] == dc.MOUSEEVENTF_LEFTDOWN]
        ups = [i for i, e in enumerate(ev) if e[1] == dc.MOUSEEVENTF_LEFTUP]
        moves = [i for i, e in enumerate(ev) if e[1] & dc.MOUSEEVENTF_MOVE]
        LEDGER.ok(ok is True and presses == [dc.MOUSEEVENTF_LEFTDOWN,
                                             dc.MOUSEEVENTF_LEFTUP,
                                             dc.MOUSEEVENTF_LEFTDOWN,
                                             dc.MOUSEEVENTF_LEFTUP],
                  "a double-click is down, up, down, up -- two of each, in order",
                  f"returned {ok!r}, presses {[hex(p) for p in presses]}")
        LEDGER.ok(len(downs) == 2 and len(ups) == 2
                  and not any(ev[i][1] & dc.MOUSEEVENTF_MOVE
                              for i in range(downs[0], ups[-1] + 1))
                  and moves == [0] and ev[0][1] == ABS
                  and ev[0][2] * 1920 // 65536 == 960
                  and ev[0][3] * 1080 // 65536 == 540
                  and fake.cursor == [(960, 540)] and fake.pointer == (960, 540),
                  "ZERO movement between the presses: the pointer is placed "
                  "once (SetCursorPos + one absolute move at (960, 540)) "
                  "before the first down and never moves again",
                  f"moves at {moves}, downs {downs}, ups {ups}, SetCursorPos "
                  f"{fake.cursor}, pointer ends at {fake.pointer} -- a move "
                  f"between the clicks is what SM_CXDOUBLECLK forbids")
        # The gap: every recorded sleep between the first down and the
        # second down, summed. 80 ms is the fake's literal.
        tl = fake.timeline
        idx = [i for i, e in enumerate(tl) if e[0] == "mouse"
               and e[1] == dc.MOUSEEVENTF_LEFTDOWN]
        gap = sum(e[1] for e in tl[idx[0]:idx[1]] if e[0] == "sleep") \
            if len(idx) == 2 else 99.0
        LEDGER.ok(0 < gap < 0.08,
                  "the second down follows the first inside GetDoubleClickTime "
                  "(80 ms here), and the bound is READ from it",
                  f"gap {gap * 1000:.0f} ms -- an implementation pacing the pair "
                  f"for the 500 ms default would sit at 100 ms and fail this")

        fake = FakeUser32(owner=1111, dclick_ms=80)
        ok = run(dc.double_click, fake, 1, 4321, 0.5, 0.5)
        LEDGER.ok(ok is False and not mouse(fake) and not fake.cursor,
                  "a client that does not own the foreground gets no double-click",
                  f"returned {ok!r}, {len(mouse(fake))} mouse event(s)")

        # THE POINTER LEFT THE RECTANGLE: GetCursorPos reports 10 px right of
        # where the pair was placed (the rectangle is 4 px). That pair was two
        # clicks as far as Windows is concerned, and the verb must say so --
        # False, loudly -- while still releasing both presses.
        fake = FakeUser32(dclick_ms=80)
        truth = fake.GetCursorPos

        def wandered(out):
            truth(out)
            out._obj.x += 10
            return 1
        fake.GetCursorPos = wandered
        ok = run(dc.double_click, fake, 1, 4321, 0.5, 0.5)
        LEDGER.ok(ok is False
                  and fake.buttons.count(dc.MOUSEEVENTF_LEFTUP) == 2
                  and fake.buttons.count(dc.MOUSEEVENTF_LEFTDOWN) == 2,
                  "a pointer found outside the double-click rectangle afterwards "
                  "is reported as NOT a double-click, with both presses released",
                  f"returned {ok!r}, buttons {[hex(b) for b in fake.buttons]} "
                  f"-- two clicks reported as a double would hide a helm that "
                  f"never went on")
    finally:
        dc.user32, dc._force_foreground, dc.time = real_u32, real_fg, real_time

    print("\n10b. --walk parses dclick and drag, and refuses the malformed ones")
    LEDGER.ok(session.parse_walk("dclick:0.411,0.561")
              == [("dclick", "0.411,0.561", 1.0)]
              and all(refused(session.parse_walk, bad)
                      for bad in ("dclick:0.5", "dclick:0.5,0.5,0.5",
                                  "dclick:1.5,0.5", "dclick:0,0.5",
                                  "dclick:0.5,1", "dclick:a,b", "dclick:")),
              "dclick parses as click does, and refuses one number, three, "
              "fractions on or outside the edge, non-numbers and no argument",
              "the same point rule as click -- a double-click at a wrong "
              "literal equips whatever is there, or opens nothing, and both "
              "look like a run")
    LEDGER.ok(session.parse_walk("drag:0.2,0.3,0.6,0.7 drag:0.2,0.3,0.6,0.7,1.5")
              == [("drag", "0.2,0.3,0.6,0.7", 0.6),
                  ("drag", "0.2,0.3,0.6,0.7", 1.5)],
              "drag parses four fractions with SECONDS defaulting to 0.6, "
              "and five with the seconds given",
              "the runsheet's helm move is one such line; the seconds are "
              "the leg's `asked`, as a hold's are")
    LEDGER.ok(all(refused(session.parse_walk, bad)
                  for bad in ("drag:0.2,0.3,0.6", "drag:0.2,0.3,0.6,0.7,1,2",
                              "drag:0,0.3,0.6,0.7", "drag:0.2,0.3,1,0.7",
                              "drag:0.2,1.5,0.6,0.7", "drag:0.5,0.5,0.5,0.5",
                              "drag:0.2,0.3,0.6,0.7,0", "drag:0.2,0.3,0.6,0.7,-1",
                              "drag:a,0.3,0.6,0.7", "drag:0.2,0.3,0.6,x",
                              "drag:0.2,0.3,0.6,0.7,x", "drag:")),
              "drag refuses three and six fields, fractions on or outside "
              "the edge, a zero-length drag, non-positive seconds, "
              "non-numbers and no argument",
              "a zero-length drag is a press-and-release on one cell, which "
              "the client may read as 'pick the helm up' -- refused at parse "
              "AND again in dc.drag when the fractions round to one pixel")
    try:
        session.parse_walk("wibble:3")
        unknown = ""
    except SystemExit as e:
        unknown = str(e)
    LEDGER.ok("dclick" in unknown and "drag" in unknown and "click" in unknown,
              "the unknown-verb refusal names dclick and drag among the verbs",
              f"{unknown!r}")
    acts = inspect.getsource(session.run_client)
    legs = inspect.getsource(session.walk_legs)
    LEDGER.ok('"dclick"' in acts and "dc.double_click(" in acts
              and "dc.drag(" in acts and "parse_walk(" in acts
              and '"dclick"' in legs and "dc.double_click(" in legs
              and "dc.drag(" in legs and '"landed"' in legs,
              "both the --actions loop and the walk executor dispatch dclick "
              "and drag to dc, the action through parse_walk's refusals, and "
              "the walk row carries the landing",
              "a verb that parses to nothing runs as nothing and the run "
              "looks like the control arm")


def section_window_geometry():
    """The Play click's aspect guard -- the rule that a fraction is only a
    position in the window shape it was measured in.

    Written because the failure was silent AND destructive: on 2026-08-18 the
    client sat at 716x1040 (another session had resized it), PLAY_FX/PLAY_FY
    landed on DELETE, and `_play` clicked it six times, opening the
    "type the name to delete Test Warrior" dialog. The run reported only
    "clicks landed: True" and a failed map checkpoint, i.e. it looked like an
    ordinary timeout. These checks are on the pure arithmetic, which is the
    half that can be tested without a window.
    """
    print("\n11. the Play click refuses a window shape it was not calibrated in")
    want = dc.CLIENT_W / float(dc.CLIENT_H)

    def deviation(w, h):
        return abs((w / float(h)) - want) / want

    LEDGER.ok(deviation(dc.CLIENT_W, dc.CLIENT_H) == 0.0
              and deviation(1926, 1039) <= dc.ASPECT_TOLERANCE,
              "the calibrated geometry and the ORIGINAL measurement window "
              "both pass",
              "PLAY_FX/PLAY_FY were measured at 1926x1039 and the runs since "
              "use 1936x1040; a guard that rejected either would be a guard "
              "against our own working configuration")
    LEDGER.ok(deviation(716, 1040) > dc.ASPECT_TOLERANCE,
              "the 716x1040 window that clicked DELETE is REFUSED",
              "the regression this whole section exists for -- 63% off, and "
              "the old code fired at it anyway")
    LEDGER.ok(deviation(1600, 900) > dc.ASPECT_TOLERANCE
              and deviation(1024, 768) > dc.ASPECT_TOLERANCE,
              "ordinary 16:9 and 4:3 windows are refused too, rather than "
              "special-casing the one shape that burned us",
              "they are legitimate sizes -- normalize_window resizes them "
              "FIRST, and the refusal only fires when that failed, so this is "
              "the fail-closed path and not a rejection of 16:9 as such")
    LEDGER.ok(0 < dc.ASPECT_TOLERANCE < 0.05,
              f"the tolerance is a real number in a sane range "
              f"({dc.ASPECT_TOLERANCE})",
              "a tolerance of 0 would refuse border jitter; one above ~5% "
              "starts admitting shapes where the button bar has relaid out")
    LEDGER.ok(callable(getattr(dc, "normalize_window", None))
              and callable(getattr(dc, "window_size", None)),
              "normalize_window and window_size exist and are callable",
              "the guard is only half the fix: without the resize every "
              "non-standard window becomes a refusal instead of a run")


section_press_key()
section_hold_key()
section_drag_dclick()
section_window_geometry()
sys.exit(LEDGER.verdict())
