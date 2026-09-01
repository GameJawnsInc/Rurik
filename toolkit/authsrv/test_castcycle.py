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

EVERY SECTION BUT 5 RUNS ON A BARE MACHINE, and saying so cost three fixes
on 2026-08-31 because the claim had never once been TRUE. It used to read
"sections 1-3 and 5 stub `skill_timing`, so they run on a bare machine" --
wrong about which section needs the vault (it is 5, not 4; the numbering
went stale when 2b/2c/2d landed) and wrong that stubbing the timing was
enough. With `RURIK_VAULT` pointed at nothing this file did not fail its
floor, it died with a TRACEBACK before check 1, which is the outcome
`checks.py` exists to prevent. Three separate defects, none of them this
file's alone:

  1. `authsrv.player_rank_for_skill` was the one lookup on the press path
     with no bare-machine fallback, so `handle_skill_press` raised
     `ContentError` on skill 42. That was a SERVER defect, not a test
     defect -- fixed there, and guarded by test_bareimport.py section 3.
  2. The press burst's 0x00A2 is `skill_cost`'s, a SECOND content read the
     old claim never accounted for. Sections 1, 2b and 4 stub it now, for
     the reason 2b already stubbed `_is_attack_skill`: what they pin is the
     ORDER of the burst, not what a spell costs.
  3. Both `LEDGER.skip` calls passed one argument to a two-argument
     signature, so the skip paths raised `TypeError` the first time they
     were ever reached. A skip path nothing has run is not a skip path.

MEASURED, both ways, from green runs (re-measured 2026-09-01 after the
ANIMREF-RE checks landed and again after the same-day revert): 35 checks
with the vault, 33 without
plus one declared skip. The floor is the BARE-MACHINE number -- the shape
test_armour.py and test_position_trust.py both use, so that a machine with
no vault is called complete when it is, and short when it is not.

