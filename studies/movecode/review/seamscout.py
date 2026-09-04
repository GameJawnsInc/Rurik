#!/usr/bin/env python3
"""Click chords whose ROUTE crosses a BLIND plane seam (MOVECODE-1z-ba).

    python studies/movecode/review/seamscout.py --census        # every blind seam on the map
    python studies/movecode/review/seamscout.py                 # chords that cross one, ranked
    python studies/movecode/review/seamscout.py --script        # ... and the walk string
    python studies/movecode/review/seamscout.py --selftest      # bare machine

WHAT THIS IS FOR. sec.1z-ar established from the code that the router's string
pull is plane-blind -- `_visible` answers `clip() == end` and clip() asks "inside
any trapezoid, on ANY plane" -- so the pull can undo the A*'s plane discipline and
neither it nor route()'s final gate would notice. What it could NOT establish was
whether that ever fires, because every desk instrument it built assumed
portal-linked trapezoids OVERLAP in 2D, and its own positive control found 92 of
300 known portals that way (31%). sec.1z-az then produced the first routed grant
under a tape and it crossed no seam at all. This file is the targeting pass
sec.1z-az.4 asked for.

WHAT A LINK IS, measured first because the first version of this file got it
wrong and its own control said so (47%). `_cross` is a CLUSTER relation: every
trapezoid sitting on portal P is linked to every trapezoid sitting on P's
partner, so two linked trapezoids are usually NOT adjacent -- the median
corner-to-corner gap between linked pairs on map 146 is 139 u, max 1,082. And
they never stack: over the file's cross-plane links no centre sits inside the
other trapezoid. So "is this plane change legitimate?" is not "are both planes
present here" (never, at a seam -- sec.1z-ar's failed control) and not "is
every linked pair adjacent" (never, for a cluster) but: at the point where the
walk changes plane, is there a portal between the two sides.

AND THE PORTAL TRAPEZOIDS ARE LINES. The third version learned this from the
nearest candidate it produced: plane 18 is a 1 km strip whose two portals are
`p18#1 y 5579..5579` and `p18#2 y 4532..4532` -- ZERO-HEIGHT trapezoids lying
along the strip's end edges, linked to zero-height plane-0 twins on the same
lines. The strip's body trapezoids link to nothing; the crossing is carried by
the lines. A point test half a unit either side of a seam never lands on such
a line, so a leg walking straight through a portal was being scored BLIND. The
link test therefore gathers every trapezoid within SEAM_TOL of the seam point
-- lines included -- on each side, and asks `_cross` about all the pairs.

A SEAM IS DIRECTIONAL, and the second version of this file learned that from
its walker control (0 of 65 blind pairs agreed). Most cross-plane pairs that
meet in 2D are STACKED -- a large plane-20 or plane-37 trapezoid lying over a
thin plane-0 band -- and a body walking across the band's edge never changes
plane, because the plane it is on continues. What a body experiences is: it is
on plane P, it reaches the edge of its trapezoid, and P does NOT continue on
the far side -- only some other plane Q does. THAT is a seam, from P's side.
The same edge seen from Q's side may be no seam at all (the ground continuing
under a deck's edge is a seam for the deck, not for the ground).

TWO MEASUREMENTS.

  1. THE BLIND-SEAM CENSUS walks EVERY trapezoid t's boundary a few units
     outside it and asks containing() what is there. If t's own plane is
     present, that is an in-plane edge (possibly under something) and not a
     seam. Otherwise every trapezoid there is on another plane and the step
     is a plane change for a body on t: LINKED if the file carries a portal
     between t and any trapezoid at that point, BLIND if not. A directed pair
     t -> u whose blind stretch is at least MIN_SEAM long is a BLIND SEAM;
     shorter meetings are CORNERS of the decomposition and set aside.
     Plane-blind clip() walks straight across a blind seam; the A* never
     would.
     POSITIVE CONTROL: every cross-plane portal pair in the file that links
     anything (21 of 189 on map 146 have an EMPTY plane-0 side and link
     nothing) must show up as at least one adjacent linked pair.

  2. THE PER-LEG WALKER. `seam_crossings(a, b, plane)` samples a segment at
     the server's own gate step (2 u) carrying the body's plane -- the leg's
     corridor plane from route(with_planes=True), the same word the grant
     puts on the wire -- and reports a crossing wherever that plane ENDS
     underfoot, bisecting to the seam and naming the trapezoids within half
     a unit of it on both sides. Linked if any pair across it is a portal.
     Without a plane it carries whatever planes the start point offers and a
     crossing is when all of them end, which is the plane-blind reading and
     what the census's control drives it with. By construction the A*
     corridor only steps across links, so a blind crossing in route()'s
     OUTPUT is the sightline's doing -- the pull or the shared-edge fallback.

THE FILTER puts them together: chords at click range aimed across each blind
seam whose route() carries a blind-seam leg, ranked by walking distance from
the spawn and by a BASIN score -- the share of chords perturbed by the run's
known error budget (an arrival ~120 u off, a bearing ~3 deg off, a range
running 0.75x-1.6x; sec.1z-az measured all three) that STILL route across a
blind seam. A chord with a small basin is a chord one run will miss.

WHAT A RUN THEN ASKS, and this file does not answer it: whether the CLIENT walks
a blind-seam leg. The tape (`agenttap.py`) reads the drawn body; a body that
parks while the sync copy walks, then snaps, is RUN-1zAO's signature and the
harm. A body that walks it is an honest null for this seam class.

Read-only over the archive's meshes. Stdlib only. The census and the filter
need a vault machine; --selftest builds its own five-trapezoid map and runs on
a bare one.
"""
import argparse
import collections
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "mapdata"))

