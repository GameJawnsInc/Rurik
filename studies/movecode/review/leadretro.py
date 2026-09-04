#!/usr/bin/env python3
"""Replay the lead campaign's keyboard leads through three rays (MOVECODE-1z-bc).

    python studies/movecode/review/leadretro.py

WHY THIS EXISTS, and why it is kept. sec.1z-bb put the router's two rays on
`pathmap.seam_clip` -- a body's plane may end only at a portal -- and the
natural next step was the LEAD's ray (`a2_clip_lead`), which still uses 1z-ap's
`clip(plane=)`: it stops at ANY plane change, portals included, and sec.1z-ar.6
had measured that as an over-clip (3 of RUN-1zAQ's 65 arm-A leads, 7.8% of the
464-lead corpus). This script was the audit of that swap, and IT REFUTED IT.

THE RAYS. For every fired keyboard lead in the campaign window (harness runs
2026-09-03 07:00 .. 2026-09-04 13:00, map 146) the ray is rebuilt from the
capture -- origin = the report the lead was armed at, plane = that report's
plane word, direction = toward the granted point, or the body's last motion
when the grant was clipped to zero reach ("dir approx") -- and walked three
ways at the server's 2 u step: plane-blind `clip()`, 1z-ap's `clip(plane=)`,
and `seam_clip` on the report's plane. Reach is compared against gate 1's
299.332591 u, the separation at which the client's arrival snap fires
(sec.1z-ag): a lead kept under it cannot arm the lock.

WHAT IT FOUND (2026-09-04, 622 leads, 27 captures): the two plane-aware rays
agree on 568 leads; where they differ the seam ray is ALWAYS the longer (54,
never shorter); 33 of those it lets past gate 1. Among them are ALL SIX fatal
leads of the six measured locks -- RUN-1zAO's (10373,8286) -> 520 u where 1z-ap
stops it at 14 u -- because at both ends of the spawn-side bridge (plane 29)
the seam the body would not walk is PORTAL-LINKED IN THE FILE. 0 of 6 kept
under the gate. So the file's link is not the body's crossing there, the lead
keeps the stricter clip, and the seam variant ships opt-in (--lead-seam-clip).

The per-capture table names the six locked captures and RUN-1zAQ's four so a
reader can check the claim against the runs that made it. Read-only over the
vault's captures and the map-146 mesh. Stdlib only.
"""
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "mapdata"))

GATE = 299.332591          # authsrv gate 1 / agtrack_guard's red line
LEAD = 520.0               # KBD_SYNC_LEAD
STEP = 2.0                 # A2_LEAD_CLIP_STEP
WINDOW = ("20260903T07", "20260904T13")
MAP_FILE = 0x1B97D
LOCKED = {"authsrv-20260903T191320-c1.jsonl", "authsrv-20260903T195931-c1.jsonl",
          "authsrv-20260903T200621-c1.jsonl", "authsrv-20260903T202121-c1.jsonl",
          "authsrv-20260903T215027-c1.jsonl", "authsrv-20260904T110025-c1.jsonl"}
AQ_A = {"authsrv-20260904T115756-c1.jsonl", "authsrv-20260904T120123-c1.jsonl"}
AQ_B = {"authsrv-20260904T115613-c1.jsonl", "authsrv-20260904T115942-c1.jsonl"}


