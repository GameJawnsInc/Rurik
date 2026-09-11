"""A generic Win32 hardware-breakpoint debugger: DR0..DR3 arming, WOW64 context
selection, the debug-event pump, thread adoption, coverage sampling, live byte
verification of sites, and the run report.

Split out of `commandertrap.py` on 2026-09-11, VERBATIM -- every line below,
comments included, is the line that stood there. Nothing here knows what it is
looking at: it takes absolute addresses and reports hits, which is what lets
the same machinery serve `commandertrap.py`'s commander chain and
`compositetrap.py`'s composite pipeline, and what lets it be tested against a
process that is not the game.

POINTER, because two moved docstrings name a table that did not move.
`HwTrap`'s and `Site`'s docstrings say `SITES below`; after the 2026-09-11
split those tables live in each consumer -- `commandertrap.py` and
`compositetrap.py`.

`SLIDE` HAS EXACTLY ONE OWNER AND IT IS THIS MODULE OBJECT. `unslide` reads it
and the consumers WRITE it, through the module: `commandertrap.main()` does
`hwtrap.SLIDE = base - IMAGE_BASE` and `compositetrap.py` does `ct.SLIDE = ...`
against the same object. A `from hwtrap import SLIDE` would bind a COPY that
stays 0 forever while the real one moves, and `unslide` would then answer with
un-slid VAs silently -- which is exactly the failure the comment on `SLIDE`
below exists to prevent, arriving by a new route.

Windows, standard library only (`ctypes`). Read-only against the target's
memory; the only thing it writes anywhere is DR0..DR3/DR7 in the target's own
thread contexts, and it clears them again on detach.
"""
import ctypes
import os
import struct
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
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

# THREAD ENUMERATION. Attaching to a RUNNING process gave us one thread, and a
# hardware breakpoint is per-thread state, so the rest were blind spots that
# looked like quiet code. Toolhelp is the ground truth the debug loop is not.
TH32CS_SNAPTHREAD = 0x00000004
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value
#: GET_CONTEXT | SET_CONTEXT | QUERY_INFORMATION -- exactly what arming needs.
THREAD_DR_ACCESS = 0x0008 | 0x0010 | 0x0040


class THREADENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD),
                ("cntUsage", wintypes.DWORD),
                ("th32ThreadID", wintypes.DWORD),
                ("th32OwnerProcessID", wintypes.DWORD),
                ("tpBasePri", ctypes.c_long),
                ("tpDeltaPri", ctypes.c_long),
                ("dwFlags", wintypes.DWORD)]


kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Thread32First.argtypes = [wintypes.HANDLE,
                                   ctypes.POINTER(THREADENTRY32)]
kernel32.Thread32First.restype = wintypes.BOOL
kernel32.Thread32Next.argtypes = [wintypes.HANDLE,
                                  ctypes.POINTER(THREADENTRY32)]
kernel32.Thread32Next.restype = wintypes.BOOL
kernel32.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenThread.restype = wintypes.HANDLE


class TrapError(Exception):
    """Refusing to arm, or refusing to answer. Never a half-measurement."""


# ---------------------------------------------------------------------------
# DR7
# ---------------------------------------------------------------------------
#: R/W field values (DR7 bits 16+4i). 00 execute, 01 WRITE, 11 read-or-write.
RW_BITS = {"x": 0b00, "w": 0b01, "rw": 0b11}
#: LEN field values (DR7 bits 18+4i). A 4-byte watch needs a 4-ALIGNED address.
LEN_BITS = {1: 0b00, 2: 0b01, 4: 0b11}


