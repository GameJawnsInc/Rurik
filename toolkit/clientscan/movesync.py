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

AND THEN THE FENCE SECTION HAD THE SAME FAMILY OF HOLE, which is the 2026-08-20
gate-fire review (probe changes C4, C5, C9). Both earlier rounds were about a
count printed over the wrong denominator; this one is about a count printed over
the wrong POPULATION, at the one number the whole probe turns on.

  9. THE SENTINEL HOLE IN THE JUMP TABLE. `tested = sum(... if be ==
     "test-runs")` was printed against `len(rows)`, and everything that was not
     `test-runs` became "The rest reached 0x00605840". Three of those were not
     states at all: the FIRST paired sample has no predecessor, a jump `t` need
     not be in the paired index, and a sample can carry `unread:<why>` because
     the reader could not read the record. A could-not-read was counted as a
     real fence-shut, inside the headline. It is a THREE-WAY tally now --
     reachable / fenced / unread-or-missing, printed separately, summing to n --
     and the sentence is REFUSED at or above 25% holes. On the vault's own
     `movetap-20260819T171436` x `authsrv-20260819T171153` pairing the old code
     printed "0 of 13 snap(s) began with the test REACHABLE. The rest reached
     0x00605840"; all 13 were a movetap that predates the field. The population
     refusal further up could not catch it -- different denominator, different
     population, hundreds of rows against thirteen.
 10. NOTHING IN THIS SECTION WAS AN OBSERVATION. `gate_reach` is a
     COUNTERFACTUAL label on a state read: it names the branch the caller WOULD
     take, and the sampler never reads the instruction pointer. The APPENDER
     WITNESS is the one positive observation available from data already on
     disk, because it watches a WRITE rather than a state -- `hist_head` or the
     +0x08..+0x14 cache changing between two samples, and `hist_head` returning
     to 0 while the label holds still. Both limits print with it: the appender
     dedups at 2500 ms, and the `shut:noop` branch writes nothing at all.
 11. TWO SPELLINGS FOR ONE STATE. `movetap` wrote `shut:apply` / `world1:apply`
     until the rename, and those strings are in stored rows that cannot be
     rewritten. Both spellings are accepted on read and only the new one is
     printed, with a note saying how many rows were normalised.

