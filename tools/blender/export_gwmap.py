"""Take a Blender mesh back OUT to a `rurik.gwmap` terrain interchange.

    blender --background --factory-startup --python-exit-code 66 \
        --python tools/blender/export_gwmap.py -- \
        --blend scene.blend --out <dir> [--name NAME] [--object NAME] \
        [--dump report.json]

The inverse of `import_gwmap.py`, and the half of the pipeline that lets a human
AUTHOR terrain rather than only look at it. `--blend` is optional: without it the
current scene is used, which is what running this from Blender's text editor
does.

`--python-exit-code` is not decoration, for the same MEASURED reason as the
importer: `blender --background --python x.py` exits 0 EVEN WHEN THE SCRIPT
RAISES. Every refusal below only reaches the shell if that flag is passed.

FOUR THINGS ARE UNDONE HERE, and each is a place a silent exporter loses data.
They are listed in the order they bite.

  1. **THE LATTICE IS RE-DERIVED FROM WORLD POSITIONS, NEVER FROM VERTEX ORDER.**
     A terrain chunk is a height field on a REGULAR GRID: the only thing it can
     store per cell is one float. Blender is under no such constraint -- a human
     can drag a vertex sideways, and there is no way to write that down. So the
     grid is rebuilt by clustering the x and y coordinates the mesh actually
     carries, every vertex is checked against the lattice that implies, and a
     displacement over `--xy-tolerance` is REFUSED rather than rounded away.
     Going by `mesh.vertices[k]` instead would have shared its row convention
     with the importer and made the check unable to see the defect it is for --
     the same trap `test_blenderimport.py`'s prop oracle was rewritten to avoid,
     where an upside-down sabotage scored the baseline UNCHANGED because the z
     values had not moved within the buffer, only the vertices owning them had.
     The object's `matrix_world` is applied first, so a moved, scaled or rotated
     object is judged on where its vertices really are; a rotation lands them off
     the lattice and is refused by that same check rather than by a special case.

  2. **THE MANUFACTURED EDGE IS DROPPED, AND WHAT THE DROP COSTS IS REPORTED.**
     The mesh is `(dimX+1)^2` vertices; the file holds `dimX * dimY`. The far
     column and far row are the CLIENT's replication of their neighbours
     (FINDINGS 17.4) and were never stored, so they cannot be stored now.
     Dropping them is correct; dropping them QUIETLY is not, because a value
     that is on screen right now will be different when the map is next read.
     `manufactured_edge_unstorable` counts those, the stderr line names them and
     `--refuse-unstorable-edge` makes it fatal. Note the name is for the EFFECT
     and not the cause: sculpting the far edge lands a vertex on that list, and
     so does sculpting the last REAL column beside it, and in the second case
     the human touched nothing on the edge at all. This is the one lossy step in
     the round trip and it is lossy in the format, not in this file.

  3. **z IS NEGATED BACK.** `stored = -mesh_z`, the inverse of the importer's
     flip. FINDINGS 25: a greater stored value is LOWER in the world, measured by
     two client runs differing in that sign alone. `stored_z()` below is the only
     place this file states it, for the same reason `test_blenderimport.mesh_z`
     is the only place that one does.

  4. **THE NON-GEOMETRY METADATA IS CARRIED, AND CROSS-CHECKED, NOT TRUSTED.**
     Tag 0's fields, the two tile tables and the emitted tag sequence are not
     recoverable from a mesh, so `import_gwmap.py` stamps the whole original
     manifest onto the object as a `gwmap` custom property and this file reads it
     back. What it does NOT do is take `dims`, `map_rect` or `cell_pitch` from
     that stamp: those are re-derived from the geometry, because the geometry is
     what the human edited, and the stamp is then compared against them. A
     disagreement is reported and recorded rather than resolved silently -- an
     exporter that preferred the stamp would emit the map that was IMPORTED no
     matter what was done to it in between, which is the shape of a round trip
     that passes while understanding nothing.

WHAT MAKES THE ROUND TRIP WORTH ITS EXIT CODE. Heights out equal to heights in
proves the pair of scripts are inverses and nothing more -- offline agreement
between two of our own components. Two things carry it past that:
`test_blenderroundtrip.py` compares against the ORIGINAL retail sidecar, which
came out of `Gw.dat` through `terrain.py` and neither script has any say in; and
its section 2 SCULPTS a vertex in Blender and requires exactly that cell to move
by exactly the negated amount, which is what an exporter that re-emitted the
stamped manifest cannot do. Without the sculpt control the identity round trip
is satisfied by a memcpy.

PROPS ROUND-TRIP (2026-08-14). Every prop object in the scene comes back out
as a props sidecar, so placements can be AUTHORED in Blender and not merely
looked at. The rule is the terrain's: GEOMETRY WINS. Position, rotation and
scale are read off `matrix_world`, so moving or turning a prop is what gets
written; the model index, flags and outline ring come from the custom
properties the importer wrote, because a transform cannot hold them and
inventing them would be fiction. The model TABLE -- which maps a prop's index
to an archive file id and that row's (size, crc) -- is carried from the
importer's `gwprops` stamp for the same reason: a file id is ARCHIVE STATE and
a Blender scene has no archive to re-derive one from.

ONE PLACE THE STAMP WINS, and it is because the geometry provably does not
carry the answer: an OUTLINE proxy is imported UNROTATED on purpose (the
compiled ring is `(x + dx, y + dy)`, the client's own add-back with no
rotation term), so deriving a basis from its identity matrix would write an
identity basis over the real one. MEASURED: 31 of Pre-Searing's 864 props took
that path before the branch existed, and every one would have had its
orientation silently flattened.

An EMPTY prop list writes no sidecar at all -- a mesh authored from nothing has
no prop layer, and emitting an empty one would claim a different fact.

WHERE THE OUTPUT MAY GO. An exported height field derived from a retail map is
derived ArenaNet data, and `CLAUDE.md`'s provenance gate keeps it out of the
repo permanently. `toolkit/mapdata/mapexport.py`'s `resolve_outdir()` is the
authority on that rule; Blender's interpreter cannot import it (see below), so
`resolve_outdir()` here reimplements it -- refuse any destination inside a git
working tree unless it is under a `vault` directory. The two are kept honest by
`test_blenderroundtrip.py`, which asserts this one refuses the SAME repo root
`mapexport` refuses.

WHY `bpy` IS ALLOWED IN THIS DIRECTORY. Same as the importer: `CLAUDE.md` pins
`toolkit/` to the standard library so the server and every checker keep working
on a bare machine, and `bpy` exists only inside Blender. Nothing under `toolkit/`
imports this file; the test drives it as a SUBPROCESS, so the two sides of the
round trip share no code at all -- not even the manifest writer, which is a
second implementation of the one in `mapexport.py` on purpose.
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
FORMAT_VERSION = 1
DTYPE_F32 = "float32-le"
DTYPE_U8 = "uint8"

STAMP = "gwmap"
PROPS_STAMP = "gwprops"                 # the object custom property the importer writes

# The pitch every shipped map uses. As in the importer, NOT used to place
# anything -- the pitch is derived from the mesh -- only to say so when the
# answer is not this. A hard-coded 96.0 would make the test's pitch control
# unable to fail.
EXPECTED_PITCH = 96.0

# Two different tolerances, and conflating them is how this would go wrong.
#
# CLUSTER_TOL groups vertices into columns and rows. It is coarse (1 unit
# against a 96-unit pitch) because its only job is deciding which column a
# vertex belongs to; a vertex dragged far enough to leave its column instead
# forms a column of its own, and the `nx * ny == vertex count` check catches
# that. LATTICE_TOL is the accuracy demanded once the lattice is known, and it
# is tight: a vertex nudged half a unit stays in its cluster and is caught here
# and nowhere else. Both bands have to be covered or a displacement in between
# them exports as if it were not there.
CLUSTER_TOL = 1.0
LATTICE_TOL = 0.0625


class NotATerrainMesh(ValueError):
    """The mesh cannot be written down as a height field on a regular grid."""


# ------------------------------------------------------------ the convention

def stored_z(mesh_z):
    """The stored height for a world z. THE ONLY PLACE THIS FILE STATES THE SIGN.

    FINDINGS 25: a greater stored value is LOWER in the world. The importer
    negates on the way in so a human looks at the map the right way up, so the
    way out negates back. Nothing in the archive can refute this -- props and
    terrain share the file's convention, so every prop-based oracle is invariant
    under the flip -- and the warrant is two client runs differing in this sign
    and nothing else.
    """
    return -mesh_z


# --------------------------------------------------------------- the lattice

def cluster(values, tol=CLUSTER_TOL):
    """Sorted distinct coordinates, values within `tol` of each other merged.

    Returns `(centres, assignment)` where `assignment[k]` is the index in
    `centres` of `values[k]`. A cluster's centre is its MEAN, so a column of
    vertices that all drifted equally still yields one column and the drift
    shows up in the pitch rather than being blamed on one vertex.
    """
    order = sorted(range(len(values)), key=lambda k: values[k])
    centres, assignment, group = [], [0] * len(values), []
    for k in order:
        if group and values[k] - values[group[-1]] > tol:
            centres.append(sum(values[g] for g in group) / len(group))
            for g in group:
                assignment[g] = len(centres) - 1
            group = []
        group.append(k)
    if group:
        centres.append(sum(values[g] for g in group) / len(group))
        for g in group:
            assignment[g] = len(centres) - 1
    return centres, assignment


class Lattice(object):
    """The regular grid a mesh's vertices lie on, plus how well they lie on it."""

    def __init__(self, dim_x, dim_y, rect, pitch_x, pitch_y, grid, residual):
        self.dim_x = dim_x
        self.dim_y = dim_y
        self.rect = rect
        self.pitch_x = pitch_x
        self.pitch_y = pitch_y
        self.grid = grid                # (dimY+1) rows of (dimX+1) world z
        self.residual = residual        # worst |actual - ideal| in x or y

    @property
    def pitch(self):
        return self.pitch_x

    def __repr__(self):
        return ("<Lattice %dx%d cells, rect %r, pitch %r/%r, residual %g>"
                % (self.dim_x, self.dim_y, self.rect, self.pitch_x,
                   self.pitch_y, self.residual))


