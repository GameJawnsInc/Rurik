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

# Floor set from a real green run (39 checks, 2026-08-22; 99 checks, 2026-09-09 SKILLS-DW; 129 checks, 2026-09-10 SKILLS-BL).
LEDGER = checks.Ledger("effect mechanics", floor=129)
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

# ---------------------------------------------------------------------------
# SKILLS-DW (2026-09-09): the agent status word, and Deep Wound's maximum.
# studies/skills/FINDINGS.md 41; deepwoundjoin.py is the corpus read.
DEEP_WOUND = effects.CONDITION_BY_NAME["Deep Wound"]
BLEEDING = effects.CONDITION_BY_NAME["Bleeding"]
OP_STATUS = authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
OP_INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
OP_APPLY, OP_REMOVE = authsrv.GAME_SMSG_EFFECT_APPLY, authsrv.GAME_SMSG_EFFECT_REMOVE
ENEMY = 10


def dw_state(health=100.0, enemy=False):
    state = fresh_state(health=health)
    authsrv.player_pools(state)
    state["player_health"] = float(health)
    if enemy:
        state["agents"][ENEMY] = {"name": "hatcher", "dead": False,
                                  "pos": (0.0, 0.0), "health": 100.0,
                                  "max_health": 100.0, "skills": (),
                                  "skill_ready": []}
    return state


def shape(sent):
    """[(opcode, first two values)] -- the batch as a reader would see it."""
    return [(op, tuple(v[:3])) for op, v, _l in sent]


def apply_dw(send, state, target=PLAYER, seconds=10.0):
    return authsrv.apply_condition(send, state, target, DEEP_WOUND, seconds,
                                   12, 0, by_skill=337)


print("== 10. status_word: retail's bits, from the live episodes alone ==")
sw = effects.status_word
check(sw([]) == 0, "no episodes, no bits")
check(sw([{"skill": DEEP_WOUND, "type_code": 8}]) == 0x22,
      "Deep Wound = 0x02 condition | 0x20 deep wound (retail's 0x22, 2 of 2)")
check(sw([{"skill": 483, "type_code": 8}]) == 0x42
      and sw([{"skill": 484, "type_code": 8}]) == 0x42,
      "Disease and Poison share 0x40 (retail 0x42, 1 each)")
check(sw([{"skill": 481, "type_code": 8}]) == 0x0A,
      "Crippled = 0x0A (retail, 2 of 2)")
check(sw([{"skill": BLEEDING, "type_code": 8}]) == 0x03,
      "Bleeding = 0x03 (retail, n=1)")
check(sw([{"skill": 480, "type_code": 8}]) == 0x02
      and sw([{"skill": 2077, "type_code": 8}]) == 0x02,
      "Burning and Cracked Armor carry only the condition bit")
check(sw([{"skill": 135, "type_code": 4}]) == 0x800, "a hex sets 0x800")
check(sw([{"skill": 307, "type_code": 6}]) == 0x80, "an enchantment sets 0x80")
check(sw([{"skill": 348, "type_code": 15}]) == 0
      and sw([{"skill": 346, "type_code": 3}]) == 0,
      "a shout and a stance move nothing (42 of 42 shout applies carried no word)")
check(sw([{"skill": DEEP_WOUND, "type_code": 8},
          {"skill": BLEEDING, "type_code": 8},
          {"skill": 135, "type_code": 4}], dead=True) == 0x833,
      "the word is the OR of everything live plus death (0x10)")

print("== 11. the apply batch on a FULL pool: retail's three messages, in order ==")
sent, send = collector()
state = dw_state()
ep = apply_dw(send, state)
check(ep is not None and ep["skill"] == DEEP_WOUND, "the episode opened")
check(shape(sent)[:3] == [(OP_APPLY, (PLAYER, DEEP_WOUND, 12)),
                          (OP_STATUS, (PLAYER, 0x22)),
                          (OP_INT, (agents.PROP_HEALTH_MAX, PLAYER, 80))],
      "[0x0042 482, 0x00F1 0x22, 0x009F 42=80] -- retail's batch, retail's order",
      f"got {shape(sent)[:3]}")
