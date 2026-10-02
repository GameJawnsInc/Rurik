"""pressstopjoin.py -- does retail STOP a body walking on held keys at an in-reach press?

    python toolkit/authsrv/pressstopjoin.py            # the census over the live corpus
    python toolkit/authsrv/pressstopjoin.py --rows     # every press in the cell, with
                                                       # the movement-family s2c to ME

THE QUESTION (MOVECODE-1z-ds, studies/movecode/FINDINGS.md): the owner's "slides
during attacks" were swings our server opened on a body still walking under held
keys -- a c2s 0x0026 in reach, nothing sent at the press, the body walking on through
the swing. What does ArenaNet's server send at such a press, and does the body stop?

THE CELL, per c2s 0x0026 on every live connection (livewire.decode_conn, both
directions on one clock; the observer by the self-scoped property 41, adrenjoin's
rule): the last c2s movement input before the press is a 0x003D with its
movementType set, at most KBD_AGE s old, with no 0x003E / 0x0047 after it; and the
press is answered by the observer's OWN attack_started ([4, me, ...]) within
ANSWER_WINDOW s with no 0x002A follow naming the observer ahead of it -- the in-reach
press on a walking body. For each: the first 0x0028 [me] after the press (and whether
it leads the swing), and the next c2s movement report -- how far the body travelled
from the last report, against walking on through the whole span at the report's
family rate and against stopping at the press.

MEASURED 2026-10-01 over the live corpus: 527 presses, 180 after a moving 0x003D
<= 3 s with no stop, 42 in the cell; 39 carry a 0x0028 [me], 37 of them within 60 ms
of the press (p50 0.040 s); 24 in the swing's batch, 15 ahead of it (11 of the 12
swings that waited over 0.1 s); 28 of 28 next reports nearer stop-at-press than
walk-on. Read-only; standard library only; refuses non-live captures by construction
(livewire.live_connections).

--after-stop (MOVECODE-1z-ds.10, MEASURED 2026-10-02): the first key report after
a stopped in-reach press -- 27; answered with a lead 26, p50 767 u, 0 zero leads;
[8, me, 0] then the lead on 23; 0 of 3 reports before the swing's close cancelled.
"""
import argparse
import collections
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import livewire  # noqa: E402

PRESS = 0x0026
PINT, PINT_T = 0x009F, 0x00A0
PROP_MAX_ENERGY = 41            # self-scoped: adrenjoin.whose_agent's rule
PROP_ATTACK_STARTED = 4
REPORT, CLICK, STOP_RPT = 0x003D, 0x003E, 0x0047
FOLLOW, HALT = 0x002A, 0x0028
KBD_AGE = 3.0                   # s: the last 0x003D's age at the press
ANSWER_WINDOW = 0.25            # s: the swing answering the press
# The census family rates (castpolicy.cast_stop_reckon's table, rounded to the
# FAMILY_RATE the server uses): forward 1-3, backward 4-6, side 7-8.
FAMILY_RATE = {1: 1.0, 2: 1.0, 3: 1.0, 4: 0.66, 5: 0.66, 6: 0.66, 7: 0.75, 8: 0.75}
RUN_SPEED = 288.0
MOVE_FAMILY = {0x0025: "DIR", HALT: "STOP", 0x0029: "WAYPT", FOLLOW: "DEST",
               0x002B: "SPEED", 0x002C: "POS"}


def whose_agent(merged):
    """The observing player's agent id, or None -- NO FALLBACK (adrenjoin)."""
    seen = {int(v[2]) for _t, d, op, v in merged
            if d == "s2c" and op == PINT and len(v) > 2
            and int(v[1]) == PROP_MAX_ENERGY}
    return seen.pop() if len(seen) == 1 else None


def _mine(v, me):
    return len(v) > 1 and isinstance(v[1], int) and int(v[1]) == me


