"""KILLFAR press table: every c2s 0x0026 on the 15 tapped launches (6 GUARDW0, 8 LEADRETIRE, the
pilot), with what the server logged at it and the tap's truth on the exact application clock.

    python pt_build.py [OUT.json]  -> the table (when OUT is given) + a summary

CLOCK (c_census.py's, OBSERVED there 122/122): a send applies at clock0 = C_run + the sum of the
0x001E deltas sent before it in stream order. A press at stream index p is judged at
clock0_p = C_run + cum[p]: world-0 truth = position_at(the last sync record with updated <= clock0_p),
drawn truth = position_at(the last async record with updated <= clock0_p + d_lo), d_lo = the lower
envelope of clock1 - clock0 over the samples around the press. Positions: AgAgent::position_at,
CLAMP FIRST.

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0): `wf10-critic/pt_build.py` (byte-identical to
`wf9-table/pt_build.py`). The shared row builder behind the scorers of record `kf_sametick.py` (KILLFAR H6, 1z-ds.45),
`tp_score.py` / `tp_controls.py` (TRAILPIN, 1z-ds.48) and `c_rows.py`. Vault paths come from toolkit/vaultpath.py; the
launch rosters (LR, KF_RUNS, TP_RUNS) are static ids instead of reads of the scratchpad's run logs; main() writes its table
only to the path given as argv[1] (it wrote pt_table.json beside the script).
"""
import json
import math
import os
import struct
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/clientscan", "toolkit/authsrv", "toolkit/schema"):
    sys.path.insert(0, os.path.join(ROOT, sub))
sys.path.insert(0, HERE)

import vaultpath  # noqa: E402
GS = vaultpath.vault_path("captures", "gamesrv")
AR = vaultpath.vault_path("research", "animref")
# label, set, arm (K = the press kill, R = the retire), action note, tape stamp, tap
RUNS = [
    ("P", "pilot", "K", "pilot", "20261003T201605-c1", "agenttap-followpin-T-20261003T201522.jsonl"),
    ("gT1", "guardw0", "K", "T", "20261004T002706-c1", "agenttap-guardw0-followpin-g-T-20261004T002623.jsonl"),
    ("gF1", "guardw0", "K", "F", "20261004T003131-c1", "agenttap-guardw0-followpin-g-F-20261004T003055.jsonl"),
    ("gG1", "guardw0", "K", "G3o", "20261004T003600-c1", "agenttap-guardw0-followpin-g-G3o-20261004T003525.jsonl"),
    ("gF2", "guardw0", "K", "F", "20261004T004026-c1", "agenttap-guardw0-followpin-g-F-20261004T003951.jsonl"),
    ("gT2", "guardw0", "K", "T", "20261004T004439-c1", "agenttap-guardw0-followpin-g-T-20261004T004404.jsonl"),
    ("gG2", "guardw0", "K", "G3o", "20261004T004855-c1", "agenttap-guardw0-followpin-g-G3o-20261004T004819.jsonl"),
]
# (label, harness stamp, tap). The original filled all but T1's tap from the scratchpad's run-lr-<lab>.txt logs;
# they are static ids, resolved once from those logs on 2026-10-06 and checked against the vault by lr_runs().
LR = [("T1", "20261004T113613", "agenttap-leadretire-followpin-g-T-20261004T113611.jsonl"),
      ("R1", "20261004T114039", "agenttap-leadretire-followpin-g-R-20261004T114039.jsonl"),
      ("T2", "20261004T114459", "agenttap-leadretire-followpin-g-T-20261004T114459.jsonl"),
      ("R2", "20261004T114916", "agenttap-leadretire-followpin-g-R-20261004T114915.jsonl"),
      ("T3", "20261004T115341", "agenttap-leadretire-followpin-g-T-20261004T115341.jsonl"),
      ("R3", "20261004T115805", "agenttap-leadretire-followpin-g-R-20261004T115804.jsonl"),
      ("T4", "20261004T120230", "agenttap-leadretire-followpin-g-T-20261004T120229.jsonl"),
      ("R4", "20261004T120655", "agenttap-leadretire-followpin-g-R-20261004T120653.jsonl")]
