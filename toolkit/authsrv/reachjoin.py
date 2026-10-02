"""reachjoin.py -- retail's press-time reach: which distance, measured how, decides swing vs follow?

    python toolkit/authsrv/reachjoin.py              # the census over the live corpus
    python toolkit/authsrv/reachjoin.py --rows       # every joined press near the boundary
    python toolkit/authsrv/reachjoin.py --lag 0.257  # the server-copy lag used (default)

THE QUESTION (MOVECODE-1z-ds.7, studies/movecode/FINDINGS.md). ANIMREF-RE 38.4 bracketed
the melee reach from DR-free rows only -- Sword (82.7, 205.5], Daggers (109.7, 146.3] -- and
"no Sword press ever tests 144". Our server judges a keyboard-walk press on the reckoned
BODY since 1z-ds.7; 38.3 found retail's server copy of a walking player trailing the body
by ~0.257 s. Which operand does retail's decision follow, and where is its edge?

THE JOIN, per c2s 0x0026 on every live connection (livewire.decode_conn, both directions on
one clock; the observer by the self-scoped property 41), answered within ANSWER s:
  SWING  -- the observer's own attack_started [4, me, T], no follow of mine ahead of it;
  FOLLOW -- my own 0x002A naming T first. Its dest IS T's server position (exact).
The TARGET at the press: a FOLLOW's own dest; otherwise the nearest 0x002A by any OTHER
mover naming T (its dest = T's server position then), a 0x0020 spawn, or a 0x002C
placement, within TARGET_WINDOW s, with an error bound of |dt| x 288 u/s when T itself
moved in the 3 s around it (0 when it did not). The PLAYER, four operands:
  rep -- the last c2s 0x003D / 0x0047 position, bare;
  est -- that report advanced along its own heading at the family rate to the press
         (our server's operand since 1z-ds.7; 1z-dr measured it p50 4 u to 2 s);
  lag -- the reported polyline at t - LAG: the report in force then, advanced to then
         (animref 38.3's model of retail's server copy);
  srv -- the nearest 0x002A by a hostile naming ME (its dest = the server's copy of me),
         within 0.3 s, when one exists.
A row whose player had a SERVER order between the last report and the press (my own 0x002A
or 0x002C) is a body on a server leg: `leg` -- its rep/est/lag do not describe it.

WHAT IS PRINTED: per weapon class (melee / ranged by the observer's own 0x00A4 launches),
for each operand, the swings' and follows' distance ranges in the tiers that can carry a
claim (target error <= TIGHT u; the player parked on a 0x0047 or walking on a report no
older than FRESH s; no leg), and the cut that misclassifies fewest. Read-only; standard
library only; refuses non-live captures by construction (livewire.live_connections).

MEASURED 2026-10-02 over the live corpus: 270 answered presses (147 swings, 62 with a
target fix once a never-moved target's 0x0020 spawn counts at any age; 123 follows), 100
claim rows. 1.33 s weapons (sword / axe / daggers), 36 rows: on `est` swings 22.8-119.6 u,
follows 135.8 u and up -- the cut at 119.6 misclassifies 0; `rep` misclassifies 2 (stale
reports of bodies walking away), `lag` at 0.257 s 3, and the lag sweep separates cleanly
only at 0-0.10 s. Retail decides on the BODY, and its melee press reach is (119.6, 135.8]
centre to centre, every radius 12.0 -- not the wiki's 144. The edges: 20260917T224104
t=442.14, a swing from a 0x0047-parked body to a never-moved target at 119.6; and
20260817T231139 t=366.86, a follow at est 135.8 (report 33 ms old) whose target was
itself walking (+-12 u in the 41 ms to the answer). Under a ~40 ms look-ahead the
walking-toward follow at 146.3 (20260819T132414 t=234.12) bounds it at ~135 too.
"""
import argparse
import collections
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import livewire  # noqa: E402
import pressstopjoin  # noqa: E402

