r"""SKILLS-CT: payoffs that ride the bearer's own SPELL completion (studies/skills 69).

    python toolkit/authsrv/test_trigcast.py

`on_cast_triggers` (authsrv.py, beside Empathy's `on_attack_triggers`) fires every live
episode ON a caster whose `content/world.toml` row says `triggers_on_cast`, right AHEAD
of the caster's [58]:

  * Aura of Restoration 180 -- the bearer healed for the paid energy x the scale % /
    100. OBSERVED (toolkit/authsrv/trigjoin.py, section 9 here): one [55, b, b, +f]
    IMMEDIATELY ahead of [58, b, 0] on 256 of 257 live spell completions, 23 / 46 over
    555 at rank 13 for a cost-5 / cost-10 spell.
  * Backfire 28 -- the hexer's scale, armour-ignoring, onto the hexed caster
    (Empathy's channel). RECONSTRUCTION: no tape.

What is checked, through the REAL land_skill (a body's completion) and the REAL press +
cast_tick (the player's E5): the 1 : 2 heals and their slot; Backfire ahead of the
monk's own heal; nothing for an attack skill, a signet, an interrupted or cancelled cast,
a failed chain step, a stripped or expired episode, the bearer's own re-cast, a hex the
caster WEARS NOTHING of (the hexer's side), or under --no-hex-cast-triggers; a killing
payoff ends the cast; Empathy's swing path byte-identical with the hook on and off; the
flag and main()'s wiring; the source sites; and the reader's numbers on the live corpus.
THE FIX PASS (2026-10-07, the review's RV-1..RV-5) added: ONE payoff per trigger skill per
completion however many live episodes of it the caster holds (a refresh, two hexers --
the newest fires; 3e, 4d, 5e); the dead-target exit's payoff (4e); the Deep Wound cut
through heal_agent (4f); the rounding the server chose (4g); the player's PAID cost (5f);
the bearer's book A/B (2c); the kill stopping a second payoff in the hook (5d); and the
reader's three-valued Deep Wound verdict on its own, bare (11a). ROUND 2 (VF-1) added 3f:
two DIFFERENT trigger skills, neither lethal, both fire on one completion (a hook that
stopped after its first payoff passed everything else).
KNOWN-BAD ARMS, each shown to redden its check: the payoff emitted AFTER the [58] (the
order check), the Backfire episode on the HEXER (nothing may fire), a fixed heal and the
word-after-58 model on the corpus (trigjoin's own arms).

Offline: fabricated state, a send collector, no client. The skills rows and attribute
tables it reads are CARRIED (skilltable.py's rows as vault/content/skills.toml holds them,
build 38974; the attribute tables test_mechanics carries) and replace the loaded ones for
the run, so a bare machine takes the same path; section 10 holds them to the vault's own.
Vault-only, each a declared skip decided on its DIRECTORY: section 9 (the live corpus)
and section 10 (the vault's content). Section 11 is pure arithmetic and runs bare.
"""
import argparse
import ast
import contextlib
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks       # noqa: E402
import authsrv      # noqa: E402
import agents       # noqa: E402
import vaultpath    # noqa: E402

# Floors from a real green run, decided on the vault's DIRECTORIES (test_mechanics'
# pattern): FLOOR_BARE with RURIK_VAULT at an empty directory, FLOOR_VAULT with the vault.
FLOOR_BARE = 31     # 2026-10-07 (round 2: +3f; the fix pass +3e 4d 4e 4f 4g 5e 5f 11a; 22 -> 30 -> 31): MEASURED 31 checks, 0 failed, 2 declared skips (sections 9 and 10, 7 checks) with RURIK_VAULT at an empty directory and again at a nonexistent path
FLOOR_VAULT = 38    # 2026-10-07 (round 2: +3f; 29 -> 37 -> 38): MEASURED 38 checks, 0 failed, with the vault (its content and its live captures)
HAVE_CONTENT = os.path.isdir(vaultpath.vault_path("content"))
HAVE_LIVE = os.path.isdir(vaultpath.vault_path("captures", "live"))
LEDGER = checks.Ledger("trigger-on-cast payoffs (SKILLS-CT)",
                       floor=FLOOR_VAULT if (HAVE_CONTENT and HAVE_LIVE) else FLOOR_BARE)
check = checks.adopt(LEDGER)

PLAYER = authsrv.PLAYER_AGENT_ID
AURA, BACKFIRE, EMPATHY, ORISON, POWER_ATTACK, RES_SIGNET, CHAIN_SPELL = 180, 28, 26, 281, 322, 2, 784
FLOAT_T = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
INT_NT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
HEAL55 = agents.GV_HEALTH_GAIN              # 55, positive: a heal
AI55 = agents.GV_ARMOR_IGNORING             # 55 TOO, negative: armour-ignoring damage (the sign and the cause tell the two apart)
FINISHED = agents.GV_SKILL_FINISHED         # 58

# THE CARRIED ROWS (2026-10-07): skilltable.py's rows exactly as vault/content/skills.toml
# holds them (build 38974) -- measured numbers, ids and slots, no text. Section 10 holds
# every one to the vault's own, column for column.
RECORD_BUILD = 38974
RECORD_PROVENANCE = {"source": "client-table", "extractor": "toolkit/clientscan/skilltable.py",
                     "build": RECORD_BUILD}
SKILL_COLUMNS = ("activation", "aftercast", "recharge", "energy", "adrenaline",
                 "adrenaline_units", "attribute", "profession", "type_code", "target", "combo",
                 "combo_req", "weapon_req", "aoe_range", "skill_arguments", "duration0",
                 "duration15", "scale0", "scale15", "bonus_scale0", "bonus_scale15",
                 "projectile", "impact_visual", "touch_range", "half_range")
