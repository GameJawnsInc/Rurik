r"""Party-wide shouts on retail's wire: every shout apply, attributed to its caster.

    python toolkit/authsrv/shoutjoin.py            # every live capture
    python toolkit/authsrv/shoutjoin.py --rows     # one line per apply and per reach pair
    python toolkit/authsrv/shoutjoin.py --json

WHY THIS EXISTS. `content/world.toml`'s row for "Charge!" (364) said "Earshot is not
modelled: the shout lands on the caster alone (the loopback party is the player)", and
DESKWORK-D5 step 5 (studies/deskwork/PLAN.md) surveyed the corpus by hand: every type-15
(Shout) 0x0042 on an observer is skill 364, all on `20260817T231139`, 42 applied by the
observer's own cast and 23 by ANOTHER caster's. This reader re-derives that from the
bytes and adds what the survey did not measure: for every shout announce and every agent
whose effect list is on the wire (the observer, a hero), whether an apply followed and how
far apart caster and wearer stood -- the REACH table -- and the speed words the apply's
batch carries for OTHER party members, which is the wire's own statement that the shout
landed on them too.

THE OBSERVER (fix pass, 2026-09-23). The first cut took the agent of the connection's
FIRST `0x00E3` as the observer -- `spellhitjoin.player_of`'s rule -- and on the one tape
with a hero (`20260914T005758`, conn 56011) that ack belongs to the HERO: agent 30 (class
tag 2, definition 0x11ab) gets 48 of the 54 acks because it casts 346 and 348 all
session, while agent 29 (the only class-tag-3 create, the agent of the first property 41,
the agent whose acks answer the c2s presses of 392 / 394 / 433 / 446 / 455) never presses
a shout. Every "6 applies on a hero" in the first record was the HERO's own Watch
Yourself! landing on the PLAYER. The observer is now `adrenjoin.whose_agent`'s rule
(property 41, self-scoped, with the JARIN kind-5 tie-break for a hero tape) CROSS-CHECKED
against the agent whose `0x00E3` / `0x00E2` answers the connection's own c2s skill
presses; a connection where the two disagree is REFUSED and counted, not scored.

THE ATTRIBUTION RULE. `0x0042 [target, skill, field3, buff, f32]` has NO source field
(bufflog), so a shout's caster is read off the cast announcement -- the LAST announce of
the same skill inside ANNOUNCE_WINDOW before the apply. An apply with no announce in the
window is UNATTRIBUTED and counted, never assigned to the nearest.

WHICH ANNOUNCE. The first cut of this reader (2026-09-23) looked for the spell's `0x009F
[60, caster, skill]` (cast_anim_msg) and found ZERO for any Shout id in 96 connections --
every apply came out unattributed. The batch context (scratch, the same day) shows what a
shout rides instead: `0x009F [48, caster, skill]` in the apply's own batch, beside a
`0x009F [21, caster, 622]` and an `0x00A5 [caster, text]` (the speech bubble), and for
the observer's own shout E4 / E5 / E3 with no E4-to-E5 gap (activation 0). Property 48
(`agents.GV_INSTANT_SKILL_ACTIVATED`, named there; sent by this server nowhere until
2026-09-25, when `authsrv.instant_open` took it up -- instantjoin.py, skills 56.9) is the
INSTANT skill's announce, not the shout's alone: the corpus census by skill type is
printed (364 and 348 are Shouts; 346, 10, 379, 349, 455 are Stances; 1217 is type 16).
The prop-60 form is kept as a counted control and expected at zero for a Shout id.

POSITIONS are the corpus's own samples, and NONE of them is the agent's position at the
apply. EXACT samples: an agent's create (0x0020 field 5) at creation, 0x002C
AGENT_UPDATE_POSITION (rare), and the observer's own c2s move requests (0x003D / 0x0047
field 1), which are ITS position at the request. LEAD samples: a 0x0029
AGENT_MOVE_TO_POINT (field 2) and a 0x002A destination are points AHEAD of the agent on
its path (movecode) -- the only samples the wire holds for any agent but the observer.
The first cut mixed the observer's own 0x0029 leads in with its c2s reports and took the
latest: on `20260817T231139` conn 50513 at t = 476.998 that was a lead 765 u from the c2s
report 35 ms earlier, and the pair it produced (912.7 u, "the largest resolved apply") is
188 u from the report. THE OBSERVER IS NOW POSITIONED FROM ITS EXACT SAMPLES ONLY.
A distance is the straight line between the two agents' samples INTERPOLATED in time
between the sample before and the sample after the event when both exist (`dist`), else
held from the last sample; every row carries the sample ages and source opcodes.

THE LEAD CHECK (fix pass). The first cut allowed a lead point 300 u ahead of its agent
(FIRST_CUT_LEAD_ALLOWANCE) and called a distance resting on leads a bound. The tape can
measure that allowance in one place: the OBSERVER, whose exact c2s report and whose own
0x0029 / 0x002A land inside LEAD_CHECK_S of each other 6,639 times in the corpus. The
offset between them is a MEDIAN 765 u and a maximum 4,264 u; 5,238 of the 6,639 exceed
300. So a lead is not a position with an allowance -- it is a point on the path ahead,
typically three quarters of the radius away -- and a pair resting on one (`on_lead`) is
a POINT ESTIMATE with no bound: it never resolves, it bounds nothing, and it is printed
as what it is. Every reach pair in this corpus rests on a lead (the only agent with exact
samples is the observer; the other agent of every pair has leads alone), so the DISTANCE
half of P4 is UNTESTABLE here and the reader says so rather than scoring it.

For EXACT samples the STATED ERROR is a bound, not a fit: MAX_SPEED x the hold age when
not interpolated, or 2 x MAX_SPEED x the nearer sample age when interpolated (an agent
moving at most MAX_SPEED between two exact samples lies within twice that of the chord
point -- a theorem, no free parameter). A FOLLOW LEAD -- a party body's 0x0029 whose
point IS the observer's own position (the follow parks on the model) -- is the special
case of a lead that says the body was walking TO the observer. An exact pair is RESOLVED
only when its verdict stands outside its stated error on EITHER side -- |d - EARSHOT| >
err -- the same rule for a pair that agrees with the radius and one that crosses it (the
first cut resolved every agreeing pair whatever its error, which is how 912.7 +/- 882.8 u
became "a bound"). What an exact pair CAN say about the radius is d - err when it applied
(a lower bound) and d + err when it did not (an upper bound); the extremes are printed.

ALLEGIANCE is the create's token (0x0020 field 12). SIDES are read from the tokens
alone, never from the outcome under test (the first cut defined a foe token as one whose
casters never produced an apply on the observer, which makes "0 foe applies" nearly true
by construction): the same token is an ALLY; `agents.ALLEGIANCE_NONCOMBATANT` ('nonc',
0x6E6F6E63) is its own class -- the arena's one non-team agent per connection, boosted by
the team's shouts every time; any other token is a FOE. The arena's team tokens are 'att1'
/ 'att2'; the owner's PvE tapes carry 'play' for the party.

THE PREDICTIONS, stated before the scan (the survey's counts are the priors; a reader
that disagrees refutes the survey, not the tape):

  P1  every Shout-type apply on the observer in the live corpus is skill 364 on
      `20260817T231139`: 65 applies, 42 attributed to the observer, 23 to another
      caster. (First run, 2026-09-23: FAILED as registered -- 348 is in the set and
      the applies sit on ten captures. Fix pass, the same day, with the observer
      corrected: 65 = 42 + 23 REPRODUCES only as caster == wearer (42) versus caster
      != wearer (23); the OBSERVER cast 35 of them, not 42 -- 58 applies sit on the
      observer and 7 on a hero, all 7 the hero's own casts. Printed beside P1 and
      pinned in test_shouts.py.)
  P2  every apply has an announce of its skill inside ANNOUNCE_WINDOW (1.5 s).
  P3  every foreign apply on the observer comes from a caster carrying the OBSERVER's
      allegiance token (a shout reaches allies, never foes).
  P4  REACH: over every (announce, wearer) pair of ALLIES, the pairs that APPLIED sit
      within EARSHOT = 1000 u -- the client's own record for 364 (+0x6C `aoe_range`,
      skilltable.py, = 1000.0) and WIKI's earshot radius (GWW "Area of effect") agree on
      the number -- and the pairs that did NOT apply sit beyond it; a FOE pair never
      applies at any distance. Judged on the interpolated distance where one exists,
      with the hold distance printed beside it; a pair that violates the radius by less
      than its own stated error, or that rests on a follow lead, is UNRESOLVED, not a
      refutation, and the unresolved count is printed.
  P5  a shout apply on a HERO body (JARIN: a hero's effect list is on the wire) is
      attributed the same way.
  P6  the batch of a 364 apply carries 0x0027 speed words for party members OTHER than
      the wearer (the shout's +33 % re-declared on every ally it reached -- F48's P5
      rule seen from the party side); every such agent carries the caster's allegiance.

Standard library only; reads the vault through `vaultpath`; a connection whose byte
accounting does not close, or whose observer the two rules do not agree on, is refused
and counted, never scored.
"""
import argparse
import bisect
import collections
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import adrenjoin        # noqa: E402  (whose_agent: the observer rule)
import livewire         # noqa: E402
import tape             # noqa: E402
import vaultpath        # noqa: E402

