"""Critic: does RETAIL ever open the player's swing in the instant of its own follow?

For every self-directed 0x002A [me, point, p, p, T] with T != 0 (a follow), the first own
attack_started (0xA0 [.., 4, me, T']) within +-0.5 s, and the gap. Symmetric: also a [4]
just BEFORE the 0x002A (|dt| <= 25 ms either side counts as "one instant").

PREDICTION (before running): 0 retail follows have their own [4] within 25 ms after them
(M2 found 0 of 5 in the band; a follow is sent because the body is out of reach).
Also: a [4] in the 25 ms BEFORE a follow is a different event (a re-approach after a start),
counted separately.

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); scorer of record for the retail control
"0 of 458 own follows carry the player's own attack start within 25 ms", published as FINDINGS 1z-ds.36 (RETAIL).

    python studies/movecode/review/c_retail_sametick.py
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import retail_conns  # noqa: E402

cs = retail_conns.conns()
n_fol = 0
after = []
before = []
gaps_after = []
for c in cs:
    me = c["me"]
    m = c["merged"]
    starts = [r[0] for r in m if r[1] == "s2c" and r[2] == 0xA0 and len(r[3]) > 2
              and r[3][1] == 4 and r[3][2] == me]
    for t, d, op, v in m:
        if d != "s2c" or op != 0x2A:
            continue
        try:
            if int(v[1]) != me or len(v) < 6 or int(v[5]) == 0:
                continue
        except (TypeError, ValueError, IndexError):
            continue
        n_fol += 1
        nxt = [s - t for s in starts if 0.0 <= s - t <= 0.5]
        prv = [t - s for s in starts if 0.0 < t - s <= 0.025]
        if nxt:
            gaps_after.append(min(nxt))
            if min(nxt) <= 0.025:
                after.append((c["cap"], round(t, 3), round(min(nxt) * 1000, 1)))
        if prv:
            before.append((c["cap"], round(t, 3), round(min(prv) * 1000, 1)))
print(f"retail own follows (0x002A [me .. T!=0]): {n_fol} over {len(cs)} observer connections")
print(f"  own [4] within 25 ms AFTER the follow: {len(after)}  {after[:10]}")
print(f"  own [4] within 25 ms BEFORE the follow: {len(before)}  {before[:10]}")
b = collections.Counter(min(int(g * 1000) // 50, 10) for g in gaps_after)
print("  first own [4] within 0.5 s after a follow, by 50 ms bins:", sorted(b.items()),
      f"n={len(gaps_after)}")
