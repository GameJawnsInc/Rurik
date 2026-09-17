r"""The swing windup on retail's wire, under every attack-speed modifier it declares.

    python toolkit/authsrv/iaswindup.py            # every live capture
    python toolkit/authsrv/iaswindup.py --json

THE QUESTION. `studies/animref/FINDINGS.md` 17 decoded the client's attack
duration math and found no additive term, left the server's windup at candidate A

    windup = modifier * base / 2 - 0.1 s

and said the corpus could not referee it: 62 `0x0035` declarations, every
modifier 1.0, zero landed swings under a stance ("zero exposure, not a null").
That was true on 2026-08-31. The owner's Warrior tapes since (JARIN's hero and
WARRIOR-PRE's player, both under Frenzy's 0.67) changed the exposure, and nobody
re-asked. This asks.

THE MEASUREMENT. Per connection, the running `0x0035 [agent, base, modifier]`
per agent; a swing is an attack start (`0x00A0` property 4, the attacker in slot
2) closed by that agent's `0x009F` property 1. The windup is close minus start.
Rows are grouped by (capture, agent, base, modifier) and the MEDIAN is scored --
the start is stamped on a batch boundary, so single rows carry +-30 ms.

THE PREDICTIONS, stated before the numbers (RUN-SKILLS-RB2's desk half,
2026-09-17):

  W1  every group of >= 4 swings has its median within 20 ms of candidate A.
  W2  candidate B (no additive term, modifier * base / 2) misses every such
      group by more than 50 ms -- so the -0.1 is measured, not fitted.
  W3  the exposure is real: at least two groups carry a modifier other than 1.0,
      on at least two different bases.

Labels: the windup law OBSERVED where a group exists; nothing is claimed for a
base or a modifier the corpus does not hold.
"""
import argparse
import collections
import json
import os
import statistics
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import bufflog          # noqa: E402
import deepwoundjoin    # noqa: E402
import tape             # noqa: E402
import vaultpath        # noqa: E402

OP_INT = 0x009F            # [prop, agent, value]
OP_INT_TARGET = 0x00A0     # [prop, a, b, value]
OP_ATTACK_SPEED = 0x0035   # [agent, f32 base, f32 modifier]
PROP_MELEE_FINISHED = 1
PROP_ATTACK_STARTED = 4
MIN_GROUP = 4              # swings before a group's median is scored
NEAR_A = 0.020             # s; W1
FAR_B = 0.050              # s; W2
WINDOW = (0.1, 3.0)        # s; a start..close outside this is not one swing


def _f32(x):
    if isinstance(x, float):
        return x
    return struct.unpack("<f", struct.pack("<I", int(x) & 0xFFFFFFFF))[0]


def candidate_a(base, modifier):
    return modifier * base / 2.0 - 0.1


def candidate_b(base, modifier):
    return modifier * base / 2.0


def swings(seq):
    """[{"agent", "base", "modifier", "windup"}] for one decoded sequence."""
    speed, start, rows = {}, {}, []
    for _i, t, op, v in seq:
        if op == OP_ATTACK_SPEED:
            speed[v[1]] = (round(_f32(v[2]), 3), round(_f32(v[3]), 3))
        elif op == OP_INT_TARGET and v[1] == PROP_ATTACK_STARTED:
            start[v[2]] = t
        elif op == OP_INT and v[1] == PROP_MELEE_FINISHED:
            agent = v[2]
            if agent in start and agent in speed:
                w = t - start.pop(agent)
                if WINDOW[0] < w < WINDOW[1]:
                    base, mod = speed[agent]
                    rows.append({"agent": agent, "base": base,
                                 "modifier": mod, "windup": round(w, 6)})
    return rows


def census(codec=None):
    """Every swing under a declared attack speed, over every live capture."""
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="iaswindup reads live captures")
    out = []
    for stamp in sorted(os.listdir(live)):
        cap_dir = os.path.join(live, stamp)
        if not os.path.isdir(cap_dir):
            continue
        for ch in tape.channel_files(cap_dir):
            try:
                seq = deepwoundjoin.sequence(cap_dir, ch["connection"], codec)
            except (bufflog.BuffLogError, tape.TapeError):
                continue
            for row in swings(seq):
                row.update(capture=stamp, connection=ch["connection"])
                out.append(row)
    return out


def score(rows):
    """W1-W3, scored on group medians."""
    g = collections.defaultdict(list)
    for r in rows:
        g[(r["capture"], r["agent"], r["base"], r["modifier"])].append(r["windup"])
    groups = []
    for (cap, agent, base, mod), ws in sorted(g.items()):
        if len(ws) < MIN_GROUP:
            continue
        med = statistics.median(ws)
        groups.append({"capture": cap, "agent": agent, "base": base,
                       "modifier": mod, "n": len(ws), "median": round(med, 4),
                       "a": round(candidate_a(base, mod), 4),
                       "b": round(candidate_b(base, mod), 4),
                       "err_a": round(med - candidate_a(base, mod), 4),
                       "err_b": round(med - candidate_b(base, mod), 4)})
    modified = [x for x in groups if abs(x["modifier"] - 1.0) > 1e-3]
    return {
        "swings": len(rows), "groups": groups,
        "modified_groups": len(modified),
        "modified_bases": sorted({x["base"] for x in modified}),
        "w1": bool(groups) and all(abs(x["err_a"]) <= NEAR_A for x in groups),
        "w2": bool(groups) and all(abs(x["err_b"]) > FAR_B for x in groups),
        "w3": len(modified) >= 2 and len({x["base"] for x in modified}) >= 2,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    sc = score(census())
    if args.json:
        print(json.dumps(sc, indent=1))
        return
    print(f"swings under a declared 0x0035: {sc['swings']}; groups of >= "
          f"{MIN_GROUP}: {len(sc['groups'])}, of which modifier != 1.0: "
          f"{sc['modified_groups']} on bases {sc['modified_bases']}")
    for x in sc["groups"]:
        print(f"   {x['capture']} agent {x['agent']:4d} base {x['base']:5.2f} "
              f"mod {x['modifier']:4.2f}  n={x['n']:3d}  median {x['median']:.3f}"
              f"   A {x['a']:.3f} ({x['err_a']:+.3f})   B {x['b']:.3f} "
              f"({x['err_b']:+.3f})")
    print(f"W1 every median within {NEAR_A * 1000:.0f} ms of A: {sc['w1']}   "
          f"W2 B off by > {FAR_B * 1000:.0f} ms everywhere: {sc['w2']}   "
          f"W3 exposure (>= 2 modified groups, >= 2 bases): {sc['w3']}")


if __name__ == "__main__":
    main()
