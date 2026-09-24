"""Children that die with their parent, however the parent ends.

    job = KillOnClose()        # one Windows Job Object, KILL_ON_JOB_CLOSE
    job.adopt(proc.pid)        # this child now dies when our last handle closes
    kill_tree(pid)             # taskkill /T /F: a process and every descendant

WHY THIS EXISTS -- OBSERVED 2026-09-24. The run orchestrator runs `session.py`
as a QProcess. Its Stop was `QProcess.kill()`, and closing the window let the
QProcess destructor do the same: on Windows both are TerminateProcess on
`session.py` ALONE. `session.py` tears its servers down in `Stack.stop()`, from
a `finally` -- which never runs when the process is terminated from outside.
Windows does not kill children with their parent, and under the orchestrator
the servers run as `pythonw.exe`, so there was no console window to notice
either. The owner closed the orchestrator at ~14:35 and two `authsrv.py
--party sandbox --persist` processes, parent gone, kept 6112 bound for hours,
blocking every other worktree's harness launch and `test_handshake.py` --
`session.py --replace` refuses a listener from another tree BY DESIGN
(test_preflight_owner.py), and "the next launch replaces any server still
running", which the orchestrator's Stop message promised, is only true from
the same tree.

THE FIX IS THE OS'S, NOT OURS. A `finally`, an atexit hook and a signal handler
all run inside the process being killed, so none of them survives
TerminateProcess -- and TerminateProcess is exactly what every outside
"stop" on Windows is (Task Manager, a QProcess, a closed terminal's host).
A Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE moves the rule into the
kernel: when the last handle to the job closes, every process in it is
terminated, and a process's handles are closed by the kernel when it dies
however it dies. So the handle is held for the parent's lifetime and NEVER
closed by this module on any normal path: the process exit closes it, and
that close IS the kill. `close()` exists for the test.

WHAT KEEPS THE HANDLE OURS ALONE. `CreateJobObjectW(NULL, ...)` makes a
non-inheritable handle, and `subprocess.Popen` on Python 3.7+ passes children
an explicit handle list (or none) -- so no child holds a handle to its own
job, which would keep the job open after the parent died and defeat the
point. Nested jobs are fine on Windows 8+: a parent that already sits in
somebody else's job (a QProcess host, a terminal) can still create this one.

WHY ADOPT AFTER Popen, NOT CREATE_SUSPENDED. There is a window between the
child starting and `adopt()` in which a grandchild the child spawned would not
be in the job. The servers spawn nothing (no subprocess in authsrv.py or
webgate.py), so the window holds no process to miss; suspending and resuming
would need the primary thread's handle, which Popen closes. If a server ever
starts spawning children, this paragraph is the one to revisit.

WHY `kill_tree` IS HERE TOO. The job covers the servers wherever `session.py`
is stopped from. It does not cover the CLIENT: `session.py` launches Gw.exe as
an ordinary child and closes it with WM_CLOSE on its own teardown, so that
Gw.log survives (drive_client.close_client). An outside Stop kills
`session.py` before that teardown can run, so the orchestrator's Stop and
window close kill the whole tree -- `session.py`, the servers and the client
-- and accept that a client killed this way may lose the tail of Gw.log. A
Stop is an abort.

Standard library only (ctypes + subprocess). Windows-only in effect: on any
other OS `KillOnClose()` raises OSError, which `session.py` reports and runs
on without.
"""
import ctypes
import os
import subprocess
from ctypes import wintypes

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS = 9      # JobObjectExtendedLimitInformation
# The two rights AssignProcessToJobObject documents for the process handle.
PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001
# IsProcessInJob and GetExitCodeProcess, for the test's positive control.
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259

