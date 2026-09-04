#!/usr/bin/env python3
"""The BENT-PATH cell of FINDINGS sec.1z-ak, filled by derivation instead of a run.

    python studies/movecode/review/bentbound.py              # map 146, the operator's area
    python studies/movecode/review/bentbound.py --map 0x287B3
    python studies/movecode/review/bentbound.py --samples 800

WHY. sec.1z-ak measured `PRESS ENDS THE WALK`'s harm at 0.0-6.9 u against the
drawn body and concluded no harm bound is needed. It also stated its own
residual: the specimen was an open-ground click kite, so a BENT path -- one the
client must walk around -- was **n = 0**. That is the cell this fills.

THE MODEL'S ERROR ON A BENT PATH IS NOT THE BOW, IT IS BIGGER. `_click_leg_arm`
records a STRAIGHT leg (p0 -> dest at 288 u/s) and `_click_leg_start` lerps it.
The body walks the ROUTE. Both advance at 288 u/s from the same instant, so at
wall time t the model sits at arclength 288t along the CHORD while the body sits
at 288t along the LONGER route: the error is lateral AND along-track, because
the model runs ahead on the shorter path. `max_t |chord(288t) - route(288t)|` is
the worst residual a press pin could carry on that leg, and it is what this
scores.

TWO CONTROLS, because a desk number with a dramatic ratio is where this repo
gets burned:
  * POSITIVE CONTROL -- a CLEAR chord's route IS the chord, so its residual must
    come out 0.000 u. A harness that invents error on a straight walk cannot be
    trusted on a bent one. Exits non-zero if it fails.
  * THE BOW IS BANDED, never pooled. "Around a rock" (bow < 1.25) and "around
    the mountain" (bow > 5) are different events and a p50 over both is a
    number about the sampler, not about the game. The tail is reported as its
    own band and is NOT the headline.

AND THE EXPOSURE TERM IS SEPARATE FROM THE HARM TERM. A residual that cannot
occur where anyone plays is not a hazard. Exposure is scored at the operator's
own body positions from the 08:46 session, over the click lengths that session
actually used -- which is why sec.1z-ak's capture had 0 of 37 bent chords.

WHAT IT FINDS, and the reason the verdict survives: the bow error belongs to the
RAW-CHORD regime (`--no-router` / `--router-raw-leg`). Under the shipped default
`ROUTER_LEG_REARM` re-aims the click-leg record at the ROUTED leg
(`_router_rearm_leg`, and again per chain leg), so the model lerps a SEGMENT OF
THE ROUTE the body is walking and the bow term vanishes by construction. That
flag's own comment names this reader: *"PRESS ENDS THE WALK's 0x002C at the
modelled body... would place the body on a straight line the client is not
walking."* This file is the size of the thing it was protecting against.

Read-only; needs the archive (a vault machine). Stdlib only.
"""
import argparse
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "mapdata"))

MAP_146 = 0x1B97D          # Ascalon City / Lakeside County -- the operator's map
CLIP_STEP = 2.0            # authsrv.A2_LEAD_CLIP_STEP, the server's own fineness
R_MATCH = 100.0            # agtrack_mirror.R_MATCH -- the client's reprieve radius
SEED = 20260904

# The operator's own drawn-body positions through the 08:46 session (the tape
# sec.1z-ak scored). Exposure is asked HERE, not over the whole map.
PLAY_ORIGINS = [
    (9951, 7975), (9896, 7962), (9867, 7945), (9839, 7929), (9830, 7960),
    (9825, 8026), (9826, 8059), (9861, 8114), (9894, 8148), (9934, 8162),
    (9966, 8171), (9979, 8140), (9985, 8074), (9980, 8036), (9930, 8015),
    (9921, 8012), (9884, 8089), (9878, 8146), (9884, 8206), (9911, 8219),
    (9935, 8197), (9950, 8195), (9412, 8041), (9551, 8099), (9578, 8118),
    (9680, 8188), (9598, 8369), (9574, 8324), (9643, 8367), (9627, 8371),
    (9543, 8392),
]
BOW_BANDS = [
    (1.00, 1.25, "a rock / a corner"),
    (1.25, 2.00, "a real detour"),
    (2.00, 5.00, "around a building"),
    (5.00, 1e9, "around the mountain"),
]


def plen(pts):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(pts, pts[1:]))


def point_at(pts, s):
    """The point at arclength `s` along a polyline, clamped to its end."""
    if s <= 0:
        return pts[0]
    acc = 0.0
    for a, b in zip(pts, pts[1:]):
        seg = math.hypot(b[0] - a[0], b[1] - a[1])
        if acc + seg >= s:
            f = (s - acc) / seg if seg > 0 else 0.0
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        acc += seg
    return pts[-1]


def worst_residual(origin, dest, route):
    """max over the walk of |straight-line model - body on the route|.

    Both advance at the same speed from the same instant, so arclength is the
    shared clock; the model CLAMPS at its own (shorter) eta, which is what
    `_click_leg_start` does when `now >= leg["eta"]`."""
    chord = [origin, dest]
    clen, rlen = plen(chord), plen(route)
    worst = 0.0
    n = max(int(rlen / 2.0), 20)
    for i in range(n + 1):
        s = rlen * i / n
        b = point_at(route, s)
        m = point_at(chord, min(s, clen))
        worst = max(worst, math.hypot(m[0] - b[0], m[1] - b[1]))
    return worst, clen, rlen


def quant(vals, p):
    v = sorted(vals)
    return v[min(int(len(v) * p), len(v) - 1)]


