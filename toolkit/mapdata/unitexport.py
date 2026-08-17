r"""Take one UNIT body out of `Gw.dat`: geometry + textures + the FA1 sidecar.

Rung U5 of `studies/unitmodels/PLAN.md`. A unit body is an ffna type-2 file
exactly like a prop model -- the two anchors decode through `modelfile.py`
unchanged -- so this module does not reimplement the interchange: it calls
`modelexport.build_manifest` / `texture_payloads` for the FA0/FA5 half and
adds ONE thing props do not have, the skeleton/animation chunk `0xFA1`,
serialised as a sidecar in the same `.gwmodel` family:

    unit_<id>.gwmodel.json    everything model_<id>.gwmodel.json carries,
                              plus a `skeleton` block (below)
    unit_<id>.fa1.bin         the 0xFA1 chunk payload, VERBATIM

    python toolkit/mapdata/unitexport.py --file-id 116366   # burrowing worm
    python toolkit/mapdata/unitexport.py --file-id 116703   # hatcher body

THE SKELETON BLOCK IS TYPED WHERE A NAME WAS EARNED, BYTES EVERYWHERE ELSE.
The typed half is exactly `skelfile.py`'s U1/U2 layer -- sequences (lo/hi
span, start/end clamp window), the n3C key table (SoA times + tags), the
per-node animation summary (n2C node count, link hierarchy, channel key
counts), blk48 track summaries, sound events, the n3E event track -- each
value read through the committed decoder and none invented here. The bytes
half is `unit_<id>.fa1.bin`: the WHOLE chunk payload verbatim, with every
block's (offset, size) span recorded in the manifest, so the blocks nobody
has decoded (n14, n34, n38, n44, n52, n50, n54..n57 contents; the six raw
sequence-record fields) are carried at full fidelity rather than dropped --
the same posture `modelexport` takes with `dat_fvf` bits 1/3, and what a
re-serializer (rung U6) preserves. A reader that wants more than the summary
decodes the sidecar with `skelfile.Skeleton.decode`; `skeleton_from_export`
does exactly that, and the test's read-back check rides it.

CHANNEL KEY DATA IS SUMMARISED, NOT RE-SERIALISED: the manifest carries each
node's key COUNTS while the times and values stay in the sidecar's bytes.
One reason: blk2C is 80,884 of the worm's 82,169 bytes, and a JSON copy
would double the export while creating a second, divergeable encoding of
data the .bin already carries exactly.

A FILE WITH NO 0xFA1 IS RECORDED, NOT SILENT: `skeleton.present = false`
with the reason, because the hatcher body (116703) is such a file and a
consumer must be able to tell "no skeleton" from "exporter predates the
sidecar". A COMPOSITED shell (FA1 but no FA0 -- geometry arrives from
elsewhere, GAME_SMSG 0x0057) is REFUSED here: this module exports bodies,
and assembling a shell's body from its linked files is rung U4's resolver,
not a guess this module should take.

WHERE THE OUTPUT MAY GO. A decoded mesh and a copied chunk are ArenaNet's
EXPRESSION, so `resolve_outdir()` refuses the working tree with no override,
default `vault/exports/units/` -- the guard DELEGATES to
`mapexport.resolve_outdir` exactly as `modelexport.py` does, one
implementation for all three exporters.

CONVENTIONS restated in the manifest so a consumer never guesses: key times
are int32 in units of 1e-5 s (`time_unit_s`; qword constant `0x00A571B0`,
build 38797); sequence `start`/`end` are windows on the FILE-GLOBAL track
timeline, NOT indices into the key table (that binding is REFUTED --
`skelfile.sequences`); node `base` vectors are in the SAME model space as
the FA0 vertices with z AS STORED (whether a base is parent-relative or
absolute is NOT MEASURED -- on the worm every deep link chains to a node at
the origin, so the two readings coincide there); `duration_s` is
`(end - start) * time_unit_s`, arithmetic on measured values.
"""

import argparse
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, file_id_table, DEFAULT_DAT  # noqa: E402
import modelexport  # noqa: E402
import modelfile  # noqa: E402
from modelfile import ModelFile, material_table  # noqa: E402
import skelfile  # noqa: E402
from skelfile import Skeleton  # noqa: E402
import mapexport  # noqa: E402
import vaultpath  # noqa: E402

#: Where a unit export lands by default. Inside the vault, beside the prop
#: models' `exports/models`.
DEFAULT_SUBDIR = "exports/units"

#: The sidecar kind of the verbatim FA1 payload.
KIND_FA1 = "fa1"


# ---------------------------------------------------------- where output goes

def resolve_outdir(outdir=None):
    """The directory a unit export may be written to. Refuses the tree.

    Delegates to `mapexport.resolve_outdir` rather than reimplementing the
    rule, exactly as `modelexport.resolve_outdir` does: two copies of a
    provenance guard is two chances to drift.
    """
    if outdir is None:
        outdir = vaultpath.vault_path(*DEFAULT_SUBDIR.split("/"))
    return mapexport.resolve_outdir(outdir)


# ------------------------------------------------------------- the sidecar

