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
  4. **z is the stored float, unchanged -- WHICH MEANS THIS MESH IS UPSIDE DOWN
     relative to what a player sees.** MEASURED 2026-08-11 (FINDINGS 25): two
     client runs differing only in the sign of one height showed that a GREATER
     stored value is LOWER in the world. A courtyard authored floor -13 /
     surround +600 was drawn as a mesa; the same map at surround -626 was drawn
     as a walled enclosure. GuildWarsMapBrowser negates every height and is
     right to; FINDINGS 16-P5's filing of that as "ITS convention" is corrected.
     The load path still applies no transform -- tag 1 reaches the client's
     buffers through `memcpy` -- but that is a fact about bytes, not about which
     way is up.
     **Nothing here is changed yet, deliberately.** `test_blenderimport.py`'s
     orientation oracle compares Blender's own vertex z against prop z from
     chunk `0x20000004`, and props are stored in the SAME convention as terrain,
     so negating one and not the other would break an oracle that is currently
     correct. Flipping this needs both sides moved together and the test's
     0.7338 re-measured; it is PLAN.md 8 item 10(f). Until then, read a map
     imported here as a height FIELD, not as a picture.

WHAT THIS FILE IS NOT. It is not an authoring round-trip: nothing here writes to
`Gw.dat`, and the mesh it builds is `(dims+1)^2` vertices, which is one column
and one row MORE than a terrain chunk can store. Anything going the other way
has to drop the manufactured edge, not store it.

The tile indices (`.tiles.u8`) and shade bytes (`.shade.u8`) are loaded when
present and attached as mesh attributes, but their MEANING is unsettled upstream
of here (`terrain.py` labels both NOT FOUND); carrying them is transport, not
understanding, and no geometry depends on them.
"""

import argparse
import hashlib
import json
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

# The pitch the interchange is expected to carry. Not used to place a vertex --
# see convention 1 -- only to say so when a file disagrees with the measurement.
EXPECTED_PITCH = 96.0


# ------------------------------------------------------- the interchange
class GwMap(object):
    """One `rurik.gwmap` export, read from disk. Arrays are world row-major.

    `heights[gy * dim_x + gx]`, grid row 0 at world maxY. `tiles` and `shade`
    are None when the export did not carry them.
    """

    def __init__(self, meta, path, heights, tiles=None, shade=None):
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
    if meta.get("format_version") != FORMAT_VERSION:
        raise ValueError("%s: format_version is %r, not %d"
                         % (json_path, meta.get("format_version"),
                            FORMAT_VERSION))

    cells = meta["dims"]["x"] * meta["dims"]["y"]
    if meta["dims"].get("cells", cells) != cells:
        raise ValueError("%s: dims say %d x %d but cells say %d"
                         % (json_path, meta["dims"]["x"], meta["dims"]["y"],
                            meta["dims"]["cells"]))

    arrays = {}
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
        if side["count"] != cells:
            raise ValueError("%s: %d values for a %d-cell grid"
                             % (side["name"], side["count"], cells))
        with open(path, "rb") as fh:
            blob = fh.read()
        if side["dtype"] == DTYPE_F32:
            arrays[side["kind"]] = list(struct.unpack("<%df" % cells, blob))
        elif side["dtype"] == DTYPE_U8:
            arrays[side["kind"]] = blob
        else:
            raise ValueError("%s: unknown dtype %r"
                             % (side["name"], side["dtype"]))

    if "heights" not in arrays:
        raise ValueError("%s: no heights sidecar" % json_path)
    return GwMap(meta, json_path, arrays["heights"],
                 tiles=arrays.get("tiles"), shade=arrays.get("shade"))


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
            verts[row + i] = (x0 + i * pitch, wy, z[row + i])

    faces = [None] * (dx * dy)
    for j in range(dy):
        a = j * stride
        b = a + stride
        out = j * dx
        for i in range(dx):
            faces[out + i] = (a + i, b + i, b + i + 1, a + i + 1)
    return verts, faces


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
    return obj, gwmap


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
    args = ap.parse_args(_script_argv(argv))

    obj, gwmap = import_gwmap(args.json, name=args.name, clear=args.clear)
    summary = mesh_summary(obj, gwmap)

    print("imported %s" % gwmap)
    print("  mesh          %d vertices, %d quads (%d x %d cells)"
          % (summary["vertex_count"], summary["face_count"],
             gwmap.dim_x, gwmap.dim_y))
    print("  bbox min      %r" % (summary["bbox"]["min"],))
    print("  bbox max      %r" % (summary["bbox"]["max"],))
    print("  rect          %r   pitch %r" % (list(gwmap.rect), gwmap.pitch))
    print("  heights       %.1f .. %.1f  (AS STORED -- greater is LOWER in the "
          "world, so this mesh is upside down: FINDINGS 25)"
          % (summary["bbox"]["min"][2], summary["bbox"]["max"][2]))

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
