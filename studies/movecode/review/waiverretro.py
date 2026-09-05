#!/usr/bin/env python3
"""RETIRED at MOVECODE-1z-bt: STATIONARY_WAIVER was deleted (PLAN sec.7 Q15, owner's ruling
2026-09-05), so the arms this tool replayed no longer exist in agtrack_guard and main() refuses.
Its published figures stand in FINDINGS sec.1z-bn.3, sec.1z-bo.5 and sec.1z-bs.5; the deleted
build's behaviour on this corpus is its former THIRD arm, identical to the last shipped clause in
every control-OK run.  Kept for the method.

Retrodict the stationary waiver's WALK-START CLAUSE over the corpus (MOVECODE-1z-bn).

    python studies/movecode/review/waiverretro.py --all
    python studies/movecode/review/waiverretro.py 20260905T124559

THE QUESTION.  `agtrack_guard.stationary()` waives the 0.347 s stale-report gate whenever the
last two accepted reports COINCIDE, on the argument that two identical reports MEASURE a still
body, so a re-pin's harm is bounded by ZERO_DIST_SQ rather than by RUN_SPEED * report age.
sec.1z-bl found the pair it almost always fires on is {0x0047 stop -> 0x003D walk-start}: a leg
OPENS by reporting a walk-start at the point the previous leg's stop left the body, identical
to 0.000 u because the body has not moved YET.  That pair measures stillness up to the instant
the client was told to move; the re-pin acts 1-2.4 s later, inside the client's own silent
committed glide.  The windows do not overlap.  `WAIVER_WALKSTART_ENDS_STILL` refuses that one
pair -- newest report is a 0x003D, the one before it a 0x0047 -- and keeps the other two.

WHY NOT guardretro.py: its two arms vary `agtrack_mirror.GATE2_SEAM_TOL` (the sec.1z-bf fix),
and the walk-start clause is ON in both, so it cannot see this change at all.

WHICH CONTROL, and this is the part worth reading.  guardretro scores its arms against each
capture's logged `agtrack_guard` VERDICT rows.  That control is necessary but not sufficient
here: `stationary()` is read only by `_repin_block`, so no verdict can move when the clause
moves -- against the clause it is a check that cannot fail.  It is still what says the REPLAY
is faithful, so it selects the population (a run whose logged verdicts the stock arm cannot
reproduce was recorded by a guard that no longer exists, and nothing it says about a
counterfactual is worth anything).  Inside that population the clause is scored against the
capture's logged `agtrack_repin_fire` rows -- the real 0x002C re-pins the server actually
sent.  The stock arm must predict them; the fix arm must predict FEWER; and each one it drops
is then measured for the REWIND it would have caused, which is what says whether the body it
would have pinned was standing.  That arm can lose.

THE REWIND ESTIMATE.  A dropped re-pin's harm is not the distance between the reports either
side of it -- that is ~512 u by construction, the client's own 0x003D distance trigger, and
would read the same for a body that had not yet moved.  It is how far along that chord the
body had ALREADY travelled when the re-pin fired, because a 0x002C SetPositions both copies
back to the older report.  This file estimates it as chord * (t_repin - t_before) /
(t_after - t_before): constant speed across one cruise chord, an ESTIMATE and labelled one.
sec.1z-bl measured three real rewinds off the agenttap tape at 311-468 u, so the estimate has
an independent number to answer to.

EACH CAPTURE IS REPLAYED AT ITS OWN GATE-2 TOLERANCE, read from its own recorded
`AGTRACK_GATE2_SEAM` flag, and getting this wrong is not a small error.  The first draft
replayed EVERY capture at `GATE2_SEAM_TOL = 0.0` -- pre-sec.1z-bf exact containment -- and
computed the shipped-tolerance arm without ever reading it.  A capture recorded WITH the seam
tolerance then fails a control that is checking it against a guard it never ran, and gets
dropped from the evidence population.  RUN-1zBL, the single run this whole clause was derived
from and A/B'd against, was excluded that way, and the runs such a filter excludes are biased
toward sliver geometry -- which is exactly where `gate2-offmesh` lives, the one class this
clause claims to leave untouched.  A control aimed at the wrong build is not a weak control,
it is a filter.  Found by sec.1z-bo's completeness critic, after the corpus figures it produced
had already been published in sec.1z-bn.

THE THIRD ARM (sec.1z-bo) answers a question sec.1z-bn asserted from the source: is the clause
NARROWER than deleting the stationary waiver, in behaviour?  Every capture is also replayed
with `STATIONARY_WAIVER` off entirely.  It is not a rhetorical arm -- it can and does report a
difference if one exists, and today it reports none.

MOVECODE-1z-bs added a second clause on top of 1z-bn's (`WAIVER_NEWEST_MUST_BE_STOP`: the waiver
requires the newest accepted report to be a stop).  This file's stock and fix arms are the
1z-bn A/B and are replayed with that clause OFF, so they keep measuring what their names say.
The shipped (1z-bs) build's retrodiction is the THIRD arm: its differential set over 1z-bn is
the coincident {0x003D -> 0x003D} pair, which carries zero re-pin wants anywhere in the corpus
(waiverclick.py measures that directly), so on every capture held the shipped build and the
waiver-deleted arm are one object.

Read-only.  Needs the vault.  Stdlib only.  Map 146 only, as guardretro is.
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "mapdata"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "authsrv"))

import guardretro  # noqa: E402  (events(), decode_plain(), MAP146 -- the feed is identical)

MATCH_S = 0.6      # guardretro's pairing window between a predicted DUE and a real fire


def replay(evs, pm, tol, clause, waiver=True):
    """Drive the guard over one capture's feed.  Returns (verdicts, due-transitions).

    Each due-transition carries the guard's own state at that instant -- the pair of report
    KINDS the waiver was looking at, and the newest report's age -- so a dropped re-pin can be
    attributed to the clause rather than merely correlated with it.
    """
    import agtrack_guard as ag
    import agtrack_mirror as am
    s_tol, s_cl, s_w = am.GATE2_SEAM_TOL, ag.WAIVER_WALKSTART_ENDS_STILL, ag.STATIONARY_WAIVER
    s_ns = ag.WAIVER_NEWEST_MUST_BE_STOP
    am.GATE2_SEAM_TOL = tol
    ag.WAIVER_WALKSTART_ENDS_STILL = clause
    ag.STATIONARY_WAIVER = waiver
    # The 1z-bs clause is pinned OFF in every arm here: this file is the 1z-bn A/B and the
    # clause subsumes 1z-bn's, so leaving it at its shipped default would make the "stock"
    # arm refuse the very pair it exists to re-admit and fail its own control.  See the
    # module docstring for why the third arm already covers the shipped build.
    ag.WAIVER_NEWEST_MUST_BE_STOP = False
    try:
        g = ag.AgTrackGuard(mesh=am.MeshAdapter(pm))
        verdicts, dues = [], []
        seeded = False
        last = None
        for t, kind, d in evs:
            if kind == "report":
                x, y, plane, source, acc = d
                if not seeded:
                    g.on_placement(x, y, plane if plane is not None else 0, t - 1.0)
                    seeded = True
                g.on_report(x, y, plane, ("rep", source, source == "0x0047"), t, accepted=acc)
            elif kind == "click" and seeded:
                g.on_click(d[0], d[1], d[2], t)
            elif kind == "sent" and seeded:
                op, dd, _label = d
                if op == 0x2B:
                    g.on_speed(float(dd[1]), t)
                elif op in (0x29, 0x2A):
                    v = g.pre_emit(dd[1], dd[2], dd[3], dd[4], t)
                    verdicts.append((t, v.code, v.why))
                    g.on_emit(op, dd[1], dd[2], dd[3], dd[4], t)
                elif op == 0x2C:
                    g.on_emit(0x2C, dd[1], dd[2], dd[3], None, t)
            elif kind == "tick" and seeded:
                g.tick(t)
                code, why = g.repin_state(t)
                if (code, why) != last:
                    last = (code, why)
                    if code == ag.REPIN_DUE:
                        # CHRONOLOGICAL: previous report first, newest second, so the
                        # printed pair reads the way the prose and sec.1z-bl do.
                        pair = ("?" if g.prev_is_walkstart is None
                                else ("0x003D" if g.prev_is_walkstart else "0x0047"),
                                "0x003D" if g.last_is_walkstart else "0x0047")
                        age = None if g.client_pos_at is None else t - g.client_pos_at
                        dues.append((t, why, pair, age))
        return verdicts, dues
    finally:
        am.GATE2_SEAM_TOL, ag.WAIVER_WALKSTART_ENDS_STILL, ag.STATIONARY_WAIVER = s_tol, s_cl, s_w
        ag.WAIVER_NEWEST_MUST_BE_STOP = s_ns


def near(t, dues):
    return any(abs(t - d[0]) < MATCH_S for d in dues)




def load(vault, rid, pm, SC):
    """One run's guard feed, or None if it is not map-146 movement we can replay."""
    rp = os.path.join(vault, "captures", "harness", rid, "report.json")
    try:
        rep = json.load(open(rp))
    except Exception:
        return None
    caps = [c.replace("\\", "/") for c in rep.get("captures", []) if "gamesrv" in c.replace("\\", "/")]
    caps = [c for c in caps if os.path.isfile(c)]
    if not caps:
        return None
    try:
        # a run can list two gamesrv captures; take the one that actually carries the
        # movement (leadreplay.py hit this -- the other holds the login and nothing else)
        R, _bad = max((SC.load_rows(c) for c in caps),
                      key=lambda rb: sum(1 for r in rb[0] if r.get("kind") == "position_report"))
    except Exception:
        return None
    evs = guardretro.events(R)
    reports = [(t, d) for t, k, d in evs if k == "report"]
    if not reports or not pm.on_mesh(reports[0][1][0], reports[0][1][1], 1.0):
        return None
    # The capture records the server's own switches.  AGTRACK_GATE2_SEAM decides which
    # gate-2 tolerance THIS capture was recorded under, and so which arm can reproduce it.
    flags = {}
    for r in R:
        if r.get("kind") == "flags" or "flags" in r:
            flags = r.get("flags") or {k: v for k, v in r.items() if k != "kind"}
            break
    return evs, reports, flags


