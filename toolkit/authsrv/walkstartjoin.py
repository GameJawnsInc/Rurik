"""walkstartjoin.py -- what does retail do with a WALK-START, inside the windup and after a stop?

    python toolkit/authsrv/walkstartjoin.py           # both censuses over the live corpus
    python toolkit/authsrv/walkstartjoin.py --rows    # every row

THE QUESTION (MOVECODE-1z-ds.14). Our 0x003D arm measures a report's displacement from the
previous movement input, and a report that moved nothing takes 1z-db's STILL path: no [3],
the target and the follow kept. A walk-start -- the key going down after a stop -- moved
nothing by construction: it is the body's position when the key went down. Since 1z-ds.10
that covers the first report after OUR pin + halt, and since 1z-db the first report after
the client's own 0x0047. What does retail's server do with it?

CENSUS 1, THE WINDUP. Per own attack_started [4, me, T] on every live connection
(livewire.decode_conn; the observer by property 41), the windup runs to the first own
[3, me, 0] (CANCEL), [1, me] or own 0x00A4 launch (LANDED), within 1.0 s. The first moving
c2s 0x003D inside it is classed by what preceded it (back to the previous c2s movement
input, at most 10 s): STOP0 a 0x0047 with this report <= 1 u from it; STOPMV a 0x0047
further off; HALT a server 0x0028 [me] since that input (retail's press stop); CONT a
moving 0x003D (a continuing walk); CLICK a 0x003E; NOPREV nothing within 10 s.

CENSUS 2, AFTER A STOP. pressstopjoin's in-reach walking press with its 0x0028 [me] (the
"cell" with a halt), whose first c2s input after the press is a MOVING 0x003D: from that
report to the next press / click / skill (or 4 s), does the server send a follow 0x002A [me]
or a NEW own attack_started? A 0x002A answering a c2s 0x003F interact order in that window
is the interact walk, not the attack, and is counted apart. CONTROL: the press's own swing
within 0.3 s.

MEASURED 2026-10-02 over the live corpus (122 connections with an observer):
  CENSUS 1: 32 rows, 29 CANCELLED. STOP0 6/0, STOPMV 3/0, HALT 8 cancelled / 2 landed
  (20260817T231139 697.197 at 0.549 s, 20260919T103604 454.644 at 0.638 s -- at most 16 ms
  before their landing if 454.644 is the 1.5 s spear set), NOPREV 12/0, CONT 0/1 (the one
  continuing walk, 612.08 at 0.562 s). Every moving input inside a windup is a walk-start
  but one, and retail cancels it.
  CENSUS 2: 39 stopped presses (CONTROL 39 of 39 swing), 27 first inputs a moving 0x003D;
  0 attack follows and 0 new starts before the next press (21) / skill (1) / 4 s (5); 1
  interact walk (20260913T210901 377.8, ordered by its own c2s 0x003F).
Read-only; standard library only; refuses non-live captures by construction
(livewire.live_connections).
"""
import argparse
import collections
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import livewire  # noqa: E402
import pressstopjoin  # noqa: E402

CLASSES = ("STOP0", "STOPMV", "HALT", "CONT", "CLICK", "NOPREV")


def _is(v, k, x):
    try:
        return len(v) > k and int(v[k]) == x
    except (TypeError, ValueError):
        return False


def windup_rows(cap, merged, me):
    rows = []
    starts = [i for i, (t, d, op, v) in enumerate(merged)
              if d == "s2c" and op == 0x00A0 and _is(v, 1, 4) and _is(v, 2, me)]
    for si in starts:
        t_s = merged[si][0]
        end = outcome = None
        for j in range(si + 1, len(merged)):
            t, d, op, v = merged[j]
            if t - t_s > 1.0:
                break
            if d != "s2c":
                continue
            if op == 0x009F and _is(v, 1, 3) and _is(v, 2, me):
                end, outcome = j, "CANCEL"
                break
            if op == 0x009F and _is(v, 1, 1) and _is(v, 2, me):
                end, outcome = j, "LANDED"
                break
            if op == 0x00A4 and _is(v, 1, me):
                end, outcome = j, "LANDED"
                break
            if op == 0x00A0 and _is(v, 1, 4) and _is(v, 2, me):
                break
        if end is None:
            continue
        for j in range(si + 1, end):
            t, d, op, v = merged[j]
            if d == "c2s" and op == 0x003E:
                break
            if not (d == "c2s" and op == 0x003D and len(v) > 4
                    and isinstance(v[4], int) and v[4] != 0):
                continue
            prev, halt = None, False
            for k in range(j - 1, -1, -1):
                tk, dk, opk, vk = merged[k]
                if t - tk > 10:
                    break
                if dk == "s2c" and opk == 0x0028 and _is(vk, 1, me):
                    halt = True
                if dk == "c2s" and opk in (0x003D, 0x0047, 0x003E):
                    prev = (tk, opk, vk)
                    break
            if prev is None:
                cls = "NOPREV"
            elif halt:
                cls = "HALT"
            elif prev[1] == 0x0047:
                try:
                    dd = math.hypot(v[1][0] - prev[2][1][0], v[1][1] - prev[2][1][1])
                except (TypeError, IndexError):
                    dd = None
                cls = "STOP0" if dd is not None and dd <= 1.0 else "STOPMV"
            elif prev[1] == 0x003E:
                cls = "CLICK"
            else:
                cls = "CONT"
            rows.append((cap, round(t_s, 3), round(t - t_s, 3), cls, outcome))
            break
    return rows


