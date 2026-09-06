#!/usr/bin/env python3
"""What does ArenaNet's server grant when a body slides along a wall? (MOVECODE-1z-ce)

    python studies/movecode/review/wallslide.py            # the live-corpus census
    python studies/movecode/review/wallslide.py --check    # with sec.1z-ce's bars
    python studies/movecode/review/wallslide.py --list     # every blocked-ray pair

THE QUESTION. RUN-GROUNDZ-R3's stair climb sent 15 keyboard leads of ZERO length in
8 s: the client's own heading vector (0x003D's vec2) read due east on every report
while its collision slid the body 44 deg up the stairs' right side, so our lead's
ray was blocked at its first 2 u sample and `a2_clip_lead` granted the report back.
The sync copy trailed the drawn body by 100-139 u for the climb. That was first
read as a missing trapezoid (GROUNDZ-Q7); it is not -- the body never left our
mesh by more than 0.5 u -- it is a lead aimed into a wall. So: what does retail
send in that situation?

WHAT THIS MEASURES, on ArenaNet's own traffic (captures/live, origin live -- the
control corpus, never pooled with ours). For every consecutive pair of the
player's own 0x003D reports 0.2-1.5 s apart with the body moving >= 40 u between
them, the retail 0x0029 to the player issued on the first report (within 0.4 s),
and on OUR decode of that map's pathing chunk:

  * ELIGIBLE: the report's heading ray, clipped on the report's plane exactly as
    `a2_clip_lead` clips it, stops within 4 u -- the body is against a wall;
  * the candidate rules for what retail then grants, each scored by its distance
    to retail's actual grant:
      TODAY      the zero-length lead (the report itself);
      WALL-SLIDE `pathmap.wall_slide`: the next vertex of the wall the body
                 presses against, in the heading's slide direction.

It reports the eligible set split by whether retail's grant left the heading by
more than 10 deg (a slide the eye can see) or not, and the discriminator that
matters: eligibility among the pairs where retail granted ALONG the heading must
be ~zero, or the rule would be firing where the clip already agrees with retail.

THE POSITIVE CONTROL IS THE STRAIGHT SET: 1,984 pairs where heading and motion
agree, on which retail grants the 766 u chord along the heading and our clip
reproduces it to 1.5 u p50 -- the same decoder, the same meshes, scored where the
answer is known.

Read-only. Stdlib only. Needs the vault (the owner's own live captures) and the
archive (the meshes); both refuse loudly rather than printing a flattering zero.
"""
import bisect
import collections
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _p in ("toolkit", os.path.join("toolkit", "authsrv"),
           os.path.join("toolkit", "clientscan"), os.path.join("toolkit", "mapdata")):
    sys.path.insert(0, os.path.join(ROOT, _p))

import vaultpath                                            # noqa: E402
import cmsgstream                                           # noqa: E402
import resyncscore as RS                                    # noqa: E402
from pathmap import PathingMap                              # noqa: E402

CHORD = 767.0            # the client's own report-trigger chord (sec.1z-ab)
STEP = 2.0               # authsrv.A2_LEAD_CLIP_STEP
FLOOR = 4.0              # authsrv.A2_LEAD_WALL_SLIDE_FLOOR
INSTANCE_LOAD = 405      # 0x0195; vals[1] is the map's file id

# THE BARS sec.1z-ce registered off the 2026-09-06 census (20 live stamps, 2,156
# pairs). FLOORS on what must be found, RATES where the corpus can grow, and a
# SIGNATURE SET of retail vertices the rule must keep reproducing exactly --
# [[corpus-counts-redden]]: never an exact count on a corpus that gains captures.
FLOOR_PAIRS = 2000
FLOOR_ELIGIBLE = 55                 # 62 measured
FLOOR_ELIGIBLE_OFF = 30             # 33 measured (retail's grant > 10 deg off the heading)
MIN_RULE_RATE_OFF = 0.75            # 27 of 33 within 3 u measured
MIN_RULE_RATE_STRAIGHT = 0.65       # 22 of 29 measured
MAX_ELIGIBLE_ALONG_RATE = 0.03      # 0 of 124 measured
MIN_RULE_OVER_ZERO = 2.0            # the rule's hits must be at least twice the zero lead's
SIGNATURE = [                       # (fid, retail's vertex) -- exact hits on 2026-09-06
    (0x28F32, (4688.0, 366.0)), (0x287B3, (-8993.0, 1995.0)),
    (0x287B3, (10368.0, 7872.0)), (0x287B3, (-4934.0, 1122.0)),
    (0x287B3, (-7708.0, 3658.0)), (0x26529, (-9931.0, 10003.0)),
]


def _vecs(vals):
    return [v for v in vals if isinstance(v, (list, tuple)) and len(v) >= 2
            and all(isinstance(z, (int, float)) for z in v[:2])]


