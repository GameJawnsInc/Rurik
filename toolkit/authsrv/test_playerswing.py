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

import math
import os
import sys
import time as _tt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402

# FLOOR 55, from the green run of 2026-09-01 that added section 8, the
# ANIMREF-RE 37 leg-time bound on the click latch (42 with section 7's
# constant bound; 35 with section 6's landing hold release; 30 with section
# 5's chain pause; 24 before that day; 13 when the file carried only the
# windup split). Sections 5-8 are all fixture-free -- they stub the clock
# and drive the real attack_tick -- so 55 is the BARE-MACHINE number too.
# FLOOR 82 from the green run of 2026-09-02 that added section 9 (ANIMREF-RE
# 38's reach and approach: 27 fixture-free checks driving the real attack_tick
# with the flag forced on and restored), so 82 is the bare-machine number too.
# FLOOR 96 from the green run of 2026-09-02 that added section 10 (ANIMREF-RE
# 39: the press supersedes the walk, a move ends the chain; 14 fixture-free
# checks). 82 with section 9 alone.
# FLOOR 116 from the green run of 2026-09-03 that added section 11 (ANIMREF-RE
# 41: the press supersedes the keyboard belief, and every press leaves a
# press_verdict row; 20 fixture-free checks). 96 with section 10 alone.
# SWINGCANCEL +7 (123): 1 known-bad arm + 3 reach row + 1 control + 2 other
# branches (1z-cx). MOVECODE-1z-da +5 (128): the lifecycle pins, ours and
# retail's. MOVECODE-1z-db +5 (133): the displacement gate, known-bad arm
# first. MOVECODE-1z-dc +4 (137): the chain-pause row. §13 needs the
# gamesrv corpus and §13b the live one; each declares a skip by name.
LEDGER = checks.Ledger("player swing windup", floor=267)   # MOVECODE-1z-ds.31 +12 (21a-k and section 6's shipped arm: every start holds to the next input); MOVECODE-1z-ds.30 +4 (20g-j: a new follow's leg starts at the body estimate); MOVECODE-1z-ds.29 +5 (10k-o: a press on our own follow's target is spared, arrived or not); MOVECODE-1z-ds.28 +6 (22a-f: no follow inside our windup, the re-approach rides the landing); MOVECODE-1z-ds.27 +4 (19g-j: a death mid-windup carries [3]); MOVECODE-1z-ds.21 +4 (17b-k..n: the landed race, the follow_swing closes); MOVECODE-1z-ds.20 +6 (20a-f, the placement frame and the click dest); MOVECODE-1z-ds.19 +2 (17b-i/j, the follow_swing row); MOVECODE-1z-ds.13 +1 (17b-h, the walk-in variant); MOVECODE-1z-ds.15 +7 (19, the dead press: begin_attack, the real arm, the dead tick); MOVECODE-1z-ds.13 +7 (17b-a..g, a cancelled windup holds no clock); MOVECODE-1z-ds.9 +2 (the 136 u press, both arms); MOVECODE-1z-ds.7 +3 (9l-g..i); MOVECODE-1z-ds.6 +6 (9l-a..f); MOVECODE-1z-dr +4 (9k, the keyboard snap guard), +3 round 2; SLICE-F50 +8 (the deadline wake: served at its instant, never twice, the revert, the fuse); SLICE-F49 +7 (the carried swing clock, its known-bad arm, the second strike's nearest tick); from the green run
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

    # THE DENOMINATOR THAT WAS READ BACKWARDS, and it is why the hold
    # left this file: castmech 3c censuses the prop-8 HOLDS and finds 4 of
    # 4 riding an ATTACK_STARTED -- an ORDER fact about the holds that
    # occurred. It was read as a RATE over the STARTS, so this server sent
    # one on every swing: 52 of 52 (100%) against retail's 83 of 1,332
    # (6.2%). ANIMREF-RE 35 sends none on an auto swing.
    # RE-AIMED 2026-10-02 (MOVECODE-1z-ds.31): that denominator counted TRANSITIONS of a
    # transition-only property; the STATE at start + 0.1 s is held on 1,647 of 1,654 retail
    # own starts, raised in the start's own batch directly behind the [4] (210 of 210).
    ops = [op for op, _, _ in sent]
    check(ops == [authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT]
          and sent[0][1] == [authsrv.agents.GV_ATTACK_STARTED, PLAYER, 10, 0]
          and sent[1][1] == [authsrv.agents.GV_DISABLED, PLAYER, 1],
          "the first tick sends ATTACK_STARTED and then the hold [8, me, 1] -- no damage "
          "(MOVECODE-1z-ds.31: retail holds 1,647 of 1,654 own starts, raised behind the [4])",
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
    check(len(sent) == 2, "an undue swing does not land early (the start and its hold, "
          "nothing more)", f"{len(sent)} sends")

    _rewind(state, expect + 0.01)
    authsrv.attack_tick(send, state, 0)
    ops = [op for op, _, _ in sent]
    # ANIMREF-RE 43 (2026-09-30): the landing is FINISHED, gain, damage --
    # retail's [1] first, 1,376 of 1,376; "gain, damage, FINISHED" was our order
    # and drew the player's numbers on whichever agent the client had latched
    # (test_damagelatch). --hit-finish-last keeps the old order, checked below.
    _int_t = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
    _int = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
    _gain = authsrv.AGENT_ADRENALINE_GAIN
    _word = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
    _held = [v for op, v, _l in sent[2:] if op == _int and v[0] == authsrv.agents.GV_DISABLED]
    check(ops[:2] == [_int_t, _int] and _held == []
          and ops[2:] == ([_int, _gain, _word] if authsrv.HIT_FINISH_FIRST
                          else [_gain, _word, _int]),
          "the landing is FINISHED, gain, damage (ANIMREF-RE 43; gain, damage, "
          "FINISHED under --hit-finish-last) -- and no second STARTED "
          "and NO property 8 in either direction. This check has moved "
          "three times and the trail is the record: it once ended 'a "
          "landing releases nothing (the chain still holds)', which was the "
          "ANIMREF-RE 33 defect written as an assertion; 33 F1 then added a "
          "release here; 35 removed the hold that release existed for; 43 "
          "moved the FINISHED ahead of the word. Section 6 owns the three arms",
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

    print("\n3. an armed swing whose target DIED is dropped silently; one "
          "whose target WALKED OUT lands anyway (SLICE-F21)")
    # ANIMREF-RE 39: with the approach the DEFAULT, a target that walks out
    # of reach is answered by retail's auto-chase (a 0x002A with no press,
    # 16/24 chains on the live tapes) -- section 9 owns that. This section
    # is about the armed swing, so it runs the no-approach arm.
    saved_ap = authsrv.ATTACK_APPROACH
    authsrv.ATTACK_APPROACH = False
    dmg_op = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
    for name, wreck, lands in (
            ("dies", lambda st: st["agents"][10].__setitem__("dead", True),
             False),
            ("walks out of reach",
             lambda st: st["agents"][10].__setitem__(
                 "pos", (authsrv.ATTACK_RANGE * 2, 0.0)), True)):
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
        hit = [v for op, v, _ in sent if op == dmg_op
               and v[0] in (authsrv.agents.PROP_DAMAGE, authsrv.agents.GV_CRITICAL)]
        if lands:
            check(state["player_swing"] is None and len(hit) == 1
                  and state["agents"][10]["health"] < 100.0,
                  f"target {name}: the armed swing LANDS wherever the target "
                  f"went -- retail judges reach at the START, never at the "
                  f"hit: 33 of 34 player swings on a moving target and 7 of 7 "
                  f"swings at a running player landed (SLICE-F21, "
                  f"latehitjoin)",
                  f"swing={state['player_swing']}, hit={hit}, "
                  f"health={state['agents'][10]['health']}")
        else:
            # The dead-target arm used to also carry [8, 31, 0] -- the one
            # live target-death close, t=20.1637, n=1, castmech 3c -- but
            # since ANIMREF-RE 35 an auto swing sets no hold, so
            # `action_hold` is transition-only and there is nothing to
            # release.
            # RE-AIMED 2026-10-02 (MOVECODE-1z-ds.31): the start holds again, so the
            # target-gone tick releases it -- the one live target-death close above.
            check(state["player_swing"] is None
                  and [(op, v) for op, v, _ in sent]
                  == [(authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                       [authsrv.agents.GV_DISABLED, PLAYER, 0])],
                  f"target {name}: the swing whiffs -- ArenaNet's own "
                  f"truncation (the Lakeside 7th swing, 0.24 s in) -- and the "
                  f"start's hold is released, nothing else",
                  f"swing={state['player_swing']}, sent={sent!r}")
    # THE REVERT ARM (--no-late-hit): the walk-out drops silently, the
    # pre-F21 rule this section pinned as retail's until 2026-09-12.
    saved_lh = authsrv.LATE_HIT
    authsrv.LATE_HIT = False
    try:
        sent = []
        send = lambda op, vals, label="", quiet=False: \
            sent.append((op, vals, label))
        state = _state()
        authsrv.begin_attack(send, state, 10, 0)
        authsrv.attack_tick(send, state, 0)
        sent.clear()
        state["agents"][10]["pos"] = (authsrv.ATTACK_RANGE * 2, 0.0)
        _rewind(state, 10.0)
        authsrv.attack_tick(send, state, 0)
        check(state["player_swing"] is None and sent == [],
              "REVERT ARM (--no-late-hit): the walk-out drops the armed swing "
              "silently -- the rule that let a kiter pay nothing",
              f"swing={state['player_swing']}, sent={sent!r}")
    finally:
        authsrv.LATE_HIT = saved_lh

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
    authsrv.ATTACK_APPROACH = saved_ap


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
          and not [v for op, v, _ in sent
                   if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                   and v[0] == authsrv.agents.GV_DISABLED]
          and len(sent) == 4,
          "a default (unarmed) call still opens with its own STARTED -- and "
          "NO hold behind it since ANIMREF-RE 35 -- and lands in one "
          "instant: the attack-skill path's recorded divergence, unchanged",
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
        # THE ORDER IS STILL PINNED, on the arm that still produces both
        # halves. Since ANIMREF-RE 35 an auto swing sets no hold, so the
        # [8 -> 0] is transition-only and elides -- the press burst opens
        # with the STOPPED alone. The corpus order (release PRECEDES stop,
        # necro t=18.511, ranger t=21.543, 2 of 2) is re-checked below on a
        # state where a hold IS riding, which is what those instants were.
        check(ops[:3] == [authsrv.GAME_SMSG_SKILL_ACTIVATED_BROADCAST,
                          authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                          authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT]
              and sent[1][1] == [authsrv.agents.GV_DISABLED, PLAYER, 0]
              and sent[2][1] == [authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0],
              "the press burst is E4, then the start's hold released, then "
              "GV_ATTACK_STOPPED [3, agent, 0] -- RE-AIMED 2026-10-02 "
              "(MOVECODE-1z-ds.31: the auto swing holds again; retail's skill-press "
              "release follows the E4 on 128 of 128)",
              f"ops={[hex(o) for o in ops]}, "
              f"second={sent[1][1] if len(sent) > 1 else None}")
        # The measured ORDER, on a body that IS holding (as a cast leaves it).
        state2 = _state()
        state2["action_hold"] = 1
        state2["attacking"] = 10
        state2["player_swing"] = {"target": 10, "lands_at": _tt.time() + 9.0}
        sent2 = []
        send2 = lambda op, vals, label="", quiet=False: sent2.append(
            (op, vals, label))
        _press(authsrv, send2, state2)
        pair = [(op, v) for op, v, _ in sent2
                if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT]
        check(pair[:2] == [(authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                            [authsrv.agents.GV_DISABLED, PLAYER, 0]),
                           (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                            [authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0])],
              "and with a hold riding, the release still PRECEDES the stop "
              "-- retail's own order, 2 of 2 live presses with a chain "
              "running. ANIMREF-RE 35 narrowed when the pair occurs; it did "
              "not reorder it",
              f"{[(hex(o), v) for o, v in pair[:2]]}")
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
          "and the stop rides behind the release -- the corpus PAIR, [8 -> 0] "
          "before the [3, agent, 0], the t=16.578 retarget's own adjacency "
          "(castmech 3c; retail 7 of 7 in flight). RE-AIMED 2026-10-02: the "
          "auto swing holds again (MOVECODE-1z-ds.31)",
          f"{[(hex(op), v) for op, v, _ in sent[:2]]}")
    sent.clear()
    authsrv.attack_tick(send, state, 0)
    swing = state.get("player_swing")
    check(swing is not None and swing["target"] == 11
          and state["agents"][10]["health"] == 100.0,
          "the old swing is dropped unlanded and the new one opens on the "
          "new target in the same tick",
          f"swing={swing}, old health={state['agents'][10]['health']}")


def section_click_latch_bound():
    """ANIMREF-RE 33 F5: the click-walk latch is age-bounded, both ways.

    THE OPERATOR'S BUG, reported the same day 31 shipped: "click-to-walk
    cancelled by spacebar [interact/attack] doesn't start attacking. if the
    last move command wasn't WASD, spacebar doesn't fire attacks at all."

    MECHANISM: `click_moving_at` is armed on every 0x003E and cleared only by a
    later movement report (0x003D) or a stop report (0x0047). A click leg that
    merely ARRIVES clears nothing -- the client reports nothing at all while
    click-walking. Before 31 that cost nothing, because the latch's only
    readers wanted to refuse on a maybe-moving body. 31 made `attack_tick` a
    reader with the OPPOSITE polarity, so a stale latch made `if moving:
    return` fire forever and no swing ever opened. `begin_attack` had already
    accepted the order; it was then silently starved.

    BOTH DIRECTIONS MATTER, which is why this section checks both: a latch that
    never expires breaks the attack, and a latch that expires too eagerly
    breaks 31's chain pause on click-walks and regresses the quarterstep.
    """
    import authsrv
    import time as _t

    print("\n7. ANIMREF-RE 33 F5: the click-walk latch is bounded")

    W = authsrv.GRANT_LOCAL_WINDOW
    now = _t.time()
    check(W > 0.5,
          "the bound is the EXISTING GRANT_LOCAL_WINDOW, not a new constant -- "
          "the same one the zero-lead grant already applies to the keyboard "
          "latch",
          f"GRANT_LOCAL_WINDOW = {W}")
    check(authsrv._player_body_moving({"click_moving_at": now}) is True,
          "a click leg JUST issued still reads as moving -- 31's chain pause "
          "must keep pausing through a real click-walk, or the quarterstep "
          "regresses",
          "fresh click")
    check(authsrv._player_body_moving(
              {"click_moving_at": now - (W + 1.0)}) is False,
          "and a click leg older than the window does NOT -- the operator's "
          "bug: a completed click-walk left the latch set forever, so "
          "`attack_tick` returned before opening any swing and spacebar did "
          "nothing at all",
          f"click {W + 1.0:.1f}s old")
    check(authsrv._player_body_moving({"kbd_moving_at": now - 600.0}) is True,
          "the KEYBOARD latch is still not AGE-bounded here: with no press "
          "since the report, a 600 s old latch reads moving. (This used to "
          "say the 0x0047 terminator arrives 36 of 36 -- REFUTED 2026-09-03: "
          "the 08:46 session had 5 keyboard reports and 0 stops, the body "
          "parked 14 s with the latch armed. The terminator that ends it for "
          "THIS reader is now a newer attack press, section 11; rule 1 and "
          "the cast-stop keep the raw latch)",
          "old kbd latch, no press since: still reads moving")

    # THE END-TO-END SHAPE: an attack ordered after a completed click-walk must
    # actually swing. This is the operator's report as a test.
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append(
        (op, vals, label))
    state = _state()
    state["click_moving_at"] = _t.time() - (W + 1.0)   # a click leg long done
    authsrv.begin_attack(send, state, 10, 0)
    sent.clear()
    authsrv.attack_tick(send, state, 0)
    started = [v for op, v, _l in sent
               if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
               and v[0] == authsrv.agents.GV_ATTACK_STARTED]
    check(started == [[authsrv.agents.GV_ATTACK_STARTED, PLAYER, 10, 0]],
          "END TO END: after a click-walk that finished, an ordered attack "
          "OPENS A SWING. This is the operator's report as an assertion -- "
          "before the bound it opened none, ever, and the order was accepted "
          "and starved",
          f"{started}")

    # KNOWN-BAD ARM: with the latch fresh, the pause is still in force.
    sent.clear()
    state2 = _state()
    state2["click_moving_at"] = _t.time()
    authsrv.begin_attack(send, state2, 10, 0)
    sent.clear()
    authsrv.attack_tick(send, state2, 0)
    started2 = [v for op, v, _l in sent
                if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                and v[0] == authsrv.agents.GV_ATTACK_STARTED]
    check(started2 == [],
          "KNOWN-BAD ARM for the other direction: while the click leg is "
          "genuinely in flight the swing STILL waits -- a fix that opened a "
          "swing here would have traded the operator's bug for a regression "
          "of 31's pause, and the test would not have noticed",
          f"{started2}")


def section_landing_hold_release():
    """ANIMREF-RE 35: an auto swing sends NO property-8 hold at all.

    THE DENOMINATOR THAT WAS READ BACKWARDS. castmech 3c censuses the prop-8
    HOLDS and reports "4 of 4" of them riding an ATTACK_STARTED -- an ORDER
    fact about the holds that occurred. It was read as a RATE over the STARTS,
    so this server sent a hold on every swing. Measured over the same
    quantity on both sides: retail 83 of 1,332 attack starts (6.2%), ours
    52 of 52 (100.0%).

    WHAT IT COST, from the operator's own post-33 capture: a pre-landing
    movement press met a SET gate 25 times in 32, with p10 ground speed 0.0
    u/s, drift p50 108.0 u and 6 of 32 episodes travelling under 5 u in 1.5 s
    -- against 4 of 111 gate-set and 1 of 111 frozen post-landing. That is
    the operator's "the mid windup is causing warps now while still not
    moving out smoothly".

    33 F1 (release the hold at the landing) is SUBSUMED but not deleted: with
    the hold restored by --swing-holds-walk-gate it is still what keeps the
    gate open post-landing, and the two flags compose. This section pins all
    three arms so neither can be changed without the other being scored.

    WHAT IS NOT KNOWN, stated rather than smoothed: 6.2% is not 0%. Retail
    DOES hold on some attack starts and the condition is NOT FOUND. Shipping
    zero is closer to retail than 100% by every measure we have, and it is
    still an approximation of a behaviour whose trigger we have not read.
    """
    import authsrv

    print("\n6. ANIMREF-RE 35: an auto swing holds no walk gate")

    def swing_cycle(hold, release, start=False):
        """One swing through the real attack_tick; return (open, landing).
        `start` is MOVECODE-1z-ds.31's ATTACK_START_HOLDS; the ANIMREF-RE 35 arms run off."""
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append(
            (op, vals, label))
        state = _state()
        sh, lr = authsrv.SWING_HOLDS_WALK_GATE, authsrv.LANDING_HOLD_RELEASE
        sa = authsrv.ATTACK_START_HOLDS
        authsrv.SWING_HOLDS_WALK_GATE = hold
        authsrv.LANDING_HOLD_RELEASE = release
        authsrv.ATTACK_START_HOLDS = start
        try:
            authsrv.begin_attack(send, state, 10, 0)
            authsrv.attack_tick(send, state, 0)
            opened = [v for op, v, _l in sent
                      if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                      and v[0] == authsrv.agents.GV_DISABLED]
            sent.clear()
            _rewind(state, authsrv.swing_windup(authsrv.ATTACK_INTERVAL) + 0.01)
            authsrv.attack_tick(send, state, 0)
            landed = [v for op, v, _l in sent
                      if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                      and v[0] == authsrv.agents.GV_DISABLED]
            return opened, landed, state
        finally:
            authsrv.SWING_HOLDS_WALK_GATE = sh
            authsrv.LANDING_HOLD_RELEASE = lr
            authsrv.ATTACK_START_HOLDS = sa

    # ARM 1 -- ANIMREF-RE 35's shape (--no-attack-start-hold): no hold anywhere in the swing.
    # RE-AIMED 2026-10-02 (MOVECODE-1z-ds.31): no longer the shipped arm. The freeze it removed
    # was a held gate meeting a ZERO-lead answer (RECONSTRUCTION); since 1z-ds.10/.17 the
    # released hold's report gets a real lead.
    opened, landed, st = swing_cycle(False, True)
    check(opened == [] and landed == [] and not st.get("action_hold"),
          "ANIMREF-RE 35 ARM (--no-attack-start-hold): the swing sends NO property 8, at the "
          "open or the landing",
          f"open={opened}, landing={landed}, hold={st.get('action_hold')}")
    # ARM 0 -- SHIPPED since MOVECODE-1z-ds.31: the start holds and the landing keeps it.
    opened0, landed0, st0 = swing_cycle(False, True, start=True)
    check(opened0 == [[authsrv.agents.GV_DISABLED, PLAYER, 1]] and landed0 == []
          and st0.get("action_hold") == 1 and st0.get("press_hold") is True,
          "SHIPPED ARM (MOVECODE-1z-ds.31): the start raises [8, me, 1] and the landing keeps it "
          "to the next input -- retail 1,647 of 1,654 own starts held at start + 0.1 s, the "
          "landing ending 3 of 347 hold episodes",
          f"open={opened0}, landing={landed0}, hold={st0.get('action_hold')}")

    # ARM 2 -- the revert, with 33 F1 still on: hold set, released at landing.
    opened2, landed2, st2 = swing_cycle(True, True)
    check(opened2 == [[authsrv.agents.GV_DISABLED, PLAYER, 1]]
          and landed2 == [[authsrv.agents.GV_DISABLED, PLAYER, 0]]
          and st2.get("action_hold") == 0,
          "--swing-holds-walk-gate: the hold returns at the open and 33 F1 "
          "still releases it at the landing -- the two flags COMPOSE, which "
          "is why F1 is subsumed rather than deleted",
          f"open={opened2}, landing={landed2}")

    # ARM 3 -- KNOWN-BAD, both legacy: held at the open, never released.
    opened3, landed3, st3 = swing_cycle(True, False)
    check(opened3 == [[authsrv.agents.GV_DISABLED, PLAYER, 1]]
          and landed3 == [] and st3.get("action_hold") == 1,
          "KNOWN-BAD ARM (--swing-holds-walk-gate --no-landing-hold-release): "
          "held at the open and never released -- every build before "
          "2026-09-01, and the configuration that produced the measured "
          "0.601/0.869/1.015 s movement stall over 104 hold windows",
          f"open={opened3}, landing={landed3}, hold={st3.get('action_hold')}")

    check(st.get("action_hold", 0) == 0 and st0.get("action_hold") == 1,
          "and the shipped and ANIMREF-RE 35 arms SEPARATE on the one number that "
          "matters -- the gate's state while the player is swinging",
          f"35={st.get('action_hold', 0)}, shipped={st0.get('action_hold')}")

    # THE CAST PATH IS UNTOUCHED, and that is the boundary of this change.
    sentc = []
    sendc = lambda op, vals, label="", quiet=False: sentc.append(
        (op, vals, label))
    statec = {"agents": {}}
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 8.0)
    try:
        _press(authsrv, sendc, statec)
        holds = [v for op, v, _l in sentc
                 if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                 and v[0] == authsrv.agents.GV_DISABLED and v[2] == 1]
        check(holds == [[authsrv.agents.GV_DISABLED, PLAYER, 1]],
              "and a CAST still holds -- property 8 around a cast is "
              "retail-correct and separately corpus-backed (castmech 3c). "
              "ANIMREF-RE 35 narrows the AUTO-SWING sites only, and a change "
              "that silenced the cast half too would pass every other check "
              "in this section",
              f"{holds}")
    finally:
        authsrv.skill_timing = saved


