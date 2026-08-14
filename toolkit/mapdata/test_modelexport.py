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
ORACLE = {KAMADAN_FILE_ID: (474, 474), PRESEARING_FILE_ID: (664, 664)}

#: (models with a collision mesh, collision meshes) over both reference maps,
#: MEASURED 2026-08-13.
COLLISION_POPULATION = (25, 28)

#: The collision/ring population, MEASURED 2026-08-13. See the docstring: the
#: reference maps have ZERO props carrying both, which is what killed the
#: oracle this rung was scoped around.
RING_POPULATION = {
    KAMADAN_FILE_ID: dict(props=516, ring=46, on_collision_model=30, both=0),
    PRESEARING_FILE_ID: dict(props=864, ring=34, on_collision_model=23,
                             both=0),
}

# FLOOR: 48, from a real green run on `vault/dat_study/Gw.dat` 2026-08-13
# (85 s). Sections 0-2 alone score 27 -- MEASURED by pointing --dat at a
# missing file, not counted by eye -- so a vault-less run lands 21 short and
# goes RED. `--all` widens sections 3-4 from a sample to every model of both
# reference maps and adds ONE check (the pinned sub-model census), so a green
# `--all` run is 49.
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
FLOOR = 48

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
        return
    with Archive(dat) as ar:
        table = file_id_table(ar)
        by_row = {e.index: e for e in ar.entries}
        _section3(check, ar, table, by_row, tmp, args)
        _section4(check, ar, table, by_row, tmp, args)
        _section5(check, ar, table, by_row)
        _section6(check, ar, table, by_row)


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
