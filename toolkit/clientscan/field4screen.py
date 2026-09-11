#!/usr/bin/env python3
r"""REALFIX-F1b -- the FIELD-4 policy pre-screen.

Given a candidate policy for the `0x0029`'s FIELD 4 -- the plane word the client
writes to `agent+0x80` on the SYNC copy -- how many grants would have carried a
value that disagreed with the plane that copy was actually on? The whole case
for the instrument, which half of it is falsifiable and which half is a theorem
of its own simulator, is the banner immediately below: it travelled here
verbatim with the code it argues about, and it is the thing to read first.

TWO POINTERS, because two of the moved comments name a referent that STAYED in
`grantsim.py`. Neither moved line was reworded.

  (1) The banner's "a different instrument from everything above it" and
      "Everything above this line scores whether a policy would have SNAPPED"
      mean **`grantsim.py`'s** own sections -- REALFIX-C0's radius, C1/C2's
      calibration, C3's replay, C5's band and its refusal to rank. Those are
      still above this code in that file; they are not in this one.

  (2) `FIELD4_SCREEN`'s comment says `authsrv.py` "MAY NOT import this module
      (grantsim imports authsrv; the server path stays dependency-clean)". The
      ban is unchanged and it now covers this file too, for the same reason and
      in the same direction. This module reaches the server only through
      `grantinputs._authsrv()`, which imports it on FIRST USE and never at
      import time -- so the dependency still runs one way, and `authsrv.py`
      still imports neither file. The tie is still made on the test side:
      `test_grantsim.py` §10 pins every cell against the live computation and
      `test_position_trust.py` §16 rebuilds the banner's rows from the dict,
      both of them reading it as `grantsim.FIELD4_SCREEN`, which `grantsim.py`
      re-exports from here.

THE REFUSAL MESSAGES SAY `grantsim:` AND THAT IS DELIBERATE, not a rename this
move forgot. They travelled verbatim, and they are still correct: this module
has no CLI, and the command whose output a reader is holding is
`python toolkit/clientscan/grantsim.py --field4`.

READS ONLY, like its origin: opens vault captures through `grantinputs`, writes
nothing, sends nothing, launches nothing, and nothing here runs at import time.
"""
import bisect
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import movesync                                                # noqa: E402
from grantinputs import (Refused, capture_path, movetap_path,  # noqa: E402
                         require_ours, _authsrv)


# =========================================================================
# REALFIX-F1b -- the FIELD-4 POLICY PRE-SCREEN, and it is a different
# instrument from everything above it
# =========================================================================
#
# WHAT IT IS FOR. Everything above this line scores whether a policy would have
# SNAPPED. This scores a different question, cheaply and against captures the
# vault already holds: given a candidate policy for the 0x0029's FIELD 4 -- the
# plane word the client writes to agent+0x80 on the SYNC copy -- how many
# grants would have carried a value that disagreed with the plane that copy was
# actually on? That count is REALFIX-F1's own pre-registered falsifier, it is
# the one F1 FAILED (5 of 93), and it is measurable offline because the grants
# are on the wire and the copy's true plane is in movetap.
#
# WHY IT IS WORTH A PERMANENT MODULE rather than a scratch script: this is how
# every future field-4 policy gets pre-screened before it costs a live arm.
# Three have now been proposed, two have been run, and one of the two ran
# against a prediction that an hour of offline replay would have shown it could
# not meet.
#
# WHAT IT MEASURES THAT IS NOT A TAUTOLOGY, stated first because the headline
# number IS partly one and saying so afterwards would be too late:
#
#   1. THE ARRIVAL MODEL IS FALSIFIABLE AND IT SURVIVES. The SYNC copy's plane
#      word is written by TWO writers: field 4 at the grant, and field 3 again
#      at ARRIVAL, when the client consumes the destination into m_point. In
#      capture 20260821T143411 the word changes 24 times and 17 of those are
#      NOT at a grant -- and all 17 land on an arrival this model predicts,
#      with ZERO free parameters (the formula is the client's own bake, the
#      speed is the 288.0 the client itself holds in 4,115 of 4,115 samples).
#      Had the model been wrong, 17 writes at up to 1.9 s from any grant had
#      every opportunity to say so.
#   2. THE REPLAY REPRODUCES BOTH CAPTURES' MEASURED COUNTS. Run each capture's
#      OWN arm through the simulator and it must return the number measured
#      directly against movetap -- 8 for the P2 control, 5 for the F1 arm.
#      That is the calibration gate and it is checked, not assumed.
#
# AND THE PART THAT IS ANALYTIC, NAMED HERE SO NOBODY HAS TO DISCOVER IT: once
# the arrival model is granted, F1b's zero FOLLOWS *under the closed model*.
# The copy's plane word is the more recent of (the last field 4 we sent) and
# (the field 3 of the last grant that arrived); F1b sends exactly the second of
# those; and when no arrival has intervened since the last grant, F1b's own
# previous send is already that same value. So `field4_replay` returning 0 for
# F1b is a THEOREM OF THAT SIMULATOR and NOT a measurement of the fix. It is
# reported, labelled, and it is NOT the headline.
#
# WHICH IS WHY THE PRIMARY METRIC IS `field4_anchored`, NOT `field4_replay`.
# It compares a policy's field 4 against the plane word MOVETAP ACTUALLY READ in
# the sample before the grant, and it refuses every grant where the observation
# has been contaminated by the counterfactual's own divergence. It cannot be
# satisfied by a model agreeing with itself -- and on the F1 capture it says
# F1b would have left THREE mismatches, not zero. See `FIELD4_RESIDUAL_NOTE`.

