"""The servers die with session.py, however session.py ends.

WHY THIS FILE EXISTS -- OBSERVED 2026-09-24. The run orchestrator stopped a run
by TerminateProcess on `session.py` alone (QProcess.kill(), and the QProcess
destructor when the window closed). `Stack.stop()` runs from a `finally`, which
a terminated process never reaches, and Windows does not kill children with
their parent: two `authsrv.py` processes outlived the orchestrator by hours
holding 6112, and every other worktree's launch was refused behind them. The
fix (`childjob.py`) puts each server in a Job Object with KILL_ON_JOB_CLOSE,
whose only handle is `session.py`'s -- the kernel closes it when `session.py`
dies and the close kills the job.

THE LOAD-BEARING CHECK IS SECTION 3, AND IT HAS A KNOWN-BAD ARM. A stand-in
parent builds the REAL `session.Stack` over a stand-in server on an ephemeral
port, the test TerminateProcesses the parent, and the server's listener must be
gone within DEADLINE seconds. The same run with the job disabled -- the parent
swaps `childjob.KillOnClose` for one that refuses, so the Stack takes its own
"no job" path -- must leave the listener UP past the same deadline: that arm
is the defect, reproduced, and it is what proves the check can go red. It is
also the only evidence here that Windows really does orphan the child; without
it a treatment that "passed" could be a server that died of something else.

Section 1 is the kernel's rule on its own, with no process dying (adopt, then
close the handle: the adopted child dies, a non-adopted sibling does not).
Section 2 is `Stack.start()` adopting every server it starts. Section 4 is the
orchestrator's other half, `kill_tree`: a parent AND its child, killed by pid.

Every listener is on an ephemeral port at 127.0.0.1, so this file runs beside a
live session's stack, like test_preflight_owner.py. No vault, no client.

    python toolkit/harness/test_childjob.py
"""

import os
import socket
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402
import childjob  # noqa: E402

# How long a dead parent's server may keep its listener. The kernel's kill is
# effectively immediate (MEASURED well under a second on the first green run);
# the slack is for a loaded machine running the suite in a pool. The known-bad
# arm waits the whole of it, so it is also what that arm costs.
DEADLINE = 5.0

# MEASURED 2026-09-24: 27 checks on the first green run, on the machine the
# incident happened on. Nothing in this file skips on a Windows machine, so the
# floor is the whole count. SABOTAGED the same day -- `Stack.start`'s adopt()
# replaced by `pass` -- and 4 went red: section 2's membership, section 3's
# membership, its listener-gone and its process-dead; the known-bad arm and
# sections 1, 4 and 5 stayed green, as they must (none of them reads Stack).
# 27 -> 28 the same day: a closed job answers None for membership (holds()
# guarded; without the guard IsProcessInJob(NULL) asks "any job" -- red when
# the guard is removed).
LEDGER = checks.Ledger("child job", floor=28)
check = checks.adopt_named(LEDGER)

HOST = "127.0.0.1"


def free_port(host=HOST):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, 0))
    port = s.getsockname()[1]
    s.close()
    return port


def listening(port, host=HOST):
    """pids holding LISTEN on host:port, read off the OS's TCP table."""
    import portclaim
    return {r["pid"] for r in portclaim.listeners_on(port, host)}


def wait_for(pred, seconds):
    """Poll `pred` until true or `seconds` pass; returns (result, elapsed)."""
    t0 = time.monotonic()
    while True:
        got = pred()
        if got or time.monotonic() - t0 >= seconds:
            return got, time.monotonic() - t0
        time.sleep(0.05)


