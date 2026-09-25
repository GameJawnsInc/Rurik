"""SKILLS-LU: the first per-skill residue consumers, on synthetic rows.

studies/skills/FINDINGS.md 59 (DESKWORK-D4's residue, 2026-09-23). The step-4
gate (skills 55.2) EXCLUDED three classes of plain SERVED rows because no
consumer acted where retail acts; this file drives the three consumers that
now do, each through the REAL cast path (handle_skill_press -> cast_tick for
the player, land_skill for a body, resolve_heal for a heal), on SYNTHETIC
skills + skill_effect rows installed under saved copies:

  (A) the CASTER-centred area   -- caster_area / burst_player_caster_area /
                                   body_caster_area_condition; --no-caster-areas
  (B) the caster-centred PARTY HEAL -- party_heal_radius / party_within in
                                   resolve_heal; --no-party-heals
  (C) the NON-attack CHAIN GATE  -- the E5 judges combo_req for any type and
                                   974's `combo` advances; --no-nonattack-chain-gate

Every consumer has a known-bad arm (its flag off, or the pre-arm shape forced)
that must LOOK different on the wire, and a vacuity guard (a geometry that
reaches nobody). Section 5 reads the LOADED label overlay -- the vault's, or
RURIK_CONTENT_EXTRA's -- and checks each row's mark against the server's own
predicate, the way test_skilldamage 14 checks AREA_BURST against spell_burst;
it declares a skip on an overlay with none of the three marks (the vault
before the SKILLS-LU regeneration). The fix pass (skills 59.7) added: a BODY's
cast of a chain-gated row lands on NOBODY (the reviewers' blocker: a hero put
784's Poison on its target with no lead), --no-nonattack-chain-gate is the
gate's EXCLUSION (NOBODY) rather than the ungated landing, a hostile's party
is its spawn GROUP, the player's caster area knocks down as the body's does,
a failed step skips a heal and an effect ON THE WIRE, and 5b reads the HAND
rows through the same predicates (a hand row a consumer would silently
re-route is named).

NOT bare-capable in section 5b only; sections 1-5a need no vault.
"""
import contextlib
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks  # noqa: E402
import agents  # noqa: E402
import authsrv  # noqa: E402
import effects  # noqa: E402

# FLOOR 30, from the green run of 2026-09-23 (SKILLS-LU): 8 (A, player) + 6 (A,
# body) + 7 (B) + 8 (C) + 1 (the flags) -- section 5b declares a skip without a
# regenerated overlay and adds 3 with one (33 under RURIK_CONTENT_EXTRA).
# The fix pass of the same day (skills 59.7): +10 -> FLOOR 40 from the bare run (the
# knock-down arm, the hostile group, the flag's NOBODY arm, the heal and stance guards,
# a hero's and a hostile's chain-gated casts + the flag on the body path + the positive
# control, 5a's two hand-row sweeps; 1643's record is a declared skip on a bare machine);
# 41 with the vault's skills table, 44 with the marks loaded.
# SKILLS-LV (2026-09-25, skills 60): +26 -> FLOOR 66 from the bare run (RURIK_VAULT at an
# empty dir: 66 + 3 skips) -- section 6 the on-hit rider (the class readers, the player's
# sword / wand / bow swings, the flag, a spell's null, a hero's sword and staff, a
# hostile's axe at the player, the source lock), section 7 the single-target knock-down
# (231's, 784's, 294's shapes for the player and a hostile, the flag, the term being the
# tier's only, the source lock), section 8 the flat constant (the reader, the flag, the
# wire, the hand-row census), section 5's three flags; 70 + 1 skip with the vault's
# 57-row overlay, 73 with the 60-row emit loaded (5c's marks).
# The fix pass of the same day (skills 60.8): +4 -> FLOOR 70 from the bare run (70 + 3
# skips) -- 1041's shape through the widened caster arm (the predicate and the E5 burst,
# bare-capable), a killing blow carrying no rider, and the rider's SIDE (the player's
# 1997-shape at a FOE arms nothing); 74 + 1 skip with the vault's 57-row overlay, 77 with
# the 60-row emit.
LEDGER = checks.Ledger("label consumers", floor=70)
check = LEDGER.ok

PLAYER = authsrv.PLAYER_AGENT_ID
FOE, FOE2, FAR = 10, 11, 12          # hostiles: adjacent, adjacent, 400 u off
HERO, HERO2 = 200, 201               # party bodies: 110 u off, 6000 u off
POISON = effects.CONDITION_BY_NAME["Poison"]
CRIPPLED = effects.CONDITION_BY_NAME["Crippled"]
BLIND = effects.CONDITION_BY_NAME["Blind"]

# ---- synthetic rows: the shapes of 183 / 840 / 287 / 784 / 974 / a plain self heal,
# and (the fix pass) 1033's damage shape, a chained self heal, a chained stance
S_FIRE, S_POISON, S_PARTY, S_CHAIN, S_STEP, S_SELF = 900001, 900002, 900003, 900004, 900005, 900006
S_CHAINDMG, S_CHAINHEAL, S_CHAINSTANCE = 900007, 900008, 900009
# SKILLS-LV (2026-09-25, skills 60): 435's and 1997's rider shapes, 231's / 784's /
# 294's knock-down shapes, a HAND-shaped knock-down row, 167's and 1033's slot shapes;
# the fix pass (skills 60.8): 1041's shape, a byte-0 Stance over 156 u with a Blind slot
S_PREP, S_ENCH, S_TOUCH, S_KDCOND, S_SIGNET, S_HANDKD, S_FLAT, S_INDET, S_STANCEAREA = (
    900010, 900011, 900012, 900013, 900014, 900015, 900016, 900017, 900018)


def _skill(target, tc=5, aoe=0.0, s=(30, 30), args=2, d=(0, 0), combo=0, combo_req=0):
    return {"type_code": tc, "target": target, "aoe_range": aoe, "projectile": 2077,
            "impact_visual": 2077, "combo": combo, "combo_req": combo_req, "weapon_req": 0,
            "skill_arguments": args, "scale0": s[0], "scale15": s[1],
            "bonus_scale0": 0, "bonus_scale15": 0, "duration0": d[0], "duration15": d[1],
            "attribute": 10, "profession": 6, "activation": 1.0, "aftercast": 0.75,
            "recharge": 5, "energy": 5, "adrenaline": 0, "adrenaline_units": 0}


SKILLS = {
    str(S_FIRE): _skill(0, aoe=156.0, s=(30, 30)),                       # 183's shape
    str(S_POISON): _skill(0, aoe=156.0, s=(5, 5), args=3, d=(10, 10)),   # 840's shape
    str(S_PARTY): _skill(0, aoe=5000.0, s=(40, 40)),                     # 287's shape
    str(S_CHAIN): _skill(5, s=(5, 5), combo_req=2),                      # 784's: must follow a lead
    str(S_STEP): _skill(5, tc=10, s=(5, 5), combo=2),                    # 974's: counts as an off-hand
    str(S_SELF): _skill(0, aoe=0.0, s=(40, 40)),                         # a plain self heal (control)
    str(S_CHAINDMG): _skill(5, tc=10, s=(25, 25), combo_req=1),          # 1033's: a dual, earth damage
    str(S_CHAINHEAL): _skill(0, aoe=0.0, s=(40, 40), combo_req=2),       # a self heal that must follow a lead
    str(S_CHAINSTANCE): _skill(0, tc=3, s=(0, 0), d=(5, 5), combo_req=2),  # a stance that must follow a lead
    str(S_PREP): dict(_skill(0, tc=19, s=(0, 0), args=4, d=(24, 24)), bonus_scale0=3, bonus_scale15=15),  # 435
    str(S_ENCH): _skill(3, tc=6, s=(5, 20), args=3, d=(5, 20)),           # 1997's shape
    str(S_TOUCH): _skill(5, tc=10, s=(10, 60)),                           # 231's shape
    str(S_KDCOND): _skill(5, s=(5, 5)),                                   # 784's shape, unchained
    str(S_SIGNET): _skill(5, tc=7, aoe=156.0, s=(15, 75)),                # 294's shape
    str(S_HANDKD): _skill(5, tc=10, s=(10, 60)),                          # a HAND row's shape
    str(S_FLAT): dict(_skill(5, s=(10, 40)), bonus_scale0=10, bonus_scale15=10),   # 167's shape
    str(S_INDET): dict(_skill(5, s=(10, 40)), bonus_scale0=5, bonus_scale15=20),   # 1033's slot shape
    str(S_STANCEAREA): dict(_skill(0, tc=3, aoe=156.0, s=(0, 0), args=5, d=(10, 30)),
                            bonus_scale0=5, bonus_scale15=20),                      # 1041's shape
}
EFFECTS = {
    str(S_FIRE): {"scale_means": "Fire damage", "tier": "label", "tier_detail": ["AREA_CASTER"]},
    str(S_POISON): {"scale_means": "Poison", "tier": "label", "tier_detail": ["AREA_CASTER"]},
    str(S_PARTY): {"scale_means": "Heal", "tier": "label", "tier_detail": ["HEAL_PARTY"]},
    str(S_CHAIN): {"scale_means": "Poison", "tier": "label", "tier_detail": ["CHAIN_GATED"]},
    str(S_STEP): {"scale_means": "Crippled", "tier": "label", "tier_detail": ["CHAIN_STEP_ADVANCES"]},
    str(S_SELF): {"scale_means": "Heal", "tier": "label", "tier_detail": []},
    str(S_CHAINDMG): {"scale_means": "Earth damage", "tier": "label", "tier_detail": ["CHAIN_GATED"]},
    str(S_CHAINHEAL): {"scale_means": "Heal", "tier": "label", "tier_detail": ["CHAIN_GATED"]},
    str(S_PREP): {"bonus_scale_means": "Poison", "condition_rider": "on_hit", "rider_weapon": "physical",
                  "tier": "label", "tier_detail": ["CONDITION_RIDER_ON_HIT"]},
    str(S_ENCH): {"scale_means": "Weakness", "condition_rider": "on_hit", "rider_weapon": "melee",
                  "tier": "label", "tier_detail": ["TARGET_ALLY", "CONDITION_RIDER_ON_HIT"]},
    str(S_TOUCH): {"scale_means": "Lightning damage", "knocks_down": True, "tier": "label",
                   "tier_detail": ["TOUCH", "AREA_ONE_TARGET", "KNOCKDOWN_APPLIED"]},
    str(S_KDCOND): {"scale_means": "Poison", "knocks_down": True, "tier": "label",
                    "tier_detail": ["TARGET_FOE", "KNOCKDOWN_APPLIED"]},
    str(S_SIGNET): {"scale_means": "Holy damage", "knocks_down": True, "tier": "label",
                    "tier_detail": ["ALL_FOES", "AREA_ADJACENT", "TARGET_FOE", "AREA_ONE_TARGET", "KNOCKDOWN_APPLIED"]},
    str(S_HANDKD): {"scale_means": "Lightning damage", "knocks_down": True},     # no tier: a hand row
    str(S_FLAT): {"scale_means": "Earth damage", "bonus_scale_means": "Blind", "tier": "label",
                  "tier_detail": ["CONDITION_FLAT_CONSTANT"]},
    str(S_INDET): {"scale_means": "Earth damage", "bonus_scale_means": "Deep Wound", "tier": "label",
                   "tier_detail": ["INDETERMINATE_SLOT", "CONDITION_BIT_CLEAR_REFUSED"]},
    str(S_STANCEAREA): {"bonus_scale_means": "Blind", "tier": "label",
                        "tier_detail": ["AREA_CASTER", "CLAUSE_UNBLOCKABLE"]},
}


