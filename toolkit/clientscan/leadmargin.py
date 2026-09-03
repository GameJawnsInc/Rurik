#!/usr/bin/env python3
"""MOVECODE-1z-ab: the keyboard lead's LENGTH, measured rather than argued.

The question, as sec.1z-u.4 left it: should `KBD_SYNC_LEAD` stay at 520 u
(read off the client's own ~515 u report chord) or move to retail's 766 u
(the client's own proposal, a fixed ~768 u ray on every movement type), "on
maturation margin -- 766 leaves ~250 u over the report chord where 520
leaves 5"?  This module holds the three measurements that answer it, each
an extractor over the owner's own captures, so the argument in
studies/movecode/FINDINGS.md sec.1z-ab can be re-run rather than re-read:

  1. cruise_chords / chord_census -- the client's 0x003D DISTANCE trigger,
     measured as the chord between consecutive same-heading reports at
     cruise cadence, with the teleports filtered OUT (a 6,182 u "chord" in
     21.8 s is a warp, not a report) and the tail SPLIT: a chord a little
     over the trigger is a late report (a frame hitch), a chord of 1.4-12
     triggers at cruise speed is a body that walked without reporting --
     the sec.0.11 lock regime's own signature, visible in the server log
     alone.
  2. lead_legs -- on an agenttap capture, per world-0 leg: did the sync
     copy reach its granted point before the next grant re-aimed it (a
     MATURATION), how far from the point was it when the re-aim landed, and
     how far from the drawn body.  Positions are the client's own
     AgAgent::position_at rule (w0score.live: clamp first, then dead-reckon
     from +0x78, which is the leg ORIGIN and not the live point).
  3. bounds -- the inequalities the length must satisfy, from the server's
     own constants: the copy must not mature inside the hold window the
     1z-y re-bake bounds (floor + one tick), it must outlast the trigger,
     and the hold's own residual (how far two copies can separate before
     the re-bake lands, against gate 1's 299.33 u) is stated for the
     cross-family and the same-family turn.

No client launch, no static reads.  Read-only over the vault; the vault is
found through vaultpath, never a relative walk.
"""

import argparse
import collections
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))                      # toolkit/

import w0score                                                 # noqa: E402

# The client's 0x003D distance trigger: ~512 u (studies/movement/
# FINDINGS.md:1219, REALFIX-W2), with the measured in-band spread below.
TRIGGER = 512.0
# Where a same-heading cruise chord lands when the trigger fires: 1,126 of
# the 1,160 corpus chords at or over 505 u sit in [505, 518) -- the client
# tests the distance once per frame, so the excess over the trigger is at
# most a frame's motion. (The 225 same-heading pairs UNDER 505 u are reports
# a sub-degree heading nudge fired, not the trigger; counted as `below`.)
IN_BAND = (505.0, 518.0)
# A chord over the band but under this many triggers is a LATE report (a
# frame hitch of 13-52 u = 45-180 ms at 288 u/s); at or over it the body
# walked a whole further chord without reporting, which a free body never
# does -- the lock regime (sec.0.11 stage 2, "releases go unreported").
HITCH_MAX_RATIO = 1.15
# Speed families, the client's own (studies/movement/FINDINGS.md:1201; the
# agenttap velocity fields hold exactly these three, 1z-ab).
RUN, BACK, SIDE = 288.0, 190.0, 216.0
FAMILY = {1: RUN, 2: RUN, 3: RUN, 4: BACK, 5: BACK, 6: BACK, 7: SIDE, 8: SIDE}
# Gate 1 of the client's snap test (agtrack_guard.GATE1_RED).
GATE1 = 299.332591
# The reprieve radius (agtrack_mirror.R_MATCH).
R_MATCH = 100.0

# The lead-ON agenttap captures (vault/research/animref), by stamp: label
# and the tap-clock second after which the capture is contaminated (the
# enslavement onset w0score measured, sec.1z-x) or None.  The 07:29 attempt
# is double-driven (RUN-1zT.md) and is not a margin substrate.
LEAD_ON_TAPS = (
    ("agenttap-20260903T073122", "RUN-1zT, scripted, --kbd-lead 520", 17.77),
    ("agenttap-20260903T084632", "RUN-FEEL, operator, lead ON", None),
)


def read_rows(path):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


# ---------------------------------------------------------------------------
# 1. the report chord
# ---------------------------------------------------------------------------

