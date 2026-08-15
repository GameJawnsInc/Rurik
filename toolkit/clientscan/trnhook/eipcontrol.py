"""Does a hardware breakpoint fire AT ALL in this client? Ask the client.

Five silent runs were all read as facts about the terrain functions, and the
last one showed why that was unsafe: the control was `PeekMessageW`, and
nothing ever established that a 2005-era Win32 client pumps the WIDE variant
rather than `PeekMessageA`. Verifying the instrument is not verifying the
probe.

So this control assumes NOTHING about the client. It takes the breakpoint
address out of the process's own EIP:

  1. sample a thread's EIP twice, a moment apart -- if it MOVED, that thread is
     executing code, which is a fact and not an assumption;
  2. arm those EIPs as execute breakpoints (up to four, Dr0..Dr3);
  3. watch.

A running thread re-executes its hot code within milliseconds, so:

    fires   -> the instrument works. Every earlier silence is then about which
               function is called, and the terrain question is live again.
    silent  -> hardware breakpoints do not deliver in this client, full stop.
               Nothing measured this way says anything about the terrain, and
               the route is an int3 patch or a D3D9 wrapper instead.

Usage: eipcontrol.py <pid> [seconds]
"""
import ctypes
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "harness"))
import arm64        # noqa: E402
import debugread as D  # noqa: E402  (arm_native, DEBUG_EVENT, constants)

k32 = ctypes.windll.kernel32


def eip_of(tid):
    h = k32.OpenThread(arm64.THREAD_ACCESS, False, tid)
    if not h:
        return None
    c = arm64.WOW64_CONTEXT()
    c.ContextFlags = arm64.WOW64_CONTEXT_i386 | 0x1      # CONTEXT_CONTROL
    # 0x1 is CONTROL (where Eip lives); 0x2 is INTEGER. Using 0x2 made
    # Wow64GetThreadContext succeed with Eip==0 on every thread, which
    # read as 'nothing is executing' in a visibly rendering client.
    k32.SuspendThread(h)
    try:
        if k32.Wow64GetThreadContext(h, ctypes.byref(c)):
            return c.Eip
    finally:
        k32.ResumeThread(h)
        k32.CloseHandle(h)
    return None


def arm_four(tid, addrs):
    """Dr0..Dr3 = addrs, in the NATIVE context, verified by native read-back."""
    h = k32.OpenThread(arm64.THREAD_ACCESS, False, tid)
    if not h:
        return False
    raw, p = D._ctx_buf()
    k32.SuspendThread(h)
    try:
        ctypes.memset(p, 0, D.CTX_SIZE)
        ctypes.memmove(p + D.OFF_FLAGS,
                       D.struct.pack("<I", D.CONTEXT_DEBUG_REGISTERS_64), 4)
        if not k32.GetThreadContext(h, ctypes.c_void_p(p)):
            return False
        ctl = 0
        for i, a in enumerate(addrs[:4]):
            D._put(p, D.OFF_DR0 + 8 * i, a)
            ctl |= (1 << (2 * i))                        # L0..L3
        D._put(p, D.OFF_DR7, ctl)
        ctypes.memmove(p + D.OFF_FLAGS,
                       D.struct.pack("<I", D.CONTEXT_DEBUG_REGISTERS_64), 4)
        return bool(k32.SetThreadContext(h, ctypes.c_void_p(p)))
    finally:
        k32.ResumeThread(h)
        k32.CloseHandle(h)


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    pid = int(argv[0])
    budget = int(argv[1]) if len(argv) > 1 else 45

    tids = arm64.threads_of(pid)
    first = {t: eip_of(t) for t in tids}
    time.sleep(0.35)
    moving = []
    for t in tids:
        a, b = first.get(t), eip_of(t)
        if a and b and a != b:
            moving.append((t, b))
    print(f"{len(tids)} thread(s); {len(moving)} PROVABLY EXECUTING "
          f"(EIP moved between two samples)")
    if not moving:
        print("  no thread's EIP moved -- cannot build an honest control")
        return 2
    for t, e in moving[:6]:
        print(f"    tid {t}: eip now 0x{e:08X}")

    addrs = [e for _, e in moving[:4]]
    k32.DebugSetProcessKillOnExit(False)
    if not k32.DebugActiveProcess(pid):
        raise SystemExit(f"DebugActiveProcess failed: {ctypes.GetLastError()}")
    print(f"attached; arming {[hex(a) for a in addrs]} on every thread")

    armed = sum(1 for t in arm64.threads_of(pid) if arm_four(t, addrs))
    print(f"armed {armed} thread(s); watching {budget}s")

    ev = D.DEBUG_EVENT()
    fired = None
    spent = 0
    while spent < budget * 1000 and fired is None:
        if not k32.WaitForDebugEvent(ctypes.byref(ev), 500):
            spent += 500
            continue
        status = D.DBG_CONTINUE
        if ev.dwDebugEventCode == D.EXCEPTION_DEBUG_EVENT:
            code = ev.u.Exception.ExceptionRecord.ExceptionCode
            if code == D.EXCEPTION_SINGLE_STEP:
                fired = ev.u.Exception.ExceptionRecord.ExceptionAddress
                print(f"  *** HIT at 0x{(fired or 0):08X} on tid {ev.dwThreadId}")
            elif code != D.EXCEPTION_BREAKPOINT:
                status = D.DBG_EXCEPTION_NOT_HANDLED
        k32.ContinueDebugEvent(ev.dwProcessId, ev.dwThreadId, status)

    k32.DebugActiveProcessStop(pid)
    if fired is not None:
        print("\nINSTRUMENT WORKS. Hardware breakpoints deliver in this "
              "client, so every earlier silence is about WHICH function runs.")
        return 0
    print("\nINSTRUMENT IS DEAD. Breakpoints were set on addresses the client "
          "was provably executing and nothing fired. No result obtained this "
          "way says anything about the terrain functions.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
