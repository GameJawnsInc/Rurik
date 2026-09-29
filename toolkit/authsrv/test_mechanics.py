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
import math
import time
import struct
import random
import inspect

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks       # noqa: E402
import authsrv      # noqa: E402
import agents       # noqa: E402
import effects      # noqa: E402
import combatmath   # noqa: E402

# Floor set from a real green run (39 checks, 2026-08-22; 99 checks, 2026-09-09 SKILLS-DW; 129 checks, 2026-09-10 SKILLS-BL; 153 checks, 2026-09-10 SKILLS-RC; 162 checks, 2026-09-10 SKILLS-MA).
LEDGER = checks.Ledger("effect mechanics", floor=383)  # 2026-09-29 (RANGERPRE-S3): +4 -- sec.16c a rate back at zero is +0.0 (a foe's and the player's Bleeding expiry, the --regen-zero-signed known-bad arm, the source); measured 383; before that 2026-09-29 (RANGERPRE-S1): +10 -- sec.16b the floored Deep Wound on retail's two edges (64 -> 52 and its [44] / next-hit 42 / word, 483 -> 387, the round() and --no-deep-wound known-bad arms, the close's re-division) and sec.18's 64, 483, the 1..2000 sweep and predicted_max against the server; measured 379; before that 2026-09-28 (CASTAI-Z1 round 3): +1 -- sec.20 healjoin P2's annotation test with BOTH conjuncts (never-beside-damage exact per tape, no candidate over the corpus); measured 369; before that 2026-09-28 (CASTAI-Z1, the Zaishen capture): +10 -- sec.19 the Deep Wound stacking signature and its witness (P1 / P3 pin-scoped); sec.20 P1 / P2 recorded FAILED as written, the allegiance-token signature, the healjoin-P2 annotation signature, the token pass's gapped set-aside and its reader cross-check, P1c / P2c on the capture; measured 368; before that 2026-09-27 (the cast-time word): +3 -- sec.41 property 61 ahead of a modified cast's [60] (the Dazed press, the Rusted untargeted signet, the attack skill that sends none, the revert; a Dazed hostile; the source); measured 358; before that 2026-09-27 (the D6 client runs): +1 -- sec.37 one episode per skill (strongest_per_skill): two Rusts x2 not x4, Suffering and Shadow of Fear re-applied count once, two different skills still combine; measured 355; before that 2026-09-27 (the D6 review's repair): +17 -- sec.35 the cap that binds (M1) and the [44] at the apply through land_skill (HEX-2); sec.36 the four body gates through the real functions (M8); sec.37 the press and ally_cast_tick under Rust (M3); sec.38 the player's chain through the real press + E5 (M4); sec.39 200 AR (M2), the Core reading's arm (R34-3), the scythe and the splash (M9), the shield inside the leaf (R34-7); sec.40 the spell word on a Dazed caster (M7), the press and ally_cast_tick under Dazed (M3); the source locks through _lock (M13), main()'s eight flips pinned (M10); sec.16's heal-kill re-pinned to the whole death word + step-down (EV-2); MEASURED from the green run, 354 checks, floor 337 -> 354  2026-09-27 (later): +40, DESKWORK-D6 B4 sec.39-40 (Cracked Armor: -20 into the bonus category before the cap and the penetration, the floor, the player and the five body sites; Dazed: spells x2, a landed attack or Dazed itself landing interrupts the spell in activation, never a signet or a swing), from the green run  # 2026-09-27: +40, DESKWORK-D6 B2 sec.35-38 (Suffering's hex pips, Soothing Images' adrenaline block, Rust's explicit damage + signet x2, Panic's chain), from the green run  # 2026-09-26: +1, sec.16 (a HOSTILE's heal-kill under Deep Wound still pays the kill reward -- the control on hurt_agent_row's rule at heal_agent's door; the party arm is test_agentlife JARIN-S 5b), from the green run  # 2026-09-23: +11, SKILLS-MC sec.34 (Mend Condition: heal IF removed, the no-condition control, the other-ally byte, the revert), from the green run  # 2026-09-17: +5, RUN-SKILLS-WKL sec.33 + WKL1-2 (a cast that lifts Weakness heals at the weakened rank), from the green run  # 2026-09-17: +12, SKILLS-WK sec.31-32 (Weakness takes one off every attribute), from the green run  # 2026-09-16: +14, SLICE-F48 sec.8b (movement speed on the wire), from the green run  # 2026-09-14 (late night): +2, PVPMAX sec.16 (the 42 rides the next hit)  # 2026-09-14 (night): +2, SLICE-H17's rank sweep and not-a-double   # SLICE-H14 +7 (section 30), from the green run; JARIN-S +4 (section 7b rewritten), from the green run; MANTID-S +17 (section 29), from the green run; SLICE-H13 +6 (section 7b), from the green run; SLICE-B7a +4, B7c +8; from the green run
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

print("== 3. taker_damage: Frenzy's percent at the taker's Strength, then the "
      "conversion, in GWW's order ==")
# SLICE-H17 (2026-09-14): Frenzy is "take 175..125 % damage" at Strength on
# the client's own 38888 row (content/world.toml), not the 2023 wiki's double
# -- the WARRIOR-PRE tape refuted the double (slice FINDINGS F45). The expected
# number is DERIVED here from the fixture's own Strength rank, the way the
# server derives it, and the rank sweep below is what makes it falsifiable.
STR = dict(agents.PLAYER_ATTRIBUTE_RANKS).get(17, 0)
FRENZY_MULT = round(175 + (125 - 175) * STR / 15.0) / 100.0
state = fresh_state()
dealt, conv = authsrv.taker_damage(state, PLAYER, 13.0)
check(dealt == 13.0 and conv is None, "no episodes: the hit passes untouched")
open_ep(state, FRENZY)
dealt, conv = authsrv.taker_damage(state, PLAYER, 13.0)
check(abs(dealt - 13.0 * FRENZY_MULT) < 1e-9 and conv is None,
      f"Frenzy alone at Strength {STR}: x{FRENZY_MULT} (175..125 % on 38888), "
      f"no conversion", f"dealt={dealt}")
check(abs(dealt - 26.0) > 1e-9 or FRENZY_MULT == 2.0,
      "and it is NOT the 2023 double (0 of 18 hits on the WARRIOR-PRE tape "
      "sat where a double puts them)")
_saved = agents.PLAYER_ATTRIBUTE_RANKS
try:
    sweep = {}
    for r in (0, 3, 9, 15):
        agents.PLAYER_ATTRIBUTE_RANKS = ((17, r),)
        _s = fresh_state()
        open_ep(_s, FRENZY)
        sweep[r] = authsrv.taker_damage(_s, PLAYER, 100.0)[0]
finally:
    agents.PLAYER_ATTRIBUTE_RANKS = _saved
check(sweep == {0: 175.0, 3: 165.0, 9: 145.0, 15: 125.0},
      "the rank sweep: 175 at Strength 0, 165 at 3, 145 at 9, 125 at 15 -- "
      "the client's own endpoints, interpolated and rounded its way",
      f"{sweep}")
