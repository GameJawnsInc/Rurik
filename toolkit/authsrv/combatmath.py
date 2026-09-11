"""Armour and the swing arithmetic -- how much a hit takes off, and how often.

Lifted out of `authsrv.py` on 2026-09-11 (REFACTOR-A12). The arithmetic, the
wiki citations and the two measurement banners below are the same lines, in the
same order, that sat in `authsrv.py` between the CREATURE ARMOUR banner and
`swing_damage`; `authsrv.py` re-exports every name here, and every caller in the
server still reaches them by bare name through that re-export. This is where
they live, not a second way to call them.

WHAT STAYED BEHIND, AND WHY THE PARAMETERS ARE SHOUTED. Five constants could not
travel. `ARMOUR_DIVISOR`, `ARMOR_RATING_MODIFIER`, `ARMOR_VS_TYPE_MODIFIER`,
`CRITICAL_ARMOUR_REDUCTION` and `CRITICAL_RATE_BY_RANK` sit inside one
contiguous commented block in `authsrv.py`, next to `ARMOUR_TERM` and
`SPELL_ARMOUR`, which `main()` rebinds with `global` and so cannot move at all --
and that block's own comment warns that its 20.0 and its 40.0 are ONE statement
(`2^(20/40) = sqrt(2)`) that must not drift apart, so it was not cut up to free
five lines. Those five, and the `EQUIP_ARMOUR` flag, are PASSED IN at call time
by the wrappers in `authsrv.py`: read there, never bound here, and never given a
default. A default is evaluated once at `def` time and would freeze the flag,
which is the exact bug the wrappers exist to prevent -- `test_mechanics.py` sets
`authsrv.ARMOUR_TERM = False` to get a deterministic base hit, and a frozen copy
of it would read as damage arithmetic drifting rather than as a refactor bug.
The parameters carry those constants' own UPPERCASE names on purpose: it keeps
the moved bodies character for character what they were, and it says at the call
which `authsrv.py` constant fills each slot.

THE CHAIN IS THREADED TO FULL DEPTH. `spell_armour_for` -> `player_spell_armour`
-> `player_armour_at` -> `armour_of_piece` all run inside this module, so a
wrapper on the outermost one alone would be bypassed by the three calls beneath
it; every level takes the flags as arguments and hands them down.

WHERE THE MOVED COMMENTS STILL POINT. They cite `authsrv.py` for the pieces that
stayed there, and those pointers are still true: the ARMOUR TERM derivation
banner and `ARMOUR_TERM`/`SPELL_ARMOUR` themselves; `HIT_FRACTION`, the fallback
a missing weapon word falls back to; and the two import-time binds that call into
this module from over there, `ENEMY_ARMOR_RATING` and `PLAYER_SWING_DAMAGE`.

Standard library only, and no import of `authsrv`: the server runs as
`__main__`, so importing it back would load a second copy whose flags `main()`
never set.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents  # noqa: E402


# ---- CREATURE ARMOUR, derived from the level and profession we already hold --
#
# WIKI (GWW, "Armor rating", rev. 2026): "The armor rating for creatures in PvE
# is dependent on level where the actual armor rating can be typically
# calculated by (creature AR = 3 * Level + Armor bonus), where armor bonus is
# profession specific." The same page states the baseline this repo's own
# measurement already assumes -- "Having 60 armor rating is regarded as the
# baseline" -- and its damage-multiplier table CORROBORATES the divisor the
# Isle measured from the opposite direction: AR 0 -> 2.828, AR 20 -> 2.000,
# AR 60 -> 1.000, AR 100 -> 0.500, which is 2^((60-AR)/40) to three decimals.
# Wire and wiki agreeing here is two independent observers, not one.
#
# THE PROFESSION BONUS IS READ OFF THE WIKI'S OWN MAX-AR COLUMN, not guessed:
# (GWW, "Basic armor", rev. 2026) gives level-20 maxima of Warrior 80, Ranger
# 70, Assassin 70, Dervish 70, Paragon 80 and 60 for the rest, and 3*20 = 60,
# so the bonus is that column minus 60. Warrior's is also visible on our own
# armour rows as `Armor +20 (vs. physical damage)` -- the wiki says Warrior
# armour is "25...80" with that bonus, and our five starter pieces decode to
# exactly 25 and +20 (studies/itemmods). Player observation and ArenaNet's own
# wire agreeing, from sources sharing no ancestry.
#
# THIS REPLACES A PICKED 60. That number sat here for one commit and was
# level-20 armour on a level-1 creature -- the wrong SHAPE, the same failure
# studies/monsterai section 3.3 records for reach, where one global number was
# wrong in kind rather than in value.
ARMOR_BONUS_BY_PROFESSION = {1: 20, 2: 10, 7: 10, 10: 10, 9: 20}


def creature_armor_rating(npc, override=None):
    """AR for a creature, from its own level and profession. WIKI-sourced.

    `override` wins when a content row declares one, because the same wiki page
    says many PvE creatures do not follow the formula -- but an override is a
    measurement about one creature and should say where it came from.
    """
    if override is not None:
        return float(override)
    if not npc or npc.get("level") is None:
        return None
    bonus = ARMOR_BONUS_BY_PROFESSION.get(npc.get("profession"), 0)
    return float(3 * int(npc["level"]) + bonus)


# ---- THE PLAYER'S OWN ARMOUR, which nothing read until 2026-08-20 ----------
#
# Five pieces went out carrying `Armor: 25` and `Armor +20 (vs. physical
# damage)` -- decoded, screen-verified, byte-identical to nine retail sightings
# each -- and every incoming swing ignored all of it. This closes that.
#
# ARMOUR IS PER-LOCATION, NOT A TOTAL, and the wiki is blunt about it:
# WIKI (GWW, "Armor rating", rev. 2026) -- "Each piece of armor protects only
# one part of a character: a character with 4 pieces with AR 80 and headgear
# with AR 40 will take double damage any time they take a hit to the head; they
# will not have AR 360." Summing our five 25s to 125 would be the single most
# natural wrong thing to do here, so it is named.
#
# THE ODDS ARE PUBLISHED, and they are not uniform. Same page: chest 3/8, legs
# 2/8, and feet, hands and head 1/8 each -- "Armor costs and bonuses reflect
# this, with the material costs and insignia bonuses typically tripled for the
# chest and doubled for the legs", which is the wiki checking its own table
# against the game's economy.
HIT_LOCATION_ODDS = (
    # (content key, weight out of 8)
    ("warrior_body", 3),      # chest
    ("warrior_legs", 2),      # legs
    ("warrior_boots", 1),     # feet
    ("warrior_gloves", 1),    # hands
    ("warrior_head", 1),      # head
)
# The baseline every quoted damage figure is implicitly AT. WIKI, same page:
# "Having 60 armor rating is regarded as the baseline, so a spell that reads
# 'Deals 100 fire damage to target foe' would deal the full 100 damage to a foe
# with 60 armor but only 50 damage to a foe with 100 armor." So an incoming
# figure with no armour context is a figure at AR 60, and any other rating
# scales it by 2^((60-AR)/40) -- which IS the wiki's own damage-multiplier
# table, and `test_agentlife` checks our arithmetic against every row of it.
ARMOR_BASELINE = 60.0
# WIKI (GWW, "Armor calculation" step 2): the Bonus-armour category caps at 25.
BONUS_ARMOUR_CAP = 25.0
# NOT MODELLED, and listed so the gap is a decision rather than an oversight:
# armour PENETRATION (step 3 -- `AR * (1 - pen/100)`, and Lightning Orb's 25%
# is the worked example), insignia, shields, and every skill-driven armour
# effect. None of them exists in this server yet.
#
# ONE THING ON THAT PAGE IS A THIRD WITNESS FOR SOMETHING WE ALREADY SHIP:
# it lists CRITICAL HITS under "Special armor" PENALTIES -- i.e. retail models
# a critical as an armour reduction on the target, which is exactly the shape
# `studies/isle` measured from 495 damage events (AR-20, since 2^(20/40) is
# sqrt(2)) and exactly how `swing_damage` implements it. Three independent
# sources -- the wire, the damage-multiplier table, and this categorisation.


def armour_of_piece(item, physical, ARMOR_RATING_MODIFIER,
                    ARMOR_VS_TYPE_MODIFIER):
    """(rating, vs_physical_bonus) from a piece's own modifier words, or None.

    Identifier 572's argument is the rating and 527's is the "+N vs. <type>"
    bonus, whose type comes from the companion word -- identifier 4 resolves to
    the string `vs. physical damage` (studies/itemmods 2). Lazy import and
    fail-soft, the same shape as weapon_damage_range.
    """
    try:
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "clientscan"))
        import itemmods                                   # noqa: PLC0415
    except Exception:                                     # noqa: BLE001
        return None
    rating = bonus = None
    for word in (item or {}).get("modifiers", []):
        d = itemmods.decode(word)
        if d["skipped_high"] or d["skipped_bit18"]:
            continue
        if d["identifier"] == ARMOR_RATING_MODIFIER:
            rating = d["arg"]
        elif d["identifier"] == ARMOR_VS_TYPE_MODIFIER:
            bonus = d["arg"]
    if rating is None:
        return None
    return (float(rating), float(bonus or 0.0) if physical else 0.0)


def player_armour_at(location_key, physical, EQUIP_ARMOUR,
                     ARMOR_RATING_MODIFIER, ARMOR_VS_TYPE_MODIFIER):
    """The player's effective AR at one body location, or None if unarmoured."""
    if not EQUIP_ARMOUR:
        return None
    try:
        piece = agents.item_template(location_key)
    except Exception:                                     # noqa: BLE001
        return None
    got = armour_of_piece(piece, physical, ARMOR_RATING_MODIFIER,
                          ARMOR_VS_TYPE_MODIFIER)
    if got is None:
        return None
    rating, bonus = got
    return rating + bonus_armour(bonus)


