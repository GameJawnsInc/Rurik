"""The cast cycle's gaps, read off the live wire: is the aftercast on it?

The question `studies/castmech/FINDINGS.md` SS3 exists to answer. The emitter
schedules E3 at E5 + aftercast (`authsrv.py`, the QUEUE LAW block), where
`aftercast` is the client table's per-skill float at +0x40 -- but until
2026-08-22 nobody had measured the live E5->E3 gap directly; the schedule was
validated only through the queue law's E4->E5 residuals.

PREDICTION, stated before the numbers (house rule): if `0x00E3` marks the
AFTERCAST ENDING, the Necromancer spell cycles (skills 153 and 105, table
+0x40 = 0.75) show E5->E3 ~= 0.75 s and the Ranger attack-skill cycles (394
Power Shot, +0x40 = 0.0) show ~= 0. If E3 is a fixed follow-on, all six gaps
agree with each other instead. If E3 trails E5 by milliseconds everywhere,
the emitter's schedule is an invention.

MEASURED 2026-08-22: 0.749 / 0.748 / 0.758 / 0.765 for the four spell cycles,
0.000 / 0.000 (same segment) for the two attack-skill cycles. Per-skill, not
fixed. The same pass resolved combat/PLAN SS0a's CONTESTED orphan: the t=5.027
E4 is answered at t=5.912 by the corpus's one `0x00E2` with no E5 ever -- a
terminated cast (the cancel shape: no recharge started), not an orphan.

Read-only over the live captures; no client, no server, no socket. Stdlib
only. Times are connection-local tape times -- the same clock combat/PLAN's
own citations use (its t=9.744 E5 is this tool's 9.7442).
"""
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(HERE)), "schema"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import tape  # noqa: E402
from codec import Codec  # noqa: E402

OPS = {0x00E2: "E2", 0x00E3: "E3", 0x00E4: "E4", 0x00E5: "E5", 0x00E6: "E6"}
CAPTURES = ("20260807T143055", "20260810T235916")
GAPS = (("E4", "E5"), ("E5", "E3"), ("E5", "E6"), ("E4", "E2"))


def cycles(hits):
    """Group lifecycle events into per-(agent, skill) cycles, E4-opened.

    A message's values echo the opcode first: [op, agent, skill, copy, ...].
    """
    seq = defaultdict(list)
    for t, op, vals in hits:
        seq[(vals[1], vals[2])].append((t, OPS[op]))
    out = []
    for (agent, skill), evs in sorted(seq.items()):
        cyc = None
        for t, tag in evs:
            if tag == "E4":
                if cyc:
                    out.append(cyc)
                cyc = {"agent": agent, "skill": skill, "E4": t}
            elif cyc is not None and tag not in cyc:
                cyc[tag] = t
        if cyc:
            out.append(cyc)
    return out


def main():
    codec = Codec()
    n_cycles = 0
    for stamp in CAPTURES:
        cap = tape.resolve_capture(os.path.join("captures", "live", stamp))
        print(f"\n=== {stamp} ===")
        for chan in tape.channel_files(cap):
            conn = chan["connection"] if isinstance(chan, dict) else chan
            try:
                info, events = tape.load_tape(cap, conn)
            except tape.TapeError as exc:
                print(f"  {conn}: TapeError {exc}")
                continue
            msgs, (consumed, total, err) = tape.decode_all(
                events, codec, "GAME_SMSG", 0)
            if err is not None or consumed != total:
                print(f"  {conn}: partial decode {consumed}/{total} ({err}) "
                      f"-- REFUSED, a partial frame invents opcodes")
                continue
            hits = [(t, op, vals) for (t, op, vals) in msgs if op in OPS]
            if not hits:
                continue
            print(f"\n-- conn {conn}  ({len(msgs)} msgs, framed to the last byte)")
            for t, op, vals in hits:
                print(f"   t={t:9.4f}  {OPS[op]:2s} {vals}")
            for c in cycles(hits):
                n_cycles += 1
                parts = [f"agent={c['agent']} skill={c['skill']}"]
                for a, b in GAPS:
                    if a in c and b in c:
                        parts.append(f"{a}->{b}={c[b] - c[a]:+.4f}")
                print("   CYCLE  " + "  ".join(parts))
    print(f"\n{n_cycles} cycles across {len(CAPTURES)} captures "
          f"(6 complete + 1 E2-terminated expected on the 2026-08 corpus)")


if __name__ == "__main__":
    main()
