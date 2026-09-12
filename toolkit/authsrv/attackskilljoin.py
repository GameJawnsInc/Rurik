"""attackskilljoin.py -- what answers an ATTACK-SKILL press (c2s 0x0027) on retail.

    python toolkit/authsrv/attackskilljoin.py            # the census over the live corpus
    python toolkit/authsrv/attackskilljoin.py --dump 20260817T231139:717.315
                                                         # the wire around one press

THE QUESTION (SLICE-C2, studies/slice/FINDINGS.md F20): a press of an attack
skill with the target OUT OF REACH -- what does ArenaNet's server send at the
press, what while the body walks in, what at arrival, and what cancels it?
The ordinary attack's contract (ANIMREF-RE 38: a 0x002A follow to the target's
own point, re-pathed every 0.5 s) was measured on 267 c2s 0x0026 presses; the
attack-skill press is a different opcode and had never been joined.

WHAT IS JOINED, per press, on one clock (livewire.decode_conn, both
directions; the observer by the self-scoped property 41, adrenjoin's rule):
E4 [me, skill, copy] within 6 s (accepted) or E2 (refused); the 0x002A follows
naming the target before the animation; the property-50 animation
[50, me, target, skill]; E5; and the E2 after an accepted E4 (a cancel). A
FREE press is one whose E4 lands within 0.1 s -- a queued press (caster busy)
gets its E4 at the previous cast's E3 and says nothing about the press-time
contract. The out-of-reach cell is the free presses with a follow in the
press instant (within 0.15 s); the in-reach cell the free presses without.

MEASURED 2026-09-12 over 20 live captures: 94 presses, 80 accepted, 14
refused (the ANIMREF-RE 19 charge gate); 51 free, 11 with a follow at the
press. In the follow cell the animation lands 0.23-3.4 s after the press
(p50 0.687) and 0.085-3.4 s after the last follow -- the arrival -- and the
debit rides the same instant; in the in-reach cell the animation's p50 is
0.307 s (n=38), a warrior with a live sword chain, which F20 records and does
not explain. Read-only; standard library only; refuses non-live captures by
construction (livewire.live_connections).
"""
import argparse
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import livewire  # noqa: E402

PRESS = 0x0027
E4, E5, E3, E2 = 0x00E4, 0x00E5, 0x00E3, 0x00E2
DEST = 0x002A
PINT, PINT_T = 0x009F, 0x00A0
PROP_MAX_ENERGY = 41            # self-scoped: adrenjoin.whose_agent's rule
GV_ATTACK_SKILL_ACTIVATED = 50
FREE_WINDOW = 0.1               # s: an E4 later than this is a queued press
FOLLOW_AT_PRESS = 0.15          # s: a follow inside this rides the press batch
MOVES = {0x003D: "WASD", 0x003E: "CLICK", 0x0047: "STOP"}
NAMES = {E4: "E4", E5: "E5", E3: "E3", E2: "E2", DEST: "DEST",
         0x0029: "WAYPT", 0x0028: "STOP", 0x002C: "POS", 0x00D2: "ADRSPEND",
         0x00CF: "ADRGAIN", 0x00D0: "ADRCLEAR", 0x003D: "c:WASD",
         0x003E: "c:CLICK", 0x0047: "c:STOPRPT", 0x0026: "c:ATTACK",
         0x0027: "c:ATKSKILL", 0x0046: "c:USESKILL"}


def whose_agent(merged):
    """The observing player's agent id, or None -- NO FALLBACK (adrenjoin)."""
    seen = {int(v[2]) for _t, d, op, v in merged
            if d == "s2c" and op == PINT and len(v) > 2
            and int(v[1]) == PROP_MAX_ENERGY}
    return seen.pop() if len(seen) == 1 else None


def join_press(merged, i, me):
    """One press's answers: dict, or None when the press was never answered."""
    t, _d, _op, v = merged[i]
    skill, copy, target = int(v[1]), int(v[2]), int(v[3])
    last_move = None
    for j in range(i - 1, -1, -1):
        tj, dj, opj, _vj = merged[j]
        if dj == "c2s" and opj in MOVES:
            last_move = (MOVES[opj], round(t - tj, 3))
            break
        if t - tj > 30:
            break
    e4 = e2 = a50 = e5 = cancel = None
    follows = []
    for j in range(i + 1, len(merged)):
        tj, dj, opj, vj = merged[j]
        if tj - t > 6.0 or (a50 is not None and tj - t > a50 + 2.5):
            break
        if dj != "s2c":
            continue
        mine = (len(vj) > 1 and isinstance(vj[1], int)
                and int(vj[1]) == me)
        if opj == E4 and mine and int(vj[2]) == skill and e4 is None:
            e4 = tj - t
        elif opj == E2 and mine and int(vj[2]) == skill:
            if e4 is None and e2 is None:
                e2 = tj - t
            elif e4 is not None and cancel is None:
                cancel = tj - t
        elif opj == DEST and mine and len(vj) > 5 and int(vj[5]) == target \
                and a50 is None:
            follows.append(round(tj - t, 3))
        elif opj == PINT_T and int(vj[1]) == GV_ATTACK_SKILL_ACTIVATED \
                and int(vj[2]) == me and a50 is None:
            a50 = tj - t
        elif opj == E5 and mine and int(vj[2]) == skill and e4 is not None \
                and e5 is None:
            e5 = tj - t
    return dict(t=round(t, 3), skill=skill, copy=copy, target=target,
                last=last_move, e4=e4, e2=e2, follows=follows, a50=a50,
                e5=e5, cancel=cancel)