def lattice_from_vertices(verts, cluster_tol=CLUSTER_TOL):
    """`Lattice` from world-space `(x, y, z)` triples. RAISES if it is not one.

    Every refusal here is a thing a terrain chunk genuinely cannot express, and
    each names what the human did rather than what the array looked like.
    """
    if not verts:
        raise NotATerrainMesh("the mesh has no vertices")
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    xc, xi = cluster(xs, cluster_tol)
    yc, yi = cluster(ys, cluster_tol)
    nx, ny = len(xc), len(yc)

    if nx < 2 or ny < 2:
        raise NotATerrainMesh(
            "the vertices form a %d x %d lattice; terrain needs at least 2 x 2"
            % (nx, ny))
    if nx * ny != len(verts):
        raise NotATerrainMesh(
            "%d vertices do not fill a %d x %d lattice (%d cells). Terrain is a "
            "height field on a REGULAR grid: every column must have the same "
            "rows. A vertex dragged out of its column shows up here as an extra "
            "column of one." % (len(verts), nx, ny, nx * ny))

    # j = 0 is world maxY, which is grid row 0 (FINDINGS 17.4 and the
    # interchange's own `grid_row_0`), so the y clusters are walked DESCENDING.
    grid = [[None] * nx for _ in range(ny)]
    for k, (_x, _y, z) in enumerate(verts):
        j = ny - 1 - yi[k]
        i = xi[k]
        if grid[j][i] is not None:
            raise NotATerrainMesh(
                "two vertices occupy lattice cell (%d, %d) at about (%r, %r). "
                "Terrain stores one height per grid corner and cannot hold both."
                % (i, j, xc[i], yc[ny - 1 - j]))
        grid[j][i] = z
    missing = [(i, j) for j in range(ny) for i in range(nx)
               if grid[j][i] is None]
    if missing:
        raise NotATerrainMesh(
            "%d lattice positions have no vertex, the first being (%d, %d). The "
            "mesh is not a complete grid." % (len(missing), missing[0][0],
                                              missing[0][1]))

    x0, x1 = xc[0], xc[-1]
    y0, y1 = yc[0], yc[-1]
    pitch_x = (x1 - x0) / (nx - 1)
    pitch_y = (y1 - y0) / (ny - 1)

    # THE ACCURACY CHECK, and it is separate from the clustering on purpose --
    # see CLUSTER_TOL. Measured against the ideal lattice the pitch implies, so
    # a mesh that is regular but for one nudged vertex is caught even though
    # every vertex landed in the right cluster.
    residual = 0.0
    for k, (x, y, _z) in enumerate(verts):
        residual = max(residual,
                       abs(x - (x0 + xi[k] * pitch_x)),
                       abs(y - (y0 + yi[k] * pitch_y)))
    return Lattice(nx - 1, ny - 1, (x0, y0, x1, y1), pitch_x, pitch_y, grid,
                   residual)


