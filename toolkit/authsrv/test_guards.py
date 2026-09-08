"""The guard contract: a refused value refuses BEFORE anything is sent or changed.

`_fraction` is the wire's last line of defense -- the client dies on
`fraction <= 1.0f` (CharPool.cpp:84) two seconds after a bad float, with no
server-side symptom. But a guard that fires AFTER the first send has already
half-happened: the refusal leaves a partial effect burst on the wire (an
attack with no damage, a revive with no refill), and on the CONNECTION thread
an escaping ValueError goes further -- `handle`'s except tuple is
ConnectionError/socket.timeout/OSError only, so the raise runs the `finally`,
closes the socket, and the client is disconnected by a number that was never
sent.

All of that is DORMANT today: every `_fraction` call site passes a fixed
constant inside [-1, 1]. It stops being dormant the day computed per-skill
values arrive (studies/combat/PLAN.md step 8), which is why this contract
lands FIRST (step 2, amendments C4/C8b/C9).

RED-FIRST, per C8b, so the observed failure mode is on record rather than
assumed. Against the pre-guard tree (82854b2), section 1 measured:

    hit_enemy with HIT_FRACTION poisoned to 1.5 raised ValueError only AFTER
    sending GV_ATTACK_STARTED (1 message on the wire) and after consuming the
    swing timer and the target's health (100 -> 0 bookkept, nothing sent).

which is exactly the guard-after-effect shape the gate map calls out. The
checks below assert the DESIRED contract and therefore went red on that tree.
"""

import io
import contextlib
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402

# FLOOR 40, from a green run on 2026-08-15. Was 37 until section 2 was
# rewritten: moving the damage to cast end made the connection thread's
# ValueError contract unreachable, so that section now checks what replaced
# it -- a press opens a cycle and lands nothing -- and carries 5 checks where
# it carried 3, plus section 11's new single-caller check. Nothing here is
# conditional, so a short run means a section stopped rather than passed.
LEDGER = checks.Ledger("guard contract", floor=41)
check = LEDGER.ok


def _fresh_agent():
    return {"name": "target", "dead": False, "last_hit": 0.0,
            "max_health": 100.0, "health": 100.0, "pos": (0.0, 0.0)}


