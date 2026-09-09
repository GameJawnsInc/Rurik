#!/usr/bin/env python3
"""What decides how far the Hatcher stands from the DRAWN player at a halt? (MOVECODE-1z-cv)

    python studies/movecode/review/haltreach.py                 # every RUN-1zCG session with a tape
    python studies/movecode/review/haltreach.py --cap C          # one capture (tape by wall overlap)
    python studies/movecode/review/haltreach.py --check          # sec.1z-cv's bars

THE QUESTION sec.1z-cs.2 LEFT OPEN. Shape 2 would hand the follow `_npc_frame` (the client's
world-0 copy of the player) instead of `state["pos"]` (the position model) as the point it
orders; two retrodiction scorers disagreed about it -- the order's error against the DRAWN
body ranks it worse, against WORLD-0 better -- and neither was pre-registered. The operator
feels neither. The operator feels **the Hatcher's drawn body standing outside melee reach of
their own drawn body** at the halt (sec.1z-cp.2: p50 100.6 u moving, 10 of 19 beyond 92 u).

WHAT DECIDES THAT DISTANCE, from the follow's own code (authsrv `_npc_model_advance`,
`_npc_follow_tick`): the copy dead-reckons toward the ORDERED point and parks EITHER when it
enters the 80 u disc around `_npc_frame` with the frame in its cone (a DISC park -- and the
client does the same around its own world-0, NPCTRACK-Q1) OR when it arrives at the ordered
point with no disc entered (a POINT park). So at a disc park the halt point is 80 u from the
FRAME whatever was ordered, and the felt distance is `80 (+/- the angle) + |frame - body|`;
only at a point park does the ordered point reach the outcome at all. Shape 2 can therefore
only ever change point parks (it turns every park into a disc park around the frame), and
its ceiling everywhere is the frame's own error against the drawn body -- world-0's lag.

WHAT THIS MEASURES, per 0x0028 halt sent to the hostile, joined to the agenttap tape at the
halt's wall instant (the join is validated per halt: the server's own park point against the
tape's hostile body, which NPCTRACK-Q1 put at 6.7-15.7 u):

  mechanism   DISC (an npc_model act=disc row since the last order) or POINT
  felt        |hostile body - player body|      the operator's quantity; in reach <= 92 u
  park-frame  |hostile body - player world-0|   80 by construction at a disc park
  frame-body  |player world-0 - player body|    the client's own lag; shape 2's floor
  order-body  |ordered point - player body|     the drawn-body scorer of sec.1z-cs.2
  order-w0    |ordered point - player world-0|  the world-0 scorer of sec.1z-cs.2

and the derived shape-2 counterfactual with NO simulator: a point park becomes a disc park at
80 u from the frame, felt' = |park' - body| with park' on the frame's disc along the chord from
the hostile's start; a disc park is unchanged. Everything else is printed as what it is.

Read-only. Stdlib only. Needs the vault (captures and tapes are the owner's own).
"""
import bisect
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/clientscan", "toolkit/authsrv", "studies/movecode/review"):
    sys.path.insert(0, os.path.join(ROOT, sub))

import vaultpath                                   # noqa: E402
import w0score as W                                # noqa: E402
import sessionscore as S                           # noqa: E402

REACH = 92.0          # authsrv.enemy_reach(): the swing opens inside this
STOP = 80.0           # authsrv.follow_stop_radius(): the disc
JOIN_OK = 20.0        # u: server park point vs tape hostile body, Q1's 6.7-15.7 with margin
HOSTILE = 10


