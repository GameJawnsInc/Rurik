"""READ-ONLY. Run the M-A2 detector over ALL 41 agenttap tapes.
Prints: per-tape sample count, hz, dt p50/p90/max, naive >150u single-sample
body jumps AND their dt, dt-normalised (implied speed >400 u/s over dt>=0.05s)
jumps, and the same for the sync copy. Nothing is written.
"""
import sys, os, glob, math, json
sys.path.insert(0, r"C:/gd/Rurik/toolkit")
sys.path.insert(0, r"C:/gd/Rurik/toolkit/clientscan")
import w0score

VAULT = r"C:/gd/Rurik/vault"
JUMP = 150.0
R_MATCH = 100.0
SPEED_BAR = 400.0
MIN_DT = 0.05

tapes = sorted(glob.glob(os.path.join(VAULT, "research", "animref", "agenttap-*.jsonl")))
print("n tapes:", len(tapes))
tot_naive = tot_speed = 0
free_gaps = 0
for tp in tapes:
    stamp = os.path.basename(tp)[9:24]
    try:
        head, rows = w0score.load(tp)
    except Exception as e:
        print(f"{stamp}  LOAD FAIL: {type(e).__name__} {e}")
        continue
    dts = []
    naive = []
    naive100 = []
    speeded = []
    syncnaive = []
    prev = None
    n = 0
    for s in rows:
        a = (s.get("agents") or {}).get("1")
        if not a:
            continue
        sy, ay = a.get("sync"), a.get("async")
        if not sy or not ay or "x" not in sy or "x" not in ay:
            continue
        b = w0score.live(ay, s.get("clock1"))
        y = w0score.live(sy, s.get("clock0"))
        if prev is not None:
            dt = s["t"] - prev[0]
            dts.append(dt)
            db = math.hypot(b[0] - prev[1][0], b[1] - prev[1][1])
            ds = math.hypot(y[0] - prev[2][0], y[1] - prev[2][1])
            if db > JUMP:
                naive.append((round(s["t"], 2), round(db), round(dt, 3)))
            if db > R_MATCH:
                naive100.append((round(s["t"], 2), round(db), round(dt, 3)))
            if dt >= MIN_DT and db / dt > SPEED_BAR:
                speeded.append((round(s["t"], 2), round(db), round(dt, 3),
                                round(db / dt)))
            if ds > JUMP:
                syncnaive.append((round(s["t"], 2), round(ds), round(dt, 3)))
            if dt > JUMP / 288.0:
                free_gaps += 1
        prev = (s["t"], b, y)
        n += 1
    if not dts:
        print(f"{stamp}  no samples")
        continue
    sd = sorted(dts)
    p50 = sd[len(sd) // 2]
    p90 = sd[int(len(sd) * 0.9)]
    mx = sd[-1]
    tot_naive += len(naive)
    tot_speed += len(speeded)
    print(f"{stamp} n={n:4d} hz={n/(rows[-1]['t']-rows[0]['t']):5.1f} "
          f"dt p50={p50:.3f} p90={p90:.3f} max={mx:.3f} "
          f"| body>150u:{len(naive):2d} {naive[:3]} "
          f"| body>100u:{len(naive100):2d} "
          f"| speed>400:{len(speeded):2d} {speeded[:3]} "
          f"| sync>150u:{len(syncnaive):2d} {syncnaive[:2]}")
print(f"TOTALS naive>150u body jumps = {tot_naive}; "
      f"speed-gated = {tot_speed}; sample gaps > 150/288 s = {free_gaps}")
