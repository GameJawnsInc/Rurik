"""The effect channel: `0x0042` opens an episode, `0x0044` closes it.

R4b's spine. Six of the nine `type_code` families R4b is graded on -- Stance,
Hex, Enchantment, Preparation and, once their meaning is sourced per skill,
Shout and the rest -- are the same mechanism: something is put on an agent for
a length of time and taken off again. Until 2026-08-20 this server modelled
none of it. `authsrv.py` knew `EFFECT_DEAD` and `EFFECT_TRANSITION` and nothing
else, and every skill whose scale was not damage resolved to nothing at all.

THIS MODULE IS THE WRITER; `bufflog.py` IS THE READER, and it was written
first. That is the order this repo's wins come in -- read retail, then
replicate one piece -- and it paid immediately, because the reader's corpus
answered the one question the writer could not have answered for itself.

  0x0042  [target, skill, field3, buff_id, f32 duration]      apply
  0x0044  [target, buff_id]                                   remove

WHAT FIELD 3 IS, AND WHOSE FINDING THAT IS. It is the applying skill's
ATTRIBUTE RANK, and the f32 duration is that skill's duration progression
evaluated at it. **That was settled on 2026-08-18, two days before this module
existed** -- `studies/isle/FINDINGS.md`, rung-8 prep section 2, "FIELD 3 IS THE
APPLIER'S ATTRIBUTE RANK -- settled offline, four ways" -- and settled BETTER
than by arithmetic alone: it is CORROBORATED against GWW across five values and
four skills, with the wiki and the wire sharing no author, code or ancestry.
The cleanest row is skill 160 = Windborne Speed, where GWW's Master of Winds
page independently supplies BOTH the rank ("15 Air Magic") and the duration
(13 s at rank 15), and the wire carries exactly those two numbers.

WHAT IS NEW HERE IS NOT THE FINDING. It is that the finding is now (1) checked
mechanically over the WHOLE corpus rather than five hand-picked rows, and
(2) READ BY THE SERVER, which is the part that was missing. Over 102 applies:

    interp(duration0, duration15, field3) == the f32 duration on the wire

holds for **96 of 96 non-condition applies, with no misses**, where `interp` is
the client's own two-point scaler (`max(0, round(lo + (hi-lo)*rank/15.0))`,
0x005A8920) and both endpoints come from the client's own skill table. No free
parameter: the endpoints are ArenaNet's, field3 and the duration are retail's
own bytes, and the formula was measured for a different field entirely (the
damage scale). Two rows would carry it alone -- skill 364 at TWO field3 values,
10 -> 10.0 (n=27) and 13 -> 12.0 (n=14) against endpoints 5->13; and skill 160
at field3 = 15 against a duration of 13.0, which a duration-shaped field cannot
produce.

AND `bufflog.field3_report`'S DOCSTRING SAID OTHERWISE FOR TWO DAYS. It
registered the question, listed both readings, and ended "the answer is one
session away and the prediction is on record before the run" -- while the
answer sat in `studies/isle/FINDINGS.md`. It has been corrected. THIS IS THE
FOURTH TIME IN ONE WEEK that a measured number sat unread beside code using an
invented one (property 17, the rung-7 damage formula, the item modifiers, and
now this), and the first three were all in the SAME direction: the measurement
was made, written down, and then not wired.

The six condition applies are counted separately here and are NOT support for
the rule as this module states it: a condition's duration comes from the skill
that INFLICTED it, not from the condition row's own endpoints -- 480 has
endpoints 3/3 and is on the wire at 9.0. (Isle section 2 fits 481 Crippled to
the rank reading too, using PIN DOWN's 3->15 progression rather than the
condition row's. Same rule, different join, and this server has no model of
"which skill inflicted this condition" to make that join with.)

WHAT THE DURATION SLOT HOLDS WHEN THE BIT IS CLEAR, which is the trap this
module exists to not fall into. `skill_arguments` bit 1 enables the duration
set, and `authsrv.skill_scale_value` REFUSES to read a disabled set -- correctly,
for the scale, where Rush's slot holds a constant 25 that is not a progression.
But retail sent duration 30.0 for skills 984 and 998, whose duration bit is
CLEAR. So the bit means "this duration SCALES with rank", not "this slot is
meaningful", and a server that honours it the strict way cannot reproduce two of
retail's own applies.

Measured over the 1,333-skill player corpus, the slot with the bit clear:

    endpoints EQUAL   666 skills   488 of them 0, the rest 1..120 ... and 30
                                   holding 131072 (x22), 196608 (x7) or
                                   999999 (x1)
    endpoints DIFFER   49 skills   no witness anywhere in the corpus

131072 is 0x20000 and 196608 is 0x30000 -- an enum in the high word, not a
second count, and 24 of the 30 are ENCHANTMENTS, which is where a "maintained
until removed" sentinel belongs. Vital Blessing (289) is one of them. So:

  * bit SET                             -> interpolate. Witnessed: 160, 364,
                                           348, 814.
  * bit CLEAR, equal, below the floor    -> the flat value. Witnessed: 984, 998
                                           at 30.0.
  * bit CLEAR, equal, at or above it     -> REFUSE. It is a sentinel we have not
                                           decoded, and 131072 seconds is not a
                                           duration.
  * bit CLEAR, endpoints DIFFER          -> REFUSE. 49 skills, zero witnesses.

Every permitted branch has a retail witness and every refused branch has none.
That is the whole design.

WHICH SKILLS GET AN EPISODE AT ALL, and this is the same refusal
`SCALE_MEANS_DAMAGE` makes one layer over. A duration in the slot does NOT mean
"this skill puts a timed effect on its target": Desperation Blow is an Attack
carrying 2/2, and what those two seconds are is not stated anywhere in the
table. So an episode needs a reason, and there are exactly two:

  * THE TYPE IS ONE WHOSE DEFINITION IS A TIMED EFFECT. Stance, Hex Spell,
    Enchantment Spell and Preparation are not skills that happen to have a
    duration -- GWW defines each of them AS a timed effect on the target the
    skill names. That is one citation per type covering hundreds of skills,
    and the type column corroborates the target byte independently (see
    `SELF_TARGET`).
  * OR A CONTENT ROW SAYS SO, per skill, the way `scale_means` does. None
    exists yet, so Shout, Spell, Signet, Glyph, Skill and Attack apply nothing
    -- including the two Shouts the corpus itself witnesses (348, 364). That is
    deliberate. Two witnesses say a shout CAN open an episode; neither says
    what any OTHER shout does, and party-wide shouts mean the target byte's 0
    does not settle who receives it.

Standard library only, no imports from authsrv: this module is a pure state
machine plus arithmetic, so its tests need no socket and no client.
"""

