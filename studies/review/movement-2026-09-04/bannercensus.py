"""Read-only: label harness runs by their gamesrv.log banner (--router ON present?) and by whether
the walk script drove keys/clicks, join to their gamesrv capture, score movesync's two-arm hard bar
per active minute. Stdout only."""
import glob, json, os, sys, re
sys.path.insert(0, r"C:/gd/Rurik/toolkit"); sys.path.insert(0, r"C:/gd/Rurik/toolkit/clientscan")
import movesync

rows = []
for d in sorted(glob.glob(r"C:/gd/Rurik/vault/captures/harness/*")):
    rp = os.path.join(d, "report.json"); lg = os.path.join(d, "gamesrv.log")
    if not os.path.exists(rp):
        continue
    try:
        rep = json.load(open(rp, encoding="utf-8"))
    except Exception:
        continue
    cap = None
    for c in rep.get("captures", []) or []:
        if "gamesrv" in c.replace("/", "\\") and c.endswith(".jsonl"):
            cap = c
    if not cap or not os.path.exists(cap):
        continue
    banner = None
    router = None
    if os.path.exists(lg):
        txt = open(lg, encoding="utf-8", errors="replace").read()
        banner = ("[map]" in txt)
        router = ("--router ON" in txt)
    walk = rep.get("walk") or []
    keys = sum(1 for w in walk if w.get("kind") == "key")
    clicks = sum(1 for w in walk if w.get("kind") in ("click", "clickat", "aim"))
    scripted = (keys + clicks) > 0
    st = os.path.basename(cap)[8:23]
    try:
        w = movesync.wire_only(cap)
    except Exception as e:
        print("ERR", st, e); continue
    den = w["den"]; hard = w["hard"]
    rows.append(dict(run=os.path.basename(d), stamp=st, banner=banner, router=router, keys=keys, clicks=clicks,
                     scripted=scripted, active=den["active"], span=den["span"], intervals=den["intervals"],
                     hard=len(hard), maxd=max((r["dist"] for r in hard), default=0.0), refuse=w["refuse_all"]))

def rate(n, s): return 60.0*n/s if s > 0 else float("nan")
print("run             stamp            banner router keys clicks scripted  span active hard rate  maxd")
for r in rows:
    print(f"{r['run']} {r['stamp']} {str(r['banner']):6} {str(r['router']):6} {r['keys']:4d} {r['clicks']:5d} {str(r['scripted']):8} {r['span']:5.0f} {r['active']:6.1f} {r['hard']:3d} {rate(r['hard'],r['active']):6.2f}{'*' if r['refuse'] else ' '} {r['maxd']:5.0f}")

def group(name, pred):
    g = [r for r in rows if pred(r)]
    h = sum(r["hard"] for r in g); a = sum(r["active"] for r in g)
    print(f"{name:60s} runs={len(g):3d} hard={h:3d} active={a/60:6.2f}min pooled={rate(h,a):5.2f}/act-min maxd={max((r['maxd'] for r in g), default=0):5.0f}")
print()
group("harness runs with gamesrv.log banner, --router ON", lambda r: r["banner"] and r["router"])
group("harness runs with gamesrv.log banner, router OFF", lambda r: r["banner"] and r["router"] is False)
group("  ...router ON, stamp <= 20260830", lambda r: r["banner"] and r["router"] and r["stamp"] <= "20260830T235959")
group("  ...router OFF, stamp <= 20260830", lambda r: r["banner"] and r["router"] is False and r["stamp"] <= "20260830T235959")
group("harness runs, no banner in log", lambda r: not r["banner"])
group("since 09-01: scripted (keys/clicks in walk)", lambda r: r["stamp"] >= "20260901" and r["scripted"])
group("since 09-01: harness-launched, operator-driven (no walk steps)", lambda r: r["stamp"] >= "20260901" and not r["scripted"])
group("09-03..04: scripted", lambda r: r["stamp"] >= "20260903" and r["scripted"])
group("09-03..04: harness-launched, operator-driven", lambda r: r["stamp"] >= "20260903" and not r["scripted"])
