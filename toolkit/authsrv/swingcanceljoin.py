"""swingcanceljoin.py -- which swing holds retail's clock: the one that LANDED, or any?

    python toolkit/authsrv/swingcanceljoin.py          # the census over the live corpus
    python toolkit/authsrv/swingcanceljoin.py --rows   # every binding press, classified

THE QUESTION (MOVECODE-1z-ds.13). swingclockjoin.py measured retail's start-to-start across a
move at the PERIOD on 55 of 88 binding presses and left 33 "early, a cancelled previous swing
or a retarget restarting the clock, open". Our clock follows the TARGET: a retarget resets
it, a re-press on the target a move forgot keeps it (MOVECODE-1z-dg's resume). Which fact
does retail's clock follow?

THE JOIN is swingclockjoin's (per c2s 0x0026 on every live connection, livewire.decode_conn;
the observer by property 41; answered by the observer's own attack_started [4, me, T] within
2.0 s with nothing of mine between; the previous own start p0 < 3 s back), on CORRECTED
operands, because swingclockjoin's reads two things short:
  start  = the later of p0 and an own attack-skill start [50, me, T] between p0 and the press
           (the next auto start is [50] + period, 6 of 6);
  period = the 0x0035 base x its MODIFIER at that start (v[2] * v[3]; 15 of swingclockjoin's
           33 off-period rows carry modifier 0.67, 0 of its 55 on-period rows).
A press is BINDING when it came inside the corrected period (dt < eff - BAND). Its answer is
WAIT (the swing at start + eff, within BAND), RESET (the swing at the press, <= IMMEDIATE s,
early) or OTHER. The candidate column is CANCELLED: the previous start's swing ended in its
WINDUP -- an own [3, me, 0] after the start and before any landing ([1, me] / own 0x00A4 /
0x00A3 damage props 16-17-55 from me / [38, T, me]), or the previous target dying before any
landing.

MEASURED 2026-10-02 over the live corpus: 153 answered presses, 98 binding on the raw
period, 88 of them after the body moved. Moved and binding on the corrected period: 82, 79
scored (WAIT 65, RESET 14). CANCELLED: TRUE -> RESET 13, WAIT 0 | FALSE -> RESET 1, WAIT 65
(1 wrong: 20260929T100038 549.18, an IAS stance mid-gap). Ours (reset iff retarget): 10
wrong. The discriminating rows (ours and CANCELLED disagree, 11 moved + 1 unmoved): the
same-target re-press after a windup cancel swings AT THE PRESS 5 of 5 (1.5 / 1.75 / 2.475 s
weapons, 3 of the 5 from one bow capture; no 1.33 s row); a retarget after a LANDED swing
WAITS 6 of 7 (the 7th is 549.18; 462.19 was pressed 70 ms before start + eff, so it barely
discriminates). The rival "a cancel restarts the clock at the [3]" fits 0 of 13. Unmoved and
binding: CANCELLED 0 wrong of 9, ours 1. Read-only; standard library only; refuses non-live captures
by construction (livewire.live_connections).
"""
import argparse
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import livewire  # noqa: E402
import pressstopjoin  # noqa: E402

BAND = 0.05          # s: a start-to-start within this of start + eff is WAIT
IMMEDIATE = 0.07     # s: a swing this soon after the press is "at the press"
DMG_PROPS = (16, 17, 55)   # 0x00A3 [prop, target, source, value]: damage / critical / armour-ignoring


def f32(word):
    return struct.unpack("<f", struct.pack("<I", int(word) & 0xFFFFFFFF))[0]


def _i(x):
    return int(x) if isinstance(x, int) else None


