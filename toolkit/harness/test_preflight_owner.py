"""The --replace ownership gate: pre-flight may stop THIS tree's stale
listeners, and nothing else's.

WHY THIS FILE EXISTS. On 2026-08-20 ~23:00, `session.py --replace` killed a
PARALLEL session's live webgate (pid 18520) and authsrv (pid 8412) mid-run.
The pre-flight's whole test was "is the listener python", and under CLAUDE.md's
one-worktree-per-session rule a parallel session's live stack is exactly that:
a python on our ports, indistinguishable by image name from our own stale one.
The fix reads the listener's COMMAND LINE and stops it only when the script it
names resolves into THIS session's tree -- tree compared to tree, never by
path prefix, because worktrees nest UNDER the main checkout and a prefix test
would call every one of them "ours" (the same defect through a different
door). A refusal prints the other listener's tree, because the operator's next
move is to coordinate with whoever works there.

Every check runs on ephemeral ports at 127.0.0.1/127.0.0.3, so this file can
run while a real session is up -- the same constraint test_harness.py meets.

    python toolkit/harness/test_preflight_owner.py
"""

import ast
import inspect
import os
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import session  # noqa: E402
import checks  # noqa: E402

# MEASURED 2026-08-20: 30, from a green run on the machine the incident
# happened on. The floor sits ONE below the measure for the single check that
# can legitimately skip -- the cross-check of this_tree() against git's own
# `rev-parse --show-toplevel`, which a machine without a git binary cannot run
# (everything else here is pure ctypes + sockets and must keep working).
LEDGER = checks.Ledger("preflight owner", floor=29)
check = checks.adopt_named(LEDGER)


def refused(fn, *args, **kw):
    """The SystemExit message if fn exited loudly, else None.

    The message, not a bool, because half the point of the refusal is WHAT it
    names: a refusal that does not print the other session's tree leaves the
    operator with a pid and no idea whose it is.
    """
    try:
        fn(*args, **kw)
        return None
    except SystemExit as ex:
        return str(ex)


