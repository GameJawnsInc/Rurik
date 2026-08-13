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
       0   10    {u8 a/256, u8 b/256, u32 raw f32, u8 gain 1+d*15/256, u8 e/256,
                 u16 dep ref} -- layout MEASURED, PURPOSE NOT FOUND
       1    6    POST-PROCESS: {u8 BloomAmount, u8 PostProcSaturation,
                 u8 tint strength, u8 B, u8 G, u8 R} -- see below
       2   19    FOG: {u8 r, g, b, u32 near, u32 far, i32, i32}, near<far 349/349
       3    8    DIRECTIONAL LIGHT: two {u8 r, u8 g, u8 b, u8 intensity} pairs,
                 fed to GrLight setters -- see below
       4    2    a bare u16 dep-list index (0xFFFF NULL); PURPOSE NOT FOUND
       5   15 or 16   ONE SKY-LAYER configuration; the WIDTH is chosen by `flag`,
                 and the 16th byte is one more /256 scalar
       6   57    the WATER record -- see below
       7    4    {u8 angle, u8 wrapped angle, u8 /256, u8 x1000/256} -- two angles
                 plus a weight and a magnitude, all weight-blended so none is an
                 id. PURPOSE NOT FOUND (no read site reached)
       8   17    FIXED, no count: the map-GLOBAL default environment --
                 EIGHT u16 selectors (one per aspect array, tag order) plus
                 the SUN ELEVATION byte at +0x10
       9   32    the ZONE list: {u16 sel[8], i32 x, i32 y, u32 r_in, u32 r_out}
      11    5    the tagged-environment table; indexes the zone list
      12   var   OPTIONAL polygons: count * {u8 npoints, u16 envIndex, npoints*(f32,f32)}

    Tag 10 never occurs (its handler slot is NULL). Tags 0-9 and 11 are present
    in all 349 maps; tag 12 in 104.

THE CENTRAL IDEA, because it is what makes the multiplicity make sense. A map
holds SEVERAL environment configurations and blends between them SPATIALLY, not
by time of day. **A configuration is a SELECTOR TUPLE**: eight u16 indices, one
into each aspect array. `tag8` is the map's default tuple; a `tag9` zone is the
same tuple plus a world-space circle `{x, y, r_in, r_out}` that overrides the
default inside its blend band. The clincher: all 73 maps with no zones have every
aspect array at count exactly 1 (MEASURED). The selector-to-array mapping is
forced by the resolver at `0x0071F2F0`, which bounds each slot against its own
array's count and indexes with its own stride (`imul ecx, eax, 0x39` for tag6's
57, and so on) -- and by the corpus, where all 20,936 zone slot reads are in
bounds while rotating the slot-to-array assignment by one puts 3,562 out.
`tag11` and `tag12` are the second level -- each carries an index the client
bounds against the zone-array count (the two `EnvDataImport` asserts, strings
verbatim `tag->index < envArray.Count()` at VA `0x0072032d` and
`data->envIndex < ...` at `0x0072044a`).

TAG6 IS THE WATER RECORD, and this correction is worth stating loudly because a
first pass called it "the main environment record" purely from its size. It is
the parameter block of the animated water surface: its selected record reaches
`MapWater`'s setter as one struct, and the floats are a water shader's --
`+0x05` is the water plane's base height (the ONE float the zone blender refuses
to interpolate, copied from the dominant zone instead), `+0x09` is wave
amplitude scaling a five-sine surface sum, and two (tiling-scale, scroll-speed)
pairs drive texture matrices through `GrTrans`. `+0x00` is a mode enum the loader
VALIDATES -- `cmp eax, 3; ja <abort>` at `0x0071F6F3` then a four-arm jump table,
so a value above 3 aborts the whole import. `+0x02..+0x04` are padding (zero in
865 of 865 records). The two u32s at `+0x2D`/`+0x31` are D3DCOLOR `0xAARRGGBB`.

**THREE OF ITS FLOATS ARE NAMED BY ARENANET, NOT BY US**, which is the strongest
form the evidence takes anywhere in this chunk: the client uploads them to shader
constants it looks up BY NAME, and the name strings are in the image.
`+0x21` is **`waterFresnel`** (string at `0x00A6C430`, bound to the handle the
upload at `0x0070B0F2` uses) and `+0x25` scales an RGB triple into
**`waterSpecularColor`** (string at `0x00A6C474`, upload at `0x0070B134`). Both
are 0..1 in 865/865, and both also act as GATES -- `+0x21 > 0` and `+0x25 != 0`
each promote the water technique, so the only path that reads a field is unlocked
by that same field. `+0x29` is read as `0.5 / value` and installed as the x and y
scale of a projective texture matrix on `GrTrans` slot 3 (`0x0070AD21`).

TAG1 IS THE POST-PROCESS ASPECT, and its six bytes are likewise named by the
client's own 19-entry shader-constant name table at `0xBF7DA8`:
`{u8 BloomAmount, u8 PostProcSaturation, u8 PostProcTintColor.w, u8 B, u8 G,
u8 R}` -- the last three a packed tint colour stored **B, G, R**. Corpus
corroboration that these are the right names rather than plausible ones: byte 1
is 255 (saturation 1.0) in **648 of 741** records, which is what a defaulted
saturation looks like and what a second bloom scalar would not; and byte 2, the
tint strength, is 0 in 571 of 741 -- tint off by default. NOTE the correction:
this module's earlier docstring called bytes 3-4 "a raw u16", and it is not an
index at all, it is two thirds of a packed colour.

