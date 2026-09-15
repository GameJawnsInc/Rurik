r"""The browsable catalog behind the model viewer: every model head in the
archive, classified from its first chunk header, plus the textured,
de-indexed build of one model that a renderer can draw. READ ONLY.

    python toolkit/mapdata/modelcatalog.py --scan            # build + cache
    python toolkit/mapdata/modelcatalog.py --file-id 116703  # one model's facts
    python toolkit/mapdata/modelcatalog.py --templates       # content npc rows

WHAT THIS IS FOR. `tools/viewer/modelviewer.py` (PySide6, outside `toolkit/`
because of the stdlib rule) is a GUI over this module and holds no archive
knowledge of its own: every byte it draws comes through here, through the
decoders the models/unitmodels arcs committed -- `modelfile.py` for geometry
and materials, `atex.py`/`dxt1.py` for textures, `skelfile.py` for the
skeleton, `unitassembly.py` for a template's shell -> body closure. Nothing
here re-implements a layout; the one thing it adds is the SCAN below, and the
scan is a shortcut with a test that can refute it.

THE SCAN READS A PREFIX, NOT THE FILE. A full decode of every flags-515 head
is the reference index's "twenty-minute CLI run" (`refindex.build`); a
catalog that took that long to open would not be browsed. MEASURED
2026-09-14 on `vault/dat_study/Gw.dat`, 400 random heads: **when a head
carries a 0xFA0 geometry chunk it is the FIRST chunk, 400 of 400**, and the
other first chunks are 0xFA1 (an anim-only or composited shell) or 0xFA6 (a
shell whose sound list precedes its skeleton). So `archive.magic(entry, n)`
-- the decompressor asked to stop after `n` bytes -- classifies a head in
~0.5 ms against ~34 ms for the full read: 0.22 s versus 13.6 s over the same
400. The prefix is `PREFIX_BYTES` long: magic + type, one chunk header, and
enough payload for FA0's `num_models`/`collision_count` or FA1's 0x58-byte
header (sequence count, node count, the COMPOSITED flag). An FA6-first head
costs one more prefix read that reaches past its sound list to the FA1 header.

THE KIND IS TWO-WAY, AND WHY IT IS NOT THREE. A head with no FA0 is either a
creature SHELL -- a skeleton whose geometry the wire supplies as 0x0057 body
ids per definition -- or an ANIM FILE, ArenaNet's word (`MdlBloat: unable to
find anim file`) for a skeleton another model reaches through its FA8 link
list for extra sequences. Both are worth telling apart in a browser, and this
module tried to and could not, twice, MEASURED 2026-09-14 on all 759
geometry-less heads of `vault/dat_study/Gw.dat`:

  * `MODEL_SKELETON_FLAG_COMPOSITED` (FA1 header bit 0, MdlBuild:1556) does
    not do it: it is set on 759 of 759. That is the unitmodels result read
    the other way -- the flag is equivalent to "no FA0 chunk" on every FA1
    in the archive (14,571/14,571), so it says "no geometry here", not "a
    body will arrive".
  * FA8 linkage does not do it either: 394 of the 759 are link targets of
    another skeleton head (and every FA8 target in the population IS a
    skeleton head: 394/394, 0 models, 0 non-heads), but 13 of the 32 shells
    the live wire has named as creatures are targets too. Shells link to
    shells. The 311 FA1-only heads (no FA6, no FA8) match the ~312 "anim
    file" class unitmodels sec 2.3 counted, and that is the nearest thing to
    a structural tell -- a floor, not a rule.

So the archive-side kind is `skel`, and the label that answers "is this a
creature I can see?" comes from OUTSIDE the archive: `content/npcs.toml`'s
rows, which name a shell and its bodies because a capture did (0x0056 +
0x0057), and which `shell_templates()` joins onto the catalog. A skeleton
head with no row is honestly unknown -- shell nobody has spawned, or anim
file -- and the viewer says so rather than picking.

    The shortcut's failure mode is a geometry chunk that is NOT first, and
    the catalog would then file a model as a shell. `test_modelcatalog.py`
    re-walks a strided sample of heads in full and asserts the prefix
    classification agrees with the whole chunk list on every one -- a check
    the archive can fail. A build that broke the ordering would redden it,
    not silently shrink the model list.

THE CACHE IS STAMPED, AND A STALE ONE IS REFUSED. The scan result lands under
`vault/cache/modelcatalog/` keyed by the archive's MFT sha256 -- the identity
`refindex.stamp_of` defines, reused rather than re-typed -- and `load` refuses
a cache built from another archive state exactly as `refindex.load` does,
because a catalog answering for rows that have since moved is the same wrong
answer that module was written to never give. The vault directory is the only
place the cache may go (`vaultpath.resolve_out`); a cache of ArenaNet file
ids and chunk counts is measurement, but it is a measurement of the owner's
archive and it stays with the archive.

THE BUILD IS DE-INDEXED ON PURPOSE. `SubMesh.pos/nrm/uv` are flat float
arrays with three corners per triangle, not the archive's indexed vertices --
a renderer with only `glDrawArrays` (the portable subset a Qt widget exposes
without a native binding) can draw them directly, and the test's check is the
one that matters: gathering the sub-model's own `positions()` through its own
`indices` reproduces `pos` exactly, so no corner was invented or dropped.

THE DIFFUSE RULE IS THE BLENDER IMPORTER'S, imported as a fact rather than
re-derived: a sub-model's material is `mtlIndex` into the layered table, and
its diffuse is the FIRST LAYER SAMPLING A STORED UV SET (`texarray >= 0`) --
not layer 0, because 92 of Kamadan's 1,063 layered sub-models put a generated
(environment) layer first and those rendered black (models FINDINGS §6.1).
That layer's `texpath` names the FA5 slot and its `texarray` the UV set the
corners carry. A binary (AMAT) material or a sub-model whose layers are all
generated gets `texture_fid = None` and the viewer draws it flat -- stated,
never guessed. Which of the OTHER layers is detail, lightmap or specular is
still open and this module does not pretend otherwise: it carries them as
`layers` for display.

ALPHA IS NOT ALWAYS TRANSPARENCY. `modelexport._alpha_class` (opaque / cutout
/ erases) travels with every texture because seven of Kamadan's prop textures
and the hatcher's own picked diffuse are "erasers" whose alpha would delete
the surface (unitexport FINDINGS §5). A consumer that alpha-tests must skip
those; `SubMesh.alpha` says which.

CONVENTIONS A RENDERER NEEDS, all measured elsewhere and only restated:
  * model-space -z is world-up (import_gwmap convention 4: "far into
    negative z -- which is UP once negated"); `UP = (0, 0, -1)`.
  * UVs are Direct3D's -- v = 0 is the TOP row -- and unnormalised, so wrap.
  * blk2C node bases are ABSOLUTE rest positions in the same model space as
    the body's vertices (unitexport §3: every channel-carrying base falls
    inside the mesh's own box), so a skeleton draws over its body untransformed.
"""

