"""GROUNDZ-F11 / RUN-R3 -- the plane word and the drawn height of a hostile on ground our mesh
does not cover, per sample, joined to the server's orders.

    python studies/renderobj/review/terrace.py --tape T --cap C [--timeline]

Per paired sample: both bodies' client planes and ground z (the height reader, GROUNDZ-F3), our
mesh's planes under each, the distance between them.  Then the EXPOSURE (hostile within the
follow stop radius of the player while our mesh has no trapezoid under the hostile), and inside
it: P1 the fraction of samples where the hostile's client plane equals the player's, P2 the
height gap (hostile minus player, `up is -Z`: positive = the hostile drawn LOWER), and every
order to the hostile with its mover-plane word.  The feel session (2026-09-06 15:48) reads:
exposure 16 s, P1 0 %, P2 +51.9 u -- the sink.
"""
import sys, os, math, json, statistics, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(ROOT, "studies", "npctrack", "review"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "clientscan"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "mapdata"))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
import npcdrift as N                 # noqa: E402
import w0score as W                  # noqa: E402
import agtrack_replay as AR          # noqa: E402

REACH = 80.0
LABEL_PLANE = re.compile(r"plane (\d+)->(\d+)")
CORRECT = re.compile(r"PLANE CORRECT: agent (\d+) .*plane moved (\d+) -> (\d+)")


def load_mesh(fid):
    try:
        from pathmap import PathingMap
        return PathingMap.load(fid)
    except Exception as e:                     # noqa: BLE001
        print("no mesh for %s: %s" % (hex(fid) if fid else fid, e))
        return None


def samples(tape, t0):
    head, rows = W.load(tape)
    out = []
    for s in rows:
        a = s.get("agents") or {}
        p, h = a.get("1"), a.get("10")
        if not p or not h or not p.get("async") or not h.get("async"):
            continue
        pa, ha = p["async"], h["async"]
        if "x" not in pa or "x" not in ha:
            continue
        out.append(dict(t=head["t0"] + s["t"] - t0,
                        px=pa["x"], py=pa["y"], pplane=pa.get("plane"), pz=(p.get("groundz") or {}).get("ground_z"),
                        hx=ha["x"], hy=ha["y"], hplane=ha.get("plane"), hz=(h.get("groundz") or {}).get("ground_z"),
                        hv=math.hypot(ha.get("vx", 0.0), ha.get("vy", 0.0))))
    return out


def main(argv):
    if "--tape" not in argv or "--cap" not in argv:
        print(__doc__)
        return 2
    tape = argv[argv.index("--tape") + 1]
    cap = argv[argv.index("--cap") + 1]
    crows = W.load_gamesrv(cap)
    t0 = N.cap_t0(crows)
    _ev, fid = AR.load_events(cap)
    pm = load_mesh(fid)
    ss = samples(tape, t0)
    if not ss:
        print("no paired samples")
        return 1

    def planes(x, y):
        if pm is None:
            return None
        return set(pm.planes_at(x, y))
    for s in ss:
        s["d"] = math.hypot(s["px"] - s["hx"], s["py"] - s["hy"])
        s["pmesh"] = planes(s["px"], s["py"])
        s["hmesh"] = planes(s["hx"], s["hy"])
        s["dz"] = (s["hz"] - s["pz"]) if (s["hz"] is not None and s["pz"] is not None) else None
    orders = []
    for r in crows:
        if r.get("kind") != "sent":
            continue
        lab = r.get("label") or ""
        m = CORRECT.search(lab)
        if m and m.group(1) == "10":
            orders.append((r["t"], "CORRECT", int(m.group(2)), int(m.group(3))))
            continue
        if "agent 10" in lab and r.get("opcode") in (0x29, 0x2A):
            m = LABEL_PLANE.search(lab)
            if m:
                orders.append((r["t"], "FOLLOW", int(m.group(1)), int(m.group(2))))
    if "--timeline" in argv:
        last = -9.0
        print("t | dist | player plane z mesh | hostile plane z mesh | dz")
        for s in ss:
            if s["t"] - last < 1.0:
                continue
            last = s["t"]
            print("  %6.1f | %5.0f | (%5.0f,%5.0f) pl %2s z %8s mesh %-6s | (%5.0f,%5.0f) pl %2s z %8s mesh %-6s | %s" % (
                s["t"], s["d"], s["px"], s["py"], s["pplane"], "%.1f" % s["pz"] if s["pz"] is not None else "?",
                "NONE" if s["pmesh"] == set() else (sorted(s["pmesh"]) if s["pmesh"] else "?"),
                s["hx"], s["hy"], s["hplane"], "%.1f" % s["hz"] if s["hz"] is not None else "?",
                "NONE" if s["hmesh"] == set() else (sorted(s["hmesh"]) if s["hmesh"] else "?"),
                "%+.1f" % s["dz"] if s["dz"] is not None else "?"))
    def span(sel):
        return (sel[-1]["t"] - sel[0]["t"]) if len(sel) > 1 else 0.0
    on_terrace = [s for s in ss if s["pmesh"] == {0} and s["py"] > 8800 and s["px"] > 11000]
    exposure = [s for s in ss if s["hmesh"] == set() and s["d"] <= REACH and s["hv"] < 5.0]
    print("paired samples %d over %.1f s | player on the terrace: %d samples (%.1f s) | EXPOSURE (hostile parked within %.0f u of the player on ground our mesh does not cover): %d samples (%.1f s)" % (
        len(ss), ss[-1]["t"] - ss[0]["t"], len(on_terrace), span(on_terrace), REACH, len(exposure), span(exposure)))
    if exposure:
        eq = sum(1 for s in exposure if s["hplane"] == s["pplane"])
        dzs = [s["dz"] for s in exposure if s["dz"] is not None]
        t_lo, t_hi = exposure[0]["t"], exposure[-1]["t"]
        print("  P1 the hostile's client plane == the player's: %d of %d (%.0f %%); planes seen hostile %s player %s" % (
            eq, len(exposure), 100.0 * eq / len(exposure),
            sorted(set(s["hplane"] for s in exposure)), sorted(set(s["pplane"] for s in exposure))))
        if dzs:
            deep = [s for s in exposure if s["dz"] is not None and s["dz"] >= 35.0]
            print("  P2 height gap hostile - player (positive = drawn lower): p50 %+.1f p90 %+.1f max %+.1f min %+.1f | samples >= 35 u: %d (%.1f s)" % (
                statistics.median(dzs), sorted(dzs)[int(0.9 * len(dzs))], max(dzs), min(dzs), len(deep), span(deep)))
        print("  orders to the hostile from 2 s before the exposure (t, kind, mover plane -> dest plane / old -> new):")
        for t, k, a, b in orders:
            if t_lo - 2.0 <= t <= t_hi + 0.5:
                print("    %6.2f %-7s %d -> %d" % (t, k, a, b))
    else:
        print("  ZERO TRIALS: the hostile never parked within reach on uncovered ground -- P1/P2 unscored")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