# KILLFAR (1z-ds.45) and TRAILPIN (1z-ds.47/.48) launches: label -> (harness stamp, gamesrv stamp, agenttap).
# The scorers of record (kf_check.locate, c_fzbuild.kf_runs, tp_score.locate) read these out of the 1z-ds scratchpad's
# run-kf-<RUN>.txt / run-tp-<RUN>.txt logs (the harness dir named there, its report.json's gamesrv capture, and the
# 'tap ...' line). They are static ids: resolved once from those logs on 2026-10-06 (DEATHWALK-D0). kK*/kN* are the
# KILLFAR launches under c_fzbuild's labels (K = --press-kill-always, N = the defaults); NF is the owner's feel run.
KF_RUNS = {
    "kK1": ("20261004T152312", "20261004T152358-c1",
           "agenttap-killfar2-followpin-g-K-20261004T152309.jsonl"),
    "kN1": ("20261004T153041", "20261004T153115-c1",
           "agenttap-killfar2-followpin-g-N-20261004T153039.jsonl"),
    "kK2": ("20261004T153758", "20261004T153832-c1",
           "agenttap-killfar2-followpin-g-K-20261004T153756.jsonl"),
    "kN2": ("20261004T154515", "20261004T154550-c1",
           "agenttap-killfar2-followpin-g-N-20261004T154513.jsonl"),
    "kK3": ("20261004T155235", "20261004T155328-c1",
           "agenttap-killfar2-followpin-g-K-20261004T155232.jsonl"),
    "kN3": ("20261004T160011", "20261004T160051-c1",
           "agenttap-killfar2-followpin-g-N-20261004T160009.jsonl"),
    "kK4": ("20261004T160735", "20261004T160810-c1",
           "agenttap-killfar2-followpin-g-K-20261004T160733.jsonl"),
    "kN4": ("20261004T161453", "20261004T161526-c1",
           "agenttap-killfar2-followpin-g-N-20261004T161451.jsonl"),
    "kNF": ("20261004T164434", "20261004T164509-c1",
           "agenttap-killfarfeel-followpin-g-N-20261004T164432.jsonl"),
}

TP_RUNS = {
    "T1": ("20261004T194405", "20261004T194444-c1",
           "agenttap-trailpin-followpin-g-T-20261004T194403.jsonl"),
    "N1": ("20261004T195229", "20261004T195308-c1",
           "agenttap-trailpin-followpin-g-N-20261004T195226.jsonl"),
    "T2": ("20261004T200053", "20261004T200131-c1",
           "agenttap-trailpin-followpin-g-T-20261004T200051.jsonl"),
    "N2": ("20261004T200916", "20261004T200955-c1",
           "agenttap-trailpin-followpin-g-N-20261004T200913.jsonl"),
    "T3": ("20261004T201739", "20261004T201815-c1",
           "agenttap-trailpin-followpin-g-T-20261004T201737.jsonl"),
    "N3": ("20261004T202559", "20261004T202637-c1",
           "agenttap-trailpin-followpin-g-N-20261004T202557.jsonl"),
    "T4": ("20261004T203421", "20261004T203454-c1",
           "agenttap-trailpin-followpin-g-T-20261004T203419.jsonl"),
    "N4": ("20261004T204238", "20261004T204312-c1",
           "agenttap-trailpin-followpin-g-N-20261004T204236.jsonl"),
    "NF": ("20261004T210849", "20261004T210928-c1",
           "agenttap-trailfeel-followpin-g-N-20261004T210847.jsonl"),
}

MOVE_OPS = (0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D)
LEG_ACTS = ("arm", "regrant", "chain", "refresh", "regrant-stop", "chain-stop", "refresh-late",
            "refresh-blocked", "clear", "kill", "retire", "avoid-halt", "avoid-halt-pickup")


