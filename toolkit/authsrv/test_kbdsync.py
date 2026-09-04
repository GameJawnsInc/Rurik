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

import math                 # noqa: E402
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
# 33 at 1z-t; +27 at 1z-y (sections 10-11: the held heading, the lead kill);
# +9 at 1z-z (section 12: the matched plane word on the lead grant); +15 at
# 1z-aa (section 13: the fence-shutter gate); +22 at 1z-ae (section 14:
# refresh before maturation).
LEDGER = checks.Ledger("MOVECODE-1z-t, the keyboard world-0 sync", floor=106)
check = checks.adopt(LEDGER)

SRC = open(authsrv.__file__, encoding="utf-8").read()


def drive_heading(values, *, kbd_sync=True, lead=True, speed=True,
                  d1=False, state=None, since=10.0, hold=True, kill=True,
                  carry=False, matched=True, fence=True):
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
             authsrv.KBD_SYNC_HOLD, authsrv.KBD_LEAD_KILL,
             authsrv.KBD_SYNC_MATCHED, authsrv.KBD_LEAD_FENCE_GATE)
    authsrv.ZERO_LEAD = True
    authsrv.KBD_SYNC, authsrv.D1_LEAD = kbd_sync, d1
    authsrv.KBD_SYNC_LEAD_ON, authsrv.KBD_SYNC_SPEED_ON = lead, speed
    authsrv.KBD_SYNC_HOLD, authsrv.KBD_LEAD_KILL = hold, kill
    authsrv.KBD_SYNC_MATCHED = matched
    authsrv.KBD_LEAD_FENCE_GATE = fence
    authsrv.PLANE_CARRY = carry
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
         authsrv.KBD_LEAD_KILL, authsrv.KBD_SYNC_MATCHED,
         authsrv.KBD_LEAD_FENCE_GATE) = saved
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

    print("\n12. MOVECODE-1z-z: the sec.0.11 armer-kill on the KBD lead grant")
    check(authsrv.KBD_SYNC_MATCHED is True
          and "--no-kbd-matched-plane" in SRC
          and "KBD_SYNC_MATCHED = not a.no_kbd_matched_plane" in SRC
          and SRC.count("global KBD_SYNC_HOLD, KBD_LEAD_KILL, KBD_SYNC_MATCHED") == 1,
          "the matched word ships ON with its revert flag, rebound through a "
          "declared global",
          "1z-t skipped the armer-kill 'to change one variable'; 1z-u.4 "
          "measured the skip as a decoded lock cause")
    REPORT_29 = [1, [1000.5, 2000.25], 29, [766.0, 0.0], 1]

    def crossing(plane_prev=0):
        return {"pos": (1000.0, 2000.0), "plane": 0, "pos_seen": 0.0,
                "zl_last_grant_plane": plane_prev}
    st, w = drive_heading(REPORT_29, lead=True, carry=True, state=crossing())
    mv = w.of(MOVE)
    row = st["_rec"].of("grant_verdict")[-1]
    check(len(mv) == 1 and mv[0][1][2] == 29 and mv[0][1][3] == 29,
          "a crossing lead grant carries MATCHED words -- dest 29 / cur 29 -- "
          "not 073121's dest 29 / cur 0",
          f"sent {mv[0][1] if mv else None}")
    check(row["fired"] is True and row["pc_matched"] is True
          and row["plane_cur"] == 29 and row["plane_dest"] == 29
          and row["plane_differs"] is False,
          "and the row's pc_matched -- sec.0.11's verification key -- is TRUE "
          "where the override changed the wire",
          f"row {row}")
    st, w = drive_heading(REPORT_29, lead=True, carry=True, state=crossing(),
                          matched=False)
    mv = w.of(MOVE)
    row = st["_rec"].of("grant_verdict")[-1]
    check(len(mv) == 1 and mv[0][1][2] == 29 and mv[0][1][3] == 0
          and row["pc_matched"] is False and row["plane_differs"] is True,
          "KNOWN-BAD ARM (--no-kbd-matched-plane): the raw carry goes out, "
          "dest 29 / cur 0 -- the 073121 12.358 s shape",
          f"sent {mv[0][1] if mv else None}")
    st, w = drive_heading(REPORT_29, lead=True, carry=True,
                          state=crossing(plane_prev=29))
    row = st["_rec"].of("grant_verdict")[-1]
    check(w.of(MOVE)[0][1][3] == 29 and row["pc_matched"] is False,
          "on a same-plane lead the words already agree and the override is "
          "recorded as NOT having fired",
          f"row {row}")
    st, w = drive_heading(REPORT_29, lead=True, carry=True, state=crossing(),
                          since=0.1)
    hold = st.get("heading_hold")
    check(hold is not None and hold["plane"] == 29 and hold["plane_cur"] == 29,
          "a refused crossing re-aim is HELD with the matched word, so the "
          "re-bake at the floor carries it too (1z-y x 1z-z)",
          f"hold {hold}")
    st, w = drive_heading(REPORT_29, lead=False, carry=True, state=crossing())
    mv = w.of(MOVE)
    check(len(mv) == 1 and mv[0][1][2] == 29 and mv[0][1][3] == 0,
          "SCOPED OUT, pinned: under zero-lead (the shipped default) the grant "
          "keeps --plane-carry's one-grant lag, dest 29 / cur 0 -- F1's ruled "
          "wire, unchanged by this item",
          "the item names the KBD lead grant; the zero-lead crossing snap "
          "recovers on the next press (0.11's control era, 3/3) and is filed")
    check('[PLAYER_AGENT_ID, list(reported),\n'
          '                                  plane, plane],\n'
          '                                 f"KBD STOP-ECHO' in SRC,
          "the stop echo sends the report's plane in BOTH words -- matched by "
          "construction, the item's other half already true",
          "a zero-distance echo has one plane; a carry there would import a "
          "lag into a site that cannot need one")
    i_branch = SRC.index("elif KBD_SYNC and KBD_SYNC_LEAD_ON:")
    i_match = SRC.index("if KBD_SYNC_MATCHED:")
    i_kbd = SRC.index("a2_dest, a2_src = kbd_lead_dest(")
    check(i_branch < i_match < i_kbd,
          "the match sits inside the KBD lead branch, before the lead point, "
          "after the carry -- the D1 branch's own order",
          "after the point it would still be right; outside the branch it "
          "would change the zero-lead default")

    print("\n13. MOVECODE-1z-aa: the fence-shutter audit's gate -- no lead into a "
          "fence we shut")
    PIN = authsrv.GAME_SMSG_AGENT_UPDATE_POSITION
    check(authsrv.KBD_LEAD_FENCE_GATE is True
          and "--no-kbd-lead-fence-gate" in SRC
          and "KBD_LEAD_FENCE_GATE = not a.no_kbd_lead_fence_gate" in SRC
          and SRC.count("global KBD_SYNC_HOLD, KBD_LEAD_KILL, KBD_SYNC_MATCHED, "
                        "KBD_LEAD_FENCE_GATE") == 1,
          "the gate ships ON with its revert flag, rebound through a declared "
          "global",
          "12 of 12 server 0x002Cs on the movetap corpus shut the fence at the "
          "next sample; a lead into that window is REALFIX 0.11's lock armer")
    # the tracker: a player 0x002C stamps it, a grant or an NPC 0x002C does not
    st = {"pos": (0.0, 0.0), "plane": 0}
    w = Sent(st)
    w(authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT, [1, [10.0, 0.0], 0, 0], "grant")
    check(st.get("fence_shut_at") is None,
          "a 0x0029 does not stamp the fence tracker")
    w(PIN, [10, [10.0, 0.0], 0], "an NPC placement")
    check(st.get("fence_shut_at") is None,
          "an NPC 0x002C does not stamp it -- the fence is the player's")
    w(PIN, [1, [10.0, 0.0], 0], "PRESS ENDS THE WALK: 0x002C ...")
    check(st.get("fence_shut_at") is not None,
          "a player 0x002C stamps fence_shut_at, whatever sender labelled it")
    # a lead computed while shut degrades to the zero-lead point
    st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
          "fence_shut_at": _t.time() - 0.2, "kbd_moving_at": _t.time() - 0.3}
    st, w = drive_heading(REPORT, lead=True, state=st)
    mv = w.of(MOVE)
    row = st["_rec"].of("grant_verdict")[-1]
    check(len(mv) == 1 and mv[0][1][1] == [1000.5, 2000.25]
          and row["lead_src"] == "fallback"
          and row["lead_clip_why"] == "fence-shut"
          and "ZERO LEAD" in mv[0][2],
          "MID-WALK under a fence we shut: the keyboard lead degrades to the "
          "zero-lead point and the row says fence-shut",
          f"sent {mv[0] if mv else None} row {row}")
    check(st.get("fence_shut_at") is not None and st.get("kbd_leg") is None,
          "the tracker stays set (a mid-walk report is not a walk-start) and "
          "no keyboard leg record is armed for a degraded lead")
    # a WALK-START report re-arms the fence and the lead fires again
    st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
          "fence_shut_at": _t.time() - 2.0, "kbd_moving_at": None}
    st, w = drive_heading(REPORT, lead=True, state=st)
    mv = w.of(MOVE)
    frows = st["_rec"].of("fence")
    check(st.get("fence_shut_at") is None and frows
          and frows[-1]["act"] == "rearm" and frows[-1]["by"] == "walk-start"
          and 2.0 <= frows[-1]["shut_for"] < 30.0,   # the arm extraction is slow
          "a moving report after the latch was clear is a walk-start: it "
          "re-arms the fence with a row naming how long it was shut",
          f"fence rows {frows}")
    check(len(mv) == 1 and mv[0][1][1] == [1520.5, 2000.25]
          and "KBD LEAD" in mv[0][2],
          "and the lead of that same report fires -- the applier ran before "
          "the report was sent (the tape's 7 of 8)",
          f"sent {mv[0] if mv else None}")
    # the hold stores the degraded point
    st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
          "fence_shut_at": _t.time() - 0.2, "kbd_moving_at": _t.time() - 0.3}
    st, w = drive_heading(REPORT, lead=True, state=st, since=0.1)
    hold = st.get("heading_hold")
    check(hold is not None and hold["point"] == [1000.5, 2000.25]
          and hold["a2_src"] == "fallback" and hold["clip_why"] == "fence-shut",
          "a refused re-aim under a shut fence is HELD with the degraded "
          "point (1z-y x 1z-aa): the re-bake cannot lead into the window "
          "either", f"hold {hold}")
    # the D1 lead takes the same gate
    st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
          "fence_shut_at": _t.time() - 0.2, "kbd_moving_at": _t.time() - 0.3}
    st, w = drive_heading(REPORT, lead=False, d1=True, state=st)
    row = st["_rec"].of("grant_verdict")[-1]
    check(w.of(MOVE)[0][1][1] == [1000.5, 2000.25]
          and row["lead_src"] == "fallback"
          and row["lead_clip_why"] == "fence-shut"
          and st.get("a2_leg") is None,
          "the D1 lead degrades the same way (0.11 was discovered under it) "
          "and arms no a2_leg", f"row {row}")
    # known-bad arm
    st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
          "fence_shut_at": _t.time() - 0.2, "kbd_moving_at": _t.time() - 0.3}
    st, w = drive_heading(REPORT, lead=True, state=st, fence=False)
    check(w.of(MOVE)[0][1][1] == [1520.5, 2000.25],
          "KNOWN-BAD ARM (--no-kbd-lead-fence-gate): the 520 u lead goes into "
          "the shut fence -- the 08:46 lock's shape",
          f"sent {w.of(MOVE)[0][1]}")
    # source locks: stamped in the send choke, cleared in ONE place, never by a stop
    check(SRC.count('state["fence_shut_at"] = now') == 1
          and SRC.index('state["fence_shut_at"] = now')
          > SRC.index("def _note_wire_move("),
          "the tracker is stamped in the send choke, once, so every sender "
          "counts", "a per-sender stamp would miss the next sender")
    check(SRC.count('state["fence_shut_at"] = None') == 1
          and SRC.index('state["fence_shut_at"] = None')
          > SRC.index("_kbd_was_moving = state.get(\"kbd_moving_at\") is not None"),
          "cleared in ONE place, the 0x003D arm's walk-start test",
          "the tape: 0 of 4 stops re-armed; a click is unmeasured, so neither "
          "clears it")
    i_stop = SRC.index('rec.event("kbd_leg", act="clear", by="0x0047"')
    check("fence_shut_at" not in SRC[i_stop - 3000:i_stop + 3000],
          "and the stop arm does not touch it")
    check(SRC.count("_fence_gate_lead(state, reported,") == 3,
          "both lead branches pass through the gate, after their clip chains "
          "(the def and two call sites)")

    print("\n14. MOVECODE-1z-ae: REFRESH BEFORE MATURATION -- the arrival that "
          "armed 1z-ad's lock never fires")
    # One leg, so every arithmetic below is exact: 520 u at 190 u/s (backpedal,
    # 1z-ad's own family) from t0 = 100.0, so the arrival is at t0 + 2.7368 s
    # and the refresh is due one margin before it.
    SPEED, LEAD = 190.0, authsrv.KBD_SYNC_LEAD
    def leg(t0=100.0, refreshed=0, dest=(520.0, 0.0), x0=0.0):
        return {"x0": x0, "y0": 0.0, "dest": dest, "plane": 7, "t0": t0,
                "speed": SPEED, "wd_fired": False, "refreshed": refreshed}
    ETA = 100.0 + 520.0 / SPEED
    DUE = ETA - authsrv.KBD_LEAD_REFRESH_MARGIN
    saved = (authsrv.KBD_SYNC_LEAD_ON, authsrv.KBD_LEAD_REFRESH)
    authsrv.KBD_SYNC_LEAD_ON = True

    check(authsrv.KBD_LEAD_REFRESH is False
          and "--kbd-lead-refresh" in SRC and "--no-kbd-lead-refresh" in SRC
          and "KBD_LEAD_REFRESH = bool(a.kbd_lead_refresh)" in SRC
          and SRC.count("global KBD_LEAD_REFRESH") == 1,
          "the refresh ships OFF and OPT-IN -- 1z-af convicted it on two runs "
          "that both locked, one past a refresh-late",
          "it was ON for one evening; keeping a refuted backstop on by default "
          "is how sec.29's rule gets broken")
    authsrv.KBD_LEAD_REFRESH = True
    check(abs(authsrv.KBD_LEAD_REFRESH_MARGIN - 2.0 * authsrv.TICK_SECONDS) < 1e-9
          and authsrv.KBD_LEAD_REFRESH_MAX == 1,
          "the margin is two server ticks and the budget is one extension per "
          "report", "a margin under one tick could not be met by the poll at all")

    # not due yet -> nothing on the wire
    st = {"pos": (0.0, 0.0), "plane": 7, "kbd_moving_at": 99.0,
          "kbd_leg": leg()}
    w, r = Sent(st), FakeRec()
    sent = authsrv.kbd_lead_refresh_tick(w, st, 1, r, now=ETA - 1.0)
    check(sent is False and not w.of(MOVE),
          "mid-leg, with the arrival a second out, the tick sends nothing")

    # DUE: the re-aim the next report would have sent, from the model
    st = {"pos": (0.0, 0.0), "plane": 7, "kbd_moving_at": 99.0,
          "kbd_leg": leg()}
    w, r = Sent(st), FakeRec()
    sent = authsrv.kbd_lead_refresh_tick(w, st, 1, r, now=DUE)
    mv = w.of(MOVE)
    # the model has walked 520 - 190*0.1 = 501.0 u of the leg
    check(sent is True and len(mv) == 1
          and abs(mv[0][1][1][0] - (520.0 + LEAD)) < 1e-6
          and abs(mv[0][1][1][1]) < 1e-6,
          "DUE: one grant, pushing the leg's OWN destination a full lead "
          "further along the ray it is already on",
          f"sent {mv[0][1] if mv else None}")
    check(mv[0][1][2] == 7 and mv[0][1][3] == 7,
          "and its plane words are MATCHED (field 4 = field 3), so the refresh "
          "cannot recreate sec.0.11's stage-1 route either (1z-z)")
    check("KBD LEAD REFRESH" in mv[0][2],
          "the wire label names the sender, so a capture can be split by it")
    new = st["kbd_leg"]
    new_eta = new["t0"] + math.dist((new["x0"], new["y0"]), new["dest"]) / new["speed"]
    check(new["refreshed"] == 1 and new_eta > ETA + 2.0,
          "THE POINT: the arrival moves a full leg out instead of firing",
          f"old eta {ETA:.3f}, new eta {new_eta:.3f}")
    check(new["x0"] == 0.0 and new["y0"] == 0.0 and new["t0"] == 100.0,
          "and the record keeps its ORIGIN and t0 -- the ray stays anchored "
          "on the report the client sent, never on the model "
          "(--heading-grant's epitaph, and test_d1lead's clip lock)",
          f"{new['x0']},{new['y0']} t0 {new['t0']}")
    check(abs(authsrv.a2_leg_position(new, DUE)[0] - 501.0) < 1e-6,
          "so the position model is CONTINUOUS across the refresh: the same "
          "instant reads the same point before and after")
    rows = [e for e in r.events if e.get("kind") == "kbd_leg"]
    check(rows and rows[-1]["act"] == "refresh" and rows[-1]["n"] == 1,
          "and it says so in a row", f"{rows}")

    # once per report
    w2, r2 = Sent(st), FakeRec()
    check(authsrv.kbd_lead_refresh_tick(w2, st, 1, r2, now=new_eta - 0.1) is False
          and not w2.of(MOVE),
          "ONCE PER REPORT: the second extension is refused -- a client that "
          "has gone on being silent is not a race any more",
          f"due says {authsrv.kbd_lead_refresh_due(st, st['kbd_leg'], new_eta - 0.1)}")
    check(authsrv.kbd_lead_refresh_due(st, leg(refreshed=0), DUE)[0] is True,
          "and the budget resets with the leg record, which every 0x003D "
          "re-arms")

    # the refusals that keep it bounded
    for label, state_bits, why in (
            ("a reported STOP cleared the keyboard latch",
             {"kbd_moving_at": None}, "stopped"),
            ("our own 0x002C has the fence shut (1z-aa composes)",
             {"kbd_moving_at": 99.0, "fence_shut_at": 99.0}, "fence-shut")):
        stx = dict(state_bits)
        wx, rx = Sent(stx), FakeRec()
        stx["kbd_leg"] = leg()
        check(authsrv.kbd_lead_refresh_tick(wx, stx, 1, rx, now=DUE) is False
              and not wx.of(MOVE)
              and authsrv.kbd_lead_refresh_due(stx, stx["kbd_leg"], DUE)[1] == why,
              f"REFUSED, {why}: {label}")

    # past the ETA: nothing, and never silently
    st = {"pos": (0.0, 0.0), "plane": 7, "kbd_moving_at": 99.0,
          "kbd_leg": leg()}
    w, r = Sent(st), FakeRec()
    late = authsrv.kbd_lead_refresh_tick(w, st, 1, r, now=ETA + 0.5)
    rows = [e for e in r.events if e.get("kind") == "kbd_leg"]
    check(late is False and not w.of(MOVE)
          and rows and rows[-1]["act"] == "refresh-late",
          "PAST THE ARRIVAL it sends nothing -- a grant at the dest re-bakes "
          "nothing -- and records `refresh-late`, which is 1z-ad's own event",
          f"{rows}")
    w2, r2 = Sent(st), FakeRec()
    authsrv.kbd_lead_refresh_tick(w2, st, 1, r2, now=ETA + 0.6)
    check(not [e for e in r2.events if e.get("kind") == "kbd_leg"],
          "and it says it ONCE per leg, not once per tick")

    # KNOWN-BAD ARM
    authsrv.KBD_LEAD_REFRESH = False
    st = {"pos": (0.0, 0.0), "plane": 7, "kbd_moving_at": 99.0,
          "kbd_leg": leg()}
    w, r = Sent(st), FakeRec()
    check(authsrv.kbd_lead_refresh_tick(w, st, 1, r, now=DUE) is False
          and not w.of(MOVE) and st["kbd_leg"]["refreshed"] == 0,
          "KNOWN-BAD ARM (--no-kbd-lead-refresh): the lead is left to reach "
          "its arrival -- RUN-1zAB's rerun, five locked legs")
    authsrv.KBD_LEAD_REFRESH = True

    # inert without the lead
    authsrv.KBD_SYNC_LEAD_ON = False
    st = {"pos": (0.0, 0.0), "plane": 7, "kbd_moving_at": 99.0,
          "kbd_leg": leg()}
    w, r = Sent(st), FakeRec()
    check(authsrv.kbd_lead_refresh_tick(w, st, 1, r, now=DUE) is False
          and not w.of(MOVE),
          "INERT under the shipped default (the lead is opt-in), so this "
          "changes no wire anybody is running")
    (authsrv.KBD_SYNC_LEAD_ON, authsrv.KBD_LEAD_REFRESH) = saved

    # source locks
    check(SRC.count("kbd_lead_refresh_tick(send, state, conn_id, rec)") == 3,
          "polled at all three tick sites, beside the held heading",
          "the arrival it pre-empts runs on the client's clock, so a poll that "
          "only ran on a report would miss exactly the silent leg")
    check(SRC.index("kbd_lead_refresh_tick(send, state, conn_id, rec)")
          > SRC.index("heading_hold_tick(send, state, conn_id, rec)"),
          "and after it, so a held re-aim wins the tick it shares")
    check("a2_clip_lead(state, reported, dest)" in SRC,
          "the extension is clipped along the ray FROM THE REPORT, so every "
          "a2_clip_lead call in the file is still report-anchored",
          "test_d1lead pins that census and it caught this one")
    st = {"pos": (0.0, 0.0), "plane": 7, "kbd_moving_at": 99.0,
          "kbd_leg": leg()}
    w, r = Sent(st), FakeRec()
    authsrv.KBD_SYNC_LEAD_ON = True
    authsrv.KBD_LEAD_REFRESH = True
    _real = authsrv.a2_clip_lead
    authsrv.a2_clip_lead = lambda s, o, d: ([o[0] + 520.0, o[1]], True, "clipped")
    try:
        blocked = authsrv.kbd_lead_refresh_tick(w, st, 1, r, now=DUE)
    finally:
        authsrv.a2_clip_lead = _real
    rows = [e for e in r.events if e.get("kind") == "kbd_leg"]
    late_after = authsrv.kbd_lead_refresh_tick(Sent(st), st, 1, r, now=ETA + 0.5)
    (authsrv.KBD_SYNC_LEAD_ON, authsrv.KBD_LEAD_REFRESH) = saved
    rows = [e for e in r.events if e.get("kind") == "kbd_leg"]
    check(blocked is False and not w.of(MOVE)
          and [x["act"] for x in rows] == ["refresh-blocked", "refresh-late"]
          and late_after is False,
          "A WALL AHEAD: refresh-blocked, nothing sent -- and the arrival that "
          "follows STILL says refresh-late, on its own latch. Sharing one latch "
          "made a whole run's `zero refresh-late` unreadable", f"{rows}")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
