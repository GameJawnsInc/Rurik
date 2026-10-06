"""TRAILPIN scorer (MOVECODE-1z-ds.47): the registered floors, aborts and H1-H7 (TRAILPIN-run-registered.txt).

    python tp_score.py T1 N1 T2 N2 ...    the run's launches (pt_build.TP_RUNS: T1-T4, N1-N4, NF)
        --logs DIR     read each launch's verdict / assert count from DIR/run-tp-<RUN>.txt (else report.json)
        --json PATH    write the scored rows to PATH (nothing is written otherwise)
        LABEL=HARNESS_STAMP,GAMESRV_STAMP,TAP   score a launch not in TP_RUNS
    python tp_score.py --check N1         the between-launch ABORTS only, for one launch (exit 1 on an abort)
    python tp_score.py --selftest         the 12 KILLFAR/LEADRETIRE kill-arm launches as T stand-ins (no
                                          guard.trail on those tapes: the offline K term is scored instead)

Domain: follow-answered key-walk presses (mt not 0) whose press->follow window holds no LEGACY 0x002C (a 'rule
trail' re-pin is IN the domain: it is the treatment). The K term is recomputed offline from our own sends through
the pinned w0replica, at the snapshot just before the follow's first player position send of that tick (the trail
0x002C when there is one), and compared with the logged guard.trail.
THE HOP has two columns: hop_g = gw0_hop2's last-seen measure over 30 u, GATED to drawn records stamped in
[C + cum_press + d_lo - 5, C + cum_follow + d_lo + 700] (kf_score.hop_gated's window); hop_p = the same pairs kept
only when PROVEN (the record past the 288 u/s bound from the last sample that showed its predecessor, or the
BY-TIME signature: on the tap's world-0 path at its own stamp within 2 u, world-0 moving, stops equal). The
follow-HANDOVER hop is a proven pair stamped -5..+50 ms around the follow's drawn application. Registered checks
read hop_p; hop_g is printed beside it.

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); scorer of record for TRAILPIN's H1-H7 table,
published as FINDINGS 1z-ds.48 (`python studies/movecode/review/tp_score.py T1 N1 T2 N2 T3 N3 T4 N4`). The 'same-tick
swings on follow re-paths 0-6 per launch (T 7, N 10)' control in that section is NOT this file's: it is `tp_controls.py`.
"""
import bisect
import json
import math
import os
import re
import struct
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, HERE)
import c_rows as CR  # noqa: E402   (the repo's w0replica + codec, the proof, the replay; paths asserted there)
PB, W = CR.PB, CR.W
vaultpath = PB.vaultpath

SELF = [("LT1", "K"), ("LT2", "K"), ("LT3", "K"), ("LT4", "K"), ("kK1", "K"), ("kN1", "N"), ("kK2", "K"),
        ("kN2", "N"), ("kK3", "K"), ("kN3", "N"), ("kK4", "K"), ("kN4", "N")]


LOGS = None        # --logs DIR: the run logs (run-tp-<RUN>.txt) the verdict and assert counts were read from
JSON_OUT = None    # --json PATH: where to write the rows (the original wrote tp_score.json / tp_selftest.json beside the script)


