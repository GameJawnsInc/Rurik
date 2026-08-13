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

THE VERTEX STRIDE is computed from `dat_fvf` by a byte-cost rule derived in the
survey (RECONSTRUCTION — it is our reading, not the client's own table, which
is rung M2's target):

    +12 for bit 0        +4 for bit 1        +12 for bit 2
    +8 per set bit in 0xF0        +24 if any bit of 0x3000

Its evidence is closure, not preference: the two-stage walk closes to the
exact final byte through 3,834 sub-model records under this rule, and the
thirteen (dat_fvf, stride) pairs it produces are pinned as literals in
`test_modelfile.py`. GuildWarsMapBrowser's FVF lookup table agrees on 3,833 of
3,834 and disagrees on the ONE 0x2C sub-model — which is the ambiguous parse
above, so the disagreement itself rests on an uncertain read. No GWMB table is
used or embedded here; the rule stands on the corpus and awaits the client's
own dispatch (M2).

THE LOAD-BEARING ORACLE, and why this module can be trusted at all: the
Bloated prop record's `f11` field equals `scale * max(sqrt(x^2 + y^2))` over
the referenced model's vertices — a number that crosses TWO FILES and eight
decode steps (prop record -> filename index -> dependency pair -> file id ->
MFT row -> geometry chunk -> sub-model walk -> vertex stride), so no decoder
error at any step survives it. MEASURED at 1e-5 on 12,766 of 12,875 props
over the 14-map sample; 474/474 and 664/664 on the reference maps' comparable
props; the 3D-radius rival scores 103 of 12,875. `test_modelfile.py` pins all
of it.

WHAT IS OPAQUE, so nobody reads more than was measured: the preamble, the
sub-model `unk` word, every vertex byte past the position floats (normals,
UVs and colours are rung M2), the trailing blocks, and the meaning of the
texture-name chunks' contents. `SubModel.vertex_data` and `.trailing` carry
the bytes; nothing interprets them.

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


def vertex_stride(dat_fvf):
    """Bytes per vertex for a format word. RECONSTRUCTION — see the docstring:
    pinned by walk closure over 3,834 sub-models and thirteen literal pairs in
    the test, not by the client's own dispatch (that is rung M2)."""
    s = 0
    if dat_fvf & 1:
        s += 12
    if dat_fvf & 2:
        s += 4
    if dat_fvf & 4:
        s += 12
    s += 8 * bin(dat_fvf & 0xF0).count("1")
    if dat_fvf & 0x3000:
        s += 24
    return s


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

    def positions(self):
        """The f32 (x, y, z) at the head of each vertex. Everything after
        them in the stride is rung M2's problem and stays bytes."""
        out = []
        for i in range(self.nv):
            out.append(POSITION.unpack_from(self.vertex_data, i * self.stride))
        return out

    def __repr__(self):
        return (f"<SubModel {self.nv} verts stride {self.stride} "
                f"(fvf 0x{self.dat_fvf:X}), {self.ti} indices>")


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

        starts = []
        first_walk = None
        for s in range(PREAMBLE_MIN, len(payload) - SUBMODEL_HEADER.size):
            walked = _walk_models(payload, s, num_models)
            if walked is None:
                continue
            end, raw = walked
            if coll == 0:
                if end == len(payload):
                    starts.append(s)
                    if first_walk is None:
                        first_walk = raw
            else:
                cw = _walk_collision(payload, end, coll)
                if cw is not None and cw[0] == len(payload):
                    starts.append(s)
                    if first_walk is None:
                        first_walk = (raw, cw[1])
        if not starts:
            raise NoClose(
                f"no start offset in [{PREAMBLE_MIN}, {len(payload)}) lets "
                f"{num_models} sub-model(s) and {coll} collision mesh(es) "
                f"close on the chunk's {len(payload)} bytes")

        if coll:
            raw, craw = first_walk
        else:
            raw, craw = first_walk, []
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
