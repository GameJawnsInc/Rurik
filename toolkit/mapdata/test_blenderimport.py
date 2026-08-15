"""Drive Blender headless on a terrain interchange and check the MESH it built.

    python toolkit/mapdata/test_blenderimport.py
    python toolkit/mapdata/test_blenderimport.py --blender "C:\\...\\blender.exe"

WHAT THIS FILE IS AND IS NOT ALLOWED TO IMPORT. `tools/blender/import_gwmap.py`
imports `bpy`, which is not stdlib and exists only inside Blender's own
interpreter, so `CLAUDE.md`'s stdlib rule keeps it out of `toolkit/`. This test
lives under `toolkit/`, is stdlib-only, and NEVER imports the importer -- it runs
Blender as a subprocess and has Blender dump what it built as JSON and as a raw
float32 vertex buffer. The two sides of the check therefore share no code at all.

THE TWO ORACLES, in order of how much they can refute.

  1. **The props chunk, `0x20000004`, against the built mesh** (section 3). Every
     prop carries a world `(x, y, z)`. Read Blender's vertex buffer back and look
     up the vertex at each prop's cell corner **by the world coordinates Blender
     stored**, not by a lattice index, then compare with the prop's `z`. The
     chunk is read HERE by this file's own walker; the TERRAIN path -- the
     height arrays through `mapexport.py` and the mesh through
     `import_gwmap.py` -- never touches it (since 2026-08-13 both tools handle
     props as a separate sidecar/collection, which shares nothing with the
     height path), so a flipped row order, a wrong pitch or a lost
     de-tiling all move the mesh away from the props standing on it.

     Looking up by position rather than by index is not a detail. The first
     version of this file indexed the buffer as `(gy*(dimX+1) + gx)*3 + 2`, which
     shares its row convention with the code under test, and a sabotage that
     built the whole map upside down (`y0 + j*pitch` for `y1 - j*pitch`) scored
     the baseline UNCHANGED -- the z values had not moved within the buffer, only
     the vertices they belonged to had. Four other checks caught that sabotage,
     but the oracle did not, and an oracle that cannot see the defect it is
     named for is decoration.

     WHAT THIS ORACLE CANNOT SEE, MEASURED 2026-08-11 rather than assumed, so
     that 0.7338 is not read as more than it is. It resolves gross LAYOUT, not
     REGISTRATION. Shifting Pre-Searing's whole height field by one cell and
     re-scoring gives 0.7477 (+1 in x), 0.6806 (-1 in x), 0.7292 (+1 in y) and
     0.6944 (-1 in y) against the baseline's 0.7338 -- a one-cell error is
     inside the spread, and +1 in x scores HIGHER than the truth. Terrain is
     smooth at a 96-unit pitch, so no prop-based oracle can pin the lattice to
     one cell and none should be quoted as doing it. What pins the registration
     instead is the `(dims+1)` span against the Map Parameters rect (a different
     chunk again), the client's own `x0 + 96*i` with no half-cell term
     (FINDINGS 17.4, SOURCE-CODE), and the per-axis digests over every vertex.
     The flips and the de-tiling are what the prop oracle is for, and there it
     is decisive: 9.5x and 5.3x.

     PREDICTION, STATED BEFORE THE MEASUREMENT: the mesh's score must be
     IDENTICAL to `test_mapexport.py` section 5's baseline for the same map --
     0.7338 within 100 units, median |dz| 29.97 -- because vertex `(i, j)` for
     `i < dimX, j < dimY` carries cell `(i, j)`'s height and nothing else. Not
     "close to": equal. A mesh that merely correlates would mean the lattice has
     picked up an offset somewhere, and that is worth failing over.

  2. **The Map Parameters chunk, `0x2000000C`, against the mesh's bounding box**
     (sections 1 and 3). The mesh must span the world rect EXACTLY -- which is
     the whole reason the far column and far row are manufactured. It is a real
     cross-chunk check but it is weaker than it looks, and the file says so
     rather than letting a reader over-trust it: a mesh whose rows run
     bottom-to-top has the SAME bounding box. That is measured here as a
     sabotage, and it is why oracle 1 exists.

  3. Below both, the interchange itself: every vertex coordinate, as a sha256
     over the packed float32 of each axis, against the lattice this file
     computes from `mapexport.load_export`. That is our code against our code and
     proves only that the mesh realises the file it was given -- it is here
     because it covers all 213,921 vertices rather than the handful a printout
     has room for, not because it establishes anything about ArenaNet's layout.

THREE NEGATIVE CONTROLS, in section 2, each fed to the SAME importer:

    changed cell pitch      the bounding box must stop matching the rect
    reversed row order      the z digest and the corner heights must change
    corrupted heights       the import must FAIL and write no dump

The pitch control is the one the brief asks for and it is also why
`import_gwmap.py` reads the pitch out of the interchange instead of hard-coding
the measured 96.0: a hard-coded constant would make this control unable to fail,
and a check that cannot fail is not a check. The importer cross-checks instead
(`extent_matches_rect`).

NO BLENDER, NO RUN. If Blender cannot be found the whole file skips loudly and
goes RED, the same way `toolkit/harness/test_keytap.py` behaves off Windows: a
run that measured nothing has not passed. Point it at another install with
`RURIK_BLENDER` or `--blender` -- and an explicit path that does not exist is
REFUSED rather than fallen through to the default install, which is section 0
and is there because the first version fell through and a run that asked for one
Blender silently measured another and printed ALL CHECKS PASSED.

SECTIONS 0 TO 2b NEED NO VAULT and build their fixture from nothing --
including section 2b's textured ground, whose three tiles ride synthetic ATEX
rows behind a fake archive and whose third tile deliberately resolves to
nothing, so the untextured path (its OWN named slot, never a silent fall
through to slot 0) is exercised on a bare machine. Sections 3-5 need
`vault/dat_study/Gw.dat`, declare a skip naming the path when it is absent,
and the floor then fails the run -- because the synthetic half cannot refute
anything about ArenaNet's bytes.

SECTION 5 IS RUNG T5, and its criterion is against the SIDECAR rather than
the importer's own loop: every tile's slot material must be the image the
manifest names for that tile byte, and every FACE's material index --
recomputed here from tiles.u8 through the dump's slot table -- must
sha256-match what Blender read back off its own built polygons. All 212,992
Pre-Searing faces, not a sample; `--no-terrain-textures` is the control.
"""

import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, file_id_table  # noqa: E402
from terrain import CELL_PITCH  # noqa: E402
from mapexport import (build_manifest, build_terrain_textures,  # noqa: E402
                       export_row, load_export, write_export)
from mapfile import MapFile  # noqa: E402
# The prop oracle's chunk walk, its pinned populations and its measured
# fractions live in `test_mapexport.py` and are imported rather than copied. One
# copy of a measured constant is the point: if that file's oracle is ever
# re-measured, the prediction below moves with it instead of quietly disagreeing.
from test_mapexport import (ORACLE, PROPS_CHUNK, PRESEARING_DIMS,  # noqa: E402
                            PRESEARING_FILE_ID, PRESEARING_PROPS,
                            PRESEARING_RECT, PRESEARING_ROW, PROPS_VERSION,
                            read_chunks, read_props, synthetic_terrain,
                            SYN_X, SYN_Y, _synth_pair, _TexArchive, _tex_deps)
import atex  # noqa: E402
from mapexport import build_props  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
IMPORTER = os.path.join(REPO_ROOT, "tools", "blender", "import_gwmap.py")

BLENDER_ENV = "RURIK_BLENDER"
# The install this rung was measured on. Tried only after the environment
# variable, and `shutil.which` is tried after both, so a machine that keeps
# Blender anywhere else still runs.
KNOWN_BLENDER = r"C:\Program Files\Blender Foundation\Blender 5.1\blender.exe"
MEASURED_BLENDER = "5.1.1"

# MEASURED 2026-08-13: how many of Pre-Searing's 864 props carry an outline
# viable as a footprint prism (>= 3 distinct points after dropping the closing
# repeat). All 34 outlines qualify, so outlined proxies == props with outlines.
PRESEARING_OUTLINED = 34