def cruise_chords(paths, max_speed=320.0, min_gap=1.0, cos_tol=0.9998):
    """Consecutive player 0x003D pairs -- same movementType (non-zero), same
    heading (cosine over `cos_tol`), gap >= `min_gap` s, implied speed <=
    `max_speed` u/s -- as chords.  A 0x0047 between two reports breaks the
    pair.  The speed bar is what excludes the teleports: a report chord is
    walked, a warp is not."""
    out = []
    for p in paths:
        prev = None
        for r in read_rows(p):
            if r.get("kind") != "decoded":
                continue
            op = r.get("opcode")
            if op == 0x47:
                prev = None
                continue
            if op != 0x3D:
                continue
            try:
                v = r["values"]
                pos = (float(v[1][0]), float(v[1][1]))
                vec = (float(v[3][0]), float(v[3][1]))
                mt = int(v[4])
                t = float(r["t"])
            except (KeyError, IndexError, TypeError, ValueError):
                continue
            m = math.hypot(vec[0], vec[1])
            if prev is not None and prev["mt"] == mt and mt != 0 \
                    and m > 1.0 and prev["m"] > 1.0:
                dot = (vec[0] * prev["vec"][0] + vec[1] * prev["vec"][1]) \
                    / (m * prev["m"])
                d = math.dist(pos, prev["pos"])
                dt = t - prev["t"]
                if dot > cos_tol and dt >= min_gap and d / dt <= max_speed:
                    out.append({"d": d, "dt": dt, "mt": mt, "path": p,
                                "t": t, "ratio": d / TRIGGER,
                                "speed": d / dt})
            prev = {"t": t, "pos": pos, "vec": vec, "m": m, "mt": mt}
    return out


def _q(vals, frac):
    v = sorted(vals)
    if not v:
        return None
    return v[min(int(frac * len(v)), len(v) - 1)]


def chord_census(chords):
    """Per-type stats, the in-band excess histogram (1 u bins over the
    trigger), the in-band ceiling, and the tail split hitch / silent."""
    per_type = {}
    by = collections.defaultdict(list)
    for c in chords:
        by[c["mt"]].append(c["d"])
    for mt, v in sorted(by.items()):
        per_type[mt] = {"n": len(v), "p50": _q(v, .5), "p90": _q(v, .9),
                        "p99": _q(v, .99), "max": max(v)}
    lo, hi = IN_BAND
    in_band = [c for c in chords if lo <= c["d"] < hi]
    hist = collections.Counter(int(math.floor(c["d"] - TRIGGER))
                               for c in in_band)
    ceiling = max((c["d"] for c in in_band), default=None)
    tail = sorted((c for c in chords if c["d"] >= hi), key=lambda c: c["d"])
    hitch = [c for c in tail if c["ratio"] < HITCH_MAX_RATIO]
    silent = [c for c in tail if c["ratio"] >= HITCH_MAX_RATIO]
    below = [c for c in chords if c["d"] < lo]
    return {"n": len(chords), "per_type": per_type, "in_band": len(in_band),
            "hist": dict(sorted(hist.items())), "ceiling": ceiling,
            "below": len(below), "hitch": hitch, "silent": silent}


# ---------------------------------------------------------------------------
# 2. the copy's legs on a tap
# ---------------------------------------------------------------------------

def lead_legs(tap_path, min_len=300.0, until=None, aid=1, at_dest=2.0):
    """Per world-0 leg (one granted point, from the sync copy's own target
    fields) on an agenttap capture: length, duration, whether the LIVE copy
    reached the point before the next grant (matured), how long it sat
    there, the distance still to go when the re-aim landed, and the live
    separation from the drawn body.  Legs shorter than `min_len` (zero-lead
    grants, echoes, clipped stubs) are dropped; `until` cuts the capture at
    a tap-clock second (a contaminated tail)."""
    head, rows = w0score.load(tap_path)
    ser = w0score.series(head, rows, aid)
    dest_at = {}
    for s in rows:
        a = (s.get("agents") or {}).get(str(aid))
        if a and a.get("sync"):
            tx, ty = a["sync"].get("tx"), a["sync"].get("ty")
            if (tx is not None and ty is not None
                    and math.isfinite(tx) and math.isfinite(ty)):
                dest_at[s["t"]] = (tx, ty)
    legs, cur = [], None
    for p in ser:
        d = dest_at.get(p["t"])
        if cur is None or d != cur["dest"]:
            if cur is not None:
                legs.append(cur)
            cur = {"dest": d, "t0": p["t"], "start": p["w0"], "S": []}
        cur["S"].append(p)
    if cur is not None:
        legs.append(cur)
    out = []
    for lg in legs:
        if lg["dest"] is None:
            continue
        if until is not None and lg["t0"] > until:
            continue
        L = math.dist(lg["start"], lg["dest"])
        if L < min_len:
            continue
        S = lg["S"]
        at = [p for p in S if math.dist(p["w0"], lg["dest"]) < at_dest]
        seps = [math.dist(p["w0"], p["body"]) for p in S]
        v0 = collections.Counter(int(round(p["v0"])) for p in S)
        vb = collections.Counter(int(round(p["vbody"])) for p in S)
        out.append({
            "t0": lg["t0"], "len": L, "dur": S[-1]["t"] - S[0]["t"],
            "dest": lg["dest"], "samples": len(S),
            "matured": bool(at), "park_s": (S[-1]["t"] - at[0]["t"]) if at else 0.0,
            "at_dest_samples": len(at),
            "left": math.dist(S[-1]["w0"], lg["dest"]),
            "sep_p50": _q(seps, .5), "sep_max": max(seps), "sep_end": seps[-1],
            "v0": dict(v0), "vbody": dict(vb),
        })
    return out


