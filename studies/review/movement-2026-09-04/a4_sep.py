"""READ-ONLY: moving-sample sync-vs-async separation on agenttap tapes.
Prints only. No writes anywhere.
"""
import json, math, os, sys, glob

D = r"C:\gd\Rurik\vault\research\animref"

def stats(v):
    if not v:
        return None
    v = sorted(v)
    def p(q):
        i = min(len(v) - 1, int(q * (len(v) - 1)))
        return v[i]
    return len(v), round(p(0.5), 1), round(p(0.9), 1), round(v[-1], 1)

for path in sorted(glob.glob(os.path.join(D, "agenttap-20260904*.jsonl"))):
    mov, allv = [], []
    n = 0
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or '"kind": "sample"' not in line:
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                a = r.get("agents", {}).get("1")
                if not a:
                    continue
                s, y = a.get("sync"), a.get("async")
                if not s or not y:
                    continue
                if s.get("x") is None or y.get("x") is None:
                    continue
                d = math.hypot(s["x"] - y["x"], s["y"] - y["y"])
                if not math.isfinite(d):
                    continue
                n += 1
                allv.append(d)
                vx, vy = y.get("vx") or 0.0, y.get("vy") or 0.0
                sp = math.hypot(vx, vy) * (y.get("maxspeed") or 0.0) \
                    if abs(vx) <= 1.001 and abs(vy) <= 1.001 else math.hypot(vx, vy)
                if sp > 50.0:
                    mov.append(d)
    except Exception as e:
        print(os.path.basename(path), "ERR", e)
        continue
    print(f"{os.path.basename(path)}  n={n}  all={stats(allv)}  moving={stats(mov)}")