ANSWER = 0.25          # s: the swing or the follow answering the press
TARGET_WINDOW = 0.6    # s: the nearest target fix
TIGHT = 30.0           # u: the target-error bar a claim row must meet
FRESH = 1.0            # s: a walking row's report age bar
RUN = 288.0
FR = {1: 1.0, 2: 1.0, 3: 1.0, 4: 0.66, 5: 0.66, 6: 0.66, 7: 0.75, 8: 0.75}


def _poly(reports, tq):
    """The reported polyline at tq: the report in force, advanced along its heading."""
    prev = None
    for r in reports:
        if r[0] <= tq:
            prev = r
        else:
            break
    if prev is None:
        return None
    rt, op, v = prev
    p = (float(v[1][0]), float(v[1][1]))
    if op != 0x003D or len(v) < 5 or not int(v[4]):
        return p
    h = v[3]
    hm = math.hypot(float(h[0]), float(h[1]))
    if hm < 1.0:
        return p
    d = RUN * FR.get(int(v[4]), 1.0) * min(tq - rt, 2.0)
    return (p[0] + h[0] / hm * d, p[1] + h[1] / hm * d)


def scan(lag):
    rows, weapons = [], {}
    for capdir, gf in livewire.live_connections():
        conn, merged, _ok = livewire.decode_conn(capdir, gf)
        me = pressstopjoin.whose_agent(merged)
        if me is None:
            continue
        key = (os.path.basename(capdir), conn)
        ranged = False
        fixes = collections.defaultdict(list)   # agent -> [(t, (x, y), src, mover)]
        radius = {}                              # agent -> its 0x0020 collision radius
        periods = []                             # (t, my 0x0035 attack period)
        moved = collections.defaultdict(list)   # agent as a mover -> [t]
        orders_me = []                           # my own server orders (0x002A / 0x002C)
        for t, d, op, v in merged:
            if d != "s2c":
                continue
            try:
                if op == 0x0020 and len(v) > 5:
                    fixes[int(v[1])].append((t, (float(v[5][0]), float(v[5][1])), "spawn", None))
                    if len(v) > 11:
                        # slot 11 carries the radius as a float's bits (ours: 0x41400000 = 12.0)
                        radius[int(v[1])] = struct.unpack("<f", struct.pack("<I", int(v[11]) & 0xFFFFFFFF))[0]
                elif op == 0x0035 and len(v) > 2 and int(v[1]) == me:
                    periods.append((t, struct.unpack("<f", struct.pack("<I", int(v[2]) & 0xFFFFFFFF))[0]))
                elif op == 0x002C and len(v) > 2:
                    a = int(v[1])
                    fixes[a].append((t, (float(v[2][0]), float(v[2][1])), "placed", None))
                    moved[a].append(t)
                    if a == me:
                        orders_me.append(t)
                elif op == 0x002A and len(v) > 5:
                    a = int(v[1])
                    fixes[int(v[5])].append((t, (float(v[2][0]), float(v[2][1])), "followed", a))
                    moved[a].append(t)
                    if a == me:
                        orders_me.append(t)
                elif op in (0x0029, 0x0028) and len(v) > 1:
                    moved[int(v[1])].append(t)
                elif op == 0x00A4 and len(v) > 1 and int(v[1]) == me:
                    ranged = True
            except (TypeError, ValueError, IndexError):
                continue
        weapons[key] = "ranged" if ranged else "melee"
        reports = [(t, op, v) for t, d, op, v in merged
                   if d == "c2s" and op in (0x003D, 0x0047) and len(v) > 1]
        for i, (t, d, op, v) in enumerate(merged):
            if d != "c2s" or op != 0x0026 or len(v) < 2:
                continue
            T = int(v[1])
            if T in (0, me):
                continue
            ans = None
            for j in range(i + 1, len(merged)):
                tj, dj, opj, vj = merged[j]
                if tj - t > ANSWER:
                    break
                if dj != "s2c":
                    continue
                if opj == 0x002A and len(vj) > 5 and int(vj[1]) == me:
                    ans = ("FOLLOW", tj, (float(vj[2][0]), float(vj[2][1])))
                    break
                if (opj == 0x00A0 and len(vj) > 3 and int(vj[1]) == 4
                        and int(vj[2]) == me):
                    ans = ("SWING", tj, None)
                    break
            if ans is None:
                continue
            if ans[0] == "FOLLOW":
                tpos, terr, tsrc = ans[2], 0.0, "answer"
            else:
                cand = [f for f in fixes[T] if abs(f[0] - t) <= TARGET_WINDOW and f[3] != me]
                spawn = [f for f in fixes[T] if f[2] == "spawn" and f[0] <= t]
                if not cand and spawn and not any(m <= t for m in moved[T]):
                    # NEVER MOVED since its 0x0020: the spawn point is exact however old
                    # (animref 38.4's DR-free target rows).
                    cand = [spawn[-1]]
                    tpos, terr, tsrc = spawn[-1][1], 0.0, "spawn-unmoved"
                elif not cand:
                    rows.append(dict(key=key, t=t, ans="SWING", tsrc=None))
                    continue
                else:
                    f = min(cand, key=lambda f: abs(f[0] - t))
                    lo, hi = min(f[0], t), max(f[0], t)
                    moving = any(lo - 3.0 <= m <= hi for m in moved[T])
                    tpos, terr, tsrc = f[1], (abs(f[0] - t) * RUN if moving else 0.0), f[2]
            prev = [r for r in reports if r[0] <= t]
            if not prev:
                continue
            rt, rop, rv = prev[-1]
            walking = rop == 0x003D and len(rv) > 4 and bool(int(rv[4]))
            leg = any(rt < o <= t for o in orders_me)
            ops = {"rep": (float(rv[1][0]), float(rv[1][1])),
                   "est": _poly(reports, t), "lag": _poly(reports, t - lag)}
            sc = [f for f in fixes[me] if abs(f[0] - t) <= 0.3 and f[3] not in (None, me)]
            ops["srv"] = min(sc, key=lambda f: abs(f[0] - t))[1] if sc else None
            dist = {k: (None if p is None else
                        round(math.hypot(p[0] - tpos[0], p[1] - tpos[1]), 1))
                    for k, p in ops.items()}
            toward = None
            if walking:
                h = rv[3]
                hm = math.hypot(float(h[0]), float(h[1]))
                vx, vy = tpos[0] - ops["est"][0], tpos[1] - ops["est"][1]
                vm = math.hypot(vx, vy)
                if hm > 1.0 and vm > 1.0:
                    toward = round((h[0] * vx + h[1] * vy) / (hm * vm), 2)
            per = [p for pt, p in periods if pt <= t]
            rr = (radius.get(T), radius.get(me))
            edge = {("edge_" + k): (None if d is None or None in rr else round(d - rr[0] - rr[1], 1))
                    for k, d in dist.items()}
            rows.append(dict(key=key, t=round(t, 3), ans=ans[0], T=T, tsrc=tsrc,
                             terr=round(terr, 1), age=round(t - rt, 3), walking=walking,
                             parked=(rop == 0x0047), leg=leg, toward=toward,
                             period=(round(per[-1], 3) if per else None),
                             r_t=rr[0], r_me=rr[1], **dist, **edge))
    return rows, weapons


