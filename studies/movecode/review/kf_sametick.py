"""KILLFAR H6 / LEADRETIRE: player swings in the tick of a follow (a new follow, or an `APPROACH re-path`).

For every launch, the count of own `attack_started: player` (0x00A0) within 25 ms AFTER an own 0x002A -- split into new
follows (`APPROACH:`) and re-paths (`APPROACH re-path`). One row per launch.

    python studies/movecode/review/kf_sametick.py                  # the 15 calibration launches + K1 N1 K2 N2 K3
    python studies/movecode/review/kf_sametick.py LABEL=STAMP ...  # extra launches (gamesrv stamp, e.g. 20261004T195308-c1)

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); scorer of record for "KILLFAR H6's '0 same-tick
swings' FAILED as written, on both arms alike (1-4 per launch)" (FINDINGS 1z-ds.45), and "LEADRETIRE carried 0-1 per
launch on both arms (6 of its 8 launches)". The original read wf9-table/pt_table.json for the 15 calibration stamps and
kf_check.locate for K1..K3's; here PB.RUNS + PB.lr_runs() + PB.KF_RUNS name them (ids resolved from the same logs).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pt_build as PB  # noqa: E402

runs = {}
for lab, _set, _arm, _note, st, _tap in PB.RUNS + PB.lr_runs():
    runs.setdefault(lab, st)
for k in ("K1", "N1", "K2", "N2", "K3"):
    runs[k] = PB.KF_RUNS["k" + k][1]
for a in sys.argv[1:]:
    lab, st = a.split("=", 1)
    runs[lab] = st
for run, st in runs.items():
    tape = PB.load_tape(st)
    starts = [r for r in tape if r.get("kind") == "sent" and r.get("opcode") == 0xA0 and "attack_started: player" in r.get("label", "")]
    newf = [r for r in tape if r.get("kind") == "sent" and r.get("opcode") == 0x2A and r.get("label", "").startswith("APPROACH:")]
    rep = [r for r in tape if r.get("kind") == "sent" and r.get("opcode") == 0x2A and r.get("label", "").startswith("APPROACH re-path")]
    a = sum(1 for f in newf if any(0 <= s["t"] - f["t"] < 0.025 for s in starts))
    b = sum(1 for f in rep if any(0 <= s["t"] - f["t"] < 0.025 for s in starts))
    print(f"{run:5s} new follows {len(newf):3d} same-tick swing {a}   re-paths {len(rep):3d} same-tick swing {b}")
