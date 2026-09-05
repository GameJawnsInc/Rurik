"""Read-only: retail's c2s 0x003D inter-report gap and chord during same-heading cruise,
measured directly on the live corpus through livewire.decode_conn, with the SAME pairing
rule leadmargin.cruise_chords uses on our captures (same movementType != 0, heading cosine
> 0.9998, no 0x0047 between), but with NO min_gap so the whole gap distribution is shown.
Then the same rule over our 2026-09-04 keyboard gamesrv captures for the side-by-side.
Prints only.
"""
import sys, os, math, glob, collections
sys.path.insert(0, r"C:\gd\Rurik\toolkit")
sys.path.insert(0, r"C:\gd\Rurik\toolkit\authsrv")
sys.path.insert(0, r"C:\gd\Rurik\toolkit\clientscan")
import livewire, leadmargin, vaultpath

OP_REPORT, OP_STOP, OP_CLICK = 61, 71, 62

def q(v, f):
    if not v: return float('nan')
    s = sorted(v); i = min(len(s)-1, int(round(f*(len(s)-1)))); return s[i]

def pairs_from_merged(merged, cos_tol=0.9998):
    out = []; prev = None
    for t, d, op, v in merged:
        if d != "c2s": continue
        if op == OP_STOP or op == OP_CLICK:
            prev = None; continue
        if op != OP_REPORT: continue
        try:
            pos = (float(v[1][0]), float(v[1][1])); vec = (float(v[3][0]), float(v[3][1])); mt = int(v[4])
        except Exception:
            continue
        m = math.hypot(*vec)
        if prev and prev["mt"] == mt and mt != 0 and m > 1 and prev["m"] > 1:
            dot = (vec[0]*prev["vec"][0] + vec[1]*prev["vec"][1])/(m*prev["m"])
            dd = math.dist(pos, prev["pos"]); dt = t - prev["t"]
            if dot > cos_tol and dt > 0:
                out.append((dt, dd, mt, dd/dt))
        prev = {"t": t, "pos": pos, "vec": vec, "m": m, "mt": mt}
    return out

def summarize(label, pairs):
    pairs = [p for p in pairs if p[3] <= 320.0]   # exclude warps, as leadmargin does
    dts = [p[0] for p in pairs]; ds = [p[1] for p in pairs]
    print(f"\n== {label}: n={len(pairs)} same-heading same-type consecutive 0x003D pairs (speed<=320)")
    print(f"   dt  p10 {q(dts,.1):.3f}  p50 {q(dts,.5):.3f}  p90 {q(dts,.9):.3f}  max {max(dts) if dts else 0:.3f}")
    print(f"   chord p10 {q(ds,.1):.1f}  p50 {q(ds,.5):.1f}  p90 {q(ds,.9):.1f}")
    h = collections.Counter()
    for dt in dts:
        b = "<0.3" if dt < 0.3 else "0.3-0.6" if dt < 0.6 else "0.6-1.0" if dt < 1.0 else "1.0-1.6" if dt < 1.6 else "1.6-2.0" if dt < 2.0 else ">=2.0"
        h[b] += 1
    print("   dt bins:", dict(sorted(h.items())))
    # the cruise subset: forward type 1 only, chord >= 400
    fw = [p for p in pairs if p[2] == 1]
    print(f"   type-1 pairs n={len(fw)}: dt p50 {q([p[0] for p in fw],.5):.3f} p90 {q([p[0] for p in fw],.9):.3f}; chord p50 {q([p[1] for p in fw],.5):.1f} p90 {q([p[1] for p in fw],.9):.1f}")
    big = [p for p in pairs if p[1] >= 400]
    print(f"   chords>=400u n={len(big)} of {len(pairs)} ({100.0*len(big)/max(1,len(pairs)):.1f}%): chord p50 {q([p[1] for p in big],.5):.1f}")
    return pairs

live_pairs = []; conns = 0; bad = 0; reports = 0
for capdir, conn_file in livewire.live_connections():
    conn, merged, ok = livewire.decode_conn(capdir, conn_file)
    if not ok:
        bad += 1; continue
    conns += 1
    reports += sum(1 for t, d, op, v in merged if d == "c2s" and op == OP_REPORT)
    live_pairs += pairs_from_merged(merged)
print(f"live connections decoded ok: {conns}, refused: {bad}, c2s 0x003D total: {reports}")
summarize("RETAIL (live corpus)", live_pairs)

# ours: 09-04 gamesrv captures (keyboard walks), same rule via a merged-shaped adapter
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
    ours += pairs_from_merged(merged)
print(f"\nours: {len(gs)} gamesrv captures 09-02..09-04")
summarize("OURS (09-02..09-04 gamesrv)", ours)
