#!/usr/bin/env python3
r"""Read the client's skill DESCRIPTION TEMPLATES into labels, and referee every
slot against the same skill's own record.

Python 3 standard library only. Read-only on the client binary and the archive;
never launches anything. DESKWORK-D4 steps 1-3 / SKILLS-DT (studies/skills/FINDINGS.md).

WHAT A TEMPLATE IS. `textrec.TextIndex.get(record["description_id"])` returns
the description as ArenaNet authored it, with `%strN%` placeholders where the
client prints a number from the skill record (studies/skills FINDINGS 3: skill
322 wearing 318's text printed 322's OWN numbers). 1,265 of the 1,333
player-usable rows carry at least one placeholder (MEASURED here, build 38797;
the orchestrator's independent script agrees to the row: str1 1,090, str2 582,
str3 685).

WHICH SLOT IS WHICH FIELD -- MEASURED, and the natural order is WRONG.

    %str1%  ->  scale0 / scale15          (+0x5C / +0x60)
    %str2%  ->  bonus_scale0 / bonus_scale15  (+0x64 / +0x68)
    %str3%  ->  duration0 / duration15    (+0x44 / +0x48)

The controls that decide it, every one a row whose slots are already pinned to
the wiki by `content/world.toml`'s hand rows or by FINDINGS 4: Power Attack
(322, args = scale only) numbers its `+%str1% damage` from 10..40, which is its
SCALE slot; Sever Artery (382, args = bonus only) numbers `Bleeding for %str2%
seconds` from 5..25, its BONUS slot; Faintheartedness (135, args = duration |
bonus) puts `%str3% seconds` on 3..16 (duration) and `-%str2% Health
degeneration` on 0..3 (bonus); Defy Pain (318), Rush (319) and "To the Limit!"
(316) all say `For %str3% seconds` on their duration slots. The reading "str1 =
duration" would have Power Attack print a 0-second duration as its damage.

THE THEOREM THE ARTIFACT CAN REFUTE. Under this mapping, of the 2,357 slot
occurrences in the corpus, ZERO point at a field that is 0/0 -- WHATEVER its
bit says -- zero reach a duration sentinel (>= 0x10000), and every `%strN%`
has N in 1..3. Shift the mapping by one (`shifted()`), and 760+ of the 2,320
distinct slots land on 0/0 fields -- `test_skilldesc.py` runs that known-bad
arm and requires the referee to redden on it. The theorem's reach, stated:
it can refute a slot only where some OTHER field of the same row is 0/0,
which is 1,264 of the 2,320 distinct slots; on the other 1,056 the label
distribution is the witness (356 of the 359 str3 slots there carry a time
label). "seconds" is NOT the duration slot's word: of 905 "second" slots,
682 are str3, 141 are str2 and 82 are str1 -- a condition's duration lives in
the bonus or scale slot (Sever Artery), which is why the mapping is per INDEX
and never inferred from the words.

THE REFEREE. For each slot: the field it maps to, and one of
  AGREE_PROGRESSION   bit set, lo != hi         the client scales it by rank
  AGREE_FLAT          lo == hi != 0             a constant the client prints
  INDETERMINATE       bit clear, lo != hi       FINDINGS 12's unwitnessed shape:
                                                two numbers, no rule for which
                                                the client prints; NOT fitted
  CONFLICT_EMPTY      0/0, bit set OR clear     the text numbers an empty field
  CONFLICT_SENTINEL   duration >= 0x10000       upkeep / no-duration marker
  CONFLICT_INDEX      N not in the mapping
A disagreement is listed, never fitted -- including a template that gives ONE
index two different labels (`self_conflicts`: the classifier disagreeing with
itself, 18 rows). The same goes for the 54 hand rows: where `world.toml` names
`scale_means` / `bonus_scale_means`, the label this parser reads at the index
the mapping gives that FIELD must belong to the same family, or the row is a
listed conflict (`referee_hand_row`) -- and because the verdict is read from
the template, the hand rows are a second witness for the mapping that the
known-bad arm can fail: under `shifted()` their 51 AGREE collapse to 3.

THE LABELS ARE OURS. `Label` is our own enum, read from the words around a
slot after `normalise()` -- it is not ArenaNet's text and none of that text is
carried past the parse: what leaves is a label, a slot index, a verdict and
numbers already in `vault/content/skills.toml`. Two tiers, per ROW: SERVED
when every slot's (label, INDEX, type_code) has a consumer in the server today
(`CONSUMERS`, read off the sites: `skill_damage` reads `scale_means` on an
at-cast type, `skill_condition` reads bonus then scale on any type, the
movement means only on an open episode, ...); RECOGNISED when every slot is
labelled but some slot has no reader -- for its label, at its index, or on its
type. UNPARSED is the residue, reported and never guessed at. The classifier's
own precision is measured, not assumed: a "N% faster" with no movement verb is
a RATE_PERCENT (a recharge, an expiry), and a percent is a HEALTH_PERCENT only
when health is the thing named.

PROVENANCE. Commit the id, resolve the string at run time (CLAUDE.md). This
module prints template windows only from `--row` / `--residue`, as a TOOL over
the owner's own install, the way `textrec.py`'s CLI prints strings. Nothing it
writes goes into the repo; tests assert on counts, enums, indices and ids.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for _p in (HERE, HERE.parent, HERE.parent / "mapdata", HERE.parent / "authsrv"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
import skilltable   # noqa: E402
import pinned       # noqa: E402

find_exe = pinned.find

# --------------------------------------------------------------------------
# the slot -> field mapping (MEASURED, see the module docstring)
# --------------------------------------------------------------------------

SLOT_FIELD = {1: "scale", 2: "bonus_scale", 3: "duration"}
FIELD_BIT = {"duration": 1, "scale": 2, "bonus_scale": 4}   # skill_arguments
SENTINEL_FLOOR = 0x10000                                    # FINDINGS 13
SLOT_RE = re.compile(r"%str(\d+)%")

AGREE_PROGRESSION = "AGREE_PROGRESSION"
AGREE_FLAT = "AGREE_FLAT"
INDETERMINATE = "INDETERMINATE"
CONFLICT_EMPTY = "CONFLICT_EMPTY"
CONFLICT_SENTINEL = "CONFLICT_SENTINEL"
CONFLICT_INDEX = "CONFLICT_INDEX"
VERDICTS = (AGREE_PROGRESSION, AGREE_FLAT, INDETERMINATE,
            CONFLICT_EMPTY, CONFLICT_SENTINEL, CONFLICT_INDEX)
CONFLICTS = frozenset({CONFLICT_EMPTY, CONFLICT_SENTINEL, CONFLICT_INDEX})


def shifted(mapping=None, by=1):
    """The known-bad arm: every index moved `by` places along the field order.

    `shifted()` sends str1 to bonus_scale, str2 to duration and str3 to scale.
    A referee that does not redden on this is not refereeing anything.
    """
    mapping = mapping or SLOT_FIELD
    order = [mapping[k] for k in sorted(mapping)]
    return {k: order[(i + by) % len(order)] for i, k in enumerate(sorted(mapping))}


def field_endpoints(rec, field):
    """(lo, hi, bit_set) for one of the three scaling fields of a record."""
    lo, hi = int(rec[field + "0"]), int(rec[field + "15"])
    return lo, hi, bool(int(rec["skill_arguments"]) & FIELD_BIT[field])


def referee_slot(index, rec, mapping=None):
    """(verdict, field, lo, hi) for one `%strN%` against the SAME id's record.

    Never reads another row: the PvP twins (177 `pvp_only` family-0 rows whose
    `linked_id` points INTO the corpus) carry their own templates -- 0 of 177
    share the original's `description_id` (MEASURED) -- so the join is id to
    its own record and `linked_id` is never followed for a number.
    """
    mapping = mapping or SLOT_FIELD
    field = mapping.get(index)
    if field is None:
        return CONFLICT_INDEX, None, None, None
    lo, hi, on = field_endpoints(rec, field)
    if field == "duration" and max(lo, hi) >= SENTINEL_FLOOR:
        return CONFLICT_SENTINEL, field, lo, hi
    if lo == hi == 0:
        # Before the bit: an ENABLED 0..0 is still no number for the text to
        # print. The first version tested the bit first and graded a bit-set
        # 0/0 AGREE_FLAT against its own docstring, which hid 33 empty-field
        # landings from each known-bad arm (reviewers D4-R5 / ENG-8). Under
        # the measured mapping the count is 0 at either bit state.
        return CONFLICT_EMPTY, field, lo, hi
    if on:
        return (AGREE_PROGRESSION if lo != hi else AGREE_FLAT), field, lo, hi
    if lo == hi:
        return AGREE_FLAT, field, lo, hi
    return INDETERMINATE, field, lo, hi


# --------------------------------------------------------------------------
# our label enum
# --------------------------------------------------------------------------

class Label:
    """Our own names for what a slot numbers. Strings, so they print and join."""
    FIRE_DAMAGE = "FIRE_DAMAGE"
    COLD_DAMAGE = "COLD_DAMAGE"
    LIGHTNING_DAMAGE = "LIGHTNING_DAMAGE"
    EARTH_DAMAGE = "EARTH_DAMAGE"
    HOLY_DAMAGE = "HOLY_DAMAGE"
    SHADOW_DAMAGE = "SHADOW_DAMAGE"
    CHAOS_DAMAGE = "CHAOS_DAMAGE"
    DARK_DAMAGE = "DARK_DAMAGE"
    PHYSICAL_DAMAGE = "PHYSICAL_DAMAGE"      # slashing / piercing / blunt
    DAMAGE = "DAMAGE"                        # untyped "N damage"
    PLUS_DAMAGE = "PLUS_DAMAGE"              # "+N damage" on an attack
    DAMAGE_REDUCTION = "DAMAGE_REDUCTION"    # "take N less damage", "-N damage"
    DAMAGE_PERCENT = "DAMAGE_PERCENT"        # "N% more/less damage"
    HEAL = "HEAL"
    HEALTH = "HEALTH"                        # a health amount not a heal (lose, sacrifice)
    LIFE_STEAL = "LIFE_STEAL"
    MAX_HEALTH = "MAX_HEALTH"
    HEALTH_REGEN = "HEALTH_REGEN"
    HEALTH_DEGEN = "HEALTH_DEGEN"
    HEALTH_PERCENT = "HEALTH_PERCENT"        # "N% Health"
    ENERGY = "ENERGY"                        # gain / cost / amount
    ENERGY_LOSS = "ENERGY_LOSS"              # drain / steal / lose
    ENERGY_REGEN = "ENERGY_REGEN"
    ENERGY_DEGEN = "ENERGY_DEGEN"
    ENERGY_PERCENT = "ENERGY_PERCENT"
    ADRENALINE = "ADRENALINE"
    ARMOR = "ARMOR"
    ARMOR_PENETRATION = "ARMOR_PENETRATION"
    MOVE_SPEED_UP = "MOVE_SPEED_UP"
    MOVE_SPEED_DOWN = "MOVE_SPEED_DOWN"
    ATTACK_SPEED_UP = "ATTACK_SPEED_UP"
    ATTACK_SPEED_DOWN = "ATTACK_SPEED_DOWN"
    CAST_SPEED = "CAST_SPEED"                # "cast N% faster"
    CHANCE = "CHANCE"                        # "N% chance"
    BLOCK_CHANCE = "BLOCK_CHANCE"
    RATE_PERCENT = "RATE_PERCENT"            # "N% faster/slower" of a recharge, an
                                             # expiry, adrenaline -- not a body
    PERCENT = "PERCENT"                      # some other percentage
    DURATION = "DURATION"                    # "for N seconds" (the effect)
    CONDITION_DURATION = "CONDITION_DURATION"  # detail = the condition
    DISABLE_DURATION = "DISABLE_DURATION"    # "disabled for N seconds"
    KNOCKDOWN_DURATION = "KNOCKDOWN_DURATION"
    LIFETIME = "LIFETIME"                    # a spirit / minion "dies after N"
    INTERVAL = "INTERVAL"                    # "every N seconds"
    SECONDS = "SECONDS"                      # a second count with no clearer role
    LEVEL = "LEVEL"                          # "a level N spirit / pet / minion"
    COUNT = "COUNT"                          # foes, allies, spells, hexes, ...
    ATTRIBUTE = "ATTRIBUTE"                  # "+N to <attribute>", "attributes increased by N"
    MAX_ENERGY = "MAX_ENERGY"
    REDUCTION = "REDUCTION"                  # "reduced by N" with no damage named
    UNPARSED = "UNPARSED"


# The ten conditions, by the word a template uses for "you have it". The join
# key into `effects.CONDITION_BY_NAME` is the NAME (value); the word (key) is
# how the text says it -- "Bleeding", "Crippled", "Blinded", "on fire".
CONDITION_WORDS = {
    "bleeding": "Bleeding", "bleeds": "Bleeding", "bleed": "Bleeding",
    "blinded": "Blind", "blind": "Blind", "blindness": "Blind",
    "on fire": "Burning", "burning": "Burning",
    "crippled": "Crippled", "cripple": "Crippled",
    "deep wound": "Deep Wound",
    "disease": "Disease", "diseased": "Disease",
    "poison": "Poison", "poisoned": "Poison",
    "dazed": "Dazed",
    "weakness": "Weakness", "weakened": "Weakness",
    "cracked armor": "Cracked Armor",
}
CONDITION_NAMES = tuple(sorted(set(CONDITION_WORDS.values())))

ELEMENT_WORDS = {
    "fire": Label.FIRE_DAMAGE, "cold": Label.COLD_DAMAGE,
    "lightning": Label.LIGHTNING_DAMAGE, "earth": Label.EARTH_DAMAGE,
    "holy": Label.HOLY_DAMAGE, "shadow": Label.SHADOW_DAMAGE,
    "chaos": Label.CHAOS_DAMAGE, "dark": Label.DARK_DAMAGE,
    "slashing": Label.PHYSICAL_DAMAGE, "piercing": Label.PHYSICAL_DAMAGE,
    "blunt": Label.PHYSICAL_DAMAGE, "physical": Label.PHYSICAL_DAMAGE,
}

# SERVED: a `skill_effect` row carrying this meaning is acted on by the server
# today -- by ONE consumer each, and every consumer reads ONE field, most of
# them on ONE family of types. So the tier is a fact about (label, INDEX,
# type_code), not about the label alone: a heal numbered by %str2% has no
# reader, because `skill_heal` reads `scale_means` and nothing else. The
# first version tiered by label and counted 583 rows SERVED; against what the
# consumers read it is 350 (reviewers D4-R1 / ENG-1). The sites, 2026-09-22
# (line numbers move, the names do not):
#
#   FIRE/COLD/LIGHTNING/EARTH/HOLY_DAMAGE, PLUS_DAMAGE
#       authsrv.skill_damage: `scale_means` in SCALE_MEANS_DAMAGE, and only
#       when `_resolves_at_cast` (type NOT in effects.EFFECT_TYPES); the one
#       episode reader is the preparation's arrow bonus (episodemods /
#       authsrv `"preparation"`, type 19).       -> str1; at-cast types or 19
#   HEAL    authsrv.skill_heal: `scale_means` in SCALE_MEANS_HEAL, at cast.
#                                                -> str1; at-cast types
#   CONDITION_DURATION
#       authsrv.skill_condition: `bonus_scale_means` then `scale_means` through
#       effects.condition_id, at the land, any type; never the duration field.
#                                                -> str1 or str2; any type
#   ARMOR_PENETRATION
#       authsrv (combatmath.BASE_PENETRATION_MEANS): `bonus_scale_means`, and
#       the value must be flat.                  -> str2; any type
#   MOVE_SPEED_UP / DOWN
#       episodemods.move_speed_terms: either means, on OPEN EPISODES only.
#                                                -> str1 or str2; EFFECT_TYPES
#   ATTACK_SPEED_UP / DOWN
#       episodemods attack_speed_factor: `scale_means`, open episodes only.
#                                                -> str1; EFFECT_TYPES
#   ENERGY  authsrv.glyph_energy_amount: `scale_means == "Energy"`, called from
#       energy_cost_for over GLYPH episodes and nowhere else.
#                                                -> str1; type 12
#   DURATION  effects.resolve_duration reads duration0/15 for EFFECT_TYPES.
#                                                -> str3; EFFECT_TYPES
#
# RECOGNISED although a reader mentions the word (so NOT served):
#   ENERGY_LOSS     read only as the Energy Feast pair -- `scale_means ==
#                   "Energy loss"` AND `bonus_scale_means == "Heal per energy
#                   lost"` -- one row's shape, not a consumer of the label.
#   HEALTH_PERCENT  the one reader is `"Health threshold %"` on the BONUS of an
#                   attack whose bonus damage doubles below it (Final Thrust,
#                   flat); the parse cannot tell a threshold from a share of
#                   health, and of the 20 slots it labels none is that shape.
#
# Whether a served (label, index, type) is RIGHT for the skill -- Ignite
# Arrows' "Fire damage" rides the arrows, authsrv "A LABEL DOES NOT SAY WHEN"
# -- is D4 step 4's gate, not this tier's.
_AT_CAST, _EPISODE, _ANY, _GLYPH, _AT_CAST_OR_PREP = (
    "at-cast", "episode", "any", "glyph", "at-cast-or-preparation")
CONSUMERS = {
    Label.FIRE_DAMAGE: ((1,), _AT_CAST_OR_PREP),
    Label.COLD_DAMAGE: ((1,), _AT_CAST_OR_PREP),
    Label.LIGHTNING_DAMAGE: ((1,), _AT_CAST_OR_PREP),
    Label.EARTH_DAMAGE: ((1,), _AT_CAST_OR_PREP),
    Label.HOLY_DAMAGE: ((1,), _AT_CAST_OR_PREP),
    Label.PLUS_DAMAGE: ((1,), _AT_CAST_OR_PREP),
    Label.HEAL: ((1,), _AT_CAST),
    Label.CONDITION_DURATION: ((1, 2), _ANY),
    Label.ARMOR_PENETRATION: ((2,), _ANY),
    Label.MOVE_SPEED_UP: ((1, 2), _EPISODE),
    Label.MOVE_SPEED_DOWN: ((1, 2), _EPISODE),
    Label.ATTACK_SPEED_UP: ((1,), _EPISODE),
    Label.ATTACK_SPEED_DOWN: ((1,), _EPISODE),
    Label.ENERGY: ((1,), _GLYPH),
    Label.DURATION: ((3,), _EPISODE),
}
SERVED = frozenset(CONSUMERS)
RECOGNISED = frozenset(v for k, v in vars(Label).items()
                       if k.isupper() and v not in SERVED and v != Label.UNPARSED)
GLYPH_TYPE = 12          # effects.EFFECT_TYPES[12] == "glyph"
PREPARATION_TYPE = 19    # effects.EFFECT_TYPES[19] == "preparation"


def served_reason(label, index, type_code):
    """None when the server consumes a slot carrying `label` at `%str<index>%`
    on a skill of `type_code`; else a short reason it does not.

    `import effects` is what makes the type families the server's own list
    and not a copy of it.
    """
    rule = CONSUMERS.get(label)
    if rule is None:
        return "no consumer"
    indices, when = rule
    if index not in indices:
        return "wrong slot"
    import effects
    tc = int(type_code)
    episode = tc in effects.EFFECT_TYPES
    if when == _ANY:
        return None
    if when == _EPISODE:
        return None if episode else "non-episode type"
    if when == _AT_CAST:
        return None if not episode else "episode type"
    if when == _AT_CAST_OR_PREP:
        return None if (not episode or tc == PREPARATION_TYPE) else "episode type"
    if when == _GLYPH:
        return None if tc == GLYPH_TYPE else "not a glyph"
    raise ValueError(when)


def slot_served(label, index, type_code):
    """Does the server consume a slot carrying `label` at this index on this type?"""
    return served_reason(label, index, type_code) is None

# Row-level classifier flags: conditional / compound wording and area wording.
FLAG_IF = "IF"
FLAG_FOR_EACH = "FOR_EACH"
FLAG_WHILE = "WHILE"
FLAG_WHEN = "WHEN"
FLAG_EXCEPTION = "EXCEPTION"          # unless / instead / otherwise
FLAG_CHANCE = "CHANCE"
FLAG_LITERAL_PERCENT = "LITERAL_PERCENT"   # a constant printed as text (66%)
FLAG_AREA_ADJACENT = "AREA_ADJACENT"
FLAG_AREA_NEARBY = "AREA_NEARBY"
FLAG_AREA_IN_THE_AREA = "AREA_IN_THE_AREA"
FLAG_AREA_EARSHOT = "AREA_EARSHOT"
FLAG_TOUCH = "TOUCH"
FLAG_ALL_FOES = "ALL_FOES"
FLAG_ALL_ALLIES = "ALL_ALLIES"
FLAG_TARGET_FOE = "TARGET_FOE"
FLAG_TARGET_ALLY = "TARGET_ALLY"
FLAG_PATTERNS = (
    (FLAG_IF, r"\bif\b"),
    (FLAG_FOR_EACH, r"\bfor (each|every)\b|\bper\b"),
    (FLAG_WHILE, r"\bwhile\b"),
    (FLAG_WHEN, r"\bwhen(ever)?\b"),
    (FLAG_EXCEPTION, r"\bunless\b|\binstead\b|\botherwise\b"),
    (FLAG_CHANCE, r"\bchance\b"),
    # on the NORMALISED text `%%` is already `%`, so a literal percent is a
    # digit then `%` ("25%") -- with the digit not preceded by a letter, or
    # the `1%` closing `%str1%` matches and the flag is raised on every
    # slot-bearing row (it was, 1,278 rows: a flag that could not stay down)
    (FLAG_LITERAL_PERCENT, r"(?<![a-z])\d%"),
    (FLAG_AREA_ADJACENT, r"\badjacent\b"),
    (FLAG_AREA_NEARBY, r"\bnearby\b"),
    (FLAG_AREA_IN_THE_AREA, r"\bin (the|this) area\b"),
    (FLAG_AREA_EARSHOT, r"\bearshot\b"),
    (FLAG_TOUCH, r"\btouch(ed)?\b"),
    (FLAG_ALL_FOES, r"\ball (nearby |adjacent |non-spirit )?foes\b"),
    (FLAG_ALL_ALLIES, r"\ball (nearby |adjacent |non-spirit )?(party members|allies)\b|\bparty\b"),
    (FLAG_TARGET_FOE, r"\btarget foe\b"),
    (FLAG_TARGET_ALLY, r"\btarget (other )?ally\b"),
)
FLAGS = tuple(f for f, _ in FLAG_PATTERNS)
AREA_FLAGS = frozenset({FLAG_AREA_ADJACENT, FLAG_AREA_NEARBY,
                        FLAG_AREA_IN_THE_AREA, FLAG_AREA_EARSHOT})
COMPOUND_FLAGS = frozenset({FLAG_IF, FLAG_FOR_EACH, FLAG_WHILE, FLAG_WHEN,
                            FLAG_EXCEPTION, FLAG_CHANCE})


def row_flags(text):
    """The classifier flags a template's wording raises. A frozenset of FLAG_*."""
    low = text.lower()
    return frozenset(f for f, pat in FLAG_PATTERNS if re.search(pat, low))


