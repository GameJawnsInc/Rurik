#!/usr/bin/env python3
"""Replay the AgTrack guard over the harness corpus, stock and fixed, and count what changes (MOVECODE-1z-bf).

    python studies/movecode/review/guardretro.py --all
    python studies/movecode/review/guardretro.py 20260904T174050 20260904T173704
    python studies/movecode/review/guardretro.py --all --tol 0.5

THE QUESTION. sec.1z-be found that every gate2-offmesh re-pin the server sent
landed on a body the client's own snap test had just passed: the guard's gate 2
asked exact trapezoid containment (pathmap.walkable) of the modelled sync copy,
which stood on the client's own previous report -- a point our edges miss by
<= 0.5 u. The fix (agtrack_mirror.GATE2_SEAM_TOL, pathmap.on_mesh) tolerates
SEAM_TOL. Before it ships as a default it has to be RETRODICTED: replay every
capture's guard feed through the guard twice -- exact (stock) and tolerant
(fix) -- and report

  1. the POSITIVE CONTROL: the stock replay must reproduce the capture's own
     logged verdicts (`agtrack_guard` rows, one per grant) and its re-pin fires.
     A replay that cannot reproduce the past has no authority over the
     counterfactual; the mismatch count is printed, never hidden. Captures
     from before the guard existed (2026-08) carry no verdict rows and are
     reported as a separate population ("preguard") -- replaying today's guard
     over traffic an older server produced says nothing about the fix, and the
     summary refuses to pool them with the runs that can;
  2. per run: vetoes and gate2-offmesh re-pins predicted by each arm;
  3. the removed re-pins, each with the client's OWN outcome where the corpus
     can show it: the two RUN-1zBD runs carry a movehook capture (snaptest ran,
     no reseed -- read separately with hookwin.py), and the position_report that
     followed each re-pin is printed so a body the re-pin dragged (a jump) can be
     told from one that stood.

THE FEED, rebuilt from the gamesrv capture exactly as authsrv feeds the guard:
placement from the first report's server position; `position_report` rows ->
on_report (sig = ("rep", source, stop) as authsrv builds it); decoded 0x003E
rows -> on_click; the player's sent 0x0029/0x002A -> pre_emit + on_emit; sent
0x002C -> on_emit; sent 0x002B -> on_speed; every WORLD_SIMULATION_TICK sent
row -> tick, with repin_state sampled at EVERY tick (the server samples every
tenth; see the note in replay() for why episodes, not samples, are counted). Times are the rows' wall clock. Map 146 only (the mesh the guard used);
other maps are counted and skipped.

Read-only. Needs the vault. Stdlib only.
"""
import argparse
import glob
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "mapdata"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "authsrv"))

PLAYER = 1
MAP146 = 0x1B97D


def decode_plain(op, plain):
    b = bytes.fromhex(plain)
    if op == 0x29:
        _o, agent, x, y, p1, p2 = struct.unpack_from("<HIffHH", b)
        return agent, x, y, p1, p2
    if op == 0x2A:
        _o, agent, x, y, p1, p2 = struct.unpack_from("<HIffII", b)
        return agent, x, y, p1, p2
    if op == 0x2C:
        _o, agent, x, y, p1 = struct.unpack_from("<HIffH", b)
        return agent, x, y, p1, None
    if op == 0x2B:
        _o, agent, spd = struct.unpack_from("<HIf", b)
        return agent, spd, None, None, None
    return None


