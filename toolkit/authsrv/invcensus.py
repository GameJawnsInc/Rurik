r"""The inventory-registration census: 0x0144 vs 0x013F vs 0x0072, per connection.

Desk work for `studies/pvpui/FINDINGS.md` §26.1. Reads the decrypted live
captures and nothing else; writes nothing; launches nothing.

PREDICTIONS ON RECORD, stated before the first run (the probes.py rule):

  Static tracing (38797) says the 0x0144 ITEM_STREAM_CREATE handler is the
  ONLY direct caller of the inventoryTable insert, and the 0x013F bag handler
  ASSERTS its field-1 lookup succeeds (ItCliApi:1942) -- so every connection
  should show its 0x0144 BEFORE its bags, every 0x013F field 1 should equal
  that connection's 0x0144 field 1, and a hero on retail tape would appear as
  a SECOND 0x0144 with a distinct key echoed by 0x0072 field 3. What the
  first run found (2026-08-18): 38/38 connections carry exactly one
  0x0144 [key, 0], field 2 always 0, all nine bags citing the key; the key is
  an arbitrary per-connection handle (the same character drew 1, 23, 184, 188
  and 4 on different connections); and there are ZERO 0x0072 in the corpus --
  no retail hero activation exists to imitate.

BUILD POOLING: same rule as createburst.py -- origin must be "live" for every
connection or the run refuses, because this is a claim about ArenaNet's server.

    python toolkit/authsrv/invcensus.py            # the census, writes nothing
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import npcdefs  # noqa: E402
import tape  # noqa: E402
from codec import Codec  # noqa: E402

STREAM_CREATE = 0x0144
HERO_ACTIVATE = 0x0072
CREATE_BAG = 0x013F
OPS = {STREAM_CREATE: "STREAM_CREATE", HERO_ACTIVATE: "HERO_ACTIVATE",
       CREATE_BAG: "CREATE_BAG"}


def main():
    codec = Codec()
    connections = violations = 0
    for capture_dir in npcdefs.live_captures():
        for row in tape.channel_files(capture_dir):
            connection = row["connection"]
            info, events = tape.load_tape(capture_dir, connection)
            origin = info.get("origin", "unknown")
            if origin != "live":
                raise SystemExit(
                    f"{capture_dir} {connection}: origin={origin!r}. This "
                    f"census is a claim about ArenaNet's server; one non-live "
                    f"connection in the pool and every number is about "
                    f"something else.")
            msgs, receipt = tape.decode_all(events, codec, "GAME_SMSG", 0)
            consumed, total, err = receipt
            if err is not None or consumed != total:
                raise SystemExit(
                    f"{capture_dir} {connection} framed {consumed}/{total} "
                    f"({err}); a partial decode drops the tail silently.")
            cap = info.get("capture") or os.path.basename(capture_dir)
            hits = [(t, op, v) for (t, op, v) in msgs if op in OPS]
            if not hits:
                continue
            connections += 1
            print(f"== {cap} conn {connection}")
            counts = collections.Counter(op for _, op, _ in hits)
            print("   counts:", {OPS[o]: n for o, n in sorted(counts.items())})
            for t, op, v in hits:
                if op in (STREAM_CREATE, HERO_ACTIVATE):
                    print(f"   {t:10.3f} {OPS[op]} {v[1:]}")
            keys = {v[1] for _, op, v in hits if op == STREAM_CREATE}
            bags = collections.Counter(
                v[1] for _, op, v in hits if op == CREATE_BAG)
            if bags:
                print("   0x013F field1 ->", dict(sorted(bags.items())))
            orphans = {k: n for k, n in bags.items() if k not in keys}
            if orphans:
                violations += 1
                print(f"   [VIOLATION] bags keyed to no 0x0144: {orphans}")
    if not connections:
        raise SystemExit("zero decodable live connections: the census "
                         "measured nothing, which is a failure, not an "
                         "empty answer.")
    print(f"\n{connections} connection(s); "
          f"{violations} bag-before-registration violation(s)")
    if violations:
        raise SystemExit("the static model says ItCliApi:1942 makes an "
                         "orphan bag impossible; a violation above means the "
                         "model or the decode is wrong.")


if __name__ == "__main__":
    main()
