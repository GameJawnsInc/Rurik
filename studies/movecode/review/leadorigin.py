#!/usr/bin/env python3
"""The lead's origin test, retrodicted: what the 179 `origin-unwalkable` refusals would have granted (MOVECODE-1z-bg).

    python studies/movecode/review/leadorigin.py
    python studies/movecode/review/leadorigin.py --since 20260901

THE QUESTION. `a2_clip_lead` refused a keyboard lead whenever the client's
reported origin was not INSIDE a trapezoid (`pathmap.walkable`), and handed out
a zero-lead instead. sec.1z-bf found the same exact-containment test false at
the guard's gate 2: the client's reports at the wedge tip sit <= 0.5 u outside
our edges. Before the origin test loosens, three things have to be measured on
the corpus, because the leads are this arc's subject:

  1. WHAT THE FIX GRANTS. For every fired keyboard lead the capture refused as
     origin-unwalkable, rebuild the ray (leadretro.leads_from: origin = the
     report, direction = toward the granted point or the body's last motion),
     ask on_mesh / plane_near as the fixed server would, and walk 1z-ap's plane
     clip. The reach distribution is printed against the corpus's GRANTED leads
     (clear / clipped) walked the same way -- a new lead must look like an old
     one, not like a longer one -- and every new lead at or past gate 1
     (299.332591 u, the arrival snap's line) is listed with its capture.
  2. THE SIX LOCKED RUNS. The fatal leads of the six measured locks were granted
     (not refused), so the fix cannot touch them; what it CAN do is add leads in
     those captures. They are listed per capture with reach.
  3. WHAT THE REFUSAL COST. After each refused lead the sync copy sat at the
     report while the body walked; after each granted lead it moved. The next
     accepted report's `drift` (the separation the server measured between the
     report and its own copy) and any AGTRACK re-pin fired within 1.5 s are
     tabulated for both kinds, so the harm of the zero-lead is a number rather
     than the LAW's arithmetic.

Read-only over the vault's captures and the map-146 mesh. Stdlib only.
"""
import argparse
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "mapdata"))

GATE = 299.332591
LEAD = 520.0
STEP = 2.0
MAP_FILE = 0x1B97D
AFTER_S = 1.5


