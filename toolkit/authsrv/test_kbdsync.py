#!/usr/bin/env python3
"""MOVECODE-1z-t (KBD_SYNC): keep the client's WORLD-0 copy near the body.

What this file is for. The arc's other movement tests pin the arms that
already existed; this one pins the behaviour that ships by default from
2026-09-03 and the derivation each of its three constants came from. The
VERDICT on the behaviour is an operator run with `agenttap.py --agents 1` --
a test written against my own hypothesis is two of our components agreeing
(CLAUDE.md, and [[operator-symptoms-close-on-runs]]). What this file CAN
refuse to let rot:

  * the lead's LENGTH is ours and its DIRECTION is the client's -- the
    distinction that separates this from `--heading-grant`'s graveyard, where
    the ray was aimed from `state["pos"]`, a model belief;
  * the band refusal (refuse, never clamp) and the fallback it degrades to;
  * the composition -- D1_LEAD owns the slot when both are set, so a
    --d1-lead run still measures REALFIX-A2 and not a mixture;
  * the three terms' independent off switches, so ONE run can convict ONE
    term (sec.29's lesson: shipping two defaults into one run convicts the
    pair and clears neither);
  * the burst ORDER, which is retail's own grammar and not a preference:
    0x0025 then 0x002B then 0x0029, with 0x0029 last in every shape that
    contains it (3,023 of 3,071 live bursts, zero counter-examples);
  * and the registered prediction, so the run that closes this cannot be
    rationalised into agreeing with it afterwards.

The stop echo's own wire shape is pinned next door, in test_position_trust
section "THE STOP ARM, BOTH REGIMES", because that is where the arm it
replaced was pinned and a guard is worth more sitting where the thing it
guards against used to live.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))

import authsrv              # noqa: E402
import checks               # noqa: E402
# The arm extractor is test_position_trust's and is IMPORTED rather than
# copied: it re-parses authsrv.py on every call and executes the server's own
# bytes, and two copies of a subtle extractor drifting apart is exactly the
# failure this repo keeps recording. Importing is safe -- that file guards its
# main() behind __name__.
from test_position_trust import receive_arm, Sent, FakeRec   # noqa: E402

# Floor read off the first green run of this file, per CLAUDE.md -- never
# guessed from a head-count, which this arc has got wrong three times.
# 33 at 1z-t; +27 at 1z-y (sections 10-11: the held heading, the lead kill).
LEDGER = checks.Ledger("MOVECODE-1z-t, the keyboard world-0 sync", floor=60)
check = checks.adopt(LEDGER)

SRC = open(authsrv.__file__, encoding="utf-8").read()


def drive_heading(values, *, kbd_sync=True, lead=True, speed=True,
                  d1=False, state=None, since=10.0, hold=True, kill=True):
    """One 0x003D through the SHIPPED heading arm. Returns (state, wire).
    `since` is the age of the last grant when the report arrives: 10 s
    clears the rate floor, 0.1 s is refused `heading-rate` (1z-y)."""
    st = state if state is not None else {
        "pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0}
    w, r = Sent(st), FakeRec()
    arm = receive_arm("GAME_CMSG_TURN_TO_DIRECTION",
                      ("values", "state", "rec", "send", "conn_id"))
    saved = (authsrv.ZERO_LEAD, authsrv.KBD_SYNC, authsrv.KBD_SYNC_LEAD_ON,
             authsrv.KBD_SYNC_SPEED_ON, authsrv.D1_LEAD, authsrv.PLANE_CARRY,
             authsrv.KBD_SYNC_HOLD, authsrv.KBD_LEAD_KILL)
    authsrv.ZERO_LEAD = True
    authsrv.KBD_SYNC, authsrv.D1_LEAD = kbd_sync, d1
    authsrv.KBD_SYNC_LEAD_ON, authsrv.KBD_SYNC_SPEED_ON = lead, speed
    authsrv.KBD_SYNC_HOLD, authsrv.KBD_LEAD_KILL = hold, kill
    authsrv.PLANE_CARRY = False
    try:
        import time as _t
        w.now = _t.time() - since
        st["grant_at"] = w.now
        st["_rec"] = r
        arm(values, st, r, w, 0)
    finally:
        (authsrv.ZERO_LEAD, authsrv.KBD_SYNC, authsrv.KBD_SYNC_LEAD_ON,
         authsrv.KBD_SYNC_SPEED_ON, authsrv.D1_LEAD,
         authsrv.PLANE_CARRY, authsrv.KBD_SYNC_HOLD,
         authsrv.KBD_LEAD_KILL) = saved
    return st, w


# A report whose vec2 is in the verified proposal band, pointing +x.
REPORT = [1, [1000.5, 2000.25], 7, [766.0, 0.0], 1]


def main():
    import math

    print("1. the constants, and where each number came from")
    # 1z-u (2026-09-03 evening): this check used to pin all four ON. The
    # operator's first ordinary session convicted term 1 -- a lead that
    # matures unanswered (a rate-refused re-aim is DROPPED) makes the client's
    # arrival reconcile snap the body 498 u and shut the AgTrack fence -- and
    # two skeptic lanes then refuted the correction built for it. So the lead
    # is OPT-IN (--kbd-lead) and the pin is the SPLIT: the two additive terms
    # ship, the lead does not, until 1z-u's (a)/(b) land with their own tests.
    check(authsrv.KBD_SYNC is True and authsrv.KBD_SYNC_LEAD_ON is False
          and authsrv.KBD_SYNC_SPEED_ON is True
          and authsrv.KBD_SYNC_STOP_ON is True,
          "KBD_SYNC ships with the family rate and the stop echo ON and the "
          "LEAD OFF -- one run convicted one term, so that term is out",
          "a lead defaulting ON after the 08:46 session would be shipping a "
          "refuted arm; a stop echo or family rate defaulting OFF would be "
          "withholding two additive terms nothing has convicted")
    check("--kbd-lead" in SRC and "--no-kbd-lead" in SRC
          and "bool(a.kbd_lead) and not a.no_kbd_lead" in SRC,
          "the lead is opt-in through --kbd-lead, and --no-kbd-lead still "
          "parses and wins, so pre-1z-u runsheets keep their meaning",
          "a runsheet that said --no-kbd-lead must not silently start "
          "meaning something else")
    check(authsrv.KBD_SYNC_LEAD == 520.0,
          "the lead is 520 u -- the client's OWN 0x003D distance trigger, "
          "held-heading chord p95 513.8 / p99 515.1 u",
          "NOT tuned: the lead must cover the most ground the body can "
          "travel between two re-aims or the arrival tick +0x48 fires and "
          "the copy parks. Corroborates REALFIX-W2's ~515 u from a "
          "different corpus. D1_LEAD's 766 is the client's PROPOSED "
          "endpoint, 1.49x the trigger distance, and overshoots")
    check(authsrv.KBD_SYNC_LEAD > 288.0 * 1.5,
          "and it exceeds one grant-interval of travel by a real margin",
          "at 288 u/s a 0.5 s interval is 144 u; a lead under the report "
          "chord is the shipped defect with a smaller number")
    check(authsrv.FAMILY_RATE[4] == 0.66 and authsrv.FAMILY_RATE[1] == 1.00
          and abs(0.66 * 288.0 - 190.08) < 1e-9,
          "term 2's operand is the SAME corpus table the watchdog uses, and "
          "0.66 x 288 = 190.08 is the speed the drawn body was measured at",
          "the 2026-09-02 tap: the drawn body runs at {190.1, 288.0} u/s "
          "while world-0 has only ever run at 288.0, because the player is "
          "sent no 0x002B at all")

    print("\n2. kbd_lead_dest: the length is OURS, the direction is THEIRS")
    f = authsrv.kbd_lead_dest
    d, s = f([100.0, 200.0], [766.0, 0.0])
    check(s == "kbd" and d == [620.0, 200.0],
          "axis-aligned: dest = reported + 520 * unit(vec2)",
          f"{d} -- 100 + 520 = 620, and the y is untouched")
    d2, s2 = f([100.0, 200.0], [0.0, -766.0])
    check(s2 == "kbd" and d2 == [100.0, -320.0],
          "and the sign of the client's own vector is carried",
          f"{d2}")
    d3, s3 = f([0.0, 0.0], [383.0, 383.0 * math.sqrt(3.0)])
    check(s3 == "kbd" and abs(math.hypot(*d3) - 520.0) < 1e-6,
          "DIAGONAL: the lead's LENGTH is exactly 520 u regardless of the "
          "vec2's own magnitude -- this is the whole difference from "
          "d1_lead_dest, which carries the client's 766 u endpoint",
          f"{d3} -> |d| = {math.hypot(*d3):.6f}. A lead that inherited the "
          f"vec2's length would be D1 with extra steps")
    check(abs(math.hypot(*f([0.0, 0.0], [700.0, 0.0])[0]) - 520.0) < 1e-6
          and abs(math.hypot(*f([0.0, 0.0], [768.0, 0.0])[0]) - 520.0) < 1e-6,
          "and it is 520 at BOTH ends of the accepted band",
          "the length must not vary with the client's own magnitude, or the "
          "lead is a function of a number we did not choose")

    print("\n3. refuse, do not clamp -- the band and the fallback")
    for bad, why in (([5.0, 0.0], "mid-magnitude, below the floor"),
                     ([2000.0, 0.0], "above the ceiling"),
                     ([0.0, 0.0], "degenerate"),
                     ([float("inf"), 0.0], "non-finite"),
                     ("garbage", "malformed"),
                     ([1.0], "short")):
        dd, ss = f([100.0, 200.0], bad)
        check(ss == "fallback" and dd == [100.0, 200.0],
              f"{why}: falls back to the REPORT, and says so in `src`",
              f"{dd}, {ss} -- a clamped wrong vector is still a wrong "
              f"destination, and a short lead nobody registered is still a "
              f"policy nobody registered. The row records which")
    check(authsrv.D1_VEC2_FLOOR == 700.0 and authsrv.D1_VEC2_CEILING == 769.0,
          "and the band is d1_lead_dest's own, REUSED not restated",
          "two copies of the band would drift; the census behind it "
          "(1 of 15,285 c2s rows outside) covers both callers")

    print("\n4. composition -- D1_LEAD owns the slot when both are set")
    _, w_d1 = drive_heading(REPORT, kbd_sync=True, d1=True)
    labels_d1 = [row[2] for row in w_d1.rows]
    check(any("D1 LEAD" in x for x in labels_d1)
          and not any("KBD LEAD" in x for x in labels_d1),
          "with --d1-lead ON the wire carries D1's 766 u endpoint and NOT "
          "1z-t's 520 -- a --d1-lead run still measures REALFIX-A2",
          f"{labels_d1} -- D1_LEAD is the explicit experiment arm and it "
          f"carries its own registered predictions; a mixture would "
          f"invalidate both registrations at once")
    _, w_ks = drive_heading(REPORT, kbd_sync=True, d1=False)
    labels_ks = [row[2] for row in w_ks.rows]
    check(any("KBD LEAD" in x for x in labels_ks)
          and not any("D1 LEAD" in x for x in labels_ks),
          "and with 1z-t alone the wire carries KBD LEAD",
          f"{labels_ks}")

    print("\n5. the wire, term by term")
    grants = w_ks.of(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT)
    check(len(grants) == 1
          and abs(grants[0][1][1][0] - (1000.5 + 520.0)) < 1e-6
          and abs(grants[0][1][1][1] - 2000.25) < 1e-6,
          "TERM 1: exactly one 0x0029, led 520 u along the client's own "
          "heading FROM THE REPORT IN HAND",
          f"{grants} -- anchored on `reported`, never state['pos']: a ray "
          f"from the model's belief aims the lead from somewhere the client "
          f"is not, which is --heading-grant's epitaph (R2-1)")
    speeds = w_ks.of(authsrv.GAME_SMSG_AGENT_UPDATE_SPEED)
    check(len(speeds) == 1 and speeds[0][1][1] == 1.0
          and speeds[0][1][2] == 1
          and "KBD SPEED-TRUTH" in speeds[0][2],
          "TERM 2: one 0x002B carrying FAMILY_RATE[mt] and the report's own "
          "movementType, labelled with its arm",
          f"{speeds} -- the label is how a capture says which of the two "
          f"policies that send this exact message produced it (REALFIX-Q8)")
    order = [r[0] for r in w_ks.rows]
    i25 = order.index(authsrv.GAME_SMSG_AGENT_MOVE_DIRECTION)
    i2b = order.index(authsrv.GAME_SMSG_AGENT_UPDATE_SPEED)
    i29 = order.index(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT)
    check(i25 < i2b < i29,
          "BURST ORDER: 0x0025 then 0x002B then 0x0029, with the grant LAST "
          "-- retail's own grammar, not a preference",
          f"{[row[2] for row in w_ks.rows]} -- 0x0029 is last in every live "
          f"shape that contains it and 0x0025 precedes 0x002B: 3,023 of "
          f"3,071 bursts, zero counter-examples. Out of order, the client "
          f"bakes the leg before the family rate reaches +0x60")

    print("\n6. each term reverts on its own -- ONE run convicts ONE term")
    _, w_nolead = drive_heading(REPORT, lead=False)
    lb = [row[2] for row in w_nolead.rows]
    check(not any("KBD LEAD" in x for x in lb)
          and any("ZERO LEAD" in x for x in lb)
          and any("KBD SPEED-TRUTH" in x for x in lb),
          "--no-kbd-lead: the grant returns to the reported point verbatim "
          "while term 2 stays live",
          f"{lb}")
    _, w_nospeed = drive_heading(REPORT, speed=False)
    ls = [row[2] for row in w_nospeed.rows]
    check(not any("SPEED-TRUTH" in x for x in ls)
          and any("KBD LEAD" in x for x in ls),
          "--no-kbd-speed-truth: no 0x002B while term 1 stays live",
          f"{ls}")
    _, w_off = drive_heading(REPORT, kbd_sync=False)
    lo = [row[2] for row in w_off.rows]
    check(not any("KBD" in x for x in lo)
          and any("ZERO LEAD" in x for x in lo)
          and w_off.of(authsrv.GAME_SMSG_AGENT_UPDATE_SPEED) == [],
          "--legacy-kbd-sync: the pre-1z-t wire exactly -- the reported "
          "point, and no player 0x002B at all",
          f"{lo} -- if this is not byte-identical to the old server the "
          f"flag is not a revert, and the run that convicts 1z-t has no "
          f"control to be compared against")

    print("\n7. the telemetry a later session scores this from")
    rows = [e for e in w_ks.state.get("_rec_rows", [])] if False else None
    _, w_t = drive_heading(REPORT)
    check(any(row[2].startswith("KBD LEAD (") and " from (" in row[2]
              for row in w_t.rows),
          "the wire label names the point AND its anchor, D1's own shape",
          f"{[r[2] for r in w_t.rows]} -- a label carrying only the "
          f"destination cannot be checked against the report that produced "
          f"it without re-deriving the policy")

    print("\n8. source locks")
    check(SRC.count("a2_dest, a2_src = kbd_lead_dest(") == 1,
          "ONE dest-computation site routes through kbd_lead_dest",
          "a second computation site is two formulas for one wire point")
    i_d1 = SRC.index("a2_dest, a2_src = d1_lead_dest(")
    i_kbd = SRC.index("a2_dest, a2_src = kbd_lead_dest(")
    i_verdict = SRC.index('rec.event("grant_verdict"', i_d1)
    check(i_d1 < i_kbd < i_verdict,
          "1z-t's branch is the elif of D1's, and BOTH sit above the "
          "verdict row so the row records the point that goes out",
          "below the verdict row, the row logs `reported` while the wire "
          "carries the lead -- the unattributable-capture defect (Q8)")
    check('if a2_src == "kbd":' in SRC[i_kbd:i_kbd + 400],
          "and the clip is gated on a REAL kbd lead, never on a fallback",
          "clipping a fallback second-guesses the client's own reported "
          "point, which is the one point in the exchange we did not choose")
    check(SRC.count("KBD_SYNC = False") == 1
          and SRC.count("global KBD_SYNC, KBD_SYNC_LEAD_ON") == 1,
          "main() rebinds the flags through ONE declared global statement",
          "an unpinned rebind survives every test while the console claims "
          "an arm the server is not running -- the 2026-08-25 lesson")
    check("--legacy-kbd-sync" in SRC and "--no-kbd-lead" in SRC
          and "--no-kbd-speed-truth" in SRC and "--no-kbd-stop-echo" in SRC,
          "all four flags are registered",
          "a behaviour with no revert arm is an assertion")
    # NAME THE ARMS, DO NOT COUNT THE STRING. A bare count of
    # '"AGENT_UPDATE_SPEED(player, 1.0, type 9) "' reads 3, not 2, because the
    # A2 ETA WATCHDOG sends the same sentinel from a third site -- so a count
    # here would have been a lock that failed for a reason unrelated to what
    # it guards. Each arm carries its own bracket tag precisely so a capture
    # (and this check) can tell the three apart.
    check(SRC.count("[kbd-stop]") == 1 and SRC.count("[a2-stop]") == 1
          and SRC.count("[a2-watchdog]") >= 1
          and SRC.count("KBD STOP-ECHO") == 1,
          "term 3's pair exists and is TAGGED distinctly from A2's stop and "
          "from the watchdog -- three senders of [1.0, 9], three labels",
          "the bytes are identical by design, so the label is the only "
          "thing that tells a later session which policy produced a row "
          "(REALFIX-Q8). The stop echo's wire SHAPE is pinned in "
          "test_position_trust, where the arm it replaced was pinned")

    print("\n9. the registered prediction -- stated before the run")
    check(True,
          "REGISTERED: on the operator's next keyboard walk, agenttap.py "
          "--agents 1 reads world-0 vs world-1 p50 under 150 u (shipped "
          "baseline: p50 237 u, p90 431 u, max 516 u on "
          "agenttap-20260902T213401)",
          "the offline counterfactual against the client's own world-0 "
          "track says p50 0 / p90 13 / max 86 u, and the model's own "
          "validation error is p90 16 u. REFUTED IF the p50 stays above "
          "200 u, or if the operator reports a NEW visible warp class the "
          "shipped default did not have. The 2026-09-02 tap is the "
          "before-picture and needs no new run to compare against")
    check(True,
          "AND THE RUN MUST DRIVE W/S, NOT A/D: in Guild Wars A and D TURN "
          "IN PLACE, and all four A/D legs of the 2026-09-02 kite travelled "
          "0 u",
          "a scorer that counts turn legs as movement measures a frozen "
          "residual and calls it drift; Q/E are the strafe keys")


    print("\n10. MOVECODE-1z-y: a refused re-aim is HELD, and a press or a click "
          "KILLS an in-flight lead")
    import inspect
    import time as _t
    MOVE = authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT
    check(authsrv.KBD_SYNC_HOLD is True and authsrv.KBD_LEAD_KILL is True
          and authsrv.HEADING_HOLD_MAX_AGE == authsrv.GRANT_PENDING_MAX_AGE,
          "both gates ship ON, and the held heading expires exactly when a "
          "held click does",
          "one expiry for the two holds; a second constant is a second place "
          "to disagree")
    check("--no-kbd-hold" in SRC and "--no-kbd-lead-kill" in SRC
          and "KBD_SYNC_HOLD = not a.no_kbd_hold" in SRC
          and "KBD_LEAD_KILL = not a.no_kbd_lead_kill" in SRC
          and SRC.count("global KBD_SYNC_HOLD, KBD_LEAD_KILL") == 1,
          "each gate has its revert flag, rebound through a declared global",
          "a behaviour with no revert arm is an assertion")

    # (a1) HOLD: a report refused `heading-rate` stores the grant the arm
    # would have sent -- the LEAD from the report's own heading.
    st, w = drive_heading(REPORT, lead=True, since=0.1)
    hold = st.get("heading_hold")
    check(not w.of(MOVE) and hold is not None
          and hold["point"] == [1520.5, 2000.25] and hold["a2_src"] == "kbd"
          and hold["plane"] == 7 and hold["plane_cur"] == 7
          and hold["reported"] == (1000.5, 2000.25) and hold["moving"] == 1,
          "a rate-refused report sends no 0x0029 and is HELD with the lead "
          "its own heading names, plane words as the arm computed them",
          f"hold={hold}")
    rec, w2 = FakeRec(), Sent(st)
    t_floor = st["grant_at"] + authsrv.GRANT_MIN_INTERVAL
    check(authsrv.heading_hold_tick(w2, st, 0, rec, now=t_floor - 0.05) is False
          and not w2.rows and st.get("heading_hold") is not None,
          "inside the floor the hold is kept and nothing is sent",
          "the flush is the coalescing half of the rate limit, not a bypass")
    fired = authsrv.heading_hold_tick(w2, st, 0, rec, now=t_floor + 0.01)
    moves = w2.of(MOVE)
    rows = [x for x in rec.events if x.get("kind") == "grant_verdict"]
    check(fired is True and len(moves) == 1
          and moves[0][1] == [1, [1520.5, 2000.25], 7, 7]
          and "HELD HEADING" in moves[0][2] and "[kbd]" in moves[0][2],
          "at the floor the HELD grant goes out with the words computed at "
          "refusal",
          f"sent {moves}")
    check(len(rows) == 1 and rows[0]["fired"] is True
          and rows[0]["reason"] == "deferred-heading"
          and rows[0]["deferred"] is True and rows[0]["arm"] == "zero-lead"
          and rows[0]["lead_src"] == "kbd" and rows[0]["plane_cur"] == 7,
          "the row is a DEFERRED fire on the heading arm, reason "
          "deferred-heading, so grantsim's replay filter (zero-lead / "
          "heading-rate) leaves it alone",
          f"rows {rows}")
    speeds = w2.of(authsrv.GAME_SMSG_AGENT_UPDATE_SPEED)
    check(st.get("heading_hold") is None and st.get("kbd_leg") is not None
          and st["kbd_leg"]["dest"] == (1520.5, 2000.25)
          and st["zl_last_grant_plane"] == 7
          and (not speeds or w2.rows.index(speeds[0]) < w2.rows.index(moves[0])),
          "the hold is consumed, the keyboard leg record is armed from the "
          "held send, the plane slot advances, and any family row precedes "
          "the move",
          f"kbd_leg={st.get('kbd_leg')} speeds={speeds}")
    # newest wins: a second refused report overwrites; a fired one clears
    st, w = drive_heading(REPORT, since=0.1)
    REPORT_UP = [1, [1010.5, 2000.25], 7, [0.0, 766.0], 1]
    st, w = drive_heading(REPORT_UP, since=0.1, state=st)
    check(st["heading_hold"]["point"] == [1010.5, 2520.25],
          "a second refused report REPLACES the hold (newest wins, never a "
          "queue)", f"{st['heading_hold']['point']}")
    st, w = drive_heading(REPORT, since=10.0, state=st)
    check(st.get("heading_hold") is None and len(w.of(MOVE)) == 1,
          "a fired report clears the hold", f"{st.get('heading_hold')}")
    # zero-lead (lead OFF): the held point is the report itself
    st, w = drive_heading(REPORT, lead=False, since=0.1)
    check(st["heading_hold"]["point"] == [1000.5, 2000.25]
          and st["heading_hold"]["a2_src"] is None,
          "under zero-lead the hold is the REPORT: the copy gets the freshest "
          "anchor at the floor instead of waiting out a silent interval",
          f"{st['heading_hold']}")
    # expiry, stop, action hold
    st, w = drive_heading(REPORT, since=0.1)
    st["heading_hold"]["at"] -= 5.0
    rec = FakeRec()
    check(authsrv.heading_hold_tick(Sent(st), st, 0, rec,
                                    now=_t.time() + 1.0) is False
          and st.get("heading_hold") is None
          and rec.events and rec.events[-1]["reason"] == "heading-hold-expired",
          "a hold older than the expiry is dropped with a row",
          f"{rec.events}")
    st, w = drive_heading(REPORT, since=0.1)
    st["kbd_moving_at"] = None
    rec = FakeRec()
    check(authsrv.heading_hold_tick(Sent(st), st, 0, rec,
                                    now=st["grant_at"] + 1.0) is False
          and st.get("heading_hold") is None
          and rec.events[-1]["reason"] == "heading-hold-stopped",
          "a hold whose body has stopped is dropped -- never a walk order for "
          "a parked body", f"{rec.events}")
    st, w = drive_heading(REPORT, since=0.1)
    st["action_hold"] = 1
    saved_gdh = authsrv.GRANT_DURING_HOLD
    authsrv.GRANT_DURING_HOLD = False
    try:
        rec = FakeRec()
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            r_ah = authsrv.heading_hold_tick(Sent(st), st, 0, rec,
                                             now=st["grant_at"] + 1.0)
        check(r_ah is False and st.get("heading_hold") is None
              and rec.events[-1]["reason"] == "heading-hold-action-hold",
              "R11's action hold guards the held send as it guards the arm's",
              f"{rec.events}")
    finally:
        authsrv.GRANT_DURING_HOLD = saved_gdh
    # known-bad arm
    st, w = drive_heading(REPORT, since=0.1, hold=False)
    check(st.get("heading_hold") is None and not w.of(MOVE),
          "KNOWN-BAD ARM (--no-kbd-hold): the refused report is dropped, "
          "nothing held, nothing sent -- the 08:46 shape",
          f"{st.get('heading_hold')}")

    # (a2) KILL: a fired lead arms the keyboard leg record; a press or a
    # click ends it with a zero-lead grant at the modelled body.
    st, w = drive_heading(REPORT, lead=True, since=10.0)
    leg = st.get("kbd_leg")
    check(leg is not None and leg["dest"] == (1520.5, 2000.25)
          and leg["speed"] == 288.0 and leg["plane"] == 7
          and any(x.get("kind") == "kbd_leg" and x.get("act") == "arm"
                  for x in st["_rec"].events),
          "a fired kbd lead arms the leg record the kill consults, with a row",
          f"{leg}")
    w3, rec = Sent(st), FakeRec()
    killed = authsrv._kbd_lead_kill(w3, st, 0, rec, "press", now=leg["t0"] + 1.0)
    mv = w3.of(MOVE)
    check(killed is True and len(mv) == 1
          and mv[0][1] == [1, [1288.5, 2000.25], 7, 7]
          and "KBD LEAD KILLED on press" in mv[0][2],
          "1.0 s into a 520 u lead at 288 u/s the kill grants the modelled "
          "body, 288 u along the heading, on its own plane both words",
          f"{mv}")
    krow = [x for x in rec.events if x.get("kind") == "kbd_leg"]
    check(st.get("kbd_leg") is None and krow
          and krow[-1]["act"] == "kill" and krow[-1]["why"] == "press"
          and krow[-1]["matured"] is False
          and abs(krow[-1]["remaining"] - 232.0) < 0.1,
          "the leg is consumed and the row names the cause and the unwalked "
          "remainder", f"{krow}")
    st, w = drive_heading(REPORT, lead=True, since=10.0)
    leg = st["kbd_leg"]
    w4, rec = Sent(st), FakeRec()
    check(authsrv._kbd_lead_kill(w4, st, 0, rec, "click",
                                 now=leg["t0"] + 10.0) is False
          and not w4.rows and st.get("kbd_leg") is None
          and rec.events[-1]["matured"] is True,
          "a MATURED lead is not re-granted (its arrival already ran); the "
          "record is consumed and the row says matured",
          f"{rec.events}")
    st = {"pos": (0.0, 0.0), "plane": 0}
    check(authsrv._kbd_lead_kill(Sent(st), st, 0, FakeRec(), "press") is False,
          "no leg, nothing sent")
    st, w = drive_heading(REPORT, lead=True, since=10.0, kill=False)
    check(st.get("kbd_leg") is None,
          "KNOWN-BAD ARM (--no-kbd-lead-kill): no leg record is armed, so the "
          "lead outlives any press", f"{st.get('kbd_leg')}")
    st = {"pos": (0.0, 0.0), "plane": 0,
          "kbd_leg": authsrv.a2_leg_note((0.0, 0.0), (520.0, 0.0), 0, 1,
                                         _t.time())}
    saved_kill = authsrv.KBD_LEAD_KILL
    authsrv.KBD_LEAD_KILL = False
    try:
        w5 = Sent(st)
        check(authsrv._kbd_lead_kill(w5, st, 0, FakeRec(), "press") is False
              and not w5.rows and st.get("kbd_leg") is not None,
              "and with the flag off an armed record is left alone")
    finally:
        authsrv.KBD_LEAD_KILL = saved_kill
    # the kill is a GRANT, never a 0x002C
    ksrc = inspect.getsource(authsrv._kbd_lead_kill)
    check("GAME_SMSG_AGENT_MOVE_TO_POINT" in ksrc
          and "GAME_SMSG_AGENT_UPDATE_POSITION" not in ksrc,
          "the kill is a zero-lead 0x0029 at the body, NOT a 0x002C -- a "
          "0x002C runs AgTrack::Clear and closes the fence until the next "
          "movement command, which would make the following grants orders",
          "agtrack_mirror.on_update_position -> clear(): client_controlled = "
          "False. The reprieve test MATCHES a grant on the body's own trail")

    print("\n11. 1z-y source locks")
    check(SRC.count('_kbd_lead_kill(send, state, conn_id, rec, "press")') == 1
          and SRC.count('_kbd_lead_kill(send, state, conn_id, rec, "click")') == 1,
          "the press arm and the click arm each kill once",
          "a third caller is a third opinion about when a lead ends")
    check(SRC.count("heading_hold_tick(send, state, conn_id, rec)") == 3
          and SRC.count("grant_flush_tick(send, state, conn_id, rec)") == 3,
          "the held heading is polled at the three sites the held click is",
          "a hold nobody polls is a drop with extra steps")
    i_row = SRC.index('rec.event("grant_verdict", fired=zero_ok')
    i_hold = SRC.index('state["heading_hold"] = heading_hold_note(')
    i_fire = SRC.index("                                if zero_ok:\n"
                       "                                    if cw_dest is not None:")
    check(i_row < i_hold < i_fire,
          "the hold is stored after the verdict row and before the fire, "
          "inside the heading arm",
          "stored earlier it would hold refused-for-other-reasons reports; "
          "later it would sit inside the fire branch")
    check(SRC.count('elif a2_src == "kbd" and KBD_LEAD_KILL:') == 1
          and SRC.count('_old_kleg = state.pop("kbd_leg", None)') == 2,
          "the kbd leg is armed at the fire site and popped by both report arms",
          "an unpopped record would kill a lead the client already ended")
    i_stop = SRC.index('rec.event("kbd_leg", act="clear", by="0x0047"')
    check('state["heading_hold"] = None' in SRC[i_stop:i_stop + 400],
          "the stop arm clears the held heading beside the leg pop")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
