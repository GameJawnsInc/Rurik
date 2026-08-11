"""The pathing chunk `0x20000008`, decoded to typed values and encoded back.

`pathmap.py` reads this chunk to answer "is this walkable" and throws the rest
away: it skips the boundary polygon, the point-location DAG, the plane map and
the obstacle grid, and it keeps no framing. That is the right shape for a
server. It is the wrong shape for an author, who has to hand the client back
every byte it expects. This module is the other half -- a whole-chunk codec --
and it exists to be judged by one number:

    A RETAIL PATHING CHUNK RE-ENCODES BYTE-IDENTICALLY ON 349 OF 349 MAPS.

WHY THAT NUMBER IS WORTH ANYTHING. It would be worthless if this were a memcpy,
and there is a real way to write one by accident: keep every record's declared
`size` and every plane header's declared count, replay them, and a codec that
understood nothing would round-trip every file it could walk. So nothing
declared is stored.

  * Every record's `size` is RE-DERIVED from the payload this module emits.
  * Every one of the eight plane-header counts is RE-DERIVED from the length of
    the list it counts.
  * The `u16 count` in the boundary polygon, the `u16 n` of the plane map and
    the `u16 m` of the obstacle list are re-derived the same way.

`test_pathchunk.py` mutates a decoded chunk until its payload changes length and
requires the emitted size and count fields to move with it, because that is the
only check that separates this from the memcpy.

TAG 11'S SIZE FIELD IS DOUBLE ITS DATA, AND WE REPRODUCE THE LIE. In every plane
of every map -- MEASURED, 11,795 of 11,795 -- the `polyData` sub-record declares
exactly twice the bytes that follow it. The counts are authoritative and the
size is not (`pathmap.py`'s header says the same, from the reading side). An
encoder that "fixes" this to the true length emits a chunk that differs from
retail in one u32 per plane, and it is the single most likely way to get this
module wrong. `_emit` therefore takes an explicit size, and the tag-11 call site
is the only one that passes one.

WHAT IS FIXED, AND WHY THIS MODULE IS ALLOWED TO BE STRICT. There is no dispatch
loop anywhere in this format. The client drives a fixed seven-stage table
(FINDINGS §17.4, read out of `Gw.exe` at `0x00A6F278`) -- header, tag 7, 8, 12,
13, 14, 255 -- and a fixed ten-record table per plane at `0xBF730C` in the order
0, 11, 1, 2, 3, 4, 5, 6, 10, 9. The archive agrees on 349/349 and 11,795/11,795.
So a record out of order is a broken chunk, not a variant, and `from_chunk`
raises rather than guessing past it.

WHAT IS MEASURED HERE, ALL 349/349 OR 11,795/11,795 unless stated:

  header      `u32 0xEEFE704C, u32 12, u32 sequence` -- TWELVE bytes. The
              terrain chunk's header is eight, and using eight here desyncs the
              first record. `sequence` is read, compared against 0xFFFFFFFF and
              discarded by the loader; it is stored and replayed here.
  tag 7       `u16 count` + count Vec2f, `size == 2 + 8*count`. Never read by
              the Bloated loader -- only its size matters, because tag 8 must
              land at the next offset. It is a byte-identical copy of plane 0's
              `polyData` (with the count prefixed) on 349 of 349, which this
              module records and does NOT enforce: the two are separate fields
              in the file and an author may make them disagree.
  tag 8       `u32 planeCount`, then per plane the ten sub-records above with
              element sizes 32/8/8/44/1/16/12/4/4/9.
  tag 12      `u16 n` + n `u16`. `n == planeCount` on 346 maps; on the three
              one-plane maps (rows 26209, 46196, 71496) `n == 0` and the record
              is two bytes. Both forms are round-tripped as they sit.
  tag 13      `u16 w, u16 h, u16 m`, then `w*h` 3-byte tiles and `m` 12-byte
              records, `size == 6 + 3wh + 12m`. The grid is the map rect at
              1024 units per cell: `w*1024 == rectX` and `h*1024 == rectY` on
              349 of 349, measured against the Map Parameters chunk.
  tag 14      `u32 hash, u8 flag`, size 5.
  tag 255     terminator, size 0, and the walk closes to the final byte.

THE DAG CHILD REFERENCES ARE TAGGED, and an author has to reproduce the tag
space exactly. `0x007264A0` decodes each `u32` as: `0xFFFFFFFF` NULL,
`>= 0x80000000` sink node, `>= 0x40000000` y node, else x node (FINDINGS §17.4).
Re-measured here while building this module: 10,829,572 references across the
corpus split 4,462,623 x / 2,784,573 null / 2,125,005 y / 1,457,371 sink with
zero out-of-range indices after masking -- the same four figures §17.4 reports,
from a second walk. `child_ref` and `child_kind` are that encoding, and they are
the only part of a plane an author is likely to have to compute rather than copy.

WHAT IS STILL NOT UNDERSTOOD, said plainly because `minimal()` has to emit it
anyway: tag 12's values (non-decreasing, first element 0 on 346 of 346, but
larger than the plane count on 343 of them, so they are NOT plane indices --
meaning NOT FOUND); tag 13's 3-byte tiles (NOT FOUND -- 112,276 of the corpus's
tiles are three zero bytes, which is what every cell of the smallest map is);
and what `edgeVectors` are geometrically (their count is never the polyData
count -- 11,795 of 11,795 -- so they are not one per polygon point).

Sink node payloads are trapezoid indices as far as the file can say: every value
is below its own plane's trapezoid count, 11,795 of 11,795 planes. `rootType`
(tag 3) is 1 on all 11,795 planes; the client's code has three modes and retail
exercises one.

    python toolkit/mapdata/pathchunk.py            # round-trip one map, verbosely
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# The typed values are pathmap's, deliberately: it is the module that already
# consumes them, and a second Trapezoid class would be a second definition of
# the same 44 bytes. Nothing here writes to pathmap.
from pathmap import Portal, Trapezoid  # noqa: E402
from archive import Archive, ffna_chunks, file_id_table  # noqa: E402

PATHING_CHUNK = 0x20000008
SIGNATURE = 0xEEFE704C
VERSION = 12

TAG_BOUNDARY = 7
TAG_PLANES = 8
TAG_PLANE_MAP = 12
TAG_OBSTACLES = 13
TAG_SYNC = 14
TERMINATOR = 255

# The client's seven-stage table, and the archive's own order on 349/349.
CHUNK_TAG_ORDER = (TAG_BOUNDARY, TAG_PLANES, TAG_PLANE_MAP, TAG_OBSTACLES,
                   TAG_SYNC, TERMINATOR)
# The per-plane table at 0xBF730C, with the disk stride of one element.
PLANE_TAG_ORDER = (0, 11, 1, 2, 3, 4, 5, 6, 10, 9)
PLANE_ELEMENT_SIZE = {11: 8, 1: 8, 2: 44, 4: 16, 5: 12, 6: 4, 10: 4, 9: 9}
# Plane header counts, in the order the 32-byte record stores them. NOTE that
# `portals` precedes `portalTraps` here while the RECORDS run 10 (portalTraps)
# then 9 (portals); the two orders genuinely differ.
PLANE_HEADER_FIELDS = ("polyData", "edgeVectors", "trapezoids", "xNodes",
                       "yNodes", "sinkNodes", "portals", "portalTraps")
PLANE_HEADER_SIZE = 32
ROOT_TYPE_SIZE = 1
OBSTACLE_CELL = 1024.0

NO_NEIGHBOUR = 0xFFFFFFFF
NO_PORTAL = 0xFFFF

# The point-location DAG's child reference tag space (FINDINGS §17.4).
CHILD_NULL = 0xFFFFFFFF
CHILD_SINK_BASE = 0x80000000
CHILD_Y_BASE = 0x40000000

_HEADER = struct.Struct("<III")
_REC = struct.Struct("<BI")
_U16 = struct.Struct("<H")
_U32 = struct.Struct("<I")
_VEC2 = struct.Struct("<2f")
_TRAP = struct.Struct("<4I2H6f")
_PORTAL = struct.Struct("<4HB")
_XNODE = struct.Struct("<4I")
_YNODE = struct.Struct("<3I")
_PLANE_HEADER = struct.Struct("<8I")
_GRID = struct.Struct("<3H")
_OBSTACLE = struct.Struct("<3f")
_SYNC = struct.Struct("<IB")


# ------------------------------------------------------------ the tag space

def child_kind(ref):
    """('null'|'sink'|'ynode'|'xnode', index) for one DAG child reference.

    The index of a NULL is None. Everything else is the reference with its tag
    bits cleared, which is what the client's bounds asserts compare.
    """
    if ref == CHILD_NULL:
        return ("null", None)
    if ref >= CHILD_SINK_BASE:
        return ("sink", ref - CHILD_SINK_BASE)
    if ref >= CHILD_Y_BASE:
        return ("ynode", ref - CHILD_Y_BASE)
    return ("xnode", ref)


def child_ref(kind, index=0):
    """The inverse of `child_kind`. Raises rather than truncating an index."""
    if kind == "null":
        return CHILD_NULL
    base = {"xnode": 0, "ynode": CHILD_Y_BASE, "sink": CHILD_SINK_BASE}.get(kind)
    if base is None:
        raise ValueError(f"no such child kind: {kind!r}")
    # An x or y index has 30 bits. A sink has 31, minus the one value that
    # would collide with NULL -- index 0x7FFFFFFF encodes as 0xFFFFFFFF, which
    # the client reads as "no child" rather than as sink 0x7FFFFFFF.
    limit = CHILD_Y_BASE if kind in ("xnode", "ynode") else CHILD_NULL - CHILD_SINK_BASE
    if not 0 <= index < limit:
        raise ValueError(f"{kind} index {index} does not fit the tag space")
    return base + index


# ------------------------------------------------------------------ framing

def _emit(out, tag, payload, size=None):
    """Append one `u8 tag, u32 size, payload` record.

    `size` defaults to the true payload length and is passed explicitly at
    exactly one call site: tag 11, whose declared size is double its data in
    every plane of every retail map.
    """
    out += _REC.pack(tag, len(payload) if size is None else size)
    out += payload


def _header(buf, p, want, where):
    """Read a record header, checking the tag. Returns (body offset, declared)."""
    if p + _REC.size > len(buf):
        raise ValueError(f"{where}: record header runs off the end at {p} "
                         f"of {len(buf)}")
    tag, size = _REC.unpack_from(buf, p)
    if tag != want:
        raise ValueError(f"{where}: expected tag {want}, found tag {tag} at {p}")
    if p + _REC.size + size > len(buf):
        raise ValueError(f"{where}: declares {size} bytes at {p}, only "
                         f"{len(buf) - p - _REC.size} remain")
    return p + _REC.size, size


def _vec2s(buf, off, count):
    return [_VEC2.unpack_from(buf, off + 8 * i) for i in range(count)]


def _pack_vec2s(points):
    return b"".join(_VEC2.pack(float(x), float(y)) for x, y in points)


# ------------------------------------------------------------------- values

class Obstacles:
    """Tag 13: a coarse grid over the map rect plus a list of round obstacles.

    `width`/`height` are cells of 1024 world units -- `w*1024` equals the Map
    Parameters rect extent on 349 of 349 maps, measured against that chunk.
    `tiles` is `3*width*height` bytes whose meaning is NOT FOUND and which are
    therefore carried verbatim; `records` are (x, y, radius) float triples, the
    radii running 2.167 to 525.83 over 194,200 of them (FORMAT.md).
    """

    __slots__ = ("width", "height", "tiles", "records")

    def __init__(self, width, height, tiles=None, records=()):
        self.width = int(width)
        self.height = int(height)
        want = 3 * self.width * self.height
        self.tiles = bytes(tiles) if tiles is not None else bytes(want)
        if len(self.tiles) != want:
            raise ValueError(f"obstacle grid {self.width}x{self.height} needs "
                             f"{want} tile bytes, got {len(self.tiles)}")
        self.records = [tuple(r) for r in records]

    @classmethod
    def for_rect(cls, rect):
        """An empty grid sized the way every retail map sizes it.

        `rect` is (min_x, min_y, max_x, max_y). The cell count is the extent
        over 1024, which is exact for every legal map rect (extent is
        dims*96 with dims a multiple of 32, hence a multiple of 3072).
        """
        min_x, min_y, max_x, max_y = rect
        ex, ey = max_x - min_x, max_y - min_y
        if ex <= 0 or ey <= 0:
            raise ValueError(f"rect {rect} has no extent")
        w = int(-(-ex // OBSTACLE_CELL))
        h = int(-(-ey // OBSTACLE_CELL))
        return cls(w, h)

    def encode(self):
        return (_GRID.pack(self.width, self.height, len(self.records))
                + self.tiles
                + b"".join(_OBSTACLE.pack(*r) for r in self.records))

    @classmethod
    def decode(cls, buf, off, size):
        if size < _GRID.size:
            raise ValueError(f"tag 13: {size} bytes cannot hold its 6-byte head")
        w, h, m = _GRID.unpack_from(buf, off)
        want = _GRID.size + 3 * w * h + _OBSTACLE.size * m
        if size != want:
            raise ValueError(f"tag 13: size {size} != 6 + 3*{w}*{h} + 12*{m} "
                             f"= {want}")
        base = off + _GRID.size
        tiles = bytes(buf[base:base + 3 * w * h])
        rbase = base + 3 * w * h
        recs = [_OBSTACLE.unpack_from(buf, rbase + _OBSTACLE.size * i)
                for i in range(m)]
        return cls(w, h, tiles, recs)

    def __repr__(self):
        return (f"<Obstacles {self.width}x{self.height} grid, "
                f"{len(self.records)} obstacle(s)>")


class Plane:
    """One walkable surface: ten sub-records, in the client's fixed order.

    Every count in the 32-byte header is derived from the list it counts when
    this is encoded, so the lists are the truth and the header is output.
    """

    __slots__ = ("index", "poly", "edges", "traps", "root_type",
                 "x_nodes", "y_nodes", "sinks", "portal_traps", "portals")

    def __init__(self, index=0, poly=(), edges=(), traps=(), root_type=1,
                 x_nodes=(), y_nodes=(), sinks=(), portal_traps=(), portals=()):
        self.index = index
        self.poly = list(poly)                 # [(x, y)]
        self.edges = list(edges)               # [(x, y)]
        self.traps = list(traps)               # [Trapezoid]
        self.root_type = int(root_type)        # 0 = x, 1 = y, 2 = sink
        self.x_nodes = list(x_nodes)           # [(edgeA, edgeB, child0, child1)]
        self.y_nodes = list(y_nodes)           # [(edge, child0, child1)]
        self.sinks = list(sinks)               # [trapezoid index]
        self.portal_traps = list(portal_traps)  # [trapezoid index]
        self.portals = list(portals)           # [Portal]

    # -- the eight header counts, derived and never stored ----------------

    @property
    def counts(self):
        return (len(self.poly), len(self.edges), len(self.traps),
                len(self.x_nodes), len(self.y_nodes), len(self.sinks),
                len(self.portals), len(self.portal_traps))

    def encode(self):
        out = bytearray()
        _emit(out, 0, _PLANE_HEADER.pack(*self.counts))
        poly = _pack_vec2s(self.poly)
        # THE DOUBLING. Not a bug being propagated blindly -- see the module
        # header; retail declares 2x here in 11,795 of 11,795 planes.
        _emit(out, 11, poly, size=2 * len(poly))
        _emit(out, 1, _pack_vec2s(self.edges))
        _emit(out, 2, b"".join(
            _TRAP.pack(t.neighbours[0], t.neighbours[1], t.neighbours[2],
                       t.neighbours[3], t.portal_left, t.portal_right,
                       t.y_top, t.y_bottom, t.x_top_left, t.x_top_right,
                       t.x_bottom_left, t.x_bottom_right) for t in self.traps))
        _emit(out, 3, bytes((self.root_type,)))
        _emit(out, 4, b"".join(_XNODE.pack(*n) for n in self.x_nodes))
        _emit(out, 5, b"".join(_YNODE.pack(*n) for n in self.y_nodes))
        _emit(out, 6, b"".join(_U32.pack(v) for v in self.sinks))
        _emit(out, 10, b"".join(_U32.pack(v) for v in self.portal_traps))
        _emit(out, 9, b"".join(
            _PORTAL.pack(p.traps, p.offset, p.neighbour, p.pair_id, p.flag)
            for p in self.portals))
        return bytes(out)

    @classmethod
    def decode(cls, buf, p, index, limit):
        """Read one plane starting at `p`. Returns (plane, next offset)."""
        where = f"plane {index}"
        counts = {}
        self = cls(index=index)
        for want in PLANE_TAG_ORDER:
            body, declared = _header(buf, p, want, where)
            esz = PLANE_ELEMENT_SIZE.get(want)
            if want == 0:
                if declared != PLANE_HEADER_SIZE:
                    raise ValueError(f"{where}: header record declares "
                                     f"{declared} bytes, not {PLANE_HEADER_SIZE}")
                counts = dict(zip(PLANE_HEADER_FIELDS,
                                  _PLANE_HEADER.unpack_from(buf, body)))
                length = declared
            elif want == 3:
                if declared != ROOT_TYPE_SIZE:
                    raise ValueError(f"{where}: root-type record declares "
                                     f"{declared} bytes, not {ROOT_TYPE_SIZE}")
                self.root_type = buf[body]
                length = declared
            else:
                field = PLANE_HEADER_FIELDS[
                    {11: 0, 1: 1, 2: 2, 4: 3, 5: 4, 6: 5, 9: 6, 10: 7}[want]]
                n = counts[field]
                length = n * esz
                if want == 11:
                    # The lie, checked rather than assumed. A map that broke it
                    # would be re-encoded wrong, so this refuses instead.
                    if declared != 2 * length:
                        raise ValueError(
                            f"{where}: tag 11 declares {declared}, expected "
                            f"twice its {length} bytes of data")
                elif declared != length:
                    raise ValueError(f"{where}: tag {want} declares {declared}, "
                                     f"expected {n} x {esz} = {length}")
                if body + length > limit:
                    raise ValueError(f"{where}: tag {want} runs past tag 8's "
                                     f"payload ({body + length} > {limit})")
                self._fill(want, buf, body, n)
            p = body + length
        return self, p

    def _fill(self, tag, buf, body, n):
        if tag == 11:
            self.poly = _vec2s(buf, body, n)
        elif tag == 1:
            self.edges = _vec2s(buf, body, n)
        elif tag == 2:
            self.traps = [
                Trapezoid(self.index, i, *_reorder_trap(
                    _TRAP.unpack_from(buf, body + 44 * i)))
                for i in range(n)]
        elif tag == 4:
            self.x_nodes = [_XNODE.unpack_from(buf, body + 16 * i)
                            for i in range(n)]
        elif tag == 5:
            self.y_nodes = [_YNODE.unpack_from(buf, body + 12 * i)
                            for i in range(n)]
        elif tag == 6:
            self.sinks = list(struct.unpack_from(f"<{n}I", buf, body)) if n else []
        elif tag == 10:
            self.portal_traps = (list(struct.unpack_from(f"<{n}I", buf, body))
                                 if n else [])
        elif tag == 9:
            self.portals = [Portal(self.index, i,
                                   *_PORTAL.unpack_from(buf, body + 9 * i))
                            for i in range(n)]

    def __repr__(self):
        return (f"<Plane {self.index}: {len(self.traps)} trapezoid(s), "
                f"{len(self.portals)} portal(s)>")


def _reorder_trap(t):
    """44 disk bytes -> Trapezoid's constructor order."""
    ntl, ntr, nbl, nbr, pl, pr, yt, yb, xtl, xtr, xbl, xbr = t
    return (yt, yb, xtl, xtr, xbl, xbr, (ntl, ntr, nbl, nbr), pl, pr)