def tiers(rows):
    ok = [r for r in rows if r.get("tsrc") and r["terr"] <= TIGHT and not r["leg"]]
    return (("parked on a 0x0047", [r for r in ok if r["parked"]]),
            (f"walking, report <= {FRESH:g} s", [r for r in ok if r["walking"] and r["age"] <= FRESH]))


def separation(rs, field):
    sw = sorted(r[field] for r in rs if r["ans"] == "SWING" and r.get(field) is not None)
    fo = sorted(r[field] for r in rs if r["ans"] == "FOLLOW" and r.get(field) is not None)
    if not sw or not fo:
        return sw, fo, None
    best = None
    for thr in sorted(set(sw + fo)):
        bad = sum(x > thr for x in sw) + sum(x <= thr for x in fo)
        if best is None or bad < best[0]:
            best = (bad, thr)
    return sw, fo, best


# The weapon is the 0x0035 attack period in force at the press (WIKI, GWW "Attack speed":
# 1.33 sword / axe / daggers, 1.5 scythe / spear, 1.75 hammer / wand / staff, 2.0+ bows).
# A connection's own 0x00A4 launches only say it held a ranged weapon at SOME point --
# 20260919T103604 swaps sets, and its 1.5 s rows are a spear.
GROUPS = (("1.33 s (sword/axe/daggers)", lambda p: p is not None and abs(p - 1.33) < 0.01),
          ("1.5 s (scythe/spear)", lambda p: p is not None and abs(p - 1.5) < 0.01),
          ("1.75 s (hammer/wand/staff)", lambda p: p is not None and abs(p - 1.75) < 0.01),
          ("other / unknown period", lambda p: p is None or min(abs(p - x) for x in (1.33, 1.5, 1.75)) >= 0.01))