import math

# The two opcodes. Both are in `schema/messages.json` with the shapes above and
# both are ATTESTED IN LIVE TRAFFIC -- 102 applies and 88 removals across the
# corpus -- which is worth saying because `studies/isle/PLAN.md` 3.3 planned
# rung 8 expecting the opposite: 0x0042's layout came from our own loopback
# plus disassembly with ZERO ArenaNet witnesses, and "conditions ride some
# other channel" was the likely outcome. They do not.
OP_EFFECT_APPLY = 0x0042
OP_EFFECT_REMOVE = 0x0044

# At or above this, the duration slot is not a second count. The floor is
# 0x10000 rather than any specific value because the SHAPE (high word set) is
# what a server must refuse to send as a duration -- but the values are now
# NAMED, from the client's own code (studies/skills 13.1, 2026-08-22):
#
#   0x20000  ENERGY UPKEEP. GmCtlSkCard.cpp (the skill-card tooltip) reads the
#            skill record's duration slot (+0x44) and EXACT-compares it to
#            0x20000 at 0x008CC4EF; the branch's assert is ArenaNet's own words
#            -- `!(hasEnergyUpkeep && skillData.healthSacrifice)`
#            (GmCtlSkCard.cpp:462, 0x008CC50B). It is a skill record: the same
#            function tests the flags at +0x10. All 27 skills in the full table
#            that carry it are type 6 (Enchantment Spell) -- a maintained
#            enchantment, whose duration slot is free because it lasts until
#            removed. This is the marker the finding was after.
#   0x30000  NOT an upkeep flavor and NOT read at this slot. 367 skills of every
#            type carry it (mostly duration-bit-clear), and NONE of the image's
#            fifteen 0x30000 compares is fed by a +0x44 read -- it is the
#            duration slot's default filler for a skill with no fixed duration.
#            The old "2 and 3 are an enum in the high word" reading was half
#            right: 2 is read, 3 is a default the client never branches on here.
#   999999   never compared anywhere in the image -- a "forever" magnitude the
#            arithmetic passes through, not an enum value.
DURATION_SENTINEL_FLOOR = 0x10000
DURATION_ENERGY_UPKEEP = 0x20000    # GmCtlSkCard.cpp `hasEnergyUpkeep`