def _hostile(pos, name="suit"):
    return {"name": name, "dead": False, "died_at": 0.0, "health": 9000.0, "max_health": 9000.0,
            "last_hit": 0.0, "pos": pos, "plane": 0, "armor_rating": 60.0,
            "allegiance": agents.ALLEGIANCE_HOSTILE, "attack_speed": 1.75, "effects": 0,
            "attacks_back": False, "skills": (), "skill_ready": [],
            "npc": {"profession": 6, "level": 20}}


def _party(pos, name="monk"):
    return {"name": name, "dead": False, "died_at": 0.0, "health": 100.0, "max_health": 300.0,
            "last_hit": 0.0, "pos": pos, "plane": 0, "allegiance": agents.ALLEGIANCE_PLAYER,
            "effects": 0, "attack_speed": 1.75, "attacks_back": False, "skills": (),
            "skill_ready": [], "npc": {"profession": 3, "level": 20}, "party_slot": 0,
            "weapon_item": "caster_staff"}


def _world():
    return {"agents": {FOE: _hostile((100.0, 0.0)), FOE2: _hostile((0.0, 140.0), "second"),
                       FAR: _hostile((400.0, 0.0), "far"),
                       HERO: _party((0.0, 110.0)), HERO2: _party((6000.0, 0.0), "far monk")},
            "pos": (0.0, 0.0), "player_health": 50.0, "player_dead": False, "level": 20}


def _sender():
    sent = []
    return sent, (lambda op, vals, label="", quiet=False: sent.append((op, list(vals))))


def _words(batch):
    return [(v[1], v[0]) for op, v in batch if op == 0x00A3 and v[0] in (16, 17)]


def _conditioned(state, aid, cond):
    return any(ep["skill"] == cond for ep in authsrv.effect_table(state).on_agent(aid))


def _press_and_land(st, send, sid, target):
    """One press through the real handler, then the E5 through the real tick."""
    authsrv.handle_skill_press([0, sid, 0, target], send, st, 1, authsrv.GAME_CMSG_USE_SKILL)
    for cast in st["pending_casts"]:
        for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
            cast[k] -= 30.0
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        authsrv.cast_tick(send, st, 1)
    return buf.getvalue()


