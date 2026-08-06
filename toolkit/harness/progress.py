"""Classify how far each game-channel session got, so run-to-run variance is a
measurement instead of an impression.

Two consecutive runs on identical code ended in different places -- one reached
INSTANCE_LOAD_REQUEST_SPAWN, the next stopped before REQUEST_ITEMS -- while
producing byte-identical screenshots. A loading screen at 100% looks the same
whether the client is mid-load or has quietly stopped asking for anything, so the
screenshot cannot tell those apart and the capture has to.

The ladder is the client's own request order. Each rung is a message only the
client sends, so reaching rung N means the client decided to advance, not that we
managed to send something.

    python toolkit/harness/progress.py                    # all game sessions
    python toolkit/harness/progress.py --last 8
"""

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vaultpath import vault_path  # noqa: E402

VAULTS = (vault_path("captures", "authsrv"),
          vault_path("captures", "gamesrv"))

# (opcode, short name), in the order the client sends them.
LADDER = [
    (0x000A, "sysinfo"),
    (0x008A, "armors"),
    (0x0091, "items"),
    (0x0088, "spawn"),
    (0x0090, "players"),
]
NAMES = {op: n for op, n in LADDER}


def read(path):
    ev = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    ev.append(json.loads(line))
                except json.JSONDecodeError:
                    pass          # a live capture can end mid-line
    return ev


def summarise(path):
    ev = read(path)
    ver = next((e for e in ev if e.get("kind") == "version"), None)
    if not ver or ver.get("channel") != "game":
        return None

    got, last_sent, ended = [], None, "open"
    for e in ev:
        k = e.get("kind")
        if k == "decoded" and e.get("opcode") in NAMES:
            got.append((NAMES[e["opcode"]], e.get("t", 0.0)))
        elif k == "sent":
            last_sent = (e.get("label", "?"), e.get("t", 0.0))
        elif k == "error":
            ended = "reset"

    # Rung = furthest rung actually reached, not the count: a client that skips
    # one and sends a later one has still got further than one that stopped.
    order = [n for _, n in LADDER]
    rung = max((order.index(n) + 1 for n, _ in got), default=0)
    return {
        "file": os.path.basename(path),
        "map_id": ver.get("map_id"),
        "rung": rung,
        "reached": order[rung - 1] if rung else "-",
        "got": got,
        "last_sent": last_sent,
        "ended": ended,
        "duration": ev[-1].get("t", 0.0) if ev else 0.0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--last", type=int, default=12)
    args = ap.parse_args()

    paths = []
    for v in VAULTS:
        paths += glob.glob(os.path.join(v, "*.jsonl"))
    paths.sort(key=os.path.getmtime)

    rows = [r for r in (summarise(p) for p in paths) if r][-args.last:]
    if not rows:
        print("no game-channel sessions found")
        return

    print(f"{'session':<34} {'map':>4} {'rung':>4}  {'reached':<8} "
          f"{'end':<6} {'dur':>7}  client messages")
    for r in rows:
        seq = " ".join(f"{n}@{t:.2f}" for n, t in r["got"]) or "(none)"
        print(f"{r['file']:<34} {r['map_id']:>4} {r['rung']:>4}  "
              f"{r['reached']:<8} {r['ended']:<6} {r['duration']:>6.1f}s  {seq}")

    # The distribution is the point: one run proves nothing about the next.
    hist = {}
    for r in rows:
        hist[r["reached"]] = hist.get(r["reached"], 0) + 1
    print("\nfurthest rung reached, over "
          f"{len(rows)} session(s):")
    for name in [n for _, n in LADDER] + ["-"]:
        if name in hist:
            print(f"  {name:<9} {hist[name]:>2}  {'#' * hist[name]}")

    stalls = [r for r in rows if r["rung"] and r["rung"] < len(LADDER) - 1]
    if stalls:
        print("\nlast thing we sent before each stall:")
        for r in stalls:
            lbl, t = r["last_sent"] or ("?", 0.0)
            print(f"  {r['reached']:<8} <- {lbl} @{t:.2f}s")


if __name__ == "__main__":
    main()