def after_stop_rows(cap, merged, me):
    rows, cells, ctrl = [], 0, 0
    for i, (t, d, op, v) in enumerate(merged):
        if d != "c2s" or op != 0x0026:
            continue
        kind, row = pressstopjoin.join_press(merged, i, me)
        if kind != "cell" or row["halt"] is None:
            continue
        cells += 1
        if any(dj == "s2c" and opj == 0x00A0 and _is(vj, 1, 4) and _is(vj, 2, me)
               for tj, dj, opj, vj in merged[i + 1:i + 400] if tj - t <= 0.3):
            ctrl += 1
        rep = None
        for j in range(i + 1, len(merged)):
            tj, dj, opj, vj = merged[j]
            if tj - t > 6.0:
                break
            if dj == "c2s" and opj in (0x003D, 0x003E, 0x0047, 0x0026, 0x0027, 0x0046):
                rep = j
                break
        if (rep is None or merged[rep][2] != 0x003D
                or not (len(merged[rep][3]) > 4 and merged[rep][3][4])):
            continue
        tr = merged[rep][0]
        fol = interact = starts = 0
        interact_order = False
        until = "4s"
        for k in range(rep + 1, len(merged)):
            tk, dk, opk, vk = merged[k]
            if tk - tr > 4.0:
                break
            if dk == "c2s" and opk == 0x003F:
                interact_order = True
            if dk == "c2s" and opk in (0x0026, 0x003E, 0x0027, 0x0046):
                until = hex(opk)
                break
            if dk != "s2c":
                continue
            if opk == 0x002A and _is(vk, 1, me):
                if interact_order:
                    interact += 1
                else:
                    fol += 1
            if opk == 0x00A0 and _is(vk, 1, 4) and _is(vk, 2, me):
                starts += 1
        rows.append((cap, round(t, 2), round(tr - t, 2), fol, interact, starts, until))
    return rows, cells, ctrl


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", action="store_true", help="every row")
    a = ap.parse_args()
    wrows, arows, cells, ctrl, nconn = [], [], 0, 0, 0
    for capdir, gf in livewire.live_connections():
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        me = pressstopjoin.whose_agent(merged)
        if me is None:
            continue
        nconn += 1
        cap = os.path.basename(capdir)
        wrows += windup_rows(cap, merged, me)
        r, c, k = after_stop_rows(cap, merged, me)
        arows += r
        cells += c
        ctrl += k
    print(f"connections with an observer: {nconn}")
    tab = collections.Counter((r[3], r[4]) for r in wrows)
    print(f"\n#### CENSUS 1: the first moving 0x003D inside an own windup -- {len(wrows)} rows")
    for cls in CLASSES:
        print(f"  {cls:7s} cancelled {tab[(cls, 'CANCEL')]:3d}  landed {tab[(cls, 'LANDED')]:3d}")
    print(f"  all     cancelled {sum(r[4] == 'CANCEL' for r in wrows):3d}  landed "
          f"{sum(r[4] == 'LANDED' for r in wrows):3d}")
    for r in wrows:
        if r[4] == "LANDED" or a.rows:
            print("   ", r)
    print(f"\n#### CENSUS 2: stopped in-reach walking presses {cells}; CONTROL their own swing "
          f"<= 0.3 s {ctrl}; first input after the press a MOVING 0x003D {len(arows)}")
    print(f"  with an attack follow 0x002A [me] before the next press/click/skill (<= 4 s): "
          f"{sum(r[3] > 0 for r in arows)}")
    print(f"  with an interact walk (0x002A after a c2s 0x003F): {sum(r[4] > 0 for r in arows)}")
    print(f"  with a NEW own attack_started before it: {sum(r[5] > 0 for r in arows)}")
    print(f"  window ended by: {dict(collections.Counter(r[6] for r in arows))}")
    for r in arows:
        if r[3] or r[5] or a.rows:
            print("   ", r)


if __name__ == "__main__":
    main()