def halts(rows):
    """Every 0x0028 to the hostile, with the order and the park that preceded it."""
    out = []
    last_order = None
    park = None
    for r in rows:
        k = r.get("kind")
        if k == "npc_order" and r.get("agent") == HOSTILE:
            last_order = r
            park = None
        elif (k == "sent" and r.get("opcode") in (0x2A, 0x29)
              and (r.get("plain") or "")[4:12] == "0a000000"
              and "FOLLOW" in (r.get("label") or "") and "player at (" in r["label"]):
            # Sessions before MOVECODE-1z-cn (2026-09-08) carry no npc_order row; the
            # sent follow's own label names the point it ordered (to the unit) and the
            # tape's hostile body at that instant is where it set off from -- filled in
            # by score() -- so those sessions score too, marked as such.
            try:
                xy = r["label"].split("player at (")[1].split(")")[0].split(",")
                last_order = {"to": [float(xy[0]), float(xy[1])], "solve_from": None,
                              "wall_unix": r["wall_unix"], "from_label": True}
                park = None
            except (IndexError, ValueError):
                pass
        elif k == "npc_model" and r.get("agent") == HOSTILE and r.get("act") == "disc":
            park = r
        elif k == "sent" and r.get("opcode") == 0x28 and (r.get("plain") or "").startswith("28000a00"):
            out.append({"t": r["t"], "w": r["wall_unix"], "label": r.get("label", ""),
                        "order": last_order, "disc": park})
            park = None
    return out


COS_CONE = 0.5        # authsrv.NPC_DISC_COS_CONE: the resolver's +-60 degree cone


def park_of(start, target, centre):
    """Where a copy set off at `start` toward `target` parks, by the resolver's own
    rule (authsrv._npc_disc_hit_ms, on the leg's line): the FIRST point of the leg
    inside the `STOP` disc around `centre` with the centre inside the forward cone
    -> (point, "disc"); else the target itself -> (target, "point")."""
    sx, sy = start
    tx, ty = target
    cx, cy = centre
    vx, vy = tx - sx, ty - sy
    v2 = vx * vx + vy * vy
    if v2 <= 1e-9:
        return (sx, sy), "point"
    qx, qy = sx - cx, sy - cy
    q2 = qx * qx + qy * qy
    r2 = STOP * STOP
    if q2 <= r2:
        hit = (sx, sy)
    else:
        b = qx * vx + qy * vy
        disc = b * b - v2 * (q2 - r2)
        if disc < 0.0:
            return (tx, ty), "point"
        u = (-b - math.sqrt(disc)) / v2
        if u < 0.0 or u > 1.0:
            return (tx, ty), "point"
        hit = (sx + vx * u, sy + vy * u)
    dx, dy = cx - hit[0], cy - hit[1]
    d = math.hypot(dx, dy)
    if d > 1e-9 and (vx * dx + vy * dy) / (math.sqrt(v2) * d) < COS_CONE:
        return (tx, ty), "point"
    return hit, "disc"


def nearest(series, w):
    ws = [s["w"] for s in series]
    i = bisect.bisect_left(ws, w)
    cands = [j for j in (i - 1, i) if 0 <= j < len(series)]
    if not cands:
        return None
    j = min(cands, key=lambda j: abs(ws[j] - w))
    return series[j] if abs(ws[j] - w) <= 0.25 else None