def section_hit_enemy():
    """An out-of-range fraction refuses hit_enemy before ANY effect."""
    import authsrv

    print("1. hit_enemy: guard before effect, both directions of the timer")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {10: _fresh_agent()}, "pos": (0.0, 0.0)}

    saved = authsrv.PLAYER_SWING_DAMAGE
    # NEGATIVE damage -- a heal riding the damage property. This poison was
    # 1.5 when the section was written red-first; amendment C4 then made
    # overkill VALID (clamp-to-kill, section 9), so 1.5 stopped being an
    # error and the invalid shape here had to become one that still is.
    #
    # AND IT MOVED 2026-08-20, from HIT_FRACTION to PLAYER_SWING_DAMAGE. The
    # player's swing stopped being a fraction of the target's max health and
    # became the equipped weapon's own damage range, read out of its 584
    # modifier word. Poisoning the constant the code no longer reads is a
    # guard test that cannot fail -- it went green on a tree where the guard
    # was never reached, which is the exact defect this file exists to catch.
    authsrv.PLAYER_SWING_DAMAGE = (-150, -150)
    try:
        raised = False
        try:
            authsrv.hit_enemy(send, state, 10, 0)
        except ValueError:
            raised = True
        check(raised, "an invalid computed damage still raises ValueError",
              "the guard is a refusal, not a silent clamp -- negative "
              "damage on the damage property would be a heal")
        check(sent == [], "and NOTHING was sent first",
              f"sent={sent!r} -- on the pre-guard tree this held "
              f"GV_ATTACK_STARTED, an attack opened on the wire with no "
              f"damage and no close ever coming")
        agent = state["agents"][10]
        check(agent["health"] == 100.0, "the target's health is untouched",
              f"health={agent['health']} -- the pre-guard tree bookkept "
              f"100 -> 0 while sending nothing, a kill the wire never saw")
        check(agent["last_hit"] == 0.0, "and the swing timer is unconsumed",
              "a refused swing must be retryable next tick, not eaten")
    finally:
        authsrv.PLAYER_SWING_DAMAGE = saved

    # The control: with the real constant the same call sends the whole
    # swing. A guard that refuses everything would pass every check above.
    sent.clear()
    state["agents"][10] = _fresh_agent()
    authsrv.hit_enemy(send, state, 10, 0)
    ops = [op for op, _, _ in sent]
    # 4 = the swing trio, plus the 0x00CF the landed WEAPON hit earns. It was
    # 3 until 2026-08-21 put the adrenaline family on the wire; the count is
    # spelled out rather than left bare so the next change names itself here.
    #
    # THE GAIN SITS IMMEDIATELY BEFORE THE DAMAGE, which is measured and was
    # briefly pinned the other way round. Over the 49 live connections the
    # message immediately after a 0x00CF is the damage (163/prop 16-or-17) 601
    # times of 663, and the one before it is 159/prop 1 594 of 663 -- modal
    # batch [159/prop1, 207, 163/prop16, 30], n=425. This check first shipped
    # asserting the gain was LAST "because a hit has to land before it earns
    # one", which is a plausible story about a sequence ArenaNet does not send.
    # 4 since ANIMREF-RE 35, and the history is the point. It was 4, then 5
    # from 2026-08-22 when the [8 -> 1] action hold was added "behind the
    # STARTED (castmech 3c)", and now 4 again. THE ADDITION READ A DENOMINATOR
    # BACKWARDS: castmech 3c censuses the prop-8 HOLDS and says 4 of 4 of them
    # rode an ATTACK_STARTED -- an ORDER fact about the holds observed. We read
    # it as a RATE over the starts and sent one on every swing. Retail's real
    # rate is 83 of 1,332 attack starts (6.2%); ours was 52 of 52 (100%), and
    # the cost was the client's walk gate shut for every swing.
    check(len(sent) == 4
          and ops.index(authsrv.AGENT_ADRENALINE_GAIN)
              == ops.index(authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET) - 1,
          "control: the in-range path still sends the swing, gain before damage",
          f"{len(sent)} messages: {ops} -- retail puts the 0x00CF between the "
          f"attack marker and the damage, 601 of 663 by the following message")
    lo, hi = authsrv.PLAYER_SWING_DAMAGE
    left = state["agents"][10]["health"]
    check(100.0 - hi <= left <= 100.0 - lo,
          "control: and the in-range damage is bookkept",
          f"health={left}, a swing of the hammer's own {lo}-{hi}. A RANGE and "
          f"not an equality, because the roll inside the weapon's range is "
          f"random -- pinning it to one number would be pinning our own roll, "
          f"not ArenaNet's range")