# The two REALFIX-L3 arms, their taps, and WHICH POLICY ACTUALLY RAN in each.
# The third L3 arm (P0 default, 20260821T131938) is NOT here: it sent zero
# grants, so it has no field-4 stream to score and a 0-of-0 would read as a
# perfect policy.
FIELD4_PAIRS = (
    ("20260821T132546", "movetap-20260821T132603.jsonl", "shipped-zerolead"),
    ("20260821T143411", "movetap-20260821T143429.jsonl", "F1-planecarry"),
)

# THE PUBLISHED NUMBERS, and this instrument CORRECTS THEM UPWARDS BY TWO AND
# BY ONE. `studies/movement/FINDINGS.md` (REALFIX-F1 RAN) records 8 of 88 and 5
# of 93, measured by pairing each grant with the movetap sample NEAREST it. That
# pairing admits a sample taken AFTER the grant -- and a sample after the grant
# reads the plane word THE GRANT JUST WROTE, so a genuine rewrite scores as a
# match. It happens twice in the P2 capture (leads +0.044 s, +0.043 s) and once
# in the F1 capture (+0.016 s). Pairing with the last sample STRICTLY BEFORE the
# grant gives 10 and 6, and 10 is independently corroborated: FINDINGS's own L3
# table already reports "plane-word changes 10" for that arm, beside the 8.
# Both are kept so the correction is visible rather than silently applied.
FIELD4_PUBLISHED_NEAREST = {"20260821T132546": 8, "20260821T143411": 5}
FIELD4_MEASURED = {"20260821T132546": 10, "20260821T143411": 6}

# WHAT THE COUNTERFACTUAL FOUND, recorded here because it is a NEGATIVE and
# negatives are the ones that get quietly dropped. REALFIX-F1b's pre-registered
# prediction is "the field-4 mismatch count reaches 0". Against the F1 capture,
# observation-anchored, IT DOES NOT: 3 of 69 scorable grants survive, at capture
# t = 50.21 / 77.42 / 104.67 -- three of the same five rows FINDINGS lists as
# F1's residual.
#
# THE THREE ARE A TIMING RACE, NOT A LOGIC ERROR, and the distinction is the
# whole diagnosis. F1b's field 4 turns on one comparison, `arrival <= now`, and
# all three grants land 8 / 24 / 35 ms AFTER a modelled arrival that the client
# had not yet performed. Measured against the client's own 17 unambiguous
# arrival writes, the model lands INSIDE the observation bracket in 13 of 17 and
# is strictly early by AT MOST 20 ms in the other 4. That one-sided residual is
# the size of a display frame, and the client consumes an arrival on a frame
# rather than on the tick -- so the model is right about the tick and early
# about the ACT.
#
# F1b's LOGIC nonetheless fixes what it was built to fix: of F1's 6 anchored
# residuals, the 3 that are genuine TWO-INTERVAL lags are GONE. Only the race
# remains, and it is a class of error F1 shares -- those same three grants are
# in F1's residual too, and FINDINGS reads all five of F1's as two-interval
# lags. Three of them are not; they are this race, and F1 hit them by sending
# the right value 24 ms early rather than by lagging.
#
# THE OBVIOUS PATCH IS REFUSED. A guard band -- treat a grant as arrived only
# past `arrival + eps` -- closes all three at eps ~ 40 ms. It is NOT adopted:
# eps has no derivation, it would be fitted to the one capture that scores it,
# and the house rule is to prefer the check with no free parameter. If a
# frame-consumption term is real it should be MEASURED (the client's frame clock
# is readable) and then it stops being free. Until then F1b ships with its
# residual stated rather than tuned away, and its startup banner predicts 3
# rather than 0.
FIELD4_RESIDUAL_NOTE = (
    "F1b does NOT reach 0. Anchored on the F1 capture it leaves 3 of 69, all "
    "three grants landing 8-35 ms after a modelled arrival the client had not "
    "yet performed -- a sub-frame race on `arrival <= now`, not a logic error. "
    "Its logic does close all 3 of F1's genuine two-interval lags. A ~40 ms "
    "guard band would close the rest and is REFUSED as a fitted parameter.")

