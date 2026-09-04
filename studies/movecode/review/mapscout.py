#!/usr/bin/env python3
"""Which map can carry a CLICK router probe? (MOVECODE-1z-at)

    python studies/movecode/review/mapscout.py            # every explorable map
    python studies/movecode/review/mapscout.py --map 90

WHAT THIS IS FOR. sec.1z-ar needs a routed multi-waypoint click path under a tape, and
sec.1z-as found the bind on map 146: its only click-reachable route-forcing
geometry IS the bridge, and a PROP takes the click and walks the body straight at
it instead of routing. The way out named there was "a map whose routing obstacles
are terrain rather than props". This is that search.

TWO THINGS ARE MEASURED, and the second is the one that matters.

  1. ROUTE-FORCING DENSITY -- the share of (origin, bearing, range) triples at
     CLICK range where the straight chord is blocked but a route exists. That is
     what makes the string pull run at all. Map 146 scores near zero, which is
     why a blind fan there produced nothing but `verbatim`.

  2. THE BLOCKING OBSTACLE'S SIZE, as the prop-vs-terrain discriminator, because
     we carry NO PROP GEOMETRY and cannot ask what a hole is. A prop carves a
     COMPACT hole -- a building or a bridge footprint, tens to a couple of
     hundred units. Terrain -- a cliff, a canyon wall, a water body -- is a LONG
     BARRIER. So the unwalkable region around the blocking point is flood-filled
     on a grid and its extent reported: compact holes are prop-like and eat
     clicks, big ones are terrain and do not.

THAT DISCRIMINATOR IS A PROXY AND IS LABELLED AS ONE. It cannot see a prop; it
infers one from a footprint, and a large building or a small island would each
fool it. What it is for is RANKING candidates for a run, not deciding what a hole
is -- and the run itself carries the real sensor (`clickcal.py`: off-mesh
destination = the click hit a prop or the void), so a wrong guess here costs a
run, not a finding.

Read-only over the archive's meshes. Needs a vault machine. Stdlib only.
"""
import argparse
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "mapdata"))

CLIP_STEP = 8.0
CELL = 48.0              # flood-fill cell; a prop footprint spans a few of these
FLOOD_CAP = 400          # cells; past this the region is "big" and we stop
COMPACT_U = 260.0        # a hole smaller than this across is prop-shaped
CLICK_RANGES = (300.0, 450.0, 600.0)

# The explorable maps content/maps.toml can actually serve, so a candidate here
# is one the harness can be pointed at without new content work.
MAPS = [
    (146, 0x1B97D, "Lakeside County"),
    (474, 219215, "Domain of Anguish"),
    (558, 287493, "Sparkfly Swamp"),
    (90, 46594, "Lornar's Pass"),
    (280, 0x287B3, "Isle of the Nameless"),
]


