#!/usr/bin/env python3
"""The keyboard arm's grant floor: what retail does, and what the floor cost us (MOVECODE-1z-cw).

    python studies/movecode/review/floorcensus.py            # both halves
    python studies/movecode/review/floorcensus.py --check    # sec.1z-cw's figures as bars
    python studies/movecode/review/floorcensus.py --ours-only / --retail-only
    python studies/movecode/review/floorcensus.py --ours-only --cap C [--cap C2]   # named runs
    python studies/movecode/review/floorcensus.py --ours-only --parked   # the parked copy (1z-cw.6)

TWO HALVES, two corpora, never pooled (toolkit/origin.py's rule; livewire gates LIVE).

  RETAIL (origin live, through toolkit/authsrv/livewire.py). For every c2s 0x003D on
  every live game connection: was it answered by a 0x0029 addressed to the PLAYER (the
  agent most often named within 0.3 s after a report) within 0.3 s, and how long after
  the previous player grant did it arrive? `_heading_grant_ok`'s own predicate is
  `since < floor`, so "reports inside 0.5 s of the previous grant, answered anyway" is
  the retail contract the floor contradicts, measured with the floor's own operand.
  Also: where the granted point sits against the report it answers (retail grants the
  client's own ~766 u proposed endpoint, along the heading, 99.9%).

  OURS (origin ours, the RUN-1zCG hand-driven sessions with an agenttap tape). (a) The
  verdict census: fired at once / refused `heading-rate` / re-baked by the 1z-y hold.
  (b) WHERE WORLD-0'S LAG ACCRUES: per tape sample while the drawn body moves, the
  change in world-0's along-track offset behind the body, attributed to the copy's
  state (walking / parked) and the last grant verdict in force. Lag that accrues under
  a `heading-rate` refusal is lag the floor caused; the parked share is the copy
  standing at a matured lead while the body runs, which the refused report would have
  extended.

Read-only. Stdlib only. Needs the vault (captures and tapes are the owner's own).
"""
import bisect
import collections
import glob
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/clientscan", "toolkit/authsrv", "toolkit/schema",
            "studies/movecode/review"):
    sys.path.insert(0, os.path.join(ROOT, sub))

import vaultpath                                   # noqa: E402
import w0score as W                                # noqa: E402
import sessionscore as S                           # noqa: E402

C2S_HEADING = 61          # MOVE_SET_HEADING / TURN_TO_DIRECTION, the 0x003D
S2C_MOVE_TO_POINT = 41    # 0x0029
OLD_FLOOR = 0.5
ANSWER_WINDOW = 0.3


def q(vals, f):
    if not vals:
        return float("nan")
    s = sorted(vals)
    return s[min(len(s) - 1, int(f * len(s)))]


def retail():
    import livewire
    out = {"conns": 0, "reports": 0, "answered": 0, "inside": 0, "inside_answered": 0,
           "delay_inside": [], "grant_gaps": [], "report_gaps": [], "mag": [], "along": [],
           "across": []}
    for capdir, conn_file in livewire.live_connections():
        conn, merged, ok = livewire.decode_conn(capdir, conn_file)
        if not ok or not merged:
            continue
        c61 = [(t, v) for (t, dr, op, v) in merged if dr == "c2s" and op == C2S_HEADING]
        s29 = [(t, v) for (t, dr, op, v) in merged
               if dr == "s2c" and op == S2C_MOVE_TO_POINT and len(v) >= 3]
        if len(c61) < 20 or not s29:
            continue
        # the player: the agent a 0x0029 names most often within 0.3 s after a 0x003D.
        # livewire's s2c values carry the opcode in slot 0, the agent in slot 1, the
        # point in slot 2 (c2s: agent, point, plane, vec2, movementType).
        cnt = collections.Counter()
        st = [t for t, _ in s29]
        for t, _ in c61:
            i = bisect.bisect_left(st, t)
            for j in range(i, min(i + 4, len(s29))):
                if s29[j][0] - t <= ANSWER_WINDOW:
                    cnt[s29[j][1][1]] += 1
        if not cnt:
            continue
        pid = cnt.most_common(1)[0][0]
        p29 = [(t, v) for t, v in s29 if v[1] == pid]
        pt = [t for t, _ in p29]
        if len(p29) < 10:
            continue
        out["conns"] += 1
        out["grant_gaps"] += [b - a for a, b in zip(pt, pt[1:])]
        out["report_gaps"] += [b[0] - a[0] for a, b in zip(c61, c61[1:])]
        for t, v in c61:
            out["reports"] += 1
            k = bisect.bisect_left(pt, t) - 1
            since = t - pt[k] if k >= 0 else None
            i = bisect.bisect_left(pt, t)
            answered = i < len(p29) and pt[i] - t <= ANSWER_WINDOW
            if answered:
                out["answered"] += 1
            if since is not None and since < OLD_FLOOR:
                out["inside"] += 1
                if answered:
                    out["inside_answered"] += 1
                    out["delay_inside"].append(pt[i] - t)
            if not answered:
                continue
            R, h, P = v[1], v[3], p29[i][1][2]
            hm = math.hypot(h[0], h[1])
            if hm < 1:
                continue
            dx, dy = P[0] - R[0], P[1] - R[1]
            out["mag"].append(math.hypot(dx, dy))
            out["along"].append((dx * h[0] + dy * h[1]) / hm)
            out["across"].append(abs((-dx * h[1] + dy * h[0]) / hm))
    return out


