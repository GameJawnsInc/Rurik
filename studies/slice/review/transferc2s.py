#!/usr/bin/env python3
"""SLICE-U3: what does the CLIENT send before the server hands it to another map?

    python studies/slice/review/transferc2s.py
    python studies/slice/review/transferc2s.py --window 15

THE QUESTION. `0x01A5 GAME_SERVER_TRANSFER` is decoded end to end (studies/tape
T8/T9) and our server has never sent one outside tape playback. Before it can,
somebody has to know what makes retail send it -- i.e. what the player's client
transmits when the player walks into a portal or asks to go back to an outpost.
No named GAME_CMSG covers it.

WHY THIS IS A DESK QUESTION AND NOT A RUN. The corpus already holds the event:
live captures with real map changes, both directions, with c2s timing
recoverable by `cmsgstream.timed`. Reading it costs nothing and rules out
candidates a run would then have to re-test anyway.

THE TRAP THIS IS BUILT AROUND, and it is the reason for the control column. The
client sends `0x003D MOVE_SET_HEADING` constantly -- 161 of one tape's 330
messages. So "0x003D appears just before the transfer" is true and means
NOTHING. What would mean something is an opcode whose occurrences are CONCENTRATED
in the pre-transfer windows: seen k times in the corpus, and k of those k inside a
window. So every opcode is reported as `in-window / total`, and an opcode that
fires all session long is visibly not the answer no matter how close to the
transfer it lands (`feedback-a-dramatic-desk-ratio-is-not-a-mechanism`).

A FORWARD WINDOW IS MEASURED TOO, as a symmetry control. If an opcode is as
common just AFTER the transfer as just before it, proximity is an artifact of the
window and not a relationship (`feedback-symmetric-join-window`).

READ ONLY. Opens vault captures and writes nothing.
"""
import argparse
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for p in (os.path.join(ROOT, "toolkit"),
          os.path.join(ROOT, "toolkit", "authsrv"),
          os.path.join(ROOT, "toolkit", "schema")):
    if p not in sys.path:
        sys.path.insert(0, p)

import cmsgstream  # noqa: E402
from vaultpath import vault_path  # noqa: E402

TRANSFER = 0x01A5
# THE DESTINATION COMES OFF 0x01A5 ITSELF, field[4] -- no join required, and the
# first version of this script got it wrong in a way worth recording: it joined
# to the following 0x0099 and read values[0], which is the OPCODE (codec puts it
# there), so all 41 transfers reported "map 153" = 0x0099. A constant answer
# across every row is the shape of a field error, not a finding.
DEST_FIELD = 4
SIGNAL = 0x00B1          # the candidate this study found; see the split below


def live_stamps():
    root = vault_path("captures", "live")
    return sorted(d for d in os.listdir(root)
                  if os.path.isdir(os.path.join(root, d)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("stamps", nargs="*", help="capture stamps; default: all live")
    ap.add_argument("--window", type=float, default=10.0,
                    help="seconds before a transfer to call 'pre' (default 10)")
    a = ap.parse_args(argv)

    stamps = a.stamps or live_stamps()
    W = a.window

    transfers = []          # (stamp, conn, t)
    pre = collections.Counter()
    post = collections.Counter()
    total = collections.Counter()
    last_before = collections.Counter()
    detail = []

    scanned = 0
    for stamp in stamps:
        try:
            s2c = cmsgstream.timed(stamp, "s2c", "game")
            c2s = cmsgstream.timed(stamp, "c2s", "game")
        except Exception as exc:                       # noqa: BLE001
            print(f"  {stamp}: SKIPPED ({type(exc).__name__}: {exc})")
            continue
        scanned += 1
        hits = [(conn, t, v) for (t, conn, op, v) in s2c if op == TRANSFER]
        if not hits:
            continue
        by_conn = collections.defaultdict(list)
        for (t, conn, op, _v) in c2s:
            by_conn[conn].append((t, op))
            total[op] += 1
        for conn, t0, tv in hits:
            transfers.append((stamp, conn, t0))
            msgs = sorted(by_conn.get(conn, []))
            before = [(t, op) for (t, op) in msgs if t0 - W <= t <= t0]
            after = [(t, op) for (t, op) in msgs if t0 < t <= t0 + W]
            for _t, op in before:
                pre[op] += 1
            for _t, op in after:
                post[op] += 1
            if before:
                last_before[before[-1][1]] += 1
            try:
                dest = int(tv[DEST_FIELD])
            except (TypeError, ValueError, IndexError):
                dest = None
            detail.append((stamp, conn, t0, before[-6:], dest))

    print(f"scanned {scanned} capture(s); {len(transfers)} transfer(s) found "
          f"on the game channel\n")
    if not transfers:
        print("NO TRANSFERS -- nothing was measured. This is not evidence that "
              "the client sends nothing; it is a corpus with no map change in it.")
        return 2

    print(f"c2s opcodes in the {W:.0f}s BEFORE a transfer, with the controls that "
          f"decide whether that means anything:\n")
    print(f"  {'opcode':>8}  {'pre':>5} {'post':>5} {'total':>6}  "
          f"{'pre/total':>9}  {'was LAST before':>15}")
    for op in sorted(set(pre) | set(post), key=lambda o: -pre[o]):
        share = pre[op] / total[op] if total[op] else 0.0
        print(f"  0x{op:04X}  {pre[op]:>5} {post[op]:>5} {total[op]:>6}  "
              f"{share:>8.1%}  {last_before[op]:>15}")

    print("\nHOW TO READ THIS. A high `pre` with a high `total` is the client's "
          "ordinary chatter landing near the transfer by arithmetic. The answer, "
          "if it is here, is an opcode with pre/total near 100% AND post near 0 "
          "-- fired only in the approach to a transfer and never after one.")

    # A 100%-concentrated opcode that precedes only SOME transfers is two
    # mechanisms, not one -- so split the transfers by whether it appeared and
    # ask where each group was going. The destination is the 0x0099
    # MAP_UPDATE_CURRENT the transfer tail carries (studies/smsg: the tail is
    # 0x0028 -> 0x01A5 -> 0x0099, 3/3).
    print(f"\nsplit by whether {hex(SIGNAL)} appeared, and where each group went:")
    groups = collections.defaultdict(collections.Counter)
    counts = collections.Counter()
    for stamp, conn, t0, tail, dest in detail:
        had = any(op == SIGNAL for _t, op in tail)
        counts[had] += 1
        groups[had][dest] += 1
    for had in (True, False):
        label = f"WITH {hex(SIGNAL)}" if had else f"WITHOUT {hex(SIGNAL)}"
        dests = ", ".join(f"map {d}×{n}" for d, n in groups[had].most_common())
        print(f"  {label:<16} {counts[had]:>3} transfer(s) -> {dests or '(no 0x0099 read)'}")

    print(f"\nthe last c2s message(s) before each transfer, and the destination:")
    for stamp, conn, t0, tail, dest in detail:
        seq = " ".join(f"0x{op:04X}@-{t0 - t:.2f}s" for t, op in tail) or "(none)"
        print(f"  {stamp} {conn.split('->')[0]:<22} t={t0:>8.2f} -> map "
              f"{str(dest):<6} {seq}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
