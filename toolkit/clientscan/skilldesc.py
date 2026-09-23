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
occurrences in the corpus, ZERO point at a field that is empty (bit clear and
0/0), zero reach a duration sentinel (>= 0x10000), and every `%strN%` has N in
1..3. Shift the mapping by one (`shifted()`), and hundreds of slots land on
empty fields -- `test_skilldesc.py` runs that known-bad arm and requires the
referee to redden on it. "seconds" is NOT the duration slot's word: 682 of 872
"second" slots are str3, but 141 are str2 and 82 are str1 -- a condition's
duration lives in the bonus or scale slot (Sever Artery), which is why the
mapping is per INDEX and never inferred from the words.

THE REFEREE. For each slot: the field it maps to, and one of
  AGREE_PROGRESSION   bit set, lo != hi         the client scales it by rank
  AGREE_FLAT          lo == hi != 0             a constant the client prints
  INDETERMINATE       bit clear, lo != hi       FINDINGS 12's unwitnessed shape:
                                                two numbers, no rule for which
                                                the client prints; NOT fitted
  CONFLICT_EMPTY      bit clear, 0/0            the text numbers an empty field
  CONFLICT_SENTINEL   duration >= 0x10000       upkeep / no-duration marker
  CONFLICT_INDEX      N not in the mapping
A disagreement is listed, never fitted. The same goes for the 54 hand rows:
where `world.toml` names `scale_means` / `bonus_scale_means`, the label this
parser reads at str1 / str2 must belong to the same family, or the row is a
listed conflict (`referee_hand_row`).

THE LABELS ARE OURS. `Label` is our own enum, read from the words around a
slot after `normalise()` -- it is not ArenaNet's text and none of that text is
carried past the parse: what leaves is a label, a slot index, a verdict and
numbers already in `vault/content/skills.toml`. Two tiers: SERVED are the labels
the server consumes today through `skill_effect` rows (authsrv
`SCALE_MEANS_DAMAGE`, `SCALE_MEANS_HEAL`, the movement / attack-speed means,
`effects.condition_id`, ...); RECOGNISED are parsed to a label with no consumer
yet. UNPARSED is the residue, reported and never guessed at.

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
    if on:
        return (AGREE_PROGRESSION if lo != hi else AGREE_FLAT), field, lo, hi
    if lo == hi == 0:
        return CONFLICT_EMPTY, field, lo, hi
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
# today. The consumer sites, so the tier is a fact and not a hope:
#   elemental / plus damage    authsrv.SCALE_MEANS_DAMAGE, combatmath
#   heal                       authsrv.SCALE_MEANS_HEAL (property 55)
#   energy, energy loss        authsrv glyph_energy_amount / "Energy loss"
#   move / attack speed        episodemods.MOVE_SPEED_MEANS, attack_speed_factor
#   armour penetration         combatmath.BASE_PENETRATION_MEANS
#   health threshold %         authsrv "Health threshold %"
#   condition duration         authsrv skill_condition -> effects.condition_id
SERVED = frozenset({
    Label.FIRE_DAMAGE, Label.COLD_DAMAGE, Label.LIGHTNING_DAMAGE,
    Label.EARTH_DAMAGE, Label.HOLY_DAMAGE, Label.PLUS_DAMAGE,
    Label.HEAL, Label.ENERGY, Label.ENERGY_LOSS,
    Label.MOVE_SPEED_UP, Label.MOVE_SPEED_DOWN,
    Label.ATTACK_SPEED_UP, Label.ATTACK_SPEED_DOWN,
    Label.ARMOR_PENETRATION, Label.HEALTH_PERCENT,
    Label.CONDITION_DURATION,
    # DURATION is served by the EPISODE machinery, not by a label row:
    # `effects.resolve_duration` reads duration0/15 for the `EFFECT_TYPES`
    # families (stance, hex, enchantment, glyph, preparation) and for nothing
    # else, so `slot_served` gates it by type_code rather than by the label.
    Label.DURATION,
})
RECOGNISED = frozenset(v for k, v in vars(Label).items()
                       if k.isupper() and v not in SERVED and v != Label.UNPARSED)


def slot_served(label, type_code):
    """Does the server consume a slot carrying `label` on a skill of this type?

    The one type-gated label is DURATION: a Shout's "for N seconds" has no
    consumer because no episode opens for a Shout (effects.EFFECT_TYPES), while
    a Stance's does. Every other SERVED label is consumed through a
    `skill_effect` row whatever the type -- and whether that is RIGHT for the
    type (Ignite Arrows' "Fire damage" is a preparation, authsrv "A LABEL DOES
    NOT SAY WHEN") is D4 step 4's gate, not this tier's.
    """
    if label == Label.DURATION:
        import effects
        return int(type_code) in effects.EFFECT_TYPES
    return label in SERVED

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
    # digit then `%` ("25%"); a slot's percent is "%strN%%" and has no digit.
    (FLAG_LITERAL_PERCENT, r"\d%"),
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


