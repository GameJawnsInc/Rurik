"""Read-only warp census over gamesrv captures: movesync two-arm hard bar per active minute,
grouped by the capture's own flags banner. Writes NOTHING (stdout only)."""
import glob, json, os, sys, math, collections
sys.path.insert(0, r"C:/gd/Rurik/toolkit")
sys.path.insert(0, r"C:/gd/Rurik/toolkit/clientscan")
import movesync

SINCE = sys.argv[1] if len(sys.argv) > 1 else "20260828"
caps = sorted(glob.glob(r"C:/gd/Rurik/vault/captures/gamesrv/authsrv-*-c1.jsonl"))
caps = [c for c in caps if os.path.basename(c)[8:16] >= SINCE]
harness = {}
for rp in glob.glob(r"C:/gd/Rurik/vault/captures/harness/*/report.json"):
    try:
        rep = json.load(open(rp, encoding="utf-8"))
    except Exception:
        continue
    for c in rep.get("captures", []) or []:
        b = os.path.basename(c)
        if b.startswith("authsrv-") and "gamesrv" in c.replace("/", "\\"):
            harness[b[8:23]] = os.path.basename(os.path.dirname(rp))

def stamp_of(path):
    return os.path.basename(path)[8:23]

def is_harness(stamp):
    return harness.get(stamp)

KEYS = ["ROUTER", "KBD_SYNC", "A2_LEAD_PLANE_CLIP", "ROUTER_SEAM_CLIP", "A2_LEAD_SEAM_CLIP",
        "AGTRACK_GATE2_SEAM", "A2_LEAD_ORIGIN_SEAM", "AGTRACK_REPIN", "KBD_LEAD", "D1_LEAD",
        "RESYNC", "agtrack_guard.STATIONARY_WAIVER"]

