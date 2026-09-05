"""Read-only, prints only.
(1) Retail s2c 0x002C naming the PLAYER (routerbench.player_agent attribution) over the live corpus,
    split by whether the player reported a 0x003D within the previous 2.5 s (a walking body).
(2) The 0x003D inter-report gap restricted to TRUE CRUISE pairs (implied speed >= 250 u/s), retail vs ours,
    so the heartbeat cluster (slow/maneuvering) cannot hide the cruise trigger.
"""
import sys, os, math, glob, collections
sys.path.insert(0, r"C:\gd\Rurik\toolkit")
sys.path.insert(0, r"C:\gd\Rurik\toolkit\authsrv")
sys.path.insert(0, r"C:\gd\Rurik\toolkit\clientscan")
import livewire, leadmargin, vaultpath, routerbench

OP_REPORT, OP_STOP, OP_CLICK, OP_UPDPOS = 61, 71, 62, 44

def q(v, f):
    if not v: return float('nan')
    s = sorted(v); return s[min(len(s)-1, int(round(f*(len(s)-1))))]

def pairs(merged, cos_tol=0.9998):
    out = []; prev = None
    for t, d, op, v in merged:
        if d != "c2s": continue
        if op in (OP_STOP, OP_CLICK): prev = None; continue
        if op != OP_REPORT: continue
        try:
            pos = (float(v[1][0]), float(v[1][1])); vec = (float(v[3][0]), float(v[3][1])); mt = int(v[4])
        except Exception: continue
        m = math.hypot(*vec)
        if prev and prev["mt"] == mt and mt != 0 and m > 1 and prev["m"] > 1:
            dot = (vec[0]*prev["vec"][0] + vec[1]*prev["vec"][1])/(m*prev["m"])
            dd = math.dist(pos, prev["pos"]); dt = t - prev["t"]
            if dot > cos_tol and dt > 0: out.append((dt, dd, mt, dd/dt))
        prev = {"t": t, "pos": pos, "vec": vec, "m": m, "mt": mt}
    return out

def cruise(label, ps):
    c = [p for p in ps if 250.0 <= p[3] <= 320.0]
    dts = [p[0] for p in c]; ds = [p[1] for p in c]
    h = collections.Counter()
    for dt in dts:
        h["<0.6" if dt < 0.6 else "0.6-1.5" if dt < 1.5 else "1.5-2.0" if dt < 2.0 else ">=2.0"] += 1
    print(f"{label}: cruise pairs (250<=v<=320) n={len(c)}: dt p50 {q(dts,.5):.3f} p90 {q(dts,.9):.3f}; chord p50 {q(ds,.5):.1f} p90 {q(ds,.9):.1f}; bins {dict(sorted(h.items()))}")

tot2c = 0; to_player = 0; to_player_walking = 0; conns = 0; attributed = 0
live_pairs = []
per_conn = []
for capdir, conn_file in livewire.live_connections():
    conn, merged, ok = livewire.decode_conn(capdir, conn_file)
    if not ok: continue
    conns += 1
    live_pairs += pairs(merged)
    pid, votes = routerbench.player_agent(merged)
    if pid is None: continue
    attributed += 1
    reports = [t for t, d, op, v in merged if d == "c2s" and op == OP_REPORT]
    n2c = 0; np = 0; npw = 0
    ri = 0
    for t, d, op, v in merged:
        if d == "s2c" and op == OP_UPDPOS:
            n2c += 1
            try: aid = v[1]
            except Exception: continue
            if aid == pid:
                np += 1
                while ri < len(reports) and reports[ri] <= t: ri += 1
                last = reports[ri-1] if ri > 0 else None
                if last is not None and t - last <= 2.5: npw += 1
    tot2c += n2c; to_player += np; to_player_walking += npw
    per_conn.append((os.path.basename(capdir), conn_file[:40], pid, n2c, np, npw, len(reports)))
print(f"live conns ok {conns}, player-attributed {attributed}")
print(f"s2c 0x002C total {tot2c}; naming the player {to_player}; of those within 2.5 s after a player 0x003D: {to_player_walking}")
for row in per_conn:
    if row[4]: print("  ", row)
cruise("RETAIL", live_pairs)

gs = sorted(glob.glob(os.path.join(vaultpath.vault_root(), "captures", "gamesrv", "authsrv-2026090[234]T*-c1.jsonl")))
ours = []
for p in gs:
    merged = []
    for r in leadmargin.read_rows(p):
        if r.get("kind") != "decoded": continue
        op = r.get("opcode")
        if op in (0x3D, 0x47, 0x3E):
            try: merged.append((float(r["t"]), "c2s", op, r["values"]))
            except Exception: pass
    ours += pairs(merged)
cruise("OURS 09-02..04", ours)