import argparse
import collections
import hashlib
import json
import os
import struct
import sys
import time
from array import array

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

from archive import Archive, DEFAULT_DAT, FFNA_MAGIC, ffna_chunks, \
    ffna_type, file_id_table  # noqa: E402
import atex  # noqa: E402
import modelfile  # noqa: E402
from modelfile import ModelFile, GEOMETRY_CHUNK, SKELETON_CHUNK, \
    TEXNAME_CHUNK_B, MODEL_FFNA_TYPE  # noqa: E402
import modelexport  # noqa: E402
import refindex  # noqa: E402
from refindex import HEAD_FLAGS, head_rows, display_id, stamp_of  # noqa: E402
import skelfile  # noqa: E402
import vaultpath  # noqa: E402

#: magic(4) + type(1) + one chunk header(8) + the larger payload head we read:
#: FA1's 0x58-byte header. FA0 needs only 0x4E (collision_count is a u16 at
#: +0x4C), so the same prefix serves both.
CHUNK_HEADER = 8
PAYLOAD_AT = 5 + CHUNK_HEADER
PREFIX_BYTES = PAYLOAD_AT + 0x58

SOUND_CHUNK = 0x00000FA6

KIND_MODEL = "model"        # first chunk 0xFA0: the file carries geometry
KIND_SKEL = "skel"          # an FA1 skeleton and NO geometry: a creature shell
                            #   whose body arrives on the wire (0x0057), or an
                            #   anim file another model links to (FA8). The
                            #   archive does not say which -- see the docstring.
KIND_OTHER = "other"        # a head this classifier does not name

#: 2 (2026-09-14): the geometry-less kind renamed and the FA6/FAE-first heads
#: resolved by a chained prefix read. A version-1 cache carries the old kind
#: word, so it is refused and re-scanned.
FORMAT_VERSION = 2

#: How many chunk headers `scan` will chase before the FA1 on a head whose
#: skeleton is not first. The archive needs two (FA6, FAE -> FA1); three is
#: the margin, not a measurement.
MAX_CHAIN = 3
UP = (0.0, 0.0, -1.0)


# ---------------------------------------------------------------------------
# The scan
# ---------------------------------------------------------------------------