def legs_summary(legs):
    return {"n": len(legs),
            "matured": sum(1 for l in legs if l["matured"]),
            "park_max_s": max((l["park_s"] for l in legs), default=0.0),
            "left_min": min((l["left"] for l in legs), default=None),
            "sep_end_max": max((l["sep_end"] for l in legs), default=None)}


# ---------------------------------------------------------------------------
# 3. the bounds
# ---------------------------------------------------------------------------

def bounds(lead=520.0, floor=0.5, tick=0.05, gate1=GATE1, trigger=TRIGGER,
           ceiling=None, run=RUN, back=BACK):
    """The inequalities, each with its two sides so a caller can print the
    margin and a test can refuse a constant that breaks one.

    hold_window     the longest a rate-refused re-aim waits under 1z-y's
                    hold: the floor plus one server tick.
    no_mature_in_hold   lead > run * hold_window -- a copy re-aimed at the
                    re-bake has not reached its old point meanwhile.
    outlasts_trigger    lead > trigger (and > the measured in-band ceiling
                    when given) -- the copy is still walking when the next
                    chord report re-aims it, so the arrival tick never fires
                    in cruise.
    hold_residual_cross / hold_residual_same   how far the two copies can be
                    apart when the re-bake's grant is EVALUATED, for a turn
                    across families (288 + 190) and within the forward
                    family (2 x 288); each against gate 1.  The lead's
                    length does not enter either -- they are the hold's.
    order_walk      the most a lead can move the body if it is ever walked
                    as an order: the lead itself, by construction.
    """
    hw = floor + tick
    out = {
        "hold_window_s": hw,
        "no_mature_in_hold": (lead, run * hw, lead > run * hw),
        "outlasts_trigger": (lead, trigger, lead > trigger),
        "hold_residual_cross": ((run + back) * hw, gate1, (run + back) * hw < gate1),
        "hold_residual_same": (2 * run * hw, gate1, 2 * run * hw < gate1),
        "order_walk_u": lead,
    }
    if ceiling is not None:
        out["outlasts_ceiling"] = (lead, ceiling, lead > ceiling)
    return out


# ---------------------------------------------------------------------------
# printing + CLI
# ---------------------------------------------------------------------------

def print_census(c):
    print(f"CRUISE CHORDS  n={c['n']} (same heading, gap >= 1 s, <= 320 u/s)")
    for mt, s in c["per_type"].items():
        print(f"  type {mt}: n={s['n']:4d} p50 {s['p50']:6.1f} p90 {s['p90']:6.1f} "
              f"p99 {s['p99']:6.1f} max {s['max']:6.1f}")
    print(f"  in band [{IN_BAND[0]:.0f}, {IN_BAND[1]:.0f}): {c['in_band']}  "
          f"below: {c['below']}  ceiling {c['ceiling']:.1f} u")
    print("  excess over the trigger, 1 u bins:",
          " ".join(f"{k:+d}:{v}" for k, v in c["hist"].items()))
    print(f"  TAIL >= {IN_BAND[1]:.0f}: {len(c['hitch'])} late reports (hitch, "
          f"< {HITCH_MAX_RATIO} triggers), {len(c['silent'])} silent walks "
          f"(>= {HITCH_MAX_RATIO} triggers)")
    for h in c["hitch"]:
        print(f"    hitch  {h['d']:6.1f} u {h['dt']:5.2f} s type {h['mt']} "
              f"{os.path.basename(h['path'])} t={h['t']:.1f}")
    for h in c["silent"]:
        print(f"    silent {h['d']:6.1f} u {h['dt']:5.2f} s  {h['ratio']:5.2f} triggers "
              f"{os.path.basename(h['path'])} t={h['t']:.1f}")


def print_legs(label, legs):
    s = legs_summary(legs)
    print(f"LEAD LEGS  {label}: {s['n']} legs >= 300 u, matured before the "
          f"re-aim {s['matured']}, longest park {s['park_max_s']:.2f} s")
    for l in legs:
        fam0 = "/".join(str(k) for k in sorted(l["v0"]))
        famb = "/".join(str(k) for k in sorted(l["vbody"]))
        print(f"  t={l['t0']:6.2f} L={l['len']:6.1f} dur {l['dur']:5.2f}s "
              f"{'MATURED park %.2fs' % l['park_s'] if l['matured'] else 'walking'}"
              f"  left {l['left']:6.1f} u  sep p50 {l['sep_p50']:6.1f} "
              f"max {l['sep_max']:6.1f} end {l['sep_end']:6.1f}  "
              f"copy {fam0} body {famb} u/s")