def rows_of(cap):
    out = []
    with open(cap, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def leads_with_time(rows):
    """leadretro.leads_from's rebuild, plus the grant's wall time and what followed."""
    reports = []
    out = []
    for i, r in enumerate(rows):
        if r.get("kind") == "position_report" and r.get("reported"):
            reports.append((tuple(r["reported"]), r.get("plane"), r.get("wall_unix"), r.get("drift")))
        elif (r.get("kind") == "grant_verdict" and r.get("fired")
              and r.get("lead_src") == "kbd" and reports):
            (ox, oy), plane, _t, _d = reports[-1]
            dest = tuple(r["dest"])
            dx, dy = dest[0] - ox, dest[1] - oy
            approx = False
            if math.hypot(dx, dy) < 1.0:
                if len(reports) < 2:
                    continue
                (px, py), _p, _t2, _d2 = reports[-2]
                dx, dy = ox - px, oy - py
                approx = True
            L = math.hypot(dx, dy)
            if L < 1.0:
                continue
            t = r.get("wall_unix")
            nxt = next((rr for rr in rows[i + 1:] if rr.get("kind") == "position_report"), None)
            repin = next((rr.get("why") for rr in rows[i + 1:]
                          if rr.get("kind") == "agtrack_repin_fire" and rr.get("wall_unix") is not None
                          and t is not None and rr["wall_unix"] - t <= AFTER_S), None)
            out.append({"o": (ox, oy), "plane": plane, "raw": (ox + LEAD * dx / L, oy + LEAD * dy / L),
                        "why": r.get("lead_clip_why"), "approx": approx, "t": t,
                        "next_drift": nxt.get("drift") if nxt else None,
                        "next_gap": (nxt["wall_unix"] - t) if (nxt and t is not None and nxt.get("wall_unix")) else None,
                        "repin": repin})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default="20260901", help="first harness run id prefix to include")
    a = ap.parse_args()
    from vaultpath import require_dir
    from pathmap import PathingMap
    import leadretro
    vault = require_dir()
    pm = PathingMap.load(MAP_FILE)

    def reach(p, o):
        return math.hypot(p[0] - o[0], p[1] - o[1])

    refused, granted, ambiguous, still_off = [], [], [], []
    for d in sorted(glob.glob(os.path.join(vault, "captures", "harness", "*"))):
        rid = os.path.basename(d)
        if rid < a.since:
            continue
        p = os.path.join(d, "report.json")
        if not os.path.exists(p):
            continue
        rep = json.load(open(p))
        caps = [c.replace("\\", "/") for c in rep.get("captures", []) if "gamesrv" in c.replace("\\", "/")]
        if not caps or not os.path.exists(caps[0]):
            continue
        rows = rows_of(caps[0])
        leads = leads_with_time(rows)
        if not leads:
            continue
        # map check: the first report of the run must be on/near the map-146 mesh
        first = next((r for r in rows if r.get("kind") == "position_report"), None)
        if first is None or not pm.on_mesh(first["reported"][0], first["reported"][1], 1.0):
            continue
        name = os.path.basename(caps[0])
        for L in leads:
            o, plane, raw = L["o"], L["plane"], L["raw"]
            L["cap"], L["rid"] = name, rid
            if L["why"] == "origin-unwalkable":
                if not pm.on_mesh(o[0], o[1]):
                    still_off.append(L)
                    continue
                pl = pm.plane_near(o[0], o[1], prefer=plane)
                if pl is None:
                    ambiguous.append(L)
                    continue
                stop = pm.clip(o[0], o[1], raw[0], raw[1], step=STEP, plane=pl)
                L["pl"], L["reach"] = pl, reach(stop, o)
                refused.append(L)
            elif L["why"] in ("clear", "clipped", "plane-seam"):
                pl = pm.plane_at(o[0], o[1], prefer=plane)
                stop = (pm.clip(o[0], o[1], raw[0], raw[1], step=STEP, plane=pl) if pl is not None
                        else pm.clip(o[0], o[1], raw[0], raw[1], step=STEP))
                L["pl"], L["reach"] = pl, reach(stop, o)
                granted.append(L)

    n_ref = len(refused) + len(ambiguous) + len(still_off)
    print("keyboard leads refused as origin-unwalkable since %s: %d in %d captures" % (
        a.since, n_ref, len({L["cap"] for L in refused + ambiguous + still_off})))
    print("  under the fix: %d become leads (origin on the mesh within 1 u, plane named), "
          "%d stay refused as origin-ambiguous, %d stay refused (origin > 1 u off the mesh)"
          % (len(refused), len(ambiguous), len(still_off)))
    if refused:
        byplane = {}
        for L in refused:
            byplane[L["pl"]] = byplane.get(L["pl"], 0) + 1
        print("  planes the fix names for them: %s (report words honoured: %d of %d)" % (
            byplane, sum(1 for L in refused if L["pl"] == L["plane"]), len(refused)))

    def hist(Ls):
        b = {"0-14": 0, "14-100": 0, "100-299": 0, ">=299 (gate 1)": 0}
        for L in Ls:
            r = L["reach"]
            k = "0-14" if r < 14 else "14-100" if r < 100 else "100-299" if r < GATE else ">=299 (gate 1)"
            b[k] += 1
        return b

    print("\nREACH under 1z-ap's plane clip -- the fix's new leads vs the corpus's granted leads:")
    print("  %-22s %s" % ("new leads (%d)" % len(refused), hist(refused)))
    print("  %-22s %s" % ("granted leads (%d)" % len(granted), hist(granted)))
    past = [L for L in refused if L["reach"] >= GATE]
    print("\nnew leads at or past gate 1: %d" % len(past))
    def heading(L):
        return math.degrees(math.atan2(L["raw"][1] - L["o"][1], L["raw"][0] - L["o"][0]))
    for L in sorted(past, key=lambda L: -L["reach"])[:40]:
        print("  cap %s run %s origin (%.1f,%.1f) report plane %s -> plane %s, reach %.0f u, heading %+.0f deg%s"
              % (L["cap"][8:23], L["rid"], L["o"][0], L["o"][1], L["plane"], L["pl"], L["reach"], heading(L),
                 "  (dir approx)" if L["approx"] else ""))

    print("\nTHE SIX LOCKED CAPTURES: new leads the fix would add there")
    for name in sorted(leadretro.LOCKED):
        Ls = [L for L in refused if L["cap"] == name]
        G = [L for L in granted if L["cap"] == name]
        t0 = min([L["t"] for L in Ls + G if L.get("t")] or [0.0])
        # the FATAL shape in that capture: a granted lead the plane-blind ray runs
        # past gate 1 and the plane clip stops short (leadretro's "prevented")
        fatal = []
        for L in G:
            blind = pm.clip(L["o"][0], L["o"][1], L["raw"][0], L["raw"][1], step=STEP)
            if reach(blind, L["o"]) >= GATE > L["reach"]:
                fatal.append(L)
        if not Ls:
            print("  %-38s none   (fatal-shape leads at %s s)" % (name, ", ".join("%.0f" % (L["t"] - t0) for L in fatal)))
            continue
        print("  %-38s %d new: %s   (fatal-shape leads at %s s)"
              % (name, len(Ls), "; ".join("%.0f u @%.0f s hdg %+.0f" % (L["reach"], (L["t"] or t0) - t0, heading(L)) for L in Ls),
                 ", ".join("%.0f" % (L["t"] - t0) for L in fatal)))

    print("\nWHAT THE REFUSAL COST -- the next accepted report after the grant, and AGTRACK re-pins within %.1f s:" % AFTER_S)
    for label, Ls in (("refused (zero-lead)", refused + ambiguous + still_off), ("granted (clear/clipped)", granted)):
        drifts = sorted(L["next_drift"] for L in Ls if isinstance(L.get("next_drift"), (int, float)))
        gaps = sorted(L["next_gap"] for L in Ls if isinstance(L.get("next_gap"), (int, float)))
        repins = {}
        for L in Ls:
            if L.get("repin"):
                repins[L["repin"]] = repins.get(L["repin"], 0) + 1
        if not drifts:
            print("  %-26s n %4d  (no next report)" % (label, len(Ls)))
            continue
        q = lambda v, f: v[min(len(v) - 1, int(f * len(v)))]
        print("  %-26s n %4d  next-report drift p50 %6.1f  p90 %6.1f  max %6.1f u  (gap p50 %.2f s)  re-pins within %.1f s: %s"
              % (label, len(Ls), q(drifts, 0.5), q(drifts, 0.9), drifts[-1], q(gaps, 0.5) if gaps else float("nan"), AFTER_S, repins or "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