# --------------------------------------------------------------------------
# the parser
# --------------------------------------------------------------------------

_MARKUP = (
    (re.compile(r"<c=[^>]*>|</c>"), ""),          # colour tags
    (re.compile(r'\[pl:"([^"]*)"\]'), r"\1"),     # plural forms
    (re.compile(r"\[s\]"), "s"),                  # the plural s
    (re.compile(r"%%"), "%"),                     # an escaped literal percent
)
_SLOT_GUARD = "\x00"


def normalise(text):
    """Strip the template markup the classifier does not care about.

    `%strN%` is left alone. Everything else the client's text engine handles
    (colour, `[s]`, `[pl:...]`, `%%`) is reduced to the plain word. The slots
    are fenced before the `%%` rewrite so a slot's closing `%` can never pair
    with the escape that follows it: the corpus spells a slotted percent
    `%strN%%%` (250 times, MEASURED) and never `%strN%%`, so nothing was lost
    on this build -- by ArenaNet's spelling, not by this function's design.
    """
    text = SLOT_RE.sub(lambda m: f"{_SLOT_GUARD}str{m.group(1)}{_SLOT_GUARD}", text)
    for pat, rep in _MARKUP:
        text = pat.sub(rep, text)
    return text.replace(_SLOT_GUARD, "%")