def lr_runs():
    taps = sorted(f for f in os.listdir(AR) if f.startswith("agenttap-leadretire-followpin-g-"))
    out = []
    for lab, hstamp, tap in LR:
        rep = json.load(open(vaultpath.vault_path("captures", "harness", hstamp, "report.json"),
                             encoding="utf-8"))
        g = [p for p in rep["captures"] if "gamesrv" in p and p.endswith(".jsonl")][0]
        stamp = os.path.basename(g)[len("authsrv-"):-len(".jsonl")]
        assert tap in taps, (lab, tap)
        out.append(("L" + lab, "leadretire", "K" if lab[0] == "T" else "R", lab[0], stamp, tap))
    return out


def fin(v):
    return isinstance(v, (int, float)) and math.isfinite(v)


def pos(b, clk):
    if b["stop"] and clk - b["stop"] >= 0 and fin(b.get("segx")):
        return (b["segx"], b["segy"])
    dt = (clk - b["updated"]) * 0.001
    return (b["x"] + b["vx"] * dt, b["y"] + b["vy"] * dt)


def d2(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def seg_dist(p, a, b):
    vx, vy = b[0] - a[0], b[1] - a[1]
    L2 = vx * vx + vy * vy
    if L2 <= 0:
        return d2(p, a)
    s = max(0.0, min(1.0, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
    return d2(p, (a[0] + s * vx, a[1] + s * vy))


def rkey(b):
    return (b["updated"], round(b["x"], 3), round(b["y"], 3), b["stop"], round(b["vx"], 3), round(b["vy"], 3))


def u32(pl, o):
    return struct.unpack_from("<I", pl, o)[0] if len(pl) >= o + 4 else None


def load_tape(stamp):
    out = []
    for l in open(os.path.join(GS, "authsrv-%s.jsonl" % stamp), encoding="utf-8", errors="replace"):
        if not l.startswith("{"):
            continue
        try:
            r = json.loads(l)
        except ValueError:
            continue
        if not isinstance(r.get("t"), (int, float)):
            continue
        r["_i"] = len(out)
        out.append(r)
    return out


def load_tap(name):
    S, head = [], None
    for l in open(os.path.join(AR, name), encoding="utf-8"):
        try:
            x = json.loads(l)
        except ValueError:
            continue
        if x.get("kind") == "head":
            head = x
        elif x.get("kind") == "sample" and "1" in (x.get("agents") or {}):
            S.append(x)
    return head, S


KEYS = ("x", "y", "vx", "vy", "updated", "stop", "segx", "segy", "tx", "ty", "movespeed")


def records(S, lo, hi, copy):
    out, seen = [], set()
    for j in range(max(0, lo), min(len(S), hi)):
        b = S[j]["agents"]["1"][copy]
        k = rkey(b)
        if k not in seen:
            seen.add(k)
            out.append(dict(j=j, **{q: b.get(q) for q in KEYS}))
    return out


def at_clock(recs, clk):
    pre = [r for r in recs if r["updated"] <= clk]
    if not pre:
        return None, None
    r = max(pre, key=lambda q: (q["updated"], q["j"]))
    return r, pos(r, clk)


def hop2(S, W, wf):
    """gw0_hop2.py's measure, verbatim logic."""
    win = [k for k in range(len(S)) if -0.4 <= W[k] - wf <= 0.7]
    best, at = 0.0, None
    for a, b in zip(win, win[1:]):
        ra, rb = S[a]["agents"]["1"]["async"], S[b]["agents"]["1"]["async"]
        if rb["updated"] == ra["updated"] or not (-0.3 <= W[b] - wf <= 0.7):
            continue
        dt = (rb["updated"] - ra["updated"]) * 0.001
        px, py = ra["x"] + ra["vx"] * dt, ra["y"] + ra["vy"] * dt
        if ra["stop"] and rb["updated"] - ra["stop"] >= 0 and fin(ra["segx"]):
            px, py = ra["segx"], ra["segy"]
        h = math.hypot(rb["x"] - px, rb["y"] - py)
        if h > best:
            best, at = h, round(W[b] - wf, 3)
    return round(best, 1), at


def run_one(run):
    label, sset, arm, note, stamp, tapname = run
    tape = load_tape(stamp)
    cum, cumb = 0, []
    for r in tape:
        cumb.append(cum)
        if r.get("kind") == "sent" and r.get("opcode") == 0x1E:
            cum += u32(bytes.fromhex(r.get("plain") or ""), 2) or 0
    ps = []                              # player position sends
    for r in tape:
        if r.get("kind") == "sent" and r.get("opcode") in MOVE_OPS:
            pl = bytes.fromhex(r.get("plain") or "")
            if u32(pl, 2) != 1:
                continue
            if r["opcode"] != 0x2B and len(pl) >= 14:
                r["xy"] = list(struct.unpack_from("<ff", pl, 6))
            ps.append(r)
    c2s = [r for r in tape if r.get("kind") == "decoded"]
    presses = [r for r in c2s if r.get("opcode") == 0x26]
    head, S = load_tap(tapname)
    t0 = head["t0"]
    W = [s["t"] + t0 for s in S]
    # C_run: the mode of (world-0 updated - cum) at follows the tap joins (c_census's join)
    cnt = Counter()
    for f in ps:
        if f["opcode"] != 0x2A or not f.get("label", "").startswith("APPROACH") or "xy" not in f:
            continue
        wf, P = f["wall_unix"], f["xy"]
        for i in range(1, len(S)):
            if W[i] < wf - 0.3:
                continue
            if W[i] > wf + 0.6:
                break
            sy = S[i]["agents"]["1"]["sync"]
            if fin(sy["tx"]) and math.hypot(sy["tx"] - P[0], sy["ty"] - P[1]) < 3.0:
                cnt[sy["updated"] - cumb[f["_i"]]] += 1
                break
    C, share = (cnt.most_common(1)[0][0], (cnt.most_common(1)[0][1], sum(cnt.values()))) if cnt else (None, (0, 0))
    rows = []
    for pi, p in enumerate(presses):
        nxt_t = presses[pi + 1]["t"] if pi + 1 < len(presses) else 1e18
        nxt_i = presses[pi + 1]["_i"] if pi + 1 < len(presses) else 1 << 60
        lo, hi = p["_i"], nxt_i
        seg = tape[lo:min(hi, len(tape))]
        win = [r for r in seg if r["t"] <= p["t"] + 0.6]
        follow = next((r for r in win if r.get("kind") == "sent" and r.get("opcode") == 0x2A
                       and r.get("label", "").startswith("APPROACH:") and "xy" in r), None)
        f_i = follow["_i"] if follow else lo + 1 + len(win)
        before_f = [r for r in win if r["_i"] < f_i]

        def first(pred):
            return next((r for r in before_f if pred(r)), None)
        kill = first(lambda r: r.get("kind") == "kbd_leg" and r.get("act") == "kill")
        kill_send = first(lambda r: r.get("kind") == "sent" and r.get("opcode") == 0x29
                          and "KBD LEAD KILLED" in r.get("label", ""))
        retire = first(lambda r: r.get("kind") == "kbd_leg" and r.get("act") == "retire")
        repin = first(lambda r: r.get("kind") == "sent" and r.get("opcode") == 0x2C)
        pstop = first(lambda r: r.get("kind") == "press_stop")
        pverd = next((r for r in win if r.get("kind") == "press_verdict"), None)
        appr = None
        if follow is not None:
            appr = next((r for r in reversed(before_f) if r.get("kind") == "approach" and r.get("act") == "send"), None)
        late = next((r for r in seg if r.get("kind") == "sent" and r.get("opcode") == 0x29
                     and "(late" in r.get("label", "")), None)
        # the client's state before the press
        prev = [x for x in c2s if x["_i"] < p["_i"]]
        last_mv = next((x for x in reversed(prev) if x.get("opcode") in (0x3D, 0x47, 0x3E)), None)
        last_rep = next((x for x in reversed(prev) if x.get("opcode") == 0x3D), None)
        lastv = (last_mv or {}).get("values") or []
        mt = lastv[4] if last_mv is not None and last_mv.get("opcode") == 0x3D and len(lastv) > 4 else None
        # the keyboard lead in force: its rows since the last arm, if no clear/kill/retire since
        legrows = [r for r in tape[max(0, lo - 4000):lo] if r.get("kind") == "kbd_leg"]
        chain = []
        for r in reversed(legrows):
            chain.append(r)
            if r.get("act") in ("arm", "clear", "kill", "retire"):
                break
        chain.reverse()
        leg_live = bool(chain) and chain[0].get("act") == "arm"
        last_ps = next((r for r in reversed(ps) if r["_i"] < lo), None)
        row = dict(run=label, set=sset, arm=arm, note=note, stamp=stamp, tap=tapname,
                   p_i=lo, p_t=round(p["t"], 4), p_wall=p.get("wall_unix"),
                   target=(p.get("values") or [None, None])[1],
                   mt=mt, last_mv_op=None if last_mv is None else last_mv["opcode"],
                   last_mv_t=None if last_mv is None else round(last_mv["t"], 4),
                   rep_age=None if last_rep is None else round(p["t"] - last_rep["t"], 4),
                   rep_values=None if last_rep is None else last_rep.get("values"),
                   leg_live=leg_live,
                   leg_rows=[{k: v for k, v in r.items() if k not in ("wall", "_i")} | {"_i": r["_i"]} for r in chain],
                   last_pos_send=None if last_ps is None else dict(i=last_ps["_i"], t=round(last_ps["t"], 4),
                                                                   op=last_ps["opcode"], xy=last_ps.get("xy"),
                                                                   label=last_ps.get("label", "")[:90]),
                   follow=None if follow is None else dict(i=follow["_i"], t=round(follow["t"], 4), P=follow["xy"],
                                                           gap=round(follow["t"] - p["t"], 4)),
                   kill=None if kill is None else {k: kill.get(k) for k in ("matured", "point", "remaining", "age", "dest", "t")},
                   kill_xy=None if kill_send is None else kill_send["xy"],
                   kill_i=None if kill_send is None else kill_send["_i"],
                   retire=None if retire is None else {k: retire.get(k) for k in ("point", "remaining", "age", "dest", "t")},
                   late_kill=None if late is None else dict(t=round(late["t"], 4), xy=late.get("xy")),
                   repin=None if repin is None else dict(t=round(repin["t"], 4), xy=repin.get("xy"),
                                                         label=repin.get("label", "")[:80]),
                   press_stop=None if pstop is None else {k: v for k, v in pstop.items() if k not in ("wall", "_i", "wall_unix")},
                   press_verdict=None if pverd is None else {k: pverd.get(k) for k in ("fired", "reason", "refused_by", "dist")},
                   guard=None if appr is None else appr.get("guard"),
                   appr=None if appr is None else {k: appr.get(k) for k in ("origin", "frame_origin", "to", "dist_frame",
                                                                             "dist_model", "dist_report", "report_age",
                                                                             "frame_vs_model")},
                   C_run=C, cum_p=cumb[lo])
        # tap truth at the press, exact clock
        if C is not None:
            ip = next((k for k in range(len(S)) if W[k] >= p["wall_unix"]), len(S) - 1)
            srecs = records(S, ip - 25, ip + 25, "sync")
            arecs = records(S, ip - 25, ip + 25, "async")
            dd = [S[j]["clock1"] - S[j]["clock0"] for j in range(max(0, ip - 15), min(len(S), ip + 16))]
            dl = min(dd) if dd else None
            c0 = C + cumb[lo]
            r0, w0 = at_clock(srecs, c0)
            r1, dr = at_clock(arecs, c0 + dl) if dl is not None else (None, None)
            row.update(clock0_p=c0, d_lo=dl,
                       w0_true=None if w0 is None else [round(w0[0], 2), round(w0[1], 2)],
                       w0_rec=None if r0 is None else {k: r0[k] for k in ("x", "y", "vx", "vy", "updated", "stop", "tx", "ty", "movespeed")},
                       drawn_true=None if dr is None else [round(dr[0], 2), round(dr[1], 2)],
                       d_true=None if (w0 is None or dr is None) else round(d2(w0, dr), 2))
            # the last-sample version (lr_class.py's operand)
            pre = [k for k in range(len(S)) if W[k] <= p["wall_unix"]]
            if pre:
                s = S[pre[-1]]
                a0 = pos(s["agents"]["1"]["sync"], s["clock0"])
                a1 = pos(s["agents"]["1"]["async"], s["clock1"])
                row.update(d_last=round(d2(a0, a1), 2), last_lag=round(p["wall_unix"] - W[pre[-1]], 4))
            # the kill: static and behind (c_census.derive's definitions)
            if kill_send is not None and follow is not None:
                tz = C + cumb[kill_send["_i"]]
                tf = C + cumb[follow["_i"]]
                K, P = kill_send["xy"], follow["xy"]
                lp = next((r for r in reversed(ps) if r["_i"] < kill_send["_i"] and r["opcode"] in (0x28, 0x29, 0x2A, 0x2C, 0x2D)), None)
                prerecs = [s for s in srecs if s["updated"] < tz]
                if prerecs:
                    pr = max(prerecs, key=lambda q: (q["updated"], q["j"]))
                    X = pos(pr, tz)
                    row["XK"] = round(d2(X, K), 2)
                    row["static"] = row["XK"] <= 1.0
                    row["pre_ok"] = bool(lp is not None and pr["updated"] == C + cumb[lp["_i"]])
                    ux, uy = P[0] - K[0], P[1] - K[1]
                    n = math.hypot(ux, uy) or 1.0
                    Af = [a for a in arecs if a["updated"] <= tf + dl]
                    if Af:
                        Df = pos(max(Af, key=lambda q: (q["updated"], q["j"])), tf + dl)
                        row["proj_f"] = round(((Df[0] - K[0]) * ux + (Df[1] - K[1]) * uy) / n, 2)
                        row["behind"] = row["proj_f"] < 0
            # the follow: hop + where world-0 and drawn stand at its application
            if follow is not None:
                row["hop"], row["hop_at"] = hop2(S, W, follow["wall_unix"])
                tf = C + cumb[follow["_i"]]
                _, w0f = at_clock(srecs, tf)
                _, drf = at_clock(arecs, tf + dl) if dl is not None else (None, None)
                if w0f is not None and drf is not None:
                    row["sep_f"] = round(d2(w0f, drf), 2)
                    row["segdist_f"] = round(seg_dist(drf, w0f, follow["xy"]), 2)
        rows.append(row)
    return rows, dict(label=label, C=C, share=share, presses=len(presses))


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else None      # the table is written only where told
    allrows, metas = [], []
    for run in RUNS + lr_runs():
        rows, meta = run_one(run)
        metas.append(meta)
        allrows += rows
        print("== %-4s C_run %s (%d/%d)  presses %d  follow-answered %d  kill %d  retire %d  d_true %d" % (
            meta["label"], meta["C"], meta["share"][0], meta["share"][1], meta["presses"],
            sum(1 for r in rows if r["follow"]), sum(1 for r in rows if r["kill_xy"]),
            sum(1 for r in rows if r["retire"]), sum(1 for r in rows if r.get("d_true") is not None)))
    if out:
        json.dump(dict(runs=metas, rows=allrows), open(out, "w"), indent=0, default=str)
    dom = [r for r in allrows if r["follow"] and not r["repin"] and r["mt"] not in (None, 0)]
    print("\nunpinned follow-answered key-walk presses: %d" % len(dom))
    for arm in ("K", "R"):
        a = [r for r in dom if r["arm"] == arm]
        print(" arm %s: n %d, hops>30 %d" % (arm, len(a), sum(1 for r in a if (r.get("hop") or 0) > 30)))
        for lo_, hi_ in ((0, 10), (10, 20), (20, 25), (25, 1e9)):
            for key in ("d_true", "d_last"):
                b = [r for r in a if r.get(key) is not None and lo_ <= r[key] < hi_]
                print("   %-6s [%g,%g): n %d hops %d" % (key, lo_, hi_, len(b), sum(1 for r in b if (r.get("hop") or 0) > 30)))


if __name__ == "__main__":
    main()
