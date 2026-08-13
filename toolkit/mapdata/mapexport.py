"""Take one map's terrain AND PROPS out of `Gw.dat`; put them in a neutral
interchange.

`terrain.py` and `props.py` decode the chunks; this module turns that into
something a tool which knows nothing about ArenaNet's archive can open. Up to
five files per map:

    <name>.gwmap.json     dims, the world rect, the cell pitch, tag 0's fields,
                          where it came from, and a sha256 for each sidecar
    <name>.heights.f32    dimX*dimY little-endian float32, DE-TILED
    <name>.tiles.u8       dimX*dimY tile indices, same order       (optional)
    <name>.shade.u8       dimX*dimY tag-9 bytes, same order        (optional)
    <name>.props.json     every prop placement, both streams joined (optional)

    python toolkit/mapdata/mapexport.py --row 22371
    python toolkit/mapdata/mapexport.py --file-id 0x345CC --out D:\\scratch

Read back with `load_export(path_to_json)`, which verifies every sha256 before
it hands you a byte.

WHERE THE OUTPUT MAY GO, AND WHY IT IS ENFORCED RATHER THAN DOCUMENTED. An
exported height field is derived ArenaNet data. `CLAUDE.md`'s provenance gate
says zero ArenaNet bytes in the repo, ever, and it is not retrofittable -- so
`resolve_outdir()` REFUSES a destination inside the working tree, with no flag
to override it, and the default is `vault/exports/` (gitignored, local, found
through `vaultpath.py` so a git worktree resolves it correctly). The vault sits
inside the repo ROOT in the main checkout, so the rule is "inside the vault is
fine, anywhere else inside the tree is not" and not a plain prefix test.

This module opens the archive `'rb'` through `Archive` and writes nothing to it.

THE FOUR CONVENTIONS THIS FILE COMMITS TO. Every one is MEASURED, none is ours
to choose, and each is stated in the JSON as well as here so a consumer never
has to guess:

  1. **Cell pitch is 96.0 world units.** Not a parameter. MEASURED two ways --
     `(x1-x0)/dimX` from the Map Parameters chunk is exactly 96.0 on 349/349
     maps, and the client's `TrnDataBloat:191` multiplies by an IEEE double
     96.0. The `(dim-1)` divisor is the control and gives 96.15..96.50.
  2. **Samples sit at cell CORNERS, and the file stores `dimX * dimY` of them.**
     The client allocates a `(dimX/32 + 1) x (dimY/32 + 1)` chunk grid and
     manufactures the extra column and row by REPLICATING their neighbours
     (FINDINGS 17.4: a per-chunk min/max over `mov eax, 0x441` = 1089 = 33x33
     samples for a 32-cell chunk; ArenaNet's own `TrnQueryBasic:385 vertexRect`
     and `TrnMap:935 rect.x1 <= dims.x + 1`). So a mesh has `(dimX+1)*(dimY+1)`
     vertices and `dimX*dimY` quads and spans the rect exactly, but the FILE
     never holds that last column -- `corner_heights()` below is the replication,
     and it is labelled as the client's behaviour, not as stored data.
  3. **Grid row 0 is world maxY.** `gx = int((wx-x0)/96)`, `gy = int((y1-wy)/96)`.
  4. **Heights are emitted AS STORED, and a greater stored value is LOWER in
     the world.** This rule used to read "heights are NOT negated" and cited
     the load path applying no transform -- tag 1 reaches the client's buffers
     through `memcpy` and nothing else (FINDINGS 17.4). That part is still true
     and it is about BYTES, not about which way is up; the headline drawn from
     it was wrong. MEASURED 2026-08-11 (FINDINGS 25) by two client runs
     differing in one sign: a courtyard authored with its floor at -13 and its
     surround at +600 was drawn by the retail client as a MESA, the floor
     standing 613 above the surround; the same map with the surround at -626
     was drawn as a walled enclosure, the surround standing 613 above the floor.
     **So GuildWarsMapBrowser's `Terrain.cpp::GenerateTerrainMesh`, which
     negates every height, agrees with the client, and FINDINGS 16-P5's filing
     of that as "ITS renderer's convention" is CORRECTED.**
     Nothing in this file changes: an interchange format is entitled to carry
     the stored value, and every consumer here is told which it is. What it
     means is that a consumer building a mesh a HUMAN will look at must negate
     z -- `tools/blender/import_gwmap.py` does not, and its mesh is upside down
     relative to what the player sees. 86.4% of corpus samples are negative and
     every one of the 60,468,224 of them is an exact integer, which now reads as
     "most of the world is above the origin" rather than below it.

THE THING MOST LIKELY TO BE WRONG IS THE DE-TILING, so it is the thing checked
hardest. Tag 1's storage order is 32x32 tiles:

    stored_index(gx, gy) = ((gy>>5)*(dimX>>5) + (gx>>5))*1024 + (gy&31)*32 + (gx&31)

and this module emits world row-major, `gy*dimX + gx`. `detile()` does it by
whole 32-element slices for speed; `retile()` is its inverse. Neither is
evidence for the layout -- a permutation agreeing with its own inverse proves
nothing, and `test_mapexport.py` says so and checks `detile` against
`terrain.Terrain.index` element-for-element instead, which is a different
implementation in a module this one does not own.

HOW THE ORIENTATION IS ESTABLISHED, and it is not by anything in the terrain
path. The oracle is a DIFFERENT CHUNK: props, `0x20000004`, carry a world
`(x, y, z)` each. Sampling the exported height field at every prop's `(x, y)`
and comparing with its stored `z` scores the layout. Since 2026-08-13 this
module also EXPORTS the props chunk, so the old framing ("a chunk the exporter
never reads") is dead -- the independence that carries the oracle survives and
is narrower: the TERRAIN path (`detile`, the height sidecar) never reads props,
and the props path never touches the height arrays, so neither can force the
comparison. MEASURED by `test_mapexport.py` on the two reference maps, against
three rival layouts:

    map                 baseline   y-flip   x-flip   not de-tiled
    Kamadan     n=516      0.304    0.070    0.033          0.085
    Pre-Searing n=864      0.734    0.078    0.139          0.137

(fraction of props whose |dz| is under 100 world units). Every control collapses
to under a fifth of the baseline; the not-de-tiled column reproduces FINDINGS 4's
0.089 for the flat row-major rival from the other side, which is a corroboration
nobody set out to make. FINDINGS 4's corpus figures are median |dz| 97.4 and
argmax 0.504 against 0.247 for the nearest rival -- **Kamadan is well below that
median and is reported rather than dropped**; it is a dense city whose props sit
on buildings, and its controls collapse just as hard.

WHAT AN EXPORT IS NOT EVIDENCE OF. Tag 2's tile indices and tag 9's shade bytes
are carried through as arrays whose MEANING is unsettled (`terrain.py` names both
NOT FOUND / not-settled). Exporting them is transport, not understanding. Tag 3
is deliberately not exported at all: its bit-pair position inside a byte is not
established by anything measured, so any per-cell unpacking would be a convention
we invented and could never refute.

THE PROPS SIDECAR (format_version 2, 2026-08-13). Every placement, from BOTH
streams, made to check each other at export time: the Stripped chunk
`0x10000004` (partner row) is the authoring form -- model index, three rot
bytes, scale byte, flags, prop-local outline -- and the Bloated chunk
`0x20000004` (head row) is the compiled form -- the two basis vectors, the f32
scale, the placement radius. `BloatedProps.corresponds()` joins them, retail
satisfies it 349/349, so a disagreement at export is a finding and the export
REFUSES rather than picking a side. The model index resolves through the
dependency chunks (`0x21000004` head, `0x11000004` partner -- MEASURED
identical on 39/39 probed maps, refused on disagreement) to a file id, and the
file id to the MFT's (size, crc) -- recorded because a file id is ARCHIVE
STATE, not a property of the map (`test_contentids.py`).

WHAT A PROPS EXPORT IS AND IS NOT. Placements are MEASUREMENTS -- positions,
ids, bounds, angles -- and sit on the provenance gate's permitted side, in the
vault like everything else here. Model GEOMETRY is not exported and nothing in
this tree decodes it; a prop reaches a consumer as a transform, a footprint and
a radius, never as ArenaNet's mesh.

THE ROTATION COMPOSITION IS MEASURED, closing what `props.py` left open. Each
rot byte b is an angle b*2*pi/256 about x/y/z with signs (-, +, -) (the
single-axis result recorded in `props.py`); the COMPOSITION is z first, then
x, then y -- Blender's 'ZXY' -- which reproduces the compiled basis on
3,545 of 3,545 multi-axis records over a 12-map probe (2026-08-13), the
nearest rival order closing 2,070. `test_mapexport.py` pins it on the
reference maps. The sidecar still carries the compiled basis verbatim, so no
consumer is forced through the formula.

SCOPE. Terrain and props. Zones, water and the navmesh are not exported;
`pathmap.py` already reads the last of those and joining them is a separate
rung. Nothing here writes to an archive.
"""

