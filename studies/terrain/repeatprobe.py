"""Does the exported ground still repeat at cell period, at distance?

The last mechanism-level suspect for large-scale repetition died with
FINDINGS 7.18 (there is no second UV rectangle), so the question is now
empirical: composite the ground exactly as the exported artifact says to
draw it, and MEASURE the periodicity instead of eyeballing a render.
Texture space, no camera, no lighting -- the 7.5/7.16 compositor precedent,
rebuilt here because the original died with its session scratchpad.

PREDICTIONS, stated before the first run (house rule: a probe with no
stated expectation can be rationalised into agreeing with anything).

  P1  INSTRUMENT VALIDITY. The pinned pre-arc model (identity selector,
      variation quadrant 0 everywhere) must show autocorrelation peaks at
      cell-period lags far above its half-lag surroundings, because every
      same-configuration cell is byte-identical there. If P1 fails the
      instrument cannot see repetition and the run measured NOTHING.

  P2  THE QUESTION. If the closed mechanism (selection-sort selector,
      physical masks, PRNG base variation) is what stops the ground
      repeating, the exported model's peaks collapse toward the
      ideal-random-quadrant floor: full ~= random << pinned. If instead
      full ~= pinned, the export still repeats and -- with 7.2 refuted --
      there is no hypothesis left on the table.

The three conditions composited over identical regions:

  full    the artifact as shipped (layers.u16, variation.u8)
  pinned  base quadrant 0 everywhere, identity selector -- the pre-arc
          model, the known-repeating control
  random  base quadrant drawn uniformly per cell (fixed seed) -- the floor
          an ideal variation mechanism could reach with 4 quadrants

Before measuring anything the probe re-derives layers.u16 from tiles.u8 +
variation.u8 through trnblend and demands byte equality -- 7.15's lesson:
diff the artifact, not just the unit. A probe that composites a stale or
drifted artifact would measure the drift, not the ground.

Usage (any tree, finds the vault itself):

    python studies/terrain/repeatprobe.py kamadan
    python studies/terrain/repeatprobe.py lornars --res 8 --focus-res 32

Output: metrics on stdout, PNGs + a metrics.json under
vault/research/terrain/repeatprobe/. Requires numpy -- this is a
studies/ instrument, not toolkit/ (the stdlib-only rule governs toolkit/).
"""

import argparse
import json
import os
import struct
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "toolkit", "mapdata"))

import png                                # noqa: E402  toolkit/mapdata
import trnblend                           # noqa: E402  toolkit/mapdata
import trnvariation                       # noqa: E402  toolkit/mapdata
from toolkit import vaultpath             # noqa: E402

CELL_TEXELS = 111          # one cell = 111 texels of a 128x128 quadrant
QUAD_ORIGIN = 8.5          # the half-texel inset, FINDINGS 3.1
BLEND_LAYERS = 3
EMPTY = 0xFFFF
RANDOM_SEED = 0x5EED       # fixed: the probe must reproduce byte-for-byte


# ------------------------------------------------------------- loading

def load_map(name):
    """Everything the compositor needs, verified against the manifest."""
    root = vaultpath.vault_root()
    exports = os.path.join(root, "exports")
    with open(os.path.join(exports, f"{name}.gwmap.json")) as fh:
        manifest = json.load(fh)
    dims = manifest["dims"]
    dim_x, dim_y, cells = dims["x"], dims["y"], dims["cells"]

    def sidecar(kind, dtype, per_cell):
        side = next(s for s in manifest["sidecars"] if s["kind"] == kind)
        raw = open(os.path.join(exports, side["name"]), "rb").read()
        want = cells * per_cell * dtype().itemsize
        if len(raw) != want:
            raise SystemExit(f"[FAIL] {side['name']}: {len(raw)} bytes, "
                             f"manifest says {want}")
        return np.frombuffer(raw, dtype=dtype)

    layers = sidecar("layers", np.uint16, BLEND_LAYERS).reshape(cells, 3)
    tiles = sidecar("tiles", np.uint8, 1)
    variation = sidecar("variation", np.uint8, 1)
    shade = sidecar("shade", np.uint8, 1)

    textures = {}
    for entry in manifest["terrain_textures"]["tiles"]:
        img = entry["image"]
        if img is None:
            continue
        pixels, w, h, colour = png.read(os.path.join(exports, img))
        ch = {2: 3, 6: 4}[colour]
        arr = np.frombuffer(pixels, np.uint8).reshape(h, w, ch)
        if ch == 3:
            arr = np.concatenate(
                [arr, np.full((h, w, 1), 255, np.uint8)], axis=2)
        if (w, h) != (256, 256):
            raise SystemExit(f"[FAIL] {img} is {w}x{h}, not 256x256")
        textures[entry["tile"]] = arr.astype(np.float32) / 255.0

    return {"name": name, "manifest": manifest, "dim_x": dim_x,
            "dim_y": dim_y, "cells": cells, "layers": layers,
            "tiles": tiles, "variation": variation, "shade": shade,
            "table_a": manifest["tile_table_a"], "textures": textures}


