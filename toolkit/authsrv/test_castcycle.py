"""The four-opcode cast cycle: E4 now, E5 at cast end, E3 an aftercast later,
E6 when the recharge runs out.

The template is ArenaNet's, not ours: six complete cycles across the two live
captures, same order every time, E6 - E5 equal to the recharge field within
13.7 ms on all six (studies/combat/PLAN.md section 6). What this file checks
is that our server reproduces that template's SHAPE and its timing LAW --
including the queue law, which is the one part that took measurement to see:
E4 fires when the press is accepted, but the cast BEGINS when the caster
frees, so a press during another cast's aftercast schedules from the
aftercast's end, not from the press (skill 105's two cycles both exceed its
2.0 s activation by exactly the previous cast's remaining aftercast).

Timing here is tested by REWINDING THE SCHEDULE, not by sleeping: the
entries' due-times are shifted into the past and cast_tick is asked what is
due. A test that sleeps 8 seconds per cycle measures the wall clock, not the
scheduler.

Sections 1-3 and 5 stub `skill_timing`, so they run on a bare machine.
Section 4 reads the real content rows (vault overlay) and SKIPS, loudly,
when no vault is present -- the values it pins are the live-corroborated
trio for skill 153.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402

LEDGER = checks.Ledger("cast cycle", floor=16)
check = LEDGER.ok

PLAYER = 1   # authsrv.PLAYER_AGENT_ID, restated so a drift reddens something


def _press(authsrv, send, state, skill=42, copy=7, target=0):
    authsrv.handle_skill_press([0, skill, copy, target], send, state, 0,
                               authsrv.GAME_CMSG_USE_SKILL)


def _rewind(state, seconds):
    """Move every pending phase due-time into the past by `seconds`."""
    for cast in state.get("pending_casts", ()):
        for k in ("e5_at", "e3_at", "e6_at"):
            cast[k] -= seconds


def section_press_shape():
    import authsrv

    print("1. the press: E4 + the observed cast-animation shape, and a queue "
          "entry")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}}

    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 8.0)
    try:
        _press(authsrv, send, state)
        ops = [op for op, _, _ in sent]
        # 0x00A2 IS THE ENERGY DEBIT, wired 2026-08-20 -- skill 42 costs 10 and
        # the corpus puts property 62 inside 0.03-0.7 s of the USE_SKILL, so it
        # rides the press burst rather than the tick. Still an exact op list,
        # and it still says what this section is about: none of E5/E3/E6 and no
        # damage leaves at the press. test_pools sections 6-6c own the debit.
        check(ops == [0x00E4, 0x00A2, 0x00A0],
              "the press sends E4, the energy debit, then the 0x00A0 "
              "[60, caster, target, skill] animation -- retail's own batch "
              "order, spend before the property that names the skill "
              "(45 of 45, test_pools section 2c) -- and nothing else yet",
              f"ops={[hex(o) for o in ops]} -- E5/E3/E6 belong to the tick; "
              f"the old immediate 0x00E3 is gone from the press")
        # sent[2], not [1]: the debit now sits between E4 and the animation
        check(sent[2][1] == [authsrv.agents.GV_SKILL_ACTIVATED, PLAYER, 0, 42],
              "the animation carries the OBSERVED player shape (4/4 in the "
              "live corpus); GV 58 belongs to the cast END, not the press "
              "-- section 2 pins it riding the E5 (castmech 3c)",
              f"vals={sent[1][1]}")
        casts = state["pending_casts"]
        c = casts[0]
        check(len(casts) == 1
              and abs((c["e3_at"] - c["e5_at"]) - 0.75) < 1e-9
              and abs((c["e6_at"] - c["e5_at"]) - 8.0) < 1e-9
              and c["recharge"] == 8,
              "one entry, scheduled by the law: E3 at E5+aftercast, E6 at "
              "E5+recharge",
              f"{ {k: round(v - c['e5_at'], 3) for k, v in c.items() if k.endswith('_at')} }")
    finally:
        authsrv.skill_timing = saved


def section_tick_order():
    import authsrv

    print("\n2. the tick fires E5 -> E3 -> E6, each exactly once, in order")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}}
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 8.0)
    try:
        _press(authsrv, send, state)
        sent.clear()

        authsrv.cast_tick(send, state, 0)
        check(sent == [], "nothing is due at press time")

        _rewind(state, 1.0)                      # activation over
        authsrv.cast_tick(send, state, 0)
        check([op for op, _, _ in sent] == [0x00E5, 0x009F]
              and sent[0][1] == [PLAYER, 42, 7, 8],
              "E5 fires at cast end carrying [agent, skill, copy, recharge "
              "seconds]", f"{sent}")
        check(sent[1][1] == [authsrv.agents.GV_SKILL_FINISHED, PLAYER, 0],
              "and [58, agent, 0] rides the very next slot -- the corpus "
              "position, 5 of 5, four of them right behind the "
              "necromancer's spell E5s (castmech 3c)", f"{sent[1]}")

        _rewind(state, 0.75)                     # aftercast over
        authsrv.cast_tick(send, state, 0)
        check([op for op, _, _ in sent] == [0x00E5, 0x009F, 0x00E3]
              and sent[2][1] == [PLAYER, 42, 7],
              "E3 fires an aftercast later, echoing the pending key",
              f"{sent[2:]}")

        _rewind(state, 7.25)                     # recharge over
        authsrv.cast_tick(send, state, 0)
        check([op for op, _, _ in sent] == [0x00E5, 0x009F, 0x00E3, 0x00E6]
              and not state["pending_casts"],
              "E6 closes the cycle at E5+recharge and the entry is gone",
              f"{sent[3:]}")

        authsrv.cast_tick(send, state, 0)
        check(len(sent) == 4, "and a further tick fires NOTHING -- each "
              "phase is once per cycle", f"{len(sent)} sends total")
    finally:
        authsrv.skill_timing = saved


def section_attack_family():
    import authsrv

    print("\n2b. the ATTACK family: property 50 at the press, silence at "
          "the cast end")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}}
    saved = authsrv.skill_timing
    saved_attack = authsrv._is_attack_skill
    authsrv.skill_timing = lambda sid: (1.0, 0.0, 3.0)
    # Stubbed rather than read from content: on a bare machine every id is
    # "not attack" (no rows), so the family split is pinned by forcing it.
    authsrv._is_attack_skill = lambda sid: True
    try:
        _press(authsrv, send, state, skill=394)
        check([op for op, _, _ in sent] == [0x00E4, 0x00A2, 0x00A0]
              and sent[2][1] == [authsrv.agents.GV_ATTACK_SKILL_ACTIVATED,
                                 PLAYER, 0, 394],
              "the burst keeps its shape and the animation carries 50 "
              "(CastAttackSkill) -- both live Power Shot presses, and all "
              "39 adrenal 0x00D2s ride into a property-50, never a 60 "
              "(castmech 3b/3c)",
              f"{[(hex(op), vals) for op, vals, _ in sent]}")
        sent.clear()
        _rewind(state, 1.0)
        authsrv.cast_tick(send, state, 0)
        fifty_eight = [vals for op, vals, _ in sent
                       if op == 0x009F
                       and vals[0] == authsrv.agents.GV_SKILL_FINISHED]
        check([op for op, _, _ in sent][0] == 0x00E5 and not fifty_eight,
              "the E5 fires and NO [58, agent, 0] follows -- the ranger's "
              "two Power Shot E5s carry neither 58 nor 46, 0 of 2, so the "
              "spell family's property is not borrowed (castmech 3c)",
              f"{[(hex(op), vals) for op, vals, _ in sent]}")
    finally:
        authsrv.skill_timing = saved
        authsrv._is_attack_skill = saved_attack


def section_order_pinned_when_inverted():
    import authsrv

    print("\n3. a zero-recharge skill still closes E5 -> E3 -> E6, never "
          "E6 before E3")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}}
    saved = authsrv.skill_timing
    # recharge 0 < aftercast 0.75: e6_at lands BEFORE e3_at. The corpus never
    # shows E6 preceding E3, so the tick must hold E6 for its E3.
    authsrv.skill_timing = lambda sid: (0.0, 0.75, 0.0)
    try:
        _press(authsrv, send, state)
        sent.clear()
        _rewind(state, 0.5)   # e5 and e6 both past due; e3 not yet
        authsrv.cast_tick(send, state, 0)
        check([op for op, _, _ in sent] == [0x00E5, 0x009F],
              "E6 is due but WAITS: the observed order outranks the clock",
              f"{[hex(op) for op, _, _ in sent]}")
        _rewind(state, 0.5)
        authsrv.cast_tick(send, state, 0)
        check([op for op, _, _ in sent] == [0x00E5, 0x009F, 0x00E3, 0x00E6],
              "then E3 and E6 land together on the next tick, in order",
              f"{[hex(op) for op, _, _ in sent]}")
    finally:
        authsrv.skill_timing = saved


def section_queue_law():
    import authsrv

    print("\n4. the queue law: a press during an aftercast schedules from "
          "the aftercast's end")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}}
    saved = authsrv.skill_timing
    authsrv.skill_timing = lambda sid: (2.0, 0.75, 6.0)
    try:
        _press(authsrv, send, state, skill=105)
        first = state["pending_casts"][0]
        _press(authsrv, send, state, skill=105)
        second = state["pending_casts"][1]
        gap = second["e5_at"] - first["e5_at"]
        check(abs(gap - (0.75 + 2.0)) < 0.05,
              "the second cast's E5 lands aftercast + activation after the "
              "first's -- skill 105's own two live cycles, generalized",
              f"gap={gap:.3f}s (the naive press+activation model is refuted "
              f"by +0.64s and +0.57s residuals in the corpus)")
    finally:
        authsrv.skill_timing = saved


def section_real_content():
    import authsrv

    print("\n5. the real numbers: skill 153 from the content store")
    try:
        authsrv.agents.WORLD.get("skills", "153")
    except Exception:
        LEDGER.skip("no 'skills' content rows -- vault overlay absent on "
                    "this machine; run skilltable.py --emit-content. The "
                    "values this section pins are checked in "
                    "test_skilltable.py section 6 wherever the vault exists.")
        return
    act, aft, rech = authsrv.skill_timing(153)
    check((act, aft, rech) == (1.0, 0.75, 8.0),
          "skill 153 times the cycle with the live-corroborated trio "
          "(1.0, 0.75, 8)", f"got ({act}, {aft}, {rech})")
    sent = []
    send = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    state = {"agents": {}}
    _press(authsrv, send, state, skill=153, copy=0)
    _rewind(state, 20.0)
    authsrv.cast_tick(send, state, 0)
    e5 = [vals for op, vals, _ in sent if op == 0x00E5]
    check(e5 == [[PLAYER, 153, 0, 8]],
          "and E5 carries recharge 8 -- the value ArenaNet's own wire echoed "
          "for this skill", f"{e5}")


def main():
    section_press_shape()
    section_tick_order()
    section_attack_family()
    section_order_pinned_when_inverted()
    section_queue_law()
    section_real_content()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