class PathChunk:
    """A whole `0x20000008` payload: six records and a 12-byte header."""

    __slots__ = ("version", "sequence", "boundary", "planes", "plane_map",
                 "obstacles", "sync_hash", "sync_flag")

    def __init__(self, sequence=0, boundary=(), planes=(), plane_map=(),
                 obstacles=None, sync_hash=0, sync_flag=0, version=VERSION):
        self.version = int(version)
        self.sequence = int(sequence)
        self.boundary = [tuple(p) for p in boundary]
        self.planes = list(planes)
        self.plane_map = [int(v) for v in plane_map]
        self.obstacles = obstacles if obstacles is not None else Obstacles(0, 0)
        self.sync_hash = int(sync_hash)
        self.sync_flag = int(sync_flag)

    # -- encode ----------------------------------------------------------

    def encode(self):
        """The chunk payload. Every size and count below is derived here."""
        out = bytearray(_HEADER.pack(SIGNATURE, self.version, self.sequence))
        _emit(out, TAG_BOUNDARY,
              _U16.pack(len(self.boundary)) + _pack_vec2s(self.boundary))
        _emit(out, TAG_PLANES, self._planes_payload())
        _emit(out, TAG_PLANE_MAP,
              _U16.pack(len(self.plane_map))
              + b"".join(_U16.pack(v) for v in self.plane_map))
        _emit(out, TAG_OBSTACLES, self.obstacles.encode())
        _emit(out, TAG_SYNC, _SYNC.pack(self.sync_hash, self.sync_flag))
        out += _REC.pack(TERMINATOR, 0)
        return bytes(out)

    def _planes_payload(self):
        out = bytearray(_U32.pack(len(self.planes)))
        for pl in self.planes:
            out += pl.encode()
        return bytes(out)

    # -- decode ----------------------------------------------------------

    @classmethod
    def from_chunk(cls, blob):
        """Decode a pathing chunk payload. Raises ValueError on anything odd.

        Strict on purpose: the client has no dispatch loop here, so an
        unexpected tag is a broken chunk rather than a variant to skip.
        """
        buf = bytes(blob)
        if len(buf) < _HEADER.size:
            raise ValueError(f"pathing chunk is {len(buf)} bytes, under the "
                             f"{_HEADER.size}-byte header")
        sig, version, sequence = _HEADER.unpack_from(buf, 0)
        if sig != SIGNATURE:
            raise ValueError(f"pathing signature 0x{sig:08X} != 0x{SIGNATURE:08X}")
        if version != VERSION:
            raise ValueError(f"pathing version {version} != {VERSION}")
        self = cls(sequence=sequence, version=version)

        p = _HEADER.size
        body, size = _header(buf, p, TAG_BOUNDARY, "tag 7")
        self.boundary = _decode_points(buf, body, size, "tag 7")
        p = body + size

        body, size = _header(buf, p, TAG_PLANES, "tag 8")
        self.planes = _decode_planes(buf, body, size)
        p = body + size

        body, size = _header(buf, p, TAG_PLANE_MAP, "tag 12")
        self.plane_map = _decode_u16s(buf, body, size, "tag 12")
        p = body + size

        body, size = _header(buf, p, TAG_OBSTACLES, "tag 13")
        self.obstacles = Obstacles.decode(buf, body, size)
        p = body + size

        body, size = _header(buf, p, TAG_SYNC, "tag 14")
        if size != _SYNC.size:
            raise ValueError(f"tag 14: size {size} != {_SYNC.size}")
        self.sync_hash, self.sync_flag = _SYNC.unpack_from(buf, body)
        p = body + size

        body, size = _header(buf, p, TERMINATOR, "tag 255")
        if size != 0:
            raise ValueError(f"tag 255: terminator declares {size} bytes")
        p = body
        if p != len(buf):
            raise ValueError(f"tag walk ended at {p} of {len(buf)} bytes")
        return self

    @classmethod
    def from_map(cls, data):
        """Decode the pathing chunk out of a whole `ffna` map payload."""
        for chunk_id, off, size in ffna_chunks(data):
            if chunk_id == PATHING_CHUNK:
                return cls.from_chunk(bytes(data[off:off + size]))
        raise ValueError("this map file has no 0x20000008 pathing chunk")

    @classmethod
    def load(cls, map_file_id, archive=None, table=None):
        """Open a map by the file id a server hands the client. Read-only."""
        own = archive is None
        ar = archive or Archive()
        try:
            table = table if table is not None else file_id_table(ar)
            row = table.get(map_file_id)
            if row is None:
                raise KeyError(f"no file id 0x{map_file_id:X} in the archive")
            entry = next(e for e in ar.entries if e.index == row)
            return cls.from_map(ar.read(entry))
        finally:
            if own:
                ar.close()

    # -- authoring -------------------------------------------------------

    @classmethod
    def minimal(cls, planes=1, rect=(0.0, 0.0, 3072.0, 3072.0), sequence=0,
                plane_map=None):
        """A mesh with `planes` planes and one rectangular trapezoid each.

        Enough to author a pathing chunk without an archive. Every plane covers
        the whole rect and no plane is joined to another: there are no portals,
        so a character cannot cross between them. That is the honest minimum --
        a plane is not an elevation and nothing in the file says what z it sits
        at, so inventing a connection would be inventing geometry.

        Defaults reproduce what row 46196 -- the smallest complete retail map,
        and the ladder's template -- actually carries: one plane, a 3x3 zeroed
        obstacle grid over its 3072x3072 rect, no obstacle records, and the
        TWO-BYTE form of tag 12 (n == 0), which is what all three one-plane
        maps in the corpus use. `minimal(planes=2)` gets the other form.

        The point-location DAG is INFERRED, not copied: `rootType` is 1 (a y
        node) because retail is 1 on 11,795 of 11,795 planes, and the single y
        node sends both children to the one sink, which names trapezoid 0. Both
        branches therefore land in the only trapezoid there is, whatever the
        split test decides, so the split's `edge` never has to mean anything --
        which is as well, since what an edge vector is geometrically is NOT
        FOUND.

        OBSERVED 2026-08-11 (FINDINGS 23), and this replaces the standing
        "UNVERIFIED against a client" on this docstring: the retail client
        COLLIDES against what this returns. Two maps identical but for 33 bytes
        in this chunk -- `rect` 0..3072 against 1024..2048 -- confined the
        character to bounding boxes of 3072.0 and 1024.0 units, pinned to the
        rect's own edges to the bit. What is verified is the walkable geometry
        as a whole; the boundary polygon, the trapezoid and the DAG were shrunk
        together, so which of the three the client reads is still open.
        """
        if planes < 1:
            raise ValueError("a pathing chunk with no plane has no geometry")
        min_x, min_y, max_x, max_y = (float(v) for v in rect)
        if max_x <= min_x or max_y <= min_y:
            raise ValueError(f"rect {rect} has no extent")
        corners = [(min_x, min_y), (min_x, max_y), (max_x, max_y), (max_x, min_y)]
        out = []
        for i in range(planes):
            trap = Trapezoid(i, 0, max_y, min_y, min_x, max_x, min_x, max_x,
                             (NO_NEIGHBOUR,) * 4, NO_PORTAL, NO_PORTAL)
            out.append(Plane(
                index=i, poly=corners, edges=[(0.0, 0.0)], traps=[trap],
                root_type=1,
                y_nodes=[(0, child_ref("sink", 0), child_ref("sink", 0))],
                sinks=[0]))
        if plane_map is None:
            # n == 0 on every one-plane map in the corpus, n == planeCount
            # otherwise. The VALUES are NOT FOUND; zeros satisfy both laws the
            # corpus shows (non-decreasing, first element 0) and nothing more.
            plane_map = [] if planes == 1 else [0] * planes
        return cls(sequence=sequence, boundary=list(corners), planes=out,
                   plane_map=plane_map,
                   obstacles=Obstacles.for_rect((min_x, min_y, max_x, max_y)))

    # -- queries ---------------------------------------------------------

    @property
    def trapezoids(self):
        return [t for pl in self.planes for t in pl.traps]

    def child_census(self):
        """{'xnode'|'ynode'|'sink'|'null': count} over every DAG reference."""
        out = {"xnode": 0, "ynode": 0, "sink": 0, "null": 0}
        for pl in self.planes:
            for n in pl.x_nodes:
                out[child_kind(n[2])[0]] += 1
                out[child_kind(n[3])[0]] += 1
            for n in pl.y_nodes:
                out[child_kind(n[1])[0]] += 1
                out[child_kind(n[2])[0]] += 1
        return out

    def __repr__(self):
        return (f"<PathChunk {len(self.planes)} plane(s), "
                f"{len(self.trapezoids)} trapezoid(s), "
                f"seq {self.sequence}>")


