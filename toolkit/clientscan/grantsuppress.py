#!/usr/bin/env python3
"""WHAT WOULD SUPPRESSING THE GRANT HAVE DONE? Replayed against tonight's captures.

    python toolkit/clientscan/grantsuppress.py --all        # START HERE
    python toolkit/clientscan/grantsuppress.py --capture PATH
    python toolkit/clientscan/grantsuppress.py --sweep      # the window, priced
    python toolkit/clientscan/grantsuppress.py --selftest   # runs test_grantsuppress

THIS FILE SENDS NOTHING AND CHANGES NOTHING. It never imports `authsrv.py`, and
`authsrv.py` never imports it. It is a costing instrument for a server change
somebody else is making, run BEFORE the owner plays the reproduction again.

------------------------------------------------------------------------------
WHY A NEW FILE AND NOT AN EXTENSION
------------------------------------------------------------------------------
`movesync.py` owns SEPARATION and the two-arm hard-jump bar, and this file
IMPORTS both rather than re-deriving either -- `load_wire_reports`, `steps`,
`hard_steps`, `load_grants`, `against_grants`, `RUN_SPEED`. Nothing here decodes
a position or decides what a jump is. `resyncscore.py` is the neighbouring
counterfactual and prices an ADDITIVE fix: send a `0x002C` we have never sent.
Its whole API -- `track`, `outstanding`, `fires`, `coverage`, arrival models --
is built around a message going out. This question is the SUBTRACTION, and its
spine is a stream neither file loads: the c2s control traffic (`0x003D` with its
`movementType`, `0x0047`, `0x003E`) that says whether the player's own hands were
on the keyboard when we granted.

------------------------------------------------------------------------------
THE MECHANISM THIS PRICES, in the sentences the binary and the wire support
------------------------------------------------------------------------------
`0x0029 AGENT_MOVE_TO_POINT` is SYNC-ONLY: it steers `[agentMgr+0xE8]`, the
server-authoritative copy, and cannot reach the locally-predicted copy the
player sees (`0x0025`'s async arm is gated shut for the client-controlled
agent). So a grant issued WHILE THE PLAYER IS WALKING UNDER THEIR OWN KEYBOARD
CONTROL drives one copy while the other goes somewhere else, and the separation
grows unrendered. Each grant also re-evaluates the client's own snap test --
the grant bake `0x005FEBEB` is one of only three callers of `0x00605FC0`, all
message-driven, never per-frame -- and above 299.332591 u of straight-line
separation the client hard-copies SYNC onto ASYNC. That is the warp.

------------------------------------------------------------------------------
THE RULE, WRITTEN OUT BEFORE ANY NUMBER IS PRINTED
------------------------------------------------------------------------------
TWO ARMS, and both are priced, because an arm scored only behind another arm has
not been scored.

ARM 1 -- KEYBOARD-DRIVING SUPPRESSION. Refuse to send a player `0x0029` at
server time `t` when the client is driving itself from the keyboard at `t`:

    a c2s 0x003D MOVE_SET_HEADING arrived at h, with t - W <= h <= t
    AND that heading's movementType (values[4]) is non-zero
    AND no c2s 0x0047 MOVE_CANCEL_REPORT_POSITION arrived in (h, t]

ARM 2 -- RATE LIMIT. Refuse a grant that comes less than `GRANT_MIN_INTERVAL`
after the last grant that WAS SENT. It is a state machine, not a pairwise
filter over the log: a suppressed grant does not reset the floor.

`W` and the floor are the only free parameters and both are swept, never
asserted. The DEFAULTS ARE THE SERVER'S OWN (`GRANT_LOCAL_WINDOW` 3.0,
`GRANT_MIN_INTERVAL` 0.5, read out of `authsrv.py`'s source text and pinned by
`test_grantsuppress.py` §15), so every number here is a number for the rule
that will actually run. This file's own independently derived window is
`MEASURED_WINDOW` = 2.0 -- of the 1,001 gamesrv captures on disk, the 74 that
carry two headings inside one hold give n = 4,190 intervals at p50 0.452 s, p95
1.808 s, 96.25% at or under 2.00 s -- and the
headline is the same at both, which is worth something because the two windows
were sized separately. A W of 1.0 (`authsrv.py`'s own `fresh` constant, and the
value a reviewer reaches for) is NOT enough: 11% of intra-hold gaps exceed it,
which is grant-shaped leakage in the exact posture (run in a straight line,
spam-click) the owner is most likely to try next.

ARM 1'S THREE TERMS, AND ONLY TWO OF THEM CAN EVER DECIDE ANYTHING.
  - RECENCY (`t - h <= W`) discriminates and is the parameter.
  - THE STOP (`no 0x0047 in (h, t]`) discriminates: in `20260820T182934`, the
    click at t=15.445 sits 0.916 s after a heading -- INSIDE W=1.0 -- and is
    correctly refused only because a `0x0047` at 14.578 lies between them.
    Delete the term and that capture's specificity goes 0/5 -> 1/5.
  - `movementType != 0` IS INERT AND IS SAID SO OUT LOUD. Re-censused in
    `authsrv.py` over 7,988 records in 119 vault captures, **0 never appears**.
    It is kept because it is the field the server's own arm reads
    (`moving = values[4]`), and it is reported as a check that has never fired
    rather than as a check. A term that cannot fail is not a term.

------------------------------------------------------------------------------
THE THING THIS FILE REFUSES TO LET ANYONE QUOTE, AND IT IS THE HEADLINE
------------------------------------------------------------------------------
"4 of the 5 hard jumps had a grant inside 0.5 s" is TRUE and is very nearly
CONTENT-FREE, because during the reproduction's click storm the grants arrive
every 0.150 s (p50). Almost every instant in that capture has a grant inside
0.5 s. So `density_null` computes the SAME statistic over the same population
the jumps are drawn from -- every report instant -- and `rotation_control`
re-asks it of the jump times rotated inside the grant span. If the jumps do not
beat their own baseline, the 0.5 s association is grant DENSITY and not
mechanism, and this file says so above the number rather than below it.

What does discriminate is geometry, and it is `movesync`'s and not this file's:
the landing sits on the granted segment (perp p50 5.0 u against a 492.2 u
unrelated-grant control), and two of the five landings are BIT-IDENTICAL to a
point we granted. Those are printed here as `nearest granted point`, with the
same control, because the jump the 0.5 s window misses is the jump that number
explains.

READ ONLY. Opens vault captures and writes nothing.
"""
import argparse
import glob
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import movesync    # noqa: E402
import origin      # noqa: E402
import vaultpath   # noqa: E402

