#!/usr/bin/env python3
"""SEPARATION: how far the client's own position is from the agent we drive.

    python toolkit/clientscan/movesync.py                 # newest overlapping pair
    python toolkit/clientscan/movesync.py --movetap X --capture Y
    python toolkit/clientscan/movesync.py --wire-only     # no movetap needed
    python toolkit/clientscan/movesync.py --selftest      # no captures needed

WHY THIS EXISTS, and it is a correction rather than a new idea. Until
2026-08-19 every instrument in this arc scored the WRONG QUANTITY. `warpscan.py`
asks whether a big client step landed near a point we granted, and answered
"NOT near any grant" for 10 of its 12 detections -- which read as a puzzle for
two runs and was in fact the finding, sitting in the output unread.

Run 20260819T171436 watched both sides at once for the first time. `movetap`
reads the SYNC array (`[AGBASE+0xE8]`) -- the server-authoritative agent, the one
our 0x0029 grants steer. The client REPORTS from the copy it predicts and
renders. Those are different objects, and over 182 matched pairs they sat p50
125.9 u apart and reached 673.7 u. Every client step over 300 u collapsed that
gap: 13 of 13, mean 395.1 u -> 119.7 u, and the biggest jump closed the biggest
gap. **The warp is the client snapping its predicted copy onto the authoritative
one.** The landing point is on the authoritative glide path, which is exactly why
scoring it against granted points found nothing.

So the quantity that predicts a warp is SEPARATION, and nothing printed it. This
does.

THE QUESTION: does separation grow while the two copies disagree, and collapse
when the client jumps? THE PREDICTION, stated before the run rather than after:
if the resync model is right, separation immediately BEFORE a large client step
is large, immediately AFTER it is small, and the step size tracks the gap closed.
REFUTED IF: separation is the same either side of a jump (then the jump is
something else), or if the same collapse appears under the shuffled control
below (then it is an artifact of pairing, not a fact about the client).

THE CONTROL, and this file will not report a collapse without it. Pair each
report against a movetap sample chosen from the WRONG time and the collapse must
vanish. A statistic that survives its own shuffle is measuring the procedure.

CLOCK ALIGNMENT IS THE WEAK POINT AND IS TREATED AS ONE. The capture's `wall`
stamps are whole seconds, so a naive offset is worth +/-0.5 s, and at 288 u/s
half a second is 144 units -- the same order as the separation being measured. Two
things are done about it. The offset is estimated as max(timegm(wall) - t) over
every stamped record, which converges on the true offset from below because
truncation only ever loses fraction. And the headline is then re-scored across a
+/-1.0 s sweep: a collapse that only exists at one offset is an alignment
artifact and is reported as such.

FOUR DEFECTS FOUND IN THIS FILE BY THE 2026-08-19 CORPUS PASS, all fixed here,
all of which had already produced a wrong number that reached a document:

  1. THE WRONG SOURCE. `load_reports` reads the capture's `position_report`
     rows, and until 2026-08-19 those were emitted from the c2s `0x0047` STOP
     ARM ONLY -- 28 of the 158 positions in `20260811T173940`, the other 130
     sitting in the `0x003D` heading stream, invisible. On that source the
     capture reads 5 "unexplained jumps"; SPLICED it reads 2, both of them at
     <=288 u/s, i.e. a client that walked the whole way. `warpscan.load` had
     been reading the spliced stream all along. `--wire-only` now does too, and
     prints the `position_report` count beside it whenever the two disagree
     (they are identical row for row on every post-fix capture, so the
     cross-check is free on current data and loud on old data).
  2. A CONTAMINATED DETECTOR. `JUMP_UNITS = 300 u` with no time normalisation
     counts ordinary walking: the client emits `0x003D` only while moving, so at
     288 u/s a 300 u step is FREE above 300/288 = 1.042 s of silence. RETAIL
     scores 6.4 jumps/min on that bar while having ZERO of 2,665 intervals above
     400 u/s (max implied 388.8, just over the 383.04 boost its own wire
     declares). A bar that cannot tell retail from our worst build is not a bar.
     The verdict-bearing detector is now SPEED-GATED -- implied speed above
     400 u/s over a dt of at least 0.05 s -- and both magnitude and rate are
     printed, because this arc has already shipped a fix that bounded jump SIZE
     while the harm arrived as FREQUENCY.
  3. A BLIND DENOMINATOR. The cadence refusal tested the MEDIAN gap, which
     passes a capture whose median is 0.251 s and whose span is 58% silence
     (`20260811T173940`, max gap 39.1 s). The median is the wrong statistic for
     a bar that is cleared inside the GAPS. Cadence p50, cadence MAX and
     actively-reported coverage are all printed, and the legacy bar is refused
     whenever any interval exceeds the free-silence line.
  4. REFUSAL SEMANTICS. The "5 unexplained jumps" hole was minted by quoting a
     count printed ABOVE a refusing line. Every count now sits BELOW its own
     bar's refusal and is prefixed `refused count:`, so there is nothing
     quotable above a refusal to quote.

Note what the speed gate does NOT need: a long silence makes an implied speed
SMALLER, never larger, so a sparse capture cannot mint a hard jump. That is why
the hard bar answers on captures where the legacy bar refuses.

AND THEN THE NEW BAR HAD A HOLE THE OLD ONE DID NOT, which is the 2026-08-19
adversarial pass and the rest of this header. Fixing an instrument is how you
mint the next defect in it; these are that round's.

  5. THE HARD BAR WAS DISTANCE-BLIND. `dt >= 0.05 s` refused a short interval
     whatever it carried, which discarded the corpus's three fastest genuine
     events: 740.7 u / 0.0318 s, 617.0 u / 0.0324 s, 582.1 u / 0.0331 s. They
     are real -- each pair arrives in SEPARATE TCP frames (c2s seq 465->466,
     50->51, 190->191, each a distinct 26-byte read), so 32 ms is a real client
     cadence and not decode-loop coalescing, and a 740 u step needs 2.57 s of
     walking. Worse, the refusal was ANTI-correlated with the mechanism: a
     resync emits a report either side of the snap, so real warps preferentially
     arrive at SHORT dt. The bar now has a DISTANCE ARM below the dt floor --
     see `HARD_JUMP_UNITS` for why the narrow form and not the obvious one.
  6. AN IMPLIED VELOCITY IS NOT A HEADLINE. For a discontinuity it is a
     denominator artifact the event itself created: "23,279 u/s" is 740.7 u over
     a 32 ms window the snap produced, and the same physical event reads
     differently at a different report cadence. MAGNITUDE and EXCESS OVER BUDGET
     (`d - 288*dt`) do not move with the cadence, so those are printed as the
     pair, and the implied speed is printed labelled as the gate's own input.
  7. A REFUSAL MUST NOT SUPPRESS A COUNT. The `MIN_INTERVALS` floor returned
     before the hard section, so a nine-interval capture carrying a 3,000 u
     impossible step printed only a refused tally. Only the per-minute RATE
     needs that many intervals; the count and its magnitude do not, and now
     print.
  8. THE HARD RATE SILENTLY DEPENDED ON THE LEGACY CONSTANT. "Actively
     reported" is the sum of gaps <= FREE_SILENCE -- 300/288, the very constant
     this file calls "never a verdict". It is load-bearing: `20260819T145717`'s
     7 hard jumps read 14.21/min at a 0.30 s threshold and 3.40/min at 5.00 s.
     The threshold is now printed beside the rate with that sweep, so the number
     is never quotable without it, and hard intervals LONGER than the threshold
     -- which happened in time the denominator excludes -- are reconciled aloud.

READ ONLY. Opens vault captures and writes nothing.
"""
import argparse
import calendar
import glob
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import vaultpath  # noqa: E402

