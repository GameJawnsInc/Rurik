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

AND TWO OF THEM POINT WITH A DIRECTION, which is what this paragraph is for: R7
says a moved comment travels verbatim and the fix for a referent left behind is
a pointer added HERE, never a reword of the line. The WEAPON DAMAGE banner opens
"The paragraph above says ..." -- that paragraph is the `---- the combat loop`
banner over `HIT_FRACTION` in `authsrv.py`, and nothing above it in this file --
and it closes "the same shape as `_build_of_tag` below", which is `authsrv.py`'s
build-tag reader, also still over there. Both lines are the lines that were
there; only their addresses moved, and these are the addresses.

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


def armour_of_piece(item, damage_type, ARMOR_RATING_MODIFIER,
                    ARMOR_VS_TYPE_MODIFIER, met=True, level=None):
    """(rating, vs-type bonus) from a piece's own modifier words, or None.

    Identifier 572's argument is the rating -- or 635's on a REQUIRED shield
    when `met`, and the wiki's 8 / 5 when not (the WEAPONS-W4 block below) --
    or 573's LEVEL-SCALED pair (arg the level-20 rating, arg2 the level-1
    one; `level` is the wearer's, the module's block below) --
    and each 527's is a `+N vs. <condition>` line that counts only when the
    SPECIAL word right before it admits `damage_type`: an id from the
    client's fourteen (content/world.toml [damage_type.table]) or a class
    name, "physical" / "elemental" / "other". Identifier 4 is `vs. physical
    damage`, 3 `vs. elemental damage`, 5 `vs. <the named type> damage`
    (studies/itemmods 2; the corpus's pieces carry 4 or 3 and nothing else,
    400 of 400). WEAPONS-W4 (2026-09-19): this used to take a `physical`
    boolean and read every 527 as "vs. physical". Lazy import and fail-soft,
    the same shape as weapon_damage_range.
    """
    try:
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "clientscan"))
        import itemmods                                   # noqa: PLC0415
    except Exception:                                     # noqa: BLE001
        return None
    rating = None
    bonus = 0.0
    pending = None
    for word in (item or {}).get("modifiers", []):
        d = itemmods.decode(word)
        if d["skipped_high"] or d["skipped_bit18"]:
            continue
        ident = d["identifier"]
        if ident in CONDITION_IDENTIFIERS:
            pending = (ident, d["arg"], d["arg2"])       # qualifies the NEXT line
            continue
        if ident == ARMOR_RATING_MODIFIER:
            rating = float(d["arg"])
        elif ident == LEVEL_SCALED_ARMOUR:
            rating = level_scaled_rating(d["arg2"], d["arg"], level)
        elif ident == SHIELD_ARMOUR_REQUIRED:
            rating = (float(d["arg"]) if met
                      else UNMET_SHIELD_ARMOUR[int(d["arg"]) >= 16])
        elif ident == ARMOR_VS_TYPE_MODIFIER and condition_applies(pending, damage_type):
            bonus += float(d["arg"])
        pending = None
    if rating is None:
        return None
    return (rating, bonus)


# ---- THE ENERGY THE ARMOUR GIVES (DAGGERS-F15) --------------------------------
#
# Two more identifiers on the pieces the owner's level-3 Assassin wore
# (20260819T132414): 556 arg 5 on the chest, 558 arg 1 on the boots and on the
# legs. Their tooltip lines resolve through text ids 2071 and 2072, which this
# server does not read; what it CAN check is the arithmetic. WIKI (GWW
# "Energy"): every profession starts from 20 energy and 2 pips, and the
# Assassin's armour brings "+5 / +2" -- 20 + 5 and 2 + 1 + 1. The same
# character ran property 43 at wire_regen_rate(4, 25) on retail. So 556 is
# "+N energy" and 558 is "+N energy recovery", CORROBORATED by two arithmetic
# coincidences that had no reason to hold. The Warrior fixture's pieces carry
# neither word, and its 25 / 3 pool is the Ranger row (pools.py) -- typed in
# before any of this was read, and left alone: the check below runs only for
# a party row that names its armour.
ENERGY_BASE, PIPS_BASE = 20, 2
ENERGY_MODIFIER, ENERGY_REGEN_MODIFIER = 556, 558


