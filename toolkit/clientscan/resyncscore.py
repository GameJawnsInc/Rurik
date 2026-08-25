#!/usr/bin/env python3
"""WHAT WOULD THE 0x002C RESYNC HAVE DONE? Replayed against captures we already have.

    python toolkit/clientscan/resyncscore.py --compare       # START HERE
    python toolkit/clientscan/resyncscore.py                 # the arc's captures
    python toolkit/clientscan/resyncscore.py --capture PATH --rule B:lower-bound
    python toolkit/clientscan/resyncscore.py --retail        # the CONTROL alone
    python toolkit/clientscan/resyncscore.py --sweep         # threshold x cooldown
    python toolkit/clientscan/resyncscore.py --selftest      # runs test_resyncscore

THIS FILE SENDS NOTHING AND CHANGES NOTHING. It is a costing instrument for a
server change that has not been made: `toolkit/authsrv/authsrv.py` is untouched
by this arc and this module never imports it.

------------------------------------------------------------------------------
THE DEFECT BEING PRICED, in the four sentences the binary supports
------------------------------------------------------------------------------
The client keeps two copies of the player: SYNC (`[agentMgr+0xE8]`, which our
`0x0029` grants steer) and ASYNC (`[agentMgr+0x14C]`, which it renders and
reports from). We answer a click with `0x0029`, a SYNC-ONLY message; the
authoritative copy glides to the granted point and PARKS -- 93.4 s of the
shipped build's 177.3 s. The player then keyboards away and **nothing we send
afterwards reaches the copy they see**: `0x0025`'s async arm is gated shut for
the client-controlled agent (`0x005FD5D3`). Separation grows unwatched to
3,648 u, and the next grant or arrival redeems it in one hard SetPosition
(`0x006022B0`) that reseeds every world-1 agent.

`GAME_SMSG 0x002C AGENT_UPDATE_POSITION` (handler `0x005FDA50`) is the one
catalogued primitive that calls `AgTrack::Clear` first (`0x005FDA78`) and then
SetPositions BOTH copies with no gate on either arm. Our server has sent it
ZERO times in this corpus -- re-measured here, 0 of the `sent` records in all
three arc captures. *** STALE SINCE 2026-08-20 as a statement about the
server: the `--resync` run `authsrv-20260820T182119-c1.jsonl` sent 18 (zero
grants, so not a disarm test), and `--cast-stop=pin` (shipped 2026-08-25)
has added 6 co-timed with movetap, no warp observed -- corpus total 24
(studies/movement/followon-notes/refute-lens-empirical.md sec.1.1/sec.8.2,
README sec.2.1). Still TRUE of the three
2026-08-19 arc captures this file's pinned cells replay, which predate
both senders. *** Full derivation: `studies/movement/FINDINGS.md`, sections
dated 2026-08-19 round 3 and 2026-08-20 rounds 1-3.

------------------------------------------------------------------------------
WHY THIS IS NOT THE FIX THAT WAS ALREADY TRIED AND REMOVED
------------------------------------------------------------------------------
`authsrv.py:7583-7597` records an earlier build that announced ARRIVALS with
`AGENT_UPDATE_POSITION`: "five went out and three were arrivals, carrying the
client 630, 189 and 765 units... our integrator had run the whole leg while the
client had not moved at all. That is the warp the player described: not a snap,
a WALK."

**It sent OUR INTEGRATOR'S position.** The proposal priced here sends the
CLIENT'S OWN last accepted report, which `_take_client_position` has tracked
since 2026-08-19. That distinction is the entire cost argument and it is why
this file measures STALENESS as its headline cost: a message carrying the
client's own word about where it is standing can only move the rendered copy by
however far the client has walked since it said so. The old build's payload
could be arbitrarily wrong; this one's error is bounded by one report interval
of walking, and that bound is MEASURED below rather than asserted.

------------------------------------------------------------------------------
THE DECISION RULE, WRITTEN OUT BEFORE ANY NUMBER IS PRINTED
------------------------------------------------------------------------------
FIVE rules, not one. Some need an arrival model and some do not, and an
instrument that offers only the modelled ones hides its own assumption. Every
number this file prints carries the rule that made it, and `RULE_TEXT` is
printed above every table.

RULE A -- PARKED-AND-SEPARATED. The mechanism says the harm accrues while the
authoritative copy is parked at the point we granted, so:

    on each client position report at time t, position P:
        D, t_g = the outstanding player 0x0029 (destination, grant time)
        P_g    = the client's own last report at or before t_g
        t_park = t_g + |D - P_g| / RUN_SPEED          <- THE ARRIVAL MODEL
        if t < t_park:                    no fire (the copy is still gliding)
        sep_hat = |D - P|                            <- the parked copy vs P
        if sep_hat < THRESHOLD:           no fire
        if t - t_last_fire < COOLDOWN:    no fire
        else: send 0x002C(player, state["pos"], state["plane"])

`RUN_SPEED` and the straight line are ASSUMPTIONS, named here and nowhere
buried. `movesync.py`'s own header warns against exactly this stack, and the
warning is right about a MEASUREMENT. It is survivable in a DECISION rule for
one reason, which is the whole design: **a wrong `sep_hat` costs a firing, and
a firing carries the client's own coordinates.** The rule may be wrong about
whether the copies disagree; the payload cannot be wrong about where the client
said it was.

RULE B -- SEPARATION LOWER BOUND. No speed, no arrival rule, no collision:

    off_leg = distance from P to the SEGMENT [P_g, D]
    if off_leg < THRESHOLD:               no fire   (+ the same cooldown)

Under the single premise that the sync copy lies somewhere on the segment it was
granted, `off_leg` is a LOWER BOUND on the true separation at every instant.
Every Rule B firing is a moment when the copies are provably at least THRESHOLD
apart. It is the honest one to quote when somebody asks whether the fix is
justified rather than what it costs.

RULE C -- BEFORE THE GRANT. Rules A and B are report-driven and both MISS most
of the harm, and the reason is in the miss column rather than in a parameter:
every hard jump Rule A cannot reach is missed for `not-parked`. The snaps land
while the copy is still gliding, which is exactly what the binary predicts --
the desync test has three callers and the GRANT BAKE (`0x005FEBEB`) is one of
them. So Rule C fires at the one instant the test is about to run:

    on every outgoing player 0x0029 at t_g:
        sep_hat = |PREVIOUS destination - the client's own last report|
        if sep_hat >= THRESHOLD: send 0x002C first, then the grant

RULE D -- C plus A's arrival model applied to the PREVIOUS leg.

RULE E -- THE FULL SYNC MODEL, and it is the one to build. A forward model of
the authoritative copy: it glides from wherever the model last had it toward
each new destination at 288 u/s and PARKS on arrival, and separation is
|model - report| at every report. That is four assumptions stacked, which is
exactly the stack `movesync.py`'s header refuses -- **so it is CHECKED.** Paired
against `movetap-20260819T145939`, a `ReadProcessMemory` of `[agentMgr+0xE8]` in
the very session `20260819T145717` recorded:

    residual |model - what the client's memory held|   p50 0.0 u, max 67 u, n=251
    separation from the model                         1164 / 2163 / 3648 u
    separation from movetap                           1164 / 2163 / 3648 u

The right-hand column is `studies/movement/HANDOFF.md` section 1's recorded
harm figure, reproduced here from GRANTS ON THE WIRE by a path that never opens
the movetap file to compute it. `validate_sync_model()` is that check and
`--compare` always prints it; a forward model quoted without it is not quotable.

**AND THE CONTROL DECIDES BETWEEN THEM, AGAINST THE RULE THAT SCORES BEST.**
Retail scores ZERO hard jumps, so a rule that fires on ArenaNet's traffic is
reading the wire. Measured at threshold 299.33 u, cooldown 0.0, against the
SHIPPED build (`20260819T145717`) and the pooled live corpus:

    rule   ours /min   covers      retail /min   ratio    verdict
    A         21.73     3 of 7         0.52      0.024    separates
    B         15.92     1 of 7         0.42      0.026    separates
    C          7.12     5 of 7        29.41      4.132    FAILS
    D          0.75     2 of 7         0.61      0.816    FAILS
    E         39.90     7 of 7         9.09      0.228    separates

**The rule with the best coverage of the four cheap ones is the one that cannot
tell retail from our defect**, because `|previous destination - report|` is large
whenever a leg was superseded before it finished, and supersession every ~0.5 s
is retail's entire shape. Rule D adds the park gate that fixes that and loses
the coverage with it. Only Rule E gets both, and only because it models the copy
rather than approximating it. That is pinned in `test_resyncscore.py` section 15
so a later session cannot quietly "improve" C past it.

TWO THINGS THAT PRICE THE PARAMETERS, both measured here:

  * **The COOLDOWN is where the coverage goes, not the threshold.** Rule E on
    the shipped build: cooldown 0.00 s covers 7/7 at 39.90/min; 0.25 s covers
    4/7; 0.50 s covers 3/7; 2.50 s covers 2/7 -- while the yank stays p50
    0.08 u at every one of them, because the payload is always the client's own
    freshest adopted report. Firing more often costs FREQUENCY and not
    MAGNITUDE, and that asymmetry is the whole proposal.
  * **RETAIL IS NOT SYNCHRONISED TO THE UNIT.** Its own two copies, through the
    same model, sit **p50 83 u, p75 260 u, p90 653 u, max 2,972 u** apart with
    zero snaps. A resync threshold of 100 u therefore sits at ArenaNet's own
    MEDIAN separation and would fire on half of a healthy session; raising it
    to 299.33 u costs NO coverage on our corpus (7/7 either way) and halves the
    retail rate. Raise the threshold, drop the cooldown.

    *** RULED AGAINST, 2026-08-25 (owner-delegated; the full record is
    studies/movement/followon-notes/p5-resync-disarm.md sec.4.2a and the
    ruling block on `authsrv.py`'s RESYNC_SEPARATION). The shipped threshold
    stays 100.0 and THIS FILE'S DEFAULT NOW AGREES. The decisive measurement
    is the DIFFERENTIAL BAND [100, 299.33): over the shipped-regime corpus
    (558 reports) 120 of 157 fires sit in it -- p50 143.7 u -- every one
    refused `in-agreement` at the fence, each leaving a HOLE-B residual leg
    (p5 note sec.3.5: the threshold IS the residual snap magnitude, and Q10
    judges the residual). The fence's fire set is a strict SUBSET of 100's
    (fence-only fires 0 of 558, and structurally impossible under zero-lead
    inside the 0.5 s rate-limit shadow: 2 x 288 x 0.5 = 288 u < 299.33), so
    the band is pure addition; and on `182652` the 100 cell covers 13 of 13
    hard jumps against the fence's 12 -- the miss is `below-threshold` at
    sep 269.3, inside the band -- so this paragraph's "costs NO coverage
    (7/7 either way)" was true of the shipped capture, not of the corpus.
    The retail-rate half prices the rule on traffic it never runs on
    (origins are never pooled, and retail sends 0x002C to the player's own
    agent 5 times in the whole live corpus -- fidelity was conceded at
    birth), and the first bullet's own finding -- firing more often costs
    FREQUENCY and not MAGNITUDE -- is the cheap-axis half of the same
    ruling. GATE1_UNITS below is untouched: it is a measured client
    constant and the gate-1 proxy still needs it. ***

THE THRESHOLD DEFAULT IS MEASURED, THE COOLDOWN DEFAULT IS NOT, and they are
labelled accordingly below.

------------------------------------------------------------------------------
WHAT IS COUNTED AS THE COST, in the units the harm arrives in
------------------------------------------------------------------------------
This arc has already shipped a fix that bounded warp SIZE while the harm arrived
as FREQUENCY (`studies/movement/HANDOFF.md` §6). So both are printed, and the
cost is expressed as a jump on the SAME BAR the harm is measured on:

  YANK      |P_sent - P_client(t_land)|, the backwards pull the player feels.
            Bracketed rather than point-estimated, because the capture cannot
            see when the message lands: ZERO-LATENCY uses the client's position
            at the firing instant, ONE-REPORT uses its next report, and the
            truth is between them. Neither is the operative figure -- the
            capture records both sides on one clock, so how long after its
            trigger the message actually LEAVES is measurable: **p50 0.26-0.31
            ms, max 50 ms across the three arc captures**. At that delay Rule
            A's yank is p50 **0.08 u** and Rule C's **15.97 u** (C's payload is
            a report the grant may postdate by most of an interval). Against a
            p50 1,969 u hard jump, that is the whole cost argument.
            One caveat is stated wherever it is printed: on an interval that
            ITSELF carries a snap, interpolating the client's position returns
            the snap's own magnitude, so those rows are FLAGGED `dirty` and the
            clean subset is the headline.
  STALENESS |P_sent - P_at_fire|, which is non-zero only where the position
            trust guard REFUSED the triggering report -- 4 refusals in the whole
            arc corpus, all in `20260819T145717`. It is printed because a zero
            that is zero by construction has to be visible as one, not hidden
            inside a median -- and because it is the ONE path by which this
            proposal can carry a large error: Rule B finds two firings whose
            payload would be **2,016 u** stale, which is the old build's failure
            mode exactly. The tool names the one-line mitigation beside it (do
            not resync while `state['pos_rejects']` is non-zero) rather than
            leaving the reader to notice.
  SELF-MINTED HARD JUMPS
            A yank is an instantaneous displacement, so on `movesync`'s hard bar
            it clears the DISTANCE arm iff it is >= `HARD_JUMP_UNITS`. Firings
            that would themselves score as hard jumps are counted with the same
            constant that counts the ones we are trying to remove. A fix that
            mints more than it prevents is refused by its own scoreboard.

  PROTECTION, AND IT IS AN UPPER BOUND. `clientControlled` (record+0x00) is
            ONE-SHOT: `AgTrack::Clear` zeroes it and only local player input
            re-arms it (`0x00605F10`). The client emits `0x003D` only while
            moving, so the NEXT report after a firing is evidence that local
            input has happened -- somewhere in the interval, not necessarily at
            its end. A hard jump is therefore scored COVERED only when a firing
            landed on the report that OPENS its interval, and even that is
            optimistic: any local input inside the interval re-arms the record
            before the jump. If the covered count is already near zero, the
            pessimistic count is zero.

------------------------------------------------------------------------------
WHAT THIS FILE REFUSES
------------------------------------------------------------------------------
  * No capture, no answer. `vaultpath.require_dir` raises rather than returning
    a path that is not there.
  * Origins are never pooled: `origin.origin_of` classifies every file and a run
    that mixes `ours` with `live` is refused. `20260811T173940` is `ours` (build
    38797, `captures/gamesrv/`) and is used as an INTERNAL null, not as the
    retail control -- the retail control is `captures/live/`, decoded through
    `cmsgstream`, and this file will say so if asked to treat the two as one.
  * A capture with no player grant cannot fire the rule at all. That prints as a
    DECLARED NULL with its reason, never as a bare 0 beside a rate.
  * Under `movesync.MIN_INTERVALS` the RATE is refused and the count is not --
    both halves of `movesync`'s defect 7.
  * A retail connection whose player agent cannot be named from its own
    `0x0037` is refused rather than guessed at.

READ ONLY. Opens vault captures and writes nothing.
"""
import argparse
import bisect
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
import movesync   # noqa: E402
import origin     # noqa: E402
import vaultpath  # noqa: E402

