r"""Morale, and the death penalty that is negative morale.

THE ARITHMETIC ONLY. Nothing here sends a message or knows an opcode: the wire
shape lives in `authsrv.py` beside the other sends, and the rule constants live
in `content/world.toml` under `[player.morale]`. What this module owns is the one
piece that is neither -- turning a morale percentage into the two pool maxima the
client is told about -- because that is the part that was wrong in every guess
this project made before 2026-08-20.

WHY A MODULE. `0x00E9` field 10 has been called `morale` by every lineage since
the first recon sweep, our own display probe found that setting it moved nothing,
and the server has shipped it as a zero ever since with a comment admitting we did
not know what it meant. The answer came out of ArenaNet's own wire -- one player
death in fourteen live captures -- and it is small enough to write down and exact
enough to test offline, which is what this file is for.

    morale = 100 is neutral. A death is -15. The floor is 40 and the ceiling 110.
    effective_max = total_max + base * (morale - 100) / 100

THE TRAP IN THAT SECOND LINE, and it is the whole reason this is not a one-liner
at the call site: the scale applies to the character's BASE health and energy, not
to the totals. Armor and weapon bonuses ride along unscaled. It is the difference
between 22 and 21.25 on the one observation we have --

    energy  25 total, 20 base, morale 85  ->  25 - 3    = 22   (observed 22)
    energy  25 total, scaled whole        ->  25 * 0.85 = 21.25 (no rounding
                                                                 rule reaches 22)

-- so the naive model does not merely lose precision, it produces a number the
game never shows, and it would have needed an invented rounding rule to look
plausible while doing it. Evidence, both halves: `studies/morale/FINDINGS.md`.

Standard library only, and no import of the server: `test_morale.py` exercises
every function here with no vault, no client and no socket.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents  # noqa: E402

_ROW = agents.WORLD.get("player", "morale")

# The neutral value. Retail sends it explicitly -- `0x009C [player, 100]` at login
# and `0x00E9` field 10 = 100 in 43 of 43 sightings -- so "we set it to 100" is the
# right thing to send and was, until this rung, a number with no meaning attached.
BASELINE = int(_ROW["baseline"])
FLOOR = int(_ROW["floor"])              # -60% death penalty, the cap
CEILING = int(_ROW["ceiling"])          # +10% morale boost, the cap
DEATH_STEP = int(_ROW["death_step"])    # what one death costs
XP_PER_PERCENT = int(_ROW["xp_per_percent"])
BASE_ENERGY = int(_ROW["base_energy"])
BASE_HEALTH_LEVEL_1 = int(_ROW["base_health_level_1"])
HEALTH_PER_LEVEL = int(_ROW["health_per_level"])


def clamp(value):
    """A morale value forced into the range the game allows.

    Clamping rather than refusing, and this is the one place in the module that
    bends the house rule. `_fraction` refuses an out-of-range pool fraction
    because a wrong number there is a client assert with no server-side symptom;
    here the bounds ARE the mechanic -- "cumulative, up to a maximum of 60%" is
    a clamp in the game's own description, and a fifth consecutive death has to
    do something rather than raise.
    """
    return max(FLOOR, min(CEILING, int(value)))


def base_health(level):
    """The level-derived health a character has before any equipment.

    WIKI (GWW, "Health", section Maximum health): a roleplaying character starts
    at level 1 with 100 health and gains 20 per level to 480 at level 20. Both
    endpoints check: 100 + 20 * 19 = 480.

    CORROBORATED on ArenaNet's wire in passing -- the capture's level-2 character
    carried maximum health 120, which is this formula, and the death then moved
    it to 102, which is this formula times 0.85.
    """
    if level < 1:
        raise ValueError(f"level {level!r} is not a level; morale arithmetic "
                         f"needs a real one to know the base health")
    return BASE_HEALTH_LEVEL_1 + HEALTH_PER_LEVEL * (int(level) - 1)


def effective_max(total, base, value):
    """The maximum the client should be told, for one pool, at this morale.

    `total` is what the character has at neutral morale (base plus armor, runes,
    weapon bonuses). `base` is the part morale scales. They are equal for health
    on a character with no health upgrades and DIFFERENT for energy on almost
    everybody, which is why they are two arguments rather than a ratio.

    Never below 1: WIKI (GWW, "Health", section Maximum health) -- "a character
    cannot decrease their maximum health below 1". At the -60% floor with a
    level-1 character that bound is nowhere near, but a caller handing in a
    small base is not a reason to put a zero pool on the wire.
    """
    scaled = total + base * (clamp(value) - BASELINE) / 100.0
    return max(1, int(round(scaled)))


def after_death(value):
    """Morale after one death: -15, floored at the -60% cap."""
    return clamp(int(value) - DEATH_STEP)


def experience_credit(value, bank, gained):
    """(morale, bank, recovered) after earning `gained` experience.

    WIKI (GWW, "Death Penalty", section Counters): "In PvE, gaining 75 experience
    will remove 1% DP". So experience buys death penalty back a percent at a
    time, and the remainder banks -- a kill worth 26 XP is not a third of a
    percent on the wire, it is nothing until the third kill.

    IT NEVER BECOMES A BOOST, and the same section says why: "Gaining experience
    and certain consumables will remove Death Penalty, but will not provide or
    increase your Morale Boost." So the ceiling here is the BASELINE, not
    `CEILING` -- a character at neutral morale banks nothing and the bank is
    dropped rather than carried, because carrying it would make a later death
    cheaper than the first one by however much was hoarded.
    """
    value, bank, gained = int(value), int(bank), int(gained)
    if value >= BASELINE:
        return value, 0, 0
    bank += max(0, gained)
    recovered = bank // XP_PER_PERCENT
    if not recovered:
        return value, bank, 0
    bank -= recovered * XP_PER_PERCENT
    healed = min(BASELINE, value + recovered)
    if healed >= BASELINE:
        bank = 0                    # at neutral again: nothing hoards for later
    return healed, bank, healed - value


def regen_fraction(fraction_at, pool_at, pool_now):
    """The property-43 value for a pool that changed size, same absolute rate.

    MEASURED, and it is the observation that named property 43 at all: the same
    character carried 0.0528f at 25 maximum energy and 0.0600f at 22 across a
    death, and 0.0528 * 25 == 0.0600 * 22 == 1.32 energy per second. The channel
    carries a FRACTION of the pool per second, so shrinking the pool without
    resending this would silently slow regeneration by the same 15% the penalty
    took off the maximum -- which retail does not do.
    """
    if pool_at <= 0 or pool_now <= 0:
        raise ValueError(
            f"refusing to rescale a regeneration fraction against a pool of "
            f"{pool_at!r} -> {pool_now!r}: the value is a fraction OF the pool, "
            f"so a zero pool makes it meaningless rather than large")
    return float(fraction_at) * float(pool_at) / float(pool_now)


def display(value):
    """`-15%` / `+10%` / `0%` -- what the game shows, for our own logs.

    Ours, from the 100-baseline encoding this module is built on. Named here so
    every print of a morale value spells it the same way, and so a log line can
    be read against a screenshot without arithmetic.
    """
    delta = int(value) - BASELINE
    return f"{delta:+d}%" if delta else "0%"