def section_skill_press():
    """A press opens a cycle and lands NOTHING -- the damage waits for E5.

    REWRITTEN 2026-08-15. This section used to assert the connection thread's
    own ValueError contract, because `handle_skill_press` resolved the hit
    synchronously and an escaping refusal there would run `handle`'s finally
    and close the socket. That contract is now unreachable BY CONSTRUCTION:
    the press no longer damages, so nothing on that path can raise. The
    refusal contract moved to the world tick with the damage, where
    `world_tick`'s own except already covers it (section 11 is where the
    two-thread claim now lives).

    So what this section checks is the thing that replaced it: a press is
    ONLY a cycle opening, and the target's health is untouched until the cast
    completes. Deleting the section would have lost that; keeping the old
    assertions would have tested a path that no longer exists.
    """
    import authsrv

    print("\n2. handle_skill_press: opens the cycle, lands nothing yet")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    agent = _fresh_agent()
    state = {"agents": {10: agent}, "pos": (0.0, 0.0)}
    # SKILL 322 (Power Attack), NOT AN ARBITRARY ID, and it went from 42 to
    # this on 2026-08-20 when the cast path started dispatching on the skill's
    # TYPE. Before that, any skill with a target swung the player's hammer --
    # which is why casting a hex produced `attack_started: player swings at 10`
    # in a real run. Now only an ATTACK skill (type_code 14) rides a swing, so
    # a made-up id resolves to nothing and this section's real subject -- that
    # the damage lands at E5 rather than at the press -- would silently stop
    # being tested. Power Attack is an attack, has "+ Damage" and is on our own
    # bar, so the timing claim is exercised against a skill that really swings.
    press = [0, 322, 7, 10]  # header slot, skill 322, copy 7, target agent 10

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        authsrv.handle_skill_press(press, send, state, 0,
                                   authsrv.GAME_CMSG_USE_SKILL)
    ops = [op for op, _, _ in sent]
    # THE THIRD MESSAGE IS THE ENERGY DEBIT, wired 2026-08-20: Power Attack
    # costs 5 and the corpus puts property 62 within 0.03-0.7 s of the
    # USE_SKILL, so it rides the press burst. The assertion is not weakened --
    # it is still an exact op list, and it still says the damage trio is
    # absent, which is the whole subject of this section.
    check(ops == [authsrv.GAME_SMSG_SKILL_ACTIVATED_BROADCAST,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT],
          "the press sends E4, the energy debit, the cast animation "
          "(retail's batch order: spend before the skill-naming property, "
          "45 of 45), and the [8 -> 1] hold closing the burst -- and NO "
          "damage",
          f"ops={ops} -- until 2026-08-15 this also sent the swing trio, so a "
          f"two-second spell dealt its damage before its own casting "
          f"animation began")
    check(agent["health"] == 100.0 and agent["last_hit"] == 0.0,
          "the target is untouched: no health spent, no swing timer consumed",
          f"health={agent['health']}, last_hit={agent['last_hit']} -- the hit "
          f"has not happened yet, which is what makes a cancel window exist")
    check(len(state["pending_casts"]) == 1
          and state["pending_casts"][0]["target"] == 10,
          "and the pending cast carries the target for cast_tick to resolve",
          f"{state['pending_casts']}")

    # THE HIT ARRIVES WHEN THE CAST COMPLETES. Rewind e5_at rather than
    # sleeping -- the same trick test_castcycle uses, for the same reason.
    state["pending_casts"][0]["e5_at"] = time.time() - 0.001
    sent.clear()
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.cast_tick(send, state, 0)
    ops = [op for op, _, _ in sent]
    check(authsrv.GAME_SMSG_SKILL_RECHARGE in ops
          and authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET in ops,
          "at E5 the cast completes AND the damage lands, same tick",
          f"ops={ops}")
    check(agent["health"] < 100.0,
          "and only now is the target's health spent",
          f"health={agent['health']}")

    # AND THE CONTROL THE TYPE DISPATCH NOW NEEDS: a NON-attack skill aimed at
    # the same agent must not swing at it. This is the check that would have
    # caught the old behaviour, and it could not exist until the fix did.
    sent.clear()
    agent2 = _fresh_agent()
    state2 = {"agents": {10: agent2}, "pos": (0.0, 0.0)}
    with contextlib.redirect_stdout(io.StringIO()):
        authsrv.handle_skill_press([0, 135, 7, 10], send, state2, 0,
                                   authsrv.GAME_CMSG_USE_SKILL)
        state2["pending_casts"][0]["e5_at"] = time.time() - 0.001
        authsrv.cast_tick(send, state2, 0)
    starts = [v for op, v, _l in sent
              if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
              and v[0] == authsrv.agents.GV_ATTACK_STARTED]
    check(not starts and agent2["health"] == 100.0,
          "CONTROL: casting a HEX at the same agent swings nothing at it",
          f"attack_started x{len(starts)}, health={agent2['health']} -- "
          f"Faintheartedness is a Hex Spell, and until 2026-08-20 it made the "
          f"player hit the target with a hammer for 5")


def _refusing_fraction(authsrv):
    """A _fraction stub that refuses everything.

    The tick-side functions pass LITERAL fractions (1.0, -ENEMY_HIT_FRACTION),
    so no constant poison can make the real guard fire -- the stub stands in
    for the day those literals become computed values. What each section
    asserts is placement: when the guard fires, NOTHING has been sent and the
    retry state is intact.
    """
    def stub(x, prop, what):
        raise ValueError(f"stub refusal: {x!r} as property {prop} ({what})")
    return stub


