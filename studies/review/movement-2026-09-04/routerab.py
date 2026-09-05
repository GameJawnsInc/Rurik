"""Read-only reproduction attempt of the 2026-08-30 'router-ON 1.60/min vs router-OFF 2.44/min'
head-to-head: label every harness run by its gamesrv.log banner ([map] --router ON), join to a gamesrv
capture (report.json captures list, else nearest capture stamp within 180 s), score movesync's
two-arm hard bar over the active-time denominator, pool. Stdout only."""
import glob, json, os, sys, datetime as dt
sys.path.insert(0, r"C:/gd/Rurik/toolkit"); sys.path.insert(0, r"C:/gd/Rurik/toolkit/clientscan")
import movesync

caps = sorted(glob.glob(r"C:/gd/Rurik/vault/captures/gamesrv/authsrv-*-c1.jsonl"))
capstamps = {os.path.basename(c)[8:23]: c for c in caps}
def parse(s): return dt.datetime.strptime(s, "%Y%m%dT%H%M%S")
capkeys = sorted(capstamps)

def nearest(stamp):
    t = parse(stamp); best = None
    for k in capkeys:
        d = (parse(k) - t).total_seconds()
        if 0 <= d <= 180 and (best is None or d < best[0]):
            best = (d, k)
    return capstamps[best[1]] if best else None

rows = []
for d in sorted(glob.glob(r"C:/gd/Rurik/vault/captures/harness/*")):
    lg = os.path.join(d, "gamesrv.log"); rp = os.path.join(d, "report.json")
    if not os.path.exists(lg):
        continue
    txt = open(lg, encoding="utf-8", errors="replace").read()
    if "[map]" not in txt:
        continue
    router = "[map] --router ON" in txt
    cap = None; how = "report"
    if os.path.exists(rp):
        try:
            rep = json.load(open(rp, encoding="utf-8"))
            for c in rep.get("captures", []) or []:
                if "gamesrv" in c.replace("/", "\\") and c.endswith(".jsonl") and os.path.exists(c):
                    cap = c
        except Exception:
            pass
    if cap is None:
        cap = nearest(os.path.basename(d)); how = "nearest"
    if cap is None:
        rows.append(dict(run=os.path.basename(d), router=router, cap=None)); continue
    w = movesync.wire_only(cap)
    den = w["den"]; hard = w["hard"]
    rows.append(dict(run=os.path.basename(d), router=router, cap=os.path.basename(cap), how=how,
                     active=den["active"], hard=len(hard), maxd=max((r["dist"] for r in hard), default=0.0),
                     refuse=w["refuse_all"], intervals=den["intervals"]))

def rate(n, s): return 60.0*n/s if s > 0 else float("nan")
print("ROUTER-ON runs (banner):")
for r in rows:
    if r["router"]:
        print("  ", r["run"], r.get("cap"), r.get("how"), "active %.1f hard %d maxd %.0f refuse %s" % (r.get("active", 0), r.get("hard", 0), r.get("maxd", 0), r.get("refuse")) if r.get("cap") else "NO CAPTURE JOINED")

def group(name, pred):
    g = [r for r in rows if r.get("cap") and pred(r)]
    h = sum(r["hard"] for r in g); a = sum(r["active"] for r in g)
    print(f"{name:55s} runs={len(g):4d} hard={h:3d} active={a/60:7.2f}min pooled={rate(h,a):5.2f}/act-min maxd={max((r['maxd'] for r in g), default=0):5.0f} unjoined={sum(1 for r in rows if pred(r) and not r.get('cap'))}")
print()
group("router ON, all banner runs", lambda r: r["router"])
group("router OFF, all banner runs", lambda r: not r["router"])
group("router ON, runs <= 20260830", lambda r: r["router"] and r["run"] <= "20260830T235959")
group("router OFF, runs <= 20260830", lambda r: (not r["router"]) and r["run"] <= "20260830T235959")
group("router OFF, runs >= 20260826 and <= 20260830", lambda r: (not r["router"]) and "20260826" <= r["run"] <= "20260830T235959")
group("router OFF, runs >= 20260819 and <= 20260830", lambda r: (not r["router"]) and "20260819" <= r["run"] <= "20260830T235959")
