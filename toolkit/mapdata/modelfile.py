r"""The prop model file: read `ffna` type 2 geometry. READ ONLY, on purpose.

Rung M1 of `studies/models/PLAN.md`: the layout `studies/customarea/FINDINGS.md`
§5 measured from scratch scripts, promoted to committed code. Nothing here
writes a file, opens an archive `r+b`, or emits a byte of ArenaNet data — this
module decodes in memory and returns typed values. The interchange half is
rung M3.

    mf  = ModelFile.load(0x2E52A, archive)      # a model file id from a map's
    geo = mf.geometry()                         #   0x21000004 dependency list
    geo.max_2d_radius()                         # the number the f11 identity is
                                                #   built on

WHAT A MODEL FILE IS. `ffna` type 2, reached from a map's props chunk by index:
Stripped prop `model` -> chunk 0x11000004 / Bloated 0x21000004 -> the pair
formula (`mapchunks.dependency_file_id`) -> the archive's file-id table. Chunk
map (MEASURED over 2,048 files, 14-map sample): 0xFA0 geometry, 0xFA1/0xFA5
texture filenames, 0xFA6, 0xFAD AMAT materials. This module decodes the
GEOMETRY chunk; the texture chunks are carried as opaque payloads a later rung
resolves (`atex.py` already decodes what they point at).

THE GEOMETRY CHUNK. A 0x54-byte preamble region, then `num_models` sub-model
records, then `collision_count` collision meshes, closing on the chunk's exact
final byte:

    +0x44 u32 num_models
    +0x4C u16 collision_count
    +0x54 .. start-of-array: NOT DECODED (see below)

    sub-model record:
      u32 unk
      u32 n0, n1, n2       index counts; the wire count is
                           ti = n0 + (n0!=n1)*n1 + (n1!=n2)*n2
      u32 nv               vertex count
      u32 dat_fvf          vertex format word
      u32 u0, u1, u2       trailing-block counts; (u0 + u1 + 3*u2) * 4 bytes
                           follow the vertices, content OPAQUE
      ti * u16             triangle-list indices (ti % 3 == 0 on 3,834 of
                           3,834 sub-models; every index < nv on all of them)
      nv * stride          interleaved vertices; +0 is f32 x, y, z
      (u0 + u1 + 3*u2) * 4 the trailing blocks, carried opaquely

    collision mesh:
      u32 ni, u32 nv       then ni * u16 indices and nv * 12 bytes of f32
                           x, y, z — position-only geometry

THE START OFFSET IS SEARCHED, NOT DECODED, and that is the honest state of the
preamble: the bytes between +0x54 and the sub-model array have no decoder, so
`decode` scans every offset from 0x54 and keeps those from which the whole
two-stage walk closes on the chunk's exact final byte. Three populations, kept
apart because §A5's lesson is that conflating them manufactured a false theory:

  * UNIQUE closure — 1,741 of 2,048 files on the 14-map sample (85.0%).
  * NO closure — 306 (14.9%): `NoClose` is raised, never guessed past.
  * AMBIGUOUS — 1 (file id 0x1BAE2, closing at 97 and 101 with all indices in
    range under BOTH parses, so nothing downstream can break the tie either).
    `decode` keeps the LOWEST offset — the same choice the f11 survey made —
    and records every closing offset in `starts`, because closure is NOT
    identity (§B5) and a caller for whom the difference matters must check
    `ambiguous`. The single corpus occurrence of dat_fvf 0x2C is this file's
    chosen parse; its rival parse is format 21, so THE RARE FORMAT'S VERY
    EXISTENCE rests on an ambiguous tie and is UNCONFIRMED.

THE VERTEX STRIDE IS THE CLIENT'S OWN, read out of its `.data` (rung M2,
2026-08-13). Three tables at VA `0x00BF5B80` (16 u32), `0x00BF5BC0` (8) and
`0x00BF5BE0` (16), summed by the accessor at `0x00688010`, which shifts its
`fvf` argument by 12, 8, 4 and 0 and indexes them — SOURCE-CODE, build 38797.
The caller's `dat_fvf` reaches it through the remap
`((d & 0xFF0) << 4) | ((d >> 8) & 0x30) | (d & 0xF)`.

    stride = FVF0[(f>>12)&0xF] + FVF0[(f>>8)&0xF] + FVF1[(f>>4)&7] + FVF2[f&0xF]

**This REPLACED a byte-cost rule of our own** (M1: +12/+4/+12 for bits 0-2,
+8 per bit of 0xF0, +24 for any of 0x3000). The two agree on twelve of the
thirteen (dat_fvf, stride) pairs the corpus appeared to hold and differ on
**60,168 of 65,536 possible words** — they agreed exactly where the corpus
lives and nowhere else, which is what made the wrong rule survive M1.

**dat_fvf 0x2C NEVER EXISTED.** Its single corpus sighting was our rule's
stride-20 misparse of file 0x1BAE2, the ambiguous file: under the client's
table only offset 101 closes, the format there is the common 21, and the
corpus holds TWELVE formats, not thirteen. The cross-file oracle confirms the
correction from a source that shares nothing with the client binary — that
model's props scored **f11 0 of 16 under the old rule and 16 of 16 under the
client's**, which is the entire corpus-wide improvement from 12,766 to
**12,782 of 12,875**. GuildWarsMapBrowser's FVF tables are these same client
tables and were right where we were wrong; §B6's recorded disagreement is
resolved in upstream's favour.

THE LOAD-BEARING ORACLE, and why this module can be trusted at all: the
Bloated prop record's `f11` field equals `scale * max(sqrt(x^2 + y^2))` over
the referenced model's vertices — a number that crosses TWO FILES and eight
decode steps (prop record -> filename index -> dependency pair -> file id ->
MFT row -> geometry chunk -> sub-model walk -> vertex stride), so no decoder
error at any step survives it. MEASURED at 1e-5 on 12,766 of 12,875 props
over the 14-map sample; 474/474 and 664/664 on the reference maps' comparable
props; the 3D-radius rival scores 103 of 12,875. `test_modelfile.py` pins all
of it.

THE VERTEX FIELD MAP (rung M2). The three tables are PERFECTLY ADDITIVE over
their bits — each table entry is the sum of its set bits' costs, checked for
all 40 entries — so the client's own data states the size of every field, and
`dat_fvf` bit b maps to one of them:

    bit 0        12  position f32 x, y, z        (offset 0; pinned by f11)
    bit 1         4  a small INDEX, purpose UNVERIFIED (see below)
    bit 2        12  NORMAL, unit f32 x, y, z
    bit 3         4  UNVERIFIED (absent from every corpus format)
    bits 12, 13  12  TANGENT FRAME, unit f32 x, y, z each
    bits 4..11    8  texture coordinates, f32 u, v (up to eight sets)
    bits 14, 15   —  DROPPED by the remap; they cost nothing

Field ORDER within a vertex is the client's table order — the FVF2 group
(bits 0-3), then FVF1 (bits 12-13), then the two FVF0 groups (bits 4-11) —
and it is CORROBORATED rather than assumed, because a permutation gives the
same stride: the unit-length tests below hold at the offsets this order
computes and collapse four bytes away.

Each name is a REFUTABLE PREDICTION the corpus was asked, never an inference
from a field's size (the `envchunk.py` tag-6 lesson, where a name read off a
size was wrong). MEASURED over 90,108 vertices of a 7-map sample:

  * **bit 2 is the normal**: unit length within 1e-3 on **90,108 of 90,108**;
    the same read four bytes early is unit on 2.7%.
  * **bits 12/13 are a tangent frame**: unit on **10,017 of 10,017** each
    (controls 6.5% and 3.6%), and bit 12 is orthogonal to bit 2 on **93.0%**
    against a 26.0% control that pairs a normal with the NEXT vertex's
    vector. 93% rather than 100% is what a tangent frame does at UV seams and
    mirrored shells; the figure is reported rather than rounded up, and which
    of the two is tangent vs binormal is NOT established.
  * **bits 4-11 are texture coordinates**: two f32, 97.8% inside +/-16 with a
    full range of -519.7 .. 520.4 — wrapped/atlased UVs, not normalised ones.
  * **bit 1 is NOT a colour.** The D3DCOLOR reading is REFUTED: its high three
    bytes are zero on 9,128 of 9,128 and the low byte takes ten values, all
    <= 9. It is a small integer index and its PURPOSE IS UNVERIFIED — naming
    it (matrix index? material slot?) would be the size-inference mistake
    again.

WHAT IS OPAQUE, so nobody reads more than was measured: the preamble, the
sub-model `unk` word, the trailing blocks, the meaning of the texture-name
chunks' contents, and bits 1 and 3 of the format word. `SubModel.vertex_data`
and `.trailing` carry the bytes; `field_offsets` says where the named fields
sit and nothing interprets the rest.

Corrections this module carries from the study (§A/§B): the format census was
fitted and tested on the same sub-models (§B6), so the stride rule is labelled
RECONSTRUCTION above rather than MEASURED; and ~0.5% of props whose model DID
close carry an `f11` that disagrees grossly — a population DISJOINT from the
no-close files, unexplained, and excluded from nothing (the oracle counts are
reported over every comparable prop).
"""