def _clip_len(pm, x, y, ex, ey, plane):
    """The lead clip as a2_clip_lead runs it: the sliver origin, then the plane term."""
    if not pm.walkable(x, y):
        n = pm.nearest_walkable(x, y, 16.0)
        if n is None:
            return None
        x, y = n[0], n[1]
    pl = pm.plane_at(x, y, prefer=plane)
    s = pm.clip(x, y, ex, ey, step=STEP, plane=pl)
    return math.hypot(s[0] - x, s[1] - y)


def pairs():
    """Every scored report pair across the live corpus."""
    root = vaultpath.require_dir("captures", "live",
                                 why="the retail control: ArenaNet's own grants")
    tracks = {t["label"]: t for t in RS.retail_tracks()}
    meshes = {}
    out = []
    for st in sorted(os.listdir(root)):
        try:
            c2s = cmsgstream.timed(st, "c2s", "game")
            s2c = cmsgstream.timed(st, "s2c", "game")
        except Exception:                                   # noqa: BLE001
            continue
        fids, grants, reps = {}, collections.defaultdict(list), collections.defaultdict(list)
        for t, conn, op, vals in s2c:
            if (op == INSTANCE_LOAD and conn not in fids and len(vals) > 1
                    and isinstance(vals[1], int)):
                fids[conn] = vals[1]
            elif op == 0x29:
                a = vals[1] if len(vals) > 1 and isinstance(vals[1], int) else None
                vv = _vecs(vals)
                if a is not None and vv:
                    grants[conn].append((t, a, float(vv[0][0]), float(vv[0][1])))
        for t, conn, op, vals in c2s:
            if op != 0x3D:
                continue
            vv = _vecs(vals)
            if len(vv) < 2:
                continue
            plane = vals[2] if len(vals) > 2 and isinstance(vals[2], int) else 0
            reps[conn].append((t, float(vv[0][0]), float(vv[0][1]), plane,
                               float(vv[1][0]), float(vv[1][1])))
        for conn, R in reps.items():
            tr = tracks.get("%s %s" % (st, conn))
            aid = tr.get("player_agent") if tr else None
            fid = fids.get(conn)
            if aid is None or fid is None:
                continue
            if fid not in meshes:
                try:
                    meshes[fid] = PathingMap.load(fid)
                except Exception as e:                      # noqa: BLE001
                    print("  [mesh] 0x%X unavailable: %s" % (fid, e))
                    meshes[fid] = None
            pm = meshes[fid]
            if pm is None:
                continue
            R.sort()
            G = sorted(g for g in grants.get(conn, []) if g[1] == aid)
            gt = [g[0] for g in G]
            for i in range(len(R) - 1):
                t1, x1, y1, pl, hx, hy = R[i]
                t2, x2, y2, _, _, _ = R[i + 1]
                dt = t2 - t1
                mx, my = x2 - x1, y2 - y1
                m, hm = math.hypot(mx, my), math.hypot(hx, hy)
                if not (0.2 <= dt <= 1.5) or m < 40.0 or hm < 1.0:
                    continue
                j = bisect.bisect_left(gt, t1 - 0.05)
                g = G[j] if j < len(G) and G[j][0] <= t1 + 0.4 else None
                if g is None:
                    continue
                gx, gy = g[2], g[3]
                gl = math.hypot(gx - x1, gy - y1)
                cosv = (mx * hx + my * hy) / (m * hm)
                ang = math.degrees(math.acos(max(-1.0, min(1.0, cosv))))
                if gl > 1.0:
                    c2 = ((gx - x1) * hx + (gy - y1) * hy) / (gl * hm)
                    off = math.degrees(math.acos(max(-1.0, min(1.0, c2))))
                else:
                    off = 0.0
                ex, ey = x1 + CHORD * hx / hm, y1 + CHORD * hy / hm
                L = _clip_len(pm, x1, y1, ex, ey, pl)
                rec = dict(st=st, fid=fid, t=t1, x=x1, y=y1, plane=pl, hx=hx, hy=hy,
                           slide=ang > 20.0, off=off, g=(gx, gy), gl=gl, clip=L,
                           eligible=(L is not None and L < FLOOR))
                if rec["eligible"]:
                    pt, why = pm.wall_slide(x1, y1, hx, hy, pl, chord=CHORD)
                    rec["rule"], rec["rule_why"] = pt, why
                    rec["rule_err"] = math.hypot(pt[0] - gx, pt[1] - gy) if pt else None
                out.append(rec)
    return out


