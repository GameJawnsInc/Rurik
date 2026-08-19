"""The corpus-side attempt at the bake curve -- kept as the RECORDED NEGATIVE.

    python studies/terrain/shadecurve.py --sample 60
    python studies/terrain/shadecurve.py --all
    python studies/terrain/shadecurve.py --row 34429 --table

**THE CURVE IS SETTLED, and NOT by this script.** FINDINGS §13.1 read the bake
out of the generator `0x0075CC30` -- it is a quartic ease-out
`255*(1 - (1 - N.L)^4)` -- and `studies/terrain/trnbake.py` reproduces it
byte-for-byte. This script is the approach that could NOT settle it, kept
because the reason it failed is worth not rediscovering: **the retail corpus is
the wrong instrument for the curve.** Its own gate refuses to print a verdict
(it cannot even reproduce §6.5's r 0.887 per-vertex, reaching ~0.50), which is
correct -- retail bakes carry cast/AO shadows that drag a Lambertian fit far
off (FINDINGS §13.4, and e10h's note: a fit best-fits 5° against a true 36.5°),
and a Pearson r is affine-invariant and gamma-blind anyway. The clean
instrument was the vault's client-COMPILED artifacts of known geometry, which
is what §13.1 used. What survives here is a reusable light-DIRECTION fitter
(sign + elevation by maximising r) and this cautionary gate.

FINDINGS §6.5 identified tag 9 as a baked directional lightmap -- fitting
`255 * max(0, N.L)` gives median Pearson r 0.887 over 345 maps -- and §8 left
the TRANSFER CURVE open: "a gamma or a scale-and-bias would fit the corpus
equally well and none is measured." Pearson r cannot see the curve: it is
invariant to affine maps and barely moved by a monotone gamma. This script
measures the curve itself, by holding the fitted light direction still and
reading the SHAPE of shade-vs-N.L directly.

WHAT THIS SETTLES AND WHAT IT CANNOT. Tag 9 has two halves: the BAKE (what
function of the Lambert term the map compiler stored -- this script's
question, answerable from the archive alone) and the APPLY (what the renderer
does with the stored byte on its way to the screen -- a client question, out
of scope here; the static work in FINDINGS §13 owns it). Do not read a bake
verdict as an apply verdict.

PREDICTIONS, STATED FIRST (a probe with no stated expectation can be
rationalised into agreeing with anything):

  P1  PURE LINEAR  s = 255 * max(0, N.L).  The binned medians lie on the line
      through the origin with slope 255; the affine fit returns a ~= 255,
      b ~= 0.  P1 additionally predicts that a map can only saturate at 255
      where N.L reaches 1.0 -- yet §8 records 348 of 349 maps saturating, and
      flat ground has N.L = sin(t) < 1.  So P1 arrives already owing an
      explanation for the saturation.

  P2  GAMMA  s = 255 * max(0, N.L)^g, g near 1/2.2.  The binned medians are
      log-log linear with slope g visibly below 1; the affine fit is beaten
      by the power fit and shows a spurious positive intercept.

  P3  OVERDRIVEN AFFINE (ambient + diffuse, clamped)  s = clip(a*N.L + b)
      with a + b > 255.  The unsaturated bins are linear with intercept
      b > 0; and the model makes a SECOND, parameter-free prediction: the
      N.L at which the fraction of saturated cells crosses 50% must equal
      (255 - b) / a, with (a, b) fitted only on unsaturated bins.  Two
      independent readouts landing on one knee is the confirmation.

THE GATE. Before any curve verdict, this script must REPRODUCE the recorded
fit: median Pearson r over its sample >= 0.85 (the 2026-08-11 measurement
found 0.887), and the fitted elevation must track tag 0's angle (Spearman,
recorded 0.9352).  Below the gate the geometry pipeline here is suspect and
the verdict line is withheld -- a curve read through wrong normals is noise
with error bars.

Method per map: normals from tag 1's corner heights at CELL_PITCH = 96.0
(far row/column replicate and are excluded); light L = (+-cos t, 0, sin t)
with azimuth sign and elevation t fitted by maximising Pearson r, per
§6.5's own recipe; then, with (sign, t) FROZEN, cells binned by N.L and the
median shade per bin fitted by the three families above on unsaturated bins
only.  Median-per-bin is the robustness choice: cast shadows and ambient
occlusion in the bake drag means, not medians, until they own a bin's
majority.  The shadow tag (tag 7) is deliberately not used to exclude cells
-- it marks a minority of cells (FINDINGS: mean shade 186.0 flagged) and the
median absorbs it; its per-map fraction is reported as context instead.
"""