def is_bent(pm, ox, oy, dx, dy):
    sx, sy = pm.clip(ox, oy, dx, dy, step=CLIP_STEP)
    return math.hypot(dx - sx, dy - sy) >= 1.0


def exposure(pm, origins, headings=16):
    """How often a click is BENT where the operator actually plays."""
    print("EXPOSURE -- how often is a click BENT where the operator plays?")
    print("  origins: %d drawn-body positions from the 08:46 session, %d headings each"
          % (len(origins), headings))
    for lo, hi, name in ((50, 300, "the session's own click range (53-276 u)"),
                         (300, 500, "longer clicks")):
        tot = bent = 0
        L = (lo + hi) / 2.0
        for ox, oy in origins:
            if not pm.walkable(ox, oy):
                continue
            for k in range(headings):
                th = 2 * math.pi * k / headings
                dx, dy = ox + L * math.cos(th), oy + L * math.sin(th)
                if not pm.walkable(dx, dy):
                    continue
                tot += 1
                if is_bent(pm, ox, oy, dx, dy):
                    bent += 1
        pct = 100.0 * bent / tot if tot else 0.0
        print("    %-42s %3d of %3d bent (%.1f%%)" % (name, bent, tot, pct))
    print()


def harm(pm, n_target, seed=SEED):
    """Sampled bent chords: the residual, banded by bow. Returns (ok, rows)."""
    rnd = random.Random(seed)
    bent, control = [], []
    tries = 0
    while len(bent) < n_target and tries < 200 * n_target:
        tries += 1
        t = pm.trapezoids[rnd.randrange(len(pm.trapezoids))]
        ox, oy = t.centre
        if not pm.walkable(ox, oy):
            continue
        L = rnd.uniform(50.0, 500.0)
        th = rnd.uniform(0, 2 * math.pi)
        dx, dy = ox + L * math.cos(th), oy + L * math.sin(th)
        if not pm.walkable(dx, dy):
            continue
        if not is_bent(pm, ox, oy, dx, dy):
            if len(control) < 60:
                r = pm.route(ox, oy, dx, dy)
                if r and len(r) >= 2:
                    control.append(worst_residual((ox, oy), (dx, dy), r)[0])
            continue
        r = pm.route(ox, oy, dx, dy)
        if not r or len(r) < 2:
            continue
        w, clen, rlen = worst_residual((ox, oy), (dx, dy), r)
        bent.append((w, clen, rlen, rlen / clen if clen else 0.0))

    print("POSITIVE CONTROL -- a CLEAR chord's route IS the chord, so 0.000 u:")
    ok = True
    if not control:
        print("    no clear chords sampled -- control did not run, so nothing below stands")
        ok = False
    else:
        print("    n=%d   max residual %.3f u" % (len(control), max(control)))
        if max(control) > 1.0:
            print("    !! CONTROL FAILED: the harness invents error on a straight walk")
            ok = False
    print()

    if not bent:
        print("no bent chords sampled -- zero exposure for the harm question")
        return ok, bent

    bows = [b[3] for b in bent]
    print("HARM -- max |model - drawn body| on a bent leg (n=%d), BANDED BY BOW"
          % len(bent))
    print("    bow itself: p50 %.2f  p90 %.2f  max %.1f" %
          (quant(bows, .5), quant(bows, .9), max(bows)))
    for lo, hi, name in BOW_BANDS:
        g = [b for b in bent if lo <= b[3] < hi]
        if not g:
            continue
        gw = [x[0] for x in g]
        print("    bow %4.2f-%-5.2f %-20s n=%-4d p50 %7.1f  p90 %7.1f  max %8.1f   "
              "over R_MATCH %d/%d"
              % (lo, min(hi, 99.99), name, len(g), quant(gw, .5), quant(gw, .9),
                 max(gw), sum(1 for x in gw if x > R_MATCH), len(g)))
    mild = [b for b in bent if b[3] < 1.25]
    if mild:
        print("\n    THE HEADLINE IS THE MILDEST BAND, not the tail: even at bow < 1.25 "
              "-- a rock,\n    not a mountain -- %d of %d exceed the client's own %.0f u "
              "reprieve radius." % (sum(1 for b in mild if b[0] > R_MATCH), len(mild),
                                    R_MATCH))
    return ok, bent


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", default=hex(MAP_146),
                    help="map file id (default 0x1B97D, the operator's)")
    ap.add_argument("--samples", type=int, default=400,
                    help="bent chords to sample for the harm distribution")
    a = ap.parse_args()

    from pathmap import PathingMap
    fid = int(a.map, 0)
    try:
        pm = PathingMap.load(fid)
    except (OSError, KeyError, ValueError) as e:
        print("cannot load mesh 0x%X (%r) -- this needs the archive, i.e. a vault "
              "machine. Refusing rather than guessing." % (fid, e))
        return 1
    print("mesh 0x%X: %d trapezoids\n" % (fid, len(pm.trapezoids)))

    exposure(pm, PLAY_ORIGINS)
    ok, _rows = harm(pm, a.samples)

    print("\nVERDICT. The bow error is the RAW-CHORD regime's: `--no-router` or")
    print("`--router-raw-leg`, which is what the 08:46 specimen ran (ROUTER=False).")
    print("Under the shipped default ROUTER_LEG_REARM re-aims the click-leg record at")
    print("the ROUTED leg, so the model lerps a SEGMENT OF THE ROUTE the body walks and")
    print("the bow term is gone by construction. sec.1z-ak's 0.0-6.9 u stands for the")
    print("default; these numbers are the cost of the revert flags on bent geometry.")
    if not ok:
        print("\nBut the control did not pass, so treat the harm numbers as unproven.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