def locate(run):
    """(tap, stamp, verdict lines, assert count) for a TRAILPIN launch.

    The tap, the gamesrv stamp and the harness dir come from pt_build.TP_RUNS (the original read them out of the
    scratchpad's run-tp-<RUN>.txt). The verdict lines and the assert count come from that run log when --logs DIR has
    it, else from the harness report.json (verdict text from `passed`; asserts = gw_log lines matching the same
    pattern, plus a crash-dialog.txt) -- the aborts() verdict clause is then read from a different source, and says so.
    """
    hstamp, stamp, tap = PB.TP_RUNS[run]
    lp = os.path.join(LOGS, f"run-tp-{run}.txt") if LOGS else None
    if lp and os.path.exists(lp):
        log = open(lp, encoding="utf-8", errors="replace").read().replace("\x00", "")
        return tap, stamp, re.findall(r"RUN VERDICT[^\n]*", log), len(re.findall(r"(?i)assertion|crash dump|Code=0", log))
    hd = vaultpath.vault_path("captures", "harness", hstamp)
    rep = json.load(open(os.path.join(hd, "report.json"), encoding="utf-8"))
    n = sum(1 for x in (rep.get("gw_log") or []) if re.search(r"(?i)assertion|crash dump|Code=0", x))
    n += int(os.path.exists(os.path.join(hd, "crash-dialog.txt")))
    return tap, stamp, [f"RUN VERDICT: {'PASS' if rep.get('passed') else 'FAIL'}  (report.json passed={rep.get('passed')}; no run log)"], n


def self_locate(run):
    """The 12 KILLFAR/LEADRETIRE kill-arm launches as T stand-ins: (tap, stamp) from the pt_build rosters."""
    if run in PB.KF_RUNS:
        _h, st, tap = PB.KF_RUNS[run]
    else:
        x = next(r for r in PB.lr_runs() if r[0] == run)
        st, tap = x[4], x[5]
    return tap, st, ["RUN VERDICT PASS (selftest)"], 0


