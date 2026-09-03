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

THE ENSLAVEMENT DETECTOR (MOVECODE-1z-u.5 item c, FINDINGS sec.1z-x). The
number above cannot tell "world-0 follows the body" from "the body follows
world-0": once the client's AgTrack fence is shut, every 0x0029 we send is
walked as an ORDER, the drawn body's walk target becomes OUR granted point
to the unit, and the two copies agree because the body is enslaved -- which
is what happened from 18.65 s of RUN-1zT and made its p50 0.0 a measurement
but not a confirmation. So this scorer joins the tap to the gamesrv capture
that produced it and reads, per moving sample, whether the ASYNC copy's
target (+0x9C) equals a SERVER-CHOSEN grant -- a 0x0029 whose point is
neither the client's own click nor its own reported position (a lead). A
verbatim click echo or a zero-lead grant at the report is the client's own
point and following it is not enslavement. The capture-level fraction is
printed beside THE NUMBER, a contaminated capture gets no CONFIRMED verdict,
and --baseline runs the detector's two controls too: the 2026-09-02 baseline
must read FREE and RUN-1zT's 073122 must read ENSLAVED from 18.65 s.

Read-only over JSONLs already on disk: no client, no vault write, stdlib only.
"""
import argparse
import glob
import json
import math
import os
import statistics
import struct
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

# ENSLAVEMENT. "To the unit": the tap reads the client's f32 target and the
# gamesrv capture carries the f32 we sent, so a followed grant matches to
# float precision and 1.0 u is a generous band (RUN-1zT: 0.00 u on 115 of 115
# matched samples). A grant is SERVER-CHOSEN when it is neither the client's
# own last click point (a verbatim echo) nor within LEAD_MIN of its last
# reported position (a zero-lead grant at the report): retail's own leads
# start at ~130 u (ROUTER.md sec.1's 131.1 u minimum part-way waypoint) and
# ours at 520, so 50 separates "where you are" from "where we sent you".
GRANT_EPS = 1.0
LEAD_MIN = 50.0
# Capture-level: above this fraction of moving samples the world-0 number is
# CONTAMINATED and no CONFIRMED verdict is printed. RUN-1zT reads 59.6%;
# the baseline and the 08:46 mouse session read 0.0%; the double-driven
# first attempt reads 3.7% (operator input kept re-seizing the body).
ENSLAVED_FRAC = 0.25
# Per leg: the leg is ENSLAVED above this fraction of its moving samples,
# FREE at zero, MIXED between. RUN-1zT's Q/E/S legs read 100%, its opening
# W 2.3%, its second S 25% (the 18.65 s transition lies inside it).
LEG_ENSLAVED_FRAC = 0.5
# The ONSET is the first SUSTAINED run of enslaved moving samples, not the
# first one: RUN-1zT carries a single matched sample at 8.00 s (the first
# lead firing at the walk's start) and the record's onset is the arrival
# snap at 18.65 s, after which every leg follows. Three consecutive moving
# samples is ~0.3 s at the tap's ~10 Hz -- longer than any blip seen.
SUSTAIN = 3
# A leg needs this many moving samples for a per-leg verdict; below it the
# leg is reported by its travel only.
LEG_MIN_MOVING = 3
# A HELD KEY that moved the body under this many units is the other face of
# the same symptom -- the body parked at a granted endpoint and ignoring the
# key (RUN-1zT's third W: 2.9 u for a 5.0 s hold). Flagged, counted, never
# silently scored as "moved nothing".
HELD_KEY_PARKED_U = 50.0
# The detector's own controls (vault captures), asserted by --baseline.
CONTROL_FREE = "agenttap-20260902T213401"          # zero-lead: 0 of 130
CONTROL_ENSLAVED = "agenttap-20260903T073122"      # RUN-1zT: 115 of 193
# The onset on the TAP's clock (head t0 = 07:31:22). sec.1z-u.3 dated the
# arrival snap 18.65 s on the GAMESRV recorder's clock, which starts ~1.0 s
# earlier; the tap shows the body land on the 14.7 s lead's endpoint with
# v = 0 and an infinite target at 17.69 s, and follow the next lead from
# 17.77 s. Same instant, two clocks -- say which axis when quoting.
CONTROL_ENSLAVED_FIRST_T = 17.77


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


def load_gamesrv(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def grants(gamesrv_rows):
    """Every player 0x0029 the server sent, in order, classified against the
    client's OWN last click (decoded 0x003E) and last report (0x003D/0x0047)
    before it: `own-click` (a verbatim echo), `at-report` (a zero-lead grant
    at the reported point), or `server-chosen` (a lead or a routed waypoint
    -- a point the client did not propose). The point is decoded from the
    row's own plaintext bytes, never from the label's rounded text: the
    match is to the unit."""
    out = []
    last_click = None
    last_rep = None
    for r in gamesrv_rows:
        k = r.get("kind")
        if k == "decoded" and r.get("opcode") == 0x3E:
            try:
                last_click = (float(r["values"][1][0]), float(r["values"][1][1]))
            except (KeyError, IndexError, TypeError, ValueError):
                pass
        elif k == "decoded" and r.get("opcode") in (0x3D, 0x47):
            try:
                last_rep = (float(r["values"][1][0]), float(r["values"][1][1]))
            except (KeyError, IndexError, TypeError, ValueError):
                pass
        elif k == "sent" and r.get("opcode") == 0x29:
            try:
                plain = bytes.fromhex(r["plain"])
                _op, aid, x, y, _p1, _p2 = struct.unpack("<HIffHH", plain[:18])
            except (KeyError, ValueError, struct.error):
                continue
            if aid != 1:
                continue
            dest = (x, y)
            lead = None if last_rep is None else math.dist(dest, last_rep)
            if last_click is not None and math.dist(dest, last_click) < GRANT_EPS:
                kind = "own-click"
            elif lead is not None and lead < LEAD_MIN:
                kind = "at-report"
            else:
                kind = "server-chosen"
            out.append({"w": float(r.get("wall_unix", 0.0)), "dest": dest,
                        "kind": kind, "lead": lead,
                        "label": str(r.get("label", ""))})
    return out


def targets(head, rows, aid=1):
    """Per sample: wall time, capture time, the ASYNC copy's walk target
    (+0x9C), its live position and its raw speed."""
    out = []
    for s in rows:
        a = (s.get("agents") or {}).get(str(aid))
        if not a:
            continue
        ay = a.get("async")
        if not ay or "x" not in ay or ay.get("tx") is None:
            continue
        out.append({"w": head["t0"] + s["t"], "t": s["t"],
                    "tgt": (ay["tx"], ay["ty"]),
                    "body": live(ay, s.get("clock1")),
                    "v": math.hypot(ay.get("vx", 0.0), ay.get("vy", 0.0))})
    return out


def enslavement(head, rows, G, aid=1, slack=0.05):
    """Join the drawn body's target to the grants: a moving sample is
    ENSLAVED when its target equals, to GRANT_EPS, a SERVER-CHOSEN grant sent
    at or before it (`slack` covers the two wall clocks' write order). Returns
    the per-sample rows (each with `hit`, the matched grant or None) and the
    capture-level summary."""
    per = targets(head, rows, aid)
    for p in per:
        hit = None
        for g in G:
            if g["w"] <= p["w"] + slack and math.dist(p["tgt"], g["dest"]) < GRANT_EPS:
                hit = g
        p["hit"] = hit
    moving = [p for p in per if p["v"] > 1.0]
    ens = [p for p in moving if p["hit"] is not None
           and p["hit"]["kind"] == "server-chosen"]
    own = [p for p in moving if p["hit"] is not None
           and p["hit"]["kind"] != "server-chosen"]
    frac = len(ens) / len(moving) if moving else 0.0
    first_t, run, run_t = None, 0, None
    for p in moving:
        if p["hit"] is not None and p["hit"]["kind"] == "server-chosen":
            run += 1
            run_t = p["t"] if run == 1 else run_t
            if run >= SUSTAIN:
                first_t = run_t
                break
        else:
            run, run_t = 0, None
    return per, {"moving": len(moving), "enslaved": len(ens), "own": len(own),
                 "frac": frac, "first_t": first_t,
                 "first_any_t": (ens[0]["t"] if ens else None),
                 "grants": len(G),
                 "server_chosen": sum(1 for g in G if g["kind"] == "server-chosen"),
                 "verdict": ("ENSLAVED" if frac >= ENSLAVED_FRAC
                             else "FREE" if not ens else "MIXED")}


def leg_verdicts(per, walk):
    """Per harness leg: hold, body travel, the free-walk expectation
    (median moving speed x hold), and the enslaved fraction of its moving
    samples -> FREE / MIXED / ENSLAVED. An enslaved body's travel is capped
    at the granted leg whatever the hold (RUN-1zT: Q 509 u for a 3 s hold at
    216 u/s, S 504 u for 4 s at 190)."""
    out = []
    for w in walk:
        a0, a1 = w.get("started_unix"), w.get("ended_unix")
        if a0 is None or a1 is None:
            continue
        seg = [p for p in per if a0 <= p["w"] <= a1]
        mv = [p for p in seg if p["v"] > 1.0]
        bt = travel([p["body"] for p in seg]) if len(seg) > 1 else 0.0
        vmed = sorted(p["v"] for p in mv)[len(mv) // 2] if mv else 0.0
        ens = sum(1 for p in mv if p["hit"] is not None
                  and p["hit"]["kind"] == "server-chosen")
        frac = ens / len(mv) if mv else 0.0
        parked = (w.get("kind") == "key" and (a1 - a0) >= 1.0
                  and bt < HELD_KEY_PARKED_U)
        out.append({"kind": w.get("kind", ""), "key": str(w.get("key", "")),
                    "start": a0,
                    "hold": a1 - a0, "travel": bt, "expected": vmed * (a1 - a0),
                    "moving": len(mv), "enslaved": ens, "frac": frac,
                    "parked": parked,
                    "verdict": ("-" if len(mv) < LEG_MIN_MOVING else
                                "ENSLAVED" if frac >= LEG_ENSLAVED_FRAC
                                else "FREE" if ens == 0 else "MIXED")})
    return out


def find_gamesrv(head, rows):
    """The gamesrv capture that produced this tap: the newest
    authsrv-*-c1.jsonl whose wall span overlaps the tap's. None if the vault
    cannot be resolved or nothing overlaps -- the caller then SAYS SO."""
    if not rows:
        return None
    t_lo, t_hi = head["t0"], head["t0"] + rows[-1]["t"]
    try:
        import vaultpath
        d = vaultpath.vault_path("captures", "gamesrv")
    except Exception:                              # noqa: BLE001
        return None
    best = None
    for p in sorted(glob.glob(os.path.join(d, "authsrv-*-c1.jsonl"))):
        w0 = w1 = None
        try:
            with open(p, encoding="utf-8") as fh:
                for line in fh:
                    try:
                        r = json.loads(line)
                    except ValueError:
                        continue
                    wu = r.get("wall_unix")
                    if wu is None:
                        continue
                    w0 = wu if w0 is None else w0
                    w1 = wu
        except OSError:
            continue
        if w0 is None or w1 < t_lo or w0 > t_hi:
            continue
        best = p
    return best


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


def score(path, legs=None, quiet=False, grants_path=None):
    head, rows = load(path)
    p = series(head, rows, 1)
    if not p:
        raise SystemExit(f"{path}: no agent-1 samples with both copies")
    # THE ENSLAVEMENT JOIN, before the number is printed: a contaminated
    # capture must say so on the same screen as its p50.
    gpath = grants_path or find_gamesrv(head, rows)
    ens = None
    per = None
    if gpath is not None and os.path.exists(gpath):
        per, ens = enslavement(head, rows, grants(load_gamesrv(gpath)))

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
        print()
        print("ENSLAVEMENT  -- who follows whom (sec.1z-u.3: world-0 vs body "
              "cannot tell)")
        if ens is None:
            print("  ** NOT MEASURED: no gamesrv capture overlaps this tap "
                 "(pass --grants <authsrv-*-c1.jsonl>). Without the grants "
                 "the number above is a measurement, never a confirmation.")
        else:
            print(f"  grants joined               {os.path.basename(gpath)}: "
                  f"{ens['grants']} player 0x0029, {ens['server_chosen']} "
                  f"server-chosen")
            print(f"  body target == server-chosen grant (to {GRANT_EPS:.0f} u) on "
                  f"{ens['enslaved']} of {ens['moving']} moving samples "
                  f"({100.0 * ens['frac']:.1f}%)")
            if ens["first_t"] is not None:
                print(f"  onset (first {SUSTAIN} consecutive)  t={ens['first_t']:.2f} s"
                      + (f"   (first single match t={ens['first_any_t']:.2f} s)"
                         if ens["first_any_t"] != ens["first_t"] else ""))
            elif ens["first_any_t"] is not None:
                print(f"  no sustained run; first single match t="
                      f"{ens['first_any_t']:.2f} s")
            print(f"  body target == the client's OWN point (click / report) on "
                  f"{ens['own']} -- following its own point is not enslavement")
            print(f"  verdict                     {ens['verdict']}"
                  + (f"   (>= {100.0 * ENSLAVED_FRAC:.0f}% contaminates)"
                     if ens["verdict"] == "ENSLAVED" else ""))

    if legs:
        print()
        print("PER LEG  (A and D TURN IN PLACE in Guild Wars -- Q/E strafe)")
        rep = json.load(open(legs, encoding="utf-8"))
        lv = {round(x["start"], 3): x
              for x in (leg_verdicts(per, rep.get("walk", [])) if per else [])}
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
            x = lv.get(round(a0, 3))
            ens_col = ("" if x is None or x["verdict"] == "-" else
                       f"   {x['verdict']:8s} {100.0 * x['frac']:5.1f}% "
                       f"(free walk {x['expected']:6.0f} u)")
            if x is not None and x["parked"]:
                flag = (f"  <-- HELD KEY, BODY PARKED ({bt:.0f} u in "
                        f"{x['hold']:.1f} s): the key was ignored")
            print(f"  {w.get('kind',''):5s} {str(w.get('key','')):2s} "
                  f"body {bt:7.1f} u   world-0 {wt:7.1f} u   "
                  f"sep {min(sep):6.1f}..{max(sep):6.1f}{ens_col}{flag}")

    enemy = series(head, rows, 10)
    if enemy and not quiet:
        e_own = [math.dist(r["w0"], r["body"]) for r in enemy]
        em, _, ep90, emx = q(e_own)
        print()
        print("ENEMY CONTROL (agent 10, its own two copies -- must stay small)")
        print(f"  world-0 vs drawn            p50 {em:7.1f}"
              f"              p90 {ep90:7.1f}  max {emx:8.1f}")

    return {"live": q(live_sep), "raw": q(raw_sep),
            "travel": body_travel, "moving": len(moving),
            "enslavement": ens, "grants_path": gpath}


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
    ap.add_argument("--grants", default=None,
                    help="the gamesrv capture (authsrv-*-c1.jsonl) that "
                         "produced this tap, for the enslavement join; "
                         "default: the newest one whose wall span overlaps")
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
        else:
            print(f"[FAIL] control does NOT reproduce. Expected live "
                  f"{BASELINE_LIVE} and raw {BASELINE_RAW}; got live "
                  f"({m:.1f}, {mx:.1f}) and raw ({rm:.1f}, {rmx:.1f}).")
        # THE DETECTOR'S OWN CONTROLS: the same baseline must read FREE, and
        # RUN-1zT's registered arm must read ENSLAVED from 18.65 s -- a
        # detector that cannot find the known contamination cannot clear a
        # new run of it.
        e = r.get("enslavement")
        ok_free = e is not None and e["verdict"] == "FREE" and e["enslaved"] == 0
        print(f"[{'PASS' if ok_free else 'FAIL'}] the zero-lead baseline reads "
              f"FREE: "
              + ("no gamesrv capture joined" if e is None else
                 f"{e['enslaved']} of {e['moving']} moving samples enslaved, "
                 f"{e['server_chosen']} server-chosen grants"))
        import vaultpath
        cp = os.path.join(vaultpath.vault_path("research", "animref"),
                          CONTROL_ENSLAVED + ".jsonl")
        ok_ens = False
        if os.path.exists(cp):
            print()
            r2 = score(cp, quiet=True)
            e2 = r2.get("enslavement")
            ok_ens = (e2 is not None and e2["verdict"] == "ENSLAVED"
                      and e2["first_t"] is not None
                      and abs(e2["first_t"] - CONTROL_ENSLAVED_FIRST_T) < 0.3)
            print(f"[{'PASS' if ok_ens else 'FAIL'}] RUN-1zT's registered arm "
                  f"reads ENSLAVED from {CONTROL_ENSLAVED_FIRST_T} s (tap clock; "
                  f"18.65 s on the gamesrv clock): "
                  + ("no gamesrv capture joined" if e2 is None else
                     f"{e2['verdict']}, {e2['enslaved']} of {e2['moving']} "
                     f"({100.0 * e2['frac']:.1f}%), first at "
                     f"t={e2['first_t']}"))
        else:
            print(f"[FAIL] the enslaved control is missing: {cp}")
        return 0 if (ok and ok_free and ok_ens) else 1

    path = a.capture or newest()
    r = score(path, legs=a.legs, grants_path=a.grants)
    m = r["live"][0]
    e = r.get("enslavement")

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
    if e is None:
        print(f"  ** MEASURED, NOT CONFIRMED: p50 {m:.1f} u, but no gamesrv "
              f"capture was joined so enslavement is unknown (sec.1z-u.3). "
              f"Pass --grants.")
        return 3
    if e["verdict"] == "ENSLAVED":
        print(f"  ** MEASURED, CONTAMINATED: p50 {m:.1f} u with the drawn body "
              f"following server-chosen grants on {100.0 * e['frac']:.1f}% of "
              f"moving samples (onset t="
              f"{(e['first_t'] if e['first_t'] is not None else e['first_any_t']):.2f} s). World-0 vs "
              f"body cannot tell who follows whom here; this is not a "
              f"confirmation of anything. Look for the lead that matured "
              f"unanswered (sec.1z-u.3).")
        return 3
    if m < CONFIRM_P50:
        print(f"  CONFIRMED: p50 {m:.1f} u"
              + (" (body FREE: no server-chosen grant was followed)."
                 if e["verdict"] == "FREE" else
                 f" (body MIXED: {e['enslaved']} of {e['moving']} moving "
                 f"samples followed a server-chosen grant -- under the "
                 f"{100.0 * ENSLAVED_FRAC:.0f}% bar, say so when quoting)."))
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
