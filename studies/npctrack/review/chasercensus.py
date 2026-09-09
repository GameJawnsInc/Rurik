#!/usr/bin/env python3
"""What does retail's server send the SECOND chaser? (NPCTRACK-Q10, the retail half)

    python studies/npctrack/review/chasercensus.py                 # chases of the PLAYER
    python studies/npctrack/review/chasercensus.py --any-target    # two NPCs on ANY one target

RUN-Q10 put two Hatchers on the same player and both drawn bodies ended at 0.0 u from each
other, parked on identical server halt points: our follow names the player's frame for
every hostile, so two chasers receive the SAME order, and the client's agent-avoidance pass
(F14, rule 1) skips an obstacle whose target point is our own. This census asks the live
corpus what ArenaNet's server does when two or more of its NPCs chase one player at once.

For every live connection (livewire, origin LIVE): the player is the agent whose 0x0029s
answer the c2s 0x003D reports (floorcensus's rule); a CHASE is a non-player agent's 0x002A
naming the player as target, open from its first such order until that agent's next 0x0028
halt. Where two chases overlap in time, it prints per pair: the two chasers' 0x002A point
separation (the point in a 0x002A is the server's copy of the target at the send), how many
0x0029 point legs each chaser got DURING the overlap and where those points sit relative to
the player and to the other chaser, and the two chasers' last ordered points at their halts.

Read-only. Stdlib only. Needs the vault's live captures.
"""
import bisect
import collections
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/authsrv", "toolkit/clientscan"):
    sys.path.insert(0, os.path.join(ROOT, sub))

C2S_HEADING = 61          # 0x003D
S2C_LEG = 41              # 0x0029  [op, agent, point, w, w]
S2C_FOLLOW = 42           # 0x002A  [op, agent, point, w, w, target]
S2C_HALT = 40             # 0x0028  [op, agent]
ANSWER_WINDOW = 0.3
MAX_CHASE_S = 60.0        # a chase with no halt is closed after this


def d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def q(v, f):
    v = sorted(v)
    return v[min(int(f * len(v)), len(v) - 1)] if v else float("nan")


def player_of(merged):
    c61 = [(t, v) for (t, dr, op, v) in merged if dr == "c2s" and op == C2S_HEADING]
    s29 = [(t, v) for (t, dr, op, v) in merged if dr == "s2c" and op == S2C_LEG and len(v) >= 3]
    if len(c61) < 5 or not s29:
        return None, c61
    cnt = collections.Counter()
    st = [t for t, _ in s29]
    for t, _ in c61:
        i = bisect.bisect_left(st, t)
        for j in range(i, min(i + 4, len(s29))):
            if s29[j][0] - t <= ANSWER_WINDOW:
                cnt[s29[j][1][1]] += 1
    return (cnt.most_common(1)[0][0] if cnt else None), c61


def chases(merged, pid, any_target=False):
    """-> [{agent, t0, t1, target, follows[(t, point)], legs[(t, point)]}] -- one record per
    chase: a non-player agent's 0x002A naming `pid` (or, with any_target, naming ANY agent:
    the same server rule, two chasers on one target, with far more exposure), open until
    that agent's next 0x0028."""
    by_agent = collections.defaultdict(list)          # agent -> [(t, kind, point, target)]
    for (t, dr, op, v) in merged:
        if dr != "s2c" or len(v) < 2 or v[1] == pid:
            continue
        if op == S2C_FOLLOW and len(v) >= 6 and (any_target or v[5] == pid):
            by_agent[v[1]].append((t, "follow", tuple(v[2]), v[5]))
        elif op == S2C_LEG and len(v) >= 3:
            by_agent[v[1]].append((t, "leg", tuple(v[2]), None))
        elif op == S2C_HALT:
            by_agent[v[1]].append((t, "halt", None, None))
    out = []
    for a, ev in by_agent.items():
        ev.sort(key=lambda e: e[0])
        cur = None
        for t, kind, p, tgt in ev:
            if kind == "follow":
                if cur is not None and cur["target"] != tgt:
                    cur["t1"] = t                     # re-targeted: a new chase
                    out.append(cur)
                    cur = None
                if cur is None:
                    cur = {"agent": a, "t0": t, "target": tgt, "follows": [], "legs": []}
                cur["follows"].append((t, p))
            elif cur is not None and kind == "leg":
                cur["legs"].append((t, p))
            elif cur is not None and kind == "halt":
                cur["t1"] = t
                out.append(cur)
                cur = None
            if cur is not None and t - cur["t0"] > MAX_CHASE_S:
                cur["t1"] = cur["t0"] + MAX_CHASE_S
                out.append(cur)
                cur = None
        if cur is not None:
            cur["t1"] = ev[-1][0]
            out.append(cur)
    return out