import argparse
import math
import struct
import sys
import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, ffna_type, file_id_table, \
    DEFAULT_DAT  # noqa: E402
import mapchunks  # noqa: E402

#: The chunk ids a model file carries (MEASURED census, 14-map sample).
GEOMETRY_CHUNK = 0x00000FA0
TEXNAME_CHUNK_A = 0x00000FA1
TEXNAME_CHUNK_B = 0x00000FA5
UNKNOWN_CHUNK_FA6 = 0x00000FA6
AMAT_CHUNK = 0x00000FAD

MODEL_FFNA_TYPE = 2

#: Geometry-chunk header offsets. Everything else before the sub-model array
#: is the UNDECODED preamble.
NUM_MODELS_AT = 0x44
COLLISION_COUNT_AT = 0x4C
PREAMBLE_MIN = 0x54

SUBMODEL_HEADER = struct.Struct("<9I")
COLLISION_HEADER = struct.Struct("<2I")
POSITION = struct.Struct("<3f")

#: The walk's validity gates, exactly the survey's — the closure censuses in
#: the test are measured UNDER these bounds, so changing one moves them.
MAX_VERTICES = 200000
MAX_FVF = 0xFFFFF
MIN_STRIDE = 8
MAX_STRIDE = 0x80
MAX_COLLISION_COUNT_FIELD = 500000


class Undecodable(ValueError):
    """These bytes are not a model geometry this module understands."""


class NoClose(Undecodable):
    """No start offset lets the two-stage walk close on the chunk's end.

    ~15% of retail model files are in this state (306 of 2,048 on the 14-map
    sample) because the preamble is undecoded and the array is found by
    search. Raised, never guessed past.
    """


#: THE CLIENT'S OWN STRIDE TABLES, read from build 38797's `.data` at the VAs
#: below and summed by the accessor at `FVF_ACCESSOR_VA`. MEASURED, not ours:
#: `test_modelfile.py` re-reads them out of the vaulted image and requires
#: these literals to match, so a build change is a red test rather than a
#: silent drift. They are strides -- explicitly on the provenance gate's
#: permitted side (PLAN §7 Q3) -- and the extractor is this repo's
#: `clientscan/codescan.py` plus the test's own PE walk.
FVF0_VA = 0x00BF5BE0
FVF1_VA = 0x00BF5BC0
FVF2_VA = 0x00BF5B80
FVF_ACCESSOR_VA = 0x00688010
FVF_BUILD = 38797