def print_bounds(b):
    print(f"BOUNDS  (hold window {b['hold_window_s']:.2f} s)")
    for k in ("no_mature_in_hold", "outlasts_trigger", "outlasts_ceiling"):
        if k not in b:
            continue
        a, c, ok = b[k]
        print(f"  {k:22s} {a:7.1f} > {c:7.1f}  {'holds' if ok else 'FAILS'}")
    for k in ("hold_residual_cross", "hold_residual_same"):
        a, c, ok = b[k]
        print(f"  {k:22s} {a:7.1f} < {c:7.1f}  "
              f"{'covered by the hold' if ok else 'NOT covered: the hold residual'}")
    print(f"  order_walk_u           {b['order_walk_u']:7.1f}  (the lead, by construction)")


def vault_gamesrv():
    import vaultpath
    return sorted(glob.glob(os.path.join(
        vaultpath.vault_path("captures", "gamesrv"), "authsrv-*-c1.jsonl")))


def vault_tap(stamp):
    import vaultpath
    return os.path.join(vaultpath.vault_path("research", "animref"),
                        stamp + ".jsonl")


def check_corpus(lead=520.0):
    """The reproduction the FINDINGS section rests on, as floors and
    signatures rather than exact counts (the corpus grows).  Returns the
    exit code: 0 reproduced, 3 not."""
    ok = True
    c = chord_census(cruise_chords(vault_gamesrv()))
    b = bounds(lead, ceiling=c["ceiling"])
    print_census(c)
    print_bounds(b)

    def say(cond, msg):
        nonlocal ok
        print(f"  [{'OK' if cond else 'NOT REPRODUCED'}] {msg}")
        ok = ok and cond
    say(c["in_band"] >= 1126, f"in-band cruise chords >= 1126 (got {c['in_band']})")
    say(c["ceiling"] is not None and 517.0 <= c["ceiling"] < lead,
        f"in-band ceiling in [517, {lead:.0f}) (got {c['ceiling']})")
    say(len(c["hitch"]) >= 6 and all(h["d"] < 600 for h in c["hitch"]),
        f"hitch tail >= 6, all under 600 u (got {len(c['hitch'])})")
    say(len(c["silent"]) >= 28, f"silent-walk tail >= 28 (got {len(c['silent'])})")
    for stamp, label, until in LEAD_ON_TAPS:
        p = vault_tap(stamp)
        if not os.path.exists(p):
            say(False, f"{stamp} present")
            continue
        legs = lead_legs(p, until=until)
        print_legs(label, legs)
        s = legs_summary(legs)
        say(s["park_max_s"] <= 0.05,
            f"{stamp}: no lead leg parked longer than one tap sample "
            f"(longest {s['park_max_s']:.2f} s)")
        if stamp.endswith("073122"):
            say(s["n"] == 3 and s["left_min"] is not None and s["left_min"] < 1.0,
                f"RUN-1zT: 3 cruise legs before the onset, one at its point "
                f"when the re-aim landed (min left {s['left_min']})")
    return 0 if ok else 3


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--gamesrv", nargs="*", help="gamesrv jsonl files "
                    "(default: the vault's captures/gamesrv corpus)")
    ap.add_argument("--tap", action="append", default=[],
                    help="an agenttap capture to read lead legs from "
                         "(repeatable; default: the lead-ON captures)")
    ap.add_argument("--until", type=float, default=None,
                    help="cut every --tap at this tap-clock second")
    ap.add_argument("--lead", type=float, default=520.0,
                    help="the lead length to state the bounds for")
    ap.add_argument("--check", action="store_true",
                    help="reproduce sec.1z-ab's corpus figures; exit 3 if not")
    a = ap.parse_args(argv)
    if a.check:
        return check_corpus(a.lead)
    paths = a.gamesrv if a.gamesrv else vault_gamesrv()
    c = chord_census(cruise_chords(paths))
    print_census(c)
    print()
    if a.tap:
        for p in a.tap:
            print_legs(os.path.basename(p), lead_legs(p, until=a.until))
    else:
        for stamp, label, until in LEAD_ON_TAPS:
            p = vault_tap(stamp)
            if os.path.exists(p):
                print_legs(label, lead_legs(p, until=until))
            else:
                print(f"LEAD LEGS  {label}: {p} missing")
    print()
    print_bounds(bounds(a.lead, ceiling=c["ceiling"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
