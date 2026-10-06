"""H2 (retail), refined: only ATTACK-HOLD episodes -- a hold that was up at one or more own
S4 starts -- and what ends each, with the batch order; the death release timed against the
dead bit, the last own landing and the chain's NEXT DUE START (last own S4 + period); and the
retarget-with-no-swing rows' context.

Period: the own 0x0035 attack-speed period if seen (retail decode carries it as a float in
v[2]), else 1.33 s.  Reported both raw and with 1.33.

PREDICTIONS (stated before running):
  attack episodes end by the next input (M/CLK/K/P/CAN) >= 70 %, death 15-30 %, re-approach
  5-15 %, landing <= 3 %;
  death release - dead bit p50 ~0.4 s, and it sits CLOSER to the chain's next due start
  (|release - due| p50 <= 0.15 s) than to the dead bit + a constant (IQR of the dead-bit lag
  > 0.25 s) -- i.e. the server releases when the chain tries its next swing;
  retarget no-swing released rows: the new target out of reach (a 0x2A or no start follows).

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); `periods()` / `period_at()` are what
`h_retail_death.py` imports (the own 0x0035 attack-speed period per connection).
"""
import collections
import os
import statistics
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h_core as C  # noqa: E402
import h_retail_release as R  # noqa: E402
import retail_conns  # noqa: E402


def periods():
    """{conn name: [(t, period)]} from own 0x0035 (retail decode v = [op, agent, period_bits, mod])."""
    cs = retail_conns.conns()
    out = {}
    for c in cs:
        me = c["me"]
        name = f"{c['cap']} {c['gf'][5:30]}"
        ps = []
        for (t, d, op, v) in c["merged"]:
            if d == "s2c" and op == 0x35 and len(v) > 2 and int(v[1]) == me:
                try:
                    p = struct.unpack("<f", struct.pack("<I", int(v[2]) & 0xFFFFFFFF))[0]
                except Exception:
                    continue
                if 0.5 < p < 4.0:
                    ps.append((t, p))
        out[name] = ps
    return out


def period_at(ps, t):
    p = 1.33
    for (tt, pp) in ps:
        if tt <= t:
            p = pp
    return p


def main():
    P = periods()
    causes = collections.Counter()
    orders = collections.defaultdict(collections.Counter)
    other_ctx = []
    dl = []
    for name, ev in C.retail():
        ps = P.get(name, [])
        state = 0
        ep_starts = 0
        tgt = None
        last_start = None
        last_land = None
        dead_at = {}
        for j, e in enumerate(ev):
            k = e["k"]
            if k == "DEAD":
                dead_at[e["a"]] = (e["t"], j)
            if k == "S4":
                tgt = e["a"]
                last_start = e["t"]
                if state == 1:
                    ep_starts += 1
            if k == "S50":
                tgt = e["a"]
            if k in ("LAND", "L"):
                last_land = e["t"]
            if k == "H":
                if e["a"] == 1:
                    if state == 0:
                        ep_starts = 0
                        # a start in the same batch just before the raise counts
                        for x in reversed(ev[max(0, j - 6):j]):
                            if e["t"] - x["t"] > 0.005:
                                break
                            if x["k"] == "S4":
                                ep_starts += 1
                    state = 1
                    continue
                if state == 1:
                    state = 0
                    if ep_starts == 0:
                        continue
                    tR = e["t"]
                    cause = None
                    for x in reversed(ev[max(0, j - 40):j]):
                        if tR - x["t"] > 0.08:
                            break
                        if x["d"] == "c2s" and x["k"] != "ROT":
                            cause = x["k"]
                            if cause == "P":
                                cause = "P-same" if x["a"] == tgt else "P-retarget"
                            break
                    lo, hi = R.batch(ev, j)
                    tags = [R.TAG[x["k"]](x) for x in ev[lo:hi + 1] if x["k"] in R.TAG]
                    if cause is None:
                        if tgt in dead_at and -1.5 <= dead_at[tgt][0] - tR <= 0.05:
                            cause = "death"
                            per = period_at(ps, tR)
                            due = (last_start + per) if last_start is not None else None
                            dl.append(dict(dead=tR - dead_at[tgt][0],
                                           land=(tR - last_land) if last_land else None,
                                           due=(tR - due) if due else None,
                                           due133=(tR - (last_start + 1.33)) if last_start else None,
                                           per=per, st3=("3:0" in tags)))
                        elif any(x["k"] == "F" for x in ev[j:hi + 1]):
                            cause = "re-approach"
                        elif any(x["k"] in ("LAND", "L") for x in ev[lo:hi + 1]):
                            cause = "landing"
                        elif any(x["k"] in ("E3", "F46") for x in ev[lo:hi + 1]):
                            cause = "cast-end"
                        else:
                            cause = "other"
                            ctx = [(round(x["t"] - tR, 3), x["k"], x["a"]) for x in ev[max(0, j - 12):j + 6]
                                   if abs(x["t"] - tR) <= 0.6]
                            other_ctx.append((name[:34], round(tR, 3), tags, ctx))
                    causes[cause] += 1
                    orders[cause][" ".join(tags)] += 1
    n = sum(causes.values())
    print("ATTACK-HOLD episodes ended:", n, dict(causes.most_common()))
    for c, oc in orders.items():
        print(f"  {c}: {oc.most_common(4)}")
    print()
    print("'other' contexts:")
    for x in other_ctx[:25]:
        print("  ", x)
    print()
    if dl:
        for key in ("dead", "land", "due", "due133"):
            xs = sorted(d[key] for d in dl if d[key] is not None)
            q = lambda f: xs[min(len(xs) - 1, int(f * len(xs)))]
            print(f"death release - {key:7s}: n {len(xs)} p10 {q(0.1):.3f} p25 {q(0.25):.3f} p50 {statistics.median(xs):.3f} "
                  f"p75 {q(0.75):.3f} p90 {q(0.9):.3f}; |x| p50 {statistics.median(abs(v) for v in xs):.3f}")
        print("  periods seen:", collections.Counter(round(d["per"], 3) for d in dl))
        print("  with a [3,0] in the release batch:", sum(d["st3"] for d in dl), "of", len(dl))


if __name__ == "__main__":
    main()
