#!/usr/bin/env python3
"""SEPARATION: how far the client's own position is from the agent we drive.

    python toolkit/clientscan/movesync.py                 # newest overlapping pair
    python toolkit/clientscan/movesync.py --movetap X --capture Y
    python toolkit/clientscan/movesync.py --selftest      # no captures needed

WHY THIS EXISTS, and it is a correction rather than a new idea. Until
2026-08-19 every instrument in this arc scored the WRONG QUANTITY. `warpscan.py`
asks whether a big client step landed near a point we granted, and answered
"NOT near any grant" for 10 of its 12 detections -- which read as a puzzle for
two runs and was in fact the finding, sitting in the output unread.

Run 20260819T171436 watched both sides at once for the first time. `movetap`
reads the SYNC array (`[AGBASE+0xE8]`) -- the server-authoritative agent, the one
our 0x0029 grants steer. The client REPORTS from the copy it predicts and
renders. Those are different objects, and over 182 matched pairs they sat p50
125.9 u apart and reached 673.7 u. Every client step over 300 u collapsed that
gap: 13 of 13, mean 395.1 u -> 119.7 u, and the biggest jump closed the biggest
gap. **The warp is the client snapping its predicted copy onto the authoritative
one.** The landing point is on the authoritative glide path, which is exactly why
scoring it against granted points found nothing.

So the quantity that predicts a warp is SEPARATION, and nothing printed it. This
does.

THE QUESTION: does separation grow while the two copies disagree, and collapse
when the client jumps? THE PREDICTION, stated before the run rather than after:
if the resync model is right, separation immediately BEFORE a large client step
is large, immediately AFTER it is small, and the step size tracks the gap closed.
REFUTED IF: separation is the same either side of a jump (then the jump is
something else), or if the same collapse appears under the shuffled control
below (then it is an artifact of pairing, not a fact about the client).

THE CONTROL, and this file will not report a collapse without it. Pair each
report against a movetap sample chosen from the WRONG time and the collapse must
vanish. A statistic that survives its own shuffle is measuring the procedure.

CLOCK ALIGNMENT IS THE WEAK POINT AND IS TREATED AS ONE. The capture's `wall`
stamps are whole seconds, so a naive offset is worth +/-0.5 s, and at 288 u/s
half a second is 144 units -- the same order as the separation being measured. Two
things are done about it. The offset is estimated as max(timegm(wall) - t) over
every stamped record, which converges on the true offset from below because
truncation only ever loses fraction. And the headline is then re-scored across a
+/-1.0 s sweep: a collapse that only exists at one offset is an alignment
artifact and is reported as such.

READ ONLY. Opens vault captures and writes nothing.
"""
import argparse
import calendar
import glob
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import vaultpath  # noqa: E402

# A client step this big is the event we are scoring. Set from the run that
# established the mechanism: its resync jumps were 339.7 u to 757.5 u, and its
# ordinary walking steps were 20-40 u per report. 300 sits in the empty band
# between the two populations rather than inside either.
JUMP_UNITS = 300.0
# How far a report may be from its nearest sample before the pair is dropped.
# The reader sustains ~13 Hz, so a healthy pair is inside 80 ms; 250 ms means a
# stall and the sample no longer describes the same instant.
MAX_PAIR_GAP = 0.25
# The offset sweep, in seconds, around the timestamp-derived estimate.
SWEEP = (-1.0, -0.5, -0.25, 0.0, 0.25, 0.5, 1.0)


def load_movetap(path):
    S = []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("kind") == "sample":
            S.append(r)
    return S


def load_reports(path):
    """(server_t, [x, y]) for every client position report, plus the wall pairs.

    Returns the wall pairs separately because the offset estimate needs EVERY
    stamped record, not just the position ones -- more stamps is a tighter bound
    on a truncated clock.
    """
    reps, walls = [], []
    for line in open(path, encoding="utf-8", errors="replace"):
        try:
            r = json.loads(line)
        except ValueError:
            continue
        if r.get("wall") and isinstance(r.get("t"), (int, float)):
            try:
                walls.append(calendar.timegm(
                    time.strptime(r["wall"], "%Y-%m-%dT%H:%M:%SZ")) - r["t"])
            except ValueError:
                pass
        if r.get("kind") == "position_report" and r.get("reported"):
            reps.append((r["t"], list(r["reported"])))
    return reps, walls


def offset_from_stamps(walls):
    """unix epoch of server t=0, estimated from truncated whole-second stamps.

    Each stamp gives floor(unix) - t = true_offset - frac, frac in [0,1). The
    MAXIMUM over many stamps therefore approaches the true offset from below,
    and the spread is the residual uncertainty. Taking the mean instead would be
    biased low by half a second -- 144 units at run speed.
    """
    if not walls:
        return None, None
    return max(walls), max(walls) - min(walls)