# --- the rule's constants, each labelled MEASURED or CHOSEN ------------------
#
# MEASURED. Gate 1 of the fallback half compares straight-line separation
# against `300.0f @0x00946564`, and the client's LUT sqrt is a one-sided
# over-estimate, so the effective cut is 299.332591 u and exactly 300.0 snaps
# (studies/movement/FINDINGS.md, 2026-08-20 round 2). Firing AT the fence is
# deliberately the least aggressive defensible default: it is the last moment at
# which a snap is not already earned.
GATE1_UNITS = 299.332591
# RECONCILED 2026-08-25: the shipped constant, agreeing with `authsrv.py`'s
# (test_resyncscore pins the agreement). This file's default was GATE1_UNITS
# until the ruling recorded in the header paragraph above; the pinned replay
# cells measured at that fence keep naming GATE1_UNITS explicitly, because a
# pin that silently floats with a default is not a pin.
RESYNC_SEPARATION = 100.0
# CHOSEN, NOT MEASURED, and it is the one free parameter in the rule. Nothing in
# the binary or the corpus names a re-fire interval; the client's own report
# cadence is ~0.25 s, so 0.0 means "on every qualifying report" and anything
# larger leaves gaps in the protection window. It is swept everywhere it is
# printed, because a number with a free parameter behind it is not quotable
# without the sweep -- the same rule `movesync` applies to its active-time
# threshold.
RESYNC_COOLDOWN = 1.0
# The sweep axes. THRESH_SWEEP brackets the measured fence from both sides
# AND names the shipped default (100.0 -- absent until the 2026-08-25
# reconciliation, which meant the tool never priced the value that ships);
# COOLDOWN_SWEEP runs from "every report" to "twice a minute".
THRESH_SWEEP = (100.0, 150.0, GATE1_UNITS, 600.0, 1200.0)
COOLDOWN_SWEEP = (0.0, 0.25, 1.0, 2.5, 5.0)

