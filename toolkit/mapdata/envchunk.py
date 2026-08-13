r"""The Environment chunk: read and write `0x10000009`.

The map's sky, fog, ambient light and horizon water -- the chunk rung (e10i)
proved was the difference between a black void and a lit world ("yep that's a
sky, and it was key to the lighting"). Until 2026-08-13 it was BORROWED whole
from Pre-Searing because nobody had read it; this module is the framing, decoded
to typed sections and re-encoded byte-identically.

    blob = ...                        # chunk 0x10000009 out of a map's partner row
    ec   = EnvChunk.decode(blob)
    assert ec.encode() == blob        # 349 of 349 retail maps

WHAT THE CHUNK IS. Not a flat struct -- a set of PARALLEL ARRAYS of environment
aspects plus a spatial ZONE LIST that binds them to places. This shape was
derived from the corpus (the reference graph closes 349/349) and CORROBORATED
against the client loader at `0x00712750 -> 0x0071ef70`, whose handler table and
two `EnvDataImport` asserts name the pieces. Both are cited per claim.

    u32 signature 0x92991030   u16 version 16   u16 flag       (8-byte header)
    then sections {u8 tag, u16 count, count * record} in STRICTLY ASCENDING tag
    order, then a single 0xFF terminator. The record size per tag (MEASURED from
    each handler's stride, VAs in _SECTIONS):

      tag  size  what it is
       0   10    an aspect array (meaning of the record NOT FOUND)
       1    6    an aspect array
       2   19    FOG: {u8 r, g, b, u32 near, u32 far, i32, i32}, near<far 349/349
       3    8    an aspect array (two 4-byte colour+alpha, INFERRED)
       4    2    a u16 aspect array
       5   15 or 16   an aspect array; the record WIDTH is chosen by `flag`
       6   57    the main environment record: 10 f32 params + 2 colours + 2 deps
       7    4    an opaque u32 array (resource ids? NOT FOUND)
       8   17    FIXED, no count -- the map-GLOBAL default environment ('envGlobal')
       9   32    the ZONE list: {u16 sel[8], i32 x, i32 y, u32 r_in, u32 r_out}
      11    5    per-region records that index the zone list
      12   var   OPTIONAL polygons: count * {u8 npoints, u16 envIndex, npoints*(f32,f32)}

    Tag 10 never occurs (its handler slot is NULL). Tags 0-9 and 11 are present
    in all 349 maps; tag 12 in 104.

THE CENTRAL IDEA, because it is what makes the multiplicity make sense. A map
holds SEVERAL environment configurations and blends between them SPATIALLY, not
by time of day. Record 0 of each aspect array is the map default; a `tag9` zone
is a world-space circle `{x, y, r_in, r_out}` carrying `sel[8]`, one index into
each of the eight arrays (tags 0-7), that overrides the default inside its blend
band `r_in..r_out`. The clincher: all 73 maps with no zones have every aspect
array at count exactly 1 (MEASURED). `tag11` and `tag12` are the second level --
each carries an index the client bounds against the zone-array count (the two
`EnvDataImport` asserts, strings verbatim `tag->index < envArray.Count()` at VA
`0x0072032d` and `data->envIndex < ...` at `0x0072044a`).

WHAT `flag` IS, and the correction it cost. `flag` is the header u16 at offset 6,
and it selects `tag5`'s record width: 15 bytes when 0, 16 when >=1 (the loader
branch `0x0071f1d5 and ecx,0xffff0000; cmp ecx,0x10000`). An earlier corpus-only
reading put this flag in `tag0`'s count field; it is NOT there -- the header word
and `tag0.count` disagree in 168 of 349 maps, and using `tag0`'s count would pick
the wrong `tag5` width in 92. The header is 8 bytes, not the 5 a first pass
guessed; offsets 4-7 are `{u16 version, u16 flag}`.

WHAT IS UNDERSTOOD, AND WHAT IS CARRIED. Fully typed: the header, the fog record,
the zone record, the tag12 polygons, and the two dep references inside every
`tag6` record (offsets 53 and 55, indices into `0x11000009`). Carried as opaque
bytes: the interiors of the tag0/1/3/5/6/8 records -- the loader itself stores
those as raw {ptr, count} and decodes no colour and none of tag6's ten floats
(there is NO `1/101` constant anywhere in the image, so the "authored 0..100
slider" reading is an authoring-time guess, not a runtime fact). This module
exposes the framing and the understood fields; it does not pretend to know the
rest.

NOTHING DECLARED IS STORED. Every section count is re-derived from its record
list on encode; `tag8` has no count; `tag12`'s polygon count is recomputed by
walking. So 349 byte-identical re-encodes are assertions about the framing, not
replays -- `test_envchunk.py` builds the memcpy saboteur that proves it.
"""

import struct

SIGNATURE = 0x92991030
VERSION = 16
TERMINATOR = 0xFF
NONE = 0xFFFF

TAG_GLOBAL = 8                  # the one section with no count field (17 bytes)
TAG_FOG = 2
TAG_ZONES = 9
TAG_POLYGONS = 12
TAG_MAIN = 6

#: tag -> fixed record size for the count-prefixed sections. tag5 is absent here
#: because its width depends on `flag`; tag8 is absent because it has no count;
#: tag12 is absent because its records are variable-length.
_FIXED = {0: 10, 1: 6, 2: 19, 3: 8, 4: 2, 6: 57, 7: 4, 9: 32, 11: 5}

