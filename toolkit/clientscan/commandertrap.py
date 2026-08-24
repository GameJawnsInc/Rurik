"""Trap the commander-create chain in a live client, to answer the one question
static reading and a memory read both left open.

WHY THIS EXISTS. `studies/heroes/FINDINGS.md` §32 stops the heroes arc at a
single unmeasured fact. The party-window hero button asserts `commander` /
`GmView.cpp(5890)` because no commander object exists for our hero -- §27
MEASURED that, reading the container header out of the live process: `cap=7
count=0`, seven empty slots. But an empty container cannot distinguish

    (a) the event that would create one is never RAISED, from
    (b) it is raised, and the handler's my-id filter REJECTS our entry.

Both leave the container at zero, and four hypotheses have already been killed
by experiment here (`inventoryId` §16, `msg+0x10` §19, the party-cache gate §26,
the subscriber map §28). §26.4 named the instrument that separates them and the
arc never spent it: a trap on `0x008590CA`.

WHAT IT DOES, and what it deliberately does not. It is a debugger: it attaches
with `DebugActiveProcess` and sets EXECUTE breakpoints in the processor's DEBUG
REGISTERS (DR0..DR3), which are per-thread state, not memory. **Nothing is
written into the client.** No `int3` is patched over an instruction, no code
cave is assembled, no DLL is injected, no thread is created in the target. That
matters beyond tidiness: an `int3` patch mutates the very bytes this arc has
been reading, and every address in `studies/heroes/` was measured against the
unmodified image. `CLAUDE.md` carve-out 3 permits a compiler; this did not need
one, which is the cheaper end of the same permission.

THE CHAIN, and every address below is OBSERVED on build 38833 -- disassembled,
with the bytes recorded here and re-verified against the RUNNING process before
a single breakpoint is armed:

    0x00859010  the 0x01C2 worker entry            <- THE CONTROL
    0x008590CA  `push 0x1000011e` -- the raise      (a) above
    0x004E5DE1  dispatch case 93, the handler body
    0x004E5DF2  `cmp [esi+4],eax` -- the my-id filter, WITH BOTH OPERANDS  (b)

THE PREDICTION, stated before the run because a probe with no stated expectation
can be rationalised into agreeing with anything afterwards. `0x00524CC0`
(`GmHeroCommander`, the roster-index search) reaches the get-or-create
`0x00524C40` on BOTH of its exits -- found, via `0x00524D2C` -> `0x00524D1A`,
and NOT-found, via `0x00524D03` -> the `GmHeroCommander:140`
`rosterIndex != (unsigned)-1` assert -> `0x00524D1A`. So if that search had ever
run for our hero a commander would exist whatever the key, and a miss would have
raised its own assert at instance-load time. We see neither. **Therefore the
break is upstream of the search, and the trap should show the chain stopping at
the raise, at the dispatch, or at the filter.** If instead `filter` hits and
PASSES, the prediction is dead and the fault is inside the search -- which is a
result, and a different arc.

THE CONTROL, and it is the §28 lesson wired in rather than written down. §28's
subscriber reader produced a clean, memorable, completely WRONG answer -- "the
commander event has no subscriber" -- and only a control caught it. So: the
worker site MUST hit. If our `0x01C2` never reaches `0x00859010`, the trap
machinery is unproven and NO verdict is given about the sites downstream of it,
because "it never fired" and "we cannot see it fire" look identical from here.

    python toolkit/clientscan/commandertrap.py --wait --seconds 180
    python toolkit/clientscan/commandertrap.py --pid 1234 --sites worker,search,create,notfound

Windows, standard library only (`ctypes`). Read-only against the target's
memory; the only thing it writes anywhere is DR0..DR3/DR7 in the target's own
thread contexts, and it clears them again on detach.
"""
import argparse
import ctypes
import os
import struct
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
sys.path.insert(0, HERE)
import keytap                                                   # noqa: E402

IMAGE_BASE = 0x00400000
# The ASLR slide of the CURRENT target, filled in by main() once the base is
# known. Captures need it to turn a runtime pointer back into a VA they can
# compare against the addresses in this file -- and the need is not
# hypothetical: `create`'s first version compared a SLID return address
# against the static 0x00524FA9 and reported `from the rebuild loop: False`
# for a call that came from exactly there. A capture that silently answers
# the wrong question is the failure this whole module is built against.
SLIDE = 0


def unslide(p):
    """Runtime pointer -> image VA, or None if it is not in the image."""
    if p is None:
        return None
    va = p - SLIDE
    return va if IMAGE_BASE <= va < IMAGE_BASE + 0x01000000 else None

# ---------------------------------------------------------------------------
# Win32
# ---------------------------------------------------------------------------
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

DEBUG_ONLY_THIS_PROCESS = 0x00000002
CREATE_NEW_CONSOLE = 0x00000010

EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
CREATE_PROCESS_DEBUG_EVENT = 3
EXIT_THREAD_DEBUG_EVENT = 4
EXIT_PROCESS_DEBUG_EVENT = 5
LOAD_DLL_DEBUG_EVENT = 6
UNLOAD_DLL_DEBUG_EVENT = 7
OUTPUT_DEBUG_STRING_EVENT = 8
RIP_EVENT = 9

DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001

EXCEPTION_BREAKPOINT = 0x80000003
EXCEPTION_SINGLE_STEP = 0x80000004

# THE WOW64 CODES, and missing them is why the first version of this module
# measured nothing. A 64-bit debugger attached to a 32-bit target does NOT
# receive 0x80000003/0x80000004 for the target's own exceptions -- it receives
# STATUS_WX86_BREAKPOINT and STATUS_WX86_SINGLE_STEP. MEASURED: the control in
# `test_commandertrap.py` 3 armed DR0 correctly (read back: Dr0 = the entry
# point, Dr7 = 1), the processor DID trap on it, and the loop passed the hit
# back to the target as somebody else's exception and reported NO HITS. That is
# precisely the false negative this arc's question is shaped like -- "does this
# instruction ever execute" -- and the control is the only reason it was caught
# here rather than published as a finding about the client.
STATUS_WX86_BREAKPOINT = 0x4000001F
STATUS_WX86_SINGLE_STEP = 0x4000001E

BREAKPOINTS = (EXCEPTION_BREAKPOINT, STATUS_WX86_BREAKPOINT)
SINGLE_STEPS = (EXCEPTION_SINGLE_STEP, STATUS_WX86_SINGLE_STEP)

ERROR_SEM_TIMEOUT = 121

# x86 CONTEXT flags. The WOW64_CONTEXT a 64-bit debugger uses for a 32-bit
# target has the same layout and the same flag values.
CONTEXT_i386 = 0x00010000
CONTEXT_CONTROL = CONTEXT_i386 | 0x0001
CONTEXT_INTEGER = CONTEXT_i386 | 0x0002
CONTEXT_DEBUG_REGISTERS = CONTEXT_i386 | 0x0010
CONTEXT_FULL_READ = CONTEXT_CONTROL | CONTEXT_INTEGER | CONTEXT_DEBUG_REGISTERS

# EFLAGS.RF, the RESUME flag, and it is load-bearing. A hardware EXECUTE
# breakpoint is a FAULT: the #DB is delivered BEFORE the instruction runs, with
# EIP still pointing at it. Intel sets RF in the saved EFLAGS so that the
# resume executes the instruction once without re-trapping -- and MEASURED on
# this path, that does NOT survive the trip out through ContinueDebugEvent.
# The first live run trapped the SAME instruction 32 times in 4 milliseconds,
# identical ESP every time, until the runaway guard disarmed the slot. So the
# debugger has to set RF itself on the way out. Missing this does not look like
# a hang -- the guard caps it -- it looks like "that site executed 32 times".
EFLAGS_RF = 1 << 16

MAX_SLOTS = 4                      # DR0..DR3, and the processor has no more


class WOW64_FLOATING_SAVE_AREA(ctypes.Structure):
    _fields_ = [("ControlWord", wintypes.DWORD),
                ("StatusWord", wintypes.DWORD),
                ("TagWord", wintypes.DWORD),
                ("ErrorOffset", wintypes.DWORD),
                ("ErrorSelector", wintypes.DWORD),
                ("DataOffset", wintypes.DWORD),
                ("DataSelector", wintypes.DWORD),
                ("RegisterArea", ctypes.c_byte * 80),
                ("Cr0NpxState", wintypes.DWORD)]


