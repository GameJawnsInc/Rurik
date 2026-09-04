#!/usr/bin/env python3
"""WORLD -> SCREEN for the harness's click verb (MOVECODE-1z-aw).

    python studies/movecode/review/clickaim.py --fit             # fit from captured runs
    python studies/movecode/review/clickaim.py --aim 520         # fy for a 520 u click

WHY. sec.1z-av ended the blind fan: seven runs of guessed screen fractions produced
ONE ground click the router answered. The click verb needs to be pointed at a
CHOSEN world point -- the route-forcing chord `mapscout.py` already computes --
and that is arithmetic, not another run.

THE MODEL, and every term in it is measured or fitted, none assumed:

    a screen row `fy` is a ray depressed by  theta + alpha(fy)  below horizontal
    it meets flat ground at horizontal range  H / tan(theta + alpha)  from the CAMERA
    the body sits  D  in front of the camera, so  range_from_body = H/tan(.) - D

  alpha(fy) = atan( (2*v(fy) - 1) * tan(FOV_v / 2) ),  v(fy) the fraction DOWN
  THE VIEWPORT -- and the viewport is not the window. `dc.click` takes its
  fractions from `GetWindowRect`, which includes the title bar and borders, so
  v(fy) = (fy - T) / S with T and S the viewport's top and height as window
  fractions. T and S are fitted rather than guessed at.

  FOV_v comes from the repo's own measurement: FOV_h = 75.000 deg HORIZONTAL
  (studies fovread/fovaxis), so tan(FOV_v/2) = tan(FOV_h/2) / aspect.

FOUR UNKNOWNS -- H, theta, T, S -- and D is folded into H and theta by the fit
rather than pretended to be independent, because a single centre-column sweep
cannot separate a camera that is higher from one that is further back.

★ IT IS FITTED ON ONE RUN AND SCORED ON ANOTHER. A projection fitted and reported
on the same points is a curve, not a prediction -- sec.1z-as's yaw calibration
earned its keep precisely by predicting `yaw:1500 -> 240.0` before the run, and
this file holds itself to the same test: `--fit` reports a HOLD-OUT error on
click->world pairs the fit never saw, and refuses to print an aim table if that
error is worse than the flat-ground assumption can excuse.

THE KNOWN HAZARD, on file before the first fit: sec.1z-as.3 measured the same `fy`
returning 511 u and 1,767 u where the ground falls away. FLAT GROUND IS AN
ASSUMPTION AND IT FAILS ON SLOPES -- so the fit is taken on the flattest ground the
mesh has, the aim table carries its residual, and a click aimed downhill will land
long. That is a reason to aim on open level ground, not a reason to distrust the
arithmetic.

★★ AND THE MODEL IS REFUTED. IT FAILED ITS OWN HOLD-OUT, AND THAT IS WHY THE GATE
IS HERE (MOVECODE-1z-aw). An eight-point sweep on the map's most open ground, every
click landing on GROUND and every body position read from the tape, came back:

    fy   0.36  0.42  0.48  0.54  0.60  0.66  0.70  0.44
    u     686   255  1057   923   141    62    83   464

**That is not monotone in `fy`, and no flat-ground camera at a fixed pitch can
produce it** -- a lower click must land nearer. Fitted on five and scored on three,
the hold-out came to **205 u mean and 569 u worst**, against an aiming need of
about +-100 u. So `--aim` refuses to print a table: a curve fitted through
non-monotone data would have looked fine on its own residual and been wrong in the
field.

THE DIAGNOSIS, and it names the fix: **the camera's pitch is not constant**, so
`fy` alone does not determine the ray, and no amount of fitting over `fy` will
recover a parameter that moves between samples.

THE ROUTE, which is a READ rather than a fit and needs no new derivation:
`toolkit/clientscan/fovread.py` ALREADY reads the client's live camera --
`Position` at `0x00C07860`, `Target` at `0x00C0786C` and `fov` at `0x00C078C4`,
the same three the frustum builder's own failure path prints. Position, target and
FOV are the entire view transform, so world->screen becomes exact arithmetic
evaluated per click instead of a model fitted across clicks, and a varying pitch
stops being an error term because it is being read. **This file's own approach was
the wrong one, and the instrument that replaces it was built for a different
question two arcs ago.**

Read-only over captured runs. Stdlib only.
"""
import argparse
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "clientscan"))