#: Rung M4, RE-MEASURED after rung M6 landed the client's computed preamble
#: walk. **The proxy population is now ZERO**: every one of Pre-Searing's 864
#: props gets ArenaNet's real mesh, over 229 datablocks. It was 664/200/152 --
#: the 200 proxies were props whose model the retired brute-force search
#: could not read, and all 77 of those models decode now.
#:
#: The proxy PATH is still exercised, by section 3's `--proxies-only` run and
#: by the synthetic sections; what is gone is any prop that NEEDS it here. A
#: model that fails to decode still falls back, and the check below that
#: `real + proxy == count` is what keeps that honest.
PRESEARING_REAL = 864
PRESEARING_PROXY = 0
PRESEARING_MODELS = 229

#: The z-sign claim: prop geometry must reach ABOVE the terrain under it.
#: MEASURED over both reference maps at 0.735 (Kamadan) and 0.743
#: (Pre-Searing) mean vertex fraction; the object-level figure this file
#: scores is higher because one vertex above ground is enough. The floor is
#: set well under the measurement and the CONTROL (the opposite sign) is what
#: carries the claim -- it scored 0.257 and 0.143 on the same props.
Z_SIGN_MIN = 0.85

# MEASURED 2026-08-11: the mesh oracle must reproduce test_mapexport section 5's
# baseline for Pre-Searing exactly, because the vertex lattice carries the cell
# grid unchanged for i < dimX, j < dimY. Not a tolerance -- a prediction.
MESH_ORACLE_LAYOUT = "baseline"
MESH_CONTROLS = ("y-flip", "x-flip")
FRAC_TOL = 0.005
MIN_RATIO = 2.0

BLENDER_TIMEOUT = 300

# MEASURED, and it is a trap worth naming: `blender --background --python x.py`
# exits 0 EVEN WHEN THE SCRIPT RAISES. Blender 5.1.1 prints the traceback and
# returns success, so a pipeline that trusts the exit code reads a refused import
# as a completed one. `--python-exit-code N` is what makes the failure reach the
# shell, and section 2's digest control asserts this exact value rather than
# "non-zero" -- the first version of that check asserted `rc != 0` and went red
# against a working importer, which is how the flag was found.
PYTHON_EXIT_CODE = 66

# FLOOR: 84, from a real green run on `vault/dat_study/Gw.dat` with Blender
# 5.1.1, 2026-08-13 (17.6 s). Sections 0-2 alone score 45 -- MEASURED by
# running with `--dat` pointed at nothing, not counted by eye -- so a run with no
# archive lands 39 short and goes RED. That is deliberate: a
# mesh built from a grid this file invented has verified the plumbing and
# NOTHING about ArenaNet's layout, and a green exit code there would be
# `test_codec.py`'s silent-success failure again.
#
# It was 69 until section 0 landed. Section 0 is five checks on the install
# SELECTOR rather than on a mesh, and it exists because the selector silently
# fell through a bad `--blender` to the known install: a run that asked for one
# Blender measured another and printed ALL CHECKS PASSED (69 checks).
#
# 74 -> 75 on 2026-08-12, when the mesh was flipped the right way up (FINDINGS
# 25) and `mesh_z` became the one place stating the sign. The added check is the
# only one that can catch that function itself, because every other z prediction
# is computed through it.
#
# 75 -> 84 on 2026-08-13, when the props sidecar landed: the synthetic fixture
# now carries three props (one outlined), the --no-props flag has a control,
# and section 3 pins all 864 Pre-Searing proxies at (x, y, -z) with the proxy
# OBJECTS scoring the chunk's own 0.7338 against the mesh.
#
# 84 -> 92 the same day with rung M4's section 4: REAL meshes from the
# `.gwmodel` family, the instancing (664 props over 152 datablocks, none
# shared across file ids), the real/proxy split with nothing lost between
# them, and THE Z SIGN -- 0.961 of real props reach above the terrain against
# 0.032 for the reflected control. Sections 0-2 still score 45.
#
# 108 -> 114 on 2026-08-14, rung T6: section 5 recomputes the overlay
# geometry straight from the .layers.u16 sidecar -- one face per non-base
# layer, rotated where bit 15 is set -- and requires Blender's built
# object to match (262,310 faces over 148,882 cells, 68,201 rotated on
# Pre-Searing), requires all four base quadrants to be in use (T5 pinned
# every cell to quadrant 0, which was the repetition), and adds the
# --no-blend control. Sections 0-2b score 54.
#
# 92 -> 108 on 2026-08-14, rung T5 (46.0 s green): section 2b binds a
# synthetic ground -- two decodable tiles plus one whose file id resolves to
# nothing, which must get its OWN named empty slot rather than falling
# through to slot 0 -- and section 5 asserts the real map's binding against
# the SIDECAR (every tile's slot material the manifest's image, all 212,992
# face indices digest-equal to a recomputation from tiles.u8), with
# --no-terrain-textures as the control on both.
#
# 108 -> 110 the same day, after the first human look at the scene: the
# blend mask was DARKENING the ground (Blender premultiplies STRAIGHT-mode
# images, so the Color output was RGB x alpha -- measured on the PNGs:
# window luminance flat, window alpha banded), and the terrain was
# flat-shaded where the client's vertex layouts carry normals. One check
# per section pins CHANNEL_PACKED and all-faces-smooth, read back off the
# scene. Sections 0-2b score 54, so a vault-less run lands 56 short.
FLOOR = 118


# ------------------------------------------------------------------ helpers

def find_blender(explicit=None, environ=None):
    """`(path, why)` -- the Blender to run, or `(None, reason)`.

    AN EXPLICIT REQUEST IS NEVER FALLEN THROUGH. `--blender` and `RURIK_BLENDER`
    name one specific install; if that path is not a file the answer is None,
    not "some other Blender". The first version of this function walked
    `(explicit, env, KNOWN_BLENDER)` and took the first that existed, so
    `--blender C:\\nope\\blender.exe` silently ran the install at
    `KNOWN_BLENDER` and the run printed ALL CHECKS PASSED (69 checks) for a
    binary nobody asked for -- an override that overrides nothing, and the
    silent-success failure this repository keeps finding in its own tools. It
    matters most in the case the flag exists for: pointing the suite at a second
    Blender to see whether a result is version-specific would have re-measured
    the first one and agreed with itself.

    Section 0 is the check, and it carries its own positive control so the two
    refusals cannot pass vacuously.
    """
    environ = os.environ if environ is None else environ
    for source, cand in (("--blender", explicit),
                         (BLENDER_ENV, environ.get(BLENDER_ENV))):
        if cand:
            if os.path.isfile(cand):
                return cand, source
            return None, ("%s names %s, which is not a file. An explicit "
                          "request is refused rather than fallen through -- "
                          "fix it, or drop it to use the default install."
                          % (source, cand))
    if os.path.isfile(KNOWN_BLENDER):
        return KNOWN_BLENDER, "the known install"
    found = shutil.which("blender")
    if found:
        return found, "PATH"
    return None, ("no Blender found: %s is unset, %s does not exist, and "
                  "'blender' is not on PATH. Point at an install with %s or "
                  "--blender." % (BLENDER_ENV, KNOWN_BLENDER, BLENDER_ENV))