class WOW64_CONTEXT(ctypes.Structure):
    """The x86 CONTEXT. Dr0..Dr7 first, which is the half this module is for."""
    _fields_ = [("ContextFlags", wintypes.DWORD),
                ("Dr0", wintypes.DWORD), ("Dr1", wintypes.DWORD),
                ("Dr2", wintypes.DWORD), ("Dr3", wintypes.DWORD),
                ("Dr6", wintypes.DWORD), ("Dr7", wintypes.DWORD),
                ("FloatSave", WOW64_FLOATING_SAVE_AREA),
                ("SegGs", wintypes.DWORD), ("SegFs", wintypes.DWORD),
                ("SegEs", wintypes.DWORD), ("SegDs", wintypes.DWORD),
                ("Edi", wintypes.DWORD), ("Esi", wintypes.DWORD),
                ("Ebx", wintypes.DWORD), ("Edx", wintypes.DWORD),
                ("Ecx", wintypes.DWORD), ("Eax", wintypes.DWORD),
                ("Ebp", wintypes.DWORD), ("Eip", wintypes.DWORD),
                ("SegCs", wintypes.DWORD), ("EFlags", wintypes.DWORD),
                ("Esp", wintypes.DWORD), ("SegSs", wintypes.DWORD),
                ("ExtendedRegisters", ctypes.c_byte * 512)]


class EXCEPTION_RECORD(ctypes.Structure):
    pass


EXCEPTION_RECORD._fields_ = [
    ("ExceptionCode", wintypes.DWORD),
    ("ExceptionFlags", wintypes.DWORD),
    ("ExceptionRecord", ctypes.POINTER(EXCEPTION_RECORD)),
    ("ExceptionAddress", ctypes.c_void_p),
    ("NumberParameters", wintypes.DWORD),
    ("ExceptionInformation", ctypes.c_size_t * 15)]


class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("ExceptionRecord", EXCEPTION_RECORD),
                ("dwFirstChance", wintypes.DWORD)]


class CREATE_THREAD_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("hThread", wintypes.HANDLE),
                ("lpThreadLocalBase", ctypes.c_void_p),
                ("lpStartAddress", ctypes.c_void_p)]


class CREATE_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("hFile", wintypes.HANDLE),
                ("hProcess", wintypes.HANDLE),
                ("hThread", wintypes.HANDLE),
                ("lpBaseOfImage", ctypes.c_void_p),
                ("dwDebugInfoFileOffset", wintypes.DWORD),
                ("nDebugInfoSize", wintypes.DWORD),
                ("lpThreadLocalBase", ctypes.c_void_p),
                ("lpStartAddress", ctypes.c_void_p),
                ("lpImageName", ctypes.c_void_p),
                ("fUnicode", wintypes.WORD)]


class EXIT_THREAD_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("dwExitCode", wintypes.DWORD)]


class EXIT_PROCESS_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("dwExitCode", wintypes.DWORD)]


class LOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("hFile", wintypes.HANDLE),
                ("lpBaseOfDll", ctypes.c_void_p),
                ("dwDebugInfoFileOffset", wintypes.DWORD),
                ("nDebugInfoSize", wintypes.DWORD),
                ("lpImageName", ctypes.c_void_p),
                ("fUnicode", wintypes.WORD)]


class UNLOAD_DLL_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("lpBaseOfDll", ctypes.c_void_p)]


class OUTPUT_DEBUG_STRING_INFO(ctypes.Structure):
    _fields_ = [("lpDebugStringData", ctypes.c_void_p),
                ("fUnicode", wintypes.WORD),
                ("nDebugStringLength", wintypes.WORD)]


class RIP_INFO(ctypes.Structure):
    _fields_ = [("dwError", wintypes.DWORD), ("dwType", wintypes.DWORD)]


class DEBUG_EVENT_UNION(ctypes.Union):
    _fields_ = [("Exception", EXCEPTION_DEBUG_INFO),
                ("CreateThread", CREATE_THREAD_DEBUG_INFO),
                ("CreateProcessInfo", CREATE_PROCESS_DEBUG_INFO),
                ("ExitThread", EXIT_THREAD_DEBUG_INFO),
                ("ExitProcess", EXIT_PROCESS_DEBUG_INFO),
                ("LoadDll", LOAD_DLL_DEBUG_INFO),
                ("UnloadDll", UNLOAD_DLL_DEBUG_INFO),
                ("DebugString", OUTPUT_DEBUG_STRING_INFO),
                ("RipInfo", RIP_INFO)]


class DEBUG_EVENT(ctypes.Structure):
    _fields_ = [("dwDebugEventCode", wintypes.DWORD),
                ("dwProcessId", wintypes.DWORD),
                ("dwThreadId", wintypes.DWORD),
                ("u", DEBUG_EVENT_UNION)]


class STARTUPINFOW(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
                ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
                ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
                ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
                ("dwXCountChars", wintypes.DWORD),
                ("dwYCountChars", wintypes.DWORD),
                ("dwFillAttribute", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("wShowWindow", wintypes.WORD),
                ("cbReserved2", wintypes.WORD),
                ("lpReserved2", ctypes.c_void_p),
                ("hStdInput", wintypes.HANDLE),
                ("hStdOutput", wintypes.HANDLE),
                ("hStdError", wintypes.HANDLE)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
                ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD)]


kernel32.DebugActiveProcess.argtypes = [wintypes.DWORD]
kernel32.DebugActiveProcess.restype = wintypes.BOOL
kernel32.DebugActiveProcessStop.argtypes = [wintypes.DWORD]
kernel32.DebugActiveProcessStop.restype = wintypes.BOOL
kernel32.DebugSetProcessKillOnExit.argtypes = [wintypes.BOOL]
kernel32.DebugSetProcessKillOnExit.restype = wintypes.BOOL
kernel32.WaitForDebugEvent.argtypes = [ctypes.POINTER(DEBUG_EVENT),
                                       wintypes.DWORD]
kernel32.WaitForDebugEvent.restype = wintypes.BOOL
kernel32.ContinueDebugEvent.argtypes = [wintypes.DWORD, wintypes.DWORD,
                                        wintypes.DWORD]
kernel32.ContinueDebugEvent.restype = wintypes.BOOL
kernel32.IsWow64Process.argtypes = [wintypes.HANDLE,
                                    ctypes.POINTER(wintypes.BOOL)]
kernel32.IsWow64Process.restype = wintypes.BOOL
kernel32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p,
    wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
    ctypes.POINTER(STARTUPINFOW), ctypes.POINTER(PROCESS_INFORMATION)]
kernel32.CreateProcessW.restype = wintypes.BOOL


class TrapError(Exception):
    """Refusing to arm, or refusing to answer. Never a half-measurement."""


# ---------------------------------------------------------------------------
# DR7
# ---------------------------------------------------------------------------
def dr7_for(n_slots):
    """DR7 with the low `n_slots` LOCAL enables set, each an EXECUTE breakpoint.

    Per slot i: L(i) is bit 2i; the R/W field at bit 16+4i is 00 for
    execute; the LEN field at bit 18+4i is 00, the only legal length for an
    execute breakpoint. So an execute-only DR7 is exactly the enable bits and
    nothing else -- written out because a wrong R/W field does not fail, it
    silently becomes a DATA breakpoint on the same address and fires on the
    instruction FETCH of whatever reads there.
    """
    if not 0 <= n_slots <= MAX_SLOTS:
        raise TrapError(f"{n_slots} breakpoints; the processor has {MAX_SLOTS}")
    v = 0
    for i in range(n_slots):
        v |= 1 << (2 * i)
    return v