def normalise(text):
    """Strip the template markup the classifier does not care about.

    `%strN%` is left alone. Everything else the client's text engine handles
    (colour, `[s]`, `[pl:...]`, `%%`) is reduced to the plain word.
    """
    for pat, rep in _MARKUP:
        text = pat.sub(rep, text)
    return text


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
        rest = " ".join(aw[1:4]) if a1 == "%" else (a1[1:] + " " + " ".join(aw[1:3])).strip()
        if rest.startswith("faster"):
            if "attack" in btail or rest.startswith("faster and attack"):
                return Label.ATTACK_SPEED_UP, ""
            if "cast" in btail or "activat" in btail:
                return Label.CAST_SPEED, ""
            return Label.MOVE_SPEED_UP, ""
        if rest.startswith("slower"):
            if "attack" in btail:
                return Label.ATTACK_SPEED_DOWN, ""
            if "cast" in btail or "activat" in btail:
                return Label.CAST_SPEED, ""
            return Label.MOVE_SPEED_DOWN, ""
        if rest.startswith("chance"):
            return (Label.BLOCK_CHANCE if "block" in " ".join(aw[:8]) or "block" in btail
                    else Label.CHANCE), ""
        if rest.startswith("armor penetration"):
            return Label.ARMOR_PENETRATION, ""
        if rest.startswith("less damage") or rest.startswith("more damage") \
                or rest.startswith("damage") or rest.startswith("of the damage"):
            return Label.DAMAGE_PERCENT, ""
        if rest.startswith("health") or rest.startswith("of your maximum health") \
                or rest.startswith("of its maximum health") or rest.startswith("of your health") \
                or rest.startswith("of that") or rest.startswith("of the target") \
                or rest.startswith("of target") or rest.startswith("of your"):
            return Label.HEALTH_PERCENT, ""
        if rest.startswith("energy"):
            return Label.ENERGY_PERCENT, ""
        if rest.startswith("longer") or rest.startswith("shorter"):
            return Label.PERCENT, "duration"
        return Label.PERCENT, rest.split(" ")[0] if rest else ""

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
HAND_SLOT = (("scale_means", 1), ("bonus_scale_means", 2))


def hand_agrees(label, detail, means):
    """True / False, or None when the hand label is not comparable."""
    fam = HAND_FAMILY.get(means)
    if fam is None:
        return None
    return label in fam or (label, detail) in fam


def referee_hand_row(slots, hand_row, mapping=None):
    """[(means_key, index, hand_label, parsed_label, verdict)] for one hand row.

    verdict is AGREE, CONFLICT, NO_SLOT (the hand names a slot the template does
    not number), NOT_COMPARABLE (a hand label outside HAND_FAMILY) or
    MAPPING_CONFLICT: the hand row says `scale_means`, i.e. the SCALE field,
    and `mapping` sends the index that field's slot should be to another field.
    Under `shifted()` every comparable hand row reddens this way, which makes
    the 51 wiki-verified rows a second witness for the mapping, independent of
    the empty-field theorem.
    """
    mapping = mapping or SLOT_FIELD
    out = []
    by_index = {}
    for n, label, detail in slots:
        by_index.setdefault(n, (label, detail))
    for key, index in HAND_SLOT:
        means = hand_row.get(key)
        if not means:
            continue
        if means not in HAND_FAMILY:
            out.append((key, index, means, None, "NOT_COMPARABLE"))
            continue
        if mapping.get(index) != key[:-len("_means")]:
            out.append((key, index, means, None, "MAPPING_CONFLICT"))
            continue
        if index not in by_index:
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
    or LookupError) rather than returning something empty.
    """
    import textrec
    exe, why = (exe, "given") if exe else find_exe()
    ix = textrec.TextIndex(exe, dat or textrec.DEFAULT_DAT, language)
    data = ix.pe.data
    base, count, _score = skilltable.locate_table(data)
    rows = [skilltable.parse_record(data, base, i) for i in range(count)]
    corpus = skilltable.player_corpus(rows)
    records = {r["id"]: r for r in rows if r["id"] in set(corpus)}
    texts = {sid: (ix.get(records[sid]["description_id"]) or "") for sid in corpus}
    return records, texts, ix, exe, why


def hand_rows():
    """{skill_id: row} from content.load()'s `skill_effect` table (repo + vault)."""
    import content
    world = content.load()
    return {int(k): dict(v) for k, v in world.rows("skill_effect").items()}


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
    for sid in sorted(records):
        rec = records[sid]
        text = texts.get(sid) or ""
        slots, fl = parse_row(text)
        for f in fl:
            flags[f] += 1
        row = {"id": sid, "type_code": int(rec["type_code"]), "slots": [], "flags": sorted(fl)}
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
        # per-row tier
        if not slots:
            row["tier"] = "NO_SLOT"
        elif any(s["label"] == Label.UNPARSED for s in row["slots"]):
            row["tier"] = "UNPARSED"
        elif all(slot_served(s["label"], rec["type_code"]) for s in row["slots"]):
            row["tier"] = "SERVED"
        else:
            row["tier"] = "RECOGNISED"
            # which unserved labels keep this row out of the served tier
            for lbl in sorted({s["label"] for s in row["slots"]
                               if not slot_served(s["label"], rec["type_code"])}):
                blocking[lbl if lbl != Label.DURATION else "DURATION (non-episode type)"] += 1
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

