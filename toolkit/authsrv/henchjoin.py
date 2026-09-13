"""henchjoin.py -- what a retail PARTY BODY does: the henchman sessions in the
live corpus, joined.  SLICE hero arc / studies/slice/FINDINGS.md F28.

    python toolkit/authsrv/henchjoin.py              # the census
    python toolkit/authsrv/henchjoin.py --rows       # every engagement, one line
    python toolkit/authsrv/henchjoin.py --casts      # every party cast, one line

THE QUESTION.  studies/heroes/FINDINGS.md 0 recorded "zero live occurrences
of the party-add family in 22,524 messages" (2026-08-12) and the hero's
behaviour was authored blind: HERO_FOLLOW_STOP = 200 is "ours, unmeasured",
the hero never swings, and hostiles never look at it.  Two later captures --
20260817T231139 (three level-20 henchmen, map 167730) and 20260819T132414
(three level-3 henchmen, map 157087) -- carry 0x01BF PARTY_HENCHMAN_ADD
three times each, and GWW (Henchman, See also) says "heroes and henchmen
share the same AI".  So the party body's contract is OBSERVABLE, and this
reads it.

WHAT IS JOINED, per connection with a henchman body created in it:

  formation  every henchman 0x0029 lead [41, H, (x,y), a, b] while no hostile
             bout is open -- the lead's END against the observer's latest
             c2s 0x003D/0x0047 report (<= 2 s old): the distance, and the
             offset in the observer's frame (along its 0x003D direction).
             Split by whether the observer was moving.
  halt       after each observer stop (0x0047), the henchman's last lead END
             inside the next 3 s against the stop point.
  engage     every party attack_started [4, H, T, 0] / attack-skill [50, H, T,
             skill] that OPENS a bout (no start by H in the previous 3 s): what
             preceded it inside 6 s -- the observer's own start / skill press
             (c2s 0x0027), a hostile start ON the party -- and who T is.
  targets    every hostile start [4, X, T, 0] / [50, X, T, s]: T's class.
  casts      every party [60|50, H, T, skill]: the skill, T's class, and for
             a heal-shaped spell whether damage had landed on T inside 5 s.
  deaths     0x00F1 [H, status] with the dead bit (rising edges), per member.
  hostile    (--hostile, SLICE-H3) every hostile start [4|50, X, T] that OPENS
             X's bout (no start by X in 3 s): is T the NEAREST party body to X
             at that instant (positions sample-and-held from creates, leads,
             destinations and 0x002C; the observer from its own reports), is
             T the last party body to have HIT X inside 10 s, and T's rank by
             distance; then every SWITCH inside a bout (a start naming a
             different T than X's previous one): nearer? the last hitter?
  cadence    the gap between one party 0x0029 and the next by the same body
             while the observer is moving; leads sent while the observer has
             stood > 1 s; and 0x0028 halts per body against its leads.

Read-only; standard library only; live captures only.
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
HENCH_ADD, CREATE, LEAD, DEST, STATUS = 0x01BF, 0x0020, 0x0029, 0x002A, 0x00F1
PROP_MAX_ENERGY = 41
DEAD_BIT = 0x10
BOUT_GAP = 3.0        # s without a start by H closes H's bout
PRE = 6.0             # s of history read before an opening start
FRESH = 2.0           # s: a report older than this does not anchor a lead
HALT_WINDOW = 3.0     # s after a stop in which the last lead counts
HEAL_SHAPED = 5.0     # s: damage on T this recently makes a heal "on hurt"


def whose_agent(merged):
    seen = {int(v[2]) for _t, d, op, v in merged
            if d == "s2c" and op == PINT and len(v) > 2
            and int(v[1]) == PROP_MAX_ENERGY}
    return seen.pop() if len(seen) == 1 else None


def party_of(merged):
    """{agent_id: (profession_byte, level_byte)} for henchmen whose body is
    CREATED in this connection -- a 0x01BF for a body never created is a
    roster row only (20260819T132414 c53419: adds at 126 s, no 0x0020 until
    a different map)."""
    added = {}
    for _t, d, op, v in merged:
        if d == "s2c" and op == HENCH_ADD and len(v) > 5:
            added[int(v[2])] = (int(v[4]), int(v[5]))
    created = {int(v[1]) for _t, d, op, v in merged
               if d == "s2c" and op == CREATE and len(v) > 1}
    return {a: pl for a, pl in added.items() if a in created}


def classify(agent, me, party):
    if agent == me:
        return "player"
    if agent in party:
        return "hench"
    return "other"


def frame_offset(end, pos, direction):
    """(along, across) of end-pos in the frame whose +along is `direction`."""
    dx, dy = end[0] - pos[0], end[1] - pos[1]
    n = math.hypot(direction[0], direction[1])
    if n < 1e-6:
        return None
    ux, uy = direction[0] / n, direction[1] / n
    return dx * ux + dy * uy, -dx * uy + dy * ux


def scan():
    out = dict(formation=[], halt=[], engage=[], targets=collections.Counter(),
               casts=[], deaths=collections.Counter(), conns=[],
               cadence=[], standing_leads=0, moving_leads=0,
               halts=collections.Counter(), leads=collections.Counter())
    for capdir, gf in livewire.live_connections():
        stamp = os.path.basename(capdir)
        conn, merged, _ok = livewire.decode_conn(capdir, gf)
        if not merged:
            continue
        party = party_of(merged)
        if not party:
            continue
        me = whose_agent(merged)
        if me is None:
            continue
        out["conns"].append((stamp, gf, me, party))
        # the observer's track: c2s reports (pos, dir, moving)
        reports = []
        last_dir = None
        for t, d, op, v in merged:
            if d == "c2s" and op == 0x003D and len(v) > 3 \
                    and isinstance(v[1], (tuple, list)):
                last_dir = (float(v[3][0]), float(v[3][1]))
                reports.append((t, (float(v[1][0]), float(v[1][1])),
                                last_dir, True))
            elif d == "c2s" and op == 0x0047 and len(v) > 1 \
                    and isinstance(v[1], (tuple, list)):
                # a stop carries no direction: the frame is the last heading
                reports.append((t, (float(v[1][0]), float(v[1][1])),
                                last_dir, False))
        # starts by anyone, in order, for the bout and trigger logic
        starts = [(t, int(v[2]), int(v[3]), int(v[1]))
                  for t, d, op, v in merged
                  if d == "s2c" and op == PINT_T and len(v) > 3
                  and int(v[1]) in (4, 50)]
        presses = [t for t, d, op, v in merged if d == "c2s" and op == 0x0027]
        damage = [(t, int(v[2]), int(v[3])) for t, d, op, v in merged
                  if d == "s2c" and op == PFLOAT_T and len(v) > 3
                  and int(v[1]) in (16, 17)]
        # bout state per party member: last start time
        last_start = {}
        hostile_bout_until = 0.0
        was_dead = {}
        last_lead = {}
        ri = 0
        for i, (t, d, op, v) in enumerate(merged):
            if d != "s2c":
                continue
            while ri < len(reports) and reports[ri][0] <= t:
                ri += 1
            latest = reports[ri - 1] if ri else None
            if op == 0x0028 and len(v) > 1 and int(v[1]) in party:
                out["halts"][(stamp, int(v[1]))] += 1
            if op == LEAD and len(v) > 2 and int(v[1]) in party \
                    and isinstance(v[2], (tuple, list)):
                if t < hostile_bout_until:
                    continue
                H = int(v[1])
                out["leads"][(stamp, H)] += 1
                if latest is not None and latest[3] \
                        and t - latest[0] <= FRESH:
                    out["moving_leads"] += 1
                    if H in last_lead:
                        out["cadence"].append(t - last_lead[H])
                elif latest is not None and not latest[3] \
                        and t - latest[0] > 1.0:
                    out["standing_leads"] += 1
                last_lead[H] = t
                if latest is None or t - latest[0] > FRESH:
                    continue
                end = (float(v[2][0]), float(v[2][1]))
                dist = math.hypot(end[0] - latest[1][0], end[1] - latest[1][1])
                off = (frame_offset(end, latest[1], latest[2])
                       if latest[2] is not None else None)
                out["formation"].append(dict(
                    stamp=stamp, t=t, H=int(v[1]), dist=dist,
                    moving=latest[3], along=(None if off is None else off[0]),
                    across=(None if off is None else off[1])))
            elif op == STATUS and len(v) > 2 and int(v[1]) in party:
                # a RISING EDGE of the dead bit: the status word re-sends
                # with other bits changing while the body stays dead
                dead = bool(int(v[2]) & DEAD_BIT)
                if dead and not was_dead.get(int(v[1])):
                    out["deaths"][(stamp, int(v[1]))] += 1
                was_dead[int(v[1])] = dead
            elif op == PINT_T and len(v) > 3 and int(v[1]) in (4, 50, 60):
                kind, A, T = int(v[1]), int(v[2]), int(v[3])
                if kind in (4, 50) and classify(A, me, party) == "other":
                    out["targets"][classify(T, me, party)] += 1
                    hostile_bout_until = max(hostile_bout_until, t + BOUT_GAP)
                if A not in party:
                    continue
                if kind in (4, 50):
                    opens = t - last_start.get(A, -1e9) > BOUT_GAP
                    last_start[A] = t
                    if opens:
                        pre_me = [s for s in starts
                                  if s[1] == me and t - PRE <= s[0] < t]
                        pre_press = [p for p in presses
                                     if t - PRE <= p < t]
                        pre_hostile = [s for s in starts
                                       if classify(s[1], me, party) == "other"
                                       and (s[2] in party or s[2] == me)
                                       and t - PRE <= s[0] < t]
                        if pre_me or pre_press:
                            trig = "player-first"
                        elif pre_hostile:
                            trig = "party-hit-first"
                        else:
                            trig = "hench-first"
                        same = any(s[1] == me and s[2] == T for s in pre_me)
                        out["engage"].append(dict(
                            stamp=stamp, t=t, H=A, T=T, kind=kind, trig=trig,
                            player_target_same=same,
                            lead_me=(None if not pre_me else t - pre_me[-1][0]),
                            lead_press=(None if not pre_press
                                        else t - pre_press[-1]),
                            lead_hostile=(None if not pre_hostile
                                          else t - pre_hostile[-1][0])))
                if kind in (50, 60):
                    skill = int(v[4]) if len(v) > 4 else None
                    hurt = any(dt == T and t - HEAL_SHAPED <= td < t
                               for td, dt, _da in damage)
                    out["casts"].append(dict(
                        stamp=stamp, t=t, H=A, T=T, kind=kind, skill=skill,
                        tclass=("self" if T == A
                                else classify(T, me, party)), hurt=hurt))
        # halts: after each observer stop, the party's last lead inside 3 s
        leads = [(t, int(v[1]), (float(v[2][0]), float(v[2][1])))
                 for t, d, op, v in merged
                 if d == "s2c" and op == LEAD and len(v) > 2
                 and int(v[1]) in party and isinstance(v[2], (tuple, list))]
        for t, pos, _dir, moving in reports:
            if moving:
                continue
            for H in party:
                after = [l for l in leads
                         if l[1] == H and t <= l[0] <= t + HALT_WINDOW]
                if after:
                    end = after[-1][2]
                    out["halt"].append(dict(
                        stamp=stamp, t=t, H=H,
                        dist=math.hypot(end[0] - pos[0], end[1] - pos[1]),
                        n=len(after)))
    return out


# Base armour by profession (GWW, Armor rating: Warrior 80, Ranger 70, Monk /
# Elementalist / Mesmer / Necromancer / Ritualist 60, Assassin 70, Paragon 80,
# Dervish 70), the enum order of 0x00A6's field 2 / 0x01BF's profession byte.
BASE_AR = {1: 80, 2: 70, 3: 60, 4: 60, 5: 60, 6: 60, 7: 70, 8: 60, 9: 80, 10: 70}


def hostile_targets():
    """-> (opens, switches): rows for hostile opening starts and in-bout
    retargets, with the distance ranking and the last-hitter test."""
    opens, switches = [], []
    for capdir, gf in livewire.live_connections():
        stamp = os.path.basename(capdir)
        conn, merged, _ok = livewire.decode_conn(capdir, gf)
        if not merged:
            continue
        party = party_of(merged)
        if not party:
            continue
        me = whose_agent(merged)
        if me is None:
            continue
        pos = {}                      # agent -> (x, y), sample-and-hold
        dead = {}
        prof = {a: pl[0] for a, pl in party.items()}
        last_hit = {}                 # hostile -> (t, party attacker)
        last_start = {}               # hostile -> (t, T)
        for t, d, op, v in merged:
            if d == "c2s":
                if op in (0x003D, 0x0047) and len(v) > 1 \
                        and isinstance(v[1], (tuple, list)):
                    pos[me] = (float(v[1][0]), float(v[1][1]))
                continue
            if op == 0x00A6 and len(v) > 2 and int(v[1]) == me:
                prof[me] = int(v[2])
            if op == CREATE and len(v) > 5 and isinstance(v[5], (tuple, list)):
                pos[int(v[1])] = (float(v[5][0]), float(v[5][1]))
            elif op in (LEAD, DEST, 0x002C) and len(v) > 2 \
                    and isinstance(v[2], (tuple, list)):
                pos[int(v[1])] = (float(v[2][0]), float(v[2][1]))
            elif op == STATUS and len(v) > 2:
                dead[int(v[1])] = bool(int(v[2]) & DEAD_BIT)
            elif op == PFLOAT_T and len(v) > 3 and int(v[1]) in (16, 17):
                tgt, atk = int(v[2]), int(v[3])
                if (atk == me or atk in party) and tgt != me and tgt not in party:
                    last_hit[tgt] = (t, atk)
            elif op == PINT_T and len(v) > 3 and int(v[1]) in (4, 50):
                A, T = int(v[2]), int(v[3])
                if A == me or A in party:
                    if T != me and T not in party:
                        # a start on X counts as a hit for the "who is on
                        # me" test even before its damage lands
                        last_hit.setdefault(T, (t, A))
                        if last_hit[T][0] < t:
                            last_hit[T] = (t, A)
                    continue
                if T != me and T not in party:
                    continue
                cands = [c for c in [me] + list(party)
                         if c in pos and not dead.get(c)]
                if A not in pos or T not in pos:
                    continue
                ax, ay = pos[A]
                ranked = sorted(cands, key=lambda c: math.hypot(
                    pos[c][0] - ax, pos[c][1] - ay))
                rank = ranked.index(T) + 1 if T in ranked else None
                dT = math.hypot(pos[T][0] - ax, pos[T][1] - ay)
                d1 = math.hypot(pos[ranked[0]][0] - ax,
                                pos[ranked[0]][1] - ay) if ranked else None
                lh = last_hit.get(A)
                hitter = lh[1] if lh and t - lh[0] <= 10.0 else None
                ars = {c: BASE_AR.get(prof.get(c, 0), 99) for c in ranked}
                soft = [c for c in ranked if ars[c] == min(ars.values())] \
                    if ranked else []
                row = dict(stamp=stamp, t=t, X=A, T=T,
                           tclass=classify(T, me, party), rank=rank,
                           n=len(ranked), dT=dT, d1=d1,
                           hitter=hitter, hit_by_T=(hitter == T),
                           softest=(T in soft), soft_nearest=(bool(soft) and soft[0] == T),
                           soft_n=len(soft), T_prof=prof.get(T))
                prev = last_start.get(A)
                if prev is None or t - prev[0] > BOUT_GAP:
                    opens.append(row)
                elif prev[1] != T:
                    row["prev"] = prev[1]
                    switches.append(row)
                last_start[A] = (t, T)
    return opens, switches


def pct(xs, p):
    if not xs:
        return None
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(p * (len(xs) - 1))))]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rows", action="store_true")
    ap.add_argument("--casts", action="store_true")
    ap.add_argument("--hostile", action="store_true",
                    help="SLICE-H3: how a hostile picks among the party")
    args = ap.parse_args(argv)
    if args.hostile:
        opens, switches = hostile_targets()
        c = collections.Counter((r["tclass"], r["rank"], r["hit_by_T"])
                                for r in opens)
        print("HOSTILE OPENING STARTS -- T's class, T's rank by distance "
              "among the live party (1 = nearest), T is the last party body "
              "to hit X (10 s):")
        for k in sorted(c, key=str):
            print(f"  {k[0]:7s} rank={k[1]!s:5s} last-hitter={k[2]!s:5s} n={c[k]}")
        near = [r for r in opens if r["rank"] == 1]
        print(f"  nearest: {len(near)} of {len(opens)}; last-hitter: "
              f"{sum(1 for r in opens if r['hit_by_T'])} of {len(opens)}; "
              f"either: {sum(1 for r in opens if r['rank'] == 1 or r['hit_by_T'])}")
        print(f"  ARMOUR: T in the lowest-base-armour set of the live party: "
              f"{sum(1 for r in opens if r['softest'])} of {len(opens)}; T the "
              f"NEAREST of that set: {sum(1 for r in opens if r['soft_nearest'])}; "
              f"set size p50 {pct([r['soft_n'] for r in opens], .5)!r}")
        cp = collections.Counter((r["T_prof"], r["softest"]) for r in opens)
        print("  by T's profession byte:", dict(sorted(cp.items(), key=str)))
        gaps = [r["dT"] - r["d1"] for r in opens if r["rank"] != 1]
        print(f"  when NOT nearest, T was further than the nearest by "
              f"p10/p50/p90 = {pct(gaps, .1)!r} {pct(gaps, .5)!r} "
              f"{pct(gaps, .9)!r}")
        c2 = collections.Counter((r["rank"] == 1, r["hit_by_T"]) for r in switches)
        print(f"SWITCHES inside a bout: n={len(switches)}")
        for k in sorted(c2, key=str):
            print(f"  new T nearest={k[0]!s:5s} new T last-hitter={k[1]!s:5s} n={c2[k]}")
        if args.rows:
            for r in opens:
                print(f"    open   {r['stamp']} t={r['t']:8.3f} X={r['X']:4d} "
                      f"T={r['T']:4d} {r['tclass']:6s} rank={r['rank']}/{r['n']} "
                      f"dT={r['dT']:.0f} d1={r['d1']:.0f} hitter={r['hitter']}")
            for r in switches:
                print(f"    switch {r['stamp']} t={r['t']:8.3f} X={r['X']:4d} "
                      f"{r['prev']}->{r['T']} rank={r['rank']}/{r['n']} "
                      f"dT={r['dT']:.0f} d1={r['d1']:.0f} hitter={r['hitter']}")
        return 0
    out = scan()
    print("connections with a henchman body:")
    for stamp, gf, me, party in out["conns"]:
        print(f"  {stamp} {gf[:40]} me={me} party={party}")
    print("\nFORMATION -- henchman lead END vs the observer's latest report:")
    for moving in (True, False):
        rows = [r for r in out["formation"] if r["moving"] == moving]
        d = [r["dist"] for r in rows]
        al = [r["along"] for r in rows if r["along"] is not None]
        ac = [abs(r["across"]) for r in rows if r["across"] is not None]
        print(f"  observer {'MOVING' if moving else 'STANDING'}: n={len(d)} "
              f"dist p10/p50/p90 = {pct(d, .1)!r:>8} {pct(d, .5)!r:>8} "
              f"{pct(d, .9)!r:>8}   along p50={pct(al, .5)!r} "
              f"|across| p50={pct(ac, .5)!r}")
    print("  per body, observer MOVING (signed: +along = ahead of the "
          "observer, +across = its left):")
    byh = collections.defaultdict(list)
    for r in out["formation"]:
        if r["moving"] and r["along"] is not None:
            byh[(r["stamp"], r["H"])].append(r)
    for k in sorted(byh):
        rs = byh[k]
        print(f"    {k[0]} H={k[1]:3d} n={len(rs):3d} dist p50="
              f"{pct([r['dist'] for r in rs], .5):6.1f} along p50="
              f"{pct([r['along'] for r in rs], .5):7.1f} across p50="
              f"{pct([r['across'] for r in rs], .5):7.1f}")
    cd = out["cadence"]
    print(f"\nCADENCE -- gap to the next lead by the same body while the "
          f"observer moves: n={len(cd)} p10/p50/p90 = {pct(cd, .1)!r} "
          f"{pct(cd, .5)!r} {pct(cd, .9)!r}; leads with the observer moving "
          f"{out['moving_leads']}, leads > 1 s into a stand "
          f"{out['standing_leads']}")
    print("  0x0028 halts vs 0x0029 leads per body:",
          {k: (out['halts'][k], out['leads'][k]) for k in sorted(out['leads'])})
    hd = [r["dist"] for r in out["halt"]]
    print(f"\nHALT -- the last lead END within 3 s of an observer stop, vs "
          f"the stop point: n={len(hd)} p10/p50/p90 = {pct(hd, .1)!r} "
          f"{pct(hd, .5)!r} {pct(hd, .9)!r}")
    print("\nENGAGE -- what preceded a party member's opening start (6 s):")
    c = collections.Counter((r["trig"], r["player_target_same"])
                            for r in out["engage"])
    for k in sorted(c, key=str):
        print(f"  trigger={k[0]:16s} same target as the observer={k[1]!s:5s} "
              f"n={c[k]}")
    if args.rows:
        for r in out["engage"]:
            print(f"    {r['stamp']} t={r['t']:8.3f} H={r['H']:3d} T={r['T']:4d}"
                  f" kind={r['kind']} {r['trig']:16s} same={r['player_target_same']!s:5s}"
                  f" lead_me={r['lead_me']} lead_press={r['lead_press']}"
                  f" lead_hostile={r['lead_hostile']}")
    print("\nHOSTILE TARGETS -- who a hostile's start names:")
    for k, n in out["targets"].most_common():
        print(f"  {k:8s} {n}")
    print("\nPARTY CASTS -- skill x target class (hurt = damage on T in 5 s):")
    cc = collections.Counter((r["H"], r["kind"], r["skill"], r["tclass"],
                              r["hurt"]) for r in out["casts"])
    for k in sorted(cc, key=str):
        print(f"  H={k[0]:3d} kind={k[1]} skill={k[2]:4d} target={k[3]:7s} "
              f"hurt={k[4]!s:5s} n={cc[k]}")
    if args.casts:
        for r in out["casts"]:
            print(f"    {r['stamp']} t={r['t']:8.3f} H={r['H']} kind={r['kind']}"
                  f" skill={r['skill']} T={r['T']} {r['tclass']} hurt={r['hurt']}")
    print("\nDEATHS -- 0x00F1 dead bit per party member:")
    for k, n in sorted(out["deaths"].items()):
        print(f"  {k[0]} agent {k[1]}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
