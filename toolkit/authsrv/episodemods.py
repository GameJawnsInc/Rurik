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


# SKILLS-WK (2026-09-17, studies/skills 51): WEAKNESS TAKES ONE OFF EVERY
# ATTRIBUTE. WIKI (GWW "Weakness"): "all of your attributes are reduced by 1 ...
# Attributes at rank 0 are not affected". OBSERVED on the owner's Isle tape
# 20260917T090355: the Weakness apply's own batch re-declares every non-zero
# attribute one lower (0x003B [agent, attr, base, effective - 1], right behind
# the status word) and the removal's batch restores them; and a Mend Ailment
# cast at Protection Prayers 8 under it healed 35, the rank-7 number, where
# the tooltip said 40. The flag lives HERE because `taker_rank` needs it and a
# leaf may not import its origin; `authsrv.main()` clears it for
# --no-weakness-attributes.
WEAKNESS_ATTRIBUTES = True


def weakened(state, agent_id):
    """True if a live Weakness (486) episode sits on the agent. Pure read."""
    if not WEAKNESS_ATTRIBUTES:
        return False
    table = state.get("effects")
    if not table:
        return False
    weak = effects.CONDITION_BY_NAME["Weakness"]
    return any(ep["skill"] == weak for ep in table.on_agent(agent_id))


def weakened_rank(state, agent_id, rank):
    """The rank an agent's numbers scale at RIGHT NOW: one lower under Weakness,
    never below zero, and a rank of 0 (or None) is untouched."""
    if rank is None or rank <= 0 or not weakened(state, agent_id):
        return rank
    return rank - 1


def taker_rank(state, agent_id, attribute):
    """The taker's rank in `attribute`: the player's from [player.attributes]
    (the player is NOT a row in state["agents"] -- SLICE-B7a's asymmetry is
    the test here), a body's from its own `attributes` or its npc row's;
    0 when it has none, which is a Warrior's honest rank in Smiting."""
    rows = state.get("agents") or {}
    if agent_id not in rows:
        return weakened_rank(state, agent_id, int(
            dict(agents.PLAYER_ATTRIBUTE_RANKS).get(attribute, 0)))
    agent = rows[agent_id] or {}
    ranks = agent.get("attributes")
    if ranks is None:
        ranks = (agent.get("npc") or {}).get("attributes")
    if not ranks:
        return 0
    table = {int(a): int(r) for a, r in
             (ranks.items() if isinstance(ranks, dict) else ranks)}
    return weakened_rank(state, agent_id, table.get(attribute, 0))


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



def strongest_per_skill(table, agent_id):
    """The agent's live episodes with ONE per skill id: the most powerful (the highest
    rank) and, on a tie, the most recent (the later `applied_at`). WIKI (GWW "Effect
    stacking" rev 2739765, Skill effects: "Most skill effects do not stack -- the most
    recent or the most powerful application takes precedence"). The table still HOLDS
    every overlapping episode -- a re-application gets its own buff id, retail's shape
    (skills 16.1) -- but what an effect DOES counts its skill once. Found by harness run
    20260927T174700 (DESKWORK-D6): a hostile's second Suffering on the player summed to
    4 pips where one Suffering is 2. Different skills still combine, each by its own rule."""
    best = {}
    for ep in table.on_agent(agent_id):
        cur = best.get(ep["skill"])
        key = (ep.get("rank", 0) or 0, ep.get("applied_at", 0.0) or 0.0, ep["buff"])
        if cur is None or key > cur[0]:
            best[ep["skill"]] = (key, ep)
    return sorted((v[1] for v in best.values()), key=lambda ep: ep["buff"])

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
    for ep in strongest_per_skill(table, agent_id):     # one per skill (WIKI, Effect stacking)
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


