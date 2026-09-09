#!/usr/bin/env python3
"""Drive RUN-NPCTRACK-Q10 (two hostiles) agent-driven: the agenttap tape and the harness
together, no human at the keys. Same shape as studies/movecode/review/floorrun.py.

    python studies/npctrack/review/q10run.py            # tape q10-agenttap.jsonl
    python studies/npctrack/review/q10run.py --label b  # a second run, tape q10b-agenttap.jsonl

The tape lands at vault/research/npctrack/q10<label>-agenttap.jsonl; the capture is
whichever gamesrv file overlaps it (w0score.find_gamesrv). Score with
    python studies/npctrack/review/npcdrift.py <tape> [--agent 11]
    python studies/movecode/review/sessionscore.py
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
# RUN-1zCE's stairs script, as RUN-Q10.md registers it.
WALK = "wait:3 W:9 wait:5 Q:2 W:3 wait:8"
GAME = "--map 146 --explorable --enemies 2 --no-enemy-skills --enemy-hit 0.02 --skills 0,0,0,0,0,0,0,0"


def pump(proc, tag):
    for line in proc.stdout:
        sys.stdout.write(f"[{tag}] {line}")
        sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--label", default="", help="suffix on the tape name (q10<label>-agenttap.jsonl)")
    ap.add_argument("--walk", default=WALK)
    ap.add_argument("--game", default=GAME)
    ap.add_argument("--tape-seconds", type=int, default=150)
    ap.add_argument("--hold", type=int, default=15)
    a = ap.parse_args()
    py = sys.executable
    out_dir = vaultpath.vault_path("research", "npctrack")
    os.makedirs(out_dir, exist_ok=True)
    tape = os.path.join(out_dir, f"q10{a.label}-agenttap.jsonl")
    print(f"[q10run] game-args {a.game!r}; walk {a.walk!r}; tape {tape}", flush=True)
    tap = subprocess.Popen([py, "-u", os.path.join(TREE, "toolkit/clientscan/agenttap.py"),
                            "--agents", "1,10,11", "--seconds", str(a.tape_seconds),
                            "--wait", "300", "--out", tape],
                           cwd=TREE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    threading.Thread(target=pump, args=(tap, "tap"), daemon=True).start()
    sess = subprocess.Popen([py, "-u", os.path.join(TREE, "toolkit/harness/session.py"),
                             "--exe", EXE, "--enemy", "--walk", a.walk, "--hold", str(a.hold),
                             "--shots", "2.0", "--game-args", a.game],
                            cwd=TREE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    threading.Thread(target=pump, args=(sess, "sess"), daemon=True).start()
    rc = sess.wait()
    print(f"[q10run] session exited {rc}", flush=True)
    try:
        tap.wait(timeout=a.tape_seconds + 60)
    except subprocess.TimeoutExpired:
        tap.kill()
        print("[q10run] tap killed after timeout", flush=True)
    print(f"[q10run] tap exited {tap.returncode}", flush=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