def parse_slots(text, window=48):
    """[(index, before, after)] for every `%strN%` in a NORMALISED template.

    `before` is the WHOLE prefix, because the classifier reads the slot's own
    sentence (Dismember names its Deep Wound sixty characters before the slot
    that numbers it); `after` is a `window`-character tail.
    """
    out = []
    for m in SLOT_RE.finditer(text):
        before = text[:m.start()]
        after = text[m.end():m.end() + window]
        # a neighbouring slot is just another number to the classifier
        out.append((int(m.group(1)), SLOT_RE.sub(" N ", before).lower(),
                    SLOT_RE.sub(" N ", after).lower()))
    return out


def _words(s):
    return re.findall(r"[a-z%+\-]+", s)


_CONDITION_RE = re.compile(
    r"\b(deep wound|cracked armor|on fire|bleeding|bleeds|bleed|blinded|blindness|blind"
    r"|burning|crippled|cripple|diseased|disease|poisoned|poison|dazed|weakness|weakened)\b")


def _sentence_before(before):
    """The part of `before` after the last sentence break: the slot's own sentence."""
    cut = max(before.rfind(". "), before.rfind("! "), before.rfind("? "))
    return before if cut < 0 else before[cut + 2:]


def _condition_before(before):
    """The condition whose duration this "for N seconds" slot is, or None.

    The nearest condition word in the slot's OWN sentence, when the words right
    before the slot are "for" (a duration). Dismember (337) names its Deep
    Wound at the head of the sentence and numbers it at the tail -- "inflict a
    Deep Wound ..., lowering ... maximum Health by 20% for N seconds" -- so a
    fixed short window misses it while the sentence does not. The sentence
    bound is what keeps "target foe is Crippled. For N seconds, you ..." a
    plain DURATION.
    """
    tail = " ".join(_words(before)[-3:])
    if not re.search(r"\bfor( an additional| the next| another)?\s*$", tail):
        return None
    # "Burning foes ... are HEXED for N seconds": the verb right before "for"
    # is the thing timed, and it is not a condition -- the condition word was
    # only an adjective on the subject (Ash Blast, 1085).
    if re.search(r"\b(hexed|enchanted|knocked|disabled|stunned|interrupted)\b", tail):
        return None
    hits = _CONDITION_RE.findall(_sentence_before(before))
    return CONDITION_WORDS.get(hits[-1]) if hits else None


