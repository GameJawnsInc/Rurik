r"""The UNIT export: geometry re-interleave, the FA1 sidecar, the measured viewer.

    python toolkit/mapdata/test_unitexport.py
    python toolkit/mapdata/test_unitexport.py --no-blender   # skip section 3
                                                             # (fails the floor)

Rung U5 of `studies/unitmodels/PLAN.md`. Three claims, three kinds of check:

  1. **The geometry survives serialisation** -- the models-arc RE-INTERLEAVE:
     put the exported per-field arrays back together with a packer written in
     `test_modelexport.py` out of `struct.pack_into` (no code shared with any
     module under test) and compare against the FA0 chunk's own vertex bytes
     read FRESH from `Gw.dat`. Plus the position-sidecar check that reads the
     written file with `struct.unpack` and never through `load_model` -- the
     one check a stashing loader cannot dodge (that lesson is
     test_modelexport's, imported with the helpers).

  2. **The FA1 sidecar carries the decoder's values, unchanged, and the
     chunk's bytes, verbatim.** `unit_<id>.fa1.bin` off disk must equal the
     archive's own 0xFA1 payload byte-for-byte, and every typed value in the
     manifest's skeleton block -- sequence count, lo/hi, start/end,
     durations, key times/tags, node links, channel key counts -- must equal
     what `skelfile.Skeleton` decodes from the ARCHIVE, fresh, with the
     comparison function's own power proven by a tamper control beside it
     (a comparison that cannot fail is not a check). A file with no FA1
     (the hatcher body) must RECORD the absence; a manifest with no skeleton
     block at all must be refused by `skeleton_from_export`, so "old export"
     can never read as "no skeleton".

  3. **The viewer is MEASURED HEADLESS, never eyeballed** (the repo's
     "measure the scene, not the export"). Blender is driven as a subprocess
     (`tools/blender/import_gwunit.py`; this file never imports bpy) and
     everything asserted is computed from its dump or its rendered pixels:
     vertex/face counts against the manifest, the bounding box against the
     position sidecar (z NEGATED, the M4-measured model convention), the
     node empties against the blk2C bases, and the RENDER -- an orthographic
     silhouette whose alpha-coverage must be non-empty where the control
     frame (everything render-hidden) must measure ZERO, and whose pixel
     bounding box must match the extent PREDICTED from the export's own
     bbox through the dump's ortho scale, within 4 px. A render check whose
     control cannot go black would be decoration.

  THE POSE THAT SHIPPED IS THE FLAT PLACEMENT -- FA0 vertices as stored, no
  node transform applied -- and section 2 pins the measurement that makes
  that the BIND POSE rather than a guess: every channel-carrying node's base
  position falls INSIDE the mesh's own bounding box (18/18 on the worm; the
  two channel-less nodes sit at the origin). Applying per-node transforms to
  vertices would need a sub-model-to-node binding nothing has measured
  (3 sub-models, 20 nodes), so the flat placement is what is honest.

SECTIONS 0-1 NEED NO VAULT: the geometry is `test_modelfile.synth_geometry`
and the FA1 is `test_skelfile.synth_anim` -- struct.pack synthetics, zero
ArenaNet bytes. Sections 2-3 need `vault/dat_study/Gw.dat`; section 3 needs
Blender too. Each declares its skip naming what is missing, and the floor
then fails the run -- a machine without the archive has verified plumbing
and nothing about ArenaNet's bytes.
"""

import argparse
import copy
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
from archive import Archive, ffna_chunks, file_id_table  # noqa: E402
import modelexport  # noqa: E402
from modelexport import load_model, verify_manifest, write_export  # noqa: E402
from modelfile import ModelFile, ModelGeometry  # noqa: E402
import unitexport  # noqa: E402
from unitexport import (build_unit_manifest, export_unit,  # noqa: E402
                        resolve_outdir, skeleton_from_export)
import skelfile  # noqa: E402
from skelfile import Skeleton  # noqa: E402
import png  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402
# The re-interleaver and the loader-free sidecar reader are IMPORTED from
# test_modelexport rather than copied: they share no code with any module
# under test, and one copy of an instrument beats two that can drift.
from test_modelexport import reinterleave, _sidecar_positions  # noqa: E402
from test_modelfile import synth_geometry  # noqa: E402
from test_skelfile import synth_anim  # noqa: E402
from test_blenderimport import (find_blender, BLENDER_TIMEOUT,  # noqa: E402
                                PYTHON_EXIT_CODE)

REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
IMPORTER = os.path.join(REPO_ROOT, "tools", "blender", "import_gwunit.py")

#: The two anchors (`studies/unitmodels/FINDINGS.md` §2.4): the burrowing
#: worm is a self-contained unit body (FA0 + the 82,169-byte FA1 + FA5 +
#: FA6); the hatcher body is the plain 0x0057 geometry file, NO skeleton.
WORM_FILE_ID = 116366
HATCHER_FILE_ID = 116703

#: MEASURED 2026-08-16 on `vault/dat_study/Gw.dat` through the committed
#: decoders, pinned so a drift in either module moves a number two files
#: have to agree on.
WORM = dict(submodels=3, vertices=825, triangles=2618, textures=5,
            fa1_bytes=82169, seqs=10, keys=3, nodes=20, tracks=0,
            sound_events=6, radius=43.1509)
HATCHER = dict(submodels=4, vertices=1463, triangles=3746, textures=3,
               radius=18.9861)

#: Silhouette tolerance: the projected bbox is exact under an orthographic
#: camera, so the slack covers pixel quantisation and the alpha threshold's
#: edge behaviour only.
SIL_TOL_PX = 4
ALPHA_MIN = 26
#: The coverage floor is deliberately low: what carries the "non-empty"
#: claim is the CONTROL frame measuring exactly zero, and the hatcher body
#: is a thin shape -- MEASURED at 0.0147 of the frame (the worm: 0.0820),
#: so a 0.02 floor was refuted by the first real run and lowered.
COVER_MIN = 0.005

# FLOOR: 71, from a real green run on `vault/dat_study/Gw.dat` with Blender
# 5.1.1, 2026-08-16 (8.3 s; the three Blender runs are most of it).
# Sections 0-1 alone score 28 -- MEASURED by pointing --dat at a missing
# file, not counted by eye -- so a vault-less run lands 43 short and goes
# RED; a run with the archive but no Blender scores 52 (MEASURED with
# --no-blender) and lands 19 short, also RED. Both are deliberate:
# synthetics verify plumbing, and a scene nobody measured is not a viewer.
# 69 -> 71 the same day, when the hatcher's default render measured a
# floating head over an invisible torso and the --opaque control was added
# to pin why (its diffuse texture's alpha, wired as transparency by the
# inherited prop convention, is ~0 on 99.9% of texels).
#
# The first real run had TWO reds worth recording, both fixed the same day:
# 18/20 node empties were measured OFF their bases (the depsgraph had not
# evaluated the parent's matrix_world before the parent-inverse was taken
# from it -- background Blender evaluates nothing until asked), and the
# hatcher's silhouette refuted the guessed 0.02 coverage floor at 0.0147
# (see COVER_MIN). A check that finds two defects on its first contact with
# real data is earning its runtime.
FLOOR = 71


# ------------------------------------------------------------------ helpers