def spawn(*args):
    """This file, in one of its stand-in roles, with its stdout piped to us."""
    return subprocess.Popen([sys.executable, "-u", __file__] + list(args),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace")


def read_tagged(proc, tag, seconds=30):
    """The first stdout line starting `tag`, its remainder; None on exit/timeout.

    Read on a thread so a stand-in that hangs cannot hang the test.
    """
    import threading
    box = {}

    def reader():
        for line in proc.stdout:
            if line.startswith(tag):
                box["v"] = line[len(tag):].strip()
                return
            box.setdefault("seen", []).append(line.rstrip())
    t = threading.Thread(target=reader, daemon=True)
    t.start()
    t.join(seconds)
    if "v" not in box:
        print("    stand-in said: " + " | ".join(box.get("seen", [])[-8:]))
    return box.get("v")


def reap(*pids):
    """Kill whatever a failed or known-bad arm left behind. Never a check."""
    for pid in pids:
        if pid and childjob.alive(pid):
            childjob.kill_tree(pid)


# ----------------------------------------------------------- stand-in roles --

def role_server(host, port):
    """A server that binds, listens and then says NOTHING, like an idle authsrv.

    Silent on purpose: the webgate in the incident died on its own (a broken
    stdout pipe, likely), and a stand-in that printed would die the same way in
    the known-bad arm and make the orphan look handled.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((host, int(port)))
    s.listen(1)
    print("listening", flush=True)
    while True:
        time.sleep(60)


def role_parent(host, port, arm):
    """The REAL session.Stack over one stand-in server; READY <server pid>.

    arm "job" is session.py as shipped. arm "nojob" swaps KillOnClose for one
    that refuses, so Stack.start takes its own no-job path (and prints its
    warning) -- the defect as it stood before 2026-09-24.
    """
    import session
    if arm == "nojob":
        class Refused:
            def __init__(self):
                raise OSError("disabled: the known-bad arm")
        session.childjob.KillOnClose = Refused
    spec = [("standin", host, int(port),
             [sys.executable, "-u", __file__, "--role-server", host, str(port)])]
    stack = session.Stack(spec, logdir=tempfile.mkdtemp(prefix="childjob_"))
    stack.start(timeout=20)
    pid = stack.procs["standin"].pid
    print(f"READY {pid} {'held' if stack.job and stack.job.holds(pid) else 'free'}",
          flush=True)
    while True:                        # until the test kills us from outside
        time.sleep(60)


def role_tree():
    """A parent with one sleeping child and no job at all; TREE <child pid>."""
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
    print(f"TREE {child.pid}", flush=True)
    while True:
        time.sleep(60)


# ------------------------------------------------------------------ checks --

def test_kernel_rule():
    print("\n1. the job's own rule: closing the handle kills the adopted, only them")
    job = childjob.KillOnClose()
    check("a kill-on-close job is created", bool(job.handle))
    sleep = [sys.executable, "-c", "import time; time.sleep(600)"]
    a = subprocess.Popen(sleep)
    b = subprocess.Popen(sleep)
    try:
        job.adopt(a.pid)
        check("the adopted child is in THIS job", job.holds(a.pid) is True)
        check("and its sibling, not adopted, is not -- the control",
              job.holds(b.pid) is False)
        job.close()
        dead, took = wait_for(lambda: a.poll() is not None, DEADLINE)
        check("closing the job's last handle kills the adopted child", dead,
              f"{took:.2f}s")
        check("and leaves the sibling alive", b.poll() is None)
        check("a closed job answers None for membership, never 'any job's' bool",
              job.holds(b.pid) is None)
        refused = None
        try:
            childjob.KillOnClose().adopt(a.pid)
        except OSError as exc:
            refused = str(exc)
        check("adopting a pid that has exited raises, naming the step",
              refused is not None and "pid" in refused, refused or "no raise")
    finally:
        for p in (a, b):
            if p.poll() is None:
                p.kill()
                p.wait(5)


def test_stack_adopts():
    print("\n2. Stack.start() adopts every server it starts")
    import session
    port = free_port()
    spec = [("standin", HOST, port,
             [sys.executable, "-u", __file__, "--role-server", HOST, str(port)])]
    stack = session.Stack(spec, logdir=tempfile.mkdtemp(prefix="childjob_"))
    stack.start(timeout=20)
    try:
        pid = stack.procs["standin"].pid
        check("the stand-in server is up, its listener proven by pid (Stack.start)",
              pid in listening(port))
        check("Stack holds a kill-on-close job", stack.job is not None
              and bool(stack.job.handle))
        check("and the server is in it", stack.job.holds(pid) is True)
    finally:
        stack.stop()
    gone, took = wait_for(lambda: not listening(port), DEADLINE)
    check("Stack.stop() still stops it the ordinary way", gone, f"{took:.2f}s")


def parent_killed(arm):
    """Run one arm of section 3.

    Returns (said, pid, up, gone, took, alive_after): the READY line, the
    server's pid, whether it listened before the kill, whether the listener
    was gone within DEADLINE and how long that took, and whether the server
    process was still running at that moment -- read BEFORE the cleanup below
    reaps a known-bad arm's orphan, or the reap would answer for it.
    """
    port = free_port()
    parent = spawn("--role-parent", HOST, str(port), arm)
    pid = None
    try:
        said = read_tagged(parent, "READY ")
        if not said:
            return None, None, None, None, None, None
        pid = int(said.split()[0])
        up = pid in listening(port)
        parent.kill()                  # TerminateProcess: no finally runs
        parent.wait(10)
        gone, took = wait_for(lambda: not listening(port), DEADLINE)
        return said, pid, up, gone, took, childjob.alive(pid)
    finally:
        if parent.poll() is None:
            parent.kill()
        reap(pid)


def test_parent_killed():
    print("\n3. TerminateProcess on the parent: the server's listener goes with it")
    said, pid, up, gone, took, live = parent_killed("job")
    check("the stand-in parent brought its server up (treatment arm)", said is not None,
          said or "no READY line")
    check("  with the server in the job before the kill",
          bool(said) and said.endswith("held"), said)
    check("  and listening, owned by that pid, before the kill", bool(up))
    check("THE FIX: the listener is gone within the deadline after the parent dies",
          bool(gone), f"{took:.2f}s of {DEADLINE}s" if took is not None else "")
    check("  and the server process itself is dead", live is False)
    print("   ...and the known-bad arm, the job disabled (this is the defect):")
    said, pid, up, gone, took, live = parent_killed("nojob")
    check("the stand-in parent brought its server up (known-bad arm)", said is not None,
          said or "no READY line")
    check("  with the server OUTSIDE any job of the Stack's",
          bool(said) and said.endswith("free"), said)
    check("  and listening before the kill", bool(up))
    check("KNOWN-BAD: without the job the listener OUTLIVES its parent's death "
          "-- the check above can go red", gone is False,
          f"still listening after {took:.2f}s" if took is not None else "")
    check("  and the orphan was still a live process at the deadline", live is True)


def test_kill_tree():
    print("\n4. kill_tree: the orchestrator's Stop takes the parent AND its children")
    parent = spawn("--role-tree")
    child = None
    try:
        said = read_tagged(parent, "TREE ")
        check("a parent with one child, no job anywhere", said is not None,
              said or "no TREE line")
        child = int(said) if said else None
        check("  both alive before the kill",
              child is not None and childjob.alive(child) and parent.poll() is None)
        ok, detail = childjob.kill_tree(parent.pid)
        check("kill_tree reports success", ok, detail)
        dead, took = wait_for(lambda: parent.poll() is not None
                              and child is not None and not childjob.alive(child),
                              DEADLINE)
        check("  and the parent AND its child are dead", dead, f"{took:.2f}s")
        ok, detail = childjob.kill_tree(parent.pid)
        check("a tree already gone is not a failure (taskkill: not found)", ok, detail)
    finally:
        if parent.poll() is None:
            parent.kill()
        reap(child)


def test_alive():
    print("\n5. alive(), the reading the checks above rest on")
    check("alive() says True of this process", childjob.alive(os.getpid()))
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait(10)
    # Popen still holds the handle, so the pid is not reused: this is the
    # exited-process answer, not the not-found one.
    check("and False of a process that has exited", not childjob.alive(p.pid))


def main():
    if len(sys.argv) > 1:
        role = sys.argv[1]
        if role == "--role-server":
            return role_server(sys.argv[2], sys.argv[3])
        if role == "--role-parent":
            return role_parent(sys.argv[2], sys.argv[3], sys.argv[4])
        if role == "--role-tree":
            return role_tree()
        raise SystemExit(f"unknown role {role!r}")
    if os.name != "nt":
        LEDGER.skip("everything", "Job Objects and taskkill are Windows-only")
        return LEDGER.verdict()
    test_kernel_rule()
    test_stack_adopts()
    test_parent_killed()
    test_kill_tree()
    test_alive()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