# --- the constants, and where each came from ---------------------------------
#
# THIS FILE'S OWN WINDOW, derived here from the captures before the server-side
# rule existed. THE DENOMINATOR IS NAMED THREE TIMES OVER, because "74 captures"
# on its own reads as the corpus and is not: `vault/captures/gamesrv` holds
# 1,001 `.jsonl`, only 80 carry a single `0x003D` at all, and 74 of those carry
# two headings inside one hold. Those 74 give n = 4,190 heading-to-heading
# intervals that do NOT straddle a `0x0047`: p50 0.452 s, p90 1.785 s, p95
# 1.808 s, and 96.25% at or under 2.00 s. The 1.80 s cluster is the client's
# straight-line report mode, which `authsrv.py` records independently ("a 1.80 s
# mode on a straight line"). 2.0 clears it with margin; 1.0 does not and leaks
# on 11.05% of intra-hold time.
#
# IT IS NOT THE OPERATING POINT AND MUST NOT BE. `authsrv.py` ships 3.0, sized
# over a NARROWER FILTER of the same corpus -- moving-`0x003D` to
# moving-`0x003D`, n = 3,420 against this file's 4,190, which is the same
# question asked without the idle stretches -- and it finds a real mode at
# 2.74-2.79 s that 2.0 cuts through. The two n's disagree because the filters
# do, not because either is wrong, and the longer window is the safe direction:
# over-refusing costs a grant, under-refusing costs a warp.
#
# So the DEFAULT below is the SHIPPED value, and every number this tool prints
# is a number for the rule that will actually run. 2.0 stays as the independent
# derivation and as a sweep row, and `test_grantsuppress.py` §15 checks the
# headline is the same at both -- an agreement worth having precisely because
# the two windows were sized separately.
MEASURED_WINDOW = 2.0
# The window swept whenever a headline is printed, so no answer exists at one
# value only. 1.0 is `authsrv.py`'s own `fresh` constant for `pos_seen`, kept in
# the sweep because a reviewer will reach for it.
WINDOW_SWEEP = (0.5, 1.0, 1.5, 2.0, 3.0, 5.0)
# How far before a jump a grant is allowed to sit and still be called its
# neighbour. 0.5 s is the number the owner's reproduction was described with;
# it is a REPORTING window, never a causal claim, and `density_null` is the
# reason that distinction is enforceable.
JUMP_LOOKBACK = 0.5
# A landing this close to a point we granted is that point, for reporting. Two
# of the reproduction's five sit at 0.000 u -- bit-identical floats -- so this
# is a display band and not a fitted threshold; the raw distance is always
# printed beside it, and the counterfactual is reported as a BRACKET across
# this band and the parameter-free one below rather than at either alone.
LANDED_ON_GRANT_UNITS = 50.0
# Rotations for the density control, in seconds. Chosen to be much larger than
# JUMP_LOOKBACK and much smaller than a capture, and SIGNED both ways so a
# one-directional artifact cannot hide.
ROTATIONS = (-7.0, -5.0, -3.0, 3.0, 5.0, 7.0)

# --- THE SECOND ARM, and where this file learned it existed ------------------
#
# The rule above was derived here from the captures alone. `authsrv.py` has since
# grown the server-side implementation, and it has TWO arms, not one: a keyboard
# latch (rule 1) AND a rate limit (rule 2). A replay that priced only the arm it
# happened to invent would hand the owner a number for a fix that is not the fix.
# So the second arm is modelled too, and the two are reported with their
# MARGINALS -- what each removes alone, and what the pair removes -- because the
# reproduction's keyboard arm swallows the whole capture and an arm measured only
# behind another arm has not been measured.
#
# THESE ARE MIRRORS OF SOMEBODY ELSE'S CONSTANTS AND ARE PINNED AS SUCH.
# `read_shipped_constants` reads `authsrv.py`'s SOURCE TEXT (never imports it --
# that is a server module and this is a read-only analyser) and
# `test_grantsuppress.py` §15 asserts these two agree with it. If the server
# retunes, that check goes red and whoever retuned re-runs this replay, which is
# the coupling that should exist: every number below is a number FOR THESE
# VALUES.
SHIPPED_LOCAL_WINDOW = 3.0      # authsrv.GRANT_LOCAL_WINDOW
SHIPPED_MIN_INTERVAL = 0.5      # authsrv.GRANT_MIN_INTERVAL
# THE RATE ARM IS SEQUENTIAL AND MUST BE SIMULATED, NOT FILTERED. The floor is
# measured from the last grant that WAS SENT, so a suppressed grant does not
# reset the clock -- filtering the logged timestamps pairwise gives a different
# and smaller answer. `suppression` runs the state machine.
ARM_KEYBOARD = "keyboard"
ARM_RATE = "rate"
ARM_BOTH = "both"

OP_SET_HEADING = movesync.OP_SET_HEADING        # c2s 0x003D
OP_CANCEL_REPORT = movesync.OP_CANCEL_REPORT    # c2s 0x0047
OP_MOVE_TO_COORD = 62                           # c2s 0x003E -- a click
OP_MOVE_TO_POINT = movesync.OP_MOVE_TO_POINT    # s2c 0x0029 -- a grant