def section_land_swing():
    import authsrv

    print("\n3. land_swing: guard before the finished/damage pair")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}, "pos": (0.0, 0.0)}
    agent = _fresh_agent()

    saved = authsrv._fraction
    authsrv._fraction = _refusing_fraction(authsrv)
    try:
        raised = False
        try:
            authsrv.land_swing(send, state, 10, agent, 0)
        except ValueError:
            raised = True
        check(raised and sent == [],
              "a refused enemy swing raises with NOTHING sent",
              f"raised={raised}, sent={sent!r} -- pre-hoist this held "
              f"MELEE_ATTACK_FINISHED, a landing announced with no damage")
        check(state["player_health"] == float(authsrv.agents.PLAYER_HEALTH),
              "and the player's health is untouched",
              f"health={state['player_health']}")
    finally:
        authsrv._fraction = saved

    sent.clear()
    state["player_health"] = float(authsrv.agents.PLAYER_HEALTH)
    authsrv.land_swing(send, state, 10, agent, 0)
    # 3 since 2026-08-21: finished, the 0x00CF the player earns for the damage
    # TAKEN, then the damage. THIS SITE REPRODUCES RETAIL'S BATCH EXACTLY --
    # [159/prop1, 207, 163/prop16] is the modal shape of all 663 corpus gains
    # (n=425 with the trailing world tick) -- because land_swing already sent
    # the finished marker before the damage.
    #
    # The pin briefly read "appended after the measured sequence, never
    # inserted into it", which had the adrenaline message last. It belongs
    # BETWEEN the two: the measured pair is finished-then-damage and the gain
    # sits inside it, which is what the corpus shows and what this now asserts.
    check(len(sent) == 3 and sent[0][0] ==
          authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
          and sent[1][0] == authsrv.AGENT_ADRENALINE_GAIN
          and sent[2][0] == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
          "control: in-range is retail's own batch -- finished, gain, damage",
          f"{[op for op, _, _ in sent]} -- the finished/damage pair is 6 of 6 "
          f"swings in the Lakeside tape by byte offset (land_swing docstring); "
          f"the gain's position between them is 601 of 663 in the live corpus")


def section_land_skill():
    import authsrv

    print("\n4. land_skill: guard before the cast slot and the health are spent")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}, "pos": (0.0, 0.0)}
    agent = _fresh_agent()
    # 312 Holy Strike, and it must be a real DAMAGE skill for this section to
    # mean anything: since step 8, land_skill returns early on a skill whose
    # scale is not damage, so the synthetic id this used to carry would now
    # skip the guarded path entirely and the section would pass vacuously.
    agent["casting"], agent["skills"] = 0, ((312, 1.0, 20.0),)

    saved = authsrv._fraction
    authsrv._fraction = _refusing_fraction(authsrv)
    try:
        raised = False
        try:
            authsrv.land_skill(send, state, 10, agent, 0)
        except ValueError:
            raised = True
        check(raised and sent == [],
              "a refused enemy skill raises with NOTHING sent",
              f"raised={raised}, sent={sent!r}")
        check(state["player_health"] == float(authsrv.agents.PLAYER_HEALTH),
              "and the player's health was not spent on an unsent message",
              f"health={state['player_health']} -- pre-hoist the pool was "
              f"debited and the cast slot cleared for a damage that never "
              f"went out")
    finally:
        authsrv._fraction = saved

    sent.clear()
    state["player_health"] = float(authsrv.agents.PLAYER_HEALTH)
    agent["casting"] = 0
    authsrv.land_skill(send, state, 10, agent, 0)
    # 3 since ANIMREF-R2 (D19): the property-58 finish OPENS the batch (58
    # leading, 709/709 finished other-agent episodes in the live corpus),
    # then the 0x00CF the player earns for taking the damage, then the
    # damage -- the gain immediately before it, as the corpus puts it (601
    # of 663 by the following message). A CAST grants the caster no strike --
    # that half of the wiki's rule says WEAPON hit -- so the only adrenaline
    # message here is the victim's, and it is the player's own.
    # 4 since ANIMREF-R8: the on-body effect visual rides between the 58 and
    # the target-facing properties, which is retail's own batch shape
    # (['58','21','21','55','55'], R2 sec.9). Skill 312's client row carries a
    # RECIPIENT visual (+0x7c = 556) and no caster one, so exactly one
    # property-20 goes out, naming the player as the recipient and the
    # caster second -- the victim-first order reading B settled.
    vis = [(op, v) for op, v, _ in sent
           if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
           and v[0] == authsrv.agents.GV_EFFECT_ON_TARGET]
    check(len(sent) == 4 and agent["casting"] is None
          and sent[0][0] == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
          and sent[0][1][0] == authsrv.agents.GV_SKILL_FINISHED
          and vis == [(authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET,
                       [authsrv.agents.GV_EFFECT_ON_TARGET,
                        authsrv.PLAYER_AGENT_ID, 10, 556])]
          and sent[2][0] == authsrv.AGENT_ADRENALINE_GAIN,
          "control: in-range lands the skill and clears the slot -- 58 "
          "leading, then the on-body visual, then gain and damage",
          f"{[op for op, _, _ in sent]}, visual={vis}, "
          f"casting={agent['casting']}")


