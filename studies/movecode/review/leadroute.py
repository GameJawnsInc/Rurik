#!/usr/bin/env python3
"""Which map, and which heading, can actually carry an UNCLIPPED keyboard lead?

    python studies/movecode/review/leadroute.py                    # score the candidates
    python studies/movecode/review/leadroute.py --map 0x287B3      # one mesh
    python studies/movecode/review/leadroute.py --map 0x1B97D --from 9826,8077

RUN-1zAH's exposure lesson, made answerable at the desk (MOVECODE-1z-ai.3). That
run's floor demanded ">= 8 KBD LEAD grants" and got 25-33 -- but only **2-4 per
run** survived `a2_clip_lead` at full length. The rest were `origin-unwalkable`
(the client's reported point is off OUR mesh, so the lead degrades to a
zero-distance grant) or mesh-clipped short. The arm under test is a 520 u lead
MATURING, so the run measured a quarter of what its floor certified.

The fix is not a bigger number in the sheet: it is a ROUTE that produces the
arm. This scores a mesh for exactly the thing the server does at the lead site
-- `pm.walkable(origin)` then `pm.clip(origin -> origin + 520*u)` -- over a grid
of origins and a fan of headings, and reports the fraction of (origin, heading)
pairs on which a lead would go out at FULL LENGTH.

It answers three questions the run sheet needs:
  * which mesh can carry the arm at all (`clear` fraction, whole map);
  * where on that mesh to stand (the best origins, and their radius of clear
    headings);
  * which headings from a given start -- so a --walk script can be written
    against geometry rather than hope.

Read-only. Uses the same PathingMap the server loads, so a lead this scores as
`clear` is one `a2_clip_lead` will pass. Needs the archive (a vault machine);
without it, it says so rather than guessing.
"""
import argparse
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "mapdata"))

LEAD = 520.0            # authsrv.KBD_SYNC_LEAD
CLIP_STEP = 2.0         # authsrv.A2_LEAD_CLIP_STEP -- the same fineness

# The candidates, by the file id the server hands the client (content/maps.toml).
CANDIDATES = [
    (0x1B97D, "Ascalon City / Lakeside County (RUN-1zAH's route)", (9826.0, 8077.0)),
    (0x287B3, "Isle of the Nameless", (-6036.0, -2519.0)),
    (0x345CC, "Kamadan, Jewel of Istan", (-9067.0, 13218.0)),
]


def clear_at(pm, x, y, heading, lead=LEAD):
    """Exactly what a2_clip_lead would do with this origin and heading.

    -> "origin-unwalkable" / "clipped" / "clear".  The server's own order
    (MOVECODE-1z-bg): walkable(origin) first; an origin the mesh holds within
    SEAM_TOL of an edge is admitted when plane_near can name its plane (here
    with no report word, so only a sole candidate counts) and its ray then
    takes the plane clip; an origin further off, or on an ambiguous sliver,
    gets a zero-distance lead and never reaches the clip. This twin exists to
    score meshes, so it mirrors the server's order rather than re-deriving it
    -- when a2_clip_lead moves, this moves with it.
    """
    plane = None
    if not pm.walkable(x, y):
        if not (hasattr(pm, "on_mesh") and hasattr(pm, "plane_near") and pm.on_mesh(x, y)):
            return "origin-unwalkable"
        plane = pm.plane_near(x, y)
        if plane is None:
            return "origin-unwalkable"
    dx, dy = math.cos(heading), math.sin(heading)
    tx, ty = x + lead * dx, y + lead * dy
    sx, sy = (pm.clip(x, y, tx, ty, step=CLIP_STEP, plane=plane) if plane is not None
              else pm.clip(x, y, tx, ty, step=CLIP_STEP))
    if abs(sx - tx) < 1e-6 and abs(sy - ty) < 1e-6:
        return "clear"
    return "clipped"


def fan(pm, x, y, n=16, lead=LEAD):
    """(clear, clipped, unwalkable, [clear headings in degrees]) at one point."""
    out = {"clear": 0, "clipped": 0, "origin-unwalkable": 0}
    good = []
    for i in range(n):
        h = 2.0 * math.pi * i / n
        v = clear_at(pm, x, y, h, lead)
        out[v] += 1
        if v == "clear":
            good.append(round(math.degrees(h)))
        if v == "origin-unwalkable":
            # the origin decides for every heading; no point fanning
            return out["clear"], out["clipped"], n, []
    return out["clear"], out["clipped"], out["origin-unwalkable"], good