check(len(sent) == 3, "and nothing else (no regen: Deep Wound has no pips)",
      f"sent {len(sent)}")
check(authsrv.player_max_health(state) == 80.0, "the server's maximum is 80")
check(state["player_health"] == 80.0,
      "a full pool stays full: 100 + (80-100) = 80 of 80 (wiki: still at full health)")
check(state["deep_wound"] == {PLAYER: 20}, "the book holds the 20")
check(authsrv.player_full_max_health(state) == 100.0,
      "the unconditioned maximum the enemy's hit scales from is still 100")

print("== 12. a DAMAGED pool: the client's signed delta, in the server's own book ==")
sent, send = collector()
state = dw_state(health=25.0)
apply_dw(send, state)
check(state["player_health"] == 5.0,
      "25 + (80-100) = 5 -- the number the HUD must read (health_shrink's delta)",
      f"health={state['player_health']}")
sent, send = collector()
state = dw_state(health=10.0)
apply_dw(send, state)
check(state["player_health"] == -10.0 and not state.get("player_dead"),
      "below zero and NOT dead: Deep Wound never kills by itself (wiki)",
      f"health={state['player_health']} dead={state.get('player_dead')}")
saved_armour, saved_energy = authsrv.ARMOUR_TERM, authsrv.ENERGY
try:
    authsrv.ARMOUR_TERM = False
    authsrv.ENERGY = False
    enemy = {"name": "hatcher", "dead": False, "pos": (0.0, 0.0)}
    base = 100.0 * authsrv.ENEMY_HIT_FRACTION
    sent, send = collector()
    authsrv.land_swing(send, state, ENEMY, enemy, 0)
    check(state.get("player_dead") is True,
          "the next health loss triggers it: one swing kills the -10 player")
    # and the blow itself is unchanged by the smaller pool
    sent, send = collector()
    state2 = dw_state(health=100.0)
    apply_dw(send, state2)
    sent, send = collector()
    authsrv.land_swing(send, state2, ENEMY, enemy, 0)
    check(abs((80.0 - state2["player_health"]) - base) < 1e-9,
          "the enemy's swing deals the SAME base hit under Deep Wound "
          "(scaled from the full maximum, not the reduced one)",
          f"drop={80.0 - state2['player_health']} base={base}")
    frac_msgs = [v for op, v, _l in sent
                 if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
                 and v[0] == agents.PROP_DAMAGE]
    check(bool(frac_msgs) and abs(float(frac_msgs[0][3])
                                 - float(authsrv._f32(-base / 80.0))) < 1e-6,
          "the wire fraction divides by the REDUCED maximum, the number the "
          "client holds after our own 0x009F 42",
          f"got {frac_msgs[0][3] if frac_msgs else None} want {authsrv._f32(-base / 80.0)}")
finally:
    authsrv.ARMOUR_TERM, authsrv.ENERGY = saved_armour, saved_energy

print("== 13. healing under Deep Wound: -20%, health gain exempt, a heal can kill ==")
sent, send = collector()
state = dw_state(health=40.0)
apply_dw(send, state)                       # 40 -> 20 of 80
sent, send = collector()
landed = authsrv.heal_agent(send, state, PLAYER, PLAYER, 50.0, 0)
check(landed == 40.0 and state["player_health"] == 60.0,
      "a 50 heal lands 40 (wiki: 20% less benefit from healing)",
      f"landed={landed} health={state['player_health']}")
sent, send = collector()
state = dw_state(health=40.0)
apply_dw(send, state)
landed = authsrv.heal_agent(send, state, PLAYER, PLAYER, 50.0, 0, healing=False)
check(landed == 50.0, "a health GAIN (healing=False, Reversal of Fortune) is not cut",
      f"landed={landed}")