# --- the bars, and where each number came from -------------------------------
#
# THE LEGACY BAR. A client step this big was the event this file originally
# scored, set from the run that established the mechanism: its resync jumps were
# 339.7 u to 757.5 u and its ordinary walking steps were 20-40 u per report. It
# is kept because two documents quote counts measured with it, and it is never a
# verdict again: with no time term it counts any walk across a report gap.
JUMP_UNITS = 300.0
# The measured base speed on `0x0027 AGENT_UPDATE_SPEED_BASE`: 288.00 u/s in 65
# of retail's 153 player-directed sends, and the value our own client walks at.
RUN_SPEED = 288.0
# THE HONEST BAR the legacy one has to clear. Above this much silence, an
# ordinary walk at run speed covers JUMP_UNITS, so a 300 u "jump" inside such a
# gap is indistinguishable from walking. 300/288 = 1.042 s.
FREE_SILENCE = JUMP_UNITS / RUN_SPEED
# THE HARD BAR, and it is the verdict-bearing one. It has TWO ARMS, because a
# speed alone is blind in the one direction the mechanism prefers.
#
# ARM 1 -- SPEED. Retail's own client reports, re-measured here over the whole
# live corpus (13 stamped sessions, 2,789 self-reports, 2,747 intervals): ZERO
# above 400 u/s at dt >= 0.05 s, maximum implied 388.80 -- just over the 383.04
# u/s boost base its wire declares. So 400 sits above every speed retail ever
# legitimately produces, and nothing that clears it is walking.
HARD_JUMP_SPEED = 400.0
# ...over a dt of at least this. A displacement divided by a near-zero interval
# is an arbitrarily large speed, so a SPEED verdict is refused below this rather
# than believed. 0.05 s is a fifth of the ~0.25 s report cadence.
HARD_JUMP_MIN_DT = 0.05
# ARM 2 -- DISTANCE, and it exists because arm 1 alone made the bar
# DISTANCE-BLIND (defect 5 in the header). Below the dt floor a speed is not a
# measurement, so DISTANCE decides there instead of the interval being thrown
# away. Throwing it away is what discarded the corpus's three fastest genuine
# events, all of them at ~32 ms.
#
# 520 u IS RETAIL-CALIBRATED. Retail: 0 of its 2,629 intervals inside 2.0 s
# exceed 520 u, largest 517.87 u / 1.352 s = 383.1 u/s; and BELOW the 0.05 s dt
# floor -- the only place this arm ever fires -- retail's largest displacement
# is 19.15 u over 82 intervals. 27x of headroom against the client the bar is
# calibrated on, and retail still scores zero on both arms.
#
# THE FORM IS NARROW ON PURPOSE, and the wide one was measured before it was
# rejected. `dist >= 520 AND dt <= 2.0 s` is CONTAMINATED: over the 961 vault
# captures it adds four ORDINARY WALKING rows at 284-286 u/s across ~1.85 s gaps
# (20260818T103840 538.6 u, 20260819T150522 533.6 u, 20260816T131839 528.5 u,
# 20260814T090541 525.3 u). `dist >= 520 AND dt < HARD_JUMP_MIN_DT` -- this arm,
# firing only where the speed arm has abdicated -- adds exactly the three
# genuine rows and nothing else: 61 -> 64 hard rows over the same 961 captures.
HARD_JUMP_UNITS = 520.0
# Fewer intervals than this and a per-minute rate is noise dressed as a number.
MIN_INTERVALS = 10
# How far a report may be from its nearest sample before the pair is dropped.
# The reader sustains ~13 Hz, so a healthy pair is inside 80 ms; 250 ms means a
# stall and the sample no longer describes the same instant.
MAX_PAIR_GAP = 0.25
# The offset sweep, in seconds, around the timestamp-derived estimate.
SWEEP = (-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0)
# Kept as the legacy cadence gate. It is no longer the only gate -- see defect 3.
GOOD_CADENCE = 0.5

PLAYER_AGENT = 1
OP_MOVE_TO_POINT = 41       # s2c 0x0029
OP_SET_HEADING = 61         # c2s 0x003D -- the client's position WHILE MOVING
OP_CANCEL_REPORT = 71       # c2s 0x0047 -- the client's position at a STOP


def load_movetap(path):
    S = []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") == "sample":
            S.append(r)
    return S


def load_reports(path):
    """(server_t, [x, y]) from the capture's own `position_report` rows.

    THE WRONG SOURCE ON A LEGACY CAPTURE, and kept only as the cross-check that
    says so. Before 2026-08-19 authsrv emitted `position_report` from the
    `0x0047` stop arm alone, so this returns 28 of the 158 positions in
    `20260811T173940` and is blind between stops -- which is exactly where the
    phenomenon lives. Use `load_wire_reports`.

    Returns the wall pairs separately because the offset estimate needs EVERY
    stamped record, not just the position ones -- more stamps is a tighter bound
    on a truncated clock.
    """
    reps, walls = [], []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("wall") and isinstance(r.get("t"), (int, float)):
            try:
                walls.append(calendar.timegm(
                    time.strptime(r["wall"], "%Y-%m-%dT%H:%M:%SZ")) - r["t"])
            except ValueError:
                pass
        if r.get("kind") == "position_report" and r.get("reported"):
            reps.append((r["t"], list(r["reported"])))
    return reps, walls


def load_wire_reports(path):
    """The SPLICED client self-report stream, which is the whole of it.

    Every c2s `0x003D MOVE_SET_HEADING` carries the client's live position in
    field 1, and every `0x0047 MOVE_CANCEL_REPORT_POSITION` carries it at a
    stop. Together they are the client's own account of where it was; either one
    alone is a sample of one phase of walking. `warpscan.load` has read both
    since it was written, and this file did not, which is defect 1.

    Returns (reports, walls, source) where `source` counts what each opcode
    contributed and how many `position_report` rows the capture holds, so the
    caller can print the disagreement rather than silently inherit it.

    A report row is `(t, [x, y], plane)`. `plane` is `values[2]`, which
    `warpscan` has always kept and this file used to drop on the floor. It is
    carried as ANNOTATION and never as a filter: 6 of the corpus's 64 hard rows
    straddle a flip, and planes 0/18/19 share the x/y frame on `20260819T145717`
    -- so a flip does not make a displacement fictional, it just says which of
    them to look at first. `steps()` accepts the two-element form too, because
    every synthetic fixture builds that one.
    """
    reps, walls = [], []
    n_head = n_stop = n_pr = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("wall") and isinstance(r.get("t"), (int, float)):
            try:
                walls.append(calendar.timegm(
                    time.strptime(r["wall"], "%Y-%m-%dT%H:%M:%SZ")) - r["t"])
            except ValueError:
                pass
        kind = r.get("kind")
        if kind == "position_report" and r.get("reported"):
            n_pr += 1
            continue
        if kind != "decoded":
            continue
        op = r.get("opcode")
        if op not in (OP_SET_HEADING, OP_CANCEL_REPORT):
            continue
        vals = r.get("values")
        # A shape that is not what the schema says must be DROPPED rather than
        # indexed into: values[1] is the position vec2 for both opcodes, and a
        # silent IndexError inside a broad except is how a census gets zeroed.
        if not isinstance(vals, (list, tuple)) or len(vals) < 2:
            continue
        p = vals[1]
        if not isinstance(p, (list, tuple)) or len(p) < 2:
            continue
        plane = vals[2] if len(vals) > 2 else None
        if not isinstance(plane, int):
            plane = None
        reps.append((r["t"], [float(p[0]), float(p[1])], plane))
        if op == OP_SET_HEADING:
            n_head += 1
        else:
            n_stop += 1
    reps.sort(key=lambda row: row[0])
    return reps, walls, {"heading": n_head, "stop": n_stop,
                         "position_report": n_pr, "spliced": len(reps)}


def offset_from_stamps(walls):
    """unix epoch of server t=0, estimated from truncated whole-second stamps.

    Each stamp gives floor(unix) - t = true_offset - frac, frac in [0,1). The
    MAXIMUM over many stamps therefore approaches the true offset from below,
    and the spread is the residual uncertainty. Taking the mean instead would be
    biased low by half a second -- 144 units at run speed.
    """
    if not walls:
        return None, None
    return max(walls), max(walls) - min(walls)