# MOVEMENT SPEED (SLICE-F48, 2026-09-16). Three kinds of term, read off retail's
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
#            x0.34 rows (Teinai's Prison, -66%) on 20260913T210901, and 14 x0.25
#            rows (-75%) on the Zaishen tapes -- 9 batch-joined to skill 493's
#            apply or its buff's 0x0043 renewals, 5 with no source on the wire
#            (speedwords P7j). The rows that declare one today: Deep Freeze 234
#            and Ice Spikes 211 (the flat 66 in the bonus slot, DESKWORK-D6),
#            and on a vault machine the label tier's 1044, 1404 (Flail's 33)
#            and 1652.
#   Crippled MULTIPLIES the result by 0.5 -- "you move 50% slower" (WIKI, GWW
#            "Crippled", rev. 2020-10-23). OBSERVED, and this is the arithmetic
#            the corpus settles: Crippled over a 33% boost reads x0.665 =
#            1.33 x 0.5 on 21 of 21 such rows, and the additive x0.83 appears
#            nowhere. Alone it is x0.5 (27 rows, 288 -> 144.0).
#
# BOOST x SNARE, TWO REGIMES (SLICE-F48b, 2026-10-07, studies/slice/FINDINGS.md
# F48.7):
#
#   UNDER the -50 cap: the WIKI's multiplicative rule -- GWW "Effect stacking"
#            (rev. 2026-09-07): "Attack speed and movement speed stack
#            multiplicatively. For example, a character affected by Flail and
#            'Fall Back!' will have 89.1% movement speed rather than 100%."
#            WIKI only: no under-cap skill snare over a boost is on any tape
#            (the one under-cap row, a bundle's x0.8 under "Charge!", read
#            x1.13 = 1 + 0.33 - 0.20, ADDITIVE, 3 of 3 -- a bundle is not a
#            skill and nothing here models one; CONTESTED, on record).
#   OVER the cap (a single snare above 50): the snare OVERRIDES the boosts --
#            the factor is 1 - snare/100 whatever boosts are open, and they
#            come back when it ends. OBSERVED on retail's wire at x0.25
#            (speedwords P7-P10, n small): a "Charge!" applied to and ending on
#            an observer under 493 sends NO word (2 of 2, an unsnared ally's
#            word moved with the boost in both batches); a boosted body's onset
#            reads 75.0 = 300 x 0.25 (2 of 2, never the multiplicative 99.75 or
#            the additive 174.0) and the snare's end restores the boosted 399.0
#            (2 of 2) -- but those onsets' source is NOT on the wire (P7j), so
#            that they are 493's, or one 75% snare's, is RECONSTRUCTION. So is
#            every other over-cap snare -- the 66s (Deep Freeze, Ice Spikes,
#            Teinai's Prison) and the client table's 90s: same regime, never seen
#            under a boost. SNARE_OVERRIDES_BOOST; the revert
#            --snare-multiplies-boost restores the multiplicative product above
#            the cap too (Windborne + Deep Freeze = 130.2, retail's shape says
#            97.92).
#
# Crippled's x0.5 still multiplies on top of an overriding snare: UNVERIFIED
# (no tape holds Crippled and an over-cap snare at once); it is the reading that
# keeps Crippled's own rule (P3, 21 of 21) untouched.
MOVE_SPEED_CAP_UP = 34.0
MOVE_SPEED_CAP_DOWN = 50.0
CRIPPLED_FACTOR = 0.5
MOVE_SPEED_MEANS = {"Movement speed increase": +1, "Movement speed decrease": -1}
# SLICE-F48b: past the snare cap the boosts are dropped (above). A leaf flag for the
# reason WEAKNESS_ATTRIBUTES is one; `authsrv.main()` clears it for
# --snare-multiplies-boost.
SNARE_OVERRIDES_BOOST = True


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
    for ep in strongest_per_skill(table, agent_id):     # one per skill (WIKI, Effect stacking)
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


def _capped_snare(terms, cap):
    """The snare percent: the boosts' rule below the cap, and ABOVE it the
    LARGEST single snare, never the sum. A single 66 passes the 50 cap
    (Teinai's Prison's x0.34, OBSERVED 6/6) and, until the D6 review
    (HEX-1, 2026-09-27), two of them SUMMED to 132 through `_capped` and
    declared a negative speed (0x0027 [foe, -92.16]) -- Deep Freeze +
    Ice Spikes on one foe, or the placeholder AI's re-cast. RECONSTRUCTION:
    retail's stacking of two over-cap snares is on no tape (one 75% snare at
    a time is all the Zaishen tapes hold, SLICE-F48b); whatever the rule is,
    a speed below the strongest single snare's is wrong under all of them."""
    if max(terms) > cap:
        return max(terms)
    return _capped(terms, cap)