RULE_A = "A:parked"
RULE_B = "B:lower-bound"
RULE_C = "C:before-grant"
RULE_D = "D:before-grant-parked"
RULE_E = "E:sync-model"
RULES = (RULE_A, RULE_B, RULE_C, RULE_D, RULE_E)
# Printed verbatim above every number a rule produces, so a table of cells can
# never be read without the rule that made it. Each names its own assumption.
RULE_TEXT = {
    RULE_A: ("REPORT-DRIVEN, and the arrival model is NAMED: the copy is "
             "treated as parked at the granted point from "
             "t_grant + |D - P_grant| / 288 u/s onward, then separation is "
             "|D - report|."),
    RULE_B: ("REPORT-DRIVEN, NO arrival model: distance to the granted "
             "SEGMENT, a lower bound on separation under the one premise that "
             "the sync copy lies on the leg it was granted."),
    RULE_C: ("GRANT-DRIVEN: a 0x002C immediately BEFORE each player 0x0029 "
             "whose |previous destination - the client's own last report| "
             "clears the threshold. No arrival model, and it is aimed at the "
             "grant bake `0x005FEBEB` -- one of the desync test's exactly "
             "three callers, all message-driven."),
    RULE_D: ("GRANT-DRIVEN AND PARKED: Rule C, plus Rule A's arrival model "
             "applied to the PREVIOUS leg -- fire only if that leg had time to "
             "finish before this grant superseded it. It exists because Rule C "
             "failed its own retail control; this is the conjunction that "
             "separates a parked copy from a re-granted one."),
    RULE_E: ("REPORT-DRIVEN, against a FULL FORWARD MODEL of the sync copy: it "
             "glides from wherever the model last had it toward each new "
             "destination at 288 u/s and parks on arrival, and separation is "
             "|model - report| at every report. FOUR assumptions stacked -- "
             "the speed, the straight line, no collision, and the arrival rule "
             "-- which is exactly the stack `movesync.py`'s header refuses for "
             "a MEASUREMENT. It is here because it is the shape a server "
             "actually implements, and pricing it is the only way to say "
             "anything about that shape before it runs."),
}

# How close a capture's `position_report` row must sit to the decoded c2s row it
# describes before the two are joined. MEASURED on `20260819T145717`: the
# `position_report` event is emitted 0.063-0.167 ms after the row it reports,
# n = 268, and its `reported` vector is bit-identical in all of them. 5 ms is
# 30x the observed maximum and still 50x below the report cadence, so a wrong
# join is a mismatch rather than a near-miss.
JOIN_TOLERANCE_S = 0.005

# GAME_SMSG opcodes this file reads or would write. `0x002C` is here to be
# COUNTED, not sent: the census below is what turns "we have never sent one"
# from a recollection into a measurement.
OP_UPDATE_POSITION = 0x002C
# GAME_SMSG 0x0037 names an agent in field 1 and retail sends it to the player's
# own agent. It is how a retail connection's player id is resolved; see
# `retail_tracks`.
OP_ATTRIBUTE_POINTS = 0x0037

# A retail connection needs at least this many self-reports before its rule
# firings mean anything. Same argument as `movesync.MIN_INTERVALS`, one level
# up: a connection with four reports can produce a 0 that is about nothing.
RETAIL_MIN_REPORTS = 10


class Refused(SystemExit):
    """A measurement this tool will not make, with the reason in the message."""


# --- loading ----------------------------------------------------------------
def _accept_flags(path, reps):
    """[bool] parallel to `reps`, joined from the capture's `position_report`.

    Returns (flags, joined, seen) so the caller can print the join rather than
    trust it. A row that cannot be joined is left None -- NOT True. The whole
    point of the accepted flag is that the server sometimes refuses the client's
    word, and defaulting an unjoined row to "accepted" would erase exactly the
    rows that make the staleness column non-vacuous.
    """
    times = [r[0] for r in reps]
    flags = [None] * len(reps)
    seen = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("kind") != "position_report" or not rec.get("reported"):
            continue
        seen += 1
        t = rec.get("t")
        if not isinstance(t, (int, float)) or not times:
            continue
        i = bisect.bisect_left(times, t)
        best, gap = None, None
        for j in (i - 1, i, i + 1):
            if 0 <= j < len(times):
                d = abs(times[j] - t)
                if gap is None or d < gap:
                    best, gap = j, d
        if best is None or gap > JOIN_TOLERANCE_S:
            continue
        # The join is CHECKED, not assumed: the row it landed on must carry the
        # same coordinates the event reports. A time-only join would silently
        # attach the flag to a neighbour at high cadence.
        p = reps[best][1]
        r = rec["reported"]
        if math.hypot(p[0] - r[0], p[1] - r[1]) > 0.01:
            continue
        flags[best] = bool(rec.get("accepted"))
    joined = sum(1 for f in flags if f is not None)
    return flags, joined, seen


def count_sent(path, opcode):
    """(count of one opcode, sorted times of EVERY `sent` record).

    The count exists so "we have never sent a 0x002C" is a number this run
    produced and not a sentence quoted out of a handoff.

    The TIMES are the measured latency term. A resync is a message this server
    would emit, so how long after its trigger it actually leaves the process is
    not a guess -- the capture records both sides on one clock. p50 0.26-0.31 ms
    across the three arc captures, max 50 ms. That is what turns "the yank is
    the client's speed times the latency" from a formula into a number.
    """
    n, times = 0, []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if rec.get("kind") != "sent":
            continue
        if rec.get("opcode") == opcode:
            n += 1
        if isinstance(rec.get("t"), (int, float)):
            times.append(rec["t"])
    times.sort()
    return n, times


def track_from_capture(path):
    """One of OUR captures, loaded through `movesync`'s own readers.

    Deliberately no decoder of its own: `load_wire_reports` is the SPLICED
    `0x003D`+`0x0047` stream (a second reader here would be a second chance to
    disagree about what the client said), `load_grants` reads the agent id out
    of the wire bytes rather than off a label, and `steps`/`hard_steps` are the
    repaired two-arm bar verbatim.
    """
    org, why = origin.origin_of(path)
    if org != origin.OURS:
        raise Refused(
            f"resyncscore: {os.path.basename(path)} classifies as {org!r}, not "
            f"{origin.OURS!r} -- {why}\n"
            f"  This entry point scores OUR server's captures. The retail "
            f"control lives in captures/live/ and is read with --retail, "
            f"because a consumer that pools origins is measuring neither.")
    reps, _walls, source = movesync.load_wire_reports(path)
    grants = movesync.load_grants(path)
    flags, joined, seen = _accept_flags(path, reps)
    rows = movesync.steps(reps)
    n2c, sent_t = count_sent(path, OP_UPDATE_POSITION)
    return {
        "label": os.path.basename(path),
        "origin": org, "build": origin.build_of(path)[0],
        "reps": reps, "accepted": flags,
        "accept_joined": joined, "accept_seen": seen,
        "accept_known": True,
        "grants": grants, "source": source,
        "rows": rows,
        "hard_idx": [k for k, r in enumerate(rows) if movesync.hard_step(r)],
        "den": movesync.denominator(reps),
        "sent_0x2c": n2c, "sent_t": sent_t,
    }


def retail_tracks(stamp=None):
    """The CONTROL: ArenaNet's own traffic, one track per game connection.

    The player's agent id is read from that connection's own `0x0037`, which
    retail sends to the player's agent. A connection with no `0x0037` is
    REFUSED, never guessed: every other agent on the wire is a candidate, and
    picking the busiest one would make the control agree with whatever the rule
    happens to do.

    Each track also carries `sig`, the id-free corroboration -- the p50 of
    |grant destination - the client's own last report| for the chosen agent and
    for the runner-up. On this corpus the player's own value reproduces the
    765.52 u recorded in FINDINGS to four decimals while other agents sit at
    thousands, so a chosen id that does not look like that is visible.
    """
    import cmsgstream  # noqa: E402  -- deferred: only the retail path needs it
    root = vaultpath.require_dir(
        "captures", "live",
        why="the retail control: ArenaNet's own traffic, which must score near "
            "zero if the rule is measuring the defect and not the wire")
    stamps = [stamp] if stamp else sorted(os.listdir(root))
    out = []
    for st in stamps:
        try:
            c2s = cmsgstream.timed(st, "c2s", "game")
            s2c = cmsgstream.timed(st, "s2c", "game")
        except Exception:
            continue          # a stamp with no keyed game wire is not a failure
        reps, grants, named = {}, {}, {}
        for t, conn, op, vals in c2s:
            if op not in (movesync.OP_SET_HEADING, movesync.OP_CANCEL_REPORT):
                continue
            p = _vec(vals, 1)
            if p:
                reps.setdefault(conn, []).append((t, p, None))
        for t, conn, op, vals in s2c:
            if op == OP_ATTRIBUTE_POINTS and _dword(vals, 1) is not None:
                named.setdefault(conn, {})
                a = _dword(vals, 1)
                named[conn][a] = named[conn].get(a, 0) + 1
            if op != movesync.OP_MOVE_TO_POINT:
                continue
            a, p = _dword(vals, 1), _vec(vals, 2)
            if a is not None and p:
                grants.setdefault(conn, {}).setdefault(a, []).append((t, p))
        for conn in sorted(set(reps) | set(grants)):
            R = sorted(reps.get(conn, []), key=lambda z: z[0])
            G = grants.get(conn, {})
            label = f"{st} {conn}"
            if len(R) < RETAIL_MIN_REPORTS:
                out.append(_null_track(label, R, G,
                                       f"only {len(R)} self-report(s); "
                                       f"{RETAIL_MIN_REPORTS} needed"))
                continue
            if not named.get(conn):
                out.append(_null_track(label, R, G,
                                       "no 0x0037 on this connection, so the "
                                       "player's agent id cannot be named -- "
                                       "refused rather than guessed"))
                continue
            aid = max(named[conn].items(), key=lambda kv: kv[1])[0]
            rows = movesync.steps(R)
            out.append({
                "label": label, "origin": origin.LIVE, "build": None,
                "reps": R, "accepted": [True] * len(R),
                "accept_joined": 0, "accept_seen": 0,
                # DECLARED: a retail capture carries no acceptance decision of
                # ours, so every report is treated as adopted. That makes the
                # STALENESS column structurally zero on this corpus and it is
                # printed as "not applicable", never as a measured zero.
                "accept_known": False,
                "player_agent": aid, "sig": _signature(R, G, aid),
                "grants": sorted(G.get(aid, [])), "source": None,
                "rows": rows,
                "hard_idx": [k for k, r in enumerate(rows)
                             if movesync.hard_step(r)],
                "den": movesync.denominator(R),
                "sent_0x2c": None, "sent_t": None,
            })
    return out


