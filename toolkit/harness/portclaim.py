"""Who owns port 6112 and 6113, and whether it is a process from THIS worktree.

Lifted out of `session.py` unchanged. The whole block is one question asked two
ways: the TCP table says which pid is holding an endpoint, and Windows' own
process APIs say whether that pid is one of ours -- and the answer decides
whether `--replace` may stop it. The rule is OWNERSHIP, NOT SPECIES, and the
comments below are why: "is it python" matched a parallel session's LIVE stack
on 2026-08-20 ~23:00 and --replace killed that session's webgate and authsrv
mid-run. One session per worktree means two sessions' servers are identical by
image name, so nothing short of tree-compared-to-tree separates them.

Every comment travels verbatim, including the argtypes scar (a HANDLE truncated
to a 32-bit int silently corrupts every call that receives it back) and the
rationale for reading another process's command line through
NtQueryInformationProcess and splitting it with CommandLineToArgvW rather than
shlex -- the operand is ANOTHER process's argv, so it gets the OS's own quoting
rules and not ours.

ONE WORD OF A MOVED DOCSTRING IS NOW STALE, DELIBERATELY. `this_tree` says "the
one this session.py was loaded from". It is loaded from THIS file now. The
answer is byte-identical -- same directory, so the same nearest `.git` ancestor
-- and `test_preflight_owner.py` still proves that equivalence against
`git rev-parse --show-toplevel`. The line is NOT reworded: this repo has a
recorded incident of rewriting 46 citations for tidiness and reverting all 46,
and a pointer in a header costs less than an edit to the evidence itself.

THE REFERENTS THAT STAYED BEHIND. `main()` is the one caller of `preflight`, and
it hands it the WHOLE spec list un-narrowed (asserted on the syntax tree by
`test_preflight_owner.py`, which is why that call must stay a bare name);
`Stack.start` is the one caller of `listeners_on` outside this file; `--replace`
is `main()`'s flag; and `server_specs()`, named in `this_tree`'s docstring, is
not here either. `session.py` re-exports all eight functions, so every one of
those call sites is the bare name it always was, and so are the seven that
`test_preflight_owner.py` reaches as `session.<name>`.

Standard library plus `tcptable`, and no import of `session.py` (R4): session.py
runs as `__main__`, so importing it back would load a second copy.
"""
import ctypes
import os
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
from tcptable import connections  # noqa: E402


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
# argtypes are not optional: a HANDLE truncated to a 32-bit int silently
# corrupts every call that receives it back. Same scar as drive_client.
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

# Reading a listener's COMMAND LINE, for the --replace ownership test below.
# NtQueryInformationProcess(ProcessCommandLineInformation) answers for any
# same-user process since Win 8.1 and needs only the LIMITED right image_name
# already opens with -- no PEB walk, no third-party dependency, the same pure
# ctypes budget keytap.py runs its cross-process reads on. The split is
# CommandLineToArgvW rather than shlex because the operand is ANOTHER
# process's argv: it gets the OS's own quoting rules, not ours.
ntdll = ctypes.WinDLL("ntdll")
ntdll.NtQueryInformationProcess.argtypes = [
    wintypes.HANDLE, wintypes.ULONG, wintypes.LPVOID, wintypes.ULONG,
    ctypes.POINTER(wintypes.ULONG)]
ntdll.NtQueryInformationProcess.restype = ctypes.c_uint32       # NTSTATUS
shell32 = ctypes.WinDLL("shell32", use_last_error=True)
shell32.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR,
                                       ctypes.POINTER(ctypes.c_int)]
shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
PROCESS_COMMAND_LINE_INFORMATION = 60
STATUS_INFO_LENGTH_MISMATCH = 0xC0000004


class UNICODE_STRING(ctypes.Structure):
    # Buffer as c_void_p, not c_wchar_p: Length is authoritative and excludes
    # the terminator, so the read below is wstring_at(ptr, Length // 2) rather
    # than trusting a NUL that the contract does not promise.
    _fields_ = [("Length", ctypes.c_ushort),
                ("MaximumLength", ctypes.c_ushort),
                ("Buffer", ctypes.c_void_p)]