rof = open_ep(state, ROF, rank=12)
dealt, conv = authsrv.taker_damage(state, PLAYER, 67.0)
check(conv is not None and abs(dealt - (67.0 * FRENZY_MULT - 67.0)) < 1e-9
      and conv["heal"] == 67.0 and conv["cap"] == 67.0,
      f"GWW's rank-12 example at the new number: 67 x{FRENZY_MULT} = "
      f"{67.0 * FRENZY_MULT:.2f}, cap 67 -- 67 reduced, 67 healed, the rest lands",
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

print("== 7b. SLICE-H13 / JARIN: the attack-speed pair follows the stance, and rides the next start ==")
# The server paced Frenzy's swings since 2026-08-22; the CLIENT animates to
# the 0x0035 pair it holds (base x modifier, 0x007F837E). H13: one resend per
# change of the factor. JARIN (studies/slice F39): retail sends that resend
# WITH the agent's next attack start -- 19 of 19 on the hero tape, never at
# the stance's apply, nothing at its close (the 1.0 rides the next chain's
# first start). So the tick RECORDS the change and the start SENDS it;
# --attack-speed-at-change is H13's tick-time send.
state = fresh_state()
state["agents"] = {10: {"name": "bandit", "dead": False, "attack_speed": 1.33}}
sent, send = collector()
saved_sync, saved_start = authsrv.ATTACK_SPEED_SYNC, authsrv.ATTACK_SPEED_AT_START
try:
    authsrv.ATTACK_SPEED_SYNC = True
    authsrv.ATTACK_SPEED_AT_START = True
    authsrv.attack_speed_tick(send, state, 0)
    check(not sent and not authsrv.attack_speed_flush(send, state, PLAYER),
          "nothing open, nothing sent and nothing pending -- the load's declaration stands")
    ep = open_ep(state, 346, rank=9, duration=8.0)                 # Frenzy
    authsrv.attack_speed_tick(send, state, 0)
    ws = authsrv.WEAPON_ATTACK_SPEED
    check(not sent and abs(state["attack_speed_pending"].get(PLAYER, (0, 0.0))[1] - 0.67) < 1e-6,
          "Frenzy opens: the tick sends NOTHING and records 0.67 as pending -- "
          "retail's six out-of-combat applies sent no 0x0035", f"sent={sent}")
    flushed = authsrv.attack_speed_flush(send, state, PLAYER)
    check(flushed and len(sent) == 1
          and sent[0][0] == authsrv.GAME_SMSG_AGENT_UPDATE_ATTACK_SPEED
          and sent[0][1] == [PLAYER, authsrv._f32(ws), authsrv._f32(0.67)],
          "the next attack start flushes ONE 0x0035 [player, base, 0.67] -- the "
          "client's modifier field (studies/enemy PLAN 6q: 0.67 = +33% IAS), the "
          "base unchanged, in the start's own instant (19 of 19)", f"sent={sent}")
    check(not authsrv.attack_speed_flush(send, state, PLAYER) and len(sent) == 1,
          "a second start sends nothing more -- the pending pair was consumed")
    authsrv.attack_speed_tick(send, state, 0)
    check(len(sent) == 1 and PLAYER not in state["attack_speed_pending"],
          "a second tick with the stance still open records nothing")
    state["effects"].close(ep["buff"])
    authsrv.attack_speed_tick(send, state, 0)
    check(len(sent) == 1, "the stance closes: the tick sends nothing (retail sends "
          "nothing at a close)")
    authsrv.attack_speed_flush(send, state, PLAYER)
    check(len(sent) == 2
          and sent[1][1] == [PLAYER, authsrv._f32(ws), authsrv._f32(1.0)],
          "...and the next chain's first start restores modifier 1.0 -- ONE 0x0035",
          f"sent={sent[1:]}")
    # a BODY under a stance: its own base, its own modifier, riding ITS start
    sent.clear()
    bep = open_ep(state, 346, rank=0, duration=8.0, agent=10)
    authsrv.attack_speed_tick(send, state, 0)
    authsrv.start_swing(send, 10, 0, target_id=PLAYER, state=state)
    check([(op, v) for op, v, _l in sent][:2]
          == [(authsrv.GAME_SMSG_AGENT_UPDATE_ATTACK_SPEED,
               [10, authsrv._f32(1.33), authsrv._f32(0.67)]),
              (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET,
               [authsrv.agents.GV_ATTACK_STARTED, 10, PLAYER, 0])]
          and PLAYER not in state["attack_speed_pending"],
          "a body under Frenzy: start_swing puts [body, its 1.33, 0.67] IMMEDIATELY "
          "before its own attack start (the tape's instant), and the player, "
          "unchanged at 1.0, is not re-declared", f"sent={sent}")
    # THE REVERT ARM: --attack-speed-at-change is H13's shape, sent at the tick.
    state["effects"].close(bep["buff"])
    sent.clear()
    authsrv.ATTACK_SPEED_AT_START = False
    authsrv.attack_speed_tick(send, state, 0)
    check([(op, v) for op, v, _l in sent]
          == [(authsrv.GAME_SMSG_AGENT_UPDATE_ATTACK_SPEED,
               [10, authsrv._f32(1.33), authsrv._f32(1.0)])]
          and not state.get("attack_speed_pending"),
          "REVERT ARM (--attack-speed-at-change): the close is declared AT THE TICK, "
          "nothing pending -- SLICE-H13's shape", f"sent={sent}")
    sent.clear()
    authsrv.ATTACK_SPEED_SYNC = False
    open_ep(state, 346, rank=0, duration=8.0, agent=10)
    authsrv.attack_speed_tick(send, state, 0)
    check(not sent, "REVERT ARM (--no-attack-speed-sync): nothing is ever "
          "re-declared; the pre-H13 shape")
finally:
    authsrv.ATTACK_SPEED_SYNC, authsrv.ATTACK_SPEED_AT_START = saved_sync, saved_start

print("== 8. the movement speed base: on by default (SLICE-F48), exact, one word per change ==")
state = fresh_state()
open_ep(state, RUSH, rank=12, duration=18.0)
check(authsrv.move_speed_percent(state, PLAYER) == 25.0,
      "Rush reads 25% from its own flat slot")
sent, send = collector()
saved = authsrv.MOVE_SPEED_EFFECTS
try:
    authsrv.MOVE_SPEED_EFFECTS = False
    authsrv.speed_tick(send, state, 0)
    check(not sent, "OFF (--no-move-speed-effects, the revert arm): the tick declares nothing")
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

print("== 8b. SLICE-F48: the retail arithmetic -- x1.33, x0.5, x0.665, the 34% cap, the cure ==")
CHARGE, WINDBORNE, CRIPPLED_ID = 364, 160, effects.CONDITION_BY_NAME["Crippled"]
saved = authsrv.MOVE_SPEED_EFFECTS
try:
    authsrv.MOVE_SPEED_EFFECTS = True
    # Windborne Speed alone: retail's 288 -> 383.04 (51 applies).
    state = fresh_state()
    sent, send = collector()
    open_ep(state, WINDBORNE, rank=15, duration=13.0)
    authsrv.push_speed(send, state, PLAYER, 0)
    check(len(sent) == 1 and abs(sent[0][1][1] - 383.04) < 1e-6,
          "Windborne Speed open: 288 x 1.33 = 383.04 on the wire", f"sent={sent}")
    # "Charge!" is a Shout and opens NOTHING by type; the content row's
    # `opens_episode` is the door, and the episode carries the same 33.
    row = agents.WORLD.get("skills", str(CHARGE))
    check(effects.applies_effect(row) is None
          and agents.WORLD.get("skill_effect", str(CHARGE)).get("opens_episode") == "shout",
          "\"Charge!\" opens by its content row, not by its type (the type list is unchanged)")
    open_ep(state, CHARGE, rank=10, duration=10.0, type_code=15)
    authsrv.push_speed(send, state, PLAYER, 0)
    check(len(sent) == 2 and abs(sent[1][1][1] - 385.92) < 1e-6,
          "a second 33% boost over the first: 288 x 1.34 = 385.92 -- GWW's +34% cap, "
          "retail's 8 of 8 (not x1.33, not x1.77)", f"sent={sent}")
    # Crippled alone: 288 -> 144.0 (the Isle's Pin Down).
    state = fresh_state()
    sent, send = collector()
    authsrv.apply_condition(send, state, PLAYER, CRIPPLED_ID, 13.0, 13, 0, by_skill=392)
    ops = [op for op, _v, _l in sent]
    check(ops.count(authsrv.GAME_SMSG_AGENT_UPDATE_SPEED_BASE) == 1
          and sent[-1][1] == [PLAYER, 144.0]
          and ops.index(authsrv.GAME_SMSG_AGENT_UPDATE_STATUS)
          < ops.index(authsrv.GAME_SMSG_AGENT_UPDATE_SPEED_BASE),
          "Crippled: [0x0042 481, 0x00F1, 0x0027 144.0] -- the word behind the status, "
          "as on the Isle", f"ops={[hex(o) for o in ops]}")
    check(abs(authsrv.move_speed_factor(state, PLAYER) - 0.5) < 1e-9,
          "the factor is 0.5 exactly")
    # Crippled OVER a boost: x0.665, multiplicative (21 of 21 retail rows; the
    # additive 0.83 appears nowhere).
    open_ep(state, WINDBORNE, rank=15, duration=13.0)
    authsrv.push_speed(send, state, PLAYER, 0)
    check(abs(sent[-1][1][1] - 191.52) < 1e-6,
          "Windborne over Crippled: 288 x 1.33 x 0.5 = 191.52 (the Isle's own 191.52)",
          f"last={sent[-1]}")
    check(abs(authsrv.move_speed_factor(state, PLAYER) - 0.665) < 1e-9,
          "the factor is 0.665, not the additive 0.83")
    # "Charge!" cures Crippled (its initial effect) and boosts: the cast path.
    state = fresh_state()
    sent, send = collector()
    authsrv.apply_condition(send, state, PLAYER, CRIPPLED_ID, 13.0, 13, 0, by_skill=392)
    del sent[:]
    ep = authsrv.apply_effect(send, state, PLAYER, CHARGE, 10, PLAYER, 0)
    ops = [op for op, _v, _l in sent]
    check(ep is not None and ep["skill"] == CHARGE and ep["duration"] == 10.0,
          "\"Charge!\" at rank 10 opens a 10.0 s episode (retail: field3 10 -> 10.0, n=27)")
    check(not any(e["skill"] == CRIPPLED_ID for e in state["effects"].on_agent(PLAYER)),
          "and the Crippled episode is GONE -- 'Allies in earshot lose the Crippled condition'")
    check(ops[:2] == [authsrv.GAME_SMSG_EFFECT_APPLY, authsrv.GAME_SMSG_EFFECT_REMOVE]
          and sent[-1][0] == authsrv.GAME_SMSG_AGENT_UPDATE_SPEED_BASE
          and abs(sent[-1][1][1] - 383.04) < 1e-6,
          "the cure batch: [0x0042 364, 0x0044 crippled, 0x00F1, ..., 0x0027 383.04] -- "
          "retail's order, one speed word", f"ops={[hex(o) for o in ops]}")
    # The 34% cap is on the SUM, and a single source may exceed it.
    state = fresh_state()
    open_ep(state, RUSH, rank=12, duration=18.0)
    open_ep(state, WINDBORNE, rank=15, duration=13.0)
    check(abs(authsrv.move_speed_factor(state, PLAYER) - 1.34) < 1e-9,
          "Rush 25 + Windborne 33 = 58, capped at 34")
    # A body gets its own word, fed to its own client-side model.
    state = fresh_state()
    state["agents"][10] = {"name": "hatcher", "pos": (300.0, 0.0), "plane": 0,
                           "max_health": 100.0, "health": 100.0}
    sent, send = collector()
    authsrv.apply_condition(send, state, 10, CRIPPLED_ID, 15.0, 0, 0, by_skill=323)
    check(any(op == authsrv.GAME_SMSG_AGENT_UPDATE_SPEED_BASE and v == [10, 144.0]
              for op, v, _l in sent),
          "a crippled body is declared at 144.0 (retail: 27 such words, 281 of 473 "
          "speed words target non-player agents)", f"sent={sent}")
    check(abs(authsrv.npc_declared_speed(state, 10) - 144.0) < 1e-9
          and abs(authsrv.npc_declared_speed(state, 11) - 288.0) < 1e-9,
          "the chase reads the body's declared speed; an undeclared body walks at 288")
    # The revert arm declares nothing on any path.
    authsrv.MOVE_SPEED_EFFECTS = False
    state = fresh_state()
    sent, send = collector()
    authsrv.apply_condition(send, state, PLAYER, CRIPPLED_ID, 13.0, 13, 0, by_skill=392)
    check(not any(op == authsrv.GAME_SMSG_AGENT_UPDATE_SPEED_BASE for op, _v, _l in sent),
          "--no-move-speed-effects: the condition opens, the status word goes, no 0x0027")
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
    # DAMAGE-INT (2026-09-14): the wire and the books carry WHOLE points,
    # truncated -- retail's 2 x 1.75 = 3.5 arrived as 3 on the WARRIOR-PRE
    # tape -- so x1.45 on a 10 is 14, not 14.5.
    check(abs((100.0 - state["player_health"]) - math.floor(FRENZY_MULT * base)) < 1e-9,
          f"under Frenzy the same swing takes exactly x{FRENZY_MULT} "
          f"(Strength {STR}, the 38888 row), truncated to whole points "
          f"({math.floor(FRENZY_MULT * base)} off a {base:.0f})",
          f"drop={100.0 - state['player_health']}")

    # ZEROWORD (2026-09-14): a swing that lands for NOTHING still sends its
    # damage word, as -0.0 -- ten such words on retail's wire (F46.7). A base
    # of 0.5 truncates to 0 (DAMAGE-INT) and the pool does not move.
    saved_hit = authsrv.ENEMY_HIT_FRACTION
    authsrv.ENEMY_HIT_FRACTION = 0.005
    try:
        sent, send = collector()
        state = fresh_state()
        authsrv.land_swing(send, state, 10, enemy, 0)
    finally:
        authsrv.ENEMY_HIT_FRACTION = saved_hit
    graze = [v for op, v, _l in sent
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
             and v[0] == agents.PROP_DAMAGE]
    check(graze == [[agents.PROP_DAMAGE, PLAYER, 10, 0x80000000]]
          and state["player_health"] == 100.0,
          "a swing that truncates to nothing still sends [16, player, foe, -0.0] "
          "(0x80000000) and takes nothing off the pool -- retail's ten -0.0 words",
          f"damage words {graze}, health {state['player_health']}")

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
    # CONVWORD (2026-09-14, F46.8): the converted swing gets its damage word
    # too, AFTER the heal -- one rule (a landed hit always gets its word).
    # Shipped by analogy as -0.0; OBSERVED 2026-09-16 (RUN-SKILLS-RB,
    # 20260916T213125, skills FINDINGS 48): retail's word for a FULLY converted
    # hit is +0.0 (0x00000000), 7 of 7, the remainder -(hit - cap), 3 of 3,
    # and the heal precedes the damage 10 of 10. The graze keeps its -0.0.
    floats = [(v[0], v[3]) for op, v, _l in sent
              if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
    check(floats and [f for f in floats if f[0] == agents.PROP_DAMAGE] == [(agents.PROP_DAMAGE, 0x00000000)]
          and [f[0] for f in floats].index(agents.GV_HEALTH_GAIN)
          < [f[0] for f in floats].index(agents.PROP_DAMAGE),
          "a fully converted swing sends ONE damage word, +0.0 (0x00000000), "
          "after the heal word -- retail's 7 of 7 under Reversal of Fortune "
          "(RUN-SKILLS-RB), a different word from the graze's -0.0",
          f"floats={[(p, hex(x)) for p, x in floats]}")
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
                                  "skill_ready": [],
                                  "allegiance": agents.ALLEGIANCE_HOSTILE}
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
check(status_msgs == [[PLAYER, effects.STATUS_DEAD | effects.STATUS_CONDITION
                       | effects.CONDITION_STATUS_BITS[DEEP_WOUND]],
                      [PLAYER, agents.EFFECT_DEAD]],
      "TWO status messages in the death batch when a condition is up: the "
      "WHOLE word first (dead | condition | Deep Wound's bit), then 0x10 once "
      "the strips are out -- retail 5 of 5 with Blind up: 18, then 16 "
      "(MORALE-Q8, studies/morale 1.3); one message, 0x10, when nothing is up",
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
# PVPMAX (2026-09-14, F46.10): a BODY's Deep Wound batch is the status word
# alone -- retail declares another agent's moved maximum on the observer's
# next landed hit (4 of 4 edges on the PvP tape, the 42 between the gain and
# the damage word), and party hits carry none. This check used to pin the
# 42 inside the batch, which was the PLAYER's isle shape copied to a foe.
check(shape(sent)[:1] == [(OP_STATUS, (ENEMY, 0x22))]
      and not [1 for op, v, _l in sent if op == OP_INT and v[0] == agents.PROP_HEALTH_MAX]
      and state.get("effect_list_suppressed") == 1,
      "a foe's batch is the status word MINUS the 0x0042 (MANTID: retail sends a "
      "foe's effect list to nobody, 0 of 369) and MINUS the maximum, which "
      "rides the next hit (PVPMAX)", f"got {shape(sent)[:3]}")
check(agent["max_health"] == 80.0 and agent["health"] == 80.0,
      "agent book: 80 of 80")
_saved_swing = authsrv.PLAYER_SWING_DAMAGE
authsrv.PLAYER_SWING_DAMAGE = (5, 5)
try:
    agent.update({"last_hit": 0.0, "pos": (0.0, 0.0)})
    state["pos"] = (0.0, 0.0)
    sent, send = collector()
    authsrv.hit_enemy(send, state, ENEMY, 0)
    ops1 = [(op, tuple(v[:3])) for op, v, _l in sent
            if (op == OP_INT and v[0] == agents.PROP_HEALTH_MAX)
            or (op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
                and v[0] == agents.PROP_DAMAGE)]
    check(ops1[:1] == [(OP_INT, (agents.PROP_HEALTH_MAX, ENEMY, 80))]
          and len(ops1) == 2 and ops1[1][0] != OP_INT,
          "the player's next landed hit declares [42, foe, 80] BEFORE its damage "
          "word -- retail's tick order (close, gain, 42, word), 27 of 27",
          f"got {ops1}")
    agent["last_hit"] = 0.0
    sent, send = collector()
    authsrv.hit_enemy(send, state, ENEMY, 0)
    check(not [1 for op, v, _l in sent if op == OP_INT and v[0] == agents.PROP_HEALTH_MAX],
          "and the hit after that carries no 42 -- only the first, and the first "
          "after a move (13 of the observer's 90 hits on the tape)")
finally:
    authsrv.PLAYER_SWING_DAMAGE = _saved_swing
agent["health"] = -10.0
sent, send = collector()
authsrv.heal_agent(send, state, ENEMY, ENEMY, 5.0, 0)
check(agent["dead"] is True
      and [v for op, v, _l in sent if op == OP_STATUS]
      == [[ENEMY, agents.EFFECT_DEAD | 0x22], [ENEMY, agents.EFFECT_DEAD]],
      "a heal that does not clear zero kills the agent through kill_agent's "
      "measured template -- the WHOLE word first (0x32: dead | the Deep Wound's "
      "0x20 | the condition bit, retail's 0x833 at 631.935 / the player's 18), then the "
      "step-down to 0x10 once the strip took the condition (the D6 review's EV-2; "
      "until 2026-09-27 a body's kill word was the bare 16 with the strip ahead of it)")
check(authsrv.GAME_SMSG_AGENT_KILL_REWARD in [op for op, _v, _l in sent],
      "and a HOSTILE's heal-kill pays the kill reward: hurt_agent_row's rule, "
      "whose party arm (a hero's pays nobody) is test_agentlife's JARIN-S 5b",
      f"ops {[hex(op) for op, _v, _l in sent]}")
check(not state["deep_wound"].get(ENEMY) and agent["max_health"] == 100.0,
      "death stripped it and restored the agent's book")

print("== 16b. the 20 % is FLOORED, and Bleeding's rate re-divides by the new maximum ==")
# RANGERPRE-S1 (2026-09-29, studies/skills 41.7). OBSERVED, 20260929T150923
# :53756, agent 30, an NPC (n=1): three Bleeding pips over 64 ([44] = -6/64 at
# t=1113.4097); Deep Wound's edge at t=1116.0485 is [0x00F1 [30, 0x23],
# 0x00A2 [44, 30, f32(-6/52)]] with no 42 in the batch (PVPMAX); the
# observer's next landed hit at t=1117.3818 is [42, 30, 52] ahead of the
# 4-point word f32(-4/52). OBSERVED, 20260817T231139 :50513, agent 10, a
# PvP-arena OPPONENT (not an NPC): 483 -> 387 under Bleeding + Burning, the
# edge's [44] f32(-20/387) at t=460.161. round() sent 51 and 386.
RETAIL_44_64 = 3186380485      # f32(-6/52)
RETAIL_WORD_52 = 3181218265    # f32(-4/52)
RETAIL_44_483 = 3176377849     # f32(-20/387)
ROUND_44_64 = 3186684145       # f32(-6/51): what the retired round() sent
OP_FLOAT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT


def retired_round_reduction(maximum):
    """The pre-RANGERPRE-S1 rule, kept as the known-bad arm: round(), not floor."""
    return min(authsrv.DEEP_WOUND_CAP,
               int(round(float(maximum) * authsrv.DEEP_WOUND_FRACTION)))


def dw_edge(maximum, pre=(BLEEDING,)):
    """A hostile at `maximum` of `maximum` with the conditions in `pre` live (their
    batches sent to nobody), then Deep Wound from skill 384, retail's applier.
    Returns (state, the 482 episode, the 482 batch as [(opcode, values)])."""
    state = dw_state(enemy=True)
    state["agents"][ENEMY].update(max_health=float(maximum), health=float(maximum))
    _pre, noop = collector()
    for cond in pre:
        authsrv.apply_condition(noop, state, ENEMY, cond, 10.0, 12, 0, by_skill=382)
    sent, send = collector()
    ep = authsrv.apply_condition(send, state, ENEMY, DEEP_WOUND, 10.0, 12, 0,
                                 by_skill=384)
    return state, ep, [(op, v) for op, v, _l in sent]


state, ep64, batch = dw_edge(64)
agent = state["agents"][ENEMY]
check(batch == [(OP_STATUS, [ENEMY, 0x23]),
                (OP_FLOAT, [agents.GV_CHANGE_HEALTH_REGEN, ENEMY, RETAIL_44_64])]
      and agent["max_health"] == 52.0 and agent["health"] == 52.0,
      "64 bleeding: the edge is [0x00F1 0x23, 0x00A2 [44, foe, f32(-6/52)]] -- retail's "
      "dword bit-exact -- and the book reads 52 of 52 (round() sent -6/51 and booked 51)",
      f"got {batch} book {agent['health']}/{agent['max_health']}")
_saved_hit = (authsrv.PLAYER_SWING_DAMAGE, random.random)
try:
    authsrv.PLAYER_SWING_DAMAGE = (4, 4)
    random.random = lambda: 1.0            # no critical, no block: the roll alone
    agent.update({"last_hit": 0.0, "pos": (0.0, 0.0)})
    state["pos"] = (0.0, 0.0)
    sent, send = collector()
    authsrv.hit_enemy(send, state, ENEMY, 0)
    hit = [(op, v[:3] if op == OP_INT else [v[0], v[1], v[3]]) for op, v, _l in sent
           if (op == OP_INT and v[0] == agents.PROP_HEALTH_MAX)
           or (op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
               and v[0] == agents.PROP_DAMAGE)]
    check(hit == [(OP_INT, [agents.PROP_HEALTH_MAX, ENEMY, 52]),
                  (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
                   [agents.PROP_DAMAGE, ENEMY, RETAIL_WORD_52])],
          "the player's next landed hit declares [42, foe, 52] ahead of a 4-point word of "
          "f32(-4/52), retail's 3181218265 (round() declared 51 and sent -4/51)",
          f"got {hit}")
finally:
    authsrv.PLAYER_SWING_DAMAGE, random.random = _saved_hit
state, _ep, batch = dw_edge(483, pre=(BLEEDING, 480))
check([v for op, v in batch if op == OP_FLOAT]
      == [[agents.GV_CHANGE_HEALTH_REGEN, ENEMY, RETAIL_44_483]]
      and state["agents"][ENEMY]["max_health"] == 387.0,
      "483 under Bleeding + Burning (10 pips): the edge's [44] is f32(-20/387), retail's "
      "PvP-arena opponent bit-exact, and the book reads 387 (round(): 386)",
      f"got {batch} max {state['agents'][ENEMY]['max_health']}")
_saved_red = authsrv.deep_wound_reduction
try:
    authsrv.deep_wound_reduction = retired_round_reduction
    state, _ep, batch = dw_edge(64)
    check([v[2] for op, v in batch if op == OP_FLOAT] == [ROUND_44_64] != [RETAIL_44_64]
          and state["agents"][ENEMY]["max_health"] == 51.0,
          "KNOWN-BAD ARM, the retired round(): the same edge sends -6/51 and books 51 -- "
          "the dword this section pins is the rounding's, not the fixture's",
          f"got {batch}")
finally:
    authsrv.deep_wound_reduction = _saved_red
_saved_dw = authsrv.DEEP_WOUND
try:
    authsrv.DEEP_WOUND = False
    state, _ep, batch = dw_edge(64)
    check(batch == [(OP_STATUS, [ENEMY, 0x23])],
          "KNOWN-BAD ARM, --no-deep-wound: the word alone and NO [44] -- the rate goes out "
          "again only because the maximum moved (the denominator's falsifier)",
          f"got {batch}")
finally:
    authsrv.DEEP_WOUND = _saved_dw
state, ep64, _batch = dw_edge(64)
ep64["expires_at"] = 0.0
sent, send = collector()
authsrv.effect_tick(send, state, 0)
check([v for op, v, _l in sent if op == OP_FLOAT]
      == [[agents.GV_CHANGE_HEALTH_REGEN, ENEMY, authsrv._f32(-6.0 / 64.0)]]
      and state["agents"][ENEMY]["max_health"] == 64.0,
      "RECONSTRUCTION, the close: the 482 expires with Bleeding live and the [44] goes back "
      "to f32(-6/64) over the restored 64 (retail's close re-division is witnessed only on "
      "the player's natural regeneration)",
      f"got {[(hex(op), v) for op, v, _l in sent]}")

print("== 16c. a rate back at zero is +0.0 (0x00000000), never -0.0 ==")
# RANGERPRE-S3 (2026-09-29). OBSERVED, 20260929T150923 :53756 t=1137.703144,
# agent 27 (max 64), Bleeding's expiry: [0x009F [7, 27, 23], 0x00F1 [27, 0],
# 0x00A2 [44, 27, 0x00000000]]. Every zero prop-44 word on the live corpus is
# +0.0: 561 of 561 over 38 captures / 127 connections, none 0x80000000, the
# observer's own included ([44, 9, 0x00000000] at t=1112.830452). Ours packed
# -(0 x 2)/64 = -0.0. Only the float word and its place behind the 0x00F1 are
# pinned here; the [7] ahead of them is RANGERPRE-S13's, pinned in test_condwords.
RETAIL_ZERO_44 = 0x00000000


def bleed_close(target, maximum=64.0):
    """Bleeding opened on `target` (a foe at `maximum`, or the player), then
    expired through effect_tick. Returns the close as [(opcode, values)]."""
    state = dw_state(enemy=True)
    state["agents"][ENEMY].update(max_health=maximum, health=maximum)
    _pre, noop = collector()
    ep = authsrv.apply_condition(noop, state, target, BLEEDING, 5.0, 12, 0, by_skill=382)
    ep["expires_at"] = 0.0
    sent, send = collector()
    authsrv.effect_tick(send, state, 0)
    return [(op, v) for op, v, _l in sent]


close = bleed_close(ENEMY)
check([v for op, v in close if op == OP_FLOAT]
      == [[agents.GV_CHANGE_HEALTH_REGEN, ENEMY, RETAIL_ZERO_44]]
      and [op for op, v in close if op in (OP_STATUS, OP_FLOAT)] == [OP_STATUS, OP_FLOAT],
      "a foe's Bleeding expiry sends 0x00F1 [foe, 0] then 0x00A2 [44, foe, 0x00000000] -- "
      "retail's +0.0 bit-exact (t=1137.703144); the pre-S3 wire was 0x80000000",
      f"got {[(hex(op), v) for op, v in close]}")
close = bleed_close(PLAYER)
check([v for op, v in close if op == OP_FLOAT]
      == [[agents.GV_CHANGE_HEALTH_REGEN, PLAYER, RETAIL_ZERO_44]],
      "and the PLAYER's own Bleeding expiry: [44, me, 0x00000000] -- the same push_regen, "
      "retail's observer zeros are +0.0 too",
      f"got {[(hex(op), v) for op, v in close]}")
_saved_zero = authsrv.REGEN_ZERO_POSITIVE
try:
    authsrv.REGEN_ZERO_POSITIVE = False
    close = bleed_close(ENEMY)
    check([v for op, v in close if op == OP_FLOAT]
          == [[agents.GV_CHANGE_HEALTH_REGEN, ENEMY, 0x80000000]],
          "KNOWN-BAD ARM, --regen-zero-signed: the same expiry sends -0.0 (0x80000000), the "
          "pre-S3 wire -- the dword above is the flag's, not the fixture's",
          f"got {[(hex(op), v) for op, v in close]}")
finally:
    authsrv.REGEN_ZERO_POSITIVE = _saved_zero
import serverargs  # noqa: E402
_ap = serverargs.build_parser(
    doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
    HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
    GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
    VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
_src = open(authsrv.__file__, encoding="utf-8").read()
_main = _src.find("\ndef main():")
_flag = _src.find("    if a.regen_zero_signed:", _main)
_pr = _src.find("def push_regen(")
_rate = _src.find("    rate = -(pips * effects.PIP_HEALTH_PER_SECOND) / pool\n", _pr)
_guard = _src.find("    if REGEN_ZERO_POSITIVE and not pips:\n        rate = 0.0", _pr)
_seen = _src.find('    seen = state.setdefault("regen_rate", {})', _pr)
check(_ap.parse_args([]).regen_zero_signed is False
      and _ap.parse_args(["--regen-zero-signed"]).regen_zero_signed is True
      and 0 < _main < _flag
      and "REGEN_ZERO_POSITIVE = False" in _src[_flag:_flag + 120]
      and 0 < _pr < _rate < _guard < _seen,
      "the source: --regen-zero-signed parses (default off), main() flips "
      "REGEN_ZERO_POSITIVE = False under it, and push_regen's zero guard sits between the "
      "rate and the change test")

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
# RANGERPRE-S1 (2026-09-29, studies/skills 41.7): every check above sits on a
# multiple of 5, where round and floor agree, so none of them could see the
# rounding. These can.
check(authsrv.deep_wound_reduction(64) == 12,
      "64 -> 12: retail's NPC went 64 -> 52 (OBSERVED, 20260929T150923 :53756, agent 30, "
      "n=1); round() takes 13 and books 51", f"got {authsrv.deep_wound_reduction(64)}")
check(authsrv.deep_wound_reduction(483) == 96,
      "483 -> 96: retail's PvP-arena opponent went 483 -> 387 (OBSERVED, 20260817T231139 "
      ":50513, agent 10); round() takes 97 and books 386",
      f"got {authsrv.deep_wound_reduction(483)}")
_sweep_bad = [m for m in range(1, 2001)
              if not (authsrv.deep_wound_reduction(m) == min(100, m // 5)
                      == authsrv.deep_wound_reduction(float(m)))]
check(not _sweep_bad,
      "the sweep 1..2000: the reduction is min(100, m // 5) on every integer maximum, int or "
      "float -- round() misses at m=3, and floor(m * (1.0 - 0.8)) at m=5 (1.0 - 0.8 is "
      "0.19999999999999996)", f"first misses {_sweep_bad[:5]}")
import deepwoundjoin                                      # noqa: E402  (offline: arithmetic only)
_tool_bad = [m for m in range(1, 2001)
             if deepwoundjoin.predicted_max(m) != m - authsrv.deep_wound_reduction(m)]
check(not _tool_bad and deepwoundjoin.predicted_max(64) == 52
      and deepwoundjoin.predicted_max(483) == 387,
      "deepwoundjoin.predicted_max, the corpus reader's prediction, is the server's own "
      "number over the sweep: 64 -> 52 and 483 -> 387",
      f"first misses {_tool_bad[:5]} 64->{deepwoundjoin.predicted_max(64)} "
      f"483->{deepwoundjoin.predicted_max(483)}")

print("== 19. the corpus, with no free parameter (deepwoundjoin) ==")
try:
    import deepwoundjoin
    rows = deepwoundjoin.census()
    n, joined, exact, cj, ce, stray, orders = deepwoundjoin.score(rows)
    check(n >= 2, f"the live corpus holds Deep Wound applies (n={n})")
    # RE-SCOPED 2026-09-28 (CASTAI-Z1), not loosened. The Zaishen capture holds the
    # corpus's first Deep Wound RE-APPLIED while the first was live (the observer, :50061):
    # retail sent the second 0x0042 with no prop-42 and let the first run out on its own
    # clock, again with no prop-42. P1 / P3 as written stay exact on the captures they were
    # pinned on; the signature below says what EVERY apply and close does, stacked or not.
    _pin = "20260928T103123"
    n_p, joined_p, exact_p, cj_p, ce_p, _s, _o = deepwoundjoin.score(
        [r for r in rows if r["capture"] < _pin])
    check(joined_p == n_p and exact_p == n_p and n_p >= 2,
          "every 482 apply is joined to a same-batch prop-42 of exactly 0.8x (the captures "
          "at the pin)",
          f"n={n_p} joined={joined_p} exact={exact_p}")
    check(cj_p == ce_p and ce_p >= 2,
          "every close restores the previous maximum (the captures at the pin)",
          f"joined={cj_p} exact={ce_p}")
    _stack_bad, _stacked, _witness = [], [], []
    for r in rows:
        events = sorted([(a["t"], 0, "apply", a) for a in r["applies"]]
                        + [(c_["t"], 1, "close", c_) for c_ in r["closes"]],
                        key=lambda e: (e[0], e[1]))
        live_dw = {}                   # agent -> {buff: the chain's maximum before it}
        for t_, _k, kind, e in events:
            on = live_dw.setdefault(e["agent"], {})
            if kind == "apply":
                if on:                 # stacked: the maximum is already down
                    base, ok = next(iter(on.values())), e["wire"] is None
                    _stacked.append(e)
                else:
                    base = e["before"]
                    ok = e["wire"] is not None and e["wire"] == e["predicted"]
                on[e["buff"]] = base
            else:
                base = on.pop(e["buff"], None)
                if on:                 # another episode still holds the maximum down
                    ok = e["wire"] is None
                    _stacked.append(e)
                else:
                    ok = e["wire"] is not None and e["wire"] == base
            if r["capture"] == _pin:
                _witness.append((r["connection"].split("->")[0].rsplit(":", 1)[-1],
                                 round(t_, 3), kind, e["agent"], e["buff"], e["wire"]))
            if not ok:
                _stack_bad.append((r["capture"], round(t_, 3), kind, e["agent"], e["buff"],
                                   e["wire"], base))
    check(not _stack_bad and n >= 4 and len(_stacked) >= 2,
          f"SIGNATURE (whole corpus): an apply onto an agent with NO live Deep Wound is "
          f"joined to exactly 0.8x its maximum, and a close that leaves none live restores the "
          f"maximum from BEFORE the chain; an apply or close while ANOTHER stays live sends no "
          f"prop-42 ({n} applies, {len(_stacked)} stacked events)",
          f"{_stack_bad}")
    check(_witness == [("50061", 203.938, "apply", 7, 67, 384),
                       ("50061", 222.644, "apply", 7, 51, None),
                       ("50061", 223.923, "close", 7, 67, None),
                       ("50061", 225.284, "close", 7, 51, 480)],
          "NEW (OBSERVED, 20260928T103123): the observer's Deep Wound re-applied while live -- "
          "buff 67 (20 s) at 203.938 takes 480 to 384; skill 338's hit applies buff 51 (19 s) at "
          "222.644 with NO prop-42 and NO remove of 67; 67 runs out at 223.923 (its own 20 s) "
          "with no prop-42; 51's removal at 225.284, beside the observer's 277, restores 480. "
          "Our apply_condition REMOVES-then-APPLIES a longer re-application: escalated",
          f"{_witness}")
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
    # RUN-SKILLS-WKL (2026-09-17): Crippled landed while Blind was live, twice,
    # so the generic 0x02 was already set and 481 newly set 0x08 alone -- the
    # 482 and 484 lines' own shape. 0x0A stays REQUIRED as the positive control.
    check(newly(481) <= {0x0A, 0x08} and 0x0A in newly(481),
          "481 sets 0x08 (with 0x02 when no condition was live)",
          f"{ {hex(b) for b in newly(481)} }")
    # RUN-SKILLS-RB2 (2026-09-17): Poison landed while Weakness was live, so
    # the generic 0x02 was already set and 484 newly set 0x40 alone, twice --
    # the same shape the 482 line above has carried since it was written.
    check(newly(483) <= {0x42, 0x40} and newly(484) <= {0x42, 0x40}
          and 0x42 in newly(484) | newly(483),
          "483 and 484 set 0x40 (with 0x02 when no condition was live)",
          f"483 { {hex(b) for b in newly(483)} } 484 { {hex(b) for b in newly(484)} }")
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
def _heal_tokens():
    """Every property-55 word in the live corpus with the ALLEGIANCE relation of its two
    agents: 'self', 'same' or 'across' by the tokens their 0x0020 creates carry in field
    12 (castethogram's reading: 'play' / 'mons' / 'nonc' on PvE maps, 'att1' / 'att2' on
    an arena), 'unknown' when either create is not on the connection. A connection its
    capture's OWN manifest declares gapped is set aside by name (livewire.declared_gaps,
    the refusal in deepwoundjoin.sequence untouched); any other refusal raises."""
    import bufflog
    import deepwoundjoin
    import livewire
    import tape
    import vaultpath

    def fourcc(x):
        return struct.pack("<I", x & 0xFFFFFFFF)[::-1].decode("latin-1")

    codec = bufflog.Codec()
    live = vaultpath.require_dir("captures", "live", why="the heal tokens")
    out = {"rows": [], "set_aside": []}
    for stamp in sorted(os.listdir(live)):
        cap = os.path.join(live, stamp)
        if not os.path.isdir(cap):
            continue
        gaps = livewire.declared_gaps(cap)
        for ch in tape.channel_files(cap):
            if ch["connection"] in gaps:
                out["set_aside"].append((stamp, ch["connection"]))
                print(f"   set aside BY ITS MANIFEST: {stamp} {ch['connection']} "
                      f"{gaps[ch['connection']]}")
                continue
            tok = {}
            for _i, t, op, v in deepwoundjoin.sequence(cap, ch["connection"], codec):
                if op == 0x0020 and len(v) > 12:
                    tok[v[1]] = fourcc(v[12])
                elif op == healjoin.OP_FLOAT_TARGET and v[1] == healjoin.PROP_HEAL:
                    tgt, cause = v[2], v[3]
                    pair = (tok.get(tgt), tok.get(cause))
                    rel = ("self" if tgt == cause else "unknown" if None in pair
                           else "same" if pair[0] == pair[1] else "across")
                    out["rows"].append({"capture": stamp, "t": round(t, 3), "target": tgt,
                                        "cause": cause, "value": healjoin._f32(v[4]),
                                        "self": tgt == cause, "relation": rel,
                                        "tokens": tuple(sorted(p for p in pair if p))})
    check(out["set_aside"] == [("20260928T103123", "10.0.0.210:65009->98.95.137.136:80")],
          "the token pass sets aside exactly the connections their capture's manifest "
          "declares gapped (CASTAI-Z1's match 2), by name", f"{out['set_aside']}")
    return out


print("== 20. the heal batch on retail's wire, and the overheal (healjoin) ==")
try:
    import healjoin
    _hrows = healjoin.census()
    hs = healjoin.score(_hrows)
    check(hs["n"] >= 800, f"the live corpus holds property-55 gains (n={hs['n']})")
    # RUN-DAGGERS-1 RE-PIN (2026-09-17). The owner's dagger tape 20260917T160915
    # put 28 NEGATIVE 55s on the corpus in one afternoon -- Death Blossom's
    # damage to the two foes ADJACENT to its target, [55, neighbour, observer,
    # -40/480] on both strikes of all 7 landed duals (studies/daggers F12) --
    # and "97%+ positive" fell to 95.9% on confirming evidence, not on a
    # defect. So the claim is split rather than its floor lowered: P1 is
    # judged on every OTHER tape, where it still holds, and P1b says what this
    # tape's negatives ARE, exactly, so a stray one still reddens.
    _DB_TAPE = "20260917T160915"
    _h55 = [r for r in _hrows if r["prop"] == healjoin.PROP_HEAL]
    # RE-SCOPED 2026-09-28 (CASTAI-Z1), not lowered -- the dagger split's pattern again.
    # The Zaishen capture is four-against-four PvP-style combat: 54 of its 245 property-55
    # words are negative (armour-ignoring damage between the two arena teams, and the
    # Necromancer's sacrifices), and "97%+" fell to 93.5% on confirming evidence. P1's
    # 97% stays exact on the captures at the pin; P1 AS WRITTEN is recorded FAILED on the
    # corpus through the new capture; the claim is carried over the WHOLE corpus by the
    # allegiance-token signature below (a negative 55 never lands inside one team), and
    # the capture's own negatives are pinned exactly on it, as P1b pins the dagger tape's.
    _PIN = "20260928T103123"
    _rest = [r for r in _h55 if r["capture"] != _DB_TAPE and r["capture"] < _PIN]
    check(sum(1 for r in _rest if r["value"] > 0) >= 0.97 * len(_rest)
          and len(_rest) >= 800,
          "P1: 55 is the health-GAIN direction, positive in 97%+ (the "
          "negatives are armour-ignoring DAMAGE: Empathy's trigger on "
          "20260913T210901, MANTID) -- judged without the dagger tape, on the "
          "captures at the pin",
          f"{sum(1 for r in _rest if r['value'] > 0)} of {len(_rest)}")
    _thru = [r for r in _h55 if r["capture"] != _DB_TAPE and r["capture"] <= _PIN]
    check(sum(1 for r in _thru if r["value"] > 0) == 1219 and len(_thru) == 1304,
          "P1 AS WRITTEN is recorded FAILED on the corpus through 20260928T103123 "
          "without the dagger tape: 1219 of 1304 positive (93.5% < 97%) -- the verdict "
          "rests on the pin-scoped check above and the signature below",
          f"{sum(1 for r in _thru if r['value'] > 0)} of {len(_thru)}")
    _tok = _heal_tokens()
    check(len(_tok["rows"]) == len(_h55),
          "the token pass reads the same property-55 words healjoin.census() does -- one "
          "corpus, two readers", f"{len(_tok['rows'])} vs {len(_h55)}; set aside "
          f"{_tok['set_aside']}")
    _neg_other = [x for x in _tok["rows"] if x["value"] <= 0 and not x["self"]]
    _bad = [x for x in _neg_other if x["relation"] != "across"]
    check(not _bad and len(_neg_other) >= 57,
          f"SIGNATURE (whole corpus): a NEGATIVE 55 onto another agent always crosses "
          f"allegiance tokens (0x0020's field 12) -- damage between teams, never inside one: "
          f"{len(_neg_other)} of {len(_neg_other)} (floor 57, the captures at the pin); the "
          f"only other negatives are self-directed (a sacrifice)",
          f"{[(x['capture'], x['t'], x['target'], x['cause'], x['relation']) for x in _bad[:6]]}")
    _zn = [x for x in _tok["rows"] if x["capture"] == _PIN and x["value"] <= 0]
    check(len([x for x in _tok["rows"] if x["capture"] == _PIN]) == 245 and len(_zn) == 54
          and sorted({x["cause"] for x in _zn if x["self"]}) == [4]
          and sum(1 for x in _zn if x["self"]) == 7
          and sum(1 for x in _zn if x["relation"] == "across") == 47
          and {x["tokens"] for x in _zn if not x["self"]} == {("att1", "att2")},
          "P1c: the Zaishen capture's 54 negatives of 245 are TWO things -- 47 words "
          "across the two arena teams (att1 / att2) and 7 sacrifices, every one by agent 4 "
          "(the opponent that casts the Necromancer hex 135) -- OBSERVED",
          f"{len(_zn)} negative; self causes {sorted({x['cause'] for x in _zn if x['self']})}")
    _db = [r for r in _h55 if r["capture"] == _DB_TAPE and r["value"] <= 0]
    check(len(_db) == 28 and not any(r["self"] for r in _db)
          and {round(r["value"], 4) for r in _db} == {-0.0833}
          and len({r["target"] for r in _db}) == 2,
          "P1b: the dagger tape's negatives are ONE thing -- 28 words of "
          "-40/480 dealt by the observer onto two neighbours, never a self "
          "word: an attack skill's ADJACENT damage rides 55, armour-ignoring, "
          "where its target's rides 16/17",
          f"n={len(_db)}, values { {round(r['value'], 4) for r in _db} }, "
          f"targets { {r['target'] for r in _db} }")
    # RE-SCOPED 2026-09-28 (CASTAI-Z1), not lowered: a heal inside a four-against-four
    # fight shares its batch with the fight (the Zaishen capture: 163 of 245 within the
    # set), so the 85% stays exact on the captures at the pin, P2 AS WRITTEN is recorded
    # FAILED through the new capture, and what P2 was FOR -- healjoin's own sentence: a
    # sibling riding beside 55 "in most batches and never beside damage" would be the
    # annotation candidate -- is the whole-corpus signature.
    _known = ("9F:58", "9F:21", "A0:20", "9F:8", "9F:42", "A3:55")
    hs_pin = healjoin.score([r for r in _hrows if r["capture"] < _PIN])
    check(hs_pin["within_known"] >= 0.85 * hs_pin["n"],
          "P2: a heal's same-agent siblings are messages this server already "
          "sends (58, the 20/21 visuals, 8, 42, another 55) in 85%+ of batches "
          "(measured 90.0% on 800; the floor sits under it on purpose) -- the "
          "captures at the pin",
          f"{hs_pin['within_known']} of {hs_pin['n']} -- outside the set: "
          + ", ".join(f"{k} x{v}" for k, v in hs_pin["siblings"].items()
                      if k not in _known))
    hs_thru = healjoin.score([r for r in _hrows if r["capture"] <= _PIN])
    check(hs_thru["within_known"] == 1126 and hs_thru["n"] == 1332,
          "P2 AS WRITTEN is recorded FAILED on the corpus through 20260928T103123: "
          "1126 of 1332 (84.5% < 85%) -- the verdict rests on the pin-scoped check "
          "above and the signature below",
          f"{hs_thru['within_known']} of {hs_thru['n']} -- outside the set: "
          + ", ".join(f"{k} x{v}" for k, v in hs_thru["siblings"].items()
                      if k not in _known))
    _out = {k: v for k, v in hs["siblings"].items() if k not in _known}
    _never_dmg = {k: v for k, v in _out.items() if hs["damage_siblings"].get(k, 0) == 0}
    check(hs["n"] >= 1087 and _out and max(_out.values()) < 0.5 * hs["n"],
          f"SIGNATURE (whole corpus, healjoin P2's own test for an annotation property -- one "
          f"riding beside 55 'in most batches and never beside damage'): no sibling outside "
          f"the set rides beside a 55 in even half the heal batches (the most frequent: "
          f"{max(_out, key=_out.get)} in {max(_out.values())} of {hs['n']}; floor 1087, the "
          f"pin's)",
          f"outside the set {_out}; never beside damage {_never_dmg}")
    _zh = healjoin.score([r for r in _hrows if r["capture"] == _PIN])
    check(_zh["n"] == 245 and _zh["within_known"] == 163,
          "P2c: the Zaishen capture alone -- 163 of its 245 heal batches within the set "
          "(the fight rides beside the heals: 16, 60, 44, 57, 4, 10 on the same agent) -- "
          "OBSERVED",
          f"{_zh['within_known']} of {_zh['n']}")
    # healjoin P2's annotation test has TWO conjuncts -- "in most batches AND never
    # beside damage" -- and the signature above states only the first; `_never_dmg`
    # was computed and printed, never asserted (round-2 review note). Both, here: the
    # never-beside-damage set EXACT per tape (the pin's captures; the Zaishen capture
    # alone), and over the whole corpus no sibling meets both conjuncts.
    _nd_pin = {k: v for k, v in hs_pin["siblings"].items()
               if k not in _known and hs_pin["damage_siblings"].get(k, 0) == 0}
    _nd_z = {k: v for k, v in _zh["siblings"].items()
             if k not in _known and _zh["damage_siblings"].get(k, 0) == 0}
    _cand = sorted(k for k, v in _never_dmg.items() if v >= 0.5 * hs["n"])
    check(_nd_pin == {"A0:54": 3, "9F:32": 2}
          and _nd_z == {"A0:54": 2, "9F:32": 1, "A2:43": 1, "9F:41": 1}
          and not _cand,
          "and P2's annotation test, BOTH conjuncts: the siblings outside the set that "
          "never ride beside damage are exactly A0:54 x3 and 9F:32 x2 on the captures at "
          "the pin, and A0:54 x2, 9F:32 x1, A2:43 x1, 9F:41 x1 on the Zaishen capture alone "
          "(OBSERVED, per tape); over the whole corpus none of them rides beside a 55 in "
          "half the heal batches -- no annotation candidate",
          f"pin {_nd_pin}; Zaishen {_nd_z}; whole corpus {_never_dmg}; candidates {_cand}")
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
#        corpus read). The RATE was WIKI (GWW "Blind": 90%) until RUN-SKILLS-RB
#        (2026-09-16, 20260916T213125) measured 27 misses of 30 blinded closes
#        = 0.90 on retail; the SHAPE is the client's own attack-fail word read
#        out of its drain (agents.py), and that tape carries it 27 times.
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
      "the rate is 0.90 -- the wiki's, and OBSERVED on retail: 27 misses of "
      "30 blinded closes (RUN-SKILLS-RB, missjoin P2; band [0.735, 0.979])")

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

print("== 23. the corpus: retail's swings close WITH damage, a blinded swing "
      "misses nine in ten, and property 38 rides with no damage (missjoin) ==")
try:
    import missjoin
    ms = missjoin.score(missjoin.census())
    check(ms["closes"] >= 1000,
          "at least 1,000 retail swing closes framed (measured 1,042)",
          f"closes={ms['closes']}")
    check(ms["p1"] and ms["p1_rate"] < 0.02,
          "P1: an unblinded close carries its damage -- UNEXPLAINED no-damage "
          "closes under 2% (measured 7 of 1,042 = 0.67%, every one a dead or "
          "unreachable target; a close carrying the fail word is explained, "
          "and the Student of Blind's 26 self-blinded misses ride there since "
          "RUN-SKILLS-RB)",
          f"rate={ms['p1_rate']} worded={ms['plain_miss_worded']}")
    # RUN-SKILLS-RB (2026-09-16): the day came. 30 closes under a live 479 on
    # 20260916T213125, 27 of them no-damage closes with [38, target, player,
    # 3]; the rate is OBSERVED and the pin is a band, not a zero.
    check(ms["blind"] >= 30 and ms["p2"] is True
          and ms["p2_band"][0] > 0.5 and ms["p2_band"][1] >= 0.9,
          "P2 OBSERVED: >= 30 retail closes under a live 479, and the "
          "no-damage rate's band holds 0.90 and excludes 0.50 (27 of 30 on "
          "RUN-SKILLS-RB; the band is the tool's own)",
          f"blind closes={ms['blind']} rate={ms['p2_rate']} band={ms['p2_band']}")
    check(ms["fails"] >= 1 and ms["fail_reasons"].get(2, 0) >= 1,
          "property 38 is on retail's wire, reason 2 'fail' at least once "
          "(20260819T132414 [38, 217, 27, 2])", f"reasons={ms['fail_reasons']}")
    check(ms["p5"] is True,
          "P5: no property 38 shares its batch with damage from that attacker "
          "onto that target -- the word and the number are exclusive",
          f"with damage={ms['fail_with_damage']}")
    check(ms["fail_blind"] >= 27 and ms["fail_reasons"].get(3, 0) >= 27,
          "and the Blind miss IS on retail's wire: >= 27 property-38 words "
          "with reason 3 'miss' from a blinded attacker (RUN-SKILLS-RB) -- "
          "the batch shape [close, 38] this server sends is OBSERVED, not "
          "reconstructed",
          f"reasons={ms['fail_reasons']} blind={ms['fail_blind']}")
except Exception as exc:                                     # noqa: BLE001
    LEDGER.skip("section 23 (corpus)", f"{type(exc).__name__}: {exc}")

# ---------------------------------------------------------------------------
# 24-26: SKILLS-RC, Restore Condition (studies/skills/FINDINGS.md 45). The
#        "AI heals itself" item was a MECHANIC error: WIKI (GWW "Restore
#        Condition") removes all conditions from target OTHER ally and heals
#        per condition removed. No retail cast of 276 exists to copy.
print("== 24. SKILLS-RC: Restore Condition removes the recipient's conditions "
      "and heals ONCE PER CONDITION REMOVED -- nothing removed, nothing "
      "healed ==")
RC, BLEED, DW = 276, 478, 482
EFFECT_REMOVE = authsrv.GAME_SMSG_EFFECT_REMOVE
INT_NT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT


def two_hostiles(h11=60.0):
    state = fresh_state()
    for aid, hp in ((10, 100.0), (11, h11)):
        state["agents"][aid] = {
            "name": "t", "dead": False, "died_at": 0.0, "health": hp,
            "max_health": 100.0, "last_hit": 0.0, "armor_rating": 60,
            "pos": (0.0, 0.0), "allegiance": agents.ALLEGIANCE_HOSTILE,
            "attacks_back": True}
    return state


def heals(sent):
    return [v for op, v, _l in sent if op == FLOAT_T
            and v[0] == agents.GV_HEALTH_GAIN]


def removes(sent):
    return [v for op, v, _l in sent if op == EFFECT_REMOVE]


saved = (authsrv.CONDITION_HEAL_RULE, authsrv.ENERGY, authsrv.STATUS_WORD)
try:
    authsrv.CONDITION_HEAL_RULE = True
    authsrv.ENERGY = False
    check(authsrv.skill_heal(RC, 12) == 58,
          "the client's own scale at rank 12: 10 + 60 x 12/15 = 58 (GWW's "
          "10...58...70)", f"{authsrv.skill_heal(RC, 12)}")

    sent, send = collector()
    state = two_hostiles()
    out = authsrv.resolve_heal(send, state, RC, 12, 10, 11, 0)
    check(out is not None and out["removed"] == 0 and out["healed"] == 0.0
          and not heals(sent) and not removes(sent)
          and state["agents"][11]["health"] == 60.0,
          "no condition on the ally: nothing removed, NOTHING healed, nothing "
          "on the wire -- the old flat 58 is gone", f"out={out} sent={sent}")

    sent, send = collector()
    state = two_hostiles()
    authsrv.apply_condition(send, state, 11, BLEED, 9.0, 12, 0, 382)
    check(len(state["effects"].on_agent(11)) == 1, "setup: Bleeding on 11")
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, RC, 12, 10, 11, 0)
    ops = [op for op, _v, _l in sent]
    check(out["removed"] == 1 and out["healed"] == 40.0
          and state["agents"][11]["health"] == 100.0
          and not state["effects"].on_agent(11),
          "ONE condition: it is removed and the ally is healed 58 (40 lands "
          "on a 60/100 pool)", f"out={out} health={state['agents'][11]['health']}")
    check(not removes(sent) and len(heals(sent)) == 1
          and ops.index(OP_STATUS) < ops.index(FLOAT_T),
          "the wire: NO 0x0044 for a body (MANTID) -- its status word clears "
          "BEFORE the 55 heal (the sentence's own order -- RECONSTRUCTION, "
          "no retail 276 cast exists)",
          f"ops={[hex(o) for o in ops]}")
    check(heals(sent)[0][1] == 11 and heals(sent)[0][2] == 10,
          "the heal names the ally as taker and the caster as cause")

    sent, send = collector()
    state = two_hostiles(h11=30.0)
    authsrv.apply_condition(send, state, 11, BLEED, 9.0, 12, 0, 382)
    authsrv.apply_condition(send, state, 11, DW, 9.0, 12, 0, 382)
    check(state["agents"][11]["max_health"] == 80.0
          and state["agents"][11]["health"] == 10.0,
          "setup: Bleeding + Deep Wound (maximum 80, the 20 taken off the "
          "pool, 30 -> 10)", f"{state['agents'][11]}")
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, RC, 12, 10, 11, 0)
    check(out["removed"] == 2 and abs(out["healed"] - 70.0) < 1e-9
          and state["agents"][11]["max_health"] == 100.0
          and state["agents"][11]["health"] == 100.0,
          "TWO conditions: both removed, the Deep Wound's close gives the 20 "
          "back to the pool FIRST (10 -> 30, SKILLS-DW's signed delta), then "
          "116 is healed (2 x 58) and 70 lands on the 30/100 pool",
          f"out={out} agent={state['agents'][11]}")
    maxes = [v for op, v, _l in sent if op == INT_NT
             and v[0] == agents.PROP_HEALTH_MAX]
    ops = [op for op, _v, _l in sent]
    # PVPMAX (2026-09-14, F46.10): a BODY's restored maximum is not in this
    # batch any more -- retail declares another agent's moved maximum on the
    # observer's next landed hit (hit_enemy), 4 of 4 edges on the PvP tape.
    check(not removes(sent) and not maxes and FLOAT_T in ops
          and state["agents"][11].get("max_declared_on_hit", 0) is None,
          "the wire: no 0x0044 for a body (MANTID); NO 0x009F 42 either -- the "
          "restored maximum rides the player's next hit (PVPMAX) -- then the heal",
          f"sent={sent}")

    authsrv.CONDITION_HEAL_RULE = False
    sent, send = collector()
    state = two_hostiles()
    authsrv.apply_condition(send, state, 11, BLEED, 9.0, 12, 0, 382)
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, RC, 12, 10, 10, 0)
    check(out["healed"] == 0.0 and not removes(sent) and len(heals(sent)) == 1
          and heals(sent)[0][1] == 10
          and len(state["effects"].on_agent(11)) == 1,
          "--no-condition-heal-rule (the known-bad arm): the caster heals "
          "ITSELF the flat 58 on a full pool, and the ally keeps its Bleeding",
          f"out={out} sent={sent}")
    authsrv.CONDITION_HEAL_RULE = True