READ ONLY. Opens vault captures and writes nothing.
"""
import argparse
import calendar
import glob
import json
import math
import os
import re
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


# --- REALFIX-T1: which clock the wire<->tap offset came from ----------------
# Two estimators, never mixed. `authsrv.Recorder.event` stamped only the
# truncated `wall` until 2026-08-21, so every capture in the vault older than
# that has one source available and exactly one; captures written after it carry
# `wall_unix` too and get an offset that is per row rather than bounded from
# below across the whole file.
OFFSET_SRC_UNIX = "wall_unix"
OFFSET_SRC_TRUNC = "wall(truncated)"


class WallStamps(list):
    """The truncated per-row offsets, carrying the FLOAT ones alongside.

    THIS IS A `list` ON PURPOSE. Every caller before REALFIX-T1 received a plain
    list of `floor(unix) - t` values and does `max(walls)`, `len(walls)` or
    `if not walls` on it, and every synthetic fixture in the suite hands
    `offset_from_stamps` a hand-built list of floats. Subclassing keeps all of
    that working unchanged and puts the new source in an attribute a plain list
    simply does not have -- so `getattr(walls, "unix", ())` IS the fallback
    test, and there is no version flag to get wrong.
    """

    def __init__(self, trunc=(), unix=()):
        list.__init__(self, trunc)
        self.unix = list(unix)


def _wall_offsets(r, trunc, unix):
    """Append this row's clock offsets to the two lists. One row, both sources.

    Kept in one place because the two loaders below had already grown two copies
    of the truncated half, and a third copy of the parsing is a third chance for
    them to disagree about what a stamp means.
    """
    t = r.get("t")
    if not isinstance(t, (int, float)):
        return
    wu = r.get("wall_unix")
    # bool is an int; a `true` here would silently become an offset of 1 - t.
    if isinstance(wu, (int, float)) and not isinstance(wu, bool):
        unix.append(float(wu) - t)
    if r.get("wall"):
        try:
            trunc.append(calendar.timegm(
                time.strptime(r["wall"], "%Y-%m-%dT%H:%M:%SZ")) - t)
        except ValueError:
            pass


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
    reps, walls, walls_unix = [], [], []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        _wall_offsets(r, walls, walls_unix)
        if r.get("kind") == "position_report" and r.get("reported"):
            reps.append((r["t"], list(r["reported"])))
    return reps, WallStamps(walls, walls_unix)


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
    reps, walls, walls_unix = [], [], []
    n_head = n_stop = n_pr = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        _wall_offsets(r, walls, walls_unix)
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
    return reps, WallStamps(walls, walls_unix), {
        "heading": n_head, "stop": n_stop,
        "position_report": n_pr, "spliced": len(reps)}


def offset_detail(walls):
    """unix epoch of server t=0, and WHICH clock said so. REALFIX-T1.

    Returns `{source, offset, spread, n, n_trunc}`. `spread` is the achieved
    residual in seconds on the source that was actually used -- so it is
    comparable across the two only in the sense that both are "how wrong the
    pairing can be", which is the number a reader needs.

    TWO ESTIMATORS, AND THEY ARE NEVER MIXED. A row carrying `wall_unix` gives
    `wall_unix - t` = the true offset directly, to the system clock's own
    resolution, so the estimator over many such rows is the MEDIAN and the
    max-min spread measures perf_counter<->system-clock drift over the run. A
    row carrying only the truncated `wall` gives `floor(unix) - t =
    true_offset - frac` with frac in [0,1), so the estimator is the MAXIMUM --
    which approaches the truth from below -- and the spread is ~1.0 s by
    construction on any run longer than a second. Averaging the two families
    together would produce a number that is neither, biased by the mix ratio;
    pooling the max-estimator over float rows would throw away the resolution
    that makes them worth having. So one family is chosen and the other is
    counted, and `n` vs `n_trunc` is what tells a reader the file was mixed.

    A mean over truncated stamps would sit half a second low -- 144 units at
    run speed, the same size as the separation being measured -- which is why
    the truncated arm takes the max and has since this file was written.
    """
    unix = sorted(getattr(walls, "unix", ()) or ())
    n_trunc = len(walls)
    if unix:
        return {"source": OFFSET_SRC_UNIX, "offset": unix[len(unix) // 2],
                "spread": unix[-1] - unix[0], "n": len(unix),
                "n_trunc": n_trunc}
    if not walls:
        return {"source": None, "offset": None, "spread": None,
                "n": 0, "n_trunc": 0}
    return {"source": OFFSET_SRC_TRUNC, "offset": max(walls),
            "spread": max(walls) - min(walls), "n": n_trunc,
            "n_trunc": n_trunc}


def offset_line(d, indent=""):
    """The one line REALFIX-T1 asks for: which estimator, and the residual.

    Printed rather than returned-and-forgotten because the whole point of T1 is
    that the residual stops being an assumption. A run that silently fell back
    to the truncated stamps looks identical in every downstream number; this
    line is the only place it says so.
    """
    if not d["n"]:
        return (indent + "clock offset: NO STAMPS -- the two clocks cannot be "
                         "aligned and nothing paired against them would mean "
                         "anything")
    mixed = ("" if d["n"] == d["n_trunc"] else
             f"; {d['n_trunc']} row(s) carry only the truncated stamp and were "
             f"NOT pooled in")
    if d["source"] == OFFSET_SRC_UNIX:
        return (indent + f"clock offset {d['offset']:.6f} from {d['n']} "
                f"`wall_unix` row(s) [REALFIX-T1, float, median]: residual "
                f"{d['spread'] * 1000.0:.3f} ms = "
                f"{d['spread'] * RUN_SPEED:.2f} u at {RUN_SPEED:.0f} u/s"
                + mixed)
    return (indent + f"clock offset {d['offset']:.3f} from {d['n']} truncated "
            f"`wall` stamp(s) [PRE-REALFIX-T1, max-estimator]: residual "
            f"{d['spread']:.3f} s = {d['spread'] * RUN_SPEED:.0f} u at "
            f"{RUN_SPEED:.0f} u/s -- this capture predates the float stamp")


def offset_from_stamps(walls, announce=True):
    """(offset, spread), the two-value contract every caller already unpacks.

    Kept at two values deliberately: `pair()`, `resyncscore`, `grantsim` and the
    tests all unpack exactly two, and REALFIX-T1 is an instrument change that
    must not cost a rewrite of everything downstream of it. `offset_detail` is
    where the third and fourth facts live for a caller that wants them.
    """
    d = offset_detail(walls)
    if announce:
        print(offset_line(d, "   "))
    return d["offset"], d["spread"]


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

# `gate_reach` IS A COUNTERFACTUAL LABEL ON A STATE READ, and every sentence
# this file prints about it is written to that. `movetap` reads two fields out
# of the AgTrack state record -- `clientControlled` (record+0x00) and the
# agent's world index -- and names the branch the caller at 0x00605FC0 WOULD
# take if it ran. It never reads the instruction pointer. So anything here about
# 0x006055E0 or 0x00605840 RUNNING is an INFERENCE from those two fields plus
# the caller's tail (0x00606009, 0x00606013), and is printed saying so. The one
# positive observation available is the appender witness further down, and it is
# positive precisely because it watches a WRITE rather than a state.
#
# THE TWO SPELLINGS, and why this file reads both while printing one. `movetap`
# wrote `shut:apply` / `world1:apply` until the 2026-08-20 rename (probe change
# C9). "apply" reads as "the server's position was applied", which is the
# opposite of what that branch does -- 0x00605840 APPENDS to the position
# history (0x00605A50 allocates, 0x00605A5D links new->old head) and corrects
# nothing -- and the string is written into every stored row permanently, so the
# captures already in the vault cannot be re-spelled. A consumer that silently
# failed to match the old name would score a real fenced sample as an unknown
# label and drop it into the unread bucket, which is worse than refusing. So
# BOTH spellings are accepted on read, canonicalised here, and only the NEW name
# is ever printed.
REACH_ALIASES = {"shut:apply": "shut:append", "world1:apply": "world1:append"}
# The one value in which the snap test at 0x006055E0 is reached at all.
REACH_TEST_RUNS = "test-runs"
# The values in which it is not: fence shut (either tail), or fence open on the
# world-1 copy, which goes to 0x00605840 without consulting any gate.
REACH_FENCED = ("shut:append", "shut:noop", "world1:append")
# At or above this share of UNREADABLE rows, the jump-row sentence is refused
# rather than qualified. Nine rows with three holes is not a measurement.
UNREAD_REFUSE_SHARE = 0.25


def unread_refuses(unread, n):
    """THE BAR, computed from `UNREAD_REFUSE_SHARE` and from nowhere else.

    It used to be spelled `unread * 4 >= n` at both call sites while the
    printed prose said "the 25% bar" off the constant -- two copies of one
    number, and only one of them checked. Setting `UNREAD_REFUSE_SHARE` to
    0.90 left the code still refusing at 25% and the output still claiming a
    90% bar, with every check green. A constant the code does not read is
    documentation, and documentation that disagrees with the code is worse
    than none: this is the number that decides whether the probe's headline
    sentence is printed at all.
    """
    return n > 0 and unread >= UNREAD_REFUSE_SHARE * n


def reach_label(v):
    """One `gate_reach` value in its canonical spelling. Old name in, new out."""
    if isinstance(v, str):
        return REACH_ALIASES.get(v, v)
    return v


def classify_reach(v):
    """THE THREE-WAY SPLIT: 'reachable' | 'fenced' | 'unread'.

    Everything that is not one of movetap's four real states -- a `None` from a
    sample that has no such key, an `unread:<why>` sentinel from the reader, a
    `missing:*` sentinel from `fence_at_jumps`, or a label this file has never
    heard of -- lands in 'unread' and NEVER in 'fenced'. Folding a could-not-read
    into a real state is the exact defect this function exists to make
    impossible: it put could-not-reads inside the one headline count the probe
    turns on.
    """
    v = reach_label(v)
    if v == REACH_TEST_RUNS:
        return "reachable"
    if v in REACH_FENCED:
        return "fenced"
    return "unread"


def fence_rows(pairs):
    """(counts, n_with_field, n_total, n_legacy_spelling) over gate_reach.

    Counts are keyed by the CANONICAL label, so a capture written before the C9
    rename tallies under the same key as one written after it, and `legacy` is
    how many rows arrived in the old spelling -- printed as provenance, because
    a normalisation the reader cannot see is a normalisation they cannot audit.
    """
    counts, have, legacy = {}, 0, 0
    for _t, _p, s, _g in pairs:
        v = s.get(FENCE_KEY)
        if v is None:
            continue
        have += 1
        if isinstance(v, str) and v in REACH_ALIASES:
            legacy += 1
        k = reach_label(v)
        counts[k] = counts.get(k, 0) + 1
    return counts, have, len(pairs), legacy


# The three ways a cell in the table below can fail to be a state read. They are
# `missing:*` strings rather than `None` because a bare `None` printed as the
# word "None" and tallied as a fenced sample: the sentinel has to survive into
# the count, not just into the display.
MISSING_NO_PRIOR = "missing:no-earlier-paired-sample"
MISSING_UNPAIRED = "missing:jump-t-not-in-pairs"
MISSING_NO_FIELD = "missing:sample-carries-no-gate_reach"


def fence_at_jumps(pairs, jumps):
    """[(t, step, before_reach, at_reach)] -- the fence either side of a snap.

    `before` is the state at the sample that OPENS the interval, because that is
    the read the jump came out of; `at` is the state once it landed.

    EVERY CELL IS A NAMED VALUE AND NONE IS `None`. Three separate things used to
    arrive here as a bare `None` -- the first paired sample has no predecessor, a
    jump `t` need not be in `by_t` at all, and a sample can carry no `gate_reach`
    -- and every one of them was then counted as a real fence-shut in the
    headline. They are `missing:*` sentinels now, in a value domain that cannot
    collide with movetap's four real states or its `unread:<why>` strings, so
    `classify_reach` can separate them and the table prints what happened.

    THE `at` COLUMN IS NOT AN OBSERVATION OF A BRANCH. On the snap branch the
    caller is documented to call AgTrack::Clear (0x00605F70) at 0x0060602E, so
    `before` != `at` is CONSISTENT with that branch having run. It is not
    evidence that it did: the sampler reads the record and never the instruction
    pointer, and at the ~10 Hz this reader sustains any number of branches can
    run between two reads.
    """
    by_t = {t: s for t, _p, s, _g in pairs}
    order = [t for t, _p, _s, _g in pairs]
    prev = {order[i]: order[i - 1] for i in range(1, len(order))}
    out = []
    for row in jumps:
        t = row[0]
        pt = prev.get(t)
        if t not in by_t:
            be = at = MISSING_UNPAIRED
        else:
            at = by_t[t].get(FENCE_KEY) or MISSING_NO_FIELD
            if pt is None:
                be = MISSING_NO_PRIOR
            else:
                be = by_t[pt].get(FENCE_KEY) or MISSING_NO_FIELD
        out.append((t, row[1], reach_label(be), reach_label(at)))
    return out


def jump_tally(rows):
    """THE THREE-WAY TALLY over the BEFORE column. The three sum to n, always.

    `labels` keeps the per-bucket breakdown so nothing disappears into a
    category name: a `world1:append` and a `shut:noop` are both "the test was
    not reached" and are still different states of the client.
    """
    out = {"n": len(rows), "reachable": 0, "fenced": 0, "unread": 0,
           "labels": {"reachable": {}, "fenced": {}, "unread": {}}}
    for _t, _s, be, _a in rows:
        c = classify_reach(be)
        out[c] += 1
        k = str(reach_label(be))
        out["labels"][c][k] = out["labels"][c].get(k, 0) + 1
    return out


def _detail(counts):
    return ", ".join(f"{k} x{v}" for k, v in
                     sorted(counts.items(), key=lambda kv: -kv[1])) or "none"


def print_jump_tally(rows, indent="   "):
    """The three-way tally, its refusal, and the sentence -- in that order.

    Returns 0 if the sentence was printed, 1 if it was refused. THE SENTENCE IS
    REFUSED, not qualified, when a quarter or more of the jump rows could not be
    classified: this is the number §6 of the probe quotes as its evidence, and a
    footnote under a headline is not a refusal.
    """
    tl = jump_tally(rows)
    n = tl["n"]
    if n == 0:
        print(f"{indent}  REFUSED: zero jump rows to judge. A tally over an "
              f"empty population is not a measurement.")
        return 1
    # The row count is asserted before anything is judged, and the partition is
    # asserted to be exhaustive: a three-way split that does not add up invites
    # the reader to complete it with whichever bucket they expected.
    assert tl["reachable"] + tl["fenced"] + tl["unread"] == n
    print(f"{indent}  THREE-WAY over the BEFORE column, and they sum to {n}:")
    print(f"{indent}    reachable       {tl['reachable']:4d}   BEFORE read "
          f"`{REACH_TEST_RUNS}` -- fence open, world != 1")
    print(f"{indent}    fenced          {tl['fenced']:4d}   BEFORE read a real "
          f"state in which the test is NOT reached "
          f"({_detail(tl['labels']['fenced'])})")
    print(f"{indent}    unread/missing  {tl['unread']:4d}   "
          f"({_detail(tl['labels']['unread'])}) -- NOT folded into either "
          f"count above, which is what this bucket exists for")
    if unread_refuses(tl["unread"], n):
        print(f"{indent}  REFUSED: {tl['unread']} of {n} jump row(s) "
              f"({100.0 * tl['unread'] / n:.0f}%) could not be classified, at "
              f"or above the {100 * UNREAD_REFUSE_SHARE:.0f}% bar. There is no "
              f"sentence about the client available from {n} row(s) with that "
              f"many holes in them.")
        print(f"{indent}  ...and the population refusal above cannot stand in "
              f"for this one: it is a different denominator over a different "
              f"population -- every paired sample, hundreds of rows -- while "
              f"this bar is over these {n}.")
        return 1
    print(f"{indent}  {tl['reachable']} of {n} snap(s) began with the record in "
          f"the ONE state where 0x006055E0 is reached; {tl['fenced']} began in "
          f"a state whose branch is 0x00605840 or a bare return.")
    print(f"{indent}  THAT SECOND HALF IS AN INFERENCE AND HERE IS ITS PREMISE: "
          f"the sampler reads `clientControlled` (AgTrack record+0x00) and the "
          f"agent's world index, never the instruction pointer, and the "
          f"caller's tail at 0x00606009/0x00606013 selects the branch from "
          f"exactly those two fields. NOTHING HERE OBSERVED 0x00605840 EXECUTE. "
          f"For an observation rather than an inference, read the appender "
          f"witness below.")
    return 0


# THE TABLE READ BACK OUT OF ITS OWN OUTPUT.
#
# Every check above this line asks `jump_tally` for a dict. The operator reads
# the TEXT, and `PROBE-GATEFIRE.md` §6 quotes the text -- so the two can
# disagree and nothing notices. They did: swapping the printed `reachable` and
# `fenced` cells, hard-wiring the printed `unread` count to 0, printing the
# unread label breakdown in the fenced row, and DELETING THE WHOLE TABLE while
# keeping the tally and the refusal were each fully green, because the checks
# grepped for marker substrings and one sentence.
#
# A missing row is an ABSENT KEY and never a zero. `{}` means the table was not
# printed at all, so a comparison against the dict fails loudly rather than
# defaulting to agreement -- the same rule as `state_fields` refusing to return
# 0 for a field it could not read.
_THREE_WAY_ROW = re.compile(r"^\s*(reachable|fenced|unread/missing)\s+(\d+)\s+(\S.*)$")
_THREE_WAY_NAME = {"unread/missing": "unread"}


def read_back_three_way(out):
    """{bucket: (printed_count, printed_detail)} parsed from printed text."""
    seen = {}
    for line in out.splitlines():
        m = _THREE_WAY_ROW.match(line)
        if m:
            seen[_THREE_WAY_NAME.get(m.group(1), m.group(1))] = (
                int(m.group(2)), m.group(3).strip())
    return seen


# --- the appender witness, from fields movetap already stores ---------------
#
# WHY THIS EXISTS AND WHAT MAKES IT DIFFERENT. Everything above is a state read:
# `gate_reach` names the branch the caller WOULD take, and no sample ever sees
# the caller run. These two counts are the only POSITIVE observations available
# from data already on disk, and they are positive because each is a CHANGE the
# client wrote between two of our reads:
#
#   (a) `hist_head` (record+0x04) or the last-appended position cache at
#       record+0x08..+0x14 differs across two consecutive samples. 0x00605840 is
#       the history APPENDER -- 0x00605A50 allocates a node, 0x00605A5D links
#       new -> old head -- so a changed head is a node that came into existence
#       between our reads and a changed cache is that path's own bookkeeping.
#       The WRITE is observed; that the appender is what wrote it is the
#       inference, and the premise is that those are the fields it writes.
#   (b) `hist_head` went to 0 while `gate_reach` did NOT change. A head returns
#       to 0 through an arm or an AgTrack::Clear, so this witnesses that
#       something ran BETWEEN two samples -- an aliasing detector that does not
#       depend on the state field whose aliasing is the question.
#
# TWO LIMITS, PRINTED EVERY TIME, because a zero here is weak evidence and would
# otherwise read as a strong one:
#   - the appender DEDUPS at 2500 ms (`0x0060593A cmp eax, 0x9c4`) -- BUT ONLY
#     TOGETHER WITH A MATCHING SAMPLE, which is narrower than this file claimed
#     until 2026-08-20 and is the correction below.
#   - the `shut:noop` branch writes nothing and is unobservable by construction.
#
# LIMIT 1 AS THIS FILE USED TO STATE IT WAS WRONG, and it was wrong in the text
# `PROBE-GATEFIRE.md` §6 quotes: "it cannot append twice inside that window".
# Re-read out of build 38797's own bytes with
# `python toolkit/clientscan/codescan.py --dis 0x00605910 --count 70`, the 2500 ms
# test is the FIRST of a chain and not the whole guard:
#
#   0x0060592A  mov edi,[esi+4] / test edi,edi / je   0x605A2F  (empty head)
#   0x0060593A  cmp eax,0x9c4   ................ jg   0x605A2F  (> 2500 ms)
#   0x0060594B  fucompp [esi+8]  ............... jp   0x605A2F  (cache x)
#   0x0060595E  fucompp [esi+0xC] ............   jp   0x605A2F  (cache y)
#   0x0060596B  cmp edx,[esi+0x10] ...........   jne  0x605A2F  (cache word)
#   0x0060597B  call 0x604760 / test eax,eax ..  jne  0x605A2F  (head node cmp)
#
# Every one of them jumps to the SAME append target, 0x00605A2F, which writes the
# cache at [esi+8..+0x18] and then allocates (0x00605A50) and links new -> old
# head (0x00605A55/0x00605A5D). So the append is suppressed only when the head is
# younger than 2500 ms AND the sample still matches the cached one: a MOVING
# agent CAN append twice inside the window. The direction of the old error was
# conservative -- it made a zero look weaker than it is -- but it was stated as a
# fact about the client, so it is corrected rather than left as the safe lie.
S_HIST_HEAD = 0x04          # movetap.S_HIST_HEAD -- 0x00605F4F, 0x006056AF
S_CACHE_LO = 0x08           # the last-appended position cache, +0x08..+0x14
S_CACHE_HI = 0x18           # ...ending where the record's time field begins
APPEND_DEDUP_S = 2.5        # `0x0060593A cmp eax, 0x9c4` = 2500 ms
# The other tests in the chain above, and the one target they all reach. They are
# CONSTANTS rather than literals inside the sentence because the sentence is the
# artifact: a printed address that no constant feeds is an address nothing can
# be wrong about, and the clause this replaces was exactly that.
APPEND_DEDUP_CHAIN = (0x0060594B, 0x0060595E, 0x0060596B, 0x0060597B)
APPEND_TARGET = 0x00605A2F


def state_fields(s):
    """(hist_head, cache_hex) from one sample; either is None where unread.

    Read out of `state_record` -- the whole 28 bytes movetap stores -- and falls
    back to the `hist_head` field alone when the record is absent. Returns None
    per field rather than a zero, because 0 is a REAL head value (an empty
    chain) and a zero standing in for "not read" is the family of defect this
    file keeps finding in itself.
    """
    rec = s.get("state_record")
    if isinstance(rec, str) and len(rec) >= 2 * S_CACHE_HI:
        try:
            b = bytes.fromhex(rec)
        except ValueError:
            b = None
        if b is not None and len(b) >= S_CACHE_HI:
            return (int.from_bytes(b[S_HIST_HEAD:S_HIST_HEAD + 4], "little"),
                    b[S_CACHE_LO:S_CACHE_HI].hex())
    h = s.get("hist_head")
    return (h if isinstance(h, int) else None), None


def appender_witness(samples):
    """The two positive observations over consecutive samples. Counts only.

    Every denominator it will need is carried out with it, because a count whose
    denominator is computed somewhere else is a count that gets quoted alone.
    """
    n = len(samples)
    w = {"samples": n, "adjacent": max(0, n - 1), "judged": 0, "unjudgeable": 0,
         "head_pairs": 0, "cache_pairs": 0, "head_changed": 0,
         "cache_changed": 0, "witnessed": 0, "reach_pairs": 0,
         "head_to_zero": 0, "dts": []}
    for i in range(1, n):
        a, b = samples[i - 1], samples[i]
        ha, ca = state_fields(a)
        hb, cb = state_fields(b)
        head_ok = ha is not None and hb is not None
        cache_ok = ca is not None and cb is not None
        if not head_ok and not cache_ok:
            w["unjudgeable"] += 1
            continue
        w["judged"] += 1
        w["head_pairs"] += int(head_ok)
        w["cache_pairs"] += int(cache_ok)
        hc = head_ok and ha != hb
        cc = cache_ok and ca != cb
        w["head_changed"] += int(hc)
        w["cache_changed"] += int(cc)
        # THE OR IS THE POINT. Either field changing is one write observed; the
        # cache moves on appends the head does not (the head only changes when a
        # node is allocated), so a head-only tally would miss them.
        w["witnessed"] += int(hc or cc)
        ta, tb = a.get("t"), b.get("t")
        if isinstance(ta, (int, float)) and isinstance(tb, (int, float)):
            w["dts"].append(tb - ta)
        ra, rb = reach_label(a.get(FENCE_KEY)), reach_label(b.get(FENCE_KEY))
        # THE GATE IS `classify_reach` AND NOT A LOCAL SPELLING RULE, and the
        # local rule it replaces is the same disagreement the distribution
        # printer had one section down. `not ra.startswith("unread:")` catches
        # movetap's OWN sentinel and nothing else, so anything this file has
        # never heard of -- a movetap that grows a fifth state, a rename nobody
        # taught this reader, a typo -- passed as a REAL state and entered arm
        # (b)'s DENOMINATOR, where a head -> 0 beside it counts as an arm having
        # run. That denominator is the aliasing witness §6 reads to decide
        # between polling and paying for a hook DLL. `classify_reach` is the
        # function every check interrogates, so it is the function the code
        # asks; `None` and every `missing:*`/`unread:*` sentinel land in
        # 'unread' through it too, which is why no `isinstance` guard is needed
        # in front of it.
        if head_ok and ra == rb and classify_reach(ra) != "unread":
            w["reach_pairs"] += 1
            if ha != 0 and hb == 0:
                w["head_to_zero"] += 1
    return w


def print_appender_witness(samples, indent="   ", population="movetap sample(s)"):
    """Both counts, both denominators, both limits. Refuses; never prints a 0.

    Returns 0 if it measured something, 1 if it refused.
    """
    w = appender_witness(samples)
    print(f"\n{indent}APPENDER WITNESS -- the only POSITIVE observations in this "
          f"section, over {w['adjacent']} consecutive pair(s) of "
          f"{w['samples']} {population}:")
    if w["adjacent"] == 0:
        print(f"{indent}  REFUSED: {w['samples']} sample(s) is not a pair, so "
              f"there is nothing to observe a change across.")
        return 1
    if w["judged"] == 0:
        print(f"{indent}  REFUSED: none of the {w['adjacent']} pair(s) carries "
              f"`state_record` or `hist_head` on BOTH sides "
              f"({w['unjudgeable']} unjudgeable). This movetap predates those "
              f"fields -- re-run `python toolkit/clientscan/movetap.py` and "
              f"pair the new file. This is NOT 'the appender never ran'.")
        return 1
    if w["unjudgeable"]:
        print(f"{indent}  PARTIAL: {w['judged']} of {w['adjacent']} pair(s) "
              f"judged; {w['unjudgeable']} could not be read on both sides and "
              f"are counted in NEITHER arm below.")
    print(f"{indent}  (a) a WRITE to the state record landed between two "
          f"samples: {w['witnessed']} of {w['judged']} judged pair(s) "
          f"(hist_head moved on {w['head_changed']}, the +0x08..+0x14 cache on "
          f"{w['cache_changed']}; the arms overlap and the tally is the OR)")
    print(f"{indent}      arm coverage: hist_head readable both sides on "
          f"{w['head_pairs']} pair(s), the cache on {w['cache_pairs']}. The "
          f"write is OBSERVED; that 0x00605840 is what wrote it is the "
          f"inference, premised on those being the fields it writes.")
    # Phrased so it reads correctly AT ZERO: "an arm ran between two samples"
    # asserts an event that a count of 0 says did not happen.
    print(f"{indent}  (b) hist_head -> 0 with gate_reach UNCHANGED: "
          f"{w['head_to_zero']} of {w['reach_pairs']} pair(s) where both "
          f"gate_reach reads are real and equal. EACH SUCH PAIR is an arm or an "
          f"AgTrack::Clear running BETWEEN two samples -- an aliasing witness "
          f"that does not depend on the state field whose aliasing is the "
          f"question.")
    dts = sorted(w["dts"])
    p50 = dts[len(dts) // 2] if dts else float("nan")
    dmax = dts[-1] if dts else float("nan")
    far = sum(1 for d in dts if d >= APPEND_DEDUP_S)
    chain = ", ".join(f"0x{va:08X}" for va in APPEND_DEDUP_CHAIN)
    print(f"{indent}  LIMIT 1 -- a zero above is WEAK, and the window is "
          f"CONDITIONAL: the appender dedups at {APPEND_DEDUP_S * 1000:.0f} ms "
          f"(`0x0060593A cmp eax, 0x9c4`), but that test is only the FIRST of a "
          f"chain -- {chain} each jump to the SAME append target "
          f"0x{APPEND_TARGET:08X} on INEQUALITY -- so the append is suppressed "
          f"only when the head is younger than {APPEND_DEDUP_S * 1000:.0f} ms "
          f"AND the sample still matches the cached one. A MOVING agent CAN "
          f"append twice inside the window; silence across a shorter pair "
          f"proves nothing only where the cached fields also held still. "
          f"Spacing p50 {p50:.3f}s, max {dmax:.3f}s; "
          f"{far} of {len(dts)} judged pair(s) span {APPEND_DEDUP_S:.1f}s or "
          f"more.")
    print(f"{indent}  LIMIT 2: the `shut:noop` branch writes nothing at all and "
          f"is unobservable by construction -- an absent witness is not "
          f"evidence that it did not run.")
    return 0


# THE WITNESS READ BACK OUT OF ITS OWN OUTPUT, for the reason above. Arm (a)'s
# `witnessed` hard-wired to 0, `judged` substituted for `reach_pairs` as arm
# (b)'s denominator, and the arm-coverage and PARTIAL lines deleted outright
# were each fully green: the checks asked the dict, and the dict was never the
# artifact. A count printed beside the WRONG denominator is the same defect C4
# was about -- a share whose bottom half nobody checked.
#
# Every field is keyed off a distinctive substring of the sentence that carries
# it, so a deleted line yields an ABSENT key rather than a zero.
_WITNESS_FIELDS = (
    ("witnessed", r"\(a\) a WRITE to the state record landed between two "
                  r"samples: (\d+) of \d+ judged pair"),
    ("judged", r"\(a\) a WRITE to the state record landed between two "
               r"samples: \d+ of (\d+) judged pair"),
    ("head_changed", r"hist_head moved on (\d+), the \+0x08"),
    ("cache_changed", r"the \+0x08\.\.\+0x14 cache on (\d+); the arms overlap"),
    ("head_pairs", r"arm coverage: hist_head readable both sides on (\d+) pair"),
    ("cache_pairs", r"arm coverage: hist_head readable both sides on \d+ "
                    r"pair\(s\), the cache on (\d+)\."),
    ("head_to_zero", r"\(b\) hist_head -> 0 with gate_reach UNCHANGED: "
                     r"(\d+) of \d+ pair"),
    ("reach_pairs", r"\(b\) hist_head -> 0 with gate_reach UNCHANGED: "
                    r"\d+ of (\d+) pair"),
    ("partial_judged", r"PARTIAL: (\d+) of \d+ pair\(s\) judged"),
    ("partial_adjacent", r"PARTIAL: \d+ of (\d+) pair\(s\) judged"),
    ("partial_unjudgeable", r"judged; (\d+) could not be read on both sides"),
)


def read_back_witness(out):
    """{field: printed_int} parsed from `print_appender_witness`'s own text."""
    seen = {}
    for name, pat in _WITNESS_FIELDS:
        m = re.search(pat, out)
        if m:
            seen[name] = int(m.group(1))
    return seen


