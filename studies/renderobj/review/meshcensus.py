#!/usr/bin/env python3
"""Does the client's own body ever stand where our navmesh has no trapezoid? (GROUNDZ-Q7)

    python studies/renderobj/review/meshcensus.py             # map 146, every capture and tape
    python studies/renderobj/review/meshcensus.py --check     # with Q7's bars
    python studies/renderobj/review/meshcensus.py --map 0x1B97D --tape vault/research/renderobj/r3-agenttap.jsonl

THE QUESTION GROUNDZ-Q7 ASKED was whether `from_chunk` drops trapezoids: RUN-R3's
stair climb read NONE under 7 of 17 grant points and the terrace above the stairs
had none either. This is the census that answers it, and it does so from the one
witness that cannot be our own decoder agreeing with itself: WHERE THE CLIENT'S
BODY STOOD. Two sources, both the client's own words:

  * every ACCEPTED player position report (0x003D / 0x0047, the `position_report`
    rows) in every gamesrv capture on the map -- the client reports where its
    body is, and it will not walk its body off its own mesh;
  * every sample of the player's DRAWN body on the agenttap tapes (world 1,
    `agenttap.py`), 10-30 Hz, the body between reports.

Each point is scored against our decode: inside a trapezoid, or the distance to
the nearest one. A body standing > 2 u off our mesh is either ground our decode
lacks or a body a SERVER GRANT put there -- the client walks a 0x0029 wherever it
points (ROUTER-B3's off-mesh episodes) -- so every far report is joined to the
last player grant before it and to the segment from the previous report, and the
row says which.

THE ANSWER ON 2026-09-06 (397 captures, 10,529 reports; 9 tapes, 6,591 samples):
9,786 reports inside a trapezoid, 552 distinct points within 0.5 u of an edge
(the client's mover lays waypoints ALONG edges, sec.1z-bd.2), 2 within 2 u, and
18 beyond. Of the 18, 10 were walking a server grant whose destination sits off
our mesh or lie on the granted leg (2026-08-19's endpoint echoes), 7 came within
3 s of a > 200 u jump between consecutive reports (the body MOVED by the server,
then walking back onto the mesh -- among them a 62.8 u park beside the bridge's
north-west end on 2026-08-22, plane 18, held 11 s, the one point in 10,529 worth
a second look), and 1 is FREE: a 10.7 u stop-report at the foot of the stairs on
2026-09-03. The drawn body on the tapes:
never more than 0.36 u off, 6,591 of 6,591. The stairs are in our mesh; the hole
above them is a hole in the client's too (the player's body slid along its edge
to 0.2 u for 80 u, feel tape 45.6-48.0 s).

Read-only. Stdlib only. Needs the vault and the archive; refuses loudly without.
"""
import glob
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _p in ("toolkit", os.path.join("toolkit", "clientscan"), os.path.join("toolkit", "mapdata")):
    sys.path.insert(0, os.path.join(ROOT, _p))

import vaultpath                                            # noqa: E402
import agtrack_replay as AR                                 # noqa: E402
import w0score as W                                         # noqa: E402
from pathmap import PathingMap                              # noqa: E402

DEFAULT_MAP = 0x1B97D
EDGE = 0.5               # the sliver class (sec.1z-bf)
FAR = 2.0                # beyond this a point is off our mesh, not our edge rounding
LEG_TOL = 8.0            # a far report this close to the granted leg was walking it
JUMP = 200.0             # consecutive reports further apart than a walk covers: the body was MOVED
JUMP_WINDOW = 3.0        # s after a jump during which a far report is the jump's, not the client's
GRANT_RE = re.compile(r"\((-?\d+),(-?\d+)\)")

# Q7's bars (2026-09-06): floors and rates, never exact counts on a growing corpus.
FLOOR_REPORTS = 10000
MIN_ON_OR_EDGE = 0.99            # 10,340 of 10,529 = 0.982 inside-or-edge; distinct-off counted once
MAX_FREE_FAR_POINTS = 4          # far reports the server did not put there: 1 measured (see below)
MAX_TAPE_OFF = 1.0               # the drawn body's worst distance off our mesh, u: 0.5 measured


def _seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    f = 0.0 if L == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(a[0] + f * dx - p[0], a[1] + f * dy - p[1])


