"""H2/H4 positive control for the target-death release on OUR tapes: every DEAD event the
loader decodes (0xF1 word gaining 0x10), whose agent it is, whether it is the chain's
target (the last own S4 target), the real prop-8 state there, and our [8,0] lag after it.
Also the press_stop refusals by reason (the click-freeze door: a held start with the
keyboard latch newer than any order of ours).

PREDICTION (before running): DEAD decodes on every tape that killed something (positive
control: the party deaths on 200929); chain-target deaths with a hold up are rare (<= 5
over seven tapes); our release lag after the target's death <= 0.06 s (the next tick).

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); the positive control behind FINDINGS 1z-ds.31's
"0 owner exposure: no hostile died on the seven tapes" -- one row per owner tape (h_core.TAPES) listing every decoded
dead bit (the party deaths on 200929 are the positive control), whether it was the chain's target, and our release lag.

    python studies/movecode/review/h_ours_deaths.py
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h_core as C  # noqa: E402

for name, _ in C.TAPES:
    ev, flags = C.ours(name)
    tgt = None
    state = 0
    deaths = []
    ps = collections.Counter()
    for j, e in enumerate(ev):
        if e["k"] == "S4":
            tgt = e["a"]
        if e["k"] == "H":
            state = e["a"]
        if e["k"] == "EV:press_stop":
            r = e["a"]
            ps[(bool(r.get("fired")), r.get("why"), r.get("mode"))] += 1
        if e["k"] == "DEAD":
            rel = None
            for x in ev[j + 1:]:
                if x["t"] - e["t"] > 3.0:
                    break
                if x["k"] == "H" and x["a"] == 0:
                    rel = round(x["t"] - e["t"], 3)
                    break
            deaths.append((round(e["t"], 3), e["a"], "TARGET" if e["a"] == tgt else "", state, rel))
    print(name, "deaths:", deaths)
    print("    press_stop rows:", dict(ps))