def _channel_count(pair):
    """Key count of one `(times, values)` channel, 0 when absent."""
    return 0 if pair is None else len(pair[0])


def skeleton_meta(sk, bin_name):
    """The manifest's `skeleton` block for one decoded `Skeleton`.

    Every value below is READ THROUGH the committed decoder (`skelfile.py`,
    rungs U1/U2); nothing is computed from the payload here except
    `duration` arithmetic, which the block labels. `bin_name` names the
    sidecar carrying the verbatim chunk payload.
    """
    h = sk.header
    seqs = []
    for i, s in enumerate(sk.sequences()):
        seqs.append({
            "index": i,
            "lo": s["lo"], "hi": s["hi"],
            "start": s["start"], "end": s["end"],
            "duration": s["end"] - s["start"],
            "duration_s": (s["end"] - s["start"]) * skelfile.KEYTIME_SCALE,
            # The six fields nothing has named, verbatim under offset names.
            "u8_00": s["u8_00"], "u32_01": s["u32_01"],
            "u32_0F": s["u32_0F"], "f32_13": s["f32_13"],
        })
    nodes = []
    for a in sk.anims():
        nodes.append({
            "link": a["link"],
            "base": list(a["base"]),
            "flags": a["flags"],
            "emitter_count": a["emitter_count"],
            "light_attach": a["light_attach"],
            "keys": {"trans": _channel_count(a["trans"]),
                     "rot": _channel_count(a["rot"]),
                     "aux": _channel_count(a["aux"])},
        })
    tracks = []
    for t in sk.tracks():
        tracks.append({
            "base": list(t["base"]), "flags": t["flags"], "u10": t["u10"],
            "looping": t["looping"],
            "keys": {"ch0": _channel_count(t["ch0"]),
                     "ch1": _channel_count(t["ch1"])},
        })
    ev_times, ev_recs = sk.event_track()
    return {
        "present": True,
        "chunk": f"0x{skelfile.SKELETON_CHUNK:X}",
        "sidecar": bin_name,
        "bytes": len(sk.payload),
        "version": h["ver"],
        "flags": h["flags"],
        "composited": sk.composited,
        "time_unit_s": skelfile.KEYTIME_SCALE,
        "header": dict(h),
        # Every block's byte span in the SIDECAR, in stream order, tiling it
        # exactly -- how a reader locates the blocks this manifest does not
        # decode. The spans are the walk's own (`skelfile._walk_spans`).
        "spans": [{"name": nm, "offset": off, "size": size}
                  for nm, off, size in sk.spans],
        "sequences": seqs,
        "keys": {"count": h["n3C"],
                 "times_raw": sk.key_times_raw(),
                 "tags": sk.key_tags()},
        "nodes": {"count": h["n2C"], "records": nodes},
        "tracks": {"count": h["n48"], "records": tracks},
        "sound_events": [{"seq": e["seq"], "time": e["time"],
                          "path_index": e["path_index"],
                          "raw_tail": e["raw_tail"].hex()}
                         for e in sk.sound_events()],
        "event_track": {"times": ev_times,
                        "records": [list(r) for r in ev_recs]},
        "conventions": {
            "times": "int32 in units of time_unit_s (1e-5 s; qword const "
                     "0x00A571B0, build 38797)",
            "sequence_window": "start/end clamp the FILE-GLOBAL track "
                               "timeline (MdlSeq 0x00792F56); lo/hi select "
                               "keys[lo:hi] of the n3C table. The "
                               "start/end-as-key-index reading is REFUTED "
                               "(skelfile.sequences).",
            "node_base": "model-space vec3, z AS STORED; parent-relative "
                         "vs absolute is NOT MEASURED (skelfile docstring)",
            "opaque": "channel key data and every unnamed block live in the "
                      "sidecar's verbatim bytes at the recorded spans; this "
                      "block is a summary, not a second encoding",
        },
    }


def build_unit_manifest(geo, name, source, mtable=None, fa1_payload=None):
    """The unit manifest and sidecar payloads, no file touched yet.

    `modelexport.build_manifest` for the geometry half, plus the `skeleton`
    block. Split out (same reason as modelexport's) so the round-trip test
    sections can run on synthetic bytes with no vault.
    """
    meta, payloads = modelexport.build_manifest(geo, name, source,
                                               mtable=mtable)
    if fa1_payload is None:
        meta["skeleton"] = {"present": False,
                            "reason": "the container carries no 0xFA1 chunk"}
        return meta, payloads
    sk = Skeleton.decode(bytes(fa1_payload))
    bin_name = f"{name}.fa1.bin"
    blob = bytes(fa1_payload)
    meta["skeleton"] = skeleton_meta(sk, bin_name)
    payloads = payloads + [(bin_name, blob)]
    meta["sidecars"].append(
        {"kind": KIND_FA1, "name": bin_name, "dtype": modelexport.DTYPE_BYTES,
         "count": len(blob), "bytes": len(blob),
         "sha256": hashlib.sha256(blob).hexdigest()})
    return meta, payloads