sent, send = collector()
state = dw_state(health=40.0)
landed = authsrv.heal_agent(send, state, PLAYER, PLAYER, 50.0, 0)
check(landed == 50.0, "control: no Deep Wound, the full 50 lands")
sent, send = collector()
state = dw_state(health=10.0)
apply_dw(send, state)                       # -10 of 80
sent, send = collector()
authsrv.heal_agent(send, state, PLAYER, PLAYER, 5.0, 0)
check(state.get("player_dead") is True,
      "a 5 heal (4 after the cut) leaves -6: the gain did not clear zero, "
      "and the player dies (wiki)", f"health={state['player_health']}")
sent, send = collector()
state = dw_state(health=10.0)
apply_dw(send, state)
sent, send = collector()
authsrv.heal_agent(send, state, PLAYER, PLAYER, 20.0, 0)
check(state.get("player_dead") is not True and state["player_health"] == 6.0,
      "a 20 heal (16 after the cut) clears zero: alive at 6",
      f"health={state['player_health']} dead={state.get('player_dead')}")

print("== 14. the close: expiry restores, in retail's order; death strips silently ==")
sent, send = collector()
state = dw_state(health=25.0)
ep = apply_dw(send, state)                  # 5 of 80
ep["expires_at"] = 0.0
sent, send = collector()
authsrv.effect_tick(send, state, 0)
check(shape(sent)[:3] == [(OP_REMOVE, (PLAYER, ep["buff"])),
                          (OP_STATUS, (PLAYER, 0)),
                          (OP_INT, (agents.PROP_HEALTH_MAX, PLAYER, 100))],
      "[0x0044, 0x00F1 0, 0x009F 42=100] -- retail's close, retail's order",
      f"got {shape(sent)[:3]}")
check(state["player_health"] == 25.0 and authsrv.player_max_health(state) == 100.0
      and not state["deep_wound"],
      "the 20 comes back with the maximum: 25 of 100, book empty")
# strip at death
sent, send = collector()
state = dw_state(health=100.0)
apply_dw(send, state)
sent, send = collector()
authsrv.kill_player(send, state, 0, "test")
ops = [op for op, _v, _l in sent]
check(OP_REMOVE in ops, "death strips the episode (0x0044 goes out)")
check(not any(op == OP_INT and v[0] == agents.PROP_HEALTH_MAX
              for op, v, _l in sent),
      "and sends NO 0x009F 42 onto the corpse -- the revive carries the maximum")
check(not state["deep_wound"] and authsrv.player_max_health(state) == 100.0,
      "the book is restored so the revive's own maximum reads 100")
check(state["status_word"][PLAYER] == effects.STATUS_DEAD,
      "the status book records the death word the kill path sent itself")
status_msgs = [v for op, v, _l in sent if op == OP_STATUS]
check(status_msgs == [[PLAYER, agents.EFFECT_DEAD]],
      "exactly ONE status message in the death batch, the measured 0x10",
      f"got {status_msgs}")

print("== 15. a second condition: the word is the whole word ==")
sent, send = collector()
state = dw_state()
apply_dw(send, state)
sent, send = collector()
ep_b = authsrv.apply_condition(send, state, PLAYER, BLEEDING, 10.0, 12, 0,
                               by_skill=382)
words = [v[1] for op, v, _l in sent if op == OP_STATUS]
check(words == [0x23], "Bleeding on top of Deep Wound sends 0x23, the OR",
      f"got {[hex(w) for w in words]}")
# close the Deep Wound alone: 0x03 remains, not 0
for e in state["effects"].on_agent(PLAYER):
    if e["skill"] == DEEP_WOUND:
        e["expires_at"] = 0.0
sent, send = collector()
authsrv.effect_tick(send, state, 0)
words = [v[1] for op, v, _l in sent if op == OP_STATUS]
check(words == [0x03], "closing Deep Wound with Bleeding live leaves 0x03",
      f"got {[hex(w) for w in words]}")
