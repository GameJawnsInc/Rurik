"""NPCTRACK-Q3 -- the hostile's SYNC copy against its DRAWN body, every sample of every tape:
does the drawn body ever path around something the sync copy dead-reckons through?

    python studies/npctrack/review/copysep.py [--tape T --cap C]

Per tape: the separation's p50 / p90 / max over all samples, the same while either copy moves,
and the three widest instants with both positions and both speeds.  Pinned 2026-09-06 (FINDINGS
Q3) over the arc's eight tapes: n = 6,192, p50 1.4 / p90 13.0 / p99 20.2 / max 57.9 u; while
either moves p50 4.9 / p90 13.4.  The widest are the spawn chase's first second (the drawn body
trailing the sync copy 21-37 u -- the AgTrack handoff's lag, ANIMREF-RE 37.2) and the old arm's
transients at a park; nothing on the staircase side or at the wedge tip.  Fixed files: exact pins.
"""
import sys, os, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "toolkit", "clientscan"))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
import npcdrift as N                 # noqa: E402
import w0score as W                  # noqa: E402
import avoidcensus                   # noqa: E402

R4 = ("R4", os.path.join(avoidcensus.V, "research/npctrack/r4-agenttap.jsonl"),
      os.path.join(avoidcensus.V, "captures/gamesrv/authsrv-20260906T151305-c1.jsonl"))


def main(argv):
    runs = avoidcensus.runs_from(argv)
    if runs is avoidcensus.RUNS:
        runs = runs + [R4]
    pooled, moving = [], []
    for name, tape, cap in runs:
        if not (os.path.exists(tape) and os.path.exists(cap)):
            print("%-10s SKIPPED: tape or capture missing" % name)
            continue
        head, rows = W.load(tape)
        s10 = W.series(head, rows, 10)
        crows = W.load_gamesrv(cap)
        t0 = N.cap_t0(crows)
        seps = [(N.dist(s["w0"], s["body"]), s["w"] - t0, s["w0"], s["body"], s["v0"], s["vbody"]) for s in s10]
        ds = [x[0] for x in seps]
        mv = [x[0] for x in seps if x[4] > 5 or x[5] > 5]
        pooled.extend(ds)
        moving.extend(mv)
        top = sorted(seps, reverse=True)[:3]
        print("%-10s n=%4d sync vs drawn: p50 %5.1f p90 %5.1f max %5.1f | either moving n=%3d p50 %5.1f p90 %5.1f | widest: %s" % (
            name, len(ds), statistics.median(ds), avoidcensus.q(ds, 0.9), max(ds), len(mv),
            statistics.median(mv) if mv else float("nan"), avoidcensus.q(mv, 0.9) if mv else float("nan"),
            "; ".join("t=%.1f %.0f u sync (%.0f,%.0f) drawn (%.0f,%.0f) v %.0f/%.0f" % (t, d, w0[0], w0[1], b[0], b[1], v0, vb)
                      for d, t, w0, b, v0, vb in top)))
    if pooled:
        print("POOLED n=%d: p50 %.1f p90 %.1f p99 %.1f max %.1f | either moving n=%d p50 %.1f p90 %.1f" % (
            len(pooled), statistics.median(pooled), avoidcensus.q(pooled, 0.9), avoidcensus.q(pooled, 0.99), max(pooled),
            len(moving), statistics.median(moving), avoidcensus.q(moving, 0.9)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