def hole_extent(pm, x, y, cap=FLOOD_CAP):
    """How big is the unwalkable region containing (x, y)? -> (units across, capped).

    Grid flood fill. Returns the bounding-box diagonal in world units and whether
    the cap was hit -- a capped region is BIG, which is the answer we want, so
    the cap costs nothing.
    """
    start = (int(x // CELL), int(y // CELL))
    seen = {start}
    stack = [start]
    minx = maxx = start[0]
    miny = maxy = start[1]
    while stack and len(seen) < cap:
        cx, cy = stack.pop()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (cx + dx, cy + dy)
            if n in seen:
                continue
            wx, wy = (n[0] + 0.5) * CELL, (n[1] + 0.5) * CELL
            if pm.walkable(wx, wy):
                continue
            seen.add(n)
            stack.append(n)
            minx, maxx = min(minx, n[0]), max(maxx, n[0])
            miny, maxy = min(miny, n[1]), max(maxy, n[1])
    across = math.hypot((maxx - minx + 1) * CELL, (maxy - miny + 1) * CELL)
    return across, len(seen) >= cap


def scout(pm, name, mid, samples, rnd):
    origins = []
    tries = 0
    while len(origins) < samples and tries < samples * 40:
        tries += 1
        t = pm.trapezoids[rnd.randrange(len(pm.trapezoids))]
        ox, oy = t.centre
        if pm.walkable(ox, oy):
            origins.append((ox, oy))
    tested = forcing = 0
    compact = big = 0
    exemplars = []
    for ox, oy in origins:
        for k in range(6):
            th = 2 * math.pi * (k + rnd.random()) / 6.0
            L = rnd.choice(CLICK_RANGES)
            dx, dy = ox + L * math.cos(th), oy + L * math.sin(th)
            if not pm.walkable(dx, dy):
                continue
            tested += 1
            sx, sy = pm.clip(ox, oy, dx, dy, step=CLIP_STEP)
            if math.hypot(dx - sx, dy - sy) < 1.0:
                continue                       # straight line is fine, no routing
            r = pm.route(ox, oy, dx, dy)
            if not r or len(r) <= 2:
                continue                       # unroutable, or a straight answer
            forcing += 1
            # the blocking point is just past where the clip stopped
            f = (math.hypot(sx - ox, sy - oy) + CLIP_STEP) / max(L, 1e-6)
            bx, by = ox + (dx - ox) * min(f, 1.0), oy + (dy - oy) * min(f, 1.0)
            if pm.walkable(bx, by):
                continue
            across, capped = hole_extent(pm, bx, by)
            if capped or across >= COMPACT_U:
                big += 1
                if len(exemplars) < 4:
                    exemplars.append((round(across) if not capped else ">cap",
                                      len(r),
                                      tuple(round(v) for v in (ox, oy)),
                                      tuple(round(v) for v in (dx, dy))))
            else:
                compact += 1
    dens = 100.0 * forcing / max(tested, 1)
    terr = 100.0 * big / max(forcing, 1)
    print("%-22s map %-4d  chords %5d  route-forcing %4d (%4.1f%%)   "
          "terrain-shaped %4d (%4.0f%%)  prop-shaped %d"
          % (name, mid, tested, forcing, dens, big, terr, compact))
    for e in exemplars:
        print("      e.g. hole %-6s across, %d waypoints,  %s -> %s" % e)
    return dens, terr, big


# --- emitting the walk script ---------------------------------------------
# The camera calibration MOVECODE-1z-as measured and then confirmed
# predictively: yaw:1500 (=120 deg) produced a click bearing of 240.0.
PX_PER_DEG = 12.5
RUN_SPEED = 288.0
CLICK_FY = 0.46          # ~420-620 u on level ground (sec.1z-as.3)
SPAWNS = {146: (9826.0, 8077.0)}


def yaw_to(bearing, facing):
    """`yaw:N` pixels to swing the camera from `facing` to `bearing`.

    Positive yaw turns the view RIGHT and the click bearing DECREASED by 24 deg
    per 300 px, so the pixel count carries a negative sign against the bearing
    delta. Wrapped to +-180 so the camera never takes the long way round.
    """
    d = (facing - bearing + 180.0) % 360.0 - 180.0
    return int(round(d * PX_PER_DEG)), bearing


def emit_script(pm, mid, spot, dest, settle=1.5):
    """A walk string that WALKS to `spot` and then CLICKS toward `dest`.

    The walk legs come from the mesh's own route, one yaw+W pair per leg, so
    the plan follows walkable ground rather than a straight line through it.

    ASSUMED AND NOT VERIFIED HERE: that `W` walks along the CAMERA's forward,
    the same axis the click calibration measured. It is the natural reading and
    the spawn's own facing agrees (an unyawed click came back at bearing 0.0,
    due east), but the run's tape is what checks it -- if W follows something
    else, the body lands somewhere else and `clickcal.py` will say so.
    """
    sp = SPAWNS.get(mid)
    if sp is None:
        return None
    path = pm.route(sp[0], sp[1], spot[0], spot[1])
    if not path:
        return None
    steps = ["wait:3"]
    facing = 0.0                      # the spawn's own camera forward
    for a, b in zip(path, path[1:]):
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        if L < 40.0:
            continue
        brg = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 360.0
        px, facing = yaw_to(brg, facing)
        if px:
            steps.append("yaw:%d" % px)
        steps.append("W:%.1f" % (L / RUN_SPEED))
    brg = math.degrees(math.atan2(dest[1] - spot[1], dest[0] - spot[0])) % 360.0
    px, facing = yaw_to(brg, facing)
    if px:
        steps.append("yaw:%d" % px)
    for _ in range(4):
        steps.append("click:0.5,%.2f" % CLICK_FY)
        steps.append("wait:3")
    return " ".join(steps)


def nearest_forcing(pm, spawn, rnd, want=40, tries_cap=40000):
    """The terrain-shaped route-forcing spot closest ON FOOT to the spawn.

    Distance is the MESH's route length, not the straight line: a spot 2 km away
    across a lake is not near. -> (walk_u, stand, click_at, bearing, waypoints).
    """
    hits = []
    tries = 0
    while len(hits) < want and tries < tries_cap:
        tries += 1
        t = pm.trapezoids[rnd.randrange(len(pm.trapezoids))]
        ox, oy = t.centre
        if not pm.walkable(ox, oy):
            continue
        th = rnd.uniform(0, 2 * math.pi)
        L = rnd.choice(CLICK_RANGES)
        dx, dy = ox + L * math.cos(th), oy + L * math.sin(th)
        if not pm.walkable(dx, dy):
            continue
        sx, sy = pm.clip(ox, oy, dx, dy, step=CLIP_STEP)
        if math.hypot(dx - sx, dy - sy) < 1.0:
            continue
        r = pm.route(ox, oy, dx, dy)
        if not r or len(r) <= 2:
            continue
        f = (math.hypot(sx - ox, sy - oy) + CLIP_STEP) / max(L, 1e-6)
        bx, by = ox + (dx - ox) * min(f, 1.0), oy + (dy - oy) * min(f, 1.0)
        if pm.walkable(bx, by):
            continue
        across, capped = hole_extent(pm, bx, by)
        if not (capped or across >= COMPACT_U):
            continue
        walk = pm.route(spawn[0], spawn[1], ox, oy)
        if not walk:
            continue
        wlen = sum(math.hypot(b[0] - a[0], b[1] - a[1])
                   for a, b in zip(walk, walk[1:]))
        hits.append((wlen, (round(ox), round(oy)), (round(dx), round(dy)),
                     math.degrees(math.atan2(dy - oy, dx - ox)) % 360.0, len(r)))
    hits.sort()
    return hits[0] if hits else None


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", type=int, help="only this map id")
    ap.add_argument("--samples", type=int, default=90, help="origins per map")
    ap.add_argument("--script", action="store_true",
                    help="emit a walk string that reaches the nearest "
                         "terrain-shaped route-forcing spot and clicks there")
    a = ap.parse_args()

    from pathmap import PathingMap
    rnd = random.Random(20260904)
    print("Route-forcing geometry at CLICK range (%s u), and whether the blocking\n"
          "hole is COMPACT (prop-shaped, eats the click) or BIG (terrain).\n"
          % ", ".join("%.0f" % r for r in CLICK_RANGES))
    best = []
    for mid, fid, name in MAPS:
        if a.map and mid != a.map:
            continue
        try:
            pm = PathingMap.load(fid)
        except (OSError, KeyError, ValueError) as e:
            print("%-22s map %-4d  NOT LOADABLE (%r)" % (name, mid, e))
            continue
        d, terr, big = scout(pm, name, mid, a.samples, rnd)
        best.append((big, d, terr, name, mid))
    if not best:
        print("\nno mesh loaded -- this needs the archive, i.e. a vault machine.")
        return 1
    best.sort(reverse=True)
    print("\nRANKED by terrain-shaped route-forcing chords (what a click probe needs):")
    for big, d, terr, name, mid in best:
        print("  %-22s map %-4d  %4d such chords   density %4.1f%%   terrain share %3.0f%%"
              % (name, mid, big, d, terr))
    top = best[0]
    print("\n  -> %s (map %d) is the candidate." % (top[3], top[4]))
    print("     The size test is a PROXY for 'is it a prop' and cannot see one; the "
          "RUN carries\n     the real sensor (clickcal.py: an off-mesh destination "
          "IS the prop signature).")

    if a.script:
        mid = a.map or top[4]
        if mid not in SPAWNS:
            print("\n  no spawn on file for map %d, so no script." % mid)
            return 0
        fid = dict((m, f) for m, f, _ in MAPS)[mid]
        pm = PathingMap.load(fid)
        sp = SPAWNS[mid]
        near = nearest_forcing(pm, sp, rnd)
        if not near:
            print("\n  found no terrain-shaped route-forcing spot reachable on foot.")
            return 0
        wlen, spot, dest, brg, wp = near
        print("\n  NEAREST terrain-shaped route-forcing spot on map %d:" % mid)
        print("    stand at %s, click toward %s (bearing %.0f, %d waypoints)"
              % (spot, dest, brg, wp))
        print("    %.0f u of walking from the spawn -- about %.0f s at run speed"
              % (wlen, wlen / RUN_SPEED))
        s = emit_script(pm, mid, spot, dest)
        print("\n  --walk %r" % s)
        print("\n  The walk legs are the MESH's own route, one yaw+W pair per leg, so"
              "\n  the plan follows walkable ground. That W follows the CAMERA's"
              "\n  forward is assumed, not verified here -- the run's tape checks it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