FVF0 = (0, 8, 8, 16, 8, 16, 16, 24, 8, 16, 16, 24, 16, 24, 24, 32)
FVF1 = (0, 12, 12, 24, 12, 24, 24, 36)
FVF2 = (0, 12, 4, 16, 12, 24, 16, 28, 4, 16, 8, 20, 16, 28, 20, 32)

#: Per-bit field sizes, DERIVED from the tables above by additivity (each of
#: the 40 entries equals the sum of its set bits' costs -- checked, not
#: assumed). The key is a `dat_fvf` bit; bits 14 and 15 are dropped by the
#: remap and cost nothing.
FIELD_SIZE = {0: 12, 1: 4, 2: 12, 3: 4,
              4: 8, 5: 8, 6: 8, 7: 8, 8: 8, 9: 8, 10: 8, 11: 8,
              12: 12, 13: 12}

#: The order fields sit in a vertex: the client's table order. CORROBORATED
#: by the unit-length tests at these offsets, not merely by the total (a
#: permutation would give the same stride).
FIELD_ORDER = (0, 1, 2, 3, 12, 13, 4, 5, 6, 7, 8, 9, 10, 11)

#: Names for the bits a refutable corpus prediction established. Bits 1 and 3
#: are deliberately absent -- see the docstring; bit 1's colour reading is
#: REFUTED and its purpose is unverified.
FIELD_POSITION = 0
FIELD_NORMAL = 2
FIELD_TANGENT_BITS = (12, 13)
FIELD_TEXCOORD_BITS = (4, 5, 6, 7, 8, 9, 10, 11)


def remap_fvf(dat_fvf):
    """The file's format word to the accessor's argument. SOURCE-CODE: the
    caller's shifts feeding `FVF_ACCESSOR_VA`."""
    return ((dat_fvf & 0xFF0) << 4) | ((dat_fvf >> 8) & 0x30) | (dat_fvf & 0xF)


def vertex_stride(dat_fvf):
    """Bytes per vertex. THE CLIENT'S OWN TABLES (`FVF_ACCESSOR_VA`), not a
    rule of ours -- see the module docstring for the byte-cost rule this
    replaced and the phantom format it invented."""
    f = remap_fvf(dat_fvf)
    return (FVF0[(f >> 12) & 0xF] + FVF0[(f >> 8) & 0xF]
            + FVF1[(f >> 4) & 7] + FVF2[f & 0xF])


def field_offsets(dat_fvf):
    """`{dat_fvf bit: byte offset}` for the fields a vertex carries.

    Sums to `vertex_stride(dat_fvf)` by construction; which OFFSET each field
    lands on is the corroborated claim (see the docstring's unit-length
    measurements), not the total.
    """
    off = 0
    out = {}
    for bit in FIELD_ORDER:
        if dat_fvf >> bit & 1:
            out[bit] = off
            off += FIELD_SIZE[bit]
    return out


class SubModel:
    """One render sub-model: a triangle list over interleaved vertices.

    `indices` are the ti wire indices; `vertex_data` is the raw interleaved
    block (`nv * stride` bytes) of which only the leading position floats are
    interpreted; `trailing` is the opaque post-vertex block.
    """

    __slots__ = ("unk", "counts", "nv", "dat_fvf", "stride", "u_counts",
                 "indices", "vertex_data", "trailing")

    def __init__(self, unk, counts, nv, dat_fvf, stride, u_counts, indices,
                 vertex_data, trailing):
        self.unk = unk
        self.counts = counts                    # (n0, n1, n2)
        self.nv = nv
        self.dat_fvf = dat_fvf
        self.stride = stride
        self.u_counts = u_counts                # (u0, u1, u2)
        self.indices = indices
        self.vertex_data = vertex_data
        self.trailing = trailing

    @property
    def ti(self):
        n0, n1, n2 = self.counts
        return n0 + (n0 != n1) * n1 + (n1 != n2) * n2

    @property
    def triangles(self):
        """Index triples. `ti % 3 == 0` on every measured sub-model."""
        it = self.indices
        return [(it[i], it[i + 1], it[i + 2]) for i in range(0, len(it), 3)]

    @property
    def fields(self):
        """`{dat_fvf bit: offset}` — where each named field sits."""
        return field_offsets(self.dat_fvf)

    def positions(self):
        """The f32 (x, y, z) at the head of each vertex."""
        out = []
        for i in range(self.nv):
            out.append(POSITION.unpack_from(self.vertex_data, i * self.stride))
        return out

    def normals(self):
        """Unit f32 (x, y, z) per vertex, or None when the format has none.

        MEASURED unit on 90,108 of 90,108 sampled vertices, with the same
        read four bytes early unit on 2.7% — that control is what makes this
        the normal rather than three floats at a plausible offset.
        """
        return self._vec3(FIELD_NORMAL)

    def tangent_frame(self):
        """The unit vectors at bits 12/13 as a `(first, second)` tuple, each
        a per-vertex list or None. WHICH IS TANGENT AND WHICH IS BINORMAL IS
        NOT ESTABLISHED — bit 12 is orthogonal to the normal on 93.0% against
        a 26.0% control, so they are a tangent frame; the naming is not ours
        to assert."""
        return tuple(self._vec3(b) for b in FIELD_TANGENT_BITS)

    def texcoords(self, which=0):
        """Texture-coordinate set `which` (0..7) as (u, v) pairs, or None.

        Retail UVs are NOT normalised: 97.8% inside +/-16 over a full range
        of -519.7 .. 520.4, so a consumer must wrap rather than clamp.
        """
        bit = FIELD_TEXCOORD_BITS[which]
        off = self.fields.get(bit)
        if off is None:
            return None
        return [struct.unpack_from("<2f", self.vertex_data,
                                   i * self.stride + off)
                for i in range(self.nv)]

    @property
    def texcoord_sets(self):
        return sum(1 for b in FIELD_TEXCOORD_BITS if self.dat_fvf >> b & 1)

    def _vec3(self, bit):
        off = self.fields.get(bit)
        if off is None:
            return None
        return [POSITION.unpack_from(self.vertex_data, i * self.stride + off)
                for i in range(self.nv)]

    def __repr__(self):
        has = []
        if self.fields.get(FIELD_NORMAL) is not None:
            has.append("N")
        if any(b in self.fields for b in FIELD_TANGENT_BITS):
            has.append("T")
        if self.texcoord_sets:
            has.append(f"UV x{self.texcoord_sets}")
        return (f"<SubModel {self.nv} verts stride {self.stride} "
                f"(fvf 0x{self.dat_fvf:X}: pos"
                + (", " + ", ".join(has) if has else "")
                + f"), {self.ti} indices>")