def strip_manufactured_edge(lattice):
    """`(heights, unstorable)` -- the `dimX * dimY` the file holds, world row-major.

    The far column and the far row are the client's replication of their
    neighbours and were never stored (FINDINGS 17.4, and `mapexport.py`'s
    `corner_heights` is the forward direction). `unstorable` lists the positions
    on that edge whose value is NOT the replication, because those are exactly
    the values that will not survive: the next import regenerates them from the
    neighbour, so whatever they hold now is being discarded.

    IT IS NAMED FOR THE EFFECT, NOT THE CAUSE, and the distinction is real.
    There are two ways to land on this list -- sculpting a far-edge vertex, or
    sculpting the LAST REAL column or row so that the edge beside it stops
    matching. The second is not a mistake and the human did nothing to the edge;
    calling either one "edited" would report the wrong thing about it. What both
    share is that a value currently on screen will change when the map is next
    read, and that is what a human needs told.

    Heights come out in the STORED convention -- negated (see `stored_z`) -- so
    that what this returns is what goes in the sidecar.
    """
    dx, dy = lattice.dim_x, lattice.dim_y
    grid = lattice.grid
    unstorable = []
    for j in range(dy + 1):
        if grid[j][dx] != grid[j][dx - 1]:
            unstorable.append((dx, j))
    for i in range(dx + 1):
        if grid[dy][i] != grid[dy - 1][i]:
            unstorable.append((i, dy))
    heights = []
    for j in range(dy):
        for i in range(dx):
            heights.append(stored_z(grid[j][i]))
    return heights, unstorable


# --------------------------------------------------------- where output goes