RECORD = {
    "2": (3.0, 0.0, 0, 0, 0, 0, 51, 0, 7, 6, 0, 0, 0, 0.0, 6, 0, 0, 100, 100, 25, 25, 2077, 2077, False, False),  # a signet (type 7)
    "26": (2.0, 0.75, 10, 10, 0, 0, 2, 5, 4, 5, 0, 0, 0, 0.0, 7, 5, 15, 10, 55, 1, 15, 2077, 2077, False, False),  # Empathy: a cost-10 hex
    "28": (3.0, 0.75, 20, 15, 0, 0, 2, 5, 4, 5, 0, 0, 0, 0.0, 2, 10, 10, 35, 140, 0, 0, 2077, 2077, False, False),  # Backfire
    "180": (0.25, 0.75, 20, 5, 0, 0, 12, 6, 6, 0, 0, 0, 0, 0.0, 2, 60, 60, 200, 500, 0, 1, 2077, 2077, False, False),  # Aura of Restoration
    "281": (1.0, 0.75, 2, 5, 0, 0, 13, 3, 5, 3, 0, 0, 0, 0.0, 2, 0, 0, 30, 80, 0, 0, 2077, 2077, False, False),  # Orison of Healing: a cost-5 heal
    "322": (0.0, 0.0, 3, 5, 0, 0, 17, 1, 14, 5, 0, 0, 185, 0.0, 2, 0, 0, 10, 40, 0, 0, 2077, 2077, False, False),  # Power Attack: an attack skill
    "784": (1.0, 0.75, 20, 10, 0, 0, 30, 7, 5, 5, 0, 2, 0, 0.0, 2, 0, 0, 5, 20, 0, 0, 2077, 2077, False, False),  # a SPELL with a chain requirement
}
ATTRIBUTE_COST = {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6, 7: 7, 8: 9, 9: 11, 10: 13, 11: 16, 12: 20}
ATTRIBUTE_PROFESSION = {0: 5, 1: 5, 2: 5, 3: 5, 4: 4, 5: 4, 6: 4, 7: 4, 8: 6, 9: 6, 10: 6,
                        11: 6, 12: 6, 13: 3, 14: 3, 15: 3, 16: 3, 17: 1, 18: 1, 19: 1,
                        20: 1, 21: 1, 22: 2, 23: 2, 24: 2, 25: 2, 26: 11, 27: 11, 28: 11,
                        29: 7, 30: 7, 31: 7, 32: 8, 33: 8, 34: 8, 35: 7, 36: 8, 37: 9,
                        38: 9, 39: 9, 40: 9, 41: 10, 42: 10, 43: 10, 44: 10, 45: 11,
                        46: 11, 47: 11, 48: 11, 49: 11, 50: 11}
ATTRIBUTE_PRIMARY = {0, 6, 12, 16, 17, 23, 35, 36, 40, 44}


def carried_tables():
    return {
        "skills": {k: agents.content.Row(dict(zip(SKILL_COLUMNS, v)), "skills", k,
                                         dict(RECORD_PROVENANCE))
                   for k, v in RECORD.items()},
        "attribute_cost": {str(k): {"points": v} for k, v in ATTRIBUTE_COST.items()},
        "attribute": {str(k): {"profession": v, "is_primary": k in ATTRIBUTE_PRIMARY}
                      for k, v in ATTRIBUTE_PROFESSION.items()},
    }


_LOADED_TABLES = {k: agents.WORLD.tables.get(k) for k in ("skills", "attribute_cost", "attribute")}
agents.WORLD.tables.update(carried_tables())
_SAVED = {n: getattr(authsrv, n) for n in ("HEX_CAST_TRIGGERS", "HEX_TRIGGERS", "ENERGY",
                                           "EFFECTS", "STATUS_WORD", "ARMOUR_TERM")}


def collector():
    sent = []
    return sent, lambda op, vals, label="", quiet=False: sent.append((op, list(vals), label))


def fresh_state(player_health=100.0):
    st = {"agents": {}, "pos": (0.0, 0.0), "player_health": player_health}
    authsrv.effect_table(st)
    authsrv.player_pools(st)
    return st


def body(st, aid, bar, slot, target, health=300.0, maximum=555.0):
    """A hostile casting `bar[slot]` at `target`, its landing due -- land_skill's input."""
    st["agents"][aid] = {"name": "t", "dead": False, "died_at": 0.0, "health": health,
                         "max_health": maximum, "last_hit": 0.0, "armor_rating": 60,
                         "pos": (0.0, 0.0), "allegiance": agents.ALLEGIANCE_HOSTILE,
                         "attacks_back": True, "skills": list(bar),
                         "skill_ready": [0.0] * len(bar), "casting": slot,
                         "cast_target": target, "cast_lands_at": time.time() - 0.01}
    return st["agents"][aid]


def episode(st, wearer, sid, rank, caster, seconds=60.0, applied=None):
    tc = int(agents.WORLD.get("skills", str(sid))["type_code"])
    return st["effects"].apply(wearer, sid, rank, seconds,
                               time.time() if applied is None else applied,
                               type_code=tc, caster=caster)


def dec(bits):
    """A wire f32 (the int authsrv._f32 encodes) back to its float."""
    import struct
    return struct.unpack("<f", struct.pack("<I", int(bits) & 0xFFFFFFFF))[0]


def f32(x):
    return dec(authsrv._f32(x))


def words(sent, prop, target, cause=None):
    """[(index, f32)] of 0x00A3 [prop, target, cause, f] words."""
    return [(i, dec(v[3])) for i, (op, v, _l) in enumerate(sent)
            if op == FLOAT_T and v[0] == prop and v[1] == target
            and (cause is None or v[2] == cause)]


def finished_at(sent, who):
    return [i for i, (op, v, _l) in enumerate(sent) if op == INT_NT and v[0] == FINISHED and v[1] == who]


def payoff_ahead(sent, who, cause):
    """THE ORDER CHECK: exactly one [55, who, cause, f] and it is the message
    IMMEDIATELY before [58, who, 0] (trigjoin P1c's slot)."""
    w = [i for i, (op, v, _l) in enumerate(sent)
         if op == FLOAT_T and v[0] == HEAL55 and v[1] == who and v[2] == cause]
    f = finished_at(sent, who)
    return len(f) == 1 and len(w) >= 1 and w[0] == f[0] - 1


