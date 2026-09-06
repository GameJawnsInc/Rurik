#!/usr/bin/env python3
"""Score a stair climb under the wall slide (MOVECODE-1z-ce, RUN-1zCE): the climb's keyboard
leads by kind and length, and the player's world-0 copy against its drawn body while climbing.

    python studies/movecode/review/slidescore.py --cap C --tape T [--compare-cap C2 --compare-tape T2]

P1 reads the capture's own rows: every fired keyboard grant (`grant_verdict`, lead_src kbd)
joined to the accepted report it was armed on, its `lead_clip_why` and the granted length. The
CLIMB is the set of grants whose report is on plane 29 (map 146's staircase). P2 reads the tape
THROUGH THE CLIENT'S OWN ACCESSOR (`w0score.live`, AgAgent::position_at with its clamp): per
sample inside the climb window, |world-0 - drawn body| for the player, and the gap's sign along
the body's motion (+ = world-0 ahead). The tape's raw `x, y` is m_point, sample-and-hold -- the
first draft of this scorer read it and printed a half-second "dead time" after every grant that
did not exist ([[project-rurik-movetap-point-column-trap]]). P3 lists the body's reports through
the climb (their spacing and plane), the fence word on the tape, and any 0x002C. The same
instrument runs on the comparison run so the before/after numbers cannot come from two scorers.
"""
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _p in ("toolkit", os.path.join("toolkit", "clientscan"), os.path.join("studies", "npctrack", "review")):
    sys.path.insert(0, os.path.join(ROOT, _p))

import w0score as W          # noqa: E402
import npcdrift as N         # noqa: E402

CLIMB_PLANE = 29


def load_cap(path):
    rows = W.load_gamesrv(path)
    t0 = next(r["t"] for r in rows if r.get("t") is not None)
    reports, grants, repins = [], [], []
    for r in rows:
        k = r.get("kind")
        t = (r.get("t") or 0.0) - t0
        if k == "position_report" and r.get("accepted") and r.get("reported"):
            reports.append(dict(t=t, x=float(r["reported"][0]), y=float(r["reported"][1]),
                                plane=r.get("plane"), src=r.get("source")))
        elif k == "grant_verdict" and r.get("fired") and r.get("lead_src") == "kbd":
            grants.append(dict(t=t, dest=r.get("dest"), why=r.get("lead_clip_why"),
                               plane=r.get("plane_dest")))
        elif k == "sent" and r.get("opcode") == 0x2C:
            repins.append(t)
    # join each grant to the last accepted report at or before it
    for g in grants:
        rep = None
        for r in reports:
            if r["t"] <= g["t"] + 0.01:
                rep = r
            else:
                break
        g["rep"] = rep
        g["len"] = (math.hypot(g["dest"][0] - rep["x"], g["dest"][1] - rep["y"])
                    if (rep and g.get("dest")) else None)
    return rows, t0, reports, grants, repins


def climb_window(reports):
    ts = [r["t"] for r in reports if r["plane"] == CLIMB_PLANE]
    if not ts:
        return None
    return min(ts), max(ts) + 0.5


def tape_sep(tape, cap_rows, lo, hi):
    """(t, |world-0 - body|, signed along-track gap, fence) per tape sample inside
    [lo, hi] capture seconds, both copies through the client's own accessor."""
    head, rows = W.load(tape)
    t0 = N.cap_t0(cap_rows)
    ser = W.series(head, rows, 1)
    fences = {}
    for s in rows:
        p = (s.get("agents") or {}).get("1") or {}
        f = p.get("fence")
        if isinstance(f, dict):
            f = f.get("fence_state")
        if f is not None:
            fences[head["t0"] + s["t"]] = f
    out = []
    prev = None
    for e in ser:
        t = e["w"] - t0
        bx, by = e["body"]
        if prev is not None and lo <= t <= hi:
            mx, my = bx - prev[0], by - prev[1]
            m = math.hypot(mx, my)
            dx, dy = e["w0"][0] - bx, e["w0"][1] - by
            along = (dx * mx + dy * my) / m if m > 1e-6 else float("nan")
            out.append((t, math.hypot(dx, dy), along, fences.get(e["w"])))
        prev = (bx, by)
    return out


