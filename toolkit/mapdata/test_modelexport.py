r"""The model interchange, and the two checks that can refute it.

    python toolkit/mapdata/test_modelexport.py
    python toolkit/mapdata/test_modelexport.py --all    # every model of both
                                                        #   reference maps

THE STRUCTURAL CHECK IS THE RE-INTERLEAVE, and it is the reason this rung is
trustable. `modelexport.py` SPLITS an interleaved vertex block into typed
per-field arrays -- a real transformation, not a copy -- so the exported
arrays can be put back together and compared against the bytes ArenaNet
wrote:

    re-interleave(exported arrays)  ==  the geometry chunk's own vertex bytes

read FRESH from `Gw.dat`, never from anything the exporter produced. The
re-interleaver is written in this file out of `struct.pack_into` and shares
no code with the module under test. **519 of 519 sub-models over both
reference maps, all nine formats.**

That check is not decoration and it did not pass first time: the exporter's
first version silently dropped `dat_fvf` bits 12/13 -- the tangent frame, 24
bytes a vertex -- and produced a perfectly plausible mesh. Six sub-models of
format 12405 failed the re-interleave and nothing else would have noticed,
because a dropped field costs no vertex, no triangle and no radius. For the
comparison to be byte-exact the export must account for EVERY byte of the
stride, which is why the two unnamed fields (bits 1 and 3) are carried as raw
bytes and why this test would redden if they stopped being.

EVERY OTHER CHECK HERE READS GEOMETRY THROUGH `load_model`, so one does not:
`_sidecar_positions` unpacks the position sidecar with `struct.unpack` and
compares it against the archive. MEASURED to be the only thing covering the
written files -- a loader that stashes the source block and rebuilds its
arrays from it passes the re-interleave AND both f11 oracles while the
sidecar it wrote is wrong, and exactly this one check goes red. The bare
memcpy loader, whose files are still correct, reddens nothing, which is the
right answer: the export is sound and only the loader is redundant.

THE CROSS-FILE ORACLE is M1/M2's, now running through the serialised
interchange: for every prop instance in a map, `f11 == scale * max 2D radius`
where the radius is recomputed from the exported POSITION SIDECAR read back
off disk. The map file is one this module never opens, so a wrong vertex
range, a dropped sub-model, a byte-order slip or a truncated array all move a
number two different files have to agree on. **474 of 474 and 664 of 664** on
the reference maps, matching `test_modelfile.py`'s in-memory figures exactly
-- which is the stated prediction, because the export must not change the
geometry.

WHAT THE COLLISION/RING ORACLE TURNED OUT TO BE, recorded because the rung
was scoped around it. `studies/models/PLAN.md` M3 proposed checking decoded
collision meshes against the outline rings retail ships. **It cannot be done
on the reference maps: the two populations are DISJOINT there** -- Kamadan
has 46 props with a ring and 30 on a collision-carrying model and ZERO with
both; Pre-Searing 34, 23 and ZERO. Corpus-wide (14-map sample) it is 1,782
with a ring, 346 on a collision model, and **28 with both** out of 14,095
props -- roughly what independence predicts (~44), so there is no anti-
correlation to report either, and n=28 spread over a sample is far too thin
to carry a floor-guarded assertion. Section 5 pins those population figures
instead, so the negative result is recorded as a measurement rather than
lost. Collision meshes ARE exported; nothing here claims they mean anything.

SECTIONS 0-2 NEED NO VAULT and build a model geometry from `struct.pack`.
Sections 3-5 need `vault/dat_study/Gw.dat`, declare skips naming the path,
and the floor then fails the run -- a synthetic mesh this file invented has
verified the plumbing and nothing about ArenaNet's bytes.
"""

import argparse
import hashlib
import json
import math
import os
import collections
import struct
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, file_id_table  # noqa: E402
from mapfile import MapFile  # noqa: E402
from props import BloatedProps  # noqa: E402
import modelexport  # noqa: E402
from modelexport import (build_manifest, export_file_id,  # noqa: E402
                         export_map_models, load_model, map_model_ids,
                         resolve_outdir, verify_manifest, write_export,
                         FORMAT, FORMAT_VERSION)
from modelfile import (ModelFile, ModelGeometry, NoClose,  # noqa: E402
                       Undecodable, FIELD_SIZE)
import checks  # noqa: E402
import vaultpath  # noqa: E402
from test_modelfile import (KAMADAN_FILE_ID, PRESEARING_FILE_ID,  # noqa: E402
                            CENSUS, synth_geometry, PROPS_BLOATED,
                            PROPS_DEPS_BLOATED, F11_TOL)

#: `dat_fvf` bits, in the order `modelfile.FIELD_ORDER` lays them out. Kept
#: here as literals rather than imported so the re-interleaver below does not
#: share its field map with the module it is checking.
BIT_POSITION = 0
BIT_NORMAL = 2
BIT_TANGENT = (12, 13)
BIT_TEXCOORD = (4, 5, 6, 7, 8, 9, 10, 11)
BIT_RAW = (1, 3)

#: MEASURED 2026-08-13 on `vault/dat_study/Gw.dat`. Sub-models over both
#: reference maps, and the formats they use.
REFERENCE_SUBMODELS = 519
REFERENCE_FORMATS = 9

#: The f11 oracle through the export must reproduce `test_modelfile.py`'s
#: in-memory numbers EXACTLY -- serialising the geometry may not change it.
#: RE-MEASURED after rung M6: every prop-referenced model now decodes, so the
#: comparable population is the WHOLE map rather than the subset the retired
#: search could read. `test_modelfile.py` scores the two populations apart
#: and shows the previously-readable ones still at 474/474 and 664/664; this
#: file pins the totals, and the two must agree because they are the same
#: measurement either side of a serialisation.
ORACLE = {KAMADAN_FILE_ID: (510, 516), PRESEARING_FILE_ID: (846, 864)}