# re-sending the same word is refused: a third condition that adds no bit
sent, send = collector()
authsrv.apply_condition(send, state, PLAYER, 480, 3.0, 12, 0, by_skill=0)
check(not [1 for op, _v, _l in sent if op == OP_STATUS],
      "Burning on top of Bleeding adds no bit and sends no word "
      "(retail: 2 of 7 Burning applies carried none -- the ones with a "
      "condition already live)")

print("== 16. the enemy takes it too, and its heal can kill it ==")
sent, send = collector()
state = dw_state(enemy=True)
apply_dw(send, state, target=ENEMY)
agent = state["agents"][ENEMY]
check(shape(sent)[:3] == [(OP_APPLY, (ENEMY, DEEP_WOUND, 12)),
                          (OP_STATUS, (ENEMY, 0x22)),
                          (OP_INT, (agents.PROP_HEALTH_MAX, ENEMY, 80))],
      "the same batch for an agent", f"got {shape(sent)[:3]}")
check(agent["max_health"] == 80.0 and agent["health"] == 80.0,
      "agent book: 80 of 80")
agent["health"] = -10.0
sent, send = collector()
authsrv.heal_agent(send, state, ENEMY, ENEMY, 5.0, 0)
check(agent["dead"] is True
      and [v for op, v, _l in sent if op == OP_STATUS] == [[ENEMY, agents.EFFECT_DEAD]],
      "a heal that does not clear zero kills the agent through kill_agent's "
      "measured template (status 0x10)")
check(not state["deep_wound"].get(ENEMY) and agent["max_health"] == 100.0,
      "death stripped it and restored the agent's book")

print("== 17. the known-bad arms ==")
saved_dw, saved_sw = authsrv.DEEP_WOUND, authsrv.STATUS_WORD
try:
    authsrv.DEEP_WOUND = False
    sent, send = collector()
    state = dw_state(health=25.0)
    apply_dw(send, state)
    check(shape(sent) == [(OP_APPLY, (PLAYER, DEEP_WOUND, 12)),
                          (OP_STATUS, (PLAYER, 0x22))],
          "--no-deep-wound: the apply and the word, no maximum", f"got {shape(sent)}")
    check(state["player_health"] == 25.0 and authsrv.player_max_health(state) == 100.0,
          "and the books do not move")
    sent, send = collector()
    check(authsrv.heal_agent(send, state, PLAYER, PLAYER, 50.0, 0) == 50.0,
          "and heals are not cut")
    authsrv.DEEP_WOUND = True
    authsrv.STATUS_WORD = False
    sent, send = collector()
    state = dw_state()
    apply_dw(send, state)
    check(shape(sent) == [(OP_APPLY, (PLAYER, DEEP_WOUND, 12)),
                          (OP_INT, (agents.PROP_HEALTH_MAX, PLAYER, 80))],
          "--no-status-word: the apply and the maximum, no word -- the "
          "pre-2026-09-09 wire plus the new mechanic", f"got {shape(sent)}")
finally:
    authsrv.DEEP_WOUND, authsrv.STATUS_WORD = saved_dw, saved_sw

print("== 18. the reduction rule: 20%, capped at 100 ==")
check(authsrv.deep_wound_reduction(480) == 96, "480 -> 96 (retail's 384, 2 of 2)")
check(authsrv.deep_wound_reduction(100) == 20, "100 -> 20")
check(authsrv.deep_wound_reduction(600) == 100, "600 -> 100: the wiki's cap binds")
check(authsrv.deep_wound_reduction(505) == 100, "505 -> 100, not 101")

