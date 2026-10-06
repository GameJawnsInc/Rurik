"""TRAILPIN controls (FINDINGS 1z-ds.48): per launch, the run verdict, assert count, stale-pair census, same-tick swings
on NEW follows and on `APPROACH re-path`s, and late kills.

    python studies/movecode/review/tp_controls.py [--logs DIR]
        --logs DIR   read each launch's verdict / assert count from DIR/run-tp-<RUN>.txt (else the harness report.json)

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0): `tp_controls.py`. Scorer of record for "same-tick swings
on follow re-paths 0-6 per launch on both arms (T 7, N 10), 0 on new follows" (FINDINGS 1z-ds.48, Controls) -- the numbers
the 1z-ds.48 text files under tp_score.py. The tape of each launch comes from pt_build.TP_RUNS (the original read the
scratchpad's run-tp-<RUN>.txt and the harness report.json named in it).
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tp_score as TS  # noqa: E402   (the locate() roster/verdict logic; imports c_rows, pt_build)
import stalepair  # noqa: E402
PB = TS.PB

args = sys.argv[1:]
if args and args[0] == "--logs":
    TS.LOGS = args[1]
for run in ("T1", "N1", "T2", "N2", "T3", "N3", "T4", "N4"):
    _tap, st, v, asserts = TS.locate(run)
    lp = os.path.join(TS.LOGS, f"run-tp-{run}.txt") if TS.LOGS else None
    if lp and os.path.exists(lp):      # the original counted these two patterns only (tp_score's locate adds Code=0)
        asserts = len(re.findall(r"(?i)assertion|crash dump", open(lp, encoding="utf-8", errors="replace").read().replace("\x00", "")))
    tape = PB.load_tape(st)
    sp = stalepair.census(tape)
    starts = [r for r in tape if r.get("kind") == "sent" and r.get("opcode") == 0xA0 and "attack_started: player" in r.get("label", "")]
    newf = [r for r in tape if r.get("kind") == "sent" and r.get("opcode") == 0x2A and r.get("label", "").startswith("APPROACH:")]
    rp = [r for r in tape if r.get("kind") == "sent" and r.get("opcode") == 0x2A and r.get("label", "").startswith("APPROACH re-path")]
    a = sum(1 for f in newf if any(0 <= s["t"] - f["t"] < 0.025 for s in starts))
    b = sum(1 for f in rp if any(0 <= s["t"] - f["t"] < 0.025 for s in starts))
    v = v[-1:]
    late = sum(1 for r in tape if r.get("kind") == "sent" and r.get("opcode") == 0x29 and "(late" in r.get("label", ""))
    print(f"{run}: {v} asserts {asserts} stalepair {sp['pairs']}/{sp['split']}/{sp['bare']} same-tick new {a} re-path {b} late kills {late}")