# ---------------------------------------------------------------------------
# The debugger
# ---------------------------------------------------------------------------
class HwTrap:
    """Execute breakpoints on up to four addresses, over every thread.

    Deliberately generic: it takes absolute addresses and reports hits. The
    hero-specific knowledge lives in SITES below, and the machinery is
    therefore testable against a process that is not the game -- which is the
    only way to know the machinery works when the game says nothing.
    """

    def __init__(self, on_hit=None, on_create=None, verbose=False):
        self.on_hit = on_hit
        self.on_create = on_create        # (info) -> addresses, for spawn()
        self.verbose = verbose
        self.addrs = []
        self.pid = None
        self.threads = {}                 # tid -> hThread
        self.hproc = None
        self.hits = []
        self.attached = False
        self.spawned = None
        self.exited = False
        self.bp_first = 0            # int3 swallowed -- 1-2 at attach is the OS
        self.bp_second = 0
        self.foreign_steps = 0       # single-steps that were not ours
        self.other_exceptions = 0
        self.arm_failures = 0
        self.resume_failures = 0
        self.hit_counts = {}
        self.max_hits = 32
        self.disarmed = set()
        # slot -> trigger slot. A deferred slot starts in `disarmed` and is
        # armed the moment its trigger fires. See Site.arm_after.
        self.deferred = {}
        self.oneshot = set()
        # Kept apart from `disarmed`, because a slot goes down for two very
        # different reasons and the report must not confuse them: a CAPPED slot
        # hit its ceiling and its count is a floor, while a ONESHOT slot took
        # itself down on purpose and its count is exactly what was asked for.
        # The first version reported a completed oneshot as "counts are floors,
        # not totals", which is false and is the kind of label that gets a
        # correct measurement re-litigated later.
        self.capped = set()
        # Filled by snapshot_coverage() at the end of pump().
        self.coverage = None
        self._getctx = None
        self._setctx = None

    # -- attach / spawn ----------------------------------------------------
    def attach(self, pid):
        if not kernel32.DebugActiveProcess(int(pid)):
            raise TrapError(
                f"DebugActiveProcess({pid}) failed: WinError "
                f"{ctypes.get_last_error()}. A process already being debugged, "
                f"or one this shell may not open, refuses here.")
        self.pid = int(pid)
        self.attached = True
        # So a crash in THIS script does not take the client with it. Without
        # it the client dies the moment the debugger exits, which would turn a
        # tooling bug into a lost run.
        kernel32.DebugSetProcessKillOnExit(False)

    def spawn(self, exe, args=""):
        """Start `exe` under the debugger. For the self-test, not for the game."""
        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(si)
        pi = PROCESS_INFORMATION()
        cmd = ctypes.create_unicode_buffer(f'"{exe}" {args}')
        ok = kernel32.CreateProcessW(None, cmd, None, None, False,
                                     DEBUG_ONLY_THIS_PROCESS | CREATE_NEW_CONSOLE,
                                     None, None, ctypes.byref(si),
                                     ctypes.byref(pi))
        if not ok:
            raise TrapError(f"CreateProcessW({exe}) failed: WinError "
                            f"{ctypes.get_last_error()}")
        self.pid = pi.dwProcessId
        self.attached = True
        self.spawned = pi
        kernel32.DebugSetProcessKillOnExit(False)
        return pi.dwProcessId

    # -- context -----------------------------------------------------------
    def _pick_context_fns(self, hproc):
        """`Wow64*ThreadContext` for a 32-bit target under a 64-bit debugger.

        Getting this wrong does not raise: `GetThreadContext` on a WOW64 thread
        from a 64-bit caller returns the SIXTY-FOUR-bit context, whose Dr0 is at
        a different offset -- so the breakpoints would be written into the wrong
        fields of the wrong structure and simply never fire.
        """
        wow = wintypes.BOOL()
        kernel32.IsWow64Process(hproc, ctypes.byref(wow))
        host64 = sys.maxsize > 2 ** 32
        if wow.value and host64:
            return (kernel32.Wow64GetThreadContext,
                    kernel32.Wow64SetThreadContext, "Wow64")
        return kernel32.GetThreadContext, kernel32.SetThreadContext, "plain"

    def _get_context(self, hthread, flags=CONTEXT_FULL_READ):
        ctx = WOW64_CONTEXT()
        ctx.ContextFlags = flags
        if not self._getctx(hthread, ctypes.byref(ctx)):
            return None
        return ctx

    def _arm(self, hthread):
        ctx = self._get_context(hthread, CONTEXT_DEBUG_REGISTERS)
        if ctx is None:
            return False
        slots = (list(self.addrs) + [0] * MAX_SLOTS)[:MAX_SLOTS]
        for i in self.disarmed:
            if i < MAX_SLOTS:
                slots[i] = 0
        ctx.Dr0, ctx.Dr1, ctx.Dr2, ctx.Dr3 = slots
        ctx.Dr6 = 0
        ctx.Dr7 = 0
        for i, a in enumerate(slots):
            if a:
                ctx.Dr7 |= 1 << (2 * i)      # execute, 1 byte: see dr7_for
        ctx.ContextFlags = CONTEXT_DEBUG_REGISTERS
        ok = bool(self._setctx(hthread, ctypes.byref(ctx)))
        if not ok:
            self.arm_failures += 1
        return ok

    def _arm_all(self):
        return sum(1 for h in self.threads.values() if self._arm(h))

    def armed_now(self, hthread):
        """What DR0..DR3/DR7 ACTUALLY hold. Read back, never assumed.

        `SetThreadContext` returning TRUE is not the same as the breakpoint
        being live -- the WOW64 case above returns success and then discards
        the values.
        """
        ctx = self._get_context(hthread, CONTEXT_DEBUG_REGISTERS)
        if ctx is None:
            return None
        return (ctx.Dr0, ctx.Dr1, ctx.Dr2, ctx.Dr3, ctx.Dr7)

    def snapshot_coverage(self):
        """Per thread: do the debug registers ACTUALLY hold our addresses?

        `armed_now()` has existed since this module was written and was called
        only from its own test -- so no RUN had ever verified its own coverage,
        and `arm_failures == 0` counts only the threads we TRIED. That gap
        matters most for the claim a trap is best at: a site firing ZERO times
        means nothing unless every thread could have fired it. Sampled before
        `detach()` clears the registers, and stored for `_report`.
        """
        want = {a for a in self.addrs if a}
        ok, bad = 0, []
        for tid, h in list(self.threads.items()):
            got = self.armed_now(h)
            if got is None:
                bad.append((tid, "context unreadable"))
                continue
            have = {d for d in got[:MAX_SLOTS] if d}
            missing = sorted(want - have)
            if not missing and got[4]:
                ok += 1
            else:
                bad.append((tid, f"missing {[hex(m) for m in missing]} "
                                 f"dr7=0x{got[4]:X}"))
        self.coverage = {"threads": len(self.threads), "armed": ok,
                         "bad": bad, "want": sorted(want)}
        return self.coverage

    def _disarm_all(self):
        keep, self.addrs = self.addrs, []
        for h in self.threads.values():
            self._arm(h)
        self.addrs = keep

    # -- the loop ----------------------------------------------------------
    def pump(self, seconds, stop_when=None):
        """Run the debug loop for `seconds`. Returns when it expires or exits."""
        deadline = time.time() + seconds
        ev = DEBUG_EVENT()
        while time.time() < deadline and not self.exited:
            if stop_when and stop_when(self):
                break
            ms = max(1, min(400, int((deadline - time.time()) * 1000)))
            if not kernel32.WaitForDebugEvent(ctypes.byref(ev), ms):
                err = ctypes.get_last_error()
                if err == ERROR_SEM_TIMEOUT:
                    continue
                raise TrapError(f"WaitForDebugEvent failed: WinError {err}")
            status = self._dispatch(ev)
            kernel32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, status)
        return self.hits

    def _dispatch(self, ev):
        code = ev.dwDebugEventCode
        if code == CREATE_PROCESS_DEBUG_EVENT:
            info = ev.u.CreateProcessInfo
            self.hproc = info.hProcess
            self._getctx, self._setctx, kind = self._pick_context_fns(info.hProcess)
            if self.verbose:
                print(f"  [attached, {kind} thread contexts]")
            if self.on_create:
                self.addrs = list(self.on_create(self, info))
            self.threads[ev.dwThreadId] = info.hThread
            self._arm(info.hThread)
            if info.hFile:
                kernel32.CloseHandle(info.hFile)
            return DBG_CONTINUE
        if code == CREATE_THREAD_DEBUG_EVENT:
            h = ev.u.CreateThread.hThread
            self.threads[ev.dwThreadId] = h
            self._arm(h)
            return DBG_CONTINUE
        if code == EXIT_THREAD_DEBUG_EVENT:
            self.threads.pop(ev.dwThreadId, None)
            return DBG_CONTINUE
        if code == LOAD_DLL_DEBUG_EVENT:
            # The debugger owns this handle and leaks it otherwise.
            if ev.u.LoadDll.hFile:
                kernel32.CloseHandle(ev.u.LoadDll.hFile)
            return DBG_CONTINUE
        if code == EXIT_PROCESS_DEBUG_EVENT:
            self.exited = True
            return DBG_CONTINUE
        if code == EXCEPTION_DEBUG_EVENT:
            return self._exception(ev)
        return DBG_CONTINUE

    def _exception(self, ev):
        rec = ev.u.Exception.ExceptionRecord
        addr = rec.ExceptionAddress or 0
        first = bool(ev.u.Exception.dwFirstChance)
        if rec.ExceptionCode in BREAKPOINTS:
            # SWALLOW first-chance int3, and this is a deliberate trade rather
            # than laziness. Attaching to a WOW64 process from a 64-bit debugger
            # injects a break-in that can arrive as TWO int3s (the 64-bit ntdll's
            # and the 32-bit one), and passing either back as unhandled kills the
            # client outright -- turning a measurement into a lost run. The cost
            # is that a client int3 would also be stepped over, so both counts
            # are REPORTED: 1-2 at attach is the OS, more than that means this
            # trap altered the client's own behaviour and the run must be read
            # with that in mind. (The asserts this arc chases raise a DIALOG,
            # not an exception -- 16.1 -- so they are not in this path.)
            if first:
                self.bp_first += 1
                # AND RE-ARM. On a WOW64 target the thread is still running
                # 64-bit loader code at CREATE_PROCESS, and the 32-bit context
                # -- debug registers included -- is initialised afterwards, so
                # anything armed at create is WIPED by the time the image runs.
                # MEASURED: test_commandertrap 3 caught exactly this, arming at
                # create and never firing on an entry point that certainly
                # executed. Re-arming at the initial int3 is the fix, and it is
                # harmless on attach, where the DRs already stuck.
                self._arm_all()
                return DBG_CONTINUE
            self.bp_second += 1
            return DBG_EXCEPTION_NOT_HANDLED
        if rec.ExceptionCode not in SINGLE_STEPS:
            self.other_exceptions += 1
            return DBG_EXCEPTION_NOT_HANDLED
        if addr not in self.addrs:
            # Somebody else's single-step. Not ours to consume.
            self.foreign_steps += 1
            return DBG_EXCEPTION_NOT_HANDLED
        h = self.threads.get(ev.dwThreadId)
        ctx = self._get_context(h) if h else None
        slot = self.addrs.index(addr)
        # DR6's low four bits say which slot the processor thinks fired. We
        # identify the site by EIP instead -- the sites are distinct addresses,
        # so EIP is unambiguous and needs no context WRITE to clear the sticky
        # DR6. Reading it anyway makes it a cross-check that can disagree.
        dr6_slot = None
        if ctx is not None:
            for i in range(MAX_SLOTS):
                if ctx.Dr6 & (1 << i):
                    dr6_slot = i
        hit = {"addr": addr, "slot": slot, "tid": ev.dwThreadId,
               "t": time.time(), "ctx": ctx, "dr6_slot": dr6_slot,
               "dr6_agrees": dr6_slot == slot}
        self.hits.append(hit)
        n = self.hit_counts[addr] = self.hit_counts.get(addr, 0) + 1
        if self.on_hit:
            self.on_hit(self, hit)
        # RESUME PAST IT. See EFLAGS_RF: without this the same instruction
        # re-traps on every continue and the site's hit count becomes a count of
        # our own re-entries. DR6 is cleared in the same write, so the sticky
        # bits stay a usable cross-check rather than accumulating.
        if ctx is not None and h:
            ctx.EFlags |= EFLAGS_RF
            ctx.Dr6 = 0
            ctx.ContextFlags = CONTEXT_FULL_READ
            if not self._setctx(h, ctypes.byref(ctx)):
                self.resume_failures += 1
        rearm = False
        if n >= self.max_hits and slot not in self.oneshot:
            # A runaway guard, not an optimisation: if the resume flag were
            # ever not honoured the same instruction would re-trap forever and
            # the client would hang rather than crash. Disarming the slot ends
            # that, and the report says the slot was capped.
            self.disarmed.add(slot)
            self.capped.add(slot)
            rearm = True
        if slot in self.oneshot and slot not in self.disarmed:
            self.disarmed.add(slot)
            rearm = True
        for dep, trigger in self.deferred.items():
            if trigger == slot and dep in self.disarmed:
                self.disarmed.discard(dep)
                rearm = True
        if rearm:
            self._arm_all()
        return DBG_CONTINUE

    def detach(self):
        if not self.attached:
            return
        # BEFORE _disarm_all clears the registers -- this is the last moment
        # the coverage question can be answered, and every consumer calls
        # detach() in a finally block, so putting it here means no run can
        # report hit counts without also reporting whether they were watchable.
        try:
            self.snapshot_coverage()
        except Exception:                                    # noqa: BLE001
            self.coverage = None
        try:
            self._disarm_all()
        except Exception:
            pass
        kernel32.DebugActiveProcessStop(self.pid)
        self.attached = False