FOV_H = 75.0             # degrees, MEASURED (studies fovread/fovaxis)
DEFAULT_ASPECT = 1936.0 / 1040.0


def fov_v(aspect=DEFAULT_ASPECT):
    return 2.0 * math.degrees(math.atan(math.tan(math.radians(FOV_H / 2.0)) / aspect))


def ground_range(fy, H, theta_deg, top, span, aspect=DEFAULT_ASPECT):
    """Body-relative ground range for a centre-column click at `fy`.

    None when the ray points at or above the horizon -- there is no ground to
    hit, and returning a huge number instead would be a lie with a unit on it.
    """
    v = (fy - top) / span
    t = math.tan(math.radians(fov_v(aspect) / 2.0))
    alpha = math.atan((2.0 * v - 1.0) * t)
    dep = math.radians(theta_deg) + alpha
    if dep <= 1e-4:
        return None
    return H / math.tan(dep)


def fit(samples, aspect=DEFAULT_ASPECT):
    """Least-squares over (fy, range) by coarse-to-fine sweep. -> (params, rms).

    A grid search rather than a solver: four parameters, a few hundred points,
    and a closed form that is only valid where the ground really is flat. The
    search is transparent and cannot silently converge somewhere absurd.
    """
    best = None
    grid = [(200.0, 4000.0, 12), (5.0, 70.0, 12), (-0.20, 0.30, 10), (0.60, 1.40, 10)]
    centre = [1200.0, 30.0, 0.03, 0.95]
    for it in range(6):
        rngs = []
        for (lo, hi, n), c in zip(grid, centre):
            w = (hi - lo) / (2.0 ** it)
            rngs.append([max(lo, c - w / 2) + (min(hi, c + w / 2) - max(lo, c - w / 2))
                         * k / (n - 1) for k in range(n)])
        for H in rngs[0]:
            for th in rngs[1]:
                for top in rngs[2]:
                    for span in rngs[3]:
                        if span <= 0.1:
                            continue
                        s = n = 0
                        for fy, r in samples:
                            p = ground_range(fy, H, th, top, span, aspect)
                            if p is None:
                                s += 1e6
                                n += 1
                                continue
                            s += (p - r) ** 2
                            n += 1
                        rms = math.sqrt(s / max(n, 1))
                        if best is None or rms < best[0]:
                            best = (rms, (H, th, top, span))
        centre = list(best[1])
    return best[1], best[0]




# --- the camera the CLIENT reports, and the exact projection over it ---------
#
# MOVECODE-1z-ax. sec.1z-aw fitted a camera and was refuted by its own hold-out:
# the ranges came back NON-MONOTONE in `fy`, which no fixed camera can produce,
# because the pitch moves between samples. So the camera is READ instead --
# `fovread.py` already locates all three terms of the view transform, from the
# frustum builder's own failure path:
#
#     Position  0x00C07860   Target  0x00C0786C   fov  0x00C078C4
#
# With position, target and fov there is nothing left to fit: the transform is
# evaluated PER CLICK from the client's own state, and a pitch that varies stops
# being an error term because it is being measured.
#
# TWO THINGS HERE ARE NOT YET ESTABLISHED, and both are marked at the call site
# rather than buried:
#   * WHICH AXIS IS UP in Position/Target. The movement wire is (x, y) with the
#     pathing file carrying NO HEIGHT, so the third float is presumably height --
#     but "presumably" is not a measurement, and `UP_AXIS` exists so a run can
#     settle it rather than a comment asserting it.
#   * WHETHER `fov` as read is the FULL angle or the HALF one. `fovread.describe`
#     prints both readings precisely because it is unsettled; sec.fovaxis settled
#     the AXIS as horizontal at 75.000 deg, which is the full-angle reading, and
#     that is what `FOV_IS_FULL_ANGLE` selects.
#
# THE VIEWPORT OFFSET IS NOT FITTED EITHER, and that is the other half of the
# sec.1z-aw correction. `dc.click` takes its fractions from GetWindowRect, which
# includes the title bar and borders; the client renders into the CLIENT rect.
# The difference is readable exactly (GetClientRect + ClientToScreen), so
# `viewport_in_window()` measures it instead of the four-parameter fit sec.1z-aw
# used. Nothing about the window's chrome should ever have been a fitted term.