def skeleton_from_export(exp):
    """Re-decode a loaded export's FA1 sidecar with the committed decoder.

    `exp` is `modelexport.load_model`'s return (digests already verified).
    Returns a `skelfile.Skeleton`, or None when the export records no
    skeleton -- WHICH THE MANIFEST MUST SAY (`present: false`); an export
    with neither a skeleton block nor a sidecar predates this module and
    raises rather than reading as "no skeleton".
    """
    block = exp.meta.get("skeleton")
    if block is None:
        raise ValueError(f"{exp.meta.get('name')}: no skeleton block in the "
                         f"manifest -- not a unit export")
    if not block.get("present"):
        return None
    return Skeleton.decode(bytes(exp.arrays[KIND_FA1]))


# ------------------------------------------------------------- the export

def export_unit(file_id, archive, outdir=None, name=None, table=None,
                textures=True):
    """One unit body to an interchange on disk. Returns the JSON path.

    Refuses a file with no FA0 geometry chunk: a COMPOSITED shell's body
    arrives from its linked files (rung U4's resolver) and inventing one
    here would be fiction.
    """
    table = file_id_table(archive) if table is None else table
    row = table.get(file_id)
    if row is None:
        raise KeyError(f"no file id {file_id} in {archive.path}")
    entry = next(e for e in archive.entries if e.index == row)
    mf = ModelFile.decode(archive.read(entry))
    geo = mf.geometry()
    if geo is None:
        fa1 = mf.find(skelfile.SKELETON_CHUNK)
        why = ("a COMPOSITED shell: its body arrives from linked files "
               "(rung U4), and exporting it here would invent geometry"
               if fa1 is not None else "not a model this module can export")
        raise ValueError(f"file {file_id} carries no 0x{modelfile.GEOMETRY_CHUNK:X} "
                         f"geometry chunk -- {why}")
    name = name or f"unit_{file_id:X}"
    source = {"archive": os.path.basename(archive.path), "file_id": file_id,
              "row": row, "size": entry.size, "crc": entry.crc,
              "chunks": [f"0x{cid:X}" for cid, _p in mf.chunks]}
    meta, payloads = build_unit_manifest(
        geo, name, source,
        mtable=material_table(mf.find(modelfile.GEOMETRY_CHUNK)),
        fa1_payload=mf.find(skelfile.SKELETON_CHUNK))
    if textures:
        entries, tex_payloads, census = modelexport.texture_payloads(
            mf, name, archive, table=table)
        meta["textures"] = entries
        meta["texture_census"] = dict(census)
        payloads = payloads + tex_payloads
        for side_name, blob in tex_payloads:
            meta["sidecars"].append(
                {"kind": "texture", "name": side_name,
                 "dtype": modelexport.DTYPE_PNG, "count": 1,
                 "bytes": len(blob),
                 "sha256": hashlib.sha256(blob).hexdigest()})
    return modelexport.write_export(meta, payloads, resolve_outdir(outdir))


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--file-id", default=None,
                    help="one unit body, e.g. 116366 or 0x1C6AE")
    ap.add_argument("--out", default=None,
                    help="destination (default: vault/exports/units; the "
                         "working tree is refused)")
    ap.add_argument("--no-textures", action="store_true")
    ap.add_argument("--verify", default=None, metavar="JSON")
    args = ap.parse_args(argv)

    if args.verify:
        bad = modelexport.verify_manifest(args.verify)
        for line in bad:
            print(f"  [FAIL] {line}")
        if bad:
            return 1
        exp = modelexport.load_model(args.verify)
        print(f"[PASS] {args.verify} verifies")
        _report(exp)
        return 0

    if args.file_id is None:
        ap.error("give --file-id (or --verify)")
    with Archive(args.dat) as ar:
        path = export_unit(int(args.file_id, 0), ar, outdir=args.out,
                           textures=not args.no_textures)
        print(f"wrote {path}")
        _report(modelexport.load_model(path))
    return 0


def _report(exp):
    g = exp.meta["geometry"]
    print(f"  sub-models    {len(exp.submodels)}")
    print(f"  geometry      {g['vertices']} vertices, "
          f"{g['indices'] // 3} triangles")
    print(f"  max 2D radius {exp.max_2d_radius():.4f}")
    skel = exp.meta.get("skeleton") or {}
    if skel.get("present"):
        n_seq = len(skel["sequences"])
        durs = ", ".join(f"{s['duration_s']:.3f}" for s in skel["sequences"])
        print(f"  skeleton      {skel['bytes']} B FA1: {n_seq} sequence(s) "
              f"[{durs} s], {skel['keys']['count']} keys, "
              f"{skel['nodes']['count']} nodes, "
              f"{skel['tracks']['count']} tracks, "
              f"{len(skel['sound_events'])} sound events")
    else:
        print(f"  skeleton      absent "
              f"({skel.get('reason', 'no skeleton block')})")
    texs = [t for t in exp.meta.get("textures", []) if t.get("image")]
    if texs:
        print(f"  textures      {len(texs)} decoded to PNG")
    print(f"  sidecars      "
          + ", ".join(s["name"] for s in exp.meta["sidecars"]))


if __name__ == "__main__":
    sys.exit(_main())