def events(R):
    """The guard's feed, in capture order."""
    out = []
    for r in R:
        k = r.get("kind")
        t = r.get("wall_unix")
        if t is None:
            continue
        if k == "position_report":
            x, y = r["reported"]
            out.append((t, "report", (float(x), float(y), r.get("plane"), r.get("source"), bool(r.get("accepted")))))
        elif k == "decoded" and r.get("opcode") == 0x3E:
            v = r.get("values") or []
            if len(v) >= 3 and isinstance(v[1], list):
                out.append((t, "click", (float(v[1][0]), float(v[1][1]), v[2])))
        elif k == "sent":
            op = r.get("opcode")
            if op == 30:
                out.append((t, "tick", None))
            elif op in (0x29, 0x2A, 0x2B, 0x2C):
                d = decode_plain(op, r.get("plain", ""))
                if d and d[0] == PLAYER:
                    out.append((t, "sent", (op, d, r.get("label", ""))))
        elif k == "agtrack_guard":
            out.append((t, "logged_verdict", (r.get("code"), r.get("why"))))
        elif k == "agtrack_repin_fire":
            out.append((t, "logged_fire", r.get("why")))
        elif k == "agtrack_repin" and r.get("code") == "due":
            out.append((t, "logged_due", r.get("why")))
    return out


