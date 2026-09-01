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
import time as _tt

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402

# FLOOR 41, from the green runs of 2026-09-01 that added section 7, the
# ANIMREF-RE 33 F5 click-latch bound (35 with section 6's landing hold
# release; 30 with section 5's chain pause; 24 before that day; 13 when the
# file carried only the windup split). Sections 5-7 are all fixture-free --
# they stub the clock and drive the real attack_tick -- so 41 is the
# BARE-MACHINE number too, measured both ways that day.
LEDGER = checks.Ledger("player swing windup", floor=42)
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
          "the KEYBOARD latch is deliberately NOT bounded here -- it is "
          "cleared by the 0x0047 stop report, which the client does send "
          "(36 of 36 in the corpus), so it has a real terminator and needs "
          "no age guess. Bounding only the latch that lacks one is the whole "
          "point",
          "old kbd latch still reads moving")

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
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
