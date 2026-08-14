"""Build a Blender mesh from a `rurik.gwmap` terrain interchange.

    blender --background --python-exit-code 66 \
        --python tools/blender/import_gwmap.py -- \
        <map>.gwmap.json [--out scene.blend] [--dump summary.json] [--clear]

and the same file opened inside Blender's text editor and run with the path in
`--` works identically; nothing here needs a command line to exist.

`--python-exit-code` is not decoration. MEASURED on Blender 5.1.1:
`blender --background --python x.py` exits 0 EVEN WHEN THE SCRIPT RAISES -- the
traceback is printed and the process reports success, so anything downstream that
trusts the exit code reads a refused import as a completed one. Every refusal
below (a bad sha256, a missing sidecar, a wrong format version) only reaches the
shell if that flag is passed.

WHY `bpy` IS ALLOWED IN THIS DIRECTORY AND NOWHERE ELSE. `CLAUDE.md` pins
`toolkit/` to Python 3 standard library only, so that the server and every
checker keep working on a bare machine. `bpy` is not stdlib and is not
installable -- it only exists inside Blender's own interpreter. `tools/blender/`
is outside the `toolkit/` rule for exactly that reason and holds only code that
cannot run anywhere else. Nothing under `toolkit/` imports this file, and
`toolkit/mapdata/test_blenderimport.py` drives it as a SUBPROCESS rather than
importing it, so the stdlib rule is never bent to test it.

THE INTERCHANGE IS READ HERE FROM SCRATCH, and that is deliberate. Blender's
interpreter is not this project's, so a `sys.path` walk into `toolkit/` would be
a dependency the format is supposed to remove: the point of `mapexport.py`'s
output is that a tool which knows nothing about ArenaNet's archive can open it.
The loader below is ~40 lines of `json` and `struct` and verifies every sha256
before it uses a byte, the same as `mapexport.load_export` does. That it is a
SECOND implementation is also why the test can compare the two.

THE CONVENTIONS THIS FILE HONOURS. Every one is MEASURED, none is ours, and each
is restated in the interchange's own `conventions` block. `studies/customarea/
FINDINGS.md` 17.4 is where they were measured and 16-P5/16-P6 is where the
rival conventions are recorded as belonging to somebody else's renderer.

  1. **Cell pitch is 96.0 world units.** A compile-time constant on the client's
     Bloated path and a hard `== 96.0` gate on the Stripped one. This file takes
     the pitch from the interchange rather than hard-coding it, for one reason
     only: a hard-coded 96.0 would make the test's pitch control unable to fail,
     and a check that cannot fail is not a check. It cross-checks instead --
     `dims * pitch` must equal the map rect span, and a disagreement is reported
     loudly on stderr and recorded as `extent_matches_rect: false` in the dump.
  2. **Samples are at cell CORNERS.** The file stores `dimX * dimY` of them; the
     client manufactures the far column and the far row by REPLICATING their
     neighbours (a per-chunk min/max over 1089 = 33x33 samples for a 32-cell
     chunk). So the mesh is `(dimX+1) * (dimY+1)` vertices and `dimX * dimY`
     quads and spans the rect exactly. `corner_heights()` below is that
     replication. Do NOT invent an edge -- an extrapolated or dropped far edge
     is a convention nothing measured supports.
  3. **Grid row 0 is world maxY.** Vertex `(i, j)` sits at `x = x0 + i*pitch`,
     `y = y1 - j*pitch`. So `j` increases as world y DECREASES, which is why the
     quad winding below runs (i,j) -> (i,j+1) -> (i+1,j+1) -> (i+1,j): that is
     the order whose face normal comes out +Z, and the other order is upside
     down.
  4. **z is the NEGATION of the stored float, so the mesh is the right way up.**
     MEASURED 2026-08-11 (FINDINGS 25): two
     client runs differing only in the sign of one height showed that a GREATER
     stored value is LOWER in the world. A courtyard authored floor -13 /
     surround +600 was drawn as a mesa; the same map at surround -626 was drawn
     as a walled enclosure. GuildWarsMapBrowser negates every height and is
     right to; FINDINGS 16-P5's filing of that as "ITS convention" is corrected.
     The load path still applies no transform -- tag 1 reaches the client's
     buffers through `memcpy` -- but that is a fact about bytes, not about which
     way is up.
     **Both sides moved together, 2026-08-12.** `test_blenderimport.py`'s
     orientation oracle compares Blender's vertex z against prop z from chunk
     `0x20000004`, and props are stored in the SAME convention as terrain, so
     the oracle negates the prop too. Its score is INVARIANT under that --
     |-a - -b| == |a - b| -- so 0.7338 must come back unchanged to the fourth
     decimal, and the test asserts that rather than re-measuring it. The oracle
     therefore still cannot see the sign; what warrants it is FINDINGS 25's
     client runs, and the check below says so at the call site.

WHAT THIS FILE IS NOT. It is not an authoring round-trip: nothing here writes to
`Gw.dat`, and the mesh it builds is `(dims+1)^2` vertices, which is one column
and one row MORE than a terrain chunk can store. Anything going the other way
has to drop the manufactured edge, not store it.

The tile indices (`.tiles.u8`) and shade bytes (`.shade.u8`) are loaded when
present and attached as mesh attributes, but their MEANING is unsettled upstream
of here (`terrain.py` labels both NOT FOUND); carrying them is transport, not
understanding, and no geometry depends on them.

REAL PROP MESHES (rung M4, 2026-08-13). When a `.gwmodel` family sits beside
the map export (`models/`, which is what `modelexport.py --map` writes, or
`--models DIR`), each prop gets ArenaNet's ACTUAL geometry instead of the
proxy below -- one mesh datablock per model file id, shared by every prop
using it, so Kamadan's 516 props cost 71 meshes rather than 516 copies. A
prop whose model does not decode (~15% of the corpus) keeps its measured
proxy, so a placement is never lost; `obj["gw_real"]` says which it got and
`--proxies-only` forces the proxy path as a control.

**The model-space z sign is MEASURED, not assumed** -- see `gwmodel_mesh`.
Models are negated exactly as the terrain is, and the check is that prop
geometry ends up ABOVE the ground it stands on: 0.961 of Pre-Searing's real
props against 0.032 for the reflected control, pinned by
`test_blenderimport.py` section 4.

THE GROUND'S MATERIAL (rung T5, 2026-08-14). When the export carries the
`terrain_textures` block (rung T4), every terrain face gets a material: one
Blender material per DISTINCT texture image, `material_index` per face from
the `gw_tile` attribute's value through the manifest's tile table -- the same
pattern the props use, and the binding is the archive's
(`file_id = dep[tile + dep_offset]`, measured 349/349; see `mapexport.py`).
Three deliberate limits, stated so a render is read for what it is:

  * **One opaque layer per cell.** Retail terrain is THREE blended layers per
    cell with the texture's alpha as the mask (only 7 of 192 tiles are fully
    opaque -- `studies/terrain/FINDINGS.md` §3.5), so this ground has hard
    edges at tile boundaries and no alpha wired anywhere. That is honest and
    far better than grey; blending is T6, deferred.
  * **Every cell samples quadrant 0.** A terrain texture is four 128x128
    variants; the per-cell selector is terrain tag 3 plus a per-cell PRNG
    draw (FINDINGS §3.2), and the interchange does not carry tag 3. The UV
    window below is T3's MEASURED arithmetic -- one cell = one variant's
    inner 111x111 texels, corners inset 8.5 texels -- with the variation
    pinned to 0. Which world axis maps to +u is a CONVENTION chosen here;
    nothing measured orients the quadrant yet.
  * **A tile whose texture did not decode gets its OWN empty material**
    (`gw_untextured_<fid>`), never slot 0 -- the prop fall-through defect
    (31.6% of Kamadan's prop area silently drawing whichever image landed
    first) is exactly what this refuses to repeat.

PROPS (format_version 2, 2026-08-13). When the export carries a props sidecar,
every placement becomes a PROXY object in a `<name>.props` collection --
**never ArenaNet's geometry**, which nothing in this tree decodes. A prop with
an outline gets its measured footprint polygon extruded; one without gets a
16-gon cylinder at the measured placement radius (the compiled `radius` field:
scale * the model's max 2D vertex radius). The proxy HEIGHT is invented for
display -- half the radius, floored at 10 -- and is the one number here that
measures nothing; everything else on the object is the archive's. The z
negation is the terrain's (convention 4), so a prop stands ON the mesh it
shipped beside. The outline is NOT rotated -- the compiled ring is literally
`(x + dx, y + dy)`, the client's own add-back, with no rotation term -- while
a radius proxy carries the compiled basis as its object rotation (conjugated
through the z-flip, so det stays +1). Each object records the sidecar record
on itself as custom properties (`gw_index`, `gw_model`, `gw_model_file_id`,
`gw_rot_bytes`, `gw_scale_byte`, `gw_radius`, `gw_flags`).
"""

