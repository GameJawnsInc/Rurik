"""Read the terrain chunk pointer with a real debugger loop.

WHY NOT THE DLL. `trnhook.dll` hosts a 32-bit vectored handler and it never
receives the hardware-breakpoint exception: the control armed `PeekMessageW`
on 49 verified threads in a rendering client and got nothing, which retracted
two commits' worth of conclusions. In a WOW64 process the debug-register
exception is raised on the 64-bit side, so it has to be COLLECTED there --
`DebugActiveProcess` + `WaitForDebugEvent` from this 64-bit interpreter.

THE CONTROL IS BUILT IN, and it is not optional after what it just caught.
Dr2 watches `PeekMessageW`, which any Windows game loop calls every frame. So
one run answers both questions and cannot repeat the last failure:

    Dr2 fires, Dr0/Dr1 do not  -> the path works, the terrain funcs really are
                                  not called (the earlier claim, now earned)
    nothing fires              -> this route is broken too; report that, do
                                  NOT interpret it as a fact about the client
    Dr0 or Dr1 fires           -> read [esp+4], that IS the chunk

`DebugSetProcessKillOnExit(FALSE)` so detaching leaves the client alive.

Usage: debugread.py <pid> [seconds]
"""
import ctypes
import os
import struct
import sys
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "harness"))
import keytap   # noqa: E402
import arm64    # noqa: E402  (WOW64_CONTEXT, threads_of, constants)
import inject   # noqa: E402  (export_rva)

HI_RVA, LO_RVA = 0x0035DD50, 0x0035E650
SEL_OFF, RNG_OFF, SEL_LEN = 0x2B4, 0x2A4, 1024
OUTDIR = r"C:\gd\Rurik\vault\research\terrain"

EXCEPTION_DEBUG_EVENT = 1
CREATE_THREAD_DEBUG_EVENT = 2
EXCEPTION_SINGLE_STEP = 0x80000004
EXCEPTION_BREAKPOINT = 0x80000003
DBG_CONTINUE = 0x00010002
DBG_EXCEPTION_NOT_HANDLED = 0x80010001
k32 = ctypes.windll.kernel32


class EXCEPTION_RECORD(ctypes.Structure):
    pass


EXCEPTION_RECORD._fields_ = [
    ("ExceptionCode", wintypes.DWORD), ("ExceptionFlags", wintypes.DWORD),
    ("ExceptionRecord", ctypes.POINTER(EXCEPTION_RECORD)),
    ("ExceptionAddress", ctypes.c_void_p),
    ("NumberParameters", wintypes.DWORD),
    ("ExceptionInformation", ctypes.c_void_p * 15)]


class EXCEPTION_DEBUG_INFO(ctypes.Structure):
    _fields_ = [("ExceptionRecord", EXCEPTION_RECORD),
                ("dwFirstChance", wintypes.DWORD)]


class DEBUG_EVENT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("Exception", EXCEPTION_DEBUG_INFO),
                    ("pad", ctypes.c_byte * 256)]
    _fields_ = [("dwDebugEventCode", wintypes.DWORD),
                ("dwProcessId", wintypes.DWORD),
                ("dwThreadId", wintypes.DWORD), ("u", _U)]



# --- NATIVE 64-bit CONTEXT arming -------------------------------------------
# Wow64SetThreadContext writes the 32-bit SHADOW context. The CPU debug
# registers are per-thread NATIVE state, so on a WOW64 target they have to be
# set in the 64-bit CONTEXT. Every silent run before this one armed the shadow
# and then read the shadow back, so the read-back could not have caught it.
# AMD64 CONTEXT: ContextFlags at +0x30, Dr0 at +0x48, Dr7 at +0x70, size 1232,
# and the buffer MUST be 16-byte aligned.
CTX_SIZE = 1232
CONTEXT_AMD64 = 0x00100000
CONTEXT_DEBUG_REGISTERS_64 = CONTEXT_AMD64 | 0x10
OFF_FLAGS, OFF_DR0, OFF_DR7 = 0x30, 0x48, 0x70


