"""Check the terrain interchange, and check the ORIENTATION against a different chunk.

THE HEADLINE IS SECTION 5 AND IT IS NOT OUR CODE AGREEING WITH OUR CODE. An
exporter verified by our own importer proves nothing -- `CLAUDE.md` says so in
those words -- so the layout is scored against the props chunk `0x20000004`,
which `mapexport.py` never reads and which no part of this pipeline produced.
Every prop carries a world `(x, y, z)`; sample the exported height field at
`(x, y)` and compare with `z`. A wrong de-tiling, a flipped row order or a wrong
pitch all move the sampled height away from the prop that is standing on it.

  Three rival layouts ship alongside as controls and every one must collapse:
  the y-flip (`gy = int((wy-y0)/96)`), the x-flip, and NOT DE-TILING at all --
  reading tag 1's 32x32 storage order as if it were already world row-major.
  The brief for this rung says the de-tiling is the thing most likely to be
  wrong, so it gets its own control rather than being covered by implication.

  The controls' collapse is what makes the number evidence. A baseline of 0.30
  means nothing on its own; a baseline of 0.30 against 0.03 for the same field
  read four cells to the left means the layout is placed.

WHAT THE MEASUREMENT PREDICTED BEFORE IT RAN. FINDINGS 4 measured this corpus-
wide at median |dz| 97.4 and a within-100 fraction of 0.504, against 0.247 for
the nearest rival and 0.082 for the y-flip control. The prediction stated before
this file existed was ~0.50 on both reference maps with the controls near 0.08.
**Pre-Searing came in at 0.734 and Kamadan at 0.304**, i.e. one reference map is
well above the corpus median and the other well below it, and Kamadan is
reported at its real value rather than being dropped for disagreeing -- it is a
dense city whose props sit on buildings and roofs, which is exactly where a
single-valued heightmap has nothing to say (FINDINGS 2: "what height a bridge or
a second storey sits at" is a standing negative). Its controls collapse just as
hard, which is the claim under test.

THE OTHER CROSS-CHUNK CHECK, cheaper and independent: the exported grid's extent
must equal the Map Parameters rect exactly, and `(x1-x0)/dimX` must be 96.0.
Section 6 runs it over a sample of maps and section 4 ships the `(dim-1)` divisor
and a perturbed dimension as controls that must NOT pass.

SECTIONS 0-4 NEED NO VAULT and build everything they check out of nothing. A run
with no archive still executes them, declares the two vault sections as skips
naming the path, and then FAILS on the floor -- because a run that measured
nothing about ArenaNet's bytes has not verified this module, whatever it printed.

MEASURED VALUES ARE THIS ARCHIVE'S, `vault/dat_study/Gw.dat`. File ids travel
between installs; MFT rows do not, so the row-indexed constants are used only
after the entry count matches.

    python toolkit/mapdata/test_mapexport.py
    python toolkit/mapdata/test_mapexport.py --sample 40
    python toolkit/mapdata/test_mapexport.py --all        # every map, slow
"""

import argparse
import hashlib
import json
import os
import struct
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, file_id_table  # noqa: E402
from terrain import Terrain, CELL_PITCH, CHUNK_SIZE, TERRAIN_CHUNK  # noqa: E402
import mapexport  # noqa: E402
from mapexport import (MAP_PARAMS_CHUNK, build_manifest, detile,  # noqa: E402
                       export_row, load_export, map_rect, resolve_outdir,
                       retile, verify_manifest, write_export, FORMAT,
                       FORMAT_VERSION, _check_rect)
import checks  # noqa: E402
import vaultpath  # noqa: E402

MAP_FLAGS = 259
MEASURED_ENTRY_COUNT = 177342

PROPS_CHUNK = 0x20000004
PROPS_SIG = 0x39583392
PROPS_VERSION = 17

# The two reference maps. Rows are pinned separately from file ids because only
# the file id is portable; every row-indexed claim is gated on the entry count.
KAMADAN_FILE_ID = 0x345CC
KAMADAN_ROW = 22371
KAMADAN_DIMS = (416, 448)
KAMADAN_RECT = (-18432.0, -21504.0, 21504.0, 21504.0)
KAMADAN_PROPS = 516

PRESEARING_FILE_ID = 0x1B97D
PRESEARING_ROW = 7982
PRESEARING_DIMS = (416, 512)
PRESEARING_RECT = (-18432.0, -24576.0, 21504.0, 24576.0)
PRESEARING_PROPS = 864