SEAM_EPS = 3.0          # how far OUTSIDE an edge the census samples
SEAM_STRIDE = 8.0       # along-edge sampling stride
MIN_SEAM = 12.0         # shorter than this is a corner touch, not a seam
WALK_STEP = 2.0         # the server's own gate step (A2_LEAD_CLIP_STEP)
SEAM_HALF = 0.5         # the walker names the trapezoids this close to the seam
SEAM_TOL = 1.0          # ... and looks for portal LINES within this of it
CLICK_RANGES = (300.0, 400.0, 500.0, 600.0)
STAND_OFF = (160.0, 240.0, 320.0)    # origin's distance back from the seam
# The run's error budget, each term MEASURED: sec.1z-az arrived 118 u off over
# 10.5 km; sec.1z-ay predicts bearing to 1.02 deg mean / 1.81 max, and the
# blind yaw calibration held to 0.0 at one check, so 3 deg is generous; the
# range ran 561 u against ~350 predicted (1.6x) with sec.1z-ay's P2 unresolved.
BASIN_ORIGIN_R = 120.0
BASIN_BEARING = (-3.0, 0.0, 3.0)
BASIN_RANGE = (0.75, 1.0, 1.3, 1.6)


def flat(pm, t):
    return pm._flat_index(t)


def is_linked(pm, fa, fb):
    """Does the file carry a portal between these two trapezoids (flat ids)?"""
    return fb in pm._cross.get(fa, ()) or fa in pm._cross.get(fb, ())