def score(cap_path, tape_path):
    rows = W.load_gamesrv(cap_path)
    head, trows = W.load(tape_path)
    p1 = W.series(head, trows, 1)
    p10 = W.series(head, trows, HOSTILE)
    reps = [r for r in rows if r.get("kind") == "position_report" and r.get("accepted")]
    rep_w = [r["wall_unix"] for r in reps]
    out = []
    for h in halts(rows):
        a = nearest(p1, h["w"])
        b = nearest(p10, h["w"])
        if a is None or b is None or h["order"] is None:
            out.append(dict(h, valid=False, why="no tape sample within 0.25 s or no order"))
            continue
        body, w0 = a["body"], a["w0"]
        hb = b["body"]
        M = tuple(h["order"]["to"])
        mech = "disc" if h["disc"] is not None else "point"
        # the join validated on the server's own park point vs the tape's hostile body
        srv_park = tuple(h["disc"]["at"]) if h["disc"] else None
        lab = h["label"]
        if srv_park is None:
            try:
                s = lab.split("halts at (")[1].split(")")[0].split(",")
                srv_park = (float(s[0]), float(s[1]))
            except Exception:                        # noqa: BLE001
                srv_park = None
        join = math.dist(srv_park, hb) if srv_park else float("nan")
        F = tuple(h["disc"]["frame"]) if h["disc"] else w0
        # the frame at the ORDER instant, from the tape: world-0 then, and the
        # last accepted report (the body's position as the client last stated it)
        ao = nearest(p1, h["order"]["wall_unix"])
        w0_order = ao["w0"] if ao else w0
        i_rep = bisect.bisect_right(rep_w, h["order"]["wall_unix"]) - 1
        R = tuple(reps[i_rep]["reported"]) if i_rep >= 0 else None
        rec = dict(h, valid=(join == join and join <= JOIN_OK), mech=mech,
                   felt=math.dist(hb, body), park_w0=math.dist(hb, w0),
                   frame_body=math.dist(w0, body), order_body=math.dist(M, body),
                   order_w0=math.dist(M, w0), frame_srv=math.dist(F, body),
                   join=join, moving=a["vbody"] > 1.0, M=M, F=F, body=body, w0=w0, hb=hb,
                   start=(tuple(h["order"]["solve_from"]) if h["order"].get("solve_from")
                          else (nearest(p10, h["order"]["wall_unix"]) or {}).get("body")),
                   from_label=bool(h["order"].get("from_label")))
        if rec["start"] is None:
            out.append(dict(h, valid=False, why="no tape sample at the order"))
            continue
        # THE REPLAY, validated on the shipped arm first: from the order's own start
        # and point and the tape's world-0 at the order, the resolver's rule says
        # where the copy parks and by which mechanism. Then the same rule on the
        # same geometry with the point replaced: shape 2 = the frame (world-0 at the
        # order), shape 3 = the last accepted report (retail's own direction,
        # sec.1z-cq.3: the copy lags the client and never leads it).
        pk0, m0 = park_of(rec["start"], M, w0_order)
        rec["pred_mech"], rec["pred_felt"] = m0, math.dist(pk0, body)
        pk2, m2 = park_of(rec["start"], w0_order, w0_order)
        rec["felt2"], rec["mech2"] = math.dist(pk2, body), m2
        if R is not None:
            pk3, m3 = park_of(rec["start"], R, w0_order)
            rec["felt3"], rec["mech3"], rec["R"] = math.dist(pk3, body), m3, R
        else:
            rec["felt3"], rec["mech3"], rec["R"] = float("nan"), None, None
        # shape 4: the report ONLY when the client has repeated its coordinate (the
        # last two accepted reports within 2 u -- a body the wall holds while the key
        # is down keeps reporting the same point, sec.1z-cp.3), else the model as shipped
        pinned = (i_rep >= 1 and R is not None
                  and math.dist(R, tuple(reps[i_rep - 1]["reported"])) <= 2.0)
        rec["pinned"] = pinned
        if pinned:
            rec["felt4"], rec["mech4"] = rec["felt3"], rec["mech3"]
        else:
            rec["felt4"], rec["mech4"] = rec["pred_felt"], rec["pred_mech"]
        out.append(rec)
    return out


def q(vals, f):
    if not vals:
        return float("nan")
    s = sorted(vals)
    return s[min(len(s) - 1, int(f * len(s)))]


