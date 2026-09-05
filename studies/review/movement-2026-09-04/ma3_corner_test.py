"""M-A3 refuter desk check (READ-ONLY, prints only).

Question: are the CLIENT's own tier-3 intermediate waypoints (r7 ret-tap corpus,
map 280 / file 0x287B3) bit-exact trapezoid CORNERS of our decode, the way
retail's part-way grants are (13/19, movecode FINDINGS 1p.6)?  And how do OUR
route() waypoints for the same queries classify?  Also: on the 'bent' rows where
ours is a 2-point chord, is the straight chord clear on our mesh (seam_clip)?
"""
import os, sys, math, collections
TK = r"C:\gd\Rurik\toolkit"
sys.path.insert(0, TK); sys.path.insert(0, os.path.join(TK, "mapdata"))
sys.path.insert(0, os.path.join(TK, "clientscan", "movehook"))
import readhook, pathdiff
from pathmap import PathingMap
from archive import Archive, file_id_table

cap = readhook.Capture(r"C:\gd\Rurik\vault\research\movecode\r7\movehook.bin")
names = readhook.site_names(cap)
pairs, notes = pathdiff.answered(cap, names)
print("pairs", len(pairs), "notes", notes)
ar = Archive(); table = file_id_table(ar)
pm = PathingMap.load(0x287B3, archive=ar, table=table)
_f = readhook._f

corners = set()
edges = []   # (x0,y0,x1,y1)
for t in pm.trapezoids:
    tl = (t.x_top_left, t.y_top); tr = (t.x_top_right, t.y_top)
    bl = (t.x_bottom_left, t.y_bottom); br = (t.x_bottom_right, t.y_bottom)
    for c in (tl, tr, bl, br):
        corners.add(c)
    edges.append((tl, tr)); edges.append((bl, br)); edges.append((tl, bl)); edges.append((tr, br))
print("trapezoids", len(pm.trapezoids), "distinct corners", len(corners))

def seg_dist(p, a, b):
    px, py = p; ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    if L2 == 0: return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

# spatial bucket for edges
BK = 512.0
bucket = collections.defaultdict(list)
for e in edges:
    xs = (e[0][0], e[1][0]); ys = (e[0][1], e[1][1])
    for bx in range(int(min(xs) // BK), int(max(xs) // BK) + 1):
        for by in range(int(min(ys) // BK), int(max(ys) // BK) + 1):
            bucket[(bx, by)].append(e)

def edge_dist(p):
    bx, by = int(p[0] // BK), int(p[1] // BK)
    best = 1e9
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for e in bucket.get((bx + dx, by + dy), ()):
                d = seg_dist(p, e[0], e[1])
                if d < best: best = d
    return best

def classify(pts):
    """pts: intermediate waypoints (start and final dest excluded)."""
    out = collections.Counter()
    for p in pts:
        if p in corners: out["corner"] += 1
        else:
            d = edge_dist(p)
            if d <= 0.01: out["edge<=0.01"] += 1
            elif d <= 1.0: out["edge<=1"] += 1
            else: out["interior"] += 1
        if float(p[0]).is_integer() and float(p[1]).is_integer(): out["int"] += 1
    return out

client_tot = collections.Counter(); ours_tot = collections.Counter()
n_bent = 0; n_chord_ours = 0; chord_clear = 0; chord_blocked = 0
n_rows = 0; n_client_int = 0; n_client_pts = 0
first_wp_corner = collections.Counter()
leglens = []
rowsdiffer = 0
for q, r in pairs:
    if not (r.get("have_out", 0) & 1): continue
    theirs = r["out_count"]
    if not theirs: continue
    whole = (r.get("have_out", 0) & 2) and r["out_n"] >= theirs
    if not whole: continue
    if q.src is None or q.dst is None: continue
    x0, y0, x1, y1 = q.src[0], q.src[1], q.dst[0], q.dst[1]
    if not (pm.walkable(x0, y0) and pm.walkable(x1, y1)): continue
    pts = [(_f(r["out_path"][i * 4]), _f(r["out_path"][i * 4 + 1])) for i in range(theirs)]
    n_rows += 1
    if theirs >= 2:
        n_bent += 1
        inter = pts[:-1]
        c = classify(inter); client_tot += c
        fc = classify(inter[:1]); first_wp_corner += fc
        poly = [(x0, y0)] + pts
        for a, b in zip(poly, poly[1:]):
            leglens.append(math.hypot(b[0] - a[0], b[1] - a[1]))
        ours = pm.route(x0, y0, x1, y1)
        if ours:
            if len(ours) <= 2:
                n_chord_ours += 1
                # is the straight chord clear on our mesh?
                try:
                    plane = pm.plane_at(x0, y0)
                    clip = pm.seam_clip(x0, y0, x1, y1, plane)
                    cx, cy = clip[0], clip[1]
                    if math.hypot(cx - x1, cy - y1) <= 1.0: chord_clear += 1
                    else: chord_blocked += 1
                except Exception as ex:
                    print("seam_clip err", ex)
            oi = [tuple(p[:2]) for p in ours[1:-1]]
            ours_tot += classify(oi)

print(f"scorable whole rows (both endpoints on our mesh, count>0): {n_rows}; client multi-point (>=2) rows: {n_bent}")
print("CLIENT intermediate waypoints (final dest excluded):", dict(client_tot),
      "total", sum(v for k, v in client_tot.items() if k != "int"))
print("CLIENT FIRST waypoint class:", dict(first_wp_corner))
print("OURS intermediate waypoints (route() interior):", dict(ours_tot),
      "total", sum(v for k, v in ours_tot.items() if k != "int"))
print(f"rows where ours is a 2-point chord while client bent: {n_chord_ours}; "
      f"chord seam_clip clear: {chord_clear}, blocked: {chord_blocked}")
leglens.sort()
if leglens:
    def pct(p): return leglens[min(len(leglens) - 1, int(p * len(leglens)))]
    print(f"client leg lengths n={len(leglens)} p10 {pct(.1):.0f} p50 {pct(.5):.0f} p90 {pct(.9):.0f} max {leglens[-1]:.0f}")
# vacuity: random walkable points
import random
random.seed(7)
xs = [t.x_top_left for t in pm.trapezoids]; ys = [t.y_top for t in pm.trapezoids]
rnd = []
while len(rnd) < 300:
    x = random.uniform(min(xs), max(xs)); y = random.uniform(min(ys), max(ys))
    if pm.walkable(x, y): rnd.append((x, y))
print("VACUITY random walkable 300:", dict(classify(rnd)))