GRADE_MODELLED = "modelled"          # a skill_effect row: acts beyond its icon
GRADE_EPISODE = "episode-only"       # EFFECT_TYPES: icon, timer, expiry; no numbers
GRADE_EPISODE_REFUSED = "episode-refused"   # EFFECT_TYPES but resolve_duration refuses
GRADE_NOTHING = "nothing"


def census(records, hand, rank=12):
    """{skill_id: grade}, what the server resolves for each corpus row TODAY.

    `effects.applies_effect` decides the episode; `effects.resolve_duration` at
    `rank` decides whether that episode would actually apply (FINDINGS 12/13's
    refusals). A hand row wins over both: it is the one tier that acts.
    """
    import effects
    out = {}
    for sid, rec in records.items():
        if sid in hand:
            out[sid] = GRADE_MODELLED
            continue
        if effects.applies_effect(rec):
            try:
                effects.resolve_duration(rec, rank)
                out[sid] = GRADE_EPISODE
            except Exception:                                   # noqa: BLE001
                out[sid] = GRADE_EPISODE_REFUSED
            continue
        out[sid] = GRADE_NOTHING
    return out


def census_by_type(records, grades, report=None):
    """type_code -> Counter(n, modelled, episode-only, episode-refused, nothing,
    with_slot, SERVED, RECOGNISED, UNPARSED, NO_SLOT)."""
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
    a = ap.parse_args(argv)

    records, texts, ix, exe, why = load_corpus(a.exe, a.dat)
    print(f"client: {exe}\n        ({why})\n")
    mapping = shifted(by=a.shift) if a.shift else SLOT_FIELD
    if a.shift:
        print(f"KNOWN-BAD ARM: mapping shifted by {a.shift}: {mapping}\n")
    hand = hand_rows()
    rep = analyse(records, texts, hand, mapping)
    print(f"{rep['n_rows']} corpus rows, {rep['n_with_slot']} with a %strN% slot, "
          f"{rep['n_slot_occurrences']} slot occurrences")
    print(f"verdicts: {rep['verdicts']}")
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
        grades = census(records, hand)
        cbt = census_by_type(records, grades, rep)
        print("== coverage census (what the server resolves today) ==")
        rows = []
        for code in sorted(cbt):
            t = cbt[code]
            rows.append((code, names[code], t["n"], t[GRADE_MODELLED], t[GRADE_EPISODE],
                         t[GRADE_EPISODE_REFUSED], t[GRADE_NOTHING], t["with_slot"],
                         t["SERVED"], t["RECOGNISED"], t["UNPARSED"]))
        tot = collections.Counter()
        for t in cbt.values():
            tot.update(t)
        rows.append(("all", "", tot["n"], tot[GRADE_MODELLED], tot[GRADE_EPISODE],
                     tot[GRADE_EPISODE_REFUSED], tot[GRADE_NOTHING], tot["with_slot"],
                     tot["SERVED"], tot["RECOGNISED"], tot["UNPARSED"]))
        _print_table(("type", "name", "n", "modelled", "episode", "ep-refused", "nothing",
                      "slot", "SERVED", "RECOG", "UNPARSED"), rows)
        print()

    if a.hand:
        print("== the hand rows against the parse ==")
        for r in rep["hand"]:
            if r[-1] != "AGREE":
                print("   ", r)
        print(f"   {rep['hand_summary']}\n")

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
            norm = normalise(texts[sid])
            print(f"== {sid}  type {rec['type_code']}  args {rec['skill_arguments']}  "
                  f"scale {rec['scale0']}/{rec['scale15']}  bonus {rec['bonus_scale0']}/"
                  f"{rec['bonus_scale15']}  duration {rec['duration0']}/{rec['duration15']}")
            for (n, b, af), (_, label, detail) in zip(parse_slots(norm), parse_row(texts[sid])[0]):
                v = referee_slot(n, rec, mapping)
                print(f"   str{n} -> {v[1]} {v[0]} {v[2]}/{v[3]}  {label}{':' + detail if detail else ''}")
                print(f"        ...{b[-32:]!r} [] {af[:32]!r}")
            print(f"   flags: {sorted(rep['rows'][sid]['flags'])}")
            if sid in hand:
                print(f"   hand: {referee_hand_row(parse_row(texts[sid])[0], hand[sid])}")
        print()

    if a.label:
        want_label, _, want_detail = a.label.partition(":")
        print(f"== slot windows labelled {a.label} ==")
        n_shown = 0
        for sid in sorted(records):
            norm = normalise(texts[sid])
            for (n, b, af), (_, label, detail) in zip(parse_slots(norm), parse_row(texts[sid])[0]):
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
            norm = normalise(texts[sid])
            for (n, b, af), (_, label, detail) in zip(parse_slots(norm), parse_row(texts[sid])[0]):
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
    ix.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