def dr7_for(n_slots, kinds=None, sizes=None):
    """DR7 with the low `n_slots` LOCAL enables set.

    Per slot i: L(i) is bit 2i; the R/W field at bit 16+4i selects execute
    (00) or WRITE (01); the LEN field at bit 18+4i is 00 for execute -- the
    only legal length -- and 11 for a four-byte watch. So an execute-only DR7
    is exactly the enable bits and nothing else. That was written out because
    a wrong R/W field does not fail, it silently becomes a DATA breakpoint on
    the same address; `kinds` now makes that the deliberate case rather than
    the accident, and the same sentence still names the failure mode.
    """
    if not 0 <= n_slots <= MAX_SLOTS:
        raise TrapError(f"{n_slots} breakpoints; the processor has {MAX_SLOTS}")
    kinds = list(kinds or []) + ["x"] * n_slots
    sizes = list(sizes or []) + [4] * n_slots
    v = 0
    for i in range(n_slots):
        v |= 1 << (2 * i)
        k = kinds[i] or "x"
        if k == "x":
            continue                      # R/W = 00, LEN = 00
        if k not in RW_BITS:
            raise TrapError(f"unknown breakpoint kind {k!r}; "
                            f"have {', '.join(sorted(RW_BITS))}")
        sz = sizes[i]
        if sz not in LEN_BITS:
            raise TrapError(f"{sz}-byte watchpoint; x86 allows 1, 2 or 4")
        v |= RW_BITS[k] << (16 + 4 * i)
        v |= LEN_BITS[sz] << (18 + 4 * i)
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
        # Filled by snapshot_coverage() at attach, and AGAIN at the end of
        # pump(). Two samples, because they answer different questions: the
        # first says the run started covered, the second says it STAYED
        # covered. A run can pass the first and lose its registers at hit one
        # -- which is exactly what the resume path did to the row watch -- and
        # an attach-time sample reads "10 of 10" all the way through.
        self.coverage = None
        self.coverage_end = None
        self.adopted = None       # (threads the process had, newly armed)
        self._opened = []         # thread handles WE opened, ours to close
        # Per slot, parallel to `addrs`: "x" execute, "w" write-watch; and the
        # watch length in bytes. A watch's address is not known until the
        # object it lives in exists, so `arm_watch` fills it mid-run.
        self.kinds = []
        self.sizes = []
        # slot -> [still live, GONE], counted at every hit AFTER arming.
        self.watch_recheck = {}
        # slot -> {(dr_value, dr7): n}, sampled when a watch reads as GONE
        self.watch_seen = {}
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

    def dr_state(self):
        """(Dr0, Dr1, Dr2, Dr3, Dr7) for the CURRENTLY armed set.

        Built per ENABLED slot rather than through dr7_for's contiguous
        `n_slots`, because a disarmed slot in the middle must stay off while
        the ones after it stay on. `dr7_for` keeps the encoding documented and
        tested; this is the same encoding applied to a sparse set.
        """
        slots = (list(self.addrs) + [0] * MAX_SLOTS)[:MAX_SLOTS]
        kinds = (list(self.kinds) + ["x"] * MAX_SLOTS)[:MAX_SLOTS]
        sizes = (list(self.sizes) + [4] * MAX_SLOTS)[:MAX_SLOTS]
        for i in self.disarmed:
            if i < MAX_SLOTS:
                slots[i] = 0
        dr7 = 0
        for i, a in enumerate(slots):
            if not a:
                continue
            k = kinds[i] or "x"
            dr7 |= 1 << (2 * i)
            if k != "x":
                dr7 |= RW_BITS[k] << (16 + 4 * i)
                dr7 |= LEN_BITS[sizes[i]] << (18 + 4 * i)
        return tuple(slots) + (dr7,)

    def _arm(self, hthread):
        ctx = self._get_context(hthread, CONTEXT_DEBUG_REGISTERS)
        if ctx is None:
            return False
        d = self.dr_state()
        ctx.Dr0, ctx.Dr1, ctx.Dr2, ctx.Dr3 = d[:4]
        ctx.Dr6 = 0
        ctx.Dr7 = d[4]
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

    def arm_watch(self, slot, address, size=4):
        """Point `slot` at a DATA WRITE watchpoint on `address`, mid-run.

        The address of a row inside a heap object cannot be known before the
        object exists, so this is called from an `on_hit` handler -- where the
        process is frozen inside a debug event and the contexts are safe to
        write. Returns (ok, why).

        REFUSES an unaligned address instead of arming it: x86 requires a
        4-byte watch to sit on a 4-byte boundary, and a misaligned DR does not
        fail, it watches the wrong bytes and reports silence.
        """
        if not 0 <= slot < MAX_SLOTS:
            return False, f"slot {slot} outside DR0..DR{MAX_SLOTS - 1}"
        if size not in LEN_BITS:
            return False, f"{size}-byte watch; x86 allows 1, 2 or 4"
        if address % size:
            return False, (f"0x{address:08X} is not {size}-byte aligned -- a "
                           f"misaligned watch reports silence, it does not "
                           f"error")
        while len(self.addrs) <= slot:
            self.addrs.append(0)
        while len(self.kinds) <= slot:
            self.kinds.append("x")
        while len(self.sizes) <= slot:
            self.sizes.append(4)
        self.addrs[slot] = address
        self.kinds[slot] = "w"
        self.sizes[slot] = size
        self.disarmed.discard(slot)
        n = self._arm_all()
        # VERIFY, do not assume. This module's own `armed_now` docstring says
        # SetThreadContext can return TRUE on a WOW64 target and discard the
        # values -- so a watch that silently never took is indistinguishable
        # from a write that never happened, which is the entire question.
        live = 0
        want_rw = RW_BITS["w"] << (16 + 4 * slot)
        for h in self.threads.values():
            got = self.armed_now(h)
            if got is None:
                continue
            if got[slot] == address and (got[4] & (1 << (2 * slot))) \
                    and (got[4] & (0b11 << (16 + 4 * slot))) == want_rw:
                live += 1
        self.watching = dict(getattr(self, "watching", {}))
        self.watching[slot] = (address, size, n, live)
        if not live:
            return False, (f"armed {size} bytes at 0x{address:08X} on {n} "
                           f"thread(s) but VERIFIED on none -- the debug "
                           f"registers did not take, so a zero hit count "
                           f"here would mean nothing")
        return True, (f"watching {size} bytes at 0x{address:08X}: armed {n} "
                      f"thread(s), VERIFIED live on {live}")

    def adopt_existing_threads(self):
        """Arm every thread the process ALREADY has, a few events EARLY.

        BELT AND BRACES, NOT A BUG FIX -- and this docstring used to say
        otherwise, so read the correction before trusting either version.

        It was added on the strength of "after attaching to a running client,
        `self.threads` held **one** thread", and that number was sampled inside
        the CREATE_PROCESS handler -- the FIRST debug event after attach. One
        thread at that instant is what you see WHETHER OR NOT the OS goes on to
        deliver a CREATE_THREAD event per pre-existing thread. The number could
        not tell "the loop never reports them" from "the loop had not reported
        them yet", and it was read as the first.

        MEASURED 2026-08-23, against a 32-bit WOW64 target -- the client's own
        configuration -- with this function disabled: the loop reached **4 of 4**
        threads on its own and `snapshot_coverage` read every one of them
        holding the armed address. Windows synthesises the CREATE_THREAD events
        on attach. The same run, with this function back on, still reported
        "(5, 4) found, newly armed", because it runs before those events arrive
        -- so that second number is a count of threads the loop had not
        ANNOUNCED yet, never a count of unwatched ones. `test_commandertrap.py`
        section 9 pins both halves.

        What it is still worth: it closes the microseconds between
        ContinueDebugEvent(CREATE_PROCESS) and the synthetic CREATE_THREAD
        events, during which a pre-existing thread is briefly running unarmed,
        and it covers a thread whose CREATE event is missed for any other
        reason. Cheap, and `snapshot_coverage` is what actually makes coverage
        auditable.

        Called from inside the debug loop, where the process is frozen, so the
        contexts can be written safely.
        """
        found, armed = 0, 0
        snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
        if snap == INVALID_HANDLE_VALUE:
            return 0, 0
        try:
            te = THREADENTRY32()
            te.dwSize = ctypes.sizeof(THREADENTRY32)
            ok = kernel32.Thread32First(snap, ctypes.byref(te))
            while ok:
                if te.th32OwnerProcessID == self.pid:
                    found += 1
                    tid = te.th32ThreadID
                    if tid not in self.threads:
                        h = kernel32.OpenThread(THREAD_DR_ACCESS, False, tid)
                        if h:
                            self.threads[tid] = h
                            self._opened.append(h)
                            if self._arm(h):
                                armed += 1
                te.dwSize = ctypes.sizeof(THREADENTRY32)
                ok = kernel32.Thread32Next(snap, ctypes.byref(te))
        finally:
            kernel32.CloseHandle(snap)
        self.adopted = (found, armed)
        return found, armed

    def snapshot_coverage(self, store="coverage"):
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
        cov = {"threads": len(self.threads), "armed": ok,
               "bad": bad, "want": sorted(want)}
        setattr(self, store, cov)
        return cov

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
        # SAMPLE AGAIN, HERE. The attach-time sample cannot see a register lost
        # mid-run, and `detach()` is too late -- by then the client has usually
        # exited and every context reads "unreadable", which looks like a
        # coverage failure and is only a dead process.
        if not self.exited and self.threads:
            try:
                self.snapshot_coverage(store="coverage_end")
            except Exception:                                # noqa: BLE001
                self.coverage_end = None
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
            # The process is FROZEN inside a debug event, so this is the safe
            # moment to take in every thread the debug loop did not report.
            # Attaching to a running client gave us exactly ONE.
            try:
                self.adopt_existing_threads()
                # AND SAMPLE COVERAGE HERE, while the process is alive and
                # frozen. The detach-time sample reads a client that has
                # already exited -- "0 of 1, context unreadable" -- which
                # looks like a coverage failure and is only a dead process.
                self.snapshot_coverage()
            except Exception:                                # noqa: BLE001
                self.adopted = None
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
        h = self.threads.get(ev.dwThreadId)
        ctx = self._get_context(h) if h else None
        slot = self.addrs.index(addr) if addr in self.addrs else None
        if slot is None:
            # A DATA watchpoint traps AFTER the store completes, so EIP is the
            # instruction FOLLOWING the write and is not one of our addresses.
            # DR6 is the only witness, and without this branch the hit would
            # be counted as somebody else's single-step and handed back to the
            # client -- which is what a naive port of the execute path does.
            fired = None
            if ctx is not None:
                for i in range(MAX_SLOTS):
                    if ctx.Dr6 & (1 << i):
                        fired = i
            if (fired is not None and fired < len(self.kinds)
                    and self.kinds[fired] == "w"
                    and fired not in self.disarmed):
                slot = fired
            else:
                # Somebody else's single-step. Not ours to consume.
                self.foreign_steps += 1
                return DBG_EXCEPTION_NOT_HANDLED
        # DR6's low four bits say which slot the processor thinks fired. We
        # identify the site by EIP instead -- the sites are distinct addresses,
        # so EIP is unambiguous and needs no context WRITE to clear the sticky
        # DR6. Reading it anyway makes it a cross-check that can disagree.
        dr6_slot = None
        if ctx is not None:
            for i in range(MAX_SLOTS):
                if ctx.Dr6 & (1 << i):
                    dr6_slot = i
        kind = self.kinds[slot] if slot < len(self.kinds) else "x"
        # For a WATCH the hit's identity is the watched address, and `addr`
        # (EIP) is the far more interesting field: the instruction after the
        # store, i.e. the WRITER. Keeping both under distinct names is the
        # whole point -- conflating them is how a watch reports its own
        # target as its own caller.
        hit = {"addr": self.addrs[slot] if kind == "w" else addr,
               "slot": slot, "kind": kind, "tid": ev.dwThreadId,
               "t": time.time(), "ctx": ctx, "dr6_slot": dr6_slot,
               "dr6_agrees": dr6_slot == slot}
        if kind == "w":
            hit["eip"] = addr
            hit["writer (VA)"] = unslide(addr)
        self.hits.append(hit)
        # RE-VERIFY ANY WATCH, on this thread, on every hit. Arming-time
        # verification says the registers took; it does NOT say they stayed.
        # A watch that is live at t=4s and cleared by t=18s reports the same
        # zero as one that was never written to, and this run cannot tell
        # those apart without a sample AFTER the event of interest.
        for wslot, st in list(getattr(self, "watching", {}).items()):
            live = False
            if ctx is not None:
                dr = (ctx.Dr0, ctx.Dr1, ctx.Dr2, ctx.Dr3)[wslot]
                live = (dr == st[0]
                        and bool(ctx.Dr7 & (1 << (2 * wslot)))
                        and ((ctx.Dr7 >> (16 + 4 * wslot)) & 0b11)
                        == RW_BITS["w"])
            self.watch_recheck.setdefault(wslot, [0, 0])
            self.watch_recheck[wslot][0 if live else 1] += 1
            # WHAT it found, not just whether. "The address survived and only
            # R/W reverted" and "the whole register was cleared" are different
            # diagnoses with different causes, and a boolean cannot tell them
            # apart. A few distinct samples is enough and costs nothing.
            if ctx is not None and not live:
                dr = (ctx.Dr0, ctx.Dr1, ctx.Dr2, ctx.Dr3)[wslot]
                seen = self.watch_seen.setdefault(wslot, {})
                k = (dr, ctx.Dr7)
                if len(seen) < 6 or k in seen:
                    seen[k] = seen.get(k, 0) + 1
        key = self.addrs[slot]
        n = self.hit_counts[key] = self.hit_counts.get(key, 0) + 1
        if self.on_hit:
            self.on_hit(self, hit)
        # RESUME PAST IT. See EFLAGS_RF: without this the same instruction
        # re-traps on every continue and the site's hit count becomes a count of
        # our own re-entries. DR6 is cleared in the same write, so the sticky
        # bits stay a usable cross-check rather than accumulating.
        if ctx is not None and h:
            ctx.EFlags |= EFLAGS_RF
            ctx.Dr6 = 0
            # AND RE-STAMP THE DEBUG REGISTERS FROM THE CURRENT ARMED SET.
            # `ctx` was read BEFORE `on_hit`, and CONTEXT_FULL_READ includes
            # the debug registers -- so writing it back verbatim RESTORES
            # whatever DR state existed before the handler ran. Anything a
            # handler armed is silently undone, on the very thread that just
            # produced a hit, which is the thread most likely to matter.
            # MEASURED: a row watch armed from `on_hit` verified live on 51
            # threads and was then found cleared at 50 of 50 later checks,
            # with DR7 back to 0x15 -- exactly the three execute slots that
            # existed before it. The deferred-arming path never hit this only
            # because it re-arms AFTER this write rather than during the
            # handler.
            d = self.dr_state()
            ctx.Dr0, ctx.Dr1, ctx.Dr2, ctx.Dr3 = d[:4]
            ctx.Dr7 = d[4]
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
        # Only if the live sample never happened. Re-sampling here would
        # overwrite a good reading with a dead process's.
        if self.coverage is None:
            try:
                self.snapshot_coverage()
            except Exception:                                # noqa: BLE001
                self.coverage = None
        try:
            self._disarm_all()
        except Exception:
            pass
        kernel32.DebugActiveProcessStop(self.pid)
        for h in self._opened:
            kernel32.CloseHandle(h)
        self._opened = []
        self.attached = False


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
                 arm_after=None, oneshot=False, kind="x", size=4):
        # kind "w" is a DATA WRITE watchpoint rather than an execute
        # breakpoint. Such a site has no fixed VA -- the address lives inside
        # a heap object and is supplied mid-run by `HwTrap.arm_watch` -- and
        # therefore no bytes to verify, which is why `code` may be None and
        # `verify_sites` already reports that case as "unverified" rather than
        # as a failure.
        self.name, self.va, self.code, self.why = name, va, code, why
        self.kind, self.size = kind, size
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
              f"{cov['threads']}  (at attach)\n")
            ad = getattr(trap, "adopted", None)
            if ad:
                # WORDED CAREFULLY. This line used to read "(N adopted beyond
                # the debug loop's)", which says the loop would never have had
                # them -- and that reading cost a whole re-audit. Adoption runs
                # inside CREATE_PROCESS, BEFORE the OS delivers its synthetic
                # CREATE_THREAD events, so its second number is a count of
                # threads not yet ANNOUNCED, not of threads left unwatched.
                w(f"  threads the PROCESS had        {ad[0]} "
                  f"({ad[1]} armed early, before the loop announced them)\n")
            end = getattr(trap, "coverage_end", None)
            if end is None:
                w("  coverage AT THE END            NOT SAMPLED -- the run "
                  "started covered; whether it stayed covered is unknown\n")
            else:
                w(f"  threads armed and VERIFIED     {end['armed']} of "
                  f"{end['threads']}  (at the end of the run)\n")
                if end["armed"] < end["threads"]:
                    w("      COVERAGE WAS LOST DURING THE RUN -- a zero hit "
                      "count from this run is not evidence of absence\n")
                    for tid, why in end["bad"][:8]:
                        w(f"      tid {tid}: {why}\n")
        # WATCHPOINT STATE, in the report rather than only on stdout -- a
        # live console scrolls and gets truncated, and "the watch never
        # fired" is worth nothing without "the watch was verified live".
        watching = getattr(trap, "watching", None)
        if watching:
            for slot, st in sorted(watching.items()):
                addr, size, armed, live = (list(st) + [None])[:4]
                w(f"  WATCH slot {slot}: {size}B at 0x{addr:08X}, armed "
                  f"{armed} thread(s), VERIFIED live on {live}\n")
                rc = getattr(trap, "watch_recheck", {}).get(slot)
                if rc:
                    w(f"      re-checked at later hits: still live {rc[0]}, "
                      f"GONE {rc[1]}"
                      + ("   <- the register did NOT survive, so this "
                         "watch's zero means nothing" if rc[1] else "")
                      + "\n")
                    for (dr, dr7), n in sorted(
                            getattr(trap, "watch_seen", {})
                            .get(slot, {}).items(), key=lambda kv: -kv[1]):
                        w(f"        x{n:<5} DR{slot}=0x{dr:08X} "
                          f"DR7=0x{dr7:08X}"
                          + ("  (address SURVIVED, R/W reverted)"
                             if dr == addr else "  (address cleared too)")
                          + "\n")
        elif any(getattr(s, "kind", "x") == "w" for s in sites):
            w("  WATCH: a write-watch site was armed but NEVER GIVEN AN "
              "ADDRESS -- its zero hit count means nothing\n")
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