print("== 19. the corpus, with no free parameter (deepwoundjoin) ==")
try:
    import deepwoundjoin
    rows = deepwoundjoin.census()
    n, joined, exact, cj, ce, stray, orders = deepwoundjoin.score(rows)
    check(n >= 2, f"the live corpus holds Deep Wound applies (n={n})")
    check(joined == n and exact == n,
          "every 482 apply is joined to a same-batch prop-42 of exactly 0.8x",
          f"n={n} joined={joined} exact={exact}")
    check(cj == ce and ce >= 2,
          "every close restores the previous maximum", f"joined={cj} exact={ce}")
    check(stray == 0, "no other prop-42 moves inside a Deep Wound episode")
    check(orders == [2],
          "the prop-42 sits exactly two messages behind the effect message "
          "(the status word between them), on every apply and close",
          f"offsets={orders}")
    sc = deepwoundjoin.status_census()
    def newly(skill):
        return set(sc["set"].get(skill, {}))
    check(newly(482) <= {0x22, 0x20} and sc["n"].get(482, 0) >= 2,
          "482's apply sets 0x20 (with 0x02 when no condition was live)",
          f"{ {hex(b) for b in newly(482)} }")
    check(newly(481) == {0x0A}, "481 sets 0x0A")
    check(newly(483) == {0x42} and newly(484) == {0x42}, "483 and 484 set 0x42")
    check(newly(160) == {0x80} and sc["set"][160][0x80] >= 50,
          "the enchantment 160 sets 0x80, fifty-plus times")
    check(newly(179) == {0x800}, "the hex 179 sets 0x800")
    check(sc["no_status"].get(364, 0) >= 40 and not newly(364) - {0},
          "the shout 364 moves no bit (40+ applies with no word)")
except Exception as exc:                                     # noqa: BLE001
    LEDGER.skip("section 19 (corpus)", f"{type(exc).__name__}: {exc}")

# -- 20. SKILLS-HN: the heal number needs no sibling, and retail sends the
#        overheal (studies/skills/FINDINGS.md 42; healjoin.py is the corpus
#        read, its predictions P1-P4 in its docstring). FLOORS, not values: the
#        live corpus grows on confirming evidence, so a count pinned exactly
#        would redden on the next capture.
print("== 20. the heal batch on retail's wire, and the overheal (healjoin) ==")
try:
    import healjoin
    hs = healjoin.score(healjoin.census())
    check(hs["n"] >= 800, f"the live corpus holds property-55 gains (n={hs['n']})")
    check(hs["positive"] >= 0.99 * hs["n"],
          "P1: 55 is the health-GAIN direction, positive in 99%+",
          f"{hs['positive']} of {hs['n']}")
    check(hs["within_known"] >= 0.85 * hs["n"],
          "P2: a heal's same-agent siblings are messages this server already "
          "sends (58, the 20/21 visuals, 8, 42, another 55) in 85%+ of batches "
          "(measured 90.0% on 800; the floor sits under it on purpose)",
          f"{hs['within_known']} of {hs['n']} -- outside the set: "
          + ", ".join(f"{k} x{v}" for k, v in hs["siblings"].items()
                      if k not in ("9F:58", "9F:21", "A0:20", "9F:8", "9F:42",
                                   "A3:55")))
    check(hs["bare_58_55"] >= 150,
          "P2: the bare [58, 55] batch -- a heal with nothing else "
          "target-facing -- is common, so no sibling is REQUIRED to draw",
          f"{hs['bare_58_55']} bare batches")
    check(hs["tick_heal"] == hs["n"] and hs["tick_damage"] == hs["n_damage"],
          "P3: the world tick 0x001E closes every heal AND every damage batch "
          "-- a terminator, not a candidate",
          f"heals {hs['tick_heal']}/{hs['n']}, damage "
          f"{hs['tick_damage']}/{hs['n_damage']}")
    check(hs["virgin"] >= 40 and all(v > 0 for v in hs["virgin_values"]),
          "P4: retail sends a positive 55 onto a pool that is FULL by "
          "construction (no prior loss on the connection) -- the overheal is "
          "on the wire, the client clamps",
          f"{hs['virgin']} virgin-pool heals, values {hs['virgin_values']}")
    check(hs["exceeds_loss"] >= 500,
          "P4: and most heals exceed the loss the ledger still owes "
          "(a floor -- the ledger is regen-blind)",
          f"{hs['exceeds_loss']} of {hs['non_virgin']}")
