r"""Take one prop model out of `Gw.dat` and put it in a neutral interchange.

Rung M3 of `studies/models/PLAN.md`. `modelfile.py` decodes the geometry; this
module turns it into something a tool that knows nothing about ArenaNet's
archive can open -- the same bargain `mapexport.py` makes for terrain, and the
same rules. One model file becomes:

    model_<id>.gwmodel.json   sub-model table, formats, sidecar digests,
                              conventions, and where it came from
    model_<id>.pos.f32        every render vertex's x, y, z
    model_<id>.idx.u16        every triangle index                (optional)
    model_<id>.nrm.f32        every normal                        (optional)
    model_<id>.uv<n>.f32      texcoord set n, one file per set    (optional)
    model_<id>.raw<b>.bin     the UNNAMED fields, carried as bytes (optional)
    model_<id>.cpos.f32       collision-mesh vertices             (optional)
    model_<id>.cidx.u16       collision-mesh indices              (optional)

    python toolkit/mapdata/modelexport.py --file-id 0x1BAE2
    python toolkit/mapdata/modelexport.py --map 0x345CC     # every model a
                                                            #   map references

KEYED BY FILE ID, ONE FILE PER MODEL, and that is a measurement rather than a
preference: **80.1% of prop models are used by more than one map**
(`studies/customarea/FINDINGS.md` §5), so a per-map bundle would write the
same mesh hundreds of times. A map export names model file ids in its props
sidecar (`mapexport.build_props`) and a consumer resolves them here.

WHERE THE OUTPUT MAY GO. A decoded mesh is ArenaNet's EXPRESSION, not a
measurement of it, so this is the strictest case of the provenance gate:
`resolve_outdir()` REFUSES any destination inside the working tree, with no
flag to override, and the default is `vault/exports/models/`. The rule is
inherited from `mapexport.py` deliberately -- one implementation, one
behaviour -- and it is here FROM BIRTH because `atex.py` shipped a writer with
no guard at all and `--make C:\gw\Gw.dat` would have truncated the owner's
4.2 GB archive.

THE INTERCHANGE DE-INTERLEAVES, AND THAT IS WHAT MAKES IT CHECKABLE. A model
file stores vertices interleaved -- position, then whatever else the format
word says, at a stride of 20..84 bytes. This module splits them into typed
per-field arrays. That is a real transformation rather than a copy, so it can
be checked the hard way:

    re-interleave the exported arrays  ==  the archive's own vertex bytes

`test_modelexport.py` does exactly that, against bytes read fresh from
`Gw.dat` rather than from anything this module wrote. For it to be BYTE-EXACT
the export must account for every byte of the stride, including the two fields
nobody has named (`dat_fvf` bits 1 and 3) -- which is why they are carried, as
bytes, in `raw<b>.bin`. Nothing here interprets them, and the manifest says so.
An exporter that quietly dropped them would still produce a plausible mesh and
would fail that check on the first model that carries one.

WHAT THE ORACLE IS. `f11`, the placement radius in every prop record of every
map that uses this model, equals `scale * max(sqrt(x^2 + y^2))` over the
model's render vertices (M1/M2: 12,782 of 12,875 props). The test computes
that max from the EXPORTED position array, read back off disk, and compares
against the prop records in a map file this module never opens -- so a wrong
vertex range, a dropped sub-model, a byte-order slip or a truncated array all
move a number that two different files have to agree on.

TEXTURES (format_version 2, rung M5). Every `0x00000FA5` slot is resolved to
an archive row and decoded to a PNG sidecar at FULL RESOLUTION -- which only
became possible when the ATEX level codec landed, since 98.4% of containers
carry a compressed level 0. A sub-model names its slot in `texture`, from the
header word this module used to carry unnamed as `unk`. A slot that is null,
unresolvable or in a refused format is recorded WITH ITS REASON rather than
dropped.

WHAT IS NOT EXPORTED, so nobody reads absence as emptiness: the geometry
chunk's undecoded preamble, the trailing blocks, `0xFA1` (whose "texture
filenames" reading is REFUTED -- see `modelfile.texture_refs`) and the AMAT
materials (`0xFAD`), so a model's shading beyond its diffuse image is not
here. `NoClose` models cannot be exported at all and are REPORTED per map
rather than silently skipped -- a population M6 reduced to zero on both
reference maps.

CONVENTIONS THE MANIFEST STATES, because a consumer must never guess:

  1. **Positions are model-space**, the space the `f11` identity is written
     in. A prop places them with its own scale, rotation basis and position
     (`mapexport`'s props sidecar carries all three).
  2. **z is AS STORED.** Unlike the terrain interchange this module applies no
     sign flip: FINDINGS 25's negation is a fact about the WORLD's vertical
     axis, and whether a model's local frame shares it is NOT MEASURED. A
     consumer that negates terrain must decide for models on its own evidence,
     and `tools/blender/import_gwmap.py` records what it chose.
  3. **Triangles are a list, not a strip**: `ti % 3 == 0` on 3,834 of 3,834
     measured sub-models, every index below its own sub-model's vertex count.
  4. **Indices are per SUB-MODEL**, not global. Each sub-model's manifest entry
     carries its own base into the shared arrays.
  5. **Texcoords are not normalised** -- 97.8% inside +/-16 over a measured
     range of -519.7 .. 520.4. Wrap, never clamp.
"""