def sentinel_name(value):
    """ArenaNet's name for a duration-slot sentinel, or a generic label.

    Only 0x20000 has a sourced client name (energy upkeep / maintained
    enchantment); the rest are honestly generic. Kept as a function rather than
    a dict so the un-named values read as `no fixed duration` rather than as a
    missing key.
    """
    if value == DURATION_ENERGY_UPKEEP:
        return "energy upkeep (maintained enchantment)"
    return "no fixed duration"

# The `target` byte at +0x31. Two codes are resolved by the TYPE column
# (studies/skills 14): all 199 Attacks are 5, 75 of 76 Stances are 0, and
# every Glyph, Preparation and type-16 skill is 0. TWO MORE ARE RESOLVED BY
# THE WIKI'S OWN TARGETING WORDS, 2026-09-10 (SKILLS-RC, studies/skills 45):
# of the 41 skills carrying 4, every one checked says "target other ally"
# and "cannot self-target" -- Heal Other 286, Infuse Health 292, Restore
# Condition 276, Dwayna's Kiss 283, Draw Conditions 311, Convert Hexes 303;
# of the 124 carrying 3, every one checked says "target ally" -- Mend
# Ailment 277, Purge Conditions 278, Word of Healing 282, Remove Hex 301,
# Reversal of Fortune 307. Eleven skills, two columns that share no author
# (a byte in ArenaNet's table, a sentence on GWW), zero disagreements:
# CORROBORATED. Codes 1, 6, 14 and 16 stay UNRESOLVED and fall through to
# the caster's chosen target.
SELF_TARGET = 0
ALLY_TARGET = 3          # "target ally" -- the caster is a legal target
OTHER_ALLY_TARGET = 4    # "target other ally" -- the caster is NOT
FOE_TARGET = 5
TARGET_KINDS = {SELF_TARGET: "self", ALLY_TARGET: "ally",
                OTHER_ALLY_TARGET: "other_ally", FOE_TARGET: "foe"}

# The four `type_code` families whose GWW definition IS "a timed effect on the
# target". WIKI (GWW, rev. 2026): a Stance "lasts for a set amount of time";
# an Enchantment Spell is "maintained on the target until removed or expired";
# a Hex Spell is the same thing on a foe; a Preparation is "an effect on
# yourself that lasts for a period of time". `studies/presearing/MANIFEST.md`
# 8 decoded the codes themselves by Rosetta-stone against skills whose wiki
# type was independently known.
#
# NOT INCLUDED, and each absence is a decision: Shout (15), even though the
# corpus's own witnesses include two of them, because party-wide shouts break
# the "the target byte names the recipient" premise; Condition (8), because a
# condition is inflicted BY another skill and its duration comes from that
# skill rather than from its own row (the corpus's 480 proves it); and every
# type whose duration slot means something the table does not state.
EFFECT_TYPES = {
    3: "stance",
    4: "hex",
    6: "enchantment",
    12: "glyph",
    19: "preparation",
}

# AND THE TABLE ITSELF CORROBORATES THE LIST, which is why Glyph could be added
# on 2026-08-20 without waiting for a run. Across the 478 corpus skills in these
# five types, **every single one has a duration** -- 74 of 76 stances, 9 of 10
# glyphs, 13 of 14 preparations, 142 of 151 hexes and 194 of 227 enchantments
# resolve, and the remainder REFUSE on a sentinel or an unwitnessed shape.
# **Not one resolves to "no duration".** Meanwhile 488 of the 1,333-skill corpus
# have duration endpoints of 0/0, and none of them is in these five types. If
# the mapping from type to "this is a timed effect" were wrong, that is exactly
# where it would show: a type full of skills with nothing to time.
# `test_effects.py` checks it, and our decoder cannot force it true.