def resolve_outdir(outdir):
    """The directory an export may be written to. Refuses a git working tree.

    `mapexport.resolve_outdir()` is the authority and this is the same rule for
    an interpreter that cannot import it: derived ArenaNet data never enters the
    repo, `CLAUDE.md` says retrofitting provenance is not possible, and so this
    is a refusal with no flag to turn it off. A `vault` directory is allowed
    because the vault lives inside the repo root in the main checkout and is
    gitignored -- a plain prefix test would refuse the normal destination.

    A git WORKTREE's `.git` is a file rather than a directory, and both count.
    """
    outdir = os.path.abspath(outdir)
    parts = [p.lower() for p in outdir.replace("\\", "/").split("/")]
    if "vault" in parts:
        return outdir
    probe = outdir
    while True:
        if os.path.exists(os.path.join(probe, ".git")):
            raise ValueError(
                "refusing to export into the git working tree at %s\n"
                "  An exported height field can be derived ArenaNet data, and "
                "CLAUDE.md's provenance gate keeps it out of the repo, "
                "permanently.\n"
                "  Write under a vault directory, or to a scratch directory "
                "outside the tree." % probe)
        parent = os.path.dirname(probe)
        if parent == probe:
            return outdir
        probe = parent


# ------------------------------------------------------------- the manifest

def build_manifest(name, lattice, heights, tiles=None, shade=None, stamp=None,
                   disagreements=(), edge_unstorable=(), stamped=None,
                   blend=None, props=None, prop_report=None):
    """The JSON body and the sidecar payloads, with no file touched yet.

    Geometry comes from `lattice`; everything a mesh cannot carry comes from
    `stamp`, which is the manifest `import_gwmap.py` put on the object. The
    stamp NEVER supplies dims, the rect or the pitch -- see the module docstring
    for why that would make the round trip meaningless.
    """
    stamp = dict(stamp or {})
    dim_x, dim_y = lattice.dim_x, lattice.dim_y
    cells = dim_x * dim_y
    x0, y0, x1, y1 = lattice.rect

    payloads = [("heights", "%s.heights.f32" % name, DTYPE_F32,
                 struct.pack("<%df" % cells, *heights), cells)]
    # An EMPTY prop list writes NO sidecar. A mesh authored from nothing has
    # no props, and emitting an empty sidecar for it would claim the scene
    # carried a prop layer that happened to be empty -- a different fact, and
    # one that makes "only a heights sidecar is written" untestable.
    if props:
        # The props sidecar, rebuilt from the OBJECTS. Model identity comes
        # from the stamp's own model table -- a Blender scene has no archive
        # to resolve a file id against, and re-deriving one would be
        # inventing archive state.
        stamp_props = {}
        holder = pick_object(None)
        raw = holder.get(PROPS_STAMP) if holder else None
        if raw:
            try:
                stamp_props = json.loads(raw)
            except ValueError:
                stamp_props = {}
        body = {
            "format": "rurik.gwprops",
            "count": len(props),
            "conventions": stamp_props.get("conventions", {}),
            "models": stamp_props.get("models", []),
            "props": props,
            "refs4": stamp_props.get("refs4", []),
            "refs6": stamp_props.get("refs6"),
        }
        blob = json.dumps(body, indent=2, sort_keys=True).encode("utf-8")
        payloads.append(("props", "%s.props.json" % name, "json", blob,
                         len(props)))
    if tiles is not None:
        payloads.append(("tiles", "%s.tiles.u8" % name, DTYPE_U8,
                         bytes(tiles), cells))
    if shade is not None:
        payloads.append(("shade", "%s.shade.u8" % name, DTYPE_U8,
                         bytes(shade), cells))

    meta = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "name": name,
        "dims": {"x": dim_x, "y": dim_y, "cells": cells},
        "map_rect": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
        "cell_pitch": lattice.pitch_x,
        "tile_size": stamp.get("tile_size", 32),
        "conventions": {
            "sample_position": "cell corners",
            "array_order": "world row-major, index = gy * dimX + gx",
            "grid_row_0": "world maxY; gx = int((wx-x0)/pitch), "
                          "gy = int((y1-wy)/pitch)",
            "height_sign": "as stored, and a GREATER stored value is LOWER in "
                           "the world (FINDINGS 25). A consumer drawing this "
                           "for a human must negate z.",
            "stored_samples": "dimX * dimY; a mesh has (dimX+1)*(dimY+1) "
                              "vertices, the extra column and row being "
                              "replicated by the client",
            "extent": "dims * pitch, which equals the map_rect span",
        },
        # WHERE THIS ONE CAME FROM, which an export out of Blender has to say
        # and an export out of the archive does not: a human may have changed
        # any of it.
        "authored": {
            "tool": "tools/blender/export_gwmap.py",
            "blender": bpy.app.version_string if bpy is not None else None,
            "from_blend": os.path.abspath(blend) if blend else None,
            "lattice_residual": lattice.residual,
            "pitch_y": lattice.pitch_y,
            "manufactured_edge_unstorable": len(edge_unstorable),
            "manufactured_edge_positions": [list(p) for p in
                                            edge_unstorable[:32]],
            "stamp_disagreements": list(disagreements),
            # PASSED IN, not `bool(stamp)`. The first version derived it from
            # the dict here, and the caller had already added the .blend path to
            # that dict -- so a mesh authored from nothing, whose whole point is
            # that it carries no manifest, reported `stamped: true`.
            "stamped": bool(stamp) if stamped is None else bool(stamped),
        },
        "sidecars": [
            {"kind": kind, "name": fname, "dtype": dtype, "count": count,
             "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
            for kind, fname, dtype, blob, count in payloads
        ],
    }
    # Carried verbatim when the stamp has them: none is recoverable from a mesh,
    # and inventing a default would be a value nothing measured supports.
    for key in ("source", "terrain_tag0", "tile_table_a", "tile_table_b",
                "tag_sequence", "terrain_tag3b"):
        if key in stamp:
            meta[key] = stamp[key]
    return meta, [(fname, blob) for _k, fname, _d, blob, _c in payloads]