def run_blender(blender, json_path, workdir, verts=False,
                timeout=BLENDER_TIMEOUT, extra=()):
    """Run the importer headless. Returns `(returncode, output, summary, verts)`.

    `summary` is the parsed dump or None when the importer did not write one --
    which is itself a check: a failing import must leave no artifact behind for a
    later section to read as a success.
    """
    dump = os.path.join(workdir, "summary.json")
    vpath = os.path.join(workdir, "verts.f32")
    for stale in (dump, vpath):
        if os.path.exists(stale):
            os.remove(stale)
    cmd = [blender, "--background", "--factory-startup",
           "--python-exit-code", str(PYTHON_EXIT_CODE),
           "--python", IMPORTER, "--",
           json_path, "--dump", dump, "--clear"]
    if verts:
        cmd += ["--dump-verts", vpath]
    cmd += list(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          errors="replace")
    out = (proc.stdout or "") + (proc.stderr or "")
    summary = None
    if os.path.isfile(dump):
        with open(dump, "r", encoding="utf-8") as fh:
            summary = json.load(fh)
    buf = None
    if verts and os.path.isfile(vpath):
        with open(vpath, "rb") as fh:
            blob = fh.read()
        buf = struct.unpack("<%df" % (len(blob) // 4), blob)
    return proc.returncode, out, summary, buf


def f32_digest(values):
    """sha256 over the values as little-endian float32 -- what a vertex IS.

    Blender stores a vertex coordinate as a C float, so packing our doubles the
    same way makes the comparison exact instead of tolerance-based. A tolerance
    here would hide a half-cell offset in the last bits and pass a mesh that is
    not the one the file describes.
    """
    return hashlib.sha256(struct.pack("<%df" % len(values), *values)).hexdigest()


def expected_lattice(exp):
    """The `(dimX+1)*(dimY+1)` vertex lattice, computed from the interchange.

    `exp` is a `mapexport.MapExport`. Row-major in `j`, `i`, which is the order
    `import_gwmap.build_geometry` emits and the order the digests are taken in.
    """
    dx, dy = exp.dim_x, exp.dim_y
    xs, ys = [], []
    for j in range(dy + 1):
        _wx, wy = exp.world_at(0, j)
        for i in range(dx + 1):
            xs.append(exp.world_at(i, 0)[0])
            ys.append(wy)
    return xs, ys, exp.corner_heights()


def rewrite_export(src_json, dst_dir, mutate_meta=None, mutate_heights=None):
    """Copy an export into `dst_dir`, optionally changing it, digests fixed up.

    `mutate_meta(meta)` edits the JSON in place; `mutate_heights(list)` returns a
    new height list, whose sha256 is then recomputed so the change survives
    verification. A control that only broke the digest would be testing the
    digest, not the geometry.
    """
    src_dir = os.path.dirname(os.path.abspath(src_json))
    os.makedirs(dst_dir, exist_ok=True)
    with open(src_json, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    for side in meta["sidecars"]:
        blob = open(os.path.join(src_dir, side["name"]), "rb").read()
        if mutate_heights is not None and side["kind"] == "heights":
            values = list(struct.unpack("<%df" % side["count"], blob))
            blob = struct.pack("<%df" % side["count"],
                               *mutate_heights(values, meta))
            side["bytes"] = len(blob)
            side["sha256"] = hashlib.sha256(blob).hexdigest()
        open(os.path.join(dst_dir, side["name"]), "wb").write(blob)
    if mutate_meta is not None:
        mutate_meta(meta)
    dst = os.path.join(dst_dir, os.path.basename(src_json))
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    return dst


def f32(value):
    """One double rounded to float32 -- what Blender stored, so keys compare exact."""
    return struct.unpack("<f", struct.pack("<f", value))[0]


def height_map(verts):
    """`{(x, y): z}` from Blender's raw vertex buffer.

    THE ORACLE LOOKS THE MESH UP BY WORLD POSITION, not by an index. An earlier
    version of this file addressed the lattice as `(gy*stride + gx)*3 + 2`, which
    shares the row convention with the code under test -- and a sabotage that
    placed every vertex at `y0 + j*pitch` instead of `y1 - j*pitch` (the whole
    map upside down) scored the baseline UNCHANGED, because the z values had not
    moved within the buffer. Going through the coordinates Blender actually
    stored is what makes the placement part of the claim.
    """
    out = {}
    for k in range(0, len(verts), 3):
        out[(verts[k], verts[k + 1])] = verts[k + 2]
    return out


def mesh_z(stored):
    """World z for a stored height. THE ONLY PLACE THIS TEST STATES THE SIGN.

    FINDINGS 25: a greater stored value is LOWER in the world, measured by two
    client runs differing in nothing else. The importer negates on the way into
    Blender so a human looks at the map the right way up, and every prediction
    below goes through here so the convention lives in one place instead of
    eight. Nothing in the ARCHIVE can refute it -- props and terrain share the
    file's convention, so the prop oracle is invariant under the flip and says
    nothing about it. The warrant is the client.
    """
    return -stored


def score_mesh(zmap, dim_x, dim_y, rect, props, layout):
    """Score one layout of the MESH against the props. `(frac<100, median, n, out)`.

    For each prop, take its cell `(gx, gy)`, work out the WORLD position of that
    cell's corner, and ask the mesh what is standing there. `missing` counts the
    props whose corner is not a vertex at all, which a mesh laid on the wrong
    pitch would produce in quantity.
    """
    x0, y0, _x1, y1 = rect
    dz, outside, missing = [], 0, 0
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
        z = zmap.get((f32(x0 + gx * CELL_PITCH), f32(y1 - gy * CELL_PITCH)))
        if z is None:
            missing += 1
            continue
        # THE PROP IS NEGATED TOO, and it has to be. The importer emits world z
        # (FINDINGS 25) while the props chunk stores the file's convention, so
        # comparing them raw would score a correct mesh as inverted. Negating
        # BOTH leaves this oracle's number bit-identical -- |-a - -b| == |a - b|
        # -- which is exactly why it cannot see the sign and must not be quoted
        # as evidence for it.
        dz.append(abs(z - (-wz)))
    if not dz:
        return 0.0, float("inf"), 0, outside + missing
    dz.sort()
    return (sum(1 for d in dz if d < 100.0) / len(dz),
            dz[len(dz) // 2], len(dz), outside + missing)


def structural_checks(check, summary, exp, tag):
    """The claims that hold for any map: counts, quads, winding, bbox, digests.

    Shared by the synthetic section and the real-map section so the real map is
    held to exactly the same standard, and so a claim cannot be quietly weakened
    for the fixture that is harder to satisfy.
    """
    dx, dy = exp.dim_x, exp.dim_y
    x0, y0, x1, y1 = exp.rect

    check(summary["vertex_count"] == (dx + 1) * (dy + 1),
          "%s: %d vertices, the (dimX+1)*(dimY+1) lattice"
          % (tag, (dx + 1) * (dy + 1)), "%d" % summary["vertex_count"])
    check(summary["face_count"] == dx * dy,
          "%s: %d faces, one per cell" % (tag, dx * dy),
          "%d" % summary["face_count"])
    check(summary["face_sizes"] == {"4": dx * dy},
          "%s: every face is a quad" % tag, "%r" % summary["face_sizes"])
    check(summary["faces_normal_up"] == dx * dy,
          "%s: every face normal points +Z (the winding is not inside out)" % tag,
          "%d of %d" % (summary["faces_normal_up"], dx * dy))
    check(summary["first_face"] == [0, dx + 1, dx + 2, 1],
          "%s: face (0,0) is wound (0,0)->(0,1)->(1,1)->(1,0)" % tag,
          "%r" % summary["first_face"])

    # THE CROSS-CHUNK CHECK: the mesh spans the Map Parameters rect exactly.
    bmin, bmax = summary["bbox"]["min"], summary["bbox"]["max"]
    check((bmin[0], bmax[0]) == (x0, x1),
          "%s: the mesh's x bounds ARE the map rect's" % tag,
          "%r..%r vs %r..%r" % (bmin[0], bmax[0], x0, x1))
    check((bmin[1], bmax[1]) == (y0, y1),
          "%s: the mesh's y bounds ARE the map rect's" % tag,
          "%r..%r vs %r..%r" % (bmin[1], bmax[1], y0, y1))
    check(summary["extent_matches_rect"],
          "%s: the importer agrees dims * pitch == the rect span" % tag)
    check(summary["cell_pitch"] == CELL_PITCH,
          "%s: the pitch carried into Blender is %r" % (tag, CELL_PITCH),
          "%r" % summary["cell_pitch"])

    lo, hi = min(exp.heights), max(exp.heights)
    # NOTE THE SWAP: negation turns the lowest stored value into the highest
    # world z, so a version of this check that negated without swapping would
    # fail on every map with any relief and pass on a flat one.
    check((bmin[2], bmax[2]) == (mesh_z(hi), mesh_z(lo)),
          "%s: z spans the stored heights NEGATED (FINDINGS 25)" % tag,
          "%r..%r vs %r..%r" % (bmin[2], bmax[2], mesh_z(hi), mesh_z(lo)))

    # The four lattice corners, by name. Row 0 is world maxY, so j=0 is north.
    corners = exp.corner_heights()
    stride = dx + 1
    want = {"nw": (0, 0), "ne": (dx, 0), "sw": (0, dy), "se": (dx, dy)}
    bad = []
    for name, (i, j) in want.items():
        got = summary["corners"][name]
        wx, wy = exp.world_at(i, j)
        if (got["x"], got["y"], got["z"]) != (wx, wy,
                                              mesh_z(corners[j * stride + i])):
            bad.append((name, got))
    check(not bad, "%s: all four lattice corners carry the world position and "
                   "height the interchange says" % tag,
          "%r" % bad if bad else "nw/ne/sw/se")

    # EVERY vertex, through the digests, rather than the handful printed above.
    xs, ys, zs = expected_lattice(exp)
    zs = [mesh_z(v) for v in zs]
    check(summary["digest_x"] == f32_digest(xs),
          "%s: all %d vertex x agree with x0 + i*pitch"
          % (tag, len(xs)))
    check(summary["digest_y"] == f32_digest(ys),
          "%s: all %d vertex y agree with y1 - j*pitch (row 0 is maxY)"
          % (tag, len(ys)))
    check(summary["digest_z"] == f32_digest(zs),
          "%s: all %d vertex z are the stored heights NEGATED, with the "
          "client's replicated far edge" % (tag, len(zs)))

    probes = summary["probes"]
    off = [p for p in probes
           if (p["x"], p["y"], p["z"])
           != (exp.world_at(p["i"], p["j"])[0], exp.world_at(p["i"], p["j"])[1],
               mesh_z(corners[p["j"] * stride + p["i"]]))]
    check(not off, "%s: the %d scattered probe vertices land where the "
                   "interchange puts them" % (tag, len(probes)),
          "%d off" % len(off) if off else "")


# --------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender", default=None)
    ap.add_argument("--dat", default=None)
    args = ap.parse_args(argv)

    led = checks.Ledger("blender import", floor=FLOOR)
    check = checks.adopt(led)
    t0 = time.perf_counter()

    blender, why = find_blender(args.blender)
    if blender is None:
        led.skip("all sections", why)
        return led.verdict()
    print("blender: %s   (%s)" % (blender, why))

    if not os.path.isfile(IMPORTER):
        led.skip("all sections", "no importer at %s" % IMPORTER)
        return led.verdict()

    _section0(check, blender)
    with tempfile.TemporaryDirectory(prefix="rurik_blender_") as tmp:
        base_json = _section1(check, led, blender, tmp)
        _section2(check, led, blender, tmp, base_json)
        _section2b(check, led, blender, tmp)
        _section3(check, led, blender, tmp, args)

    print("\n(%.1fs)" % (time.perf_counter() - t0))
    return led.verdict()


# --- 0. the install selector -----------------------------------------------

def _section0(check, blender):
    """The `--blender` / `RURIK_BLENDER` override must actually override.

    Cheap, needs no Blender run, and it is here because the shipped version
    silently fell through to `KNOWN_BLENDER` when the requested path did not
    exist -- so a run that asked for install B measured install A and printed
    green. Every refusal below is paired with a positive control: a selector
    that refused EVERYTHING would pass the two refusals and fail the two that
    follow.
    """
    print("\n== 0. the install selector honours an explicit request ==")
    missing = os.path.join(os.path.dirname(blender), "no_such_blender.exe")
    check(not os.path.isfile(missing),
          "the control path really does not exist", missing)

    got, why = find_blender(missing, environ={})
    check(got is None and "not a file" in why,
          "--blender at a path that does not exist is REFUSED, not silently "
          "replaced by the known install", "got %r" % (got,))

    got, why = find_blender(None, environ={BLENDER_ENV: missing})
    check(got is None and "not a file" in why,
          "%s at a path that does not exist is REFUSED the same way"
          % BLENDER_ENV, "got %r" % (got,))

    # THE POSITIVE CONTROLS. Without these a selector that answered None to
    # everything would score the two checks above and measure nothing.
    got, why = find_blender(blender, environ={BLENDER_ENV: missing})
    check(got == blender and why == "--blender",
          "an explicit path that DOES exist is honoured, and beats the "
          "environment", "%r (%s)" % (got, why))

    got, why = find_blender(None, environ={})
    check(got is not None,
          "with nothing explicit the default install is still found",
          "%r (%s)" % (got, why))


# --- 1. a mesh built from a grid this file invented ------------------------

def _section1(check, led, blender, tmp):
    print("\n== 1. Blender builds the lattice the interchange describes (no vault) ==")
    # AGAINST LITERALS, and this is the only check in the file that can catch
    # `mesh_z` ITSELF being changed. Every other z prediction here routes through
    # that function, so making it the identity would move all of them together
    # and the run would stay green while Blender drew every map upside down --
    # the same shape as the twelve combat constants in test_agentlife that could
    # each be set to a wrong value with 125 checks passing, because every
    # expectation was computed FROM the symbol under test. A symbol appearing in
    # a test file is not a check.
    check(mesh_z(100.0) == -100.0 and mesh_z(-13.0) == 13.0
          and mesh_z(0.0) == 0.0,
          "the sign convention is NEGATION, asserted against literals",
          "mesh_z(100)=%r, mesh_z(-13)=%r -- FINDINGS 25, warranted by two "
          "client runs and by nothing in the archive"
          % (mesh_z(100.0), mesh_z(-13.0)))

    dx, dy = SYN_X, SYN_Y
    trn = synthetic_terrain(dx, dy)
    # A rect that is NOT centred on the origin and whose y0 is not -y1, so a sign
    # error or a swapped pair cannot come out looking right by symmetry.
    rect = (-1536.0, -3072.0, dx * CELL_PITCH - 1536.0, dy * CELL_PITCH - 3072.0)
    # WITH PROPS: the fixture carries test_mapexport's synthetic pair, so the
    # proxy path runs on a bare machine too. Three props, one with an outline.
    head, partner, sp = _synth_pair()
    pd = build_props(head, partner)
    meta, payloads = build_manifest(trn, rect, "synthetic",
                                    {"archive": None, "row": None,
                                     "file_id": None},
                                    props=pd, props_state="exported")
    src = write_export(meta, payloads, os.path.join(tmp, "syn"))
    exp = load_export(src)

    # The fixture must be able to refute: every height distinct, so a shuffled,
    # transposed or flipped lattice cannot match by coincidence.
    check(len(set(exp.heights)) == exp.cells,
          "the fixture's %d heights are all distinct, so a misplaced vertex "
          "cannot pass" % exp.cells, "%d distinct" % len(set(exp.heights)))

    work = os.path.join(tmp, "run_syn")
    os.makedirs(work, exist_ok=True)
    rc, out, summary, _v = run_blender(blender, src, work)
    check(rc == 0, "Blender exits 0 on the synthetic export", "rc=%d" % rc)
    check(summary is not None, "Blender wrote the mesh summary")
    if summary is None:
        led.skip("1. the built mesh", "no summary; blender said: %s"
                 % out.strip().splitlines()[-3:])
        return src
    check(summary["blender"].split(".")[0] == MEASURED_BLENDER.split(".")[0],
          "the Blender that ran is major version %s, as measured"
          % MEASURED_BLENDER.split(".")[0], summary["blender"])

    structural_checks(check, summary, exp, "synthetic")

    # The tile and shade arrays reached the mesh as per-face attributes. Their
    # MEANING is unsettled upstream (terrain.py labels both NOT FOUND); this is
    # a transport check and nothing more.
    check("gw_tile" in summary["attributes"] and
          "gw_shade" in summary["attributes"],
          "the tile and shade sidecars arrive as per-face attributes",
          ",".join(a for a in summary["attributes"] if not a.startswith(".")))

    # ---- the synthetic props ----------------------------------------------
    ps = summary.get("props")
    check(ps is not None and ps["count"] == len(sp.props)
          and ps["sidecar_count"] == len(sp.props),
          "the three synthetic props became proxy objects",
          "%r" % (ps and (ps["count"], ps["sidecar_count"]),))
    if ps is not None:
        # Prop 1's outline is a CLOSED ring (first == last), so the proxy drops
        # the repeated point and extrudes a 3-vertex footprint; the other two
        # fall back to radius cylinders.
        check(ps["outlined"] == 1,
              "exactly the one outlined prop became a footprint prism",
              "%d" % ps["outlined"])
        # Placement: (x, y, -z), the terrain's own negation, EXACTLY -- every
        # coordinate here is f32-exact so a tolerance would only hide a defect.
        want = [(p.x, p.y, -p.z) for p in sp.props]
        got = [tuple(o["location"]) for o in ps["objects"]]
        check(got == want,
              "every proxy sits at (x, y, -z) -- the prop z is negated the "
              "same way the terrain is (FINDINGS 25)",
              "%r vs %r" % (got[:2], want[:2]) if got != want else "3 exact")
        check([o["file_id"] for o in ps["objects"]] == [0x1111, 0x2222, 0x1111],
              "each proxy carries its model's file id from the sidecar")

    # THE FLAG CONTROL: --no-props must actually turn the proxies off. A flag
    # that silently stopped working would re-import props into every scene an
    # operator asked to keep clean, and nothing else here would notice.
    work_np = os.path.join(tmp, "run_syn_noprops")
    os.makedirs(work_np, exist_ok=True)
    rc, _out, s2, _v = run_blender(blender, src, work_np,
                                   extra=["--no-props"])
    check(rc == 0 and s2 is not None and "props" not in s2,
          "--no-props imports the terrain alone and the dump says so",
          "rc=%d, props block %s" % (rc, "absent" if s2 and "props" not in s2
                                     else "PRESENT"))
    return src


# --- 2. the three negative controls ----------------------------------------

def _section2(check, led, blender, tmp, src):
    print("\n== 2. controls the importer must NOT survive ==")
    if src is None:
        led.skip("2. the negative controls", "section 1 built no fixture")
        return
    exp = load_export(src)
    dx, dy = exp.dim_x, exp.dim_y
    x0, y0, x1, y1 = exp.rect
    work = os.path.join(tmp, "run_ctl")
    os.makedirs(work, exist_ok=True)

    # (a) THE PITCH CONTROL. Change nothing but `cell_pitch`. The digests all
    # verify, so the importer has no way to notice except by arithmetic -- and
    # the mesh must stop covering the rect.
    bad_pitch = 64.0

    def set_pitch(meta):
        meta["cell_pitch"] = bad_pitch

    ctl = rewrite_export(src, os.path.join(tmp, "ctl_pitch"),
                         mutate_meta=set_pitch)
    rc, out, summary, _v = run_blender(blender, ctl, work)
    check(rc == 0 and summary is not None,
          "the pitch control still imports (so what follows is about geometry, "
          "not a crash)", "rc=%d" % rc)
    if summary is not None:
        bmin, bmax = summary["bbox"]["min"], summary["bbox"]["max"]
        check((bmin[0], bmax[0]) != (x0, x1) or (bmin[1], bmax[1]) != (y0, y1),
              "PITCH CONTROL: the bounding box no longer matches the map rect",
              "x %r..%r vs %r..%r" % (bmin[0], bmax[0], x0, x1))
        check(bmax[0] == x0 + dx * bad_pitch and bmin[1] == y1 - dy * bad_pitch,
              "PITCH CONTROL: and it is off by exactly the pitch it was given",
              "%r, %r" % (bmax[0], bmin[1]))
        check(summary["extent_matches_rect"] is False,
              "PITCH CONTROL: the importer reports the rect disagreement rather "
              "than passing it on silently")
        check("[warn]" in out and "pitch" in out,
              "PITCH CONTROL: and says so on stderr")

    # (b) THE ROW-ORDER CONTROL. Reverse the grid's rows and fix the digest, so
    # the file verifies perfectly and only the geometry is wrong. Its BOUNDING
    # BOX IS UNCHANGED -- which is the point: this is the defect oracle 2 cannot
    # see, and the reason section 3's prop oracle exists.
    def flip_rows(values, meta):
        w = meta["dims"]["x"]
        h = meta["dims"]["y"]
        out = []
        for gy in range(h - 1, -1, -1):
            out.extend(values[gy * w:(gy + 1) * w])
        return out

    ctl = rewrite_export(src, os.path.join(tmp, "ctl_flip"),
                         mutate_heights=flip_rows)
    rc, out, summary_flip, _v = run_blender(blender, ctl, work)
    check(rc == 0 and summary_flip is not None,
          "the row-order control imports cleanly", "rc=%d" % rc)
    if summary_flip is not None:
        xs, ys, zs = expected_lattice(exp)
        zs = [mesh_z(v) for v in zs]
        check(summary_flip["digest_z"] != f32_digest(zs),
              "ROW CONTROL: the z digest changes when the rows are reversed")
        check(summary_flip["digest_x"] == f32_digest(xs) and
              summary_flip["digest_y"] == f32_digest(ys),
              "ROW CONTROL: x and y are untouched -- only the heights moved")
        check(summary_flip["corners"]["nw"]["z"] != mesh_z(exp.heights[0]),
              "ROW CONTROL: the north-west corner now carries a different height",
              "%r vs %r" % (summary_flip["corners"]["nw"]["z"], exp.heights[0]))
        check(summary_flip["bbox"] == _bbox_of(exp),
              "ROW CONTROL: and the BOUNDING BOX is identical -- which is why "
              "oracle 2 alone would have passed this")

    # (c) THE DIGEST CONTROL. One mantissa bit of one height, digest untouched.
    # A file we cannot vouch for must produce no mesh at all.
    ctl = rewrite_export(src, os.path.join(tmp, "ctl_corrupt"))
    side = next(s for s in json.load(open(ctl, encoding="utf-8"))["sidecars"]
                if s["kind"] == "heights")
    hpath = os.path.join(os.path.dirname(ctl), side["name"])
    blob = bytearray(open(hpath, "rb").read())
    before, = struct.unpack_from("<f", bytes(blob), 400)
    blob[400] ^= 0x01
    after, = struct.unpack_from("<f", bytes(blob), 400)
    open(hpath, "wb").write(bytes(blob))
    check(before != after and len(blob) == side["bytes"],
          "the corruption really changed one height and nothing else",
          "%r -> %r, still %d bytes" % (before, after, len(blob)))
    rc, out, summary_bad, _v = run_blender(blender, ctl, work)
    check(rc == PYTHON_EXIT_CODE,
          "DIGEST CONTROL: Blender exits %d on a sidecar whose sha256 disagrees "
          "(only because --python-exit-code was passed; without it a raising "
          "script still exits 0)" % PYTHON_EXIT_CODE, "rc=%d" % rc)
    check(summary_bad is None,
          "DIGEST CONTROL: and writes no summary, so nothing downstream can "
          "read a failed import as a success")
    check("sha256" in out,
          "DIGEST CONTROL: the refusal names the digest", out.strip()[-90:])


def _bbox_of(exp):
    x0, y0, x1, y1 = exp.rect
    return {"min": [x0, y0, mesh_z(max(exp.heights))],
            "max": [x1, y1, mesh_z(min(exp.heights))]}


# --- 2b. rung T5 on a synthetic fixture, no vault ---------------------------

def _section2b(check, led, blender, tmp):
    print("\n== 2b. rung T5: the ground's material, synthetic (no vault) ==")
    # Three tiles: two behind decodable synthetic ATEX rows, one whose file id
    # the table cannot resolve -- so the UNTEXTURED path runs on a bare
    # machine, and the prop fall-through defect (unbound faces silently
    # drawing slot 0) has a check that would catch its return.
    fids = (0x1111, 0x2222, 0x3333)
    blobs = {10 + i: atex.build(b"DXT1", 8, 8, fill=0x01010101 * (i + 1))
             for i in range(3)}
    table = {0x1111: 10, 0x2222: 11}
    trn = synthetic_terrain()
    block, tex_payloads = build_terrain_textures(
        MapFile(chunks=[_tex_deps(*fids)]), trn, _TexArchive(blobs),
        table=table)
    rect = (-1536.0, -3072.0, SYN_X * CELL_PITCH - 1536.0,
            SYN_Y * CELL_PITCH - 3072.0)
    meta, payloads = build_manifest(trn, rect, "syntex",
                                    {"archive": None, "row": None,
                                     "file_id": None},
                                    terrain_textures=block,
                                    textures_state="exported")
    src = write_export(meta, payloads + tex_payloads,
                       os.path.join(tmp, "syntex"))
    exp = load_export(src)

    work = os.path.join(tmp, "run_syntex")
    os.makedirs(work, exist_ok=True)
    rc, out, summary, _v = run_blender(blender, src, work)
    check(rc == 0 and summary is not None,
          "Blender imports the textured synthetic export", "rc=%d" % rc)
    if summary is None:
        led.skip("2b. the ground material", "no summary; blender said: %r"
                 % out.strip()[-200:])
        return
    tt = summary.get("terrain_textures")
    check(tt is not None and tt.get("state") == "bound",
          "the ground is bound", "%r" % (tt and tt.get("state"),))
    if not tt or tt.get("state") != "bound":
        return

    check(tt["materials"] == ["tex_1111.png", "tex_2222.png",
                              "gw_untextured_3333"],
          "one material per distinct image, and the unresolvable tile gets "
          "its OWN named slot rather than impersonating slot 0",
          "%r" % (tt["materials"],))
    check(tt["tile_slot"] == [0, 1, 2] and tt["untextured_tiles"] == [2],
          "tile->slot is the manifest's order and names the untextured tile")

    # THE BINDING, at full coverage: recompute the per-face material index
    # from the SIDECAR's tile bytes and the dump's slot table, and it must
    # equal the digest Blender took off its own built polygons.
    idx = [tt["tile_slot"][t] for t in exp.tiles]
    want = hashlib.sha256(struct.pack("<%dH" % len(idx), *idx)).hexdigest()
    check(want == tt["material_index_digest"],
          "all %d faces bind by their tile byte, including the untextured "
          "slot -- reached explicitly, never by fall-through" % len(idx))
    census = {}
    for t in exp.tiles:
        s = str(tt["tile_slot"][t])
        census[s] = census.get(s, 0) + 1
    check(tt["faces_per_slot"] == census and
          sum(census.values()) == exp.cells,
          "the per-slot face counts match the sidecar's own census",
          "%r" % (tt["faces_per_slot"],))
    check(tt["uv_window"] == [8.5 / 256.0, 119.5 / 256.0],
          "the UV window is T3's measured inner 111 texels (corners inset "
          "8.5)", "%r" % (tt["uv_window"],))
    check(tt["image_alpha_modes"] == ["CHANNEL_PACKED"]
          and tt["faces_smooth"] == exp.cells,
          "the mask is CHANNEL_PACKED (alpha is DATA -- premultiplication "
          "was darkening clean RGB by the blend mask) and every face is "
          "smooth-shaded (the client's terrain vertices carry normals)",
          "%r, %d smooth" % (tt["image_alpha_modes"], tt["faces_smooth"]))

    # THE FLAG CONTROL: --no-terrain-textures leaves the ground bare.
    work2 = os.path.join(tmp, "run_syntex_ctl")
    os.makedirs(work2, exist_ok=True)
    rc, _out, s2, _v = run_blender(blender, src, work2,
                                   extra=["--no-terrain-textures"])
    check(rc == 0 and s2 is not None
          and s2.get("terrain_textures", {}).get("state") == "skipped",
          "--no-terrain-textures leaves the ground unmaterialed and the "
          "dump says so",
          "rc=%d, state %r" % (rc, s2 and s2.get("terrain_textures")))


# --- 3. a real map, and the props that stand on it --------------------------

def _section3(check, led, blender, tmp, args):
    dat = args.dat
    if dat is None:
        dat = os.path.join(vaultpath.vault_root(), "dat_study", "Gw.dat")
    if not os.path.isfile(dat):
        led.skip("3. a real map, and the prop-z oracle on the built mesh",
                 "no archive at %s (vault resolved to %s, %s)"
                 % (dat, vaultpath.vault_root(), vaultpath.vault_why()))
        return

    print("\n== 3. THE ORACLE: prop z against Blender's own vertex buffer ==")
    print("   props chunk 0x%08X, read here by this file's own walker -- the\n"
          "   TERRAIN path (exporter and importer both) never touches it\n"
          % PROPS_CHUNK)

    with Archive(dat) as ar:
        row = file_id_table(ar).get(PRESEARING_FILE_ID)
        check(row == PRESEARING_ROW,
              "file id 0x%X resolves to row %d" % (PRESEARING_FILE_ID,
                                                   PRESEARING_ROW),
              "got %r" % row)
        if row is None:
            led.skip("3. the prop oracle", "the reference map did not resolve")
            return
        src = export_row(row, ar, outdir=os.path.join(tmp, "real"),
                         file_id=PRESEARING_FILE_ID, name="presearing")
        chunks = read_chunks(ar, row)

    exp = load_export(src)
    dx, dy = exp.dim_x, exp.dim_y
    check((dx, dy) == PRESEARING_DIMS,
          "row %d is the pinned %dx%d grid" % (row, PRESEARING_DIMS[0],
                                               PRESEARING_DIMS[1]),
          "%dx%d" % (dx, dy))
    check(exp.rect == PRESEARING_RECT, "row %d has the pinned map rect" % row,
          "%r" % (exp.rect,))
    # A flat map would make every z claim below vacuous. Pre-Searing is not one.
    check(len(set(exp.heights)) > 1000,
          "the real map's heights actually vary, so the z checks are not vacuous",
          "%d distinct values over %d cells" % (len(set(exp.heights)),
                                                exp.cells))

    work = os.path.join(tmp, "run_real")
    os.makedirs(work, exist_ok=True)
    t = time.perf_counter()
    # --proxies-only is EXPLICIT, not incidental. This section's claims are
    # about the measured proxies, and without the flag it would get them only
    # because no `models/` directory happens to sit beside the temp export --
    # so exporting a model family there would silently turn this section into
    # a test of something else, with every check still green.
    rc, out, summary, verts = run_blender(blender, src, work, verts=True,
                                          extra=["--proxies-only"])
    check(rc == 0, "Blender exits 0 on the real map", "rc=%d" % rc)
    check(summary is not None and verts is not None,
          "Blender wrote both the summary and the raw vertex buffer")
    if summary is None or verts is None:
        led.skip("3. the built mesh", "no dump; blender said: %r"
                 % out.strip()[-200:])
        return
    print("   %d x %d cells -> %d vertices, %d quads in %.1fs"
          % (dx, dy, summary["vertex_count"], summary["face_count"],
             time.perf_counter() - t))

    structural_checks(check, summary, exp, "row %d" % row)
    check(len(verts) == 3 * (dx + 1) * (dy + 1),
          "the vertex buffer holds xyz for all %d vertices"
          % ((dx + 1) * (dy + 1)), "%d floats" % len(verts))

    # ---- the props ---------------------------------------------------------
    check(PROPS_CHUNK in chunks,
          "row %d carries the props chunk 0x%08X" % (row, PROPS_CHUNK))
    props, version, array_size, consumed = read_props(chunks[PROPS_CHUNK])
    check(version == PROPS_VERSION and consumed == array_size,
          "the prop walk closes on its own declared array size",
          "v%d, %d of %d bytes" % (version, consumed, array_size))
    check(len(props) == PRESEARING_PROPS,
          "%d props, the pinned population" % PRESEARING_PROPS,
          "got %d" % len(props))
    if len(props) != PRESEARING_PROPS:
        led.skip("3. the prop oracle", "the prop population moved")
        return

    zmap = height_map(verts)
    check(len(zmap) == (dx + 1) * (dy + 1),
          "every vertex sits at its own world position -- %d distinct (x, y) "
          "for %d vertices, so the lookup below is unambiguous"
          % (len(zmap), (dx + 1) * (dy + 1)), "%d" % len(zmap))

    results = {}
    for layout in (MESH_ORACLE_LAYOUT,) + MESH_CONTROLS:
        frac, med, n, outside = score_mesh(zmap, dx, dy, exp.rect, props,
                                           layout)
        results[layout] = (frac, med, n, outside)
        print("    %-10s frac<100 %.4f  median |dz| %9.2f  n=%d  outside=%d"
              % (layout, frac, med, n, outside))

    check(all(r[3] == 0 and r[2] == len(props) for r in results.values()),
          "all %d props land inside the mesh under every layout, so no control "
          "loses on sample size" % len(props))

    base_frac, base_med = results[MESH_ORACLE_LAYOUT][:2]
    want_f, want_m = ORACLE[MESH_ORACLE_LAYOUT][PRESEARING_ROW]
    # THE PREDICTION, stated in the module docstring before this ran: the mesh
    # must reproduce test_mapexport's number for the same map EXACTLY, not
    # approximately, because the lattice carries the cell grid unchanged.
    check(abs(base_frac - want_f) < FRAC_TOL,
          "the MESH scores test_mapexport section 5's baseline fraction %r"
          % want_f, "%.4f" % base_frac)
    check(abs(base_med - want_m) < 1.0,
          "the MESH scores its baseline median |dz| of %r" % want_m,
          "%.2f" % base_med)

    for layout in MESH_CONTROLS:
        frac, med = results[layout][:2]
        want_f, _wm = ORACLE[layout][PRESEARING_ROW]
        check(abs(frac - want_f) < FRAC_TOL,
              "the %s control on the mesh scores %r" % (layout, want_f),
              "%.4f" % frac)
        check(frac * MIN_RATIO <= base_frac,
              "the %s control collapses to under 1/%g of the mesh's baseline"
              % (layout, MIN_RATIO),
              "%.4f vs %.4f (%.1fx)" % (frac, base_frac, base_frac / frac)
              if frac else "0 vs %.4f" % base_frac)
        check(base_med * 2.0 <= med,
              "the %s control's median |dz| is at least 2x the baseline's"
              % layout, "%.1f vs %.1f" % (med, base_med))

    # ---- the prop PROXIES, against the sidecar and the mesh ----------------
    # The proxies are OBJECTS, so the checks above (which read the chunk) say
    # nothing about them; these read the summary's props block instead.
    ps = summary.get("props")
    check(ps is not None and ps["count"] == PRESEARING_PROPS
          and ps["sidecar_count"] == PRESEARING_PROPS,
          "all %d props became proxy objects" % PRESEARING_PROPS,
          "%r" % (ps and (ps["count"], ps["sidecar_count"]),))
    if ps is None:
        return
    check(ps["outlined"] == PRESEARING_OUTLINED,
          "%d outlined footprints, the pinned population (the rest are radius "
          "cylinders)" % PRESEARING_OUTLINED, "%d" % ps["outlined"])

    # Every proxy at (x, y, -z) of its sidecar record, wholesale and exact.
    pd = exp.props
    same = sum(1 for o, r in zip(ps["objects"], pd["props"])
               if tuple(o["location"]) == (r["position"][0], r["position"][1],
                                           -r["position"][2]))
    check(pd is not None and same == PRESEARING_PROPS,
          "every proxy sits at its sidecar record's (x, y, -z)",
          "%d/%d" % (same, PRESEARING_PROPS))

    # THE OBJECTS STAND ON THE MESH. Score the proxies' own locations against
    # Blender's vertex buffer, the same way the chunk was scored above. The
    # PREDICTION: identical to the chunk's baseline -- the proxies carry the
    # chunk's positions and both sides negate, so |dz| is invariant. A proxy
    # placement bug (a dropped negation, a swapped axis) breaks it.
    obj_props = [(o["location"][0], o["location"][1], -o["location"][2])
                 for o in ps["objects"]]
    frac, med, n, outside = score_mesh(zmap, dx, dy, exp.rect, obj_props,
                                       MESH_ORACLE_LAYOUT)
    want_f, _wm = ORACLE[MESH_ORACLE_LAYOUT][PRESEARING_ROW]
    check(outside == 0 and n == PRESEARING_PROPS
          and abs(frac - want_f) < FRAC_TOL,
          "the proxy OBJECTS score the same baseline %r against the mesh"
          % want_f, "%.4f, n=%d, outside=%d" % (frac, n, outside))

    _section4(check, led, blender, tmp, exp, zmap, src)
    _section5(check, led, blender, tmp, exp, src, summary)


# --- 4. REAL meshes, and the z sign they are built under --------------------

def _section4(check, led, blender, tmp, exp, zmap, src):
    print("\n== 4. real prop meshes, instanced, and the MEASURED z sign ==")
    models = os.path.join(os.path.dirname(os.path.abspath(src)), "models")
    vault_models = os.path.join(vaultpath.vault_root(), "exports", "models")
    if not os.path.isdir(models) and os.path.isdir(vault_models):
        models = vault_models
    if not os.path.isdir(models):
        led.skip("4. real prop meshes", "no .gwmodel family at %s" % models)
        return

    work = os.path.join(tmp, "run_real")
    os.makedirs(work, exist_ok=True)
    rc, out, summary, _v = run_blender(blender, src, work,
                                       extra=["--models", models])
    check(rc == 0 and summary is not None and "props" in summary,
          "Blender imports the map with the model family available",
          "rc=%d" % rc)
    if summary is None or "props" not in summary:
        led.skip("4. real prop meshes", "no summary")
        return
    ps = summary["props"]
    print("    %d props: %d real over %d datablocks, %d proxies"
          % (ps["count"], ps["real"], ps["real_meshes"], ps["proxy"]))

    check(ps["real"] == PRESEARING_REAL and ps["proxy"] == PRESEARING_PROXY,
          "%d props get a REAL mesh and %d keep a proxy -- the pinned split"
          % (PRESEARING_REAL, PRESEARING_PROXY),
          "%d/%d" % (ps["real"], ps["proxy"]))
    check(ps["real"] + ps["proxy"] == ps["count"] == PRESEARING_PROPS,
          "and no placement is LOST between the two paths -- a prop whose "
          "model does not decode keeps its proxy rather than vanishing")

    # INSTANCING. Every prop sharing a model must share one datablock; a
    # per-prop copy would be 664 meshes rather than 152 and is the obvious
    # way to get this "working" while multiplying the scene by four.
    check(ps["real_meshes"] == PRESEARING_MODELS,
          "the %d real props share exactly %d mesh datablocks (one per model)"
          % (PRESEARING_REAL, PRESEARING_MODELS), "%d" % ps["real_meshes"])
    by_mesh = {}
    for o in ps["objects"]:
        if o["real"]:
            by_mesh.setdefault(o["mesh"], set()).add(o["file_id"])
    check(all(len(v) == 1 for v in by_mesh.values()),
          "and no datablock is shared across DIFFERENT model file ids",
          "%d datablocks, worst %d ids"
          % (len(by_mesh), max((len(v) for v in by_mesh.values()), default=0)))

    # THE Z SIGN. MEASURED, not assumed: a prop's geometry must end up ABOVE
    # the terrain it stands on. `zmax` is world-space and comes off the built
    # objects, so this reads Blender's own answer rather than our arithmetic.
    above = n = 0
    for o in ps["objects"]:
        if not o["real"]:
            continue
        gy = int((exp.rect[3] - o["location"][1]) / CELL_PITCH)
        gx = int((o["location"][0] - exp.rect[0]) / CELL_PITCH)
        if not (0 <= gx < exp.dim_x and 0 <= gy < exp.dim_y):
            continue
        ground = zmap.get((f32(exp.rect[0] + gx * CELL_PITCH),
                           f32(exp.rect[3] - gy * CELL_PITCH)))
        if ground is None:
            continue
        n += 1
        above += o["zmax"] > ground
    frac = above / max(n, 1)
    print("    %d/%d real props reach ABOVE the terrain under them (%.3f)"
          % (above, n, frac))
    check(n > 500 and frac >= Z_SIGN_MIN,
          "prop geometry stands ABOVE the ground on at least %.0f%% of real "
          "props -- the model-space z sign, MEASURED" % (100 * Z_SIGN_MIN),
          "%.3f over n=%d" % (frac, n))

    # THE CONTROL, and it is what makes the line above a measurement: the
    # opposite sign buries the geometry. Scored on the SAME props, from the
    # same objects, by reflecting each mesh about its own placement z.
    flipped = sum(1 for o in ps["objects"] if o["real"]
                  and (2 * o["location"][2] - o["zmax"]) > _ground_of(
                      o, exp, zmap))
    fflip = flipped / max(n, 1)
    check(fflip * 2 < frac,
          "and the OPPOSITE sign collapses -- geometry reflected about its "
          "placement point sits above ground far less often",
          "%.3f vs %.3f" % (fflip, frac))

    # A prop whose model did not decode still has to be somewhere sensible.
    check(all(o["verts"] > 0 for o in ps["objects"]),
          "every object -- real or proxy -- carries geometry")


# --- 5. rung T5 on the real map ---------------------------------------------

def _section5(check, led, blender, tmp, exp, src, summary):
    print("\n== 5. rung T5: the real ground against the sidecar ==")
    block = exp.terrain_textures
    check(block is not None,
          "the real export carries its texture block (rung T4)")
    tt = (summary or {}).get("terrain_textures")
    check(tt is not None and tt.get("state") == "bound",
          "section 3's import bound the ground",
          "%r" % (tt and tt.get("state"),))
    if block is None or not tt or tt.get("state") != "bound":
        led.skip("5. the ground binding", "no block or unbound")
        return

    # THE RUNG CRITERION, against the SIDECAR rather than the importer's own
    # loop: (a) every tile's slot material is the image the MANIFEST names
    # for that tile byte; (b) every FACE's material index, recomputed here
    # from the tiles sidecar through the dump's slot table, digests to what
    # Blender read back off its own built polygons.
    slot_names, tile_slot = tt["materials"], tt["tile_slot"]
    bad = [e["tile"] for e in block["tiles"]
           if slot_names[tile_slot[e["tile"]]] !=
           (os.path.basename(e["image"]) if "image" in e
            else "gw_untextured_%X" % e["file_id"])]
    check(not bad,
          "every one of the %d tiles binds the texture the manifest names "
          "for it" % len(block["tiles"]), "wrong: %r" % (bad,))
    idx = [tile_slot[t] for t in exp.tiles]
    want = hashlib.sha256(struct.pack("<%dH" % len(idx), *idx)).hexdigest()
    check(want == tt["material_index_digest"],
          "all %d faces carry the material their tile byte names"
          % len(idx))
    check(sum(tt["faces_per_slot"].values()) == exp.cells,
          "every face is bound -- none fell through unassigned")
    check(tt["untextured_tiles"] == [],
          "every tile of the real map decoded, so no slot is a placeholder",
          "%r" % (tt["untextured_tiles"],))
    check(tt["uv_window"] == [8.5 / 256.0, 119.5 / 256.0],
          "the UV window is T3's measured inner 111 texels")
    check(tt["image_alpha_modes"] == ["CHANNEL_PACKED"]
          and tt["faces_smooth"] == exp.cells,
          "channel-packed mask and smooth shading on the real ground too",
          "%r, %d smooth" % (tt["image_alpha_modes"], tt["faces_smooth"]))

    # ---- rung T6: the blend overlays, against the sidecar ------------------
    # Recompute what the overlay geometry MUST be straight from the
    # `.layers.u16` sidecar -- one face per non-base layer, rotated where
    # bit 15 is set -- and require Blender's built object to match. The
    # sidecar is the exporter's resolved answer and this file never asks the
    # importer how many faces it meant to make.
    tbl = summary.get("terrain_blend") or {}
    words = exp.layers
    check(words is not None and len(words) == exp.cells * 3,
          "the export carries the resolved blend layers, three slots per cell",
          "%r" % (words is None or len(words),))
    if words is not None:
        want_faces = sum(1 for i in range(exp.cells) for s in (1, 2)
                         if words[i * 3 + s] != 0xFFFF)
        want_rot = sum(1 for i in range(exp.cells) for s in (1, 2)
                       if words[i * 3 + s] != 0xFFFF
                       and words[i * 3 + s] & 0x8000)
        want_cells = sum(1 for i in range(exp.cells)
                         if words[i * 3 + 1] != 0xFFFF)
        check(tbl.get("state") == "bound"
              and tbl.get("overlay_faces") == want_faces
              and tbl.get("cells_blended") == want_cells
              and tbl.get("rotated_faces") == want_rot,
              "Blender's overlay geometry is exactly the sidecar's non-base "
              "layers -- %d faces over %d cells, %d rotated"
              % (want_faces, want_cells, want_rot),
              "%r" % ({k: tbl.get(k) for k in
                       ("state", "overlay_faces", "cells_blended",
                        "rotated_faces")},))
        # The base quadrant must not be stuck at 0 any more: T5 pinned every
        # cell to quadrant 0 and that is precisely the repetition T6 removes.
        check(sorted(set(tt.get("base_quadrants") or [])) == [0, 1, 2, 3],
              "all four base quadrants are in use, so the ground no longer "
              "repeats one variant per tile type",
              "%r" % (tt.get("base_quadrants"),))

    # ---- tag 9's baked lightmap, against the sidecar ----------------------
    # The attribute is per VERTEX because tag 9 shares tag 1's grid and
    # those samples are cell CORNERS, so its lattice must be the mesh's and
    # its statistics must be the sidecar's own -- computed here, including
    # the far-edge replication, and never taken from the importer.
    lm = tt.get("lightmap") or {}
    want_n = (exp.dim_x + 1) * (exp.dim_y + 1)
    dx, dy = exp.dim_x, exp.dim_y
    lattice = []
    for gy in range(dy):
        rowv = list(exp.shade[gy * dx:(gy + 1) * dx])
        lattice.extend(rowv + [rowv[-1]])
    lattice.extend(lattice[-(dx + 1):])
    want_mean = sum(lattice) / len(lattice) / 255.0
    check(lm.get("state") == "attached" and lm.get("vertices") == want_n,
          "the lightmap is attached to every vertex of the lattice (%d), not "
          "per face -- tag 9 shares tag 1's corner grid" % want_n,
          "%r" % ({k: lm.get(k) for k in ("state", "vertices")},))
    check(abs((lm.get("mean") or 0) - want_mean) < 1e-3,
          "and its mean equals the shade sidecar's own, replicated edge "
          "included (%.4f)" % want_mean, "%r" % (lm.get("mean"),))
    # It has to actually VARY, or multiplying it in changes nothing and the
    # checks above would pass over a uniform white attribute.
    check((lm.get("max") or 0) - (lm.get("min") or 0) > 0.5,
          "the bake spans a real range, so multiplying it in is visible",
          "%r..%r" % (lm.get("min"), lm.get("max")))

    # THE LIGHTMAP CONTROL: --no-lightmap must leave the ground unlit.
    workl = os.path.join(tmp, "run_real_lmctl")
    os.makedirs(workl, exist_ok=True)
    rc, _out, s4, _v = run_blender(blender, src, workl,
                                   extra=["--no-props", "--no-lightmap"])
    lm2 = ((s4 or {}).get("terrain_textures") or {}).get("lightmap") or {}
    check(rc == 0 and lm2.get("state") == "skipped",
          "--no-lightmap leaves tag 9 unapplied and says so",
          "rc=%d, %r" % (rc, lm2))

    # THE T6 CONTROL: --no-blend must drop the overlays and keep the base.
    workb = os.path.join(tmp, "run_real_t6ctl")
    os.makedirs(workb, exist_ok=True)
    rc, _out, s3, _v = run_blender(blender, src, workb,
                                   extra=["--no-props", "--no-blend"])
    check(rc == 0 and s3 is not None
          and (s3.get("terrain_blend") or {}).get("state") == "skipped"
          and (s3.get("terrain_textures") or {}).get("state") == "bound",
          "--no-blend draws the base layer alone and says so, while the "
          "ground stays textured",
          "rc=%d, %r" % (rc, s3 and s3.get("terrain_blend")))

    # THE FLAG CONTROL on the real map, terrain only for speed.
    work = os.path.join(tmp, "run_real_t5ctl")
    os.makedirs(work, exist_ok=True)
    rc, _out, s2, _v = run_blender(blender, src, work,
                                   extra=["--no-props",
                                          "--no-terrain-textures"])
    check(rc == 0 and s2 is not None
          and s2.get("terrain_textures", {}).get("state") == "skipped",
          "--no-terrain-textures leaves the real ground unmaterialed",
          "rc=%d, state %r" % (rc, s2 and s2.get("terrain_textures")))


def _ground_of(o, exp, zmap):
    gy = int((exp.rect[3] - o["location"][1]) / CELL_PITCH)
    gx = int((o["location"][0] - exp.rect[0]) / CELL_PITCH)
    if not (0 <= gx < exp.dim_x and 0 <= gy < exp.dim_y):
        return float("inf")
    g = zmap.get((f32(exp.rect[0] + gx * CELL_PITCH),
                  f32(exp.rect[3] - gy * CELL_PITCH)))
    return float("inf") if g is None else g


if __name__ == "__main__":
    sys.exit(main())