def flags_of(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if '"flags"' in line:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("kind") == "flags":
                    return r
            if i > 30:
                break
    return None

rows = []
for c in caps:
    st = stamp_of(c)
    fl = flags_of(c) or {}
    try:
        w = movesync.wire_only(c)
    except Exception as e:
        print("ERR", st, e)
        continue
    den = w["den"]
    hard = w["hard"]
    mx = max((r["dist"] for r in hard), default=0.0)
    mxe = max((movesync.excess(r) for r in hard), default=0.0)
    rows.append(dict(stamp=st, harness=is_harness(st), flags={k: fl.get(k, "ABSENT") for k in KEYS},
                     reports=den["reports"], intervals=den["intervals"], span=den["span"],
                     active=den["active"], hard=len(hard), maxd=mx, maxexc=mxe,
                     refuse=w["refuse_all"], nsent=w["grants"]))

def rate(n, sec):
    return 60.0 * n / sec if sec > 0 else float("nan")

print("stamp            harn  ROUT KBDS PLNC SEAMR SEAML GATE2 ORIG REPIN  reps  intv  span   active  hard  rate/actmin  maxd   maxexc")
for r in rows:
    f = r["flags"]
    def s(k):
        v = f[k]
        return {"ABSENT": "-", True: "T", False: "F", None: "n"}.get(v, str(v)[:3])
    print(f"{r['stamp']} {'H' if r['harness'] else 'op':4} {s('ROUTER'):4} {s('KBD_SYNC'):4} {s('A2_LEAD_PLANE_CLIP'):4} {s('ROUTER_SEAM_CLIP'):5} {s('A2_LEAD_SEAM_CLIP'):5} {s('AGTRACK_GATE2_SEAM'):5} {s('A2_LEAD_ORIGIN_SEAM'):4} {s('AGTRACK_REPIN'):5} {r['reports']:5d} {r['intervals']:5d} {r['span']:6.0f} {r['active']:7.1f} {r['hard']:4d} {rate(r['hard'], r['active']):8.2f}{'*' if r['refuse'] else ' '}  {r['maxd']:6.0f} {r['maxexc']:6.0f}")

def group(name, pred):
    g = [r for r in rows if pred(r)]
    n = len(g); h = sum(r["hard"] for r in g); a = sum(r["active"] for r in g)
    ok = [r for r in g if not r["refuse"]]
    mx = max((r["maxd"] for r in g), default=0.0)
    hs = sum(1 for r in g if r["harness"])
    print(f"{name:70s} caps={n:3d} (harness {hs}, operator {n-hs}) hard={h:3d} active={a/60:7.2f} min  pooled {rate(h,a):5.2f}/act-min  max_disp={mx:6.0f} u  (unrefused caps {len(ok)})")

print()
print("=== GROUPS (pooled: sum hard / sum active minutes) ===")
group("ALL since " + SINCE, lambda r: True)
group("2026-08-30 only", lambda r: r["stamp"].startswith("20260830"))
group("2026-08-30 ROUTER=T", lambda r: r["stamp"].startswith("20260830") and r["flags"]["ROUTER"] is True)
group("2026-08-30 ROUTER=F", lambda r: r["stamp"].startswith("20260830") and r["flags"]["ROUTER"] is False)
group("08-28..09-02 ROUTER=T", lambda r: r["stamp"] < "20260903" and r["flags"]["ROUTER"] is True)
group("08-28..09-02 ROUTER=F", lambda r: r["stamp"] < "20260903" and r["flags"]["ROUTER"] is False)
group("pre-1z-t (< 2026-09-03) all", lambda r: r["stamp"] < "20260903")
group("KBD_SYNC=T & ROUTER=T (world-0 sync + router)", lambda r: r["flags"]["KBD_SYNC"] is True and r["flags"]["ROUTER"] is True)
group("... & A2_LEAD_PLANE_CLIP=T (plane clip)", lambda r: r["flags"]["KBD_SYNC"] is True and r["flags"]["ROUTER"] is True and r["flags"]["A2_LEAD_PLANE_CLIP"] is True)
group("... & ROUTER_SEAM_CLIP=T (seam rays)", lambda r: r["flags"]["KBD_SYNC"] is True and r["flags"]["ROUTER"] is True and r["flags"]["A2_LEAD_PLANE_CLIP"] is True and r["flags"]["ROUTER_SEAM_CLIP"] is True)
group("... & AGTRACK_GATE2_SEAM=T (guard fix)", lambda r: r["flags"]["KBD_SYNC"] is True and r["flags"]["ROUTER"] is True and r["flags"]["A2_LEAD_PLANE_CLIP"] is True and r["flags"]["ROUTER_SEAM_CLIP"] is True and r["flags"]["AGTRACK_GATE2_SEAM"] is True)
group("... & A2_LEAD_ORIGIN_SEAM=T (lead origin)", lambda r: r["flags"]["KBD_SYNC"] is True and r["flags"]["ROUTER"] is True and r["flags"]["A2_LEAD_PLANE_CLIP"] is True and r["flags"]["ROUTER_SEAM_CLIP"] is True and r["flags"]["AGTRACK_GATE2_SEAM"] is True and r["flags"]["A2_LEAD_ORIGIN_SEAM"] is True)
group("2026-09-04 all", lambda r: r["stamp"].startswith("20260904"))
group("2026-09-04 harness", lambda r: r["stamp"].startswith("20260904") and r["harness"])
group("2026-09-04 operator", lambda r: r["stamp"].startswith("20260904") and not r["harness"])
group("2026-09-03..04 harness", lambda r: r["stamp"] >= "20260903" and r["harness"])
group("2026-09-03..04 operator", lambda r: r["stamp"] >= "20260903" and not r["harness"])
group("since 09-01 all", lambda r: r["stamp"] >= "20260901")
group("since 09-01 harness", lambda r: r["stamp"] >= "20260901" and r["harness"])
group("since 09-01 operator", lambda r: r["stamp"] >= "20260901" and not r["harness"])
print()
print("per-capture median rate (unrefused, active>60s), groups:")
for name, pred in [("ROUTER=F pre-09-03", lambda r: r["stamp"] < "20260903" and r["flags"]["ROUTER"] is False),
                   ("ROUTER=T pre-09-03", lambda r: r["stamp"] < "20260903" and r["flags"]["ROUTER"] is True),
                   ("09-03..04 seam+plane+sync+router", lambda r: r["stamp"] >= "20260903" and r["flags"]["ROUTER_SEAM_CLIP"] is True and r["flags"]["A2_LEAD_PLANE_CLIP"] is True)]:
    g = sorted(rate(r["hard"], r["active"]) for r in rows if pred(r) and not r["refuse"] and r["active"] > 60)
    if g:
        print(f"  {name:40s} n={len(g)} median={g[len(g)//2]:.2f} max={g[-1]:.2f} zeros={sum(1 for x in g if x==0)}")
    else:
        print(f"  {name:40s} n=0")
