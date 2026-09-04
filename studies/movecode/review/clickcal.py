#!/usr/bin/env python3
"""Where does a harness `click:<fx>,<fy>` LAND in the world? (MOVECODE-1z-as)

    python studies/movecode/review/clickcal.py                 # newest harness run
    python studies/movecode/review/clickcal.py 20260904T131500

WHY THIS EXISTS. `session.py`'s walk plan has carried a `click:` verb since the
panel probes, and its own executor calls it *"a UI click at a FIXED window
fraction -- a panel button, not a world target"*; `parse_walk`'s docstring retires
the "this harness cannot aim" caveat *"for everything except a world-anchored
CLICK"*. So the primitive exists and has never been pointed at the ground: 4 runs
in the whole corpus use it, all at (0.39-0.41, 0.56-0.61), all UI.

sec.1z-ar needs click movement -- the ROUTER only runs on a click, and the whole
recent campaign is `--walk` keyboard-only, so there are no router grants under any
tape. This is the calibration that makes a click script writable.

THE AIMING PROBLEM IS REAL AND THIS DOES NOT SOLVE IT. Nothing here can decide
which world POINT a screen fraction hits -- that needs the scene. What it does
instead is measure the mapping empirically and let the WIRE report the answer:
the client turns the click into a `MOVE_TO_COORD` and tells us the world point it
chose. So a click script can be blind about aim and still be scoreable, because
every destination it produced is recorded. That is enough for a router probe,
which needs routed grants rather than a particular destination.

★ AND PROPS SWALLOW CLICKS -- the owner's observation, watching the calibration
run, and it is the reason this file classifies destinations at all:

    "your click landed on the bridge prop, which was obscuring what is the
     ground point you were trying to click. when you click a prop like that
     you'll walk in a straight line at it"

That is the harness's aiming limit stated exactly: **a prop occludes the ground
and takes the click**, and no screen fraction chosen at the desk can know it is
there. It explains the whole first calibration -- `verbatim` router verdicts (a
straight walk AT the prop, never a route), ranges jumping from ~550 u to 2,697 u
at the same `fy`, and `dest-off-mesh` refusals, because **we carry no prop
geometry** (sec.0.17's named remainder) so a prop surface point is never on our
navmesh.

So the mesh is the SENSOR: a click whose destination is off our navmesh is a prop
hit or out of bounds, and a click whose destination is on it reached the ground.
A blind script cannot aim, but a run can be SCORED on the subset that landed --
which is what makes a click probe possible at all without the owner at the
keyboard.

WHAT IT PRINTS, per click leg: the screen fraction, the body's position when the
click fired, the `MOVE_TO_COORD` the client sent, and the displacement in world
units -- range and bearing relative to the body's own facing where a heading is
known. Plus whether the router answered (a `grant_verdict` with a routed chain),
which is the thing sec.1z-ar actually wants exposure of.

Read-only over a harness run's report and its gamesrv capture. Stdlib only.
"""
import argparse
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))

HARNESS = "captures/harness"
MAP_146 = 0x1B97D    # the harness route's map


def newest_run(root):
    runs = sorted(glob.glob(os.path.join(root, "*", "report.json")))
    return os.path.dirname(runs[-1]) if runs else None


def load(rundir):
    rep = json.load(open(os.path.join(rundir, "report.json")))
    caps = [c.replace("\\", "/") for c in (rep.get("captures") or [])
            if "gamesrv" in c.replace("\\", "/")]
    if not caps or not os.path.exists(caps[0]):
        return rep, None
    return rep, [json.loads(l) for l in open(caps[0], encoding="utf-8") if l.strip()]


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", nargs="?", help="harness run stamp (default: newest)")
    a = ap.parse_args()

    import vaultpath
    root = vaultpath.vault_path("captures", "harness")
    rundir = os.path.join(root, a.run) if a.run else newest_run(root)
    if not rundir or not os.path.isdir(rundir):
        print("no harness run found -- this needs the vault.")
        return 1
    rep, R = load(rundir)
    if R is None:
        print("run %s has no gamesrv capture" % os.path.basename(rundir))
        return 1
    print("run %s" % os.path.basename(rundir))

    clicks = [w for w in (rep.get("walk") or []) if w.get("kind") == "click"]
    if not clicks:
        print("  no click: legs in this run -- nothing to calibrate, which is not "
              "a result. Drive a walk plan with click: steps.")
        return 1

    moves = [(r["wall_unix"], tuple(r["values"][1])) for r in R
             if r.get("kind") == "decoded" and r.get("name") == "MOVE_TO_COORD"]
    reports = [(r["wall_unix"], tuple(r["reported"])) for r in R
               if r.get("kind") == "position_report" and r.get("accepted")
               and r.get("reported")]
    routes = [(r["wall_unix"], r) for r in R if r.get("kind") == "router_route"]

    # The mesh is the prop sensor (see the header). Absent, every landing
    # reads "?" rather than a guess -- this file never invents a verdict it
    # cannot support.
    pm = None
    try:
        sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "mapdata"))
        from pathmap import PathingMap
        pm = PathingMap.load(MAP_146)
    except Exception as e:
        print("  (no mesh: %r -- the GROUND/prop column cannot be filled)" % (e,))

    def body_at(w):
        prev = None
        for t, p in reports:
            if t <= w:
                prev = p
            else:
                break
        return prev

    print("\n%-16s %-9s %-19s %-19s %8s  %-9s %s"
          % ("click fx,fy", "fired", "body at click", "MOVE_TO_COORD",
             "range", "landed", "router"))
    hit = ground = 0
    for w in clicks:
        s, e = w["started_unix"], w["ended_unix"]
        m = [(t, d) for t, d in moves if s - 0.3 <= t <= e + 2.0]
        b = body_at(s)
        if not m:
            print("%-16s %-9s %-19s %-19s %8s  %-9s %s"
                  % (w["key"], "NO MOVE", "-", "-", "-", "-",
                     "the click produced no movement command"))
            continue
        hit += 1
        t, d = m[0]
        rng = math.hypot(d[0] - b[0], d[1] - b[1]) if b else float("nan")
        rr = [v for vt, v in routes if t - 0.3 <= vt <= t + 1.5]
        land = "?" if pm is None else ("GROUND" if pm.walkable(d[0], d[1])
                                       else "prop/void")
        if land == "GROUND":
            ground += 1
        print("%-16s %-9s (%7.0f,%7.0f) (%7.0f,%7.0f) %8.1f  %-9s %s"
              % (w["key"], "yes",
                 (b[0] if b else 0), (b[1] if b else 0), d[0], d[1], rng, land,
                 (rr[0].get("verdict", "?") + "/" + str(rr[0].get("reason")))
                 if rr else "no router row"))

    print("\n  %d of %d click legs produced a MOVE_TO_COORD" % (hit, len(clicks)))
    if pm is not None:
        print("  %d of those landed on GROUND our mesh knows; the rest hit a prop "
              "or the void" % ground)
        print("  -- the owner's rule: a prop occludes the ground and takes the "
              "click, and the\n     client then walks a STRAIGHT LINE AT IT rather "
              "than routing. We carry no prop\n     geometry, so off-mesh IS the "
              "prop signature and this column is the sensor.")
    if hit == 0:
        print("  -> the click verb does not reach the WORLD in this configuration; "
              "a router\n     probe cannot be built on it until that is understood.")
        return 1
    print("  -> the verb reaches the world; a click script is writable, and every "
          "destination\n     it produces is recorded on the wire whatever the "
          "screen fraction meant.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
