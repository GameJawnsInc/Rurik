r"""Our navmesh boundary against the client's collision, with the tape as the referee -- both ways.

    python studies/movecode/review/meshboundary.py            # every paired tape
    python studies/movecode/review/meshboundary.py --edges    # the corner's boundary segments too

THE QUESTION (MOVECODE-1z-dl). Three findings today put our mesh's boundary and the client's
collision on different lines at the corner of RUN-1zDB: our ray clip stopped 6 u into a wall
the body then slid 93 u along (1z-dd.8); the mirror's pass would have sidestepped at 18.64 s
through a waypoint at (10555, 8072) our mesh calls walkable and the client's halt says is not
(1z-dk); and the corner hold's wall-presses at headings 50-105 deg stood still where our clip
said 0-48 u (1z-dd.6). Only the second is a boundary difference on its face; the first is a slide
our RAY does not take (the body's centre stayed within 1 u of our edge), and the third may be
walls we do have. This census measures the boundary itself, in both directions, with the
drawn body as the referee:

  (A) WE WALKABLE, THE CLIENT BLOCKED: a 0x003D whose drawn body moves < 2 u in the next 0.5 s,
      with NO hostile inside the combined radius and the 60-degree cone (else it is 1z-dk's
      halt), while our mesh holds the point 12 u along the heading AND the ray runs >= 20 u.
  (B) THE CLIENT WALKS, WE SAY OFF: any drawn-body sample whose centre is > 3 u off our mesh
      (`nearest_walkable`), counted as episodes with their worst depth and where they were.
  plus the agreement classes, so the two disagreement rates have their denominators.

PREDICTION, stated first: (A) rare and clustered north-east of the corner around (10555, 8072);
(B) near zero -- the morning's slide ran ON our edge, and the client's copies stand where exact
containment says nothing is only within SEAM_TOL (pathmap.on_mesh's own measurement).

Standard library only; the vault through vaultpath; the mesh through authsrv.load_pathmap.
"""
import bisect
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _sub in ("toolkit", "toolkit/authsrv", "toolkit/clientscan", "toolkit/mapdata"):
    sys.path.insert(0, os.path.join(ROOT, _sub))

import vaultpath                  # noqa: E402

INF = float("inf")
CORNER = (10488.0, 8117.0)
PAIRS = [("1zDB-A", "captures/gamesrv/authsrv-20260910T141412-c1.jsonl", "research/movecode/1zdb1-agenttap.jsonl"),
         ("1zDB-B", "captures/gamesrv/authsrv-20260910T141651-c1.jsonl", "research/movecode/1zdb2-agenttap.jsonl"),
         ("1zDB-3", "captures/gamesrv/authsrv-20260910T151457-c1.jsonl", "research/movecode/1zdb3-agenttap.jsonl"),
         ("1zDB-4", "captures/gamesrv/authsrv-20260910T151638-c1.jsonl", "research/movecode/1zdb4-agenttap.jsonl"),
         ("1zDC-1", "captures/gamesrv/authsrv-20260910T154327-c1.jsonl", "research/movecode/1zdc1-agenttap.jsonl"),
         ("1zDC-2", "captures/gamesrv/authsrv-20260910T154638-c1.jsonl", "research/movecode/1zdc2-agenttap.jsonl"),
         ("1zCG-s8", "captures/gamesrv/authsrv-20260909T221342-c1.jsonl", "research/movecode/1zcg8-agenttap.jsonl"),
         # RUN-1zCW's six agent-driven steer legs (paired by wall time, within 2 s)
         ("1zCW-T1", "captures/gamesrv/authsrv-20260909T114746-c1.jsonl", "research/movecode/1zcw-T1-agenttap.jsonl"),
         ("1zCW-C1", "captures/gamesrv/authsrv-20260909T115038-c1.jsonl", "research/movecode/1zcw-C1-agenttap.jsonl"),
         ("1zCW-T2", "captures/gamesrv/authsrv-20260909T115701-c1.jsonl", "research/movecode/1zcw-T2-agenttap.jsonl"),
         ("1zCW-C2", "captures/gamesrv/authsrv-20260909T115902-c1.jsonl", "research/movecode/1zcw-C2-agenttap.jsonl"),
         ("1zCW-T3", "captures/gamesrv/authsrv-20260909T120108-c1.jsonl", "research/movecode/1zcw-T3-agenttap.jsonl"),
         ("1zCW-C3", "captures/gamesrv/authsrv-20260909T120301-c1.jsonl", "research/movecode/1zcw-C3-agenttap.jsonl")]