def scan():
    rows = []
    for capdir, gf in livewire.live_connections():
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        me = pressstopjoin.whose_agent(merged)
        if me is None:
            continue
        cap = os.path.basename(capdir)
        starts, askills, periods, moves, landings, stops = [], [], [], [], [], []
        deaths = collections.defaultdict(list)
        for t, d, op, v in merged:
            try:
                if d == "s2c":
                    if op == 0x00A0 and len(v) > 3 and _i(v[2]) == me:
                        if int(v[1]) == 4:
                            starts.append((t, int(v[3])))
                        elif int(v[1]) == 50:
                            askills.append((t, int(v[3])))
                    if op == 0x00A0 and len(v) > 3 and int(v[1]) == 38 and _i(v[3]) == me:
                        landings.append(t)
                    elif op == 0x0035 and len(v) > 3 and _i(v[1]) == me:
                        periods.append((t, f32(v[2]), f32(v[3])))
                    elif op == 0x009F and len(v) > 3 and _i(v[2]) == me:
                        if int(v[1]) == 3:
                            stops.append(t)
                        elif int(v[1]) == 1:
                            landings.append(t)
                    elif op == 0x00A4 and len(v) > 1 and _i(v[1]) == me:
                        landings.append(t)
                    elif (op == 0x00A3 and len(v) > 4 and int(v[1]) in DMG_PROPS
                          and _i(v[3]) == me and _i(v[2]) != me):
                        landings.append(t)
                    elif op == 0x00F1 and len(v) > 2 and (int(v[2]) & 0x10):
                        deaths[int(v[1])].append(t)
                elif op in (0x003D, 0x0047, 0x003E):
                    moves.append((t, op == 0x003E or (op == 0x003D and len(v) > 4 and int(v[4]) != 0)))
            except (TypeError, ValueError, IndexError):
                continue
        landings.sort()
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
                if dj == "s2c" and opj == 0x002A and len(vj) > 1 and _i(vj[1]) == me:
                    break
                if (dj == "s2c" and opj == 0x00A0 and len(vj) > 3 and _i(vj[1]) == 4
                        and _i(vj[2]) == me):
                    sw = tj
                    break
            if sw is None:
                continue
            prev = [s for s in starts if s[0] < t - 1e-6]
            per = [p for p in periods if p[0] <= t]
            if not prev or not per or t - prev[-1][0] > 3.0:
                continue
            p0, T_prev = prev[-1]
            period = per[-1][1]
            before = [m for m in moves if m[0] <= p0]
            moving = before[-1][1] if before else False
            span, last_t = 0.0, p0
            for mt, mv in moves:
                if p0 < mt <= t:
                    if moving:
                        span += mt - last_t
                    moving, last_t = mv, mt
            if moving:
                span += t - last_t
            T_press = _i(v[1]) if len(v) > 1 else None
            ask = [a for a in askills if p0 < a[0] < t]
            p0c = ask[-1][0] if ask else p0
            per0 = [p for p in periods if p[0] <= p0c + 1e-6]
            base0, mod0 = (per0[-1][1], per0[-1][2]) if per0 else (period, 1.0)
            eff = base0 * mod0
            lands = [x for x in landings if p0c < x < sw - 0.002]
            first = lands[0] if lands else None
            st = [x for x in stops if p0c + 0.002 < x <= sw + 0.002 and (first is None or x < first)]
            dd = [x for x in deaths.get(T_prev, []) if p0c < x <= t + 1e-6
                  and (first is None or x < first)]
            rows.append(dict(
                cap=cap, t=round(t, 3), period=round(period, 4), span=round(span, 3),
                s2s=round(sw - p0, 3), p2s=round(sw - t, 3),
                binding=(t - p0) < period - BAND,
                retarget=(T_press is not None and T_press != T_prev),
                eff=round(eff, 4), mod0=round(mod0, 4), askill=bool(ask),
                dt_c=round(t - p0c, 3), s2s_c=round(sw - p0c, 3),
                binding_c=(t - p0c) < eff - BAND,
                landed_at=(None if first is None else round(first - p0c, 3)),
                stop_at=(None if not st else round(st[0] - p0c, 3)),
                death=bool(dd), cancelled=bool(st) or bool(dd)))
    return rows


