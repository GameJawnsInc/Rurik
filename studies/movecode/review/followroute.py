#!/usr/bin/env python3
"""Does the routed NPC follow escape the corner RUN-1zBW's Hatcher died in? (MOVECODE-1z-by)

    python studies/movecode/review/followroute.py

THE DEFECT, MEASURED (FINDINGS sec.1z-bx.3). In RUN-1zBW the server's copy of the Hatcher
stopped at (10683.46, 4329.52) -- a walkable point about 7 u from its trapezoid's left
edge -- and ALL 15 follow orders after t=20.793 clipped 0.000 u. The chase was dead for
155 s of a 190 s session while the client went on drawing the body 965.6 u away, which
nothing in the protocol can reconcile: 0x0028 carries no point and an NPC never receives a
0x002C. The operator reported it as "inconsistent aggro behavior".

`enemy_move_tick`'s docstring had described this since ANIMREF-RE 40 and called the cost
honest -- "a hostile on the far side of a building will stand against the wall for as long
as you stay there". What the run showed is that the wall does not have to be a building: a
trapezoid EDGE is enough, and `pm.route` leaves that same corner 49 times out of 49.

THIS FILE IS THE KNOWN-BAD ARM, RUN ON THE REAL MESH. Two scenarios, each scored with
NPC_FOLLOW_ROUTER False and True:

  A. THE POSITIVE CONTROL -- a player parked 331 u away, inside the leash, with clip()
     returning 0.00 u toward them and a route existing. The routed arm must close to the
     80 u disc; the straight-line arm must not move at all. If BOTH arms move, the
     fixture is not reproducing the wedge and nothing below it means anything.

  B. THE REAL TRAJECTORY -- the player's own accepted position reports from
     RUN-1zBW's capture, replayed from the moment the copy wedged. This one does NOT
     end in a caught chase and is not supposed to: that player kept going and was
     3,000 u away by t=60, so both arms leash. What it shows is the copy MOVING
     (705.6 u against 0.0) and it is where the leash interaction was found.

THE LEASH INTERACTION, and why the guard exists. A route out of a corner runs AWAY from
the player before it runs toward them -- the escape leg here is 309 u due EAST of a player
to the west. Judged on the detoured copy, our own pathing tripped the 1,200 u leash and
ended the chase 3 s EARLIER than the straight-line arm did. The leash now also reads the
corridor's solve point and takes the MINIMUM, which is the direction that cannot regress.
Scenario B re-run is what that guard was measured against.

Needs the vault (map 146's navmesh out of the owner's own Gw.dat) and RUN-1zBW's capture.
Read-only. Stdlib only.
"""
import bisect
import json
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
for sub in (("toolkit",), ("toolkit", "authsrv"), ("toolkit", "mapdata")):
    sys.path.insert(0, os.path.join(ROOT, *sub))
import authsrv                       # noqa: E402
from vaultpath import require_dir    # noqa: E402

CAP = os.path.join(require_dir(), "captures", "gamesrv",
                   "authsrv-20260905T213122-c1.jsonl")
MAP146 = 0x1B97D
WEDGE = (10683.46, 4329.52)     # OBSERVED: where the copy stopped
T_WEDGE = 20.5                  # capture seconds
PARKED = (10400.0, 4500.0)      # scenario A's player: 331 u out, clip 0.00, route exists


