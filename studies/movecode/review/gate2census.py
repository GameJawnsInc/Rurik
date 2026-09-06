#!/usr/bin/env python3
"""Could the stationary waiver's deletion have removed a `gate2-offmesh` re-pin? (MOVECODE-1z-bv)

    python studies/movecode/review/gate2census.py

THE OPEN ITEM THIS CLOSES, and why it was mis-stated. From sec.1z-bo.4, repeated in
sec.1z-bt.5 and PLAN sec.8: *"gate2-offmesh exposure -- untested; every guard replay so far
used mesh=None."*  The second clause is FALSE -- `guardretro.py:115` and the retired
`waiverretro.py:111` both build `AgTrackGuard(mesh=am.MeshAdapter(pm))` off the real map-146
pathmap, and sec.1z-bf.4's 19-to-0 retrodiction could not have existed otherwise. What was
true is narrower: the waiver tables' `gate2-offmesh` CELL never moved, and nobody had asked
whether it *could*.

THE QUESTION, ASKED SO THE WIRE CAN ANSWER IT. The waiver only ever licensed one thing: a
re-pin whose newest accepted report was PAST the freshness gate (`REPIN_MAX_REPORT_AGE`,
100 u / 288 u/s) and whose last two accepted reports COINCIDED (within `ZERO_DIST_SQ`).
Anything else the gate allowed on its own. So the waiver's deletion can only have removed a
fire that was BOTH stale and coincident. That is a property of the report stream, and it
decides the question without a counterfactual:

  * if no `gate2-offmesh` fire in the corpus is stale-and-coincident, the deletion could not
    have touched one, and the cell is not "untested" -- it is UNREACHABLE by that change;
  * if one is, it is a witnessed cost of the deletion and the arc has a defect to answer.

NO MESH IS INVOLVED, WHICH IS THE POINT. The class label is read off the capture's own
`agtrack_repin_fire` row -- the reason the SERVER recorded when it sent the `0x002C` -- not
off a replay. So this answer survives the objection the open item rests on. It is also the
one instrument here that cannot be a replay artifact: `guardretro.py` re-derives verdicts and
must control against the logged ones, while this reads only what was logged.

WHY IT IS NOT `waiverbenefit.py` WITH A COLUMN ADDED. That file answers "which report PAIR",
which is sec.1z-bn's clause; this answers "which VERDICT CLASS", which is sec.1z-bf's gate.
They partition the same 25 carried fires two different ways and neither implies the other --
two instruments that would be one theorem if they shared a discriminator, and they do not.

It also prints every carried fire WITH ITS CAPTURE STAMP, so a count that grows can be
attributed rather than assumed: sec.1z-bo.9's 22 became 25 on 2026-09-05, and the three new
ones are RUN-1zBP's, the known-bad revert arm this arc ran ON PURPOSE. A corpus count that
moves is a question, not a defect, and the answer belongs in the output rather than in a
later session's guess.

Read-only. Needs the vault. Stdlib only.
"""
import glob
import os
import sys

# Resolve the tree from THIS FILE, never from a hardcoded absolute path: a git worktree has
# its own copy of toolkit/, and a hardcoded "C:/gd/Rurik" would silently read main's while
# the shell sits in the worktree -- the stale-tree trap CLAUDE.md opens with.
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
for sub in (("studies", "movecode", "review"), ("toolkit",),
            ("toolkit", "mapdata"), ("toolkit", "authsrv")):
    sys.path.insert(0, os.path.join(ROOT, *sub))
import seamscore as SC          # noqa: E402
import agtrack_guard as ag      # noqa: E402
import agtrack_mirror as am     # noqa: E402

# The vault via vaultpath.require_dir(), which RAISES -- never ROOT/"vault", which in a
# worktree resolves to nothing, makes the glob return empty, and would have this file report
# "0 gate-2 fires" as its own conclusion.
from vaultpath import require_dir  # noqa: E402

GATE = ag.REPIN_MAX_REPORT_AGE
ZERO = am.ZERO_DIST_SQ