def section_revive_due():
    import authsrv

    print("\n5. revive_due: a refused refill leaves the body DEAD and retryable")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    agent = _fresh_agent()
    agent["dead"], agent["died_at"] = True, 0.0   # long past REVIVE_AFTER
    state = {"agents": {10: agent}}

    saved = authsrv._fraction
    authsrv._fraction = _refusing_fraction(authsrv)
    try:
        raised = False
        try:
            authsrv.revive_due(send, state, 0)
        except ValueError:
            raised = True
        check(raised and sent == [],
              "a refused revive raises with NOTHING sent",
              f"raised={raised}, sent={sent!r} -- pre-hoist the status went "
              f"out first: a body stood up with no bar behind it")
        check(agent["dead"] is True,
              "and the agent is still dead, so next tick retries the WHOLE "
              "revive", f"dead={agent['dead']}")
    finally:
        authsrv._fraction = saved

    sent.clear()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        authsrv.revive_due(send, state, 0)
    revived_ops = [op for op, _, _ in sent]
    check(agent["dead"] is False and len(sent) in (1, 3),
          "control: the in-range revive stands the body up",
          f"dead={agent['dead']}, ops={revived_ops} (1 with the refill "
          f"deferred, 3 with it inline -- REVIVE_REFILL_DEFER decides)")


def section_player_revive_due():
    import authsrv

    print("\n6. player_revive_due: same contract, the player's side")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}, "player_dead": True, "player_died_at": 0.0,
             "player_health": 0.0}

    saved = authsrv._fraction
    authsrv._fraction = _refusing_fraction(authsrv)
    try:
        raised = False
        try:
            authsrv.player_revive_due(send, state, 0)
        except ValueError:
            raised = True
        check(raised and sent == [],
              "a refused player revive raises with NOTHING sent",
              f"raised={raised}, sent={sent!r}")
        check(state["player_dead"] is True,
              "and the player is still dead, retryable next tick",
              f"player_dead={state['player_dead']}")
    finally:
        authsrv._fraction = saved

    sent.clear()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        authsrv.player_revive_due(send, state, 0)
    check(state["player_dead"] is False and len(sent) in (1, 3),
          "control: the in-range revive stands the player up",
          f"player_dead={state['player_dead']}, "
          f"ops={[op for op, _, _ in sent]}")


def section_agent_refill_due():
    import authsrv

    print("\n7. agent_refill_due: a refused refill stays DUE")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    agent = _fresh_agent()
    agent["refill_due_at"] = 1.0   # long past due
    state = {"agents": {10: agent}}

    saved = authsrv._fraction
    authsrv._fraction = _refusing_fraction(authsrv)
    try:
        raised = False
        try:
            authsrv.agent_refill_due(send, state, 0)
        except ValueError:
            raised = True
        check(raised and sent == [] and agent["refill_due_at"] == 1.0,
              "refused: nothing sent, and the refill timer is still armed",
              f"raised={raised}, sent={sent!r}, "
              f"due={agent['refill_due_at']!r} -- pre-hoist the timer was "
              f"disarmed and PROP_HEALTH_MAX sent for a refill that never came")
    finally:
        authsrv._fraction = saved

    sent.clear()
    authsrv.agent_refill_due(send, state, 0)
    check(len(sent) == 2 and agent["refill_due_at"] is None,
          "control: in-range sends both refill halves and disarms",
          f"ops={[op for op, _, _ in sent]}, due={agent['refill_due_at']!r}")