def ours(paths):
    verdicts = collections.Counter()
    acc = collections.defaultdict(float)
    samples = collections.Counter()
    sep_by = collections.defaultdict(list)
    per_session = []
    for cap in paths:
        rows = W.load_gamesrv(cap)
        tape = S.find_tape(rows)
        if tape is None:
            continue
        head, trows = W.load(tape)
        p1 = W.series(head, trows, 1)
        gv = [r for r in rows if r.get("kind") == "grant_verdict" and r.get("arm") == "zero-lead"]
        gw = [r["wall_unix"] for r in gv]
        n_s = collections.Counter()
        for r in gv:
            key = r.get("reason") if not r.get("fired") else (
                "deferred-heading" if r.get("deferred") else "fired")
            verdicts[key] += 1
            n_s[key] += 1
        prev = None
        seps = []
        for smp in p1:
            if prev is None or smp["vbody"] <= 1.0 or smp["w"] - prev["w"] > 0.2:
                prev = smp
                continue
            bx, by = smp["body"][0] - prev["body"][0], smp["body"][1] - prev["body"][1]
            bm = math.hypot(bx, by)
            if bm < 1.0:
                prev = smp
                continue
            ux, uy = bx / bm, by / bm

            def along(x):
                dx, dy = x["w0"][0] - x["body"][0], x["w0"][1] - x["body"][1]
                return dx * ux + dy * uy
            da = along(smp) - along(prev)
            i = bisect.bisect_right(gw, smp["w"]) - 1
            v = gv[i] if i >= 0 else None
            cls = ("none" if v is None else
                   ("refused:" + str(v.get("reason")) if not v.get("fired")
                    else "fired:" + str(v.get("lead_clip_why"))))
            state = "parked" if smp["v0"] <= 1.0 else "walking"
            if da < 0:
                acc[(state, cls)] += -da
            samples[(state, cls)] += 1
            sep = math.dist(smp["w0"], smp["body"])
            sep_by[cls].append(sep)
            seps.append(sep)
            prev = smp
        per_session.append((os.path.basename(cap)[8:23], dict(n_s), q(seps, .5), len(seps)))
    return verdicts, acc, samples, sep_by, per_session


def parked_episodes(paths):
    """1z-cw.6: the copy PARKED while the body moves and a refusal is in force -- which
    grant parked it, where, how long after, and for how long. One record per episode."""
    eps = []
    for cap in paths:
        rows = W.load_gamesrv(cap)
        tape = S.find_tape(rows)
        if tape is None:
            continue
        head, trows = W.load(tape)
        p1 = W.series(head, trows, 1)
        gv = [r for r in rows if r.get("kind") == "grant_verdict" and r.get("arm") == "zero-lead"]
        gw = [r["wall_unix"] for r in gv]
        fired = [r for r in gv if r.get("fired")]
        fw = [r["wall_unix"] for r in fired]
        cur = None
        for smp in p1:
            i = bisect.bisect_right(gw, smp["w"]) - 1
            v = gv[i] if i >= 0 else None
            on = (smp["vbody"] > 1.0 and smp["v0"] <= 1.0
                  and v is not None and not v.get("fired"))
            if on and cur is None:
                j = bisect.bisect_right(fw, smp["w"]) - 1
                g = fired[j] if j >= 0 else None
                cur = {"t0": smp["w"], "w0": smp["w0"], "grant": g,
                       "since": (smp["w"] - g["wall_unix"]) if g else None}
            elif not on and cur is not None:
                cur["dur"] = smp["w"] - cur["t0"]
                eps.append(cur)
                cur = None
    return eps