# MEASURED by RUN-1zAY (sec.1z-ay.2), not presumed: re-scoring one capture under
# five (up, fov) variants put the declared reading at a 1.02 deg mean bearing
# residual against 9.35 deg for the next best -- a factor of nine. The
# off-centre click columns are what made that a real test; at fx=0.5 a wrong
# horizontal FOV is invisible. `fov` reads 1.30900 rad = 75.000 deg EXACTLY on
# a live client, which is sec.fovaxis confirmed from the running process.
UP_AXIS = (0.0, 0.0, 1.0)      # MEASURED (RUN-1zAY)
FOV_IS_FULL_ANGLE = True       # MEASURED (RUN-1zAY); sec.fovaxis's axis


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _norm(a):
    L = math.sqrt(_dot(a, a))
    return (a[0] / L, a[1] / L, a[2] / L) if L > 1e-9 else None


def basis(pos, target, up=UP_AXIS):
    """(forward, right, up) for the camera, or None if it is degenerate."""
    f = _norm(_sub(target, pos))
    if f is None:
        return None
    r = _norm(_cross(f, up))
    if r is None:                 # looking straight along `up`
        return None
    return f, r, _cross(r, f)


def project(world, pos, target, fov, aspect=DEFAULT_ASPECT, up=UP_AXIS):
    """A world point -> (fx, fy) in VIEWPORT fractions, or None if behind.

    Viewport, not window: `viewport_in_window()` converts, and it MEASURES the
    chrome rather than fitting it.
    """
    b = basis(pos, target, up)
    if b is None:
        return None
    f, r, u = b
    v = _sub(world, pos)
    depth = _dot(v, f)
    if depth <= 1e-6:
        return None
    fh = fov if FOV_IS_FULL_ANGLE else fov * 2.0
    th = math.tan(fh / 2.0)
    tv = th / aspect
    return (0.5 + (_dot(v, r) / (depth * th)) / 2.0,
            0.5 - (_dot(v, u) / (depth * tv)) / 2.0)


def ray(fx, fy, pos, target, fov, aspect=DEFAULT_ASPECT, up=UP_AXIS):
    """The world-space direction a VIEWPORT fraction looks along."""
    b = basis(pos, target, up)
    if b is None:
        return None
    f, r, u = b
    fh = fov if FOV_IS_FULL_ANGLE else fov * 2.0
    th = math.tan(fh / 2.0)
    tv = th / aspect
    sx = (fx - 0.5) * 2.0 * th
    sy = (0.5 - fy) * 2.0 * tv
    return _norm((f[0] + r[0] * sx + u[0] * sy,
                  f[1] + r[1] * sx + u[1] * sy,
                  f[2] + r[2] * sx + u[2] * sy))


def to_ground(fx, fy, pos, target, fov, ground_z,
              aspect=DEFAULT_ASPECT, up=UP_AXIS):
    """Where a viewport fraction meets the plane z = ground_z, or None.

    None when the ray does not descend to the plane -- a click at or above the
    horizon has no ground point, and inventing a distant one would be a lie with
    a unit on it (the same rule sec.1z-aw's `ground_range` follows).
    """
    d = ray(fx, fy, pos, target, fov, aspect, up)
    if d is None or abs(d[2]) < 1e-9:
        return None
    t = (ground_z - pos[2]) / d[2]
    if t <= 0:
        return None
    return (pos[0] + d[0] * t, pos[1] + d[1] * t, ground_z)


def viewport_in_window(hwnd):
    """(top, span) of the client area as fractions of the WINDOW rect.

    MEASURED, not fitted. sec.1z-aw carried these as two of its four fitted
    parameters, which is how a window border ended up inside a camera model.
    """
    import ctypes
    from ctypes import wintypes
    u = ctypes.windll.user32
    w = wintypes.RECT()
    c = wintypes.RECT()
    if not u.GetWindowRect(hwnd, ctypes.byref(w)):
        return None
    if not u.GetClientRect(hwnd, ctypes.byref(c)):
        return None
    p = wintypes.POINT(0, 0)
    u.ClientToScreen(hwnd, ctypes.byref(p))
    wh = w.bottom - w.top
    if wh <= 0:
        return None
    return ((p.y - w.top) / wh, (c.bottom - c.top) / wh)


