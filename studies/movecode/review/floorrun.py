#!/usr/bin/env python3
"""Drive one RUN-1zCW arm: the agenttap tape and the harness together, no human at the keys.

    python studies/movecode/review/floorrun.py T1            # the shipped arm, tape 1zcw-T1
    python studies/movecode/review/floorrun.py C1 --floor 0.5

Starts agenttap first (it waits for the client's pid), then session.py with the registered
script; pumps both processes' stdout with a tag; exits when both have. The tape lands at
vault/research/movecode/1zcw-<arm>-agenttap.jsonl, where sessionscore's tape finder looks.
"""
import argparse
import os
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
TREE = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(TREE, "toolkit"))
import vaultpath                                            # noqa: E402

EXE = vaultpath.vault_path("run", "2026-07-29_221c13772c7a", "Gw.exe")   # absolute: a worktree has no vault
# RUN-1zCW's second script (pair 1's single-step legs never reported inside the
# floor): the body keeps walking while the view turns, W then S so it stays near
# spawn, four steers of 3 s each per cycle, three cycles.
WALK = "wait:2 " + "steer:W,240,3 steer:S,-240,3 steer:W,-240,3 steer:S,240,3 " * 3
GAME = "--map 146 --explorable --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"


def pump(proc, tag):
    for line in proc.stdout:
        sys.stdout.write(f"[{tag}] {line}")
        sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("arm", help="tape label, e.g. T1 / C1")
    ap.add_argument("--floor", type=float, default=None, help="--kbd-grant-floor for the server")
    ap.add_argument("--walk", default=WALK.strip())
    ap.add_argument("--tape-seconds", type=int, default=75)
    ap.add_argument("--hold", type=int, default=8)
    a = ap.parse_args()
    py = sys.executable
    game = GAME + (f" --kbd-grant-floor {a.floor}" if a.floor is not None else "")
    out_dir = vaultpath.vault_path("research", "movecode")
    os.makedirs(out_dir, exist_ok=True)
    tape = os.path.join(out_dir, f"1zcw-{a.arm}-agenttap.jsonl")
    print(f"[floorrun] arm {a.arm}: game-args {game!r}; tape {tape}", flush=True)
    tap = subprocess.Popen([py, "-u", os.path.join(TREE, "toolkit/clientscan/agenttap.py"),
                            "--agents", "1,10", "--seconds", str(a.tape_seconds), "--out", tape],
                           cwd=TREE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    threading.Thread(target=pump, args=(tap, "tap"), daemon=True).start()
    sess = subprocess.Popen([py, "-u", os.path.join(TREE, "toolkit/harness/session.py"),
                             "--exe", EXE, "--enemy", "--walk", a.walk, "--hold", str(a.hold),
                             "--settle", "0.3", "--game-args", game],
                            cwd=TREE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    threading.Thread(target=pump, args=(sess, "sess"), daemon=True).start()
    rc = sess.wait()
    print(f"[floorrun] session exited {rc}", flush=True)
    try:
        tap.wait(timeout=a.tape_seconds + 60)
    except subprocess.TimeoutExpired:
        tap.kill()
        print("[floorrun] tap killed after timeout", flush=True)
    print(f"[floorrun] tap exited {tap.returncode}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