import argparse
import hashlib
import json
import math
import os
import struct
import sys

try:
    import bpy
except ImportError:                                          # pragma: no cover
    bpy = None

FORMAT = "rurik.gwmap"
# 1 is the terrain-only interchange; 2 adds the OPTIONAL props sidecar; 3 adds
# the OPTIONAL terrain-texture block (rung T4). Each addition changes nothing
# else, so all three load here.
FORMAT_VERSIONS = (1, 2, 3)
# The MODEL interchange (rung M3), read when a prop's model has one beside
# the map export.
MODEL_FORMAT = "rurik.gwmodel"
MODEL_VERSIONS = (1, 2, 3)
DTYPE_F32 = "float32-le"
DTYPE_U8 = "uint8"
DTYPE_JSON = "json"

# The object custom property carrying the manifest across the round trip. Read
# back by `tools/blender/export_gwmap.py`; the two agree on this name and on
# nothing else.
STAMP = "gwmap"
#: The props sidecar's non-per-prop half, for the round trip.
PROPS_STAMP = "gwprops"

# The pitch the interchange is expected to carry. Not used to place a vertex --
# see convention 1 -- only to say so when a file disagrees with the measurement.
EXPECTED_PITCH = 96.0


# ------------------------------------------------------- the interchange
class GwMap(object):
    """One `rurik.gwmap` export, read from disk. Arrays are world row-major.

    `heights[gy * dim_x + gx]`, grid row 0 at world maxY. `tiles` and `shade`
    are None when the export did not carry them.
    """

    def __init__(self, meta, path, heights, tiles=None, shade=None,
                 props=None):
        self.meta = meta
        self.path = path
        self.name = meta.get("name") or os.path.basename(path).split(".")[0]
        self.dim_x = meta["dims"]["x"]
        self.dim_y = meta["dims"]["y"]
        r = meta["map_rect"]
        self.rect = (r["x0"], r["y0"], r["x1"], r["y1"])
        self.pitch = meta["cell_pitch"]
        self.heights = heights
        self.tiles = tiles
        self.shade = shade
        self.props = props

    @property
    def cells(self):
        return self.dim_x * self.dim_y

    @property
    def vertex_dims(self):
        """The mesh lattice: one more than the cells on each axis."""
        return self.dim_x + 1, self.dim_y + 1

    @property
    def extent(self):
        return self.dim_x * self.pitch, self.dim_y * self.pitch

    @property
    def rect_span(self):
        x0, y0, x1, y1 = self.rect
        return x1 - x0, y1 - y0

    def extent_matches_rect(self):
        """`dims * pitch == the rect span`. MEASURED true on 349/349 maps.

        Two chunks written by different subsystems predicting one another, so a
        misread rect, a wrong dim or a wrong pitch all break it.
        """
        return self.extent == self.rect_span

    def world_at(self, i, j):
        """The world `(x, y)` of vertex `(i, j)`. No half-cell offset anywhere.

        The client computes exactly this, `x0 + pitch*i` and `y1 - pitch*j`,
        with no half-cell term -- which is the falsifier for the cell-centre
        reading, and it is absent.
        """
        x0, _y0, _x1, y1 = self.rect
        return x0 + i * self.pitch, y1 - j * self.pitch

    def corner_heights(self):
        """The `(dimX+1) x (dimY+1)` lattice the CLIENT manufactures.

        The file holds `dimX*dimY`; the far column replicates each row's last
        real sample and the far row replicates the last real row. This is the
        client's behaviour, not stored data.
        """
        dx, dy = self.dim_x, self.dim_y
        out = []
        for gy in range(dy):
            row = self.heights[gy * dx:(gy + 1) * dx]
            out.extend(row)
            out.append(row[-1])
        out.extend(out[-(dx + 1):])
        return out

    @property
    def terrain_textures(self):
        """The manifest's terrain-texture block (rung T4), or None."""
        return self.meta.get("terrain_textures")

    def __repr__(self):
        return ("<GwMap %s %dx%d cells, rect %r, pitch %r>"
                % (self.name, self.dim_x, self.dim_y, self.rect, self.pitch))


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_export(json_path):
    """Read an export. RAISES if the format, a size or a sha256 disagrees.

    Refusing beats repairing: an interchange whose digest does not match is a
    file we cannot say anything about, and handing back its bytes with a warning
    is the silent-success failure this repository keeps finding in its own tools.
    """
    json_path = os.path.abspath(json_path)
    base = os.path.dirname(json_path)
    with open(json_path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)

    if meta.get("format") != FORMAT:
        raise ValueError("%s: format is %r, not %r"
                         % (json_path, meta.get("format"), FORMAT))
    if meta.get("format_version") not in FORMAT_VERSIONS:
        raise ValueError("%s: format_version is %r, not one of %r"
                         % (json_path, meta.get("format_version"),
                            FORMAT_VERSIONS))

    cells = meta["dims"]["x"] * meta["dims"]["y"]
    if meta["dims"].get("cells", cells) != cells:
        raise ValueError("%s: dims say %d x %d but cells say %d"
                         % (json_path, meta["dims"]["x"], meta["dims"]["y"],
                            meta["dims"]["cells"]))

    arrays = {}
    props = None
    for side in meta["sidecars"]:
        path = os.path.join(base, side["name"])
        if not os.path.isfile(path):
            raise ValueError("%s: sidecar %s is missing" % (json_path,
                                                            side["name"]))
        size = os.path.getsize(path)
        if size != side["bytes"]:
            raise ValueError("%s: %d bytes on disk, the manifest says %d"
                             % (side["name"], size, side["bytes"]))
        digest = _sha256_file(path)
        if digest != side["sha256"]:
            raise ValueError("%s: sha256 %s... does not match the manifest's "
                             "%s..." % (side["name"], digest[:16],
                                        side["sha256"][:16]))
        with open(path, "rb") as fh:
            blob = fh.read()
        if side["dtype"] == DTYPE_JSON:
            # The props sidecar: its count is PROPS, not cells.
            if side["kind"] != "props":
                raise ValueError("%s: unknown json sidecar kind %r"
                                 % (side["name"], side["kind"]))
            props = json.loads(blob.decode("utf-8"))
            n = len(props.get("props", ()))
            if side["count"] != n or props.get("count") != n:
                raise ValueError(
                    "%s: manifest says %d props, the sidecar declares %r and "
                    "holds %d" % (side["name"], side["count"],
                                  props.get("count"), n))
            continue
        if side["count"] != cells:
            raise ValueError("%s: %d values for a %d-cell grid"
                             % (side["name"], side["count"], cells))
        if side["dtype"] == DTYPE_F32:
            arrays[side["kind"]] = list(struct.unpack("<%df" % cells, blob))
        elif side["dtype"] == DTYPE_U8:
            arrays[side["kind"]] = blob
        else:
            raise ValueError("%s: unknown dtype %r"
                             % (side["name"], side["dtype"]))

    # The terrain-texture images (format_version 3) verify exactly like
    # sidecars; their digests live in their own block because the PNGs are
    # keyed by file id and shared between maps.
    for img in (meta.get("terrain_textures") or {}).get("images", []):
        path = os.path.join(base, img["name"])
        if not os.path.isfile(path):
            raise ValueError("%s: terrain texture %s is missing"
                             % (json_path, img["name"]))
        size = os.path.getsize(path)
        if size != img["bytes"]:
            raise ValueError("%s: %d bytes on disk, the manifest says %d"
                             % (img["name"], size, img["bytes"]))
        digest = _sha256_file(path)
        if digest != img["sha256"]:
            raise ValueError("%s: sha256 %s... does not match the manifest's "
                             "%s..." % (img["name"], digest[:16],
                                        img["sha256"][:16]))

    if "heights" not in arrays:
        raise ValueError("%s: no heights sidecar" % json_path)
    return GwMap(meta, json_path, arrays["heights"],
                 tiles=arrays.get("tiles"), shade=arrays.get("shade"),
                 props=props)