class HeadRecord:
    """One flags-515 head as the catalog lists it."""

    __slots__ = ("row", "fids", "size", "first_chunk", "first_size", "kind",
                 "num_models", "collision_count", "seq_count", "node_count",
                 "composited", "problem")

    def __init__(self, row, fids, size):
        self.row = row
        self.fids = list(fids)
        self.size = size                    # bytes on disk (compressed)
        self.first_chunk = None
        self.first_size = None
        self.kind = KIND_OTHER
        self.num_models = None
        self.collision_count = None
        self.seq_count = None
        self.node_count = None
        self.composited = None
        self.problem = None

    @property
    def fid(self):
        """The reported id -- `refindex.display_id`'s convention, a label."""
        return display_id(self.fids) if self.fids else None

    def to_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}

    @classmethod
    def from_dict(cls, d):
        rec = cls(d["row"], d["fids"], d["size"])
        for k in cls.__slots__[3:]:
            setattr(rec, k, d.get(k))
        return rec


def classify_prefix(prefix):
    """What the first `PREFIX_BYTES` of a head say about it. Pure.

    Returns a dict with `first_chunk`, `first_size`, `kind` and the
    chunk-specific counts, or a `problem` string when the bytes are not an
    ffna type-2 file. Never raises on short input: a head shorter than the
    prefix is a fact about the head and is recorded as such.
    """
    out = {"first_chunk": None, "first_size": None, "kind": KIND_OTHER,
           "num_models": None, "collision_count": None, "seq_count": None,
           "node_count": None, "composited": None, "problem": None}
    if prefix[:4] != FFNA_MAGIC:
        out["problem"] = f"not ffna: {bytes(prefix[:4])!r}"
        return out
    if ffna_type(prefix) != MODEL_FFNA_TYPE:
        out["problem"] = f"ffna type {ffna_type(prefix)}, not {MODEL_FFNA_TYPE}"
        return out
    if len(prefix) < PAYLOAD_AT:
        out["problem"] = f"{len(prefix)} bytes: no chunk header"
        return out
    cid, size = struct.unpack_from("<II", prefix, 5)
    out["first_chunk"], out["first_size"] = cid, size
    body = prefix[PAYLOAD_AT:PAYLOAD_AT + size]
    if cid == GEOMETRY_CHUNK:
        out["kind"] = KIND_MODEL
        if len(body) >= modelfile.COLLISION_COUNT_AT + 2:
            out["num_models"] = struct.unpack_from(
                "<I", body, modelfile.NUM_MODELS_AT)[0]
            out["collision_count"] = struct.unpack_from(
                "<H", body, modelfile.COLLISION_COUNT_AT)[0]
        else:
            out["problem"] = f"FA0 payload prefix is {len(body)} bytes"
    elif cid == SKELETON_CHUNK:
        _fa1_facts(body, out)
        out["kind"] = KIND_SKEL if out["problem"] is None else KIND_OTHER
    else:
        # A skeleton file whose sound (FA6) or FAE list precedes its FA1 --
        # 2% of heads. The FA1 header sits past those lists, so `scan` reads a
        # longer prefix and `classify_chain` walks the headers to it; until
        # then the kind is unresolved and says so.
        out["problem"] = (f"first chunk 0x{cid:X}: the FA1 header, if any, "
                          f"is past it")
    return out


def classify_chain(prefix, at):
    """Walk chunk headers from offset `at` to the FA1 and read its header. Pure.

    For a head whose first chunk is not FA0/FA1 (FA6 or FAE lists come first
    on 2% of heads). Returns the FA1 facts and `kind`, or a problem naming
    where the walk stopped: a prefix that ends before the header, a chain
    longer than `MAX_CHAIN`, or a geometry chunk found late (which would
    refute the FA0-first measurement and is reported, never filed as a
    model on the quiet).
    """
    out = {"kind": KIND_OTHER, "seq_count": None, "node_count": None,
           "composited": None, "problem": None}
    for _hop in range(MAX_CHAIN):
        if len(prefix) < at + CHUNK_HEADER:
            out["problem"] = (f"prefix of {len(prefix)} bytes ends before a "
                              f"chunk header at {at}")
            return out
        cid, size = struct.unpack_from("<II", prefix, at)
        if cid == SKELETON_CHUNK:
            body = prefix[at + CHUNK_HEADER:at + CHUNK_HEADER + size]
            _fa1_facts(body, out)
            out["kind"] = KIND_SKEL if out["problem"] is None else KIND_OTHER
            return out
        if cid == GEOMETRY_CHUNK:
            out["problem"] = (f"a geometry chunk at offset {at}, NOT first -- "
                              f"refutes the FA0-first measurement; re-check")
            return out
        at += CHUNK_HEADER + size
    out["problem"] = f"no FA1 within {MAX_CHAIN} chunks"
    return out


def _fa1_facts(body, out):
    if len(body) < 0x58:
        out["problem"] = f"FA1 header prefix is {len(body)} bytes"
        return
    ver = struct.unpack_from("<I", body, 0)[0]
    if ver != skelfile.SKELETON_VERSION:
        out["problem"] = f"FA1 version 0x{ver:X}"
        return
    out["seq_count"] = struct.unpack_from("<I", body, skelfile.HDR["n18"])[0]
    out["node_count"] = struct.unpack_from("<I", body, skelfile.HDR["n2C"])[0]
    out["composited"] = bool(body[skelfile.HDR["flags"]]
                             & skelfile.FLAG_COMPOSITED)