RULE_TEXT = (
    "KEYBOARD-DRIVING SUPPRESSION: refuse a player 0x0029 at t when a c2s "
    "0x003D arrived in [t-W, t] with movementType != 0 and no 0x0047 arrived "
    "between it and t."
)

# The three arms of `authsrv.py` that can emit a player `0x0029`, told apart by
# the label the server wrote beside the bytes. Read as a PREFIX match, because
# each label carries coordinates after it.
ARM_LABELS = (
    ("HEADING GRANT", "heading"),
    ("CLIENT ENDPOINT", "client-endpoint"),
    ("AGENT_MOVE_TO_POINT(", "click"),
)
ARM_UNKNOWN = "unlabelled"


class Refused(SystemExit):
    """A refusal that stops the run rather than printing a comfortable zero."""


# --- the c2s control stream, which is what makes this a different question ---
def load_control_stream(path):
    """The client's own control traffic: headings, stops, clicks.

    A `head` row is `(t, movementType)`. `movementType` is `values[4]` and is
    kept as-is -- never coerced to a bool -- so `mt_zero` below can report that
    the term has never fired instead of the caller quietly relying on it.

    A row whose `values` is not the shape the schema says is DROPPED and
    counted, never indexed into: a silent IndexError inside a broad except is
    how a census gets zeroed, and `movesync.load_wire_reports` learned that the
    hard way.
    """
    heads, stops, clicks = [], [], []
    malformed = 0
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") != "decoded":
            continue
        op = r.get("opcode")
        if op not in (OP_SET_HEADING, OP_CANCEL_REPORT, OP_MOVE_TO_COORD):
            continue
        t = r.get("t")
        if not isinstance(t, (int, float)):
            malformed += 1
            continue
        vals = r.get("values")
        if op == OP_SET_HEADING:
            if not isinstance(vals, (list, tuple)) or len(vals) < 5:
                malformed += 1
                continue
            heads.append((float(t), vals[4]))
        elif op == OP_CANCEL_REPORT:
            stops.append(float(t))
        else:
            clicks.append(float(t))
    heads.sort()
    stops.sort()
    clicks.sort()
    return {"heads": heads, "stops": stops, "clicks": clicks,
            "malformed": malformed,
            "mt_zero": sum(1 for _t, m in heads if not m),
            "mt_values": sorted({m for _t, m in heads})}


def load_grant_arms(path, agent=movesync.PLAYER_AGENT):
    """[(t, arm)] for every player 0x0029, from the server's own label.

    The AGENT FILTER IS THE WIRE BYTES, exactly as `movesync.load_grants` does
    it, because NPC grants share the opcode and only the payload tells them
    apart. The label is read for the ARM ONLY -- which of `authsrv.py`'s three
    sites emitted it -- and never to decide whether the row counts.
    """
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
        try:
            b = bytes.fromhex(raw)
        except ValueError:
            continue
        if len(b) < 14:
            continue
        aid, = struct.unpack_from("<I", b, 2)
        if aid != agent:
            continue
        label = str(r.get("label") or "")
        arm = ARM_UNKNOWN
        for prefix, name in ARM_LABELS:
            if label.startswith(prefix):
                arm = name
                break
        out.append((float(r["t"]), arm))
    out.sort()
    return out


# --- the rule ----------------------------------------------------------------
def keyboard_driving(cs, t, window=SHIPPED_LOCAL_WINDOW):
    """(bool, why) -- was the client driving itself from the keyboard at `t`?

    `why` names the term that decided, so a caller can count WHICH term did the
    work rather than only the verdict. That is what makes the stop term
    auditable: on `20260820T182934` it is the sole reason one of five clicks is
    refused, and a mutation that deletes it changes a printed count.
    """
    heads = cs["heads"]
    # last heading at or before t, by binary search over a sorted list
    lo, hi = 0, len(heads)
    while lo < hi:
        mid = (lo + hi) // 2
        if heads[mid][0] <= t:
            lo = mid + 1
        else:
            hi = mid
    if lo == 0:
        return False, "no-heading-yet"
    h, mt = heads[lo - 1]
    if t - h > window:
        return False, "stale-heading"
    if not mt:
        return False, "movementType-zero"
    for s in cs["stops"]:
        if h < s <= t:
            return False, "stopped-since"
    return True, "driving"


def suppression(cs, grants, window=SHIPPED_LOCAL_WINDOW, min_interval=None,
                arms=ARM_KEYBOARD):
    """Per-grant verdicts plus the tallies, keyed by emitting arm and by reason.

    `grants` is `[(t, arm)]` from `load_grant_arms`. `arm` there is the
    `authsrv.py` SITE that emitted the grant (click / heading / client-endpoint);
    `arms` here is which arm of the RULE is switched on. Two different senses of
    one word, both already in use on either side of the wire, so both are
    spelled out at every call site rather than renamed under one of them.

    THE RATE ARM RUNS AS A STATE MACHINE. `min_interval` is measured from the
    last grant that SURVIVED, so a suppressed grant does not reset the floor. A
    pairwise filter over the logged timestamps is a different and smaller
    number, and it is the number a one-liner would produce.

    Returns a dict whose `n` is the denominator EVERY count in it is over,
    because a suppression share printed without its denominator is the defect
    this repo keeps re-finding.
    """
    rows, by_arm, by_reason = [], {}, {}
    last_sent = None
    for t, emitter in grants:
        drop, why = False, None
        # THE `why` IS ALWAYS THE TERM THAT DECIDED, on both verdicts. For a
        # suppressed grant it names the arm that stopped it; for a kept one it
        # names the term that let it through -- which is what makes "the stop
        # term keeps 10 of 40 grants" a countable claim rather than prose.
        drive, kbd_why = keyboard_driving(cs, t, window)
        if arms in (ARM_KEYBOARD, ARM_BOTH) and drive:
            drop, why = True, "driving"
        elif (arms in (ARM_RATE, ARM_BOTH) and min_interval is not None
                and last_sent is not None and t - last_sent < min_interval):
            drop, why = True, "rate-limited"
        else:
            why = kbd_why if arms in (ARM_KEYBOARD, ARM_BOTH) else "rate-ok"
            last_sent = t
        rows.append({"t": t, "arm": emitter, "suppressed": drop, "why": why})
        a = by_arm.setdefault(emitter, {"n": 0, "suppressed": 0})
        a["n"] += 1
        a["suppressed"] += int(drop)
        by_reason[why] = by_reason.get(why, 0) + 1
    n = len(rows)
    sup = sum(1 for r in rows if r["suppressed"])
    return {"n": n, "suppressed": sup, "kept": n - sup, "rows": rows,
            "by_arm": by_arm, "by_reason": by_reason, "arms": arms,
            "window": window, "min_interval": min_interval,
            "share": (sup / n) if n else float("nan")}


