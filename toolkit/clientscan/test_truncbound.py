#!/usr/bin/env python3
"""The truncated clock offset's error, measured against the float stamp.

    python toolkit/clientscan/test_truncbound.py

WHAT THIS IS REALLY CHECKING. Before REALFIX-T1 (2026-08-21) a server capture
stamped each row with `wall`, the time truncated to the second, and
`movesync.offset_detail` estimates the wire<->movetap clock offset from those
rows as max(floor(unix) - t). Its printed line called the max - min of those
per-row offsets the "residual", ~1.000 s = 288 u at run speed, and
studies/movement/REALFIX.md section 2.1 read that as the clock slop on every
pre-T1 pairing. It is the other way round. Each row gives the true offset minus
the fraction of its second, so with a steady clock the truth lies in
[max, min + 1): a spread NEAR one second is a TIGHT bound on the max, and the
error bound is 1 - spread, not spread.

Every capture written since T1 carries both stamps, so the truncated estimator
can be scored against the float one on real rows. That scan was a scratch
script until this file. It is the evidence behind `offset_line`'s truncated
arm, which since 2026-09-23 prints `bound` (how far above the offset the truth
can lie) instead of the spread, and refuses a capture whose stamps show the
clock moved.

PREDICTION, written before this file's scan ran (2026-09-23), kept with its
outcome:
  P1 PLACEMENT: the truncated max sits in [-25 ms, +0.1 ms] of the float
     median on every both-stamp capture. HELD: -17.262 to -0.105 ms, never
     above.
  P2 THE BOUND: median - max <= 1 - spread (+0.1 ms) wherever spread <= 1.
     REFUTED as written, on 191 of 511 captures by up to 1.475 ms, and 36 have
     a spread ABOVE 1 s while the max stays below the truth. The cause:
     `time.gmtime()` reads GetSystemTimeAsFileTime, a clock that advances once
     per timer interrupt and lags `time.time()` by up to a tick, so a `wall`
     second rolls over LATE. The bound is 1 - spread + one tick
     (`movesync.WALL_TICK`, the coarsest, 15.625 ms), and that holds on every
     capture by at least 14.150 ms (§2).
  P3 DRIFT: the float offset's lower envelope moves <= 20 ppm across a
     capture. HELD, by far: the first and last tenth of rows differ by at most
     0.024 ms on any capture.
  P4 KNOWN-BAD ARMS: a MEAN estimator sits 0.4-0.6 s below the truth, so the
     bound check goes red on every capture; a planted 50 ms monotone drift
     lifts the max above the float median on most. HELD (§2, both counted).

THE KNOWN-BAD ARMS, and why each is here. A bound that no estimator could
break is not a bound. §1 breaks it on synthetic rows and §2 on every real
capture: the mean (the estimator the max replaced) must fail the bound on all
of them, and a planted drift -- added to both families, which is exactly
perf_counter running fast against the system clock -- must fail the
steady-clock check on all of them and push the max above the truth on most.
§3's positive control is real: the two pre-T1 captures the new line refuses
show their step in the stamps alone, with no float stamp to lean on.

WHAT IT DOES NOT CHECK. A pre-T1 capture has no float stamp, so §3 can only
say which of them the bound applies to; that the bound is RIGHT on them is the
inference from §2, on the same `Recorder.event` code path. `WALL_TICK` is the
coarsest interval Windows reports on this box, not a property of the capture:
the largest late rollover seen in a capture is 1.474 ms.

§4, ADDED LATER THE SAME DAY: WHAT THE BOUND CHANGES. REALFIX-L1 (FINDINGS,
2026-08-21) registered P2's separation at p50 <= 150 u and p90 <= 520 u, got
267.5 / 523.0, and recorded UNDECIDABLE-leaning-miss on "a 1.00 s spread, worth
up to ~288 u on any single pairing". §4 re-scores it through movesync's own
pair() and score() at every offset the corrected bound admits, and with movetap
interpolated to the instant (the nearest-sample phase removed, REALFIX 2.2's
transport term added). Its prediction, written before it ran, and the outcome:
  (1) the published figures reproduce first. HELD, exactly.
  (2) arm B's p50 stays within +/-15 u of 267.5 across the bound, so the p50
     miss is DECIDED. HELD: 267.5 at every offset, 256.1-262.4 interpolated.
  (3) arm B's p90 straddles 520 under nearest-sample pairing, now because of
     the sample phase and not the clock. HELD: 515.8-523.0; interpolated it is
     514.4-518.6, under 520 at every offset by less than the interpolation's
     own error -- AT the bound, leaning met.
  (4) arm A's p50 >= 800 holds across its bound. HELD, 4402.4 unmoved.
  (5) no offset in the bound mints a hard row. HELD.

Sections: §1 synthetic, bare machine (the floor). §2 and §3 read the vault's
server captures through `movesync.load_wire_reports`, the shipped loader, and
declare a skip without it. Exact figures are asserted on a PINNED population
(capture stamps up to `CUT`, all closed files), so they reproduce; the
per-capture properties are asserted on every capture, because a new one that
breaks them is a finding, not noise.
"""
import bisect
import glob
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks     # noqa: E402
import movesync   # noqa: E402
import vaultpath  # noqa: E402