import argparse
import collections
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, file_id_table, DEFAULT_DAT  # noqa: E402
from mapfile import MapFile  # noqa: E402
from props import BloatedProps  # noqa: E402
import modelfile  # noqa: E402
from modelfile import (ModelFile, NoClose, Undecodable,  # noqa: E402
                       FIELD_NORMAL, FIELD_POSITION, FIELD_TEXCOORD_BITS,
                       FIELD_SIZE, material_table)
import mapexport  # noqa: E402
import atex  # noqa: E402
import png  # noqa: E402
import vaultpath  # noqa: E402

FORMAT = "rurik.gwmodel"
FORMAT_VERSION = 3
#: 1 is geometry only; 2 adds the OPTIONAL texture sidecars and the
#: per-sub-model binding, and changes nothing else, so both load.
FORMAT_VERSIONS_READ = (1, 2, 3)

DTYPE_F32 = "float32-le"
DTYPE_U16 = "uint16-le"
DTYPE_BYTES = "bytes"
#: A texture sidecar is a PNG written by `png.py` -- stdlib zlib, no
#: third-party dependency, and any tool opens it.
DTYPE_PNG = "png"

#: Where a model export lands by default. Inside the vault, like every other
#: derived-ArenaNet artifact in this repo.
DEFAULT_SUBDIR = "exports/models"

PROPS_BLOATED_CHUNK = 0x20000004
PROPS_DEPS_BLOATED = 0x21000004


class ModelExport:
    """One exported model, read back from disk. What `load_model` returns."""

    __slots__ = ("meta", "submodels", "arrays", "path")

    def __init__(self, meta, submodels, arrays, path=None):
        self.meta = meta
        self.submodels = submodels
        self.arrays = arrays
        self.path = path

    @property
    def file_id(self):
        return self.meta["source"]["file_id"]

    def positions(self, sub=None):
        """Model-space (x, y, z). One sub-model's, or every one in order."""
        pos = self.arrays["pos"]
        if sub is None:
            return pos
        s = self.submodels[sub]
        return pos[s["vertex_base"]:s["vertex_base"] + s["nv"]]

    def normals(self, sub):
        s = self.submodels[sub]
        base = s.get("normal_base")
        if base is None:
            return None
        return self.arrays["nrm"][base:base + s["nv"]]

    def tangent(self, sub, which=0):
        """Tangent-frame vector `which` (0 or 1), or None. WHICH IS TANGENT
        AND WHICH BINORMAL IS NOT ESTABLISHED -- see `modelfile.py`."""
        s = self.submodels[sub]
        base = (s.get("tangent_bases") or {}).get(str(which))
        if base is None:
            return None
        return self.arrays[f"tan{which}"][base:base + s["nv"]]

    def texcoords(self, sub, which=0):
        s = self.submodels[sub]
        base = (s.get("texcoord_bases") or {}).get(str(which))
        if base is None:
            return None
        return self.arrays[f"uv{which}"][base:base + s["nv"]]

    def triangles(self, sub):
        """Index triples, LOCAL to the sub-model's own vertex array."""
        s = self.submodels[sub]
        idx = self.arrays["idx"][s["index_base"]:s["index_base"] + s["ti"]]
        return [tuple(idx[i:i + 3]) for i in range(0, len(idx), 3)]

    def max_2d_radius(self):
        """max sqrt(x^2 + y^2) over every render vertex -- the model half of
        the f11 identity, recomputed from the EXPORTED array."""
        best = 0.0
        for x, y, _z in self.arrays["pos"]:
            h = x * x + y * y
            if h > best:
                best = h
        return best ** 0.5

    def __repr__(self):
        return (f"<ModelExport 0x{self.file_id:X}, {len(self.submodels)} "
                f"sub-model(s), {len(self.arrays['pos'])} vertices>")