def write_export(meta, payloads, outdir):
    """Write a built manifest and its sidecars. Returns the JSON path."""
    outdir = resolve_outdir(outdir)
    if not os.path.isdir(outdir):
        os.makedirs(outdir)
    for fname, blob in payloads:
        with open(os.path.join(outdir, fname), "wb") as fh:
            fh.write(blob)
    json_path = os.path.join(outdir, "%s.gwmap.json" % meta["name"])
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
        fh.write("\n")
    return json_path


# ----------------------------------------------------------------- Blender

def world_vertices(obj):
    """Every vertex as a world-space `(x, y, z)` triple.

    `matrix_world` is APPLIED, unless it is the identity. A human who moved or
    scaled the object meant it, and reading local coordinates would export a
    mesh nobody is looking at. A ROTATED object lands off the lattice and is
    refused by `lattice_from_vertices`, which is the right refusal and needs no
    special case here.

    THE IDENTITY IS SKIPPED RATHER THAN APPLIED, and it is not a speed tweak.
    MEASURED 2026-08-12: multiplying by the identity matrix is not a bitwise
    no-op on SIGNED ZERO. A stored height of `0.0` reaches Blender as `-0.0`
    (the importer negates), survives `from_pydata` and survives the .blend --
    both checked directly -- and then `-0.0 * 1.0 + 0.0` evaluates to `+0.0`,
    because IEEE addition of the two zeroes gives the positive one. Negating
    back therefore produced `-0.0`, and one cell of a 6,144-cell round trip came
    back `00000080` where ArenaNet's byte was `00000000`. Numerically identical,
    bytewise not -- which is exactly the class of difference a tolerance would
    have hidden and a digest would have reported as a mystery. Skipping the
    transform when there is no transform makes the common path exact; a genuinely
    moved object still loses the sign of zero, and that is stated where the round
    trip is claimed rather than left to be rediscovered.
    """
    mesh = obj.data
    n = len(mesh.vertices)
    co = [0.0] * (3 * n)
    mesh.vertices.foreach_get("co", co)
    if _is_identity(obj.matrix_world):
        return [(co[3 * k], co[3 * k + 1], co[3 * k + 2]) for k in range(n)]
    m = obj.matrix_world
    out = []
    for k in range(n):
        v = m @ _Vector((co[3 * k], co[3 * k + 1], co[3 * k + 2]))
        out.append((v[0], v[1], v[2]))
    return out


def _is_identity(matrix):
    from mathutils import Matrix
    return matrix == Matrix.Identity(4)


def _Vector(triple):
    from mathutils import Vector
    return Vector(triple)


def face_cells(obj, lattice):
    """`{(gx, gy): polygon index}` -- which cell each face covers.

    BY POSITION, like everything else here: a face's cell is the one at its
    minimum x and maximum y, which is the corner the importer wound it from.
    Face ORDER is not trusted, because a human who deleted and rebuilt a face
    changed it and the tile attribute would then be read into the wrong cell.

    WHAT THIS IS NOT EXACT ABOUT, stated rather than left to be discovered. The
    export defines terrain by the VERTEX LATTICE, so face topology is not
    constrained: a triangulated grid exports the same height field, correctly,
    because the client builds its own quads. But two triangles covering one cell
    collapse to one entry here and the last one wins, so a per-face attribute
    read off a triangulated mesh takes an arbitrary half of each cell. Nothing
    geometric depends on it -- `terrain.py` labels the MEANING of both tile
    indices and shade bytes NOT FOUND, and carrying them is transport -- but the
    arbitrariness is real, and a mesh whose faces do not cover every cell makes
    `read_cell_attribute` return None rather than a half-filled array.
    """
    mesh = obj.data
    m = obj.matrix_world
    x0, _y0, _x1, y1 = lattice.rect
    out = {}
    for poly in mesh.polygons:
        xs, ys = [], []
        for vi in poly.vertices:
            v = m @ mesh.vertices[vi].co
            xs.append(v[0])
            ys.append(v[1])
        gx = int(round((min(xs) - x0) / lattice.pitch_x))
        gy = int(round((y1 - max(ys)) / lattice.pitch_y))
        out[(gx, gy)] = poly.index
    return out