def armour_energy_bonus(keys):
    """(energy, pips) the worn pieces add, summed over their 556 / 558 words.
    None when the decoder is unavailable (a bare machine)."""
    try:
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "clientscan"))
        import itemmods                                   # noqa: PLC0415
    except Exception:                                     # noqa: BLE001
        return None
    energy = pips = 0
    for key in keys:
        for word in agents.item_template(key).get("modifiers", []):
            d = itemmods.decode(word)
            if d["skipped_high"] or d["skipped_bit18"]:
                continue
            if d["identifier"] == ENERGY_MODIFIER:
                energy += int(d["arg"])
            elif d["identifier"] == ENERGY_REGEN_MODIFIER:
                pips += int(d["arg"])
    return energy, pips


def player_armour_at(location_key, damage_type, EQUIP_ARMOUR,
                     ARMOR_RATING_MODIFIER, ARMOR_VS_TYPE_MODIFIER, level=None):
    """The player's effective AR at one body location against `damage_type`
    (an id or a class name -- armour_of_piece), or None if unarmoured;
    `level` is the wearer's, for a 573 piece."""
    if not EQUIP_ARMOUR:
        return None
    try:
        piece = agents.item_template(agents.worn_piece_key(location_key))
    except Exception:                                     # noqa: BLE001
        return None
    got = armour_of_piece(piece, damage_type, ARMOR_RATING_MODIFIER,
                          ARMOR_VS_TYPE_MODIFIER, level=level)
    if got is None:
        return None
    rating, bonus = got
    return rating + bonus_armour(bonus)