# MEASURED 2026-09-23 off real green runs: 25 checks with the vault present,
# 11 with `RURIK_VAULT` pointed at an empty directory (2 declared skips). 11 is
# the bare-machine core, §1, and is the floor. Later that day §4 (the
# REALFIX-L1 re-score) took the vaulted run to 31; it needs the vault, so the
# floor holds.
LEDGER = checks.Ledger("the truncated offset's error is 1 - spread + a tick, "
                       "not the spread", floor=11)
check = checks.adopt(LEDGER)

TICK = movesync.WALL_TICK
MS = 1000.0
# The pinned population: every server capture whose stamp is at or before this
# one. The newest capture when it was measured, closed minutes before (another
# session was writing captures at the time, so the corpus grows past it).
CUT = "20260923T154308"
STAMP = re.compile(r"authsrv-(\d{8}T\d{6})-c\d+\.jsonl$")
MIN_ROWS = 50
# Planted defects for the known-bad arms.
PLANT_DRIFT = 0.050
STEADY_MAX = 0.001          # the steady-clock check: 1 ms end to end
# Block 12 of studies/movement/PROBE-GATEFIRE.md, and the two pre-T1 captures
# whose stamps show a clock step.
BLOCK12 = "authsrv-20260819T145717-c1.jsonl"
STEPPED = ("authsrv-20260810T151946-c1.jsonl",
           "authsrv-20260817T011449-c1.jsonl")
# REALFIX-L1's two arms (studies/movement/FINDINGS.md, 2026-08-21), capture and
# movetap. Its registered claim (REALFIX.md, the P2 block): separation, SYNC vs
# the client's report, P0 p50 >= 800 u; P2 p50 <= 150 u and p90 <= 520 u.
L1_ARMS = (("A (P0 control)", "authsrv-20260821T081744-c1.jsonl",
            "movetap-20260821T081927.jsonl"),
           ("B (P2 --zero-lead)", "authsrv-20260821T082631-c1.jsonl",
            "movetap-20260821T082702.jsonl"))
L1_P50, L1_P90, L1_P0_P50 = 150.0, 520.0, 800.0
# REALFIX.md section 2.2's transport term: a report is the client's position
# when SENT, up to this much before the server stamped it.
TRANSPORT = 0.006
GRID = 400


def stamps(truth, ts, lags=None, step=None):
    """Truncated per-row offsets for rows at server times `ts`.

    The row's clock reads `truth + t` (plus `step(t)` if given), and its `wall`
    is the floor of that minus the coarse clock's lag on that row (`lags`,
    parallel to `ts`): exactly what `floor(gmtime()) - t` gives when gmtime's
    clock lags by that much.
    """
    out = []
    for i, t in enumerate(ts):
        u = truth + t + (step(t) if step else 0.0)
        out.append(math.floor(u - (lags[i] if lags else 0.0)) - t)
    return movesync.WallStamps(out, ())


def row_diffs(walls):
    """Per-row `wall_unix - floor(wall)`, from the two aligned families.

    In [0, 1) on a row read in the same second, >= 1 on a row whose coarse
    second rolled over late (the excess is at least the lag), < 0 if the coarse
    clock ever LED the precise one.
    """
    return [f - g for g, f in zip(walls, walls.unix)]