def score(cap, tape, label, timeline=False):
    rows, t0, reports, grants, repins = load_cap(cap)
    win = climb_window(reports)
    print("== %s: %s" % (label, os.path.basename(cap)))
    print("   accepted reports %d, fired keyboard grants %d, 0x002C %d" % (len(reports), len(grants), len(repins)))
    if win is None:
        print("   NO plane-%d report: the climb did not happen -- ZERO TRIALS" % CLIMB_PLANE)
        return None
    lo, hi = win
    climb = [g for g in grants if g["rep"] and g["rep"]["plane"] == CLIMB_PLANE]
    print("   climb window %.2f-%.2f s; climb grants %d" % (lo, hi, len(climb)))
    for g in climb:
        print("     %6.2f report (%7.1f,%7.1f) pl %s -> %-11s %6.1f u" % (
            g["t"], g["rep"]["x"], g["rep"]["y"], g["rep"]["plane"], g["why"], g["len"] or 0.0))
    n_slide = sum(1 for g in climb if g["why"] == "wall-slide" and (g["len"] or 0) >= 50.0)
    n_zero = sum(1 for g in climb if (g["len"] or 0) < 1.0)
    print("   P1: wall-slide >= 50 u: %d of %d | zero leads: %d" % (n_slide, len(climb), n_zero))
    sep = tape_sep(tape, rows, lo, hi) if tape else []
    if sep:
        v = sorted(d for _t, d, _a, _f in sep)
        ahead = [a for _t, _d, a, _f in sep if a == a and a > 0]
        behind = [a for _t, _d, a, _f in sep if a == a and a < 0]
        fw = sorted(set(str(f) for _t, _d, _a, f in sep if f is not None))
        print("   P2: world-0 vs drawn body (client accessor) in the climb window: n %d, p50 %.1f, p90 %.1f, max %.1f u"
              " | ahead on %d (p50 %+.0f), behind on %d (p50 %+.0f) | fence words seen %s" % (
                  len(v), statistics.median(v), v[int(0.9 * len(v))], v[-1],
                  len(ahead), statistics.median(ahead) if ahead else 0.0,
                  len(behind), statistics.median(behind) if behind else 0.0, fw or "n/a"))
        if timeline:
            last = -9.0
            for t, d, a, f in sep:
                if t - last >= 0.45:
                    last = t
                    print("       %6.2f |gap| %5.0f  along %+6.0f  fence %s" % (t, d, a, f))
    else:
        print("   P2: no tape samples in the window")
    cr = [r for r in reports if lo - 0.1 <= r["t"] <= hi + 3.0]
    steps = [math.hypot(b["x"] - a["x"], b["y"] - a["y"]) for a, b in zip(cr, cr[1:])]
    top = next((r for r in reports if r["y"] > 9100.0), None)
    print("   P3: climb reports %d, step p50 %.0f u, max %.0f u; first report past y 9100 at %s; 0x002C in window: %d" % (
        len(cr), statistics.median(steps) if steps else 0.0, max(steps) if steps else 0.0,
        ("%.2f s" % top["t"]) if top else "never", sum(1 for t in repins if lo <= t <= hi)))
    return dict(n_slide=n_slide, n_zero=n_zero, n_climb=len(climb), sep=sep)


def main(argv):
    if "--cap" not in argv:
        print(__doc__)
        return 2
    cap = argv[argv.index("--cap") + 1]
    tape = argv[argv.index("--tape") + 1] if "--tape" in argv else None
    tl = "--timeline" in argv
    score(cap, tape, "THIS RUN", tl)
    if "--compare-cap" in argv:
        c2 = argv[argv.index("--compare-cap") + 1]
        t2 = argv[argv.index("--compare-tape") + 1] if "--compare-tape" in argv else None
        score(c2, t2, "COMPARISON", tl)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