def pair(S, reps, offset):
    """[(server_t, report_xy, sample, gap_seconds)] for reports inside the window."""
    if not S:
        return []
    out = []
    i = 0
    for st, p in reps:
        ut = offset + st
        while i + 1 < len(S) and abs(S[i + 1]["t"] - ut) <= abs(S[i]["t"] - ut):
            i += 1
        j = i
        # the scan above is monotone; step back once in case reports are not
        while j > 0 and abs(S[j - 1]["t"] - ut) < abs(S[j]["t"] - ut):
            j -= 1
        gap = abs(S[j]["t"] - ut)
        if gap <= MAX_PAIR_GAP:
            out.append((st, p, S[j], gap))
    return out


def sep(p, s, key="live"):
    v = s[key]
    if not all(math.isfinite(c) for c in v[:2]):
        return None
    return math.hypot(v[0] - p[0], v[1] - p[1])


def pct(xs, q):
    if not xs:
        return float("nan")
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * q))]


def score(pairs, key="live"):
    """(separations, jump rows). A jump row is (t, step, before, after)."""
    seps = [d for _t, p, s, _g in pairs
            for d in [sep(p, s, key)] if d is not None]
    jumps = []
    for i in range(1, len(pairs)):
        (_t0, p0, s0, _g0), (t1, p1, s1, _g1) = pairs[i - 1], pairs[i]
        step = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        if step < JUMP_UNITS:
            continue
        b, a = sep(p0, s0, key), sep(p1, s1, key)
        if b is not None and a is not None:
            jumps.append((t1, step, b, a))
    return seps, jumps


def collapse(jumps):
    if not jumps:
        return None
    b = sum(j[2] for j in jumps) / len(jumps)
    a = sum(j[3] for j in jumps) / len(jumps)
    return b, a, (1.0 - a / b) if b else 0.0


def newest(pattern):
    hits = sorted(glob.glob(pattern), key=os.path.getmtime)
    return hits[-1] if hits else None