def print_fence(pairs, jumps, indent="   ", samples=None):
    """Returns 0 if the fence share was read, 1 if it refused. Prints either way.

    `samples` is the WHOLE movetap sample stream when the caller has one. The
    appender witness is about consecutive SAMPLES, not about paired reports, and
    pairing drops every sample that had no report beside it -- so handing it the
    paired subset stretches the intervals it judges. It falls back to the paired
    samples with the population NAMED, because a witness over a subset is still
    a positive observation and printing nothing would be worse.

    The return value is about the fence SHARE alone. The jump tally and the
    witness carry their own refusals over their own populations, and print on
    every path including the refusing ones -- one refusal standing in for
    another is what C4 exists to undo.
    """
    rc = 0
    counts, have, total, legacy = fence_rows(pairs)
    print(f"\nTHE FENCE ON THE SNAP TEST (0x006055E0), from movetap's "
          f"`{FENCE_KEY}` -- a COUNTERFACTUAL label on a state read, not an "
          f"observation that the caller ran:")
    if not have:
        print(f"{indent}REFUSED: none of the {total} paired samples carries "
              f"`{FENCE_KEY}`. This movetap predates the field -- re-run "
              f"`python toolkit/clientscan/movetap.py` and pair the new file. "
              f"Nothing here is a fact about the client, and in particular it "
              f"is NOT 'the fence was never open'.")
        rc = 1
    else:
        if have < total:
            print(f"{indent}PARTIAL: {have} of {total} paired samples carry the "
                  f"field; the shares below are over {have}, not {total}.")
        # THE PRINTER AND THE CLASSIFIER ARE ONE FUNCTION NOW, AND THEY WERE TWO.
        # This sum read `str(k).startswith("unread:")`, which catches movetap's
        # own could-not-read sentinel and NOTHING ELSE, while `classify_reach`
        # -- the function every check in this file interrogates -- also lands a
        # label this file has never heard of in `unread`. So an UNRECOGNISED
        # `gate_reach` value was a hole to the dict and a REAL CLIENT STATE to
        # the printer, with a percentage beside it and nothing refusing: 9 rows
        # of `a-label-from-the-future` in 10 printed `90.0%` at rc 0. That is
        # C4's defect one section ABOVE C4's site, in the very distribution
        # `PROBE-GATEFIRE.md` §6 quotes. The BUCKET is printed per row for the
        # same reason: a share whose classification is not beside it is a number
        # the reader completes with whichever bucket they expected.
        unread = sum(c for k, c in counts.items()
                     if classify_reach(k) == "unread")
        for k, c in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"{indent}{str(k):34} {c:6d}  {100.0 * c / have:5.1f}%  "
                  f"{classify_reach(k)}")
        if legacy:
            print(f"{indent}NOTE: {legacy} of {have} row(s) carry movetap's "
                  f"pre-rename spelling (`:apply`) and are counted under the "
                  f"`:append` name above. Stored rows are not rewritable, so "
                  f"both spellings are accepted on read and only the new one "
                  f"is printed.")
        if unread_refuses(unread, have):
            # ...and the sentence says what the count now means. "could not
            # read the record" was true of the `unread:` sentinel and false of
            # a label this file has never heard of, and the second kind is
            # exactly what this refusal was blind to until 2026-08-20.
            print(f"{indent}REFUSED: {unread} of {have} carry no state this "
                  f"file can read -- a could-not-read sentinel, or a label it "
                  f"has never heard of. No share above is a fact about the "
                  f"client. This bar is over the WHOLE paired population and "
                  f"says nothing about the jump rows below, which carry their "
                  f"own.")
            rc = 1
    rows = fence_at_jumps(pairs, jumps)
    print(f"{indent}the fence at each hard jump (n={len(rows)}):")
    if not rows:
        print(f"{indent}  (no hard jump in this window -- the distribution "
              f"above is the whole result)")
    else:
        # The BEFORE column is 38 wide because the `missing:*` sentinels are up
        # to 36 characters and a name that overflows its column pushes the AT
        # column out of line -- which is how a table stops being readable at
        # exactly the rows that matter most.
        print(f"{indent}  server t     step   "
              f"{'fence BEFORE':38} fence AT")
        for t, step, be, at in rows:
            print(f"{indent}  {t:9.3f}  {step:7.1f}   {str(be):38} {str(at)}")
        print_jump_tally(rows, indent)
    if samples is None:
        pop = [s for _t, _p, s, _g in pairs]
        name = ("PAIRED sample(s) -- the caller passed no full sample stream, "
                "so consecutive here can skip unpaired samples")
    else:
        pop, name = samples, "movetap sample(s)"
    print_appender_witness(pop, indent, name)
    return rc


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