def _null_track(label, R, G, why):
    rows = movesync.steps(R)
    return {"label": label, "origin": origin.LIVE, "build": None,
            "reps": R, "accepted": [True] * len(R),
            "accept_joined": 0, "accept_seen": 0, "accept_known": False,
            "player_agent": None, "sig": None,
            "grants": [], "source": None, "rows": rows,
            "hard_idx": [k for k, r in enumerate(rows)
                         if movesync.hard_step(r)],
            "den": movesync.denominator(R), "sent_0x2c": None,
            "sent_t": None, "refused": why}


def _vec(vals, i):
    if not isinstance(vals, (list, tuple)) or len(vals) <= i:
        return None
    p = vals[i]
    if not isinstance(p, (list, tuple)) or len(p) < 2:
        return None
    return [float(p[0]), float(p[1])]


def _dword(vals, i):
    if not isinstance(vals, (list, tuple)) or len(vals) <= i:
        return None
    v = vals[i]
    return v if isinstance(v, int) else None


def _signature(R, G, aid):
    """(chosen p50, runner-up p50, n) of |grant dest - the client's own report|.

    The id-free player signature from the 2026-08-19 corpus pass, recomputed
    here so a wrong `0x0037` read is visible rather than inherited.
    """
    times = [t for t, _p, *_ in R]

    def score(agent):
        ds = []
        for gt, D in G.get(agent, []):
            i = bisect.bisect_right(times, gt) - 1
            if i < 0:
                continue
            P = R[i][1]
            ds.append(math.hypot(D[0] - P[0], D[1] - P[1]))
        return (movesync.pct(ds, 0.5), len(ds)) if ds else (float("nan"), 0)

    mine = score(aid)
    others = sorted(s for s in (score(a)[0] for a in G if a != aid)
                    if math.isfinite(s))
    return {"chosen": mine[0], "n": mine[1],
            # THE RUNNER-UP IS NOT THE RIGHT COMPARISON and this is measured:
            # in a crowded instance a henchman one step behind the player
            # produces a signature within a few percent of theirs, so the
            # nearest rival separates on only 25 of 34 connections. The
            # POPULATION median does separate, because every agent that is not
            # walking with the player sits thousands of units from the point we
            # granted it. Both are returned; only the population one is a check.
            "runner_up": others[0] if others else float("nan"),
            "others_p50": movesync.pct(others, 0.5) if others
            else float("nan"),
            "others_n": len(others)}


# --- the rule ---------------------------------------------------------------
def leg_distance(P, A, B):
    """Distance from P to the SEGMENT A->B, via `movesync.on_segment`.

    The clamp is the whole difference: `on_segment` returns the perpendicular to
    the INFINITE line plus the along-track fraction, which is the right pair for
    asking whether a landing lies ON a granted path and the wrong one for a
    lower bound -- a point far past the end of the segment has a small
    perpendicular and a large true distance.
    """
    perp, f = movesync.on_segment(A, B, P)
    if f < 0.0:
        return math.hypot(P[0] - A[0], P[1] - A[1])
    if f > 1.0:
        return math.hypot(P[0] - B[0], P[1] - B[1])
    return perp


def outstanding(track, t):
    """(D, t_g, P_g) for the grant in force at time t, or None.

    `P_g` is the client's own last report at or before the grant, which is what
    the leg is modelled as starting from. A grant with no report before it
    cannot be modelled and yields None rather than a guessed origin.
    """
    grants = track["grants"]
    if not grants:
        return None
    i = bisect.bisect_right([g[0] for g in grants], t) - 1
    if i < 0:
        return None
    gt, D = grants[i]
    reps = track["reps"]
    j = bisect.bisect_right([r[0] for r in reps], gt) - 1
    if j < 0:
        return None
    return D, gt, reps[j][1]


def sync_track(track, run_speed=movesync.RUN_SPEED):
    """[(t, modelled sync position)] at every client report. Four assumptions.

    THE MODEL, stated so it can be argued with rather than inferred:
      * the sync copy is seeded at the client's first report, because the wire
        gives no other starting point;
      * each grant re-aims it from WHEREVER THE MODEL HAS IT, not from the
        client's report -- which is what the client's own bake does, reading
        the sync agent's `+0x78`;
      * it covers |D - here| at exactly `run_speed` in a straight line;
      * and it PARKS on arrival.
    Collision is ignored, and that is the assumption that killed the earlier
    `AGENT_UPDATE_POSITION` build: our integrator ran a whole leg the client's
    own collision had stopped. It is survivable HERE and not there, for the same
    reason as everywhere in this file -- a wrong model costs a firing, and the
    firing carries the client's own coordinates rather than the model's.
    """
    reps, grants = track["reps"], track["grants"]
    if not reps:
        return []
    out = []
    here = list(reps[0][1])
    target, leg_t0, leg_from, leg_t1 = None, None, None, None
    gi = 0

    def at(t):
        if target is None or leg_t1 is None or t >= leg_t1:
            return list(target) if target is not None else list(here)
        f = (t - leg_t0) / (leg_t1 - leg_t0) if leg_t1 > leg_t0 else 1.0
        return [leg_from[0] + f * (target[0] - leg_from[0]),
                leg_from[1] + f * (target[1] - leg_from[1])]

    for t, _P, *_rest in reps:
        while gi < len(grants) and grants[gi][0] <= t:
            gt, D = grants[gi]
            here = at(gt)
            leg_from, leg_t0, target = list(here), gt, list(D)
            leg_t1 = gt + math.hypot(D[0] - here[0],
                                     D[1] - here[1]) / run_speed
            gi += 1
        out.append((t, at(t)))
    return out


# The one movetap run that sits INSIDE an arc capture, and the pair that makes
# Rule E's model checkable rather than merely stated. `movetap-20260819T145939`
# reads the SYNC array (`[agentMgr+0xE8]`) out of the live process; capture
# `20260819T145717` is the session it was reading. 39 of that capture's 40
# grants fall in the movetap window.
VALIDATION = ("20260819T145717", "movetap-20260819T145939.jsonl")


def validate_sync_model(capture_path_, movetap_path, run_speed=None):
    """Rule E's forward model against a DIRECT MEMORY READ of the sync array.

    THIS IS THE CHECK THAT CAN REFUTE RULE E, and it is the reason Rule E is
    quotable at all. Everything else in this file is arithmetic on the wire; a
    forward model of the authoritative copy is exactly the "four assumptions
    stacked under a conclusion" that `movesync.py`'s header refuses -- unless
    somebody compares it against the object it claims to model.

    `movetap` did that read. This pairs every client self-report with the
    nearest movetap sample through `movesync`'s own `pair()` (so the truncated
    whole-second clock is estimated the same way, from below) and returns the
    residual, plus the separation computed BOTH ways.

    Returns None when either fixture is missing -- no fixture, no answer.
    """
    if not (os.path.isfile(capture_path_) and os.path.isfile(movetap_path)):
        return None
    samples = movesync.load_movetap(movetap_path)
    reps, walls, _src = movesync.load_wire_reports(capture_path_)
    off, spread = movesync.offset_from_stamps(walls)
    if off is None or not samples:
        return None
    pairs = movesync.pair(samples, reps, off)
    track = track_from_capture(capture_path_)
    model = {t: p for t, p in sync_track(
        track, run_speed or movesync.RUN_SPEED)}
    res, sep_model, sep_tap = [], [], []
    for st, p, s, _gap in pairs:
        if st not in model:
            continue
        v = s.get("live")
        if not v or not all(math.isfinite(c) for c in v[:2]):
            continue
        m = model[st]
        res.append(math.hypot(m[0] - v[0], m[1] - v[1]))
        sep_model.append(math.hypot(m[0] - p[0], m[1] - p[1]))
        sep_tap.append(math.hypot(v[0] - p[0], v[1] - p[1]))
    if not res:
        return None
    q = movesync.pct
    return {"n": len(res), "offset_spread": spread,
            "residual_p50": q(sorted(res), 0.5),
            "residual_p90": q(sorted(res), 0.9),
            "residual_max": max(res),
            "sep_model": (q(sorted(sep_model), 0.5), q(sorted(sep_model), 0.9),
                          max(sep_model)),
            "sep_tap": (q(sorted(sep_tap), 0.5), q(sorted(sep_tap), 0.9),
                        max(sep_tap))}


def _sync_model_moments(track, thresh, run_speed):
    """Rule E's moments: every report where |model - report| clears the bar."""
    model = sync_track(track, run_speed)
    out = []
    for i, (t, S) in enumerate(model):
        P = track["reps"][i][1]
        sep = math.hypot(S[0] - P[0], S[1] - P[1])
        if sep >= thresh:
            out.append((t, sep, i, None, None))
    return out