def report(pairs, check=False):
    pooled = []
    for cap, tape in pairs:
        recs = score(cap, tape)
        name = os.path.basename(cap)[8:23]
        v = [r for r in recs if r.get("valid")]
        bad = [r for r in recs if not r.get("valid")]
        print(f"\n{name}  halts {len(recs)}  joined {len(v)}  unjoined {len(bad)}"
              f"  (join p50 {q([r['join'] for r in v], .5):.1f} u, max {q([r['join'] for r in v], 1.0):.1f})")
        print("   t       mech   mov  felt  park-w0  frame-body  order-body  order-w0  | pred  felt   shape2  shape3")
        for r in v:
            print(f"   {r['t']:6.2f}  {r['mech']:5}  {'M' if r['moving'] else 'S'}  "
                  f"{r['felt']:6.1f}  {r['park_w0']:6.1f}   {r['frame_body']:7.1f}   "
                  f"{r['order_body']:8.1f}  {r['order_w0']:8.1f}  | {r['pred_mech']:5} {r['pred_felt']:6.1f}"
                  f"  {r['felt2']:6.1f}  {r['felt3']:6.1f}"
                  f"{'  BEYOND' if r['felt'] > REACH else ''}")
        for r in v:
            r["cap"] = name
        pooled.extend(v)

    print("\nPOOLED, joined halts only")
    for mech in ("disc", "point"):
        for mov, tag in ((True, "moving"), (False, "still")):
            sel = [r for r in pooled if r["mech"] == mech and r["moving"] == mov]
            if not sel:
                continue
            felt = [r["felt"] for r in sel]
            beyond = sum(1 for r in sel if r["felt"] > REACH)
            print(f"  {mech:5} {tag:6} n={len(sel):3}  felt p50 {q(felt, .5):6.1f}  beyond reach {beyond:3}"
                  f"  park-w0 p50 {q([r['park_w0'] for r in sel], .5):6.1f}"
                  f"  frame-body p50 {q([r['frame_body'] for r in sel], .5):6.1f}"
                  f"  order-body p50 {q([r['order_body'] for r in sel], .5):6.1f}"
                  f"  order-w0 p50 {q([r['order_w0'] for r in sel], .5):6.1f}")

    # WHICH proxy tracks the felt distance, halt by halt. On DISC parks the derivation
    # says felt ~ 80 + frame-body and the order's error is irrelevant; on POINT parks
    # felt ~ order-body. Spearman-free: the mean absolute residual of each linear
    # proxy, so a reader sees the number and not a coefficient.
    def resid(sel, key, offset):
        return q([abs(r["felt"] - (r[key] + offset)) for r in sel], .5) if sel else float("nan")
    disc = [r for r in pooled if r["mech"] == "disc"]
    point = [r for r in pooled if r["mech"] == "point"]
    print("\nWHICH PROXY PREDICTS THE FELT DISTANCE (median |felt - proxy|, u):")
    print(f"  disc parks  n={len(disc)}: 80+frame-body {resid(disc, 'frame_body', STOP):5.1f}"
          f"   order-body {resid(disc, 'order_body', 0.0):5.1f}   80+order-w0 {resid(disc, 'order_w0', STOP):5.1f}")
    print(f"  point parks n={len(point)}: 80+frame-body {resid(point, 'frame_body', STOP):5.1f}"
          f"   order-body {resid(point, 'order_body', 0.0):5.1f}   80+order-w0 {resid(point, 'order_w0', STOP):5.1f}")

    beyond = [r for r in pooled if r["felt"] > REACH]
    print(f"\nHALTS BEYOND REACH ({len(beyond)} of {len(pooled)}): by mechanism "
          f"disc {sum(1 for r in beyond if r['mech'] == 'disc')} / point "
          f"{sum(1 for r in beyond if r['mech'] == 'point')}; frame-body p50 on them "
          f"{q([r['frame_body'] for r in beyond], .5):.1f} u, order-body p50 "
          f"{q([r['order_body'] for r in beyond], .5):.1f} u")
    # THE REPLAY'S VALIDATION on the shipped arm, before either counterfactual is read
    agree = sum(1 for r in pooled if r["pred_mech"] == r["mech"])
    pres = q([abs(r["pred_felt"] - r["felt"]) for r in pooled], .5)
    pres90 = q([abs(r["pred_felt"] - r["felt"]) for r in pooled], .9)
    print(f"\nTHE REPLAY ON THE SHIPPED ARM (its validation): mechanism predicted right on "
          f"{agree} of {len(pooled)}; |predicted felt - measured| p50 {pres:.1f} u, p90 {pres90:.1f}")
    f1 = [r["felt"] for r in pooled]
    # Each counterfactual is scored against the REPLAY's own shipped prediction (pred_felt),
    # never against the measured felt, so the replay's residual cannot masquerade as an
    # effect in either direction; the measured column is printed beside it.
    for key, mk, what in (("felt2", "mech2", "SHAPE 2 (order the frame = world-0)"),
                          ("felt3", "mech3", "SHAPE 3 (order the last accepted report)"),
                          ("felt4", "mech4", "SHAPE 4 (the report ONLY on a repeated coordinate)")):
        sel = [r for r in pooled if r[key] == r[key]]
        print(f"{what}, the same replay:")
        for mov, tag in ((None, "all"), (True, "moving"), (False, "still")):
            ss = [r for r in sel if mov is None or r["moving"] == mov]
            if not ss:
                continue
            f = [r[key] for r in ss]
            f0 = [r["pred_felt"] for r in ss]
            fm = [r["felt"] for r in ss]
            print(f"   {tag:6} n={len(ss):3}  felt p50 measured {q(fm, .5):6.1f} / replayed {q(f0, .5):6.1f}"
                  f" -> {q(f, .5):6.1f}; beyond reach {sum(1 for x in f0 if x > REACH):3} -> "
                  f"{sum(1 for x in f if x > REACH):3}; better {sum(1 for r in ss if r[key] < r['pred_felt'] - 0.5):3}"
                  f", worse {sum(1 for r in ss if r[key] > r['pred_felt'] + 0.5):3}; disc parks "
                  f"{sum(1 for r in ss if r[mk] == 'disc')}")
    pinned = [r for r in pooled if r.get("pinned")]
    print(f"   (shape 4's trigger, a repeated coordinate, was live at {len(pinned)} of {len(pooled)} halts; "
          f"of those, still {sum(1 for r in pinned if not r['moving'])}, beyond reach as shipped "
          f"{sum(1 for r in pinned if r['pred_felt'] > REACH)})")
    if check:
        ok = True

        def bar(c, what):
            nonlocal ok
            print(f"   [{'PASS' if c else 'FAIL'}] {what}")
            ok = ok and c
        print("\n--check")
        bar(len(pooled) >= 60, f"exposure: {len(pooled)} joined halts (>= 60)")
        bar(len(disc) >= 30, f"exposure: {len(disc)} disc parks (>= 30)")
        bar(q([r["park_w0"] for r in disc], .5) <= STOP + 15 and q([r["park_w0"] for r in disc], .5) >= STOP - 15,
            f"disc parks sit at the disc: park-w0 p50 {q([r['park_w0'] for r in disc], .5):.1f} within 80 +/- 15")
        bar(resid(disc, "frame_body", STOP) < resid(disc, "order_body", 0.0),
            "on disc parks 80+frame-body predicts felt better than order-body")
        bar(agree >= 0.75 * len(pooled), f"the replay names the mechanism on >= 75% of shipped halts ({agree})")
        bar(pres <= 25.0, f"the replay's felt residual p50 <= 25 u ({pres:.1f})")
        print("ALL BARS MET" if ok else "A BAR FAILED")
        return 0 if ok else 1
    return 0


def main(argv):
    check = "--check" in argv
    argv = [a for a in argv if a != "--check"]
    pairs = []
    if "--cap" in argv:
        cap = argv[argv.index("--cap") + 1]
        rows = W.load_gamesrv(cap)
        tape = S.find_tape(rows)
        if tape is None:
            print("no tape overlaps that capture", file=sys.stderr)
            return 2
        pairs = [(cap, tape)]
    else:
        d = vaultpath.require_dir("captures", "gamesrv")
        for cap in sorted(glob.glob(os.path.join(d, "authsrv-2026090[6-9]*-c1.jsonl"))):
            rows = W.load_gamesrv(cap)
            tape = S.find_tape(rows)
            if tape is not None and "1zcg" in os.path.basename(tape):
                pairs.append((cap, tape))
    if not pairs:
        print("no capture/tape pairs", file=sys.stderr)
        return 2
    return report(pairs, check)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
