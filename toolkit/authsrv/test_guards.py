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
assumed. Against the pre-guard tree (cdefe83), section 1 measured:

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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402

LEDGER = checks.Ledger("guard contract", floor=32)
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

    saved = authsrv.HIT_FRACTION
    # NEGATIVE damage -- a heal riding the damage property. This poison was
    # 1.5 when the section was written red-first; amendment C4 then made
    # overkill VALID (clamp-to-kill, section 9), so 1.5 stopped being an
    # error and the invalid shape here had to become one that still is.
    authsrv.HIT_FRACTION = -1.5
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
        authsrv.HIT_FRACTION = saved

    # The control: with the real constant the same call sends the whole
    # swing. A guard that refuses everything would pass every check above.
    sent.clear()
    state["agents"][10] = _fresh_agent()
    authsrv.hit_enemy(send, state, 10, 0)
    ops = [op for op, _, _ in sent]
    check(len(sent) == 3, "control: the in-range path still sends the swing",
          f"{len(sent)} messages: {ops}")
    check(state["agents"][10]["health"] == 100.0 - 100.0 * authsrv.HIT_FRACTION,
          "control: and the in-range damage is bookkept",
          f"health={state['agents'][10]['health']}")


def section_skill_press():
    """The connection thread survives a refusal -- world_tick's contract."""
    import authsrv

    print("\n2. handle_skill_press: a refusal costs the value, not the socket")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {10: _fresh_agent()}, "pos": (0.0, 0.0)}
    press = [0, 42, 7, 10]   # header slot, skill 42, copy 7, target agent 10

    saved = authsrv.HIT_FRACTION
    authsrv.HIT_FRACTION = -1.5   # invalid (a heal-shaped damage); see section 1
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            authsrv.handle_skill_press(press, send, state, 0,
                                       authsrv.GAME_CMSG_USE_SKILL)
        # No raise reached us -- that IS the check; an escaping ValueError
        # here is what handle's except tuple turns into a socket close.
        check("REFUSED a value" in out.getvalue(),
              "the refusal is LOGGED, not silent",
              out.getvalue().strip().splitlines()[-1] if out.getvalue() else
              "(nothing printed)")
        ops = [op for op, _, _ in sent]
        check(ops == [authsrv.GAME_SMSG_SKILL_ACTIVATED],
              "the valid echo went out; the refused effect sent NOTHING",
              f"ops={ops} -- the echo precedes the effect and is a valid "
              f"message; refusing it too would un-answer the client's "
              f"pending-skill key over a number it never saw")
    finally:
        authsrv.HIT_FRACTION = saved

    sent.clear()
    state["agents"][10] = _fresh_agent()
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        authsrv.handle_skill_press(press, send, state, 0,
                                   authsrv.GAME_CMSG_USE_SKILL)
    check(len(sent) == 4, "control: the in-range press sends echo + swing",
          f"{len(sent)} messages: {[op for op, _, _ in sent]}")


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
    check(len(sent) == 2 and sent[0][0] ==
          authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
          "control: in-range keeps ArenaNet's order -- finished, then damage",
          f"{[op for op, _, _ in sent]} -- 6 of 6 swings in the Lakeside "
          f"tape, checked by byte offset (land_swing docstring)")


def section_land_skill():
    import authsrv

    print("\n4. land_skill: guard before the cast slot and the health are spent")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}, "pos": (0.0, 0.0)}
    agent = _fresh_agent()
    agent["casting"], agent["skills"] = 0, ((7, 1.0, 20.0),)

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
    check(len(sent) == 1 and agent["casting"] is None,
          "control: in-range lands the skill and clears the slot",
          f"{[op for op, _, _ in sent]}, casting={agent['casting']}")


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
    check(len(sent) == 2 and state["player_refill_due_at"] is None,
          "control: in-range sends both refill halves and disarms",
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
    saved = authsrv.HIT_FRACTION
    authsrv.HIT_FRACTION = 1.5
    try:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            authsrv.hit_enemy(send, state, 10, 0)
    finally:
        authsrv.HIT_FRACTION = saved
    agent = state["agents"][10]
    damage_vals = [vals for op, vals, _ in sent
                   if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
    check(len(sent) == 4 and agent["dead"] is True and
          damage_vals and damage_vals[0][3] == F32_MINUS_ONE,
          "an overkill swing sends -1.0 and the target dies",
          f"{len(sent)} messages (swing trio + kill status), "
          f"dead={agent['dead']}, wire fraction=0x{damage_vals[0][3]:08X}"
          if damage_vals else f"sent={sent!r}")


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
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