STILL_U, WALK_U, OFF_U, AHEAD_U, RAY_U = 2.0, 10.0, 3.0, 12.0, 20.0


def _load(cap, tape):
    rows = [json.loads(l) for l in open(cap, encoding="utf-8")]
    T = [json.loads(l) for l in open(tape, encoding="utf-8")]
    t0 = T[0]["t0"]
    S = [s for s in T if s.get("kind") == "sample"]
    cap0 = rows[0]["wall_unix"] - rows[0]["t"]
    W = [t0 + s["t"] - cap0 for s in S]
    return rows, S, W


def _at(S, W, t):
    i = bisect.bisect_left(W, t)
    return S[min(max(i, 0), len(S) - 1)]


def _drawn(s, aid="1"):
    a = s["agents"].get(aid, {}).get("async")
    return (a["x"], a["y"]) if a else None


def census(verbose=True, edges=False):
    import agtrack_mirror as am
    import content
    import authsrv
    V = vaultpath.vault_root()
    pm = authsrv.load_pathmap(content.load().map_static_config()[148][0])
    R, cosc = am.AVOID_COMBINED_RADIUS, am.AVOID_COS_CONE
    cls = {}
    A_rows, B_eps = [], []
    n_samples = n_off = 0
    for name, cap, tape in PAIRS:
        cap, tape = os.path.join(V, cap), os.path.join(V, tape)
        if not (os.path.exists(cap) and os.path.exists(tape)):
            continue
        rows, S, W = _load(cap, tape)
        # every movement order the client sent, so a press that was released or
        # re-aimed inside the window is not read as a wall
        orders = sorted(r["t"] for r in rows if r.get("kind") == "decoded"
                        and r.get("name") in ("MOVE_SET_HEADING", "MOVE_CANCEL_REPORT_POSITION",
                                              "MOVE_TO", "ROTATE_PLAYER"))
        # (A) every heading report
        for r in rows:
            if r.get("kind") != "decoded" or r.get("name") != "MOVE_SET_HEADING":
                continue
            v = r["values"]
            if len(v) < 4:
                continue
            t = r["t"]
            hx, hy = float(v[3][0]), float(v[3][1])
            hm = math.hypot(hx, hy)
            if hm < 1.0:
                continue
            ux, uy = hx / hm, hy / hm
            s0, s1 = _at(S, W, t), _at(S, W, t + 0.5)
            b0, b1 = _drawn(s0), _drawn(s1)
            if not (b0 and b1):
                continue
            moved = math.hypot(b1[0] - b0[0], b1[1] - b0[1])
            j = bisect.bisect_right(orders, t + 0.005)
            held = not (j < len(orders) and orders[j] <= t + 0.5)
            hostile = False          # the pass's own trigger: inside the disc AND the cone
            approach = None          # inside the disc, in the front half-plane: the overlap
            for aid in ("10", "11"):
                h = _drawn(s0, aid)
                if not h:
                    continue
                rx, ry = h[0] - b0[0], h[1] - b0[1]
                d = math.hypot(rx, ry)
                if not d:
                    continue
                c = (rx * ux + ry * uy) / d
                if d <= R and c > cosc:
                    hostile = True
                if d <= R and c > 0.0:
                    approach = (round(d), round(math.degrees(math.acos(max(-1.0, min(1.0, c))))))
            plane = pm.plane_at(b0[0], b0[1], prefer=0)
            ex, ey = b0[0] + ux * 767.0, b0[1] + uy * 767.0
            st = (pm.clip(b0[0], b0[1], ex, ey, step=2.0, plane=plane) if plane is not None
                  else pm.clip(b0[0], b0[1], ex, ey, step=2.0))
            ray = math.hypot(st[0] - b0[0], st[1] - b0[1])
            ahead_on = pm.on_mesh(b0[0] + ux * AHEAD_U, b0[1] + uy * AHEAD_U)
            we_clear = (ray >= RAY_U and ahead_on)
            if hostile:
                key = "hostile-in-cone (1z-dk's class, excluded)"
            elif moved < STILL_U and not held:
                key = "still, but released or re-aimed inside the window (not a block)"
            elif moved < STILL_U and we_clear and approach:
                key = "A2: client BLOCKED, we WALKABLE, a hostile inside 80 u ahead (overlap, outside the cone)"
                A_rows.append((name, round(t, 2), (round(b0[0]), round(b0[1])),
                               round(math.degrees(math.atan2(uy, ux))), round(ray),
                               round(math.hypot(b0[0] - CORNER[0], b0[1] - CORNER[1])), approach))
            elif moved < STILL_U and we_clear:
                key = "A1: client BLOCKED, we WALKABLE, no hostile near -- a WALL we lack"
                A_rows.append((name, round(t, 2), (round(b0[0]), round(b0[1])),
                               round(math.degrees(math.atan2(uy, ux))), round(ray),
                               round(math.hypot(b0[0] - CORNER[0], b0[1] - CORNER[1])), None))
            elif moved < STILL_U:
                key = "still, we block too (ray < 20 u or 12 u ahead off)"
            elif moved >= WALK_U and we_clear:
                key = "walks, we clear too"
            elif moved >= WALK_U:
                key = "walks, we block (the body slid or turned; see B for off-mesh depth)"
            else:
                key = "moved 2-10 u (ambiguous)"
            cls[key] = cls.get(key, 0) + 1
        # (B) every drawn-body sample off our mesh by > OFF_U, as episodes
        cur = None
        for s, w in zip(S, W):
            b = _drawn(s)
            if not b:
                continue
            n_samples += 1
            off = 0.0
            if not pm.on_mesh(b[0], b[1], OFF_U):
                nw = pm.nearest_walkable(b[0], b[1], 200.0)
                off = nw[2] if nw else 200.0
            if off > OFF_U:
                n_off += 1
                if cur is None:
                    cur = {"run": name, "t0": w, "t1": w, "worst": off, "at": b}
                else:
                    cur["t1"] = w
                    if off > cur["worst"]:
                        cur["worst"], cur["at"] = off, b
            elif cur is not None:
                B_eps.append(cur)
                cur = None
        if cur is not None:
            B_eps.append(cur)
    if verbose:
        print("(A) heading reports by class, seven tapes:")
        for k, v in sorted(cls.items(), key=lambda kv: -kv[1]):
            print(f"   {v:5d}  {k}")
        print(f"   A instances (run, t, body, heading deg, our ray u, from the corner u):")
        for a in A_rows[:24]:
            print("     ", a)
        print(f"(B) drawn-body samples off our mesh by > {OFF_U:.0f} u: {n_off} of {n_samples}; episodes {len(B_eps)}")
        for e in sorted(B_eps, key=lambda e: -e["worst"])[:10]:
            print(f"      {e['run']} {e['t0']:.2f}-{e['t1']:.2f} s worst {e['worst']:.1f} u at "
                  f"({e['at'][0]:.0f},{e['at'][1]:.0f}), {math.hypot(e['at'][0]-CORNER[0], e['at'][1]-CORNER[1]):.0f} u from the corner")
    if edges:
        from pathmap import _Walls
        walls = _Walls(pm, 0)
        near = []
        for ax, ay, bx, by, nx, ny in walls.segs:
            mx, my = (ax + bx) / 2, (ay + by) / 2
            if math.hypot(mx - CORNER[0], my - CORNER[1]) <= 160.0:
                near.append((round(ax), round(ay), round(bx), round(by), round(math.degrees(math.atan2(ny, nx)))))
        print(f"\nour plane-0 boundary segments within 160 u of the corner ({len(near)}): (ax, ay, bx, by, outward normal deg)")
        for seg in sorted(near):
            print("     ", seg)
    return cls, A_rows, B_eps


if __name__ == "__main__":
    census(edges="--edges" in sys.argv)