def player_spell_armour(EQUIP_ARMOUR, ARMOR_RATING_MODIFIER,
                        ARMOR_VS_TYPE_MODIFIER):
    """The ONE rating an incoming armour-respecting spell resolves against.

    ELEMENTAL -- `physical=False`, so the pieces' `+20 vs. physical damage`
    does not reach a fire spell (WIKI, GWW "Damage calculation" sec. Example
    of armor effect: the Elementalist's `+10 vs. Elemental` counts against a
    physical attack for nothing, and the Warrior's +20 vs. physical the same
    way for a spell). Today every piece this server equips reads 25 elemental
    and 45 physical (content/items.toml, identifier 572 + 527), so a single
    rating and a location roll are byte-identical on the wire; what differs
    is the claim, and the corpus's is the single value (studies/skills 43).

    IF THE FIVE PIECES EVER DISAGREE, this takes the CHEST'S -- the most
    likely location under the wiki's own odds -- and says so on stdout once
    per session, because which rating a spell scales against on a lopsided
    set is exactly the thing no capture has yet measured (43.5). None when
    the player is unarmoured, and the caller then deals the stated amount.
    """
    ratings = {}
    for key, _w in HIT_LOCATION_ODDS:
        ar = player_armour_at(key, False, EQUIP_ARMOUR,
                              ARMOR_RATING_MODIFIER,
                              ARMOR_VS_TYPE_MODIFIER)
        if ar is not None:
            ratings[key] = ar
    if not ratings:
        return None
    if len(set(ratings.values())) > 1 and not _SPELL_ARMOUR_WARNED:
        _SPELL_ARMOUR_WARNED.append(True)
        print("SPELL ARMOUR: the five pieces disagree elementally "
              f"{ratings}; a spell resolves against the CHEST's rating "
              "-- UNVERIFIED which one retail uses on a lopsided set "
              "(studies/skills 43.5)", flush=True)
    chest = HIT_LOCATION_ODDS[0][0]
    return ratings.get(chest, next(iter(ratings.values())))