def spellings_by_row(ar):
    """Row -> every file id naming it, from the CLIENT's table (raw=True),
    the inversion `refindex.build` uses so both tools name a row alike."""
    by_row = {}
    for fid, row in file_id_table(ar, raw=True).items():
        by_row.setdefault(row, []).append(fid)
    for fids in by_row.values():
        fids.sort()
    return by_row


class Catalog:
    """Every head of one archive, with the facts the prefix scan yields."""

    def __init__(self, stamp, records, scanned_rows=None):
        self.stamp = stamp
        self.records = list(records)
        self.scanned_rows = (len(self.records) if scanned_rows is None
                             else scanned_rows)
        self.by_row = {r.row: r for r in self.records}
        self.by_fid = {}
        for r in self.records:
            for f in r.fids:
                self.by_fid[f] = r

    def models(self):
        return [r for r in self.records if r.kind == KIND_MODEL]

    def skeletons(self):
        """Every head with an FA1 skeleton and no geometry -- creature shells
        AND anim files, which the archive does not tell apart (docstring)."""
        return [r for r in self.records if r.kind == KIND_SKEL]

    def shells(self):
        """Kept as a name: the same population as `skeletons()`."""
        return self.skeletons()

    def census(self):
        return dict(collections.Counter(r.kind for r in self.records))

    def to_dict(self):
        return {"format_version": FORMAT_VERSION, "stamp": self.stamp,
                "scanned_rows": self.scanned_rows,
                "records": [r.to_dict() for r in self.records]}

    @classmethod
    def from_dict(cls, d):
        return cls(d["stamp"], [HeadRecord.from_dict(x) for x in d["records"]],
                   d.get("scanned_rows"))


def scan(ar, rows=None, progress=None):
    """Classify every head (or `rows`, a subset of ROW numbers) from its prefix.

    `progress(n, total)` is called every 500 heads when given, so a GUI can
    show the bar; a library call passes nothing and stays silent.
    """
    by_row = spellings_by_row(ar)
    walk = head_rows(ar) if rows is None else sorted(set(rows))
    records = []
    for n, row in enumerate(walk, 1):
        if progress and n % 500 == 0:
            progress(n, len(walk))
        entry = ar.row(row)
        rec = HeadRecord(row, by_row.get(row, ()), entry.size)
        if not rec.fids:
            rec.problem = "no file id in the raw table names this head row"
            records.append(rec)
            continue
        try:
            prefix = ar.magic(entry, PREFIX_BYTES)
        except Exception as exc:                            # noqa: BLE001
            # Broad on purpose, as `refindex.build` is: one damaged row must
            # not end the scan, and the row is named rather than dropped.
            rec.problem = f"{type(exc).__name__}: {exc}"
            records.append(rec)
            continue
        for k, v in classify_prefix(prefix).items():
            setattr(rec, k, v)
        if rec.first_chunk not in (GEOMETRY_CHUNK, SKELETON_CHUNK, None) \
                and rec.first_size is not None:
            # chase the chain ONE chunk header at a time, each read sized
            # exactly by the header before it. Not a single long read: the
            # early-stopping decoder raises `backtrack >= produced` when asked
            # for more bytes than the file decompresses to (rows 48660 and
            # 151293, 9,322 and 4,455 bytes, against a 12 KB ask -- MEASURED
            # 2026-09-14), so an over-long prefix turns two readable heads into
            # problems. Each hop here re-decodes a few hundred bytes; the
            # chunk table's own sizes guarantee every target is inside the file.
            at0 = at = PAYLOAD_AT + rec.first_size
            prefix2 = None
            try:
                for _hop in range(MAX_CHAIN):
                    prefix2 = ar.magic(entry, at + CHUNK_HEADER)
                    if len(prefix2) < at + CHUNK_HEADER:
                        break
                    cid, size = struct.unpack_from("<II", prefix2, at)
                    if cid in (SKELETON_CHUNK, GEOMETRY_CHUNK):
                        prefix2 = ar.magic(entry, at + CHUNK_HEADER + 0x58)
                        break
                    at += CHUNK_HEADER + size
            except Exception as exc:                        # noqa: BLE001
                rec.problem = f"{type(exc).__name__}: {exc}"
                records.append(rec)
                continue
            at = at0
            for k, v in classify_chain(prefix2, at).items():
                setattr(rec, k, v)
        records.append(rec)
    if progress:
        progress(len(walk), len(walk))
    return Catalog(stamp_of(ar), records, scanned_rows=len(walk))


# ---------------------------------------------------------------------------
# The cache
# ---------------------------------------------------------------------------