finally:
    authsrv.CONDITION_HEAL_RULE, authsrv.ENERGY, authsrv.STATUS_WORD = saved

print("== 25. SKILLS-RC: the recipient is the client's target byte's verdict -- "
      "4 = other ally never the caster, 3 = ally else the caster ==")
try:
    HEAL_OTHER, INFUSE, KISS, DRAW, CONVERT = 286, 292, 283, 311, 303
    MEND_AIL, PURGE, WOH, REMOVE_HEX = 277, 278, 282, 301
    bytes4 = {s: int(agents.WORLD.get("skills", str(s))["target"])
              for s in (RC, HEAL_OTHER, INFUSE, KISS, DRAW, CONVERT)}
    bytes3 = {s: int(agents.WORLD.get("skills", str(s))["target"])
              for s in (MEND_AIL, PURGE, WOH, REMOVE_HEX, ROF)}
    check(all(v == effects.OTHER_ALLY_TARGET for v in bytes4.values()),
          "six 'target other ally' skills on GWW (Heal Other, Infuse Health, "
          "Restore Condition, Dwayna's Kiss, Draw Conditions, Convert Hexes) "
          "ALL carry byte 4 in the client's table", f"{bytes4}")
    check(all(v == effects.ALLY_TARGET for v in bytes3.values()),
          "five 'target ally' skills on GWW (Mend Ailment, Purge Conditions, "
          "Word of Healing, Remove Hex, Reversal of Fortune) ALL carry byte 3",
          f"{bytes3}")
    check(int(agents.WORLD.get("skills", "1")["target"]) == effects.SELF_TARGET
          and int(agents.WORLD.get("skills", "253")["target"])
          == effects.FOE_TARGET,
          "controls: Healing Signet is 0 (self), Scourge Sacrifice 5 (foe)")
    allies = {11, 12}
    check(authsrv.cast_recipient(RC, 10, 11, allies) == 11
          and authsrv.cast_recipient(RC, 10, 10, allies) is None
          and authsrv.cast_recipient(RC, 10, PLAYER, allies) is None
          and authsrv.cast_recipient(RC, 10, None, allies) is None
          and authsrv.cast_recipient(RC, 10, 11, set()) is None,
          "other ally: the selected ally, NEVER the caster, never a foe, "
          "never nobody -- and no allies means no recipient at all")
    check(authsrv.cast_recipient(MEND_AIL, 10, 11, allies) == 11
          and authsrv.cast_recipient(MEND_AIL, 10, PLAYER, allies) == 10
          and authsrv.cast_recipient(MEND_AIL, 10, None, allies) == 10,
          "ally: the selected ally, else the caster (an ally spell aimed at a "
          "foe lands on yourself)")
    check(authsrv.cast_recipient(1, PLAYER, 10, set()) == PLAYER
          and authsrv.cast_recipient(253, 10, PLAYER, allies) == PLAYER,
          "self lands on the caster whatever is selected; a foe skill on the "
          "selected target")
    # SLICE-B7a re-aimed this lock. It read "the player has no allies today --
    # no heroes, no party" and pinned a HARDCODED empty set; the hero arm has
    # landed a body since, so the same call now answers from the world. The
    # empty-world case is kept as the first conjunct, because "no party members
    # means no allies" must still hold and is the half that could regress into
    # inventing one.
    check(authsrv.allies_of({"agents": {}}, PLAYER) == set(),
          "an empty world still gives the player no allies")
    _hero = {"name": "h", "dead": False, "died_at": 0.0, "health": 100.0,
             "max_health": 100.0, "last_hit": 0.0, "armor_rating": 60,
             "pos": (0.0, 0.0), "allegiance": agents.ALLEGIANCE_PLAYER,
             "attacks_back": False}
    _st = {"agents": {200: dict(_hero), 201: dict(_hero)}}
    check(authsrv.allies_of(_st, PLAYER) == {200, 201},
          "the player's allies are the party BODIES, which carry "
          "ALLEGIANCE_PLAYER -- this is what SLICE-B7a unblocked",
          f"{authsrv.allies_of(_st, PLAYER)}")
    check(authsrv.allies_of(_st, 200) == {201, PLAYER},
          "and a hero's allies are the rest of the party PLUS the player, who "
          "is not a row in `agents` at all -- the asymmetry is the finding",
          f"{authsrv.allies_of(_st, 200)}")
    _dead_hero = {"agents": {200: dict(_hero), 201: dict(_hero, dead=True)}}
    check(authsrv.allies_of(_dead_hero, PLAYER) == {200}
          and authsrv.allies_of(_dead_hero, 200) == {PLAYER},
          "a dead party member is not an ally, from either side")
    check(authsrv.allies_of(dict(_st, player_dead=True), 200) == {201},
          "and a DEAD PLAYER is not an ally either -- without this a hero "
          "heals a corpse and resolve_heal moves a number nobody can see",
          f"{authsrv.allies_of(dict(_st, player_dead=True), 200)}")
    st = two_hostiles()
    st["agents"][12] = dict(st["agents"][11], dead=True)
    st["agents"][13] = dict(st["agents"][11], allegiance=0)
    check(authsrv.allies_of(st, 10) == {11},
          "a hostile's allies are the OTHER LIVING hostiles: not itself, not "
          "a corpse, not a body of another allegiance",
          f"{authsrv.allies_of(st, 10)}")
    sent, send = collector()
    st = two_hostiles()
    out = authsrv.resolve_heal(send, st, RC, 12, PLAYER, 10, 0)
    check(out is None and not sent and st["agents"][10]["health"] == 100.0,
          "the PLAYER casting Restore Condition at a foe resolves NOTHING -- "
          "no heal on the enemy (the old fall-through would have healed it)")
except agents.content.ContentError as exc:
    LEDGER.skip("section 25 (needs the vault's skill rows)", str(exc))

print("== 26. SKILLS-RC: the cast site -- a LONE hostile cannot cast Restore "
      "Condition and swings instead; with an ally it casts AT the ally, and "
      "the landing heals only what it cured ==")


def world(n_hostiles, bar=((RC, 0.75, 2.0),)):
    state = {"agents": {}, "pos": (0.0, 0.0), "player_health": 100.0,
             "player_dead": False}
    authsrv.effect_table(state)
    for k in range(n_hostiles):
        # SLICE-B3: every hostile HURT (50/100), because a hostile's heal now
        # aims at whoever is under HERO_HEAL_AT and a full-health squad draws
        # no cast at all. What these sections measure -- the targeted form,
        # the removal, the per-condition heal -- is unchanged by it.
        state["agents"][10 + k] = {
            "name": "hatcher", "dead": False, "died_at": 0.0,
            "health": 50.0, "max_health": 100.0, "last_hit": 0.0,
            "pos": (85.0, 10.0 * k), "plane": 0,
            "allegiance": agents.ALLEGIANCE_HOSTILE,
            "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
            "effects": 0, "attacks_back": True,
            "skills": bar, "skill_ready": [0.0] * len(bar),
            "last_swing": time.time() - 100.0}
    return state


def tick(state, n=1):
    sent = []
    for _ in range(n):
        authsrv.enemy_attack_tick(
            lambda op, vals, label="", quiet=False: sent.append(
                (op, list(vals), label)), state, 0)
    return sent


def casts(sent):
    return [v for op, v, _l in sent
            if (op == INT_T and v[0] == agents.GV_SKILL_ACTIVATED)
            or (op == INT and v[0] == agents.GV_SKILL_ACTIVATED)]


saved = (authsrv.ENERGY, authsrv.NPC_FOLLOW, authsrv.CONDITION_HEAL_RULE)
try:
    authsrv.ENERGY = False
    authsrv.NPC_FOLLOW = False
    authsrv.CONDITION_HEAL_RULE = True
    st = world(1)
    sent = tick(st)
    started = [v for op, v, _l in sent if op == INT_T
               and v[0] == agents.GV_ATTACK_STARTED]
    check(not casts(sent) and len(started) == 1 and st["agents"][10].get(
              "skill_ready") == [0.0],
          "alone: no cast of 276 goes out, the slot STAYS ready (not "
          "consumed), and the hostile swings instead",
          f"casts={casts(sent)} started={started} ready="
          f"{st['agents'][10]['skill_ready']}")

    st = world(2)
    sent = tick(st)
    c = [v for v in casts(sent) if v[1] == 10]
    check(len(c) == 1 and c[0] == [agents.GV_SKILL_ACTIVATED, 10, 11, RC]
          and st["agents"][10]["cast_target"] == 11,
          "with an ally: the cast goes out NAMING THE ALLY -- 0x00A0 [60, 10, "
          "11, 276] -- not the player (and the ally casts back at 10, the "
          "same rule from the other side)", f"casts={casts(sent)}")
    st["agents"][10]["cast_lands_at"] = time.time() - 1.0
    sent = tick(st)
    check([v for op, v, _l in sent if op == INT
           and v[0] == agents.GV_SKILL_FINISHED] == [[58, 10, 0]]
          and not heals(sent) and st["agents"][11]["health"] == 50.0,
          "the landing: property 58 closes the cast, and with no condition on "
          "the ally NOTHING is healed -- the ally stays at the 50/100 the "
          "fixture gave it", f"sent={sent}")

    st = world(2)
    st["agents"][11]["health"] = 50.0
    s0, send0 = collector()
    authsrv.apply_condition(send0, st, 11, BLEED, 9.0, 12, 0, 382)
    sent = tick(st)
    st["agents"][10]["cast_lands_at"] = time.time() - 1.0
    sent = tick(st)
    check(not removes(sent) and len(heals(sent)) == 1
          and heals(sent)[0][1] == 11 and st["agents"][11]["health"] == 100.0
          and not st["effects"].on_agent(11),
          "a bleeding ally: the cast lands as one 58 heal on the ALLY (50 -> "
          "100) with no 0x0044 (MANTID), and the ally is cured", f"sent={sent}")

    authsrv.CONDITION_HEAL_RULE = False
    st = world(1)
    sent = tick(st)
    c = casts(sent)
    check(len(c) == 1 and c[0][-1] == RC,
          "--no-condition-heal-rule: the lone hostile casts 276 again (the "
          "known-bad arm)", f"casts={c}")
finally:
    authsrv.ENERGY, authsrv.NPC_FOLLOW, authsrv.CONDITION_HEAL_RULE = saved

# ---------------------------------------------------------------------------
# 27: SKILLS-MA, Mend Ailment (studies/skills/FINDINGS.md 46): remove ONE
#     condition -- the most recently applied (GWW "Cover") -- and heal per
#     condition REMAINING. Target byte 3: an ally spell, the caster legal.
print("== 27. SKILLS-MA: Mend Ailment removes the NEWEST condition and heals "
      "once per condition that REMAINS -- one condition cured heals nothing ==")
MA, POISON = 277, 484
saved = (authsrv.CONDITION_HEAL_RULE, authsrv.ENERGY)
try:
    authsrv.CONDITION_HEAL_RULE = True
    authsrv.ENERGY = False
    check(authsrv.skill_heal(MA, 12) == 57,
          "the client's scale at rank 12: 5 + 65 x 12/15 = 57 (GWW's 5...57...70)",
          f"{authsrv.skill_heal(MA, 12)}")
    row = agents.WORLD.get("skill_effect", str(MA))
    check(row.get("removes_conditions") == 1
          and row.get("heal_per_condition_remaining") is True
          and not row.get("heal_per_condition_removed"),
          "the row: remove ONE, heal per REMAINING (and not per removed)")

    sent, send = collector()
    state = two_hostiles()
    out = authsrv.resolve_heal(send, state, MA, 12, 10, 11, 0)
    check(out["removed"] == 0 and out["remaining"] == 0
          and out["healed"] == 0.0 and not sent,
          "no condition: nothing removed, nothing healed, nothing sent")

    sent, send = collector()
    state = two_hostiles()
    authsrv.apply_condition(send, state, 11, BLEED, 9.0, 12, 0, 382)
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, MA, 12, 10, 11, 0)
    check(out["removed"] == 1 and out["remaining"] == 0
          and out["healed"] == 0.0 and not removes(sent)
          and not heals(sent) and not state["effects"].on_agent(11)
          and state["agents"][11]["health"] == 60.0,
          "ONE condition: it is removed and NOTHING is healed -- none remains "
          "(the difference from Restore Condition, which would heal 58 here)",
          f"out={out} sent={sent}")

    sent, send = collector()
    state = two_hostiles()
    authsrv.apply_condition(send, state, 11, BLEED, 9.0, 12, 0, 382)
    time.sleep(0.01)
    authsrv.apply_condition(send, state, 11, POISON, 9.0, 12, 0, 382)
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, MA, 12, 10, 11, 0)
    left = [ep["skill"] for ep in state["effects"].on_agent(11)]
    check(out["removed"] == 1 and out["remaining"] == 1
          and left == [BLEED] and out["healed"] == 40.0
          and state["agents"][11]["health"] == 100.0,
          "TWO conditions, Bleeding then Poison: the NEWEST (Poison) goes, the "
          "Bleeding stays, and the one remaining heals 57 (40 lands on 60/100)",
          f"out={out} left={left}")
    ops = [op for op, _v, _l in sent]
    check(not removes(sent) and len(heals(sent)) == 1,
          "the wire: no 0x0044 for a body (MANTID); the 55 heal alone",
          f"ops={[hex(o) for o in ops]}")

    sent, send = collector()
    state = two_hostiles(h11=10.0)
    for cond in (BLEED, POISON, DW):
        authsrv.apply_condition(send, state, 11, cond, 9.0, 12, 0, 382)
        time.sleep(0.01)
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, MA, 12, 10, 11, 0)
    left = sorted(ep["skill"] for ep in state["effects"].on_agent(11))
    check(out["removed"] == 1 and out["remaining"] == 2
          and left == [BLEED, POISON]
          and state["agents"][11]["max_health"] == 100.0
          and abs(out["healed"] - 90.0) < 1e-9,
          "THREE, Deep Wound newest: the Deep Wound goes (its open took the "
          "pool 10 -> -10 SIGNED, SKILLS-DW; its close gives the 20 back, -10 "
          "-> 10), two remain, 114 is healed and 90 lands on the 10/100 pool",
          f"out={out} left={left} agent={state['agents'][11]}")

    # The ally rule with a real ally spell: the PLAYER casts Mend Ailment
    # with a FOE selected -- it lands on the player (ALLY_TARGET: else the
    # caster), curing the player's newest condition.
    sent, send = collector()
    state = two_hostiles()
    state["player_health"] = 50.0
    authsrv.player_pools(state)
    authsrv.apply_condition(send, state, PLAYER, BLEED, 9.0, 12, 0, 382)
    time.sleep(0.01)
    authsrv.apply_condition(send, state, PLAYER, POISON, 9.0, 12, 0, 382)
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, MA, 12, PLAYER, 10, 0)
    left = [ep["skill"] for ep in state["effects"].on_agent(PLAYER)]
    check(out["recipient"] == PLAYER and left == [BLEED]
          and out["remaining"] == 1 and out["healed"] > 0
          and state["agents"][10]["health"] == 100.0,
          "the PLAYER casting Mend Ailment at a FOE: it lands on the player "
          "(target byte 3, the caster is the legal fall-back), cures the "
          "player's newest condition and heals per the one left; the foe is "
          "untouched", f"out={out} left={left}")

    authsrv.CONDITION_HEAL_RULE = False
    sent, send = collector()
    state = two_hostiles()
    authsrv.apply_condition(send, state, 11, BLEED, 9.0, 12, 0, 382)
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, MA, 12, 10, 11, 0)
    check(not removes(sent) and len(heals(sent)) == 1
          and len(state["effects"].on_agent(11)) == 1,
          "--no-condition-heal-rule: a flat 57 and no cure (the known-bad arm)")
    authsrv.CONDITION_HEAL_RULE = True
finally:
    authsrv.CONDITION_HEAL_RULE, authsrv.ENERGY = saved