class CollisionMesh:
    """Position-only geometry after the render models."""

    __slots__ = ("indices", "positions")

    def __init__(self, indices, positions):
        self.indices = indices
        self.positions = positions

    def __repr__(self):
        return (f"<CollisionMesh {len(self.positions)} verts, "
                f"{len(self.indices)} indices>")


class ModelGeometry:
    """A decoded 0xFA0 payload. `starts` holds EVERY closing offset;
    `submodels` and `collisions` are the parse at `start = starts[0]`."""

    __slots__ = ("num_models", "collision_count", "start", "starts",
                 "submodels", "collisions")

    def __init__(self, num_models, collision_count, start, starts, submodels,
                 collisions):
        self.num_models = num_models
        self.collision_count = collision_count
        self.start = start
        self.starts = tuple(starts)
        self.submodels = list(submodels)
        self.collisions = list(collisions)

    @property
    def ambiguous(self):
        """More than one closing start. Real (file 0x1BAE2) — closure is not
        identity, and a caller for whom it matters must look."""
        return len(self.starts) > 1

    @classmethod
    def decode(cls, payload):
        payload = bytes(payload)
        if len(payload) < PREAMBLE_MIN:
            raise Undecodable(
                f"geometry chunk is {len(payload)} bytes, under the "
                f"{PREAMBLE_MIN}-byte header region")
        num_models, = struct.unpack_from("<I", payload, NUM_MODELS_AT)
        coll, = struct.unpack_from("<H", payload, COLLISION_COUNT_AT)

        # THE SUB-MODEL ARRAY IS COMPUTED, NOT SEARCHED (rung M6). The
        # preamble is six gated variable-length blocks and `preamble_end`
        # walks them exactly as `MdlLoad.cpp`'s parser does; see its
        # docstring for the block table and the addresses.
        start = preamble_end(payload)
        starts = [start]
        walked = _walk_models(payload, start, num_models)
        if walked is None:
            raise NoClose(
                f"the computed sub-model start {start} does not admit "
                f"{num_models} sub-model(s) in {len(payload)} bytes")
        end, raw = walked
        craw = []
        if coll:
            cw = _walk_collision(payload, end, coll)
            if cw is None:
                raise NoClose(
                    f"the computed start {start} admits {num_models} "
                    f"sub-model(s) but not {coll} collision mesh(es)")
            end, craw = cw

        # THE CLOSURE GATE IS ARENANET'S OWN, not ours: `0x007957CB` does
        # `cmp [ebp+8], esi / jne -> return 4`. Keeping it means N green
        # decodes are N assertions about the whole preamble derivation rather
        # than N comparisons of a value with itself -- and because the offset
        # is now COMPUTED, closure can genuinely fail, where a search made it
        # true by selection.
        end = trailing_end(payload, end)
        if end != len(payload):
            raise NoClose(
                f"the walk ends at {end} of {len(payload)} bytes; the "
                f"client's own gate at 0x007957CB requires the exact end")
        submodels = [_submodel(payload, rec) for rec in raw]
        for i, sm in enumerate(submodels):
            bad = sum(1 for v in sm.indices if v >= sm.nv)
            if bad:
                # 0 of 3,834 measured sub-models; a parse that closed with an
                # index past its vertex array is broken, not novel.
                raise Undecodable(
                    f"sub-model {i}: {bad} of {len(sm.indices)} indices are "
                    f">= its vertex count {sm.nv}; every measured retail "
                    f"sub-model has all indices in range")
        collisions = [_collision(payload, rec) for rec in craw]
        return cls(num_models, coll, starts[0], starts, submodels, collisions)

    def max_2d_radius(self):
        """max sqrt(x^2 + y^2) over every render vertex — the model half of
        the f11 identity. Model-space and rotation-independent (MEASURED on
        238/238 non-yaw props)."""
        best = 0.0
        for sm in self.submodels:
            for x, y, _z in sm.positions():
                h = x * x + y * y
                if h > best:
                    best = h
        return math.sqrt(best)

    def max_3d_radius(self):
        """The 3D rival, kept as the control: 103 of 12,875 at 1e-5."""
        best = 0.0
        for sm in self.submodels:
            for x, y, z in sm.positions():
                h = x * x + y * y + z * z
                if h > best:
                    best = h
        return math.sqrt(best)

    def __repr__(self):
        amb = f", AMBIGUOUS x{len(self.starts)}" if self.ambiguous else ""
        return (f"<ModelGeometry {self.num_models} sub-model(s), "
                f"{self.collision_count} collision mesh(es), "
                f"start {self.start}{amb}>")


#: The chunk's own version word, gated by `MdlLoad.cpp` at 0x00794586
#: (`cmp dword ptr [eax], 0x26` / `jne` -> error 6). MEASURED 0x26 on
#: 2,951 of 2,951 sampled model files.
GEOMETRY_VERSION = 0x26