def scan():
    """[(stamp, conn, row)] for every c2s 0x0027 on every live connection."""
    rows = []
    for capdir, gf in livewire.live_connections():
        conn, merged, _ok = livewire.decode_conn(capdir, gf)
        me = whose_agent(merged)
        if me is None:
            continue
        stamp = os.path.basename(capdir)
        for i, (_t, d, op, _v) in enumerate(merged):
            if d == "c2s" and op == PRESS:
                rows.append((stamp, conn, join_press(merged, i, me)))
    return rows


def _q(xs):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return "n=0"
    return (f"n={len(xs)} min {xs[0]:.3f} p50 {statistics.median(xs):.3f} "
            f"max {xs[-1]:.3f}")


def census(rows):
    acc = [r for _s, _c, r in rows if r["e4"] is not None]
    ref = [r for _s, _c, r in rows if r["e2"] is not None and r["e4"] is None]
    free = [r for r in acc if r["e4"] <= FREE_WINDOW]
    follow = [r for r in free if r["follows"] and r["follows"][0] <= FOLLOW_AT_PRESS]
    reach = [r for r in free if r not in follow]
    print(f"presses {len(rows)}: accepted {len(acc)}, refused {len(ref)}, "
          f"unanswered {len(rows) - len(acc) - len(ref)}")
    print(f"FREE presses (E4 within {FREE_WINDOW} s): {len(free)} -- "
          f"out of reach (a follow at the press): {len(follow)}, "
          f"in reach: {len(reach)}")
    print("  out of reach: animation after the press ",
          _q([r["a50"] for r in follow]))
    print("  out of reach: animation after the LAST follow (the arrival) ",
          _q([r["a50"] - r["follows"][-1] for r in follow if r["a50"]]))
    print("  out of reach: cancelled (E2 after E4) ",
          _q([r["cancel"] for r in follow]))
    print("  in reach    : animation after the press ",
          _q([r["a50"] for r in reach]))
    print("  in reach    : E5 after the press ", _q([r["e5"] for r in reach]))
    print("  in reach    : cancelled ", _q([r["cancel"] for r in reach]))
    print()
    for stamp, _conn, r in rows:
        if r in follow:
            print(f"  {stamp} t={r['t']:8.3f} skill {r['skill']:4d} -> "
                  f"{r['target']:4d} last={r['last']} follows={r['follows']} "
                  f"E4={r['e4']:.3f} anim={r['a50']} cancel={r['cancel']}")


def dump(stamp, t_press, window=3.2):
    """Print the wire around one press: every c2s, and every s2c that touches
    the observer or the target (plus the E-series)."""
    root = livewire.captures_root()
    capdir = os.path.join(root, stamp)
    for gf in livewire.connections(capdir):
        _conn, merged, _ok = livewire.decode_conn(capdir, gf)
        me = whose_agent(merged)
        if me is None:
            continue
        for i, (t, d, op, v) in enumerate(merged):
            if d != "c2s" or op != PRESS or abs(t - t_press) > 0.002:
                continue
            target = int(v[3])
            print(f"===== {stamp} press t={t:.3f} skill {int(v[1])} -> "
                  f"{target} (me={me})")
            for j in range(max(0, i - 6), len(merged)):
                tj, dj, opj, vj = merged[j]
                if tj - t > window:
                    break
                if tj - t < -0.6:
                    continue
                touches = (dj == "c2s" or any(
                    isinstance(x, int) and x in (me, target) for x in vj[1:4]))
                if not touches and opj not in (E4, E5, E3, E2):
                    continue
                print(f"  {tj - t:+7.3f} {dj} {NAMES.get(opj, hex(opj)):>10} "
                      f"{vj[1:]}")
            return
    print(f"no press at t={t_press} in {stamp}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dump", metavar="STAMP:T",
                    help="print the wire around the press at time T (s) in "
                         "capture STAMP")
    args = ap.parse_args(argv)
    if args.dump:
        stamp, t = args.dump.split(":")
        dump(stamp, float(t))
        return 0
    census(scan())
    return 0


if __name__ == "__main__":
    sys.exit(main())