def score_run(run, arm, loc):
    tap, stamp, verdict, asserts = loc
    rows, meta = PB.run_one((run, "trailpin", arm, arm, stamp, tap))
    C = meta["C"]
    tape = PB.load_tape(stamp)
    tmap = {r["_i"]: r for r in tape}
    before, after, _ms, idxs, snaps = CR.replay(tape)
    head, S = PB.load_tap(tap)
    arecs, srecs = CR.recs_of(S, "async"), CR.recs_of(S, "sync")
    gaps = sorted(b["t"] - a["t"] for a, b in zip(S, S[1:]))
    out = []
    prev_t, idx = None, 0
    for x in sorted((r for r in rows if r["follow"]), key=lambda r: r["p_t"]):
        idx = idx + 1 if (prev_t is not None and 1.8 <= x["p_t"] - prev_t <= 3.0) else 1
        prev_t = x["p_t"]
        if x["mt"] in (None, 0) or C is None or x.get("d_lo") is None:
            continue
        fi = x["follow"]["i"]
        win = [tmap[i] for i in range(x["p_i"], fi + 1) if i in tmap]
        pins = [r for r in win if r.get("kind") == "sent" and r.get("opcode") == 0x2C
                and PB.u32(bytes.fromhex(r.get("plain") or ""), 2) == 1]
        trail = [r for r in pins if "rule trail" in r.get("label", "")]
        legacy = [r for r in pins if r not in trail]
        if legacy:
            continue                                   # outside the domain, as in every earlier census
        g = x.get("guard") or {}
        # the action and the press-time operand (fz_build's): the replica just before the press's first send
        act = "kill" if x.get("kill_xy") else ("retire" if x.get("retire") else
                                               ("matured" if (x.get("kill") or {}).get("matured") else "none"))
        kp = bisect.bisect_left(idxs, x["p_i"]) - 1
        wp = W.position_at(snaps[kp][0]) if kp >= 0 and snaps[kp][0] is not None else None
        Bp = (x.get("kill") or x.get("retire") or {}).get("point")
        op = None if (wp is None or Bp is None) else math.hypot(W.f32(Bp[0]) - wp[0], W.f32(Bp[1]) - wp[1])
        si = trail[0]["_i"] if trail else fi           # the reading's snapshot: before the tick's first position send
        sb = before.get(si)
        if sb is None:
            continue
        tf = sb[W.S_CLOCK]
        w0f = W.position_at(sb)
        P = (W.f32(x["follow"]["P"][0]), W.f32(x["follow"]["P"][1]))
        K = None if not x.get("kill_xy") else (W.f32(x["kill_xy"][0]), W.f32(x["kill_xy"][1]))
        kseg = None if K is None else CR.seg(K, w0f, P)
        dl = x["d_lo"]
        fz = C + before[fi][W.S_CLOCK] + dl
        lo, hi = x["clock0_p"] + dl - 5, fz + 700
        pairs = [CR.proof(a, b, srecs) for a, b in zip(arecs, arecs[1:])
                 if b["updated"] != a["updated"] and lo <= b["updated"] <= hi]
        hop_g = max((p["hop"] for p in pairs), default=0.0)
        pr = [p for p in pairs if p["proven"] and p["hop"] > 30]
        hand = [p for p in pr if -5 <= p["t_b"] - fz <= 50]
        # the replica against the tap's world-0 at the reading's clock -- EXCLUDING the trail re-pin's own record
        # (it applies at that same clock: m_point = the pin, v = 0). AMENDED after N2: read with it, every re-pinned
        # row's rep_err equalled its K term and the row was scored as the avoidance blind spot.
        _srecs = srecs
        if trail:
            _pin = struct.unpack_from("<ff", bytes.fromhex(trail[0]["plain"]), 6)
            _srecs = [q for q in srecs if not (q["updated"] == C + tf and CR.d((q["x"], q["y"]), _pin) < 0.5)]
        _r, w0t = CR.w0_at(_srecs, C + tf)
        rep_err = None if w0t is None else CR.d(w0t, w0f)
        nudge = None
        if trail:
            pin = struct.unpack_from("<ff", bytes.fromhex(trail[0]["plain"]), 6)   # agent u32 at 2, x y at 6
            pc = C + tf + dl
            pre = [b for b in arecs if b["updated"] <= pc]
            if pre:
                r0 = max(pre, key=lambda q: q["updated"])
                at_rest = math.hypot(r0["vx"], r0["vy"]) < 1.0
                age = pc - max(r0["t_seen"], r0["updated"])
                nudge = dict(d=round(CR.d(PB.pos(r0, pc), pin), 2), age=age, resolved=bool(at_rest or age <= 60),
                             pin_K=None if K is None else round(CR.d(pin, K), 3))
                # the pin's OWN drawn record (both copies land on the point): the gated displacement INTO it,
                # with its proof -- the visible nudge as the tap can resolve it (an in-place re-aim of the
                # record before it, which keeps its stamp, makes the extrapolated `d` above an upper estimate)
                nxt = next((b for b in arecs if b["updated"] >= pc - 5 and CR.d((b["x"], b["y"]), pin) < 1.0), None)
                if nxt is not None:
                    k = arecs.index(nxt)
                    pp = CR.proof(arecs[k - 1], nxt, srecs) if k > 0 else None
                    nudge.update(rec_dt=nxt["updated"] - pc, into=None if pp is None else pp["hop"],
                                 into_proven=None if pp is None else pp["proven"],
                                 into_unseen=None if pp is None else pp["unseen"])
        out.append(dict(run=run, arm=arm, p_t=x["p_t"], idx=idx, act=act, mt=x["mt"], op=op,
                        kseg=None if kseg is None else round(kseg, 2), logged=g.get("trail"), rule=g.get("rule"),
                        trail_pin=bool(trail), trail_label=(trail[0].get("label", "")[:60] if trail else None),
                        rep_err=None if rep_err is None else round(rep_err, 2), hop_g=hop_g,
                        hop_p=max((p["hop"] for p in pr), default=0.0), hand=bool(hand), nudge=nudge,
                        jump100=any(p["hop"] > 100 for p in pairs)))
    meta2 = dict(run=run, arm=arm, stamp=stamp, verdict=verdict[-1:] or None, asserts=asserts, C=C,
                 tap_gap_p50=round(gaps[len(gaps) // 2], 3) if gaps else None)
    return out, meta2


def aborts(rows, meta):
    bad = []
    if not meta["verdict"] or "PASS" not in meta["verdict"][-1]:
        bad.append(f"verdict {meta['verdict']}")
    if meta["asserts"]:
        bad.append(f"{meta['asserts']} assert/crash lines")
    for r in rows:
        if r["arm"] == "T" and r["trail_pin"]:
            bad.append(f"T trail re-pin at {r['p_t']}")
        if r["arm"] == "N" and r["trail_pin"] and (r["logged"] is None or r["logged"] <= 19.0):
            bad.append(f"N trail re-pin with guard.trail {r['logged']} at {r['p_t']}")
        if r["arm"] == "N" and r["trail_pin"] and r["hop_p"] > 30:
            bad.append(f"N PROVEN hop {r['hop_p']} after a trail re-pin at {r['p_t']} (H4 falsified: STOP)")
        if r["arm"] == "N" and r["nudge"] and r["nudge"]["resolved"] and r["nudge"]["d"] > 30:
            bad.append(f"N trail re-pin {r['nudge']['d']} u from the tap's drawn copy at {r['p_t']}")
        if r["arm"] == "N" and r["jump100"]:
            bad.append(f"N drawn jump > 100 u at {r['p_t']}")
    return bad


def report(rows, metas):
    def far(r):
        return r["act"] == "kill" and (r["op"] or 0) > 2.0 and r["kseg"] is not None
    for m in metas:
        print("  ", m)
    for arm in ("T", "N"):
        a = [r for r in rows if r["arm"] == arm]
        f = [r for r in a if far(r)]
        if not a:
            continue
        blind = [r for r in f if (r["rep_err"] or 0) > 5.0]      # the replica's avoidance blind spot
        f = [r for r in f if r not in blind]
        tc = [r for r in f if (r["logged"] if r["logged"] is not None else r["kseg"]) > 19.0]
        tc25 = [r for r in f if (r["logged"] if r["logged"] is not None else r["kseg"]) > 25.0]
        print(f"\n== arm {arm}: domain {len(a)}  far kills {len(f)} (+{len(blind)} blind)  trailing class (> 19 u) "
              f"{len(tc)}  (> 25 u) {len(tc25)}")
        print(f"   blind-spot far kills (replica > 5 u off the tap), scored apart: "
              f"{[(r['run'], r['p_t'], r['rep_err'], r['kseg'], r['trail_pin'], r['hop_p']) for r in blind]}")
        print(f"   FLOORS: far kills >= 40 {len(f) >= 40}; trailing class >= 3 {len(tc) >= 3}")
        lg = [r for r in f + blind if r["logged"] is not None]
        print(f"   H2 the reading: logged {len(lg)}; |logged - offline| <= 0.1 u on "
              f"{sum(1 for r in lg if abs(r['logged'] - r['kseg']) <= 0.1)}; replica vs tap world-0 <= 1 u on "
              f"{sum(1 for r in f + blind if (r['rep_err'] or 0) <= 1.0)}/{len(f) + len(blind)} (predict >= 97 %)")
        if arm == "N":
            due = [r for r in f if r["logged"] is not None and r["logged"] > 19.0]
            print(f"   H1 N: trail re-pins {sum(r['trail_pin'] for r in a)}; due (logged > 19) {len(due)}, re-pinned "
                  f"{sum(r['trail_pin'] for r in due)} (predict all); re-pins at the kill point "
                  f"{sum(1 for r in a if r['trail_pin'] and r['nudge'] and (r['nudge']['pin_K'] or 0) < 0.01)}")
            rp = [r for r in a if r["trail_pin"]]
            print(f"   H4 N trail-re-pinned proven hops within 700 ms: {sum(1 for r in rp if r['hop_p'] > 30)}/{len(rp)}"
                  f" (predict 0); gated (unproven) {sum(1 for r in rp if r['hop_g'] > 30)}")
            nd = [r["nudge"]["d"] for r in rp if r["nudge"] and r["nudge"]["resolved"]]
            print(f"   H5 N nudge |pin - drawn| resolved {len(nd)}/{len(rp)}: <= 8 u on {sum(1 for v in nd if v <= 8)}"
                  f" (predict >= 90 %, p50 <= 1 u) values {sorted(nd)}")
            off3 = [r for r in rp if r["idx"] != 3]
            print(f"   H6 N trail re-pins outside chain index 3: {len(off3)} {[(r['run'], r['p_t']) for r in off3]}"
                  f" (predict <= 1 per launch)")
        else:
            print(f"   H1 T: trail re-pins {sum(r['trail_pin'] for r in a)} (predict 0)")
            print(f"   H3 T > 25 u: proven HANDOVER hops {sum(r['hand'] for r in tc25)}/{len(tc25)} (predict >= 70 %); "
                  f"<= 19 u: {sum(r['hand'] for r in f if r not in tc)}/{len(f) - len(tc)} (predict <= 1 per 100)")
        print(f"   H7 proven far-kill hops per 100: {100 * sum(1 for r in f if r['hop_p'] > 30) / max(len(f), 1):.2f}"
              f" ({sum(1 for r in f if r['hop_p'] > 30)}/{len(f)}); gated {sum(1 for r in f if r['hop_g'] > 30)}")
        print("   trailing-class rows:", [(r["run"], r["p_t"], r["idx"], r["kseg"], r["logged"], r["trail_pin"],
                                          r["hop_p"], r["hand"], r["nudge"]) for r in tc])


def main():
    global LOGS, JSON_OUT
    args, rest = [], sys.argv[1:]
    while rest:
        a = rest.pop(0)
        if a == "--logs":
            LOGS = rest.pop(0)
        elif a == "--json":
            JSON_OUT = rest.pop(0)
        elif "=" in a and not a.startswith("--"):          # LABEL=HARNESS_STAMP,GAMESRV_STAMP,TAP : an extra launch
            lab, spec = a.split("=", 1)
            PB.TP_RUNS[lab] = tuple(spec.split(","))
            args.append(lab)
        else:
            args.append(a)
    if args and args[0] == "--selftest":
        rows, metas = [], []
        for run, arm in SELF:
            r, m = score_run(run, "T", self_locate(run))
            rows += r
            metas.append(m)
        if JSON_OUT:
            json.dump(dict(meta=metas, rows=rows), open(JSON_OUT, "w"), indent=0, default=str)
        report(rows, metas)
        f = [r for r in rows if r["act"] == "kill" and (r["op"] or 0) > 2 and r["kseg"] is not None and (r["rep_err"] or 0) < 5]
        hi = [(r["run"], r["p_t"]) for r in f if r["kseg"] > 25]
        ok = (sorted(hi) == [("LT4", 70.6531), ("kK1", 49.4488), ("kN3", 70.5567)]
              and all(r["hand"] for r in f if r["kseg"] > 25) and not any(r["hand"] for r in f if r["kseg"] <= 19))
        print(f"\nSELFTEST {'PASS' if ok else 'FAIL'}: K term > 25 on {hi}; handover hops > 25 "
              f"{sum(r['hand'] for r in f if r['kseg'] > 25)}, <= 19 {sum(r['hand'] for r in f if r['kseg'] <= 19)}")
        sys.exit(0 if ok else 1)
    check = bool(args and args[0] == "--check")
    runs = args[1:] if check else args
    rows, metas, bad_any = [], [], False
    for run in runs:
        arm = run[0]
        r, m = score_run(run, arm, locate(run))
        bad = aborts(r, m)
        print(f"== {run}: {'ABORT: ' + '; '.join(bad) if bad else 'no abort'}")
        bad_any = bad_any or bool(bad)
        rows += r
        metas.append(m)
    if not check:
        if JSON_OUT:
            json.dump(dict(meta=metas, rows=rows), open(JSON_OUT, "w"), indent=0, default=str)
        report(rows, metas)
    sys.exit(1 if (check and bad_any) else 0)


if __name__ == "__main__":
    main()