Section 5 reads the real content rows (vault overlay) and SKIPS, loudly,
when no vault is present -- the values it pins are the live-corroborated
trio for skill 153.
"""

import os
import sys
import time as _time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import checks  # noqa: E402

LEDGER = checks.Ledger("cast cycle", floor=33)
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
    saved_cost = authsrv.skill_cost
    authsrv.skill_timing = lambda sid: (1.0, 0.75, 8.0)
    # THE COST IS STUBBED FOR THE SAME REASON THE TIMING IS, and until
    # 2026-08-31 it was not: the debit below is `skill_cost`'s, a SECOND
    # content read the docstring's bare-machine claim never accounted for, so
    # with no vault skill 42 cost 0, no 0x00A2 went out, and this section's
    # exact op list was unreachable. 10 is skill 42's own vault figure, pinned
    # here so the burst has the same shape on both machines -- what this
    # section is about is the ORDER of the burst, not what a spell costs
    # (test_pools sections 6-6c own the amount).
    authsrv.skill_cost = lambda sid: (10, 0)
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
        authsrv.skill_cost = saved_cost


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
              and sent[4][1] == [PLAYER, 42, 7]
              and state.get("action_hold") == 1,
              "E3 fires an aftercast later, echoing the pending key, and "
              "the hold RIDES ON -- the default again since the 2026-09-01 "
              "revert. The corpus says retail frees it here (19 of 19 "
              "unmoved cycles, which also resolves castmech P10) and this "
              "section pinned that release for half a day; it went back "
              "because the operator scored the shipped pair 'very floaty' "
              "and 'warping' (FINDINGS 29). The wire fact is not "
              "withdrawn -- the DEFAULT is, pending a run that scores "
              "--e3-release alone",
              f"{sent[4:]}")

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

        # THE OTHER ARM, still exercised because the flag still has to
        # WORK: --e3-release frees the hold at the E3. Both directions run
        # in every suite pass, which is what makes the next A/B cheap --
        # the arm is proven live before the operator ever launches.
        state2 = {"agents": {}}
        sent2 = []
        send2 = lambda op, vals, label="", quiet=False: \
            sent2.append((op, vals, label))
        authsrv.ANIMREF_E3_RELEASE = True
        try:
            _press(authsrv, send2, state2)
            _rewind(state2, 1.0)
            authsrv.cast_tick(send2, state2, 0)
            _rewind(state2, 0.75)
            sent2.clear()
            authsrv.cast_tick(send2, state2, 0)
            check([op for op, _, _ in sent2] == [0x00E3, 0x009F]
                  and sent2[1][1] == [authsrv.agents.GV_DISABLED, PLAYER, 0]
                  and state2.get("action_hold") == 0,
                  "--e3-release: [8 -> 0] rides behind the E3, E3 first -- "
                  "retail's shape (19/19 unmoved cycles) and the arm that "
                  "ARMS the client's 250 ms resume poll via the walk-gate "
                  "clear (0x0081C090). Live, and off by default until a "
                  "run scores it alone", f"{sent2}")
        finally:
            authsrv.ANIMREF_E3_RELEASE = False
        check(authsrv.ANIMREF_E3_RELEASE is False,
              "and the release is OPT-IN, not the default -- reverted "
              "2026-09-01 on the operator's verdict ('very floaty', "
              "'warping'), the same day it shipped. A default a feel "
              "verdict rejected does not stay on because its derivation "
              "was good")
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
    saved_cost = authsrv.skill_cost
    authsrv.skill_timing = lambda sid: (1.0, 0.0, 3.0)
    # Stubbed rather than read from content: on a bare machine every id is
    # "not attack" (no rows), so the family split is pinned by forcing it.
    authsrv._is_attack_skill = lambda sid: True
    # And the cost, for the same reason and the same way -- the 0x00A2 in the
    # op list below is a content read this stub set forgot until 2026-08-31.
    authsrv.skill_cost = lambda sid: (10, 0)
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
        # BEFORE the E3 only: the E3 release ([8 -> 0] behind the E3,
        # ANIMREF-RE) is the caster freeing, not a borrowed cast-end pulse.
        e3_at = [op for op, _, _ in sent].index(0x00E3) \
            if 0x00E3 in [op for op, _, _ in sent] else len(sent)
        borrowed = [vals for op, vals, _ in sent[:e3_at]
                    if op == 0x009F
                    and vals[0] in (authsrv.agents.GV_SKILL_FINISHED,
                                    authsrv.agents.GV_DISABLED)]
        own46 = [vals for op, vals, _ in sent
                 if op == 0x009F
                 and vals[0] == authsrv.agents.GV_ATTACK_SKILL_FINISHED]
        check([op for op, _, _ in sent][0] == 0x00E5 and not borrowed
              and own46 == [[authsrv.agents.GV_ATTACK_SKILL_FINISHED,
                             PLAYER, 0]],
              "the E5 fires with NO [58, agent, 0] and NO hold pulse -- "
              "nothing of the spell family's cast end is borrowed -- and "
              "WITH the attack family's own [46, agent, 0] (ANIMREF-R6): "
              "castmech's 'neither 58 nor 46, 0 of 2' was the bow artifact "
              "sec.3 refuted -- 46 rides the melee execution batch 40/40 in "
              "the full corpus, and it goes out even on a whiff (this press "
              "targets an agent the state does not hold), because it closes "
              "the PLAYER's action, not the hit",
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
        authsrv.skill_cost = saved_cost


def section_attack_finish_batch():
    """ANIMREF-R6: the execution batch, both arms.

    The referent is the live corpus (FINDINGS 13): 40 of 40 self prop-46
    events open their batch with 0x009F [46, agent, 0], the adrenaline and
    the damage follow, and NO swing bracket (attack_started, melee_finished)
    rides along -- the skill replaces the swing its windup announced. The
    legacy arm preserves the pre-R6 wire exactly, including its defect: the
    interval-gated swing path, where a press mid-chain dealt nothing.
    """
    import authsrv

    print("\n2c. ANIMREF-R6: the attack-skill execution batch, both arms")
    saved = authsrv.skill_timing
    saved_attack = authsrv._is_attack_skill
    saved_dmg = authsrv.PLAYER_SWING_DAMAGE
    authsrv.skill_timing = lambda sid: (1.0, 0.0, 3.0)
    authsrv._is_attack_skill = lambda sid: True
    authsrv.PLAYER_SWING_DAMAGE = (5, 5)
    try:
        def run_arm():
            sent = []
            send = lambda op, vals, label="", quiet=False: \
                sent.append((op, vals, label))
            agent = {"name": "target", "dead": False,
                     "last_hit": _time.time(),        # MID-CHAIN, on purpose
                     "max_health": 100.0, "health": 100.0, "pos": (0.0, 0.0)}
            state = {"agents": {40: agent}, "pos": (0.0, 0.0)}
            _press(authsrv, send, state, skill=394, target=40)
            sent.clear()
            _rewind(state, 1.0)
            authsrv.cast_tick(send, state, 0)
            return sent, agent, state

        sent, agent, state = run_arm()
        ops = [op for op, _, _ in sent]
        vals46 = [v for op, v, _ in sent if op == 0x009F
                  and v[0] == authsrv.agents.GV_ATTACK_SKILL_FINISHED]
        dmg = [v for op, v, _ in sent if op ==
               authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
               and v[0] in (authsrv.agents.PROP_DAMAGE,
                            authsrv.agents.GV_CRITICAL)]
        started = [v for op, v, _ in sent if op ==
                   authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                   and v[0] == authsrv.agents.GV_ATTACK_STARTED]
        finished = [v for op, v, _ in sent if op == 0x009F
                    and v[0] == authsrv.agents.GV_MELEE_ATTACK_FINISHED]
        check(vals46 == [[authsrv.agents.GV_ATTACK_SKILL_FINISHED,
                          PLAYER, 0]]
              and len(dmg) == 1 and dmg[0][1] == 40,
              "default arm: [46, player, 0] goes out and the damage lands "
              "IN THE BATCH despite a swing landed this instant -- the "
              "windup was the interval, so the mid-chain press is not "
              "swallowed (the old path's silent return)",
              f"46={vals46}, dmg={dmg}, agent health={agent['health']}")
        rel = [v for op, v, _ in sent if op == 0x009F
               and v[0] == authsrv.agents.GV_DISABLED and v[2] == 0]
        check(not started and not finished
              and ops.index(0x00E5) < ops.index(0x009F)
              and ops[-1] == 0x00E3 and rel == [],
              "and NO swing bracket rides the batch -- no attack_started, "
              "no melee_attack_finished, 40/40 in the corpus -- with the "
              "E5 opening and the E3 closing. NO hold release behind the "
              "E3: that shipped as the default on 2026-09-01 and was "
              "reverted the same day (operator: 'very floaty', "
              "'warping'), so the attack family closes on its E3 again. "
              "The corpus's own attack-skill releases scatter 0.14-1.1 s "
              "after E5 (n=16) -- consistent with the release but far too "
              "few to pin it, which is part of why it went back",
              f"ops={[hex(o) for o in ops]}, rel={rel}")
        check(agent["health"] == 95.0,
              "the strike is the weapon's own number (5 pinned) -- a real "
              "hit, not a phantom",
              f"health={agent['health']}")
        # ANIMREF-R7b: the swing clock is stamped so the chain's next START
        # opens one windup after the execution, LAW B's 0.749..0.783 cluster
        # (21/38) against swing_windup(interval). The gate reads
        # now - player_last_swing < interval, so the stamp is
        # exec + windup - interval.
        iv = authsrv.ATTACK_INTERVAL * authsrv.attack_interval_factor(
            state, authsrv.PLAYER_AGENT_ID)
        gap = (state.get("player_last_swing", 0.0) + iv) - _time.time()
        check(abs(gap - authsrv.swing_windup(iv)) < 0.1,
              "and the chain's next START is paced one windup out "
              "(ANIMREF-R7b, LAW B) -- not reopened in the execution tick",
              f"next START opens in {gap:.3f}s, windup is "
              f"{authsrv.swing_windup(iv):.3f}s")

        authsrv.ATTACK_FINISH_BATCH = False
        try:
            sent, agent, _state2 = run_arm()
            vals46 = [v for op, v, _ in sent if op == 0x009F
                      and v[0] == authsrv.agents.GV_ATTACK_SKILL_FINISHED]
            dmg = [v for op, v, _ in sent if op ==
                   authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET
                   and v[0] in (authsrv.agents.PROP_DAMAGE,
                                authsrv.agents.GV_CRITICAL)]
            check(not vals46 and not dmg and agent["health"] == 100.0,
                  "--legacy-attack-finish restores the pre-R6 wire exactly: "
                  "no 46, and the mid-chain press deals NOTHING (the "
                  "interval gate swallows it) -- the defect is the legacy "
                  "arm's pinned shape, so the comparison stays one flag away",
                  f"46={vals46}, dmg={dmg}, health={agent['health']}")
        finally:
            authsrv.ATTACK_FINISH_BATCH = True
    finally:
        authsrv.skill_timing = saved
        authsrv._is_attack_skill = saved_attack
        authsrv.PLAYER_SWING_DAMAGE = saved_dmg


def section_skill_visual():
    """ANIMREF-R8: the on-body effect visual, and the channel rule.

    The ids come from `content/world.toml`'s `skill_visual` block (extracted
    from the client's own s_skill row), so this section needs the content
    store; it SKIPS loudly without it rather than passing on stubs. What it
    pins is the part that is ours to get wrong -- which channel each visual
    rides, and that a skill with no row sends nothing at all.
    """
    import authsrv

    print("\n2d. ANIMREF-R8: the on-body effect visual and its channel rule")
    try:
        authsrv.agents.WORLD.get("skill_visual", "312")
    except Exception as exc:
        LEDGER.skip("2d. the on-body effect visual and its channel rule",
                    f"no skill_visual content rows ({type(exc).__name__}) -- "
                    f"the channel rule is checked wherever content loads")
        return

    def fire(skill, caster, target):
        sent = []
        send = lambda op, vals, label="", quiet=False: \
            sent.append((op, vals, label))
        authsrv.send_skill_visual(send, {}, caster, skill, target, 0)
        return [(op, v) for op, v, _ in sent]

    INT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
    TGT = authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
    ON_AGENT = authsrv.agents.GV_EFFECT_ON_AGENT
    ON_TARGET = authsrv.agents.GV_EFFECT_ON_TARGET

    # 200 carries a CASTER visual only (+0x78 = 362, +0x7c is the client's
    # own 2077 "none"): one property 21 on the caster, nothing on the target.
    out = fire(200, 1, 10)
    check(out == [(INT, [ON_AGENT, 1, 362])],
          "a caster-only skill sends ONE property 21 on the caster and "
          "nothing at the target -- the +0x7c sentinel is silence, not a "
          "substitute id",
          f"{out}")

    # 312 carries a RECIPIENT visual only (+0x7c = 556): property 20, and the
    # slot order is victim-first (reading B -- caster-first attributes
    # nothing in the corpus).
    out = fire(312, 10, 1)
    check(out == [(TGT, [ON_TARGET, 1, 10, 556])],
          "a recipient visual at another body rides property 20 as "
          "[prop, RECIPIENT, CASTER, id] -- victim slot first, as 0x00A3 "
          "damage does",
          f"{out}")

    # The same skill with no separate target: the recipient IS the caster, so
    # the id moves to property 21. This is the branch that explains one id
    # appearing on both channels in the corpus.
    out = fire(312, 10, None)
    check(out == [(INT, [ON_AGENT, 10, 556])],
          "and self-cast, the SAME id rides property 21 instead -- the "
          "channel follows the body, which is the whole content of the "
          "20/21 split",
          f"{out}")

    # A skill we have not extracted sends nothing. Inventing a component id
    # is exactly what R4 refused (FINDINGS sec.10).
    out = fire(99999, 1, 10)
    check(out == [],
          "a skill with no skill_visual row sends NOTHING -- silence rather "
          "than an invented component id",
          f"{out}")

    authsrv.SKILL_VISUALS = False
    try:
        out = fire(312, 10, 1)
        check(out == [],
              "--no-skill-visuals turns the whole channel off",
              f"{out}")
    finally:
        authsrv.SKILL_VISUALS = True


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
    saved_cost = authsrv.skill_cost
    authsrv.skill_timing = lambda sid: (2.0, 0.75, 6.0)
    # The debit that rides the E3 batch below is a content read, so it is
    # stubbed with the timing. Without this, a bare machine sent no 0x00A2,
    # the batch was two opcodes short, and the LAST check here died with an
    # IndexError off `sent[5]` -- a traceback, not a verdict, which is the one
    # outcome checks.py exists to prevent.
    authsrv.skill_cost = lambda sid: (10, 0)
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
        authsrv.skill_cost = saved_cost


def section_real_content():
    import authsrv

    print("\n5. the real numbers: skill 153 from the content store")
    try:
        authsrv.agents.WORLD.get("skills", "153")
    except Exception:
        LEDGER.skip("5. the real numbers: skill 153 from the content store",
                    "no 'skills' content rows -- vault overlay absent on "
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
    section_attack_finish_batch()
    section_skill_visual()
    section_order_pinned_when_inverted()
    section_queue_law()
    section_real_content()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
