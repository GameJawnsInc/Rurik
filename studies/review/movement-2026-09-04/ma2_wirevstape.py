"""READ-ONLY. For every tape with a naive >150u single-sample drawn-body jump,
join the gamesrv capture that spans the tape t0 and print movesync's wire hard
count beside it, plus the capture's lead flag. Prints only."""
import sys, os, glob, math, json
sys.path.insert(0, r"C:/gd/Rurik/toolkit")
sys.path.insert(0, r"C:/gd/Rurik/toolkit/clientscan")
import w0score, movesync

VAULT = r"C:/gd/Rurik/vault"
JUMP = 150.0
caps = sorted(glob.glob(os.path.join(VAULT, "captures", "gamesrv",
                                     "authsrv-*-c1.jsonl")))


def flags_of(path):
    for i, line in enumerate(open(path, encoding="utf-8", errors="replace")):
        if '"flags"' in line:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("kind") == "flags":
                return r
        if i > 40:
            break
    return {}


def span_cap(t0, day):
    for c in caps:
        st = os.path.basename(c)[8:23]
        if st[:8] != day:
            continue
        try:
            w = [json.loads(l)["wall_unix"] for l in
                 open(c, encoding="utf-8", errors="replace")
                 if l.strip() and '"wall_unix"' in l]
        except Exception:
            continue
        if w and w[0] - 5 <= t0 <= w[-1]:
            return c
    return None


tot_j = tot_hard = 0
for tp in sorted(glob.glob(os.path.join(VAULT, "research", "animref",
                                        "agenttap-*.jsonl"))):
    stamp = os.path.basename(tp)[9:24]
    try:
        head, rows = w0score.load(tp)
    except Exception:
        continue
    ser = w0score.series(head, rows, 1)
    jumps = []
    for i in range(1, len(ser)):
        db = math.hypot(ser[i]["body"][0] - ser[i-1]["body"][0],
                        ser[i]["body"][1] - ser[i-1]["body"][1])
        if db > JUMP:
            jumps.append((round(ser[i]["t"], 2), round(db)))
    if not jumps:
        continue
    cap = span_cap(head["t0"], stamp[:8])
    if cap is None:
        print(f"{stamp} jumps={jumps} -- NO CAPTURE SPANS THE TAPE")
        continue
    w = movesync.wire_only(cap)
    f = flags_of(cap)
    tot_j += len(jumps)
    tot_hard += len(w["hard"])
    print(f"{stamp} cap={os.path.basename(cap)[8:23]} "
          f"LEAD_ON={f.get('KBD_SYNC_LEAD_ON')} ROUTER={f.get('ROUTER')} "
          f"KBD_SYNC={f.get('KBD_SYNC')} | tape body jumps={len(jumps)} "
          f"{jumps} | WIRE hard={len(w['hard'])} refuse={w['refuse_all']} "
          f"active={w['den']['active']:.1f}s")
print(f"\nTOTAL tape drawn-body jumps >{JUMP:.0f} u = {tot_j}; "
      f"wire hard steps on the same captures = {tot_hard}")