except Exception as exc:                                     # noqa: BLE001
    LEDGER.skip("section 20 (corpus)", f"{type(exc).__name__}: {exc}")


# ---------------------------------------------------------------------------
# 21-23: SKILLS-BL, Blind (studies/skills/FINDINGS.md 44; missjoin.py is the
#        corpus read). The RATE is WIKI (GWW "Blind": 90%), the SHAPE is the
#        client's own attack-fail word read out of its drain (agents.py).
print("== 21. SKILLS-BL: a blinded hostile's swing misses nine in ten, and the "
      "miss is [close, 0x00A0 [38, PLAYER, agent, 3]] ==")
INT, INT_T = (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
              authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET)
FLOAT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
BLIND_ID = effects.CONDITION_BY_NAME["Blind"]
ENEMY = 10


def damage_props(sent):
    return [v[0] for op, v, _l in sent if op == FLOAT_T
            and v[0] in (agents.PROP_DAMAGE, agents.GV_CRITICAL)]


def fail_words(sent):
    return [v for op, v, _l in sent if op == INT_T
            and v[0] == agents.GV_ATTACK_FAIL]


check(BLIND_ID == 479 and agents.GV_ATTACK_FAIL == 38
      and agents.ATTACK_FAIL_REASONS[agents.ATTACK_FAIL_MISS] == "miss",
      "479 is Blind (isle R4-2), 38 is the attack-fail word and reason 3 is "
      "the archive's 'miss' (string id 476 via the drain's table at 0x007FA574)")
check(abs(authsrv.BLIND_MISS_CHANCE - 0.90) < 1e-12,
      "the rate is the wiki's 90%, WIKI and not measured -- 0 of 1,042 "
      "retail closes were swung blind (missjoin P2 NO WITNESS)")

saved = (authsrv.ARMOUR_TERM, authsrv.ENERGY, authsrv.BLIND,
         authsrv.random.random)
try:
    authsrv.ARMOUR_TERM = False
    authsrv.ENERGY = False
    enemy = {"name": "hatcher", "dead": False, "pos": (0.0, 0.0)}

    authsrv.random.random = lambda: 0.0        # a roll that WOULD miss
    sent, send = collector()
    state = fresh_state()
    authsrv.land_swing(send, state, ENEMY, enemy, 0)
    check(state["player_health"] < 100.0 and not fail_words(sent),
          "control: no Blind on the swinger, the roll is never consulted and "
          "the swing lands", f"health={state['player_health']} sent={sent}")

    authsrv.random.random = lambda: 0.5        # < 0.9: a miss
    sent, send = collector()
    state = fresh_state()
    open_ep(state, BLIND_ID, duration=9.0, type_code=8, agent=ENEMY)
    authsrv.land_swing(send, state, ENEMY, enemy, 0)
    check(state["player_health"] == 100.0,
          "under Blind a 0.5 roll misses: the player's pool is untouched",
          f"health={state['player_health']}")
    check(len(sent) == 2
          and sent[0][0] == INT
          and sent[0][1] == [agents.GV_MELEE_ATTACK_FINISHED, ENEMY, 0]
          and sent[1][0] == INT_T
          and sent[1][1] == [agents.GV_ATTACK_FAIL, PLAYER, ENEMY,
                             agents.ATTACK_FAIL_MISS],
          "the wire is exactly [melee_attack_finished, 0x00A0 [38, PLAYER, "
          "agent, 3]] -- the close first, the word beside the TARGET, nothing "
          "else", f"sent={sent}")
    check(not damage_props(sent), "and no damage message at all")

    authsrv.random.random = lambda: 0.95       # >= 0.9: the one in ten
    sent, send = collector()
    state = fresh_state()
    open_ep(state, BLIND_ID, duration=9.0, type_code=8, agent=ENEMY)
    authsrv.land_swing(send, state, ENEMY, enemy, 0)
    check(state["player_health"] < 100.0 and not fail_words(sent)
          and damage_props(sent) == [agents.PROP_DAMAGE],
          "the one in ten lands whole: damage, no fail word",
          f"health={state['player_health']} sent={sent}")

    authsrv.random.random = lambda: 0.9        # the boundary is exclusive
    sent, send = collector()
    state = fresh_state()
    open_ep(state, BLIND_ID, duration=9.0, type_code=8, agent=ENEMY)
    authsrv.land_swing(send, state, ENEMY, enemy, 0)
    check(state["player_health"] < 100.0 and not fail_words(sent),
          "a roll of exactly 0.90 lands (strict less-than, so the miss "
          "fraction is 0.90 and not 0.90 + epsilon)")

    authsrv.random.random = lambda: 0.5
    sent, send = collector()
    state = fresh_state()
    ep = open_ep(state, BLIND_ID, duration=9.0, type_code=8, agent=ENEMY)
    state["effects"].close(ep["buff"])
    authsrv.land_swing(send, state, ENEMY, enemy, 0)
    check(state["player_health"] < 100.0 and not fail_words(sent),
          "a CLOSED Blind episode no longer makes the swing miss")

    authsrv.BLIND = False
    sent, send = collector()
    state = fresh_state()
    open_ep(state, BLIND_ID, duration=9.0, type_code=8, agent=ENEMY)
    authsrv.land_swing(send, state, ENEMY, enemy, 0)
    check(state["player_health"] < 100.0 and not fail_words(sent),
          "--no-blind (the known-bad arm): the same blinded swing lands")
    authsrv.BLIND = True