# ------------------------------------- the artifact-vs-unit gate (7.15)

def pack_words(cell_layer_list):
    words = [EMPTY] * BLEND_LAYERS
    for s, lay in enumerate(cell_layer_list[:BLEND_LAYERS]):
        words[s] = ((0x8000 if lay.rotated else 0)
                    | ((lay.quadrant & 3) << 8) | (lay.tile & 0xFF))
    return words


def derive_words(m, variation, identity=False):
    """layers.u16 recomputed through trnblend, world row-major.

    `identity=True` reproduces the pre-arc model: no selector, corner 0 is
    the cell's own tile. Otherwise this is `mapexport.build_blend_layers`'
    exact loop, calling the same trnblend functions -- the point is to have
    ONE implementation of the rules and N callers, not a fourth copy.
    """
    dim_x, dim_y = m["dim_x"], m["dim_y"]
    tiles, table_a = m["tiles"], m["table_a"]
    out = np.empty((m["cells"], 3), np.uint16)
    for gy in range(dim_y):
        gy1 = min(gy + 1, dim_y - 1)
        row, row1 = gy * dim_x, gy1 * dim_x
        for gx in range(dim_x):
            gx1 = min(gx + 1, dim_x - 1)
            i = row + gx
            corners = (int(tiles[i]), int(tiles[row + gx1]),
                       int(tiles[row1 + gx]), int(tiles[row1 + gx1]))
            if identity:
                lays = trnblend.cell_layers(corners, table_a,
                                            int(variation[i]))
            else:
                sel = trnblend.corner_selector(
                    tuple(table_a[c] for c in corners))
                perm = tuple((sel >> (2 * k)) & 3 for k in range(4))
                lays = trnblend.cell_layers(
                    tuple(corners[p] for p in perm), table_a,
                    int(variation[i]), perm=perm)
            out[i] = pack_words(lays)
    return out


# ---------------------------------------------------------- compositing

def build_patches(m, res):
    """(word -> stack index), rgb[n,res,res,3], alpha[n,res,res].

    Nearest-texel sampling of the 111-texel window at `res` px per cell.
    u runs with world +x (gx), v with world +y (gy = image row); every
    layer of every cell uses the SAME convention, which is what 7.5's
    flipped-probe bug teaches -- a consistent flip cannot fake or hide a
    period, an inconsistent one manufactures one.
    """
    words = np.unique(m["layers"][m["layers"] != EMPTY])
    coords = QUAD_ORIGIN + (np.arange(res) + 0.5) * (CELL_TEXELS / res)
    idx = np.clip(coords.astype(np.int64), 0, 255)
    index, rgbs, alphas = {}, [], []
    for word in words:
        word = int(word)
        tile, quad, rot = word & 0xFF, (word >> 8) & 3, bool(word & 0x8000)
        tex = m["textures"][tile]
        window = tex[np.ix_(idx + 128 * (quad >> 1), idx + 128 * (quad & 1))]
        if rot:
            window = window[::-1, ::-1]
        index[word] = len(rgbs)
        rgbs.append(window[:, :, :3])
        alphas.append(window[:, :, 3])
    return index, np.stack(rgbs), np.stack(alphas)