# ---------------------------------------------------------- where output goes

def resolve_outdir(outdir=None):
    """The directory a model export may be written to. Refuses the tree.

    Delegates to `mapexport.resolve_outdir` rather than reimplementing the
    rule: two copies of a provenance guard is two chances to drift, and this
    one protects the more sensitive artifact of the two.
    """
    if outdir is None:
        outdir = vaultpath.vault_path(*DEFAULT_SUBDIR.split("/"))
    return mapexport.resolve_outdir(outdir)


# ------------------------------------------------------------- the manifest

def texture_payloads(model, name, archive, table=None):
    """Decode a model file's textures to PNG. `(entries, payloads, census)`.

    Each `0x00000FA5` slot becomes one entry naming its file id, the archive
    identity of the row it resolved to (size and crc -- a file id is archive
    STATE, so the id alone does not pin the bytes), and the PNG sidecar it
    was written to. A slot that is NULL, unresolvable, or in a format this
    decoder does not handle is recorded with a `skipped` reason rather than
    dropped, because a texture list with silent holes cannot be audited.

    Level 0 is exported -- the full-resolution image. That is only possible
    since the ATEX level codec landed: before it, 98.4% of containers had a
    compressed level 0 and the best available was a small raw mip.
    """
    if table is None:
        table = file_id_table(archive)
    by_row = getattr(archive, "_row_index", None)
    entries, payloads = [], []
    census = collections.Counter()
    written = {}
    for slot, file_id in enumerate(model.texture_refs()):
        entry = {"slot": slot, "file_id": file_id}
        if file_id is None:
            entry["skipped"] = "null slot"
            census["null"] += 1
            entries.append(entry)
            continue
        row = table.get(file_id)
        if row is None:
            entry["skipped"] = "file id not in the archive's table"
            census["unresolved"] += 1
            entries.append(entry)
            continue
        mft = archive.row(row)
        entry["row"] = row
        entry["size"] = mft.size
        entry["crc"] = mft.crc
        if file_id in written:
            entry["image"] = written[file_id]
            census["shared"] += 1
            entries.append(entry)
            continue
        try:
            data = archive.read(mft)
            if data[:4] == atex.DDS_MAGIC:
                got = atex.dds_rgba(data)
                if got is None:
                    entry["skipped"] = "a DDS shape this decoder refuses"
                    census["dds_refused"] += 1
                    entries.append(entry)
                    continue
                rgba, width, height = got
                census["dds"] += 1
            else:
                rgba, width, height = atex.decode_rgba(data)
                census["atex"] += 1
        except Exception as exc:                       # noqa: BLE001
            entry["skipped"] = f"{type(exc).__name__}: {exc}"
            census["error"] += 1
            entries.append(entry)
            continue
        # NAMED BY FILE ID ALONE, not by the model. 80.1% of prop models
        # are shared between maps and they share TEXTURES harder still --
        # naming these per model wrote 1,783 files and 110 MB for 485
        # distinct images. Same argument as one mesh datablock per model.
        fname = f"tex_{file_id:X}.png"
        payloads.append((fname, png.encode(rgba, width, height)))
        written[file_id] = fname
        entry.update(image=fname, width=width, height=height)
        entries.append(entry)
    return entries, payloads, census


