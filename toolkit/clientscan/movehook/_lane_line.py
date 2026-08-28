"""LANE: does the body land where a STRAIGHT LINE from the click origin toward the
click destination, walked at run speed, would have put it?

Scratch instrument for the r2 capture. Not a published tool.
"""
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "mapdata"))
import readhook  # noqa: E402

BIN = r"C:/gd/Rurik/vault/research/movecode/r2/movehook.bin"
SPEED = 288.0          # u/s, PINNED -- the sync copy's measured walk speed
LOCAL = 0x21B3D158
SYNC = 0x21B3EC40

cap = readhook.Capture(BIN)
names = readhook.site_names(cap)
f = readhook._f
idx = {n: i for i, n in enumerate(names)}
for i, r in enumerate(cap.recs):
    r["_i"] = i


def nm(r):
    return names[r["site"]] if r["site"] < len(names) else str(r["site"])


def pt(r, key="point"):
    return (f(r[key][0]), f(r[key][1]))


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


# ---------------------------------------------------------------- clicks ----
# chcli_point (the click-to-move entry) is followed IN THE SAME TICK by the
# MapFindPath it issues; the query carries from/to dereferenced at capture time.
clicks = []
for r in cap.recs:
    if r["site"] != idx["mapfindpath"]:
        continue
    if (r["retaddr"] - cap.base + readhook.static_base()) != 0x0081AF56:
        continue          # the snap gate's own query, not a click
    hp = r.get("have_pts", 0)
    if hp != 3:
        continue
    clicks.append({"t": r["tick"], "S": pt(r, "pt_a"), "D": pt(r, "pt_b"),
                   "i": r["_i"]})
clicks.sort(key=lambda c: c["t"])
print(f"{len(clicks)} click-to-move gestures with both endpoints captured")

# ------------------------------------------------------------ objects -------
objs = {}
for r in cap.recs:
    if r.get("have_agent"):
        objs.setdefault(r["ecx"], []).append(r)

# --------------------------------------------------------- displacements ----
disp = []
pairs_total = 0
for addr, seq in objs.items():
    for k in range(1, len(seq)):
        p, q = seq[k - 1], seq[k]
        pairs_total += 1
        if q["ptime"] != p["ptime"]:
            continue
        d = dist(pt(p), pt(q))
        if not (math.isfinite(d) and d > 1.0):
            continue
        disp.append({"addr": addr, "p": p, "q": q, "d": d, "t": q["tick"]})
disp.sort(key=lambda x: x["t"])
print(f"{len(disp)} displacement(s) over {pairs_total} adjacent same-object pairs")


def straight_pred(c, t):
    """Where a body leaving c['S'] at c['t'] toward c['D'] at SPEED is at tick t."""
    S, D = c["S"], c["D"]
    L = dist(S, D)
    if L <= 0:
        return S, 0.0
    travelled = SPEED * (t - c["t"]) / 1000.0
    fr = min(1.0, travelled / L)
    return (S[0] + (D[0] - S[0]) * fr, S[1] + (D[1] - S[1]) * fr), travelled


def perp_along(c, P):
    S, D = c["S"], c["D"]
    ux, uy = D[0] - S[0], D[1] - S[1]
    L = math.hypot(ux, uy)
    if L <= 0:
        return float("nan"), float("nan")
    ux, uy = ux / L, uy / L
    vx, vy = P[0] - S[0], P[1] - S[1]
    along = vx * ux + vy * uy
    perp = vx * (-uy) + vy * ux
    return perp, along / L


print("\n" + "=" * 78)
print("PRIMARY: the straight-line-from-click-origin predictor, SPEED PINNED 288 u/s")
print("=" * 78)
print(f"{'#':>3} {'dt s':>6} {'jump u':>7} {'|pred-q|':>9} {'|pred-p|':>9} "
      f"{'perp q':>8} {'perp p':>8} {'frac':>6}  verdict")
rows = []
for n_, dd in enumerate(disp):
    prior = [c for c in clicks if c["t"] <= dd["t"]]
    if not prior:
        print(f"{n_:>3}  no prior click")
        continue
    c = prior[-1]
    P, travelled = straight_pred(c, dd["t"])
    q, p = pt(dd["q"]), pt(dd["p"])
    dq, dp = dist(P, q), dist(P, p)
    perp_q, fr_q = perp_along(c, q)
    perp_p, _ = perp_along(c, p)
    v = "LANDS ON the line-walk" if dq < dp else "does NOT"
    rows.append({"i": n_, "c": c, "dd": dd, "P": P, "dq": dq, "dp": dp,
                 "perp_q": perp_q, "perp_p": perp_p, "fr": fr_q,
                 "dt": (dd["t"] - c["t"]) / 1000.0, "trav": travelled})
    print(f"{n_:>3} {(dd['t']-c['t'])/1000.0:6.2f} {dd['d']:7.0f} {dq:9.1f} "
          f"{dp:9.1f} {perp_q:8.1f} {perp_p:8.1f} {fr_q:6.2f}  {v}")