def _decode_points(buf, off, size, where):
    if size < 2:
        raise ValueError(f"{where}: {size} bytes cannot hold a u16 count")
    count, = _U16.unpack_from(buf, off)
    if size != 2 + 8 * count:
        raise ValueError(f"{where}: size {size} != 2 + 8*{count} = {2 + 8 * count}")
    return _vec2s(buf, off + 2, count)


def _decode_u16s(buf, off, size, where):
    if size < 2:
        raise ValueError(f"{where}: {size} bytes cannot hold a u16 count")
    n, = _U16.unpack_from(buf, off)
    if size != 2 + 2 * n:
        raise ValueError(f"{where}: size {size} != 2 + 2*{n} = {2 + 2 * n}")
    return list(struct.unpack_from(f"<{n}H", buf, off + 2)) if n else []


def _decode_planes(buf, off, size):
    if size < 4:
        raise ValueError(f"tag 8: {size} bytes cannot hold a u32 plane count")
    count, = _U32.unpack_from(buf, off)
    limit = off + size
    p = off + 4
    planes = []
    for i in range(count):
        pl, p = Plane.decode(buf, p, i, limit)
        planes.append(pl)
    if p != limit:
        raise ValueError(f"tag 8: plane walk ended at {p - off} of {size} bytes")
    return planes