def near_trapezoids(pm, x, y, tol=SEAM_TOL):
    """Every trapezoid within `tol` of (x, y), zero-height portal lines included."""
    from pathmap import BAND, _nearest_on_trapezoid
    out = []
    seen = set()
    for b in range(int((y - tol) // BAND), int((y + tol) // BAND) + 1):
        for t in pm._bands.get(b, ()):
            if id(t) in seen:
                continue
            seen.add(id(t))
            if not (t.y_bottom - tol <= y <= t.y_top + tol):
                continue
            xmn = min(t.x_bottom_left, t.x_top_left) - tol
            xmx = max(t.x_bottom_right, t.x_top_right) + tol
            if not (xmn <= x <= xmx):
                continue
            if _nearest_on_trapezoid(t, x, y)[2] <= tol:
                out.append(t)
    return out


def linked_at(pm, s, planes_a, planes_b, tol=SEAM_TOL):
    """Is there a portal at seam point `s` from planes_a to planes_b?
    -> (bool, (flat_a, flat_b) or None, ids_a, ids_b) -- the trapezoids within
    `tol` of the point on each side, and the first linked pair among them."""
    near = near_trapezoids(pm, s[0], s[1], tol)
    A = [flat(pm, t) for t in near if t.plane in planes_a]
    B = [flat(pm, t) for t in near if t.plane in planes_b]
    for a in A:
        for b in B:
            if is_linked(pm, a, b):
                return True, (a, b), A, B
    return False, None, A, B


def boundary_pairs(t, eps=SEAM_EPS, stride=SEAM_STRIDE):
    """(outside, inside) point pairs across each of `t`'s four edges."""
    span = t.y_top - t.y_bottom
    ny = max(1, int(span / stride))
    for i in range(ny + 1):
        y = t.y_bottom + span * i / ny
        f = 0.0 if span <= 0.0 else (y - t.y_bottom) / span
        left = t.x_bottom_left + f * (t.x_top_left - t.x_bottom_left)
        right = t.x_bottom_right + f * (t.x_top_right - t.x_bottom_right)
        yield (left - eps, y), (left + eps, y)
        yield (right + eps, y), (right - eps, y)
    for yo, yi, xl, xr in ((t.y_bottom - eps, t.y_bottom + eps,
                            t.x_bottom_left, t.x_bottom_right),
                           (t.y_top + eps, t.y_top - eps,
                            t.x_top_left, t.x_top_right)):
        w = xr - xl
        nx = max(1, int(w / stride))
        for i in range(nx + 1):
            yield (xl + w * i / nx, yo), (xl + w * i / nx, yi)


def census(pm, planes=None):
    """Every plane change a body can make by stepping off a trapezoid's edge.

    -> {(ft, fu): {"planes": (pt, pu), "linked": [(out, in), ...],
                   "blind": [(out, in), ...], "via": {(a, b), ...},
                   "span": u, "kind": "seam"|"corner"}}
    DIRECTED: ft is the trapezoid stepped OFF, fu one it steps ONTO. Points
    are (outside, inside) pairs across the edge. A point is `linked` if the
    file carries a portal AT THE EDGE POINT between t's plane and the far
    side's -- `linked_at`, which sees the zero-height portal lines -- and
    `via` collects the linked pairs it found; `blind` if there is none.
    `span` is the extent of the blind points; below MIN_SEAM the pair is a
    "corner".
    """
    out = {}
    for t in pm.trapezoids:
        if planes is not None and t.plane not in planes:
            continue
        ft = flat(pm, t)
        for q, qi in boundary_pairs(t):
            there = pm.containing(*q)
            if not there or any(v.plane == t.plane for v in there):
                continue                      # mesh edge, or t's plane continues
            edge = ((q[0] + qi[0]) / 2.0, (q[1] + qi[1]) / 2.0)
            lk, via, _A, _B = linked_at(pm, edge, {t.plane},
                                        {v.plane for v in there})
            for u in there:
                key = (ft, flat(pm, u))
                rec = out.get(key)
                if rec is None:
                    rec = out[key] = {"planes": (t.plane, u.plane),
                                      "linked": [], "blind": [], "via": set(),
                                      "bbox": None}
                rec["linked" if lk else "blind"].append((q, qi))
                if lk:
                    rec["via"].add(via)
                if not lk:
                    bb = rec["bbox"]
                    if bb is None:
                        rec["bbox"] = [q[0], q[0], q[1], q[1]]
                    else:
                        bb[0], bb[1] = min(bb[0], q[0]), max(bb[1], q[0])
                        bb[2], bb[3] = min(bb[2], q[1]), max(bb[3], q[1])
    for rec in out.values():
        bb = rec.pop("bbox")
        rec["span"] = 0.0 if bb is None else math.hypot(bb[1] - bb[0], bb[3] - bb[2])
        rec["kind"] = "seam" if (rec["linked"] or rec["span"] >= MIN_SEAM) else "corner"
    return out


def blind_seams(found):
    """Directed pairs with a blind stretch at least MIN_SEAM long."""
    return {k: r for k, r in found.items()
            if r["blind"] and r["span"] >= MIN_SEAM}


def portal_control(pm, found):
    """POSITIVE CONTROL: every cross-plane PORTAL PAIR in the file that links
    anything is the `via` of at least one linked census point.
    -> (found, portal pairs, pairs with an empty side)

    Built from the same fields `_build_cross_links` reads, so a pair here is a
    pair there -- and a portal whose side carries no trapezoid produces no
    link there either, which is why it is counted rather than tested.
    """
    from pathmap import NO_PORTAL
    on = {}
    for i, t in enumerate(pm.trapezoids):
        for k in (t.portal_left, t.portal_right):
            if k != NO_PORTAL:
                on.setdefault((t.plane, k), []).append(i)
    by_pair = {}
    for row in pm.portals:
        for p in row:
            by_pair.setdefault(p.pair_id, []).append(p)
    via = set()
    for r in found.values():
        for a, b in r["via"]:
            via.add((a, b))
            via.add((b, a))
    hit = tot = empty = 0
    for grp in by_pair.values():
        if len(grp) != 2 or grp[0].plane == grp[1].plane:
            continue
        a, b = grp
        ta = on.get((a.plane, a.index), ())
        tb = on.get((b.plane, b.index), ())
        if not ta or not tb:
            empty += 1                 # links nothing; there is nothing to find
            continue
        tot += 1
        if any((i, j) in via for i in ta for j in tb):
            hit += 1
    return hit, tot, empty


def seam_crossings(pm, a, b, plane=None, step=WALK_STEP):
    """Where a body walking a->b on `plane` changes plane, and whether each
    change is a portal.

    -> [{"at": (x, y), "f": 0..1, "from": (planes), "to": (planes),
         "pair": (flat, flat), "sides": (ids_a, ids_b), "linked": bool,
         "gap": u}]

    Sampled at the server's gate step. The walker CARRIES the planes the body
    is on -- `plane` if given and present at the start, else every plane the
    start point offers -- and a sample that keeps any of them is not a
    change: so a sample landing exactly on a shared edge, which lies in BOTH
    trapezoids, neither hides a seam nor splits it (the self-test's toy does
    exactly that at x = 100), and a deck over continuing ground is a seam
    for a body on the deck and not for one on the ground. A crossing is when
    EVERY carried plane has ended. A sample in no trapezoid is carried over
    (a sub-step gap between abutting trapezoids is not a plane change).

    The seam is then BISECTED from both sides -- the last point still on a
    carried plane, the first point on the new ones -- and the link test is
    `linked_at` on the seam point: every trapezoid within SEAM_TOL of it on
    the old planes against every one on the new, portal LINES included.
    `pair` is the linked pair when there is one, else the trapezoids
    SEAM_HALF either side; `sides` is everything the link test saw. `gap`
    is the empty distance between the two sides, normally ~0.
    """
    dx, dy = b[0] - a[0], b[1] - a[1]
    dist = math.hypot(dx, dy)
    n = max(1, int(dist / step))

    def at(f):
        return (a[0] + dx * f, a[1] + dy * f)

    def planes_at(f):
        return {t.plane for t in pm.containing(*at(f))}

    carried, prev, prev_f = None, None, None
    out = []
    for i in range(n + 1):
        f = i / n
        cur = pm.containing(*at(f))
        if not cur:
            continue
        cp = {t.plane for t in cur}
        if carried is None:
            carried = {plane} if (plane is not None and plane in cp) else cp
        elif carried & cp:
            carried = carried & cp
        else:
            pp = carried
            lo, hi = prev_f, f                 # last f still on a carried plane
            for _ in range(12):
                mid = (lo + hi) / 2.0
                if planes_at(mid) & pp:
                    lo = mid
                else:
                    hi = mid
            f_old = lo
            lo, hi = prev_f, f                 # first f on the new side
            for _ in range(12):
                mid = (lo + hi) / 2.0
                if planes_at(mid) & cp:
                    hi = mid
                else:
                    lo = mid
            f_new = hi
            h = SEAM_HALF / max(dist, 1e-9)
            side_a = [t for t in pm.containing(*at(max(0.0, f_old - h)))
                      if t.plane in pp] or [t for t in prev if t.plane in pp]
            side_b = [t for t in pm.containing(*at(min(1.0, f_new + h)))
                      if t.plane in cp] or cur
            sf = (f_old + f_new) / 2.0
            lk, via, A, B = linked_at(pm, at(sf), pp, cp)
            out.append({"at": at(sf), "f": sf,
                        "from": tuple(sorted(pp)), "to": tuple(sorted(cp)),
                        "pair": via or (flat(pm, side_a[0]), flat(pm, side_b[0])),
                        "sides": (A, B),
                        "linked": lk, "gap": max(0.0, (f_new - f_old) * dist)})
            carried = cp
        prev, prev_f = cur, f
    return out


def route_seams(pm, path, planes=None):
    """Per leg of a route: its crossings, each leg walked on its corridor
    plane (route(with_planes=True)'s word for the leg's start waypoint).
    -> [(leg_index, crossing), ...]"""
    out = []
    for i, (a, b) in enumerate(zip(path, path[1:])):
        pl = planes[i] if planes else None
        for c in seam_crossings(pm, a, b, plane=pl):
            out.append((i, c))
    return out


def walker_control(pm, found, sample=300, rnd=None):
    """POSITIVE CONTROL for the walker, both ways. For directed pairs the
    census found, a short walk on the stepped-off trapezoid's plane, from a
    point inside it to the census's outside point, must report ONE crossing
    with that trapezoid on its near side whose verdict AGREES with the
    census -- linked at a linked point, blind at a blind one. A walker that
    only ever said "linked" would pass a one-sided version. Pairs whose
    start cannot be placed inside the trapezoid are not tested.
    -> (agree, tested, agree_blind, tested_blind)

    THE RESIDUAL DISAGREEMENT ON MAP 146 IS ONE CLASS, and it is recorded
    rather than tuned away: 3 of 25 blind pairs, each a portal SLIVER on the
    stepped-off plane (`p0#4870 y 24381..24398`, `p13#1 y 3541..3547`) that
    covers only part of the seam. Where it ends, the census's sample 3 u
    outside the edge clears it and says blind; the walker, bisecting to
    where the plane ends and looking SEAM_TOL around that point, finds it
    and says linked. A one-unit ambiguity at a portal's end, in the
    direction of calling FEWER legs blind -- so a leg this walker calls
    blind is blind by more than a unit.
    """
    rnd = rnd or random.Random(2)
    keys = [k for k, r in found.items() if r["kind"] == "seam"]
    if len(keys) > sample:
        keys = rnd.sample(keys, sample)
    agree = agree_b = tested_b = tested = 0
    for ft, fu in keys:
        rec = found[(ft, fu)]
        # The blind arm is tested only on a real blind STRETCH: a single
        # blind sample among linked ones is a portal line missed by one
        # edge point's tolerance, and the walker (which bisects to the seam)
        # rightly calls it linked.
        blind_ok = bool(rec["blind"]) and rec["span"] >= MIN_SEAM
        want = not blind_ok or (bool(rec["linked"]) and rnd.random() < 0.5)
        if want:
            q, qi = rec["linked"][len(rec["linked"]) // 2]
        else:
            # The INTERIOR of the blind stretch: the blind point farthest
            # from any linked point of the same pair. A portal is carried by
            # a sliver that can end mid-edge, and within SEAM_TOL of its end
            # the census (3 u outside the edge) says blind while the walker
            # (bisecting to where the plane ends) finds the sliver and says
            # linked -- a one-unit ambiguity, in the direction of calling
            # fewer legs blind, and not what this control is for.
            lk = [p for p, _i in rec["linked"]]
            q, qi = max(rec["blind"], key=lambda b: min(
                [math.hypot(b[0][0] - p[0], b[0][1] - p[1]) for p in lk] or [0.0]))
        t = pm.trapezoids[ft]
        # 9 u inside along the edge normal, or the mirror point, or a point
        # toward the centre -- a slanted edge can put the mirror outside t.
        cx, cy = t.centre
        for start in ((qi[0] + (qi[0] - q[0]), qi[1] + (qi[1] - q[1])), qi,
                      (qi[0] + (cx - qi[0]) * 0.1, qi[1] + (cy - qi[1]) * 0.1),
                      (qi[0] + (cx - qi[0]) * 0.5, qi[1] + (cy - qi[1]) * 0.5)):
            if t.contains(*start):
                break
        else:
            continue
        xs = seam_crossings(pm, start, q, plane=t.plane)
        # The crossing must be OFF t's plane; which plane-P trapezoid sits
        # within a unit of the seam is a decomposition detail (a sliver
        # between t and the edge is common) and not what is being checked.
        ok = (len(xs) == 1 and xs[0]["from"] == (t.plane,)
              and xs[0]["linked"] == want)
        tested += 1
        if not want:
            tested_b += 1
            agree_b += ok
        agree += ok
    return agree, tested, agree_b, tested_b


# --- the chord filter --------------------------------------------------------

def chord_verdict(pm, o, d):
    """One chord -> None (unroutable / no blind leg) or a record.

    Routed as the server routes it -- the body's plane at the origin and the
    clicked surface's plane at the destination as preferences (ROUTER-B4),
    corridor planes returned -- then every leg walked.
    """
    if not (pm.walkable(*o) and pm.walkable(*d)):
        return None
    r = pm.route(o[0], o[1], d[0], d[1],
                 start_plane=pm.plane_at(*o), goal_plane=pm.plane_at(*d),
                 with_planes=True)
    if not r:
        return None
    path, planes = r
    xs = route_seams(pm, path, planes)
    blind = [(i, c) for i, c in xs if not c["linked"]]
    if not blind:
        return None
    sx, sy = pm.clip(o[0], o[1], d[0], d[1], step=WALK_STEP)
    straight = math.hypot(d[0] - sx, d[1] - sy) < 1.0
    return {"origin": o, "dest": d, "path": path, "planes": planes,
            "legs": len(path) - 1, "straight_clear": straight,
            "crossings": xs, "blind": blind}


def basin(pm, o, d):
    """Share of chords inside the run's error budget that still carry a blind leg."""
    L = math.hypot(d[0] - o[0], d[1] - o[1])
    brg = math.atan2(d[1] - o[1], d[0] - o[0])
    origins = [o] + [(o[0] + BASIN_ORIGIN_R * math.cos(k * math.pi / 4),
                      o[1] + BASIN_ORIGIN_R * math.sin(k * math.pi / 4))
                     for k in range(8)]
    hit = tot = 0
    for oo in origins:
        if not pm.walkable(*oo):
            continue
        for db in BASIN_BEARING:
            th = brg + math.radians(db)
            for rf in BASIN_RANGE:
                dd = (oo[0] + L * rf * math.cos(th), oo[1] + L * rf * math.sin(th))
                tot += 1
                if chord_verdict(pm, oo, dd) is not None:
                    hit += 1
    return (hit / tot if tot else 0.0), tot


def candidates(pm, seams, spawn, rnd, per_seam=6):
    """Chords aimed ACROSS each blind seam, from either side, at click range.

    For a seam point s: an origin STAND_OFF back along a bearing, the click
    CLICK_RANGE forward along the same bearing, so the seam sits between them.
    Bearings spread around the seam's own local normal (from the census's two
    trapezoid centres).  -> [record + walk_u + seam info], unranked.
    """
    out = []
    items = list(seams.items())
    rnd.shuffle(items)
    for (fa, fb), rec in items:
        ca, cb = pm.trapezoids[fa].centre, pm.trapezoids[fb].centre
        normal = math.atan2(cb[1] - ca[1], cb[0] - ca[0])
        where = [q for q, _qi in rec["blind"]]
        made = 0
        for _ in range(per_seam * 6):
            if made >= per_seam:
                break
            s = rnd.choice(where)
            th = normal + math.radians(rnd.uniform(-35, 35))
            if rnd.random() < 0.5:
                th += math.pi                      # from the other side
            back = rnd.choice(STAND_OFF)
            L = rnd.choice(CLICK_RANGES)
            o = (s[0] - back * math.cos(th), s[1] - back * math.sin(th))
            d = (o[0] + L * math.cos(th), o[1] + L * math.sin(th))
            v = chord_verdict(pm, o, d)
            if v is None:
                continue
            walk = pm.route(spawn[0], spawn[1], o[0], o[1])
            if not walk:
                continue
            v["walk_u"] = sum(math.hypot(b[0] - a[0], b[1] - a[1])
                              for a, b in zip(walk, walk[1:]))
            v["seam"] = (rec["planes"], (fa, fb), round(rec["span"]),
                         (round(s[0]), round(s[1])))
            v["bearing"] = math.degrees(th) % 360.0
            v["range"] = L
            out.append(v)
            made += 1
    return out


def describe(v):
    o, d = v["origin"], v["dest"]
    seq = " ".join("p%d" % p for p in v["planes"])
    print("  stand (%d,%d)  click brg %.0f range %.0f -> (%d,%d)   legs %d  %s%s"
          % (o[0], o[1], v["bearing"], v["range"], d[0], d[1], v["legs"], seq,
             "   [straight chord CLEAR]" if v["straight_clear"] else ""))
    for i, c in v["blind"]:
        print("      leg %d crosses BLIND seam %s -> %s at (%d,%d), f=%.2f"
              % (i, c["from"], c["to"], c["at"][0], c["at"][1], c["f"]))
    for i, c in v["crossings"]:
        if c["linked"]:
            print("      leg %d crosses a PORTAL %s -> %s at (%d,%d)"
                  % (i, c["from"], c["to"], c["at"][0], c["at"][1]))
    pl, pair, span, s = v["seam"]
    print("      aimed at seam plane %d -> %d (traps %s, blind stretch %d u) at %s;"
          "  %.0f u walk from spawn" % (pl[0], pl[1], pair, span, s, v["walk_u"]))


# --- self-test on a synthetic map ---------------------------------------------

def _toy():
    """Eight trapezoids, flat ids in list order.

      0 A (plane 0)  x 0..100,  y 0..100   | 2 B (plane 1) x 100..200 | 3 C (plane 2) x 200..300
      1 LA (plane 0) the LINE y = 0, x 0..100 -- A's bottom edge
      4 D (plane 3)  x 300..400, y 100..200: touches C at ONE CORNER only
      5 E (plane 4)  x 150..250, y 0..100: lies OVER the B|C seam
      6 G (plane 5)  x 0..100, y -100..0: below A
      7 LG (plane 5) the LINE y = 0, x 0..100 -- G's top edge

    Links: A<->B directly (adjacent full trapezoids), and LA<->LG -- the
    file's own shape, a portal carried by two zero-height lines on the
    shared edge, with the bodies A and G linking to nothing. So A->B is a
    portal, B->C a blind seam, A->G a portal THROUGH THE LINES, C|D a corner
    that must not count, and the B|C edge is a seam for a body on B and not
    for a body on E.
    """
    from pathmap import PathingMap, Trapezoid
    A = Trapezoid(0, 0, 100.0, 0.0, 0.0, 100.0, 0.0, 100.0)
    LA = Trapezoid(0, 1, 0.0, 0.0, 0.0, 100.0, 0.0, 100.0)
    B = Trapezoid(1, 0, 100.0, 0.0, 100.0, 200.0, 100.0, 200.0)
    C = Trapezoid(2, 0, 100.0, 0.0, 200.0, 300.0, 200.0, 300.0)
    D = Trapezoid(3, 0, 200.0, 100.0, 300.0, 400.0, 300.0, 400.0)
    E = Trapezoid(4, 0, 100.0, 0.0, 150.0, 250.0, 150.0, 250.0)
    G = Trapezoid(5, 0, 0.0, -100.0, 0.0, 100.0, 0.0, 100.0)
    LG = Trapezoid(5, 1, 0.0, 0.0, 0.0, 100.0, 0.0, 100.0)
    pm = PathingMap([A, LA, B, C, D, E, G, LG], [{}] * 6)
    pm._cross = {0: [2], 2: [0], 1: [7], 7: [1]}
    return pm


def selftest():
    from checks import Ledger, adopt_named
    L = Ledger("seamscout", floor=21)
    check = adopt_named(L)
    pm = _toy()
    A, LA, B, C, D, E, G, LG = range(8)
    found = census(pm)
    seams = {k for k, r in found.items() if r["kind"] == "seam"}
    check("A->B and B->A are linked seams",
          all(k in seams and found[k]["linked"] and not found[k]["blind"]
              for k in ((A, B), (B, A))))
    check("B->C and C->B are BLIND seams",
          all(k in seams and found[k]["blind"] and not found[k]["linked"]
              for k in ((B, C), (C, B))))
    check("C|D is a CORNER, not a seam",
          found[(C, D)]["kind"] == "corner" and found[(D, C)]["kind"] == "corner")
    check("E's edges are blind seams onto B and C (E -> B, E -> C)",
          (E, B) in blind_seams(found) and (E, C) in blind_seams(found))
    check("B's right edge also steps onto E (B -> E), blind",
          (B, E) in blind_seams(found))
    check("blind seams are ~100 u long",
          all(80 < found[k]["span"] <= 106 for k in ((B, C), (C, B))))
    check("A->G is LINKED, through the lines LA<->LG, not A and G themselves",
          (A, G) in seams and found[(A, G)]["linked"] and not found[(A, G)]["blind"]
          and found[(A, G)]["via"] == {(LA, LG)}
          and not is_linked(pm, A, G))
    check("G->A likewise, via (LG, LA)",
          (G, A) in seams and not found[(G, A)]["blind"]
          and found[(G, A)]["via"] == {(LG, LA)})
    check("portal control has nothing to test on a portal-less toy",
          portal_control(pm, found) == (0, 0, 0))
    xs = seam_crossings(pm, (50.0, 50.0), (150.0, 50.0), plane=0)
    check("A->B on plane 0: one crossing, linked, at the seam",
          len(xs) == 1 and xs[0]["linked"] and abs(xs[0]["at"][0] - 100.0) < 1.0)
    xs = seam_crossings(pm, (50.0, 50.0), (50.0, -50.0), plane=0)
    check("A->G on plane 0: one crossing, LINKED via the lines, named",
          len(xs) == 1 and xs[0]["linked"] and xs[0]["pair"] == (LA, LG)
          and LA in xs[0]["sides"][0] and LG in xs[0]["sides"][1])
    xs = seam_crossings(pm, (160.0, 50.0), (240.0, 50.0), plane=1)
    check("B->C on plane 1: one crossing, BLIND, onto {2, 4}",
          len(xs) == 1 and not xs[0]["linked"] and xs[0]["to"] == (2, 4))
    check("the SAME walk on plane 4 (over the seam) crosses nothing",
          seam_crossings(pm, (160.0, 50.0), (240.0, 50.0), plane=4) == [])
    check("the same walk with NO plane carries {1, 4} and crosses nothing",
          seam_crossings(pm, (160.0, 50.0), (240.0, 50.0)) == [])
    xs = seam_crossings(pm, (50.0, 50.0), (250.0, 50.0), plane=0)
    check("A->C on plane 0: portal then blind",
          [x["linked"] for x in xs] == [True, False])
    check("a walk inside one plane crosses nothing",
          seam_crossings(pm, (10.0, 10.0), (90.0, 90.0), plane=0) == [])
    xs = seam_crossings(pm, (260.0, 50.0), (350.0, 150.0), plane=2)
    check("corner-to-corner walk names C and D, blind",
          len(xs) == 1 and set(xs[0]["pair"]) == {C, D} and not xs[0]["linked"])
    pm._cross = {2: [3], 3: [2], 1: [7], 7: [1]}
    xs = seam_crossings(pm, (50.0, 50.0), (250.0, 50.0), plane=0)
    check("known-bad: relinking B<->C instead of A<->B flips the verdicts",
          [x["linked"] for x in xs] == [False, True])
    pm._cross = {0: [2], 2: [0]}
    xs = seam_crossings(pm, (50.0, 50.0), (50.0, -50.0), plane=0)
    check("known-bad: dropping the line link makes A->G BLIND",
          len(xs) == 1 and not xs[0]["linked"])
    pm._cross = {0: [2], 2: [0], 1: [7], 7: [1]}
    check("chord_verdict refuses an unroutable chord",
          chord_verdict(pm, (50.0, 50.0), (250.0, 50.0)) is None)
    wa, wt, wb, wtb = walker_control(pm, found)
    check("walker control agrees on every toy seam, blind ones included",
          wa == wt and wb == wtb and wtb >= 3 and wt >= 6)
    return L.verdict()


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", type=int, default=146)
    ap.add_argument("--census", action="store_true",
                    help="print every blind seam on the map and stop")
    ap.add_argument("--per-seam", type=int, default=6)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--no-basin", action="store_true")
    ap.add_argument("--script", action="store_true",
                    help="emit a walk string to the best candidate")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    from pathmap import PathingMap
    import mapscout
    fid = dict((m, f) for m, f, _ in mapscout.MAPS)[a.map]
    pm = PathingMap.load(fid)
    rnd = random.Random(20260904)

    found = census(pm)
    seams = blind_seams(found)
    corners = sum(1 for r in found.values() if r["kind"] == "corner")
    nseam = len(found) - corners
    hit, tot, empty = portal_control(pm, found)
    print("BLIND-SEAM CENSUS, map %d: %d directed plane changes off a trapezoid "
          "edge -- %d corners set aside; of the %d seams %d are linked throughout, "
          "%d carry a BLIND stretch >= %.0f u"
          % (a.map, len(found), corners, nseam, nseam - len(seams), len(seams),
             MIN_SEAM))
    print("  portal control: %d of %d cross-plane portal pairs that link anything "
          "found as an adjacent pair (%.0f%%); %d pairs have an empty side and "
          "link nothing%s"
          % (hit, tot, 100.0 * hit / max(tot, 1), empty,
             "" if hit >= 0.9 * tot else "   <-- CONTROL WEAK, read no further"))
    wa, wt, wb, wtb = walker_control(pm, found)
    print("  walker control: %d of %d seam-local walks agree with the census "
          "(%.0f%%); of the BLIND ones %d of %d (%.0f%%)%s"
          % (wa, wt, 100.0 * wa / max(wt, 1), wb, wtb, 100.0 * wb / max(wtb, 1),
             "" if wa >= 0.9 * wt and wb >= 0.9 * wtb else "   <-- CONTROL WEAK"))
    if a.census:
        by_pair = collections.defaultdict(lambda: [0, 0])
        for r in found.values():
            if r["kind"] == "corner":
                continue
            s = by_pair[r["planes"]]
            s[0] += 1
            s[1] += bool(r["blind"] and r["span"] >= MIN_SEAM)
        print("\n  from->to   seams  BLIND   blind stretch lengths (u)")
        for k in sorted(by_pair):
            s = by_pair[k]
            if s[1]:
                lens = sorted(round(r["span"]) for kk, r in seams.items()
                              if r["planes"] == k)
                print("  %-9s %5d  %5d     %s" % (k, s[0], s[1], lens[:14]))
        print("\n  (directions with no blind seam omitted)")
        return 0

    spawn = mapscout.SPAWNS.get(a.map)
    if spawn is None:
        print("no spawn on file for map %d" % a.map)
        return 1
    cands = candidates(pm, seams, spawn, rnd, per_seam=a.per_seam)
    print("\n%d chords route across a blind seam (%d seams sampled)"
          % (len(cands), len(seams)))
    if not cands:
        return 0
    # Rank: nearest on foot first, then most legs (a multi-leg route is the
    # pull's work; a straight one is the gate's).
    cands.sort(key=lambda v: (v["walk_u"], -v["legs"]))
    top = cands[:a.top]
    if not a.no_basin:
        for v in top:
            v["basin"], v["basin_n"] = basin(pm, v["origin"], v["dest"])
        top.sort(key=lambda v: (-v["basin"], v["walk_u"]))
    print("\nTOP %d, by basin then walk (basin = share of the run's error "
          "budget that still crosses blind):" % len(top))
    for v in top:
        if "basin" in v:
            print("\n  BASIN %.2f (n=%d)" % (v["basin"], v["basin_n"]))
        describe(v)

    if a.script:
        v = top[0]
        o = v["origin"]
        s = mapscout.emit_script(pm, a.map, (round(o[0]), round(o[1])),
                                 (round(v["dest"][0]), round(v["dest"][1])))
        print("\n  --walk %r" % s)
    return 0


if __name__ == "__main__":
    sys.exit(main())