_CONST_LINE = ("GRANT_LOCAL_WINDOW", "GRANT_MIN_INTERVAL", "GRANT_SUPPRESS")


def read_shipped_constants(path=None):
    """The server's own rule constants, read from its SOURCE TEXT.

    NEVER imported. `authsrv.py` is the server and this is a read-only
    analyser; importing it to read three floats would put the whole server on
    this tool's dependency path for no gain. A missing name returns absent
    rather than a default, so a caller cannot mistake "the flag was reverted"
    for "the flag reads 3.0".
    """
    if path is None:
        path = os.path.join(os.path.dirname(HERE), "authsrv", "authsrv.py")
    out = {}
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                for name in _CONST_LINE:
                    if line.startswith(name + " ="):
                        out.setdefault(name, line.split("=", 1)[1].strip())
    except OSError as exc:
        return {"unreadable": str(exc)}
    return out


def click_specificity(cs, window=SHIPPED_LOCAL_WINDOW):
    """The rule scored over CLICKS rather than grants -- the control that fires.

    A capture with zero grants has nothing to suppress, so its suppression
    share is 0/0 and is not a measurement. Its CLICKS are, and they are the
    population the rule would have been asked about had the server answered
    them: `20260820T182934` has five, and the rule must call zero of them
    keyboard-driving because the player stopped before every one. That check has
    a denominator, and it can go the other way.
    """
    rows = []
    for t in cs["clicks"]:
        drive, why = keyboard_driving(cs, t, window)
        rows.append({"t": t, "driving": drive, "why": why})
    n = len(rows)
    return {"n": n, "driving": sum(1 for r in rows if r["driving"]),
            "rows": rows}


def duty_cycle(cs, window=SHIPPED_LOCAL_WINDOW, step=0.1):
    """The classifier's own POSITIVE control: what share of the span it calls driving.

    Sampled on a fixed grid over the control stream's span rather than at the
    events, because sampling at the events is sampling where the answer is known.
    On the keyboard-only capture this must be HIGH and on a click-walk it must be
    LOW; a classifier that answers the same on both is reading "a packet arrived
    recently" and not "the player's hands are on the keyboard".
    """
    ts = [h[0] for h in cs["heads"]] + cs["stops"] + cs["clicks"]
    if len(ts) < 2:
        return {"n": 0, "driving": 0, "span": 0.0, "share": float("nan")}
    lo, hi = min(ts), max(ts)
    n = int((hi - lo) / step) + 1
    drive = sum(1 for i in range(n)
                if keyboard_driving(cs, lo + step * i, window)[0])
    return {"n": n, "driving": drive, "span": hi - lo,
            "share": drive / n if n else float("nan")}


def intra_hold_gaps(cs):
    """Heading-to-heading intervals that do NOT straddle a stop.

    This is where `KEYBOARD_WINDOW` comes from, so every run can re-derive it
    from the capture in front of it instead of trusting the constant's comment.
    """
    heads, stops = cs["heads"], cs["stops"]
    out = []
    for i in range(1, len(heads)):
        a, b = heads[i - 1][0], heads[i][0]
        if any(a < s <= b for s in stops):
            continue
        out.append(b - a)
    return sorted(out)


# --- attributing a jump to a grant, and refusing to over-read it -------------
def attribute_jumps(reps, grants, jumps, lookback=JUMP_LOOKBACK):
    """Per-jump: the grants near it in TIME, and the grant nearest it in SPACE.

    Two independent attributions, because they disagree and the disagreement is
    the finding. TIME is the `lookback` window the reproduction was described
    with and it is nearly free during a click storm -- see `density_null`.
    SPACE asks whether the landing point IS a point we granted, which is what a
    matured `+0x48` arrival looks like and what the time window cannot see: the
    reproduction's fifth jump landed BIT-IDENTICALLY on a point granted 5.07 s
    earlier.

    `grants` here is `movesync.load_grants`'s `[(t, [x, y])]`.
    """
    out = []
    for j in jumps:
        t0, t1 = j["t0"], j["t"]
        inwin = [g for g in grants if t1 - lookback <= g[0] <= t1]
        prior = [g for g in grants if g[0] <= t1]
        age = (t1 - prior[-1][0]) if prior else None
        near = None
        for gt, gp in prior:
            d = math.hypot(gp[0] - j["p"][0], gp[1] - j["p"][1])
            if near is None or d < near["dist"]:
                near = {"dist": d, "t": gt, "age": t1 - gt, "point": list(gp)}
        # THE CONTROL FOR THE SPACE ARM, and it has to be a population the
        # landing could plausibly have come from rather than a straw man. The
        # client's OWN earlier reported positions are exactly that: if a landing
        # is no closer to a granted point than to somewhere it has already
        # stood, "it landed on our grant" is the map's geometry talking.
        ctrl = None
        for row in reps:
            if row[0] >= t0:
                break
            d = math.hypot(row[1][0] - j["p"][0], row[1][1] - j["p"][1])
            if ctrl is None or d < ctrl:
                ctrl = d
        out.append({"t0": t0, "t": t1, "dist": j["dist"], "dt": j["dt"],
                    "speed": j["speed"], "in_window": len(inwin),
                    "window_ts": [g[0] for g in inwin],
                    "grant_age": age, "nearest": near, "control": ctrl})
    return out