def leads_from(cap):
    """(origin, plane, raw_dest, why, dir_approx) per fired keyboard lead."""
    out = []
    reports = []
    with open(cap, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("kind") == "position_report" and r.get("reported"):
                reports.append((tuple(r["reported"]), r.get("plane")))
            elif (r.get("kind") == "grant_verdict" and r.get("fired")
                  and r.get("lead_src") == "kbd" and reports):
                (ox, oy), plane = reports[-1]
                dest = tuple(r["dest"])
                dx, dy = dest[0] - ox, dest[1] - oy
                approx = False
                if math.hypot(dx, dy) < 1.0:
                    if len(reports) < 2:
                        continue
                    (px, py), _ = reports[-2]
                    dx, dy = ox - px, oy - py
                    approx = True
                L = math.hypot(dx, dy)
                if L < 1.0:
                    continue
                out.append(((ox, oy), plane,
                            (ox + LEAD * dx / L, oy + LEAD * dy / L),
                            r.get("lead_clip_why"), approx))
    return out


def main():
    from vaultpath import require_dir
    from pathmap import PathingMap
    vault = require_dir()
    pm = PathingMap.load(MAP_FILE)
    rows = []
    for d in sorted(glob.glob(os.path.join(vault, "captures", "harness", "2026090[34]T*"))):
        rid = os.path.basename(d)
        if not (WINDOW[0] <= rid <= WINDOW[1]):
            continue
        p = os.path.join(d, "report.json")
        if not os.path.exists(p):
            continue
        rep = json.load(open(p))
        caps = [c.replace("\\", "/") for c in rep["captures"] if "gamesrv" in c.replace("\\", "/")]
        if not caps or not os.path.exists(caps[0]):
            continue
        for lead in leads_from(caps[0]):
            rows.append((os.path.basename(caps[0]), rid) + lead)
    print("fired keyboard leads with a recoverable ray: %d over %d captures"
          % (len(rows), len({r[0] for r in rows})))

    def reach(p, o):
        return math.hypot(p[0] - o[0], p[1] - o[1])

    same = longer = shorter = past_gate = 0
    lets = []
    by_cap = {}
    for name, rid, o, plane, raw, why, approx in rows:
        pl = pm.plane_at(o[0], o[1], prefer=plane)
        blind = pm.clip(o[0], o[1], raw[0], raw[1], step=STEP)
        if pl is None:
            planec = seamc = blind
        else:
            planec = pm.clip(o[0], o[1], raw[0], raw[1], step=STEP, plane=pl)
            seamc = pm.seam_clip(o[0], o[1], raw[0], raw[1], pl, step=STEP)
        rb, rp, rs = reach(blind, o), reach(planec, o), reach(seamc, o)
        c = by_cap.setdefault(name, {"n": 0, "prevented": 0, "seam_too": 0, "longer": 0})
        c["n"] += 1
        if rb >= GATE and rp < GATE:
            c["prevented"] += 1
            if rs < GATE:
                c["seam_too"] += 1
        if abs(rs - rp) < 1e-6:
            same += 1
        elif rs > rp:
            longer += 1
            c["longer"] += 1
            if rs >= GATE > rp:
                past_gate += 1
            lets.append((name[8:23], rid, tuple(round(v) for v in o), pl, round(rp),
                         round(rs), round(rb), why, approx))
        else:
            shorter += 1
    print("seam_clip vs clip(plane=): same %d, seam longer %d, seam shorter %d; "
          "seam lets past gate 1 what the plane clip stopped: %d"
          % (same, longer, shorter, past_gate))
    print("\nleads the SEAM ray grants longer than the PLANE ray (file-linked portals):")
    for row in lets:
        print("  cap %s run %s origin %s plane %s: plane %3d u -> seam %3d u "
              "(blind %3d u) why=%s%s"
              % (row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7],
                 "  (dir approx)" if row[8] else ""))
    print("\nper capture -- the six locked runs and RUN-1zAQ's four:")
    print("  %-38s %-7s %5s  %s" % ("capture", "arm", "leads",
                                     "prevented by the plane clip / of which the seam clip also keeps under gate 1"))
    for name in sorted(by_cap):
        tag = ("LOCKED" if name in LOCKED else "1zAQ-A" if name in AQ_A
               else "1zAQ-B" if name in AQ_B else "")
        if tag:
            c = by_cap[name]
            print("  %-38s %-7s %5d  %d / %d" % (name, tag, c["n"], c["prevented"], c["seam_too"]))
    locked = [by_cap[n] for n in LOCKED if n in by_cap]
    kept = sum(c["seam_too"] for c in locked)
    prevented = sum(c["prevented"] for c in locked)
    print("\nVERDICT: the plane clip kept %d of %d fatal leads under gate 1; the seam clip "
          "keeps %d of %d." % (prevented, len(locked), kept, len(locked)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