def _ctx_buf():
    raw = ctypes.create_string_buffer(CTX_SIZE + 16)
    addr = ctypes.addressof(raw)
    return raw, addr + ((16 - (addr % 16)) % 16)


def _put(p, off, val):
    ctypes.memmove(p + off, struct.pack("<Q", val), 8)


def _get(p, off):
    b = (ctypes.c_char * 8).from_address(p + off)
    return struct.unpack("<Q", bytes(b))[0]


def arm_native(tid, hi, lo, ctl):
    """Set Dr0/Dr1/Dr2 in the NATIVE context. Returns (ok, dr0_readback)."""
    h = k32.OpenThread(arm64.THREAD_ACCESS, False, tid)
    if not h:
        return False, 0
    raw, p = _ctx_buf()
    k32.SuspendThread(h)
    try:
        ctypes.memset(p, 0, CTX_SIZE)
        _put(p, OFF_FLAGS - 8, 0)
        ctypes.memmove(p + OFF_FLAGS,
                       struct.pack("<I", CONTEXT_DEBUG_REGISTERS_64), 4)
        if not k32.GetThreadContext(h, ctypes.c_void_p(p)):
            return False, 0
        _put(p, OFF_DR0, hi)
        _put(p, OFF_DR0 + 8, lo)
        _put(p, OFF_DR0 + 16, ctl)
        _put(p, OFF_DR7, (_get(p, OFF_DR7) & ~0xFFFFFF00) | 0x15)
        ctypes.memmove(p + OFF_FLAGS,
                       struct.pack("<I", CONTEXT_DEBUG_REGISTERS_64), 4)
        if not k32.SetThreadContext(h, ctypes.c_void_p(p)):
            return False, 0
        # read back the NATIVE context -- the check the shadow version faked
        raw2, p2 = _ctx_buf()
        ctypes.memset(p2, 0, CTX_SIZE)
        ctypes.memmove(p2 + OFF_FLAGS,
                       struct.pack("<I", CONTEXT_DEBUG_REGISTERS_64), 4)
        if k32.GetThreadContext(h, ctypes.c_void_p(p2)):
            return True, _get(p2, OFF_DR0)
        return True, 0
    finally:
        k32.ResumeThread(h)
        k32.CloseHandle(h)


