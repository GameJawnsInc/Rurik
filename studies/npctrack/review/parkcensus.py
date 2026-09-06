"""NPCTRACK-F15 -- where the CLIENT parks the hostile's sync copy relative to the player's
world-0 copy.  The disc stop is the agent-avoidance pass's target-agent exit (0x0060181C, F14),
run at the world-0 tick; the server's Q1 model parks exactly ON the 80 u disc, solved on the
leg's line.  So the client's park should sit INSIDE the disc by whatever the copy walked
between contact and its next tick, and never outside it.

Census over the arc's seven tapes: every stop of agent 10's sync copy (walking -> velocity zero
with both target blocks invalid), classed as OURS (a 0x0028 to agent 10 within +-150 ms in the
capture), an ARRIVAL (the copy sits on its previous target: the tick's 0x00600333), or a DISC
PARK (stopped short of the target), and for the disc parks the distance to the player's world-0
live position at that sample.  `-v` lists them.

    python studies/npctrack/review/parkcensus.py [-v] [--tape T --cap C]

Pinned 2026-09-06 (FINDINGS F15): 103 disc parks; at a STANDING player (n = 37) d p10 63.8 /
p50 71.1 / p90 79.6, min 61.8, 36 of 37 inside (one at 84.9) -- the park lands 0-18 u inside the
disc, mean 8.4 u, which is Q1's residual at the halts; at a MOVING player (n = 66) p50 84.2 by the sample's
lag behind the park.  The tapes are fixed files: exact pins.
"""
import sys, os, math, bisect, statistics, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "toolkit", "clientscan"))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
import npcdrift as N                 # noqa: E402
import w0score as W                  # noqa: E402
import avoidcensus                   # noqa: E402

R = 80.0
HALT_RE = re.compile(r"agent (\d+) halts at")


def stops(rows, head, t0, halts):
    prev = None
    out = []
    for s in rows:
        a = (s.get("agents") or {})
        h, p = a.get("10"), a.get("1")
        if not h or not p or not h.get("sync") or not p.get("sync") or "x" not in h["sync"] or "x" not in p["sync"]:
            continue
        hs, ps = h["sync"], p["sync"]
        c0 = s.get("clock0")
        tt = head["t0"] + s["t"] - t0
        walking = math.isfinite(hs.get("tx", float("inf"))) and (hs.get("vx", 0) or hs.get("vy", 0))
        parked = (not math.isfinite(hs.get("tx", float("inf")))) and hs.get("vx", 0) == 0 and hs.get("vy", 0) == 0
        if prev is not None and prev[0] and parked:
            i = bisect.bisect_left(halts, tt - 0.15)
            ours = i < len(halts) and halts[i] <= tt + 0.15
            hp = (hs["x"], hs["y"])
            pp = W.live(ps, c0)
            pv = math.hypot(ps.get("vx", 0), ps.get("vy", 0)) if math.isfinite(ps.get("tx", float("inf"))) else 0.0
            d = math.hypot(hp[0] - pp[0], hp[1] - pp[1])
            short = math.hypot(hp[0] - prev[1][0], hp[1] - prev[1][1])
            kind = "ours" if ours else ("arrival" if short <= 2.0 else "disc")
            out.append(dict(t=tt, d=d, kind=kind, player_v=pv, short=short))
        prev = (walking, (hs.get("tx", 0.0), hs.get("ty", 0.0)))
    return out


def main(argv):
    verbose = "-v" in argv
    pooled, stand, move = [], [], []
    for name, tape, cap in avoidcensus.runs_from(argv):
        if not (os.path.exists(tape) and os.path.exists(cap)):
            print("%-10s SKIPPED: tape or capture missing" % name)
            continue
        head, rows = W.load(tape)
        crows = W.load_gamesrv(cap)
        t0 = N.cap_t0(crows)
        halts = sorted(r["t"] for r in crows if r.get("kind") == "sent" and r.get("opcode") == 0x28
                       and HALT_RE.search(r.get("label") or "")
                       and int(HALT_RE.search(r["label"]).group(1)) == 10)
        st = stops(rows, head, t0, halts)
        disc = [x for x in st if x["kind"] == "disc"]
        ds = [x["d"] for x in disc]
        sd = [x["d"] for x in disc if x["player_v"] < 5]
        md = [x["d"] for x in disc if x["player_v"] >= 5]
        print("%-10s stops %2d (ours %2d, arrivals %2d) | DISC parks %2d: d to world-0 p10 %5.1f p50 %5.1f p90 %5.1f max %5.1f | standing n=%2d p50 %5.1f min %5.1f | moving n=%2d p50 %5.1f min %5.1f" % (
            name, len(st), sum(1 for x in st if x["kind"] == "ours"), sum(1 for x in st if x["kind"] == "arrival"), len(ds),
            avoidcensus.q(ds, 0.1), statistics.median(ds) if ds else float("nan"), avoidcensus.q(ds, 0.9), max(ds) if ds else float("nan"),
            len(sd), statistics.median(sd) if sd else float("nan"), min(sd) if sd else float("nan"),
            len(md), statistics.median(md) if md else float("nan"), min(md) if md else float("nan")))
        if verbose:
            for x in disc:
                print("    t=%7.3f d=%5.1f short-of-target %6.1f player v=%4.0f" % (x["t"], x["d"], x["short"], x["player_v"]))
        pooled.extend(ds); stand.extend(sd); move.extend(md)
    print("POOLED disc parks n=%d: d p10 %.1f p50 %.1f p90 %.1f max %.1f" % (
        len(pooled), avoidcensus.q(pooled, 0.1), statistics.median(pooled), avoidcensus.q(pooled, 0.9), max(pooled)))
    if stand:
        h = collections.Counter(int((R - d) // 5) * 5 for d in stand)
        print("  STANDING player n=%d: d p10 %.1f p50 %.1f p90 %.1f min %.1f max %.1f | inside the disc by (80 - d): mean %.1f u, histogram in 5 u bins: %s" % (
            len(stand), avoidcensus.q(stand, 0.1), statistics.median(stand), avoidcensus.q(stand, 0.9), min(stand), max(stand),
            statistics.mean(R - d for d in stand), " ".join("[%d,%d):%d" % (k, k + 5, h[k]) for k in sorted(h))))
    if move:
        print("  MOVING player   n=%d: d p10 %.1f p50 %.1f p90 %.1f min %.1f max %.1f (the sample lags the park; the player walked on)" % (
            len(move), avoidcensus.q(move, 0.1), statistics.median(move), avoidcensus.q(move, 0.9), min(move), max(move)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
