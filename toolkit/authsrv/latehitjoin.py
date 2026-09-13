"""latehitjoin.py -- does a melee swing land on a target that MOVED during
the windup, on retail?  SLICE-C3 / studies/slice/FINDINGS.md F21.

    python toolkit/authsrv/latehitjoin.py            # the census over the live corpus
    python toolkit/authsrv/latehitjoin.py --rows     # one line per swing at the
                                                     # observer with a report inside

THE QUESTION. Ours judged reach TWICE: at the start of a swing (the halt
disc for a hostile, the press-time reach for the player) and again at the
landing -- the enemy loop dropped an armed swing the moment the player left
enemy_reach() or the chase re-issued, attack_tick dropped the player's swing
in flight past attack_reach(), and SLICE-C1 released an attack skill's strike
past reach.  The owner: "enemies don't attack you if you just constantly
kite them."  Whether retail's landing has a reach term was NOT MEASURED
until this scan.

WHAT IS JOINED.  Every attack_started [4, A, T, 0] (0x00A0) and every
attack-skill animation [50, A, T, skill] on every live connection, its
OUTCOME -- the first of, within 3 s: damage 0x00A3 [16|17, T, A, f] (hit);
the attack-fail word [38, T, A, reason] (fail); the swinger's close ([1, A, 0]
for a swing, [46, A, 0] for a skill) with no damage in its batch
(close-nodmg); the swinger's stop ([3] / [49]) (stopped); a fresh start by
A (restart); nothing (none) -- and whether the TARGET MOVED inside the
window: for the observing player, c2s 0x003D/0x003E reports inside it (and
the displacement from a report <= 0.5 s before the start to the last report
inside, when both exist); for an NPC, s2c 0x0029/0x002A/0x0025 naming it.

MEASURED 2026-09-12 over 20 live captures: swings AT the observer during
which the observer moved -- 7 of 7 hit, four of them with an anchored
report showing 81-288 u of displacement at the last report before the
landing (0.3-0.5 s of running short of the hit itself); the observer's own
swings on a target that moved -- 33 hit, 1 stopped (a retarget); attack-
skill strikes on a moving target -- 11 of 11 hit; NPC-on-NPC -- 51 hit
against 21 stopped (the chases' own retargets).  The corpus carries ONE
attack-fail word in 1,332 starts (SKILLS-BL).  So retail judges reach at the
START and never at the landing; the three sites above keep the start gates
and lose the landing gates (LATE_HIT; --no-late-hit reverts).  Read-only;
standard library only; live captures only (livewire.live_connections).
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

PINT, PINT_T, PFLOAT_T = 0x009F, 0x00A0, 0x00A3
PROP_MAX_ENERGY = 41            # self-scoped: adrenjoin.whose_agent's rule
REASONS = {0: "block", 1: "dodge", 2: "fail", 3: "miss", 4: "obstructed",
           5: "stray"}
WINDOW = 3.0                    # s: an outcome later than this is "none"
ANCHOR = 0.5                    # s: a report this fresh before the start anchors
BATCH = 0.06                    # s: damage rides the close's own batch


def whose_agent(merged):
    """The observing player's agent id, or None -- NO FALLBACK (adrenjoin)."""
    seen = {int(v[2]) for _t, d, op, v in merged
            if d == "s2c" and op == PINT and len(v) > 2
            and int(v[1]) == PROP_MAX_ENERGY}
    return seen.pop() if len(seen) == 1 else None