OP_CREATE = 0x0020         # [agent, model, type, kind, (x, y), plane, ..., allegiance @12]
OP_SPEED = 0x0027          # [agent, f32 u/s] -- AGENT_UPDATE_SPEED_BASE (speedwords.py)
OP_LEAD = 0x0029           # [agent, (x, y), ...] -- AGENT_MOVE_TO_POINT, a point ahead
OP_DEST = 0x002A           # [agent, (x, y), ...] -- AGENT_UPDATE_DESTINATION
OP_POSITION = 0x002C       # [agent, (x, y), ...] -- AGENT_UPDATE_POSITION, exact
OP_APPLY = 0x0042          # [target, skill, field3, buff, f32 duration]
OP_INT = 0x009F            # [prop, agent, value]
OP_INT_TARGET = 0x00A0     # [prop, a, b, value]
OP_SKILL_RELEASED = 0x00E2
OP_SKILL_ACTIVATED = 0x00E3
OP_CMSG_MOVE = (0x003D, 0x0047)   # c2s: the observer's own position requests
OP_CMSG_PRESS = (0x0027, 0x0046)  # c2s: attack-skill and cast presses (adrenreplay)
PRESS_ANSWER_S = 0.3       # s; the observer's E3/E2 answering its own press
PROP_SHOUT_ANNOUNCE = 48   # [48, caster, skill] -- the INSTANT skill's announce (OBSERVED)
PROP_SKILL_ACTIVATED = 60  # the spell's announce; a counted control here, expected 0
SHOUT_TYPE = 15
ANNOUNCE_WINDOW = 1.5      # s; the survey's window
BATCH_S = 0.060            # s; the corpus's batch shoulder (speedwords.py)
EARSHOT = 1000.0           # u; the client's aoe_range for 364 and WIKI's earshot
MAX_SPEED = 400.0          # u/s; the fastest speed word in the corpus is 399 (x1.33 on 300)
FIRST_CUT_LEAD_ALLOWANCE = 300.0   # u; what the first cut allowed a lead point -- REFUTED by
#                                    the lead check (median offset 765 u); printed, not used
FOLLOW_EPS = 5.0           # u; a lead this close to the other agent's sample is a follow lead
LEAD_CHECK_S = 0.1         # s; an observer lead this close to a c2s report is checked against it
BOOST = 1.33               # the shout's speed factor (F48 P1)
TOKEN_NONCOMBATANT = 0x6E6F6E63   # 'nonc' -- agents.ALLEGIANCE_NONCOMBATANT, the client's own
# The survey's priors, carried as predictions so the acceptance can redden.
EXPECT_SKILL = 364
EXPECT_CAPTURE = "20260817T231139"
EXPECT_APPLIES = 65
EXPECT_SELF = 42
EXPECT_OTHER = 23