#: The section order every retail map uses (MEASURED, corpus + loader). tag12 is
#: the only optional one; its handler saves and restores the cursor on a tag
#: mismatch (0x007203b5), while the mandatory handlers abort. tag10 is NULL.
ORDER = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12)
_MANDATORY = frozenset(ORDER) - {TAG_POLYGONS}

_HDR = struct.Struct("<IHH")            # signature, version, flag
_U16 = struct.Struct("<H")
GLOBAL_SIZE = 17

_FOG = struct.Struct("<BBBIIii")        # r, g, b, near, far, c, d
_ZONE = struct.Struct("<8HiiII")        # sel[8], x, y, r_in, r_out


class Undecodable(ValueError):
    """The bytes are not an Environment chunk this module understands."""


class Section:
    """One `{tag, records}` section. Records are the raw per-record byte slices;
    `size` is fixed except for tag12, whose records vary. Understood sections
    have typed views layered on top (see `fog`, `zones`, `polygons`)."""

    __slots__ = ("tag", "records")

    def __init__(self, tag, records):
        self.tag = tag
        self.records = list(records)

    def __repr__(self):
        return f"Section(tag={self.tag}, records={len(self.records)})"


class EnvChunk:
    __slots__ = ("version", "flag", "sections")

    def __init__(self, version, flag, sections):
        self.version = version
        self.flag = flag
        self.sections = list(sections)

    def __repr__(self):
        return (f"EnvChunk(version={self.version}, flag={self.flag}, "
                f"sections={[s.tag for s in self.sections]})")

    def tag5_size(self):
        return 16 if self.flag >= 1 else 15

    def section(self, tag):
        for s in self.sections:
            if s.tag == tag:
                return s
        return None

    # ---- typed views over the understood sections -----------------------

    def fog(self):
        """The fog aspect array as `(r, g, b, near, far, c, d)` tuples."""
        s = self.section(TAG_FOG)
        return [_FOG.unpack(r) for r in s.records] if s else []

    def zones(self):
        """The zone list as `(sel(8-tuple), x, y, r_in, r_out)` tuples."""
        s = self.section(TAG_ZONES)
        out = []
        for r in (s.records if s else []):
            v = _ZONE.unpack(r)
            out.append((v[:8], v[8], v[9], v[10], v[11]))
        return out

    def polygons(self):
        """The optional per-region polygons as `(env_index, [(x, y), ...])`."""
        s = self.section(TAG_POLYGONS)
        out = []
        for r in (s.records if s else []):
            m = r[0]
            env_index = _U16.unpack_from(r, 1)[0]
            pts = [struct.unpack_from("<ff", r, 3 + 8 * i) for i in range(m)]
            out.append((env_index, pts))
        return out

    def global_env(self):
        """The 17-byte map-global default environment record, raw."""
        s = self.section(TAG_GLOBAL)
        return s.records[0] if s and s.records else None

    # ---- codec ----------------------------------------------------------

    @classmethod
    def decode(cls, blob):
        if len(blob) < 8 or _HDR.unpack_from(blob, 0)[0] != SIGNATURE:
            raise Undecodable("signature is not an Environment chunk")
        _sig, version, flag = _HDR.unpack_from(blob, 0)
        off = 8
        t5 = 16 if flag >= 1 else 15
        sections = []
        for tag in ORDER:
            if off >= len(blob) or blob[off] != tag:
                if tag in _MANDATORY:
                    raise Undecodable(
                        f"expected mandatory tag {tag} at offset {off}, "
                        f"got {blob[off] if off < len(blob) else 'EOF'}")
                continue
            off += 1
            if tag == TAG_GLOBAL:
                sections.append(Section(tag, [blob[off:off + GLOBAL_SIZE]]))
                off += GLOBAL_SIZE
                continue
            count = _U16.unpack_from(blob, off)[0]
            off += 2
            if tag == TAG_POLYGONS:
                recs = []
                for _ in range(count):
                    m = blob[off]
                    n = 3 + 8 * m
                    recs.append(blob[off:off + n])
                    off += n
                sections.append(Section(tag, recs))
            else:
                size = t5 if tag == 5 else _FIXED[tag]
                recs = [blob[off + i * size:off + (i + 1) * size]
                        for i in range(count)]
                off += count * size
                sections.append(Section(tag, recs))
        if off >= len(blob) or blob[off] != TERMINATOR:
            raise Undecodable(f"terminator missing at offset {off}")
        off += 1
        if off != len(blob):
            raise Undecodable(f"{len(blob) - off} trailing bytes after terminator")
        return cls(version, flag, sections)

    def encode(self):
        out = bytearray(_HDR.pack(SIGNATURE, self.version, self.flag))
        for s in self.sections:
            out.append(s.tag)
            if s.tag == TAG_GLOBAL:
                if len(s.records) != 1 or len(s.records[0]) != GLOBAL_SIZE:
                    raise ValueError("tag8 must hold exactly one 17-byte record")
                out += s.records[0]
                continue
            out += _U16.pack(len(s.records))
            for r in s.records:
                out += r
        out.append(TERMINATOR)
        return bytes(out)
