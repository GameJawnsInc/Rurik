"""Author terrain IN Blender and bring it back: the round trip through a .blend.

    python toolkit/mapdata/test_blenderroundtrip.py
    python toolkit/mapdata/test_blenderroundtrip.py --blender "C:\\...\\blender.exe"

`test_blenderimport.py` proved Blender builds the mesh the interchange
describes. This is the other direction and the one that makes the pipeline an
AUTHORING tool rather than a viewer: a mesh is saved to a `.blend`, a SEPARATE
Blender process opens that file, and `tools/blender/export_gwmap.py` writes an
interchange back out. Two processes, not one scene -- because a round trip
inside a single session proves the two functions are inverses and says nothing
about whether the `.blend` carried anything.

WHY AN IDENTITY ROUND TRIP IS NOT ENOUGH, AND WHAT IS ADDED. Heights out equal
to heights in is satisfied by a memcpy, and this was RUN rather than reasoned
about. The sabotage: `import_gwmap._stamp` also stashes the height array on the
object, and the exporter prefers it when present. That tool reads no vertex and
understands nothing, and it keeps ALL SIX byte-identity checks GREEN -- including
ArenaNet's own 851,968 bytes in section 5. Exactly two checks catch it, both in
section 2 and 3's edit path. (`_stamp` strips the `sidecars` block for this
reason, so the sabotage takes a deliberate edit to both scripts; the point is
that the identity result cannot tell the difference.) Three things carry the file
past that, and they are the point of it.

  1. **SECTION 2 SCULPTS.** One vertex is moved in Blender by a literal +250.0,
     and the export must show EXACTLY that cell moved, by EXACTLY -250.0 in the
     stored convention, with every other cell and both other sidecars untouched.
     A stamp-replaying exporter fails this and nothing else, which is why it is
     the first thing after the identity check rather than an afterthought.
  2. **SECTION 5's ANCHOR IS ARENANET'S.** The real-map round trip compares
     against the sidecar `mapexport.py` wrote out of `Gw.dat` through
     `terrain.py` -- a module neither Blender script imports and a decode path
     neither has any say in. Sections 1 and 2 are ours against ours.
  3. **SECTION 4 STARTS FROM NOTHING.** A mesh built in Blender by a script with
     no stamp at all, exported, and then assembled by `mapbuild.py` into a whole
     map file whose terrain chunk decodes back to the heights that were
     authored. Nothing is carried because there is nothing to carry.

THE THREE REFUSALS IN SECTION 3 ARE THINGS TERRAIN CANNOT EXPRESS, and each is
a real way to lose a human's work silently.

    a vertex dragged 40 units in x     leaves its column: the lattice does not fill
    a vertex nudged 0.5 units in x     STAYS in its column: only the residual sees it
    a far-edge vertex holding a value  the file has nowhere to put it

The first two are one defect at two magnitudes and they are caught by two
different checks -- `CLUSTER_TOL` groups vertices into columns and cannot see a
sub-tolerance nudge, `LATTICE_TOL` measures accuracy against the derived grid
and never runs if the clustering already refused. A version of this test with
only the 40-unit case would pass an exporter that dropped the residual check
entirely, and a half-unit displacement would export as though it were not
there. Both bands, or the pair is decoration.

The third is checked from BOTH of its causes, because the count is named for its
effect. Sculpting the far edge puts a vertex on the unstorable list and the
stored heights come back IDENTICAL -- the drop happened. Sculpting the last REAL
column beside it puts a vertex on the same list and the stored heights CHANGE --
the human edited something storable and the edge merely stopped matching. One
number, two meanings, and an exporter that conflated them would report the wrong
thing about a legitimate edit.

NO BLENDER, NO RUN -- the whole file skips loudly and goes RED, the same as
`test_blenderimport.py`, whose install selector is imported rather than copied
so the two cannot drift. SECTIONS 0 TO 4 NEED NO VAULT. Section 5 needs
`vault/dat_study/Gw.dat` and declares a skip naming the path when it is absent,
and the floor then fails the run -- a round trip on a grid this file invented
has verified the plumbing and nothing about ArenaNet's bytes.
"""

import argparse
import hashlib
import json
import os
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
                       retile, write_export)
from mapfile import MapFile  # noqa: E402
import mapexport  # noqa: E402
import mapbuild  # noqa: E402
# The Blender selector, its measured version and the exit-code trap, imported
# from the file that established them. One copy of a measured constant: if the
# suite is ever pointed at another install, both Blender tests move together.
from test_blenderimport import (BLENDER_TIMEOUT, MEASURED_BLENDER,  # noqa: E402
                                PYTHON_EXIT_CODE, find_blender)
from test_mapexport import (PRESEARING_DIMS, PRESEARING_FILE_ID,  # noqa: E402
                            PRESEARING_RECT, PRESEARING_ROW,
                            synthetic_terrain, SYN_X, SYN_Y)
from test_mapbuild import placeholder_constants  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
IMPORTER = os.path.join(REPO_ROOT, "tools", "blender", "import_gwmap.py")
EXPORTER = os.path.join(REPO_ROOT, "tools", "blender", "export_gwmap.py")

# The sculpt, and every number in it is a literal on purpose. The prediction is
# `stored_after == stored_before - SCULPT_DZ`, because the importer negates on
# the way in and the exporter negates back (FINDINGS 25): raising a vertex in
# Blender LOWERS its stored value. A test that computed this expectation from
# the exporter's own `stored_z` would move with a sign flip and stay green.
SCULPT_I, SCULPT_J = 5, 7
SCULPT_DZ = 250.0

# The two displacement bands -- see the module docstring. 40.0 is larger than
# the exporter's CLUSTER_TOL of 1.0 and so forms a column of its own; 0.5 is
# smaller than it and so does not, and is caught only by the residual against
# LATTICE_TOL (0.0625).
MOVE_OUT_OF_COLUMN = 40.0
MOVE_WITHIN_COLUMN = 0.5

# Section 4's authored hill: `z = ((i*7 + j*13) % 97) * 4`. Integer-valued so
# every height is exactly representable as float32 and the comparison is exact
# rather than tolerance-based. AUTHORED_PROBE is that formula evaluated at
# (3, 4) BY HAND -- (3*7 + 4*13) = 73, 73 * 4 = 292, negated by the export -- so
# one value in the section is pinned to a literal instead of to a second copy of
# the formula. Every other check there recomputes it, which is transport.
# 32x32 because the loader caps dims at multiples of 32 and `retile` gates on
# it. 16 was the first value here and `mapexport.retile` refused it, which is
# the gate working: an authored map that could never be assembled is not a
# demonstration of anything.
AUTHORED_X, AUTHORED_Y = 32, 32
AUTHORED_PROBE_IJ = (3, 4)
AUTHORED_PROBE_STORED = -292.0