def report_at(c61, t):
    ts = [x[0] for x in c61]
    i = bisect.bisect_right(ts, t) - 1
    return tuple(c61[max(i, 0)][1][1]) if c61 else None


def main(argv):
    import livewire
    any_target = "--any-target" in argv
    conns = 0
    chase_n = 0
    overlaps = []
    for capdir, conn_file in livewire.live_connections():
        conn, merged, ok = livewire.decode_conn(capdir, conn_file)
        if not ok or not merged:
            continue
        pid, c61 = player_of(merged)
        if pid is None:
            continue
        ch = chases(merged, pid, any_target=any_target)
        if not ch:
            continue
        conns += 1
        chase_n += len(ch)
        ch.sort(key=lambda c: c["t0"])
        for i, a in enumerate(ch):
            for b in ch[i + 1:]:
                if b["t0"] >= a["t1"]:
                    break
                if b["target"] != a["target"]:
                    continue                          # two chasers, one target
                lo, hi = b["t0"], min(a["t1"], b["t1"])
                if hi - lo < 0.5:
                    continue
                overlaps.append((os.path.basename(capdir), conn_file, a, b, lo, hi, c61))
    print(f"live connections with a chase of the player: {conns}; chases {chase_n}; "
          f"overlapping chase pairs (>= 0.5 s): {len(overlaps)}")
    same_pt, legs_a, legs_b, last_sep, follow_sep, leg_vs_player, leg_vs_other = [], [], [], [], [], [], []
    for stamp, conn_file, a, b, lo, hi, c61 in overlaps:
        fa = [(t, p) for t, p in a["follows"] if lo <= t <= hi]
        fb = [(t, p) for t, p in b["follows"] if lo <= t <= hi]
        la = [(t, p) for t, p in a["legs"] if lo <= t <= hi]
        lb = [(t, p) for t, p in b["legs"] if lo <= t <= hi]
        legs_a.append(len(la))
        legs_b.append(len(lb))
        # follows within 0.5 s of each other: the same server copy of the player?
        for ta, pa in fa:
            for tb, pb in fb:
                if abs(ta - tb) <= 0.5:
                    follow_sep.append(d(pa, pb))
        # leg points relative to the player's report and to the other chaser's last order
        def last_order(c, t):
            ords = sorted(c["follows"] + c["legs"])
            i = bisect.bisect_right([x[0] for x in ords], t) - 1
            return ords[i][1] if i >= 0 else None
        for t, p in la + lb:
            rp = report_at(c61, t)
            if rp:
                leg_vs_player.append(d(p, rp))
            other = b if (t, p) in la else a
            op = last_order(other, t)
            if op:
                leg_vs_other.append(d(p, op))
        # the two chasers' last ordered points at the end of the overlap
        pa, pb = last_order(a, hi), last_order(b, hi)
        if pa and pb:
            last_sep.append(d(pa, pb))
        print(f"  {stamp} {conn_file}: agents {a['agent']} & {b['agent']} -> {a['target']} overlap {hi - lo:5.1f} s "
              f"[{lo:7.1f}-{hi:7.1f}]  follows {len(fa)}/{len(fb)}  legs {len(la)}/{len(lb)}  "
              f"last-order sep {d(pa, pb) if pa and pb else float('nan'):6.1f} u")
    if not overlaps:
        print("no overlapping chases in the corpus -- zero exposure, not a null")
        return 2
    print(f"\nPOOLED over {len(overlaps)} pairs:")
    print(f"  0x002A points sent to the two chasers within 0.5 s of each other: n={len(follow_sep)}, "
          f"separation p50 {q(follow_sep, .5):.1f} p90 {q(follow_sep, .9):.1f} max {max(follow_sep) if follow_sep else float('nan'):.1f} u")
    print(f"  0x0029 legs during the overlap: chaser A p50 {q(legs_a, .5):.0f} max {max(legs_a)}, "
          f"chaser B p50 {q(legs_b, .5):.0f} max {max(legs_b)}; pairs with legs on either: "
          f"{sum(1 for x, y in zip(legs_a, legs_b) if x or y)}")
    if leg_vs_player:
        print(f"  those leg points vs the player's report: p50 {q(leg_vs_player, .5):.0f} p10 {q(leg_vs_player, .1):.0f} u; "
              f"vs the other chaser's last order: p50 {q(leg_vs_other, .5):.0f} p10 {q(leg_vs_other, .1):.0f} u")
    print(f"  the two chasers' last ordered points at the overlap's end: sep p50 {q(last_sep, .5):.1f} "
          f"p10 {q(last_sep, .1):.1f} u; identical (< 1 u) on {sum(1 for x in last_sep if x < 1)} of {len(last_sep)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
