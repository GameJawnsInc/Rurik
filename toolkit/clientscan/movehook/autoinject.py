"""Inject the moment the client exists, because terrain builds once.

    python toolkit/clientscan/trnhook/autoinject.py trnblock.dll

WHY THIS EXISTS, and it cost a run to learn. The terrain chunk builders run
ONCE, at map load -- walking does not retrigger them -- so a hook armed after
that point sees nothing at all. On 2026-08-18 a capture came back
`hits 0 / distinct blocks seen 0` with a perfectly correct, ASLR-resolved
breakpoint address: the client started at 16:30:45, the map loaded at
16:30:52, and the injection landed around 16:31:15. Seven seconds is the
whole window, and a human-paced "poll for the pid, then run inject.py" round
trip does not fit inside it.

So this polls hard (25 ms) for the process and injects in the same breath,
starting BEFORE the client is launched. It reuses `inject.py` rather than
reimplementing the remote-thread dance, so there is one injector and not two.

It refuses a SECOND injection into the same pid: the DLL patches a byte and
restores it, and a double load would arm the site twice and restore it once.
"""

import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "harness"))


def find_pid(image="Gw.exe"):
    """The newest pid running `image`, or None. `tasklist` keeps this stdlib."""
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV",
                          "/NH"], capture_output=True, text=True).stdout
    pids = []
    for line in out.splitlines():
        parts = [p.strip('" ') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == image.lower():
            try:
                pids.append(int(parts[1]))
            except ValueError:
                pass
    return max(pids) if pids else None


def main(argv):
    dll = argv[0] if argv else "trnblock.dll"
    if not os.path.isabs(dll):
        dll = os.path.join(HERE, dll)
    if not os.path.exists(dll):
        raise SystemExit(f"no DLL at {dll} -- build it first")
    timeout = float(argv[1]) if len(argv) > 1 else 180.0

    print(f"[autoinject] waiting for Gw.exe, will load {os.path.basename(dll)}")
    t0 = time.time()
    pid = None
    while time.time() - t0 < timeout:
        pid = find_pid()
        if pid:
            break
        time.sleep(0.025)
    if not pid:
        raise SystemExit(f"[FAIL] no Gw.exe within {timeout:.0f}s")

    waited = time.time() - t0
    print(f"[autoinject] pid {pid} seen at t+{waited:.2f}s; injecting now")
    r = subprocess.run([sys.executable, os.path.join(HERE, "inject.py"),
                        str(pid), dll], capture_output=True, text=True)
    sys.stdout.write(r.stdout)
    sys.stderr.write(r.stderr)
    if r.returncode != 0:
        raise SystemExit(f"[FAIL] inject.py exited {r.returncode}")
    print(f"[autoinject] injected into {pid} at t+{time.time()-t0:.2f}s "
          f"after the process appeared")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
