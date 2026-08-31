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

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                    # noqa: E402
import agtrack_mirror as am      # noqa: E402
import agtrack_guard as ag       # noqa: E402
import authsrv                   # noqa: E402

# Floor from the 2026-08-30 green run: 49 checks, all unconditional.
LEDGER = checks.Ledger("agtrack guard: the derived pre-emit rule", floor=49)
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

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
