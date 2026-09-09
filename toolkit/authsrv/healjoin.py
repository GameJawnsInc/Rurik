r"""Every property-55 gain on retail's wire: what rides beside it, and whether the
pool it lands on was already full.

    python toolkit/authsrv/healjoin.py            # every live capture
    python toolkit/authsrv/healjoin.py --json

WHY THIS EXISTS. `studies/skills/FINDINGS.md` 19 confirmed property 55 as the
healing channel at the client (the orb moved 54 -> 100 by exactly the 46 sent)
and then reported that the client draws NO number for it -- a green-pixel scan
over twenty frames found 0-8 saturated green pixels -- and filed the annotation
as OPEN for three weeks. The desk half of closing it is the same method that
found the damage batch and the Deep Wound batch (`deepwoundjoin.py`): census
every retail 55 for sibling properties in its batch, so that if some OTHER
property is what makes the client draw, it shows up riding beside the 55.

THE PREDICTIONS, stated before the numbers:

  P1  property 55 is the health-GAIN direction: positive in >= 99% of events
      (FINDINGS 19 measured 502 of 506; the four negatives read as sacrifice).
  P2  no sibling property is REQUIRED to annotate a heal. Operationally: the
      same-agent siblings of a 55 fall inside the set this server already
      sends at a cast end -- {58 skill_finished, 21/20 skill visuals, 8, 42,
      another 55} -- in >= 90% of events, and the bare shape `[58, 55]` (a
      heal riding with nothing target-facing at all) occurs >= 100 times. If
      instead some property rode beside 55 in most batches and never beside
      damage, THAT would be the annotation candidate and would need the probe.
  P3  the world tick `0x001E` closes every batch, heal or damage alike -- it
      is a terminator this server already sends, not a candidate.
  P4  retail sends a 55 on a FULL pool. WIKI (GWW "Heal", rev. 2023-08-05):
      "The healing player and healed player see blue numbers showing the
      amount healed. Blue numbers are shown even when no health are actually
      gained (usually because the character is at full health)." The client
      cannot print an amount it never received, so the wire must carry the
      55 regardless of the pool. Test: a positive 55 on an agent that has
      taken NO health loss on this connection before it (no 16/17 damage, no
      negative 44, no negative 55, no 34 setter) lands on a pool that is full
      by construction -- agents spawn full (property 42 sets max AND pool,
      agentprops 1). Prediction: >= 40 such events, non-zero values.

WHAT THIS DELIBERATELY DOES NOT DO. It does not say what the client DRAWS --
that is a frame, not a wire (FINDINGS 42.2 re-read the 2026-08-20 frames and
found the number the green scan could not see). And "virgin pool" is a floor
on overheals, not a count of them: regen (positive 44) refills pools this
ledger never credits, so every heal it calls an overheal is one, and some it
does not call one are.

A batch is a contiguous run of messages with no inter-message gap above the
corpus's 50 ms shoulder (`deepwoundjoin.BATCH`). Standard library only; reads
the vault through `vaultpath`; refuses a tape that does not frame whole.
"""
import argparse
import collections
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import bufflog          # noqa: E402
import deepwoundjoin    # noqa: E402
import tape             # noqa: E402
import vaultpath        # noqa: E402

BATCH = deepwoundjoin.BATCH
OP_INT = 0x009F            # [prop, agent, value]
OP_INT_TARGET = 0x00A0     # [prop, a, b, value]
OP_FLOAT = 0x00A2          # [prop, agent, f32]
OP_FLOAT_TARGET = 0x00A3   # [prop, target, cause, f32]
OP_TICK = 0x001E           # the world simulation tick
PROP_HEAL = 55
PROP_DAMAGE = (16, 17)
PROP_REGEN = 44
PROP_HEALTH_SET = 34
# Decoded values carry the opcode at [0]; agent slots per property opcode.
_AGENT_SLOTS = {OP_INT: (2,), OP_INT_TARGET: (2, 3), OP_FLOAT: (2,),
                OP_FLOAT_TARGET: (2, 3)}
# What this server already sends around a cast end (authsrv.cast_tick,
# send_skill_visual, action_hold) -- a sibling inside this set is not a gap.
KNOWN_SIBLINGS = frozenset({(OP_INT, 58), (OP_INT, 21), (OP_INT_TARGET, 20),
                            (OP_INT, 8), (OP_INT, 42),
                            (OP_FLOAT_TARGET, PROP_HEAL)})


def _f32(bits):
    return struct.unpack("<f", struct.pack("<I", bits & 0xFFFFFFFF))[0]


def batches(seq):
    """Split a decoded sequence into batches at gaps above the shoulder."""
    out, cur = [], []
    for row in seq:
        if cur and row[1] - cur[-1][1] > BATCH:
            out.append(cur)
            cur = []
        cur.append(row)
    if cur:
        out.append(cur)
    return out


