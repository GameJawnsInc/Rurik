#!/usr/bin/env python3
"""Score an agenttap capture for the MOVECODE-1z-t verdict: how far is the
client's WORLD-0 copy of the player from the body it draws?

    python toolkit/clientscan/w0score.py --baseline      # positive control
    python toolkit/clientscan/w0score.py                 # newest capture
    python toolkit/clientscan/w0score.py <capture.jsonl>
    python toolkit/clientscan/w0score.py <capture.jsonl> --legs <report.json>

WHY THIS IS A TOOL AND NOT THREE LINES AT A PROMPT. The number this prints is
the whole verdict of MOVECODE-1z-t, and the arc has already published a wrong
version of it: sec.40.11's headline "max 806 u" was `m_point` read RAW, and
`m_point` is sample-and-hold. Read through the client's own accessor the same
capture gives 516. Any hand-rolled scoring of a new run would reproduce that
mistake, compare 806-scale numbers against 516-scale ones, and read a fix as a
regression or a regression as a fix.

So this file replicates `AgAgent::position_at` (0x005FF820) exactly, and its
CLAMP is the part a reimplementation gets wrong: if `m_timeStopMovement` is
non-zero and `when >= it`, the client copies `m_segmentPoint` out verbatim and
never integrates. Dead-reckoning past the arrival tick invents a separation the
client never computes. Same rule as `movetap.py:851-876`.

TWO GUARDS, because a run that measured nothing failed:
  * `--baseline` re-scores the 2026-09-02 capture and must reproduce p50 237 /
    max 516 u. That is a POSITIVE CONTROL for this scorer: if it cannot
    reproduce the known before-picture it cannot be trusted on the after.
  * EXPOSURE. If the drawn body barely translated, the run has no trials and
    this REFUSES to print a verdict rather than printing a flattering zero. In
    Guild Wars **A and D turn in place** (Q/E strafe) -- every A/D leg of the
    2026-09-02 kite travelled 0 u, so a walk script of `S:4 D:4 A:5 W:4` spends
    half its time measuring nothing. Drive W/S.

Read-only over a JSONL already on disk: no client, no vault write, stdlib only.
"""
import argparse
import glob
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

# The registered prediction (FINDINGS sec.1z-t.8), stated before the run so the
# reading cannot be rationalised afterwards.
CONFIRM_P50 = 150.0
REFUTE_P50 = 200.0
# The before-picture, re-scored with THIS scorer. Both are asserted by
# --baseline; the raw column is carried too because that is the number the
# arc published and a reader will meet it in sec.40.11.
BASELINE_STAMP = "agenttap-20260902T213401"
BASELINE_LIVE = (237.0, 516.1)      # p50, max -- position_at semantics
BASELINE_RAW = (237.0, 805.8)       # p50, max -- raw m_point, the artifact
# Exposure floor: the drawn body must actually translate. 500 u is a little
# over one report chord (~515 u), i.e. at least one full grant cycle of real
# movement; below that the capture cannot speak to a drift that accrues at
# report_gap x speed.
MIN_TRAVEL = 500.0
MIN_MOVING_SAMPLES = 20


def live(copy, clock):
    """AgAgent::position_at (0x005FF820), replicated. CLAMP FIRST."""
    stop = copy.get("stop") or 0
    if stop != 0 and clock is not None and (clock - stop) >= 0:
        sx, sy = copy.get("segx"), copy.get("segy")
        if (sx is not None and sy is not None
                and math.isfinite(sx) and math.isfinite(sy)):
            return sx, sy
        return copy["x"], copy["y"]
    dt = ((clock - copy["updated"]) * 0.001) if clock is not None else 0.0
    return (copy["x"] + copy.get("vx", 0.0) * dt,
            copy["y"] + copy.get("vy", 0.0) * dt)


def load(path):
    head, rows = None, []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("kind") == "head":
                head = r
            elif r.get("kind") == "sample":
                rows.append(r)
    if head is None:
        raise SystemExit(f"{path}: no head row -- not an agenttap capture")
    return head, rows