def _rec(head, cache=0, controlled=1, tail=0):
    """One 28-byte AgTrack state record, hex, exactly as movetap stores it.

    +0x00 clientControlled, +0x04 the history head, +0x08..+0x14 the
    last-appended position cache, +0x18 a time; STRIDE 0x1C.
    """
    words = (controlled, head, cache, cache, cache, cache, tail)
    return b"".join(w.to_bytes(4, "little") for w in words).hex()


def _fake_pair(t, reach=None, rec=None):
    """One `pair()` row -- (server_t, report_xy, sample, gap)."""
    s = {"t": float(t), "live": [0.0, 0.0, 0]}
    if reach is not None:
        s[FENCE_KEY] = reach
    if rec is not None:
        s["state_record"] = rec
    return (float(t), [0.0, 0.0], s, 0.0)


def _line_with(out, needle):
    """The ONE printed line carrying `needle`, or None if zero or many do.

    THE WHOLE LINE, so a check can compare it against a HAND-COMPUTED string
    rather than grep a substring out of it. Every hole this file has found in
    itself twice over is a number printed beside the wrong denominator, and a
    substring test passes on all of them: `"REFUSED" in out` is satisfied by a
    refusal that names any two integers at all. Returning None on a DUPLICATE
    as well as on an absence is deliberate -- a sentence printed twice with two
    different numbers in it is not a line anybody can quote.
    """
    hits = [ln for ln in out.splitlines() if needle in ln]
    return hits[0] if len(hits) == 1 else None


def _floor(name, n, want):
    """A section that judged fewer rows than a green run does has FAILED.

    Set from a real green run and never from a guess. A section whose fixtures
    stop matching prints PASS on nothing at all otherwise, which is the defect
    `test_codec.py` shipped with its glob matching zero files.
    """
    if n >= want:
        return 0
    print(f"   [FAIL] section {name} executed {n} check(s), below its floor of "
          f"{want}. A run that measured nothing failed.")
    return 1


def _selftest_jump_tally():
    """C4: the sentinel hole in the jump table, and the three-way tally.

    THE DEFECT THIS PINS, and it sat at the one number the whole probe turns on.
    `tested = sum(1 for ... if be == "test-runs")` was printed against
    `len(rows)`, so `be is None` -- the first paired sample, or a jump `t` that
    is not in `by_t` at all -- and `be == "unread:<why>"` were both swept into
    "The rest reached 0x00605840 ... the HISTORY APPENDER". A could-not-read
    counted as a real fence-shut, in the headline.
    """
    import contextlib
    import io
    bad = n = 0
    print("\n8. C4: the jump table is a THREE-WAY tally, and refuses on holes")

    # Every way a BEFORE cell can fail to be a state read, one row each.
    pairs = [_fake_pair(1, "shut:append"), _fake_pair(2, "shut:append"),
             _fake_pair(3, "test-runs"), _fake_pair(4, "test-runs"),
             _fake_pair(5, "shut:append"), _fake_pair(6),
             _fake_pair(7, "shut:append"), _fake_pair(8, "shut:append")]
    #        t=1 is FIRST, so it has no predecessor; t=9 was never paired;
    #        t=7's predecessor carries no `gate_reach` at all.
    jumps = [(1.0, 900.0, 0.0, 0.0, 0.1), (9.0, 900.0, 0.0, 0.0, 0.1),
             (3.0, 900.0, 0.0, 0.0, 0.1), (5.0, 900.0, 0.0, 0.0, 0.1),
             (7.0, 900.0, 0.0, 0.0, 0.1)]
    rows = fence_at_jumps(pairs, jumps)
    # THE ROW COUNT FIRST. A control that judges zero rows is a defect.
    ok = len(rows) == 5
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the fixture yields {len(rows)} jump "
          f"row(s) to judge -- counted before anything is judged")

    bes = [r[2] for r in rows]
    # THE DISTINCTNESS IS HALF THE CLAIM, and it was the unchecked half: the
    # subset test alone is satisfied when all three constants hold the SAME
    # string, so collapsing them to one name left this check green while its
    # own message still said "their OWN named sentinel" -- a check that cannot
    # fail on the sentence it prints.
    named = {MISSING_NO_PRIOR, MISSING_UNPAIRED, MISSING_NO_FIELD}
    ok = None not in bes and len(named) == 3 and named <= set(bes)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] all three ways a cell can fail "
          f"arrive as their OWN named sentinel, never as a bare None and never "
          f"as each other ({len(named)} distinct name(s)): "
          f"{sorted(set(bes) - {'shut:append', 'test-runs'})}")

    tl = jump_tally(rows)
    ok = (tl["reachable"] == 1 and tl["fenced"] == 1 and tl["unread"] == 3
          and tl["reachable"] + tl["fenced"] + tl["unread"] == tl["n"] == 5)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] reachable {tl['reachable']} + "
          f"fenced {tl['fenced']} + unread {tl['unread']} = {tl['n']}: the "
          f"three sum to n, and the 3 holes are NOT in the fenced count")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = print_jump_tally(rows)
    out = buf.getvalue()
    ok = (rc == 1 and "REFUSED" in out and "60%" in out
          and "began with the record in the ONE state" not in out)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] 3 of 5 rows unreadable is at or "
          f"above the {100 * UNREAD_REFUSE_SHARE:.0f}% bar, so the sentence is "
          f"REFUSED rather than qualified (rc {rc})")
    ok = "0x00605840 without any gate being evaluated" not in out
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the old sentence -- which "
          f"asserted an execution nobody observed -- is gone from the output")

    # ...AND THE TABLE IS STILL PRINTED ON THE REFUSING PATH. Deleting it while
    # keeping the tally and the refusal was green: the refusal names a total and
    # the table is the only place the three parts appear. A refusal that also
    # withholds the breakdown leaves the reader with the pre-C4 fold.
    seen = read_back_three_way(out)
    ok = (len(seen) == 3 and seen["reachable"][0] == tl["reachable"]
          and seen["fenced"][0] == tl["fenced"]
          and seen["unread"][0] == tl["unread"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the three-way table is PRINTED "
          f"even on the refusing path, and its cells read back as the dict "
          f"({ {k: v[0] for k, v in sorted(seen.items())} } against reachable "
          f"{tl['reachable']} / fenced {tl['fenced']} / unread {tl['unread']})")

    # THE BAR IS ONE CONSTANT NOW. It was two -- `unread * 4 >= n` in the code
    # beside a "25% bar" printed off `UNREAD_REFUSE_SHARE` -- so raising the
    # constant to 0.90 left the code refusing at 25% and the prose claiming 90%,
    # with everything green. Both directions, because a bar that only ever
    # loosens is as unchecked as one that never moves.
    g = globals()
    keep = g["UNREAD_REFUSE_SHARE"]
    try:
        g["UNREAD_REFUSE_SHARE"] = 0.90
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc90 = print_jump_tally(rows)
        out90 = buf.getvalue()
    finally:
        g["UNREAD_REFUSE_SHARE"] = keep
    ok = rc90 == 0 and "REFUSED" not in out90
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the bar the CODE enforces is "
          f"`UNREAD_REFUSE_SHARE` itself: at 0.90 the same 60% of holes is "
          f"under it and the sentence prints (rc {rc90})")

    # THE MIRROR, or the refusal above is a constant: the same machinery under
    # the bar must print the sentence, with all three counts.
    marks = [None, "shut:append", "shut:append", "test-runs", "shut:append",
             "unread:record-unreadable", "shut:append", "world1:append",
             "shut:noop", "test-runs", "shut:append"]
    pairs2 = [_fake_pair(t, marks[t]) for t in range(1, 11)]
    jumps2 = [(float(t), 900.0, 0.0, 0.0, 0.1) for t in range(2, 10)]
    rows2 = fence_at_jumps(pairs2, jumps2)
    ok = len(rows2) == 8
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the sub-bar fixture yields "
          f"{len(rows2)} row(s) -- counted before it is judged")
    tl2 = jump_tally(rows2)
    ok = (tl2["reachable"] == 1 and tl2["fenced"] == 6 and tl2["unread"] == 1
          and tl2["reachable"] + tl2["fenced"] + tl2["unread"] == 8)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] reachable {tl2['reachable']} + "
          f"fenced {tl2['fenced']} + unread {tl2['unread']} = 8, one hole at "
          f"12.5% -- under the bar")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc2 = print_jump_tally(rows2)
    out2 = buf.getvalue()
    ok = (rc2 == 0 and "REFUSED" not in out2
          and "1 of 8 snap(s) began with the record in the ONE state" in out2
          and "INFERENCE" in out2)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] so it prints the sentence (rc "
          f"{rc2}) -- as an INFERENCE with its premise named, not as an "
          f"observation")

    # ...and the bar TIGHTENS off the same constant. One hole in eight is 12.5%
    # and passes at 0.25; at 0.10 it must refuse, or `UNREAD_REFUSE_SHARE` is
    # only being read on the loosening side.
    try:
        g["UNREAD_REFUSE_SHARE"] = 0.10
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc10 = print_jump_tally(rows2)
        out10 = buf.getvalue()
    finally:
        g["UNREAD_REFUSE_SHARE"] = keep
    ok = (rc10 == 1 and "REFUSED" in out10 and "10% bar" in out10
          and "began with the record in the ONE state" not in out10)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and it TIGHTENS off the same "
          f"constant: at 0.10 the same 1-in-8 is at the bar and the sentence is "
          f"refused (rc {rc10}), with the printed bar naming 10% -- one number, "
          f"not two")

    # THE PRINTED CELLS, against a fixture whose three counts are ALL DIFFERENT.
    # The two fixtures above cannot catch a swap -- reachable and fenced are
    # both 1 in the first and reachable and unread are both 1 in the second --
    # and swapping two printed cells was one of the mutations that stayed green.
    # 2 / 5 / 1 makes every permutation of the three visible.
    marks3 = [None, "test-runs", "test-runs", "shut:append", "shut:append",
              "shut:noop", "world1:append", "shut:append",
              "unread:record-unreadable", "test-runs"]
    pairs3 = [_fake_pair(t, marks3[t]) for t in range(1, 10)]
    jumps3 = [(float(t), 900.0, 0.0, 0.0, 0.1) for t in range(2, 10)]
    rows3 = fence_at_jumps(pairs3, jumps3)
    tl3 = jump_tally(rows3)
    ok = (len(rows3) == 8 and tl3["reachable"] == 2 and tl3["fenced"] == 5
          and tl3["unread"] == 1)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the swap fixture yields "
          f"{len(rows3)} row(s) tallying reachable {tl3['reachable']} / fenced "
          f"{tl3['fenced']} / unread {tl3['unread']} -- three DIFFERENT numbers, "
          f"asserted before anything is read back")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc3 = print_jump_tally(rows3)
    out3 = buf.getvalue()
    seen3 = read_back_three_way(out3)
    ok = (rc3 == 0 and len(seen3) == 3
          and seen3["reachable"][0] == tl3["reachable"]
          and seen3["fenced"][0] == tl3["fenced"]
          and seen3["unread"][0] == tl3["unread"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the PRINTED cells are the dict's "
          f"own three counts, each in its own row "
          f"({ {k: v[0] for k, v in sorted(seen3.items())} }) -- a swapped "
          f"pair, a hard-wired 0 or a deleted table all fail here")
    ok = (_detail(tl3["labels"]["fenced"]) in seen3["fenced"][1]
          and _detail(tl3["labels"]["unread"]) in seen3["unread"][1]
          and _detail(tl3["labels"]["unread"]) not in seen3["fenced"][1])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and each breakdown sits beside its "
          f"OWN count -- fenced `{_detail(tl3['labels']['fenced'])}`, unread "
          f"`{_detail(tl3['labels']['unread'])}` -- so printing one where the "
          f"other belongs is caught, not just printing something")

    # THE TABLE'S OTHER TWO PRINTED NUMBERS, and they were the ones still free.
    # Every check above reads the three CELLS. The header's "and they sum to
    # {n}" and the refusal's "{unread} of {n} jump row(s) ({pct}%)" were read by
    # nothing at all, so repointing EITHER at `reachable + fenced` -- dropping
    # the unread-or-missing holes out of the denominator, which is the pre-C4
    # defect restated as a fraction -- was green through this selftest AND
    # `test_movesync.py`. Both lines are compared WHOLE against a hand-computed
    # string here, because the sentence is what §6 quotes and a substring test
    # ("REFUSED" in out) is satisfied by a refusal naming any two integers.
    #
    # THE FIXTURE IS BUILT SO NO ARITHMETIC COINCIDENCE CAN SATISFY THEM: the
    # three cells are 1 / 2 / 3, their sum is 6, and `reachable + fenced` is 3
    # -- four numbers, all different, and 3 of 6 (50%) reads 100% over the
    # narrowed denominator. Every fixture above has two cells sharing a value.
    marks4 = [None, "test-runs", "shut:append", "world1:append",
              "unread:record-unreadable", None, "a-label-from-the-future",
              "shut:append"]
    pairs4 = [_fake_pair(t, marks4[t]) for t in range(1, 8)]
    jumps4 = [(float(t), 900.0, 0.0, 0.0, 0.1) for t in range(2, 8)]
    rows4 = fence_at_jumps(pairs4, jumps4)
    tl4 = jump_tally(rows4)
    narrowed = tl4["reachable"] + tl4["fenced"]
    ok = (len(rows4) == 6 and tl4["n"] == 6 and tl4["reachable"] == 1
          and tl4["fenced"] == 2 and tl4["unread"] == 3 and narrowed == 3
          and len({tl4["reachable"], tl4["fenced"], tl4["unread"],
                   tl4["n"]}) == 4 and narrowed != tl4["n"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the pinned-line fixture yields "
          f"{len(rows4)} row(s) at reachable {tl4['reachable']} / fenced "
          f"{tl4['fenced']} / unread {tl4['unread']}, summing to {tl4['n']} "
          f"while `reachable + fenced` is {narrowed} -- four DIFFERENT numbers, "
          f"counted before a line is read")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc4 = print_jump_tally(rows4)
    out4 = buf.getvalue()
    hdr = _line_with(out4, "THREE-WAY over the BEFORE column")
    want_hdr = "     THREE-WAY over the BEFORE column, and they sum to 6:"
    ok = hdr == want_hdr
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the HEADER line is exactly "
          f"{want_hdr!r} -- it sums the three-way tally over all {tl4['n']} "
          f"rows and not over the {narrowed} that carry a state; got {hdr!r}")
    ref = _line_with(out4, "could not be classified")
    want_ref = ("     REFUSED: 3 of 6 jump row(s) (50%) could not be "
                "classified, at or above the 25% bar. There is no sentence "
                "about the client available from 6 row(s) with that many holes "
                "in them.")
    ok = rc4 == 1 and ref == want_ref
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the REFUSAL line is exactly "
          f"{want_ref!r} (rc {rc4}) -- 3 of 6 is 50%, where the same 3 over "
          f"the {narrowed} classified rows would read 100%, so a narrowed "
          f"denominator cannot print this line")
    # THE REFUSAL'S SECOND LINE CARRIES A THIRD FREE `n`, and it is the one
    # that tells the reader the population refusal upstairs is NOT this bar.
    # Repointing it at `narrowed` (3) said "this bar is over these 3" beside a
    # refusal that had just said 3 of 6 -- a sentence that reads as though the
    # holes were the whole population -- and nothing anywhere failed.
    stand = _line_with(out4, "population refusal above cannot stand in")
    want_stand = ("     ...and the population refusal above cannot stand in "
                  "for this one: it is a different denominator over a "
                  "different population -- every paired sample, hundreds of "
                  "rows -- while this bar is over these 6.")
    ok = stand == want_stand
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the line that separates the two "
          f"refusals is exactly {want_stand!r} -- it names {tl4['n']}, every "
          f"jump row, and not the {narrowed} that carry a state; got "
          f"{stand!r}")

    # THE SENTENCE ITSELF, WHOLE, AND IT WAS THE LAST FREE NUMBER IN HERE. Both
    # lines above are on the REFUSING path. The path that PRINTS was checked by
    # one substring -- `"1 of 8 snap(s) began with the record in the ONE state"
    # in out2` -- which says nothing at all about the SECOND half of the same
    # sentence, so `{tl['fenced']}` -> `{tl['unread']}` was `--selftest` 75/75
    # and `test_movesync.py` green while printing the HOLE count as the number
    # of snaps that began fenced. That is the pre-C4 fold arriving through the
    # printer instead of through the tally, into the one sentence
    # `PROBE-GATEFIRE.md` §6 quotes as its H1 evidence.
    #
    # NO ARITHMETIC COINCIDENCE CAN SATISFY IT: 3 / 8 / 1 sum to 12, and every
    # cell differs from every other cell, from n, from `reachable + fenced`
    # (11) and from `n - reachable` (9) -- so a swap, a borrowed denominator or
    # a substituted count all move a printed digit. One hole in twelve is 8%,
    # under the bar, so the sentence prints rather than refusing.
    marks5 = [None, "test-runs", "test-runs", "test-runs",
              "shut:append", "shut:append", "shut:append",
              "shut:noop", "shut:noop", "shut:noop",
              "world1:append", "world1:append",
              "unread:record-unreadable", "shut:append"]
    pairs5 = [_fake_pair(t, marks5[t]) for t in range(1, 14)]
    jumps5 = [(float(t), 900.0, 0.0, 0.0, 0.1) for t in range(2, 14)]
    rows5 = fence_at_jumps(pairs5, jumps5)
    tl5 = jump_tally(rows5)
    narrowed5 = tl5["reachable"] + tl5["fenced"]
    ok = (len(rows5) == 12 and tl5["n"] == 12 and tl5["reachable"] == 3
          and tl5["fenced"] == 8 and tl5["unread"] == 1 and narrowed5 == 11
          and len({tl5["reachable"], tl5["fenced"], tl5["unread"], tl5["n"],
                   narrowed5, tl5["n"] - tl5["reachable"]}) == 6
          and not unread_refuses(tl5["unread"], tl5["n"]))
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the SUCCESS-sentence fixture yields "
          f"{len(rows5)} row(s) at reachable {tl5['reachable']} / fenced "
          f"{tl5['fenced']} / unread {tl5['unread']}, summing to {tl5['n']} "
          f"with `reachable + fenced` {narrowed5} and `n - reachable` "
          f"{tl5['n'] - tl5['reachable']} -- six DIFFERENT numbers, one hole in "
          f"twelve so the bar does not fire, all counted before a line is read")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc5 = print_jump_tally(rows5)
    out5 = buf.getvalue()
    sent = _line_with(out5, "snap(s) began with the record in the ONE state")
    want_sent = ("     3 of 12 snap(s) began with the record in the ONE state "
                 "where 0x006055E0 is reached; 8 began in a state whose branch "
                 "is 0x00605840 or a bare return.")
    ok = rc5 == 0 and sent == want_sent
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the SENTENCE is exactly "
          f"{want_sent!r} (rc {rc5}) -- BOTH halves, so the `{tl5['fenced']}` "
          f"after the semicolon can no longer be the unread count "
          f"({tl5['unread']}), the reachable count ({tl5['reachable']}), the "
          f"total ({tl5['n']}) or `n - reachable` "
          f"({tl5['n'] - tl5['reachable']}); got {sent!r}")
    return bad + _floor("8", n, 20), n