def free_port(host):
    """An ephemeral port that was free on `host` a moment ago."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, 0))
    port = s.getsockname()[1]
    s.close()
    return port


# ------------------------------------------------- 1. reading a command line ----

def test_cmdline():
    print("\n1. reading another process's command line (pure ctypes)")
    cmd = session.cmdline(os.getpid())
    check("cmdline() reads our own process", bool(cmd), repr(cmd)[:120])
    argv = session.argv_of(cmd or "")
    check("argv_of() splits it with the OS's own rules and finds this script",
          any(t.lower().replace("/", "\\").endswith("test_preflight_owner.py")
              for t in argv), argv[:4])
    # The refusal path's input: a pid that is gone answers None, it does not
    # raise -- the caller must land on "cannot identify, so cannot stop".
    check("a pid that does not exist answers None, never raises",
          session.cmdline(0x7ABC0001) is None)
    check("argv_of('') is [] rather than the CommandLineToArgvW surprise "
          "(the empty string expands to OUR exe)", session.argv_of("") == [])


# --------------------------------------------------------- 2. whose tree is it ----

def test_tree_of():
    print("\n2. tree_of: nearest .git ancestor, worktrees included")
    ours = session.this_tree()
    check("this_tree() answers at all", bool(ours), ours)
    try:
        top = subprocess.run(["git", "-C", HERE, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True).stdout.strip()
    except FileNotFoundError:
        top = ""
    if top:
        want = os.path.normcase(os.path.realpath(top.replace("/", os.sep)))
        check("this_tree() agrees with git rev-parse --show-toplevel",
              want == os.path.normcase(ours), f"git: {top}  ours: {ours}")
    else:
        LEDGER.skip("git cross-check", "no git binary answered here")

    with tempfile.TemporaryDirectory() as d:
        main_root = os.path.join(d, "Rurik")
        os.makedirs(os.path.join(main_root, ".git"))       # main checkout: a DIR
        deep = os.path.join(main_root, "toolkit", "portal")
        os.makedirs(deep)
        check("a .git DIRECTORY marks the main checkout's root",
              session.tree_of(os.path.join(deep, "webgate.py")) == main_root)

        wt = os.path.join(main_root, ".claude", "worktrees",
                          "sleepy-cartwright-4143ba")
        os.makedirs(os.path.join(wt, "toolkit", "portal"))
        with open(os.path.join(wt, ".git"), "w") as f:      # worktree: a FILE
            f.write("gitdir: somewhere-else\n")
        wt_script = os.path.join(wt, "toolkit", "portal", "webgate.py")
        check("a .git FILE marks a worktree's root the same way",
              session.tree_of(wt_script) == wt)
        # THE NESTING TRAP, which is the 2026-08-20 defect restated: the
        # worktree sits INSIDE the main checkout, so a prefix test against
        # main_root would claim its stack. Nearest-ancestor must answer the
        # WORKTREE.
        check("a worktree nested under the checkout resolves to the WORKTREE, "
              "not the checkout above it",
              os.path.normcase(session.tree_of(wt_script) or "")
              == os.path.normcase(wt))

        lone = os.path.join(d, "no-repo", "srv.py")
        os.makedirs(os.path.dirname(lone))
        check("a path with no .git ancestor answers None",
              session.tree_of(lone) is None)


# ------------------------------------------------------ 3. the verdict itself ----

def test_replace_verdict():
    print("\n3. replace_verdict: ownership, not species")
    ours = session.this_tree()
    own_script = os.path.join(os.path.dirname(HERE), "portal", "webgate.py")
    own_cmd = subprocess.list2cmdline([sys.executable, "-u", own_script,
                                       "--port", "6601"])
    may, tree, why = session.replace_verdict(own_cmd, ours)
    check("a listener whose script is in THIS tree may be stopped", may, why)

    with tempfile.TemporaryDirectory() as d:
        # The exact 23:00 shape: our session at the checkout root, the victim
        # in a worktree NESTED under it.
        main_root = os.path.join(d, "Rurik")
        os.makedirs(os.path.join(main_root, ".git"))
        wt = os.path.join(main_root, ".claude", "worktrees",
                          "sleepy-cartwright-4143ba")
        os.makedirs(os.path.join(wt, "toolkit", "portal"))
        with open(os.path.join(wt, ".git"), "w") as f:
            f.write("gitdir: somewhere-else\n")
        victim = os.path.join(wt, "toolkit", "portal", "webgate.py")
        with open(victim, "w") as f:
            f.write("# stand-in for the victim's webgate\n")
        cmd = subprocess.list2cmdline([sys.executable, "-u", victim,
                                       "--port", "6601"])
        may, tree, why = session.replace_verdict(cmd, main_root)
        check("another worktree's listener is refused EVEN WHEN our tree "
              "contains that worktree", not may, why)
        check("and the verdict names the worktree, so the operator knows "
              "who to coordinate with",
              bool(tree) and os.path.normcase(tree)
              == os.path.normcase(os.path.realpath(wt)), tree)

    may, _t, _w = session.replace_verdict(None, ours)
    check("an unreadable command line is refused", not may)
    may, _t, _w = session.replace_verdict(
        subprocess.list2cmdline([sys.executable, "-c", "import time"]), ours)
    check("a command line with no script is refused", not may)
    may, _t, why = session.replace_verdict(
        subprocess.list2cmdline([sys.executable, "-u",
                                 os.path.join("toolkit", "authsrv",
                                              "authsrv.py")]), ours)
    check("a RELATIVE script path is refused -- a hand-run three-terminal "
          "server's cwd is invisible from here", not may, why)
    may, _t, _w = session.replace_verdict(own_cmd, None)
    check("no tree of our own refuses everything", not may)


# ------------------------- 4. integration: the foreign listener SURVIVES ----

def test_foreign_listener_survives():
    print("\n4. pre-flight vs a live listener from ANOTHER tree")
    with tempfile.TemporaryDirectory() as d:
        foreign = os.path.join(d, "other-worktree")
        os.makedirs(os.path.join(foreign, "toolkit"))
        with open(os.path.join(foreign, ".git"), "w") as f:
            f.write("gitdir: somewhere-else\n")
        srv = os.path.join(foreign, "toolkit", "srv.py")
        portfile = os.path.join(d, "port.txt")
        with open(srv, "w") as f:
            f.write(
                "import socket, sys, time\n"
                "s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)\n"
                "s.bind(('127.0.0.1', 0))\n"
                "s.listen(1)\n"
                "with open(sys.argv[1], 'w') as f:\n"
                "    f.write(str(s.getsockname()[1]))\n"
                "time.sleep(120)\n")
        proc = subprocess.Popen([sys.executable, srv, portfile],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 15
            port = None
            while time.monotonic() < deadline and port is None:
                try:
                    with open(portfile, encoding="ascii") as f:
                        port = int(f.read())
                except (OSError, ValueError):
                    time.sleep(0.1)
            check("the stand-in foreign stack is up and owns its port",
                  port is not None and any(
                      r["pid"] == proc.pid
                      for r in session.listeners_on(port, "127.0.0.1")))
            specs = [("authsrv", "127.0.0.1", port, ["unused"])]
            msg = refused(session.preflight, specs, replace=True)
            check("--replace REFUSES it", msg is not None)
            check("the refusal names the foreign tree",
                  msg is not None and os.path.normcase(
                      os.path.realpath(foreign)) in os.path.normcase(msg), msg)
            # The load-bearing one. Everything above could pass with the
            # listener already dead; this is the difference between a refusal
            # and an apology.
            check("and the foreign listener is STILL ALIVE afterwards",
                  proc.poll() is None)
            check("without --replace it is refused as well",
                  refused(session.preflight, specs) is not None)
        finally:
            proc.kill()
            proc.wait(timeout=10)


# ---------------- 5. integration: OUR OWN stale listener still gets stopped ----

def test_own_stale_listener_dies():
    print("\n5. pre-flight vs this tree's own stale listener "
          "(the design intent must survive the fix)")
    port = free_port("127.0.0.1")
    webgate = os.path.join(os.path.dirname(HERE), "portal", "webgate.py")
    with tempfile.TemporaryDirectory() as d:
        proc = subprocess.Popen(
            [sys.executable, "-u", webgate, "--bind", "127.0.0.1",
             "--port", str(port), "--vault", os.path.join(d, "portal")],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 15
            up = False
            while time.monotonic() < deadline and not up:
                up = any(r["pid"] == proc.pid
                         for r in session.listeners_on(port, "127.0.0.1"))
                time.sleep(0.1)
            check("a real webgate from THIS tree is up on an ephemeral port", up)
            specs = [("webgate", "127.0.0.1", port, ["unused"])]
            msg = refused(session.preflight, specs, replace=True)
            check("--replace stops it without a refusal", msg is None, msg)
            check("the endpoint is free afterwards",
                  not session.listeners_on(port, "127.0.0.1"))
            try:
                proc.wait(timeout=10)
                gone = True
            except subprocess.TimeoutExpired:
                gone = False
            check("and the process is actually gone", gone)
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)


# ------------------------------------- 6. the gamesrv alias IS pre-flighted ----

def test_gamesrv_alias_preflighted():
    print("\n6. the gamesrv alias (127.0.0.3) is inside the pre-flight, "
          "not beside it")
    # Raised as a question after the same evening's second failure -- a bind
    # failure on 127.0.0.3:6112 aborting a run after the stack was half-up --
    # so the answer is pinned here as executable fact rather than a reading of
    # the code: the gamesrv row server_specs() builds is caught by preflight()
    # like any other endpoint.
    specs = {name: (host, port)
             for name, host, port, _ in session.server_specs()}
    check("server_specs puts the gamesrv on its own loopback alias",
          specs.get("gamesrv", ("", 0))[0] == "127.0.0.3", specs.get("gamesrv"))

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.3", 0))
    s.listen(1)
    port = s.getsockname()[1]
    try:
        row = [sp for sp in session.server_specs(game_port=port)
               if sp[0] == "gamesrv"]
        msg = refused(session.preflight, row)
        check("a squatter on the gamesrv alias is refused BEFORE the stack "
              "starts, named as the gamesrv's endpoint",
              msg is not None and "gamesrv" in msg, msg)
    finally:
        s.close()

    # And main() hands preflight the WHOLE spec list, un-narrowed -- asserted
    # on the syntax tree, because "the row exists" plus "preflight checks what
    # it is given" still allows a call site that filters between the two.
    mod = ast.parse(inspect.getsource(session))
    mainfn = next(n for n in ast.walk(mod)
                  if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = [n for n in ast.walk(mainfn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "preflight"]
    check("main() calls preflight exactly once, on the name `specs`",
          len(calls) == 1 and len(calls[0].args) == 1
          and isinstance(calls[0].args[0], ast.Name)
          and calls[0].args[0].id == "specs")
    assigns = [n for n in ast.walk(mainfn) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == "specs"
                       for t in n.targets)]
    check("and `specs` is assigned once, straight from server_specs()",
          len(assigns) == 1 and isinstance(assigns[0].value, ast.Call)
          and isinstance(assigns[0].value.func, ast.Name)
          and assigns[0].value.func.id == "server_specs")


if __name__ == "__main__":
    test_cmdline()
    test_tree_of()
    test_replace_verdict()
    test_foreign_listener_survives()
    test_own_stale_listener_dies()
    test_gamesrv_alias_preflighted()
    sys.exit(LEDGER.verdict())