# ONE AT A TIME, PER CHARACTER -- three of the five types say so in the wiki,
# and two of them say it in text the game itself shows a player.
#
#   WIKI (GWW, "Stance", rev. 2020-10-23), quoting Isokeh, Expert Ranger, in
#   game: "Only one Stance can be active at any time, so if you are under the
#   effects of a Stance, using a new Stance will replace the previous one."
#   The article body agrees: "Each character can only have one stance in effect
#   at a time."
#
#   WIKI (GWW, "Preparation", rev. 2020-06-18): "Only one preparation can be
#   active at a time. Activating another preparation will override the previous
#   one."
#
#   WIKI (GWW, "Glyph", rev. 2024): "If a glyph is cast while another glyph is
#   already active, the new one replaces the old one."
#
# The rule is per TYPE, not per skill -- any stance replaces any stance. Hexes
# and enchantments carry no such rule and many can be live at once, which is why
# they are absent here rather than overlooked.
#
# THIS IS ALSO THE FIRST ANSWER TO "HOW DOES AN EFFECT GET REPLACED", which was
# NOT FOUND as of this morning. Re-sending `0x0042` does nothing (measured, both
# id choices), so a replacement has to be `0x0044` for the old one and `0x0042`
# for the new -- which is what `strip` + `apply` produce, and what a run can
# watch: press stance A, press stance B, A's icon must vanish.
EXCLUSIVE_TYPES = {3, 12, 19}

# THE TEN CONDITIONS, by the skill id the wire carries. MEASURED: `type_code
# == 8` in the client's own table selects exactly these ten and nothing else,
# and `studies/isle` R4-2 corroborated 478 and 480 on a rendered client. The
# names are GWW's, and they are the join key -- a skill's GWW progression
# variable is called `Bleeding` or `Crippled`, and that label is what says
# which condition it inflicts.
#
# A CONDITION IS NOT AN EFFECT TYPE, which is why 8 is absent from
# `EFFECT_TYPES` above. Nothing casts a condition: a condition is INFLICTED by
# another skill, and its duration comes from that skill's progression rather
# than from its own row. The corpus proves it -- skill 480 has endpoints 3/3
# and appears on the wire at duration 9.0, which its own row cannot produce.
# So conditions ride the same `0x0042` and reach it by a different door.
CONDITION_SKILLS = {
    478: "Bleeding", 479: "Blind", 480: "Burning", 481: "Crippled",
    482: "Deep Wound", 483: "Disease", 484: "Poison", 485: "Dazed",
    486: "Weakness", 2077: "Cracked Armor",
}
CONDITION_BY_NAME = {name: sid for sid, name in CONDITION_SKILLS.items()}

# WHAT A CONDITION DOES, for the four that degenerate health. WIKI (GWW,
# "Health degeneration", fetched 2026-08-18 for `studies/isle` 5): "each pip
# represents a loss of two health per second", the total is capped at 10 pips,
# and the per-condition pips are **Bleeding 3, Burning 7, Disease 4, Poison 4**.
#
# THE OTHER SIX DEGENERATE NOTHING and their absence here is a fact rather than
# a gap: Blind, Crippled, Deep Wound, Dazed, Weakness and Cracked Armor do
# other things (miss chance, movement, maximum health, casting, damage, armour)
# and none of them is modelled. A dict that gave every condition a pip would be
# the easy wrong generalisation.
CONDITION_PIPS = {478: 3, 480: 7, 483: 4, 484: 4}
PIP_HEALTH_PER_SECOND = 2.0
MAX_PIPS = 10.0