def raises(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except (ValueError, KeyError):
        return True
    return False


def _cc(pair):
    return 0 if pair is None else len(pair[0])


def sidecar_mismatches(block, sk):
    """Every typed skeleton value in the manifest vs a fresh `Skeleton`.

    Returns a list of mismatch strings; `[]` means every compared field
    agrees. Written HERE, field by field, rather than delegated to the
    module under test -- and the tamper control beside its call sites is
    what proves it can return non-empty.
    """
    bad = []
    seqs = sk.sequences()
    if len(block["sequences"]) != sk.seq_count:
        bad.append(f"sequence count {len(block['sequences'])} != "
                   f"{sk.seq_count}")
        return bad
    for i, (bs, ds) in enumerate(zip(block["sequences"], seqs)):
        for key in ("lo", "hi", "start", "end"):
            if bs[key] != ds[key]:
                bad.append(f"seq {i} {key}: {bs[key]} != {ds[key]}")
        if bs["duration"] != ds["end"] - ds["start"]:
            bad.append(f"seq {i} duration: {bs['duration']} != "
                       f"{ds['end'] - ds['start']}")
    if block["keys"]["count"] != sk.header["n3C"] \
            or block["keys"]["times_raw"] != sk.key_times_raw() \
            or block["keys"]["tags"] != sk.key_tags():
        bad.append("key table differs")
    an = sk.anims()
    if block["nodes"]["count"] != len(an):
        bad.append(f"node count {block['nodes']['count']} != {len(an)}")
    else:
        for i, (bn, dn) in enumerate(zip(block["nodes"]["records"], an)):
            if bn["link"] != dn["link"] or bn["base"] != list(dn["base"]):
                bad.append(f"node {i} link/base differs")
            want = {"trans": _cc(dn["trans"]), "rot": _cc(dn["rot"]),
                    "aux": _cc(dn["aux"])}
            if bn["keys"] != want:
                bad.append(f"node {i} keys {bn['keys']} != {want}")
    tr = sk.tracks()
    if block["tracks"]["count"] != len(tr):
        bad.append("track count differs")
    ev = sk.sound_events()
    got = [(e["seq"], e["time"], e["path_index"])
           for e in block["sound_events"]]
    if got != [(e["seq"], e["time"], e["path_index"]) for e in ev]:
        bad.append("sound events differ")
    return bad


def coverage(png_path):
    """`(fraction, bbox)` of alpha-covered pixels. bbox is (x0, x1, y0, y1)
    inclusive, or None when nothing is covered."""
    pixels, w, h, colour = png.read(png_path)
    if colour != png.COLOUR_RGBA:
        raise ValueError(f"{png_path}: colour {colour}, wanted RGBA")
    xs, ys, n = [], [], 0
    for y in range(h):
        row = (y * w) * 4
        for x in range(w):
            if pixels[row + x * 4 + 3] >= ALPHA_MIN:
                n += 1
                xs.append(x)
                ys.append(y)
    frac = n / float(w * h)
    box = (min(xs), max(xs), min(ys), max(ys)) if xs else None
    return frac, box


def run_gwunit(blender, json_path, workdir, tag, render=True, extra=()):
    """Run the unit importer headless. `(rc, output, summary)`."""
    dump = os.path.join(workdir, f"{tag}.summary.json")
    if os.path.exists(dump):
        os.remove(dump)
    cmd = [blender, "--background", "--factory-startup",
           "--python-exit-code", str(PYTHON_EXIT_CODE),
           "--python", IMPORTER, "--",
           json_path, "--dump", dump, "--clear"]
    if render:
        cmd += ["--render", os.path.join(workdir, tag)]
    cmd += list(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True,
                          timeout=BLENDER_TIMEOUT, errors="replace")
    out = (proc.stdout or "") + (proc.stderr or "")
    summary = None
    if os.path.isfile(dump):
        with open(dump, "r", encoding="utf-8") as fh:
            summary = json.load(fh)
    return proc.returncode, out, summary


# --------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=None)
    ap.add_argument("--blender", default=None)
    ap.add_argument("--no-blender", action="store_true",
                    help="skip section 3 (declared; the floor then fails)")
    args = ap.parse_args(argv)

    led = checks.Ledger("unit export", floor=FLOOR)
    check = checks.adopt(led)
    t0 = time.perf_counter()

    with tempfile.TemporaryDirectory(prefix="rurik_unitexport_") as tmp:
        _section0(check, tmp)
        _section1(check, tmp)
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
    print("\n== 0. a unit export may not land in the working tree ==")
    tree = _find_tree()
    for rel in ("", "toolkit", "studies"):
        target = os.path.join(tree, rel) if rel else tree
        check(raises(resolve_outdir, target),
              f"refuses to export a unit into the working tree "
              f"({rel or '.'})")
    # POSITIVE CONTROLS beside the refusals, or the guard proves nothing.
    vault_out = vaultpath.vault_path("exports", "units")
    check(resolve_outdir(vault_out) == os.path.abspath(vault_out),
          "the vault is allowed even though it sits inside the repo root")
    check(resolve_outdir(None) == os.path.abspath(vault_out),
          "the default destination is vault/exports/units")
    check(resolve_outdir(tmp) == os.path.abspath(tmp),
          "a scratch directory outside the tree is allowed")
    import mapexport
    check(unitexport.resolve_outdir.__module__ == "unitexport"
          and "mapexport.resolve_outdir" in
          (unitexport.resolve_outdir.__doc__ or ""),
          "the guard delegates to mapexport's rather than reimplementing it")
    check(raises(mapexport.resolve_outdir, tree)
          and raises(resolve_outdir, tree),
          "and both refuse the same tree")


# --- 1. a synthetic unit, no vault -----------------------------------------

def _section1(check, tmp):
    print("\n== 1. a synthetic unit exports and reads back (no vault) ==")
    geo = ModelGeometry.decode(synth_geometry())
    fa1 = synth_anim()
    meta, payloads = build_unit_manifest(
        geo, "syn_unit", {"archive": None, "file_id": 0x1234, "row": None},
        fa1_payload=fa1)
    out = os.path.join(tmp, "syn")
    path = write_export(meta, payloads, out)
    exp = load_model(path)

    check(verify_manifest(path) == [], "a freshly written unit export "
                                       "verifies (digests cover the sidecar)")
    skel = exp.meta["skeleton"]
    check(skel["present"] and skel["sidecar"] == "syn_unit.fa1.bin",
          "the manifest's skeleton block names its sidecar")
    disk = open(os.path.join(out, "syn_unit.fa1.bin"), "rb").read()
    check(disk == fa1,
          "the sidecar's bytes ARE the FA1 payload, verbatim off disk",
          f"{len(disk)} B")
    check(skel["spans"][0] == {"name": "header", "offset": 0, "size": 0x58}
          and sum(s["size"] for s in skel["spans"]) == len(fa1),
          "the recorded spans tile the sidecar exactly",
          f"{len(skel['spans'])} spans, {sum(s['size'] for s in skel['spans'])}"
          f"/{len(fa1)} B")

    # The typed layer, against the committed decoder run on the SOURCE bytes.
    sk = Skeleton.decode(fa1)
    check(sidecar_mismatches(skel, sk) == [],
          "every typed skeleton value equals the committed decoder's",
          "; ".join(sidecar_mismatches(skel, sk)[:2]) or "all agree")
    check(len(skel["sequences"]) == 1
          and skel["sequences"][0]["start"] == 0
          and skel["sequences"][0]["end"] == 100000
          and skel["sequences"][0]["duration"] == 100000
          and abs(skel["sequences"][0]["duration_s"] - 1.0) < 1e-9,
          "the planted sequence: start 0, end 100000, duration 1.0 s")
    check(skel["keys"] == {"count": 2, "times_raw": [0, 100000],
                           "tags": [2, 6]},
          "the planted key table (SoA times + tags)")
    check(skel["nodes"]["count"] == 1
          and skel["nodes"]["records"][0]["keys"] ==
          {"trans": 2, "rot": 2, "aux": 0},
          "the planted node summary: 1 node, 2 trans + 2 rot keys")
    check(skel["tracks"]["count"] == 1
          and skel["tracks"]["records"][0]["looping"]
          and skel["tracks"]["records"][0]["keys"] == {"ch0": 2, "ch1": 0},
          "the planted blk48 track, with its bit-27 loop flag")
    check(skel["sound_events"] == [{"seq": 0, "time": 50000,
                                    "path_index": 0,
                                    "raw_tail": "00" * 10}],
          "the planted sound event")
    check(skel["event_track"] == {"times": [0, 50000],
                                  "records": [[0, 0], [1, 5]]},
          "the planted n3E event track")

    # THE TAMPER CONTROLS: the comparison must be able to fail, one field
    # at a time, or the [] above is decoration.
    bent = copy.deepcopy(skel)
    bent["sequences"][0]["end"] += 1
    check(any("end" in m for m in sidecar_mismatches(bent, sk)),
          "a tampered sequence end is CAUGHT by the comparison")
    bent = copy.deepcopy(skel)
    bent["nodes"]["records"][0]["keys"]["rot"] = 3
    check(any("keys" in m for m in sidecar_mismatches(bent, sk)),
          "and so is a tampered channel key count")

    # Read-back through the committed decoder, off the written file.
    sk2 = skeleton_from_export(exp)
    check(sk2 is not None and sk2.payload == sk.payload
          and sk2.sequences() == sk.sequences(),
          "skeleton_from_export re-decodes the DISK sidecar to the same "
          "values")

    # A corrupted sidecar must be refused by name, like every other sidecar.
    blob = bytearray(disk)
    blob[len(blob) // 2] ^= 0xFF
    open(os.path.join(out, "syn_unit.fa1.bin"), "wb").write(bytes(blob))
    try:
        load_model(path)
        check(False, "a corrupted fa1.bin is refused by its sha256")
    except ValueError as exc:
        check("syn_unit.fa1.bin" in str(exc),
              "a corrupted fa1.bin is refused by its sha256, by name",
              str(exc)[:60])
    open(os.path.join(out, "syn_unit.fa1.bin"), "wb").write(disk)

    # ABSENCE IS RECORDED, and pre-sidecar manifests are refused.
    meta2, payloads2 = build_unit_manifest(
        geo, "syn_bare", {"archive": None, "file_id": 0x1235, "row": None},
        fa1_payload=None)
    path2 = write_export(meta2, payloads2, os.path.join(tmp, "syn_bare"))
    exp2 = load_model(path2)
    check(exp2.meta["skeleton"] == {"present": False,
                                    "reason": "the container carries no "
                                              "0xFA1 chunk"},
          "a unit with no FA1 records the absence, with its reason")
    check(skeleton_from_export(exp2) is None,
          "skeleton_from_export returns None for a recorded absence")
    del exp2.meta["skeleton"]
    check(raises(skeleton_from_export, exp2),
          "but a manifest with NO skeleton block at all is refused -- "
          "'old export' can never read as 'no skeleton'")

    # The geometry half rides modelexport unchanged; prove the plumbing on
    # bytes this file built, with the non-vacuity control beside it.
    both = all(reinterleave(exp, i) == bytes(geo.submodels[i].vertex_data)
               for i in range(len(geo.submodels)))
    check(both, "re-interleaving the synthetic unit reproduces both vertex "
                "blocks byte-for-byte")
    exp.arrays["pos"][0] = (0.0, 0.0, 0.0)
    check(reinterleave(exp, 0) != bytes(geo.submodels[0].vertex_data),
          "and one changed position breaks it -- the check is not vacuous")


# --- 2-3. the archive ------------------------------------------------------

def _vault_sections(check, led, args, tmp):
    dat = args.dat
    if dat is None:
        dat = os.path.join(vaultpath.vault_root(), "dat_study", "Gw.dat")
    if not os.path.isfile(dat):
        why = (f"no archive at {dat} (vault resolved to "
               f"{vaultpath.vault_root()}, {vaultpath.vault_why()})")
        led.skip("2. the anchors against ArenaNet's own bytes", why)
        led.skip("3. the measured Blender viewer", why)
        return
    with Archive(dat) as ar:
        table = file_id_table(ar)
        by_row = {e.index: e for e in ar.entries}
        paths = _section2(check, ar, table, by_row, tmp)
        _section3(check, led, args, paths, tmp)


def _section2(check, ar, table, by_row, tmp):
    print("\n== 2. the anchors: worm 116366 and hatcher body 116703 ==")
    out = os.path.join(tmp, "anchors")
    paths = {}
    for fid, want in ((WORM_FILE_ID, WORM), (HATCHER_FILE_ID, HATCHER)):
        jpath = export_unit(fid, ar, outdir=out, table=table)
        paths[fid] = jpath
        exp = load_model(jpath)
        data = ar.read(by_row[table[fid]])
        geo = ModelFile.decode(data).geometry()

        # (a) THE RE-INTERLEAVE, against bytes read fresh from the archive.
        ok = sum(1 for si, sm in enumerate(geo.submodels)
                 if reinterleave(exp, si) == bytes(sm.vertex_data))
        check(len(geo.submodels) == want["submodels"]
              and ok == want["submodels"],
              f"0x{fid:X}: re-interleave reproduces the archive's vertex "
              f"bytes on all {want['submodels']} sub-models",
              f"{ok}/{len(geo.submodels)}")
        # (b) the triangle lists, through the manifest's own bases.
        same = sum(1 for si, sm in enumerate(geo.submodels)
                   if list(sm.indices) ==
                   [i for t in exp.triangles(si) for i in t])
        check(same == want["submodels"],
              f"0x{fid:X}: every sub-model's triangle list reads back "
              f"exactly", f"{same}/{want['submodels']}")
        # (c) the position sidecar's own bytes, never through load_model.
        got = _sidecar_positions(jpath)
        want_pos = [p for sm in geo.submodels for p in sm.positions()]
        check(got == want_pos and len(got) == want["vertices"],
              f"0x{fid:X}: the position sidecar IS the archive's "
              f"{want['vertices']} vertices, read with struct.unpack")
        check(exp.meta["geometry"]["indices"] // 3 == want["triangles"],
              f"0x{fid:X}: the pinned triangle count",
              f"{exp.meta['geometry']['indices'] // 3}")
        # (d) the radius both ways: through the export, and fresh.
        fresh_r = max((x * x + y * y) for x, y, _z in want_pos) ** 0.5
        check(exp.max_2d_radius() == fresh_r
              and abs(fresh_r - want["radius"]) < 1e-3,
              f"0x{fid:X}: max 2D radius through the export equals the "
              f"fresh computation", f"{exp.max_2d_radius():.4f}")
        # (e) textures: every slot decoded, none skipped.
        imgs = [t for t in exp.meta["textures"] if t.get("image")]
        census = exp.meta["texture_census"]
        check(len(imgs) == want["textures"]
              and not census.get("unresolved") and not census.get("error"),
              f"0x{fid:X}: all {want['textures']} FA5 slots decoded to PNG",
              f"{census}")

    # -- the worm's skeleton sidecar ----------------------------------------
    wpath = paths[WORM_FILE_ID]
    exp = load_model(wpath)
    skel = exp.meta["skeleton"]
    data = ar.read(by_row[table[WORM_FILE_ID]])
    raw_fa1 = next(bytes(data[o:o + s]) for cid, o, s in ffna_chunks(data)
                   if cid == skelfile.SKELETON_CHUNK)
    disk = open(os.path.join(os.path.dirname(wpath),
                             skel["sidecar"]), "rb").read()
    check(disk == raw_fa1 and len(disk) == WORM["fa1_bytes"],
          f"the worm's fa1.bin off disk IS the archive's 0xFA1 payload, "
          f"byte-for-byte", f"{len(disk)}/{WORM['fa1_bytes']} B")

    sk_fresh = Skeleton.decode(raw_fa1)
    check(len(skel["sequences"]) == WORM["seqs"]
          and sk_fresh.seq_count == WORM["seqs"],
          f"sequence count off disk == the committed decoder's == "
          f"{WORM['seqs']}")
    mis = sidecar_mismatches(skel, sk_fresh)
    n_fields = (len(skel["sequences"]) * 5 + 1
                + len(skel["nodes"]["records"]) * 2 + 1
                + len(skel["sound_events"]))
    check(mis == [],
          f"every serialised skeleton value equals the fresh decode "
          f"({n_fields} field comparisons over {WORM['seqs']} sequences, "
          f"{WORM['nodes']} nodes, {WORM['sound_events']} sound events)",
          "; ".join(mis[:3]) or "all agree")
    # The control ON REAL DATA: the comparison must see one bent duration.
    bent = copy.deepcopy(skel)
    bent["sequences"][3]["start"] -= 1
    check(sidecar_mismatches(bent, sk_fresh) != [],
          "and it CATCHES one tampered start time on the real record")

    durs = [s["duration"] for s in skel["sequences"]]
    fresh_durs = [s["end"] - s["start"] for s in sk_fresh.sequences()]
    check(durs == fresh_durs and durs[0] == 200000 and durs[3] == 33333,
          "the durations survive serialisation unchanged",
          f"{[d * 1e-5 for d in durs]} s")
    check(skel["keys"]["times_raw"] == sk_fresh.key_times_raw()
          and skel["keys"]["count"] == WORM["keys"],
          f"the {WORM['keys']}-entry key table survives")
    check(skel["nodes"]["count"] == WORM["nodes"]
          and [r["link"] for r in skel["nodes"]["records"]] ==
          [a["link"] for a in sk_fresh.anims()],
          f"all {WORM['nodes']} node links survive")
    check(len(skel["sound_events"]) == WORM["sound_events"]
          and not skel["composited"]
          and skelfile.container_has_geometry(data),
          "sound events pinned; COMPOSITED is false and the container "
          "really does carry FA0 -- the bit 0 rule, on this file")

    # THE BIND-POSE MEASUREMENT: the flat placement is honest because the
    # stored vertices already stand around their skeleton. Every node that
    # carries an animation channel must have its base INSIDE the mesh's own
    # bbox (as stored, no negation anywhere on this path).
    pos = _sidecar_positions(wpath)
    lo = [min(p[i] for p in pos) for i in range(3)]
    hi = [max(p[i] for p in pos) for i in range(3)]
    animated = [r for r in skel["nodes"]["records"]
                if sum(r["keys"].values())]
    inside = sum(1 for r in animated
                 if all(lo[i] <= r["base"][i] <= hi[i] for i in range(3)))
    print(f"    mesh bbox {[round(v, 1) for v in lo]} .. "
          f"{[round(v, 1) for v in hi]}; {len(animated)} channel-carrying "
          f"nodes, {inside} inside")
    check(len(animated) == 18 and inside == 18,
          "every channel-carrying node's base falls INSIDE the stored "
          "mesh's bbox -- the measurement that makes the flat placement "
          "the BIND POSE rather than a guess", f"{inside}/{len(animated)}")

    # -- the hatcher records its absence ------------------------------------
    hexp = load_model(paths[HATCHER_FILE_ID])
    hdata = ar.read(by_row[table[HATCHER_FILE_ID]])
    has_fa1 = any(cid == skelfile.SKELETON_CHUNK
                  for cid, _o, _s in ffna_chunks(hdata))
    check(not has_fa1 and hexp.meta["skeleton"]["present"] is False
          and "no 0xFA1" in hexp.meta["skeleton"]["reason"],
          "the hatcher body carries no FA1 and its export SAYS so")
    check(skeleton_from_export(hexp) is None,
          "skeleton_from_export reads that absence as None")

    # -- a COMPOSITED shell is refused, not invented ------------------------
    check(raises(export_unit, 116228, ar, outdir=out, table=table),
          "the hatcher's geometry-less shell (116228) is REFUSED -- its "
          "body is rung U4's to assemble, not this module's to invent")
    return paths


# --- 3. the measured viewer ------------------------------------------------

def _section3(check, led, args, paths, tmp):
    print("\n== 3. Blender, headless and measured ==")
    if args.no_blender:
        led.skip("3. the measured Blender viewer", "--no-blender")
        return
    blender, why = find_blender(args.blender)
    if blender is None:
        led.skip("3. the measured Blender viewer", why)
        return
    print(f"    {blender} ({why})")

    # ---- the worm: body + skeleton + render -------------------------------
    wpath = paths[WORM_FILE_ID]
    exp = load_model(wpath)
    skel = exp.meta["skeleton"]
    rc, out, summ = run_gwunit(blender, wpath, tmp, "worm")
    check(rc == 0 and summ is not None,
          "the worm import exits 0 and writes its dump",
          f"rc {rc}" + ("" if summ else ", NO DUMP: " + out[-200:]))
    if summ is None:
        return
    m = summ["mesh"]
    check(m["vertex_count"] == WORM["vertices"]
          and m["face_count"] == WORM["triangles"]
          and m["submodels"] == WORM["submodels"],
          f"Blender's built mesh has the manifest's {WORM['vertices']} "
          f"vertices and {WORM['triangles']} faces",
          f"{m['vertex_count']}/{m['face_count']}")

    # The bbox against the POSITION SIDECAR, z negated (the M4 convention
    # the importer states); x and y must come through untouched.
    pos = _sidecar_positions(wpath)
    lo = [min(p[i] for p in pos) for i in range(3)]
    hi = [max(p[i] for p in pos) for i in range(3)]
    got_lo, got_hi = m["bbox"]["min"], m["bbox"]["max"]
    tol = 1e-4
    check(abs(got_lo[0] - lo[0]) < tol and abs(got_hi[0] - hi[0]) < tol
          and abs(got_lo[1] - lo[1]) < tol and abs(got_hi[1] - hi[1]) < tol,
          "the scene bbox's x/y equal the sidecar's")
    check(abs(got_lo[2] - -hi[2]) < tol and abs(got_hi[2] - -lo[2]) < tol,
          "and its z is the sidecar's NEGATED -- the measured model-space "
          "convention, stated once in import_gwmap.gwmodel_mesh",
          f"scene z {got_lo[2]:.2f}..{got_hi[2]:.2f}")
    check(abs(m["max_2d_radius"] - exp.max_2d_radius()) < 1e-3,
          "the scene's max 2D radius equals the export's (z negation "
          "cannot move it)", f"{m['max_2d_radius']:.4f}")
    check(m["material_slots"] == WORM["textures"]
          and len(m["images"]) == WORM["textures"]
          and m["faces_with_image"] == m["face_count"]
          and m["uv_layers"] == 1,
          f"all {WORM['textures']} textures bound, every face on an "
          f"imaged material, one UV layer",
          f"{m['faces_with_image']}/{m['face_count']} faces")

    # The node empties against the blk2C bases.
    nd = summ["skeleton"]
    recs = skel["nodes"]["records"]
    check(nd["present"] and nd["node_count"] == WORM["nodes"]
          and nd["roots"] == 1,
          f"{WORM['nodes']} node empties, one root (the one self-link)")
    placed = sum(
        1 for i, (n, r) in enumerate(zip(nd["nodes"], recs))
        if abs(n["location"][0] - r["base"][0]) < tol
        and abs(n["location"][1] - r["base"][1]) < tol
        and abs(n["location"][2] - -r["base"][2]) < tol)
    check(placed == WORM["nodes"],
          "every empty sits at its node's RAW base (z negated), world "
          "position kept through parenting", f"{placed}/{WORM['nodes']}")
    parents_ok = sum(
        1 for i, (n, r) in enumerate(zip(nd["nodes"], recs))
        if (n["parent"] is None) == (r["link"] == i)
        and (n["parent"] is None
             or n["parent"].endswith("node%02d" % r["link"])))
    check(parents_ok == WORM["nodes"],
          "and the parent of each is exactly its measured link",
          f"{parents_ok}/{WORM['nodes']}")

    # THE RENDER, measured. Coverage, the zero control, and the pixel bbox
    # against a prediction computed HERE from the export's own bbox.
    r = summ["render"]
    frac, box = coverage(r["body_png"])
    check(box is not None and COVER_MIN < frac < 0.9,
          "the body renders a non-empty, non-degenerate silhouette",
          f"coverage {frac:.4f}")
    efrac, ebox = coverage(r["empty_png"])
    check(efrac == 0.0 and ebox is None,
          "the hidden-everything control measures EXACTLY zero -- the "
          "instrument can read black")
    res = r["resolution"][0]
    scale = r["ortho_scale"]
    pred_w = (hi[0] - lo[0]) / scale * res
    pred_h = (hi[2] - lo[2]) / scale * res
    got_w = box[1] - box[0] + 1
    got_h = box[3] - box[2] + 1
    check(abs(got_w - pred_w) <= SIL_TOL_PX
          and abs(got_h - pred_h) <= SIL_TOL_PX,
          f"the silhouette's pixel bbox matches the bbox PREDICTED from "
          f"the export through the dump's ortho scale (+/-{SIL_TOL_PX}px)",
          f"{got_w}x{got_h} px vs {pred_w:.1f}x{pred_h:.1f}")

    # ---- the hatcher: a body with no skeleton -----------------------------
    rc, out, summ = run_gwunit(blender, paths[HATCHER_FILE_ID], tmp,
                               "hatcher")
    check(rc == 0 and summ is not None,
          "the hatcher import exits 0 and writes its dump", f"rc {rc}")
    if summ is None:
        return
    m = summ["mesh"]
    check(m["vertex_count"] == HATCHER["vertices"]
          and m["face_count"] == HATCHER["triangles"]
          and m["submodels"] == HATCHER["submodels"],
          f"the hatcher mesh has {HATCHER['vertices']} vertices, "
          f"{HATCHER['triangles']} faces",
          f"{m['vertex_count']}/{m['face_count']}")
    check(summ["skeleton"] == {"present": False, "node_count": 0,
                               "roots": 0, "nodes": []},
          "and NO node empties -- absence stays absence in the scene")
    frac, box = coverage(summ["render"]["body_png"])
    check(box is not None and COVER_MIN < frac < 0.9,
          "the hatcher renders a non-empty silhouette too",
          f"coverage {frac:.4f}")
    hpos = _sidecar_positions(paths[HATCHER_FILE_ID])
    hlo = [min(p[i] for p in hpos) for i in range(3)]
    hhi = [max(p[i] for p in hpos) for i in range(3)]
    scale = summ["render"]["ortho_scale"]
    res = summ["render"]["resolution"][0]
    pred_w = (hhi[0] - hlo[0]) / scale * res
    pred_h = (hhi[2] - hlo[2]) / scale * res
    got_w = box[1] - box[0] + 1
    got_h = box[3] - box[2] + 1
    check(abs(got_w - pred_w) <= SIL_TOL_PX
          and abs(got_h - pred_h) <= SIL_TOL_PX,
          f"and its silhouette bbox matches its prediction "
          f"(+/-{SIL_TOL_PX}px)",
          f"{got_w}x{got_h} px vs {pred_w:.1f}x{pred_h:.1f}")

    # THE ALPHA FINDING, measured on pixels: the hatcher's bound diffuse
    # texture carries alpha < 26/255 on 99.9% of its texels (MEASURED on
    # tex_1C7DB.png), and the prop-path convention wires texture alpha into
    # the shader, so the DEFAULT render is a floating head over an
    # invisible torso. What a unit texture's alpha means is NOT DECODED
    # (the AMAT chain); --opaque is the display control, and the coverage
    # gap between the two renders is the measurement that pins the finding.
    rc, out, osumm = run_gwunit(blender, paths[HATCHER_FILE_ID], tmp,
                                "hatcher_op", extra=("--opaque",))
    check(rc == 0 and osumm is not None and osumm.get("opaque") is True,
          "the hatcher imports with --opaque and the dump says so",
          f"rc {rc}")
    if osumm is not None:
        ofrac, obox = coverage(osumm["render"]["body_png"])
        check(obox is not None and ofrac > 3 * frac,
              "--opaque at least triples the hatcher's silhouette coverage "
              "-- the measured cost of wiring unit texture alpha as "
              "transparency", f"{frac:.4f} -> {ofrac:.4f}")


if __name__ == "__main__":
    sys.exit(main())