class _Cursor:
    """A bounds-checked cursor, mirroring the client's own refusals."""

    __slots__ = ("p", "n", "at")

    def __init__(self, payload):
        self.p = payload
        self.n = len(payload)
        self.at = 0

    def take(self, k, why):
        if k < 0 or self.at + k > self.n:
            raise NoClose(f"{why}: {k} bytes from {self.at} runs past the "
                          f"chunk's {self.n}")
        self.at += k

    def cstring(self, why):
        z = self.p.find(b"\0", self.at, self.n)
        if z < 0:
            raise NoClose(f"{why}: unterminated string at {self.at}")
        self.at = z + 1


def _u8(p, o):
    return p[o]


def _u16(p, o):
    return struct.unpack_from("<H", p, o)[0]


def _u32(p, o):
    return struct.unpack_from("<I", p, o)[0]


def material_block_start(payload):
    """Where block C -- the MATERIAL TABLE -- begins: past blocks A and B.

    Split out of `preamble_end` rather than re-derived, so the material
    reader and the sub-model walk can never drift apart on the same file.
    """
    n = len(payload)
    if n < PREAMBLE_MIN:
        raise Undecodable(f"geometry chunk is {n} bytes, under the "
                          f"{PREAMBLE_MIN}-byte header region")
    version = _u32(payload, 0)
    if version != GEOMETRY_VERSION:
        raise Undecodable(
            f"geometry chunk version 0x{version:X} != 0x{GEOMETRY_VERSION:X}; "
            f"MdlLoad.cpp refuses it at 0x00794586")
    w = _Cursor(payload)
    w.at = PREAMBLE_MIN
    if _u8(payload, 0x30):                                          # A
        w.take(28 * _u8(payload, 0x30), "block A")
    for _ in range(_u16(payload, 0x50)):                            # B
        rec = w.at
        w.take(0x18, "block B header")
        w.take(7 * _u32(payload, rec + 8)
               + 8 * (_u32(payload, rec + 0x0C) + _u32(payload, rec + 0x10)
                      + _u32(payload, rec + 0x14)), "block B payload")
    return w.at


class Material:
    """One LAYERED material: a run of layers in the model's layer arrays."""

    __slots__ = ("flags", "blend", "opaque", "pixel_shader_id",
                 "layer_count", "layer_base")

    def __init__(self, flags, blend, opaque, pixel_shader_id, layer_count,
                 layer_base):
        self.flags = flags
        self.blend = blend
        self.opaque = opaque
        self.pixel_shader_id = pixel_shader_id
        self.layer_count = layer_count
        self.layer_base = layer_base

    def __repr__(self):
        return (f"Material({self.layer_count} layer(s) from "
                f"{self.layer_base}, shader={self.pixel_shader_id})")


class Layer:
    """One texture layer of a material.

    `texpath` is ArenaNet's own `texPathIndex` -- an index into the model's
    `0x00000FA5` texture list, bounded against `texPathCount` by
    `MdlCombine:568`. `texarray` is the UV SET it samples; a NEGATIVE value
    means the coordinates are generated rather than stored.
    """

    __slots__ = ("flags", "texarray", "opaque", "conv", "texpath",
                 "tex_flag", "slot")

    def __init__(self, flags, texarray, opaque, conv, texpath, tex_flag,
                 slot):
        self.flags = flags
        self.texarray = texarray
        self.opaque = opaque
        self.conv = conv
        self.texpath = texpath
        self.tex_flag = tex_flag
        self.slot = slot

    def __repr__(self):
        return (f"Layer(tex={self.texpath}, uv={self.texarray}, "
                f"flags={self.flags:#06x})")


class MaterialTable:
    """A model's layered materials and their layers, from block C.

    **THIS IS WHAT BINDS A SUB-MODEL TO ITS TEXTURES**, and it is the thing
    rungs M4 and M5 were missing. `SubModel.unk` is ArenaNet's `mtlIndex`
    (its low 16 bits; the high half is zero on every sub-model measured), and
    it selects a material here -- NOT a texture directly, which is why using
    it as an `0x00000FA5` index put specular maps on Kamadan's buildings.

    The chain is `sub-model -> material -> layers -> texPathIndex -> FA5`.
    ArenaNet's own asserts name every step: `MdlTex:2823`
    `geosets.Count() == materials.Count()` (one material per sub-model),
    `MdlCombine:565` `mtlData->shaderCount < arrsize(combo->texPathIndex)`
    and `MdlCombine:568` `texPathIndex < texPathCount`.

    THE ORACLE, and it is one this decoder cannot force: a material's layers
    name the UV SETS they sample, and the highest one must match the number
    of sets the SUB-MODEL's vertex format actually carries --

        max(layer.texarray >= 0) + 1 == submodel.texcoord_sets

    which crosses from the material table to the vertex declaration, two
    structures written by different parts of the exporter. MEASURED
    **1,063 of 1,063** over both reference maps, against **926 of 1,022** for
    a rival that binds by sub-model POSITION instead of by `mtlIndex`, and
    **621 of 1,064** for a random material. A material whose every layer has
    a negative `texarray` samples no stored set at all, so the identity is
    undefined there and those are excluded rather than counted as failures.
    """

    __slots__ = ("materials", "layers")

    def __init__(self, materials, layers):
        self.materials = materials
        self.layers = layers

    def __len__(self):
        return len(self.materials)

    def layers_of(self, index):
        """The layers of material `index`, in order. Layer 0 is the base."""
        m = self.materials[index]
        return self.layers[m.layer_base:m.layer_base + m.layer_count]

    def for_submodel(self, sub):
        """`(kind, layers)` for a sub-model. `kind` is 'layered' or 'binary'.

        A `mtlIndex` past the layered array names a BINARY material, which
        lives in the AMAT files of the model's `0x00000FAD` list -- a
        different mechanism this returns None for rather than guessing at.
        """
        index = sub.unk & 0xFFFF
        if index >= len(self.materials):
            return "binary", None
        return "layered", self.layers_of(index)

    def __repr__(self):
        return (f"MaterialTable({len(self.materials)} material(s), "
                f"{len(self.layers)} layer(s))")


