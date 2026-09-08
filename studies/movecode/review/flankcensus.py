#!/usr/bin/env python3
"""THE FOOT-FLANK CENSUS (MOVECODE-1z-cn): why the hostile's drawn body leaves our mesh.

    python studies/movecode/review/flankcensus.py                  # every RUN-1zCG session
    python studies/movecode/review/flankcensus.py --cap C --tape T  # one session

WHY THIS EXISTS. `sessionscore.py` has printed "hostile drawn body off our mesh" RED on every
hand-driven session since RUN-1zCG session 1 (14.3 u worst, then 17.5, then 12.5), always at
the stairs' foot flank, and nothing had traced it. The owner's session-4 words for the same
thing were "the Hatcher commits too hard at waypoints around the top of the stairs".

WHAT IT MEASURES, and the order matters because three earlier readings of this number were
artifacts of the instrument rather than the server:

  1. THE PARKED BODY. The drawn (async, world-1) copy at rest -- v <= 1 u/s -- off our mesh.
     This is the RED. Read on the RAW column deliberately: at rest the sample-and-hold column
     IS the client's position, and w0score.live's dead reckoning adds nothing (1z-ck's trap
     runs the other way -- it is the MOVING samples the raw column lies about).

  2. THE CHORD. `0x002A` is agent-addressed and carries a point; the client does NOT path it,
     it dead-reckons the body in a straight line (movement/FINDINGS :1147). So the quantity
     that puts the body off the mesh is the straight chord from where the copy IS to the point
     we ordered -- not the point, which is always on the mesh.

  3. WHY NO CORRIDOR LEG WENT OUT INSTEAD. `_follow_leg` returns None -- and `_order` then
     sends the bare `0x002A` -- for FOUR different reasons that this splits apart: route()
     returned nothing; route() returned a 2-point path (it says the line is clear); the
     inside-disc rule dropped a real corridor; or none of those, which is reported as
     unexplained rather than guessed at.

THE OPERAND IS PINNED, NEVER RECONSTRUCTED. `_order` solves from `agent["pos"]`, the Q1 model,
which is the client's own SYNC copy and is on the tape. A candidate origin is accepted only
when the distance it implies matches the order label's own "N u out" to within 3 u; anything
else is skipped. An unpinned operand is not evidence (feedback: verify the operand, not just
the predicate), and a census that guessed it would name causes for orders it cannot see.

TOLERANCE. "Off the mesh" here means beyond 2 u. Our trapezoid edges are exact containment and
the client legitimately stands a sub-unit sliver outside them (`pathmap.on_mesh`, SEAM_TOL 1 u,
MOVECODE-1z-bf: 17 of 17 gate2 re-pins were <= 0.5 u out). Filtering at exact containment
instead reports the edge class as a defect -- it produced 25 false rows on the first pass here.
"""
import argparse
import bisect
import glob
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/clientscan", "toolkit/mapdata", "toolkit/authsrv",
            "studies/renderobj/review"):
    sys.path.insert(0, os.path.join(ROOT, sub))

import vaultpath                                   # noqa: E402
import w0score as W                                # noqa: E402
import content                                     # noqa: E402
from meshcensus import Mesh                        # noqa: E402
import authsrv                                     # noqa: E402

FAR = 2.0                     # u: beyond the edge class (on_mesh's SEAM_TOL is 1 u)
PIN_TOL = 3.0                 # u: the label's "N u out" must agree with the tape's sync copy
OUT_RE = re.compile(r"(\d+) u out")
HOSTILE = 10


def _agent(plain):
    try:
        return int.from_bytes(bytes.fromhex(plain[4:12]), "little")
    except (ValueError, TypeError):
        return None


def _point_planes(plain):
    """(x, y, field3, field4) of a 0x0029/0x002A payload."""
    x, y = struct.unpack("<ff", bytes.fromhex(plain[12:28]))
    f3 = int.from_bytes(bytes.fromhex(plain[28:32]), "little")
    f4 = int.from_bytes(bytes.fromhex(plain[32:36]), "little")
    return x, y, f3, f4


def parked_off_mesh(mesh, rows, agent=str(HOSTILE)):
    """[(t0, t1, worst, point)] -- episodes with the drawn body AT REST off our mesh."""
    eps, cur = [], None
    for sm in rows:
        a = (sm.get("agents") or {}).get(agent)
        if not a or "x" not in (a.get("async") or {}):
            continue
        b = a["async"]
        v = math.hypot(b.get("vx", 0.0), b.get("vy", 0.0))
        off = mesh.off(b["x"], b["y"])
        bad = v <= 1.0 and off > FAR
        if bad:
            if cur is None:
                cur = [sm["t"], sm["t"], off, (b["x"], b["y"])]
            cur[1] = sm["t"]
            if off > cur[2]:
                cur[2], cur[3] = off, (b["x"], b["y"])
        elif cur is not None:
            eps.append(tuple(cur))
            cur = None
    if cur is not None:
        eps.append(tuple(cur))
    return eps