def section_chain_pause():
    """ANIMREF-RE 31: no swing opens while the body moves. RE-AIMED 2026-10-02 by
    MOVECODE-1z-ds.11: the clock CHARGE this docstring argues for below is REFUTED
    (swingclockjoin.py: 55 of 88 binding presses at the period, 0 at period + span);
    the ratio of medians was the player's re-press time, not a frozen clock.

    THE METRIC IS RETAIL'S OWN AND IT MUST RANK THE KNOWN-BAD ARM BADLY.
    Retail's attack-started gaps are a metronome when the player stands still
    (n=816, p50 1.330 s, p10 1.318, p90 1.345) and stretch to 2.007 s when a
    move falls inside (n=40, p90 3.853) -- ratio of medians 1.51. OUR arm as
    the operator played it scored 1.003 (move-containing n=112 p50 1.783
    against no-move n=312 p50 1.777): a chain that never noticed the player
    walking. So the check is the RATIO, measured on both arms of our own
    scheduler, and the legacy arm must score ~1.0 or this section is
    measuring the wrong quantity.

    Absolute intervals differ from retail legitimately -- our
    WEAPON_ATTACK_SPEED is the hammer's -- so the dimensionless ratio is the
    comparable, exactly as the corpus lane argued.
    """
    import authsrv

    print("\n5. ANIMREF-RE 31: no swing OPENS on a moving body; the clock is not "
          "charged for it (MOVECODE-1z-ds.11)")

    def gap_with_move(paused, move_span, charges=False):
        """Seconds between two ATTACK_STARTEDs with `move_span` of motion
        inside, driven through the REAL attack_tick on a synthetic clock."""
        sent = []
        send = lambda op, vals, label="", quiet=False: \
            sent.append((op, vals, label))
        agent = {"name": "t", "dead": False, "last_hit": 0.0,
                 "max_health": 1e9, "health": 1e9, "pos": (0.0, 0.0)}
        state = {"agents": {10: agent}, "pos": (0.0, 0.0), "attacking": 10}
        saved = (authsrv.CHAIN_PAUSES_WHILE_MOVING, authsrv.SWING_CLOCK_CHARGES_MOVING)
        saved_time = authsrv.time.time
        authsrv.CHAIN_PAUSES_WHILE_MOVING = paused
        authsrv.SWING_CLOCK_CHARGES_MOVING = charges
        clock = [1000.0]
        authsrv.time.time = lambda: clock[0]
        try:
            starts = []
            # 12 s of 50 ms ticks; the body moves from t=+2.0 for move_span
            for i in range(240):
                clock[0] = 1000.0 + i * 0.05
                t = i * 0.05
                state["kbd_moving_at"] = (
                    clock[0] if 2.0 <= t < 2.0 + move_span else None)
                before = len(sent)
                authsrv.attack_tick(send, state, 0)
                for op, vals, _l in sent[before:]:
                    if (op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                            and vals[0] == authsrv.agents.GV_ATTACK_STARTED):
                        starts.append(clock[0])
                # never let a landing end the chain: keep the target alive
                agent["health"] = 1e9
                state["player_swing_cancel"] = None
            return starts
        finally:
            authsrv.CHAIN_PAUSES_WHILE_MOVING, authsrv.SWING_CLOCK_CHARGES_MOVING = saved
            authsrv.time.time = saved_time

    # MOVECODE-1z-ds.11 (2026-10-02) RE-AIMED this section. It used to pin the CHARGE --
    # "the move-containing gap stretches by the moving span" -- on retail's ratio of
    # medians (1.51, n = 40). swingclockjoin.py split the corpus on the presses the two
    # rules disagree about (made inside the interval after a move, n = 88): start-to-start
    # lands at the PERIOD on 55 and at period + span on 0. A move-containing gap is long on
    # retail because the player re-presses later, not because the clock froze. What stays
    # is the REFUSAL: a swing that falls due while the body moves waits for it to stop.
    # The move runs 2.0 -> 4.0 s; the chain's start at 1.75 makes the next due at 3.5,
    # inside the move.
    interval = authsrv.ATTACK_INTERVAL
    span = 2.0
    shipped = gap_with_move(True, span)
    charge = gap_with_move(True, span, charges=True)
    legacy = gap_with_move(False, span)
    quiet = gap_with_move(True, 0.0)

    def move_gap(starts):
        before = [t for t in starts if t - 1000.0 < 2.0]
        after = [t for t in starts if t - 1000.0 >= 2.0]
        return (after[0] - before[-1], before[-1] - 1000.0) if before and after else (None, None)

    g_ship, last_ship = move_gap(shipped)
    g_charge, _l = move_gap(charge)
    g_legacy, _l = move_gap(legacy)
    qg = [b - a for a, b in zip(quiet, quiet[1:])]
    check(g_ship is not None and g_charge is not None and g_legacy is not None and len(qg) >= 3,
          "every arm produced starts on both sides of the move -- the rig is not vacuous",
          f"shipped {g_ship}, charge {g_charge}, legacy {g_legacy}, quiet gaps {qg[:4]}")
    if g_ship is None or g_charge is None or g_legacy is None:
        return
    move_end = 2.0 + span
    check(abs(g_ship - (move_end - last_ship)) <= 0.051,
          "SHIPPED: the swing due inside the move waits for the body to STOP and no longer "
          "-- it opens on the first tick after the move, the period counted from the last "
          "start with nothing added (retail: 55 of 88 binding presses at the period)",
          f"gap {g_ship:.2f} s; the move ended {move_end - last_ship:.2f} s after the last start")
    check(abs(g_charge - (interval + span)) <= 0.10,
          "KNOWN-BAD ARM (--swing-clock-charges-moving, 1z-dg's charge): the gap is the period "
          "PLUS the moving span -- retail lands there on 0 of 88",
          f"gap {g_charge:.2f} s against period + span {interval + span:.2f}")
    check(abs(g_legacy - interval) <= 0.051,
          "KNOWN-BAD ARM (--legacy-move-stops-chain): no refusal, so the swing opens ON the "
          "moving body at the period -- the slide",
          f"gap {g_legacy:.2f} s against the period {interval:.2f}")
    check(g_charge > g_ship + 0.5 and g_ship > g_legacy + 0.2,
          "and the three arms SEPARATE",
          f"charge {g_charge:.2f} > shipped {g_ship:.2f} > legacy {g_legacy:.2f}")

    check(authsrv.CHAIN_PAUSES_WHILE_MOVING is True
          and authsrv.MOVE_KEEPS_CHAIN is True
          and authsrv.SWING_CLOCK_CHARGES_MOVING is False,
          "the refusal and LAW A are the SHIPPED default (reverting together on "
          "--legacy-move-stops-chain, the ANIMREF-RE 29 lesson), and the clock charge is OFF "
          "(1z-ds.11)",
          f"pause={authsrv.CHAIN_PAUSES_WHILE_MOVING}, lawA={authsrv.MOVE_KEEPS_CHAIN}, "
          f"charge={authsrv.SWING_CLOCK_CHARGES_MOVING}")


def section_click_leg_eta():
    """ANIMREF-RE 37: the click-walk latch ends when the LEG does.

    34 bounded the latch by GRANT_LOCAL_WINDOW (3.0 s) because a sibling
    reader used that constant; 36 measured what that costs on the operator's
    own capture -- CLICK-last presses answered 60.6% against ~91% for
    STOP-last, every unanswered one refused by the latch on a body that had
    already arrived, and swings opening at 3.00/3.02/3.02/3.12 s after a
    click and never earlier (the constant's fingerprint on the wire).

    THE DERIVED BOUND is the leg's own travel time: the client walks a click
    as a straight segment at the declared base speed, and a press does not
    stop that segment (0x0081BDB0 clears the queued waypoints and the
    AgTrack record, writes nothing on the async agent -- the body finishes
    its segment and parks, silently). So the latch is TRUE until
    t_click + |dest - start| / speed and FALSE after, whatever a constant
    would have said in either direction. Both directions are pinned here:
    a short leg releases before 3.0 s (the operator's bug) and a long leg
    holds past 3.0 s (the constant's other failure, a swing on a walking
    body). The leg starts where the model says the body stood: the previous
    leg's interpolation when the client has been silent since it, else the
    last report.
    """
    import authsrv
    import time as _t

    print("\n8. ANIMREF-RE 37: the click-walk latch ends when the LEG does")

    check(authsrv.CLICK_LATCH_LEG_ETA is True,
          "the leg bound is the SHIPPED default; --click-latch-window is "
          "the revert arm (34's 3.0 s constant)",
          f"CLICK_LATCH_LEG_ETA = {authsrv.CLICK_LATCH_LEG_ETA}")
    W = authsrv.GRANT_LOCAL_WINDOW
    now = _t.time()

    # 8a. the leg record: 288 u at the declared 288 u/s is 1.0 s, from the
    # last report when the client has spoken since the previous click.
    st = {"client_pos": (0.0, 0.0), "pos": (0.0, 0.0)}
    t0 = now - 0.5
    st["click_moving_at"] = t0
    leg = authsrv._click_leg_arm(st, (288.0, 0.0), t0, silent=False)
    check(leg is not None and leg["p0"] == (0.0, 0.0)
          and abs(leg["dist"] - 288.0) < 1e-9
          and abs(leg["eta"] - (t0 + 1.0)) < 1e-6,
          "a 288 u click at the declared 288 u/s base arrives 1.0 s after "
          "the click, starting from the last accepted report",
          f"p0={leg and leg['p0']} dist={leg and leg['dist']:.1f} "
          f"eta-t0={leg and leg['eta'] - t0:.3f}")
    check(authsrv._player_body_moving(st) is True,
          "0.5 s into a 1.0 s leg the body is MOVING -- 31's chain pause "
          "must keep pausing through a real click-walk (the known-bad arm "
          "of the other direction)",
          "in flight")
    # 8b. the operator's bug in miniature: past the leg's end but inside
    # the old 3.0 s window, the body is PARKED and the swing may open.
    st["click_moving_at"] = now - 1.5
    leg["t0"], leg["eta"] = now - 1.5, now - 0.5
    check(authsrv._player_body_moving(st) is False,
          "1.5 s after a 1.0 s click the body is PARKED -- under the 3.0 s "
          "constant it read as moving for another 1.5 s and the press was "
          "starved; this is the 60.6% deficit as one assertion",
          f"click age 1.5 s < window {W:.1f} s, yet not moving")
    # 8c. the constant's OTHER failure: a long leg is still walking at 3.5 s.
    st2 = {"client_pos": (0.0, 0.0), "pos": (0.0, 0.0)}
    t0 = now - 3.5
    st2["click_moving_at"] = t0
    leg2 = authsrv._click_leg_arm(st2, (1440.0, 0.0), t0, silent=False)
    check(leg2 is not None and abs(leg2["eta"] - (t0 + 5.0)) < 1e-6
          and authsrv._player_body_moving(st2) is True,
          "3.5 s into a 1440 u (5.0 s) click the body is STILL MOVING -- "
          "the constant declared it parked at 3.0 s and would open a "
          "swing on a walking body",
          f"click age 3.5 s > window {W:.1f} s, still moving")
    # 8d. a chained click starts from the previous leg's model when the
    # client has been silent since it (no report ends a click leg).
    st3 = {"client_pos": (0.0, 0.0), "pos": (0.0, 0.0)}
    t0 = now - 0.5
    st3["click_moving_at"] = t0
    authsrv._click_leg_arm(st3, (288.0, 0.0), t0, silent=False)
    leg3 = authsrv._click_leg_arm(st3, (288.0, 288.0), now, silent=True)
    check(leg3 is not None and abs(leg3["p0"][0] - 144.0) < 1e-6
          and abs(leg3["p0"][1]) < 1e-9
          and abs(leg3["dist"] - math.hypot(144.0, 288.0)) < 1e-6,
          "a second click 0.5 s into a 1.0 s leg starts from the leg's "
          "half-way point, not from the stale report -- the client reports "
          "nothing while click-walking, so the model is the only start",
          f"p0={leg3 and leg3['p0']}")
    leg3b = authsrv._click_leg_arm(st3, (288.0, 288.0), now, silent=False)
    check(leg3b is not None and leg3b["p0"] == (0.0, 0.0),
          "and when the client HAS spoken since (silent=False), the report "
          "is the start and the old leg is ignored",
          f"p0={leg3b and leg3b['p0']}")
    # 8e. the speed is the base this server DECLARED (0x0027), not 288 by
    # assumption: under a +25% stance the same leg is shorter in time.
    st4 = {"client_pos": (0.0, 0.0), "pos": (0.0, 0.0),
           "declared_speed_base": 360.0}
    leg4 = authsrv._click_leg_arm(st4, (360.0, 0.0), now, silent=False)
    check(leg4 is not None and abs(leg4["eta"] - (now + 1.0)) < 1e-6
          and leg4["speed"] == 360.0,
          "the leg runs at the declared base (Rush's 360 u/s here): the "
          "client moves at the 0x0027 base we sent, so the model must too",
          f"speed={leg4 and leg4['speed']} eta-t0={leg4 and leg4['eta'] - now:.3f}")
    # 8f. identity, not age: a leftover leg from an EARLIER click does not
    # bound this latch -- the constant does, as before.
    st5 = {"click_moving_at": now - 1.5, "click_leg": dict(leg, t0=now - 9.0,
                                                          eta=now - 8.0)}
    check(authsrv._player_body_moving(st5) is True,
          "a leg whose stamp is not THIS latch's is a leftover: the latch "
          "falls back to the constant (still inside 3.0 s -> moving), so a "
          "click with no placeable start never reads as parked by accident",
          "leftover leg ignored")
    # 8g. the revert arm restores 34's constant exactly.
    authsrv.CLICK_LATCH_LEG_ETA = False
    try:
        st6 = {"click_moving_at": now - 1.5,
               "click_leg": {"t0": now - 1.5, "p0": (0.0, 0.0),
                             "dest": (288.0, 0.0), "dist": 288.0,
                             "speed": 288.0, "eta": now - 0.5}}
        check(authsrv._player_body_moving(st6) is True,
              "REVERT ARM --click-latch-window: the same parked leg reads "
              "as moving until the 3.0 s constant expires -- 34's shape, "
              "reproducible on purpose",
              "constant bound in force")
    finally:
        authsrv.CLICK_LATCH_LEG_ETA = True

    # 8h. END TO END, the operator's report as a test: click-walk 86 u
    # (0.3 s), press spacebar 0.5 s after the click -> the swing OPENS NOW,
    # not 2.5 s later.
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append(
        (op, vals, label))
    state = _state()
    state["client_pos"] = (0.0, 0.0)
    t0 = _t.time() - 0.5
    state["click_moving_at"] = t0
    authsrv._click_leg_arm(state, (86.4, 0.0), t0, silent=False)
    authsrv.begin_attack(send, state, 10, 0)
    sent.clear()
    authsrv.attack_tick(send, state, 0)
    started = [v for op, v, _l in sent
               if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
               and v[0] == authsrv.agents.GV_ATTACK_STARTED]
    check(started == [[authsrv.agents.GV_ATTACK_STARTED, PLAYER, 10, 0]],
          "END TO END: a press 0.5 s after a 0.3 s click-walk OPENS A "
          "SWING on the first tick -- under the constant this exact press "
          "waited 2.5 s on a parked body (14:32 rows 11-17: latencies "
          "2.22, 2.07, 1.89, 1.72, 1.34 s, all on a 0.34 s leg)",
          f"{started}")
    # KNOWN-BAD ARM: the same press 0.5 s into a 1.0 s leg still waits.
    sent.clear()
    state2 = _state()
    state2["client_pos"] = (0.0, 0.0)
    t0 = _t.time() - 0.5
    state2["click_moving_at"] = t0
    authsrv._click_leg_arm(state2, (288.0, 0.0), t0, silent=False)
    authsrv.begin_attack(send, state2, 10, 0)
    sent.clear()
    authsrv.attack_tick(send, state2, 0)
    started2 = [v for op, v, _l in sent
                if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                and v[0] == authsrv.agents.GV_ATTACK_STARTED]
    check(started2 == [],
          "KNOWN-BAD ARM: a press 0.5 s into a 1.0 s leg still WAITS -- the "
          "body is walking (seen continuing through a press 3/3 on the "
          "12:59 tape), and a swing here would slide",
          f"{started2}")

    # 8i. the 0x003E arm records the leg beside the latch it bounds -- a
    # source pin, because the arm lives inside handle() and cannot be
    # driven here. The string is the call with its arguments, not a
    # substring another line could satisfy.
    src = open(authsrv.__file__, encoding="utf-8").read()
    check(src.count('_click_leg_arm(state, dest, state["click_moving_at"],')
          == 1 and src.count('state["click_moving_at"] = time.time()') == 1,
          "the click arm arms the leg record right after the latch stamp "
          "(one arming site, one latch stamp -- test_cancelwalk pins the "
          "latch's own count)",
          "source pin")