def join_press(merged, i, me):
    """One press -> (kind, row). kind: 'press' (not walking), 'kbd' (walking, not
    the cell), 'cell' (walking, answered in reach)."""
    t = merged[i][0]
    last = None
    for j in range(i - 1, -1, -1):
        tj, dj, opj, vj = merged[j]
        if dj == "c2s" and opj in (REPORT, CLICK, STOP_RPT):
            last = (tj, opj, vj)
            break
        if t - tj > 10.0:
            break
    if last is None or last[1] != REPORT or t - last[0] > KBD_AGE:
        return "press", None
    lv = last[2]
    mt = int(lv[4]) if len(lv) > 4 else 0
    if not mt:
        return "press", None
    swing = follow = None
    for j in range(i + 1, len(merged)):
        tj, dj, opj, vj = merged[j]
        if tj - t > ANSWER_WINDOW:
            break
        if dj != "s2c":
            continue
        if opj == FOLLOW and _mine(vj, me) and follow is None:
            follow = tj
        if (opj == PINT_T and len(vj) > 2 and int(vj[1]) == PROP_ATTACK_STARTED
                and int(vj[2]) == me):
            swing = tj
            break
    if swing is None or (follow is not None and follow < swing):
        return "kbd", None
    halt, wire, nxt = None, [], None
    for j in range(i + 1, len(merged)):
        tj, dj, opj, vj = merged[j]
        if tj - t > 6.0:
            break
        if dj == "s2c" and opj in MOVE_FAMILY and _mine(vj, me):
            if tj - swing <= 0.6:
                wire.append((round(tj - t, 3), MOVE_FAMILY[opj], vj[2:]))
            if opj == HALT and halt is None:
                halt = tj - t
        if dj == "c2s" and opj in (REPORT, CLICK, STOP_RPT):
            nxt = (tj, opj, vj)
            break
    row = dict(t=round(t, 3), mt=mt, kbd_age=round(t - last[0], 3),
               swing=round(swing - t, 3), halt=(None if halt is None else round(halt, 3)),
               wire=wire, moved=None, walk_on=None, stop_at_press=None)
    if nxt is not None and nxt[1] in (REPORT, STOP_RPT):
        q, p0 = nxt[2][1], lv[1]
        if isinstance(q, (list, tuple)) and isinstance(p0, (list, tuple)):
            sp = RUN_SPEED * FAMILY_RATE.get(mt, 1.0)
            row["moved"] = round(math.hypot(q[0] - p0[0], q[1] - p0[1]), 1)
            row["walk_on"] = round(sp * (nxt[0] - last[0]), 1)
            row["stop_at_press"] = round(sp * (t - last[0]), 1)
    return "cell", row


def scan():
    """(counts, [(stamp, conn, row)]) over every live connection."""
    counts = {"press": 0, "kbd": 0, "cell": 0}
    rows = []
    for capdir, gf in livewire.live_connections():
        conn, merged, _ok = livewire.decode_conn(capdir, gf)
        me = whose_agent(merged)
        if me is None:
            continue
        stamp = os.path.basename(capdir)
        for i, (_t, d, op, _v) in enumerate(merged):
            if d != "c2s" or op != PRESS:
                continue
            kind, row = join_press(merged, i, me)
            counts["press"] += 1
            if kind in ("kbd", "cell"):
                counts["kbd"] += 1
            if kind == "cell":
                counts["cell"] += 1
                rows.append((stamp, conn, row))
    return counts, rows


def census(counts, rows):
    cell = [r for _s, _c, r in rows]
    halted = [r for r in cell if r["halt"] is not None]
    d = sorted(r["halt"] for r in halted)
    out = [f"presses {counts['press']}; after a moving 0x003D <= {KBD_AGE:g} s with no "
           f"stop: {counts['kbd']}; in reach, answered by the swing: {counts['cell']}",
           f"  carry a 0x0028 [me]: {len(halted)} of {len(cell)}"]
    if d:
        out.append(f"  its delay after the press: min {d[0]:.3f} p50 "
                   f"{statistics.median(d):.3f} max {d[-1]:.3f} s; within 60 ms: "
                   f"{sum(x <= 0.06 for x in d)}")
        ahead = sum(r["halt"] < r["swing"] - 0.005 for r in halted)
        same = sum(abs(r["halt"] - r["swing"]) <= 0.005 for r in halted)
        waited = [r for r in halted if r["swing"] > 0.1]
        out.append(f"  in the swing's batch {same}, ahead of it {ahead}; of the "
                   f"{len(waited)} swings that waited > 0.1 s, the stop led "
                   f"{sum(r['halt'] < r['swing'] - 0.005 for r in waited)}")
    judged = [r for r in halted if r["moved"] is not None]
    near = sum(abs(r["moved"] - r["stop_at_press"]) < abs(r["moved"] - r["walk_on"])
               for r in judged)
    out.append(f"  next report nearer stop-at-press than walk-on: {near} of {len(judged)}")
    return "\n".join(out)