# FLOOR: 94, from a real green run on vault/dat_study/Gw.dat with Blender
# 5.1.1, 2026-08-14 (was 79). Sections 0-4 alone score 67 -- UNCHANGED by
# section 6, which is vault-gated, so the vault-less shortfall grew from 12 to
# 27. 79 -> 94 is the PROPS round trip: import a retail map's 864 props into
# Blender, export them back, and require the sidecar to match -- then EDIT two
# of them and require exactly those two records to move.
#
# The old comment said sections 0-4 score 67 -- MEASURED by
# running with --dat pointed at nothing, not counted by eye, and the first guess
# written here was 56 -- so a vault-less run lands 12 short and goes RED. That is
# deliberate and it is the rule test_blenderimport.py states: a round trip on a
# grid this file invented has verified the plumbing and refuted nothing about
# ArenaNet's bytes. Only section 5 compares against a sidecar that came out of
# the archive.
#
# 77 -> 79 on 2026-08-13, when props proxies made a crowded scene the normal
# case: the two-mesh refusal split into the unstamped-intruder POSITIVE control
# (the stamp picks the terrain) and the two-stamped-meshes refusal (genuine
# ambiguity still refuses).
#: Which props section 6 edits. Two DIFFERENT ones, so 'moved' and
#: 'rotated' cannot both be satisfied by a single record changing.
MOVE_INDEX = 7
ROTATE_INDEX = 11

FLOOR = 94


# ------------------------------------------------------------------ helpers

def _argv_preamble():
    """The `--` argument split, copied into every script this file writes.

    These scripts run inside Blender's interpreter, which cannot import
    anything from this repository, so they carry their own three lines.
    """
    return ("import argparse, sys\n"
            "import bpy\n"
            "def _argv():\n"
            "    a = list(sys.argv[1:])\n"
            "    return a[a.index('--') + 1:] if '--' in a else a\n")


EDIT_SCRIPT = _argv_preamble() + '''
ap = argparse.ArgumentParser()
ap.add_argument("--blend", required=True)
ap.add_argument("--save", required=True)
ap.add_argument("--at", default=None)          # "x,y" of the vertex to touch
ap.add_argument("--dz", type=float, default=0.0)
ap.add_argument("--dx", type=float, default=0.0)
ap.add_argument("--duplicate", action="store_true")
ap.add_argument("--duplicate-stamped", action="store_true")
args = ap.parse_args(_argv())

bpy.ops.wm.open_mainfile(filepath=args.blend)
obj = [o for o in bpy.data.objects if o.type == "MESH"][0]

if args.at:
    # BY POSITION, never by index -- the same rule the exporter follows. A test
    # helper that reached for vertices[k] would share its row convention with
    # the code under test and could not tell a correctly placed mesh from a
    # transposed one.
    tx, ty = [float(v) for v in args.at.split(",")]
    best, bd = None, None
    for v in obj.data.vertices:
        d = (v.co.x - tx) ** 2 + (v.co.y - ty) ** 2
        if bd is None or d < bd:
            best, bd = v, d
    print("EDIT_FOUND index=%d at (%r, %r, %r) dist2=%r"
          % (best.index, best.co.x, best.co.y, best.co.z, bd))
    best.co.z += args.dz
    best.co.x += args.dx
    print("EDIT_NOW (%r, %r, %r)" % (best.co.x, best.co.y, best.co.z))
    obj.data.update()

if args.duplicate:
    m = bpy.data.meshes.new("intruder")
    m.from_pydata([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)], [],
                  [(0, 1, 2)])
    m.update()
    bpy.context.scene.collection.objects.link(
        bpy.data.objects.new("intruder", m))

if args.duplicate_stamped:
    # obj.copy() copies custom properties, so the duplicate carries the STAMP
    # too -- which is what makes it genuine ambiguity where the intruder above
    # is not.
    dup = obj.copy()
    dup.data = obj.data.copy()
    bpy.context.scene.collection.objects.link(dup)

bpy.ops.wm.save_as_mainfile(filepath=args.save)
print("EDIT_SAVED %s" % args.save)
'''

AUTHOR_SCRIPT = _argv_preamble() + '''
ap = argparse.ArgumentParser()
ap.add_argument("--save", required=True)
ap.add_argument("--nx", type=int, required=True)      # CELLS, not vertices
ap.add_argument("--ny", type=int, required=True)
ap.add_argument("--pitch", type=float, default=96.0)
ap.add_argument("--x0", type=float, default=0.0)
ap.add_argument("--y1", type=float, default=0.0)
args = ap.parse_args(_argv())

for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

nx, ny, pitch = args.nx, args.ny, args.pitch
stride = nx + 1

# The height a human is authoring. Integer-valued so every value is exactly
# representable as float32 and the round trip can be asserted byte-for-byte.
def h(i, j):
    return float(((i * 7 + j * 13) % 97) * 4)

# THE FAR EDGE IS AUTHORED AS A REPLICATION OF ITS NEIGHBOUR, deliberately. The
# file holds nx*ny samples and the client manufactures the extra column and row
# by copying theirs (FINDINGS 17.4), so a far edge holding anything else is a
# value that will change the next time the map is read. The exporter reports
# that rather than refusing it, and section 3 checks the report -- here the aim
# is a clean export, so the mesh is authored the way the format can keep.
def z(i, j):
    return h(min(i, nx - 1), min(j, ny - 1))

verts = []
for j in range(ny + 1):
    wy = args.y1 - j * pitch
    for i in range(stride):
        verts.append((args.x0 + i * pitch, wy, z(i, j)))

faces = []
for j in range(ny):
    a = j * stride
    b = a + stride
    for i in range(nx):
        faces.append((a + i, b + i, b + i + 1, a + i + 1))

mesh = bpy.data.meshes.new("authored")
mesh.from_pydata(verts, [], faces)
mesh.update()
bpy.context.scene.collection.objects.link(bpy.data.objects.new("authored", mesh))
bpy.ops.wm.save_as_mainfile(filepath=args.save)
print("AUTHOR_SAVED %s  %d verts, %d faces" % (args.save, len(verts), len(faces)))
'''


def run_blender(blender, script, args, timeout=BLENDER_TIMEOUT):
    """`(rc, output)` from one headless Blender run. Never raises on failure."""
    cmd = [blender, "--background", "--factory-startup",
           "--python-exit-code", str(PYTHON_EXIT_CODE),
           "--python", script, "--"] + [str(a) for a in args]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          errors="replace")
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def do_import(blender, json_path, blend_out, dump=None):
    args = [json_path, "--clear", "--out", blend_out]
    if dump:
        args += ["--dump", dump]
    rc, out = run_blender(blender, IMPORTER, args)
    summary = None
    if dump and os.path.isfile(dump):
        with open(dump, "r", encoding="utf-8") as fh:
            summary = json.load(fh)
    return rc, out, summary