class Refused(SystemExit):
    """A cache that must not be used, with the reason."""


def cache_dir():
    return vaultpath.vault_path("cache", "modelcatalog")


def cache_path(ar, stamp=None):
    """Where this archive's catalog lives: keyed by its MFT digest."""
    stamp = stamp or stamp_of(ar)
    return os.path.join(cache_dir(), f"catalog-{stamp['mft_sha256'][:16]}.json")


def save(catalog, path):
    """Write the catalog as JSON. The working tree is refused, the vault is not."""
    try:
        out = vaultpath.resolve_out(path, what="a model catalog cache")
    except ValueError as exc:
        raise Refused(str(exc))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    tmp = out + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(catalog.to_dict(), fh)
    os.replace(tmp, out)
    return out


def load(path, ar=None):
    """Read a catalog back; with `ar`, refuse one built from another archive."""
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise Refused(f"could not read the catalog {path}: "
                      f"{type(exc).__name__}: {exc}")
    if not isinstance(doc, dict) or doc.get("format_version") != FORMAT_VERSION:
        raise Refused(f"{path} is not a format_version {FORMAT_VERSION} "
                      f"catalog; re-scan rather than read across formats")
    try:
        cat = Catalog.from_dict(doc)
    except (KeyError, TypeError, ValueError) as exc:
        raise Refused(f"{path} is malformed: {type(exc).__name__}: {exc}")
    if ar is not None:
        now = stamp_of(ar)
        bad = [k for k in refindex.IDENTITY_FIELDS
               if cat.stamp.get(k) != now[k]]
        if bad:
            rows = "\n".join(f"    {k}: {cat.stamp.get(k)!r} -> {now[k]!r}"
                             for k in bad)
            raise Refused(
                f"REFUSING to browse {now['archive']} with the catalog {path}\n"
                f"  It was scanned from a different archive state:\n{rows}\n"
                f"  Re-scan:  python toolkit/mapdata/modelcatalog.py --scan")
    return cat


def open_catalog(ar, progress=None, rescan=False):
    """The cached catalog for `ar`, or a fresh scan saved under the vault."""
    path = cache_path(ar)
    if not rescan and os.path.isfile(path):
        try:
            return load(path, ar), path, False
        except Refused:
            pass
    cat = scan(ar, progress=progress)
    return cat, save(cat, path), True


# ---------------------------------------------------------------------------
# The build: one model, ready to draw
# ---------------------------------------------------------------------------

class SubMesh:
    """One sub-model, de-indexed: `pos`/`nrm`/`uv` hold 3 corners per tri."""

    __slots__ = ("index", "nv", "ntri", "dat_fvf", "pos", "nrm", "uv",
                 "uv_set", "uv_sets", "material_kind", "material_index",
                 "blend", "layers", "texture_slot", "texture_fid", "alpha",
                 "rigid")

    def __init__(self, index):
        self.index = index
        self.nv = 0
        self.ntri = 0
        self.dat_fvf = 0
        self.pos = array("f")
        self.nrm = None
        self.uv = None
        self.uv_set = None
        self.uv_sets = 0
        self.material_kind = "none"
        self.material_index = None
        self.blend = 0
        self.layers = []
        self.texture_slot = None
        self.texture_fid = None
        self.alpha = None
        self.rigid = True

    def summary(self):
        tex = (f"slot {self.texture_slot} -> 0x{self.texture_fid:X}"
               if self.texture_fid is not None else "flat")
        return (f"sub {self.index}: {self.nv} v, {self.ntri} tri, "
                f"fvf 0x{self.dat_fvf:X}, uv sets {self.uv_sets}, "
                f"{self.material_kind} mtl, {tex}"
                + (f", alpha {self.alpha}" if self.alpha else "")
                + (f", blend {self.blend}" if self.blend else ""))


class SkeletonNode:
    __slots__ = ("index", "base", "link", "keyed")

    def __init__(self, index, base, link, keyed):
        self.index = index
        self.base = base
        self.link = link
        self.keyed = keyed


class ModelView:
    """Everything the viewer draws and displays for one file."""

    def __init__(self, fid, row):
        self.fid = fid
        self.row = row
        self.chunks = []                 # (chunk id, size)
        self.submeshes = []
        self.collision = None            # (pos array of line corners) or None
        self.collision_tris = 0
        self.bounds = None               # (min xyz, max xyz)
        self.texture_ids = []            # FA5 slots, None per null slot
        self.textures = {}               # fid -> Texture
        self.skeleton = None             # list of SkeletonNode, or None
        self.skeleton_from = None        # the file the skeleton came from
        self.composited = None
        self.sequences = []
        self.problems = []

    @property
    def triangles(self):
        return sum(s.ntri for s in self.submeshes)

    @property
    def vertices(self):
        return sum(s.nv for s in self.submeshes)

    def centre(self):
        lo, hi = self.bounds
        return tuple((a + b) / 2.0 for a, b in zip(lo, hi))

    def radius(self):
        lo, hi = self.bounds
        return max(0.5 * max(b - a for a, b in zip(lo, hi)), 1e-3)