_SPELL_ARMOUR_WARNED = []


def spell_armour_for(skill_id, SPELL_ARMOUR, ARMOUR_TERM,
                     ARMOUR_RESPECTING_MEANS, SCALE_MEANS_DAMAGE,
                     EQUIP_ARMOUR, ARMOR_RATING_MODIFIER,
                     ARMOR_VS_TYPE_MODIFIER):
    """The rating an incoming cast of `skill_id` scales by, or None (unscaled).

    None means "deal the stated amount": the label is armour-ignoring, or
    the term is off, or the player wears nothing. Read from the same
    `skill_effect` row `skill_damage` reads, so a skill that resolves no
    damage there resolves no armour here either.
    """
    if not (SPELL_ARMOUR and ARMOUR_TERM):
        return None
    try:
        row = agents.WORLD.get("skill_effect", str(skill_id))
    except Exception:                                     # noqa: BLE001
        return None
    if row.get("scale_means") not in ARMOUR_RESPECTING_MEANS:
        return None
    if SCALE_MEANS_DAMAGE.get(row.get("scale_means")) != "standalone":
        return None
    return player_spell_armour(EQUIP_ARMOUR, ARMOR_RATING_MODIFIER,
                               ARMOR_VS_TYPE_MODIFIER)


def bonus_armour(net):
    """The Bonus-armour category's contribution, WITH its documented cap.

    WIKI (GWW, "Armor calculation", rev. 2026) step 2: "If the net Bonus is 26
    or above, add 25 armor or the highest flat bonus provided by a single
    effect (if higher than 25). ... If the net Bonus is 25 or lower, add that
    value." Our armour's `+20 vs. physical` is 20, so the cap does not bite
    today and this function is currently the identity -- which is exactly why
    it is written down now rather than discovered later by a stack of bonuses
    that silently over-counted.

    AND ONE AMBIGUITY, RECORDED RATHER THAN RESOLVED SILENTLY. The same page
    puts "Inherent mods" in Bonus armour while GWW's "Basic armor" page prints
    the Warrior's `Armor +20 (vs. physical damage)` as part of BASIC (Core)
    armour. Core is uncapped, Bonus is capped at 25 -- so the two readings
    disagree only above 25, and at our +20 they give the same number. If a
    second bonus ever lands on a piece, this is the line to settle first.
    """
    return float(net) if net <= BONUS_ARMOUR_CAP else float(BONUS_ARMOUR_CAP)