def section_reach_and_approach():
    """ANIMREF-RE 38: the press-time reach, and the approach that walks the
    body into it.

    ATTACK_RANGE = 1500 was "ours entirely; nothing measured it" and the
    operator could attack from far away (36.4). Two numbers replace it, both
    derived: ATTACK_REACH, the press-time test (retail accepts a standing
    Sword press at <= 82.7 u and refuses >= 205.5 u, Daggers 109.7 / 146.3;
    the wiki's 144 sits inside both brackets), and the follow's stop radius
    r + r + 56 = 80 u, read out of the client's own collision resolver
    (0x006011F0 stops a follower dead when the agent named by 0x002A's fifth
    field comes within (rA + rB + pad)^2, pad = 56.0f @0x00A52D60) and
    matching retail's approaches opening at 58-101 u (fit 81 u).

    The approach is retail's contract, OBSERVED on 61 live connections: a
    press with the body out of reach gets a 0x002A follow to the TARGET'S
    OWN position naming the target, re-pathed every 0.500 s while it moves
    and never while it stands, the wire silent both ways until the swing
    opens at reach. Shipped DEFAULT OFF (--attack-approach) for one reason:
    CASE 6's registered predictions need an unsuperseded click leg. Every
    check here drives the real attack_tick with the flag forced on and
    restored after.
    """
    import authsrv
    import struct
    import time as _t

    print("\n9. ANIMREF-RE 38: the reach, and the approach that walks the body "
          "into it")

    UD = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION
    UP = authsrv.GAME_SMSG_AGENT_UPDATE_POSITION
    STARTED = authsrv.agents.GV_ATTACK_STARTED

    def starts(sent):
        return [v for op, v, _l in sent
                if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                and v[0] == STARTED]

    def follows(sent):
        return [v for op, v, _l in sent if op == UD]

    def repins(sent):
        return [v for op, v, _l in sent if op == UP]

    # 9a. the constants and where they come from
    check(authsrv.ATTACK_APPROACH is True,
          "the approach is the DEFAULT since ANIMREF-RE 39 (the operator on "
          "CASE 6: 'spacebar should cancel the move and either run to the "
          "target ... or start attacking immediately'); --no-attack-approach "
          "is the 1500 u revert arm",
          f"ATTACK_APPROACH = {authsrv.ATTACK_APPROACH}")
    radius_on_wire = struct.unpack("<f", struct.pack("<I", 0x41400000))[0]
    check(radius_on_wire == authsrv.BOUNDING_RADIUS == 12.0,
          "BOUNDING_RADIUS is the 0x0020 field-11 float this server sends "
          "(agents.create_agent's 0x41400000), the value the client's ctor "
          "stores at [AgAgent+0xD0] m_boundingRadius -- retail sends 12.0 for "
          "the player and every creature it attacked",
          f"0x41400000 = {radius_on_wire}")
    check(authsrv.follow_stop_radius({}) == 12.0 + 12.0 + 56.0 == 80.0,
          "the follow stops at r_self + r_target + 56: the client's def pad "
          "(f32 @0x00A52D60, written for every def by AgApi 0x005FC290) added "
          "in 0x005FED20 and tested in the resolver 0x006011F0 -- 80 u, "
          "against retail's 58-101 u per row and 81 u joint fit",
          f"{authsrv.follow_stop_radius({})}")
    check(authsrv.follow_stop_radius({"radius": 42.0}) == 110.0,
          "a target carrying its own radius moves the stop, as (rA + rB + 56)^2 "
          "would (retail's radius-42 model 0x200013BC would stop at 110 u -- "
          "a falsifiable prediction nobody has run)",
          f"{authsrv.follow_stop_radius({'radius': 42.0})}")
    check(authsrv.ATTACK_REACH == 128.0
          and 119.6 < authsrv.ATTACK_REACH <= 135.8
          and 82.7 < authsrv.ATTACK_REACH <= 205.5
          and 109.7 < authsrv.ATTACK_REACH <= 146.3
          and not 119.6 < authsrv.ATTACK_REACH_WIKI <= 135.8,
          "ATTACK_REACH = 128, the midpoint of retail's measured edge (119.6, 135.8] "
          "(reachjoin.py, 1z-ds.8: 0 misclassified over 36 presses) and inside both "
          "older DR-free brackets; the wiki's 144 is OUTSIDE the measured one",
          f"ATTACK_REACH = {authsrv.ATTACK_REACH}")
    check(authsrv.follow_stop_radius({}) < authsrv.ATTACK_REACH,
          "the stop radius is inside the reach, so a follow that arrives is "
          "always in reach and the swing opens on arrival",
          f"{authsrv.follow_stop_radius({})} < {authsrv.ATTACK_REACH}")
    saved = authsrv.ATTACK_APPROACH
    authsrv.ATTACK_APPROACH = False
    check(authsrv.attack_reach() == authsrv.ATTACK_RANGE == 1500.0,
          "REVERT ARM (--no-attack-approach): the reach is the old 1500 u and "
          "no follow is sent",
          f"attack_reach() = {authsrv.attack_reach()}")
    authsrv.ATTACK_APPROACH = True
    try:
        check(authsrv.attack_reach() == authsrv.ATTACK_REACH == 128.0,
              "the shipped reach is the measured 128 u",
              f"attack_reach() = {authsrv.attack_reach()}")
        # 1z-ds.9: a PARKED press at 136 u -- between the two reaches. Retail walks
        # in from there (its follows start at 135.8); the wiki's 144 swung at once.
        def parked_at(dist, reach):
            got = []
            snd = lambda op, vals, label="", quiet=False: got.append((op, label))  # noqa: E731
            stp = _state()
            stp["agents"][10]["pos"] = (dist, 0.0)
            saved_r = authsrv.ATTACK_REACH
            authsrv.ATTACK_REACH = reach
            try:
                authsrv.begin_attack(snd, stp, 10, 0)
                authsrv.attack_tick(snd, stp, 0)
            finally:
                authsrv.ATTACK_REACH = saved_r
            return (any("player swings" in l for _o, l in got),
                    any(op == authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION for op, _l in got))
        sw136, fo136 = parked_at(136.0, authsrv.ATTACK_REACH)
        sw136w, fo136w = parked_at(136.0, authsrv.ATTACK_REACH_WIKI)
        sw120, _fo120 = parked_at(120.0, authsrv.ATTACK_REACH)
        check(fo136 and not sw136 and sw120,
              "1z-ds.9: a parked press at 136 u is walked in (retail's follows start at "
              "135.8) and one at 120 u swings at once (retail's swings reach 119.6)",
              f"136: swing {sw136} follow {fo136}; 120: swing {sw120}")
        check(sw136w and not fo136w,
              "KNOWN-BAD ARM (--attack-reach-wiki): the same 136 u press swings at once "
              "from the wiki's 144 -- what every build before 2026-10-02 did",
              f"136 under 144: swing {sw136w} follow {fo136w}")

        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append(
            (op, vals, label))

        def fresh(target_xy, player_xy=(0.0, 0.0)):
            st = _state()
            st["agents"][10]["pos"] = target_xy
            st["pos"] = player_xy
            st["client_pos"] = player_xy
            st["plane"] = 0
            authsrv.begin_attack(send, st, 10, 0)
            sent.clear()
            return st

        # 9b. a standing press in reach: the swing itself is the first
        # reaction, no follow (retail 0.029-0.045 s, n=8, no 0x002A)
        st = fresh((100.0, 0.0))
        authsrv.attack_tick(send, st, 0)
        check(len(starts(sent)) == 1 and follows(sent) == []
              and st.get("approach") is None,
              "IN REACH (100 u <= 144): the swing opens on the first tick and "
              "no follow goes out -- retail's in-reach cell",
              f"starts {len(starts(sent))}, follows {follows(sent)}")

        # 9c. a press at 400 u: a follow to the TARGET'S OWN position naming
        # it, the latch and leg armed to the stop point, the copy walking,
        # and NO swing this tick
        st = fresh((400.0, 0.0))
        t_press = _t.time()
        authsrv.attack_tick(send, st, 0)
        f = follows(sent)
        check(f == [[1, (400.0, 0.0), 0, 0, 10]] and starts(sent) == [],
              "OUT OF REACH (400 u): one 0x002A [player, target's own point, "
              "plane, plane, target] and no swing -- retail's shape (61/61 "
              "name the target; the point is bit-exact on 16/16 never-moved "
              "targets)",
              f"follows {f}, starts {starts(sent)}")
        leg = st.get("click_leg")
        ap = st.get("approach")
        check(leg is not None and ap is not None
              and leg["t0"] == st.get("click_moving_at") == ap["t0"]
              and abs(leg["dist"] - 320.0) < 1e-6
              and abs((leg["eta"] - leg["t0"]) - 320.0 / 288.0) < 1e-6
              and abs(leg["dest"][0] - 320.0) < 1e-6,
              "the follow arms the click latch and a leg to the STOP POINT "
              "(80 u short of the target: 320 u at 288 u/s), identity by the "
              "latch stamp -- the same record a click leg uses",
              f"leg {leg}")
        check(st.get("dest") is not None
              and abs(st["dest"][0] - 320.0) < 1e-6
              and abs(st["dest"][1]) < 1e-6,
              "and the server's own copy walks there: dest = the stop point "
              "for the world tick's integrator (retail's server owns the leg)",
              f"dest {st.get('dest')}")
        check(authsrv._player_body_moving(st) is True,
              "the chain pauses while the follow walks -- 31's rule through "
              "the latch the follow armed",
              "moving")
        check(ap["target"] == 10 and ap["told"] == (400.0, 0.0)
              and abs(ap["sent_at"] - t_press) < 1.0,
              "the follow record names its target, the point it told, and "
              "when",
              f"approach {ap}")

        # 9d. the next tick, target unmoved, inside the re-path interval:
        # nothing more goes out (retail: 0 of 31 re-paths on a standing
        # target)
        sent.clear()
        authsrv.attack_tick(send, st, 0)
        check(follows(sent) == [] and starts(sent) == [],
              "a standing target gets NO re-path and the swing still waits",
              f"follows {follows(sent)}, starts {starts(sent)}")

        # 9e. the target moves and the 0.5 s tick comes round: a re-path to
        # its CURRENT position, the leg re-armed from the copy's position
        st["agents"][10]["pos"] = (400.0, 50.0)
        st["approach"]["sent_at"] -= authsrv.FOLLOW_REPATH_INTERVAL + 0.1
        sent.clear()
        authsrv.attack_tick(send, st, 0)
        check(follows(sent) == [[1, (400.0, 50.0), 0, 0, 10]]
              and starts(sent) == [] and st["approach"]["told"] == (400.0, 50.0),
              "a MOVED target gets one re-path to where it is now, on the "
              "0.500 s tick (retail p50 0.504 s, 35 intervals)",
              f"follows {follows(sent)}")
        # ... but not again before the interval has passed
        st["agents"][10]["pos"] = (400.0, 100.0)
        sent.clear()
        authsrv.attack_tick(send, st, 0)
        check(follows(sent) == [],
              "and not again inside the interval, however far it moved",
              f"follows {follows(sent)}")

        # 9f. ARRIVAL: the integrator parks the copy at the stop point and
        # the leg's eta passes -> the swing opens this tick, the follow is
        # forgotten, and no stop message was sent (retail 8/9 clean rows)
        st["pos"] = st["dest"]
        st["dest"] = None
        st["click_leg"]["eta"] = _t.time() - 0.01
        st["approach"]["eta"] = st["click_leg"]["eta"]
        sent.clear()
        authsrv.attack_tick(send, st, 0)
        stopmsgs = [v for op, v, _l in sent
                    if op == authsrv.GAME_SMSG_AGENT_STOP_MOVING]
        check(len(starts(sent)) == 1 and st.get("approach") is None
              and follows(sent) == [] and stopmsgs == [],
              "ARRIVAL: the swing opens on the first tick after the leg ends, "
              "the follow is forgotten, no 0x0028 and no further movement -- "
              "retail's natural path",
              f"starts {len(starts(sent))}, approach {st.get('approach')}, "
              f"stops {stopmsgs}")

        # 9g. a client report ends the follow (retail: client steering after a
        # press wins, 11/15 chains withheld): the arms clear the latch and call
        # _approach_abandon, which forgets the follow AND the copy's walk
        st = fresh((400.0, 0.0))
        authsrv.attack_tick(send, st, 0)
        st["click_moving_at"] = None       # what the 0x003D / 0x0047 arms do
        authsrv._approach_abandon(st)
        check(st.get("approach") is None and st.get("dest") is None,
              "a report abandons the follow and stops the integrator walk -- a "
              "stale dest would march the model to a point the body left",
              f"approach {st.get('approach')}, dest {st.get('dest')}")
        sent.clear()
        authsrv.attack_tick(send, st, 0)
        check(len(follows(sent)) == 1,
              "and the next tick, still out of reach with the target kept, "
              "starts a fresh follow from where the copy now is -- a press "
              "after steering is answered again, as retail re-paths (11/13)",
              f"follows {follows(sent)}")

        # 9h. a retarget ends the follow it named and starts the new one
        st = fresh((400.0, 0.0))
        authsrv.attack_tick(send, st, 0)
        st["agents"][11] = dict(_fresh_agent(), pos=(0.0, 400.0))
        authsrv.begin_attack(send, st, 11, 0)
        sent.clear()
        authsrv.attack_tick(send, st, 0)
        check(follows(sent) == [[1, (0.0, 400.0), 0, 0, 11]]
              and st["approach"]["target"] == 11,
              "a RETARGET forgets the old follow and sends one for the new "
              "target the same tick",
              f"follows {follows(sent)}")

        # 9i. THE SNAP GUARD: after a click-walk the server's copy sits at the
        # leg's START while the modelled body stands at its END; a 0x002A
        # would hand the body to the sync nodes and snap it back (the client's
        # reprieve radius is 100 u). The follow is preceded by a 0x002C re-pin
        # at the modelled end, and the leg starts from there.
        st = fresh((900.0, 0.0))
        t0 = _t.time() - 3.0
        st["click_moving_at"] = t0
        st["click_leg"] = authsrv._leg_record((0.0, 0.0), (500.0, 0.0), t0,
                                              288.0)
        sent.clear()
        authsrv.attack_tick(send, st, 0)
        ops = [op for op, _v, _l in sent]
        check(ops[:2] == [UP, UD] and repins(sent) == [[1, [500.0, 0.0], 0]],
              "SNAP GUARD: the copy 500 u from the modelled click-leg end gets "
              "a 0x002C AT THE MODELLED END before the 0x002A -- 0x002C's "
              "handler clears the history chain first, so no reprieve test "
              "runs behind it (p5-resync-disarm 1)",
              f"ops {[hex(o) for o in ops[:3]]}, repins {repins(sent)}")
        check(st["pos"] == (500.0, 0.0)
              and abs(st["click_leg"]["dist"] - 320.0) < 1e-6
              and st["click_leg"]["p0"] == (500.0, 0.0),
              "and the follow leg starts from the re-pinned point: 400 u to "
              "the target, 320 u to the stop",
              f"pos {st['pos']}, leg {st['click_leg']}")
        # inside the reprieve radius: no re-pin
        st = fresh((900.0, 0.0))
        t0 = _t.time() - 3.0
        st["click_moving_at"] = t0
        st["click_leg"] = authsrv._leg_record((0.0, 0.0), (60.0, 0.0), t0,
                                              288.0)
        sent.clear()
        authsrv.attack_tick(send, st, 0)
        check(repins(sent) == [] and len(follows(sent)) == 1,
              "a copy within the 100 u reprieve of the modelled body gets no "
              "re-pin -- the client's own test would pass",
              f"repins {repins(sent)}")

        # 9k. MOVECODE-1z-dr, the KEYBOARD regime (the owner's "short backwards
        # warp when pressing W and attacking", 20261001T185315): no click latch,
        # so the snap guard's model was the bare last report -- the body as it was
        # up to a second ago. It is now that report advanced along its heading.
        def kbd_state(copy_xy, age=1.0):
            st = fresh((0.0, 3000.0), player_xy=copy_xy)
            st["client_pos"] = (0.0, 0.0)
            st["client_pos_at"] = _t.time() - age
            st["client_heading"] = (0.0, 766.0, 1, st["client_pos_at"])
            return st
        st = kbd_state((0.0, 288.0))           # the copy where the body is (135.21's shape)
        authsrv.attack_tick(send, st, 0)
        check(repins(sent) == [] and len(follows(sent)) == 1,
              "KEYBOARD, the copy at the body: the report 1.0 s old advanced 288 u "
              "along its heading IS the copy, so no re-pin -- where the bare report "
              "re-pinned 288 u behind (the short backwards warp)",
              f"repins {repins(sent)}")
        st = kbd_state((0.0, 1900.0))          # the copy run ahead (128.40's shape)
        authsrv.attack_tick(send, st, 0)
        rp = repins(sent)
        check(len(rp) == 1 and abs(rp[0][1][0]) < 0.5 and abs(rp[0][1][1] - 288.0) < 2.0,
              "KEYBOARD, the copy 1,612 u ahead: the re-pin lands on the ESTIMATED "
              "body (0, 288), not on the 1 s old report (0, 0)",
              f"repins {rp}")
        st = kbd_state((0.0, 288.0), age=3.0)  # past the measured ages: no estimate
        authsrv.attack_tick(send, st, 0)
        rp = repins(sent)
        check(len(rp) == 1 and rp[0][1] == [0.0, 0.0],
              "a report older than KBD_BODY_ESTIMATE_MAX_AGE is not advanced: the "
              "old behaviour, said by its own branch", f"repins {rp}")
        # ROUND 2 (20261001T192303, "still warping ... Q or E to strafe then
        # attack"): the client is silent 1.3-1.7 s under a lead chain, and strafes
        # walk at their family rate.
        st = kbd_state((0.0, 1.7 * 288.0), age=1.7)
        authsrv.attack_tick(send, st, 0)
        check(repins(sent) == [],
              "ROUND 2: a report 1.7 s old (the strafe session's ages) is still "
              "advanced -- the cap is the measured 2.0 s -- so no re-pin",
              f"repins {repins(sent)}")
        st = kbd_state((0.0, 1.5 * 0.66 * 288.0), age=1.5)
        st["client_heading"] = (0.0, 766.0, 4, st["client_pos_at"])   # a strafe
        authsrv.attack_tick(send, st, 0)
        check(repins(sent) == [],
              "ROUND 2: a strafe (movementType 4) is advanced at its family rate, "
              "0.66 x 288 u/s -- 285 u in 1.5 s -- so no re-pin",
              f"repins {repins(sent)}")
        st = kbd_state((0.0, 700.0), age=3.0)
        st["kbd_kill_point"], st["kbd_kill_at"] = (0.0, 700.0), _t.time()
        authsrv.attack_tick(send, st, 0)
        check(repins(sent) == [],
              "ROUND 2: past the cap, the press's OWN fresh lead kill is the body "
              "(it matched the estimate within 80 u at 20 of 22 kills that day): "
              "the copy it just re-aimed agrees, so no re-pin", f"repins {repins(sent)}")
        _sv_kbe = authsrv.KBD_BODY_ESTIMATE
        authsrv.KBD_BODY_ESTIMATE = False
        try:
            st = kbd_state((0.0, 288.0))
            authsrv.attack_tick(send, st, 0)
            rp = repins(sent)
            check(len(rp) == 1 and rp[0][1] == [0.0, 0.0],
                  "KNOWN-BAD (--no-kbd-body-estimate): the same press re-pins at the "
                  "bare report, 288 u behind the body -- the owner's warp",
                  f"repins {rp}")
        finally:
            authsrv.KBD_BODY_ESTIMATE = _sv_kbe

        # 9j. the copy already inside the stop radius but outside reach cannot
        # happen (80 < 144); inside reach nothing is sent even with a stale
        # follow record from another target
        st = fresh((60.0, 0.0))
        st["approach"] = {"target": 99, "t0": 1.0, "told": (0.0, 0.0),
                          "sent_at": 0.0, "eta": 2.0}
        st["dest"] = (30.0, 0.0)
        sent.clear()
        authsrv.attack_tick(send, st, 0)
        check(st.get("approach") is None and st.get("dest") is None
              and len(starts(sent)) == 1 and follows(sent) == [],
              "a leftover follow naming another target is abandoned, its walk "
              "stopped, and the in-reach swing opens",
              f"approach {st.get('approach')}, starts {len(starts(sent))}")
    finally:
        authsrv.ATTACK_APPROACH = saved

    # 9k. source pins: the three report/click arms end a follow, and the two
    # target-loss branches of attack_tick do too. Exact strings, counted.
    src = open(authsrv.__file__, encoding="utf-8").read()
    n_arms = src.count("_approach_abandon(state)   # ANIMREF-RE 38")
    n_all = (src.count("_approach_abandon(state)")
             - src.count("def _approach_abandon(state)"))   # the def is not a call
    check(n_arms == 3 and n_all == 12,
          "the 0x003D, 0x0047 and 0x003E arms each abandon the follow (3 "
          "tagged sites), attack_tick's two target-loss branches do (2), "
          "approach_tick's retarget branch (1), since ANIMREF-RE 39 a "
          "move command (cancel_on_move) and the press that ends a click leg "
          "(_press_supersedes), since the SLICE arc the interact-walk "
          "(interact_route: a click supersedes a follow, SLICE-B5) and the "
          "attack skill whose target dies on the approach (cast_tick's "
          "approach arm, SLICE-C2), the player's death (kill_player, "
          "SLICE-F23: a corpse does not walk), and since RANGERPRE-S15 the "
          "pickup press (handle_pickup: a follow still on record goes BEFORE "
          "the pickup's dest is written, or the world tick's abandon takes "
          "that dest with it -- test_loot 3k) -- 12 call sites, no more",
          f"arms {n_arms}, all {n_all}")
    check(src.count('state["click_moving_at"] = now') == 2,
          "the follow stamps the latch once, with the tick's `now` -- not "
          "time.time(), which test_cancelwalk pins to the click arm alone -- "
          "and interact_route stamps it once more as the click it is (SLICE-"
          "B5: the 0x003E arm's own preparation, `now` read once above it)",
          "source pin")


def section_press_supersedes_and_move_ends():
    """ANIMREF-RE 39: the operator on CASE 6, in two sentences.

    "we're not supposed to wait to arrive before attacking. spacebar should
    cancel the move and either run to the target to get in range or start
    attacking immediately if they're already in range." -- and -- "once you
    issue a move command you stop autoattacking."

    Both are retail's contract. The first is 37.3's own reading (the press
    supersedes the leg; the server drives the body), which 37.5 built as a
    WAIT. The second is MEASURED on the live tapes (scratch chainmove.py):
    of 28 consecutive same-target swing pairs with a player move command
    between them, all 28 carry a re-press between the move and the next
    swing, 0 chains resumed without one, 39 chains ended at a move with no
    press. 31's "the chain survives a move" counted the absence of a wire
    close as survival.

    The press: a 0x0026 with a click leg in flight clears the latch and its
    record, sends ONE 0x002C at the modelled body (the only message that
    halts the client's segment without handing the body to a sync copy
    parked at the leg's start), and lets the tick swing (in reach) or follow
    (out of reach) that instant. The move: cancel_on_move forgets the target
    on any move command; the swing in flight keeps 32's landing split.
    """
    import authsrv
    import time as _t

    print("\n10. ANIMREF-RE 39: the press supersedes the walk; a move ends "
          "the chain")

    UD = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION
    UP = authsrv.GAME_SMSG_AGENT_UPDATE_POSITION
    STARTED = authsrv.agents.GV_ATTACK_STARTED
    STOPPED = authsrv.agents.GV_ATTACK_STOPPED

    def starts(sent):
        return [v for op, v, _l in sent
                if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                and v[0] == STARTED]

    def stops(sent):
        return [v for op, v, _l in sent
                if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                and v[0] == STOPPED]

    check(authsrv.PRESS_SUPERSEDES_LEG is True
          and authsrv.MOVE_ENDS_CHAIN is True
          and authsrv.ATTACK_APPROACH is True,
          "all three are the SHIPPED default; --press-waits-for-leg, "
          "--move-keeps-target and --no-attack-approach revert them one at a "
          "time",
          f"press={authsrv.PRESS_SUPERSEDES_LEG} move={authsrv.MOVE_ENDS_CHAIN} "
          f"approach={authsrv.ATTACK_APPROACH}")

    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append(
        (op, vals, label))

    def walking(target_xy, leg_len=500.0):
        """A body 1.0 s into a click leg from (0,0) toward (leg_len, 0),
        target at target_xy; the server's copy still at the leg's start."""
        st = _state()
        st["agents"][10]["pos"] = target_xy
        st["pos"] = (0.0, 0.0)
        st["client_pos"] = (0.0, 0.0)
        st["plane"] = 0
        t0 = _t.time() - 1.0
        st["click_moving_at"] = t0
        st["click_leg"] = authsrv._leg_record((0.0, 0.0), (leg_len, 0.0), t0,
                                              288.0)
        sent.clear()
        return st

    # 10a. IN REACH: a press mid-leg ends the leg, re-pins the body where the
    # model puts it (288 u along), and the swing opens on the very next tick
    st = walking((350.0, 0.0))
    authsrv._press_supersedes(send, st, 0, 10)
    authsrv.begin_attack(send, st, 10, 0)
    repins = [v for op, v, _l in sent if op == UP]
    check(st.get("click_moving_at") is None and st.get("click_leg") is None
          and len(repins) == 1 and abs(repins[0][1][0] - 288.0) < 1.0
          and abs(st["pos"][0] - 288.0) < 1.0,
          "the press ENDS the click leg: latch and record cleared, ONE 0x002C "
          "at the modelled body (1.0 s at 288 u/s = 288 u along), the "
          "server's copy moved there",
          f"latch {st.get('click_moving_at')}, repins {repins}, pos {st['pos']}")
    sent.clear()
    authsrv.attack_tick(send, st, 0)
    check(len(starts(sent)) == 1 and not [v for op, v, _l in sent if op == UD],
          "IN REACH (62 u from the re-pinned body): the swing opens on the "
          "first tick, no follow -- 'start attacking immediately if they're "
          "already in range'",
          f"starts {len(starts(sent))}")

    # 10b. OUT OF REACH: the same press, target 900 u out: re-pin, then the
    # tick sends the follow from the re-pinned point and no swing yet
    st = walking((900.0, 0.0))
    authsrv._press_supersedes(send, st, 0, 10)
    authsrv.begin_attack(send, st, 10, 0)
    sent.clear()
    authsrv.attack_tick(send, st, 0)
    follows = [v for op, v, _l in sent if op == UD]
    leg = st.get("click_leg")
    check(follows == [[1, (900.0, 0.0), 0, 0, 10]] and starts(sent) == []
          and leg is not None and abs(leg["p0"][0] - 288.0) < 1.0
          and abs(leg["dist"] - (612.0 - 80.0)) < 1.0,
          "OUT OF REACH: the follow goes out from the re-pinned body (612 u "
          "to the target, 532 u to the stop), no swing until arrival -- "
          "'run to the target to get in range'",
          f"follows {follows}, leg {leg}")

    # 10c. the revert arm: --press-waits-for-leg leaves the leg alone
    saved = authsrv.PRESS_SUPERSEDES_LEG
    authsrv.PRESS_SUPERSEDES_LEG = False
    try:
        st = walking((350.0, 0.0))
        authsrv._press_supersedes(send, st, 0, 10)
        check(st.get("click_moving_at") is not None and sent == [],
              "REVERT ARM (--press-waits-for-leg): the press leaves the leg "
              "in flight and sends nothing -- 37's wait",
              f"latch {st.get('click_moving_at')}, sent {sent}")
    finally:
        authsrv.PRESS_SUPERSEDES_LEG = saved

    # 10d. a press on the target our own follow is walking to is left alone
    st = _state()
    st["agents"][10]["pos"] = (900.0, 0.0)
    st["pos"] = (0.0, 0.0)
    st["client_pos"] = (0.0, 0.0)
    st["plane"] = 0
    authsrv.begin_attack(send, st, 10, 0)
    authsrv.attack_tick(send, st, 0)        # starts the follow
    t_follow = st["click_moving_at"]
    sent.clear()
    authsrv._press_supersedes(send, st, 0, 10)
    check(st.get("click_moving_at") == t_follow and st.get("approach")
          and sent == [],
          "a repeat press on the target OUR follow is walking to leaves the "
          "follow alone (retail re-paths rather than halts, 11/13)",
          f"latch kept {st.get('click_moving_at') == t_follow}, sent {sent}")

    # 10e. a parked body: the press sends nothing extra and the swing opens
    st = _state()
    st["agents"][10]["pos"] = (100.0, 0.0)
    st["pos"] = (0.0, 0.0)
    st["client_pos"] = (0.0, 0.0)
    sent.clear()
    authsrv._press_supersedes(send, st, 0, 10)
    authsrv.begin_attack(send, st, 10, 0)
    sent.clear()
    authsrv.attack_tick(send, st, 0)
    check(len(starts(sent)) == 1
          and not [v for op, v, _l in sent if op == UP],
          "a PARKED body gets no re-pin and swings at once -- the STOP-last "
          "case that always worked",
          f"starts {len(starts(sent))}")

    # 10f. A MOVE ENDS THE CHAIN. Post-landing move: the target is forgotten,
    # no close goes out (retail sends none: 87/100 moves carry no property
    # 3), and nothing swings on the next tick.
    st = _state()
    st["agents"][10]["pos"] = (50.0, 0.0)
    st["pos"] = (0.0, 0.0)
    authsrv.begin_attack(send, st, 10, 0)
    authsrv.attack_tick(send, st, 0)        # the swing opens
    st["player_swing"]["lands_at"] = _t.time() - 0.01   # landed
    sent.clear()
    authsrv.cancel_on_move(send, st, 0)
    check(st.get("attacking") is None and stops(sent) == [],
          "POST-LANDING move: the target is FORGOTTEN and no attack_stopped "
          "goes out -- retail's player re-presses (28/28), the wire carries "
          "no close",
          f"attacking {st.get('attacking')}, stops {stops(sent)}")
    sent.clear()
    for _ in range(3):
        authsrv.attack_tick(send, st, 0)
    check(starts(sent) == [],
          "and the chain does NOT resume when the body stops: the next swing "
          "needs a press ('once you issue a move command you stop "
          "autoattacking')",
          f"starts {starts(sent)}")

    # 10g. pre-landing move: 32's split still holds -- the stop pair goes out
    st = _state()
    st["agents"][10]["pos"] = (50.0, 0.0)
    st["pos"] = (0.0, 0.0)
    authsrv.begin_attack(send, st, 10, 0)
    authsrv.attack_tick(send, st, 0)
    sent.clear()
    authsrv.cancel_on_move(send, st, 0)
    check(st.get("attacking") is None
          and stops(sent) == [[STOPPED, PLAYER, 0]],
          "PRE-LANDING move: the swing in flight is cancelled with the stop "
          "pair and the target forgotten -- 32's landing split is untouched",
          f"attacking {st.get('attacking')}, stops {stops(sent)}")

    # 10h. a move ends OUR follow too
    st = _state()
    st["agents"][10]["pos"] = (900.0, 0.0)
    st["pos"] = (0.0, 0.0)
    st["client_pos"] = (0.0, 0.0)
    authsrv.begin_attack(send, st, 10, 0)
    authsrv.attack_tick(send, st, 0)
    check(st.get("approach") is not None, "a follow is in flight", "")
    sent.clear()
    authsrv.cancel_on_move(send, st, 0)
    check(st.get("approach") is None and st.get("dest") is None
          and st.get("attacking") is None,
          "a move command during the approach ends the follow, the copy's "
          "walk and the order -- client steering wins (retail 11/15)",
          f"approach {st.get('approach')}, dest {st.get('dest')}")

    # 10i. the revert arm: --move-keeps-target restores 32's post-landing keep
    saved = authsrv.MOVE_ENDS_CHAIN
    authsrv.MOVE_ENDS_CHAIN = False
    try:
        st = _state()
        st["agents"][10]["pos"] = (50.0, 0.0)
        st["pos"] = (0.0, 0.0)
        authsrv.begin_attack(send, st, 10, 0)
        authsrv.attack_tick(send, st, 0)
        st["player_swing"]["lands_at"] = _t.time() - 0.01
        sent.clear()
        authsrv.cancel_on_move(send, st, 0)
        check(st.get("attacking") == 10,
              "REVERT ARM (--move-keeps-target): a post-landing move keeps "
              "the target, 32's shape",
              f"attacking {st.get('attacking')}")
    finally:
        authsrv.MOVE_ENDS_CHAIN = saved

    # 10j. source pin: the press arm calls the supersede BEFORE begin_attack
    src = open(authsrv.__file__, encoding="utf-8").read()
    i = src.find("_press_supersedes(send, state, conn_id, values[1],")
    j = src.find("begin_attack(send, state, values[1], conn_id, rec=rec)")
    check(i > 0 and j > i and j - i < 200,
          "the 0x0026 arm supersedes the leg, then takes the order -- in that "
          "order, adjacent (and since ANIMREF-RE 41 hands the recorder over, "
          "so the order's press_verdict row can be written)",
          f"offsets {i}, {j}")

    # 10k-o. MOVECODE-1z-ds.29: a press while OUR follow to that target is the leg in force is
    # spared whatever `approach` holds -- arrived by eta or by distance (retail 0 pins in 160).
    def own_follow():
        st = _state()
        st["agents"][10]["pos"] = (900.0, 0.0)
        st["pos"] = (0.0, 0.0)
        st["client_pos"] = (0.0, 0.0)
        st["plane"] = 0
        authsrv.begin_attack(send, st, 10, 0)
        authsrv.attack_tick(send, st, 0)        # the follow: marker, latch and leg, one instant
        return st

    def repress(st, on=True, target=10):
        rec = _Rec()
        saved_sp = authsrv.PRESS_SPARES_OWN_FOLLOW
        authsrv.PRESS_SPARES_OWN_FOLLOW = on
        sent.clear()
        try:
            authsrv._press_supersedes(send, st, 0, target, rec=rec)
        finally:
            authsrv.PRESS_SPARES_OWN_FOLLOW = saved_sp
        return [v for op, v, _l in sent if op == UP], rec.events

    st = own_follow()
    fol, latch = st["follow_order_at"], st["click_moving_at"]
    st["approach"] = None                                  # approach_tick's arrival
    st["click_leg"]["eta"] = _t.time() - 0.05              # by its eta
    pins, rows = repress(st)
    spared = [r for r in rows if r["kind"] == "press_spared"]
    check(pins == [] and st.get("click_moving_at") == latch and st.get("click_leg") is not None
          and st.get("follow_order_at") == fol
          and len(spared) == 1 and spared[0]["arrived"] is True,
          "10k. a press after OUR follow arrived (by its eta; `approach` already cleared) sends "
          "NO 0x002C and keeps the latch, the leg and the marker -- retail 0 pins in 65 such "
          "presses (122155 16.146, 201011 113.425 were pinned)",
          f"pins {pins}, latch kept {st.get('click_moving_at') == latch}, rows {spared}")
    st = own_follow()
    st["approach"] = None                                  # arrived by distance...
    st["click_leg"]["eta"] = _t.time() + 0.6               # ...before its eta
    pins, rows = repress(st)
    check(pins == [] and authsrv._player_body_moving(st)
          and [r["arrived"] for r in rows if r["kind"] == "press_spared"] == [False],
          "10l. arrived BY DISTANCE before the eta: spared too, and the body still reads as "
          "walking until the leg's eta -- retail's walk-in gate, not a pin and a swing at once",
          f"pins {pins}, moving {authsrv._player_body_moving(st)}")
    st = own_follow()
    st["approach"] = None
    st["click_leg"]["eta"] = _t.time() - 0.05
    pins, _rows = repress(st, on=False)
    check(len(pins) == 1 and st.get("click_moving_at") is None,
          "10m. KNOWN-BAD ARM (--press-repins-own-follow): the same press puts one PRESS ENDS "
          "THE WALK 0x002C on the wire and ends the leg -- the shape of 122155 16.146",
          f"pins {pins}")
    st = own_follow()
    st["approach"] = None
    st["agents"][11] = dict(_fresh_agent(), pos=(0.0, 400.0))
    pins_o, _r = repress(st, target=11)
    st = own_follow()
    st["approach"] = None
    st["click_moving_at"] = _t.time()                      # a 0x003E click since our follow
    pins_c, _r = repress(st)
    st = own_follow()
    st["approach"] = None
    st["follow_order_at"] = (st["follow_order_at"][0], 777, st["follow_order_at"][2])  # a pickup's
    pins_p, _r = repress(st)
    check(len(pins_o) == 1 and len(pins_c) == 1 and len(pins_p) == 1,
          "10n. CONTROLS: a press on ANOTHER target, a press after a click re-stamped the latch, "
          "and a press during a PICKUP walk (its marker names the item) still end the walk",
          f"other {pins_o}, click {pins_c}, pickup {pins_p}")
    src = open(authsrv.__file__, encoding="utf-8").read()
    args = open(os.path.join(os.path.dirname(authsrv.__file__), "serverargs.py"),
                encoding="utf-8").read()
    check(authsrv.PRESS_SPARES_OWN_FOLLOW is True
          and src.count('if why not in ("parked", "pinned-parked", "no-report", "click-walk"):') == 1
          and "--press-repins-own-follow" in args and "if a.press_repins_own_follow:" in src,
          "10o. the flag ships on, the spared press's reckon ('click-walk') is a quiet refusal, "
          "and the revert arm is wired")