# ------------------------------------------------------------ the geometry
def build_geometry(gwmap):
    """`(verts, faces)` for the map. Pure Python; no `bpy` is touched here.

    `verts[j * (dimX+1) + i]` is vertex `(i, j)`, at
    `(x0 + i*pitch, y1 - j*pitch, height)`. Faces are quads wound
    (i,j) -> (i,j+1) -> (i+1,j+1) -> (i+1,j), which is the order whose normal
    comes out +Z given that world y decreases as j increases.
    """
    dx, dy = gwmap.dim_x, gwmap.dim_y
    x0, _y0, _x1, y1 = gwmap.rect
    pitch = gwmap.pitch
    z = gwmap.corner_heights()
    stride = dx + 1

    verts = [None] * (stride * (dy + 1))
    for j in range(dy + 1):
        wy = y1 - j * pitch
        row = j * stride
        for i in range(stride):
            # NEGATED. A greater stored value is LOWER in the world -- FINDINGS
            # 25, measured by two client runs differing only in this sign. The
            # load path still applies no transform (tag 1 reaches the client's
            # buffers through memcpy), but that is a fact about bytes, not about
            # which way is up. Blender is a place a human LOOKS at the map, so
            # it gets the world's convention and not the file's.
            verts[row + i] = (x0 + i * pitch, wy, -z[row + i])

    faces = [None] * (dx * dy)
    for j in range(dy):
        a = j * stride
        b = a + stride
        out = j * dx
        for i in range(dx):
            faces[out + i] = (a + i, b + i, b + i + 1, a + i + 1)
    return verts, faces


def basis_matrix_blender(basis):
    """The 3x3 rotation for a prop, in BLENDER's frame. Pure Python.

    The sidecar's `basis` is the compiler's own two vectors (basis_a, basis_b),
    which at rot (0,0,0) are (0,0,-1) and (0,1,0) -- so in the GAME frame the
    rotation's columns are (b x -a, b, -a), right-handed (at identity that is
    exactly the identity matrix). Blender's terrain negates z (convention 4), a
    MIRROR, so the rotation must be conjugated through it: B = M R M with
    M = diag(1, 1, -1), which flips the sign of every element with exactly one
    index on the z axis and keeps det = +1.
    """
    a, b = basis
    na = (-a[0], -a[1], -a[2])
    c1 = (b[1] * na[2] - b[2] * na[1],
          b[2] * na[0] - b[0] * na[2],
          b[0] * na[1] - b[1] * na[0])
    # rows of R_game from its columns (c1, b, na)
    r = [[c1[0], b[0], na[0]],
         [c1[1], b[1], na[1]],
         [c1[2], b[2], na[2]]]
    for i in range(3):
        for j in range(3):
            if (i == 2) != (j == 2):
                r[i][j] = -r[i][j]
    return r


def prop_proxy_geometry(rec, min_height=10.0):
    """`(verts, faces, kind)` for one prop's PROXY. Pure Python; local frame.

    An outlined prop is its measured footprint -- the prop-local (dx, dy)
    pairs, which the compiled ring proves are UNROTATED world-axis offsets --
    extruded upward. One without an outline is a 16-gon cylinder at the
    measured placement radius. The HEIGHT is invented for display (half the
    radius, floored at `min_height`); it is the only number here that measures
    nothing.
    """
    radius = rec["radius"]
    h = max(min_height, 0.5 * radius)
    ring = [tuple(p) for p in rec["outline"]]
    if ring:
        if len(ring) > 1 and ring[0] == ring[-1]:
            ring = ring[:-1]                    # closed outlines repeat point 0
        kind = "outline"
    if not ring or len(ring) < 3:
        # 37,505 of 37,548 retail outlines are closed rings; a degenerate one
        # (or none) falls back to the radius cylinder.
        n = 16
        r = max(radius, 1.0)
        ring = [(r * math.cos(2 * math.pi * k / n),
                 r * math.sin(2 * math.pi * k / n)) for k in range(n)]
        kind = "radius"
    n = len(ring)
    verts = ([(x, y, 0.0) for x, y in ring]
             + [(x, y, h) for x, y in ring])
    faces = [tuple(range(n))[::-1], tuple(range(n, 2 * n))]
    for k in range(n):
        k2 = (k + 1) % n
        faces.append((k, k2, n + k2, n + k))
    return verts, faces, kind


