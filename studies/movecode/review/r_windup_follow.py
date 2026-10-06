"""S-2 retail: does retail's server send the observer a FOLLOW (0x002A [me]) inside its own windup?

PREDICTION (stated before the run): 0 server 0x002A [me] inside an own windup with no own c2s
input since the start -- retail lets the swing finish and re-approaches after the landing; and
among windups whose TARGET moved (a 0x0029/0x002A/0x0025 naming T inside the windup), the
re-approach, when there is one, comes after the landing.

Per own attack_started [4, me, T] on every live connection: the windup runs to the first own
[3, me, 0] (CANCEL), [1, me] / own 0x00A4 (LANDED), or 1.0 s. Inside it: own c2s inputs, s2c
0x002A / 0x0029 / 0x0028 / 0x002C naming me, and target movement. After a LANDED windup, the
first s2c 0x002A [me] within 1.5 s with no own input before it (the post-landing re-approach).

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); scorer of record for "0 server 0x002A [me]
inside 1,654 own windups; the target moved in 86, 76 landed; re-approaches 18 of 18 at or after the landing, 13 in
the landing's batch", published as FINDINGS 1z-ds.28 (Retail).

    python studies/movecode/review/r_windup_follow.py
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rlib  # noqa: E402

INPUT = (0x26, 0x27, 0x46, 0x3D, 0x3E, 0x47, 0x28, 0x39, 0x3F)
tot = collections.Counter()
rows = []
post = collections.Counter()
for c in rlib.conns():
    me = c["me"]
    R = c["merged"]
    for si, r in enumerate(R):
        if not rlib.is_prop(r, 0xA0, 4, me):
            continue
        t0, T = r[0], rlib.i(r[3][3])
        tot["starts"] += 1
        end = outcome = None
        inp = False
        f_in = []
        tmoved = False
        for j in range(si + 1, len(R)):
            t, d, op, v = R[j]
            if t - t0 > 1.0:
                break
            if d == "c2s" and op in INPUT:
                inp = True
            if rlib.is_prop(R[j], 0x9F, 3, me):
                end, outcome = j, "CANCEL"
                break
            if rlib.is_prop(R[j], 0x9F, 1, me) or rlib.mine(R[j], me, (0xA4,)):
                end, outcome = j, "LANDED"
                break
            if d == "s2c" and op in (0x29, 0x2A, 0x25) and len(v) > 1 and rlib.i(v[1]) == T:
                tmoved = True
            if rlib.mine(R[j], me, (0x2A,)):
                f_in.append((round(t - t0, 3), inp))
        tot[outcome or "OPEN"] += 1
        if tmoved:
            tot["target-moved"] += 1
            tot[f"target-moved:{outcome}"] += 1
        if f_in:
            tot["follow-in-windup"] += 1
            if not f_in[0][1]:
                tot["follow-in-windup-no-input"] += 1
                rows.append((c["cap"], round(t0, 2), T, outcome, f_in, tmoved))
        if outcome == "LANDED" and tmoved:
            tl = R[end][0]
            for j in range(end + 1, len(R)):
                t, d, op, v = R[j]
                if t - tl > 1.5:
                    post["none"] += 1
                    break
                if d == "c2s" and op in INPUT:
                    post["input-first"] += 1
                    break
                if rlib.mine(R[j], me, (0x2A,)):
                    post[f"follow +{t - tl:.2f}"] += 1
                    break
                if rlib.is_prop(R[j], 0xA0, 4, me):
                    post["next-start-first"] += 1
                    break
print(dict(tot))
print("post-landing, target moved in the windup:", dict(post))
for x in rows[:40]:
    print("  ", x)
