"""Check the terrain interchange, and check the ORIENTATION against a different chunk.

THE HEADLINE IS SECTION 5 AND IT IS NOT OUR CODE AGREEING WITH OUR CODE. An
exporter verified by our own importer proves nothing -- `CLAUDE.md` says so in
those words -- so the layout is scored against the props chunk `0x20000004`,
which no part of the TERRAIN pipeline reads or produced. (Since 2026-08-13
`mapexport.py` also exports props, so the old framing "a chunk the exporter
never reads" is dead; the independence that carries the oracle is narrower and
still real -- the height arrays' path never reads props, the props path never
touches the height arrays, and this section reads the chunk through its OWN
48-byte walker rather than through either.) Every prop carries a world
`(x, y, z)`; sample the exported height field at `(x, y)` and compare with
`z`. A wrong de-tiling, a flipped row order or a wrong pitch all move the
sampled height away from the prop that is standing on it.

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

SECTIONS 0-4c NEED NO VAULT and build everything they check out of nothing --
including a matched props pair whose Bloated half is assembled here from
`struct.pack`, and synthetic ATEX/DDS texture rows behind a fake two-method
archive, which is what lets `build_props`'s and `build_terrain_textures`'s
refusals each sit beside a live baseline. A run with no archive still executes
them, declares the four vault sections as skips naming the path, and then
FAILS on the floor -- because a run that measured nothing about ArenaNet's
bytes has not verified this module, whatever it printed.

SECTION 8 IS RUNG T4: Kamadan's 51-entry texture table exported whole -- every
distinct tile byte in use resolving to a decoded image, the MFT identity on
every entry re-read here, a flipped byte in one PNG refusing the whole export
-- plus the tag3b reference map (row 56835), whose extra LEADING dependency is
one of the corpus's four DDS rows and must reach no tile, and the resolution
law over the sampled maps (`--all` for the corpus).

SECTION 7 IS THE PROPS SIDECAR against the archive: every position equal to
this file's own independent walk of the Bloated chunk, every placement inside
the rect, the props-vs-heights fraction reproducing section 5's pinned number
from the sidecar's own two files, every model file resolving with the MFT's
(size, crc), and THE ROTATION COMPOSITION -- z first, then x, then y, per-axis
signs (-, +, -) -- reproducing the compiled basis on every record, with the
nearest rival order (zyx) required to keep failing on the pinned multi-axis
populations so the pin cannot go vacuous.

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
from mapexport import (MAP_PARAMS_CHUNK, build_manifest, build_props,  # noqa: E402
                       build_terrain_textures, detile, export_row, load_export,
                       map_rect, resolve_outdir, retile, verify_manifest,
                       write_export, FORMAT, FORMAT_VERSION, TEX_SUBDIR,
                       TERRAIN_DEPS_CHUNK, _check_rect)
import atex  # noqa: E402
from mapfile import MapFile, Chunk, FORM_OPAQUE, FORM_DEPENDENCIES  # noqa: E402
from mapchunks import (Dependencies, dependency_pair,  # noqa: E402
                       DEPENDENCY_SIGNATURE, DEPENDENCY_VERSION)
from props import Prop, PropRef, StrippedProps  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402
import math  # noqa: E402

MAP_FLAGS = 259

PROPS_CHUNK = 0x20000004
PROPS_SIG = 0x39583392
PROPS_VERSION = 17

# The two reference maps. Each is REACHED through its file id -- the portable
# key -- and section 5 then asserts the row it landed on, so a copy where the
# rows moved goes red and names both numbers instead of skipping. (It has not:
# both ids resolve to these rows in `vault/dat_study` and in
# `vault/client/2026-04-30_b174de1f2d8d`, MEASURED 2026-08-13.) Nothing in this
# file is gated on the archive's MFT row count any more -- see `_section6`.
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

# FLOOR: 185, from a real green run on `vault/dat_study/Gw.dat` 2026-08-14
# (74 s; was 145 before the terrain-texture sections landed, 108 before the
# props sections). The count does not move with `--sample` or `--all` -- every
# archive section reports an aggregate, so the floor is a constant rather than
# a function of the fixture.
#
# Sections 0-4c alone score 114 (MEASURED by pointing --dat at a missing
# file), so a run with no archive lands short and goes RED. That is
# deliberate and it is the whole reason the floor exists: those checks about a
# synthetic grid, synthetic props and synthetic textures this file built
# itself have verified the plumbing and NOTHING about ArenaNet's layout, and a
# green exit code there would be the `test_codec.py` failure all over again.
# The placeholder value this constant carried while the file was being
# written was 46, and a vault-less run duly printed ALL CHECKS PASSED --
# which is how the number came to be measured rather than guessed.
#
# 188 -> 189 the same day, when T6's RESOLVED blend layers joined it as a
# fifth sidecar (.layers.u16, three u16 slots per cell).
#
# 185 -> 188 on 2026-08-14, when T6's variation sidecar joined the tiles
# export: the synthetic fixture now packs a per-cell variation 0..3 and
# section 1 asserts it de-tiles with the measured (i&3)*2 bit order.
FLOOR = 191


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
    bits = bytearray(cells // 4)
    for gy in range(dim_y):
        for gx in range(dim_x):
            i = Terrain.index(gx, gy, dim_x)
            heights[i] = float(gy * dim_x + gx)
            tiles[i] = (gx + gy) % 3
            shade[i] = (gx * 7 + gy * 13) & 0xFF
            # A per-cell variation 0..3, packed the way bits_at reads it, so
            # a wrong bit-pair position or a wrong de-tile is visible.
            bits[i >> 2] |= ((gx * 3 + gy) & 3) << ((i & 3) * 2)
    trn.heights = heights
    trn.tiles = bytes(tiles)
    trn.shade = bytes(shade)
    trn.bits = bytes(bits)
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
        _section1b(check, tmp)
        _section2(check)
        _section3(check, tmp)
        _section4(check)
        _section4b(check)
        _section4c(check, tmp)
        _section_selector_parity(check)
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
    check(exp.variation is not None and len(exp.variation) == dx * dy,
          "the variation sidecar is present, one byte per cell (T6)")
    bad_v = sum(1 for gy in range(dy) for gx in range(dx)
                if exp.variation[gy * dx + gx] != ((gx * 3 + gy) & 3))
    check(bad_v == 0, "tag 3's variation de-tiles with the measured (i&3)*2 "
          "bit order (FINDINGS §3.3)", f"{bad_v} wrong")

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
    # CORRECTED 2026-08-12. This asserted `"NOT negated" in height_sign`, which
    # pinned the claim FINDINGS 25 RETIRED -- so the machine-readable half of
    # the interchange went on telling consumers the wrong thing for a day after
    # the docstring beside it was fixed, held in place by this check. The rule
    # is now stated as its SUBSTANCE, and the retired phrase is asserted ABSENT
    # rather than merely not required, so a revert to the old wording reddens
    # here instead of passing quietly.
    sign = conv["height_sign"]
    check("maxY" in conv["grid_row_0"]
          and "LOWER in the world" in sign and "NOT negated" not in sign
          and conv["sample_position"] == "cell corners",
          "the manifest states row 0 = maxY, corner samples, and that a GREATER "
          "stored value is LOWER in the world (FINDINGS 25)", sign[:80])
    check(len(meta["sidecars"]) == 5
          and {s["kind"] for s in meta["sidecars"]}
          == {"heights", "tiles", "variation", "layers", "shade"},
          "five sidecars, each named by kind in the manifest "
          "(variation and the resolved blend layers joined tiles for T6)")


# --- 1b. the props sidecar, built from nothing -----------------------------

def _bloated_payload(sp, basis=(-0.0, -0.0, -1.0, 0.0, 1.0, -0.0)):
    """A Bloated `0x20000004` payload built HERE to match `sp` record for
    record, out of `struct.pack` and the documented layout -- so the no-vault
    sections can hand `build_props` a pair that satisfies `corresponds()`
    without an archive. `basis` is per-record constant; `corresponds` does not
    check it and the synthetic props carry rot (0, 0, 0), where it is what the
    compiler emits."""
    body = bytearray(struct.pack("<H", len(sp.props)))
    for p in sp.props:
        body += struct.pack("<H3f", p.model, p.x, p.y, p.z)
        body += struct.pack("<6f", *basis)
        body += struct.pack("<f", p.scale * (255 / 128) / 256 + 1 / 128)
        body += b"\x00\x00\x00\x00"                 # tail; corresponds ignores
        body += bytes((p.flags, p.points))
        for dx, dy in p.outline:
            body += struct.pack("<ff", p.x + dx, p.y + dy)
    out = bytearray(struct.pack("<IB", PROPS_SIG, PROPS_VERSION))
    for tag in (0, 1, 2, 3, 4):
        payload = bytes(body) if tag == 0 else b""
        out += struct.pack("<BI", tag, len(payload)) + payload
    if sp.refs6 is not None:
        out += struct.pack("<BI", 6, 0)
    out += struct.pack("<BI", 0xFF, 0)
    return bytes(out)


def _synth_pair(fids=(0x1111, 0x2222)):
    """A (head MapFile, partner MapFile, StrippedProps) trio from nothing."""
    sp = StrippedProps(props=[
        Prop(0, 100.0, 200.0, -50.0, rot=(0, 0, 0), scale=0x99),
        Prop(1, -300.0, 40.0, 12.5, rot=(0, 0, 0), scale=0x7F, flags=2,
             outline=((-5, -5), (5, -5), (5, 5), (-5, -5))),
        Prop(0, 0.0, -8.0, 3.0),
    ], refs4=[PropRef(7, 1)])
    dep = Dependencies(DEPENDENCY_SIGNATURE, DEPENDENCY_VERSION,
                       [(*dependency_pair(f), 0) for f in fids])
    head = MapFile(chunks=[
        Chunk(mapexport.PROPS_BLOATED_CHUNK, _bloated_payload(sp), FORM_OPAQUE),
        Chunk(mapexport.PROPS_DEPS_BLOATED, dep, FORM_DEPENDENCIES)])
    partner = MapFile(chunks=[
        Chunk(mapexport.PROPS_STRIPPED_CHUNK, sp.encode(), FORM_OPAQUE),
        Chunk(mapexport.PROPS_DEPS_STRIPPED, dep, FORM_DEPENDENCIES)])
    return head, partner, sp


def _section1b(check, tmp):
    print("\n== 1b. the props sidecar round-trips through load_export (no vault) ==")
    trn = synthetic_terrain()
    rect = (0.0, 0.0, SYN_X * CELL_PITCH, SYN_Y * CELL_PITCH)
    src = {"archive": None, "row": None, "file_id": None}
    head, partner, sp = _synth_pair()

    pd = build_props(head, partner)
    check(pd is not None and pd["count"] == len(sp.props),
          f"build_props reads the synthetic pair ({len(sp.props)} props)")
    check([m["file_id"] for m in pd["models"]] == [0x1111, 0x2222]
          and all(m["mft"] is None for m in pd["models"]),
          "the model list carries the file ids; mft is None without an archive")

    meta, payloads = build_manifest(trn, rect, "withprops", src,
                                    props=pd, props_state="exported")
    path = write_export(meta, payloads, os.path.join(tmp, "wp"))
    exp = load_export(path)
    check(exp.props == pd,
          "the props sidecar comes back DEEP-EQUAL through disk and json")
    check(meta.get("props_state") == "exported"
          and {s["kind"] for s in meta["sidecars"]}
          == {"heights", "tiles", "variation", "layers", "shade", "props"},
          "the manifest declares props_state and the props sidecar")
    side = next(s for s in meta["sidecars"] if s["kind"] == "props")
    check(side["dtype"] == mapexport.DTYPE_JSON
          and side["count"] == pd["count"] and side["count"] != exp.cells,
          "the props sidecar entry counts PROPS, not cells")
    check(exp.props["props"][1]["outline"] == [[-5, -5], [5, -5], [5, 5],
                                               [-5, -5]],
          "an outline survives as the prop-local pairs")

    # v2 is BACKWARD compatible: a version-1 manifest still loads. The other
    # direction -- version 3 refused -- is section 3's existing check.
    meta1, payloads1 = build_manifest(trn, rect, "v1", src)
    p1 = write_export(meta1, payloads1, os.path.join(tmp, "v1"))
    obj = json.load(open(p1, encoding="utf-8"))
    obj["format_version"] = 1
    open(p1, "w", encoding="utf-8").write(json.dumps(obj))
    exp1 = load_export(p1)
    check(exp1.props is None and exp1.dim_x == SYN_X,
          "a version-1 manifest (terrain only) still loads under the v2 reader")

    # Count coherence: a sidecar whose declared count disagrees with what it
    # holds is refused even though every digest is clean.
    bad = dict(pd, count=pd["count"] + 1)
    metab, payloadsb = build_manifest(trn, rect, "badcount", src,
                                      props=bad, props_state="exported")
    pb = write_export(metab, payloadsb, os.path.join(tmp, "bc"))
    check(raises(load_export, pb),
          "a props sidecar whose declared count disagrees with its records "
          "is refused")

    # THE NEGATIVE CONTROL, section 3's shape: one byte of the props sidecar
    # changed, same length, so nothing but the digest can catch it.
    pj = os.path.join(tmp, "wp", "withprops.props.json")
    original = open(pj, "rb").read()
    i = original.index(b"100.0")
    corrupt = bytearray(original)
    corrupt[i] = ord("9")
    check(len(corrupt) == len(original) and bytes(corrupt) != original,
          "the control really changed one byte and nothing else")
    open(pj, "wb").write(bytes(corrupt))
    bad_list = verify_manifest(path)
    check(len(bad_list) == 1 and "withprops.props.json" in bad_list[0],
          "verify_manifest catches the corrupted prop and names the file",
          bad_list[0][:70] if bad_list else "NOTHING REPORTED")
    check(raises(load_export, path),
          "load_export RAISES rather than handing back corrupted props")
    open(pj, "wb").write(original)
    check(load_export(path).props == pd,
          "restoring the original bytes makes it load again")


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


# --- 4b. build_props refuses, each refusal beside a live baseline -----------

def _section4b(check):
    print("\n== 4b. build_props refusals (no vault) ==")
    head, partner, sp = _synth_pair()
    ok = build_props(head, partner)
    check(ok is not None and ok["count"] == 3,
          "the matched pair is ACCEPTED -- the refusals below have a live "
          "baseline")

    check(build_props(MapFile(chunks=[]), MapFile(chunks=[])) is None,
          "no props chunk on either side is None, not an error "
          "(three retail maps have none)")
    check(raises(build_props, head, MapFile(chunks=[])),
          "a props chunk on ONE side only is refused")

    # A compiled record that disagrees: record 0's x is at header(5) +
    # section header(5) + count(2) + model(2) = offset 14.
    blob = bytearray(_bloated_payload(sp))
    struct.pack_into("<f", blob, 14, 999.0)
    bad_head = MapFile(chunks=[
        Chunk(mapexport.PROPS_BLOATED_CHUNK, bytes(blob), FORM_OPAQUE),
        head.find(mapexport.PROPS_DEPS_BLOATED)])
    check(raises(build_props, bad_head, partner),
          "a compiled record disagreeing with the Stripped one is refused "
          "(corresponds; retail agrees 349/349)")

    # Dependency lists that disagree are refused, not resolved.
    dep2 = Dependencies(DEPENDENCY_SIGNATURE, DEPENDENCY_VERSION,
                        [(*dependency_pair(0x3333), 0),
                         (*dependency_pair(0x2222), 0)])
    head2 = MapFile(chunks=[
        Chunk(mapexport.PROPS_BLOATED_CHUNK, _bloated_payload(sp), FORM_OPAQUE),
        Chunk(mapexport.PROPS_DEPS_BLOATED, dep2, FORM_DEPENDENCIES)])
    check(raises(build_props, head2, partner),
          "model dependency lists that disagree are refused")

    # A model index past the list; both streams consistent, so corresponds
    # passes and the range check is the one that must fire.
    sp2 = StrippedProps(props=[Prop(9, 1.0, 2.0, 3.0)])
    dep1 = Dependencies(DEPENDENCY_SIGNATURE, DEPENDENCY_VERSION,
                        [(*dependency_pair(0x1111), 0)])
    head3 = MapFile(chunks=[
        Chunk(mapexport.PROPS_BLOATED_CHUNK, _bloated_payload(sp2), FORM_OPAQUE),
        Chunk(mapexport.PROPS_DEPS_BLOATED, dep1, FORM_DEPENDENCIES)])
    partner3 = MapFile(chunks=[
        Chunk(mapexport.PROPS_STRIPPED_CHUNK, sp2.encode(), FORM_OPAQUE),
        Chunk(mapexport.PROPS_DEPS_STRIPPED, dep1, FORM_DEPENDENCIES)])
    check(raises(build_props, head3, partner3),
          "a model index past the dependency list is refused "
          "(stripbuild's rule, read direction)")

    # The POSITIVE control for the dep rules: a zero-prop chunk with no
    # dependency list is row 26209's real shape and must export empty.
    sp0 = StrippedProps()
    head0 = MapFile(chunks=[
        Chunk(mapexport.PROPS_BLOATED_CHUNK, _bloated_payload(sp0),
              FORM_OPAQUE)])
    partner0 = MapFile(chunks=[
        Chunk(mapexport.PROPS_STRIPPED_CHUNK, sp0.encode(), FORM_OPAQUE)])
    z = build_props(head0, partner0)
    check(z is not None and z["count"] == 0 and z["models"] == [],
          "a zero-prop chunk with no dependency list exports empty "
          "(row 26209's shape)")


# --- 4c. rung T4's tile->texture table, no vault -----------------------------

PNG_SIG = b"\x89PNG\r\n\x1a\n"


class _TexEntry:
    def __init__(self, index, size, crc):
        self.index, self.size, self.crc = index, size, crc


class _TexArchive:
    """The two methods `build_terrain_textures` needs, over in-memory rows.

    The crc is invented (recorded, never verified against bytes here) -- what
    the test checks is that the exporter CARRIES the archive identity, not
    what the identity is.
    """

    def __init__(self, blobs):                       # {row: bytes}
        self._blobs = blobs

    def row(self, n):
        return _TexEntry(n, len(self._blobs[n]), 0xC0FFEE00 + n)

    def read(self, entry):
        return self._blobs[entry.index]


def _tex_deps(*fids):
    return Chunk(TERRAIN_DEPS_CHUNK,
                 Dependencies(DEPENDENCY_SIGNATURE, DEPENDENCY_VERSION,
                              [(*dependency_pair(f), 0) for f in fids]),
                 FORM_DEPENDENCIES)


def _dds32(width, height, pixel):
    """A minimal uncompressed A8R8G8B8 DDS, one repeated pixel."""
    hdr = bytearray(128)
    hdr[0:4] = b"DDS "
    struct.pack_into("<I", hdr, 4, 124)
    struct.pack_into("<2I", hdr, 12, height, width)
    struct.pack_into("<I", hdr, 80, 0x41)            # RGB | ALPHAPIXELS
    struct.pack_into("<I", hdr, 88, 32)
    struct.pack_into("<4I", hdr, 92, 0x00FF0000, 0x0000FF00, 0x000000FF,
                     0xFF000000)
    return bytes(hdr) + struct.pack("<I", pixel) * (width * height)


def _dds_refused():
    """A compressed-flagged DDS, which `dds_rgba` answers None to."""
    hdr = bytearray(128)
    hdr[0:4] = b"DDS "
    struct.pack_into("<I", hdr, 4, 124)
    struct.pack_into("<2I", hdr, 12, 8, 8)
    struct.pack_into("<I", hdr, 80, 0x4)             # FOURCC
    hdr[84:88] = b"DXT1"
    return bytes(hdr) + b"\0" * 32


def _section4c(check, tmp):
    print("\n== 4c. rung T4: the tile->texture table (no vault) ==")
    # Three synthetic ATEX rows, one per tile of `synthetic_terrain`'s 3-entry
    # table. Distinct fills so no two images can share a digest.
    fids = (0x1111, 0x2222, 0x3333)
    blobs = {10 + i: atex.build(b"DXT1", 8, 8, fill=0x01010101 * (i + 1))
             for i in range(3)}
    table = {fid: 10 + i for i, fid in enumerate(fids)}
    ar = _TexArchive(blobs)
    trn = synthetic_terrain()

    # -- the happy path, and what the block promises
    block, payloads = build_terrain_textures(
        MapFile(chunks=[_tex_deps(*fids)]), trn, ar, table=table)
    check(block["dep_offset"] == 0 and block["tile_count"] == 3
          and block["dep_count"] == 3,
          "an identity map binds with dep_offset 0", f"{block['dep_offset']}")
    check(block["used_tiles"] == [0, 1, 2],
          "used_tiles is the distinct tile bytes of tag 2")
    check([e["file_id"] for e in block["tiles"]] == list(fids),
          "tile t names dep[t], in order")
    check(all(e.get("image") == f"{TEX_SUBDIR}/tex_{e['file_id']:X}.png"
              for e in block["tiles"]),
          "every tile decoded to a PNG named by its FILE ID under "
          f"{TEX_SUBDIR}/")
    check(all(e["size"] == len(blobs[e["row"]])
              and e["crc"] == 0xC0FFEE00 + e["row"]
              for e in block["tiles"]),
          "every tile carries the MFT's (row, size, crc) -- a file id is "
          "archive STATE")
    by_name = dict(payloads)
    check(len(payloads) == 3
          and all(img["sha256"] == hashlib.sha256(by_name[img["name"]])
                  .hexdigest() and img["bytes"] == len(by_name[img["name"]])
                  for img in block["images"]),
          "each image's manifest digest is the sha256 of its payload")
    check(all(blob[:8] == PNG_SIG for blob in by_name.values()),
          "every payload is a PNG")
    check(block["census"] == {"ATEX": 3}, "the census names the container "
          "magics", f"{block['census']}")

    # -- two tiles sharing one texture share one image
    block2, payloads2 = build_terrain_textures(
        MapFile(chunks=[_tex_deps(0x1111, 0x2222, 0x1111)]), trn, ar,
        table=table)
    check(len(block2["images"]) == 2 and len(payloads2) == 2
          and block2["tiles"][0]["image"] == block2["tiles"][2]["image"]
          and block2["census"].get("shared") == 1,
          "a repeated dependency is decoded once and shared")

    # -- the second tag-3 record moves the binding by one, MEASURED 349/349
    trn3b = synthetic_terrain()
    trn3b.tag3b = (7, (0.0, 0.0, 0.0, 0.0))
    lead_blobs = dict(blobs)
    lead_blobs[20] = b"????this is not a texture"
    table_lead = {**table, 0x9999: 20}
    block3, _pl3 = build_terrain_textures(
        MapFile(chunks=[_tex_deps(0x9999, *fids)]), trn3b,
        _TexArchive(lead_blobs), table=table_lead)
    check(block3["dep_offset"] == 1
          and [e["file_id"] for e in block3["tiles"]] == list(fids),
          "with tag3b, tile t names dep[t+1] -- the 24-map realignment")
    lead = block3.get("extra_leading")
    check(lead is not None and lead["file_id"] == 0x9999
          and lead["row"] == 20 and lead["size"] == len(lead_blobs[20]),
          "the extra LEADING dependency is recorded with its archive "
          "identity and NOT decoded", f"{lead}")
    check(not any(e["file_id"] == 0x9999 for e in block3["tiles"])
          and all(img["file_id"] != 0x9999 for img in block3["images"]),
          "the leading entry reaches no tile and no image -- its meaning is "
          "UNVERIFIED")

    # -- the two refusals; the corpus law is the evidence, 349/349 each
    check(raises(build_terrain_textures,
                 MapFile(chunks=[_tex_deps(0x1111, 0x2222)]), trn, ar,
                 table=table),
          "a dep list SHORTER than the tile table is refused")
    check(raises(build_terrain_textures,
                 MapFile(chunks=[_tex_deps(0x9999, *fids)]), trn,
                 _TexArchive(lead_blobs), table=table_lead),
          "a dep list LONGER than the table without tag3b is refused -- the "
          "length law is two-sided")
    check(raises(build_terrain_textures,
                 MapFile(chunks=[_tex_deps(*fids)]), trn3b, ar, table=table),
          "tag3b with no extra dependency is refused")
    trn_hot = synthetic_terrain()
    trn_hot.tiles = bytes([3]) * trn_hot.cells
    check(raises(build_terrain_textures,
                 MapFile(chunks=[_tex_deps(*fids)]), trn_hot, ar,
                 table=table),
          "a used tile byte outside the table is refused")
    check(raises(build_terrain_textures, MapFile(chunks=[]), trn, ar,
                 table=table),
          "a map with no Terrain Dependencies chunk is refused")

    # -- what is recorded rather than refused: holes a reader can audit
    table_hole = {0x1111: 10, 0x2222: 11}          # 0x3333 unresolvable
    blockh, _ = build_terrain_textures(
        MapFile(chunks=[_tex_deps(*fids)]), trn, ar, table=table_hole)
    check(blockh["tiles"][2].get("skipped") == "file id not in the "
          "archive's table" and len(blockh["images"]) == 2
          and blockh["census"].get("unresolved") == 1,
          "an unresolvable file id is recorded with its reason, not dropped")
    dds_blobs = dict(blobs)
    dds_blobs[13] = _dds32(4, 4, 0x80FF8040)
    dds_blobs[14] = _dds_refused()
    dds_table = {**table, 0x4444: 13, 0x5555: 14}
    trn5 = synthetic_terrain()
    trn5.table_a = bytes(range(5))
    trn5.table_b = bytes(5)
    blockd, pld = build_terrain_textures(
        MapFile(chunks=[_tex_deps(*fids, 0x4444, 0x5555)]), trn5,
        _TexArchive(dds_blobs), table=dds_table)
    check(blockd["tiles"][3].get("image") is not None
          and blockd["tiles"][3]["width"] == 4
          and blockd["census"].get("dds") == 1,
          "an uncompressed 32-bit DDS decodes (2 of the corpus's 8 "
          "non-ATTX rows are this shape)")
    check(blockd["tiles"][4].get("skipped") ==
          "a DDS shape this decoder refuses"
          and blockd["census"].get("dds_refused") == 1,
          "a DDS this tree cannot decode is recorded with its reason -- "
          "the V8U8 pair's path")

    # -- through the manifest and back, with the negative controls
    dx, dy = SYN_X, SYN_Y
    rect = (0.0, 0.0, dx * CELL_PITCH, dy * CELL_PITCH)
    meta, sidecars = build_manifest(trn, rect, "textest",
                                    {"archive": None, "row": None,
                                     "file_id": None},
                                    terrain_textures=block,
                                    textures_state="exported")
    check(meta["format_version"] == 3 == FORMAT_VERSION,
          "the texture block rides format_version 3")
    outdir = os.path.join(tmp, "t4c")
    path = write_export(meta, sidecars + payloads, outdir)
    exp = load_export(path)
    check(exp.terrain_textures == block
          and exp.meta.get("terrain_textures_state") == "exported",
          "the block round-trips through load_export")
    check(exp.tile_image(0) == f"{TEX_SUBDIR}/tex_1111.png"
          and exp.tile_image(3) is None,
          "tile_image resolves a tile and answers None off the table")

    png_path = os.path.join(outdir, TEX_SUBDIR, "tex_2222.png")
    good = open(png_path, "rb").read()
    with open(png_path, "wb") as fh:
        fh.write(good[:-1] + bytes([good[-1] ^ 0xFF]))
    bad = verify_manifest(path)
    check(any("tex_2222" in b and "sha256" in b for b in bad),
          "NEGATIVE CONTROL: a corrupted texture byte is named by "
          "verify_manifest", f"{bad}")
    check(raises(load_export, path),
          "NEGATIVE CONTROL: load_export refuses the corrupted image")
    os.remove(png_path)
    check(any("tex_2222" in b and "missing" in b
              for b in verify_manifest(path)),
          "NEGATIVE CONTROL: a missing texture file is named")
    with open(png_path, "wb") as fh:
        fh.write(good)
    check(verify_manifest(path) == [],
          "restored, the export verifies clean -- the controls measured "
          "the corruption, not the fixture")


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
        led.skip("7. the props sidecar against the archive", why)
        led.skip("8. the terrain textures against the archive", why)
        return

    with Archive(dat) as ar:
        _section5(check, led, ar, tmp)
        _section6(check, led, ar, args)
        _section7(check, led, ar, tmp)
        _section8(check, led, ar, tmp, args)


def _section5(check, led, ar, tmp):
    print("\n== 5. THE ORACLE: prop z against the exported height field ==")
    print("   props chunk 0x20000004, read here by this file's own walker --\n"
          "   the terrain path never touches it\n")

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

        # textures=False: this section's claim is the LAYOUT, and decoding
        # 51 ground textures per map would treble its runtime saying nothing
        # about it. The texture path has sections 4c and 8.
        path = export_row(row, ar, outdir=os.path.join(tmp, f"m{row}"),
                          file_id=fid, textures=False)
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
    # NO ENTRY-COUNT GATE HERE, and its removal on 2026-08-13 is worth the
    # paragraph. This section used to skip whole unless the archive had exactly
    # 177,342 MFT rows, "because these row constants were measured on it" -- and
    # it has no row constants. Every row it touches comes from `sample_rows`,
    # which selects on `flags == 259` and never on an index. The gate could not
    # fail for the reason it was there and did nothing but hide the section:
    # pointed at `vault/client/2026-04-30_b174de1f2d8d` (177,311 rows, and the
    # same 349 map pairs at the same indices with the same sizes and crcs, 349
    # of 349, MEASURED 2026-08-13) the run dropped four checks and went RED on
    # its own floor.
    #
    # What actually guards this section is the check immediately below: an
    # archive that is not a Guild Wars archive of the right vintage does not
    # hold exactly CORPUS_MAPS rows with those flags, and that is a population
    # assertion the artifact can refute rather than a fact about the copy. Same
    # correction as `test_mapfile.py`'s `resolve_pinned` on the same day --
    # identity of the thing being read, never a census of the file it sits in.
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


# --- 7. the props sidecar against the archive -------------------------------

TAU = 2.0 * math.pi
AXIS_SIGN = (-1.0, 1.0, -1.0)                  # x, y, z -- props.py, MEASURED
BASIS_A0 = (0.0, 0.0, -1.0)                    # the rot-(0,0,0) vectors
BASIS_B0 = (0.0, 1.0, 0.0)
BASIS_TOL = 5e-4                               # f32 chain vs our f64 rebuild

# MEASURED on this archive 2026-08-13, first green run of this section. The
# multi-axis populations are pinned so the rival check cannot go vacuous on a
# map whose props all rotate about one axis; `zyx` is the NEAREST rival (2,070
# of 3,545 on the 12-map probe) and still failed 20 of Kamadan's 53 and 95 of
# Pre-Searing's 179 on that run.
MULTI_AXIS = {KAMADAN_ROW: 53, PRESEARING_ROW: 179}


# --- 8. rung T4 against the archive ------------------------------------------

# The tag3b reference: one of the 24 maps carrying the second tag-3 record,
# picked because its extra LEADING dependency is one of the corpus's four DDS
# rows (0x475C8), so a single export exercises the offset AND shows the
# leading entry staying out of the tile table. MEASURED on this archive
# 2026-08-14 (this rung's scan; the row is this archive's, the file id
# travels).
T3B_ROW = 56835
T3B_LEAD_FID = 0x475C8
KAMADAN_TILES = 51


def _section8(check, led, ar, tmp, args):
    print("\n== 8. rung T4: the terrain textures against the archive ==")
    table = file_id_table(ar)
    by_row = {e.index: e for e in ar.entries}

    row = table.get(KAMADAN_FILE_ID)
    if row is None:
        led.skip("8. terrain textures", "Kamadan's file id unresolved")
        return
    path = export_row(row, ar, outdir=os.path.join(tmp, "t8"),
                      file_id=KAMADAN_FILE_ID)
    exp = load_export(path)
    block = exp.terrain_textures
    check(block is not None
          and exp.meta.get("terrain_textures_state") == "exported",
          "Kamadan exports with its texture block")
    if block is None:
        return

    check(block["dep_offset"] == 0 and block["tile_count"] == KAMADAN_TILES
          and block["dep_count"] == KAMADAN_TILES,
          f"Kamadan: {KAMADAN_TILES} dependencies bind {KAMADAN_TILES} tiles "
          f"directly (no tag3b)",
          f"offset {block['dep_offset']}, {block['tile_count']} tiles")
    check(block["census"] == {"ATTX": KAMADAN_TILES},
          f"Kamadan: all {KAMADAN_TILES} tile textures are ATTX and all "
          f"decode", f"{block['census']}")
    check(len(block["images"]) == KAMADAN_TILES
          and not any("skipped" in e for e in block["tiles"]),
          "no tile was skipped -- the table has no holes on this map")

    # THE RUNG CRITERION: every distinct tile byte the map uses resolves to
    # an image, checked from the SIDECAR's own bytes rather than the block's
    # claim about itself.
    used = sorted(set(exp.tiles))
    check(block["used_tiles"] == used,
          f"used_tiles matches the tiles sidecar ({len(used)} distinct)")
    unresolved = [t for t in used if exp.tile_image(t) is None]
    check(not unresolved,
          f"EVERY distinct tile byte in use ({len(used)}) resolves to a "
          f"decoded image", f"unresolved: {unresolved}")

    # The archive identity on every entry, against rows read here.
    bad_mft = [e["tile"] for e in block["tiles"]
               if by_row[e["row"]].size != e["size"]
               or by_row[e["row"]].crc != e["crc"]
               or table.get(e["file_id"]) != e["row"]]
    check(not bad_mft,
          "every tile's (row, size, crc) matches the MFT read by this test",
          f"disagree: {bad_mft}")

    # One image re-hashed off disk, then the corrupt-a-byte control.
    img = block["images"][0]
    ipath = os.path.join(os.path.dirname(path), img["name"])
    good = open(ipath, "rb").read()
    check(hashlib.sha256(good).hexdigest() == img["sha256"]
          and len(good) == img["bytes"] and good[:8] == PNG_SIG,
          f"{img['name']} on disk is the PNG the manifest promises")
    with open(ipath, "wb") as fh:
        fh.write(good[:100] + bytes([good[100] ^ 1]) + good[101:])
    check(raises(load_export, path),
          "NEGATIVE CONTROL: one flipped byte in one texture refuses the "
          "whole export")
    with open(ipath, "wb") as fh:
        fh.write(good)

    # -- 8b. the tag3b reference map
    t3b_path = export_row(T3B_ROW, ar, outdir=os.path.join(tmp, "t8b"))
    t3b = load_export(t3b_path).terrain_textures
    check(t3b["dep_offset"] == 1
          and t3b["dep_count"] == t3b["tile_count"] + 1,
          f"row {T3B_ROW}: the second tag-3 record shifts the binding by "
          f"one", f"offset {t3b['dep_offset']}")
    lead = t3b.get("extra_leading")
    check(lead is not None and lead["file_id"] == T3B_LEAD_FID
          and by_row[lead["row"]].size == lead["size"],
          f"row {T3B_ROW}: the extra leading dependency is DDS row "
          f"0x{T3B_LEAD_FID:X}, recorded with its identity and not decoded",
          f"{lead}")
    check(not any(e["file_id"] == T3B_LEAD_FID for e in t3b["tiles"])
          and not any("skipped" in e for e in t3b["tiles"]),
          f"row {T3B_ROW}: the leading entry reaches no tile, and every "
          f"tile decodes")

    # -- 8c. the resolution law over the sample (--all for the corpus)
    picks, _all_rows = sample_rows(ar, args.sample, args.all)
    law_ok = law_bad = 0
    for prow in picks:
        mf = MapFile.from_row(prow, ar)
        trn = mf.terrain()
        dep = mf.find(TERRAIN_DEPS_CHUNK)
        if trn is None or dep is None:
            law_bad += 1
            continue
        off = 1 if trn.tag3b is not None else 0
        if (len(dep.value.file_ids) == len(trn.table_a) + off
                and max(trn.tiles) < len(trn.table_a)):
            law_ok += 1
        else:
            law_bad += 1
    check(law_bad == 0 and law_ok == len(picks),
          f"the resolution law (len(dep) == len(table_a) + tag3b, "
          f"max(tiles) < len(table_a)) holds on {len(picks)} of "
          f"{len(picks)} sampled maps (349/349 measured 2026-08-14)",
          f"{law_ok} ok, {law_bad} bad")


def _rotm(axis, theta):
    c, s = math.cos(theta), math.sin(theta)
    if axis == 0:
        return ((1, 0, 0), (0, c, -s), (0, s, c))
    if axis == 1:
        return ((c, 0, s), (0, 1, 0), (-s, 0, c))
    return ((c, -s, 0), (s, c, 0), (0, 0, 1))


def _matmul(m, n):
    return tuple(tuple(sum(m[i][k] * n[k][j] for k in range(3))
                       for j in range(3)) for i in range(3))


def _apply(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def _compose(rot_bytes, order):
    """The rotation matrix for three rot bytes, axis matrices applied in
    `order` (first-to-last). The measured composition is (2, 0, 1): z, x, y."""
    mats = [_rotm(i, AXIS_SIGN[i] * rot_bytes[i] * TAU / 256.0)
            for i in range(3)]
    m = mats[order[0]]
    m = _matmul(mats[order[1]], m)
    return _matmul(mats[order[2]], m)


def _basis_close(m, sa, sb, tol=BASIS_TOL):
    a = _apply(m, BASIS_A0)
    b = _apply(m, BASIS_B0)
    return (all(abs(p - q) <= tol for p, q in zip(a, sa))
            and all(abs(p - q) <= tol for p, q in zip(b, sb)))


def _section7(check, led, ar, tmp):
    print("\n== 7. the props sidecar against the archive and the compiled basis ==")
    table = file_id_table(ar)
    by_row = {e.index: e for e in ar.entries}
    for fid, nprops in ((KAMADAN_FILE_ID, KAMADAN_PROPS),
                        (PRESEARING_FILE_ID, PRESEARING_PROPS)):
        row = table.get(fid)
        if row is None:
            led.skip(f"7. props export of 0x{fid:X}", "file id unresolved")
            continue

        path = export_row(row, ar, outdir=os.path.join(tmp, f"p{row}"),
                          file_id=fid, textures=False)
        exp = load_export(path)
        pd = exp.props
        check(pd is not None and pd["count"] == nprops
              and exp.meta.get("props_state") == "exported",
              f"row {row}: the export carries all {nprops} props",
              f"{pd and pd['count']}, state {exp.meta.get('props_state')!r}")
        if pd is None:
            continue

        # THE INDEPENDENT WALKER. `read_props` is this file's own 48-byte walk
        # over the Bloated chunk, sharing nothing with props.py; every sidecar
        # position must equal it, in order, byte-exactly.
        chunks = read_chunks(ar, row)
        props, _v, _sz, _consumed = read_props(chunks[PROPS_CHUNK])
        same = sum(1 for (x, y, z), r in zip(props, pd["props"])
                   if [x, y, z] == r["position"])
        check(len(props) == pd["count"] and same == pd["count"],
              f"row {row}: every sidecar position equals the test's own "
              f"48-byte walk", f"{same}/{pd['count']}")

        # Placements land inside the map rect -- the same oracle that derived
        # the record stride (props.py; 285,670/285,670 corpus-wide).
        x0, y0, x1, y1 = exp.rect
        inside = sum(1 for r in pd["props"]
                     if x0 <= r["position"][0] <= x1
                     and y0 <= r["position"][1] <= y1)
        check(inside == pd["count"],
              f"row {row}: all {pd['count']} placements land inside the rect",
              f"{inside}/{pd['count']}")

        # The terrain tie: scoring the SIDECAR's positions against the SIDECAR's
        # heights reproduces section 5's pinned baseline, so the two sidecars of
        # one export are placed in the same world.
        frac, _med, n, outside = score_layout(
            exp.heights, exp.dim_x, exp.dim_y, exp.rect,
            [tuple(r["position"]) for r in pd["props"]], "baseline")
        want_f, _ = ORACLE["baseline"][row]
        check(outside == 0 and n == pd["count"]
              and abs(frac - want_f) < FRAC_TOL,
              f"row {row}: the sidecar's own props-vs-heights fraction is "
              f"{want_f}", f"{frac:.4f}, n={n}, outside={outside}")

        # THE COMPOSITION PIN. z first, then x, then y reproduces the compiled
        # basis on every record; the nearest rival order must keep failing.
        multi = m_ok = s_ok = rival_ok = 0
        for r in pd["props"]:
            good = _basis_close(_compose(r["rot_bytes"], (2, 0, 1)),
                                r["basis"][0], r["basis"][1])
            if sum(1 for v in r["rot_bytes"] if v) >= 2:
                multi += 1
                m_ok += good
                if _basis_close(_compose(r["rot_bytes"], (2, 1, 0)),
                                r["basis"][0], r["basis"][1]):
                    rival_ok += 1
            else:
                s_ok += good
        print(f"    row {row}: {multi} multi-axis records, ZXY closes "
              f"{m_ok + s_ok}/{pd['count']}, rival ZYX closes "
              f"{rival_ok}/{multi} of the multi-axis")
        check(m_ok == multi and s_ok == pd["count"] - multi,
              f"row {row}: the ZXY composition reproduces the compiled basis "
              f"on ALL {pd['count']} records",
              f"{m_ok}/{multi} multi, {s_ok}/{pd['count'] - multi} single")
        pinned = MULTI_AXIS[row]
        check(pinned is None or (multi == pinned and rival_ok < multi),
              f"row {row}: the rival order still fails on multi-axis records "
              f"-- the pin has power",
              f"{multi} multi-axis (pinned {pinned}), rival closes {rival_ok}")

        # The scale formula, transported: the compiled f32 must equal the
        # byte's formula on every record, to the bit.
        bad_scale = sum(
            1 for r in pd["props"]
            if struct.pack("<f", r["scale"])
            != struct.pack("<f", r["scale_byte"] * (255 / 128) / 256 + 1 / 128))
        check(bad_scale == 0,
              f"row {row}: scale == the byte formula as f32 on every record",
              f"{bad_scale} disagree")

        # Model identity: every file id resolves in THIS archive and the
        # recorded (size, crc) is the MFT's own.
        ok_m = 0
        for m in pd["models"]:
            mft = m["mft"]
            e = by_row.get(mft["row"]) if mft else None
            if (mft and table.get(m["file_id"]) == mft["row"] and e is not None
                    and e.size == mft["size"] and e.crc == mft["crc"]):
                ok_m += 1
        check(ok_m == len(pd["models"]),
              f"row {row}: all {len(pd['models'])} model files resolve and "
              f"(size, crc) match the MFT", f"{ok_m}/{len(pd['models'])}")

        # Every reference lands in range.
        nm = len(pd["models"])
        check(all(0 <= r["model"] < nm for r in pd["props"])
              and all(0 <= p < pd["count"] for _v, p in pd["refs4"])
              and (pd["refs6"] is None
                   or all(0 <= p < pd["count"]
                          for _v, p in pd["refs6"]["entries"])),
              f"row {row}: every model index and tag-4/6 reference is in range")


def _section_selector_parity(check):
    """`build_blend_layers` must agree with `trnblend.map_layers`, cell for cell.

    These are TWO COPIES of the same loop, and on 2026-08-17 only one of them
    got the physical-mask fix: trnblend was corrected to 212/212 against the
    client and the exporter silently kept the pre-selector behaviour, so a full
    re-export changed exactly ZERO bytes. The diff caught it; nothing in the
    suite would have. This check is that hole closed.
    """
    import trnblend
    import trnvariation
    dim_x = dim_y = 6
    # a patch with real material boundaries, so most cells are mixed
    tiles = [(0 if (gx // 2 + gy // 3) % 2 else 2) if gx != 3 else 1
             for gy in range(dim_y) for gx in range(dim_x)]
    table_a = [0, 1, 2]
    var = [0] * (dim_x * dim_y)

    want = trnblend.map_layers(dim_x, dim_y, tiles, table_a, var)
    got = []
    for gy in range(dim_y):
        gy1 = min(gy + 1, dim_y - 1)
        for gx in range(dim_x):
            gx1 = min(gx + 1, dim_x - 1)
            corners = (tiles[gy * dim_x + gx], tiles[gy * dim_x + gx1],
                       tiles[gy1 * dim_x + gx], tiles[gy1 * dim_x + gx1])
            sel = trnblend.corner_selector(tuple(table_a[c] for c in corners))
            perm = tuple((sel >> (2 * k)) & 3 for k in range(4))
            got.append(trnblend.cell_layers(tuple(corners[p] for p in perm),
                                            table_a, var[gy * dim_x + gx],
                                            perm=perm))
    same = sum(1 for a, b in zip(want, got) if a == b)
    mixed = sum(1 for v in want if len(v) > 1)
    check(same == len(want),
          "the exporter's loop and map_layers agree cell for cell -- two "
          "copies of one rule cannot drift apart silently",
          f"{same}/{len(want)}")
    check(mixed >= 8,
          "and the fixture actually exercises mixed cells, or the check above "
          "is vacuous", f"{mixed} mixed")


if __name__ == "__main__":
    sys.exit(main())