import argparse
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, file_id_table, DEFAULT_DAT  # noqa: E402
from terrain import CELL_PITCH, CHUNK_SIZE  # noqa: E402
from mapfile import MapFile  # noqa: E402
from mapchunks import next_stream  # noqa: E402
from props import StrippedProps, BloatedProps  # noqa: E402
import vaultpath  # noqa: E402

FORMAT = "rurik.gwmap"
FORMAT_VERSION = 2

#: Versions a reader accepts. 1 is the terrain-only interchange; 2 adds the
#: OPTIONAL props sidecar and changes nothing else, so a version-1 file stays
#: readable forever and a version-2 file with no props sidecar is a version-1
#: file wearing the new number.
FORMAT_VERSIONS_READ = (1, 2)

# The Map Parameters chunk, FINDINGS 3 and 17.4. 41 bytes: u32 signature, u8
# version, four f32 x0,y0,x1,y1 -- which start at the UNALIGNED offset 5,
# because the version is a byte -- then five u32 we do not read. The client's
# own gate is `size >= 41`, not `== 41`.
MAP_PARAMS_CHUNK = 0x2000000C
MAP_PARAMS_SIG = 0x5943EEEF
MAP_PARAMS_VERSION = 2
MAP_PARAMS_MIN = 41
MAP_RECT = struct.Struct("<4f")