print("== 28. SLICE-B7c: a PARTY body casts a heal at the player, and the two "
      "arms that say the cast is what did it ==")
_b7c = (authsrv.HERO_SKILLS, authsrv.HERO_HEAL_AT)
try:
    def _party_world(bar, player_health=40.0, **over):
        """One party body (agent 200) and a player at `player_health`.

        The body carries ALLEGIANCE_PLAYER and `attacks_back` False -- the two
        values BOTH creation sites actually set -- so this is the hero the
        run gets, not a hostile relabelled."""
        row = {"name": "Academy Monk", "dead": False, "died_at": 0.0,
               "health": 100.0, "max_health": 100.0, "last_hit": 0.0,
               "pos": (50.0, 0.0), "plane": 0,
               "allegiance": agents.ALLEGIANCE_PLAYER, "attack_speed": 1.0,
               "effects": 0, "attacks_back": False,
               "skills": bar, "skill_ready": [0.0] * len(bar)}
        row.update(over)
        st = fresh_state(health=player_health)
        st["player_dead"] = False
        st["agents"][200] = row
        return st

    # -- the policy, on its own. Three checks and one of them is the refusal.
    st = _party_world(())
    check(authsrv.ally_heal_target(st, 200) == PLAYER,
          "a party caster's heal target is the hurt PLAYER -- who is not a row "
          "in `agents`, which is the whole B7a asymmetry arriving here",
          f"{authsrv.ally_heal_target(st, 200)}")
    check(authsrv.ally_heal_target(_party_world((), player_health=100.0), 200)
          is None,
          "and at full health there is NO target, so a monk does not burn its "
          "pool topping up a party that needs nothing")
    st = _party_world(())
    st["agents"][201] = dict(st["agents"][200], health=10.0, skills=(),
                             skill_ready=[])
    check(authsrv.ally_heal_target(st, 200) == 201,
          "among several it takes the WORST by fraction, not the lowest id -- "
          "a 10/100 henchman outranks a 40/100 player",
          f"{authsrv.ally_heal_target(st, 200)}")

    RC = 276                      # Restore Condition, target OTHER ally
    bar = ((RC, 0.75, 2.0),)
    authsrv.HERO_SKILLS = bar

    sent, send = collector()
    st = _party_world(bar)
    authsrv.ally_cast_tick(send, st, 0)
    check(st["agents"][200].get("cast_lands_at") is not None
          and st["agents"][200].get("cast_target") == PLAYER and sent,
          "a party body with a bar and a hurt player CASTS: an activation goes "
          "out and the landing is armed at the player",
          f"sent={[hex(o) for o, _v, _l in sent]} "
          f"target={st['agents'][200].get('cast_target')}")

    # ARM 1: nobody hurt. Same bar, same body -- only the health differs.
    sent, send = collector()
    st = _party_world(bar, player_health=100.0)
    authsrv.ally_cast_tick(send, st, 0)
    check(not sent and st["agents"][200].get("cast_lands_at") is None,
          "ARM: a full-health party gets no cast at all, so the heal is driven "
          "by the health and not by the tick merely running",
          f"sent={[hex(o) for o, _v, _l in sent]}")

    # ARM 2: no bar. This is every hero run before 2026-09-12.
    sent, send = collector()
    st = _party_world(())
    authsrv.ally_cast_tick(send, st, 0)
    check(not sent and st["agents"][200].get("cast_lands_at") is None,
          "ARM: an EMPTY bar casts nothing -- the state every hero body was in "
          "before --hero-skills existed",
          f"sent={[hex(o) for o, _v, _l in sent]}")

    # ARM 3: a HOSTILE body is not swept by this tick, so the two paths cannot
    # be confused for one another.
    sent, send = collector()
    st = _party_world(bar)
    st["agents"][200]["allegiance"] = agents.ALLEGIANCE_HOSTILE
    authsrv.ally_cast_tick(send, st, 0)
    check(not sent,
          "ARM: the same body under ALLEGIANCE_HOSTILE is untouched here -- "
          "this tick owns the party and nothing else")

    # ARM 4, and it is a REGRESSION rather than a control: the two ticks in the
    # order the world tick runs them. `enemy_attack_tick` goes first and its
    # `not attacks_back` branch used to CLEAR `cast_lands_at` before the
    # allegiance gate -- and a party body has `attacks_back` False, so it landed
    # there every tick. The live result was 28 party casts on the wire and ZERO
    # landings. This check exists because the section above could not see it:
    # driving `ally_cast_tick` alone is exactly the offline agreement that
    # proves nothing.
    sent, send = collector()
    st = _party_world(bar)
    authsrv.ally_cast_tick(send, st, 0)
    _armed = st["agents"][200].get("cast_lands_at")
    authsrv.enemy_attack_tick(send, st, 0)
    check(_armed is not None
          and st["agents"][200].get("cast_lands_at") == _armed,
          "ARM: the hostile tick running first does NOT wipe a party body's "
          "armed cast -- the defect that made 28 casts land nothing",
          f"armed={_armed} after={st['agents'][200].get('cast_lands_at')}")

    # -- and the LANDING resolves a real heal on the player.
    #
    # THE PLAYER HAS TO BE CONDITIONED FIRST, and that is not a test fixture
    # detail -- it is the constraint studies/slice/PLAN.md registered as
    # SLICE-B3's trap before any of this was built. Restore Condition heals
    # PER CONDITION REMOVED (SKILLS-RC, 2026-09-10), so against a clean target
    # it cures nothing and therefore heals nothing. Written without the
    # condition this check failed, correctly, and the failure is the evidence
    # that the slice needs an UNCONDITIONAL heal wired before a monk hero looks
    # like a monk. Both heals that work today are condition-gated.
    sent, send = collector()
    st = _party_world(bar)
    authsrv.apply_condition(send, st, PLAYER, BLEED, 9.0, 12, 0, 382)
    sent, send = collector()
    authsrv.ally_cast_tick(send, st, 0)
    st["agents"][200]["cast_lands_at"] = 0.0        # due
    sent, send = collector()
    authsrv.ally_cast_tick(send, st, 0)
    check(heals(sent) and removes(sent)
          and st["agents"][200].get("cast_lands_at") is None,
          "and when the landing falls due the same tick resolves it into a "
          "real heal on the player -- a cure AND a heal, through `land_skill` "
          "and the shared `resolve_heal`",
          f"heals={heals(sent)} removes={removes(sent)}")
except agents.content.ContentError as exc:
    LEDGER.skip("section 28 (needs the vault's skill rows)", str(exc))
finally:
    authsrv.HERO_SKILLS, authsrv.HERO_HEAL_AT = _b7c


# -- 29. MANTID: what the Factions tutorial tape corrected (studies/slice F38).
print("== 29. MANTID: the effect list is the player's own; a hex's auras; a hex "
      "that punishes attacks; Ether Feast; a skill granted mid-map ==")
EMPATHY, ETHER_FEAST = 26, 40
_m29 = (authsrv.EFFECT_LIST_SELF_ONLY, authsrv.HEX_TRIGGERS, authsrv.ENERGY,
        authsrv.STATUS_WORD, authsrv.ARMOUR_TERM, list(authsrv.SKILLBAR))
try:
    authsrv.EFFECT_LIST_SELF_ONLY, authsrv.HEX_TRIGGERS = True, True
    authsrv.ENERGY, authsrv.STATUS_WORD, authsrv.ARMOUR_TERM = False, True, False
    agents.WORLD.get("skills", str(EMPATHY))            # needs the vault overlay
    # (a) Empathy on a FOE: no 0x0042, the status word, the two auras
    state = two_hostiles()
    authsrv.player_pools(state)
    sent, send = collector()
    ep = authsrv.apply_effect(send, state, PLAYER, EMPATHY, 0, 11, 0)
    ops = [op for op, _v, _l in sent]
    check(ep is not None and ep["caster"] == PLAYER and ep["agent"] == 11,
          "Empathy by the player on foe 11 opens an episode that REMEMBERS "
          "its caster", str(ep)[:120])
    check(OP_APPLY not in ops and state.get("effect_list_suppressed") == 1,
          "no 0x0042 goes to the foe (retail: 0 of 369 on anyone but the "
          "player)", f"ops={[hex(o) for o in ops]}")
    check([v for op, v, _l in sent if op == OP_STATUS] == [[11, 0x800]],
          "the foe's status word carries the hex bit 0x800 (12 sightings on "
          "others in the corpus)", f"{sent}")
    check([tuple(v) for op, v, _l in sent if op == INT_NT and v[0] == agents.PROP_AURA_ON]
          == [(6, 11, 1), (6, 11, 4)],
          "and the row's two auras go on: [6, foe, 1], [6, foe, 4] -- the "
          "tape's batch, 5 of 5", f"{sent}")
    sent, send = collector()
    authsrv.strip_effects(send, state, 11, 0, "the foe died")
    check([tuple(v) for op, v, _l in sent if op == INT_NT and v[0] == agents.PROP_AURA_OFF]
          == [(7, 11, 1), (7, 11, 4)]
          and OP_REMOVE not in [op for op, _v, _l in sent],
          "stripping the foe switches the auras OFF ([7, foe, 1], [7, foe, 4], "
          "the death batch) and sends no 0x0044", f"{sent}")
    # (a') the PLAYER's own list still goes out
    sent, send = collector()
    ep2 = authsrv.apply_effect(send, state, 10, EMPATHY, 0, PLAYER, 0)
    check(ep2 is not None and [op for op, _v, _l in sent][0] == OP_APPLY
          and sent[0][1][0] == PLAYER,
          "a hex on the PLAYER goes out as 0x0042 as before", f"{sent[:1]}")
    authsrv.strip_effects(send, state, PLAYER, 0, "clear")
    # (a'') the revert arm
    authsrv.EFFECT_LIST_SELF_ONLY = False
    state = two_hostiles()
    sent, send = collector()
    authsrv.apply_effect(send, state, PLAYER, EMPATHY, 0, 11, 0)
    check(OP_APPLY in [op for op, _v, _l in sent],
          "REVERT ARM (--effect-list-to-all): the foe gets the 0x0042 again")
    authsrv.EFFECT_LIST_SELF_ONLY = True
    # (b) the hexed foe swings: the trigger lands ahead of its hit
    state = two_hostiles()
    authsrv.player_pools(state)
    authsrv.apply_effect(send, state, PLAYER, EMPATHY, 0, 11, 0)
    sent, send = collector()
    res = authsrv.land_swing(send, state, 11, state["agents"][11], 0)
    dmg = [(op, v) for op, v, _l in sent if op == FLOAT_T]
    maxes = [v for op, v, _l in sent if op == INT_NT and v[0] == agents.PROP_HEALTH_MAX]
    check(res == "landed" and len(dmg) == 2
          and dmg[0][1] == [agents.GV_ARMOR_IGNORING, 11, PLAYER, authsrv._f32(-0.1)]
          and dmg[1][1][0] == agents.PROP_DAMAGE and dmg[1][1][1] == PLAYER,
          "the foe's swing: [55, foe, hexer, -0.10] (10 of its 100) BEFORE its "
          "own [16, player, foe, ...] -- the tape's order, 3 of 3",
          f"dmg={dmg} res={res}")
    i42 = [i for i, (op, v, _l) in enumerate(sent)
           if op == INT_NT and v[0] == agents.PROP_HEALTH_MAX]
    i55 = [i for i, (op, v, _l) in enumerate(sent) if op == FLOAT_T]
    check(i42 and i55 and i42[0] == i55[0] - 1
          and sent[i42[0]][1] == [agents.PROP_HEALTH_MAX, 11, 100],
          "and the foe's maximum is declared right before the fraction (3 of 3)",
          f"{sent[:4]}")
    check(state["agents"][11]["health"] == 50.0,
          "the foe's own book: 60 -> 50", f"{state['agents'][11]['health']}")
    # (b') the trigger can kill, and then the swing never lands
    state = two_hostiles(h11=5.0)
    authsrv.player_pools(state)
    authsrv.apply_effect(send, state, PLAYER, EMPATHY, 0, 11, 0)
    hp = state["player_health"]
    sent, send = collector()
    res = authsrv.land_swing(send, state, 11, state["agents"][11], 0)
    check(state["agents"][11]["dead"] and state["player_health"] == hp
          and not [1 for op, v, _l in sent if op == FLOAT_T and v[0] == agents.PROP_DAMAGE],
          "a foe at 5 dies to its own swing's punishment and its hit never lands",
          f"dead={state['agents'][11].get('dead')} hp={state['player_health']}")
    # (b'') the revert arm
    authsrv.HEX_TRIGGERS = False
    state = two_hostiles()
    authsrv.player_pools(state)
    authsrv.apply_effect(send, state, PLAYER, EMPATHY, 0, 11, 0)
    sent, send = collector()
    authsrv.land_swing(send, state, 11, state["agents"][11], 0)
    check(not [1 for op, v, _l in sent if op == FLOAT_T and v[0] == agents.GV_ARMOR_IGNORING]
          and state["agents"][11]["health"] == 60.0,
          "REVERT ARM (--no-hex-triggers): the hex is a bit and an icon, the "
          "swing costs the swinger nothing")
    authsrv.HEX_TRIGGERS = True
    # (c) Ether Feast: the foe loses 3, the caster is healed 3 x 20
    state = two_hostiles()
    authsrv.player_pools(state)
    state["player_health"] = 50.0
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, ETHER_FEAST, 0, PLAYER, 11, 0)
    check(out is not None and out["recipient"] == PLAYER
          and out["healed"] == 50.0 and state["player_health"] == 100.0
          and heals(sent) == [[agents.GV_HEALTH_GAIN, PLAYER, PLAYER, authsrv._f32(0.6)]],
          "Ether Feast at Inspiration 0: [55, me, me, 0.60] = 60 on a 100 pool "
          "(the tape's 0.68 x 88 = 60), 50 landing on 50/100",
          f"out={out} heals={heals(sent)}")
    # (d) a skill granted mid-map
    authsrv.SKILLBAR[:] = [1, 2, 0, 0, 0, 0, 0, 0]
    state = fresh_state()
    sent, send = collector()
    slot = authsrv.grant_skill(send, state, EMPATHY, 0)
    check(slot == 2 and authsrv.SKILLBAR[2] == EMPATHY
          and [(op, v) for op, v, _l in sent] == [
              (authsrv.GAME_SMSG_SKILL_SET_COPIES, [EMPATHY, 1]),
              (authsrv.GAME_SMSG_SKILLBAR_UPDATE_SKILL, [PLAYER, 2, EMPATHY, 0]),
              (authsrv.GAME_SMSG_SKILL_UNLOCKED, [EMPATHY, 0])],
          "a granted skill: 0x00DC [skill, 1], 0x00D9 [player, first empty "
          "slot, skill, 0], 0x001C [skill, 0] -- the tape's batch, 3 of 3",
          f"{sent}")
    sent, send = collector()
    authsrv.grant_skill(send, state, EMPATHY, 0)
    check(authsrv.GAME_SMSG_SKILL_UNLOCKED not in [op for op, _v, _l in sent],
          "granting a skill the account already knows sends no 0x001C (the "
          "Resurrection Signet at the reward)", f"{sent}")
    authsrv.SKILLBAR[:] = [1, 2, 3, 4, 5, 6, 7, 8]
    sent, send = collector()
    slot = authsrv.grant_skill(send, state, ETHER_FEAST, 0)
    check(slot is None
          and authsrv.GAME_SMSG_SKILLBAR_UPDATE_SKILL not in [op for op, _v, _l in sent]
          and authsrv.SKILLBAR == [1, 2, 3, 4, 5, 6, 7, 8],
          "a FULL bar learns the skill (0x00DC, 0x001C) and equips nothing "
          "(RECONSTRUCTION: the tape's bar always had room)", f"{sent}")
    authsrv.SKILLBAR[:] = [1, 2, 0, 0, 0, 0, 0, 0]
    state = fresh_state()
    authsrv.player_pools(state)
    sent, send = collector()
    authsrv.grant_quest_reward(send, state, "q", {"reward_experience": 100,
                                                  "reward_skills": [ETHER_FEAST]}, 0)
    ops = [op for op, _v, _l in sent]
    check(authsrv.GAME_SMSG_SKILLBAR_UPDATE_SKILL in ops
          and ops.index(authsrv.GAME_SMSG_SKILLBAR_UPDATE_SKILL)
          < ops.index(authsrv.GAME_SMSG_AGENT_KILL_REWARD)
          and authsrv.SKILLBAR[2] == ETHER_FEAST,
          "a quest row's reward_skills are granted in the reward frame, ahead "
          "of the experience", f"{[hex(o) for o in ops]}")
except agents.content.ContentError as exc:
    LEDGER.skip("section 29 (needs the vault's skill rows)", str(exc))
finally:
    (authsrv.EFFECT_LIST_SELF_ONLY, authsrv.HEX_TRIGGERS, authsrv.ENERGY,
     authsrv.STATUS_WORD, authsrv.ARMOUR_TERM) = _m29[:5]
    authsrv.SKILLBAR[:] = _m29[5]

print("\n== 30. SLICE-H14: Healing Signet costs its caster 40 armour WHILE it is "
      "used -- a hostile swing landing inside the activation deals exactly "
      "double, and nothing else does ==")
# WIKI ONLY (GWW "Healing Signet": "-40 armor while using this skill"; Notes:
# "results in double damage"; Anomaly: applied AFTER the armor cap). The live
# corpus holds no cast of skill 1 (0 of 19 prop-60 announces), so 2 ** (40/40)
# is the wiki's own arithmetic and not a measured ratio. The window is the
# pending cast's [begin_at, e5_at): begun and not completed.
_m30 = (authsrv.ARMOUR_TERM, authsrv.ENERGY, authsrv.BLIND,
        authsrv.CASTING_ARMOUR, authsrv.roll_hit_location)
try:
    authsrv.ARMOUR_TERM = True
    authsrv.ENERGY = False
    authsrv.BLIND = False
    authsrv.CASTING_ARMOUR = True
    # ONE hit location for every swing: the ratio below is exactly 2 only if
    # both swings strike the same rating, and roll_hit_location does not
    # read random.random (the first draft pinned that and still saw gloves,
    # body, boots and legs across six swings -- green only because the
    # default set wears 45 everywhere).
    _loc = authsrv.roll_hit_location()
    authsrv.roll_hit_location = lambda: _loc
    _ar = authsrv.player_armour_at(_loc, physical=True)
    if _ar is None:
        LEDGER.skip("section 30 (the default equipment gives no location rating)",
                    "player_armour_at returned None")
    else:
        _foe = {"name": "hatcher", "dead": False, "pos": (0.0, 0.0)}

        def _swing(pending=None):
            sent, send = collector()
            state = fresh_state()
            if pending is not None:
                state["pending_casts"] = pending
            authsrv.land_swing(send, state, ENEMY, _foe, 0)
            return 100.0 - state["player_health"]

        _quiet = _swing()
        _casting = _swing([{"skill_id": 1, "begin_at": 0.0, "e5_at": math.inf,
                            "e5_sent": False}])
        # DAMAGE-INT (2026-09-14): both numbers are truncated to whole points,
        # and floor(2q) is 2*floor(q) or 2*floor(q) + 1 for every q >= 0 -- no
        # free parameter, and a x2.0833 that is NOT a double (25 off a 12.5
        # base shown as 12) is exactly what the quiet 12 / casting 25 reads.
        check(_quiet > 0 and _casting in (2 * _quiet, 2 * _quiet + 1),
              "a swing landing while Healing Signet is being used deals EXACTLY "
              "double the quiet swing (2 ** (40 / 40)), to the whole point",
              f"quiet {_quiet:.4f}, casting {_casting:.4f}, ratio "
              f"{_casting / _quiet if _quiet else 'n/a'}")
        check(abs(_swing([{"skill_id": 1, "begin_at": 0.0, "e5_at": 1.0,
                           "e5_sent": True}]) - _quiet) < 1e-9,
              "a COMPLETED cast (E5 sent) costs nothing -- the window closes "
              "at completion")
        check(abs(_swing([{"skill_id": 1, "begin_at": math.inf,
                           "e5_at": math.inf, "e5_sent": False}]) - _quiet) < 1e-9,
              "a QUEUED cast that has not begun costs nothing -- the window "
              "opens at begin_at")
        check(abs(_swing([{"skill_id": 1, "begin_at": 0.0, "e5_at": math.inf,
                           "e5_sent": False, "cancelled": True}]) - _quiet) < 1e-9,
              "a CANCELLED cast costs nothing")
        check(abs(_swing([{"skill_id": 322, "begin_at": 0.0, "e5_at": math.inf,
                           "e5_sent": False}]) - _quiet) < 1e-9,
              "a skill whose row carries no armour_while_casting (Power Attack) "
              "costs nothing -- the term is content, not a signet rule")
        authsrv.CASTING_ARMOUR = False
        check(abs(_swing([{"skill_id": 1, "begin_at": 0.0, "e5_at": math.inf,
                           "e5_sent": False}]) - _quiet) < 1e-9,
              "--no-casting-armour reverts to the quiet swing (the known-bad arm)")
        authsrv.CASTING_ARMOUR = True
        check(authsrv.casting_armour_penalty(
                  {"pending_casts": [{"skill_id": 1, "begin_at": 0.0,
                                      "e5_at": math.inf, "e5_sent": False}]},
                  now=1.0) == -40.0,
              "and the penalty itself reads -40 off the content row, added to "
              "the CAPPED rating (the wiki's order), never folded into the "
              "bonus combatmath caps")
except agents.content.ContentError as exc:
    LEDGER.skip("section 30 (needs the skill_effect rows)", str(exc))
finally:
    (authsrv.ARMOUR_TERM, authsrv.ENERGY, authsrv.BLIND,
     authsrv.CASTING_ARMOUR, authsrv.roll_hit_location) = _m30

# ---------------------------------------------------------------------------
# 31: SKILLS-WK, Weakness's attribute penalty (studies/skills/FINDINGS.md 51).
print("== 31. SKILLS-WK: Weakness takes ONE off every attribute -- at every "
      "rank read, and on the wire as retail's 0x003B batch ==")
WEAK = effects.CONDITION_BY_NAME["Weakness"]
ATTR = authsrv.GAME_SMSG_AGENT_UPDATE_ATTRIBUTE
_m31 = authsrv.episodemods.WEAKNESS_ATTRIBUTES
try:
    state = fresh_state()
    check(authsrv.weakened_rank(state, PLAYER, 8) == 8,
          "no Weakness: a rank reads as it is")
    open_ep(state, WEAK, duration=20.0, type_code=8)
    check(authsrv.weakened_rank(state, PLAYER, 8) == 7
          and authsrv.weakened_rank(state, PLAYER, 1) == 0,
          "under Weakness a rank reads one lower (8 -> 7, 1 -> 0)",
          "WIKI (GWW 'Weakness'): all attributes reduced by 1; OBSERVED as "
          "the 35-point Mend Ailment at Protection Prayers 8 (RUN-SKILLS-RB2)")
    check(authsrv.weakened_rank(state, PLAYER, 0) == 0
          and authsrv.weakened_rank(state, PLAYER, None) is None,
          "a rank of 0 is untouched, and so is 'no rank' (WIKI: rank 0 is "
          "not affected)")
    check(authsrv.weakened_rank(state, 10, 8) == 8,
          "and it is the WEAKENED agent's ranks, not everyone's",
          "agent 10 carries no Weakness")
    # the number that opened this: 5..70 at rank 7, not 8
    lo, hi = 5.0, 70.0
    check(math.floor(lo + (hi - lo) * authsrv.weakened_rank(state, PLAYER, 8) / 15.0) == 35,
          "Mend Ailment's 5..70 at the weakened rank is retail's 35, where "
          "rank 8 gives the tooltip's 40",
          f"rank 7 -> {lo + (hi - lo) * 7 / 15.0:.2f}, rank 8 -> "
          f"{lo + (hi - lo) * 8 / 15.0:.2f}; the tape's word is 0.07292 x 480")

    # the wire: apply through the real path, then the expiry
    sent, send = collector()
    state = fresh_state()
    st = authsrv.attribute_state(state)
    live_attrs = sorted(a for a in st.ranks if st.rank_of(a) > 0)
    authsrv.apply_condition(send, state, PLAYER, WEAK, 20.0, 0, 0, by_skill=0)
    ops = [op for op, _v, _l in sent]
    rows = [v for op, v, _l in sent if op == ATTR]
    check(live_attrs and [r[1] for r in rows] == live_attrs
          and all(r[0] == PLAYER and r[2] == st.rank_of(r[1])
                  and r[3] == st.effective_of(r[1]) - 1 for r in rows),
          "the Weakness apply re-declares EVERY attribute with a base rank as "
          "[player, attr, base, effective - 1] -- the base is not moved",
          f"{rows} for attributes {live_attrs}")
    check(OP_STATUS in ops and ATTR in ops
          and ops.index(OP_STATUS) < ops.index(ATTR)
          and ops.index(OP_APPLY) < ops.index(OP_STATUS),
          "in retail's order: 0x0042, the status word, then the 0x003B rows",
          f"{[hex(o) for o in ops]}")
    sent, send = collector()
    authsrv.apply_condition(send, state, PLAYER, WEAK, 5.0, 0, 0, by_skill=0)
    check(not [v for op, v, _l in sent if op == ATTR],
          "a shorter re-application sends no second batch (one burst per "
          "CHANGE)")
    sent, send = collector()
    for ep in list(state["effects"].on_agent(PLAYER)):
        ep["expires_at"] = 0.0
    authsrv.effect_tick(send, state, 0)
    rows = [v for op, v, _l in sent if op == ATTR]
    check([r[1] for r in rows] == live_attrs
          and all(r[3] == st.effective_of(r[1]) for r in rows),
          "and its expiry restores them, one 0x003B per attribute at the full "
          "effective rank", f"{rows}")

    # the revert arm
    authsrv.episodemods.WEAKNESS_ATTRIBUTES = False
    sent, send = collector()
    state = fresh_state()
    authsrv.apply_condition(send, state, PLAYER, WEAK, 20.0, 0, 0, by_skill=0)
    check(not [v for op, v, _l in sent if op == ATTR]
          and authsrv.weakened_rank(state, PLAYER, 8) == 8,
          "--no-weakness-attributes: no rank moves and no 0x003B is sent "
          "(the pre-SKILLS-WK arm)")
finally:
    authsrv.episodemods.WEAKNESS_ATTRIBUTES = _m31

# 33 (unit half): RUN-SKILLS-WKL -- a cast that removes Weakness ITSELF heals
# at the WEAKENED rank, and the restores ride ahead of the heal word.
print("== 33. RUN-SKILLS-WKL: Mend Ailment lifting Weakness heals at the rank "
      "it was CAST at, the 0x003B restores ahead of the 55 word ==")
