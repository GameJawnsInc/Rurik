#!/usr/bin/env python3
"""Score a click run's granted legs against the BLIND-SEAM question (MOVECODE-1z-ba).

    python studies/movecode/review/seamscore.py                    # newest harness run
    python studies/movecode/review/seamscore.py 20260904T151500 [--tape PATH]

WHAT IT ASKS. `seamscout.py` finds click chords whose route() crosses a BLIND
seam -- a plane change the file carries no portal for, which the router's
plane-blind string pull walks straight across. The run then asks the CLIENT:
does its drawn body walk such a leg, or does it park at the seam while the
server's sync copy walks on and the grant's arrival teleports it (RUN-1zAO's
signature, FINDINGS sec.1z-ao.2)?

THREE JOINS, each on the wall clock:

  1. The harness report's `click` steps -> the client's MOVE_TO_COORD rows in
     the gamesrv capture (same window `clickaim.pairs_from_run` uses).
  2. Each MOVE_TO_COORD -> the server's `router_route` event that answered it
     and the legs it granted: `router_leg` rows for a routed answer, the
     event itself for a verbatim one-leg answer or a clip fallback.
  3. Each granted leg -> the agenttap tape over [grant, grant + ETA + 1 s]:
     both copies of the player (sync = world 0, the server-driven copy;
     async = world 1, the DRAWN body), the fence column, and the camera.

PER LEG: the seam verdict from `seamscout.seam_crossings` on the leg the
server actually granted (origin = the sync copy at the grant, the corridor
plane the grant carried), and the body's behaviour on it -- how far the
drawn body moved, whether it reached the granted point, the largest
separation between the copies, the largest single-sample jump of the drawn
body, and every fence transition in the window. The classification:

    WALKED   the drawn body's velocity was non-zero for >= 60% of the leg,
             it reached within ARRIVE_U of the granted point, and its LIVE
             position never jumped SNAP_U in one sample
    PARKED   its velocity read zero for >= 80% of the leg while the sync
             copy walked more than 3 x PARK_U; "+SNAP" when its live position
             then jumped >= SNAP_U (the arrival teleport)
    OTHER    anything else -- printed in full, decided by a reader

The positions are LIVE, reconstructed from the anchor + velocity * elapsed
(see `live`); the raw `m_point` is a sample-and-hold anchor and scoring it
directly reads every healthy leg as a park followed by a snap.

The clauses (registered in RUN-1zBA.md) are then scored: P1 exposure (blind
legs granted), P2 the question (how blind legs were walked), P3 the control
(legs crossing a portal or no seam were WALKED -- if those park too the
instrument or the harness is at fault, not the seam).

Read-only over a harness run's report, its gamesrv capture and a tape.
Stdlib only; needs the vault (the mesh and the captures).
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

RUN_SPEED = 288.0
ARRIVE_U = 40.0
PARK_U = 40.0
SNAP_U = 150.0
WINDOW_SLACK = 1.0
MAP_FILE = {146: 0x1B97D}


def newest_run(root):
    runs = sorted(d for d in glob.glob(os.path.join(root, "*")) if os.path.isdir(d))
    return runs[-1] if runs else None


def load_rows(path):
    out = []
    bad = 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                bad += 1
    return out, bad


def pick_tape(tapes, t_lo, t_hi):
    """The tape whose head t0 falls inside the run's window, else the newest."""
    best = None
    for p in tapes:
        try:
            with open(p, encoding="utf-8") as fh:
                head = json.loads(fh.readline())
        except (OSError, ValueError):
            continue
        t0 = head.get("t0")
        if t0 is not None and t_lo <= t0 <= t_hi:
            best = p
    return best or (tapes[-1] if tapes else None)