# The sidecars, and the one dtype each. Fixed here so the JSON's `dtype` field
# is never a free-form string a reader has to interpret. The first two are
# per-cell arrays and their `count` is the cell count; `json` is the props
# sidecar and its `count` is the prop record count.
DTYPE_F32 = "float32-le"
DTYPE_U8 = "uint8"
DTYPE_JSON = "json"

# The props chunks and their model dependency lists, one pair per stream.
# `props.py` owns both codecs; `mapchunks.py` owns the dependency decode.
PROPS_BLOATED_CHUNK = 0x20000004
PROPS_STRIPPED_CHUNK = 0x10000004
PROPS_DEPS_BLOATED = 0x21000004
PROPS_DEPS_STRIPPED = 0x11000004

# `HERE` is toolkit/mapdata, so the repo root is two levels up FROM IT -- three
# dirnames from the file. The first version of this line took two from the file
# and named `toolkit/`, which let an export be written into the working tree; it
# was caught by running the refusal rather than by reading it, and
# `test_mapexport.py` section 5 now pins the resolved path itself.
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))


# ------------------------------------------------------------ the world rect

def map_rect(payload):
    """`(x0, y0, x1, y1)` out of a Map Parameters chunk payload.

    Both of the client's hard gates are reproduced (`MAP_PARAMS_SIG`, version 2)
    because getting either wrong means we are reading a different chunk and the
    four floats would be noise that still parses.
    """
    payload = bytes(payload)
    if len(payload) < MAP_PARAMS_MIN:
        raise ValueError(f"Map Parameters chunk is {len(payload)} bytes, "
                         f"under the client's {MAP_PARAMS_MIN}-byte gate")
    signature, version = struct.unpack_from("<IB", payload, 0)
    if signature != MAP_PARAMS_SIG:
        raise ValueError(f"Map Parameters signature 0x{signature:08X} != "
                         f"0x{MAP_PARAMS_SIG:08X}")
    if version != MAP_PARAMS_VERSION:
        raise ValueError(f"Map Parameters version {version} != "
                         f"{MAP_PARAMS_VERSION}")
    return MAP_RECT.unpack_from(payload, 5)


# ---------------------------------------------------------------- de-tiling

