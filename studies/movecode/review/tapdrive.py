#!/usr/bin/env python3
"""Drive one hooked lead run: tape + harness, and attach movehook the moment the body is in the map.

    python studies/movecode/review/tapdrive.py <out dir> [--walk "..."] [--game-args "..."]

RUN-1zBD's driver (MOVECODE-1z-bd). The movehook DLL's run timer starts at
INJECTION, so `attach.py` wants the client in the world first; the harness prints
"body is in the map" as a checkpoint, and that line is the trigger. The harness's
opening `wait:` must be long enough for the attach (measured 2.7-4.4 s after the
line) to land before the first key -- 8 s here. The client's stdout is read with
`python -u`, because a piped child buffers and the trigger line would arrive after
the run.

The DLL lives beside attach.py in whichever checkout built it -- `--main` names
that tree (default C:/gd/Rurik); the tape and the harness run from THIS tree.
"""
import argparse
import os
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EXE = "C:/gd/Rurik/vault/run/2026-07-29_221c13772c7a/Gw.exe"      # build 38797, movehook's addresses
WALK = "wait:8 W:5 S:4 W:5 Q:3 E:3 S:4 W:4"
GAME = ("--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0 "
        "--kbd-lead --lead-seam-clip")   # --no-repin-stationary-waiver retired at 1z-bt: the waiver is gone


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out", help="movehook output directory for this run")
    ap.add_argument("--main", default="C:/gd/Rurik", help="the checkout whose movehook.dll is built")
    ap.add_argument("--exe", default=EXE)
    ap.add_argument("--walk", default=WALK)
    ap.add_argument("--game-args", default=GAME)
    ap.add_argument("--minutes", type=float, default=1.0)
    ap.add_argument("--tape-seconds", type=int, default=95)
    ap.add_argument("--hold", type=int, default=30,
                    help="long enough for the hook's timer to elapse and write before the client closes")
    a = ap.parse_args()
    py = sys.executable

    tap = subprocess.Popen([py, "-u", os.path.join(TREE, "toolkit/clientscan/agenttap.py"),
                            "--agents", "1,10", "--seconds", str(a.tape_seconds)],
                           cwd=TREE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def pump(proc, tag):
        for line in proc.stdout:
            sys.stdout.write("[%s] %s" % (tag, line))
            sys.stdout.flush()
    threading.Thread(target=pump, args=(tap, "tap"), daemon=True).start()

    sess = subprocess.Popen([py, "-u", os.path.join(TREE, "toolkit/harness/session.py"), "--exe", a.exe,
                             "--enemy", "--walk", a.walk, "--hold", str(a.hold), "--game-args", a.game_args],
                            cwd=TREE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    attached = False
    for line in sess.stdout:
        sys.stdout.write("[sess] " + line)
        sys.stdout.flush()
        if not attached and "body is in the map" in line:
            attached = True
            t_att = time.time()
            r = subprocess.run([py, os.path.join(a.main, "toolkit/clientscan/movehook/attach.py"),
                                "--minutes", str(a.minutes), "--out", a.out],
                               cwd=a.main, capture_output=True, text=True)
            for l in (r.stdout + r.stderr).splitlines():
                sys.stdout.write("[attach] " + l + "\n")
            sys.stdout.write("[drive] attach exit %d, %.2fs after the map line\n"
                             % (r.returncode, time.time() - t_att))
            sys.stdout.flush()
    sess.wait()
    print("[drive] session exit", sess.returncode)
    tap.wait(timeout=240)
    print("[drive] tap exit", tap.returncode)
    st = os.path.join(a.main, "toolkit/clientscan/movehook/movehook.status")
    if os.path.exists(st):
        print("[drive] movehook.status:\n" + open(st, encoding="utf-8", errors="replace").read())
    else:
        print("[drive] no movehook.status written")
    if not attached:
        print("[drive] WARNING: the map line never appeared; nothing was attached")
    return 0


if __name__ == "__main__":
    sys.exit(main())