def roll_hit_location():
    """Which piece an incoming attack lands on. WIKI odds, our RNG."""
    total = sum(w for _k, w in HIT_LOCATION_ODDS)
    pick = random.randrange(total)
    for key, weight in HIT_LOCATION_ODDS:
        if pick < weight:
            return key
        pick -= weight
    return HIT_LOCATION_ODDS[0][0]


def armour_multiplier(armour, ARMOUR_DIVISOR):
    """How much of a baseline hit lands against `armour`. WIKI's own table."""
    return 2.0 ** ((ARMOR_BASELINE - float(armour)) / ARMOUR_DIVISOR)


# ---- WEAPON DAMAGE, and it is the first number in this block that is NOT ours
#
# The paragraph above says "the wiki documents attack rates and weapon damage,
# and a captured fight would give the real thing". Neither was needed. A weapon
# carries its own damage range in the item ArenaNet sends, and on 2026-08-20
# `studies/itemmods` decoded the words: identifier 584, `arg` the MAXIMUM and
# `arg2` the minimum. Our hammer's 0xA4880503 is 584 arg 5 arg2 3, and the
# client's own tooltip draws `Blunt Dmg: 3-5` (20260820T125155) -- which is also
# how the max/min order was settled, because the static read could not.
#
# WHAT IS MEASURED AND WHAT IS STILL OURS, because this replaces one invented
# number with a measured one and not with a damage model:
#   MEASURED   the range itself -- ArenaNet's own word for our own weapon
#   OURS       the roll inside it (uniform), and every term Guild Wars puts
#              around it: no armour reduction, no attribute-rank scaling, no
#              critical hits. Nothing in this server reads an armour rating
#              even though it now sends five pieces carrying one.
#
# LAZY AND FAIL-SOFT, the same shape as `_build_of_tag` below. `itemmods` lives
# in clientscan and imports `pinned`, and the server must keep working on a
# machine with no client and no vault -- so a failure here falls back to
# HIT_FRACTION, which is what this server did until today.
def weapon_damage_range(item):
    """(min, max) health points from an item's own 584 modifier word, or None."""
    try:
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "clientscan"))
        import itemmods                                   # noqa: PLC0415
    except Exception:                                     # noqa: BLE001
        return None
    for word in (item or {}).get("modifiers", []):
        d = itemmods.decode(word)
        if d["skipped_high"] or d["skipped_bit18"]:
            continue
        if d["identifier"] == itemmods.DAMAGE_RANGE:
            lo, hi = d["arg2"], d["arg"]
            return (lo, hi) if lo <= hi else (hi, lo)
    return None


def attack_strength(rank, level=20):
    """SL -- the attacker's damage level, from its weapon attribute rank."""
    threshold = (level + 4) / 2.0
    if rank <= threshold:
        return 5.0 * rank
    return 5.0 * threshold + 2.0 * (rank - threshold)


def critical_rate(rank, CRITICAL_RATE_BY_RANK):
    """Chance of a critical at `rank`. Measured at 8/9/11/12/13, ours between."""
    ranks = sorted(CRITICAL_RATE_BY_RANK)
    if rank <= ranks[0]:
        return CRITICAL_RATE_BY_RANK[ranks[0]]
    if rank >= ranks[-1]:
        return CRITICAL_RATE_BY_RANK[ranks[-1]]
    lo = max(r for r in ranks if r <= rank)
    hi = min(r for r in ranks if r >= rank)
    if lo == hi:
        return CRITICAL_RATE_BY_RANK[lo]
    a, b = CRITICAL_RATE_BY_RANK[lo], CRITICAL_RATE_BY_RANK[hi]
    return a + (b - a) * (rank - lo) / (hi - lo)


def swing_damage(rank, armour, damage_range, level=20, critical=False,
                 mult=1.0, roll=None, *, ARMOUR_DIVISOR,
                 CRITICAL_ARMOUR_REDUCTION):
    """One swing in health points, armour and criticals included.

    A critical takes the range's MAXIMUM and reduces the target's armour by 20;
    an ordinary swing rolls inside the range at full armour. Returns a float so
    the caller keeps the same `_damage_fraction` guard it always had.
    """
    lo, hi = damage_range
    if critical:
        roll = float(hi)
        armour = armour - CRITICAL_ARMOUR_REDUCTION
    elif roll is None:
        roll = float(random.randint(lo, hi))
    sl = attack_strength(rank, level)
    return max(0.0, round(roll * mult * 2.0 ** ((sl - armour) / ARMOUR_DIVISOR)))