# ---------------------------------------------------------------------------
# The sites
# ---------------------------------------------------------------------------
class Site:
    """One trap address, its expected bytes, and what to read when it fires.

    `code` is the whole point of the class. Every address here was measured on
    build 38833, the pin is 38797, and this arc has ALREADY read a 38797 address
    in a 38833 binary once (`studies/heroes/FINDINGS.md` §24). Against the wrong
    build a hardware breakpoint does not error -- it arms on whatever
    instruction happens to live at that address and reports it as the chain.
    Verifying the bytes in the RUNNING process closes that off, and it closes
    off the patched-copy question at the same time, which a build hash alone
    would not.
    """

    def __init__(self, name, va, code, why, capture=None,
                 arm_after=None, oneshot=False):
        self.name, self.va, self.code, self.why = name, va, code, why
        self.capture = capture
        # DEFERRED ARMING, and it is what makes a HOT site measurable at all.
        # `0x0064CA47` sits inside the raise that EVERY UI event in the client
        # passes through; arming it for a whole session would trap thousands of
        # times and slow the client for one answer. Armed only when `arm_after`
        # fires, it is live for the handful of instructions between our own
        # raise and its map lookup, and `oneshot` takes it down again after.
        # The first hit after the trigger is then unambiguously OURS -- the
        # raise is a synchronous call on the same thread, so no other event can
        # interleave between `0x008590CA` and `0x0064CA47`.
        self.arm_after = arm_after
        self.oneshot = oneshot


def _dw(reader, addr, n=1):
    """`n` dwords at `addr` in the target, or None. Never a partial answer."""
    raw = reader(addr, 4 * n)
    if raw is None:
        return None
    return struct.unpack("<%dI" % n, raw)


def _cap_worker(ctx, reader):
    """At `push ebp`, the seven args are still on the stack at [esp+4..].

    `ret 0x1c` = 28 bytes = 7 arguments, and 25.1 decoded which wire field each
    one is. Reading them here checks that decode against the live stack rather
    than against our own sender.
    """
    a = _dw(reader, ctx.Esp, 8)
    if not a:
        return {"esp": ctx.Esp, "args": None}
    return {"this(ecx)": ctx.Ecx, "party_id": a[1], "msg+8 owner": a[2],
            "msg+0xc agent": a[3], "msg+0x10 heroId": a[4],
            "hardcoded0": (a[5], a[6]), "msg+0x14": a[7]}


def _cap_raise(ctx, reader):
    """At `push 0x1000011e`, `ecx` still holds the entry (26.1) and `esi` the
    party id or 0. So this dumps the row the client actually stored."""
    e = _dw(reader, ctx.Ecx, 6)
    return {"entry(ecx)": ctx.Ecx, "esi": ctx.Esi,
            "entry+0 agent": e[0] if e else None,
            "entry+4 owner": e[1] if e else None,
            "entry+8 heroId": e[2] if e else None,
            "entry+0xc": e[3] if e else None,
            "entry+0x10": e[4] if e else None,
            "entry+0x14": e[5] if e else None}


def _cap_case93(ctx, reader):
    """`edi` is the dispatcher's payload; `[edi+4]` is the entry pointer, which
    is what `0x004E5DE7 mov esi,[edi+4]` reads one instruction later. That
    single instruction is what closes 25.4's loose end."""
    p = _dw(reader, ctx.Edi, 2)
    return {"payload(edi)": ctx.Edi,
            "payload+0": p[0] if p else None,
            "payload+4 entry": p[1] if p else None}


def _cap_filter(ctx, reader):
    """THE measurement. `cmp [esi+4],eax`: eax is the my-id from `0x0084DD70`
    and `[esi+4]` is the entry's owner. Both operands, at the instant the
    client compares them -- and 27.2 said reading the my-id needed a TLS walk,
    which is true from outside and irrelevant from in here."""
    e = _dw(reader, ctx.Esi + 4, 2)
    owner = e[0] if e else None
    return {"entry(esi)": ctx.Esi, "my_id(eax)": ctx.Eax,
            "entry+4 owner": owner, "entry+8 heroId": e[1] if e else None,
            "VERDICT": ("PASSES -- falls through to call 0x524cc0"
                        if owner == ctx.Eax else
                        "REJECTS -- jne 0x4e62f4, the handler returns")}