def section_player_refill_due():
    import authsrv

    print("\n8. player_refill_due: same contract, the player's side")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}, "player_refill_due_at": 1.0}

    saved = authsrv._fraction
    authsrv._fraction = _refusing_fraction(authsrv)
    try:
        raised = False
        try:
            authsrv.player_refill_due(send, state, 0)
        except ValueError:
            raised = True
        check(raised and sent == [] and state["player_refill_due_at"] == 1.0,
              "refused: nothing sent, and the refill timer is still armed",
              f"raised={raised}, sent={sent!r}, "
              f"due={state['player_refill_due_at']!r}")
    finally:
        authsrv._fraction = saved

    sent.clear()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        authsrv.player_refill_due(send, state, 0)
    # FIVE MESSAGES SINCE 875ae5a (2026-08-22), four since 2026-08-20: the
    # health pair (max, then the property-34 fraction), then the ENERGY trio --
    # property 52 = 1.0, the int property 54 "+N" callout 875ae5a added in
    # retail's position, and property 43 back to the rate. The batch is retail's
    # resurrect instant, OBSERVED in capture 20260817T183756 (52/43/55) plus
    # retail's [54, 27, 22] callout; test_pools 8b pins its composition, so
    # this count follows restore_player_energy rather than re-pinning it. The
    # contract this section is about is unchanged and still checked: a refused
    # value sends nothing and leaves the timer armed; an accepted one disarms.
    check(len(sent) == 5 and state["player_refill_due_at"] is None,
          "control: in-range sends the full refill batch and disarms",
          f"ops={[op for op, _, _ in sent]}, "
          f"due={state['player_refill_due_at']!r}")


