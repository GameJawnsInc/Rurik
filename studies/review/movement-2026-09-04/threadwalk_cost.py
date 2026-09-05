"""Read-only: time _threads_of() as movetap calls it. No client needed.

Prints only. Re-derives studies/movement/FINDINGS.md:5309's 51.7 ms/call.
"""
import os
import sys
import time

sys.path.insert(0, r"C:\gd\Rurik\toolkit\clientscan")
import movetap  # noqa: E402

pid = os.getpid()
# warm
movetap._threads_of(pid)
ts = []
for _ in range(20):
    t0 = time.perf_counter()
    movetap._threads_of(pid)
    ts.append((time.perf_counter() - t0) * 1000.0)
ts.sort()
print(f"_threads_of(self) n=20  min {ts[0]:.1f}  p50 {ts[10]:.1f}  max {ts[-1]:.1f} ms")
print(f"  -> ceiling from this call alone: {1000.0 / ts[10]:.1f} Hz")