finally:
    (authsrv.ARMOUR_TERM, authsrv.ENERGY, authsrv.BLIND,
     authsrv.random.random) = saved

print("== 22. SKILLS-BL: the PLAYER swings blind -- the bracket goes out, then "
      "the word beside the TARGET, no damage and no strike; a spell never "
      "misses ==")
saved = (authsrv.ARMOUR_TERM, authsrv.ENERGY, authsrv.BLIND,
         authsrv.random.random, authsrv.SWING_HOLDS_WALK_GATE)


def enemy_state():
    state = fresh_state()
    state["agents"] = {ENEMY: {"name": "t", "dead": False, "died_at": 0.0,
                               "health": 5000.0, "max_health": 5000.0,
                               "last_hit": 0.0, "armor_rating": 60,
                               "pos": (0.0, 0.0)}}
    return state


try:
    authsrv.ARMOUR_TERM = False
    authsrv.ENERGY = False
    authsrv.SWING_HOLDS_WALK_GATE = False

    authsrv.random.random = lambda: 0.5
    sent, send = collector()
    state = enemy_state()
    open_ep(state, BLIND_ID, duration=9.0, type_code=8, agent=PLAYER)
    authsrv.hit_enemy(send, state, ENEMY, 0)
    check(state["agents"][ENEMY]["health"] == 5000.0,
          "the blinded player's swing deals nothing",
          f"health={state['agents'][ENEMY]['health']}")
    check([(op, v) for op, v, _l in sent] == [
              (INT_T, [agents.GV_ATTACK_STARTED, PLAYER, ENEMY, 0]),
              (INT, [agents.GV_MELEE_ATTACK_FINISHED, PLAYER, 0]),
              (INT_T, [agents.GV_ATTACK_FAIL, ENEMY, PLAYER,
                       agents.ATTACK_FAIL_MISS])],
          "the wire is [attack_started, melee_attack_finished, 0x00A0 [38, "
          "ENEMY, PLAYER, 3]] and nothing else", f"sent={sent}")
    before = len(sent)
    authsrv.hit_enemy(send, state, ENEMY, 0)
    check(len(sent) == before,
          "the miss SPENT the swing timer: an immediate second call sends "
          "nothing (the swing happened, it just did not land)")

    authsrv.random.random = lambda: 0.95
    sent, send = collector()
    state = enemy_state()
    open_ep(state, BLIND_ID, duration=9.0, type_code=8, agent=PLAYER)
    authsrv.hit_enemy(send, state, ENEMY, 0)
    check(state["agents"][ENEMY]["health"] < 5000.0 and not fail_words(sent),
          "the one in ten lands: damage, no fail word", f"sent={sent}")

    authsrv.random.random = lambda: 0.0
    sent, send = collector()
    state = enemy_state()
    open_ep(state, BLIND_ID, duration=9.0, type_code=8, agent=PLAYER)
    authsrv.hit_enemy(send, state, ENEMY, 0, exact=20.0, swing=False,
                      label="Flare")
    check(state["agents"][ENEMY]["health"] == 4980.0 and not fail_words(sent),
          "a SPELL cast blind lands its 20 whatever the roll -- GWW: 'melee "
          "and missile attacks', a spell is neither", f"sent={sent}")

    authsrv.random.random = lambda: 0.5
    sent, send = collector()
    state = enemy_state()
    open_ep(state, BLIND_ID, duration=9.0, type_code=8, agent=PLAYER)
    authsrv.hit_enemy(send, state, ENEMY, 0, bonus_damage=10.0,
                      skill_strike=True, label="an attack skill")
    check(state["agents"][ENEMY]["health"] == 5000.0
          and [(op, v) for op, v, _l in sent] == [
              (INT_T, [agents.GV_ATTACK_FAIL, ENEMY, PLAYER,
                       agents.ATTACK_FAIL_MISS])],
          "an ATTACK SKILL's strike misses too, and its wire is the word "
          "alone -- the skill's own prop 46 close is the caller's, exactly "
          "the [46, 38] batch retail's one witness carries", f"sent={sent}")

    sent, send = collector()
    state = enemy_state()
    authsrv.hit_enemy(send, state, ENEMY, 0)
    check(state["agents"][ENEMY]["health"] < 5000.0 and not fail_words(sent),
          "control: unblinded, the 0.5 roll is never consulted")