def listeners_on(port, host=None):
    """LISTEN rows on a port; with host, only rows that would collide there.

    host=None keeps the old port-only reading. With a host, a row matches if
    it is bound to that exact host OR to the 0.0.0.0 wildcard -- a wildcard
    bind owns the port on every alias, so it is never out of the way.
    """
    rows = [c for c in connections()
            if c["state"] == "LISTEN" and c["local"].endswith(f":{port}")]
    if host is None:
        return rows
    return [r for r in rows
            if r["local"] in (f"{host}:{port}", f"0.0.0.0:{port}")]


def image_name(pid):
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return "?"
    try:
        buf = ctypes.create_unicode_buffer(1024)
        n = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
            return buf.value
        return "?"
    finally:
        kernel32.CloseHandle(h)


def cmdline(pid):
    """The process's full command line, or None when it cannot be read.

    None is an ANSWER, not an error state to hide: the caller refuses to stop
    what it cannot identify, so a pid that exited between the table read and
    this call, an access-denied handle and a truncated buffer all land on the
    same safe side.
    """
    h = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    try:
        need = wintypes.ULONG(0)
        st = ntdll.NtQueryInformationProcess(
            h, PROCESS_COMMAND_LINE_INFORMATION, None, 0, ctypes.byref(need))
        if st != STATUS_INFO_LENGTH_MISMATCH or not need.value:
            return None
        buf = ctypes.create_string_buffer(need.value)
        st = ntdll.NtQueryInformationProcess(
            h, PROCESS_COMMAND_LINE_INFORMATION, buf, need.value,
            ctypes.byref(need))
        if st != 0:
            return None
        us = UNICODE_STRING.from_buffer(buf)
        if not us.Buffer or not us.Length:
            return None
        return ctypes.wstring_at(us.Buffer, us.Length // 2)
    finally:
        kernel32.CloseHandle(h)


def argv_of(cmd):
    """Split a Windows command line exactly as the OS would. [] on failure."""
    if not cmd:
        return []
    argc = ctypes.c_int(0)
    p = shell32.CommandLineToArgvW(cmd, ctypes.byref(argc))
    if not p:
        return []
    try:
        return [p[i] for i in range(argc.value)]
    finally:
        kernel32.LocalFree(ctypes.cast(p, wintypes.HLOCAL))


def tree_of(path):
    """The git tree owning `path`: the NEAREST ancestor with a `.git` entry.

    Nearest, not outermost, and that distinction is load-bearing: worktrees
    live UNDER the main checkout (`.claude/worktrees/<name>`), so testing "is
    the path inside my root" by prefix would call every worktree's stack the
    main session's own -- the 2026-08-20 kill again, from a different angle.
    A worktree's `.git` is a FILE (gitdir pointer), the main checkout's a
    directory; os.path.exists answers for both. None when no ancestor
    qualifies.
    """
    d = os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def this_tree():
    """THIS session's tree: the one this session.py was loaded from, which is
    also the tree whose servers server_specs() builds argvs for. Matches
    `git rev-parse --show-toplevel` run beside this file, without shelling out
    -- the test proves that equivalence against git's own answer."""
    return tree_of(os.path.realpath(os.path.abspath(__file__)))


def replace_verdict(cmd, our_tree):
    """(may_stop, listener_tree, why): may --replace stop the python listener
    whose command line is `cmd`?

    The rule is OWNERSHIP, not species. "Is it python" was the whole test
    until 2026-08-20 ~23:00, when it matched a parallel session's live stack
    -- one session per worktree means two sessions' servers are identical by
    image name -- and --replace killed that session's webgate and authsrv
    mid-run. Now the script the command line names must resolve into OUR
    tree, tree compared to tree.

    Everything unprovable refuses: a command line that could not be read, no
    script token in it, a RELATIVE script path (a hand-run three-terminal
    server, started from a shell whose cwd this process cannot see). The
    direction is deliberate -- an over-refusal costs the operator one
    taskkill; the under-refusal cost a parallel session its live stack.
    """
    if not our_tree:
        return (False, None, "THIS tree has no .git ancestor, so ownership "
                             "cannot be proven for anything")
    if not cmd:
        return (False, None, "its command line could not be read")
    scripts = [t for t in argv_of(cmd) if t.lower().endswith((".py", ".pyw"))]
    if not scripts:
        return (False, None, "no python script in its command line")
    script = scripts[0]
    if not os.path.isabs(script):
        return (False, None,
                f"its script path {script!r} is relative -- started from a "
                f"shell whose cwd this pre-flight cannot see")
    their = tree_of(os.path.realpath(script))
    if their is None:
        return (False, None, f"{script} is outside any git tree")
    if os.path.normcase(their) != os.path.normcase(os.path.realpath(our_tree)):
        return (False, their, "it was started from a DIFFERENT tree")
    return (True, their, "")


def preflight(specs, replace=False):
    """Every endpoint free, or a loud exit naming exactly what is in the way.

    Host-aware on purpose: authsrv and gamesrv both use port 6112, at
    different loopback aliases. A port-only match would report each as
    squatting on the other's endpoint. The gamesrv alias (127.0.0.3 by
    default) and every chain hop are in `specs` and get the same check --
    main() hands this the WHOLE list, and the test pins that with a listener
    parked on the alias.

    --replace stops a listener only when THREE things hold: it is python, its
    command line could be read, and the script that command line names lives
    in THIS session's tree (replace_verdict). A refusal prints the other
    listener's tree, because the operator's next move is to coordinate with
    whoever is working THERE, and a pid alone does not say who that is.
    """
    ours = this_tree()
    for name, host, port, _ in specs:
        for row in listeners_on(port, host):
            img = image_name(row["pid"])
            base = os.path.basename(img).lower()
            is_python = base in ("python.exe", "pythonw.exe")
            cmd = cmdline(row["pid"]) if is_python else None
            may_stop, their_tree, why = (replace_verdict(cmd, ours)
                                         if is_python else (False, None, ""))
            if replace and may_stop:
                print(f"pre-flight: stopping stale {name} listener "
                      f"pid {row['pid']} on {row['local']} (this tree's own)")
                os.kill(row["pid"], 15)
                continue
            if not is_python:
                hint = ("not a python server -- REFUSING to touch it; "
                        "stop it yourself")
            elif may_stop:
                hint = ("this tree's own stale listener -- re-run with "
                        "--replace to stop it")
            else:
                hint = (
                    f"python, but NOT provably this tree's: {why}.\n"
                    + (f"  its tree:  {their_tree}\n" if their_tree else "")
                    + (f"  its argv:  {cmd}\n" if cmd else "")
                    + f"  this tree: {ours}\n"
                    f"  A parallel session's LIVE stack looks exactly like a "
                    f"stale one from here\n"
                    f"  (one was killed mid-run 2026-08-20), so --replace "
                    f"refuses it too. Coordinate\n"
                    f"  with that tree's session, or stop the pid yourself")
            raise SystemExit(
                f"{host}:{port} ({name}) is taken by pid {row['pid']} ({img}).\n"
                f"  {hint}.")
    # Verify the kills landed rather than assuming: TerminateProcess is
    # asynchronous and a bind that races the dying listener still fails.
    deadline = time.monotonic() + 5
    while replace and time.monotonic() < deadline:
        if not any(listeners_on(p, h) for _, h, p, _ in specs):
            return
        time.sleep(0.1)
    leftover = [(n, h, p) for n, h, p, _ in specs if listeners_on(p, h)]
    if leftover:
        raise SystemExit(f"pre-flight: endpoints still taken after --replace: {leftover}")
