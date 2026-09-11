r"""A miss on retail's wire: the swing that closes with no damage, and Blind.

    python toolkit/authsrv/missjoin.py            # every live capture
    python toolkit/authsrv/missjoin.py --rows     # one line per no-damage close
    python toolkit/authsrv/missjoin.py --json

THE QUESTION. GWW "Blind" (rev. 2020-10-23): "Your melee and missile attacks
have a 90% chance to miss." GWW "Miss" (rev. 2019-12-30): "After each miss,
the game displays a yellow 'miss' message beside the target." A yellow word
on the screen needs a word on the wire, and this server has never sent one
because it has never had a swing that misses. Before a miss-roll ships, the
corpus is asked what a miss LOOKS LIKE and whether Blind produces it.

THE PREDICTIONS, stated before the numbers:

  P1  a swing close (0x009F property 1, GV_MELEE_ATTACK_FINISHED, on agent C)
      is joined in its own batch (healjoin's 50 ms shoulder) by a damage
      (0x00A3 property 16/17 whose CAUSE is C) in the large majority of
      cases when C carries no live 479 -- the baseline "no-damage close"
      rate is under 25 %.  Blocks, misses from other sources and fully
      converted hits are the residue, so it is a bound and not a zero.
  P2  a swing close by an agent under a LIVE 479 episode (bufflog's
      apply..close window) is a no-damage close at a rate consistent with
      0.90 -- a two-sided binomial 95 % band on the witnesses, and the
      unblinded rate sits OUTSIDE that band.  If the corpus holds no blinded
      swinger this prints NO WITNESS and P2 is carried, not tested.
  P3  a no-damage close carries a message naming the swinger or its target
      that landed closes do not -- the wire word behind the yellow "miss".
      Its opcode and property are READ from the batch-shape histogram, not
      assumed: the candidate is unknown before the run.
  P4  the connection's OWN missed swing grants no adrenaline: no 0x00CF in
      the batch.  WIKI (GWW "Adrenaline"): a strike per SUCCESSFUL hit.
  P5  (added after P3's histogram named nothing, and the client's own
      handler table was read instead -- agents.GV_ATTACK_FAIL): every
      0x00A0 property 38 [target, attacker, reason] on the wire rides a
      batch with NO damage from that attacker onto that target.  The word
      and the number are exclusive.  Reasons are printed by the client's
      own names (block / dodge / fail / miss / obstructed / stray).

WHAT IS TRACKED. The target of a swing is not on the close (property 1
names only the swinger), so the last 0x00A0 property 4 (attack_started
[4, attacker, target]) by the same swinger names it; a close with no start
on record is scored with target None and never counts for P3's target half.

Standard library only. Reads the vault through `vaultpath` (worktree-safe);
refuses a tape that does not frame to its last byte, like `bufflog`.
"""
import argparse
import collections
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import bufflog          # noqa: E402
import deepwoundjoin    # noqa: E402
import healjoin         # noqa: E402
import spellhitjoin     # noqa: E402
import tape             # noqa: E402
import vaultpath        # noqa: E402

BLIND = 479
OP_INT = 0x009F            # [prop, agent, value]
OP_INT_TARGET = 0x00A0     # [prop, a, b, value]
OP_FLOAT = 0x00A2          # [prop, agent, f32]
OP_FLOAT_TARGET = 0x00A3   # [prop, target, cause, f32]
OP_ADRENALINE_GAIN = 0x00CF
PROP_MELEE_FINISHED = 1
PROP_ATTACK_STARTED = 4
PROP_DAMAGE = (16, 17)
PROP_ATTACK_FAIL = 38      # agents.GV_ATTACK_FAIL: [38, target, attacker, reason]
REASONS = {0: "block", 1: "dodge", 2: "fail", 3: "miss", 4: "obstructed",
           5: "stray"}     # the client's own string table, agents.py
