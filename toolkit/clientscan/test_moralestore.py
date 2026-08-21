"""Prove the morale-store scanner can find and follow a value, with no client.

`moralestore.py` answered MORALE-Q7 by finding a dword in the client's memory
and watching it change. Everything that answer rests on is the SEARCH -- region
walk, aligned scan, windowed poll -- and none of it is about Guild Wars, so it
is tested against a process this machine controls: a child that holds a known
value at a known address and then changes it on a schedule.

WHY THIS FILE EXISTS AT ALL, rather than "the run worked so the tool works".
The tool's headline output is a NEGATIVE as often as a positive -- "nothing in
this window ever changed" is exactly what "the delta is ignored" would look
like, and it is also exactly what a scanner that cannot see anything looks
like. A null from a filter nobody has proven can see is not evidence
(`feedback: a negative needs a positive control`), and this is that control,
made repeatable.

It also pins the defect that cost the first Q7 attempt: `scan_u32` returning
hits for a value the experiment has not set yet is not a bug, it is arithmetic
-- a plain integer occurs by coincidence hundreds of times in any large process
-- so §3 measures that coincidence rate rather than pretending it is zero, and
the tool's documented method (anchor on a CONSTANT, watch a window) is what §2
exercises.

Windows only; every section skips honestly elsewhere. No vault, no client.

    python toolkit/clientscan/test_moralestore.py
"""
import os
import struct
import subprocess
import sys
import textwrap
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "harness"))
import checks  # noqa: E402
import keytap  # noqa: E402
import moralestore  # noqa: E402

LEDGER = checks.Ledger("morale store scanner", floor=8)
IS_WINDOWS = sys.platform == "win32"

# The child holds these, in this order, one second apart. ANCHOR is the value it
# never changes -- the tool's whole method is locating on one of those.
ANCHOR = 424242
SEQUENCE = (77, 88, 66, 53)
STEP_SECONDS = 1.0

CHILD = textwrap.dedent("""
    import ctypes, sys, time
    buf = (ctypes.c_uint32 * 64)()
    buf[0] = {anchor}          # the constant, at +0
    buf[32] = {first}          # the value under test, at +128
    print("%d %d" % (ctypes.windll.kernel32.GetCurrentProcessId(),
                     ctypes.addressof(buf)), flush=True)
    t0 = time.time()
    for i, v in enumerate({rest!r}, start=1):
        while time.time() - t0 < i * {step}:
            time.sleep(0.05)
        buf[32] = v
    time.sleep(6)
""")


def main():
    if not IS_WINDOWS:
        LEDGER.skip("all", f"moralestore is Windows-only; platform is {sys.platform}")
        return LEDGER.verdict()

    src = CHILD.format(anchor=ANCHOR, first=SEQUENCE[0], rest=SEQUENCE[1:],
                       step=STEP_SECONDS)
    child = subprocess.Popen([sys.executable, "-c", src],
                             stdout=subprocess.PIPE, text=True)
    try:
        line = child.stdout.readline().split()
        pid, addr = int(line[0]), int(line[1])

        # ---- 1. the anchor is found, and it is the child's own address -------
        print("1. a constant in another process is located by scanning")
        hits, scanned = moralestore.scan_u32(pid, ANCHOR)
        LEDGER.ok(scanned > 1_000_000,
                  "the region walk actually reads memory",
                  f"{scanned / 1e6:.1f} MB -- a walk that terminates early "
                  f"reports a confident zero, which is how the first Q7 "
                  f"attempt failed")
        LEDGER.ok(addr in hits,
                  "and the anchor is found at the address the child printed",
                  f"0x{addr:X} in {len(hits)} hit(s)")
        LEDGER.ok(all(a % 4 == 0 for a in hits),
                  "every hit is 4-byte aligned",
                  "an unaligned 'hit' is three bytes of one value and one of "
                  "the next, and it can never be a stored dword")

        # ---- 2. the window around it follows the whole sequence -------------
        print("\n2. the watched window follows a value the test controls")
        watch_for = STEP_SECONDS * (len(SEQUENCE) + 1)
        hist = moralestore.watch_window(pid, [addr], span=0x100,
                                        seconds=watch_for, period=0.2)
        seen = [v for _t, v in hist[addr].get(128, [])]
        LEDGER.ok(seen[:1] == [SEQUENCE[0]] if seen else False,
                  f"the window's +128 slot starts at {SEQUENCE[0]}",
                  f"{seen}")
        LEDGER.ok(seen == list(SEQUENCE),
                  "and records every value in order, and no others",
                  f"{seen} against {list(SEQUENCE)} -- a poll that misses a "
                  f"step would have shown a shorter trail, and a scanner "
                  f"reading a stale page would have shown none")
        quiet = [o for o, h in hist[addr].items() if len(h) > 1 and o != 128]
        LEDGER.ok(not quiet,
                  "and nothing else in the window moved",
                  f"{quiet} -- the neighbours are the control: a window that "
                  f"reports everything moving is reporting noise")

        # ---- 3. the coincidence rate is real, and is why anchors are used ---
        print("\n3. a plain value occurs by coincidence; a rare constant does not")
        common, _ = moralestore.scan_u32(pid, 1)
        LEDGER.ok(len(common) > len(hits),
                  "scanning for 1 finds far more than scanning for the anchor",
                  f"{len(common):,} hits for 1 against {len(hits)} for "
                  f"{ANCHOR} -- this is the arithmetic that broke the first "
                  f"Q7 attempt: a scan for the value UNDER TEST, run before "
                  f"the probe sets it, locks onto coincidences that no later "
                  f"step can rescue")

        # ---- 4. and an address that is gone reads as gone -------------------
        print("\n4. an unmapped address is a clean miss, not a wrong value")
        LEDGER.ok(keytap.read_at(pid, 0x10, 4) is None,
                  "reading page zero returns None",
                  "a reader that returns stale or zeroed bytes for an "
                  "unreadable address would make every negative meaningless")
    finally:
        child.kill()
        child.wait(timeout=10)

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