def _cap_posse(ctx, reader):
    """GmPosseRoster's handler, with the message it was handed.

    At `0x005392AC` esi is the message struct (loaded at `0x005392A8`) and
    `[esi+4]` is the switch selector. 36.9 left three possibilities and this
    separates the first two by itself: NO hits means the handler is not
    installed; hits WITHOUT message 9 mean it is installed and never created;
    a message 9 hit would contradict 36.7's census and put the fault elsewhere.
    """
    m = _dw(reader, ctx.Esi + 4, 1)
    v = m[0] if m else None
    return {"message([esi+4])": v,
            "VERDICT": ("MESSAGE 9 -- instance create, the subscribe path"
                        if v == 9 else f"message {v}, not the create path")}


def _cap_gate(ctx, reader):
    """THE GATE on GmPosseRoster's existence. `0x00815E90` resolves the root
    context, takes `ctx[0x2c]` (the same character context 14 read `+0x6BC`
    from) and loads `[+0x67C]` into esi; zero returns 0 and the caller at
    `0x00578BFE` skips installing the posse-roster handler entirely. No handler
    means no `message 9`, no subscribe block, and therefore no roster
    subscriber for 0x1000011E -- which is exactly what 36.7 measured."""
    return {"field ctx[0x2c]+0x67C (esi)": ctx.Esi,
            "bound-holder (edi)": ctx.Edi,
            "VERDICT": ("ZERO -- gate FAILS, GmPosseRoster is never installed"
                        if ctx.Esi == 0 else
                        "non-zero -- gate passes, the roster handler installs")}


def _cap_subscribe(ctx, reader):
    """WHO registers WHAT. `esi` holds the event id (it is stored to the scratch
    slot at `0x0064CDA0` and passed to the lookup by address), and `[ebp+4]` is
    the caller's return address -- so a census here names both the event and the
    code that subscribed to it. 34 could read whether a subscriber EXISTS; this
    reads where it came from."""
    # TWO FRAMES, and the second is the one that answers the question. 36.6:
    # capturing only `[ebp+4]` returned the SAME value for every event --
    # 0x00633C07, inside the subscribe WRAPPER 0x00633BD0 -- because the
    # trapped function is the wrapper's callee, so its return address is the
    # wrapper by construction and identifies nothing. The subscriber is one
    # frame further up: `[[ebp]+4]`. Both are reported so the inner value stays
    # visible as its own control: if `inner` ever varies, this reasoning about
    # the frame layout is wrong and `outer` cannot be trusted either.
    inner = _dw(reader, ctx.Ebp + 4, 1)
    saved = _dw(reader, ctx.Ebp, 1)
    outer = _dw(reader, saved[0] + 4, 1) if saved and saved[0] else None
    return {"event(esi)": ctx.Esi,
            "inner(wrapper)": inner[0] if inner else None,
            "SUBSCRIBER(outer)": outer[0] if outer else None}


def _cap_lookup(ctx, reader):
    """THE subscriber answer, read out of the client's own lookup.

    At `0x0064CA47`, `ebp` is set up and `[ebp+8]` still holds the event id
    (stored back at `0x0064CA3B`), while `eax` is whatever `0x00491F20`
    returned for it. 28 could not walk this map -- its keys hash through
    `0x004920B0` and a plain bucket walk finds nothing -- and this sidesteps
    the whole problem: let the client hash it, and read the answer.
    """
    ev = _dw(reader, ctx.Ebp + 8, 1)
    return {"event(ebp+8)": ev[0] if ev else None,
            "subscribers(eax)": ctx.Eax,
            "VERDICT": ("NO SUBSCRIBER -- takes `je 0x64ca58`, the raise "
                        "returns having called nothing"
                        if ctx.Eax == 0 else
                        "SUBSCRIBED -- falls through to `call 0x64c7d0` "
                        "with the list")}