def classify(before, after):
    """(label, detail) for the words around one slot. Our enum; never text."""
    aw = _words(after)
    bw = _words(before)
    a1 = aw[0] if aw else ""
    a2 = " ".join(aw[:2])
    a3 = " ".join(aw[:3])
    btail = " ".join(bw[-4:])
    btail6 = " ".join(bw[-6:])
    blast = bw[-1] if bw else ""
    sentence = _sentence_before(before)

    # -- phrasings decided by the words BEFORE the slot, whatever follows it
    if re.search(r"\b(healed|heals?|regain|regains)( target (other )?ally| you| all[a-z ]*allies| adjacent allies| party members)?( for)?\s*$", btail6) \
            and not a1.startswith("second"):
        return Label.HEAL, ""
    if re.search(r"\bmaximum\s*$", btail) and re.search(r"\bhealth|\bheal", sentence) \
            and not (aw and aw[0] in ("health", "energy")):
        return Label.HEAL, "maximum"
    if re.search(r"\bmaximum health (is|are) (increased|raised) by\s*$", btail6) \
            or re.search(r"\bhave (an additional|\+)\s*$", btail) and a1.startswith("health") \
            and not (len(aw) > 1 and aw[1].startswith(("regen", "degen"))):
        return Label.MAX_HEALTH, ""
    if re.search(r"\b(attributes?|magic|mastery|marksmanship|survival|storage|strength|tactics"
                 r"|expertise|casting|reaping|favor|healing prayers|prayers|communing|spawning"
                 r"|channeling|restoration|scythe|spear|leadership|command|motivation|dagger"
                 r"|critical strikes|deadly arts|shadow arts|swordsmanship|axe|hammer|curses"
                 r"|blood|death|soul|illusion|domination|inspiration|fast|energy storage"
                 r"|protection|smiting|divine|wilderness|beast|air|earth|fire|water)"
                 r"( attribute)?s? (is|are) (increased|boosted|raised|set to|reduced|lowered)( by| to)?( \+)?\s*$", btail6) \
            or re.search(r"\b(gain|gains|have|has) \+\s*$", btail) and re.search(r"\bto (all|these|your) [a-z ]*attributes|\bmagic\b|\bmastery\b|\battributes?\b", " ".join(aw[:5])):
        return Label.ATTRIBUTE, ""
    if re.search(r"\b(is|are) reduced by\s*$", btail) or re.search(r"\breduced by\s*$", btail):
        return (Label.DAMAGE_REDUCTION if re.search(r"\bdamage|\blife steal", sentence)
                else Label.REDUCTION), ""
    if re.search(r"\benergy (above|below|to)\s*$", btail):
        return Label.ENERGY, "cap"
    if a2.startswith("base damage") and "reduction" in a3:
        return Label.DAMAGE_REDUCTION, ""
    if blast == "by" and re.search(r"\bmaximum health\b", sentence) \
            and re.search(r"\b(increase|increases|raise|raises|boost|boosts)\b", sentence):
        return Label.MAX_HEALTH, ""

    # -- percentages: the slot is followed by a literal %
    if a1.startswith("%"):
        # the five words after the percent sign, so "of your maximum health"
        # reaches its noun; a percent label needs the thing it is a percent OF
        # named, or it is a plain PERCENT (reviewers ENG-2 / D4-R8: "faster"
        # alone was a movement speed and "of that" alone was a health share)
        tail = (aw[1:6] if a1 == "%" else [a1[1:]] + aw[1:5])
        tail = [w for w in tail if w]
        rest = " ".join(tail)
        if rest.startswith("faster") or rest.startswith("slower"):
            up = rest.startswith("faster")
            if re.search(r"\brecharge", btail6) or rest.startswith(("faster and recharge", "slower and recharge")):
                return Label.RATE_PERCENT, "recharge"
            if re.search(r"\bexpire", btail6):
                return Label.RATE_PERCENT, "expire"
            if "adrenaline" in btail6:
                return Label.RATE_PERCENT, "adrenaline"
            if "attack" in btail or rest.startswith(("faster and attack", "slower and attack")):
                return (Label.ATTACK_SPEED_UP if up else Label.ATTACK_SPEED_DOWN), ""
            if "cast" in btail or "activat" in btail:
                return Label.CAST_SPEED, ""
            if re.search(r"\b(move|moves|moving|movement|run|runs|running|walk|walks)\b", btail6):
                return (Label.MOVE_SPEED_UP if up else Label.MOVE_SPEED_DOWN), ""
            return Label.RATE_PERCENT, blast
        if rest.startswith("chance"):
            return (Label.BLOCK_CHANCE if "block" in " ".join(aw[:8]) or "block" in btail
                    else Label.CHANCE), ""
        if rest.startswith("armor penetration"):
            return Label.ARMOR_PENETRATION, ""
        if rest.startswith(("less damage", "more damage", "damage", "of the damage")) \
                or "damage" in tail[:3]:
            return Label.DAMAGE_PERCENT, ""
        if "health" in tail:
            return Label.HEALTH_PERCENT, ""
        if "energy" in tail:
            return Label.ENERGY_PERCENT, ""
        if rest.startswith("longer") or rest.startswith("shorter"):
            return Label.PERCENT, "duration"
        return Label.PERCENT, tail[0] if tail else ""

    # -- seconds
    if a1.startswith("second"):
        cond = _condition_before(before)
        if cond:
            return Label.CONDITION_DURATION, cond
        if re.search(r"disabled? (for|an additional)?\s*$", btail) or "disabled" in btail \
                or "recharge" in btail or "recharges" in btail:
            return Label.DISABLE_DURATION, ""
        if "knocked down" in btail or "knock down" in btail or "knockdown" in btail:
            return Label.KNOCKDOWN_DURATION, ""
        if re.search(r"\bdies? after\b", btail) or "lifespan" in btail:
            return Label.LIFETIME, ""
        if re.search(r"\bevery\s*$", btail):
            return Label.INTERVAL, ""
        if re.search(r"\b(for|for the next|lasts?|next|within|after|last)\s*$", btail) \
                or btail.endswith("for +") or btail.endswith("for an additional") \
                or btail.endswith("for the next") or blast in ("for", "next", "an", "additional"):
            return Label.DURATION, ""
        return Label.SECONDS, ""

    # -- damage
    if a1 in ELEMENT_WORDS and any(w.startswith("damage") for w in aw[1:5]):
        lbl = ELEMENT_WORDS[a1]
        return lbl, ("plus" if blast.endswith("+") else "")
    if blast.endswith("+") and a1 in ("against", "to", "vs"):
        return Label.PLUS_DAMAGE, ""
    if a1.startswith("damage"):
        if blast.endswith("+") or btail.endswith("an additional") or btail.endswith("additional") \
                or "extra" in btail:
            return Label.PLUS_DAMAGE, ""
        if blast.endswith("-") or "less" in btail or "reduced by" in btail or "fewer" in btail:
            return Label.DAMAGE_REDUCTION, ""
        return Label.DAMAGE, ""
    if a2.startswith("less energy") or a2.startswith("fewer energy"):
        return Label.ENERGY, "cost"
    if a2.startswith("less damage") or a2.startswith("fewer damage") or a1 == "less":
        return Label.DAMAGE_REDUCTION, ""
    if a2.startswith("more damage") or a2.startswith("extra damage") or a2.startswith("additional damage"):
        return Label.PLUS_DAMAGE, ""
    if a1 == "extra" and len(aw) > 1 and aw[1] in ELEMENT_WORDS:
        return ELEMENT_WORDS[aw[1]], "plus"

    # -- health
    if a2.startswith("health regeneration") or a2.startswith("health regen"):
        return Label.HEALTH_REGEN, ""
    if a2.startswith("health degeneration") or a2.startswith("health degen"):
        return Label.HEALTH_DEGEN, ""
    if a2.startswith("maximum health") or a2.startswith("max health") \
            or re.search(r"maximum health\s*(is|are)\s*(increased|reduced)\s*by\s*$", btail):
        return Label.MAX_HEALTH, ""
    if a1.startswith("health") or a1 == "hp":
        if re.search(r"\b(steal|steals|drain|drains|from)\b", btail) or "from" in a3:
            return Label.LIFE_STEAL, ""
        if re.search(r"\b(lose|loses|sacrifice|sacrifices|losing|cost|costs)\b", btail):
            return Label.HEALTH, "loss"
        if re.search(r"\b(healed|heal|heals|gain|gains|regain|restored|restore|healing|receives?)\b", btail) \
                or blast.endswith("+"):
            return Label.HEAL, ""
        if "maximum" in btail:
            return Label.MAX_HEALTH, ""
        return Label.HEALTH, ""

    # -- energy
    if a2.startswith("maximum energy") or a2.startswith("max energy"):
        return Label.MAX_ENERGY, ""
    if a2.startswith("energy regeneration") or a2.startswith("energy regen"):
        return Label.ENERGY_REGEN, ""
    if a2.startswith("energy degeneration") or a2.startswith("energy degen"):
        return Label.ENERGY_DEGEN, ""
    if a1.startswith("energy"):
        if re.search(r"\b(lose|loses|drain|drains|steal|steals|losing)\b", btail):
            return Label.ENERGY_LOSS, ""
        return Label.ENERGY, ""
    if a2.startswith("less energy") or a2.startswith("fewer energy"):
        return Label.ENERGY, "cost"

    # -- the rest of the vocabulary
    if "adrenaline" in a3:
        return Label.ADRENALINE, ""
    if a1.startswith("armor") or a1 == "ar" or a2.startswith("elemental armor") \
            or a2.startswith("base armor"):
        return Label.ARMOR, ""
    if re.search(r"\b(a|of) level\s*$", btail) or blast == "level":
        return Label.LEVEL, ""
    if a1 in ("foe", "foes", "ally", "allies", "party", "spell", "spells", "attack", "attacks",
              "hex", "hexes", "enchantment", "enchantments", "condition", "conditions",
              "skill", "skills", "minion", "minions", "corpse", "corpses", "time", "times",
              "strike", "strikes", "arrow", "arrows", "creature", "creatures", "target", "targets",
              "point", "points", "level", "levels", "other", "additional", "more", "of", "shot",
              "shots", "hit", "hits", "spirit", "spirits", "signet", "signets", "stance", "stances",
              "item", "items", "bones", "bone", "knock", "charges", "uses", "clone", "clones",
              "negative", "adjacent", "nearby", "incoming", "binding", "random", "different",
              "hexhexes", "enchanted", "attacking", "melee", "ranged", "shout", "shouts",
              "chant", "chants", "echo", "echoes", "trap", "traps", "ward", "wards"):
        return Label.COUNT, a1
    if re.search(r"\b(up to|maximum|next|first|additional)\s*$", btail) \
            or re.search(r"\b(up to|maximum)\s+\S*\s*$", btail):
        return Label.COUNT, a1
    return Label.UNPARSED, a2


def parse_row(text):
    """(slots, flags) for one template: [(index, label, detail)], frozenset(FLAG_*)."""
    norm = normalise(text)
    slots = [(n,) + tuple(classify(b, a)) for n, b, a in parse_slots(norm)]
    return slots, row_flags(norm)


LITERAL_MATCH = "LITERAL_MATCH"
LITERAL_MISS = "LITERAL_MISS"


def literal_constants(text):
    """The integers the template prints as TEXT (Rush's 25, Deep Freeze's 66)."""
    plain = SLOT_RE.sub(" ", normalise(text))
    return {int(x) for x in re.findall(r"(?<![\w%])\d+", plain)}


def literal_check(rec, text, shown, mapping=None):
    """[(index, field, value, LITERAL_MATCH | LITERAL_MISS)] for every flat,
    non-zero, non-sentinel field the template does NOT number with a slot.

    A census, not a verdict: 255 of 358 such fields in the corpus are printed
    literally (the flat 25 behind "move 25% faster"), and 103 are constants the
    engine holds that the text never states. Neither is a conflict -- the
    template is free not to mention a number -- but the match half is what
    lets a reader see that a bit-clear flat slot IS the text's constant.
    """
    mapping = mapping or SLOT_FIELD
    lits = literal_constants(text)
    out = []
    for n, field in mapping.items():
        if n in shown:
            continue
        lo, hi, _on = field_endpoints(rec, field)
        if lo != hi or lo == 0 or lo >= SENTINEL_FLOOR:
            continue
        out.append((n, field, lo, LITERAL_MATCH if lo in lits else LITERAL_MISS))
    return out


# --------------------------------------------------------------------------
# the hand rows as a second witness
# --------------------------------------------------------------------------

# A `skill_effect` label (world.toml, the wiki's progression-variable name) and
# the FAMILY of our labels it names. Families rather than one-to-one because
# the hand rows spell one meaning several ways ("Heal" / "Healing" / "Maximum
# heal") and our enum splits one wiki word several ways (ENERGY / ENERGY_LOSS).
# A hand label absent here is NOT COMPARABLE and is counted, not judged.
HAND_FAMILY = {
    "Fire damage": {Label.FIRE_DAMAGE}, "Cold damage": {Label.COLD_DAMAGE},
    "Lightning damage": {Label.LIGHTNING_DAMAGE}, "Earth damage": {Label.EARTH_DAMAGE},
    "Holy damage": {Label.HOLY_DAMAGE}, "+ Holy damage": {Label.HOLY_DAMAGE},
    # "+N <element> damage" on an attack: the wiki's variable is "+ Lightning
    # damage" (Spear of Lightning, world.toml 1551's own `verified`) and the
    # hand row wrote the family name. Our parse keeps the element as `plus`
    # detail; the family accepts it so the finer reading is not a conflict.
    "+ Damage": {Label.PLUS_DAMAGE, Label.DAMAGE}
                | {(lbl, "plus") for lbl in ELEMENT_WORDS.values()},
    "Damage on attack": {Label.DAMAGE, Label.PLUS_DAMAGE},
    "Damage reduction": {Label.DAMAGE_REDUCTION},
    "Heal": {Label.HEAL}, "Healing": {Label.HEAL}, "Maximum heal": {Label.HEAL},
    "Heal per energy lost": {Label.HEAL},
    "+ Maximum health": {Label.MAX_HEALTH}, "+ Max health": {Label.MAX_HEALTH},
    "Health degeneration": {Label.HEALTH_DEGEN},
    "Health threshold %": {Label.HEALTH_PERCENT},
    "Energy": {Label.ENERGY, Label.ENERGY_LOSS}, "Energy gain": {Label.ENERGY},
    "Energy loss": {Label.ENERGY_LOSS, Label.ENERGY},
    "Energy per melee block": {Label.ENERGY},
    "Movement speed increase": {Label.MOVE_SPEED_UP},
    "Movement speed decrease": {Label.MOVE_SPEED_DOWN},
    "Attack speed increase": {Label.ATTACK_SPEED_UP},
    "Attack speed decrease": {Label.ATTACK_SPEED_DOWN},
    "Armor penetration %": {Label.ARMOR_PENETRATION},
    "Block chance %": {Label.BLOCK_CHANCE, Label.CHANCE},
    "Duration": {Label.DURATION},
}
for _c in CONDITION_NAMES:
    HAND_FAMILY[_c] = {(Label.CONDITION_DURATION, _c)}
    HAND_FAMILY[_c + " duration"] = {(Label.CONDITION_DURATION, _c)}