def bounds(pm):
    xs, ys = [], []
    for t in pm.trapezoids:
        xs += [t.x_top_left, t.x_top_right, t.x_bottom_left, t.x_bottom_right]
        ys += [t.y_top, t.y_bottom]
    return min(xs), max(xs), min(ys), max(ys)


def score_map(pm, name, step=256.0, n_head=16, lead=LEAD, top=8):
    x0, x1, y0, y1 = bounds(pm)
    print("  extent  x %.0f..%.0f   y %.0f..%.0f   (%d planes, %d trapezoids)"
          % (x0, x1, y0, y1, len(pm.planes), len(pm.trapezoids)))
    tot = {"clear": 0, "clipped": 0, "origin-unwalkable": 0}
    best = []
    nx = max(1, int((x1 - x0) / step))
    ny = max(1, int((y1 - y0) / step))
    for i in range(nx):
        for j in range(ny):
            x = x0 + (i + 0.5) * step
            y = y0 + (j + 0.5) * step
            c, cl, un, good = fan(pm, x, y, n_head, lead)
            tot["clear"] += c
            tot["clipped"] += cl
            tot["origin-unwalkable"] += un
            if c:
                best.append((c, x, y, good))
    n = sum(tot.values()) or 1
    print("  a %.0f u lead from a grid of origins x %d headings:  "
          "clear %5.1f%%   clipped %5.1f%%   origin-unwalkable %5.1f%%"
          % (lead, n_head, 100.0 * tot["clear"] / n,
             100.0 * tot["clipped"] / n,
             100.0 * tot["origin-unwalkable"] / n))
    best.sort(key=lambda r: -r[0])
    if best:
        print("  best origins (clear headings of %d):" % n_head)
        for c, x, y, good in best[:top]:
            print("    (%8.0f, %8.0f)  %2d/%d clear   headings %s"
                  % (x, y, c, n_head, good[:10]))
    else:
        print("  NO origin on this mesh carries a full-length lead in any "
              "direction.")
    return tot, best


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", default=None,
                    help="file id (0x... or decimal); default scores the candidates")
    ap.add_argument("--from", dest="start", default=None, metavar="X,Y",
                    help="fan this one point instead of gridding the map")
    ap.add_argument("--lead", type=float, default=LEAD)
    ap.add_argument("--step", type=float, default=256.0)
    ap.add_argument("--headings", type=int, default=16)
    a = ap.parse_args()

    try:
        from pathmap import PathingMap
    except Exception as e:                                     # noqa: BLE001
        raise SystemExit("no pathmap module (%r)" % e)

    todo = CANDIDATES
    if a.map:
        fid = int(a.map, 16) if a.map.lower().startswith("0x") else int(a.map)
        todo = [(fid, "map 0x%X" % fid, None)]

    for fid, name, spawn in todo:
        print("\n0x%X  %s" % (fid, name))
        try:
            pm = PathingMap.load(fid)
        except Exception as e:                                 # noqa: BLE001
            print("  no mesh: %r" % e)
            continue
        if a.start:
            sx, sy = (float(v) for v in a.start.split(","))
            c, cl, un, good = fan(pm, sx, sy, a.headings, a.lead)
            print("  at (%.0f, %.0f): %d/%d clear, %d clipped, %s"
                  % (sx, sy, c, a.headings, cl,
                     "ORIGIN OFF MESH" if un == a.headings else "%d unwalkable" % un))
            if good:
                print("  clear headings (deg): %s" % good)
            continue
        score_map(pm, name, step=a.step, n_head=a.headings, lead=a.lead)
        if spawn:
            c, cl, un, good = fan(pm, spawn[0], spawn[1], a.headings, a.lead)
            print("  AT THE SPAWN (%.0f, %.0f): %d/%d clear%s"
                  % (spawn[0], spawn[1], c, a.headings,
                     "  -- ORIGIN OFF MESH" if un == a.headings else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