if __name__ == "__main__":
    KAMADAN = 0x345CC
    fid = int(sys.argv[1], 0) if len(sys.argv) > 1 else KAMADAN
    import time
    with Archive() as _ar:
        _table = file_id_table(_ar)
        _row = _table[fid]
        _entry = next(e for e in _ar.entries if e.index == _row)
        _data = _ar.read(_entry)
        _blob = None
        for _cid, _off, _size in ffna_chunks(_data):
            if _cid == PATHING_CHUNK:
                _blob = bytes(_data[_off:_off + _size])
    t0 = time.perf_counter()
    pc = PathChunk.from_chunk(_blob)
    t1 = time.perf_counter()
    out = pc.encode()
    t2 = time.perf_counter()
    print(f"file id 0x{fid:X} (row {_row}): {len(_blob)} bytes, {pc!r}")
    print(f"  decode {t1 - t0:.2f}s, encode {t2 - t1:.2f}s")
    print(f"  boundary {len(pc.boundary)} pts, plane map {len(pc.plane_map)}, "
          f"{pc.obstacles!r}, sync 0x{pc.sync_hash:08X}/{pc.sync_flag}")
    print(f"  DAG children: {pc.child_census()}")
    print("  round-trip: " + ("IDENTICAL" if out == _blob else
                              f"DIFFERS ({len(out)} vs {len(_blob)} bytes)"))
