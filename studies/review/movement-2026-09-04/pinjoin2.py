#!/usr/bin/env python3
"""Independent re-derivation: can ANY join rule over agenttap-20260903T084632 x
authsrv-20260903T084616-c1 produce 1z-u.6's 13.8/19.5/83.8/30.2/96.9/57.4/0.3/86.5/0.2/39.2?

Read-only. Prints only. Scratch, not in the tree.
"""
import glob, json, os, struct, sys

TREE = r"C:/gd/Rurik"
sys.path.insert(0, os.path.join(TREE, "toolkit"))
sys.path.insert(0, os.path.join(TREE, "toolkit", "clientscan"))
from w0score import live, load  # noqa

CAP = os.path.join(TREE, "vault/captures/gamesrv/authsrv-20260903T084616-c1.jsonl")
TAP = os.path.join(TREE, "vault/research/animref/agenttap-20260903T084632.jsonl")
TARGET = [13.8, 19.5, 83.8, 30.2, 96.9, 57.4, 0.3, 86.5, 0.2, 39.2]


def hyp(a, b):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


rows = [json.loads(l) for l in open(CAP, encoding="utf-8") if l.strip()]
pins = [r for r in rows if r.get("kind") == "sent" and r.get("opcode") == 0x2C]
head, samples = load(TAP)
t0cap = rows[0]["t"]
T0 = head["t0"]


def raw(s, key):
    a = (s.get("agents") or {}).get("1") or {}
    c = a.get(key)
    if not c or "x" not in c:
        return None
    return (c["x"], c["y"])


def livep(s, key, clk):
    a = (s.get("agents") or {}).get("1") or {}
    c = a.get(key)
    if not c or "x" not in c:
        return None
    return live(c, s.get(clk))


def pinpt(r):
    b = bytes.fromhex(r["plain"])
    return struct.unpack_from("<ff", b, 6)


print("sample count", len(samples), "t0 offset", T0 - rows[0]["wall_unix"])

# world-0 jump detector: consecutive raw sync displacement
jumps = []
for i in range(1, len(samples)):
    a, b = raw(samples[i - 1], "sync"), raw(samples[i], "sync")
    if a and b:
        d = hyp(a, b)
        if d > 1.0:
            jumps.append((i, d, T0 + samples[i]["t"]))
print("world-0 raw jumps >1u:", len(jumps))
for i, d, w in jumps[:40]:
    print("   idx %3d  d=%8.1f  capt=%7.3f" % (i, d, w - rows[0]["wall_unix"]))

rules = {}


def emit(name, vals):
    rules[name] = vals


# rule A: |pin - sync raw| at last sample <= pin wall
# rule B: |pin - sync live|
# rule C: |pin - async raw|
# rule D: |pin - async live|  (= pressharm)
for key, mode in (("sync", "raw"), ("sync", "live"), ("async", "raw"), ("async", "live")):
    vals = []
    for r in pins:
        W = r["wall_unix"]
        before = [s for s in samples if T0 + s["t"] <= W]
        if not before:
            vals.append(None); continue
        s = before[-1]
        p = raw(s, key) if mode == "raw" else livep(s, key, "clock0" if key == "sync" else "clock1")
        vals.append(None if p is None else hyp(p, pinpt(r)))
    emit("pin vs %s %s (last sample <= pin)" % (key, mode), vals)

# rule E/F: last sample BEFORE the world-0 jump that FOLLOWS the pin
for key, mode in (("sync", "raw"), ("async", "raw"), ("async", "live")):
    vals = []
    for r in pins:
        W = r["wall_unix"]
        nxt = [j for j in jumps if j[2] > W]
        if not nxt:
            vals.append(None); continue
        idx = nxt[0][0]
        s = samples[idx - 1]
        p = raw(s, key) if mode == "raw" else livep(s, key, "clock1")
        vals.append(None if p is None else hyp(p, pinpt(r)))
    emit("pin vs %s %s (last sample before NEXT w0 jump)" % (key, mode), vals)

# rule G: body displacement across the pin: sample before pin -> sample after pin
for key in ("sync", "async"):
    vals = []
    for r in pins:
        W = r["wall_unix"]
        before = [s for s in samples if T0 + s["t"] <= W]
        after = [s for s in samples if T0 + s["t"] > W]
        if not before or not after:
            vals.append(None); continue
        a, b = raw(before[-1], key), raw(after[0], key)
        vals.append(None if not a or not b else hyp(a, b))
    emit("%s displacement across pin (prev->next sample)" % key, vals)

# rule H: displacement across the following w0 jump, both copies
for key in ("sync", "async"):
    vals = []
    for r in pins:
        W = r["wall_unix"]
        nxt = [j for j in jumps if j[2] > W]
        if not nxt:
            vals.append(None); continue
        idx = nxt[0][0]
        a, b = raw(samples[idx - 1], key), raw(samples[idx], key)
        vals.append(None if not a or not b else hyp(a, b))
    emit("%s displacement across next w0 jump" % key, vals)

# rule I: async(before pin) vs sync(after pin) -- cross-copy
vals = []
for r in pins:
    W = r["wall_unix"]
    before = [s for s in samples if T0 + s["t"] <= W]
    after = [s for s in samples if T0 + s["t"] > W]
    if not before or not after:
        vals.append(None); continue
    a, b = raw(before[-1], "async"), raw(after[0], "sync")
    vals.append(None if not a or not b else hyp(a, b))
emit("async(before pin) vs sync(after pin)", vals)

# rule J: the two copies' separation at the pin
vals = []
for r in pins:
    W = r["wall_unix"]
    before = [s for s in samples if T0 + s["t"] <= W]
    if not before:
        vals.append(None); continue
    a, b = raw(before[-1], "async"), raw(before[-1], "sync")
    vals.append(None if not a or not b else hyp(a, b))
emit("copy separation at pin (async vs sync)", vals)

fmt = lambda v: "  --  " if v is None else "%6.1f" % v
print("\nTARGET (1z-u.6):", " ".join("%6.1f" % v for v in TARGET))
for name, vals in rules.items():
    line = " ".join(fmt(v) for v in vals)
    hit = sum(1 for a, b in zip(vals, TARGET) if a is not None and abs(a - b) < 0.6)
    print("%-52s %s   match %d/10" % (name[:52], line, hit))