def _moments(track, thresh, rule, run_speed):
    """[(t, sep, i, grant_age, park_age, payload_index)] the rule would act on.

    `i` is the index of the report that OPENS the interval the moment lands in,
    which is what makes coverage answerable for a grant-driven rule and a
    report-driven one with the same code.
    """
    reps, flags = track["reps"], track["accepted"]
    times = [r[0] for r in reps]
    if rule in (RULE_C, RULE_D):
        # GRANT-DRIVEN. The desync test has exactly three callers and all three
        # are message-driven; the grant bake is one of them (`0x005FEBEB`). So
        # the moment that matters is the instant we are ABOUT to grant, and the
        # separation the client is about to test is between the copy parked at
        # the PREVIOUS destination and where it says it is now.
        out, prev, prev_t, prev_org = [], None, None, None
        for gt, D in track["grants"]:
            i = bisect.bisect_right(times, gt) - 1
            if prev is None or i < 0:
                prev, prev_t = D, gt
                prev_org = reps[i][1] if i >= 0 else None
                continue
            P = reps[i][1]
            sep = math.hypot(prev[0] - P[0], prev[1] - P[1])
            park_age = None
            if rule == RULE_D and prev_org is not None:
                # THE CONJUNCTION, and it exists because Rule C FAILED its own
                # retail control: |previous destination - report| is large
                # whenever the previous leg was superseded before it finished,
                # which is retail's entire shape (p50 0.491 s between grants).
                # Requiring the previous leg to be MODELLED COMPLETE is what
                # separates "the copy is parked away from the player" from
                # "we re-granted before it arrived".
                t_park = prev_t + math.hypot(prev[0] - prev_org[0],
                                             prev[1] - prev_org[1]) / run_speed
                park_age = gt - t_park
            prev, prev_t, prev_org = D, gt, P
            if rule == RULE_D and (park_age is None or park_age < 0.0):
                continue
            if sep >= thresh:
                out.append((gt, sep, i, 0.0, park_age))
        return out
    if rule == RULE_E:
        return _sync_model_moments(track, thresh, run_speed)
    out = []
    for i, row in enumerate(reps):
        t, P = row[0], row[1]
        og = outstanding(track, t)
        if og is None:
            continue
        D, gt, Pg = og
        if rule == RULE_A:
            t_park = gt + math.hypot(D[0] - Pg[0], D[1] - Pg[1]) / run_speed
            if t < t_park:
                continue
            sep = math.hypot(D[0] - P[0], D[1] - P[1])
            park_age = t - t_park
        else:
            sep, park_age = leg_distance(P, Pg, D), None
        if sep >= thresh:
            out.append((t, sep, i, t - gt, park_age))
    return out


def fires(track, thresh=RESYNC_SEPARATION, cooldown=RESYNC_COOLDOWN,
          rule=RULE_A, run_speed=movesync.RUN_SPEED):
    """Every moment the proposed rule would have sent a 0x002C. One row each.

    Rules A and B are REPORT-DRIVEN by design: `authsrv` already runs
    `_take_client_position` on every client report, so a rule evaluated there
    needs no new timer and no new state beyond `t_last_fire`. Rule C is
    GRANT-DRIVEN, which is one `send` call earlier in a function that already
    exists.

    The payload is `state["pos"]` at that instant -- the client's own last
    ACCEPTED report -- which is what makes STALENESS the honest cost column.
    """
    if rule not in RULES:
        raise Refused(f"resyncscore: unknown rule {rule!r}; known: {RULES}")
    reps, flags = track["reps"], track["accepted"]
    out, last_fire = [], None
    for t, sep, i, grant_age, park_age in _moments(track, thresh, rule,
                                                   run_speed):
        # state["pos"] as of this instant: the last ACCEPTED report at or
        # before it. `None` flags (a row the join could not reach) are NOT
        # treated as accepted -- see `_accept_flags`.
        sent = None
        for j in range(i, -1, -1):
            if flags[j]:
                sent = (reps[j][0], reps[j][1])
                break
        if sent is None:
            continue                      # nothing to put in the payload yet
        if last_fire is not None and (t - last_fire) < cooldown:
            continue
        last_fire = t
        st, Ps = sent
        P = reps[i][1]
        stale = math.hypot(Ps[0] - P[0], Ps[1] - P[1])
        if i + 1 < len(reps):
            nxt, dt_next = reps[i + 1][1], reps[i + 1][0] - t
            yank = math.hypot(Ps[0] - nxt[0], Ps[1] - nxt[1])
            # IS THE INTERVAL WE MEASURED THE BOUND OVER ITSELF A HARD JUMP?
            # If it is, the "next report" is on the far side of a snap and the
            # bound is measuring the pre-existing harm, not this message's cost.
            # Those rows are kept and FLAGGED rather than dropped: dropping them
            # would quietly remove exactly the firings that matter most.
            dirty = movesync.hard_step(track["rows"][i])
        else:
            nxt, dt_next, yank, dirty = None, float("nan"), stale, False
        # HOW LONG AFTER THE TRIGGER THE MESSAGE ACTUALLY LEAVES, measured from
        # this capture's own `sent` stream rather than assumed. Both sides are
        # on one clock, so this is an observation; the loopback wire leg beneath
        # it is under a millisecond and is not separately measurable here.
        delay = float("nan")
        st_t = track.get("sent_t")
        if st_t:
            j = bisect.bisect_left(st_t, t)
            if j < len(st_t):
                delay = st_t[j] - t
        rate = (yank / dt_next) if (nxt is not None and dt_next > 0) \
            else float("nan")
        # THE YANK AT THE INSTANT THE MESSAGE LANDS, which is the firing time
        # plus the measured send delay -- NOT the report time. For a
        # report-driven rule those are the same instant; for Rule C the grant
        # can sit most of a report interval after the report whose position it
        # would carry, and that gap is real staleness the report-driven form
        # does not have. The client's position at the landing instant is
        # LINEARLY INTERPOLATED between the bracketing reports: one assumption,
        # named, and wrong exactly on the `dirty` rows, which are flagged.
        at_send = stale
        if nxt is not None and dt_next > 0 and math.isfinite(delay):
            frac = min(max((t + delay - reps[i][0]) / dt_next, 0.0), 1.0)
            land = (P[0] + frac * (nxt[0] - P[0]),
                    P[1] + frac * (nxt[1] - P[1]))
            at_send = math.hypot(Ps[0] - land[0], Ps[1] - land[1])
        out.append({
            "i": i, "t": t, "sep": sep, "rule": rule,
            "grant_age": grant_age, "park_age": park_age,
            "payload": list(Ps), "payload_age": t - st,
            "stale": stale, "yank": yank, "dt_next": dt_next,
            "has_next": nxt is not None, "dirty": dirty,
            "send_delay": delay, "yank_at_send": at_send,
            # How fast the bound GROWS with latency: the client's own speed
            # across the interval. The yank at a real network latency L is
            # ~= rate * L, which is the form a person can act on -- the
            # one-report figure is the worst case of L = a whole report gap.
            "yank_rate": rate,
            # A yank is a displacement at ~zero world time, so on movesync's
            # two-arm bar it is a DISTANCE-arm event. Same constant that counts
            # the jumps we are trying to remove -- a fix scored on a friendlier
            # bar than the defect is scored on nothing.
            "mints_hard": yank >= movesync.HARD_JUMP_UNITS,
            "over_legacy": yank >= movesync.JUMP_UNITS,
        })
    return out


def coverage(track, firings):
    """(covered, uncovered) hard-jump indices, under the OPTIMISTIC proxy.

    A hard jump is the interval opened by report k, and every firing carries the
    index of the interval it lands in -- report-driven ones by construction,
    Rule C's grant-driven ones because `_moments` resolves the grant time back
    to the report that precedes it. So a jump is scored covered exactly when a
    firing lands INSIDE its interval.

    `AgTrack::Clear` shuts the fence at the firing instant and only local input
    re-arms it. This is therefore an UPPER BOUND on protection: any local input
    inside the interval re-arms the record before the jump, and the wire cannot
    see input, only the report that input eventually produces.
    """
    fired = {f["i"] for f in firings}
    cov = [k for k in track["hard_idx"] if k in fired]
    return cov, [k for k in track["hard_idx"] if k not in fired]


