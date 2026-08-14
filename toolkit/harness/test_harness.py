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
LEDGER = checks.Ledger("harness", floor=99)
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
    test. The chase gate is a real distance test against AGGRO_RANGE = 1200, but
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


if __name__ == "__main__":
    test_assert_safe()
    test_capture_tail()
    test_preflight_helpers()
    test_game_args()
    test_enemy_default()
    test_crash_capture_always()
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


section_press_key()
section_hold_key()
sys.exit(LEDGER.verdict())
