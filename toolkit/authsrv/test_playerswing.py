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
# branches (1z-cr). MOVECODE-1z-cs +5 (128): the lifecycle pins, ours and
# retail's. MOVECODE-1z-ct +5 (133): the displacement gate, known-bad arm
# first. §13 needs the gamesrv corpus and §13b the live one; each
# declares a skip by name without it.
LEDGER = checks.Ledger("player swing windup", floor=133)
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
    ops = [op for op, _, _ in sent]
    check(ops == [authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET]
          and sent[0][1] == [authsrv.agents.GV_ATTACK_STARTED, PLAYER, 10, 0],
          "the first tick sends ATTACK_STARTED and NOTHING ELSE -- no hold, "
          "no damage. The hold used to ride behind it here; see above for "
          "the denominator that put it there",
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
    check(len(sent) == 1, "an undue swing does not land early",
          f"{len(sent)} sends")

    _rewind(state, expect + 0.01)
    authsrv.attack_tick(send, state, 0)
    ops = [op for op, _, _ in sent]
    check(ops == [authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET,
                  authsrv.AGENT_ADRENALINE_GAIN,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET,
                  authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT],
          "the landing is gain, damage, FINISHED -- and no second STARTED "
          "and NO property 8 in either direction. This check has moved "
          "twice in a day and the trail is the record: it once ended 'a "
          "landing releases nothing (the chain still holds)', which was the "
          "ANIMREF-RE 33 defect written as an assertion; 33 F1 then added a "
          "release here; 35 removed the hold that release existed for. "
          "Section 6 owns the three arms",
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
    # ANIMREF-RE 39: with the approach the DEFAULT, a target that walks out
    # of reach is answered by retail's auto-chase (a 0x002A with no press,
    # 16/24 chains on the live tapes) -- section 9 owns that. This section
    # is about the swing's silent truncation, so it runs the no-approach arm.
    saved_ap = authsrv.ATTACK_APPROACH
    authsrv.ATTACK_APPROACH = False
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
        # The SWING drops silently either way (retail's truncation). The
        # dead-target arm used to also carry [8, 31, 0] -- the one live
        # target-death close, t=20.1637, n=1, castmech 3c -- but since
        # ANIMREF-RE 35 an auto swing sets no hold, so `action_hold` is
        # transition-only and there is nothing to release. The corpus
        # instant remains true about a body that WAS holding; the door is
        # unchanged and still fires when a cast is what held.
        expected = []
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
        check(ops[:2] == [authsrv.GAME_SMSG_SKILL_ACTIVATED_BROADCAST,
                          authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT]
              and sent[1][1] == [authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0],
              "the press burst carries GV_ATTACK_STOPPED [3, agent, 0] "
              "immediately after E4, with no [8 -> 0] ahead of it -- the "
              "auto swing never held",
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
    check([(op, v) for op, v, _ in sent[:1]] ==
          [(0x009F, [authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0])],
          "and the stop rides ALONE now -- the auto swing set no hold, so "
          "the [8 -> 0] half elides. The corpus PAIR was [8 -> 0] before "
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

    def swing_cycle(hold, release):
        """One swing through the real attack_tick; return (open, landing)."""
        sent = []
        send = lambda op, vals, label="", quiet=False: sent.append(
            (op, vals, label))
        state = _state()
        sh, lr = authsrv.SWING_HOLDS_WALK_GATE, authsrv.LANDING_HOLD_RELEASE
        authsrv.SWING_HOLDS_WALK_GATE = hold
        authsrv.LANDING_HOLD_RELEASE = release
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

    # ARM 1 -- SHIPPED. No hold anywhere in the swing.
    opened, landed, st = swing_cycle(False, True)
    check(opened == [] and landed == [] and not st.get("action_hold"),
          "SHIPPED ARM: the swing sends NO property 8, at the open or the "
          "landing. The client's walk gate is never shut by an auto attack, "
          "so a pre-landing movement press meets a clear gate -- the 25-of-32 "
          "refusals the operator felt as a warp cannot occur",
          f"open={opened}, landing={landed}, hold={st.get('action_hold')}")

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

    check(st.get("action_hold", 0) == 0 and st3.get("action_hold") == 1,
          "and the shipped and known-bad arms SEPARATE on the one number "
          "that matters -- the gate's state while the player is swinging",
          f"shipped={st.get('action_hold', 0)}, legacy={st3.get('action_hold')}")

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
    """ANIMREF-RE 31: the swing clock freezes while the body moves.

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

    print("\n5. ANIMREF-RE 31: the chain pauses while the body moves")

    def gap_with_move(paused, move_span):
        """Seconds between two ATTACK_STARTEDs with `move_span` of motion
        inside, driven through the REAL attack_tick on a synthetic clock."""
        sent = []
        send = lambda op, vals, label="", quiet=False: \
            sent.append((op, vals, label))
        agent = {"name": "t", "dead": False, "last_hit": 0.0,
                 "max_health": 1e9, "health": 1e9, "pos": (0.0, 0.0)}
        state = {"agents": {10: agent}, "pos": (0.0, 0.0), "attacking": 10}
        saved = authsrv.CHAIN_PAUSES_WHILE_MOVING
        saved_time = authsrv.time.time
        authsrv.CHAIN_PAUSES_WHILE_MOVING = paused
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
            authsrv.CHAIN_PAUSES_WHILE_MOVING = saved
            authsrv.time.time = saved_time

    def ratio(paused, move_span=1.5):
        quiet = gap_with_move(paused, 0.0)
        moved = gap_with_move(paused, move_span)
        if len(quiet) < 3 or len(moved) < 3:
            return None, quiet, moved
        # the gap that CONTAINS the move: the first gap whose span covers t=2.0
        qg = [b - a for a, b in zip(quiet, quiet[1:])]
        mg = [b - a for a, b in zip(moved, moved[1:])]
        base = sorted(qg)[len(qg) // 2]
        # the move-containing gap is the widest one in the moved arm
        return (max(mg) / base if base else None), qg, mg

    r_on, q_on, m_on = ratio(True)
    r_off, q_off, m_off = ratio(False)

    check(r_on is not None and r_off is not None,
          "both arms produced enough ATTACK_STARTEDs to form gaps -- the "
          "rig is not vacuous",
          f"paused starts-gaps={m_on}, legacy={m_off}")
    if r_on is None or r_off is None:
        return

    check(r_off < 1.10,
          "KNOWN-BAD ARM: with the pause off the move-containing gap is "
          "indistinguishable from the metronome -- the free-running chain "
          "the operator played and called 'very floaty'. Retail scores 1.51 "
          "here; a chain that never notices scores ~1.0, and ours measured "
          "1.003 on the live wire",
          f"legacy ratio {r_off:.3f} (gaps {m_off})")
    check(r_on > 1.30,
          "SHIPPED ARM: the move-containing gap stretches -- the swing "
          "clock froze for the moving span, so the attack animation can "
          "finish and hand the pose back to locomotion (priority table "
          "0x00A92ED8: locomotion 0x0040 against an attack's 0x0110/0x0120)",
          f"paused ratio {r_on:.3f} (gaps {m_on})")
    check(r_on > r_off + 0.25,
          "and the two arms SEPARATE -- a metric that scored them alike "
          "would be measuring the wrong quantity, which is the whole reason "
          "this section exists",
          f"{r_on:.3f} against {r_off:.3f}")

    # THE SHAPE OF THE PAUSE: gap - moving_span must land back on the
    # metronome. Retail's residual p50 is 1.330 s, exactly its quiet median;
    # `next - last_move` does NOT land there (0 of 40), which is what makes
    # this a PAUSE rather than a re-stamp.
    span = 1.5
    base = sorted(q_on)[len(q_on) // 2]
    residual = max(m_on) - span
    check(abs(residual - base) < 0.20,
          "and it is a PAUSE, not a re-stamp: gap minus the moving span "
          "lands back on the metronome, the corpus's own signature "
          "(residual p50 1.330 s against a 1.330 s quiet median, 10/40 in "
          "band, while next-minus-last-move is 0/40)",
          f"residual {residual:.3f}s against a {base:.3f}s metronome")

    check(authsrv.CHAIN_PAUSES_WHILE_MOVING is True
          and authsrv.MOVE_KEEPS_CHAIN is True,
          "both halves are the SHIPPED default and revert together on "
          "--legacy-move-stops-chain -- one behaviour, one A/B, which is "
          "the ANIMREF-RE 29 lesson (two independent defaults meant one run "
          "convicted the pair and cleared neither)",
          f"pause={authsrv.CHAIN_PAUSES_WHILE_MOVING}, "
          f"lawA={authsrv.MOVE_KEEPS_CHAIN}")


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
    check(authsrv.ATTACK_REACH == 144.0
          and 82.7 < authsrv.ATTACK_REACH <= 205.5
          and 109.7 < authsrv.ATTACK_REACH <= 146.3,
          "ATTACK_REACH = 144 sits inside BOTH DR-free brackets retail's wire "
          "gives -- Sword (82.7, 205.5], Daggers (109.7, 146.3] -- and is the "
          "wiki's melee range; the tapes bracket it, they do not select it",
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
        check(authsrv.attack_reach() == 144.0,
              "the shipped reach is the derived 144 u",
              f"attack_reach() = {authsrv.attack_reach()}")

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
    check(n_arms == 3 and n_all == 8,
          "the 0x003D, 0x0047 and 0x003E arms each abandon the follow (3 "
          "tagged sites), attack_tick's two target-loss branches do (2), "
          "approach_tick's retarget branch (1), and since ANIMREF-RE 39 a "
          "move command (cancel_on_move) and the press that ends a click leg "
          "(_press_supersedes) -- 8 call sites, no more",
          f"arms {n_arms}, all {n_all}")
    check(src.count('state["click_moving_at"] = now') == 1,
          "the follow stamps the latch once, with the tick's `now` -- not "
          "time.time(), which test_cancelwalk pins to the click arm alone",
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
    check(src.count("attack_tick(send, state, conn_id, rec)") == 1
          and src.count("begin_attack(send, state, foe, conn_id, rec=rec)") == 1
          and src.count("begin_attack(send, state, values[1], conn_id, rec=rec)") == 1,
          "the world tick, the harness control slot and the 0x0026 arm all "
          "pass the recorder, so no press path can be silent by omission",
          "source pin")
    check(src.count('state["attack_press_at"] = now') == 1
          and src.count('state.get("attack_press_at")') == 1,
          "the press stamp has ONE writer (begin_attack) and ONE reader "
          "(_player_body_moving) -- rule 1 and the cast-stop never see it",
          "source pin")
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

    # THE KNOWN-BAD ARM: the old code path, with the drop unlogged.
    saved = authsrv._swing_dropped
    authsrv._swing_dropped = lambda *a, **k: None
    try:
        rec = _Rec()
        st = _armed_world(400.0)          # far beyond attack_reach()
        authsrv.attack_tick(lambda *a, **k: None, st, 0, rec=rec)
        check(st["player_swing"] is None and not rec.rows,
              "KNOWN-BAD ARM: the drop happens and writes NOTHING",
              f"swing={st['player_swing']}, rows={rec.rows} -- this is what "
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
    check(rows and rows[0].get("dist", 0) > rows[0].get("reach", 1e9) - 1e-9
          and rows[0]["target"] == 10,
          "and it carries the OPERANDS the branch tested -- dist and reach",
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

    print("\n13. the swing lifecycle against retail's own (MOVECODE-1z-cs)")
    # 1z-cs asked whether `attack_tick`'s reach gate and `_npc_follow_tick`
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
          "our own swing corpus is still at least what 1z-cs measured",
          f"{sc['landed']} landed of {sc['swings']} swings (floors 585/700)")
    silent = (sc["by_branch"].get("reach", 0)
              + sc["by_branch"].get("unattributed", 0))
    check(silent <= 0.03 * sc["swings"],
          "the SILENT drop stays at retail's own rate (retail 0.8 %)",
          f"{silent} of {sc['swings']} = "
          f"{100.0*silent/sc['swings']:.1f} % -- retail's 11 of 1,332 is "
          f"0.8 %, so this is a CEILING at 3 %, not a target. 1z-cr's four "
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
          "and its silent and stopped rates are the numbers 1z-cs compared to",
          f"silent {r.get('silent')} ({100.0*r.get('silent',0)/n:.1f} %), "
          f"stopped {r.get('stopped')} ({100.0*r.get('stopped',0)/n:.1f} %). "
          f"The attacker slot is MEASURED: 0x00A0 is [prop, attacker, target], "
          f"876 to 28 -- reading it victim-first turns 92.7 % into 0.8 %, and "
          f"that was 1z-cs's first cut")

    print("\n14. a report that moved NOTHING does not cancel the chain "
          "(MOVECODE-1z-ct)")
    # 1z-ct: `cancel_on_move`'s own docstring justified firing on every
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

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