#: (models with a collision mesh, collision meshes) over both reference maps.
#: RE-MEASURED after M6 -- (25, 28) before, and the growth is entirely models
#: the retired search could not read.
COLLISION_POPULATION = (39, 43)

#: The collision/ring population, RE-MEASURED after M6. See the docstring:
#: the reference maps still have ZERO props carrying BOTH a ring and a
#: collision-carrying model, which is what killed the oracle this rung was
#: scoped around -- and that negative now rests on the FULL population rather
#: than on the ~85% the search could read, so it is a stronger negative than
#: when it was first recorded.
RING_POPULATION = {
    KAMADAN_FILE_ID: dict(props=516, ring=46, on_collision_model=32, both=0),
    PRESEARING_FILE_ID: dict(props=864, ring=34, on_collision_model=56,
                             both=0),
}

# FLOOR: 58, from a real green run on `vault/dat_study/Gw.dat` 2026-08-14
# (427 s -- section 7's strided corpus sweep is most of it). Sections 0-2
# alone score 27 -- MEASURED by pointing --dat at a missing file, not counted
# by eye -- so a vault-less run lands 31 short and goes RED. `--all` widens
# sections 3-4 from a sample to every model of both reference maps and adds
# ONE check (the pinned sub-model census).
#
# 48 -> 58 on 2026-08-14 with rung M5's section 7: the FA5 walk, the
# resolution oracle (every reference lands on a texture MAGIC, which is what
# a wrong pair formula fails), the PNG round trip and its sha256 refusal, and
# the two checks that pin what the per-sub-model index IS without claiming
# what it SELECTS.
#
# WHICH CHECKS ARE LOAD-BEARING WAS MEASURED, by building eight sabotaged
# exporters and running this file against each. Results, for the next person
# who wants to know whether a check here earns its line:
#
#   drop normals              2 red   (re-interleave 0/33)
#   drop the tangent frame    2 red   (re-interleave 32/33 -- only ONE
#                                      sub-model of the default sample has
#                                      one, so the population guard beside
#                                      it is what really holds this)
#   drop the unnamed fields   2 red   (re-interleave 27/33)
#   vertex_base always 0      3 red   (re-interleave 17/33)
#   truncate a vertex         9 red   -- and it reddened NOTHING before the
#                                      read-backs were guarded: it raised
#                                      IndexError, killed the process, and
#                                      the run printed no verdict at all,
#                                      which is the one failure `checks.py`
#                                      cannot see (`test_content.py` records
#                                      the same shape)
#   weaken resolve_outdir     1 red   (the default-destination check alone)
#   memcpy loader             0 red   -- CORRECTLY: it stashes the source
#                                      block and rebuilds arrays from it, but
#                                      the FILES it writes are still right,
#                                      so the export is still sound
#   memcpy loader + a
#     corrupted sidecar       1 red   -- and it is the sidecar check, ALONE.
#                                      The re-interleave and both f11 oracles
#                                      pass green, because every one of them
#                                      reads geometry through `load_model`.
#
# That last pair is why `_sidecar_positions` exists and why it must never be
# routed through the module's loader.
FLOOR = 63

DEFAULT_SAMPLE = 12


# ------------------------------------------------------------------ helpers