def pair(S, reps, offset):
    """[(server_t, report_xy, sample, gap_seconds)] for reports inside the window.

    Indexes `reps` rows rather than unpacking them, so a two-element synthetic
    row and a three-element `load_wire_reports` row (which carries `plane`) both
    pass through the same code.
    """
    if not S:
        return []
    out = []
    i = 0
    for row in reps:
        st, p = row[0], row[1]
        ut = offset + st
        while i + 1 < len(S) and abs(S[i + 1]["t"] - ut) <= abs(S[i]["t"] - ut):
            i += 1
        j = i
        # the scan above is monotone; step back once in case reports are not
        while j > 0 and abs(S[j - 1]["t"] - ut) < abs(S[j]["t"] - ut):
            j -= 1
        gap = abs(S[j]["t"] - ut)
        if gap <= MAX_PAIR_GAP:
            out.append((st, p, S[j], gap))
    return out


def sep(p, s, key="live"):
    v = s[key]
    if not all(math.isfinite(c) for c in v[:2]):
        return None
    return math.hypot(v[0] - p[0], v[1] - p[1])


def pct(xs, q):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))]


def per_minute(n, seconds):
    """A rate is a count over a NAMED denominator, or it is not a rate."""
    return 60.0 * n / seconds if seconds and seconds > 0 else float("nan")