def after_stop():
    """MOVECODE-1z-ds.10: retail's answer to the FIRST c2s 0x003D after a stopped press.

    For every cell press that carried the stop, the first movement input after it, when it
    is a 0x003D: the 0x0029 lead to me within 60 ms (its length from the report's own point;
    under 1 u is a zero lead), [8, me, 0] (the hold's release) and its order against the
    lead, and [3, me, 0] (attack_stopped) -- split by whether the report came before the
    swing's close ([1, me] melee finished, or my own 0x00A4 launch)."""
    rows = []
    for capdir, gf in livewire.live_connections():
        conn, merged, _ok = livewire.decode_conn(capdir, gf)
        me = whose_agent(merged)
        if me is None:
            continue
        for i, (t, d, op, _v) in enumerate(merged):
            if d != "c2s" or op != PRESS:
                continue
            kind, row = join_press(merged, i, me)
            if kind != "cell" or row["halt"] is None:
                continue
            t_sw = t + row["swing"]
            close = rep = None
            for j in range(i + 1, len(merged)):
                tj, dj, opj, vj = merged[j]
                if tj - t > 6.0:
                    break
                if dj == "s2c" and close is None and tj >= t_sw and (
                        (opj == PINT and len(vj) > 2 and int(vj[1]) == 1 and int(vj[2]) == me)
                        or (opj == 0x00A4 and len(vj) > 1 and int(vj[1]) == me)):
                    close = tj
                if dj == "c2s" and opj in (REPORT, CLICK, STOP_RPT, PRESS, 0x0027, 0x0046):
                    rep = (j, tj, opj, vj)
                    break
            if rep is None or rep[2] != REPORT:
                continue
            j, tr, _op, rv = rep
            lead, order, stopped = None, [], False
            for k in range(j + 1, len(merged)):
                tk, dk, opk, vk = merged[k]
                if tk - tr > 0.06:
                    break
                if dk != "s2c" or len(vk) < 2 or not isinstance(vk[1], int):
                    continue
                if opk == 0x0029 and int(vk[1]) == me and lead is None:
                    lead = math.hypot(vk[2][0] - rv[1][0], vk[2][1] - rv[1][1])
                    order.append("LEAD")
                if (opk == PINT and len(vk) > 3 and int(vk[1]) == 8 and int(vk[2]) == me
                        and int(vk[3]) == 0):
                    order.append("REL")
                if opk == PINT and len(vk) > 3 and int(vk[1]) == 3 and int(vk[2]) == me:
                    stopped = True
            rows.append(dict(pre_landing=(close is None or tr < close), lead=lead,
                             order=tuple(order), stopped=stopped))
    leads = sorted(r["lead"] for r in rows if r["lead"] is not None)
    pre = [r for r in rows if r["pre_landing"]]
    return "\n".join([
        f"first 0x003D after a stopped in-reach press: {len(rows)}",
        f"  answered with a lead: {len(leads)}"
        + (f", p50 {statistics.median(leads):.0f} u, zero leads (< 1 u): "
           f"{sum(x < 1.0 for x in leads)}" if leads else ""),
        f"  order: {collections.Counter(r['order'] for r in rows).most_common(4)}",
        f"  before the swing's close: {len(pre)}, cancelled ([3, me, 0]): "
        f"{sum(r['stopped'] for r in pre)}; after it: {len(rows) - len(pre)}, cancelled: "
        f"{sum(r['stopped'] for r in rows if not r['pre_landing'])}"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--rows", action="store_true", help="print every press in the cell")
    ap.add_argument("--after-stop", action="store_true",
                    help="retail's answer to the first key report after the stop (1z-ds.10)")
    a = ap.parse_args(argv)
    if a.after_stop:
        print(after_stop())
        return 0
    counts, rows = scan()
    print(census(counts, rows))
    if a.rows:
        for stamp, conn, r in rows:
            print(f"{stamp} {conn} {r['t']:8.2f} mt {r['mt']} kbd {r['kbd_age']:.2f}s "
                  f"swing +{r['swing']:.3f} halt "
                  f"{'-' if r['halt'] is None else '+%.3f' % r['halt']} moved {r['moved']} "
                  f"walk-on {r['walk_on']} stop-at-press {r['stop_at_press']}")
            for w in r["wire"]:
                print(f"      {w[0]:+.3f} {w[1]} {str(w[2])[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
