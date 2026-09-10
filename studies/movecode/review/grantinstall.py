r"""Which of our keyboard leads the client's sync copy INSTALLED, and why the rest were not.

    python studies/movecode/review/grantinstall.py            # the census over the five tapes
    python studies/movecode/review/grantinstall.py --specimen # three instants through the mirror's own pass

THE QUESTION (MOVECODE-1z-dk). 1z-cq observed "the client REFUSES our long leads while parked
-- 0 of 7 grants >= 400 u appear in either world copy's m_targetPoint vs 12 of 18 unparked",
and 1z-dj registered the mechanism as an undecoded client rule. This reads it off the tape and
the binary. The tape: agenttap's sync copy carries `tx, ty` (m_targetPoint, +0x9C) and `stop`
(+0x48, the arrival timer -- 0 = no walk in flight, i.e. parked). A lead is INSTALLED when the
sync target equals the grant point within 0.25 s; SUPERSEDED when the target is a LATER grant by
then; NEVER when neither. The binary: 0x0029's handler 0x005FD890 has no gate (two asserts, then
the setter 0x00602A40 unconditionally); the setter writes +0x9C..+0xA8 unconditionally, then the
bake 0x005FE950, the terrain trace 0x00600840 and the agent-avoidance pass 0x006011F0 -- whose
HALT (0x00601899 -> 0x006020B0) zeroes the velocity and invalidates both target blocks. So a
grant that "never appeared" was written and invalidated in the same call, by the pass.

PREDICTION, stated first: refusals coincide with a hostile inside the combined radius (80 u)
within the 60-degree cone of the lead, and the parked/walking split is the corner confound (a
copy is parked BECAUSE it is blocked where the sidestep waypoint fails the mesh). The one check
that could refute the reading: at the client's halts, our own mesh at the pass's waypoint should
say OFF (we would halt too); a large ON share would mean the client refuses for a reason the pass
does not model.

MEASURED 2026-09-10 (RUN-1zDB legs A/B, RUN-1zCG session 8, RUN-1zDC legs 1/2): 452 leads, 190
installed. Parked + hostile in the cone: 72, 0 installed (62 never, 10 superseded). Walking +
clear: 211, 167 installed, 38 superseded, 6 never. Parked + clear: 8 (6 never, 2 superseded).
At the 72 client halts our mesh says OFF at the pass's waypoint in 71; the one ON (leg B 18.64,
waypoint (10555, 8072)) is the corner's north-east side and is what seeded the --mesh replay's
514 u mirror cascade (the mirror sidestepped where the client halted, and every later waypoint
was computed from a displaced copy).

Standard library only; the vault through vaultpath; the mirror through agtrack_mirror.
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

INF = float("inf")
LEAD = re.compile(r"KBD LEAD \((-?\d+),(-?\d+)\) from \((-?\d+),(-?\d+)\)")
RUNS = [("1zDB-A", "captures/gamesrv/authsrv-20260910T141412-c1.jsonl", "research/movecode/1zdb1-agenttap.jsonl"),
        ("1zDB-B", "captures/gamesrv/authsrv-20260910T141651-c1.jsonl", "research/movecode/1zdb2-agenttap.jsonl"),
        ("1zCG-s8", "captures/gamesrv/authsrv-20260909T221342-c1.jsonl", "research/movecode/1zcg8-agenttap.jsonl"),
        ("1zDC-1", "captures/gamesrv/authsrv-20260910T154327-c1.jsonl", "research/movecode/1zdc1-agenttap.jsonl"),
        ("1zDC-2", "captures/gamesrv/authsrv-20260910T154638-c1.jsonl", "research/movecode/1zdc2-agenttap.jsonl")]


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


def _pass_waypoint(cx, cy, ux, uy, hx, hy, R, pad, cos_cone):
    """The client's sidestep waypoint for one obstacle, or None when the pass
    would not fire (outside the disc or the cone). Mirrors SyncAgent.avoid."""
    rx, ry = hx - cx, hy - cy
    d = math.hypot(rx, ry)
    if d <= 0.0 or d > R or (rx * ux + ry * uy) / d <= cos_cone:
        return None
    across = -rx * uy + ry * ux
    disp = (R + pad) - abs(across)
    side = -1.0 if across > 0.0 else 1.0
    return (cx - uy * side * disp, cy + ux * side * disp), d, across


def census(verbose=True):
    import agtrack_mirror as am
    import content
    import authsrv
    V = vaultpath.vault_root()
    pm = authsrv.load_pathmap(content.load().map_static_config()[148][0])
    R, pad, cosc = am.AVOID_COMBINED_RADIUS, am.AVOID_PAD, am.AVOID_COS_CONE
    cells, halts_off, halts_on, halts_nocone, on_examples = {}, 0, 0, 0, []
    n_leads = n_inst = 0
    for name, cap, tape in RUNS:
        cap, tape = os.path.join(V, cap), os.path.join(V, tape)
        if not (os.path.exists(cap) and os.path.exists(tape)):
            continue
        rows, S, W = _load(cap, tape)
        leads = []
        for r in rows:
            if r.get("kind") != "sent":
                continue
            m = LEAD.match(r.get("label", ""))
            if m:
                leads.append((r["t"], (int(m.group(1)), int(m.group(2))),
                              (int(m.group(3)), int(m.group(4)))))
        pts, lt = [l[1] for l in leads], [l[0] for l in leads]
        for t, g, frm in leads:
            L = math.hypot(g[0] - frm[0], g[1] - frm[1])
            if L < 100.0:
                continue
            n_leads += 1
            s0 = _at(S, W, t - 0.03)
            y0 = s0["agents"]["1"]["sync"]
            parked = (y0["stop"] == 0)
            cx, cy = (y0["x"], y0["y"]) if y0["x"] != INF else frm
            ux, uy = g[0] - cx, g[1] - cy
            Lu = math.hypot(ux, uy)
            if Lu < 1.0:
                continue
            ux, uy = ux / Lu, uy / Lu
            wp = None
            for aid in ("10", "11"):
                h = s0["agents"].get(aid, {}).get("sync") or s0["agents"].get(aid, {}).get("async")
                if h:
                    wp = _pass_waypoint(cx, cy, ux, uy, h["x"], h["y"], R, pad, cosc)
                    if wp:
                        break
            verdict = "never"
            for dt in (0.05, 0.12, 0.25, 0.5):
                s = _at(S, W, t + dt)
                tx, ty = s["agents"]["1"]["sync"]["tx"], s["agents"]["1"]["sync"]["ty"]
                if abs(tx - g[0]) < 2 and abs(ty - g[1]) < 2:
                    verdict = "installed"
                    break
                if tx != INF and any(abs(p[0] - tx) < 2 and abs(p[1] - ty) < 2 and lt[i] > t
                                     for i, p in enumerate(pts)):
                    verdict = "superseded"
                    break
            n_inst += (verdict == "installed")
            key = ("parked" if parked else "walking", "hostile-in-cone" if wp else "clear", verdict)
            cells[key] = cells.get(key, 0) + 1
            if parked and verdict != "installed":
                if wp is None:
                    halts_nocone += 1
                elif pm.on_mesh(wp[0][0], wp[0][1]):
                    halts_on += 1
                    if len(on_examples) < 4:
                        on_examples.append((name, round(t, 2), (round(cx), round(cy)),
                                            (round(wp[0][0]), round(wp[0][1])), round(wp[1]), round(wp[2])))
                else:
                    halts_off += 1
    if verbose:
        print(f"keyboard leads >= 100 u across {len(RUNS)} runs: {n_leads}, installed {n_inst}")
        for k, v in sorted(cells.items()):
            print(f"  copy {k[0]:8s} {k[1]:16s} {k[2]:11s} {v:4d}")
        print(f"client halts at the setter (parked, not installed): hostile in the cone {halts_off + halts_on}, "
              f"none in the cone {halts_nocone}")
        print(f"  our mesh at the pass's waypoint: OFF (we halt too) {halts_off} | ON (we sidestep) {halts_on}")
        for e in on_examples:
            print("   ", e)
    return cells, halts_off, halts_on, halts_nocone


def specimen(verbose=True):
    """Three instants through the shipped mirror's own pass with our mesh."""
    import agtrack_mirror as am
    import content
    import authsrv
    pm = authsrv.load_pathmap(content.load().map_static_config()[148][0])
    out = []
    for label, cx, cy, hx, hy, gx, gy in (
            ("1zDB-B 23.54 (refused)", 10499.0, 8075.0, 10517.0, 8006.0, 10406.0, 7564.0),
            ("1zDB-B 23.79 (installed)", 10481.0, 8071.0, 10517.0, 8006.0, 10062.0, 7764.0),
            ("1zDB-A 30.36 (the ghost)", 10488.0, 8117.0, 10458.0, 8054.0, 10266.0, 7647.0)):
        s = am.AgTrackMirror(mesh=am.MeshAdapter(pm)).sync
        s.set_position(cx, cy, 0, 1000)
        s.max_speed, s.move_speed = 288.0, 1.0
        s.bake_grant(gx, gy, 0, 0, 1000)
        res = s.avoid(1000, [(hx, hy, 0.0, 0.0)], mesh_ok=pm.on_mesh)
        out.append((label, res))
        if verbose:
            print(f"  {label:26s} -> the pass says {res}")
    return out


if __name__ == "__main__":
    if "--specimen" in sys.argv:
        specimen()
    else:
        census()