def move_speed_factor(state, agent_id):
    """What the agent's open episodes do to its declared 0x0027 base. 1.0 = nothing.

    Boosts x snares x Crippled, with ONE exception (SLICE-F48b, the banner
    above): a single snare past MOVE_SPEED_CAP_DOWN drops the boosts --
    Windborne + Deep Freeze is 0.34, not 1.33 x 0.34 = 0.4522 -- and the boosts
    come back when it closes, because this is recomputed from the open
    episodes at every change. Under the cap the product stands (WIKI)."""
    boosts, snares, crippled = move_speed_terms(state, agent_id)
    overridden = (SNARE_OVERRIDES_BOOST and bool(snares)
                  and max(snares) > MOVE_SPEED_CAP_DOWN)
    factor = 1.0
    if boosts and not overridden:
        factor *= 1.0 + _capped(boosts, MOVE_SPEED_CAP_UP) / 100.0
    if snares:
        factor *= 1.0 - _capped_snare(snares, MOVE_SPEED_CAP_DOWN) / 100.0
    if crippled:
        factor *= CRIPPLED_FACTOR       # over an override too: UNVERIFIED (banner)
    return factor


def move_speed_percent(state, agent_id):
    """The open BOOST total on this agent, capped, in percent (Rush: 25.0).

    Kept for its readers (test_mechanics, the speed_tick banner); the full
    factor with snares and Crippled is `move_speed_factor`.
    """
    boosts, _snares, _crippled = move_speed_terms(state, agent_id)
    return _capped(boosts, MOVE_SPEED_CAP_UP) if boosts else 0.0


# THE HEX MECHANISMS (DESKWORK-D6 step 4, B2, 2026-09-27; studies/weapons 43).
# Three more pure readers over the wearer's open episodes, each keyed on a
# content-row field because the client's own slot cannot carry the number:
#
#   * `hex_pips`  -- "Health degeneration" on a row (Suffering 108's 0..-3,
#     Faintheartedness 135's 0..3): pips the wearer LOSES, summed by the caller
#     with effects.pips_from under the same cap of 10 (WIKI, GWW "Health
#     degeneration"). Suffering's 0..3 sits in a BIT-CLEAR slot with DIFFERING
#     endpoints (args = 1), the shape both skillread readers refuse, so the row
#     carries the endpoints itself -- `health_degeneration0/15`, the glyph's
#     `energy_reduction0/15` precedent -- interpolated by the client's own
#     formula; a row without them reads its slot (135's bonus bit IS set).
#     Degeneration is not damage: it never words and never scatters (WIKI,
#     GWW "Area damage over time"). Whether a HEX's pips share the conditions'
#     cap of 10 is RECONSTRUCTION -- the wiki caps "health degeneration" as a
#     whole and names no separate ledger.
#   * `blocks_adrenaline` -- Soothing Images 56's "cannot gain adrenaline"
#     (WIKI, GWW "Soothing Images" rev. 2714814), a row field with no client
#     slot (the record's scale and bonus are 0/0). The caller grants nothing
#     and SENDS nothing; whether retail sends a 0x00CF 0 to a blocked gain is
#     UNVERIFIED (no tape holds a blocked gain).
#   * `signet_activation_factor` -- Rust 204's "take twice as long to activate
#     signets" (WIKI, GWW "Rust" rev. 2740665): `signet_activation_multiplier`
#     on the row, a number with NO client slot (Frenzy's
#     `damage_taken_multiplier` shape), multiplied over the live episodes. The
#     caller applies it to a SIGNET (type_code 7, OBSERVED 4 of 4: Healing
#     Signet 1, Resurrection Signet 2, 294, Signet of Return 1778) and to
#     nothing else.
HEX_DEGEN_MEANS = "Health degeneration"
SIGNET_TYPE_CODE = 7
_HEX_DEGEN_UNREADABLE = set()