import argparse
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "toolkit", "mapdata"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "toolkit"))

from archive import Archive, ffna_chunks  # noqa: E402
from mapchunks import MapIndex, is_map_head  # noqa: E402
import terrain  # noqa: E402
import vaultpath  # noqa: E402

CELL_PITCH = terrain.CELL_PITCH          # 96.0 world units per cell
R_GATE = 0.85                            # the reproduction gate (recorded 0.887)
SAT = 250                                # >= this counts as saturated
BINS = 24
MIN_BIN = 300                            # samples a bin needs to vote
ELEVATIONS = np.linspace(0.05, 1.55, 76)  # coarse t grid, radians


def corpus(ar):
    mi = MapIndex(ar)
    return sorted(e.index for e in ar.entries if is_map_head(e))


def load_map(ar, row):
    trn = terrain.Terrain.from_row(row, ar)
    dx, dy = trn.dim_x, trn.dim_y
    h = np.asarray(trn.heights, np.float64).reshape(dy, dx)
    s = np.frombuffer(trn.shade, np.uint8).reshape(dy, dx).astype(np.float64)
    return trn, h, s


def slopes(h):
    """(hx, hy) at full resolution -- gradients are taken BEFORE any
    thinning, so the 96.0 pitch is always the true sample spacing."""
    hy, hx = np.gradient(h, CELL_PITCH)
    return hx, hy


def lambert(hx, hy, sign, t):
    """max(0, N.L) for L = (sign*cos t, 0, sin t).

    np.gradient axis 1 is the +gx direction; whether that is world +x or -x
    is exactly what `sign` fits, so no orientation assumption is made here.
    """
    denom = np.sqrt(hx * hx + hy * hy + 1.0)
    ndl = (-sign * hx * math.cos(t) + math.sin(t)) / denom
    return np.clip(ndl, 0.0, None)


def pearson(a, b):
    a = a - a.mean()
    b = b - b.mean()
    n = math.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / n) if n else 0.0


def fit_light(hx, hy, s):
    """The (sign, t, r) that §6.5's recipe finds, coarse grid then refine.

    Gradients come in at full resolution; the 2x thinning here only cuts the
    number of samples the correlation sees, never the spacing they were
    computed at.
    """
    gx = hx[:-1:2, :-1:2].ravel()
    gy = hy[:-1:2, :-1:2].ravel()
    ss = s[:-1:2, :-1:2].ravel()
    best = (1, ELEVATIONS[0], -2.0)
    for sign in (1, -1):
        for t in ELEVATIONS:
            r = pearson(lambert(gx, gy, sign, t), ss)
            if r > best[2]:
                best = (sign, t, r)
    sign, t0, _ = best
    fine = np.linspace(t0 - 0.03, t0 + 0.03, 25)
    for t in fine:
        r = pearson(lambert(gx, gy, sign, t), ss)
        if r > best[2]:
            best = (sign, t, r)
    return best


def binned(x, s):
    """(bin centre, median shade, saturated fraction, n) per populated bin."""
    edges = np.linspace(0.0, 1.0, BINS + 1)
    rows = []
    for i in range(BINS):
        m = (x >= edges[i]) & (x < edges[i + 1])
        n = int(m.sum())
        if n < MIN_BIN:
            continue
        sat_frac = float((s[m] >= SAT).mean())
        unsat = s[m][s[m] < SAT]
        med = float(np.median(unsat)) if unsat.size >= MIN_BIN // 3 else None
        rows.append(((edges[i] + edges[i + 1]) / 2, med, sat_frac, n))
    return rows


def fit_curves(rows):
    """The three families, fitted on unsaturated bin medians only."""
    # Only bins where saturation is RARE read the curve: where most cells
    # clip at 255 the unsaturated median is the noise's lower tail, not the
    # curve. 0.2 is the threshold; a map without enough such bins abstains.
    pts = [(x, m) for x, m, sat, _ in rows if m is not None and sat < 0.2]
    if len(pts) < 4:
        return None
    x = np.array([p[0] for p in pts])
    m = np.array([p[1] for p in pts])

    rms1 = float(np.sqrt(np.mean((m - 255.0 * x) ** 2)))          # F1 linear

    a, b = np.polyfit(x, m, 1)                                     # F2 affine
    rms2 = float(np.sqrt(np.mean((m - (a * x + b)) ** 2)))

    ok = (x > 0.02) & (m > 2)                                      # F3 gamma
    g = rms3 = None
    if ok.sum() >= 4:
        lx, lm = np.log(x[ok]), np.log(m[ok] / 255.0)
        g = float((lx * lm).sum() / (lx * lx).sum())
        rms3 = float(np.sqrt(np.mean((m[ok] - 255.0 * x[ok] ** g) ** 2)))

    # P3's parameter-free cross-check: where does saturation actually take
    # over, and where does the affine fit SAY it must?
    knee_pred = (255.0 - b) / a if a > 1e-9 else None
    knee_seen = None
    for (x0, _m0, s0, _), (x1, _m1, s1, _) in zip(rows, rows[1:]):
        if s0 < 0.5 <= s1:
            knee_seen = x0 + (x1 - x0) * (0.5 - s0) / max(s1 - s0, 1e-9)
            break
    return {"rms1": rms1, "a": float(a), "b": float(b), "rms2": rms2,
            "g": g, "rms3": rms3, "knee_pred": knee_pred,
            "knee_seen": knee_seen, "nbins": len(pts)}