# What `--zero-lead --arrival-carry` should be expected to produce on a rerun of
# the REALFIX-L3 plan, and it is the number the server's startup banner prints.
# NOT zero. Scored offline, above.
FIELD4_F1B_EXPECTED = 3

# THE SIX CELLS THE SERVER'S --arrival-carry BANNER TRANSCRIBES, so that the
# banner and the scorer cannot drift apart in silence. `authsrv.py` prints this
# table as the evidence for its own pre-registered prediction and MAY NOT import
# this module (grantsim imports authsrv; the server path stays dependency-clean),
# so the tie is made on the test side: `test_grantsim.py` §10 pins every cell
# against the live computation, and `test_position_trust.py` §16 rebuilds the
# banner's three printed rows from this dict and requires them verbatim.
#
# WHY IT IS A CONSTANT AND NOT A COMMENT. It was a comment. A mutation lane
# rewrote the banner's F1b row from "3 of 69" to "0 of 69" -- the DRAFTED
# prediction this screen had already refuted, printed beside prose still reading
# "F1b DOES NOT REACH ZERO" and "come in at ~3" -- and the whole suite stayed
# green at 215/215. That is section 15's own defect (a number the artifact
# exists to make unrationalisable, left free) reappearing in the numeric half of
# the same banner one section later.
#
# (mismatch, scored) per policy per capture; `scored` is the denominator AFTER
# the contamination refusal, which is why the two counterfactual columns on the
# P2 capture score over 8 grants and not 88.
FIELD4_SCREEN = {
    "shipped-zerolead": {"20260821T132546": (10, 88),
                         "20260821T143411": (18, 36)},
    "F1-planecarry": {"20260821T132546": (0, 8),
                      "20260821T143411": (6, 93)},
    "F1b-arrivalcarry": {"20260821T132546": (0, 8),
                         "20260821T143411": (3, 69)},
}

# TWO ROLES, TWO CONSTANTS, and they were ONE constant until 2026-08-21.
#
# (a) PAIRING. Pair a grant with a tap sample, refusing past this. Both files
# carry `wall_unix`, so this is REALFIX-T1-exact -- the residual is the float
# stamp's own 0.354 ms, not a clock alignment -- and 0.25 s is the same window
# REALFIX-E is defined over. The tap runs at 7.8-9.5 Hz against a 20 Hz request,
# so a sample is 0.103-0.108 s wide (median, both captures) and this admits at
# most two. Used by `_nearest_tap`, `field4_seed` and `field4_anchored`.
#
# ⚠ THIS ROLE IS NOT BINDING ON THE TWO CAPTURES WE HAVE, which is exactly why
# it needs its own name and its own check rather than sharing a number. Every
# grant's last-strictly-before sample lands within 0.122 s, so all 88 and all 93
# pair identically at 0.25 s and at 5.0 s: a 20x widening moves neither the
# anchored headline nor the calibration pin, and nothing would have gone red.
# On a capture with a real tap dropout the strictly-before rule would reach back
# ACROSS the gap and only this constant would stop it. `test_grantsim.py` §10
# therefore brackets it from BOTH sides against the captures' own cadence --
# wide enough that the observed pairing lead fits, narrow enough that it cannot
# span three tap intervals -- so the guard is a check the data can refute.
FIELD4_PAIR_GAP = 0.25

# (b) ATTRIBUTION. "Is this plane-word transition one WE wrote?" A transition
# within this of a grant is ours (field 4 stamped it); everything else is a
# write by the CLIENT and is the population the arrival model is falsified
# against. Used by `field4_client_writes` and `field4_arrival_check`.
#
# THIS ROLE IS BINDING, and it is the one a mutation reddens: widening it makes
# every transition attributable to a grant, the arrival control loses its
# population, and the instrument refuses 0-of-0 rather than passing it. Same
# value as (a) today and derived the same way -- two tap intervals -- but they
# answer different questions and either could move without the other.
FIELD4_ATTRIB_GAP = 0.25