def player_track():
    t0, rows = None, []
    raw = []
    with open(CAP, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            raw.append(r)
            w = r.get("wall_unix")
            if isinstance(w, (int, float)):
                t0 = w if t0 is None else min(t0, w)
    for r in raw:
        if r.get("kind") != "position_report" or not r.get("accepted"):
            continue
        p, w = r.get("reported"), r.get("wall_unix")
        if p and isinstance(w, (int, float)):
            rows.append((w - t0, float(p[0]), float(p[1])))
    rows.sort()
    return rows


def at(track, t):
    ts = [r[0] for r in track]
    i = bisect.bisect_left(ts, t)
    if i <= 0:
        return track[0][1], track[0][2]
    if i >= len(track):
        return track[-1][1], track[-1][2]
    (t0, x0, y0), (t1, x1, y1) = track[i - 1], track[i]
    f = 0.0 if t1 == t0 else (t - t0) / (t1 - t0)
    return x0 + f * (x1 - x0), y0 + f * (y1 - y0)


def run(pm, router, player_at, t0, t1, hz=20.0):
    """Drive _npc_follow_tick over [t0, t1]; player_at(t) -> (x, y)."""
    authsrv.NPC_FOLLOW_ROUTER = router
    # NPCTRACK-Q1 (2026-09-06): the corridor integrator this file measures is the
    # REVERT arm now (--no-npc-client-model). Under the default the copy is the
    # client's own sync copy, which dead-reckons straight and never wedges -- so
    # both arms here would move and the vacuity guard would fire. Pin the arm.
    authsrv.NPC_CLIENT_MODEL = False
    p0 = player_at(t0)
    agent = {"pos": WEDGE, "plane": 0, "name": "hatcher", "moved_at": t0,
             "moving": True, "follow": {"told": p0, "sent_at": t0, "t0": t0}}
    state = {"pos": p0, "player_dead": False, "agents": {10: agent}}
    halts, moved, prev, now = [], 0.0, agent["pos"], t0
    dt = 1.0 / hz

    def send(op, values, label="", quiet=False):
        if "halts at (" in label:
            halts.append((round(now, 2), label.split(":")[-1].strip()[:52]))

    while now < t1:
        now += dt
        px, py = player_at(now)
        state["pos"] = (px, py)
        ax, ay = agent["pos"]
        authsrv._npc_follow_tick(send, state, 0, 10, agent, (px, py),
                                 math.hypot(px - ax, py - ay), now, pm)
        moved += math.dist(prev, agent["pos"])
        prev = agent["pos"]
    px, py = player_at(t1)
    return moved, agent["pos"], math.hypot(px - agent["pos"][0], py - agent["pos"][1]), halts


def main():
    pm = authsrv.load_pathmap(MAP146)
    if pm is None:
        print("no navmesh for map 146 -- ZERO TRIALS, nothing here is quotable")
        return 3
    saved = authsrv.NPC_FOLLOW_ROUTER
    saved_model = authsrv.NPC_CLIENT_MODEL
    try:
        print("wedge (%.2f, %.2f) on our mesh: %s"
              % (WEDGE + (pm.on_mesh(WEDGE[0], WEDGE[1], 1.0),)))
        cx, cy = pm.clip(WEDGE[0], WEDGE[1], PARKED[0], PARKED[1])
        r = pm.route(WEDGE[0], WEDGE[1], PARKED[0], PARKED[1])
        print("toward the parked player: clip moves %.2f u, route gives %s"
              % (math.hypot(cx - WEDGE[0], cy - WEDGE[1]),
                 ("%d waypoints" % len(r)) if r else "NO PATH"))

        print("\n=== A. POSITIVE CONTROL: player parked %.0f u out, stop radius %.0f u ==="
              % (math.hypot(PARKED[0] - WEDGE[0], PARKED[1] - WEDGE[1]),
                 authsrv.follow_stop_radius({})))
        res = {}
        for router in (False, True):
            res[router] = run(pm, router, lambda _t: PARKED, 0.0, 8.0)
            moved, end, dist, halts = res[router]
            print("  router=%-5s travelled %8.1f u  ended (%.0f,%.0f)  %6.1f u from the "
                  "player  halts %s" % (router, moved, end[0], end[1], dist,
                                        halts[:1] or "none"))
        if res[False][0] > 1.0:
            print("  [FIXTURE FAILURE] the straight-line arm MOVED -- this is not the "
                  "wedge and nothing here is quotable")
            return 1
        print("  -> the routed arm closes the chase the straight-line arm cannot start")

        print("\n=== B. RUN-1zBW's REAL TRAJECTORY, replayed from the wedge (t=%.1f) ==="
              % T_WEDGE)
        track = player_track()
        p0 = at(track, T_WEDGE)
        print("  %d accepted reports; at the wedge the player was (%.0f, %.0f), %.0f u out"
              % (len(track), p0[0], p0[1],
                 math.hypot(p0[0] - WEDGE[0], p0[1] - WEDGE[1])))
        for router in (False, True):
            moved, end, dist, halts = run(pm, router, lambda t: at(track, t),
                                          T_WEDGE, 60.0)
            print("  router=%-5s travelled %8.1f u  ended (%.0f,%.0f)  %6.0f u from the "
                  "player at t=60" % (router, moved, end[0], end[1], dist))
            print("           halts: %s" % (halts[:3] or "none"))
        print("  -> BOTH arms leash here and that is correct: this player kept going and\n"
              "     was ~3,000 u away by t=60. The measurable difference is that the copy\n"
              "     MOVES. The capture's own record: it never moved again after t=20.79.")
    finally:
        authsrv.NPC_FOLLOW_ROUTER = saved
        authsrv.NPC_CLIENT_MODEL = saved_model
    return 0


if __name__ == "__main__":
    sys.exit(main())