def section_overkill():
    """Amendment C4: overkill is a valid game event, not a wrong number."""
    import authsrv

    print("\n9. overkill clamps to a kill; the true invalids are still refused")
    # The wire value for a clamped kill, pinned as a LITERAL: f32(-1.0) is
    # 0xBF800000. Computing it from authsrv._f32 would let the symbol under
    # test move and the test move with it (TESTS.md's own lesson).
    F32_MINUS_ONE = 0xBF800000

    check(authsrv._damage_fraction(150.0, 100.0, 16, "overkill") ==
          F32_MINUS_ONE,
          "damage past the whole pool goes out as exactly -1.0",
          "raw _fraction would REFUSE -150/100 -- a lethal hit that "
          "silently no-ops, the exact failure C4 names")
    check(authsrv._damage_fraction(30.0, 100.0, 16, "a scratch") ==
          0xBE99999A,
          "in-range damage is the plain fraction (f32(-0.3) = 0xBE99999A)")

    for bad_dealt, bad_max, why in ((-5.0, 100.0, "negative damage"),
                                    (float("nan"), 100.0, "NaN damage"),
                                    (10.0, 0.0, "zero pool"),
                                    (10.0, -100.0, "negative pool")):
        raised = False
        try:
            authsrv._damage_fraction(bad_dealt, bad_max, 16, why)
        except ValueError:
            raised = True
        check(raised, f"{why} is refused, not clamped",
              f"dealt={bad_dealt!r}, pool_max={bad_max!r} -- the clamp is "
              f"for overkill only; everything else keeps refuse-don't-clamp")

    # End to end: an overkill swing KILLS, on the wire and in the books.
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {10: _fresh_agent()}, "pos": (0.0, 0.0)}
    saved = authsrv.PLAYER_SWING_DAMAGE
    authsrv.PLAYER_SWING_DAMAGE = (150, 150)
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            authsrv.hit_enemy(send, state, 10, 0)
    finally:
        authsrv.PLAYER_SWING_DAMAGE = saved
    agent = state["agents"][10]
    damage_vals = [vals for op, vals, _ in sent
                   if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
    # 8 = the swing trio, the [8 -> 1] hold behind the STARTED (2026-08-22),
    # the 0x00CF the landing earns, then the kill window's
    # three (status, reward, flags). It was 4 until step 9 gave a death its
    # reward and flags messages, and 6 until 2026-08-21 put adrenaline on the
    # wire; the count is spelled out rather than left as a bare literal so the
    # next change to the kill window names itself here. NOTHING is sent for
    # the dying AGENT's own adrenaline -- retail is self-scoped 9 of 9 -- and
    # the count is what would catch a later session "fixing" that asymmetry.
    # 7 since ANIMREF-RE 35 (was 8): the swing no longer carries a prop-8
    # hold. See the in-range control above for the denominator that was read
    # backwards.
    check(len(sent) == 7 and agent["dead"] is True and
          damage_vals and damage_vals[0][3] == F32_MINUS_ONE,
          "an overkill swing sends -1.0 and the target dies",
          f"{len(sent)} messages (swing trio + kill window), "
          f"dead={agent['dead']}, wire fraction=0x{damage_vals[0][3]:08X}"
          if damage_vals else f"sent={sent!r}")


def section_concurrency():
    """F10: the two live threads enter the combat state together.

    hit_enemy has two callers on two threads (world tick at attack_tick,
    connection thread at handle_skill_press) and NOTHING locks the agent
    dicts between them. What this section pins is the contract that matters
    today: concurrent entry must never RAISE (an exception on the tick
    thread silently stops the world; on the connection thread it used to
    close the socket), the health floor must hold, and every damage that
    reaches the wire must carry the valid fraction. Known-benign races
    (a lost health decrement, a doubled kill status -- both possible while
    the read-modify-writes are unlocked) are MEASURED and printed, not
    asserted: pinning them green would claim a synchronization the code
    does not have, and red would flake. Step 3's pending-recharge timers
    extend this section the day they add new cross-thread state
    (studies/combat/PLAN.md, amendment C9).
    """
    import inspect
    import threading
    import authsrv

    # F10 IS NOW CLOSED BY CONSTRUCTION, and this is the check that says so.
    # Until 2026-08-15 hit_enemy had two callers on two threads -- attack_tick
    # on the world tick and handle_skill_press on the connection thread -- and
    # the races below were tolerated because nothing locked the agent dicts.
    # Moving skill damage to cast end removed the connection-thread caller, so
    # every path into hit_enemy is world-tick-only. That is a stronger
    # guarantee than a lock and a cheaper one, but it is only true while it is
    # true: this walks the module's own source and fails if a third caller
    # appears anywhere else.
    src = inspect.getsource(authsrv).splitlines()
    callers = set()
    for i, line in enumerate(src):
        if "hit_enemy(" in line and not line.lstrip().startswith("def "):
            for j in range(i, -1, -1):
                if src[j].startswith("def "):
                    callers.add(src[j].split("(")[0][4:])
                    break
    check(callers == {"attack_tick", "cast_tick"},
          "hit_enemy is reached from the WORLD TICK ONLY",
          f"callers={sorted(callers)} -- both are world-tick functions, so "
          f"F10's race cannot occur. A new caller on the connection thread "
          f"reopens it and reddens this line")

    print("\n10. concurrent entry: two threads, one agent, nothing raises")
    sent = []
    sent_lock = threading.Lock()

    def send(op, vals, label="", quiet=False):
        with sent_lock:
            sent.append((op, vals, label))

    agent = _fresh_agent()
    agent["max_health"] = agent["health"] = 1000.0
    state = {"agents": {10: agent}, "pos": (0.0, 0.0),
             "attacking": 10, "player_dead": False}
    errors = []

    saved_interval, saved_revive = authsrv.ATTACK_INTERVAL, authsrv.REVIVE_AFTER
    authsrv.ATTACK_INTERVAL, authsrv.REVIVE_AFTER = 0.0, 0.0
    try:
        out = io.StringIO()

        def hammer(rounds):
            try:
                for _ in range(rounds):
                    authsrv.hit_enemy(send, state, 10, 0)
            except BaseException as ex:   # noqa: BLE001 -- the check IS the catch
                errors.append(repr(ex))

        def churn(rounds):
            try:
                for _ in range(rounds):
                    authsrv.revive_due(send, state, 0)
            except BaseException as ex:   # noqa: BLE001
                errors.append(repr(ex))

        threads = [threading.Thread(target=hammer, args=(300,)),
                   threading.Thread(target=hammer, args=(300,)),
                   threading.Thread(target=churn, args=(300,))]
        with contextlib.redirect_stdout(out):
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=30)
        check(errors == [] and not any(t.is_alive() for t in threads),
              "600 swings and 300 revive sweeps across three threads, "
              "zero exceptions",
              f"errors={errors!r} -- an exception here is the world tick "
              f"dying silently or a client disconnected mid-fight")
        check(0.0 <= agent["health"] <= agent["max_health"],
              "the health floor and ceiling held through every interleaving",
              f"health={agent['health']}")
        damage_bits = {vals[3] for op, vals, _ in sent
                       if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
                       and vals[0] == authsrv.agents.PROP_DAMAGE}
        lo, hi = authsrv.PLAYER_SWING_DAMAGE
        expected = {authsrv._damage_fraction(float(d), 1000.0,
                                             authsrv.agents.PROP_DAMAGE,
                                             "expected")
                    for d in range(lo, hi + 1)}
        check(damage_bits <= expected,
              "every damage that reached the wire carried a valid fraction",
              f"distinct wire values: { {hex(b) for b in damage_bits} } "
              f"against the {len(expected)} the hammer's {lo}-{hi} range can "
              f"produce. A SET, since 2026-08-20: the swing rolls inside the "
              f"weapon's own range rather than taking a fixed fraction of the "
              f"target, so one expected value would be the wrong shape")
        # The races this section deliberately does NOT assert, measured so a
        # future locking change has a before-number: dead flips and kill
        # statuses per life can exceed 1 while the read-modify-writes are
        # unlocked.
        kills = sum(1 for op, vals, _ in sent
                    if op == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
                    and vals[1] == authsrv.agents.EFFECT_DEAD)
        revives = sum(1 for op, vals, _ in sent
                      if op == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
                      and vals[1] == 0)
        print(f"   measured, not asserted: {kills} kill statuses, "
              f"{revives} revives, {len(sent)} total sends "
              f"(a doubled kill per life is the F10 race, tolerated today)")
    finally:
        authsrv.ATTACK_INTERVAL, authsrv.REVIVE_AFTER = (saved_interval,
                                                         saved_revive)