BASELINE_CEILING = 0.25    # P1
BLIND_RATE = 0.90          # P2, WIKI


def _names(op, v):
    """Agent ids a message names, by slot, for the four property opcodes."""
    if op == OP_INT or op == OP_FLOAT:
        return (v[2],)
    if op == OP_INT_TARGET:
        return (v[2], v[3])
    if op == OP_FLOAT_TARGET:
        return (v[2], v[3])
    return ()


def _prop(op, v):
    return v[1] if op in (OP_INT, OP_INT_TARGET, OP_FLOAT, OP_FLOAT_TARGET) \
        else None


def blind_windows(capture_dir, connection, codec):
    """{agent: [(t_open, t_close_or_inf)]} for every 479 episode."""
    ev = bufflog.read_effects(capture_dir, connection, codec)
    out = collections.defaultdict(list)
    for ep in bufflog.episodes(ev):
        if ep["skill"] != BLIND:
            continue
        close = ep["close_t"] if ep["close_t"] is not None else math.inf
        out[ep["target"]].append((ep["t"], close))
    return out


def under_blind(windows, agent, t):
    return any(a <= t <= b for a, b in windows.get(agent, ()))


def closes(seq, windows, player):
    """Every swing close, joined to its batch.

    A row: {"t", "swinger", "target", "blind", "landed", "damage_props",
    "siblings" (sorted 'OP:prop' pairs in the batch that name the swinger or
    the target, the close itself and the damage excluded), "self", "gain"
    (a 0x00CF in the batch)}.
    """
    last_target = {}
    rows = []
    for batch in healjoin.batches(seq):
        gain = any(op == OP_ADRENALINE_GAIN for _i, _t, op, _v in batch)
        for _i, t, op, v in batch:
            if op == OP_INT_TARGET and v[1] == PROP_ATTACK_STARTED:
                last_target[v[2]] = v[3]
        for _i, t, op, v in batch:
            if not (op == OP_INT and v[1] == PROP_MELEE_FINISHED):
                continue
            swinger = v[2]
            target = last_target.get(swinger)
            damage = [v2[1] for _j, _t2, op2, v2 in batch
                      if op2 == OP_FLOAT_TARGET and v2[1] in PROP_DAMAGE
                      and v2[3] == swinger]
            sib = []
            for _j, _t2, op2, v2 in batch:
                if op2 == OP_INT and v2[1] == PROP_MELEE_FINISHED \
                        and v2[2] == swinger:
                    continue
                if op2 == OP_FLOAT_TARGET and v2[1] in PROP_DAMAGE \
                        and v2[3] == swinger:
                    continue
                names = _names(op2, v2)
                if swinger in names or (target is not None and target in names):
                    sib.append(f"{op2:#06x}:{_prop(op2, v2)}")
            rows.append({"t": round(t, 6), "swinger": swinger,
                         "target": target,
                         "blind": under_blind(windows, swinger, t),
                         "landed": bool(damage), "damage_props": damage,
                         "siblings": sorted(sib),
                         "self": swinger == player, "gain": gain})
    return rows


def fails(seq, windows, player):
    """Every property 38, joined to its batch (P5).

    A row: {"t", "target", "attacker", "reason", "name", "damage" (16/17
    from the attacker onto the target in the batch), "closes" (the
    attacker's own 1/3/8/46 in the batch, wire order), "blind", "self"}.
    """
    rows = []
    for batch in healjoin.batches(seq):
        for _i, t, op, v in batch:
            if not (op == OP_INT_TARGET and v[1] == PROP_ATTACK_FAIL):
                continue
            target, attacker, reason = v[2], v[3], v[4]
            damage = [v2[1] for _j, _t2, op2, v2 in batch
                      if op2 == OP_FLOAT_TARGET and v2[1] in PROP_DAMAGE
                      and v2[3] == attacker and v2[2] == target]
            closes_ = [v2[1] for _j, _t2, op2, v2 in batch
                       if op2 == OP_INT and v2[1] in (1, 3, 8, 46)
                       and v2[2] == attacker]
            rows.append({"t": round(t, 6), "target": target,
                         "attacker": attacker, "reason": reason,
                         "name": REASONS.get(reason, str(reason)),
                         "damage": damage, "closes": closes_,
                         "blind": under_blind(windows, attacker, t),
                         "self": attacker == player})
    return rows