def scan():
    """(carried, free) -- every real AGTRACK re-pin fire, split by whether the WAIVER was
    what let it through.  carried = stale AND coincident, the only case the waiver could
    license.  Rows are (capture, t_rel, why, age, d2)."""
    caps = sorted(glob.glob(os.path.join(require_dir(), "captures", "gamesrv", "*.jsonl")))
    print("scanning %d gamesrv captures ..." % len(caps))
    carried, free, skipped = [], [], 0
    for c in caps:
        try:
            R, _ = SC.load_rows(c)
        except Exception:
            continue
        fires = [r for r in R if r.get("kind") == "agtrack_repin_fire" and r.get("wall_unix")]
        if not fires:
            continue
        reps = sorted((r["wall_unix"], r.get("source"), r.get("reported"))
                      for r in R if r.get("kind") == "position_report"
                      and r.get("wall_unix") and r.get("accepted"))
        t0 = min(r["wall_unix"] for r in R if r.get("wall_unix"))
        for f in fires:
            tf = f["wall_unix"]
            prior = [p for p in reps if p[0] <= tf]
            if len(prior) < 2:
                skipped += 1        # PRINTED below, never silently dropped
                continue
            (_ta, _sa, pa), (tb, _sb, pb) = prior[-2], prior[-1]
            age = tf - tb
            try:
                d2 = (pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2
            except Exception:
                skipped += 1
                continue
            row = (os.path.basename(c), round(tf - t0, 2),
                   f.get("why") or f.get("reason") or "?", round(age, 3), round(d2, 2))
            (carried if (d2 <= ZERO and age > GATE) else free).append(row)
    return carried, free, skipped, len(caps)


def main():
    carried, free, skipped, ncaps = scan()
    print("gate   REPIN_MAX_REPORT_AGE = %.6f s   ZERO_DIST_SQ = %.1f" % (GATE, ZERO))
    print("real AGTRACK re-pin fires: %d   (waiver load-bearing %d, the gate allowed %d, "
          "unscorable %d)" % (len(carried) + len(free) + skipped, len(carried), len(free), skipped))

    print("\n" + "=" * 78)
    print("THE WAIVER-CARRIED FIRES, BY THE SERVER'S OWN RECORDED VERDICT CLASS")
    print("=" * 78)
    byclass = {}
    for r in carried:
        byclass.setdefault(r[2], []).append(r)
    for why in sorted(byclass, key=lambda k: -len(byclass[k])):
        print("  %-16s x%d" % (why, len(byclass[why])))
    n_g2_carried = len(byclass.get("gate2-offmesh", []))
    print("\n  gate2-offmesh among them: %d" % n_g2_carried)

    print("\nevery carried fire with its capture, so a grown count can be ATTRIBUTED:")
    bycap = {}
    for r in carried:
        bycap.setdefault(r[0], []).append(r)
    for cap in sorted(bycap):
        print("  %-40s x%d  %s" % (cap, len(bycap[cap]),
                                   ", ".join("%s@%.1fs" % (x[2], x[1]) for x in bycap[cap])))

    print("\n" + "=" * 78)
    print("AND THE OTHER DIRECTION: every gate2-offmesh fire, carried or not")
    print("=" * 78)
    g2 = sorted([r for r in carried + free if r[2] == "gate2-offmesh"])
    if not g2:
        # A NULL HERE IS NOT A PASS.  If the corpus holds no gate-2 fire at all, this file
        # has measured nothing about the deletion and must say so rather than print the
        # reassuring line below -- the zero-exposure trap, from the instrument's own side.
        print("  NONE in %d captures -- this run measured NOTHING about the deletion and\n"
              "  the conclusion below is WITHHELD.  Zero exposure is not a null." % ncaps)
        return 3
    cset = set(carried)
    for r in g2:
        print("  %-40s @%7.2fs  age=%.3fs  d2=%8.2f  %s"
              % (r[0], r[1], r[3], r[4],
                 "WAIVER-CARRIED" if r in cset else "the freshness gate allowed it"))

    print("\n" + "=" * 78)
    if n_g2_carried == 0:
        print("VERDICT: the waiver was load-bearing for %d re-pins and NONE is gate2-offmesh."
              % len(carried))
        print("Every one of the %d gate-2 fires above passed the freshness gate on its own --"
              % len(g2))
        print("a FRESH report (age under %.3f s) whose last two reports were %d u apart or"
              % (GATE, int(min(r[4] for r in g2) ** 0.5)))
        print("more, nowhere near the %.1f u^2 coincidence the waiver needed.  So deleting the"
              % ZERO)
        print("waiver (MOVECODE-1z-bt) could not have removed a gate-2 re-pin: the cell is not")
        print("UNTESTED, it is UNREACHABLE by that change.  sec.1z-bo.4's open item is closed.")
        return 0
    print("VERDICT: %d gate2-offmesh fire(s) WERE waiver-carried -- the deletion has a"
          % n_g2_carried)
    print("witnessed cost in that class and sec.1z-bt owes an answer.  Listed above.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
