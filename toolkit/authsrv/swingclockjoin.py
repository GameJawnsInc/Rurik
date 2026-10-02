"""swingclockjoin.py -- does a MOVE between two swings delay the next one on retail?

    python toolkit/authsrv/swingclockjoin.py          # the census over the live corpus
    python toolkit/authsrv/swingclockjoin.py --rows   # every binding press

THE QUESTION (MOVECODE-1z-ds.11). ANIMREF-RE 31 froze the player's swing clock while the
body moves, and MOVECODE-1z-dg charged that freeze through the whole moving span, on
"retail's START-to-START across a move = interval + moving span (28 of 28 pairs; 1z-dc.3:
2.701 s against 2.657)". The owner, 20261002T124708: "sometimes when i press the attack
button right next to the enemy i'll just slowly turn for ~1s before attacking". Which rule
does retail's server keep: start-to-start = period, or period + moving span?

THE JOIN, per c2s 0x0026 on every live connection (livewire.decode_conn; the observer by
property 41), answered by the observer's own attack_started within 2.0 s with no follow of
mine and no movement input of mine first: the previous own start p0 (< 3 s back), the 0x0035
period in force, and the MOVING span between p0 and the press (time whose last movement
input was a moving 0x003D or a click). THE BINDING presses are the ones the two rules split
on: the press came while the interval was still running (press - p0 < period - 0.05), so
  no charge:      start-to-start = period
  1z-dg's charge: start-to-start = period + span
and the swing's own instant says which. A press after the interval elapsed is answered at
the press under both rules and decides nothing; it is counted, not scored.

MEASURED 2026-10-02 over the live corpus: 153 answered presses with a previous start
< 3 s; 98 binding, 88 of them after the body moved > 0.1 s. Of those 88, start-to-start
lands within 0.05 s of the PERIOD on 55 and of period + span on 0 (the other 33 come
EARLY, 0.2-1.6 s inside the period -- a cancelled previous swing or a retarget, open).
Unmoved and binding: 6 of 10 at the period. 1z-dg's charge is refuted at scale.
Read-only; standard library only; refuses non-live captures by construction.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import livewire  # noqa: E402
import pressstopjoin  # noqa: E402

BAND = 0.05      # s: a start-to-start within this of a rule's prediction matches it


def _f32(word):
    return struct.unpack("<f", struct.pack("<I", int(word) & 0xFFFFFFFF))[0]


def scan():
    rows = []
    for capdir, gf in livewire.live_connections():
        conn, merged, _ok = livewire.decode_conn(capdir, gf)
        me = pressstopjoin.whose_agent(merged)
        if me is None:
            continue
        starts, periods, moves = [], [], []
        for t, d, op, v in merged:
            if d == "s2c" and op == 0x00A0 and len(v) > 3 and int(v[1]) == 4 and int(v[2]) == me:
                starts.append(t)
            elif d == "s2c" and op == 0x0035 and len(v) > 2 and int(v[1]) == me:
                periods.append((t, _f32(v[2])))
            elif d == "c2s" and op in (0x003D, 0x0047, 0x003E):
                moves.append((t, op == 0x003E or (op == 0x003D and len(v) > 4 and int(v[4]) != 0)))
        for i, (t, d, op, v) in enumerate(merged):
            if d != "c2s" or op != 0x0026:
                continue
            sw = None
            for j in range(i + 1, len(merged)):
                tj, dj, opj, vj = merged[j]
                if tj - t > 2.0:
                    break
                if dj == "c2s" and opj in (0x003D, 0x003E, 0x0047, 0x0026, 0x0027, 0x0046):
                    break
                if dj == "s2c" and opj == 0x002A and len(vj) > 1 and int(vj[1]) == me:
                    break
                if (dj == "s2c" and opj == 0x00A0 and len(vj) > 3 and int(vj[1]) == 4
                        and int(vj[2]) == me):
                    sw = tj
                    break
            if sw is None:
                continue
            prev = [s for s in starts if s < t - 1e-6]
            per = [p for pt, p in periods if pt <= t]
            if not prev or not per or t - prev[-1] > 3.0:
                continue
            p0, period = prev[-1], per[-1]
            before = [m for m in moves if m[0] <= p0]
            state = before[-1][1] if before else False
            span, last_t = 0.0, p0
            for mt, mv in moves:
                if p0 < mt <= t:
                    if state:
                        span += mt - last_t
                    state, last_t = mv, mt
            if state:
                span += t - last_t
            rows.append(dict(cap=os.path.basename(capdir), t=round(t, 3), period=round(period, 3),
                             dt_prev=round(t - p0, 3), span=round(span, 3),
                             s2s=round(sw - p0, 3),
                             binding=(t - p0) < period - BAND))
    return rows


def census(rows):
    b = [r for r in rows if r["binding"]]
    moved = [r for r in b if r["span"] > 0.1]
    def near(rs, key):
        return sum(abs(r["s2s"] - key(r)) <= BAND for r in rs)
    return "\n".join([
        f"answered presses with a previous start < 3 s: {len(rows)}; binding (pressed inside "
        f"the interval): {len(b)}, of which the body MOVED > 0.1 s since the start: {len(moved)}",
        f"  moved & binding: start-to-start within {BAND:g} s of period {near(moved, lambda r: r['period'])}"
        f", of period + span {near(moved, lambda r: r['period'] + r['span'])}",
        f"  unmoved & binding: within {BAND:g} s of period "
        f"{near([r for r in b if r['span'] <= 0.1], lambda r: r['period'])} of "
        f"{len(b) - len(moved)}"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--rows", action="store_true")
    a = ap.parse_args(argv)
    rows = scan()
    print(census(rows))
    if a.rows:
        for r in rows:
            if r["binding"]:
                print(f"  {r['cap']} {r['t']:9.2f} period {r['period']} dt_prev {r['dt_prev']} "
                      f"span {r['span']} start-to-start {r['s2s']} "
                      f"(period {r['s2s'] - r['period']:+.3f}, +span {r['s2s'] - r['period'] - r['span']:+.3f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
