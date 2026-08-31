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
import time as _time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402

LEDGER = checks.Ledger("cast cycle", floor=20)
check = LEDGER.ok

PLAYER = 1   # authsrv.PLAYER_AGENT_ID, restated so a drift reddens something


def _press(authsrv, send, state, skill=42, copy=7, target=0):
    authsrv.handle_skill_press([0, skill, copy, target], send, state, 0,
                               authsrv.GAME_CMSG_USE_SKILL)


def _rewind(state, seconds):
    """Move every pending phase due-time into the past by `seconds`."""
    for cast in state.get("pending_casts", ()):
        for k in ("begin_at", "e5_at", "e3_at", "e6_at"):
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
        _press(authsrv, send, state, target=40)
        ops = [op for op, _, _ in sent]
        # 0x00A2 IS THE ENERGY DEBIT, wired 2026-08-20 -- skill 42 costs 10 and
        # the corpus puts property 62 inside 0.03-0.7 s of the USE_SKILL, so it
        # rides the press burst rather than the tick. Still an exact op list,
        # and it still says what this section is about: none of E5/E3/E6 and no
        # damage leaves at the press. test_pools sections 6-6c own the debit.
        check(ops == [0x00E4, 0x00A2, 0x00A0, 0x009F]
              and sent[3][1] == [authsrv.agents.GV_DISABLED, PLAYER, 1],
              "the press sends E4, the energy debit, the 0x00A0 "
              "[60, caster, target, skill] animation, then [8 -> 1] closing "
              "the burst -- retail's own batch order, spend before the "
              "property that names the skill (45 of 45, test_pools 2c), "
              "hold last (3 of 3 bursts, castmech 3c). NO [8 -> 0] opens "
              "it here: the flag was still 0, the ranger's t=12.9508 "
              "elision -- and nothing else yet",
              f"ops={[hex(o) for o in ops]} -- E5/E3/E6 belong to the tick; "
              f"the old immediate 0x00E3 is gone from the press")
        # sent[2], not [1]: the debit now sits between E4 and the animation.
        # Target 40, not 0: every one of the 4/4 live opens named its real
        # target, and 0x00A0-with-target-0 is a form retail uses ZERO times
        # in 758 corpus opens (ANIMREF-R1 sec.2).
        check(sent[2][1] == [authsrv.agents.GV_SKILL_ACTIVATED, PLAYER, 40, 42],
              "the animation carries the OBSERVED player shape (4/4 in the "
              "live corpus); GV 58 belongs to the cast END, not the press "
              "-- section 2 pins it riding the E5 (castmech 3c)",
              f"vals={sent[2][1]}")
        # And the FORM RULE's other half: a press that names no target rides
        # the untargeted 0x009F channel (531/531 untargeted retail opens) --
        # the channel follows the target, never a zero in the target slot.
        sent2 = []
        send2 = lambda op, vals, label="", quiet=False: \
            sent2.append((op, vals, label))
        state2 = {"agents": {}}
        _press(authsrv, send2, state2)
        anim2 = [(op, vals) for op, vals, _ in sent2
                 if vals and vals[0] == authsrv.agents.GV_SKILL_ACTIVATED]
        check(anim2 == [(authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                         [authsrv.agents.GV_SKILL_ACTIVATED, PLAYER, 42])],
              "a targetless press rides 0x009F [60, caster, skill] -- "
              "retail's untargeted form, never 0x00A0 with an empty slot",
              f"{[(hex(op), vals) for op, vals in anim2]}")
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
        check([op for op, _, _ in sent] == [0x00E5, 0x009F, 0x009F, 0x009F]
              and sent[0][1] == [PLAYER, 42, 7, 8],
              "E5 fires at cast end carrying [agent, skill, copy, recharge "
              "seconds]", f"{sent}")
        check(sent[1][1] == [authsrv.agents.GV_SKILL_FINISHED, PLAYER, 0],
              "and [58, agent, 0] rides the very next slot -- the corpus "
              "position, 5 of 5, four of them right behind the "
              "necromancer's spell E5s (castmech 3c)", f"{sent[1]}")
        check([v[1] for v in (sent[2][1], sent[3][1])] == [PLAYER, PLAYER]
              and (sent[2][1][0], sent[2][1][2]) == (8, 0)
              and (sent[3][1][0], sent[3][1][2]) == (8, 1),
              "and the hold pulse closes the instant: [8 -> 0] then "
              "[8 -> 1], the cast releasing and the aftercast taking hold "
              "-- 4 of 4 spell E5s, always at the batch's end "
              "(castmech 3c)", f"{sent[2:]}")

        _rewind(state, 0.75)                     # aftercast over
        authsrv.cast_tick(send, state, 0)
        check([op for op, _, _ in sent] ==
              [0x00E5, 0x009F, 0x009F, 0x009F, 0x00E3]
              and sent[4][1] == [PLAYER, 42, 7],
              "E3 fires an aftercast later, echoing the pending key -- and "
              "carries NO hold release: the corpus's E3 instants never "
              "toggle property 8 (the flag rides until something else "
              "frees it)", f"{sent[4:]}")

        _rewind(state, 7.25)                     # recharge over
        authsrv.cast_tick(send, state, 0)
        check([op for op, _, _ in sent] ==
              [0x00E5, 0x009F, 0x009F, 0x009F, 0x00E3, 0x00E6]
              and not state["pending_casts"],
              "E6 closes the cycle at E5+recharge and the entry is gone",
              f"{sent[5:]}")

        authsrv.cast_tick(send, state, 0)
        check(len(sent) == 6, "and a further tick fires NOTHING -- each "
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
        _press(authsrv, send, state, skill=394, target=40)
        check([op for op, _, _ in sent] == [0x00E4, 0x00A2, 0x00A0, 0x009F]
              and sent[2][1] == [authsrv.agents.GV_ATTACK_SKILL_ACTIVATED,
                                 PLAYER, 40, 394],
              "the burst keeps its shape (the [8 -> 1] hold closes it, as "
              "every family's does) and the animation carries 50 "
              "(CastAttackSkill) -- both live Power Shot presses, and all "
              "39 adrenal 0x00D2s ride into a property-50, never a 60 "
              "(castmech 3b/3c)",
              f"{[(hex(op), vals) for op, vals, _ in sent]}")
        sent.clear()
        _rewind(state, 1.0)
        authsrv.cast_tick(send, state, 0)
        borrowed = [vals for op, vals, _ in sent
                    if op == 0x009F
                    and vals[0] in (authsrv.agents.GV_SKILL_FINISHED,
                                    authsrv.agents.GV_DISABLED)]
        check([op for op, _, _ in sent][0] == 0x00E5 and not borrowed,
              "the E5 fires with NO [58, agent, 0] and NO hold pulse -- "
              "the ranger's two Power Shot E5s carry neither 58 nor 46 "
              "nor property 8, 0 of 2 each, so nothing of the spell "
              "family's cast end is borrowed (castmech 3c)",
              f"{[(hex(op), vals) for op, vals, _ in sent]}")
        # THE TIMING LAW'S ATTACK-SKILL HALF (ANIMREF-R3 fix 3): a
        # zero-activation attack skill's E5 rides the weapon, landing at
        # begin + swing_windup(current interval) -- Power Shot's own two
        # live gaps (1.1374/1.1387 over a 2.475 bow) against the law's
        # 1.1375. A LISTED activation still wins (the branch above used
        # activation 1.0 and scheduled begin + 1.0).
        authsrv.skill_timing = lambda sid: (0.0, 0.0, 3.0)
        state2 = {"agents": {}}
        sent2 = []
        send2 = lambda op, vals, label="", quiet=False: \
            sent2.append((op, vals, label))
        t0 = _time.time()
        _press(authsrv, send2, state2, skill=394, target=40)
        c2 = state2["pending_casts"][0]
        expect = authsrv.swing_windup(
            authsrv.ATTACK_INTERVAL
            * authsrv.attack_interval_factor(state2, authsrv.PLAYER_AGENT_ID))
        check(abs((c2["e5_at"] - t0) - expect) < 0.05,
              "a ZERO-activation attack skill schedules its E5 a weapon "
              "windup out, not instantly -- the activation-column model "
              "left Power Shot's E5 at the press, 1.14 s early",
              f"e5 in {c2['e5_at'] - t0:.4f}s, law says {expect:.4f}s "
              f"(hammer {authsrv.ATTACK_INTERVAL}s -> "
              f"{authsrv.swing_windup(authsrv.ATTACK_INTERVAL):.4f}s)")
        # AND THE REVERT ARM, added 2026-08-31 with the flag it tests. The
        # window this widened (0 -> ~0.775 s on a 1.75 s weapon) is the first
        # suspect for the R5 operator's "attacks block movement longer than
        # stock", so the comparison has to be one flag away and has to stay
        # working. A revert flag with no test is a revert flag that rots.
        try:
            authsrv.ATTACK_E5_WINDUP = False
            state3 = {"agents": {}}
            sent3 = []
            send3 = lambda op, vals, label="", quiet=False: \
                sent3.append((op, vals, label))
            t3 = _time.time()
            _press(authsrv, send3, state3, skill=394, target=40)
            c3 = state3["pending_casts"][0]
            check(abs(c3["e5_at"] - t3) < 0.05,
                  "--legacy-attack-e5 puts that E5 back AT the press",
                  f"e5 in {c3['e5_at'] - t3:.4f}s -- the pre-ANIMREF-R3 wire, "
                  f"against {expect:.4f}s with the fix on")
        finally:
            authsrv.ATTACK_E5_WINDUP = True
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
        check([op for op, _, _ in sent] == [0x00E5, 0x009F, 0x009F, 0x009F],
              "E6 is due but WAITS: the observed order outranks the clock",
              f"{[hex(op) for op, _, _ in sent]}")
        _rewind(state, 0.5)
        authsrv.cast_tick(send, state, 0)
        check([op for op, _, _ in sent] ==
              [0x00E5, 0x009F, 0x009F, 0x009F, 0x00E3, 0x00E6],
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
        _press(authsrv, send, state, skill=105, target=40)
        first = state["pending_casts"][0]
        sent.clear()
        _press(authsrv, send, state, skill=105, target=40)
        second = state["pending_casts"][1]
        gap = second["e5_at"] - first["e5_at"]
        check(abs(gap - (0.75 + 2.0)) < 0.05,
              "the second cast's E5 lands aftercast + activation after the "
              "first's -- skill 105's own two live cycles, generalized",
              f"gap={gap:.3f}s (the naive press+activation model is refuted "
              f"by +0.64s and +0.57s residuals in the corpus)")
        check([op for op, _, _ in sent] == [0x00E4]
              and first["begun"] and not second["begun"],
              "and the QUEUED press sends E4 ALONE -- no debit, no "
              "animation: both live queued presses (t=9.8501, 19.6902) "
              "carry nothing after their E4, and the burst tail belongs "
              "to the begin (castmech 3b/3c)",
              f"{[(hex(op), vals) for op, vals, _ in sent]}")
        sent.clear()
        _rewind(state, 2.75)   # first's E5+E3 due; second's begin due
        authsrv.cast_tick(send, state, 0)
        check([op for op, _, _ in sent] ==
              [0x00E5, 0x009F, 0x009F, 0x009F, 0x00E3, 0x00A2, 0x00A0],
              "the first cast completes (E5, 58, the hold pulse) and the "
              "queued burst rides its E3: the debit then the animation, "
              "retail's own order at both of 153's E3 instants (E3, "
              "property 62, property 60 -- 2 of 2), with NO property 8 at "
              "the begin (2 of 2 there too)",
              f"{[(hex(op), vals) for op, vals, _ in sent]}")
        check(sent[5][1][0] == authsrv.agents.GV_ENERGY_SPENT
              and sent[6][1] == [authsrv.agents.GV_SKILL_ACTIVATED,
                                 PLAYER, 40, 105]
              and second["begun"],
              "the debit names the energy property and the animation names "
              "the queued skill AND its target -- [60, 31, 40, 105] rode "
              "153's E3 on the live wire verbatim, deferred to the moment "
              "the caster freed",
              f"debit={sent[5][1]}, animation={sent[6][1]}")
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
