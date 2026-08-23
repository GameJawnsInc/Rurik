r"""The effect MECHANICS: episodes that finally do something, held to the wiki.

    python toolkit/authsrv/test_mechanics.py

R4b's substrate (2026-08-20) opened and closed episodes; this file tests the
2026-08-22 layer that makes them act -- Frenzy's attack speed and doubled
damage, Reversal of Fortune's conversion, the glyph's discount going live,
the preparation bonus, and the gated movement-speed base. Every magnitude
here is either the client's own table read under a stated rule or a
wiki-sourced content row; the checks pin the values GWW itself publishes
(the +33% hammer at exactly 1.1725 s, the rank-12 RoF converting exactly the
134-damage example), so a drift in either the rule or the row goes red
against a number nobody here invented.

Offline: fabricated state, a send collector, no vault and no client.
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks       # noqa: E402
import authsrv      # noqa: E402
import agents       # noqa: E402
import effects      # noqa: E402

# Floor set from a real green run (39 checks, 2026-08-22).
LEDGER = checks.Ledger("effect mechanics", floor=39)
check = checks.adopt(LEDGER)

FRENZY, RUSH, ROF, GLYPH, IGNITE, FAINT = 346, 319, 307, 200, 431, 135
PLAYER = authsrv.PLAYER_AGENT_ID


def collector():
    sent = []
    return sent, lambda op, vals, label="", quiet=False: sent.append(
        (op, list(vals), label))


def fresh_state(health=100.0):
    state = {"agents": {}, "pos": (0.0, 0.0), "player_health": health}
    authsrv.effect_table(state)
    return state


def open_ep(state, skill_id, rank=0, duration=8.0, type_code=None,
            agent=PLAYER):
    if type_code is None:
        type_code = int(agents.WORLD.get("skills", str(skill_id))["type_code"])
    return state["effects"].apply(agent, skill_id, rank, duration,
                                  time.time(), type_code=type_code)


# ---------------------------------------------------------------------------
print("== 1. skill_flat_constant: the bit-clear-EQUAL rule ==")
check(authsrv.skill_flat_constant(FRENZY) == 33,
      "Frenzy's flat 33 reads (scale 33/33, bit clear)")
check(authsrv.skill_flat_constant(RUSH) == 25,
      "Rush's flat 25 reads")
check(authsrv.skill_flat_constant(FAINT) == 50,
      "Faintheartedness's flat 50 reads")
check(authsrv.skill_flat_constant(GLYPH, "bonus_scale") == 2,
      "the glyph's bonus slot reads 2 -- the client's own charge count")
for sid, which, why in ((ROF, "scale", "bit SET -- a progression"),
                        (GLYPH, "scale", "bit clear, 10 != 18")):
    try:
        authsrv.skill_flat_constant(sid, which)
        check(False, f"skill {sid} {which} must refuse ({why})")
    except ValueError:
        check(True, f"skill {sid} {which} refuses ({why})")

print("== 2. attack_interval_factor: GWW's exact table, not /1.33 ==")
state = fresh_state()
check(authsrv.attack_interval_factor(state, PLAYER) == 1.0,
      "no episodes: factor 1.0")
open_ep(state, FRENZY)
factor = authsrv.attack_interval_factor(state, PLAYER)
check(abs(factor - 0.67) < 1e-9, "Frenzy: x(1 - 33/100) = 0.67",
      f"factor={factor}")
hammer = 1.75 * factor
check(abs(hammer - 1.1725) < 1e-9,
      "the hammer lands on GWW's OWN exact value: 1.75 -> 1.1725",
      f"got {hammer}; the /1.33 reading gives {1.75 / 1.33:.4f} and is wrong "
      f"by {abs(1.75 / 1.33 - 1.1725):.3f} s a swing")
open_ep(state, FAINT, type_code=4)     # the hex lands ON the player
both = authsrv.attack_interval_factor(state, PLAYER)
check(abs(both - 0.67 * 1.5) < 1e-9,
      "Frenzy + Faintheartedness compose: 0.67 x 1.5",
      f"factor={both}; the -50% row of the same table is 1.75 -> 2.625")

print("== 3. taker_damage: doubling, then the conversion, in GWW's order ==")
state = fresh_state()
dealt, conv = authsrv.taker_damage(state, PLAYER, 13.0)
check(dealt == 13.0 and conv is None, "no episodes: the hit passes untouched")
open_ep(state, FRENZY)
dealt, conv = authsrv.taker_damage(state, PLAYER, 13.0)
check(dealt == 26.0 and conv is None,
      "Frenzy alone: take double damage, no conversion")
rof = open_ep(state, ROF, rank=12)
dealt, conv = authsrv.taker_damage(state, PLAYER, 67.0)
check(conv is not None and dealt == 67.0
      and conv["heal"] == 67.0 and conv["cap"] == 67.0,
      "GWW's rank-12 example EXACTLY: 67 doubles to 134, cap 67 -- "
      "67 reduced, 67 healed, 67 lands",
      f"dealt={dealt} conv={conv}")
state2 = fresh_state()
open_ep(state2, ROF, rank=12)
dealt, conv = authsrv.taker_damage(state2, PLAYER, 30.0)
check(dealt == 0.0 and conv["heal"] == 30.0 and conv["reduced"] == 30.0,
      "a hit under the cap converts FULLY: 0 lands, 30 healed")

print("== 4. resolve_taker_conversion: heal first, close once ==")
sent, send = collector()
state = fresh_state(health=50.0)
rof = open_ep(state, ROF, rank=12)
dealt, conv = authsrv.taker_damage(state, PLAYER, 30.0)
authsrv.resolve_taker_conversion(send, state, conv, 0)
ops = [op for op, _v, _l in sent]
heal_ix = next(i for i, (op, v, _l) in enumerate(sent)
               if v and v[0] == agents.GV_HEALTH_GAIN)
rm_ix = ops.index(authsrv.GAME_SMSG_EFFECT_REMOVE)
check(heal_ix < rm_ix,
      "the heal goes out BEFORE the episode closes ('healing occurs before "
      "damage', GWW)", f"ops={ops}")
check(state["player_health"] == 80.0,
      "the heal landed for the converted amount", f"{state['player_health']}")
check(not state["effects"].on_agent(PLAYER),
      "the enchantment is GONE -- one packet, one conversion")
dealt, conv = authsrv.taker_damage(state, PLAYER, 30.0)
check(dealt == 30.0 and conv is None,
      "the NEXT hit lands whole -- a conversion cannot fire twice")

print("== 5. skill_heal: the at-cast cap heal is retired ==")
check(authsrv.skill_heal(ROF, 12) is None,
      "Reversal of Fortune heals NOTHING at cast now")
check(authsrv.skill_heal(1, 0) == 82,
      "Healing Signet still heals its endpoint at rank 0")

print("== 6. the glyph is LIVE: wiki row, client formula, real discount ==")
check(authsrv.glyph_energy_amount(GLYPH, 0) == 10
      and authsrv.glyph_energy_amount(GLYPH, 15) == 18,
      "the explicit row carries GWW's 10..18 endpoints")
check(authsrv.glyph_energy_amount(GLYPH, 12) == 16,
      "rank 12 interpolates by the client's own formula: round(10+8*12/15)=16")
state = fresh_state()
base_cost, ep0, disc0 = authsrv.energy_cost_for(state, PLAYER, 194, 12)
check(base_cost == 5 and ep0 is None and disc0 == 0,
      "Flare with no glyph: its own 5, no episode touched")
glyph_ep = open_ep(state, GLYPH, rank=12)
cost, ep, disc = authsrv.energy_cost_for(state, PLAYER, 194, 12)
check(cost == 0 and ep is glyph_ep and disc == 16,
      "under the glyph a 5-energy Flare costs 0 -- the discount floors at "
      "zero (ConstSkill:3769's own direction)", f"cost={cost} disc={disc}")
sent, send = collector()
authsrv.spend_glyph_charge(send, state, glyph_ep, 0, 194)
check(state["effects"].on_agent(PLAYER) and not sent,
      "one charge spent: the episode survives, nothing on the wire")
authsrv.spend_glyph_charge(send, state, glyph_ep, 0, 194)
check(not state["effects"].on_agent(PLAYER)
      and [op for op, _v, _l in sent] == [authsrv.GAME_SMSG_EFFECT_REMOVE],
      "the second spends it: one real 0x0044, episode gone")

print("== 7. the preparation bonus: gated on the weapon, not the type enum ==")
state = fresh_state()
open_ep(state, IGNITE, rank=12, duration=24.0)
bow = {"fires_arrows": True}
bonus, sid = authsrv.swing_preparation_bonus(state, bow, PLAYER)
check(bonus == 15.0 and sid == IGNITE,
      "a bow under Ignite Arrows at rank 12: +15 fire (round(3+15*12/15))",
      f"bonus={bonus}")
bonus, _sid = authsrv.swing_preparation_bonus(state, agents.STARTER_HAMMER,
                                              PLAYER)
check(bonus == 0.0,
      "the starter hammer fires no arrows: the preparation stays inert")
bonus, _sid = authsrv.swing_preparation_bonus(fresh_state(), bow, PLAYER)
check(bonus == 0.0, "a bow with no preparation open: nothing")

print("== 8. the movement lever: off by default, exact when on ==")
state = fresh_state()
open_ep(state, RUSH, rank=12, duration=18.0)
check(authsrv.move_speed_percent(state, PLAYER) == 25.0,
      "Rush reads 25% from its own flat slot")
sent, send = collector()
saved = authsrv.MOVE_SPEED_EFFECTS
try:
    authsrv.MOVE_SPEED_EFFECTS = False
    authsrv.speed_tick(send, state, 0)
    check(not sent, "OFF (the default): the tick declares nothing")
    authsrv.MOVE_SPEED_EFFECTS = True
    authsrv.speed_tick(send, state, 0)
    check(len(sent) == 1
          and sent[0][0] == authsrv.GAME_SMSG_AGENT_UPDATE_SPEED_BASE
          and sent[0][1] == [PLAYER, 360.0],
          "ON with Rush open: ONE 0x0027 declaring 288 x 1.25 = 360",
          f"sent={sent}")
    authsrv.speed_tick(send, state, 0)
    check(len(sent) == 1, "a second tick with nothing changed sends nothing")
    for ep in state["effects"].on_agent(PLAYER):
        state["effects"].close(ep["buff"])
    authsrv.speed_tick(send, state, 0)
    check(len(sent) == 2 and sent[1][1] == [PLAYER, 288.0],
          "the stance ends: the base is RESTORED on the next tick",
          f"sent={sent}")
finally:
    authsrv.MOVE_SPEED_EFFECTS = saved

print("== 9. land_swing end to end: the pipeline in the measured batch ==")
saved_armour = authsrv.ARMOUR_TERM
saved_energy = authsrv.ENERGY
try:
    authsrv.ARMOUR_TERM = False    # a deterministic base hit, no location roll
    authsrv.ENERGY = False         # adrenaline aside; its 0-unit case is
                                   # test_pools' ground
    base = 100.0 * authsrv.ENEMY_HIT_FRACTION

    sent, send = collector()
    state = fresh_state()
    enemy = {"name": "hatcher", "dead": False, "pos": (0.0, 0.0)}
    authsrv.land_swing(send, state, 10, enemy, 0)
    control_drop = 100.0 - state["player_health"]
    check(abs(control_drop - base) < 1e-9,
          "control: the base hit lands unmodified", f"drop={control_drop}")

    sent, send = collector()
    state = fresh_state()
    open_ep(state, FRENZY)
    authsrv.land_swing(send, state, 10, enemy, 0)
    check(abs((100.0 - state["player_health"]) - 2 * base) < 1e-9,
          "under Frenzy the same swing takes exactly double",
          f"drop={100.0 - state['player_health']}")

    sent, send = collector()
    state = fresh_state(health=60.0)
    open_ep(state, ROF, rank=12)
    authsrv.land_swing(send, state, 10, enemy, 0)
    ops = [op for op, _v, _l in sent]
    check(state["player_health"] == 60.0 + base,
          "under RoF the swing heals instead of landing",
          f"health={state['player_health']}")
    first_int = sent[0]
    check(first_int[0] == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
          and first_int[1][0] == agents.GV_MELEE_ATTACK_FINISHED,
          "MELEE_ATTACK_FINISHED still opens the batch -- the swing landed, "
          "its damage did not")
    check(agents.PROP_DAMAGE not in
          [v[0] for op, v, _l in sent
           if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET],
          "and NO damage message follows a fully converted swing")
finally:
    authsrv.ARMOUR_TERM = saved_armour
    authsrv.ENERGY = saved_energy

sys.exit(LEDGER.verdict())
