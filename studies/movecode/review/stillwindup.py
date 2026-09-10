r"""Retail's player windups split by what the client REPORTED inside them: nothing, a
still 0x003D (position repeats the previous report), or a moved one -- and what followed.

    python studies/movecode/review/stillwindup.py

THE QUESTION (MOVECODE-1z-dd). 1z-db shipped "a keyboard report that moved nothing does not
cancel the swing" and RUN-1zDB found the same report still killing the swing through a second
door: `cancel_on_move` forgets the TARGET on every report, ungated, and `attack_tick` then
drops the swing as `move-ended-order`. Extending the displacement gate to the target-forget
is the same rule applied to a second consumer, and this is the retail check that could refute
it: if ArenaNet's player, with a still report inside its windup, then STOPS at the moved rate,
the target-forget on a still report is retail's and the extension is wrong.

PREDICTION, stated before the run: such windups are RARE on retail (its corpus stands and
auto-attacks; 1z-cz.2 -- "retail has never walked the corner"), and the ones that exist LAND
at the still rate (~99 %), not the moved rate (~36 %). Fewer than 5 of them is NOT FOUND, and
the extension stands on 1z-db's rule alone.

Same join as swingcensus.retail(): livewire's live connections, the player named by whose
0x0029 grants answer the c2s headings, outcome = the first of damage/stop/finish within 3 s.
Standard library only.
"""
import bisect
import collections
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for _sub in ("toolkit", "toolkit/authsrv", "toolkit/clientscan", HERE):
    sys.path.insert(0, os.path.join(ROOT, _sub))

import swingcensus as SC          # noqa: E402

WINDUP = 0.90     # s after the START inside which a report counts as "in the windup"
STILL = 1.0       # u, the empty gap 1z-db.4 measured (0.1 % of reports in 0.001-1 u)


def run(verbose=True):
    import livewire
    table = {k: collections.Counter() for k in ("none", "still", "moved")}
    still_rows = []
    conns = 0
    for capdir, cf in livewire.live_connections():
        try:
            _c, merged, ok = livewire.decode_conn(capdir, cf)
        except Exception:                                   # noqa: BLE001
            continue
        if not ok or not merged:
            continue
        conns += 1
        pid = SC._player_of(merged)
        if pid is None:
            continue
        # the player's own report stream, with per-report displacement
        reps = []
        prev = None
        for (t, dr, op, v) in merged:
            if dr == "c2s" and op == SC.C2S_HEADING and len(v) >= 2:
                p = (float(v[1][0]), float(v[1][1]))
                d = math.hypot(p[0] - prev[0], p[1] - prev[1]) if prev else None
                reps.append((t, d))
                prev = p
        rt = [t for t, _d in reps]
        ev = []
        for (t, dr, op, v) in merged:
            if dr != "s2c":
                continue
            if op == 0xA0 and len(v) >= 4 and v[1] == SC.STARTED and v[2] == pid:
                ev.append((t, "start"))
            elif op == 0x9F and len(v) >= 3 and v[1] == SC.FINISHED and v[2] == pid:
                ev.append((t, "finish"))
            elif op == 0x9F and len(v) >= 3 and v[1] == SC.STOPPED and v[2] == pid:
                ev.append((t, "stop"))
            elif op == 0xA3 and len(v) >= 5 and v[1] in (16, 17) and v[3] == pid:
                ev.append((t, "damage"))
        ev.sort()
        for i, (t, k) in enumerate(ev):
            if k != "start":
                continue
            later = [(t2, k2) for t2, k2 in ev[i + 1:] if 0 < t2 - t <= 3.0]
            outcome = "silent"
            end = t + 3.0
            for t2, k2 in later:
                if k2 in ("damage", "stop", "finish"):
                    outcome = k2
                    end = t2
                    break
            lo = bisect.bisect_right(rt, t)
            hi = bisect.bisect_right(rt, min(end, t + WINDUP))
            inside = [d for _t, d in reps[lo:hi] if d is not None]
            if not inside:
                cls = "none"
            elif max(inside) < STILL:
                cls = "still"
            else:
                cls = "moved"
            table[cls][outcome] += 1
            if cls == "still":
                still_rows.append((os.path.basename(capdir), cf, round(t, 3), outcome,
                                   [round(d, 3) for d in inside]))
    if verbose:
        print(f"retail, {conns} connections; the PLAYER's windups by the report inside them:")
        for cls in ("none", "still", "moved"):
            c = table[cls]
            n = sum(c.values())
            land = c.get("damage", 0)
            stop = c.get("stop", 0)
            pct = (lambda x: f"{100.0 * x / n:5.1f} %" if n else "   -  ")
            print(f"  {cls:6s} n={n:5d}  damage {land:5d} ({pct(land)})  stop {stop:4d} "
                  f"({pct(stop)})  finish-no-damage {c.get('finish', 0):3d}  "
                  f"silent {c.get('silent', 0):3d}")
        print("  the STILL windups, one per line (capture, conn, t, outcome, displacements):")
        for r in still_rows:
            print("   ", r)
    return table, still_rows, conns


if __name__ == "__main__":
    run()
