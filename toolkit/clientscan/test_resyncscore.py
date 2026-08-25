#!/usr/bin/env python3
"""THE COUNTERFACTUAL SCORER, and the ways a counterfactual lies.

    python toolkit/clientscan/test_resyncscore.py

WHAT THIS IS REALLY CHECKING. `resyncscore.py` answers "what would the 0x002C
resync have done?" against captures already on disk. That question has three
failure modes this arc has already paid for, and each has a section here.

  1. A RULE THAT AGREES WITH ITSELF. A decision rule replayed against the data
     that suggested it will always look good. So the load-bearing section is
     §15, the RETAIL CONTROL: ArenaNet's own traffic scores ZERO hard jumps on
     `movesync`'s two arms, so a rule that fires on retail as often as on our
     defective build is reading the wire and not the defect. It is written so
     it CAN fail and it currently DOES fail for two of the five rules -- Rule C
     fires 4.13x more often on retail than on the build we ship, and Rule D
     0.816x. Those two failures are PINNED, not tolerated: a session that
     "improves" C without re-running the control turns this section red.
     §17 is the same argument one level down and it prices every threshold in
     the file: ArenaNet's own copies sit **p50 83 u, p75 260 u, p90 653 u**
     apart with zero snaps, so a resync threshold of 100 u sits at retail's
     MEDIAN.
  2. A COST QUOTED IN THE WRONG UNITS. `studies/movement/HANDOFF.md` §6 records
     a fix that bounded warp SIZE while the harm arrived as FREQUENCY. So §6-§9
     pin the yank's brackets and the self-minted-jump count, and §9 asserts the
     self-mint threshold IS `movesync.HARD_JUMP_UNITS` by identity rather than
     by value -- a private copy of the constant is how a fix ends up scored on
     a friendlier bar than the defect.
  3. A CONTROL OVER ZERO ROWS. `test_movesync`'s own no-collapse control judged
     zero rows and passed, because `all([])` is True. Every section here asserts
     its population FIRST, and the retail control refuses outright rather than
     returning a comfortable zero over an empty corpus.

AND ONE MORE, WHICH IS THE REASON §14 EXISTS. The prompt this file was written
from described `20260811T173940` as a retail/live capture. It is not:
`origin.origin_of` says `ours`, build 38797, and it sits in `captures/gamesrv/`.
§14 pins that, because a control that is secretly a treatment is the failure
`toolkit/origin.py` was written to prevent, and a document has already made this
mistake once.

AND THE ONE THING THIS FILE ASSERTS THAT IS NOT ABOUT THIS FILE. Rule E is a
FORWARD MODEL of the client's authoritative copy -- four assumptions stacked,
which `movesync.py`'s header refuses for exactly this reason. §18 is the check
that can refute it, and it does not: paired against `movetap-20260819T145939`,
a `ReadProcessMemory` of `[agentMgr+0xE8]` in the very session capture
`20260819T145717` recorded, the model sits **p50 0.0 u** from what the client's
own memory held over n = 251, and the separation it computes reproduces
`studies/movement/HANDOFF.md` section 1's **1,164 / 2,163 / 3,648 u** exactly --
from grants on the wire, by a path that never opens the movetap file to compute
them.

Sections 1-12 are pure logic and run on a bare machine. 13-14 replay
`captures/gamesrv`, 15-17 `captures/live`, 18-19 need both plus
`captures/movetap`, and each group declares its own `LEDGER.skip`.
"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))

import checks       # noqa: E402
import movesync     # noqa: E402
import origin       # noqa: E402
import resyncscore  # noqa: E402
import vaultpath    # noqa: E402

# MEASURED from a real green run on 2026-08-25 (the RESYNC_SEPARATION
# reconciliation: section 0's cross-file pins, section 13's second table at
# the shipped 100.0 cell): 116 checks with the whole vault present, 50 with
# `RURIK_VAULT` pointed at an empty directory (2 declared skips; 98/47 before
# the reconciliation, measured 2026-08-20). Sections 0-12 need no fixture;
# 13-14 replay `captures/gamesrv`, 15-17 `captures/live`, and 18-19 need BOTH
# plus `captures/movetap`, and each group declares its own skip. 50 is the
# bare-machine subset and is the floor -- read off the run, never off a count
# in anybody's head, which is the slip `test_movesync` records against itself.
LEDGER = checks.Ledger("the 0x002C resync, priced against captures we have",
                       floor=50)
check = checks.adopt(LEDGER)

R = resyncscore
GATE = R.RESYNC_SEPARATION


# --------------------------------------------------------------------------
def synth(reports, grants, accepted=None, sent_t=None):
    """A track built by hand, with the same keys `track_from_capture` returns.

    Deliberately NOT a partial dict: a fixture missing a key that the code
    later starts reading fails with a KeyError in the middle of a section,
    which reads as a crash rather than as the fixture being wrong.
    """
    reps = [(t, [x, y], None) for t, x, y in reports]
    rows = movesync.steps(reps)
    return {"label": "synthetic", "origin": origin.OURS, "build": None,
            "reps": reps,
            "accepted": (list(accepted) if accepted is not None
                         else [True] * len(reps)),
            "accept_joined": len(reps), "accept_seen": len(reps),
            "accept_known": True,
            "grants": list(grants), "source": None, "rows": rows,
            "hard_idx": [k for k, r in enumerate(rows)
                         if movesync.hard_step(r)],
            "den": movesync.denominator(reps),
            "sent_0x2c": 0, "sent_t": (list(sent_t) if sent_t else [])}


def walk(n, x0=0.0, dt=0.25, speed=movesync.RUN_SPEED, y=0.0):
    """A client walking east at run speed, one report every `dt`."""
    return [(i * dt, x0 + i * dt * speed, y) for i in range(n)]


def main():
    # ---------------------------------------------------------------- 0
    print("0. the ONE threshold: this file and the server agree, pinned")
    # RECONCILED 2026-08-25. Until then authsrv.py shipped 100.0 while this
    # module's default was GATE1_UNITS = 299.332591, each with its own
    # argument -- two numbers for one dial, and the flag ran at whichever
    # file the reader trusted (followon-notes/p5-resync-disarm.md sec.4.2a
    # called it out; the ruling is recorded on both constants). This check
    # is the reconciliation's enforcement: a rule nothing checks is a wish.
    import authsrv    # the header's sys.path already names the authsrv dir
    check(R.RESYNC_SEPARATION == authsrv.RESYNC_SEPARATION == 100.0,
          f"resyncscore.RESYNC_SEPARATION ({R.RESYNC_SEPARATION}) == "
          f"authsrv.RESYNC_SEPARATION ({authsrv.RESYNC_SEPARATION}) == 100.0",
          "the threshold IS the residual snap magnitude (HOLE B), so a "
          "drifted default here means every table this tool prints prices "
          "a rule the server does not run")
    check(R.GATE1_UNITS == 299.332591 and R.RESYNC_SEPARATION < R.GATE1_UNITS,
          f"and GATE1_UNITS stays the measured client constant "
          f"({R.GATE1_UNITS}), above the shipped threshold",
          "gate 1's cut is a fact about the binary, not a policy dial; the "
          "gap between the two is the headroom the SYNC model gets to be "
          "wrong in before the client's own reconcile is earned")
    check(100.0 in R.THRESH_SWEEP,
          "and the sweep prices the shipped cell",
          "until 2026-08-25 THRESH_SWEEP did not contain the value the "
          "server actually runs, so every printed sweep skipped the one "
          "cell that ships")

    # ---------------------------------------------------------------- 1
    print("1. leg_distance is the SEGMENT distance, not the line's")
    # `movesync.on_segment` gives the perpendicular to the INFINITE line. Past
    # the end of a leg that number is small and the truth is not, which is the
    # difference between a lower bound and a comfortable one.
    perp, frac = movesync.on_segment([0.0, 0.0], [100.0, 0.0], [500.0, 0.0])
    check(abs(perp) < 1e-6 and frac > 1.0,
          f"on_segment puts a point 400 u past the end at perpendicular "
          f"{perp:.3f} u (fraction {frac:.2f})",
          "the borrowed primitive really does under-report past the end, so "
          "the clamp below is load-bearing rather than decorative")
    check(abs(R.leg_distance([500.0, 0.0], [0.0, 0.0], [100.0, 0.0])
              - 400.0) < 1e-6,
          "and leg_distance clamps it to 400.0 u",
          f"{R.leg_distance([500.0, 0.0], [0.0, 0.0], [100.0, 0.0]):.3f}")
    check(abs(R.leg_distance([-30.0, 40.0], [0.0, 0.0], [100.0, 0.0])
              - 50.0) < 1e-6,
          "and to 50.0 u before the start",
          f"{R.leg_distance([-30.0, 40.0], [0.0, 0.0], [100.0, 0.0]):.3f}")
    check(abs(R.leg_distance([50.0, 7.0], [0.0, 0.0], [100.0, 0.0])
              - 7.0) < 1e-6,
          "and is the plain perpendicular in between (7.0 u)")

    print("\n2. ...and it really is a LOWER BOUND on separation")
    # The premise Rule B rests on: the sync copy is SOMEWHERE on [P_g, D]. The
    # bound has to hold for every such position, so it is checked against a
    # swept one rather than argued for in a comment.
    A, B, P = [0.0, 0.0], [1000.0, 0.0], [400.0, 250.0]
    lb = R.leg_distance(P, A, B)
    seps = [math.hypot(P[0] - (A[0] + f * (B[0] - A[0])),
                       P[1] - (A[1] + f * (B[1] - A[1])))
            for f in [i / 200.0 for i in range(201)]]
    check(len(seps) == 201, f"the sweep produced {len(seps)} sync positions",
          "asserted FIRST -- a bound checked against an empty sweep is `all([])`")
    check(all(s >= lb - 1e-9 for s in seps),
          f"and the bound {lb:.1f} u is <= every one of them "
          f"(min {min(seps):.1f} u)",
          "one position closer than the bound would make every Rule B firing "
          "an assertion rather than a proof")

    # ---------------------------------------------------------------- 3
    print("\n3. Rule A's ARRIVAL MODEL gates, in both directions")
    # A 2,000 u leg at 288 u/s takes 6.944 s. The client walks the other way,
    # so separation is enormous from the first report -- and the rule must
    # still refuse to fire until the modelled arrival.
    reps = [(t, -t * movesync.RUN_SPEED, 0.0)
            for t in [i * 0.25 for i in range(60)]]
    tr = synth(reps, [(0.0, [2000.0, 0.0])])
    early = R.fires(tr, GATE, 0.0, R.RULE_A)
    check(len(early) > 0, f"the fixture produced {len(early)} Rule A firing(s)",
          "asserted FIRST: a gate checked over zero firings is vacuous")
    t_park = 2000.0 / movesync.RUN_SPEED
    check(min(f["t"] for f in early) >= t_park,
          f"and the earliest is at t={min(f['t'] for f in early):.3f}s, at or "
          f"after the modelled arrival t_park={t_park:.3f}s",
          "before t_park the copy is still gliding and there is nothing "
          "parked to be separated from")
    before = [f for f in early if f["t"] < t_park]
    check(not before,
          f"and {len(before)} firing(s) land before it",
          "a single early firing means the model is not being consulted")
    check(all(f["sep"] >= GATE for f in early),
          f"every firing clears the threshold ({GATE:.2f} u)")

    print("\n4. Rule B needs no arrival model, and refuses a client ON the leg")
    on_leg = [(i * 0.25, i * 0.25 * movesync.RUN_SPEED, 0.0)
              for i in range(30)]
    tr_on = synth(on_leg, [(0.0, [3000.0, 0.0])])
    fb_on = R.fires(tr_on, GATE, 0.0, R.RULE_B)
    check(len(tr_on["reps"]) == 30,
          f"the on-leg fixture holds {len(tr_on['reps'])} report(s)",
          "asserted FIRST")
    check(len(fb_on) == 0,
          f"and Rule B fires {len(fb_on)} time(s) while the client walks the "
          f"granted leg",
          "a client doing exactly what it was told is not desynchronised, and "
          "a rule that fires there is measuring the grant")
    off_leg = [(i * 0.25, 500.0, i * 0.25 * movesync.RUN_SPEED)
               for i in range(30)]
    tr_off = synth(off_leg, [(0.0, [3000.0, 0.0])])
    fb_off = R.fires(tr_off, GATE, 0.0, R.RULE_B)
    check(len(fb_off) > 0,
          f"while a client walking PERPENDICULAR to it fires {len(fb_off)} "
          f"time(s)",
          "the same fixture shape in the other direction -- without this the "
          "check above passes for a rule that never fires at all")

    # ---------------------------------------------------------------- 5
    print("\n5. Rule D is a SUBSET of Rule C, structurally")
    reps5 = walk(40)
    grants5 = [(i * 1.0, [i * 300.0 + 4000.0, 900.0]) for i in range(9)]
    tr5 = synth(reps5, grants5)
    fc = R.fires(tr5, GATE, 0.0, R.RULE_C)
    fd = R.fires(tr5, GATE, 0.0, R.RULE_D)
    check(len(fc) > 0, f"Rule C fires {len(fc)} time(s) on the fixture",
          "asserted FIRST -- a subset relation over an empty superset holds "
          "for free")
    check(set(f["t"] for f in fd) <= set(f["t"] for f in fc),
          f"and Rule D's {len(fd)} firing(s) are a subset of them",
          "D is C plus a park gate, so anything D fires on C must fire on too; "
          "if that ever breaks, one of them has stopped being what it says")
    check(len(fd) < len(fc),
          f"and strictly fewer ({len(fd)} < {len(fc)}) on grants superseded "
          f"before arrival",
          "equal counts would mean the park gate is not being applied, which "
          "is the whole difference between the two")
    # ...AND D IS NOT SIMPLY ALWAYS EMPTY. The subset check above is satisfied
    # by a rule that never fires, which is `all([])` wearing a different hat.
    slow = synth(walk(200), [(0.0, [72.0, 0.0]), (20.0, [8000.0, 900.0])])
    fd2 = R.fires(slow, GATE, 0.0, R.RULE_D)
    check(len(fd2) == 1,
          f"and on a leg that DID finish before the next grant, D fires "
          f"{len(fd2)} time(s)",
          "the positive half: without it, every check above passes for a rule "
          "whose park gate is `return False`")

    # ---------------------------------------------------------------- 6
    print("\n6. the COOLDOWN is honoured, and it is the only free parameter")
    reps6 = [(i * 0.25, -i * 0.25 * movesync.RUN_SPEED, 0.0)
             for i in range(80)]
    tr6 = synth(reps6, [(0.0, [10.0, 0.0])])
    f0 = R.fires(tr6, GATE, 0.0, R.RULE_A)
    check(len(f0) > 5, f"at cooldown 0 the rule fires {len(f0)} time(s)",
          "asserted FIRST")
    for cd in (0.5, 1.0, 2.5):
        fx = R.fires(tr6, GATE, cd, R.RULE_A)
        gaps = [fx[i]["t"] - fx[i - 1]["t"] for i in range(1, len(fx))]
        check(len(fx) <= len(f0) and (not gaps or min(gaps) >= cd - 1e-9),
              f"at cooldown {cd:.2f}s: {len(fx)} firing(s), min gap "
              f"{(min(gaps) if gaps else float('inf')):.3f}s",
              "a cooldown that does not bound the gap is a parameter that "
              "does nothing, and it is swept in every table this tool prints")

    print("\n7. raising the THRESHOLD can only remove firings")
    # sorted(), since 2026-08-25: GATE is now 100.0, which sits BELOW the
    # 150.0 that used to follow it, and a monotonicity check over an
    # unsorted axis refutes the axis rather than the rule.
    counts = [len(R.fires(tr6, th, 0.0, R.RULE_A))
              for th in sorted((0.0, 150.0, GATE, 600.0, 1200.0))]
    check(counts[0] > 0, f"the sweep produced counts {counts}",
          "asserted FIRST")
    check(all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1)),
          "and they are monotonically non-increasing",
          "a non-monotone threshold means the rule is not a threshold, and "
          "every sweep table this tool prints would be uninterpretable")

    # ---------------------------------------------------------------- 8
    print("\n8. STALENESS is non-zero exactly where a report was REFUSED")
    reps8 = walk(20)
    acc = [True] * 20
    acc[10] = acc[11] = acc[12] = False       # the trust guard refuses three
    # The grant lands where the client already is, so the leg is over at once
    # and Rule A's park gate is open from the first report -- the section is
    # about the PAYLOAD, and a fixture that never fires would test nothing.
    tr8 = synth(reps8, [(0.0, [0.0, 0.0])], accepted=acc)
    f8 = R.fires(tr8, GATE, 0.0, R.RULE_A)
    check(len(f8) >= 15, f"the fixture fires {len(f8)} time(s)",
          "asserted FIRST")
    at12 = [f for f in f8 if f["i"] == 12]
    check(len(at12) == 1, "including exactly one at the third refused report")
    step = 0.25 * movesync.RUN_SPEED
    check(abs(at12[0]["stale"] - 3 * step) < 1e-6,
          f"whose payload is stale by {at12[0]['stale']:.2f} u = THREE report "
          f"intervals of walking ({3 * step:.2f} u expected -- reports 10, 11 "
          f"and 12 were all refused, so `state['pos']` is still report 9's)",
          "the payload is `state['pos']`, which only an ACCEPTED report moves; "
          "this is the one path by which the proposal can carry a large error")
    clean = [f for f in f8 if f["i"] not in (10, 11, 12)]
    check(clean and all(f["stale"] == 0.0 for f in clean),
          f"and all {len(clean)} firing(s) on adopted reports are stale by 0.0 u",
          "a zero that is zero BY CONSTRUCTION has to be visible as one -- "
          "which is why the tool prints it beside a count of the non-zeros "
          "rather than folding it into a median")

    # ---------------------------------------------------------------- 9
    print("\n9. the YANK brackets, and the self-mint bar is movesync's own")
    f9 = R.fires(tr6, GATE, 0.0, R.RULE_A, )
    row = f9[3]
    check(abs(row["stale"]) < 1e-9,
          "at zero latency the yank is the staleness (0.0 u here)")
    nxt = tr6["reps"][row["i"] + 1][1]
    want = math.hypot(row["payload"][0] - nxt[0], row["payload"][1] - nxt[1])
    check(abs(row["yank"] - want) < 1e-6,
          f"at one report it is the distance to the next report "
          f"({row['yank']:.2f} u)",
          "the two ends of the bracket, so anything in between is a latency "
          "the capture cannot see")
    tr9 = synth(walk(6) + [(1.5, 900.0 + 5 * 0.25 * movesync.RUN_SPEED, 0.0)],
                [(0.0, [0.0, 0.0])], sent_t=[0.0])
    f9b = R.fires(tr9, GATE, 0.0, R.RULE_A)
    mint = [f for f in f9b if f["mints_hard"]]
    check(len(f9b) > 0 and len(mint) == 1,
          f"a planted 900 u step mints exactly {len(mint)} self-jump of "
          f"{len(f9b)} firing(s)")
    check(all(f["mints_hard"] == (f["yank"] >= movesync.HARD_JUMP_UNITS)
              for f in f9b),
          f"and the bar IS `movesync.HARD_JUMP_UNITS` "
          f"({movesync.HARD_JUMP_UNITS:.0f} u), read from the module",
          "asserted against the module's constant and not a copy: a private "
          "number here is how a fix ends up scored on a friendlier bar than "
          "the defect it replaces")
    small = [f for f in R.fires(synth(walk(20), [(0.0, [0.0, 0.0])]),
                                GATE, 0.0, R.RULE_A) if f["mints_hard"]]
    check(len(small) == 0,
          f"while ordinary 72 u walking steps mint {len(small)}",
          "the negative half -- without it the check above passes for a bar "
          "of zero")

    # ---------------------------------------------------------------- 10
    print("\n10. COVERAGE is the interval a firing lands in, and nothing else")
    tr10 = synth(walk(6) + [(1.5, 900.0 + 5 * 0.25 * movesync.RUN_SPEED, 0.0)],
                 [(0.0, [0.0, 0.0])])
    check(len(tr10["hard_idx"]) == 1,
          f"the fixture carries {len(tr10['hard_idx'])} hard jump(s), opening "
          f"at report {tr10['hard_idx'][0]}",
          "asserted FIRST")
    f10 = R.fires(tr10, GATE, 0.0, R.RULE_A)
    cov, unc = R.coverage(tr10, f10)
    check(len(cov) == 1 and not unc,
          f"a firing on that report covers it ({len(cov)} covered, "
          f"{len(unc)} not)")
    shifted = [f for f in f10 if f["i"] != tr10["hard_idx"][0]]
    cov2, unc2 = R.coverage(tr10, shifted)
    check(len(shifted) > 0 and not cov2 and len(unc2) == 1,
          f"and removing it uncovers the jump again ({len(cov2)} covered over "
          f"{len(shifted)} remaining firing(s))",
          "the mutation, in-process: coverage that survives deleting the "
          "firing that produced it is not measuring the firing")
    check(set(cov) <= set(tr10["hard_idx"]),
          "and the covered set is always a subset of the measured jumps")

    # ---------------------------------------------------------------- 11
    print("\n11. REFUSALS -- the tool declines rather than guessing")
    try:
        R.fires(tr10, GATE, 0.0, "E:invented")
        bad_rule = False
    except SystemExit:
        bad_rule = True
    check(bad_rule, "an unknown rule name raises rather than defaulting",
          "a silent default would score one rule under another's name")
    nog = synth(walk(20), [])
    check(R.score(nog, GATE, 0.0, R.RULE_A)["n"] == 0
          and "ZERO player 0x0029" in (R._why_no_fire(nog) or ""),
          "a capture with no player grant declares a NULL with its reason",
          f"{R._why_no_fire(nog)!r} -- a bare 0 beside a rate reads as 'the "
          f"rule is well behaved here' when it means 'the rule could not run'")
    try:
        R.print_retail_control([], R.RULE_A)
        empty_ok = False
    except SystemExit:
        empty_ok = True
    check(empty_ok,
          "and the retail control over ZERO connections REFUSES",
          "this repo's own recorded trap: `all([])` is True, so a control "
          "judging nothing certifies whatever it is asked to")

    print("\n11b. the SYNC MODEL glides at run speed and PARKS")
    # Rule E's model, before any capture touches it. A model that never parks
    # would read every legitimate click-walk as a growing desync, and one that
    # parks instantly would read the whole glide as one.
    # 2,880 u at 288 u/s is a 10.000 s leg, and the fixture runs to 14.75 s so
    # the PARK is inside it -- a fixture that stops before the arrival would
    # leave the park assertion untestable and the check would have to be
    # dropped or fudged, which is how a model ends up with no arrival rule.
    mt = synth(walk(60), [(0.0, [2880.0, 0.0])])
    sm = dict(R.sync_track(mt))
    check(len(sm) == 60, f"the model produced {len(sm)} sample(s)",
          "asserted FIRST")
    check(abs(sm[0.0][0] - 0.0) < 1e-6,
          "it is seeded at the client's first report",
          "the wire offers no other starting point, and seeding it at the "
          "GRANT would make the first leg instantaneous")
    check(abs(sm[5.0][0] - 5.0 * movesync.RUN_SPEED) < 1e-6,
          f"at t=5.0s it has covered {sm[5.0][0]:.1f} u = 5 s at "
          f"{movesync.RUN_SPEED:.0f} u/s")
    check(abs(sm[9.75][0] - 9.75 * movesync.RUN_SPEED) < 1e-6,
          f"it is still gliding at t=9.75s, 0.25 s short of the 10.000 s leg "
          f"({sm[9.75][0]:.1f} u)",
          "the negative half of the park check: without it, a model that "
          "teleported to the destination on the first tick would pass the "
          "one below")
    check(abs(sm[12.0][0] - 2880.0) < 1e-6 and abs(sm[14.5][0] - 2880.0) < 1e-6,
          f"and at t=12.0s and t=14.5s, past it, it PARKS on the granted "
          f"point ({sm[12.0][0]:.1f} u)",
          "a model that overshoots would make separation grow without bound "
          "on its own, which is the defect it is supposed to be measuring")
    mt2 = synth(walk(60), [(0.0, [2880.0, 0.0]), (5.0, [0.0, 0.0])])
    sm2 = dict(R.sync_track(mt2))
    check(abs(sm2[5.0][0] - 5.0 * movesync.RUN_SPEED) < 1e-6
          and sm2[6.0][0] < sm2[5.0][0],
          f"a re-grant re-aims it from where the MODEL has it "
          f"({sm2[5.0][0]:.0f} u), not from the client's report",
          "which is what the client's own bake does -- it reads the sync "
          "agent's +0x78, not anything we sent")

    print("\n12. the rule text is printed for every rule that exists")
    check(set(R.RULE_TEXT) == set(R.RULES),
          f"all {len(R.RULES)} rule(s) carry a printed description",
          "a rule added without one prints a table of numbers with no "
          "statement of what made them -- and section 5's own C/D pair was mislabelled "
          "exactly that way for one revision")
    check(all("assum" in t or "model" in t or "premise" in t or "aimed" in t
              for t in R.RULE_TEXT.values()),
          "and each names its own assumption")

    # ---------------------------------------------------------------- 13-16
    try:
        gs = vaultpath.require_dir("captures", "gamesrv")
        paths = {s: os.path.join(gs, f"authsrv-{s}-c1.jsonl")
                 for s in R.ARC_STAMPS + (R.NULL_STAMP,)}
        missing = [s for s, p in paths.items() if not os.path.isfile(p)]
        if missing:
            raise SystemExit(f"missing captures: {missing}")
    except SystemExit as exc:
        paths = None
        LEDGER.skip("vault replay (13-14)",
                    f"the arc's captures are not reachable here ({exc})")

    if paths:
        print("\n13. the vault replay, pinned at BOTH threshold cells")
        # PINNED so a change to the rule cannot pass unnoticed. The first
        # table was measured from a real run on 2026-08-20 at threshold
        # 299.332591 u (GATE1_UNITS), cooldown 0.0, and they are the numbers
        # the write-up quotes -- it names its cell EXPLICITLY since the
        # 2026-08-25 reconciliation moved the default to 100.0: a pin that
        # silently floats with a default is not a pin. The second table is
        # the SHIPPED cell (100.0), measured 2026-08-25 over the same three
        # captures. One row of the comparison is itself a finding: on
        # 182652, Rule E at 100.0 covers 13 of 13 hard jumps where the
        # fence cell covered 12 -- the lower threshold GAINS a jump, so
        # "raising costs NO coverage (7/7 either way)" was true of the
        # shipped capture and not of the corpus.
        want = {
            "20260819T145717": {R.RULE_A: (116, 3), R.RULE_B: (85, 1),
                                R.RULE_C: (38, 5), R.RULE_D: (4, 2),
                                R.RULE_E: (213, 7)},
            "20260819T171153": {R.RULE_A: (1, 1), R.RULE_B: (7, 0),
                                R.RULE_C: (702, 20), R.RULE_D: (1, 1),
                                R.RULE_E: (66, 20)},
            "20260819T182652": {R.RULE_A: (0, 0), R.RULE_B: (3, 0),
                                R.RULE_C: (318, 13), R.RULE_D: (0, 0),
                                R.RULE_E: (40, 12)},
        }
        want_ship = {
            "20260819T145717": {R.RULE_A: (117, 3), R.RULE_B: (154, 5),
                                R.RULE_C: (39, 5), R.RULE_D: (4, 2),
                                R.RULE_E: (244, 7)},
            "20260819T171153": {R.RULE_A: (2, 1), R.RULE_B: (11, 0),
                                R.RULE_C: (726, 20), R.RULE_D: (2, 1),
                                R.RULE_E: (234, 20)},
            "20260819T182652": {R.RULE_A: (1, 0), R.RULE_B: (5, 0),
                                R.RULE_C: (320, 13), R.RULE_D: (1, 0),
                                R.RULE_E: (110, 13)},
        }
        for thresh, label, table in ((R.GATE1_UNITS, "fence", want),
                                     (100.0, "shipped", want_ship)):
            for stamp, cells in table.items():
                tr = R.track_from_capture(paths[stamp])
                for rule, (n, cov) in cells.items():
                    s = R.score(tr, thresh, 0.0, rule)
                    check(s["n"] == n and len(s["covered"]) == cov,
                          f"{stamp} {rule} @{label}: {s['n']} firing(s), "
                          f"{len(s['covered'])}/{s['hard_n']} covered",
                          f"expected {n} and {cov} -- pinned from a real "
                          f"run (2026-08-20 fence / 2026-08-25 shipped) so "
                          f"a rule change shows up here rather than in a "
                          f"quoted number nobody re-derived")

        ship = R.track_from_capture(paths[R.SHIPPED])
        check(len(ship["hard_idx"]) == 7 and ship["sent_0x2c"] == 0,
              f"the shipped build carries {len(ship['hard_idx'])} hard jump(s) "
              f"and has sent {ship['sent_0x2c']} x 0x002C",
              "the census, re-measured every run: 'we have never sent one' is "
              "a number this run produced, not a sentence from a handoff")
        sA = R.score(ship, GATE, 0.0, R.RULE_A)
        check(sA["atsend_clean_mints"] == 0 and sA["atsend_clean_p50"] < 1.0,
              f"and Rule A's own yank at the landing instant is p50 "
              f"{sA['atsend_clean_p50']:.2f} u, minting "
              f"{sA['atsend_clean_mints']} hard jump(s)",
              "the cost, in the units the harm arrives in")
        check(sA["stale_nonzero"] == 0 and sA["send_p50"] < 0.010,
              f"over a measured send delay of p50 "
              f"{1000 * sA['send_p50']:.2f} ms, {sA['stale_nonzero']} "
              f"firing(s) on a refused payload",
              "both terms of the yank, each from the capture's own clock")
        misses = {r for _k, r, _v in sA["misses"]}
        check(misses == {"not-parked"},
              f"and every uncovered jump is missed for {sorted(misses)}",
              "THE FINDING: the 4 Rule A cannot reach are blocked by the "
              "arrival model, not by a threshold or a cooldown, so no "
              "parameter reaches them")

        print("\n14. 20260811T173940 is OURS, and is the internal null")
        null = paths[R.NULL_STAMP]
        org, why = origin.origin_of(null)
        check(org == origin.OURS,
              f"origin.py classifies it {org!r}",
              f"{why} -- the prompt this file was written from called it "
              f"retail/live; it is our own server, build "
              f"{origin.build_of(null)[0]}, in captures/gamesrv/")
        tn = R.track_from_capture(null)
        check(len(tn["grants"]) == 0 and len(tn["hard_idx"]) == 0,
              f"it holds {len(tn['grants'])} player grant(s) and "
              f"{len(tn['hard_idx'])} hard jump(s)",
              "so the rule cannot fire and there is nothing for it to prevent "
              "-- an internal null, and a consistency check on both halves")
        check("ZERO player 0x0029" in (R._why_no_fire(tn) or ""),
              "and the tool declares that null rather than printing a 0")
        live_one = None
        try:
            import glob
            hits = sorted(glob.glob(vaultpath.vault_path(
                "captures", "live", "*", "game-*.jsonl")))
            live_one = next((p for p in hits
                             if origin.origin_of(p)[0] == origin.LIVE), None)
        except SystemExit:
            live_one = None
        if live_one is None:
            LEDGER.skip("origin pooling",
                        "no live capture to pair against the gamesrv one")
        else:
            check(R.require_single_origin([null]) == origin.OURS,
                  "one origin passes require_single_origin")
            try:
                R.require_single_origin([null, live_one])
                pooled = False
            except SystemExit:
                pooled = True
            check(pooled,
                  "and pooling `ours` with `live` in one run is REFUSED",
                  "each file passes its own per-file check, so this is the "
                  "only place the AVERAGE of two oracles is caught -- and "
                  "`test_movement_fidelity` already pooled a corpus that way")

    try:
        live_root = vaultpath.require_dir("captures", "live")
        retail = R.retail_tracks()
        usable = [t for t in retail if not t.get("refused")]
        if not usable:
            raise SystemExit(f"no usable connection under {live_root}")
    except SystemExit as exc:
        retail = usable = None
        LEDGER.skip("retail control (15-16)",
                    f"the live corpus is not reachable here ({exc})")

    if usable:
        print("\n15. THE RETAIL CONTROL, and two rules currently FAIL it")
        reports = sum(len(t["reps"]) for t in usable)
        hard = sum(len(t["hard_idx"]) for t in usable)
        check(len(usable) >= 30 and reports >= 2500,
              f"the control judges {len(usable)} connection(s) and "
              f"{reports} retail self-report(s)",
              "asserted FIRST and before any zero is believed: a control over "
              "an empty corpus is the shape this suite exists to refuse")
        check(hard == 0,
              f"and retail scores {hard} hard jump(s) on movesync's two arms",
              "this is WHY it is the control -- ArenaNet's own client never "
              "clears the bar, so any firing on this corpus is the rule "
              "reading the wire rather than the defect")
        if paths:
            ship = R.track_from_capture(paths[R.SHIPPED])
            verdicts = {}
            for rule in R.RULES:
                _n, _sp, rate = R.retail_rate(usable, GATE, 0.0, rule)
                ours = R.score(ship, GATE, 0.0, rule)["rate_span"]
                verdicts[rule] = rate / ours if ours > 0 else float("inf")
            check(verdicts[R.RULE_A] < 1.0 / R.DISCRIMINATION
                  and verdicts[R.RULE_B] < 1.0 / R.DISCRIMINATION,
                  f"rules A and B SEPARATE: retail fires "
                  f"{verdicts[R.RULE_A]:.3f}x / {verdicts[R.RULE_B]:.3f}x the "
                  f"shipped build's rate",
                  f"the bar is 1/{R.DISCRIMINATION:.0f}; both are ~40x below "
                  f"the build that has the defect")
            check(verdicts[R.RULE_C] >= 1.0 / R.DISCRIMINATION
                  and verdicts[R.RULE_D] >= 1.0 / R.DISCRIMINATION,
                  f"and rules C and D FAIL it: {verdicts[R.RULE_C]:.3f}x and "
                  f"{verdicts[R.RULE_D]:.3f}x",
                  "PINNED AS A FAILURE, not tolerated. Rule C has the best "
                  "coverage on our own capture (5 of 7) and fires more often "
                  "on traffic with nothing wrong with it; a session that "
                  "'improves' C without re-running this control turns this "
                  "check red, which is the point")
            check(verdicts[R.RULE_C] > 4.0,
                  f"specifically, Rule C fires {verdicts[R.RULE_C]:.2f}x more "
                  f"per minute on retail than on the build we ship",
                  "quoted with its direction, because the number that reads "
                  "as a success on our corpus is the same number that reads "
                  "as a refutation here")
        else:
            LEDGER.skip("retail-vs-ours ratio",
                        "the shipped-build capture is not present, so there "
                        "is nothing to take a ratio against")

        print("\n16. the retail PLAYER AGENT is named, never guessed")
        named = [t for t in usable if t.get("player_agent") is not None]
        check(len(named) == len(usable),
              f"{len(named)} of {len(usable)} usable connection(s) name their "
              f"player from their own 0x0037",
              "a connection with no 0x0037 is refused into the unusable pile "
              "rather than having its busiest agent assumed")
        # A POPULATION FLOOR, and it is a real one rather than a convenience.
        # `20260817T231139 :62132` has 17 reports and THREE rival agents, so
        # its "population median" is the median of three numbers and the chosen
        # agent sits 661 u against 639 u -- not a wrong read, an instance too
        # small to discriminate in. Five rivals is where the ratio stops being
        # noise: over the 20 connections that clear it the margin is 1.12x at
        # worst and 4.43x at the median.
        sigs = [t["sig"] for t in named
                if t["sig"] and math.isfinite(t["sig"]["others_p50"])
                and t["sig"]["others_n"] >= 5]
        thin = len(named) - len(sigs)
        check(len(sigs) >= 20,
              f"and {len(sigs)} of them have >= 5 rival agents to discriminate "
              f"against ({thin} too thin, and named rather than dropped)",
              "asserted FIRST, and the floor is declared: a check whose "
              "population is chosen after seeing which rows pass is not a "
              "check")
        better = sum(1 for s in sigs if s["chosen"] < s["others_p50"])
        near = sum(1 for s in sigs if s["chosen"] <= s["runner_up"])
        check(better == len(sigs),
              f"the named agent beats the POPULATION median of every other "
              f"agent on that connection, {better} of {len(sigs)}",
              "the corroboration the 2026-08-19 corpus pass used: |grant dest "
              "- the client's own report| is p50 765.52 u for the player and "
              "thousands for everything else. A wrong 0x0037 read shows up "
              "here rather than silently choosing a henchman")
        check(near >= 10,
              f"and it is the outright NEAREST agent on {near} of "
              f"{len(sigs)} -- MEASURED, and deliberately not the check",
              "in a crowded instance a henchman walking a step behind the "
              "player produces a signature within a few percent, so the "
              "nearest-rival form separates on 25 of 35 and would be a bar "
              "this corpus fails for a reason that is not an error. The "
              "population median is the form that discriminates; both are "
              "printed so nobody has to take that on trust")
        refused = [t for t in retail if t.get("refused")]
        check(len(refused) > 0,
              f"and {len(refused)} connection(s) were refused outright",
              "the refusal path is exercised on real data, not only asserted "
              "to exist")

        print("\n17. RETAIL'S OWN modelled separation, which is not zero")
        seps = []
        for t in usable:
            for i, (_t, S) in enumerate(R.sync_track(t)):
                P = t["reps"][i][1]
                seps.append(math.hypot(S[0] - P[0], S[1] - P[1]))
        seps.sort()
        p50, p75, p90 = (movesync.pct(seps, q) for q in (0.5, 0.75, 0.9))
        check(len(seps) > 2500,
              f"the model runs over {len(seps)} retail report(s)",
              "asserted FIRST")
        check(70.0 < p50 < 100.0 and 600.0 < p90 < 700.0,
              f"and ArenaNet's own copies sit p50 {p50:.0f} u, p75 {p75:.0f} u, "
              f"p90 {p90:.0f} u apart -- with ZERO snaps",
              "THE NUMBER THAT PRICES A THRESHOLD. Retail is not synchronised "
              "to the unit; it routinely runs hundreds of units apart and "
              "never snaps, which is why 'separation alone' was never the "
              "trigger -- and why a resync threshold at 100 u sits at retail's "
              "own MEDIAN and would fire on half of a healthy session")
        if paths:
            ship = R.track_from_capture(paths[R.SHIPPED])
            ours = []
            for i, (_t, S) in enumerate(R.sync_track(ship)):
                P = ship["reps"][i][1]
                ours.append(math.hypot(S[0] - P[0], S[1] - P[1]))
            om = movesync.pct(sorted(ours), 0.5)
            check(om > 10 * p50,
                  f"while the shipped build sits p50 {om:.0f} u apart, "
                  f"{om / p50:.1f}x retail's",
                  "the separation itself separates, which is what makes the "
                  "rate comparison in section 15 interpretable rather than a "
                  "coincidence of two different maps")

    if paths and usable is not None:
        print("\n18. THE SYNC MODEL, checked against a direct memory read")
        # Rule E is a FORWARD MODEL, which is precisely the "four assumptions
        # stacked under a conclusion" `movesync.py`'s header refuses. This is
        # the check that can refute it, and without it Rule E is not quotable.
        v = R.validation_pair()
        if v is None:
            LEDGER.skip("sync-model validation",
                        "the vault has no movetap run overlapping an arc "
                        "capture, so Rule E is UNCHECKED here")
        else:
            check(v["n"] >= 200,
                  f"{v['n']} client report(s) pair with a movetap sample of "
                  f"[agentMgr+0xE8]",
                  "asserted FIRST -- a model validated against nothing is a "
                  "model nobody validated")
            check(v["residual_p50"] < 5.0 and v["residual_max"] < 100.0,
                  f"and the model sits p50 {v['residual_p50']:.1f} u from what "
                  f"the client's own memory held (p90 {v['residual_p90']:.0f}, "
                  f"max {v['residual_max']:.0f})",
                  "against separations of 1,164 u p50: the model's error is "
                  "two orders of magnitude below the quantity it measures")
            for k, (a, b) in enumerate(zip(v["sep_model"], v["sep_tap"])):
                check(abs(a - b) <= max(1.0, 0.02 * b),
                      f"separation {('p50', 'p90', 'max')[k]}: model "
                      f"{a:.0f} u vs movetap {b:.0f} u",
                      "the two are computed from disjoint sources -- one from "
                      "grants on the wire, one from a ReadProcessMemory of the "
                      "sync array -- so agreement is a fact about the client, "
                      "not about this file")
            check(abs(v["sep_tap"][0] - 1164.0) < 2.0
                  and abs(v["sep_tap"][2] - 3648.0) < 2.0,
                  f"and both reproduce HANDOFF section 1's recorded "
                  f"{v['sep_tap'][0]:.0f} / {v['sep_tap'][1]:.0f} / "
                  f"{v['sep_tap'][2]:.0f} u",
                  "the arc's own headline harm figure, re-derived rather than "
                  "quoted")
            # POSITIVE CONTROL ON THE VALIDATION ITSELF. A residual of ~0 is
            # the answer we wanted, which is exactly when a residual that is
            # STRUCTURALLY 0 -- a comparison that never happens -- is
            # indistinguishable from success. Found by mutation: hard-wiring
            # the residual to 0.0 left this whole section green. So the model
            # is deliberately broken and the same measurement must move.
            cap = paths[R.SHIPPED]
            tap = os.path.join(vaultpath.vault_path("captures", "movetap"),
                               R.VALIDATION[1])
            slow = R.validate_sync_model(cap, tap,
                                         run_speed=movesync.RUN_SPEED / 2)
            check(slow is not None and slow["n"] == v["n"]
                  and slow["residual_p50"] > 50 * max(v["residual_p50"], 1.0),
                  f"and halving the model's speed moves the residual from "
                  f"{v['residual_p50']:.1f} u to "
                  f"{(slow['residual_p50'] if slow else float('nan')):.0f} u "
                  f"over the same {v['n']} pair(s)",
                  "the comparison is real: a p50 of 0.0 that cannot be made "
                  "to move is not a measurement of agreement, it is the "
                  "absence of a measurement")
            check(v["residual_p90"] > 0.0 and v["residual_max"] > 0.0,
                  f"and the residual is not identically zero either "
                  f"(p90 {v['residual_p90']:.0f} u, max "
                  f"{v['residual_max']:.0f} u)",
                  "the cheap half of the same guard")
            # AND THE REFUSAL PATH, which the happy path can never exercise.
            other = os.path.join(vaultpath.vault_path("captures", "movetap"),
                                 "movetap-20260819T171436.jsonl")
            if os.path.isfile(other):
                check(R.validate_sync_model(cap, other) is None,
                      "a movetap run from a DIFFERENT session validates "
                      "nothing and returns None",
                      "no fixture, no answer -- and the alternative found by "
                      "mutation was a function that invented a comfortable "
                      "row when it had none, which no full-vault run would "
                      "ever notice")
            else:
                LEDGER.skip("validation refusal",
                            "no second movetap run to pair wrongly")
            check(R.validate_sync_model(cap, cap + ".nope") is None,
                  "and a missing movetap file does too")

        print("\n19. the COOLDOWN is what costs the coverage, not the threshold")
        ship = R.track_from_capture(paths[R.SHIPPED])
        by_cd = {cd: R.score(ship, GATE, cd, R.RULE_E)
                 for cd in (0.0, 0.5, 2.5)}
        check(len(by_cd[0.0]["covered"]) == by_cd[0.0]["hard_n"],
              f"at cooldown 0.00s Rule E covers "
              f"{len(by_cd[0.0]['covered'])}/{by_cd[0.0]['hard_n']} of the "
              f"shipped build's hard jumps",
              "the protection windows tile the report stream, so every jump "
              "opens on a report where the record had just been cleared")
        check(len(by_cd[0.5]["covered"]) < len(by_cd[0.0]["covered"])
              and len(by_cd[2.5]["covered"]) <= len(by_cd[0.5]["covered"]),
              f"and a 0.50s / 2.50s rate limit drops it to "
              f"{len(by_cd[0.5]['covered'])} / "
              f"{len(by_cd[2.5]['covered'])}",
              "THE ACTIONABLE HALF: the rate limit is not a free safety "
              "margin, it is where the coverage goes")
        yanks = [by_cd[cd]["atsend_clean_p50"] for cd in (0.0, 0.5, 2.5)]
        check(all(y < 1.0 for y in yanks),
              f"while the yank does NOT grow with the rate: p50 "
              + " / ".join(f"{y:.2f}" for y in yanks) + " u",
              "because the payload is always the client's own freshest "
              "adopted report, so firing more often costs frequency and not "
              "magnitude -- which is the asymmetry the whole proposal rests "
              "on")
        # Until 2026-08-25 this cell read "dropping the threshold to 100 u
        # buys NO coverage ... so the threshold trades specificity against
        # nothing here" -- with GATE at the fence, the 100 u arm was the
        # counterfactual. The reconciliation made 100.0 the default (the
        # ruling is on both constants), so the comparison now runs the other
        # way and its finding is restated with the ruling's own framing:
        # hard-jump coverage was NEVER the dial's job (F35's sub-299 family
        # is), it is EQUAL on this capture, the corpus GAINS one jump at the
        # shipped cell (182652: 13 vs 12, pinned in section 13), and the
        # extra firings are the frequency cost the ruling accepted as the
        # cheap axis -- the yank check above is why it is cheap.
        hi = R.score(ship, R.GATE1_UNITS, 0.0, R.RULE_E)
        check(len(by_cd[0.0]["covered"]) == len(hi["covered"])
              and by_cd[0.0]["n"] > hi["n"],
              f"and the shipped 100 u cell holds the fence cell's coverage "
              f"({len(by_cd[0.0]['covered'])} vs {len(hi['covered'])}) at "
              f"{by_cd[0.0]['n'] - hi['n']} extra firing(s) on this capture",
              "coverage equal here, +1 on 182652 (section 13); the extra "
              "firings are frequency, the measured-cheap axis, while the "
              "threshold bounds HOLE B's residual snap -- the thing Q10 "
              "judges")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