def do_export(blender, blend, outdir, name, extra=()):
    """Run the exporter. Returns `(rc, output, manifest or None)`."""
    dump = os.path.join(outdir, "manifest.json")
    if os.path.exists(dump):
        os.remove(dump)
    args = ["--blend", blend, "--out", outdir, "--name", name, "--dump", dump]
    rc, out = run_blender(blender, EXPORTER, args + list(extra))
    meta = None
    if os.path.isfile(dump):
        with open(dump, "r", encoding="utf-8") as fh:
            meta = json.load(fh)
    return rc, out, meta


def sidecar(json_path, kind):
    """One sidecar's raw bytes, by kind, from an interchange on disk."""
    with open(json_path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    base = os.path.dirname(os.path.abspath(json_path))
    for side in meta["sidecars"]:
        if side["kind"] == kind:
            with open(os.path.join(base, side["name"]), "rb") as sh:
                return sh.read()
    return None


def heights_of(json_path):
    blob = sidecar(json_path, "heights")
    return list(struct.unpack("<%df" % (len(blob) // 4), blob)) if blob else None


def differing(a, b):
    """Indices where two float lists disagree. `None` when the lengths do."""
    if a is None or b is None or len(a) != len(b):
        return None
    return [k for k in range(len(a)) if a[k] != b[k]]


def out_json(outdir, name):
    return os.path.join(outdir, "%s.gwmap.json" % name)


def compare_sidecar(was, now, kind):
    """`(equal, detail)` -- and when bytes differ, say whether the VALUES do.

    The distinction earned its place on 2026-08-12. The first green-looking run
    of this file had exactly one of 6,144 heights disagree, `00000000` against
    `00000080`: the same number, opposite signed zero, from an identity
    `matrix_world` multiply where `-0.0 * 1.0 + 0.0` is `+0.0`. A bare digest
    comparison says "the heights are wrong" and sends a reader looking at the
    de-tiling; this says "1 byte-differs, 0 value-differs", which names the
    class of defect immediately. A tolerance would have hidden it altogether.
    """
    if was is None or now is None:
        return False, "%s missing (%r / %r)" % (kind, was is None, now is None)
    if was == now:
        return True, "%d bytes, sha %s" % (len(was),
                                           hashlib.sha256(was).hexdigest()[:16])
    if len(was) != len(now):
        return False, "%d bytes vs %d" % (len(was), len(now))
    byte_diff = sum(1 for k in range(0, len(was), 4)
                    if was[k:k + 4] != now[k:k + 4])
    detail = "%d of %d words byte-differ" % (byte_diff, len(was) // 4)
    if kind == "heights":
        n = len(was) // 4
        a = struct.unpack("<%df" % n, was)
        b = struct.unpack("<%df" % n, now)
        value_diff = sum(1 for k in range(n) if a[k] != b[k])
        detail += ", %d differ in VALUE (0 means signed zero or another " \
                  "bit-pattern difference, not a wrong height)" % value_diff
    return False, detail


# --------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blender", default=None)
    ap.add_argument("--dat", default=None)
    args = ap.parse_args(argv)

    led = checks.Ledger("blender round trip", floor=FLOOR)
    check = checks.adopt(led)
    t0 = time.perf_counter()

    blender, why = find_blender(args.blender)
    if blender is None:
        led.skip("all sections", why)
        return led.verdict()
    print("blender: %s   (%s)" % (blender, why))

    with tempfile.TemporaryDirectory(prefix="rurik_rt_") as tmp:
        edit = os.path.join(tmp, "edit.py")
        author = os.path.join(tmp, "author.py")
        with open(edit, "w", encoding="utf-8") as fh:
            fh.write(EDIT_SCRIPT)
        with open(author, "w", encoding="utf-8") as fh:
            fh.write(AUTHOR_SCRIPT)

        _section0(check, blender)
        base = _section1(check, led, blender, tmp)
        _section2(check, led, blender, tmp, base, edit)
        _section3(check, led, blender, tmp, base, edit)
        _section4(check, led, blender, tmp, author)
        _section5(check, led, blender, tmp, args)
        _section6(check, led, blender, tmp, args)

    print("\n(%.1fs)" % (time.perf_counter() - t0))
    return led.verdict()


# --- 0. both halves of the pipeline exist ----------------------------------

def _section0(check, blender):
    print("\n== 0. the two scripts ==")
    check(os.path.isfile(IMPORTER), "the importer is at %s"
          % os.path.relpath(IMPORTER, REPO_ROOT))
    check(os.path.isfile(EXPORTER), "the exporter is at %s"
          % os.path.relpath(EXPORTER, REPO_ROOT))


# --- 1. the identity round trip, through a .blend, in two processes ---------

def _section1(check, led, blender, tmp):
    print("\n== 1. interchange -> .blend -> a SEPARATE Blender -> interchange "
          "(no vault) ==")
    trn = synthetic_terrain(SYN_X, SYN_Y)
    # A rect that is neither centred on the origin nor symmetric in y, so a sign
    # error or a swapped pair cannot come out looking right by accident.
    rect = (-1536.0, -3072.0, SYN_X * CELL_PITCH - 1536.0,
            SYN_Y * CELL_PITCH - 3072.0)
    meta, payloads = build_manifest(trn, rect, "synthetic",
                                    {"archive": None, "row": None,
                                     "file_id": None})
    src = write_export(meta, payloads, os.path.join(tmp, "syn"))
    exp = load_export(src)
    check(len(set(exp.heights)) == exp.cells,
          "the fixture's %d heights are all distinct, so a transposed or "
          "shifted grid cannot round trip by coincidence" % exp.cells,
          "%d distinct" % len(set(exp.heights)))

    blend = os.path.join(tmp, "scene.blend")
    dump = os.path.join(tmp, "import.json")
    rc, out, summary = do_import(blender, src, blend, dump=dump)
    check(rc == 0, "the import runs", "rc=%d %s" % (rc, out.strip()[-160:]))
    check(os.path.isfile(blend) and os.path.getsize(blend) > 4096,
          "a .blend was written", "%d bytes" % (os.path.getsize(blend)
                                                if os.path.isfile(blend) else 0))
    if summary is None or rc != 0:
        led.skip("1. the round trip", "the import produced nothing to export")
        return None

    check(summary["blender"].split(".")[0] == MEASURED_BLENDER.split(".")[0],
          "the Blender that ran is major version %s, as measured"
          % MEASURED_BLENDER.split(".")[0], summary["blender"])
    # The stamp is what carries everything a lattice of vertices cannot. If it
    # stops being written the failure surfaces HERE, on the way in, rather than
    # as a silently missing tile table on the way out.
    for key in ("tile_table_a", "tile_table_b", "tag_sequence",
                "terrain_tag0"):
        check(key in summary["stamp_keys"],
              "the import stamps %s onto the object" % key,
              ",".join(summary["stamp_keys"])[:120])

    outdir = os.path.join(tmp, "back")
    rc, out, back = do_export(blender, blend, outdir, "synthetic")
    check(rc == 0, "a separate Blender process exports it back",
          "rc=%d %s" % (rc, out.strip()[-200:]))
    if back is None:
        led.skip("1. the round trip", "the export wrote no manifest")
        return None

    a = back["authored"]
    check((back["dims"]["x"], back["dims"]["y"]) == (exp.dim_x, exp.dim_y),
          "the dims come back %dx%d, RE-DERIVED from the mesh rather than read "
          "from the stamp" % (exp.dim_x, exp.dim_y),
          "%rx%r" % (back["dims"]["x"], back["dims"]["y"]))
    r = back["map_rect"]
    check((r["x0"], r["y0"], r["x1"], r["y1"]) == exp.rect,
          "and the map rect is the one the mesh spans", "%r" % (r,))
    check(back["cell_pitch"] == CELL_PITCH,
          "and the pitch measures %r" % CELL_PITCH, "%r" % back["cell_pitch"])
    check(a["lattice_residual"] == 0.0,
          "every vertex sits EXACTLY on the regular lattice",
          "worst %r" % a["lattice_residual"])
    check(a["manufactured_edge_unstorable"] == 0,
          "and nothing on the manufactured far edge is unstorable -- the "
          "replication survived the trip intact",
          "%d" % a["manufactured_edge_unstorable"])
    check(not a["stamp_disagreements"],
          "the re-derived geometry agrees with the stamp on all three of dims, "
          "rect and pitch", "%r" % (a["stamp_disagreements"],))
    check(a["stamped"] is True, "and the stamp was found on the object")

    dst = out_json(outdir, "synthetic")
    for kind in ("heights", "tiles", "shade"):
        same, detail = compare_sidecar(sidecar(src, kind), sidecar(dst, kind),
                                       kind)
        check(same, "the %s sidecar comes back BYTE-IDENTICAL" % kind, detail)

    # The metadata a mesh cannot hold, carried through the .blend and back.
    with open(src, "r", encoding="utf-8") as fh:
        first = json.load(fh)
    for key in ("tile_table_a", "tile_table_b", "tag_sequence",
                "terrain_tag0"):
        check(back.get(key) == first.get(key),
              "%s survives the round trip through the .blend" % key,
              "%r vs %r" % (str(back.get(key))[:40], str(first.get(key))[:40]))

    # The export's own manifest against the files it wrote: a digest that
    # described something else would make every later comparison meaningless.
    bad = [s["name"] for s in back["sidecars"]
           if hashlib.sha256(open(os.path.join(outdir, s["name"]),
                                  "rb").read()).hexdigest() != s["sha256"]]
    check(not bad, "and the export's own sha256s describe the bytes it wrote",
          "%r" % bad if bad else "%d sidecars" % len(back["sidecars"]))
    return {"src": src, "blend": blend, "exp": exp, "dst": dst}


# --- 2. THE SCULPT: the control an identity round trip cannot survive -------

def _section2(check, led, blender, tmp, base, edit):
    print("\n== 2. THE SCULPT -- one vertex moved IN Blender, by a literal ==")
    if base is None:
        led.skip("2. the sculpt", "section 1 built no .blend")
        return
    exp = base["exp"]
    dx = exp.dim_x
    wx, wy = exp.world_at(SCULPT_I, SCULPT_J)
    cell = SCULPT_J * dx + SCULPT_I
    print("   vertex (%d, %d) at world (%r, %r) -> cell index %d"
          % (SCULPT_I, SCULPT_J, wx, wy, cell))

    sculpted = os.path.join(tmp, "sculpted.blend")
    rc, out = run_blender(blender, edit,
                          ["--blend", base["blend"], "--save", sculpted,
                           "--at=%r,%r" % (wx, wy), "--dz", SCULPT_DZ])
    check(rc == 0 and "EDIT_SAVED" in out, "Blender moved the vertex and saved",
          "rc=%d %s" % (rc, out.strip()[-160:]))
    found = [ln for ln in out.splitlines() if ln.startswith("EDIT_FOUND")]
    check(bool(found) and "dist2=0.0" in found[0],
          "and it found the vertex EXACTLY at the world position asked for, so "
          "the cell below is the one that was edited",
          found[0][:120] if found else "no EDIT_FOUND line")

    outdir = os.path.join(tmp, "back_sculpt")
    rc, out, meta = do_export(blender, sculpted, outdir, "synthetic")
    check(rc == 0 and meta is not None, "the sculpted mesh exports",
          "rc=%d %s" % (rc, out.strip()[-200:]))
    if meta is None:
        led.skip("2. the sculpt", "no manifest")
        return

    before = heights_of(base["dst"])
    after = heights_of(out_json(outdir, "synthetic"))
    moved = differing(before, after)
    check(moved == [cell],
          "EXACTLY one stored height changed, and it is cell %d -- vertex "
          "(%d, %d)" % (cell, SCULPT_I, SCULPT_J),
          "changed: %r" % (moved[:8] if moved else moved))
    if moved == [cell]:
        # THE PREDICTION, and both numbers in it are literals. Raising a vertex
        # in Blender by +250.0 must LOWER the stored value by 250.0, because the
        # importer negates in and the exporter negates back (FINDINGS 25). An
        # exporter that dropped the negation round-trips section 1 perfectly and
        # fails only here.
        check(after[cell] == before[cell] - SCULPT_DZ,
              "and it moved by exactly -%r: raising a vertex in Blender LOWERS "
              "its stored height (FINDINGS 25)" % SCULPT_DZ,
              "%r -> %r (delta %r)" % (before[cell], after[cell],
                                       after[cell] - before[cell]))
    check(sidecar(base["dst"], "tiles") == sidecar(out_json(outdir, "synthetic"),
                                                   "tiles")
          and sidecar(base["dst"], "shade") == sidecar(
              out_json(outdir, "synthetic"), "shade"),
          "the tile and shade sidecars are untouched -- only the height moved")
    check(meta["authored"]["manufactured_edge_unstorable"] == 0,
          "and an interior sculpt costs nothing on the far edge",
          "%d" % meta["authored"]["manufactured_edge_unstorable"])


# --- 3. what the exporter must refuse or report ----------------------------

def _section3(check, led, blender, tmp, base, edit):
    print("\n== 3. the refusals: things a height field cannot express ==")
    if base is None:
        led.skip("3. the refusals", "section 1 built no .blend")
        return
    exp = base["exp"]
    dx, dy = exp.dim_x, exp.dim_y
    baseline = heights_of(base["dst"])

    # (a) OUT OF ITS COLUMN. 40 units is far past the exporter's clustering
    # tolerance, so the vertex forms a column of its own and the lattice stops
    # filling. Caught by the count, never reaching the residual check.
    wx, wy = exp.world_at(SCULPT_I, SCULPT_J)
    moved = os.path.join(tmp, "moved_far.blend")
    rc, _out = run_blender(blender, edit,
                           ["--blend", base["blend"], "--save", moved,
                            "--at=%r,%r" % (wx, wy),
                            "--dx", MOVE_OUT_OF_COLUMN])
    # THE PRECONDITION, AND IT IS NOT BOOKKEEPING. The first run of this file
    # had a broken `--at` and never wrote these .blend files -- so the two
    # refusal checks below went GREEN on exit 66 meaning "no such file". A
    # refusal control has to fail for its own reason, and there are two ways to
    # know it did: this, and the message check paired with each rc.
    check(rc == 0 and os.path.isfile(moved),
          "the %r-unit x move was applied AND saved" % MOVE_OUT_OF_COLUMN,
          "rc=%d, .blend %s" % (rc, "written" if os.path.isfile(moved)
                                else "MISSING -- the refusal below would be "
                                     "about a missing file, not geometry"))
    outdir = os.path.join(tmp, "ctl_far")
    os.makedirs(outdir, exist_ok=True)
    rc, out, meta = do_export(blender, moved, outdir, "synthetic")
    check(rc == PYTHON_EXIT_CODE,
          "OFF-LATTICE (%r units): REFUSED with exit %d" % (MOVE_OUT_OF_COLUMN,
                                                            PYTHON_EXIT_CODE),
          "rc=%d" % rc)
    check(meta is None and not os.path.isfile(out_json(outdir, "synthetic")),
          "and no interchange is written, so nothing downstream can read a "
          "refused export as a completed one")
    check("regular" in out.lower() or "lattice" in out.lower(),
          "and the refusal says the mesh is not a regular grid",
          out.strip()[-160:])

    # (b) WITHIN ITS COLUMN. Half a unit keeps the vertex in its cluster, so the
    # count check above cannot see it. This is the band that only the residual
    # covers, and without it a sub-tolerance displacement exports silently.
    nudged = os.path.join(tmp, "nudged.blend")
    rc, _out = run_blender(blender, edit,
                           ["--blend", base["blend"], "--save", nudged,
                            "--at=%r,%r" % (wx, wy),
                            "--dx", MOVE_WITHIN_COLUMN])
    check(rc == 0 and os.path.isfile(nudged),
          "the %r-unit x nudge was applied AND saved" % MOVE_WITHIN_COLUMN,
          "rc=%d, .blend %s" % (rc, "written" if os.path.isfile(nudged)
                                else "MISSING"))
    outdir = os.path.join(tmp, "ctl_nudge")
    os.makedirs(outdir, exist_ok=True)
    rc, out, meta = do_export(blender, nudged, outdir, "synthetic")
    check(rc == PYTHON_EXIT_CODE,
          "SUB-TOLERANCE (%r units): REFUSED too -- it stays in its column, so "
          "the lattice still fills and only the residual sees it"
          % MOVE_WITHIN_COLUMN, "rc=%d" % rc)
    check("off the regular lattice" in out,
          "and the refusal names the residual rather than the column count",
          out.strip()[-160:])

    # (c) THE FAR EDGE, CAUSE ONE: the edge itself is sculpted. Reported, not
    # refused -- and the stored heights must come back IDENTICAL, which is what
    # proves the drop actually happened rather than the edit landing in a cell.
    ex, ey = exp.world_at(dx, 3)
    edged = os.path.join(tmp, "edge.blend")
    rc, _out = run_blender(blender, edit,
                           ["--blend", base["blend"], "--save", edged,
                            "--at=%r,%r" % (ex, ey), "--dz", 500.0])
    check(rc == 0, "a far-edge vertex (%d, 3) was sculpted" % dx)
    outdir = os.path.join(tmp, "ctl_edge")
    rc, out, meta = do_export(blender, edged, outdir, "synthetic")
    check(rc == 0 and meta is not None,
          "FAR EDGE: the export still runs -- this is reported, not refused",
          "rc=%d" % rc)
    if meta is not None:
        a = meta["authored"]
        check(a["manufactured_edge_unstorable"] == 1,
              "FAR EDGE: exactly one vertex is named unstorable",
              "%d at %r" % (a["manufactured_edge_unstorable"],
                            a["manufactured_edge_positions"]))
        check(a["manufactured_edge_positions"] == [[dx, 3]],
              "FAR EDGE: and it is the one that was sculpted",
              "%r" % (a["manufactured_edge_positions"],))
        check(heights_of(out_json(outdir, "synthetic")) == baseline,
              "FAR EDGE: the stored heights are IDENTICAL to the baseline -- "
              "the edit was dropped, which is the whole claim")
        check("cannot be stored" in out,
              "FAR EDGE: and the warning says so on stderr", out.strip()[-160:])

    outdir2 = os.path.join(tmp, "ctl_edge_strict")
    os.makedirs(outdir2, exist_ok=True)
    rc, out, meta = do_export(blender, edged, outdir2, "synthetic",
                              extra=["--refuse-unstorable-edge"])
    check(rc == PYTHON_EXIT_CODE and meta is None,
          "FAR EDGE: and --refuse-unstorable-edge makes the same mesh fatal",
          "rc=%d" % rc)

    # (d) THE FAR EDGE, CAUSE TWO: the LAST REAL column is sculpted. The same
    # counter goes to 1, and this time the stored heights MUST change -- the
    # human edited something storable and the edge merely stopped matching it.
    # One number, two meanings; an exporter that conflated them reports the
    # wrong thing about a legitimate edit.
    lx, ly = exp.world_at(dx - 1, 3)
    lastcol = os.path.join(tmp, "lastcol.blend")
    rc, _out = run_blender(blender, edit,
                           ["--blend", base["blend"], "--save", lastcol,
                            "--at=%r,%r" % (lx, ly), "--dz", 500.0])
    check(rc == 0, "the LAST REAL column vertex (%d, 3) was sculpted" % (dx - 1))
    outdir = os.path.join(tmp, "ctl_lastcol")
    rc, out, meta = do_export(blender, lastcol, outdir, "synthetic")
    if meta is not None:
        a = meta["authored"]
        now = heights_of(out_json(outdir, "synthetic"))
        check(a["manufactured_edge_unstorable"] == 1,
              "LAST COLUMN: the same counter reads 1, from the OTHER cause",
              "%d at %r" % (a["manufactured_edge_unstorable"],
                            a["manufactured_edge_positions"]))
        check(differing(baseline, now) == [3 * dx + (dx - 1)],
              "LAST COLUMN: and unlike the far-edge case the stored heights DO "
              "change, in exactly the cell that was edited",
              "changed %r" % (differing(baseline, now) or [])[:8])

    # (e) an UNSTAMPED intruder beside the stamped terrain. Until 2026-08-13
    # ANY second mesh refused; the props proxies made a crowded scene the
    # NORMAL case, so the exporter now picks the terrain by its STAMP --
    # identity, never position in a list. This half is the positive control:
    # the export must succeed and be the terrain (the intruder's three
    # vertices cannot form a lattice, and the dims pin it).
    twinned = os.path.join(tmp, "twinned.blend")
    rc, _out = run_blender(blender, edit,
                           ["--blend", base["blend"], "--save", twinned,
                            "--duplicate"])
    check(rc == 0, "an unstamped intruder mesh was added to the scene")
    outdir = os.path.join(tmp, "ctl_two")
    os.makedirs(outdir, exist_ok=True)
    rc, out, meta = do_export(blender, twinned, outdir, "synthetic")
    check(rc == 0 and meta is not None
          and meta["dims"] == {"x": dx, "y": dy, "cells": dx * dy},
          "INTRUDER: the stamp picks the terrain and the export succeeds",
          "rc=%d, dims %r" % (rc, meta and meta.get("dims")))

    # (e2) TWO STAMPED meshes are genuine ambiguity and must still refuse --
    # picking one by position in a list is how the wrong client got launched
    # on 2026-08-06, and a duplicated terrain copies its stamp.
    stamped2 = os.path.join(tmp, "stamped2.blend")
    rc, _out = run_blender(blender, edit,
                           ["--blend", base["blend"], "--save", stamped2,
                            "--duplicate-stamped"])
    check(rc == 0, "a STAMPED duplicate of the terrain was added")
    outdir2 = os.path.join(tmp, "ctl_two_stamped")
    os.makedirs(outdir2, exist_ok=True)
    rc, out, meta = do_export(blender, stamped2, outdir2, "synthetic")
    check(rc == PYTHON_EXIT_CODE and meta is None,
          "TWO STAMPS: refused rather than exporting whichever comes first",
          "rc=%d" % rc)

    # (f) THE PROVENANCE GATE. mapexport.resolve_outdir is the authority and
    # Blender's interpreter cannot import it, so the exporter reimplements the
    # rule. This asserts the reimplementation refuses the SAME repo root, which
    # is the only thing keeping the two from drifting apart.
    outdir = os.path.join(REPO_ROOT, "toolkit", "mapdata", "_rt_should_refuse")
    rc, out, meta = do_export(blender, base["blend"], outdir, "synthetic")
    check(rc == PYTHON_EXIT_CODE,
          "PROVENANCE: exporting into the working tree is REFUSED",
          "rc=%d" % rc)
    check(not os.path.exists(outdir),
          "PROVENANCE: and the directory was never even created", outdir)


# --- 4. authored in Blender from nothing, and assembled into a map ----------

def _section4(check, led, blender, tmp, author):
    print("\n== 4. a mesh AUTHORED in Blender, with no stamp at all (no vault) ==")
    blend = os.path.join(tmp, "authored.blend")
    rc, out = run_blender(blender, author,
                          ["--save", blend, "--nx", AUTHORED_X,
                           "--ny", AUTHORED_Y, "--pitch", CELL_PITCH,
                           "--x0", 0.0, "--y1", AUTHORED_Y * CELL_PITCH])
    check(rc == 0 and "AUTHOR_SAVED" in out, "Blender built a terrain mesh from "
          "nothing", "rc=%d %s" % (rc, out.strip()[-160:]))
    if rc != 0:
        led.skip("4. the authored map", "the author script failed")
        return

    outdir = os.path.join(tmp, "authored_out")
    rc, out, meta = do_export(blender, blend, outdir, "authored")
    check(rc == 0 and meta is not None, "and it exports with no stamp to carry",
          "rc=%d %s" % (rc, out.strip()[-200:]))
    if meta is None:
        led.skip("4. the authored map", "no manifest")
        return

    a = meta["authored"]
    check(a["stamped"] is False,
          "the manifest says so rather than pretending otherwise -- this mesh "
          "never came from an interchange")
    check((meta["dims"]["x"], meta["dims"]["y"]) == (AUTHORED_X, AUTHORED_Y),
          "the dims are read out of the geometry: %dx%d cells from %dx%d "
          "vertices" % (AUTHORED_X, AUTHORED_Y, AUTHORED_X + 1, AUTHORED_Y + 1),
          "%rx%r" % (meta["dims"]["x"], meta["dims"]["y"]))
    check(meta["cell_pitch"] == CELL_PITCH and a["pitch_y"] == CELL_PITCH,
          "and the pitch is measured at %r on both axes" % CELL_PITCH,
          "%r / %r" % (meta["cell_pitch"], a["pitch_y"]))
    check(a["lattice_residual"] == 0.0 and
          a["manufactured_edge_unstorable"] == 0,
          "the authored lattice is exact and its far edge is a proper "
          "replication", "residual %r, unstorable %d"
          % (a["lattice_residual"], a["manufactured_edge_unstorable"]))
    check([s["kind"] for s in meta["sidecars"]] == ["heights"],
          "only a heights sidecar is written -- the mesh carries no tile or "
          "shade attributes and none is invented",
          "%r" % [s["kind"] for s in meta["sidecars"]])

    hs = heights_of(out_json(outdir, "authored"))
    i, j = AUTHORED_PROBE_IJ
    check(hs[j * AUTHORED_X + i] == AUTHORED_PROBE_STORED,
          "the height authored at (%d, %d) arrives as the literal %r -- the "
          "one value here not recomputed from the formula under test"
          % (i, j, AUTHORED_PROBE_STORED), "%r" % hs[j * AUTHORED_X + i])
    check(len(set(hs)) > 20,
          "and the authored surface actually varies, so the check above is not "
          "one value repeated", "%d distinct heights" % len(set(hs)))

    # ---- and into a map file. The terrain chunk is the deliverable; whether
    # this map would LOAD is a question about the borrowed constants, which are
    # placeholders here, so section 5 is where gates() gets a real answer.
    consts = placeholder_constants()
    rect = (0.0, 0.0, AUTHORED_X * CELL_PITCH, AUTHORED_Y * CELL_PITCH)
    params = dict(dim_x=AUTHORED_X, dim_y=AUTHORED_Y,
                  heights=retile(hs, AUTHORED_X, AUTHORED_Y),
                  tiles=0, table_a=b"\x00", table_b=b"\x00", bits=0, shade=0,
                  shadow=None, order=mapbuild.SEQUENCE_SHORT)
    spec = mapbuild.MapSpec(mapbuild.FLAT_ORDER, terrain_params=params,
                            rect=rect,
                            path=mapbuild.PathChunk.minimal(rect=rect))
    built, report = mapbuild.build(spec, constants=consts,
                                   donor_row="placeholder")
    check(len(built) == len(mapbuild.FLAT_ORDER),
          "mapbuild assembles a whole map file from the authored heights",
          "%d chunks, %d bytes" % (len(built), report.total))

    trn = built.terrain()
    back = [trn.height_at(gx, gy)
            for gy in range(AUTHORED_Y) for gx in range(AUTHORED_X)]
    check(back == hs,
          "and the map file's terrain chunk decodes back to the heights that "
          "were authored in Blender -- every one of %d" % len(hs),
          "%d differ" % len(differing(back, hs) or []))


# --- 5. a real map, whose anchor is ArenaNet's ------------------------------

def _section5(check, led, blender, tmp, args):
    dat = args.dat
    if dat is None:
        dat = os.path.join(vaultpath.vault_root(), "dat_study", "Gw.dat")
    if not os.path.isfile(dat):
        led.skip("5. a real map, and gates() on a built one",
                 "no archive at %s (vault resolved to %s, %s)"
                 % (dat, vaultpath.vault_root(), vaultpath.vault_why()))
        return

    print("\n== 5. a RETAIL map through the round trip, against terrain.py's "
          "own bytes ==")
    with Archive(dat) as ar:
        row = file_id_table(ar).get(PRESEARING_FILE_ID)
        check(row == PRESEARING_ROW, "file id 0x%X resolves to row %d"
              % (PRESEARING_FILE_ID, PRESEARING_ROW), "got %r" % row)
        if row is None:
            led.skip("5. the real map", "the reference map did not resolve")
            return
        # textures=False: this file's claim is the GEOMETRY round trip, and
        # the texture block never survives the stamp anyway (import_gwmap
        # strips it -- a scene cannot vouch for files it does not contain).
        src = export_row(row, ar, outdir=os.path.join(tmp, "real"),
                         file_id=PRESEARING_FILE_ID, name="presearing",
                         textures=False)
        constants, donor = mapbuild.borrowed_constants(ar, exclude_row=row)

    exp = load_export(src)
    check((exp.dim_x, exp.dim_y) == PRESEARING_DIMS,
          "row %d is the pinned %dx%d grid" % (row, PRESEARING_DIMS[0],
                                               PRESEARING_DIMS[1]),
          "%dx%d" % (exp.dim_x, exp.dim_y))
    check(exp.rect == PRESEARING_RECT, "and has the pinned map rect",
          "%r" % (exp.rect,))
    check(len(set(exp.heights)) > 1000,
          "its heights actually vary, so the comparison below is not vacuous",
          "%d distinct over %d cells" % (len(set(exp.heights)), exp.cells))

    blend = os.path.join(tmp, "real.blend")
    t = time.perf_counter()
    rc, out, _summary = do_import(blender, src, blend)
    check(rc == 0, "the retail map imports", "rc=%d %s" % (rc, out.strip()[-160:]))
    outdir = os.path.join(tmp, "real_back")
    rc, out, meta = do_export(blender, blend, outdir, "presearing")
    check(rc == 0 and meta is not None, "and a separate process exports it back",
          "rc=%d %s" % (rc, out.strip()[-200:]))
    print("   %d x %d cells round-tripped in %.1fs"
          % (exp.dim_x, exp.dim_y, time.perf_counter() - t))
    if meta is None:
        led.skip("5. the real round trip", "no manifest")
        return

    dst = out_json(outdir, "presearing")
    # THE ANCHOR. This sidecar was written by mapexport.py out of Gw.dat through
    # terrain.py -- a decode path neither Blender script imports and neither has
    # any say in. Sections 1 and 2 are our code against our code; this is not.
    for kind in ("heights", "tiles", "shade"):
        same, detail = compare_sidecar(sidecar(src, kind), sidecar(dst, kind),
                                       kind)
        check(same, "ArenaNet's %s comes back BYTE-IDENTICAL through Blender"
              % kind, detail)
    a = meta["authored"]
    check(a["lattice_residual"] == 0.0 and
          a["manufactured_edge_unstorable"] == 0,
          "a %dx%d retail grid survives with an exact lattice and nothing "
          "unstorable" % (exp.dim_x, exp.dim_y),
          "residual %r, unstorable %d" % (a["lattice_residual"],
                                          a["manufactured_edge_unstorable"]))
    check(not a["stamp_disagreements"],
          "and the re-derived geometry agrees with the stamp",
          "%r" % (a["stamp_disagreements"],))

    # ---- gates() with REAL constants, on the small authored map -------------
    # Section 4 built one with placeholders, which a zeroed Header chunk makes
    # unloadable by construction. Here the FINDINGS 14 constants are the
    # archive's own, so the loader's open-time rules get a real answer about a
    # map whose terrain a human authored in Blender.
    print("\n   and gates() on a map built from an authored height field:")
    hs = [float(((i * 7 + j * 13) % 97) * 4)
          for j in range(AUTHORED_Y) for i in range(AUTHORED_X)]
    rect = (0.0, 0.0, AUTHORED_X * CELL_PITCH, AUTHORED_Y * CELL_PITCH)
    params = dict(dim_x=AUTHORED_X, dim_y=AUTHORED_Y,
                  heights=retile([-v for v in hs], AUTHORED_X, AUTHORED_Y),
                  tiles=0, table_a=b"\x00", table_b=b"\x00", bits=0, shade=0,
                  shadow=None, order=mapbuild.SEQUENCE_SHORT)
    spec = mapbuild.MapSpec(mapbuild.FLAT_ORDER, terrain_params=params,
                            rect=rect,
                            path=mapbuild.PathChunk.minimal(rect=rect))
    built, _report = mapbuild.build(spec, constants=constants, donor_row=donor)
    results = mapbuild.gates(MapFile.decode(built.encode()))
    failed = [(n, d) for n, ok, d in results if not ok]
    check(not failed,
          "all %d of the client's open-time rules pass on a map whose terrain "
          "was authored in Blender" % len(results),
          "; ".join("%s (%s)" % (n, d) for n, d in failed) if failed
          else "%d gates" % len(results))




# --- 6. the PROPS round trip ----------------------------------------------

MOVE_PROP_SCRIPT = _argv_preamble() + """
import math
import mathutils
ARGV = _argv()
blend, out, move_i, rot_i = ARGV[0], ARGV[1], int(ARGV[2]), int(ARGV[3])
bpy.ops.wm.open_mainfile(filepath=blend)
props = sorted([o for o in bpy.data.objects if "gw_model" in o.keys()],
               key=lambda o: o["gw_index"])
target = props[move_i]
target.location.x += 1000.0
target.location.y -= 500.0
target.location.z += 250.0
# Rotate about the object's OWN origin, not the world's -- the world-origin
# form MOVES the prop as well, which would make the position check below
# ambiguous. Measured while writing this: it displaced the prop by
# (-20344, +15804), and the exporter correctly reported both changes.
rot = props[rot_i]
loc = rot.matrix_world.translation.copy()
turn = mathutils.Matrix.Rotation(math.radians(90.0), 4, "Z")
rot.matrix_world = (mathutils.Matrix.Translation(loc) @ turn
                    @ mathutils.Matrix.Translation(-loc) @ rot.matrix_world)
bpy.ops.wm.save_as_mainfile(filepath=out)
print("EDITED", target.name, rot.name)
"""


def _props_of(path):
    """A props sidecar read from disk. `sidecar()` returns BYTES, so the
    source side uses json.loads on those instead -- two shapes, one format."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _section6(check, led, blender, tmp, args):
    """Props survive the round trip, and an EDIT to one is carried out."""
    print("\n== 6. the PROPS round trip, and the edit control ==")
    dat = args.dat or os.path.join(vaultpath.vault_root(), "dat_study",
                                   "Gw.dat")
    if not os.path.isfile(dat):
        led.skip("6. the props round trip", "no archive at %s" % dat)
        return

    work = os.path.join(tmp, "props")
    os.makedirs(work, exist_ok=True)
    with Archive(dat) as ar:
        src = mapexport.export_file_id(PRESEARING_FILE_ID, ar, outdir=work,
                                       name="rt", props=True)
    original = sidecar(src, "props")
    if original is None:
        led.skip("6. the props round trip", "the export carried no props")
        return
    before = json.loads(original.decode("utf-8"))
    check(before["count"] > 800,
          "the source export carries a real prop population",
          "%d props" % before["count"])

    blend = os.path.join(work, "scene.blend")
    rc, out, _summary = do_import(blender, src, blend)
    check(rc == 0, "the import runs", "rc=%d %s" % (rc, out.strip()[-120:]))
    if rc != 0:
        return

    rc, out, _meta = do_export(blender, blend, work, "rtprops")
    check(rc == 0, "the export runs and writes a props sidecar",
          "rc=%d %s" % (rc, out.strip()[-120:]))
    after_path = os.path.join(work, "rtprops.props.json")
    if rc != 0 or not os.path.isfile(after_path):
        check(False, "a props sidecar came back out", after_path)
        return
    after = _props_of(after_path)

    # THE IDENTITY IS THE WEAK HALF and is labelled as such: an exporter that
    # re-emitted a stamped sidecar would pass every line in this block. The
    # edit control below is what it cannot pass.
    check(after["count"] == before["count"],
          "every prop comes back", "%d -> %d" % (before["count"],
                                                 after["count"]))
    check(len(after["models"]) == len(before["models"]),
          "and the model table -- ARCHIVE STATE a Blender scene cannot "
          "re-derive -- is carried intact",
          "%d -> %d" % (len(before["models"]), len(after["models"])))
    same = sum(1 for a, b in zip(before["props"], after["props"])
               if a["model"] == b["model"] and a["flags"] == b["flags"]
               and a["outline"] == b["outline"])
    check(same == before["count"],
          "model index, flags and the outline ring are identical on all of "
          "them", "%d/%d" % (same, before["count"]))
    worst_pos = max(abs(a["position"][k] - b["position"][k])
                    for a, b in zip(before["props"], after["props"])
                    for k in range(3))
    worst_basis = max(abs(a["basis"][u][k] - b["basis"][u][k])
                      for a, b in zip(before["props"], after["props"])
                      for u in range(2) for k in range(3))
    check(worst_pos == 0.0,
          "every position is EXACT -- not within a tolerance, identical",
          "worst |dposition| %g" % worst_pos)
    check(worst_basis < 1e-5,
          "and every rotation basis survives to float32 precision",
          "worst |dbasis| %g" % worst_basis)

    # THE EDIT CONTROL, and it is the whole reason this section is worth its
    # runtime. Move one prop by a known amount and turn a DIFFERENT one by 90
    # degrees about its own origin, then require EXACTLY those two records to
    # change and exactly as asked. An exporter re-emitting the stamp cannot do
    # it; nor can one that reads an object's location but not its rotation,
    # which is why the two edits are on two different props.
    script = os.path.join(tmp, "moveprop.py")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(MOVE_PROP_SCRIPT)
    moved_blend = os.path.join(work, "moved.blend")
    rc, out = run_blender(blender, script,
                          [blend, moved_blend, str(MOVE_INDEX),
                           str(ROTATE_INDEX)])
    check(rc == 0, "the edit script runs", "rc=%d %s" % (rc, out[-120:]))
    if rc != 0:
        return
    rc, out, _meta = do_export(blender, moved_blend, work, "rtmoved")
    check(rc == 0, "the edited scene exports", "rc=%d" % rc)
    edited_path = os.path.join(work, "rtmoved.props.json")
    if not os.path.isfile(edited_path):
        check(False, "the edited scene wrote a props sidecar", edited_path)
        return
    edited = _props_of(edited_path)

    changed = []
    for i, (a, b) in enumerate(zip(before["props"], edited["props"])):
        dpos = [b["position"][k] - a["position"][k] for k in range(3)]
        dbasis = max(abs(a["basis"][u][k] - b["basis"][u][k])
                     for u in range(2) for k in range(3))
        if any(abs(x) > 1e-3 for x in dpos) or dbasis > 1e-3:
            changed.append((i, dpos, dbasis))
    check(len(changed) == 2,
          "EXACTLY two prop records changed -- the two that were edited, and "
          "no other of the %d" % before["count"],
          "%d changed: %r" % (len(changed), [c[0] for c in changed]))
    by_index = {c[0]: c for c in changed}

    # The z sign is the sharp end: Blender +250 must land as stored -250, the
    # same negation the terrain half applies, now measured on a PROP.
    if MOVE_INDEX in by_index:
        dpos = by_index[MOVE_INDEX][1]
        check(abs(dpos[0] - 1000.0) < 1e-3 and abs(dpos[1] + 500.0) < 1e-3
              and abs(dpos[2] + 250.0) < 1e-3,
              "the moved prop moved by exactly (+1000, -500) and by -250 in "
              "STORED z for +250 in Blender -- the negation, on props",
              "%r" % [round(x, 3) for x in dpos])
        check(by_index[MOVE_INDEX][2] < 1e-3,
              "and moving it did NOT disturb its rotation",
              "max|dbasis| %g" % by_index[MOVE_INDEX][2])
    else:
        check(False, "the moved prop is among the changed records",
              "index %d not in %r" % (MOVE_INDEX, sorted(by_index)))

    if ROTATE_INDEX in by_index:
        dpos, dbasis = by_index[ROTATE_INDEX][1], by_index[ROTATE_INDEX][2]
        check(dbasis > 0.5,
              "the rotated prop's BASIS moved substantially -- a 90-degree "
              "turn is not a rounding difference", "max|dbasis| %g" % dbasis)
        check(all(abs(x) < 1e-3 for x in dpos),
              "and rotating it about its own origin did NOT move it",
              "%r" % [round(x, 3) for x in dpos])
    else:
        check(False, "the rotated prop is among the changed records",
              "index %d not in %r" % (ROTATE_INDEX, sorted(by_index)))


if __name__ == "__main__":
    sys.exit(main())
