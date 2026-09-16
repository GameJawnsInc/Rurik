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


def taker_rank(state, agent_id, attribute):
    """The taker's rank in `attribute`: the player's from [player.attributes]
    (the player is NOT a row in state["agents"] -- SLICE-B7a's asymmetry is
    the test here), a body's from its own `attributes` or its npc row's;
    0 when it has none, which is a Warrior's honest rank in Smiting."""
    rows = state.get("agents") or {}
    if agent_id not in rows:
        return int(dict(agents.PLAYER_ATTRIBUTE_RANKS).get(attribute, 0))
    agent = rows[agent_id] or {}
    ranks = agent.get("attributes")
    if ranks is None:
        ranks = (agent.get("npc") or {}).get("attributes")
    if not ranks:
        return 0
    table = {int(a): int(r) for a, r in
             (ranks.items() if isinstance(ranks, dict) else ranks)}
    return table.get(attribute, 0)


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
        pct = row.get("damage_taken_percent")
        if pct:
            # SLICE-H17: "take lo..hi % damage" scaled at the TAKER's rank in
            # the row's attribute (Frenzy: 175..125 at Strength on build
            # 38888), rounded to a whole percent the way skill_scale_value
            # rounds every client set. The taker's rank, not the episode's:
            # a stance is self-cast so they coincide for the player, but a
            # body's episode records the caster's rank in the SKILL's
            # attribute, which on the pin (38797) is "none".
            lo, hi = float(pct[0]), float(pct[1])
            rank = taker_rank(state, agent_id, int(row.get("damage_taken_attribute", -1)))
            dealt *= max(0.0, round(lo + (hi - lo) * rank / 15.0)) / 100.0
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


# MOVEMENT SPEED (SLICE-F47, 2026-09-16). Three kinds of term, read off retail's
# wire by speedwords.py (501 speed words, 17 captures) and GWW's published rules:
#
#   boosts   sum, capped at +34 -- "Speed boosts can be stacked, but movement
#            rate is capped at 34% faster than normal" (WIKI, GWW "Speed
#            boost", rev. 2020-05-09). OBSERVED: a second 33% boost over an open
#            one reads x1.34, 8 of 8 (not x1.33, which a "largest applies" rule
#            would send, and not x1.77). A SINGLE source may exceed the cap
#            (Dash's +50%: five x1.5 rows on one Lakeside body).
#   snares   sum, capped at -50 -- "capped at -50% slower than normal; however,
#            a single skill that causes more than -50% ... can override the -50%
#            cap" (WIKI, GWW "Snare (tactic)", rev. 2026-04-24). OBSERVED: six
#            x0.34 rows (a -66% source) on the MANTID tape. No content row
#            declares a decrease today, so this arm runs on nothing; it is here
#            so the day one does, the rule is the game's.
#   Crippled MULTIPLIES the result by 0.5 -- "you move 50% slower" (WIKI, GWW
#            "Crippled", rev. 2020-10-23). OBSERVED, and this is the arithmetic
#            the corpus settles: Crippled over a 33% boost reads x0.665 =
#            1.33 x 0.5 on 21 of 21 such rows, and the additive x0.83 appears
#            nowhere. Alone it is x0.5 (27 rows, 288 -> 144.0).
#
# BOOST x SNARE is the WIKI's multiplicative rule -- GWW "Effect stacking"
# (rev. 2026-09-07): "Attack speed and movement speed stack multiplicatively.
# For example, a character affected by Flail and 'Fall Back!' will have 89.1%
# movement speed rather than 100%." CONTESTED by one row: a PvP body that read
# x0.8 from its create batch (an 0x006F item change in the same batch -- GWW
# "Bundle": "Some bundles ... reduce movement speed") took "Charge!" to x1.13 =
# 1 + 0.33 - 0.20, additive, on 3 of 3. A bundle's slow is not a skill's, and
# nothing here models a bundle, so the wiki's rule ships and the row is on
# record (studies/slice/FINDINGS.md SLICE-F47).
MOVE_SPEED_CAP_UP = 34.0
MOVE_SPEED_CAP_DOWN = 50.0
CRIPPLED_FACTOR = 0.5
MOVE_SPEED_MEANS = {"Movement speed increase": +1, "Movement speed decrease": -1}


def _episode_percent(ep, which):
    """The percent in the episode's `which` slot: flat, else the progression."""
    try:
        return float(skill_flat_constant(ep["skill"], which))
    except ValueError:
        return float(skill_scale_value(ep["skill"], ep.get("rank", 0), which))


def move_speed_terms(state, agent_id):
    """(boosts, snares, crippled): the open episodes' movement terms, in percent.

    A row names the term in `scale_means` or `bonus_scale_means` (Storm Chaser's
    25 sits in its BONUS slot; Rush's, "Charge!"'s and Windborne Speed's in the
    scale slot), and the percent is read from THAT slot. Unreadable percents
    modify nothing and say so. Crippled is the condition episode itself.
    """
    table = state.get("effects")
    boosts, snares, crippled = [], [], False
    if not table:
        return boosts, snares, crippled
    for ep in table.on_agent(agent_id):
        if ep["skill"] == effects.CONDITION_BY_NAME["Crippled"]:
            crippled = True
            continue
        try:
            row = agents.WORLD.get("skill_effect", str(ep["skill"]))
        except Exception:                                      # noqa: BLE001
            continue
        for which, key in (("scale", "scale_means"), ("bonus_scale", "bonus_scale_means")):
            sign = MOVE_SPEED_MEANS.get(row.get(key))
            if sign is None:
                continue
            try:
                pct = _episode_percent(ep, which)
            except ValueError as ex:
                print(f"[effects] {ep['skill']} names a movement-speed change "
                      f"with an UNREADABLE percent, so the base stays: {ex}",
                      flush=True)
                continue
            (boosts if sign > 0 else snares).append(pct)
    return boosts, snares, crippled


def _capped(terms, cap):
    total = sum(terms)
    if total > cap and max(terms) <= cap:
        return cap
    return total


def move_speed_factor(state, agent_id):
    """What the agent's open episodes do to its declared 0x0027 base. 1.0 = nothing."""
    boosts, snares, crippled = move_speed_terms(state, agent_id)
    factor = 1.0
    if boosts:
        factor *= 1.0 + _capped(boosts, MOVE_SPEED_CAP_UP) / 100.0
    if snares:
        factor *= 1.0 - _capped(snares, MOVE_SPEED_CAP_DOWN) / 100.0
    if crippled:
        factor *= CRIPPLED_FACTOR
    return factor


def move_speed_percent(state, agent_id):
    """The open BOOST total on this agent, capped, in percent (Rush: 25.0).

    Kept for its readers (test_mechanics, the speed_tick banner); the full
    factor with snares and Crippled is `move_speed_factor`.
    """
    boosts, _snares, _crippled = move_speed_terms(state, agent_id)
    return _capped(boosts, MOVE_SPEED_CAP_UP) if boosts else 0.0