def _dist_to(t, x, y):
    if t.contains(x, y):
        return 0.0
    pts = [(t.x_top_left, t.y_top), (t.x_top_right, t.y_top),
           (t.x_bottom_right, t.y_bottom), (t.x_bottom_left, t.y_bottom)]
    best = 1e18
    for i in range(4):
        ax, ay = pts[i]
        bx, by = pts[(i + 1) % 4]
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        f = 0.0 if L == 0 else max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / L))
        best = min(best, math.hypot(ax + f * dx - x, ay + f * dy - y))
    return best


class Mesh:
    def __init__(self, fid):
        self.fid = fid
        self.pm = PathingMap.load(fid)

    def off(self, x, y):
        """0.0 on the mesh, else the distance to the nearest trapezoid."""
        if self.pm.planes_at(x, y):
            return 0.0
        return min((_dist_to(t, x, y) for t in self.pm.trapezoids
                    if t.y_bottom - 600 <= y <= t.y_top + 600), default=1e18)

    def seg_off(self, a, b, step=4.0):
        d = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(d / step))
        worst = 0.0
        for i in range(n + 1):
            f = i / n
            worst = max(worst, self.off(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
        return worst


def census_captures(mesh, caps):
    """The report census over the captures on this mesh's map."""
    stats = dict(caps=0, on_map=0, reports=0, on=0, edge=0, near=0, far=0, dup=0)
    seen = set()
    far = []
    for cap in caps:
        stats["caps"] += 1
        try:
            _ev, fid = AR.load_events(cap)
        except Exception:                                   # noqa: BLE001
            continue
        if fid != mesh.fid:
            continue
        stats["on_map"] += 1
        last_grant, prev, prev_t, jumped_at = None, None, None, None
        with open(cap, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                k = r.get("kind")
                if k == "sent" and r.get("opcode") == 0x29 and "agent 10" not in (r.get("label") or ""):
                    m = GRANT_RE.search(r.get("label") or "")
                    if m:
                        last_grant = ((float(m.group(1)), float(m.group(2))), r.get("t"))
                    continue
                if k != "position_report" or not r.get("accepted") or not r.get("reported"):
                    continue
                x, y = float(r["reported"][0]), float(r["reported"][1])
                stats["reports"] += 1
                t_ = r.get("t") or 0.0
                if prev is not None and math.hypot(x - prev[0], y - prev[1]) > JUMP:
                    jumped_at = t_
                recent_jump = jumped_at is not None and t_ - jumped_at <= JUMP_WINDOW
                d = mesh.off(x, y)
                if d == 0.0:
                    stats["on"] += 1
                else:
                    key = (round(x, 1), round(y, 1))
                    if key in seen:
                        stats["dup"] += 1
                    else:
                        seen.add(key)
                        if d <= EDGE:
                            stats["edge"] += 1
                        elif d <= FAR:
                            stats["near"] += 1
                        else:
                            stats["far"] += 1
                            # ENSLAVED: the body was walking a server grant -- the
                            # grant's own destination is off our mesh, or the point
                            # lies on the leg from the previous report to that
                            # destination (the client walks a 0x0029 wherever it
                            # points). FREE otherwise: the client's own doing.
                            gd = mesh.off(*last_grant[0]) if last_grant else 0.0
                            on_leg = (_seg_dist((x, y), prev, last_grant[0])
                                      if (last_grant and prev) else 1e18)
                            ens = bool(last_grant) and (gd > FAR or on_leg <= LEG_TOL)
                            far.append(dict(cap=os.path.basename(cap), t=t_, x=x, y=y, d=d,
                                            plane=r.get("plane"), src=r.get("source"),
                                            grant=last_grant[0] if last_grant else None,
                                            grant_off=gd, on_leg=on_leg,
                                            jump=math.hypot(x - prev[0], y - prev[1]) if prev else None,
                                            cls=("ENSLAVED" if ens else
                                                 "JUMP" if recent_jump else "FREE")))
                prev, prev_t = (x, y), t_
    return stats, far


def census_tapes(mesh, tapes, agent="1"):
    out = []
    for tape in tapes:
        try:
            _head, rows = W.load(tape)
        except Exception as e:                              # noqa: BLE001
            print("  [tape] %s unreadable: %s" % (tape, e))
            continue
        n = 0
        worst = 0.0
        far = 0
        for s in rows:
            a = (s.get("agents") or {}).get(agent)
            if not a or not a.get("async") or "x" not in a["async"]:
                continue
            n += 1
            d = mesh.off(a["async"]["x"], a["async"]["y"])
            worst = max(worst, d)
            far += 1 if d > FAR else 0
        out.append((os.path.relpath(tape, ROOT), n, worst, far))
    return out


def main(argv):
    fid = DEFAULT_MAP
    if "--map" in argv:
        v = argv[argv.index("--map") + 1]
        fid = int(v, 16) if v.lower().startswith("0x") else int(v)
    t0 = time.time()
    mesh = Mesh(fid)
    root = vaultpath.require_dir("captures", "gamesrv", why="the report census reads our own captures")
    caps = sorted(glob.glob(os.path.join(root, "*.jsonl")))
    if "--tape" in argv:
        tapes = [argv[argv.index("--tape") + 1]]
    else:
        rr = vaultpath.vault_root()
        tapes = sorted(glob.glob(os.path.join(rr, "research", "npctrack", "*-agenttap.jsonl"))
                       + glob.glob(os.path.join(rr, "research", "renderobj", "*-agenttap.jsonl")))
    stats, far = census_captures(mesh, caps)
    print("map 0x%X: %d captures on disk, %d on this map, %d accepted reports (%.0f s)" % (
        fid, stats["caps"], stats["on_map"], stats["reports"], time.time() - t0))
    print("  inside a trapezoid %d | distinct off-mesh points: within %.1f u of an edge %d, %.1f-%.0f u %d, beyond %d (repeats %d)" % (
        stats["on"], EDGE, stats["edge"], EDGE, FAR, stats["near"], stats["far"], stats["dup"]))
    free = [f for f in far if f["cls"] == "FREE"]
    print("  far points: ENSLAVED (walking a server grant off our mesh, or on its leg) %d | JUMP (within %.0f s of a > %.0f u jump between reports) %d | FREE %d" % (
        sum(1 for f in far if f["cls"] == "ENSLAVED"), JUMP_WINDOW, JUMP, sum(1 for f in far if f["cls"] == "JUMP"), len(free)))
    for f in sorted(far, key=lambda f: -f["d"]):
        print("    %6.1f u (%8.1f,%8.1f) plane %s %s  grant %s off %.1f u, point %s u off its leg, %s u from the previous report  %s  %s" % (
            f["d"], f["x"], f["y"], f["plane"], f["src"], f["grant"], f["grant_off"],
            ("%.1f" % f["on_leg"]) if f["on_leg"] < 1e17 else "-",
            ("%.0f" % f["jump"]) if f["jump"] is not None else "-",
            f["cls"], f["cap"]))
    tp = census_tapes(mesh, tapes)
    for name, n, worst, nfar in tp:
        print("  tape %-45s player drawn-body samples %5d | worst off our mesh %.2f u | > %.0f u: %d" % (name, n, worst, FAR, nfar))
    if "--check" not in argv:
        return 0
    print("\n--check, against GROUNDZ-Q7's bars")
    bad = 0

    def bar(ok, text):
        nonlocal bad
        print("  [%s] %s" % ("PASS" if ok else "FAIL", text))
        bad += 0 if ok else 1

    bar(stats["reports"] >= FLOOR_REPORTS, "accepted reports %d >= %d" % (stats["reports"], FLOOR_REPORTS))
    good = stats["on"] + stats["edge"] + stats["dup"]
    rate = good / stats["reports"] if stats["reports"] else 0.0
    bar(rate >= MIN_ON_OR_EDGE, "reports inside a trapezoid or within %.1f u of an edge: %.4f >= %.2f" % (EDGE, rate, MIN_ON_OR_EDGE))
    bar(len(free) <= MAX_FREE_FAR_POINTS,
        "far reports the server did not put there: %d <= %d (the client's free body stays on our mesh)" % (len(free), MAX_FREE_FAR_POINTS))
    bar(bool(tp) and all(w <= MAX_TAPE_OFF for _n, _c, w, _f in tp),
        "the drawn body on every tape: worst %.2f u off our mesh <= %.1f" % (max((w for _n, _c, w, _f in tp), default=-1), MAX_TAPE_OFF))
    print("--check: %s" % ("ALL BARS HELD" if bad == 0 else "%d BAR(S) FAILED" % bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