def _material_entry(mtable, sub):
    """One sub-model's material, as the manifest carries it."""
    if mtable is None:
        return {"kind": "none"}
    kind, layers = mtable.for_submodel(sub)
    if kind != "layered":
        return {"kind": kind, "index": sub.unk & 0xFFFF}
    material = mtable.materials[sub.unk & 0xFFFF]
    return {"kind": "layered", "index": sub.unk & 0xFFFF,
            # `blend` is NON-ZERO on the materials that need real alpha
            # blending rather than opaque rendering. MEASURED on Kamadan:
            # 16 of 194 layered sub-models, and 14 of those draw one texture
            # -- a 512x128 mist band with 164 distinct alpha values and NOT
            # ONE fully opaque pixel. What the individual values MEAN (5, 6,
            # 8, 9, 10 occur) is NOT DECODED; that it separates blended from
            # opaque is what a consumer can use.
            "blend": material.blend,
            "material_flags": material.flags,
            "layers": [{"texpath": lay.texpath, "uv": lay.texarray,
                        "flags": lay.flags, "slot": lay.slot}
                       for lay in layers]}


def build_manifest(geo, name, source, mtable=None):
    """The JSON body and the sidecar payloads, with no file touched yet.

    Split out so the whole interchange can be built from a `ModelGeometry`
    that never came out of an archive -- which is what lets the round-trip
    sections of the test run on a bare machine.
    """
    pos, nrm, idx = [], [], []
    uvs = {}
    tangents = {}
    raw = {}
    subs = []
    for si, sm in enumerate(geo.submodels):
        fields = sm.fields
        entry = {
            "index": si,
            "dat_fvf": sm.dat_fvf,
            "stride": sm.stride,
            "nv": sm.nv,
            "ti": sm.ti,
            "counts": list(sm.counts),
            "u_counts": list(sm.u_counts),
            "unk": sm.unk,
            # A PER-SUB-MODEL INDEX, and what it indexes is NOT ESTABLISHED.
            # Same word as `unk`, kept beside it so the raw value stays
            # visible and a format-1 consumer is not broken.
            #
            # What IS measured: it is a real index rather than an ordinal or
            # a count. Over 1,076 sub-models of the two reference maps it
            # lands in [0, FA5 slot count) on 1,048 (97.4%) where the count
            # fields score 2-5%; on the 210 models carrying both several
            # sub-models and several textures it VARIES on 208 and reaches
            # >= 2 on 157. The one rival the range test could not separate,
            # `u2`, is ALL ZERO on all 210 and so is trivially in range
            # rather than an index. The exceptions are the shape that
            # settles that much: file 0x35140 reads [2, 3] over four slots
            # (an ordinal starts at 0) and 0x2D831 reads
            # [0,1,2,3,1,1,3,3,1,3,4,5,5] over nine (an ordinal never
            # repeats).
            #
            # **What is REFUTED is that it selects the DIFFUSE texture.**
            # Rendering Kamadan with this binding puts a specular/gloss map
            # on most building surfaces -- black with soft highlights --
            # while awnings and foliage come out right. So FA5 is a mixed
            # list of map kinds and this index does not name the colour one.
            # The likely chain is sub-model -> an AMAT material (chunk
            # 0xFAD, 457/457 resolving to files with that magic) -> the FA5
            # slot, and AMAT is NOT DECODED. Nothing here should be read as
            # "the diffuse texture is slot `material_index`".
            "material_index": sm.unk,
            # THE MATERIAL'S LAYERS, which is what actually binds a surface
            # to its textures (`modelfile.MaterialTable`). Each layer names
            # an FA5 slot (`texpath`, ArenaNet's texPathIndex) and the UV
            # SET it samples (`uv`; negative means generated, not stored).
            # A `kind` of "binary" means the material lives in the model's
            # AMAT list instead and no layers are given.
            "material": _material_entry(mtable, sm),
            "vertex_base": len(pos),
            "index_base": len(idx),
            "field_offsets": {str(b): o for b, o in sorted(fields.items())},
        }
        pos.extend(sm.positions())
        idx.extend(sm.indices)

        normals = sm.normals()
        if normals is not None:
            entry["normal_base"] = len(nrm)
            nrm.extend(normals)

        # The tangent frame, bits 12 and 13. Exported as its own arrays and
        # NOT folded into the normals: they are three different vectors and a
        # consumer that conflated them would light the mesh wrongly. Omitting
        # them was this module's first defect -- 24 bytes a vertex vanished on
        # every format that carries them, and only the re-interleave check
        # could see it.
        for k, vecs in enumerate(sm.tangent_frame()):
            if vecs is None:
                continue
            arr = tangents.setdefault(k, [])
            entry.setdefault("tangent_bases", {})[str(k)] = len(arr)
            arr.extend(vecs)

        bases = {}
        for w in range(len(FIELD_TEXCOORD_BITS)):
            uv = sm.texcoords(w)
            if uv is None:
                continue
            bases[str(w)] = len(uvs.setdefault(w, []))
            uvs[w].extend(uv)
        if bases:
            entry["texcoord_bases"] = bases

        # THE UNNAMED FIELDS. Bits 1 and 3 occupy real bytes and nothing has
        # established what they mean, so they are carried verbatim -- without
        # them the re-interleave check below could not be byte-exact, and an
        # exporter that dropped them would look correct on every mesh.
        rawbases = {}
        for bit in (1, 3):
            off = fields.get(bit)
            if off is None:
                continue
            size = FIELD_SIZE[bit]
            blob = b"".join(
                sm.vertex_data[i * sm.stride + off:
                               i * sm.stride + off + size]
                for i in range(sm.nv))
            rawbases[str(bit)] = len(raw.setdefault(bit, bytearray()))
            raw[bit].extend(blob)
        if rawbases:
            entry["raw_bases"] = rawbases
        subs.append(entry)

    collisions = []
    cpos, cidx = [], []
    for cm in geo.collisions:
        collisions.append({"vertex_base": len(cpos), "nv": len(cm.positions),
                           "index_base": len(cidx), "ni": len(cm.indices)})
        cpos.extend(cm.positions)
        cidx.extend(cm.indices)

    payloads = [("pos", f"{name}.pos.f32", DTYPE_F32,
                 _pack_vec3(pos), len(pos))]
    if idx:
        payloads.append(("idx", f"{name}.idx.u16", DTYPE_U16,
                         struct.pack(f"<{len(idx)}H", *idx), len(idx)))
    if nrm:
        payloads.append(("nrm", f"{name}.nrm.f32", DTYPE_F32,
                         _pack_vec3(nrm), len(nrm)))
    for k in sorted(tangents):
        payloads.append((f"tan{k}", f"{name}.tan{k}.f32", DTYPE_F32,
                         _pack_vec3(tangents[k]), len(tangents[k])))
    for w in sorted(uvs):
        vals = uvs[w]
        payloads.append((f"uv{w}", f"{name}.uv{w}.f32", DTYPE_F32,
                         struct.pack(f"<{2 * len(vals)}f",
                                     *[c for uv in vals for c in uv]),
                         len(vals)))
    for bit in sorted(raw):
        payloads.append((f"raw{bit}", f"{name}.raw{bit}.bin", DTYPE_BYTES,
                         bytes(raw[bit]), len(raw[bit])))
    if cpos:
        payloads.append(("cpos", f"{name}.cpos.f32", DTYPE_F32,
                         _pack_vec3(cpos), len(cpos)))
    if cidx:
        payloads.append(("cidx", f"{name}.cidx.u16", DTYPE_U16,
                         struct.pack(f"<{len(cidx)}H", *cidx), len(cidx)))

    meta = {
        "format": FORMAT,
        "format_version": FORMAT_VERSION,
        "name": name,
        "source": dict(source),
        "geometry": {
            "num_models": geo.num_models,
            "collision_count": geo.collision_count,
            "start": geo.start,
            "starts": list(geo.starts),
            "ambiguous": geo.ambiguous,
            "vertices": len(pos),
            "indices": len(idx),
        },
        "conventions": {
            "space": "model space; a prop applies its own scale, rotation "
                     "basis and position (see a map export's props sidecar)",
            "height_sign": "AS STORED -- no negation. FINDINGS 25's flip is "
                           "about the WORLD's vertical axis; whether a "
                           "model's local frame shares it is NOT MEASURED.",
            "topology": "triangle list, ti % 3 == 0 (3,834 of 3,834 measured "
                        "sub-models); indices are per sub-model, not global",
            "texcoords": "NOT normalised: 97.8% inside +/-16 over a measured "
                         "range of -519.7 .. 520.4. Wrap, never clamp.",
            "normals": "unit, MEASURED on 90,108 of 90,108 sampled vertices",
            "unnamed_fields": "dat_fvf bits 1 and 3 occupy bytes nobody has "
                              "named; carried verbatim in raw<bit>.bin so a "
                              "re-interleave is byte-exact. Bit 1 is a small "
                              "index (its D3DCOLOR reading is REFUTED); bit 3 "
                              "occurs in no corpus format.",
            "stride_source": f"the client's own tables at VA "
                             f"0x{modelfile.FVF0_VA:08X} / "
                             f"0x{modelfile.FVF1_VA:08X} / "
                             f"0x{modelfile.FVF2_VA:08X}, accessor "
                             f"0x{modelfile.FVF_ACCESSOR_VA:08X}, build "
                             f"{modelfile.FVF_BUILD}",
        },
        "submodels": subs,
        "collisions": collisions,
        "sidecars": [
            {"kind": kind, "name": fname, "dtype": dtype, "count": count,
             "bytes": len(blob), "sha256": hashlib.sha256(blob).hexdigest()}
            for kind, fname, dtype, blob, count in payloads
        ],
    }
    return meta, [(fname, blob) for _k, fname, _d, blob, _c in payloads]