def pairs_from_run(rundir, tape=None):
    """(fy, body-relative range) for every click leg, body from the TAPE.

    The tape, not the position reports: a click-walking client goes silent, and
    sec.1z-as's first calibration reported `nan` ranges for exactly that reason.
    """
    rep = json.load(open(os.path.join(rundir, "report.json")))
    caps = [c.replace("\\", "/") for c in (rep.get("captures") or [])
            if "gamesrv" in c.replace("\\", "/")]
    if not caps or not os.path.exists(caps[0]):
        return []
    R = [json.loads(l) for l in open(caps[0], encoding="utf-8") if l.strip()]
    moves = [(r["wall_unix"], tuple(r["values"][1])) for r in R
             if r.get("kind") == "decoded" and r.get("name") == "MOVE_TO_COORD"]
    if tape is None:
        return []
    from w0score import live
    rows = [json.loads(l) for l in open(tape, encoding="utf-8") if l.strip()]
    head = next(r for r in rows if r.get("kind") == "head")
    S = [r for r in rows if r.get("kind") == "sample"]

    def body(w):
        best = None
        for s in S:
            if head["t0"] + s["t"] <= w:
                a = (s["agents"].get("1") or {}).get("async")
                if a and "x" in a:
                    best = live(a, s.get("clock1"))
            else:
                break
        return best

    out = []
    for w in [x for x in rep["walk"] if x["kind"] == "click"]:
        m = [(t, d) for t, d in moves
             if w["started_unix"] - 0.3 <= t <= w["ended_unix"] + 2.0]
        b = body(w["started_unix"])
        if not m or not b:
            continue
        fx, fy = (float(p) for p in w["key"].split(","))
        if abs(fx - 0.5) > 1e-6:
            continue                     # centre column only: no lateral term yet
        d = m[0][1]
        out.append((fy, math.hypot(d[0] - b[0], d[1] - b[1])))
    return out


# --- the self-check, movetap's precedent -------------------------------------
# NOT a `test_*.py`: `run_suite.py` walks `toolkit/` only, and `test_srclint`
# section 7 requires every name in TESTS.md to EXIST there -- so a test file
# under `studies/` is both undiscovered by the suite and a stale entry in the
# list. `movetap.py --selftest` is the pattern for a study tool that wants its
# checks to travel with it, and this follows it rather than bending the lint.
import checks                                                    # noqa: E402

LEDGER = checks.Ledger("clickaim read-camera projection", floor=12)
check = checks.adopt_named(LEDGER)

BODY = (1000.0, 2000.0, 0.0)
POS = (400.0, 2000.0, 400.0)        # 600 u behind, 400 up
TGT = (1000.0, 2000.0, 80.0)
FOV = math.radians(75.0)            # sec.fovaxis: 75.000 deg HORIZONTAL