def read_cell_attribute(obj, lattice, name):
    """A per-face INT attribute back as `dimX*dimY` bytes, world row-major.

    Returns None when the mesh does not carry it -- a mesh authored from nothing
    has no tile indices and the interchange's sidecars are optional, so an
    absent attribute is a fact rather than a failure.
    """
    mesh = obj.data
    attr = mesh.attributes.get(name)
    if attr is None or attr.domain != "FACE":
        return None
    values = [0] * len(mesh.polygons)
    attr.data.foreach_get("value", values)
    cells = face_cells(obj, lattice)
    dx, dy = lattice.dim_x, lattice.dim_y
    out = bytearray(dx * dy)
    for gy in range(dy):
        for gx in range(dx):
            idx = cells.get((gx, gy))
            if idx is None:
                return None                 # incomplete; say nothing rather than half
            out[gy * dx + gx] = values[idx] & 0xFF
    return bytes(out)


def read_stamp(obj):
    """The manifest `import_gwmap.py` left on the object, or `{}`.

    A mesh built in Blender from nothing has no stamp, and that is a supported
    case -- it is the whole authoring direction. What it costs is the metadata a
    mesh cannot carry, and `build_manifest` simply omits what it does not have
    rather than inventing it.
    """
    raw = obj.get(STAMP)
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        sys.stderr.write("[warn] the %r custom property on %s is not JSON; "
                         "treating the mesh as unstamped.\n" % (STAMP, obj.name))
        return {}


def check_stamp(stamp, lattice):
    """Geometry facts in the stamp against the geometry. A list of disagreements.

    NOT resolved -- reported. The mesh wins because the mesh is what was edited;
    an exporter that took `dims`, the rect or the pitch from the stamp would
    emit the map that was imported however it had been changed since, and every
    round trip would pass while the tool understood nothing.
    """
    out = []
    if not stamp:
        return out
    dims = stamp.get("dims") or {}
    if dims and (dims.get("x"), dims.get("y")) != (lattice.dim_x, lattice.dim_y):
        out.append("dims: the stamp says %rx%r, the mesh is %dx%d"
                   % (dims.get("x"), dims.get("y"), lattice.dim_x,
                      lattice.dim_y))
    r = stamp.get("map_rect") or {}
    if r:
        was = (r.get("x0"), r.get("y0"), r.get("x1"), r.get("y1"))
        if was != lattice.rect:
            out.append("map_rect: the stamp says %r, the mesh spans %r"
                       % (was, lattice.rect))
    if "cell_pitch" in stamp and stamp["cell_pitch"] != lattice.pitch_x:
        out.append("cell_pitch: the stamp says %r, the mesh measures %r"
                   % (stamp["cell_pitch"], lattice.pitch_x))
    return out


def pick_object(name=None):
    """The mesh to export. Named, or the only one there is."""
    if bpy is None:                                          # pragma: no cover
        raise RuntimeError(
            "bpy is not importable, so this is not Blender's interpreter. Run "
            "it as:  blender --background --python %s -- --out <dir>"
            % os.path.abspath(__file__))
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if name is not None:
        for obj in meshes:
            if obj.name == name:
                return obj
        raise ValueError("no mesh object named %r; the scene has %r"
                         % (name, [o.name for o in meshes]))
    if not meshes:
        raise ValueError("the scene holds no mesh object")
    if len(meshes) > 1:
        # A props-carrying import (2026-08-13) legitimately fills the scene
        # with proxy objects, so a crowd is no longer proof of ambiguity. The
        # terrain is picked by IDENTITY -- the importer's stamp, which proxies
        # never carry -- and only an actual tie (or no stamp at all) refuses.
        # Never by position in a list: that is how the wrong client got
        # launched on 2026-08-06, and a duplicated terrain copies its stamp,
        # so the duplicate case still refuses.
        stamped = [o for o in meshes if o.get(STAMP) is not None]
        if len(stamped) == 1:
            return stamped[0]
        raise ValueError(
            "the scene holds %d mesh objects and %d carry the %r stamp, so "
            "no single terrain can be picked. Pass --object; picking one by "
            "position in a list is how the wrong client got launched on "
            "2026-08-06." % (len(meshes), len(stamped), STAMP))
    return meshes[0]


def game_basis(matrix):
    """The compiler's `(basis_a, basis_b)` back out of a Blender rotation.

    The exact inverse of `import_gwmap.basis_matrix_blender`, and it has to
    be: that function conjugates the game rotation through the z-mirror
    `M = diag(1, 1, -1)` as `B = M R M`, and `M` is its own inverse, so
    `R = M B M` -- the same sign flip applied again. R's columns are
    `(b x -a, b, -a)`, so `b` is column 1 and `a` is the NEGATED column 2.

    `matrix` is the object's 3x3 with scale divided out; a matrix that still
    carries scale gives basis vectors of the wrong length and the identity
    the client compiles from would not hold.
    """
    r = [[matrix[i][j] for j in range(3)] for i in range(3)]
    for i in range(3):
        for j in range(3):
            if (i == 2) != (j == 2):
                r[i][j] = -r[i][j]
    b = (r[0][1], r[1][1], r[2][1])
    a = (-r[0][2], -r[1][2], -r[2][2])
    return [list(a), list(b)]