def replay(evs, pm, tol):
    import agtrack_guard as ag
    import agtrack_mirror as am
    saved = am.GATE2_SEAM_TOL
    am.GATE2_SEAM_TOL = tol
    try:
        g = ag.AgTrackGuard(mesh=am.MeshAdapter(pm))
        verdicts, dues, fires_seen = [], [], []
        seeded = False
        nt = 0
        last_code = None
        for t, kind, d in evs:
            if kind == "report":
                x, y, plane, source, acc = d
                if not seeded:
                    g.on_placement(x, y, plane if plane is not None else 0, t - 1.0)
                    seeded = True
                g.on_report(x, y, plane, ("rep", source, source == "0x0047"), t, accepted=acc)
            elif kind == "click" and seeded:
                g.on_click(d[0], d[1], d[2], t)
            elif kind == "sent" and seeded:
                op, dd, label = d
                if op == 0x2B:
                    g.on_speed(float(dd[1]), t)
                elif op in (0x29, 0x2A):
                    v = g.pre_emit(dd[1], dd[2], dd[3], dd[4], t)
                    verdicts.append((t, v.code, v.why))
                    g.on_emit(op, dd[1], dd[2], dd[3], dd[4], t)
                elif op == 0x2C:
                    g.on_emit(0x2C, dd[1], dd[2], dd[3], None, t)
                    if label.startswith("AGTRACK RE-PIN"):
                        fires_seen.append(t)
            elif kind == "tick" and seeded:
                g.tick(t)
                nt += 1
                # EVERY tick, not every tenth: the server samples at 2 Hz and
                # whether a 0.14 s DUE window is seen is phase luck (17 of the
                # corpus's 19 gate2 vetoes fired; the other 2 fell between
                # samples). A retrodiction counts EPISODES -- a transition into
                # DUE -- so the arms are compared on what the guard would have
                # licensed, not on where the clock happened to land.
                code, why = g.repin_state(t)
                if (code, why) != last_code:
                    last_code = (code, why)
                    if code == ag.REPIN_DUE:
                        dues.append((t, why, g.repin_block_reason(t)))
        return verdicts, dues, fires_seen
    finally:
        am.GATE2_SEAM_TOL = saved


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="*")
    ap.add_argument("--all", action="store_true", help="every harness run with a gamesrv capture")
    ap.add_argument("--tol", type=float, default=None, help="the fix arm's tolerance (default: agtrack_mirror.GATE2_SEAM_TOL)")
    ap.add_argument("--only-flagged", action="store_true",
                    help="with --all: replay only runs whose capture logged a gate2-offmesh verdict")
    a = ap.parse_args()
    from vaultpath import require_dir
    from pathmap import PathingMap
    import agtrack_mirror as am
    import seamscore as SC
    vault = require_dir()
    tol = am.GATE2_SEAM_TOL if a.tol is None else a.tol
    pm = PathingMap.load(MAP146)
    if a.all:
        runs = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(vault, "captures", "harness", "*", "report.json")))
    else:
        runs = a.runs
    if not runs:
        print("no runs given (pass ids or --all)")
        return 1
    tot = {"runs": 0, "skipped": 0, "ctrl_ok": 0, "ctrl_bad": 0, "logged_v": 0, "stock_v": 0, "fix_v": 0,
           "logged_g2": 0, "stock_g2": 0, "fix_g2": 0, "logged_fire": 0, "stock_due_g2": 0, "fix_due_g2": 0}
    removed = []
    for rid in runs:
        rp = os.path.join(vault, "captures", "harness", rid, "report.json")
        try:
            rep = json.load(open(rp))
        except Exception:
            tot["skipped"] += 1
            continue
        caps = [c.replace("\\", "/") for c in rep.get("captures", []) if "gamesrv" in c.replace("\\", "/")]
        if not caps or not os.path.isfile(caps[0]):
            tot["skipped"] += 1
            continue
        try:
            R, _bad = SC.load_rows(caps[0])
        except Exception:
            tot["skipped"] += 1
            continue
        evs = events(R)
        logged = [(t, c, w) for t, k, (c, w) in ((t, k, d) for t, k, d in evs if k == "logged_verdict")]
        logged_fires = [(t, d) for t, k, d in evs if k == "logged_fire"]
        logged_dues = [(t, d) for t, k, d in evs if k == "logged_due" and d == "gate2-offmesh"]
        if a.only_flagged and not any(w == "gate2-offmesh" for _t, _c, w in logged) and not any(w == "gate2-offmesh" for _t, w in logged_fires):
            continue
        reports = [d for t, k, d in evs if k == "report"]
        if not reports:
            tot["skipped"] += 1
            continue
        # map check: the first report must sit on (or within 1 u of) map 146's mesh
        x0, y0 = reports[0][0], reports[0][1]
        if not pm.on_mesh(x0, y0, 1.0):
            tot["skipped"] += 1
            continue
        tot["runs"] += 1
        sv, sdue, fires_seen = replay(evs, pm, 0.0)
        fv, fdue, _ = replay(evs, pm, tol)
        # positive control: the stock replay against the log
        ok = len(sv) == len(logged) and all(c1 == c2 and w1 == w2 for (_t, c1, w1), (_t2, c2, w2) in zip(sv, logged))
        tot["ctrl_ok" if ok else "ctrl_bad"] += 1
        pop = "ok" if ok else "bad"
        if not logged:
            pop = "preguard"
            tot["preguard"] = tot.get("preguard", 0) + 1
        P = tot.setdefault("pop", {})
        pp = P.setdefault(pop, {"runs": 0, "logged_g2": 0, "stock_g2": 0, "fix_g2": 0, "stock_v": 0, "fix_v": 0, "logged_v": 0})
        pp["runs"] += 1
        lg2 = sum(1 for _t, _c, w in logged if w == "gate2-offmesh")
        sg2 = sum(1 for _t, _c, w in sv if w == "gate2-offmesh")
        fg2 = sum(1 for _t, _c, w in fv if w == "gate2-offmesh")
        tot["logged_v"] += sum(1 for _t, c, _w in logged if c == "veto")
        tot["stock_v"] += sum(1 for _t, c, _w in sv if c == "veto")
        tot["fix_v"] += sum(1 for _t, c, _w in fv if c == "veto")
        tot["logged_g2"] += lg2
        tot["stock_g2"] += sg2
        tot["fix_g2"] += fg2
        pp["logged_v"] += sum(1 for _t, c, _w in logged if c == "veto")
        pp["stock_v"] += sum(1 for _t, c, _w in sv if c == "veto")
        pp["fix_v"] += sum(1 for _t, c, _w in fv if c == "veto")
        pp["logged_g2"] += lg2; pp["stock_g2"] += sg2; pp["fix_g2"] += fg2
        tot["logged_fire"] += sum(1 for _t, w in logged_fires if w == "gate2-offmesh")
        tot["logged_due"] = tot.get("logged_due", 0) + len(logged_dues)
        sdg = [d for d in sdue if d[1] == "gate2-offmesh"]
        fdg = [d for d in fdue if d[1] == "gate2-offmesh"]
        tot["stock_due_g2"] += len(sdg)
        tot["fix_due_g2"] += len(fdg)
        if lg2 or sg2 or fg2 or sdg or fdg or not ok:
            print("%s: control %s (%d logged verdicts, %d replayed%s); gate2 verdicts logged %d / stock %d / fix %d; "
                  "gate2 re-pins logged %d / stock due %d / fix due %d"
                  % (rid, "OK" if ok else "MISMATCH", len(logged), len(sv),
                     "" if ok else ", first difference at #%d" % next((i for i, (x, y) in enumerate(zip(sv, logged)) if x[1:] != y[1:]), min(len(sv), len(logged))),
                     lg2, sg2, fg2, sum(1 for _t, w in logged_fires if w == "gate2-offmesh"), len(sdg), len(fdg)))
            for t, why, blk in sdg:
                after = [(rt, d) for rt, k, d in evs if k == "report" and rt > t][:1]
                before = [(rt, d) for rt, k, d in evs if k == "report" and rt <= t][-1:]
                fx = "still predicted" if any(abs(ft - t) < 0.6 for ft, _w, _b in fdg) else "REMOVED by the fix"
                b = before[0][1] if before else None
                n = after[0][1] if after else None
                jump = None
                if b and n:
                    jump = ((n[0] - b[0]) ** 2 + (n[1] - b[1]) ** 2) ** 0.5
                print("    stock re-pin due at +%.2fs (%s): %s; report before (%.1f,%.1f) pl %s -> next report %s%s"
                      % (t - evs[0][0], blk or "unblocked", fx,
                         b[0] if b else float("nan"), b[1] if b else float("nan"), b[2] if b else "?",
                         "(%.1f,%.1f) %+.2fs" % (n[0], n[1], after[0][0] - t) if n else "none",
                         " jump %.1f u" % jump if jump is not None else ""))
                if fx.startswith("REMOVED"):
                    removed.append((rid, t - evs[0][0], jump))
    print("\nRUNS %d replayed (%d skipped: other map / no capture); positive control OK %d, MISMATCH %d"
          % (tot["runs"], tot["skipped"], tot["ctrl_ok"], tot["ctrl_bad"]))
    print("VETOES  logged %d | stock replay %d | fix replay %d" % (tot["logged_v"], tot["stock_v"], tot["fix_v"]))
    print("gate2-offmesh VERDICTS logged %d | stock %d | fix %d" % (tot["logged_g2"], tot["stock_g2"], tot["fix_g2"]))
    print("gate2-offmesh RE-PINS  logged due-transitions %d, fires %d | stock replay due-transitions %d | fix replay %d"
          % (tot.get("logged_due", 0), tot["logged_fire"], tot["stock_due_g2"], tot["fix_due_g2"]))
    print("removed by the fix: %d; next-report jumps after the (real) re-pin: %s" % (len(removed), ", ".join("%.0f" % j for _r, _t, j in removed if j is not None)))
    print("\nBY POPULATION -- only 'control OK' runs are evidence about the fix; 'preguard' captures carry no guard rows at all")
    print("(the guard did not exist when they were recorded), and 'MISMATCH' runs logged an older guard's verdicts:")
    for pop, label in (("ok", "control OK"), ("bad", "MISMATCH (older guard)"), ("preguard", "preguard (no verdict rows)")):
        pp = tot.get("pop", {}).get(pop)
        if not pp:
            continue
        print("  %-28s runs %3d  vetoes logged %3d / stock %3d / fix %3d   gate2-offmesh logged %3d / stock %3d / fix %3d"
              % (label, pp["runs"], pp["logged_v"], pp["stock_v"], pp["fix_v"], pp["logged_g2"], pp["stock_g2"], pp["fix_g2"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
