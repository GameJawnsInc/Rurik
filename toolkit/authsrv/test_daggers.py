"""Daggers and the Assassin's attack chain (studies/daggers, DAGGERS-B2..B5).

    python toolkit/authsrv/test_daggers.py

WHAT IS STRONG HERE AND WHAT IS NOT. Section 5's failed-step batch is checked
against RETAIL'S OWN ORDER, read off 20260819T132414 (the owner's cold off-hand
at t = 236.303 beside an armed press of the same skill at 255.343): that is
the verbatim part. Sections 1-4 are our grammar and our plumbing agreeing with
the content rows -- necessary, and they each carry the arm that makes them
mean something (the rival bit order, the hammer in hand, the revert flag).
Since RUN-DAGGERS-1 (20260917T160915) the dual's two batches, the cold dual's two
fail words, the silent re-lead, the double strike's batch and the critical's
energy pair are retail's own order too. What stays RECONSTRUCTION: the clear at
the ATTACKER's death, the bare release for a wrong weapon, a blocked lead
advancing nothing, and what a missed first strike does to a double.

No socket, no client. Sections 3-6 read `skills` rows, which are VAULT-ONLY
(skilltable.py --emit-content); without them the chain fields read 0 and the
sections declare a skip rather than passing on nothing.
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import agents  # noqa: E402
import chain  # noqa: E402
import checks  # noqa: E402

# FLOOR 76, from the green run of 2026-09-17 on the machine with the vault.
LEDGER = checks.Ledger("daggers and the attack chain", floor=76)
check = LEDGER.ok

PLAYER = 1
FOE = 10
LEAD, OFF, DUAL, AFTER_DUAL = 782, 780, 775, 781
E2, E3, E4, E5, E6 = 0x00E2, 0x00E3, 0x00E4, 0x00E5, 0x00E6
COMBO = 0x005C


def section_grammar():
    print("1. chain.py: the grammar, and the rival bit order refuted")
    met = chain.requirement_met
    check(all(met(0, s) for s in range(4)),
          "a skill with no must-follow word lands on any state")
    check(met(0x02, 1) and not met(0x02, 0) and not met(0x02, 2)
          and not met(0x02, 3),
          "0x02 lands after a LEAD and after nothing else")
    check(met(0x04, 2) and not met(0x04, 1) and not met(0x04, 3),
          "0x04 lands after an OFF-HAND and after nothing else")
    check(met(0x01, 3) and not met(0x01, 1) and not met(0x01, 2),
          "0x01 lands after a DUAL -- bit 0 is the dual, which is what "
          "refutes 1 << (combo - 1): under that rule 0x01 would follow a lead")
    check(met(0x10, 0),
          "the one UNVERIFIED bit (0x10, one row) is not judged as a chain "
          "requirement")
    t = chain.ChainTable()
    now = 1000.0
    check(t.advance(FOE, 0, now) is None and t.state_on(FOE, now) == 0,
          "a skill that counts as nothing advances nothing")
    check(t.advance(FOE, 1, now) == 1 and t.state_on(FOE, now + 14.9) == 1
          and t.state_on(FOE, now + 15.0) == 0,
          f"a lead holds for CHAIN_SECONDS = {chain.CHAIN_SECONDS} and not past")
    t.advance(FOE, 2, now + 10.0)
    check(t.state_on(FOE, now + 24.9) == 2 and t.expired(now + 24.9) == []
          and t.expired(now + 25.0) == [FOE],
          "an advance RESTARTS the clock (OBSERVED: RUN-DAGGERS-1's clears "
          "are 15.000 s after the LAST chain hit, section 8)")
    check(t.clear(FOE) and not t.clear(FOE),
          "clear() says whether there was an icon to take down")


def section_content():
    import authsrv
    print("\n2. the item row and the maps (DAGGERS-B2)")
    dag = agents.item_template("starter_daggers")
    check(dag["item_type"] == 32 and authsrv.weapon_damage_range(dag) == (1, 3),
          "starter_daggers: type 32 (the wire's), and its own 584 word reads "
          "1-3 -- the owner's own pair's word, WIKI's Starter Daggers",
          f"type {dag['item_type']}, range {authsrv.weapon_damage_range(dag)}")
    check(authsrv.WEAPON_TYPE_ATTRIBUTE.get(32) == 29
          and authsrv.WEAPON_TYPE_RATE.get(32) == "daggers"
          and float(agents.ATTACK_SPEED["daggers"]) == 1.33,
          "daggers swing at Dagger Mastery (29), 1.33 s apart")
    check(authsrv.WEAPON_TYPE_REQ_BIT == {2: 0x01, 32: 0x08, 15: 0x10, 27: 0x80},
          "item_type -> weapon_req bit: axe, daggers, hammer, sword",
          str(authsrv.WEAPON_TYPE_REQ_BIT))
    key = authsrv.PARTY_WEAPON_ITEMS.get(
        authsrv.PARTY_WEAPON_BY_PROFESSION.get(7))
    check(key == "starter_daggers"
          and agents.item_template(key)["item_type"] == 32,
          "a profession-7 party body resolves a weapon item (it resolved "
          "None before today)", str(key))
    for sid, means in ((780, "+ Damage"), (775, "+ Damage"), (781, "+ Damage"),
                       (782, "Bleeding")):
        row = agents.WORLD.get("skill_effect", str(sid))
        check(row.get("scale_means") == means,
              f"skill_effect.{sid} says its scale slot is {means!r}")


def _saved(authsrv):
    return (authsrv.SPAWN_PROFESSION, authsrv.PLAYER_ENERGY_PIPS,
            agents.PLAYER_ENERGY, agents.PLAYER_FLOAT_43,
            agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND,
            authsrv.PLAYER_SWING_DAMAGE, authsrv.WEAPON_ATTACK_SPEED,
            authsrv.ATTACK_INTERVAL, authsrv.PARTY_SKILLBAR,
            agents.PLAYER_LEVEL, agents.PLAYER_HEALTH,
            agents.PLAYER_ATTRIBUTE_RANKS, agents.PLAYER_ATTRIBUTE_POINTS)


def _restore(authsrv, saved):
    (authsrv.SPAWN_PROFESSION, authsrv.PLAYER_ENERGY_PIPS,
     agents.PLAYER_ENERGY, agents.PLAYER_FLOAT_43,
     agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND,
     authsrv.PLAYER_SWING_DAMAGE, authsrv.WEAPON_ATTACK_SPEED,
     authsrv.ATTACK_INTERVAL, authsrv.PARTY_SKILLBAR,
     agents.PLAYER_LEVEL, agents.PLAYER_HEALTH,
     agents.PLAYER_ATTRIBUTE_RANKS, agents.PLAYER_ATTRIBUTE_POINTS) = saved


def section_party():
    import authsrv
    import pools
    print("\n3. [party.daggers]: the profession knob and its pool (DAGGERS-B3)")
    base = (authsrv.SPAWN_PROFESSION, agents.PLAYER_ENERGY,
            authsrv.PLAYER_ENERGY_PIPS)
    changed = authsrv.apply_party_character(agents.WORLD.get("party", "daggers"))
    check(base == (1, 25, 3) and authsrv.SPAWN_PROFESSION == 7,
          "the base fixture is a Warrior on the 25 / 3-pip pool; the row makes "
          "the character profession 7", f"base {base}, changed {changed}")
    check(agents.PLAYER_ENERGY == 25 and authsrv.PLAYER_ENERGY_PIPS == 4
          and agents.PLAYER_FLOAT_43 == pools.wire_regen_rate(4, 25)
          and abs(agents.PLAYER_FLOAT_43 - 0.0528) < 5e-5,
          "25 energy at 4 pips, the property-43 rate DERIVED from the pair: "
          "0.0528, the rate the owner's own Assassin ran at on retail "
          "(20260817T183756, pools.py)", f"{agents.PLAYER_FLOAT_43!r}")
    check(authsrv.PLAYER_SWING_DAMAGE == (1, 3)
          and round(authsrv.ATTACK_INTERVAL, 3) == 1.33
          and agents.PLAYER_WEAPON["item_type"] == 32
          and agents.PLAYER_OFFHAND is None
          and authsrv.player_weapon_rank({}) == 3,
          "it holds the daggers and NOTHING in the off hand: 1-3 at 1.33 s, "
          "weapon rank Dagger Mastery 3",
          f"{authsrv.PLAYER_SWING_DAMAGE}, {authsrv.ATTACK_INTERVAL}, rank "
          f"{authsrv.player_weapon_rank({})}")
    check(authsrv.default_skillbar()[:4] == [LEAD, OFF, DUAL, AFTER_DUAL],
          "and its bar opens with a whole chain", str(authsrv.default_skillbar()))
    try:
        authsrv.apply_party_character({"player_profession": 0})
        refused = False
    except ValueError:
        refused = True
    check(refused and authsrv.SPAWN_PROFESSION == 7,
          "a profession the 0x00B7 guard refuses is refused HERE, before it "
          "is bound")


def _world(authsrv):
    entry = {"name": "suit", "dead": False, "died_at": 0.0,
             "health": 400.0, "max_health": 400.0, "last_hit": 0.0,
             "pos": (50.0, 0.0), "plane": 0, "armor_rating": 60.0,
             "allegiance": agents.ALLEGIANCE_HOSTILE,
             "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
             "effects": 0, "attacks_back": False, "skills": (),
             "skill_ready": []}
    return {"agents": {FOE: entry}, "pos": (0.0, 0.0), "player_health": 140.0}


def _land(authsrv, st, skill, target=FOE):
    """One press through the real handler, then the real tick past every
    phase. Returns what went on the wire, in order."""
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))
    authsrv.handle_skill_press([0, skill, 0, target], send, st, 1,
                               authsrv.GAME_CMSG_ATTACK_SKILL)
    for cast in st.get("pending_casts", ()):
        for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
            cast[k] -= 30.0
    st["cast_busy_until"] = 0.0
    for _ in range(3):
        authsrv.cast_tick(send, st, 1)
    # A dual's second strike is half a REAL second behind its first: rewind
    # that too, and let the tick land it and close the cycle.
    for cast in st.get("pending_casts", ()):
        if cast.get("second_at") is not None and not cast.get("second_done"):
            for k in ("second_at", "e3_at", "e6_at"):
                cast[k] -= 30.0
    for _ in range(3):
        authsrv.cast_tick(send, st, 1)
    return sent


def _damage_words(sent):
    return [v for op, v in sent
            if op == 0x00A3 and v[0] in (agents.PROP_DAMAGE, agents.GV_CRITICAL)]


def _index(sent, pred):
    return next((i for i, (op, v) in enumerate(sent) if pred(op, v)), None)


def section_weapon_gate(have_fields):
    import authsrv
    print("\n4. the weapon gate (DAGGERS-B4)")
    if not have_fields:
        LEDGER.skip("section 4",
                    "the skills rows carry no weapon_req (the vault table predates DAGGERS-B1) -- 5 checks")
        return
    hammer = agents.item_template("starter_hammer")
    held = agents.PLAYER_WEAPON
    try:
        agents.PLAYER_WEAPON = hammer
        check(not authsrv.weapon_satisfies(OFF) and authsrv.weapon_satisfies(322),
              "a hammer satisfies Power Attack's any-melee mask (0xB9) and "
              "not Fox Fangs's daggers (0x08)")
        sent = _land(authsrv, _world(authsrv), OFF)
        check([op for op, _ in sent] == [E2],
              "Fox Fangs pressed with a hammer in hand: the bare release and "
              "NOTHING else -- no 0x00E4, no energy, no cast (RECONSTRUCTION: "
              "retail's answer is not observed)", str([hex(o) for o, _ in sent]))
        authsrv.WEAPON_GATE = False
        sent = _land(authsrv, _world(authsrv), OFF)
        check(E4 in [op for op, _ in sent],
              "--no-weapon-gate: the same press is accepted (the arm before "
              "today)")
    finally:
        authsrv.WEAPON_GATE = True
        agents.PLAYER_WEAPON = held
    check(authsrv.weapon_satisfies(OFF) and authsrv.weapon_satisfies(322),
          "with the daggers held both are satisfied -- daggers are a melee "
          "weapon under 0xB9")
    saved_equip = authsrv.EQUIP_WEAPON
    try:
        authsrv.EQUIP_WEAPON = False
        check(not authsrv.weapon_satisfies(322) and authsrv.weapon_satisfies(2),
              "an unarmed character satisfies no weapon mask, and a skill "
              "that asks for no weapon is untouched")
    finally:
        authsrv.EQUIP_WEAPON = saved_equip


def section_chain(have_fields):
    import authsrv
    print("\n5. the chain through the real press and the real landing "
          "(DAGGERS-B5)")
    if not have_fields:
        LEDGER.skip("section 5",
                    "the skills rows carry no combo / combo_req (the vault table predates DAGGERS-B1) -- 17 checks")
        return
    saved_cost, saved_blocks = authsrv.skill_cost, authsrv.blocks
    try:
        # ---- the COLD off-hand: retail's batch, in retail's order ----------
        st = _world(authsrv)
        sent = _land(authsrv, st, OFF)
        ops = [op for op, _ in sent]
        i_e5 = _index(sent, lambda o, v: o == E5 and v[1] == OFF and v[3] == 3)
        i_46 = _index(sent, lambda o, v: o == 0x009F
                      and v[:2] == [agents.GV_ATTACK_SKILL_FINISHED, PLAYER])
        i_38 = _index(sent, lambda o, v: o == 0x00A0
                      and v == [agents.GV_ATTACK_FAIL, FOE, PLAYER, 2])
        i_e5z = _index(sent, lambda o, v: o == E5 and v[1] == OFF and v[3] == 0)
        i_e3 = _index(sent, lambda o, v: o == E3 and v[1] == OFF)
        check(None not in (i_e5, i_46, i_38, i_e5z, i_e3)
              and i_e5 < i_46 < i_38 < i_e5z < i_e3,
              "a cold Fox Fangs: 0x00E5 with the recharge (3), the close (46), "
              "[38, target, player, 2], a SECOND 0x00E5 with recharge 0, then "
              "0x00E3 -- retail's batch at 236.303 of 20260819T132414, in its "
              "order", f"{(i_e5, i_46, i_38, i_e5z, i_e3)}")
        check(_damage_words(sent) == [] and COMBO not in ops and E6 not in ops
              and st["agents"][FOE]["health"] == 400.0,
              "and no damage word, no 0x005C, no 0x00E6, the target untouched")
        spends = [v for op, v in sent
                  if op == 0x00A2 and v[0] == agents.GV_ENERGY_SPENT]
        check(len(spends) == 1 and E4 in ops,
              "the press was ACCEPTED and the energy was debited once -- a "
              "failed step still costs (WIKI; -0.20 of 25 on the tape)",
              str(spends))
        check(OFF not in authsrv.recharging_skills(st)
              and not st.get("pending_casts"),
              "the skill is not recharging afterwards and its cycle is closed")
        sent = _land(authsrv, st, OFF)
        check(E4 in [op for op, _ in sent]
              and _index(sent, lambda o, v: o == 0x00A0 and v[0] == 38) is not None,
              "so the re-press is accepted at once and fails the same way")

        # ---- lead -> off-hand -> dual -> the off-hand that follows a dual --
        authsrv.skill_cost = lambda sid: (0, 0)
        st = _world(authsrv)
        states, fails = [], []
        for skill, want in ((LEAD, 1), (OFF, 2), (DUAL, 3), (AFTER_DUAL, 2),
                            (DUAL, 3)):
            sent = _land(authsrv, st, skill)
            i_c = _index(sent, lambda o, v: o == COMBO)
            i_d = _index(sent, lambda o, v: o == 0x00A3 and v[0] in
                         (agents.PROP_DAMAGE, agents.GV_CRITICAL))
            i_5 = _index(sent, lambda o, v: o == E5 and v[1] == skill)
            i_3 = _index(sent, lambda o, v: o == E3 and v[1] == skill)
            states.append((skill, sent[i_c][1] if i_c is not None else None))
            fails += [v for op, v in sent if op == 0x00A0 and v[0] == 38]
            if skill != DUAL:
                check(i_c is not None and sent[i_c][1] == [PLAYER, FOE, want]
                      and None not in (i_d, i_5, i_3) and i_5 < i_c < i_d < i_3
                      and len(_damage_words(sent)) == 1,
                      f"skill {skill} lands ONCE: 0x005C [player, target, "
                      f"{want}] between its 0x00E5 and its damage word, "
                      f"0x00E3 last (retail's order, 314.733 of RUN-DAGGERS-1)",
                      f"{(i_5, i_c, i_d, i_3)}")
                continue
            words = [i for i, (o, v) in enumerate(sent) if o == 0x00A3
                     and v[0] in (agents.PROP_DAMAGE, agents.GV_CRITICAL)]
            i_47 = _index(sent, lambda o, v: o == 0x009F
                          and v == [agents.GV_DUAL_SECOND_STRIKE, PLAYER, 0])
            i_46 = _index(sent, lambda o, v: o == 0x009F
                          and v[:2] == [agents.GV_ATTACK_SKILL_FINISHED, PLAYER])
            check(len(words) == 2 and None not in (i_5, i_46, i_47, i_c, i_3)
                  and i_5 < i_46 < words[0] < i_47 < words[1] < i_c < i_3
                  and sent[i_c][1] == [PLAYER, FOE, 3],
                  "the DUAL strikes TWICE: 0x00E5, 46, the first word; then "
                  "[47, player, 0], the second word, 0x005C [.., 3] BEHIND "
                  "it, and the 0x00E3 last -- retail's two batches at 316.425 "
                  "and 316.929, 7 of 7",
                  f"{(i_5, i_46, words, i_47, i_c, i_3)}")
        check(fails == [] and len(states) == 5,
              "Moebius Strike after a landed dual, and the dual after it, "
              "never fail -- the requirement reads the state the dual set",
              str(states))

        # ---- the RE-LEAD: nothing on the wire, and the clock restarts -------
        st = _world(authsrv)
        _land(authsrv, st, LEAD)
        authsrv.player_chain(st).rows[FOE]["until"] -= 8.0
        aged = authsrv.player_chain(st).rows[FOE]["until"]
        sent = _land(authsrv, st, LEAD)
        check(COMBO not in [op for op, _ in sent]
              and len(_damage_words(sent)) == 1
              and authsrv.player_chain(st).rows[FOE]["until"] > aged + 7.0,
              "a second lead on a target already at 1: a hit, NO 0x005C, and "
              "the clock restarted -- retail's 404.246 and 412.539, whose 0 "
              "came 15.000 s after the THIRD lead")

        # ---- a cold DUAL fails twice ----------------------------------------
        st = _world(authsrv)
        sent = _land(authsrv, st, DUAL)
        f = [i for i, (o, v) in enumerate(sent)
             if o == 0x00A0 and v == [agents.GV_ATTACK_FAIL, FOE, PLAYER, 2]]
        i_e5z = _index(sent, lambda o, v: o == E5 and v[1] == DUAL and v[3] == 0)
        i_47 = _index(sent, lambda o, v: o == 0x009F
                      and v == [agents.GV_DUAL_SECOND_STRIKE, PLAYER, 0])
        i_e3 = _index(sent, lambda o, v: o == E3 and v[1] == DUAL)
        check(len(f) == 2 and None not in (i_e5z, i_47, i_e3)
              and f[0] < i_e5z < i_47 < f[1] < i_e3
              and _damage_words(sent) == [] and COMBO not in [o for o, _ in sent],
              "a cold Death Blossom: the fail word and the zeroed recharge, "
              "then [47] and a SECOND fail word, then 0x00E3 -- retail's "
              "473.315 / 473.824, 4 of 4 (WIKI: a failed dual still makes "
              "two attacks)", f"{(f, i_e5z, i_47, i_e3)}")

        # ---- a lead that does not HIT advances nothing ---------------------
        st = _world(authsrv)
        authsrv.blocks = lambda state, tid: True
        sent = _land(authsrv, st, LEAD)
        authsrv.blocks = saved_blocks
        check(COMBO not in [op for op, _ in sent]
              and authsrv.player_chain(st).state_on(FOE, time.time()) == 0,
              "a BLOCKED lead sets no state ('if it hits'; n = 0 on retail, "
              "no lead ever failed there)")
        sent = _land(authsrv, st, OFF)
        check(_index(sent, lambda o, v: o == 0x00A0 and v[:1] == [38]
                     and v[3] == 2) is not None,
              "so the off-hand behind it fails")

        # ---- the clock, and the target's death -----------------------------
        st = _world(authsrv)
        _land(authsrv, st, LEAD)
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))
        authsrv.chain_tick(send, st, 1)
        check(sent == [], "a live icon draws nothing from the tick")
        authsrv.player_chain(st).rows[FOE]["until"] -= chain.CHAIN_SECONDS
        authsrv.chain_tick(send, st, 1)
        authsrv.chain_tick(send, st, 1)
        check(sent == [(COMBO, [PLAYER, FOE, 0])],
              "when the clock runs out: ONE [player, target, 0] (retail: "
              "15.66 s after the set, on the one target that lived)", str(sent))
        _land(authsrv, st, LEAD)
        sent.clear()
        authsrv.kill_agent(send, st, FOE, st["agents"][FOE], 1, time.time(),
                           reward=False)
        check((COMBO, [PLAYER, FOE, 0]) in sent,
              "the target DIES with an icon on it: the 0 rides its death "
              "(retail, 6 of 6 short lifetimes end on the dead bit)")
        sent.clear()
        authsrv.kill_agent(send, st, FOE, st["agents"][FOE], 1, time.time(),
                           reward=False)
        check(COMBO not in [op for op, _ in sent],
              "and a target with no icon draws no 0x005C at its death")

        # ---- the revert ----------------------------------------------------
        authsrv.CHAIN_STATE = False
        st = _world(authsrv)
        sent = _land(authsrv, st, OFF)
        check(COMBO not in [op for op, _ in sent] and len(_damage_words(sent)) == 1
              and _index(sent, lambda o, v: o == 0x00A0 and v[:1] == [38]) is None,
              "--no-chain-state: a cold Fox Fangs lands its damage, no fail "
              "word, no 0x005C (the arm before today)")
    finally:
        authsrv.CHAIN_STATE = True
        authsrv.skill_cost, authsrv.blocks = saved_cost, saved_blocks


def section_second_strike_and_crits(have_fields):
    import authsrv
    print("\n7. the double strike and Critical Strikes (DAGGERS-B6/B7)")
    if not have_fields:
        LEDGER.skip("section 7", "no skills rows -- 10 checks")
        return
    check(abs(authsrv.double_strike_chance({}) - (0.02 + 0.02 * 3)) < 1e-9,
          "daggers at Dagger Mastery 3 double 8 % of the time (WIKI: 2 % + "
          "2 % a rank; retail doubled 16 of 65 at rank 12, 24.6 % against 26)",
          str(authsrv.double_strike_chance({})))
    held = agents.PLAYER_WEAPON
    agents.PLAYER_WEAPON = agents.item_template("starter_hammer")
    check(authsrv.double_strike_chance({}) == 0.0, "and a hammer never does")
    agents.PLAYER_WEAPON = held
    check([authsrv.critical_strikes_energy(r) for r in (0, 2, 3, 7, 8, 12, 13, 18)]
          == [0, 0, 1, 1, 2, 2, 3, 4],
          "energy per critical by rank: WIKI's table, and retail's +2 at "
          "rank 8 (26 of 26)")
    saved = (authsrv.double_strike_chance, authsrv.critical_rate,
             authsrv.critical_strikes_rank)
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, list(vals)))
    try:
        # a swing that doubles, neither strike critical
        authsrv.double_strike_chance = lambda state: 1.0
        authsrv.critical_rate = lambda rank: 0.0
        authsrv.critical_strikes_rank = lambda state: 0
        st = _world(authsrv)
        authsrv._land_player_swing(send, st, 1, {"target": FOE})
        first = list(sent)
        authsrv.second_strike_tick(send, st, 1)
        check(len(_damage_words(first)) == 1 and sent == first
              and st.get("player_second_strike") is not None,
              "the first dagger lands one word and ARMS the second -- nothing "
              "more goes out until its half second is up")
        st["player_second_strike"]["at"] -= authsrv.SECOND_STRIKE_S
        authsrv.second_strike_tick(send, st, 1)
        tail = sent[len(first):]
        check([op for op, _ in tail[:1]] == [0x009F]
              and tail[0][1] == [agents.GV_DOUBLE_STRIKE, PLAYER, 0]
              and len(_damage_words(tail)) == 1
              and not any(o == 0x00A0 and v[0] == agents.GV_ATTACK_STARTED
                          for o, v in tail)
              and not any(o == 0x009F and v[0] == agents.GV_MELEE_ATTACK_FINISHED
                          for o, v in tail),
              "then [2, player, 0] and the second word, with NO start and NO "
              "close of its own -- retail's second-strike batch, 16 of 16",
              str([(hex(o), v) for o, v in tail]))
        n = len(sent)
        authsrv.second_strike_tick(send, st, 1)
        check(len(sent) == n, "and it lands once")
        # a critical at Critical Strikes 8
        authsrv.double_strike_chance = lambda state: 0.0
        authsrv.critical_rate = lambda rank: 1.0
        authsrv.critical_strikes_rank = lambda state: 8
        st = _world(authsrv)
        pool = authsrv.player_energy(st)
        pool.current = 10.0
        del sent[:]
        authsrv._land_player_swing(send, st, 1, {"target": FOE})
        i52 = _index(sent, lambda o, v: o == 0x00A3
                     and v[:3] == [agents.GV_ENERGY_GAIN, PLAYER, PLAYER])
        i54 = _index(sent, lambda o, v: o == 0x00A0
                     and v == [agents.PROP_ENERGY_GAIN_CALLOUT, PLAYER, PLAYER, 2])
        i17 = _index(sent, lambda o, v: o == 0x00A3 and v[0] == agents.GV_CRITICAL)
        check(None not in (i52, i54, i17) and i52 < i54 < i17,
              "a critical at rank 8: 0x00A3 [52, player, player, fraction], "
              "0x00A0 [54, player, player, 2], THEN the critical's word -- "
              "retail's order, 26 of 26", f"{(i52, i54, i17)}")
        import struct
        got = struct.unpack("<f", struct.pack("<I", sent[i52][1][3]))[0] \
            if i52 is not None else None
        check(got is not None and abs(got - 2 / pool.maximum) < 1e-6
              and abs(pool.current - 12.0) < 0.2,
              "the fraction is 2 of the maximum (retail: +0.08 of 25) and the "
              "pool holds 2 more", f"{got}, pool {pool.current:.2f}")
        authsrv.CRITICAL_STRIKES = False
        del sent[:]
        authsrv._land_player_swing(send, _world(authsrv), 1, {"target": FOE})
        check(_index(sent, lambda o, v: o == 0x00A3
                     and v[0] == agents.GV_ENERGY_GAIN) is None,
              "--no-critical-strikes: a critical pays nothing")
        authsrv.CRITICAL_STRIKES = True
        authsrv.SECOND_STRIKE = False
        authsrv.double_strike_chance = lambda state: 1.0
        st = _world(authsrv)
        authsrv._land_player_swing(send, st, 1, {"target": FOE})
        check(st.get("player_second_strike") is None,
              "--no-second-strike: a swing arms nothing")
    finally:
        authsrv.CRITICAL_STRIKES = authsrv.SECOND_STRIKE = True
        (authsrv.double_strike_chance, authsrv.critical_rate,
         authsrv.critical_strikes_rank) = saved


def section_retail(have_fields):
    """RUN-DAGGERS-1 through chainjoin.py. Pinned BY TAPE NAME and exactly --
    one tape cannot grow -- so the next dagger capture adds to the corpus
    without reddening this; a changed number here means the JOIN changed."""
    print("\n8. retail's own wire: RUN-DAGGERS-1, 20260917T160915 (chainjoin)")
    import vaultpath
    tape_dir = None
    try:
        tape_dir = os.path.join(vaultpath.require_dir("captures", "live"),
                                "20260917T160915")
    except (Exception, SystemExit):                            # noqa: BLE001
        pass
    if not have_fields or tape_dir is None or not os.path.isdir(tape_dir):
        LEDGER.skip("section 8",
                    "needs the vault's skills rows and the live capture 20260917T160915 -- 8 checks")
        return
    import chainjoin
    got = chainjoin.summary(chainjoin.census("20260917T160915"))
    check(got["chain_messages"] == 24
          and got["states"] == {1: 7, 2: 7, 3: 7, 0: 3},
          "24 x 0x005C: seven leads, seven off-hands, seven duals, three clears",
          f"{got['chain_messages']} {got['states']}")
    check(got["clears_since_hit"] == [15.0, 15.0, 15.0]
          and got["clears_since_set"] == [15.0, 15.0, 31.442],
          "every clear is 15.000 s after the LAST chain hit -- and one of them "
          "31.4 s after its set, which is the re-lead restarting the clock",
          f"{got['clears_since_hit']} / {got['clears_since_set']}")
    check(got["releads"] == 2 and got["releads_resent"] == 0,
          "2 leads landed on a target already at 1 and NEITHER re-sent a state")
    check(got["duals_landed"] == 7 and got["duals_two_words"] == 7
          and got["duals_state3_with_second"] == 7
          and got["duals_marker47"] == 11
          and 0.45 < got["dual_gap"][0] and got["dual_gap"][1] < 0.55,
          "7 duals landed: two words each, 0.487-0.504 s apart, the state 3 "
          "riding the SECOND; [47] opens the second strike on all 11, landed "
          "or failed", str({k: got[k] for k in ("duals_landed", "dual_gap",
                                                "duals_marker47")}))
    check(got["duals_adjacent"] == 28 and got["adjacent_values"] == [-0.0833],
          "and each strike dealt the two ADJACENT foes -40/480 on property 55 "
          "-- 28 words, armour-ignoring, never a critical")
    check(got["cold"] == 12 and got["cold_zeroed"] == 12
          and got["cold_by_fails"] == {1: 8, 2: 4},
          "12 cold presses, 12 zeroed recharges: 8 off-hands with one fail "
          "word, 4 duals with two")
    check(got["plain_swings"] == 64 and got["double_strikes"] == 16
          and got["double_marker2"] == 16 and got["double_close_on_first"] == 16
          and got["double_close_on_second"] == 0
          and abs(got["double_gap"][1] - 0.5) < 0.01
          and abs(got["next_start_after_double"] - got["next_start_after_single"]) < 0.02,
          "16 of 64 plain swings doubled (25 %; WIKI 26 % at rank 12): [2] "
          "opens the second word 0.500 s behind the first, the close rode the "
          "FIRST, and the next start is not delayed",
          str({k: got[k] for k in ("double_gap", "next_start_after_single",
                                   "next_start_after_double")}))
    check(got["crits"] == 26 and got["crits_with_gain"] == 26
          and got["crits_ordered"] == 26 and got["crit_gains"] == {(0.08, 2): 26},
          "26 criticals, 26 x [52, self, self, +0.08] then [54, self, self, 2] "
          "ahead of the word")


def section_adjacent(have_fields):
    import authsrv
    print("\n9. an attack skill's ADJACENT damage (DAGGERS-B8)")
    if not have_fields or authsrv.skill_adjacent_damage(DUAL, 12) is None:
        LEDGER.skip("section 9", "the skills rows carry no aoe_range (the vault "
                    "table predates DAGGERS-B8) -- 8 checks")
        return
    check(authsrv.skill_adjacent_damage(DUAL, 12) == (40.0, 156.0),
          "Death Blossom at rank 12: 40 points inside 156 u -- the client's own "
          "interpolator and its own aoe_range, and 40 is the -40/480 of all 28 "
          "adjacent words on RUN-DAGGERS-1. Derived, not typed",
          str(authsrv.skill_adjacent_damage(DUAL, 12)))
    check(authsrv.skill_adjacent_damage(OFF, 12) is None
          and authsrv.skill_adjacent_damage(LEAD, 12) is None,
          "a skill whose row does not opt in deals none, whatever its radius")

    def _crowd():
        st = _world(authsrv)
        base = st["agents"][FOE]
        # retail's geometry: two bodies 78 u and 94 u from the target -- plus
        # one past the radius, a corpse inside it, and an ally inside it.
        for aid, pos, over in ((11, (50.0 + 78.0, 0.0), {}),
                               (12, (50.0, 94.0), {}),
                               (13, (50.0 + 200.0, 0.0), {}),
                               (14, (50.0, -60.0), {"dead": True, "health": 0.0}),
                               (15, (50.0, 60.0),
                                {"allegiance": agents.ALLEGIANCE_PLAYER})):
            st["agents"][aid] = {**base, "pos": pos, "health": 480.0,
                                 "max_health": 480.0, **over}
        return st

    saved_cost = authsrv.skill_cost
    authsrv.skill_cost = lambda sid: (0, 0)
    try:
        st = _crowd()
        _land(authsrv, st, LEAD)
        _land(authsrv, st, OFF)
        sent = _land(authsrv, st, DUAL)
        adj = [(i, v) for i, (o, v) in enumerate(sent)
               if o == 0x00A3 and v[0] == agents.GV_ARMOR_IGNORING]
        words = [i for i, (o, v) in enumerate(sent) if o == 0x00A3
                 and v[0] in (agents.PROP_DAMAGE, agents.GV_CRITICAL)]
        i_47 = _index(sent, lambda o, v: o == 0x009F
                      and v == [agents.GV_DUAL_SECOND_STRIKE, PLAYER, 0])
        i_c = _index(sent, lambda o, v: o == COMBO and v[2] == 3)
        check([v[1] for _i, v in adj] == [11, 12, 11, 12]
              and all(v[2] == PLAYER for _i, v in adj),
              "the two bodies inside the radius each take a [55, body, player, "
              "-f] on EACH strike -- four words; the far one, the corpse and "
              "the ally take none", str([v[:3] for _i, v in adj]))
        import struct
        vals = {round(struct.unpack("<f", struct.pack("<I", v[3]))[0], 4)
                for _i, v in adj}
        rank3 = authsrv.skill_adjacent_damage(DUAL, 3)[0]
        check(vals == {round(-rank3 / 480.0, 4)}
              and st["agents"][11]["health"] == 480.0 - 2 * rank3
              and st["agents"][13]["health"] == 480.0,
              "every word is the skill's own number over the body's maximum, "
              "identical on both strikes (armour-ignoring, never critical), and "
              "the books agree", f"{vals}, body 11 at {st['agents'][11]['health']}")
        check(len(words) == 2 and len(adj) == 4 and None not in (i_47, i_c)
              and words[0] < adj[0][0] < adj[1][0] < i_47 < words[1]
              < adj[2][0] < adj[3][0] < i_c,
              "retail's order: the word, the 55s; then [47], the word, the 55s, "
              "and the 0x005C behind them (316.425 / 316.929)",
              f"{(words, [i for i, _v in adj], i_47, i_c)}")
        maxima = [v for o, v in sent if o == 0x009F
                  and v[0] == agents.PROP_HEALTH_MAX and v[1] in (11, 12)]
        check(maxima == [],
              "no maximum is re-declared for a body whose maximum never moved "
              "(ours declares it at the create; retail's [42] rode the FIRST "
              "adjacent word on each body and none of the 13 after)", str(maxima))
        st["agents"][11]["max_declared_on_hit"] = None      # it moved
        _land(authsrv, st, LEAD)
        _land(authsrv, st, OFF)
        sent = _land(authsrv, st, DUAL)
        maxima = [v for o, v in sent if o == 0x009F
                  and v[0] == agents.PROP_HEALTH_MAX and v[1] in (11, 12)]
        check(maxima == [[agents.PROP_HEALTH_MAX, 11, 480]],
              "a body whose maximum MOVED gets it declared once, ahead of its "
              "first adjacent word, and not on the second strike", str(maxima))
        # a cold dual reaches nobody
        st = _crowd()
        sent = _land(authsrv, st, DUAL)
        check(not any(o == 0x00A3 and v[0] == agents.GV_ARMOR_IGNORING
                      for o, v in sent) and st["agents"][11]["health"] == 480.0,
              "a FAILED dual deals no adjacent damage ('if it hits')")
        authsrv.AREA_DAMAGE = False
        st = _crowd()
        _land(authsrv, st, LEAD)
        _land(authsrv, st, OFF)
        sent = _land(authsrv, st, DUAL)
        check(not any(o == 0x00A3 and v[0] == agents.GV_ARMOR_IGNORING
                      for o, v in sent) and len(_damage_words(sent)) == 2,
              "--no-area-damage: the dual still strikes twice and nobody "
              "beside the target is touched (the arm before today)")
    finally:
        authsrv.AREA_DAMAGE = True
        authsrv.skill_cost = saved_cost


def section_condition_slot(have_fields):
    import authsrv
    print("\n6. Jagged Strike's Bleeding sits in the SCALE slot")
    if not have_fields:
        LEDGER.skip("section 6", "no skills rows -- 2 checks")
        return
    got = authsrv.skill_condition(LEAD, 3)
    check(got is not None and got[0] == 478 and got[1] == 8.0,
          "skill_condition(782, rank 3) = Bleeding for 5 + 15 x 3/15 = 8 s, "
          "read from `scale_means` because its bonus slot is empty", str(got))
    check(authsrv.skill_condition(382, 3) is not None
          and authsrv.skill_damage(LEAD, 3) is None,
          "Sever Artery still reads its bonus slot, and a scale slot naming a "
          "condition is never damage")


def main():
    import authsrv
    section_grammar()
    section_content()
    have_fields = authsrv.skill_chain_fields(OFF) == (2, 0x02, 0x08)
    saved = _saved(authsrv)
    try:
        section_party()
        section_weapon_gate(have_fields)
        section_chain(have_fields)
        section_condition_slot(have_fields)
        section_second_strike_and_crits(have_fields)
        section_retail(have_fields)
        section_adjacent(have_fields)
    finally:
        _restore(authsrv, saved)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