# MEASURED 2026-08-11 on this archive by this file's section 5. `frac` is the
# fraction of props whose |dz| is under 100 world units; `med` is the median
# |dz|. The four layouts are scored on identical prop sets -- every prop of both
# maps lands inside the grid under all four, so no variant is helped or hurt by
# a different sample. See the module docstring for why Kamadan sits low.
#          layout        Kamadan frac   med     Pre-Searing frac   med
ORACLE = {
    "baseline":     {KAMADAN_ROW: (0.3043, 306.88),
                     PRESEARING_ROW: (0.7338, 29.97)},
    "y-flip":       {KAMADAN_ROW: (0.0698, 892.71),
                     PRESEARING_ROW: (0.0775, 668.48)},
    "x-flip":       {KAMADAN_ROW: (0.0330, 4799.79),
                     PRESEARING_ROW: (0.1389, 573.51)},
    "not-detiled":  {KAMADAN_ROW: (0.0853, 1107.91),
                     PRESEARING_ROW: (0.1366, 507.76)},
}
CONTROLS = ("y-flip", "x-flip", "not-detiled")
FRAC_TOL = 0.005          # the measurement is deterministic; this is slack, not noise
# The claim the controls have to carry. Weaker than what was measured (3.6x on
# Kamadan, 5.3x on Pre-Searing) so a future archive with slightly different
# content cannot turn a real result red, but far above 1.0, which is where a
# layout that did not matter would sit.
MIN_RATIO = 2.0

# FINDINGS 4's corpus figure, for the pooled number to be reported against.
FINDINGS_CORPUS_FRAC = 0.504

# Synthetic grid for the bare-machine sections. Both dims are multiples of 32
# and DIFFER, so a transposed index cannot pass; neither is 32, so the tiling is
# genuinely exercised (on a 32x32 grid de-tiling is the identity).
SYN_X, SYN_Y = 64, 96

CORPUS_MAPS = 349
DEFAULT_SAMPLE = 12

# FLOOR: 108, from a real green run on `vault/dat_study/Gw.dat` 2026-08-11
# (31 s). The count does not move with `--sample` or `--all` -- every archive
# section reports an aggregate, so the floor is a constant rather than a
# function of the fixture.
#
# Sections 0-4 alone score 65, so a run with no archive lands 43 short and goes
# RED. That is deliberate and it is the whole reason the floor exists: 65 checks
# about a synthetic grid this file built itself have verified the plumbing and
# NOTHING about ArenaNet's layout, and a green exit code there would be the
# `test_codec.py` failure all over again. The placeholder value this constant
# carried while the file was being written was 46, and a vault-less run duly
# printed ALL CHECKS PASSED -- which is how the number below came to be measured
# rather than guessed.
FLOOR = 108


# ------------------------------------------------------------------ helpers

def raises(fn, *a, **kw):
    """True if `fn` raises ValueError or KeyError. Deliberately NOT bare except.

    A helper that swallows every exception scores a TypeError in the code under
    test as a pass; `terrain.py`'s tag-7 refusal shipped broken behind exactly
    that. Where the exception TYPE is the claim, the checks below assert it
    directly instead of coming here.
    """
    try:
        fn(*a, **kw)
    except (ValueError, KeyError):
        return True
    return False


def read_chunks(archive, row):
    """`{chunk_id: payload}` for one MFT row, walked here and not by mapexport.

    Straight through `ffna_chunks` on the decompressed row: the oracle chunk must
    not arrive through the same path the exporter used.
    """
    entry = next(e for e in archive.entries if e.index == row)
    data = archive.read(entry)
    return {cid: bytes(data[off:off + size])
            for cid, off, size in ffna_chunks(data)}


def read_props(payload):
    """Every prop's world `(x, y, z)`, and the walk's own consistency numbers.

    FINDINGS 5: `u32 signature, u16 version, u32 arraySize, u16 count`, then
    `count` records of `48 + 8*ringCount` bytes -- the array size is measured
    from offset 10 and INCLUDES the count word, so the walk closes when
    `p - 10 == arraySize`. That closure is the check that the record stride is
    right; a wrong stride desyncs and misses it by thousands of bytes.

    Position is three f32 at +2. Nothing else is read here -- the rotation basis,
    scale and radius are not this oracle's business.
    """
    signature, version, array_size, count = struct.unpack_from("<IHIH", payload, 0)
    if signature != PROPS_SIG:
        raise ValueError(f"props signature 0x{signature:08X} != 0x{PROPS_SIG:08X}")
    out = []
    p = 12
    for i in range(count):
        if p + 48 > len(payload):
            raise ValueError(f"prop {i} of {count} runs past the chunk")
        out.append(struct.unpack_from("<3f", payload, p + 2))
        p += 48 + 8 * payload[p + 47]
    return out, version, array_size, p - 10


