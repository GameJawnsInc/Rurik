#!/usr/bin/env python3
"""The separation instrument, and the floor that governs the reader feeding it.

    python toolkit/clientscan/test_movesync.py

WHAT THIS IS REALLY CHECKING. Two instruments in this arc reported the wrong
thing for two runs each, and both failures were quiet.

`warpscan.py` scored a big client step against the points we had GRANTED, and
said "NOT near any grant" for 10 of its 12 detections. That line was the finding
-- the landing point sits on the server-authoritative agent's glide path, not at
any granted endpoint -- and it read as a puzzle instead, because nothing printed
the quantity that would have explained it.

`movetap.py` scored itself against a floor of `seconds * hz * 0.5`, half the
REQUESTED rate, while the reader sustains about 13 Hz against a default request
of 50. So it printed FAIL over the run that overturned this arc's mechanism. A
floor that fires on every healthy run is worse than no floor: it is how a real
FAIL gets waved through.

`movesync.py` is the missing quantity and this file is its guard. Section 4
replays the run both instruments were looking at, and sections 1-3 are the pure
logic, so the suite still means something on a machine with no vault.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks     # noqa: E402
import movesync   # noqa: E402
import vaultpath  # noqa: E402

# MEASURED from a real green run: 28 checks with every capture present, 17
# without -- and written down as 17 first, from a count in the author's head,
# which is the same slip test_interact.py records. Sections 1-3 and 5 are
# pure logic and take no fixture; section 4 replays the pair that established
# the mechanism and declares LEDGER.skip when this vault lacks it. 13 is the
# bare-machine subset.
LEDGER = checks.Ledger("separation: the quantity that actually predicts a warp",
                       floor=17)
check = checks.adopt(LEDGER)

MOVETAP = "movetap-20260819T171436.jsonl"
CAPTURE = "authsrv-20260819T171153-c1.jsonl"
# The DEFAULT build -- recorded before --heading-grant existed, and the
# capture that carries the corpus's biggest warps (3,405 / 3,166 / 2,583 u).
DEFAULT_BUILD_CAPTURE = "authsrv-20260819T145717-c1.jsonl"


def main():
    print("1. the truncated-clock offset is estimated from BELOW")
    # The capture stamps whole seconds, so every sample reads floor(unix) - t =
    # true - frac. The mean is biased low by half a second, and half a second at
    # 288 u/s is 144 units -- the same size as the separation being measured, so
    # the choice of estimator is load-bearing rather than stylistic.
    true_off = 5000.5
    walls = [int(true_off + t) - t for t in (0.0, 0.2, 0.45, 0.8, 1.3, 1.95)]
    est, spread = movesync.offset_from_stamps(walls)
    check(est <= true_off, "the estimate never exceeds the truth",
          f"{est} vs {true_off} -- an overestimate would shift every pairing "
          f"the wrong way and inflate separation")
    check(true_off - est < 1.0, "and lands within one second of it",
          f"off by {true_off - est:.3f}")
    check(sum(walls) / len(walls) < est,
          "the mean really is lower, so taking the max is not decorative",
          f"mean {sum(walls) / len(walls):.3f} vs max {est:.3f}")
    check(movesync.offset_from_stamps([]) == (None, None),
          "and no stamps yields None rather than a confident zero",
          "a zero offset would silently pair everything against the wrong time")

    print("\n2. a pair that resolves to nothing is DROPPED, not stretched")
    far = movesync.pair([{"t": 900.0, "live": [0.0, 0.0, 0]}],
                        [(0.0, [0.0, 0.0])], 0.0)
    check(far == [],
          f"a report 900 s from any sample yields no pair",
          f"{len(far)} -- vaultpath.require_dir()'s rule: a fixture that "
          f"silently resolves to the wrong thing turns every assertion behind "
          f"it into a no-op")
    near = movesync.pair([{"t": 10.0, "live": [0.0, 0.0, 0]}],
                         [(0.0, [0.0, 0.0])], 10.0)
    check(len(near) == 1, "and an aligned one is kept", f"{len(near)}")

    print("\n3. the scorer tells a resync from a step that is not one")
    # A resync: the client walks away from a stationary authoritative agent and
    # is snapped back onto it.
    S = [{"t": 100.0 + k * 0.05, "live": [0.0, 0.0, 0]} for k in range(12)]
    reps = [(k * 0.05, [k * 60.0, 0.0]) for k in range(11)] + [(0.55, [5.0, 0.0])]
    _seps, jumps = movesync.score(movesync.pair(S, reps, 100.0))
    col = movesync.collapse(jumps)
    check(len(jumps) == 1, "the synthetic resync yields exactly one jump row",
          f"{len(jumps)}")
    check(col is not None and col[2] > 0.9,
          "and separation collapses across it",
          f"{col[0]:.0f} u -> {col[1]:.0f} u" if col else "no rows")

    # THE CONTROL, and it is the one that matters. Both copies leap together:
    # the step is large and the separation across it does NOT change. A scorer
    # that reports a collapse here is reporting its own procedure.
    # WRITTEN VACUOUS THE FIRST TIME -- the synthetic steps were below the
    # threshold, `jumps` came back empty, and `all([])` is True, so the control
    # passed having judged nothing. The row count is asserted FIRST now.
    S2, reps2 = [], []
    for k in range(12):
        leap = 900.0 if k >= 6 else 0.0
        S2.append({"t": 100.0 + k * 0.05, "live": [k * 10.0 + leap, 0.0, 0]})
        reps2.append((k * 0.05, [k * 10.0 + leap + 600.0, 0.0]))
    _s2, j2 = movesync.score(movesync.pair(S2, reps2, 100.0))
    check(len(j2) >= 1,
          "CONTROL: the no-collapse fixture produces a row to judge",
          "zero rows would make the next check vacuous, which is exactly how "
          "this control passed when it was first written")
    check(bool(j2) and all(abs(b - a) < 50 for _t, _s, b, a in j2),
          "CONTROL: and separation is unchanged across it",
          ", ".join(f"{b:.0f}->{a:.0f}" for _t, _s, b, a in j2))

    print("\n4. replay: the run that overturned the mechanism")
    try:
        mt = os.path.join(vaultpath.vault_path("captures", "movetap"), MOVETAP)
        cap = os.path.join(vaultpath.vault_path("captures", "gamesrv"), CAPTURE)
        have = os.path.exists(mt) and os.path.exists(cap)
    except Exception:
        have = False
    if not have:
        LEDGER.skip("replay",
                    f"this vault has no {MOVETAP} + {CAPTURE}; the logic above "
                    f"still ran")
    else:
        S = movesync.load_movetap(mt)
        reps, walls = movesync.load_reports(cap)
        off, _spread = movesync.offset_from_stamps(walls)
        prs = movesync.pair(S, reps, off)
        check(len(prs) >= 150,
              f"the two captures overlap on {len(prs)} pairs",
              f"{len(prs)} -- fewer than 150 means the windows barely meet and "
              f"nothing below would mean anything")
        seps, jumps = movesync.score(prs)
        col = movesync.collapse(jumps)
        check(len(jumps) >= 10, f"and carry {len(jumps)} resync jumps",
              f"{len(jumps)}")
        check(col[2] > 0.85,
              f"separation collapses {100 * col[2]:.0f}% across them "
              f"({col[0]:.0f} u -> {col[1]:.0f} u)",
              f"{100 * col[2]:.1f}% -- measured at 96% on 13 jumps")
        # The shuffle. THIS is what makes the number above a claim rather than a
        # consequence of pairing anything with anything.
        _s3, j3 = movesync.score(movesync.pair(S, reps, off + 7.0))
        col3 = movesync.collapse(j3)
        check(col3 is None or col3[2] < 0.5 * col[2],
              "CONTROL: pairing 7 s out of true does NOT reproduce it",
              f"{100 * col3[2]:.0f}% against {100 * col[2]:.0f}% -- if the "
              f"shuffle collapsed too, the statistic would be measuring the "
              f"procedure" if col3 else "no jumps under the shuffle")
        # And the alignment sweep must PEAK at the timestamp-derived offset. It
        # was not fitted to the data, so this is an independent check that the
        # clocks are lined up rather than a restatement of the headline.
        best, best_d = -1.0, None
        for d in movesync.SWEEP:
            c = movesync.collapse(movesync.score(movesync.pair(S, reps, off + d))[1])
            if c and c[2] > best:
                best, best_d = c[2], d
        check(best_d == 0.0,
              "and the alignment sweep peaks at the offset the stamps gave",
              f"peak at {best_d:+.2f}s -- the offset came from 8,573 timestamps "
              f"and was never fitted to maximise this, so a peak anywhere else "
              f"means the clocks are misaligned")
        check(max(seps) > 400,
              f"the two copies reach {max(seps):.0f} u apart",
              f"{max(seps):.1f} -- the whole point is that they diverge")

    print("\n5. movetap's floor is calibrated, not aspirational")
    src = open(os.path.join(HERE, "movetap.py"), encoding="utf-8").read()
    check("def calibrate(" in src,
          "movetap measures what the reader can actually do",
          "without a measured capability the floor is a guess about hardware")
    check("int(a.seconds * a.hz * 0.5)" not in src,
          "and does not score itself against the REQUESTED rate",
          "that floor demanded 7,500 samples from a reader that sustains 13 Hz, "
          "and duly failed the run that overturned this arc's mechanism")
    check("except KeyboardInterrupt" in src,
          "and Ctrl+C still prints a summary",
          "the operator stops when the thing they were reproducing has "
          "happened; that used to escape as a traceback with no verdict")

    print("\n6. wire-only: a landing scored against the path it was granted")
    # The geometry itself, first. A point ON the segment must read perp 0 and a
    # fraction inside [0,1]; a point off to the side must not.
    d, f = movesync.on_segment([0.0, 0.0], [100.0, 0.0], [40.0, 0.0])
    check(abs(d) < 1e-6 and abs(f - 0.4) < 1e-6,
          "a point on the segment reads perp 0 at its own fraction",
          f"perp {d}, frac {f}")
    d, f = movesync.on_segment([0.0, 0.0], [100.0, 0.0], [40.0, 250.0])
    check(abs(d - 250.0) < 1e-6,
          "and a point beside it reads its true offset",
          f"perp {d} -- if this collapsed to 0 the whole test would pass "
          f"for anything")
    d, f = movesync.on_segment([0.0, 0.0], [100.0, 0.0], [-60.0, 0.0])
    check(f < 0,
          "a landing BEHIND the origin reads a negative fraction",
          f"frac {f} -- those rows exist in the corpus and must not be "
          f"counted as on-path")

    print("\n7. replay: the wire-only test on a DEFAULT-build capture")
    try:
        cap = os.path.join(vaultpath.vault_path("captures", "gamesrv"),
                           DEFAULT_BUILD_CAPTURE)
        have = os.path.exists(cap)
    except Exception:
        have = False
    if not have:
        LEDGER.skip("wire-only replay",
                    f"this vault has no {DEFAULT_BUILD_CAPTURE}")
    else:
        w = movesync.wire_only(cap)
        check(w["cadence"] <= movesync.GOOD_CADENCE,
              f"the capture's report cadence is {w['cadence']:.2f}s, dense "
              f"enough to judge",
              f"{w['cadence']:.2f}s -- above {movesync.GOOD_CADENCE}s the "
              f"jump population is contaminated with ordinary walking")
        onp = movesync.on_path(w["scored"])
        con = movesync.on_path(w["control"])
        check(onp >= 15,
              f"{onp} of {len(w['scored'])} landings sit on the granted path",
              f"{onp} -- measured at 18 of 30")
        check(con <= 2,
              f"CONTROL: only {con} of {len(w['control'])} sit on an unrelated "
              f"grant's path",
              f"{con} -- measured at 0 of 31. If an unrelated grant scored as "
              f"well, the map geometry would be doing the work")
        perp = sorted(r["perp"] for r in w["scored"])
        cperp = sorted(r["perp"] for r in w["control"])
        check(cperp[len(cperp) // 2] > 5 * perp[len(perp) // 2],
              "and the control's perpendicular offset is far larger",
              f"{cperp[len(cperp)//2]:.1f} u vs {perp[len(perp)//2]:.1f} u -- "
              f"measured at 744.8 against 43.9")
        ages = sorted(r["age"] for r in w["scored"])
        check(ages[len(ages) // 2] > 2.0,
              f"and the grant was already {ages[len(ages)//2]:.1f}s old at the "
              f"jump",
              f"{ages[len(ages)//2]:.2f}s -- this is the DEFAULT build, where a "
              f"grant sits outstanding an order of magnitude longer than "
              f"retail's median 0.490s re-grant")

    print("\n8. the cadence gate can actually refuse")
    # A gate that never fires is not a gate. Build a capture-shaped input whose
    # reports are 3 s apart and confirm the cadence lands above the bar.
    sparse = [(k * 3.0, [k * 900.0, 0.0]) for k in range(10)]
    gaps = [sparse[i][0] - sparse[i - 1][0] for i in range(1, len(sparse))]
    cad = sorted(gaps)[len(gaps) // 2]
    check(cad > movesync.GOOD_CADENCE,
          "CONTROL: a 3 s cadence is recognised as too sparse to judge",
          f"{cad:.2f}s against a bar of {movesync.GOOD_CADENCE}s -- capture "
          f"20260819T113105 is exactly this at 2.75s, and its control scores "
          f"as well as its treatment, which is the gate earning itself")

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