def raises(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except (ValueError, KeyError):
        return True
    return False


def reinterleave(exp, si):
    """Rebuild sub-model `si`'s interleaved vertex block from the EXPORT.

    Written here out of `struct.pack_into` and the manifest's own
    `field_offsets`, sharing no code with `modelexport`. If this does not
    reproduce the archive's bytes exactly, the export lost something -- which
    is how the missing tangent frame was found.
    """
    s = exp.submodels[si]
    stride, nv = s["stride"], s["nv"]
    out = bytearray(stride * nv)
    fo = {int(k): v for k, v in s["field_offsets"].items()}
    for i in range(nv):
        b = i * stride
        struct.pack_into("<3f", out, b + fo[BIT_POSITION],
                         *exp.arrays["pos"][s["vertex_base"] + i])
        if s.get("normal_base") is not None:
            struct.pack_into("<3f", out, b + fo[BIT_NORMAL],
                             *exp.arrays["nrm"][s["normal_base"] + i])
        for k, base in (s.get("tangent_bases") or {}).items():
            struct.pack_into("<3f", out, b + fo[BIT_TANGENT[int(k)]],
                             *exp.arrays[f"tan{k}"][base + i])
        for k, base in (s.get("texcoord_bases") or {}).items():
            struct.pack_into("<2f", out, b + fo[BIT_TEXCOORD[int(k)]],
                             *exp.arrays[f"uv{k}"][base + i])
        for k, base in (s.get("raw_bases") or {}).items():
            bit = int(k)
            size = FIELD_SIZE[bit]
            out[b + fo[bit]:b + fo[bit] + size] = \
                exp.arrays[f"raw{bit}"][base + i * size:base + (i + 1) * size]
    return bytes(out)


def _sidecar_positions(json_path):
    """The position sidecar's own bytes, unpacked HERE.

    Deliberately does not call `load_model`: this is the only path in the
    suite that touches the file a third-party consumer would read, so it must
    not share a loader with the module under test.
    """
    with open(json_path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    side = next(s for s in meta["sidecars"] if s["kind"] == "pos")
    blob = open(os.path.join(os.path.dirname(os.path.abspath(json_path)),
                             side["name"]), "rb").read()
    flat = struct.unpack(f"<{3 * side['count']}f", blob)
    return [tuple(flat[i * 3:i * 3 + 3]) for i in range(side["count"])]


def map_props(ar, table, by_row, map_fid):
    """(prop records, model file ids) for a map -- the oracle's other file."""
    mf = MapFile.decode(ar.read(by_row[table[map_fid]]), strict=False)
    bp = BloatedProps.decode(mf.find(PROPS_BLOATED).payload())
    return bp.records, mf.find(PROPS_DEPS_BLOATED).value.file_ids


# --------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=None)
    ap.add_argument("--sample", type=int, default=DEFAULT_SAMPLE)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    led = checks.Ledger("model export", floor=FLOOR)
    check = checks.adopt(led)
    t0 = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="rurik_modelexport_") as tmp:
        _section0(check, tmp)
        _section1(check, tmp)
        _section2(check, tmp)
        _vault_sections(check, led, args, tmp)

    print(f"\n({time.perf_counter() - t0:.1f}s)")
    return led.verdict()


# --- 0. the provenance refusal ---------------------------------------------

def _find_tree():
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
    print("\n== 0. a decoded MESH may not land in the working tree ==")
    tree = _find_tree()
    for rel in ("", "toolkit", os.path.join("toolkit", "mapdata"), "studies",
                "content"):
        target = os.path.join(tree, rel) if rel else tree
        check(raises(resolve_outdir, target),
              f"refuses to export a mesh into the working tree "
              f"({rel or '.'})")
    # POSITIVE CONTROLS: a guard that refuses everything protects nothing,
    # because the tool then never runs.
    vault_out = vaultpath.vault_path("exports", "models")
    check(resolve_outdir(vault_out) == os.path.abspath(vault_out),
          "the vault is allowed even though it sits inside the repo root")
    check(resolve_outdir(None) == os.path.abspath(vault_out),
          "the default destination is vault/exports/models")
    check(resolve_outdir(tmp) == os.path.abspath(tmp),
          "a scratch directory outside the tree is allowed")
    # And it must be the SAME guard mapexport uses, not a second copy that
    # can drift away from it.
    import mapexport
    check(modelexport.resolve_outdir.__module__ == "modelexport"
          and "mapexport.resolve_outdir" in
          (modelexport.resolve_outdir.__doc__ or ""),
          "the guard delegates to mapexport's rather than reimplementing it")
    check(raises(mapexport.resolve_outdir, tree)
          and raises(resolve_outdir, tree),
          "and both refuse the same tree")


# --- 1. an export built from nothing ---------------------------------------

def _section1(check, tmp):
    print("\n== 1. a synthetic model exports and reads back (no vault) ==")
    geo = ModelGeometry.decode(synth_geometry())
    meta, payloads = build_manifest(geo, "syn", {"archive": None,
                                                 "file_id": 0x1234,
                                                 "row": None})
    path = write_export(meta, payloads, os.path.join(tmp, "syn"))
    exp = load_model(path)

    check(exp.meta["format"] == FORMAT
          and exp.meta["format_version"] == FORMAT_VERSION,
          f"the manifest declares {FORMAT} v{FORMAT_VERSION}")
    check(len(exp.submodels) == 2 and exp.meta["geometry"]["vertices"] == 7,
          "both sub-models and all seven vertices survive",
          f"{len(exp.submodels)} subs, "
          f"{exp.meta['geometry']['vertices']} verts")
    check(exp.positions(0)[0] == (30.0, 40.0, -100.0),
          "the first position is the planted one", f"{exp.positions(0)[0]}")
    check(exp.max_2d_radius() == 50.0,
          "max 2D radius through the EXPORT is the planted 50.0",
          f"{exp.max_2d_radius()!r}")
    check(exp.triangles(0) == [(0, 1, 2), (2, 1, 3)],
          "triangles come back as index triples, local to the sub-model",
          f"{exp.triangles(0)}")
    check(exp.positions(1)[0] == (1.0, 1.0, 0.0)
          and exp.submodels[1]["vertex_base"] == 4,
          "the second sub-model's vertices sit after the first's")
    check(len(exp.meta["collisions"]) == 1
          and exp.arrays["cpos"][2] == (0.0, 0.0, 9.0),
          "the collision mesh is exported too")

    # THE STRUCTURAL CHECK, on bytes this file built itself.
    both = all(reinterleave(exp, i) == bytes(geo.submodels[i].vertex_data)
               for i in range(2))
    check(both, "re-interleaving the export reproduces both synthetic vertex "
                "blocks byte-for-byte")
    # And it has power: corrupt one exported position and it must fail.
    exp.arrays["pos"][0] = (0.0, 0.0, 0.0)
    check(reinterleave(exp, 0) != bytes(geo.submodels[0].vertex_data),
          "and one changed position breaks it -- the check is not vacuous")


# --- 2. the digests, and what load_model refuses ---------------------------

def _section2(check, tmp):
    print("\n== 2. the sha256 manifest and a corrupted vertex ==")
    geo = ModelGeometry.decode(synth_geometry())
    meta, payloads = build_manifest(geo, "dg", {"archive": None,
                                                "file_id": 1, "row": None})
    out = os.path.join(tmp, "dg")
    path = write_export(meta, payloads, out)
    check(verify_manifest(path) == [], "a freshly written export verifies")

    pos = os.path.join(out, "dg.pos.f32")
    original = open(pos, "rb").read()
    corrupt = bytearray(original)
    corrupt[0] ^= 0x01                      # one mantissa bit of one vertex
    before, = struct.unpack_from("<f", original, 0)
    after, = struct.unpack_from("<f", bytes(corrupt), 0)
    check(len(corrupt) == len(original) and before != after,
          "the control changed one coordinate and nothing else",
          f"{before!r} -> {after!r}")
    open(pos, "wb").write(bytes(corrupt))
    bad = verify_manifest(path)
    check(len(bad) == 1 and "dg.pos.f32" in bad[0],
          "verify_manifest catches it and names the file",
          bad[0][:60] if bad else "NOTHING REPORTED")
    check(raises(load_model, path),
          "load_model RAISES rather than handing back corrupted geometry")
    open(pos, "wb").write(original)
    check(verify_manifest(path) == [], "restoring the bytes makes it verify")

    open(pos, "wb").write(original[:-12])
    check(any("bytes on disk" in b for b in verify_manifest(path)),
          "a truncated sidecar is a size mismatch")
    os.remove(pos)
    check(any("missing" in b for b in verify_manifest(path)),
          "a deleted sidecar is reported missing, not silently skipped")

    other = os.path.join(tmp, "wrongver.gwmodel.json")
    obj = json.loads(open(path, encoding="utf-8").read())
    obj["format_version"] = FORMAT_VERSION + 1
    open(other, "w", encoding="utf-8").write(json.dumps(obj))
    check(any("format_version" in b for b in verify_manifest(other)),
          "a manifest from another format version is refused")


# --- 3-5. the archive -------------------------------------------------------

def _vault_sections(check, led, args, tmp):
    dat = args.dat
    if dat is None:
        dat = os.path.join(vaultpath.vault_root(), "dat_study", "Gw.dat")
    if not os.path.isfile(dat):
        why = (f"no archive at {dat} (vault resolved to "
               f"{vaultpath.vault_root()}, {vaultpath.vault_why()})")
        led.skip("3. the re-interleave against ArenaNet's own bytes", why)
        led.skip("4. the f11 oracle through the export", why)
        led.skip("5. the collision/ring population", why)
        led.skip("6. the collision-mesh invariants", why)
        led.skip("7. the texture layer", why)
        return
    with Archive(dat) as ar:
        table = file_id_table(ar)
        by_row = {e.index: e for e in ar.entries}
        _section3(check, ar, table, by_row, tmp, args)
        _section4(check, ar, table, by_row, tmp, args)
        _section5(check, ar, table, by_row)
        _section6(check, ar, table, by_row)
        try:
            _section7(check, ar, table, by_row, tmp)
        except Exception as exc:                       # noqa: BLE001
            # A section that dies must be a NAMED failing check, never a
            # bare traceback with no verdict and no floor line.
            check(False, "section 7 (textures) completed",
                  f"{type(exc).__name__}: {exc}")


def _section7(check, ar, table, by_row, tmp):
    """The TEXTURE layer (rung M5), and what it does NOT establish."""
    print("\n== 7. textures: FA5 -> the archive -> PNG ==")
    import modelfile
    import png as pngmod

    # (a) THE CHUNK WALK. `texture_refs` closes on the exact final byte, and
    # the rival framing -- fixed 6-byte slots, i.e. no NULL sentinel -- must
    # NOT, or the null slot is a rule with no evidence behind it.
    walked = rival = 0
    total_refs = 0
    for fid in (KAMADAN_FILE_ID, PRESEARING_FILE_ID):
        for model_id in modelexport.map_model_ids(fid, ar, table=table):
            row = table.get(model_id)
            if row is None:
                continue
            mf = ModelFile.decode(ar.read(by_row[row]))
            payload = mf.find(modelfile.TEXNAME_CHUNK_B)
            if payload is None:
                continue
            try:
                refs = mf.texture_refs()
            except Undecodable:
                continue
            walked += 1
            total_refs += len(refs)
            count, = struct.unpack_from("<I", payload, 0)
            if 4 + 6 * count == len(payload):
                rival += 1
    check(walked > 250 and total_refs > 1500,
          "every reference-map model's FA5 chunk closes on its exact final "
          "byte", f"{walked} chunks, {total_refs} slots")
    # THE NULL SLOT IS NOT TESTABLE ON THESE MAPS, and saying so is the
    # point: both reference maps carry ZERO null slots (0 of 1,795), so the
    # fixed-6-byte rival closes on all 315 chunks too. Asserting that the
    # rival fails here would be asserting evidence this sample cannot
    # provide. The discrimination is a CORPUS fact, so it is measured on a
    # strided sweep of ffna type-2 rows instead.
    check(rival == walked,
          "on the reference maps the fixed-6-byte rival closes too -- they "
          "hold no null slot, so they cannot decide the sentinel",
          f"{rival}/{walked}")
    nulls = swept = rival_closes = 0
    for entry in ar.entries[::97]:
        # CLASSIFY on four bytes, decode only on a hit. 64% of the strided rows
        # are not models at all, and reading them whole to look at `data[:4]`
        # decompressed megabytes of texture and threw them away -- MEASURED
        # 2026-08-14: this loop was 65 s of the file's 480 s, and 4.6x of it was
        # decode of entries that never reached `ModelFile`.
        try:
            if ar.magic(entry) != b"ffna":
                continue
            data = ar.read(entry)
        except Exception:                              # noqa: BLE001
            continue
        try:
            mf = ModelFile.decode(data)
            payload = mf.find(modelfile.TEXNAME_CHUNK_B)
            if payload is None or len(payload) < 4:
                continue
            refs = mf.texture_refs()
        except (Undecodable, ValueError, struct.error, IndexError):
            continue
        swept += 1
        nulls += sum(1 for r in refs if r is None)
        count, = struct.unpack_from("<I", payload, 0)
        if 4 + 6 * count == len(payload):
            rival_closes += 1
    print(f"    strided sweep: {swept} FA5 chunks, {nulls} null slots")
    if swept > 30 and nulls:
        check(rival_closes < swept,
              "and over a strided CORPUS sweep the fixed-6-byte rival fails "
              "on the chunks carrying a null slot",
              f"rival closes {rival_closes}/{swept}, {nulls} nulls seen")
    else:
        check(swept > 30,
              "the strided sweep found FA5 chunks to test the sentinel on",
              f"{swept} chunks, {nulls} nulls")

    # (b) THE RESOLUTION ORACLE, and it is the strong one here: a decoded
    # reference must land on a row that IS a texture. A wrong pair formula
    # would still resolve some rows -- it is the MAGIC that refutes it.
    magics = collections.Counter()
    resolved = unresolved = 0
    # The magic of a texture row, four bytes and once per ROW. This section was
    # 176 s of the file's 480 s and both halves of that were waste: it fully
    # decompressed a multi-megabyte texture to slice `[:4]`, and it did so once
    # per REFERENCE rather than once per row -- 1,795 references land on 472
    # distinct rows, so 3.8 of every 4 decodes reproduced a byte string the loop
    # had already seen. MEASURED: 143 s -> under a second, same counter.
    _magic_by_row = {}

    def row_magic(row):
        m = _magic_by_row.get(row)
        if m is None:
            m = _magic_by_row[row] = ar.magic(by_row[row])
        return m

    for fid in (KAMADAN_FILE_ID, PRESEARING_FILE_ID):
        for model_id in modelexport.map_model_ids(fid, ar, table=table):
            row = table.get(model_id)
            if row is None:
                continue
            try:
                refs = ModelFile.decode(ar.read(by_row[row])).texture_refs()
            except Undecodable:
                continue
            for file_id in refs:
                if file_id is None:
                    continue
                trow = table.get(file_id)
                if trow is None:
                    unresolved += 1
                    continue
                resolved += 1
                magics[row_magic(trow)] += 1
    known = magics[b"ATEX"] + magics[b"ATTX"] + magics[b"DDS "]
    check(unresolved == 0 and resolved > 1500,
          "every non-null texture reference resolves to an archive row",
          f"{resolved} resolved, {unresolved} not")
    check(known == resolved,
          "and EVERY resolved row carries a texture magic -- the check a "
          "wrong pair formula fails", f"{dict(magics)}")

    # (c) THE EXPORT. Decode to PNG and read it back with the codec's own
    # reader, then require the dimensions to match the container's header --
    # which the PNG writer never sees.
    outdir = os.path.join(tmp, "tex")
    fid = modelexport.map_model_ids(KAMADAN_FILE_ID, ar, table=table)[0]
    path = modelexport.export_file_id(fid, ar, outdir=outdir, table=table)
    exp = modelexport.load_model(path)
    entries = [t for t in exp.meta.get("textures", []) if t.get("image")]
    check(entries, f"model 0x{fid:X} exported {len(entries)} texture(s)")
    checked = 0
    for entry in entries:
        pixels, width, height, _colour = pngmod.read(
            os.path.join(outdir, entry["image"]))
        if width == entry["width"] and height == entry["height"] \
                and len(pixels) == width * height * 4:
            checked += 1
    check(checked == len(entries),
          "every PNG reads back at the size the manifest claims",
          f"{checked}/{len(entries)}")

    # (d) The sidecar digests cover the PNGs too -- a corrupted texture must
    # be caught by the same manifest rule the geometry arrays get.
    victim = [s for s in exp.meta["sidecars"]
              if s["kind"] == "texture"][0]
    blob = bytearray(open(os.path.join(outdir, victim["name"]), "rb").read())
    blob[len(blob) // 2] ^= 0xFF
    open(os.path.join(outdir, victim["name"]), "wb").write(bytes(blob))
    try:
        modelexport.load_model(path)
        check(False, "a corrupted PNG sidecar is refused by its sha256")
    except ValueError as exc:
        check(victim["name"] in str(exc),
              "a corrupted PNG sidecar is refused by its sha256, by name",
              str(exc)[:56])

    # (e) WHAT THIS DOES NOT ESTABLISH, asserted so nobody later reads the
    # binding as settled. `material_index` is a real per-sub-model index --
    # it must vary and must not be a bare ordinal -- but WHICH FA5 slot is
    # the DIFFUSE is refuted, not merely unknown (a render puts specular
    # maps on buildings). The check is on the property that IS measured.
    varies = ordinal = models = 0
    for model_id in modelexport.map_model_ids(KAMADAN_FILE_ID, ar,
                                              table=table):
        row = table.get(model_id)
        if row is None:
            continue
        mf = ModelFile.decode(ar.read(by_row[row]))
        geo = mf.geometry()
        if geo is None or len(geo.submodels) < 2:
            continue
        if len(mf.texture_refs()) < 2:
            continue
        models += 1
        vals = [sm.unk for sm in geo.submodels]
        varies += len(set(vals)) > 1
        ordinal += vals == list(range(len(vals)))
    check(models > 40 and varies > models * 0.9,
          "the per-sub-model index VARIES on over 90% of multi-texture "
          "models -- it is an index, not a constant",
          f"{varies}/{models}")
    check(ordinal < models,
          "and it is not always the bare ordinal 0..n-1, which is what a "
          "sub-model counter would be", f"{ordinal}/{models} are ordinals")

    _section8(check, ar, table, by_row)


def _section8(check, ar, table, by_row):
    """THE MATERIAL TABLE, and the oracle that binds a surface to a texture."""
    print("\n== 8. the material table: sub-model -> material -> texture ==")
    import random
    from modelfile import material_table

    rnd = random.Random(5)
    stat = collections.Counter()
    for fid in (KAMADAN_FILE_ID, PRESEARING_FILE_ID):
        for model_id in modelexport.map_model_ids(fid, ar, table=table):
            row = table.get(model_id)
            if row is None:
                continue
            mf = ModelFile.decode(ar.read(by_row[row]))
            geo = mf.geometry()
            if geo is None:
                continue
            mtable = material_table(mf.find(0x00000FA0))
            if mtable is None:
                stat["amat_only"] += 1
                continue
            stat["models"] += 1
            ntex = len(mf.texture_refs())
            for pos, sub in enumerate(geo.submodels):
                kind, layers = mtable.for_submodel(sub)
                if kind != "layered":
                    stat["binary"] += 1
                    continue
                stat["layered"] += 1
                for lay in layers:
                    stat["layers"] += 1
                    stat["texpath_in_range"] += lay.texpath < ntex

                # THE ORACLE. The material's layers name the UV SETS they
                # sample; the highest must match what the SUB-MODEL's vertex
                # format actually carries. That crosses the material table
                # and the vertex declaration -- two structures this decoder
                # does not derive from one another.
                for name, index in (("real", sub.unk & 0xFFFF),
                                    ("position", pos),
                                    ("random", rnd.randrange(
                                        len(mtable.materials)))):
                    if index >= len(mtable.materials):
                        continue
                    lay_n = mtable.layers_of(index)
                    used = [x.texarray for x in lay_n if x.texarray >= 0]
                    if not used:
                        continue          # samples no stored set: undefined
                    stat[name + "_n"] += 1
                    stat[name + "_ok"] += (max(used) + 1 == sub.texcoord_sets)

    print(f"    {stat['models']} models with a layered table "
          f"(+{stat['amat_only']} AMAT-only), {stat['layered']} layered "
          f"sub-models, {stat['layers']} layers")
    check(stat["models"] > 250 and stat["layered"] > 900,
          "both reference maps yield a layered material table",
          f"{stat['models']} models, {stat['layered']} sub-models")

    # ArenaNet's own bound, MdlCombine:568 texPathIndex < texPathCount.
    check(stat["texpath_in_range"] == stat["layers"],
          "every layer's texPathIndex is inside the model's FA5 texture "
          "list -- the client's own bound at MdlCombine:568",
          f"{stat['texpath_in_range']}/{stat['layers']}")

    real = stat["real_ok"] / max(stat["real_n"], 1)
    pos_r = stat["position_ok"] / max(stat["position_n"], 1)
    rnd_r = stat["random_ok"] / max(stat["random_n"], 1)
    print(f"    UV-set oracle: real {stat['real_ok']}/{stat['real_n']}, "
          f"position {stat['position_ok']}/{stat['position_n']}, "
          f"random {stat['random_ok']}/{stat['random_n']}")
    check(stat["real_ok"] == stat["real_n"] and stat["real_n"] > 900,
          "a material's layers name exactly the UV sets its sub-model "
          "carries: max(texarray) + 1 == texcoord_sets, on ALL of them",
          f"{stat['real_ok']}/{stat['real_n']}")

    # THE CONTROLS. Binding by POSITION is the obvious wrong implementation
    # and it is nearly right, which is precisely why it has to be measured
    # rather than dismissed -- and a random material sets the floor.
    check(pos_r < 0.95 and rnd_r < 0.75 and real > pos_r > rnd_r,
          "and both rivals collapse -- binding by sub-model POSITION, and a "
          "RANDOM material",
          f"real {real:.3f} > position {pos_r:.3f} > random {rnd_r:.3f}")

    # The client's own consistency gate, exercised through real files: the
    # per-material layer counts must sum to the header's total. A model
    # where they do not would have every texture index after it misaligned.
    check(stat["models"] + stat["amat_only"] > 300,
          "and no model in either map fails the layer-count sum gate -- a "
          "refusal would have raised Undecodable above",
          f"{stat['models']} + {stat['amat_only']} AMAT-only")


def _section3(check, ar, table, by_row, tmp, args):
    print("\n== 3. THE STRUCTURAL CHECK: re-interleave vs the archive ==")
    ok = mismatch = subs = 0
    fmts = set()
    raws = tangents = 0
    first = []
    # The INDEX arrays are checked separately and deliberately: the
    # re-interleave below covers vertex BYTES only, and the f11 oracle covers
    # positions only, so without this an exporter that scrambled, truncated
    # or mis-based the triangle list would pass every other check in this
    # file. Found by reading the suite rather than by a sabotage.
    idx_same = idx_subs = idx_tris = 0
    idx_range_ok = idx_div3 = 0
    errors = []
    raw_pos, want_pos = [], []
    for map_fid in (KAMADAN_FILE_ID, PRESEARING_FILE_ID):
        ids = map_model_ids(map_fid, ar, table=table)
        if not args.all:
            ids = ids[::max(1, len(ids) // args.sample)][:args.sample]
        for fid in ids:
            row = table.get(fid)
            if row is None:
                continue
            try:
                geo = ModelFile.decode(ar.read(by_row[row])).geometry()
            except (NoClose, Undecodable, ValueError):
                continue
            if geo is None:
                continue
            jpath = export_file_id(fid, ar, outdir=os.path.join(tmp, "ri"),
                                   table=table)
            exp = load_model(jpath)
            # THE SIDECAR ITSELF, read with struct.unpack in this file and
            # never through `load_model`. Everything else in this suite reads
            # geometry through the module's own loader, so a loader that
            # reconstructed the arrays from anything OTHER than the sidecars
            # -- a stashed copy of the interleaved block, say -- would return
            # correct values and pass every one of them while the files it
            # claims to have written went unchecked. This is the only check
            # that reads the bytes a third-party consumer would actually get.
            raw_pos.append(_sidecar_positions(jpath))
            want_pos.append([p for sm2 in geo.submodels
                             for p in sm2.positions()])
            for si, sm in enumerate(geo.submodels):
                subs += 1
                fmts.add(sm.dat_fvf)
                raws += bool(exp.submodels[si].get("raw_bases"))
                tangents += bool(exp.submodels[si].get("tangent_bases"))
                # EVERY READ-BACK IS GUARDED, and this is not defensive
                # habit -- a sabotage that truncated each sub-model's vertex
                # array while leaving `nv` alone raised IndexError here and
                # KILLED THE PROCESS: section 3 printed no [FAIL], the two
                # headline checks below never ran, and `checks.py` never
                # reached its verdict, so the run died with no banner and no
                # floor shortfall. That is the one failure the ledger cannot
                # see (`test_content.py` records the same shape). A broken
                # export must produce a RED CHECK, never a traceback.
                try:
                    if reinterleave(exp, si) == bytes(sm.vertex_data):
                        ok += 1
                    else:
                        mismatch += 1
                        if len(first) < 3:
                            first.append((hex(fid), si, sm.dat_fvf))
                except Exception as exc:                    # noqa: BLE001
                    errors.append((hex(fid), si, type(exc).__name__))
                # ...and the triangle list, which no other check reaches.
                idx_subs += 1
                try:
                    got = [i for t in exp.triangles(si) for i in t]
                    idx_same += list(sm.indices) == got
                    idx_tris += len(got) // 3
                    idx_range_ok += all(v < sm.nv for v in got)
                    idx_div3 += len(got) % 3 == 0
                except Exception as exc:                    # noqa: BLE001
                    errors.append((hex(fid), si, type(exc).__name__))
    print(f"    {subs} sub-models, {len(fmts)} formats, {tangents} with a "
          f"tangent frame, {raws} with an unnamed field")
    # The guard's own check. Without it the try/except above would turn a
    # crash into SILENCE, which is worse than the traceback it replaced.
    check(not errors,
          "no sub-model raised while being read back -- a malformed export "
          "must be a red check, not a traceback that kills the run",
          f"{len(errors)} raised: {errors[:3]}" if errors else "0")
    check(subs > 0 and mismatch == 0,
          f"re-interleaving the export reproduces ArenaNet's vertex bytes on "
          f"all {subs} sub-models", f"{ok} ok, {mismatch} MISMATCH {first}")
    # THE POPULATION GUARDS. Without these the check above passes vacuously on
    # a sample that happens to contain no format carrying the fields whose
    # loss it exists to catch -- which is exactly the defect it DID catch.
    check(tangents > 0,
          "the sample includes sub-models with a tangent frame (bits 12/13), "
          "whose loss is what this check first caught", f"{tangents}")
    check(raws > 0,
          "and sub-models carrying an unnamed field (bit 1), without which "
          "the byte-exactness is untested", f"{raws}")

    # THE TRIANGLE LIST. Read back through `exp.triangles()`, which resolves
    # the manifest's per-sub-model index_base -- so a wrong base, a truncated
    # array or a scrambled order all move it.
    print(f"    {idx_tris} triangles read back through the manifest's bases")
    check(idx_subs > 0 and idx_same == idx_subs,
          f"every sub-model's triangle list comes back EXACTLY as the "
          f"archive has it ({idx_subs} of {idx_subs})",
          f"{idx_same}/{idx_subs}")
    check(idx_range_ok == idx_subs and idx_div3 == idx_subs,
          f"and every exported index is below its own sub-model's vertex "
          f"count, in multiples of 3", f"{idx_range_ok}/{idx_div3}/{idx_subs}")

    # THE SIDECAR BYTES, compared without the module's loader anywhere in the
    # path. See `_sidecar_positions`: this is what stops a loader that
    # reconstructs geometry from a stashed copy of the source from passing
    # the whole suite while the files it wrote go unchecked.
    nfiles = len(raw_pos)
    same = sum(1 for got, want in zip(raw_pos, want_pos) if got == want)
    nvert = sum(len(w) for w in want_pos)
    check(nfiles > 0 and same == nfiles,
          f"the POSITION SIDECAR's own bytes are the archive's vertices on "
          f"all {nfiles} models ({nvert} vertices), read with struct.unpack "
          f"and never through load_model", f"{same}/{nfiles}")
    if args.all:
        check(subs == REFERENCE_SUBMODELS and len(fmts) == REFERENCE_FORMATS,
              f"--all covers the pinned {REFERENCE_SUBMODELS} sub-models and "
              f"{REFERENCE_FORMATS} formats", f"{subs}, {len(fmts)}")


def _section4(check, ar, table, by_row, tmp, args):
    print("\n== 4. THE ORACLE: f11 vs the exported position sidecar ==")
    out = os.path.join(tmp, "oracle")
    for map_fid in (KAMADAN_FILE_ID, PRESEARING_FILE_ID):
        records, fids = map_props(ar, table, by_row, map_fid)
        radii = {}
        skipped = 0
        for idx in sorted({r.model for r in records}):
            if idx >= len(fids):
                continue
            try:
                path = export_file_id(fids[idx], ar, outdir=out, table=table)
            except (NoClose, Undecodable, ValueError, KeyError):
                skipped += 1
                continue
            # Read the radius back OFF DISK, never from the live geometry.
            radii[idx] = load_model(path).max_2d_radius()

        ok = rival = n = 0
        for rec in records:
            if rec.model not in radii:
                continue
            n += 1
            f11, = struct.unpack("<f", rec.tail)
            pred = radii[rec.model] * rec.scale
            if pred > 0 and abs(f11 - pred) / pred < F11_TOL:
                ok += 1
        want_ok, want_n = ORACLE[map_fid]
        print(f"    0x{map_fid:X}: {n} comparable props, {ok} match, "
              f"{skipped} models undecodable")
        check(n == want_n and ok == want_ok,
              f"0x{map_fid:X}: f11 == scale * the EXPORTED mesh's max 2D "
              f"radius on {want_ok}/{want_n} props", f"{ok}/{n}")
        # THE PREDICTION, stated in the docstring: serialising must not change
        # the geometry, so this must equal test_modelfile's in-memory figure.
        check((ok, n) == (CENSUS[map_fid]["f11_ok"], CENSUS[map_fid]["cmp"]),
              f"0x{map_fid:X}: and it EQUALS test_modelfile's in-memory "
              f"{CENSUS[map_fid]['f11_ok']}/{CENSUS[map_fid]['cmp']} -- the "
              f"export changed nothing", f"{ok}/{n}")


def _section6(check, ar, table, by_row):
    print("\n== 6. the collision meshes: invariants the decoder does NOT force ==")
    # These are worth more than the ring oracle M3 was scoped around, because
    # `ModelGeometry.decode` validates RENDER indices only -- its refusal
    # loops over `submodels` and never touches `collisions` -- so every count
    # below is a fact about ArenaNet's bytes that our decoder could not have
    # manufactured.
    import inspect
    import modelfile as _mf
    src = inspect.getsource(_mf.ModelGeometry.decode)
    check("sm.indices" in src and "cm.indices" not in src,
          "the decoder validates RENDER indices only -- so the collision "
          "checks below are unforced")

    meshes = models = 0
    idx_ok = idx_tot = div3 = rival3 = allref = 0
    for map_fid in (KAMADAN_FILE_ID, PRESEARING_FILE_ID):
        for fid in map_model_ids(map_fid, ar, table=table):
            row = table.get(fid)
            if row is None:
                continue
            try:
                geo = ModelFile.decode(ar.read(by_row[row])).geometry()
            except (NoClose, Undecodable, ValueError):
                continue
            if geo is None or not geo.collisions:
                continue
            models += 1
            for cm in geo.collisions:
                meshes += 1
                nv, ni = len(cm.positions), len(cm.indices)
                idx_tot += ni
                idx_ok += sum(1 for v in cm.indices if v < nv)
                div3 += ni % 3 == 0
                rival3 += nv % 3 == 0
                allref += len(set(cm.indices)) == nv
    print(f"    {meshes} collision meshes on {models} models, "
          f"{idx_tot} indices")
    check((models, meshes) == COLLISION_POPULATION,
          f"the pinned collision population {COLLISION_POPULATION}",
          f"({models}, {meshes})")
    check(idx_tot > 0 and idx_ok == idx_tot,
          f"every collision index is below its own mesh's vertex count "
          f"({idx_tot} of {idx_tot}) -- and nothing in the decoder requires it",
          f"{idx_ok}/{idx_tot}")
    check(meshes > 0 and div3 == meshes,
          f"every collision mesh is a triangle LIST (ni % 3 == 0) on "
          f"{meshes} of {meshes}", f"{div3}/{meshes}")
    # THE CONTROL, and it is what pins the header's FIELD ORDER: read the
    # header as (nv, ni) instead of (ni, nv) and the divisibility collapses.
    check(rival3 * 2 < meshes,
          f"the rival header order (nv, ni) divides by 3 on only "
          f"{rival3}/{meshes} -- so `u32 ni` really is first",
          f"{rival3}/{meshes}")
    check(allref == meshes,
          f"every collision vertex is referenced by some triangle "
          f"({allref} of {meshes} meshes)", f"{allref}/{meshes}")


def _section5(check, ar, table, by_row):
    print("\n== 5. the collision/ring populations (the oracle that ISN'T) ==")
    # Recorded as a MEASUREMENT because M3 was scoped around an oracle these
    # numbers refute. See the module docstring.
    for map_fid in (KAMADAN_FILE_ID, PRESEARING_FILE_ID):
        records, fids = map_props(ar, table, by_row, map_fid)
        with_coll = set()
        for idx in sorted({r.model for r in records}):
            if idx >= len(fids):
                continue
            row = table.get(fids[idx])
            if row is None:
                continue
            try:
                geo = ModelFile.decode(ar.read(by_row[row])).geometry()
            except (NoClose, Undecodable, ValueError):
                continue
            if geo is not None and geo.collisions:
                with_coll.add(idx)
        ring = sum(1 for r in records if r.points)
        onc = sum(1 for r in records if r.model in with_coll)
        both = sum(1 for r in records if r.points and r.model in with_coll)
        want = RING_POPULATION[map_fid]
        print(f"    0x{map_fid:X}: {len(records)} props, {ring} with a ring, "
              f"{onc} on a collision model, {both} with BOTH")
        check((len(records), ring, onc, both)
              == (want["props"], want["ring"], want["on_collision_model"],
                  want["both"]),
              f"0x{map_fid:X}: the pinned population "
              f"{want['ring']}/{want['on_collision_model']}/{want['both']}",
              f"{ring}/{onc}/{both}")
        check(both == 0,
              f"0x{map_fid:X}: ZERO props carry both a ring and a collision "
              f"model -- which is why the ring-vs-collision oracle cannot be "
              f"asserted here", f"{both}")


if __name__ == "__main__":
    sys.exit(main())