def report_parked(eps):
    print(f"\nTHE PARKED COPY under a refusal (1z-cw.6): {len(eps)} episodes")
    if not eps:
        return
    dur = [e["dur"] for e in eps]
    since = [e["since"] for e in eps if e["since"] is not None]
    print(f"  duration p50 {q(dur, .5):.2f} s, p90 {q(dur, .9):.2f}, total {sum(dur):.1f} s; "
          f"park begins p50 {q(since, .5):.2f} s after the last fired grant (p90 {q(since, .9):.2f})")
    why = collections.Counter((e["grant"] or {}).get("lead_clip_why") for e in eps)
    print("  the grant that parked it, by clip: " + ", ".join(f"{k} {v}" for k, v in why.most_common(8)))
    src = collections.Counter(((e["grant"] or {}).get("lead_src"), (e["grant"] or {}).get("reason")) for e in eps)
    print("  its source / reason: " + ", ".join(f"{k[0]}/{k[1]} {v}" for k, v in src.most_common(4)))
    d = [math.dist(e["w0"], e["grant"]["dest"]) for e in eps if e["grant"] and e["grant"].get("dest")]
    print(f"  the copy sits ON that grant's point: within 8 u on {sum(1 for x in d if x < 8)} of {len(d)}, "
          f"|copy - dest| p50 {q(d, .5):.1f} u -- it ARRIVED at a lead the wall or the fence cut short")