def stored_order(world, dim_x, dim_y):
    """World row-major back to tag 1's storage order, via `Terrain.index`.

    Deliberately NOT `mapexport.retile`: this builds the "not de-tiled" control
    and checks `detile` itself, so it must not come from the module under test.
    `Terrain.index` is a different implementation in a file this rung does not
    own, and it is the one FINDINGS 4's corpus measurement is written against.
    """
    out = [0.0] * (dim_x * dim_y)
    for gy in range(dim_y):
        row = gy * dim_x
        for gx in range(dim_x):
            out[Terrain.index(gx, gy, dim_x)] = world[row + gx]
    return out


def score_layout(field, dim_x, dim_y, rect, props, layout):
    """Score one layout against the props. Returns (frac<100, median, n, outside).

    `field` is world row-major for every layout but "not-detiled", which is
    handed the storage-order array instead -- that IS the defect being modelled.
    """
    x0, y0, _x1, y1 = rect
    dz, outside = [], 0
    for wx, wy, wz in props:
        gx = int((wx - x0) / CELL_PITCH)
        gy = int((y1 - wy) / CELL_PITCH)
        if layout == "y-flip":
            gy = int((wy - y0) / CELL_PITCH)
        elif layout == "x-flip":
            gx = dim_x - 1 - gx
        if not (0 <= gx < dim_x and 0 <= gy < dim_y):
            outside += 1
            continue
        dz.append(abs(field[gy * dim_x + gx] - wz))
    if not dz:
        return 0.0, float("inf"), 0, outside
    dz.sort()
    return (sum(1 for d in dz if d < 100.0) / len(dz),
            dz[len(dz) // 2], len(dz), outside)


def synthetic_terrain(dim_x=SYN_X, dim_y=SYN_Y):
    """A `Terrain` built from nothing, whose every cell is distinguishable.

    Heights, tiles and shade all carry a value that is a function of `(gx, gy)`
    and are laid into STORAGE order through `Terrain.index`, so a de-tiling that
    is off by one tile, transposed, or absent puts a value where the test can
    name it. A uniform grid -- which is what `Terrain.blank()` gives -- would
    pass every layout in this file.
    """
    trn = Terrain.blank(dim_x, dim_y, tiles=3)
    cells = dim_x * dim_y
    heights = [0.0] * cells
    tiles = bytearray(cells)
    shade = bytearray(cells)
    for gy in range(dim_y):
        for gx in range(dim_x):
            i = Terrain.index(gx, gy, dim_x)
            heights[i] = float(gy * dim_x + gx)
            tiles[i] = (gx + gy) % 3
            shade[i] = (gx * 7 + gy * 13) & 0xFF
    trn.heights = heights
    trn.tiles = bytes(tiles)
    trn.shade = bytes(shade)
    return trn


def sample_rows(archive, sample, want_all):
    rows = [e.index for e in archive.entries
            if (e.flags & 0xFFFF) == MAP_FLAGS]
    if want_all or sample >= len(rows):
        return rows, rows
    step = max(1, len(rows) // sample)
    return rows[::step][:sample], rows


# --------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=None)
    ap.add_argument("--sample", type=int, default=DEFAULT_SAMPLE)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    led = checks.Ledger("map export", floor=FLOOR)
    check = checks.adopt(led)
    t0 = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="rurik_mapexport_") as tmp:
        _section0(check, tmp)
        _section1(check, tmp)
        _section2(check)
        _section3(check, tmp)
        _section4(check)
        _vault_sections(check, led, args, tmp)

    print(f"\n({time.perf_counter() - t0:.1f}s)")
    return led.verdict()


# --- 0. the provenance refusal --------------------------------------------

def _find_tree():
    """The working tree, found HERE and not taken from the module under test.

    Walk up until CLAUDE.md is beside a `toolkit/`. If the refusal's targets came
    from `mapexport.REPO_ROOT` they would move with the bug and every refusal
    would still pass while the guard protected the wrong directory -- which is
    not hypothetical: `REPO_ROOT` shipped one dirname short, named `toolkit/`,
    and wrote a 745 KB height field into the repo before anything caught it.
    """
    d = HERE
    while True:
        if os.path.isfile(os.path.join(d, "CLAUDE.md")) and \
                os.path.isdir(os.path.join(d, "toolkit")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise RuntimeError(f"no working tree above {HERE}")
        d = parent


def _section0(check, tmp):
    print("\n== 0. exports may not land in the working tree ==")

    tree = _find_tree()
    check(os.path.normcase(mapexport.REPO_ROOT) == os.path.normcase(tree),
          "REPO_ROOT is the working tree, not a directory inside it",
          f"{mapexport.REPO_ROOT}")

    # Targets built from the INDEPENDENTLY found tree, so a REPO_ROOT that has
    # drifted fails these too rather than only the pin above.
    for rel in ("", "toolkit", os.path.join("toolkit", "mapdata"), "content",
                "exports", os.path.join("studies", "customarea")):
        target = os.path.join(tree, rel) if rel else tree
        check(raises(resolve_outdir, target),
              f"refuses to export into the working tree ({rel or '.'})")

    # ...and the vault, which lives INSIDE the repo root in the main checkout,
    # must still be allowed. A plain prefix test would refuse the default.
    vault_out = vaultpath.vault_path("exports")
    check(resolve_outdir(vault_out) == os.path.abspath(vault_out),
          "the vault is allowed even though it sits inside the repo root")
    check(resolve_outdir(None) == os.path.abspath(vault_out),
          "the default destination is the vault, not the working directory")
    check(resolve_outdir(tmp) == os.path.abspath(tmp),
          "a scratch directory outside the tree is allowed")


# --- 1. a whole export built from nothing ---------------------------------

def _section1(check, tmp):
    print("\n== 1. synthetic export round-trips through load_export (no vault) ==")
    dx, dy = SYN_X, SYN_Y
    trn = synthetic_terrain(dx, dy)
    rect = (-1536.0, -3072.0, dx * CELL_PITCH - 1536.0, dy * CELL_PITCH - 3072.0)
    meta, payloads = build_manifest(trn, rect, "synthetic",
                                    {"archive": None, "row": None,
                                     "file_id": None})
    path = write_export(meta, payloads, os.path.join(tmp, "syn"))
    exp = load_export(path)

    check(exp.dim_x == dx and exp.dim_y == dy,
          f"dims survive the round-trip ({dx}x{dy})")
    check(exp.rect == rect, "the map rect survives the round-trip")
    check(exp.pitch == CELL_PITCH, f"the pitch is {CELL_PITCH}")
    check(exp.cells == dx * dy and len(exp.heights) == dx * dy,
          f"{dx * dy} height samples, one per cell")
    check(exp.vertex_dims == (dx + 1, dy + 1),
          f"the MESH is {dx + 1}x{dy + 1} vertices for {dx}x{dy} quads")

    # The whole point: every cell must come back where the world says it is.
    wrong = [(gx, gy) for gy in range(dy) for gx in range(dx)
             if exp.heights[gy * dx + gx] != float(gy * dx + gx)]
    check(not wrong, f"all {dx * dy} heights de-tile to world row-major",
          f"{len(wrong)} misplaced" if wrong else "0 misplaced")
    check(exp.tiles is not None and len(exp.tiles) == dx * dy,
          "the tiles sidecar is present and one byte per cell")
    bad_t = sum(1 for gy in range(dy) for gx in range(dx)
                if exp.tiles[gy * dx + gx] != (gx + gy) % 3)
    check(bad_t == 0, "the tile indices de-tile the same way", f"{bad_t} wrong")
    bad_s = sum(1 for gy in range(dy) for gx in range(dx)
                if exp.shade[gy * dx + gx] != ((gx * 7 + gy * 13) & 0xFF))
    check(bad_s == 0, "the shade bytes de-tile the same way", f"{bad_s} wrong")

    # Geometry the JSON promises.
    check(exp.extent == (dx * CELL_PITCH, dy * CELL_PITCH),
          f"extent is dims * {CELL_PITCH}", f"{exp.extent}")
    check(exp.extent == (rect[2] - rect[0], rect[3] - rect[1]),
          "extent equals the map rect span exactly")
    check(exp.world_at(0, 0) == (rect[0], rect[3]),
          "grid (0,0) is the rect's (x0, maxY) corner -- no half-cell offset")
    check(exp.world_at(dx, dy) == (rect[2], rect[1]),
          "grid (dimX, dimY) is the far corner, so the mesh spans the rect")
    check(exp.grid_at(*exp.world_at(5, 7)) == (5, 7),
          "world_at and grid_at are inverse on a cell corner")
    check(exp.sample(rect[0] - CELL_PITCH, rect[3]) is None,
          "sampling outside the grid returns None rather than wrapping")

    # The (dims+1) lattice the CLIENT manufactures, and the replication rule.
    corners = exp.corner_heights()
    check(len(corners) == (dx + 1) * (dy + 1),
          f"corner_heights is the {dx + 1}x{dy + 1} vertex lattice",
          f"{len(corners)}")
    dup_col = all(corners[gy * (dx + 1) + dx] == corners[gy * (dx + 1) + dx - 1]
                  for gy in range(dy + 1))
    check(dup_col, "the manufactured far column replicates its neighbour")
    dup_row = corners[dy * (dx + 1):] == corners[(dy - 1) * (dx + 1):dy * (dx + 1)]
    check(dup_row, "the manufactured far row replicates its neighbour")
    check(all(corners[gy * (dx + 1) + gx] == exp.heights[gy * dx + gx]
              for gy in range(dy) for gx in range(dx)),
          "every REAL sample is untouched by the replication")

    # The manifest states the conventions rather than leaving them to a docstring.
    check(meta["format"] == FORMAT and meta["format_version"] == FORMAT_VERSION,
          f"the manifest declares {FORMAT} v{FORMAT_VERSION}")
    conv = meta["conventions"]
    check("maxY" in conv["grid_row_0"] and "NOT negated" in conv["height_sign"]
          and conv["sample_position"] == "cell corners",
          "the manifest states row 0 = maxY, un-negated heights, corner samples")
    check(len(meta["sidecars"]) == 3
          and {s["kind"] for s in meta["sidecars"]} == {"heights", "tiles", "shade"},
          "three sidecars, each named by kind in the manifest")


# --- 2. the de-tiling, against a different implementation ------------------

def _section2(check):
    print("\n== 2. de-tiling agrees with terrain.Terrain.index, cell for cell ==")
    # `detile` moves whole 32-element slices for speed. `Terrain.index` computes
    # one cell at a time and lives in a module this rung does not own. They must
    # agree everywhere; that they are written differently is the point.
    for dx, dy in ((32, 32), (64, 96), (96, 64), (128, 32), (416, 448)):
        src = list(range(dx * dy))
        world = detile(src, dx, dy)
        wrong = sum(1 for gy in range(dy) for gx in range(dx)
                    if world[gy * dx + gx] != Terrain.index(gx, gy, dx))
        check(wrong == 0,
              f"detile == Terrain.index on a {dx}x{dy} grid ({dx * dy} cells)",
              f"{wrong} disagree")

    # A permutation, not a lossy shuffle -- and its inverse really inverts.
    dx, dy = SYN_X, SYN_Y
    src = list(range(dx * dy))
    check(sorted(detile(src, dx, dy)) == src,
          "de-tiling is a permutation: every stored sample appears once")
    check(retile(detile(src, dx, dy), dx, dy) == src,
          "retile inverts detile")
    check(detile(retile(src, dx, dy), dx, dy) == src,
          "detile inverts retile")
    check(isinstance(detile(bytes(dx * dy), dx, dy), bytes),
          "bytes in, bytes out -- the u8 sidecars keep their type")

    # On a single tile it is the identity, which is why the synthetic grid is
    # not 32x32: a test built there would pass with no de-tiling at all.
    check(detile(list(range(1024)), 32, 32) == list(range(1024)),
          "de-tiling a 32x32 grid is the identity (so 32x32 cannot test it)")
    check(detile(list(range(64 * 32)), 64, 32) != list(range(64 * 32)),
          "de-tiling a 64x32 grid is NOT the identity")

    check(raises(detile, list(range(100)), 10, 10),
          "refuses dims that are not multiples of 32")
    check(raises(detile, list(range(10)), 64, 96),
          "refuses a value count that does not match the dims")


# --- 3. the manifest, and one corrupted byte -------------------------------

def _section3(check, tmp):
    print("\n== 3. the sha256 manifest, and a corrupted height it must catch ==")
    trn = synthetic_terrain()
    rect = (0.0, 0.0, SYN_X * CELL_PITCH, SYN_Y * CELL_PITCH)
    meta, payloads = build_manifest(trn, rect, "digest",
                                    {"archive": None, "row": None,
                                     "file_id": None})
    out = os.path.join(tmp, "digest")
    path = write_export(meta, payloads, out)

    check(verify_manifest(path) == [], "a freshly written export verifies clean")
    for side in meta["sidecars"]:
        blob = open(os.path.join(out, side["name"]), "rb").read()
        check(hashlib.sha256(blob).hexdigest() == side["sha256"]
              and len(blob) == side["bytes"],
              f"{side['kind']}: the manifest's sha256 and size are the file's")

    heights = os.path.join(out, "digest.heights.f32")
    original = open(heights, "rb").read()

    # THE NEGATIVE CONTROL. One height changed, the file the same length, so
    # nothing but the digest can catch it. Flip the low mantissa bit of one
    # sample -- a change no eye and no size check would see.
    sample = 1234
    i = sample * 4
    corrupt = bytearray(original)
    corrupt[i] ^= 0x01
    before, = struct.unpack_from("<f", original, i)
    after, = struct.unpack_from("<f", bytes(corrupt), i)
    check(bytes(corrupt) != original and len(corrupt) == len(original)
          and before != after,
          "the control really changed one height and nothing else",
          f"sample {sample}: {before!r} -> {after!r}, still "
          f"{len(corrupt)} bytes")
    open(heights, "wb").write(bytes(corrupt))

    bad = verify_manifest(path)
    check(len(bad) == 1 and "digest.heights.f32" in bad[0],
          "verify_manifest catches the corrupted height and names the file",
          bad[0][:70] if bad else "NOTHING REPORTED")
    raised = None
    try:
        load_export(path)
    except ValueError as exc:
        raised = exc
    check(isinstance(raised, ValueError),
          "load_export RAISES rather than handing back corrupted data",
          type(raised).__name__ if raised else "returned normally")

    # A truncation, which the size check catches before the digest does.
    open(heights, "wb").write(original[:-4])
    bad = verify_manifest(path)
    check(len(bad) == 1 and "bytes on disk" in bad[0],
          "a truncated sidecar is reported as a size mismatch")
    os.remove(heights)
    check(any("missing" in b for b in verify_manifest(path)),
          "a deleted sidecar is reported as missing, not silently skipped")

    open(heights, "wb").write(original)
    check(verify_manifest(path) == [],
          "restoring the original bytes makes it verify again")

    # A manifest whose own format is wrong is refused before any file is read.
    other = os.path.join(tmp, "wrongver.gwmap.json")
    obj = json.loads(open(path, encoding="utf-8").read())
    obj["format_version"] = FORMAT_VERSION + 1
    open(other, "w", encoding="utf-8").write(json.dumps(obj))
    check(any("format_version" in b for b in verify_manifest(other)),
          "a manifest from a different format version is refused")


# --- 4. the chunk gates and the extent controls ----------------------------

def _section4(check):
    print("\n== 4. Map Parameters gates, and the extent controls that must fail ==")
    good = struct.pack("<IB4f5I", mapexport.MAP_PARAMS_SIG, 2,
                       -18432.0, -21504.0, 21504.0, 21504.0, 0, 0, 0, 0, 0)
    check(map_rect(good) == (-18432.0, -21504.0, 21504.0, 21504.0),
          "map_rect reads the four floats from the UNALIGNED offset 5")
    check(len(good) == 41, "the Map Parameters chunk is 41 bytes", f"{len(good)}")
    check(raises(map_rect, b"\x00" * 41), "refuses a wrong signature")
    check(raises(map_rect, struct.pack("<IB4f5I", mapexport.MAP_PARAMS_SIG, 3,
                                       0.0, 0.0, 1.0, 1.0, 0, 0, 0, 0, 0)),
          "refuses a wrong version")
    check(raises(map_rect, good[:40]), "refuses a chunk under the 41-byte gate")

    # The cross-chunk agreement, and the two controls FINDINGS 4 names.
    rect = (-18432.0, -21504.0, 21504.0, 21504.0)
    dx, dy = KAMADAN_DIMS
    _check_rect(rect, dx, dy)          # must not raise
    check(True, "the rect and dims agree at exactly 96.0 on both axes",
          f"{(rect[2] - rect[0]) / dx} x {(rect[3] - rect[1]) / dy}")
    check((rect[2] - rect[0]) / (dx - 1) != CELL_PITCH,
          "the (dim-1) divisor does NOT give 96.0 -- the control has power",
          f"{(rect[2] - rect[0]) / (dx - 1):.4f}")
    check(raises(_check_rect, rect, dx + CHUNK_SIZE, dy),
          "one tile of dimX error is refused")
    check(raises(_check_rect, rect, dx, dy - CHUNK_SIZE),
          "one tile of dimY error is refused")


# --- 5 and 6. the archive ---------------------------------------------------

def _vault_sections(check, led, args, tmp):
    dat = args.dat
    if dat is None:
        study = os.path.join(vaultpath.vault_root(), "dat_study")
        dat = os.path.join(study, "Gw.dat")
    if not os.path.isfile(dat):
        why = (f"no archive at {dat} (vault resolved to "
               f"{vaultpath.vault_root()}, {vaultpath.vault_why()})")
        led.skip("5. the prop-z oracle and its three controls", why)
        led.skip("6. extent agreement across the corpus", why)
        return

    with Archive(dat) as ar:
        _section5(check, led, ar, tmp)
        _section6(check, led, ar, args)


def _section5(check, led, ar, tmp):
    print("\n== 5. THE ORACLE: prop z against the exported height field ==")
    print("   props chunk 0x20000004 -- a chunk mapexport.py never reads\n")

    table = file_id_table(ar)
    pooled = {k: [0, 0] for k in ("baseline",) + CONTROLS}   # [within100, n]
    for fid, row, dims, rect, nprops in (
            (KAMADAN_FILE_ID, KAMADAN_ROW, KAMADAN_DIMS, KAMADAN_RECT,
             KAMADAN_PROPS),
            (PRESEARING_FILE_ID, PRESEARING_ROW, PRESEARING_DIMS,
             PRESEARING_RECT, PRESEARING_PROPS)):
        resolved = table.get(fid)
        check(resolved == row,
              f"file id 0x{fid:X} resolves to row {row}", f"got {resolved}")
        if resolved is None:
            continue
        row = resolved

        path = export_row(row, ar, outdir=os.path.join(tmp, f"m{row}"),
                          file_id=fid)
        exp = load_export(path)
        dx, dy = exp.dim_x, exp.dim_y
        check((dx, dy) == dims, f"row {row}: exported grid is {dims[0]}x{dims[1]}",
              f"{dx}x{dy}")
        check(exp.rect == rect, f"row {row}: the exported rect is the pinned one",
              f"{exp.rect}")

        chunks = read_chunks(ar, row)
        check(PROPS_CHUNK in chunks,
              f"row {row}: the props chunk 0x{PROPS_CHUNK:08X} is present")
        props, version, array_size, consumed = read_props(chunks[PROPS_CHUNK])
        check(version == PROPS_VERSION and consumed == array_size,
              f"row {row}: the prop walk closes on its own declared array size",
              f"v{version}, {consumed} of {array_size} bytes")
        # POPULATION. A silently empty prop list would make every layout score
        # 0.0 and the ratio test would divide zero by zero into a pass.
        check(len(props) == nprops,
              f"row {row}: {nprops} props, the pinned population",
              f"got {len(props)}")
        if len(props) != nprops:
            continue

        stored = stored_order(exp.heights, dx, dy)
        results = {}
        for layout in ("baseline",) + CONTROLS:
            field = stored if layout == "not-detiled" else exp.heights
            frac, med, n, outside = score_layout(field, dx, dy, rect, props,
                                                 layout)
            results[layout] = (frac, med, n, outside)
            print(f"    {layout:12s} frac<100 {frac:.4f}  median |dz| "
                  f"{med:9.2f}  n={n}  outside={outside}")

        # Every layout scored the SAME props. Without this the controls could be
        # losing on sample size rather than on placement.
        check(all(r[3] == 0 and r[2] == len(props) for r in results.values()),
              f"row {row}: all {len(props)} props land inside the grid under "
              f"all four layouts")

        base_frac, base_med = results["baseline"][0], results["baseline"][1]
        want_f, want_m = ORACLE["baseline"][row]
        check(abs(base_frac - want_f) < FRAC_TOL,
              f"row {row}: baseline fraction within 100 units is {want_f}",
              f"{base_frac:.4f}")
        check(abs(base_med - want_m) < 1.0,
              f"row {row}: baseline median |dz| is {want_m}", f"{base_med:.2f}")
        pooled["baseline"][0] += round(base_frac * len(props))
        pooled["baseline"][1] += len(props)

        for layout in CONTROLS:
            frac, med = results[layout][0], results[layout][1]
            want_f, want_m = ORACLE[layout][row]
            check(abs(frac - want_f) < FRAC_TOL,
                  f"row {row}: the {layout} control scores {want_f}",
                  f"{frac:.4f}")
            # THE CLAIM. A control that did not collapse would mean the
            # orientation is not established, and this must go red rather than
            # the number being shipped anyway.
            check(frac * MIN_RATIO <= base_frac,
                  f"row {row}: the {layout} control collapses to under "
                  f"1/{MIN_RATIO:g} of the baseline",
                  f"{frac:.4f} vs {base_frac:.4f} "
                  f"({base_frac / frac:.1f}x)" if frac else f"0 vs {base_frac:.4f}")
            check(base_med * 2.0 <= med,
                  f"row {row}: the {layout} control's median |dz| is at least "
                  f"2x the baseline's", f"{med:.1f} vs {base_med:.1f}")
            pooled[layout][0] += round(frac * len(props))
            pooled[layout][1] += len(props)

    n = pooled["baseline"][1]
    if n:
        base = pooled["baseline"][0] / n
        print(f"\n    pooled over {n} props: baseline {base:.4f}, controls "
              + ", ".join(f"{k} {pooled[k][0] / pooled[k][1]:.4f}"
                          for k in CONTROLS))
        check(n == KAMADAN_PROPS + PRESEARING_PROPS,
              f"the pooled population is all {KAMADAN_PROPS + PRESEARING_PROPS} "
              f"props of both reference maps", f"{n}")
        check(base >= FINDINGS_CORPUS_FRAC,
              f"pooled, the baseline is at least FINDINGS 4's corpus figure "
              f"of {FINDINGS_CORPUS_FRAC}", f"{base:.4f}")
        check(all(pooled[k][0] / pooled[k][1] * MIN_RATIO <= base
                  for k in CONTROLS),
              f"pooled, every control collapses to under 1/{MIN_RATIO:g} of the "
              f"baseline")
    else:
        led.skip("5. pooled oracle", "no reference map resolved")


def _section6(check, led, ar, args):
    print("\n== 6. the exported extent equals the Map Parameters rect ==")
    if ar.entry_count != MEASURED_ENTRY_COUNT:
        led.skip("6. extent agreement across the corpus",
                 f"this archive has {ar.entry_count} MFT rows, not the "
                 f"{MEASURED_ENTRY_COUNT} these row constants were measured on")
        return

    picks, all_rows = sample_rows(ar, args.sample, args.all)
    check(len(all_rows) == CORPUS_MAPS,
          f"the archive holds {CORPUS_MAPS} map rows (flags {MAP_FLAGS})",
          f"{len(all_rows)}")
    check(len(picks) >= min(args.sample, CORPUS_MAPS) and len(picks) > 0,
          f"the sample is the {len(picks)} rows it claims to be")

    ok = 0
    fails = []
    for row in picks:
        chunks = read_chunks(ar, row)
        rect = map_rect(chunks[MAP_PARAMS_CHUNK])
        # dims straight out of tag 0, by a walker that is four lines long and
        # imports nothing from mapexport: header(8) + record header(5), then two
        # u32. Reading them here rather than through the decoder keeps the
        # agreement below a comparison between two CHUNKS.
        trn_blob = chunks[TERRAIN_CHUNK]
        dim_x, dim_y = struct.unpack_from("<II", trn_blob, 13)
        px = (rect[2] - rect[0]) / dim_x
        py = (rect[3] - rect[1]) / dim_y
        if (px, py) == (CELL_PITCH, CELL_PITCH) and \
                (dim_x * CELL_PITCH, dim_y * CELL_PITCH) == \
                (rect[2] - rect[0], rect[3] - rect[1]):
            ok += 1
        else:
            fails.append((row, dim_x, dim_y, px, py))
    check(ok == len(picks),
          f"extent == dims * {CELL_PITCH} == the rect span on {len(picks)} of "
          f"{len(picks)} maps",
          f"{ok}/{len(picks)}" + (f"; first miss {fails[0]}" if fails else ""))

    # The control, on the same rows: the (dim-1) divisor must never give 96.0.
    bad_control = 0
    for row in picks:
        chunks = read_chunks(ar, row)
        rect = map_rect(chunks[MAP_PARAMS_CHUNK])
        dim_x, dim_y = struct.unpack_from("<II", chunks[TERRAIN_CHUNK], 13)
        if (rect[2] - rect[0]) / (dim_x - 1) == CELL_PITCH:
            bad_control += 1
    check(bad_control == 0,
          f"the (dim-1) divisor gives 96.0 on 0 of {len(picks)} maps -- the "
          f"control still has power", f"{bad_control} would have passed")


if __name__ == "__main__":
    sys.exit(main())