try:
    authsrv.ENERGY, authsrv.EFFECTS, authsrv.STATUS_WORD, authsrv.ARMOUR_TERM = False, True, True, False
    authsrv.HEX_CAST_TRIGGERS, authsrv.HEX_TRIGGERS = True, True

    # ------------------------------------------------------------------ 1
    print("== 1. the rows: 180 and 28 carry `triggers_on_cast`, no `scale_means` ==")
    r180 = authsrv.skill_effect_row(AURA)
    r28 = authsrv.skill_effect_row(BACKFIRE)
    check(r180.get("triggers_on_cast") == authsrv.CAST_TRIGGER_HEAL
          and r28.get("triggers_on_cast") == authsrv.CAST_TRIGGER_DAMAGE
          and "scale_means" not in r180 and "scale_means" not in r28,
          "1a. world.toml's two hand rows name the payoff and nothing a cast-time reader keys on",
          (dict(r180), dict(r28)))
    check(authsrv.skill_heal(AURA, 13) is None and authsrv.skill_damage(BACKFIRE, 3) is None
          and authsrv.skill_damage(AURA, 13) is None,
          "1b. so the casts themselves resolve nothing at completion: 180 heals no-one 460 on "
          "its own [58], Backfire strikes nobody on landing (the scale is the EPISODE's)",
          (authsrv.skill_heal(AURA, 13), authsrv.skill_damage(BACKFIRE, 3)))
    check(authsrv.skill_scale_value(AURA, 13) == 460 and authsrv.skill_scale_value(BACKFIRE, 3) == 56,
          "1c. the scales the payoffs read: 180 at rank 13 = 460 % (the tape bearers' fit), "
          "Backfire at rank 3 = 56", (authsrv.skill_scale_value(AURA, 13),
                                       authsrv.skill_scale_value(BACKFIRE, 3)))

    # ------------------------------------------------------------------ 2
    print("== 2. an Aura of Restoration bearer: cost 5 and cost 10 heal 1 : 2, ahead of the 58 ==")
    st = fresh_state()
    ele = body(st, 11, [(ORISON, 1.0, 2), (EMPATHY, 2.0, 10)], 0, 11, health=300.0)
    episode(st, 11, AURA, 13, caster=11)
    sent5, send = collector()
    authsrv.land_skill(send, st, 11, ele, 0)
    w5 = words(sent5, HEAL55, 11, 11)
    hp_after5 = st["agents"][11]["health"]
    ele["casting"], ele["cast_target"] = 1, PLAYER
    sent10, send = collector()
    authsrv.land_skill(send, st, 11, ele, 0)
    w10 = words(sent10, HEAL55, 11, 11)
    check(payoff_ahead(sent5, 11, 11) and payoff_ahead(sent10, 11, 11),
          "2a. each completion's payoff is the message IMMEDIATELY before [58, 11, 0] (retail's "
          "slot, 256 of 257)", (sent5[:3], sent10[:3]))
    check(len(w5) == 2 and abs(w5[0][1] - f32(23 / 555.0)) < 1e-7
          and len(w10) == 1 and abs(w10[0][1] - f32(46 / 555.0)) < 1e-7,
          "2b. the cost-5 Orison draws 23 / 555 (5 x 460 %) -- and then its OWN heal behind the 58 "
          "-- the cost-10 Empathy 46 / 555 (10 x 460 %): the tape's 0.04144 / 0.08288",
          (w5, w10))
    # The book half, A/B (the fix pass's RV-5): Orison heals its own caster on the same
    # completion, so "health >= 323" passed with the payoff's book write removed and with no
    # payoff at all (393 / 370 / 370). The same completion from the same state under
    # --no-hex-cast-triggers must leave the bearer EXACTLY 23 lower.
    authsrv.HEX_CAST_TRIGGERS = False
    try:
        st_off = fresh_state()
        ele_off = body(st_off, 11, [(ORISON, 1.0, 2), (EMPATHY, 2.0, 10)], 0, 11, health=300.0)
        episode(st_off, 11, AURA, 13, caster=11)
        _sink, send = collector()
        authsrv.land_skill(send, st_off, 11, ele_off, 0)
    finally:
        authsrv.HEX_CAST_TRIGGERS = True
    hp_off5 = st_off["agents"][11]["health"]
    ratio = (w10[0][1] / w5[0][1]) if (w5 and w10 and w5[0][1]) else None
    check(ratio is not None and abs(ratio - 2.0) < 1e-6 and abs((hp_after5 - hp_off5) - 23.0) < 1e-9,
          "2c. the ratio is exactly 2 and the bearer's book took the 23: the same cost-5 "
          "completion under --no-hex-cast-triggers leaves it exactly 23 lower (A/B -- Orison's "
          "own self-heal rides both arms)", (ratio, hp_after5, hp_off5))
    # KNOWN-BAD ARM: the payoff emitted AFTER the 58 -- the order check must redden
    real = authsrv.on_cast_triggers
    st = fresh_state()
    ele = body(st, 11, [(ORISON, 1.0, 2)], 0, 11)
    episode(st, 11, AURA, 13, caster=11)
    sent, send = collector()
    authsrv.on_cast_triggers = lambda *a, **k: 0
    try:
        authsrv.land_skill(send, st, 11, ele, 0)
    finally:
        authsrv.on_cast_triggers = real
    real(send, st, 11, ORISON, 0)              # the arm: the same payoff, behind the 58
    check(not payoff_ahead(sent, 11, 11) and len(words(sent, HEAL55, 11, 11)) == 2,
          "2d. KNOWN-BAD ARM: the same payoff emitted AFTER the [58] fails the order check "
          "(both words present, the slot wrong)", sent[:4])

    # ------------------------------------------------------------------ 3
    print("== 3. Backfire: the hexed monk's own heal is punished first ==")
    st = fresh_state()
    monk = body(st, 12, [(ORISON, 1.0, 2)], 0, 12, health=80.0, maximum=100.0)
    episode(st, 12, BACKFIRE, 3, caster=PLAYER, seconds=10.0)
    sent, send = collector()
    authsrv.land_skill(send, st, 12, monk, 0)
    pun = words(sent, AI55, 12, PLAYER)
    own = words(sent, HEAL55, 12, 12)
    fin = finished_at(sent, 12)
    check(len(pun) == 1 and abs(pun[0][1] - f32(-0.56)) < 1e-7 and len(fin) == 1
          and pun[0][0] == fin[0] - 1 and own and all(i > pun[0][0] for i, _f in own),
          "3a. exactly one [55, monk, hexer, -0.56] (56 at the hexer's rank 3, armour-ignoring) "
          "IMMEDIATELY ahead of the monk's [58] and AHEAD of its own heal words",
          (pun, fin, own))
    check(bool(own) and not monk["dead"]
          and abs(st["agents"][12]["health"] - min(100.0, 24.0 + own[0][1] * 100)) < 1.0,
          "3b. the monk's book: 80 -> 24 by the punishment, then its own heal", st["agents"][12]["health"])
    # the kill: the cast ends there
    st = fresh_state()
    monk = body(st, 12, [(ORISON, 1.0, 2)], 0, 12, health=50.0, maximum=100.0)
    episode(st, 12, BACKFIRE, 3, caster=PLAYER, seconds=10.0)
    sent, send = collector()
    authsrv.land_skill(send, st, 12, monk, 0)
    check(monk["dead"] and monk.get("casting") is None and not finished_at(sent, 12)
          and not words(sent, HEAL55, 12, 12) and len(words(sent, AI55, 12, PLAYER)) == 1,
          "3c. a Backfire that KILLS the monk ends the cast: no [58], no heal, the slot released "
          "(land_swing's rule for a killing trigger)", [(hex(o), v) for o, v, _l in sent][:6])
    # KNOWN-BAD ARM: the hex worn by the HEXER -- the monk is the caster of a Backfire on the player
    st = fresh_state()
    monk = body(st, 12, [(ORISON, 1.0, 2)], 0, 12, health=80.0, maximum=100.0)
    episode(st, PLAYER, BACKFIRE, 3, caster=12, seconds=10.0)
    sent, send = collector()
    authsrv.land_skill(send, st, 12, monk, 0)
    check(not [w for w in words(sent, AI55, 12) if w[1] < 0]       # 55 is both channels:
          and not words(sent, AI55, PLAYER)                         # the sign says which
          and st["agents"][12]["health"] >= 80.0 and st["player_health"] == 100.0,
          "3d. KNOWN-BAD ARM: the monk is the HEXER (its Backfire sits on the player): its own "
          "completion fires nothing -- the hook reads episodes ON the caster, never BY it", sent[:3])
    # TWO Backfires on the monk from two hexers (the fix pass's RV-1): ONE punishment, the
    # NEWEST episode's -- its hexer, its rank (EffectTable.apply stacks a second episode;
    # retail's one-word-per-completion is OBSERVED for 180, newest-wins is RECONSTRUCTION)
    st = fresh_state()
    body(st, 10, [], None, PLAYER, health=100.0, maximum=100.0)
    monk = body(st, 12, [(ORISON, 1.0, 2)], 0, 12, health=250.0, maximum=300.0)
    episode(st, 12, BACKFIRE, 3, caster=PLAYER, seconds=10.0, applied=time.time() - 2.0)
    episode(st, 12, BACKFIRE, 12, caster=10, seconds=10.0, applied=time.time() - 1.0)
    sent, send = collector()
    authsrv.land_skill(send, st, 12, monk, 0)
    pun = [w for w in words(sent, AI55, 12) if w[1] < 0]
    fin = finished_at(sent, 12)
    check(len(pun) == 1 and pun == words(sent, AI55, 12, 10)
          and abs(pun[0][1] - f32(-authsrv.skill_scale_value(BACKFIRE, 12) / 300.0)) < 1e-7
          and len(fin) == 1 and pun[0][0] == fin[0] - 1,
          "3e. two hexers' Backfires on one monk: ONE [55, monk, hexer, -f] ahead of its [58], "
          "the NEWER episode's (agent 10 at rank 12, 119) -- not one per episode, not the older "
          "hexer's 56", (pun, fin))
    # TWO DIFFERENT trigger skills on one completion, NEITHER lethal (round 2's VF-1): the
    # rule is once per trigger SKILL, so the monk under the player's Backfire that also wears
    # its own 180 draws BOTH payoffs -- a hook that stopped after the first payoff passed every
    # other check here (5d's Backfire kills, where stopping is right). The order across the two
    # skills (ascending buff: the Backfire was opened first) is RECONSTRUCTION -- no tape holds
    # a bearer under both. The book A/B: the same completion with the hook off ends 56 - 23 =
    # 33 higher (Orison's own heal rides both arms, uncapped from 150 / 300).
    books = {}
    for on in (True, False):
        authsrv.HEX_CAST_TRIGGERS = on
        try:
            st = fresh_state()
            monk = body(st, 12, [(ORISON, 1.0, 2)], 0, 12, health=150.0, maximum=300.0)
            episode(st, 12, BACKFIRE, 3, caster=PLAYER, seconds=10.0, applied=time.time() - 2.0)
            episode(st, 12, AURA, 13, caster=12, applied=time.time() - 1.0)
            sent, send = collector()
            authsrv.land_skill(send, st, 12, monk, 0)
        finally:
            authsrv.HEX_CAST_TRIGGERS = True
        books[on] = (st["agents"][12]["health"], monk["dead"], sent)
    sent = books[True][2]
    fin = finished_at(sent, 12)
    pay = [(i, v[2], dec(v[3])) for i, (op, v, _l) in enumerate(sent)
           if op == FLOAT_T and v[0] == AI55 and v[1] == 12 and (fin and i < fin[0])]
    check(len(fin) == 1 and not books[True][1]
          and [(i, cause) for i, cause, _f in pay] == [(fin[0] - 2, PLAYER), (fin[0] - 1, 12)]
          and abs(pay[0][2] - f32(-56 / 300.0)) < 1e-7 and abs(pay[1][2] - f32(23 / 300.0)) < 1e-7
          and abs((books[False][0] - books[True][0]) - 33.0) < 1e-9,
          "3f. a monk under a NON-lethal Backfire that also wears its own 180 completes Orison: "
          "BOTH payoffs, one per trigger skill -- [55, monk, hexer, -56 / 300] then [55, monk, "
          "monk, +23 / 300] -- the last two messages before its [58], and its book 33 lower than "
          "the same completion with the hook off (the cross-skill order RECONSTRUCTION)",
          (pay, fin, books[True][0], books[False][0]))

    # ------------------------------------------------------------------ 4
    print("== 4. nothing fires: an attack skill, a signet, a stripped / expired / re-cast "
          "episode, an interrupted cast, the revert flag ==")
    got = {}
    st = fresh_state()
    episode(st, 11, AURA, 13, caster=11)
    episode(st, 11, BACKFIRE, 3, caster=PLAYER, seconds=10.0)
    body(st, 11, [(POWER_ATTACK, 0.0, 3)], 0, PLAYER)
    for sid in (POWER_ATTACK, RES_SIGNET):
        sent, send = collector()
        got[sid] = (authsrv.on_cast_triggers(send, st, 11, sid, 0), len(sent))
    check(got == {POWER_ATTACK: (0, 0), RES_SIGNET: (0, 0)},
          "4a. under BOTH payoffs an attack skill and a signet completing fire nothing (not "
          "spells; retail's signet under a live 180: 0 of 5)", got)
    # stripped / expired / re-cast / revert, each through the real land_skill
    cases = {}
    for name in ("stripped", "expired", "recast", "revert", "control"):
        st = fresh_state()
        bar = [(AURA, 0.25, 20)] if name == "recast" else [(ORISON, 1.0, 2)]
        ele = body(st, 11, bar, 0, 11)
        ep = episode(st, 11, AURA, 13, caster=11,
                     applied=(time.time() - 61.0) if name == "expired" else None)
        if name == "stripped":
            st["effects"].close(ep["buff"])         # Drain Enchantment's strip, on the book
        authsrv.HEX_CAST_TRIGGERS = name != "revert"
        sent, send = collector()
        try:
            authsrv.land_skill(send, st, 11, ele, 0)
        finally:
            authsrv.HEX_CAST_TRIGGERS = True
        f = finished_at(sent, 11)
        cases[name] = bool(f) and any(i < f[0] for i, _x in words(sent, HEAL55, 11, 11))
    check(cases == {"stripped": False, "expired": False, "recast": False, "revert": False,
                    "control": True},
          "4b. no payoff ahead of the 58 when 180 was STRIPPED (retail 74 of 74), past its 60 s "
          "and not yet ticked out (one at 60.031 drew none), on the bearer's own 180 re-cast (0 "
          "of 2), or under --no-hex-cast-triggers; the control fires", cases)
    # an interrupted cast never completes: interrupt_body clears the slot, and the tick
    # that would have landed it lands nothing
    st = fresh_state()
    ele = body(st, 11, [(ORISON, 1.0, 2)], 0, 11)
    episode(st, 11, AURA, 13, caster=11)
    sent, send = collector()
    res = authsrv.interrupt_body(send, st, 11, ele, 0, BACKFIRE, PLAYER, mode=authsrv.INTERRUPT_MODE_SKILL)
    check(res == "cast" and ele.get("casting") is None and not words(sent, HEAL55, 11, 11),
          "4c. an INTERRUPTED cast ([59] / [35]) fires nothing -- retail's stopped casts under a live "
          "180: 0 of 13", (res, sent[:3]))

    print("== 4b. the fix pass: a refreshed 180, a dead target, Deep Wound, the rounding ==")
    # RV-1: a bearer holding TWO live 180 episodes (a re-cast stacks one: EffectTable.apply)
    # draws ONE heal per completion -- retail, 11 of 11 completions after a refresh
    st = fresh_state()
    ele = body(st, 11, [(ORISON, 1.0, 2)], 0, 11)
    episode(st, 11, AURA, 13, caster=11, applied=time.time() - 30.0)
    episode(st, 11, AURA, 13, caster=11, applied=time.time() - 5.0)
    sent, send = collector()
    authsrv.land_skill(send, st, 11, ele, 0)
    ahead = [x for x in words(sent, HEAL55, 11, 11) if finished_at(sent, 11) and x[0] < finished_at(sent, 11)[0]]
    check(len(st["effects"].on_agent(11)) == 2 and payoff_ahead(sent, 11, 11) and len(ahead) == 1
          and abs(ahead[0][1] - f32(23 / 555.0)) < 1e-7,
          "4d. a bearer holding two live 180 episodes (a refresh) completing Orison: ONE 23 / 555 "
          "ahead of its [58], not one per episode (retail 11 of 11 after a refresh, "
          "20260928T103123 :50061 / :58544)", ahead)
    # RV-2: the cast's TARGET died during the cast -- land_skill's dead-target exit still
    # sends the bearer's [58], and retail's payoff rides it (3 of 3 live completions)
    st = fresh_state()
    corpse = body(st, 13, [], None, PLAYER, health=0.0, maximum=100.0)
    corpse["dead"] = True
    ele = body(st, 11, [(EMPATHY, 2.0, 10)], 0, 13)
    episode(st, 11, AURA, 13, caster=11)
    sent, send = collector()
    authsrv.land_skill(send, st, 11, ele, 0)
    fin = finished_at(sent, 11)
    died_ok = (payoff_ahead(sent, 11, 11) and len(fin) == 1 and "(its target died)" in sent[fin[0]][2]
               and abs(words(sent, HEAL55, 11, 11)[0][1] - f32(46 / 555.0)) < 1e-7)
    # ...and a Backfire that KILLS the caster at that exit ends it there too: no [58]
    st = fresh_state()
    corpse = body(st, 13, [], None, PLAYER, health=0.0, maximum=100.0)
    corpse["dead"] = True
    monk = body(st, 12, [(ORISON, 1.0, 2)], 0, 13, health=50.0, maximum=100.0)
    episode(st, 12, BACKFIRE, 3, caster=PLAYER, seconds=10.0)
    sent2, send = collector()
    authsrv.land_skill(send, st, 12, monk, 0)
    killed_ok = (monk["dead"] and not finished_at(sent2, 12) and len(words(sent2, AI55, 12, PLAYER)) == 1)
    check(died_ok and killed_ok,
          "4e. a 180 bearer whose spell's TARGET died mid-cast: its [58] '(its target died)' still "
          "carries the heal IMMEDIATELY ahead of it (OBSERVED 3 of 3: 20260817T231139 :54071 b10 / "
          "b14, :50286 b10); a Backfire that kills the caster there ends the cast, no [58]",
          ([(hex(o), v, l) for o, v, l in sent][:3], [(hex(o), v) for o, v, _l in sent2][:4]))
    # RV-4 (a): the 180 heal is HEALING -- a Deep-Wounded bearer's word is cut through
    # heal_agent's door (healing=True), never the uncut 46; the twin is heal_agent itself
    st = fresh_state()
    ele = body(st, 11, [(EMPATHY, 2.0, 10)], 0, PLAYER)
    episode(st, 11, AURA, 13, caster=11)
    st["deep_wound"] = {11: 111.0}
    sent, send = collector()
    authsrv.land_skill(send, st, 11, ele, 0)
    st_twin = fresh_state()
    body(st_twin, 11, [], None, PLAYER)
    st_twin["deep_wound"] = {11: 111.0}
    twin, send = collector()
    authsrv.heal_agent(send, st_twin, 11, 11, 46, 0, healing=True)
    got = [round(f * 555.0, 3) for _i, f in words(sent, HEAL55, 11, 11)]
    want = [round(dec(v[3]) * 555.0, 3) for op, v, _l in twin if op == FLOAT_T]
    check(payoff_ahead(sent, 11, 11) and len(got) == 1 and got == want and got[0] in (36.0, 37.0),
          "4f. a Deep-Wounded 180 bearer's cost-10 completion: the word is heal_agent's Deep Wound "
          "cut of 46 (healing=True; 36 by HEAL-INT's truncation, where retail's six words round to "
          "37 -- CONTESTED, skills 69.4), never the uncut 46", (got, want))
    # RV-4 (c): the rounding the server CHOSE (half-up; the tape cannot discriminate -- every
    # witnessed product is whole): 7 x 240 % = 16.8 -> 17 (truncation 16), 7 x 220 % = 15.4 -> 15
    # (ceiling 16)
    rounded = {}
    for rank in (2, 1):
        st = fresh_state()
        body(st, 11, [], None, PLAYER)
        episode(st, 11, AURA, rank, caster=11)
        sent, send = collector()
        authsrv.on_cast_triggers(send, st, 11, ORISON, 0, paid=7)
        rounded[rank] = [round(f * 555.0, 3) for _i, f in words(sent, HEAL55, 11, 11)]
    check(rounded == {2: [17.0], 1: [15.0]},
          "4g. a paid 7 at rank 2 (240 %) heals 17 and at rank 1 (220 %) heals 15 -- half-up, the "
          "server's CHOICE (UNDISCRIMINATED on tape: costs 5 / 10 make every product whole)", rounded)

    # ------------------------------------------------------------------ 5
    print("== 5. the player: the real press and cast_tick's E5 ==")

    def press_and_land(sid, target, st, paid=None, close=False):
        """The real press, then cast_tick's E5. `paid`: the cast PAID that much (a glyph's
        discount, written onto the pending cast) and the completion runs under ENERGY, the
        arm that hands `cast["cost"]` to the payoff. `close`: the E3 / E6 run out too and the
        caster frees, so the next press is a fresh cast (the RV-1 re-cast)."""
        saved = (authsrv.skill_cost, authsrv.weapon_satisfies)
        authsrv.skill_cost = lambda s: (0, 0)          # the press's gates; the payoff reads the row
        authsrv.weapon_satisfies = lambda s: True
        try:
            sink, drop = collector()
            authsrv.handle_skill_press([0, sid, 0, target], drop, st, 0, authsrv.GAME_CMSG_USE_SKILL)
        finally:
            authsrv.skill_cost, authsrv.weapon_satisfies = saved
        for c in st.get("pending_casts") or ():
            for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
                c[k] -= 30.0
            if paid is not None:
                c["cost"] = paid
        sent, send = collector()
        _energy = authsrv.ENERGY
        authsrv.ENERGY = _energy or paid is not None
        try:
            authsrv.cast_tick(send, st, 0)
        finally:
            authsrv.ENERGY = _energy
        if close:
            for c in st.get("pending_casts") or ():
                for k in ("e3_at", "e6_at"):
                    c[k] -= 60.0
            _sink2, send2 = collector()
            authsrv.cast_tick(send2, st, 0)
            st["cast_busy_until"] = 0.0
        return sent

    st = fresh_state(player_health=50.0)
    body(st, 10, [], None, PLAYER, health=100.0, maximum=100.0)
    episode(st, PLAYER, AURA, 12, caster=PLAYER)
    sent = press_and_land(ORISON, PLAYER, st)
    pool = authsrv.player_max_health(st)
    w = words(sent, HEAL55, PLAYER, PLAYER)
    e5 = [i for i, (op, _v, _l) in enumerate(sent) if op == authsrv.GAME_SMSG_SKILL_RECHARGE]
    check(payoff_ahead(sent, PLAYER, PLAYER) and bool(w) and bool(e5) and e5[0] < w[0][0]
          and abs(w[0][1] - f32(22 / float(pool))) < 1e-7,
          "5a. the player bearing 180 (rank 12, 440 %) completes Orison: E5, then 22 = 5 x 440 % "
          "IMMEDIATELY ahead of its [58] (RECONSTRUCTION: no observer ever cast under 180)",
          [(hex(o), v) for o, v, _l in sent][:4])
    # a failed chain step: the requirement unmet, the payoff never fires
    authsrv.HEX_CAST_TRIGGERS = True
    st = fresh_state(player_health=50.0)
    body(st, 10, [], None, PLAYER, health=100.0, maximum=100.0)
    episode(st, PLAYER, AURA, 12, caster=PLAYER)
    unmet = authsrv.player_chain_unmet(st, CHAIN_SPELL, 10, time.time())
    sent = press_and_land(CHAIN_SPELL, 10, st)
    check(unmet and not words(sent, HEAL55, PLAYER, PLAYER)
          and not authsrv.player_chain_unmet(st, ORISON, 10, time.time())
          and not authsrv.player_chain_unmet(st, POWER_ATTACK, 10, time.time()),
          "5b. 784 (a SPELL that must follow a lead) with no lead on its target: the E5 block's "
          "chain verdict is FAILED and no payoff rides it; Orison and an attack skill are never "
          "chain-unmet", [(hex(o), v) for o, v, _l in sent][:5])
    # a cancelled cast releases and lands nothing
    st = fresh_state(player_health=50.0)
    episode(st, PLAYER, AURA, 12, caster=PLAYER)
    saved = (authsrv.skill_cost, authsrv.weapon_satisfies)
    authsrv.skill_cost, authsrv.weapon_satisfies = (lambda s: (0, 0)), (lambda s: True)
    try:
        sink, drop = collector()
        authsrv.handle_skill_press([0, ORISON, 0, PLAYER], drop, st, 0, authsrv.GAME_CMSG_USE_SKILL)
    finally:
        authsrv.skill_cost, authsrv.weapon_satisfies = saved
    for c in st["pending_casts"]:
        c["cancelled"] = "a test cancel"
        for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
            c[k] -= 30.0
    sent, send = collector()
    authsrv.cast_tick(send, st, 0)
    check(not words(sent, HEAL55, PLAYER, PLAYER) and not finished_at(sent, PLAYER),
          "5c. a CANCELLED cast releases ([59] / E2) and fires nothing", sent[:3])
    # a Backfire that kills the player ends the completion
    # The player ALSO wears its own 180, opened after the Backfire (the higher buff id, so it
    # would fire second): the killing payoff must stop the hook itself, or a dead player is
    # "healed" -- heal_agent has no dead-player door (the fix pass made 5d carry the 180)
    st = fresh_state(player_health=20.0)
    body(st, 10, [], None, PLAYER, health=100.0, maximum=100.0)
    episode(st, PLAYER, BACKFIRE, 3, caster=10, seconds=10.0)
    episode(st, PLAYER, AURA, 12, caster=PLAYER)
    sent = press_and_land(ORISON, PLAYER, st)
    check(st.get("player_dead") and len(words(sent, AI55, PLAYER, 10)) == 1
          and not finished_at(sent, PLAYER) and not words(sent, HEAL55, PLAYER, PLAYER),
          "5d. a foe's Backfire (56) killing the player at its E5 ends the completion: the "
          "punishment, the death, no [58], no heal -- not even its own live 180's payoff, which "
          "would have fired next", [(hex(o), v) for o, v, _l in sent][:4])
    # RV-1 on the player's own path (no AI gate holds its re-cast): 180 cast TWICE through the
    # real press and cast_tick stacks two episodes; the next Orison draws ONE heal, not two
    st = fresh_state(player_health=50.0)
    body(st, 10, [], None, PLAYER, health=100.0, maximum=100.0)
    with contextlib.redirect_stdout(io.StringIO()):
        press_and_land(AURA, PLAYER, st, close=True)
        press_and_land(AURA, PLAYER, st, close=True)
        n_aura = len([e for e in st["effects"].on_agent(PLAYER) if e["skill"] == AURA])
        sent = press_and_land(ORISON, PLAYER, st)
    fin = finished_at(sent, PLAYER)
    ahead = [x for x in words(sent, HEAL55, PLAYER, PLAYER) if fin and x[0] < fin[0]]
    check(n_aura == 2 and payoff_ahead(sent, PLAYER, PLAYER) and len(ahead) == 1,
          "5e. the player re-casts 180 (two live episodes) and completes Orison: ONE heal ahead of "
          "its [58] -- one payoff per trigger skill per completion (retail 11 of 11 after a refresh)",
          (n_aura, ahead))
    # RV-4 (b): the player is healed on the energy the cast PAID (`cast["cost"]` under ENERGY),
    # not the record's 5: a glyph-discounted 3 at 440 % = 13.2 -> 13, never 22
    st = fresh_state(player_health=50.0)
    body(st, 10, [], None, PLAYER, health=100.0, maximum=100.0)
    episode(st, PLAYER, AURA, 12, caster=PLAYER)
    with contextlib.redirect_stdout(io.StringIO()):
        sent = press_and_land(ORISON, PLAYER, st, paid=3)
    pool = authsrv.player_max_health(st)
    w = words(sent, HEAL55, PLAYER, PLAYER)
    check(payoff_ahead(sent, PLAYER, PLAYER) and abs(w[0][1] - f32(13 / float(pool))) < 1e-7,
          "5f. the player's paid cost: Orison discounted to 3 energy (written onto the cast, as "
          "a glyph does) under rank-12 180 heals 13 = 3 x 440 %, not the record's 22",
          (round(w[0][1] * pool, 3) if w else None, pool))

    # ------------------------------------------------------------------ 6
    print("== 6. Empathy's swing path: byte-identical with the cast hook on and off ==")
    # The swinging foe ALSO wears both cast-trigger episodes -- its own 180 and the player's
    # Backfire -- so a cast hook that leaked into the swing path would fire here and the
    # two arms would differ (a foe wearing neither could not tell; the mutation pass's M15).
    out = {}
    for on in (True, False):
        authsrv.HEX_CAST_TRIGGERS = on
        st = fresh_state()
        foe = body(st, 11, [], None, PLAYER, health=60.0, maximum=100.0)
        foe["max_declared_on_hit"] = None
        episode(st, 11, EMPATHY, 0, caster=PLAYER, seconds=10.0)
        episode(st, 11, AURA, 13, caster=11)
        episode(st, 11, BACKFIRE, 3, caster=PLAYER, seconds=10.0)
        sent, send = collector()
        res = authsrv.land_swing(send, st, 11, foe, 0)
        out[on] = (res, [(op, v) for op, v, _l in sent], st["agents"][11]["health"])
    authsrv.HEX_CAST_TRIGGERS = True
    check(out[True] == out[False]
          and [v for op, v in out[True][1] if op == FLOAT_T and v[0] == AI55 and v[1] == 11]
          == [[AI55, 11, PLAYER, authsrv._f32(-0.10)]],
          "6a. the foe's swing under Empathy (and wearing 180 and Backfire): ONE [55, foe, hexer, "
          "-0.10] ahead of its hit and no cast payoff, every byte the same with "
          "--no-hex-cast-triggers (a swing is not a spell completion)",
          (out[True][0], out[True][2]))

    # ------------------------------------------------------------------ 7
    print("== 7. the flag and main()'s wiring ==")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            parsed = (ap.parse_args([]).no_hex_cast_triggers,
                      ap.parse_args(["--no-hex-cast-triggers"]).no_hex_cast_triggers)
    except (SystemExit, AttributeError) as exc:
        parsed = ("refused", repr(exc))
    check(parsed == (False, True) and _SAVED["HEX_CAST_TRIGGERS"] is True,
          "7a. --no-hex-cast-triggers parses (default off) and the hook ships ON", parsed)
    tree = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    funcs = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
    wiring = [n for n in ast.walk(funcs["main"]) if isinstance(n, ast.If)
              and isinstance(n.test, ast.Attribute) and n.test.attr == "no_hex_cast_triggers"]
    flipped = {}
    for flag in (True, False):
        authsrv.HEX_CAST_TRIGGERS = True
        mod = ast.Module(body=wiring, type_ignores=[])
        ast.fix_missing_locations(mod)
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(mod, authsrv.__file__, "exec"),                  # noqa: S102
                 authsrv.__dict__, {"a": argparse.Namespace(no_hex_cast_triggers=flag)})
        flipped[flag] = authsrv.HEX_CAST_TRIGGERS
    authsrv.HEX_CAST_TRIGGERS = True
    check(len(wiring) == 1 and flipped == {True: False, False: True},
          "7b. main()'s `if a.no_hex_cast_triggers:` block, lifted out and RUN against authsrv's "
          "globals, flips HEX_CAST_TRIGGERS (a block without its `global` would leave it True) "
          "and leaves it alone with the flag off", (len(wiring), flipped))

    # ------------------------------------------------------------------ 8
    print("== 8. the source: the two call sites, ahead of each [58] ==")
    src = open(authsrv.__file__, encoding="utf-8").read()

    def body_of(name):
        n = funcs[name]
        return "\n".join(src.splitlines()[n.lineno - 1:n.end_lineno])

    ls, ct = body_of("land_skill"), body_of("cast_tick")
    # RE-AIMED by the fix pass (RV-2): land_skill holds TWO calls now -- the dead-target
    # exit's (retail fires the payoff there, 3 of 3) and the main exit's -- each ahead of
    # its own [58] send; the first cut held one and labelled the dead-target exit silent
    hook = "if on_cast_triggers(send, state, agent_id, skill_id, conn_id) and agent.get(\"dead\"):"
    i_dt = ls.find(hook)
    i_dt58 = ls.find("f\"agent {agent_id} finishes casting {skill_id} (its target died)\")", i_dt)
    i_ls = ls.find(hook, i_dt + 1)
    i_ls58 = ls.find("f\"agent {agent_id} finishes casting {skill_id}\")", i_ls)
    i_ct = ct.find("and on_cast_triggers(send, state, PLAYER_AGENT_ID, cast[\"skill_id\"], conn_id,")
    i_ct58 = ct.find("f\"skill_finished: skill {cast['skill_id']} completes\")", i_ct)
    order = [funcs[n].lineno for n in ("signet_activation", "hex_skill_use_chain",
                                       "on_attack_triggers", "on_cast_triggers")]
    check(0 < i_dt < i_dt58 < i_ls < i_ls58 and i_ct > 0 and i_ct58 > i_ct
          and ls.count("on_cast_triggers(") == 2 and ct.count("on_cast_triggers(") == 1
          and src.count("if not _na_fail:") == 2
          and order[0] < order[1] < order[2] < order[3],
          "8a. two calls in land_skill (the dead-target exit's, then the main exit's) and one in "
          "cast_tick, each before its own [58] send; test_labelconsumers' `if not _na_fail:` count "
          "still 2; on_cast_triggers sits after on_attack_triggers, outside test_mechanics' "
          "signet_activation..hex_skill_use_chain slice", (i_dt, i_dt58, i_ls, i_ls58, i_ct, i_ct58, order))

    # ------------------------------------------------------------------ 9
    print("== 9. the reader on the live corpus (trigjoin.py) ==")
    if not HAVE_LIVE:
        LEDGER.skip("9. trigjoin.py over the live corpus (6 checks)",
                    f"no vault/captures/live directory at {vaultpath.vault_path('captures', 'live')}")
    else:
        import trigjoin
        with contextlib.redirect_stdout(io.StringIO()):
            c = trigjoin.census()
            s = trigjoin.score(c)
            fx, af, tr = trigjoin.score(c, "fixed"), trigjoin.score(c, "after58"), trigjoin.score(c, "trunc")
        v = trigjoin.verdicts(s, fx, af, tr)
        check(all(v.values()), "9a. the reader's own verdict holds: P1 / P2 failed as registered, "
              "P1c P2c P3 and Q4-Q6 hold, all three known-bad arms redden", v)
        check(s["p1_n"] >= 257 and s["p1c_ok"] >= 256 and s["unexplained"] == 0
              and s["p1_n"] - s["p1c_ok"] == len(s["misses"])
              and all(m[-1] for m in s["misses"]),
              "9b. P1c: one word IMMEDIATELY ahead of the bearer's 58 on >= 256 of >= 257 live "
              "completions (FLOORS); every miss has a Drain Enchantment onto its bearer",
              (s["p1c_ok"], s["p1_n"], s["misses"]))
        # RE-AIMED by the fix pass (RV-3): the law checked PER ROW -- f x predicted_max ==
        # round(0.8 h), h the bearer's fit's heal -- where the first cut matched the two literal
        # tuples (46, 37, 455) / (23, 18, 455), so a later capture's confirming Deep Wound word
        # at any other cost or maximum would have reddened it. The counts stay FLOORS; an
        # UNDECIDED word (a bearer with no clean fit) is printed by the reader, never scored.
        ele = {k: v for k, v in s["p2c_fits"].items() if v == [(555, [13])]}
        dw = [x for x in s["p2c_dw"] if x[-1] is not None]
        law = [x for x in dw if x[-1] is True and x[4] == int(0.8 * x[3] + 0.5)
               and abs(x[6] - x[4]) <= 0.003]
        sharp = [x for x in law if int(0.8 * x[3] + 0.5) != int(0.8 * x[3])]
        check(len(ele) >= 14 and len(dw) >= 6 and len(law) == len(dw) and len(sharp) >= 4,
              "9c. P2c: >= 14 bearers fit (555, rank 13) alone -- 23 / 46, the server's 460 % -- and "
              "every decided Deep Wound word is round(0.8 h) over predicted_max (>= 6, >= 4 of them "
              "where round and truncation differ: 37 from 46)",
              (len(ele), len(dw), len(law), len(sharp), s["p2c_dw"][:2]))
        check(s["p3_not_live"] >= 74 and not s["p3_with_word"]
              and s["q4"] and s["q5"] and s["q6"],
              "9d. no word on >= 74 completions under no live 180, the 180 re-cast, a signet or a "
              "stopped cast -- the four 'nothing fires' the server copies",
              (s["p3_not_live"], s["q4_refresh"], len(s["q5_nonspell"]), len(s["q6_stopped"])))
        check(len(fx["p2c_off"]) == fx["p2c_pairs"] > 0 and af["p1c_ok"] == 0
              and [x for x in tr["p2c_dw"] if x[-1] is False],
              "9e. the arms: a fixed heal is off on every ratio pair, the word-after-58 model "
              "places 0, the truncating cut misses the 37s",
              (fx["p2c_pairs"], af["p1c_ok"], len([x for x in tr["p2c_dw"] if x[-1] is False])))
        check(s["p1_mixed"] >= 1 and not s["p1"] and not s["p2"],
              "9f. and the two predictions FAILED as registered stay printed as failed (a mixed "
              "instant; the Deep Wound words) -- never re-worded", (s["p1_mixed"], s["p1"], s["p2"]))

    # ------------------------------------------------------------------ 10
    print("== 10. the rows this file carries, against the vault's own ==")
    if not HAVE_CONTENT:
        LEDGER.skip("10. the carried rows against the vault's (1 check)",
                    f"no vault/content directory at {vaultpath.vault_path('content')}")
    else:
        for _k, _t in _LOADED_TABLES.items():
            if _t is None:
                agents.WORLD.tables.pop(_k, None)
            else:
                agents.WORLD.tables[_k] = _t
        off = {}
        for kind, rows in carried_tables().items():
            loaded = agents.WORLD.rows(kind)
            for key, row in rows.items():
                got = loaded.get(key)
                if got is None:
                    off[f"{kind}.{key}"] = "absent"
                    continue
                cols = [c for c, val in row.items() if got.get(c, "absent") != val]
                if kind == "skills":
                    cols += [c for c in got if c not in row]
                    if got.provenance != row.provenance:
                        cols.append(f"provenance {got.provenance}")
                if cols:
                    off[f"{kind}.{key}"] = cols
            if kind != "skills":
                for key in sorted(set(loaded) - set(rows), key=str):
                    off[f"{kind}.{key}"] = "not carried"
        check(not off, f"10a. every one of the {len(RECORD)} carried skills rows and both attribute "
              f"tables are the vault's own, column for column (build {RECORD_BUILD})", off)

    # ------------------------------------------------------------------ 11
    print("== 11. the reader's Deep Wound verdict on its own (trigjoin.dw_verdict; bare) ==")
    # The fix pass's RV-3: a Deep Wound word over a bearer whose clean words fit SEVERAL
    # (max, rank) pairs -- 20260917T224104 :62557 b117's shape, 25 / 480 and 50 / 480 at cost
    # 5 / 10, five fits 192..576 -- used to score False whatever it said, so a CONFIRMING word
    # reddened P2c. Now: True when some fit predicts it, False when none does, None (UNDECIDED)
    # with no fit at all. Pure arithmetic, no vault.
    import trigjoin
    multi = trigjoin.bearer_fit([(5, f32(25 / 480.0)), (10, f32(50 / 480.0))], 200, 500)
    unique = trigjoin.bearer_fit([(5, f32(23 / 555.0)), (10, f32(46 / 555.0))], 200, 500)
    verdict = {
        "confirming": trigjoin.dw_verdict(multi, 5, f32(20 / 384.0), 200, 500)[-1],
        "refuting": trigjoin.dw_verdict(multi, 5, f32(19 / 384.0), 200, 500)[-1],
        "no fit": trigjoin.dw_verdict([], 5, f32(20 / 384.0), 200, 500)[-1],
        "37 round": trigjoin.dw_verdict(unique, 10, f32(37 / 455.0), 200, 500)[-1],
        "37 trunc": trigjoin.dw_verdict(unique, 10, f32(37 / 455.0), 200, 500, "trunc")[-1],
    }
    check(len(multi) == 5 and unique == [(555, [13])]
          and verdict == {"confirming": True, "refuting": False, "no fit": None,
                          "37 round": True, "37 trunc": False},
          "11a. a confirming Deep Wound word over a five-fit bearer (20 / 384 = round(0.8 x 25) over "
          "predicted_max(480)) is CONFIRMING, a 19 / 384 refutes every fit, no fit is UNDECIDED; "
          "on the unique (555, 13) bearer 37 / 455 holds by round and fails by truncation",
          (multi, unique, verdict))
finally:
    for _n, _v in _SAVED.items():
        setattr(authsrv, _n, _v)
    for _k, _t in _LOADED_TABLES.items():
        if _t is None:
            agents.WORLD.tables.pop(_k, None)
        else:
            agents.WORLD.tables[_k] = _t

sys.exit(LEDGER.verdict())
