import os, sys, struct
ROOT = "C:/gd/Rurik"
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "mapdata"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "clientscan", "movehook"))
import readhook, pathdiff
from pathmap import PathingMap, _nearest_on_trapezoid

def f(dw): return struct.unpack("<f", struct.pack("<I", dw))[0]

def nearest_of_plane(pm, x, y, plane):
    best = None
    for t in pm.trapezoids:
        if t.plane != plane: continue
        d = _nearest_on_trapezoid(t, x, y)[2]
        if best is None or d < best: best = d
    return best

def nearest_any(pm, x, y):
    best = None
    for t in pm.trapezoids:
        d = _nearest_on_trapezoid(t, x, y)[2]
        if best is None or d < best: best = d
    return best

def run(label, binpath, fid, verbose_all=False):
    cap = readhook.Capture(binpath)
    names = readhook.site_names(cap)
    pairs, orphan, esp_bad = readhook._pair_mfp(cap, names)
    sbase = readhook.static_base()
    def reb(va): return va - cap.base + sbase if va >= cap.base else va
    pm = PathingMap.load(fid)
    print(f"\n===== {label}: {binpath} map 0x{fid:X}; pairs={len(pairs)} orphan={orphan} esp_bad={esp_bad}")
    tally = {"match":[0,0], "mismatch":[0,0], "offmesh":[0,0]}
    rows = []
    for ent, ret in pairs:
        if not (ret.get("have_out",0) & 1):
            print("  UNREADABLE", ent["seq"]); continue
        pc = ret["out_count"]
        a = ent.get("pt_a"); hp = ent.get("have_pts",0)
        if not ((hp & 1) and a):
            print("  no src", ent["seq"]); continue
        x, y, pl = f(a[0]), f(a[1]), a[2]
        offered = sorted({t.plane for t in pm.containing(x, y)})
        if not offered: cls = "offmesh"
        elif pl in offered: cls = "match"
        else: cls = "mismatch"
        tally[cls][0] += 1
        if pc == 0: tally[cls][1] += 1
        if cls != "match" or verbose_all:
            dpl = nearest_of_plane(pm, x, y, pl)
            dany = nearest_any(pm, x, y)
            near1 = sorted({t.plane for t in pm._near(x, y, 1.0)})
            rows.append((ent["seq"], reb(ret.get("retaddr",0)), cls, x, y, pl, offered, pc, dpl, dany, near1, pm.on_mesh(x,y)))
    for k,v in tally.items():
        print(f"  {k:9s} n={v[0]:4d} pathCount==0: {v[1]}")
    print("  seq  retaddr     class    x          y        decl offered pathCount  d(decl plane)  d(any)  near1u on_mesh")
    for r in rows:
        print(f"  {r[0]:5d} 0x{r[1]:08X} {r[2]:8s} {r[3]:10.2f} {r[4]:10.2f} {r[5]:4d} {str(r[6]):8s} {r[7]:3d}   {r[8] if r[8] is None else round(r[8],2)!s:>10}  {round(r[9],2):8}  {str(r[10]):8s} {r[11]}")

V = os.path.join(ROOT, "vault", "research", "movecode")
run("R7", os.path.join(V, "r7", "movehook.bin"), 0x287B3)
run("1zBD run1", os.path.join(V, "1zbd-run1", "movehook.bin"), 0x1B97D, verbose_all=True)
run("1zBD run2", os.path.join(V, "1zbd-run2", "movehook.bin"), 0x1B97D, verbose_all=True)