def density_null(reps, grants, lookback=JUMP_LOOKBACK):
    """The baseline "a grant inside `lookback`" has to beat, over the SAME population.

    Every interval's landing instant `t1` -- which is the population the hard
    jumps are drawn from -- is asked the same question. If the jumps' share is
    not above this, the association is grant density and the number is not
    evidence. On the reproduction it is not, and this file prints that above
    the count rather than under it.
    """
    rows = movesync.steps(reps)
    if not rows:
        return {"n": 0, "hits": 0, "share": float("nan")}
    gt = [g[0] for g in grants]
    hits = 0
    for r in rows:
        t1 = r["t"]
        if any(t1 - lookback <= x <= t1 for x in gt):
            hits += 1
    return {"n": len(rows), "hits": hits, "share": hits / len(rows)}


def rotation_control(reps, grants, jumps, lookback=JUMP_LOOKBACK,
                     rotations=ROTATIONS):
    """The same count, with the jump times moved. A survivor is an artifact.

    Rotating the JUMPS rather than the grants keeps the grant train exactly as
    it was -- density, cadence, blackouts and all -- and asks whether the times
    the jumps actually happened are special. Rotated times outside the report
    span are dropped and COUNTED, because a control whose rows quietly vanish is
    a control that judges zero rows.
    """
    if not reps or not jumps:
        return {"rows": [], "dropped": 0}
    lo, hi = reps[0][0], reps[-1][0]
    gt = [g[0] for g in grants]
    rows, dropped = [], 0
    for off in rotations:
        hits = judged = 0
        for j in jumps:
            t1 = j["t"] + off
            if not (lo <= t1 <= hi):
                dropped += 1
                continue
            judged += 1
            if any(t1 - lookback <= x <= t1 for x in gt):
                hits += 1
        rows.append({"offset": off, "judged": judged, "hits": hits})
    return {"rows": rows, "dropped": dropped}


# --- one capture, end to end -------------------------------------------------
def arm_marginals(cs, grants, window, min_interval):
    """What each arm removes ALONE, and what the pair removes together.

    THE REASON THIS EXISTS. On the reproduction the keyboard arm suppresses all
    140 grants, so the rate arm behind it removes nothing MORE -- and a report
    that only prints the pair would read as "the rate limit does nothing",
    which is false and would get it deleted. Alone it takes the same run from
    140 to 38.
    """
    return {a: suppression(cs, grants, window, min_interval, a)
            for a in (ARM_KEYBOARD, ARM_RATE, ARM_BOTH)}


def replay(path, window=SHIPPED_LOCAL_WINDOW, lookback=JUMP_LOOKBACK,
           min_interval=SHIPPED_MIN_INTERVAL):
    """Everything one capture can answer, with its refusals attached.

    Reuses `movesync` for the report stream and the verdict-bearing jump bar.
    Nothing here re-decides what a jump is.
    """
    org, why = origin.origin_of(path)
    reps, _walls, src = movesync.load_wire_reports(path)
    grants_xy = movesync.load_grants(path)
    grants_arm = load_grant_arms(path)
    cs = load_control_stream(path)
    den = movesync.denominator(reps)
    rows = movesync.steps(reps)
    hard = movesync.hard_steps(rows)
    return {
        "path": path, "origin": org, "origin_why": why,
        "source": src, "den": den, "cs": cs,
        "grants": grants_xy, "grant_arms": grants_arm,
        "hard": hard,
        "suppression": suppression(cs, grants_arm, window),
        "marginals": arm_marginals(cs, grants_arm, window, min_interval),
        "shipped": read_shipped_constants(),
        "min_interval": min_interval,
        "clicks": click_specificity(cs, window),
        "duty": duty_cycle(cs, window),
        "gaps": intra_hold_gaps(cs),
        "jumps": attribute_jumps(reps, grants_xy, hard, lookback),
        "null": density_null(reps, grants_xy, lookback),
        "rotation": rotation_control(reps, grants_xy, hard, lookback),
        "window": window, "lookback": lookback,
    }


ATTRIB_NARROW = "narrow"
ATTRIB_WIDE = "wide"
ATTRIB_TEXT = {
    ATTRIB_NARROW: ("time lookback, plus a landing within "
                    f"{LANDED_ON_GRANT_UNITS:.0f} u of a granted point"),
    ATTRIB_WIDE: ("time lookback, plus a landing STRICTLY CLOSER to a granted "
                  "point than to anywhere the client had already stood -- no "
                  "free threshold at all"),
}


def causal_set(j, attribution=ATTRIB_NARROW):
    """The grant times that could have caused one jump, under one attribution.

    TWO ATTRIBUTIONS AND THE ANSWER IS REPORTED AS THE BRACKET BETWEEN THEM,
    because picking one is picking the number. They genuinely disagree: on
    `20260819T145717` the 3,166 u jump sits 93.9 u from a point granted 18.77 s
    earlier against a 1,226 u control -- outside the narrow band, inside the
    wide one -- while its 3,405 u jump sits 49.2 u from a granted point and
    EXACTLY 49.2 u from a place the client had already stood, which is inside
    the narrow band and outside the wide one. Neither is obviously right, so
    both are printed.

    THE WIDE CONTROL IS DELIBERATELY HARSH. A resync lands the rendered copy on
    the authoritative one, which glided out of a place the client really was --
    so "nearest own report" can veto a true positive. That is the direction a
    control is supposed to err in.
    """
    causal = list(j["window_ts"])
    near, ctrl = j["nearest"], j["control"]
    if near is not None:
        if attribution == ATTRIB_NARROW:
            if near["dist"] <= LANDED_ON_GRANT_UNITS:
                causal.append(near["t"])
        elif ctrl is not None and near["dist"] < ctrl:
            causal.append(near["t"])
    return sorted(set(causal))


