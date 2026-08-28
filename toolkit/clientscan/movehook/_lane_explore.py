"""Scratch exploration for the straight-line lane. Not a published tool."""
import os
import sys
import struct
import math

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
import readhook  # noqa: E402

BIN = r"C:/gd/Rurik/vault/research/movecode/r2/movehook.bin"
cap = readhook.Capture(BIN)
names = readhook.site_names(cap)
f = readhook._f

LOCAL = 0x21B3D158
SYNC = 0x21B3EC40


def nm(r):
    return names[r["site"]] if r["site"] < len(names) else str(r["site"])


for i, r in enumerate(cap.recs):
    r["_i"] = i

# --- tick vs ptime relation ------------------------------------------------
pairs = [(r["tick"], r["ptime"]) for r in cap.recs if r.get("have_agent")]
d = sorted(p - t for t, p in pairs)
print(f"ptime - tick over {len(d)} agent records: "
      f"min {d[0]}  p10 {d[len(d)//10]}  p50 {d[len(d)//2]}  "
      f"p90 {d[9*len(d)//10]}  max {d[-1]}")

# --- the displacements -----------------------------------------------------
print("\nDISPLACEMENTS (same object, m_point moved >1u, ptime unchanged):")
objs = {}
for r in cap.recs:
    if r.get("have_agent"):
        objs.setdefault(r["ecx"], []).append(r)
disp = []
for addr, seq in objs.items():
    for k in range(1, len(seq)):
        p, q = seq[k - 1], seq[k]
        if q["ptime"] != p["ptime"]:
            continue
        dd = math.hypot(f(q["point"][0]) - f(p["point"][0]),
                        f(q["point"][1]) - f(p["point"][1]))
        if not (math.isfinite(dd) and dd > 1.0):
            continue
        disp.append((addr, p, q, dd))
disp.sort(key=lambda t: -t[3])
for addr, p, q, dd in disp:
    print(f"  0x{addr:08X} {dd:8.1f} u  prev #{p['_i']} {nm(p):10} tick {p['tick']} "
          f"ptime {p['ptime']} pt=({f(p['point'][0]):.0f},{f(p['point'][1]):.0f})")
    print(f"                          land #{q['_i']} {nm(q):10} tick {q['tick']} "
          f"ptime {q['ptime']} pt=({f(q['point'][0]):.0f},{f(q['point'][1]):.0f}) "
          f"seg=({f(q['segment'][0]):.0f},{f(q['segment'][1]):.0f}) "
          f"tgt=({f(q['target'][0]):.0f},{f(q['target'][1]):.0f}) stop={q['stop']}")

# --- mapfindpath queries ---------------------------------------------------
print("\nMAPFINDPATH queries:")
idx = {n: i for i, n in enumerate(names)}
sbase = readhook.static_base()
for r in cap.recs:
    if r["site"] != idx.get("mapfindpath"):
        continue
    hp = r.get("have_pts", 0)
    a, b = r.get("pt_a"), r.get("pt_b")
    sa = f"({f(a[0]):9.1f},{f(a[1]):9.1f},{f(a[2]):8.1f})" if hp & 1 else "NONE"
    sb = f"({f(b[0]):9.1f},{f(b[1]):9.1f},{f(b[2]):8.1f})" if hp & 2 else "NONE"
    ret = r["retaddr"] - cap.base + sbase
    print(f"  #{r['_i']:<5} tick {r['tick']}  ret 0x{ret:08X}  rng {f(r['arg3']):.1f}"
          f"  {sa} -> {sb}")

print("\nCHCLI_POINT calls:")
for r in cap.recs:
    if r["site"] != idx.get("chcli_point"):
        continue
    hp = r.get("have_pts", 0)
    a, b = r.get("pt_a"), r.get("pt_b")
    sa = f"({f(a[0]):9.1f},{f(a[1]):9.1f})" if hp & 1 else "NONE"
    sb = f"({f(b[0]):9.1f},{f(b[1]):9.1f})" if hp & 2 else "NONE"
    ret = r["retaddr"] - cap.base + sbase
    print(f"  #{r['_i']:<5} tick {r['tick']}  ret 0x{ret:08X} "
          f"a1=0x{r['arg1']:08X} a2=0x{r['arg2']:08X} a3=0x{r['arg3']:08X} "
          f"{sa} -> {sb}")
