#!/usr/bin/env python3
"""The integrator's flat 288 u/s against the movement family's own rate (MOVECODE-1z-cu).

    python studies/movecode/review/modelrate.py                  # every September gamesrv capture
    python studies/movecode/review/modelrate.py --since 20260908 # from that stamp on
    python studies/movecode/review/modelrate.py <gamesrv.jsonl> ...
    python studies/movecode/review/modelrate.py --check          # sec.1z-cu's figures as bars

THE DEFECT (sec.1z-cq.5). The world tick walks `state["pos"]` toward `state["dest"]` at
`DEFAULT_RUN_SPEED * TICK_SECONDS` = 14.4 u per tick whatever the 0x003D's movementType
said, while the same file's lead model (`a2_leg_note`) walks the SAME heading at
`FAMILY_RATE[mt] * 288` -- 190.08 u/s on a backpedal (mt 4-6), 216 on a strafe (7-8).
So the position model runs 51% ahead of a backpedalling body even when the body is
genuinely moving, and the NPC follow, the leash and the range gate read the result.

WHAT THIS MEASURES, off the capture alone -- no mesh, no replay of the server:

  (a) THE BODY'S OWN RATE PER FAMILY. Consecutive accepted 0x003D reports on an
      unchanged heading (cos > 0.996, the arm's own `turned` test) give the body's
      displacement over the gap. v / 288 per movementType is the check with no free
      parameter: if the table is right on OUR client, forward reads ~1.0, backpedal
      ~0.66, strafe ~0.75 -- and if it reads 1.0 everywhere, the fix is wrong and
      this prints so.

  (b) THE INTEGRATOR, REPRODUCED FROM ITS OWN OUTPUT. Each accepted 0x003D adopts the
      report as `state["pos"]` and arms `state["dest"]`; the next position_report row
      records `ours` -- where the integrator had walked to. So the shipped model's
      advance L = |ours(t1) - reported(t0)| and its direction are OBSERVED, not
      simulated. Where the model did not arrive, L / 14.4 is the tick count and must be
      near-integer (the instrument's own validation, printed); where it parked at the
      clipped dest, L is the leg. The FIXED arm walks the same direction at
      rate(mt) * 14.4 per tick for the same ticks, capped at the same L (a slower
      walker never passes where the faster one parked). Its drift against the client's
      next report is then |model_fix - reported(t1)| beside the recorded drift.

  (c) The two split by whether the BODY moved over the gap (> one tick step) -- the
      phantom-leg class is 1z-cp's and a rate can only shrink it, never remove it.

A gap is excluded when anything else could have written `state["pos"]` inside it: a
click (`kbd_leg kill why=click`, a click-armed grant), a stop report closing it that
was not the next report, an unaccepted report, or a tick count that is not
near-integer in the walking case (something else moved the model; say so, count it,
do not score it).

Read-only. Stdlib only. Needs the vault (the captures are the owner's own).
"""
import glob
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))

import vaultpath                                            # noqa: E402

RUN = 288.0
TICK = 0.05
STEP = RUN * TICK
FAMILY_RATE = {1: 1.00, 2: 1.00, 3: 1.00,
               4: 0.66, 5: 0.66, 6: 0.66,
               7: 0.75, 8: 0.75}
FAMILY_NAME = {1: "fwd", 2: "fwd", 3: "fwd", 4: "back", 5: "back", 6: "back",
               7: "side", 8: "side"}
TICK_TOL = 0.08          # |L/14.4 - round| within this: the model walked whole ticks
COS_SAME = 0.996          # the 0x003D arm's own `turned` threshold


