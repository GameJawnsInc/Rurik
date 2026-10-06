"""H2 (retail): what ends retail's hold, by class, and the ORDER inside the release's batch.

For every own [8, me, 0] that ends a hold (state 1 -> 0) on every cached live connection
with an observer:
  cause = the last c2s input within 80 ms before it (M moving 0x3D, M0, STOP 0x47, CLK 0x3E,
          P-same / P-retarget 0x26, K skill press, CAN 0x28, INT 0x39), else server-side:
          death (the chain target's dead bit in [-1.5, +0.05] s), re-approach (an own 0x2A
          within 5 ms after), own-death/rise, landing (an own LAND / launch in its batch),
          cast-end (an own E3 / [46] in its batch), other.
  order = the s2c rows of its batch (contiguous, within 5 ms) as a short string.
Then, the discriminating questions:
  (a) does a 0x47 (key-up STOP) release a hold?  ours never does (the 0x0047 arm has no
      action_hold);
  (b) does an interact 0x39 release it (ours: _order_walk sends its 0x2A with no release)?
  (c) the target-death lag: from the dead bit, and from the last own LAND; is the killing
      blow our own landing (LAND in the dead bit's batch)?
  (d) a retarget 0x26 while held: by swing-in-flight; is the release the re-approach's?

PREDICTIONS (stated before running):
  movement releases (M) are release-first ahead of [3] and ahead of the 0x29 lead >= 95 %;
  (a) a 0x47 while held releases <= 10 % (the stop is not an input that ends an action);
  (b) n small (<= 5), released when a 0x2A walk goes out;
  (c) lag from the dead bit p50 0.35-0.50 s, and the dead bit shares a batch with an own LAND
      on >= 70 % (our swing killed it), so lag from the landing ~ the same;
  (d) retarget with no swing in flight: the released ones are exactly those followed by an
      0x2A (re-approach) to the new target, >= 80 %.

Ported 2026-10-06 from the 1z-ds batch scratchpad (DEATHWALK-D0); `batch()` and `TAG` are what `h_retail_death.py`
imports. Its own main() is the H2 retail census (FINDINGS 1z-ds.31's "what ends retail's hold" table, 347 episodes).
"""
import collections
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import h_core as C  # noqa: E402

TAG = {"H": lambda e: f"8:{e['a']}", "ST3": lambda e: f"3:{e['a']}", "LEAD": lambda e: "29",
       "F": lambda e: "2A", "HALT": lambda e: "28", "PIN": lambda e: "2C", "S4": lambda e: "4",
       "S50": lambda e: "50", "S60": lambda e: "60", "LAND": lambda e: "1", "L": lambda e: "A4",
       "F46": lambda e: "46", "F49": lambda e: "49", "F59": lambda e: "59", "E3": lambda e: "E3",
       "DEAD": lambda e: "DEAD"}


def batch(ev, j):
    """The contiguous s2c rows around j within 5 ms."""
    t = ev[j]["t"]
    lo = j
    while lo - 1 >= 0 and ev[lo - 1]["d"] == "s2c" and t - ev[lo - 1]["t"] <= 0.005:
        lo -= 1
    hi = j
    while hi + 1 < len(ev) and ev[hi + 1]["d"] == "s2c" and ev[hi + 1]["t"] - t <= 0.005:
        hi += 1
    return lo, hi