# Build 38833. Disassembled, not copied from a study: every `code` below is the
# instruction's own bytes as `codescan --dis` printed them.
SITES = {
    "worker": Site(
        "worker", 0x00859010, bytes.fromhex("558bec83ec08"),
        "0x01C2's worker entry -- THE CONTROL. If this never fires, nothing "
        "below it means anything.", _cap_worker),
    "raise": Site(
        "raise", 0x008590CA, bytes.fromhex("681e010010"),
        "`push 0x1000011e` -- the commander event being raised, gated on the "
        "party-cache miss at 0x008590AF (26.2)", _cap_raise),
    "case93": Site(
        "case93", 0x004E5DE1, bytes.fromhex("57e849383e00"),
        "dispatch case 93 -- the handler the raise reaches (25.2)",
        _cap_case93),
    "filter": Site(
        "filter", 0x004E5DF2, bytes.fromhex("394604"),
        "`cmp [esi+4],eax` -- the my-id filter, with BOTH operands",
        _cap_filter),
    # THE BISECT SITE, added 2026-08-23 for an anomaly this file's own verdict
    # refused to believe. A `--hero-late` run reported case93=1 filter=0, and
    # the verdict says that "should be impossible -- they are four
    # instructions apart with no branch between them". Re-read on 38833, that
    # is correct: 0x004E5DE1 `push edi; call 0x8c9630; mov esi,[edi+4]; add
    # esp,4; call 0x84dd70; cmp [esi+4],eax` is straight-line with TWO calls
    # in it. So execution either stopped inside a call or the trap missed the
    # hit, and this site separates those: it is the instruction the FIRST call
    # returns to. case93 hit + postcall miss => 0x8c9630 did not return;
    # case93 + postcall hit + filter miss => 0x84dd70 (the identity getter,
    # which reaches through TLS at 0x0047F660) did not return; all three hit
    # => the earlier miss was the trap, not the client.
    "postcall": Site(
        "postcall", 0x004E5DE7, bytes.fromhex("8b770483c404"),
        "`mov esi,[edi+4]` -- where case 93's first call RETURNS. Bisects a "
        "case93-without-filter run into 'a call did not return' versus 'the "
        "trap missed it'",
        capture=lambda ctx, rd: {"esi(entry) after load": None,
                                 "edi(payload)": ctx.Edi,
                                 "VERDICT": "the first call returned"}),
    # Downstream. Not in the default set because the prediction says the chain
    # stops before them -- so they are the flags a SECOND run uses if it does not.
    "search": Site(
        "search", 0x00524CC0, bytes.fromhex("558bec515356"),
        "GmHeroCommander's roster-index search, which reaches get-or-create on "
        "BOTH exits"),
    "notfound": Site(
        "notfound", 0x00524D06, bytes.fromhex("688c000000"),
        "the `GmHeroCommander:140 rosterIndex != (unsigned)-1` assert -- the "
        "search ran and found no entry"),
    "create": Site(
        "create", 0x00524C40, bytes.fromhex("558bec5153"),
        "get-or-create. If this fires, a commander object exists and 27's "
        "count=0 is about a later teardown, not a create that never ran",
        # WHICH AGENT, and it is the question left after the fix worked.
        # studies/pvpui/FINDINGS.md 20 measured a commander existing for the
        # first time -- count 0 -> 1 -- but `heroCommanderSlot` holds container
        # KEYS, not agent ids, so it cannot say WHOSE. The caller at 0x00524FA3
        # pushes `edi = [rec+8]`, the agent id the rebuild copied out of the
        # party container (11), so the argument here names it directly.
        #
        # At the breakpoint `push ebp` has NOT executed, so [esp] is the return
        # address and [esp+4] is arg0. Both are read: a return address that is
        # not 0x00524FA9 means the call came from somewhere other than the
        # rebuild loop, and then the id is about something else.
        capture=lambda ctx, rd: (lambda w: {
            "return address (VA)": None if not w else unslide(w[0]),
            "from the rebuild loop": None if not w else
                unslide(w[0]) == 0x00524FA9,
            "key (arg0)": None if not w else w[1],
            # NOT an agent id, and the first version of this string said
            # it was. The rebuild passes `[item+8]`, and `agents.py`
            # names item+8 as 0x01C2's `scan_key` (msg+0x10) -- which
            # callers fill with the HERO ID, not an agent id. So a 1 here
            # is hero 1, not the player's agent 1; the two collide on the
            # default rig, which is exactly the trap `--player-number`
            # exists to break.
            "VERDICT": "unreadable stack" if not w else (
                f"the commander is filed under key {w[1]} -- this is "
                f"0x01C2's scan_key (msg+0x10), the value --hero-roster-id "
                f"overrides, NOT an agent id"),
        })(_dw(rd, ctx.Esp, 2))),
    "bulk": Site(
        "bulk", 0x004E5D20, bytes.fromhex("8b1eff37895da8"),
        "dispatch case 90, the bulk activeHeroes scan -- the path that DOES "
        "create commanders. 25.2 says all eight callers of its raiser are UI"),
    "lookup": Site(
        "lookup", 0x0064CA47, bytes.fromhex("85c0740dff75"),
        "`test eax,eax` one instruction after the subscriber-map lookup in the "
        "raise (0x0064CA30). EAX IS THE SUBSCRIBER LIST for the event in "
        "[ebp+8]: zero takes `je 0x64ca58` and the raise returns having called "
        "nothing. This answers 28's question WITHOUT replicating the 0x004920B0 "
        "hash -- the client does the lookup and we read its result.",
        capture=lambda ctx, rd: _cap_lookup(ctx, rd),
        arm_after="raise", oneshot=True),
    # THE SAME QUESTION, ASKED OF THE EVENT THAT ACTUALLY DRIVES THE COMMANDER.
    # `studies/pvpui/FINDINGS.md` §14.3: the rebuild `0x00524E00` has exactly ONE
    # caller, inside GmView's event case 90, selected by exactly one event --
    # `0x10000114`, NOT the `0x1000011E` the heroes arc spent itself on. Run 1
    # (2026-08-17) measured `bulkraise` (0x00858850's entry) firing once while
    # `bulk` (that case) never fired at all, with `worker` green as the control.
    # BOTH branches of 0x00858850 raise 0x10000114 -- the arg1 != 0 path at
    # 0x008588AD below, and the arg1 == 0 path via `mov eax,0x10000114` at
    # 0x008588D1 into the shared tail -- so the entry firing means the event WAS
    # raised. `agents.py:434` sends PARTY_SET_MINE with arg1 = 1, which is this
    # path, so THIS is the site that fires on our wire.
    "raise114": Site(
        "raise114", 0x008588AD, bytes.fromhex("6814010010"),
        "`push 0x10000114` inside 0x00858850, reached from the 0x01B2 "
        "PARTY_SET_MINE handler. The event whose GmView case calls the "
        "commander-model rebuild."),
    "lookup114": Site(
        "lookup114", 0x0064CA47, bytes.fromhex("85c0740dff75"),
        "the same subscriber-map read as `lookup`, armed off `raise114` instead "
        "of `raise`. EAX is the subscriber list for 0x10000114 at the moment we "
        "raise it; zero means raised into nothing, which would explain case 90 "
        "never running without any appeal to ordering.",
        capture=lambda ctx, rd: _cap_lookup(ctx, rd),
        arm_after="raise114", oneshot=True),
    # AND IF IT IS SUBSCRIBED, WHO GOT IT. Run 2 (2026-08-17) measured
    # `lookup114` SUBSCRIBED while `bulk` -- GmView's case for that very event --
    # never fired. Exactly one of three things is then true: the subscriber is
    # not GmView, GmView's dispatch routes 0x10000114 somewhere other than case
    # 90, or `bulk`'s address is not that case body. This site separates them by
    # reading the event id GmView's own event half is entered with.
    #
    # `0x004E366A` is `sub eax, 0x10000007`, the first instruction of the event
    # half of GmView's frame handler 0x004E27D0, so EAX still holds the RAW
    # event id when the breakpoint fires. It is hot -- every UI event GmView
    # receives passes here -- which is why it is deferred behind `raise114` and
    # oneshot: the raise is a synchronous call chain on one thread, so the first
    # entry after it is ours. Same argument `lookup` rests on (§33.6).
    "gmvEvent": Site(
        "gmvEvent", 0x004E366A, bytes.fromhex("2d07000010"),
        "the event half of GmView's frame handler, entered with the raw event "
        "id in EAX. Armed off `raise114`, so it names the event GmView is "
        "handed at the moment we raise 0x10000114.",
        capture=lambda ctx, rd: {
            "event id (eax)": ctx.Eax,
            "is 0x10000114": ctx.Eax == 0x10000114,
            "VERDICT": ("GmView WAS handed 0x10000114 -- so the break is in its "
                        "own dispatch, not in delivery"
                        if ctx.Eax == 0x10000114 else
                        "GmView was handed a DIFFERENT event -- ours went to "
                        "some other subscriber, or not to GmView at all"),
        },
        arm_after="raise114", oneshot=True),
    # THE CENSUS FORM OF THE SAME SITE, and it exists because run 3's oneshot
    # cannot carry the weight the deferred argument gives `lookup`.
    #
    # `lookup` is sound deferred-and-oneshot because `0x0064CA47` sits INSIDE the
    # raise's own synchronous call chain -- the first hit after the trigger is
    # necessarily ours. `0x004E366A` is not: it is only reached if GmView's frame
    # handler is entered for the event at all, so "the next hit was some other
    # event" is consistent with BOTH "GmView never got ours" and "GmView got ours
    # by a path that does not pass here". Heroes §36.7 named GmView's SUBSCRIBER
    # as `0x004ED055`, which is not this function -- so the subscriber callback
    # and the frame-handler event half are two different doors, and a oneshot at
    # one of them cannot speak for the other.
    #
    # Armed for the whole session with a high `--max-hits`, this answers the
    # question the oneshot only gestured at: does 0x10000114 EVER reach GmView's
    # frame handler? Same shape as `lookupany`, and for the same reason.
    "gmvEventAny": Site(
        "gmvEventAny", 0x004E366A, bytes.fromhex("2d07000010"),
        "the event half of GmView's frame handler, armed for the whole session. "
        "A census of every event id GmView's frame dispatch is entered with -- "
        "0x10000114's presence or absence in it is the measurement.",
        capture=lambda ctx, rd: {"event id (eax)": ctx.Eax}),
    # GMVIEW'S OWN SUBSCRIBE OF 0x10000114, TIMESTAMPED AGAINST OUR RAISE.
    #
    # Run 5's `subscribe` census DID find GmView registering 0x10000114 (outer
    # return address 0x004ED03F un-slid, which is this call's return), so §18.1
    # holds: we are on the non-observer branch and GmView takes the event we
    # raise. What the census could not say is WHEN -- it aggregates, and
    # aggregated rows carry no timestamps, while the ordered hit list showed
    # only `worker` and `raise114`, both at +1.710s.
    #
    # This site is the same subscribe, anchored on the `call` so it lands in the
    # ORDERED list. Run it beside `raise114` and the two timestamps answer the
    # only question left: does GmView subscribe before or after we raise.
    #
    # `0x004ED03A` is `call 0x00633BD0` with EAX already holding the computed
    # event id from `add eax, 0x10000114` five instructions earlier, so the
    # capture also re-reads which branch of §18's conditional was taken --
    # making this its own control rather than trusting the static reading.
    "gmvSub114": Site(
        "gmvSub114", 0x004ED03A, bytes.fromhex("e8916b1400"),
        "GmView's CONDITIONAL subscribe call. EAX is the event id it is "
        "registering -- 0x10000114 on the normal branch, 0x1000012B in observer "
        "mode. Timestamped against `raise114`.",
        capture=lambda ctx, rd: {
            "event being subscribed (eax)": ctx.Eax,
            "branch": ("NORMAL -- 0x10000114, the event we raise"
                       if ctx.Eax == 0x10000114 else
                       "OBSERVER -- 0x1000012B, not the event we raise"
                       if ctx.Eax == 0x1000012B else "UNEXPECTED"),
        }),
    "posseMsg": Site(
        "posseMsg", 0x005392AC, bytes.fromhex("8b460483f856"),
        "GmPosseRoster's handler at its switch selector, esi already loaded. "
        "Reads WHICH message the roster handler receives -- the discriminator "
        "for 36.9's surviving possibilities.",
        capture=lambda ctx, rd: _cap_posse(ctx, rd)),
    "posseGate": Site(
        "posseGate", 0x00815EA0, bytes.fromhex("85f67505"),
        "`test esi,esi` inside 0x00815E90, where esi IS ctx[0x2c]+0x67C. This is "
        "the guard at 0x00578BFE that decides whether GmPosseRoster's message "
        "handler is installed at all -- and 36.7 measured that the roster never "
        "subscribes to the commander event despite its window being on screen.",
        capture=lambda ctx, rd: _cap_gate(ctx, rd)),
    "subscribe": Site(
        # ANCHORED ON THE `call`, NOT THE `mov` FIVE BYTES EARLIER, and the
        # reason is a defect this guard caught in itself. `0x0064CDA4` is
        # `mov ecx, 0x00C11BC4` -- an absolute DATA address, which the loader
        # RELOCATES. Live it reads `b9c41be200` = 0x00E21BC4, and
        # 0xE21BC4 - 0xC11BC4 = 0x210000 is exactly the ASLR slide, so the
        # verification refused a site that was perfectly correct. A byte anchor
        # must not contain a relocated absolute address. `call rel32` is
        # PC-relative and therefore identical in the file and in memory, and at
        # this instruction `esi` and `[ebp+4]` hold the same values they held
        # five bytes earlier.
        "subscribe", 0x0064CDA9, bytes.fromhex("e87251e4ff"),
        "the subscriber-map INSERT path: it looks the event up and, when absent, "
        "allocates a list and stores the id (`mov [ebx],esi`). Census it to learn "
        "which UI construction registers 0x1000011E and when -- the question 34.4 "
        "and 35 could not reach by watching the raise. HOT: raise --max-hits.",
        capture=lambda ctx, rd: _cap_subscribe(ctx, rd)),
    "lookupany": Site(
        "lookupany", 0x0064CA47, bytes.fromhex("85c0740dff75"),
        "THE POSITIVE CONTROL for `lookup`, and the same address armed with no "
        "trigger. A reader that only ever prints NO SUBSCRIBER is 28 again, so "
        "this censuses whatever events the client raises on its own and must "
        "show some of them SUBSCRIBED. Hot by construction -- it is capped by "
        "max_hits and the report says so.",
        capture=lambda ctx, rd: _cap_lookup(ctx, rd)),
    "bulkraise": Site(
        "bulkraise", 0x00858850, bytes.fromhex("558bec568bf157"),
        "the function that raises 0x10000114, reached through 0x00856920. If "
        "this never runs, no UI action in our session asks for the scan"),
}

