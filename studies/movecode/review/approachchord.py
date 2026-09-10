r"""The approach's CHORD against the mesh -- 1z-cn's question, asked of the player's own follow leg.

    python studies/movecode/review/approachchord.py

THE QUESTION (MOVECODE-1z-dn). 1z-cn traced the hostile's standing RED to a straight chord:
"the point we order is always on the mesh; the LINE to it is not", and `0x002A` is dead-reckoned
rather than pathed. The player's approach has the same shape and has never been asked. Unlike
the hostile's case the WIRE is not at risk -- `_approach_send` sends the TARGET's own position
and the client paths the body itself -- so a chord through a wall is a MODEL error, not a bad
grant. It still costs, because `state["pos"]` is the NPC follow's order operand (1z-cp.3): a
model that walks through a wall is a phantom the hostile chases.

WHAT IS SCORED, per approach send:
  * the CHORD from the body's own position to the stop point (the point `follow_stop_radius`
    short of the target along the line) against the map's pathmap -- clear, or cut and by how
    much. The origin is the drawn body where a tape covers the instant, else the last accepted
    report: both are the CLIENT's own position, which is what the client's pathing starts from
    and what our leg claims to model.
  * the ORDERED POINT's own off-mesh distance, so the 1z-cn distinction (the point is fine, the
    line is not) is measurable here too rather than assumed.
  * the REFEREE, where a tape covers it: what the drawn body actually did over the leg -- how
    far it travelled, and its worst distance from our chord.

PREDICTION, stated before the first run: most approach chords are CLEAR (the corpus's approaches
are 55-160 u on open ground); a minority near the stairs are cut; the ordered point is on the
mesh in nearly all cases (1z-cn: 0 of 159 off, on the hostile's side); and where the chord IS
cut, the drawn body did not walk it.

Standard library only; the vault through vaultpath; the mesh through authsrv.load_pathmap.
"""
import bisect
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _sub in ("toolkit", "toolkit/authsrv", "toolkit/clientscan", "toolkit/mapdata"):
    sys.path.insert(0, os.path.join(ROOT, _sub))

import vaultpath                  # noqa: E402

APPROACH = re.compile(r"APPROACH( re-path)?: player -> agent (\d+) at \((-?\d+),(-?\d+)\), "
                      r"([\d.]+) u out, stops at ([\d.]+) u")
# the tapes that cover an approach-carrying capture, by capture stem
TAPES = {"20260909T221342": "research/movecode/1zcg8-agenttap.jsonl",
         "20260910T141412": "research/movecode/1zdb1-agenttap.jsonl",
         "20260910T141651": "research/movecode/1zdb2-agenttap.jsonl"}
STEP = 2.0                        # authsrv.A2_LEAD_CLIP_STEP
CUT_U = 5.0                       # a chord counts as cut when the clip stops this far short


def _tape(path, cap_rows):
    T = [json.loads(l) for l in open(path, encoding="utf-8")]
    t0 = T[0]["t0"]
    S = [s for s in T if s.get("kind") == "sample"]
    cap0 = cap_rows[0]["wall_unix"] - cap_rows[0]["t"]
    return S, [t0 + s["t"] - cap0 for s in S]


def _at(S, W, t):
    i = bisect.bisect_left(W, t)
    return S[min(max(i, 0), len(S) - 1)]


def _drawn(s, aid="1"):
    a = s["agents"].get(aid, {}).get("async")
    return (a["x"], a["y"]) if a else None


def _seg_dist(p, a, b):
    ax, ay, bx, by = a[0], a[1], b[0], b[1]
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0.0 if L2 <= 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / L2))
    return math.hypot(p[0] - (ax + dx * t), p[1] - (ay + dy * t))