_s33 = (authsrv.CONDITION_HEAL_RULE, authsrv.ENERGY)
try:
    authsrv.CONDITION_HEAL_RULE = True
    authsrv.ENERGY = False
    sent, send = collector()
    state = fresh_state()
    authsrv.apply_condition(send, state, PLAYER, 484, 5.0, 0, 0, by_skill=0)
    time.sleep(0.01)
    authsrv.apply_condition(send, state, PLAYER, WEAK, 20.0, 0, 0, by_skill=0)
    rank = authsrv.weakened_rank(state, PLAYER, 8)      # read as the cast resolves
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, 277, rank, PLAYER, PLAYER, 0)
    left = [ep["skill"] for ep in state["effects"].on_agent(PLAYER)]
    pool = authsrv.player_max_health(state)
    words = heals(sent)
    _f32_33 = lambda b: struct.unpack("<f", struct.pack("<I", int(b) & 0xFFFFFFFF))[0]  # noqa: E731
    check(out["removed"] == 1 and left == [484] and len(words) == 1
          and abs(_f32_33(words[0][-1]) * pool - 35.0) < 0.01,
          "Poison then Weakness: WEAKNESS goes, Poison remains, and the one "
          "heal is 35 -- the rank-7 number, retail's 5 of 5 (RUN-SKILLS-WKL)",
          f"out={out} left={left} words={words} pool={pool}")
    ops = [op for op, _v, _l in sent]
    heal_at = next(k for k, (op, v, _l) in enumerate(sent)
                   if op == FLOAT_T and v[0] == agents.GV_HEALTH_GAIN)
    attr_at = [k for k, op in enumerate(ops) if op == ATTR]
    check(OP_REMOVE in ops and attr_at
          and ops.index(OP_REMOVE) < min(attr_at) and max(attr_at) < heal_at,
          "in retail's order: 0x0044, the 0x003B restores, THEN the 55 word "
          "-- the client already reads rank 8 when the rank-7 number lands",
          f"{[hex(o) for o in ops]}")
    check(authsrv.weakened_rank(state, PLAYER, 8) == 8,
          "and after the cast the rank reads 8 again")
finally:
    authsrv.CONDITION_HEAL_RULE, authsrv.ENERGY = _s33

print("== 32. the corpus: retail's Weakness batch (deepwoundjoin."
      "weakness_attributes) ==")
try:
    import deepwoundjoin
    wk = deepwoundjoin.score_weakness(deepwoundjoin.weakness_attributes())
    check(wk["applies_declared"] >= 2 and wk["closes_declared"] >= 2,
          "WK1 retail's Weakness apply AND removal carry 0x003B rows in their "
          "own batch (the player's, on the owner's Isle tape)",
          f"{wk} -- other agents' Weakness carries none, which is why these "
          f"are floors and not 'every apply'")
    check(wk["pairs"] >= 6 and wk["lifted_by_one"] == wk["pairs"]
          and wk["same_base"] == wk["pairs"] and wk["zero_base_rows"] == 0,
          "WK2 every attribute's effective at the removal is the apply's plus "
          "ONE, the base is the same at both, and no rank-0 attribute rides",
          f"{wk['lifted_by_one']} of {wk['pairs']} lifted by one, "
          f"{wk['same_base']} same base")
    lifts = [r for r in deepwoundjoin.weakness_lifts() if r["others"] >= 1]
    known = [r for r in lifts if r["points"] is not None]
    PROT = 15       # Protection Prayers, Mend Ailment's attribute

    def _at(r, lift):
        return r["others"] * authsrv.skill_heal(277, r["restored"][PROT] - lift)

    check(len(known) >= 4 and all(PROT in r["restored"] for r in known)
          and all(abs(r["points"] - _at(r, 1)) < 0.01 for r in known)
          and not any(abs(r["points"] - _at(r, 0)) < 0.01 for r in known),
          "WKL1 a cast that removes Weakness with other conditions remaining "
          "heals per remaining at the WEAKENED rank -- one under the rank its "
          "own batch restores -- and never at the restored one (RUN-SKILLS-"
          "WKL: 3 x 35 and 2 x 70 at Protection 8, where the controls heal 40)",
          f"{[(r['others'], r['restored'].get(PROT), r['points']) for r in known]}")
    check(lifts and all(r["attrs_before_heal"] for r in lifts),
          "WKL2 and every one carries its 0x003B restores AHEAD of the 55 word",
          f"{len(lifts)} lifts")
except (Exception, SystemExit) as exc:                           # noqa: BLE001
    LEDGER.skip("section 32 (corpus)", f"{type(exc).__name__}: {exc}")

# 34: SKILLS-MC, Mend Condition (275) -- DESKWORK-D5 3(d), studies/skills 58:
#     remove ONE condition (the newest) and heal the FLAT scale once, only if a
#     condition was actually removed. Target byte 4: other ally, the caster
#     NOT legal. The no-condition CONTROL is what separates this shape from
#     Mend Ailment's (277, heal per REMAINING) and Restore Condition's (276,
#     heal per REMOVED).
print("== 34. SKILLS-MC: Mend Condition removes the NEWEST condition and heals the "
      "flat scale once IF one was removed; nothing otherwise ==")
MC = 275
saved = (authsrv.CONDITION_HEAL_RULE, authsrv.ENERGY)
try:
    authsrv.CONDITION_HEAL_RULE = True
    authsrv.ENERGY = False
    check(authsrv.skill_heal(MC, 12) == 57,
          "the client's scale at rank 12: 5 + 65 x 12/15 = 57 (the same progression as 277)",
          f"{authsrv.skill_heal(MC, 12)}")
    row = agents.WORLD.get("skill_effect", str(MC))
    check(row.get("removes_conditions") == 1 and row.get("heal_if_removed") is True
          and not row.get("heal_per_condition_removed")
          and not row.get("heal_per_condition_remaining"),
          "the row: remove ONE, heal IF removed (and neither per-removed nor per-remaining)")
    check(int(agents.WORLD.get("skills", str(MC))["target"]) == effects.OTHER_ALLY_TARGET,
          "the client's target byte is 4 = other ally (the caster is not a legal recipient)")

    # THE CONTROL: no condition -> nothing removed, nothing healed, nothing sent.
    sent, send = collector()
    state = two_hostiles()
    out = authsrv.resolve_heal(send, state, MC, 12, 10, 11, 0)
    check(out["removed"] == 0 and out["remaining"] == 0
          and out["healed"] == 0.0 and not sent
          and state["agents"][11]["health"] == 60.0,
          "CONTROL, no condition: nothing removed, NOTHING healed, nothing sent -- the "
          "wounded ally stays at 60 (a flat heal here would be Mend Ailment's revert arm)",
          f"out={out} sent={sent}")

    # ONE condition: removed, and the flat 57 heals (40 lands on 60/100).
    sent, send = collector()
    state = two_hostiles()
    authsrv.apply_condition(send, state, 11, BLEED, 9.0, 12, 0, 382)
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, MC, 12, 10, 11, 0)
    check(out["removed"] == 1 and out["remaining"] == 0 and out["healed"] == 40.0
          and not state["effects"].on_agent(11)
          and state["agents"][11]["health"] == 100.0,
          "ONE condition: it is removed and the flat 57 heals once (40 landing on 60/100) "
          "-- the whole difference from Mend Ailment, which heals nothing here",
          f"out={out}")
    check(not removes(sent) and len(heals(sent)) == 1,
          "the wire: no 0x0044 for a body (MANTID); the one 55 heal word",
          f"ops={[hex(o) for o, _v, _l in sent]}")

    # TWO conditions: the NEWEST goes, the other stays, still ONE flat heal.
    sent, send = collector()
    state = two_hostiles(h11=10.0)
    authsrv.apply_condition(send, state, 11, BLEED, 9.0, 12, 0, 382)
    time.sleep(0.01)
    authsrv.apply_condition(send, state, 11, POISON, 9.0, 12, 0, 382)
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, MC, 12, 10, 11, 0)
    left = [ep["skill"] for ep in state["effects"].on_agent(11)]
    check(out["removed"] == 1 and out["remaining"] == 1 and left == [BLEED]
          and out["healed"] == 57.0 and state["agents"][11]["health"] == 67.0,
          "TWO conditions, Bleeding then Poison: the NEWEST (Poison) goes, the Bleeding "
          "stays, and the heal is the flat 57 ONCE -- not 57 per remaining (277) and not "
          "57 per removed (276)", f"out={out} left={left}")

    # THE RECIPIENT: byte 4 -- a hostile casting it at itself has no legal target.
    sent, send = collector()
    state = two_hostiles()
    authsrv.apply_condition(send, state, 10, BLEED, 9.0, 12, 0, 382)
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, MC, 12, 10, 10, 0)
    check(out is None and len(state["effects"].on_agent(10)) == 1 and not sent,
          "aimed at the CASTER: no legal recipient (other ally), nothing resolves, the "
          "caster keeps its Bleeding", f"out={out}")

    # THE REVERT: a flat 57 on the aimed target and no cure.
    authsrv.CONDITION_HEAL_RULE = False
    sent, send = collector()
    state = two_hostiles()
    authsrv.apply_condition(send, state, 11, BLEED, 9.0, 12, 0, 382)
    sent, send = collector()
    out = authsrv.resolve_heal(send, state, MC, 12, 10, 11, 0)
    check(not removes(sent) and len(heals(sent)) == 1
          and len(state["effects"].on_agent(11)) == 1 and out["healed"] == 40.0,
          "--no-condition-heal-rule: a flat 57 and no cure (the known-bad arm)")
    sent, send = collector()
    state = two_hostiles()
    out = authsrv.resolve_heal(send, state, MC, 12, 10, 11, 0)
    check(len(heals(sent)) == 1 and out["healed"] == 40.0,
          "  and under it the no-condition control DOES heal -- the two arms differ on "
          "exactly the gate this shape adds")
    authsrv.CONDITION_HEAL_RULE = True
finally:
    authsrv.CONDITION_HEAL_RULE, authsrv.ENERGY = saved


# ---------------------------------------------------------------------------
# 35-38: DESKWORK-D6 step 4, B2 (2026-09-27; studies/weapons/PLAN.md 43): the four
#        area hexes that need a mechanism of their own. NONE was cast on any live
#        tape (aotjoin P8), so every shape here is RECONSTRUCTION from the wiki's
#        sentence and the client's record, and every check names its known-bad
#        arm (the flag off) so the rule is shown load-bearing, not decorative.
SUFFER, SOOTHE, RUST, PANIC = 108, 56, 204, 52
HEAL_SIG, RES_SIG = 1, 2          # signets: type_code 7, OBSERVED 4 of 4
BURN = effects.CONDITION_BY_NAME["Burning"]
REGEN_FLOAT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT


def hex_on(state, sid, agent=PLAYER, rank=12, caster=None, seconds=8.0):
    return state["effects"].apply(agent, sid, rank, seconds, time.time(),
                                  type_code=4, caster=caster)


def hostile(state, aid, pos=(0.0, 0.0), **more):
    row = {"name": "t", "dead": False, "died_at": 0.0, "health": 100.0,
           "max_health": 100.0, "last_hit": 0.0, "armor_rating": 60, "pos": pos,
           "allegiance": agents.ALLEGIANCE_HOSTILE, "attacks_back": True}
    row.update(more)
    state["agents"][aid] = row
    return row



# The D6 review's M13: the source locks below used bare `src.index`, so ONE missing
# substring raised ValueError and skipped every later section. `_idx` / `_ridx` record
# a miss (and return -1, which a `<` comparison could pass), and `_lock` fails the check
# whenever one was recorded during its evaluation -- one miss, one red check, the rest runs.
_MISSING = []


def _idx(text, needle, start=0):
    try:
        return text.index(needle, start)
    except ValueError:
        _MISSING.append(needle[:70])
        return -1


def _ridx(text, needle):
    try:
        return text.rindex(needle)
    except ValueError:
        _MISSING.append(needle[:70])
        return -1


def _lock(value):
    missed, _MISSING[:] = list(_MISSING), []
    if missed:
        print(f"      source lock: MISSING substring(s) {missed}")
        return False
    return bool(value)




def press_e5(sid, target, hexid=None, cond=None):
    """The player's REAL press (handle_skill_press) with the costs and the weapon gate stubbed:
    the E5 clock it armed, in seconds. `hexid` / `cond` go on the player first."""
    _saved = (authsrv.skill_cost, authsrv.weapon_satisfies)
    authsrv.skill_cost = lambda sid: (0, 0)
    authsrv.weapon_satisfies = lambda sid: True
    try:
        st = fresh_state()
        hostile(st, 10, (50.0, 0.0))
        now = time.time()
        if hexid is not None:
            st["effects"].apply(PLAYER, hexid, 12, 30.0, now, type_code=4, caster=10)
        if cond is not None:
            st["effects"].apply(PLAYER, cond, 12, 30.0, now, type_code=8)
        sent, send = collector()
        authsrv.handle_skill_press([0, sid, 0, target], send, st, 0, authsrv.GAME_CMSG_USE_SKILL)
        c = (st.get("pending_casts") or [None])[0]
        return None if c is None else round(c["e5_at"] - c["begin_at"], 3)
    finally:
        authsrv.skill_cost, authsrv.weapon_satisfies = _saved


def e5_batch(sid, target, st, send):
    """Press `sid` at `target` on `st` and run the real cast_tick through its E5 (the
    clocks wound back 30 s); `send` collects the E5 batch alone."""
    _saved = (authsrv.skill_cost, authsrv.weapon_satisfies)
    authsrv.skill_cost = lambda sid: (0, 0)
    authsrv.weapon_satisfies = lambda sid: True
    try:
        sink, drop = collector()
        authsrv.handle_skill_press([0, sid, 0, target], drop, st, 0, authsrv.GAME_CMSG_USE_SKILL)
        for cast in st["pending_casts"]:
            for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                cast[k] -= 30.0
        authsrv.cast_tick(send, st, 0)
    finally:
        authsrv.skill_cost, authsrv.weapon_satisfies = _saved


def ally_cast(bar, hexid=None, cond=None, monk_health=100.0):
    """A party monk (200) with `bar` through the REAL ally_cast_tick, the player hurt (40/100):
    (its landing offset, its cast target, its recharge anchor offset)."""
    _saved = authsrv.HERO_SKILLS
    authsrv.HERO_SKILLS = bar
    try:
        st = fresh_state(health=40.0)
        st["player_dead"] = False
        row = {"name": "Academy Monk", "dead": False, "died_at": 0.0, "health": monk_health,
               "max_health": 100.0, "last_hit": 0.0, "pos": (50.0, 0.0), "plane": 0,
               "allegiance": agents.ALLEGIANCE_PLAYER, "attack_speed": 1.0, "effects": 0,
               "attacks_back": False, "skills": bar, "skill_ready": [0.0] * len(bar)}
        st["agents"][200] = row
        now = time.time()
        if hexid is not None:
            st["effects"].apply(200, hexid, 12, 30.0, now, type_code=4, caster=10)
        if cond is not None:
            st["effects"].apply(200, cond, 12, 30.0, now, type_code=8)
        sent, send = collector()
        authsrv.ally_cast_tick(send, st, 0)
        a = st["agents"][200]
        return (None if a.get("cast_lands_at") is None else round(a["cast_lands_at"] - now, 2),
                a.get("cast_target"), round(a["skill_ready"][0] - now, 2))
    finally:
        authsrv.HERO_SKILLS = _saved

print("== 35. Suffering (108): a `Health degeneration` HEX degenerates its wearer -- the "
      "explicit endpoints, one cap with the conditions, Faintheartedness lit up ==")
saved = (authsrv.HEX_DEGENERATION, authsrv.EFFECTS)
try:
    authsrv.HEX_DEGENERATION = True
    authsrv.EFFECTS = True
    row = agents.WORLD.get("skill_effect", str(SUFFER))
    rec = agents.WORLD.get("skills", str(SUFFER))
    check(row.get("scale_means") == "Health degeneration"
          and (row.get("health_degeneration0"), row.get("health_degeneration15")) == (0, 3)
          and (int(rec["scale0"]), int(rec["scale15"])) == (0, 3)
          and not int(rec["skill_arguments"]) & 2,
          "the row carries the client's own scale0/15 (0, 3) EXPLICITLY, because the slot's "
          "bit is clear with differing endpoints -- the shape both readers refuse")
    try:
        authsrv.skill_scale_value(SUFFER, 12)
        check(False, "skill_scale_value must refuse Suffering's scale slot")
    except ValueError:
        check(True, "and skill_scale_value DOES refuse it (a disabled set is not a progression) "
                    "-- the explicit field is the only way the number enters")
    st = fresh_state()
    check(authsrv.hex_pips(st, PLAYER) == 0.0 and authsrv.net_pips(st, PLAYER) == 0.0,
          "no episodes: no hex pips, no net pips")
    got = {}
    for r in (0, 5, 12, 15):
        st = fresh_state()
        hex_on(st, SUFFER, rank=r)
        got[r] = authsrv.hex_pips(st, PLAYER)
    check(got == {0: 0.0, 5: 1.0, 12: 2.0, 15: 3.0},
          "Suffering's pips by the client's formula on the explicit endpoints: 0 / 1 / 2 / 3 "
          "at rank 0 / 5 / 12 / 15 (2.4 rounds to 2, 1.0 exact)", f"{got}")
    sent, send = collector()
    st = fresh_state()
    hex_on(st, SUFFER, rank=15)
    rate = authsrv.push_regen(send, st, PLAYER, 0)
    check(abs(rate - (-0.06)) < 1e-9 and len(sent) == 1 and sent[0][0] == REGEN_FLOAT
          and sent[0][1][:2] == [agents.GV_CHANGE_HEALTH_REGEN, PLAYER],
          "push_regen sends prop 44 at -3 x 2 / 100 = -0.06/s for a rank-15 Suffering -- the "
          "same wire a three-pip Bleeding sends (test_effects 4e)", f"rate={rate} sent={sent}")
    st = fresh_state()
    hex_on(st, SUFFER, rank=15)
    st["effects"].apply(PLAYER, BURN, 3, 9.0, time.time(), type_code=8)
    check(authsrv.net_pips(st, PLAYER) == 10.0
          and effects.pips_from(st["effects"].on_agent(PLAYER)) == 7.0,
          "Burning (7) + Suffering (3) = 10, ONE cap shared with the conditions (RECONSTRUCTION: "
          "the wiki caps 'health degeneration' as a whole); pips_from alone still says 7")
    hex_on(st, FAINT, rank=15)
    check(authsrv.net_pips(st, PLAYER) == 10.0
          and authsrv.hex_pips(st, PLAYER) == 6.0
          and effects.pips_from(st["effects"].on_agent(PLAYER)) + authsrv.hex_pips(st, PLAYER) == 13.0,
          "and Burning (7) + Suffering (3) + Faintheartedness (3) = 13 reads 10 -- the cap BINDS "
          "(the review's M1: 7 + 3 was exactly 10, so the cap was never exercised)")
    # the review's HEX-2: the rate reaches the CLIENT -- a hostile's Suffering at the player
    # through the real land_skill sends 0x00A2 [44] at the apply and 0 at the close
    st = world(1, bar=((SUFFER, 1.0, 10.0),))
    a = st["agents"][10]
    a.update({"casting": 0, "cast_lands_at": time.time() - 0.01, "cast_target": PLAYER})
    sent, send = collector()
    authsrv.land_skill(send, st, 10, a, 0)
    regen = [v[1] for op, v, _l in sent if op == REGEN_FLOAT and v[0] == agents.GV_CHANGE_HEALTH_REGEN]
    rate_at_apply = st.get("regen_rate", {}).get(PLAYER)
    i_42 = next((i for i, (op, v, _l) in enumerate(sent) if op == authsrv.GAME_SMSG_EFFECT_APPLY), None)
    i_f1 = next((i for i, (op, v, _l) in enumerate(sent) if op == OP_STATUS and v[0] == PLAYER), None)
    i_44 = next((i for i, (op, v, _l) in enumerate(sent) if op == REGEN_FLOAT and v[1] == PLAYER), None)
    at_apply = list(sent)
    sent.clear()
    for e in st["effects"].live.values():
        e["expires_at"] -= 60.0
    authsrv.effect_tick(send, st, 0)
    close = [v[:2] for op, v, _l in sent if op == REGEN_FLOAT]
    check(regen == [PLAYER] and rate_at_apply is not None and abs(rate_at_apply - (-0.04)) < 1e-9
          and abs(st["regen_rate"].get(PLAYER, 0.0) - 0.0) < 1e-9
          and i_42 is not None and i_f1 is not None and i_44 is not None and i_42 < i_f1 < i_44
          and close == [[agents.GV_CHANGE_HEALTH_REGEN, PLAYER]],
          "a hostile's Suffering at the player through the real land_skill: ONE 0x00A2 [44, me] "
          "behind the 0x0042 and the 0x00F1 (2 pips at rank 12: -0.04/s on a 100 pool), and the "
          "0 back at the close -- the review's HEX-2: no apply path sent the rate, so the wearer "
          "bled in silence against a bar the client drew full",
          f"regen={regen} apply={[(hex(op), v) for op, v, _l in at_apply]} close={close}")
    check(effects.CONDITION_PIPS == {478: 3, 480: 7, 483: 4, 484: 4}
          and effects.pips_from([{"skill": SUFFER}, {"skill": FAINT}]) == 0.0,
          "the hex pips sit BESIDE effects.pips_from, not inside it: CONDITION_PIPS is exactly "
          "test_effects 4e's four, and pips_from knows no hex")
    st = fresh_state()
    hex_on(st, FAINT, rank=15)
    lit = authsrv.net_pips(st, PLAYER)
    st0 = fresh_state()
    hex_on(st0, FAINT, rank=0)
    # KEYED ON THE BUILD THE LOADED 135 ROW RECORDS (the content38888 arc,
    # 2026-09-28): the pips are the bonus slot through the client's interpolator,
    # round(bonus_scale0 + (bonus_scale15 - bonus_scale0) x rank / 15), and 38888
    # re-balanced the slot. OBSERVED, skilltable.py on each pristine Gw.exe:
    # 38797 0..3 -> (rank 15, rank 0) = (3, 0), this check's original literals;
    # 38888 1..3 -> (3, 1). Any other build has no expectation and FAILS by name.
    faint_pips = {38797: (3.0, 0.0), 38888: (3.0, 1.0)}
    faint_build = agents.WORLD.get("skills", str(FAINT)).provenance.get("build")
    faint_want = faint_pips.get(faint_build)
    unlit = authsrv.net_pips(st0, PLAYER)
    check(faint_want is not None and (lit, unlit) == faint_want,
          "Faintheartedness's `Health degeneration` bonus (bit SET, read from the slot) is LIT "
          "UP by the same reader: 3 pips at rank 15, and at rank 0 its row's bonus0 (build "
          "38797: 0, build 38888: 1) -- dormant since 2026-08-22, a behaviour change decided "
          "on (--no-hex-degeneration is its revert too)",
          f"(rank 15, rank 0) = {(lit, unlit)} on a build-{faint_build} row, expected {faint_want}"
          + ("" if faint_want is not None else f" -- NO EXPECTATION for build {faint_build}"))
    sent, send = collector()
    st = fresh_state()
    st["player_energy"] = 50.0
    hex_on(st, SUFFER, rank=15)
    st["degen_at"] = time.time() - 1.0
    authsrv.degen_tick(send, st, 0)
    check(abs(st["player_health"] - 94.0) < 0.05 and not sent,
          "degen_tick spends 3 pips x 2 x 1 s = 6 health off the player and SENDS NOTHING: "
          "degeneration is not damage -- no word, no [10], no scatter (WIKI)",
          f"health={st['player_health']} sent={sent}")
    sent, send = collector()
    st = fresh_state()
    body = hostile(st, 10)
    hex_on(st, SUFFER, agent=10, rank=15, caster=PLAYER)
    st["degen_at"] = time.time() - 1.0
    authsrv.degen_tick(send, st, 0)
    check(abs(body["health"] - 94.0) < 0.05 and not sent and not body["dead"],
          "a hexed BODY degenerates the same 6 in silence (the hex is the player's; the body "
          "path reads net_pips too)", f"health={body['health']}")
    # THE KNOWN-BAD ARM: the flag off -- the hex degenerates nothing, Burning still does.
    authsrv.HEX_DEGENERATION = False
    st = fresh_state()
    hex_on(st, SUFFER, rank=15)
    hex_on(st, FAINT, rank=15)
    off = authsrv.net_pips(st, PLAYER)
    st["effects"].apply(PLAYER, BURN, 3, 9.0, time.time(), type_code=8)
    check(off == 0.0 and authsrv.net_pips(st, PLAYER) == 7.0,
          "--no-hex-degeneration: Suffering and Faintheartedness degenerate NOTHING and Burning's "
          "7 still counts -- the reading every run before 2026-09-27 made", f"{off}")
    authsrv.HEX_DEGENERATION = True
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    check(_lock(src.count("effects.pips_from(") == 1
          and src.count("pips = net_pips(state, agent_id, live)") == 1
          and src.count("pips = net_pips(state, agent_id, table.on_agent(agent_id))") == 1
          and _idx(src, "def push_regen(") < _idx(src, "pips = net_pips(state, agent_id, live)")
          and _idx(src, "def degen_tick(") < _idx(src, "pips = net_pips(state, agent_id, table.on_agent(agent_id))")
          and "hex_pips, blocks_adrenaline, signet_activation_factor," in src
          and "HEX_DEGENERATION = False" in src[_idx(src, "    if a.no_hex_degeneration:", _idx(src, "\ndef main():")):
                                              _idx(src, "    if a.no_hex_degeneration:", _idx(src, "\ndef main():")) + 160]
          and _idx(src, "    push_regen(send, state, ep[\"agent\"], conn_id)\n    return ep", _idx(src, "def _apply_effect_on(")) > 0),
          "the source: effects.pips_from is read ONCE, inside net_pips; push_regen and degen_tick "
          "both go through net_pips; the leaf readers are re-exported; main() flips "
          "HEX_DEGENERATION = False under --no-hex-degeneration (M10); _apply_effect_on ends with "
          "push_regen (HEX-2)")
finally:
    authsrv.HEX_DEGENERATION, authsrv.EFFECTS = saved

print("== 36. Soothing Images (56): a `blocks_adrenaline` wearer gains NOTHING and nothing is "
      "sent -- the player's sender and a body's site ==")