class Texture:
    __slots__ = ("fid", "width", "height", "rgba", "alpha", "kind")

    def __init__(self, fid, width, height, rgba, alpha, kind):
        self.fid = fid
        self.width = width
        self.height = height
        self.rgba = rgba
        self.alpha = alpha
        self.kind = kind


def diffuse_layer(mtable, sub):
    """`(kind, slot, uv_set, blend, layers)` for a sub-model.

    THE BLENDER IMPORTER'S RULE (tools/blender/import_gwmap.py,
    `gwmodel_materials`): the diffuse is the first layer whose `texarray` is
    non-negative -- a stored UV set -- falling back to layer 0 only when every
    layer is generated. `slot` is None for a binary material or no table.
    """
    if mtable is None:
        return "none", None, None, 0, []
    kind, layers = mtable.for_submodel(sub)
    if kind != "layered" or not layers:
        return kind, None, None, 0, []
    material = mtable.materials[sub.unk & 0xFFFF]
    stored = [lay for lay in layers if lay.texarray >= 0]
    pick = (stored or layers)[0]
    uv_set = pick.texarray if pick.texarray >= 0 else None
    summary = [{"texpath": lay.texpath, "uv": lay.texarray,
                "flags": lay.flags} for lay in layers]
    return kind, pick.texpath, uv_set, material.blend, summary


def _deindex(values, indices, width):
    out = array("f")
    ext = out.extend
    for i in indices:
        ext(values[i])
    assert len(out) == width * len(indices)
    return out


def build_submeshes(geo, mtable, texture_ids):
    """`ModelGeometry` -> `[SubMesh]`, materials resolved to FA5 file ids."""
    out = []
    for si, sm in enumerate(geo.submodels):
        sub = SubMesh(si)
        sub.nv, sub.ntri, sub.dat_fvf = sm.nv, len(sm.indices) // 3, sm.dat_fvf
        sub.uv_sets = sm.texcoord_sets
        sub.rigid = sm.groups() is None
        idx = sm.indices
        sub.pos = _deindex(sm.positions(), idx, 3)
        normals = sm.normals()
        if normals is not None:
            sub.nrm = _deindex(normals, idx, 3)
        kind, slot, uv_set, blend, layers = diffuse_layer(mtable, sm)
        sub.material_kind = kind
        sub.material_index = sm.unk & 0xFFFF
        sub.blend = blend
        sub.layers = layers
        if uv_set is None and sub.uv_sets:
            uv_set = 0                  # generated-only material: show set 0
        if uv_set is not None and uv_set < sub.uv_sets:
            sub.uv_set = uv_set
            sub.uv = _deindex(sm.texcoords(uv_set), idx, 2)
        if slot is not None and 0 <= slot < len(texture_ids):
            sub.texture_slot = slot
            sub.texture_fid = texture_ids[slot]
        out.append(sub)
    return out


def _bounds(submeshes):
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3
    for s in submeshes:
        p = s.pos
        for k in range(3):
            col = p[k::3]
            if len(col):
                lo[k] = min(lo[k], min(col))
                hi[k] = max(hi[k], max(col))
    if lo[0] == float("inf"):
        return (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)
    return tuple(lo), tuple(hi)


def collision_lines(geo):
    """Every collision-mesh edge as line corners, or None."""
    if not geo.collisions:
        return None, 0
    out = array("f")
    tris = 0
    for cm in geo.collisions:
        pos = cm.positions
        it = cm.indices
        for i in range(0, len(it) - 2, 3):
            a, b, c = pos[it[i]], pos[it[i + 1]], pos[it[i + 2]]
            out.extend(a); out.extend(b)
            out.extend(b); out.extend(c)
            out.extend(c); out.extend(a)
            tris += 1
    return out, tris


class TextureCache:
    """Decoded textures by file id -- ATEX and the one DDS shape, to RGBA."""

    def __init__(self, ar, table, limit=256):
        self.ar = ar
        self.table = table
        self.limit = limit
        self.items = collections.OrderedDict()

    def get(self, fid):
        """A `Texture`, or None with the reason in `.problems` of the caller."""
        if fid in self.items:
            self.items.move_to_end(fid)
            return self.items[fid]
        row = self.table.get(fid)
        if row is None:
            raise KeyError(f"texture 0x{fid:X} is not in the archive's table")
        data = self.ar.read(self.ar.row(row))
        if data[:4] == atex.DDS_MAGIC:
            got = atex.dds_rgba(data)
            if got is None:
                raise ValueError(f"texture 0x{fid:X}: a DDS shape the "
                                 f"decoder refuses")
            rgba, w, h = got
            kind = "dds"
        else:
            rgba, w, h = atex.decode_rgba(data)
            kind = "atex"
        tex = Texture(fid, w, h, bytes(rgba), modelexport._alpha_class(rgba),
                      kind)
        self.items[fid] = tex
        while len(self.items) > self.limit:
            self.items.popitem(last=False)
        return tex


