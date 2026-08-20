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

WHAT FIELD 3 IS. `bufflog.field3_report`'s docstring records two surviving
readings -- (a) it is the applying skill's ATTRIBUTE RANK, (b) it is a
duration-shaped field -- and says "the answer is one session away". It was
ZERO sessions away: the discriminator was already in the vault. Over the whole
live corpus, 102 applies, the prediction

    interp(duration0, duration15, field3) == the f32 duration on the wire

holds for **96 of 96 non-condition applies, with no misses**, where `interp` is
the client's own two-point scaler (`max(0, round(lo + (hi-lo)*rank/15.0))`,
0x005A8920) and both endpoints come from the client's own skill table. THE
CHECK HAS NO FREE PARAMETER: the endpoints are ArenaNet's, field3 and the
duration are retail's own bytes, and the formula was measured for a different
field entirely (the damage scale).

Two rows carry it alone:
  * skill 364 appears at TWO field3 values -- 10 with duration 10.0 (n=27) and
    13 with duration 12.0 (n=14), against endpoints 5->13. One skill, two
    ranks, two different durations, both predicted exactly. A duration-shaped
    field3 cannot produce 13 -> 12.0.
  * skill 160 carries field3 = 15 with duration 13.0. Reading (b) requires
    those to be the same number. They are not.

So field3 is the rank, and READING (b) IS REFUTED for non-conditions. The six
condition applies are the named exception and are NOT counted as support: a
condition's duration is set by the skill that inflicted it, not by the
condition row's own endpoints, and 480 proves it -- endpoints 3/3, seen on the
wire at duration 9.0.

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

# At or above this, the duration slot is not a second count. 0x20000 and
# 0x30000 are an enum in the high word; 999999 is the other spelling of
# forever. The floor is 0x10000 rather than any of the three, because what is
# established is the SHAPE (high word set) and not the specific values.
DURATION_SENTINEL_FLOOR = 0x10000

# The `target` byte at +0x31. Only these two codes are resolved, and the type
# column is what resolves them rather than a guess: all 199 Attacks are 5, 75
# of 76 Stances are 0, and every Glyph, Preparation and type-16 skill is 0.
# Codes 1, 3, 4, 6, 14 and 16 exist and are UNRESOLVED -- nothing here reads
# them, and a skill carrying one falls through to the caster's chosen target.
SELF_TARGET = 0
FOE_TARGET = 5

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
    19: "preparation",
}


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
            f"duration slot holds {lo} (0x{lo:X}), which is a sentinel and not "
            f"a second count -- 22 skills carry 0x20000, 7 carry 0x30000 and "
            f"one carries 999999, and 24 of the 30 are enchantments, which is "
            f"where a 'maintained until removed' marker belongs. Vital "
            f"Blessing is one of them. Refusing to put 36 hours on the wire.")

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

    def apply(self, agent_id, skill_id, rank, duration, now):
        """Open an episode and return it. The caller sends the `0x0042`.

        Refuses a duration of zero or less: a zero-length episode would be
        applied and removed in the same instant, which is a message pair that
        says nothing and a reader that has to special-case it.
        """
        if duration is None or duration <= 0:
            raise EffectError(
                f"skill {skill_id} resolved to duration {duration!r} -- an "
                f"episode with no length is two messages that cancel out. The "
                f"caller decides what no duration means; this table does not "
                f"invent one.")
        buff = self._alloc()
        ep = {"buff": buff, "agent": agent_id, "skill": skill_id,
              "rank": int(rank), "duration": float(duration),
              "applied_at": now, "expires_at": now + float(duration)}
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