def is_signet(skill_id):
    """The client's own type code says signet (7). A rowless id is not one."""
    try:
        row = agents.WORLD.get("skills", str(skill_id))
    except Exception:                                          # noqa: BLE001
        return False
    return int(row.get("type_code") or 0) == SIGNET_TYPE_CODE


def _rate_pips(state, agent_id, means, field, rowless_counts_nothing=False):
    """The pips the agent's open episodes name under `means` in either slot,
    one per skill, uncapped: a row's explicit `<field>0/15` endpoints when it
    carries them (interpolated by the client's formula at the episode's rank),
    else the slot through skill_scale_value. A slot that reader refuses
    (ValueError) and no explicit endpoints count nothing, said once per skill.
    A skill with NO client record raises, as hex_pips always has, unless
    `rowless_counts_nothing` -- regen_pips' choice (SKILLS-RG, the review's
    EV-8): the new reader degrades to the degeneration-only server for that
    skill, logged once, and hex_pips keeps 642d8957's raise under both arms."""
    table = state.get("effects")
    if not table:
        return 0.0
    total = 0.0
    for ep in strongest_per_skill(table, agent_id):     # one per skill (WIKI, Effect stacking)
        try:
            row = agents.WORLD.get("skill_effect", str(ep["skill"]))
        except Exception:                                      # noqa: BLE001
            continue
        for which, key in (("scale", "scale_means"), ("bonus_scale", "bonus_scale_means")):
            if row.get(key) != means:
                continue
            lo, hi = row.get(f"{field}0"), row.get(f"{field}15")
            if lo is not None and hi is not None:
                total += effects.interp(int(lo), int(hi), ep.get("rank", 0))
                continue
            try:
                total += skill_scale_value(ep["skill"], ep.get("rank", 0), which)
            except Exception as ex:                        # noqa: BLE001 -- a refused slot OR no skills row
                if not isinstance(ex, ValueError):
                    if not rowless_counts_nothing:
                        raise
                    ex = f"no client record to read ({type(ex).__name__})"
                if (means, ep["skill"]) not in _HEX_DEGEN_UNREADABLE:
                    _HEX_DEGEN_UNREADABLE.add((means, ep["skill"]))
                    print(f"[effects] {ep['skill']} names a {means.lower()} "
                          f"with an UNREADABLE slot and no {field}0/15 on its "
                          f"row, so it counts nothing: {ex}", flush=True)
    return float(total)


def hex_pips(state, agent_id):
    """Degeneration pips the agent's open NON-condition episodes name
    (`Health degeneration` in either slot), uncapped -- the caller caps the
    sum with the conditions' pips. 0.0 with no such episode."""
    return _rate_pips(state, agent_id, HEX_DEGEN_MEANS, "health_degeneration")


# SKILLS-RG (2026-10-07, studies/skills 64): the other sign. `Health
# regeneration` in either slot (Troll Unguent 446's scale 3..10, Healing Breeze
# 288's 4..9; skilldesc's HEALTH_REGEN label) is pips the wearer GAINS, read with
# hex_pips' endpoint rules and summed by authsrv.net_pips under ONE clamp with
# every degeneration -- OBSERVED on retail's apply words (regenjoin.py P1: 446
# +3 at rank 0, 3 of 3; 288 +8 at rank 13, and -13 + 8 = -5 under degeneration).
REGEN_MEANS = "Health regeneration"


def regen_pips(state, agent_id):
    """Regeneration pips the agent's open episodes name (`Health regeneration`
    in either slot, or a row's explicit `health_regeneration0/15`), one per
    skill, uncapped. 0.0 with none."""
    return _rate_pips(state, agent_id, REGEN_MEANS, "health_regeneration",
                      rowless_counts_nothing=True)