def player_spell_armour(EQUIP_ARMOUR, ARMOR_RATING_MODIFIER,
                        ARMOR_VS_TYPE_MODIFIER, location_key=None,
                        damage_type="elemental"):
    """The rating an incoming armour-respecting spell resolves against --
    against `damage_type`, the spell's OWN (a type id from the client's
    fourteen, or a class name; "elemental" for a spell with no type read,
    the reading every run before 2026-09-19 made for all of them).

    SKILLS-LR (2026-09-17, studies/skills 50): WITH A `location_key` IT IS
    THAT PIECE'S -- a spell rolls a hit location like an attack. OBSERVED on
    the owner's Isle tape 20260917T090355: head, hands and feet off, one
    Lightning Orb from one caster lands for 101 (an armoured piece) and 286
    (a bare one), 2^(60/40) apart, where five equal pieces gave 101 four
    times of four. A location that wears nothing while others do is rated
    0.0, which is what 286 / 101 says. Without a key this is the pre-LR
    reading below, kept as `--no-spell-location-roll`'s arm and REFUTED as
    a claim about retail.

    ELEMENTAL -- damage_type "elemental", so the pieces' `+20 vs. physical
    damage` does not reach a fire spell (a `+N vs. elemental` would, since
    WEAPONS-W4) (WIKI, GWW "Damage calculation" sec. Example
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
        ar = player_armour_at(key, damage_type, EQUIP_ARMOUR,
                              ARMOR_RATING_MODIFIER,
                              ARMOR_VS_TYPE_MODIFIER)
        if ar is not None:
            ratings[key] = ar
    if not ratings:
        return None
    if location_key is not None:
        return ratings.get(location_key, 0.0)
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
                     ARMOR_VS_TYPE_MODIFIER, SPELL_LOCATION_ROLL=False,
                     damage_type="elemental"):
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
    return player_spell_armour(
        EQUIP_ARMOUR, ARMOR_RATING_MODIFIER, ARMOR_VS_TYPE_MODIFIER,
        location_key=roll_hit_location() if SPELL_LOCATION_ROLL else None,
        damage_type=damage_type)


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
# WEAPONS-C7 (2026-09-18): a weapon WITH a 633 requirement carries its range as
# 634 (max, min) and NO 584 -- an exact partition over every weapon-typed item in
# the live corpus (sword 233 / 229, bow 99 / 32 ..., not one item in both). This
# reader knew 584 only, so a retail-shaped required weapon read as rangeless.
# The UNMET case is still unmodelled by decision (studies/isle; WEAPONS-Q10).
DAMAGE_RANGE_REQUIRED = 634


def weapon_damage_range(item):
    """(min, max) health points from an item's own 584 (or, on a weapon with a
    requirement, 634) modifier word, or None."""
    try:
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "clientscan"))
        import itemmods                                   # noqa: PLC0415
    except Exception:                                     # noqa: BLE001
        return None
    rng, percent = None, None
    for word in (item or {}).get("modifiers", []):
        d = itemmods.decode(word)
        if d["skipped_high"] or d["skipped_bit18"]:
            continue
        if d["identifier"] in (itemmods.DAMAGE_RANGE, DAMAGE_RANGE_REQUIRED) and rng is None:
            lo, hi = d["arg2"], d["arg"]
            rng = (lo, hi) if lo <= hi else (hi, lo)
        elif d["identifier"] == CUSTOMISED:
            percent = d["arg"]
    if rng is None:
        return None
    if percent:
        # WEAPONS-W8: the customisation word scales the RANGE, integer ends --
        # the isle's "Damage +20%" sword rolled 18..26 on a 15-22 range.
        rng = (int(rng[0] * percent // 100), int(rng[1] * percent // 100))
    return rng


# WEAPONS-W8 (2026-09-19): modifier 585 is the CUSTOMISATION word, its arg the
# percentage (120 = "Damage +20%"). CORROBORATED by two witnesses that do not
# share a source: (1) studies/isle/FINDINGS.md records the operator's PvP Sword
# as `Damage +20%, customized` from its own tooltip, and the corpus's copy of
# that item (205 on the 20260821 tapes) carries (585, 120, 0); (2) across all 29
# live captures 85 items carry the word, every one at 120, and all but one are
# the owner's own weapons (own weapon set or a player's 0x006E) -- no hostile's
# item has it (RUN-WEAPONS-1A, studies/weapons/PLAN.md section 26). The client's
# own parser (clientscan/itemmods.py) does not name it, so this is not OBSERVED
# from the binary. The isle study's fit ("an integer roll over the customized
# range 18..26 reproduces ... exactly") is what fixes the arithmetic to the
# range's ends rather than to the final number.
CUSTOMISED = 585


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
                 mult=1.0, roll=None, strike_level=None, *, ARMOUR_DIVISOR,
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
    # WEAPONS-W4c: a caller that knows the strike level hands it in (a wand or
    # staff: 3 x the character's level, no mastery); everyone else's is the
    # weapon attribute's, with the level threshold.
    sl = attack_strength(rank, level) if strike_level is None else float(strike_level)
    return max(0.0, round(roll * mult * 2.0 ** ((sl - armour) / ARMOUR_DIVISOR)))


# ---- WEAPONS-W4 (2026-09-19): THE DAMAGE TYPE, THE vs-TYPE ARMOUR, THE REQUIREMENT
#
# THE ENUM IS THE CLIENT'S OWN. Identifier 587's argument, 0x00A7's kind field
# and the `vs. %str1% damage` condition (special identifier 5) index ONE
# fourteen-entry table, `s_charDamage` (ConstChar.cpp, `damage <
# arrsize(s_charDamage)`), through accessors guarded by `< 14`; the item
# accessor's default with no 587 word is 14 (0x008451C6). content/world.toml's
# [damage_type.table] carries the string ids (0 Blunt, 1 Piercing, 2 Slashing,
# 3 Cold, 4 Lightning, 5 Fire, 6 Chaos, 7 Dark, 8 Holy, 9 Nature, 10 Sacrifice,
# 11 Earth, 12 Generic, 13 = 7 again) and [damage_type.classes] the wiki's
# grouping -- physical 0 / 1 / 2, elemental 3 / 4 / 5 / 11, the rest neither.
# OBSERVED on the corpus (3,857 items over 96 connections): bows, daggers and
# spears carry 1, hammers 0, swords and axes 2 (18 swords 5), wands and staves
# 3..8 and 11; no item carries 9, 10, 12 or 13.
#
# A 527 `Armor +N` line is qualified by the SPECIAL word right BEFORE it --
# (572, 4, 527) on 345 pieces and (572, 3, 527) on 55, the corpus's only two
# shapes on a worn piece: 4 renders "vs. physical damage" (string 2480), 3
# "vs. elemental damage" (2477), 5 "vs. %str1% damage" with the type's name
# (2476; on no item in the corpus), and 9..20 are situational ("while
# attacking", "while in a Stance", ...) and are NOT modelled: a 527 under one
# of those adds nothing here, said once. The rule that a bonus counts against
# the types its condition names is the wiki's (GWW "Damage type", "Armor
# rating"); the client has no reader for 527 (itemmods --reads 527: the
# tooltip only), so the server is the only place it can be true or false.
#
# THE REQUIREMENT is identifier 633 {attribute, rank} (studies/itemmods 5). A
# required weapon carries its range as 634, a required shield its armour as
# 635 and a required focus its energy as 636 -- an exact partition on the
# corpus (weapons 634 only; 286 shields 635 only; 20 foci 636 only; 510 staves
# 556 + 634, the energy ungated). UNMET: the weapon's damage divides by 3.098
# -- OBSERVED on the isle's rank ladder (studies/isle/FINDINGS.md 9.2: one
# hammer at ranks 5..8, 235 events, per-block divisors 3.073..3.133, the
# naive 3 and 10/3 both excluded). A divisor on the rank-appropriate damage is
# ONE of the two parameterisations that ladder admits (the other a strike-level
# drop); both give those four numbers, RUN-WEAPONS-3 separates them, and the
# number ships because it reproduces four independent blocks within 1.1 %
# where the wiki's "approximately two-thirds" is the same claim with fewer
# digits. A shield's armour falls to 8 (a 16-armour shield) or 5 (below 16)
# and a focus's energy to +3 -- WIKI (GWW "Requirement" sec. Drawbacks, read
# 2026-09-19), the not-randomly-generated arm of each rule, because every item
# this server hands out is made, never dropped.
DAMAGE_TYPE_MODIFIER = 587
VS_ELEMENTAL, VS_PHYSICAL, VS_NAMED_TYPE = 3, 4, 5
CONDITION_IDENTIFIERS = frozenset(range(1, 21))
REQUIREMENT_MODIFIER = 633
SHIELD_ARMOUR_REQUIRED = 635
ENERGY_REQUIRED = 636
DAMAGE_TYPE_NONE = 14
UNMET_REQUIREMENT_DIVISOR = 3.098
UNMET_SHIELD_ARMOUR = {True: 8.0, False: 5.0}      # rating >= 16 -> 8, else 5
UNMET_FOCUS_ENERGY = 3
_CONDITION_WARNED = []


def word_fields(word):
    """(identifier, arg, arg2) of one modifier word by the client walker's own
    layout (bits 29-20 / 17-8 / 7-0), or None for a word it skips (bits 31-30
    == 3, or bit 18) -- pure arithmetic, so it works on a bare machine."""
    w = int(word) & 0xFFFFFFFF
    if (w >> 30) & 3 == 3 or (w >> 18) & 1:
        return None
    return (w >> 20) & 0x3FF, (w >> 8) & 0x3FF, w & 0xFF


def item_words(item):
    return [f for f in map(word_fields, (item or {}).get("modifiers", ())) if f]


def item_damage_type(item):
    """The 587 argument, or None when the item carries no type line."""
    for ident, arg, _a2 in item_words(item):
        if ident == DAMAGE_TYPE_MODIFIER:
            return int(arg)
    return None


def damage_class(damage_type):
    """'physical' / 'elemental' / 'other' for a type id; a class name passes
    through; None for no type (None, or the accessor's 14)."""
    if damage_type in ("physical", "elemental", "other"):
        return damage_type
    if damage_type is None or int(damage_type) == DAMAGE_TYPE_NONE:
        return None
    classes = agents.WORLD.get("damage_type", "classes")
    d = int(damage_type)
    if d in classes["physical"]:
        return "physical"
    if d in classes["elemental"]:
        return "elemental"
    return "other"


def damage_type_label(damage_type):
    """A one-word tag for a banner: the class name, or the table's label."""
    if damage_type in ("physical", "elemental", "other"):
        return damage_type
    if damage_type is None or int(damage_type) == DAMAGE_TYPE_NONE:
        return "untyped"
    labels = agents.WORLD.get("damage_type", "table")["labels"]
    d = int(damage_type)
    return labels[d] if 0 <= d < len(labels) else f"type {d}"


def condition_applies(condition, damage_type):
    """Does a 527's condition word admit this damage type? No condition: yes.
    4 / 3: the wiki's class. 5: that one named type. A situational condition
    (9..20): no, and said once per identifier."""
    if condition is None:
        return True
    ident, arg, _a2 = condition
    cls = damage_class(damage_type)
    if ident == VS_PHYSICAL:
        return cls == "physical"
    if ident == VS_ELEMENTAL:
        return cls == "elemental"
    if ident == VS_NAMED_TYPE:
        return (damage_type is not None and not isinstance(damage_type, str)
                and int(damage_type) == int(arg))
    if ident not in _CONDITION_WARNED:
        _CONDITION_WARNED.append(ident)
        print(f"ARMOUR: a +N line under condition identifier {ident} (situational) "
              f"is not modelled and adds nothing [WEAPONS-W4]", flush=True)
    return False


def weapon_requirement(item):
    """(attribute, rank) from the item's 633 word, or None."""
    for ident, arg, arg2 in item_words(item):
        if ident == REQUIREMENT_MODIFIER:
            return int(arg), int(arg2)
    return None


def requirement_met(item, rank_of):
    """True when the item has no 633 or the rank in its attribute reaches the
    requirement; `rank_of` is a mapping {attribute: rank} or a callable."""
    req = weapon_requirement(item)
    if req is None:
        return True
    attribute, rank = req
    have = (rank_of.get(attribute, 0) if hasattr(rank_of, "get")
            else rank_of(attribute))
    return have is not None and int(have) >= rank


# ---- WEAPONS-W5b (2026-09-19): A STAFF'S 570 -- "HALVES SKILL RECHARGE OF SPELLS"
#
# THE WORD, OBSERVED: identifier 570 sits on 518 of the corpus's staves and on
# nothing else (aw_570census, 96 connections) -- (arg, arg2) = (16, 1) x333,
# (17, 1) x104, (15, 1) x53, (14, 1) x18, (10, 1) x8, (20, 0) x2 -- and the
# tooltip handler (0x009260A2) renders `arg` through 2439 `%str1%: %num1%%%`
# under 2376 `Chance` and the line 2432 `Halves %str1% of spells` with 2392
# `skill recharge`: "Halves skill recharge of spells (Chance: 16%)". `arg2`
# only picks a display-record variant (both read the same), unread further.
# GWW "Staff": "Halves skill recharge of spells (Chance: 10...20%)", an
# inherent property of nearly every staff -- the corpus's 10..20.
#
# THE RULE IS WIKI, and NO tape can witness it: no observing player and no
# hero ever cast a spell holding a staff (the JARIN hero held a sword; the
# players' leads were wands, bows, hammers, swords, daggers). GWW "HSR" (read
# 2026-09-19): it "affects only spells"; a staff's inherent one maxes at 20 %,
# an inscription's at 10 %, a wand's or focus's attribute-specific one at
# 20 %; "capped at 50%, i.e. the skill recharge time ... can only be halved at
# best". GWW "Recharge time": the recharge "is calculated as the skill
# finishes activating"; "effects that alter recharge time round to the
# nearest second". So: rolled at the completion, on a spell, each 570 held its
# own trigger, any success a halving, the halved value rounded to the nearest
# whole second (a .5 rounds UP -- RECONSTRUCTION, the wiki does not say which
# way). "Spell" is the client's own type column (studies/skills 35.3, the
# namer's words): 4 Hex Spell, 5 Spell, 6 Enchantment Spell, 9 Well Spell, 11
# Ward Spell, 24 Item Spell, 25 Weapon Spell -- GWW "Skill type" lists exactly
# those six subtypes under Spell. The attribute-specific wand / focus form is
# not on any corpus item and is not modelled; the generic inscription would
# be a 570 on a non-staff and reads the same way here.
HALF_RECHARGE_MODIFIER = 570
SPELL_TYPE_CODES_HSR = frozenset({4, 5, 6, 9, 11, 24, 25})


def half_recharge_chances(items):
    """The chance (percent) of every 570 word among `items`, in order."""
    out = []
    for item in items:
        for ident, arg, _a2 in item_words(item):
            if ident == HALF_RECHARGE_MODIFIER:
                out.append(int(arg))
    return out


def is_spell_type(type_code):
    try:
        return int(type_code) in SPELL_TYPE_CODES_HSR
    except (TypeError, ValueError):
        return False


def halved_recharge(seconds):
    """Half of a whole-second recharge, to the nearest second, .5 up."""
    return int(float(seconds) / 2.0 + 0.5)


# ---- IDENTIFIER 573 (2026-09-19): "Armor: N (depends on level)" -- A HERO'S PIECE
#
# THE WORD, OBSERVED: 573 sits on twenty corpus pieces and nothing else -- one
# five-piece set (types 4 / 7 / 13 / 16 / 19, models 17977..17980 and 19012),
# always (573, 80, 23) followed by (4, 527 20), created into inventory key 5
# behind 0x015A ITEM_SET_PROFESSION [.., item, 1] on the JARIN hero tape
# (20260914T005758, three connections) and the aggro tape (20260916T150306):
# the Warrior hero's armour. Its tooltip handler (0x009240F4): with a level in
# the walker context (+0x24) it draws 2438 `Armor: N` with
# N = arg2 + (arg - arg2) * X / 10, else 2440 `Armor: N-N` with arg2..arg,
# and appends 51163 `depends on level`; so arg2 is the LOW rating and arg the
# HIGH one. What X is (the tooltip's caller) is unread; the SERVER's rule is
# the wiki's and needs no X.
#
# WIKI (GWW "Hero armor" sec. Armor rating, read 2026-09-19): a hero's rating
# "is dependent solely on their profession and level" -- Warrior / Paragon 23
# at level 1 to 80 at 20, Ranger / Assassin / Dervish 13 to 70, the casters 3
# to 60, three per level -- and GWW "Hero": "It is set at an armor rating
# suitable for the hero's level and automatically increases ... with the hero
# level". (80, 23) IS the Warrior row's two ends, and the rating at level L is
# the straight line between them, low + (high - low) * (L - 1) / 19 -- which
# for every corpus pair is 3 * L + 20, the creature formula
# `creature_armor_rating` already uses (3 * level + a profession bonus of 20 /
# 10 / 0 -- the wiki's three rows again). CORROBORATED three ways; the client
# has no reader for 573 outside the tooltip (itemmods --reads 573), so the
# server is where the number lives. Our heroes rate by creature_armor_rating
# and wear no pieces on the wire; this reader makes a content row that carries
# the tape's word rate the same way, at the wearer's level, clamped to 1..20.
LEVEL_SCALED_ARMOUR = 573
HERO_LEVEL_MIN, HERO_LEVEL_MAX = 1, 20


def level_scaled_rating(low, high, level):
    """A 573 piece's rating at `level`: the line from `low` at level 1 to
    `high` at level 20 (the wiki's hero-armour rows are exactly that line).
    No level: the low end, said nowhere better than here -- a caller that
    knows the wearer passes it."""
    lo, hi = float(low), float(high)
    if level is None:
        return lo
    lvl = min(max(int(level), HERO_LEVEL_MIN), HERO_LEVEL_MAX)
    return lo + (hi - lo) * (lvl - HERO_LEVEL_MIN) / float(HERO_LEVEL_MAX - HERO_LEVEL_MIN)


# ---- A SPELL'S OWN DAMAGE TYPE (2026-09-19, studies/weapons/PLAN.md 34) ---------
#
# THE CLIENT HAS NO COLUMN FOR IT. Over all 41 dword columns of the 164-byte
# s_skill record (3,443 named rows) only three range inside the enum's 0..14 --
# +0x08 the campaign, +0x14 the chain mask, +0x58 the argument count -- and
# each is already named; the type sits in the authored description ("deals
# 15...63 fire damage") and nowhere structured. THE WIRE CARRIES IT: a spell's
# projectile arrives (0x00A7, third field) as the SPELL's type, not the held
# weapon's -- Lightning Orb 229 as 4 under an earth staff (587 = 11,
# 20260917T090355, x11), a fire staff (5, 20260917T224104, x11) and a lightning
# wand (x5); Lightning Javelin 230 as 4 under the same two staves (x15);
# Dancing Daggers 858 as 11 (earth) with a hammer (587 = 0, x3) or daggers (1,
# x14) in hand; Fireball 186 as 5 (x35) -- 79 of 79, the held type ruled out
# on 54 (aw_spellkinds3 over the corpus). So the SOURCE for a skill's type is
# its content row: `skill_effect.<id>.damage_type` when a row carries the id,
# else the wiki's own label in `scale_means` / `bonus_scale_means` ("Fire
# damage" -> the [damage_type.table] label "fire" -> 5; "+ Holy damage" -> 8),
# else None. Whether typed damage RESPECTS armour is a separate, per-row fact
# (ARMOUR_RESPECTING_MEANS in authsrv; GWW "Armor-ignoring damage": "This
# property is independent of damage type" -- shadow, most holy and typeless
# skill damage ignore it, elemental spells respect it).
def damage_type_from_label(label):
    """The type id a wiki scale label names -- "Fire damage" 5, "+ Holy damage"
    8, "Cold damage" 3 -- or None for a label that is not "<type> damage"."""
    if not isinstance(label, str):
        return None
    word = label.strip().lower()
    if word.startswith("+"):
        word = word[1:].strip()
    if not word.endswith(" damage"):
        return None
    word = word[:-len(" damage")].strip()
    try:
        labels = list(agents.WORLD.get("damage_type", "table")["labels"])
    except Exception:                                     # noqa: BLE001
        return None
    return labels.index(word) if word in labels else None


def spell_damage_type_of(row):
    """A skill_effect row's own type: its `damage_type`, else the type its
    scale label names, else the bonus label's, else None."""
    if not row:
        return None
    if row.get("damage_type") is not None:
        return int(row["damage_type"])
    for key in ("scale_means", "bonus_scale_means"):
        got = damage_type_from_label(row.get(key))
        if got is not None:
            return got
    return None


# ---- BASE ARMOUR PENETRATION (2026-09-19, studies/weapons/PLAN.md 35) ----------
#
# WIKI (GWW "Armor penetration"): two tiers. BASE penetration is "the
# non-stackable, fixed amount of penetration listed in a skill's description";
# with more than one source "only the highest value is used". Its sources:
# Strength, "1% per rank -- When using attack skills" (GWW "Strength": on
# attack skills "that don't already have a higher amount" -- Penetrating
# Attack "can still be affected with 11 or more Strength"; never a pet attack,
# never a plain swing); Air Magic spells, "25% -- Each one that deals
# lightning damage"; Penetrating Blow / Chop 20 %; Penetrating / Sundering
# Attack 10 %; Spear of Lightning 25 %; the Ritualist's held ashes and
# Sundering Weapon. BONUS penetration ("armor penetration +20%") "does stack
# (adding them together) and add[s] to the largest base": the hornbow's 10 %
# ([bow_class.rules]), a Sundering upgrade's 20 % at its chance, Judge's
# Insight's 20 %. GWW "Armor calculation" step 3: the rating times (1 - p),
# rounded -- its own examples 81 x 0.75 = 60.75 -> 61 and 131 x 0.75 = 98.25
# -> 98 -- then the Special step (a critical's 20, Healing Signet's 40) after.
#
# THE CLIENT'S OWN SLOT carries the per-skill numbers: the s_skill record's
# bonus slot holds the wiki's percentage with equal endpoints on 398 and 1191
# (10 / 10, bit clear), 339 and 1136 (20 / 20, bit clear), 1551 (25 / 25, bit
# set), 1218 / 1732 / 2148 (10 / 20 / 10) and the PvP copies -- CORROBORATED,
# the record and the page agreeing on eight of eight, on every snapshot in
# the vault (the scale endpoints of 339 / 1136 moved 5..20 -> 10..25 with the
# 2026-09-01 build; the slot did not). The Air spells do NOT carry theirs
# (Lightning Orb's slot holds 1800, Lightning Strike's 0): that tier is the
# attribute rule, OBSERVED once on the wire -- Lightning Orb onto a PvP
# Warrior's five 80-armour pieces reads exactly its tooltip and 2^(60/40) of
# it bare (studies/skills 50.1: 101 x 9, 286 x 2), an effective 60 from 80.
# STRENGTH'S TERM IS UNWITNESSED: no live tape lands a Warrior's attack skill
# on a target of known rating (the isle's engagement blocks were plain swings,
# 0 casts; the RB2 Warrior at Strength 8 pressed none at a foe), and none of
# the five penetration skills was ever announced by a player.
BASE_PENETRATION_MEANS = "Armor penetration %"   # the bonus_scale_means naming the slot


def armour_penetration(base=(), bonus=()):
    """The fraction of the rating a hit ignores: the LARGEST base source plus
    every bonus source (WIKI). An empty tier is 0; None entries are 0."""
    b = max([0.0] + [float(x) for x in base if x])
    return b + sum(float(x) for x in bonus if x)


def strength_penetration(rank, per_rank=0.01):
    """Strength's base penetration at `rank` on an attack skill: 1 % a rank."""
    return max(0, int(rank or 0)) * float(per_rank)


def penetrated_rating(armour, penetration):
    """The wiki's step 3: the rating times (1 - p), to the nearest whole
    number (a .5 up, ours). None stays None; p <= 0 leaves it alone."""
    if armour is None:
        return None
    p = float(penetration or 0.0)
    if p <= 0.0:
        return armour
    return float(int(float(armour) * (1.0 - p) + 0.5))