def selftest():
    """Everything checkable with no captures. Exits non-zero on any gap."""
    bad = 0
    print("movesync selftest -- no captures required\n")

    print("1. the truncated-clock estimator takes the MAX, not the mean")
    # A mean would sit half a second low, which is 144 units at 288 u/s -- the
    # same size as the thing being measured.
    true_off = 1000.5
    walls = [math.floor(true_off + t) - t for t in (0.0, 0.3, 0.7, 1.1, 1.9)]
    est, spread = offset_from_stamps(walls)
    ok = abs(est - true_off) < 1.0 and est <= true_off
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] estimate {est:.3f} for a true "
          f"{true_off} -- from below, within one second (spread {spread:.3f})")
    mean = sum(walls) / len(walls)
    ok = mean < est
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] and the mean ({mean:.3f}) really is "
          f"lower, so the choice of estimator is not decorative")

    print("\n2. the jump scorer separates a resync from ordinary walking")
    # Synthetic: the client walks away from a stationary authoritative agent,
    # then snaps back onto it. Separation must be large before and small after.
    S, reps = [], []
    for k in range(10):
        S.append({"t": 100.0 + k * 0.1, "live": [0.0, 0.0, 0]})
        reps.append((k * 0.1, [k * 50.0, 0.0]))
    S.append({"t": 101.0, "live": [0.0, 0.0, 0]})
    reps.append((1.0, [10.0, 0.0]))          # the snap back
    prs = pair(S, reps, 100.0)
    seps, jumps = score(prs)
    ok = len(jumps) == 1 and jumps[0][2] > 400 and jumps[0][3] < 20
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] one jump found, separation "
          f"{jumps[0][2]:.0f} u -> {jumps[0][3]:.0f} u"
          if jumps else "   [FAIL] no jump found in the synthetic resync")

    print("\n3. CONTROL: the same scorer finds NO collapse when there is none")
    # BOTH copies jump together: the step is large, and the separation across it
    # is unchanged. A scorer that reports a collapse here is reporting its own
    # procedure rather than a fact about the client.
    #
    # THIS CONTROL WAS VACUOUS WHEN FIRST WRITTEN and the selftest passed it.
    # Its synthetic steps were 50 u against a 300 u threshold, so `j2` was empty
    # and `all(...)` over an empty list is True -- a check that could not fail,
    # inside the section whose whole job is to prove the checks can. It now
    # asserts the row count FIRST.
    S2, reps2 = [], []
    for k in range(12):
        leap = 900.0 if k >= 6 else 0.0     # both copies leap at the same index
        S2.append({"t": 100.0 + k * 0.1, "live": [k * 10.0 + leap, 0.0, 0]})
        reps2.append((k * 0.1, [k * 10.0 + leap + 600.0, 0.0]))
    _s2, j2 = score(pair(S2, reps2, 100.0))
    ok = len(j2) >= 1
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] the control produced {len(j2)} "
          f"jump row(s) to judge -- zero would make the next check vacuous")
    ok = bool(j2) and all(abs(b - a) < 50 for _t, _st, b, a in j2)
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] and separation is unchanged across "
          f"each ("
          + ", ".join(f"{b:.0f}->{c:.0f}" for _t, _st, b, c in j2)
          + ") -- so a collapse means something")

    print("\n4. pairs beyond MAX_PAIR_GAP are dropped, not silently stretched")
    far = pair([{"t": 500.0, "live": [0.0, 0.0, 0]}], [(0.0, [0.0, 0.0])], 0.0)
    ok = far == []
    bad += not ok
    print(f"   [{'PASS' if ok else 'FAIL'}] a report 500 s from any sample "
          f"yields {len(far)} pair(s) -- a fixture that resolves to nothing "
          f"must raise, not return a confident number")

    print("\n" + ("selftest passed" if not bad else f"selftest FAILED ({bad})"))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--movetap", help="a movetap-*.jsonl; default the newest")
    ap.add_argument("--capture", help="a gamesrv capture; default the newest")
    ap.add_argument("--key", default="live", choices=("live", "point"),
                    help="which movetap field to score. `point` is the raw "
                         "+0x78 and is the check that the result is not an "
                         "artifact of the reconstruction.")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    mt = a.movetap or newest(os.path.join(
        vaultpath.vault_path("captures", "movetap"), "movetap-*.jsonl"))
    cap = a.capture or newest(os.path.join(
        vaultpath.vault_path("captures", "gamesrv"), "*.jsonl"))
    if not mt or not cap:
        print("need one movetap capture and one gamesrv capture")
        return 2
    print(f"movetap: {os.path.basename(mt)}\ncapture: {os.path.basename(cap)}\n")

    S = load_movetap(mt)
    reps, walls = load_reports(cap)
    off, spread = offset_from_stamps(walls)
    if off is None:
        print("the capture carries no wall stamp, so the two clocks cannot be "
              "aligned. Nothing here would mean anything.")
        return 2
    print(f"clock offset {off:.3f} (from {len(walls)} whole-second stamps, "
          f"spread {spread:.3f}s)")

    prs = pair(S, reps, off)
    # THE PAIR COUNT COMES BEFORE THE VERDICT. warpscan learned this the hard
    # way: a run with nothing in it prints the same shape of report as a run
    # with everything in it, and only the count tells them apart.
    print(f"PAIRS {len(prs)} of {len(reps)} reports and {len(S)} samples "
          f"(dropped {len(reps) - len(prs)} outside +/-{MAX_PAIR_GAP}s)")
    if len(prs) < 20:
        print("FAIL: fewer than 20 pairs. These two captures barely overlap; "
              "this run measured nothing. Check that the movetap window sits "
              "inside the capture's span.")
        return 1

    seps, jumps = score(prs, a.key)
    print(f"\nseparation ({a.key} vs the client's own report), n={len(seps)}:")
    print(f"   p50 {pct(seps, .5):.1f} u   p90 {pct(seps, .9):.1f} u   "
          f"max {max(seps):.1f} u")

    print(f"\nclient steps over {JUMP_UNITS:.0f} u, with the separation either "
          f"side:")
    print("   server t     step     before      after")
    for t, st, b, c in jumps:
        print(f"   {t:9.3f}  {st:7.1f}   {b:8.1f}   {c:8.1f}")
    c = collapse(jumps)
    if not jumps:
        print("   (none -- no resync in this window)")
    else:
        print(f"\n   n={len(jumps)}  mean {c[0]:.1f} u -> {c[1]:.1f} u  "
              f"(collapse {100 * c[2]:.0f}%)")

    # THE CONTROL. Pair every report against a sample from the wrong time. If
    # the collapse survives, it is a fact about the procedure and not about the
    # client, and the headline above must not be believed.
    if jumps:
        shifted = pair(S, reps, off + 7.0)
        _s, j2 = score(shifted, a.key)
        c2 = collapse(j2)
        print(f"\n   CONTROL (paired 7 s out of true): "
              + (f"n={len(j2)} mean {c2[0]:.1f} -> {c2[1]:.1f} u "
                 f"(collapse {100 * c2[2]:.0f}%)" if c2 else "no jumps"))
        if c2 and c2[2] > 0.5 * c[2]:
            print("   WARNING: the control collapses nearly as much as the "
                  "real pairing. This statistic is measuring the procedure.")

    # ALIGNMENT SWEEP. A collapse that exists at one offset only is an artifact
    # of a whole-second clock, not a property of the client.
    print("\n   alignment sweep (collapse % vs offset error):")
    row = []
    for d in SWEEP:
        _s, j = score(pair(S, reps, off + d), a.key)
        cc = collapse(j)
        row.append(f"{d:+.2f}s:{'--' if not cc else '%.0f%%' % (100 * cc[2])}")
    print("      " + "  ".join(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