def outcome(r):
    """WAIT (at start + eff), RESET (at the press, early) or OTHER -- the corrected operands."""
    if abs(r["s2s_c"] - r["eff"]) <= BAND:
        return "WAIT"
    if r["p2s"] <= IMMEDIATE and r["s2s_c"] < r["eff"] - BAND:
        return "RESET"
    return "OTHER"


def two(rows, pred, name):
    a = sum(1 for r in rows if pred(r) and outcome(r) == "RESET")
    b = sum(1 for r in rows if pred(r) and outcome(r) == "WAIT")
    c = sum(1 for r in rows if not pred(r) and outcome(r) == "RESET")
    d = sum(1 for r in rows if not pred(r) and outcome(r) == "WAIT")
    return (f"  {name:50s} TRUE: RESET {a:3d} WAIT {b:3d} | FALSE: RESET {c:3d} WAIT {d:3d}"
            f" | wrong {b + c}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", action="store_true", help="every binding press, classified")
    a = ap.parse_args()
    rows = scan()
    b = [r for r in rows if r["binding"]]
    print(f"answered presses with a previous own start < 3 s: {len(rows)}; binding on the raw "
          f"period {len(b)} (moved {sum(r['span'] > 0.1 for r in b)}, unmoved "
          f"{sum(r['span'] <= 0.1 for r in b)})")
    for name, sub in (("MOVED & binding", [r for r in b if r["span"] > 0.1]),
                      ("UNMOVED & binding", [r for r in b if r["span"] <= 0.1])):
        cb = [r for r in sub if r["binding_c"]]
        sc = [r for r in cb if outcome(r) != "OTHER"]
        print(f"\n#### {name}: {len(sub)}; binding on the corrected period {len(cb)}; scored "
              f"{len(sc)}: {dict(collections.Counter(outcome(r) for r in sc))}; OTHER "
              f"{[(r['cap'], r['t']) for r in cb if outcome(r) == 'OTHER']}")
        print(two(sc, lambda r: r["retarget"], "OURS: reset iff retarget"))
        print(two(sc, lambda r: r["cancelled"], "reset iff CANCELLED in the windup ([3] or death)"))
        print(two(sc, lambda r: r["stop_at"] is not None, "  ... [3, me, 0] in the windup only"))
        print(two(sc, lambda r: r["death"], "  ... target death in the windup only"))
        disc = [r for r in sc if r["retarget"] != r["cancelled"]]
        print(f"  DISCRIMINATING (ours and CANCELLED disagree): {len(disc)}")
        for r in disc:
            print(f"    {r['cap']} {r['t']:8.2f} retarget {int(r['retarget'])} cancelled "
                  f"{int(r['cancelled'])} (stop@{r['stop_at']} death {int(r['death'])}) "
                  f"landed@{r['landed_at']} -> {outcome(r)}: s2s {r['s2s_c']} eff {r['eff']} "
                  f"press->swing {r['p2s']}")
        rc = [r for r in sc if r["cancelled"] and r["stop_at"] is not None]
        fits = sum(1 for r in rc if abs(r["s2s_c"] - (r["stop_at"] + r["eff"])) <= BAND)
        print(f"  RIVAL 'the cancel restarts the clock' (start = [3] + eff), {len(rc)} rows: "
              f"fits {fits}")
    if a.rows:
        print("\n#### every binding press")
        for r in b:
            print(f"  {r['cap']} {r['t']:8.2f} {outcome(r):5s} span {r['span']} ret "
                  f"{int(r['retarget'])} canc {int(r['cancelled'])} landed@{r['landed_at']} "
                  f"stop@{r['stop_at']} ask {int(r['askill'])} mod {r['mod0']} eff {r['eff']} "
                  f"dt {r['dt_c']} s2s {r['s2s_c']} p2s {r['p2s']}")


if __name__ == "__main__":
    main()
