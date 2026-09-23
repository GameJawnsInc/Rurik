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
LEDGER = checks.Ledger("label consumers", floor=40)
check = LEDGER.ok

PLAYER = authsrv.PLAYER_AGENT_ID
FOE, FOE2, FAR = 10, 11, 12          # hostiles: adjacent, adjacent, 400 u off
HERO, HERO2 = 200, 201               # party bodies: 110 u off, 6000 u off
POISON = effects.CONDITION_BY_NAME["Poison"]
CRIPPLED = effects.CONDITION_BY_NAME["Crippled"]

# ---- synthetic rows: the shapes of 183 / 840 / 287 / 784 / 974 / a plain self heal,
# and (the fix pass) 1033's damage shape, a chained self heal, a chained stance
S_FIRE, S_POISON, S_PARTY, S_CHAIN, S_STEP, S_SELF = 900001, 900002, 900003, 900004, 900005, 900006
S_CHAINDMG, S_CHAINHEAL, S_CHAINSTANCE = 900007, 900008, 900009


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
    finally:
        tables["skills"] = saved_tables["skills"]
        tables["skill_effect"] = saved_tables["skill_effect"]
        (authsrv.skill_timing, authsrv.skill_cost, authsrv.weapon_satisfies,
         authsrv.CASTER_AREAS, authsrv.PARTY_HEALS, authsrv.NONATTACK_CHAIN_GATE,
         agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND) = saved
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
