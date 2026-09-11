r"""What the wearer's open episodes do to a number.

SIX PURE MODIFIERS. Every function here takes a state dict and an agent, reads
that agent's open episodes out of the effect table, and returns a number or a
verdict. None of them sends, closes an episode or touches a connection -- the
half that does is `resolve_taker_conversion`, which stayed in `authsrv.py` next
to the `taker-side damage modifiers` banner that documents both halves. That
split is the point: the caller has to know the outcome before choosing what to
put on the wire, and a conversion resolved twice would heal twice.

WHAT STAYS IN `authsrv.py`, because a moved comment's referent has to be
findable from here:

  * `SCALE_MEANS_DAMAGE` (authsrv.py:2679) with its banner -- the table
    `swing_preparation_bonus`'s docstring cites by name. It does NOT move: it
    has three readers in three destinations (`skill_damage` and
    `spell_armour_for` in `authsrv.py`, `swing_preparation_bonus` here), so it
    is passed in rather than owned by any of them.
  * `BLIND` and `BLIND_MISS_CHANCE` (authsrv.py:3423-3424) and the `--no-blind`
    flag. `BLIND` is `global`-rebound inside `main()`, so it must be read at the
    CALL; `blind_miss` takes both as required parameters carrying those exact
    names, which is what lets its two-line body travel verbatim, and the
    `authsrv.py` wrapper reads them from the server's globals per call. A
    default would be evaluated once at `def` time and freeze the flag -- the
    failure the wrapper exists to prevent.
  * `attack_fails`, the 0x00A0 word a miss puts on the wire. It sat between
    `blinded` and `blind_miss` and stays there: it sends.
  * The callers, all of which stay -- `attack_tick`, `handle_skill_press`,
    `cast_tick`, `enemy_attack_tick` (attack interval), `hit_enemy` and
    `land_swing` (the preparation bonus and the blind roll), `land_swing` and
    `land_skill` (taker damage), `speed_tick` (movement percent).

`skill_scale_value` and `skill_flat_constant` are imported from `skillread.py`,
not from the server: both leaves read the same two skill-row readers and neither
may import `authsrv.py`, which runs as `__main__` and would be loaded a second
time with flags `main()` never set.

Standard library only.
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agents  # noqa: E402
import effects  # noqa: E402
from skillread import skill_scale_value, skill_flat_constant  # noqa: E402


def blinded(state, agent_id):
    """True if a live Blind (479) episode sits on the agent. Pure read."""
    table = state.get("effects")
    if not table:
        return False
    blind = effects.CONDITION_BY_NAME["Blind"]
    return any(ep["skill"] == blind for ep in table.on_agent(agent_id))


def blind_miss(state, agent_id, BLIND, BLIND_MISS_CHANCE):
    """One roll: does THIS swing by a blinded agent miss? False when not blind."""
    if not BLIND or not blinded(state, agent_id):
        return False
    return random.random() < BLIND_MISS_CHANCE


def taker_damage(state, agent_id, dealt):
    """(final_damage, conversion) after the taker's open episodes have spoken.

    `conversion` is None or {"episode", "heal", "reduced", "cap"} -- decided
    but NOT performed. Only the FIRST prevention episode fires (one packet,
    one conversion; a second RoF would need its own packet), and it fires on
    the post-multiplier number -- Frenzy's doubling is what RoF sees.
    """
    table = state.get("effects")
    if not table or dealt <= 0:
        return dealt, None
    conversion = None
    for ep in table.on_agent(agent_id):
        try:
            row = agents.WORLD.get("skill_effect", str(ep["skill"]))
        except Exception:                                      # noqa: BLE001
            continue
        mult = row.get("damage_taken_multiplier")
        if mult is not None:
            dealt *= float(mult)
    for ep in table.on_agent(agent_id):
        try:
            row = agents.WORLD.get("skill_effect", str(ep["skill"]))
        except Exception:                                      # noqa: BLE001
            continue
        if not row.get("prevents_damage"):
            continue
        try:
            cap = float(skill_scale_value(ep["skill"], ep.get("rank", 0),
                                          "scale"))
        except ValueError as ex:
            # An unreadable cap converts NOTHING -- the glyph's rule from the
            # other side: refusing is the direction that cannot invent.
            print(f"[effects] {ep['skill']} prevents damage but its cap is "
                  f"UNREADABLE, so the hit lands whole: {ex}", flush=True)
            continue
        reduced = min(dealt, cap)
        conversion = {"episode": ep, "heal": min(dealt, cap),
                      "reduced": reduced, "cap": cap}
        dealt = max(0.0, dealt - reduced)
        break
    return dealt, conversion


def attack_interval_factor(state, agent_id):
    """What the agent's open episodes do to its attack DURATION. 1.0 = nothing.

    THE PERCENT CUTS THE DURATION; IT DOES NOT DIVIDE THE RATE. GWW's "Attack
    speed" article (rev. 2026-07-03) publishes the exact values the game uses:
    a hammer's 1.75 becomes 1.1725 under +33% -- that is 1.75 x (1 - 0.33),
    where the rate reading (1.75 / 1.33 = 1.3158) misses by 0.14 s a swing.
    Increases multiply by (1 - p/100), decreases by (1 + p/100), and the same
    table's -50% row (1.75 -> 2.625) pins the decrease side.

    The percent itself comes from the skill's own flat scale slot
    (`skill_flat_constant`), or from the progression at the episode's rank if
    the slot's bit is set -- no skill today scales its IAS, but the reader
    should not decide that. Unreadable percents modify nothing and say so.
    """
    table = state.get("effects")
    if not table:
        return 1.0
    factor = 1.0
    for ep in table.on_agent(agent_id):
        try:
            row = agents.WORLD.get("skill_effect", str(ep["skill"]))
        except Exception:                                      # noqa: BLE001
            continue
        means = row.get("scale_means")
        if means not in ("Attack speed increase", "Attack speed decrease"):
            continue
        try:
            pct = skill_flat_constant(ep["skill"])
        except ValueError:
            try:
                pct = skill_scale_value(ep["skill"], ep.get("rank", 0))
            except ValueError as ex:
                print(f"[effects] {ep['skill']} names an attack-speed change "
                      f"but its percent is UNREADABLE, so the swing keeps its "
                      f"base interval: {ex}", flush=True)
                continue
        if means == "Attack speed increase":
            factor *= 1.0 - pct / 100.0
        else:
            factor *= 1.0 + pct / 100.0
    return factor


def swing_preparation_bonus(state, weapon_row, agent_id, SCALE_MEANS_DAMAGE):
    """(bonus damage, preparation skill id) an open PREPARATION adds to one
    swing, or (0.0, None).

    WIKI (GWW, "Preparation", rev. 2020-06-18): "preparations generally alter
    bow attacks, allowing the fired arrows to cause additional effects" --
    which is why Ignite Arrows' `Fire damage` 3..18 shares Flare's label and
    does not mean the same thing (SCALE_MEANS_DAMAGE's own comment). The
    bonus therefore rides a swing, and ONLY a swing the equipped weapon fires
    as an arrow: the gate is the weapon row's `fires_arrows` field, declared
    per item in content rather than through a bow type-code enum this repo has
    no witnessed value for. Today's starter hammer does not carry it, so this
    is live-but-inert against current content -- the glyph's old shape, and
    like it, the refusing direction invents nothing.

    KNOWN GAP, named: Ignite Arrows' damage is "to target and all adjacent
    foes" -- the adjacency splash is not modelled, only the on-target bonus.
    """
    if not weapon_row or not weapon_row.get("fires_arrows"):
        return 0.0, None
    table = state.get("effects")
    if not table:
        return 0.0, None
    for ep in table.on_agent(agent_id):
        # 19 = preparation, effects.EFFECT_TYPES' own vocabulary.
        if effects.EFFECT_TYPES.get(int(ep.get("type_code", 0))) != "preparation":
            continue
        try:
            row = agents.WORLD.get("skill_effect", str(ep["skill"]))
        except Exception:                                      # noqa: BLE001
            continue
        if row.get("scale_means") not in SCALE_MEANS_DAMAGE:
            continue
        try:
            return (float(skill_scale_value(ep["skill"], ep.get("rank", 0))),
                    ep["skill"])
        except ValueError as ex:
            print(f"[effects] preparation {ep['skill']}'s bonus is "
                  f"UNREADABLE, so the arrow flies plain: {ex}", flush=True)
    return 0.0, None


def move_speed_percent(state, agent_id):
    """The LARGEST open movement-speed boost on this agent, in percent.

    Largest rather than a product: GW speed boosts famously do not stack (the
    strongest applies), and stances -- today's only carriers -- are exclusive
    per type anyway, so the max and the product cannot differ against current
    content. Recorded as max so the day two sources coexist, the modelled rule
    is the game's rather than an accident of arithmetic.
    """
    table = state.get("effects")
    if not table:
        return 0.0
    best = 0.0
    for ep in table.on_agent(agent_id):
        try:
            row = agents.WORLD.get("skill_effect", str(ep["skill"]))
        except Exception:                                      # noqa: BLE001
            continue
        if row.get("scale_means") != "Movement speed increase":
            continue
        try:
            pct = skill_flat_constant(ep["skill"])
        except ValueError:
            try:
                pct = skill_scale_value(ep["skill"], ep.get("rank", 0))
            except ValueError as ex:
                print(f"[effects] {ep['skill']} names a speed boost with an "
                      f"UNREADABLE percent, so the base stays: {ex}",
                      flush=True)
                continue
        best = max(best, float(pct))
    return best
