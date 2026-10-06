"""COMPOSING CRITIC (wf10): one row per domain press of the 24 tapped launches, with every operand the
three lanes' candidate triggers read, the tap's truth at the follow's handover, and a PROOF label on the hop.

    python c_rows.py FZ_TABLE.json OUT.json  -> OUT.json + a printed summary

Built on c_fzbuild.py's fz_table.json (byte-identical to wf10-table's, re-derived from this folder's pin).
Per row (domain = unpinned, follow-answered, key-walk), on the client clock (C_run + replica clock):
  K      f32(kill point)                      X   world-0 at the kill's application (replica)
  w0f    world-0 at the follow's application  P   the follow's target (f32)
  Kseg   dist(K, segment [w0f, P])            -- FZ-trail's K term (the drawn copy at K, case a)
  mseg   dist(guard model, [w0f, P])          -- FZ-trail's model term (the walked-on copy, case b)
  op, along_rep  |f32(B) - w0| at the press and (B - w0) . unit(P - B)  -- FZ-retail's better-fix flag
  PROOF  of the max gated pair: excess over the 288 u/s bound from the last sample that SHOWED the
         earlier record (> 0 = proven), and the BY-TIME signature (the record on the tap's world-0 path at
         its own stamp within 2 u, world-0 moving, stops equal) -- FZ-short's gate, re-implemented here.
  handover  the first drawn record at/after the follow's drawn application: its form (bytime / atK /
         other), its distance from [w0f, P] u [X, w0f] (h_obs), and whether it was re-aimed toward P or w0f.
  Df     the drawn copy at the follow's drawn application from the newest record stamped at/before it,
         and whether that record is FRESH (stamped after the kill's drawn application) or STALE.
Counterfactual (RECONSTRUCTION): an R-arm retire with op > 2 is a far kill under today's code; its w0f
  is simulated as X walked toward K at 288 x moveSpeed for the tick, and its Kseg read from that.

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0): `wf10-critic/c_rows.py`. `tp_score.py` imports its replay,
recs_of, proof, w0_at, seg and d (the pinned w0replica + codec are the repo's own, byte-identical at 99a9cf51). Its own main()
needs c_fzbuild.py's cached fz_table.json, which is NOT ported (c_fzbuild.py reads the scratchpad's run-kf logs and a pinned
tree; nothing in D0 needs it); main() is kept for the record and is unrun.
"""
import bisect
import json
import math
import os
import sys
from collections import defaultdict

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/clientscan", "toolkit/authsrv", "toolkit/schema"):
    sys.path.insert(0, os.path.join(ROOT, sub))
sys.path.insert(0, HERE)
import pt_build as PB  # noqa: E402
import w0replica as W  # noqa: E402   (the scratchpad's pinned copy is byte-identical to toolkit/authsrv/w0replica.py at 99a9cf51)
import codec  # noqa: E402            (likewise toolkit/schema/codec.py)
assert os.path.abspath(W.__file__).startswith(os.path.join(ROOT, "toolkit")), W.__file__
assert os.path.abspath(codec.__file__).startswith(os.path.join(ROOT, "toolkit")), codec.__file__
assert os.path.dirname(os.path.abspath(PB.__file__)) == HERE, PB.__file__

CD = codec.Codec(os.path.join(ROOT, "schema", "messages.json"))
# fz_table.json (c_fzbuild.py's cached table) is read only by main(): see load_fz_table(). tp_score does not need it.
T = None
CM = {}


def load_fz_table(path):
    global T, CM
    T = json.load(open(path))
    CM = {m["run"]: m["C"] for m in T["runs"]}
VMAX = 288.0


