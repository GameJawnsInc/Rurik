"""H2 (retail): the death release, row by row.  Split by |release - next due start| <= 0.05 s
('at-due') vs not; for each: release - dead bit, release - last own LAND, whether the dead
bit shares a batch with an own LAND, whether a [3,0] rides the release, and the window
between the last start and its landing (did the swing in flight land before the death?).

PREDICTION (before running): the not-at-due rows are kills during a SWING IN FLIGHT that
never landed (the target died to someone else in our windup) -> released at the death's
batch or the landing instant; the at-due rows are kills by our own landing.

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); scorer of record for retail's target-death
release ("released at the chain's next scheduled event, [3] for a swing in flight, 20 of 20"), published as FINDINGS
1z-ds.31 ("Recorded, not changed").

    python studies/movecode/review/h_retail_death.py
"""
import collections
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h_core as C  # noqa: E402
import h_retail_release as R  # noqa: E402
import h_retail_release2 as R2  # noqa: E402

P = R2.periods()
rows = []
for name, ev in C.retail():
    ps = P.get(name, [])
    state = 0
    tgt = None
    last_start = None
    last_land = None
    landed_since_start = True
    dead_at = {}
    started_in_ep = False
    for j, e in enumerate(ev):
        k = e["k"]
        if k == "DEAD":
            dead_at[e["a"]] = (e["t"], j, landed_since_start)
        if k == "S4":
            tgt = e["a"]
            last_start = e["t"]
            landed_since_start = False
            if state == 1:
                started_in_ep = True
        if k in ("LAND", "L"):
            last_land = e["t"]
            landed_since_start = True
        if k != "H":
            continue
        if e["a"] == 1:
            if state == 0:
                started_in_ep = any(x["k"] == "S4" and e["t"] - x["t"] <= 0.005 for x in ev[max(0, j - 6):j])
            state = 1
            continue
        if state != 1:
            continue
        state = 0
        if not started_in_ep:
            continue
        tR = e["t"]
        inp = any(x["d"] == "c2s" and x["k"] != "ROT" and tR - x["t"] <= 0.08 for x in ev[max(0, j - 40):j])
        if inp or tgt not in dead_at or not (-1.5 <= dead_at[tgt][0] - tR <= 0.05):
            continue
        dt, dj, landed_before_death = dead_at[tgt]
        dlo, dhi = R.batch(ev, dj)
        land_in_dead_batch = any(x["k"] == "LAND" for x in ev[dlo:dhi + 1])
        lo, hi = R.batch(ev, j)
        tags = [R.TAG[x["k"]](x) for x in ev[lo:hi + 1] if x["k"] in R.TAG]
        per = R2.period_at(ps, tR)
        due = last_start + per
        rows.append(dict(name=name[:30], tR=round(tR, 3), dead=round(tR - dt, 3),
                         land=round(tR - last_land, 3) if last_land else None,
                         due=round(tR - due, 3), per=per, landed_before_death=landed_before_death,
                         land_in_dead_batch=land_in_dead_batch, st3="3:0" in tags,
                         start_to_dead=round(dt - last_start, 3)))
at = [r for r in rows if abs(r["due"]) <= 0.05]
off = [r for r in rows if abs(r["due"]) > 0.05]
print("death releases", len(rows), "at-due", len(at), "off-due", len(off))
for grp, rs in (("at-due", at), ("off-due", off)):
    print("==", grp)
    print("   landed before death:", collections.Counter(r["landed_before_death"] for r in rs),
          " LAND in the dead bit's batch:", collections.Counter(r["land_in_dead_batch"] for r in rs),
          " [3,0] in the release:", collections.Counter(r["st3"] for r in rs))
    for key in ("dead", "land", "start_to_dead"):
        xs = sorted(r[key] for r in rs if r[key] is not None)
        if xs:
            print(f"   release-{key}: p10 {xs[len(xs)//10]:.3f} p50 {statistics.median(xs):.3f} p90 {xs[(9*len(xs))//10]:.3f}")
    for r in rs[:12]:
        print("    ", r)