class _Rec:
    """The Recorder's event() shape, kept in memory: what a capture would
    hold, readable by the checks."""

    def __init__(self):
        self.events = []

    def event(self, kind, **kw):
        kw["kind"] = kind
        self.events.append(kw)


def section_press_ends_kbd_latch():
    """ANIMREF-RE 41: the press supersedes the KEYBOARD belief, and every
    press leaves a row.

    THE SYMPTOM (RUN-FEEL, 2026-09-03 08:46): "couldn't resume attacking
    after some point". The point was the session's first 0x003D at 23.56 s:
    five keyboard reports, then NO 0x0047 for the remaining 16.6 s -- the
    tap shows the drawn body snapped ~498 u onto our own 520 u keyboard
    lead's endpoint at 26.85 s, and the release never reported (why is
    MOVECODE 1z-u's, FINDINGS 41.2) -- so `kbd_moving_at` stayed armed while
    the body stood parked from 26.85 s and the Hatcher swung at it.
    22 presses after that point: 2 got a follow, 0 got a swing. Before it:
    4 of 5 fresh presses swung, the fifth lost its order to a click 1 ms
    behind it (retail-faithful, MOVE_ENDS_CHAIN). The handed-down diagnosis
    blamed the CLICK latch armed by refused clicks; the capture refutes it --
    the click latch is ended by every press (_press_supersedes) and the
    starved presses had no click within 215 ms.

    RETAIL (live corpus, 267 presses): of the 48 whose last movement input
    was a 0x003D no older than 0.5 s, 9 opened a swing and 15 a follow within
    0.2 s -- it does not wait for a stop. And under MOVE_ENDS_CHAIN the
    keyboard latch has no job at the swing gate: a 0x003D forgets the target,
    so `attacking` is set again only by a press. So the gate reads the latch
    as ended by a newer press (`attack_press_at`), and a report newer than
    the press re-arms it -- the client steering wins, as on retail (11/15).

    THE INSTRUMENT: a `press_verdict` row per press -- the branch that
    answered it (swing / follow, with latency) or the FIRST branch that
    refused it (moving + which latch and its age, interval, reach, cast,
    move-ended-order, target-gone, dead-player), plus repeat / no-target /
    dead-target from begin_attack itself. The first refusal PRINTS, the R11
    rule applied to the swing.
    """
    import authsrv
    import time as _t

    print("\n11. ANIMREF-RE 41: the press supersedes the keyboard belief; every "
          "press leaves a row")

    STARTED = authsrv.agents.GV_ATTACK_STARTED
    UD = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION

    def starts(sent):
        return [v for op, v, _l in sent
                if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                and v[0] == STARTED]

    def rows(rec, reason=None):
        return [e for e in rec.events if e["kind"] == "press_verdict"
                and (reason is None or e["reason"] == reason)]

    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append(
        (op, vals, label))

    check(authsrv.PRESS_ENDS_KBD_LATCH is True,
          "the press-ends-the-keyboard-belief rule is the SHIPPED default; "
          "--press-waits-for-stop is the revert arm",
          f"PRESS_ENDS_KBD_LATCH = {authsrv.PRESS_ENDS_KBD_LATCH}")

    # 11a. the reader: a keyboard latch OLDER than the press does not move
    # the body; one NEWER (or equal) does.
    now = _t.time()
    check(authsrv._player_body_moving(
              {"kbd_moving_at": now - 0.29, "attack_press_at": now}) is False,
          "a keyboard report 0.29 s BEFORE the press (the 08:46 24.44 s "
          "press, latch age 0.29 s, no stop ever) no longer reads as moving",
          "press newer than the latch")
    check(authsrv._player_body_moving(
              {"kbd_moving_at": now, "attack_press_at": now - 0.1}) is True,
          "a keyboard report AFTER the press re-arms the belief -- the "
          "client steering wins (retail 11/15), and MOVE_ENDS_CHAIN ends the "
          "chain on that same report",
          "report newer than the press")
    check(authsrv._player_body_moving(
              {"kbd_moving_at": now, "attack_press_at": now}) is True,
          "equal stamps: the report speaks last (>=), failing toward the "
          "pause",
          "equal stamps")
    check(authsrv._player_body_moving({"kbd_moving_at": now - 600.0}) is True,
          "and with no press at all the raw latch holds, so rule 1 (the "
          "grant gate) and cast_stop_reckon -- which read the latch itself, "
          "never the stamp -- see exactly what they saw before",
          "no press: unchanged")

    # 11b. END TO END, the 08:46 shape: a 0x003D 0.29 s ago, no 0x0047 ever,
    # the Hatcher 86 u away -> the press opens the swing on the FIRST tick,
    # and the row says so.
    rec = _Rec()
    state = _state()
    state["agents"][10]["pos"] = (86.0, 0.0)
    state["kbd_moving_at"] = _t.time() - 0.29
    authsrv.begin_attack(send, state, 10, 0, rec=rec)
    sent.clear()
    authsrv.attack_tick(send, state, 0, rec)
    r = rows(rec, "swing")
    check(len(starts(sent)) == 1 and len(r) == 1 and r[0]["fired"] is True
          and r[0]["refused_by"] is None and r[0]["target"] == 10
          and r[0]["age"] < 1.0,
          "END TO END: the 24.44 s press -- keyboard latch 0.29 s old, no "
          "stop, target 86 u -- OPENS A SWING on the first tick, and its "
          "press_verdict row is `swing`, refused by nothing; on the capture "
          "this press and the 21 after it got nothing",
          f"starts {len(starts(sent))}, rows {r}")

    # 11c. KNOWN-BAD ARM: --press-waits-for-stop reproduces the starve, and
    # the instrument names it -- ONE row on the first refused tick, not one
    # per tick; then the stop arrives and the answer row closes the press.
    saved = authsrv.PRESS_ENDS_KBD_LATCH
    authsrv.PRESS_ENDS_KBD_LATCH = False
    try:
        rec2 = _Rec()
        state2 = _state()
        state2["agents"][10]["pos"] = (86.0, 0.0)
        state2["kbd_moving_at"] = _t.time() - 0.29
        authsrv.begin_attack(send, state2, 10, 0, rec=rec2)
        sent.clear()
        for _ in range(3):
            authsrv.attack_tick(send, state2, 0, rec2)
        r = rows(rec2, "moving")
        check(starts(sent) == [] and len(r) == 1 and r[0]["fired"] is False
              and r[0]["latch"] == "kbd" and 0.2 <= r[0]["latch_age"] <= 1.0
              and len(rows(rec2)) == 1,
              "KNOWN-BAD ARM (--press-waits-for-stop): the same press WAITS, "
              "and the one press_verdict row names the branch and the latch "
              "-- `moving`, latch `kbd`, ~0.29 s old -- written on the first "
              "refused tick only (three ticks, one row)",
              f"starts {starts(sent)}, rows {rows(rec2)}")
        state2["kbd_moving_at"] = None          # the 0x0047 arm's clear
        sent.clear()
        authsrv.attack_tick(send, state2, 0, rec2)
        r = rows(rec2, "swing")
        check(len(starts(sent)) == 1 and len(r) == 1 and r[0]["fired"] is True
              and r[0]["refused_by"] == "moving" and r[0]["ticks"] == 3,
              "and when the stop finally clears the latch the swing opens "
              "and the ANSWER row carries the starve: refused_by `moving`, "
              "3 ticks -- the capture shows the wait AND its release",
              f"rows {r}")
    finally:
        authsrv.PRESS_ENDS_KBD_LATCH = saved

    # 11d. a report AFTER the press: the 0x003D arm forgets the order
    # (cancel_on_move, MOVE_ENDS_CHAIN) and re-arms the latch; the tick
    # finds a pending press with no target -> `move-ended-order`, terminal.
    # The 08:46 21.859 s press, whose click landed 1 ms behind it.
    rec3 = _Rec()
    state3 = _state()
    state3["agents"][10]["pos"] = (86.0, 0.0)
    state3["kbd_moving_at"] = _t.time() - 0.29
    authsrv.begin_attack(send, state3, 10, 0, rec=rec3)
    authsrv.cancel_on_move(send, state3, 0)     # what the 0x003D/0x003E arm does
    state3["kbd_moving_at"] = _t.time()
    sent.clear()
    authsrv.attack_tick(send, state3, 0, rec3)
    authsrv.attack_tick(send, state3, 0, rec3)
    r = rows(rec3, "move-ended-order")
    check(starts(sent) == [] and state3.get("attacking") is None
          and len(r) == 1 and r[0]["fired"] is False
          and state3.get("press_pending") is None,
          "a move command BETWEEN the press and the tick forgets the order "
          "(retail: any move ends the chain, 28/28 re-pressed) -- no swing, "
          "and the press closes as `move-ended-order`, once",
          f"attacking {state3.get('attacking')}, rows {rows(rec3)}")

    # 11e. THE REFUSED CLICK DOES NOT STARVE A PRESS INSIDE REACH. The 0x003E
    # arm stamps the latch and the leg BEFORE its freshness verdict, so a
    # click the server refuses `geo-stale` still arms them -- CORRECTLY: the
    # client paths a refused click itself (5 of 5, cos 0.994-1.000; the
    # 08:46 tap shows the body at 288 u/s on every refused-click leg). The
    # press then ENDS that leg (_press_supersedes) and swings the same tick.
    # On the capture: 16.42, 19.42, 21.06 and 22.51 s, each behind a run of
    # refused clicks, each answered within 14-32 ms.
    rec4 = _Rec()
    state4 = _state()
    state4["agents"][10]["pos"] = (100.0, 0.0)   # 42 u past the re-pin
    state4["pos"] = (0.0, 0.0)
    state4["client_pos"] = (0.0, 0.0)
    state4["plane"] = 0
    t0 = _t.time() - 0.2
    state4["click_moving_at"] = t0                       # the arm's stamp
    authsrv._click_leg_arm(state4, (1000.0, 0.0), t0, silent=False)
    # ... and the verdict then refused the click: nothing else is written.
    sent.clear()
    authsrv._press_supersedes(send, state4, 0, 10)
    authsrv.begin_attack(send, state4, 10, 0, rec=rec4)
    sent.clear()
    authsrv.attack_tick(send, state4, 0, rec4)
    check(len(starts(sent)) == 1 and rows(rec4, "swing")
          and state4.get("click_moving_at") is None,
          "a click the server REFUSED (latch and leg armed, no answer) does "
          "not starve the next press: the press ends the leg and the swing "
          "opens on the first tick -- the click latch was never the starver",
          f"starts {len(starts(sent))}, latch {state4.get('click_moving_at')}")
    src = open(authsrv.__file__, encoding="utf-8").read()
    i_stamp = src.find('state["click_moving_at"] = time.time()')
    i_verdict = src.find('fresh = (time.time() - state.get("pos_seen", 0.0)) <= 1.0')
    check(0 < i_stamp < i_verdict,
          "and the arm's order is pinned as INTENDED: the latch stamp "
          "precedes the freshness verdict, because a refused click is still "
          "a click the client walks (moving the stamp below the verdict was "
          "the handed-down fix, and it would have unarmed a moving body)",
          f"stamp at {i_stamp}, verdict at {i_verdict}")

    # 11f. the other rows begin_attack writes itself.
    rec5 = _Rec()
    state5 = _state()
    state5["agents"][10]["pos"] = (50.0, 0.0)
    authsrv.begin_attack(send, state5, 10, 0, rec=rec5)
    authsrv.attack_tick(send, state5, 0, rec5)            # the swing opens
    authsrv.begin_attack(send, state5, 10, 0, rec=rec5)   # a REPEAT press
    r = rows(rec5, "repeat")
    check(len(r) == 1 and r[0]["fired"] is False
          and r[0]["swing_in_flight"] is True and r[0]["pending_refused"] is None,
          "a REPEAT press on the running chain leaves a `repeat` row naming "
          "the swing in flight -- retail does not re-arm the clock (128 "
          "held presses, cadence p50 1.335 s), and neither do we, but the "
          "press is no longer invisible",
          f"rows {r}")
    authsrv.begin_attack(send, state5, 99, 0, rec=rec5)
    state5["agents"][10]["dead"] = True
    authsrv.begin_attack(send, state5, 10, 0, rec=rec5)
    check(len(rows(rec5, "no-target")) == 1
          and len(rows(rec5, "dead-target")) == 1
          and state5.get("attacking") is None,
          "a press on no such agent and a press on a corpse each leave their "
          "own row (`no-target`, `dead-target`) and drop the order",
          f"{[e['reason'] for e in rows(rec5)]}")

    # 11g. OUT OF REACH: the follow IS the answer, and the row says `follow`.
    rec6 = _Rec()
    state6 = _state()
    state6["agents"][10]["pos"] = (900.0, 0.0)
    state6["pos"] = (0.0, 0.0)
    state6["client_pos"] = (0.0, 0.0)
    state6["plane"] = 0
    state6["kbd_moving_at"] = _t.time() - 0.3
    authsrv.begin_attack(send, state6, 10, 0, rec=rec6)
    sent.clear()
    authsrv.attack_tick(send, state6, 0, rec6)
    follows = [v for op, v, _l in sent if op == UD]
    r = rows(rec6, "follow")
    check(len(follows) == 1 and len(r) == 1 and r[0]["fired"] is True
          and r[0]["refused_by"] is None and state6.get("press_pending") is None,
          "OUT OF REACH with the keyboard latch set: the follow goes out on "
          "the first tick (retail: 15 of the 48 fresh KBD-last presses were "
          "answered by a 0x002A) and the row is `follow`, fired",
          f"follows {len(follows)}, rows {r}")
    sent.clear()
    for _ in range(3):
        authsrv.attack_tick(send, state6, 0, rec6)
    check(len(rows(rec6)) == 1,
          "and the follow's later ticks write nothing more: one press, one row",
          f"{len(rows(rec6))} rows")

    # 11h. the interval branch names itself too (a retarget mid-chain re-
    # arms the clock, so this needs the revert of begin_attack's reset: a
    # pending press with a fresh player_last_swing).
    rec7 = _Rec()
    state7 = _state()
    state7["agents"][10]["pos"] = (50.0, 0.0)
    authsrv.begin_attack(send, state7, 10, 0, rec=rec7)
    state7["player_last_swing"] = _t.time()               # clock just ran
    sent.clear()
    authsrv.attack_tick(send, state7, 0, rec7)
    r = rows(rec7, "interval")
    check(starts(sent) == [] and len(r) == 1 and 0.0 < r[0]["remaining"] <= 5.0,
          "the interval gate names itself: `interval` with the seconds "
          "remaining -- a press cannot pass it in practice (begin_attack "
          "zeroes the clock) but a chain resuming can, and it was silent",
          f"rows {r}")

    # 11i. the tick without a recorder is the tests' own call and stays legal
    state8 = _state()
    state8["agents"][10]["pos"] = (50.0, 0.0)
    authsrv.begin_attack(send, state8, 10, 0)
    sent.clear()
    authsrv.attack_tick(send, state8, 0)
    check(len(starts(sent)) == 1 and state8.get("press_pending") is None,
          "with no recorder (rec=None, every earlier section) the press is "
          "still resolved and the swing still opens -- telemetry is never "
          "load-bearing",
          f"starts {len(starts(sent))}")

    # 11j. the call sites hand the recorder over: source pins.
    # SLICE-F50: TWO sites now -- the world tick and combat_pass, the early
    # wake -- and the pin is that BOTH hand the recorder over and none does not.
    check(src.count("attack_tick(send, state, conn_id, rec)") == 2
          and not [l for l in src.splitlines()
                   if l.strip() == "attack_tick(send, state, conn_id)"]
          and src.count("begin_attack(send, state, foe, conn_id, rec=rec)") == 1
          and src.count("begin_attack(send, state, values[1], conn_id, rec=rec)") == 1,
          "the world tick, the early combat pass, the harness control slot and "
          "the 0x0026 arm all pass the recorder, so no press path can be silent "
          "by omission",
          "source pin")
    # MOVECODE-1z-ds.21 widened the reader set by ONE, named: _approach_send stamps the
    # router's follow marker with the press behind it. Each read must sit in one of the two.
    def _fn_of(i):
        j = src.rfind("\ndef ", 0, i)
        return src[j + 5:src.index("(", j + 5)] if j >= 0 else None
    _reads = []
    _k = src.find('state.get("attack_press_at")')
    while _k >= 0:
        _reads.append(_fn_of(_k))
        _k = src.find('state.get("attack_press_at")', _k + 1)
    check(src.count('state["attack_press_at"] = now') == 1
          and sorted(_reads) == ["_approach_send", "_player_body_moving"],
          "the press stamp has ONE writer (begin_attack) and TWO readers -- "
          "_player_body_moving and _approach_send's follow marker (1z-ds.21) -- so rule 1 "
          "and the cast-stop still never see it",
          f"readers {_reads}")
    import ast as _ast
    n_kbd_writes = sum(
        1 for node in _ast.walk(_ast.parse(src))
        if isinstance(node, _ast.Assign)
        for tgt in node.targets
        if isinstance(tgt, _ast.Subscript)
        and isinstance(tgt.value, _ast.Name) and tgt.value.id == "state"
        and isinstance(getattr(tgt, "slice", None), _ast.Constant)
        and tgt.slice.value == "kbd_moving_at")
    check(n_kbd_writes == 2,
          "and `kbd_moving_at` itself still has exactly its two writers (the "
          "0x003D arm and the 0x0047 arm): 41 adds a reader's rule, not a "
          "third policy on the latch (test_position_trust's AST lock)",
          f"{n_kbd_writes} writes")