saved = (authsrv.ADRENALINE_BLOCK, authsrv.ENERGY, authsrv.ADREN_BAR_GATE)
try:
    authsrv.ADRENALINE_BLOCK = True
    authsrv.ENERGY = True
    authsrv.ADREN_BAR_GATE = False        # the bar gate is SKILLS-B1's question, not this one
    row = agents.WORLD.get("skill_effect", str(SOOTHE))
    rec = agents.WORLD.get("skills", str(SOOTHE))
    check(row.get("blocks_adrenaline") is True
          and (int(rec["scale0"]), int(rec["scale15"]), int(rec["bonus_scale0"])) == (0, 0, 0),
          "the row states the rule; the record's slots are 0/0 (unnumbered text)")
    st = fresh_state()
    check(not authsrv.blocks_adrenaline(st, PLAYER) and not authsrv.adrenaline_blocked(st, PLAYER),
          "no hex: not blocked")
    hex_on(st, SOOTHE, caster=10)
    check(authsrv.blocks_adrenaline(st, PLAYER) and authsrv.adrenaline_blocked(st, PLAYER)
          and not authsrv.adrenaline_blocked(st, 10),
          "Soothing Images on the player: the player is blocked, agent 10 is not (per wearer)")
    # THE PLAYER'S SENDER, control then treatment.
    sent, send = collector()
    st = fresh_state()
    authsrv.player_gains_adrenaline(send, st, 25, time.time(), 0, "a hit")
    ctl = dict(authsrv.player_adrenaline(st).units)
    check(len(sent) == 1 and sent[0][0] == authsrv.AGENT_ADRENALINE_GAIN
          and sent[0][1] == [PLAYER, 25] and ctl and all(v == 25 for v in ctl.values()),
          "CONTROL, unhexed: 0x00CF [player, 25] goes out and every pool takes 25",
          f"sent={sent} units={ctl}")
    sent, send = collector()
    st = fresh_state()
    hex_on(st, SOOTHE, caster=10)
    authsrv.player_gains_adrenaline(send, st, 25, time.time(), 0, "a hit")
    units = dict(authsrv.player_adrenaline(st).units)
    check(not sent and units and all(v == 0 for v in units.values()),
          "hexed: NOTHING is sent and NOTHING is granted (0x00CF 0 vs silence: UNVERIFIED, "
          "silence chosen)", f"sent={sent} units={units}")
    # A BODY'S SITE: hurt_agent_row's hostile arm, control then treatment.
    sent, send = collector()
    st = fresh_state()
    body = hostile(st, 10, skills=((317, 0.0, 0.0),))
    authsrv.hurt_agent_row(send, st, PLAYER, 10, 20.0, 0.2, 0, "a hit")
    ctl = dict(authsrv.agent_adrenaline(body).units)
    check(ctl == {317: 20} and body["health"] == 80.0,
          "CONTROL, an unhexed hostile hit for 20 % of its maximum: 20 units into its pool")
    sent, send = collector()
    st = fresh_state()
    body = hostile(st, 10, skills=((317, 0.0, 0.0),))
    hex_on(st, SOOTHE, agent=10, caster=PLAYER)
    authsrv.hurt_agent_row(send, st, PLAYER, 10, 20.0, 0.2, 0, "a hit")
    units = dict(authsrv.agent_adrenaline(body).units)
    check(units == {317: 0} and body["health"] == 80.0
          and [v for op, v, _l in sent if op == authsrv.AGENT_ADRENALINE_GAIN] == [],
          "hexed: the hit lands (80 left) and the pool takes NOTHING; no 0x00CF names it",
          f"units={units}")
    # THE REVIEW'S M8: the four body sites that were only text-checked, through the real
    # functions -- hit_enemy (the player's swing on a hexed hostile), hurt_agent_row's PARTY
    # arm, land_swing (a hexed hostile landing its swing), scythe_extra_hit.
    _saved_36 = (random.random, authsrv.PLAYER_SWING_DAMAGE, authsrv.BLIND, authsrv.NPC_FOLLOW)
    random.random = lambda: 1.0
    authsrv.PLAYER_SWING_DAMAGE = (10, 10)
    authsrv.BLIND = False
    authsrv.NPC_FOLLOW = False
    try:
        got = {}
        for hexed in (False, True):
            st = fresh_state()
            body = hostile(st, 10, skills=((317, 0.0, 0.0),), max_health=1000.0, health=1000.0)
            if hexed:
                hex_on(st, SOOTHE, agent=10, caster=PLAYER)
            sent, send = collector()
            res = authsrv.hit_enemy(send, st, 10, 0)
            got[hexed] = (res, dict(authsrv.agent_adrenaline(body).units))
        check(got[False][0] == got[True][0] == "landed" and got[False][1].get(317, 0) > 0
              and got[True][1] == {317: 0},
              "hit_enemy: the player's swing lands on a hostile either way (its pool charges); "
              "the HEXED one's pool takes nothing", f"{got}")
        got = {}
        for hexed in (False, True):
            st = fresh_state()
            body = hostile(st, 12, allegiance=agents.ALLEGIANCE_PLAYER, skills=((317, 0.0, 0.0),))
            if hexed:
                hex_on(st, SOOTHE, agent=12, caster=10)
            sent, send = collector()
            authsrv.hurt_agent_row(send, st, 10, 12, 20.0, 0.2, 0, "a hit")
            got[hexed] = (body["health"], dict(authsrv.agent_adrenaline(body).units),
                          [v for op, v, _l in sent if op == authsrv.AGENT_ADRENALINE_GAIN])
        check(got[False] == (80.0, {317: 20}, []) and got[True] == (80.0, {317: 0}, []),
              "hurt_agent_row's PARTY arm: a party body hit for 20 % charges 20 units unhexed and "
              "NOTHING hexed (the hit lands either way; no 0x00CF for a plain party body)", f"{got}")
        got = {}
        for hexed in (False, True):
            st = fresh_state()
            body = hostile(st, 10, (0.0, 0.0), skills=((317, 0.0, 0.0),))
            if hexed:
                hex_on(st, SOOTHE, agent=10, caster=PLAYER)
            sent, send = collector()
            authsrv.land_swing(send, st, 10, body, 0)
            got[hexed] = (st["player_health"] < 100.0, dict(authsrv.agent_adrenaline(body).units))
        check(got[False] == (True, {317: 25}) and got[True] == (True, {317: 0}),
              "land_swing: a hostile's swing lands on the player either way; the HEXED one gains "
              "no strike units (25 unhexed)", f"{got}")
        got = {}
        for hexed in (False, True):
            st = fresh_state()
            body = hostile(st, 11, (10.0, 0.0), skills=((317, 0.0, 0.0),), max_health=1000.0,
                           health=1000.0)
            if hexed:
                hex_on(st, SOOTHE, agent=11, caster=PLAYER)
            sent, send = collector()
            dealt = authsrv.scythe_extra_hit(send, st, 11, 0, None, 0.0, 1.0, time.time(), "extra")
            got[hexed] = (dealt, dict(authsrv.agent_adrenaline(body).units))
        check(got[False][0] == got[True][0] == 10.0 and got[False][1].get(317, 0) > 0
              and got[True][1] == {317: 0},
              "scythe_extra_hit: the extra target takes the same 10 either way and the HEXED one's "
              "pool takes nothing", f"{got}")
    finally:
        random.random, authsrv.PLAYER_SWING_DAMAGE, authsrv.BLIND, authsrv.NPC_FOLLOW = _saved_36
    # THE KNOWN-BAD ARM: the flag off -- the hexed player gains as if unhexed.
    authsrv.ADRENALINE_BLOCK = False
    sent, send = collector()
    st = fresh_state()
    hex_on(st, SOOTHE, caster=10)
    authsrv.player_gains_adrenaline(send, st, 25, time.time(), 0, "a hit")
    check(len(sent) == 1 and sent[0][1] == [PLAYER, 25]
          and all(v == 25 for v in authsrv.player_adrenaline(st).units.values()),
          "--no-adrenaline-block: the hexed player gains and the 0x00CF goes out -- the "
          "reading every run before 2026-09-27 made")
    authsrv.ADRENALINE_BLOCK = True
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    i_pg = _idx(src, "def player_gains_adrenaline(")
    check(_lock(src.count("adrenaline_blocked(state, ") == 7
          and _idx(src, "if adrenaline_blocked(state, PLAYER_AGENT_ID):", i_pg)
          < _idx(src, "if ADREN_BAR_GATE and not bar_holds_adrenal():", i_pg)
          and src.count("if ENERGY and not adrenaline_blocked(state, aid):") == 1
          and src.count("if ENERGY and not adrenaline_blocked(state, target_id):") == 1
          and src.count("\n        if ENERGY and not adrenaline_blocked(state, tid):") == 1
          and src.count("\n    elif ENERGY and not adrenaline_blocked(state, tid):") == 1
          and src.count("if not adrenaline_blocked(state, agent_id):") == 1
          and all(_idx(src, site) > _idx(src, "def " + fn + "(")
              for site, fn in (("if ENERGY and not adrenaline_blocked(state, aid):", "scythe_extra_hit"),
                               ("if ENERGY and not adrenaline_blocked(state, target_id):", "hit_enemy"),
                               ("if ENERGY and not adrenaline_blocked(state, tid):", "hurt_agent_row"),
                               ("if not adrenaline_blocked(state, agent_id):", "land_swing")))
          and "ADRENALINE_BLOCK = False" in src[_idx(src, "    if a.no_adrenaline_block:", _idx(src, "\ndef main():")):
                                               _idx(src, "    if a.no_adrenaline_block:", _idx(src, "\ndef main():")) + 160]),
          "the source: the gate reads at the player's sender (ahead of the bar gate) and at the "
          "five body sites -- scythe_extra_hit, hit_enemy, hurt_agent_row's two arms, land_swing's "
          "hit landed (the hero's 0x00CF inside the gated block) -- 7 reads with the def; main() "
          "flips ADRENALINE_BLOCK = False under --no-adrenaline-block (M10)")
finally:
    authsrv.ADRENALINE_BLOCK, authsrv.ENERGY, authsrv.ADREN_BAR_GATE = saved

print("== 37. Rust (204): the on-cast Cold damage from EXPLICIT endpoints (the record's build: "
      "38888's 10..85, CORROBORATED by the wiki; 38797 read 10..70), and a signet under it "
      "activates x2 ==")
saved = (authsrv.SIGNET_ACTIVATION, authsrv.ENERGY, authsrv.NPC_FOLLOW, authsrv.AREA_HEXES,
         authsrv.SPELL_AREAS)
try:
    authsrv.SIGNET_ACTIVATION = True
    authsrv.ENERGY = False
    authsrv.NPC_FOLLOW = False
    authsrv.AREA_HEXES = True
    authsrv.SPELL_AREAS = True
    row = agents.WORLD.get("skill_effect", str(RUST))
    rec = agents.WORLD.get("skills", str(RUST))
    # The content38888 arc (2026-09-28). skill_effect.204's damage0/15 is a RECORD
    # copied from a client row, and the row names that row's build in its
    # provenance (`build`): 10 / 70 from 38797 until the owner's ruling, 10 / 85
    # from 38888 since (CORROBORATED, client table 38888 + the wiki's 10..85). So
    # the record is compared against ITS OWN build's client row, exactly: the
    # loaded row when the vault is that build's, else the pristine table of that
    # build read through pinned.find + skilltable. SEPARATELY, the loaded row's own
    # bonus slot is keyed on the build that row records. Both tables are OBSERVED,
    # skilltable.py on each pristine Gw.exe: 38797 (10, 70), 38888 (10, 85). A
    # record or a row of any other build FAILS by name.
    rust_slot_by_build = {38797: (10, 70), 38888: (10, 85)}
    rust_record_build = row.provenance.get("build")
    rust_record = (row.get("damage0"), row.get("damage15"))
    rust_build = rec.provenance.get("build")
    rust_loaded = (int(rec["bonus_scale0"]), int(rec["bonus_scale15"]))
    if rust_build == rust_record_build:
        rust_record_src, rust_record_slot = f"the loaded build-{rust_build} row", rust_loaded
    elif rust_record_build not in rust_slot_by_build:
        rust_record_src, rust_record_slot = f"NO EXPECTATION for record build {rust_record_build}", None
    else:
        try:
            sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
            import pinned        # noqa: E402
            import skilltable    # noqa: E402
            _exe, _why = pinned.find(build=rust_record_build)
            with open(_exe, "rb") as _fh:
                _data = _fh.read()
            _base, _count, _score = skilltable.locate_table(_data)
            _r = skilltable.parse_record(_data, _base, RUST)
            rust_record_src = f"the build-{rust_record_build} client table ({_why})"
            rust_record_slot = (int(_r["bonus_scale0"]), int(_r["bonus_scale15"]))
        except (SystemExit, OSError, KeyError, ValueError) as exc:
            rust_record_src, rust_record_slot = (f"UNREADABLE build-{rust_record_build} table: "
                                                 f"{exc}", None)
    check(row.get("bonus_scale_means") == "Cold damage" and row.get("hits_on_cast") is True
          and rust_record_build in rust_slot_by_build
          and rust_record == rust_slot_by_build[rust_record_build]
          and rust_record_slot == rust_record
          and rust_build in rust_slot_by_build
          and rust_loaded == rust_slot_by_build[rust_build]
          and int(rec["skill_arguments"]) == 1 and row.get("signet_activation_multiplier") == 2,
          "the row: `Cold damage` in the BONUS slot with the client's own endpoints carried "
          "explicitly (args = 1: both slots bit-clear and differing), hits_on_cast, x2 signets "
          "-- the record is its provenance build's (38797: 10..70, 38888: 10..85, the wiki's) "
          "and equals THAT build's client row exactly; the loaded row's slot is its own build's",
          f"record {rust_record} of build {rust_record_build} (expected "
          f"{rust_slot_by_build.get(rust_record_build)}) vs {rust_record_slot} from "
          f"{rust_record_src}; loaded build {rust_build} slot {rust_loaded}, expected "
          f"{rust_slot_by_build.get(rust_build)}"
          + ("" if rust_record_build in rust_slot_by_build else
             f" -- NO EXPECTATION for record build {rust_record_build}")
          + ("" if rust_build in rust_slot_by_build else
             f" -- NO EXPECTATION for build {rust_build}"))
    # hex_cast_damage at rank 0 / 12 / 15, keyed on the RECORD's build. The rank-12
    # middle is the check's own interpolation, 10 + (e15 - 10) x 12 / 15, exact on
    # both builds (no rounding question): 38797 10 + 60 x 0.8 = 58, 38888 10 + 75 x
    # 0.8 = 70 -- and the literals are held to it.
    rust_cast_by_build = {38797: (10, 58, 70), 38888: (10, 70, 85)}
    rust_interp_ok = all(e[0] + (e[2] - e[0]) * 12 / 15 == e[1]
                         and (e[0], e[2]) == rust_slot_by_build[b]
                         for b, e in rust_cast_by_build.items())
    want = rust_cast_by_build.get(rust_record_build)
    got = [authsrv.hex_cast_damage(RUST, r) for r in (0, 12, 15)]
    check(rust_interp_ok and want is not None
          and got == [(v, "standalone") for v in want],
          f"hex_cast_damage at rank 0 / 12 / 15 on the record's build {rust_record_build}: "
          f"{' / '.join(map(str, want)) if want else 'NO EXPECTATION'} (38797: 10 / 58 / 70, "
          f"38888: 10 / 70 / 85 -- the middle interpolated here, exact) -- "
          + ({38888: "38888's client row, CORROBORATED by the wiki's 10..85",
              38797: "38797's client row, CONTESTED by the wiki's 10..85"}.get(
              rust_record_build, "NO EXPECTATION")), f"{got}")
    check(authsrv.area_hex(RUST) == 156.0,
          "and it is an area hex at the record's 156 u (adjacent), so the burst rides B1's arms")
    for k in ("damage0", "damage15"):
        row.pop(k)
    try:
        try:
            authsrv.hex_cast_damage(RUST, 12)
            check(False, "without the explicit endpoints the bonus slot must be REFUSED")
        except ValueError:
            check(True, "CONTROL: without damage0/15 the read falls to the slot and skill_scale_value "
                        "REFUSES it (the bit is clear) -- the field is load-bearing, and a "
                        "mislabelled row raises at the completion rather than dealing a number")
    finally:
        row["damage0"], row["damage15"] = rust_record
    check(authsrv.is_signet(HEAL_SIG) and authsrv.is_signet(RES_SIG)
          and not authsrv.is_signet(RUST) and not authsrv.is_signet(FRENZY)
          and not authsrv.is_signet(99999),
          "is_signet: Healing Signet and Resurrection Signet (type 7) yes; a hex, a stance, a "
          "rowless id no")
    st = fresh_state()
    check(authsrv.signet_activation_factor(st, PLAYER) == 1.0
          and authsrv.signet_activation(st, PLAYER, HEAL_SIG, 2.0) == 2.0,
          "no episodes: factor 1.0, the activation untouched")
    hex_on(st, RUST, caster=10)
    check(authsrv.signet_activation_factor(st, PLAYER) == 2.0
          and authsrv.signet_activation(st, PLAYER, HEAL_SIG, 2.0) == 4.0
          and authsrv.signet_activation(st, PLAYER, RES_SIG, 3.0) == 6.0
          and authsrv.signet_activation(st, PLAYER, FRENZY, 0.0) == 0.0
          and authsrv.signet_activation(st, PLAYER, 234, 2.0) == 2.0,
          "under Rust: Healing Signet 2.0 -> 4.0, Resurrection Signet 3.0 -> 6.0; a stance and a "
          "spell keep their own time (signets only, the wiki's word)")
    hex_on(st, RUST, caster=11)
    per_episode = 1.0
    for _ep in st["effects"].on_agent(PLAYER):             # the first cut's product
        per_episode *= float(authsrv.agents.WORLD.get("skill_effect", str(_ep["skill"]))
                             .get("signet_activation_multiplier") or 1.0)
    check(authsrv.signet_activation_factor(st, PLAYER) == 2.0 and per_episode == 4.0
          and len(st["effects"].on_agent(PLAYER)) == 2,
          "two Rusts count ONCE (x2), though the table holds both episodes (retail's "
          "overlapping shape): WIKI GWW 'Effect stacking' rev 2739765 -- most skill effects do "
          "not stack, the strongest application takes precedence (strongest_per_skill). The "
          "known-bad arm, the per-episode product the first cut shipped, reads x4 -- found by "
          "harness run 20260927T174700, a hostile's second Suffering doubling the pips")
    # the same rule for the other two hex readers the D6 hexes ride
    st2 = fresh_state()
    hex_on(st2, SUFFER, caster=10)
    one_suffer = authsrv.episodemods.hex_pips(st2, PLAYER)
    hex_on(st2, SUFFER, caster=10)
    two_suffer = authsrv.episodemods.hex_pips(st2, PLAYER)
    hex_on(st2, FAINT, caster=11)
    with_faint = authsrv.episodemods.hex_pips(st2, PLAYER)
    st3 = fresh_state()
    hex_on(st3, 136, caster=10)
    one_fear = authsrv.episodemods.attack_interval_factor(st3, PLAYER)
    hex_on(st3, 136, caster=10, rank=0)
    two_fear = authsrv.episodemods.attack_interval_factor(st3, PLAYER)
    check(one_suffer > 0 and two_suffer == one_suffer and with_faint > two_suffer
          and one_fear == 1.5 and two_fear == one_fear,
          "Suffering re-applied degenerates ONCE (the same pips), Faintheartedness beside it ADDS "
          "(two skills, the conditions' additive rule); Shadow of Fear re-applied slows the swing "
          "ONCE (x1.5, not x2.25)", (one_suffer, two_suffer, with_faint, one_fear, two_fear))
    # THE BODY SITE, for real: a hostile casting Healing Signet through enemy_attack_tick.
    lands = {}
    for rust in (False, True):
        st = world(1, bar=((HEAL_SIG, 2.0, 4.0),))
        if rust:
            hex_on(st, RUST, agent=10, caster=PLAYER)
        now = time.time()
        tick(st)
        a = st["agents"][10]
        lands[rust] = (a.get("casting"), round(a["cast_lands_at"] - now, 1),
                       round(a["skill_ready"][0] - now, 1))
    check(lands[False][0] == 0 and lands[True][0] == 0
          and lands[False][1] == 2.0 and lands[True][1] == 4.0
          and lands[True][2] - lands[False][2] == 2.0,
          "enemy_attack_tick: the hostile's Healing Signet lands at +2.0 s unhexed and +4.0 s "
          "under Rust, and its recharge anchor moves by the same 2.0 (completion-anchored)",
          f"{lands}")
    # THE PLAYER'S PRESS and ALLY_CAST_TICK, for real (the review's M3: both sites were only
    # text-checked; a plant that left the text in a comment stayed green).
    got = {}
    for rust in (False, True):
        got[rust] = press_e5(HEAL_SIG, PLAYER, hexid=RUST if rust else None)
    check(got == {False: 2.0, True: 4.0},
          "handle_skill_press: the player's Healing Signet's E5 clock is 2.0 s plain and 4.0 s "
          "under Rust -- the doubled activation reaches the real press", f"{got}")
    got = {}
    for rust in (False, True):
        got[rust] = ally_cast(((HEAL_SIG, 2.0, 4.0),), hexid=RUST if rust else None, monk_health=40.0)
    check(got[False][:2] == (2.0, 200) and got[True][:2] == (4.0, 200)
          and abs((got[True][2] - got[False][2]) - 2.0) < 1e-6,
          "ally_cast_tick: a hurt party monk's Healing Signet on itself lands at +2.0 plain and "
          "+4.0 under Rust, its recharge anchor moved by the same 2.0", f"{got}")
    # THE KNOWN-BAD ARM.
    authsrv.SIGNET_ACTIVATION = False
    st = fresh_state()
    hex_on(st, RUST, caster=10)
    check(authsrv.signet_activation(st, PLAYER, HEAL_SIG, 2.0) == 2.0
          and press_e5(HEAL_SIG, PLAYER, hexid=RUST) == 2.0,
          "--no-signet-activation: the signet keeps its table time under Rust, at the reader and "
          "at the real press")
    authsrv.SIGNET_ACTIVATION = True
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    i_press = _idx(src, "def handle_skill_press(")
    check(_lock(src.count("activation = signet_activation(state, agent_id, skill_id, activation)") == 2
          and src.count("activation = signet_activation(state, PLAYER_AGENT_ID, skill_id, activation)") == 1
          and _idx(src, "activation, aftercast, recharge = skill_timing(skill_id)", i_press)
          < _idx(src, "activation = signet_activation(state, PLAYER_AGENT_ID, skill_id, activation)", i_press)
          < _idx(src, "e5_at = begin + activation", i_press)
          and _idx(src, "def enemy_attack_tick(")
          < _idx(src, "activation = signet_activation(state, agent_id, skill_id, activation)")
          < _idx(src, "def ally_cast_tick(")
          < _ridx(src, "activation = signet_activation(state, agent_id, skill_id, activation)")
          and "GV_CASTTIME" not in src[_idx(src, "def signet_activation("):_idx(src, "def hex_skill_use_chain(")]
          and "SIGNET_ACTIVATION = False" in src[_idx(src, "    if a.no_signet_activation:", _idx(src, "\ndef main():")):
                                                 _idx(src, "    if a.no_signet_activation:", _idx(src, "\ndef main():")) + 160]),
          "the source: the three activation sites (the press between skill_timing and the E5 "
          "clock; enemy_attack_tick; ally_cast_tick) all pass through signet_activation, "
          "property 61 is not sent from signet_activation itself (cast_time_word sends it at the "
          "announce, section 41), main() flips "
          "SIGNET_ACTIVATION = False under --no-signet-activation (M10)")
finally:
    (authsrv.SIGNET_ACTIVATION, authsrv.ENERGY, authsrv.NPC_FOLLOW, authsrv.AREA_HEXES,
     authsrv.SPELL_AREAS) = saved

print("== 38. Panic (52): a wearer's skill COMPLETION interrupts every OTHER wearer in 240 u "
      "that is activating -- the skill-less mode, never a swing ==")