DEFAULT_SITES = ("worker", "raise", "case93", "filter")
CONTROL = "worker"


def wait_for_module(pid, module="Gw.exe", timeout=30.0):
    """The module's runtime base, retried while the process is still mapping.

    `--wait` deliberately grabs the pid the INSTANT the process exists, because
    the whole point is to be armed long before the instance load. A process that
    new has no module list yet, and the toolhelp snapshot fails with
    ERROR_PARTIAL_COPY (299) rather than returning an empty list. MEASURED: the
    first live run died here, having found pid 4220 microseconds after CreateProcess.
    Retrying is the fix; refusing after a timeout keeps it from becoming a
    silent wait.
    """
    last, deadline = None, time.time() + timeout
    while time.time() < deadline:
        try:
            return keytap.module_base(pid, module)
        except keytap.TapError as ex:
            last = ex
            time.sleep(0.2)
    raise TrapError(f"{module} never appeared in pid {pid} within "
                    f"{timeout:.0f}s: {last}")


def verify_sites(pid, sites, module="Gw.exe"):
    """(base, [(site, ok, detail)]). Reads the RUNNING process, not the file."""
    base = wait_for_module(pid, module)
    out = []
    for s in sites:
        if s.code is None:
            out.append((s, None, "no bytes recorded for this site -- unverified"))
            continue
        addr = base + (s.va - IMAGE_BASE)
        got = keytap.read_at(pid, addr, len(s.code))
        if got is None:
            out.append((s, False, f"unreadable at 0x{addr:08X}"))
        elif got != s.code:
            out.append((s, False, f"expected {s.code.hex()} got {got.hex()}"))
        else:
            out.append((s, True, f"0x{addr:08X} = {got.hex()}"))
    return base, out


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def _report(sites, hits, base, out=sys.stdout, trap=None):
    w = out.write
    order = [s.name for s in sites]
    counts = {n: 0 for n in order}
    # A CENSUS SITE IS SUMMARISED, NOT LISTED. A hot address can produce
    # thousands of hits, and printing each one buries the only thing that
    # matters -- how many DISTINCT values were seen. The first control run
    # printed 32 near-identical lines spanning 4ms and looked like a sample of
    # the client's events when it was one event repeated.
    BULK = 12
    bulky = {i for i in range(len(sites))
             if sum(1 for h in hits if h["slot"] == i) > BULK}
    for i in sorted(bulky):
        rows = {}
        for h in hits:
            if h["slot"] != i or not h.get("cap"):
                continue
            # Sequences are coerced, not assumed away. A capture that returns
            # an ARRAY -- compositetrap's slot-cache sites read CpsBase's
            # nine-slot tables -- made this line raise `unhashable type` and
            # took the whole report with it, AFTER a real run had completed:
            # every hit was in memory and none of it reached the page. The
            # report must not be the thing that loses a run.
            key = tuple((k, tuple(v) if isinstance(v, (list, tuple)) else v)
                        for k, v in h["cap"].items()
                        if not isinstance(v, str))
            rows[key] = rows.get(key, 0) + 1
        w("\n" + "=" * 72 + f"\nCENSUS: {order[i]} -- {len(rows)} distinct, "
          f"{sum(rows.values())} hits\n" + "=" * 72 + "\n")
        for key, n in sorted(rows.items(), key=lambda kv: -kv[1]):
            w(f"  x{n:<6} " + "  ".join(
                f"{k}=0x{v:08X}" if isinstance(v, int) else f"{k}={v}"
                for k, v in key) + "\n")

    # COUNTED BEFORE THE SKIP. This loop used to increment `counts` inside
    # the per-hit body, which the bulky-site `continue` skips -- so a run
    # whose sites were ALL summarised printed "TOTALS: cache 0" directly
    # under "CENSUS: cache -- 13 hits". Contradicting itself on the same
    # page is worse than being terse.
    for h in hits:
        name = order[h["slot"]] if h["slot"] < len(order) else "?"
        counts[name] = counts.get(name, 0) + 1

    w("\n" + "=" * 72 + "\nHITS, in order\n" + "=" * 72 + "\n")
    if not hits:
        w("  none\n")
    t0 = hits[0]["t"] if hits else 0
    for h in hits:
        if h["slot"] in bulky:
            continue
        site = sites[h["slot"]]
        w(f"\n  +{h['t'] - t0:7.3f}s  {name:9} "
          f"va 0x{site.va:08X}  tid {h['tid']}\n")
        if not h["dr6_agrees"]:
            w(f"      NOTE: DR6 says slot {h['dr6_slot']}, EIP says "
              f"{h['slot']} -- the cross-check disagrees\n")
        # Decoded AT THE HIT, not here. The first live run decoded at report
        # time, by which point `main`'s finally-block had closed the read handle
        # and the client had exited -- so every captured field came back None
        # and the run recorded no state at all. State belongs to the moment the
        # thread was frozen; anything later is reading a different process.
        for k, v in (h.get("cap") or {}).items():
            if isinstance(v, int):
                w(f"      {k:18} 0x{v:08X}  ({v})\n")
            else:
                w(f"      {k:18} {v}\n")
    w("\n" + "=" * 72 + "\nTOTALS\n" + "=" * 72 + "\n")
    for n in order:
        w(f"  {n:9} {counts.get(n, 0)}\n")
    if trap is not None:
        # Printed every run, not only when it looks wrong: these are the ways
        # this tool could have CHANGED the client rather than watched it.
        w(f"\n  int3 swallowed (first-chance) {trap.bp_first}"
          f"   <- 1-2 is the attach break-in; more means we stepped the "
          f"client over its own\n")
        w(f"  int3 passed on (second-chance) {trap.bp_second}\n")
        w(f"  single-steps not ours          {trap.foreign_steps}\n")
        w(f"  other exceptions passed on     {trap.other_exceptions}\n")
        w(f"  arm failures / resume failures {trap.arm_failures} / "
          f"{trap.resume_failures}\n")
        # COVERAGE, printed every run. A site firing zero times is evidence of
        # absence only if every thread could have fired it, and until
        # 2026-08-23 no run said whether they could.
        cov = getattr(trap, "coverage", None)
        if cov is None:
            w("  DR coverage                    NOT SAMPLED -- a zero hit "
              "count from this run is not evidence of absence\n")
        else:
            w(f"  threads armed and VERIFIED     {cov['armed']} of "
              f"{cov['threads']}\n")
            for tid, why in cov["bad"][:8]:
                w(f"      tid {tid}: {why}\n")
            if len(cov["bad"]) > 8:
                w(f"      ... {len(cov['bad']) - 8} more\n")
        if trap.capped:
            w(f"  SLOTS CAPPED AT max_hits: "
              f"{sorted(order[i] for i in trap.capped)} -- those counts are "
              f"FLOORS, not totals\n")
        done = sorted(order[i] for i in trap.oneshot if i not in trap.capped)
        if done:
            w(f"  one-shot slots, taken down after their hit: {done} -- these "
              f"counts are exactly what was asked for\n")
    return counts