def section_still_streak():
    import agents
    import authsrv

    print("\n16. a REPEATED still report is a body that did not move -- the chain "
          "pause's read of the keyboard latch (MOVECODE-1z-df)")
    # RUN-1zDC arm A: the tap's still report kept the target (1z-dd) and ARMED
    # the keyboard latch; a tap into a wall sends no 0x0047, so the pause
    # charged p50 1.43 s a cycle (18 rows) on a body whose tape spread was
    # 0.0 u, and without the run's retarget the next swing would have waited
    # for the next press. The predicate is the one that separates a wall tap
    # from a WALK-START: a walk-start is ONE still report (the body has not
    # moved yet) followed by motion or a stop; two consecutive still reports
    # with no stop between cannot be a walk. Retail: 4 repeated-still reports
    # in 61 connections and 0 inter-swing gaps containing one (NOT FOUND;
    # review/stillwindup.py --streaks), so this rests on the derivation.

    st = _state()
    authsrv._kbd_report_still(st, 0.0)
    authsrv._kbd_report_still(st, 0.0)
    check(st.get("kbd_still_streak") == 2,
          "two consecutive still reports count a streak of 2",
          f"streak={st.get('kbd_still_streak')}")
    authsrv._kbd_report_still(st, 60.0)
    check(st.get("kbd_still_streak") == 0,
          "a report that MOVED resets it",
          f"streak={st.get('kbd_still_streak')}")
    authsrv._kbd_report_still(st, 0.0)
    authsrv._kbd_report_still(st, None)
    check(st.get("kbd_still_streak") == 0,
          "and a report with no predecessor counts nothing (the first of a "
          "session cancels as it always did, 1z-db)",
          f"streak={st.get('kbd_still_streak')}")

    def _latched(streak, needs=True):
        s = _state()
        s["kbd_moving_at"] = _tt.time()
        s["kbd_still_streak"] = streak
        saved = authsrv.MOVE_CANCEL_NEEDS_DISPLACEMENT
        try:
            authsrv.MOVE_CANCEL_NEEDS_DISPLACEMENT = needs
            return authsrv._player_body_moving(s)
        finally:
            authsrv.MOVE_CANCEL_NEEDS_DISPLACEMENT = saved

    check(_latched(2, needs=False) is True,
          "KNOWN-BAD ARM: an armed latch with a repeated still report reads "
          "as a body in motion",
          "RUN-1zDC arm A, 20260910T154327: chain_pause charged p50 1.43 s "
          "on 18 of 20 cycles, body spread 0.0 u on the tape")
    check(_latched(2) is False,
          "SHIPPED: a repeated still report is a body that did not move, "
          "whatever the latch says",
          "structural: at 288 u/s two reports > 4 ms apart with the body "
          "moving differ by > 1 u, so two stills with no stop between cannot "
          "be a walk")
    check(_latched(1) is True,
          "a SINGLE still report still reads as moving -- a walk-start's first "
          "report is still too, and a quarterstep's whole motion often sits "
          "between it and its 0x0047",
          "the naive rule (ignore every still report) would never arm the "
          "pause for a quarterstep at all")

    class _Rec:
        def __init__(self): self.rows = []
        def event(self, kind, **kw): self.rows.append((kind, kw))

    def _tick(needs):
        s = _state()
        s["agents"][10]["pos"] = (50.0, 0.0)          # in reach
        s["attacking"] = 10
        s["player_health"] = 100.0
        s["player_dead"] = False
        s["kbd_moving_at"] = _tt.time()
        s["kbd_still_streak"] = 2
        s["player_last_swing"] = 0.0
        sent = []
        rec = _Rec()
        saved = authsrv.MOVE_CANCEL_NEEDS_DISPLACEMENT
        try:
            authsrv.MOVE_CANCEL_NEEDS_DISPLACEMENT = needs
            authsrv.attack_tick(
                lambda op, vals, label="", quiet=False: sent.append((op, vals)),
                s, 0, rec=rec)
        finally:
            authsrv.MOVE_CANCEL_NEEDS_DISPLACEMENT = saved
        opened = any(v and v[0] == agents.GV_ATTACK_STARTED for _op, v in sent)
        return s, opened

    s, opened = _tick(False)
    check(not opened and s.get("player_swing") is None,
          "KNOWN-BAD ARM: the tick after a repeated still report refuses the "
          "open as `moving` -- the frozen chain RUN-1zDC's retarget was "
          "designed around",
          f"opened={opened} swing={s.get('player_swing')!r}")
    s, opened = _tick(True)
    check(opened and s.get("player_swing") is not None,
          "SHIPPED: the same tick OPENS the swing -- the body did not move",
          f"opened={opened} swing={s.get('player_swing')!r}")
    check((s.get("chain_pause_stats") or {}).get("charged", 0.0) == 0.0
          and s.get("chain_pause_tick") is None,
          "and the pause charged nothing across it",
          f"stats={s.get('chain_pause_stats')} tick={s.get('chain_pause_tick')}")

    # The two arms that feed the count, pinned by source: fed once beside
    # 1z-db's own displacement read, and reset where the stop disarms the
    # latch -- the streak must not outlive the stop that ended the reports.
    src = open(authsrv.__file__, encoding="utf-8").read()
    check(src.count("_kbd_report_still(state, _moved)") == 1,
          "the 0x003D arm feeds the streak exactly once, beside the "
          "displacement 1z-db reads",
          f"{src.count('_kbd_report_still(state, _moved)')} call(s)")
    i = src.find('state["kbd_moving_at"] = None\n')
    check(i > 0 and 'state["kbd_still_streak"] = 0' in src[i:i + 400],
          "the 0x0047 arm resets the streak beside its disarm of the latch",
          "a stop ends whatever the reports were; the next 0x003D is a "
          "walk-start")


def section_no_target_charge():
    import agents
    import authsrv

    print("\n17. the re-press after a move RESUMES the chain on the swing clock, "
          "uncharged (MOVECODE-1z-dg, re-aimed by 1z-ds.11)")
    # 1z-dc measured the accumulator charging 19 % of the real moving span;
    # RUN-1zDB/1zDC's rows named the starved branch: `no-target`. Section 5's
    # rig never saw it because it keeps `attacking` through the move -- the
    # real lifecycle FORGETS the target on the move's report (cancel_on_move,
    # ANIMREF-RE 39) and the client re-presses 30-40 ms after the 0x0047,
    # which begin_attack answered with a fresh clock. This rig does both.
    # Retail's START-to-START gap across a move with the re-press inside it
    # is interval + moving span (1z-dc.3: 2.701 modelled against 2.657
    # measured); the KNOWN-BAD arm collapses it to "the stop plus a tick".

    class _Rec:
        def __init__(self): self.rows = []
        def event(self, kind, **kw): self.rows.append((kind, kw))

    def lifecycle(charges, move_at=2.0, span=1.5, repress_target=10, clock_charge=False,
                  frees=True, target_pos=None):
        """Starts (synthetic clock) of a chain that a real move interrupts:
        the move's report forgets the target, the body moves for `span`,
        the stop clears the latch and the client re-presses `repress_target`
        40 ms later. Returns (starts, rec rows, state); the state also carries
        `_t_sent` (clock, op, vals, label) and `_t_moved_from`, the move's
        chain_moved_from read BEFORE the re-press consumes it (1z-ds.13)."""
        sent = []
        timed = []

        def send(op, vals, label="", quiet=False):
            sent.append((op, vals, label))
            timed.append((clock[0], op, vals, label))
        agent = {"name": "t", "dead": False, "last_hit": 0.0,
                 "max_health": 1e9, "health": 1e9, "pos": (0.0, 0.0)}
        state = {"agents": {10: agent, 11: dict(agent)}, "pos": (0.0, 0.0),
                 "attacking": 10, "player_health": 100.0, "player_dead": False,
                 "last_report": (0.0, 0.0, False, 999.0)}
        rec = _Rec()
        saved = (authsrv.CHAIN_PAUSE_CHARGES_WITHOUT_TARGET, authsrv.SWING_CLOCK_CHARGES_MOVING,
                 authsrv.CANCELLED_SWING_FREES_CLOCK)
        saved_time = authsrv.time.time
        clock = [1000.0]
        authsrv.time.time = lambda: clock[0]
        authsrv.CHAIN_PAUSE_CHARGES_WITHOUT_TARGET = charges
        authsrv.SWING_CLOCK_CHARGES_MOVING = clock_charge
        authsrv.CANCELLED_SWING_FREES_CLOCK = frees
        state["_t_sent"] = timed
        try:
            starts = []
            forgot = repressed = False
            for i in range(200):
                clock[0] = 1000.0 + i * 0.05
                t = i * 0.05
                if t >= move_at and not forgot:
                    # the arm's own path for a report that MOVED 60 u
                    authsrv.cancel_on_move(send, state, 0, moved=60.0)
                    state["_t_moved_from"] = dict(state.get("chain_moved_from") or {})
                    forgot = True
                moving = move_at <= t < move_at + span
                state["kbd_moving_at"] = clock[0] if moving else None
                if t >= move_at + span + 0.04 and forgot and not repressed:
                    if target_pos is not None:      # 17b-h: the re-press finds it out of reach
                        state["agents"][repress_target]["pos"] = target_pos
                    authsrv.begin_attack(send, state, repress_target, 0, rec=rec)
                    repressed = True
                before = len(sent)
                authsrv.attack_tick(send, state, 0, rec=rec)
                for op, vals, _l in sent[before:]:
                    if (op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                            and vals[0] == agents.GV_ATTACK_STARTED):
                        starts.append((clock[0], vals[2]))
                agent["health"] = 1e9
            return starts, rec.rows, state
        finally:
            (authsrv.CHAIN_PAUSE_CHARGES_WITHOUT_TARGET, authsrv.SWING_CLOCK_CHARGES_MOVING,
             authsrv.CANCELLED_SWING_FREES_CLOCK) = saved
            authsrv.time.time = saved_time

    def gap_across(starts, move_at=2.0):
        before = [t for t, _ in starts if t - 1000.0 < move_at]
        after = [t for t, _ in starts if t - 1000.0 >= move_at]
        return (after[0] - before[-1]) if before and after else None

    # MOVECODE-1z-ds.11 RE-AIMED this section. 1z-dg shipped two halves; the RESUME stays
    # (the re-press keeps the clock) and the CHARGE goes: on retail a press made inside the
    # interval after a move swings at the PERIOD from the previous start (55 of 88), never
    # at period + span (0 of 88; swingclockjoin.py). The binding case is a SHORT move -- the
    # re-press lands inside the interval -- so span 0.5 s: move 2.0 -> 2.5, re-press 2.54,
    # the previous start at 1.75, the period due at 3.5.
    # MOVECODE-1z-ds.13 RE-AIMED it once more. That move (2.0) fell 0.25 s into the 1.75-start
    # swing's 0.775 s windup: a CANCELLED swing, which on retail holds no clock (17b below).
    # The resume is a move AFTER the landing (2.525): move 2.65 -> 3.05, re-press 3.09, the
    # period from the 1.75 start due at 3.5 -- retail's 65 of 65 landed-swing WAIT rows.
    interval = authsrv.ATTACK_INTERVAL
    span = 0.4
    move_at = 2.65
    s_ship, rows_ship, st_ship = lifecycle(True, move_at=move_at, span=span)
    s_reset, rows_reset, _st = lifecycle(False, move_at=move_at, span=span)
    s_charge, rows_charge, _st = lifecycle(True, move_at=move_at, span=span, clock_charge=True)
    g_ship, g_reset, g_charge = (gap_across(s_ship, move_at), gap_across(s_reset, move_at),
                                 gap_across(s_charge, move_at))
    check(None not in (g_ship, g_reset, g_charge) and len(s_ship) >= 3,
          "every arm produced starts before and after the move -- the rig is not vacuous",
          f"ship={[(round(t - 1000, 2), a) for t, a in s_ship]} "
          f"reset={[(round(t - 1000, 2), a) for t, a in s_reset]}")
    if None in (g_ship, g_reset, g_charge):
        return
    check(abs(g_ship - interval) <= 0.051,
          "SHIPPED: a re-press inside the interval after a POST-LANDING move swings ONE PERIOD "
          "after the previous start -- retail's START-to-START on 55 of 88 binding presses",
          f"gap {g_ship:.2f} s against the period {interval:.2f}")
    check(g_reset < interval - 0.30,
          "KNOWN-BAD ARM (--no-pause-charge-without-target): the re-press resets the clock "
          "and swings at once, inside the period",
          f"gap {g_reset:.2f} s against the period {interval:.2f}")
    check(abs(g_charge - (interval + span)) <= 0.10,
          "KNOWN-BAD ARM (--swing-clock-charges-moving): the period PLUS the moving span -- "
          "1z-dg's charge, which retail shows on 0 of 88",
          f"gap {g_charge:.2f} s against {interval + span:.2f}")
    check(g_charge > g_ship + 0.3 and g_ship > g_reset + 0.3,
          "and the three arms SEPARATE",
          f"charge {g_charge:.2f} > shipped {g_ship:.2f} > reset {g_reset:.2f}")
    cp_ship = [kw for k, kw in rows_ship if k == "chain_pause"]
    cp_charge = [kw for k, kw in rows_charge if k == "chain_pause"]
    check(cp_ship and cp_ship[-1]["charged"] < 0.06
          and cp_charge and abs(cp_charge[-1]["charged"] - span) <= 0.10,
          "the row on the resumed swing: the shipped clock charged nothing, the charge arm "
          "the whole span",
          f"shipped {cp_ship[-1] if cp_ship else None}, charge {cp_charge[-1] if cp_charge else None}")
    pv_ship = [kw for k, kw in rows_ship if k == "press_verdict"]
    check(any(kw.get("reason") == "swing" and 0.30 <= kw.get("age", 0) <= 0.50
              for kw in pv_ship),
          "the re-press is ANSWERED by the tick when the period elapses -- its row carries "
          "the ~0.40 s wait as `age`",
          f"{[(kw.get('reason'), kw.get('age')) for kw in pv_ship]}")
    s_new, _rows, _st = lifecycle(True, move_at=move_at, span=span, repress_target=11)
    g_new = gap_across(s_new, move_at)
    check(g_new is not None and g_new < interval - 0.30
          and s_new[-1][1] == 11,
          "CONTROL: a press on a DIFFERENT target after the move is a "
          "retarget and swings at once -- only the target the move forgot "
          "resumes",
          f"gap {g_new:.2f} s, last start at agent {s_new[-1][1] if s_new else None}")
    st = _state()
    st["attacking"] = 10
    st["last_report"] = (0.0, 0.0, False, _tt.time())
    authsrv.cancel_on_move(lambda *a, **k: None, st, 0, moved=0.0)
    check(st.get("chain_moved_from") is None and st.get("attacking") == 10,
          "and a STILL report remembers nothing -- it kept the target "
          "(1z-dd), so there is nothing to resume",
          f"moved_from={st.get('chain_moved_from')} attacking={st.get('attacking')}")

    # 17b. MOVECODE-1z-ds.13: A SWING CANCELLED IN ITS WINDUP HOLDS NO CLOCK. The rig 17 used
    # until now: the move at 2.0 is 0.25 s into the 1.75-start swing's windup (lands 2.525), the
    # re-press at 2.54. Retail swings at the press on 13 of 13 such presses (5 of 5 on the same
    # target); 1z-dg's resume made ours wait out the cancelled swing's period.
    print("\n17b. a re-press after a move that CANCELLED the windup swings at once "
          "(MOVECODE-1z-ds.13)")
    P = authsrv.PLAYER_AGENT_ID
    s_free, rows_free, st_free = lifecycle(True, move_at=2.0, span=0.5)
    s_hold, _rows, st_hold = lifecycle(True, move_at=2.0, span=0.5, frees=False)
    g_free, g_hold = gap_across(s_free, 2.0), gap_across(s_hold, 2.0)
    mf = st_free.get("_t_moved_from") or {}
    stops = [lab for _c, op, vals, lab in st_free["_t_sent"]
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
             and vals[0] == agents.GV_ATTACK_STOPPED and vals[1] == P]
    check(any("before the swing landed" in lab for lab in stops) and mf.get("cancelled") is True,
          "17b-a. the move caught the windup: it sent [3, player, 0] 'before the swing landed' "
          "and the move's record says cancelled -- the operand begin_attack reads",
          f"stops={stops} moved_from={mf}")
    press_at = st_free.get("attack_press_at")
    after = [t for t, _a in s_free if t - 1000.0 >= 2.0]
    check(g_free is not None and g_free < interval - 0.30 and press_at is not None
          and after and abs(after[0] - press_at) <= 0.051,
          "17b-b. SHIPPED: the re-press swings AT the press, not one period after the cancelled "
          "start -- retail 13 of 13 (28-50 ms after the press)",
          f"gap {g_free} against the period {interval:.2f}; first start after the move "
          f"{(after[0] - 1000.0) if after else None}, press {(press_at - 1000.0) if press_at else None}")
    lands = [c - 1000.0 for c, op, vals, _l in st_free["_t_sent"]
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
             and vals[0] == agents.GV_MELEE_ATTACK_FINISHED and vals[1] == P]
    check(any(c < 1.75 for c in lands) and not any(1.75 <= c < 2.55 for c in lands),
          "17b-c. and the cancelled swing dealt nothing: the first swing's landing is on the "
          "wire (the positive control) and the cancelled one's never is",
          f"landings at {[round(c, 2) for c in lands]}")
    pv_free = [kw for k, kw in rows_free if k == "press_verdict"]
    check(any(kw.get("reason") == "swing" and kw.get("age", 1.0) <= 0.06 for kw in pv_free)
          and not any(kw.get("refused_by") == "interval" for kw in pv_free),
          "17b-d. its press row is answered `swing` at once, never refused by the interval",
          f"{[(kw.get('reason'), kw.get('age'), kw.get('refused_by')) for kw in pv_free]}")
    check(g_hold is not None and abs(g_hold - interval) <= 0.051,
          "17b-e. KNOWN-BAD ARM (--cancelled-swing-holds-clock): the same re-press waits one "
          "period from the CANCELLED start -- 1z-dg's resume, which retail shows on 0 of 13",
          f"gap {g_hold} against the period {interval:.2f}")
    s_lh, _rows, st_lh = lifecycle(True, move_at=move_at, span=span, frees=False)
    g_lh = gap_across(s_lh, move_at)
    check((st_ship.get("_t_moved_from") or {}).get("cancelled") is False
          and g_lh is not None and abs(g_lh - g_ship) <= 0.051,
          "17b-f. CONTROL: a POST-landing move's record says not cancelled, and the flag does "
          "not reach it -- the landed swing waits the period under both arms (65 of 65)",
          f"moved_from={st_ship.get('_t_moved_from')} gap off {g_lh} shipped {g_ship:.2f}")
    s_r1, _rows, _st = lifecycle(True, move_at=2.0, span=0.5, repress_target=11)
    s_r0, _rows, _st = lifecycle(True, move_at=2.0, span=0.5, repress_target=11, frees=False)
    g_r1, g_r0 = gap_across(s_r1, 2.0), gap_across(s_r0, 2.0)
    check(None not in (g_r1, g_r0) and g_r1 < interval - 0.30 and g_r0 < interval - 0.30,
          "17b-g. CONTROL: a pre-landing cancel then a press on ANOTHER target swings at once "
          "under both arms -- retail's retarget cancel cell, which ours already matched",
          f"gaps {g_r1} / {g_r0}")
    # 17b-h: the walk-in variant (the second pass's lane P3: 201800 51.411, 005405 31.378,
    # 124708 25.160). The re-press after the windup cancel finds the target out of reach, so
    # a FOLLOW answers it; retail swings on arrival, ours waited max(arrival, the cancelled
    # start + period) -- the same resume, so the same flag.
    s_wf, rows_wf, st_wf = lifecycle(True, move_at=2.0, span=0.5, target_pos=(200.0, 0.0))
    s_wh, rows_wh, st_wh = lifecycle(True, move_at=2.0, span=0.5, target_pos=(200.0, 0.0),
                                     frees=False)
    a_wf = [t - 1000.0 for t, _a in s_wf if t - 1000.0 >= 2.0]
    a_wh = [t - 1000.0 for t, _a in s_wh if t - 1000.0 >= 2.0]
    follows_wf = [c for c, op, _v, _l in st_wf["_t_sent"]
                  if op == authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION]
    check(follows_wf and a_wf and a_wh and a_wf[0] < 1.75 + interval - 0.2
          and a_wh[0] >= 1.75 + interval - 0.051 and a_wh[0] - a_wf[0] > 0.2,
          "17b-h. the WALK-IN variant: a follow answers the re-press, and the swing opens on "
          "ARRIVAL, not at the cancelled start + period; the known-bad arm waits the period "
          "(1.75 + 1.75)",
          f"follow at {[round(c - 1000.0, 2) for c in follows_wf]}, shipped first start "
          f"{a_wf[:1]}, known-bad {a_wh[:1]}")
    # 17b-i/j. MOVECODE-1z-ds.19 (U1): the gates that held a follow-answered press after its
    # walk now leave a row -- the press row closed at the 0x002A and said nothing more.
    fs_wh = [kw for k, kw in rows_wh if k == "follow_swing"]
    fs_wf = [kw for k, kw in rows_wf if k == "follow_swing"]
    pvf_wh = [kw for k, kw in rows_wh if k == "press_verdict" and kw.get("reason") == "follow"]
    def _walked(h):
        return h.get("reach", 0) + h.get("moving", 0)      # the walk's own gates
    check(len(fs_wh) == 1 and fs_wh[0].get("fired") is True
          and _walked(fs_wh[0]["held"]) >= 1 and fs_wh[0]["held"].get("interval", 0) >= 1
          and len(pvf_wh) == 1,
          "17b-i. a follow-answered press whose clock outlasts the walk writes ONE follow_swing "
          "row naming both gates that held it (the walk, then the interval), and the press row "
          "is still the single `follow` row",
          f"follow_swing {fs_wh}, press follow rows {len(pvf_wh)}")
    check(len(fs_wf) == 1 and fs_wf[0].get("fired") is True
          and _walked(fs_wf[0]["held"]) >= 1 and "interval" not in fs_wf[0]["held"],
          "17b-j. CONTROL: when the walk outlasts the clock the row names the walk alone -- "
          "the interval is not counted on every tick", f"follow_swing {fs_wf}")

    # 17b-k. MOVECODE-1z-ds.21 (the review's race): the world tick LANDED the swing while the
    # move's thread was inside a send, so the move's record says cancelled but that very swing
    # hit. It holds its clock: the re-press resumes, it is not freed.
    def repress_after(record, landed):
        st = _state()
        st.update({"player_health": 100.0, "player_dead": False,
                   "player_last_swing": 1001.75, "chain_moved_from": record,
                   "player_landed_armed_at": landed})
        authsrv.begin_attack(lambda *a, **k: None, st, 10, 0)
        return st.get("player_last_swing")
    rec_k = {"target": 10, "t": 1002.0, "cancelled": True, "armed_at": 1001.75}
    lk_race = repress_after(dict(rec_k), 1001.75)
    lk_free = repress_after(dict(rec_k), 1000.0)
    check(lk_race == 1001.75 and lk_free == 0.0,
          "17b-k. a 'cancelled' record whose swing LANDED anyway (the tick won the race inside "
          "the move's send) keeps the clock; one whose swing never landed frees it",
          f"race {lk_race}, free {lk_free}")

    # 17b-l/m. The follow_swing row's other closes (the review: no test asserted fired False).
    def followed_then(action):
        rows = []

        class _R:
            def event(self, kind, **kw):
                rows.append((kind, kw))
        st = _state()
        st["agents"][10]["pos"] = (300.0, 0.0)
        st["agents"][11] = dict(_fresh_agent(), pos=(50.0, 0.0))
        st.update({"player_health": 100.0, "player_dead": False, "player_last_swing": 0.0})
        snd = lambda *a, **k: None  # noqa: E731
        authsrv.begin_attack(snd, st, 10, 0, rec=_R())
        authsrv.attack_tick(snd, st, 0, rec=_R())          # the follow answers the press
        if action == "dies":
            st["player_dead"] = True
            authsrv.attack_tick(snd, st, 0, rec=_R())
        else:
            authsrv.begin_attack(snd, st, 11, 0, rec=_R())  # retarget to an in-reach foe
            authsrv.attack_tick(snd, st, 0, rec=_R())
        return [kw for k, kw in rows if k == "follow_swing"]
    fs_l = followed_then("dies")
    fs_m = followed_then("retarget")
    check(len(fs_l) == 1 and fs_l[0]["fired"] is False and fs_l[0]["reason"] == "dead-player"
          and fs_l[0]["target"] == 10,
          "17b-l. the player dies on the walk: the followed press closes fired=False, "
          "'dead-player'", f"{fs_l}")
    check(len(fs_m) == 1 and fs_m[0]["fired"] is False and fs_m[0]["reason"] == "superseded"
          and fs_m[0]["target"] == 10,
          "17b-m. a retarget during the walk closes the followed press as 'superseded', never "
          "fired on the new target's swing", f"{fs_m}")
    rows_n = []

    class _Rn:
        def event(self, kind, **kw):
            rows_n.append((kind, kw))
    st_n = _state()
    st_n["agents"][10]["pos"] = (300.0, 0.0)
    st_n["agents"][11] = dict(_fresh_agent(), pos=(50.0, 0.0))
    st_n.update({"player_health": 100.0, "player_dead": False, "player_last_swing": 0.0})
    _snd = lambda *a, **k: None  # noqa: E731
    authsrv.begin_attack(_snd, st_n, 10, 0, rec=_Rn())
    authsrv.attack_tick(_snd, st_n, 0, rec=_Rn())            # followed press on 10
    # The chain moved with NO press pending -- the attack skill's path, whose _press_supersedes
    # has already ended our leg -- and the next tick swings on 11.
    st_n.update({"attacking": 11, "click_moving_at": None, "click_leg": None, "approach": None})
    authsrv.attack_tick(_snd, st_n, 0, rec=_Rn())            # the swing on 11
    fs_n = [kw for k, kw in rows_n if k == "follow_swing"]
    check(len(fs_n) == 1 and fs_n[0]["fired"] is False and fs_n[0]["reason"] == "superseded",
          "17b-n. a swing on ANOTHER target with no press pending (the attack skill's approach "
          "rewrote the chain) closes the followed press 'superseded', not fired", f"{fs_n}")


