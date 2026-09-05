#!/usr/bin/env python3
"""Is pressharm's join sample already POST-SET?

For each pin: the index pressharm uses (last tape sample with T0+t <= pin wall_unix),
the SYNC copy's distance to the pin at that sample (0 => the hard set has ALREADY
landed in this sample), the ASYNC copy's distance, and the same one and two samples
earlier.  Read-only, prints only.
"""
import json, os, struct, sys

TREE = r"C:/gd/Rurik"
sys.path.insert(0, os.path.join(TREE, "toolkit"))
sys.path.insert(0, os.path.join(TREE, "toolkit", "clientscan"))
from w0score import live, load  # noqa

rows = [json.loads(l) for l in open(
    TREE + "/vault/captures/gamesrv/authsrv-20260903T084616-c1.jsonl", encoding="utf-8") if l.strip()]
pins = [r for r in rows if r.get("kind") == "sent" and r.get("opcode") == 0x2C]
head, samples = load(TREE + "/vault/research/animref/agenttap-20260903T084632.jsonl")
T0 = head["t0"]
W0 = rows[0]["wall_unix"]
hyp = lambda a, b: ((a[0]-b[0])**2 + (a[1]-b[1])**2) ** 0.5
pt = lambda r: struct.unpack_from("<ff", bytes.fromhex(r["plain"]), 6)


def c(s, key, live_=False):
    a = s["agents"]["1"][key]
    return live(a, s.get("clock0" if key == "sync" else "clock1")) if live_ else (a["x"], a["y"])


print("pin  send_t   join_idx  join_t   dt(join-send)  syncD@join  asyncD@join  "
      "syncD@-1  asyncD@-1  syncD@-2  asyncD@-2")
post = 0
for j, r in enumerate(pins):
    W = r["wall_unix"]
    idx = max(i for i, s in enumerate(samples) if T0 + s["t"] <= W)
    p = pt(r)
    row = [idx, T0 + samples[idx]["t"] - W0, T0 + samples[idx]["t"] - W]
    ds = []
    for k in (0, -1, -2):
        if idx + k < 0:
            ds += [float("nan")] * 2
            continue
        ds.append(hyp(c(samples[idx+k], "sync"), p))
        ds.append(hyp(c(samples[idx+k], "async"), p))
    if ds[0] < 1.0:
        post += 1
    print("%2d  %7.3f   %5d   %7.3f   %+7.3f      %8.1f %10.1f %9.1f %10.1f %9.1f %10.1f"
          % (j+1, r["t"] - rows[0]["t"], row[0], row[1], row[2], *ds))
print("\n%d of %d join samples already have the SYNC copy ON the pin (< 1 u) -- "
      "i.e. the hard set had already landed when the 'body at the press' was read." % (post, len(pins)))