def skeleton_nodes(sk):
    """blk2C rest pose: one node per record -- base, link, whether keyed.

    Reads only the 16-byte record heads and the three channel counts, not
    the key data (`Skeleton.anims()` decodes every key; a shell with 242
    sequences carries megabytes of them and a viewer showing the rest pose
    needs none).
    """
    blk = sk.block_bytes("blk2C")
    n = sk.header["n2C"]
    off = 16 * n
    out = []
    for r in range(n):
        base = struct.unpack_from("<3f", blk, 16 * r)
        flags = struct.unpack_from("<I", blk, 16 * r + 12)[0]
        w0, w2, w4 = struct.unpack_from("<3H", blk, off)
        off += 6 + w0 * 16 + w2 * 20 + w4 * 16
        out.append(SkeletonNode(r, base, flags & 0xFF, bool(w0 or w2 or w4)))
    return out


def build_view(ar, table, fid, textures=None, skeleton_fid=None):
    """One model file -> `ModelView`. `textures` is a `TextureCache` or None
    to skip decoding; `skeleton_fid` names a shell whose FA1 should be drawn
    over this body (a template's composite), else this file's own FA1.
    """
    row = table.get(fid)
    if row is None:
        raise KeyError(f"no file id 0x{fid:X} in {ar.path}")
    data = ar.read(ar.row(row))
    mf = ModelFile.decode(data)
    view = ModelView(fid, row)
    view.chunks = [(cid, len(p)) for cid, p in mf.chunks]
    geo = mf.geometry()
    mtable = None
    if geo is not None:
        try:
            mtable = modelfile.material_table(mf.find(GEOMETRY_CHUNK))
        except modelfile.Undecodable as exc:
            view.problems.append(f"material table: {exc}")
        view.texture_ids = list(mf.texture_refs()) \
            if mf.find(TEXNAME_CHUNK_B) is not None else []
        view.submeshes = build_submeshes(geo, mtable, view.texture_ids)
        view.collision, view.collision_tris = collision_lines(geo)
        view.bounds = _bounds(view.submeshes)
        if textures is not None:
            for sub in view.submeshes:
                if sub.texture_fid is None or sub.texture_fid in view.textures:
                    continue
                try:
                    tex = textures.get(sub.texture_fid)
                except Exception as exc:                    # noqa: BLE001
                    view.problems.append(
                        f"texture 0x{sub.texture_fid:X}: "
                        f"{type(exc).__name__}: {exc}")
                    continue
                view.textures[sub.texture_fid] = tex
            for sub in view.submeshes:
                tex = view.textures.get(sub.texture_fid)
                sub.alpha = tex.alpha if tex is not None else None
    skel_source = data
    view.skeleton_from = fid
    if skeleton_fid is not None and skeleton_fid != fid:
        srow = table.get(skeleton_fid)
        if srow is None:
            view.problems.append(f"skeleton file 0x{skeleton_fid:X} is not "
                                 f"in the archive's table")
            skel_source = None
        else:
            skel_source = ar.read(ar.row(srow))
            view.skeleton_from = skeleton_fid
    if skel_source is not None:
        try:
            sk = skelfile.Skeleton.from_container(skel_source)
        except (skelfile.Undecodable, ValueError) as exc:
            sk = None
            view.problems.append(f"skeleton: {exc}")
        if sk is not None:
            view.composited = sk.composited
            view.sequences = sk.sequences()
            view.skeleton = skeleton_nodes(sk)
            if view.bounds is None:
                pts = [n.base for n in view.skeleton]
                view.bounds = (tuple(min(p[k] for p in pts) for k in range(3)),
                               tuple(max(p[k] for p in pts) for k in range(3)))
    if view.bounds is None:
        view.bounds = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    return view


# ---------------------------------------------------------------------------
# Templates: the content rows and their closure
# ---------------------------------------------------------------------------

def templates(world=None):
    """`content/*.toml` npc rows as `{key, name, file_id, model_id, ...}`."""
    if world is None:
        import content
        world = content.load()
    out = []
    for key, row in sorted(world.rows("npc").items()):
        if row.get("file_id") is None:
            continue
        out.append({"key": key, "name": row.get("name") or key,
                    "file_id": int(row["file_id"]),
                    "model_id": (int(row["model_id"])
                                 if row.get("model_id") is not None else None),
                    "profession": row.get("profession"),
                    "level": row.get("level")})
    return out


