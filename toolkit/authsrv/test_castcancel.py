"""Movement cancels the cast: a bare E2, no recharge, no aftercast.

The contract is the wiki's and the shape is the corpus's. WIKI (GWW
"Cancel", rev. 2014-08-16): a cancelled skill does not activate, its initial
costs ARE incurred, it does NOT recharge, no aftercast follows. The corpus's
one terminated cast is byte-for-byte that silence: E4 t=5.027 answered by a
bare 0x00E2 at t=5.912 with no E5 between or ever after, the player's own
movement riding the same instant (studies/castmech 3-4, castgaps.py). WIKI
(GWW "Quarterstepping"): movement cannot cancel an ATTACK skill
mid-activation -- but a skill still queued, its begin not reached, drops
whatever its type.

`cancel_on_move` runs on the connection thread and only MARKS; the release
itself is cast_tick's, on the world tick -- the same single-writer split
every other phase of the cycle uses. Timing by rewinding, never sleeping.

NO VAULT, NO SOCKET, NO CLIENT: every section stubs `skill_timing` and
asserts on the CANCEL wire, which carries no content-derived value -- so the
count is the same number with and without a vault (MEASURED both ways
2026-09-01, re-measured after ANIMREF-RE 32 added the landing split: 30 and
30) and the floor below is that number for real. This
paragraph is new, and the property is one day old rather than original: until
2026-08-31 a bare run died in `handle_skill_press` with a `ContentError` on
skill 42, because `authsrv.player_rank_for_skill` was the one lookup on the
press path taking no bare-machine fallback. That was a server defect and it
is fixed there; test_bareimport.py section 3 is what keeps it fixed. The
sibling file test_castcycle.py carried the bare-machine claim in prose while
this one did not, and both were equally broken -- so an UNSTATED dependency
is not a safer one, it is only a quieter one.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402

# FLOOR 30, from the green runs of 2026-09-01 that added §7, the LANDING
# SPLIT -- the day LAW A went to the default, came back on the operator's
# "very floaty", and went out again composed with the chain pause and the
# two-regime rule. 24 earlier that day, 21 before it, 15 when the file
# carried the movement door alone. Measured both ways: 30 with a vault, 30
# without -- §7 stubs nothing it does not already stub.
LEDGER = checks.Ledger("cast cancel", floor=31)
check = LEDGER.ok

PLAYER = 1   # authsrv.PLAYER_AGENT_ID, restated so a drift reddens something


def _press(authsrv, send, state, skill=42, copy=7, target=0):
    authsrv.handle_skill_press([0, skill, copy, target], send, state, 0,
                               authsrv.GAME_CMSG_USE_SKILL)


def _rewind(state, seconds):
    for cast in state.get("pending_casts", ()):
        for k in ("e5_at", "e3_at", "e6_at", "begin_at"):
            cast[k] -= seconds


def section_move_cancels():
    import authsrv

    print("1. movement mid-activation: one bare E2, then silence forever")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}}
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (2.0, 0.75, 8.0)
    try:
        _press(authsrv, send, state)
        sent.clear()
        authsrv.cancel_on_move(send, state, 0)
        check([(op, vals) for op, vals, _ in sent] ==
              [(0x009F, [authsrv.agents.GV_DISABLED, PLAYER, 0]),
               (0x009F, [authsrv.agents.GV_SKILL_STOPPED, PLAYER, 0]),
               (0x00E2, [PLAYER, 42, 7])]
              and state["pending_casts"][0].get("cancelled"),
              "the whole release burst rides the input's own instant, in "
              "ArenaNet's order: [8 -> 0], then [59, agent, 0], then the "
              "bare E2 -- 4 of 4 cancelled casts in the live capture "
              "20260824T074002 (castmech 3f)",
              f"sent={[(hex(o), v) for o, v, _ in sent]}, "
              f"cancelled={state['pending_casts'][0].get('cancelled')}")
        sent.clear()
        check(state.get("cast_busy_until", 1e18) <= time.time(),
              "and the busy window is rolled back: the next press begins "
              "now, not behind the ghost of a cast that will never complete",
              f"busy in {state.get('cast_busy_until', 0) - time.time():.2f}s")

        authsrv.cast_tick(send, state, 0)
        check(sent == [],
              "the tick announces NOTHING a second time -- the burst went "
              "out with the input; the tick's remaining job is removal",
              f"{[(hex(o), v) for o, v, _ in sent]}")
        check(not state["pending_casts"],
              "the entry is gone", f"{state['pending_casts']}")

        sent.clear()
        _rewind(state, 60.0)
        authsrv.cast_tick(send, state, 0)
        check(sent == [],
              "and no E5, E3 or E6 ever follows: no recharge started, no "
              "aftercast served -- the wiki's cancel contract as wire "
              "silence. The press-time debit is the 'costs stay paid' half",
              f"{[(hex(o), v) for o, v, _ in sent]}")
    finally:
        authsrv.skill_timing = saved


def section_aftercast_uncancellable():
    import authsrv

    print("\n2. past its E5 a cast is aftercast, and nothing cancels that")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}}
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 8.0)
    try:
        _press(authsrv, send, state)
        _rewind(state, 1.0)
        authsrv.cast_tick(send, state, 0)                  # E5 fires
        sent.clear()
        authsrv.cancel_on_move(send, state, 0)
        check(not state["pending_casts"][0].get("cancelled"),
              "a completed activation is not marked -- WIKI: the aftercast "
              "cannot be reduced or cancelled",
              f"{state['pending_casts'][0]}")
        _rewind(state, 10.0)
        authsrv.cast_tick(send, state, 0)
        # sent[0] is the movement's own [8, agent, 0]: the hold releases on
        # ANY movement (the measured rule -- retail's client refuses input
        # during aftercast, so the mid-aftercast case has no wire witness
        # and inherits the general one). The CYCLE is untouched by it.
        check([op for op, _, _ in sent] == [0x009F, 0x00E3, 0x00E6]
              and sent[0][1] == [authsrv.agents.GV_DISABLED, PLAYER, 0],
              "and the cycle closes normally: E3, then E6 -- the recharge "
              "was already running and keeps running (the movement released "
              "the hold, nothing more)",
              f"{[hex(o) for o, _, _ in sent]}")
    finally:
        authsrv.skill_timing = saved


def section_attack_skills():
    import authsrv

    print("\n3. attack skills: movement cannot touch one mid-activation, "
          "but drops one still queued")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}}
    saved_t = authsrv.skill_timing
    saved_a = authsrv._is_attack_skill
    authsrv.skill_timing = lambda sid: (1.0, 0.0, 3.0)
    authsrv._is_attack_skill = lambda sid: True
    try:
        _press(authsrv, send, state, skill=394)            # begins NOW
        sent.clear()
        authsrv.cancel_on_move(send, state, 0)
        check(not state["pending_casts"][0].get("cancelled"),
              "mid-activation, an attack skill shrugs movement off -- WIKI "
              "(Quarterstepping): 'attack skills can not be accidentally "
              "cancelled by moving prematurely'",
              f"{state['pending_casts'][0].get('cancelled')}")
        _rewind(state, 1.0)
        authsrv.cast_tick(send, state, 0)
        check(0x00E5 in [op for op, _, _ in sent],
              "and it completes: its E5 fires on schedule",
              f"{[hex(o) for o, _, _ in sent]}")

        # A queued one is different: press a spell, then the attack skill --
        # its begin waits on the spell's aftercast, and movement drops both.
        state = {"agents": {}}
        sent2 = []
        send2 = lambda op, vals, label="", quiet=False: \
            sent2.append((op, vals, label))
        authsrv._is_attack_skill = lambda sid: sid == 394
        authsrv.skill_timing = lambda sid: (2.0, 0.75, 8.0)
        _press(authsrv, send2, state, skill=105)           # activating
        _press(authsrv, send2, state, skill=394)           # QUEUED behind it
        sent2.clear()
        authsrv.cancel_on_move(send2, state, 0)
        marked = [c.get("cancelled") for c in state["pending_casts"]]
        check(marked == ["movement", "movement"],
              "the activating spell AND the queued attack skill are both "
              "dropped -- queued means its begin never came, so its type "
              "never protected it", f"marked={marked}")
        authsrv.cast_tick(send2, state, 0)
        e2s = [v for op, v, _ in sent2
               if op == authsrv.GAME_SMSG_SKILL_REFUSED]
        check(e2s == [[PLAYER, 105, 7], [PLAYER, 394, 7]]
              and not state["pending_casts"],
              "two releases, no recharge for either",
              f"e2s={e2s}, pending={state['pending_casts']}")
    finally:
        authsrv.skill_timing = saved_t
        authsrv._is_attack_skill = saved_a


def section_clean_restart():
    import authsrv

    print("\n4. a press after a cancel schedules from NOW, not from the "
          "cancelled cast's ghost")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}}
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (2.0, 0.75, 8.0)
    try:
        _press(authsrv, send, state, skill=105)
        authsrv.cancel_on_move(send, state, 0)
        now = time.time()
        _press(authsrv, send, state, skill=153)
        fresh = state["pending_casts"][-1]
        check(abs((fresh["e5_at"] - now) - 2.0) < 0.05,
              "the new cast's E5 sits one activation out -- the queue law "
              "measures from a busy window the cancel rolled back",
              f"e5 in {fresh['e5_at'] - now:.3f}s against activation 2.0")
    finally:
        authsrv.skill_timing = saved


def section_chain_half():
    import authsrv

    print("\n5. the chain half: LAW A is the default again, COMPOSED with "
          "the chain pause; --legacy-move-stops-chain reverts both")
    check(authsrv.MOVE_KEEPS_CHAIN is True
          and authsrv.CHAIN_PAUSES_WHILE_MOVING is True,
          "LAW A and the chain pause are BOTH the default, as one arm. LAW "
          "A alone shipped on 2026-09-01 and came back the same day (the "
          "operator scored it 'very floaty'); ANIMREF-RE 31 found the half "
          "that was missing and it was never a movement gate at all -- the "
          "client refuses a walk cycle by ANIMATION PRIORITY while an "
          "attack animation is latched (table 0x00A92ED8, locomotion 0x0040 "
          "against 0x0110/0x0120), and retail sends no pose-ender: it "
          "stretches the chain so the animation finishes. They are "
          "meaningless apart -- with the chain closed on every move there "
          "is no chain to pace -- so they revert together, one flag, which "
          "is the ANIMREF-RE 29 lesson wired in",
          f"lawA={authsrv.MOVE_KEEPS_CHAIN}, "
          f"pause={authsrv.CHAIN_PAUSES_WHILE_MOVING}")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    agent = {"name": "target", "dead": False, "last_hit": 0.0,
             "max_health": 100.0, "health": 100.0, "pos": (0.0, 0.0)}
    state = {"agents": {10: agent}, "pos": (0.0, 0.0)}
    authsrv.begin_attack(send, state, 10, 0)
    authsrv.attack_tick(send, state, 0)                    # arm the swing
    # PAST THE LANDING before moving -- this section's claim is about the
    # chain SURVIVING a move, and since ANIMREF-RE 32 that is regime 2's
    # property, not a blanket one. A move inside the windup is regime 1 and
    # cancels by design; §7 owns both regimes and pins the split itself.
    state["player_swing"]["lands_at"] -= 5.0
    sent.clear()
    authsrv.cancel_on_move(send, state, 0)
    stops = [v for op, v, _ in sent
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
             and v[0] == authsrv.agents.GV_ATTACK_STOPPED]
    holds = [v for op, v, _ in sent
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
             and v[0] == authsrv.agents.GV_DISABLED]
    check(stops == [] and state.get("attacking") is None
          and state.get("player_swing") is not None
          and not state.get("player_swing_cancel"),
          "default door: NO property 3 and the armed swing survives the "
          "move (325 of 343 corpus mid-chain moves carry no property 3), "
          "but since ANIMREF-RE 39 the TARGET is forgotten: a move command "
          "ends the auto-attack -- retail's player re-presses after every "
          "mid-chain move (28 of 28 pairs; 39 chains end at a move with no "
          "press; 0 resume). The absence of a close was never survival",
          f"stops={stops}, attacking={state.get('attacking')}, "
          f"swing={state.get('player_swing') is not None}")
    # NOTHING TO RELEASE since ANIMREF-RE 35: an auto swing no longer sets
    # the hold at all (retail 83 of 1,332 attack starts = 6.2%, ours was
    # 52 of 52), and `action_hold` is transition-only. The DOOR is unchanged
    # -- it still calls action_hold(0) on every move, and still emits when a
    # CAST set the flag, which is the case castmech 3c actually witnessed.
    # What changed is what reaches it. Both arms of the flag agree here,
    # which is why this check is not part of the revert either way.
    check(holds == [],
          "and no hold release rides the move -- the auto swing never set "
          "one. A cast still does, and this same door still releases that",
          f"holds={holds}")
    state["attacking"] = None
    state["player_swing"] = None
    state["player_swing_cancel"] = None
    state["action_hold"] = 0

    # THE REVERT ARM, both halves off together -- the pre-ANIMREF-RE-31
    # door. It has to keep WORKING, because it is the operator's one-flag
    # way back and because the next A/B is scored against it.
    authsrv.MOVE_KEEPS_CHAIN = False
    authsrv.CHAIN_PAUSES_WHILE_MOVING = False
    try:
        authsrv.begin_attack(send, state, 10, 0)
        authsrv.attack_tick(send, state, 0)                # re-arm
        sent.clear()
        authsrv.cancel_on_move(send, state, 0)
        stops = [v for op, v, _ in sent
                 if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                 and v[0] == authsrv.agents.GV_ATTACK_STOPPED]
        check(stops == [[authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0]]
              and state.get("attacking") is None,
              "--legacy-move-stops-chain: one STOPPED and the target is "
              "forgotten. That property 3 is an APPEND to the client's "
              "AvChar animation queue (0x007DFA60 -> 0x007F6C00 -> "
              "0x007F2E90, spliced at [AvChar+0xC4]/[+0xC8]), so what this "
              "arm really does is cancel the attack ANIMATION on every "
              "move -- the operator's 'cancelling the animation instead of "
              "sliding while the animation plays'",
              f"stops={stops}, attacking={state.get('attacking')}")
        sent.clear()
        authsrv.attack_tick(send, state, 0)
        check(state.get("player_swing") is None and sent == []
              and agent["health"] == 100.0,
              "and its armed swing is dropped unlanded",
              f"swing={state.get('player_swing')}, health={agent['health']}")
    finally:
        authsrv.MOVE_KEEPS_CHAIN = True
        authsrv.CHAIN_PAUSES_WHILE_MOVING = True
        state["attacking"] = None
        state["player_swing"] = None
        state["player_swing_cancel"] = None
        state["action_hold"] = 0

    # The negative: a chain already paused by a cast gets no second close.
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (2.0, 0.75, 8.0)
    try:
        authsrv.begin_attack(send, state, 10, 0)
        _press(authsrv, send, state)                       # pauses the chain
        sent.clear()
        authsrv.cancel_on_move(send, state, 0)
        stops = [v for op, v, _ in sent
                 if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                 and v[0] == authsrv.agents.GV_ATTACK_STOPPED]
        check(stops == [] and state["pending_casts"][-1].get("cancelled"),
              "moving during the cast cancels the CAST but sends no second "
              "STOPPED -- the press already closed the chain, the same "
              "negative the press path measured (necro press 2, t=9.85)",
              f"stops={stops}")
    finally:
        authsrv.skill_timing = saved


def section_landing_split():
    """ANIMREF-RE 32: the TWO REGIMES, split by the landing instant.

    OPERATOR, 2026-09-01, on stock Guild Wars, verbatim:

      1. start attacking -> move BEFORE the attack lands (or the projectile
         launches) -> the attack animation STOPS and normal movement resumes.
      2. start attacking -> WAIT for the landing -> then move -> the animation
         PLAYS TO COMPLETION while the body slides.

    Every previous version of this door had ONE rule and was therefore wrong in
    one of the two regimes: the legacy door cancelled always (their "cancelling
    the animation instead of sliding"), LAW A cancelled never (their "the legs
    don't move, the attack animation completes"). This section pins BOTH
    regimes, so neither can be fixed by breaking the other.

    The discriminator is `player_swing["lands_at"]`, which this server already
    stamps a `swing_windup(interval)` after the START -- no new state.
    """
    import authsrv
    import time as _t

    print("\n7. ANIMREF-RE 32: the landing splits movement into two regimes")

    def move_at(offset_from_start):
        """Open a swing, jump the clock `offset` seconds in, then move."""
        sent = []
        send = lambda op, vals, label="", quiet=False: \
            sent.append((op, vals, label))
        agent = {"name": "t", "dead": False, "last_hit": 0.0,
                 "max_health": 100.0, "health": 100.0, "pos": (0.0, 0.0)}
        state = {"agents": {10: agent}, "pos": (0.0, 0.0)}
        authsrv.begin_attack(send, state, 10, 0)
        authsrv.attack_tick(send, state, 0)              # START, arms the swing
        # Move the swing's landing into the past or future by rewinding it.
        sw = state["player_swing"]
        windup = sw["lands_at"] - _t.time()
        sw["lands_at"] -= offset_from_start
        state["player_last_swing"] -= offset_from_start
        sent.clear()
        authsrv.cancel_on_move(send, state, 0)
        stops = [v for op, v, _l in sent
                 if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                 and v[0] == authsrv.agents.GV_ATTACK_STOPPED]
        return stops, state, windup

    # REGIME 1 -- the move lands INSIDE the windup. offset 0 means no time has
    # passed since the START, so the landing is still ahead.
    stops, st1, windup = move_at(0.0)
    check(windup > 0.05,
          "the rig has a real windup to sit inside -- not a degenerate zero",
          f"windup {windup:.3f}s")
    check(stops == [[authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0]],
          "REGIME 1 (move BEFORE the landing): property 3 goes out -- the "
          "attack animation STOPS and normal movement resumes, which is what "
          "the operator described on stock. LAW A alone got this wrong: it "
          "cancelled never, and they reported 'the legs don't move, the "
          "attack animation completes'",
          f"stops={stops}")
    check(st1.get("attacking") is None
          and st1.get("player_swing_cancel") == "movement",
          "and a cancel is a real close -- the target is forgotten and the "
          "armed swing is dropped, exactly as the legacy door always did. The "
          "18 of 343 corpus mid-chain moves that DO carry property 3 are "
          "these",
          f"attacking={st1.get('attacking')}, "
          f"cancel={st1.get('player_swing_cancel')}")

    # REGIME 2 -- the move lands AFTER the strike. Rewinding past the windup
    # puts `lands_at` in the past.
    stops2, st2, _w = move_at(windup + 0.05)
    check(stops2 == [],
          "REGIME 2 (move AFTER the landing): NO property 3 -- the animation "
          "plays to completion while the body slides. That is the "
          "quarterstep, and the legacy door broke it by cancelling here",
          f"stops={stops2}")
    check(st2.get("attacking") is None
          and not st2.get("player_swing_cancel"),
          "and the swing LANDS but the chain ENDS (ANIMREF-RE 39): the "
          "target is forgotten without a close, and the next swing needs a "
          "press -- retail's player re-presses after every mid-chain move "
          "(28 of 28 on the live tapes), which is the operator's 'once you "
          "issue a move command you stop autoattacking'",
          f"attacking={st2.get('attacking')}, "
          f"cancel={st2.get('player_swing_cancel')}")

    # THE SPLIT MUST BE THE LANDING, not the flag: with LAW A off the legacy
    # door cancels in BOTH regimes, which is the known-bad arm for regime 2.
    authsrv.MOVE_KEEPS_CHAIN = False
    authsrv.CHAIN_PAUSES_WHILE_MOVING = False
    try:
        stops3, _st3, w3 = move_at(0.0)
        stops4, _st4, _w4 = move_at(w3 + 0.05)
        check(stops3 and stops4,
              "KNOWN-BAD ARM (--legacy-move-stops-chain): property 3 in BOTH "
              "regimes -- correct in regime 1 and wrong in regime 2, the "
              "single-rule door this section replaces. A test that could not "
              "tell the two arms apart would not be measuring the split",
              f"regime1={stops3}, regime2={stops4}")
    finally:
        authsrv.MOVE_KEEPS_CHAIN = True
        authsrv.CHAIN_PAUSES_WHILE_MOVING = True

    # AND THE CAST HALF ALREADY DOES THIS, which is the internal corroboration
    # the wire evidence leans on: E5 is the cast's landing, and §2 above pins
    # that a completed activation is not marked. Restated here as an explicit
    # cross-check rather than left implicit two sections away.
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 8.0)
    try:
        sentc = []
        sendc = lambda op, vals, label="", quiet=False: \
            sentc.append((op, vals, label))
        statec = {"agents": {}}
        _press(authsrv, sendc, statec)
        pre = authsrv._mark_cancelled(statec, "movement", _t.time(),
                                      spare_mid_attack=False)
        statec2 = {"agents": {}}
        _press(authsrv, sendc, statec2)
        statec2["pending_casts"][0]["e5_sent"] = True      # past its landing
        post = authsrv._mark_cancelled(statec2, "movement", _t.time(),
                                       spare_mid_attack=False)
        check(pre == 1 and post == 0,
              "CROSS-CHECK: the CAST path splits on its own landing (E5) the "
              "same way -- a cast short of E5 is cancelled by a move, one "
              "past it is aftercast and untouched. The swing path was the "
              "only one still all-or-nothing; this section closes that",
              f"pre-landing marked {pre}, post-landing marked {post}")
    finally:
        authsrv.skill_timing = saved


def section_cancel_action_door():
    import authsrv

    print("\n6. the 0x0028 door: the one that reaches a held cast")
    # The run that forced this arm: 20260823T101329, where the operator's
    # three cancel inputs during the one 2.0 s cast each arrived as a
    # header-only 0x0028 and NO movement c2s at all -- so cancel_on_move,
    # wired to the movement arms, could never fire and checklist item 1
    # failed on screen. The client asks through THIS opcode while casting.
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}}
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (2.0, 0.75, 8.0)
    try:
        _press(authsrv, send, state)
        sent.clear()
        authsrv.cancel_action(send, state, 0)
        check(state["pending_casts"][0].get("cancelled") == "cancel action"
              and [(op, v) for op, v, _ in sent] ==
              [(authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                [authsrv.agents.GV_DISABLED, PLAYER, 0]),
               (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                [authsrv.agents.GV_SKILL_STOPPED, PLAYER, 0]),
               (authsrv.GAME_SMSG_SKILL_REFUSED, [PLAYER, 42, 7])],
              "Esc gets the SAME burst as movement -- [8 -> 0, 59, E2] -- "
              "which the capture shows too: its Esc cancel (t=88.946) is "
              "byte-identical to the W one bar the movement grant",
              f"cancelled={state['pending_casts'][0].get('cancelled')}, "
              f"sent={[(hex(o), v) for o, v, _ in sent]}")
        n = len(sent)
        authsrv.cast_tick(send, state, 0)
        check(len(sent) == n and not state["pending_casts"],
              "and the tick only removes the entry -- no second E2",
              f"{[(hex(o), v) for o, v, _ in sent[n:]]}")
    finally:
        authsrv.skill_timing = saved

    # Esc reaches the mid-activation attack skill that movement spares:
    # the client withholds the request for skills that resist it, so a
    # request that arrived is granted whatever the type.
    sent = []
    state = {"agents": {}}
    saved_t, saved_a = authsrv.skill_timing, authsrv._is_attack_skill
    authsrv.skill_timing = lambda sid: (1.0, 0.0, 3.0)
    authsrv._is_attack_skill = lambda sid: True
    try:
        _press(authsrv, send, state, skill=394)
        authsrv.cancel_action(send, state, 0)
        check(state["pending_casts"][0].get("cancelled") == "cancel action",
              "an attack skill mid-activation IS cancelled through this "
              "door -- section 3's movement exemption is the wiki's rule "
              "about movement, not about Esc",
              f"{state['pending_casts'][0].get('cancelled')}")
    finally:
        authsrv.skill_timing, authsrv._is_attack_skill = saved_t, saved_a

    # An aftercast stays uncancellable through EVERY door, and its hold
    # keeps riding: past the E5 nothing is marked and nothing is sent.
    sent = []
    state = {"agents": {}}
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 8.0)
    try:
        _press(authsrv, send, state)
        _rewind(state, 1.0)
        authsrv.cast_tick(send, state, 0)                  # E5: aftercast now
        sent.clear()
        authsrv.cancel_action(send, state, 0)
        check(sent == [] and not state["pending_casts"][0].get("cancelled"),
              "cancel-action during the aftercast: nothing marked, nothing "
              "sent -- the hold is the aftercast's own and keeps riding",
              f"sent={[(hex(o), v) for o, v, _ in sent]}")
    finally:
        authsrv.skill_timing = saved

    # And the chain half: Esc closes a live chain with the measured pair
    # and forgets the attack order.
    sent = []
    agent = {"name": "target", "dead": False, "last_hit": 0.0,
             "max_health": 100.0, "health": 100.0, "pos": (0.0, 0.0)}
    state = {"agents": {10: agent}, "pos": (0.0, 0.0)}
    authsrv.begin_attack(send, state, 10, 0)
    authsrv.attack_tick(send, state, 0)                    # arm the swing
    sent.clear()
    authsrv.cancel_action(send, state, 0)
    pair = [(op, v) for op, v, _ in sent]
    # THE ORDER IS STILL THE POINT and it is still pinned -- what changed
    # is that the second half only exists when something SET the hold. An
    # auto swing no longer does (ANIMREF-RE 35), so a chain closed by Esc
    # sends the [3] alone. The corpus instants this cites (Esc t=119.425, W
    # t=114.641) were both mid-WINDUP with a hold already riding, and the
    # measurement was of the ORDER between the two, not of a rate at which
    # the pair occurs -- the same distinction the 4-of-4 hold census turned
    # on. When a cast holds, this door still emits both, in this order.
    expect_stop = (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                   [authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0])
    check(pair == [expect_stop]
          and state.get("attacking") is None
          and state.get("player_swing_cancel") == "cancel action",
          "a live chain closes with the STOP -- and with no [8 -> 0] behind "
          "it, because an auto swing no longer sets the hold to release. "
          "The ORDER measured at this door ([3] then [8 -> 0], Esc "
          "t=119.425 and W t=114.641, 2 of 2) is unchanged and still "
          "applies whenever a cast is what holds. And the attack order is "
          "forgotten: Esc means stop",
          f"{[(hex(o), v) for o, v in pair]}, "
          f"attacking={state.get('attacking')}")

    # AND THE ORDER ITSELF, on the case that still produces both halves: set
    # the hold the way a cast would, then close the chain. This keeps the
    # corpus fact under test rather than deleting it with the swing hold.
    state["attacking"] = 10
    state["player_swing"] = {"target": 10, "lands_at": time.time() + 9.0}
    state["player_swing_cancel"] = None
    state["action_hold"] = 1
    sent.clear()
    authsrv.cancel_action(send, state, 0)
    pair2 = [(op, v) for op, v, _ in sent]
    check(pair2 == [expect_stop,
                    (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                     [authsrv.agents.GV_DISABLED, PLAYER, 0])],
          "with a hold riding (as a cast leaves), the door emits BOTH in "
          "the measured order -- [3] then [8 -> 0]. The corpus fact "
          "survives ANIMREF-RE 35; only its trigger narrowed",
          f"{[(hex(o), v) for o, v in pair2]}")


def main():
    section_move_cancels()
    section_aftercast_uncancellable()
    section_attack_skills()
    section_clean_restart()
    section_chain_half()
    section_landing_split()
    section_cancel_action_door()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