def section_reach_frame():
    import agents
    import authsrv

    print("\n18. the player's reach geometry runs in the CLIENT's frame, not the "
          "position model (MOVECODE-1z-dm)")
    # Measured on 10 approach sends across five tapes, against the DRAWN body:
    # the model's error in the distance to the target is p50 30.0 u, max 76.9,
    # over 40 u on 5 of 10 -- and the five clean ones are exactly the ones an
    # APPROACH RE-PIN preceded, because that re-pin's threshold is the client's
    # 100 u SNAP reprieve while the gates it feeds run at 80 u (the stop
    # radius) and 144 u (the reach). RUN-1zDB leg A, 38.27 s: the gate read
    # 146.9 u against 144 while the bodies were 86.4 u apart, and the swing
    # dropped. _npc_frame scored p50 0.0 / over-40 1 of 10 on the same
    # instants; the last report p50 1.0 / 2 of 10.

    class _Rec:
        def __init__(self): self.rows = []
        def event(self, kind, **kw): self.rows.append((kind, kw))

    def _reach_state(model, frame_report):
        """The model at `model`, the client's last STOP report at
        `frame_report` -- _npc_frame's standing branch, no guard needed."""
        st = _state()
        st["agents"][10]["pos"] = (150.0, 0.0)       # 150 u from the ORIGIN
        st["attacking"] = 10
        st["player_health"] = 100.0
        st["player_dead"] = False
        st["pos"] = model
        st["last_report"] = (frame_report[0], frame_report[1], True, _tt.time())
        st["player_last_swing"] = 0.0
        return st

    # The specimen's shape: the body (and its stop report) at 20 u from the
    # target -- well inside reach -- while the model lags 90 u behind it.
    def _run(frame_on):
        st = _reach_state((0.0, 0.0), (130.0, 0.0))
        rec, sent = _Rec(), []
        saved = authsrv.APPROACH_READS_FRAME
        try:
            authsrv.APPROACH_READS_FRAME = frame_on
            authsrv.attack_tick(
                lambda op, vals, label="", quiet=False: sent.append((op, vals, label)),
                st, 0, rec=rec)
        finally:
            authsrv.APPROACH_READS_FRAME = saved
        opened = any(v and v[0] == agents.GV_ATTACK_STARTED for _op, v, _l in sent)
        walked = [l for _op, _v, l in sent if l.startswith("APPROACH")]
        app = [kw for k, kw in rec.rows if k == "approach"]
        return opened, walked, app

    opened, walked, app = _run(False)
    check(not opened and walked,
          "KNOWN-BAD ARM (--no-approach-frame): the gate reads the MODEL, 150 u "
          "from the target, so the swing is refused and the server WALKS the "
          "body toward a target it is already standing 20 u from -- RUN-1zDB "
          "leg A's 38.27 s drop, from the operand's side",
          f"opened={opened} sent={walked}")
    check(app and app[0]["dist_model"] == 150.0 and app[0]["dist_frame"] == 150.0,
          "and under the revert the row's two distances AGREE, because the "
          "frame IS the model there -- the row cannot be read as evidence for "
          "an arm that is off",
          f"{app[0] if app else None}")

    opened, walked, app = _run(True)
    check(opened and not walked,
          "SHIPPED: the same tick reads the client's frame (20 u out), the "
          "swing opens and no follow is sent",
          f"opened={opened} sent={walked}")

    # The row that makes this self-scoring on the next session, under EITHER
    # arm: all three candidate operands at every approach send (n = 10 is thin,
    # and 1z-cv killed _npc_frame as an ORDER TARGET on n = 277 -- a different
    # use of the same estimate, so the next session must be able to re-decide).
    st = _reach_state((0.0, 0.0), (130.0, 0.0))
    st["agents"][10]["pos"] = (400.0, 0.0)         # out of reach in BOTH frames
    rec = _Rec()
    authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
    app = [kw for k, kw in rec.rows if k == "approach"]
    check(app and app[0]["dist_model"] == 400.0 and app[0]["dist_frame"] == 270.0
          and app[0]["dist_report"] == 270.0 and app[0]["frame_vs_model"] == 130.0,
          "the `approach` row carries all THREE operands and their disagreement "
          "at every send -- the model, the frame, the last report",
          f"{app[0] if app else None}")
    # 1z-dn: and the CHORD, so the next census reads it from the row instead
    # of reconstructing the origin from a tape. Origin (130,0), target (400,0),
    # stop 80 -> the leg runs to (320,0), 190 u.
    check(app and app[0]["origin"] == [130.0, 0.0] and app[0]["to"] == [320.0, 0.0]
          and app[0]["run"] == 190.0,
          "and the CHORD ITSELF -- its origin, its end and its length -- because "
          "the first cut of this row carried three distances and neither "
          "endpoint, so 1z-dn's census had to reconstruct them from a tape",
          f"{app[0] if app else None}")
    check(app and app[0]["chord_cut"] is None,
          "chord_cut is None with no mesh loaded rather than 0.0 -- 'we did not "
          "look' and 'we looked and it was clear' are different rows, and a "
          "census that cannot tell them apart counts the first as the second",
          f"chord_cut={app[0].get('chord_cut') if app else None}")

    class _Wall:
        """A mesh with a wall across x = 200: the chord is cut there."""
        def walkable(self, x, y): return not (190.0 <= x <= 240.0)
        def on_mesh(self, x, y, tol=1.0): return self.walkable(x, y)
        def plane_at(self, x, y, prefer=None): return 0
        def clip(self, x0, y0, x1, y1, step=2.0, plane=None):
            d = math.hypot(x1 - x0, y1 - y0)
            n = max(1, int(d / step))
            last = (x0, y0)
            for i in range(1, n + 1):
                f = i / n
                p = (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
                if not self.walkable(*p):
                    return last
                last = p
            return (x1, y1)

    st = _reach_state((0.0, 0.0), (130.0, 0.0))
    st["agents"][10]["pos"] = (400.0, 0.0)
    st["pathmap"] = _Wall()
    rec = _Rec()
    authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
    app = [kw for k, kw in rec.rows if k == "approach"]
    check(app and app[0]["chord_cut"] is not None and app[0]["chord_cut"] > 100.0,
          "a chord that crosses ground the mesh refuses says so and by how much "
          "-- 1z-cn's question ('the point is on the mesh; the LINE is not') "
          "asked of the player's own follow leg",
          f"chord_cut={app[0].get('chord_cut') if app else None} of a 190 u leg")

    # THE REGRESSION THIS CHANGE ALREADY CAUSED ONCE, kept as a check: the
    # reach gate sits ABOVE attack_tick's own `now = time.time()`, so passing
    # `now` there is an unbound name and raised NameError on the world tick.
    # A bare state with no guard and no report must reach the gate and open.
    st = _state()
    st["agents"][10]["pos"] = (50.0, 0.0)
    st["attacking"] = 10
    st["player_health"] = 100.0
    st["player_dead"] = False
    st["player_last_swing"] = 0.0
    authsrv.attack_tick(lambda *a, **k: None, st, 0)
    check(st.get("player_swing") is not None,
          "and the gate runs on a BARE state -- no guard, no report, no click "
          "leg: `_reach_frame` reads its own clock rather than a name the "
          "caller binds twenty lines later (this raised NameError once)",
          f"swing={st.get('player_swing')!r}")

    st = _state()
    st["pos"] = (5.0, 7.0)
    check(authsrv._reach_frame(st) == (5.0, 7.0),
          "CONTROL: with nothing to go on the frame IS the model -- the "
          "helper degrades to today's operand rather than to the origin",
          f"{authsrv._reach_frame(st)}")
    saved = authsrv.APPROACH_READS_FRAME
    try:
        authsrv.APPROACH_READS_FRAME = False
        st2 = _state()
        st2["pos"] = (5.0, 7.0)
        st2["last_report"] = (600.0, 0.0, True, _tt.time())
        got = authsrv._reach_frame(st2)
    finally:
        authsrv.APPROACH_READS_FRAME = saved
    check(got == (5.0, 7.0),
          "and the revert really reverts: with the flag off a fresh stop report "
          "600 u away does not move the operand",
          f"{got}")

    src = open(authsrv.__file__, encoding="utf-8").read()
    check(authsrv.APPROACH_READS_FRAME is True
          and "--no-approach-frame" in src
          and authsrv.capture_flags().get("APPROACH_READS_FRAME") is True
          and src.count("_reach_frame(state") >= 4,
          "ships ON with its revert, on the capture's flags row, at all four "
          "sites (approach_tick's distance, the send's geometry, the press "
          "row's distance and the reach gate)",
          f"{src.count('_reach_frame(state')} call sites")


def section_swing_clock_carry():
    """SLICE-F49: the start-to-start clock carries its remainder."""
    import authsrv
    print("\n13. the swing clock carries its remainder (SLICE-F49)")
    stamp = authsrv.swing_clock_stamp
    LEDGER.ok(abs(stamp(100.0, 1.333, 101.35) - 101.333) < 1e-9,
              "a swing opened 17 ms past due is stamped at the instant it was DUE")
    LEDGER.ok(stamp(100.0, 1.333, 101.6) == 101.6 and stamp(0.0, 1.333, 50.0) == 50.0,
              "one opened LATE (out of reach, a cast between) or FIRST restarts from now")

    def simulate(interval, n=200, tick=0.051):
        last, t, starts = 0.0, 0.0, []
        while len(starts) < n:
            t += tick
            if t - last < interval:
                continue
            last = stamp(last, interval, t)
            starts.append(t)
        gaps = [b - a for a, b in zip(starts, starts[1:])]
        return sum(gaps) / len(gaps), {round(g / tick) for g in gaps}

    mean, ticks = simulate(1.333)
    LEDGER.ok(abs(mean - 1.333) < 0.002 and ticks == {26, 27},
              "daggers on a 51 ms tick: 26 and 27 ticks alternate, MEAN 1.333 "
              "(retail 1.326-1.335)", f"{mean:.4f} {sorted(ticks)}")
    mean, ticks = simulate(1.75)
    LEDGER.ok(abs(mean - 1.75) < 0.002, "and a hammer's mean is 1.75",
              f"{mean:.4f} {sorted(ticks)}")
    authsrv.SWING_CLOCK_CARRY = False
    try:
        mean, ticks = simulate(1.333)
        LEDGER.ok(abs(mean - 1.377) < 0.002 and ticks == {27},
                  "--no-swing-clock-carry, the KNOWN-BAD arm: every interval is 27 "
                  "ticks, 1.377 s -- what harness 20260917T232539 measured "
                  "(1.376-1.379)", f"{mean:.4f} {sorted(ticks)}")
        LEDGER.ok(abs(authsrv.second_strike_due({}, 10.0) - 10.5) < 1e-9,
                  "and a second strike is due at its instant")
    finally:
        authsrv.SWING_CLOCK_CARRY = True
    authsrv.COMBAT_DEADLINES = False        # SLICE-F50 owns the default arm
    _half = authsrv.second_strike_due({}, 10.0)
    authsrv.COMBAT_DEADLINES = True
    LEDGER.ok(abs(_half - (10.5 - authsrv.TICK_SECONDS / 2.0)) < 1e-9,
              "with the carry on it is due half a tick EARLY, so the tick that "
              "lands it is the NEAREST one -- armed on a tick, 0.5 s is 10 ticks "
              "(0.510) and 0.335 s is 7 (0.357) either way, which is what harness "
              "20260918T081923 measured; 0.375 s would move from 8 ticks to 7")


def section_combat_deadlines():
    """SLICE-F50: the world thread wakes at a combat deadline."""
    import authsrv
    print("\n14. combat one-shots fire at their instant (SLICE-F50)")
    now = _tt.time()
    st = {"player_second_strike": {"target": 10, "at": now + 0.2},
          "player_swing": {"target": 10, "lands_at": now + 0.3},
          "pending_casts": [{"begun": True, "e5_sent": False, "e5_at": now + 0.4,
                             "e3_sent": False, "e3_at": now + 0.6, "e6_at": now + 0.9},
                            {"cancelled": True, "e5_at": now + 0.05}],
          "agents": {10: {"dead": False, "swing_lands_at": now + 0.7},
                     11: {"dead": True, "swing_lands_at": now + 0.01}}}
    got = sorted(round(d - now, 2) for d in authsrv.combat_deadlines(st))
    LEDGER.ok(got == [0.2, 0.3, 0.4, 0.6, 0.7, 0.9],
              "the deadlines: the second strike, the swing's landing, a cast's "
              "unsent phases, a live NPC's landing -- not a cancelled cast's, "
              "not a corpse's", str(got))
    calls, saved = [], authsrv.combat_pass
    authsrv.combat_pass = lambda send, state, conn_id, rec=None: calls.append(_tt.time())
    try:
        t0 = _tt.time()
        st = {"player_second_strike": {"target": 10, "at": t0 + 0.020}}
        n = authsrv.combat_sleep(None, st, 1, tick=0.051)
        took = _tt.time() - t0
        LEDGER.ok(n == 1 and len(calls) == 1 and abs(calls[0] - (t0 + 0.020)) < 0.012,
                  "a second strike due 20 ms into the tick is served AT its "
                  "instant (within the sleep's own error), once",
                  f"passes {n}, off by {calls and round(calls[0] - t0 - 0.020, 4)}")
        LEDGER.ok(0.045 < took < 0.090, "and the tick still lasts a tick",
                  f"{took:.4f}")
        calls.clear()
        n = authsrv.combat_sleep(None, st, 1, tick=0.051)
        LEDGER.ok(n == 0 and not calls,
                  "a deadline already SERVED is not served again -- a due swing "
                  "that the timer refuses cannot spin the loop", f"passes {n}")
        calls.clear()
        authsrv.COMBAT_DEADLINES = False
        st = {"player_second_strike": {"target": 10, "at": _tt.time() + 0.020}}
        n = authsrv.combat_sleep(None, st, 1, tick=0.051)
        LEDGER.ok(n == 0 and not calls,
                  "--no-combat-deadlines: the plain sleep, no early pass")
        LEDGER.ok(abs(authsrv.second_strike_due({}, 10.0)
                      - (10.5 - authsrv.TICK_SECONDS / 2.0)) < 1e-9,
                  "and only THAT arm rounds a second strike to the nearest tick")
        authsrv.COMBAT_DEADLINES = True
        LEDGER.ok(abs(authsrv.second_strike_due({}, 10.0) - 10.5) < 1e-9,
                  "with the wake on, a second strike is due at its instant")

        def boom(send, state, conn_id, rec=None):
            raise RuntimeError("an early pass that faults")
        authsrv.combat_pass = boom
        st = {"player_second_strike": {"target": 10, "at": _tt.time() + 0.010}}
        n = authsrv.combat_sleep(None, st, 1, tick=0.051)
        LEDGER.ok(st.get("combat_deadlines_fused") is True
                  and authsrv.combat_sleep(None, st, 1, tick=0.02) == 0,
                  "FUSED: a faulting early pass is printed once and the session "
                  "sleeps plainly from there", f"passes {n}")
    finally:
        authsrv.combat_pass = saved
        authsrv.COMBAT_DEADLINES = True


def section_dead_press():
    """MOVECODE-1z-ds.15: a dead player's attack press is no order, and an order set across the
    kill dies with the player. 20261002T124708 39.10: a press handled in the killing-blow instant
    pinned and halted the corpse and set `attacking`; 0.055 s after the rise the tick sent a
    2325 u follow. Retail walks 0 of 23 risen bodies before their own input (risejoin.py)."""
    import ast
    import time
    import authsrv
    import leadgeom

    print("\n19. 1z-ds.15: a dead player's press orders nothing; the order dies with the player")

    class _Rec:
        def __init__(self): self.rows = []
        def event(self, kind, **kw): self.rows.append((kind, kw))

    class _PM:
        def walkable(self, x, y):
            return True

        def clip(self, x0, y0, x1, y1, step=None):
            return (x1, y1)

        def plane_at(self, x, y, prefer=None):
            return prefer

        def containing(self, x, y):
            return []

    PIN, HALT = authsrv.GAME_SMSG_AGENT_UPDATE_POSITION, authsrv.GAME_SMSG_AGENT_STOP_MOVING
    DEST = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION

    def walking_dead(dead=True):
        t = time.time()
        st = _state()
        st.update({"client_pos": (30.0, 0.0), "client_pos_at": t - 0.1, "client_plane": 0,
                   "kbd_moving_at": t - 0.1, "heading": (0.0, 766.0), "heading_mt": 1,
                   "pathmap": _PM(), "player_dead": dead, "player_health": 100.0})
        return st

    def press(on, dead=True):
        sent, rec = [], _Rec()
        send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))  # noqa: E731
        st = walking_dead(dead)
        saved = authsrv.PRESS_REFUSES_DEAD_PLAYER
        authsrv.PRESS_REFUSES_DEAD_PLAYER = on
        try:
            authsrv.begin_attack(send, st, 10, 0, rec=rec)
        finally:
            authsrv.PRESS_REFUSES_DEAD_PLAYER = saved
        return st, sent, rec

    st, sent, rec = press(True)
    pv = [kw for k, kw in rec.rows if k == "press_verdict"]
    check(sent == [] and st.get("attacking") is None
          and [kw.get("reason") for kw in pv] == ["dead-player"],
          "19a. a dead player's press on a walking body sends NOTHING -- no pin, hold or halt "
          "on the corpse -- sets no order, and its row says dead-player",
          f"sent {[l[:30] for _o, _v, l in sent]}, attacking {st.get('attacking')}, rows {pv}")
    stk, sentk, _r = press(False)
    opsk = [op for op, _v, _l in sentk]
    check(PIN in opsk and HALT in opsk and stk.get("attacking") == 10,
          "19b. KNOWN-BAD ARM (--press-allows-dead-player): the corpse is pinned and halted "
          "and the order is taken -- 20261002T124708 39.104",
          f"{[l[:30] for _o, _v, l in sentk]}, attacking {stk.get('attacking')}")
    stc, sentc, _r = press(True, dead=False)
    check(PIN in [op for op, _v, _l in sentc] and stc.get("attacking") == 10,
          "19c. CONTROL: the same press from a LIVING player stops the body and takes the "
          "order -- the gate is the death, not the press",
          f"{[l[:30] for _o, _v, l in sentc]}")

    # The REAL 0x0026 arm (lifted out of the receive loop as test_position_trust's
    # receive_arm does; that one matches `opcode == NAME`, this arm is `opcode in (...)`).
    tree = ast.parse(open(authsrv.__file__, encoding="utf-8").read())
    node = None
    for n in ast.walk(tree):
        if (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
                and isinstance(n.test.left, ast.Name) and n.test.left.id == "opcode"
                and len(n.test.ops) == 1 and isinstance(n.test.ops[0], ast.In)
                and isinstance(n.test.comparators[0], ast.Tuple)
                and any(isinstance(e, ast.Name) and e.id == "GAME_CMSG_ATTACK_AGENT"
                        for e in n.test.comparators[0].elts)):
            node = n
    check(node is not None, "the 0x0026 arm is found in the source -- the drive below is real")
    if node is None:
        return
    args = ast.arguments(posonlyargs=[], args=[ast.arg(p) for p in
                                               ("values", "state", "rec", "send", "conn_id")],
                         vararg=None, kwonlyargs=[], kw_defaults=[], kwarg=None, defaults=[])
    mod = ast.Module(body=[ast.FunctionDef(name="_arm", args=args, body=node.body,
                                           decorator_list=[], returns=None, type_params=[])],
                     type_ignores=[])
    ast.fix_missing_locations(mod)
    ns = {}
    exec(compile(mod, authsrv.__file__, "exec"), authsrv.__dict__, ns)   # noqa: S102
    arm = ns["_arm"]

    def arm_press(on):
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))  # noqa: E731
        t = time.time()
        st = walking_dead(True)
        st.update({"click_moving_at": t - 0.2,
                   "click_leg": leadgeom._leg_record((0.0, 0.0), (0.0, 300.0), t - 0.2, 288.0)})
        saved = authsrv.PRESS_REFUSES_DEAD_PLAYER
        authsrv.PRESS_REFUSES_DEAD_PLAYER = on
        try:
            arm([0, 10], st, _Rec(), send, 0)
        finally:
            authsrv.PRESS_REFUSES_DEAD_PLAYER = saved
        return st, sent

    sta, senta = arm_press(True)
    stb, sentb = arm_press(False)
    check(senta == [] and sta.get("click_moving_at") is not None
          and any("PRESS ENDS THE WALK" in l for _o, _v, l in sentb),
          "19d. through the REAL 0x0026 arm: the corpse's press ends no walk on its behalf "
          "(no PRESS ENDS THE WALK 0x002C) -- the known-bad arm places the corpse",
          f"shipped {[l[:30] for _o, _v, l in senta]}, known-bad {[l[:30] for _o, _v, l in sentb]}")

    def across_kill(on):
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))  # noqa: E731
        st = _state()
        st["agents"][10]["pos"] = (400.0, 0.0)
        st.update({"attacking": 10, "player_dead": True, "player_health": 0.0,
                   "player_last_swing": 0.0})
        saved = authsrv.PRESS_REFUSES_DEAD_PLAYER
        authsrv.PRESS_REFUSES_DEAD_PLAYER = on
        try:
            authsrv.attack_tick(send, st, 0)          # dead: the branch that returns
            kept = st.get("attacking")
            st.update({"player_dead": False, "player_health": 100.0})   # the rise
            sent.clear()
            authsrv.attack_tick(send, st, 0)
        finally:
            authsrv.PRESS_REFUSES_DEAD_PLAYER = saved
        return kept, [op for op, _v, _l in sent]

    kept1, ops1 = across_kill(True)
    kept0, ops0 = across_kill(False)
    check(kept1 is None and DEST not in ops1 and kept0 == 10 and DEST in ops0,
          "19e. an order set across the kill dies at the next dead tick, so the risen body is "
          "walked nowhere -- the known-bad arm keeps it and FOLLOWS 400 u out on the first live "
          "tick (124708 49.805: 2325 u, 0.055 s after the rise; retail 0 of 23)",
          f"shipped kept {kept1} ops {ops1}; known-bad kept {kept0} ops {ops0}")
    src = open(authsrv.__file__, encoding="utf-8").read()
    args_src = open(os.path.join(os.path.dirname(authsrv.__file__), "serverargs.py"),
                    encoding="utf-8").read()
    check("--press-allows-dead-player" in args_src and "if a.press_allows_dead_player:" in src,
          "19f. --press-allows-dead-player is wired")

    # 19g-j. MOVECODE-1z-ds.27: a death with the player's swing in flight carries [3, me, 0]
    # right after the KILL status (retail 30 of 30 open-windup deaths, 0 of 155 without).
    STATUS, INT = authsrv.GAME_SMSG_AGENT_UPDATE_STATUS, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
    STOP = [authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0]

    def die(on=True, phase="windup"):
        sent, rec = [], _Rec()
        send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))  # noqa: E731
        st = _state()
        st.update({"player_health": 0.0, "player_dead": False})
        authsrv.begin_attack(send, st, 10, 0)
        authsrv.attack_tick(send, st, 0)                  # START: a swing in its windup
        if phase == "landed":
            _rewind(st, 5.0)
            authsrv.attack_tick(send, st, 0)              # it lands; none in flight
        elif phase == "overdue":
            st["player_swing"]["lands_at"] -= 5.0         # due, the landing tick not yet run
        sent.clear()
        saved = authsrv.DEATH_STOPS_WINDUP
        authsrv.DEATH_STOPS_WINDUP = on
        try:
            authsrv.kill_player(send, st, 0, "test")
            batch = [(op, v) for op, v, _l in sent]
            sent.clear()
            authsrv.attack_tick(send, st, 0, rec=rec)
        finally:
            authsrv.DEATH_STOPS_WINDUP = saved
        stops = [i for i, (op, v) in enumerate(batch) if op == INT and v == STOP]
        status = [i for i, (op, _v) in enumerate(batch) if op == STATUS]
        return batch, stops, status, st, sent

    b19g, s19g, k19g, st19g, after19g = die()
    check(k19g[:1] == [0] and s19g == [1] and st19g.get("player_swing") is None
          and not any(op == INT and v[0] == authsrv.agents.GV_MELEE_ATTACK_FINISHED
                      for op, v, _l in after19g),
          "19g. a death inside the windup: the KILL status, then [3, me, 0] at index 1 (retail "
          "27 of 30 there), and the next tick drops the swing unlanded as before",
          f"batch {[hex(op) for op, _v in b19g]} stops {s19g}")
    _b, s19h, _k, _st, _a = die(on=False)
    check(s19h == [],
          "19h. KNOWN-BAD ARM (--death-keeps-windup): no [3] -- the corpse is never told its "
          "swing ended (201011 78.198, 124708 71.079)", f"stops {s19h}")
    _b, s19i, _k, _st, _a = die(phase="landed")
    _b, s19i2, _k, _st, _a = die(phase="overdue")
    check(s19i == [] and s19i2 == [1],
          "19i. CONTROL: a death after the swing LANDED sends no [3] (retail 0 of 155); an "
          "overdue swing the tick had not yet landed is in flight and gets one -- the dead branch "
          "drops it with no [1]", f"landed {s19i}, overdue {s19i2}")
    check(authsrv.DEATH_STOPS_WINDUP is True and "--death-keeps-windup" in args_src
          and "if a.death_keeps_windup:" in src,
          "19j. the flag ships on and its revert arm is wired")