def composite(m, words, res, with_shade):
    """uint8 (dimY*res, dimX*res, 3) for one condition's word array."""
    dim_x, dim_y, cells = m["dim_x"], m["dim_y"], m["cells"]
    index, rgbs, alphas = build_patches(
        {**m, "layers": words}, res)
    lut = np.zeros(1 << 16, np.int32)
    for word, k in index.items():
        lut[word] = k

    img = rgbs[lut[words[:, 0]]].copy()          # the opaque base
    for s in (1, 2):
        used = words[:, s] != EMPTY
        if not used.any():
            continue
        k = lut[words[used, s]]
        a = alphas[k][..., None]
        img[used] = img[used] * (1.0 - a) + rgbs[k] * a

    if with_shade:
        s = (m["shade"].reshape(dim_y, dim_x).astype(np.float32) / 255.0)
        sx = np.concatenate([s, s[:, -1:]], axis=1)     # replicate far col
        sxy = np.concatenate([sx, sx[-1:, :]], axis=0)  # and far row
        f = (np.arange(res, dtype=np.float32) + 0.5) / res
        w11 = f[:, None] * f[None, :]                   # toward (+x,+y)
        w01, w10 = f[None, :] - w11, f[:, None] - w11
        w00 = 1.0 - w01 - w10 - w11
        cell = (sxy[:-1, :-1].reshape(cells, 1, 1) * w00
                + sxy[:-1, 1:].reshape(cells, 1, 1) * w01
                + sxy[1:, :-1].reshape(cells, 1, 1) * w10
                + sxy[1:, 1:].reshape(cells, 1, 1) * w11)
        img *= cell[..., None]

    img = (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    return (img.reshape(dim_y, dim_x, res, res, 3)
               .transpose(0, 2, 1, 3, 4)
               .reshape(dim_y * res, dim_x * res, 3))


# -------------------------------------------------------------- metrics

def luma(img):
    return (img[..., 0] * 0.299 + img[..., 1] * 0.587
            + img[..., 2] * 0.114).astype(np.float32)


def autocorr_profiles(gray):
    """Normalised autocorrelation along +x and +y (lag 0 == 1.0)."""
    g = gray - gray.mean()
    f = np.fft.rfft2(g)
    ac = np.fft.irfft2(f * np.conj(f), s=g.shape)
    ac /= ac[0, 0]
    return ac[0, :], ac[:, 0]


def peak_stats(profile, period, k_max=8):
    """(corr, prominence) at lag k*period; prominence vs half-lag valleys."""
    out = {}
    half = max(1, period // 2)
    for k in range(1, k_max + 1):
        lag = k * period
        if lag + half >= len(profile):
            break
        valley = 0.5 * (profile[lag - half] + profile[lag + half])
        out[k] = (float(profile[lag]), float(profile[lag] - valley))
    return out


def neighbour_identical(m, words):
    """Fraction of adjacent cell pairs drawing byte-identical ground."""
    key = (words[:, 0].astype(np.int64)
           | (words[:, 1].astype(np.int64) << 16)
           | (words[:, 2].astype(np.int64) << 32))
    key = key.reshape(m["dim_y"], m["dim_x"])
    same_x = key[:, 1:] == key[:, :-1]
    same_y = key[1:, :] == key[:-1, :]
    total = same_x.size + same_y.size
    return float(same_x.sum() + same_y.sum()) / total


def focus_window(m, span=64):
    """The span x span cell window fullest of the map's modal base tile."""
    base = (m["layers"][:, 0] & 0xFF).reshape(m["dim_y"], m["dim_x"])
    vals, counts = np.unique(base, return_counts=True)
    modal = vals[np.argmax(counts)]
    hit = (base == modal).astype(np.float64)
    span_y = min(span, m["dim_y"])
    span_x = min(span, m["dim_x"])
    integral = hit.cumsum(0).cumsum(1)
    pad = np.zeros((m["dim_y"] + 1, m["dim_x"] + 1))
    pad[1:, 1:] = integral
    window = (pad[span_y:, span_x:] - pad[:-span_y, span_x:]
              - pad[span_y:, :-span_x] + pad[:-span_y, :-span_x])
    gy, gx = np.unravel_index(np.argmax(window), window.shape)
    frac = window[gy, gx] / (span_y * span_x)
    return int(gy), int(gx), span_y, span_x, int(modal), float(frac)


def crop_cells(m, words, gy, gx, span_y, span_x):
    sub = {**m, "dim_x": span_x, "dim_y": span_y, "cells": span_y * span_x}
    grid = words.reshape(m["dim_y"], m["dim_x"], 3)
    sub_words = grid[gy:gy + span_y, gx:gx + span_x].reshape(-1, 3)
    shade = m["shade"].reshape(m["dim_y"], m["dim_x"])
    sub["shade"] = shade[gy:gy + span_y, gx:gx + span_x].reshape(-1)
    return sub, np.ascontiguousarray(sub_words)


def mip(img, factor):
    h = img.shape[0] // factor * factor
    w = img.shape[1] // factor * factor
    x = img[:h, :w].astype(np.float32)
    x = x.reshape(h // factor, factor, w // factor, factor, -1)
    return (x.mean(axis=(1, 3)) + 0.5).astype(np.uint8)


# ----------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("map", help="export name, e.g. kamadan or lornars")
    ap.add_argument("--res", type=int, default=8,
                    help="px per cell for the whole-map metric (default 8)")
    ap.add_argument("--focus-res", type=int, default=32,
                    help="px per cell for the focus window (default 32)")
    ap.add_argument("--focus-span", type=int, default=64,
                    help="focus window size in cells (default 64)")
    ap.add_argument("--focus-at", metavar="GX,GY",
                    help="pin the focus window's top-left cell instead of "
                         "searching -- the search maximises tile uniformity "
                         "and on Kamadan that finds out-of-bounds filler")
    ap.add_argument("--skip-artifact-check", action="store_true",
                    help="trust layers.u16 without re-deriving it (fast "
                         "iteration only; a report must not use this)")
    args = ap.parse_args(argv)

    print(__doc__.splitlines()[0])
    print("P1: pinned control must peak at cell lags, or nothing was "
          "measured.\nP2: full ~= random << pinned means the mechanism "
          "works; full ~= pinned\n    means the ground still repeats and "
          "no hypothesis is left (7.18).\n")

    m = load_map(args.map)
    print(f"[ok] {args.map}: {m['dim_x']}x{m['dim_y']} cells, "
          f"{len(m['textures'])} textures")

    # `.variation.u8` is the AUTHORED tag 3 (0 = defer to the PRNG); the
    # layers artifact carries the RESOLVED quadrant. Feeding the authored
    # array in raw tripped the gate below on exactly 75.02% of cells --
    # P(draw != 0) -- the first time this probe ran.
    resolved = np.frombuffer(
        trnvariation.map_variation(m["dim_x"], m["dim_y"],
                                   m["variation"].tobytes()), np.uint8)

    # -- the 7.15 gate: the artifact must equal the unit before we measure
    if args.skip_artifact_check:
        print("[skip] artifact-vs-unit gate SKIPPED on request -- do not "
              "report numbers from this run")
        full = np.array(m["layers"], copy=True)
    else:
        full = derive_words(m, resolved)
        if np.array_equal(full, m["layers"]):
            print(f"[PASS] artifact gate: layers.u16 == trnblend over all "
                  f"{m['cells']} cells")
        else:
            bad = int((full != m["layers"]).any(axis=1).sum())
            raise SystemExit(
                f"[FAIL] artifact gate: layers.u16 differs from trnblend on "
                f"{bad} of {m['cells']} cells -- the export is stale or a "
                f"rule drifted again (7.15); re-export before measuring")

    # -- the three conditions
    pinned = derive_words(m, np.zeros(m["cells"], np.uint8), identity=True)
    rng = np.random.default_rng(RANDOM_SEED)
    random_words = np.array(full, copy=True)
    random_words[:, 0] = ((full[:, 0] & 0xFF)
                          | (rng.integers(0, 4, m["cells"],
                                          dtype=np.uint16) << 8))
    conditions = [("full", full), ("pinned", pinned),
                  ("random", random_words)]

    out_dir = os.path.join(vaultpath.vault_root(), "research", "terrain",
                           "repeatprobe")
    os.makedirs(out_dir, exist_ok=True)
    metrics = {"map": args.map, "res": args.res,
               "focus_res": args.focus_res, "conditions": {}}

    if args.focus_at:
        gx, gy = (int(v) for v in args.focus_at.split(","))
        span_y = min(args.focus_span, m["dim_y"] - gy)
        span_x = min(args.focus_span, m["dim_x"] - gx)
        print(f"[ok] focus window: {span_x}x{span_y} cells at ({gx},{gy}), "
              f"pinned by --focus-at\n")
    else:
        gy, gx, span_y, span_x, modal, frac = focus_window(m,
                                                           args.focus_span)
        print(f"[ok] focus window: {span_x}x{span_y} cells at ({gx},{gy}), "
              f"modal tile {modal} fills {frac:.1%}\n")

    for label, words in conditions:
        img = composite(m, words, args.res, with_shade=False)
        px, py = autocorr_profiles(luma(img))
        whole_x = peak_stats(px, args.res)
        whole_y = peak_stats(py, args.res)

        sub, sub_words = crop_cells(m, words, gy, gx, span_y, span_x)
        fimg = composite(sub, sub_words, args.focus_res, with_shade=False)
        fx, fy = autocorr_profiles(luma(fimg))
        focus_x = peak_stats(fx, args.focus_res)
        focus_y = peak_stats(fy, args.focus_res)

        cell_means = luma(mip(img, args.res))
        cx, cy = autocorr_profiles(cell_means)
        dist_x = peak_stats(cx, 1, k_max=4)
        dist_y = peak_stats(cy, 1, k_max=4)

        ident = neighbour_identical(m, words)

        metrics["conditions"][label] = {
            "whole_map": {"x": whole_x, "y": whole_y},
            "focus": {"x": focus_x, "y": focus_y},
            "cell_means": {"x": dist_x, "y": dist_y},
            "identical_neighbours": ident,
        }
        k1 = 0.5 * (whole_x[1][1] + whole_y[1][1])
        f1 = 0.5 * (focus_x[1][1] + focus_y[1][1])
        d1 = 0.5 * (dist_x[1][1] + dist_y[1][1])
        print(f"  {label:7s} prominence@1cell: whole {k1:+.4f}  "
              f"focus {f1:+.4f}  cell-means {d1:+.4f}  "
              f"identical-neighbours {ident:.3%}")

        png_img = composite(sub, sub_words, args.focus_res, with_shade=True)
        for suffix, arr in ((f"focus_{label}", fimg),
                            (f"focus_{label}_shade", png_img),
                            (f"focus_{label}_dist8", mip(fimg, 8))):
            h, w = arr.shape[:2]
            rgba = np.concatenate(
                [arr, np.full((h, w, 1), 255, np.uint8)], axis=2)
            png.write(os.path.join(
                out_dir, f"{args.map}_g{gx}_{gy}_{suffix}.png"),
                rgba.tobytes(), w, h)

    with open(os.path.join(out_dir,
                           f"{args.map}_g{gx}_{gy}_metrics.json"), "w") as fh:
        json.dump(metrics, fh, indent=1)
    print(f"\n[ok] PNGs and metrics under {out_dir}")

    # -- the verdict lines, mechanical so two runs read the same way
    c = metrics["conditions"]
    pin = 0.5 * (c["pinned"]["focus"]["x"][1][1]
                 + c["pinned"]["focus"]["y"][1][1])
    ful = 0.5 * (c["full"]["focus"]["x"][1][1]
                 + c["full"]["focus"]["y"][1][1])
    ran = 0.5 * (c["random"]["focus"]["x"][1][1]
                 + c["random"]["focus"]["y"][1][1])
    print()
    if pin < 0.05:
        print("[FAIL] P1: the pinned control does not peak -- the "
              "instrument cannot see repetition; this run measured NOTHING")
        return 1
    print(f"[PASS] P1: pinned control peaks at +{pin:.4f}")
    gap = (ful - ran) / (pin - ran) if pin > ran else float("nan")
    print(f"P2: full sits {gap:.1%} of the way from the random floor "
          f"({ran:+.4f}) to the pinned ceiling ({pin:+.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