# A hand row names a FIELD, never an index: `scale_means` is the scale field.
HAND_FIELD = (("scale_means", "scale"), ("bonus_scale_means", "bonus_scale"))


def hand_agrees(label, detail, means):
    """True / False, or None when the hand label is not comparable."""
    fam = HAND_FAMILY.get(means)
    if fam is None:
        return None
    return label in fam or (label, detail) in fam


def referee_hand_row(slots, hand_row, mapping=None):
    """[(means_key, index, hand_label, parsed_label, verdict)] for one hand row.

    The hand row names a FIELD; `mapping` says which `%strN%` numbers that
    field; the verdict compares the hand label with the label the parser read
    AT THAT INDEX: AGREE, CONFLICT, NO_SLOT (the template numbers no such
    index), NOT_COMPARABLE (a hand label outside HAND_FAMILY). `index` in the
    result is the one the mapping gave.

    The verdict is read from the TEMPLATE, so the known-bad arm is a
    measurement: under `shifted()` the 51 AGREE collapse to 3 (shift 2: 2),
    the rest NO_SLOT or CONFLICT. The first version short-circuited to a
    MAPPING_CONFLICT computed from the mapping alone -- a check that could not
    fail on data, counted as a witness (reviewers D4-R4 / ENG-3).

    A repeated index keeps its FIRST label here; a template that labels one
    index two ways is listed separately (`analyse()`'s `self_conflicts`).
    """
    mapping = mapping or SLOT_FIELD
    index_of = {field: n for n, field in mapping.items()}
    out = []
    by_index = {}
    for n, label, detail in slots:
        by_index.setdefault(n, (label, detail))
    for key, field in HAND_FIELD:
        means = hand_row.get(key)
        if not means:
            continue
        index = index_of.get(field)
        if means not in HAND_FAMILY:
            out.append((key, index, means, None, "NOT_COMPARABLE"))
            continue
        if index is None or index not in by_index:
            out.append((key, index, means, None, "NO_SLOT"))
            continue
        label, detail = by_index[index]
        ok = hand_agrees(label, detail, means)
        out.append((key, index, means, label if not detail else f"{label}:{detail}",
                    "AGREE" if ok else "CONFLICT"))
    return out


# --------------------------------------------------------------------------
# corpus loading and the whole-corpus analysis
# --------------------------------------------------------------------------

def load_corpus(exe=None, dat=None, language=0):
    """(records, texts, ix, exe, why): the player corpus, id -> record and id -> template.

    Needs the pinned exe and the archive. Raises (SystemExit from pinned.find,
    or LookupError) rather than returning something empty. A description the
    archive cannot resolve is `None` in `texts` -- `analyse()` counts it
    (`n_unreadable`, tier UNREADABLE) instead of folding it into "no slot"
    (0 today, MEASURED; on another build or language it would not be silent).
    """
    import textrec
    exe, why = (exe, "given") if exe else find_exe()
    ix = textrec.TextIndex(exe, dat or textrec.DEFAULT_DAT, language)
    data = ix.pe.data
    base, count, _score = skilltable.locate_table(data)
    rows = [skilltable.parse_record(data, base, i) for i in range(count)]
    corpus = set(skilltable.player_corpus(rows))
    records = {r["id"]: r for r in rows if r["id"] in corpus}
    texts = {sid: ix.get(records[sid]["description_id"]) for sid in sorted(corpus)}
    return records, texts, ix, exe, why


def hand_rows(world=None):
    """{skill_id: row}: the HAND `skill_effect` rows of content.load() -- every row
    NOT carrying `tier = "label"`, whichever layer it came from. The label tier
    (`loaded_label_rows`) is generated FROM this module's parse, so counting it
    as a hand witness would be one witness counted twice."""
    import content
    world = world or content.load()
    return {int(k): dict(v) for k, v in world.rows("skill_effect").items()
            if v.get("tier") != LABEL_TIER}


def loaded_label_rows(world=None):
    """{skill_id: row}: the `tier = "label"` skill_effect rows content.load() sees
    -- the emitted overlay, as the server reads it ({} on a machine without it)."""
    import content
    world = world or content.load()
    return {int(k): dict(v) for k, v in world.rows("skill_effect").items()
            if v.get("tier") == LABEL_TIER}


def analyse(records, texts, hand=None, mapping=None):
    """The whole referee over a corpus. Returns a plain dict of counts and lists.

    Everything in it is a count, an id, an index, a verdict or one of our
    labels -- no template text.
    """
    mapping = mapping or SLOT_FIELD
    hand = hand or {}
    rows = {}
    verdicts = collections.Counter()
    verdict_by_index = collections.Counter()
    labels = collections.Counter()
    label_by_index = collections.Counter()
    conflicts = []
    indeterminate = []
    hidden = []          # bit set, endpoints differ, no slot shows it
    hand_results = []
    literals = collections.Counter()
    flags = collections.Counter()
    blocking = collections.Counter()     # RECOGNISED rows per unserved label
    self_conflicts = []  # (sid, index, [labels]): one index, two labels
    n_unreadable = 0
    for sid in sorted(records):
        rec = records[sid]
        text = texts.get(sid)
        if text is None:
            n_unreadable += 1
            rows[sid] = {"id": sid, "type_code": int(rec["type_code"]), "slots": [],
                         "flags": [], "literals": [], "tier": "UNREADABLE"}
            continue
        slots, fl = parse_row(text)
        for f in fl:
            flags[f] += 1
        row = {"id": sid, "type_code": int(rec["type_code"]), "slots": [], "flags": sorted(fl)}
        labels_at = collections.defaultdict(set)
        for n, label, _detail in slots:
            labels_at[n].add(label)
        for n in sorted(labels_at):
            if len(labels_at[n]) > 1:
                self_conflicts.append((sid, n, sorted(labels_at[n])))
        seen = set()
        row["literals"] = literal_check(rec, text, {n for n, _l, _d in slots}, mapping)
        for lit in row["literals"]:
            literals[lit[-1]] += 1
        for n, label, detail in slots:
            verdict, field, lo, hi = referee_slot(n, rec, mapping)
            row["slots"].append({"index": n, "field": field, "verdict": verdict,
                                 "lo": lo, "hi": hi, "label": label, "detail": detail})
            labels[label] += 1
            label_by_index[(n, label)] += 1
            if n in seen:
                continue         # a repeated index is one slot refereed once
            seen.add(n)
            verdicts[verdict] += 1
            verdict_by_index[(n, verdict)] += 1
            if verdict in CONFLICTS:
                conflicts.append((sid, n, verdict, field, lo, hi))
            elif verdict == INDETERMINATE:
                indeterminate.append((sid, n, field, lo, hi))
        for n, field in mapping.items():
            lo, hi, on = field_endpoints(rec, field)
            if on and lo != hi and n not in seen:
                hidden.append((sid, n, field, lo, hi))
        if sid in hand:
            for r in referee_hand_row(slots, hand[sid], mapping):
                hand_results.append((sid,) + r)
        # per-row tier: SERVED when EVERY slot has a consumer for its
        # (label, index, type_code); the reasons keeping a row out are counted
        # per row as "LABEL strN: reason"
        reasons = {}
        for s in row["slots"]:
            why = served_reason(s["label"], s["index"], rec["type_code"])
            if why is not None:
                reasons[f"{s['label']} str{s['index']}: {why}"] = True
        if not slots:
            row["tier"] = "NO_SLOT"
        elif any(s["label"] == Label.UNPARSED for s in row["slots"]):
            row["tier"] = "UNPARSED"
        elif not reasons:
            row["tier"] = "SERVED"
        else:
            row["tier"] = "RECOGNISED"
            for key in reasons:
                blocking[key] += 1
        rows[sid] = row
    tiers = collections.Counter(r["tier"] for r in rows.values())
    return {
        "mapping": dict(mapping),
        "rows": rows,
        "n_rows": len(rows),
        "n_with_slot": sum(1 for r in rows.values() if r["slots"]),
        "n_slot_occurrences": sum(len(r["slots"]) for r in rows.values()),
        "verdicts": dict(verdicts),
        "verdict_by_index": {f"str{n}:{v}": c for (n, v), c in sorted(verdict_by_index.items())},
        "labels": dict(labels),
        "label_by_index": {f"str{n}:{l}": c for (n, l), c in sorted(label_by_index.items())},
        "tiers": dict(tiers),
        "conflicts": conflicts,
        "indeterminate": indeterminate,
        "hidden_progressions": hidden,
        "self_conflicts": self_conflicts,
        "n_unreadable": n_unreadable,
        "hand": hand_results,
        "hand_summary": dict(collections.Counter(r[-1] for r in hand_results)),
        "literals": dict(literals),
        "blocking": dict(blocking),
        "flags": dict(flags),
    }


def by_type(report, records):
    """{type_code: {n, with_slot, tiers..., conflicts, indeterminate}}."""
    out = {}
    for sid, row in report["rows"].items():
        t = out.setdefault(row["type_code"], collections.Counter())
        t["n"] += 1
        if row["slots"]:
            t["with_slot"] += 1
        t[row["tier"]] += 1
        for s in row["slots"]:
            if s["verdict"] in CONFLICTS:
                t["conflict_slots"] += 1
            elif s["verdict"] == INDETERMINATE:
                t["indeterminate_slots"] += 1
    return out