def outcome_of(merged, i, t, A, T, kind):
    """(outcome, t_out, reason) for the start at index i. kind: swing|skill."""
    close_prop = 1 if kind == "swing" else 46
    stop_prop = 3 if kind == "swing" else 49
    for j in range(i + 1, len(merged)):
        tj, dj, opj, vj = merged[j]
        if tj - t > WINDOW:
            break
        if dj != "s2c":
            continue
        if opj == PFLOAT_T and len(vj) > 3 and int(vj[1]) in (16, 17) \
                and int(vj[2]) == T and int(vj[3]) == A:
            return "hit", tj, None
        if opj == PINT_T and len(vj) > 4 and int(vj[1]) == 38 \
                and int(vj[2]) == T and int(vj[3]) == A:
            return "fail", tj, REASONS.get(int(vj[4]), vj[4])
        if opj == PINT and len(vj) > 2 and int(vj[2]) == A:
            p = int(vj[1])
            if p == close_prop:
                hit = any(dk == "s2c" and opk == PFLOAT_T and len(vk) > 3
                          and int(vk[1]) in (16, 17) and int(vk[2]) == T
                          and int(vk[3]) == A
                          for tk, dk, opk, vk in merged[j:j + 40]
                          if tk - tj <= BATCH)
                return ("hit" if hit else "close-nodmg"), tj, None
            if p == stop_prop:
                return "stopped", tj, None
        if kind == "skill" and opj == 0x00E2 and len(vj) > 1 \
                and isinstance(vj[1], int) and vj[1] == A:
            return "cancelled", tj, None
        if kind == "swing" and opj == PINT_T and len(vj) > 3 \
                and int(vj[1]) == 4 and int(vj[2]) == A:
            return "restart", tj, None
    return "none", None, None


def scan():
    """-> (cells, rows): cells Counter[(who, moved, outcome)], rows the
    swings at the observer that have a report inside the windup."""
    cells = collections.Counter()
    rows = []
    for capdir, gf in livewire.live_connections():
        stamp = os.path.basename(capdir)
        conn, merged, _ok = livewire.decode_conn(capdir, gf)
        me = whose_agent(merged)
        if me is None:
            continue
        reports = [(t, (float(v[1][0]), float(v[1][1])),
                    "stop" if op == 0x0047 else "move")
                   for t, d, op, v in merged
                   if d == "c2s" and op in (0x003D, 0x0047) and len(v) > 1
                   and isinstance(v[1], (tuple, list))]
        for i, (t, d, op, v) in enumerate(merged):
            if d != "s2c" or op != PINT_T or len(v) < 4:
                continue
            p = int(v[1])
            if p not in (4, 50):
                continue
            kind = "swing" if p == 4 else "skill"
            A, T = int(v[2]), int(v[3])
            out, t_out, reason = outcome_of(merged, i, t, A, T, kind)
            t_end = t_out if t_out is not None else t + 1.5
            if T == me:
                inside = [(tp, pt, k) for tp, pt, k in reports
                          if t < tp <= t_end]
                moved = any(k == "move" for _tp, _pt, k in inside)
                who = "target=me"
                if kind == "swing" and inside:
                    anchor = [(tp, pt) for tp, pt, _k in reports
                              if t - ANCHOR <= tp <= t]
                    disp = None
                    if anchor:
                        ax, ay = anchor[-1][1]
                        disp = max(math.hypot(pt[0] - ax, pt[1] - ay)
                                   for _tp, pt, _k in inside)
                    rows.append(dict(stamp=stamp, t=round(t, 3), A=A, out=out,
                                     dur=(None if t_out is None
                                          else round(t_out - t, 3)),
                                     disp=(None if disp is None
                                           else round(disp, 1)),
                                     reports=[(round(tp - t, 3), k)
                                              for tp, _pt, k in inside]))
            else:
                moved = any(dj == "s2c" and opj in (0x0029, 0x002A, 0x0025)
                            and len(vj) > 1 and isinstance(vj[1], int)
                            and vj[1] == T and t < tj <= t_end
                            for tj, dj, opj, vj in merged[i + 1:i + 400])
                who = "attacker=me" if A == me else "npc-vs-npc"
            cells[(kind, who, "moved" if moved else "still", out)] += 1
    return cells, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", action="store_true",
                    help="one line per swing at the observer with a report "
                         "inside the windup")
    args = ap.parse_args(argv)
    cells, rows = scan()
    print(f"{'kind':6s} {'who':12s} {'target':6s} {'outcome':12s} n")
    for k in sorted(cells, key=str):
        print(f"{k[0]:6s} {k[1]:12s} {k[2]:6s} {k[3]:12s} {cells[k]}")
    if args.rows:
        print("\nswings at the observer with a report inside the windup "
              "(disp: from a report <= 0.5 s before the start to the last "
              "report inside):")
        for r in sorted(rows, key=lambda r: (r["disp"] is None, r["disp"] or 0)):
            print(f"  {r['stamp']} t={r['t']:8.3f} A={r['A']:4d} "
                  f"{r['out']:12s} dur={r['dur']} disp={r['disp']} "
                  f"reports={r['reports']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