def main():
    tables = agents.WORLD.tables
    saved_tables = {k: dict(tables.get(k, {})) for k in ("skills", "skill_effect")}
    saved = (authsrv.skill_timing, authsrv.skill_cost, authsrv.weapon_satisfies,
             authsrv.CASTER_AREAS, authsrv.PARTY_HEALS, authsrv.NONATTACK_CHAIN_GATE,
             agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND)
    saved_lv = (authsrv.CONDITION_RIDERS, authsrv.LABEL_KNOCKDOWNS, authsrv.CONDITION_FLAT_CONSTANTS)
    tables.setdefault("skills", {}).update(SKILLS)
    tables.setdefault("skill_effect", {}).update(EFFECTS)
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 0.0)
    authsrv.skill_cost = lambda sid: (0, 0)
    authsrv.weapon_satisfies = lambda sid: True
    authsrv.apply_party_character({"player_weapon": "starter_wand"})
    try:
        # ------------------------------------------------------------------
        print("1. (A) the CASTER-centred area at the player's E5")
        check(authsrv.caster_area_row(S_FIRE) and authsrv.caster_area(S_FIRE) == 156.0
              and authsrv.caster_area_row(S_POISON) and authsrv.caster_area(S_POISON) == 156.0
              and not authsrv.caster_area_row(S_SELF) and authsrv.caster_area(S_SELF) is None
              and not authsrv.caster_area_row(S_CHAIN) and authsrv.caster_area(S_STEP) is None
              and authsrv.caster_area(187) is None and authsrv.caster_area_row(999999) is False,
              "caster_area_row: byte 0 + a Spell + an aoe_range + no projectile (the fire and the "
              "Poison rows, 156 u); a byte-0 heal with NO radius, a byte-5 Spell, a Skill and an "
              "unknown id are not; a byte-16 burst (187) is spell_burst's, not this")
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_FIRE, FAR)      # the SELECTED target is 400 u off
        w = _words(sent)
        check([a for a, _p in w] == [FOE, FOE2] and st["agents"][FOE]["health"] == 9000.0 - 30.0
              and st["agents"][FOE2]["health"] == 9000.0 - 30.0 and st["agents"][FAR]["health"] == 9000.0
              and st["agents"][HERO]["health"] == 100.0,
              "the player's byte-0 fire Spell at the E5: a word on EACH hostile within 156 u of the "
              "PLAYER (100 u and 140 u), 30 each -- and NOTHING on the selected target 400 u off, "
              "nor on the party body 110 u off (an ally, not a foe)", (w, log[-300:]))
        check("bursts over 2 foe(s) within 156 u of the CASTER (2 landed) [SKILLS-LU]" in log
              and "resolves through a LABEL-tier row (AREA_CASTER)" in log,
              "the log names the caster-centred burst and the label tier", log[-400:])
        # the fix pass (ENG-D4C-5): the row's knock-down rides the player's burst as it
        # rides the body's (burst_body_spell) -- latent (no AREA_CASTER label row knocks
        # down), pinned so the two arms cannot drift apart
        tables["skill_effect"][str(S_FIRE)]["knocks_down"] = True
        st, (sent, send) = _world(), _sender()
        _press_and_land(st, send, S_FIRE, FAR)
        del tables["skill_effect"][str(S_FIRE)]["knocks_down"]
        kds = [v for op, v in sent if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT and v[0] == 63]
        check([k[1] for k in kds] == [FOE, FOE2] and all(k[2] > 0 for k in kds)
              and st["agents"][FOE].get("knocked_until", 0) > time.time()
              and not st["agents"][FAR].get("knocked_until"),
              "a caster-area row carrying `knocks_down` knocks down EACH landed, living foe inside "
              "([63, foe, s] x2, the burst_player_spell shape) and not the far selected one", kds)
        st, (sent, send) = _world(), _sender()
        st["pos"] = (5000.0, 5000.0)                       # the caster far from everyone
        log = _press_and_land(st, send, S_FIRE, FOE)
        check(_words(sent) == [] and st["agents"][FOE]["health"] == 9000.0
              and "bursts over 0 foe(s)" in log,
              "VACUITY GUARD: the caster 7 km from every hostile reaches nobody -- no word, the "
              "selected target untouched (the centre is the CASTER, not the selection)", log[-200:])
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_POISON, FAR)
        check(_conditioned(st, FOE, POISON) and _conditioned(st, FOE2, POISON)
              and not _conditioned(st, FAR, POISON) and not _conditioned(st, HERO, POISON)
              and _words(sent) == [] and "condition on each" in log,
              "a condition-only byte-0 Spell (840's shape): Poison on both adjacent hostiles, no "
              "damage word, nothing on the far selected target or the ally")
        # KNOWN-BAD ARM: the flag off -- NOBODY, never the one-target path
        authsrv.CASTER_AREAS = False
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_FIRE, FOE)
        st2, (sent2, send2) = _world(), _sender()
        log2 = _press_and_land(st2, send2, S_POISON, FOE)
        authsrv.CASTER_AREAS = True
        check(_words(sent) == [] and st["agents"][FOE]["health"] == 9000.0
              and st["agents"][FOE2]["health"] == 9000.0 and "lands on NOBODY" in log
              and not _conditioned(st2, FOE, POISON) and not _conditioned(st2, FOE2, POISON)
              and "lands on NOBODY" in log2,
              "KNOWN-BAD ARM --no-caster-areas: the same presses land on NOBODY -- not on the "
              "selected adjacent target either, because the one-target path is the "
              "over-application the gate refused; the log says so", (log[-200:], log2[-200:]))
        st, (sent, send) = _world(), _sender()
        _press_and_land(st, send, S_SELF, FOE)
        check(_words(sent) == [] and st["agents"][FOE]["health"] == 9000.0,
              "CONTROL: a byte-0 row with NO radius takes no area arm (a self heal: no word, no hit)")
        # the fix pass (skills 60.8 #5): the caster arm WIDENED to an EPISODE type -- 1041's
        # shape, a byte-0 Stance over 156 u with a Blind bonus slot, marked AREA_CASTER. Before
        # this arm only 5c (the fresh emit) could redden a Spell-only predicate; bare could not.
        check(authsrv.caster_area_row(S_STANCEAREA) and authsrv.caster_area(S_STANCEAREA) == 156.0
              and not authsrv.caster_area_row(S_CHAINSTANCE) and authsrv.caster_area(S_CHAINSTANCE) is None,
              "caster_area_row admits an EPISODE type (a byte-0 Stance with a radius, 1041's shape) "
              "and still refuses a stance with NO radius")
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_STANCEAREA, FAR)     # the SELECTED target is 400 u off
        eps_p = [ep["skill"] for ep in authsrv.effect_table(st).on_agent(PLAYER)]
        ep_b = [e for e in authsrv.effect_table(st).on_agent(FOE) if e["skill"] == BLIND]
        i_blind = log.find("Blind on agent 11")
        i_stance = log.find(f"stance {S_STANCEAREA} on agent")
        check(_conditioned(st, FOE, BLIND) and _conditioned(st, FOE2, BLIND) and ep_b and ep_b[0]["duration"] == 5.0
              and not _conditioned(st, FAR, BLIND) and not _conditioned(st, HERO, BLIND)
              and eps_p == [S_STANCEAREA] and _words(sent) == []
              and 0 <= i_blind < i_stance,
              "1041's shape at the player's E5: Blind 5 s (the bonus slot at rank 0) on BOTH hostiles "
              "within 156 u of the PLAYER and on neither the far selected one nor the ally, no damage "
              "word, then the STANCE opens on the player -- the Blind ahead of the stance in the log",
              (eps_p, ep_b, i_blind, i_stance, log[-400:]))
        src = open(authsrv.__file__, encoding="utf-8").read()
        i_gate = src.index("_carea_row = caster_area_row(cast[\"skill_id\"]) and not _na_fail")
        i_att = src.index("elif target and _is_attack_skill(cast[\"skill_id\"]):", i_gate)
        i_std = src.index('elif target and found and found[1] == "standalone":', i_att)
        check(i_gate < i_att < i_std
              and src.count("                    burst_player_caster_area(send, state, conn_id, cast, found,") == 1,
              "SOURCE: the E5 branches to the caster arm FIRST, then the attack branch, then the "
              "one-target standalone branch -- the caster arm never falls through to either")

        # ------------------------------------------------------------------
        print("\n2. (A) the CASTER-centred area at a BODY's completion")

        def body_world(sid, caster_pos=(100.0, 0.0)):
            st = _world()
            st["player_health"] = 480.0          # a pool the burst cannot empty
            foe = st["agents"][FOE]
            foe.update({"pos": caster_pos, "skills": [[sid, 1.0, 5.0]], "skill_ready": [0.0],
                        "casting": 0, "cast_target": PLAYER})
            return st
        st, (sent, send) = body_world(S_FIRE), _sender()
        health, monk = st["player_health"], st["agents"][HERO]["health"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        log = buf.getvalue()
        w = _words(sent)
        ar = authsrv.spell_armour_for(S_FIRE)
        want = authsrv._whole_points(30.0 * authsrv.strike_multiplier(
            authsrv.agent_strike_level(st["agents"][FOE]), ar)) if ar is not None else 30.0
        check(sent[0][1][:2] == [58, FOE] and [a for a, _p in w] == [PLAYER, HERO]
              and st["player_health"] == health - want and st["agents"][HERO]["health"] < monk
              and st["agents"][HERO2]["health"] == 100.0 and st["agents"][FOE]["casting"] is None,
              "a hostile's byte-0 fire Spell completes: [58, it, 0], then a word on the PLAYER (100 u "
              "off, its armour term) and on the monk (at 110 u from the caster, 149 u away); the "
              "monk 6 km off untouched; the caster released", (w, log[-300:]))
        check("bursts over 2 foe(s)" in log and "resolves through a LABEL-tier row (AREA_CASTER)" in log,
              "the body's log names the burst and the tier", log[-400:])
        st, (sent, send) = body_world(S_FIRE, caster_pos=(3000.0, 0.0)), _sender()
        health = st["player_health"]
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        check(_words(sent) == [] and st["player_health"] == health
              and st["agents"][HERO]["health"] == 100.0,
              "VACUITY GUARD: the hostile casting from 3 km away reaches nobody -- its cast_target "
              "(the player) takes NO word at any range")
        st, (sent, send) = body_world(S_POISON), _sender()
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        check(_conditioned(st, PLAYER, POISON) and _conditioned(st, HERO, POISON)
              and not _conditioned(st, HERO2, POISON) and _words(sent) == [],
              "a hostile's condition-only byte-0 Spell: Poison on the player and the monk within 156 u "
              "of the caster, no damage word, the far monk clean")
        authsrv.CASTER_AREAS = False
        st, (sent, send) = body_world(S_FIRE), _sender()
        health = st["player_health"]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            authsrv.land_skill(send, st, FOE, st["agents"][FOE], 1)
        st2, (sent2, send2) = body_world(S_POISON), _sender()
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.land_skill(send2, st2, FOE, st2["agents"][FOE], 1)
        authsrv.CASTER_AREAS = True
        check(_words(sent) == [] and st["player_health"] == health and "lands on NOBODY" in buf.getvalue()
              and not _conditioned(st2, PLAYER, POISON) and st["agents"][FOE]["casting"] is None,
              "KNOWN-BAD ARM --no-caster-areas on the body path: no word on the player (its "
              "cast_target, 100 u off), no Poison; the caster is still released", buf.getvalue()[-200:])
        check('elif damage is not None and _spell_how is None and _carea is not None' in src
              and "if inflicted and _carea_row and _burst_terms is None:" in src
              and src.count("            body_caster_area_condition(send, state, conn_id, agent_id, skill_id,") == 1,
              "SOURCE: the body's terms take the caster centre before the one-target branch, and the "
              "condition-only arm sits ahead of the one-target condition")

        # ------------------------------------------------------------------
        print("\n3. (B) the CASTER-centred party heal in resolve_heal")
        check(authsrv.party_heal_radius(S_PARTY) == 5000.0 and authsrv.party_heal_radius(S_SELF) is None
              and authsrv.party_heal_radius(S_FIRE) is None and authsrv.party_heal_radius(999999) is None
              and authsrv.party_heal_radius(1) is None,
              "party_heal_radius: byte 0 + a Spell + a radius + a Heal means (5000 u); a self heal "
              "with no radius, a damage row, an unknown id and Healing Signet (the hand row, byte 0, "
              "no radius) are None")
        st = _world()
        st["agents"][HERO]["health"] = 100.0
        st["agents"][HERO2]["health"] = 100.0
        check(authsrv.party_within(st, PLAYER, 5000.0) == [PLAYER, HERO]
              and authsrv.party_within(st, HERO, 5000.0) == [HERO, PLAYER]
              and authsrv.party_within(st, PLAYER, 50.0) == [PLAYER]
              and authsrv.party_within(st, FOE, 5000.0) == [FOE, FOE2, FAR],
              "party_within: the caster first, then its living allies inside the radius by id -- the "
              "player's party (the monk at 110 u; not the one 6 km off), a hero's (itself, then the "
              "player), a 50 u radius the caster alone, a hostile's WITHOUT a group the other hostiles")
        # the fix pass (LU-R2 / ENG-D4C-6): a hostile's party is its spawn GROUP when it has
        # one -- two groups inside 5000 u must not heal each other (the sandbox spaces
        # groups 2,100 u apart); UNVERIFIED as retail's rule, the narrower reading
        st = _world()
        for aid, g, hp in ((FOE, "a", 500.0), (FOE2, "a", 500.0), (FAR, "b", 500.0)):
            st["agents"][aid]["group"] = g
            st["agents"][aid]["health"] = hp
        st["agents"][HERO]["group"] = "a"                   # a party body's group is NOT read
        sent, send = _sender()
        with contextlib.redirect_stdout(io.StringIO()):
            out = authsrv.resolve_heal(send, st, S_PARTY, 0, FOE, PLAYER, 1)
        check(authsrv.party_within(st, FOE, 5000.0) == [FOE, FOE2]
              and authsrv.party_within(st, FAR, 5000.0) == [FAR]
              and authsrv.party_within(st, HERO, 5000.0) == [HERO, PLAYER]
              and out["recipients"] == [FOE, FOE2] and st["agents"][FOE]["health"] == 540.0
              and st["agents"][FOE2]["health"] == 540.0 and st["agents"][FAR]["health"] == 500.0
              and st["player_health"] == 50.0 and st["agents"][HERO]["health"] == 100.0,
              "a HOSTILE of group 'a' casting the party heal heals itself and its group-mate 140 u off "
              "and NOT the group-'b' hostile 400 u off (inside the radius); group 'b' alone heals "
              "itself alone; a party body's `group` is not read (allegiance is the party marker)",
              (out, {a: st["agents"][a]["health"] for a in (FOE, FOE2, FAR)}))
        st, (sent, send) = _world(), _sender()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            out = authsrv.resolve_heal(send, st, S_PARTY, 0, PLAYER, FOE, 1)
        heals = [v for op, v in sent if op == 0x00A3 and v[0] == agents.GV_HEALTH_GAIN]
        check(out is not None and out["recipients"] == [PLAYER, HERO] and out["healed"] == 80.0
              and st["player_health"] == 90.0 and st["agents"][HERO]["health"] == 140.0
              and st["agents"][HERO2]["health"] == 100.0 and [h[1] for h in heals] == [PLAYER, HERO]
              and "heals 2 party member(s) within 5000 u of the caster for 40 each (80 landed)" in buf.getvalue(),
              "the player's party heal (287's shape, 40 flat): the player (50 -> 90) AND the monk 110 u "
              "off (100 -> 140) each gain 40 and a heal word (property 55), the monk 6 km off nothing; "
              "the log counts them", (out, heals, buf.getvalue()[-200:]))
        st, (sent, send) = _world(), _sender()
        with contextlib.redirect_stdout(io.StringIO()):
            out = authsrv.resolve_heal(send, st, S_PARTY, 0, HERO, PLAYER, 1)
        check(out["recipients"] == [HERO, PLAYER] and st["agents"][HERO]["health"] == 140.0
              and st["player_health"] == 90.0,
              "a HERO casting it heals itself and the player -- the caster is in the class")
        st, (sent, send) = _world(), _sender()
        with contextlib.redirect_stdout(io.StringIO()):
            out = authsrv.resolve_heal(send, st, S_SELF, 0, PLAYER, FOE, 1)
        check(out["recipient"] == PLAYER and "recipients" not in out and st["player_health"] == 90.0
              and st["agents"][HERO]["health"] == 100.0,
              "CONTROL: a byte-0 heal with NO radius heals the caster alone (cast_recipient's path)")
        authsrv.PARTY_HEALS = False
        st, (sent, send) = _world(), _sender()
        with contextlib.redirect_stdout(io.StringIO()):
            out = authsrv.resolve_heal(send, st, S_PARTY, 0, PLAYER, FOE, 1)
        authsrv.PARTY_HEALS = True
        check(out["recipient"] == PLAYER and "recipients" not in out and st["player_health"] == 90.0
              and st["agents"][HERO]["health"] == 100.0,
              "KNOWN-BAD ARM --no-party-heals: the caster alone -- the monk 110 u off gains nothing "
              "(a subset of the right recipients, the pre-2026-09-23 path)")
        st, (sent, send) = _world(), _sender()
        st["pos"] = (20000.0, 0.0)
        with contextlib.redirect_stdout(io.StringIO()):
            out = authsrv.resolve_heal(send, st, S_PARTY, 0, PLAYER, FOE, 1)
        check(out["recipients"] == [PLAYER] and st["agents"][HERO]["health"] == 100.0,
              "VACUITY GUARD: the caster 20 km from its party heals itself alone")

        # ------------------------------------------------------------------
        print("\n4. (C) the NON-attack chain gate at the E5, and the non-attack chain step")
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_CHAIN, FOE)
        fails = [v for op, v in sent if op == 0x00A0 and v[0] == agents.GV_ATTACK_FAIL]
        e5s = [v for op, v in sent if op == authsrv.GAME_SMSG_SKILL_RECHARGE]
        check(fails == [[agents.GV_ATTACK_FAIL, FOE, PLAYER, agents.ATTACK_FAIL_FAIL]]
              and len(e5s) == 2 and e5s[1][3] == 0 and not _conditioned(st, FOE, POISON)
              and "FAILED on agent 10: a non-attack that must follow a lead" in log,
              "a Spell that must follow a LEAD (784's shape) pressed at a target with NO chain state "
              "FAILS at the E5: [38, target, player, 2], a second E5 with recharge 0, no Poison -- the "
              "attack gate's shape (RECONSTRUCTION for a non-attack)", (fails, e5s, log[-300:]))
        st, (sent, send) = _world(), _sender()
        authsrv.player_chain(st).advance(FOE, authsrv.chain.LEAD, time.time())
        log = _press_and_land(st, send, S_CHAIN, FOE)
        fails = [v for op, v in sent if op == 0x00A0 and v[0] == agents.GV_ATTACK_FAIL]
        check(fails == [] and _conditioned(st, FOE, POISON) and "FAILED" not in log,
              "the same press after a LEAD on that target: no fail word, the Poison lands")
        st, (sent, send) = _world(), _sender()
        authsrv.player_chain(st).advance(FOE2, authsrv.chain.LEAD, time.time())
        log = _press_and_land(st, send, S_CHAIN, FOE)
        check(not _conditioned(st, FOE, POISON) and "FAILED" in log,
              "the chain state is PER TARGET: a lead on the other hostile does not satisfy this one")
        # the fix pass (LU-R3): the flag is the gate's EXCLUSION -- NOBODY, no fail word --
        # never the ungated landing (which the exclusion existed to refuse); a lead on the
        # target changes nothing under the flag
        authsrv.NONATTACK_CHAIN_GATE = False
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_CHAIN, FOE)
        st2, (sent2, send2) = _world(), _sender()
        authsrv.player_chain(st2).advance(FOE, authsrv.chain.LEAD, time.time())
        log2 = _press_and_land(st2, send2, S_CHAIN, FOE)
        authsrv.NONATTACK_CHAIN_GATE = True
        fails = [v for op, v in sent + sent2 if op == 0x00A0 and v[0] == agents.GV_ATTACK_FAIL]
        e5s = [v for op, v in sent if op == authsrv.GAME_SMSG_SKILL_RECHARGE]
        check(fails == [] and not _conditioned(st, FOE, POISON) and not _conditioned(st2, FOE, POISON)
              and "lands on NOBODY (the gate's exclusion until 2026-09-23)" in log
              and "lands on NOBODY" in log2 and len(e5s) == 1 and "FAILED" not in log,
              "--no-nonattack-chain-gate: the row lands on NOBODY -- no Poison, no fail word, ONE E5 "
              "(the cast's own, its recharge kept) -- with or without a lead on the target: the "
              "gate's exclusion, the server until 2026-09-23, never the ungated landing", (log[-200:],))
        # the fix pass (ENG-D4C-3): a failed step skips a HEAL and an EFFECT on the wire, not
        # just in a source count -- a self heal and a stance that must follow a lead
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_CHAINHEAL, FOE)
        heals = [v for op, v in sent if op == 0x00A3 and v[0] == agents.GV_HEALTH_GAIN]
        st2, (sent2, send2) = _world(), _sender()
        authsrv.player_chain(st2).advance(FOE, authsrv.chain.LEAD, time.time())
        log2 = _press_and_land(st2, send2, S_CHAINHEAL, FOE)
        heals2 = [v for op, v in sent2 if op == 0x00A3 and v[0] == agents.GV_HEALTH_GAIN]
        check(heals == [] and st["player_health"] == 50.0 and "FAILED on agent 10" in log
              and [h[1] for h in heals2] == [PLAYER] and st2["player_health"] == 90.0 and "FAILED" not in log2,
              "a SELF HEAL that must follow a lead: no lead -> the fail word and NO heal word, the "
              "player stays at 50; after a lead -> one heal word, 50 -> 90 (resolve_heal skipped on "
              "the fail, on the wire)", (heals, heals2, log[-200:]))
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_CHAINSTANCE, FOE)
        eps = [ep["skill"] for ep in authsrv.effect_table(st).on_agent(PLAYER)]
        st2, (sent2, send2) = _world(), _sender()
        authsrv.player_chain(st2).advance(FOE, authsrv.chain.LEAD, time.time())
        log2 = _press_and_land(st2, send2, S_CHAINSTANCE, FOE)
        eps2 = [ep["skill"] for ep in authsrv.effect_table(st2).on_agent(PLAYER)]
        check(S_CHAINSTANCE not in eps and "FAILED on agent 10" in log
              and eps2 == [S_CHAINSTANCE] and "FAILED" not in log2,
              "a STANCE that must follow a lead: no lead -> the fail word and NO episode on the "
              "player; after a lead -> the episode opens (apply_effect skipped on the fail)",
              (eps, eps2, log[-200:]))
        # the fix pass (LU-R1 / ENG-D4C-1, the reviewers' BLOCKER): a BODY's cast of a
        # chain-gated row lands on NOBODY -- a hero at a hostile, a hostile at the player,
        # 784's Poison shape and 1033's damage shape; the cast still closes (58, released)
        st, (sent, send) = _world(), _sender()
        hero = st["agents"][HERO]
        hero.update({"pos": (60.0, 0.0), "skills": [[S_CHAIN, 1.0, 5.0]], "skill_ready": [0.0],
                     "casting": 0, "cast_target": FOE})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            authsrv.land_skill(send, st, HERO, hero, 1)
        log = buf.getvalue()
        fails = [v for op, v in sent if op == 0x00A0 and v[0] == agents.GV_ATTACK_FAIL]
        check(not _conditioned(st, FOE, POISON) and fails == [] and hero["casting"] is None
              and [v[:2] for op, v in sent if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                   and v[0] == 58] == [[58, HERO]]
              and "must follow a lead and a body carries no chain: it lands on NOBODY" in log
              and "retail's bodies meet it" in log,
              "a HERO casting 784's shape at a hostile with no chain: NO Poison, no fail word, the "
              "58 closes its cast and it is released; the log names the unmet requirement and that "
              "retail's bodies DO meet it (5 of 5 live 784s after their own 782)", (fails, log[-300:]))
        st, (sent, send) = _world(), _sender()
        st["player_health"] = 480.0
        foe = st["agents"][FOE]
        foe.update({"skills": [[S_CHAIN, 1.0, 5.0], [S_CHAINDMG, 1.0, 5.0]], "skill_ready": [0.0, 0.0],
                    "casting": 0, "cast_target": PLAYER})
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.land_skill(send, st, FOE, foe, 1)
        foe.update({"casting": 1})
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.land_skill(send, st, FOE, foe, 1)
        check(not _conditioned(st, PLAYER, POISON) and st["player_health"] == 480.0
              and _words(sent) == [] and foe["casting"] is None,
              "a HOSTILE casting 784's and 1033's shapes at the player: no Poison, no damage word, "
              "the player untouched (the over-application the gate's exclusion refused)")
        authsrv.NONATTACK_CHAIN_GATE = False
        st, (sent, send) = _world(), _sender()
        foe = st["agents"][FOE]
        foe.update({"skills": [[S_CHAIN, 1.0, 5.0]], "skill_ready": [0.0], "casting": 0, "cast_target": PLAYER})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            authsrv.land_skill(send, st, FOE, foe, 1)
        authsrv.NONATTACK_CHAIN_GATE = True
        check(not _conditioned(st, PLAYER, POISON) and "--no-nonattack-chain-gate, the gate's exclusion" in buf.getvalue(),
              "and under --no-nonattack-chain-gate the body's cast lands on NOBODY too (the exclusion "
              "covered bodies): the log names the flag")
        # POSITIVE CONTROL for the body arm: a body's NON-gated Poison (840's shape) does land
        # through the same land_skill, so 'no Poison' above is the gate, not a dead path
        st, (sent, send) = _world(), _sender()
        foe = st["agents"][FOE]
        foe.update({"skills": [[S_POISON, 1.0, 5.0]], "skill_ready": [0.0], "casting": 0, "cast_target": PLAYER})
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.land_skill(send, st, FOE, foe, 1)
        check(_conditioned(st, PLAYER, POISON),
              "POSITIVE CONTROL: the same hostile's un-gated byte-0 Poison lands on the player "
              "through land_skill -- the body's 'no Poison' above is the requirement, not a dead path")
        # 974's shape: a Skill that counts as an off-hand attack
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_STEP, FOE)
        combo = [(i, v) for i, (op, v) in enumerate(sent) if op == authsrv.GAME_SMSG_AGENT_COMBO_STATE]
        e5_i = [i for i, (op, v) in enumerate(sent) if op == authsrv.GAME_SMSG_SKILL_RECHARGE]
        e3_i = [i for i, (op, v) in enumerate(sent) if op == authsrv.GAME_SMSG_SKILL_ACTIVATED]
        check(len(combo) == 1 and combo[0][1] == [PLAYER, FOE, authsrv.chain.OFF_HAND]
              and authsrv.player_chain(st).state_on(FOE, time.time()) == authsrv.chain.OFF_HAND
              and _conditioned(st, FOE, CRIPPLED) and e5_i and e3_i and e5_i[0] < combo[0][0] < e3_i[0],
              "a Skill that 'counts as an off-hand attack' (974's shape) lands its Crippled and MOVES "
              "the chain: ONE 0x005C [player, target, off-hand] between the E5 and the E3 (the attack's "
              "order), and the target's state reads off-hand", (combo, e5_i, e3_i))
        st, (sent, send) = _world(), _sender()
        st["agents"][FOE]["dead"] = True
        log = _press_and_land(st, send, S_STEP, FOE)
        check(not [v for op, v in sent if op == authsrv.GAME_SMSG_AGENT_COMBO_STATE]
              and authsrv.player_chain(st).state_on(FOE, time.time()) == 0,
              "VACUITY GUARD: on a DEAD target the chain step neither lands nor moves")
        authsrv.NONATTACK_CHAIN_GATE = False
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_STEP, FOE)
        authsrv.NONATTACK_CHAIN_GATE = True
        check(not [v for op, v in sent if op == authsrv.GAME_SMSG_AGENT_COMBO_STATE]
              and authsrv.player_chain(st).state_on(FOE, time.time()) == 0
              and _conditioned(st, FOE, CRIPPLED),
              "KNOWN-BAD ARM --no-nonattack-chain-gate: the Crippled lands and the chain does NOT move")
        # the attack gate is untouched: an ATTACK skill's combo_req is DAGGERS-B5's branch, not this
        check("_na_combo, _na_req, _ = skill_chain_fields(cast[\"skill_id\"])" in src
              and src.index("            if not _is_attack_skill(cast[\"skill_id\"]):\n                _na_combo")
              < src.index("_na_combo, _na_req, _ = skill_chain_fields(cast[\"skill_id\"])")
              and src.count("if not _na_fail:") == 2
              and src.count("_na_body_req = 0 if _is_attack_skill(skill_id) else skill_chain_fields(skill_id)[1]") == 1,
              "SOURCE: the non-attack gate reads the chain fields only for a non-attack, a failed "
              "step skips BOTH the effect and the heal (two `if not _na_fail:` guards), and "
              "land_skill reads a body's requirement once (the NOBODY arm)")

        # ------------------------------------------------------------------
        print("\n6. (D) SKILLS-LV: the ON-HIT condition rider on the wearer's landed attacks")
        WEAKNESS = effects.CONDITION_BY_NAME["Weakness"]
        WIC, IT = authsrv.weapon_in_rider_class, agents.item_template
        check(WIC(IT("starter_sword"), "physical") and WIC(IT("starter_bow"), "physical")
              and WIC(IT("starter_daggers"), "physical") and not WIC(IT("starter_wand"), "physical")
              and not WIC(IT("caster_staff"), "physical")
              and WIC(IT("starter_sword"), "melee") and WIC(IT("starter_axe"), "melee")
              and not WIC(IT("starter_bow"), "melee") and not WIC(IT("starter_spear"), "melee")
              and not WIC(IT("caster_staff"), "melee")
              and WIC(None, "any") and WIC(IT("starter_wand"), "any")
              and not WIC(None, "physical") and not WIC(None, "melee") and not WIC(IT("starter_sword"), "dagger"),
              "weapon_in_rider_class: 'physical' by the item's 587 word (a sword, a bow, daggers are; a "
              "wand's chaos and a staff are not), 'melee' by its [weapon_type] delivery (a sword, an axe "
              "are; a bow, a spear, a staff are not), 'any' everything including no item; no item is "
              "neither physical nor melee, and a class with no reader is nothing")
        authsrv.apply_party_character({"player_weapon": "starter_sword"})
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_PREP, FOE)
        eps = [ep["skill"] for ep in authsrv.effect_table(st).on_agent(PLAYER)]
        check(eps == [S_PREP] and not _conditioned(st, FOE, POISON) and not _conditioned(st, PLAYER, POISON)
              and authsrv.skill_condition(S_PREP, 0) is None and "CONDITION_RIDER_ON_HIT" in log,
              "the player's cast of 435's shape at a selected foe opens the PREPARATION on the player "
              "and puts NOTHING on the foe -- skill_condition is None for a rider row (the "
              "over-application CONDITION_ON_EPISODE refused); the log names the tier", (eps, log[-300:]))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = authsrv.hit_enemy(send, st, FOE, 1)
        ep_p = [e for e in authsrv.effect_table(st).on_agent(FOE) if e["skill"] == POISON]
        check(res == "landed" and _conditioned(st, FOE, POISON) and len(ep_p) == 1
              and ep_p[0]["duration"] == 3.0 and "rider on a physical attack [SKILLS-LV]" in buf.getvalue()
              and st.get("effect_list_suppressed", 0) >= 1,
              "then a SWORD swing lands: the foe is Poisoned for 3 s (the row's bonus slot at rank 0) "
              "through apply_condition -- one episode on the foe, its 0x0042 suppressed as every "
              "foe's is (effect_list_send; retail shows a foe's condition as the status word) -- and "
              "the log names the rider", (res, ep_p, buf.getvalue()[-300:]))
        st["agents"][FOE2]["last_hit"] = 0.0
        with contextlib.redirect_stdout(io.StringIO()):
            res2 = authsrv.hit_enemy(send, st, FOE2, 1)
        check(res2 == "landed" and _conditioned(st, FOE2, POISON) and not _conditioned(st, FAR, POISON),
              "every landed hit carries it: a second foe struck is Poisoned too; the one never hit is not")
        with contextlib.redirect_stdout(io.StringIO()):
            res3 = authsrv.hit_enemy(send, st, FAR, 1, exact=20.0, swing=False, label="a spell")
        check(res3 == "landed" and not _conditioned(st, FAR, POISON),
              "VACUITY: a SPELL's damage through hit_enemy (exact, no swing) is not an attack and "
              "carries no rider")
        authsrv.apply_party_character({"player_weapon": "starter_wand"})
        st, (sent, send) = _world(), _sender()
        _press_and_land(st, send, S_PREP, FOE)
        with contextlib.redirect_stdout(io.StringIO()):
            res = authsrv.hit_enemy(send, st, FOE, 1)
        check(res == "landed" and not _conditioned(st, FOE, POISON)
              and [ep["skill"] for ep in authsrv.effect_table(st).on_agent(PLAYER)] == [S_PREP],
              "KNOWN-BAD ARM (the class): the same episode and a WAND (587 = 6, not physical): the "
              "swing lands and no Poison rides it -- the episode is open, the item fails the class")
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        st, (sent, send) = _world(), _sender()
        _press_and_land(st, send, S_PREP, FOE)
        with contextlib.redirect_stdout(io.StringIO()):
            res = authsrv.hit_enemy(send, st, FOE, 1)
        check(res == "landed" and _conditioned(st, FOE, POISON),
              "a BOW (piercing, physical) carries it: 'physical attacks' is the damage type, not melee")
        authsrv.apply_party_character({"player_weapon": "starter_sword"})
        authsrv.CONDITION_RIDERS = False
        st, (sent, send) = _world(), _sender()
        _press_and_land(st, send, S_PREP, FOE)
        with contextlib.redirect_stdout(io.StringIO()):
            res = authsrv.hit_enemy(send, st, FOE, 1)
        riders_off = authsrv.episode_condition_riders(st, PLAYER, agents.PLAYER_WEAPON)
        authsrv.CONDITION_RIDERS = True
        riders_on = authsrv.episode_condition_riders(st, PLAYER, agents.PLAYER_WEAPON)
        check(res == "landed" and not _conditioned(st, FOE, POISON)
              and [ep["skill"] for ep in authsrv.effect_table(st).on_agent(PLAYER)] == [S_PREP]
              and riders_off == [] and [r[2] for r in riders_on] == [S_PREP],
              "KNOWN-BAD ARM --no-condition-riders: the episode still opens (icon and timer, the "
              "excluded state), the reader answers nothing under the flag and the rider again "
              "with it, and the sword swing carried no Poison", (riders_off, riders_on))
        st, (sent, send) = _world(), _sender()
        with contextlib.redirect_stdout(io.StringIO()):
            res = authsrv.hit_enemy(send, st, FOE, 1)
        check(res == "landed" and not _conditioned(st, FOE, POISON),
              "CONTROL: no episode, no rider -- the null above is the flag, not a dead swing")
        # the fix pass (skills 60.8 #5): a KILLING BLOW carries no rider -- hit_enemy's
        # `never a corpse` guard, which no arm reddened before this one (apply_condition does
        # not refuse a corpse on its own, so the guard is the only thing between the rider and
        # a Poison episode on a body the death just stripped)
        st, (sent, send) = _world(), _sender()
        _press_and_land(st, send, S_PREP, FOE)
        st["agents"][FOE]["health"] = 1.0
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = authsrv.hit_enemy(send, st, FOE, 1)
        check(res == "landed" and st["agents"][FOE]["dead"] and not _conditioned(st, FOE, POISON)
              and authsrv.effect_table(st).on_agent(FOE) == [] and "[SKILLS-LV]" not in buf.getvalue()
              and [ep["skill"] for ep in authsrv.effect_table(st).on_agent(PLAYER)] == [S_PREP],
              "a KILLING BLOW with the preparation open: the foe dies and carries NO Poison -- no "
              "episode on the corpse, no rider line; the preparation is still open on the player",
              buf.getvalue()[-300:])
        # a BODY wearing 1997's shape: the enchantment on the ALLY (byte 3), its melee attacks Weaken
        st, (sent, send) = _world(), _sender()
        hero = st["agents"][HERO]
        hero.update({"weapon_item": "starter_sword", "pos": (60.0, 0.0)})
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.apply_effect(send, st, PLAYER, S_ENCH, 0, HERO, 1)
        eps_h = [ep["skill"] for ep in authsrv.effect_table(st).on_agent(HERO)]
        with contextlib.redirect_stdout(io.StringIO()):
            res = authsrv.land_swing_on_body(send, st, HERO, hero, FOE, 1)
        ep_w = [e for e in authsrv.effect_table(st).on_agent(FOE) if e["skill"] == WEAKNESS]
        check(eps_h == [S_ENCH] and not _conditioned(st, HERO, WEAKNESS) and res == "landed"
              and ep_w and ep_w[0]["duration"] == 5.0 and not _conditioned(st, PLAYER, WEAKNESS),
              "the player's cast of 1997's shape at a hero puts the ENCHANTMENT on the hero (byte 3) "
              "and no Weakness on anyone; the hero's SWORD swing at a hostile then Weakens it for 5 s "
              "(land_swing_on_body's seam)", (eps_h, res, ep_w))
        st, (sent, send) = _world(), _sender()
        hero = st["agents"][HERO]
        hero.update({"weapon_item": "caster_staff", "pos": (60.0, 0.0)})
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.apply_effect(send, st, PLAYER, S_ENCH, 0, HERO, 1)
            res = authsrv.land_swing_on_body(send, st, HERO, hero, FOE, 1)
        check(res == "landed" and not _conditioned(st, FOE, WEAKNESS),
              "KNOWN-BAD ARM (the class): the same enchantment on a hero holding a STAFF -- not melee "
              "-- carries no Weakness")
        st, (sent, send) = _world(), _sender()
        st["player_health"] = 480.0
        foe = st["agents"][FOE]
        foe["weapon_item"] = "starter_axe"
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.apply_effect(send, st, FOE2, S_ENCH, 0, FOE, 1)
            res = authsrv.land_swing(send, st, FOE, foe, 1)
        check(res == "landed" and _conditioned(st, PLAYER, WEAKNESS) and st["player_health"] < 480.0,
              "a HOSTILE wearing it (cast by its ally) swings an AXE at the player: the player is "
              "Weakened (land_swing's seam) -- the wearer is the caster's ally, the side the "
              "template names")
        # the fix pass (skills 60.8 #1, the reviewers' RV-1): the player's byte-3 rider
        # enchantment pressed with a FOE selected -- effect_recipient puts the episode on the
        # FOE (the inert icon every byte-3 row wore before this pass; here the VACUITY GUARD:
        # the reader has an episode to refuse) -- and the foe's axe swing at the player carries
        # NO Weakness: a rider rides the caster's side only, never a foe wearing a misplaced
        # ally enchantment
        st, (sent, send) = _world(), _sender()
        st["player_health"] = 480.0
        _press_and_land(st, send, S_ENCH, FOE)
        foe = st["agents"][FOE]
        foe["weapon_item"] = "starter_axe"
        on_foe = [ep["skill"] for ep in authsrv.effect_table(st).on_agent(FOE)]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            res = authsrv.land_swing(send, st, FOE, foe, 1)
        check(on_foe == [S_ENCH] and res == "landed" and st["player_health"] < 480.0
              and not _conditioned(st, PLAYER, WEAKNESS) and "[SKILLS-LV]" not in buf.getvalue()
              and authsrv.episode_condition_riders(st, FOE, IT("starter_axe")) == [],
              "the player's 1997-shape pressed at a HOSTILE: the enchantment lands on the hostile (the "
              "pre-pass inert icon -- the episode the reader must refuse), its axe swing lands on the "
              "player and carries NO Weakness, the reader answers nothing for the foe: the rider rides "
              "the SIDE the template names (the caster or its allies)", (on_foe, res, buf.getvalue()[-300:]))
        check(src.count("        apply_episode_riders(send, state,") == 3
              and 'if row.get("condition_rider"):' in src
              and src.index("def skill_condition(") < src.index('if row.get("condition_rider"):')
              < src.index("def _condition_terms("),
              "SOURCE: the riders ride the three landing seams (hit_enemy, land_swing, "
              "land_swing_on_body), and skill_condition returns None for a rider row before the "
              "shared reader")

        # ------------------------------------------------------------------
        print("\n7. (E) SKILLS-LV: a label row's knock-down on the single-target non-attack land")

        def kd_words(batch):
            return [(i, v) for i, (op, v) in enumerate(batch)
                    if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT and v[0] == 63]

        def word_idx(batch):
            return [i for i, (op, v) in enumerate(batch) if op == 0x00A3 and v[0] in (16, 17)]

        def apply_idx(batch, cond):
            return [i for i, (op, v) in enumerate(batch)
                    if op == authsrv.GAME_SMSG_EFFECT_APPLY and v[1] == cond]

        TWO_S = authsrv._f32(2.0)
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_TOUCH, FOE)
        kds, ws = kd_words(sent), word_idx(sent)
        check(len(kds) == 1 and kds[0][1][1] == FOE and kds[0][1][2] == TWO_S and ws and ws[-1] < kds[0][0]
              and st["agents"][FOE].get("knocked_until", 0) > time.time()
              and st["agents"][FOE]["health"] < 9000.0 and "[SKILLS-LV]" in log,
              "231's shape (a touch Skill, Lightning damage, knocks_down) at the player's E5: the word, "
              "then [63, foe, 2.0] -- the foe is down for KNOCK_DOWN_SECONDS", (kds, ws, log[-200:]))
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_KDCOND, FOE)
        kds = kd_words(sent)
        check(len(kds) == 1 and kds[0][1][1] == FOE and kds[0][1][2] == TWO_S and _conditioned(st, FOE, POISON)
              and "KNOCKED DOWN" in log and "Poison on agent 10" in log
              and log.index("KNOCKED DOWN") < log.index("Poison on agent 10"),
              "784's shape (a condition-only Spell, knocks_down): [63, foe, 2.0] BEFORE the Poison "
              "(the foe's 0x0042 is suppressed; the log carries the order) -- retail's completion "
              "order: the fall OBSERVED 4 of 5 live 784s, ahead of the Poison on the 2 that show one "
              "(skills 60.3; the 2 that show none are CONTESTED there)", (kds, log[-300:]))
        st, (sent, send) = _world(), _sender()
        _press_and_land(st, send, S_SIGNET, FOE)
        kds = kd_words(sent)
        check(len(kds) == 1 and kds[0][1][1] == FOE and st["agents"][FOE]["health"] < 9000.0
              and st["agents"][FOE2]["health"] == 9000.0 and not st["agents"][FOE2].get("knocked_until"),
              "294's shape (a Signet with area words, AREA_ONE_TARGET): ONE target takes the word and "
              "falls; the other adjacent hostile is untouched -- the one-target path, marked as such")
        st, (sent, send) = _world(), _sender()
        st["player_health"] = 480.0
        foe = st["agents"][FOE]
        foe.update({"skills": [[S_KDCOND, 1.0, 5.0]], "skill_ready": [0.0], "casting": 0, "cast_target": PLAYER})
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            authsrv.land_skill(send, st, FOE, foe, 1)
        kds, ai = kd_words(sent), apply_idx(sent, POISON)
        check(len(kds) == 1 and kds[0][1][1] == PLAYER and kds[0][1][2] == TWO_S and ai and kds[0][0] < ai[0]
              and st.get("player_knocked_until", 0) > time.time() and _conditioned(st, PLAYER, POISON),
              "a HOSTILE casting 784's shape at the player: [63, player, 2.0] before the Poison's "
              "0x0042 (the player's list is shown, so the order is on the wire) -- the player is down "
              "and Poisoned (land_skill's condition-only seam)", (kds, ai))
        st, (sent, send) = _world(), _sender()
        st["player_health"] = 480.0
        foe = st["agents"][FOE]
        foe.update({"skills": [[S_TOUCH, 1.0, 5.0]], "skill_ready": [0.0], "casting": 0, "cast_target": PLAYER})
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.land_skill(send, st, FOE, foe, 1)
        kds, ws = kd_words(sent), word_idx(sent)
        check(len(kds) == 1 and kds[0][1][1] == PLAYER and ws and ws[-1] < kds[0][0]
              and st["player_health"] < 480.0,
              "a HOSTILE casting 231's shape at the player: the word, then the fall (land_skill's "
              "damage seam)", (kds, ws))
        authsrv.LABEL_KNOCKDOWNS = False
        st, (sent, send) = _world(), _sender()
        _press_and_land(st, send, S_TOUCH, FOE)
        reads_off = (authsrv.skill_knocks_down(S_TOUCH), authsrv.skill_knocks_down(S_HANDKD))
        authsrv.LABEL_KNOCKDOWNS = True
        check(kd_words(sent) == [] and st["agents"][FOE]["health"] < 9000.0
              and not st["agents"][FOE].get("knocked_until") and reads_off == (False, True),
              "KNOWN-BAD ARM --no-label-knockdowns: the LABEL row's word lands and nobody falls; the "
              "reader still answers True for a HAND-shaped row (no tier) -- the flag is the tier's, the "
              "hand rows' knock-downs (the attack path, the bursts) stand", reads_off)
        st2, (sent2, send2) = _world(), _sender()
        _press_and_land(st2, send2, S_HANDKD, FOE)
        check(kd_words(sent2) == [] and st2["agents"][FOE]["health"] < 9000.0
              and not st2["agents"][FOE].get("knocked_until"),
              "the single-target term is the TIER's only: a HAND-shaped row with knocks_down on this "
              "path keeps the pre-pass shape (its word, no fall) -- Earthquake under --no-spell-areas "
              "is that case and test_weapons pins it; so --no-label-knockdowns reverts every fall this "
              "pass added and nothing else")
        check(src.count("        nonattack_knock_down(send, state,") == 4
              and src.index("_st_res = hit_enemy(send, state, target, conn_id, exact=float(found[0]),")
              < src.index("nonattack_knock_down(send, state, cast[\"skill_id\"], target,"),
              "SOURCE: the single-target term sits at four sites (the player's standalone word and "
              "condition-only land, a body's condition-only land and its word) and the player's "
              "damage site reads hit_enemy's verdict first")

        # ------------------------------------------------------------------
        print("\n8. (F) SKILLS-LV: the flat-constant condition slot")
        check(authsrv.skill_condition(S_FLAT, 0) == (BLIND, 10.0) and authsrv.skill_condition(S_FLAT, 15) == (BLIND, 10.0)
              and authsrv.skill_condition(S_INDET, 0) is None and authsrv.skill_condition(S_INDET, 15) is None,
              "skill_condition reads a bit-clear slot with EQUAL endpoints as the flat constant (167's "
              "shape: Blind 10 s at any rank) and still refuses DIFFERING ones (1033's shape: None)")
        authsrv.CONDITION_FLAT_CONSTANTS = False
        off = (authsrv.skill_condition(S_FLAT, 0), authsrv.skill_condition(S_INDET, 0))
        authsrv.CONDITION_FLAT_CONSTANTS = True
        check(off == (None, None),
              "KNOWN-BAD ARM --no-condition-flat-constants: both refuse, as until 2026-09-25")
        st, (sent, send) = _world(), _sender()
        log = _press_and_land(st, send, S_FLAT, FOE)
        ep_b = [e for e in authsrv.effect_table(st).on_agent(FOE) if e["skill"] == BLIND]
        check(st["agents"][FOE]["health"] < 9000.0 and len(ep_b) == 1 and ep_b[0]["duration"] == 10.0
              and word_idx(sent) and "hit agent 10" in log and "Blind on agent 10" in log
              and log.index("hit agent 10") < log.index("Blind on agent 10"),
              "through the real cast: 167's shape deals its earth damage (the word on the wire) and "
              "then Blinds the target for 10 s (the foe's episode; its 0x0042 suppressed as a foe's)",
              (ep_b, log[-300:]))
        # every loaded HAND row with a condition means has its slot's bit SET, so the reader
        # changes no hand row (a census, 24 loaded slots on 2026-09-25: only 167 and 1033 are
        # bit-clear, both label rows)
        hand_rows_loaded = {int(k): r for k, r in saved_tables["skill_effect"].items()
                            if r.get("tier") != "label" and str(k).isdigit()}
        skills_loaded = agents.WORLD.tables.get("skills", {})
        hand_clear = []
        for k, r in hand_rows_loaded.items():
            for means, bit in (("scale_means", 2), ("bonus_scale_means", 4)):
                if effects.condition_id(r.get(means)) is None:
                    continue
                srow_ = skills_loaded.get(str(k))
                if srow_ is not None and not int(srow_["skill_arguments"]) & bit:
                    hand_clear.append(k)
        if any(str(k) in skills_loaded for k in hand_rows_loaded):
            check(hand_clear == [],
                  "no HAND row's condition means sits on a bit-clear slot -- the flat reader moves no "
                  "hand row (the census of 2026-09-25)", hand_clear)
        else:
            LEDGER.skip("8. the hand rows' condition slots (1 check)", "no skills table (a bare machine)")

        # ------------------------------------------------------------------
        print("\n5. the flags parse and rebind; the loaded overlay's marks agree with the predicates")
        import serverargs
        ap = serverargs.build_parser(
            doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
            HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
            GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
            VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
        a0 = ap.parse_args([])
        a1 = ap.parse_args(["--no-caster-areas", "--no-party-heals", "--no-nonattack-chain-gate"])
        i_main = src.index("\ndef main():")
        i_listen = src.index("srv.listen(", i_main)
        binds = [src.index(f"        global {g}\n        {g} = False", i_main)
                 for g in ("CASTER_AREAS", "PARTY_HEALS", "NONATTACK_CHAIN_GATE")]
        check((a0.no_caster_areas, a0.no_party_heals, a0.no_nonattack_chain_gate) == (False, False, False)
              and (a1.no_caster_areas, a1.no_party_heals, a1.no_nonattack_chain_gate) == (True, True, True)
              and all(i_main < b < i_listen for b in binds)
              and (authsrv.CASTER_AREAS, authsrv.PARTY_HEALS, authsrv.NONATTACK_CHAIN_GATE) == (True, True, True),
              "--no-caster-areas / --no-party-heals / --no-nonattack-chain-gate parse (default off) "
              "and main() rebinds each global to False before the listener; the defaults are on")
        a2 = ap.parse_args(["--no-condition-riders", "--no-label-knockdowns", "--no-condition-flat-constants"])
        binds_lv = [src.index(f"        global {g}\n        {g} = False", i_main)
                    for g in ("CONDITION_RIDERS", "LABEL_KNOCKDOWNS", "CONDITION_FLAT_CONSTANTS")]
        check((a0.no_condition_riders, a0.no_label_knockdowns, a0.no_condition_flat_constants) == (False, False, False)
              and (a2.no_condition_riders, a2.no_label_knockdowns, a2.no_condition_flat_constants) == (True, True, True)
              and all(i_main < b < i_listen for b in binds_lv)
              and (authsrv.CONDITION_RIDERS, authsrv.LABEL_KNOCKDOWNS, authsrv.CONDITION_FLAT_CONSTANTS) == (True, True, True),
              "SKILLS-LV: --no-condition-riders / --no-label-knockdowns / --no-condition-flat-constants "
              "parse (default off) and main() rebinds each global before the listener; the defaults are on")
        lab = {int(k): r for k, r in saved_tables["skill_effect"].items() if r.get("tier") == "label"}
        hand = {int(k): r for k, r in saved_tables["skill_effect"].items()
                if r.get("tier") != "label" and str(k).isdigit()}
        marks = {m: sorted(s for s, r in lab.items() if m in (r.get("tier_detail") or ()))
                 for m in ("AREA_CASTER", "HEAL_PARTY", "CHAIN_GATED")}
        # the fix pass (ENG-D4C-4): the server predicates are BROADER than the gate (no
        # wording test, no reading), so a HAND row they match would be re-routed with no
        # mark and no test reddening. Every loaded hand row through the same readers: the
        # allow-list of hand rows a consumer may re-route is EMPTY today, so any match is
        # named. Runs on any overlay (the hand rows are always loaded).
        HAND_REROUTED_OK = frozenset()
        hand_area = sorted(s for s in hand if authsrv.caster_area_row(s)
                           and (authsrv.skill_damage(s, 0) or authsrv.skill_condition(s, 0))
                           and s not in HAND_REROUTED_OK)
        hand_party = sorted(s for s in hand if authsrv.party_heal_radius(s) is not None
                            and s not in HAND_REROUTED_OK)
        hand_gated = sorted(s for s in hand if authsrv.skill_chain_fields(s)[1]
                            and not authsrv._is_attack_skill(s))
        check(hand_area == [] and hand_party == [] and len(hand) >= 10,
              f"no HAND skill_effect row ({len(hand)} loaded) is a caster_area_row with a damage or "
              f"a condition, nor a party_heal_radius row -- a consumer re-routes no hand row "
              f"silently (the allow-list is empty)", (hand_area, hand_party))
        check(hand_gated == [],
              "no HAND row is a non-attack with combo_req -- among the effect rows the gate reaches "
              "label rows only", hand_gated)
        if "1643" in agents.WORLD.rows("skills"):
            check(authsrv.skill_chain_fields(1643)[1] == 1 and not authsrv._is_attack_skill(1643)
                  and "1643" not in saved_tables["skill_effect"],
                  "1643 -- a Skill, combo_req 1, NO effect row -- is the one loaded row the gate's "
                  "RECORD read fails unchained beyond the label rows (LU-R6, stated in skills 59.7)")
        else:
            LEDGER.skip("5a. 1643's record (1 check)", "no skills table row 1643 (a bare machine)")
        if not any(marks.values()):
            LEDGER.skip("5b. the loaded overlay's SKILLS-LU marks (3 checks)",
                        "no AREA_CASTER / HEAL_PARTY / CHAIN_GATED row is loaded -- the vault's "
                        "overlay predates SKILLS-LU; regenerate it (skilldesc.py --emit-labels) "
                        "or point RURIK_CONTENT_EXTRA at a fresh emit")
        else:
            # the synthetic rows are still installed; read the REAL rows through the same readers
            areas_pred = sorted(s for s in lab if authsrv.caster_area_row(s)
                                and (authsrv.skill_damage(s, 0) or authsrv.skill_condition(s, 0)))
            check(marks["AREA_CASTER"] == areas_pred and len(areas_pred) >= 5
                  and all(authsrv.caster_area(s) == float(agents.WORLD.get("skills", str(s))["aoe_range"])
                          for s in areas_pred),
                  f"every loaded AREA_CASTER row ({len(areas_pred)}) is exactly a caster_area_row with a "
                  f"damage or a condition, and its radius is the record's own aoe_range -- and no other "
                  f"label row is", (marks["AREA_CASTER"], areas_pred))
            heals_pred = sorted(s for s in lab if authsrv.party_heal_radius(s) is not None)
            check(marks["HEAL_PARTY"] == heals_pred and len(heals_pred) >= 2
                  and all(authsrv.party_heal_radius(s) == 5000.0 for s in heals_pred),
                  f"every loaded HEAL_PARTY row ({len(heals_pred)}) is exactly a party_heal_radius row, "
                  f"5000 u each -- and no other label row is", (marks["HEAL_PARTY"], heals_pred))
            gated_pred = sorted(s for s in lab if authsrv.skill_chain_fields(s)[1]
                                and not authsrv._is_attack_skill(s))
            check(marks["CHAIN_GATED"] == gated_pred and len(gated_pred) >= 3,
                  f"every loaded CHAIN_GATED row ({len(gated_pred)}) is exactly a non-attack with "
                  f"combo_req -- and no other label row is", (marks["CHAIN_GATED"], gated_pred))
        # SKILLS-LV's marks against the server's own readers (a skip on an overlay
        # that predates pass 2)
        marks_lv = {m: sorted(s for s, r in lab.items() if m in (r.get("tier_detail") or ()))
                    for m in ("CONDITION_RIDER_ON_HIT", "KNOCKDOWN_APPLIED", "CONDITION_FLAT_CONSTANT")}
        if not any(marks_lv.values()):
            LEDGER.skip("5c. the loaded overlay's SKILLS-LV marks (3 checks)",
                        "no CONDITION_RIDER_ON_HIT / KNOCKDOWN_APPLIED / CONDITION_FLAT_CONSTANT row is "
                        "loaded -- the vault's overlay predates SKILLS-LV; regenerate it or point "
                        "RURIK_CONTENT_EXTRA at a fresh emit")
        else:
            riders_pred = sorted(s for s in lab if lab[s].get("condition_rider"))
            check(marks_lv["CONDITION_RIDER_ON_HIT"] == riders_pred and len(riders_pred) >= 2
                  and all(authsrv.skill_condition(s, 0) is None
                          and authsrv._condition_terms(s, lab[s], 0) is not None
                          and int(agents.WORLD.get("skills", str(s))["type_code"]) in effects.EFFECT_TYPES
                          and lab[s].get("rider_weapon") in ("any", "physical", "melee") for s in riders_pred),
                  f"every loaded CONDITION_RIDER_ON_HIT row ({len(riders_pred)}) carries condition_rider, "
                  f"lands nothing at the cast, reads a condition for the rider, is an episode type and "
                  f"names a class the server reads -- and no other label row does",
                  (marks_lv["CONDITION_RIDER_ON_HIT"], riders_pred))
            kd_pred = sorted(s for s in lab if authsrv.skill_knocks_down(s))
            authsrv.LABEL_KNOCKDOWNS = False
            kd_off = sorted(s for s in lab if authsrv.skill_knocks_down(s))
            authsrv.LABEL_KNOCKDOWNS = True
            check(marks_lv["KNOCKDOWN_APPLIED"] == kd_pred and len(kd_pred) >= 5 and kd_off == []
                  and all(int(agents.WORLD.get("skills", str(s))["duration0"]) == 0 for s in kd_pred),
                  f"every loaded KNOCKDOWN_APPLIED row ({len(kd_pred)}) is exactly one skill_knocks_down "
                  f"reads, none under --no-label-knockdowns, each on an untimed record",
                  (marks_lv["KNOCKDOWN_APPLIED"], kd_pred, kd_off))
            flat_on = sorted(s for s in lab if authsrv.skill_condition(s, 0) is not None)
            authsrv.CONDITION_FLAT_CONSTANTS = False
            flat_off = sorted(s for s in lab if authsrv.skill_condition(s, 0) is not None)
            authsrv.CONDITION_FLAT_CONSTANTS = True
            flat_pred = sorted(set(flat_on) - set(flat_off))
            check(marks_lv["CONDITION_FLAT_CONSTANT"] == flat_pred and len(flat_pred) >= 1,
                  f"every loaded CONDITION_FLAT_CONSTANT row ({len(flat_pred)}) is exactly a row whose "
                  f"condition resolves ONLY through the flat reader (the flag off removes it) -- and no "
                  f"other label row is", (marks_lv["CONDITION_FLAT_CONSTANT"], flat_on, flat_off))
    finally:
        tables["skills"] = saved_tables["skills"]
        tables["skill_effect"] = saved_tables["skill_effect"]
        (authsrv.skill_timing, authsrv.skill_cost, authsrv.weapon_satisfies,
         authsrv.CASTER_AREAS, authsrv.PARTY_HEALS, authsrv.NONATTACK_CHAIN_GATE,
         agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND) = saved
        (authsrv.CONDITION_RIDERS, authsrv.LABEL_KNOCKDOWNS, authsrv.CONDITION_FLAT_CONSTANTS) = saved_lv
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
