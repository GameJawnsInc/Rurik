"""Read-only census: 0x002C sends by label class, and grants, per gamesrv capture
from the ROUTER-default commit onward (2026-09-03 18:39 .. 09-04). Prints only."""
import glob, json, os, collections, sys
root = "C:/gd/Rurik/vault/captures/gamesrv"
files = sorted(glob.glob(os.path.join(root, "authsrv-2026090[34]T*-c1.jsonl")))
files = [f for f in files if os.path.basename(f)[8:23] >= "20260903T183941"]
tot = collections.Counter(); grants = 0; ncap = 0; caps_with = 0
per = []
for f in files:
    c = collections.Counter(); g = 0; sends = 0
    with open(f, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try: r = json.loads(line)
            except Exception: continue
            if r.get("kind") != "sent": continue
            op = r.get("opcode")
            if op in (0x29, 0x2A): g += 1
            if op == 0x2C:
                lab = r.get("label", "")
                key = lab.split(" 0x002C")[0].split(":")[0][:28]
                c[key] += 1
    ncap += 1; grants += g; tot.update(c)
    if sum(c.values()): caps_with += 1
    per.append((os.path.basename(f)[8:23], g, dict(c)))
print("captures", ncap, "grants(0x29/0x2A)", grants, "caps with any 0x002C", caps_with)
print("0x002C by class:", dict(tot), "total", sum(tot.values()))
for p in per:
    if p[2]: print(p)