saved = (authsrv.HEX_SKILL_USE_CHAIN, authsrv.INTERRUPTS, authsrv.ENERGY, authsrv.NPC_FOLLOW)
try:
    authsrv.HEX_SKILL_USE_CHAIN = True
    authsrv.INTERRUPTS = True
    authsrv.ENERGY = False
    authsrv.NPC_FOLLOW = False
    RC_BAR = ((RC, 0.75, 2.0),)
    row = agents.WORLD.get("skill_effect", str(PANIC))
    rec = agents.WORLD.get("skills", str(PANIC))
    check(row.get("on_skill_use") == "interrupt other wearers"
          and float(rec["aoe_range"]) == 240.0 and int(rec["target"]) == 16,
          "the row states the chain; the record's radius is 240 (nearby), target byte 16")

    def casting(aid, st, at=0.5):
        a = st["agents"][aid]
        a.update({"skills": RC_BAR, "skill_ready": [0.0], "casting": 0,
                  "cast_lands_at": time.time() + at, "cast_recharge": 2.0})
        return a

    def swinging(aid, st):
        a = st["agents"][aid]
        a.update({"casting": None, "swing_lands_at": time.time() + 0.5, "swinging": True})
        return a

    st = fresh_state()
    for aid, pos in ((10, (0.0, 0.0)), (11, (100.0, 0.0)), (12, (300.0, 0.0)),
                     (13, (50.0, 0.0)), (14, (60.0, 0.0)), (15, (70.0, 0.0))):
        hostile(st, aid, pos)
    for aid in (10, 11, 12, 13, 14):
        casting(aid, st)
    swinging(15, st)
    for aid in (10, 11, 12, 14, 15):
        hex_on(st, PANIC, agent=aid, caster=PLAYER)     # the player's Panic on five
    hex_on(st, PANIC, agent=13, caster=99)               # another caster's Panic on 13
    st["agents"][14]["casting"] = None                   # a wearer activating nothing
    st["agents"][14]["cast_lands_at"] = None
    sent, send = collector()
    hit = authsrv.hex_skill_use_chain(send, st, 0, 10, RC)
    ops = [(v[0], v[1]) for op, v, _l in sent if op == INT]
    check(hit == [11] and ops == [(agents.GV_SKILL_STOPPED, 11), (agents.GV_INTERRUPTED, 11)]
          and st["agents"][11]["casting"] is None
          and st["agents"][10]["casting"] == 0 and st["agents"][12]["casting"] == 0
          and st["agents"][13]["casting"] == 0
          and st["agents"][15]["swing_lands_at"] is not None,
          "wearer 10 completes: wearer 11 (100 u, casting) gets [59, 11, 0] [35, 11, 0] and its "
          "cast is gone; 12 (300 u), 13 (another caster's Panic), 14 (activating nothing), 15 "
          "(swinging) and 10 itself are untouched", f"hit={hit} ops={ops}")
    check(not [v for op, v, _l in sent if op == authsrv.GAME_SMSG_SKILL_RECHARGE]
          and st["agents"][11]["skill_ready"][0] - time.time() < 2.5,
          "no disable: the interrupted slot recharges its own 2 s and nothing more (the "
          "interrupter named is the hex, whose row carries no interrupt_disable)")
    # THE MODE IS LOAD-BEARING: the swinging wearer under the OLD mode would be stopped.
    sent, send = collector()
    res = authsrv.interrupt_body(send, st, 15, st["agents"][15], 0, PANIC, 10, mode="action")
    check(res == "swing" and st["agents"][15]["swing_lands_at"] is None,
          "KNOWN-BAD ARM, mode 'action': the same swinging wearer IS stopped -- so the chain's "
          "mode 'skill' is what spares the swing (the wiki's 'interrupted' read as a skill, "
          "RECONSTRUCTION)")
    # THE PLAYER AS VICTIM: a hostile's Panic on the player and a hero; the hero completes.
    st = fresh_state()
    st["action_hold"] = 1
    authsrv.player_pools(st)
    hostile(st, 10, (50.0, 0.0))
    hero = hostile(st, 12, (80.0, 0.0), allegiance=agents.ALLEGIANCE_PLAYER)
    casting(12, st)
    hex_on(st, PANIC, agent=PLAYER, caster=10)
    hex_on(st, PANIC, agent=12, caster=10)
    now = time.time()
    st["pending_casts"] = [{"skill_id": HEAL_SIG, "copy": 0, "begun": True, "cost": 0, "units": 0,
                            "target": None, "begin_at": now, "attack": False,
                            "e5_at": now + 1.0, "e3_at": now + 1.75, "e6_at": now + 5.0,
                            "recharge": 4, "e5_sent": False, "e3_sent": False, "approach": None,
                            "activation": 2.0, "aftercast": 0.75, "recharge_s": 4.0}]
    sent, send = collector()
    hit = authsrv.hex_skill_use_chain(send, st, 0, 12, RC)
    ops = [(op, v[:3]) for op, v, _l in sent]
    E5, E2 = authsrv.GAME_SMSG_SKILL_RECHARGE, authsrv.GAME_SMSG_SKILL_REFUSED
    check(hit == [PLAYER] and ops == [(INT, [8, PLAYER, 0]), (E5, [PLAYER, HEAL_SIG, 0]),
                                       (INT, [agents.GV_SKILL_STOPPED, PLAYER, 0]),
                                       (E2, [PLAYER, HEAL_SIG, 0]),
                                       (INT, [agents.GV_INTERRUPTED, PLAYER, 0])]
          and st["pending_casts"][0]["e5_sent"] and st["pending_casts"][0]["recharge"] == 4,
          "the hero (a wearer) completes: the PLAYER's Healing Signet in activation takes retail's "
          "victim run [8,0] E5(4) [59] E2 [35] and NO disable E5 (test_interrupt 1's shape less "
          "the +20)", f"hit={hit} ops={ops}")
    # THE PLAYER'S REAL PATH (the review's M4): the player wears Panic, so does a casting hostile
    # 100 u off (the same caster's); the player's Flare through the real press + E5 closes its
    # batch with [59, 11, 0] [35, 11, 0]; under the flag the hostile keeps casting.
    got = {}
    for on in (True, False):
        authsrv.HEX_SKILL_USE_CHAIN = on
        st = fresh_state()
        hostile(st, 10, (50.0, 0.0))
        foe11 = casting(11, hostile(st, 11, (100.0, 0.0)) and st)
        hex_on(st, PANIC, agent=PLAYER, caster=10)
        hex_on(st, PANIC, agent=11, caster=10)
        sent, send = collector()
        e5_batch(194, 10, st, send)
        ops = [(v[0], v[1]) for op, v, _l in sent if op == INT]
        got[on] = (ops[-2:], foe11.get("casting"))
    authsrv.HEX_SKILL_USE_CHAIN = True
    check(got[True] == ([(agents.GV_SKILL_STOPPED, 11), (agents.GV_INTERRUPTED, 11)], None)
          and got[False][1] == 0
          and not [x for x in got[False][0] if x[0] in (agents.GV_SKILL_STOPPED, agents.GV_INTERRUPTED)],
          "the PLAYER completes Flare through the real press + E5 wearing Panic: the batch ends "
          "[59, 11, 0] [35, 11, 0] and the hostile's cast is gone; --no-hex-skill-use-chain: it "
          "keeps casting (the review's M4: the hook `... and False` stayed green)", f"{got}")
    # THE BODY'S REAL PATH: land_skill's completion, the chain right behind the 58.
    st = world(2, bar=RC_BAR)
    for aid in (10, 11):
        hex_on(st, PANIC, agent=aid, caster=PLAYER)
        st["agents"][aid].update({"casting": 0, "cast_lands_at": time.time() - 0.01,
                                  "cast_target": aid})
    sent, send = collector()
    authsrv.land_skill(send, st, 10, st["agents"][10], 0)
    ops = [(v[0], v[1]) for op, v, _l in sent if op == INT]
    check(ops[:3] == [(agents.GV_SKILL_FINISHED, 10), (agents.GV_SKILL_STOPPED, 11),
                      (agents.GV_INTERRUPTED, 11)]
          and st["agents"][11]["casting"] is None and st["agents"][10]["casting"] is None,
          "through the real land_skill: [58, 10, 0] then [59, 11, 0] [35, 11, 0] -- the chain "
          "right behind the completion property", f"{ops}")
    # THE KNOWN-BAD ARM: the flag off.
    authsrv.HEX_SKILL_USE_CHAIN = False
    st = world(2, bar=RC_BAR)
    for aid in (10, 11):
        hex_on(st, PANIC, agent=aid, caster=PLAYER)
        st["agents"][aid].update({"casting": 0, "cast_lands_at": time.time() - 0.01,
                                  "cast_target": aid})
    sent, send = collector()
    authsrv.land_skill(send, st, 10, st["agents"][10], 0)
    check(authsrv.hex_skill_use_chain(send, st, 0, 10, RC) == []
          and st["agents"][11]["casting"] == 0
          and not [v for op, v, _l in sent if op == INT and v[0] == agents.GV_INTERRUPTED],
          "--no-hex-skill-use-chain: the completion interrupts nobody and 11 keeps casting")
    authsrv.HEX_SKILL_USE_CHAIN = True
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    i_ip, i_ib = _idx(src, "def interrupt_player("), _idx(src, "def interrupt_body(")
    check(_lock(src.count("hex_skill_use_chain(send, state, conn_id, PLAYER_AGENT_ID, cast[\"skill_id\"])") == 1
          and src.count("hex_skill_use_chain(send, state, conn_id, agent_id, skill_id)") == 1
          and _idx(src, "def cast_tick(") < _idx(src, "if HEX_SKILL_USE_CHAIN and not _na_fail:")
          < _idx(src, "def apply_effect(")
          and _idx(src, "def land_skill(") < _idx(src, "hex_skill_use_chain(send, state, conn_id, agent_id, skill_id)")
          and src.count('mode in ("action", "attacking")') == 2
          and src.count("mode == INTERRUPT_MODE_SKILL") == 2
          and i_ip < _idx(src, "mode == INTERRUPT_MODE_SKILL") < i_ib
          < _ridx(src, "mode == INTERRUPT_MODE_SKILL")
          and src.count("if not _na_fail:") == 2
          and "HEX_SKILL_USE_CHAIN = False" in src[_idx(src, "    if a.no_hex_skill_use_chain:", _idx(src, "\ndef main():")):
                                                   _idx(src, "    if a.no_hex_skill_use_chain:", _idx(src, "\ndef main():")) + 160]),
          "the source: the two hook sites (the player's E5 batch, a body's land_skill), main() "
          "flips HEX_SKILL_USE_CHAIN = False under its flag (M10); the new "
          "mode is read in both cast branches and in NEITHER swing branch (the two 'action / "
          "attacking' swing gates are untouched); test_labelconsumers' `if not _na_fail:` count "
          "still 2")
finally:
    (authsrv.HEX_SKILL_USE_CHAIN, authsrv.INTERRUPTS, authsrv.ENERGY, authsrv.NPC_FOLLOW) = saved

# ---------------------------------------------------------------------------
# 39-40: DESKWORK-D6 step 5, B4 (2026-09-27; studies/skills/FINDINGS.md 62): the last
#        two conditions to DO something -- Cracked Armor 2077 and Dazed 485. NEITHER
#        was ever inflicted by a skill on any live tape (the Isle's are environmental,
#        hexjoin C1), so every number is the condition's OWN client record and every
#        rule is the wiki's; every check names its control and its known-bad arm.
CRACKED = effects.CONDITION_BY_NAME["Cracked Armor"]
DAZED_C = effects.CONDITION_BY_NAME["Dazed"]
SHELL, HAZE, ORB_J, POWER = 2059, 799, 230, 322       # Shell Shock, Beguiling Haze, Lightning Javelin, Power Attack
CR_PEN, CR_FLOOR = 20.0, 60.0


def cond_on(state, cid, agent=PLAYER, rank=12, seconds=8.0):
    return state["effects"].apply(agent, cid, rank, seconds, time.time(), type_code=8)


def pending_spell(state, sid=ORB_J, activation=1.0, recharge=5, attack=False):
    now = time.time()
    state["action_hold"] = 1
    authsrv.player_pools(state)
    state["pending_casts"] = [{"skill_id": sid, "copy": 0, "begun": True, "cost": 0, "units": 0,
                               "target": 10, "begin_at": now, "attack": attack,
                               "e5_at": now + activation, "e3_at": now + activation + 0.75,
                               "e6_at": now + 10.0, "recharge": recharge, "e5_sent": False,
                               "e3_sent": False, "approach": None, "activation": activation,
                               "aftercast": 0.75, "recharge_s": float(recharge)}]
    return state["pending_casts"][0]


def stops(sent, who):
    return [v[0] for op, v, _l in sent if op == INT and v[1] == who
            and v[0] in (agents.GV_SKILL_STOPPED, agents.GV_INTERRUPTED)]


print("== 39. Cracked Armor (2077): -20 INTO the bonus category before its cap, before the "
      "penetration, floored at 60 or the core -- the player and every body site ==")
saved = (authsrv.CRACKED_ARMOR, authsrv.ARMOUR_TERM, authsrv.ENERGY, authsrv.BLIND,
         authsrv.CASTING_ARMOUR, authsrv.roll_hit_location, authsrv.NPC_FOLLOW,
         authsrv.PLAYER_SWING_DAMAGE, random.random)
try:
    authsrv.CRACKED_ARMOR = True
    authsrv.ARMOUR_TERM = True
    authsrv.ENERGY = False
    authsrv.BLIND = False
    authsrv.CASTING_ARMOUR = True
    authsrv.NPC_FOLLOW = False
    row = agents.WORLD.get("skill_effect", str(SHELL))
    rec = agents.WORLD.get("skills", str(SHELL))
    check(row.get("scale_means") == "Lightning damage" and row.get("bonus_scale_means") == "Cracked Armor"
          and row.get("damage_type") == 4 and int(rec["skill_arguments"]) == 6
          and (int(rec["scale0"]), int(rec["scale15"]), int(rec["bonus_scale0"]), int(rec["bonus_scale15"]))
          == (10, 30, 5, 20)
          and authsrv.skill_condition(SHELL, 12) == (CRACKED, 17.0)
          and authsrv.skill_damage(SHELL, 12) == (26, "standalone")
          and authsrv.skill_base_penetration(SHELL) == 0.25,
          "the inflicter, Shell Shock 2059: the word 10..30 lightning (26 at rank 12), Cracked "
          "Armor 5..20 s (17 at rank 12) through the EXISTING skill_condition join, and Air "
          "Magic's 25 % already on skill_base_penetration -- zero join code")
    na = combatmath.net_armour
    check([na(80, 20), na(80, 20, 0, CR_PEN), na(60, 0, 0, CR_PEN), na(50, 0, 0, CR_PEN),
           na(50, 20, 0, CR_PEN), na(60, 0, 16, CR_PEN), na(0, 0, 16, CR_PEN)]
          == [100.0, 80.0, 60.0, 50.0, 50.0, 60.0, 16.0],
          "net_armour: 80 + 20 = 100 uncracked and 80 cracked; 60 cracked stays 60 (the floor); "
          "50 stays 50 and 50 + 20 falls to 50 (a core below 60 is its own floor -- WIKI "
          "'Effect stacking'); a 60 core with a 16 shield holds at 60; a bare location with a "
          "shield keeps the shield")
    check(na(80, 46, 0, CR_PEN) == na(80, 46) == 105.0
          and na(80, 40, 0, CR_PEN) == 100.0 and na(80, 40) == 105.0,
          "BEFORE THE CAP: a +46 boost leaves Cracked Armor without effect (46 - 20 = 26 caps to "
          "the same 25 -- the page's own bug note), while +40 - 20 = 20 loses five of the capped "
          "25; subtracting AFTER the cap could not produce the note")
    st = fresh_state()
    check(not authsrv.is_cracked(st, PLAYER) and authsrv.cracked_penalty(st, PLAYER) == 0.0
          and authsrv.cracked_penalty(None, PLAYER) == 0.0,
          "no episode: not Cracked, no penalty; no state (the printing callers) no penalty")
    cond_on(st, CRACKED)
    check(authsrv.is_cracked(st, PLAYER) and authsrv.has_condition(st, PLAYER, CRACKED)
          and authsrv.cracked_penalty(st, PLAYER) == 20.0 and authsrv.cracked_penalty(st, 10) == 0.0,
          "Cracked Armor on the player: 20 for the player, 0 for agent 10 (per wearer)")
    # THE PLAYER'S PHYSICAL RATING, and a hostile's swing landing on it.
    _loc = authsrv.roll_hit_location()
    authsrv.roll_hit_location = lambda: _loc
    plain_ar = authsrv.player_armour_at(_loc, physical=True, state=fresh_state())
    cracked_ar = authsrv.player_armour_at(_loc, physical=True, state=st)
    piece = agents.item_template(agents.worn_piece_key(_loc))
    rating, bonus = combatmath.armour_of_piece(piece, "physical", authsrv.ARMOR_RATING_MODIFIER,
                                               authsrv.ARMOR_VS_TYPE_MODIFIER,
                                               level=authsrv.player_level_of(st))
    check(plain_ar is not None and plain_ar == na(rating, bonus)
          and cracked_ar == na(rating, bonus, 0.0, CR_PEN) and cracked_ar == plain_ar - 20.0,
          f"the location's physical rating is the piece's {rating:.0f} + its {bonus:.0f} vs. "
          f"physical = {plain_ar:.0f}; Cracked eats the bonus: {cracked_ar:.0f} (-20)",
          f"plain={plain_ar} cracked={cracked_ar} piece={rating, bonus}")
    _foe = {"name": "hatcher", "dead": False, "pos": (0.0, 0.0)}

    def _swing(state):
        sent, send = collector()
        authsrv.land_swing(send, state, ENEMY, _foe, 0)
        return 100.0 - state["player_health"]

    base = authsrv.player_full_max_health(fresh_state()) * authsrv.ENEMY_HIT_FRACTION
    quiet = _swing(fresh_state())
    cracked = _swing(st)
    check(quiet == math.floor(base * authsrv.armour_multiplier(plain_ar))
          and cracked == math.floor(base * authsrv.armour_multiplier(cracked_ar))
          and cracked > quiet,
          f"a hostile's swing on the Cracked player: {quiet:.0f} quiet, {cracked:.0f} cracked "
          f"-- the fraction at the cracked rating, 2^(20/40) to the whole point",
          f"quiet={quiet} cracked={cracked}")
    st2 = fresh_state()
    cond_on(st2, CRACKED)
    st2["pending_casts"] = [{"skill_id": 1, "begin_at": 0.0, "e5_at": math.inf, "e5_sent": False}]
    both = _swing(st2)
    check(both == math.floor(base * authsrv.armour_multiplier(cracked_ar - 40.0)),
          "Cracked Armor AND Healing Signet's -40 in use: the -40 comes off the CRACKED rating "
          "after the cap (the wiki's step 4 -- casting_armour_penalty's own quote)", f"{both}")
    # THE ELEMENTAL FLOOR: the starter set's 25 elemental is its core and cannot be cracked.
    sp_plain = authsrv.spell_armour_for(ORB_J, fresh_state())
    sp_cracked = authsrv.spell_armour_for(ORB_J, st)
    check(sp_plain is not None and sp_cracked == sp_plain
          and combatmath.armour_of_piece(piece, "elemental", authsrv.ARMOR_RATING_MODIFIER,
                                         authsrv.ARMOR_VS_TYPE_MODIFIER,
                                         level=authsrv.player_level_of(st))[0] < CR_FLOOR,
          f"a spell on the Cracked player meets the SAME rating ({sp_plain}): the set's elemental "
          f"core is below 60 and a core below 60 is its own floor -- Cracked Armor moves nothing "
          f"there (WIKI 'Effect stacking'; the physical +20 above is what it eats)",
          f"plain={sp_plain} cracked={sp_cracked}")
    # BODIES: the one helper, then the three real paths.
    st = fresh_state()
    hostile(st, 10, armor_rating=100.0)
    plain_b = [authsrv.cracked_body_armour(st, 10, r) for r in (100.0, 60.0, 50.0, None)]
    cond_on(st, CRACKED, agent=10)
    check(plain_b == [100.0, 60.0, 50.0, None]
          and [authsrv.cracked_body_armour(st, 10, r) for r in (100.0, 60.0, 50.0, None)]
          == [80.0, 60.0, 50.0, None],
          "cracked_body_armour: identity uncracked; cracked 100 -> 80, 60 stays 60, 50 stays 50, "
          "an armour-less row (None) stays armour-less")
    dealt = {}
    for cr in (False, True):
        st = fresh_state()
        hostile(st, 10, (0.0, 0.0))
        body = hostile(st, 12, (10.0, 0.0), allegiance=agents.ALLEGIANCE_PLAYER,
                       armor_rating=100.0, max_health=1000.0, health=1000.0)
        if cr:
            cond_on(st, CRACKED, agent=12)
        sent, send = collector()
        res = authsrv.land_swing_on_body(send, st, 10, st["agents"][10], 12, 0)
        dealt[cr] = (res, 1000.0 - body["health"])
    check(dealt == {False: ("landed", 50.0), True: ("landed", 70.0)},
          "land_swing_on_body, a hostile at a party body of 1000/100 AR: 50 uncracked "
          "(1000 x 0.10 x 2^-1), 70 cracked (at 80: 2^-0.5 = 70.7)", f"{dealt}")
    random.random = lambda: 1.0            # no critical, no block: the roll alone
    authsrv.PLAYER_SWING_DAMAGE = (100, 100)
    dealt = {}
    for cr in (False, True):
        st = fresh_state()
        body = hostile(st, 10, armor_rating=100.0, max_health=1000.0, health=1000.0)
        if cr:
            cond_on(st, CRACKED, agent=10)
        sent, send = collector()
        res = authsrv.hit_enemy(send, st, 10, 0)
        dealt[cr] = (res, 1000.0 - body["health"])
    random.random = saved[-1]
    authsrv.PLAYER_SWING_DAMAGE = saved[-2]
    check(dealt[False][0] == "landed" and dealt[True][0] == "landed"
          and dealt[True][1] > dealt[False][1]
          and abs(dealt[True][1] / dealt[False][1] - 2 ** 0.5) < 0.03,
          "hit_enemy, the player's flat 100 hammer on a 100-AR hostile: the cracked hit is "
          "2^(20/40) the plain one to the whole point (the rating read now wraps "
          "cracked_body_armour)", f"{dealt}")
    terms = {}
    for cr in (False, True):
        st = fresh_state()
        hostile(st, 10)
        hostile(st, 12, allegiance=agents.ALLEGIANCE_PLAYER, armor_rating=100.0)
        if cr:
            cond_on(st, CRACKED, agent=12)
        terms[cr] = authsrv.body_spell_terms(st, st["agents"][10], ORB_J, 40.0, 12, True)[3]
    check(terms == {False: 75.0, True: 60.0},
          "body_spell_terms, a Javelin (25 % penetration) at a Cracked party body of 100 AR: "
          "75 uncracked, 60 cracked = (100 - 20) x 0.75 -- BEFORE the penetration", f"{terms}")
    terms = {}
    for cr in (False, True):
        st = fresh_state()
        hostile(st, 10)
        hostile(st, 12, allegiance=agents.ALLEGIANCE_PLAYER, armor_rating=200.0)
        if cr:
            cond_on(st, CRACKED, agent=12)
        terms[cr] = authsrv.body_spell_terms(st, st["agents"][10], ORB_J, 40.0, 12, True)[3]
    check(terms == {False: 150.0, True: 135.0},
          "and at 200 AR, where the floor cannot bite: 150 uncracked, 135 cracked = (200 - 20) x "
          "0.75 -- after the penetration it would read 150 - 20 = 130 (the review's M2: at 100 AR "
          "both orders read 60, the floor lifting 55 back)", f"{terms}")
    # THE REVIEW'S R34-3: the Bonus-vs-Core ambiguity bonus_armour records is LIVE here -- the
    # Core reading's arm, pinned beside the shipped Bonus reading (CONTESTED).
    check(na(rating, bonus, 0.0, CR_PEN) == rating and na(rating + bonus, 0.0, 0.0, CR_PEN) == rating + bonus,
          f"CONTESTED (net_armour's docstring): under the BONUS reading (shipped, GWW 'Armor "
          f"calculation') the {rating:.0f} + {bonus:.0f} vs. physical reads {rating:.0f} Cracked; "
          f"under the CORE reading (GWW 'Basic armor' prints the +20 as basic) the core is "
          f"{rating + bonus:.0f} < 60 and is its own floor -- Cracked Armor moves NOTHING on the "
          f"starter set; a tooltip / armour-panel read in a run settles it",
          f"bonus={na(rating, bonus, 0.0, CR_PEN)} core={na(rating + bonus, 0.0, 0.0, CR_PEN)}")
    # THE REVIEW'S M9: scythe_extra_hit and the preparation splash, through the real functions.
    random.random = lambda: 1.0
    authsrv.PLAYER_SWING_DAMAGE = (100, 100)
    dealt = {}
    for cr in (False, True):
        st = fresh_state()
        body = hostile(st, 11, (10.0, 0.0), armor_rating=100.0, max_health=1000.0, health=1000.0)
        if cr:
            cond_on(st, CRACKED, agent=11)
        sent, send = collector()
        dealt[cr] = authsrv.scythe_extra_hit(send, st, 11, 0, 0, 0.0, 1.0, time.time(), "extra")
    random.random = saved[-1]
    authsrv.PLAYER_SWING_DAMAGE = saved[-2]
    check(dealt[True] > dealt[False] and abs(dealt[True] / dealt[False] - 2 ** 0.5) < 0.03,
          "scythe_extra_hit on a 100-AR foe: the cracked extra hit is 2^(20/40) the plain one to "
          "the whole point", f"{dealt}")
    splash = {}
    for cr in (False, True):
        st = fresh_state()
        hostile(st, 10, (0.0, 0.0), armor_rating=100.0, max_health=1000.0, health=1000.0)
        body = hostile(st, 11, (50.0, 0.0), armor_rating=100.0, max_health=1000.0, health=1000.0)
        if cr:
            cond_on(st, CRACKED, agent=11)
        sent, send = collector()
        reached = authsrv.preparation_splash(send, st, IGNITE, 100.0, 10, 0, 12, None)
        splash[cr] = (reached, 1000.0 - body["health"])
    check(splash[False][0] == splash[True][0] == [11] and splash[True][1] > splash[False][1]
          and abs(splash[True][1] / splash[False][1] - 2 ** 0.5) < 0.03,
          "the preparation splash (Ignite Arrows, 156 u) on the 100-AR foe beside the target: "
          "reached either way, the cracked splash 2^(20/40) the plain one", f"{splash}")
    # THE REVIEW'S R34-7: player_spell_armour puts the SHIELD inside the leaf's floor, as
    # player_armour_at does -- a Cracked 60 core with a 16 shield holds at 60, not 76.
    _saved_39 = (authsrv.offhand_armour, combatmath.armour_of_piece)
    authsrv.offhand_armour = lambda damage_type="physical", state=None: 16.0
    combatmath.armour_of_piece = lambda *a, **k: (60.0, 0.0)
    try:
        st_c = fresh_state()
        cond_on(st_c, CRACKED)
        psa = (authsrv.player_spell_armour(fresh_state()), authsrv.player_spell_armour(st_c))
    finally:
        authsrv.offhand_armour, combatmath.armour_of_piece = _saved_39
    check(psa == (76.0, 60.0) and psa[1] == na(60.0, 0.0, 16.0, CR_PEN),
          "player_spell_armour with a 60 piece and a 16 shield: 76 plain, 60 Cracked -- the shield "
          "inside net_armour's floor (the first cut added it after the leaf and read 76 Cracked, "
          "76 != player_armour_at's 60)", f"{psa}")
    # THE REAL INFLICTER: a hostile's Shell Shock at the player through land_skill.
    st = world(1, bar=((SHELL, 1.0, 8.0),))
    a = st["agents"][10]
    a.update({"casting": 0, "cast_lands_at": time.time() - 0.01, "cast_target": PLAYER})
    sent, send = collector()
    authsrv.land_skill(send, st, 10, a, 0)
    ops = [(op, v[:3]) for op, v, _l in sent]
    applies = [v for op, v, _l in sent if op == authsrv.GAME_SMSG_EFFECT_APPLY]
    check(ops[0] == (INT, [agents.GV_SKILL_FINISHED, 10, 0])
          and applies and applies[0][:2] == [PLAYER, CRACKED] and applies[0][4] == authsrv._f32(17.0)
          and authsrv.is_cracked(st, PLAYER)
          and [v for op, v, _l in sent if op == FLOAT_T and v[0] == agents.PROP_DAMAGE],
          "through the real land_skill: [58, 10, 0], 0x0042 [me, 2077, r, buff, 17.0], the word "
          "-- the player is Cracked; the -20 then meets the NEXT hit", f"{ops}")
    before = st["player_health"]
    _swing(st)
    cracked2 = before - st["player_health"]
    check(cracked2 == cracked,
          f"and the next hostile swing on that player deals the cracked {cracked:.0f}, not the "
          f"quiet {quiet:.0f}", f"{cracked2}")
    # THE KNOWN-BAD ARM: the flag off -- the icon and the bit alone.
    authsrv.CRACKED_ARMOR = False
    st = fresh_state()
    cond_on(st, CRACKED)
    hostile(st, 10, armor_rating=100.0)
    cond_on(st, CRACKED, agent=10)
    check(authsrv.cracked_penalty(st, PLAYER) == 0.0
          and authsrv.player_armour_at(_loc, physical=True, state=st) == plain_ar
          and authsrv.cracked_body_armour(st, 10, 100.0) == 100.0 and _swing(st) == quiet
          and authsrv.is_cracked(st, PLAYER),
          "--no-cracked-armor: the condition is up and moves nothing -- the plain rating, the "
          "quiet swing, the body's 100 (the reading every run before 2026-09-27 made)")
    authsrv.CRACKED_ARMOR = True
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    i_ls = _idx(src, "def land_swing(")
    i_bsa, i_lsob, i_he = (_idx(src, "def body_spell_armour("), _idx(src, "def land_swing_on_body("),
                           _idx(src, "def hit_enemy("))
    check(_lock(src.count("cracked_body_armour(state, ") == 6           # five sites + the def
          and _idx(src, "def scythe_extra_hit(") < _idx(src, "cracked_body_armour(state, aid, creature_typed_rating(foe.get(")
          < _ridx(src, "cracked_body_armour(state, aid, creature_typed_rating(foe.get(") < i_bsa
          < _idx(src, "rating = cracked_body_armour(state, tid, rating)") < i_he
          < _idx(src, "cracked_body_armour(state, target_id, creature_typed_rating(agent.get(") < i_lsob
          < _idx(src, "armour = cracked_body_armour(state, tid, armour)")
          and src.count("cracked=cracked_penalty(state, PLAYER_AGENT_ID)") == 4
          and _idx(src, "armour = penetrated_armour(armour, (body_weapon_items(agent) or (None,))[0],", i_ls)
          < _idx(src, "armour += casting_armour_penalty(state)", i_ls)
          and "return spell_armour_for(skill_id, state)" in src[i_bsa:i_bsa + 1500]
          and "armour = creature_typed_rating(body_armour_rating(row), row," in src[i_lsob:i_lsob + 3000]
          and 'row.get("armor_rating")' not in inspect.getsource(authsrv.land_swing_on_body)
          and "CRACKED_ARMOR = False" in src[_idx(src, "    if a.no_cracked_armor:", _idx(src, "\ndef main():")):
                                             _idx(src, "    if a.no_cracked_armor:", _idx(src, "\ndef main():")) + 160]),
          "the source: the five body sites through cracked_body_armour (the scythe's extra hit, "
          "the preparation splash, body_spell_armour (in main's row_spell_armour since the merge, the typed "
          "rating then cracked), hit_enemy, land_swing_on_body; 6 with the def), the "
          "player's four reads passing the penalty INTO the leaf, land_swing's casting penalty "
          "still after the penetration, test_agentlife's literals intact, main() flips "
          "CRACKED_ARMOR = False under --no-cracked-armor (M10)")