def read_prop_objects(name=None):
    """Every prop object in the scene, as props-sidecar records.

    Geometry wins over the stamp, exactly as it does for terrain: the
    POSITION, ROTATION and SCALE come from `matrix_world`, so moving or
    turning a prop in Blender is what the export carries. Everything a
    transform cannot hold -- the model index, the flags, the outline ring --
    comes from the custom properties the importer wrote, because inventing
    them would be writing fiction.

    Returns `(records, report)`. `report` names the props whose derived
    transform DISAGREES with the carried stamp, which is how a rotated prop
    announces itself rather than slipping through.
    """
    import mathutils                                   # noqa: F401

    objs = [o for o in bpy.data.objects
            if o.type == "MESH" and "gw_model" in o.keys()]
    objs.sort(key=lambda o: o.get("gw_index", 0))
    records, moved, rotated = [], [], []
    for obj in objs:
        mw = obj.matrix_world
        loc = mw.translation
        # Scale is the length of a rotation column; the importer wrote
        # basis * s, so every column carries it.
        cols = [(mw[0][c], mw[1][c], mw[2][c]) for c in range(3)]
        lengths = [math.sqrt(sum(v * v for v in col)) for col in cols]
        scale = sum(lengths) / 3.0
        if scale <= 0:
            raise NotATerrainMesh(
                "prop %r has a zero or negative scale, which no prop record "
                "can express" % obj.name)
        pure = [[mw[i][j] / lengths[j] for j in range(3)] for i in range(3)]
        stamp_basis = list(obj.get("gw_basis") or [])

        # AN OUTLINE PROXY CARRIES NO ROTATION, BY DESIGN. `import_gwmap.py`
        # leaves those objects unrotated because the compiled ring is
        # literally `(x + dx, y + dy)` -- the client's own add-back with no
        # rotation term -- so rotating the proxy would move measured points
        # to invented ones. Deriving a basis from that identity matrix would
        # therefore write an IDENTITY basis over the real one and silently
        # flatten every outlined prop's orientation. MEASURED: 31 of
        # Pre-Searing's 864 props took that path before this branch existed.
        # For them the stamp is the only witness, so the stamp wins -- the
        # one place in this file where it does, and it is because the
        # geometry provably does not carry the answer.
        if obj.get("gw_proxy") == "outline" and stamp_basis:
            basis = [list(stamp_basis[0:3]), list(stamp_basis[3:6])]
        else:
            basis = game_basis(pure)
            if stamp_basis:
                flat = [c for v in basis for c in v]
                if any(abs(x - y) > 1e-4 for x, y in zip(flat, stamp_basis)):
                    rotated.append(obj.name)
        outline = list(obj.get("gw_outline") or [])
        record = {
            "model": int(obj["gw_model"]),
            "position": [loc.x, loc.y, -loc.z],
            "basis": basis,
            "scale": scale,
            "rot_bytes": list(obj.get("gw_rot_bytes") or [0, 0, 0]),
            "scale_byte": int(obj.get("gw_scale_byte", 0x7F)),
            "radius": float(obj.get("gw_radius", 0.0)),
            "flags": int(obj.get("gw_flags", 0)),
            "outline": [[outline[i], outline[i + 1]]
                        for i in range(0, len(outline) - 1, 2)],
        }
        records.append(record)
    return records, {"count": len(records), "rotated": rotated,
                     "moved": moved}