def envelope_move(unix):
    """Lower envelope of the per-row offsets: last tenth of rows - first."""
    m = max(1, len(unix) // 10)
    return min(unix[-m:]) - min(unix[:m])


def step_split(walls):
    """The first row s at which the rows, in file order, split into two runs
    that are EACH steady (spread <= 1 s + one tick), or None.

    That is what one clock step looks like in the truncated stamps alone: two
    steady regimes, back to back. A lone badly delayed row does not split this
    way (the run holding it is never steady unless it sits at an end), and a
    capture that needs no split was never refused. Needs no float stamp.
    """
    n = len(walls)
    lim = 1.0 + TICK
    pre_ok = [True] * (n + 1)
    hi = lo = None
    for i, g in enumerate(walls):
        hi = g if hi is None else max(hi, g)
        lo = g if lo is None else min(lo, g)
        pre_ok[i + 1] = pre_ok[i] and hi - lo <= lim
    hi = lo = None
    suf_ok = [True] * (n + 1)
    for i in range(n - 1, -1, -1):
        g = walls[i]
        hi = g if hi is None else max(hi, g)
        lo = g if lo is None else min(lo, g)
        suf_ok[i] = suf_ok[i + 1] and hi - lo <= lim
    for s in range(1, n):
        if pre_ok[s] and suf_ok[s]:
            return s
    return None


def pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def section1():
    print("\n1. the arithmetic, on synthetic rows (bare machine)")
    truth = 1_787_000_000.25

    # (a) STEADY, DENSE, EXACT: 200 rows 13.7 ms apart cover the second's phase
    # densely. No lag, no step: the fixed-offset interval [max, min + 1) holds
    # with nothing added, and `bound` is it plus one tick.
    ts = [0.0137 * k for k in range(200)]
    d = movesync.offset_detail(stamps(truth, ts))
    err = truth - d["offset"]
    check(0.0 <= err <= 1.0 - d["spread"] + 1e-9
          and abs(d["bound"] - (1.0 + TICK - d["spread"])) < 1e-12,
          f"a steady clock: the max sits {err * MS:.3f} ms below the truth, "
          f"inside 1 - spread = {(1.0 - d['spread']) * MS:.3f} ms, and "
          f"`bound` is that plus one {TICK * MS:.3f} ms tick "
          f"({d['bound'] * MS:.3f} ms)",
          "the fixed-offset arithmetic every other claim here rests on")
    # 13.7 ms between rows leaves a phase gap of that size: spread 0.9864 s.
    check(0.98 < d["spread"] < 1.0 and err < 0.02,
          f"and the spread is {d['spread']:.6f} s while the error is "
          f"{err * MS:.3f} ms: near one second is the TIGHT case",
          "the old line printed this spread as the residual, 288 u")

    # (b) THE COARSE CLOCK: a row read 0.1 ms after a second boundary while
    # the coarse clock lags 0.4 ms still says the old second. Its offset sits
    # 1.0001 s below the truth, and a row read 0.02 ms past another boundary
    # with the clock caught up sits 0.02 ms below it -- so the spread passes
    # 1 s, and 1 - spread alone is NEGATIVE: a "bound" the truth already
    # violates. One tick covers it. Each row: (whole seconds past the first
    # boundary, fraction of its second at the read, the coarse clock's lag).
    spec = ([(0, 0.00002, 0.00001), (1, 0.0001, 0.0004)]
            + [(1 + k, 0.0137 * k % 1.0, 0.0) for k in range(1, 80)])
    ts_b = [(math.ceil(truth) - truth) + s + frac for s, frac, _l in spec]
    d_b = movesync.offset_detail(
        stamps(truth, ts_b, lags=[lag for _s, _f, lag in spec]))
    err_b = truth - d_b["offset"]
    check(d_b["spread"] > 1.0 and err_b > 1.0 - d_b["spread"]
          and 0.0 <= err_b <= d_b["bound"],
          f"a coarse clock 0.4 ms late: spread {d_b['spread']:.6f} s, so "
          f"1 - spread is {(1.0 - d_b['spread']) * MS:+.3f} ms and the error "
          f"({err_b * MS:.3f} ms) is outside it -- and inside `bound` "
          f"({d_b['bound'] * MS:.3f} ms)",
          "this is P2's refutation in miniature: 36 real captures have a "
          "spread above 1 s and the max below the truth")

    # (c) A STEP: the clock jumps 0.4 s half way. Both halves cover nearly the
    # whole second, so the spread is ~1.4 s and no steady-clock bound exists.
    # The line's "moved by at least" is a LOWER bound on the step: it must not
    # exceed the 0.4 s planted, and the phase gaps and the tick keep it under.
    ts_c = [0.0137 * k for k in range(600)]
    d_c = movesync.offset_detail(stamps(
        truth, ts_c, step=lambda t: 0.4 if t > ts_c[-1] / 2 else 0.0))
    line_c = movesync.offset_line(d_c)
    check(d_c["bound"] < 0.0 and "NO BOUND" in line_c
          and f"at least {-d_c['bound'] * MS:.3f} ms" in line_c
          and 0.3 < -d_c["bound"] <= 0.4,
          f"a 0.4 s step: spread {d_c['spread']:.6f} s, `bound` "
          f"{d_c['bound'] * MS:.3f} ms, and the line refuses it naming a move "
          f"of at least {-d_c['bound'] * MS:.3f} ms -- no more than the step",
          f"printed {line_c!r}")

    # (d) SHORT: 0.3 s of rows sitting at 0.6-0.9 of their second. The spread
    # is 0.3 s and the error 0.6 s -- the old "residual" understated THIS
    # capture, so the old label was wrong in both directions.
    ts_d = [(math.ceil(truth) - truth) + 0.6 + 0.003 * k for k in range(101)]
    d_d = movesync.offset_detail(stamps(truth, ts_d))
    err_d = truth - d_d["offset"]
    check(err_d > d_d["spread"] + 0.25 and err_d <= d_d["bound"],
          f"a 0.3 s capture: the error is {err_d * MS:.1f} ms, twice the "
          f"{d_d['spread'] * MS:.1f} ms spread the old line printed, and "
          f"inside `bound` ({d_d['bound'] * MS:.1f} ms)",
          "a short capture's spread UNDERSTATED its error; only 1 - spread "
          "points the right way")

    # (e) THE LINE ITSELF names the bound and the spread, and never calls the
    # spread a residual.
    line = movesync.offset_line(d)
    check(f"bound +{d['bound'] * MS:.3f} ms" in line
          and f"spread {d['spread']:.6f} s" in line
          and "residual" not in line and "REALFIX-T1" in line,
          "the bounded line prints `bound` and the spread by name, and no "
          "\"residual\"", f"printed {line!r}")
    check("residual" not in line_c,
          "the refused line does not call the spread a residual either",
          f"printed {line_c!r}")

    # (f) THE FLOAT ARM is untouched: `bound` is None there, and the line
    # still says which estimator it used.
    d_f = movesync.offset_detail(movesync.WallStamps([0.0] * 3, [truth] * 3))
    check(d_f["source"] == movesync.OFFSET_SRC_UNIX and d_f["bound"] is None
          and "bound" not in movesync.offset_line(d_f),
          "the float arm carries no `bound` and prints none",
          "the bound is a property of the truncated estimator only")
    check(movesync.offset_detail([])["bound"] is None,
          "no stamps at all: `bound` is None, not a number",
          "a zero bound would read as a perfect clock")

    # KNOWN-BAD ARMS, on the synthetic rows.
    mean_err = truth - sum(stamps(truth, ts)) / len(ts)
    check(mean_err > d["bound"],
          f"KNOWN-BAD: a MEAN over the same rows sits {mean_err * MS:.1f} ms "
          f"below the truth, outside `bound` ({d['bound'] * MS:.3f} ms)",
          "the estimator the max replaced must break the bound, or the bound "
          "is not measuring the estimator")
    d_list = movesync.offset_detail(list(stamps(truth, ts)))
    check(d_list["bound"] == d["bound"] and d_list["offset"] == d["offset"],
          "a plain list of offsets, as every older caller passes, gets the "
          "same offset and `bound`", f"bound {d_list['bound']!r}")


def load(paths):
    """{name: WallStamps} for every capture the shipped loader reads."""
    out = {}
    for p in paths:
        _reps, walls, _src = movesync.load_wire_reports(p)
        out[os.path.basename(p)] = walls
    return out


def section2(caps):
    print("\n2. every vault capture carrying both stamps: the truncated max "
          "against the float median")
    post = {k: w for k, w in caps.items()
            if len(w) >= MIN_ROWS and len(w.unix) == len(w)}
    pinned = sorted(k for k in post if STAMP.search(k).group(1) <= CUT)
    rows = {}
    for k, w in post.items():
        d_f = movesync.offset_detail(w)
        d_t = movesync.offset_detail(movesync.WallStamps(list(w), ()))
        diffs = row_diffs(w)
        late = [x - 1.0 for x in diffs if x >= 1.0]
        rows[k] = {
            "above": d_t["offset"] - d_f["offset"],
            "err": d_f["offset"] - d_t["offset"],
            "bound": d_t["bound"], "spread": d_t["spread"],
            "mean_err": d_f["offset"] - sum(w) / len(w),
            "lead": min(diffs), "late": max(late) if late else 0.0,
            "n_late": len(late), "move": envelope_move(w.unix),
            "clock": d_f["clock_residual"]}
    print(f"   {len(post)} capture(s) with >= {MIN_ROWS} rows, every row "
          f"carrying both stamps; {len(pinned)} at or before {CUT}")

    def worst(key, sign=1):
        k = max(rows, key=lambda c: sign * rows[c][key])
        return k, rows[k][key]

    above = [r["above"] for r in rows.values()]
    k_hi, v_hi = worst("above")
    check(v_hi <= 0.0,
          f"P1: the truncated max never sits above the float median "
          f"(highest {v_hi * MS:+.3f} ms, {k_hi}; lowest "
          f"{min(above) * MS:+.3f} ms; p50 {pct(above, 0.5) * MS:+.3f} ms)",
          "a row delayed between `perf_counter` and `gmtime` could lift it; "
          "if one ever does, the bound is one-sided no longer")
    margins = {k: r["bound"] - r["err"] for k, r in rows.items()}
    k_lo = min(margins, key=margins.get)
    refused = sorted(k for k, r in rows.items() if r["bound"] < 0.0)
    check(margins[k_lo] >= 0.0 and not refused,
          f"THE BOUND: the float median lies inside [max, max + `bound`) on "
          f"all {len(rows)}, by at least {margins[k_lo] * MS:.3f} ms "
          f"({k_lo}); none refused",
          f"refused: {refused[:5]}" if refused else
          "the line's printed claim, scored on every capture that can "
          "score it")
    no_tick = sum(1 for r in rows.values() if r["err"] > 1.0 - r["spread"])
    over1 = sum(1 for r in rows.values() if r["spread"] > 1.0)
    print(f"   without the tick the bound would fail on {no_tick} capture(s); "
          f"{over1} have a spread above 1 s -- P2 as first written")
    k_lead, v_lead = worst("lead", -1)
    check(v_lead >= 0.0,
          f"PREMISE: the coarse clock never LEADS -- no row's `wall` second "
          f"is "
          f"ahead of its own `wall_unix` (least wall_unix - wall "
          f"{v_lead * MS:.3f} ms, {k_lead})",
          "a negative here means the lag model is wrong, or the two families "
          "are not aligned row by row")
    k_late, v_late = worst("late")
    n_late = sum(r["n_late"] for r in rows.values())
    check(v_late <= TICK,
          f"PREMISE: it lags by at most one tick -- {n_late} late rollover(s) "
          f"over {sum(1 for r in rows.values() if r['n_late'])} capture(s), "
          f"the latest {v_late * MS:.3f} ms ({k_late}), against "
          f"{TICK * MS:.3f} ms",
          "the tick in `bound` is only as good as this")
    k_mv, _v = max(((k, abs(r["move"])) for k, r in rows.items()),
                   key=lambda kv: kv[1])
    check(abs(rows[k_mv]["move"]) <= STEADY_MAX,
          f"STEADY: the float offset's lower envelope moves at most "
          f"{rows[k_mv]['move'] * MS:+.3f} ms from the first tenth of rows to "
          f"the last ({k_mv}), against {STEADY_MAX * MS:.0f} ms",
          "the bound is conditional on a steady clock; this is that "
          "condition, "
          "measured")
    ratio = min(r["spread"] / max(r["err"], 1e-12) for r in rows.values())
    check(ratio >= 50.0,
          f"THE OLD LABEL: the spread it printed as \"residual\" exceeds the "
          f"measured error by {ratio:.1f}x at the least",
          "REALFIX section 2.1's 1.00 s / 288 u is this spread")

    # KNOWN-BAD ARM 1: the mean.
    mean_bad = sum(1 for r in rows.values() if r["mean_err"] > r["bound"])
    me = [r["mean_err"] for r in rows.values()]
    check(mean_bad == len(rows),
          f"KNOWN-BAD, the mean: it breaks the bound on {mean_bad} of "
          f"{len(rows)} capture(s), sitting {min(me) * MS:.0f}-"
          f"{max(me) * MS:.0f} ms below the truth",
          "the bound must reject the estimator the max replaced, everywhere")

    # KNOWN-BAD ARM 2: a planted drift. Adding the same ramp to both families
    # IS perf_counter running fast against the system clock: the stamps are
    # untouched and t is not.
    lifted = unsteady = 0
    for k, w in post.items():
        n = len(w)
        ramp = [PLANT_DRIFT * i / (n - 1) for i in range(n)]
        g = [a + b for a, b in zip(w, ramp)]
        f = [a + b for a, b in zip(w.unix, ramp)]
        d_f = movesync.offset_detail(movesync.WallStamps(g, f))
        if max(g) - d_f["offset"] > 0.0:
            lifted += 1
        if abs(envelope_move(f)) > STEADY_MAX:
            unsteady += 1
    check(unsteady == len(post) and lifted >= 0.9 * len(post),
          f"KNOWN-BAD, a {PLANT_DRIFT * MS:.0f} ms drift planted on every "
          f"capture: STEADY goes red on {unsteady} of {len(post)}, and the "
          f"max "
          f"rises above the float median on {lifted}",
          "P1 and STEADY must see a clock that moved; without this they "
          "could be true of any data")

    # THE PINNED FIGURES, which REALFIX.md and movesync's docstring quote.
    pr = [rows[k] for k in pinned]
    got = (len(pr),
           round(min(r["above"] for r in pr) * MS, 3),
           round(max(r["above"] for r in pr) * MS, 3),
           round(min(r["bound"] - r["err"] for r in pr) * MS, 3),
           round(max(r["late"] for r in pr) * MS, 3),
           sum(1 for r in pr if r["err"] > 1.0 - r["spread"]),
           sum(1 for r in pr if r["spread"] > 1.0))
    want = (511, -17.262, -0.105, 14.150, 1.474, 191, 36)
    check(got == want,
          f"PINNED ({CUT}): {got[0]} captures, max - median {got[1]} to "
          f"{got[2]} ms, bound margin >= {got[3]} ms, latest rollover "
          f"{got[4]} ms, 1 - spread alone fails on {got[5]}, spread > 1 s on "
          f"{got[6]}",
          f"want {want}: these are the figures the documents quote; a "
          f"changed vault file changes them")
    cr = [r["clock"] for r in pr]
    mv = [abs(r["move"]) for r in pr]
    print(f"   float arm on the same captures: median - min "
          f"{min(cr) * 1e6:.1f}-{max(cr) * 1e6:.1f} us; envelope move "
          f"<= {max(mv) * MS:.3f} ms")


def section3(caps):
    print("\n3. the pre-T1 captures: which ones the bound applies to")
    pre = {k: w for k, w in caps.items()
           if len(w) >= MIN_ROWS and not w.unix}
    pinned = sorted(k for k in pre if STAMP.search(k).group(1) <= CUT)
    d = {k: movesync.offset_detail(pre[k]) for k in pinned}
    refused = sorted(k for k in pinned if d[k]["bound"] < 0.0)
    bounds = [d[k]["bound"] for k in pinned if d[k]["bound"] >= 0.0]
    lagged = sum(1 for k in pinned if 1.0 < d[k]["spread"] <= 1.0 + TICK)
    print(f"   {len(pre)} capture(s) with >= {MIN_ROWS} rows and no float "
          f"stamp; {len(pinned)} at or before {CUT}")
    if bounds:
        print(f"   bound p10 {pct(bounds, 0.1) * MS:.3f}  p50 "
              f"{pct(bounds, 0.5) * MS:.3f}  p90 {pct(bounds, 0.9) * MS:.3f}  "
              f"max {max(bounds) * MS:.3f} ms; {lagged} with a spread above "
              f"1 s by less than a tick (the coarse clock, not refused)")
    check(len(pinned) == 1034 and tuple(refused) == STEPPED,
          f"PINNED ({CUT}): {len(pinned)} pre-T1 capture(s), {len(refused)} "
          f"refused: {refused}",
          f"want 1034 and {list(STEPPED)}")
    # POSITIVE CONTROL: each refusal is ONE clock step -- the rows split, in
    # file order, into two runs that are each steady -- which is visible in the
    # truncated stamps alone. (A first draft split the rows into 8 equal
    # chunks and compared their maxes; 20260810T151946's step falls among its
    # last 25 of 1,276 rows, sparse, and no chunk saw it.)
    for k in STEPPED:
        if k in pre:
            w = pre[k]
            s = step_split(w)
            moved = (max(w[s:]) - max(w[:s])) if s else None
            check(s is not None and abs(moved) > TICK,
                  f"{k}: splits at row {s} of {len(w)} into two steady runs, "
                  f"their max-estimators {moved * MS:+.1f} ms apart -- one "
                  f"clock step, seen without the float stamp"
                  if s else f"{k}: does NOT split into two steady runs",
                  "a refusal nothing independent confirms is a guess; a lone "
                  "delayed row or a drift would not split this way")
    if BLOCK12 in pre:
        d12 = movesync.offset_detail(pre[BLOCK12])
        line = movesync.offset_line(d12)
        check(d12["spread"] <= 1.0 + TICK
              and round(d12["bound"] * MS, 3) == 16.095
              and "bound +16.095 ms = 4.64 u" in line,
              f"{BLOCK12} (PROBE-GATEFIRE block 12): steady, needs no split, "
              f"bound +{d12['bound'] * MS:.3f} ms = "
              f"{d12['bound'] * movesync.RUN_SPEED:.2f} u -- where the old "
              f"line "
              f"said 288 u",
              "the negative half of the control above, and the line the "
              "document quotes")
    # And the split cannot pass a lone outlier off as a step: lift ONE row of
    # block 12's capture by 1.3 s (a row delayed that long between the two
    # clock reads). The line refuses it, and it does not split.
    if BLOCK12 in pre:
        w = list(pre[BLOCK12])
        w[len(w) // 2] += 1.3
        d_x = movesync.offset_detail(w)
        check(d_x["bound"] < 0.0 and step_split(w) is None,
              f"CONTROL: one row lifted 1.3 s mid-capture is refused (bound "
              f"{d_x['bound'] * MS:.1f} ms) and does NOT split into two "
              f"steady "
              f"runs",
              "otherwise the positive control above could not tell a step "
              "from a single delayed row")


def interp_seps(S, keys, offset):
    """Separation, SYNC (`live`) interpolated to each report's own instant.

    `keys` is a fixed list of (server t, report xy), so every offset scores the
    same reports. Linear between the two bracketing movetap samples, and only
    when they sit within `MAX_PAIR_GAP` of each other; this removes the
    nearest-sample phase term (up to one sample interval of travel) that
    `movesync.pair` carries.
    """
    ts = [s["t"] for s in S]
    out = []
    for st, p in keys:
        ut = offset + st
        j = bisect.bisect_left(ts, ut)
        if j == 0 or j >= len(S):
            continue
        a, b = S[j - 1], S[j]
        if b["t"] - a["t"] > movesync.MAX_PAIR_GAP:
            continue
        la, lb = a["live"], b["live"]
        if not all(math.isfinite(c) for c in la[:2] + lb[:2]):
            continue
        w = (ut - a["t"]) / (b["t"] - a["t"])
        out.append(math.hypot(la[0] + w * (lb[0] - la[0]) - p[0],
                              la[1] + w * (lb[1] - la[1]) - p[1]))
    return out


def sep_stats(seps):
    """(n, p50, p90, max) by movesync's percentile, rounded as it prints."""
    return (len(seps), round(movesync.pct(seps, 0.5), 1),
            round(movesync.pct(seps, 0.9), 1), round(max(seps), 1))


def grid(lo, hi, n=GRID):
    return [lo + (hi - lo) * k / n for k in range(n + 1)]


def section4(root):
    print("\n4. REALFIX-L1's registered separation bounds, re-scored across "
          "the clock bound")
    arms = {}
    for label, cap, tap in L1_ARMS:
        pc = os.path.join(root, "captures", "gamesrv", cap)
        pt = os.path.join(root, "captures", "movetap", tap)
        if not (os.path.isfile(pc) and os.path.isfile(pt)):
            LEDGER.skip("4. REALFIX-L1 re-score",
                        f"arm {label}'s capture or movetap is not in this "
                        f"vault")
            return
        S = movesync.load_movetap(pt)
        reps, walls, _src = movesync.load_wire_reports(pc)
        d = movesync.offset_detail(walls)
        arms[label[0]] = (label, S, reps, d)

    def scored(S, reps, off):
        prs = movesync.pair(S, reps, off)
        return sep_stats(movesync.score(prs, "live")[0])

    # REPRODUCE FIRST: the published figures, from the shipped pairing at the
    # shipped offset. A re-score of numbers this cannot reproduce is fiction.
    got = {k: scored(S, reps, d["offset"]) for k, (_l, S, reps, d)
           in arms.items()}
    check(got == {"A": (63, 4402.4, 6287.3, 6811.4),
                  "B": (68, 267.5, 523.0, 530.5)},
          f"REPRODUCED at the shipped offset: arm A n/p50/p90/max {got['A']}, "
          f"arm B {got['B']} -- the figures FINDINGS published",
          "if these moved, the pipeline changed under the record and the "
          "re-score below is not of the same measurement")

    _lb, S, reps, d = arms["B"]
    off, bound = d["offset"], d["bound"]
    keys = [(t, p) for t, p, _s, _g in movesync.pair(S, reps, off)]
    near = [scored(S, reps, off + x) for x in grid(0.0, bound)]
    inter = [sep_stats(interp_seps(S, keys, off + x))
             for x in grid(-TRANSPORT, bound)]
    old = [scored(S, reps, off + x) for x in grid(0.0, 0.99, 99)]
    hard = max(len(movesync.score(movesync.pair(S, reps, off + x), "live",
                                  min_units=0.0,
                                  min_speed=movesync.HARD_JUMP_SPEED)[1])
               for x in grid(-TRANSPORT, bound))

    def rng(rows, i):
        return min(r[i] for r in rows), max(r[i] for r in rows)

    p50n, p50i, p50o = rng(near, 1), rng(inter, 1), rng(old, 1)
    print(f"   arm B, bound +{bound * MS:.3f} ms: nearest-sample pairing over "
          f"[0, +bound] p50 {p50n[0]}-{p50n[1]}, p90 {rng(near, 2)[0]}-"
          f"{rng(near, 2)[1]}; interpolated over [-{TRANSPORT * MS:.0f} ms, "
          f"+bound] p50 {p50i[0]}-{p50i[1]}, p90 {rng(inter, 2)[0]}-"
          f"{rng(inter, 2)[1]}")
    check(min(p50n[0], p50i[0]) > L1_P50
          and (p50n, p50i) == ((267.5, 267.5), (256.1, 262.4)),
          f"P2 p50 <= {L1_P50:.0f} u is MISSED, and DECIDED: {p50n[0]}-"
          f"{p50n[1]} u at every offset inside the clock bound, {p50i[0]}-"
          f"{p50i[1]} u interpolated with the transport term too -- at least "
          f"{min(p50n[0], p50i[0]) - L1_P50:.0f} u over",
          "FINDINGS recorded it UNDECIDABLE-leaning-miss on a 288 u clock "
          "systematic; the clock term is now <= 4.6 u")
    # THE CONTROL THAT MAKES "DECIDED" MEAN SOMETHING: under the old reading
    # (the offset anywhere in the whole second) the same statistic CAN cross
    # the bar. If it could not, the old UNDECIDABLE was never about the clock.
    check(p50o[0] <= L1_P50 < p50o[1] and p50o[0] == 83.8,
          f"KNOWN-BAD, the old reading: with the offset anywhere in "
          f"[offset, offset + 1 s) the p50 ranges {p50o[0]}-{p50o[1]} u and "
          f"crosses {L1_P50:.0f}",
          "the reason the record could not decide, reproduced -- and the "
          "reason the corrected bound can")
    p90n, p90i = rng(near, 2), rng(inter, 2)
    over_n = sum(1 for r in near if r[2] > L1_P90)
    over_i = sum(1 for r in inter if r[2] > L1_P90)
    # How good is the interpolation? Leave each movetap sample out, predict it
    # from its neighbours (DOUBLE the real spacing, so an over-estimate), and
    # keep the samples within MAX_PAIR_GAP of a paired report.
    inst = sorted(off + t for t, _p in keys)
    loo = []
    for a, b, c in zip(S, S[1:], S[2:]):
        if c["t"] - a["t"] > 2 * movesync.MAX_PAIR_GAP:
            continue
        k = bisect.bisect_left(inst, b["t"])
        if min(abs(inst[i] - b["t"]) for i in (k - 1, k)
               if 0 <= i < len(inst)) > movesync.MAX_PAIR_GAP:
            continue
        w = (b["t"] - a["t"]) / (c["t"] - a["t"])
        loo.append(math.hypot(
            a["live"][0] + w * (c["live"][0] - a["live"][0]) - b["live"][0],
            a["live"][1] + w * (c["live"][1] - a["live"][1]) - b["live"][1]))
    loo_p90 = movesync.pct(loo, 0.9)
    check(p90n[0] <= L1_P90 < p90n[1] and over_i == 0
          and 0.0 < L1_P90 - p90i[1] < loo_p90
          and (p90n, p90i, over_n) == ((515.8, 523.0), (514.4, 518.6), 254),
          f"P2 p90 <= {L1_P90:.0f} u sits AT the bound: {p90n[0]}-{p90n[1]} u "
          f"by the shipped nearest-sample pairing, over {L1_P90:.0f} at "
          f"{over_n} of {len(near)} offsets in the clock bound (523.0, the "
          f"published miss, is its low edge); {p90i[0]}-{p90i[1]} u "
          f"interpolated, over at {over_i} of {len(inter)} with the transport "
          f"term -- met by {L1_P90 - p90i[1]:.1f}-{L1_P90 - p90i[0]:.1f} u",
          f"a margin inside the interpolation's own error (leave-one-out p90 "
          f"{loo_p90:.1f} u at double spacing, n {len(loo)}): leaning met, "
          f"not decided either way -- and no longer because of the clock")
    check(hard == 0,
          f"and no offset in [-{TRANSPORT * MS:.0f} ms, +bound] mints a hard "
          f"row on arm B: the displacement falsifier cannot fire",
          f"max hard rows over the sweep {hard}")

    _la, S_a, reps_a, d_a = arms["A"]
    p0 = [scored(S_a, reps_a, d_a["offset"] + x)[1]
          for x in grid(0.0, d_a["bound"])]
    check(min(p0) >= L1_P0_P50,
          f"P0 p50 >= {L1_P0_P50:.0f} u is MET at every offset in arm A's "
          f"bound ({min(p0)}-{max(p0)} u): the parked copy",
          "the control's separation claim, unchanged by the re-score")


def main():
    print("the truncated clock offset: its error bound, scored against the "
          "float stamp")
    section1()
    try:
        root = vaultpath.vault_root()
        gdir = os.path.join(root, "captures", "gamesrv")
        pat = os.path.join(gdir, "authsrv-*.jsonl")
        paths = sorted(p for p in glob.glob(pat)
                       if STAMP.search(os.path.basename(p)))
    except Exception as exc:                          # noqa: BLE001
        paths, gdir = [], f"(no vault: {type(exc).__name__}: {exc})"
    if not paths:
        why = f"no server captures under {gdir}"
        LEDGER.skip("2. both-stamp captures", why)
        LEDGER.skip("3. pre-T1 captures", why)
        return LEDGER.verdict()
    caps = load(paths)
    section2(caps)
    section3(caps)
    section4(root)
    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