finally:
    (authsrv.ARMOUR_TERM, authsrv.ENERGY, authsrv.BLIND,
     authsrv.random.random, authsrv.SWING_HOLDS_WALK_GATE) = saved

print("== 23. the corpus: retail's swings close WITH damage, no swing was ever "
      "swung blind, and property 38 rides with none (missjoin) ==")
try:
    import missjoin
    ms = missjoin.score(missjoin.census())
    check(ms["closes"] >= 1000,
          "at least 1,000 retail swing closes framed (measured 1,042)",
          f"closes={ms['closes']}")
    check(ms["p1"] and ms["p1_rate"] < 0.02,
          "P1: an unblinded close carries its damage -- no-damage closes under "
          "2% (measured 7 of 1,042 = 0.67%, and every one of the seven is a "
          "dead or unreachable target, not a miss)",
          f"rate={ms['p1_rate']}")
    check(ms["blind"] == 0,
          "P2 NO WITNESS, pinned: no retail swing close under a live 479. THE "
          "DAY THIS GOES RED THE 90% CAN BE MEASURED -- move the rate from "
          "WIKI to OBSERVED and retire this check",
          f"blind closes={ms['blind']}")
    check(ms["fails"] >= 1 and ms["fail_reasons"].get(2, 0) >= 1,
          "property 38 is on retail's wire, reason 2 'fail' at least once "
          "(20260819T132414 [38, 217, 27, 2])", f"reasons={ms['fail_reasons']}")
    check(ms["p5"] is True,
          "P5: no property 38 shares its batch with damage from that attacker "
          "onto that target -- the word and the number are exclusive",
          f"with damage={ms['fail_with_damage']}")
    check(ms["fail_blind"] == 0 and 3 not in ms["fail_reasons"],
          "and no witnessed 38 is a Blind miss (reason 3) -- so the miss's "
          "own batch shape is RECONSTRUCTION by analogy with reason 2's",
          f"reasons={ms['fail_reasons']} blind={ms['fail_blind']}")
except Exception as exc:                                     # noqa: BLE001
    LEDGER.skip("section 23 (corpus)", f"{type(exc).__name__}: {exc}")

sys.exit(LEDGER.verdict())