def why_not(track, k, thresh=RESYNC_SEPARATION, rule=RULE_A,
            run_speed=movesync.RUN_SPEED, firings=()):
    """Why the rule did not fire at report k -- with the blocking term's value.

    THE MOST INFORMATIVE OUTPUT IN THIS FILE, and it exists because a coverage
    number alone reads as "tune the parameters". If the jumps the fix misses are
    missed because there was no outstanding grant, no parameter reaches them and
    the rule is aimed at the wrong moment. A count with no reason attached
    invites the reader to supply one.
    """
    if k in {f["i"] for f in firings}:
        return "fired", None
    reps = track["reps"]
    if k >= len(reps):
        return "no-report", None
    t, P = reps[k][0], reps[k][1]
    if not any(track["accepted"][:k + 1]):
        return "no-payload", None
    if rule in (RULE_C, RULE_D):
        # A grant-driven rule can only reach an interval a grant falls inside.
        # That is the whole question for C and D and it has no parameter in it.
        t1 = reps[k + 1][0] if k + 1 < len(reps) else float("inf")
        inside = [g for g in track["grants"] if t <= g[0] < t1]
        if not inside:
            return "no-grant-in-interval", None
        return "cooldown-threshold-or-not-parked", None
    if rule == RULE_E:
        model = sync_track(track, run_speed)
        S = model[k][1]
        sep = math.hypot(S[0] - P[0], S[1] - P[1])
        return ("below-threshold" if sep < thresh else "cooldown"), sep
    og = outstanding(track, t)
    if og is None:
        return "no-grant", None
    D, gt, Pg = og
    if rule == RULE_A:
        t_park = gt + math.hypot(D[0] - Pg[0], D[1] - Pg[1]) / run_speed
        if t < t_park:
            return "not-parked", t_park - t
        sep = math.hypot(D[0] - P[0], D[1] - P[1])
    else:
        sep = leg_distance(P, Pg, D)
    if sep < thresh:
        return "below-threshold", sep
    return "cooldown", sep


def score(track, thresh=RESYNC_SEPARATION, cooldown=RESYNC_COOLDOWN,
          rule=RULE_A):
    """Everything one (rule, threshold, cooldown) cell needs, with its n."""
    den = track["den"]
    if track.get("refused"):
        return {"track": track, "refused": track["refused"], "n": 0}
    f = fires(track, thresh, cooldown, rule)
    cov, unc = coverage(track, f)
    yanks = [r["yank"] for r in f if r["has_next"]]
    clean = [r for r in f if r["has_next"] and not r["dirty"]]
    cy = [r["yank"] for r in clean]
    rates = [r["yank_rate"] for r in clean if math.isfinite(r["yank_rate"])]
    delays = [r["send_delay"] for r in f if math.isfinite(r["send_delay"])]
    at_send = [r["yank_at_send"] for r in f
               if math.isfinite(r["yank_at_send"])]
    ac = [r["yank_at_send"] for r in clean if math.isfinite(r["yank_at_send"])]
    stales = [r["stale"] for r in f]
    hard = [track["rows"][k] for k in track["hard_idx"]]
    return {
        "track": track, "rule": rule, "thresh": thresh, "cooldown": cooldown,
        "fires": f, "n": len(f),
        "rate_span": movesync.per_minute(len(f), den["span"]),
        "rate_active": movesync.per_minute(len(f), den["active"]),
        "yank_p50": movesync.pct(yanks, 0.5) if yanks else float("nan"),
        "yank_p90": movesync.pct(yanks, 0.9) if yanks else float("nan"),
        "yank_max": max(yanks) if yanks else float("nan"),
        "yank_n": len(yanks),
        # The same bound over the firings whose own interval is NOT a measured
        # hard jump -- i.e. with the pre-existing harm taken out of the cost.
        "clean_n": len(cy), "dirty_n": len(yanks) - len(cy),
        "clean_p50": movesync.pct(cy, 0.5) if cy else float("nan"),
        "clean_p90": movesync.pct(cy, 0.9) if cy else float("nan"),
        "clean_max": max(cy) if cy else float("nan"),
        "rate_p50": movesync.pct(rates, 0.5) if rates else float("nan"),
        "rate_max": max(rates) if rates else float("nan"),
        # AT THE MEASURED SEND DELAY -- the operative cost on this deployment.
        "send_p50": movesync.pct(delays, 0.5) if delays else float("nan"),
        "send_max": max(delays) if delays else float("nan"),
        "send_n": len(delays),
        "atsend_p50": movesync.pct(at_send, 0.5) if at_send else float("nan"),
        "atsend_p90": movesync.pct(at_send, 0.9) if at_send else float("nan"),
        "atsend_max": max(at_send) if at_send else float("nan"),
        "atsend_mints": sum(1 for r in f
                            if r["yank_at_send"] >= movesync.HARD_JUMP_UNITS),
        # ...and the same over the CLEAN rows only. On a `dirty` row the client
        # snapped somewhere inside the interval, so interpolating its position
        # returns the SNAP's own magnitude and charges the pre-existing harm to
        # this message. That is double-counting in the direction that flatters
        # nothing -- it is reported, and it is not the headline.
        "atsend_clean_p50": movesync.pct(ac, 0.5) if ac else float("nan"),
        "atsend_clean_p90": movesync.pct(ac, 0.9) if ac else float("nan"),
        "atsend_clean_max": max(ac) if ac else float("nan"),
        "atsend_clean_mints": sum(1 for r in clean
                                  if r["yank_at_send"]
                                  >= movesync.HARD_JUMP_UNITS),
        "stale_p50": movesync.pct(stales, 0.5) if stales else float("nan"),
        "stale_max": max(stales) if stales else float("nan"),
        "stale_nonzero": sum(1 for s in stales if s > 0.0),
        "mints": sum(1 for r in f if r["mints_hard"]),
        "mints_clean": sum(1 for r in clean if r["mints_hard"]),
        "over_legacy": sum(1 for r in f if r["over_legacy"]),
        "covered": cov, "uncovered": unc,
        "misses": [(k,) + why_not(track, k, thresh, rule, firings=f)
                   for k in unc],
        "hard_n": len(track["hard_idx"]),
        "hard_p50": movesync.pct([r["dist"] for r in hard], 0.5)
        if hard else float("nan"),
        "hard_max": max((r["dist"] for r in hard), default=float("nan")),
        "refused": None,
    }


# --- printing ---------------------------------------------------------------
def config_of(label):
    """Which of the arc's three configurations a capture is, or None.

    Printed everywhere a capture's numbers are, because two of the three are
    REFUTED arms whose grant cadence is 30-40x the shipped build's, and a
    reader comparing three rows without that is comparing three different
    experiments.
    """
    for stamp, text in CONFIGS.items():
        if stamp in label:
            return text
    return None


def _why_no_fire(track):
    """The reason a zero is a zero. A bare 0 beside a rate is not an answer."""
    if track.get("refused"):
        return track["refused"]
    if not track["grants"]:
        return ("this capture holds ZERO player 0x0029 grants, so the rule has "
                "no outstanding destination to measure against and CANNOT "
                "fire. That is a declared null, not a low score.")
    if not any(track["accepted"]):
        return ("no client report in this capture was adopted, so there is no "
                "payload to send")
    return None