def _i8(payload, off):
    value = payload[off]
    return value - 256 if value > 127 else value


def material_table(payload):
    """A geometry chunk's `MaterialTable`, or None when it has no layered one.

    None is a real answer, not an absence: 12 of the two reference maps' 315
    models carry no layered material and use the AMAT (`0x00000FAD`) path
    instead.
    """
    count = _u8(payload, 0x18)
    layer_total = _u8(payload, 0x1C)
    has_slots = _u32(payload, 0x20) != 0
    if count == 0:
        return None
    at = material_block_start(payload)
    layers_at = at + 8 * count

    materials = []
    base = 0
    for i in range(count):
        rec = payload[at + 8 * i:at + 8 * i + 8]
        if len(rec) != 8:
            raise Undecodable(f"material {i} of {count} runs past the chunk")
        materials.append(Material(rec[0], rec[1],
                                  struct.unpack_from("<I", rec, 2)[0],
                                  rec[6], rec[7], base))
        base += rec[7]
    # THE CLIENT'S OWN GATE, at 0x007959B3: the per-material layer counts
    # must sum to the total the header declares. Refused, never repaired --
    # a mismatch means the arrays below would be misaligned and every
    # texture index after it silently wrong.
    if base != layer_total:
        raise Undecodable(
            f"the material layer counts sum to {base} but the header "
            f"declares {layer_total}")

    need = layers_at + (9 if has_slots else 8) * layer_total
    if need > len(payload):
        raise Undecodable(f"the layer arrays need {need} bytes of "
                          f"{len(payload)}")
    layers = []
    for j in range(layer_total):
        tex_byte = _u8(payload, layers_at + 8 * layer_total + j)
        layers.append(Layer(
            _u16(payload, layers_at + 2 * j),
            _i8(payload, layers_at + 2 * layer_total + j),
            _u32(payload, layers_at + 3 * layer_total + 4 * j),
            _u8(payload, layers_at + 7 * layer_total + j),
            tex_byte & 0x7F,
            tex_byte >> 7,
            _u8(payload, layers_at + 9 * layer_total + j) if has_slots
            else None))
    return MaterialTable(materials, layers)


def preamble_end(payload):
    """Where the sub-model array starts. COMPUTED, exactly as the client does.

    Rung M6, and it replaced a brute-force search that could not close on
    ~15% of model files. `MdlLoad.cpp`'s parser at `0x007952A0` sets a cursor
    to `begin + 0x54` (`0x007952C1 lea eax, [esi+0x54]`) and advances it
    through SIX gated variable-length blocks; the sub-model array is simply
    wherever the cursor lands. Every size comes from a header field, so the
    offset is derived rather than fitted:

        A  0x007952D7  if u8@0x30:  28 * u8@0x30
        B  0x00795307  u16@0x50 records of 0x18, each + 7*u32@rec+8
                       + 8*(u32@rec+0xC + u32@rec+0x10 + u32@rec+0x14)
        --  gates at 0x0079545B: u8@0x18 <= 0xFE, u8@0x1C <= 0x7F, u32@0x20 <= 7
        C  0x00795860  if a=u8@0x18: 8*a + 9*b + (b if c else 0)
        D  0x00794D30  if u8@0x19: 9*u8@0x19, then u8@0x1D*(3 + (c!=0)),
                       then 8*u16@0x1A, then u16@0x1A NUL-TERMINATED STRINGS,
                       then 8*u16@0x1E
        E  0x00795507  if u8@0x08 & 0x20: an 8-byte header, then its u32@+4
                       records of 0x2E bytes, each + `_block_e_payload`
        F  0x0079554E  if u8@0x08 & 0x80: u16@0x52 records of 48, then
                       24*sum(u32@rec+0x28) + 16*sum(u32@rec+0x2C)

    Nine one-term sabotages of this walk were built and run and every one
    REDUCES closure over the reference maps' 315 chunks (from 315/315 to
    1, 0, 275, 61, 314, 298, 311, 0 and 251) -- so the terms are load-bearing
    rather than decorative, and `test_modelfile.py` keeps the sharpest of them.
    """
    n = len(payload)
    if n < PREAMBLE_MIN:
        raise Undecodable(f"geometry chunk is {n} bytes, under the "
                          f"{PREAMBLE_MIN}-byte header region")
    version = _u32(payload, 0)
    if version != GEOMETRY_VERSION:
        raise Undecodable(
            f"geometry chunk version 0x{version:X} != 0x{GEOMETRY_VERSION:X}; "
            f"MdlLoad.cpp refuses it at 0x00794586")
    w = _Cursor(payload)
    w.at = material_block_start(payload)

    a, b, c = _u8(payload, 0x18), _u8(payload, 0x1C), _u32(payload, 0x20)
    if a > 0xFE:
        raise Undecodable(f"u8@0x18 = {a} > 0xFE (0x0079545B refuses)")
    if b > 0x7F:
        raise Undecodable(f"u8@0x1C = {b} > 0x7F (0x0079545B refuses)")
    if c > 7:
        raise Undecodable(f"u32@0x20 = {c} > 7 (0x0079545B refuses)")

    if a:                                                           # C
        w.take(8 * a + 9 * b + (b if c else 0), "block C")

    d0 = _u8(payload, 0x19)                                         # D
    if d0:
        w.take(9 * d0, "block D0")
        w.take(_u8(payload, 0x1D) * (3 + (1 if c else 0)), "block D1")
        d2 = _u16(payload, 0x1A)
        w.take(8 * d2, "block D2")
        for _ in range(d2):
            w.cstring("block D strings")
        w.take(8 * _u16(payload, 0x1E), "block D3")

    flags = _u8(payload, 0x08)
    if flags & 0x20:                                                # E
        base = w.at
        w.take(8, "block E header")
        for _ in range(_u32(payload, base + 4)):
            rec = w.at
            w.take(0x2E, "block E record")
            w.take(_block_e_payload(payload, rec), "block E payload")

    if flags & 0x80:                                                # F
        count = _u16(payload, 0x52)
        if count == 0:
            raise Undecodable("flags & 0x80 with u16@0x52 == 0 "
                              "(0x00795C3F refuses)")
        base = w.at
        w.take(48 * count, "block F records")
        sum_a = sum(_u32(payload, base + 48 * i + 0x28) for i in range(count))
        sum_b = sum(_u32(payload, base + 48 * i + 0x2C) for i in range(count))
        if sum_a == 0 or sum_b == 0:
            raise Undecodable("block F sums are zero "
                              "(0x00795CEA/0x00795CF2 refuse)")
        w.take(24 * sum_a + 16 * sum_b, "block F payload")
    return w.at