def _selftest_appender_witness():
    """C5: the two positive observations, and the zero it refuses to print."""
    import contextlib
    import io
    bad = n = 0
    print("\n9. C5: the appender witness -- a WRITE observed, not a state read")

    blind = [{"t": 0.0, "live": [0, 0, 0]}, {"t": 0.1, "live": [0, 0, 0]}]
    w = appender_witness(blind)
    ok = w["adjacent"] == 1 and w["judged"] == 0 and w["unjudgeable"] == 1
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a movetap with no `state_record` "
          f"judges {w['judged']} of {w['adjacent']} pair(s) -- the fixture is "
          f"counted, so the refusal below is not vacuous")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = print_appender_witness(blind)
    out = buf.getvalue()
    ok = rc == 1 and "REFUSED" in out and "NOT 'the appender never ran'" in out
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and it REFUSES (rc {rc}) instead of "
          f"printing 0 witnessed -- a zero here would read as 'the appender "
          f"never ran'")

    def _s(t, rec, reach="shut:append"):
        return {"t": t, "live": [0, 0, 0], "state_record": rec,
                FENCE_KEY: reach}

    head = appender_witness([_s(0.0, _rec(0x1000, 1)), _s(0.1, _rec(0x2000, 1))])
    ok = (head["judged"] == 1 and head["head_changed"] == 1
          and head["cache_changed"] == 0 and head["witnessed"] == 1)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] hist_head 0x1000 -> 0x2000 is "
          f"witnessed ({head['witnessed']} of {head['judged']}): a node was "
          f"allocated between two reads")

    # THE OR ARM, and it is the reason this is not a hist_head detector. The
    # cache moves on appends that allocate no node, so a head-only tally misses
    # them and would print a silence that is an artifact of the arm chosen.
    cache = appender_witness([_s(0.0, _rec(0x1000, 1)), _s(0.1, _rec(0x1000, 2))])
    ok = (cache["judged"] == 1 and cache["head_changed"] == 0
          and cache["cache_changed"] == 1 and cache["witnessed"] == 1)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and a +0x08..+0x14 cache change "
          f"with the head UNMOVED is witnessed too "
          f"({cache['witnessed']} of {cache['judged']}) -- the tally is the OR "
          f"of both arms, not hist_head alone")

    static = appender_witness([_s(0.0, _rec(0x1000, 1)), _s(0.1, _rec(0x1000, 1))])
    ok = static["judged"] == 1 and static["witnessed"] == 0
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] CONTROL: an unchanged record over a "
          f"judged pair witnesses {static['witnessed']} -- the count reads the "
          f"bytes and is not a constant")

    # ARM (b): a head that returns to 0 while the fence label does not move.
    zero = appender_witness([_s(0.0, _rec(0x1000, 1)), _s(0.1, _rec(0, 1))])
    ok = zero["reach_pairs"] == 1 and zero["head_to_zero"] == 1
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] hist_head -> 0 with gate_reach "
          f"UNCHANGED: {zero['head_to_zero']} of {zero['reach_pairs']} -- an "
          f"arm or a Clear ran BETWEEN two samples")
    moved = appender_witness([_s(0.0, _rec(0x1000, 1)),
                              _s(0.1, _rec(0, 1), "test-runs")])
    ok = moved["reach_pairs"] == 0 and moved["head_to_zero"] == 0
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] CONTROL: the same head -> 0 with "
          f"gate_reach CHANGING scores {moved['head_to_zero']} of "
          f"{moved['reach_pairs']} -- arm (b) needs the label held still, or it "
          f"is just the fence moving")
    # ...AND THE OTHER HALF OF ARM (b), WHICH NO FIXTURE ANYWHERE EXERCISED.
    # The guard is `ha != 0 and hb == 0`, and every fixture in this file and in
    # `test_movesync.py` starts from a NON-ZERO head -- so dropping the first
    # conjunct to a bare `hb == 0` was green through all 65 selftest checks and
    # all 150 of the suite's. What that mutation does is score EVERY held-still
    # consecutive pair of an agent whose history chain is already empty as "an
    # arm or an AgTrack::Clear ran BETWEEN two samples", which is the aliasing
    # witness the probe reads to decide between polling and paying for a hook
    # DLL. A false positive here is the expensive direction, so the case is
    # pinned: a head that was ALREADY 0 across a held-still pair is a TRANSITION
    # THAT DID NOT HAPPEN.
    empty_chain = [_s(0.0, _rec(0, 1)), _s(0.1, _rec(0, 1))]
    already = appender_witness(empty_chain)
    ok = already["judged"] == 1 and already["reach_pairs"] == 1
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] CONTROL: a head ALREADY 0 across a "
          f"label-held-still pair is judged and reaches arm (b)'s denominator "
          f"({already['reach_pairs']} pair(s), {already['judged']} judged) -- "
          f"asserted non-zero FIRST, because a control that judges zero rows "
          f"cannot refute anything")
    ok = already["head_to_zero"] == 0
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and it scores "
          f"{already['head_to_zero']} of {already['reach_pairs']} -- 0 -> 0 is "
          f"not a head RETURNING to 0, so nothing ran between these two reads; "
          f"a bare `hb == 0` reads 1 of 1 here and calls an empty chain an arm")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_z = print_appender_witness(empty_chain)
    out_z = buf.getvalue()
    arm_b = _line_with(out_z, "(b) hist_head -> 0 with gate_reach UNCHANGED")
    want_b = ("     (b) hist_head -> 0 with gate_reach UNCHANGED: 0 of 1 "
              "pair(s) where both gate_reach reads are real and equal. EACH "
              "SUCH PAIR is an arm or an AgTrack::Clear running BETWEEN two "
              "samples -- an aliasing witness that does not depend on the "
              "state field whose aliasing is the question.")
    ok = rc_z == 0 and arm_b == want_b
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the PRINTED arm (b) line is "
          f"exactly {want_b!r} (rc {rc_z}) -- the sentence asserts an event, so "
          f"the 0 in front of it is the whole of what makes it true; got "
          f"{arm_b!r}")

    unread = appender_witness([_s(0.0, _rec(0x1000, 1), "unread:record-unreadable"),
                               _s(0.1, _rec(0, 1), "unread:record-unreadable")])
    ok = unread["reach_pairs"] == 0
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and two equal `unread:` labels are "
          f"NOT 'unchanged' ({unread['reach_pairs']} pair(s) judged for arm b) "
          f"-- equality between two could-not-reads is not a fact")

    # ...AND THE OTHER HALF OF THAT REFUSAL, WHICH THE GATE WAS SPELLED WRONG
    # FOR. `not ra.startswith("unread:")` admits everything that is not
    # movetap's own sentinel, so a label this file has never heard of was a
    # REAL state in arm (b)'s denominator -- while `classify_reach`, the
    # function every check above interrogates, calls it a hole. The fixture
    # below is the `unread:` one with the ONE thing changed that the old gate
    # could not see, and it is the same printer-vs-classifier disagreement
    # section 11 pins one screen down, arriving here in a DENOMINATOR instead
    # of in a share.
    future_label = "a-label-from-the-future"
    future = [_s(0.0, _rec(0x1000, 1), future_label),
              _s(0.1, _rec(0, 1), future_label)]
    wf = appender_witness(future)
    ok = (wf["adjacent"] == 1 and wf["judged"] == 1
          and classify_reach(future_label) == "unread"
          and not future_label.startswith("unread:"))
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the unrecognised-label fixture is "
          f"{wf['judged']} of {wf['adjacent']} pair(s) JUDGED, held still at "
          f"`{future_label}` -- which `classify_reach` calls "
          f"`{classify_reach(future_label)}` while the retired "
          f"`unread:`-prefix rule called it real; counted first, because a "
          f"control that judges zero rows cannot refute anything")
    ok = wf["reach_pairs"] == 0 and wf["head_to_zero"] == 0
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and it enters NEITHER arm-(b) "
          f"count ({wf['head_to_zero']} of {wf['reach_pairs']}), where the old "
          f"gate scored this exact 0x1000 -> 0 as 1 of 1 -- an aliasing witness "
          f"minted out of a state nobody can name")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_appender_witness([_s(0.0, _rec(0x1000, 1)), _s(0.1, _rec(0x2000, 2))])
    out = buf.getvalue()
    ok = ("0x0060593A" in out and "2500 ms" in out and "shut:noop" in out)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] both limits print beside the "
          f"counts: the 2500 ms dedup at 0x0060593A, and `shut:noop` writing "
          f"nothing at all")

    # LIMIT 1 SAID SOMETHING THE IMAGE REFUTES, and the only check on it was the
    # substring pair above -- which is satisfied by every sentence containing
    # "2500 ms" and "0x0060593A", including the wrong one. `0x0060593A jg
    # 0x605A2F` is the FIRST test of a chain (0x0060594B, 0x0060595E,
    # 0x0060596B, 0x0060597B), each of which jumps to the SAME append target on
    # INEQUALITY, so "it cannot append twice inside that window" is false of a
    # MOVING agent. The retired clause is asserted ABSENT and the chain asserted
    # PRESENT, address by address, so neither half can drift back.
    retired = "cannot append twice inside that window"
    want_chain = [f"0x{va:08X}" for va in APPEND_DEDUP_CHAIN]
    missing = [a for a in want_chain if a not in out]
    ok = (retired not in out and not missing and len(APPEND_DEDUP_CHAIN) == 4
          and f"0x{APPEND_TARGET:08X}" in out
          and "AND the sample still matches the cached one" in out)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] LIMIT 1 states the CONDITIONAL "
          f"window the image supports -- younger than 2500 ms AND matching the "
          f"cache -- naming all {len(APPEND_DEDUP_CHAIN)} further tests "
          f"({', '.join(want_chain)}) and the one target "
          f"0x{APPEND_TARGET:08X}; the retired \"{retired}\" clause is gone "
          f"(missing addresses: {missing or 'none'})")

    # ...and those addresses are READ FROM THE CONSTANTS, not typed into the
    # sentence. A check that greps a hard-coded literal certifies the literal.
    g9 = globals()
    keep_chain, keep_target = g9["APPEND_DEDUP_CHAIN"], g9["APPEND_TARGET"]
    try:
        g9["APPEND_DEDUP_CHAIN"] = (0x00111111,)
        g9["APPEND_TARGET"] = 0x00222222
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            print_appender_witness([_s(0.0, _rec(0x1000, 1)),
                                    _s(0.1, _rec(0x2000, 2))])
        outc = buf.getvalue()
    finally:
        g9["APPEND_DEDUP_CHAIN"], g9["APPEND_TARGET"] = keep_chain, keep_target
    ok = ("0x00111111" in outc and "0x00222222" in outc
          and all(a not in outc for a in want_chain))
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] CONTROL: moving "
          f"`APPEND_DEDUP_CHAIN`/`APPEND_TARGET` moves every address in the "
          f"printed sentence -- the text is generated from the constants a "
          f"reader can audit, not from four literals nothing feeds")

    # THE MALFORMED RECORD, which is the `except ValueError` arm of
    # `state_fields`. Returning `0, "00"` there was fully green: a zero head is
    # a REAL head value (an empty chain), so a not-read wearing one is
    # indistinguishable from a client that emptied its history -- the same
    # family of defect as the sentinel hole C4 closed, one level down.
    junk = "zz" + "00" * 27          # 56 chars: long enough, not hex
    ok = state_fields({"state_record": junk}) == (None, None)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a `state_record` that is not hex "
          f"reads back {state_fields({'state_record': junk})} -- None per "
          f"field, never a 0 that means an empty history")
    ok = state_fields({"state_record": junk, "hist_head": 0x1234}) == (0x1234, None)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] ...and it falls back to the row's "
          f"own `hist_head` when there is one "
          f"({state_fields({'state_record': junk, 'hist_head': 0x1234})}) -- "
          f"the fallback is the documented path, and 0x1234 is not 0")
    wj = appender_witness([{"t": 0.0, "state_record": junk, FENCE_KEY: "shut:append"},
                           {"t": 0.1, "state_record": junk, FENCE_KEY: "shut:append"}])
    ok = wj["adjacent"] == 1 and wj["judged"] == 0 and wj["unjudgeable"] == 1
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] so a pair of malformed records is "
          f"UNJUDGEABLE ({wj['judged']} judged, {wj['unjudgeable']} "
          f"unjudgeable) rather than a judged pair that witnessed nothing")

    # --- THE PRINTED NUMBERS, not the dict behind them -----------------------
    #
    # Everything above asks `appender_witness` for a dict. What travels into
    # PROBE-GATEFIRE.md is the TEXT, and the two were free to disagree: arm
    # (a)'s printed `witnessed` hard-wired to 0, `judged` substituted for
    # `reach_pairs` as arm (b)'s DENOMINATOR, and the arm-coverage and PARTIAL
    # lines deleted outright were each fully green.
    #
    # ONE FIXTURE, BUILT SO THE SUBSTITUTIONS ARE VISIBLE. Every number below
    # differs from the ones a mutation would put in its place -- in particular
    # `judged` (8) != `reach_pairs` (6), so arm (b) borrowing arm (a)'s
    # denominator is caught, which two equal numbers would have waved through.
    # (`judged` and `head_pairs` are equal BY CONSTRUCTION and not by luck:
    # `state_fields` only ever returns a cache when it returned a head, so
    # cache-readable implies head-readable and no fixture can separate them.)
    mixed = [_s(0.0, _rec(0x1000, 1)),                  # p01 head+cache move
             _s(0.4, _rec(0x2000, 2)),
             {"t": 0.8, "live": [0, 0, 0], FENCE_KEY: "shut:append"},  # blind
             _s(1.2, _rec(0x3000, 2)),                  # p23 unjudgeable too
             _s(1.6, _rec(0, 2)),                       # p34 head -> 0
             _s(2.0, _rec(0, 2), "test-runs"),          # p45 label moves
             {"t": 2.4, "live": [0, 0, 0], "hist_head": 0x4000,
              FENCE_KEY: "test-runs"},                  # p56 head-only read
             _s(2.8, _rec(0x4000, 5), "test-runs"),     # p67 no change
             _s(3.2, _rec(0x4000, 9), "test-runs"),     # p78 cache alone
             _s(3.6, _rec(0x5000, 9), "test-runs"),     # p89 head alone
             _s(4.0, _rec(0x5000, 9), "test-runs")]     # p9-10 nothing
    wm = appender_witness(mixed)
    ok = (wm["adjacent"] == 10 and wm["judged"] == 8 and wm["unjudgeable"] == 2
          and wm["witnessed"] == 5 and wm["head_changed"] == 4
          and wm["cache_changed"] == 2 and wm["head_pairs"] == 8
          and wm["cache_pairs"] == 6 and wm["reach_pairs"] == 7
          and wm["head_to_zero"] == 1)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the read-back fixture judges "
          f"{wm['judged']} of {wm['adjacent']} pair(s) at "
          f"witnessed {wm['witnessed']} / head {wm['head_changed']} / cache "
          f"{wm['cache_changed']} / reach {wm['reach_pairs']} -- counted "
          f"BEFORE the printout is read, and no two of them collide")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rcm = print_appender_witness(mixed)
    outm = buf.getvalue()
    got = read_back_witness(outm)
    ok = (rcm == 0 and got.get("witnessed") == wm["witnessed"]
          and got.get("judged") == wm["judged"]
          and got.get("head_changed") == wm["head_changed"]
          and got.get("cache_changed") == wm["cache_changed"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] arm (a) PRINTS the dict's own "
          f"numbers: {got.get('witnessed')} of {got.get('judged')}, head "
          f"{got.get('head_changed')} / cache {got.get('cache_changed')} -- a "
          f"hard-wired zero or a borrowed count fails here")
    ok = (got.get("head_pairs") == wm["head_pairs"]
          and got.get("cache_pairs") == wm["cache_pairs"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the ARM-COVERAGE line is printed "
          f"and carries {got.get('head_pairs')} / {got.get('cache_pairs')} -- "
          f"deleting it leaves the two arm counts with no denominator at all, "
          f"which is the shape C4 was about")
    ok = (got.get("head_to_zero") == wm["head_to_zero"]
          and got.get("reach_pairs") == wm["reach_pairs"]
          and wm["reach_pairs"] != wm["judged"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] arm (b) prints "
          f"{got.get('head_to_zero')} of {got.get('reach_pairs')} and NOT of "
          f"{wm['judged']} -- its denominator is the label-held-still "
          f"population, and the two differ in this fixture on purpose")
    ok = (got.get("partial_judged") == wm["judged"]
          and got.get("partial_adjacent") == wm["adjacent"]
          and got.get("partial_unjudgeable") == wm["unjudgeable"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the PARTIAL line is printed "
          f"whenever a pair could not be read: {got.get('partial_judged')} of "
          f"{got.get('partial_adjacent')} judged, "
          f"{got.get('partial_unjudgeable')} unjudgeable -- deleting it hides "
          f"that the arms above are over a subset")
    return bad + _floor("9", n, 24), n


def _selftest_spellings():
    """C9: two spellings accepted on read, one printed, none inventing a state."""
    import contextlib
    import io
    bad = n = 0
    print("\n10. C9: the vault's OLD `:apply` rows are read, and printed `:append`")

    got = {k: classify_reach(k) for k in
           ("shut:apply", "world1:apply", "shut:append", "world1:append",
            "shut:noop", "test-runs", "unread:record-unreadable",
            "a-label-from-the-future", None)}
    ok = (got["shut:apply"] == "fenced" and got["world1:apply"] == "fenced"
          and got["shut:append"] == "fenced" and got["shut:noop"] == "fenced"
          and got["test-runs"] == "reachable")
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the pre-rename spellings classify "
          f"as the SAME state as the new ones -- a capture written before "
          f"2026-08-20 is read, not silently dropped into the hole bucket")
    ok = (got["unread:record-unreadable"] == "unread" and got[None] == "unread"
          and got["a-label-from-the-future"] == "unread")
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] while a could-not-read, a missing "
          f"sample and a label this file has never heard of all land in "
          f"`unread` -- refusing to guess is the point of the third bucket")

    legacy = [_fake_pair(1, "shut:apply", _rec(0x1000, 1)),
              _fake_pair(2, "test-runs", _rec(0x2000, 2))]
    counts, have, total, nleg = fence_rows(legacy)
    ok = (have == 2 and total == 2 and nleg == 1
          and counts.get("shut:append") == 1 and "shut:apply" not in counts)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] fence_rows tallies the old row "
          f"under the NEW key ({counts}) and reports {nleg} legacy-spelled "
          f"row(s) as provenance")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_fence(legacy, [(2.0, 900.0, 400.0, 20.0, 1.0)])
    out = buf.getvalue()
    ok = "shut:append" in out and "shut:apply" not in out
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the printed output carries "
          f"`shut:append` and never `shut:apply` -- both read, one printed")
    ok = "pre-rename spelling" in out
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] with a NOTE saying the row was "
          f"normalised, because a normalisation the reader cannot see is one "
          f"they cannot audit")
    ok = ("without any gate being evaluated" not in out
          and "INFERENCE" in out
          and "never the instruction pointer" in out)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and every sentence about "
          f"0x00605840 running is labelled an INFERENCE with its premise "
          f"named -- the sampler reads a record, never the instruction pointer")
    return bad + _floor("10", n, 6), n