def print_track(track, rule=RULE_A, thresh=RESYNC_SEPARATION,
                cooldown=RESYNC_COOLDOWN):
    den = track["den"]
    print(f"\n=== {track['label']}   [{track['origin']}"
          + (f", build {track['build']}" if track["build"] else "") + "]")
    cfg = config_of(track["label"])
    if cfg:
        print(f"    CONFIG   {cfg}")
    print(f"    REPORTS  {len(track['reps'])} client self-report(s), "
          f"{den['intervals']} interval(s) over {den['span']:.1f}s")
    if track["accept_known"]:
        unjoined = len(track["reps"]) - track["accept_joined"]
        refused = sum(1 for f in track["accepted"] if f is False)
        print(f"             adoption joined from the capture's own "
              f"`position_report`: {track['accept_joined']} of "
              f"{len(track['reps'])} row(s) joined ({unjoined} unjoined), "
              f"{refused} REFUSED by the position-trust guard")
    else:
        print(f"             adoption UNKNOWN on this corpus -- a retail "
              f"capture carries no acceptance decision of ours, so every "
              f"report is treated as adopted and STALENESS is not applicable")
    if track.get("player_agent") is not None:
        s = track["sig"]
        print(f"    PLAYER   agent {track['player_agent']}, named from this "
              f"connection's own 0x0037; id-free signature |grant dest - own "
              f"report| p50 {s['chosen']:.2f} u over n = {s['n']} against a "
              f"runner-up {s['runner_up']:.0f} u")
    print(f"    GRANTS   {len(track['grants'])} player 0x0029")
    if track["sent_0x2c"] is not None:
        print(f"    CENSUS   {track['sent_0x2c']} x 0x002C "
              f"AGENT_UPDATE_POSITION already sent in this capture")
    print(f"    MEASURED HARD JUMPS  n = {len(track['hard_idx'])} "
          f"(movesync's two arms, verbatim)")

    why = _why_no_fire(track)
    if why:
        print(f"\n    NO FIRING IS POSSIBLE HERE: {why}")
        return None

    s = score(track, thresh, cooldown, rule)
    print(f"\n    RULE {rule}   threshold {thresh:.2f} u   "
          f"cooldown {cooldown:.2f}s")
    print(f"       {RULE_TEXT[rule]}")
    print(f"       FIRES  n = {s['n']} of {den['intervals']} interval(s)")
    if s["n"] == 0:
        print(f"       and nothing in this capture ever met the rule.")
        return s
    if den["intervals"] < movesync.MIN_INTERVALS:
        print(f"       REFUSING EVERY RATE: {den['intervals']} interval(s) is "
              f"below the {movesync.MIN_INTERVALS} a per-minute number needs. "
              f"The count above is NOT refused with it.")
    else:
        print(f"              {s['rate_span']:.2f}/min of span "
              f"({den['span']:.1f}s)")
        print(f"              {s['rate_active']:.2f}/min of actively-reported "
              f"time ({den['active']:.1f}s = the sum of gaps <= "
              f"{den['active_threshold']:.3f}s, which is `FREE_SILENCE` and is "
              f"borrowed from movesync's legacy bar)")
    print(f"       YANK   the backwards pull, BRACKETED because the capture "
          f"cannot see when the message lands:")
    print(f"              at zero latency   p50 {s['stale_p50']:.1f} u   "
          f"max {s['stale_max']:.1f} u   ({s['stale_nonzero']} of {s['n']} "
          f"firing(s) non-zero -- non-zero only where a report was REFUSED)")
    if s["stale_nonzero"]:
        print(f"              *** {s['stale_nonzero']} firing(s) would carry a "
              f"payload the position-trust guard had REFUSED, stale by up to "
              f"{s['stale_max']:.0f} u. That is the OLD BUILD'S FAILURE MODE "
              f"exactly -- a server opinion the client never agreed to -- and "
              f"it is the only path by which this proposal can produce a large "
              f"yank. Reachable with a one-line guard: do not resync while "
              f"`state['pos_rejects']` is non-zero. MEASURED here, not "
              f"assumed.")
    print(f"              at one report     p50 {s['yank_p50']:.1f} u   "
          f"p90 {s['yank_p90']:.1f} u   max {s['yank_max']:.1f} u "
          f"(n = {s['yank_n']}) -- the WORST CASE, a whole report gap of "
          f"latency")
    print(f"              ...of which {s['dirty_n']} firing(s) sit at the "
          f"opening of an interval that is ITSELF a measured hard jump, so "
          f"their bound is the pre-existing harm and not this message's cost. "
          f"Without them: p50 {s['clean_p50']:.1f} u   p90 "
          f"{s['clean_p90']:.1f} u   max {s['clean_max']:.1f} u "
          f"(n = {s['clean_n']})")
    if math.isfinite(s["rate_p50"]):
        print(f"              the bound GROWS at p50 {s['rate_p50']:.0f} u/s "
              f"(max {s['rate_max']:.0f}), which is the client's own speed -- "
              f"so the one-report figure above is what it costs only if the "
              f"message takes a full report gap to land")
    if s["send_n"]:
        note = ("STRUCTURALLY ZERO for this rule -- the 0x002C leaves in the "
                "same send as the 0x0029 it precedes"
                if rule in (RULE_C, RULE_D) else
                "this capture's own `sent` clock")
        print(f"       AT THE INSTANT IT LANDS -- firing time + send delay "
              f"({note}: p50 {1000 * s['send_p50']:.2f} ms, max "
              f"{1000 * s['send_max']:.0f} ms, n = {s['send_n']}), with the "
              f"client's position LINEARLY INTERPOLATED between its "
              f"bracketing reports:")
        print(f"              p50 {s['atsend_clean_p50']:.2f} u   p90 "
              f"{s['atsend_clean_p90']:.1f} u   max "
              f"{s['atsend_clean_max']:.1f} u over the {s['clean_n']} clean "
              f"firing(s); {s['atsend_clean_mints']} clear the hard bar")
        print(f"              (over ALL {s['n']}, including the "
              f"{s['dirty_n']} whose interval carries the snap and where "
              f"interpolation returns the snap's own magnitude: p50 "
              f"{s['atsend_p50']:.2f} u, max {s['atsend_max']:.1f} u, "
              f"{s['atsend_mints']} over the bar)")
        print(f"              THIS IS THE OPERATIVE COST on a loopback "
              f"deployment. The interpolation is the one assumption in it.")
    print(f"       COST ON THE SAME BAR: {s['mints']} of {s['n']} firing(s) "
          f"would themselves clear movesync's hard bar (yank >= "
          f"{movesync.HARD_JUMP_UNITS:.0f} u at ~zero dt) at the worst-case "
          f"bound, {s['mints_clean']} once the pre-existing jumps are taken "
          f"out; {s['over_legacy']} clear the legacy "
          f"{movesync.JUMP_UNITS:.0f} u bar, which is not a verdict.")
    print(f"       PROTECTION (upper bound): {len(s['covered'])} of "
          f"{s['hard_n']} measured hard jump(s) open on a report where a "
          f"resync fired, so the record would have been cleared first.")
    if s["hard_n"]:
        print(f"              the {s['hard_n']} measured jump(s) run p50 "
              f"{s['hard_p50']:.0f} u, max {s['hard_max']:.0f} u")
    if s["misses"]:
        tally = {}
        for _k, reason, _v in s["misses"]:
            tally[reason] = tally.get(reason, 0) + 1
        print(f"              WHY THE OTHERS ARE MISSED -- "
              + ", ".join(f"{n} x {r}" for r, n in sorted(tally.items()))
              + ". A reason that is not `cooldown` or `below-threshold` is "
                "OUT OF REACH OF ANY PARAMETER.")
        for k, reason, v in s["misses"]:
            row = track["rows"][k]
            extra = "" if v is None else (
                f" ({v:.1f}s to park)" if reason == "not-parked"
                else f" (sep {v:.0f} u)")
            print(f"                 t={row['t0']:.3f}s  "
                  f"{row['dist']:.0f} u / {row['dt']:.3f}s  -> {reason}{extra}")
    print(f"              this is OPTIMISTIC: `clientControlled` is re-armed by "
          f"any local input, and the wire sees only the report that input "
          f"produced. A near-zero here is zero.")
    print(f"\n       HEADLINE  fires {s['rate_span']:.2f}/min of span, median "
          f"yank {s['atsend_clean_p50']:.2f} u at the landing instant "
          f"(n = {s['clean_n']}; worst case, a whole report gap of latency, "
          f"{s['clean_p50']:.0f} u), minting "
          f"{s['atsend_clean_mints']} hard jump(s) of its own "
          f"({s['mints_clean']} at the worst case), in exchange for covering "
          f"{len(s['covered'])} of {s['hard_n']} measured hard jump(s) at p50 "
          f"{s['hard_p50']:.0f} u.")
    return s


def print_sweep(track, rule=RULE_A):
    """The cell table. A headline with a free parameter needs its neighbours."""
    if _why_no_fire(track):
        return
    print(f"\n    SWEEP, rule {rule} -- threshold x cooldown on "
          f"{track['label']}")
    print(f"       {'thresh':>10} {'cool':>6} {'fires':>6} {'/min':>7} "
          f"{'yank p50':>9} {'yank max':>9} {'mints':>6} "
          f"{'covered':>9}")
    for th in THRESH_SWEEP:
        for cd in COOLDOWN_SWEEP:
            s = score(track, th, cd, rule)
            cov = f"{len(s['covered'])}/{s['hard_n']}"
            print(f"       {th:>10.1f} {cd:>6.2f} {s['n']:>6d} "
                  f"{s['rate_span']:>7.2f} {s['yank_p50']:>9.1f} "
                  f"{s['yank_max']:>9.1f} {s['mints']:>6d} {cov:>9}")


def print_retail_control(tracks, rule=RULE_A, thresh=RESYNC_SEPARATION,
                         cooldown=RESYNC_COOLDOWN):
    """THE CONTROL THAT CAN FAIL. Retail scores zero hard jumps; if the rule
    fires freely on retail traffic it is measuring the wire and not the defect.
    """
    usable = [t for t in tracks if not t.get("refused")]
    print(f"\n=== RETAIL CONTROL -- ArenaNet's own traffic, "
          f"{len(usable)} usable connection(s) of {len(tracks)}")
    if not usable:
        raise Refused(
            "resyncscore: the retail control judged ZERO connections. A "
            "control over an empty population certifies whatever it is asked "
            "to certify; refusing is the only honest verdict.")
    tot_f = tot_span = tot_hard = tot_cov = tot_reports = 0
    tot_mints = 0
    yanks = []
    for t in usable:
        s = score(t, thresh, cooldown, rule)
        tot_f += s["n"]
        tot_span += t["den"]["span"]
        tot_hard += s["hard_n"]
        tot_cov += len(s["covered"])
        tot_mints += s["mints"]
        tot_reports += len(t["reps"])
        yanks.extend(r["yank"] for r in s["fires"] if r["has_next"])
    print(f"    {tot_reports} retail self-report(s), {tot_span:.0f}s of span, "
          f"{tot_hard} measured hard jump(s) -- retail's own zero is the "
          f"reason this is the control")
    print(f"    rule {rule} at threshold {thresh:.2f} u / cooldown "
          f"{cooldown:.2f}s fires {tot_f} time(s) = "
          f"{movesync.per_minute(tot_f, tot_span):.2f}/min of pooled span")
    if yanks:
        print(f"    yank at one report: p50 "
              f"{movesync.pct(yanks, 0.5):.1f} u  max {max(yanks):.1f} u; "
              f"{tot_mints} firing(s) would clear the hard bar")
    for t in tracks:
        if t.get("refused"):
            print(f"    refused: {t['label']} -- {t['refused']}")
    return {"fires": tot_f, "span": tot_span, "hard": tot_hard,
            "covered": tot_cov, "connections": len(usable),
            "reports": tot_reports, "mints": tot_mints,
            "rate": movesync.per_minute(tot_f, tot_span)}