def _packed_digest(values):
    """sha256 of the values as little-endian float32, in order.

    The dump carries one of these per axis so a consumer can check EVERY vertex
    rather than the handful it has room to print. float32 because that is what
    a Blender vertex coordinate is, so the comparison is exact rather than
    tolerance-based.
    """
    return hashlib.sha256(struct.pack("<%df" % len(values), *values)).hexdigest()


# --------------------------------------------------------------- Blender
def import_gwmap(json_path, name=None, clear=False):
    """Load an export and put it in the current Blender scene. Returns the object."""
    if bpy is None:                                          # pragma: no cover
        raise RuntimeError(
            "bpy is not importable, so this is not Blender's interpreter. Run "
            "it as:  blender --background --python %s -- <map>.gwmap.json"
            % os.path.abspath(__file__))
    gwmap = load_export(json_path)
    if not gwmap.extent_matches_rect():
        sys.stderr.write(
            "[warn] %s: dims * pitch = %r but the map rect spans %r. These are "
            "equal on 349 of 349 shipped maps, so one of the three is wrong and "
            "the mesh below will not cover the rect.\n"
            % (os.path.basename(json_path), gwmap.extent, gwmap.rect_span))
    if gwmap.pitch != EXPECTED_PITCH:
        sys.stderr.write(
            "[warn] %s: cell pitch is %r, not the measured %r.\n"
            % (os.path.basename(json_path), gwmap.pitch, EXPECTED_PITCH))

    if clear:
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)

    verts, faces = build_geometry(gwmap)
    mesh_name = name or gwmap.name
    mesh = bpy.data.meshes.new(mesh_name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(mesh_name, mesh)
    bpy.context.scene.collection.objects.link(obj)

    _attach_cell_attributes(mesh, gwmap)
    _stamp(obj, gwmap)
    return obj, gwmap


def _stamp(obj, gwmap):
    """Leave the manifest on the object so the way OUT can carry it.

    Tag 0's fields, the two tile tables and the emitted tag sequence are not
    recoverable from a mesh -- a lattice of vertices simply does not contain
    them -- so `export_gwmap.py` reads them back from here. The SIDECAR block is
    stripped: its digests describe the file that was imported, and re-emitting
    them beside heights a human has since edited would produce a manifest that
    verifies against the wrong bytes.

    `dims`, `map_rect` and `cell_pitch` are left in deliberately even though the
    exporter re-derives all three from the geometry. They are what makes its
    cross-check possible: the mesh is what a human edited and therefore wins,
    and a disagreement is worth reporting rather than silently resolving.
    """
    # `props_state` goes with `sidecars`: both describe the file that was
    # imported, and the way OUT rebuilds both from what is in the scene. The
    # terrain-texture block goes with them for the same reason -- its digests
    # describe PNGs beside the file that was imported, and a scene cannot
    # vouch for files it does not contain.
    stamp = {k: v for k, v in gwmap.meta.items()
             if k not in ("sidecars", "props_state", "terrain_textures",
                          "terrain_textures_state")}
    # THE PROPS SIDECAR'S NON-PER-PROP HALF, carried so a round trip can
    # rebuild it. The model table maps a prop's `model` index to an archive
    # file id and that row's (size, crc) -- ARCHIVE STATE, which a Blender
    # scene has no way to re-derive and an exporter must therefore never
    # invent. `refs4`/`refs6` are the Stripped-side reference arrays, whose
    # meaning is UNVERIFIED (`props.PropRef`); they are transported, not
    # understood. The per-prop records are deliberately NOT stamped: those
    # are what the objects carry, and stamping them would let an exporter
    # re-emit the map that was imported no matter what was done to it.
    if gwmap.props is not None:
        obj[PROPS_STAMP] = json.dumps(
            {k: v for k, v in gwmap.props.items() if k != "props"},
            sort_keys=True)
    obj[STAMP] = json.dumps(stamp, sort_keys=True)


# T3's measured cell window (`studies/terrain/FINDINGS.md` §3.1): one cell is
# one 128x128 variant of the 256x256 texture, sampling its inner 111x111
# texels -- corners inset 8.5 texels, algebraically 128 - 17. Quadrant 0's
# window; the module docstring says why the variation is pinned to 0.
TEX_TILE_TEXELS = 256.0
TEX_UV_LO = 8.5 / TEX_TILE_TEXELS
TEX_UV_HI = 119.5 / TEX_TILE_TEXELS


def apply_terrain_textures(obj, gwmap):
    """The ground's materials, per-face indices and UVs (rung T5).

    Returns the summary block the dump carries, or None when the export has
    no texture block. Every claim a checker needs is in the block: the slot
    order, each tile's slot, and a digest over EVERY face's material index --
    so a test outside Blender can tie all 186,368 faces to the sidecar's tile
    bytes without trusting this function's own loop.
    """
    block = gwmap.terrain_textures
    if block is None:
        return None
    mesh = obj.data
    base = os.path.dirname(os.path.abspath(gwmap.path))
    if gwmap.tiles is None:
        # The block names textures but the export carried no tiles array, so
        # there is nothing to bind a face BY. Reported, not guessed.
        return {"state": "no tiles array"}

    # One material per DISTINCT image, in first-appearance tile order; a tile
    # whose texture did not decode gets its own EMPTY material rather than
    # falling through to slot 0 (the prop fall-through defect, refused).
    slot_of_name = {}
    materials = []
    tile_slot = []
    untextured = []
    for entry in block["tiles"]:
        image_name = entry.get("image")
        if image_name is None:
            mat_name = "gw_untextured_%X" % entry["file_id"]
            untextured.append(entry["tile"])
        else:
            mat_name = os.path.basename(image_name)
        if mat_name in slot_of_name:
            tile_slot.append(slot_of_name[mat_name])
            continue
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            mat = bpy.data.materials.new(mat_name)
            if image_name is None:
                # Loudly unbound: flat magenta, no nodes, no image. The
                # render gets worse and the scene gets honest.
                mat.use_nodes = False
                mat.diffuse_color = (1.0, 0.0, 1.0, 1.0)
            else:
                mat.use_nodes = True
                nodes = mat.node_tree.nodes
                links = mat.node_tree.links
                bsdf = nodes.get("Principled BSDF")
                tex = nodes.new("ShaderNodeTexImage")
                image = bpy.data.images.get(mat_name)
                if image is None:
                    image = bpy.data.images.load(
                        os.path.join(base, image_name))
                # CHANNEL_PACKED, and it is a bug fix with a measurement
                # behind it: the alpha here is a three-layer blend MASK
                # (FINDINGS §3.5), not transparency, and under the default
                # STRAIGHT mode Blender premultiplies for rendering -- so
                # the Color output arrived as RGB x alpha and every cell
                # drew its mask as a DARK BAND over clean ground colour
                # (measured on the exported PNGs: window luminance flat,
                # window alpha banded 25-52 rows of 112 below 128).
                # Channel-packed means "colour and alpha are independent
                # data", which is exactly what a splat mask is.
                image.alpha_mode = "CHANNEL_PACKED"
                tex.image = image
                tex.extension = "REPEAT"
                if bsdf is not None:
                    links.new(tex.outputs["Color"],
                              bsdf.inputs["Base Color"])
                # NO alpha wired, deliberately: one opaque layer is the
                # honest simplification. Wiring the mask would punch holes
                # in the ground where the retail client blends.
        slot_of_name[mat_name] = len(materials)
        tile_slot.append(len(materials))
        materials.append(mat)
    for mat in materials:
        mesh.materials.append(mat)

    # material_index per face from the tiles array -- the SAME world
    # row-major order as the faces, so the mapping is the identity.
    indices = [tile_slot[t] for t in gwmap.tiles]
    mesh.polygons.foreach_set("material_index", indices)

    # SMOOTH-SHADED, because the client's terrain is: both vertex layouts
    # T3 read out of the chunk builders carry a per-vertex NORMAL (FVF
    # 0xF05 and 0x105), and the lo path SHARES its 33x33 vertices between
    # cells. Faceted quads were this importer's artifact -- the stair-step
    # look on every slope -- not the archive's.
    mesh.polygons.foreach_set("use_smooth", [True] * len(mesh.polygons))

    # T3's UV window, identical on every face. Loop order is the quad winding
    # from build_geometry: (i,j) -> (i,j+1) -> (i+1,j+1) -> (i+1,j), with j
    # increasing as world y DECREASES; v is flipped for Blender exactly as
    # the prop UVs are (Direct3D puts v=0 at the top of an image).
    lo, hi = TEX_UV_LO, TEX_UV_HI
    quad = [(lo, 1.0 - lo), (lo, 1.0 - hi), (hi, 1.0 - hi), (hi, 1.0 - lo)]
    layer = mesh.uv_layers.new(name="UVMap")
    flat = [c for uv in quad for c in uv] * len(mesh.polygons)
    layer.data.foreach_set("uv", flat)

    # Read the indices BACK off the built mesh for the digest, so anything
    # Blender did on the way in shows up in it. Same for the smooth flags
    # and the images' alpha mode: the dump reports the scene, not the loop
    # that built it.
    got = [0] * len(mesh.polygons)
    mesh.polygons.foreach_get("material_index", got)
    digest = hashlib.sha256(struct.pack("<%dH" % len(got), *got)).hexdigest()
    counts = {}
    for s in got:
        counts[s] = counts.get(s, 0) + 1
    smooth = [False] * len(mesh.polygons)
    mesh.polygons.foreach_get("use_smooth", smooth)
    modes = sorted({m.node_tree.nodes["Image Texture"].image.alpha_mode
                    for m in materials
                    if m.use_nodes and "Image Texture" in m.node_tree.nodes})
    return {
        "state": "bound",
        "materials": [m.name for m in materials],
        "tile_slot": tile_slot,
        "untextured_tiles": untextured,
        "faces_per_slot": {str(k): v for k, v in sorted(counts.items())},
        "material_index_digest": digest,
        "uv_layer": "UVMap",
        "uv_window": [lo, hi],
        "faces_smooth": sum(smooth),
        "image_alpha_modes": modes,
    }


def _attach_cell_attributes(mesh, gwmap):
    """Per-FACE tile index and shade byte, when the export carried them.

    One value per cell and one face per cell, in the same world row-major order,
    so the mapping is the identity. Both are transported with their meanings
    unsettled -- see the module docstring -- and nothing geometric reads them.
    """
    for kind, data in (("gw_tile", gwmap.tiles), ("gw_shade", gwmap.shade)):
        if data is None:
            continue
        attr = mesh.attributes.new(name=kind, type="INT", domain="FACE")
        attr.data.foreach_set("value", list(data))


def load_gwmodel(json_path):
    """One `.gwmodel` export: `(meta, positions, per-sub-model triangles)`.

    A SECOND independent reader, for the same reason `load_export` is one:
    Blender's interpreter is not this project's, and a `sys.path` walk into
    `toolkit/` would reintroduce the dependency the interchange exists to
    remove. Verifies every sidecar's size and sha256 before using a byte.
    """
    base = os.path.dirname(os.path.abspath(json_path))
    with open(json_path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    if meta.get("format") != MODEL_FORMAT:
        raise ValueError("%s: format is %r, not %r"
                         % (json_path, meta.get("format"), MODEL_FORMAT))
    if meta.get("format_version") not in MODEL_VERSIONS:
        raise ValueError("%s: format_version %r not in %r"
                         % (json_path, meta.get("format_version"),
                            MODEL_VERSIONS))
    blobs = {}
    for side in meta["sidecars"]:
        path = os.path.join(base, side["name"])
        if not os.path.isfile(path):
            raise ValueError("%s: sidecar %s missing" % (json_path,
                                                          side["name"]))
        if os.path.getsize(path) != side["bytes"]:
            raise ValueError("%s: %d bytes, manifest says %d"
                             % (side["name"], os.path.getsize(path),
                                side["bytes"]))
        if _sha256_file(path) != side["sha256"]:
            raise ValueError("%s: sha256 does not match the manifest"
                             % side["name"])
        with open(path, "rb") as fh:
            blobs[side["kind"]] = (fh.read(), side["count"])

    if "pos" not in blobs:
        raise ValueError("%s: no position sidecar" % json_path)
    blob, n = blobs["pos"]
    flat = struct.unpack("<%df" % (3 * n), blob)
    positions = [(flat[i * 3], flat[i * 3 + 1], flat[i * 3 + 2])
                 for i in range(n)]
    idx = []
    if "idx" in blobs:
        blob, n = blobs["idx"]
        idx = list(struct.unpack("<%dH" % n, blob))
    uvs = []
    if "uv0" in blobs:
        blob, n = blobs["uv0"]
        flat = struct.unpack("<%df" % (2 * n), blob)
        uvs = [(flat[i * 2], flat[i * 2 + 1]) for i in range(n)]
    return meta, positions, idx, uvs


def gwmodel_materials(meta, models_dir):
    """`(materials_by_image, image_per_submodel)` for one model.

    One Blender material per distinct PNG the model names, reused across
    every model that shares it -- 316 exported models reference 472 distinct
    images, so per-model copies would multiply both.

    Alpha is wired to the shader so cut-out textures (foliage, fences,
    grates) are not solid rectangles; blend mode is left at Blender's default
    rather than guessed per texture, because nothing measured says which
    textures are meant to be alpha-tested and which alpha-blended -- that
    lives in the AMAT materials this export does not decode.

    **THE SLOT THIS PICKS IS NOT THE ESTABLISHED DIFFUSE.** A sub-model's
    `material_index` is a real per-sub-model index (see `modelexport`), but
    rendering Kamadan with it puts a specular/gloss map on most building
    surfaces while awnings and foliage come out correct -- so `0xFA5` is a
    MIXED list of map kinds and this index does not name the colour one. The
    material chain almost certainly runs through the AMAT chunk `0xFAD`,
    which nothing here decodes. Textures are attached anyway because the
    scene is far more useful with them than without, and `--no-textures` is
    the control; but a render from this file is NOT evidence about which
    texture a surface should carry.
    """
    slots = meta.get("textures") or []
    by_image, per_sub = {}, {}
    # Which images are drawn by a BLENDED material. The archive says which
    # materials need it (`blend` non-zero) and that is better evidence than
    # guessing from pixels -- a texture can carry alpha and still be drawn
    # opaque. Portals and mist are the visible case: without this they are
    # black rectangles, because their texture has no fully opaque pixel.
    blended = set()
    for sm in meta["submodels"]:
        mat = sm.get("material") or {}
        if not mat.get("blend"):
            continue
        for lay in (mat.get("layers") or []):
            slot = lay.get("texpath")
            if slot is not None and slot < len(slots):
                name = slots[slot].get("image")
                if name:
                    blended.add(name)
    for entry in slots:
        image_name = entry.get("image")
        if not image_name:
            continue
        if image_name in by_image:
            continue
        path = os.path.join(models_dir, image_name)
        if not os.path.isfile(path):
            continue
        mat = bpy.data.materials.get(image_name)
        if mat is None:
            mat = bpy.data.materials.new(image_name)
            mat.use_nodes = True
            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            bsdf = nodes.get("Principled BSDF")
            tex = nodes.new("ShaderNodeTexImage")
            image = bpy.data.images.get(image_name)
            if image is None:
                image = bpy.data.images.load(path)
            tex.image = image
            tex.extension = "REPEAT"          # texcoords are not normalised
            if bsdf is not None:
                links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
                if "Alpha" in bsdf.inputs:
                    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
        if image_name in blended:
            # Blender 4.2+ renamed these; older builds want 'BLEND'. Try in
            # order and leave the default alone if none is accepted, rather
            # than failing the whole import over a display setting.
            for value in ("BLENDED", "BLEND"):
                try:
                    mat.blend_method = value
                    break
                except TypeError:
                    continue
        by_image[image_name] = mat
    for s, sm in enumerate(meta["submodels"]):
        # THE BINDING, and it is a chain rather than an index (format 3):
        # sub-model -> material -> layers -> texPathIndex -> FA5 slot.
        # Layer 0 is the BASE layer. Using material_index as an FA5 index
        # directly -- which is what this did before the material table was
        # decoded -- is what put specular maps on Kamadan's buildings.
        mat = sm.get("material") or {}
        layers = mat.get("layers") or []
        slot = None
        if layers:
            # THE DIFFUSE IS THE FIRST LAYER SAMPLING A STORED UV SET, not
            # simply layer 0. A layer whose `uv` is NEGATIVE has GENERATED
            # coordinates -- a reflection/environment effect, which is what
            # renders as black with soft highlights and is exactly what was
            # landing on Kamadan's walls. MEASURED: 92 of 1,063 layered
            # sub-models put such a layer FIRST, and the two largest wall
            # models on Kamadan are both among them.
            stored = [lay for lay in layers if (lay.get("uv") or 0) >= 0]
            slot = (stored or layers)[0].get("texpath")
        elif mat.get("kind") in (None, "none"):
            # format 2 and earlier carried no material table; fall back to
            # the old reading so an old export still shows something.
            slot = sm.get("material_index", sm.get("texture"))
        if slot is None or slot >= len(slots):
            continue
        name = slots[slot].get("image")
        if name in by_image:
            per_sub[s] = name
    return by_image, per_sub


def gwmodel_mesh(meta, positions, idx, mesh_name, uvs=(),
                 materials=None, sub_images=None):
    """A Blender mesh for one model, in Blender's world-up convention.

    **z is NEGATED, exactly as the terrain's is, and that is MEASURED rather
    than assumed** (M4, 2026-08-13). Scoring every prop of both reference maps
    by whether its geometry ends up ABOVE the terrain it stands on:

        negate model z (the terrain's convention)   Kamadan 73.2%, Pre-Searing 83.3%
        leave it as stored                          Kamadan 23.8%, Pre-Searing  6.5%

    The diagnostic behind it: a model's own z runs from about +34 down to
    -642 (median over Kamadan's 71 decoded models), i.e. it extends from just
    under its origin far into negative z -- which is UP once negated, exactly
    what a tree or a wall standing on its base should do.

    Vertices are LOCAL: the prop's own transform applies position, rotation
    and scale.
    """
    verts = [(x, y, -z) for x, y, z in positions]
    faces = []
    face_sub = []
    for s, sm in enumerate(meta["submodels"]):
        vb, ib, ti = sm["vertex_base"], sm["index_base"], sm["ti"]
        tri = idx[ib:ib + ti]
        for i in range(0, len(tri) - 2, 3):
            faces.append((vb + tri[i], vb + tri[i + 1], vb + tri[i + 2]))
            face_sub.append(s)
    mesh = bpy.data.meshes.new(mesh_name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()

    # UVs, per LOOP. The exporter's texcoords are per VERTEX, so each face
    # corner takes its own vertex's pair.
    #
    # **v IS FLIPPED.** Direct3D puts v=0 at the TOP of an image and Blender
    # puts it at the bottom, so `v_blender = 1 - v`. That is a convention of
    # the two tools rather than a fact about the archive, which is why it is
    # applied HERE and not in the interchange -- `modelexport` carries
    # ArenaNet's own numbers unchanged.
    #
    # Texcoords are NOT normalised (97.8% inside +/-16 over a measured range
    # of -519.7..520.4), so materials must WRAP. Nothing is clamped here.
    if uvs:
        layer = mesh.uv_layers.new(name="UVMap")
        for poly in mesh.polygons:
            for li in poly.loop_indices:
                vi = mesh.loops[li].vertex_index
                if vi < len(uvs):
                    u, v = uvs[vi]
                    layer.data[li].uv = (u, 1.0 - v)

    # One material slot per sub-model TEXTURE SLOT, so a face draws with the
    # image its sub-model names. See `modelexport`'s `texture` field for how
    # well supported that binding is -- it is INFERRED, not proven.
    if materials:
        slot_of = {}
        for image_name, mat in materials.items():
            slot_of[image_name] = len(mesh.materials)
            mesh.materials.append(mat)
        for poly, s in zip(mesh.polygons, face_sub):
            name = sub_images.get(s)
            if name in slot_of:
                poly.material_index = slot_of[name]
    return mesh


def _model_dir(gwmap, explicit=None):
    """Where the `.gwmodel` family lives. `models/` beside the map export by
    default, which is what `modelexport.py --map` produces."""
    if explicit:
        return explicit
    return os.path.join(os.path.dirname(os.path.abspath(gwmap.path)), "models")


def build_prop_objects(gwmap, name=None, models_dir=None,
                       proxies_only=False, no_textures=False):
    """Every placement as an object in its own collection.

    Returns `(collection, objects)`, or `(None, [])` when the export carries
    no props. A prop whose model has a `.gwmodel` beside the map export gets
    the REAL mesh, instanced -- every prop sharing a model shares one mesh
    datablock, so Kamadan's 516 props cost 71 meshes. A prop whose model does
    NOT decode (~15% of the corpus) keeps the measured PROXY, so the scene
    never silently loses a placement; `obj["gw_real"]` says which it got.
    """
    import mathutils
    pd = gwmap.props
    if pd is None:
        return None, []
    base = name or gwmap.name
    coll = bpy.data.collections.new("%s.props" % base)
    bpy.context.scene.collection.children.link(coll)

    # ONE mesh datablock per model file id, shared by every prop that uses it.
    # Kamadan's 516 props resolve to 71 meshes; building a copy per prop would
    # be 38,952 vertices seven times over.
    mdir = _model_dir(gwmap, models_dir)
    shared = {}
    if not proxies_only:
        for m in pd["models"]:
            path = os.path.join(mdir, "model_%X.gwmodel.json" % m["file_id"])
            if not os.path.isfile(path):
                continue                  # the ~15% that never decoded
            try:
                meta, positions, idx, uvs = load_gwmodel(path)
            except (ValueError, KeyError, struct.error) as exc:
                sys.stderr.write("[warn] %s: %s\n"
                                 % (os.path.basename(path), exc))
                continue
            mats, sub_images = ({}, {})
            if not no_textures:
                mats, sub_images = gwmodel_materials(meta, mdir)
            shared[m["index"]] = gwmodel_mesh(
                meta, positions, idx, "gwmodel_%X" % m["file_id"],
                uvs=uvs, materials=mats, sub_images=sub_images)

    objs = []
    for i, rec in enumerate(pd["props"]):
        mesh = shared.get(rec["model"])
        real = mesh is not None
        kind = "real"
        if not real:
            verts, faces, kind = prop_proxy_geometry(rec)
            mesh = bpy.data.meshes.new("prop_%04d_m%d" % (i, rec["model"]))
            mesh.from_pydata(verts, [], faces)
            mesh.update()
        obj = bpy.data.objects.new(
            ("prop_%04d_m%d" % (i, rec["model"])), mesh)
        coll.objects.link(obj)

        x, y, z = rec["position"]
        rows = [[1.0, 0.0, 0.0, x],
                [0.0, 1.0, 0.0, y],
                [0.0, 0.0, 1.0, -z],          # convention 4: negated, like
                [0.0, 0.0, 0.0, 1.0]]         # the terrain it stands on
        # A REAL mesh is model-space, so it takes the prop's full transform:
        # rotation from the compiled basis and the prop's scale. A radius
        # proxy takes the rotation only (its size already came from the
        # measured radius, which has the scale in it), and an OUTLINE proxy
        # takes neither -- its ring is measured UNROTATED and UNSCALED (the
        # compiled ring is literally x+dx, y+dy), so transforming it would
        # move measured points to invented ones.
        if real or kind == "radius":
            b = basis_matrix_blender(rec["basis"])
            s = rec["scale"] if real else 1.0
            for r in range(3):
                for c in range(3):
                    rows[r][c] = b[r][c] * s
        obj.matrix_world = mathutils.Matrix(rows)

        model = pd["models"][rec["model"]] if rec["model"] < len(
            pd["models"]) else None
        obj["gw_index"] = i
        obj["gw_model"] = rec["model"]
        obj["gw_model_file_id"] = -1 if model is None else model["file_id"]
        obj["gw_rot_bytes"] = list(rec["rot_bytes"])
        obj["gw_scale_byte"] = rec["scale_byte"]
        obj["gw_radius"] = rec["radius"]
        obj["gw_flags"] = rec["flags"]
        obj["gw_proxy"] = kind
        obj["gw_real"] = real
        # CARRIED FOR THE ROUND TRIP, because a mesh cannot hold them and an
        # exporter that had to invent them would be writing fiction. The
        # OUTLINE especially: a real-mesh prop draws none of it, so without
        # this the footprint the client compiles from would be lost the first
        # time a scene went back out.
        obj["gw_outline"] = [c for pt in rec["outline"] for c in pt]
        obj["gw_basis"] = [c for v in rec["basis"] for c in v]
        objs.append(obj)
    return coll, objs


def props_summary(objs, gwmap):
    """The props block of the dump: what a checker outside Blender needs."""
    out = []
    for obj in objs:
        loc = obj.matrix_world.translation
        out.append({"name": obj.name,
                    "location": [loc.x, loc.y, loc.z],
                    "model": obj["gw_model"],
                    "file_id": obj["gw_model_file_id"],
                    "radius": obj["gw_radius"],
                    "proxy": obj["gw_proxy"],
                    "real": bool(obj["gw_real"]),
                    "mesh": obj.data.name,
                    "verts": len(obj.data.vertices),
                    # World-space z extent, which is what the "sits above the
                    # terrain" check needs and cannot get from the location.
                    "zmin": min((obj.matrix_world @ v.co).z
                                for v in obj.data.vertices),
                    "zmax": max((obj.matrix_world @ v.co).z
                                for v in obj.data.vertices)})
    pd = gwmap.props or {}
    return {"count": len(objs),
            "sidecar_count": pd.get("count", 0),
            "outlined": sum(1 for o in objs if o["gw_proxy"] == "outline"),
            "real": sum(1 for o in objs if o["gw_real"]),
            "proxy": sum(1 for o in objs if not o["gw_real"]),
            # One datablock per model, shared: the count of DISTINCT meshes
            # among real-mesh props is what proves the instancing.
            "real_meshes": len({o.data.name for o in objs if o["gw_real"]}),
            "materials": len({m.name for o in objs if o["gw_real"]
                              for m in o.data.materials if m}),
            "uv_meshes": len({o.data.name for o in objs if o["gw_real"]
                              and o.data.uv_layers}),
            "objects": out}


def mesh_summary(obj, gwmap):
    """Everything a checker outside Blender needs, as plain JSON-able values.

    Read back off the BUILT mesh (`mesh.vertices`, `mesh.polygons`) and not off
    the lists that were handed to `from_pydata`, so that anything Blender did to
    the geometry on the way in shows up here.
    """
    mesh = obj.data
    n = len(mesh.vertices)
    co = [0.0] * (3 * n)
    mesh.vertices.foreach_get("co", co)
    xs = co[0::3]
    ys = co[1::3]
    zs = co[2::3]

    stride = gwmap.dim_x + 1

    def at(i, j):
        k = j * stride + i
        return {"i": i, "j": j, "index": k,
                "x": xs[k], "y": ys[k], "z": zs[k]}

    dx, dy = gwmap.dim_x, gwmap.dim_y
    # The four rect corners of the LATTICE, named by the world compass. Row 0 is
    # world maxY, so j = 0 is north.
    corners = {"nw": at(0, 0), "ne": at(dx, 0),
               "sw": at(0, dy), "se": at(dx, dy)}
    # A deterministic scatter, so the check is not only about the boundary.
    step_i = max(1, dx // 7)
    step_j = max(1, dy // 7)
    probes = [at(i, j)
              for j in range(0, dy + 1, step_j)
              for i in range(0, dx + 1, step_i)]

    poly_sizes = {}
    for poly in mesh.polygons:
        poly_sizes[poly.loop_total] = poly_sizes.get(poly.loop_total, 0) + 1
    normals_up = sum(1 for poly in mesh.polygons if poly.normal.z > 0.0)

    return {
        "format": FORMAT,
        "name": obj.name,
        "source_json": gwmap.path,
        "blender": bpy.app.version_string,
        "dims": {"x": dx, "y": dy},
        "cell_pitch": gwmap.pitch,
        "map_rect": list(gwmap.rect),
        "extent_matches_rect": gwmap.extent_matches_rect(),
        "vertex_count": n,
        "edge_count": len(mesh.edges),
        "face_count": len(mesh.polygons),
        "face_sizes": {str(k): v for k, v in sorted(poly_sizes.items())},
        "faces_normal_up": normals_up,
        "first_face": list(mesh.polygons[0].vertices) if mesh.polygons else [],
        "bbox": {"min": [min(xs), min(ys), min(zs)],
                 "max": [max(xs), max(ys), max(zs)]},
        "corners": corners,
        "probes": probes,
        "digest_x": _packed_digest(xs),
        "digest_y": _packed_digest(ys),
        "digest_z": _packed_digest(zs),
        "attributes": sorted(a.name for a in mesh.attributes),
        # Which keys of the manifest made it onto the object. The
        # round-trip test reads this rather than reopening the .blend, so a
        # stamp that silently stopped being written fails on the way IN instead
        # of surfacing as a lost tile table on the way out.
        "stamp_keys": sorted(json.loads(obj[STAMP]).keys()) if STAMP in obj
                      else [],
    }


# ------------------------------------------------------------------ the CLI
def _script_argv(argv=None):
    """The arguments after `--`, which is how Blender hands a script its own.

    Blender consumes everything before `--` itself. Outside Blender there is no
    `--`, so the plain tail is used and the script still runs under `python`
    far enough to report that `bpy` is missing.
    """
    argv = list(sys.argv[1:] if argv is None else argv)
    return argv[argv.index("--") + 1:] if "--" in argv else argv


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="import_gwmap.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("json", help="the <name>.gwmap.json of an export")
    ap.add_argument("--out", default=None,
                    help="save the scene to this .blend when done")
    ap.add_argument("--dump", default=None,
                    help="write the built mesh's summary here as JSON")
    ap.add_argument("--dump-verts", default=None, metavar="F32",
                    help="write every vertex as interleaved little-endian "
                         "float32 x,y,z -- what a checker outside Blender needs "
                         "to score the MESH itself against something")
    ap.add_argument("--name", default=None, help="name for the object and mesh")
    ap.add_argument("--clear", action="store_true",
                    help="empty the scene first (the startup cube and friends)")
    ap.add_argument("--no-props", action="store_true",
                    help="terrain only; skip the props collection even when "
                         "the export carries the sidecar")
    ap.add_argument("--models", default=None, metavar="DIR",
                    help="where the .gwmodel family lives (default: models/ "
                         "beside the map export)")
    ap.add_argument("--no-textures", action="store_true",
                    help="build prop meshes without materials or UVs -- the "
                         "control for the texture path")
    ap.add_argument("--no-terrain-textures", action="store_true",
                    help="leave the ground unmaterialed even when the export "
                         "carries the texture block -- the control for the "
                         "T5 path")
    ap.add_argument("--proxies-only", action="store_true",
                    help="force the measured proxies even where a real mesh "
                         "is available -- the control for the real-mesh path")
    args = ap.parse_args(_script_argv(argv))

    obj, gwmap = import_gwmap(args.json, name=args.name, clear=args.clear)
    terrain_tex = None
    if not args.no_terrain_textures:
        terrain_tex = apply_terrain_textures(obj, gwmap)
    summary = mesh_summary(obj, gwmap)
    if terrain_tex is not None:
        summary["terrain_textures"] = terrain_tex
    elif gwmap.terrain_textures is not None:
        summary["terrain_textures"] = {"state": "skipped"}
    prop_objs = []
    if not args.no_props and gwmap.props is not None:
        _coll, prop_objs = build_prop_objects(
            gwmap, name=args.name, models_dir=args.models,
            proxies_only=args.proxies_only, no_textures=args.no_textures)
        summary["props"] = props_summary(prop_objs, gwmap)

    print("imported %s" % gwmap)
    print("  mesh          %d vertices, %d quads (%d x %d cells)"
          % (summary["vertex_count"], summary["face_count"],
             gwmap.dim_x, gwmap.dim_y))
    print("  bbox min      %r" % (summary["bbox"]["min"],))
    print("  bbox max      %r" % (summary["bbox"]["max"],))
    print("  rect          %r   pitch %r" % (list(gwmap.rect), gwmap.pitch))
    # WORLD z, not stored. This line said "AS STORED ... so this mesh is upside
    # down" until 2026-08-12, which was true of the mesh it described and became
    # false in the same commit that negated the z -- the docstring's rule 4 moved
    # and the readout did not.
    print("  heights       %.1f .. %.1f  (world z, the stored heights NEGATED: "
          "a greater stored value is LOWER in the world, FINDINGS 25)"
          % (summary["bbox"]["min"][2], summary["bbox"]["max"][2]))
    if terrain_tex is not None and terrain_tex.get("state") == "bound":
        print("  ground        %d materials over %d tiles, every face bound "
              "(one opaque layer, quadrant 0 -- retail blends THREE layers "
              "per cell, T6)"
              % (len(terrain_tex["materials"]),
                 len(terrain_tex["tile_slot"])))
        if terrain_tex["untextured_tiles"]:
            print("                tiles %r have NO decodable texture and "
                  "draw flat magenta rather than impersonating slot 0"
                  % (terrain_tex["untextured_tiles"],))
    elif gwmap.terrain_textures is not None:
        print("  ground        texture block present, NOT applied (%s)"
              % ("--no-terrain-textures" if args.no_terrain_textures
                 else summary["terrain_textures"]["state"]))
    if prop_objs:
        ps = summary["props"]
        print("  props         %d placed: %d REAL meshes sharing %d "
              "datablocks, %d proxies (%d outlined, %d radius)"
              % (ps["count"], ps["real"], ps["real_meshes"], ps["proxy"],
                 ps["outlined"], ps["proxy"] - ps["outlined"]))
        if ps["proxy"]:
            print("                the %d proxies are props whose model does "
                  "not decode; their meshes are NOT ArenaNet geometry"
                  % ps["proxy"])
    elif gwmap.props is not None:
        print("  props         %d in the sidecar, skipped (--no-props)"
              % gwmap.props["count"])

    if args.dump_verts:
        co = [0.0] * (3 * len(obj.data.vertices))
        obj.data.vertices.foreach_get("co", co)
        with open(args.dump_verts, "wb") as fh:
            fh.write(struct.pack("<%df" % len(co), *co))
        print("  vertices      %s (%d x xyz float32)"
              % (args.dump_verts, len(co) // 3))
    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
            fh.write("\n")
        print("  summary       %s" % args.dump)
    if args.out:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.out))
        print("  saved         %s" % os.path.abspath(args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