def skill_types():
    """{skill_id: type_code} from the loaded content (the skills table)."""
    import content  # noqa: E402  (repo-local; the skills table is content)
    world = content.load()
    out = {}
    for key, row in world.rows("skills").items():
        try:
            out[int(key)] = int(row.get("type_code", -1))
        except (TypeError, ValueError):
            continue
    return out


def shout_skills(types=None):
    """{skill_id} whose client type is Shout (15)."""
    types = types if types is not None else skill_types()
    return {sid for sid, tc in types.items() if tc == SHOUT_TYPE}


def _xy(v):
    return (float(v[0]), float(v[1])) if isinstance(v, (tuple, list)) and len(v) >= 2 else None


def _f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def observer_of(merged):
    """(observer, press_agent, why): the connection's own agent by two rules.

    `adrenjoin.whose_agent` -- property 41, self-scoped, with the JARIN kind-5
    create tie-break for a hero tape -- and the agent whose `0x00E3` / `0x00E2`
    answers the connection's own c2s skill presses inside PRESS_ANSWER_S (a
    landslide vote, or None where nothing was pressed). Both, when both answer,
    must agree; the reason is returned when they do not or neither answers.
    """
    s2c = [(t, op, v) for t, d, op, v in merged if d == "s2c"]
    by_41 = adrenjoin.whose_agent(s2c)
    votes = collections.Counter()
    answers = [(t, int(v[1])) for t, op, v in s2c
               if op in (OP_SKILL_ACTIVATED, OP_SKILL_RELEASED) and len(v) > 1]
    times = [t for t, _a in answers]
    for t, d, op, v in merged:
        if d != "c2s" or op not in OP_CMSG_PRESS:
            continue
        i = bisect.bisect_left(times, t)
        if i < len(answers) and answers[i][0] - t <= PRESS_ANSWER_S:
            votes[answers[i][1]] += 1
    by_press = votes.most_common(1)[0][0] if votes else None
    if by_41 is None and by_press is None:
        return None, None, "no observer: no property 41 and no answered press"
    if by_41 is not None and by_press is not None and by_41 != by_press:
        return None, by_press, (f"observer rules disagree: property 41 says {by_41}, "
                                f"the answered presses say {by_press} ({dict(votes)})")
    return (by_41 if by_41 is not None else by_press), by_press, None


class Samples:
    """Per-agent position samples, (t, xy, op), in time order."""

    def __init__(self):
        self.by_agent = collections.defaultdict(list)
        self.times = collections.defaultdict(list)

    def add(self, agent, t, xy, op):
        self.by_agent[agent].append((t, xy, op))
        self.times[agent].append(t)

    def at(self, agent, t):
        """(xy_interpolated_or_None, xy_hold_or_None, age_before, age_after, ops, hold_op)."""
        rows = self.by_agent.get(agent)
        if not rows:
            return None, None, None, None, (), None
        i = bisect.bisect_right(self.times[agent], t)
        before = rows[i - 1] if i > 0 else None
        after = rows[i] if i < len(rows) else None
        hold = before[1] if before else None
        age_b = round(t - before[0], 3) if before else None
        age_a = round(after[0] - t, 3) if after else None
        ops = tuple(o for o in ((before[2] if before else None), (after[2] if after else None)) if o)
        if before and after and after[0] > before[0]:
            f = (t - before[0]) / (after[0] - before[0])
            xy = (before[1][0] + f * (after[1][0] - before[1][0]),
                  before[1][1] + f * (after[1][1] - before[1][1]))
            return xy, hold, age_b, age_a, ops, before[2]
        return None, hold, age_b, age_a, ops, (before[2] if before else None)