def series(head, rows, aid):
    """Per-sample (wall, world0_live, body_live, raw0, rawbody, body_speed)."""
    out = []
    for s in rows:
        a = (s.get("agents") or {}).get(str(aid))
        if not a:
            continue
        sy, ay = a.get("sync"), a.get("async")
        if not sy or not ay or "x" not in sy or "x" not in ay:
            continue
        out.append({
            "w": head["t0"] + s["t"],
            "t": s["t"],
            "w0": live(sy, s.get("clock0")),
            "body": live(ay, s.get("clock1")),
            "raw0": (sy["x"], sy["y"]),
            "rawbody": (ay["x"], ay["y"]),
            "vbody": math.hypot(ay.get("vx", 0.0), ay.get("vy", 0.0)),
            "v0": math.hypot(sy.get("vx", 0.0), sy.get("vy", 0.0)),
        })
    return out


def q(vals):
    v = sorted(vals)
    if not v:
        return (0.0, 0.0, 0.0, 0.0)
    return (statistics.median(v), v[int(0.75 * len(v))],
            v[min(int(0.9 * len(v)), len(v) - 1)], max(v))


def travel(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def newest():
    try:
        import vaultpath
        d = vaultpath.vault_path("research", "animref")
    except Exception as exc:                       # noqa: BLE001
        raise SystemExit(f"cannot resolve the vault: {exc}")
    hits = sorted(glob.glob(os.path.join(d, "agenttap-*.jsonl")))
    if not hits:
        raise SystemExit(f"no agenttap captures under {d}")
    return hits[-1]


def baseline_path():
    import vaultpath
    p = os.path.join(vaultpath.vault_path("research", "animref"),
                     BASELINE_STAMP + ".jsonl")
    if not os.path.exists(p):
        raise SystemExit(
            f"the baseline capture is missing: {p}\n"
            f"Without it this scorer has no positive control, so it REFUSES "
            f"to certify itself. Score a new capture explicitly if you accept "
            f"that.")
    return p


def score(path, legs=None, quiet=False):
    head, rows = load(path)
    p = series(head, rows, 1)
    if not p:
        raise SystemExit(f"{path}: no agent-1 samples with both copies")

    live_sep = [math.dist(r["w0"], r["body"]) for r in p]
    raw_sep = [math.dist(r["raw0"], r["rawbody"]) for r in p]
    body_travel = travel([r["body"] for r in p])
    w0_travel = travel([r["w0"] for r in p])
    moving = [r for r in p if r["vbody"] > 1.0]

    if not quiet:
        print(f"capture   {os.path.basename(path)}")
        print(f"          {len(p)} agent-1 samples over "
              f"{p[-1]['t'] - p[0]['t']:.1f} s")
        print()
        print("WORLD-0 vs THE BODY IT DRAWS  (the 1z-t verdict)")
        m, p75, p90, mx = q(live_sep)
        print(f"  position_at (clamp first)   p50 {m:7.1f}  p75 {p75:7.1f}"
              f"  p90 {p90:7.1f}  max {mx:8.1f}   <-- THE NUMBER")
        rm, _, rp90, rmx = q(raw_sep)
        print(f"  raw m_point (sample&hold)   p50 {rm:7.1f}"
              f"              p90 {rp90:7.1f}  max {rmx:8.1f}"
              f"   (the sec.40.11 artifact; do not quote)")
        print()
        print("EXPOSURE  -- a run that measured nothing failed")
        print(f"  drawn body translated       {body_travel:8.1f} u"
              f"   (floor {MIN_TRAVEL:.0f})")
        print(f"  world-0 travelled           {w0_travel:8.1f} u")
        print(f"  samples with the body moving{len(moving):8d}"
              f"   (floor {MIN_MOVING_SAMPLES})")
        speeds = sorted({round(r["vbody"]) for r in moving if r["vbody"] > 1})
        print(f"  body speeds seen            {speeds}"
              f"   (288 = forward, 190 = backpedal)")
        v0 = sorted({round(r["v0"]) for r in p if r["v0"] > 1})
        print(f"  world-0 speeds seen         {v0}"
              f"   (a bare [288] with 190 in the body row means the 0x002B "
              f"family rate is NOT reaching the client)")

    if legs:
        print()
        print("PER LEG  (A and D TURN IN PLACE in Guild Wars -- Q/E strafe)")
        rep = json.load(open(legs, encoding="utf-8"))
        for w in rep.get("walk", []):
            a0 = w.get("started_unix")
            a1 = w.get("ended_unix")
            if a0 is None or a1 is None:
                continue
            seg = [r for r in p if a0 <= r["w"] <= a1]
            if not seg:
                continue
            bt = travel([r["body"] for r in seg])
            wt = travel([r["w0"] for r in seg])
            sep = [math.dist(r["w0"], r["body"]) for r in seg]
            flag = "  <-- moved nothing" if bt < 1.0 else ""
            print(f"  {w.get('kind',''):5s} {str(w.get('key','')):2s} "
                  f"body {bt:7.1f} u   world-0 {wt:7.1f} u   "
                  f"sep {min(sep):6.1f}..{max(sep):6.1f}{flag}")

    enemy = series(head, rows, 10)
    if enemy and not quiet:
        e_own = [math.dist(r["w0"], r["body"]) for r in enemy]
        em, _, ep90, emx = q(e_own)
        print()
        print("ENEMY CONTROL (agent 10, its own two copies -- must stay small)")
        print(f"  world-0 vs drawn            p50 {em:7.1f}"
              f"              p90 {ep90:7.1f}  max {emx:8.1f}")

    return {"live": q(live_sep), "raw": q(raw_sep),
            "travel": body_travel, "moving": len(moving)}


def main():
    ap = argparse.ArgumentParser(
        description="Score an agenttap capture for the MOVECODE-1z-t verdict.")
    ap.add_argument("capture", nargs="?", default=None,
                    help="agenttap JSONL; default: newest in the vault")
    ap.add_argument("--baseline", action="store_true",
                    help="re-score the 2026-09-02 before-picture as a POSITIVE "
                         "CONTROL: it must reproduce p50 237 / max 516 u")
    ap.add_argument("--legs", default=None,
                    help="the harness report.json, for a per-leg breakdown")
    a = ap.parse_args()

    if a.baseline:
        print("POSITIVE CONTROL -- re-scoring the 2026-09-02 before-picture.")
        print("If this does not reproduce, the scorer is wrong and no verdict")
        print("it prints on a new capture means anything.\n")
        r = score(baseline_path())
        m, _, _, mx = r["live"]
        rm, _, _, rmx = r["raw"]
        ok = (abs(m - BASELINE_LIVE[0]) < 1.0
              and abs(mx - BASELINE_LIVE[1]) < 1.0
              and abs(rm - BASELINE_RAW[0]) < 1.0
              and abs(rmx - BASELINE_RAW[1]) < 1.0)
        print()
        if ok:
            print(f"[PASS] control reproduces: live p50 {m:.1f} / max {mx:.1f}"
                  f" and raw p50 {rm:.1f} / max {rmx:.1f}")
            return 0
        print(f"[FAIL] control does NOT reproduce. Expected live "
              f"{BASELINE_LIVE} and raw {BASELINE_RAW}; got live "
              f"({m:.1f}, {mx:.1f}) and raw ({rm:.1f}, {rmx:.1f}).")
        return 1

    path = a.capture or newest()
    r = score(path, legs=a.legs)
    m = r["live"][0]

    print()
    print("VERDICT vs the prediction registered in FINDINGS sec.1z-t.8")
    print(f"  registered: p50 < {CONFIRM_P50:.0f} u confirms, "
          f"> {REFUTE_P50:.0f} u refutes. Baseline was p50 "
          f"{BASELINE_LIVE[0]:.0f} / max {BASELINE_LIVE[1]:.0f}.")
    if r["travel"] < MIN_TRAVEL or r["moving"] < MIN_MOVING_SAMPLES:
        print(f"  ** NO VERDICT -- ZERO EXPOSURE. The drawn body translated "
              f"{r['travel']:.0f} u over {r['moving']} moving samples, under "
              f"the floor. This capture has run no trials and cannot confirm "
              f"OR refute. In Guild Wars A and D TURN IN PLACE -- if the walk "
              f"script used them, re-run with W/S (and Q/E to strafe).")
        return 2
    if m < CONFIRM_P50:
        print(f"  CONFIRMED: p50 {m:.1f} u.")
    elif m > REFUTE_P50:
        print(f"  REFUTED: p50 {m:.1f} u -- at or above the shipped baseline's "
              f"scale. Do not tune the lead; the terms have their own revert "
              f"flags (--no-kbd-lead / --no-kbd-speed-truth / "
              f"--no-kbd-stop-echo) so a follow-up can convict ONE of them.")
    else:
        print(f"  INCONCLUSIVE: p50 {m:.1f} u sits between the registered "
              f"bounds. Say so rather than rounding it to the nearer one.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