def main():
    causes = collections.Counter()
    orders = collections.defaultdict(collections.Counter)
    death_lag, death_land_lag, death_ours = [], [], collections.Counter()
    stop_tab = collections.Counter()
    int_tab = collections.Counter()
    rt = collections.Counter()
    rt_ex = collections.defaultdict(list)
    nconn = 0
    for name, ev in C.retail():
        nconn += 1
        state = 0
        tgt = None
        last_start = None
        landed = True
        last_land_t = None
        dead_at = {}
        for j, e in enumerate(ev):
            k = e["k"]
            if k == "DEAD":
                dead_at[e["a"]] = (e["t"], j)
            if k in ("S4", "S50"):
                tgt = e["a"]
                last_start = e["t"]
                landed = False
            if k in ("LAND", "L"):
                landed = True
                last_land_t = e["t"]
            # (a) a 0x47 while held
            if k == "STOP" and state == 1:
                rel = False
                for x in ev[j + 1:]:
                    if x["t"] - e["t"] > 0.08 or x["d"] == "c2s":
                        break
                    if x["k"] == "H" and x["a"] == 0:
                        rel = True
                stop_tab["n"] += 1
                stop_tab["released"] += rel
            if k == "INT" and state == 1:
                rel = f2a = False
                for x in ev[j + 1:]:
                    if x["t"] - e["t"] > 0.15 or x["d"] == "c2s":
                        break
                    if x["k"] == "H" and x["a"] == 0:
                        rel = True
                    if x["k"] == "F":
                        f2a = True
                int_tab[("released" if rel else "kept", "2A" if f2a else "no-2A")] += 1
            if k == "P" and state == 1:
                same = e["a"] == tgt
                inflight = last_start is not None and e["t"] - last_start < 1.0 and not landed
                rel = f2a = start = st3 = False
                for x in ev[j + 1:]:
                    if x["t"] - e["t"] > 0.15 or x["d"] == "c2s":
                        break
                    if x["k"] == "H" and x["a"] == 0:
                        rel = True
                    if x["k"] == "F":
                        f2a = True
                    if x["k"] in ("S4", "S50"):
                        start = True
                    if x["k"] == "ST3":
                        st3 = True
                key = ("same" if same else "retarget", "in-flight" if inflight else "no-swing",
                       "released" if rel else "kept", "2A" if f2a else ("start" if start else "-"))
                rt[key] += 1
                if len(rt_ex[key]) < 4:
                    rt_ex[key].append((name[:30], round(e["t"], 3)))
            if k != "H":
                continue
            if e["a"] == 1:
                state = 1
                continue
            if state != 1:
                continue
            state = 0
            tR = e["t"]
            # cause
            cause = None
            for x in reversed(ev[max(0, j - 40):j]):
                if tR - x["t"] > 0.08:
                    break
                if x["d"] == "c2s" and x["k"] not in ("ROT",):
                    cause = x["k"]
                    if cause == "P":
                        cause = "P-same" if x["a"] == tgt else "P-retarget"
                    break
            lo, hi = batch(ev, j)
            tags = [TAG[x["k"]](x) for x in ev[lo:hi + 1] if x["k"] in TAG]
            if cause is None:
                if tgt in dead_at and -1.5 <= dead_at[tgt][0] - tR <= 0.05:
                    cause = "death"
                    dt, dj = dead_at[tgt]
                    death_lag.append(tR - dt)
                    dlo, dhi = batch(ev, dj)
                    ours = any(x["k"] == "LAND" for x in ev[dlo:dhi + 1])
                    death_ours["killing blow is our LAND" if ours else "not ours"] += 1
                    if last_land_t is not None:
                        death_land_lag.append(tR - last_land_t)
                elif any(x["k"] == "F" for x in ev[j:hi + 1]):
                    cause = "re-approach"
                elif any(x["k"] in ("LAND", "L") for x in ev[lo:hi + 1]):
                    cause = "landing"
                elif any(x["k"] in ("E3", "F46") for x in ev[lo:hi + 1]):
                    cause = "cast-end"
                else:
                    cause = "other"
            causes[cause] += 1
            orders[cause][" ".join(tags)] += 1
    print("connections", nconn)
    print("RELEASE CAUSES (retail):", dict(causes.most_common()))
    for c, oc in orders.items():
        print(f"  {c}: top batch shapes", oc.most_common(5))
    # release-first checks
    print()
    for c in ("M", "CLK", "P-retarget", "K", "CAN", "STOP", "re-approach", "death"):
        oc = orders.get(c, {})
        n = sum(oc.values())
        rf3 = sum(v for s, v in oc.items() if "3:0" in s and s.split().index("8:0") < s.split().index("3:0"))
        with3 = sum(v for s, v in oc.items() if "3:0" in s)
        rflead = sum(v for s, v in oc.items() if "29" in s and s.split().index("8:0") < s.split().index("29"))
        withlead = sum(v for s, v in oc.items() if "29" in s)
        rf2a = sum(v for s, v in oc.items() if "2A" in s and s.split().index("8:0") < s.split().index("2A"))
        with2a = sum(v for s, v in oc.items() if "2A" in s)
        print(f"  {c:12s} n {n:4d}: release before [3] {rf3}/{with3}; before 0x29 {rflead}/{withlead}; "
              f"before 0x2A {rf2a}/{with2a}")
    print()
    print("(a) 0x47 while held:", dict(stop_tab))
    print("(b) 0x39 while held:", dict(int_tab))
    if death_lag:
        d = sorted(death_lag)
        print("(c) death release lag from the dead bit: n %d p10 %.3f p50 %.3f p90 %.3f min %.3f max %.3f" % (
            len(d), d[len(d) // 10], statistics.median(d), d[(9 * len(d)) // 10], d[0], d[-1]))
        dl = sorted(death_land_lag)
        print("    from the last own LAND: n %d p50 %.3f p10 %.3f p90 %.3f" % (
            len(dl), statistics.median(dl), dl[len(dl) // 10], dl[(9 * len(dl)) // 10]))
        print("   ", dict(death_ours))
    print("(d) presses while held:")
    for key in sorted(rt):
        print("   ", key, rt[key], rt_ex[key][:3])


if __name__ == "__main__":
    main()