# The gate for "a non-grant plane write lands on a modelled arrival". Three tap
# intervals at the rate these captures actually achieved. REALFIX-T3 said the
# residual becomes sample-phase-bound once the clock stopped being the problem;
# it did, and this is that bound rather than a tolerance chosen to pass.
FIELD4_ARRIVAL_GATE = 0.30

# Per-sample agreement the plane-word model must reach on both captures. Set
# from real runs (99.73% and 99.66%), floored below both at a round number that
# a genuinely broken model could not reach: predicting the word wrongly at ANY
# of the 24 transitions costs far more than 1% of 2,600 samples.
FIELD4_WORD_AGREEMENT = 0.99


def field4_grants(path):
    """[{t, dest, w3, w4}] -- every player 0x0029, WITH BOTH PLANE WORDS.

    `movesync.load_grants` reads the same rows and drops the plane words on the
    floor, which is fine for a position metric and useless here. The layout is
    the schema's own for GAME_SMSG 41 (`declared_unpack_size` 18): dword agent,
    vec2 point, word plane_dest, word plane_cur.

    FROM THE WIRE, NOT FROM THE TELEMETRY, and that is not a style preference.
    The `grant_verdict` row's `plane_cur` field did not exist when the P2
    control was captured -- it landed with `--plane-carry` later the same day --
    so a telemetry reader scores one of these two captures and refuses the
    other. The bytes are in both.

    `t` is `wall_unix`, so it is directly comparable with a movetap sample's own
    `t` with no offset estimate in between.
    """
    out = []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") != "sent" or r.get("opcode") != movesync.OP_MOVE_TO_POINT:
            continue
        raw, when = r.get("plain"), r.get("wall_unix")
        if not raw or when is None:
            continue
        b = bytes.fromhex(raw)
        if len(b) < 18:
            continue
        aid, x, y, w3, w4 = struct.unpack_from("<IffHH", b, 2)
        if aid != movesync.PLAYER_AGENT:
            continue
        out.append({"t": float(when), "dest": (x, y), "w3": w3, "w4": w4})
    return out


def field4_taps(path):
    """[{t, plane, pos, sep}] -- the SYNC copy's plane word, per movetap sample.

    `sync_at` is `position_at(agent_block, sync_clock)` and its third element is
    the plane. On the INTEGRATED branch -- which is 5,212 of 5,212 samples
    across both captures -- that is `agent+0x80` read verbatim, which is the
    exact field REALFIX-F1's falsifier names. Samples whose gate-1 read was
    refused carry `sync_at: null` and are dropped: a refusal there means the
    reader could not resolve the twin, so the row has no plane to offer.
    """
    out = []
    for s in movesync.load_movetap(path):
        sa = s.get("sync_at")
        if not sa or len(sa) < 3:
            continue
        out.append({"t": float(s["t"]), "plane": int(sa[2]),
                    "pos": (float(sa[0]), float(sa[1])), "sep": s.get("sep")})
    return out


def _nearest_tap(taps, ts, when):
    """The tap sample nearest `when`, or None past FIELD4_PAIR_GAP."""
    i = bisect.bisect_left(ts, when)
    best = None
    for j in (i - 1, i, i + 1):
        if 0 <= j < len(taps):
            d = abs(ts[j] - when)
            if best is None or d < best[0]:
                best = (d, j)
    if best is None or best[0] > FIELD4_PAIR_GAP:
        return None
    return taps[best[1]]


def field4_observed(grants, taps):
    """The DIRECT measurement: as-sent field 4 against the copy's own plane word.

    Returns {n, paired, mismatch, rows}. No model, no replay -- this is the
    number `FIELD4_MEASURED` records and the one the simulator has to hit.

    THE PAIRED SAMPLE IS THE ONE NEAREST THE GRANT AND IN PRACTICE IT IS THE ONE
    JUST BEFORE IT (median lead 0.04 s), which is what makes the metric mean
    "did this grant REWRITE the copy's plane word". That is exactly REALFIX-L3's
    treated condition: 8 plane-rewriting above-cut grants produced 3 warps, 28
    unchanged above-cut grants produced 0, Fisher p = 0.0078.
    """
    ts = [t["t"] for t in taps]
    rows, paired = [], 0
    for g in grants:
        s = _nearest_tap(taps, ts, g["t"])
        if s is None:
            continue
        paired += 1
        if g["w4"] != s["plane"]:
            rows.append({"t": g["t"], "dest": g["dest"], "w3": g["w3"],
                         "w4": g["w4"], "copy_plane": s["plane"],
                         "sep": s["sep"]})
    return {"n": len(grants), "paired": paired, "mismatch": len(rows),
            "rows": rows}