def _pair(samples, a, b, t):
    """Distance fields for agents a and b at time t."""
    xa, ha, ab, aa, oa, hoa = samples.at(a, t)
    xb, hb, bb, ba, ob, hob = samples.at(b, t)
    d_hold = (round(math.hypot(ha[0] - hb[0], ha[1] - hb[1]), 1)
              if ha is not None and hb is not None else None)
    pa, pb = (xa if xa is not None else ha), (xb if xb is not None else hb)
    d = (round(math.hypot(pa[0] - pb[0], pa[1] - pb[1]), 1)
         if pa is not None and pb is not None else None)
    interpolated = xa is not None and xb is not None
    # ON A LEAD: either agent's sample is a 0x0029 / 0x002A point. The lead check
    # (rows_of, printed by main) measures such a point at a median 765 u from the
    # agent's exact position, so a distance resting on one is a POINT ESTIMATE
    # with no bound, and the row never resolves. The first cut allowed 300 u for
    # a lead; the measurement refutes that as a bound.
    on_lead = any(o in (OP_LEAD, OP_DEST) for o in oa + ob)
    # The stated error for EXACT samples (a bound, see the docstring): speed x
    # the hold age when not interpolated; twice speed x the nearer age when
    # interpolated. Meaningless when on_lead, and printed so.
    err = 0.0
    for age_b, age_a, interp in ((ab, aa, xa is not None), (bb, ba, xb is not None)):
        if interp:
            err += 2.0 * MAX_SPEED * min(age_b, age_a)
        elif age_b is not None:
            err += MAX_SPEED * age_b
    # A follow lead: one agent's held sample is a lead/destination sitting ON the
    # other agent's held sample -- the body was walking TO the other agent, and
    # its own position is not on the wire.
    follow = (d_hold is not None and d_hold <= FOLLOW_EPS
              and (hoa in (OP_LEAD, OP_DEST) or hob in (OP_LEAD, OP_DEST)))
    return {"dist": d, "dist_hold": d_hold, "interpolated": interpolated,
            "age": (ab, bb), "age_after": (aa, ba),
            "src": (tuple(hex(o) for o in oa), tuple(hex(o) for o in ob)),
            "err": round(err, 1), "on_lead": on_lead, "follow_lead": follow}


