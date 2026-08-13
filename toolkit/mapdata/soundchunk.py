r"""The Sound chunk: read and write `0x10000012`.

The map's ambient-sound layer, and the second of the two chunks rung E10 could
only BORROW. Until 2026-08-13 no tool in this tree could read a byte of it:
`stripbuild` carried Pre-Searing's 89 bytes verbatim and the map wore
Pre-Searing's birds and wind because we could not author our own. This module
is the whole chunk, decoded to typed fields and re-encoded byte-identically.

    blob = ...                        # chunk 0x10000012 out of a map's partner row
    sc   = SoundChunk.decode(blob)
    assert sc.encode() == blob        # 349 of 349 retail maps

WHERE THE LAYOUT COMES FROM. The framing was derived from the 349-map corpus
(every payload is `17 + 24k` bytes, MEASURED 349/349) and then CORROBORATED
against the client's own loader at VA `0x00712EE0 -> 0x0076afc0`, which settled
every field the bytes left ambiguous. Each claim below is labelled.

    u32 'msnd'  (0x6D736E64)                       MEASURED, the client chunk table
    u32 version 2                                  MEASURED (bytes 5..7 == 0)
    u8  0                                           a tag byte; stage-1 matcher
                                                    `0x0076b274 cmp byte,0` reads it
    u16 idx_a   u16 idx_b                           two dep-list indices, 0xFFFF=none
    u8  1                                           a tag byte; stage-2 matcher
    u16 k       (record count)                      MEASURED u16 @14 (0x0076b2a1)
    k * record, each 24 bytes:
        u16 dep_a   u16 dep_b                       dep-list indices, 0xFFFF=none
        i32 x       i32 y                           world position, in the map rect
        u32 r_lo    u32 r_hi    u32 r_mid           attenuation radii (SQUARED at
                                                    load, `fmul st,st` 0x0076b42a..)
    u8  0xFF                                        terminator, last byte of chunk

WHAT THE FIELDS MEAN, and how sure we are.

  * `idx_a`/`idx_b` are the map's DEFAULT ambience -- two indices into the sibling
    Dependencies chunk `0x11000012`, resolved by the same routine `0x0076b190`
    the records use and stored at container scope before any record (MEASURED).
    0xFFFF means none: the 20 maps whose value is (0xFFFF, 0xFFFF) are EXACTLY the
    20 with no Dependencies chunk (MEASURED, both directions).
  * A record is a POSITIONED EMITTER. `(x, y)` lands inside the map's own Map
    Parameters rect in 318 of 318 records (MEASURED; a +/-1 or +/-2 byte shift
    of the read collapses that to 0). No z: emitters are 2-D.
  * The three radii are stored on disk in the order `lo, hi, mid` but the client
    enforces `lo <= mid <= hi` at load (`0x0076b2ed`) and SQUARES each for a
    sqrt-free distance compare (INFERRED: min-audible / max-audible / a fade
    knee, from the ordering and the squaring; the corpus cannot force
    radius-vs-anything, so `r_*` are named for their SHAPE not their use).
  * `dep_a`/`dep_b` name up to two sounds per emitter, again 0xFFFF for none.
    The referenced file is NOT always audio -- textures and models appear as
    often as `ffna8` sound descriptors -- and the loader does NO magic dispatch
    (`0x0076b190` just bounds-checks and addrefs), so what a texture emitter
    MEANS is a consumer-side question this module does not answer.

THE SOUNDS ARE ONE HOP DEEPER. A dep index resolves to an `ffna8` sound
descriptor, whose OWN chunk-1 is a dependency list (raw MPEG / `AMP` / nested
`ffna8`) -- the audio bytes and the per-sound volume/loop parameters live there,
not here. This chunk PLACES sounds; it does not contain them.

NOTHING DECLARED IS STORED. `k` is re-derived from the record list on encode, so
349 byte-identical re-encodes are 349 assertions about the derivation rather than
349 replays of a number. `test_soundchunk.py` builds the memcpy saboteur that
this catches.
"""

import struct

SIGNATURE = 0x6D736E64          # 'msnd' little-endian
VERSION = 2
TAG_HEADER = 0                  # the u8 before the index pair
TAG_RECORDS = 1                 # the u8 before the record count
TERMINATOR = 0xFF
NONE = 0xFFFF                   # a dep index meaning "no reference"