# The lines `print_fence` emits, keyed off a distinctive substring of the
# sentence that carries each number, for the same reason `_WITNESS_FIELDS` is:
# a deleted line must arrive as an ABSENT KEY and never as a zero.
_FENCE_LINES = (
    ("refused_unread", r"REFUSED: (\d+) of \d+ carry no state this file can read"),
    ("refused_have", r"REFUSED: \d+ of (\d+) carry no state this file can read"),
    ("partial_have", r"PARTIAL: (\d+) of \d+ paired samples carry the field"),
    ("partial_total", r"PARTIAL: \d+ of (\d+) paired samples carry the field"),
    ("partial_says_have", r"the shares below are over (\d+), not \d+"),
    ("partial_says_total", r"the shares below are over \d+, not (\d+)"),
    ("note_legacy", r"NOTE: (\d+) of \d+ row\(s\) carry movetap's"),
    ("note_den", r"NOTE: \d+ of (\d+) row\(s\) carry movetap's"),
    ("witness_pairs", r"over (\d+) consecutive pair\(s\) of \d+ "),
    ("witness_pop", r"over \d+ consecutive pair\(s\) of (\d+) "),
    ("jump_n", r"the fence at each hard jump \(n=(\d+)\)"),
)


def read_back_fence(out):
    """{field: printed_int} parsed from `print_fence`'s own text."""
    seen = {}
    for name, pat in _FENCE_LINES:
        m = re.search(pat, out)
        if m:
            seen[name] = int(m.group(1))
    return seen


