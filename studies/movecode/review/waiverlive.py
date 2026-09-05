"""Can the stationary waiver EVER be load-bearing on a pair the 1z-bn clause keeps? (PLAN Q15)

sec.1z-bo.9 established the waiver has no WITNESSED benefit: of 82 real re-pin fires, the 22 it
carried are all on {0x0047 -> 0x003D}, the pair the clause refuses, and zero on a kept pair.
That is an empirical null over the routes we have walked, and sec.1z-bo.9 was careful to say so.

THIS ASKS THE STRUCTURAL QUESTION INSTEAD, which is the one that can settle Q15 without a run.
The waiver is load-bearing iff the last two accepted reports COINCIDE (<= ZERO_DIST_SQ) *and*
the newest is STALE (older than REPIN_MAX_REPORT_AGE = 0.347222 s).  So: across every coincident
consecutive report pair in the corpus -- not just the ones a re-pin happened to land on -- what
is the GAP, split by the pair's kind?

  * If coincident {0x003D -> 0x003D} pairs are always FRESH, the waiver can never be
    load-bearing on the pair the clause keeps, and it is STRUCTURALLY dead rather than merely
    unwitnessed.  Q15 answers itself and needs no route.
  * If some are stale, the waiver has a live case the clause preserves, the route that produces
    it is identifiable from the rows below, and Q15 needs that run.

Either answer is useful, which is why it is worth measuring before proposing a run.

CORRECTED MOVECODE-1z-bs: the first version scored "stale" with the pair's OWN gap
(t_b - t_a), which is the gap BEFORE the newer report.  The waiver is load-bearing when the
NEWEST report is stale at the decision instant, so the window in which it can be is
(t_b + gate, the NEXT accepted report), and the gap that decides it is t_next - t_b -- the
trap HANDOFF-WAIVER.md sec.4 lists as (3), inside the instrument that recommended it.  The
counts sec.1z-bq.1 quotes (180 / 175 / 1205) are the proxy's; the corrected ones print
below.  Pairs with no next accepted report are counted separately ("open") rather than
faked from the capture's last row.  No conclusion of the arc moves.

Read-only.  Stdlib only.  Whole corpus.
"""
import glob
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

GATE, ZERO = ag.REPIN_MAX_REPORT_AGE, am.ZERO_DIST_SQ


def pct(xs, q):
    return xs[min(len(xs) - 1, int(len(xs) * q))] if xs else float("nan")


# The vault via vaultpath.require_dir(), which RAISES -- never ROOT/"vault", which in a
# worktree resolves to nothing, makes this glob return empty, and would have this file
# report "0 fires" as a finding.  A fixture that silently resolves to nothing turns every
# assertion behind it into a no-op, and here it would have CONFIRMED its own conclusion.
from vaultpath import require_dir  # noqa: E402
caps = sorted(glob.glob(os.path.join(require_dir(), "captures", "gamesrv", "*.jsonl")))
print("scanning %d gamesrv captures for COINCIDENT consecutive report pairs ...\n" % len(caps))

gaps = {}        # pair -> [gap seconds, the pair's own]
stale_rows = {}  # pair -> [(capture, t_b, gap AFTER the newer report)]
n_pairs = 0
n_open = 0       # coincident pairs that are their file's last accepted pair (no next report)
for c in caps:
    try:
        R, _ = SC.load_rows(c)
    except Exception:
        continue
    reps = [(r["wall_unix"], r.get("source"), r.get("reported"))
            for r in R if r.get("kind") == "position_report"
            and r.get("wall_unix") and r.get("accepted")]
    if len(reps) < 2:
        continue
    for i in range(1, len(reps)):
        (ta, sa, pa), (tb, sb, pb) = reps[i - 1], reps[i]
        if not pa or not pb:
            continue
        d2 = (pb[0] - pa[0]) ** 2 + (pb[1] - pa[1]) ** 2
        if d2 > ZERO:
            continue                      # not a coincident pair: the waiver never applies
        n_pairs += 1
        key = "%s->%s" % (sa or "?", sb or "?")
        gaps.setdefault(key, []).append(tb - ta)
        # "stale" for the waiver's purpose means the NEWEST report has aged past the gate by
        # the time a re-pin acts, so the window is (t_b + gate, the NEXT accepted report) and
        # the gap that decides it is the one AFTER the newer report (1z-bs correction; the
        # first version used the pair's own gap, which is the one before it).
        if i + 1 < len(reps):
            after = reps[i + 1][0] - tb
            if after > GATE:
                stale_rows.setdefault(key, []).append((os.path.basename(c), round(tb, 2), round(after, 3)))
        else:
            n_open += 1                   # the file's last accepted pair: no next report to measure

print("=" * 84)
print("COINCIDENT CONSECUTIVE REPORT PAIRS (within %.1f u^2) -- %d found" % (ZERO, n_pairs))
print("  the waiver applies to ALL of these; it is LOAD-BEARING only on the stale ones")
print("  (gate = %.6f s; STALE = the next accepted report arrives more than the gate after the\n"
      "   newer report -- 1z-bs correction; %d pairs with no next report are not scored)\n"
      % (GATE, n_open))
print("  %-18s %6s   %8s %8s %8s   %s" % ("pair", "n", "p50 gap", "p90 gap", "max gap",
                                          "pairs leaving a STALE window"))
for k in sorted(gaps, key=lambda k: -len(gaps[k])):
    v = sorted(gaps[k])
    st = len(stale_rows.get(k, []))
    refused = (k == "0x0047->0x003D")
    print("  %-18s %6d   %8.3f %8.3f %8.3f   %6d  %s"
          % (k, len(v), pct(v, 0.5), pct(v, 0.9), v[-1], st,
             "<- REFUSED by the clause" if refused else "<- KEPT by the clause"))

print()
print("=" * 84)
kept_stale = sum(len(v) for k, v in stale_rows.items() if k != "0x0047->0x003D")
refused_stale = len(stale_rows.get("0x0047->0x003D", []))
print("  stale coincident pairs on the REFUSED pair : %d" % refused_stale)
print("  stale coincident pairs on a KEPT pair      : %d" % kept_stale)
print()
if kept_stale == 0:
    print("  THE WAIVER IS STRUCTURALLY DEAD ON EVERY PAIR THE CLAUSE KEEPS.")
    print("  Not one coincident {0x003D->...} pair anywhere in the corpus leaves a window in")
    print("  which the report is stale, so `stationary()` returning True can never be the thing")
    print("  that lets a re-pin through except on the pair 1z-bn already refuses.  Q15 does not")
    print("  need a route: the waiver's remaining branch cannot fire, by the client's own")
    print("  reporting cadence rather than by our policy.")
else:
    print("  THE WAIVER'S CONDITION IS LIVE on the kept orderings: %d stale coincident pairs." % kept_stale)
    print("  What sits under them is the question, and waiverclick.py answers it by ORDERING and by")
    print("  the guard's own click state: a pair whose newest report is a STOP is followed by a still")
    print("  body, a pair whose newest is a WALK-START by a walking one in a quarter of its windows, and")
    print("  no kept window has ever met a re-pin want (1z-bs).  Where the condition occurs:")
    for k, v in stale_rows.items():
        if k == "0x0047->0x003D":
            continue
        print("    %s  x%d" % (k, len(v)))
        for name, t, gap in v[:10]:
            print("        %s  t_b=%.2f  window %.3f s" % (name[:38], t, gap))
        if len(v) > 10:
            print("        ... %d more" % (len(v) - 10))