def _verdict(counts, sites, out=sys.stdout):
    """The control gate. 28's lesson, wired in rather than written down."""
    w = out.write
    names = [s.name for s in sites]
    w("\n" + "=" * 72 + "\nVERDICT\n" + "=" * 72 + "\n")
    if CONTROL in names and not counts.get(CONTROL):
        w("  REFUSING TO ANSWER.\n"
          "  The control site `worker` (0x00859010, 0x01C2's own worker) never\n"
          "  fired. Either the server sent no hero-add this run, or this trap\n"
          "  does not see what it thinks it sees. Every site below the control\n"
          "  reads the same either way, so 'the raise never fired' would be\n"
          "  indistinguishable from 'the trap is broken' -- which is exactly the\n"
          "  false reading 28 caught in the subscriber reader.\n")
        return 2
    stops = []
    for n in names:
        stops.append((n, counts.get(n, 0)))
    w("  chain: " + " -> ".join(f"{n}={c}" for n, c in stops) + "\n\n")
    if counts.get(CONTROL) and not counts.get("raise", 1):
        w("  The worker RAN and the raise did NOT. The event is never raised,\n"
          "  so no handler runs and nothing is ever created. 27.2's branch (a).\n")
    elif counts.get("raise") and not counts.get("case93", 1):
        w("  The raise RAN and case 93 did NOT. The event is raised into\n"
          "  nothing -- which is 28's subscriber question, answered by trap\n"
          "  rather than by walking a map we could not read.\n")
    elif counts.get("case93") and not counts.get("filter", 1):
        w("  Case 93 ran and the filter site did not. There is no BRANCH\n"
          "  between them -- but there are two CALLS, and this verdict used\n"
          "  to say the gap was impossible and to suspect the trap.\n"
          "  MEASURED 2026-08-23: the trap was right and that reading was\n"
          "  wrong. Case 93's first call (0x8c9630) forwards the event to the\n"
          "  SkillListContext singleton (ecx = 0x10886d0, then 0x8d2500),\n"
          "  whose OWN my-id test passes and calls 0x8d26d0, which ASSERTS\n"
          "  `SKILL_LIST_USERS != skillListUser` at 0x8d270a\n"
          "  (GmCtlSkListContext.cpp:574). The client raises its crash dialog\n"
          "  there, so the call never returns and the two later sites never\n"
          "  execute. Check the session log for that assert before doubting\n"
          "  the instrument; add --sites ...,postcall to see which of the two\n"
          "  calls swallowed the thread.\n")
    elif counts.get("filter"):
        w("  The filter RAN. Its two operands are printed above and they are\n"
          "  the answer: equal means the chain continues into 0x524cc0 and the\n"
          "  fault is downstream (re-run with --sites worker,search,notfound,\n"
          "  create); unequal means 27.2's branch (b), the my-id filter rejects.\n")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pid", type=int, default=None)
    ap.add_argument("--wait", action="store_true",
                    help="wait for a Gw.exe to appear and attach to it. Start "
                         "this BEFORE the harness so the attach lands well "
                         "before the instance load.")
    ap.add_argument("--seconds", type=float, default=180.0,
                    help="how long to hold the debug loop open")
    ap.add_argument("--max-hits", type=int, default=32,
                    help="per-slot ceiling before the slot is disarmed "
                         "(default 32). RAISE IT for a census site: 32 hits of "
                         "a hot address can all land inside one 4ms burst of a "
                         "single event, which looks like a sample and is not.")
    ap.add_argument("--sites", default=",".join(DEFAULT_SITES),
                    help=f"up to {MAX_SLOTS} of: {', '.join(SITES)}")
    ap.add_argument("--out", default=None, help="also write the report here")
    a = ap.parse_args(argv)

    want = [s.strip() for s in a.sites.split(",") if s.strip()]
    for n in want:
        if n not in SITES:
            raise SystemExit(f"no such site {n!r}; have {', '.join(SITES)}")
    if len(want) > MAX_SLOTS:
        raise SystemExit(f"{len(want)} sites; the processor has {MAX_SLOTS} "
                         f"debug registers. Split the run.")
    sites = [SITES[n] for n in want]

    import commanderpeek
    pid = a.pid
    if pid is None:
        t_end = time.time() + (120 if a.wait else 0)
        while True:
            pids = commanderpeek.find_client_pids()
            if pids:
                if len(pids) > 1:
                    raise SystemExit(
                        f"{len(pids)} clients running {pids}. Refusing to guess "
                        f"which one -- pass --pid. Two clients is how a run "
                        f"measures the wrong process.")
                pid = pids[0]
                break
            if time.time() >= t_end:
                raise SystemExit("no Gw.exe. Start the session, or --wait.")
            time.sleep(0.25)

    print(f"pid {pid}")
    base, checks = verify_sites(pid, sites)
    global SLIDE
    SLIDE = base - IMAGE_BASE
    print(f"Gw.exe base 0x{base:08X}  (image base 0x{IMAGE_BASE:08X}, "
          f"slide 0x{base - IMAGE_BASE:X})")
    bad = []
    for s, ok, detail in checks:
        mark = {True: "ok  ", False: "BAD ", None: "??  "}[ok]
        print(f"  {mark}{s.name:9} va 0x{s.va:08X}  {detail}")
        if ok is False:
            bad.append(s.name)
    if bad:
        raise SystemExit(
            f"\nREFUSING to arm: {', '.join(bad)} do not hold the instruction "
            f"bytes\nrecorded for them. These addresses were measured on build "
            f"38833; a hardware\nbreakpoint on the wrong build does not error, "
            f"it arms on whatever is there\nand reports it as the chain.")

    reader_h = keytap.open_read(pid)

    def reader(addr, size):
        return keytap.read_handle(reader_h, addr, size)

    def on_hit(trap, hit):
        site = sites[hit["slot"]]
        if site.capture and hit["ctx"] is not None:
            hit["cap"] = site.capture(hit["ctx"], reader)
        # flush: a run of this thing is minutes long and its output is normally
        # redirected, where Python block-buffers and the live progress a watcher
        # wants arrives only at exit.
        print(f"  HIT {site.name} (0x{site.va:08X}) tid {hit['tid']}"
              + (f"  {hit['cap'].get('VERDICT', '')}" if hit.get("cap") else ""),
              flush=True)

    trap = HwTrap(on_hit=on_hit, verbose=True)
    trap.max_hits = a.max_hits
    trap.addrs = [base + (s.va - IMAGE_BASE) for s in sites]
    for i, s in enumerate(sites):
        if s.oneshot:
            trap.oneshot.add(i)
        if s.arm_after:
            if s.arm_after not in want:
                raise SystemExit(
                    f"site {s.name!r} arms after {s.arm_after!r}, which is not "
                    f"in this run's site list -- it would never arm, and a site "
                    f"that never arms reports the same silence as a real "
                    f"negative.")
            trap.deferred[i] = want.index(s.arm_after)
            trap.disarmed.add(i)          # starts down; the trigger raises it
            print(f"  {s.name} is DEFERRED: armed when {s.arm_after} fires"
                  + (", one shot" if s.oneshot else ""))
    trap.attach(pid)
    print(f"attached; armed {len(sites)} execute breakpoints, holding "
          f"{a.seconds:.0f}s", flush=True)
    try:
        trap.pump(a.seconds)
    except KeyboardInterrupt:
        print("\ninterrupted")
    finally:
        trap.detach()
        kernel32.CloseHandle(reader_h)
        print("detached, debug registers cleared")

    counts = _report(sites, trap.hits, base, trap=trap)
    rc = _verdict(counts, sites)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            _report(sites, trap.hits, base, out=fh, trap=trap)
            _verdict(counts, sites, out=fh)
        print(f"\nwritten to {a.out}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