def _dist_row(out, label):
    """(count, share, bucket) off the distribution row for `label`, or None.

    THE WHOLE ROW AND NOT THE SHARE ALONE. This used to read the percentage and
    stop, which left the printer free to disagree with `classify_reach` about
    what the row IS: an unrecognised label printed as a real client state at
    90.0% while the classifier called it a hole. Reading the bucket column here
    is what makes that disagreement a FAIL rather than a paragraph in §6.
    """
    m = re.search(r"^\s*" + re.escape(label)
                  + r"\s+(\d+)\s+([\d.]+)%\s+(\S+)\s*$", out, re.M)
    return (int(m.group(1)), float(m.group(2)), m.group(3)) if m else None


def _selftest_print_fence():
    """C4+C5 IN THE REPORT: what `main()` actually prints, not what it could.

    THE DEFECT THIS PINS, and it is the same one twice at two altitudes. The
    round before this pinned the jump tally at the DICT while the operator reads
    the TEXT. This round found the text pinned at the FUNCTION while the
    operator reads the PIPELINE: deleting `print_appender_witness(pop, indent,
    name)` from `print_fence` -- the only path `main()` takes -- left
    `--selftest` at 49/49 and `test_movesync.py` at 147/147, with the whole of
    C5 gone from the output. Six more branches of `print_fence` judged ZERO rows
    in the entire suite and every mutation of them was green: the PARTIAL line
    deleted, the per-label share denominator moved from `have` to `total`, the
    `samples=` stream ignored while the population was still NAMED as the full
    one, the population REFUSAL deleted, the legacy NOTE quoting `total` where
    it means `have`, and `if rc: return rc` making the population refusal
    swallow the tally and the witness -- which is precisely the substitution C4
    exists to undo.

    ONE FIXTURE TAKES ALL OF IT, because these branches only co-occur on the
    production path: `samples=` supplied AND `have < total` AND unread at or
    above the bar. Every number in it is distinct from the one a substitution
    would put in its place.
    """
    import contextlib
    import io
    bad = n = 0
    print("\n11. C4+C5 in the REPORT: print_fence's own output, refusal and all")

    rec = _rec(0x1000, 1)
    pairs = [_fake_pair(1), _fake_pair(2),
             _fake_pair(3, "shut:apply", rec), _fake_pair(4, "shut:append", rec),
             _fake_pair(5, "shut:append", rec), _fake_pair(6, "test-runs", rec),
             _fake_pair(7, "unread:record-unreadable"),
             _fake_pair(8, "unread:record-unreadable")]
    jumps = [(float(t), 900.0, 400.0, 20.0, 0.1) for t in (5, 6, 7)]
    counts, have, total, legacy = fence_rows(pairs)
    rows = fence_at_jumps(pairs, jumps)
    tl = jump_tally(rows)
    # THE COUNTS FIRST, AND THEY ARE ALL DIFFERENT. 6 != 8 makes a `have`/`total`
    # swap visible; 3 of 6 shut:append is 50.0% over `have` and 37.5% over
    # `total`; 2 of 6 unread is over the 25% bar while 2 of 8 would be AT it, so
    # the refusal below is over the population the code claims.
    ok = (len(pairs) == 8 and have == 6 and total == 8 and legacy == 1
          and counts.get("shut:append") == 3 and counts.get("test-runs") == 1
          and counts.get("unread:record-unreadable") == 2
          and len(rows) == 3 and tl["reachable"] == 1 and tl["fenced"] == 2
          and tl["unread"] == 0)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the fixture carries {have} of "
          f"{total} paired samples with the field ({legacy} legacy-spelled, "
          f"{counts.get('unread:record-unreadable')} unread) and {len(rows)} "
          f"jump row(s) tallying {tl['reachable']}/{tl['fenced']}/"
          f"{tl['unread']} -- counted before print_fence is called at all")

    def _s11(t, head, cache):
        return {"t": t, "live": [0, 0, 0], "state_record": _rec(head, cache),
                FENCE_KEY: "shut:append"}
    samples = [_s11(0.0, 0x1000, 1), _s11(0.4, 0x2000, 1), _s11(0.8, 0x2000, 2),
               _s11(1.2, 0x2000, 2), _s11(1.6, 0x3000, 2), _s11(2.0, 0x3000, 3),
               _s11(2.4, 0x3000, 3), _s11(2.8, 0x4000, 3), _s11(3.2, 0x4000, 4),
               _s11(3.6, 0x4000, 4), _s11(4.0, 0x5000, 4)]
    wfull = appender_witness(samples)
    wpaired = appender_witness([s for _t, _p, s, _g in pairs])
    ok = (len(samples) == 11 and wfull["adjacent"] == 10
          and wfull["judged"] == 10 and wfull["witnessed"] == 7
          and wpaired["adjacent"] == 7 and wpaired["judged"] == 3
          and wpaired["witnessed"] == 0)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the FULL sample stream is a "
          f"different population from the paired subset: {len(samples)} "
          f"sample(s) / {wfull['judged']} judged / {wfull['witnessed']} "
          f"witnessed against {len(pairs)} / {wpaired['judged']} / "
          f"{wpaired['witnessed']} -- so a printer that quietly uses the subset "
          f"cannot print the same numbers")

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = print_fence(pairs, jumps, samples=samples)
    out = buf.getvalue()
    got = read_back_fence(out)
    ok = (rc == 1 and got.get("refused_unread") == 2
          and got.get("refused_have") == have)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the POPULATION refusal fires and "
          f"names its own denominator: {got.get('refused_unread')} of "
          f"{got.get('refused_have')} carry no state this file can read "
          f"(rc {rc})")

    ok = (got.get("partial_have") == have and got.get("partial_total") == total
          and got.get("partial_says_have") == have
          and got.get("partial_says_total") == total)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the PARTIAL line prints "
          f"{got.get('partial_have')} of {got.get('partial_total')} and says "
          f"the shares are over {got.get('partial_says_have')}, not "
          f"{got.get('partial_says_total')} -- deleting it hides that every "
          f"share below is over a subset")

    row = _dist_row(out, "shut:append")
    share = row[1] if row else None
    over_have = round(100.0 * counts["shut:append"] / have, 1)
    over_total = round(100.0 * counts["shut:append"] / total, 1)
    ok = (row is not None and row[0] == counts["shut:append"]
          and abs(share - over_have) < 0.05
          and abs(share - over_total) > 0.05 and row[2] == "fenced")
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the per-label shares really are "
          f"over `have`: shut:append prints {share}% in bucket "
          f"`{row[2] if row else None}`, where {counts['shut:append']}/{have} "
          f"is {over_have}% and the same count over {total} would be "
          f"{over_total}%")

    ok = got.get("note_legacy") == legacy and got.get("note_den") == have
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the legacy NOTE's denominator is "
          f"`have` too: it prints {got.get('note_legacy')} of "
          f"{got.get('note_den')} row(s) carrying the pre-rename spelling, "
          f"where `have` is {have} and `total` is {total}")

    # THE ORDER IS THE CLAIM. `print_fence`'s docstring says the tally and the
    # witness print on every path INCLUDING the refusing one; inserting
    # `if rc: return rc` above them was green, and that is one refusal standing
    # in for two others.
    i_ref = out.find("carry no state this file can read")
    i_tal = out.find("THREE-WAY over the BEFORE column")
    i_wit = out.find("APPENDER WITNESS")
    seen3 = read_back_three_way(out)
    ok = (-1 < i_ref < i_tal < i_wit and len(seen3) == 3
          and seen3["reachable"][0] == tl["reachable"]
          and seen3["fenced"][0] == tl["fenced"]
          and seen3["unread"][0] == tl["unread"]
          and got.get("jump_n") == len(rows)
          and "1 of 3 snap(s) began with the record in the ONE state" in out)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the jump tally AND the witness "
          f"still print BELOW the population refusal (at {i_ref} < {i_tal} < "
          f"{i_wit}), with the three-way cells intact "
          f"({ {k: v[0] for k, v in sorted(seen3.items())} }) -- a refusal that "
          f"swallows the two sections beneath it is the pre-C4 fold again")

    ok = (got.get("witness_pop") == len(samples)
          and got.get("witness_pairs") == wfull["adjacent"]
          and "movetap sample(s)" in out and "PAIRED sample(s)" not in out)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the witness's population is the "
          f"stream the caller handed in: {got.get('witness_pairs')} pair(s) of "
          f"{got.get('witness_pop')} movetap sample(s), which is "
          f"{len(samples)} and not the {len(pairs)} paired ones")

    gotw = read_back_witness(out)
    ok = (gotw.get("witnessed") == wfull["witnessed"]
          and gotw.get("judged") == wfull["judged"]
          and gotw.get("head_changed") == wfull["head_changed"]
          and gotw.get("cache_changed") == wfull["cache_changed"]
          and wfull["witnessed"] != wpaired["witnessed"])
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and its NUMBERS are that stream's: "
          f"{gotw.get('witnessed')} of {gotw.get('judged')} judged, head "
          f"{gotw.get('head_changed')} / cache {gotw.get('cache_changed')} -- "
          f"deleting the `print_appender_witness` call from print_fence, or "
          f"feeding it the paired subset, empties or moves every one of them")

    # THE MIRROR, or the two refusals above are constants. Same machinery, two
    # rows relabelled and no `samples=`: nothing refuses, the PARTIAL line does
    # not print because there is nothing partial, and the witness falls back to
    # the PAIRED population WITH THAT NAME.
    # ...and its `total` is 7 rather than 8 ON PURPOSE, so a PARTIAL line
    # hard-wired to the first fixture's "6 of 8" fails here.
    mirror = pairs[1:6] + [_fake_pair(7, "shut:append", rec),
                           _fake_pair(8, "shut:append", rec)]
    m_counts, m_have, m_total, _m_leg = fence_rows(mirror)
    ok = m_have == 6 and m_total == 7 and not any(
        str(k).startswith("unread:") for k in m_counts)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the mirror fixture carries "
          f"{m_have} of {m_total} with the field and no unread row at all -- "
          f"counted before it is judged")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rcm = print_fence(mirror, jumps)
    outm = buf.getvalue()
    gm = read_back_fence(outm)
    ok = (rcm == 0 and "REFUSED" not in outm
          and gm.get("partial_have") == m_have
          and gm.get("partial_total") == m_total
          and gm.get("witness_pop") == len(mirror)
          and "PAIRED sample(s)" in outm)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and with no unread row it does NOT "
          f"refuse (rc {rcm}), still prints PARTIAL "
          f"{gm.get('partial_have')} of {gm.get('partial_total')}, and names "
          f"the fallback population `PAIRED sample(s)` over "
          f"{gm.get('witness_pop')} -- so both the refusal and the population "
          f"name read the arguments rather than being constants")

    # THE PRINTER AND THE CLASSIFIER DISAGREED, AND THE PRINTER WAS THE WRONG
    # ONE. `classify_reach` -- the function every check above interrogates --
    # lands a label this file has never heard of in `unread`. The distribution
    # loop's own hole tally read `str(k).startswith("unread:")`, which catches
    # movetap's sentinel and nothing else, so an UNRECOGNISED `gate_reach`
    # printed as a REAL CLIENT STATE with a percentage beside it and no refusal:
    # measured at 90.0% over n = 10, rc 0. Same defect class as C4, one section
    # ABOVE the C4 site, in the distribution `PROBE-GATEFIRE.md` §6 quotes.
    unknown = "a-label-from-the-future"
    pairs5 = [_fake_pair(t, unknown) for t in range(1, 10)]
    pairs5.append(_fake_pair(10, "test-runs"))
    c5, have5, total5, _leg5 = fence_rows(pairs5)
    old_rule = sum(c for k, c in c5.items() if str(k).startswith("unread:"))
    new_rule = sum(c for k, c in c5.items() if classify_reach(k) == "unread")
    ok = (len(pairs5) == 10 and have5 == 10 and total5 == 10
          and c5.get(unknown) == 9 and c5.get("test-runs") == 1
          and classify_reach(unknown) == "unread"
          and old_rule == 0 and new_rule == 9)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the disagreement fixture: {have5} "
          f"of {total5} paired samples carry the field, {c5.get(unknown)} of "
          f"them a label this file has never heard of -- which "
          f"`classify_reach` calls `{classify_reach(unknown)}` while the "
          f"printer's old `unread:`-prefix rule counted {old_rule} of them "
          f"against the classifier's {new_rule}")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc5 = print_fence(pairs5, [])
    out5 = buf.getvalue()
    row5 = _dist_row(out5, unknown)
    want_row = ("   a-label-from-the-future                 9   90.0%  unread")
    ok = (row5 == (9, 90.0, "unread")
          and _line_with(out5, unknown) == want_row)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] its distribution row prints "
          f"{want_row!r} -- the BUCKET is the classifier's own verdict beside "
          f"the share, so a row the dict calls a hole can no longer read as a "
          f"state of the client; got {_line_with(out5, unknown)!r}")
    ref5 = _line_with(out5, "carry no state this file can read")
    want_ref5 = ("   REFUSED: 9 of 10 carry no state this file can read -- a "
                 "could-not-read sentinel, or a label it has never heard of. "
                 "No share above is a fact about the client. This bar is over "
                 "the WHOLE paired population and says nothing about the jump "
                 "rows below, which carry their own.")
    ok = rc5 == 1 and ref5 == want_ref5
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and the population refusal FIRES on "
          f"it (rc {rc5}), exactly {want_ref5!r} -- the old rule counted 0 "
          f"holes here and printed a 90.0% share of a client state that does "
          f"not exist, with no refusal at all; got {ref5!r}")

    # THE MIRROR, or the refusal above is a rule about the number 9. Same shape,
    # same 90.0%, a label the file DOES know: nothing refuses and the bucket
    # says `fenced`. So the printer is reading `classify_reach` and not the
    # count.
    pairs6 = [_fake_pair(t, "shut:append") for t in range(1, 10)]
    pairs6.append(_fake_pair(10, "test-runs"))
    c6, have6, _t6, _l6 = fence_rows(pairs6)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc6 = print_fence(pairs6, [])
    out6 = buf.getvalue()
    row6 = _dist_row(out6, "shut:append")
    ok = (have6 == 10 and c6.get("shut:append") == 9 and rc6 == 0
          and row6 == (9, 90.0, "fenced")
          and _line_with(out6, "carry no state this file can read") is None)
    bad += not ok
    n += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] MIRROR: the same {c6.get('shut:append')} "
          f"of {have6} at the same {row6[1] if row6 else None}% under a label "
          f"the file KNOWS prints bucket `{row6[2] if row6 else None}` and does "
          f"NOT refuse (rc {rc6}) -- the refusal reads the classifier, not the "
          f"share")
    return bad + _floor("11", n, 15), n


