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
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402

# FLOOR 20, from the green run of 2026-08-23 that landed section 6 (the
# 0x0028 door; 15 when the file carried the movement door alone).
LEDGER = checks.Ledger("cast cancel", floor=20)
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

    print("\n5. the chain half: moving closes a live chain once and "
          "forgets the target")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    agent = {"name": "target", "dead": False, "last_hit": 0.0,
             "max_health": 100.0, "health": 100.0, "pos": (0.0, 0.0)}
    state = {"agents": {10: agent}, "pos": (0.0, 0.0)}
    authsrv.begin_attack(send, state, 10, 0)
    authsrv.attack_tick(send, state, 0)                    # arm the swing
    sent.clear()
    authsrv.cancel_on_move(send, state, 0)
    stops = [v for op, v, _ in sent
             if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
             and v[0] == authsrv.agents.GV_ATTACK_STOPPED]
    check(stops == [[authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0]]
          and state.get("attacking") is None,
          "one STOPPED, and the target is forgotten -- a move REPLACES the "
          "attack order (WIKI, Auto attack); re-clicking is what restarts "
          "it, and 0x0026 is on the wire for exactly that",
          f"stops={stops}, attacking={state.get('attacking')}")
    sent.clear()
    authsrv.attack_tick(send, state, 0)
    check(state.get("player_swing") is None and sent == []
          and agent["health"] == 100.0,
          "the armed swing is dropped unlanded",
          f"swing={state.get('player_swing')}, health={agent['health']}")

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
    check(pair == [(authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                    [authsrv.agents.GV_ATTACK_STOPPED, PLAYER, 0]),
                   (authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                    [authsrv.agents.GV_DISABLED, PLAYER, 0])]
          and state.get("attacking") is None
          and state.get("player_swing_cancel") == "cancel action",
          "a live chain closes with the stop pair in the order measured at "
          "THIS door -- [3] then [8 -> 0], the live Esc mid-windup "
          "(t=119.425) and W mid-windup (t=114.641), 2 of 2. The press and "
          "retarget bursts keep their own opposite order; neither is tidied "
          "to match. And the attack order is forgotten: Esc means stop",
          f"{[(hex(o), v) for o, v in pair]}, "
          f"attacking={state.get('attacking')}")


def main():
    section_move_cancels()
    section_aftercast_uncancellable()
    section_attack_skills()
    section_clean_restart()
    section_chain_half()
    section_cancel_action_door()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