def _block_e_payload(payload, rec):
    """Bytes after a block-E record, per the callback at `0x00796ED0`."""
    fl = _u8(payload, rec + 0x0C)
    if fl & 2:
        eax = _u16(payload, rec + 0x14)
        edx = 0
        edi = eax
    else:
        base = _u16(payload, rec + 0x14)
        edx = (base - _u16(payload, rec + 0x28)) & 0xFFFFFFFF
        edi = eax = base
    eax &= 0xFFFF
    if fl & 0x40:
        ebx = eax
        edi = eax
    else:
        ebx = _u32(payload, rec + 0x1A)
        edi &= 0xFFFF
    ecx = _u16(payload, rec + 0x26) + _u16(payload, rec + 0x24)
    ecx = _u16(payload, rec + 0x22) + ecx * 2
    ecx += _u32(payload, rec + 0x04) + ebx + _u32(payload, rec + 0x00)
    span = (edx + _u32(payload, rec + 0x1E) * 2) & 0xFFFFFFFF
    total = (span * 9 + ecx * 2 + _u32(payload, rec + 0x2A)
             + _u32(payload, rec + 0x16))
    per = 8 * _u8(payload, rec + 0x13) + 0x0C
    return per * (edi & 0xFFFF) + 2 * total


def trailing_end(payload, at):
    """Walk the THREE blocks that follow the collision meshes.

    **This is what the search could not see, and the whole cause of the
    ~15% failure population** (rung M6): the client's stream does not end at
    the last collision mesh, so a walk requiring closure THERE could never
    close on a file carrying one of these. MEASURED on a 1,948-row sample --
    of 931 files the old search called `NoClose`, 930 carry block I and/or
    block J, and exactly one is unexplained.

        H  0x0079564A  if u8@0x31: 16*u8@0x31 + 0x54*u8@0x32
        I  0x0079574D  u32@0x48 records of 4 bytes, each + 8*u32@rec
        J  0x007957B4  if u32@0x34: that many bytes (0x00795DA0)
    """
    w = _Cursor(payload)
    w.at = at
    if _u8(payload, 0x31):                                          # H
        w.take(16 * _u8(payload, 0x31) + 0x54 * _u8(payload, 0x32),
               "block H")
    for _ in range(_u32(payload, 0x48)):                            # I
        rec = w.at
        w.take(4, "block I record")
        w.take(8 * _u32(payload, rec), "block I payload")
    tail = _u32(payload, 0x34)                                      # J
    if tail:
        w.take(tail, "block J")
    return w.at


def _walk_models(payload, start, n):
    """The survey's walk, gates and all. Returns (end, raw records) or None.

    The gates are part of the MEASUREMENT — the closure censuses were taken
    under exactly these bounds — so they live here and nowhere else.
    """
    p = start
    out = []
    for _ in range(n):
        if p + SUBMODEL_HEADER.size > len(payload):
            return None
        unk, n0, n1, n2, nv, fvf, u0, u1, u2 = SUBMODEL_HEADER.unpack_from(
            payload, p)
        if nv == 0 or nv > MAX_VERTICES or fvf > MAX_FVF:
            return None
        vs = vertex_stride(fvf)
        if vs < MIN_STRIDE or vs > MAX_STRIDE:
            return None
        ti = n0 + (n0 != n1) * n1 + (n1 != n2) * n2
        rec = SUBMODEL_HEADER.size + ti * 2 + nv * vs + (u0 + u1 + u2 * 3) * 4
        if p + rec > len(payload):
            return None
        out.append((p, unk, (n0, n1, n2), ti, nv, fvf, vs, (u0, u1, u2)))
        p += rec
    return p, out


def _walk_collision(payload, p, n):
    out = []
    for _ in range(n):
        if p + COLLISION_HEADER.size > len(payload):
            return None
        ni, nv = COLLISION_HEADER.unpack_from(payload, p)
        if ni > MAX_COLLISION_COUNT_FIELD or nv > MAX_COLLISION_COUNT_FIELD:
            return None
        rec = COLLISION_HEADER.size + ni * 2 + nv * 12
        if p + rec > len(payload):
            return None
        out.append((p, ni, nv))
        p += rec
    return p, out


def _submodel(payload, rec):
    p, unk, counts, ti, nv, fvf, vs, u = rec
    ip = p + SUBMODEL_HEADER.size
    vp = ip + ti * 2
    tp = vp + nv * vs
    tlen = (u[0] + u[1] + u[2] * 3) * 4
    return SubModel(unk, counts, nv, fvf, vs, u,
                    struct.unpack_from(f"<{ti}H", payload, ip) if ti else (),
                    payload[vp:vp + nv * vs],
                    payload[tp:tp + tlen])


