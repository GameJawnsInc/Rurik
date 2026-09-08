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
# +25 at MOVECODE-1z-ah, +20 at 1z-bn, +2 at 1z-bq, +17 at 1z-bs -- the
# stationary waiver's sections, 116 on their last green run; then the waiver
# was DELETED at MOVECODE-1z-bt (PLAN sec.7 Q15) and sections 9/14/15 became
# one section pinning the gate on age alone: 74 on the green run.  +7 at
# MOVECODE-1z-bv, a NEW section 14: the gate-2 branch driven through the
# guard with a mesh stub (every other fixture here is mesh=None, so that
# branch had never executed in a test) and the three re-pin arms over it,
# the third of which is the deleted waiver's own licence shape and goes RED
# on the pre-1z-bt build: 81 on the green run.  +8 at NPCTRACK-F14 (sec.15:
# the obstacle feed reaches both mirrors, and authsrv's provider reads the
# hostiles' client models): 89 on the 2026-09-06 green run.
# Each from a real green run, never from a guess.
LEDGER = checks.Ledger("agtrack guard: the derived pre-emit rule", floor=89)
check = checks.adopt_named(LEDGER)


class _OffMeshStub(object):
    """Gate 2's failure: the modelled sync copy is off the navmesh.  Same
    shape as test_agtrack_mirror's OffMeshStart -- the guard needs its own
    because every other fixture in this file passes mesh=None (MOVECODE-1z-bv).
    """

    def start_walkable(self, x, y):
        return False

    def path_len_ok(self, *a, **k):
        return True