def rows_of(merged, shouts):
    """(applies, reach, observer, prop60_control, refused_reason).

    An APPLY row: {"t", "skill", "wearer", "on_observer", "buff", "duration",
    "caster", "self" (caster is the wearer), "announce_dt", "announce_t", "ally",
    "batch_speed" ([(agent, u/s, side)] of the batch's 0x0027 words on agents other
    than the wearer; side True = the caster's token, False = a foe token, "nonc" =
    the noncombatant token, None = no create seen), + _pair fields}.
    A REACH row, one per (announce, candidate wearer) with wearer != caster, the
    candidates being the observer and every other agent that ever wore a shout in
    this connection (a hero): {"t", "skill", "caster", "wearer", "on_observer",
    "applied" (an apply attributed to THIS announce landed on that wearer), "ally",
    + _pair fields, "resolved" (|dist - EARSHOT| > err and no follow lead),
    "low" (dist - err, an applied pair's lower bound on the radius), "high"
    (dist + err, an unapplied pair's upper bound)}.
    """
    observer, _press_agent, why = observer_of(merged)
    if observer is None:
        return [], [], None, 0, why, []
    samples, alleg = Samples(), {}
    announces, raw_applies, speeds = [], [], []   # speeds: (t, agent, u/s)
    reports, own_leads = [], []                   # the observer's exact reports; its leads
    prop60 = 0
    for t, d, op, v in merged:
        if d == "c2s":
            if op in OP_CMSG_MOVE and len(v) > 1 and _xy(v[1]):
                samples.add(observer, t, _xy(v[1]), op)
                reports.append((t, _xy(v[1])))
            continue
        if op == OP_CREATE and len(v) > 12:
            if _xy(v[5]):
                samples.add(int(v[1]), t, _xy(v[5]), op)
            alleg[int(v[1])] = int(v[12])
        elif op in (OP_LEAD, OP_DEST) and len(v) > 2 and _xy(v[2]):
            # The observer's own leads are NOT its position (the docstring); its
            # exact samples are its c2s reports, its create and any 0x002C. Its
            # leads are kept apart, to be measured against the reports below.
            if int(v[1]) != observer:
                samples.add(int(v[1]), t, _xy(v[2]), op)
            else:
                own_leads.append((t, _xy(v[2])))
        elif op == OP_POSITION and len(v) > 2 and _xy(v[2]):
            samples.add(int(v[1]), t, _xy(v[2]), op)
        elif op == OP_SPEED and len(v) > 2:
            speeds.append((t, int(v[1]), float(v[2])))
        elif op == OP_INT and len(v) > 3 and int(v[3]) in shouts \
                and int(v[1]) in (PROP_SHOUT_ANNOUNCE, PROP_SKILL_ACTIVATED):
            if int(v[1]) == PROP_SKILL_ACTIVATED:
                prop60 += 1
            announces.append((t, int(v[2]), int(v[3])))
        elif op == OP_INT_TARGET and len(v) > 4 and int(v[4]) in shouts \
                and int(v[1]) == PROP_SKILL_ACTIVATED:
            prop60 += 1
            announces.append((t, int(v[2]), int(v[4])))
        elif op == OP_APPLY and len(v) > 5 and int(v[2]) in shouts:
            raw_applies.append((t, int(v[1]), int(v[2]), int(v[4]), _f32(int(v[5]))))

    # SIDES, from the tokens alone (never from the outcome under test): the same
    # token is an ally, the noncombatant token is its own class, any other token
    # is a foe.
    def side(a, b):
        if a not in alleg or b not in alleg:
            return None
        if alleg[a] == alleg[b]:
            return True
        if TOKEN_NONCOMBATANT in (alleg[a], alleg[b]):
            return "nonc"
        return False

    applies = []
    for t, wearer, skill, buff, dur in raw_applies:
        prior = [a for a in announces if a[2] == skill and 0.0 <= t - a[0] <= ANNOUNCE_WINDOW]
        caster = prior[-1][1] if prior else None
        row = {"t": round(t, 6), "skill": skill, "wearer": wearer,
               "on_observer": wearer == observer, "buff": buff, "duration": round(dur, 3),
               "caster": caster, "self": (caster == wearer) if caster is not None else None,
               "announce_dt": round(t - prior[-1][0], 6) if prior else None,
               "announce_t": prior[-1][0] if prior else None,
               "ally": side(caster, wearer) if caster is not None else None,
               "batch_speed": sorted({(ag, round(sp, 2), side(caster, ag) if caster is not None else None)
                                      for ts, ag, sp in speeds
                                      if abs(ts - t) <= BATCH_S and ag != wearer},
                                     key=lambda r: (r[0], r[1], str(r[2])))}
        row.update(_pair(samples, caster, wearer, t) if caster is not None
                   else {"dist": None, "dist_hold": None, "interpolated": False,
                         "age": None, "age_after": None, "src": None, "err": None,
                         "on_lead": False, "follow_lead": False})
        applies.append(row)
    wearers = {w for _t, w, _s, _b, _d in raw_applies}
    candidates = sorted(wearers | {observer})
    reach = []
    for t, caster, skill in announces:
        for wearer in candidates:
            if wearer == caster:
                continue
            # Credited by the attribution rule, never by proximity in time alone:
            # the apply's OWN caster (its last announce) must be this announce.
            # (First cut: "any apply of the skill on the wearer inside the window"
            # credited a foe's shout 1.46 s ahead of the observer's own cast.)
            applied = any(r["wearer"] == wearer and r["skill"] == skill
                          and r["caster"] == caster and r["announce_t"] == t
                          for r in applies)
            row = {"t": round(t, 6), "skill": skill, "caster": caster, "wearer": wearer,
                   "on_observer": wearer == observer, "applied": applied,
                   "ally": side(caster, wearer)}
            row.update(_pair(samples, caster, wearer, t))
            d, err = row["dist"], row["err"]
            # A pair resolves only on EXACT samples for both agents (a lead is a
            # point ahead, not a position) and only when its verdict stands
            # outside its stated error on either side of the radius.
            exact = d is not None and not row["on_lead"] and not row["follow_lead"]
            row["exact"] = exact
            row["resolved"] = exact and abs(d - EARSHOT) > err
            row["low"] = round(d - err, 1) if exact and applied else None
            row["high"] = round(d + err, 1) if exact and not applied else None
            reach.append(row)
    # THE LEAD CHECK: the one place the tape holds an exact position and a lead
    # for the same agent at the same moment is the observer -- its c2s report
    # and its own 0x0029 / 0x002A inside LEAD_CHECK_S. The offsets say what a
    # lead sample is worth as a position, and whether LEAD_ERROR is a bound.
    lead_offsets = []
    rt = [t for t, _xy_ in reports]
    for t, xy in own_leads:
        i = bisect.bisect_left(rt, t)
        near = [reports[j] for j in (i - 1, i) if 0 <= j < len(reports)
                and abs(reports[j][0] - t) <= LEAD_CHECK_S]
        if near:
            rtime, rxy = min(near, key=lambda r: abs(r[0] - t))
            lead_offsets.append((round(math.hypot(xy[0] - rxy[0], xy[1] - rxy[1]), 1),
                                 round(t - rtime, 3)))
    return applies, reach, observer, prop60, None, lead_offsets