def _rows(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def _arm(rows):
    """Which integrator the capture ran: True under 1z-cu, False on the flat one,
    None when the header predates the flag (every capture before 2026-09-09)."""
    for r in rows:
        if r.get("kind") == "flags":
            return r.get("MODEL_FAMILY_RATE")
    return None


def _origin(rows):
    for r in rows:
        if r.get("kind") == "origin":
            return r.get("origin") or r.get("value") or r.get("server")
    return None


def gaps(rows):
    """One record per accepted 0x003D -> next accepted report. Pure over the rows."""
    out = []
    fixed = _arm(rows) is True
    excluded = {"click": 0, "refused": 0, "ticks": 0, "no-model": 0}
    # Pair each position_report with the decoded 0x003D just before it (same
    # receive, the decoded row is written first).
    last_dec = None
    reps = []
    for i, r in enumerate(rows):
        k = r.get("kind")
        if k == "decoded" and r.get("opcode") in (61, 71):
            last_dec = r
        elif k == "position_report":
            mt = None
            heading = None
            if last_dec is not None and last_dec.get("opcode") == 61 \
                    and abs(float(last_dec.get("t", -9)) - float(r.get("t", 0))) < 0.05:
                v = last_dec.get("values") or []
                if len(v) >= 5:
                    mt = v[4]
                    heading = (float(v[3][0]), float(v[3][1]))
            reps.append((i, r, mt, heading))
    for (i0, a, mt, heading), (i1, b, _mt1, _h1) in zip(reps, reps[1:]):
        if a.get("source") != "0x003D" or not a.get("accepted"):
            continue
        if not b.get("accepted"):
            excluded["refused"] += 1
            continue
        # anything that could have moved the model or ended the leg by another route
        clicked = False
        for r in rows[i0 + 1:i1]:
            k = r.get("kind")
            if k == "kbd_leg" and r.get("act") == "kill" and r.get("why") == "click":
                clicked = True
            if k == "grant_verdict" and r.get("lead_src") not in (None, "kbd", "d1"):
                clicked = True
            if k == "decoded" and r.get("opcode") in (0x0026, 0x0033, 0x0024):
                clicked = True
        if clicked:
            excluded["click"] += 1
            continue
        p0 = (float(a["reported"][0]), float(a["reported"][1]))
        p1 = (float(b["reported"][0]), float(b["reported"][1]))
        m1 = b.get("ours")
        if not m1:
            excluded["no-model"] += 1
            continue
        m1 = (float(m1[0]), float(m1[1]))
        dt = float(b["t"]) - float(a["t"])
        L = math.hypot(m1[0] - p0[0], m1[1] - p0[1])
        n_walk = L / STEP
        body = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        rec = {"t0": a["t"], "t1": b["t"], "dt": dt, "mt": mt, "heading": heading,
               "p0": p0, "p1": p1, "m1": m1, "L": L, "body": body,
               "drift_rec": float(b.get("drift") or 0.0),
               "drift_ship": math.hypot(m1[0] - p1[0], m1[1] - p1[1]),
               "closer": b.get("source"), "mt1": _mt1, "h1": _h1,
               "fixed": fixed}
        out.append(rec)
    return out, excluded


def score(g):
    """Both arms on one gap. Adds n_ticks / arrived / model_fix / drift_fix."""
    rate = FAMILY_RATE.get(g["mt"], 1.0)
    # A capture recorded UNDER 1z-cu already walked at rate x 14.4 per tick, so its
    # tick count is L / (rate x STEP) and the "fix" arm is the identity on it -- the
    # (b) table then reads the SHIPPED integrator's drift in its ship column and the
    # two columns agree by construction. Say which arm the capture ran; never score
    # a fixed capture as if it were the flat one.
    step_ship = (rate if g.get("fixed") else 1.0) * STEP
    L, dt = g["L"], g["dt"]
    if L < 1e-6:
        g.update(n=0, arrived=True, advance_fix=0.0, model_fix=g["m1"],
                 drift_fix=g["drift_ship"], valid=True, step_ship=step_ship)
        return g
    n_walk = L / step_ship
    n_int = round(n_walk)
    whole = abs(n_walk - n_int) < TICK_TOL and n_int >= 1
    # Did the shipped model park (arrive) inside the gap? If the tick count the
    # walk implies is far below what the clock allows, it parked. With a whole
    # count that matches the clock it walked the whole gap.
    n_clock = int(dt / TICK)
    if whole and n_int >= n_clock - 1:
        n, arrived = n_int, False
    else:
        # Parked inside the gap. The clock bounds the ticks from above and the
        # walk it made bounds them from below (a receive stamp can trail the
        # tick thread by a tick: 19 of 739 parked gaps walked one step more than
        # dt / TICK allows); the larger is the count the slower walker gets.
        n, arrived = max(n_clock, math.ceil(n_walk - TICK_TOL), 1), True
    advance_fix = min(rate * STEP * n, L)
    ux, uy = (g["m1"][0] - g["p0"][0]) / L, (g["m1"][1] - g["p0"][1]) / L
    mf = (g["p0"][0] + ux * advance_fix, g["p0"][1] + uy * advance_fix)
    g.update(n=n, arrived=arrived, advance_fix=advance_fix, model_fix=mf, step_ship=step_ship,
             drift_fix=math.hypot(mf[0] - g["p1"][0], mf[1] - g["p1"][1]),
             valid=(whole or arrived))
    return g


def body_rates(gs, min_dt=0.1):
    """(a): v/288 per family on unchanged-heading 0x003D -> 0x003D pairs."""
    by = {}
    for g in gs:
        if g["closer"] != "0x003D" or g["heading"] is None or g["h1"] is None:
            continue
        if g["mt"] != g["mt1"]:
            continue
        hx, hy = g["heading"]
        kx, ky = g["h1"]
        mags = math.hypot(hx, hy) * math.hypot(kx, ky)
        if mags <= 0 or (hx * kx + hy * ky) < COS_SAME * mags:
            continue
        if g["dt"] < min_dt or g["body"] < STEP:
            continue
        by.setdefault(g["mt"], []).append(g["body"] / g["dt"] / RUN)
    return by


def q(vals, f):
    if not vals:
        return float("nan")
    s = sorted(vals)
    return s[min(len(s) - 1, int(f * len(s)))]


def report(paths, check=False):
    pooled = []
    excl_all = {}
    print("capture                              gaps  excl   fwd  back  side  integrator")
    for p in paths:
        rows = _rows(p)
        org = _origin(rows)
        if org not in (None, "ours"):
            print(f"  {os.path.basename(p)}: origin {org!r}, skipped")
            continue
        gs, excl = gaps(rows)
        gs = [score(g) for g in gs]
        for k, v in excl.items():
            excl_all[k] = excl_all.get(k, 0) + v
        fam = {"fwd": 0, "back": 0, "side": 0}
        for g in gs:
            fam[FAMILY_NAME.get(g["mt"], "fwd")] += 1
        arm = _arm(rows)
        arm_s = ("family-rate (1z-cu)" if arm is True
                 else "flat 288 (--no-model-family-rate)" if arm is False
                 else "flat 288 (pre-1z-cu header)")
        print(f"  {os.path.basename(p):36} {len(gs):4}  {sum(excl.values()):4}"
              f"  {fam['fwd']:4}  {fam['back']:4}  {fam['side']:4}  {arm_s}")
        for g in gs:
            g["cap"] = os.path.basename(p)
        pooled.extend(gs)
    print(f"\nexcluded: {excl_all}")
    valid = [g for g in pooled if g["valid"]]
    invalid = [g for g in pooled if not g["valid"]]
    print(f"gaps scored {len(valid)}, tick count not whole (something else moved the "
          f"model; NOT scored) {len(invalid)}")

    # the instrument's validation: recorded drift == |ours - reported| on every row
    mism = [g for g in pooled if abs(g["drift_rec"] - g["drift_ship"]) > 0.05]
    print(f"recorded drift vs |ours - reported| disagree on {len(mism)} of {len(pooled)}")

    walk = [g for g in valid if g["L"] > 1e-6 and not g["arrived"]]
    resid = max((abs(g["L"] / g["step_ship"] - round(g["L"] / g["step_ship"]))
                 for g in walk), default=0.0)
    per = [g["dt"] / round(g["L"] / g["step_ship"]) for g in walk if g["dt"] > 0.4]
    n_fixed = sum(1 for g in valid if g.get("fixed"))
    print(f"the integrator reproduced: {len(walk)} gaps walked a WHOLE number of ticks at "
          f"the arm's own step (residual max {resid:.3f}); tick period p50 "
          f"{q(per, .5):.4f} s; {n_fixed} of {len(valid)} gaps were recorded under 1z-cu "
          f"(their fix column is the identity)")

    print("\n(a) THE BODY'S OWN RATE, unchanged heading, consecutive 0x003D (v / 288).")
    print("   SUSTAINED legs (gap >= 1.0 s, the chord trigger's own cadence) -- the clean read:")
    fam_v = {}
    by = body_rates(valid, min_dt=1.0)
    for mt in sorted(by):
        vs = by[mt]
        fam_v.setdefault(FAMILY_NAME[mt], []).extend(vs)
        print(f"   mt {mt} ({FAMILY_NAME[mt]:4}) n={len(vs):3}  p50 {q(vs, .5):.3f}  "
              f"p25 {q(vs, .25):.3f}  p75 {q(vs, .75):.3f}   table {FAMILY_RATE[mt]:.2f}")
    fwd50 = q(fam_v.get("fwd", []), .5)
    for f in ("fwd", "back", "side"):
        vs = fam_v.get(f, [])
        if vs:
            ratio = q(vs, .5) / fwd50 if fwd50 == fwd50 and fwd50 else float("nan")
            print(f"   {f:4} pooled n={len(vs):3}  p50 {q(vs, .5):.3f}   / forward = {ratio:.3f}")
    print("   ALL gaps (>= 0.1 s), for the record. The 0.3-0.6 s class is the scripted")
    print("   harness's 0.5 s re-report cadence and reads ~0.72 x table on EVERY family --")
    print("   a family-independent per-gap loss, not this fix's business:")
    by_all = body_rates(valid, min_dt=0.1)
    for f, mts in (("fwd", (1, 2, 3)), ("back", (4, 5, 6)), ("side", (7, 8))):
        vs = [v for mt in mts for v in by_all.get(mt, [])]
        if vs:
            print(f"   {f:4} n={len(vs):4}  p50 {q(vs, .5):.3f}")

    print("\n(b) THE INTEGRATOR, both arms, drift at the closing report (u):")
    print("   family   class    n   ship p50   fix p50   ship mean   fix mean   better  worse  max-worse")
    cells = {}
    for f in ("back", "side", "fwd"):
        for cls in ("moving", "held"):
            sel = [g for g in valid if FAMILY_NAME.get(g["mt"], "fwd") == f
                   and ((g["body"] > STEP) == (cls == "moving"))]
            if not sel:
                continue
            ship = [g["drift_ship"] for g in sel]
            fix = [g["drift_fix"] for g in sel]
            better = sum(1 for g in sel if g["drift_fix"] < g["drift_ship"] - 0.5)
            worse = sum(1 for g in sel if g["drift_fix"] > g["drift_ship"] + 0.5)
            mw = max((g["drift_fix"] - g["drift_ship"] for g in sel), default=0.0)
            cells[(f, cls)] = {"n": len(sel), "ship_p50": q(ship, .5), "fix_p50": q(fix, .5),
                               "ship_mean": statistics.fmean(ship),
                               "fix_mean": statistics.fmean(fix),
                               "better": better, "worse": worse, "max_worse": mw}
            c = cells[(f, cls)]
            print(f"   {f:6}   {cls:6} {c['n']:4}   {c['ship_p50']:8.1f}  {c['fix_p50']:8.1f}"
                  f"   {c['ship_mean']:9.1f}  {c['fix_mean']:9.1f}   {better:6} {worse:6}"
                  f"  {mw:9.1f}")

    print("\n   the ten worst backpedal/strafe gaps with the body MOVING:")
    worst = sorted((g for g in valid if FAMILY_NAME.get(g["mt"], "fwd") != "fwd"
                    and g["body"] > STEP), key=lambda g: -g["drift_ship"])[:10]
    for g in worst:
        print(f"     {g['cap'][8:23]} t={g['t0']:8.3f} mt {g['mt']} dt {g['dt']:.3f} "
              f"body {g['body']:6.1f} model {g['L']:6.1f}{' parked' if g['arrived'] else ''}"
              f"  drift {g['drift_ship']:6.1f} -> {g['drift_fix']:6.1f}")

    if check:
        ok = True

        def bar(cond, what):
            nonlocal ok
            print(f"   [{'PASS' if cond else 'FAIL'}] {what}")
            ok = ok and cond
        print("\n--check: sec.1z-cu's bars")
        b = fam_v.get("back", [])
        s = fam_v.get("side", [])
        f = fam_v.get("fwd", [])
        bar(len(b) >= 20 and len(f) >= 20 and len(s) >= 20,
            f"exposure: sustained rate samples fwd {len(f)} / back {len(b)} / side {len(s)}")
        bar(f and 0.97 <= q(f, .5) <= 1.01, f"forward body rate p50 {q(f, .5):.3f} within 0.97..1.01")
        bar(b and f and 0.64 <= q(b, .5) / q(f, .5) <= 0.68,
            f"backpedal / forward {q(b, .5) / q(f, .5):.3f} within 0.64..0.68 (table 0.66)")
        bar(s and f and 0.73 <= q(s, .5) / q(f, .5) <= 0.77,
            f"strafe / forward {q(s, .5) / q(f, .5):.3f} within 0.73..0.77 (table 0.75)")
        bm = cells.get(("back", "moving"))
        bar(bm is not None and bm["n"] >= 20, f"exposure: back/moving gaps {bm['n'] if bm else 0}")
        bar(bm is not None and bm["fix_mean"] < 0.75 * bm["ship_mean"],
            "back/moving mean drift falls by more than a quarter under the fix")
        bar(bm is not None and bm["worse"] <= max(1, bm["n"] // 10),
            f"back/moving gaps made worse: {bm['worse'] if bm else '?'} (<= 10%)")
        fm = cells.get(("fwd", "moving"))
        bar(fm is not None and fm["max_worse"] < 1.0
            and abs(fm["fix_mean"] - fm["ship_mean"]) < 0.01,
            f"forward gaps are untouched (rate 1.0 is the identity; max change "
            f"{fm['max_worse'] if fm else '?'} u, a receive stamp trailing the tick thread)")
        print("ALL BARS MET" if ok else "A BAR FAILED")
        return 0 if ok else 1
    return 0


def main(argv):
    check = "--check" in argv
    argv = [a for a in argv if a != "--check"]
    since = "20260901"
    if "--since" in argv:
        i = argv.index("--since")
        since = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    paths = [a for a in argv if a.endswith(".jsonl")]
    if not paths:
        d = vaultpath.require_dir("captures", "gamesrv")
        paths = sorted(p for p in glob.glob(os.path.join(d, "authsrv-*-c1.jsonl"))
                       if os.path.basename(p)[8:16] >= since)
    if not paths:
        print("no captures", file=sys.stderr)
        return 2
    return report(paths, check)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