def selftest():
    print("\n1. the projection's algebra")
    for dx in (200.0, 600.0, 1500.0):
        W = (BODY[0] + dx, BODY[1], 0.0)
        s = project(W, POS, TGT, FOV)
        back = to_ground(s[0], s[1], POS, TGT, FOV, 0.0) if s else None
        err = math.hypot(back[0] - W[0], back[1] - W[1]) if back else 9e9
        check("a ground point at %4.0f u projects and unprojects to itself" % dx,
              err < 0.5,
              "err %.3f u -- if this drifts, every aimed click drifts with it" % err)

    s = project(BODY, POS, TGT, FOV)
    check("the body projects onto the CENTRE column",
          s is not None and abs(s[0] - 0.5) < 1e-6,
          "fx=%.4f (the camera is directly behind it)" % (s[0] if s else -1))

    check("a point BEHIND the camera returns None, never a coordinate",
          project((POS[0] - 500.0, POS[1], 0.0), POS, TGT, FOV) is None,
          "a projection that wrapped would aim a click at the opposite horizon")

    level = ((400.0, 2000.0, 120.0), (1000.0, 2000.0, 110.0))
    check("a ray ABOVE the horizon returns None, never a distant invention",
          to_ground(0.5, 0.02, level[0], level[1], FOV, 0.0) is None,
          "sec.1z-aw's own rule: no ground there is an answer, not a number")

    # sec.1z-as measured 12.5 px/degree on the client. Here the same 24 deg step
    # is asked of the GEOMETRY, from the measured FOV alone.
    W = (BODY[0] + 1000.0, BODY[1], 0.0)
    s0 = project(W, POS, TGT, FOV)
    a = math.radians(24.0)
    t2 = (POS[0] + math.cos(a) * (TGT[0] - POS[0]) - math.sin(a) * (TGT[1] - POS[1]),
          POS[1] + math.sin(a) * (TGT[0] - POS[0]) + math.cos(a) * (TGT[1] - POS[1]),
          TGT[2])
    s1 = project(W, POS, t2, FOV)
    want = (math.tan(math.radians(24.0)) / math.tan(math.radians(37.5))) / 2.0
    got = abs(s1[0] - s0[0]) if s1 else None
    check("a 24 deg yaw shifts a fixed point by the FOV's own fraction",
          got is not None and abs(got - want) < 0.02,
          "%.3f vs %.3f -- sec.1z-as's yaw:300 step falling OUT of the geometry "
          "rather than being assumed by it" % (got or -1, want))

    print("\n2. the V, and the correction sec.1z-aw owes")
    f, r, u = basis(POS, TGT)
    rows = [x / 100.0 for x in range(30, 77, 6)]
    signed, dist = [], []
    for fy in rows:
        g = to_ground(0.5, fy, POS, TGT, FOV, 0.0)
        if g is None:
            continue
        signed.append((g[0] - BODY[0]) * f[0] + (g[1] - BODY[1]) * f[1])
        dist.append(math.hypot(g[0] - BODY[0], g[1] - BODY[1]))
    check("SIGNED range along the view direction decreases monotonically with fy",
          all(a > b for a, b in zip(signed, signed[1:])),
          "this is the quantity a camera model is monotone in")
    check("UNSIGNED |ground - body| is NOT monotone -- it is V-shaped",
          not all(a > b for a, b in zip(dist, dist[1:])),
          "clicks BELOW the body's row land between camera and body, so the "
          "distance rises again. sec.1z-aw measured THIS and read the V as proof "
          "that no fixed camera could fit -- half its evidence was geometry")
    fyb = project(BODY, POS, TGT, FOV)[1]
    lo = min(range(len(dist)), key=lambda i: dist[i])
    check("the V's minimum sits at the BODY's own screen row",
          abs(rows[lo] - fyb) < 0.06,
          "min at fy=%.2f, body at fy=%.2f" % (rows[lo], fyb))

    print("\n3. the terms that are NOT established, pinned so a change is deliberate")
    check("UP_AXIS is +z, and the file records it as MEASURED",
          UP_AXIS == (0.0, 0.0, 1.0)
          and "MEASURED (RUN-1zAY)" in open(os.path.abspath(__file__),
                                            encoding="utf-8").read(),
          "RUN-1zAY re-scored one capture under five (up, fov) variants: 1.02 deg "
          "against 9.35 for the next best")
    check("fov is read as the FULL angle, per sec.fovaxis",
          FOV_IS_FULL_ANGLE is True,
          "fovread.describe prints both readings BECAUSE it was unsettled; "
          "fovaxis settled the axis at 75.000 deg horizontal")
    return LEDGER.verdict()



def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true",
                    help="the bare-machine checks (no client, no vault)")
    ap.add_argument("--fit", action="store_true")
    ap.add_argument("--aim", type=float, help="body-relative range in units")
    ap.add_argument("--runs", nargs="*", help="harness run stamps to fit on")
    a = ap.parse_args()
    print("FOV_h %.3f deg (measured) -> FOV_v %.2f deg at aspect %.3f"
          % (FOV_H, fov_v(), DEFAULT_ASPECT))
    print("This file is a MODEL over flat ground; sec.1z-as.3's slope hazard applies.")
    if a.selftest:
        return selftest()
    if a.aim is not None:
        print("\n--aim needs a fit first (--fit), and the fit needs a level-ground "
              "click sweep\nwith a tape over it. See the module header.")
    if a.fit:
        print("\n--fit reads harness runs whose click legs sit on the CENTRE column "
              "and\nwhose tape gives the body at each click. Pass --runs <stamp> ...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