finally:
    (authsrv.CRACKED_ARMOR, authsrv.ARMOUR_TERM, authsrv.ENERGY, authsrv.BLIND,
     authsrv.CASTING_ARMOUR, authsrv.roll_hit_location, authsrv.NPC_FOLLOW,
     authsrv.PLAYER_SWING_DAMAGE, random.random) = saved

print("== 40. Dazed (485): spells activate x2, a landed ATTACK interrupts the spell in "
      "activation, and Dazed landing interrupts it at once -- never a signet, never a swing ==")
saved = (authsrv.DAZED, authsrv.INTERRUPTS, authsrv.ENERGY, authsrv.NPC_FOLLOW, authsrv.BLIND,
         authsrv.ARMOUR_TERM)
try:
    authsrv.DAZED = True
    authsrv.INTERRUPTS = True
    authsrv.ENERGY = False
    authsrv.NPC_FOLLOW = False
    authsrv.BLIND = False
    authsrv.ARMOUR_TERM = True
    row = agents.WORLD.get("skill_effect", str(HAZE))
    rec = agents.WORLD.get("skills", str(HAZE))
    check(row.get("scale_means") == "Dazed" and int(rec["skill_arguments"]) == 2
          and (int(rec["scale0"]), int(rec["scale15"])) == (3, 9) and int(rec["type_code"]) == 5
          and authsrv.skill_condition(HAZE, 12) == (DAZED_C, 8.0),
          "the inflicter, Beguiling Haze 799: Dazed 3..9 s in the scale slot (8 at rank 12) "
          "through the existing join; a Spell, so a hostile casts it at the player (the Shadow "
          "Step is NOT modelled, said in the row)")
    check(authsrv._is_spell_skill(ORB_J) and authsrv._is_spell_skill(234) and authsrv._is_spell_skill(ROF)
          and not authsrv._is_spell_skill(HEAL_SIG) and not authsrv._is_spell_skill(FRENZY)
          and not authsrv._is_spell_skill(POWER) and not authsrv._is_spell_skill(99999),
          "_is_spell_skill: a spell, a hex, an enchantment yes; a signet, a stance, an attack "
          "skill, a rowless id no (combatmath.is_spell_type on the record)")
    st = fresh_state()
    check(not authsrv.is_dazed(st, PLAYER) and authsrv.dazed_activation(st, PLAYER, ORB_J, 2.0) == 2.0,
          "not Dazed: the activation untouched")
    cond_on(st, DAZED_C)
    check(authsrv.is_dazed(st, PLAYER)
          and authsrv.dazed_activation(st, PLAYER, ORB_J, 2.0) == 4.0
          and authsrv.dazed_activation(st, PLAYER, 234, 2.0) == 4.0
          and authsrv.dazed_activation(st, PLAYER, HEAL_SIG, 2.0) == 2.0
          and authsrv.dazed_activation(st, PLAYER, POWER, 0.0) == 0.0
          and authsrv.dazed_activation(st, PLAYER, FRENZY, 0.0) == 0.0
          and authsrv.dazed_activation(st, 10, ORB_J, 2.0) == 2.0,
          "Dazed: a spell 2.0 -> 4.0 (the record's 200 %), a hex too; a signet, an attack skill "
          "and a stance keep their time; another agent is untouched")
    # THE BODY SITE, for real: a hostile casting Restore Condition (a Spell) / Healing Signet.
    lands = {}
    for dz in (False, True):
        st = world(2, bar=((RC, 0.75, 2.0),))
        if dz:
            cond_on(st, DAZED_C, agent=10)
        now = time.time()
        tick(st)
        a = st["agents"][10]
        lands[dz] = (a.get("casting"), round(a["cast_lands_at"] - now, 2),
                     round(a["skill_ready"][0] - now, 2))
    check(lands[False][:2] == (0, 0.75) and lands[True][:2] == (0, 1.5)
          and abs((lands[True][2] - lands[False][2]) - 0.75) < 1e-6,
          "enemy_attack_tick: the hostile's Restore Condition lands at +0.75 s plain and +1.5 s "
          "Dazed, its recharge anchor moved by the same 0.75 (completion-anchored)", f"{lands}")
    st = world(1, bar=((HEAL_SIG, 2.0, 4.0),))
    cond_on(st, DAZED_C, agent=10)
    now = time.time()
    tick(st)
    check(st["agents"][10].get("casting") == 0
          and round(st["agents"][10]["cast_lands_at"] - now, 1) == 2.0,
          "CONTROL: the same hostile's Healing Signet under Dazed lands at +2.0 -- a signet is "
          "not a spell (the wiki's word)")
    # THE MODE, on the player: a spell in activation, and only that.
    E5, E2 = authsrv.GAME_SMSG_SKILL_RECHARGE, authsrv.GAME_SMSG_SKILL_REFUSED
    st = fresh_state()
    hostile(st, 10, (50.0, 0.0))
    cast = pending_spell(st)
    cond_on(st, DAZED_C)
    sent, send = collector()
    res = authsrv.dazed_interrupt(send, st, 0, PLAYER, 10)
    ops = [(op, v[:3]) for op, v, _l in sent]
    check(res == "cast" and ops == [(INT, [8, PLAYER, 0]), (E5, [PLAYER, ORB_J, 0]),
                                    (INT, [agents.GV_SKILL_STOPPED, PLAYER, 0]),
                                    (E2, [PLAYER, ORB_J, 0]), (INT, [agents.GV_INTERRUPTED, PLAYER, 0])]
          and cast["e5_sent"] and cast["recharge"] == 5
          and [v[3] for op, v, _l in sent if op == E5] == [5],
          "a Dazed player's spell: retail's victim run [8,0] E5(5) [59] E2 [35] and NO disable "
          "(the interrupter named is Dazed's own id, whose row carries none)", f"{res} {ops}")
    for sid, attack, what in ((HEAL_SIG, False, "a signet"), (POWER, True, "an attack skill")):
        st = fresh_state()
        hostile(st, 10, (50.0, 0.0))
        cast = pending_spell(st, sid=sid, attack=attack)
        cond_on(st, DAZED_C)
        sent, send = collector()
        res = authsrv.dazed_interrupt(send, st, 0, PLAYER, 10)
        check(res is None and not sent and not cast["e5_sent"],
              f"a Dazed player activating {what} ({sid}) is NOT interrupted -- mode 'spell' is "
              f"spells only", f"{res} {sent}")
    st = fresh_state()
    hostile(st, 10, (50.0, 0.0))
    cast = pending_spell(st)
    sent, send = collector()
    check(authsrv.dazed_interrupt(send, st, 0, PLAYER, 10) is None and not sent,
          "CONTROL, not Dazed: nothing")
    # THE REAL ATTACK SITE: a hostile's swing landing on the Dazed casting player.
    _foe = {"name": "hatcher", "dead": False, "pos": (0.0, 0.0)}
    shapes = {}
    for dz in (False, True):
        st = fresh_state()
        hostile(st, 10, (0.0, 0.0))
        cast = pending_spell(st)
        if dz:
            cond_on(st, DAZED_C)
        sent, send = collector()
        authsrv.land_swing(send, st, 10, _foe, 0)
        shapes[dz] = (stops(sent, PLAYER), cast["e5_sent"], st["player_health"] < 100.0)
    check(shapes[False] == ([], False, True)
          and shapes[True] == ([agents.GV_SKILL_STOPPED, agents.GV_INTERRUPTED], True, True),
          "land_swing: the hostile's plain swing lands on the casting player -- untouched when "
          "not Dazed (CONTROL), [59] [35] and the cast gone when Dazed (any successful ATTACK, "
          "WIKI 'Easily interruptible')", f"{shapes}")
    i_word = i_stop = None
    check(sent and [k for k, (op, v, _l) in enumerate(sent) if op == FLOAT_T and v[0] == agents.PROP_DAMAGE]
          < [k for k, (op, v, _l) in enumerate(sent) if op == INT and v[0] == agents.GV_SKILL_STOPPED],
          "and the interrupt run rides BEHIND the swing's damage word (retail's order for an "
          "interrupting attack, 1 of 1)")
    st = fresh_state()
    hostile(st, 10, (0.0, 0.0))
    cast = pending_spell(st)
    cond_on(st, DAZED_C)
    sent, send = collector()
    authsrv.body_spell_word(send, st, 10, ORB_J, PLAYER, False, 10.0, authsrv._f32(0.1), None, 10.0, 0)
    check(not stops(sent, PLAYER) and not cast["e5_sent"] and st["player_health"] == 90.0,
          "CONTROL: a body's SPELL (Javelin's word) landing on the Dazed casting player interrupts "
          "nothing -- an attack, not any hit (the Javelin's own 'attacking' does not reach a "
          "spell either)")
    # A BODY AS VICTIM: a hostile's swing on a Dazed casting party body; the player's swing on
    # a Dazed casting hostile; a swinging Dazed body is never touched.
    RC_BAR = ((RC, 0.75, 2.0),)

    def casting(aid, st, at=0.5):
        a = st["agents"][aid]
        a.update({"skills": RC_BAR, "skill_ready": [0.0], "casting": 0,
                  "cast_lands_at": time.time() + at, "cast_recharge": 2.0})
        return a

    shapes = {}
    for dz in (False, True):
        st = fresh_state()
        hostile(st, 10, (0.0, 0.0))
        hostile(st, 12, (10.0, 0.0), allegiance=agents.ALLEGIANCE_PLAYER, max_health=1000.0,
                health=1000.0)
        casting(12, st)
        if dz:
            cond_on(st, DAZED_C, agent=12)
        sent, send = collector()
        authsrv.land_swing_on_body(send, st, 10, st["agents"][10], 12, 0)
        shapes[dz] = (stops(sent, 12), st["agents"][12]["casting"])
    check(shapes == {False: ([], 0), True: ([agents.GV_SKILL_STOPPED, agents.GV_INTERRUPTED], None)},
          "land_swing_on_body: a hostile's swing on a party body casting RC -- untouched plain, "
          "[59, 12, 0] [35, 12, 0] and the slot cleared when Dazed", f"{shapes}")
    shapes = {}
    for dz in (False, True):
        st = fresh_state()
        casting(10, hostile(st, 10, max_health=1000.0, health=1000.0) and st)
        if dz:
            cond_on(st, DAZED_C, agent=10)
        sent, send = collector()
        res = authsrv.hit_enemy(send, st, 10, 0)
        shapes[dz] = (res, stops(sent, 10), st["agents"][10]["casting"])
    check(shapes[False][0] == shapes[True][0] == "landed"
          and shapes[False][1:] == ([], 0)
          and shapes[True][1:] == ([agents.GV_SKILL_STOPPED, agents.GV_INTERRUPTED], None),
          "hit_enemy: the player's swing on a hostile casting RC -- untouched plain, [59, 10, 0] "
          "[35, 10, 0] when Dazed", f"{shapes}")
    # THE REVIEW'S M7: the player's SPELL word (hit_enemy's exact) on a Dazed casting hostile
    # interrupts nothing -- an attack, not any hit; the swing beside it does.
    shapes = {}
    for swing in (True, False):
        st = fresh_state()
        casting(10, hostile(st, 10, max_health=1000.0, health=1000.0) and st)
        cond_on(st, DAZED_C, agent=10)
        sent, send = collector()
        if swing:
            res = authsrv.hit_enemy(send, st, 10, 0)
        else:
            res = authsrv.hit_enemy(send, st, 10, 0, exact=10.0, swing=False, armed=True,
                                    label="the player's spell")
        shapes[swing] = (res, stops(sent, 10), st["agents"][10]["casting"])
    check(shapes[True] == ("landed", [agents.GV_SKILL_STOPPED, agents.GV_INTERRUPTED], None)
          and shapes[False] == ("landed", [], 0),
          "hit_enemy on a Dazed casting hostile: the player's SWING interrupts, the player's "
          "SPELL word (exact, swing=False) lands and interrupts NOTHING -- the `swing and exact "
          "is None` gate the review's M7 found untested", f"{shapes}")
    # THE REVIEW'S M3: the player's press and ally_cast_tick under Dazed, for real.
    got = {}
    for dz in (False, True):
        got[dz] = press_e5(ORB_J, 10, cond=DAZED_C if dz else None)
    check(got == {False: 1.0, True: 2.0},
          "handle_skill_press: the player's Javelin's E5 clock is 1.0 s plain and 2.0 s Dazed -- "
          "the doubling reaches the real press", f"{got}")
    got = {}
    for dz in (False, True):
        got[dz] = ally_cast(((RC, 0.75, 2.0),), cond=DAZED_C if dz else None)
    check(got[False][:2] == (0.75, PLAYER) and got[True][:2] == (1.5, PLAYER)
          and abs((got[True][2] - got[False][2]) - 0.75) < 1e-6,
          "ally_cast_tick: a party monk's Restore Condition at the hurt player lands at +0.75 "
          "plain and +1.5 Dazed, its recharge anchor moved by the same 0.75", f"{got}")
    st = fresh_state()
    a = hostile(st, 10)
    a.update({"casting": None, "swing_lands_at": time.time() + 0.5, "swinging": True})
    cond_on(st, DAZED_C, agent=10)
    sent, send = collector()
    check(authsrv.dazed_interrupt(send, st, 0, 10, PLAYER) is None and not sent
          and a["swing_lands_at"] is not None
          and authsrv.interrupt_body(send, st, 10, a, 0, DAZED_C, PLAYER, mode="action") == "swing",
          "a SWINGING Dazed body is never touched by mode 'spell' -- and the KNOWN-BAD arm, mode "
          "'action', does stop it (the mode is load-bearing)")
    # ON APPLICATION: Dazed landing stops the spell at once; Bleeding landing does not.
    st = fresh_state()
    hostile(st, 10, (50.0, 0.0))
    cast = pending_spell(st)
    sent, send = collector()
    authsrv.apply_condition(send, st, PLAYER, DAZED_C, 8.0, 12, 0, HAZE, by_agent=10)
    ops = [(op, v[:3]) for op, v, _l in sent]
    # RANGERPRE-S13: Dazed's visual [6, me, 28] rides between the 0x0042 and the 0x00F1
    # (retail 1 of 1, 20260821T152147 :63150 t=595.985 -- test_condwords).
    check(ops[:3] == [(authsrv.GAME_SMSG_EFFECT_APPLY, [PLAYER, DAZED_C, 12]),
                      (INT, [agents.PROP_AURA_ON, PLAYER, 28]), (OP_STATUS, [PLAYER, 0x02])]
          and ops[3:] == [(INT, [8, PLAYER, 0]), (E5, [PLAYER, ORB_J, 0]),
                          (INT, [agents.GV_SKILL_STOPPED, PLAYER, 0]),
                          (E2, [PLAYER, ORB_J, 0]), (INT, [agents.GV_INTERRUPTED, PLAYER, 0])]
          and cast["e5_sent"],
          "apply_condition: Dazed on the casting player -- 0x0042 [me, 485, 12], [6, me, 28], "
          "0x00F1 0x02, THEN the victim run (the page's bug note: interrupts upon application)",
          f"{ops}")
    st = fresh_state()
    hostile(st, 10, (50.0, 0.0))
    cast = pending_spell(st)
    sent, send = collector()
    authsrv.apply_condition(send, st, PLAYER, BLEED, 8.0, 12, 0, 382, by_agent=10)
    check(not stops(sent, PLAYER) and not cast["e5_sent"],
          "CONTROL: Bleeding on the casting player stops nothing")
    st = fresh_state()
    hostile(st, 10, (50.0, 0.0))
    sent, send = collector()
    authsrv.apply_condition(send, st, PLAYER, DAZED_C, 8.0, 12, 0, HAZE, by_agent=10)
    check(not stops(sent, PLAYER) and len(sent) == 3,
          "CONTROL: Dazed on a player casting nothing is the three-message batch alone "
          "(0x0042, [6, me, 28], 0x00F1 -- RANGERPRE-S13's [6])")
    st = fresh_state()
    casting(10, hostile(st, 10) and st)
    sent, send = collector()
    authsrv.apply_condition(send, st, 10, DAZED_C, 8.0, 12, 0, HAZE, by_agent=PLAYER)
    check(stops(sent, 10) == [agents.GV_SKILL_STOPPED, agents.GV_INTERRUPTED]
          and st["agents"][10]["casting"] is None,
          "Dazed landing on a casting hostile: its status word, then [59, 10, 0] [35, 10, 0]")
    # THE REAL INFLICTER: a hostile's Beguiling Haze at the casting player through land_skill.
    st = world(1, bar=((HAZE, 0.25, 20.0),))
    a = st["agents"][10]
    a.update({"casting": 0, "cast_lands_at": time.time() - 0.01, "cast_target": PLAYER})
    cast = pending_spell(st)
    sent, send = collector()
    authsrv.land_skill(send, st, 10, a, 0)
    ops = [(op, v[:3]) for op, v, _l in sent]
    applies = [v for op, v, _l in sent if op == authsrv.GAME_SMSG_EFFECT_APPLY]
    check(ops[0] == (INT, [agents.GV_SKILL_FINISHED, 10, 0])
          and applies and applies[0][:2] == [PLAYER, DAZED_C] and applies[0][4] == authsrv._f32(8.0)
          and stops(sent, PLAYER) == [agents.GV_SKILL_STOPPED, agents.GV_INTERRUPTED]
          and authsrv.is_dazed(st, PLAYER) and cast["e5_sent"],
          "through the real land_skill: [58, 10, 0], 0x0042 [me, 485, r, buff, 8.0], the word, "
          "then the player's Javelin in activation takes the victim run -- Dazed for 8 s "
          "(its next spells x2)", f"{ops}")
    # THE KNOWN-BAD ARM: the flag off -- the icon and the bit alone.
    authsrv.DAZED = False
    st = fresh_state()
    hostile(st, 10, (50.0, 0.0))
    cast = pending_spell(st)
    cond_on(st, DAZED_C)
    sent, send = collector()
    res = authsrv.dazed_interrupt(send, st, 0, PLAYER, 10)
    off = authsrv.dazed_activation(st, PLAYER, ORB_J, 2.0)
    authsrv.apply_condition(send, st, PLAYER, DAZED_C, 9.0, 12, 0, HAZE, by_agent=10)
    check(res is None and off == 2.0 and not stops(sent, PLAYER) and not cast["e5_sent"]
          and authsrv.is_dazed(st, PLAYER),
          "--no-dazed: the condition is up, the spell keeps its 2.0 and nothing interrupts it "
          "(the reading every run before 2026-09-27 made)")
    authsrv.DAZED = True
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    i_press = _idx(src, "def handle_skill_press(")
    i_eat, i_act = _idx(src, "def enemy_attack_tick("), _idx(src, "def ally_cast_tick(")
    i_ip, i_ib = _idx(src, "def interrupt_player("), _idx(src, "def interrupt_body(")
    i_da = _idx(src, "def dazed_activation(")
    check(_lock(src.count("activation = dazed_activation(state, agent_id, skill_id, activation)") == 2
          and src.count("activation = dazed_activation(state, PLAYER_AGENT_ID, skill_id, activation)") == 1
          and _idx(src, "activation = signet_activation(state, PLAYER_AGENT_ID, skill_id, activation)", i_press)
          < _idx(src, "activation = dazed_activation(state, PLAYER_AGENT_ID, skill_id, activation)", i_press)
          < _idx(src, "e5_at = begin + activation", i_press)
          and i_eat < _idx(src, "activation = dazed_activation(state, agent_id, skill_id, activation)")
          < i_act < _ridx(src, "activation = dazed_activation(state, agent_id, skill_id, activation)")
          and src.count("mode == INTERRUPT_MODE_SPELL") == 2
          and i_ip < _idx(src, "mode == INTERRUPT_MODE_SPELL") < i_ib
          < _ridx(src, "mode == INTERRUPT_MODE_SPELL")
          and src.count("mode == INTERRUPT_MODE_SKILL") == 2
          and src.count('mode in ("action", "attacking")') == 2
          and src.count("dazed_interrupt(send, state, conn_id, ") == 5    # four sites + the def
          and "GV_CASTTIME" not in src[i_da:_idx(src, "def _hex_damage_slot(")]
          and _idx(src, "push_regen(send, state, target_id, conn_id)", _idx(src, "def apply_condition("))
          < _idx(src, "if condition_id == DAZED_ID:", _idx(src, "def apply_condition("))
          and "DAZED = False" in src[_idx(src, "    if a.no_dazed:", _idx(src, "\ndef main():")):
                                     _idx(src, "    if a.no_dazed:", _idx(src, "\ndef main():")) + 160]),
          "the source: the three activation sites behind signet_activation (the press between it "
          "and the E5 clock; enemy_attack_tick; ally_cast_tick); mode 'spell' in both cast "
          "branches and in neither swing gate (B2's two locks intact); four dazed_interrupt sites "
          "(land_swing, hit_enemy, land_swing_on_body, apply_condition behind its push_regen; 5 "
          "with the def); "
          "property 61 is not sent from dazed_activation itself (cast_time_word sends it at the "
          "announce, section 41); main() flips DAZED = False under --no-dazed (M10)")
finally:
    (authsrv.DAZED, authsrv.INTERRUPTS, authsrv.ENERGY, authsrv.NPC_FOLLOW, authsrv.BLIND,
     authsrv.ARMOUR_TERM) = saved


# ---- 41. THE CAST-TIME WORD (2026-09-27, the D6 client run 20260927T181940) -----------------------
# A Dazed player's 4.00 s cast drew the client's own 2 s bar: nothing told the client. Retail's
# shape, OBSERVED 3 of 3 on 20260917T224104 :62557: 0x00A3 [61 GV_CASTTIME, caster, target, seconds]
# immediately ahead of the cast's [60] announce whenever the time differs from the record's.
print("\n41. the cast-time word: property 61 ahead of a modified cast's [60]")
_saved41 = (authsrv.skill_cost, authsrv.weapon_satisfies, authsrv.CAST_TIME_WORD)
authsrv.skill_cost = lambda sid: (0, 0)
authsrv.weapon_satisfies = lambda sid: True
try:
    def press_batch(sid, target, cond=None, hexid=None):
        st = fresh_state()
        hostile(st, 10, (50.0, 0.0))
        now = time.time()
        if cond is not None:
            st["effects"].apply(PLAYER, cond, 12, 30.0, now, type_code=8)
        if hexid is not None:
            st["effects"].apply(PLAYER, hexid, 12, 30.0, now, type_code=4, caster=10)
        sent, send = collector()
        authsrv.handle_skill_press([0, sid, 0, target], send, st, 0, authsrv.GAME_CMSG_USE_SKILL)
        return [(op, v) for op, v, _l in sent]

    def f32(bits):
        return struct.unpack("<f", struct.pack("<I", int(bits) & 0xFFFFFFFF))[0]

    def word61(batch):
        return [(op, v[:-1] + [round(f32(v[-1]), 3)]) for op, v in batch
                if op in (0x00A3, 0x00A2) and v and v[0] == agents.GV_CASTTIME]

    def i60(batch):
        return next((i for i, (op, v) in enumerate(batch)
                     if op in (0x00A0, 0x009F) and v and v[0] == agents.GV_SKILL_ACTIVATED), None)

    dazed = press_batch(ORB_J, 10, cond=DAZED_C)
    plain = press_batch(ORB_J, 10)
    rusted = press_batch(HEAL_SIG, 0, hexid=RUST)
    power = press_batch(POWER, 10, cond=DAZED_C)
    authsrv.CAST_TIME_WORD = False
    reverted = press_batch(ORB_J, 10, cond=DAZED_C)
    authsrv.CAST_TIME_WORD = True
    i61 = next((i for i, (op, v) in enumerate(dazed) if op == 0x00A3 and v and v[0] == agents.GV_CASTTIME), None)
    check(word61(dazed) == [(0x00A3, [agents.GV_CASTTIME, PLAYER, 10, 2.0])]
          and i61 is not None and i60(dazed) is not None and i61 + 1 == i60(dazed)
          and word61(plain) == [] and word61(reverted) == []
          and word61(rusted) == [(0x00A2, [agents.GV_CASTTIME, PLAYER, 4.0])]
          and word61(power) == [],
          "a Dazed player's Lightning Javelin (record 1.0 s): 0x00A3 [61, me, 10, 2.0] IMMEDIATELY ahead "
          "of the [60] (retail's order, 3/3); undazed -- nothing (the record's time needs no word); "
          "--no-cast-time-word -- nothing (the known-bad arm: the client draws a 1 s bar over a 2 s "
          "cast); a Rusted Healing Signet (self, untargeted) rides 0x00A2 [61, me, 4.0] "
          "(RECONSTRUCTION, the channel-follows-target rule); an ATTACK skill (Power Attack) under "
          "Dazed sends none -- its time is the weapon's, and Dazed is spells-only",
          (word61(dazed), word61(plain), word61(rusted), word61(power), word61(reverted)))
    # the body site: a Dazed hostile casting a spell at the player
    st = fresh_state()
    hostile(st, 10, (80.0, 0.0), skills=[[ORB_J, 1.0, 5.0]], skill_ready=[0.0], npc={"profession": 6},
            cast_range=1200.0, target=PLAYER, target_locked=True)
    st["effects"].apply(10, DAZED_C, 12, 30.0, time.time(), type_code=8)
    sent, send = collector()
    authsrv.enemy_attack_tick(send, st, 1)
    body = [(op, v) for op, v, _l in sent]
    j61 = next((i for i, (op, v) in enumerate(body) if op == 0x00A3 and v and v[0] == agents.GV_CASTTIME), None)
    j60 = next((i for i, (op, v) in enumerate(body) if op in (0x00A0, 0x009F) and v
                and v[0] == agents.GV_SKILL_ACTIVATED and v[1] == 10), None)
    check(j61 is not None and j60 is not None and j61 + 1 == j60
          and body[j61][1][:3] == [agents.GV_CASTTIME, 10, PLAYER]
          and round(f32(body[j61][1][3]), 3) == 2.0,
          "a Dazed HOSTILE's Lightning Javelin at the player: [61, it, me, 2.0] immediately ahead of its "
          "[60] -- retail's own shape (a body casting at the observer, 3 of 3)",
          [(hex(op), v) for op, v in body][:8])
    src = open(authsrv.__file__, encoding="utf-8").read()
    check(src.count("cast_time_word(send, ") == 5                  # four sites + the def
          and "CAST_TIME_WORD = False" in src[_idx(src, "    if a.no_cast_time_word:"):
                                              _idx(src, "    if a.no_cast_time_word:") + 120],
          "the source: four announce sites (the press, the queued begin, the hostile, the hero) and "
          "main() flips CAST_TIME_WORD = False under --no-cast-time-word")
finally:
    authsrv.skill_cost, authsrv.weapon_satisfies, authsrv.CAST_TIME_WORD = _saved41

sys.exit(LEDGER.verdict())