# THE THREE POLICIES. Each takes the replay's server-shaped `state`, the grant
# instant and field 3, and returns (field 4, why). All three are driven through
# the SHIPPED code where shipped code exists -- `policy_f1b` calls
# `authsrv.arrival_carry_field4` rather than restating it -- for the reason
# `_heading_grant_ok`'s docstring gives: a scorer that paraphrases the policy
# agrees with it by construction and can never catch it being wrong.

def policy_shipped_zerolead(state, now, w3):
    """REALFIX-P2 as shipped. Field 4 = field 3 = the newest report's plane."""
    return w3, "zero-lead"


def policy_f1_planecarry(state, now, w3):
    """REALFIX-F1. Field 4 = the PREVIOUS GRANT'S plane, defaulting to field 3.

    One line, and it is the shipped one: `state.get("zl_last_grant_plane",
    plane)`. The slot is advanced by the replay loop after each grant, which is
    where the shipped send site advances it.
    """
    return state.get("zl_last_grant_plane", w3), "plane-carry"


def policy_f1b_arrivalcarry(state, now, w3):
    """REALFIX-F1b. Field 4 = the plane of the grant the copy has ARRIVED at."""
    return _authsrv().arrival_carry_field4(state, now, w3)


FIELD4_POLICIES = {
    "shipped-zerolead": policy_shipped_zerolead,
    "F1-planecarry": policy_f1_planecarry,
    "F1b-arrivalcarry": policy_f1b_arrivalcarry,
}


def field4_replay(grants, policy, seed_plane, seed_pos):
    """Replay ONE field-4 policy over one capture's own grant stream.

    Returns {n, mismatch, rows, writes, queue_max}. `rows` carries every grant
    with the field 4 the policy would have sent, the plane word the copy would
    have been holding at that instant, and whether they disagree.

    THE PLANE WORD HAS TO BE SIMULATED, and the reason is the whole subtlety of
    this scorer. Field 4 is WRITTEN to `agent+0x80`, so changing the policy
    changes the copy's plane-word history too -- the observed movetap trace is
    ground truth only for the policy that actually ran. What is POLICY-INVARIANT
    is everything else: the grant instants, the destinations and field 3 are
    identical under all three candidates (they differ in field 4 alone), so the
    ARRIVAL SCHEDULE is the same in every replay and the arrival writes are the
    same. Only the grant writes move.

    THE MODEL, and both writers are measured rather than assumed:
      * at a GRANT, the client writes field 4 to agent+0x80. Measured: 10 of 10
        plane-word transitions in the P2 capture are at a grant, and the paired
        sample before each residual reads the previous field 4 in 87 of 87.
      * at ARRIVAL, the client writes field 3 -- it consumes the destination
        into m_point, and m_point's plane is +0x80. Measured: 17 of 17 non-grant
        transitions in the F1 capture land on a modelled arrival.

    A PENDING ARRIVAL THAT A NEW GRANT SUPERSEDES NEVER FIRES, and dropping it
    is the same discard `arrival_carry_advance` makes for the same reason: the
    copy re-aims mid-leg and never reaches that destination, so its plane is
    never written. A simulator that let it fire would credit every policy with
    a write the client does not make.

    SEEDED FROM THE TAP because these captures start mid-session: the copy's
    position and plane word at the first grant are read once from the sample
    before it. The live server has no such need -- it seeds its SYNC model where
    it places the character -- and the seed is reported so a reader can see how
    little of the answer rests on it (one grant of 88, and both captures begin
    parked at the spawn point with the copy and the player on the same plane).
    """
    A = _authsrv()
    if not grants:
        raise Refused("grantsim: a field-4 replay over an empty grant stream")
    state = {"sync_from": (float(seed_pos[0]), float(seed_pos[1])),
             "sync_to": None, "sync_at": grants[0]["t"],
             "ac_queue": [], "ac_arrived": None}
    word = int(seed_plane)
    pending = None                       # (arrival_t, field3) not yet due
    rows, writes, queue_max = [], [], 0
    for g in grants:
        now, dest, w3 = g["t"], g["dest"], g["w3"]
        # (1) an arrival that came due since the last grant already wrote.
        if pending is not None and pending[0] is not None and pending[0] <= now:
            word = pending[1]
            writes.append((pending[0], pending[1], "arrival"))
        field4, why = policy(state, now, w3)
        rows.append({"t": now, "dest": dest, "w3": w3, "field4": field4,
                     "word_before": word, "mismatch": field4 != word,
                     "why": why, "as_sent": g["w4"]})
        # (2) the leg, computed BEFORE the send moves the SYNC model -- the
        # ordering that makes the in-flight supersede case come out right.
        arrival, _dist = A.arrival_carry_leg(state, now, dest)
        # (3) the grant writes field 4; any pending arrival is superseded.
        word = field4
        writes.append((now, field4, "grant"))
        pending = (arrival, w3)
        # (4) advance the server's own model exactly as the shipped send does.
        A._note_wire_move(state, A.GAME_SMSG_AGENT_MOVE_TO_POINT,
                          [A.PLAYER_AGENT_ID, list(dest)], now)
        state["zl_last_grant_plane"] = w3
        A.arrival_carry_advance(state, now, arrival, w3, dest)
        queue_max = max(queue_max, len(state["ac_queue"]))
    if pending is not None and pending[0] is not None:
        writes.append((pending[0], pending[1], "arrival"))
    writes.sort(key=lambda w: w[0])
    return {"n": len(grants), "mismatch": sum(1 for r in rows if r["mismatch"]),
            "rows": rows, "writes": writes, "queue_max": queue_max,
            "seed": (seed_plane, tuple(seed_pos))}