def census(cutoff=None):
    """Every live capture stamped at or before `cutoff` (all when None), every game
    connection that decodes whole and names one observer."""
    types = skill_types()
    shouts = shout_skills(types)
    live = vaultpath.require_dir("captures", "live",
                                 why="shoutjoin reads live captures")
    out = {"applies": [], "reach": [], "connections": 0, "refused": [],
           "shout_skills": sorted(shouts), "announces_by_skill": collections.Counter(),
           "prop48_by_type": collections.Counter(), "prop60_control": 0,
           "observers": {}, "cutoff": cutoff, "lead_offsets": []}
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir) or (cutoff is not None and stamp > cutoff):
            continue
        for ch in tape.channel_files(cap_dir):
            try:
                _conn, merged, ok = livewire.decode_conn(cap_dir, ch["file"])
            except Exception as exc:                            # noqa: BLE001
                out["refused"].append((stamp, ch["connection"], str(exc)[:80]))
                continue
            if not ok:
                out["refused"].append((stamp, ch["connection"], "byte accounting open"))
                continue
            applies, reach, observer, prop60, why, offsets = rows_of(merged, shouts)
            if observer is None:
                out["refused"].append((stamp, ch["connection"], why))
                continue
            out["connections"] += 1
            port = ch["connection"].split("->")[0].rsplit(":", 1)[-1]
            out["observers"][f"{stamp}/{port}"] = observer
            out["lead_offsets"].extend(offsets)
            for _t, d, op, v in merged:
                if d == "s2c" and op == OP_INT and len(v) > 3 \
                        and int(v[1]) == PROP_SHOUT_ANNOUNCE:
                    out["prop48_by_type"][types.get(int(v[3]))] += 1
                    if int(v[3]) in shouts:
                        out["announces_by_skill"][int(v[3])] += 1
            out["prop60_control"] += prop60
            for r in applies + reach:
                r.update(capture=stamp, connection=ch["connection"], port=port,
                         observer=observer)
            out["applies"].extend(applies)
            out["reach"].extend(reach)
    out["announces_by_skill"] = dict(out["announces_by_skill"])
    out["prop48_by_type"] = {str(k): n for k, n in out["prop48_by_type"].items()}
    return out


