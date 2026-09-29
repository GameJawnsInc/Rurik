r"""Kill experience -- what one hostile's death pays the player (RANGERPRE-S6, KILLXP-a).

THE ARITHMETIC ONLY, like `morale.py`. Nothing here sends a message or reads a
connection: the send is `authsrv.kill_agent`'s, the inputs (whose level, what
party, whether the Reforged effect is on) are `authsrv.kill_experience`'s, and
the numbers are `content/world.toml` [player.experience] with their provenance.

WHY A MODULE. Until 2026-09-29 every kill paid `KILL_REWARD_VALUE = 26`, on a
comment that read three creatures giving 26 as "evidence that it does NOT
vary". It varies: 20, 25, 26, 30, 32, 84, 105, 126 and 176 are all on ArenaNet's
wire, and all 49 own-kill awards in the live corpus are the wiki's table with
nothing fitted --

    x = floor(T(foe level - player level) * (105 if the 3434 effect else 100)
              / (100 * party))

-- with T the level-difference table, or the level-0 table when the foe's level
is 0. The three 26s were three level-0 foes killed by a level-1 character under
the Reforged effect: 25 * 1.05, floored. OBSERVED, and the evidence is
studies/presearing/RANGERPRE.md (KILLXP) and the content row's `verified`.

Standard library only, and no import of the server: `test_killxp.py`
exercises every function here with no vault, no client and no socket.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
import agents  # noqa: E402

_ROW = agents.WORLD.get("player", "experience")

# WIKI (GWW "Experience" section Experience per foe): the award by foe level minus
# player level, from DIFFERENCE_MIN (six or more below: 0) to DIFFERENCE_MAX
# (eleven or more above: 280, the cap "before applying any multipliers").
BY_DIFFERENCE = tuple(int(x) for x in _ROW["kill_by_level_difference"])
DIFFERENCE_MIN = int(_ROW["difference_min"])
DIFFERENCE_MAX = DIFFERENCE_MIN + len(BY_DIFFERENCE) - 1
# ...and a level-0 foe's, by player level 1..5. Past 5 the table stops and this
# pays 0: RECONSTRUCTION.
LEVEL_ZERO_FOE = tuple(int(x) for x in _ROW["kill_level_zero_foe"])
# The Reforged Mode effect (skill 3434): +5% from killing foes. CORROBORATED --
# WIKI, and the wire's 25 without it (17 of 17) against 26 with it (5 of 5).
REFORGED_PERCENT = int(_ROW["reforged_percent"])
# Where that effect is on: the Prophecies explorables it was OBSERVED on. The
# character's Reforged flag is NOT this -- Factions and Nightfall characters
# carry it and are paid 100% (the row's note).
REFORGED_EFFECT_MAPS = frozenset(int(m) for m in _ROW["reforged_effect_maps"])


def base(foe_level, player_level):
    """The table's award for one foe, before the party split and the effect."""
    foe, me = int(foe_level), int(player_level)
    if foe == 0:
        return LEVEL_ZERO_FOE[me - 1] if 1 <= me <= len(LEVEL_ZERO_FOE) else 0
    d = max(DIFFERENCE_MIN, min(DIFFERENCE_MAX, foe - me))
    return BY_DIFFERENCE[d - DIFFERENCE_MIN]


def share(foe_level, player_level, party=1, reforged=False):
    """What the player is paid: the base, times the effect, split by the party.

    Multiply before divide, then floor: RECONSTRUCTION -- floor and round agree
    on all 49 live awards, so the corpus does not choose. A party below 1 is
    read as the player alone rather than refused: the count always includes
    the player, and a divide by zero on the kill path would take the world tick
    with it.
    """
    percent = REFORGED_PERCENT if reforged else 100
    return base(foe_level, player_level) * percent // (100 * max(1, int(party)))


def reforged_map(map_id):
    """Is the Reforged Mode effect on in this map's instances? The content
    row's observed set; None (no map yet) is not in it."""
    try:
        return int(map_id) in REFORGED_EFFECT_MAPS
    except (TypeError, ValueError):
        return False