def census(verbose=True):
    import content
    import authsrv
    V = vaultpath.require_dir("captures", "gamesrv", why="the approach chord census")
    world = content.load()
    meshes = {}
    rows = []
    for fn in sorted(os.listdir(V)):
        if not fn.endswith(".jsonl"):
            continue
        path = os.path.join(V, fn)
        try:
            crows = [json.loads(l) for l in open(path, encoding="utf-8")]
        except Exception:                                   # noqa: BLE001
            continue
        sends = [r for r in crows if r.get("kind") == "sent" and APPROACH.search(r.get("label", ""))]
        if not sends:
            continue
        mid = next((r.get("map_id") for r in crows if r.get("kind") == "version"), None)
        if mid is None:
            continue
        if mid not in meshes:
            try:
                meshes[mid] = authsrv.load_pathmap(world.map_static_config()[int(mid)][0])
            except Exception as e:                          # noqa: BLE001
                print("  [mesh] map %s: %s" % (mid, e))
                meshes[mid] = None
        pm = meshes[mid]
        if pm is None:
            continue
        stem = fn.split("-")[1]
        S = W = None
        tp = TAPES.get(stem)
        if tp:
            tp = os.path.join(vaultpath.vault_root(), tp)
            if os.path.exists(tp):
                S, W = _tape(tp, crows)
        reps = sorted((r["t"], tuple(r["reported"])) for r in crows
                      if r.get("kind") == "position_report" and r.get("accepted"))
        rt = [x[0] for x in reps]
        for r in sends:
            m = APPROACH.search(r["label"])
            t = r["t"]
            aid = m.group(2)
            tgt = (float(m.group(3)), float(m.group(4)))
            stop = float(m.group(6))
            origin = osrc = None
            if S is not None:
                b = _drawn(_at(S, W, t))
                if b:
                    origin, osrc = b, "tape"
            if origin is None:
                i = bisect.bisect_right(rt, t)
                if i:
                    origin, osrc = reps[i - 1][1], "report"
            if origin is None:
                continue
            d = math.hypot(tgt[0] - origin[0], tgt[1] - origin[1])
            run = max(d - stop, 0.0)
            if run <= 1.0:
                rows.append({"cap": stem, "t": round(t, 2), "src": osrc, "run": 0.0,
                             "cut": 0.0, "pt_off": 0.0, "body": None, "worst": None})
                continue
            f = run / d
            sp = (origin[0] + (tgt[0] - origin[0]) * f, origin[1] + (tgt[1] - origin[1]) * f)
            plane = pm.plane_at(origin[0], origin[1], prefer=0)
            st = (pm.clip(origin[0], origin[1], sp[0], sp[1], step=STEP, plane=plane)
                  if plane is not None else
                  pm.clip(origin[0], origin[1], sp[0], sp[1], step=STEP))
            reached = math.hypot(st[0] - origin[0], st[1] - origin[1])
            cut = max(run - reached, 0.0)
            nw = None if pm.on_mesh(sp[0], sp[1]) else pm.nearest_walkable(sp[0], sp[1], 200.0)
            rec = {"cap": stem, "t": round(t, 2), "src": osrc, "run": round(run, 1),
                   "cut": round(cut, 1), "pt_off": round(nw[2], 1) if nw else 0.0,
                   "body": None, "worst": None, "tgt": (round(tgt[0]), round(tgt[1]))}
            if S is not None:
                eta = t + run / 288.0
                pts = [(_at(S, W, t + k * 0.1)) for k in range(0, max(1, int((eta - t) / 0.1)) + 1)]
                bp = [p for p in (_drawn(s) for s in pts) if p]
                if len(bp) >= 2:
                    rec["body"] = round(math.hypot(bp[-1][0] - bp[0][0], bp[-1][1] - bp[0][1]), 1)
                    rec["worst"] = round(max(_seg_dist(p, origin, sp) for p in bp), 1)
            rows.append(rec)
    if verbose:
        n = len(rows)
        moving = [r for r in rows if r["run"] > 1.0]
        cutr = [r for r in moving if r["cut"] > CUT_U]
        offp = [r for r in moving if r["pt_off"] > 1.0]
        print(f"approach sends with an origin: {n} ({len(moving)} with a leg to walk, "
              f"{n - len(moving)} already inside the stop radius)")
        print(f"  chords the mesh CUTS by > {CUT_U:.0f} u: {len(cutr)} of {len(moving)}")
        print(f"  ordered STOP POINTS off the mesh:      {len(offp)} of {len(moving)}"
              f"   (1z-cn on the hostile's side: 0 of 159)")
        if cutr:
            print("   the cut ones (cap, t, leg u, cut u, point off-mesh u, body travelled, worst |body - chord|):")
            for r in sorted(cutr, key=lambda r: -r["cut"]):
                print("     %-16s %6.2f  leg %5.1f  cut %5.1f  pt_off %4.1f  body %s  worst %s"
                      % (r["cap"], r["t"], r["run"], r["cut"], r["pt_off"],
                         r["body"], r["worst"]))
        ref = [r for r in moving if r["worst"] is not None]
        if ref:
            print(f"  the referee, where a tape covers the leg ({len(ref)}): worst |drawn body - our chord|")
            for r in sorted(ref, key=lambda r: -(r["worst"] or 0))[:8]:
                print("     %-16s %6.2f  leg %5.1f  cut %5.1f  body travelled %5.1f  worst %5.1f"
                      % (r["cap"], r["t"], r["run"], r["cut"], r["body"] or 0.0, r["worst"]))
    return rows


if __name__ == "__main__":
    census()