def score(c):
    """The numbers P1-P6 are judged on."""
    ap = c["applies"]
    on_obs = [r for r in ap if r["on_observer"]]
    on_hero = [r for r in ap if not r["on_observer"]]
    self_all = [r for r in ap if r["self"] is True]
    other_all = [r for r in ap if r["self"] is False]
    obs_own = [r for r in on_obs if r["self"] is True]
    obs_other = [r for r in on_obs if r["self"] is False]
    hero_own = [r for r in on_hero if r["self"] is True]
    hero_wearers = {r["wearer"] for r in on_hero}
    hero_to_obs = [r for r in obs_other if r["caster"] in hero_wearers]
    obs_to_hero = [r for r in on_hero if r["self"] is False and r["caster"] == r["observer"]]
    unattributed = [r for r in ap if r["caster"] is None]
    by_skill_obs = collections.Counter(r["skill"] for r in on_obs)
    by_skill_hero = collections.Counter(r["skill"] for r in on_hero)
    by_capture = collections.Counter(r["capture"] for r in on_obs)
    reach = c["reach"]
    ally = [r for r in reach if r["ally"] is True]
    foe = [r for r in reach if r["ally"] is False]
    ally_yes = [r for r in ally if r["applied"] and r["dist"] is not None]
    ally_no = [r for r in ally if not r["applied"] and r["dist"] is not None]
    yes_in = [r for r in ally_yes if r["dist"] <= EARSHOT]
    no_out = [r for r in ally_no if r["dist"] > EARSHOT]
    yes_over = [r for r in ally_yes if r["dist"] > EARSHOT]
    no_under = [r for r in ally_no if r["dist"] <= EARSHOT]
    unresolved = [r for r in yes_over + no_under if not r["resolved"]]
    refuting = [r for r in yes_over + no_under if r["resolved"]]
    exact_pairs = [r for r in ally + foe if r["exact"]]
    lows = [r["low"] for r in ally_yes if r["low"] is not None and r["low"] > 0]
    highs = [r["high"] for r in ally_no if r["high"] is not None]
    foe_near = [r for r in foe if r["dist"] is not None and r["dist"] <= EARSHOT]
    foe_inside_resolved = [r for r in foe_near if r["exact"] and r["dist"] + r["err"] <= EARSHOT]
    # P6: the boost words on OTHER agents in a 364 apply's batch (the observer's).
    boost_rows = []
    for r in on_obs:
        if r["skill"] != EXPECT_SKILL:
            continue
        for ag, sp, al in r["batch_speed"]:
            if any(abs(sp - base * BOOST) < 0.5 for base in (288.0, 300.0)):
                boost_rows.append((r["capture"], r["port"], r["t"], ag, sp, al))
    offs = sorted(o for o, _dt in c.get("lead_offsets", ()))
    return {
        "connections": c["connections"], "refused": len(c["refused"]),
        "refused_reasons": [why for _s, _c, why in c["refused"]],
        "shout_skills_in_table": len(c["shout_skills"]),
        # The observer's own leads against its c2s reports inside LEAD_CHECK_S.
        "lead_offsets_n": len(offs),
        "lead_offset_median": offs[len(offs) // 2] if offs else None,
        "lead_offset_max": offs[-1] if offs else None,
        "lead_offsets_over_first_cut": sum(1 for o in offs if o > FIRST_CUT_LEAD_ALLOWANCE),
        "announces_by_skill": c["announces_by_skill"],
        "prop48_by_type": c["prop48_by_type"],
        "prop60_control": c["prop60_control"],
        "applies": len(ap), "on_observer": len(on_obs), "on_hero": len(on_hero),
        "on_observer_by_skill": dict(by_skill_obs),
        "on_hero_by_skill": dict(by_skill_hero),
        "on_observer_by_capture": dict(sorted(by_capture.items())),
        # caster == wearer over EVERY apply, and the same split by wearer.
        "self": len(self_all), "other": len(other_all),
        "observer_own": len(obs_own), "observer_other": len(obs_other),
        "hero_own": len(hero_own), "hero_to_observer": len(hero_to_obs),
        "observer_to_hero": len(obs_to_hero),
        "unattributed": len(unattributed),
        "p1": (len(on_obs) == EXPECT_APPLIES and len(obs_own) == EXPECT_SELF
               and len(obs_other) == EXPECT_OTHER
               and set(by_skill_obs) == {EXPECT_SKILL}
               and set(by_capture) == {EXPECT_CAPTURE}),
        "p1_total": (len(ap) == EXPECT_APPLIES and len(self_all) == EXPECT_SELF
                     and len(other_all) == EXPECT_OTHER),
        "p2": bool(ap) and not unattributed,
        "other_ally": sum(1 for r in obs_other if r["ally"] is True),
        "other_foe": sum(1 for r in obs_other if r["ally"] is False),
        "other_side_unknown": sum(1 for r in obs_other if r["ally"] not in (True, False)),
        "p3": bool(obs_other) and all(r["ally"] is True for r in obs_other),
        "reach_pairs": len(reach), "reach_ally": len(ally), "reach_foe": len(foe),
        "foe_applied": sum(1 for r in foe if r["applied"]),
        "foe_within_earshot": len(foe_near),
        "foe_within_earshot_resolved": len(foe_inside_resolved),
        "foe_within_earshot_rows": [(r["capture"], r["port"], r["t"], r["caster"], r["dist"],
                                     r["dist_hold"], r["on_lead"]) for r in foe_near],
        "pairs_exact": len(exact_pairs),
        "pairs_on_lead": sum(1 for r in ally + foe if r["on_lead"]),
        "ally_applied_dist": sorted(r["dist"] for r in ally_yes),
        "ally_unapplied_dist": sorted(r["dist"] for r in ally_no),
        "ally_applied_in": len(yes_in), "ally_applied_over": len(yes_over),
        "ally_unapplied_out": len(no_out), "ally_unapplied_under": len(no_under),
        "lower_bound": max(lows) if lows else None,
        "lower_bound_pairs": len(lows),
        "upper_bound": min(highs) if highs else None,
        "unresolved": len(unresolved), "refuting": len(refuting),
        "refuting_rows": [(r["capture"], r["port"], r["t"], r["caster"], r["wearer"],
                           r["applied"], r["dist"], r["dist_hold"], r["err"], r["src"])
                          for r in refuting],
        "unresolved_rows": [(r["capture"], r["port"], r["t"], r["caster"], r["wearer"],
                             r["applied"], r["dist"], r["dist_hold"], r["err"],
                             r["on_lead"], r["follow_lead"]) for r in unresolved],
        # P4 has a SIDES half (a foe pair never applies -- testable from tokens) and
        # a DISTANCE half (testable only on exact pairs; None = untestable here).
        "p4_sides": bool(ally_yes) and not any(r["applied"] for r in foe),
        "p4_distance": (None if not exact_pairs else not refuting),
        "hero_dist": sorted(r["dist"] for r in on_hero if r["dist"] is not None),
        "p5": bool(on_hero) and all(r["caster"] is not None for r in on_hero),
        "boost_words_on_others": len(boost_rows),
        "boost_words_on_allies": sum(1 for b in boost_rows if b[5] is True),
        "boost_words_on_foes": sum(1 for b in boost_rows if b[5] is False),
        "boost_words_on_noncombatants": sum(1 for b in boost_rows if b[5] == "nonc"),
        "boost_words_side_unknown": sum(1 for b in boost_rows if b[5] is None),
        "boost_agents_per_apply": dict(sorted(collections.Counter(
            sum(1 for b in boost_rows if b[:3] == (r["capture"], r["port"], r["t"]))
            for r in on_obs if r["skill"] == EXPECT_SKILL).items())),
        # A boost word on a FOE-token agent refutes; a noncombatant does not.
        "p6": bool(boost_rows) and not any(b[5] is False for b in boost_rows),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rows", action="store_true")
    ap.add_argument("--cutoff", default=None, metavar="STAMP",
                    help="only captures stamped at or before this (test_shouts pins one)")
    a = ap.parse_args()
    c = census(cutoff=a.cutoff)
    s = score(c)
    if a.json:
        print(json.dumps({"score": s, "applies": c["applies"], "reach": c["reach"],
                          "refused": c["refused"], "observers": c["observers"]},
                         indent=1, default=str))
        return 0
    print(f"shoutjoin: {s['connections']} connections decoded whole with one observer, "
          f"{s['refused']} refused; {s['shout_skills_in_table']} Shout-type skills in the table")
    print(f"  [48, caster, skill] by skill TYPE: {s['prop48_by_type']}; for the Shout ids: "
          f"{s['announces_by_skill']}; prop-60 control on a Shout id (expected 0): "
          f"{s['prop60_control']}")
    print(f"  shout applies: {s['applies']} -- on the observer {s['on_observer']} "
          f"(by skill {s['on_observer_by_skill']}; by capture {s['on_observer_by_capture']}), "
          f"on a hero {s['on_hero']} (by skill {s['on_hero_by_skill']})")
    print(f"  caster == wearer {s['self']}, caster != wearer {s['other']}; the observer's own "
          f"{s['observer_own']}, another's on the observer {s['observer_other']} (of which a "
          f"hero's {s['hero_to_observer']}); a hero's own {s['hero_own']}, the observer's on a "
          f"hero {s['observer_to_hero']}; unattributed {s['unattributed']}")
    print(f"  P1 as registered (65 = 42 + 23 the OBSERVER's own vs another's, all 364, all "
          f"{EXPECT_CAPTURE}): {s['p1']}; 65 = 42 + 23 as caster == wearer vs not: {s['p1_total']}")
    print(f"  P2 (every apply announced inside {ANNOUNCE_WINDOW} s): {s['p2']}")
    print(f"  foreign applies on the observer: ally {s['other_ally']}, foe {s['other_foe']}, "
          f"side unknown {s['other_side_unknown']}; P3 (all from allies): {s['p3']}")
    print(f"  reach pairs: {s['reach_pairs']} (ally {s['reach_ally']}, foe {s['reach_foe']}; "
          f"foe applied {s['foe_applied']}; foe within {EARSHOT:.0f} u by POINT ESTIMATE "
          f"{s['foe_within_earshot']}, of them exact and inside within error "
          f"{s['foe_within_earshot_resolved']})")
    for row in s["foe_within_earshot_rows"]:
        print(f"    foe within earshot by point estimate, no apply (capture, port, t, caster, "
              f"dist, hold, on a lead): {row}")
    print(f"  the lead check (the observer's own 0x0029/0x002A point against its c2s report "
          f"inside {LEAD_CHECK_S} s): n {s['lead_offsets_n']}, median {s['lead_offset_median']} u, "
          f"max {s['lead_offset_max']} u, over the first cut's {FIRST_CUT_LEAD_ALLOWANCE:.0f} u "
          f"allowance: {s['lead_offsets_over_first_cut']} -- a lead is not a position")
    print(f"  pairs resting on a lead sample: {s['pairs_on_lead']} of {s['reach_pairs']}; pairs "
          f"on EXACT samples for both agents: {s['pairs_exact']}")
    print(f"  ally pairs that APPLIED, point estimates: {s['ally_applied_dist']}")
    print(f"  ally pairs that did NOT apply, point estimates: {s['ally_unapplied_dist']}")
    print(f"  against {EARSHOT:.0f} u by point estimate: applied within {s['ally_applied_in']}, "
          f"applied beyond {s['ally_applied_over']}; unapplied beyond {s['ally_unapplied_out']}, "
          f"unapplied within {s['ally_unapplied_under']}; of the crossings {s['unresolved']} "
          f"UNRESOLVED and {s['refuting']} REFUTING (an exact pair outside its error)")
    print(f"  what the tape says about the radius: lower bound max(dist - err) over the exact "
          f"applied ally pairs = {s['lower_bound']} u ({s['lower_bound_pairs']} pairs); upper "
          f"bound min(dist + err) over the exact unapplied = {s['upper_bound']}")
    for row in s["unresolved_rows"]:
        print(f"    unresolved: {row}")
    for row in s["refuting_rows"]:
        print(f"    refuting: {row}")
    print(f"  P4 sides (no foe pair applies): {s['p4_sides']}; P4 distance (no exact pair "
          f"refutes the radius; None = UNTESTABLE, no exact pair): {s['p4_distance']}")
    print(f"  hero applies: {s['on_hero']}, distances {s['hero_dist']}; P5 (attributed): {s['p5']}")
    print(f"  P6 boost words on OTHER agents in the observer's 364 apply batches: "
          f"{s['boost_words_on_others']} (team {s['boost_words_on_allies']}, foe-token "
          f"{s['boost_words_on_foes']}, noncombatant {s['boost_words_on_noncombatants']}, "
          f"no create {s['boost_words_side_unknown']}); agents per apply "
          f"{s['boost_agents_per_apply']}; P6 (none on a foe token): {s['p6']}")
    if a.rows:
        for r in c["applies"]:
            print(f"  APPLY {r['capture']} {r['port']} t={r['t']:.3f} skill {r['skill']} "
                  f"wearer {r['wearer']}{'*' if r['on_observer'] else ''} buff {r['buff']} "
                  f"dur {r['duration']} caster {r['caster']} self={r['self']} "
                  f"dt={r['announce_dt']} dist={r['dist']} hold={r['dist_hold']} "
                  f"err={r['err']} age={r['age']} src={r['src']} ally={r['ally']} "
                  f"speed_others={r['batch_speed']}")
        for r in c["reach"]:
            print(f"  REACH {r['capture']} {r['port']} t={r['t']:.3f} skill {r['skill']} "
                  f"caster {r['caster']} -> wearer {r['wearer']}{'*' if r['on_observer'] else ''} "
                  f"applied={r['applied']} ally={r['ally']} dist={r['dist']} "
                  f"hold={r['dist_hold']} err={r['err']} age={r['age']} src={r['src']} "
                  f"lead={r['on_lead']} follow={r['follow_lead']} exact={r['exact']} "
                  f"resolved={r['resolved']} low={r['low']} high={r['high']}")
    for stamp, conn, why in c["refused"]:
        print(f"  refused {stamp} {conn}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