def removed_by_rule(rep, attribution=ATTRIB_NARROW):
    """(removed, kept, unattributed, unknown) over the hard jumps.

    A jump is PLAUSIBLY REMOVED when every grant in its causal set would have
    been suppressed. A jump with an EMPTY causal set is UNATTRIBUTED and is
    neither removed nor kept -- there is no grant for the rule to have
    suppressed, so the rule says nothing about it and this function refuses to
    imply otherwise.

    `unknown` is the fourth bucket and it exists because a lookup that MISSES
    must not answer False. `suppression` is keyed on the grant times
    `load_grant_arms` read and the causal set on the times `load_grants` read;
    both come from `r["t"]` of the same rows so they are equal today, and if a
    future loader ever breaks that, a missing key has to be loud rather than
    silently scoring the jump as "the rule keeps it". Same rule as
    `movesync.state_fields` refusing to return 0 for a field it could not read.
    """
    sup_at = {r["t"]: r["suppressed"] for r in rep["suppression"]["rows"]}
    removed, kept, unattributed, unknown = [], [], [], []
    for j in rep["jumps"]:
        causal = causal_set(j, attribution)
        if not causal:
            unattributed.append(j)
        elif any(t not in sup_at for t in causal):
            unknown.append(j)
        elif all(sup_at[t] for t in causal):
            removed.append(j)
        else:
            kept.append(j)
    return removed, kept, unattributed, unknown


# --- printing ----------------------------------------------------------------
def _p(xs, q):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))]


