"""test_agtrack_guard.py -- the derived pre-emit rule, clause by clause.

Pins: the constants really are derivations (cross-pinned against authsrv's
own resync constants so two derivations of the same bound cannot drift),
HOLE D's seeding contract, the three-zone verdicts (match / gates-pass /
veto with the error budget), the re-pin preconditions, clause 2's
arrival-risk check (the closure of p5-resync-disarm HOLE A), the
fence-closed composition (re-pin then grant appends -- safe by the decode),
and that prediction is PURE (a predict never truncates or clears the chain
it predicts about).

Synthetic throughout -- no vault, no client, bare machine.
"""

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                    # noqa: E402
import agtrack_mirror as am      # noqa: E402
import agtrack_guard as ag       # noqa: E402
import authsrv                   # noqa: E402

AS_SRC = open(authsrv.__file__, encoding="utf-8").read()

# Floor from the 2026-08-30 green run: 49 checks, all unconditional;
# +25 at MOVECODE-1z-ah (section 9: the stationary waiver -- the retract);
# +20 at MOVECODE-1z-bn (section 14: the waiver's walk-start clause);
# +2 at MOVECODE-1z-bq (the waiver's founding specimen, with the kinds the
# capture actually carries); +17 at MOVECODE-1z-bs (section 15: the waiver
# requires the newest report to be a stop -- 116 on the green run).  Each
# from a real green run, never from a guess.
LEDGER = checks.Ledger("agtrack guard: the derived pre-emit rule", floor=116)
check = checks.adopt_named(LEDGER)


def seeded_guard(px=0.0, py=0.0, t0=1000.0):
    g = ag.AgTrackGuard()
    g.on_placement(px, py, 0, t0)
    return g