def section_windup_holds_approach():
    """MOVECODE-1z-ds.28: no follow inside the player's own windup; a target that left reach
    mid-swing is re-approached at the landing, [1] then the 0x002A in one tick. Retail: 0 in
    1,654 windups (86 with the target moving), 18 of 18 re-approaches at or after the landing
    (batch-3 lane S's r_windup_follow.py)."""
    import time
    import authsrv

    print("\n22. 1z-ds.28: the swing finishes in place; the re-approach rides its landing")
    DEST = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION
    INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT

    def walked_off(on=True, kill=False, swing=True):
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))  # noqa: E731
        st = _state()
        saved = (authsrv.WINDUP_HOLDS_APPROACH, authsrv.ATTACK_APPROACH)
        authsrv.WINDUP_HOLDS_APPROACH, authsrv.ATTACK_APPROACH = on, True
        windup, after = [], []
        try:
            authsrv.begin_attack(send, st, 10, 0)
            if swing:
                authsrv.attack_tick(send, st, 0)                  # START, in reach
            st["agents"][10]["pos"] = (200.0, 0.0)               # it steps out of reach
            if kill:
                st["agents"][10]["health"] = 0.5
            sent.clear()
            if swing:
                for _ in range(3):                                # ticks inside the windup
                    authsrv.attack_tick(send, st, 0)
                windup = list(sent)
                sent.clear()
                _rewind(st, 5.0)                                  # the landing is due
            authsrv.attack_tick(send, st, 0)
            after = list(sent)
        finally:
            authsrv.WINDUP_HOLDS_APPROACH, authsrv.ATTACK_APPROACH = saved
        return windup, after, st

    fol = lambda sent: [i for i, (op, _v, _l) in enumerate(sent) if op == DEST]
    fin = lambda sent: [i for i, (op, v, _l) in enumerate(sent)
                        if op == INT and v[0] == authsrv.agents.GV_MELEE_ATTACK_FINISHED]
    w1, a1, st1 = walked_off()
    check(fol(w1) == [],
          "22a. the target steps out of reach inside the windup: no follow on any windup tick "
          "(retail 0 in 1,654; 201011 22.774 sent one at +0.155 s)",
          f"windup ops {[hex(op) for op, _v, _l in w1]}")
    check(len(fin(a1)) == 1 and len(fol(a1)) == 1 and fin(a1)[0] < fol(a1)[0]
          and st1["agents"][10]["health"] < 100.0,
          "22b. the landing tick lands the hit and THEN sends the follow, one tick -- retail's "
          "[1] ... 0x002A batch (13 of 18 at +0.00 s)",
          f"landing ops {[hex(op) for op, _v, _l in a1]}")
    w0, _a0, _st = walked_off(on=False)
    check(len(fol(w0)) >= 1,
          "22c. KNOWN-BAD ARM (--approach-in-windup): the follow goes out mid-windup, the "
          "body walking while the attack is latched", f"windup ops {[hex(op) for op, _v, _l in w0]}")
    _w, a2, _st = walked_off(swing=False)
    check(len(fol(a2)) == 1,
          "22d. CONTROL: out of reach with NO swing in flight the follow goes out on that tick "
          "-- the gate is the swing, not reach", f"ops {[hex(op) for op, _v, _l in a2]}")
    _w, a3, st3 = walked_off(kill=True)
    check(st3["agents"][10]["dead"] and fol(a3) == [],
          "22e. a landing that KILLS the out-of-reach target sends no follow at the corpse",
          f"dead={st3['agents'][10]['dead']} ops {[hex(op) for op, _v, _l in a3]}")
    src = open(authsrv.__file__, encoding="utf-8").read()
    args_src = open(os.path.join(os.path.dirname(authsrv.__file__), "serverargs.py"),
                    encoding="utf-8").read()
    check(authsrv.WINDUP_HOLDS_APPROACH is True and "--approach-in-windup" in args_src
          and "if a.approach_in_windup:" in src,
          "22f. the flag ships on and its revert arm is wired")


def section_attack_start_holds():
    """MOVECODE-1z-ds.31: every own attack start leaves the action hold [8, me, 1] up, to the
    next input. Retail: 1,647 of 1,654 own starts held at start + 0.1 s, raised in the start's
    own batch directly behind the [4] when it was down (210 of 210); the next input ends 68 % of
    hold episodes, a landing 0.9 % (batch-3 lane H, re-measured by its verifier)."""
    import time
    import authsrv

    print("\n21. 1z-ds.31: every attack start holds, to the next input")
    INT, START = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
    DEST, HALT = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION, authsrv.GAME_SMSG_AGENT_STOP_MOVING
    PIN = authsrv.GAME_SMSG_AGENT_UPDATE_POSITION
    GV8 = authsrv.agents.GV_DISABLED
    FIN = authsrv.agents.GV_MELEE_ATTACK_FINISHED

    def shape(sent):
        return [("8:%d" % v[2]) if op == INT and v[0] == GV8 else
                ("4" if op == START else ("1" if op == INT and v[0] == FIN else op))
                for op, v, _l in sent]

    def walk_in(on=True):
        """A parked body, the target 300 u out: press, follow, the leg ends, the start."""
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))  # noqa: E731
        st = _state()
        st["agents"][10]["pos"] = (300.0, 0.0)
        st.update({"pos": (0.0, 0.0), "client_pos": (0.0, 0.0), "plane": 0})
        saved = authsrv.ATTACK_START_HOLDS
        authsrv.ATTACK_START_HOLDS = on
        try:
            authsrv.begin_attack(send, st, 10, 0)
            authsrv.attack_tick(send, st, 0)                      # the follow
            st["pos"] = st["dest"]
            st["dest"] = None
            st["click_leg"]["eta"] = time.time() - 0.01
            st["approach"]["eta"] = st["click_leg"]["eta"]
            sent.clear()
            authsrv.attack_tick(send, st, 0)                      # arrival: the start
            start = list(sent)
            sent.clear()
            _rewind(st, 5.0)
            authsrv.attack_tick(send, st, 0)                      # the landing
            landing = list(sent)
            sent.clear()
            st["player_last_swing"] = time.time() - 10.0
            authsrv.attack_tick(send, st, 0)                      # the chain's next start
            nxt = list(sent)
        finally:
            authsrv.ATTACK_START_HOLDS = saved
        return st, start, landing, nxt

    st21, start21, land21, next21 = walk_in()
    check(shape(start21) == ["4", "8:1"] and st21.get("press_hold") is True
          and st21.get("action_hold") == 1,
          "21a. a melee WALK-IN's start batch is [4], [8, me, 1] -- no 0x0028, no pin -- and the "
          "start marks the hold (retail walk-ins held 75 of 75; ours held 0 of 44)",
          f"{shape(start21)}")
    check("8:0" not in shape(land21) and "1" in shape(land21) and st21.get("action_hold") == 1,
          "21b. that swing's landing releases NOTHING -- the mark keeps the hold (retail: a "
          "landing ends 3 of 347 hold episodes)", f"{shape(land21)}")
    check(shape(next21) == ["4"] and st21.get("action_hold") == 1,
          "21c. the chain's next start is [4] alone and the hold stays up (transition-only; "
          "retail CONT 1,310 of 1,315 held)", f"{shape(next21)}")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))  # noqa: E731
    authsrv.cancel_on_move(send, st21, 0, moved=50.0)
    sh21d = shape(sent)
    check(sh21d[:1] == ["8:0"] and "press_hold" not in st21 and st21.get("action_hold") == 0,
          "21d. the next movement input releases it first ([8, me, 0] ahead of anything else; "
          "retail before the lead 116 of 116), and the mark goes with it", f"{sh21d}")
    _st, s0, l0, _n = walk_in(on=False)
    check(shape(s0) == ["4"] and "8:0" not in shape(l0) and not _st.get("action_hold"),
          "21e. KNOWN-BAD ARM (--no-attack-start-hold): the walk-in starts [4] alone, unheld -- "
          "every build before 1z-ds.31 (201011: 24 of 37 starts unheld)", f"{shape(s0)}")
    st = _state()
    st["agents"][10]["pos"] = (100.0, 0.0)
    st.update({"pos": (0.0, 0.0), "client_pos": (0.0, 0.0), "plane": 0,
               "last_report": (0.0, 0.0, True, time.time() - 2.0)})
    sent.clear()
    authsrv.begin_attack(send, st, 10, 0)
    authsrv.attack_tick(send, st, 0)
    check(shape(sent) == ["4", "8:1"],
          "21f. a PARKED in-reach press opens [4], [8, me, 1] -- no pin, no halt (retail "
          "IMM-parked 79 of 79 raised in the start's batch)", f"{shape(sent)}")
    sent.clear()
    st["agents"][10]["pos"] = (400.0, 0.0)                         # it steps out mid-windup
    _rewind(st, 5.0)
    authsrv.attack_tick(send, st, 0)
    sh21g = shape(sent)
    check("1" in sh21g and "8:0" in sh21g and DEST in sh21g
          and sh21g.index("1") < sh21g.index("8:0") < sh21g.index(DEST),
          "21g. a target that left reach: the landing, then [8, me, 0] directly ahead of the "
          "re-approach's 0x002A (1z-ds.28; retail '[1], [8, 0], 0x002A' 12 of 13, release "
          "before the 0x002A 39 of 39)", f"{sh21g}")
    st["agents"][10]["pos"] = (200.0, 0.0)
    st["pos"] = st["dest"]
    st["dest"] = None
    st["click_leg"]["eta"] = time.time() - 0.01
    st["approach"]["eta"] = st["click_leg"]["eta"]
    st["player_last_swing"] = time.time() - 10.0
    sent.clear()
    authsrv.attack_tick(send, st, 0)
    check(shape(sent) == ["4", "8:1"],
          "21h. that re-approach's own start re-raises it in its batch (retail CONT re-raises "
          "16 of 16)", f"{shape(sent)}")
    st["agents"][10]["dead"] = True
    sent.clear()
    authsrv.attack_tick(send, st, 0)
    check(shape(sent) == ["8:0"] and st.get("action_hold") == 0,
          "21i. the target's death releases it on the target-gone tick (recorded: retail waits "
          "for the chain's next scheduled event, 50 of 59)", f"{shape(sent)}")
    # the live interact walk (the router door): our walk goes out with the hold released
    st = _state()
    st.update({"pos": (0.0, 0.0), "plane": 0, "action_hold": 1, "press_hold": True,
               "agent_pos": {77: (2000.0, 0.0)}})
    sent.clear()
    authsrv._handle_interact(send, st, 0, 77)
    sh21j = shape(sent)
    check(sh21j[:1] == ["8:0"] and st.get("action_hold") == 0,
          "21j. an interact walk to a far NPC releases a start's hold first (retail: 0 of 458 own "
          "0x002A arrive held) -- on the live door, not --interact-walk's", f"{sh21j}")
    src = open(authsrv.__file__, encoding="utf-8").read()
    args = open(os.path.join(os.path.dirname(authsrv.__file__), "serverargs.py"),
                encoding="utf-8").read()
    i_ans = src.find('    _press_answered(state, rec, conn_id, "swing")\n')
    i_site = src.find("    if ATTACK_START_HOLDS:\n", i_ans)
    i_flush = src.find("    _chain_pause_flush(state, rec, conn_id)\n", i_ans)
    check(authsrv.ATTACK_START_HOLDS is True and 0 < i_ans < i_site < i_flush
          and src.count(" if SWING_HOLDS_WALK_GATE:\n") == 3
          and src.count("    elif SWING_HOLDS_WALK_GATE:\n") == 1
          and "--no-attack-start-hold" in args and "if a.no_attack_start_hold:" in src,
          "21k. the hold rides the one start site, after the press is answered and before the "
          "chain-pause flush; hit_enemy's three unarmed sites keep SWING_HOLDS_WALK_GATE; the "
          "revert arm is wired", f"offsets {i_ans} {i_site} {i_flush}")


def section_placement_frame():
    """MOVECODE-1z-ds.20: our placement is the standing frame, and the press ends the click's
    destination. Found by the 1z-ds.13-.19 review's integration drive (pre-existing): after
    stand -> click -> press, the reach frame was the 0x0047 from BEFORE the click."""
    import time
    import authsrv
    import leadgeom

    print("\n20. 1z-ds.20: a placement of ours is where the body stands")
    DEST, START = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION, authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET

    def stand_click_press(frame_on=True, dest_on=True, leg_age=3.0):
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))  # noqa: E731
        t = time.time()
        st = _state()
        st["agents"][10]["pos"] = (0.0, 40.0)
        st.update({"pos": (0.0, 911.0), "plane": 0, "player_health": 100.0,
                   "player_dead": False, "player_last_swing": 0.0,
                   "last_report": (0.0, 911.0, True, t - leg_age - 0.5),   # the 0x0047 BEFORE the click
                   "click_moving_at": t - leg_age, "dest": (0.0, 100.0),
                   "click_leg": leadgeom._leg_record((0.0, 911.0), (0.0, 100.0), t - leg_age, 288.0)})
        saved = (authsrv.PLACEMENT_IS_FRAME, authsrv.PRESS_ENDS_CLEARS_DEST)
        authsrv.PLACEMENT_IS_FRAME, authsrv.PRESS_ENDS_CLEARS_DEST = frame_on, dest_on
        try:
            authsrv._press_supersedes(send, st, 0, 10)
            pin = [v for op, v, l in sent if "PRESS ENDS THE WALK" in l]
            dest_after = st.get("dest")
            authsrv.begin_attack(send, st, 10, 0)
            frame = authsrv._reach_frame(st)          # what the tick's reach gate will read
            sent.clear()
            authsrv.attack_tick(send, st, 0)
        finally:
            authsrv.PLACEMENT_IS_FRAME, authsrv.PRESS_ENDS_CLEARS_DEST = saved
        ops = [op for op, _v, _l in sent]
        return pin, dest_after, frame, ops, sent

    pin, _d, frame, ops, sent = stand_click_press()
    check(pin and abs(pin[0][1][1] - 100.0) < 1.0 and abs(frame[1] - 100.0) < 1.0
          and any(op == START for op in ops) and DEST not in ops,
          "20a. stand -> click -> press after arrival: the frame is OUR pin (0, 100), 60 u from "
          "the foe, so the swing opens at once and no follow goes out",
          f"pin {pin}, frame {frame}, tick {[l[:40] for _o, _v, l in sent]}")
    _p, _d, frame0, ops0, sent0 = stand_click_press(frame_on=False)
    check(abs(frame0[1] - 911.0) < 1.0 and DEST in ops0,
          "20b. KNOWN-BAD ARM (--frame-ignores-placement): the frame is the pre-click 0x0047 "
          "(0, 911), and the tick sends a phantom follow 871 u out beside the swing -- the "
          "review's variant B, whose leg then held the next swing 1.15 s late",
          f"frame {frame0}, tick {[l[:40] for _o, _v, l in sent0]}")
    _p, dest1, _f, _o, _s = stand_click_press(leg_age=1.0)
    _p, dest0, _f, _o, _s = stand_click_press(leg_age=1.0, dest_on=False)
    check(dest1 is None and dest0 == (0.0, 100.0),
          "20c. a press 1 s into the click walk ends the click's destination too; the known-bad "
          "arm (--press-keeps-click-dest) leaves (0, 100) armed for the integrator to walk on to",
          f"shipped {dest1}, known-bad {dest0}")
    t = time.time()
    st = _state()
    st.update({"last_report": (0.0, 109.0, True, t - 5.0), "pos": (900.0, 900.0)})
    authsrv._forget_client_position(st, "the wipe placed the player at the shrine (test)")
    fw = authsrv._reach_frame(st)
    saved = authsrv.PLACEMENT_IS_FRAME
    authsrv.PLACEMENT_IS_FRAME = False
    try:
        fw0 = authsrv._reach_frame(st)
    finally:
        authsrv.PLACEMENT_IS_FRAME = saved
    check(abs(fw[0] - 900.0) < 1.0 and abs(fw[1] - 900.0) < 1.0 and abs(fw0[1] - 109.0) < 1.0,
          "20d. the wipe's shrine placement is the frame before any report -- the known-bad arm "
          "keeps the corpse's 0x0047 (a press then landed on a foe 1,273 u away)",
          f"shipped {fw}, known-bad {fw0}")
    st["last_report"] = (50.0, 50.0, True, time.time() + 1.0)      # the client speaks after it
    fr = authsrv._reach_frame(st)
    check(abs(fr[0] - 50.0) < 1.0 and abs(fr[1] - 50.0) < 1.0,
          "20e. CONTROL: a 0x0047 newer than our placement is the frame again -- the client's word "
          "out-ranks ours once it speaks", f"{fr}")
    src = open(authsrv.__file__, encoding="utf-8").read()
    args_src = open(os.path.join(os.path.dirname(authsrv.__file__), "serverargs.py"),
                    encoding="utf-8").read()
    check("--frame-ignores-placement" in args_src and "if a.frame_ignores_placement:" in src
          and "--press-keeps-click-dest" in args_src and "if a.press_keeps_click_dest:" in src,
          "20f. --frame-ignores-placement and --press-keeps-click-dest are wired")

    # 20g-j. MOVECODE-1z-ds.30: a NEW follow's leg starts at the keyboard body estimate the snap
    # guard reckoned, not the world-0 mirror (the critic's M3: the body-start lerp nearer 16 of 17).
    class _Rw:
        def __init__(self): self.rows = []
        def event(self, kind, **kw): self.rows.append((kind, kw))

    def follow_from(on=True, walking=True, repath=False):
        sent, rec = [], _Rw()
        send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))  # noqa: E731
        now = time.time()
        st = _state()
        agent = st["agents"][10]
        agent["pos"] = (0.0, 0.0)
        at = now - 0.5
        st.update({"plane": 0, "client_pos": (400.0, 0.0), "client_pos_at": at,
                   "pos": (256.0, 0.0)})
        if walking:                                   # a W walk toward the foe, 0.5 s old
            st["client_heading"] = (-766.0, 0.0, 1, at)
            st["last_report"] = (400.0, 0.0, False, at)
        else:                                         # standing: the 0x0047 is the frame
            st["last_report"] = (400.0, 0.0, True, at)
        saved = (authsrv.FOLLOW_LEG_FROM_BODY, authsrv._npc_mirror_pos)
        authsrv.FOLLOW_LEG_FROM_BODY = on
        authsrv._npc_mirror_pos = lambda s, n: (320.0, 0.0)   # the mirror, 64 u behind the body
        try:
            authsrv._approach_send(send, st, 0, 10, agent, now, repath=repath, rec=rec)
        finally:
            authsrv.FOLLOW_LEG_FROM_BODY, authsrv._npc_mirror_pos = saved
        row = [kw for k, kw in rec.rows if k == "approach"]
        return st.get("click_leg"), (row[0] if row else {}), sent

    leg, row, _s = follow_from()
    check(leg is not None and abs(leg["p0"][0] - 256.0) < 1.0 and abs(leg["dist"] - 176.0) < 1.0
          and row.get("origin") == [256.0, 0.0] and row.get("frame_origin") == [320.0, 0.0],
          "20g. a follow from a key-walking body starts its leg at the estimate (the report "
          "advanced 0.5 s at 288 u/s: (256, 0)), 176 u to the disc, and the row names both origins",
          f"leg {leg and (leg['p0'], round(leg['dist'], 1))}, row {row.get('origin')} / "
          f"{row.get('frame_origin')}")
    leg0, _r, _s = follow_from(on=False)
    check(leg0 is not None and abs(leg0["p0"][0] - 320.0) < 1.0,
          "20h. KNOWN-BAD ARM (--follow-leg-from-frame): the leg starts at the mirror, 64 u off "
          "the body, its eta 0.22 s late -- B2", f"p0 {leg0 and leg0['p0']}")
    leg_s1, _r, _s = follow_from(walking=False)
    leg_s0, _r, _s = follow_from(on=False, walking=False)
    check(leg_s1 is not None and leg_s0 is not None and abs(leg_s1["p0"][0] - 400.0) < 1.0
          and leg_s1["p0"] == leg_s0["p0"],
          "20i. CONTROL: a standing body (the 0x0047 last, no heading) starts at the report under "
          "both arms", f"{leg_s1 and leg_s1['p0']} / {leg_s0 and leg_s0['p0']}")
    leg_r, _r, _s = follow_from(repath=True)
    check(leg_r is not None and abs(leg_r["p0"][0] - 320.0) < 1.0,
          "20j. a RE-PATH keeps the frame (the mirror models the avoidance halts our leg does "
          "not)", f"{leg_r and leg_r['p0']}")