def _pack_vec3(vecs):
    return struct.pack(f"<{3 * len(vecs)}f",
                       *[c for v in vecs for c in v])


def write_export(meta, payloads, outdir):
    """Write a built manifest and its sidecars. Returns the JSON path."""
    outdir = resolve_outdir(outdir)
    os.makedirs(outdir, exist_ok=True)
    for fname, blob in payloads:
        with open(os.path.join(outdir, fname), "wb") as fh:
            fh.write(blob)
    json_path = os.path.join(outdir, f"{meta['name']}.gwmodel.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
        fh.write("\n")
    return json_path


# ----------------------------------------------------------------- reading

def verify_manifest(json_path):
    """Every sidecar's size and sha256 against the manifest. `[]` means clean."""
    with open(json_path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    return _verify_meta(meta, os.path.dirname(os.path.abspath(json_path)))


def _verify_meta(meta, base):
    bad = []
    if meta.get("format") != FORMAT:
        bad.append(f"format is {meta.get('format')!r}, not {FORMAT!r}")
    if meta.get("format_version") not in FORMAT_VERSIONS_READ:
        bad.append(f"format_version is {meta.get('format_version')!r}, not "
                   f"one of {FORMAT_VERSIONS_READ}")
    for side in meta.get("sidecars", []):
        path = os.path.join(base, side["name"])
        if not os.path.isfile(path):
            bad.append(f"{side['name']}: missing")
            continue
        size = os.path.getsize(path)
        if size != side["bytes"]:
            bad.append(f"{side['name']}: {size} bytes on disk, manifest says "
                       f"{side['bytes']}")
            continue
        got = hashlib.sha256(open(path, "rb").read()).hexdigest()
        if got != side["sha256"]:
            bad.append(f"{side['name']}: sha256 {got[:16]}... does not match "
                       f"the manifest's {side['sha256'][:16]}...")
    return bad


def load_model(json_path):
    """Read a model export back. Refuses if any sidecar fails its digest."""
    json_path = os.path.abspath(json_path)
    base = os.path.dirname(json_path)
    with open(json_path, "r", encoding="utf-8") as fh:
        meta = json.load(fh)
    bad = _verify_meta(meta, base)
    if bad:
        raise ValueError("export does not verify:\n  " + "\n  ".join(bad))

    arrays = {}
    for side in meta["sidecars"]:
        blob = open(os.path.join(base, side["name"]), "rb").read()
        n = side["count"]
        if side["dtype"] == DTYPE_F32:
            per = 2 if side["kind"].startswith("uv") else 3
            flat = struct.unpack(f"<{per * n}f", blob)
            arrays[side["kind"]] = [tuple(flat[i * per:(i + 1) * per])
                                    for i in range(n)]
        elif side["dtype"] == DTYPE_U16:
            arrays[side["kind"]] = list(struct.unpack(f"<{n}H", blob))
        elif side["dtype"] == DTYPE_BYTES:
            arrays[side["kind"]] = blob
        elif side["dtype"] == DTYPE_PNG:
            # Verified by `_verify_meta` above (size and sha256) and then
            # left ON DISK. Decoding every texture into memory would cost a
            # model's whole texture set on every load, and every consumer of
            # a PNG wants a path -- Blender loads the file itself. The
            # manifest's `textures` list is the index.
            continue
        else:
            raise ValueError(f"{side['name']}: unknown dtype "
                             f"{side['dtype']!r}")
    if "pos" not in arrays:
        raise ValueError("export has no position sidecar")
    arrays.setdefault("idx", [])
    return ModelExport(meta, meta["submodels"], arrays, path=json_path)


# ------------------------------------------------------------- the export

def export_file_id(file_id, archive, outdir=None, name=None, table=None,
                   textures=True):
    """One model file to an interchange on disk. Returns the JSON path."""
    table = file_id_table(archive) if table is None else table
    row = table.get(file_id)
    if row is None:
        raise KeyError(f"no file id 0x{file_id:X} in {archive.path}")
    entry = next(e for e in archive.entries if e.index == row)
    mf = ModelFile.decode(archive.read(entry))
    geo = mf.geometry()
    if geo is None:
        raise ValueError(f"model 0x{file_id:X} carries no geometry chunk "
                         f"0x{modelfile.GEOMETRY_CHUNK:X}")
    name = name or f"model_{file_id:X}"
    source = {"archive": os.path.basename(archive.path), "file_id": file_id,
              "row": row, "size": entry.size, "crc": entry.crc,
              "chunks": [f"0x{cid:X}" for cid, _p in mf.chunks]}
    meta, payloads = build_manifest(geo, name, source,
                                    mtable=material_table(
                                        mf.find(
                                            modelfile.GEOMETRY_CHUNK)))
    if textures:
        entries, tex_payloads, census = texture_payloads(
            mf, name, archive, table=table)
        meta["textures"] = entries
        meta["texture_census"] = dict(census)
        payloads = payloads + tex_payloads
        for side_name, blob in tex_payloads:
            meta["sidecars"].append(
                {"kind": "texture", "name": side_name, "dtype": DTYPE_PNG,
                 "count": 1, "bytes": len(blob),
                 "sha256": hashlib.sha256(blob).hexdigest()})
    return write_export(meta, payloads, outdir)


def map_model_ids(map_file_id, archive, table=None):
    """Every model file id a map's props reference, in index order."""
    table = file_id_table(archive) if table is None else table
    row = table.get(map_file_id)
    if row is None:
        raise KeyError(f"no map file id 0x{map_file_id:X}")
    mf = MapFile.from_row(row, archive, strict=False)
    chunk = mf.find(PROPS_BLOATED_CHUNK)
    dep = mf.find(PROPS_DEPS_BLOATED)
    if chunk is None or dep is None:
        return []
    bp = BloatedProps.decode(chunk.payload())
    ids = dep.value.file_ids
    return [ids[i] for i in sorted({r.model for r in bp.records})
            if i < len(ids)]


def export_map_models(map_file_id, archive, outdir=None, table=None,
                      textures=True):
    """Every model a map references. Returns (written, skipped).

    `skipped` names the models that could not be decoded and why -- the ~15%
    whose sub-model array never closes are a REPORTED population, never a
    silent gap, because a consumer that sees 152 of 229 files needs to know
    the other 77 were refused rather than absent.
    """
    table = file_id_table(archive) if table is None else table
    written, skipped = [], []
    for fid in map_model_ids(map_file_id, archive, table=table):
        try:
            written.append(export_file_id(fid, archive, outdir=outdir,
                                          table=table, textures=textures))
        except NoClose as exc:
            skipped.append((fid, "NoClose", str(exc)[:90]))
        except (Undecodable, ValueError, KeyError) as exc:
            skipped.append((fid, type(exc).__name__, str(exc)[:90]))
    return written, skipped


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--file-id", default=None, help="one model, e.g. 0x1BAE2")
    ap.add_argument("--map", default=None,
                    help="every model a map references, e.g. 0x345CC")
    ap.add_argument("--out", default=None,
                    help="destination (default: vault/exports/models; the "
                         "working tree is refused)")
    ap.add_argument("--verify", default=None, metavar="JSON")
    args = ap.parse_args(argv)

    if args.verify:
        bad = verify_manifest(args.verify)
        for line in bad:
            print(f"  [FAIL] {line}")
        if bad:
            return 1
        exp = load_model(args.verify)
        print(f"[PASS] {args.verify} verifies")
        print(f"  {exp!r}")
        return 0

    if (args.file_id is None) == (args.map is None):
        ap.error("give exactly one of --file-id and --map")

    with Archive(args.dat) as ar:
        if args.file_id is not None:
            path = export_file_id(int(args.file_id, 0), ar, outdir=args.out)
            exp = load_model(path)
            print(f"wrote {path}")
            _report(exp)
        else:
            written, skipped = export_map_models(int(args.map, 0), ar,
                                                 outdir=args.out)
            print(f"map 0x{int(args.map, 0):X}: wrote {len(written)} model(s)")
            verts = tris = 0
            for p in written:
                e = load_model(p)
                verts += len(e.arrays["pos"])
                tris += len(e.arrays["idx"]) // 3
            print(f"  geometry      {verts} vertices, {tris} triangles")
            print(f"  skipped       {len(skipped)} model(s) that do not decode")
            for fid, kind, why in skipped[:5]:
                print(f"    0x{fid:X}  {kind}: {why}")
            if len(skipped) > 5:
                print(f"    ... and {len(skipped) - 5} more")
    return 0


def _report(exp):
    g = exp.meta["geometry"]
    print(f"  sub-models    {len(exp.submodels)}"
          + (f"  (AMBIGUOUS: closes at {g['starts']})" if g["ambiguous"]
             else ""))
    print(f"  geometry      {g['vertices']} vertices, "
          f"{g['indices'] // 3} triangles")
    for s in exp.submodels:
        named = []
        if s.get("normal_base") is not None:
            named.append("N")
        if s.get("texcoord_bases"):
            named.append(f"UV x{len(s['texcoord_bases'])}")
        if s.get("raw_bases"):
            named.append(f"raw {','.join(s['raw_bases'])}")
        print(f"    sub {s['index']}: {s['nv']} verts, {s['ti'] // 3} tris, "
              f"fvf 0x{s['dat_fvf']:X} stride {s['stride']}"
              + (f" [{', '.join(named)}]" if named else ""))
    if exp.meta["collisions"]:
        cv = sum(c["nv"] for c in exp.meta["collisions"])
        print(f"  collision     {len(exp.meta['collisions'])} mesh(es), "
              f"{cv} vertices")
    print(f"  max 2D radius {exp.max_2d_radius():.4f}  (the f11 identity's "
          f"model half)")
    print(f"  sidecars      "
          + ", ".join(s["name"] for s in exp.meta["sidecars"]))


if __name__ == "__main__":
    sys.exit(_main())