def field4_seed(grants, taps):
    """(plane, position) of the SYNC copy at the first grant, from the tap."""
    ts = [t["t"] for t in taps]
    s = _nearest_tap(taps, ts, grants[0]["t"])
    if s is None:
        raise Refused(
            "grantsim: the first grant pairs with no movetap sample inside "
            f"{FIELD4_PAIR_GAP:.2f} s -- the replay would be seeded from a "
            "position and a plane nobody measured")
    return s["plane"], s["pos"]


def field4_arrival_check(replay, taps):
    """Does the model's ARRIVAL schedule explain the writes WE did not make?

    This is the falsifiable half of the instrument. Walk the observed plane-word
    transitions; ignore any within `FIELD4_ATTRIB_GAP` of a grant (we wrote those
    ourselves through field 4); every remaining one is a write by the CLIENT,
    and the model says it must be an arrival carrying that plane as its field 3.

    Returns {n, hit, miss, dt_median, dt_max, rows}. `miss` is the number the
    model cannot explain, and it is the count that can go red.
    """
    grant_ts = [w[0] for w in replay["writes"] if w[2] == "grant"]
    arrivals = [(w[0], w[1]) for w in replay["writes"] if w[2] == "arrival"]
    hit, miss, dts, early, rows = 0, 0, [], [], []
    prev, prev_t = None, None
    for s in taps:
        p = s["plane"]
        if prev is not None and p != prev:
            i = bisect.bisect_left(grant_ts, s["t"])
            near = min([abs(grant_ts[j] - s["t"])
                        for j in (i - 1, i) if 0 <= j < len(grant_ts)]
                       or [float("inf")])
            if near <= FIELD4_ATTRIB_GAP:
                prev, prev_t = p, s["t"]
                continue
            cand = sorted(((abs(a - s["t"]), a)
                           for a, pl in arrivals if pl == p))
            if cand and cand[0][0] <= FIELD4_ARRIVAL_GATE:
                hit += 1
                dts.append(cand[0][0])
                # THE SIGNED RESIDUAL, and it is the one that matters for F1b.
                # The client's write happened somewhere in (prev_t, s.t] -- the
                # tap bracket. `early_by > 0` means the model fired BEFORE that
                # bracket even opened, which is the only way F1b can call a
                # grant "arrived" that the client has not yet acted on.
                early.append(prev_t - cand[0][1])
            else:
                miss += 1
                rows.append({"t": s["t"], "was": prev, "now": p,
                             "best": cand[0][0] if cand else float("inf")})
        prev, prev_t = p, s["t"]
    early_s = sorted(early)
    return {"n": hit + miss, "hit": hit, "miss": miss, "rows": rows,
            "dt_median": (sorted(dts)[len(dts) // 2] if dts else float("nan")),
            "dt_max": (max(dts) if dts else float("nan")),
            "early_n": sum(1 for e in early if e > 0.0),
            "early_max": (max(early_s) if early_s else float("nan")),
            "early_median": (early_s[len(early_s) // 2] if early_s
                             else float("nan"))}


def field4_race(rows, replay):
    """For each anchored residual: how long after a MODELLED ARRIVAL did it land?

    The diagnosis, not a verdict. A residual a few tens of milliseconds after an
    arrival the client had not yet performed is a RACE on `arrival <= now`; one
    seconds away from any arrival is a policy LAG. Returns the same rows with
    `since_arrival` added, so the reader sees the two populations rather than a
    threshold somebody chose.
    """
    arrivals = sorted(w[0] for w in replay["writes"] if w[2] == "arrival")
    out = []
    for r in rows:
        i = bisect.bisect_right(arrivals, r["t"]) - 1
        r = dict(r)
        r["since_arrival"] = (r["t"] - arrivals[i]) if i >= 0 else float("nan")
        out.append(r)
    return out


def field4_word_check(replay, taps, seed_plane):
    """Per-sample: does the write schedule predict the observed plane word?

    2,500-odd trials per capture against 24 transitions, so a model that had the
    arrival times wrong could not sit above 99%. Returns {n, ok, frac, wrong}.
    """
    wt = [w[0] for w in replay["writes"]]
    ok = 0
    for s in taps:
        i = bisect.bisect_right(wt, s["t"]) - 1
        pred = replay["writes"][i][1] if i >= 0 else seed_plane
        if pred == s["plane"]:
            ok += 1
    n = len(taps)
    return {"n": n, "ok": ok, "wrong": n - ok,
            "frac": (ok / n if n else float("nan"))}


def field4_client_writes(grants, taps):
    """The plane-word writes the CLIENT made for itself. PURELY OBSERVATIONAL.

    Every transition of the observed word that is not within FIELD4_ATTRIB_GAP
    of a grant. No model is consulted -- that is the point: these are the instants
    at which the client overwrote whatever we had stamped, so they are where the
    observed trace RE-ANCHORS and becomes usable again for a counterfactual.

    They are also POLICY-INVARIANT. Every candidate sends the same destinations
    at the same instants with the same field 3 and differs in field 4 alone, so
    the copy's position track -- and therefore when it arrives and what the
    client writes on arriving -- is the same under all of them.
    """
    gts = [g["t"] for g in grants]
    out, prev = [], None
    for s in taps:
        p = s["plane"]
        if prev is not None and p != prev:
            i = bisect.bisect_left(gts, s["t"])
            near = min([abs(gts[j] - s["t"])
                        for j in (i - 1, i) if 0 <= j < len(gts)]
                       or [float("inf")])
            if near > FIELD4_ATTRIB_GAP:
                out.append((s["t"], p))
        prev = p
    return out


def field4_anchored(grants, taps, replay):
    """THE PRIMARY METRIC. A policy's field 4 against the word MOVETAP READ.

    Returns {scored, mismatch, skipped, rows, why_skipped}.

    THE OPERAND IS THE LAST SAMPLE STRICTLY BEFORE THE GRANT, never the nearest.
    A sample taken after the grant reads the plane word the grant itself just
    wrote, which turns a genuine rewrite into a match -- that is the defect this
    instrument found in the published counts (8 and 5 become 10 and 6; see
    FIELD4_PUBLISHED_NEAREST).

    CONTAMINATION, and refusing it is what stops this being another model
    agreeing with itself. The observed word is a record of what the arm that
    ACTUALLY RAN stamped. The moment a counterfactual policy would have sent a
    different field 4, every later observation is a reading of the wrong
    history -- until the CLIENT overwrites it at an arrival, which is
    policy-invariant and re-anchors the trace. So a grant is scored only while
    `dirty` is clear, and `dirty` is set by a divergence and cleared by a client
    write. `skipped` is reported beside every count, because 3 of 69 and 3 of 3
    are not the same claim.

    ⚠ THE P2 CAPTURE HAS ZERO CLIENT WRITES, so on it nothing ever re-anchors
    and both counterfactual columns score over ~8 grants. That is not a defect
    of this metric, it is the capture: under `--zero-lead` field 4 always equals
    the client's current plane, so the client never has to correct us and never
    reveals what it thinks. The F1 capture is the one that carries the result,
    and it does so BECAUSE F1's field 4 lags -- the lag is what makes the
    client's own opinion observable 17 times.
    """
    ts = [t["t"] for t in taps]
    writes = field4_client_writes(grants, taps)
    dirty, ci = False, 0
    scored, rows, skipped = 0, [], {"contaminated": 0, "unpaired": 0}
    # THE PAIRING WINDOW'S OWN MARGIN, reported rather than assumed. `lead_max`
    # is the largest gap between a grant and the last sample STRICTLY BEFORE it
    # -- taken whether or not that sample fell inside the window, which is the
    # whole point. Recording only the ones that PAIRED would make the margin
    # unfalsifiable from the narrow side: shrink the window and the offending
    # grants simply stop being counted, so `lead_max <= FIELD4_PAIR_GAP` would
    # hold by construction. Measured over every grant it goes red in BOTH
    # directions. Policy-invariant (pairing reads no field 4).
    leads = []
    for k, g in enumerate(grants):
        while ci < len(writes) and writes[ci][0] <= g["t"]:
            dirty = False
            ci += 1
        j = bisect.bisect_left(ts, g["t"]) - 1
        if j >= 0 and g["t"] - ts[j] >= 0.0:
            leads.append(g["t"] - ts[j])
        paired = j >= 0 and 0.0 <= g["t"] - ts[j] <= FIELD4_PAIR_GAP
        f4 = replay["rows"][k]["field4"]
        if not paired:
            skipped["unpaired"] += 1
        elif dirty:
            skipped["contaminated"] += 1
        else:
            scored += 1
            if f4 != taps[j]["plane"]:
                rows.append({"t": g["t"], "dest": g["dest"], "w3": g["w3"],
                             "field4": f4, "observed": taps[j]["plane"],
                             "lead": g["t"] - ts[j], "sep": taps[j]["sep"]})
        if f4 != g["w4"]:
            dirty = True
    return {"scored": scored, "mismatch": len(rows), "rows": rows,
            "skipped": sum(skipped.values()), "why_skipped": skipped,
            "client_writes": len(writes),
            "lead_max": max(leads) if leads else float("nan")}


def field4_capture(stamp, tap, arm):
    """One capture, every policy, plus the two calibration checks. All `ours`."""
    path = capture_path(stamp)
    require_ours([path], what="REALFIX-F1b's field-4 counterfactual")
    grants = field4_grants(path)
    taps = field4_taps(movetap_path(tap))
    if not grants or not taps:
        raise Refused(
            f"grantsim: {stamp} has {len(grants)} grants and {len(taps)} "
            f"readable movetap samples -- a field-4 census over either empty "
            f"population is not a low mismatch count")
    seed_plane, seed_pos = field4_seed(grants, taps)
    obs = field4_observed(grants, taps)
    out = {"stamp": stamp, "tap": tap, "arm": arm, "observed": obs,
           "grants": len(grants), "taps": len(taps),
           "seed_plane": seed_plane, "policies": {}, "anchored": {}}
    for name, pol in FIELD4_POLICIES.items():
        rep = field4_replay(grants, pol, seed_plane, seed_pos)
        out["policies"][name] = rep
        out["anchored"][name] = field4_anchored(grants, taps, rep)
    own = out["policies"][arm]
    own_anchored = out["anchored"][arm]
    out["calibration"] = {
        # THE GATE. Replaying a capture's OWN arm reproduces exactly what it
        # sent, so the anchored score of that replay must equal the anchored
        # score of the wire -- and `dirty` can never be set, so every grant is
        # scored. That is the pin, and it is 10 / 6 rather than the published
        # 8 / 5 for the pairing reason at FIELD4_PUBLISHED_NEAREST.
        "own_arm": arm,
        "own_anchored": own_anchored["mismatch"],
        "own_anchored_scored": own_anchored["scored"],
        "own_replay": own["mismatch"],
        "own_nearest": obs["mismatch"],
        "measured_pin": FIELD4_MEASURED.get(stamp),
        "published_nearest": FIELD4_PUBLISHED_NEAREST.get(stamp),
        "own_agrees": own_anchored["mismatch"] == FIELD4_MEASURED.get(stamp),
        "own_full_coverage": own_anchored["scored"] == len(grants),
        # THE SHARPEST HALF OF THE GATE, stated on its own because "the counts
        # agree" could in principle be two errors cancelling. Replaying a
        # capture's own arm must reproduce its field 4 BYTE FOR BYTE, all 88 and
        # all 93. For F1 that is a real exercise of the policy: its slot
        # advances only on a SEND, so the 6 rate-limit refusals in that capture
        # have to leave it alone or the stream drifts.
        "own_reproduces_wire": all(
            r["field4"] == r["as_sent"] for r in own["rows"]),
        "arrival": field4_arrival_check(own, taps),
        "word": field4_word_check(own, taps, seed_plane),
        # THE PAIRING WINDOW, BRACKETED FROM BOTH SIDES BY THE CAPTURE ITSELF.
        # `pair_lead_max` is how close FIELD4_PAIR_GAP came to binding (it does
        # not, on either capture) and `tap_dt_median` is the cadence the
        # constant's own derivation cites -- "a sample is ~0.105 s wide and this
        # admits at most two". §10 checks the constant against both, so a
        # widened window is caught by a check the data can refute instead of
        # only indirectly, through the arrival control collapsing to 0-of-0.
        "pair_lead_max": own_anchored["lead_max"],
        "tap_dt_median": (sorted(b["t"] - a["t"]
                                 for a, b in zip(taps, taps[1:]))[
                              max(len(taps) - 1, 1) // 2]
                          if len(taps) > 1 else float("nan")),
    }
    return out


def field4_census(pairs=FIELD4_PAIRS):
    return [field4_capture(*row) for row in pairs]