# THE AGENT STATUS WORD, and which effects move which bit. OBSERVED on
# retail's wire (deepwoundjoin.py's census over the live corpus, 2026-09-09):
# a `0x0042` apply is followed in the SAME batch by `0x00F1` [agent, word] --
# the agent's whole `m_status` word (schema/overrides.json 241: ChCliInt.h:254
# tests `m_status & CHAR_STATUS_DEAD` on this field), not a delta -- and the
# `0x0044` close is followed by the word with the same bits cleared. Retail's
# Deep Wound batch is exactly [0x0042 482, 0x00F1 0x22, 0x009F 42=max*0.8] and
# its close [0x0044, 0x00F1 0x00, 0x009F 42=max], n=2 each (isle capture
# 20260821T155022, agent 25).
#
# Which bit each effect sets, by the bits NEWLY SET in the word that follows
# its apply (and cleared at its remove), with the witness count:
#
#   0x0002  any CONDITION: set on 479/480/485/486/2077 alone (n=10 applies),
#           and in combination on 478 (0x03), 481 (0x0A), 482 (0x22), 483 and
#           484 (0x42); cleared at the close of the LAST live condition
#           (480 5/5, 482 2/2 with 2077 already gone, ...).
#   0x0001  with Bleeding 478 (n=1, set; the remove was not in the capture).
#   0x0008  with Crippled 481 (n=2 set, 2 cleared).
#   0x0020  with Deep Wound 482 (n=2 set, 2 cleared) -- the grey 20% of the
#           health bar, WIKI (GWW, "Deep Wound"): "the right 20% of the
#           affected character's health bar turns gray".
#   0x0040  with Disease 483 and Poison 484 (n=1 each, set and cleared) --
#           GWW "Health" gives the two ONE bar coloration, which is what one
#           shared bit looks like.
#   0x0080  any ENCHANTMENT: 160 (57 set / 52 cleared), 814 (2/2), and the
#           Isle's 984 (2/2).
#   0x0800  any HEX: 179 (1/1) and the Isle's 998 (3/3).
#   (none)  SHOUTS: 364's 47 applies carry no status message at all (46 of
#           47 have no 0x00F1 in the batch; the one that does sets nothing).
#   0x0400  set by the Isle's 999 (1 alone, 1 with 0x800); 999's identity is
#           not in the player corpus and the bit is NOT mapped here.
#
# What the bits MEAN to the client is the health-bar coloration table on GWW
# "Health" (hexed, poison/disease, bleeding, deep wound) -- which is exactly
# the set above, plus crippled. That reading is WIKI; the bit assignments are
# OBSERVED. `status_word` below is a pure function of the live episodes, so a
# caller sends the word whenever it changes and never tracks bits by hand --
# the same shape as `pips_from`, for the same reason (a tracked bit is a
# second book that drifts).
STATUS_CONDITION = 0x0002
STATUS_BLEEDING = 0x0001
STATUS_CRIPPLED = 0x0008
STATUS_DEAD = 0x0010            # agents.EFFECT_DEAD, the bit this file did not name
STATUS_DEEP_WOUND = 0x0020
STATUS_POISONED = 0x0040        # Disease and Poison share it
STATUS_ENCHANTED = 0x0080
STATUS_HEXED = 0x0800
CONDITION_STATUS_BITS = {
    478: STATUS_BLEEDING, 481: STATUS_CRIPPLED, 482: STATUS_DEEP_WOUND,
    483: STATUS_POISONED, 484: STATUS_POISONED,
}
TYPE_STATUS_BITS = {6: STATUS_ENCHANTED, 4: STATUS_HEXED}


def status_word(episodes, dead=False):
    """The agent's `m_status` word from its live episodes. OBSERVED bits only.

    A condition episode (type_code 8, the ids in CONDITION_SKILLS) contributes
    STATUS_CONDITION plus its own bit if it has one; an enchantment or hex
    contributes its type's bit; anything else contributes nothing (shouts,
    stances, preparations, glyphs -- none moved the word in the corpus). Death
    is the one bit that is not an episode and is passed in.
    """
    word = STATUS_DEAD if dead else 0
    for ep in episodes:
        skill = ep["skill"]
        if skill in CONDITION_SKILLS:
            word |= STATUS_CONDITION | CONDITION_STATUS_BITS.get(skill, 0)
        else:
            word |= TYPE_STATUS_BITS.get(int(ep.get("type_code", 0)), 0)
    return word


def pips_from(episodes):
    """Net degeneration pips from a set of live episodes, capped at 10.

    Capped because GWW caps it, and the cap is reachable: Burning alone is 7
    and Bleeding takes it to 10. A sum without the cap would out-degenerate
    retail the moment two conditions land together, which is exactly the sort
    of number that looks principled and is not.
    """
    total = sum(CONDITION_PIPS.get(ep["skill"], 0) for ep in episodes)
    return min(float(total), MAX_PIPS)


def condition_id(label):
    """The condition skill id a GWW progression label names, or None.

    `Bleeding` -> 478. Anything else -> None, including labels that are real
    progression variables but not conditions (`Health degeneration`,
    `Duration`, `+ Damage`), so an unmapped label inflicts nothing rather than
    guessing at the nearest condition.
    """
    return CONDITION_BY_NAME.get((label or "").strip())


class EffectError(Exception):
    """A refusal. Never a warning -- the house rule is refuse to guess."""