def classify(pm, mesh, origin, dest, f3, f4):
    """Why _follow_leg sent the bare 0x002A for this order."""
    ax, ay = origin
    if not pm.walkable(ax, ay):
        nw = pm.nearest_walkable(ax, ay, authsrv.NPC_LEG_ORIGIN_STEP)
        if nw:
            ax, ay = float(nw[0]), float(nw[1])
    gx, gy = dest
    if not pm.walkable(gx, gy):
        nw = pm.nearest_walkable(gx, gy, authsrv.NPC_LEG_ORIGIN_STEP)
        if nw:
            gx, gy = float(nw[0]), float(nw[1])
    try:
        r = pm.route(ax, ay, gx, gy, start_plane=f4, goal_plane=f3, with_planes=True)
        path = r[0] if isinstance(r, tuple) else r
    except Exception:                                        # noqa: BLE001
        path = None
    n = len(path) if path else 0
    if n == 0:
        return "no-route", n
    if n == 2:
        # route() promises "walking it in straight segments never leaves the navmesh".
        # Its gate samples the UNPULLED candidate at 16 u; a narrow excursion survives.
        g16 = pm._gate_clip(origin, dest, None, 16.0)
        g2 = pm._gate_clip(origin, dest, None, 2.0)
        gap = math.dist(g16, dest) < 1e-6 and math.dist(g2, dest) > 1e-6
        return ("route-2pt (gate passes at 16 u, fails at 2 u)" if gap
                else "route-2pt"), n
    if math.hypot(path[1][0] - dest[0], path[1][1] - dest[1]) < authsrv.follow_stop_radius():
        return "in-disc rule dropped the corridor", n
    return "UNEXPLAINED", n


def score(cap, tape, quiet=False):
    rows = W.load_gamesrv(cap)
    mid = next((r.get("map_id") for r in rows if r.get("kind") == "version"), None)
    if mid is None:
        return None
    mesh = Mesh(content.load().map_static_config()[int(mid)][0])
    pm = mesh.pm
    head, srows = W.load(tape)
    ref = [r for r in rows if "wall_unix" in r and "t" in r][-1]
    capoff = ref["wall_unix"] - ref["t"]
    T = [sm["t"] + head["t0"] - capoff for sm in srows]

    out = {"cap": os.path.basename(cap), "tape": os.path.basename(tape), "map": mid,
           "orders": 0, "pinned": 0, "bad": [], "parked": parked_off_mesh(mesh, srows)}
    for m in rows:
        if m.get("kind") != "sent" or m.get("opcode") != 0x2A:
            continue
        plain = m.get("plain") or ""
        if _agent(plain) != HOSTILE:
            continue
        try:
            px, py, f3, f4 = _point_planes(plain)
        except (ValueError, struct.error):
            continue
        out["orders"] += 1
        g = OUT_RE.search(m.get("label") or "")
        i = bisect.bisect_left(T, m["t"]) - 1
        if not g or i < 0:
            continue
        a = (srows[i].get("agents") or {}).get(str(HOSTILE))
        if not a or "x" not in (a.get("sync") or {}):
            continue
        origin = (a["sync"]["x"], a["sync"]["y"])
        if abs(math.dist(origin, (px, py)) - float(g.group(1))) > PIN_TOL:
            continue
        out["pinned"] += 1
        chord = mesh.seg_off(origin, (px, py), step=2.0)
        if chord <= FAR:
            continue
        why, n = classify(pm, mesh, origin, (px, py), f3, f4)
        out["bad"].append({"t": round(m["t"], 2), "chord": round(chord, 1),
                           "span": round(math.dist(origin, (px, py))),
                           "why": why, "n": n,
                           "from": (round(origin[0]), round(origin[1])),
                           "to": (round(px), round(py))})
    if not quiet:
        report(out)
    return out


def report(o):
    print("=" * 92)
    print(f"{o['cap']}   map {o['map']}   tape {o['tape']}")
    print(f"  hostile 0x002A orders {o['orders']}, operand pinned {o['pinned']}, "
          f"chord leaves our mesh {len(o['bad'])}")
    if o["parked"]:
        worst = max(p[2] for p in o["parked"])
        print(f"  PARKED off our mesh: {len(o['parked'])} episode(s), worst {worst:.2f} u")
        for t0, t1, off, pt in o["parked"]:
            print(f"     t {t0:7.2f}-{t1:7.2f}  {off:6.2f} u at "
                  f"({pt[0]:.0f},{pt[1]:.0f})")
    for b in sorted(o["bad"], key=lambda z: -z["chord"]):
        print(f"     t {b['t']:7.2f}  chord {b['chord']:6.1f} u  span {b['span']:4d} u  "
              f"{b['from']} -> {b['to']}   {b['why']}")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap")
    ap.add_argument("--tape")
    a = ap.parse_args(argv)
    if a.cap and a.tape:
        score(a.cap, a.tape)
        return 0
    root = vaultpath.vault_root()
    pairs = [
        ("authsrv-20260907T105915-c1", "1zcg2-agenttap"),
        ("authsrv-20260907T121212-c1", "1zcg3-agenttap"),
        ("authsrv-20260907T144522-c1", "1zcg4-agenttap"),
        ("authsrv-20260908T183848-c1", "1zcg5-agenttap"),
    ]
    tally = {}
    for capn, tapen in pairs:
        cap = os.path.join(root, "captures", "gamesrv", capn + ".jsonl")
        tape = os.path.join(root, "research", "movecode", tapen + ".jsonl")
        if not (os.path.isfile(cap) and os.path.isfile(tape)):
            print(f"[skip] {capn}: capture or tape missing")
            continue
        o = score(cap, tape)
        for b in (o or {}).get("bad", []):
            key = b["why"].split(" (")[0]
            tally[key] = tally.get(key, 0) + 1
    if tally:
        print("\n" + "=" * 92)
        print("why the bare 0x002A went out, pooled over the sessions:")
        for k, v in sorted(tally.items(), key=lambda kv: -kv[1]):
            print(f"  {v:3d}  {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
