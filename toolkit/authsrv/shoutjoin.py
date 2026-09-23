r"""Party-wide shouts on retail's wire: every shout apply, attributed to its caster.

    python toolkit/authsrv/shoutjoin.py            # every live capture
    python toolkit/authsrv/shoutjoin.py --rows     # one line per apply and per reach pair
    python toolkit/authsrv/shoutjoin.py --json

WHY THIS EXISTS. `content/world.toml`'s row for "Charge!" (364) says "Earshot is not
modelled: the shout lands on the caster alone (the loopback party is the player)", and
DESKWORK-D5 step 5 (studies/deskwork/PLAN.md) surveyed the corpus by hand: every type-15
(Shout) 0x0042 on an observer is skill 364, all on `20260817T231139`, 42 applied by the
observer's own cast and 23 by ANOTHER caster's. This reader re-derives that from the
bytes and adds what the survey did not measure: for every shout announce and every agent
whose effect list is on the wire (the observer, a hero), whether an apply followed and how
far apart caster and wearer stood -- the REACH table that bounds "earshot" from the wire --
and the speed words the apply's batch carries for OTHER party members, which is the wire's
own statement that the shout landed on them too.

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
(`agents.GV_INSTANT_SKILL_ACTIVATED`, named there and sent by this server nowhere) is the
INSTANT skill's announce, not the shout's alone: the corpus census by skill type is
printed (364 and 348 are Shouts; 346, 10, 379, 349, 455 are Stances; 1217 is type 16).
The prop-60 form is kept as a counted control and expected at zero for a Shout id.

POSITIONS are the corpus's own samples, and NONE of them is the agent's position at the
apply: an agent's create (0x0020 field 5) is exact at creation; a lead (0x0029
AGENT_MOVE_TO_POINT field 2) and a destination (0x002A field 2) are points AHEAD of the
agent on its path (movecode); 0x002C AGENT_UPDATE_POSITION is exact and rare; the
observer's own c2s move requests (0x003D / 0x0047 field 1) are its position at the
request. A distance here is the straight line between the two agents' samples
INTERPOLATED in time between the sample before and the sample after the event when both
exist (`dist`), else held from the last sample (`dist_hold` alone), and every row carries
the sample ages and source opcodes so a reader can weigh it. This is a BOUND with a stated
error, not a measurement of earshot: the lead length plus speed x age. A FOLLOW LEAD -- a
party body's 0x0029 whose point IS the observer's own position (the follow parks on the
model) -- says nothing about where the body stood, so a pair whose lead sample lies within
FOLLOW_EPS of the other agent's sample is UNRESOLVED whatever its distance. ALLEGIANCE is
the create's token (0x0020 field 12); the observer's own token names its side.

THE PREDICTIONS, stated before the scan (the survey's counts are the priors; a reader
that disagrees refutes the survey, not the tape):

  P1  every Shout-type apply on the observer in the live corpus is skill 364 on
      `20260817T231139`: 65 applies, 42 attributed to the observer, 23 to another
      caster. (First run, 2026-09-23: 65 = 42 + 23 REPRODUCED as a total -- 59 on the
      observer and 6 on a hero, the 23 being 17 + 6 -- but the skill and the capture
      are REFUTED: 348 is in the set and the applies sit on ten captures. The
      measured composition is printed beside P1 and pinned in test_shouts.py.)
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
accounting does not close is refused and counted, never scored.
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
OP_SKILL_ACTIVATED = 0x00E3
OP_CMSG_MOVE = (0x003D, 0x0047)   # c2s: the observer's own position requests
PROP_SHOUT_ANNOUNCE = 48   # [48, caster, skill] -- the INSTANT skill's announce (OBSERVED)
PROP_SKILL_ACTIVATED = 60  # the spell's announce; a counted control here, expected 0
SHOUT_TYPE = 15
ANNOUNCE_WINDOW = 1.5      # s; the survey's window
BATCH_S = 0.060            # s; the corpus's batch shoulder (speedwords.py)
EARSHOT = 1000.0           # u; the client's aoe_range for 364 and WIKI's earshot
MAX_SPEED = 400.0          # u/s; the fastest speed word in the corpus is 399 (x1.33 on 300)
LEAD_ERROR = 300.0         # u; a lead point's allowance ahead of the agent (movecode)
FOLLOW_EPS = 5.0           # u; a lead this close to the other agent's sample is a follow lead
BOOST = 1.33               # the shout's speed factor (F48 P1)
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
    # The stated error: a lead's allowance for each agent whose sample is a
    # lead or destination, plus speed x the hold age when not interpolated.
    err = 0.0
    for age_b, ops, interp in ((ab, oa, xa is not None), (bb, ob, xb is not None)):
        if any(o in (OP_LEAD, OP_DEST) for o in ops):
            err += LEAD_ERROR
        if not interp and age_b is not None:
            err += MAX_SPEED * age_b
    # A follow lead: one agent's held sample is a lead/destination sitting ON the
    # other agent's held sample -- the body was walking TO the other agent, and
    # its own position is not on the wire.
    follow = (d_hold is not None and d_hold <= FOLLOW_EPS
              and (hoa in (OP_LEAD, OP_DEST) or hob in (OP_LEAD, OP_DEST)))
    return {"dist": d, "dist_hold": d_hold, "interpolated": interpolated,
            "age": (ab, bb), "age_after": (aa, ba),
            "src": (tuple(hex(o) for o in oa), tuple(hex(o) for o in ob)),
            "err": round(err, 1), "follow_lead": follow}


def rows_of(merged, shouts):
    """(applies, reach, observer, prop60_control, refused_reason).

    An APPLY row: {"t", "skill", "wearer", "on_observer", "buff", "duration",
    "caster", "self" (caster is the wearer), "announce_dt", "announce_t", "ally",
    "batch_speed" ([(agent, u/s, ally)] of the batch's 0x0027 words on agents other
    than the wearer, when the wearer is the observer), + _pair fields}.
    A REACH row, one per (announce, candidate wearer) with wearer != caster, the
    candidates being the observer and every other agent that ever wore a shout in
    this connection (a hero): {"t", "skill", "caster", "wearer", "on_observer",
    "applied" (an apply attributed to THIS announce landed on that wearer), "ally",
    + _pair fields, "resolved" (the radius verdict stands outside the stated error
    and rests on no follow lead)}.
    """
    observer = None
    for _t, d, op, v in merged:
        if d == "s2c" and op == OP_SKILL_ACTIVATED and len(v) > 1:
            observer = int(v[1])
            break
    if observer is None:
        return [], [], None, 0, "no 0x00E3 names the observer"
    samples, alleg = Samples(), {}
    announces, raw_applies, speeds = [], [], []   # speeds: (t, agent, u/s)
    prop60 = 0
    for t, d, op, v in merged:
        if d == "c2s":
            if op in OP_CMSG_MOVE and len(v) > 1 and _xy(v[1]):
                samples.add(observer, t, _xy(v[1]), op)
            continue
        if op == OP_CREATE and len(v) > 12:
            if _xy(v[5]):
                samples.add(int(v[1]), t, _xy(v[5]), op)
            alleg[int(v[1])] = int(v[12])
        elif op in (OP_LEAD, OP_DEST, OP_POSITION) and len(v) > 2 and _xy(v[2]):
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

    # SIDES. The observer's token names its team. A caster whose announce never
    # produced an apply on the observer and whose token differs is a FOE caster,
    # and its token a foe token. A THIRD token -- neither the observer's nor a
    # foe's -- is UNKNOWN (None), not a foe: on 20260817T231139 conn 54071 agent
    # 15 carries one, never shouts, and is boosted by the observer's team's
    # shouts every time (the first cut called it a foe by token inequality).
    obs_token = alleg.get(observer)
    applied_casters = set()
    for t, wearer, skill, _b, _d in raw_applies:
        prior = [a for a in announces if a[2] == skill and 0.0 <= t - a[0] <= ANNOUNCE_WINDOW]
        if prior and wearer == observer:
            applied_casters.add(prior[-1][1])
    foe_tokens = {alleg[c] for _t, c, _s in announces
                  if c in alleg and c != observer and c not in applied_casters
                  and obs_token is not None and alleg[c] != obs_token}

    def side(a, b):
        if a not in alleg or b not in alleg:
            return None
        if alleg[a] == alleg[b]:
            return True
        if alleg[a] in foe_tokens or alleg[b] in foe_tokens:
            return False
        return None

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
                                      if abs(ts - t) <= BATCH_S and ag != wearer})}
        row.update(_pair(samples, caster, wearer, t) if caster is not None
                   else {"dist": None, "dist_hold": None, "interpolated": False,
                         "age": None, "age_after": None, "src": None, "err": None,
                         "follow_lead": False})
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
            d = row["dist"]
            row["resolved"] = (d is not None and row["err"] is not None
                               and not row["follow_lead"]
                               and ((applied and d <= EARSHOT)
                                    or (not applied and d > EARSHOT)
                                    or abs(d - EARSHOT) > row["err"]))
            reach.append(row)
    return applies, reach, observer, prop60, None


def census():
    """Every live capture, every game connection that decodes whole."""
    types = skill_types()
    shouts = shout_skills(types)
    live = vaultpath.require_dir("captures", "live",
                                 why="shoutjoin reads live captures")
    out = {"applies": [], "reach": [], "connections": 0, "refused": [],
           "shout_skills": sorted(shouts), "announces_by_skill": collections.Counter(),
           "prop48_by_type": collections.Counter(), "prop60_control": 0}
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
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
            out["connections"] += 1
            for _t, d, op, v in merged:
                if d == "s2c" and op == OP_INT and len(v) > 3 \
                        and int(v[1]) == PROP_SHOUT_ANNOUNCE:
                    out["prop48_by_type"][types.get(int(v[3]))] += 1
                    if int(v[3]) in shouts:
                        out["announces_by_skill"][int(v[3])] += 1
            applies, reach, observer, prop60, _why = rows_of(merged, shouts)
            out["prop60_control"] += prop60
            port = ch["connection"].split("->")[0].rsplit(":", 1)[-1]
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
    self_rows = [r for r in on_obs if r["self"] is True]
    other_rows = [r for r in on_obs if r["self"] is False]
    unattributed = [r for r in ap if r["caster"] is None]
    by_skill_obs = collections.Counter(r["skill"] for r in on_obs)
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
    resolved_yes = [r["dist"] for r in ally_yes if r["resolved"]]
    foe_near = [r for r in foe if r["dist"] is not None and r["dist"] <= EARSHOT]
    # P6: the boost words on OTHER agents in a 364 apply's batch (the observer's).
    boost_rows = []
    for r in on_obs:
        if r["skill"] != EXPECT_SKILL:
            continue
        for ag, sp, al in r["batch_speed"]:
            if any(abs(sp - base * BOOST) < 0.5 for base in (288.0, 300.0)):
                boost_rows.append((r["capture"], r["port"], r["t"], ag, sp, al))
    return {
        "connections": c["connections"], "refused": len(c["refused"]),
        "shout_skills_in_table": len(c["shout_skills"]),
        "announces_by_skill": c["announces_by_skill"],
        "prop48_by_type": c["prop48_by_type"],
        "prop60_control": c["prop60_control"],
        "applies": len(ap), "on_observer": len(on_obs), "on_hero": len(on_hero),
        "on_observer_by_skill": dict(by_skill_obs),
        "on_observer_by_capture": dict(sorted(by_capture.items())),
        "self": len(self_rows), "other": len(other_rows),
        "other_plus_hero": len(other_rows) + len(on_hero),
        "unattributed": len(unattributed),
        "p1": (len(on_obs) == EXPECT_APPLIES and len(self_rows) == EXPECT_SELF
               and len(other_rows) == EXPECT_OTHER
               and set(by_skill_obs) == {EXPECT_SKILL}
               and set(by_capture) == {EXPECT_CAPTURE}),
        "p1_total": (len(ap) == EXPECT_APPLIES and len(self_rows) == EXPECT_SELF
                     and len(other_rows) + len(on_hero) == EXPECT_OTHER),
        "p2": bool(ap) and not unattributed,
        "other_ally": sum(1 for r in other_rows if r["ally"] is True),
        "other_foe": sum(1 for r in other_rows if r["ally"] is False),
        "other_side_unknown": sum(1 for r in other_rows if r["ally"] is None),
        "p3": bool(other_rows) and all(r["ally"] is True for r in other_rows),
        "reach_pairs": len(reach), "reach_ally": len(ally), "reach_foe": len(foe),
        "foe_applied": sum(1 for r in foe if r["applied"]),
        "foe_within_earshot": len(foe_near),
        "foe_within_earshot_rows": [(r["capture"], r["port"], r["t"], r["caster"], r["dist"],
                                     r["dist_hold"], r["err"]) for r in foe_near],
        "ally_applied_dist": sorted(r["dist"] for r in ally_yes),
        "ally_unapplied_dist": sorted(r["dist"] for r in ally_no),
        "ally_applied_in": len(yes_in), "ally_applied_over": len(yes_over),
        "ally_unapplied_out": len(no_out), "ally_unapplied_under": len(no_under),
        "resolved_applied_max": max(resolved_yes) if resolved_yes else None,
        "unresolved": len(unresolved), "refuting": len(refuting),
        "refuting_rows": [(r["capture"], r["port"], r["t"], r["caster"], r["wearer"],
                           r["applied"], r["dist"], r["dist_hold"], r["err"], r["src"])
                          for r in refuting],
        "unresolved_rows": [(r["capture"], r["port"], r["t"], r["caster"], r["wearer"],
                             r["applied"], r["dist"], r["dist_hold"], r["err"],
                             r["follow_lead"]) for r in unresolved],
        "p4": (bool(ally_yes) and not refuting and not any(r["applied"] for r in foe)),
        "hero_dist": sorted(r["dist"] for r in on_hero if r["dist"] is not None),
        "p5": bool(on_hero) and all(r["caster"] is not None for r in on_hero),
        "boost_words_on_others": len(boost_rows),
        "boost_words_on_allies": sum(1 for b in boost_rows if b[5] is True),
        "boost_words_on_foes": sum(1 for b in boost_rows if b[5] is False),
        "boost_words_side_unknown": sum(1 for b in boost_rows if b[5] is None),
        "boost_agents_per_apply": collections.Counter(
            sum(1 for b in boost_rows if b[:3] == (r["capture"], r["port"], r["t"]))
            for r in on_obs if r["skill"] == EXPECT_SKILL),
        # A boost word on a FOE-token agent refutes; a third-token agent does not.
        "p6": bool(boost_rows) and not any(b[5] is False for b in boost_rows),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--rows", action="store_true")
    a = ap.parse_args()
    c = census()
    s = score(c)
    if a.json:
        print(json.dumps({"score": s, "applies": c["applies"], "reach": c["reach"],
                          "refused": c["refused"]}, indent=1, default=str))
        return 0
    print(f"shoutjoin: {s['connections']} connections decoded whole, "
          f"{s['refused']} refused; {s['shout_skills_in_table']} Shout-type skills in the table")
    print(f"  [48, caster, skill] by skill TYPE: {s['prop48_by_type']}; for the Shout ids: "
          f"{s['announces_by_skill']}; prop-60 control on a Shout id (expected 0): "
          f"{s['prop60_control']}")
    print(f"  shout applies: {s['applies']} -- on the observer {s['on_observer']} "
          f"(by skill {s['on_observer_by_skill']}; by capture {s['on_observer_by_capture']}), "
          f"on a hero {s['on_hero']}; observer self {s['self']}, other {s['other']} "
          f"(+ hero = {s['other_plus_hero']}), unattributed {s['unattributed']}")
    print(f"  P1 as registered (65 = 42 + 23, all 364, all {EXPECT_CAPTURE}): {s['p1']}; "
          f"the total 65 = 42 + 23 with the hero applies counted: {s['p1_total']}")
    print(f"  P2 (every apply announced inside {ANNOUNCE_WINDOW} s): {s['p2']}")
    print(f"  foreign applies on the observer: ally {s['other_ally']}, foe {s['other_foe']}, "
          f"side unknown {s['other_side_unknown']}; P3 (all from allies): {s['p3']}")
    print(f"  reach pairs: {s['reach_pairs']} (ally {s['reach_ally']}, foe {s['reach_foe']}, "
          f"foe applied {s['foe_applied']}, foe within {EARSHOT:.0f} u {s['foe_within_earshot']})")
    for row in s["foe_within_earshot_rows"]:
        print(f"    foe within earshot, no apply: {row}")
    print(f"  ally pairs that APPLIED, distances: {s['ally_applied_dist']}")
    print(f"  ally pairs that did NOT apply, distances: {s['ally_unapplied_dist']}")
    print(f"  against {EARSHOT:.0f} u: applied within {s['ally_applied_in']}, applied beyond "
          f"{s['ally_applied_over']}; unapplied beyond {s['ally_unapplied_out']}, unapplied "
          f"within {s['ally_unapplied_under']}; largest RESOLVED applied distance "
          f"{s['resolved_applied_max']}; of the crossings {s['unresolved']} UNRESOLVED "
          f"(inside their error or on a follow lead) and {s['refuting']} REFUTING")
    for row in s["unresolved_rows"]:
        print(f"    unresolved: {row}")
    for row in s["refuting_rows"]:
        print(f"    refuting: {row}")
    print(f"  P4 (no refuting crossing; no foe pair applies): {s['p4']}")
    print(f"  hero applies: {s['on_hero']}, distances {s['hero_dist']}; P5 (attributed): {s['p5']}")
    print(f"  P6 boost words on OTHER agents in the observer's 364 apply batches: "
          f"{s['boost_words_on_others']} (team {s['boost_words_on_allies']}, foe-token "
          f"{s['boost_words_on_foes']}, third-token {s['boost_words_side_unknown']}); agents "
          f"per apply {dict(s['boost_agents_per_apply'])}; P6 (none on a foe token): {s['p6']}")
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
                  f"follow={r['follow_lead']} resolved={r['resolved']}")
    for stamp, conn, why in c["refused"]:
        print(f"  refused {stamp} {conn}: {why}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