def detile(values, dim_x, dim_y, tile=CHUNK_SIZE):
    """Storage order to world row-major. `out[gy*dim_x + gx]` is cell (gx, gy).

    Whole-row slices rather than a per-cell index call: one 32-element slice per
    (row, tile-column), which is ~30x faster than calling an index function
    186,368 times and is why a corpus sweep is affordable. `bytes` in gives
    `bytes` out; a list of floats gives a list of floats.

    This is a permutation and nothing more. It is not evidence for the layout --
    see the module docstring for what is.
    """
    if dim_x % tile or dim_y % tile:
        raise ValueError(f"dims {dim_x}x{dim_y} are not both multiples of "
                         f"{tile}; the client gates on it")
    if len(values) != dim_x * dim_y:
        raise ValueError(f"{len(values)} values for a {dim_x}x{dim_y} grid "
                         f"({dim_x * dim_y} cells)")
    tiles_x = dim_x // tile
    out = [0] * (dim_x * dim_y)
    for gy in range(dim_y):
        band = (gy // tile) * tiles_x * tile * tile + (gy % tile) * tile
        row = gy * dim_x
        for bx in range(tiles_x):
            src = band + bx * tile * tile
            out[row + bx * tile:row + (bx + 1) * tile] = values[src:src + tile]
    return bytes(out) if isinstance(values, (bytes, bytearray)) else out


def retile(values, dim_x, dim_y, tile=CHUNK_SIZE):
    """World row-major back to storage order. The inverse of `detile`."""
    if dim_x % tile or dim_y % tile:
        raise ValueError(f"dims {dim_x}x{dim_y} are not both multiples of {tile}")
    if len(values) != dim_x * dim_y:
        raise ValueError(f"{len(values)} values for a {dim_x}x{dim_y} grid")
    tiles_x = dim_x // tile
    out = [0] * (dim_x * dim_y)
    for gy in range(dim_y):
        band = (gy // tile) * tiles_x * tile * tile + (gy % tile) * tile
        row = gy * dim_x
        for bx in range(tiles_x):
            dst = band + bx * tile * tile
            out[dst:dst + tile] = values[row + bx * tile:row + (bx + 1) * tile]
    return bytes(out) if isinstance(values, (bytes, bytearray)) else out


# --------------------------------------------------------- what a reader gets

class MapExport:
    """One exported map, read back from disk. What `load_export` returns.

    Every array is in world row-major order, `gy*dim_x + gx`, with grid row 0 at
    world maxY. `tiles` and `shade` are None when they were not exported.
    `props` is the parsed props sidecar (a dict -- see `build_props` for its
    shape) or None when the export has none.
    """

    __slots__ = ("meta", "dim_x", "dim_y", "rect", "pitch", "heights", "tiles",
                 "shade", "props", "path")

    def __init__(self, meta, dim_x, dim_y, rect, pitch, heights, tiles=None,
                 shade=None, props=None, path=None):
        self.meta = meta
        self.dim_x = dim_x
        self.dim_y = dim_y
        self.rect = tuple(rect)
        self.pitch = pitch
        self.heights = heights
        self.tiles = tiles
        self.shade = shade
        self.props = props
        self.path = path

    @property
    def cells(self):
        return self.dim_x * self.dim_y

    @property
    def extent(self):
        """`dims * pitch`. MEASURED equal to the rect span on 349/349 maps."""
        return self.dim_x * self.pitch, self.dim_y * self.pitch

    @property
    def vertex_dims(self):
        """The MESH lattice: one more than the cells on each axis."""
        return self.dim_x + 1, self.dim_y + 1

    def grid_at(self, wx, wy):
        """World `(x, y)` to grid `(gx, gy)`. Grid row 0 is world maxY."""
        x0, _y0, _x1, y1 = self.rect
        return int((wx - x0) / self.pitch), int((y1 - wy) / self.pitch)

    def world_at(self, gx, gy):
        """The world `(x, y)` of grid corner `(gx, gy)`. No half-cell offset.

        The client computes exactly this -- `x0 + 96*i` and `y1 - 96*j` at
        `0x0074DB5C`-`0x0074DB9A`, with no half-cell term anywhere, which is the
        falsifier for the cell-centre reading and it is absent.
        """
        x0, _y0, _x1, y1 = self.rect
        return x0 + gx * self.pitch, y1 - gy * self.pitch

    def height_at(self, gx, gy):
        return self.heights[gy * self.dim_x + gx]

    def sample(self, wx, wy):
        """Height under a world `(x, y)`, or None outside the grid."""
        gx, gy = self.grid_at(wx, wy)
        if not (0 <= gx < self.dim_x and 0 <= gy < self.dim_y):
            return None
        return self.heights[gy * self.dim_x + gx]

    def corner_heights(self):
        """The `(dimX+1) x (dimY+1)` vertex lattice the CLIENT manufactures.

        The file stores `dimX*dimY`; the loader synthesises the extra column by
        replicating each row's last real sample and the extra row by replicating
        the last real row (FINDINGS 17.4). This is that replication, so a mesh
        built from it spans the rect exactly.

        It is the client's behaviour, not stored data -- and it is why an
        authoring tool must store `dims x dims` and no more: a genuine
        `(dims+1)^2` grid loses its far edge.
        """
        dx, dy = self.dim_x, self.dim_y
        out = []
        for gy in range(dy):
            row = self.heights[gy * dx:(gy + 1) * dx]
            out.extend(row)
            out.append(row[-1])
        out.extend(out[-(dx + 1):])
        return out

    def __repr__(self):
        return (f"<MapExport {self.dim_x}x{self.dim_y} cells, rect {self.rect}, "
                f"pitch {self.pitch}>")


# -------------------------------------------------------------- the manifest

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def verify_manifest(json_path):
    """Every sidecar's size and sha256 against the manifest. `[]` means clean.

    Returns a list of human-readable problems rather than raising, so a caller
    can report all of them at once. `load_export` raises on the first non-empty
    result, because handing back data whose digest disagrees is exactly the
    silent-success failure this repository keeps finding in its own tools.
    """
    with open(json_path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    return _verify_meta(meta, os.path.dirname(os.path.abspath(json_path)))


def _verify_meta(meta, base):
    bad = []
    if meta.get("format") != FORMAT:
        bad.append(f"format is {meta.get('format')!r}, not {FORMAT!r}")
    if meta.get("format_version") not in FORMAT_VERSIONS_READ:
        bad.append(f"format_version is {meta.get('format_version')!r}, "
                   f"not one of {FORMAT_VERSIONS_READ}")
    for side in meta.get("sidecars", []):
        path = os.path.join(base, side["name"])
        if not os.path.isfile(path):
            bad.append(f"{side['name']}: missing")
            continue
        size = os.path.getsize(path)
        if size != side["bytes"]:
            bad.append(f"{side['name']}: {size} bytes on disk, manifest says "
                       f"{side['bytes']}")
            continue
        got = sha256_file(path)
        if got != side["sha256"]:
            bad.append(f"{side['name']}: sha256 {got[:16]}... does not match "
                       f"the manifest's {side['sha256'][:16]}...")
    return bad


def load_export(json_path):
    """Read an export back. Refuses if any sidecar fails its digest.

    Stdlib only and no knowledge of `Gw.dat` -- the whole point of the
    interchange is that a consumer needs neither the archive nor this project's
    decoders.
    """
    json_path = os.path.abspath(json_path)
    base = os.path.dirname(json_path)
    with open(json_path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    bad = _verify_meta(meta, base)
    if bad:
        raise ValueError("export does not verify:\n  " + "\n  ".join(bad))

    dim_x = meta["dims"]["x"]
    dim_y = meta["dims"]["y"]
    cells = dim_x * dim_y
    pitch = meta["cell_pitch"]
    r = meta["map_rect"]
    rect = (r["x0"], r["y0"], r["x1"], r["y1"])

    arrays = {}
    props = None
    for side in meta["sidecars"]:
        with open(os.path.join(base, side["name"]), "rb") as fh:
            blob = fh.read()
        if side["dtype"] == DTYPE_JSON:
            if side["kind"] != "props":
                raise ValueError(f"{side['name']}: unknown json sidecar kind "
                                 f"{side['kind']!r}")
            props = json.loads(blob.decode("utf-8"))
            n = len(props.get("props", ()))
            if side["count"] != n or props.get("count") != n:
                raise ValueError(
                    f"{side['name']}: manifest says {side['count']} props, "
                    f"the sidecar declares {props.get('count')} and holds {n}")
            continue
        # the per-cell array sidecars; their count is the cell count
        if side["count"] != cells:
            raise ValueError(f"{side['name']} holds {side['count']} values for "
                             f"a {dim_x}x{dim_y} grid ({cells} cells)")
        if side["dtype"] == DTYPE_F32:
            arrays[side["kind"]] = list(struct.unpack(f"<{cells}f", blob))
        elif side["dtype"] == DTYPE_U8:
            arrays[side["kind"]] = blob
        else:
            raise ValueError(f"{side['name']}: unknown dtype "
                             f"{side['dtype']!r}")

    if "heights" not in arrays:
        raise ValueError("export has no heights sidecar")
    return MapExport(meta, dim_x, dim_y, rect, pitch, arrays["heights"],
                     tiles=arrays.get("tiles"), shade=arrays.get("shade"),
                     props=props, path=json_path)


# ---------------------------------------------------------- where output goes

def resolve_outdir(outdir=None):
    """The directory an export may be written to. Refuses the working tree.

    Derived ArenaNet bytes never enter the repo (`CLAUDE.md`, and it says
    retrofitting provenance is not possible), so this is a refusal and not a
    warning, and there is no flag that turns it off. The vault lives INSIDE the
    repo root in the main checkout and is gitignored, so it is allowed
    explicitly -- a plain prefix test would refuse the default destination.
    """
    if outdir is None:
        outdir = vaultpath.vault_path("exports")
    outdir = os.path.abspath(outdir)
    vault = os.path.abspath(vaultpath.vault_root())
    if _inside(outdir, vault):
        return outdir
    if _inside(outdir, REPO_ROOT):
        raise ValueError(
            f"refusing to export into the working tree: {outdir}\n"
            f"  An exported height field is derived ArenaNet data and "
            f"CLAUDE.md's provenance gate keeps it out of the repo, "
            f"permanently.\n"
            f"  Write to {vaultpath.vault_path('exports')} (the default) or to "
            f"a scratch directory outside {REPO_ROOT}.")
    return outdir


def _inside(path, root):
    """True if `path` is `root` or below it. Case-folded: this is Windows."""
    path = os.path.normcase(os.path.abspath(path))
    root = os.path.normcase(os.path.abspath(root))
    return path == root or path.startswith(root + os.sep)


# ------------------------------------------------------------- the props

def build_props(head_mf, partner_mf, archive=None):
    """The props sidecar body, or None when the map carries no props chunk.

    Reads BOTH streams and makes them check each other -- `corresponds()` is
    satisfied by retail 349/349, so any refusal below is a finding about the
    source, not a formatting choice. With `archive` given, each model file id
    is also resolved to its MFT row's (size, crc); without one (the in-memory
    path the tests use) `mft` is None.
    """
    cb = head_mf.find(PROPS_BLOATED_CHUNK) if head_mf is not None else None
    cs = (partner_mf.find(PROPS_STRIPPED_CHUNK)
          if partner_mf is not None else None)
    if cb is None and cs is None:
        return None
    if cb is None or cs is None:
        raise ValueError(
            f"props chunk on one side only (Bloated {cb is not None}, "
            f"Stripped {cs is not None}); every retail map carries both or "
            f"neither, so this pair is broken or mismatched")

    sp = StrippedProps.decode(cs.payload())
    bp = BloatedProps.decode(cb.payload())
    bad = bp.corresponds(sp)
    if bad:
        raise ValueError(
            "the two props streams disagree; retail agrees 349/349, so "
            "refusing to export either:\n  " + "\n  ".join(bad[:8]))

    db = head_mf.find(PROPS_DEPS_BLOATED)
    ds = partner_mf.find(PROPS_DEPS_STRIPPED)
    ids_b = db.value.file_ids if db is not None else []
    ids_s = ds.value.file_ids if ds is not None else []
    if ids_b != ids_s:
        raise ValueError(
            f"the model dependency lists disagree ({len(ids_b)} vs "
            f"{len(ids_s)} entries); measured identical on every probed "
            f"retail map, so refusing to pick one")
    need = max((p.model for p in sp.props), default=-1)
    if need >= len(ids_b):
        # `stripbuild.py` refuses this in the write direction for the same
        # reason: the client's failure mode for an unresolvable model has
        # never been measured.
        raise ValueError(
            f"model index {need} into a {len(ids_b)}-entry dependency list; "
            f"an unresolvable model cannot be exported honestly")

    fid_rows = by_row = None
    if archive is not None:
        fid_rows = file_id_table(archive)
        by_row = {e.index: e for e in archive.entries}
    models = []
    for i, fid in enumerate(ids_b):
        entry = None
        if fid_rows is not None:
            row = fid_rows.get(fid)
            entry = by_row.get(row) if row is not None else None
        models.append({
            "index": i,
            "file_id": fid,
            # (size, crc) is the durable identity; `row` is this archive's.
            "mft": None if entry is None else
                   {"row": entry.index, "size": entry.size, "crc": entry.crc},
        })

    records = []
    for spr, rec in zip(sp.props, bp.records):
        records.append({
            "model": spr.model,
            "position": [spr.x, spr.y, spr.z],
            "rot_bytes": list(spr.rot),
            "basis": [list(rec.basis[:3]), list(rec.basis[3:])],
            "scale_byte": spr.scale,
            "scale": rec.scale,
            "radius": struct.unpack("<f", rec.tail)[0],
            "flags": spr.flags,
            "outline": [[dx, dy] for dx, dy in spr.outline],
        })

    return {
        "format": "rurik.gwmap-props",
        "count": len(records),
        # Everything a consumer would otherwise have to guess. Each line's
        # evidence is in this module's docstring and `props.py`'s.
        "conventions": {
            "position": "world (x, y, z); heights share the terrain's "
                        "convention -- a GREATER stored value is LOWER in "
                        "the world (FINDINGS 25)",
            "rotation": "rot_bytes[i] is an angle b*2*pi/256 about "
                        "(x, y, z)[i] with signs (-1, +1, -1), applied z "
                        "first, then x, then y (Blender 'ZXY'). MEASURED "
                        "against the compiled basis, 3545/3545 multi-axis "
                        "records, 12-map probe 2026-08-13; nearest rival "
                        "order 2070. `basis` is the compiler's own two "
                        "vectors -- at rot (0,0,0) they are (0,0,-1), "
                        "(0,1,0) -- prefer them to re-deriving",
            "scale": "scale_byte b -> b*(255/128)/256 + 1/128; `scale` is "
                     "the compiled f32, and the formula holds EXACTLY on "
                     "every retail record",
            "radius": "the compiled placement radius: scale * the model's "
                      "max 2D vertex radius (measured at 1e-5 on "
                      "12,766/12,875 props)",
            "outline": "prop-local i16 (dx, dy); world point = "
                       "(x + dx, y + dy), the client's own add-back",
            "model": "an index into `models`; a file id is ARCHIVE STATE, "
                     "so `mft` (size, crc) is the durable identity",
            "refs": "tag-4/tag-6 pairs [value, prop]; `prop` indexes "
                    "`props`, `value`'s meaning is UNVERIFIED",
        },
        "models": models,
        "props": records,
        "refs4": [[r.value, r.prop] for r in sp.refs4],
        "refs6": None if sp.refs6 is None else
                 {"word": sp.tag6_word,
                  "entries": [[r.value, r.prop] for r in sp.refs6]},
    }


# ------------------------------------------------------------- the export

def build_manifest(trn, rect, name, source, tiles=True, shade=True,
                   props=None, props_state=None):
    """The JSON body and the sidecar payloads, with no file touched yet.

    Split out from `export_map` so the whole interchange can be built in memory
    from a `Terrain` that never came out of an archive -- which is what lets the
    round-trip section of the test run on a bare machine.

    `props` is a `build_props` dict or None; `props_state` names why the
    sidecar is or is not there ("exported", "none in source", "skipped") and
    is omitted from the manifest when None -- the in-memory builders that
    carry no claim about a source archive leave it that way.
    """
    dim_x, dim_y = trn.dim_x, trn.dim_y
    cells = dim_x * dim_y

    heights = detile(trn.heights, dim_x, dim_y)
    payloads = [("heights", f"{name}.heights.f32", DTYPE_F32,
                 struct.pack(f"<{cells}f", *heights), cells)]
    if tiles:
        payloads.append(("tiles", f"{name}.tiles.u8", DTYPE_U8,
                         detile(trn.tiles, dim_x, dim_y), cells))
    if shade:
        payloads.append(("shade", f"{name}.shade.u8", DTYPE_U8,
                         detile(trn.shade, dim_x, dim_y), cells))
    if props is not None:
        blob = (json.dumps(props, indent=2) + "\n").encode("utf-8")
        payloads.append(("props", f"{name}.props.json", DTYPE_JSON, blob,
                         props["count"]))

    x0, y0, x1, y1 = rect
    meta = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "name": name,
        "source": dict(source),
        "dims": {"x": dim_x, "y": dim_y, "cells": cells},
        "map_rect": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
        "cell_pitch": CELL_PITCH,
        "tile_size": CHUNK_SIZE,
        # Everything a consumer would otherwise have to guess, stated rather
        # than left to this module's docstring. See it for the evidence.
        "conventions": {
            "sample_position": "cell corners",
            "array_order": "world row-major, index = gy * dimX + gx",
            "grid_row_0": "world maxY; gx = int((wx-x0)/pitch), "
                          "gy = int((y1-wy)/pitch)",
            # CORRECTED 2026-08-12. This read "as stored; NOT negated (the
            # client's load path applies no transform)" -- the load path fact is
            # still true and is about BYTES, but the headline drawn from it was
            # wrong, and rule 4 above was fixed while this string, which is the
            # MACHINE-READABLE half and the only one a consumer parses, was not.
            "height_sign": "as stored, and a GREATER stored value is LOWER in "
                           "the world (FINDINGS 25). A consumer drawing this "
                           "for a human must negate z.",
            "stored_samples": "dimX * dimY; a mesh has (dimX+1)*(dimY+1) "
                              "vertices, the extra column and row being "
                              "replicated by the client",
            "extent": "dims * pitch, which equals the map_rect span",
        },
        # tag 0, in record order. Three of the seven have no meaning we can
        # support, so they carry their offsets as names -- `terrain.py` does the
        # same and for the same reason.
        "terrain_tag0": {
            "chunk_distance": trn.chunk_distance,
            "angle": trn.angle,
            "tex_word": trn.tex_word,
            "tex_f12": trn.tex_f12,
            "tex_f16": trn.tex_f16,
        },
        # tag 4 / tag 5. Carried because `.tiles.u8` indexes into tag 4 and is
        # meaningless without it; what either table MEANS is NOT FOUND.
        "tile_table_a": list(trn.table_a),
        "tile_table_b": list(trn.table_b),
        "tag_sequence": list(trn.order),
        **({} if props_state is None else {"props_state": props_state}),
        "sidecars": [
            {"kind": kind, "name": fname, "dtype": dtype, "count": count,
             "bytes": len(blob),
             "sha256": hashlib.sha256(blob).hexdigest()}
            for kind, fname, dtype, blob, count in payloads
        ],
    }
    if trn.tag3b is not None:
        meta["terrain_tag3b"] = {"lead": trn.tag3b[0],
                                 "floats": list(trn.tag3b[1])}
    return meta, [(fname, blob) for _k, fname, _d, blob, _c in payloads]


def write_export(meta, payloads, outdir):
    """Write a built manifest and its sidecars. Returns the JSON path."""
    outdir = resolve_outdir(outdir)
    os.makedirs(outdir, exist_ok=True)
    for fname, blob in payloads:
        with open(os.path.join(outdir, fname), "wb") as fh:
            fh.write(blob)
    json_path = os.path.join(outdir, f"{meta['name']}.gwmap.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
        fh.write("\n")
    return json_path


def export_row(row, archive, outdir=None, name=None, file_id=None, tiles=True,
               shade=True, props=True):
    """One MFT row's terrain and props to an interchange on disk.

    Returns the JSON path. `row` is the Bloated HEAD; the props sidecar also
    reads its Stripped partner (resolved through `alloc.nextStream`, the same
    join `mapchunks.MapIndex` makes) because the two streams check each other.
    """
    mf = MapFile.from_row(row, archive)
    trn = mf.terrain()
    if trn is None:
        raise ValueError(f"row {row} has no Bloated terrain chunk 0x"
                         f"{0x20000002:08X} -- a Stripped partner row carries "
                         f"0x10000002, which is a different encoding")
    params = mf.find(MAP_PARAMS_CHUNK)
    if params is None:
        raise ValueError(f"row {row} has no Map Parameters chunk; without it "
                         f"there is no world rect and the grid cannot be placed")
    rect = map_rect(params.value)
    _check_rect(rect, trn.dim_x, trn.dim_y)

    props_dict = None
    props_state = "skipped"
    partner_row = None
    if props:
        entry = next(e for e in archive.entries if e.index == row)
        nxt = next_stream(entry)
        partner = next((e for e in archive.entries if e.index == nxt),
                       None) if nxt else None
        if partner is None:
            if mf.find(PROPS_BLOATED_CHUNK) is not None:
                raise ValueError(
                    f"row {row} carries the Bloated props chunk but its "
                    f"Stripped partner (nextStream {nxt}) resolves to no "
                    f"row; the pair is broken and the streams cannot check "
                    f"each other. --no-props exports the terrain alone.")
            props_state = "none in source"
        else:
            partner_row = partner.index
            partner_mf = MapFile.from_row(partner_row, archive)
            props_dict = build_props(mf, partner_mf, archive=archive)
            props_state = ("exported" if props_dict is not None
                           else "none in source")

    if name is None:
        name = f"map_{file_id:X}" if file_id is not None else f"row_{row}"
    source = {"archive": os.path.basename(archive.path), "row": row,
              "partner_row": partner_row, "file_id": file_id,
              "chunk_count": len(mf), "ffna_type": mf.ffna_type}
    meta, payloads = build_manifest(trn, rect, name, source, tiles=tiles,
                                    shade=shade, props=props_dict,
                                    props_state=props_state)
    return write_export(meta, payloads, outdir)


def export_file_id(file_id, archive, outdir=None, name=None, tiles=True,
                   shade=True, props=True):
    row = file_id_table(archive).get(file_id)
    if row is None:
        raise KeyError(f"no file id 0x{file_id:X} in {archive.path}")
    return export_row(row, archive, outdir=outdir, name=name, file_id=file_id,
                      tiles=tiles, shade=shade, props=props)


def _check_rect(rect, dim_x, dim_y):
    """The cheap cross-chunk check: the rect span must be `dims * 96.0`.

    Two chunks written by different subsystems predicting one another. One row
    of grid error anywhere in the terrain chunk, or a misread rect, and this
    stops being exactly 96.0 -- MEASURED as the only value on 349/349 maps.
    """
    x0, y0, x1, y1 = rect
    px = (x1 - x0) / dim_x
    py = (y1 - y0) / dim_y
    if px != CELL_PITCH or py != CELL_PITCH:
        raise ValueError(
            f"the Map Parameters rect and the terrain dims disagree: "
            f"(x1-x0)/dimX = {px!r} and (y1-y0)/dimY = {py!r}, both of which "
            f"are {CELL_PITCH} on 349 of 349 shipped maps")


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--row", type=int, default=None, help="MFT row to export")
    ap.add_argument("--file-id", default=None,
                    help="map file id instead, e.g. 0x345CC (Kamadan)")
    ap.add_argument("--out", default=None,
                    help="destination directory (default: vault/exports; the "
                         "working tree is refused)")
    ap.add_argument("--name", default=None, help="basename for the three files")
    ap.add_argument("--no-tiles", action="store_true")
    ap.add_argument("--no-shade", action="store_true")
    ap.add_argument("--no-props", action="store_true",
                    help="terrain only; skip the props sidecar and the "
                         "partner-row read it needs")
    ap.add_argument("--verify", default=None, metavar="JSON",
                    help="verify an existing export instead of making one")
    args = ap.parse_args(argv)

    if args.verify:
        bad = verify_manifest(args.verify)
        for line in bad:
            print(f"  [FAIL] {line}")
        if bad:
            print(f"\n{len(bad)} problem(s) in {args.verify}")
            return 1
        exp = load_export(args.verify)
        print(f"[PASS] {args.verify} verifies")
        print(f"  {exp!r}")
        return 0

    if (args.row is None) == (args.file_id is None):
        ap.error("give exactly one of --row and --file-id")

    with Archive(args.dat) as ar:
        if args.row is not None:
            path = export_row(args.row, ar, outdir=args.out, name=args.name,
                              tiles=not args.no_tiles, shade=not args.no_shade,
                              props=not args.no_props)
        else:
            path = export_file_id(int(args.file_id, 0), ar, outdir=args.out,
                                  name=args.name, tiles=not args.no_tiles,
                                  shade=not args.no_shade,
                                  props=not args.no_props)

    exp = load_export(path)
    ex, ey = exp.extent
    vx, vy = exp.vertex_dims
    lo, hi = min(exp.heights), max(exp.heights)
    print(f"wrote {path}")
    print(f"  grid          {exp.dim_x} x {exp.dim_y} cells "
          f"({exp.cells} samples, de-tiled to world row-major)")
    print(f"  mesh          {vx} x {vy} vertices, {exp.cells} quads")
    print(f"  rect          {exp.rect}")
    print(f"  extent        {ex:.0f} x {ey:.0f}   pitch {exp.pitch}")
    print(f"  height        {lo:.0f} .. {hi:.0f}  (as stored -- a greater value "
          f"is LOWER in the world, FINDINGS 25)")
    if exp.props is not None:
        outlined = sum(1 for p in exp.props["props"] if p["outline"])
        print(f"  props         {exp.props['count']} placements, {outlined} "
              f"with outlines, {len(exp.props['models'])} model files")
    else:
        print(f"  props         {exp.meta.get('props_state', 'absent')}")
    print(f"  sidecars      " + ", ".join(s["name"]
                                          for s in exp.meta["sidecars"]))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
