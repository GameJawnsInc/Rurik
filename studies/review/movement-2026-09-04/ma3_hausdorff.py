"""M-A3 refuter: Hausdorff gap distribution between OUR route() and the CLIENT's
answer on r7's comparable rows (map 0x287B3). Read-only, prints only.
Thresholds: 16 u (pathdiff AGREE), 100 u (reprieve band), 299.33 u (gate 1)."""
import os, sys, math
TK = r"C:\gd\Rurik\toolkit"
sys.path.insert(0, TK); sys.path.insert(0, os.path.join(TK, "mapdata"))
sys.path.insert(0, os.path.join(TK, "clientscan", "movehook"))
import readhook, pathdiff
from pathmap import PathingMap
from archive import Archive, file_id_table
cap = readhook.Capture(r"C:\gd\Rurik\vault\research\movecode\r7\movehook.bin")
names = readhook.site_names(cap); pairs, _ = pathdiff.answered(cap, names)
ar = Archive(); table = file_id_table(ar)
pm = PathingMap.load(0x287B3, archive=ar, table=table)
gaps = []; chord_gaps = []; bent_gaps = []
for q, r in pairs:
    if not (r.get("have_out", 0) & 1): continue
    theirs = r["out_count"]
    if not theirs or q.src is None or q.dst is None: continue
    whole = (r.get("have_out", 0) & 2) and r["out_n"] >= theirs
    if not whole: continue
    x0, y0, x1, y1 = q.src[0], q.src[1], q.dst[0], q.dst[1]
    if not (pm.walkable(x0, y0) and pm.walkable(x1, y1)): continue
    ours = pm.route(x0, y0, x1, y1)
    if not ours: continue
    g = pathdiff._hausdorff(ours, pathdiff._their_poly(q, r, theirs))
    gaps.append(g)
    if theirs >= 2:
        bent_gaps.append(g)
        if len(ours) <= 2: chord_gaps.append(g)
def summ(label, v):
    v = sorted(v); n = len(v)
    if not n: return print(label, "n=0")
    q = lambda f: v[min(n - 1, int(f * n))]
    print(f"{label} n={n} >16u={sum(1 for g in v if g > 16)} >100u={sum(1 for g in v if g > 100)} "
          f">299u={sum(1 for g in v if g > 299.33)} p50={q(.5):.1f} p90={q(.9):.1f} max={v[-1]:.1f}")
summ("ALL comparable rows", gaps)
summ("client bent (>=2 pts) rows", bent_gaps)
summ("client bent, ours 2-pt chord", chord_gaps)