def main(argv):
    check = "--check" in argv
    do_retail = "--ours-only" not in argv
    do_ours = "--retail-only" not in argv
    ok = True

    def bar(c, what):
        nonlocal ok
        print(f"   [{'PASS' if c else 'FAIL'}] {what}")
        ok = ok and c

    R = None
    if do_retail:
        R = retail()
        n = R["reports"]
        print(f"RETAIL: {R['conns']} live connections, {n} heading reports")
        print(f"  answered by the PLAYER's 0x0029 within {ANSWER_WINDOW} s: {R['answered']} "
              f"({100 * R['answered'] / max(1, n):.1f}%)")
        print(f"  reports INSIDE {OLD_FLOOR} s of the previous player grant: {R['inside']} "
              f"({100 * R['inside'] / max(1, n):.1f}%); answered anyway {R['inside_answered']} "
              f"({100 * R['inside_answered'] / max(1, R['inside']):.1f}%), delay p50 "
              f"{q(R['delay_inside'], .5):.3f} p90 {q(R['delay_inside'], .9):.3f} s")
        gg = R["grant_gaps"]
        print(f"  consecutive player grants: gap p10 {q(gg, .1):.3f} p50 {q(gg, .5):.3f} "
              f"p90 {q(gg, .9):.3f} s; under {OLD_FLOOR} s {sum(1 for g in gg if g < OLD_FLOOR)} "
              f"of {len(gg)} ({100 * sum(1 for g in gg if g < OLD_FLOOR) / max(1, len(gg)):.1f}%)"
              f" -- the 0.49 s median GRANT_MIN_INTERVAL cited is the CLIENT's report cadence")
        print(f"  the granted point vs the report it answers: |P-R| p50 {q(R['mag'], .5):.1f} "
              f"p90 {q(R['mag'], .9):.1f}; along the heading p50 {q(R['along'], .5):.1f}; "
              f"across p90 {q(R['across'], .9):.1f}; on the report itself "
              f"{sum(1 for m in R['mag'] if m < 2.0)} -- retail grants the client's own endpoint")
    if do_ours:
        d = vaultpath.require_dir("captures", "gamesrv")
        paths = []
        if "--cap" in argv:
            # named captures (RUN-1zCW's arms): whatever tape overlaps them
            for i, a in enumerate(argv):
                if a == "--cap" and i + 1 < len(argv):
                    paths.append(argv[i + 1])
        else:
            for cap in sorted(glob.glob(os.path.join(d, "authsrv-2026090[6-9]*-c1.jsonl"))):
                rows = W.load_gamesrv(cap)
                tape = S.find_tape(rows)
                if tape is not None and "1zcg" in os.path.basename(tape):
                    paths.append(cap)
        if "--parked" in argv:
            report_parked(parked_episodes(paths))
        verdicts, acc, samples, sep_by, per = ours(paths)
        tot_v = sum(verdicts.values())
        print(f"\nOURS: {len(paths)} hand-driven sessions with a tape; heading evaluations {tot_v}")
        for k, v in verdicts.most_common():
            print(f"  {k:20} {v:5} ({100 * v / max(1, tot_v):.1f}%)")
        for name, ns, p50, n in per:
            print(f"  {name}: {ns}  world-0 vs body moving p50 {p50:.1f} u over {n} samples")
        tot = sum(acc.values())
        print(f"\n  ALONG-TRACK LAG ACCRUED while the body moves: {tot:.0f} u, by the copy's state "
              f"and the verdict in force:")
        for k, v in sorted(acc.items(), key=lambda kv: -kv[1])[:10]:
            print(f"    {k[0]:8} {k[1]:28} {v:7.0f} u ({100 * v / max(1, tot):4.1f}%)  samples {samples[k]}")
        under = sum(v for k, v in acc.items() if k[1] == "refused:heading-rate")
        parked = acc.get(("parked", "refused:heading-rate"), 0.0)
        print(f"  under a heading-rate refusal: {under:.0f} u ({100 * under / max(1, tot):.1f}%), "
              f"of which world-0 PARKED {parked:.0f} u ({100 * parked / max(1, tot):.1f}%)")
        print(f"  world-0 vs body while moving, by verdict in force: fired:clear p50 "
              f"{q(sep_by.get('fired:clear', []), .5):.1f} u (n={len(sep_by.get('fired:clear', []))}); "
              f"refused:heading-rate p50 {q(sep_by.get('refused:heading-rate', []), .5):.1f} u "
              f"(n={len(sep_by.get('refused:heading-rate', []))})")
        if check:
            print("\n--check (ours)")
            bar(tot_v >= 1000, f"exposure: {tot_v} heading evaluations")
            fr = verdicts.get("heading-rate", 0) / max(1, tot_v)
            bar(fr >= 0.4, f"the floor refused {100 * fr:.1f}% of evaluations (>= 40%)")
            bar(under / max(1, tot) >= 0.5, f"lag accrued under refusals {100 * under / max(1, tot):.1f}% (>= 50%)")
            bar(q(sep_by.get("fired:clear", []), .5) < 0.5 * q(sep_by.get("refused:heading-rate", []), .5),
                "world-0 sits less than half as far from the body under a fresh clear grant as under a refusal")
    if check and R is not None:
        print("\n--check (retail)")
        bar(R["conns"] >= 20 and R["reports"] >= 2000,
            f"exposure: {R['conns']} connections, {R['reports']} reports")
        bar(R["answered"] / max(1, R["reports"]) >= 0.98,
            f"retail answers {100 * R['answered'] / max(1, R['reports']):.1f}% of heading reports (>= 98%)")
        bar(R["inside"] / max(1, R["reports"]) >= 0.5,
            f"{100 * R['inside'] / max(1, R['reports']):.1f}% of reports arrive inside the old floor (>= 50%)")
        bar(R["inside_answered"] / max(1, R["inside"]) >= 0.98,
            f"and {100 * R['inside_answered'] / max(1, R['inside']):.1f}% of those are answered (>= 98%)")
        bar(q(R["delay_inside"], .9) <= 0.1, f"answer delay p90 {q(R['delay_inside'], .9):.3f} s (<= 0.1)")
    if check:
        print("ALL BARS MET" if ok else "A BAR FAILED")
        return 0 if ok else 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