# --- the denominator, printed before any count ------------------------------
def denominator(reps):
    """Everything a rate and a refusal need, from the report stream alone.

    `active` is the time the client was actually reporting: the sum of the gaps
    short enough that a walk across one cannot clear the legacy bar. The rest of
    the span is silence, and silence is where the legacy bar mints jumps out of
    ordinary walking. The default build's 320.3 s span carries 74.2 s of it.

    THE THRESHOLD IS BORROWED AND IT IS LOAD-BEARING (defect 8). `FREE_SILENCE`
    is `JUMP_UNITS / RUN_SPEED` -- derived from the LEGACY bar this file
    otherwise calls never-a-verdict -- and the hard bar's per-minute rate is
    divided by a number that constant chooses. `20260819T145717`'s 7 hard jumps
    read 14.21/min at a 0.30 s threshold and 3.40/min at 5.00 s. So the
    threshold and the raw `gaps` both come back, and every printer states it
    beside the rate rather than leaving a quotable naked number.
    """
    n = len(reps)
    gaps = [reps[i][0] - reps[i - 1][0] for i in range(1, n)]
    span = (reps[-1][0] - reps[0][0]) if n >= 2 else 0.0
    sg = sorted(gaps)
    active = active_time(gaps, FREE_SILENCE)
    free = sum(1 for g in gaps if g > FREE_SILENCE)
    return {"reports": n, "intervals": len(gaps), "span": span,
            "p50": sg[len(sg) // 2] if sg else float("nan"),
            "max": sg[-1] if sg else float("nan"),
            "active": active, "gaps": gaps,
            "active_threshold": FREE_SILENCE,
            "coverage": (active / span) if span > 0 else float("nan"),
            "free": free,
            "free_fraction": (free / len(gaps)) if gaps else float("nan")}


def active_time(gaps, threshold):
    """The 'actively reporting' denominator, with its threshold NAMED.

    A free function because the rate's sensitivity to the threshold has to be
    printable: quoting an active-time rate without the threshold that produced
    it is quoting one number and hiding the other one it was made from.
    """
    return sum(g for g in gaps if g <= threshold)


def steps(reps):
    """Every consecutive interval, with the numbers a bar can test.

    A row of `reps` is `(t, [x, y])` or `(t, [x, y], plane)`; both are accepted,
    because `load_wire_reports` builds the long form and every synthetic fixture
    builds the short one. `plane_flip` is annotation, never a filter.
    """
    out = []
    for i in range(1, len(reps)):
        a, b = reps[i - 1], reps[i]
        t0, p0, t1, p1 = a[0], a[1], b[0], b[1]
        pl0 = a[2] if len(a) > 2 else None
        pl1 = b[2] if len(b) > 2 else None
        dt = t1 - t0
        d = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        out.append({"t0": t0, "t": t1, "p0": p0, "p": p1, "dt": dt, "dist": d,
                    "speed": (d / dt) if dt > 0 else float("inf"),
                    "plane0": pl0, "plane": pl1,
                    "plane_flip": (pl0 is not None and pl1 is not None
                                   and pl0 != pl1)})
    return out


def excess(row):
    """`d - RUN_SPEED*dt` -- how much further than a WALK could have carried it.

    THIS IS THE NUMBER TO QUOTE BESIDE THE MAGNITUDE, and the implied velocity
    is not. For a discontinuity the implied velocity is a denominator artifact
    the event itself created: 23,279 u/s is 740.7 u over a 32 ms window the snap
    produced, and the same physical event reads differently at a different
    report cadence. Magnitude and excess do not move with the cadence.
    """
    return row["dist"] - RUN_SPEED * row["dt"]


def hard_step(row):
    """THE VERDICT, one interval at a time. TWO ARMS, and they do not overlap.

    At `dt >= HARD_JUMP_MIN_DT` the implied speed is a measurement and SPEED
    decides. BELOW it a speed is not a measurement -- so DISTANCE decides there,
    rather than the interval being discarded. Discarding was the hole: short dt
    is exactly where a resync's own pair of reports lands, so the old refusal
    was anti-correlated with the thing it was built to find.
    """
    if row["dt"] >= HARD_JUMP_MIN_DT:
        return row["speed"] > HARD_JUMP_SPEED
    return row["dist"] >= HARD_JUMP_UNITS


def hard_steps(rows):
    """THE VERDICT-BEARING POPULATION. Nothing here is walking, at any cadence."""
    return [r for r in rows if hard_step(r)]


def legacy_steps(rows):
    """The 300 u bar, kept for continuity with two documents. Not a verdict."""
    return [r for r in rows if r["dist"] >= JUMP_UNITS]


def walkable(rows):
    """Of a jump population, the ones a walk at run speed already explains."""
    return [r for r in rows if r["speed"] <= RUN_SPEED]


def magnitude(rows, field="dist"):
    xs = sorted(r[field] for r in rows)
    if not xs:
        return None
    return xs[len(xs) // 2], xs[-1]


def newest(pattern):
    hits = sorted(glob.glob(pattern), key=os.path.getmtime)
    return hits[-1] if hits else None


def score(pairs, key="live", min_units=JUMP_UNITS, min_speed=None,
          min_dt=HARD_JUMP_MIN_DT, min_dist=HARD_JUMP_UNITS):
    """(separations, jump rows). A jump row is (t, step, before, after, dt).

    Defaults reproduce the legacy 300 u bar exactly, because two documents quote
    numbers from it and the replay test pins them. Pass `min_speed` to add the
    hard gate: `score(prs, min_units=0.0, min_speed=HARD_JUMP_SPEED)` is the
    verdict-bearing population.

    THE HARD GATE HERE IS `hard_step` SPELLED OUT AGAINST TUPLES, and it carries
    BOTH arms because it used to carry only one. This branch had the identical
    distance blindness the standalone bar had, and a fix applied to one spelling
    of a bar and not the other is how a hole survives being closed.
    """
    seps = [d for _t, p, s, _g in pairs
            for d in [sep(p, s, key)] if d is not None]
    jumps = []
    for i in range(1, len(pairs)):
        (t0, p0, s0, _g0), (t1, p1, s1, _g1) = pairs[i - 1], pairs[i]
        step = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        dt = t1 - t0
        if step < min_units:
            continue
        if min_speed is not None:
            if dt < min_dt:
                if step < min_dist:      # ARM 2: distance, below the dt floor
                    continue
            elif step / dt <= min_speed:  # ARM 1: speed, at or above it
                continue
        b, a = sep(p0, s0, key), sep(p1, s1, key)
        if b is not None and a is not None:
            jumps.append((t1, step, b, a, dt))
    return seps, jumps


# --- the fence on 0x006055E0, as read by movetap ----------------------------
#
# WHY THIS SECTION EXISTS. The separation statistic below says WHEN the client
# snaps. It cannot say whether the client's snap TEST was ever consulted: over
# 623 paired intervals, 0 of 24 snaps began below the test's own 300 u gate and
# yet 303 of 327 above-threshold intervals did not snap. A gate 92.7% of its
# population walks past is not deciding anything, and the candidate explanation
# is that the test is FENCED OFF (`clientControlled`, AgTrack record+0x00) and
# never evaluated. `movetap` reads that fence per sample as `gate_reach`; this
# prints it beside the jumps, which is the pairing the question needs.
#
# A MOVETAP THAT PREDATES THE FIELD MUST NOT SCORE AS 0%. Every capture in the
# vault on 2026-08-20 was taken before `gate_reach` existed, so the absent key
# is the common case and a share computed over it would be a confident lie
# about a client that was never asked. That is a refusal with a named fix, not
# a zero.
FENCE_KEY = "gate_reach"


def fence_rows(pairs):
    """(counts, n_with_field, n_total) over the paired samples' gate_reach."""
    counts, have = {}, 0
    for _t, _p, s, _g in pairs:
        v = s.get(FENCE_KEY)
        if v is None:
            continue
        have += 1
        counts[v] = counts.get(v, 0) + 1
    return counts, have, len(pairs)


def fence_at_jumps(pairs, jumps):
    """[(t, step, before_reach, at_reach)] -- the fence either side of a snap.

    `before` is the state at the sample that OPENS the interval, because that
    is the evaluation the jump came out of; `at` is the state once it landed,
    and they differ whenever the SNAP branch ran, since the caller calls
    AgTrack::Clear (0x00605F70) at 0x0060602E on exactly that branch.
    """
    by_t = {t: s for t, _p, s, _g in pairs}
    order = [t for t, _p, _s, _g in pairs]
    prev = {order[i]: order[i - 1] for i in range(1, len(order))}
    out = []
    for row in jumps:
        t = row[0]
        s_at = by_t.get(t, {})
        s_be = by_t.get(prev.get(t), {})
        out.append((t, row[1], s_be.get(FENCE_KEY), s_at.get(FENCE_KEY)))
    return out


def print_fence(pairs, jumps, indent="   "):
    """Returns 0 if the fence was actually read, 1 if it refused. Prints either way."""
    counts, have, total = fence_rows(pairs)
    print(f"\nTHE FENCE ON THE SNAP TEST (0x006055E0), from movetap's "
          f"`{FENCE_KEY}`:")
    if not have:
        print(f"{indent}REFUSED: none of the {total} paired samples carries "
              f"`{FENCE_KEY}`. This movetap predates the field -- re-run "
              f"`python toolkit/clientscan/movetap.py` and pair the new file. "
              f"Nothing here is a fact about the client, and in particular it "
              f"is NOT 'the fence was never open'.")
        return 1
    if have < total:
        print(f"{indent}PARTIAL: {have} of {total} paired samples carry the "
              f"field; the shares below are over {have}, not {total}.")
    unread = sum(c for k, c in counts.items() if str(k).startswith("unread:"))
    for k, c in sorted(counts.items(), key=lambda kv: -kv[1]):
        print(f"{indent}{k:34} {c:6d}  {100.0 * c / have:5.1f}%")
    if unread * 4 >= have:
        print(f"{indent}REFUSED: {unread} of {have} could not read the record. "
              f"No share above is a fact about the client.")
        return 1
    rows = fence_at_jumps(pairs, jumps)
    print(f"{indent}the fence at each hard jump (n={len(rows)}):")
    if not rows:
        print(f"{indent}  (no hard jump in this window -- the distribution "
              f"above is the whole result)")
        return 0
    print(f"{indent}  server t     step   fence BEFORE            fence AT")
    for t, step, be, at in rows:
        print(f"{indent}  {t:9.3f}  {step:7.1f}   {str(be):22} {str(at)}")
    tested = sum(1 for _t, _s, be, _a in rows if be == "test-runs")
    print(f"{indent}  {tested} of {len(rows)} snap(s) began with the test "
          f"REACHABLE. The rest reached 0x00605840 without any gate being "
          f"evaluated -- if that count is the large one, the three gates are "
          f"not what decides our runs and the fence is.")
    return 0


def collapse(jumps):
    if not jumps:
        return None
    b = sum(j[2] for j in jumps) / len(jumps)
    a = sum(j[3] for j in jumps) / len(jumps)
    return b, a, (1.0 - a / b) if b else 0.0


# --- wire-only: the same question asked of a capture with no movetap ---------
#
# WHY THIS IS NOT A RECONSTRUCTION, which is the whole point of it. The obvious
# way to test the resync model retrospectively is to integrate the authoritative
# agent's glide from each grant at 288 u/s and compare. That assumes a speed, a
# straight line, no collision and an arrival rule -- four assumptions stacked
# under a conclusion.
#
# None of that is needed, because of one MEASURED fact: in run 20260819T171153,
# scored against movetap's reading of the SYNC agent, the position the client
# reports immediately AFTER a resync sits 1.0-59.5 u from that agent (n=13,
# mean 22.3). **A landing point is therefore a reading of the authoritative
# agent**, not a model of one. So the test is built from three measured things
# -- the landing, the client's own position when we granted, and the point we
# granted -- and asks a pure geometry question: does the landing lie on the
# segment between the other two?
#
# TWO THINGS THE CAPTURE MUST CARRY BEFORE ANY OF IT MEANS ANYTHING, and both
# are checked rather than assumed:
#   - THE DENOMINATOR. The client emits 0x003D only while moving, so a capture
#     whose gaps run to 131 s is one where ordinary walking clears the legacy
#     bar inside them. That is now measured three ways -- cadence p50, cadence
#     MAX, and the share of the span actually covered by reports -- because the
#     median alone passed `20260811T173940` at 0.251 s while 58% of its span
#     carried no reports at all.
#   - ORIGIN != PRE-JUMP RECORD. Where grants outnumber reports, the "client
#     position at grant time" is often the SAME RECORD as the pre-jump position,
#     which puts it on its own segment by construction. Those rows are counted
#     and reported; the first version of this analysis read their tautological
#     0.0 as a refutation.


def load_grants(path, agent=PLAYER_AGENT):
    """Every 0x0029 we sent to one agent, decoded from the logged wire bytes.

    From `plain` rather than from the label: NPC grants share the opcode and
    only the agent id in the payload tells them apart. A label match would have
    pooled the player's grants with every creature's -- and warpscan's label
    regex undercounts besides (it reads a fraction of the 740 player grants in
    `20260819T171153`).
    """
    import struct
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") != "sent" or r.get("opcode") != OP_MOVE_TO_POINT:
            continue
        raw = r.get("plain")
        if not raw:
            continue
        b = bytes.fromhex(raw)
        if len(b) < 14:
            continue
        aid, = struct.unpack_from("<I", b, 2)
        if aid != agent:
            continue
        x, y = struct.unpack_from("<ff", b, 6)
        out.append((r["t"], [x, y]))
    return out


def on_segment(o, g, p):
    """(perpendicular offset, along-track fraction) of p against o->g."""
    dx, dy = g[0] - o[0], g[1] - o[1]
    L2 = dx * dx + dy * dy
    if L2 <= 1e-9:
        return math.hypot(p[0] - o[0], p[1] - o[1]), 0.0
    f = ((p[0] - o[0]) * dx + (p[1] - o[1]) * dy) / L2
    return (math.hypot(p[0] - (o[0] + f * dx), p[1] - (o[1] + f * dy)), f)


def against_grants(reps, grants, jumps):
    """Each jump's landing scored against the path it was granted.

    Returns (scored, control, nogrant). The control re-scores the same landings
    against the session's LAST grant, which has nothing to do with any of them:
    if an unrelated grant fits as well, the map's geometry is doing the work.
    """
    scored, control, nogrant = [], [], 0
    for j in jumps:
        t0, p1, t1 = j["t0"], j["p"], j["t"]
        prior = [g for g in grants if g[0] <= t1]
        # indexed, not unpacked: a `load_wire_reports` row carries a plane too
        earlier = ([(row[0], row[1]) for row in reps if row[0] <= prior[-1][0]]
                   if prior else [])
        if not prior or not earlier:
            nogrant += 1
            continue
        gt, G = prior[-1]
        ot, O = earlier[-1]
        d, f = on_segment(O, G, p1)
        scored.append({"t": t1, "perp": d, "frac": f, "age": t1 - gt,
                       "step": j["dist"], "speed": j["speed"],
                       "degenerate": ot == t0})
    if grants:
        Gc = grants[-1][1]
        for j in jumps:
            d, f = on_segment(j["p0"], Gc, j["p"])
            control.append({"perp": d, "frac": f})
    return scored, control, nogrant


def on_path(rows):
    return sum(1 for r in rows if r["perp"] < 100 and 0.0 <= r["frac"] <= 1.05)


def wire_only(path):
    """Score one capture: the denominator, then the hard bar, then the legacy."""
    reps, _walls, source = load_wire_reports(path)
    grants = load_grants(path)
    den = denominator(reps)
    rows = steps(reps)
    hard = hard_steps(rows)
    legacy = legacy_steps(rows)
    hs, hc, hng = against_grants(reps, grants, hard)
    ls, lc, lng = against_grants(reps, grants, legacy)
    # THE REFUSALS, each attached to the bar it governs.
    #   - the whole run: too few intervals to rate anything.
    #   - the legacy bar: any silence at all above the free line means ordinary
    #     walking clears 300 u somewhere in this capture, so its count is a
    #     mixture and not a measurement.
    # The hard bar has no cadence refusal by construction: silence lowers an
    # implied speed, so no gap can mint a hard jump.
    refuse_all = den["intervals"] < MIN_INTERVALS
    legacy_reasons = []
    if den["free"] > 0:
        legacy_reasons.append(
            f"{den['free']} of {den['intervals']} intervals "
            f"({100 * den['free_fraction']:.0f}%) exceed the "
            f"{FREE_SILENCE:.3f}s free-silence line")
    if den["p50"] > GOOD_CADENCE:
        legacy_reasons.append(
            f"cadence p50 {den['p50']:.2f}s is above the {GOOD_CADENCE}s bar")
    # THE LEGACY POPULATION SPLIT EXHAUSTIVELY. "of which N are walking" left a
    # remainder nobody named: `20260819T145717`'s 31 legacy steps are 23 walking
    # + 7 hard + ONE at 360.3 u/s that is neither. A partition that does not add
    # up invites the reader to assume the rest is the other thing.
    legacy_hard = [r for r in legacy if hard_step(r)]
    legacy_walk = walkable(legacy)
    legacy_between = [r for r in legacy
                      if r["speed"] > RUN_SPEED and not hard_step(r)]
    return {"source": source, "reports": den["reports"], "grants": len(grants),
            "den": den, "steps": rows,
            "hard": hard, "legacy": legacy,
            "walkable_legacy": legacy_walk,
            "legacy_hard": legacy_hard, "legacy_between": legacy_between,
            # RENAMED from scored/control/nogrant/degenerate. Those names
            # described the HARD population while spelling like the file's only
            # population, which is a name that changed meaning without changing
            # spelling -- the `legacy_*` twins sat right beside them.
            "hard_scored": hs, "hard_control": hc, "hard_nogrant": hng,
            "hard_degenerate": sum(1 for r in hs if r["degenerate"]),
            # Hard rows whose own dt EXCEEDS the active-time threshold: they
            # happened in time the `active` denominator excludes, so that rate
            # counts an event its denominator does not contain (defect 8).
            "hard_outside_active": [r for r in hard
                                    if r["dt"] > den["active_threshold"]],
            "hard_plane_flips": sum(1 for r in hard if r["plane_flip"]),
            "hard_by_distance": [r for r in hard
                                 if r["dt"] < HARD_JUMP_MIN_DT],
            "legacy_scored": ls, "legacy_control": lc, "legacy_nogrant": lng,
            "legacy_degenerate": sum(1 for r in ls if r["degenerate"]),
            "refuse_all": refuse_all, "legacy_refusals": legacy_reasons,
            # kept for continuity with the old dict; both are legacy-bar numbers
            "cadence": den["p50"],
            "jumps": len(legacy),
            "jump_fraction": len(legacy) / max(1, den["intervals"])}


def _print_landing(rows, control, nogrant, degenerate, indent="       "):
    """The geometry block. Never printed above its population's refusal."""
    if not rows:
        print(f"{indent}no landing scored against a grant "
              f"({nogrant} had no player grant before them)")
        return
    perp = sorted(r["perp"] for r in rows)
    ages = sorted(r["age"] for r in rows)
    print(f"{indent}LANDING vs the granted path: perp p50 "
          f"{perp[len(perp) // 2]:.1f} u   on-path {on_path(rows)}/{len(rows)}")
    if control:
        c = sorted(r["perp"] for r in control)
        print(f"{indent}CONTROL (an unrelated grant):  perp p50 "
              f"{c[len(c) // 2]:.1f} u   on-path {on_path(control)}/{len(control)}")
    print(f"{indent}grant age at the jump: p50 {ages[len(ages) // 2]:.2f}s  "
          f"max {ages[-1]:.2f}s")
    clean = [r for r in rows if not r["degenerate"]]
    print(f"{indent}{degenerate} of {len(rows)} row(s) are DEGENERATE -- the "
          f"grant-time report IS the pre-jump record, so the landing sits on "
          f"its own segment by construction")
    if not clean:
        print(f"{indent}  ...which leaves ZERO non-degenerate rows: the "
              f"on-path number above is a tautology on this capture, not "
              f"evidence")
    else:
        print(f"{indent}  non-degenerate: on-path {on_path(clean)}/{len(clean)}")
    if nogrant:
        print(f"{indent}{nogrant} jump(s) had no grant before them; this model "
              f"says nothing about those")


def _print_hard_magnitude(rows, indent="       "):
    """What a hard population IS, printed wherever it is counted.

    MAGNITUDE and EXCESS are the pair, because both are cadence-invariant. The
    implied speed comes last and labelled: for a discontinuity it is a
    denominator artifact the event itself created, and quoting it as a headline
    is quoting the bar's input back as its output.
    """
    m = magnitude(rows, "dist")
    xs = sorted(excess(r) for r in rows)
    v = magnitude(rows, "speed")
    n_dist = sum(1 for r in rows if r["dt"] < HARD_JUMP_MIN_DT)
    print(f"{indent}magnitude                p50 {m[0]:.0f} u     "
          f"max {m[1]:.0f} u")
    print(f"{indent}excess over budget       p50 {xs[len(xs) // 2]:.0f} u     "
          f"max {xs[-1]:.0f} u   (d - {RUN_SPEED:.0f}*dt: what no walk explains)")
    print(f"{indent}implied speed            p50 {v[0]:.0f} u/s   "
          f"max {v[1]:.0f} u/s")
    print(f"{indent}   ...and that speed is THE GATE'S OWN INPUT, not a "
          f"headline: for a discontinuity the denominator is a window the event "
          f"itself created, so it moves with the report cadence and the two "
          f"lines above do not.")
    print(f"{indent}arms: {len(rows) - n_dist} by SPEED "
          f"(> {HARD_JUMP_SPEED:.0f} u/s at dt >= {HARD_JUMP_MIN_DT:.2f}s), "
          f"{n_dist} by DISTANCE (>= {HARD_JUMP_UNITS:.0f} u below that dt)")
    flips = sum(1 for r in rows if r["plane_flip"])
    if flips:
        print(f"{indent}{flips} of {len(rows)} straddle a PLANE FLIP "
              f"(`values[2]`). ANNOTATION, NOT EXCLUSION -- planes 0/18/19 "
              f"share the x/y frame on this corpus, so a flip does not make a "
              f"displacement fictional.")


def print_wire_only(path, w):
    den, src = w["den"], w["source"]
    print(f"\n=== {os.path.basename(path)}")
    print(f"    SOURCE  {src['spliced']} client self-reports, SPLICED from the "
          f"decoded c2s stream ({src['heading']} x 0x003D + {src['stop']} x "
          f"0x0047)")
    if src["position_report"] != src["spliced"]:
        print(f"            CROSS-CHECK DISAGREES: the capture's own "
              f"`position_report` rows number {src['position_report']}, "
              f"{src['spliced'] - src['position_report']:+d} against the "
              f"spliced stream. A capture predating 2026-08-19 logged the "
              f"0x0047 STOP ARM ONLY and is blind between stops -- which is "
              f"where the phenomenon lives. The spliced stream is used below.")
    else:
        print(f"            cross-check: `position_report` agrees exactly "
              f"({src['position_report']} rows)")
    print(f"    GRANTS  {w['grants']} player 0x0029 to agent {PLAYER_AGENT}, "
          f"decoded from the wire bytes (never from a label)")
    print(f"    DENOMINATOR  {den['intervals']} interval(s) over "
          f"{den['span']:.1f}s")
    if den["intervals"] == 0:
        print(f"            REFUSING EVERY VERDICT: no interval to measure. "
              f"{den['reports']} report(s) is not a stream.")
        return
    print(f"            cadence p50 {den['p50']:.3f}s   MAX {den['max']:.3f}s")
    print(f"            actively reported {den['active']:.1f}s = "
          f"{100 * den['coverage']:.0f}% of span; the rest is silence")
    print(f"            THE HONEST BAR: at {RUN_SPEED:.0f} u/s a "
          f"{JUMP_UNITS:.0f} u step is FREE above {FREE_SILENCE:.3f}s of "
          f"silence, and {den['free']} of {den['intervals']} intervals "
          f"({100 * den['free_fraction']:.0f}%) are that silent")

    hard = w["hard"]
    if w["refuse_all"]:
        # ONLY THE RATE IS REFUSED. The floor exists because a per-minute number
        # off nine intervals is noise wearing a decimal point -- but a COUNT and
        # a MAGNITUDE need no denominator at all, and refusing them meant a
        # nine-interval capture carrying a 3,000 u impossible step printed
        # nothing but a tally. That costs nothing today (10 vault captures sit
        # under the floor and not one carries a hard or a 300 u step) and it is
        # expensive to discover later.
        print(f"\n    REFUSING EVERY RATE: {den['intervals']} interval(s) is "
              f"below the {MIN_INTERVALS} this tool needs before a per-minute "
              f"number means anything. The COUNT below is NOT refused with it.")
        print(f"    HARD JUMPS  n = {len(hard)} of {den['intervals']} "
              f"interval(s)")
        if hard:
            _print_hard_magnitude(hard)
        print(f"    refused rate:  no per-minute number from "
              f"{den['intervals']} interval(s), either bar")
        print(f"    LEGACY BAR  refused count: {len(w['legacy'])} step(s) >= "
              f"{JUMP_UNITS:.0f} u (gap-contaminated, and unrated here)")
        return

    print(f"\n    HARD JUMPS -- TWO ARMS, and each is the one the other cannot "
          f"be. THE VERDICT.")
    print(f"       at dt >= {HARD_JUMP_MIN_DT:.2f}s: implied speed > "
          f"{HARD_JUMP_SPEED:.0f} u/s. Silence cannot mint one -- a longer dt "
          f"LOWERS an implied speed.")
    print(f"       below that dt, where a speed is not a measurement: "
          f"displacement >= {HARD_JUMP_UNITS:.0f} u. Retail's largest step "
          f"below the floor is 19.15 u of 82 intervals, and its largest inside "
          f"2.0s is 517.87 u, so retail scores 0 on both arms.")
    print(f"       n = {len(hard)} of {den['intervals']} interval(s)")
    if hard:
        _print_hard_magnitude(hard)
        thr = den["active_threshold"]
        print(f"       RATE  {per_minute(len(hard), den['span']):.2f}/min of "
              f"span ({den['span']:.1f}s)")
        print(f"             {per_minute(len(hard), den['active']):.2f}/min of "
              f"actively-reported time ({den['active']:.1f}s = the sum of gaps "
              f"<= {thr:.3f}s)")
        print(f"             THAT THRESHOLD IS `FREE_SILENCE` = "
              f"{JUMP_UNITS:.0f}/{RUN_SPEED:.0f} -- borrowed from the LEGACY "
              f"bar this file otherwise calls never-a-verdict, and load-bearing:")
        sweep = "   ".join(
            f"{t:.3f}s -> {per_minute(len(hard), active_time(den['gaps'], t)):.2f}/min"
            for t in (0.3, thr, 5.0))
        print(f"             {sweep}")
        print(f"             so the active-time rate is not quotable without "
              f"the threshold that made it.")
        outside = w["hard_outside_active"]
        if outside:
            print(f"       RECONCILE: {len(outside)} of {len(hard)} hard "
                  f"interval(s) are THEMSELVES longer than {thr:.3f}s ("
                  + ", ".join(f"{r['dt']:.3f}s" for r in outside)
                  + f"), so they happened in time the active denominator "
                  f"EXCLUDES -- that rate's numerator counts events its own "
                  f"denominator does not contain.")
        _print_landing(w["hard_scored"], w["hard_control"], w["hard_nogrant"],
                       w["hard_degenerate"])
    else:
        print(f"       RATE  0.00/min. Nothing in this capture moved the client "
              f"further than it could have walked, on either arm.")

    print(f"\n    LEGACY BAR -- step >= {JUMP_UNITS:.0f} u, no time term. "
          f"GAP-CONTAMINATED; never a verdict.")
    # EXHAUSTIVE, because "of which N are walking" left a remainder unnamed and
    # a reader completes an unfinished partition with the other category.
    split = (f"= {len(w['walkable_legacy'])} walking (<= {RUN_SPEED:.0f} u/s) "
             f"+ {len(w['legacy_hard'])} clearing the HARD bar "
             f"+ {len(w['legacy_between'])} neither")
    if w["legacy_between"]:
        split += (" (" + ", ".join(f"{r['speed']:.1f} u/s"
                                   for r in w["legacy_between"]) + ")")
    if w["legacy_refusals"]:
        print(f"       REFUSING a verdict: " + "; ".join(w["legacy_refusals"])
              + ". Ordinary walking clears this bar inside those gaps, so what "
                "follows is a mixture, not a measurement.")
        print(f"       refused count: {len(w['legacy'])} step(s) >= "
              f"{JUMP_UNITS:.0f} u {split}")
        print(f"       refused rate:  "
              f"{per_minute(len(w['legacy']), den['span']):.2f}/min of span")
    else:
        print(f"       no gap in this capture is long enough to mint one, so "
              f"the count stands (it is still not the verdict)")
        print(f"       count: {len(w['legacy'])} step(s) >= {JUMP_UNITS:.0f} u "
              f"{split}; rate "
              f"{per_minute(len(w['legacy']), den['span']):.2f}/min of span")


def selftest():
    """Everything checkable with no captures. Exits non-zero on any gap."""
    bad = 0
    print("movesync selftest -- no captures required\n")

    print("1. the truncated-clock estimator takes the MAX, not the mean")
    # A mean would sit half a second low, which is 144 units at 288 u/s -- the
    # same size as the thing being measured.
    true_off = 1000.5
    walls = [math.floor(true_off + t) - t for t in (0.0, 0.3, 0.7, 1.1, 1.9)]
    est, spread = offset_from_stamps(walls)
    ok = abs(est - true_off) < 1.0 and est <= true_off
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] estimate {est:.3f} for a true "
          f"{true_off} -- from below, within one second (spread {spread:.3f})")
    mean = sum(walls) / len(walls)
    ok = mean < est
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] and the mean ({mean:.3f}) really is "
          f"lower, so the choice of estimator is not decorative")

    print("\n2. the jump scorer separates a resync from ordinary walking")
    # Synthetic: the client walks away from a stationary authoritative agent,
    # then snaps back onto it. Separation must be large before and small after.
    S, reps = [], []
    for k in range(10):
        S.append({"t": 100.0 + k * 0.1, "live": [0.0, 0.0, 0]})
        reps.append((k * 0.1, [k * 50.0, 0.0]))
    S.append({"t": 101.0, "live": [0.0, 0.0, 0]})
    reps.append((1.0, [10.0, 0.0]))          # the snap back
    prs = pair(S, reps, 100.0)
    seps, jumps = score(prs)
    ok = len(jumps) == 1 and jumps[0][2] > 400 and jumps[0][3] < 20
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] one jump found, separation "
          f"{jumps[0][2]:.0f} u -> {jumps[0][3]:.0f} u"
          if jumps else "   [FAIL] no jump found in the synthetic resync")

    print("\n3. CONTROL: the same scorer finds NO collapse when there is none")
    # BOTH copies jump together: the step is large, and the separation across it
    # is unchanged. A scorer that reports a collapse here is reporting its own
    # procedure rather than a fact about the client.
    #
    # THIS CONTROL WAS VACUOUS WHEN FIRST WRITTEN and the selftest passed it.
    # Its synthetic steps were 50 u against a 300 u threshold, so `j2` was empty
    # and `all(...)` over an empty list is True -- a check that could not fail,
    # inside the section whose whole job is to prove the checks can. It now
    # asserts the row count FIRST.
    S2, reps2 = [], []
    for k in range(12):
        leap = 900.0 if k >= 6 else 0.0     # both copies leap at the same index
        S2.append({"t": 100.0 + k * 0.1, "live": [k * 10.0 + leap, 0.0, 0]})
        reps2.append((k * 0.1, [k * 10.0 + leap + 600.0, 0.0]))
    _s2, j2 = score(pair(S2, reps2, 100.0))
    ok = len(j2) >= 1
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] the control produced {len(j2)} "
          f"jump row(s) to judge -- zero would make the next check vacuous")
    ok = bool(j2) and all(abs(j[2] - j[3]) < 50 for j in j2)
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] and separation is unchanged across "
          f"each ("
          + ", ".join(f"{j[2]:.0f}->{j[3]:.0f}" for j in j2)
          + ") -- so a collapse means something")

    print("\n4. pairs beyond MAX_PAIR_GAP are dropped, not silently stretched")
    far = pair([{"t": 500.0, "live": [0.0, 0.0, 0]}], [(0.0, [0.0, 0.0])], 0.0)
    ok = far == []
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] a report 500 s from any sample "
          f"yields {len(far)} pair(s) -- a fixture that resolves to nothing "
          f"must raise, not return a confident number")

    print("\n5. the SPEED GATE tells a walk across a gap from a real jump")
    # A client walking at run speed across silences: every step clears 300 u and
    # NONE of them is a jump. This is the contamination that made retail score
    # 6.4/min on the legacy bar.
    walk = [(k * 2.0, [k * 2.0 * RUN_SPEED, 0.0]) for k in range(12)]
    wrows = steps(walk)
    ok = len(wrows) == 11 and len(legacy_steps(wrows)) == 11
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] {len(legacy_steps(wrows))} of "
          f"{len(wrows)} walking steps clear the legacy {JUMP_UNITS:.0f} u bar "
          f"-- the row count is asserted first so the next check is not vacuous")
    ok = len(hard_steps(wrows)) == 0
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] and {len(hard_steps(wrows))} clear "
          f"the hard bar")
    planted = walk[:6] + [(walk[5][0] + 0.13, [walk[5][1][0] + 900.0, 0.0])]
    prows = steps(planted)
    ok = len(hard_steps(prows)) == 1
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] a planted 900 u / 0.13 s step is "
          f"caught exactly once ({len(hard_steps(prows))})")

    print("\n6. the DISTANCE ARM catches what the dt floor used to discard")
    # The three fastest genuine events in the corpus all arrive at ~32 ms,
    # because a resync emits a report either side of the snap. The old dt floor
    # refused them for being short, whatever they carried.
    real = walk[:6] + [(walk[5][0] + 0.032, [walk[5][1][0] + 700.0, 0.0])]
    rrows = steps(real)
    ok = len(rrows) == 6
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] the fixture holds {len(rrows)} "
          f"interval(s) to judge -- counted before it is judged")
    ok = len(hard_steps(rrows)) == 1
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] a 700 u / 0.032 s step is caught "
          f"({len(hard_steps(rrows))}) -- the old speed-only bar read 0 here")
    # AND THE ARM IS NOT A dt DETECTOR. The same short interval carrying a small
    # displacement must still be refused, or the fix has re-opened the hole the
    # dt floor existed to close.
    tiny = walk[:6] + [(walk[5][0] + 0.01, [walk[5][1][0] + 25.0, 0.0])]
    trows = steps(tiny)
    ok = len(trows) == 6 and len(hard_steps(trows)) == 0
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] while 25 u over 0.01 s -- an "
          f"implied 2,500 u/s -- is still refused "
          f"({len(hard_steps(trows))} of {len(trows)})")

    # --- the fence section: an absent field must REFUSE, never score 0% ------
    # Every movetap in the vault on 2026-08-20 predates `gate_reach`, so this
    # is the branch that will actually run first, and a silent 0% would read as
    # "the fence was never open" -- the finding, minted from a missing key.
    print("\n7. the fence section refuses a movetap that predates the field")
    import contextlib
    import io
    old = [(1.0, [0.0, 0.0], {"t": 1.0, "live": [0.0, 0.0, 0]}, 0.0),
           (2.0, [900.0, 0.0], {"t": 2.0, "live": [900.0, 0.0, 0]}, 0.0)]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_old = print_fence(old, [(2.0, 900.0, 400.0, 20.0, 1.0)])
    out_old = buf.getvalue()
    ok = rc_old == 1 and "REFUSED" in out_old and "predates" in out_old
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] a movetap with no `{FENCE_KEY}` "
          f"returns {rc_old} and says so, rather than printing a 0% share")

    new = [(1.0, [0.0, 0.0], {"t": 1.0, "live": [0.0, 0.0, 0],
                              FENCE_KEY: "shut:apply"}, 0.0),
           (2.0, [900.0, 0.0], {"t": 2.0, "live": [900.0, 0.0, 0],
                                FENCE_KEY: "test-runs"}, 0.0)]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_new = print_fence(new, [(2.0, 900.0, 400.0, 20.0, 1.0)])
    out_new = buf.getvalue()
    ok = (rc_new == 0 and "REFUSED" not in out_new
          and "shut:apply" in out_new and "test-runs" in out_new
          and "0 of 1 snap(s) began with the test REACHABLE" in out_new)
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] and a movetap that HAS the field "
          f"reports the state either side of the jump -- here the snap began "
          f"with the fence shut, so no gate was consulted")

    # The mirror: the same fixture with the fence OPEN before the jump must
    # count it as reachable, or the line above is printing a constant.
    new2 = [(1.0, [0.0, 0.0], dict(new[0][2], **{FENCE_KEY: "test-runs"}), 0.0),
            new[1]]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_fence(new2, [(2.0, 900.0, 400.0, 20.0, 1.0)])
    ok = "1 of 1 snap(s) began with the test REACHABLE" in buf.getvalue()
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] flipping the BEFORE state to "
          f"`test-runs` moves that count to 1 of 1 -- the tally reads the "
          f"sample and is not a constant")

    print("\n" + ("selftest passed" if not bad else f"selftest FAILED ({bad})"))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--movetap", help="a movetap-*.jsonl; default the newest")
    ap.add_argument("--capture", help="a gamesrv capture; default the newest")
    ap.add_argument("--key", default="live", choices=("live", "point"),
                    help="which movetap field to score. `point` is the raw "
                         "+0x78 and is the check that the result is not an "
                         "artifact of the reconstruction.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--wire-only", action="store_true",
                    help="score resync landings against the path they were "
                         "granted, from the capture alone -- no movetap, and "
                         "nothing integrated. Use it on captures that predate "
                         "the two-sided instrument.")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.wire_only:
        cap = a.capture or newest(os.path.join(
            vaultpath.vault_path("captures", "gamesrv"), "*.jsonl"))
        if not cap:
            print("no capture")
            return 2
        print_wire_only(cap, wire_only(cap))
        return 0

    mt = a.movetap or newest(os.path.join(
        vaultpath.vault_path("captures", "movetap"), "movetap-*.jsonl"))
    cap = a.capture or newest(os.path.join(
        vaultpath.vault_path("captures", "gamesrv"), "*.jsonl"))
    if not mt or not cap:
        print("need one movetap capture and one gamesrv capture")
        return 2
    print(f"movetap: {os.path.basename(mt)}\ncapture: {os.path.basename(cap)}\n")

    S = load_movetap(mt)
    # The SPLICED stream here too: on a post-fix capture it is identical to
    # `position_report` row for row (max |dpos| 0.0 across three runs), and on a
    # legacy one it is the difference between 158 positions and 28.
    reps, walls, src = load_wire_reports(cap)
    off, spread = offset_from_stamps(walls)
    if off is None:
        print("the capture carries no wall stamp, so the two clocks cannot be "
              "aligned. Nothing here would mean anything.")
        return 2
    print(f"clock offset {off:.3f} (from {len(walls)} whole-second stamps, "
          f"spread {spread:.3f}s)")
    print(f"SOURCE {src['spliced']} spliced self-reports "
          f"({src['heading']} x 0x003D + {src['stop']} x 0x0047); "
          + (f"`position_report` agrees exactly"
             if src["position_report"] == src["spliced"] else
             f"the capture's own `position_report` rows number "
             f"{src['position_report']} -- the stop arm only, so that field is "
             f"blind between stops"))

    den = denominator(reps)
    print(f"CADENCE p50 {den['p50']:.3f}s  MAX {den['max']:.3f}s  "
          f"actively reported {den['active']:.1f}s = "
          f"{100 * den['coverage']:.0f}% of a {den['span']:.1f}s span")

    prs = pair(S, reps, off)
    # THE PAIR COUNT COMES BEFORE THE VERDICT. warpscan learned this the hard
    # way: a run with nothing in it prints the same shape of report as a run
    # with everything in it, and only the count tells them apart.
    print(f"PAIRS {len(prs)} of {len(reps)} reports and {len(S)} samples "
          f"(dropped {len(reps) - len(prs)} outside +/-{MAX_PAIR_GAP}s)")
    if len(prs) < 20:
        print("FAIL: fewer than 20 pairs. These two captures barely overlap; "
              "this run measured nothing. Check that the movetap window sits "
              "inside the capture's span.")
        return 1

    seps, jumps = score(prs, a.key)                       # legacy population
    _s, hard = score(prs, a.key, min_units=0.0,           # the verdict
                     min_speed=HARD_JUMP_SPEED)
    # THE RATE'S DENOMINATOR IS THE PAIRED WINDOW, not the capture's span. The
    # movetap window sits inside the capture, so dividing a paired jump count by
    # the full span understates it by exactly the unpaired part.
    pden = denominator([(t, p) for t, p, _s2, _g in prs])
    print(f"PAIRED WINDOW {pden['span']:.1f}s, of which "
          f"{pden['active']:.1f}s actively reported "
          f"({100 * pden['coverage']:.0f}%)")
    print(f"\nseparation ({a.key} vs the client's own report), n={len(seps)}:")
    print(f"   p50 {pct(seps, .5):.1f} u   p90 {pct(seps, .9):.1f} u   "
          f"max {max(seps):.1f} u")

    print(f"\nHARD JUMPS -- speed > {HARD_JUMP_SPEED:.0f} u/s at "
          f"dt >= {HARD_JUMP_MIN_DT:.2f}s, or >= {HARD_JUMP_UNITS:.0f} u below "
          f"it, with the separation either side. THE VERDICT.")
    print(f"   n = {len(hard)} of {max(0, len(prs) - 1)} paired interval(s)")
    if hard:
        print("   server t     step   excess     before      after")
        for t, st, b, c, dt in hard:
            print(f"   {t:9.3f}  {st:7.1f}  {st - RUN_SPEED * dt:7.1f}   "
                  f"{b:8.1f}   {c:8.1f}")
        mags = sorted(j[1] for j in hard)
        exs = sorted(j[1] - RUN_SPEED * j[4] for j in hard)
        ch = collapse(hard)
        print(f"   magnitude p50 {mags[len(mags) // 2]:.0f} u  max "
              f"{mags[-1]:.0f} u;  excess over a {RUN_SPEED:.0f} u/s walk p50 "
              f"{exs[len(exs) // 2]:.0f} u  max {exs[-1]:.0f} u")
        print(f"   RATE {per_minute(len(hard), pden['span']):.2f}/min of the "
              f"paired window ({pden['span']:.1f}s), "
              f"{per_minute(len(hard), pden['active']):.2f}/min of "
              f"actively-reported time ({pden['active']:.1f}s = the sum of gaps "
              f"<= {pden['active_threshold']:.3f}s, a threshold borrowed from "
              f"the legacy bar)")
        print(f"   separation mean {ch[0]:.1f} u -> {ch[1]:.1f} u  "
              f"(collapse {100 * ch[2]:.0f}%)")
    else:
        print("   (none -- no resync in this window)")

    # WAS THE TEST EVEN CONSULTED? Printed before the control because it is not
    # a claim about the separation statistic -- it is the fence the separation
    # statistic cannot see, and on a movetap without the field it refuses by
    # name rather than scoring a zero.
    print_fence(prs, hard)

    # THE CONTROL. Pair every report against a sample from the wrong time. If
    # the collapse survives, it is a fact about the procedure and not about the
    # client, and the headline above must not be believed.
    if hard:
        _s2, h2 = score(pair(S, reps, off + 7.0), a.key, min_units=0.0,
                        min_speed=HARD_JUMP_SPEED)
        c2 = collapse(h2)
        ch = collapse(hard)
        print(f"\n   CONTROL (paired 7 s out of true): "
              + (f"n={len(h2)} mean {c2[0]:.1f} -> {c2[1]:.1f} u "
                 f"(collapse {100 * c2[2]:.0f}%)" if c2 else "no jumps"))
        if c2 and c2[2] > 0.5 * ch[2]:
            print("   WARNING: the control collapses nearly as much as the "
                  "real pairing. This statistic is measuring the procedure.")

        # ALIGNMENT SWEEP. A collapse that exists at one offset only is an
        # artifact of a whole-second clock, not a property of the client.
        print("\n   alignment sweep (collapse % vs offset error):")
        row = []
        for d in SWEEP:
            _s3, j3 = score(pair(S, reps, off + d), a.key, min_units=0.0,
                            min_speed=HARD_JUMP_SPEED)
            cc = collapse(j3)
            row.append(f"{d:+.2f}s:{'--' if not cc else '%.0f%%' % (100 * cc[2])}")
        print("      " + "  ".join(row))

    # THE LEGACY BAR, last and labelled, so no count sits above its refusal.
    print(f"\nLEGACY BAR -- step >= {JUMP_UNITS:.0f} u, no time term. "
          f"GAP-CONTAMINATED; never a verdict.")
    if den["free"] > 0 or den["p50"] > GOOD_CADENCE:
        print(f"   REFUSING a verdict: {den['free']} of {den['intervals']} "
              f"report intervals exceed the {FREE_SILENCE:.3f}s free-silence "
              f"line, so a walk at {RUN_SPEED:.0f} u/s clears "
              f"{JUMP_UNITS:.0f} u inside them.")
        print(f"   refused count: {len(jumps)} paired step(s) >= "
              f"{JUMP_UNITS:.0f} u")
    else:
        print(f"   count: {len(jumps)} paired step(s) >= {JUMP_UNITS:.0f} u "
              f"(no gap here is long enough to mint one)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