TAG3 IS THE DIRECTIONAL LIGHT: two `{u8 r, u8 g, u8 b, u8 intensity}` pairs fed
straight to `GrLight` setters (`0x0067B560`, `0x0067B6A0`), with the direction
set alongside them asserting `GrLight:400 m_type == GR_LIGHT_DIRECTIONAL`.
Colour-ness is forced independently of that: the zone blender reads `+0x50/+0x51/
+0x52` as THREE SEPARATE BYTES, which a u16 id could not survive. This also
REFUTES a standing suspicion -- tag3's u16s are NOT dep-list indices; they are
the low two bytes of a colour.

WHAT IS STILL NOT NAMED, stated so nobody quotes this module for more than it
did: **tag0**, whose ten bytes are fully read out but whose consumer was never
reached (the dispatcher hands its zone index to `0x0071A4C0`, undisassembled);
**tag4**, a bare dep reference with no scalar beside it; and **tag7**, whose four
bytes decode to two angles plus a weight and a magnitude -- a direction and a
distance in shape -- with no read site found. Absence here is a statement about
the ranges searched, which are recorded in
`vault/research/envsound-2026-08-13/`, not a claim that no consumer exists.

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
TAG_POSTPROC = 1                # bloom / saturation / tint -- ArenaNet's names
TAG_FOG = 2
TAG_LIGHT = 3                   # two {rgb, intensity} directional-light pairs
TAG_ZONES = 9
TAG_POLYGONS = 12
TAG_WATER = 6                   # named for what MapWater does with it, not size

#: The eight aspect arrays a selector tuple picks from, in slot order. Forced by
#: the resolver at 0x0071F2F0 (each slot bounded against its own array's count
#: and indexed with that array's stride) and corroborated by the corpus: all
#: 20,936 zone slot reads land in bounds, while rotating this assignment by one
#: puts 3,562 out.
SELECTOR_TAGS = (0, 1, 2, 3, 4, 5, 6, 7)

#: The sun elevation's scaling. The loader multiplies tag8's byte at +0x10 by the
#: f64 at 0xA6EE50 (`fmul` at 0x0071FBD8), which is float32(2*pi)/256 -- a
#: byte-turn. MEASURED against the Stripped terrain chunk's own angle_index,
#: which encodes the SAME authored angle at a different quantisation: 306 of 349
#: maps agree exactly under `round(b * 3.96875)`, 313 within one terrain quantum,
#: and 28 of the 34 that disagree carry terrain byte 127 -- the 45-degree default,
#: i.e. the terrain copy was left unset. Four controls score 0/349.
SUN_TURN = 6.2831854820251465 / 256.0

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

    def postproc(self):
        """The post-process array as
        `(bloom, saturation, tint_strength, (r, g, b))` tuples.

        The record stores the tint as B, G, R; this returns it in the r, g, b
        order every other colour accessor here uses, so a caller never has to
        remember the storage order. Values are raw bytes -- the client's own
        remap for bloom and saturation is `b/256 * 0.98 + 0.008`, which is an
        authoring detail rather than something to bake in here.
        """
        s = self.section(TAG_POSTPROC)
        out = []
        for r in (s.records if s else []):
            out.append((r[0], r[1], r[2], (r[5], r[4], r[3])))
        return out

    def lights(self):
        """The directional-light array as two `((r, g, b), intensity)` pairs
        per record. Which pair is diffuse and which is ambient is NOT FOUND --
        both reach GrLight setters, and the corpus cannot separate them."""
        s = self.section(TAG_LIGHT)
        out = []
        for r in (s.records if s else []):
            out.append((((r[0], r[1], r[2]), r[3]),
                        ((r[4], r[5], r[6]), r[7])))
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

    def default_selectors(self):
        """tag8's eight u16 selectors -- the map's default pick per aspect array.

        Same tuple shape a zone carries, so `zones()[i][0]` and this are
        interchangeable inputs to `resolve()`.
        """
        g = self.global_env()
        return struct.unpack_from("<8H", g, 0) if g else None

    def sun_index(self):
        """tag8's sun-elevation byte, raw (a byte-turn; see SUN_TURN)."""
        g = self.global_env()
        return g[16] if g else None

    def sun_elevation(self):
        """The sun elevation in radians, by the client's own scaling."""
        b = self.sun_index()
        return None if b is None else b * SUN_TURN

    def resolve(self, selectors):
        """`{tag: record-bytes}` for one selector tuple -- a whole environment.

        The tuple is tag8's (the map default) or a zone's. A slot indexing past
        its array is refused rather than clamped: the client bounds-checks every
        one and aborts the import, so an out-of-range slot is a corrupt chunk
        rather than a value to interpret.
        """
        out = {}
        for slot, tag in enumerate(SELECTOR_TAGS):
            s = self.section(tag)
            recs = s.records if s else []
            i = selectors[slot]
            if i >= len(recs):
                raise ValueError(
                    f"selector slot {slot} picks record {i} of tag {tag}, which "
                    f"holds {len(recs)}; the client bounds-checks this and aborts")
            out[tag] = recs[i]
        return out

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