def census(codec=None):
    """{"closes": [...], "fails": [...]} over every live capture that frames."""
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="missjoin reads live captures")
    out = {"closes": [], "fails": []}
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
            continue
        for ch in tape.channel_files(cap_dir):
            try:
                seq = deepwoundjoin.sequence(cap_dir, ch["connection"], codec)
                windows = blind_windows(cap_dir, ch["connection"], codec)
            except (bufflog.BuffLogError, tape.TapeError):
                continue
            player = spellhitjoin.player_of(seq)
            for key, fn in (("closes", closes), ("fails", fails)):
                for row in fn(seq, windows, player):
                    row.update(capture=stamp, connection=ch["connection"])
                    out[key].append(row)
    return out


def binomial_band(n, p=BLIND_RATE, z=1.96):
    """Two-sided normal band on the observed fraction at n witnesses."""
    if n == 0:
        return None
    half = z * math.sqrt(p * (1 - p) / n)
    return max(0.0, p - half), min(1.0, p + half)


def score(c):
    """The five predictions, scored; the shape histograms, READ."""
    rows, fail_rows = c["closes"], c["fails"]
    plain = [r for r in rows if not r["blind"]]
    blind = [r for r in rows if r["blind"]]
    plain_miss = [r for r in plain if not r["landed"]]
    blind_miss = [r for r in blind if not r["landed"]]
    p1_rate = len(plain_miss) / len(plain) if plain else None
    p2_rate = len(blind_miss) / len(blind) if blind else None
    band = binomial_band(len(blind))
    # P3: sibling shapes, landed against not, unblinded and blinded alike.
    shape_hit = collections.Counter()
    shape_miss = collections.Counter()
    for r in rows:
        key = " ".join(r["siblings"]) or "(nothing)"
        (shape_hit if r["landed"] else shape_miss)[key] += 1
    # Which single 'OP:prop' pairs ride a no-damage close and not a hit.
    pair_hit = collections.Counter()
    pair_miss = collections.Counter()
    for r in rows:
        for s in set(r["siblings"]):
            (pair_hit if r["landed"] else pair_miss)[s] += 1
    marker = sorted(((s, pair_miss[s], pair_hit.get(s, 0))
                     for s in pair_miss), key=lambda x: -x[1])
    own = [r for r in rows if r["self"]]
    own_miss = [r for r in own if not r["landed"]]
    own_miss_gain = [r for r in own_miss if r["gain"]]
    own_hit_gain = [r for r in own if r["landed"] and r["gain"]]
    return {
        "closes": len(rows), "plain": len(plain), "plain_miss": len(plain_miss),
        "p1_rate": p1_rate,
        "p1": p1_rate is not None and p1_rate < BASELINE_CEILING,
        "blind": len(blind), "blind_miss": len(blind_miss),
        "p2_rate": p2_rate, "p2_band": band,
        "p2": (None if p2_rate is None else
               (band[0] <= p2_rate <= band[1]
                and not (band[0] <= (p1_rate or 0.0) <= band[1]))),
        "blind_captures": sorted({(r["capture"], r["connection"])
                                  for r in blind}),
        "shape_hit": shape_hit.most_common(12),
        "shape_miss": shape_miss.most_common(12),
        "marker": marker[:12],
        "own": len(own), "own_hit": len(own) - len(own_miss),
        "own_hit_gain": len(own_hit_gain),
        "own_miss": len(own_miss), "own_miss_gain": len(own_miss_gain),
        "p4": len(own_miss_gain) == 0 if own_miss else None,
        "fails": len(fail_rows),
        "fail_reasons": dict(collections.Counter(r["reason"] for r in fail_rows)),
        "fail_with_damage": sum(1 for r in fail_rows if r["damage"]),
        "fail_closes": dict(collections.Counter(
            " ".join(str(x) for x in r["closes"]) or "(none)" for r in fail_rows)),
        "fail_blind": sum(1 for r in fail_rows if r["blind"]),
        "p5": (all(not r["damage"] for r in fail_rows) if fail_rows else None),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rows", action="store_true",
                    help="one line per NO-DAMAGE swing close")
    ap.add_argument("--fails", action="store_true",
                    help="one line per property 38 on the wire")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    c = census()
    rows = c["closes"]
    s = score(c)
    if a.json:
        print(json.dumps({"score": s, "closes": rows, "fails": c["fails"]},
                         indent=1, default=str))
        return
    if a.fails:
        for r in c["fails"]:
            print(f"{r['capture']} {r['connection']} t={r['t']:.3f} "
                  f"[38, target {r['target']}, attacker {r['attacker']}, "
                  f"reason {r['reason']} '{r['name']}']  damage={r['damage']} "
                  f"attacker's closes={r['closes']}  "
                  f"{'BLIND' if r['blind'] else 'plain'}  "
                  f"{'self' if r['self'] else ''}")
        print()
    if a.rows:
        for r in rows:
            if r["landed"]:
                continue
            print(f"{r['capture']} {r['connection']} t={r['t']:.3f} "
                  f"swinger {r['swinger']:4} -> {r['target']}  "
                  f"{'BLIND' if r['blind'] else 'plain'}  "
                  f"{'self' if r['self'] else '    '} gain={r['gain']}  "
                  f"[{' '.join(r['siblings'])}]")
        print()
    print(f"swing closes {s['closes']}  (own {s['own']})")
    print(f"P1 unblinded: {s['plain_miss']} of {s['plain']} no-damage closes"
          f" = {s['p1_rate'] if s['p1_rate'] is None else round(s['p1_rate'], 4)}"
          f"  (< {BASELINE_CEILING})  -> {s['p1']}")
    if s["blind"]:
        lo, hi = s["p2_band"]
        print(f"P2 blinded:   {s['blind_miss']} of {s['blind']} no-damage closes"
              f" = {round(s['p2_rate'], 4)}  band at 0.90 [{lo:.3f}, {hi:.3f}]"
              f"  -> {s['p2']}")
        for cap, conn in s["blind_captures"]:
            print(f"      blinded swinger in {cap} {conn}")
    else:
        print("P2 blinded:   NO WITNESS -- no swing close under a live 479")
    print("P3 batch shapes (siblings naming swinger/target), LANDED:")
    for key, n in s["shape_hit"]:
        print(f"      {n:5}  {key}")
    print("P3 batch shapes, NO DAMAGE:")
    for key, n in s["shape_miss"]:
        print(f"      {n:5}  {key}")
    print("P3 pairs riding a no-damage close (n_miss, n_hit):")
    for key, nm, nh in s["marker"]:
        print(f"      {key:14} {nm:5} {nh:5}")
    print(f"P4 own swings: hit {s['own_hit']} (gain in batch {s['own_hit_gain']})"
          f"  no-damage {s['own_miss']} (gain in batch {s['own_miss_gain']})"
          f"  -> {s['p4']}")
    reasons = {f"{k} '{REASONS.get(k, '?')}'": n
               for k, n in sorted(s["fail_reasons"].items())}
    print(f"P5 property 38 on the wire: {s['fails']}  reasons {reasons}  "
          f"with damage from attacker onto target {s['fail_with_damage']}  "
          f"attacker's closes in the batch {s['fail_closes']}  "
          f"attacker blind {s['fail_blind']}  -> {s['p5']}")


if __name__ == "__main__":
    main()
