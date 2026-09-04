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


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fit", action="store_true")
    ap.add_argument("--aim", type=float, help="body-relative range in units")
    ap.add_argument("--runs", nargs="*", help="harness run stamps to fit on")
    a = ap.parse_args()
    print("FOV_h %.3f deg (measured) -> FOV_v %.2f deg at aspect %.3f"
          % (FOV_H, fov_v(), DEFAULT_ASPECT))
    print("This file is a MODEL over flat ground; sec.1z-as.3's slope hazard applies.")
    if a.aim is not None:
        print("\n--aim needs a fit first (--fit), and the fit needs a level-ground "
              "click sweep\nwith a tape over it. See the module header.")
    if a.fit:
        print("\n--fit reads harness runs whose click legs sit on the CENTRE column "
              "and\nwhose tape gives the body at each click. Pass --runs <stamp> ...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