def export_gwmap(outdir, name=None, obj_name=None, blend=None,
                 xy_tolerance=LATTICE_TOL, refuse_unstorable_edge=False,
                 tiles=True, shade=True, props=True):
    """Read the scene's terrain mesh and write an interchange. `(path, report)`."""
    if bpy is None:                                          # pragma: no cover
        raise RuntimeError("this is not Blender's interpreter")
    if blend:
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(blend))

    obj = pick_object(obj_name)
    verts = world_vertices(obj)
    lattice = lattice_from_vertices(verts)

    if lattice.residual > xy_tolerance:
        raise NotATerrainMesh(
            "a vertex is %g world units off the regular lattice (tolerance "
            "%g). Terrain stores ONE HEIGHT PER GRID CORNER and has nowhere to "
            "put a sideways displacement, so exporting this would silently "
            "discard it. Move the vertex back in x and y, or raise "
            "--xy-tolerance if the drift is numerical."
            % (lattice.residual, xy_tolerance))
    if lattice.pitch_x != lattice.pitch_y:
        sys.stderr.write(
            "[warn] the mesh's x pitch is %r and its y pitch is %r. A terrain "
            "chunk has one pitch; the x pitch is what will be written.\n"
            % (lattice.pitch_x, lattice.pitch_y))
    if lattice.pitch_x != EXPECTED_PITCH:
        sys.stderr.write(
            "[warn] the mesh's cell pitch is %r, not the measured %r. Every "
            "shipped map uses %r and the client's Stripped path gates on it "
            "exactly.\n" % (lattice.pitch_x, EXPECTED_PITCH, EXPECTED_PITCH))

    heights, edge_unstorable = strip_manufactured_edge(lattice)
    if edge_unstorable:
        msg = ("[warn] %d vertices on the manufactured far edge hold a value "
               "that CANNOT be stored and will change when this map is next "
               "read: the file holds %d x %d samples and the client makes the "
               "extra column and row by replicating their neighbours (FINDINGS "
               "17.4). Either the edge itself was sculpted, or the last real "
               "column or row beside it was. First: %r\n"
               % (len(edge_unstorable), lattice.dim_x, lattice.dim_y,
                  edge_unstorable[:6]))
        sys.stderr.write(msg)
        if refuse_unstorable_edge:
            raise NotATerrainMesh(msg.strip())

    stamp = read_stamp(obj)
    stamped = bool(stamp)
    disagreements = check_stamp(stamp, lattice)
    for line in disagreements:
        sys.stderr.write("[warn] the mesh disagrees with its stamp -- %s. The "
                         "MESH is what gets written.\n" % line)

    name = name or stamp.get("name") or obj.name
    tile_bytes = read_cell_attribute(obj, lattice, "gw_tile") if tiles else None
    shade_bytes = read_cell_attribute(obj, lattice, "gw_shade") if shade else None
    prop_records, prop_report = ([], None)
    if props:
        prop_records, prop_report = read_prop_objects()
        if prop_report["rotated"]:
            sys.stderr.write(
                "[warn] %d prop(s) carry a rotation that differs from the one "
                "they were imported with; the OBJECT is what gets written. "
                "First: %r\n" % (len(prop_report["rotated"]),
                                 prop_report["rotated"][:4]))
    meta, payloads = build_manifest(name, lattice, heights, tiles=tile_bytes,
                                    shade=shade_bytes, stamp=stamp,
                                    disagreements=disagreements,
                                    edge_unstorable=edge_unstorable,
                                    stamped=stamped, blend=blend,
                                    props=prop_records if props else None,
                                    prop_report=prop_report)
    path = write_export(meta, payloads, outdir)
    return path, meta


# ------------------------------------------------------------------ the CLI

def _script_argv(argv=None):
    """The arguments after `--`, which is how Blender hands a script its own."""
    argv = list(sys.argv[1:] if argv is None else argv)
    return argv[argv.index("--") + 1:] if "--" in argv else argv


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="export_gwmap.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True,
                    help="destination directory (a git working tree is refused)")
    ap.add_argument("--blend", default=None,
                    help="open this .blend first; default is the current scene")
    ap.add_argument("--object", default=None, dest="obj",
                    help="name of the mesh to export (required if several)")
    ap.add_argument("--name", default=None,
                    help="basename for the interchange files")
    ap.add_argument("--dump", default=None,
                    help="write the manifest here as well, for a checker")
    ap.add_argument("--xy-tolerance", type=float, default=LATTICE_TOL,
                    help="how far a vertex may sit off the regular lattice "
                         "(default %g world units against a %g pitch)"
                         % (LATTICE_TOL, EXPECTED_PITCH))
    ap.add_argument("--refuse-unstorable-edge", action="store_true",
                    help="fail rather than warn when a manufactured far-edge "
                         "vertex holds a value the file cannot keep")
    ap.add_argument("--no-tiles", action="store_true")
    ap.add_argument("--no-shade", action="store_true")
    args = ap.parse_args(_script_argv(argv))

    path, meta = export_gwmap(
        args.out, name=args.name, obj_name=args.obj, blend=args.blend,
        xy_tolerance=args.xy_tolerance,
        refuse_unstorable_edge=args.refuse_unstorable_edge,
        tiles=not args.no_tiles, shade=not args.no_shade)

    a = meta["authored"]
    d = meta["dims"]
    print("wrote %s" % path)
    print("  grid          %d x %d cells (%d stored samples)"
          % (d["x"], d["y"], d["cells"]))
    print("  mesh          %d x %d vertices -- the far column and row are the "
          "client's and were dropped" % (d["x"] + 1, d["y"] + 1))
    print("  rect          %r" % (meta["map_rect"],))
    print("  pitch         %r (y %r)" % (meta["cell_pitch"], a["pitch_y"]))
    print("  lattice       worst vertex %g off the grid" % a["lattice_residual"])
    print("  far edge      %d vertex value(s) cannot be stored"
          % a["manufactured_edge_unstorable"])
    print("  stamp         %s%s"
          % ("carried" if a["stamped"] else "ABSENT (authored from nothing)",
             ", %d disagreement(s)" % len(a["stamp_disagreements"])
             if a["stamp_disagreements"] else ""))
    print("  sidecars      %s" % ", ".join(s["name"] for s in meta["sidecars"]))
    print("  heights       written in the STORED convention -- a greater value "
          "is LOWER in the world (FINDINGS 25)")

    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as fh:
            json.dump(meta, fh, indent=2)
            fh.write("\n")
        print("  manifest      %s" % args.dump)
    return 0


if __name__ == "__main__":
    sys.exit(main())