def main():
    # ---- 1. the constants are derivations, cross-pinned ----------------
    check("re-pin max age == authsrv's RESYNC_MAX_REPORT_AGE (one bound, "
          "two derivations)",
          abs(ag.REPIN_MAX_REPORT_AGE - authsrv.RESYNC_MAX_REPORT_AGE)
          < 1e-12)
    check("re-pin min interval == authsrv's RESYNC_MIN_INTERVAL",
          ag.REPIN_MIN_INTERVAL == authsrv.RESYNC_MIN_INTERVAL)
    check("the tube radius is the client's own (authsrv RESYNC_SEPARATION "
          "== R_MATCH == 100.0)",
          authsrv.RESYNC_SEPARATION == am.R_MATCH == 100.0)
    check("max age really is R_MATCH / run speed",
          abs(ag.REPIN_MAX_REPORT_AGE - 100.0 / 288.0) < 1e-12)
    check("GATE1_RED is the measured effective cut, under the raw 300",
          299.0 < ag.GATE1_RED < 300.0)
    check("min interval sits under the 0->red closing time 299.33/576",
          ag.REPIN_MIN_INTERVAL < ag.GATE1_RED / (2 * ag.RUN_SPEED))

    # ---- 2. HOLE D: unseeded has no opinion ----------------------------
    g = ag.AgTrackGuard()
    v = g.pre_emit(100.0, 0.0, 0, 0, now=1000.0)
    check("unseeded: pre_emit answers NOT_READY, never a pass",
          v.code == ag.NOT_READY and g.n_not_ready == 1)
    check("unseeded: repin_state refuses too",
          g.repin_state(1000.0)[0] == ag.REPIN_NONE)

    # ---- 3. GREEN: in-tube grant passes on MATCH -----------------------
    g = seeded_guard()
    g.on_report(0.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.1)
    v = g.pre_emit(100.0, 0.0, 0, 0, now=1000.2)
    check("green: grant from an in-tube sync copy predicts MATCH -> PASS",
          v.code == ag.PASS and v.why == "match")
    check("green: repin_state says none needed",
          g.repin_state(1000.2)[0] == ag.REPIN_NONE)

    # ---- 4. prediction is PURE -----------------------------------------
    before_len = g.mirror.chain_len
    before_head = g.mirror.head
    g.mirror.predict_grant(5000.0, 0.0, 0, 0, g._ms(1000.3), (0.0, 0.0))
    g.mirror.predict(g._ms(1000.3), (0.0, 0.0))
    check("predict/predict_grant mutate neither chain length nor head",
          g.mirror.chain_len == before_len
          and g.mirror.head is before_head)
    check("predict left the sync copy untouched",
          g.mirror.sync.x78 == 0.0 and g.mirror.sync.t_arrive != 0
          or g.mirror.sync.x78 == 0.0)

    # ---- 5. RED: the veto, and no 0x0029 escapes it --------------------
    g = seeded_guard()                       # sync parked at (0, 0)
    g.on_report(5000.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.1)
    v = g.pre_emit(5000.0, 0.0, 0, 0, now=1000.2)
    check("red: even the grant AIMED AT the player is vetoed (its own "
          "delivery evaluation snaps first)",
          v.code == ag.VETO and v.why == "gate1-red")
    check("red veto carries the re-pin answer", v.repin == ag.REPIN_DUE)
    code, why = g.repin_state(1000.2)
    check("red: standing repin_state agrees", code == ag.REPIN_DUE
          and why == "gate1-red")

    # ---- 6. the BUDGET veto (model under-read guarded by arithmetic) ---
    g = seeded_guard()
    g.on_report(250.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.0)
    v = g.pre_emit(250.0, 0.0, 0, 0, now=1000.6)      # age 0.6 s
    check("budget: modeled 250 u + 288*0.6 + 10 crosses red -> VETO",
          v.code == ag.VETO and v.why == "budget-red")
    check("budget veto's re-pin is BLOCKED by the same staleness",
          v.repin == ag.REPIN_BLOCKED)
    v = g.pre_emit(250.0, 0.0, 0, 0, now=1000.05)     # age 0.05 s
    check("same separation with a fresh report stays PASS_GATES "
          "(250 + 14.4 + 10 < 299.33)",
          v.code == ag.PASS_GATES)

    # ---- 7. re-pin preconditions ---------------------------------------
    g = seeded_guard()
    g.on_report(5000.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.0)
    check("fresh accept -> re-pin DUE", g._repin_code(1000.1) == ag.REPIN_DUE)
    check("stale (> 100/288 s) -> BLOCKED",
          g._repin_code(1000.5) == ag.REPIN_BLOCKED)
    g.on_report(9000.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.6,
                accepted=False)
    check("a refusal since the accept -> BLOCKED (the refused-report hole)",
          g._repin_code(1000.65) == ag.REPIN_BLOCKED)
    g.on_report(5100.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.7)
    check("the next accept re-opens it", g._repin_code(1000.75)
          == ag.REPIN_DUE)
    g.on_emit(0x2C, 5100.0, 0.0, 0, None, now=1000.8)
    check("rate: within 0.5 s of a sent re-pin -> BLOCKED",
          g._repin_code(1001.0) == ag.REPIN_BLOCKED)

    # ---- 8. the fence-closed composition (re-pin THEN grant) -----------
    check("after the 0x002C the fence is CLOSED", not
          g.mirror.client_controlled)
    v = g.pre_emit(5200.0, 0.0, 0, 0, now=1000.9)
    check("a grant behind the closed fence PASSES: it appends, no test "
          "runs (dispatcher fence 0x00606002)",
          v.code == ag.PASS and v.why == "fence-closed (appends)")
    g.on_report(5150.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1001.5)
    check("the next player command re-arms (fence open again)",
          g.mirror.client_controlled)
    check("rate expires once a fresh accept exists (0.75 s > 0.5, "
          "age 0.05 s)", g._repin_code(1001.55) == ag.REPIN_DUE)

    # ---- 9. clause 2: arrival risk (HOLE A closed) ---------------------
    g = seeded_guard()
    g.on_report(0.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.0)
    g.on_emit(0x29, 2880.0, 0.0, 0, 0, now=1000.1)   # 10 s leg away
    risky, _ = g.arrival_risk(1005.0)
    check("mid-leg, arrival 5 s out: not yet risky (horizon 0.5 s)",
          not risky)
    risky, pv = g.arrival_risk(1009.8)
    check("0.3 s before the arrival matures, the evaluation at q = dest "
          "predicts SNAP -> risky", risky and pv.code == am.SNAP)
    code, why = g.repin_state(1009.8)
    check("repin_state surfaces it as arrival-risk",
          why == "arrival-risk")
    check("...but the re-pin is BLOCKED on the stale report (age 9.8 s) "
          "-- the guard cannot invent a fresh position",
          code == ag.REPIN_BLOCKED)
    g.on_report(2870.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1009.85)
    risky2, _ = g.arrival_risk(1009.9)
    check("a fresh report AT the destination clears the risk (the "
          "evaluation would land in tube)", not risky2)

    # ---- 9b. the two-world join (invisible resets bracket) -------------
    # A fence closed by OUR OWN predicted snap is a guess: the TWIN (the
    # no-resets world) must still be able to veto (1z-r.3).
    g = seeded_guard()
    g.on_report(5000.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.0)
    v = g.on_emit(0x29, 0.0, 0.0, 0, 0, now=1000.1)   # far grant -> SNAP
    check("setup: the emitted grant's evaluation predicted a snap",
          v is not None and v.code == am.SNAP)
    check("main mirror's fence closed on its guess; the twin's stayed OPEN",
          not g.mirror.client_controlled and g.twin.client_controlled)
    v2 = g.pre_emit(9000.0, 0.0, 0, 0, now=1000.2)
    check("the join: a red grant is STILL vetoed (the twin's world tests)",
          v2.code == ag.VETO)
    g2 = seeded_guard()
    g2.on_report(5000.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.0)
    g2.on_emit(0x2C, 5000.0, 0.0, 0, None, now=1000.1)
    check("our own 0x002C closes BOTH worlds' fences (certain)",
          not g2.mirror.client_controlled
          and not g2.twin.client_controlled)
    v3 = g2.pre_emit(9000.0, 0.0, 0, 0, now=1000.2)
    check("certain closure: the same red grant PASSES (it appends)",
          v3.code == ag.PASS and v3.why == "fence-closed (appends)")
    g.on_report(100.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.3)
    check("player input re-arms both worlds",
          g.mirror.client_controlled and g.twin.client_controlled)

    # ---- 10. on_emit applies to the mirror -----------------------------
    g = seeded_guard()
    g.on_report(0.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.0)
    g.on_emit(0x29, 288.0, 0.0, 0, 0, now=1000.1)
    check("an emitted grant drives the mirror's sync copy",
          g.mirror.sync.dest is not None
          and g.mirror.sync.dest[0] == 288.0)
    g.on_speed(0.5, now=1000.2)
    check("an emitted speed rides through", g.mirror.sync.move_speed == 0.5)

    # ---- 11. shadow counters -------------------------------------------
    g = seeded_guard()
    g.on_report(0.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.0)
    g.pre_emit(50.0, 0.0, 0, 0, now=1000.1)
    g.pre_emit(50.0, 0.0, 0, 0, now=1000.15)
    snap = g.snapshot()
    check("snapshot sums the shadow verdicts",
          snap["pass"] + snap["pass_gates"] + snap["veto"]
          + snap["not_ready"] == 2 and snap["seeded"])

    # ---- 12. THE ACTIVE ARM (authsrv._agtrack_maybe_repin) --------------
    # Driven with a fake send that replicates the real choke's guard feed
    # (_agtrack_shadow_emit), so the fire's own bookkeeping -- both mirrors
    # Cleared, the rate limiter stamped -- runs the same one path.
    sent = []

    def fake_send(op, values, label, quiet=False):
        sent.append((op, values, label))
        authsrv._agtrack_shadow_emit(state, op, values, None)

    state = {"pathmap": None}
    authsrv._agtrack_guard_seed(state, (0.0, 0.0), 0, conn_id=99)
    check("active: seed built a live guard with its lock",
          state.get("agtrack_guard") is not None
          and state.get("agtrack_guard_lock") is not None)
    # a red state with a FRESH accept: fire expected
    authsrv._agtrack_guard_call(state, "on_report", 5000.0, 0.0, 0,
                                ("head", 1.0, 0.0, 1), 2000.0,
                                accepted=True)
    fired = authsrv._agtrack_maybe_repin(fake_send, state, None, now=2000.1)
    check("active: predicted snap + fresh report FIRES one 0x002C",
          fired and len(sent) == 1
          and sent[0][0] == authsrv.GAME_SMSG_AGENT_UPDATE_POSITION)
    check("active: the payload is the CLIENT's own report, never ours",
          sent[0][1] == [authsrv.PLAYER_AGENT_ID, [5000.0, 0.0], 0])
    check("active: the fire Cleared both mirrors through the choke "
          "(fence closed, safe-composition state)",
          not state["agtrack_guard"].mirror.client_controlled
          and not state["agtrack_guard"].twin.client_controlled)
    fired = authsrv._agtrack_maybe_repin(fake_send, state, None, now=2000.2)
    check("active: no second fire (fence closed -> nothing due; rate "
          "would also block)", not fired and len(sent) == 1)
    # stale report: wants to fire but must refuse
    state2 = {"pathmap": None}
    authsrv._agtrack_guard_seed(state2, (0.0, 0.0), 0, conn_id=99)
    authsrv._agtrack_guard_call(state2, "on_report", 5000.0, 0.0, 0,
                                ("head", 1.0, 0.0, 1), 3000.0,
                                accepted=True)
    fired = authsrv._agtrack_maybe_repin(fake_send, state2, None,
                                         now=3000.6)
    check("active: a stale report refuses the fire (harm bound)",
          not fired and len(sent) == 1)
    # flag off restores pre-1z-s wire behaviour
    authsrv.AGTRACK_REPIN = False
    try:
        state3 = {"pathmap": None}
        authsrv._agtrack_guard_seed(state3, (0.0, 0.0), 0, conn_id=99)
        authsrv._agtrack_guard_call(state3, "on_report", 5000.0, 0.0, 0,
                                    ("head", 1.0, 0.0, 1), 4000.0,
                                    accepted=True)
        fired = authsrv._agtrack_maybe_repin(fake_send, state3, None,
                                             now=4000.1)
        check("active: --no-agtrack-repin sends nothing", not fired
              and len(sent) == 1)
    finally:
        authsrv.AGTRACK_REPIN = True
    # invalid plane refuses (the u16 field cannot say -1)
    state4 = {"pathmap": None}
    authsrv._agtrack_guard_seed(state4, (0.0, 0.0), 0, conn_id=99)
    authsrv._agtrack_guard_call(state4, "on_report", 5000.0, 0.0, None,
                                ("head", 1.0, 0.0, 1), 5000.0,
                                accepted=True)
    fired = authsrv._agtrack_maybe_repin(fake_send, state4, None,
                                         now=5000.1)
    check("active: an unusable plane word refuses the fire",
          not fired and len(sent) == 1)


    # ---- 9. MOVECODE-1z-ah: THE STATIONARY WAIVER (the retract) ---------
    # RUN-1zAB run A's fatal leg, verbatim from the capture: the body parked
    # and reported (10369.4169921875, 8282.3349609375) BIT-IDENTICAL three
    # times (t=11.892 / 14.028 / 15.763) while a 520 u backpedal lead at
    # 190.08 u/s walked the sync copy away from it. The guard reported
    # `arrival-risk` at t=18.074 -- 0.426 s BEFORE the 18.500 arrival -- and
    # was refused. This section pins WHICH gate refused, that the waiver
    # lifts exactly that one, and that a walking body can never reach it.
    RA_REPORT = (10369.4169921875, 8282.3349609375)
    RA_DEST = (9849.4169921875, 8282.3349609375)
    RA_PLANE, RA_T0 = 29, 15.764
    RA_ETA = RA_T0 + 520.0 / 190.08
    RA_RISK = 18.074

    # THE KINDS BELOW ARE SYNTHETIC AND THE REAL CAPTURE'S ARE NOT (1z-bq).
    # This fixture's three reports are all WALK-STARTS, which makes the pair at
    # the risk tick {0x003D -> 0x003D} -- a legitimate coincident pair, and the
    # one this section needs in order to exercise the waiver's mechanism at all.
    # RUN-1zAB run A itself carries 0x003D / **0x0047** / 0x003D, so its real
    # pair is {0x0047 -> 0x003D}, the one 1z-bn refuses; that is checked
    # separately in section 14 against the capture's own kinds. Keeping this
    # fixture synthetic is deliberate -- renaming it to the truth would delete
    # the only kept-pair case the suite has -- but it must not be described as
    # the specimen, which is what the docstring used to do.
    def run_a(waiver=True, walking=False, kinds=(False, False, False)):
        """A coincident-report leg, SYNTHETIC kinds. Returns the guard at the
        risk tick. `kinds` is per report: True = 0x0047 stop."""
        ag.STATIONARY_WAIVER = waiver
        g = ag.AgTrackGuard(mesh=None)
        g.on_placement(RA_REPORT[0], RA_REPORT[1], RA_PLANE, 11.0)
        pts = [RA_REPORT] * 3
        if walking:
            # a body actually walking the lead reports its own 0x003D
            # distance trigger instead -- ~512 u apart.
            pts = [RA_REPORT, (RA_REPORT[0] - 512.0, RA_REPORT[1]),
                   (RA_REPORT[0] - 1024.0, RA_REPORT[1])]
        for t, p, stop in zip((11.892, 14.028, 15.763), pts, kinds):
            g.on_report(p[0], p[1], RA_PLANE, ("rep", "syn", stop), t,
                        accepted=True)
        g.on_emit(0x29, RA_DEST[0], RA_DEST[1], RA_PLANE, RA_PLANE, RA_T0)
        return g

    # 1z-bs's clause (section 15) refuses this fixture's pair -- its newest
    # report is a walk-start -- so this section, which pins the waiver's
    # MECHANISM on the synthetic kept pair, is interrogated with that clause
    # OFF: it answers as the 1z-ah and 1z-bn builds did, which is what
    # RUN-1zAB/1zBO/1zBP measured.  The flag is a module global read at call
    # time (section 14's trap), so it is set here and restored in the finally.
    ag.WAIVER_NEWEST_MUST_BE_STOP = False
    try:
        check("the waiver ships ON, with its revert flag",
              ag.STATIONARY_WAIVER is True
              and "--no-repin-stationary-waiver" in AS_SRC
              and "_ag_flag.STATIONARY_WAIVER = False" in AS_SRC)

        # -- the predicate itself, pure
        g = ag.AgTrackGuard(mesh=None)
        g.on_placement(0.0, 0.0, 0, 1000.0)
        check("a placement alone is NOT a stationary measurement (one event, "
              "not two reports)", g.stationary() is False)
        check("nor does a placement stand in as the FIRST of the two -- it is "
              "where we put the agent, not the client telling us twice",
              g._last_report_pos is None)
        g.on_report(0.0, 0.0, 0, ("a",), 1001.0, accepted=True)
        check("one accepted report is still not two", g.stationary() is False)
        g.on_report(0.0, 0.0, 0, ("b",), 1002.0, accepted=True)
        check("TWO identical accepted reports: the body is MEASURED still",
              g.stationary() is True)
        g.on_report(0.9, 0.0, 0, ("c",), 1003.0, accepted=True)
        check("and 0.9 u apart still counts -- the bound is the client's own "
              "zero-distance radius, not equality",
              g.stationary() is True and 0.9 ** 2 <= am.ZERO_DIST_SQ)
        g.on_report(2.0, 0.0, 0, ("d",), 1004.0, accepted=True)
        check("1.1 u apart does NOT: over the radius, the body moved. The "
              "boundary is the client's own `distSq <= 1.0`, so 1.0 u exactly "
              "still counts as zero distance",
              g.stationary() is False and 1.1 ** 2 > am.ZERO_DIST_SQ)
        # a refused report must not become the second measurement
        g2 = ag.AgTrackGuard(mesh=None)
        g2.on_placement(0.0, 0.0, 0, 1000.0)
        g2.on_report(0.0, 0.0, 0, ("a",), 1001.0, accepted=True)
        g2.on_report(0.0, 0.0, 0, ("b",), 1002.0, accepted=True)
        g2.on_report(900.0, 0.0, 0, ("bad",), 1003.0, accepted=False)
        check("a REFUSED report advances neither measurement (it is "
              "disbelieved, and pos_rejects blocks anyway)",
              g2.stationary() is True
              and g2._repin_block(1003.1) == "rejects")
        # a click in flight is gliding the copy: the report is not the body
        g3 = run_a()
        g3.on_click(RA_REPORT[0] - 300.0, RA_REPORT[1], RA_PLANE, RA_RISK)
        check("REFUSED while a click glides the copy -- the report is then "
              "not where the body is", g3.stationary() is False)

        # -- run A, both arms
        off = run_a(waiver=False)
        risky_off, v_off = off.arrival_risk(RA_RISK)
        code_off, why_off = off.repin_state(RA_RISK)
        check("RUN A, waiver OFF: the guard PREDICTS THE SNAP 0.426 s early "
              "-- the predicate was never the problem",
              risky_off is True and v_off.code == am.SNAP
              and why_off == "arrival-risk" and RA_RISK < RA_ETA)
        check("RUN A, waiver OFF: and is BLOCKED, by the freshness gate and "
              "nothing else -- the capture's `blocked` row, named",
              code_off == ag.REPIN_BLOCKED
              and off.repin_block_reason(RA_RISK) == "stale-report"
              and off.pos_rejects == 0 and off.last_repin_at is None,
              "report age %.3f s against the %.3f s ceiling"
              % (RA_RISK - off.client_pos_at, ag.REPIN_MAX_REPORT_AGE))

        on = run_a(waiver=True)
        code_on, why_on = on.repin_state(RA_RISK)
        harm = math.hypot(on.client_pos[0] - RA_REPORT[0],
                          on.client_pos[1] - RA_REPORT[1])
        check("RUN A, waiver ON: the re-pin is DUE",
              code_on == ag.REPIN_DUE and why_on == "arrival-risk"
              and on.repin_block_reason(RA_RISK) is None)
        check("and the 0x002C it would send lands ON the parked body -- the "
              "harm the freshness gate exists to bound is ZERO here",
              harm ** 2 <= am.ZERO_DIST_SQ and harm < 1e-9,
              "harm %.6f u" % harm)

        # THE POINT: the arrival that armed the lock never fires.
        on.on_emit(0x2C, on.client_pos[0], on.client_pos[1], RA_PLANE, None,
                   RA_RISK)
        check("THE RETRACT: the 0x002C clears the arrival tick and the "
              "destination, so the 520 u arrival that armed 0.11 stage 1 "
              "NEVER MATURES (0x00602B20's armed arm -> 0x006020B0, which "
              "clears +0x48 at 0x006021E6)",
              on.mirror.sync.t_arrive == 0 and on.mirror.sync.dest is None)
        fired, t = None, RA_RISK + 0.05
        while t <= RA_ETA + 0.5:
            r = on.tick(t)
            if r is not None:
                fired = r
                break
            t += 0.05
        sep_after = math.hypot(on.mirror.sync.x78 - RA_REPORT[0],
                               on.mirror.sync.y78 - RA_REPORT[1])
        check("and no arrival fires through the window that snapped in the "
              "capture; the sync copy sits ON the body",
              fired is None and sep_after < 1e-9,
              "fired %s, sep %.6f u" % (fired, sep_after))

        # -- THE KNOWN-BAD ARM: the warp the gate exists to prevent
        walk = run_a(waiver=True, walking=True)
        risky_w, _v = walk.arrival_risk(RA_RISK)
        code_w, why_w = walk.repin_state(RA_RISK)
        check("KNOWN-BAD ARM -- a body WALKING the lead: two reports 512 u "
              "apart never satisfy the waiver, so the stale re-pin that "
              "would drag BOTH copies backward is still refused",
              walk.stationary() is False
              and walk.repin_block_reason(RA_RISK) == "stale-report")
        check("and it does not even get proposed: a walking body's sync copy "
              "tracks it, so no snap is predicted at all",
              risky_w is False and code_w == ag.REPIN_NONE)

        # -- the other preconditions still bite under the waiver
        rate = run_a(waiver=True)
        rate.last_repin_at = RA_RISK - 0.1
        check("the RATE still blocks a stationary body (the waiver lifts one "
              "gate, not all of them)",
              rate._repin_code(RA_RISK) == ag.REPIN_BLOCKED
              and rate.repin_block_reason(RA_RISK) == "rate")
        rej = run_a(waiver=True)
        rej.on_report(RA_REPORT[0], RA_REPORT[1], RA_PLANE, ("x",),
                      RA_RISK - 0.05, accepted=False)
        check("a REFUSED report since the last accept still blocks",
              rej._repin_code(RA_RISK) == ag.REPIN_BLOCKED
              and rej.repin_block_reason(RA_RISK) == "rejects")
        check("and an unseeded guard names itself",
              ag.AgTrackGuard(mesh=None).repin_block_reason(1.0) == "unseeded")

        # -- the row carries the reason (1z-ag replayed a capture for want
        #    of it, and published two wrong explanations first)
        check("the telemetry row names the blocker, so no later session has "
              "to replay a capture to find out which gate refused",
              "blocked_by=_agtrack_guard_call(" in AS_SRC
              and '"repin_block_reason", now' in AS_SRC)

        # -- the capture header must be able to say WHICH ARM produced it
        flags = authsrv.capture_flags()
        check("the capture header names the waiver -- authsrv's own discovery "
              "is scoped to its module globals, so a switch living in a policy "
              "module beside it would have gone unrecorded, and this run is an "
              "A/B on exactly that flag",
              flags.get("agtrack_guard.STATIONARY_WAIVER") is True)
        ag.STATIONARY_WAIVER = False
        try:
            check("and it tracks the flag, not a literal",
                  authsrv.capture_flags()
                  .get("agtrack_guard.STATIONARY_WAIVER") is False)
        finally:
            ag.STATIONARY_WAIVER = True
        check("bools only from the companion module: its derived constants and "
              "verdict names are not switches",
              "agtrack_guard.PASS" not in flags
              and "agtrack_guard.REPIN_MAX_REPORT_AGE" not in flags
              and "agtrack_guard.GATE1_RED" not in flags)

        # -- a 0x002C kills the keyboard leg (the stale-arrival third door)
        st = {"pos": (0.0, 0.0), "plane": 7,
              "kbd_leg": {"x0": 0.0, "y0": 0.0, "dest": (520.0, 0.0),
                          "plane": 7, "t0": 100.0, "speed": 288.0,
                          "wd_fired": False}}
        authsrv._note_wire_move(st, authsrv.GAME_SMSG_AGENT_UPDATE_POSITION,
                                [authsrv.PLAYER_AGENT_ID, [10.0, 0.0], 7],
                                101.0, rec=None)
        check("a 0x002C CLEARS the keyboard lead's leg record: the client's "
              "teleport primitive already cleared +0x48, so a leg left armed "
              "would let the kill or the refresh act on a dead leg",
              st.get("kbd_leg") is None)
    finally:
        ag.STATIONARY_WAIVER = True
        ag.WAIVER_NEWEST_MUST_BE_STOP = True

    # ---- 13. MOVECODE-1z-bf: gate 2's edge tolerance is a recorded switch --
    # The guard's gate 2 reads the mesh through agtrack_mirror.MeshAdapter,
    # whose tolerance lives in agtrack_mirror.GATE2_SEAM_TOL; authsrv records
    # the switch as a bool (capture_flags sweeps SCREAMING_CASE bools) and
    # --agtrack-gate2-exact zeroes the tolerance -- the known-bad arm the
    # corpus convicted (17 of 17 gate2-offmesh re-pins were false vetoes on
    # sub-unit edge slivers; one halted a walking body for 3.7 s).
    check("authsrv records AGTRACK_GATE2_SEAM, ON by default",
          authsrv.AGTRACK_GATE2_SEAM is True
          and authsrv.capture_flags().get("AGTRACK_GATE2_SEAM") is True)
    check("--agtrack-gate2-exact exists and zeroes the mirror's tolerance "
          "(source lock)",
          "--agtrack-gate2-exact" in AS_SRC
          and "_am_flag.GATE2_SEAM_TOL = 0.0" in AS_SRC)
    _msrc = open(am.__file__, encoding="utf-8").read()
    check("the mirror's gate 2 reads on_mesh under the tolerance and "
          "walkable() without it (source lock)",
          "return self.pm.on_mesh(x, y, GATE2_SEAM_TOL)" in _msrc
          and "return self.pm.walkable(x, y)" in _msrc
          and am.GATE2_SEAM_TOL == 1.0)

    # ---- 14. MOVECODE-1z-bn: the waiver's WALK-START CLAUSE ---------------
    # Section 9 pinned the stationary waiver and its known-bad arm: "a body
    # WALKING the lead: two reports 512 u apart never satisfy the waiver".
    # That arm is real and still passes below -- and it is not the arm the
    # waiver actually fires on.  A keyboard leg OPENS with a 0x003D walk-start
    # sitting on the previous leg's 0x0047 stop, 0.000 u apart, because the
    # body has not moved yet; the waiver reads that as a measured-still body
    # and lifts the freshness gate 1-2.4 s into the client's own committed
    # glide.  Corpus census (1z-bl): 19 such pairs, p50 harm 366.6 u, 18 of 19
    # over 100 u, against 0.0 u for the other two orderings.  RUN-1zBL watched
    # three rewind a walking body 298-433 u; RUN-1zBM ran the route with the
    # lead off, no re-pin fired and every leg walked (7 of 7).
    #
    # The clause refuses exactly {stop -> walk-start} and keeps the rest.
    # Retrodicted over the corpus by studies/movecode/review/waiverretro.py.
    def pair(older_stop, newer_stop, dx=0.0, t0=1000.0, clause=True):
        """A guard whose last two accepted reports are that pair of KINDS,
        dx apart.  Returns it at t0 + 2.0, a report age 5.8x the gate."""
        ag.WAIVER_WALKSTART_ENDS_STILL = clause
        g = ag.AgTrackGuard(mesh=None)
        g.on_placement(0.0, 0.0, 0, t0 - 1.0)
        g.on_report(0.0, 0.0, 0, ("rep", "s", older_stop), t0, accepted=True)
        g.on_report(dx, 0.0, 0, ("rep", "s", newer_stop), t0 + 0.1, accepted=True)
        return g

    STOP, WALK = True, False       # the sig's third element: is_stop
    # Interrogated with 1z-bs's clause OFF (restored in the finally): this
    # section pins the 1z-bn build -- the one RUN-1zBO and RUN-1zBP measured
    # -- and 1z-bs's clause subsumes it, so under the shipped build half of
    # these arms would answer for the wrong reason.  Section 15 pins the
    # shipped build on top of it.
    ag.WAIVER_NEWEST_MUST_BE_STOP = False
    try:
        check("the clause ships ON, with its own revert flag",
              ag.WAIVER_WALKSTART_ENDS_STILL is True
              and "--waiver-walkstart-stands" in AS_SRC
              and "_ag_flag.WAIVER_WALKSTART_ENDS_STILL = False" in AS_SRC)
        check("and the capture header records it, so a run's arm is readable "
              "off its own capture rather than off the session that made it",
              authsrv.capture_flags()
              .get("agtrack_guard.WAIVER_WALKSTART_ENDS_STILL") is True)

        # -- the predicate, all four orderings, points IDENTICAL throughout
        check("{stop -> walk-start} is REFUSED: the older report measures a "
              "still body, the newer one announces it is leaving, and the "
              "re-pin acts after that instant",
              pair(STOP, WALK).stationary() is False)
        check("{walk-start -> walk-start} still waives -- a body that said it "
              "was walking and reported the same point twice did not move",
              pair(WALK, WALK).stationary() is True)
        check("{walk-start -> stop} still waives: it is the body arriving, "
              "and the stop is a measurement of where it stopped",
              pair(WALK, STOP).stationary() is True)
        check("{stop -> stop} still waives",
              pair(STOP, STOP).stationary() is True)

        # -- the revert flag restores the pre-1z-bn behaviour on that pair
        check("--waiver-walkstart-stands restores it: the SAME pair waives "
              "again, so the arm is a real A/B and not a rewrite",
              pair(STOP, WALK, clause=False).stationary() is True
              and pair(STOP, WALK, clause=True).stationary() is False)

        # -- the clause is scoped to the waiver, not to the gate
        fresh = pair(STOP, WALK)
        check("a FRESH report is unaffected -- the clause lifts nothing and "
              "blocks nothing when the waiver was not carrying the decision",
              fresh._repin_block(1000.2) is None
              and pair(STOP, WALK, clause=False)._repin_block(1000.2) is None)
        stale = pair(STOP, WALK)
        check("a STALE one is blocked by the freshness gate, named, and the "
              "reverted arm is not -- this is the whole behavioural delta",
              stale._repin_block(1002.1) == "stale-report"
              and pair(STOP, WALK, clause=False)._repin_block(1002.1) is None,
              "report age %.3f s against the %.3f s ceiling"
              % (1002.1 - stale.client_pos_at, ag.REPIN_MAX_REPORT_AGE))
        check("non-coincident reports are untouched either way: the waiver "
              "never applied to them and the clause is inside it",
              pair(STOP, WALK, dx=600.0).stationary() is False
              and pair(WALK, WALK, dx=600.0).stationary() is False)

        # -- the KINDS have to travel with the points, and from authsrv
        g1 = ag.AgTrackGuard(mesh=None)
        g1.on_placement(0.0, 0.0, 0, 1000.0)
        g1.on_report(0.0, 0.0, 0, ("rep", "s", True), 1001.0, accepted=True)
        check("one report after a placement cannot trip the clause: the "
              "PREVIOUS kind is unknown, not False, and unknown must not "
              "read as a stop",
              g1.prev_is_walkstart is None and g1.stationary() is False)
        g2 = ag.AgTrackGuard(mesh=None)
        g2.on_placement(0.0, 0.0, 0, 1000.0)
        g2.on_report(0.0, 0.0, 0, ("rep", "s", True), 1001.0, accepted=True)
        g2.on_report(0.0, 0.0, 0, ("rep", "s", False), 1002.0, accepted=True)
        g2.on_report(900.0, 0.0, 0, ("rep", "s", True), 1003.0, accepted=False)
        check("a REFUSED report advances neither kind (it is disbelieved, so "
              "it cannot turn a refused pair into a waived one)",
              g2.last_is_walkstart is True and g2.prev_is_walkstart is False
              and g2.stationary() is False)
        g3 = ag.AgTrackGuard(mesh=None)
        g3.on_placement(0.0, 0.0, 0, 1000.0)
        g3.on_report(0.0, 0.0, 0, ("rep", 1.0), 1001.0, accepted=True)
        g3.on_report(0.0, 0.0, 0, ("rep", 1.0), 1002.0, accepted=True)
        check("a 2-tuple sig -- the shape section 9 and guardretro build by "
              "hand -- reads as a walk-start rather than raising, so the "
              "clause never fires on a caller that predates it",
              g3.last_is_walkstart is True and g3.prev_is_walkstart is True
              and g3.stationary() is True)
        check("authsrv's call site passes the stop bit as the sig's third "
              "element, which is where the kinds come from (source lock)",
              '("rep", source, bool(stop))' in AS_SRC)
        _gsrc = open(ag.__file__, encoding="utf-8").read()
        check("the clause reads the pair's KINDS and only fires on "
              "{stop -> walk-start} (source lock)",
              "and self.last_is_walkstart and self.prev_is_walkstart is False"
              in _gsrc)

        # -- THE KNOWN-BAD ARM, and it is the run this fix was derived from:
        #    RUN-1zBL leg 4Q.  The leg opened with a walk-start on the
        #    previous leg's stop; 1.9 s later the guard called arrival-risk
        #    on a report that old and the waiver let it through; the 0x002C
        #    SetPositioned both copies back to the leg's start.
        BL_T0, BL_RISK = 100.0, 101.93       # the corpus median report age
        def bl(clause):
            """The leg, ANSWERED under `clause`. The flag is a module global
            read at call time, so an arm must be interrogated before the next
            one is built -- returning two guards and querying them afterwards
            gives both the LAST arm's answer, which is how this check first
            went green against itself."""
            ag.WAIVER_WALKSTART_ENDS_STILL = clause
            g = ag.AgTrackGuard(mesh=None)
            g.on_placement(0.0, 0.0, 0, BL_T0 - 1.0)
            g.on_report(0.0, 0.0, 0, ("rep", "0x0047", True), BL_T0 - 0.2,
                        accepted=True)
            g.on_report(0.0, 0.0, 0, ("rep", "0x003D", False), BL_T0,
                        accepted=True)
            g.on_speed(288.0, BL_T0)
            g.on_emit(0x29, 520.0, 0.0, 0, 0, BL_T0)
            return {"code": g.repin_state(BL_RISK)[0],
                    "why": g.repin_state(BL_RISK)[1],
                    "block": g.repin_block_reason(BL_RISK),
                    "risk": g.arrival_risk(BL_RISK)[0],
                    "age": BL_RISK - g.client_pos_at}
        old, new = bl(False), bl(True)
        check("KNOWN-BAD ARM -- RUN-1zBL's leg shape, clause OFF: the re-pin "
              "is DUE on a report 1.93 s old, which is the defect",
              old["code"] == ag.REPIN_DUE and old["block"] is None
              and old["why"] == "arrival-risk")
        check("and clause ON it is BLOCKED, by the freshness gate the waiver "
              "was lifting -- 1z-ah's gate, doing 1z-ah's job. The risk is "
              "still PREDICTED in both arms: the clause moves the "
              "precondition, not the prediction",
              new["code"] == ag.REPIN_BLOCKED and new["block"] == "stale-report"
              and new["risk"] is True and old["risk"] is True)
        harm = ag.RUN_SPEED * old["age"]
        check("the harm the gate bounds is NOT the waiver's claimed zero: at "
              "this age the unwaived bound is a rewind of hundreds of units, "
              "and the corpus measured p50 366.6 u on this exact pair",
              harm > 100.0 and 300.0 < harm < 600.0,
              "RUN_SPEED * age = %.1f u" % harm)

        # -- section 9's own known-bad arm must STILL pass: a walking body's
        #    512 u reports never reach the waiver, clause or no clause
        check("section 9's walking arm is untouched -- the clause narrows the "
              "waiver, it does not widen anything",
              run_a(waiver=True, walking=True).stationary() is False
              and pair(WALK, WALK, dx=512.0).stationary() is False)
        # -- and section 9's specimen (a genuinely parked body reporting the
        #    same point three times) must still be waived
        check("a synthetic three-walk-start leg on one point still waives -- "
              "{0x003D -> 0x003D} is a kept pair and the clause is inside the "
              "waiver, not over it",
              run_a(waiver=True).stationary() is True
              and run_a(waiver=True).repin_state(RA_RISK)[0] == ag.REPIN_DUE)

        # -- AND THE HISTORICAL SPECIMEN, with the kinds the capture actually
        #    carries. 1z-bq: RUN-1zAB run A is 0x003D / 0x0047 / 0x003D, not
        #    three walk-starts, so its pair at the risk tick is the one this
        #    clause REFUSES -- the waiver's founding case is an instance of the
        #    defect the clause fixes. This check exists because the section
        #    above asserted the opposite for a day, on a fixture that invented
        #    the kinds.
        #    The flag is a module global read at CALL time, so each arm is
        #    interrogated under its own setting rather than built and queried
        #    later -- the trap this section already walked into once.
        real = run_a(waiver=True, kinds=(False, True, False))
        shipped = (real.stationary(), real.repin_block_reason(RA_RISK))
        ag.WAIVER_WALKSTART_ENDS_STILL = False
        try:
            reverted = (real.stationary(), real.repin_block_reason(RA_RISK))
        finally:
            ag.WAIVER_WALKSTART_ENDS_STILL = True
        check("RUN-1zAB run A's REAL kinds (0x003D / 0x0047 / 0x003D, capture "
              "authsrv-20260903T202121-c1) make its pair {0x0047 -> 0x003D}, "
              "so the clause REFUSES the waiver's own founding specimen -- and "
              "correctly: the client reported 520.0 u away 3.05 s later, so at "
              "the risk tick the body was ~394 u downrange, not parked",
              shipped == (False, "stale-report"))
        check("...and with the clause reverted it waives again, which is what "
              "the pre-1z-bn build did and why that 394 u rewind shipped",
              reverted == (True, None))
    finally:
        ag.WAIVER_WALKSTART_ENDS_STILL = True
        ag.STATIONARY_WAIVER = True
        ag.WAIVER_NEWEST_MUST_BE_STOP = True

    # ---- 15. MOVECODE-1z-bs: the waiver requires the NEWEST report to be a STOP
    # 1z-bn refused {stop -> walk-start} and kept {walk-start -> walk-start}.
    # The corpus (studies/movecode/review/waiverclick.py) splits the kept
    # branch by ORDERING, under the waiver's own click state: where the newest
    # report is a STOP the next report finds the body still in 151 of 151
    # windows; where it is a WALK-START the body is over 100 u away in 14 of
    # 87, at the client's own walking speeds.  A leg that opens on a
    # coincident double walk-start -- a chord, or a heading change before the
    # body leaves; 446 such pairs in owner play -- is therefore a 1z-bl rewind
    # waiting for a re-pin want, and only the waiver opens that door.  The
    # clause applies 1z-bn's own argument to the one member of the pair whose
    # kind says anything about what is true AFTER it.  Sections 9 and 14 pin
    # the earlier builds with this clause off; this section pins the shipped
    # one.  Every arm below is built AND read under its own flag setting.
    def dws(bs, bn=True, waiver=True, kinds=("0x0047", "0x003D", "0x003D"),
            t0=2000.0):
        """A leg opening at one point with the given report KINDS (the
        third is 40 ms after the second, or absent), under a 520 u lead at
        288 u/s, answered at t0 + 1.5 s: report age ~1.46 s, the lead's
        sync copy ~420 u out."""
        ag.STATIONARY_WAIVER = waiver
        ag.WAIVER_WALKSTART_ENDS_STILL = bn
        ag.WAIVER_NEWEST_MUST_BE_STOP = bs
        try:
            g = ag.AgTrackGuard(mesh=None)
            g.on_placement(0.0, 0.0, 0, t0 - 1.0)
            ts = (t0 - 0.2, t0, t0 + 0.04)
            for src, t in zip(kinds, ts):
                if src is None:
                    continue
                g.on_report(0.0, 0.0, 0, ("rep", src, src == "0x0047"), t,
                            accepted=True)
            g.on_speed(288.0, t0 + 0.041)
            g.on_emit(0x29, 520.0, 0.0, 0, 0, t0 + 0.041)
            t = t0 + 1.5
            code, why = g.repin_state(t)
            return {"still": g.stationary(), "code": code, "why": why,
                    "block": g.repin_block_reason(t),
                    "risk": g.arrival_risk(t)[0], "age": t - g.client_pos_at,
                    "pair": (g.prev_is_walkstart, g.last_is_walkstart)}
        finally:
            ag.STATIONARY_WAIVER = True
            ag.WAIVER_WALKSTART_ENDS_STILL = True
            ag.WAIVER_NEWEST_MUST_BE_STOP = True

    try:
        check("1z-bs: the clause ships ON, with its own revert flag",
              ag.WAIVER_NEWEST_MUST_BE_STOP is True
              and "--waiver-walkstart-pair-stands" in AS_SRC
              and "_ag_flag.WAIVER_NEWEST_MUST_BE_STOP = False" in AS_SRC)
        check("and the capture header records it",
              authsrv.capture_flags()
              .get("agtrack_guard.WAIVER_NEWEST_MUST_BE_STOP") is True)
        check("and the 1z-bn revert alone is told it changes nothing under this "
              "clause -- RUN-1zBP's arm now needs both flags (source lock)",
              "needs --waiver-walkstart-pair-stands as well" in AS_SRC)
        _gsrc2 = open(ag.__file__, encoding="utf-8").read()
        check("the clause reads only the NEWEST kind (source lock)",
              "if WAIVER_NEWEST_MUST_BE_STOP and self.last_is_walkstart:"
              in _gsrc2)

        # -- the four orderings under the SHIPPED build, points identical
        check("{stop -> walk-start} stays refused",
              pair(STOP, WALK).stationary() is False)
        check("{walk-start -> walk-start} is now REFUSED too: the newest "
              "report says the body is leaving, whatever the older one said",
              pair(WALK, WALK).stationary() is False)
        check("{walk-start -> stop} still waives -- a stop is the only report "
              "kind that asserts rest as of its own instant, and the corpus "
              "finds the body still after it in 151 of 151 windows",
              pair(WALK, STOP).stationary() is True)
        check("{stop -> stop} still waives (and never coincides in 1,311 "
              "captures -- the surviving branch is {walk-start -> stop} alone)",
              pair(STOP, STOP).stationary() is True)
        check("a 2-tuple sig reads as a walk-start, so the hand-built shape "
              "section 9 and guardretro use is refused too, not raised on",
              (lambda g: (g.last_is_walkstart, g.prev_is_walkstart,
                          g.stationary()))(
                  (lambda g: (g.on_placement(0.0, 0.0, 0, 1000.0),
                              g.on_report(0.0, 0.0, 0, ("rep", 1.0), 1001.0,
                                          accepted=True),
                              g.on_report(0.0, 0.0, 0, ("rep", 1.0), 1002.0,
                                          accepted=True), g)[-1])(
                      ag.AgTrackGuard(mesh=None))) == (True, True, False))

        # -- the revert flag restores the 1z-bn build on that pair
        ag.WAIVER_NEWEST_MUST_BE_STOP = False
        try:
            reverted = pair(WALK, WALK).stationary()
        finally:
            ag.WAIVER_NEWEST_MUST_BE_STOP = True
        check("--waiver-walkstart-pair-stands restores it: the SAME pair "
              "waives again, so the arm is a real A/B and not a rewrite",
              reverted is True and pair(WALK, WALK).stationary() is False)

        # -- THE FOUR ARMS on a leg that opens with a DOUBLE walk-start
        A = dws(bs=False)                    # the 1z-bn build
        B = dws(bs=True)                     # shipped
        C = dws(bs=False, waiver=False)      # STATIONARY_WAIVER deleted (Q15)
        D = dws(bs=False, kinds=("0x0047", "0x003D", None))   # single opening
        check("KNOWN-BAD ARM -- the 1z-bn build re-pins a leg that opened on a "
              "double walk-start: DUE on a report ~1.46 s old with the waiver "
              "carrying it, the 1z-bl defect through the pair 1z-bn kept",
              A["code"] == ag.REPIN_DUE and A["why"] == "arrival-risk"
              and A["block"] is None and A["still"] is True
              and A["pair"] == (True, True),
              "age %.3f s" % A["age"])
        check("the SHIPPED build BLOCKS it by the freshness gate, with the "
              "risk still predicted -- the clause moves the precondition, "
              "not the prediction",
              B["code"] == ag.REPIN_BLOCKED and B["block"] == "stale-report"
              and B["risk"] is True and B["still"] is False)
        check("deleting the waiver answers identically: on this pair the "
              "clause and Q15's deletion are one object",
              (C["code"], C["block"], C["risk"])
              == (B["code"], B["block"], B["risk"]))
        check("and the SINGLE walk-start opening was already refused by 1z-bn "
              "-- the double one is the hole 1z-bn left",
              D["code"] == ag.REPIN_BLOCKED and D["block"] == "stale-report"
              and D["pair"] == (False, True))
        check("the harm the shipped build refuses is the refused pair's own "
              "class, RUN_SPEED * age, not the waiver's claimed zero",
              300.0 < ag.RUN_SPEED * A["age"] < 600.0,
              "RUN_SPEED * age = %.1f u" % (ag.RUN_SPEED * A["age"]))

        # -- the surviving branch still does the waiver's job
        S = dws(bs=True, kinds=("0x0047", "0x003D", "0x0047"))
        check("the surviving branch: a walk-start then a STOP at the same "
              "point is a body told to move that did not, the waiver still "
              "lifts the gate there, and the re-pin is DUE",
              S["still"] is True and S["code"] == ag.REPIN_DUE
              and S["block"] is None and S["pair"] == (True, False))
        check("section 9's walking arm is untouched -- a body 512 u between "
              "reports never reached the waiver and still does not",
              pair(WALK, WALK, dx=512.0).stationary() is False
              and pair(WALK, STOP, dx=512.0).stationary() is False)
    finally:
        ag.STATIONARY_WAIVER = True
        ag.WAIVER_WALKSTART_ENDS_STILL = True
        ag.WAIVER_NEWEST_MUST_BE_STOP = True

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
