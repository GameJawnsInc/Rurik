#!/usr/bin/env python3
"""THE RETAIL CONTROL for MOVECODE-1z-cm: does ArenaNet's wire ever split a 0x002B from
its destination with a 0x001E?

    python studies/movecode/review/stalepair_retail.py

Over every LIVE capture (origin-gated through livewire.live_connections; an `ours`
capture filed under live/ is refused there, never pooled), for every s2c 0x002B
(AGENT_UPDATE_SPEED, the rate/facing setter that SETS INTERNAL_FLAG_MOVEMENT_STALE):
walk forward to the same agent's next 0x0029 / 0x002A (the destination setter that
CLEARS it), record what sat between and the wire gap, and count the pairs a 0x001E
(WORLD_SIMULATION_TICK, the message that advances the client's AgTimer and fires the
movement tick whose line-1198 assert is exactly `!(m_flags & MOVEMENT_STALE)`) sits inside.

First run, 2026-09-08 (OBSERVED, 61 live connections, decode closed on all 61):
2,404 0x002B; 2,403 followed by the same agent's destination; wire gap ZERO on 2,403 of
2,403 (the same packet, every time); 0x001E between: 0. What retail does put between
them, rarely: 0x0021 (19 + 3 + 1), an item/effect burst (0x9b 0xf0 0x20 0x6d and kin,
~13). One 0x002B with no destination within 40 messages.

The test (toolkit/authsrv/test_stalepair.py sec.4) pins a FLOOR on the pair count and an
INVARIANT on the splits: the corpus grows, so the count may only rise; a split appearing
at retail would mean the mechanism claim is wrong and the test should go red.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/authsrv"):
    sys.path.insert(0, os.path.join(ROOT, sub))

import livewire     # noqa: E402
import stalepair    # noqa: E402

LOOKAHEAD = 40


def _agent(vals):
    # livewire's decoded values carry the opcode at index 0; the agent is index 1.
    if isinstance(vals, (list, tuple)) and len(vals) > 1:
        return vals[1]
    return None


def retail_census(root=None, lookahead=LOOKAHEAD):
    """{conns, bad_conns, total, pairs, split, bare, zero_gap, between, splits, gaps}."""
    out = {"conns": 0, "bad_conns": 0, "total": 0, "pairs": 0, "split": 0, "bare": 0,
           "zero_gap": 0, "between": collections.Counter(), "splits": [], "gaps": []}
    for capdir, gf in livewire.live_connections(root):
        _conn, merged, ok = livewire.decode_conn(capdir, gf)
        out["conns"] += 1
        if not ok:
            out["bad_conns"] += 1
        s2c = [(t, op, vals) for (t, d, op, vals) in merged if d == "s2c"]
        for i, (t, op, vals) in enumerate(s2c):
            if op != stalepair.OPCODE_RATE:
                continue
            out["total"] += 1
            aid = _agent(vals)
            seq = []
            found = None
            for (t2, op2, v2) in s2c[i + 1:i + 1 + lookahead]:
                if op2 in stalepair.OPCODE_DESTS and _agent(v2) == aid:
                    found = (t2, op2)
                    break
                seq.append(op2)
            if found is None:
                out["bare"] += 1
                continue
            out["pairs"] += 1
            out["between"][tuple(seq)] += 1
            gap = found[0] - t
            out["gaps"].append(gap)
            if gap == 0:
                out["zero_gap"] += 1
            if stalepair.OPCODE_TICK in seq:
                out["split"] += 1
                out["splits"].append((os.path.basename(capdir), gf, round(t, 3), aid,
                                      [hex(x) for x in seq]))
    return out


def main(argv):
    c = retail_census()
    print(f"live connections: {c['conns']} (decode not closed on {c['bad_conns']})")
    print(f"0x002B total {c['total']}; with a same-agent destination within {LOOKAHEAD}: "
          f"{c['pairs']}; bare {c['bare']}")
    print(f"wire gap 0x002B -> destination: zero on {c['zero_gap']} of {c['pairs']}"
          + (f"; max {max(c['gaps']):.4f} s" if c["gaps"] else ""))
    print("between them (top 8):")
    for k, v in c["between"].most_common(8):
        print("  ", v, [hex(x) for x in k])
    print(f"0x001E between: {c['split']}")
    for s in c["splits"][:10]:
        print("  ", s)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