def rewind_estimate(t, reports):
    """How far the body had ALREADY travelled along its current cruise chord when the re-pin
    fired -- the distance a 0x002C to the older report would throw it back.  Estimate: constant
    speed across one chord.  Returns (rewind, chord, dt_after) or (None, None, None)."""
    before = [(rt, d) for rt, d in reports if rt <= t][-1:]
    after = [(rt, d) for rt, d in reports if rt > t][:1]
    if not before or not after:
        return None, None, None
    (tb, b), (ta, n) = before[0], after[0]
    chord = ((n[0] - b[0]) ** 2 + (n[1] - b[1]) ** 2) ** 0.5
    if ta <= tb:
        return None, chord, ta - t
    frac = max(0.0, min(1.0, (t - tb) / (ta - tb)))
    return chord * frac, chord, ta - t


def pct(xs, q):
    return xs[min(len(xs) - 1, int(len(xs) * q))]


def main():
    import agtrack_guard as _ag
    if not hasattr(_ag, "STATIONARY_WAIVER"):
        print("waiverretro.py is RETIRED (MOVECODE-1z-bt): STATIONARY_WAIVER was deleted, so the\n"
              "arms this tool replays no longer exist in agtrack_guard.  Its figures stand in\n"
              "FINDINGS sec.1z-bn.3, 1z-bo.5 and 1z-bs.5; the deleted build IS its former third arm.")
        return 2
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="*")
    ap.add_argument("--all", action="store_true", help="every harness run with a gamesrv capture")
    ap.add_argument("--verbose", action="store_true", help="one line per dropped re-pin")
    a = ap.parse_args()
    from vaultpath import require_dir
    from pathmap import PathingMap
    import agtrack_guard as ag
    import agtrack_mirror as am
    import seamscore as SC
    vault = require_dir()
    pm = PathingMap.load(guardretro.MAP146)
    head_tol = am.GATE2_SEAM_TOL
    gate = ag.REPIN_MAX_REPORT_AGE
    runs = (sorted(os.path.basename(os.path.dirname(p))
                   for p in glob.glob(os.path.join(vault, "captures", "harness", "*", "report.json")))
            if a.all else a.runs)
    if not runs:
        print("no runs given (pass ids or --all)")
        return 1

    n_skip = 0
    eras = {}                      # how many captures replayed at each tolerance
    nowaiver_differs, nowaiver_all, nowaiver_ok = [], 0, 0   # third arm: the waiver deleted
    # per population: runs, real fires, fires predicted by stock / by fix, dues stock / fix
    P = {k: [0, 0, 0, 0, 0, 0] for k in ("ok", "bad", "preguard")}
    dropped, added, kept = [], [], []
    # every real 0x002C fire in the evidence population, by the capture's OWN 'why' and by
    # what the two arms did with it.  This is the table the fix is argued from.
    W = {}      # why -> [control missed, clause removes, clause keeps]
    for rid in runs:
        got = load(vault, rid, pm, SC)
        if got is None:
            n_skip += 1
            continue
        evs, reports, flags = got
        logged = [(t, c, w) for t, k, (c, w) in ((t, k, d) for t, k, d in evs if k == "logged_verdict")]
        fired = [(t, d) for t, k, d in evs if k == "logged_fire"]     # (time, the server's own why)
        real = [t for t, _d in fired]
        # THE ARM IS THE CAPTURE'S OWN, and getting this wrong cost RUN-1zBL its place in the
        # evidence population (MOVECODE-1z-bo's critic).  The first draft replayed EVERY capture
        # at GATE2_SEAM_TOL 0.0 -- pre-1z-bf exact containment -- and computed the shipped-
        # tolerance arm without ever reading it.  A capture recorded WITH the seam tolerance then
        # fails a control that is checking it against a guard it never ran, and the runs it
        # excludes are biased toward sliver geometry, which is exactly where gate2-offmesh lives:
        # the one class this clause claims to leave untouched.  A control aimed at the wrong
        # build is not a weak control, it is a filter.
        tol = head_tol if flags.get("AGTRACK_GATE2_SEAM") else 0.0
        (sv, sdue), (_fv, fdue) = (replay(evs, pm, tol, False), replay(evs, pm, tol, True))
        # THE THIRD ARM (MOVECODE-1z-bo).  sec.1z-bn.5 claims the clause is "strictly narrower
        # than the waiver".  That is true as code and it is a claim about BEHAVIOUR, so measure
        # it: replay with the whole stationary waiver deleted and see whether the shipped clause
        # differs from it anywhere.  If it never does, "narrower" is unwitnessed and the section
        # must say so rather than resting on the source.
        _nv, ndue = replay(evs, pm, tol, True, waiver=False)
        if len(ndue) != len(fdue) or any(abs(a[0] - b[0]) > 1e-9 for a, b in zip(ndue, fdue)):
            nowaiver_differs.append((rid, len(fdue), len(ndue)))
        nowaiver_all += len(ndue)
        eras[bool(flags.get("AGTRACK_GATE2_SEAM"))] = eras.get(bool(flags.get("AGTRACK_GATE2_SEAM")), 0) + 1
        # POPULATION: the verdict control says whether this replay reproduces the past at all
        ok = (len(sv) == len(logged)
              and all(c1 == c2 and w1 == w2 for (_t, c1, w1), (_t2, c2, w2) in zip(sv, logged)))
        key = "preguard" if not logged else ("ok" if ok else "bad")
        row = P[key]
        row[0] += 1
        row[1] += len(real)
        row[2] += sum(1 for t in real if near(t, sdue))
        row[3] += sum(1 for t in real if near(t, fdue))
        row[4] += len(sdue)
        row[5] += len(fdue)
        if key != "ok":
            continue
        nowaiver_ok += len(ndue)
        for t, why in fired:
            w = W.setdefault(why, [0, 0, 0])
            if not near(t, sdue):
                w[0] += 1                       # the control never predicted it
            elif near(t, fdue):
                w[2] += 1                       # the clause keeps it
            else:
                w[1] += 1                       # the clause removes it
        realpairs = [(x,) for x in real]
        for t, why, pair, age in sdue:
            rec = ((rid, why, "%s->%s" % pair, age) + rewind_estimate(t, reports)
                   + (near(t, realpairs),))
            (kept if near(t, fdue) else dropped).append(rec)
        for t, why, pair, age in fdue:
            if not near(t, sdue):
                added.append((rid, why, "%s->%s" % pair, age) + rewind_estimate(t, reports) + (False,))

    print("CORPUS  %d runs replayed on map 146, %d skipped (other map / no capture / unreadable)"
          % (sum(P[k][0] for k in P), n_skip))
    print("  each capture replayed at ITS OWN gate-2 tolerance, from its own AGTRACK_GATE2_SEAM")
    print("  flag: %d with the seam tolerance on, %d without."
          % (eras.get(True, 0), eras.get(False, 0)))
    print("\nPOPULATION -- the verdict control selects it.  Only 'control OK' runs are evidence:")
    print("  a run whose logged verdicts the stock arm cannot reproduce was written by a guard")
    print("  that no longer exists, and its counterfactual is not ours to read.")
    for k, label in (("ok", "control OK"), ("bad", "MISMATCH (older guard)"),
                     ("preguard", "preguard (no verdict rows)")):
        r, rf, ps, pf, ds, fs = P[k]
        print("  %-28s runs %3d   real 0x002C fires %3d, predicted by stock %3d / fix %3d   "
              "(all due-transitions %4d / %4d)" % (label, r, rf, ps, pf, ds, fs))
    r, rf, ps, pf, _ds, _fs = P["ok"]
    print("\nTHE CONTROL, on the evidence population: the stock arm predicts %d of the %d real"
          % (ps, rf))
    print("  0x002C AGTRACK RE-PIN sends within %.1f s.  The fix arm predicts %d." % (MATCH_S, pf))
    if rf:
        print("  -> the clause removes %d of the %d re-pins that REALLY FIRED (%.0f%%)."
              % (ps - pf, rf, 100.0 * (ps - pf) / rf))
    print("\nIS THE CLAUSE NARROWER THAN DELETING THE WAIVER -- IN BEHAVIOUR, NOT IN SOURCE?")
    print("  A third arm replays every capture with STATIONARY_WAIVER off entirely.")
    print("  on the SAME population (control-OK), shipped due-transitions %d | waiver DELETED %d"
          % (P["ok"][5], nowaiver_ok))
    print("  over every replayed run regardless of population:      %d | %d"
          % (sum(P[k][5] for k in P), nowaiver_all))
    if not nowaiver_differs:
        print("  THEY DIFFER IN ZERO RUNS.  On every capture we hold, the shipped clause is")
        print("  OBSERVATIONALLY IDENTICAL to deleting the stationary waiver: every re-pin the")
        print("  clause keeps sits on a FRESH report, where the waiver was never load-bearing.")
        print("  sec.1z-bn.5's \"strictly narrower than the waiver\" is true as CODE and")
        print("  UNWITNESSED as BEHAVIOUR, and no run on this corpus can separate the two.")
        print("  Say that, rather than resting the claim on the source.")
    else:
        print("  they differ in %d run(s) -- the waiver still carries a decision the clause keeps:"
              % len(nowaiver_differs))
        for rid, f, n in nowaiver_differs[:10]:
            print("     %s  shipped %d dues / waiver-deleted %d" % (rid, f, n))

    print("\nEVERY REAL 0x002C FIRE, by the server's OWN reason and what the two arms did:")
    print("  %-16s %8s %8s %8s   %s" % ("why", "missed", "REMOVED", "kept", "control reproduces"))
    for why, (m, rem, k) in sorted(W.items(), key=lambda kv: -(kv[1][1] + kv[1][2])):
        tot = m + rem + k
        print("  %-16s %8d %8d %8d   %d of %d (%.0f%%)"
              % (why, m, rem, k, rem + k, tot, 100.0 * (rem + k) / tot if tot else 0.0))
    print("  the control is strongest in the two classes the clause acts on and weakest in")
    print("  gate1-red, which the clause barely touches -- so the replay's fidelity gap and the")
    print("  fix's effect do not sit in the same place.  Say that out loud rather than quoting")
    print("  the pooled %d-of-%d figure alone." % (ps, rf))

    print("\nRE-PINS THE CLAUSE DROPS (control-OK runs, every due-transition): %d dropped, %d newly"
          % (len(dropped), len(added)))
    print("  raised (a blocked transition can re-raise later); net %d." % (P["ok"][4] - P["ok"][5]))
    for label, pool in (("DROPPED", dropped), ("KEPT", kept)):
        by = {}
        for _r, _w, pair, age, _rw, _c, _dt, _rl in pool:
            stale = age is not None and age > gate
            by[(pair, stale)] = by.get((pair, stale), 0) + 1
        print("  %-7s by report pair and whether the waiver was LOAD-BEARING (report older than"
              " %.3f s):" % (label, gate))
        for (pair, stale), n in sorted(by.items(), key=lambda kv: -kv[1]):
            print("      %-17s %-18s x%d" % (pair, "stale (waiver carried it)" if stale
                                             else "fresh (no waiver)", n))
    bad = {p for _r, _w, p, _a, _rw, _c, _dt, _rl in dropped if p != "0x0047->0x003D"}
    fresh = sum(1 for _r, _w, _p, age, _rw, _c, _dt, _rl in dropped
                if age is not None and age <= gate)
    if bad or fresh:
        print("  !! the clause dropped something it does not name: pairs %s, %d on a fresh report"
              % (sorted(bad), fresh))
    else:
        print("  every dropped re-pin is the {stop -> walk-start} pair the clause names, and every")
        print("  one was stale: the clause removes nothing the waiver was not carrying.")

    rw = sorted(x for _r, _w, _p, _a, x, _c, _dt, _rl in dropped if x is not None)
    if rw:
        over = sum(1 for x in rw if x > 100)
        print("\n  THE REWIND EACH DROPPED RE-PIN WOULD HAVE CAUSED (estimate, constant speed along")
        print("  the client's own cruise chord):")
        print("    n %d   p50 %.0f u   p90 %.0f u   max %.0f u   %d of %d over 100 u"
              % (len(rw), pct(rw, 0.5), pct(rw, 0.9), rw[-1], over, len(rw)))
        print("    sec.1z-bl measured three real rewinds off the agenttap tape at 311-468 u.")
    ages = sorted(x for _r, _w, _p, x, _rw, _c, _dt, _rl in dropped if x is not None)
    if ages:
        print("  report AGE at each dropped re-pin: p50 %.2f s, max %.2f s -- the gate the waiver"
              % (pct(ages, 0.5), ages[-1]))
        print("  waives is %.3f s, so these fired on a report %dx to %dx too old."
              % (gate, int(pct(ages, 0.5) / gate), int(ages[-1] / gate)))
    if added:
        arw = sorted(x for _r, _w, _p, _a, x, _c, _dt, _rl in added if x is not None)
        if arw:
            print("\n  the %d NEWLY RAISED transitions, for honesty: rewind estimate p50 %.0f u, "
                  "max %.0f u" % (len(added), pct(arw, 0.5), arw[-1]))
    if a.verbose:
        print("\n  each dropped re-pin:")
        for rid, why, pair, age, rwd, chord, dt, rl in dropped:
            print("    %s  %-14s %-17s age %s  rewind %s of chord %s%s"
                  % (rid, why, pair, "%5.2f s" % age if age is not None else "  --  ",
                     "%6.0f u" % rwd if rwd is not None else "   --  ",
                     "%6.0f u" % chord if chord is not None else "   --  ",
                     "   [REALLY FIRED]" if rl else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