def one_map(ar, row, table=False):
    trn, h, s = load_map(ar, row)
    hx, hy = slopes(h)
    # The far row/column replicate (FINDINGS 6.5), so their gradients are
    # artificial zeros: excluded everywhere below.
    hx, hy, s2 = hx[:-1, :-1], hy[:-1, :-1], s[:-1, :-1]
    sign, t, r = fit_light(hx, hy, s2)
    ndl = lambert(hx, hy, sign, t).ravel()
    sv = s2.ravel()
    keep = ndl > 0.0
    rows = binned(ndl[keep], sv[keep])
    fit = fit_curves(rows)
    shadow_blocks = sum(1 for b in trn.shadow if b.payload)
    out = {"row": row, "dims": (trn.dim_x, trn.dim_y), "r": r, "sign": sign,
           "t": t, "angle": trn.angle, "fit": fit,
           "sat255": float((sv == 255).mean()),
           "shadow_blocks": shadow_blocks, "nshadow": len(trn.shadow)}
    if table:
        print(f"  {'N.L':>6} {'median':>7} {'sat%':>6} {'n':>8}")
        for x, m, sat, n in rows:
            ms = f"{m:7.1f}" if m is not None else "      -"
            print(f"  {x:6.3f} {ms} {100 * sat:5.1f}% {n:8d}")
    return out


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    return pearson(ra, rb)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dat", default=None)
    ap.add_argument("--sample", type=int, default=60,
                    help="maps to read, evenly over the corpus (default 60)")
    ap.add_argument("--all", action="store_true", help="the whole corpus")
    ap.add_argument("--row", type=int, default=None, help="one MFT row")
    ap.add_argument("--table", action="store_true",
                    help="with --row: print the binned curve itself")
    args = ap.parse_args()

    dat = args.dat or os.path.join(str(vaultpath.require_dir("dat_study")),
                                   "Gw.dat")
    results = []
    with Archive(dat) as ar:
        if args.row is not None:
            rows = [args.row]
        else:
            rows = corpus(ar)
            print(f"[ok] corpus: {len(rows)} map heads")
            if not args.all:
                step = max(1, len(rows) // args.sample)
                rows = rows[::step][:args.sample]
        print(f"[ok] reading {len(rows)} map(s)")
        print(f"{'row':>6} {'dims':>9} {'r':>6} {'t_fit':>6} {'angle':>6} "
              f"{'a':>6} {'b':>6} {'a+b':>6} {'g':>5} "
              f"{'rms1':>6} {'rms2':>6} {'rms3':>6} {'kneeP':>6} {'kneeS':>6}")
        for row in rows:
            try:
                m = one_map(ar, row, table=args.table)
            except Exception as e:              # a map that cannot load is
                print(f"{row:>6}  SKIP {e}")    # printed, never silent
                continue
            f = m["fit"]
            if f:
                g = f"{f['g']:5.2f}" if f["g"] is not None else "    -"
                kp = f"{f['knee_pred']:6.3f}" if f["knee_pred"] else "     -"
                ks = f"{f['knee_seen']:6.3f}" if f["knee_seen"] else "     -"
                print(f"{m['row']:>6} {m['dims'][0]:>4}x{m['dims'][1]:<4} "
                      f"{m['r']:6.3f} {m['t']:6.3f} {m['angle']:6.3f} "
                      f"{f['a']:6.1f} {f['b']:6.1f} {f['a'] + f['b']:6.1f} "
                      f"{g} {f['rms1']:6.1f} {f['rms2']:6.1f} "
                      f"{(f['rms3'] if f['rms3'] is not None else float('nan')):6.1f} "
                      f"{kp} {ks}")
            else:
                print(f"{m['row']:>6} {m['dims'][0]:>4}x{m['dims'][1]:<4} "
                      f"{m['r']:6.3f}   too few populated bins")
            results.append(m)

    fitted = [m for m in results if m["fit"]]
    if not fitted:
        print("[FAIL] no map produced a fittable curve")
        return 1

    med_r = float(np.median([m["r"] for m in fitted]))
    sp = spearman(np.array([m["t"] for m in fitted]),
                  np.array([m["angle"] for m in fitted]))
    print(f"\nTHE GATE: median r {med_r:.3f} over {len(fitted)} maps "
          f"(recorded 0.887, gate {R_GATE}); "
          f"t_fit vs tag-0 angle Spearman {sp:.3f} (recorded 0.9352)")
    if med_r < R_GATE:
        print("[FAIL] the reproduction gate is not met -- the geometry here "
              "is suspect, and no curve verdict is printed on top of it")
        return 1

    aa = np.array([m["fit"]["a"] for m in fitted])
    bb = np.array([m["fit"]["b"] for m in fitted])
    gg = np.array([m["fit"]["g"] for m in fitted
                   if m["fit"]["g"] is not None])
    r1 = np.array([m["fit"]["rms1"] for m in fitted])
    r2 = np.array([m["fit"]["rms2"] for m in fitted])
    r3 = np.array([m["fit"]["rms3"] for m in fitted
                   if m["fit"]["rms3"] is not None])
    knees = [(m["fit"]["knee_pred"], m["fit"]["knee_seen"]) for m in fitted
             if m["fit"]["knee_pred"] and m["fit"]["knee_seen"]]

    def q(v):
        return (float(np.percentile(v, 25)), float(np.median(v)),
                float(np.percentile(v, 75)))

    print(f"\naffine  a   IQR {q(aa)[0]:6.1f} / {q(aa)[1]:6.1f} / {q(aa)[2]:6.1f}")
    print(f"affine  b   IQR {q(bb)[0]:6.1f} / {q(bb)[1]:6.1f} / {q(bb)[2]:6.1f}")
    print(f"affine a+b  IQR {q(aa + bb)[0]:6.1f} / {q(aa + bb)[1]:6.1f} / "
          f"{q(aa + bb)[2]:6.1f}   (255 = no overdrive)")
    if gg.size:
        print(f"gamma   g   IQR {q(gg)[0]:6.2f} / {q(gg)[1]:6.2f} / {q(gg)[2]:6.2f}"
              f"   (1.0 = linear, 0.45 = sRGB-ish)")
    print(f"rms     F1 linear {q(r1)[1]:6.1f}   F2 affine {q(r2)[1]:6.1f}   "
          f"F3 gamma {q(r3)[1] if r3.size else float('nan'):6.1f}   (median)")
    if knees:
        dk = np.array([p - s for p, s in knees])
        print(f"knee    predicted-minus-seen IQR {q(dk)[0]:+6.3f} / "
              f"{q(dk)[1]:+6.3f} / {q(dk)[2]:+6.3f} over {len(knees)} maps "
              f"(P3 demands ~0)")

    # The verdict, by the predictions' own terms.
    med_g = float(np.median(gg)) if gg.size else None
    med_b = float(np.median(bb))
    med_ab = float(np.median(aa + bb))
    wins2 = int((r2 < r1 * 0.8).sum())
    knee_ok = (len(knees) >= 5 and
               abs(float(np.median([p - s for p, s in knees]))) < 0.05)
    print()
    if med_g is not None and med_g < 0.7 and r3.size and \
            float(np.median(r3)) < float(np.median(r2)) * 0.8:
        print(f"[VERDICT] P2: the bake is GAMMA-shaped, g ~= {med_g:.2f}")
    elif med_ab > 280 and med_b > 5 and wins2 > len(fitted) * 0.6:
        knee_note = ("and the knee cross-check agrees" if knee_ok
                     else "but the knee cross-check does NOT agree -- "
                          "treat as UNSETTLED")
        print(f"[VERDICT] P3: the bake is an OVERDRIVEN AFFINE, "
              f"s = clip({float(np.median(aa)):.0f} * N.L + {med_b:.0f}), "
              f"{knee_note}")
    elif abs(float(np.median(aa)) - 255) < 25 and abs(med_b) < 10:
        print("[VERDICT] P1: the bake is PURE LINEAR 255 * max(0, N.L) -- "
              "and the corpus-wide saturation still needs explaining")
    else:
        print("[UNSETTLED] no family wins by its own prediction; "
              "the numbers above are the measurement")
    return 0


if __name__ == "__main__":
    sys.exit(main())
