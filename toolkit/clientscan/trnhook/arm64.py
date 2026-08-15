"""Arm the terrain breakpoints from OUTSIDE, with `Wow64SetThreadContext`.

WHY THIS IS A SEPARATE STEP. `trnhook.dll` arms Dr0/Dr1 from inside the
client and the breakpoint never fired -- twice, on both the hi and lo terrain
paths, so it was not path selection. On WOW64 the debug registers belong to
the 64-bit side of the thread: a 32-bit `SetThreadContext` issued from inside
the process does not stick. The DLL stays as the vectored-exception HOST,
which is the part that must run in-process; the arming moves out here, where a
64-bit caller can use `Wow64SetThreadContext`.

AND IT READS BACK. The previous version's whole failure was that it never
checked whether the write took, so two runs produced "no hit" with no way to
tell an unarmed register from an uncalled function. This one re-reads Dr0/Dr7
after setting them and says so per thread. A check that cannot fail is not a
check.

Usage: arm64.py <pid>      (run AFTER inject.py)
"""
import ctypes
import os
import sys
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "harness"))
import keytap  # noqa: E402

HI_RVA, LO_RVA = 0x0035DD50, 0x0035E650
WOW64_CONTEXT_i386 = 0x00010000
WOW64_CONTEXT_DEBUG_REGISTERS = WOW64_CONTEXT_i386 | 0x10
THREAD_ACCESS = 0x1F03FF
TH32CS_SNAPTHREAD = 0x04
k32 = ctypes.windll.kernel32


class FLOATING_SAVE_AREA(ctypes.Structure):
    _fields_ = [("ControlWord", wintypes.DWORD), ("StatusWord", wintypes.DWORD),
                ("TagWord", wintypes.DWORD), ("ErrorOffset", wintypes.DWORD),
                ("ErrorSelector", wintypes.DWORD), ("DataOffset", wintypes.DWORD),
                ("DataSelector", wintypes.DWORD),
                ("RegisterArea", ctypes.c_byte * 80),
                ("Cr0NpxState", wintypes.DWORD)]


class WOW64_CONTEXT(ctypes.Structure):
    _fields_ = [("ContextFlags", wintypes.DWORD),
                ("Dr0", wintypes.DWORD), ("Dr1", wintypes.DWORD),
                ("Dr2", wintypes.DWORD), ("Dr3", wintypes.DWORD),
                ("Dr6", wintypes.DWORD), ("Dr7", wintypes.DWORD),
                ("FloatSave", FLOATING_SAVE_AREA),
                ("SegGs", wintypes.DWORD), ("SegFs", wintypes.DWORD),
                ("SegEs", wintypes.DWORD), ("SegDs", wintypes.DWORD),
                ("Edi", wintypes.DWORD), ("Esi", wintypes.DWORD),
                ("Ebx", wintypes.DWORD), ("Edx", wintypes.DWORD),
                ("Ecx", wintypes.DWORD), ("Eax", wintypes.DWORD),
                ("Ebp", wintypes.DWORD), ("Eip", wintypes.DWORD),
                ("SegCs", wintypes.DWORD), ("EFlags", wintypes.DWORD),
                ("Esp", wintypes.DWORD), ("SegSs", wintypes.DWORD),
                ("ExtendedRegisters", ctypes.c_byte * 512)]


class THREADENTRY32(ctypes.Structure):
    _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                ("th32ThreadID", wintypes.DWORD),
                ("th32OwnerProcessID", wintypes.DWORD),
                ("tpBasePri", ctypes.c_long), ("tpDeltaPri", ctypes.c_long),
                ("dwFlags", wintypes.DWORD)]


def threads_of(pid):
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPTHREAD, 0)
    te = THREADENTRY32()
    te.dwSize = ctypes.sizeof(te)
    out = []
    if k32.Thread32First(snap, ctypes.byref(te)):
        while True:
            if te.th32OwnerProcessID == pid:
                out.append(te.th32ThreadID)
            if not k32.Thread32Next(snap, ctypes.byref(te)):
                break
    k32.CloseHandle(snap)
    return out


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    pid = int(argv[0])
    base = keytap.module_base(pid, "Gw.exe")
    if not base:
        raise SystemExit(f"Gw.exe not found in pid {pid}")
    if len(argv) > 1:
        hi = int(argv[1], 16)
        lo = int(argv[2], 16) if len(argv) > 2 else hi
    else:
        hi, lo = base + HI_RVA, base + LO_RVA
    print(f"image base 0x{base:08X}  hi 0x{hi:08X}  lo 0x{lo:08X}")

    armed = stuck = 0
    for tid in threads_of(pid):
        h = k32.OpenThread(THREAD_ACCESS, False, tid)
        if not h:
            continue
        c = WOW64_CONTEXT()
        c.ContextFlags = WOW64_CONTEXT_DEBUG_REGISTERS
        k32.SuspendThread(h)
        try:
            if not k32.Wow64GetThreadContext(h, ctypes.byref(c)):
                continue
            c.Dr0, c.Dr1, c.Dr6 = hi, lo, 0
            # L0 | L1; RW/LEN nibbles zero = execute, one byte, for both slots
            c.Dr7 = (c.Dr7 & ~0xFF0000) | 0x5
            c.ContextFlags = WOW64_CONTEXT_DEBUG_REGISTERS
            ok = k32.Wow64SetThreadContext(h, ctypes.byref(c))
            armed += 1 if ok else 0
            # READ BACK -- the check whose absence cost the last two runs
            v = WOW64_CONTEXT()
            v.ContextFlags = WOW64_CONTEXT_DEBUG_REGISTERS
            if k32.Wow64GetThreadContext(h, ctypes.byref(v)):
                if v.Dr0 == hi and (v.Dr7 & 0x5) == 0x5:
                    stuck += 1
                    print(f"  tid {tid}: Dr0=0x{v.Dr0:08X} Dr1=0x{v.Dr1:08X} "
                          f"Dr7=0x{v.Dr7:08X}  STUCK")
        finally:
            k32.ResumeThread(h)
            k32.CloseHandle(h)
    print(f"\n{armed} thread(s) accepted the write, {stuck} verified by read-back")
    if not stuck:
        print("  NOTHING ARMED -- a 'no hit' after this means the register, "
              "not the function")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