def retail_rate(tracks, thresh, cooldown, rule):
    """(fires, pooled span, rate/min) for the control at one cell."""
    n, span = 0, 0.0
    for t in tracks:
        if t.get("refused"):
            continue
        n += len(fires(t, thresh, cooldown, rule))
        span += t["den"]["span"]
    return n, span, movesync.per_minute(n, span)


# THE DISCRIMINATION BAR, and it is the whole reason the control exists.
# Retail scores ZERO hard jumps on `movesync`'s two arms, so a rule that fires
# on retail as often as it fires on our defective build is reading the wire, not
# the defect. 4x was chosen as the line at which the two populations stop
# overlapping on this corpus and is stated as CHOSEN; the ratio itself is the
# measurement and is always printed beside the verdict.
DISCRIMINATION = 4.0


def print_validation(v):
    if v is None:
        print("\n=== SYNC-MODEL VALIDATION: REFUSED -- the movetap run or the "
              "capture it sits inside is not in this vault, so Rule E's model "
              "is unchecked and its numbers should not be quoted.")
        return
    print(f"\n=== SYNC-MODEL VALIDATION -- Rule E's forward model against a "
          f"direct read of [agentMgr+0xE8]")
    print(f"    n = {v['n']} paired report/sample(s); the whole-second clock "
          f"estimate has a {v['offset_spread']:.3f}s spread")
    print(f"    RESIDUAL |model - movetap|      p50 {v['residual_p50']:.0f} u  "
          f"p90 {v['residual_p90']:.0f} u   max {v['residual_max']:.0f} u")
    print(f"    separation from the MODEL       p50 {v['sep_model'][0]:.0f} u  "
          f"p90 {v['sep_model'][1]:.0f} u   max {v['sep_model'][2]:.0f} u")
    print(f"    separation from MOVETAP         p50 {v['sep_tap'][0]:.0f} u  "
          f"p90 {v['sep_tap'][1]:.0f} u   max {v['sep_tap'][2]:.0f} u")
    print(f"    ...and the movetap column is what `studies/movement/HANDOFF.md` "
          f"section 1 records (1,164 / 2,163 / 3,648 u, n = 251) -- reproduced here by "
          f"a path that never opens the movetap file to compute it.")


def print_compare(tracks, retail, cooldown=0.0, thresh=RESYNC_SEPARATION):
    """Every rule against every capture AND against the control, in one table.

    This is the deliverable. A per-rule page cannot be compared with another
    per-rule page by eye, and the arc's own recorded failure is a candidate
    scored on a bar its rivals were not.
    """
    print(f"\n=== RULE COMPARISON   threshold {thresh:.2f} u   cooldown "
          f"{cooldown:.2f}s")
    print(f"    {'rule':<24} {'capture':<34} {'fires':>6} {'/min':>7} "
          f"{'yank p50':>9} {'mints':>6} {'covered':>9}")
    nulls = [t for t in tracks if _why_no_fire(t)]
    for t in nulls:
        # NAMED, not omitted. A capture that silently drops out of a comparison
        # table reads as one that was never offered, and this one is the arc's
        # internal null -- its absence is a result.
        print(f"    {'(every rule)':<24} {t['label']:<34} DECLARED NULL -- "
              f"{_why_no_fire(t)}")
    if nulls:
        print()
    for rule in RULES:
        for t in tracks:
            if _why_no_fire(t):
                continue
            s = score(t, thresh, cooldown, rule)
            print(f"    {rule:<24} {t['label']:<34} {s['n']:>6d} "
                  f"{s['rate_span']:>7.2f} {s['atsend_clean_p50']:>9.2f} "
                  f"{s['atsend_clean_mints']:>6d} "
                  f"{len(s['covered'])}/{s['hard_n']:<7}")
        if retail:
            n, span, rate = retail_rate(retail, thresh, cooldown, rule)
            # THE REFERENCE IS THE SHIPPED BUILD, not our worst capture. The
            # other two are REFUTED configurations whose grant cadence is
            # 3.5-5.0/s, so quoting the ratio against them would let a rule
            # that fires on grant cadence look discriminating -- which is
            # exactly the failure this control is here to catch.
            ref = next((t for t in tracks
                        if SHIPPED in t["label"] and not _why_no_fire(t)), None)
            if ref is None:
                print(f"    {rule:<24} {'RETAIL CONTROL (pooled)':<34} "
                      f"{n:>6d} {rate:>7.2f} -- no shipped-build capture in "
                      f"this run to compare against; ratio REFUSED")
                print()
                continue
            ours = score(ref, thresh, cooldown, rule)["rate_span"]
            ratio = (rate / ours) if ours > 0 else float("inf")
            verdict = ("FAILS the control" if ratio >= 1.0 / DISCRIMINATION
                       else "separates")
            print(f"    {rule:<24} {'RETAIL CONTROL (pooled)':<34} {n:>6d} "
                  f"{rate:>7.2f} {'':>9} {'':>6} "
                  f"-- {ratio:.3f}x the SHIPPED build ({ours:.2f}/min, which "
                  f"has {len(ref['hard_idx'])} hard jump(s) to retail's 0): "
                  f"{verdict}")
        print()


# --- the arc's own captures -------------------------------------------------
ARC_STAMPS = ("20260819T145717", "20260819T171153", "20260819T182652")
# WHICH OF THE THREE IS THE ONE WE SHIP, and what the other two are. Recorded
# because two of the three are REFUTED configurations whose grant cadence is an
# order of magnitude higher (3.5/s and 5.0/s against 0.125/s), and a rule that
# keys on grant cadence looks brilliant on them. `studies/movement/HANDOFF.md`
# §2, candidates 3 and 5.
SHIPPED = "20260819T145717"
CONFIGS = {
    "20260819T145717": "DEFAULT -- the build we ship (40 grants / 320.3 s)",
    "20260819T171153": "REFUTED: --heading-grant, candidate 3 (740 / 210.9 s)",
    "20260819T182652": "REFUTED: --client-endpoint, candidate 5 (327 / 65.6 s)",
    "20260811T173940": "ours, ZERO player grants -- the internal null",
}
# `ours`, build 38797, and the one with ZERO player grants -- an internal null
# rather than the retail control. It is named here because a handoff has already
# described it as retail once, and origin.py says otherwise.
NULL_STAMP = "20260811T173940"


def validation_pair():
    """`validate_sync_model` on the vault's one overlapping pair, or None."""
    stamp, tap = VALIDATION
    try:
        cap = capture_path(stamp)
        mt = os.path.join(vaultpath.require_dir("captures", "movetap"), tap)
    except SystemExit:
        return None
    return validate_sync_model(cap, mt)


def require_single_origin(paths):
    """Refuse a run that pools `ours` with `live`. Returns the single origin.

    A FREE FUNCTION so it can be exercised directly. `track_from_capture`
    already refuses a non-`ours` capture one at a time, which catches the
    single-file case and NOT the pooling one -- two files that are each fine
    on their own are still two different oracles when averaged.
    """
    orgs = {origin.origin_of(p)[0] for p in paths}
    if len(orgs) > 1:
        raise Refused(
            f"resyncscore: asked to score {sorted(orgs)} in one run. A "
            f"consumer that pools origins is measuring neither -- see "
            f"toolkit/origin.py.")
    return orgs.pop() if orgs else None


def capture_path(stamp):
    root = vaultpath.require_dir(
        "captures", "gamesrv",
        why="the arc's own captures, which are what 'what would this have "
            "done?' is asked of")
    p = os.path.join(root, f"authsrv-{stamp}-c1.jsonl")
    if not os.path.isfile(p):
        raise Refused(f"resyncscore: no capture at {p}. No capture, no answer.")
    return p


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--capture", action="append", default=None,
                    help="one of our gamesrv captures (repeatable)")
    ap.add_argument("--retail", action="store_true",
                    help="score the live corpus as the control")
    ap.add_argument("--stamp", default=None, help="one live stamp, with --retail")
    ap.add_argument("--rule", default=RULE_A, choices=list(RULES))
    ap.add_argument("--threshold", type=float, default=RESYNC_SEPARATION)
    ap.add_argument("--cooldown", type=float, default=RESYNC_COOLDOWN)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--compare", action="store_true",
                    help="every rule, every capture, and the retail control")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        import test_resyncscore
        return test_resyncscore.main()

    if a.retail and not a.compare:
        tracks = retail_tracks(a.stamp)
        print_retail_control(tracks, a.rule, a.threshold, a.cooldown)
        return 0

    paths = a.capture or [capture_path(s) for s in ARC_STAMPS] + \
        [capture_path(NULL_STAMP)]
    require_single_origin(paths)
    if a.compare:
        ours = [track_from_capture(p) for p in paths]
        print_compare(ours, retail_tracks(a.stamp), a.cooldown, a.threshold)
        # ALWAYS printed with the comparison, never on request: Rule E is in
        # that table, and a forward model quoted without the check that can
        # refute it is the thing this repo keeps catching in other people's
        # work.
        print_validation(validation_pair())
        return 0
    for p in paths:
        t = track_from_capture(p)
        print_track(t, a.rule, a.threshold, a.cooldown)
        if a.sweep:
            print_sweep(t, a.rule)
    return 0


if __name__ == "__main__":
    sys.exit(main())