def _collision(payload, rec):
    p, ni, nv = rec
    ip = p + COLLISION_HEADER.size
    vp = ip + ni * 2
    idx = struct.unpack_from(f"<{ni}H", payload, ip) if ni else ()
    pos = [POSITION.unpack_from(payload, vp + i * 12) for i in range(nv)]
    return CollisionMesh(idx, pos)


class ModelFile:
    """One `ffna` type 2 file: the chunk walk, and the geometry on demand."""

    __slots__ = ("ffna_type", "chunks")

    def __init__(self, ffna_type_, chunks):
        self.ffna_type = ffna_type_
        self.chunks = list(chunks)              # (chunk_id, payload bytes)

    @classmethod
    def decode(cls, data):
        t = ffna_type(data)
        if t != MODEL_FFNA_TYPE:
            raise Undecodable(
                f"ffna type {t}, not the model type {MODEL_FFNA_TYPE} "
                f"(3 is a map)")
        chunks = [(cid, bytes(data[off:off + size]))
                  for cid, off, size in ffna_chunks(data)]
        return cls(t, chunks)

    @classmethod
    def from_row(cls, row, archive):
        entry = next((e for e in archive.entries if e.index == row), None)
        if entry is None:
            raise ValueError(f"MFT row {row} does not exist in {archive.path}")
        return cls.decode(archive.read(entry))

    @classmethod
    def load(cls, file_id, archive, table=None):
        """Open a model by file id — the id a dependency chunk resolves to."""
        table = file_id_table(archive) if table is None else table
        row = table.get(file_id)
        if row is None:
            raise KeyError(f"no file id 0x{file_id:X} in {archive.path}")
        return cls.from_row(row, archive)

    def find(self, chunk_id):
        for cid, payload in self.chunks:
            if cid == chunk_id:
                return payload
        return None

    def geometry(self):
        """The decoded geometry, or None when the file has no 0xFA0 chunk.

        Decode refusals (`NoClose`, a bad index) propagate — a present chunk
        that does not parse is a finding, not an absence.
        """
        payload = self.find(GEOMETRY_CHUNK)
        if payload is None:
            return None
        return ModelGeometry.decode(payload)

    def texture_refs(self):
        """The model's texture file ids, in slot order. `None` per NULL slot.

        Chunk `0x00000FA5` is `u32 count` then `count` VARIABLE-LENGTH slots:
        a `u16 id0`, and if that is zero the slot ENDS there (two bytes, a
        null reference); otherwise `u16 id1, u16 pad` follows and the pair is
        the same encoding a map's Dependencies chunk uses
        (`mapchunks.dependency_file_id`).

        MEASURED 2026-08-14: the walk closes on the exact final byte for
        857/857 FA5 chunks over a strided corpus sweep and 315/315 on the two
        reference maps, where eight rival framings close 0/315 -- including
        the fixed-6-byte reading, which closes only 642/857 corpus-wide, so
        the 2-byte null slot is what explains the other 215. Every non-null
        reference resolves through the file-id table AND lands on a texture:
        1,795/1,795 on the reference maps.

        **`0x00000FA1` is NOT this.** The upstream claim that FA1 and FA5 are
        both "texture filenames" is refuted for FA1: this framing closes
        0/615 on it, its length is usually not 4-aligned, and sliding every
        6-byte window of every FA1 yields exactly 1 texture-decoding hit in
        89,013 against FA5's 1,795 of 1,798. FA1's contents are NOT DECODED.
        """
        payload = self.find(TEXNAME_CHUNK_B)
        if payload is None:
            return []
        if len(payload) < 4:
            raise Undecodable(f"texture chunk is {len(payload)} bytes, under "
                              f"its 4-byte count")
        count, = struct.unpack_from("<I", payload, 0)
        out = []
        at = 4
        for slot in range(count):
            if at + 2 > len(payload):
                raise Undecodable(f"texture slot {slot} of {count} runs past "
                                  f"the chunk's {len(payload)} bytes")
            id0, = struct.unpack_from("<H", payload, at)
            at += 2
            if id0 == 0:
                out.append(None)
                continue
            if at + 4 > len(payload):
                raise Undecodable(f"texture slot {slot} of {count} is "
                                  f"truncated")
            id1, _pad = struct.unpack_from("<HH", payload, at)
            at += 4
            out.append(mapchunks.dependency_file_id(id0, id1))
        if at != len(payload):
            raise Undecodable(
                f"the texture-slot walk ends at {at} of {len(payload)} "
                f"bytes; {count} slots do not account for the chunk")
        return out

    def __repr__(self):
        ids = ", ".join(f"0x{cid:X}" for cid, _p in self.chunks)
        return f"<ModelFile type {self.ffna_type}, chunks [{ids}]>"


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--file-id", default=None,
                    help="decode one model file, e.g. 0x2E52A")
    ap.add_argument("--row", type=int, default=None)
    args = ap.parse_args(argv)

    if (args.file_id is None) == (args.row is None):
        ap.error("give exactly one of --file-id and --row")

    with Archive(args.dat) as ar:
        if args.file_id is not None:
            mf = ModelFile.load(int(args.file_id, 0), ar)
        else:
            mf = ModelFile.from_row(args.row, ar)
        print(mf)
        try:
            geo = mf.geometry()
        except NoClose as exc:
            print(f"  geometry: NO CLOSE -- {exc}")
            return 1
        if geo is None:
            print("  geometry: no 0xFA0 chunk")
            return 1
        print(f"  {geo!r}")
        for i, sm in enumerate(geo.submodels):
            print(f"  sub-model {i}: {sm!r}")
        for i, cm in enumerate(geo.collisions):
            print(f"  collision {i}: {cm!r}")
        print(f"  max 2D radius {geo.max_2d_radius():.4f}   "
              f"(3D {geo.max_3d_radius():.4f})")
        if geo.ambiguous:
            print(f"  AMBIGUOUS: closes at {geo.starts}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