def blocks_adrenaline(state, agent_id):
    """True while an open episode's row says `blocks_adrenaline`."""
    table = state.get("effects")
    if not table:
        return False
    for ep in table.on_agent(agent_id):
        try:
            row = agents.WORLD.get("skill_effect", str(ep["skill"]))
        except Exception:                                      # noqa: BLE001
            continue
        if row.get("blocks_adrenaline"):
            return True
    return False


def signet_activation_factor(state, agent_id):
    """The product of the open episodes' `signet_activation_multiplier`s
    (Rust: 2). 1.0 with none. Two Rusts count ONCE -- one per skill,
    `strongest_per_skill` (WIKI, Effect stacking); the first cut multiplied them (x4),
    found by the D6 client runs."""
    table = state.get("effects")
    if not table:
        return 1.0
    factor = 1.0
    for ep in strongest_per_skill(table, agent_id):     # one per skill (WIKI, Effect stacking)
        try:
            row = agents.WORLD.get("skill_effect", str(ep["skill"]))
        except Exception:                                      # noqa: BLE001
            continue
        mult = row.get("signet_activation_multiplier")
        if mult:
            factor *= float(mult)
    return factor


# ---- DESKWORK-D6 step 5 (B4, 2026-09-27, studies/skills 62): CRACKED ARMOR AND DAZED
#
# The two conditions the substrate carried as icon + the 0x0002 bit alone
# (effects.py's "Dazed and Cracked Armor are not [modelled]"). What each DOES is
# the wearer's business and is read here, purely: a condition is an episode
# whose skill IS the condition's own id (apply_condition's shape, 478..486 and
# 2077), so "is the agent Dazed" is one scan of its open episodes. The numbers
# and the sites are authsrv's (CRACKED_ARMOUR_PENALTY / FLOOR, combatmath.net_
# armour; DAZED_ACTIVATION_FACTOR, dazed_activation, dazed_interrupt).
CRACKED_ARMOR_ID = effects.CONDITION_BY_NAME["Cracked Armor"]
DAZED_ID = effects.CONDITION_BY_NAME["Dazed"]


def has_condition(state, agent_id, condition_id):
    """True while an open episode on the agent IS that condition."""
    table = state.get("effects")
    if not table:
        return False
    return any(ep["skill"] == condition_id for ep in table.on_agent(agent_id))


def is_cracked(state, agent_id):
    """Cracked Armor (2077) is up on the agent."""
    return has_condition(state, agent_id, CRACKED_ARMOR_ID)


def is_dazed(state, agent_id):
    """Dazed (485) is up on the agent."""
    return has_condition(state, agent_id, DAZED_ID)


# ---- CASTAI (2026-09-27; DESKWORK-D8 step 6, owner's ruling PLAN.md sec.7 Q19): THE
# LIVE-EFFECT GATE'S PREDICATE -- "does the target already carry what this skill would
# put on it". Pure: it reads the effect table and the facts the caller hands it, and
# decides nothing about WHICH slot is cast (pick_skill stays the testing fixture; the
# gate that asks this is authsrv's `live_effect_hold`). Two questions, one per class:
#
#   "same-skill"  -- the target holds a LIVE episode of the SAME skill id, any caster
#   "condition"   -- the target holds a live episode of the condition the skill inflicts
#
# The type codes are the client's own column (effects.EFFECT_TYPES; combatmath's
# SPELL_TYPE_CODES_HSR names 25 Weapon Spell).
LIVE_EFFECT_SAME_SKILL_TYPES = {4: "hex", 6: "enchantment", 25: "weapon spell"}
# Never gated, whatever the row carries: 3 Stance, 12 Glyph, 14 Attack, 15 Shout,
# 16 the third instant type, 19 Preparation.
LIVE_EFFECT_NEVER_TYPES = {3: "stance", 12: "glyph", 14: "attack", 15: "shout",
                           16: "instant", 19: "preparation"}


