"""Read-only (M-F2 refuter): every agenttap tape 09-02..09-04, joined to its gamesrv capture by wall span.
Per tape: capture's KBD_SYNC_LEAD_ON flag, drawn-body (async, position_at live) per-sample jumps >150 u with dt
and the async raw velocity on the sample BEFORE the jump (clamp-artifact check), and movesync hard steps on the capture."""
import sys, os, json, glob, math
sys.path.insert(0, r"C:/gd/Rurik/toolkit"); sys.path.insert(0, r"C:/gd/Rurik/toolkit/clientscan")
import w0score, movesync
VAULT = r"C:/gd/Rurik/vault"
caps = []
for c in sorted(glob.glob(os.path.join(VAULT, "captures", "gamesrv", "authsrv-2026090[2-4]*-c1.jsonl"))):
    rows = []
    for l in open(c, encoding="utf-8", errors="replace"):
        try: rows.append(json.loads(l))
        except ValueError: pass
    w = [r["wall_unix"] for r in rows if "wall_unix" in r]
    fl = next((r for r in rows[:40] if r.get("kind") == "flags"), {})
    if w: caps.append((w[0], w[-1], c, fl))
tot = {"lead_on": [0, 0], "lead_off": [0, 0]}
for tp in sorted(glob.glob(os.path.join(VAULT, "research", "animref", "agenttap-2026090[2-4]*.jsonl"))):
    head = None; rows = []
    for line in open(tp, encoding="utf-8", errors="replace"):
        try: r = json.loads(line)
        except ValueError: continue
        if r.get("kind") == "head": head = r
        elif r.get("kind") == "sample": rows.append(r)
    if head is None: print(os.path.basename(tp), "unreadable"); continue
    t0 = head["t0"]; stamp = os.path.basename(tp)[9:24]
    m = [c for c in caps if c[0] - 5 <= t0 <= c[1]]
    if not m: print(f"{stamp}  NO CAPTURE"); continue
    w0, w1, cpath, fl = m[0]
    lead = fl.get("KBD_SYNC_LEAD_ON")
    prev = None; jumps = []
    for s in rows:
        a = (s.get("agents") or {}).get("1")
        if not a or not a.get("async") or "x" not in a["async"] or not a.get("sync") or "x" not in a["sync"]: continue
        b = w0score.live(a["async"], s.get("clock1"))
        vraw = math.hypot(a["async"].get("vx", 0) or 0, a["async"].get("vy", 0) or 0)
        if prev is not None:
            d = math.hypot(b[0]-prev[1][0], b[1]-prev[1][1]); dt = s["t"]-prev[0]
            if d > 150: jumps.append((round(s["t"],2), round(d), round(dt,3), round(prev[2],1), round(vraw,1)))
        prev = (s["t"], b, vraw)
    w = movesync.wire_only(cpath)
    key = "lead_on" if lead else "lead_off"
    tot[key][0] += 1; tot[key][1] += len(jumps)
    print(f"{stamp} cap={os.path.basename(cpath)[8:23]} LEAD_ON={str(lead):5} ROUTER={str(fl.get('ROUTER')):5} n={len(rows)} body_jumps>150={len(jumps)} {jumps[:4]}  wire hard={len(w['hard'])} active={w['den']['active']:.1f}s")
print("TOTAL tapes/jumps by lead flag:", tot)