def d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def seg_near(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy
    if L2 <= 0:
        return a
    s = max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
    return (a[0] + s * vx, a[1] + s * vy)


def seg(p, a, b):
    return d(p, seg_near(p, a, b))


def replay(tape):
    rep = W.W0Replica(1)
    before, after, ms, idx, snaps = {}, {}, {}, [], []
    for r in tape:
        if r.get("kind") == "sent" and r.get("opcode") in W.OPS and r.get("plain"):
            try:
                op, v, _o = CD.decode_one("GAME_SMSG", bytes.fromhex(r["plain"]))
            except Exception:  # noqa: BLE001
                continue
            before[r["_i"]] = rep.snap
            ms[r["_i"]] = rep.sync.move_speed
            rep.apply(op, v[1:])
            after[r["_i"]] = rep.snap
            idx.append(r["_i"])
            snaps.append((rep.snap, rep.sync.move_speed))
    return before, after, ms, idx, snaps


def recs_of(S, copy):
    clk = "clock1" if copy == "async" else "clock0"
    last, last_seen = {}, {}
    for s in S:
        b = s["agents"]["1"][copy]
        k = (b["updated"], round(b["x"], 3), round(b["y"], 3))
        last[k] = b
        last_seen[k] = s[clk]
    ks = sorted(last, key=lambda k: k[0])
    return [dict(last[k], t_seen=last_seen[k]) for k in ks]


def w0_at(srecs, t):
    pre = [r for r in srecs if r["updated"] <= t]
    if not pre:
        return None, None
    r = max(pre, key=lambda q: q["updated"])
    return r, PB.pos(r, t)


def proof(a, b, srecs):
    tb = b["updated"]
    ts = max(a["t_seen"], a["updated"])
    dt = (tb - a["updated"]) * 0.001
    px, py = a["x"] + a["vx"] * dt, a["y"] + a["vy"] * dt
    if a["stop"] and tb - a["stop"] >= 0 and PB.fin(a.get("segx")):
        px, py = a["segx"], a["segy"]
    hop = math.hypot(b["x"] - px, b["y"] - py)
    pa = PB.pos(a, ts)
    excess = math.hypot(b["x"] - pa[0], b["y"] - pa[1]) - VMAX * max(0, tb - ts) * 0.001 - 1.0
    wr, wp = w0_at(srecs, tb)
    bt = None if wp is None else math.hypot(b["x"] - wp[0], b["y"] - wp[1])
    moving = wr is not None and math.hypot(wr["vx"], wr["vy"]) > 1.0 and not (wr["stop"] and tb >= wr["stop"])
    sig = bool(bt is not None and bt < 2.0 and moving and wr["stop"] == b["stop"] and b["stop"] != 0)
    return dict(hop=round(hop, 1), t_b=tb, unseen=tb - ts, excess=round(excess, 1),
                bytime=None if bt is None else round(bt, 2), sig=sig, proven=bool(excess > 0 or sig))


def main(fz_path=None, out_path=None):
    if fz_path:
        load_fz_table(fz_path)
    assert T is not None and out_path, "c_rows.main() needs c_fzbuild's fz_table.json and an output path: python c_rows.py FZ_TABLE.json OUT.json"
    rows = [x for x in T["rows"] if not x["repin"] and x["mt"] not in (None, 0)]
    by = defaultdict(list)
    for x in rows:
        by[(x["run"], x["stamp"], x["tap"])].append(x)
    out = []
    for (run, stamp, tapname), xs in by.items():
        C = CM[run]
        tape = PB.load_tape(stamp)
        tmap = {r["_i"]: r for r in tape}
        before, after, ms, idx, snaps = replay(tape)
        head, S = PB.load_tap(tapname)
        arecs = recs_of(S, "async")
        srecs = recs_of(S, "sync")
        for x in xs:
            dl = x.get("d_lo")
            if C is None or dl is None:
                continue
            fi = x["follow"]["i"]
            sb = before.get(fi)
            if sb is None:
                continue
            tf = sb[W.S_CLOCK]
            w0f = W.position_at(sb)
            P = (W.f32(x["follow"]["P"][0]), W.f32(x["follow"]["P"][1]))
            vf = (after[fi][W.S_VX], after[fi][W.S_VY])
            # the replica at the press (the clock the press's kill applies at)
            k = bisect.bisect_left(idx, x["p_i"]) - 1
            snp, msp = (snaps[k] if k >= 0 else (None, None))
            row = dict(run=run, arm=x["arm"], p_t=x["p_t"], act=x["act"], mt=x["mt"], op=x["op"],
                       d_true=x.get("d_true"), along=x.get("off_along"), hop_g=x.get("hop_g"),
                       hop_g_dt=x.get("hop_g_dt"), rep_err=x.get("rep_err"), fdist=x.get("follow_dist"),
                       gap_pf=x["follow"]["gap"], tf=C + tf, w0f=[round(w0f[0], 2), round(w0f[1], 2)],
                       P=[round(P[0], 2), round(P[1], 2)], dl=dl, guard=x.get("guard"),
                       dist_frame=(x.get("appr") or {}).get("dist_frame"))
            B = x.get("B")
            if B is not None and x.get("rep_w0") is not None:
                u = (P[0] - B[0], P[1] - B[1])
                n = math.hypot(*u) or 1.0
                row["along_rep"] = round(((B[0] - x["rep_w0"][0]) * u[0] + (B[1] - x["rep_w0"][1]) * u[1]) / n, 2)
            model = (x.get("guard") or {}).get("model")
            K = None
            tk = None
            if x["act"] == "kill" and x.get("kill_i") is not None and x["kill_i"] in before:
                ki = x["kill_i"]
                X = W.position_at(before[ki])
                K = (W.f32(x["kill_xy"][0]), W.f32(x["kill_xy"][1]))
                tk = before[ki][W.S_CLOCK]
                vk = math.hypot(after[ki][W.S_VX], after[ki][W.S_VY])
                row.update(X=[round(X[0], 2), round(X[1], 2)], K=[round(K[0], 2), round(K[1], 2)],
                           dt_kf=tf - tk, v_k=round(vk, 1), XK=round(d(X, K), 2),
                           Kpt=round(d(K, w0f), 2), Kseg=round(seg(K, w0f, P), 2),
                           gap_kf=round(tmap[fi]["t"] - tmap[ki]["t"], 4))
            elif x["act"] == "retire" and B is not None and snp is not None and (x["op"] or 0) > 2.0:
                # COUNTERFACTUAL: today's code kills this press (op > 2); simulate the kill's tick
                X = W.position_at(snp)
                K = (W.f32(B[0]), W.f32(B[1]))
                tk = snp[W.S_CLOCK]
                vk = 288.0 * (msp or 1.0)
                L = d(X, K)
                step = min(L, vk * (tf - tk) * 0.001)
                w0s = X if L <= 0 else (X[0] + (K[0] - X[0]) / L * step, X[1] + (K[1] - X[1]) / L * step)
                row.update(cf=True, X=[round(X[0], 2), round(X[1], 2)], K=[round(K[0], 2), round(K[1], 2)],
                           dt_kf=tf - tk, v_k=round(vk, 1), XK=round(L, 2),
                           Kseg=round(seg(K, w0s, P), 2), Kpt=round(d(K, w0s), 2))
            if model is not None:
                row["mseg"] = round(seg((float(model[0]), float(model[1])), w0f, P), 2)
            # the drawn copy at the follow's drawn application
            fz = C + tf + dl
            pre = [b for b in arecs if b["updated"] <= fz]
            if pre:
                r0 = max(pre, key=lambda q: q["updated"])
                Df = PB.pos(r0, fz)
                row["Df"] = [round(Df[0], 2), round(Df[1], 2)]
                row["Df_fresh"] = bool(tk is not None and r0["updated"] >= C + tk + dl - 5)
                row["Df_age"] = fz - r0["updated"]
                if K is not None:
                    row["Df_K"] = round(d(Df, K), 2)
            if K is not None and tk is not None:
                lo, hi = C + tk + dl - 5, C + tf + dl - 5
                row["pre"] = [dict(upd=b["updated"], to_K=round(d((b["x"], b["y"]), K), 2),
                                   v=round(math.hypot(b["vx"], b["vy"]), 1),
                                   seg_is_K=bool(PB.fin(b.get("segx")) and d((b["segx"], b["segy"]), K) < 1.0))
                              for b in arecs if lo <= b["updated"] < hi]
            first = next((b for b in arecs if b["updated"] >= fz - 5), None)
            if first is not None:
                pt = (first["x"], first["y"])
                path = (w0f[0] + vf[0] * (first["updated"] - (C + tf)) * 0.001,
                        w0f[1] + vf[1] * (first["updated"] - (C + tf)) * 0.001)
                Xp = row.get("X")
                hh = seg(pt, w0f, P) if Xp is None else min(seg(pt, w0f, P), seg(pt, Xp, w0f))
                aim = None
                if PB.fin(first.get("segx")):
                    sg = (first["segx"], first["segy"])
                    aim = "P" if d(sg, P) < 3 else ("w0f" if d(sg, w0f) < 3 else "other")
                row["first"] = dict(dt=first["updated"] - fz, to_path=round(d(pt, path), 2),
                                    to_K=None if K is None else round(d(pt, K), 2), h_obs=round(hh, 2),
                                    form=("bytime" if d(pt, path) < 1.5 else
                                          ("atK" if (K is not None and d(pt, K) < 2.0) else "other")),
                                    aim=aim, v=round(math.hypot(first["vx"], first["vy"]), 1))
            # proof of the gated pairs
            lo = x["clock0_p"] + dl - 5 if x.get("clock0_p") is not None else None   # clock0_p = C + cum
            hi = fz + 700
            pairs = []
            for a, b in zip(arecs, arecs[1:]):
                if b["updated"] == a["updated"] or lo is None or not (lo <= b["updated"] <= hi):
                    continue
                pairs.append(proof(a, b, srecs))
            if pairs:
                mx = max(pairs, key=lambda c: c["hop"])
                pr = [c for c in pairs if c["proven"]]
                row["pmax"] = mx
                row["hop_proven"] = max((c["hop"] for c in pr), default=0.0)
                row["hop_proven_dt"] = None if not pr else max(pr, key=lambda c: c["hop"])["t_b"] - fz
            out.append(row)
        print(f"== {run} rows {len(xs)}", flush=True)
    json.dump(out, open(out_path, "w"), indent=0, default=str)
    return out


if __name__ == "__main__":
    main(*sys.argv[1:3])