def live_effect_class(type_code, condition_id=None, damages=False, heals=False,
                      area=False):
    """Which question the live-effect gate asks of a skill: "same-skill", "condition"
    or None (never held). Every edge, with its label:

      * HEX (4) and ENCHANTMENT (6) -> "same-skill". WIKI (GWW "Hero behavior" rev
        2741080): heroes know every active effect and will not apply an enchantment
        or a hex to someone already carrying the same one. For a normal-mode MONSTER
        this is RECONSTRUCTION -- the wiki's per-skill AI is tiered (heroes / hard
        mode above the lower normal-mode tiers, CASTAI-W2). OBSERVED consistent: 0 of
        170 retail AI hex / enchantment casts landed on a live same-skill episode
        (castethogram); the 19 informative cases are all SELF-enchantments, and NO
        informative hex case exists. The type decides before anything else, so a hex
        that also damages (an area hex's on-cast hit) is still "same-skill".
      * WEAPON SPELL (25) -> "same-skill", the same wiki sentence. The client's type
        column DOES distinguish it, but the check is VACUOUS today: 25 is not in
        effects.EFFECT_TYPES and no content row's `opens_episode` names one, so no
        weapon spell ever holds an episode to be found. Listed so the gate follows
        the day one does.
      * STANCE (3) -> None. OBSERVED: the JARIN hero re-cast its stance 346 while the
        previous one was live in 10 of 17 casts (20260914T005758 conn 56011: the
        re-cast batch carries 0x0044 [30, 3] then a fresh 0x0042) -- a stance is
        refreshed, not skipped. GLYPH (12) and PREPARATION (19) -> None: the wiki
        sentence does not name them, and like a stance each is one-at-a-time on the
        caster itself (effects.EXCLUSIVE_TYPES), so a re-cast replaces rather than
        stacks; RECONSTRUCTION by that analogy, no witness either way.
      * SHOUT (15) and type 16 -> None: instants the wiki sentence does not name (a
        shout's episode is `opens_episode`'s content door, 364), even one that
        inflicts a condition. RECONSTRUCTION.
      * ATTACK (14) -> None, even a condition-only attack (Sever Artery 382): the
        condition rides a SWING that can miss, and an attack is what the fixture's
        swing clock paces, not a spell the wiki sentence is about. RECONSTRUCTION.
      * Any other type whose row INFLICTS A CONDITION and has NO DAMAGE and NO HEAL
        (Blinding Flash 220, Enfeeble 117, 784's Poison) -> "condition". WIKI (the
        same hero sentence names conditions); RECONSTRUCTION for a monster, as above.
      * A DAMAGE skill whose condition is a RIDER (Immolate 191's Burning, 224's
        Weakness) -> None: the damage is the point, and the wiki sentence is about
        applying the effect, not about striking. A HEAL -> None. RECONSTRUCTION.
      * A CASTER-CENTRED AREA condition row (840, `area=True`) -> None: it reaches
        every foe around the caster, so one target's condition says nothing about
        the rest. RECONSTRUCTION.
      * Everything else (a plain spell, a signet with no condition, a resurrection)
        -> None: it puts nothing on the target this gate could find.
    """
    code = int(type_code or 0)
    if code in LIVE_EFFECT_SAME_SKILL_TYPES:
        return "same-skill"
    if code in LIVE_EFFECT_NEVER_TYPES:
        return None
    if condition_id is not None and not damages and not heals and not area:
        return "condition"
    return None


def carries_live_effect(table, wearer_id, skill_id, klass, condition_id=None):
    """Why `wearer_id` already carries what the skill would put on it, or None.

    LIVE means an episode still IN the table -- opened and not yet closed by its
    0x0044 -- and not merely inside its stated duration: the client discards every
    repeat 0x0042 for a live (agent, skill) (studies/skills/FINDINGS.md 16.1), and
    what it counts as live is what it has been told, which is the table. An episode
    past its duration but not yet closed therefore still holds the slot until
    effect_tick closes it. The world tick runs effect_tick before the AI ticks, so the
    slot is eligible on the SAME tick as the close -- a RECONSTRUCTION that is faster
    than retail (OBSERVED minimum 0.228 s, 0 of 95 AI re-casts inside 0.2 s of a
    same-skill end; authsrv's SKIP_LIVE_EFFECT banner).
    ANY CASTER: the wiki's sentence is about the target carrying the effect, and
    strongest_per_skill already counts two casters' copies once (Effect stacking).
    """
    if not table or klass is None:
        return None
    live = table.on_agent(wearer_id)
    if klass == "same-skill":
        for ep in live:
            if ep["skill"] == skill_id:
                return f"skill {skill_id} (buff {ep['buff']}, live)"
        return None
    if klass == "condition" and condition_id is not None:
        for ep in live:
            if ep["skill"] == condition_id:
                name = effects.CONDITION_SKILLS.get(condition_id, str(condition_id))
                return f"{name} ({condition_id}, buff {ep['buff']}, live)"
    return None