def claim(rows):
    """The rows that can carry a claim: a target fix within TIGHT, no server leg, and the
    player parked on a 0x0047 or walking on a report no older than FRESH."""
    return [r for r in rows if r.get("tsrc") and r["terr"] <= TIGHT and not r["leg"]
            and (r["parked"] or (r["walking"] and r["age"] <= FRESH))]


def report(rows, weapons, lag):
    out = [f"server-copy lag {lag:g} s; target error bar {TIGHT:g} u; walking report <= {FRESH:g} s"]
    n_sw = sum(r["ans"] == "SWING" for r in rows)
    n_sw_fix = sum(r["ans"] == "SWING" and bool(r.get("tsrc")) for r in rows)
    out.append(f"answered presses {len(rows)}: swings {n_sw} (with a target fix {n_sw_fix}), "
               f"follows {sum(r['ans'] == 'FOLLOW' for r in rows)}; claim rows {len(claim(rows))}")
    for gname, pred in GROUPS:
        sub = [r for r in claim(rows) if pred(r.get("period"))]
        if not sub:
            continue
        out.append(f"  {gname}: {len(sub)} claim rows")
        for f in ("est", "rep", "lag", "srv"):
            sw, fo, best = separation(sub, f)
            line = (f"    {f}: swings n={len(sw)}" + (f" [{sw[0]:.1f}..{sw[-1]:.1f}]" if sw else "")
                    + f", follows n={len(fo)}" + (f" [{fo[0]:.1f}..{fo[-1]:.1f}]" if fo else ""))
            if best is not None:
                line += f" -- best cut {best[1]:.1f} misclassifies {best[0]}"
            out.append(line)
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--lag", type=float, default=0.257)
    ap.add_argument("--rows", action="store_true", help="the claim rows within 60..260 u")
    ap.add_argument("--sweep", action="store_true", help="the lag operand's separation, 0..0.6 s")
    a = ap.parse_args(argv)
    rows, weapons = scan(a.lag)
    print(report(rows, weapons, a.lag))
    if a.rows:
        print("claim rows with est or rep within 60..260 u:")
        for r in sorted(claim(rows), key=lambda r: (r.get("period") or 0, r["est"] or 0)):
            if any(r.get(k) is not None and 60 <= r[k] <= 260 for k in ("est", "rep")):
                how = "parked" if r["parked"] else f"walking, toward {r['toward']}"
                print(f"  per {r.get('period')} {r['key'][0]} {r['t']:8.2f} {r['ans']:6s} "
                      f"est {r['est']} rep {r['rep']} lag {r['lag']} target {r['tsrc']} "
                      f"+-{r['terr']} age {r['age']} ({how})")
    if a.sweep:
        print("lag sweep over the 1.33 s claim rows, misclassified at the best cut:")
        for L in [x / 20 for x in range(0, 13)]:
            rows_l, _w = scan(L)
            sub = [r for r in claim(rows_l) if GROUPS[0][1](r.get("period"))]
            sw, fo, best = separation(sub, "lag")
            print(f"  lag {L:.2f} s: n {len(sw)}+{len(fo)}, "
                  + (f"cut {best[1]:.1f} misclassifies {best[0]}" if best else "cannot separate"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