def print_replay(rep):
    """The whole report for one capture. Returns 0, or 1 if anything refused."""
    refusals = 0
    path, den, cs = rep["path"], rep["den"], rep["cs"]
    sup, clicks, duty = rep["suppression"], rep["clicks"], rep["duty"]
    print(f"\n=== {os.path.basename(path)}")
    print(f"    ORIGIN  {rep['origin']}  ({rep['origin_why']})")
    print(f"    RULE    {RULE_TEXT}")
    print(f"    W = {rep['window']:.2f}s   jump lookback = "
          f"{rep['lookback']:.2f}s")
    print(f"    STREAM  {rep['source']['spliced']} self-reports "
          f"({rep['source']['heading']} x 0x003D + {rep['source']['stop']} x "
          f"0x0047), {len(cs['clicks'])} x 0x003E click(s), "
          f"{sup['n']} player 0x0029 grant(s)")
    if cs["malformed"]:
        print(f"            {cs['malformed']} c2s row(s) DROPPED for a values "
              f"shape the schema does not describe -- counted, never indexed "
              f"into")
    if den["intervals"] == 0:
        print("    REFUSING EVERY VERDICT: no report interval to measure.")
        return 1
    print(f"    DENOMINATOR  {den['intervals']} interval(s) over "
          f"{den['span']:.1f}s; cadence p50 {den['p50']:.3f}s MAX "
          f"{den['max']:.3f}s")

    # --- the classifier, before anything it decides ---
    print(f"\n    THE CLASSIFIER FIRST, because a rule is only as good as the "
          f"thing it asks.")
    g = rep["gaps"]
    if g:
        over = sum(1 for x in g if x > rep["window"])
        print(f"       intra-hold heading gaps (no 0x0047 between): n = "
              f"{len(g)}, p50 {_p(g, 0.5):.3f}s, p95 {_p(g, 0.95):.3f}s, max "
              f"{g[-1]:.3f}s")
        print(f"       {over} of {len(g)} ({100.0 * over / len(g):.1f}%) exceed "
              f"W = {rep['window']:.2f}s, so the rule LEAKS a grant in that "
              f"much of this capture's keyboard-hold time")
    else:
        print(f"       LEAKAGE NOT MEASURED: this capture has no two headings "
              f"inside one hold, so it cannot price W.")
        refusals += 1
    if duty["n"]:
        print(f"       duty cycle: {duty['driving']} of {duty['n']} instants on "
              f"a 0.10s grid over {duty['span']:.1f}s = "
              f"{100.0 * duty['share']:.0f}% called DRIVING")
    else:
        print(f"       duty cycle REFUSED: fewer than two control events.")
        refusals += 1
    if cs["heads"]:
        print(f"       movementType values seen: {cs['mt_values']}; the "
              f"`!= 0` term REFUSED {cs['mt_zero']} of {len(cs['heads'])} "
              f"heading(s). 0 never appears in this corpus, so the term is "
              f"INERT -- reported as a term that has never fired, never counted "
              f"as discrimination.")

    # --- what the rule would have suppressed ---
    print(f"\n    WHAT THE RULE SUPPRESSES")
    if sup["n"] == 0:
        print(f"       REFUSED: 0 grants. A suppression share of 0/0 is not a "
              f"measurement, and 'the rule suppressed nothing here' is a "
              f"sentence about the SERVER (it answered no click), not about "
              f"the rule. The click population below is what this capture can "
              f"actually judge.")
        refusals += 1
    else:
        print(f"       {sup['suppressed']} of {sup['n']} grant(s) "
              f"({100.0 * sup['share']:.1f}%) would NOT have been sent")
        for arm in sorted(sup["by_arm"]):
            a = sup["by_arm"][arm]
            print(f"          {arm:<16} {a['suppressed']:4d} of {a['n']:4d}")
        kept_why = ", ".join(
            f"{k} x{v}" for k, v in
            sorted(sup["by_reason"].items(), key=lambda kv: -kv[1])
            if k != "driving")
        print(f"       the {sup['kept']} kept, by the term that kept them: "
              + (kept_why or "none -- every grant in this capture was sent "
                             "while the client drove itself"))
        m = rep["marginals"]
        print(f"\n       THE TWO ARMS, MARGINALLY -- because an arm measured "
              f"only behind another arm has not been measured:")
        for a in (ARM_KEYBOARD, ARM_RATE, ARM_BOTH):
            s = m[a]
            print(f"          {a:<9} suppresses {s['suppressed']:4d} of "
                  f"{s['n']:4d}, leaving {s['kept']:4d} on the wire"
                  + (f"   (floor {s['min_interval']:.2f}s)"
                     if a != ARM_KEYBOARD else
                     f"   (W {s['window']:.2f}s)"))
        sh = rep["shipped"]
        if "unreadable" in sh:
            print(f"       the server's own constants could not be read: "
                  f"{sh['unreadable']}")
        else:
            print(f"       authsrv.py declares "
                  + ", ".join(f"{k}={sh[k]}" for k in _CONST_LINE if k in sh)
                  + f"; this replay ran W={rep['window']:.2f} "
                    f"floor={rep['min_interval']:.2f}")

    print(f"\n    SPECIFICITY, over the CLICKS -- the population with a "
          f"denominator when grants have none")
    if clicks["n"] == 0:
        print(f"       REFUSED: 0 clicks. Nothing here judges the rule.")
        refusals += 1
    else:
        stopped = sum(1 for r in clicks["rows"] if r["why"] == "stopped-since")
        print(f"       {clicks['driving']} of {clicks['n']} click(s) land while "
              f"the client is keyboard-driving")
        print(f"       of the {clicks['n'] - clicks['driving']} that do not, "
              f"{stopped} are refused by the STOP term alone -- delete it and "
              f"this number moves")

    # --- the jumps ---
    print(f"\n    THE HARD JUMPS -- movesync's two arms, unchanged. n = "
          f"{len(rep['hard'])} of {den['intervals']} interval(s)")
    if not rep["hard"]:
        print(f"       nothing to attribute: no interval in this capture moved "
              f"the client further than it could have walked.")
    else:
        null = rep["null"]
        inwin = sum(1 for j in rep["jumps"] if j["in_window"] > 0)
        print(f"       {inwin} of {len(rep['jumps'])} have a grant inside "
              f"{rep['lookback']:.2f}s before the landing")
        print(f"       ...AND HERE IS THE BASELINE THAT NUMBER HAS TO BEAT: "
              f"{null['hits']} of {null['n']} of THIS CAPTURE'S OWN report "
              f"instants ({100.0 * null['share']:.0f}%) also have one. The "
              f"jumps are drawn from that population.")
        jshare = inwin / len(rep["jumps"])
        if jshare <= null["share"]:
            print(f"       VERDICT ON THE TIME ARM: {100.0 * jshare:.0f}% vs "
                  f"{100.0 * null['share']:.0f}% -- NOT above baseline. On this "
                  f"capture 'a grant inside {rep['lookback']:.2f}s' is grant "
                  f"DENSITY and is NOT evidence of causation. Read the space "
                  f"arm below instead.")
        else:
            print(f"       VERDICT ON THE TIME ARM: {100.0 * jshare:.0f}% vs "
                  f"{100.0 * null['share']:.0f}% baseline -- above it, by "
                  f"{100.0 * (jshare - null['share']):.0f} points over n = "
                  f"{len(rep['jumps'])}. A margin over five rows is a hint, "
                  f"not a result.")
        rot = rep["rotation"]
        if rot["rows"]:
            print(f"       ROTATION CONTROL (jump times moved, grant train "
                  f"untouched): "
                  + "  ".join(f"{r['offset']:+.0f}s {r['hits']}/{r['judged']}"
                              for r in rot["rows"])
                  + (f"   [{rot['dropped']} rotated row(s) fell outside the "
                     f"report span and were dropped]" if rot["dropped"] else ""))
        print(f"\n       PER JUMP -- and the SPACE arm is the one that "
              f"discriminates:")
        for j in rep["jumps"]:
            near, ctrl = j["nearest"], j["control"]
            print(f"        t={j['t']:8.3f}  {j['dist']:6.0f} u over "
                  f"{j['dt']:.3f}s  excess {j['dist'] - movesync.RUN_SPEED * j['dt']:6.0f} u")
            if near is None:
                print(f"           no player grant precedes it; this file says "
                      f"nothing about this jump")
                continue
            tag = ("LANDED ON A GRANTED POINT"
                   if near["dist"] <= LANDED_ON_GRANT_UNITS else "")
            print(f"           nearest granted point {near['dist']:8.3f} u, "
                  f"granted {near['age']:5.2f}s earlier   {tag}")
            print(f"           CONTROL, nearest place the client had already "
                  f"stood: {ctrl:8.3f} u")
            print(f"           grants inside the {rep['lookback']:.2f}s "
                  f"lookback: {j['in_window']}; last grant "
                  + (f"{j['grant_age']:.2f}s before the landing"
                     if j["grant_age"] is not None else "none"))

        print(f"\n    WHAT THE RULE WOULD HAVE DONE TO THEM -- reported as a "
              f"BRACKET across two attributions, because picking one is "
              f"picking the number")
        band = []
        n_j = len(rep["jumps"])
        for att in (ATTRIB_NARROW, ATTRIB_WIDE):
            removed, kept, unattr, unknown = removed_by_rule(rep, att)
            assert (len(removed) + len(kept) + len(unattr)
                    + len(unknown) == n_j)
            band.append(len(removed))
            print(f"       {att.upper():<7} ({ATTRIB_TEXT[att]})")
            print(f"           plausibly REMOVED {len(removed):3d} of {n_j}  "
                  f"every grant in the causal set would have been suppressed")
            print(f"           plausibly KEPT    {len(kept):3d}        at "
                  f"least one causal grant survives the rule")
            print(f"           UNATTRIBUTED      {len(unattr):3d}        no "
                  f"grant in the causal set at all -- the rule says NOTHING "
                  f"about these and they are NOT counted as removed")
            if unknown:
                print(f"           UNKNOWN           {len(unknown):3d}        a "
                      f"causal grant time is missing from the suppression "
                      f"table; a miss is refused, never scored as `kept`")
        lo, hi = min(band), max(band)
        print(f"       BRACKET: the rule plausibly removes "
              + (f"{lo}" if lo == hi else f"{lo}-{hi}")
              + f" of {n_j} hard jump(s) in this capture.")
        # THE CAVEAT THAT HAS TO SIT UNDER THE 100% AND NOT IN A FOOTNOTE.
        # Where the rule suppresses EVERY grant, "every grant in the causal set
        # would have been suppressed" is true of any causal set that is not
        # empty -- so the per-jump counterfactual has no way to come out
        # differently and is not, on this capture, a test of anything. The
        # capture where the rule keeps grants is the one where the number means
        # something, which is why the corpus is six and not one.
        if sup["n"] and sup["kept"] == 0:
            print(f"       ...AND THAT NUMBER CANNOT COME OUT ANY OTHER WAY "
                  f"HERE. The rule suppresses ALL {sup['n']} of this capture's "
                  f"grants, so every non-empty causal set is covered by "
                  f"construction and the per-jump counterfactual tests nothing "
                  f"on this file. The captures where grants SURVIVE the rule "
                  f"are the ones where this number is a measurement.")
        if lo < n_j:
            print(f"       ...AND THE REMAINDER IS THE HONEST HALF. A fix that "
                  f"removes {lo} of {n_j} is a fix; one reported as removing "
                  f"all {n_j} is a lie the next run exposes.")
    return 1 if refusals else 0