def interp(lo, hi, rank):
    """The client's own two-point scaler, at 0x005A8920.

        value(rank) = max(0, round(lo + (hi - lo) * rank / 15.0))

    Divisor a literal double 15.0 (a stdlib read of 0x0094B930 confirms the
    bytes), no upper clamp so ranks above 15 extrapolate, floor at zero from
    ArenaNet's own assert ConstSkill:3769. Half-UP rather than Python's
    half-even, matching `authsrv.skill_scale_value` -- the client's CRT helper
    adjusts by +/-1.0 rather than +/-0.5 and the tie-break was never settled,
    so the two callers at least agree with each other and the choice is
    written down in both.
    """
    exact = lo + (hi - lo) * rank / 15.0
    return max(0, int(math.floor(exact + 0.5)))


def resolve_duration(row, rank):
    """Seconds this skill's effect lasts at `rank`, or None for no duration.

    `row` is a content row from `vault/content/skills.toml` -- the extractor's
    own emission, so `duration0`, `duration15` and `skill_arguments` are the
    client's bytes. Returns None when both endpoints are 0, which is 488 of the
    corpus and is genuinely "this skill has no duration". RAISES on the two
    unwitnessed shapes rather than returning a plausible number.
    """
    lo, hi = int(row["duration0"]), int(row["duration15"])
    scales = bool(int(row["skill_arguments"]) & 1)

    if scales:
        if max(lo, hi) >= DURATION_SENTINEL_FLOOR:
            raise EffectError(
                f"duration endpoints {lo}..{hi} are at or above the sentinel "
                f"floor {DURATION_SENTINEL_FLOOR} with the SCALING bit set -- "
                f"a shape the corpus never witnesses (2 skills in 1,333). "
                f"Refusing rather than interpolating between two enum values.")
        return float(interp(lo, hi, rank))

    if lo != hi:
        raise EffectError(
            f"duration endpoints {lo}..{hi} DIFFER with the scaling bit clear. "
            f"49 skills are shaped like this and not one of them appears in "
            f"the 102 live applies, so there is no witness for either reading "
            f"-- interpolate anyway, or take one endpoint? Refusing.")

    if lo >= DURATION_SENTINEL_FLOOR:
        raise EffectError(
            f"duration slot holds {lo} (0x{lo:X}) = {sentinel_name(lo)}, not a "
            f"second count. 0x20000 is ENERGY UPKEEP -- GmCtlSkCard.cpp reads "
            f"this slot and exact-compares 0x20000, asserting `hasEnergyUpkeep` "
            f"(studies/skills 13.1); all 27 skills carrying it are maintained "
            f"enchantments, and Vital Blessing is one. Refusing to put an "
            f"upkeep sentinel on the wire as 36 hours -- modelling upkeep is a "
            f"resource drain, not a timed episode.")

    return float(lo) if lo else None


def applies_effect(row):
    """Whether this skill opens an episode. Type-driven, and small on purpose.

    Returns the family name, or None. A skill outside `EFFECT_TYPES` applies
    nothing until a content row says otherwise -- the same refusal
    `skill_damage` makes for a scale whose meaning is unsourced.
    """
    return EFFECT_TYPES.get(int(row["type_code"]))


def effect_recipient(row, caster_id, target_id):
    """Which agent wears the effect: the caster, or the cast's target.

    The `target` byte decides, and only its two resolved codes are honoured.
    Anything else falls through to the cast's target, which is what the caster
    aimed at -- so an unresolved code degrades to the caster's own choice
    rather than to a guess about ArenaNet's enum.
    """
    if int(row["target"]) == SELF_TARGET:
        return caster_id
    return target_id or caster_id