class Tape:
    def __init__(self, path):
        rows, self.bad = load_rows(path)
        self.head = next(r for r in rows if r.get("kind") == "head")
        self.samples = [r for r in rows if r.get("kind") == "sample"]
        self.t0 = self.head["t0"]
        self.path = path

    def window(self, w0, w1):
        return [s for s in self.samples if w0 <= self.t0 + s["t"] <= w1]

    @staticmethod
    def copy(s, which, aid="1"):
        a = (s.get("agents") or {}).get(aid) or {}
        c = a.get(which)
        if not c or c.get("x") is None:
            return None
        return (c["x"], c["y"])

    @staticmethod
    def fence(s, aid="1"):
        return (((s.get("agents") or {}).get(aid) or {}).get("fence") or {}).get("fence_state")


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def live(c, clock):
    """Where a copy IS, from the fields the movement tick reads.

    `m_point` is the SEGMENT ANCHOR, held from `m_timeUpdated`; the body is
    at anchor + velocity * (world clock - updated), clamped to the segment
    end. The anchor jumps to the far end at arrival and stays put between --
    so an anchor's "jump" is a healthy leg's normal ending, not a snap. This
    is movetap's sample-and-hold trap in another block, and the first
    version of this scorer fell into it: it read every healthy plane-23 leg
    of sec.1z-az's run as PARKED+SNAP. What distinguishes RUN-1zAO's parked
    body is its VELOCITY reading zero while the sync copy walks (sec.1z-ao.2's
    "body v" column), and that is what the classifier below uses.
    """
    if not c or c.get("x") is None:
        return None
    vx, vy = c.get("vx") or 0.0, c.get("vy") or 0.0
    upd = c.get("updated")
    dt = max(0.0, (clock - upd) / 1000.0) if (upd is not None and clock is not None) else 0.0
    dx, dy = vx * dt, vy * dt
    sx, sy = c.get("segx"), c.get("segy")
    if (vx or vy) and sx is not None and math.isfinite(sx) and math.isfinite(sy):
        seg = math.hypot(sx - c["x"], sy - c["y"])
        mv = math.hypot(dx, dy)
        if mv > seg > 0:
            dx, dy = dx * seg / mv, dy * seg / mv
    return (c["x"] + dx, c["y"] + dy)


def speed(c):
    if not c or c.get("vx") is None:
        return 0.0
    return math.hypot(c["vx"] or 0.0, c["vy"] or 0.0)


MOVING_U_S = 10.0


def score_leg(tape, g, origin, dest):
    """The drawn body's behaviour on one granted leg. -> dict or None."""
    eta = dist(origin, dest) / RUN_SPEED
    W = tape.window(g - 0.15, g + eta + WINDOW_SLACK)
    if len(W) < 3:
        return None
    track = []
    for s in W:
        a = (s.get("agents") or {}).get("1") or {}
        bl = live(a.get("async"), s.get("clock1"))
        sl = live(a.get("sync"), s.get("clock0"))
        if bl and sl:
            track.append((tape.t0 + s["t"] - g, bl, sl, speed(a.get("async")), speed(a.get("sync")), Tape.fence(s)))
    if len(track) < 3:
        return None
    b0, s0 = track[0][1], track[0][2]
    body_move = max(dist(b, b0) for _t, b, _s, _bv, _sv, _f in track)
    sync_move = max(dist(s, s0) for _t, _b, s, _bv, _sv, _f in track)
    jumps = [dist(track[i][1], track[i - 1][1]) for i in range(1, len(track))]
    snap = max(jumps)
    snap_at = track[1 + jumps.index(snap)][0]
    sep = max(dist(b, s) for _t, b, s, _bv, _sv, _f in track)
    arrived_at = next((t for t, b, _s, _bv, _sv, _f in track if dist(b, dest) <= ARRIVE_U), None)
    horizon = arrived_at if arrived_at is not None else eta
    pre = [bv for t, _b, _s, bv, _sv, _f in track if t <= horizon + 1e-6]
    moving = sum(1 for v in pre if v > MOVING_U_S) / max(len(pre), 1)
    sync_moving = sum(1 for t, _b, _s, _bv, sv, _f in track if t <= horizon + 1e-6 and sv > MOVING_U_S) / max(len(pre), 1)
    end_to_dest = dist(track[-1][1], dest)
    fences = []
    prev = None
    for t, _b, _s, _bv, _sv, f in track:
        if prev is not None and f != prev:
            fences.append((round(t, 2), prev, f))
        prev = f
    if arrived_at is not None and snap < SNAP_U and moving >= 0.6:
        cls = "WALKED"
    elif moving < 0.2 and sync_move > 3 * PARK_U and snap >= SNAP_U:
        cls = "PARKED+SNAP"
    elif moving < 0.2 and sync_move > 3 * PARK_U:
        cls = "PARKED"
    else:
        cls = "OTHER"
    return {"eta": eta, "n": len(track), "body_move": body_move,
            "sync_move": sync_move, "moving": moving, "sync_moving": sync_moving,
            "snap": snap, "snap_at": snap_at, "max_sep": sep,
            "end_to_dest": end_to_dest, "arrived_at": arrived_at,
            "fences": fences, "class": cls, "body0": b0, "sync0": s0}