# A RUN THAT MEASURED NOTHING FAILED, AND THIS SELFTEST IS A RUN. Sections 8-11
# each carry their own `_floor`; sections 1-7 -- the pre-2026-08-20 guards, and
# the ones the operator's pre-flight actually leans on -- carried none, so
# deleting section 2's only check or section 6's took this file from 38 [PASS]
# to 37 with `--selftest` AND `test_movesync.py` both still exit 0. A per-section
# floor under a total nothing checks is half a rule.
#
# AND A PER-SECTION FLOOR SET BELOW WHAT ITS SECTION RUNS IS THE SAME HALF-RULE
# FROM THE OTHER SIDE. Sections 8 and 9 declared 8 and 9 while executing 14 and
# 14, so either could have lost six checks with its OWN floor silent -- caught
# only by this total and by `test_movesync.py`'s table, which is two external
# nets under a number the section is supposed to own. Every `_floor` below is
# now the count its section executes, INSTRUMENTED rather than counted by hand.
#
# MEASURED from a real green run on 2026-08-20 with every section executing,
# never guessed and never set above what one produces: 15 in sections 1-7, then
# 20 + 24 + 6 + 15 in the four floored sections. (It read 14 + 19 + 6 + 11 = 65
# until the 2026-08-20 second gate-fire review, which found three more places
# where the code was already right and the check was missing: arm (b)'s
# `ha != 0` conjunct, the distribution printer disagreeing with
# `classify_reach`, and the C4 table's own header and refusal lines. It read 75
# until the FOURTH review found the same disagreement twice more: arm (b)'s
# denominator gating on an `unread:` PREFIX where `classify_reach` gates on the
# label, and the two printed lines of `print_jump_tally` still free -- the
# SUCCESS sentence's second half and the refusal's stand-in line.)
SELFTEST_FLOOR = 80


def selftest():
    """Everything checkable with no captures. Exits non-zero on any gap."""
    bad = ran = 0
    print("movesync selftest -- no captures required\n")

    print("1. the truncated-clock estimator takes the MAX, not the mean")
    # A mean would sit half a second low, which is 144 units at 288 u/s -- the
    # same size as the thing being measured.
    true_off = 1000.5
    walls = [math.floor(true_off + t) - t for t in (0.0, 0.3, 0.7, 1.1, 1.9)]
    est, spread = offset_from_stamps(walls)
    ok = abs(est - true_off) < 1.0 and est <= true_off
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] estimate {est:.3f} for a true "
          f"{true_off} -- from below, within one second (spread {spread:.3f})")
    mean = sum(walls) / len(walls)
    ok = mean < est
    bad += not ok
    ran += 1
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
    ran += 1
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
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the control produced {len(j2)} "
          f"jump row(s) to judge -- zero would make the next check vacuous")
    ok = bool(j2) and all(abs(j[2] - j[3]) < 50 for j in j2)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and separation is unchanged across "
          f"each ("
          + ", ".join(f"{j[2]:.0f}->{j[3]:.0f}" for j in j2)
          + ") -- so a collapse means something")

    print("\n4. pairs beyond MAX_PAIR_GAP are dropped, not silently stretched")
    far = pair([{"t": 500.0, "live": [0.0, 0.0, 0]}], [(0.0, [0.0, 0.0])], 0.0)
    ok = far == []
    bad += not ok
    ran += 1
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
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] {len(legacy_steps(wrows))} of "
          f"{len(wrows)} walking steps clear the legacy {JUMP_UNITS:.0f} u bar "
          f"-- the row count is asserted first so the next check is not vacuous")
    ok = len(hard_steps(wrows)) == 0
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and {len(hard_steps(wrows))} clear "
          f"the hard bar")
    planted = walk[:6] + [(walk[5][0] + 0.13, [walk[5][1][0] + 900.0, 0.0])]
    prows = steps(planted)
    ok = len(hard_steps(prows)) == 1
    bad += not ok
    ran += 1
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
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] the fixture holds {len(rrows)} "
          f"interval(s) to judge -- counted before it is judged")
    ok = len(hard_steps(rrows)) == 1
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a 700 u / 0.032 s step is caught "
          f"({len(hard_steps(rrows))}) -- the old speed-only bar read 0 here")
    # AND THE ARM IS NOT A dt DETECTOR. The same short interval carrying a small
    # displacement must still be refused, or the fix has re-opened the hole the
    # dt floor existed to close.
    tiny = walk[:6] + [(walk[5][0] + 0.01, [walk[5][1][0] + 25.0, 0.0])]
    trows = steps(tiny)
    ok = len(trows) == 6 and len(hard_steps(trows)) == 0
    bad += not ok
    ran += 1
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
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] a movetap with no `{FENCE_KEY}` "
          f"returns {rc_old} and says so, rather than printing a 0% share")

    new = [(1.0, [0.0, 0.0], {"t": 1.0, "live": [0.0, 0.0, 0],
                              FENCE_KEY: "shut:append",
                              "state_record": _rec(0x1000, 1)}, 0.0),
           (2.0, [900.0, 0.0], {"t": 2.0, "live": [900.0, 0.0, 0],
                                FENCE_KEY: "test-runs",
                                "state_record": _rec(0x2000, 2)}, 0.0)]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_new = print_fence(new, [(2.0, 900.0, 400.0, 20.0, 1.0)])
    out_new = buf.getvalue()
    ok = (rc_new == 0 and "REFUSED" not in out_new
          and "shut:append" in out_new and "test-runs" in out_new
          and "0 of 1 snap(s) began with the record in the ONE state"
          in out_new)
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] and a movetap that HAS the field "
          f"reports the state either side of the jump -- here the snap began "
          f"with the fence shut, so no gate would have been consulted")

    # The mirror: the same fixture with the fence OPEN before the jump must
    # count it as reachable, or the line above is printing a constant.
    new2 = [(1.0, [0.0, 0.0], dict(new[0][2], **{FENCE_KEY: "test-runs"}), 0.0),
            new[1]]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_fence(new2, [(2.0, 900.0, 400.0, 20.0, 1.0)])
    ok = ("1 of 1 snap(s) began with the record in the ONE state"
          in buf.getvalue())
    bad += not ok
    ran += 1
    print(f"   [{'PASS' if ok else 'FAIL'}] flipping the BEFORE state to "
          f"`test-runs` moves that count to 1 of 1 -- the tally reads the "
          f"sample and is not a constant")

    for section in (_selftest_jump_tally, _selftest_appender_witness,
                    _selftest_spellings, _selftest_print_fence):
        got = section()
        bad += got[0]
        ran += got[1]

    short = ran < SELFTEST_FLOOR
    if short:
        print(f"\nONLY {ran} OF A FLOOR OF {SELFTEST_FLOOR} CHECKS RAN -- "
              f"{SELFTEST_FLOOR - ran} did not execute. A section that stops "
              f"running is not a section that passed.")
    print("\n" + ("selftest passed" if not (bad or short)
                  else f"selftest FAILED ({bad})")
          + f" -- {ran} checks, floor {SELFTEST_FLOOR}")
    return 1 if (bad or short) else 0


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
    off, spread = offset_from_stamps(walls, announce=False)
    if off is None:
        print("the capture carries no wall stamp, so the two clocks cannot be "
              "aligned. Nothing here would mean anything.")
        return 2
    # REALFIX-T1: the estimator names itself. This line used to say
    # "whole-second stamps" unconditionally, which on a post-T1 capture would
    # have been a confident lie about where the number came from.
    print(offset_line(offset_detail(walls)))
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
    # `S`, not `prs`: the appender witness inside is about consecutive movetap
    # SAMPLES, and the paired subset drops every sample that had no report
    # beside it -- which would stretch the intervals it judges and dilute the
    # 2.5 s dedup limit it prints.
    print_fence(prs, hard, samples=S)

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