def events(seq):
    """Every 55 and every 16/17 in one sequence, each with its batch context.

    A row: {"t", "prop", "target", "cause", "value", "self", "siblings"
    (same-agent (op, prop) pairs, the event itself excluded), "shape" (the
    batch's same-agent messages as 'OP:prop' in wire order, ticks included),
    "tick" (a 0x001E is in the batch), "virgin" (55 only: no prior loss)}.
    """
    loss = collections.defaultdict(float)
    touched = set()          # agents whose pool moved down by any other route
    rows = []
    for batch in batches(seq):
        for i, t, op, v in batch:
            if op == OP_FLOAT and v[1] == PROP_REGEN and _f32(v[3]) < 0:
                touched.add(v[2])
            if op == OP_FLOAT_TARGET and v[1] == PROP_HEALTH_SET:
                touched.add(v[2])
            if op != OP_FLOAT_TARGET or v[1] not in PROP_DAMAGE + (PROP_HEAL,):
                continue
            prop, target, cause, value = v[1], v[2], v[3], _f32(v[4])
            siblings, shape, tick = [], [], False
            for j, tj, opj, vj in batch:
                if opj in _AGENT_SLOTS:
                    agents = [vj[k] for k in _AGENT_SLOTS[opj]]
                    if target in agents:
                        shape.append(f"{opj:X}:{vj[1]}")
                        if j != i:
                            siblings.append((opj, vj[1]))
                elif opj == OP_TICK:
                    shape.append("1E")
                    tick = True
            row = {"t": round(t, 6), "prop": prop, "target": target,
                   "cause": cause, "value": round(value, 6),
                   "self": target == cause, "siblings": siblings,
                   "shape": " ".join(shape), "tick": tick}
            if prop == PROP_HEAL:
                virgin = loss[target] == 0.0 and target not in touched
                row["virgin"] = virgin
                row["loss_before"] = round(loss[target], 6)
                if value < 0:
                    loss[target] += -value
                else:
                    loss[target] = max(0.0, loss[target] - value)
            else:
                loss[target] += -value
            rows.append(row)
    return rows


def census(codec=None):
    """Every live capture, every game connection that frames whole."""
    codec = codec or bufflog.Codec()
    live = vaultpath.require_dir("captures", "live",
                                 why="healjoin reads live captures")
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
            for row in events(seq):
                row.update(capture=stamp, connection=ch["connection"])
                out.append(row)
    return out


def score(rows):
    """The numbers P1-P4 are judged on, from a census."""
    heals = [r for r in rows if r["prop"] == PROP_HEAL]
    dmg = [r for r in rows if r["prop"] in PROP_DAMAGE]
    sib = collections.Counter()
    for r in heals:
        for k in set(r["siblings"]):
            sib[k] += 1
    dsib = collections.Counter()
    for r in dmg:
        for k in set(r["siblings"]):
            dsib[k] += 1
    shapes = collections.Counter(r["shape"] for r in heals)
    virgin = [r for r in heals if r["value"] > 0 and r["virgin"]]
    exceeds = [r for r in heals if r["value"] > 0 and not r["virgin"]
               and r["value"] > r["loss_before"] + 1e-6]
    return {
        "n": len(heals),
        "positive": sum(1 for r in heals if r["value"] > 0),
        "self": sum(1 for r in heals if r["self"]),
        "n_damage": len(dmg),
        "within_known": sum(1 for r in heals
                            if not (set(r["siblings"]) - KNOWN_SIBLINGS)),
        "bare_58_55": sum(n for s, n in shapes.items()
                          if s.replace(" 1E", "") == "9F:58 A3:55"),
        "tick_heal": sum(1 for r in heals if r["tick"]),
        "tick_damage": sum(1 for r in dmg if r["tick"]),
        "siblings": {f"{op:X}:{p}": n for (op, p), n in sib.most_common()},
        "damage_siblings": {f"{op:X}:{p}": n for (op, p), n in dsib.most_common()},
        "shapes": shapes.most_common(12),
        "virgin": len(virgin),
        "virgin_values": sorted({r["value"] for r in virgin}),
        "exceeds_loss": len(exceeds),
        "non_virgin": sum(1 for r in heals if r["value"] > 0 and not r["virgin"]),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rows = census()
    sc = score(rows)
    if args.json:
        print(json.dumps({"score": sc, "rows": rows}, indent=1))
        return
    print(f"property-55 events {sc['n']}: positive {sc['positive']}, "
          f"self-directed {sc['self']}; damage 16/17 events {sc['n_damage']}")
    print(f"P2 siblings on the same agent, in how many heal batches "
          f"(damage batches in brackets):")
    for k, n in sc["siblings"].items():
        print(f"   {k:>8}: {n:5d}   [{sc['damage_siblings'].get(k, 0)}]")
    print(f"   within the set this server already sends: "
          f"{sc['within_known']} of {sc['n']}; bare [58, 55]: {sc['bare_58_55']}")
    print("   same-agent batch shapes, wire order:")
    for s, n in sc["shapes"]:
        print(f"   {n:5d}  {s}")
    print(f"P3 a 0x001E in the batch: heals {sc['tick_heal']}/{sc['n']}, "
          f"damage {sc['tick_damage']}/{sc['n_damage']}")
    print(f"P4 positive 55 on a VIRGIN pool: {sc['virgin']} "
          f"(values {sc['virgin_values']}); on a damaged pool "
          f"{sc['non_virgin']}, of which {sc['exceeds_loss']} exceed the "
          f"loss this ledger still owes (regen-blind, so a floor)")


if __name__ == "__main__":
    main()