def legs_for(R, i_route):
    """The legs a router_route row granted. -> [(wall, dest, plane, label)]"""
    ev = R[i_route]
    v = ev.get("verdict")
    if v == "verbatim":
        return [(ev["wall_unix"], tuple(ev["dest"]), ev.get("plane_origin"), "verbatim")]
    if v == "clip-fallback":
        return [(ev["wall_unix"], tuple(ev["stop"]), ev.get("plane_origin"), "clip-fallback")]
    if v != "routed":
        return []
    out = []
    n = ev.get("n_wp")
    for r in R[i_route:]:
        if r.get("kind") == "router_leg" and r.get("act") == "grant":
            out.append((r["wall_unix"], tuple(r["dest"]), r.get("plane"),
                        "leg %d/%d" % (r["i"], r["n"])))
            if r.get("terminal") or (n and r["i"] >= n):
                break
        elif r.get("kind") == "router_route" and r is not ev:
            break
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?", help="harness run id (default newest)")
    ap.add_argument("--tape", help="agenttap tape (default: the one inside the run's window)")
    ap.add_argument("--map", type=int, default=146)
    a = ap.parse_args()

    from vaultpath import require_dir
    from pathmap import PathingMap
    import seamscout as S
    vault = require_dir()
    hroot = os.path.join(vault, "captures", "harness")
    rundir = os.path.join(hroot, a.run) if a.run else newest_run(hroot)
    rep = json.load(open(os.path.join(rundir, "report.json")))
    cap = [c.replace("\\", "/") for c in rep["captures"] if "gamesrv" in c.replace("\\", "/")]
    if not cap:
        print("run %s has no gamesrv capture" % rundir)
        return 1
    R, bad = load_rows(cap[0])
    clicks = [w for w in rep["walk"] if w["kind"] == "click"]
    if not clicks:
        print("run %s has no click steps" % rundir)
        return 1
    t_lo = min(w["started_unix"] for w in rep["walk"]) - 120
    t_hi = max(w["ended_unix"] for w in rep["walk"]) + 60
    tapes = sorted(glob.glob(os.path.join(vault, "research", "animref", "agenttap-*.jsonl")))
    tpath = a.tape or pick_tape(tapes, t_lo, t_hi)
    if not tpath:
        print("no agenttap tape found")
        return 1
    tape = Tape(tpath)
    in_window = t_lo <= tape.t0 <= t_hi
    pm = PathingMap.load(MAP_FILE[a.map])
    print("run %s   capture %s (%d rows, %d unparseable)" % (os.path.basename(rundir), os.path.basename(cap[0]), len(R), bad))
    print("tape %s: %d samples%s" % (os.path.basename(tpath), len(tape.samples),
                                     "" if in_window else "   <-- NOT inside the run's window; joins below are suspect"))

    moves = [(i, r) for i, r in enumerate(R) if r.get("kind") == "decoded" and r.get("name") == "MOVE_TO_COORD"]
    routes = [(i, r) for i, r in enumerate(R) if r.get("kind") == "router_route"]
    results = []
    for k, w in enumerate(clicks):
        fx, fy = (float(v) for v in w["key"].split(","))
        m = [(i, r) for i, r in moves if w["started_unix"] - 0.3 <= r["wall_unix"] <= w["ended_unix"] + 2.0]
        print("\nclick %d  fx=%.3f fy=%.3f  at +%.2fs" % (k + 1, fx, fy, w["started_unix"] - clicks[0]["started_unix"]))
        if not m:
            print("   no MOVE_TO_COORD -- the click hit nothing the client would walk to")
            continue
        im, mv = m[0]
        land = tuple(mv["values"][1])
        ground = pm.walkable(*land)
        print("   MOVE_TO_COORD -> (%.0f, %.0f)  %s" % (land[0], land[1], "GROUND (on mesh)" if ground else "off-mesh (prop or void)"))
        rt = [(i, r) for i, r in routes if mv["wall_unix"] <= r["wall_unix"] <= mv["wall_unix"] + 1.5]
        if not rt:
            print("   no router_route answered it")
            continue
        ir, ev = rt[0]
        print("   ROUTER: %s%s" % (ev.get("verdict"), "" if ev.get("verdict") != "routed" else " (%d legs)" % ev.get("n_wp", 0)))
        if ev.get("verdict") in ("refused", "kbd-drop"):
            print("   reason: %s" % ev.get("reason"))
            continue
        for g, dest, plane, label in legs_for(R, ir):
            # the leg's origin: the sync copy at the grant (what the server walks)
            near = tape.window(g - 0.2, g + 0.2)
            o_sync = next((Tape.copy(s, "sync") for s in near if Tape.copy(s, "sync")), None)
            o_body = next((Tape.copy(s, "async") for s in near if Tape.copy(s, "async")), None)
            if o_sync is None:
                print("   %s -> (%.0f,%.0f): no tape sample at the grant" % (label, dest[0], dest[1]))
                continue
            if plane is None:
                plane = pm.plane_at(*o_sync)
            xs = S.seam_crossings(pm, o_sync, dest, plane=plane)
            blind = [c for c in xs if not c["linked"]]
            seam = "BLIND" if blind else ("PORTAL" if xs else "none")
            sc = score_leg(tape, g, o_sync, dest)
            print("   %s: (%.0f,%.0f) -> (%.0f,%.0f) on plane %s, %.0f u, ETA %.2fs   seam: %s"
                  % (label, o_sync[0], o_sync[1], dest[0], dest[1], plane, dist(o_sync, dest), dist(o_sync, dest) / RUN_SPEED, seam))
            for c in xs:
                print("      crosses %s -> %s at (%.0f,%.0f) f=%.2f  %s" % (c["from"], c["to"], c["at"][0], c["at"][1], c["f"], "portal" if c["linked"] else "BLIND"))
            if sc is None:
                print("      tape: too few samples in the window")
                results.append((seam, "NO-TAPE", label))
                continue
            print("      body: moving %.0f%% of the leg (sync %.0f%%), travelled %.0f u (sync %.0f u), "
                  "max separation %.0f u, largest live jump %.0f u%s, ends %.0f u from the grant%s  -> %s"
                  % (100 * sc["moving"], 100 * sc["sync_moving"], sc["body_move"], sc["sync_move"],
                     sc["max_sep"], sc["snap"],
                     "" if sc["snap"] < SNAP_U else " at +%.2fs" % sc["snap_at"],
                     sc["end_to_dest"],
                     "" if sc["arrived_at"] is None else ", arrived +%.2fs" % sc["arrived_at"], sc["class"]))
            if sc["fences"]:
                print("      fence: %s" % ", ".join("+%.2fs %s->%s" % f for f in sc["fences"]))
            if o_body and dist(o_body, o_sync) > ARRIVE_U:
                print("      NOTE: the drawn body was already %.0f u from the sync copy at the grant" % dist(o_body, o_sync))
            results.append((seam, sc["class"], label))

    blind = [r for r in results if r[0] == "BLIND"]
    ctrl = [r for r in results if r[0] in ("PORTAL", "none") and r[1] != "NO-TAPE"]
    print("\n== CLAUSES ==")
    print("P1 exposure: %d granted leg(s) cross a BLIND seam   %s" % (len(blind), "OK" if len(blind) >= 2 else "BELOW FLOOR (2)"))
    if blind:
        from collections import Counter
        c = Counter(r[1] for r in blind)
        print("P2 on blind legs: %s" % dict(c))
        if c.get("WALKED", 0) == len(blind):
            print("   -> every blind leg was WALKED: no harm on this seam class (an honest null)")
        elif c.get("PARKED+SNAP", 0) + c.get("PARKED", 0) == len(blind):
            print("   -> every blind leg PARKED: RUN-1zAO's signature on a router grant -- the harm is real")
        else:
            print("   -> mixed; read the legs")
    if ctrl:
        from collections import Counter
        c = Counter(r[1] for r in ctrl)
        print("P3 control (portal / no-seam legs): %s   %s" % (dict(c), "OK" if c.get("WALKED", 0) == len(ctrl) else "CONTROL FAILED -- a non-blind leg did not walk normally"))
    else:
        print("P3 control: no portal or seam-free leg was granted -- the treatment cannot be read against a control from this run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