def main(argv):
    check = "--check" in argv
    rows = pairs()
    straight = [r for r in rows if not r["slide"]]
    slides = [r for r in rows if r["slide"]]
    along = [r for r in slides if r["off"] <= 10.0]
    off = [r for r in slides if r["off"] > 10.0]
    elig = lambda sel: [r for r in sel if r["eligible"]]           # noqa: E731
    print("live corpus: %d moving report pairs with a retail grant on the first report" % len(rows))
    print("  straight (heading within 20 deg of the motion): %d, eligible (ray blocked at the body) %d"
          % (len(straight), len(elig(straight))))
    print("  slides retail granted ALONG the heading (<= 10 deg): %d, eligible %d"
          % (len(along), len(elig(along))))
    print("  slides retail granted OFF the heading (> 10 deg): %d, eligible %d"
          % (len(off), len(elig(off))))
    stats = {}
    for name, sel in (("off-heading slides", off), ("straight", straight)):
        E = elig(sel)
        zero = sum(1 for r in E if r["gl"] <= 30.0)
        got = [r for r in E if r.get("rule") is not None]
        errs = sorted(r["rule_err"] for r in got)
        hit3 = sum(1 for v in errs if v <= 3.0)
        hit30 = sum(1 for v in errs if v <= 30.0)
        stats[name] = dict(n=len(E), zero=zero, hit3=hit3, hit30=hit30)
        if E:
            print("  %s, eligible %d: TODAY's zero lead within 30 u of retail's grant %d | "
                  "WALL-SLIDE computed %d, err p50 %.1f p90 %.1f, within 3 u %d, 30 u %d"
                  % (name, len(E), zero, len(got), errs[len(errs) // 2] if errs else -1,
                     errs[int(0.9 * len(errs))] if errs else -1, hit3, hit30))
    sig_hits = []
    for fid, v in SIGNATURE:
        ok = any(r["fid"] == fid and r.get("rule") is not None
                 and math.hypot(r["rule"][0] - v[0], r["rule"][1] - v[1]) <= 1.0
                 and math.hypot(r["g"][0] - v[0], r["g"][1] - v[1]) <= 1.0
                 for r in rows if r["eligible"])
        sig_hits.append((fid, v, ok))
    print("  signature vertices reproduced: %d of %d" % (sum(1 for s in sig_hits if s[2]), len(SIGNATURE)))
    if "--list" in argv:
        print("\nevery eligible pair (retail's grant | the rule):")
        for r in sorted((r for r in rows if r["eligible"]), key=lambda r: (r["st"], r["t"])):
            pt = r.get("rule")
            print("  %s 0x%X t %8.2f at (%7.0f,%7.0f) pl %2d h (%5.0f,%5.0f) %s | retail (%7.0f,%7.0f) %4.0f u, %3.0f deg off | rule %s err %s [%s]"
                  % (r["st"], r["fid"], r["t"], r["x"], r["y"], r["plane"], r["hx"], r["hy"],
                     "slide" if r["slide"] else "straight", r["g"][0], r["g"][1], r["gl"], r["off"],
                     ("(%.0f,%.0f)" % pt) if pt else "none",
                     ("%.0f" % r["rule_err"]) if r.get("rule_err") is not None else "-", r.get("rule_why")))
    if not check:
        return 0
    print("\n--check, against sec.1z-ce's registered bars")
    bad = 0

    def bar(ok, text):
        nonlocal bad
        print("  [%s] %s" % ("PASS" if ok else "FAIL", text))
        bad += 0 if ok else 1

    so, ss = stats["off-heading slides"], stats["straight"]
    bar(len(rows) >= FLOOR_PAIRS, "pairs %d >= %d" % (len(rows), FLOOR_PAIRS))
    n_el = len(elig(rows))
    bar(n_el >= FLOOR_ELIGIBLE, "eligible (ray blocked at the body) %d >= %d" % (n_el, FLOOR_ELIGIBLE))
    bar(so["n"] >= FLOOR_ELIGIBLE_OFF, "eligible off-heading slides %d >= %d" % (so["n"], FLOOR_ELIGIBLE_OFF))
    rate_along = (len(elig(along)) / len(along)) if along else 0.0
    bar(rate_along <= MAX_ELIGIBLE_ALONG_RATE,
        "DISCRIMINATOR: eligibility among slides retail granted along the heading %.3f <= %.2f "
        "(the rule may not fire where the clip already agrees with retail)" % (rate_along, MAX_ELIGIBLE_ALONG_RATE))
    r_off = so["hit3"] / so["n"] if so["n"] else 0.0
    bar(r_off >= MIN_RULE_RATE_OFF, "wall-slide within 3 u of retail on off-heading slides %d of %d = %.2f >= %.2f"
        % (so["hit3"], so["n"], r_off, MIN_RULE_RATE_OFF))
    r_st = ss["hit3"] / ss["n"] if ss["n"] else 0.0
    bar(r_st >= MIN_RULE_RATE_STRAIGHT, "wall-slide within 3 u of retail on straight pairs %d of %d = %.2f >= %.2f"
        % (ss["hit3"], ss["n"], r_st, MIN_RULE_RATE_STRAIGHT))
    bar(so["hit30"] >= MIN_RULE_OVER_ZERO * max(1, so["zero"]),
        "KNOWN-BAD ARM: the rule's hits %d >= %.0fx the zero lead's %d on off-heading slides"
        % (so["hit30"], MIN_RULE_OVER_ZERO, so["zero"]))
    for fid, v, ok in sig_hits:
        bar(ok, "signature vertex 0x%X (%.0f, %.0f) reproduced exactly" % (fid, v[0], v[1]))
    print("--check: %s" % ("ALL BARS HELD" if bad == 0 else "%d BAR(S) FAILED" % bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