# --------------------------------------------------------------------------
# the coverage census (DESKWORK-Q7)
# --------------------------------------------------------------------------

GRADE_MODELLED = "modelled"          # a HAND skill_effect row: acts beyond its icon
GRADE_LABEL = "label-only"           # a generated label-tier row (SKILLS-LT): acts, marked
GRADE_EPISODE = "episode-only"       # EFFECT_TYPES: icon, timer, expiry; no numbers
GRADE_EPISODE_REFUSED = "episode-refused"   # EFFECT_TYPES but resolve_duration refuses
GRADE_NOTHING = "nothing"


def census(records, hand, rank=12, labels=None):
    """{skill_id: grade}, what the server resolves for each corpus row TODAY.

    `effects.applies_effect` decides the episode; `effects.resolve_duration` at
    `rank` decides whether that episode would actually apply (FINDINGS 12/13's
    refusals). A hand row wins over both: it is the one tier that acts. A
    label-tier row (`labels`, the loaded overlay) grades `label-only`, never
    `modelled` -- the fidelity judge's condition (deskwork D4 step 4): a skill
    served from a parsed label must not read as a hand-verified one.
    """
    import effects
    labels = labels or {}
    out = {}
    for sid, rec in records.items():
        if sid in hand:
            out[sid] = GRADE_MODELLED
            continue
        if sid in labels:
            out[sid] = GRADE_LABEL
            continue
        if effects.applies_effect(rec):
            try:
                effects.resolve_duration(rec, rank)
                out[sid] = GRADE_EPISODE
            except effects.EffectError:
                # the refusal class and nothing else: a code defect in the
                # resolver must surface, not grade as "refused" (ENG-10)
                out[sid] = GRADE_EPISODE_REFUSED
            continue
        out[sid] = GRADE_NOTHING
    return out


def census_by_type(records, grades, report=None):
    """type_code -> Counter(n, modelled, label-only, episode-only, episode-refused,
    nothing, with_slot, SERVED, RECOGNISED, UNPARSED, NO_SLOT)."""
    out = {}
    for sid, rec in records.items():
        t = out.setdefault(int(rec["type_code"]), collections.Counter())
        t["n"] += 1
        t[grades[sid]] += 1
        if report is not None:
            row = report["rows"][sid]
            if row["slots"]:
                t["with_slot"] += 1
            t[row["tier"]] += 1
    return out


def type_names(ix, codes):
    """type_code -> the client's own word for it, via typenames (run time)."""
    import typenames
    out = {}
    for c in codes:
        name = typenames.ROSETTA.get(c)
        if name is None and c in typenames.TYPE_STRING_ID:
            name = ix.get(typenames.TYPE_STRING_ID[c][1])
        out[c] = name or f"type {c}"
    return out


# --------------------------------------------------------------------------
# the label tier (DESKWORK-D4 step 4, SKILLS-LT, 2026-09-23)
# --------------------------------------------------------------------------
#
# THE OWNER'S DECISION (2026-09-23, on the failed step-3 gate): ship the PLAIN
# SERVED rows now as a marked tier; the residue is per-skill work. "Plain" is
# defined HERE, in code: tier SERVED and none of COMPOUND_FLAGS (IF, WHEN,
# FOR_EACH, WHILE, EXCEPTION, CHANCE) -- the six wordings a label would drop,
# making the skill fire unconditionally. 341 SERVED = 210 conditional + 131
# plain on build 38797 (MEASURED; `plain_served`).
#
# WHAT LEAVES: one `[skill_effect.<id>]` row per shipped skill carrying ONLY
# the fields the consumers read (`scale_means` / `bonus_scale_means`, the
# means strings the hand rows use), the record's `type_code`, `tier = "label"`,
# a `tier_detail` list of our own tokens, and client-table provenance whose
# `verified` records each slot's agreement as numbers and enums. No text: the
# whole vocabulary a row may contain is `OVERLAY_VOCABULARY`, and
# `text_leak()` names any string outside it.
#
# THE GATE ("A LABEL DOES NOT SAY WHEN", authsrv's rule for skill_damage,
# applied to every consumer): the tier says a consumer EXISTS for the
# (label, index, type); the gate asks whether that consumer acting at that
# skill's cast does what retail does. A row the server would OVER-apply is
# EXCLUDED with a reason (`EXCL_*`); one it would UNDER-apply ships with the
# shortfall named in `tier_detail` (`DETAIL_*`). Every exclusion is counted
# and written into the overlay's header, so the set never shrinks silently.

LABEL_TIER = "label"
LABELS_FILE = "skill_labels.toml"
EXTRACTOR = "toolkit/clientscan/skilldesc.py"
SOURCE = "client-table"

# Our label -> the means string the consumer compares against: the hand rows'
# vocabulary (world.toml; authsrv SCALE_MEANS_DAMAGE / SCALE_MEANS_HEAL,
# effects.CONDITION_BY_NAME, episodemods.MOVE_SPEED_MEANS and the attack-speed
# pair, combatmath.BASE_PENETRATION_MEANS, glyph_energy_amount's "Energy").
# A "+N <element> damage" on an attack is the additive "+ Damage" (the
# precedent is Spear of Lightning 1551's hand row): the bonus rides the swing
# and is added after armour, whatever its element word.
MEANS_OF = {
    Label.FIRE_DAMAGE: "Fire damage", Label.COLD_DAMAGE: "Cold damage",
    Label.LIGHTNING_DAMAGE: "Lightning damage", Label.EARTH_DAMAGE: "Earth damage",
    Label.HOLY_DAMAGE: "Holy damage", Label.PLUS_DAMAGE: "+ Damage",
    Label.HEAL: "Heal",
    Label.ARMOR_PENETRATION: "Armor penetration %",
    Label.MOVE_SPEED_UP: "Movement speed increase",
    Label.MOVE_SPEED_DOWN: "Movement speed decrease",
    Label.ATTACK_SPEED_UP: "Attack speed increase",
    Label.ATTACK_SPEED_DOWN: "Attack speed decrease",
    Label.ENERGY: "Energy",
}
DETAIL_PLUS = "plus"
FIELD_OF_INDEX = {1: "scale_means", 2: "bonus_scale_means"}   # str3 is the episode's
DAMAGE_LABELS = frozenset({Label.FIRE_DAMAGE, Label.COLD_DAMAGE, Label.LIGHTNING_DAMAGE,
                           Label.EARTH_DAMAGE, Label.HOLY_DAMAGE, Label.PLUS_DAMAGE})
STANDALONE_DAMAGE = DAMAGE_LABELS - {Label.PLUS_DAMAGE}

# The record's target byte, as the server resolves it (effects.TARGET_KINDS;
# authsrv.AREA_TARGET_BYTE): a consumer that ACTS ON THE CAST'S TARGET at the
# cast -- skill_damage, skill_condition -- is right only when that target is
# a foe (5) or the burst's aim (16); `cast_recipient` places a heal on the
# caster (0), the selected ally (3) or another ally (4), and hands every
# other byte to the SELECTED agent, a foe included.
FOE_TARGET_BYTES = frozenset({5, 16})
HEAL_TARGET_BYTES = frozenset({0, 3, 4})
AREA_BURST_TARGET_BYTE = 16     # authsrv.AREA_TARGET_BYTE
SPELL_TYPE = 5                  # authsrv.SPELL_TYPE_CODE: the one type spell_burst bursts
PET_ATTACK_TYPE = 20

EXCL_HAND_ROW = "HAND_ROW"                    # a hand row exists; the tier sits under it
EXCL_SELF_CONFLICT = "SELF_CONFLICT"          # one index, two labels: the parse disagrees
EXCL_DURATION_ONLY = "DURATION_ONLY"          # every slot is the episode's own duration
EXCL_CONDITION_ON_EPISODE = "CONDITION_ON_EPISODE"   # the episode inflicts it LATER
EXCL_PET_ATTACK = "PET_ATTACK"                # no pet is modelled
EXCL_RECIPIENT_NOT_A_FOE = "RECIPIENT_NOT_A_FOE"     # damage / condition; target byte not 5 / 16
EXCL_RECIPIENT_NOT_AN_ALLY = "RECIPIENT_NOT_AN_ALLY"  # heal; target byte not 0 / 3 / 4
EXCLUSIONS = (EXCL_HAND_ROW, EXCL_SELF_CONFLICT, EXCL_DURATION_ONLY,
              EXCL_CONDITION_ON_EPISODE, EXCL_PET_ATTACK,
              EXCL_RECIPIENT_NOT_A_FOE, EXCL_RECIPIENT_NOT_AN_ALLY)

DETAIL_AREA_BURST = "AREA_BURST"              # spell_burst covers the radius (byte 16, Spell, at cast)
DETAIL_AREA_ONE_TARGET = "AREA_ONE_TARGET"    # area wording; the server reaches one recipient
DETAIL_INDETERMINATE = "INDETERMINATE_SLOT"   # a labelled slot the consumer refuses (54.3)
DETAIL_CONDITION_BIT_CLEAR = "CONDITION_BIT_CLEAR_REFUSED"   # skill_condition refuses a bit-clear slot
DETAIL_SECOND_CONDITION = "SECOND_CONDITION_DROPPED"   # skill_condition returns one
DETAILS = (DETAIL_AREA_BURST, DETAIL_AREA_ONE_TARGET, DETAIL_INDETERMINATE,
           DETAIL_CONDITION_BIT_CLEAR, DETAIL_SECOND_CONDITION)
AREA_WORDING = AREA_FLAGS | {FLAG_ALL_FOES, FLAG_ALL_ALLIES, FLAG_TOUCH}

# EVERY string the overlay may contain. `text_leak()` is the tripwire: a
# description word reaching the vault would be a string outside this set.
OVERLAY_VOCABULARY = frozenset(
    {LABEL_TIER, SOURCE, EXTRACTOR, DETAIL_PLUS}
    | set(MEANS_OF.values()) | set(CONDITION_NAMES)
    | {v for k, v in vars(Label).items() if k.isupper()}
    | set(VERDICTS) | set(SLOT_FIELD.values()) | set(FLAGS) | set(DETAILS))
OVERLAY_MAX_STRING = max(len(s) for s in OVERLAY_VOCABULARY)


