"""S-3 retail, widened to every agent: does a death inside the dier's own windup carry [3, A, 0]?

PREDICTION (from the observer's n=1): a death with an open windup ([4, A, T] within 1.0 s before
the dead bit, no [1, A] / [3, A] / 0x00A4 [A] between) carries [3, A, 0] within 0.05 s of the
status on >= 80 %; a death with NO open windup carries it on <= 5 % (the control).

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); scorer of record for "30 of 30 open-windup
deaths carry [3, A, 0]; 0 of 155 without; 185 deaths", published as FINDINGS 1z-ds.27 (Retail).

    python studies/movecode/review/r_death_any.py
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rlib  # noqa: E402

n = collections.Counter()
ex = collections.defaultdict(list)
for c in rlib.conns():
    R = c["merged"]
    me = c["me"]
    last_start = {}      # agent -> (t, idx)
    closed = {}          # agent -> idx of last close
    deadset = set()
    for k, (t, d, op, v) in enumerate(R):
        if d != "s2c":
            continue
        if op == 0xA0 and len(v) > 3 and rlib.i(v[1]) == 4:
            last_start[rlib.i(v[2])] = (t, k)
        elif op == 0x9F and len(v) > 3 and rlib.i(v[1]) in (1, 3):
            closed[rlib.i(v[2])] = k
        elif op == 0xA4 and len(v) > 1:
            closed[rlib.i(v[1])] = k
        elif op == 0xF1 and len(v) > 2:
            A, w = rlib.i(v[1]), rlib.i(v[2]) or 0
            if w & 16 and A not in deadset:
                deadset.add(A)
                st = last_start.get(A)
                openw = st is not None and t - st[0] < 1.0 and closed.get(A, -1) < st[1]
                into = None if not openw else round(t - st[0], 3)
                got3 = False
                for j in range(k + 1, min(len(R), k + 40)):
                    tj, dj, opj, vj = R[j]
                    if tj - t > 0.05:
                        break
                    if dj == "s2c" and opj == 0x9F and len(vj) > 3 and rlib.i(vj[1]) == 3 and rlib.i(vj[2]) == A:
                        got3 = True
                        break
                who = "me" if A == me else "other"
                key = f"{who}:{'open' if openw else 'none'}:{'[3]' if got3 else 'no[3]'}"
                n[key] += 1
                if openw and len(ex[key]) < 6:
                    ex[key].append((c["cap"], round(t, 2), A, into))
            elif not (w & 16) and A in deadset:
                deadset.discard(A)
for k in sorted(n):
    print(f"{k:24s} {n[k]}")
for k, v in ex.items():
    print(k, v)
