"""The player's swing is two phases: START, a windup, then the landing.

Until 2026-08-22 the player was the one attacker whose swing had no
mid-animation window -- STARTED + damage + FINISHED left in a single call
(studies/combat/PLAN.md 17e item 1) -- so nothing could ever cancel a swing,
and quarterstepping "worked" only because there was nothing to miss. The
window now exists and is the agents' own: `swing_windup(ATTACK_INTERVAL)`
after the START, gate running START to START, and the constant carries three
independent legs (NPC swings 0.4540 n=41, the player's clean auto-attacks
0.4583/0.4669, Power Shot's E4->E5 at 0.4601/0.4595 of the declared bow
speed -- studies/castmech/FINDINGS.md M1).

Timing is tested by REWINDING the armed swing and the start gate, never by
sleeping -- the same discipline as test_castcycle.

The landing itself is hit_enemy's and stays under test_guards; what this
file owns is the SPLIT: one STARTED per swing, the damage a windup later,
and an armed swing dropped -- silently, retail's own truncation shape (the
Lakeside 7th swing, cut 0.24 s in by the target's death, no closing event)
-- when the target or the player stops being able to carry it.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402

# FLOOR 24, from the green run of 2026-08-22 that pinned the property-8
# action hold beside the swing paths (23 when sections 5-7 landed, 13 when
# the file carried only the windup split).
LEDGER = checks.Ledger("player swing windup", floor=24)
check = LEDGER.ok

PLAYER = 1   # authsrv.PLAYER_AGENT_ID, restated so a drift reddens something


def _fresh_agent():
    return {"name": "target", "dead": False, "last_hit": 0.0,
            "max_health": 100.0, "health": 100.0, "pos": (0.0, 0.0)}


def _state():
    return {"agents": {10: _fresh_agent()}, "pos": (0.0, 0.0)}


def _rewind(state, seconds):
    """Move the armed swing and the start gate into the past."""
    if state.get("player_swing"):
        state["player_swing"]["lands_at"] -= seconds
    if state.get("player_last_swing"):
        state["player_last_swing"] -= seconds


def section_two_phases():
    import authsrv

    print("1. a swing is a START, a windup, then the landing -- not one call")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = _state()
    authsrv.begin_attack(send, state, 10, 0)
    authsrv.attack_tick(send, state, 0)

    ops = [op for op, _, _ in sent]
    check(ops == [authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT]
          and sent[0][1] == [authsrv.agents.GV_ATTACK_STARTED, PLAYER, 10, 0]
          and sent[1][1] == [authsrv.agents.GV_DISABLED, PLAYER, 1],
          "the first tick sends ATTACK_STARTED, then [8 -> 1] -- the hold "
          "rides immediately behind its own START, 4 of 4 in the corpus "
          "(castmech 3c) -- and no damage",
          f"sent={[(hex(o), v) for o, v, _ in sent]}")
    swing = state.get("player_swing")
    expect = authsrv.swing_windup(authsrv.ATTACK_INTERVAL)
    check(swing is not None and swing["target"] == 10,
          "and arms a swing at the clicked target", f"{swing}")
    import time as _t
    check(swing and abs((swing["lands_at"] - _t.time()) - expect) < 0.25,
          f"due a windup out: {expect:.3f}s = SWING_WINDUP_RATIO x the "
          f"declared {authsrv.ATTACK_INTERVAL}s -- the same arithmetic the "
          f"agents use",
          f"lands in {swing['lands_at'] - _t.time():.3f}s" if swing else "none")

    authsrv.attack_tick(send, state, 0)
    check(len(sent) == 2, "an undue swing does not land early",
          f"{len(sent)} sends")

    _rewind(state, expect + 0.01)
    authsrv.attack_tick(send, state, 0)
    ops = [op for op, _, _ in sent]
    check(ops == [authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                  authsrv.AGENT_ADRENALINE_GAIN,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT],
          "the landing is gain, damage, FINISHED -- and NO second STARTED "
          "and NO hold toggle: the one from the arm-phase was the swing's "
          "own, and a landing releases nothing (the chain still holds)",
          f"ops={[hex(o) for o in ops]}")
    check(state["player_swing"] is None
          and state["agents"][10]["health"] < 100.0,
          "the swing is spent and the damage bookkept",
          f"swing={state['player_swing']}, "
          f"health={state['agents'][10]['health']}")


def section_start_to_start():
    import authsrv

    print("\n2. the interval gates START to START, not landing to landing")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = _state()
    authsrv.begin_attack(send, state, 10, 0)
    authsrv.attack_tick(send, state, 0)                    # START 1
    _rewind(state, authsrv.swing_windup(authsrv.ATTACK_INTERVAL) + 0.01)
    authsrv.attack_tick(send, state, 0)                    # landing 1
    n_after_landing = len(sent)

    authsrv.attack_tick(send, state, 0)
    check(len(sent) == n_after_landing,
          "right after a landing, no new START -- the backswing half of the "
          "interval is a WAIT, not an event (no wire message exists for it)",
          f"{len(sent) - n_after_landing} extra sends")

    # The start gate has already been rewound by one windup (landing 1); move
    # it the REST of the interval into the past and the next START is due.
    _rewind(state, authsrv.ATTACK_INTERVAL
            - authsrv.swing_windup(authsrv.ATTACK_INTERVAL))
    authsrv.attack_tick(send, state, 0)
    started = [v for op, v, _ in sent[n_after_landing:]
               if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
               and v[0] == authsrv.agents.GV_ATTACK_STARTED]
    check(started == [[authsrv.agents.GV_ATTACK_STARTED, PLAYER, 10, 0]],
          "one interval after START 1, START 2 opens",
          f"{started}")


def section_lost_target():
    import authsrv

    print("\n3. an armed swing whose target is gone is dropped, silently")
    for name, wreck in (
            ("dies", lambda st: st["agents"][10].__setitem__("dead", True)),
            ("walks out of reach",
             lambda st: st["agents"][10].__setitem__(
                 "pos", (authsrv.ATTACK_RANGE * 2, 0.0)))):
        sent = []
        send = lambda op, vals, label="", quiet=False: \
            sent.append((op, vals, label))
        state = _state()
        authsrv.begin_attack(send, state, 10, 0)
        authsrv.attack_tick(send, state, 0)               # arm
        sent.clear()
        wreck(state)
        _rewind(state, 10.0)                              # long past due
        authsrv.attack_tick(send, state, 0)
        # The SWING drops silently either way (retail's truncation), but a
        # DEAD target also releases the hold on the wire -- the one live
        # target-death close carries [8, 31, 0] (t=20.1637, n=1, castmech
        # 3c). Out-of-range has no witness and stays fully silent.
        expected = ([(0x009F, [authsrv.agents.GV_DISABLED, PLAYER, 0])]
                    if name == "dies" else [])
        check(state["player_swing"] is None
              and [(op, v) for op, v, _ in sent] == expected,
              f"target {name}: the swing whiffs -- ArenaNet's own "
              f"truncation (the Lakeside 7th swing, 0.24 s in) -- and only "
              f"a death releases the hold",
              f"swing={state['player_swing']}, sent={sent!r}")

    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = _state()
    authsrv.begin_attack(send, state, 10, 0)
    authsrv.attack_tick(send, state, 0)
    sent.clear()
    state["player_dead"] = True
    _rewind(state, 10.0)
    authsrv.attack_tick(send, state, 0)
    check(state["player_swing"] is None and sent == [],
          "and a dead player does not land the swing they were mid-way "
          "through", f"swing={state['player_swing']}, sent={sent!r}")


def section_direct_calls_unchanged():
    import authsrv

    print("\n4. hit_enemy's one-instant shape survives for its other callers")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = _state()
    authsrv.hit_enemy(send, state, 10, 0)
    ops = [op for op, _, _ in sent]
    check(ops[0] == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
          and sent[0][1][0] == authsrv.agents.GV_ATTACK_STARTED
          and sent[1][1] == [authsrv.agents.GV_DISABLED, PLAYER, 1]
          and len(sent) == 5,
          "a default (unarmed) call still opens with its own STARTED (the "
          "hold riding behind it, as at every swing open) and lands in one "
          "instant -- the attack-skill path's recorded divergence, "
          "unchanged",
          f"ops={[hex(o) for o in ops]}")
    sent.clear()
    state["agents"][10] = _fresh_agent()
    state["agents"][10]["last_hit"] = __import__("time").time()
    authsrv.hit_enemy(send, state, 10, 0)
    check(sent == [],
          "and the unarmed call still respects the interval gate",
          f"sent={sent!r}")


def _press(authsrv, send, state, skill=42, copy=7, target=0):
    authsrv.handle_skill_press([0, skill, copy, target], send, state, 0,
                               authsrv.GAME_CMSG_USE_SKILL)


def _rewind_casts(state, seconds):
    for cast in state.get("pending_casts", ()):
        for k in ("e5_at", "e3_at", "e6_at"):
            cast[k] -= seconds


def section_press_stops_swing():
    import authsrv

    print("\n5. a skill press stops the live chain: STOPPED right after E4, "
          "and the armed swing never lands")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = _state()
    authsrv.begin_attack(send, state, 10, 0)
    authsrv.attack_tick(send, state, 0)                    # arm the swing
    sent.clear()
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 8.0)
    try:
        _press(authsrv, send, state)
        ops = [op for op, _, _ in sent]
        check(ops[:3] == [authsrv.GAME_SMSG_SKILL_ACTIVATED_BROADCAST,
                          authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                          authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT]
              and sent[1][1] == [authsrv.agents.GV_DISABLED, PLAYER, 0]
              and sent[2][1] == [authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0],
              "the press burst carries [8 -> 0] then GV_ATTACK_STOPPED "
              "[3, agent, 0] immediately after E4 -- retail's own order, "
              "2 of 2 live presses with a chain running (necro t=18.511, "
              "ranger t=21.543: the release PRECEDES the stop)",
              f"ops={[hex(o) for o in ops]}, "
              f"second={sent[1][1] if len(sent) > 1 else None}")
        check(state.get("player_swing_cancel") == "skill press",
              "and asks the tick to drop the armed swing -- the entry itself "
              "is the tick's to touch", f"{state.get('player_swing_cancel')}")

        sent.clear()
        _rewind(state, 10.0)
        authsrv.attack_tick(send, state, 0)
        check(state["player_swing"] is None
              and state["agents"][10]["health"] == 100.0 and sent == [],
              "the swing in flight is dropped, its damage never lands",
              f"swing={state['player_swing']}, "
              f"health={state['agents'][10]['health']}, sent={sent!r}")
        check(state.get("attacking") == 10,
              "and the CHAIN survives the press -- retail resumes it after "
              "the aftercast, so the target must not be forgotten",
              f"attacking={state.get('attacking')}")

        sent.clear()
        _press(authsrv, send, state)
        check(all(v != [authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0]
                  for _, v, _ in sent),
              "a press while the chain is ALREADY paused stays silent -- the "
              "necro's own press 2 (t=9.85) carries no STOPPED",
              f"{[(hex(o), v) for o, v, _ in sent]}")
    finally:
        authsrv.skill_timing = saved


def section_pause_and_resume():
    import authsrv

    print("\n6. the chain pauses for cast + aftercast and resumes at E3 -- "
          "the observed instant")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = _state()
    authsrv.begin_attack(send, state, 10, 0)
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 8.0)
    try:
        _press(authsrv, send, state)
        sent.clear()
        state["player_last_swing"] = 0.0                   # gate wide open
        authsrv.attack_tick(send, state, 0)
        check(sent == [] and state.get("player_swing") is None,
              "no swing starts while the cast is short of its E3",
              f"sent={[(hex(o), v) for o, v, _ in sent]}")

        _rewind_casts(state, 2.0)                          # e5 and e3 past due
        authsrv.cast_tick(send, state, 0)
        check([op for op, _, _ in sent] ==
              [0x00E5, 0x009F, 0x009F, 0x009F, 0x00E3],
              "(the cast completes: E5, then [58, agent, 0], then the hold "
              "pulse, then E3 -- no release behind it, reverted 2026-09-01)",
              f"{[hex(o) for o, _, _ in sent]}")
        sent.clear()
        state["player_last_swing"] = 0.0
        authsrv.attack_tick(send, state, 0)
        started = [v for op, v, _ in sent
                   if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                   and v[0] == authsrv.agents.GV_ATTACK_STARTED]
        check(started == [[authsrv.agents.GV_ATTACK_STARTED, PLAYER, 10, 0]],
              "and the first tick after E3 opens the next swing -- "
              "ATTACK_STARTED rides the E3 instant on both of skill 105's "
              "live cycles", f"{[(hex(o), v) for o, v, _ in sent]}")
    finally:
        authsrv.skill_timing = saved


def section_retarget():
    import authsrv

    print("\n7. a retarget stops the swing in flight and opens on the new "
          "target")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = _state()
    state["agents"][11] = _fresh_agent()
    authsrv.begin_attack(send, state, 10, 0)
    authsrv.attack_tick(send, state, 0)                    # arm at 10
    sent.clear()
    authsrv.begin_attack(send, state, 11, 0)
    stops = [v for op, v, _ in sent
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
             and v[0] == authsrv.agents.GV_ATTACK_STOPPED]
    check(stops == [[authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0]],
          "the retarget sends one STOPPED -- the corpus's candidate cancel "
          "(17c): two target-selects, then the standalone stop 57-90 ms "
          "later, no damage for the opened swing", f"{stops}")
    check([(op, v) for op, v, _ in sent[:2]] ==
          [(0x009F, [authsrv.agents.GV_DISABLED, PLAYER, 0]),
           (0x009F, [authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0])],
          "and the stop is the corpus's PAIR: [8 -> 0] immediately before "
          "the [3, agent, 0] -- the t=16.578 retarget's own adjacency "
          "(castmech 3c)",
          f"{[(hex(op), v) for op, v, _ in sent[:2]]}")
    sent.clear()
    authsrv.attack_tick(send, state, 0)
    swing = state.get("player_swing")
    check(swing is not None and swing["target"] == 11
          and state["agents"][10]["health"] == 100.0,
          "the old swing is dropped unlanded and the new one opens on the "
          "new target in the same tick",
          f"swing={swing}, old health={state['agents'][10]['health']}")


def main():
    section_two_phases()
    section_start_to_start()
    section_lost_target()
    section_direct_calls_unchanged()
    section_press_stops_swing()
    section_pause_and_resume()
    section_retarget()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