won = sum(1 for r in rows if r["dq"] < r["dp"])
print(f"\nmodel picks the LANDING over the pre-jump position: {won}/{len(rows)}")
dqs = sorted(r["dq"] for r in rows)
dps = sorted(r["dp"] for r in rows)
print(f"  |pred - landing|   min {dqs[0]:.0f}  p50 {dqs[len(dqs)//2]:.0f}  "
      f"max {dqs[-1]:.0f} u   (n={len(dqs)})")
print(f"  |pred - pre-jump|  min {dps[0]:.0f}  p50 {dps[len(dps)//2]:.0f}  "
      f"max {dps[-1]:.0f} u")
print(f"  |perp| landing: p50 {sorted(abs(r['perp_q']) for r in rows)[len(rows)//2]:.0f} u"
      f"   |perp| pre-jump: p50 "
      f"{sorted(abs(r['perp_p']) for r in rows)[len(rows)//2]:.0f} u")

# ------------------------------------------------------------- NULL A -------
print("\n" + "=" * 78)
print("NULL A: the same landings scored against a DIFFERENT click's line")
print("=" * 78)
alt = []
for r in rows:
    q = pt(r["dd"]["q"])
    for c2 in clicks:
        if c2 is r["c"]:
            continue
        P2, _ = straight_pred(c2, r["dd"]["t"])
        alt.append(dist(P2, q))
alt.sort()
print(f"n = {len(alt)} landing x other-click pairs")
print(f"  |pred_other - landing|  min {alt[0]:.0f}  p10 {alt[len(alt)//10]:.0f}  "
      f"p50 {alt[len(alt)//2]:.0f}  max {alt[-1]:.0f} u")
print(f"  fraction under 200 u: {sum(1 for d in alt if d < 200)}/{len(alt)} "
      f"({100.0*sum(1 for d in alt if d < 200)/len(alt):.1f}%)  "
      f"[own-click: {sum(1 for r in rows if r['dq'] < 200)}/{len(rows)}]")

random.seed(7)
wins = 0
TRIALS = 20000
for _ in range(TRIALS):
    perm = clicks[:]
    random.shuffle(perm)
    w = 0
    for k, r in enumerate(rows):
        c2 = perm[k % len(perm)]
        P2, _ = straight_pred(c2, r["dd"]["t"])
        if dist(P2, pt(r["dd"]["q"])) < dist(P2, pt(r["dd"]["p"])):
            w += 1
    if w >= won:
        wins += 1
print(f"  permutation test (random click assignment, {TRIALS} trials): "
      f"P(>= {won}/{len(rows)} wins) = {wins/TRIALS:.4f}")

# ------------------------------------------------------------- NULL B -------
print("\n" + "=" * 78)
print("NULL B / VACUITY: how far apart are the two hypotheses at the yank tick?")
print("=" * 78)
seps = sorted(r["dd"]["d"] for r in rows)
print(f"  |pre-jump - landing| (the model's resolving power): "
      f"min {seps[0]:.0f}  p50 {seps[len(seps)//2]:.0f}  max {seps[-1]:.0f} u")
print(f"  model error p50 {dqs[len(dqs)//2]:.0f} u is "
      f"{100.0*dqs[len(dqs)//2]/seps[len(seps)//2]:.0f}% of the separation")

# -------------------------------------------- POSITIVE CONTROL: non-yank ----
print("\n" + "=" * 78)
print("POSITIVE CONTROL: the same predictor over ORDINARY body samples")
print("=" * 78)
print("If the straight-line predictor tracks the body ALWAYS, it is not a test of")
print("the yank. Score every local-copy sample inside a click window against it.")
ok = 0
allsamp = []
for c_i, c in enumerate(clicks):
    t_end = clicks[c_i + 1]["t"] if c_i + 1 < len(clicks) else 10 ** 12
    L = dist(c["S"], c["D"])
    for r in objs[LOCAL]:
        if not (c["t"] <= r["tick"] < t_end):
            continue
        P, trav = straight_pred(c, r["tick"])
        if trav > L:
            continue        # the line-walk has arrived; nothing left to predict
        d = dist(P, pt(r))
        allsamp.append((c_i, r["tick"], d))
allsamp.sort(key=lambda x: x[2])
ds = [d for _c, _t, d in allsamp]
print(f"  n = {len(ds)} local-copy samples inside a click window, before arrival")
print(f"  |pred - body|  p10 {ds[len(ds)//10]:.0f}  p50 {ds[len(ds)//2]:.0f}  "
      f"p90 {ds[9*len(ds)//10]:.0f}  max {ds[-1]:.0f} u")
print(f"  under 200 u: {sum(1 for d in ds if d < 200)}/{len(ds)} "
      f"({100.0*sum(1 for d in ds if d<200)/len(ds):.1f}%)")