def section_cast_timers():
    """Step 3's cross-thread state: presses append, the tick consumes.

    The amendment (C9) that demanded this: the pending-cast list is the
    arc's first genuinely NEW cross-thread structure, so it does not get to
    ride on section 10's coverage of the older dicts. The design claim under
    test is the single-writer rule -- only cast_tick mutates phases and
    removes entries -- which is what makes 'exactly one E5/E3/E6 per press,
    none lost, none doubled' a property rather than luck.
    """
    import threading
    import authsrv

    print("\n11. cast timers: N presses across threads, exactly N of each "
          "phase")
    PRESSES = 200
    sent = []
    sent_lock = threading.Lock()

    def send(op, vals, label="", quiet=False):
        with sent_lock:
            sent.append((op, vals, label))

    # A DELIBERATELY BOTTOMLESS POOL. Skill 42 costs 10 energy and the player's
    # is 25, so under the energy gate (wired 2026-08-20) 200 presses become 2
    # casts and 198 refusals -- and this section is about the single-writer rule
    # on `pending_casts`, not about what a skill costs. The gate stays ON, which
    # is the shipped default; only the fixture's pool is made large enough that
    # every press is affordable. test_pools sections 6-6b are where the gate
    # itself is proven.
    state = {"agents": {}, "energy": authsrv.pools.EnergyPool(1_000_000, 3)}
    errors = []
    done_pressing = threading.Event()

    saved_timing = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (0.0, 0.0, 0.0)   # everything due now
    try:
        out = io.StringIO()

        def presser():
            try:
                for i in range(PRESSES):
                    authsrv.handle_skill_press([0, 42, i, 0], send, state, 0,
                                               authsrv.GAME_CMSG_USE_SKILL)
            except BaseException as ex:   # noqa: BLE001
                errors.append(repr(ex))
            finally:
                done_pressing.set()

        def ticker():
            try:
                while not (done_pressing.is_set()
                           and not state.get("pending_casts")):
                    authsrv.cast_tick(send, state, 0)
            except BaseException as ex:   # noqa: BLE001
                errors.append(repr(ex))

        threads = [threading.Thread(target=presser),
                   threading.Thread(target=ticker)]
        with contextlib.redirect_stdout(out):
            for t in threads:
                t.start()
            for t in threads:
                t.join(timeout=60)
        alive = any(t.is_alive() for t in threads)

        counts = {}
        for op, _, _ in sent:
            counts[op] = counts.get(op, 0) + 1
        check(errors == [] and not alive,
              "two threads, zero exceptions, both finished",
              f"errors={errors!r}, alive={alive}")
        check(counts.get(0x00E5, 0) == PRESSES
              and counts.get(0x00E3, 0) == PRESSES
              and counts.get(0x00E6, 0) == PRESSES
              and not state.get("pending_casts"),
              f"exactly {PRESSES} E5s, E3s and E6s -- no phase lost, none "
              f"doubled",
              f"E5={counts.get(0x00E5, 0)}, E3={counts.get(0x00E3, 0)}, "
              f"E6={counts.get(0x00E6, 0)}, pending="
              f"{len(state.get('pending_casts', ()))}")
    finally:
        authsrv.skill_timing = saved_timing


def main():
    section_hit_enemy()
    section_skill_press()
    section_land_swing()
    section_land_skill()
    section_revive_due()
    section_player_revive_due()
    section_agent_refill_due()
    section_player_refill_due()
    section_overkill()
    section_concurrency()
    section_cast_timers()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