def arm(tid, hi, lo, ctl):
    h = k32.OpenThread(arm64.THREAD_ACCESS, False, tid)
    if not h:
        return False
    c = arm64.WOW64_CONTEXT()
    c.ContextFlags = arm64.WOW64_CONTEXT_DEBUG_REGISTERS
    ok = False
    k32.SuspendThread(h)
    try:
        if k32.Wow64GetThreadContext(h, ctypes.byref(c)):
            c.Dr0, c.Dr1, c.Dr2, c.Dr6 = hi, lo, ctl, 0
            # L0|L1|L2, all execute/1-byte (RW+LEN nibbles zero)
            c.Dr7 = (c.Dr7 & ~0xFFFFFF00) | 0x15
            c.ContextFlags = arm64.WOW64_CONTEXT_DEBUG_REGISTERS
            ok = bool(k32.Wow64SetThreadContext(h, ctypes.byref(c)))
    finally:
        k32.ResumeThread(h)
        k32.CloseHandle(h)
    return ok


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    pid = int(argv[0])
    budget = int(argv[1]) if len(argv) > 1 else 120

    base = keytap.module_base(pid, "Gw.exe")
    hi, lo = base + HI_RVA, base + LO_RVA
    ub, ur = inject.export_rva(pid, "USER32.DLL", "PeekMessageW")
    ctl = ub + ur
    print(f"Gw.exe 0x{base:08X}  hi 0x{hi:08X}  lo 0x{lo:08X}  "
          f"CONTROL PeekMessageW 0x{ctl:08X}")

    k32.DebugSetProcessKillOnExit(False)
    if not k32.DebugActiveProcess(pid):
        raise SystemExit(f"DebugActiveProcess failed: {ctypes.GetLastError()}")
    print("attached")

    n = ok = 0
    for t in arm64.threads_of(pid):
        good, back = arm_native(t, hi, lo, ctl)
        n += 1 if good else 0
        ok += 1 if back == hi else 0
    print(f"NATIVE arm: {n} accepted, {ok} verified by native read-back")
    if not ok:
        print("  native arming FAILED -- stop here, the result would be void")
    print(f"watching {budget}s")

    ev = DEBUG_EVENT()
    hit = None
    deadline = budget * 1000
    spent = 0
    while spent < deadline and hit is None:
        if not k32.WaitForDebugEvent(ctypes.byref(ev), 500):
            spent += 500
            continue
        status = DBG_CONTINUE
        if ev.dwDebugEventCode == CREATE_THREAD_DEBUG_EVENT:
            arm_native(ev.dwThreadId, hi, lo, ctl)   # new threads too
        elif ev.dwDebugEventCode == EXCEPTION_DEBUG_EVENT:
            code = ev.u.Exception.ExceptionRecord.ExceptionCode
            if code == EXCEPTION_SINGLE_STEP:
                h = k32.OpenThread(arm64.THREAD_ACCESS, False, ev.dwThreadId)
                c = arm64.WOW64_CONTEXT()
                c.ContextFlags = (arm64.WOW64_CONTEXT_DEBUG_REGISTERS
                                  | arm64.WOW64_CONTEXT_i386 | 0x1)  # +CONTEXT_CONTROL (Eip)
                if h and k32.Wow64GetThreadContext(h, ctypes.byref(c)):
                    which = ("hi" if c.Eip == hi else
                             "lo" if c.Eip == lo else
                             "CONTROL" if c.Eip == ctl else "?")
                    print(f"  HIT {which} eip=0x{c.Eip:08X} dr6=0x{c.Dr6:08X}")
                    if which in ("hi", "lo"):
                        arg = keytap.read_at(pid, c.Esp + 4, 4)
                        hit = (which, int.from_bytes(arg, "little"))
                    elif which == "CONTROL":
                        print("  -> the debugger route DELIVERS; keep waiting "
                              "for the terrain paths")
                        # disarm Dr2 so the control does not flood the loop
                        c.Dr2 = 0
                        c.Dr7 &= ~0x10
                        c.ContextFlags = arm64.WOW64_CONTEXT_DEBUG_REGISTERS
                        k32.Wow64SetThreadContext(h, ctypes.byref(c))
                if h:
                    k32.CloseHandle(h)
            elif code != EXCEPTION_BREAKPOINT:
                status = DBG_EXCEPTION_NOT_HANDLED
        k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, status)

    k32.DebugActiveProcessStop(pid)
    print("detached")

    if not hit:
        print("\nNO TERRAIN HIT. If no CONTROL line appeared above, this route "
              "is broken too and says NOTHING about the client.")
        return 1

    which, chunk = hit
    sel = keytap.read_at(pid, chunk + SEL_OFF, SEL_LEN)
    rng = keytap.read_at(pid, chunk + RNG_OFF, 8)
    os.makedirs(OUTDIR, exist_ok=True)
    with open(os.path.join(OUTDIR, "selector.bin"), "wb") as f:
        f.write(sel)
    import collections
    hist = collections.Counter(sel)
    fields = collections.Counter()
    for b in sel:
        fields[tuple((b >> (2 * k)) & 3 for k in range(4))] += 1
    print(f"\npath={which}  chunk=0x{chunk:08X}")
    print(f"rng +0x2A4 = {rng[:4].hex()} {rng[4:].hex()}")
    print(f"selector +0x2B4: {len(hist)} distinct byte(s)")
    print(f"  first 64: {' '.join(f'{b:02X}' for b in sel[:64])}")
    print(f"  0xE4 (identity) share: {100*hist.get(0xE4,0)/SEL_LEN:.1f}%")
    print(f"  top bytes: {[(hex(v), n) for v, n in hist.most_common(6)]}")
    print(f"  distinct (c0,c1,c2,c3) pickings: {len(fields)}")
    print(f"  top pickings: {fields.most_common(5)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