def means_for(label, detail):
    """The means string a consumer reads for this (label, detail), or None."""
    if label == Label.CONDITION_DURATION:
        return detail if detail in CONDITION_NAMES else None
    if detail == DETAIL_PLUS and label in STANDALONE_DAMAGE:
        return MEANS_OF[Label.PLUS_DAMAGE]
    return MEANS_OF.get(label)


def plain_served(report):
    """[sid]: tier SERVED and no COMPOUND flag -- the owner's definition, in code."""
    return sorted(sid for sid, row in report["rows"].items()
                  if row["tier"] == "SERVED" and not (set(row["flags"]) & COMPOUND_FLAGS))


def conditional_served(report):
    """[sid]: SERVED rows a label tier would fire unconditionally -- held back."""
    return sorted(sid for sid, row in report["rows"].items()
                  if row["tier"] == "SERVED" and set(row["flags"]) & COMPOUND_FLAGS)


def build_label_row(row, rec, hand_ids, self_conflict_ids=frozenset()):
    """(exclusion or None, tier_detail, fields, verified) for ONE report row.

    `row` is `analyse()`'s row (slots with label / detail / verdict / field /
    lo / hi, flags, type_code), `rec` the skill record. Plain-ness is NOT
    checked here -- `label_rows` selects the set and `check_label_rows` is the
    guard that a conditional row never reaches the overlay; keeping the gate
    separate is what lets the test force one in and watch the guard redden.
    """
    import effects
    sid = int(row["id"])
    tc = int(row["type_code"])
    target = int(rec["target"])
    if sid in hand_ids:
        return EXCL_HAND_ROW, [], {}, []
    if sid in self_conflict_ids:
        return EXCL_SELF_CONFLICT, [], {}, []
    fields, verified, seen = {}, [], set()
    labels = []
    for s in row["slots"]:
        n = int(s["index"])
        if n in seen:
            continue                     # the same number printed twice
        seen.add(n)
        v = {"slot": n, "field": s["field"], "lo": int(s["lo"]), "hi": int(s["hi"]),
             "verdict": s["verdict"], "label": s["label"]}
        if s["detail"] in CONDITION_NAMES or s["detail"] == DETAIL_PLUS:
            v["detail"] = s["detail"]
        verified.append(v)
        if s["label"] == Label.DURATION:
            continue                     # the episode machinery's; no field names it
        means = means_for(s["label"], s["detail"])
        field = FIELD_OF_INDEX.get(n)
        if means is None or field is None:
            raise ValueError(f"skill {sid}: served label {s['label']} at str{n} has no means")
        fields[field] = means
        labels.append((s["label"], n, s["verdict"], s["field"]))
    if not fields:
        return EXCL_DURATION_ONLY, [], {}, verified
    episode = tc in effects.EFFECT_TYPES
    conditions = [l for l in labels if l[0] == Label.CONDITION_DURATION]
    if conditions and episode:
        return EXCL_CONDITION_ON_EPISODE, [], {}, verified
    if tc == PET_ATTACK_TYPE:
        return EXCL_PET_ATTACK, [], {}, verified
    at_cast_on_foe = bool(conditions) or any(
        l[0] in DAMAGE_LABELS and not episode for l in labels)
    if at_cast_on_foe and target not in FOE_TARGET_BYTES:
        return EXCL_RECIPIENT_NOT_A_FOE, [], {}, verified
    if any(l[0] == Label.HEAL for l in labels) and target not in HEAL_TARGET_BYTES:
        return EXCL_RECIPIENT_NOT_AN_ALLY, [], {}, verified
    # shipped: name what the server does LESS of
    detail = sorted(f for f in row["flags"] if f in AREA_WORDING or f in (FLAG_TARGET_FOE, FLAG_TARGET_ALLY))
    if set(row["flags"]) & AREA_WORDING:
        standalone = any(l[0] in STANDALONE_DAMAGE for l in labels)
        if tc == SPELL_TYPE and target == AREA_BURST_TARGET_BYTE and standalone:
            detail.append(DETAIL_AREA_BURST)
        else:
            detail.append(DETAIL_AREA_ONE_TARGET)
    if any(l[2] == INDETERMINATE for l in labels):
        detail.append(DETAIL_INDETERMINATE)
    if any(not field_endpoints(rec, l[3])[2] for l in conditions):
        detail.append(DETAIL_CONDITION_BIT_CLEAR)
    if len(conditions) > 1:
        detail.append(DETAIL_SECOND_CONDITION)
    return None, detail, fields, verified


def label_rows(report, records, hand_ids):
    """({sid: row}, [(sid, exclusion)], [plain sids]) -- the label tier from a report.

    The row dict holds the emitted body (`fields`, `type_code`, `tier`,
    `tier_detail`) and its `verified` list; `emit_labels` writes it.
    """
    plain = plain_served(report)
    sc = {s[0] for s in report["self_conflicts"]}
    rows, excluded = {}, []
    for sid in plain:
        row = report["rows"][sid]
        why, detail, fields, verified = build_label_row(row, records[sid], hand_ids, sc)
        if why is not None:
            excluded.append((sid, why))
            continue
        rows[sid] = {"fields": fields, "type_code": int(row["type_code"]),
                     "tier": LABEL_TIER, "tier_detail": detail, "verified": verified}
    return rows, excluded, plain


def check_label_rows(rows, report, hand_ids):
    """Violations of the tier's own contract, as strings; [] when clean.

    The vacuity guard and the known-bad arm's target: a conditional row forced
    into `rows` is named here, as is a hand-row id, a missing field, a means
    outside the consumers' vocabulary or a string outside OVERLAY_VOCABULARY.
    """
    out = []
    for sid, r in rows.items():
        rep = report["rows"].get(sid)
        if rep is None:
            out.append(f"{sid}: not a corpus row")
            continue
        if rep["tier"] != "SERVED":
            out.append(f"{sid}: tier {rep['tier']}, not SERVED")
        bad = sorted(set(rep["flags"]) & COMPOUND_FLAGS)
        if bad:
            out.append(f"{sid}: conditional wording {' '.join(bad)}")
        if sid in hand_ids:
            out.append(f"{sid}: a hand row exists")
        if r.get("tier") != LABEL_TIER:
            out.append(f"{sid}: tier {r.get('tier')!r}")
        if not r.get("fields"):
            out.append(f"{sid}: no means field")
        for k, v in r.get("fields", {}).items():
            if k not in FIELD_OF_INDEX.values() or v not in OVERLAY_VOCABULARY:
                out.append(f"{sid}: {k} = {v!r} outside the consumers' vocabulary")
        if int(r.get("type_code", -1)) != int(rep["type_code"]):
            out.append(f"{sid}: type_code {r.get('type_code')} != {rep['type_code']}")
        if not r.get("verified"):
            out.append(f"{sid}: no slot agreement recorded")
    return out


def overlay_strings(obj, out=None):
    """Every str value in a parsed TOML table, recursively (keys are not values)."""
    out = [] if out is None else out
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            overlay_strings(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            overlay_strings(v, out)
    return out


def text_leak(table):
    """The strings in a parsed overlay that are NOT in OVERLAY_VOCABULARY.

    Empty on a clean overlay. A description word, a name, a sentence -- any
    authored text reaching the file -- is a string this set does not hold.
    """
    return sorted({s for s in overlay_strings(table) if s not in OVERLAY_VOCABULARY})


def _toml_str(s):
    if not isinstance(s, str) or any(c in s for c in '"\\\n\r\t') or not s.isprintable():
        raise ValueError(f"not a plain token: {s!r}")
    return f'"{s}"'


def _toml_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return _toml_str(v)
    if isinstance(v, (list, tuple)):
        return "[" + ", ".join(_toml_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k} = {_toml_value(x)}" for k, x in v.items()) + "}"
    raise TypeError(type(v))


def emit_labels(rows, excluded, build, exe, out_path, plain=()):
    """Write the label overlay. Deterministic: sorted ids, fixed field order, no
    clock. Returns the row count. The header carries the counts and every
    excluded id by reason, so the file itself says how the set was cut."""
    tally = collections.Counter(why for _sid, why in excluded)
    lines = [
        f"# GENERATED -- do not hand-edit. python {EXTRACTOR} --emit-labels",
        f"# exe: {exe}",
        f"# build: {build} (derived from the image's own sha256 via clientscan/pinned.py, "
        f"never typed in)",
        f"# rows: {len(rows)} label-tier skill_effect rows = {len(plain)} plain SERVED "
        f"(SERVED and none of {' '.join(sorted(COMPOUND_FLAGS))}) minus {len(excluded)} excluded",
        "# Loaded by toolkit/content.py as kind 'skill_effect', UNDER the hand rows: a",
        "# tier = \"label\" row never replaces a row without that tier. --no-skill-labels",
        "# makes the server ignore this file. studies/skills/FINDINGS.md 55 (SKILLS-LT).",
    ]
    for why in EXCLUSIONS:
        ids = sorted(sid for sid, w in excluded if w == why)
        if ids:
            lines.append(f"# excluded {why} ({tally[why]}): " + " ".join(map(str, ids)))
    lines.append("")
    for sid in sorted(rows):
        r = rows[sid]
        lines.append(f"[skill_effect.{sid}]")
        for field in ("scale_means", "bonus_scale_means"):
            if field in r["fields"]:
                lines.append(f"{field} = {_toml_str(r['fields'][field])}")
        lines.append(f"type_code = {int(r['type_code'])}")
        lines.append(f"tier = {_toml_str(r['tier'])}")
        lines.append(f"tier_detail = {_toml_value(list(r['tier_detail']))}")
        lines.append(f"[skill_effect.{sid}.provenance]")
        lines.append(f"source = {_toml_str(SOURCE)}")
        lines.append(f"extractor = {_toml_str(EXTRACTOR)}")
        lines.append(f"build = {int(build)}")
        lines.append(f"verified = {_toml_value(list(r['verified']))}")
        lines.append("")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return len(rows)