def print_sweep(rep_path, lookback=JUMP_LOOKBACK):
    """The window priced across `WINDOW_SWEEP`. No answer may exist at one W."""
    print(f"\n=== SWEEP  {os.path.basename(rep_path)}")
    print(f"    {'W':>6}  {'suppressed':>16}  {'clicks driving':>16}  "
          f"{'duty':>6}  {'intra-hold leak':>16}")
    for w in WINDOW_SWEEP:
        rep = replay(rep_path, window=w, lookback=lookback)
        s, c, d, g = (rep["suppression"], rep["clicks"], rep["duty"],
                      rep["gaps"])
        leak = (f"{sum(1 for x in g if x > w)}/{len(g)}" if g else "n/a")
        print(f"    {w:6.2f}  {s['suppressed']:7d} of {s['n']:<6d}  "
              f"{c['driving']:7d} of {c['n']:<6d}  "
              f"{100.0 * d['share']:5.0f}%  {leak:>16}")


# --- the capture set ---------------------------------------------------------
# TONIGHT'S THREE, named by stamp rather than by "the newest": two of them are
# the controls and `sorted(...)[-1]` has picked the wrong file in this repo
# three times, in three different files.
REPRO = "20260820T183311"
CONTROL_CLICK = "20260820T182934"
CONTROL_KBD = "20260820T182554"
# The older warp corpus, captured under different play. Agreement across both
# nights is worth more than either alone; these are `ours` and are the three
# configurations the arc has measured.
OLDER = ("20260819T145717", "20260819T171153", "20260819T182652")
ARC_STAMPS = (REPRO, CONTROL_CLICK, CONTROL_KBD) + OLDER


def capture_path(stamp):
    """The one gamesrv capture for a stamp, or a refusal naming what is missing."""
    d = vaultpath.vault_path("captures", "gamesrv")
    hits = sorted(glob.glob(os.path.join(d, f"*{stamp}*.jsonl")))
    if not hits:
        raise Refused(f"no capture for {stamp} under {d}. No capture, no "
                      f"number -- this tool will not model one.")
    if len(hits) > 1:
        raise Refused(f"{len(hits)} captures match {stamp}: "
                      f"{[os.path.basename(h) for h in hits]}. Refusing to "
                      f"pick one by sort order.")
    return hits[0]


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--capture", help="one gamesrv capture to replay")
    ap.add_argument("--all", action="store_true",
                    help="the arc's six: tonight's reproduction, tonight's two "
                         "controls, and the three older warp captures")
    ap.add_argument("--sweep", action="store_true",
                    help="price W across WINDOW_SWEEP on the reproduction")
    ap.add_argument("--window", type=float, default=SHIPPED_LOCAL_WINDOW)
    ap.add_argument("--min-interval", type=float, default=SHIPPED_MIN_INTERVAL,
                    help="rule 2's floor between two grants on the wire")
    ap.add_argument("--lookback", type=float, default=JUMP_LOOKBACK)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        import test_grantsuppress
        return test_grantsuppress.main()

    if a.capture:
        paths = [a.capture]
    elif a.all or a.sweep:
        paths = [capture_path(s) for s in ARC_STAMPS]
    else:
        ap.print_help()
        return 2

    if a.sweep:
        print_sweep(paths[0], a.lookback)
        return 0

    # ORIGIN IS CHECKED BEFORE ANYTHING IS POOLED. A consumer that mixes ours
    # with live is comparing a defect against a control by accident.
    origins = {}
    for p in paths:
        origins[p] = origin.origin_of(p)[0]
    kinds = set(origins.values())
    if len(kinds) > 1:
        print(f"REFUSING: these captures do not share an origin ({sorted(kinds)}). "
              f"Nothing below would be comparable.")
        return 2
    print(f"RULE UNDER TEST: {RULE_TEXT}")
    print(f"corpus: {len(paths)} capture(s), origin = {sorted(kinds)[0]}")
    bad = 0
    for p in paths:
        bad += print_replay(replay(p, a.window, a.lookback, a.min_interval))
    print(f"\n{len(paths)} capture(s) replayed; "
          f"{bad} printed at least one refusal.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