def shell_templates(world=None):
    """`{shell file id: [template dicts naming it]}` -- the wire's pairing of
    a skeleton with its bodies, as `content/npcs.toml` carries it. The only
    source that says a `skel` head is a creature shell (module docstring)."""
    out = {}
    for t in templates(world):
        out.setdefault(t["file_id"], []).append(t)
    return out


def resolve_template(ar, table, tmpl):
    """The shell -> body closure of one template, through `unitassembly`.

    Returns `{shell, body, needs_body, closed, problems, draw}` where `draw`
    is the file whose geometry the viewer should build: the body when the
    shell is COMPOSITED and one is declared, else the shell itself, else
    None (a composited shell with no body -- the parade's white box).
    """
    import unitassembly
    unit = unitassembly.UnitDef(tmpl["file_id"],
                                (tmpl["model_id"],) if tmpl.get("model_id")
                                is not None else (),
                                source=f"content:{tmpl['key']}")
    res = unitassembly.Resolver(ar, table).resolve(unit, deep=False)
    needs = res.needs_body
    draw = None
    if needs is False:
        draw = tmpl["file_id"]
    elif needs and tmpl.get("model_id") is not None:
        draw = tmpl["model_id"]
    return {"shell": tmpl["file_id"], "body": tmpl.get("model_id"),
            "needs_body": needs, "closed": res.closed,
            "problems": [list(p) for p in res.problems],
            "roles": res.role_counts(), "draw": draw}


def content_map_models(ar, table, world=None):
    """`{map key: (name, [model file ids])}` for every content map that
    decodes; a map that does not is recorded under `problems`."""
    if world is None:
        import content
        world = content.load()
    out, problems = {}, []
    for key, row in world.rows("map").items():
        fid = row.get("file_id")
        if fid is None:
            continue
        try:
            ids = modelexport.map_model_ids(int(fid), ar, table)
        except Exception as exc:                            # noqa: BLE001
            problems.append((key, f"{type(exc).__name__}: {exc}"))
            continue
        out[key] = (row.get("name") or key, ids)
    return out, problems


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _describe(view):
    lines = [f"file 0x{view.fid:X} ({view.fid}) row {view.row}",
             "  chunks   " + ", ".join(f"0x{c:X}:{n}" for c, n in view.chunks)]
    if view.submeshes:
        lines.append(f"  geometry {len(view.submeshes)} sub-model(s), "
                     f"{view.vertices} vertices, {view.triangles} triangles"
                     f", {view.collision_tris} collision tri(s)")
        lo, hi = view.bounds
        lines.append("  bounds   " + " ".join(f"{a:.1f}..{b:.1f}"
                                              for a, b in zip(lo, hi)))
        for s in view.submeshes:
            lines.append("  " + s.summary())
        lines.append("  FA5      " + ", ".join(
            "null" if t is None else f"0x{t:X}" for t in view.texture_ids))
    if view.skeleton is not None:
        lines.append(f"  skeleton {len(view.skeleton)} node(s), "
                     f"{len(view.sequences)} sequence(s), composited="
                     f"{view.composited}, from 0x{view.skeleton_from:X}")
    for p in view.problems:
        lines.append(f"  PROBLEM  {p}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--scan", action="store_true",
                    help="scan every head and (re)write the vault cache")
    ap.add_argument("--file-id", default=None,
                    help="describe one model's build, e.g. 116703 or 0x1C7DF")
    ap.add_argument("--templates", action="store_true",
                    help="list content npc templates with their closure")
    args = ap.parse_args(argv)

    with Archive(args.dat) as ar:
        if args.scan:
            t0 = time.time()
            cat, path, fresh = open_catalog(
                ar, rescan=True,
                progress=lambda n, t: print(f"  {n}/{t} heads"))
            print(f"scanned {cat.scanned_rows} heads in {time.time() - t0:.1f} s"
                  f" -> {path}")
            print(f"  {cat.census()}")
            probs = [r for r in cat.records if r.problem]
            print(f"  {len(probs)} head(s) with a recorded problem")
            for r in probs[:5]:
                print(f"    row {r.row} {r.fids}: {r.problem}")
        if args.file_id is not None:
            table = file_id_table(ar)
            fid = int(args.file_id, 0)
            t0 = time.time()
            view = build_view(ar, table, fid, textures=TextureCache(ar, table))
            print(_describe(view))
            print(f"  built in {time.time() - t0:.2f} s; textures decoded: "
                  + ", ".join(f"0x{t.fid:X} {t.width}x{t.height} {t.alpha}"
                              for t in view.textures.values()))
        if args.templates:
            table = file_id_table(ar)
            for t in templates():
                r = resolve_template(ar, table, t)
                print(f"  {t['key']:28} shell {t['file_id']:>7} body "
                      f"{str(t['model_id']):>7}  needs_body={r['needs_body']} "
                      f"closed={r['closed']} draw={r['draw']}  {t['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