def default_labels_path():
    """vault/content/skill_labels.toml, through vaultpath (never ../../vault)."""
    import vaultpath
    return Path(vaultpath.vault_path("content")) / LABELS_FILE


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _print_table(header, rows):
    widths = [max(len(str(x)) for x in col) for col in zip(header, *rows)]
    fmt = "  ".join("{:<%d}" % w for w in widths)
    print(fmt.format(*header))
    print(fmt.format(*("-" * w for w in widths)))
    for r in rows:
        print(fmt.format(*[str(x) for x in r]))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", default=None, help="client to read; default the pinned pristine build")
    ap.add_argument("--dat", default=None, help="Gw.dat to read; default textrec.DEFAULT_DAT")
    ap.add_argument("--shift", type=int, default=0,
                    help="KNOWN-BAD ARM: shift the slot->field mapping by N places")
    ap.add_argument("--mapping", action="store_true", help="slot index vs field shape, by index")
    ap.add_argument("--referee", action="store_true", help="agreement / conflict / unparsed by type")
    ap.add_argument("--census", action="store_true", help="the coverage census (DESKWORK-Q7) by type")
    ap.add_argument("--hand", action="store_true", help="the 54 hand rows against the parse")
    ap.add_argument("--labels", action="store_true", help="label counts, by index")
    ap.add_argument("--row", type=int, nargs="*", help="one skill id: its slots, verdicts and windows")
    ap.add_argument("--residue", type=int, default=0, metavar="N",
                    help="print N unparsed slot windows (a tool over the owner's install)")
    ap.add_argument("--label", default=None, metavar="LABEL[:DETAIL]",
                    help="print every slot window the classifier gave this label "
                         "(optionally restricted to one index with --index)")
    ap.add_argument("--index", type=int, default=None, help="with --label: only this %%strN%% index")
    ap.add_argument("--json", metavar="PATH", help="write the whole report here (keep it out of git)")
    ap.add_argument("--emit-labels", nargs="?", const="", default=None, metavar="PATH",
                    help="write the LABEL TIER (SKILLS-LT): one skill_effect row per plain "
                         "SERVED skill, tier = \"label\", client-table provenance, no text. "
                         "Default PATH is vault/content/skill_labels.toml. Refuses an exe "
                         "whose bytes match no pristine build (no honest `build` stamp), "
                         "a shifted mapping, and a row set its own checker faults.")
    a = ap.parse_args(argv)

    records, texts, ix, exe, why = load_corpus(a.exe, a.dat)
    print(f"client: {exe}\n        ({why})\n")
    mapping = shifted(by=a.shift) if a.shift else SLOT_FIELD
    if a.shift:
        print(f"KNOWN-BAD ARM: mapping shifted by {a.shift}: {mapping}\n")
    import content
    world = content.load()
    hand = hand_rows(world)
    labels_loaded = loaded_label_rows(world)
    rep = analyse(records, texts, hand, mapping)
    print(f"{rep['n_rows']} corpus rows, {rep['n_with_slot']} with a %strN% slot, "
          f"{rep['n_slot_occurrences']} slot occurrences, {rep['n_unreadable']} unreadable")
    print(f"verdicts: {rep['verdicts']}")
    print(f"self-conflicts (one index, two labels): {len(rep['self_conflicts'])}")
    print(f"tiers:    {rep['tiers']}")
    print(f"hand rows: {rep['hand_summary']}")
    print(f"unshown flat constants: {rep['literals']}")
    print(f"flags:    {rep['flags']}")
    print("RECOGNISED rows blocked by (rows per unserved label): "
          + ", ".join(f"{k} {v}" for k, v in sorted(rep["blocking"].items(), key=lambda kv: -kv[1])))
    print()

    if a.mapping:
        print("== slot index vs field shape ==")
        _print_table(("index", "field", "verdict", "n"),
                     [(k.split(":")[0], mapping[int(k[3])], k.split(":")[1], v)
                      for k, v in rep["verdict_by_index"].items()])
        print(f"\nhidden progressions (bit set, lo != hi, no slot): {len(rep['hidden_progressions'])}")
        for h in rep["hidden_progressions"]:
            print("   ", h)
        print()

    if a.referee or a.census:
        names = type_names(ix, sorted({int(r["type_code"]) for r in records.values()}))
    if a.referee:
        print("== referee by type_code ==")
        bt = by_type(rep, records)
        rows = []
        for code in sorted(bt):
            t = bt[code]
            rows.append((code, names[code], t["n"], t["with_slot"], t["SERVED"], t["RECOGNISED"],
                         t["UNPARSED"], t["NO_SLOT"], t["conflict_slots"], t["indeterminate_slots"]))
        _print_table(("type", "name", "n", "slot", "SERVED", "RECOG", "UNPARSED", "NO_SLOT",
                      "conflict", "indet"), rows)
        print(f"\nconflicts ({len(rep['conflicts'])}):")
        for c in rep["conflicts"][:60]:
            print("   ", c)
        print()

    if a.census:
        grades = census(records, hand, labels=labels_loaded)
        cbt = census_by_type(records, grades, rep)
        print("== coverage census (what the server resolves today) ==")
        rows = []
        for code in sorted(cbt):
            t = cbt[code]
            rows.append((code, names[code], t["n"], t[GRADE_MODELLED], t[GRADE_LABEL],
                         t[GRADE_EPISODE], t[GRADE_EPISODE_REFUSED], t[GRADE_NOTHING],
                         t["with_slot"], t["SERVED"], t["RECOGNISED"], t["UNPARSED"]))
        tot = collections.Counter()
        for t in cbt.values():
            tot.update(t)
        rows.append(("all", "", tot["n"], tot[GRADE_MODELLED], tot[GRADE_LABEL],
                     tot[GRADE_EPISODE], tot[GRADE_EPISODE_REFUSED], tot[GRADE_NOTHING],
                     tot["with_slot"], tot["SERVED"], tot["RECOGNISED"], tot["UNPARSED"]))
        _print_table(("type", "name", "n", "modelled", "label", "episode", "ep-refused",
                      "nothing", "slot", "SERVED", "RECOG", "UNPARSED"), rows)
        plain = plain_served(rep)
        print(f"plain SERVED (no {' / '.join(sorted(COMPOUND_FLAGS))}): {len(plain)}; "
              f"conditional SERVED: {len(conditional_served(rep))}; "
              f"label rows loaded: {len(labels_loaded)}")
        print()

    if a.hand:
        print("== the hand rows against the parse ==")
        for r in rep["hand"]:
            if r[-1] != "AGREE":
                print("   ", r)
        print(f"   {rep['hand_summary']}\n")

    if a.hand or a.referee:
        print(f"== self-conflicts: one index, two labels ({len(rep['self_conflicts'])}) ==")
        for sc in rep["self_conflicts"]:
            print("   ", sc)
        print()

    if a.labels:
        print("== labels by index ==")
        for k, v in sorted(rep["label_by_index"].items(), key=lambda kv: -kv[1]):
            print(f"   {v:5d}  {k}")
        print()

    if a.row:
        for sid in a.row:
            rec = records.get(sid)
            if rec is None:
                print(f"{sid}: not in the player corpus")
                continue
            text = texts.get(sid) or ""
            norm = normalise(text)
            print(f"== {sid}  type {rec['type_code']}  args {rec['skill_arguments']}  "
                  f"scale {rec['scale0']}/{rec['scale15']}  bonus {rec['bonus_scale0']}/"
                  f"{rec['bonus_scale15']}  duration {rec['duration0']}/{rec['duration15']}"
                  + ("  UNREADABLE description" if texts.get(sid) is None else ""))
            for (n, b, af), (_, label, detail) in zip(parse_slots(norm), parse_row(text)[0]):
                v = referee_slot(n, rec, mapping)
                print(f"   str{n} -> {v[1]} {v[0]} {v[2]}/{v[3]}  {label}{':' + detail if detail else ''}")
                print(f"        ...{b[-32:]!r} [] {af[:32]!r}")
            print(f"   flags: {sorted(rep['rows'][sid]['flags'])}")
            if sid in hand:
                print(f"   hand: {referee_hand_row(parse_row(text)[0], hand[sid], mapping)}")
        print()

    if a.label:
        want_label, _, want_detail = a.label.partition(":")
        print(f"== slot windows labelled {a.label} ==")
        n_shown = 0
        for sid in sorted(records):
            text = texts.get(sid) or ""
            norm = normalise(text)
            for (n, b, af), (_, label, detail) in zip(parse_slots(norm), parse_row(text)[0]):
                if label != want_label or (want_detail and detail != want_detail) \
                        or (a.index and n != a.index):
                    continue
                print(f"   {sid:5d} str{n}  ...{b[-44:]!r} [] {af[:30]!r}")
                n_shown += 1
        print(f"   {n_shown} windows\n")

    if a.residue:
        print(f"== {a.residue} unparsed slot windows ==")
        shown = 0
        for sid in sorted(records):
            text = texts.get(sid) or ""
            norm = normalise(text)
            for (n, b, af), (_, label, detail) in zip(parse_slots(norm), parse_row(text)[0]):
                if label != Label.UNPARSED:
                    continue
                print(f"   {sid:5d} str{n}  ...{b[-36:]!r} [] {af[:36]!r}")
                shown += 1
                if shown >= a.residue:
                    break
            if shown >= a.residue:
                break
        print()

    if a.json:
        Path(a.json).write_text(json.dumps(rep, indent=1, default=list), encoding="utf-8")
        print(f"wrote {a.json}")

    if a.emit_labels is not None:
        if a.shift:
            print("REFUSED: --emit-labels under a shifted mapping would stamp the known-bad "
                  "arm's slots into the vault.", file=sys.stderr)
            ix.close()
            return 2
        build = skilltable.build_of(ix.pe.data)
        if build is None:
            print("REFUSED: this exe's sha256 matches no PRISTINE build in "
                  "clientscan/pinned.py, so no honest `build` stamp exists for the "
                  "rows. Point --exe at a pristine snapshot.", file=sys.stderr)
            ix.close()
            return 2
        out = Path(a.emit_labels) if a.emit_labels else default_labels_path()
        rows, excluded, plain = label_rows(rep, records, set(hand))
        bad = check_label_rows(rows, rep, set(hand))
        if bad:
            print("REFUSED: the label rows fail their own checker:\n  " + "\n  ".join(bad[:20]),
                  file=sys.stderr)
            ix.close()
            return 2
        n = emit_labels(rows, excluded, build, exe, out, plain)
        tally = collections.Counter(w for _s, w in excluded)
        print(f"wrote {out}: {n} label-tier rows = {len(plain)} plain SERVED - "
              f"{len(excluded)} excluded {dict(sorted(tally.items()))}")
        detail = collections.Counter(d for r in rows.values() for d in r["tier_detail"] if d in DETAILS)
        print(f"   under-applied, by detail: {dict(sorted(detail.items()))}")
    ix.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