class EffectTable:
    """Live episodes on every agent, and the buff ids that name them.

    ONE INSTANCE PER CONNECTION, held in the connection's `state`, mutated only
    on the world-tick thread except for `apply`, which the connection thread
    also reaches. That is the same single-writer discipline `pending_casts`
    keeps, and for the same reason: an episode closed twice sends `0x0044`
    twice for a buff id that may already have been handed to a different
    effect.

    THE BUFF ID IS OURS. The corpus bounds it and does not determine it: ids
    run 5..121, are REUSED within a session (9 reuses in one connection), and
    at most 2 episodes are ever live at once. So a small integer, unique among
    the live episodes, released on close. This allocator hands out the lowest
    free id from 1 -- in range, small, reused, and unique, which is every
    property the corpus actually shows. What retail's allocator does between
    those constraints is NOT FOUND and nothing here pretends otherwise.
    """

    def __init__(self):
        self.live = {}          # buff_id -> episode dict
        self._next_hint = 1

    # -- allocation ---------------------------------------------------------

    def _alloc(self):
        buff = 1
        while buff in self.live:
            buff += 1
        return buff

    # -- the two halves -----------------------------------------------------

    def exclusive_on(self, agent_id, type_code):
        """Live episodes this agent must lose before gaining one of `type_code`.

        Empty unless the type is one of the three the wiki declares
        one-at-a-time. The caller sends a `0x0044` for each and then applies --
        never a silent swap, because a replacement the client is not told about
        leaves an icon on screen for an effect that is gone.
        """
        if int(type_code) not in EXCLUSIVE_TYPES:
            return []
        return sorted((ep for ep in self.live.values()
                       if ep["agent"] == agent_id
                       and ep["type_code"] == int(type_code)),
                      key=lambda ep: ep["buff"])

    def apply(self, agent_id, skill_id, rank, duration, now, type_code=0):
        """Open an episode and return it, or REFRESH the one already there.

        Refuses a duration of zero or less: a zero-length episode would be
        applied and removed in the same instant, which is a message pair that
        says nothing and a reader that has to special-case it.

        ALWAYS A NEW ID, EVEN FOR A SKILL ALREADY LIVE ON THAT AGENT, and this
        was tried the other way for one commit on 2026-08-20. The argument for
        collapsing was strong and both halves of it were wrong:

          * Run `20260820T174731` had the Hatcher re-cast Scourge Sacrifice
            every ~5 s and the client never drew more than ONE icon, whose bar
            drained straight through -- so it looked as though the client
            wanted one episode per (agent, skill).
          * `buff_id_report`'s peak of 2 concurrent episodes looked like a
            second witness.

        **THE CORPUS REFUTES IT.** Retail's own traffic holds **15 overlapping
        re-applications** -- a second `0x0042` for the same (target, skill)
        while the first is still live -- and **every one carries a NEW buff id**
        (120->121 at a 0.43 s gap, 110->114 at 0.50 s, 121->120 at 0.09 s),
        with the first episode still closing `expired` against its own duration.
        Same-id repeats occur only AFTER the previous one has closed. So
        ArenaNet's allocator is exactly this one, and collapsing would have made
        our stream a shape retail never produces.

        WHAT THE RUN ACTUALLY FOUND, then, is not a channel bug: it is that
        **our placeholder monster AI re-casts a hex the target already has**,
        which retail's overlaps (all under 0.5 s -- same-instant doubles, not
        re-casts) give no precedent for. That belongs to `pick_skill`, which
        says in its own docstring that it is a testing function and not a
        decision about AI. See `studies/skills/FINDINGS.md` 16.1.

        AND THE CLIENT'S BEHAVIOUR IS NOW A MEASURED FACT worth carrying: a
        repeat `0x0042` for a live (agent, skill) is DISCARDED -- the icon is
        not duplicated and the timer is not reset -- whether the buff id is new
        or the same. Re-sending the apply is therefore not a way to refresh an
        effect.

        ~~and how retail refreshes one is NOT FOUND~~ -- **THE WIRE HALF IS NOW
        ANSWERED, and it is not a message at all.** `studies/isle/FINDINGS.md`
        8.6: retail refreshes by sending NOTHING and delaying the `0x0044`.
        Across two live captures, 15 episodes closed LATE -- +1.25 s to +55.0 s
        past their own stated duration -- with no `0x0042`, no `0x0044` and no
        other traffic in the window, while the 7 episodes that were not being
        refreshed closed within +/-0.042 s of `apply + duration` over three
        durations and both captures. The precise seven are what rule out a
        coarse sweep and make the long holds real.

        ~~SO THIS TABLE EMITS A SHAPE RETAIL DOES NOT.~~ **SCOPE-CORRECTED
        2026-08-21 (studies/skills 36.8), and the correction is the owner's:
        the silent extension is ENVIRONMENTAL-ONLY and says nothing about casts.**
        Scored across the whole vault, all 15 late closures are the Isle's torches
        and Students, from the two runs where the operator deliberately stood in
        range; 78 cast- or attack-applied episodes over five skills and six
        captures are NEVER late -- exact, or early via a cure. The same
        environmental skills close exactly when nobody loiters (480, 984, 998 at
        +/-0.00 in the rung-6 run), so the variable is standing in the radius, not
        the skill. The Isle is a TRAINING AREA and its appliers are pedagogical
        props; generalising them to combat was a scope error.

        WHAT THAT LEAVES FOR THIS TABLE. Retail has no witnessed case of a live
        CAST effect being deliberately extended at all -- not silently, and not by
        REMOVE-then-APPLY. The 15 overlaps recorded above are same-instant doubles
        under 0.5 s, which is simultaneity rather than extension. So the shape here
        is UNWITNESSED either way, neither confirmed nor refuted, and the Isle
        cannot judge it. What is NOT settled is the half that
        decides whether we may copy it: between `apply + duration` and the late
        removal, is the effect still DRAWN? A wire capture cannot see a screen.
        `--probe effect_silent_extend` RAN 2026-08-21 (studies/skills 36) and the
        answer is a third thing neither reading proposed: **the client owns the
        expiry but does not forget the effect.** The live icon vanishes on the
        client's own timer with no packet -- ~9 s against a 10.0 s duration, some
        15 s before a late `0x0044` was sent -- and the slot then holds a STATIC,
        heavily faded ghost of the same icon until the removal arrives, which
        clears it. Measured, not eyeballed: same-state frames are byte-identical
        (diff 0.000), the slot moves 6.829 across the removal while a same-sized
        control patch beside it moves 0.000, and the ghost is held unchanged
        across 14 s of frames.

        SO THIS TABLE'S PAIR IS NOT LOAD-BEARING, AND SILENCE IS NOT FREE. The
        late removal landed correctly on an already-expired effect -- no refusal,
        no desync -- so REMOVE-then-APPLY is not required for correctness. But an
        effect held open by silence stops being VISIBLE at its stated duration,
        so anything the player must see for time T needs a duration covering T or
        a re-application. The shape here is unchanged: what changed is that both
        options are now costed from a measurement rather than assumed.
        """
        if duration is None or duration <= 0:
            raise EffectError(
                f"skill {skill_id} resolved to duration {duration!r} -- an "
                f"episode with no length is two messages that cancel out. The "
                f"caller decides what no duration means; this table does not "
                f"invent one.")
        buff = self._alloc()
        ep = {"buff": buff, "agent": agent_id, "skill": skill_id,
              "type_code": int(type_code),
              "rank": int(rank), "duration": float(duration),
              "applied_at": now, "expires_at": now + float(duration),
              "overlapping": any(e["agent"] == agent_id
                                 and e["skill"] == skill_id
                                 for e in self.live.values())}
        self.live[buff] = ep
        return ep

    def due(self, now):
        """Episodes whose stated duration has run out, oldest expiry first.

        MEASURED CLOSE RULE. Over the corpus, a removal lands at apply +
        duration: 57 of 88 within 5 ms and 83 of 88 within 50 ms
        (`bufflog.EXPIRY_TOLERANCE`). So the expiry is scheduled off the
        duration the apply itself declared, and nothing else -- not a rounded
        tick count, not a re-read of the skill row.
        """
        return sorted((ep for ep in self.live.values() if now >= ep["expires_at"]),
                      key=lambda ep: ep["expires_at"])

    def close(self, buff):
        """Retire one episode and release its id. Returns it, or None."""
        return self.live.pop(buff, None)

    def strip_agent(self, agent_id):
        """Close every episode on one agent. Returns them, lowest id first.

        DEATH IS A STRIP, not an expiry, and the distinction is one the reader
        already draws: `bufflog` classifies a removal that lands early as
        `stripped` and names a cure, a death or an overwrite as the causes. An
        effect left running on a corpse would be an episode our own reader
        scores as `open` forever.
        """
        gone = [ep for ep in self.live.values() if ep["agent"] == agent_id]
        for ep in gone:
            del self.live[ep["buff"]]
        return sorted(gone, key=lambda ep: ep["buff"])

    def on_agent(self, agent_id):
        """Live episodes on one agent, lowest buff id first."""
        return sorted((ep for ep in self.live.values()
                       if ep["agent"] == agent_id),
                      key=lambda ep: ep["buff"])