if os.name == "nt":
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # argtypes are not optional: a HANDLE truncated to a 32-bit int silently
    # corrupts every call that receives it back. Same scar as portclaim.py.
    kernel32.CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
    kernel32.CreateJobObjectW.restype = wintypes.HANDLE
    kernel32.SetInformationJobObject.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD]
    kernel32.SetInformationJobObject.restype = wintypes.BOOL
    kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel32.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel32.IsProcessInJob.argtypes = [
        wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]
    kernel32.IsProcessInJob.restype = wintypes.BOOL
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
else:                                                   # pragma: no cover
    kernel32 = None


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [(n, ctypes.c_ulonglong) for n in (
        "ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
        "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [("PerProcessUserTimeLimit", wintypes.LARGE_INTEGER),
                ("PerJobUserTimeLimit", wintypes.LARGE_INTEGER),
                ("LimitFlags", wintypes.DWORD),
                ("MinimumWorkingSetSize", ctypes.c_size_t),
                ("MaximumWorkingSetSize", ctypes.c_size_t),
                ("ActiveProcessLimit", wintypes.DWORD),
                ("Affinity", ctypes.c_size_t),          # ULONG_PTR
                ("PriorityClass", wintypes.DWORD),
                ("SchedulingClass", wintypes.DWORD)]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
    # A wrong layout is not silent: SetInformationJobObject checks the length
    # against the class and fails with ERROR_BAD_LENGTH, which __init__ raises.
    _fields_ = [("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                ("IoInfo", IO_COUNTERS),
                ("ProcessMemoryLimit", ctypes.c_size_t),
                ("JobMemoryLimit", ctypes.c_size_t),
                ("PeakProcessMemoryUsed", ctypes.c_size_t),
                ("PeakJobMemoryUsed", ctypes.c_size_t)]


def _fail(what):
    err = ctypes.get_last_error()
    return OSError(err, f"{what} failed: {ctypes.FormatError(err).strip()} (error {err})")


class KillOnClose:
    """One anonymous Job Object whose processes die when its last handle closes.

    Hold the object for as long as the children should live. There is no
    __del__ on purpose: a garbage-collected wrapper must not be what kills a
    server, so the handle lives until `close()` or the process exit.
    """

    def __init__(self):
        if kernel32 is None:
            raise OSError("Job Objects are Windows-only")
        h = kernel32.CreateJobObjectW(None, None)
        if not h:
            raise _fail("CreateJobObjectW")
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not kernel32.SetInformationJobObject(
                h, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION_CLASS,
                ctypes.byref(info), ctypes.sizeof(info)):
            e = _fail("SetInformationJobObject(KILL_ON_JOB_CLOSE)")
            kernel32.CloseHandle(h)
            raise e
        self.handle = h

    def adopt(self, pid):
        """Put process `pid` in the job. Raises OSError naming the step that failed.

        By pid rather than through Popen's private `_handle`: the caller's Popen
        still holds a handle to the child, so the pid cannot have been reused
        between the spawn and this open.
        """
        if not self.handle:
            raise OSError("the job is closed")
        hp = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid)
        if not hp:
            raise _fail(f"OpenProcess(pid {pid})")
        try:
            if not kernel32.AssignProcessToJobObject(self.handle, hp):
                raise _fail(f"AssignProcessToJobObject(pid {pid})")
        finally:
            kernel32.CloseHandle(hp)

    def holds(self, pid):
        """True/False: is `pid` in THIS job. None when the pid cannot be opened.

        A closed job answers None, never a bool: IsProcessInJob with a NULL job
        asks "is it in ANY job", which is a different question with a True answer
        for every process a terminal or a QProcess host has put in one.
        """
        if not self.handle:
            return None
        hp = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not hp:
            return None
        try:
            res = wintypes.BOOL(False)
            if not kernel32.IsProcessInJob(hp, self.handle, ctypes.byref(res)):
                return None
            return bool(res.value)
        finally:
            kernel32.CloseHandle(hp)

    def close(self):
        """Close the handle -- which KILLS every process still in the job."""
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None


def alive(pid):
    """True while `pid` runs, False once it has exited or cannot be found.

    A pid that cannot be opened reads as gone. That is the right side for the
    one question asked of it (did the child die?) only because the test that
    asks it pairs it with the listener table, which answers independently.
    """
    if kernel32 is None:
        return False
    hp = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not hp:
        return False
    try:
        code = wintypes.DWORD(0)
        if not kernel32.GetExitCodeProcess(hp, ctypes.byref(code)):
            return False
        return code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(hp)


def kill_tree(pid, timeout=15):
    """Force-kill `pid` and every descendant: `taskkill /T /F /PID pid`.

    Returns (ok, detail). ok is True when taskkill killed the tree or found
    nothing left to kill (exit 128, "not found"), False otherwise with its
    own words in detail. taskkill walks the tree by PARENT pid, so call it
    while the root is still alive -- once the root is gone its children are
    nobody's and /T cannot find them (which is the whole reason the servers
    also sit in `session.py`'s job). The binary is named from SystemRoot so
    a stray `taskkill` on PATH is never the one run, and CREATE_NO_WINDOW
    keeps a GUI caller (the orchestrator runs under pythonw) from flashing a
    console.
    """
    exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32",
                       "taskkill.exe")
    try:
        r = subprocess.run([exe, "/T", "/F", "/PID", str(int(pid))],
                           capture_output=True, text=True, errors="replace",
                           timeout=timeout,
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"{type(exc).__name__}: {exc}"
    said = " ".join((r.stdout + " " + r.stderr).split())
    return r.returncode in (0, 128), f"taskkill exit {r.returncode}: {said}"
