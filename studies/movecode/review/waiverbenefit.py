"""Every re-pin the STATIONARY WAIVER actually enabled, split by report pair (sec.1z-bo.8 item 1).

"Retract" is not a capture row -- sec.1z-bo's critic found zero rows matching it in any of
1,309 captures, and my first attempt at this scored that null as if it were a measurement.
A retract IS a re-pin fire that the waiver let through: the 0x002C clears the arrival tick so
the arrival never matures, and the ones sec.1z-ai/sec.1z-aj counted are the ones that landed on
a body at 0.0 u harm.

So the measurable form of the question is: across the whole corpus, of the re-pins that REALLY
FIRED and that the waiver was LOAD-BEARING for (last two accepted reports coincident within
ZERO_DIST_SQ, and the newest one older than REPIN_MAX_REPORT_AGE, so the unwaived gate would
have refused), how many sit on the pair sec.1z-bn's clause refuses and how many on a pair it
keeps?  A fire on a KEPT pair is a witnessed benefit the clause preserves.  If there are none,
the waiver has no measured benefit anywhere.

Read-only.  Stdlib only.
"""
import glob
import json
import os
import sys

# Resolve the tree from THIS FILE, never from a hardcoded absolute path: a git worktree
# has its own copy of toolkit/, and a hardcoded "C:/gd/Rurik" would silently read main's
# while the shell sits in the worktree -- the stale-tree trap CLAUDE.md opens with.
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
for sub in (("studies", "movecode", "review"), ("toolkit",),
            ("toolkit", "mapdata"), ("toolkit", "authsrv")):
    sys.path.insert(0, os.path.join(ROOT, *sub))
import seamscore as SC          # noqa: E402
import agtrack_guard as ag      # noqa: E402
import agtrack_mirror as am     # noqa: E402

GATE = ag.REPIN_MAX_REPORT_AGE
ZERO = am.ZERO_DIST_SQ

# The vault via vaultpath.require_dir(), which RAISES -- never ROOT/"vault", which in a
# worktree resolves to nothing, makes this glob return empty, and would have this file
# report "0 fires" as a finding.  A fixture that silently resolves to nothing turns every
# assertion behind it into a no-op, and here it would have CONFIRMED its own conclusion.
from vaultpath import require_dir  # noqa: E402
caps = sorted(glob.glob(os.path.join(require_dir(), "captures", "gamesrv", "*.jsonl")))
print("scanning %d gamesrv captures for real 0x002C AGTRACK re-pin fires ..." % len(caps))

total_fires = 0
buckets = {}          # (pair, waiver_load_bearing) -> [rows]
for c in caps:
    try:
        R, _ = SC.load_rows(c)
    except Exception:
        continue
    fires = [r for r in R if r.get("kind") == "agtrack_repin_fire" and r.get("wall_unix")]
    if not fires:
        continue
    reps = [(r["wall_unix"], r.get("source"), r.get("reported"))
            for r in R if r.get("kind") == "position_report"
            and r.get("wall_unix") and r.get("accepted")]
    t0 = min(r["wall_unix"] for r in R if r.get("wall_unix"))
    for f in fires:
        total_fires += 1
        t = f["wall_unix"]
        prior = [x for x in reps if x[0] <= t][-2:]
        if len(prior) < 2:
            key = ("<2 reports", False)
            buckets.setdefault(key, []).append((os.path.basename(c), round(t - t0, 2),
                                                f.get("why"), None, None))
            continue
        (ta, sa, pa), (tb, sb, pb) = prior
        d2 = (pb[0] - pa[0]) ** 2 + (pb[1] - pa[1]) ** 2
        age = t - tb
        # the waiver was LOAD-BEARING iff it was the thing that let this fire through:
        # the pair coincided (so stationary() said True) AND the report was too old for
        # the unwaived gate, which would otherwise have refused it.
        carried = (d2 <= ZERO) and (age > GATE)
        key = ("%s->%s" % (sa or "?", sb or "?"), carried)
        buckets.setdefault(key, []).append((os.path.basename(c), round(t - t0, 2),
                                            f.get("why"), round(d2, 3), round(age, 3)))

print("real re-pin fires in the corpus: %d\n" % total_fires)
print("=" * 82)
print("SPLIT BY REPORT PAIR, AND BY WHETHER THE WAIVER WAS WHAT LET THE FIRE THROUGH")
print("  (load-bearing = the pair coincided within %.1f u^2 AND the report was older than" % ZERO)
print("   the %.6f s gate, so without the waiver the unwaived gate would have refused it)" % GATE)
print()
carried_refused, carried_kept = 0, 0
for (pair, carried), v in sorted(buckets.items(), key=lambda kv: (-len(kv[1]), kv[0][0])):
    refused = (pair == "0x0047->0x003D")
    tag = ("WAIVER CARRIED IT" if carried else "waiver not load-bearing")
    print("  %-18s %-24s x%d   %s" % (pair, tag, len(v),
          "<- the pair 1z-bn REFUSES" if (carried and refused) else
          ("<- A BENEFIT THE CLAUSE KEEPS" if carried else "")))
    if carried:
        if refused:
            carried_refused += len(v)
        else:
            carried_kept += len(v)
        for name, dt, why, d2, age in v[:8]:
            print("        %s +%.2fs  %-14s d2=%s age=%ss" % (name[:32], dt, why, d2, age))
        if len(v) > 8:
            print("        ... %d more" % (len(v) - 8))

print()
print("=" * 82)
print("  re-pins the waiver CARRIED, on the pair the clause REFUSES : %d" % carried_refused)
print("  re-pins the waiver CARRIED, on a pair the clause KEEPS     : %d" % carried_kept)
if carried_refused and not carried_kept:
    print()
    print("  EVERY re-pin the stationary waiver has ever carried, across the whole corpus, sits")
    print("  on the pair sec.1z-bn refuses.  The waiver has NO measured benefit anywhere, and")
    print("  the question for the owner is whether STATIONARY_WAIVER should exist at all --")
    print("  which is the same answer waiverretro's third arm gives from the other direction.")
elif carried_kept:
    print()
    print("  The waiver retains %d witnessed benefit(s) on a pair the clause keeps, so the")
    print("  clause is doing real narrowing and the waiver should stay." % carried_kept)
else:
    print()
    print("  The waiver has never been load-bearing on ANY real fire in the corpus.  That is a")
    print("  stronger statement than the one above and needs the same caution: check that fires")
    print("  of this shape are present at all before reading it as a measurement.")
