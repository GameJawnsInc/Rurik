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
     stored**, not by a lattice index, then compare with the prop's `z`. Neither
     `mapexport.py` nor `import_gwmap.py` reads that chunk, and nothing in this
     pipeline produced it, so a flipped row order, a wrong pitch or a lost
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

SECTIONS 0 TO 2 NEED NO VAULT and build their fixture from nothing. Section 3
needs `vault/dat_study/Gw.dat`, declares a skip naming the path when it is
absent, and the floor then fails the run -- because the synthetic half cannot
refute anything about ArenaNet's bytes.
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
from mapexport import (build_manifest, export_row, load_export,  # noqa: E402
                       write_export)
# The prop oracle's chunk walk, its pinned populations and its measured
# fractions live in `test_mapexport.py` and are imported rather than copied. One
# copy of a measured constant is the point: if that file's oracle is ever
# re-measured, the prediction below moves with it instead of quietly disagreeing.
from test_mapexport import (ORACLE, PROPS_CHUNK, PRESEARING_DIMS,  # noqa: E402
                            PRESEARING_FILE_ID, PRESEARING_PROPS,
                            PRESEARING_RECT, PRESEARING_ROW, PROPS_VERSION,
                            read_chunks, read_props, synthetic_terrain,
                            SYN_X, SYN_Y)
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

# FLOOR: 74, from a real green run on `vault/dat_study/Gw.dat` with Blender
# 5.1.1, 2026-08-11 (13.8 s). Sections 0-2 alone score 39 -- MEASURED by
# running with `--dat` pointed at nothing, not counted by eye -- so a run with no
# archive lands 35 short and goes RED. That is deliberate: a
# mesh built from a grid this file invented has verified the plumbing and
# NOTHING about ArenaNet's layout, and a green exit code there would be
# `test_codec.py`'s silent-success failure again.
#
# It was 69 until section 0 landed. Section 0 is five checks on the install
# SELECTOR rather than on a mesh, and it exists because the selector silently
# fell through a bad `--blender` to the known install: a run that asked for one
# Blender measured another and printed ALL CHECKS PASSED (69 checks).
FLOOR = 74


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


def run_blender(blender, json_path, workdir, verts=False, timeout=BLENDER_TIMEOUT):
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
        dz.append(abs(z - wz))
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
    check((bmin[2], bmax[2]) == (lo, hi),
          "%s: z spans the stored heights, un-negated" % tag,
          "%r..%r vs %r..%r" % (bmin[2], bmax[2], lo, hi))

    # The four lattice corners, by name. Row 0 is world maxY, so j=0 is north.
    corners = exp.corner_heights()
    stride = dx + 1
    want = {"nw": (0, 0), "ne": (dx, 0), "sw": (0, dy), "se": (dx, dy)}
    bad = []
    for name, (i, j) in want.items():
        got = summary["corners"][name]
        wx, wy = exp.world_at(i, j)
        if (got["x"], got["y"], got["z"]) != (wx, wy, corners[j * stride + i]):
            bad.append((name, got))
    check(not bad, "%s: all four lattice corners carry the world position and "
                   "height the interchange says" % tag,
          "%r" % bad if bad else "nw/ne/sw/se")

    # EVERY vertex, through the digests, rather than the handful printed above.
    xs, ys, zs = expected_lattice(exp)
    check(summary["digest_x"] == f32_digest(xs),
          "%s: all %d vertex x agree with x0 + i*pitch"
          % (tag, len(xs)))
    check(summary["digest_y"] == f32_digest(ys),
          "%s: all %d vertex y agree with y1 - j*pitch (row 0 is maxY)"
          % (tag, len(ys)))
    check(summary["digest_z"] == f32_digest(zs),
          "%s: all %d vertex z are the stored heights with the client's "
          "replicated far edge" % (tag, len(zs)))

    probes = summary["probes"]
    off = [p for p in probes
           if (p["x"], p["y"], p["z"])
           != (exp.world_at(p["i"], p["j"])[0], exp.world_at(p["i"], p["j"])[1],
               corners[p["j"] * stride + p["i"]])]
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
    dx, dy = SYN_X, SYN_Y
    trn = synthetic_terrain(dx, dy)
    # A rect that is NOT centred on the origin and whose y0 is not -y1, so a sign
    # error or a swapped pair cannot come out looking right by symmetry.
    rect = (-1536.0, -3072.0, dx * CELL_PITCH - 1536.0, dy * CELL_PITCH - 3072.0)
    meta, payloads = build_manifest(trn, rect, "synthetic",
                                    {"archive": None, "row": None,
                                     "file_id": None})
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
        check(summary_flip["digest_z"] != f32_digest(zs),
              "ROW CONTROL: the z digest changes when the rows are reversed")
        check(summary_flip["digest_x"] == f32_digest(xs) and
              summary_flip["digest_y"] == f32_digest(ys),
              "ROW CONTROL: x and y are untouched -- only the heights moved")
        check(summary_flip["corners"]["nw"]["z"] != exp.heights[0],
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
    return {"min": [x0, y0, min(exp.heights)], "max": [x1, y1, max(exp.heights)]}


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
    print("   props chunk 0x%08X -- read by neither the exporter nor the "
          "importer\n" % PROPS_CHUNK)

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
    rc, out, summary, verts = run_blender(blender, src, work, verts=True)
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


if __name__ == "__main__":
    sys.exit(main())