RECORD_SIZE = 24
HEADER_SIZE = 16                # magic(4) ver(4) tag0(1) idx_a(2) idx_b(2) tag1(1) k(2)

_HDR = struct.Struct("<IIBHHBH")        # magic, ver, tag0, idx_a, idx_b, tag1, k
_REC = struct.Struct("<HHiiIII")        # dep_a, dep_b, x, y, r_lo, r_hi, r_mid


class Undecodable(ValueError):
    """The bytes are not a Sound chunk this module understands."""


class Emitter:
    """One positioned ambient emitter -- a record of the Sound chunk."""

    __slots__ = ("dep_a", "dep_b", "x", "y", "r_lo", "r_hi", "r_mid")

    def __init__(self, dep_a, dep_b, x, y, r_lo, r_hi, r_mid):
        self.dep_a = dep_a
        self.dep_b = dep_b
        self.x = x
        self.y = y
        self.r_lo = r_lo
        self.r_hi = r_hi
        self.r_mid = r_mid

    def __repr__(self):
        return (f"Emitter(dep_a={self.dep_a}, dep_b={self.dep_b}, "
                f"x={self.x}, y={self.y}, "
                f"r_lo={self.r_lo}, r_hi={self.r_hi}, r_mid={self.r_mid})")

    def __eq__(self, other):
        return isinstance(other, Emitter) and self.pack() == other.pack()

    @classmethod
    def unpack(cls, buf, off=0):
        return cls(*_REC.unpack_from(buf, off))

    def pack(self):
        return _REC.pack(self.dep_a, self.dep_b, self.x, self.y,
                         self.r_lo, self.r_hi, self.r_mid)


class SoundChunk:
    """The whole `0x10000012` payload: a default ambience pair and k emitters."""

    __slots__ = ("version", "idx_a", "idx_b", "emitters")

    def __init__(self, version, idx_a, idx_b, emitters):
        self.version = version
        self.idx_a = idx_a
        self.idx_b = idx_b
        self.emitters = list(emitters)

    def __repr__(self):
        return (f"SoundChunk(version={self.version}, idx_a={self.idx_a}, "
                f"idx_b={self.idx_b}, emitters={len(self.emitters)})")

    @classmethod
    def decode(cls, blob):
        if len(blob) < HEADER_SIZE + 1:
            raise Undecodable(f"too short for a Sound chunk: {len(blob)} bytes")
        magic, version, tag0, idx_a, idx_b, tag1, k = _HDR.unpack_from(blob, 0)
        if magic != SIGNATURE:
            raise Undecodable(f"signature {magic:#010x}, want {SIGNATURE:#010x}")
        if tag0 != TAG_HEADER or tag1 != TAG_RECORDS:
            raise Undecodable(
                f"tag bytes ({tag0}, {tag1}), want ({TAG_HEADER}, {TAG_RECORDS})")
        want = HEADER_SIZE + RECORD_SIZE * k + 1
        if len(blob) != want:
            raise Undecodable(
                f"size {len(blob)} != 17 + 24*{k} = {want}; declared k disagrees "
                f"with the byte length")
        emitters = [Emitter.unpack(blob, HEADER_SIZE + i * RECORD_SIZE)
                    for i in range(k)]
        if blob[-1] != TERMINATOR:
            raise Undecodable(f"terminator {blob[-1]:#x}, want {TERMINATOR:#x}")
        return cls(version, idx_a, idx_b, emitters)

    def encode(self):
        out = bytearray(_HDR.pack(SIGNATURE, self.version, TAG_HEADER,
                                  self.idx_a, self.idx_b, TAG_RECORDS,
                                  len(self.emitters)))
        for e in self.emitters:
            out += e.pack()
        out.append(TERMINATOR)
        return bytes(out)


def empty(version=VERSION):
    """A silent Sound chunk: no default ambience, no emitters. 17 bytes.

    Byte-identical to the 20 retail maps that carry a deliberately empty chunk
    (MEASURED). This is what an authored map wants when it wants no sound at all,
    rather than borrowing Pre-Searing's.
    """
    return SoundChunk(version, NONE, NONE, [])