# ---- CASTAI-RM (2026-10-07; studies/monsterai/FINDINGS.md 18.5): THE REMOVAL GATE'S
# PREDICATES -- "is this a removal slot, and does this body carry what it removes".
# Pure, like the live-effect predicate above: they read a content row and the effect
# table and decide nothing about WHICH slot is cast. The gate that asks them is
# authsrv's `removal_target` (REMOVAL_NEEDS_AFFLICTION), a target step inside the AI
# loops' heal arm -- not a selector, and not a second live_effect_hold call.
#
# The hex type code is the client's own column (effects.EFFECT_TYPES: 4 = hex;
# effects.TYPE_STATUS_BITS maps it to 0x800, the bit retail's removers were cast at).
REMOVAL_HEX_TYPE = 4
REMOVAL_KEYS = (("removes_conditions", "condition"), ("removes_hexes", "hex"))


def removes_some(value):
    """A removal key's value names a removal: "all" or a positive count. A bool is
    refused as a count (True would read as 1 -- a typo, not a row)."""
    if value == "all":
        return True
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def removal_class(erow):
    """'condition' | 'hex' | None -- what a skill_effect row's removal removes.

    'condition' for `removes_conditions` (Mend Condition 275, Restore Condition 276,
    Mend Ailment 277), 'hex' for `removes_hexes` (Remove Hex 301), else None. NOT
    364's singular `removes_condition` ("Charge!"): that is a shout's named side
    effect, never the reason the slot is cast, so it is not a removal slot and stays
    out of this gate (RECONSTRUCTION). A row naming BOTH plural keys asks no single
    question and returns None -- ungated, the pre-gate cast; no row has that shape,
    and the first one should decide its own rule rather than inherit one here.
    """
    if not erow:
        return None
    named = [klass for key, klass in REMOVAL_KEYS if removes_some(erow.get(key))]
    return named[0] if len(named) == 1 else None


def carries_removable(table, aid, klass):
    """Why agent `aid` carries something a `klass` removal would take off, or None.

    'condition': any LIVE episode of one of the ten conditions (effects.CONDITION_SKILLS
    -- the episodes resolve_heal's remove_conditions closes); 'hex': any live episode
    of type 4 (the episodes remove_hexes closes). Live means still in the table, the
    same reading carries_live_effect makes. Any caster, any age.

    OBSERVED, retail (CASTAI-RM1, studies/monsterai 18.5): every AI removal cast on
    tape went at a body carrying the matching status bit -- 106 of 106 condition cures
    (275 x92, 277 x14; castethogram's cond_bit) and 10 of 10 Remove Hex (301; hexed_bit,
    the 11th on the gapped :65009 prefix, zaishenrun --prefix) -- and none at a clean
    one. The status bit is the wire's proxy for the episode this reads.
    """
    if not table or klass not in ("condition", "hex"):
        return None
    for ep in table.on_agent(aid):
        if klass == "condition" and ep["skill"] in effects.CONDITION_SKILLS:
            return (f"{effects.CONDITION_SKILLS[ep['skill']]} ({ep['skill']}, "
                    f"buff {ep['buff']})")
        if klass == "hex" and int(ep.get("type_code", 0) or 0) == REMOVAL_HEX_TYPE:
            return f"hex {ep['skill']} (buff {ep['buff']})"
    return None
