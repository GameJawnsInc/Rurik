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
# refresh before maturation); +8 at 1z-bw (section 15: the fence latch is
# BOUNDED by the client's own measured re-open time, with the unbounded
# behaviour kept as the revert arm and exercised); +21 at 1z-cc (section 16:
# the SERVER'S OWN model leg -- the plane term at the primitive, the leg bound
# as a pure function, the four arms through the real receive arm, and open
# ground unchanged); +9 at 1z-cd (section 17: the GRANTED lead's own plane held
# as an invariant at the primitive, on the wire and through the refresh, with
# the word-against-point check and the known-bad arm that reddens all three --
# the cross-plane guard NPCTRACK proposed is refuted at 0 of 488 and ships as
# nothing).
LEDGER = checks.Ledger("MOVECODE-1z-t, the keyboard world-0 sync", floor=231)   # 1z-di: +7 (24h-24n), from the green run
check = checks.adopt(LEDGER)

SRC = open(authsrv.__file__, encoding="utf-8").read()


def drive_heading(values, *, kbd_sync=True, lead=True, speed=True,
                  d1=False, state=None, since=10.0, hold=True, kill=True,
                  carry=False, matched=True, fence=True):
    """One 0x003D through the SHIPPED heading arm. Returns (state, wire).
    `since` is the age of the last grant when the report arrives: 10 s
    clears any floor; 0.1 s is refused `heading-rate` (1z-y) ONLY under
    `--kbd-grant-floor 0.5`, the arm this file sets where it pins the hold --
    the shipped floor is 0.0 since MOVECODE-1z-cw (retail answers every
    report), and section 26 pins that."""
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
    # 1z-u (2026-09-03 evening) split this pin: the operator's first ordinary
    # session convicted term 1 -- a lead that matured unanswered snapped the
    # body 498 u and shut the AgTrack fence -- so the lead went OPT-IN while
    # its four gates were built (1z-y, 1z-z, 1z-ab, 1z-aa).  1z-bl then
    # localised the rewind to the AgTrack guard's stationary waiver, not to
    # the lead; RUN-1zBM measured the lead-off cost (world-0 p50 252 u behind
    # a walking body), RUN-1zBO ran the lead under the guard fix (zero 0x002C,
    # 0 of 7 legs thrown back, 13.0 u), RUN-1zBP its revert arm, and 1z-bt
    # deleted the waiver.  1z-bu (2026-09-05, PLAN sec.7 Q13, the owner's
    # ruling) puts all three terms back ON, and this pin is the whole trio.
    check(authsrv.KBD_SYNC is True and authsrv.KBD_SYNC_LEAD_ON is True
          and authsrv.KBD_SYNC_SPEED_ON is True
          and authsrv.KBD_SYNC_STOP_ON is True,
          "KBD_SYNC ships with all THREE terms ON -- the lead is back by the "
          "owner's ruling (1z-bu) after RUN-1zBO/1zBP under the guard fix",
          "the lead OFF would be shipping RUN-1zBM's measured 252 u lag "
          "after the rewind it was convicted for was localised elsewhere and "
          "removed; a stop echo or family rate OFF would be withholding two "
          "additive terms nothing has convicted")
    check("--kbd-lead" in SRC and "--no-kbd-lead" in SRC
          and "KBD_SYNC_LEAD_ON = not a.no_kbd_lead" in SRC
          and "bool(a.kbd_lead)" not in SRC,
          "the lead is the default; --kbd-lead still parses as a no-op and "
          "--no-kbd-lead reverts and wins, so runsheets of both eras keep "
          "their meaning",
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

    # MOVECODE-1z-cw: the hold is the coalescing half of a FLOOR, and the
    # keyboard arm ships with none (KBD_GRANT_FLOOR = 0.0: retail answers 99.5%
    # of heading reports inside the old window). The mechanism stays and is
    # pinned here under the revert arm it exists for, --kbd-grant-floor 0.5;
    # section 26 pins the shipped default.
    _saved_floor = authsrv.KBD_GRANT_FLOOR
    authsrv.KBD_GRANT_FLOOR = 0.5
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
    t_floor = st["grant_at"] + authsrv.KBD_GRANT_FLOOR
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
    authsrv.KBD_GRANT_FLOOR = _saved_floor

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
    _saved_kf = authsrv.KBD_GRANT_FLOOR
    authsrv.KBD_GRANT_FLOOR = 0.5                          # 1z-cw: the refusing arm
    try:
        st, w = drive_heading(REPORT_29, lead=True, carry=True, state=crossing(),
                              since=0.1)
    finally:
        authsrv.KBD_GRANT_FLOOR = _saved_kf
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
    # MOVECODE-1z-ci: a moving report that has WALKED OFF the pin point re-arms
    # the fence without a stop (the owner never stops; the client's fence was
    # open in 0.05-0.5 s on 7 of 7 pins), and a report still ON the pin does
    # not (the scripted case: a shut fence does not drive a held key, 1z-aa.2).
    st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
          "fence_shut_at": _t.time() - 0.2, "kbd_moving_at": _t.time() - 0.3,
          "fence_pin_pt": (1000.0, 2000.0)}
    st, w = drive_heading(REPORT, lead=True, state=st)
    check(st.get("fence_shut_at") is not None
          and st["_rec"].of("grant_verdict")[-1]["lead_clip_why"] == "fence-shut",
          "1z-ci: a moving report ON the pin point keeps the latch -- the body has "
          "not walked, so the fence may still be shut (the harness's held key)",
          f"shut_at {st.get('fence_shut_at')}")
    st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
          "fence_shut_at": _t.time() - 0.2, "kbd_moving_at": _t.time() - 0.3,
          "fence_pin_pt": (900.0, 2000.0)}
    st, w = drive_heading(REPORT, lead=True, state=st)
    mv = w.of(MOVE)
    frows = st["_rec"].of("fence")
    check(st.get("fence_shut_at") is None and frows
          and frows[-1]["act"] == "rearm" and frows[-1]["by"] == "walked-off-pin"
          and frows[-1]["off"] >= 99.0
          and len(mv) == 1 and mv[0][1][1] == [1520.5, 2000.25] and "KBD LEAD" in mv[0][2],
          "1z-ci: the same mid-walk report 100 u OFF the pin re-arms the fence "
          "(by=walked-off-pin, off 100 u) and the lead of that report fires",
          f"fence rows {frows}, sent {mv[0] if mv else None}")
    _saved_frm = authsrv.FENCE_REARM_MOVED_ON
    try:
        authsrv.FENCE_REARM_MOVED_ON = False
        st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
              "fence_shut_at": _t.time() - 0.2, "kbd_moving_at": _t.time() - 0.3,
              "fence_pin_pt": (900.0, 2000.0)}
        st, w = drive_heading(REPORT, lead=True, state=st)
    finally:
        authsrv.FENCE_REARM_MOVED_ON = _saved_frm
    check(st.get("fence_shut_at") is not None
          and st["_rec"].of("grant_verdict")[-1]["lead_clip_why"] == "fence-shut",
          "1z-ci KNOWN-BAD ARM (--no-fence-rearm-moved): the same report keeps the "
          "latch and the lead degrades -- the session's 79 refusals",
          f"shut_at {st.get('fence_shut_at')}")
    check(authsrv.FENCE_REARM_MOVED == 24.0 and "--no-fence-rearm-moved" in SRC
          and "global FENCE_REARM_MOVED_ON" in SRC
          and authsrv.capture_flags().get("FENCE_REARM_MOVED_ON") is True,
          "1z-ci ships ON at two bounding radii, with its revert, in the header", "")
    # the hold stores the degraded point
    st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
          "fence_shut_at": _t.time() - 0.2, "kbd_moving_at": _t.time() - 0.3}
    _saved_kf = authsrv.KBD_GRANT_FLOOR
    authsrv.KBD_GRANT_FLOOR = 0.5                          # 1z-cw: the refusing arm
    try:
        st, w = drive_heading(REPORT, lead=True, state=st, since=0.1)
    finally:
        authsrv.KBD_GRANT_FLOOR = _saved_kf
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
    # 1z-ci: TWO clears now, both in the 0x003D arm -- the walk-start and the
    # walked-off-pin re-arm -- and still none in the 0x0047 arm or the click path.
    check(SRC.count('state["fence_shut_at"] = None') == 2
          and SRC.index('state["fence_shut_at"] = None')
          > SRC.index("_kbd_was_moving = state.get(\"kbd_moving_at\") is not None"),
          "cleared in ONE place, the 0x003D arm's walk-start test",
          "the tape: 0 of 4 stops re-armed; a click is unmeasured, so neither "
          "clears it")
    i_stop = SRC.index('rec.event("kbd_leg", act="clear", by="0x0047"')
    check("fence_shut_at" not in SRC[i_stop - 3000:i_stop + 3000],
          "and the stop arm does not touch it")
    check(SRC.count("_fence_gate_lead(state, reported,") == 4,
          "both lead branches and 1z-cl's corridor chain pass through the "
          "gate, after their clip chains (the def and three call sites)")

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
          "INERT with the lead off (--no-kbd-lead): the refresh has nothing "
          "to refresh, so that arm's wire is untouched by it")
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

    print("\n15. MOVECODE-1z-bw: the fence latch is BOUNDED by the client's own "
          "measured re-open time")
    # section 13's gate degrades a lead while our latch is set, and the latch is
    # cleared in ONE place -- a keyboard walk-start, which needs a 0x0047 first.
    # A player who walks without stopping holds it set for as long as they walk:
    # on RUN-1zBW, 45.25 s in one window, 72 of 163 fired grants zeroed, while
    # the CLIENT's own fence dword read OPEN for 462 of the 498 tape samples
    # inside it. The client re-opens by itself in <= 6.087 s (26 measured shuts,
    # 14 tapes -- review/fencelatency.py), so past that the gate is degrading a
    # grant for a window that is no longer there.
    check(authsrv.FENCE_LATCH_MAX_AGE == 8.0
          and "--no-fence-latch-timeout" in SRC
          and "FENCE_LATCH_MAX_AGE = None if a.no_fence_latch_timeout else 8.0" in SRC,
          "the bound ships at 8.0 s with its revert flag, rebound through a "
          "declared global",
          "unbounded is what held the lead off for 28.7% of RUN-1zBW")
    check(authsrv.FENCE_LATCH_MAX_AGE > 6.087,
          "and it sits ABOVE the client's measured maximum shut (6.087 s), so "
          "it can never cut a genuinely-shut window short -- the bound caps the "
          "pathological case, it does not tune the normal one",
          "a bound under the measured max would trade this defect for the one "
          "the gate exists to prevent")
    # INSIDE the window: unchanged from section 13, so the bound did not
    # quietly disable the gate.
    st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
          "fence_shut_at": _t.time() - 0.2, "kbd_moving_at": _t.time() - 0.3}
    st, w = drive_heading(REPORT, lead=True, state=st)
    mv = w.of(MOVE)
    check(len(mv) == 1 and mv[0][1][1] == [1000.5, 2000.25]
          and st["_rec"].of("grant_verdict")[-1]["lead_clip_why"] == "fence-shut",
          "INSIDE the bound the gate still degrades exactly as before -- the "
          "timeout did not silently switch the gate off",
          f"sent {mv[0] if mv else None}")
    # PAST the window: the lead fires. This is the whole change.
    st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
          "fence_shut_at": _t.time() - 20.0, "kbd_moving_at": _t.time() - 30.0}
    st, w = drive_heading(REPORT, lead=True, state=st)
    mv = w.of(MOVE)
    check(len(mv) == 1 and mv[0][1][1] == [1520.5, 2000.25]
          and "KBD LEAD" in mv[0][2],
          "PAST the bound, mid-walk with no walk-start in sight, the lead "
          "FIRES at its full 520 u -- the 45 s of zeroed grants is what this "
          "removes",
          f"sent {mv[0] if mv else None}")
    check(st.get("fence_shut_at") is not None,
          "and the latch itself is NOT cleared -- the bound is read at the "
          "gate, so a later 0x002C still re-stamps it and the telemetry keeps "
          "saying the fence was shut",
          "clearing it would lose the fact that we shut the fence at all")
    # THE KNOWN-BAD ARM: with the timeout reverted the old behaviour returns.
    # A guard that passes on the broken arm is measuring the wrong quantity.
    _saved = authsrv.FENCE_LATCH_MAX_AGE
    try:
        authsrv.FENCE_LATCH_MAX_AGE = None
        st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
              "fence_shut_at": _t.time() - 20.0, "kbd_moving_at": _t.time() - 30.0}
        st, w = drive_heading(REPORT, lead=True, state=st)
        mv = w.of(MOVE)
        check(len(mv) == 1 and mv[0][1][1] == [1000.5, 2000.25]
              and st["_rec"].of("grant_verdict")[-1]["lead_clip_why"] == "fence-shut",
              "REVERT ARM (--no-fence-latch-timeout): the same 20 s latch "
              "degrades the lead again, so this section's positive really is "
              "the bound and not something else in the fixture",
              f"sent {mv[0] if mv else None}")
    finally:
        authsrv.FENCE_LATCH_MAX_AGE = _saved
    check(authsrv.FENCE_LATCH_MAX_AGE == 8.0,
          "and the module global is restored after the revert arm")
    # the gate OFF entirely still wins over the bound.  NOTE the lever: this
    # check first set authsrv.KBD_LEAD_FENCE_GATE directly and went RED,
    # because drive_heading takes its OWN `fence=` argument and rebinds the
    # global inside the call -- a module-level assignment here is overwritten
    # before the arm runs.  The failure was the fixture, not the code, and it
    # is exactly the "prove which lever you are pulling" trap.
    st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
          "fence_shut_at": _t.time() - 0.2, "kbd_moving_at": _t.time() - 0.3}
    st, w = drive_heading(REPORT, lead=True, state=st, fence=False)
    mv = w.of(MOVE)
    check(len(mv) == 1 and mv[0][1][1] == [1520.5, 2000.25],
          "--no-kbd-lead-fence-gate still wins over the bound: gate off means "
          "no degradation at any latch age",
          f"sent {mv[0] if mv else None}")

    print("\n16. MOVECODE-1z-cc: the SERVER'S OWN model leg is bounded too -- "
          "one surface, and never past the order we gave")
    # WHAT THIS IS ABOUT. `state["dest"]` never touches the wire, so nothing here
    # is a grant policy -- but the world tick's integrator walks `state["pos"]`
    # to it, and the NPC follow, the leash, the range gate and every re-path read
    # `state["pos"]`. On RUN-NPCTRACK-R1 the client sent one 0x003D from
    # (10012, 8524), walked into the staircase side, moved 0 u and said nothing
    # for five seconds; the model walked 604 u up the stairs and four follow
    # orders went out naming a player who was never there.
    #
    # THE FIXTURE IS THE SEAM, NOT A WALL, and that distinction is the whole
    # point: everything below is walkable, so a plane-BLIND clip runs the ray to
    # its end and only the plane term can stop it. A wall fixture would clip with
    # the term OFF and this section would be measuring nothing (§13's lesson:
    # prove which lever you are pulling).
    import pathmap as _pm_mod                                  # noqa: E402

    class _Stairs(object):
        """map 148's staircase seam in miniature. Plane 0 to x = 1100, 29 past.

        `clip` is `PathingMap.clip` ITSELF, bound to this geometry -- not a
        re-implementation. A second copy of that walk drifting from the real one
        is the failure this repo keeps recording, and the plane term under test
        lives inside it.
        """
        SEAM = 1100.0

        def walkable(self, x, y):
            return True

        def plane_at(self, x, y, prefer=None):
            return 0 if x <= self.SEAM else 29

        def containing(self, x, y):
            # The plane-repair arm asks the mesh which planes cover a point,
            # BEFORE this section's arm runs. One plane everywhere, so it always
            # answers `plane-legal` and never fires -- the fixture must not
            # smuggle a second policy into a section about the model leg.
            return (self,)

        @property
        def plane(self):
            return 0

        clip = _pm_mod.PathingMap.clip

    class _Blind(object):
        """A mesh from before the plane term: no `plane_at`, and a `clip` that
        would TypeError on the keyword. The hasattr door is what keeps it out."""

        def walkable(self, x, y):
            return True

        def clip(self, x0, y0, x1, y1, step=16.0):
            return (x1, y1)

    check(authsrv.MODEL_PLANE_CLIP is True and authsrv.MODEL_LEG_BOUND is True
          and "--no-model-plane-clip" in SRC and "--no-model-leg-bound" in SRC
          and "global MODEL_PLANE_CLIP" in SRC
          and "global MODEL_LEG_BOUND" in SRC,
          "both terms ship ON, each with its OWN revert flag rebound through a "
          "declared global -- one run can convict one term (sec.29)",
          f"plane={authsrv.MODEL_PLANE_CLIP} bound={authsrv.MODEL_LEG_BOUND}")

    # ---- (a) the plane term, at the primitive -----------------------------
    st = {"pos": (1000.0, 2000.0), "plane": 0, "pathmap": _Stairs()}
    aware, aware_blocked = authsrv.clip_to_walkable(st, (1900.0, 2000.0))
    _saved_pc = authsrv.MODEL_PLANE_CLIP
    try:
        authsrv.MODEL_PLANE_CLIP = False
        blind, blind_blocked = authsrv.clip_to_walkable(st, (1900.0, 2000.0))
    finally:
        authsrv.MODEL_PLANE_CLIP = _saved_pc
    check(aware[0] <= _Stairs.SEAM and aware_blocked
          and abs(aware[0] - 1100.0) <= authsrv.COLLISION_STEP,
          "the model leg STOPS at the plane seam, within one COLLISION_STEP of "
          "it, and reports blocked",
          f"{aware} blocked={aware_blocked}")
    check(blind == (1900.0, 2000.0) and not blind_blocked,
          "KNOWN-BAD ARM (--no-model-plane-clip): the same ray over the same "
          "geometry runs its FULL 900 u onto the far plane and calls it clear "
          "-- so the check above is measuring the plane term and not the "
          "fixture",
          f"{blind} blocked={blind_blocked}")
    check(math.hypot(aware[0] - 1000.0, aware[1] - 2000.0)
          <= math.hypot(blind[0] - 1000.0, blind[1] - 2000.0),
          "and the term can only ever SHORTEN the leg -- pm.clip's own "
          "contract, which is why it cannot lengthen a lead into a wall")
    st_blind = {"pos": (1000.0, 2000.0), "plane": 0, "pathmap": _Blind()}
    check(authsrv.clip_to_walkable(st_blind, (1900.0, 2000.0))
          == ((1900.0, 2000.0), False),
          "THE hasattr DOOR: a mesh predating the plane term takes the "
          "historical call and does not raise inside the recv loop",
          "a2_clip_lead guards the same way for the same reason")

    # ---- (b) the leg bound, as the pure function it is --------------------
    LB = authsrv.model_leg_bound
    O, R = (0.0, 0.0), (0.0, 0.0)
    check(LB(O, (700.0, 0.0), R, (100.0, 0.0), True, "kbd")
          == ((100.0, 0.0), "bounded"),
          "BOUNDED: a 700 u model leg against a 100 u lead our mesh cut short "
          "is trimmed to the lead's own REACH, on the model's own ray")
    # MOVECODE-1z-ct (2026-09-09): the clear lead is bounded TOO, and it gets its
    # OWN verdict. This check used to assert (None, "lead-clear") and the paragraph
    # below it is kept as the revert arm, because the reasoning it recorded is still
    # exactly right about the COST -- it was wrong only about the cost's SIZE.
    check(LB(O, (700.0, 0.0), R, (100.0, 0.0), False, "kbd")
          == ((100.0, 0.0), "bounded-clear"),
          "1z-ct: a CLEAR lead bounds too, and says so in its own word -- the "
          "call site must be able to tell a mesh cut from a reach cut")
    check(LB(O, (700.0, 0.0), R, (100.0, 0.0), True, "kbd")[1] == "bounded",
          "1z-ct: and the mesh case keeps the word it always had, because that "
          "is the one that licenses state[\"clipped\"] downstream")
    # THE SPECIMEN, from session 4 t=48.982 (1z-cs.1). On an UNCLIPPED keyboard
    # lead the grant is anchored at `reported` along unit(heading) at
    # KBD_SYNC_LEAD, and the model ray is built from the same origin and the same
    # direction -- so the trim lands ON the granted point. That is what makes this
    # a derivation and not a tuned cap, and it is the one property that would
    # break silently if either anchor ever moved.
    _sp_o = (10386.63671875, 8390.7724609375)
    _sp_grant = (10745.4, 8767.2)
    _sp_ray = (10915.8, 8946.1)
    _sp_d, _sp_w = LB(_sp_o, _sp_ray, _sp_o, _sp_grant, False, "kbd")
    check(_sp_w == "bounded-clear"
          and math.hypot(_sp_d[0] - _sp_grant[0], _sp_d[1] - _sp_grant[1]) < 0.2,
          "1z-ct SPECIMEN: the trim lands ON the granted point (session 4's "
          "t=48.982 leg: body 520.0 u, model 767.1 u, drift 247.1 -> 0.0)",
          f"{_sp_d} is "
          f"{math.hypot(_sp_d[0] - _sp_grant[0], _sp_d[1] - _sp_grant[1]):.3f} u "
          f"from the grant")
    # THE KNOWN-BAD ARM, and it must reproduce the defect rather than merely
    # differ: with the flag off the model keeps the whole 768 u ray while the
    # grant reached 520, which is the 247 u of drift 1z-cs measured.
    _saved_bc = authsrv.MODEL_BOUND_CLEAR_LEAD
    try:
        authsrv.MODEL_BOUND_CLEAR_LEAD = False
        _rev = LB(O, (700.0, 0.0), R, (100.0, 0.0), False, "kbd")
        _rev_sp = LB(_sp_o, _sp_ray, _sp_o, _sp_grant, False, "kbd")
    finally:
        authsrv.MODEL_BOUND_CLEAR_LEAD = _saved_bc
    check(_rev == (None, "lead-clear"),
          "REVERT ARM (--no-bound-clear-leads): LEAD-CLEAR again, exactly as "
          "before 1z-ct -- 520 u of lead against the client's 768 u vec2 is 248 u "
          "of margin over its own report trigger (p99 chord 515.1 u), and the "
          "cost of capping is that the model ARRIVES and clears state[\"walking\"]")
    check(_rev_sp == (None, "lead-clear"),
          "and the revert arm reproduces the DEFECT on the specimen: the model "
          "keeps its full ray while the grant reached 520 u -- 247.1 u of drift, "
          "which is what the arm exists to be scored against")
    check(authsrv.MODEL_BOUND_CLEAR_LEAD is True
          and "--no-bound-clear-leads" in open(
              authsrv.__file__, encoding="utf-8").read(),
          "1z-ct ships ON with its revert flag")
    # THE CALL SITE MUST NOT CLAIM A CLIP THAT NEVER HAPPENED. A clear lead was
    # cut by the ORDER's reach and by no mesh; telling the 0x0047 arm otherwise
    # is the shape 1z-cq's review refused A2_LEAD_HELD_STILL for.
    _src_ct = open(authsrv.__file__, encoding="utf-8").read()
    _i_ct = _src_ct.find('if a2_model_bound == "bounded":')
    _i_cl = _src_ct.find('state["clipped"] = True', _i_ct)
    check(0 < _i_ct < _i_cl < _i_ct + 200,
          "1z-ct: state[\"clipped\"] is set ONLY on the mesh verdict, so a "
          "reach-trimmed leg never reports a mesh refusal that did not happen")
    check(LB(O, (700.0, 0.0), R, (100.0, 0.0), True, "fallback")
          == (None, "no-lead")
          and LB(O, (700.0, 0.0), R, None, True, None) == (None, "no-lead"),
          "NO-LEAD: a fallback grant IS the report and a fence-zeroed one is "
          "too -- neither orders a walk, so neither bounds one")
    check(LB(O, (50.0, 0.0), R, (100.0, 0.0), True, "kbd") == (None, "within"),
          "WITHIN: a model leg already shorter than the grant is left alone")
    check(LB(O, None, R, (100.0, 0.0), True, "kbd") == (None, "no-model"),
          "NO-MODEL: no destination in hand, nothing to bound")
    _saved_lb = authsrv.MODEL_LEG_BOUND
    try:
        authsrv.MODEL_LEG_BOUND = False
        off = LB(O, (700.0, 0.0), R, (100.0, 0.0), True, "kbd")
    finally:
        authsrv.MODEL_LEG_BOUND = _saved_lb
    check(off == (None, "off"),
          "OFF (--no-model-leg-bound): the revert arm refuses first, so a run "
          "can convict this term alone")
    # THE ORIGINS DIFFER ON A REFUSED REPORT, which is why the bound compares
    # REACHES. Same lead, same 700 u model leg, model origin 500 u behind the
    # report: the answer must still be 100 u OF MODEL LEG, measured from the
    # model's own start, not the lead's endpoint borrowed across frames.
    d, why = LB((-500.0, 0.0), (200.0, 0.0), R, (100.0, 0.0), True, "kbd")
    check(why == "bounded" and abs(d[0] - (-400.0)) < 1e-9,
          "and it is REACH, not the point: with the model leg anchored 500 u "
          "behind the report (a refused report -- the one moment the two are "
          "not the same point) the trim is still 100 u of the model's own ray",
          f"{d} {why}")

    # ---- (c) the two ends joined, through the real arm ---------------------
    # RUN-NPCTRACK-R1's own geometry, scaled onto the fixture: the report sits
    # 100 u inside plane 0, the client's vec2 is its real 766 u, and the seam is
    # at 1100. The lead is clipped at the seam; the model must not out-walk it.
    STAIRS_REPORT = [1, [1000.5, 2000.25], 0, [766.0, 0.0], 1]

    def _drive_stairs(plane_clip, leg_bound):
        s = {"pos": (1000.5, 2000.25), "plane": 0, "pos_seen": 0.0,
             "pathmap": _Stairs()}
        sv = (authsrv.MODEL_PLANE_CLIP, authsrv.MODEL_LEG_BOUND)
        authsrv.MODEL_PLANE_CLIP, authsrv.MODEL_LEG_BOUND = plane_clip, leg_bound
        try:
            s, ww = drive_heading(STAIRS_REPORT, lead=True, state=s)
        finally:
            (authsrv.MODEL_PLANE_CLIP, authsrv.MODEL_LEG_BOUND) = sv
        row = s["_rec"].of("grant_verdict")[-1]
        reach = math.hypot(s["dest"][0] - 1000.5, s["dest"][1] - 2000.25)
        lead = math.hypot(row["dest"][0] - 1000.5, row["dest"][1] - 2000.25)
        return s, ww, row, reach, lead

    s_bad, _, row_bad, reach_bad, lead_bad = _drive_stairs(False, False)
    s_pc, _, row_pc, reach_pc, _ = _drive_stairs(True, False)
    s_lb, _, row_lb, reach_lb, _ = _drive_stairs(False, True)
    s_on, w_on, row_on, reach_on, lead_on = _drive_stairs(True, True)
    check(lead_bad == lead_on and lead_on < 120.0
          and row_on["lead_clip_why"] == "plane-seam",
          "THE GRANT IS IDENTICAL ON ALL FOUR ARMS and is clipped at the seam "
          "-- a2_clip_lead has had the plane term since 1z-ap. Nothing in this "
          "section changes a byte on the wire",
          f"lead reach bad={lead_bad:.1f} on={lead_on:.1f} "
          f"why={row_on['lead_clip_why']}")
    check(reach_bad > 700.0 and row_bad["model_bound"] == "off",
          "KNOWN-BAD ARM (both reverted): the model leg runs its full 766 u "
          "THROUGH the seam while the grant stopped at it -- two of our own "
          "components modelling one body 650 u apart. This is RUN-R1's 604 u",
          f"model reach {reach_bad:.1f} u, grant {lead_bad:.1f} u")
    check(reach_pc <= lead_bad,
          "THE PLANE TERM ALONE closes it: the model stops at the seam, at or "
          "inside the grant's own reach",
          f"model {reach_pc:.1f} u vs grant {lead_bad:.1f} u")
    check(reach_lb <= lead_bad + 1e-6 and row_lb["model_bound"] == "bounded",
          "THE LEG BOUND ALONE closes it too, from the other side -- with the "
          "plane term REVERTED the model is still trimmed to the granted "
          "reach. Two independent conjuncts, so a run that reddens one "
          "localises the change",
          f"model {reach_lb:.1f} u vs grant {lead_bad:.1f} u "
          f"({row_lb['model_bound']})")
    check(reach_on <= lead_on and row_on["model_bound"] in ("within", "bounded"),
          "SHIPPED, both on: the model ends at or inside the point our own "
          "mesh just refused the client",
          f"model {reach_on:.1f} u vs grant {lead_on:.1f} u "
          f"({row_on['model_bound']})")
    check(s_on.get("clipped") is True,
          "and `state['clipped']` says the leg was cut short, so the 0x0047 "
          "arm's `was_clipped` reads the bound as it reads the clip")
    # THE ROW EXISTS ON EVERY EVALUATION, not only when it fires -- a bound
    # nobody can see not-firing is a wish.
    check(all("model_bound" in r for r in s_on["_rec"].of("grant_verdict"))
          and row_bad["model_bound"] == "off",
          "every grant_verdict row carries `model_bound`, including the arms "
          "where the bound refused",
          f"{[r.get('model_bound') for r in s_on['_rec'].of('grant_verdict')]}")

    # ---- (d) OPEN GROUND IS UNTOUCHED -------------------------------------
    # The regression this must not cause. With no seam in reach the lead is
    # clear at its full 520 u and the model keeps its 766 u ray: the 248 u of
    # margin over the client's own report trigger, which is what stops the model
    # parking mid-cruise and turning the next 0x0025 into a per-report send.
    st = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0}
    st, w = drive_heading(REPORT, lead=True, state=st)
    row = st["_rec"].of("grant_verdict")[-1]
    check(st["dest"] == (1520.5, 2000.25)
          and row["lead_clip_why"] == "no-mesh"
          and row["model_bound"] == "bounded-clear"
          and w.of(MOVE)[0][1][1] == [1520.5, 2000.25],
          "NO MESH IN HAND: the WIRE is unchanged to the bit (the lead is still "
          "its derived 520), and MOVECODE-1z-ct now trims the model to that same "
          "reach -- a mesh that said nothing cannot refuse anything, but the "
          "ORDER still bounds the model that follows it",
          f"dest={st['dest']} why={row['lead_clip_why']} "
          f"bound={row['model_bound']}")
    # AND THE THING THE 248 u MARGIN WAS REALLY PROTECTING, which 1z-ct does not
    # take away. The margin used to be asserted as a DISTANCE; what stops the
    # model parking mid-cruise is TIME. It can only reach the cap after
    # KBD_SYNC_LEAD / DEFAULT_RUN_SPEED of unbroken walking, and the client
    # reports far more often than that, so a cruising leg is rewritten long
    # before the model arrives and state["walking"] is never cleared under it.
    _t_to_cap = authsrv.KBD_SYNC_LEAD / authsrv.DEFAULT_RUN_SPEED
    check(_t_to_cap > 1.5,
          "1z-ct: the model needs %.3f s of unbroken walking to reach the cap, "
          "so the margin survives as TIME where it used to be asserted as "
          "distance -- this is why the cap is inert on a cruise" % _t_to_cap,
          "measured on the corpus: 11 of 392 lead-clear legs ever get there")
    st = {"pos": (1000.0, 2000.0), "plane": 0, "pos_seen": 0.0,
          "pathmap": _Stairs()}
    # Same mesh, but aimed AWAY from the seam: nothing is CLIPPED, the wire is
    # unchanged, and since MOVECODE-1z-ct the model is trimmed to the order's
    # own reach instead of walking the client's full ray past it. The ray would
    # end at x = 234.5 (1000.5 - 766); the 520 u grant ends at x = 480.5.
    st, w = drive_heading([1, [1000.5, 2000.25], 0, [-766.0, 0.0], 1],
                          lead=True, state=st)
    row = st["_rec"].of("grant_verdict")[-1]
    check(row["lead_clip_why"] == "clear" and row["model_bound"] == "bounded-clear"
          and abs(st["dest"][0] - 480.5) < 1e-6
          and w.of(MOVE)[0][1][1] == [480.5, 2000.25],
          "AWAY FROM THE SEAM the lead reads clear and the WIRE is unchanged; "
          "1z-ct trims the model to the order's own reach rather than "
          "letting it walk the client's full 766 u ray past a 520 u grant",
          f"dest={st['dest']} why={row['lead_clip_why']} "
          f"bound={row['model_bound']}")


    print("\n17. MOVECODE-1z-cd: THE GRANTED LEAD'S OWN PLANE, pinned as an "
          "invariant -- and the cross-plane guard REFUTED for want of one case")
    # WHAT THIS SECTION IS, and it is not a new policy. NPCTRACK's wall case
    # proposed that the keyboard lead should REFUSE or SHORTEN a point whose
    # plane differs from the mover's when no same-plane route exists. Measured
    # on the real map-148 mesh at the specimen it was commissioned for
    # (capture `authsrv-20260906T094349-c1` t=25.4197, report (10014.5, 8526.5)
    # plane 0, the client's own 767.1 u vec2 due +x), the grant that went out
    # was (10118.5, 8526.5) -- `planes_at` {0}, the MOVER'S OWN PLANE, one 2 u
    # sample short of the seam at 10120.5 where plane 29 starts, with
    # `pm.route` returning a two-waypoint same-plane path because origin and
    # destination are the SAME TRAPEZOID. The precondition is false, and the
    # corpus says it is false everywhere: 240 MOVING grants with the plane clip
    # in force, ZERO off the mover's plane, while the same detector finds 49 of
    # 282 where it is reverted, bypassed or predates the flag. (Zero-distance
    # leads are excluded from both -- their destination IS the report, so
    # cross-plane is impossible by construction and counting them halves the
    # rate.) `A2_LEAD_PLANE_CLIP` shipped in df74661, 2026-09-04.
    # studies/movecode/review/leadplane.py --check re-asserts both sides.
    #
    # So no knob was added. What ships instead is the INVARIANT that made the
    # guard vacuous, held where it can be broken: 1z-cc's whole lesson is that
    # `pm.clip`'s plane term sat in one of this file's two clippers for two
    # days and nobody could see the other was missing it. A term whose absence
    # is invisible is one refactor from being lost, and the corpus would then
    # read exactly like the 49 above.
    #
    # THE FIXTURE IS SECTION 16'S SEAM, deliberately: everything in it is
    # walkable, so a plane-BLIND clip runs the ray to its end and only the
    # plane term can stop it. That is what makes the known-bad arm below
    # informative rather than decorative.
    FAR = [1, [1000.5, 2000.25], 0, [766.0, 0.0], 1]      # +x, across the seam

    # ---- (a) THE INVARIANT, at the primitive ------------------------------
    st = {"pos": (1000.0, 2000.0), "plane": 0, "pathmap": _Stairs()}
    lead = authsrv.kbd_lead_dest([1000.5, 2000.25], [766.0, 0.0])[0]
    got, clipped, why = authsrv.a2_clip_lead(st, [1000.5, 2000.25], lead)
    mesh = _Stairs()
    check(mesh.plane_at(got[0], got[1]) == mesh.plane_at(1000.5, 2000.25)
          and clipped and why == "plane-seam"
          and abs(got[0] - 1098.5) < 1e-6,
          "THE INVARIANT: the point `a2_clip_lead` grants is on the MOVER'S "
          "OWN PLANE -- `pm.clip`'s plane term only ever returns a sample it "
          "has already tested on that plane, so the granted point cannot be "
          "across the seam. It stops one step short of it and names the door",
          f"granted {got} plane {mesh.plane_at(got[0], got[1])} why={why}")
    _saved_lp = authsrv.A2_LEAD_PLANE_CLIP
    try:
        authsrv.A2_LEAD_PLANE_CLIP = False
        blind, b_clipped, b_why = authsrv.a2_clip_lead(
            st, [1000.5, 2000.25], lead)
    finally:
        authsrv.A2_LEAD_PLANE_CLIP = _saved_lp
    check(mesh.plane_at(blind[0], blind[1]) == 29 and not b_clipped
          and b_why == "clear" and abs(blind[0] - 1520.5) < 1e-6,
          "KNOWN-BAD ARM (--no-lead-plane-clip): the SAME ray over the SAME "
          "geometry is granted its full 520 u onto plane 29 and called CLEAR "
          "-- so (a) is measuring the plane term and not the fixture, and this "
          "is the shape of all 49 corpus grants where the clip is not in force",
          f"granted {blind} plane {mesh.plane_at(blind[0], blind[1])} "
          f"why={b_why}")
    check(authsrv.A2_LEAD_PLANE_CLIP is _saved_lp is True,
          "and the module global is restored after the revert arm")

    # ---- (b) THE SAME, THROUGH THE REAL RECEIVE ARM -----------------------
    # The primitive is not the wire. What the client is told is what matters,
    # so the invariant is re-asserted on the bytes the 0x0029 actually carries.
    st = {"pos": (1000.0, 2000.0), "plane": 0, "pos_seen": 0.0,
          "pathmap": _Stairs()}
    st, w = drive_heading(FAR, lead=True, state=st)
    mv = w.of(MOVE)
    row = st["_rec"].of("grant_verdict")[-1]
    check(len(mv) == 1 and abs(mv[0][1][1][0] - 1098.5) < 1e-6
          and mesh.plane_at(*mv[0][1][1]) == 0
          and row["lead_clip_why"] == "plane-seam" and row["lead_clipped"],
          "ON THE WIRE: the 0x0029 the client receives names a point on the "
          "mover's own plane, and the verdict row names the seam door",
          f"sent {mv[0][1][1] if mv else None} why={row['lead_clip_why']}")

    # ---- (c) THE PLANE WORD MUST NOT LIE ABOUT THE POINT ------------------
    # The grant's plane fields are the MOVER'S plane (`plane`, from the report),
    # NOT computed from the destination -- so the invariant in (a) is the only
    # thing keeping the word true of the point. That is precisely why it is
    # worth a guard: when the term is off the message is not merely long, it is
    # INTERNALLY INCONSISTENT, telling the client "walk to this point, which is
    # on plane 0" about a point on plane 29.
    check(mv[0][1][2] == 0 and mv[0][1][3] == 0
          and mv[0][1][2] == mesh.plane_at(*mv[0][1][1]),
          "the plane WORDS the grant carries equal the plane the granted "
          "POINT is actually on",
          f"words {mv[0][1][2]},{mv[0][1][3]} point plane "
          f"{mesh.plane_at(*mv[0][1][1])}")
    _saved_lp = authsrv.A2_LEAD_PLANE_CLIP
    try:
        authsrv.A2_LEAD_PLANE_CLIP = False
        st2 = {"pos": (1000.0, 2000.0), "plane": 0, "pos_seen": 0.0,
               "pathmap": _Stairs()}
        st2, w2 = drive_heading(FAR, lead=True, state=st2)
    finally:
        authsrv.A2_LEAD_PLANE_CLIP = _saved_lp
    mv2 = w2.of(MOVE)
    check(len(mv2) == 1 and mv2[0][1][2] == 0
          and mesh.plane_at(*mv2[0][1][1]) == 29,
          "KNOWN-BAD ARM: the word says plane 0 and the point is on plane 29 "
          "-- the grant contradicts itself, which is the failure (c) exists to "
          "catch and which no length check would have seen",
          f"words {mv2[0][1][2]},{mv2[0][1][3]} point plane "
          f"{mesh.plane_at(*mv2[0][1][1])}")

    # ---- (d) THE REFRESH RIDES THE SAME CLIP ------------------------------
    # `kbd_lead_refresh_tick` is the file's OTHER site that puts a lead point on
    # the wire, and 1z-cc's defect was exactly one of two sites missing a term.
    # It re-aims through `a2_clip_lead`, so the seam refuses the extension
    # rather than pushing the destination across it.
    _sv = (authsrv.KBD_SYNC_LEAD_ON, authsrv.KBD_LEAD_REFRESH)
    try:
        authsrv.KBD_SYNC_LEAD_ON, authsrv.KBD_LEAD_REFRESH = True, True
        SP = 190.0
        rleg = {"x0": 1000.5, "y0": 2000.25, "dest": (1100.5, 2000.25),
                "plane": 0, "t0": 100.0, "speed": SP, "wd_fired": False,
                "refreshed": 0}
        eta = 100.0 + 100.0 / SP
        st3 = {"pos": (1000.5, 2000.25), "plane": 0, "kbd_moving_at": 99.0,
               "pathmap": _Stairs(), "kbd_leg": rleg}
        w3, r3 = Sent(st3), FakeRec()
        sent = authsrv.kbd_lead_refresh_tick(
            w3, st3, 1, r3, now=eta - authsrv.KBD_LEAD_REFRESH_MARGIN)
        blocked = [e for e in r3.of("kbd_leg") if e.get("act") == "refresh-blocked"]
        check(sent is False and not w3.of(MOVE) and len(blocked) == 1
              and blocked[0]["why"] == "plane-seam",
              "THE REFRESH cannot push a lead across the seam either: the "
              "extension is clipped back to the leg it already has, nothing "
              "goes out, and the row names the seam as the refusal",
              f"sent={sent} rows={[e.get('act') for e in r3.of('kbd_leg')]}")
    finally:
        (authsrv.KBD_SYNC_LEAD_ON, authsrv.KBD_LEAD_REFRESH) = _sv

    # ---- (e) THE REGRESSION THIS MUST NOT CAUSE ---------------------------
    # Away from the seam the lead keeps its derived 520 u. The 248 u of margin
    # over the client's own report trigger (1z-ab.4) is what stops the copy
    # parking mid-cruise, and an invariant that bought its cleanliness by
    # shortening every lead would be the cure being worse.
    st4 = {"pos": (1000.0, 2000.0), "plane": 0, "pos_seen": 0.0,
           "pathmap": _Stairs()}
    st4, w4 = drive_heading([1, [1000.5, 2000.25], 0, [-766.0, 0.0], 1],
                            lead=True, state=st4)
    row4 = st4["_rec"].of("grant_verdict")[-1]
    mv4 = w4.of(MOVE)
    check(row4["lead_clip_why"] == "clear" and not row4["lead_clipped"]
          and abs(mv4[0][1][1][0] - 480.5) < 1e-6
          and mesh.plane_at(*mv4[0][1][1]) == 0,
          "AIMED AWAY FROM THE SEAM the lead is CLEAR at its full 520 u and "
          "still on the mover's plane -- the invariant costs nothing where "
          "there is no seam to cross",
          f"sent {mv4[0][1][1] if mv4 else None} why={row4['lead_clip_why']}")

    # ---- (f) THE CORPUS NUMBERS ARE AUDITABLE -----------------------------
    # The refutation in this section's header is a claim about 1,086 grants, and
    # a claim that cannot be re-run is an assertion. The census ships with its
    # own bars, INCLUDING the positive control -- without which its zero would
    # be indistinguishable from a broken detector ([[negative-needs-positive-
    # control]]).
    _lp = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                       "studies", "movecode", "review", "leadplane.py")
    _lps = open(_lp, encoding="utf-8").read() if os.path.exists(_lp) else ""
    check(bool(_lps) and "CEIL_ON_CROSS = 0" in _lps
          and "FLOOR_OFF_CROSS" in _lps and "POSITIVE CONTROL" in _lps
          # and it must read the ARM off the capture rather than infer it: an
          # earlier draft inferred it from the `plane-seam` word and mixed the
          # `--lead-seam-clip` arm, which BYPASSES the plane clip, into the
          # segment that is supposed to prove the plane clip works.
          and "A2_LEAD_SEAM_CLIP" in _lps and 'kind") != "flags"' in _lps,
          "the corpus census ships beside this file with a CEILING OF ZERO on "
          "cross-plane grants where the clip is IN FORCE, a FLOOR on what the "
          "same detector must still find where it is not, and it reads the arm "
          "from each capture's own flags row instead of inferring it",
          f"leadplane.py {'found' if _lps else 'MISSING'}")

    print("\n18. MOVECODE-1z-ce: THE WALL SLIDE -- a lead blocked at the body "
          "becomes retail's next-vertex slide along the wall")
    # THE DEFECT, on the tape: RUN-GROUNDZ-R3's stair climb. The client's own
    # vec2 read due east (766.8, 0) on all 15 reports while its collision slid
    # the body 44 deg up the stairs' right side; every lead's ray was blocked at
    # its first 2 u sample, every grant was the report back (why="clipped",
    # arm zero-lead), and the sync copy trailed the drawn body 100-139 u for
    # the climb -- the frame the hostile's disc parks in (R3's six over-40
    # halts). Not the mesh: the body never left our trapezoids by 0.5 u.
    # THE RULE is retail's, measured on the live corpus (wallslide.py --check):
    # of 62 report pairs whose ray our clip blocks at the body, ArenaNet's
    # grant is the NEXT VERTEX of the wall the body presses against, in the
    # heading's slide direction, on 49 -- to 0.0 u on our own decode. The
    # fixture is a lone 100 x 100 square; the report stands on its right side.
    sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))
    import pathmap as _pmod
    _SQ = _pmod.Trapezoid(0, 0, 100.0, 0.0, 0.0, 100.0, 0.0, 100.0,
                          (_pmod.NO_NEIGHBOUR,) * 4)
    _sq = _pmod.PathingMap([_SQ], [{}])
    _sq._cross = {}
    _H = 766.0 / math.sqrt(2.0)                    # north-east, in the vec2 band
    st18 = {"pos": (100.0, 50.0), "plane": 0, "pathmap": _sq}
    lead18 = authsrv.kbd_lead_dest([100.0, 50.0], [_H, _H])[0]
    got, clipped, why = authsrv.a2_clip_lead(st18, [100.0, 50.0], lead18)
    check(clipped and why == "wall-slide" and got == [100.0, 100.0],
          "18a. THE SLIDE: a report on the square's right side heading north-east "
          "-- the ray blocked at its first sample -- is granted the side's next "
          "vertex (100, 100), 50 u up the wall, why=wall-slide",
          f"granted {got} why={why}")
    _saved_ws = authsrv.A2_LEAD_WALL_SLIDE
    try:
        authsrv.A2_LEAD_WALL_SLIDE = False
        g0, c0, w0 = authsrv.a2_clip_lead(st18, [100.0, 50.0], lead18)
    finally:
        authsrv.A2_LEAD_WALL_SLIDE = _saved_ws
    check(c0 and w0 == "clipped" and g0 == [100.0, 50.0],
          "18b. KNOWN-BAD ARM (--no-lead-wall-slide): the same report gets the "
          "shipped-until-now answer, the report itself -- the zero lead R3 sent "
          "15 times",
          f"granted {g0} why={w0}")
    check(authsrv.A2_LEAD_WALL_SLIDE is _saved_ws is True,
          "and the module global is restored after the revert arm")
    lead_e = authsrv.kbd_lead_dest([100.0, 50.0], [766.0, 0.0])[0]
    ge, ce, we = authsrv.a2_clip_lead(st18, [100.0, 50.0], lead_e)
    check(ce and we == "clipped" and ge == [100.0, 50.0],
          "18c. A HEAD-ON PRESS (due east into the side) stays a zero lead: the "
          "heading slides along no wall, and RUN-1zBR's wall press is unchanged",
          f"granted {ge} why={we}")
    lead_w = authsrv.kbd_lead_dest([100.0, 50.0], [-766.0, 0.0])[0]
    gw, cw, ww = authsrv.a2_clip_lead(st18, [100.0, 50.0], lead_w)
    check(cw and ww == "clipped" and gw == [0.0, 50.0],
          "18d. NOT ELIGIBLE: aimed away from the wall the ray runs 100 u to the "
          "far side and is clipped there as before -- the slide is consulted "
          "only when the clip stops within A2_LEAD_WALL_SLIDE_FLOOR of the body",
          f"granted {gw} why={ww} floor {authsrv.A2_LEAD_WALL_SLIDE_FLOOR}")
    lead_s = authsrv.kbd_lead_dest([100.0, 50.0], [_H, -_H])[0]
    gs, cs, ws = authsrv.a2_clip_lead(st18, [100.0, 50.0], lead_s)
    check(cs and ws == "wall-slide" and gs == [100.0, 0.0],
          "18e. heading south-east it slides the other way, to (100, 0): the "
          "direction is the heading's component along the wall",
          f"granted {gs} why={ws}")
    lead_c = authsrv.kbd_lead_dest([100.0, 50.0], [_H, _H])[0]
    _saved_len = authsrv.KBD_SYNC_LEAD
    try:
        authsrv.KBD_SYNC_LEAD = 20.0
        gc, cc, wc = authsrv.a2_clip_lead(st18, [100.0, 50.0], lead_c)
    finally:
        authsrv.KBD_SYNC_LEAD = _saved_len
    check(cc and wc == "wall-slide" and gc == [100.0, 70.0],
          "18f. the slide is capped at the lead's own length along the wall "
          "(KBD_SYNC_LEAD): 20 u of a 50 u wall lands at (100, 70)",
          f"granted {gc} why={wc}")

    # ---- THROUGH THE REAL RECEIVE ARM ----------------------------------
    st18w = {"pos": (100.0, 50.0), "plane": 0, "pos_seen": 0.0, "pathmap": _sq}
    st18w, w18 = drive_heading([1, [100.0, 50.0], 0, [_H, _H], 1],
                               lead=True, state=st18w)
    mv18 = w18.of(MOVE)
    row18 = st18w["_rec"].of("grant_verdict")[-1]
    check(len(mv18) == 1 and mv18[0][1][1] == [100.0, 100.0]
          and mv18[0][1][2] == 0 and mv18[0][1][3] == 0
          and row18["lead_clip_why"] == "wall-slide" and row18["lead_clipped"]
          and row18["lead_src"] == "kbd",
          "18g. ON THE WIRE: the 0x0029 the client receives names the vertex "
          "(100, 100) on plane 0, and the verdict row says wall-slide on a "
          "kbd-sourced lead",
          f"sent {mv18[0][1] if mv18 else None} row {row18.get('lead_clip_why')} "
          f"arm {row18.get('arm')}")
    check(authsrv.capture_flags().get("A2_LEAD_WALL_SLIDE") is True,
          "18h. the switch is in the capture header, so a tape says which arm "
          "produced it", "")

    print("\n19. MOVECODE-1z-cf: THE MODEL'S SLIVER DOOR AND WALL SLIDE -- the "
          "server's own position model takes the lead's two doors")
    # THE DEFECT, on the owner's tape (RUN-FEEL2, 2026-09-06): the client
    # reports from the EDGE class (0.0-0.4 u outside a trapezoid side) while it
    # slides along the stairs' wall, `clip_to_walkable` read that as "standing
    # off the mesh" and SUSPENDED collision, the model walked the raw heading
    # 100-136 u into the wall between reports, and the NPC follow ordered the
    # Hatcher to that phantom: "the player at (10694, 8458)", 145 u off the
    # stairs, the hostile drawn 67-170 u below the owner on the terrain --
    # "falls through the stairs onto the ground below". Same square fixture as
    # section 18; the report stands a twentieth of a unit outside its side.
    SLV = (100.05, 50.0)
    st19 = {"pos": SLV, "plane": 0, "pathmap": _sq}
    got, blocked = authsrv.clip_to_walkable(st19, (SLV[0] + _H, SLV[1] + _H))
    check(got == (100.0, 100.0) and blocked,
          "19a. THE SLIVER DOOR: from 0.05 u outside the side, heading north-east "
          "into the wall, the model leg is the wall's next vertex (100, 100) -- "
          "not the raw 766 u heading",
          f"dest {got} blocked={blocked}")
    _saved_os = authsrv.MODEL_ORIGIN_SEAM
    try:
        authsrv.MODEL_ORIGIN_SEAM = False
        raw, rb = authsrv.clip_to_walkable(st19, (SLV[0] + _H, SLV[1] + _H))
    finally:
        authsrv.MODEL_ORIGIN_SEAM = _saved_os
    check(raw == (SLV[0] + _H, SLV[1] + _H) and not rb,
          "19b. KNOWN-BAD ARM (--model-origin-exact): the same origin suspends "
          "collision and the model walks the whole heading into the wall -- "
          "the phantom the follow aimed at",
          f"dest {raw} blocked={rb}")
    st19i = {"pos": (100.0, 50.0), "plane": 0, "pathmap": _sq}
    got, blocked = authsrv.clip_to_walkable(st19i, (100.0 + _H, 50.0 + _H))
    check(got == (100.0, 100.0) and blocked,
          "19c. an INSIDE origin on the side, same heading: the clip stops at the "
          "body and the slide takes it to the same vertex",
          f"dest {got} blocked={blocked}")
    got, blocked = authsrv.clip_to_walkable(st19i, (100.0 + 766.0, 50.0))
    check(got == (100.0, 50.0) and blocked,
          "19d. a HEAD-ON press into the side slides nowhere: the model stands, "
          "blocked, exactly where the body stands",
          f"dest {got} blocked={blocked}")
    _saved_ws = authsrv.MODEL_WALL_SLIDE
    try:
        authsrv.MODEL_WALL_SLIDE = False
        stood, sb = authsrv.clip_to_walkable(st19i, (100.0 + _H, 50.0 + _H))
    finally:
        authsrv.MODEL_WALL_SLIDE = _saved_ws
    check(stood == (100.0, 50.0) and sb,
          "19e. KNOWN-BAD ARM (--no-model-wall-slide): the blocked leg stands and "
          "the model lags the sliding body",
          f"dest {stood} blocked={sb}")
    got, blocked = authsrv.clip_to_walkable(st19, (SLV[0] - 766.0, SLV[1]))
    check(blocked and got[0] < 20.0 and got[1] == 50.0,
          "19f. from the sliver, a heading AWAY from the wall is clipped on the "
          "plane the edge names and runs the square's width -- the door admits "
          "the origin, it does not lengthen anything",
          f"dest {got} blocked={blocked}")
    st19o = {"pos": (150.0, 50.0), "plane": 0, "pathmap": _sq}
    got, blocked = authsrv.clip_to_walkable(st19o, (150.0 + _H, 50.0 + _H))
    check(got == (150.0 + _H, 50.0 + _H) and not blocked
          and st19o.get("off_mesh_warned") is True,
          "19g. 50 u off the mesh is still off the mesh: the spawn-on-uncovered-"
          "ground door stands, collision suspended and said so",
          f"dest {got} blocked={blocked}")
    st19w = {"pos": SLV, "plane": 0, "pos_seen": 0.0, "pathmap": _sq}
    st19w, w19 = drive_heading([1, [SLV[0], SLV[1]], 0, [_H, _H], 1],
                               lead=True, state=st19w)
    check(st19w.get("dest") == (100.0, 100.0) and st19w.get("clipped") is True
          and w19.of(MOVE) and w19.of(MOVE)[0][1][1] == [100.0, 100.0],
          "19h. THROUGH THE RECEIVE ARM: the model leg and the lead both name "
          "the vertex (100, 100) -- the follow's aim point is on the wall, not "
          "in it",
          f"dest {st19w.get('dest')} lead {w19.of(MOVE)[0][1][1] if w19.of(MOVE) else None}")
    check(authsrv.MODEL_ORIGIN_SEAM is True and authsrv.MODEL_WALL_SLIDE is True
          and "--model-origin-exact" in SRC and "--no-model-wall-slide" in SRC
          and "global MODEL_ORIGIN_SEAM" in SRC and "global MODEL_WALL_SLIDE" in SRC
          and authsrv.capture_flags().get("MODEL_ORIGIN_SEAM") is True
          and authsrv.capture_flags().get("MODEL_WALL_SLIDE") is True,
          "19i. both doors ship ON, each with its own revert rebound through a "
          "declared global, both in the capture header", "")

    # ---- 20. MOVECODE-1z-cg door A: a lead may not END inside a hostile's disc
    # THE DEFECT, on RUN-FEEL2's tape (63.8 s): two leads ended 61 and 78 u from
    # the parked Hatcher, the client's avoidance pass halted world-0 on each
    # (F14/Q8), and the body ran 230 u ahead in 1.2 s. The fixture is a 2000 u
    # square; the hostile is a plain agent record the obstacle list reads at
    # its position.
    print("\n20. MOVECODE-1z-cg door A: the disc")
    _BIG = _pmod.Trapezoid(0, 0, 2000.0, 0.0, 0.0, 2000.0, 0.0, 2000.0,
                           (_pmod.NO_NEIGHBOUR,) * 4)
    _big = _pmod.PathingMap([_BIG], [{}])
    _big._cross = {}

    def _st20(hx, hy, dead=False):
        return {"pos": (100.0, 1000.0), "plane": 0, "pathmap": _big,
                "agents": {10: {"pos": (hx, hy), "dead": dead, "name": "hatcher",
                                "plane": 0}}}
    lead20 = authsrv.kbd_lead_dest([100.0, 1000.0], [766.0, 0.0])[0]
    check(abs(lead20[0] - 620.0) < 1e-6,
          "20-fixture: the raw lead is 520 u east, to x = 620", f"{lead20}")
    g, c, w = authsrv.a2_clip_lead(_st20(600.0, 1000.0), [100.0, 1000.0], lead20)
    check(c and w == "clear+disc-past" and abs(g[0] - 692.0) < 1e-6 and abs(g[1] - 1000.0) < 1e-6,
          "20a. THE DOOR: a lead ending 20 u from a hostile is pushed along its "
          "own ray to one radius PAST the disc -- x = 600 + 80 + 12 = 692, "
          "why=clear+disc-past",
          f"granted {g} why={w}")
    g, c, w = authsrv.a2_clip_lead(_st20(1300.0, 1000.0), [100.0, 1000.0], lead20)
    check(not c and w == "clear" and abs(g[0] - 620.0) < 1e-6,
          "20b. a hostile 680 u off the dest changes nothing: the door reads the "
          "DEST, not the ray", f"granted {g} why={w}")
    g, c, w = authsrv.a2_clip_lead(_st20(600.0, 1000.0, dead=True), [100.0, 1000.0], lead20)
    check(not c and w == "clear" and abs(g[0] - 620.0) < 1e-6,
          "20c. a corpse is not in the pass (F14): the dead hostile's disc holds "
          "nothing", f"granted {g} why={w}")
    _saved_dc = authsrv.A2_LEAD_DISC_CLEAR
    try:
        authsrv.A2_LEAD_DISC_CLEAR = False
        g, c, w = authsrv.a2_clip_lead(_st20(600.0, 1000.0), [100.0, 1000.0], lead20)
    finally:
        authsrv.A2_LEAD_DISC_CLEAR = _saved_dc
    check(not c and w == "clear" and abs(g[0] - 620.0) < 1e-6,
          "20d. KNOWN-BAD ARM (--no-lead-disc-clear): the lead ends inside the "
          "disc, where the client halts world-0 -- FEEL2's stall",
          f"granted {g} why={w}")
    # the mesh ends at x = 2000: a hostile at 1950 cannot be passed, so the
    # lead stops one radius short of its disc instead.
    st20s = _st20(1950.0, 1000.0)
    st20s["pos"] = (1500.0, 1000.0)
    lead20s = authsrv.kbd_lead_dest([1500.0, 1000.0], [766.0, 0.0])[0]
    g, c, w = authsrv.a2_clip_lead(st20s, [1500.0, 1000.0], lead20s)
    check(c and w == "clipped+disc-short" and abs(g[0] - (1950.0 - 80.0 - 12.0)) < 1e-6,
          "20e. where the mesh cannot carry the lead past the disc it ends one "
          "radius SHORT of it: x = 1950 - 92 = 1858, why=clipped+disc-short",
          f"granted {g} why={w}")
    check(authsrv.A2_LEAD_DISC_CLEAR is True
          and "--no-lead-disc-clear" in SRC and "global A2_LEAD_DISC_CLEAR" in SRC
          and authsrv.capture_flags().get("A2_LEAD_DISC_CLEAR") is True,
          "20f. door A ships ON with its revert, in the capture header", "")

    # ---- 21. MOVECODE-1z-cg door B: the leg must hold from WORLD-0's origin
    # THE DEFECT: the lead to (11245, 9428) was clear from the report but the
    # client baked it from its stalled world-0 at (11387, 8762), through the
    # hole above the stairs, and gate 2 snapped the body into it. The fixture
    # is a stub mesh with a hole: walkable everywhere except the square
    # [200, 300] x [950, 1050]; route() goes round by the hole's top-left
    # corner. The guard is a stub holding the mirror's world-0.
    print("\n21. MOVECODE-1z-cg door B: the world-0 origin")

    class _Hole:
        def __init__(self):
            self.routes = 0

        def _in_hole(self, x, y):
            return 200.0 <= x <= 300.0 and 950.0 <= y <= 1050.0

        def walkable(self, x, y):
            return not self._in_hole(x, y)

        def on_mesh(self, x, y, tol=1.0):
            return self.walkable(x, y)

        def plane_at(self, x, y, prefer=None):
            return 0

        def plane_near(self, x, y, prefer=None):
            return 0

        def planes_at(self, x, y):
            return {0} if self.walkable(x, y) else set()

        def containing(self, x, y):
            # the send choke's plane echo reads trapezoid planes here (1z-cl:
            # the chain's send runs through the real choke in this test)
            class _T:
                plane = 0
            return [_T()] if self.walkable(x, y) else []

        def clip(self, x0, y0, x1, y1, step=2.0, plane=None):
            d = math.hypot(x1 - x0, y1 - y0)
            n = max(1, int(d / step))
            last = (x0, y0)
            for i in range(1, n + 1):
                f = i / n
                p = (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
                if self._in_hole(*p):
                    return last
                last = p
            return (x1, y1)

        def route(self, x0, y0, x1, y1, **kw):
            self.routes += 1
            if self.clip(x0, y0, x1, y1) == (x1, y1):
                return [(x0, y0), (x1, y1)]
            return [(x0, y0), (190.0, 1060.0), (x1, y1)]

    class _Guard:
        def __init__(self, w0):
            class _S:
                pass
            self.mirror = _S()
            self.mirror.sync = _S()
            self.mirror.sync.plane = 0
            self.mirror.sync.position = lambda ms, _w=w0: _w

        def _ms(self, now):
            return 0

        def __getattr__(self, name):
            # the report and send paths call the real guard's hooks; a stub
            # that raised there would get the guard DISABLED mid-check
            return lambda *a, **k: None

    _hole = _Hole()
    R21 = [250.0, 1200.0]                     # above the hole; the ray east is clear
    lead21 = authsrv.kbd_lead_dest(R21, [766.0, 0.0])[0]
    st21 = {"pos": tuple(R21), "plane": 0, "pathmap": _hole,
            "agtrack_guard": _Guard((150.0, 1000.0))}     # world-0 left of the hole, level with it
    g, c, w = authsrv.a2_clip_lead(st21, R21, lead21)
    check(c and w == "clear+w0-route" and g == [190.0, 1060.0],
          "21a. THE DOOR: the ray from the report is clear, but the leg from "
          "world-0 crosses the hole, so the lead is the corridor's first vertex "
          "from world-0 -- why=clear+w0-route",
          f"granted {g} why={w}")
    st21b = dict(st21, agtrack_guard=_Guard((250.0, 1150.0)))   # world-0 just behind the body
    g, c, w = authsrv.a2_clip_lead(st21b, R21, lead21)
    check(not c and w == "clear" and abs(g[0] - 770.0) < 1e-6,
          "21b. a world-0 whose leg to the dest holds gets the lead unchanged",
          f"granted {g} why={w}")
    st21c = {"pos": tuple(R21), "plane": 0, "pathmap": _hole}
    g, c, w = authsrv.a2_clip_lead(st21c, R21, lead21)
    check(not c and w == "clear" and abs(g[0] - 770.0) < 1e-6,
          "21c. no guard, no mirror (a bare machine): the door is skipped, not "
          "guessed", f"granted {g} why={w}")
    st21d = dict(st21, agtrack_guard=_Guard((250.0, 1000.0)))   # world-0 already IN the hole
    g, c, w = authsrv.a2_clip_lead(st21d, R21, lead21)
    check(not c and w == "clear" and abs(g[0] - 770.0) < 1e-6,
          "21d. a world-0 already off the mesh has no leg to hold: unchanged "
          "(the guard's gate-2 re-pin is that case's door)", f"granted {g} why={w}")
    _saved_wo = authsrv.A2_LEAD_W0_ORIGIN
    try:
        authsrv.A2_LEAD_W0_ORIGIN = False
        g, c, w = authsrv.a2_clip_lead(st21, R21, lead21)
    finally:
        authsrv.A2_LEAD_W0_ORIGIN = _saved_wo
    check(not c and w == "clear" and abs(g[0] - 770.0) < 1e-6,
          "21e. KNOWN-BAD ARM (--no-lead-w0-origin): the clear-from-the-report "
          "lead goes out, and the client walks world-0 through the hole",
          f"granted {g} why={w}")

    class _NoRoute(_Hole):
        def route(self, *a, **kw):
            return None
    st21f = dict(st21, pathmap=_NoRoute())
    g, c, w = authsrv.a2_clip_lead(st21f, R21, lead21)
    check(c and w == "clear+w0-clip" and g[0] < 200.0 and 1000.0 <= g[1] <= 1020.0,
          "21f. no route from world-0: the lead is the clip's stop on the leg "
          "from world-0, before the hole -- why=clear+w0-clip",
          f"granted {g} why={w}")
    check(authsrv.A2_LEAD_W0_ORIGIN is True
          and "--no-lead-w0-origin" in SRC and "global A2_LEAD_W0_ORIGIN" in SRC
          and authsrv.capture_flags().get("A2_LEAD_W0_ORIGIN") is True,
          "21g. door B ships ON with its revert, in the capture header", "")
    # 21h. MOVECODE-1z-cj (a): the corridor vertex is checked against every
    # hostile disc -- the client halts world-0 on a vertex a disc covers (F14;
    # session 3's 68.5 s snap). The hostile stands ON the corner (190, 1060);
    # the next point is the dest, whose leg from world-0 crosses the hole, so
    # the answer is the leg's last on-mesh point.
    st21h = dict(st21, agents={10: {"pos": (190.0, 1060.0), "dead": False,
                                    "name": "hatcher", "plane": 0}})
    g, c, w = authsrv.a2_clip_lead(st21h, R21, lead21)
    check(c and w == "clear+w0-clip" and g[0] < 200.0 and 1000.0 <= g[1] <= 1020.0,
          "21h. a corridor vertex INSIDE a hostile's disc is skipped (the client "
          "would halt world-0 on it): the next point's leg fails the hole, so the "
          "leg's last on-mesh point -- why=clear+w0-clip",
          f"granted {g} why={w}")

    # ---- 22. MOVECODE-1z-cj (b): the client's OWN reseed stamps the latch
    # RUN-1zCG session 3, 68.5 s: the client's separation gate snapped the body
    # 255 u back onto world-0 and shut its fence for 6.4 s; our latch knew only
    # our own 0x002C, kept leading into the window, and the body walked the
    # leads as click-orders at 190 u/s while the owner's keys were dead. The
    # wire shows the reseed: the next report lands ON the mirror's world-0
    # (3 u) while the position model expected the body 373 u away.
    print("\n22. MOVECODE-1z-cj: the client's own reseed, read off the report")
    st22 = {"pos": (1400.0, 2000.0), "plane": 7, "pos_seen": 0.0,
            "kbd_moving_at": _t.time() - 0.3, "reseed_prev_onto": 236.0,   # the body WAS away
            "agtrack_guard": _Guard((1000.0, 2000.0))}   # world-0 where the report lands
    st22, w = drive_heading(REPORT, lead=True, state=st22)
    frows = st22["_rec"].of("fence")
    row = st22["_rec"].of("grant_verdict")[-1]
    check(st22.get("fence_shut_at") is not None
          and st22.get("fence_pin_pt") == (1000.5, 2000.25)
          and frows and frows[-1]["act"] == "shut" and frows[-1]["by"] == "client-reseed"
          and frows[-1]["jump"] >= 399.0 and frows[-1]["onto"] <= 1.0
          and row["lead_clip_why"] == "fence-shut",
          "22a. THE RESEED: a report 400 u off the model that lands on the mirror's "
          "world-0 stamps the latch with itself as the pin (by=client-reseed), and "
          "the lead of that report degrades -- no lead into the client's own window",
          f"shut_at {st22.get('fence_shut_at')} pin {st22.get('fence_pin_pt')} fence {frows} why {row['lead_clip_why']}")
    st22b = {"pos": (1400.0, 2000.0), "plane": 7, "pos_seen": 0.0,
             "kbd_moving_at": _t.time() - 0.3, "reseed_prev_onto": 236.0,
             "agtrack_guard": _Guard((1400.0, 2000.0))}   # world-0 at the model, 400 u from the report
    st22b, w = drive_heading(REPORT, lead=True, state=st22b)
    check(st22b.get("fence_shut_at") is None
          and w.of(MOVE) and "KBD LEAD" in w.of(MOVE)[0][2],
          "22b. the same jump NOT onto world-0 is a body that walked: no stamp, "
          "the lead fires", f"shut_at {st22b.get('fence_shut_at')}")
    st22c = {"pos": (1000.0, 2000.0), "plane": 7, "pos_seen": 0.0,
             "kbd_moving_at": _t.time() - 0.3, "reseed_prev_onto": 236.0,
             "agtrack_guard": _Guard((1000.0, 2000.0))}   # on world-0, but no jump
    st22c, w = drive_heading(REPORT, lead=True, state=st22c)
    check(st22c.get("fence_shut_at") is None,
          "22c. a report on world-0 with no jump is the ordinary case: no stamp",
          f"shut_at {st22c.get('fence_shut_at')}")
    st22p = {"pos": (1400.0, 2000.0), "plane": 7, "pos_seen": 0.0,
             "kbd_moving_at": _t.time() - 0.3, "reseed_prev_onto": 5.0,      # parked on world-0 before
             "agtrack_guard": _Guard((1000.0, 2000.0))}
    st22p, w = drive_heading(REPORT, lead=True, state=st22p)
    check(st22p.get("fence_shut_at") is None and w.of(MOVE) and "KBD LEAD" in w.of(MOVE)[0][2]
          and abs(st22p.get("reseed_prev_onto", -1) - 0.56) < 0.1,
          "22c'. the same jump onto world-0 from a body that was ALREADY on it is a "
          "wandered model, not a reseed (the census's 19): no stamp, the lead fires, "
          "and the report's own distance is remembered for the next one",
          f"shut_at {st22p.get('fence_shut_at')} prev {st22p.get('reseed_prev_onto')}")
    _saved_crl = authsrv.CLIENT_RESEED_LATCH
    try:
        authsrv.CLIENT_RESEED_LATCH = False
        st22d = {"pos": (1400.0, 2000.0), "plane": 7, "pos_seen": 0.0,
                 "kbd_moving_at": _t.time() - 0.3, "reseed_prev_onto": 236.0,
                 "agtrack_guard": _Guard((1000.0, 2000.0))}
        st22d, w = drive_heading(REPORT, lead=True, state=st22d)
    finally:
        authsrv.CLIENT_RESEED_LATCH = _saved_crl
    check(st22d.get("fence_shut_at") is None and w.of(MOVE) and "KBD LEAD" in w.of(MOVE)[0][2],
          "22d. KNOWN-BAD ARM (--no-client-reseed-latch): the reseed goes unseen and "
          "the lead goes into the client's shut window -- session 3's enslaved walk",
          f"shut_at {st22d.get('fence_shut_at')}")
    check(authsrv.CLIENT_RESEED_LATCH is True and "--no-client-reseed-latch" in SRC
          and "global CLIENT_RESEED_LATCH" in SRC
          and authsrv.capture_flags().get("CLIENT_RESEED_LATCH") is True
          and authsrv.CLIENT_RESEED_JUMP == 150.0 and authsrv.CLIENT_RESEED_ONTO == 24.0
          and authsrv.CLIENT_RESEED_PREV_FAR == 100.0,
          "22e. ships ON with its revert, in the header; the thresholds are the "
          "session's own numbers with room (373 / 9.5 / 236 measured)", "")

    # 21i. MOVECODE-1z-cl: door B never names the vertex world-0 stands on.
    # RUN-1zCG session 4: route() from an origin stepped onto the mesh
    # returned the copy's own point as path[1] -- a 0 u lead that cost a
    # whole heading floor (93.83 s: "(10238,7992) leg 0 u"). world-0 sits ON
    # the stub corridor's vertex (190, 1060); the leg to the dest crosses the
    # hole, so the answer is the leg's last on-mesh point, not the vertex.
    print("\n21i. MOVECODE-1z-cl: the vertex world-0 already stands on is skipped")
    st21i = {"pathmap": _Hole(), "agtrack_guard": _Guard((190.0, 1060.0))}
    d21i, tag21i = authsrv._lead_origin_door(st21i, [350.0, 940.0], st21i["pathmap"])
    check(tag21i == "w0-clip" and math.hypot(d21i[0] - 190.0, d21i[1] - 1060.0) > 4.0,
          "21i. path[1] == world-0's own point is skipped; the next point's leg "
          "fails the hole, so the leg's last on-mesh point -- never a 0 u lead",
          f"got {d21i} tag {tag21i}")

    # ---- 23. MOVECODE-1z-cl: the plane words are the mesh's at the two points
    # Session 4, 93.83-96.06 s: door B's vertex (10238,7992) is a plane-0
    # corner, the report was on the stairs (29), the words went out (29, 29),
    # the client's gate 1 snapped the body onto world-0 WITH that word and left
    # it hanging in mid-air, unable to walk (F11; 1z-o.6's shape). Retail's
    # own crossing pair is (destination plane, mover's plane).
    print("\n23. MOVECODE-1z-cl: the lead's plane words are the mesh's, not the report's")

    class _Stairs:
        """x < 500 is ground (plane 0), x >= 500 the stairs (plane 29)."""
        def planes_at(self, x, y):
            return {0} if x < 500.0 else {29}

        def plane_at(self, x, y, prefer=None):
            p = self.planes_at(x, y)
            return prefer if prefer in p else min(p)

    st23 = {"pathmap": _Stairs(), "agtrack_guard": _Guard((450.0, 0.0))}
    check(authsrv.a2_lead_words(st23, (400.0, 0.0), 29) == (0, 0),
          "23a. THE SESSION-4 SHAPE: a ground vertex named by a report on the "
          "stairs, world-0 on the ground -> (0, 0), not (29, 29)",
          f"{authsrv.a2_lead_words(st23, (400.0, 0.0), 29)}")
    check(authsrv.a2_lead_words(st23, (600.0, 0.0), 29) == (29, 0),
          "23b. a destination on the stairs with world-0 still on the ground -> "
          "(29, 0): retail's crossing pair, far plane then the mover's",
          f"{authsrv.a2_lead_words(st23, (600.0, 0.0), 29)}")
    st23b = {"pathmap": _Stairs(), "agtrack_guard": _Guard((650.0, 0.0))}
    check(authsrv.a2_lead_words(st23b, (600.0, 0.0), 29) == (29, 29),
          "23c. both on the stairs -> (29, 29), matched as before",
          f"{authsrv.a2_lead_words(st23b, (600.0, 0.0), 29)}")
    check(authsrv.a2_lead_words({}, (600.0, 0.0), 29, 0) == (29, 0)
          and authsrv.a2_lead_words({"pathmap": _Stairs()}, (600.0, 0.0), 29, 0) == (29, 0),
          "23d. no mesh, or no mirror: the caller's own words stand (the raw "
          "carry arm stays measurable)",
          f"{authsrv.a2_lead_words({}, (600.0, 0.0), 29, 0)}")
    _saved_pw = authsrv.A2_LEAD_PLANE_WORDS
    try:
        authsrv.A2_LEAD_PLANE_WORDS = False
        got23e = authsrv.a2_lead_words(st23, (400.0, 0.0), 29)
    finally:
        authsrv.A2_LEAD_PLANE_WORDS = _saved_pw
    check(got23e == (29, 29),
          "23e. KNOWN-BAD ARM (--no-lead-plane-words): the report's plane on "
          "both words -- session 4's end state", f"{got23e}")
    check(authsrv.A2_LEAD_PLANE_WORDS is True and "--no-lead-plane-words" in SRC
          and "A2_LEAD_PLANE_WORDS" in SRC[SRC.index("global A2_LEAD_W0_ORIGIN"):
                                          SRC.index("global A2_LEAD_W0_ORIGIN") + 200]
          and authsrv.capture_flags().get("A2_LEAD_PLANE_WORDS") is True
          and SRC.count("a2_lead_words(") - SRC.count("def a2_lead_words(") == 4,
          "23f. ships ON with its revert, in the header; the four lead senders "
          "(the arm, the held heading, the refresh, the chain) all ask it", "")

    # ---- 24. MOVECODE-1z-cl: the corridor chain for the player's copy
    # Session 4: world-0 reached each door-B vertex in 0.03-0.7 s and idled for
    # the rest of the 0.5 s heading floor -- 11.6 s over 39 door leads -- while
    # the body ran 288 u/s; six gate-1 snaps. At the mirror's arrival the lead
    # is re-run from the leg's own report and ray through the same doors.
    print("\n24. MOVECODE-1z-cl: a door-B lead chains to the next vertex at the copy's arrival")
    import time as _t

    def _chain_state(w0, t_arrive=0, clip_why="clear+w0-route", fence=None, moving=True):
        g = _Guard(w0)
        g.mirror.sync.t_arrive = t_arrive
        now = _t.time()
        st = {"pos": (400.0, 1000.0), "plane": 0, "pathmap": _Hole(),
              "agtrack_guard": g, "kbd_moving_at": (now - 0.3) if moving else None,
              "fence_shut_at": fence,
              "kbd_leg": authsrv.a2_leg_note((400.0, 1000.0), (190.0, 1060.0), 0, 1, now,
                                             ray=(700.0, 1100.0), clip_why=clip_why)}
        return st

    st24 = _chain_state((190.0, 1060.0))
    w24, r24 = Sent(st24), FakeRec()
    sent24 = authsrv.kbd_lead_chain_tick(w24, st24, 0, r24)
    mv = w24.of(MOVE)
    check(sent24 and mv and "KBD LEAD CHAIN 1" in mv[0][2]
          and abs(mv[0][1][1][0] - 700.0) < 1e-6 and abs(mv[0][1][1][1] - 1100.0) < 1e-6
          and st24["kbd_leg"]["chained"] == 1
          and tuple(st24["kbd_leg"]["dest"]) == (700.0, 1100.0)
          and st24["kbd_leg"]["x0"] == 400.0
          and r24.of("kbd_leg") and r24.of("kbd_leg")[-1]["act"] == "chain",
          "24a. THE CHAIN: world-0 parked on the corridor vertex -> the lead is "
          "re-run from the leg's report and ray, the leg from the vertex is "
          "clear, the ray goes out at once; the leg advances, its origin stays",
          f"sent {sent24} wire {mv} leg {st24['kbd_leg']}")
    st24b = _chain_state((150.0, 1000.0), t_arrive=5000)
    w24b = Sent(st24b)
    check(not authsrv.kbd_lead_chain_tick(w24b, st24b, 0, FakeRec()) and not w24b.of(MOVE)
          and authsrv.kbd_lead_chain_due(st24b, st24b["kbd_leg"], _t.time())[1] == "walking",
          "24b. the copy still walking to the vertex: nothing sent ('walking')", "")
    st24c = _chain_state((190.0, 1060.0), fence=_t.time())
    w24c = Sent(st24c)
    check(not authsrv.kbd_lead_chain_tick(w24c, st24c, 0, FakeRec()) and not w24c.of(MOVE)
          and authsrv.kbd_lead_chain_due(st24c, st24c["kbd_leg"], _t.time())[1] == "fence-shut",
          "24c. the fence shut (ours or the client's, 1z-cj): no chain into it", "")
    # RE-AIMED 2026-09-10 (MOVECODE-1z-di), not deleted: this used to assert
    # that a lead the doors did not move is never chained, which is now the
    # KNOWN-BAD arm's claim (24j pins it there). What stays true on this
    # fixture is the DISTINCTION: a clear leg's chain is the arrival re-grant
    # -- along the leg's own heading from the arrival point, origin moved --
    # never a corridor vertex from the report's ray.
    st24d = _chain_state((190.0, 1060.0), clip_why="clear")
    w24d, r24d = Sent(st24d), FakeRec()
    sent24d = authsrv.kbd_lead_chain_tick(w24d, st24d, 0, r24d)
    mv24d = w24d.of(MOVE)
    check(sent24d and mv24d and "RE-GRANT 1" in mv24d[0][2] and "CHAIN" not in mv24d[0][2]
          and st24d["kbd_leg"]["x0"] == 190.0 and st24d["kbd_leg"]["y0"] == 1060.0
          and r24d.of("kbd_leg") and r24d.of("kbd_leg")[-1]["act"] == "regrant",
          "24d. a lead the doors did not move has no corridor: its chain is the "
          "ARRIVAL RE-GRANT (1z-di), along its own heading from where the copy "
          "stands, never a vertex from the report's ray",
          f"sent {sent24d} wire {mv24d} leg {st24d['kbd_leg']}")
    st24e = _chain_state((150.0, 1000.0))          # parked (t_arrive 0) but never moved
    w24e, r24e = Sent(st24e), FakeRec()
    check(not authsrv.kbd_lead_chain_tick(w24e, st24e, 0, r24e) and not w24e.of(MOVE)
          and st24e["kbd_leg"].get("chain_stopped") is True
          and r24e.of("kbd_leg") and r24e.of("kbd_leg")[-1]["act"] == "chain-stop"
          and not authsrv.kbd_lead_chain_due(st24e, st24e["kbd_leg"], _t.time())[0],
          "24e. NO PROGRESS (the doors give the same vertex again): the chain stops "
          "for this leg, says so once, and stays stopped", f"{r24e.of('kbd_leg')}")
    _saved_ch = authsrv.KBD_LEAD_CHAIN
    try:
        authsrv.KBD_LEAD_CHAIN = False
        st24f = _chain_state((190.0, 1060.0))
        w24f = Sent(st24f)
        got24f = authsrv.kbd_lead_chain_tick(w24f, st24f, 0, FakeRec())
    finally:
        authsrv.KBD_LEAD_CHAIN = _saved_ch
    check(not got24f and not w24f.of(MOVE),
          "24f. KNOWN-BAD ARM (--no-kbd-lead-chain): the vertex waits for the "
          "next heading tick -- session 4's idle", "")
    check(authsrv.KBD_LEAD_CHAIN is True and "--no-kbd-lead-chain" in SRC
          and authsrv.capture_flags().get("KBD_LEAD_CHAIN") is True
          and authsrv.KBD_LEAD_CHAIN_MAX == 12 and authsrv.KBD_LEAD_CHAIN_MARGIN == 0.10
          and SRC.count("kbd_lead_chain_tick(send, state, conn_id, rec)") == 3
          and SRC.index("kbd_lead_chain_tick(send, state, conn_id, rec)")
          > SRC.index("kbd_lead_refresh_tick(send, state, conn_id, rec)"),
          "24g. ships ON with its revert, in the header; polled at all three "
          "tick sites, after the refresh", "")

    # MOVECODE-1z-di: THE ARRIVAL RE-GRANT, the chain's second branch. Retail's
    # server, when its copy reaches the end of a grant and the client has said
    # nothing since, sends the next chord along the held heading unprompted --
    # 50 first re-grants in the live corpus's true silences, p50 +0.04 s after
    # arrival (Lg / 288), 765 u along the heading and 0.0 u across; 0 of 323
    # full-chord silences carried one before arrival (the trigger is arrival).
    # Ours parked on the lead's end until the next report (1z-cw.6: 255
    # episodes; RUN-1zDB leg 4: 14.6 s, the Hatcher hitting from 161 u).
    def _regrant_state(w0, x0, dest, ray, clip_why="clear", t_arrive=0,
                       moving=True, fence=None):
        g = _Guard(w0)
        g.mirror.sync.t_arrive = t_arrive
        now = _t.time()
        st = {"pos": x0, "plane": 0, "pathmap": _Hole(), "agtrack_guard": g,
              "kbd_moving_at": (now - 0.3) if moving else None,
              "fence_shut_at": fence, "dest": dest,
              "kbd_leg": authsrv.a2_leg_note(x0, dest, 0, 1, now, ray=ray,
                                             clip_why=clip_why)}
        return st

    L = authsrv.KBD_SYNC_LEAD
    st24h = _regrant_state((920.0, 1000.0), (400.0, 1000.0), (920.0, 1000.0),
                           (1167.0, 1000.0))
    w24h, r24h = Sent(st24h), FakeRec()
    sent24h = authsrv.kbd_lead_chain_tick(w24h, st24h, 0, r24h)
    mv = w24h.of(MOVE)
    lg = st24h["kbd_leg"]
    check(sent24h and mv and "KBD LEAD RE-GRANT 1" in mv[0][2]
          and abs(mv[0][1][1][0] - (920.0 + L)) < 1e-6 and abs(mv[0][1][1][1] - 1000.0) < 1e-6
          and lg["chained"] == 1 and lg["x0"] == 920.0 and lg["y0"] == 1000.0
          and tuple(lg["dest"]) == (920.0 + L, 1000.0)
          and tuple(st24h["dest"]) == (920.0 + L, 1000.0)
          and r24h.of("kbd_leg") and r24h.of("kbd_leg")[-1]["act"] == "regrant"
          and r24h.of("kbd_leg")[-1]["origin"] == [920.0, 1000.0],
          "24h. THE ARRIVAL RE-GRANT: world-0 parked on a CLEAR lead's end -> the "
          "next chord goes out from the arrival point along the leg's own heading, "
          "capped like every lead; the leg's origin moves to the arrival point and "
          "the integrator's dest follows",
          f"sent {sent24h} wire {mv} leg {lg} dest {st24h.get('dest')}")

    st24h["agtrack_guard"] = _Guard((920.0 + L, 1000.0))
    st24h["agtrack_guard"].mirror.sync.t_arrive = 0
    w24i = Sent(st24h)
    sent24i = authsrv.kbd_lead_chain_tick(w24i, st24h, 0, FakeRec())
    mv = w24i.of(MOVE)
    check(sent24i and mv and "KBD LEAD RE-GRANT 2" in mv[0][2]
          and abs(mv[0][1][1][0] - (920.0 + 2 * L)) < 1e-6
          and st24h["kbd_leg"]["chained"] == 2 and st24h["kbd_leg"]["x0"] == 920.0 + L,
          "24i. and again at the next arrival, chord by chord, while the client stays "
          "silent -- retail's corpus could not show a second one only because its "
          "1.79 s cadence reports first",
          f"sent {sent24i} wire {mv} leg {st24h['kbd_leg']}")

    st24j = _regrant_state((920.0, 1000.0), (400.0, 1000.0), (920.0, 1000.0),
                           (1167.0, 1000.0))
    w24j = Sent(st24j)
    _saved_ar = authsrv.KBD_LEAD_ARRIVAL_REGRANT
    try:
        authsrv.KBD_LEAD_ARRIVAL_REGRANT = False
        sent24j = authsrv.kbd_lead_chain_tick(w24j, st24j, 0, FakeRec())
        why24j = authsrv.kbd_lead_chain_due(st24j, st24j["kbd_leg"], _t.time())[1]
    finally:
        authsrv.KBD_LEAD_ARRIVAL_REGRANT = _saved_ar
    check(not sent24j and not w24j.of(MOVE) and why24j == "not-a-door-leg"
          and tuple(st24j["dest"]) == (920.0, 1000.0),
          "24j. KNOWN-BAD ARM (--no-arrival-regrant): the copy parks on the lead's "
          "end until the next report -- RUN-1zDB leg 4, where that report never came",
          f"sent {sent24j} why {why24j}")

    st24k = _regrant_state((700.0, 1000.0), (400.0, 1000.0), (920.0, 1000.0),
                           (1167.0, 1000.0), t_arrive=5000)
    w24k = Sent(st24k)
    check(not authsrv.kbd_lead_chain_tick(w24k, st24k, 0, FakeRec()) and not w24k.of(MOVE)
          and authsrv.kbd_lead_chain_due(st24k, st24k["kbd_leg"], _t.time())[1] == "walking",
          "24k. the copy still walking the lead: nothing -- the trigger is ARRIVAL, "
          "which retail's 323 full-chord silences with 0 early grants pin", "")
    st24k2 = _regrant_state((920.0, 1000.0), (400.0, 1000.0), (920.0, 1000.0),
                            (1167.0, 1000.0), moving=False)
    w24k2 = Sent(st24k2)
    check(not authsrv.kbd_lead_chain_tick(w24k2, st24k2, 0, FakeRec()) and not w24k2.of(MOVE)
          and authsrv.kbd_lead_chain_due(st24k2, st24k2["kbd_leg"], _t.time())[1] == "stopped-body",
          "24k2. a 0x0047 cleared the latch: the client spoke, nothing is re-granted", "")

    # A lead whose end sits at a wall, the heading INTO it: the re-grant clips
    # to nothing and the chain stops, saying so.
    st24l = _regrant_state((198.0, 1000.0), (100.0, 1000.0), (198.0, 1000.0),
                           (867.0, 1000.0), clip_why="clipped")
    w24l, r24l = Sent(st24l), FakeRec()
    sent24l = authsrv.kbd_lead_chain_tick(w24l, st24l, 0, r24l)
    rows24l = r24l.of("kbd_leg")
    check(not sent24l and not w24l.of(MOVE) and st24l["kbd_leg"].get("chain_stopped") is True
          and rows24l and rows24l[-1]["act"] == "regrant-stop"
          and rows24l[-1]["why"] == "no-progress",
          "24l. into a wall: the re-grant clips to the point it stands on, makes no "
          "progress, and the chain stops with a row -- a slide to the wall's next "
          "vertex is the clip's own arm's to give, and the corner is a run question",
          f"sent {sent24l} rows {rows24l}")

    check(authsrv.KBD_LEAD_ARRIVAL_REGRANT is True and "--no-arrival-regrant" in SRC
          and authsrv.capture_flags().get("KBD_LEAD_ARRIVAL_REGRANT") is True
          and "KBD LEAD RE-GRANT" in SRC and "MOVECODE-1z-di" in SRC,
          "24n. ships ON with its revert, on the capture's flags row, through the "
          "chain tick's own poll sites", "")

    # MOVECODE-1z-cu. The world tick's integrator walked state["pos"] toward
    # state["dest"] at a flat 14.4 u per tick whatever the 0x003D's movementType
    # said, while a2_leg_note gave the lead model of the SAME heading
    # FAMILY_RATE[mt] * 288 -- so a backpedal was integrated 51% too fast even
    # while the body genuinely moved (sec.1z-cq.5). Measured on our own client
    # before shipping (studies/movecode/review/modelrate.py, 51 captures, 3,372
    # gaps): sustained body rates 0.986 / 0.651 / 0.739 x 288, ratios 0.660 and
    # 0.750 to the table's 0.66 / 0.75; backpedal drift with the body moving
    # 83.4 -> 27.7 u mean, 303 of 390 better, 7 worse by <= 4.9 u.
    print("\n25. MOVECODE-1z-cu: the integrator walks at the family's own rate, "
          "written beside the dest at both sites that arm one")
    MLS = authsrv.model_leg_speed
    check(MLS(1) == 288.0 and MLS(2) == 288.0 and MLS(3) == 288.0
          and abs(MLS(4) - 190.08) < 1e-9 and abs(MLS(6) - 190.08) < 1e-9
          and MLS(7) == 216.0 and MLS(8) == 216.0,
          "25a. THE TABLE, as u/s: forward 288, backpedal 190.08, strafe 216 -- "
          "the numbers a2_leg_note already writes on the kbd_leg row",
          f"{[MLS(m) for m in range(1, 9)]}")
    check(MLS(9) == 288.0 and MLS(None) == 288.0 and abs(MLS(4, base=300.0) - 198.0) < 1e-9,
          "25b. an mt outside the census walks at the base (the sender has already "
          "printed the miss once); the base is a parameter, not a second literal",
          f"{MLS(9)} {MLS(None)} {MLS(4, base=300.0)}")
    _saved_fr = authsrv.MODEL_FAMILY_RATE
    try:
        authsrv.MODEL_FAMILY_RATE = False
        _bad4, _bad8 = MLS(4), MLS(8)
    finally:
        authsrv.MODEL_FAMILY_RATE = _saved_fr
    check(_bad4 == 288.0 and _bad8 == 288.0 and authsrv.MODEL_FAMILY_RATE is True
          and "--no-model-family-rate" in SRC
          and authsrv.capture_flags().get("MODEL_FAMILY_RATE") is True,
          "25c. KNOWN-BAD ARM (--no-model-family-rate): every family walks at 288 "
          "again -- the flat integrator exactly; ships ON, in the capture header",
          f"bad arm {_bad4} {_bad8}")
    # the arm itself, both families, through the shipped 0x003D body
    _back = [1, [1000.5, 2000.25], 7, [-766.0, 0.0], 4]
    s25, _ = drive_heading(_back, lead=True)
    r25 = s25["_rec"]
    _kd = [r for r in r25.of("kbd_dest") if r.get("act") == "arm"]
    _kl = [r for r in r25.of("kbd_leg") if r.get("act") == "arm"]
    check(s25.get("dest") is not None
          and abs(s25.get("dest_speed", 0.0) - 190.08) < 1e-9
          and _kd and abs(_kd[-1].get("speed", 0.0) - 190.08) < 1e-9
          and _kd[-1].get("mt") == 4,
          "25d. a backpedal report (mt 4) arms the model leg WITH its speed beside "
          "the dest, and the kbd_dest row names it",
          f"dest {s25.get('dest')} speed {s25.get('dest_speed')} row {_kd[-1:]}")
    check(_kl and abs(_kl[-1]["speed"] - s25["dest_speed"]) < 1e-9,
          "25e. ONE heading, ONE speed: the lead model's kbd_leg row and the "
          "integrator's dest_speed carry the same number",
          f"kbd_leg {_kl[-1:]} dest_speed {s25.get('dest_speed')}")
    s25f, _ = drive_heading(REPORT, lead=True)
    check(s25f.get("dest_speed") == 288.0,
          "25f. and a forward report (mt 1) arms 288 -- rate 1.0 is the identity, "
          "so every forward gap in the corpus is untouched (2,383 of 2,383)",
          f"{s25f.get('dest_speed')}")
    # THE SPECIMEN, session 7 t=49.726 (authsrv-20260908T230801-c1): mt 6, a
    # 0.752 s gap, 15 ticks, the body moved 140.8 u. The shipped integrator's
    # own recorded output (`ours` at the closing report) is reproduced from
    # the rule first -- 15 x 14.4 = 216.0 u, 75.15 u from the body -- and then
    # the fixed rule on the same direction lands 1.71 u from it.
    _p0 = (10513.2958984375, 8031.15625)
    _p1 = (10583.6474609375, 7909.134765625)
    _m1 = (10621.183225046416, 7844.029755998796)
    _L = math.hypot(_m1[0] - _p0[0], _m1[1] - _p0[1])
    _ux, _uy = (_m1[0] - _p0[0]) / _L, (_m1[1] - _p0[1]) / _L
    _ship = 15 * authsrv.DEFAULT_RUN_SPEED * authsrv.TICK_SECONDS
    _fix = 15 * MLS(6) * authsrv.TICK_SECONDS
    _mf = (_p0[0] + _ux * _fix, _p0[1] + _uy * _fix)
    _d_ship = math.hypot(_m1[0] - _p1[0], _m1[1] - _p1[1])
    _d_fix = math.hypot(_mf[0] - _p1[0], _mf[1] - _p1[1])
    check(abs(_L - 216.0) < 1e-6 and abs(_ship - 216.0) < 1e-9
          and abs(_d_ship - 75.15) < 0.01,
          "25g. THE SPECIMEN, shipped arm reproduced from the rule: 15 ticks x 14.4 "
          "= 216.0 u is exactly the model advance the capture recorded, 75.15 u "
          "from the body",
          f"L {_L:.3f} rule {_ship:.3f} drift {_d_ship:.2f}")
    check(abs(_fix - 142.56) < 1e-9 and _d_fix < 2.0 and _d_fix < _d_ship / 40,
          "25h. the same 15 ticks at the backpedal's 9.504 u: 142.56 u, landing "
          "1.7 u from where the body actually was (75.15 -> 1.71, 98% removed)",
          f"fix {_fix:.3f} drift {_d_fix:.2f}")
    # source pins: the literal is gone from the integrator, the speed is read
    # there once, and written beside the dest at exactly the two arming sites
    _i_int = SRC.index('step = (float(state.get("dest_speed") or DEFAULT_RUN_SPEED)')
    check(SRC.count("DEFAULT_RUN_SPEED * TICK_SECONDS") == 0
          and SRC.count('state.get("dest_speed")') == 1
          and SRC.index("KEEPALIVE re-grant") < _i_int
          < SRC.index("NOTHING IS BROADCAST FROM HERE"),
          "25i. the integrator reads dest_speed ONCE, where the flat literal was, "
          "and the literal is gone from the file",
          f"literal {SRC.count('DEFAULT_RUN_SPEED * TICK_SECONDS')}")
    _i_arm = SRC.index('state["dest_speed"] = model_leg_speed(moving)')
    _i_dest = SRC.index('state["dest"], state["clipped"] = model_dest, blocked')
    check(SRC.count('state["dest_speed"] = model_leg_speed(moving)') == 1
          and 0 < _i_arm - _i_dest < 200
          and SRC.count("model_leg_speed(") == 2,
          "25j. the 0x003D arm writes the speed on the line after the dest it "
          "belongs to, and nothing else consults the table through the helper",
          f"gap {_i_arm - _i_dest} calls {SRC.count('model_leg_speed(')}")
    _i_ap = SRC.index('state["dest_speed"] = speed\n')
    _i_apd = SRC.index('state["dest"] = stop_point if run > 0.0 else None')
    check(SRC.count('state["dest_speed"] = speed\n') == 1 and 0 < _i_ap - _i_apd < 80,
          "25k. the attack approach writes ITS leg's speed (the declared base, a "
          "forward run) beside its dest -- so the integrator never reads a stale "
          "family speed on a click leg",
          f"gap {_i_ap - _i_apd}")
    _i_row = SRC.index('rec.event("kbd_dest", act="arm", mt=moving,')
    check('speed=state["dest_speed"]' in SRC[_i_row:_i_row + 200],
          "25l. the row names its operand: kbd_dest carries the speed it armed", "")

    # MOVECODE-1z-cw. The keyboard arm shared GRANT_MIN_INTERVAL with the click
    # arm, and the constant's own derivation (a) had read retail's 0.49 s median
    # inter-grant gap as a floor: it is the CLIENT's re-report cadence, because
    # ArenaNet answers every 0x003D -- 70.3% of its heading reports arrive inside
    # 0.5 s of the previous player grant and 99.5% of those are answered in 35 ms
    # (26 live connections, 2,800 reports; studies/movecode/review/floorcensus.py).
    # On our five hand-driven sessions the floor refused 57.6% of evaluations and
    # 67% of ALL along-track lag between world-0 and the drawn body accrued under
    # those refusals -- the whole of the felt reach at a hostile's halt (1z-cv).
    print("\n26. MOVECODE-1z-cw: the keyboard arm answers every heading report -- "
          "retail's contract; the floor is the revert arm")
    _hg_i = SRC.index("def _heading_grant_ok(")
    _hg_body = SRC[_hg_i:SRC.index("\ndef ", _hg_i + 10)]
    check(authsrv.KBD_GRANT_FLOOR == 0.0 and "--kbd-grant-floor" in SRC
          and authsrv.capture_flags().get("KBD_GRANT_FLOOR") == 0.0
          and "since < KBD_GRANT_FLOOR:" in _hg_body
          and "GRANT_MIN_INTERVAL:" not in _hg_body,
          "26a. ships at 0.0, the predicate reads the keyboard arm's OWN floor and "
          "no longer the click arm's, and the capture header carries it by name "
          "(a float the bool sweep cannot see)",
          f"floor {authsrv.KBD_GRANT_FLOOR} header {authsrv.capture_flags().get('KBD_GRANT_FLOOR')}")
    st26, w26 = drive_heading(REPORT, lead=True, since=0.1)
    check(len(w26.of(MOVE)) == 1 and st26.get("heading_hold") is None
          and st26["_rec"].of("grant_verdict")[-1]["reason"] == "zero-lead",
          "26b. a report 0.1 s after the last grant is ANSWERED at once -- no refusal, "
          "no hold (retail: 99.5% of such reports answered, p50 35 ms)",
          f"sent {w26.of(MOVE)} hold {st26.get('heading_hold')}")
    v_now = authsrv._heading_grant_ok({"grant_at": 1000.0}, 1000.0)
    v_skew = authsrv._heading_grant_ok({"grant_at": 1001.0}, 1000.0)
    check(v_now == (True, "zero-lead", 0.0) and v_skew[:2] == (False, "heading-rate"),
          "26c. two reports at the SAME instant both grant, and a grant stamped in the "
          "future still refuses -- the comparison is unchanged, only its operand",
          f"now {v_now} skew {v_skew}")
    _sv = authsrv.KBD_GRANT_FLOOR
    try:
        authsrv.KBD_GRANT_FLOOR = 0.5
        st26d, w26d = drive_heading(REPORT, lead=True, since=0.1)
    finally:
        authsrv.KBD_GRANT_FLOOR = _sv
    check(not w26d.of(MOVE) and st26d.get("heading_hold") is not None,
          "26d. KNOWN-BAD ARM (--kbd-grant-floor 0.5): the same report is refused "
          "and held, exactly the arm that shipped 2026-08-20 -> 2026-09-09",
          f"sent {w26d.of(MOVE)}")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