def section_press_stop_hold():
    """MOVECODE-1z-ds.6: the press stop carries retail's [8, me, 1], kept to the next input.

    Retail's in-reach walking press batch (pressstopjoin's 42-press cell) is the hold then
    the 0x0028 -- 42 of 42 carry the hold, 40 in the stop's own instant -- and the hold is
    released after the swing's close on 35 of 36, by the player's next input, never by the
    landing. Driven through the real begin_attack and attack_tick, the landing included."""
    import time
    import authsrv

    print("\n9l. 1z-ds.6: the press stop holds the walk gate to the next input")

    class _PM:
        def walkable(self, x, y):
            return True

        def clip(self, x0, y0, x1, y1, step=None):
            return (x1, y1)

        def plane_at(self, x, y, prefer=None):
            return prefer

        def containing(self, x, y):
            return []

    INT, GV8 = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT, authsrv.agents.GV_DISABLED
    PIN, HALT = authsrv.GAME_SMSG_AGENT_UPDATE_POSITION, authsrv.GAME_SMSG_AGENT_STOP_MOVING
    DEST = authsrv.GAME_SMSG_AGENT_UPDATE_DESTINATION

    def holds(rows):
        return [v[2] for op, v, _l in rows if op == INT and v[0] == GV8 and v[1] == PLAYER]

    def walking(hold=True):
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))  # noqa: E731
        t = time.time()
        st = _state()
        st.update({"client_pos": (30.0, 0.0), "client_pos_at": t - 0.1, "client_plane": 0,
                   "kbd_moving_at": t - 0.1, "heading": (0.0, 766.0), "heading_mt": 1,
                   "pathmap": _PM()})
        saved = authsrv.PRESS_STOP_HOLDS
        authsrv.PRESS_STOP_HOLDS = hold
        try:
            authsrv.begin_attack(send, st, 10, 0)
        finally:
            authsrv.PRESS_STOP_HOLDS = saved
        return st, send, sent

    st, send, sent = walking()
    seq = [("8:%d" % v[2]) if op == INT and v[0] == GV8 else op for op, v, _l in sent]
    check(seq == [PIN, "8:1", HALT] and st.get("press_hold") is True
          and st.get("action_hold") == 1,
          "9l-a. the press batch is the pin, [8, me, 1], then the 0x0028 -- retail's hold "
          "ahead of its stop (40 of 42 in one instant), our pin ahead of both", f"{seq}")
    sent.clear()
    authsrv.attack_tick(send, st, 0)
    opened = [l for op, _v, l in sent if "player swings" in l]
    sent.clear()
    _rewind(st, authsrv.swing_windup(authsrv.ATTACK_INTERVAL) + 0.01)
    authsrv.attack_tick(send, st, 0)
    check(len(opened) == 1 and holds(sent) == [] and st.get("action_hold") == 1
          and st.get("press_hold") is True,
          "9l-b. the swing opens and LANDS with the hold kept -- retail ends it after the "
          "close on 35 of 36, at the next input, never at the landing",
          f"opened {opened}, landing holds {holds(sent)}, hold {st.get('action_hold')}")
    sent.clear()
    authsrv.cancel_on_move(send, st, 0, moved=5.0)
    check(holds(sent) == [0] and "press_hold" not in st and st.get("action_hold") == 0,
          "9l-c. the next movement report releases it ([8, me, 0], the 26-of-42 cause) and "
          "the mark goes with it", f"{holds(sent)}")

    st2, send2, sent2 = walking()
    st2.pop("press_hold", None)          # not a subscript: a mutation must FAIL here, not abort
    _sa9 = authsrv.ATTACK_START_HOLDS
    authsrv.ATTACK_START_HOLDS = False   # 1z-ds.31's start re-marks it; this is the exemption's control
    try:
        authsrv.attack_tick(send2, st2, 0)
        sent2.clear()
        _rewind(st2, authsrv.swing_windup(authsrv.ATTACK_INTERVAL) + 0.01)
        authsrv.attack_tick(send2, st2, 0)
    finally:
        authsrv.ATTACK_START_HOLDS = _sa9
    check(holds(sent2) == [0],
          "9l-d. CONTROL: the same landing with the mark gone releases the hold -- the "
          "exemption, not the landing path, is what keeps it", f"{holds(sent2)}")

    st3, send3, sent3 = walking()
    sent3.clear()
    authsrv._approach_send(send3, st3, 0, 10, st3["agents"][10], time.time())
    ops3 = [("8:%d" % v[2]) if op == INT and v[0] == GV8 else op for op, v, _l in sent3]
    check(ops3[:2] == ["8:0", DEST] and "press_hold" not in st3,
          "9l-e. a NEW follow releases it first, adjacent to the 0x002A (retail's "
          "re-approach shape, RANGERPRE-S16)", f"{ops3}")

    st4, _send4, sent4 = walking(hold=False)
    seq4 = [op for op, _v, _l in sent4]
    check(seq4 == [PIN, HALT] and holds(sent4) == [] and not st4.get("press_hold"),
          "9l-f. KNOWN-BAD ARM (--no-press-stop-hold): the pin and the halt with no hold -- "
          "round 1, retail's 0 of 42", f"{seq4}")

    # 1z-ds.7: REACH IS THE BODY'S. The owner's walk-ins (20261002T005405: 3 of 7 stops
    # judged in reach on a stale frame, the body 162-170 u out, then released for a
    # follow). Retail: 0 stops before 57 follows.
    def placed(frame, rep, heading, age, on_body=True):
        sent_p = []
        send_p = lambda op, vals, label="", quiet=False: sent_p.append((op, vals, label))  # noqa: E731
        t = time.time()
        stp = _state()
        stp.update({"pos": frame, "client_pos": rep, "client_pos_at": t - age,
                    "client_plane": 0, "kbd_moving_at": t - age, "heading": heading,
                    "heading_mt": 1, "pathmap": _PM()})
        saved = authsrv.PRESS_STOP_ON_BODY
        authsrv.PRESS_STOP_ON_BODY = on_body
        try:
            authsrv.begin_attack(send_p, stp, 10, 0)
            batch = [("8:%d" % v[2]) if op == INT and v[0] == GV8 else op
                     for op, v, _l in sent_p]
            sent_p.clear()
            authsrv.attack_tick(send_p, stp, 0)
        finally:
            authsrv.PRESS_STOP_ON_BODY = saved
        tick = [op for op, _v, _l in sent_p]
        swung = any("player swings" in l for _op, _v, l in sent_p)
        return batch, tick, swung, stp

    # frame ON the target (0 u), the body 0.5 s down +x at 288 u/s: (244, 0), 244 u out
    b7, k7, sw7, s7 = placed((0.0, 0.0), (100.0, 0.0), (766.0, 0.0), 0.5)
    check(b7 == [PIN] and DEST in k7 and not sw7 and not s7.get("action_hold")
          and not s7.get("press_hold"),
          "9l-g. the frame says IN reach but the reckoned body is 244 u OUT: the pin ALONE "
          "(no hold, no halt), and the tick answers with the follow, no swing -- retail "
          "sends 0 stops before 57 follows", f"press {b7}, tick {k7}, swung {sw7}")
    # frame 500 u out (stale), the body 0.6 s down -x from 280: (107, 0), IN reach
    b8, k8, sw8, _s8 = placed((500.0, 0.0), (280.0, 0.0), (-766.0, 0.0), 0.6)
    check(b8 == [PIN, "8:1", HALT] and sw8 and DEST not in k8,
          "9l-h. the stale frame says OUT but the body is 107 u IN: the full stop, and the "
          "swing opens at once instead of an 80 u walk-in", f"press {b8}, tick {k8}, swung {sw8}")
    b9, k9, sw9, _s9 = placed((0.0, 0.0), (100.0, 0.0), (766.0, 0.0), 0.5, on_body=False)
    check(b9 == [PIN, "8:1", HALT] and DEST in k9 and not sw9,
          "9l-i. KNOWN-BAD ARM (--press-stop-on-frame): 9l-g's press is STOPPED on the "
          "frame's word, then walked in -- the owner's 'attack start delay'",
          f"press {b9}, tick {k9}")


def main():
    section_two_phases()
    section_start_to_start()
    section_lost_target()
    section_direct_calls_unchanged()
    section_press_stops_swing()
    section_pause_and_resume()
    section_retarget()
    section_chain_pause()
    section_landing_hold_release()
    section_click_latch_bound()
    section_click_leg_eta()
    section_reach_and_approach()
    section_press_supersedes_and_move_ends()
    section_press_ends_kbd_latch()
    section_press_stop_hold()
    section_dead_press()
    section_windup_holds_approach()
    section_attack_start_holds()
    section_placement_frame()
    section_still_streak()
    section_no_target_charge()
    section_reach_frame()
    section_swing_clock_carry()
    section_combat_deadlines()
    print("\n12. an in-flight swing DROP writes a row and prints (SWINGCANCEL)")
    # RUN-1zCG session 8: 4 of the operator's 7 "full animation, no damage"
    # swings left NO row anywhere. `_press_refused` returns early once the
    # press is answered, and a swing in flight is by definition one whose
    # press was answered -- so every in-flight drop went through a logger
    # that had already declined to log. This section runs the known-bad arm
    # FIRST: with the helper stubbed out, the reach drop is silent, which is
    # the state the run caught.
    class _Rec:
        def __init__(self): self.rows = []
        def event(self, kind, **kw): self.rows.append((kind, kw))

    import authsrv

    def _armed_world(dist):
        """A player with a swing in flight and the target `dist` away."""
        st = _state()
        st["agents"][10]["pos"] = (float(dist), 0.0)
        st["agents"][10]["plane"] = 0
        st["attacking"] = 10
        st["player_health"] = 100.0
        st["player_dead"] = False
        now = _tt.time()
        st["player_swing"] = {"target": 10, "armed_at": now,
                              "lands_at": now + 10.0}   # never lands on its own
        return st

    # SLICE-F21 FIRST: under the default an armed swing 400 u out is NOT
    # dropped -- it survives the tick, writes no swing_verdict row, and lands
    # when due (retail 33 of 34 / 7 of 7). The drop, and the row that names
    # it, are the --no-late-hit arm's below.
    rec = _Rec()
    st = _armed_world(400.0)
    authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
    _rows = [kw for kind, kw in rec.rows if kind == "swing_verdict"]
    check(st["player_swing"] is not None and not _rows,
          "SLICE-F21: an armed swing past reach SURVIVES the reach gate -- "
          "no drop, no swing_verdict row (the gate is for the next START)",
          f"swing={st['player_swing']}, rows={_rows}")
    st["player_swing"]["lands_at"] = _tt.time() - 0.01
    _hits = []
    authsrv.attack_tick(lambda op, v, label="", quiet=False: _hits.append((op, v)),
                        st, 0, rec=rec)
    check(st["player_swing"] is None
          and st["agents"][10]["health"] < 100.0
          and any(op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
                  for op, _v in _hits),
          "and when due it LANDS from 400 u -- the damage goes out, the swing "
          "is spent", f"health={st['agents'][10]['health']}, sent={_hits}")
    saved_lh = authsrv.LATE_HIT
    authsrv.LATE_HIT = False
    # THE KNOWN-BAD ARM: the old code path, with the drop unlogged.
    saved = authsrv._swing_dropped
    authsrv._swing_dropped = lambda *a, **k: None
    try:
        rec = _Rec()
        st = _armed_world(400.0)          # far beyond attack_reach()
        authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
        # RE-AIMED 2026-09-10 (1z-dm), not loosened: this asserted `not
        # rec.rows` -- an EMPTY recorder -- when its subject is that the SWING
        # DROP is silent. 1z-dm's `approach` row now rides the same tick (the
        # target is 400 u away, so the approach sends), which is a different
        # row saying a different thing. The subject keeps its exact assertion;
        # the denominator stops being "everything anyone ever records".
        _swing_rows = [r for r in rec.rows if r[0] in ("swing_verdict", "press_verdict")]
        check(st["player_swing"] is None and not _swing_rows,
              "KNOWN-BAD ARM: the drop happens and writes NOTHING",
              f"swing={st['player_swing']}, swing/press rows={_swing_rows} "
              f"(all rows: {[r[0] for r in rec.rows]}) -- this is what "
              f"session 8 captured, and a check that cannot see it is the "
              f"reason the symptom survived a green suite")
    finally:
        authsrv._swing_dropped = saved

    # THE SHIPPED ARM: the same drop, now named.
    rec = _Rec()
    st = _armed_world(400.0)
    authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
    rows = [kw for kind, kw in rec.rows if kind == "swing_verdict"]
    check(st["player_swing"] is None and len(rows) == 1
          and rows[0]["branch"] == "reach",
          "the reach drop writes ONE swing_verdict row naming the branch",
          f"rows={rows}")
    authsrv.LATE_HIT = saved_lh
    check(rows and rows[0].get("dist", 0) > rows[0].get("reach", 1e9) - 1e-9
          and rows[0]["target"] == 10,
          "and it carries the OPERANDS the branch tested -- dist and reach "
          "(both rows are the --no-late-hit arm's since SLICE-F21)",
          f"dist={rows[0].get('dist')} reach={rows[0].get('reach')} -- the "
          f"distance is read from state['pos'], the position MODEL; "
          f"§1z-cp.3 measured that model running 259 u from the drawn body, "
          f"which is why the row records the number rather than trusting it")
    check(rows and "into_windup" in rows[0] and "lands_in" in rows[0],
          "and how far into the windup the swing died",
          f"into_windup={rows[0].get('into_windup')} "
          f"lands_in={rows[0].get('lands_in')} -- a drop at 0.01 s and one at "
          f"0.7 s look identical on the wire and are different bugs")

    # A tick that drops NOTHING says nothing -- or the rows out-number swings.
    rec = _Rec()
    st = _armed_world(50.0)               # inside reach, swing survives
    authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
    check(not [kw for kind, kw in rec.rows if kind == "swing_verdict"],
          "CONTROL: a swing that is NOT dropped writes no row",
          f"rows={rec.rows} -- the tick runs many times per swing")

    # The other drop branches are named too, not just the one we caught.
    rec = _Rec()
    st = _armed_world(50.0)
    st["player_dead"] = True
    authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
    rows = [kw for kind, kw in rec.rows if kind == "swing_verdict"]
    check(len(rows) == 1 and rows[0]["branch"] == "dead-player",
          "a death mid-windup is named too",
          f"rows={rows} -- session 8's swing at t=93.93 was exactly this and "
          f"was equally silent")

    rec = _Rec()
    st = _armed_world(50.0)
    st["player_swing_cancel"] = "movement"
    authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
    rows = [kw for kind, kw in rec.rows if kind == "swing_verdict"]
    check(len(rows) == 1 and rows[0]["branch"] == "cancel:movement",
          "and so is a movement cancel, with the CANCELLER named",
          f"rows={rows} -- this one was already visible on the wire as an "
          f"attack_stopped; the row makes the three cancellers separable")

    print("\n13. the swing lifecycle against retail's own (MOVECODE-1z-da)")
    # 1z-da asked whether `attack_tick`'s reach gate and `_npc_follow_tick`
    # should read the report instead of the position model, and the corpus
    # REFUTED the repair: ArenaNet's own copy of the player sits 22-36 u from
    # a FRESH report and 1014 u from a stale one, AHEAD of it 27 times to 18
    # behind. What the same corpus names instead is the cancel rate. These
    # pins are FLOORS and a CEILING, not exact values -- the live corpus grows
    # (project-rurik-corpus-counts-redden).
    import os
    import sys as _sys
    _here = os.path.dirname(os.path.abspath(__file__))
    _sys.path.insert(0, os.path.join(_here, "..", "..", "studies", "movecode",
                                     "review"))
    try:
        import swingcensus
        cen = swingcensus.census()
        sc = swingcensus.score(cen)
    except Exception as exc:                                  # noqa: BLE001
        LEDGER.skip("13. the swing lifecycle against retail's",
                    f"no gamesrv corpus on this machine: {exc!r}")
        return LEDGER.verdict()
    check(sc["swings"] >= 700 and sc["landed"] >= 585,
          "our own swing corpus is still at least what 1z-da measured",
          f"{sc['landed']} landed of {sc['swings']} swings (floors 585/700)")
    silent = (sc["by_branch"].get("reach", 0)
              + sc["by_branch"].get("unattributed", 0))
    check(silent <= 0.03 * sc["swings"],
          "the SILENT drop stays at retail's own rate (retail 0.8 %)",
          f"{silent} of {sc['swings']} = "
          f"{100.0*silent/sc['swings']:.1f} % -- retail's 11 of 1,332 is "
          f"0.8 %, so this is a CEILING at 3 %, not a target. 1z-cx's four "
          f"whiffs were never anomalous as a rate; they were anomalous in "
          f"leaving no row")
    cancel = sc["by_branch"].get("cancel", 0)
    check(cancel >= 100,
          "and the CANCEL population is still the arc's real divergence",
          f"{cancel} of {sc['swings']} = {100.0*cancel/sc['swings']:.1f} % "
          f"against retail's 6.1 % -- 2.4x. A floor, so this reddens if the "
          f"census stops seeing them, never if the gap widens")
    try:
        r = swingcensus.retail()
    except Exception as exc:                                  # noqa: BLE001
        LEDGER.skip("13b. retail's half", f"no live corpus: {exc!r}")
        return LEDGER.verdict()
    n = r.get("started", 0)
    check(n >= 1332 and r.get("damage", 0) >= 1235,
          "retail's own lifecycle is still on the wire: >= 1,332 starts, "
          ">= 1,235 landing damage",
          f"{r.get('damage')} of {n} = {100.0*r.get('damage',0)/n:.1f} %")
    check(r.get("silent", 0) <= 0.03 * n and r.get("stopped", 0) <= 0.12 * n,
          "and its silent and stopped rates are the numbers 1z-da compared to",
          f"silent {r.get('silent')} ({100.0*r.get('silent',0)/n:.1f} %), "
          f"stopped {r.get('stopped')} ({100.0*r.get('stopped',0)/n:.1f} %). "
          f"The attacker slot is MEASURED: 0x00A0 is [prop, attacker, target], "
          f"876 to 28 -- reading it victim-first turns 92.7 % into 0.8 %, and "
          f"that was 1z-da's first cut")

    print("\n14. a report that moved NOTHING does not cancel the chain "
          "(MOVECODE-1z-db)")
    # 1z-db: `cancel_on_move`'s own docstring justified firing on every
    # 0x003D with "every one of 7,988 corpus records carries movementType
    # 1..8, so any 0x003D is movement" -- which proves the FIELD IS SET, not
    # that the body moved. The KNOWN-BAD ARM runs first.
    import agents
    import authsrv

    def _swinging():
        st = _state()
        st["attacking"] = 10
        st["player_health"] = 100.0
        st["player_dead"] = False
        now = _tt.time()
        st["player_swing"] = {"target": 10, "armed_at": now,
                              "lands_at": now + 10.0}
        st["last_report"] = (0.0, 0.0, False, now)
        return st

    def _run(moved, needs=True):
        sent = []
        saved = authsrv.MOVE_CANCEL_NEEDS_DISPLACEMENT
        st = _swinging()
        try:
            authsrv.MOVE_CANCEL_NEEDS_DISPLACEMENT = needs
            authsrv.cancel_on_move(
                lambda op, vals, label="", quiet=False:
                    sent.append((op, vals, label)),
                st, 0, moved=moved)
        finally:
            authsrv.MOVE_CANCEL_NEEDS_DISPLACEMENT = saved
        stopped = [v for op, v, _l in sent
                   if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                   and v[0] == agents.GV_ATTACK_STOPPED]
        return st, stopped

    st, stopped = _run(0.0, needs=False)
    check(bool(stopped) and st.get("player_swing_cancel") == "movement",
          "KNOWN-BAD ARM: a report that moved 0.00 u still cancels the chain",
          f"stopped={len(stopped)}, cancel={st.get('player_swing_cancel')!r} "
          f"-- 50 of our 104 chain cancels over 68 captures fired on a windup "
          f"whose report never moved, 36 with a 0x003D nearest the stop")

    st, stopped = _run(0.0)
    check(not stopped and st.get("player_swing_cancel") is None,
          "SHIPPED: a report that moved 0.00 u leaves the swing alone",
          f"stopped={len(stopped)}, cancel={st.get('player_swing_cancel')!r}")

    st, stopped = _run(0.5)
    check(not stopped and st.get("player_swing_cancel") is None,
          "and so does one inside the measured gap (0.5 u)",
          "16,711 consecutive accepted reports: 11.8 % repeat to the DECIMAL "
          "and only 0.1 % land in (0.001, 1) u, so the epsilon sits in an "
          "EMPTY gap and cannot bite whatever value in it is chosen")

    st, stopped = _run(60.0)
    check(bool(stopped) and st.get("player_swing_cancel") == "movement",
          "a REAL move (60 u, near the p50 of 55.9) still cancels -- the rule "
          "is retail's and is not being weakened",
          f"stopped={len(stopped)} -- retail's player cancels 63.6 % of the "
          f"swings it moves during (7 of 11) against 1.0 % of the ones it "
          f"stands through (9 of 892)")

    st, stopped = _run(None)
    check(bool(stopped),
          "CONTROL: the CLICK arm passes moved=None and is untouched",
          f"stopped={len(stopped)} -- a 0x003E is an explicit move ORDER, not "
          f"a report, and the cast half of cancel_on_move is untouched on "
          f"both arms (castmech's evidence, not measured here)")

    # 1z-dd: RUN-1zDB leg A, t=30.36 -- the suppression above printed "the
    # swing keeps its windup" and the same report forgot the TARGET through
    # a second, ungated door; attack_tick then dropped the swing 0.02 s
    # later as `move-ended-order`, 62 ms before it landed, with no stop on
    # the wire. The KNOWN-BAD ARM runs first, as before.
    st, _stopped = _run(0.0, needs=False)
    check(st.get("attacking") is None,
          "KNOWN-BAD ARM: a report that moved 0.00 u also FORGETS THE TARGET",
          f"attacking={st.get('attacking')!r} -- gamesrv.log 20260910T141335 "
          f"line 396 'chain cancel SUPPRESSED ... keeps its windup', line 400 "
          f"'SWING DROPPED in flight: move-ended-order ... lands_in 0.062'")

    st, _stopped = _run(0.0)
    check(st.get("attacking") == 10,
          "SHIPPED: a report that moved 0.00 u keeps the target as well as the "
          "swing",
          f"attacking={st.get('attacking')!r}")

    st, _stopped = _run(60.0)
    check(st.get("attacking") is None,
          "a REAL move (60 u) still forgets the target -- ANIMREF-RE 39's "
          "28 of 28 re-presses were real moves",
          f"attacking={st.get('attacking')!r}")

    st, _stopped = _run(None)
    check(st.get("attacking") is None,
          "CONTROL: the CLICK arm (moved=None) still forgets the target",
          f"attacking={st.get('attacking')!r}")

    # And the swing a still report left alone LANDS on the next tick, with
    # no `move-ended-order` row -- the whole point of the run.
    class _Rec:
        def __init__(self): self.rows = []
        def event(self, kind, **kw): self.rows.append((kind, kw))

    st, _stopped = _run(0.0)
    st["agents"][10]["pos"] = (50.0, 0.0)          # in reach
    st["player_swing"]["lands_at"] = _tt.time() - 0.01
    st["player_last_swing"] = 0.0
    rec = _Rec()
    landed = []
    saved_hit = authsrv.hit_enemy
    try:
        authsrv.hit_enemy = (lambda send, state, target, conn_id, armed=False,
                             **kw: landed.append((target, armed)))
        authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
    finally:
        authsrv.hit_enemy = saved_hit
    dropped = [kw for kind, kw in rec.rows
               if kind == "swing_verdict" and kw.get("branch") == "move-ended-order"]
    check(landed == [(10, True)] and not dropped and st.get("player_swing") is None,
          "the swing a still report left alone LANDS on the next tick, and "
          "writes no move-ended-order row",
          f"landed={landed} dropped={dropped} swing={st.get('player_swing')!r} "
          f"-- retail's still-report windups: NOT FOUND, 0 of 903 "
          f"(review/stillwindup.py), so this rests on 1z-db's rule alone")

    print("\n15. the chain pause says how much it charged, and what left early "
          "(MOVECODE-1z-dc)")
    # 1z-dc measured the pause charging 19 % of the real moving span (p50
    # 0.234 s against 0.951 s) where charging the whole span reproduces
    # retail (2.701 s against their 2.657 s). Three candidate suppressors
    # were tested against the corpus and ALL THREE FAILED, so nothing about
    # the cause is shipped -- what ships is the row that will name it. The
    # KNOWN-BAD ARM is the state before it: a moving tick that returns early
    # is indistinguishable from one that charged nothing.
    import agents
    import authsrv

    class _R:
        def __init__(self): self.rows = []
        def event(self, kind, **kw): self.rows.append((kind, kw))

    def _st_moving(dist, **over):
        st = _state()
        st["agents"][10]["pos"] = (float(dist), 0.0)
        st["attacking"] = 10
        st["player_health"] = 100.0
        st["player_dead"] = False
        st["kbd_moving_at"] = _tt.time()      # the latch _player_body_moving reads
        st.update(over)
        return st

    saved_int = authsrv.ATTACK_INTERVAL
    try:
        # A moving tick that leaves through the REACH branch is counted.
        rec = _R()
        st = _st_moving(400.0)
        authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
        stats = st.get("chain_pause_stats")
        check(stats is not None and stats["left"].get("reach") == 1
              and stats["ticks_moving"] == 1,
              "a MOVING tick that returns at the reach branch is counted, with "
              "the branch named",
              f"{stats} -- before this row such a tick was indistinguishable "
              f"from one that charged nothing, which is why 1z-dc could "
              f"measure the 19 % shortfall and not attribute it")

        # A moving tick that leaves through dead-player is counted separately.
        rec = _R()
        st = _st_moving(50.0, player_dead=True)
        authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
        stats = st.get("chain_pause_stats")
        check(stats is not None and stats["left"].get("dead-player") == 1,
              "and so is one that returns at dead-player, under its own name",
              f"{stats} -- four branches return above the accumulator and the "
              f"row separates them")

        # A tick that is NOT moving counts nothing at all.
        rec = _R()
        st = _st_moving(400.0)
        st["kbd_moving_at"] = None
        authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
        check(st.get("chain_pause_stats") is None,
              "CONTROL: a STILL tick counts nothing -- the row is about the "
              "pause, not about the tick",
              f"{st.get('chain_pause_stats')}")

        # The summary rides the swing that opens, then resets.
        # The flush rides the swing that OPENS, and a swing can only open on
        # a tick that is NOT moving -- while the body moves the clock is
        # frozen, which is the mechanic itself. So: accumulate while moving,
        # motion ends, the next swing opens and carries the summary out.
        rec = _R()
        st = _st_moving(50.0)
        authsrv.begin_attack(lambda *a, **k: None, st, 10, 0)
        st["chain_pause_stats"] = {"charged": 0.4, "ticks_moving": 9,
                                   "left": {"reach": 3}}
        st["kbd_moving_at"] = None            # motion ended
        authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
        rows = [kw for kind, kw in rec.rows if kind == "chain_pause"]
        check(len(rows) == 1 and rows[0]["charged"] == 0.4
              and rows[0]["left"].get("reach") == 3
              and st.get("chain_pause_stats") is None,
              "the summary rides the swing that OPENS and then resets -- one "
              "row per swing, not 20 per second",
              f"rows={rows}, left={st.get('chain_pause_stats')}")
    finally:
        authsrv.ATTACK_INTERVAL = saved_int

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