class _OnMeshStub(object):
    """The vacuity control for the pair above: identical geometry, walkable."""

    def start_walkable(self, x, y):
        return True

    def path_len_ok(self, *a, **k):
        return True


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


    # ---- 9. MOVECODE-1z-bt: THE FRESHNESS GATE STANDS ON AGE ALONE ----------
    # The stationary waiver (1z-ah) and its two clauses (1z-bn, 1z-bs) are
    # DELETED -- PLAN sec.7 Q15, the owner's ruling, 2026-09-05.  They argued
    # that two coincident accepted reports MEASURE a still body, so a re-pin
    # onto it is harmless however old the report.  The corpus measured that
    # every re-pin the waiver ever carried (25 of 85) sat on {stop ->
    # walk-start} and rewound a walking body p50 366.6 u; that the branch it
    # kept was still in 151 of 151 windows and never met a re-pin want; and
    # that its own specimen was ~394 u downrange when it was called parked.
    # This section pins what replaced it: a 0x002C moves BOTH copies, so a
    # re-pin's harm is bounded by RUN_SPEED * report age and by nothing else.
    # The fixtures are the arc's own known-bad shapes, each BLOCKED by name.
    RA_REPORT = (10369.4169921875, 8282.3349609375)     # RUN-1zAB run A
    RA_DEST = (9849.4169921875, 8282.3349609375)
    RA_PLANE, RA_T0 = 29, 15.764
    RA_ETA = RA_T0 + 520.0 / 190.08
    RA_RISK = 18.074

    def run_a(walking=False, kinds=(False, True, False)):
        """RUN-1zAB run A's leg: three reports on ONE point (the capture's
        kinds, 0x003D / 0x0047 / 0x003D) while a 520 u backpedal lead at
        190.08 u/s walks the sync copy away.  Returns the guard at the risk
        tick.  (0x002B carries a MULTIPLIER of 288 u/s -- on_speed(288.0)
        would be 82,944 u/s, a defect two earlier fixtures carried.)"""
        g = ag.AgTrackGuard(mesh=None)
        g.on_placement(RA_REPORT[0], RA_REPORT[1], RA_PLANE, 11.0)
        pts = [RA_REPORT] * 3
        if walking:
            pts = [RA_REPORT, (RA_REPORT[0] - 512.0, RA_REPORT[1]),
                   (RA_REPORT[0] - 1024.0, RA_REPORT[1])]
        for t, p, stop in zip((11.892, 14.028, 15.763), pts, kinds):
            g.on_report(p[0], p[1], RA_PLANE, ("rep", "syn", stop), t,
                        accepted=True)
        g.on_speed(190.08 / 288.0, RA_T0)
        g.on_emit(0x29, RA_DEST[0], RA_DEST[1], RA_PLANE, RA_PLANE, RA_T0)
        return g

    _gsrc = open(ag.__file__, encoding="utf-8").read()
    check("the waiver and both clauses are GONE from the guard: no switch, no "
          "predicate, no report-kind bookkeeping (source lock)",
          not hasattr(ag, "STATIONARY_WAIVER")
          and not hasattr(ag, "WAIVER_WALKSTART_ENDS_STILL")
          and not hasattr(ag, "WAIVER_NEWEST_MUST_BE_STOP")
          and not hasattr(ag.AgTrackGuard, "stationary")
          and "def stationary" not in _gsrc
          and "prev_is_walkstart" not in _gsrc)
    check("and from authsrv's CLI: none of the three revert flags is an "
          "argument any more (a comment may still tell the history)",
          '"--no-repin-stationary-waiver"' not in AS_SRC
          and '"--waiver-walkstart-stands"' not in AS_SRC
          and '"--waiver-walkstart-pair-stands"' not in AS_SRC
          and "_ag_flag.STATIONARY_WAIVER" not in AS_SRC)
    flags = authsrv.capture_flags()
    check("and from the capture header, which no longer names them -- a run "
          "wanting the old behaviour reads it off the captures of that era",
          not any(k.startswith("agtrack_guard.") for k in flags))
    # The companion-module sweep is now VACUOUS -- the guard has no switch
    # left -- and nothing else exercises it, so it gets a positive control: a
    # bool planted in the module reaches the header, a non-bool does not.
    ag.PROBE_SWITCH, ag.PROBE_NUMBER = True, 3.0
    try:
        probed = authsrv.capture_flags()
    finally:
        del ag.PROBE_SWITCH, ag.PROBE_NUMBER
    check("...and the sweep that will record the NEXT switch still works: a "
          "bool planted in agtrack_guard reaches the header, a non-bool "
          "constant does not, and neither survives its removal",
          probed.get("agtrack_guard.PROBE_SWITCH") is True
          and "agtrack_guard.PROBE_NUMBER" not in probed
          and "agtrack_guard.PROBE_SWITCH" not in authsrv.capture_flags())
    check("the gate is a single age comparison, and nothing waives it "
          "(source lock)",
          "if now - self.client_pos_at > REPIN_MAX_REPORT_AGE:" in _gsrc
          and "stationary()" not in _gsrc)

    # -- RUN-1zAB run A: the case the waiver was built on
    on = run_a()
    risky, v = on.arrival_risk(RA_RISK)
    code, why = on.repin_state(RA_RISK)
    early = (on.mirror.sync.t_arrive - on._ms(RA_RISK)) / 1000.0
    check("RUN A: the guard still PREDICTS the snap EARLY -- the arrival is "
          "in the future at the risk tick, inside the 0.5 s horizon -- the "
          "predicate was never the problem",
          risky is True and v.code == am.SNAP and why == "arrival-risk"
          and 0.3 < early < 0.5,
          "arrival in %.3f s (the capture: 0.425 s)" % early)
    check("RUN A: and is BLOCKED, by the freshness gate, named -- three "
          "reports on one point buy nothing now",
          code == ag.REPIN_BLOCKED
          and on.repin_block_reason(RA_RISK) == "stale-report"
          and on.pos_rejects == 0 and on.last_repin_at is None,
          "report age %.3f s against the %.3f s ceiling"
          % (RA_RISK - on.client_pos_at, ag.REPIN_MAX_REPORT_AGE))
    check("the kinds no longer matter: three walk-starts answer the same",
          run_a(kinds=(False, False, False)).repin_block_reason(RA_RISK)
          == "stale-report")
    # THE ACCEPTED COST: with no retract, the arrival the waiver would have
    # pre-empted matures in the mirror, and the client's own test decides.
    fired, t = None, RA_RISK + 0.05
    while t <= RA_ETA + 0.5:
        r = on.tick(t)
        if r is not None:
            fired = r
            break
        t += 0.05
    check("the accepted cost, stated: the lead's arrival MATURES (no "
          "retract) and the client's own test decides -- 1z-bm measured this "
          "route lead-off (7 of 7 legs walked) and 1z-bo lead-on under the "
          "equivalent clause (0 of 7 rewound, separation 13.0 u)",
          fired is not None and on.mirror.sync.t_arrive == 0,
          "arrival verdict %s at t=%.2f (ETA %.2f)"
          % (getattr(fired, "code", fired), t, RA_ETA))

    # -- RUN-1zBL leg 4Q: the shape the waiver fired on 25 times
    BL_T0, BL_RISK = 100.0, 101.93
    g = ag.AgTrackGuard(mesh=None)
    g.on_placement(0.0, 0.0, 0, BL_T0 - 1.0)
    g.on_report(0.0, 0.0, 0, ("rep", "0x0047", True), BL_T0 - 0.2,
                accepted=True)
    g.on_report(0.0, 0.0, 0, ("rep", "0x003D", False), BL_T0, accepted=True)
    g.on_speed(1.0, BL_T0)                  # 0x002B: a MULTIPLIER of 288 u/s
    g.on_emit(0x29, 520.0, 0.0, 0, 0, BL_T0)
    check("RUN-1zBL's leg shape -- a walk-start on the previous stop, 1.93 s "
          "stale under a 520 u lead: the risk is predicted and the re-pin is "
          "BLOCKED, the 1z-bn behaviour RUN-1zBO confirmed on the client",
          g.arrival_risk(BL_RISK)[0] is True
          and g.repin_state(BL_RISK)[0] == ag.REPIN_BLOCKED
          and g.repin_block_reason(BL_RISK) == "stale-report")
    check("and the gate sits exactly at REPIN_MAX_REPORT_AGE: just under it "
          "the same leg is DUE, just over it BLOCKED -- the bound the waiver "
          "argued around is RUN_SPEED * age, the corpus's p50 366.6 u on "
          "this pair",
          g.repin_block_reason(BL_T0 + ag.REPIN_MAX_REPORT_AGE - 0.01) is None
          and g.repin_block_reason(BL_T0 + ag.REPIN_MAX_REPORT_AGE + 0.01)
          == "stale-report",
          "RUN_SPEED * age at the risk tick = %.1f u"
          % (ag.RUN_SPEED * (BL_RISK - g.client_pos_at)))

    # -- the double walk-start opening (1z-bs): the hole 1z-bn left, closed
    g = ag.AgTrackGuard(mesh=None)
    g.on_placement(0.0, 0.0, 0, 1999.0)
    for src, t in (("0x0047", 1999.8), ("0x003D", 2000.0), ("0x003D", 2000.04)):
        g.on_report(0.0, 0.0, 0, ("rep", src, src == "0x0047"), t,
                    accepted=True)
    g.on_speed(1.0, 2000.041)
    g.on_emit(0x29, 520.0, 0.0, 0, 0, 2000.041)
    check("a leg opening on a DOUBLE walk-start (a chord, or a heading change "
          "before the body leaves) is blocked the same way -- the 1z-bn build "
          "re-pinned it, and the corpus walks on from it 14 times in 87",
          g.arrival_risk(2001.5)[0] is True
          and g.repin_state(2001.5)[0] == ag.REPIN_BLOCKED
          and g.repin_block_reason(2001.5) == "stale-report")

    # -- THE ONE BEHAVIOURAL DELTA of the deletion: the branch 1z-bs kept.
    #    Every other fixture here has a walk-start as its newest report, which
    #    the last shipped clause already refused, so those checks are green on
    #    the 1z-bs build too.  This one is RED on it: the {walk-start -> stop}
    #    opening was DUE under 1z-bs (its section 15 pinned that) and is
    #    BLOCKED now -- the a-priori case the owner declined, with 151 of 151
    #    corpus windows still and zero re-pin wants behind it.
    g = ag.AgTrackGuard(mesh=None)
    g.on_placement(0.0, 0.0, 0, 2999.0)
    for src, t in (("0x0047", 2999.8), ("0x003D", 3000.0), ("0x0047", 3000.04)):
        g.on_report(0.0, 0.0, 0, ("rep", src, src == "0x0047"), t,
                    accepted=True)
    g.on_speed(1.0, 3000.041)
    g.on_emit(0x29, 520.0, 0.0, 0, 0, 3000.041)
    check("the deletion's one behavioural delta: a {walk-start -> stop} "
          "opening at one point -- the branch the last shipped clause still "
          "waived (DUE under 1z-bs) -- is now BLOCKED like the rest",
          g.arrival_risk(3001.5)[0] is True
          and g.repin_state(3001.5)[0] == ag.REPIN_BLOCKED
          and g.repin_block_reason(3001.5) == "stale-report")

    # -- a body WALKING the lead: never a candidate, still not one
    walk = run_a(walking=True)
    check("a body walking the lead (reports 512 u apart) tracks its sync "
          "copy: no snap is predicted and no re-pin is proposed",
          walk.arrival_risk(RA_RISK)[0] is False
          and walk.repin_state(RA_RISK)[0] == ag.REPIN_NONE)

    # -- the other preconditions, unchanged
    fresh = ag.AgTrackGuard(mesh=None)
    fresh.on_placement(0.0, 0.0, 0, 1000.0)
    fresh.on_report(5000.0, 0.0, 0, ("rep", "0x003D", False), 1000.0,
                    accepted=True)
    fresh.on_report(5000.0, 0.0, 0, ("rep", "0x003D", False), 1000.1,
                    accepted=True)
    check("a FRESH report is DUE whatever the pair looks like -- coincidence "
          "is no longer read at all",
          fresh._repin_code(1000.2) == ag.REPIN_DUE
          and fresh.repin_block_reason(1000.2) is None)
    rate = run_a()
    rate.on_report(RA_REPORT[0], RA_REPORT[1], RA_PLANE,
                   ("rep", "0x0047", True), RA_RISK - 0.1, accepted=True)
    rate.last_repin_at = RA_RISK - 0.1
    check("the RATE still blocks a fresh one",
          rate._repin_code(RA_RISK) == ag.REPIN_BLOCKED
          and rate.repin_block_reason(RA_RISK) == "rate")
    rej = run_a()
    rej.on_report(RA_REPORT[0], RA_REPORT[1], RA_PLANE, ("x",),
                  RA_RISK - 0.05, accepted=False)
    check("a REFUSED report since the last accept still blocks, by name, "
          "before the age is even asked",
          rej._repin_code(RA_RISK) == ag.REPIN_BLOCKED
          and rej.repin_block_reason(RA_RISK) == "rejects")
    check("and an unseeded guard names itself",
          ag.AgTrackGuard(mesh=None).repin_block_reason(1.0) == "unseeded")

    # -- the click glide survives: it feeds the ESTIMATE, not a waiver
    gl = run_a()
    gl.on_click(RA_REPORT[0] - 300.0, RA_REPORT[1], RA_PLANE, RA_RISK)
    est = gl._async_est(RA_RISK + 0.5)
    check("a click in flight still glides the async estimate toward its "
          "destination at the granted speed, capped there -- the budget "
          "term's input; nothing safety-bearing reads it now",
          est != gl.client_pos
          and RA_REPORT[0] - 300.0 <= est[0] < RA_REPORT[0]
          and abs(est[1] - RA_REPORT[1]) < 1e-9,
          "estimate %.1f u along a 300 u click after 0.5 s"
          % (RA_REPORT[0] - est[0]))
    gl.on_report(RA_REPORT[0] - 100.0, RA_REPORT[1], RA_PLANE,
                 ("rep", "0x003D", False), RA_RISK + 0.6, accepted=True)
    check("and any report ends the glide",
          gl.async_dest is None
          and gl._async_est(RA_RISK + 1.0) == gl.client_pos)

    # -- the row carries the reason (1z-ag replayed a capture for want
    #    of it, and published two wrong explanations first)
    check("the telemetry row names the blocker, so no later session has "
          "to replay a capture to find out which gate refused",
          "blocked_by=_agtrack_guard_call(" in AS_SRC
          and '"repin_block_reason", now' in AS_SRC)

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

    # ---- 14. MOVECODE-1z-bv: the gate-2 branch, driven THROUGH the guard --
    # Every fixture above this line builds AgTrackGuard(mesh=None), so gate 2
    # -- `mesh.start_walkable(a)` -- is None in all of them and the guard's
    # own `gate2-offmesh` branch has never been executed by a test.  It is
    # covered one layer down (test_agtrack_mirror sec.10b, both tolerance
    # arms), which is why sec.1z-bo.4's open item read "gate2-offmesh
    # exposure -- untested".
    #
    # WHAT THAT ITEM WAS REALLY ASKING, and why it belongs here.  The waiver
    # deleted at 1z-bt licensed exactly one thing: a re-pin whose newest
    # accepted report was PAST the freshness gate AND whose last two reports
    # COINCIDED.  So the deletion can only have removed a fire that was both.
    # `review/gate2census.py` asked the corpus and got zero: all 17 gate-2
    # fires ever sent were FRESH (age 0.000-0.149 s, gate 0.347) with their
    # reports ~100 u apart, and all 25 waiver-carried fires are arrival-risk
    # or budget-red.  That is a census, and a census cannot go red when
    # somebody re-introduces the licence.  These checks can.
    _g2 = _OffMeshStub()
    g = ag.AgTrackGuard(mesh=_g2)
    g.on_placement(0.0, 0.0, 0, 1000.0)
    g.on_report(100.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.1)
    v = g.pre_emit(100.0, 0.0, 0, 0, now=1000.2)
    check("gate 2 is REACHABLE through the guard: an off-mesh sync copy "
          "vetoes as gate2-offmesh, not gate1-red",
          v.code == ag.VETO and v.why == "gate2-offmesh")
    _mv = g.mirror.predict(g._ms(1000.2), g._async_est(1000.2))
    check("and it is genuinely gate 2 that failed -- gate 1 PASSED at "
          "100 u, well under the 299.33 u snap line (localises the branch: "
          "a green conjunct here would let a gate-1 fixture masquerade)",
          _mv.code == am.SNAP and _mv.gate1 is True and _mv.gate2 is False
          and abs(_mv.gate1_sep - 100.0) < 1e-9)
    # VACUITY GUARD: the same geometry on a walkable mesh must NOT produce it,
    # or the verdict is coming from the shape and the stub is decorative.
    g_ok = ag.AgTrackGuard(mesh=_OnMeshStub())
    g_ok.on_placement(0.0, 0.0, 0, 1000.0)
    g_ok.on_report(100.0, 0.0, 0, ("head", 1.0, 0.0, 1), now=1000.1)
    check("vacuity: the IDENTICAL shape on a walkable mesh is not a gate-2 "
          "veto -- the mesh is what drives it",
          g_ok.pre_emit(100.0, 0.0, 0, 0, now=1000.2).why != "gate2-offmesh")

    # The three re-pin arms over a gate-2 want.  Arm 3 is the regression
    # guard: it is the exact shape the deleted waiver licensed, and it went
    # DUE on the 1z-bs build.
    check("a gate-2 want on a FRESH report MATURES -- this is the corpus's "
          "17 fires, every one of them fresh",
          g.repin_state(1000.2) == (ag.REPIN_DUE, "gate2-offmesh")
          and g.repin_block_reason(1000.2) is None)
    _late = 1000.1 + ag.REPIN_MAX_REPORT_AGE + 0.05
    check("a gate-2 want on a STALE report is BLOCKED, and the blocker is "
          "named: the freshness gate governs gate 2 like every other class",
          g.repin_state(_late) == (ag.REPIN_BLOCKED, "gate2-offmesh")
          and g.repin_block_reason(_late) == "stale-report")
    # THE PAIR'S KINDS ARE LOAD-BEARING AND THE FIRST DRAFT MISSED IT.
    # `sig` is ("rep", source, is_stop) at the authsrv call site.  This
    # fixture first used two walk-starts -- and the 1z-bs build REFUSES that
    # pair on its own (WAIVER_NEWEST_MUST_BE_STOP: the newest member being a
    # walk-start ends the waiver), so the check passed on the broken build
    # and was measuring nothing.  Running the old module found it.  The shape
    # the waiver actually licensed is {walk-start -> STOP}, 1z-bs's KEPT
    # branch, and it is the one the deletion removed.
    #
    # VERIFIED against agtrack_guard.py as of 5bdd933 (1z-bs, the last commit
    # carrying the waiver): this exact shape gives ("due", "gate2-offmesh")
    # with stationary() True there, against ("blocked", ...) here.
    g2c = ag.AgTrackGuard(mesh=_g2)
    g2c.on_placement(0.0, 0.0, 0, 1000.0)
    g2c.on_report(100.0, 0.0, 0, ("rep", "kbd", False), now=1000.05)  # walk-start
    g2c.on_report(100.0, 0.0, 0, ("rep", "kbd", True), now=1000.1)    # STOP
    check("THE WAIVER'S OLD LICENCE, on a gate-2 want: stale AND the last "
          "two reports coincident (0.0 u) AND the newest a STOP -- the "
          "branch 1z-bs KEPT -- is STILL blocked. This is ('due', "
          "'gate2-offmesh') on the pre-1z-bt build, checked, not assumed",
          g2c.repin_state(_late) == (ag.REPIN_BLOCKED, "gate2-offmesh")
          and g2c.repin_block_reason(_late) == "stale-report")
    check("and the same coincident pair FRESH still matures -- so the block "
          "above is the AGE, not the pair (the clause 1z-bn refused is gone "
          "too, and neither is doing the work here)",
          g2c.repin_state(1000.2) == (ag.REPIN_DUE, "gate2-offmesh"))

    # ---- 15. NPCTRACK-F14: the obstacle feed reaches BOTH mirrors ----------
    # The server hands the guard a provider in SECONDS; the mirrors ask in
    # their own ms clock.  A parked hostile 75 u ahead of a 520 u lead must
    # sidestep the mirror AND the twin (a sidestep is a client behaviour in
    # both worlds), and the authsrv provider must read a hostile's client
    # model, not its server position.
    gf = ag.AgTrackGuard()
    gf.on_placement(0.0, 0.0, 0, 2000.0)
    seen = []

    def _prov(now_s):
        seen.append(now_s)
        return [(75.0, 0.0, 0.0, 0.0)]
    gf.set_obstacles(_prov)
    gf.on_emit(0x29, 520.0, 0.0, 0, 0, 2000.5)
    check("F14: the provider is asked in server SECONDS (the guard's epoch + "
          "ms), at the emit's own instant", seen and abs(seen[-1] - 2000.5) < 1e-6)
    check("F14: the mirror sidestepped the parked hostile at the setter",
          gf.mirror.sync.is_waypoint and abs(gf.mirror.sync.dest[1] - 90.0) < 1e-6)
    check("F14: and so did the twin -- the no-resets world is the same client",
          gf.twin.sync.is_waypoint)
    gf.set_obstacles(None)
    gf.on_emit(0x29, 520.0, 0.0, 0, 0, 2001.0)
    check("F14: set_obstacles(None) detaches both -- the next grant walks "
          "straight", not gf.mirror.sync.is_waypoint and not gf.twin.sync.is_waypoint)
    check("F14 ships ON with its revert flag, recorded in the capture header",
          authsrv.MIRROR_AVOID is True and "--no-mirror-avoid" in AS_SRC
          and authsrv.capture_flags().get("MIRROR_AVOID") is True)
    # the authsrv provider: a hostile with a client model answers at the
    # model's position and velocity; one without answers at its server
    # position, standing; the player is never an obstacle
    st = {"agents": {authsrv.PLAYER_AGENT_ID: {"pos": (0.0, 0.0)},
                     10: {"pos": (900.0, 0.0), "plane": 0},
                     11: {"pos": (5.0, 6.0)}}}
    sa = authsrv._npc_model(st["agents"][10], 0.0)
    sa.bake_grant(612.0, 0.0, 0, 0, 0)              # walking -x from 900 at 288
    st["agents"][10]["cmodel_clock"] = 0.5
    obs = authsrv._npc_obstacles(st)(123.0)
    by = {(round(o[0]), round(o[1])): o for o in obs}
    check("authsrv._npc_obstacles: a modelled hostile answers at its client "
          "model's dead-reckoned point (900 - 144) with its velocity (-288, 0)",
          (756, 0) in by and abs(by[(756, 0)][2] + 288.0) < 1e-6)
    check("... an unmodelled agent answers at its server position, standing",
          (5, 6) in by and by[(5, 6)][2] == 0.0 and by[(5, 6)][3] == 0.0)
    check("... and the player is never an obstacle to itself",
          (0, 0) not in by and len(obs) == 2)

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
