"""The OTHER terrain chunk: read and write a map's STRIPPED terrain, `0x10000002`.

`terrain.py` owns the Bloated chunk `0x20000002` and refuses this one loudly,
because it is a different encoding rather than a re-framing. This module is that
encoding. It matters because of what FINDINGS 35 and 36 measured: the retail
client compiles a map from its Stripped stream, and it compiles the stream WE
supply. Until this codec existed we could hand the compiler somebody else's
terrain and not our own.

    blob = ...                        # chunk 0x10000002 out of a map's partner row
    st   = StrippedTerrain.decode(blob)
    assert st.encode() == blob        # 349 of 349 retail maps
    assert st.heights == Terrain.decode(bloated).heights     # the real check

WHERE THE LAYOUT COMES FROM. All of it is SOURCE-CODE, read out of build 38797,
and then every claim was re-measured against the archive:

  * `s_chunkInfo[0x02].bloat = 0x00711EC0` calls the stage converter at
    **0x00759550**, whose two asserts name `TrnDataBloat.cpp:730/731`
    (`!stripDataLength || stripData`, `buffer`). It drives an **eleven-entry
    pipeline table at 0x00A74958** -- {fn, f32 cost} -- exactly the shape
    FINDINGS 34 found for the Path converter's seven.
  * Record headers come from `0x0073E410` (read) and `0x0073E580` (write). At
    **stage 1 a record header is ONE byte, the tag**; at stage 0 or 2 it is the
    familiar `{u8 tag, u32 size}`. That is the same split `pathchunk.StrippedPath`
    already found on the Path chunk, arrived at from the other side.
  * The bit reader is `TrnBitStore.h` -- ctor 0x00758920, `Read` 0x007593F0,
    asserts at lines 52 (`bitCount < 8 * sizeof(dword)`) and 128 (`bitCount`).
  * The height codec is `TrnCodecHeight.cpp` -- 0x00762B30 down to the per-block
    0x00762EA0 and the sixteen-sample 0x00762CB0 -- with the canonical Huffman
    reader at 0x00764AC0/0x00764C40/0x00764E00.

THE LAYOUT. Nine records, in the order the pipeline demands them; there is no
dispatch loop, so an out-of-order tag is a refusal rather than a resync.

    u32 signature 0x87821134            \
    u8  version 0x11                    / stage 0, 0x00759380
    u8  0    u32 packed, u8 angle, u16 texWord, u8 f12, u8 f16
    u8  1    the bit-coded height field           (below)
    u8  2    dimX*dimY bytes, one tile index per cell, VERBATIM
    u8  4    u8 n; u3 w; n entries of w bits; byte-align
    u8  5    the same shape
    u8  3    dimX*dimY/4 bytes, VERBATIM
   [u8  7    per 32x32 tile: {u32 k, u8 payload[k], u8 tail[128]}]  optional
   [u8  3    17 bytes, VERBATIM]                                    optional
    u8  255

**Tag 9 is not here, and that is the finding this file exists beside.** The
Bloated chunk's 65,536-byte-per-map lightmap is not stored in the Stripped stream
at all: pipeline stage 7 (0x00758AD0) reads NOTHING from the cursor and bakes it
from tag 0's sun elevation, calling 0x005BC0F0/0x005BC4F0 (sin/cos) to build
`(f(t), 0, g(t))` and handing that to 0x0075CC30 with the height field. FINDINGS
19 fitted `255 * max(0, N.L)` to tag 9 and got a median Pearson r of 0.887 over
345 maps and an azimuth on the +x axis with no y component -- that fit was
measuring this generator. The client's own `TrnTexIntensity:342 lightDir.y == 0`
is the same statement from the third side.

TAG 0's SEVEN FIELDS, from nine stored bytes. Every one of these was checked
against the Bloated chunk's own tag 0, which a different subsystem wrote:

    packed & 0xC0     == 0x80 on 349/349, and the client REFUSES anything else
    packed & 0x3F     chunkDistance / 3072.0 -- so 8 gives the corpus's 24576.0
    byte 1            the cell pitch, and the client requires it to EQUAL 96.0
                      (`fucompp` against the f32 at 0x0094DE38). It is the only
                      place in either stream where 96.0 is written down; every
                      other appearance of the pitch, including `terrain.py`'s
                      CELL_PITCH and the flood grid's divisor, is a compiled-in
                      constant.
    byte 2, byte 3    dimY/32 - 1 and dimX/32 - 1. **The axes are stored y,x**
                      and the record emits them x,y; reading them in file order
                      is a transposition that survives every square map.
    angle             f32(b * 282.74334716796875 / 45720.0), in DOUBLE, then
                      rounded once. See the correction below.
    f12, f16          f32(2*v / 255.0), in double. So the reachable set is 256
                      values and `Terrain.tex_f12`'s stored float is one of them.

THE HEIGHT CODEC. Per 32x32 terrain tile, in the same tile-row-major order
`Terrain.index` uses, and inside each tile a raster of 8x8 sub-blocks of 4x4
samples:

  * a block header of 40 bits -- `s16 dcBase`, `u4 dcBits-1`, `s16 escBase`,
    `u4 escBits-1` -- which is five bytes, so the byte-align that follows it is
    already satisfied and the Huffman table always starts on a byte.
  * a canonical Huffman table over 1024 symbols: `u8 w-1`, then eighteen counts
    of `w` bits (one per code length 1..18), then one 10-bit symbol per code in
    canonical order. 18 is the client's own `maxLength` argument and 10 is
    `bitLength(1023)`.
  * 64 sub-blocks. Coefficient 0 is `dcBase + u<dcBits>`; the other fifteen are
    Huffman symbols read as `symbol - 512`, with symbol **1023 escaping** to
    `escBase + u<escBits>`.
  * the sixteen coefficients are a 4x4 integer Haar-like transform, inverted
    columns-then-rows by `(a,b,c,d) -> (a-b-c, c+a-b, a+b-d, d+a+b)`, and the
    result is written as float32 at `out[r*32 + c]`.

WHAT IS RECONSTRUCTED AND WHAT IS CARRIED, because a round-trip over carried
bytes compares a value with itself. **Every coding parameter in the file is
re-derived on encode except one**, and each was MEASURED to be derivable rather
than assumed:

  RE-DERIVED -- the encoder computes these and never stores what it decoded:
    dcBase        == min(the block's 64 DC coefficients)      187/187 blocks
    escBase       == min(the block's escaped coefficients)     66/66 blocks
    dcBits        == max(bitLength(dc - dcBase), 1)           187/187
    escBits       == max(bitLength(esc - escBase), 1)          66/66
    w (table)     == max(bitLength(max count), 1)             187/187
    w (tags 4/5)  == max(bitLength(max entry), 1)               6/6 records
    the symbol SET == exactly the symbols the block uses      187/187
    every byte-align pad                                  zero in 187/187
    every record size, every block count, every count field

  Those counts are a census over three maps. The CORPUS asserts the same thing
  everywhere and more strongly, because `decode()` RAISES on a disagreement
  rather than preferring the stored value: all 349 maps decode, so no block in
  the archive contradicts any row above. That is why the refusals are in the
  decoder and not in the test.

  CARRIED, and it is one thing: **which code length each symbol gets** -- the
  `counts` array and the symbol ORDER within it. That is ArenaNet's frequency
  model, it is not recoverable from the samples, and inventing a Huffman
  construction to replace it would be guessing. It is 22 of 187 blocks whose
  symbol list is not merely sorted, so the order is load-bearing.

  Plus the three records the FORMAT stores raw in both streams -- tags 2, 3 and
  the optional second tag 3. Those are carried because they are carried; there is
  no encoding to understand. `encode()` reports the split so nobody has to guess
  which half a green round-trip is about.

  Tag 7 is **decoded, not carried**: it goes through `terrain.ShadowBlock`, which
  regenerates the payload from a 272x272 bitmap and DERIVES the 128-byte tail, so
  a stored tail its own bitmap disproves is a refusal here too.

A CORRECTION TO `terrain.py`, and it is the client's own arithmetic. That file
records the sun angle as landing "within 1 ULP of `b*pi/508`" and says the best
formulation it found reproduces 53 of 55 stored bit patterns and 347 of 349 maps.
The client does not compute `b*pi/508`. It computes

    (float)((double)b * 282.74334716796875 / 45720.0)

where 282.74334716796875 is `(double)(float)(90*pi)` -- a float32 constant
promoted -- and 45720 is 508*90. The two differ in the last place because the
first rounds 90pi to float32 before dividing. `ANGLE_TABLE` below is that
expression, and it reproduces the Bloated chunk's stored float on **349 of 349
maps**, which is what retires the 1-ULP caveat. `terrain.py`'s warning that an
encoder must never recompute the angle from `b` stands and is now unnecessary
for this path: here `b` IS the stored form.

TRAPS.

  * **The Stripped header is FIVE bytes, not eight.** `u32` signature then a
    `u8` version -- the Bloated chunk's is `u32` + `u32`. Reading eight puts the
    first record header three bytes late, and `terrain.py`'s own docstring got
    this wrong ("signature, then u16 17, then u16 0x6088"): 0x6088 is not a
    field, it is the first two bytes of tag 0's body.
  * **Tag 0 stores dimY before dimX.** Every square map agrees under either
    reading; 416x512 does not.
  * **The two axis counts are `dim/32 - 1`**, so the largest map a Stripped
    chunk can name is 8192x8192 and the smallest is 32x32.
  * The client's post-decode pass calls 0x007630F0 then 0x00763060 on the height
    array -- an untile followed by the matching retile, over a scratch buffer it
    then frees. The two routines are mirror images and their composition is the
    identity; the decoded array is already in the Bloated chunk's tiled order.
    Do not read that pair as evidence of a layout change, and do not reproduce
    it.
  * The client reads tag 2 and tag 3 with **no bounds check at all**
    (0x00763030 copies `dimX*dimY` bytes from the cursor whatever remains). We
    refuse instead, which is the right way round.

SCOPE. This module produces and consumes the Stripped chunk's `bytes`. It does
not bloat -- generating tag 9's lightmap and the Bloated framing is
`terrain.Terrain`'s side of the fence and the client's job in the E3 path. It
opens no file.

    python toolkit/mapdata/strippedterrain.py                    # Kamadan
    python toolkit/mapdata/strippedterrain.py --row 46196
    python toolkit/mapdata/strippedterrain.py --row 7982 --records
"""

import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archive import (Archive, ffna_chunks, file_id_table,  # noqa: E402
                     DEFAULT_DAT)
import terrain  # noqa: E402  -- ShadowBlock, the tag/dims constants, the gates

STRIPPED_TERRAIN_CHUNK = terrain.STRIPPED_TERRAIN_CHUNK   # 0x10000002
SIGNATURE = terrain.SIGNATURE                             # 0x87821134
VERSION = terrain.VERSION                                 # 17

HEADER = struct.Struct("<IB")          # 5 bytes. THE BLOATED CHUNK'S IS 8.
CHUNK_SIZE = terrain.CHUNK_SIZE        # 32
CHUNK_PITCH = terrain.CHUNK_PITCH      # 3072.0
CELL_PITCH = terrain.CELL_PITCH        # 96.0
SHADOW_TAIL = terrain.SHADOW_TAIL      # 128

TAG_DIMS = terrain.TAG_DIMS            # 0
TAG_HEIGHT = terrain.TAG_HEIGHT        # 1
TAG_TILE = terrain.TAG_TILE            # 2
TAG_BITS = terrain.TAG_BITS            # 3
TAG_TABLE_A = terrain.TAG_TABLE_A      # 4
TAG_TABLE_B = terrain.TAG_TABLE_B      # 5
TAG_SHADOW = terrain.TAG_SHADOW        # 7
TERMINATOR = terrain.TERMINATOR        # 255

# The order the eleven-stage pipeline demands. Tag 9 is absent by construction --
# stage 7 generates it -- and the two optional records may each be missing.
REQUIRED_SEQUENCE = (TAG_DIMS, TAG_HEIGHT, TAG_TILE, TAG_TABLE_A, TAG_TABLE_B,
                     TAG_BITS)

DIMS_MARKER = 0x80                     # packed & 0xC0, refused otherwise
DIMS_MARKER_MASK = 0xC0
DIMS_DISTANCE_MASK = 0x3F
STORED_PITCH = 96                      # byte 1, and the client compares == 96.0

# 0x00A749D0 / 0x00A749D8, both f64 in the image. The first is (double)(float)90pi.
ANGLE_NUM = 282.74334716796875
ANGLE_DEN = 45720.0
# 0x009495A8, f64. tex_f12 and tex_f16 are 2*v/255 in double, rounded once.
TEX_DEN = 255.0

HUFF_SYMBOLS = 0x400                   # 0x00764AC0's first argument
HUFF_MAXLEN = 0x12                     # its second: 18 code lengths
HUFF_ESCAPE = HUFF_SYMBOLS - 1         # 1023, compared at 0x00762D3A
HUFF_BIAS = HUFF_SYMBOLS // 2          # `add eax, 0xfffffe00`
HUFF_COUNT_WIDTH_BITS = 8              # `u8 w-1` ahead of the counts
SYMBOL_BITS = (HUFF_SYMBOLS - 1).bit_length()      # 0x0046E110 + 1 == 10

SUB = 4                                # the transform is 4x4
SUB_PER_TILE = CHUNK_SIZE // SUB       # 8 sub-blocks per axis
TILE_SAMPLES = CHUNK_SIZE * CHUNK_SIZE  # 1024
DC_BITS_BITS = 4                       # `u4 dcBits-1`
BASE_BITS = 16                         # `s16 dcBase`
TABLE_WIDTH_BITS = 3                   # tags 4/5: `u3 w`
TABLE_COUNT_BITS = 8                   # tags 4/5: `u8 n`
TAG3B_SIZE = 17                        # copied verbatim by stage 9


def _angle_from_index(b):
    """The client's own expression at 0x00758D99, evaluated its way."""
    return struct.unpack("<f", struct.pack("<f", b * ANGLE_NUM / ANGLE_DEN))[0]


def _tex_from_index(v):
    """0x00758E4C: `2*v / 255.0` in double, stored as f32."""
    return struct.unpack("<f", struct.pack("<f", 2.0 * v / TEX_DEN))[0]


ANGLE_TABLE = tuple(_angle_from_index(b) for b in range(256))
TEX_TABLE = tuple(_tex_from_index(v) for v in range(256))


class Undecodable(ValueError):
    """Bytes this codec will not guess past."""


class BitReader:
    """MSB-first bit reader over a byte string, from `start`.

    `TrnBitStore` keeps a 32-bit sliding window and pre-reads four bytes; this
    keeps a bit offset instead. The two agree on every in-bounds read -- the
    window is an implementation of the same MSB-first order -- and they agree on
    the byte advance, which `consumed()` computes the way 0x00762C80 does.
    Where they differ is off the end: the client walks off a short buffer
    quietly, and this raises.
    """

    __slots__ = ("buf", "start", "pos", "limit")

    def __init__(self, buf, start=0, end=None):
        self.buf = buf
        self.start = start
        self.pos = 0
        self.limit = (len(buf) if end is None else end) - start

    def take(self, n):
        if n == 0:
            return 0
        if n >= 32:
            # TrnBitStore.h:52 asserts bitCount < 8 * sizeof(dword). No caller
            # in the pipeline asks for more than 16.
            raise Undecodable(f"bit read of {n} is not below 32")
        byte = self.start + (self.pos >> 3)
        need = (self.pos & 7) + n
        span = (need + 7) >> 3
        if byte + span > self.start + self.limit:
            raise Undecodable(
                f"bit stream wants {n} bits at bit {self.pos} but the record "
                f"has {self.limit} bytes")
        word = int.from_bytes(self.buf[byte:byte + span], "big")
        self.pos += n
        return (word >> (span * 8 - need)) & ((1 << n) - 1)

    def align(self):
        """Skip to the next byte boundary, refusing a non-zero pad.

        MEASURED: the pad is zero in 187 of 187 sampled blocks, so an encoder
        that writes zeros reproduces ArenaNet's bytes. Refusing here is what
        makes that a claim the archive could refute rather than a convention.
        """
        k = -self.pos & 7
        if k and self.take(k):
            raise Undecodable(f"non-zero alignment pad of {k} bits at "
                              f"bit {self.pos - k}")

    def consumed(self):
        """Whole bytes consumed, as 0x00762C80 computes it: `(bits + 7) >> 3`."""
        return (self.pos + 7) >> 3


class BitWriter:
    """MSB-first bit writer. The shipping client has no encoder to copy.

    `asserts.py --modules` lists `TrnDataImport.cpp` and no `TrnDataStrip`, so
    the strip direction lives in ArenaNet's offline tool and not in the image.
    Every choice this class could get wrong is therefore pinned by the
    round-trip rather than by a disassembly.
    """

    __slots__ = ("out", "acc", "nbits")

    def __init__(self):
        self.out = bytearray()
        self.acc = 0
        self.nbits = 0

    def put(self, value, n):
        if n == 0:
            return
        if value >> n:
            raise ValueError(f"value {value} does not fit in {n} bits")
        self.acc = (self.acc << n) | value
        self.nbits += n
        while self.nbits >= 8:
            self.nbits -= 8
            self.out.append((self.acc >> self.nbits) & 0xFF)
            self.acc &= (1 << self.nbits) - 1

    def align(self):
        if self.nbits:
            self.put(0, 8 - self.nbits)

    def bytes(self):
        if self.nbits:
            raise ValueError("bit writer is not byte aligned")
        return bytes(self.out)


class HuffmanTable:
    """One block's canonical Huffman code, over symbols 0..1023.

    The model is the file's own two fields -- `counts[L]`, how many symbols take
    each code length, and `symbols`, those symbols in canonical order. Together
    they are an assignment of code lengths to symbols and nothing else: the
    codes themselves, the count field's width and the symbol field's width are
    all re-derived.

    **This is the one carried thing in the height codec**, and deliberately so.
    It is ArenaNet's frequency model; the samples cannot recover it, and a
    Huffman construction of our own would reproduce their bytes only by
    coincidence. 22 of 187 sampled blocks have a symbol list that is not sorted,
    so the order carries information and cannot be normalised away.
    """

    __slots__ = ("counts", "symbols", "_first", "_limit", "_base", "_code")

    def __init__(self, counts, symbols):
        if len(counts) != HUFF_MAXLEN + 1:
            raise ValueError(f"{len(counts)} counts for {HUFF_MAXLEN} lengths")
        if sum(counts) != len(symbols):
            raise ValueError(f"counts sum to {sum(counts)} but {len(symbols)} "
                             f"symbols were given")
        self.counts = list(counts)
        self.symbols = list(symbols)
        self._build()

    def _build(self):
        self._first = [0] * (HUFF_MAXLEN + 1)
        self._limit = [-1] * (HUFF_MAXLEN + 1)
        self._base = [0] * (HUFF_MAXLEN + 1)
        self._code = {}
        code = 0
        idx = 0
        for length in range(1, HUFF_MAXLEN + 1):
            self._first[length] = code
            self._base[length] = idx
            n = self.counts[length]
            if n:
                self._limit[length] = code + n - 1
                for k in range(n):
                    self._code[self.symbols[idx + k]] = (code + k, length)
            code += n
            idx += n
            if code > (1 << length):
                # Over-subscribed: more codes of this length than the length can
                # name. The client's decoder would walk off the end of its limit
                # table instead of saying so.
                raise Undecodable(
                    f"huffman code lengths are over-subscribed at length "
                    f"{length}: {code} codes need more than {1 << length}")
            code <<= 1

    @property
    def count_width(self):
        """`w`, re-derived. MEASURED equal to the stored value on 187/187."""
        return max(max(self.counts).bit_length(), 1)

    @classmethod
    def read(cls, br):
        width = br.take(HUFF_COUNT_WIDTH_BITS) + 1
        counts = [0] * (HUFF_MAXLEN + 1)
        for length in range(1, HUFF_MAXLEN + 1):
            counts[length] = br.take(width)
        total = sum(counts)
        if total > HUFF_SYMBOLS:
            raise Undecodable(f"huffman table declares {total} symbols, more "
                              f"than the {HUFF_SYMBOLS}-symbol alphabet")
        symbols = [br.take(SYMBOL_BITS) for _ in range(total)]
        if len(set(symbols)) != total:
            raise Undecodable("huffman symbol list repeats a symbol")
        table = cls(counts, symbols)
        if table.count_width != width:
            raise Undecodable(
                f"huffman count field is {width} bits but its own counts need "
                f"{table.count_width}; the encoder here re-derives it")
        return table

    def write(self, bw):
        width = self.count_width
        bw.put(width - 1, HUFF_COUNT_WIDTH_BITS)
        for length in range(1, HUFF_MAXLEN + 1):
            bw.put(self.counts[length], width)
        for sym in self.symbols:
            bw.put(sym, SYMBOL_BITS)

    def decode(self, br):
        value = 0
        for length in range(1, HUFF_MAXLEN + 1):
            value = (value << 1) | br.take(1)
            if self.counts[length] and value <= self._limit[length]:
                return self.symbols[self._base[length]
                                    + value - self._first[length]]
        raise Undecodable("huffman code ran past 18 bits without terminating")

    def encode(self, bw, symbol):
        try:
            code, length = self._code[symbol]
        except KeyError:
            if symbol == HUFF_ESCAPE:
                raise ValueError(
                    "this block needs the escape symbol and its table has no "
                    "code for it -- the samples were changed after the table "
                    "was built; rebuild it with HeightBlock.from_samples")
            raise ValueError(f"symbol {symbol} is not in this block's table")
        bw.put(code, length)

    @classmethod
    def for_frequencies(cls, freq):
        """A LEGAL table for these symbol counts. **Not ArenaNet's construction.**

        Nothing in the image builds one of these -- the strip direction is in
        their offline tool -- so this is ours, and it exists for the authoring
        direction rather than for the round trip. `decode` + `encode` never call
        it: they carry the table they read, precisely so that a green round trip
        is not secretly a claim that our construction matches theirs.

        Standard Huffman by frequency, with a flat fixed-length fallback when a
        code would exceed the format's 18-bit ceiling. Ties are broken by symbol
        so the output is deterministic. Within a length, symbols are emitted in
        increasing order, which is the canonical order the reader assumes.
        """
        symbols = sorted(freq)
        if not symbols:
            raise ValueError("a height block always codes at least one symbol")
        if len(symbols) == 1:
            return cls([0, 1] + [0] * (HUFF_MAXLEN - 1), symbols)
        import heapq
        heap = [(max(freq[s], 1), i, {s}) for i, s in enumerate(symbols)]
        heapq.heapify(heap)
        nxt = len(symbols)
        lengths = {s: 0 for s in symbols}
        while len(heap) > 1:
            w1, _, a = heapq.heappop(heap)
            w2, _, b = heapq.heappop(heap)
            for s in a | b:
                lengths[s] += 1
            heapq.heappush(heap, (w1 + w2, nxt, a | b))
            nxt += 1
        if max(lengths.values()) > HUFF_MAXLEN:
            flat = max((len(symbols) - 1).bit_length(), 1)
            if flat > HUFF_MAXLEN:
                raise ValueError(f"{len(symbols)} symbols cannot be coded in "
                                 f"{HUFF_MAXLEN} bits")
            lengths = {s: flat for s in symbols}
        counts = [0] * (HUFF_MAXLEN + 1)
        for length in lengths.values():
            counts[length] += 1
        order = sorted(symbols, key=lambda s: (lengths[s], s))
        return cls(counts, order)

    def __contains__(self, symbol):
        return symbol in self._code

    def __len__(self):
        return len(self.symbols)

    def __eq__(self, other):
        return (isinstance(other, HuffmanTable)
                and self.counts == other.counts
                and self.symbols == other.symbols)

    def __repr__(self):
        used = [length for length in range(1, HUFF_MAXLEN + 1)
                if self.counts[length]]
        return (f"<HuffmanTable {len(self.symbols)} symbols, lengths "
                f"{used[0] if used else '-'}..{used[-1] if used else '-'}>")


def _inverse4(a, b, c, d):
    """0x00762DB0 and 0x00762E00, the same four lines run twice."""
    t = a - b
    s = a + b
    return t - c, c + t, s - d, d + s


def _forward4(w, x, y, z):
    """The exact inverse of `_inverse4`. The client has no encoder; this is ours.

    `w + x == 2(a-b)` and `y + z == 2(a+b)`, so the sum of all four is `4a` and
    every division below is exact for anything `_inverse4` produced. It is NOT
    exact for arbitrary input -- `_inverse4`'s matrix has determinant 8, so its
    image is an index-8 sublattice of Z^4 and the four-vector must satisfy
    `w == x (mod 2)`, `y == z (mod 2)` and `w + x == y + z (mod 4)`.

    Refusing rather than truncating is the point. A silent floor here would move
    a height by a fraction of a unit and still round-trip most of a map, which
    is exactly the failure a byte-identity headline cannot see.
    """
    lo = w + x                       # 2(a - b)
    hi = y + z                       # 2(a + b)
    if (lo + hi) & 3 or (hi - lo) & 3 or (x - w) & 1 or (z - y) & 1:
        raise ValueError(
            f"({w}, {x}, {y}, {z}) is not in the image of the transform: it "
            f"needs w==x and y==z mod 2 and w+x==y+z mod 4")
    return (lo + hi) >> 2, (hi - lo) >> 2, (x - w) >> 1, (z - y) >> 1


def _forward4_near(w, x, y, z):
    """The nearest coefficients when the samples are not on the lattice.

    Used only by the AUTHORING path. It is an identity on anything `_inverse4`
    produced -- the divisions are exact there and rounding an integer changes
    nothing -- so a representable field is never disturbed.
    """
    def _round(num, den):
        return -((-num + den // 2) // den) if num < 0 else (num + den // 2) // den
    return (_round(w + x + y + z, 4), _round(y + z - w - x, 4),
            _round(x - w, 2), _round(z - y, 2))


def snap_block(samples):
    """Move 1024 integer samples onto the nearest representable height field.

    The transform is 8-to-1 in volume per four-vector and is applied along both
    axes, so the reachable sublattice of Z^16 has index 8^8 within each 4x4
    sub-block. A field authored freely -- out of Blender, say -- is essentially
    never on it. This projects, and returns `(snapped, worst)` so the caller can
    state the error rather than discover it in-game.

    MEASURED against the lattice's own geometry: 16,777,216 ^ (1/16) is about
    2.8 units of cell volume per axis, and the observed worst case on random
    fields is a few world units against a 96-unit cell pitch. It is a real
    quantisation and it is small; both halves of that belong in the record.
    """
    out = list(samples)
    for by in range(SUB_PER_TILE):
        for bx in range(SUB_PER_TILE):
            fin = [out[(by * SUB + r) * CHUNK_SIZE + bx * SUB + c]
                   for r in range(SUB) for c in range(SUB)]
            mid = [0] * 16
            for r in range(SUB):
                mid[SUB * r:SUB * r + SUB] = _forward4_near(
                    *fin[SUB * r:SUB * r + SUB])
            co = [0] * 16
            for i in range(SUB):
                (co[i], co[i + 4], co[i + 8],
                 co[i + 12]) = _forward4_near(mid[i], mid[i + 4], mid[i + 8],
                                              mid[i + 12])
            for i in range(SUB):
                (mid[i], mid[i + 4], mid[i + 8],
                 mid[i + 12]) = _inverse4(co[i], co[i + 4], co[i + 8],
                                          co[i + 12])
            for r in range(SUB):
                row = _inverse4(*mid[SUB * r:SUB * r + SUB])
                off = (by * SUB + r) * CHUNK_SIZE + bx * SUB
                out[off:off + SUB] = row
    worst = max((abs(a - b) for a, b in zip(out, samples)), default=0)
    return out, worst


class HeightBlock:
    """One 32x32 terrain tile of the height field: 1024 integer samples.

    `samples` is the authority and is stored row-major within the tile, which is
    the order `Terrain.index` lands on. Every coding parameter the file carries
    -- both bases, both bit widths, the symbol set, the count width, the pads --
    is re-derived from `samples` on encode; only `table` is carried, and its
    docstring says why.
    """

    __slots__ = ("samples", "table")

    def __init__(self, samples, table):
        self.samples = list(samples)
        if len(self.samples) != TILE_SAMPLES:
            raise ValueError(f"{len(self.samples)} samples for a "
                             f"{CHUNK_SIZE}x{CHUNK_SIZE} tile")
        self.table = table

    # -- the 4x4 sub-blocks ------------------------------------------------

    def _coefficients(self):
        """`samples` back to the 64 sub-blocks of 16 coefficients."""
        out = []
        for by in range(SUB_PER_TILE):
            for bx in range(SUB_PER_TILE):
                fin = [self.samples[(by * SUB + r) * CHUNK_SIZE + bx * SUB + c]
                       for r in range(SUB) for c in range(SUB)]
                mid = [0] * 16
                for r in range(SUB):
                    mid[SUB * r:SUB * r + SUB] = _forward4(*fin[SUB * r:
                                                                SUB * r + SUB])
                co = [0] * 16
                for i in range(SUB):
                    (co[i], co[i + 4], co[i + 8],
                     co[i + 12]) = _forward4(mid[i], mid[i + 4], mid[i + 8],
                                             mid[i + 12])
                out.append(co)
        return out

    @classmethod
    def from_samples(cls, samples, snap=True):
        """Author a block from 1024 integer heights. The AUTHORING direction.

        The table it builds is ours, not ArenaNet's -- see
        `HuffmanTable.for_frequencies`. A coefficient escapes when it cannot be
        a symbol: outside `-512..510`, or exactly 511, because 511 + 512 is the
        escape code itself and the client would read the next `escBits` bits.

        `snap` moves the samples onto the representable lattice and is on by
        default, because a freely authored height field is essentially never on
        it -- see `snap_block`. `snap=False` refuses instead and names the
        offending four-vector, which is the right mode for anything claiming to
        reproduce bytes rather than to author them. Either way the block's
        `samples` afterwards are what the client will read back.
        """
        if snap:
            samples, _ = snap_block(list(samples))
        block = cls(samples, None)
        freq = {}
        escaped = False
        for co in block._coefficients():
            for value in co[1:]:
                sym = value + HUFF_BIAS
                if 0 <= sym < HUFF_ESCAPE:
                    freq[sym] = freq.get(sym, 0) + 1
                else:
                    escaped = True
                    freq[HUFF_ESCAPE] = freq.get(HUFF_ESCAPE, 0) + 1
        if not freq:
            freq = {HUFF_BIAS: 1}
        block.table = HuffmanTable.for_frequencies(freq)
        if escaped and HUFF_ESCAPE not in block.table:
            raise AssertionError("the escape symbol went missing from the table")
        return block

    @classmethod
    def decode(cls, br):
        dc_base = br.take(BASE_BITS)
        if dc_base >= 0x8000:
            dc_base -= 0x10000
        dc_bits = br.take(DC_BITS_BITS) + 1
        esc_base = br.take(BASE_BITS)
        if esc_base >= 0x8000:
            esc_base -= 0x10000
        esc_bits = br.take(DC_BITS_BITS) + 1
        br.align()
        table = HuffmanTable.read(br)

        samples = [0] * TILE_SAMPLES
        dc_seen = []
        esc_seen = []
        for by in range(SUB_PER_TILE):
            for bx in range(SUB_PER_TILE):
                co = [0] * 16
                dc = dc_base + br.take(dc_bits)
                co[0] = dc
                dc_seen.append(dc)
                for i in range(1, 16):
                    sym = table.decode(br)
                    if sym == HUFF_ESCAPE:
                        value = esc_base + br.take(esc_bits)
                        esc_seen.append(value)
                        co[i] = value
                    else:
                        co[i] = sym - HUFF_BIAS
                mid = [0] * 16
                for i in range(SUB):
                    (mid[i], mid[i + 4], mid[i + 8],
                     mid[i + 12]) = _inverse4(co[i], co[i + 4], co[i + 8],
                                              co[i + 12])
                for r in range(SUB):
                    row = _inverse4(*mid[SUB * r:SUB * r + SUB])
                    off = (by * SUB + r) * CHUNK_SIZE + bx * SUB
                    samples[off:off + SUB] = row
        br.align()

        # The four parameters this codec re-derives, checked against what the
        # file stored. MEASURED equal on 187/187 sampled blocks; a disagreement
        # would mean the encoder here cannot reproduce ArenaNet's bytes, and
        # saying so loudly beats a silent round-trip failure 200 MB later.
        if dc_base != min(dc_seen):
            raise Undecodable(f"block's dcBase is {dc_base} but its smallest "
                              f"DC coefficient is {min(dc_seen)}")
        want = max(max(v - dc_base for v in dc_seen).bit_length(), 1)
        if dc_bits != want:
            raise Undecodable(f"block's dcBits is {dc_bits} but its DC range "
                              f"needs {want}")
        if esc_seen:
            if esc_base != min(esc_seen):
                raise Undecodable(f"block's escBase is {esc_base} but its "
                                  f"smallest escape is {min(esc_seen)}")
            want = max(max(v - esc_base
                           for v in esc_seen).bit_length(), 1)
            if esc_bits != want:
                raise Undecodable(f"block's escBits is {esc_bits} but its "
                                  f"escape range needs {want}")
        elif esc_base or esc_bits != 1:
            # No escape was used, so nothing constrains these two and they must
            # be carried. MEASURED: this branch is never taken in the corpus.
            raise Undecodable(f"block uses no escape but carries escBase "
                              f"{esc_base} / escBits {esc_bits}")
        return cls(samples, table)

    def encode(self, bw):
        blocks = self._coefficients()
        dcs = [co[0] for co in blocks]
        dc_base = min(dcs)
        dc_bits = max(max(v - dc_base for v in dcs).bit_length(), 1)
        escapes = []
        for co in blocks:
            for value in co[1:]:
                sym = value + HUFF_BIAS
                if sym != HUFF_ESCAPE and sym in self.table:
                    continue
                escapes.append(value)
        esc_base = min(escapes) if escapes else 0
        esc_bits = (max(max(v - esc_base for v in escapes).bit_length(), 1)
                    if escapes else 1)

        for name, base, width in (("dc", dc_base, dc_bits),
                                  ("esc", esc_base, esc_bits)):
            if not -0x8000 <= base < 0x8000:
                raise ValueError(f"{name}Base {base} does not fit the signed "
                                 f"16 bits the block header gives it")
            if width > (1 << DC_BITS_BITS):
                raise ValueError(f"{name}Bits {width} exceeds the "
                                 f"{1 << DC_BITS_BITS} the four-bit field can "
                                 f"name; this block's range is too wide to code")
        bw.put(dc_base & 0xFFFF, BASE_BITS)
        bw.put(dc_bits - 1, DC_BITS_BITS)
        bw.put(esc_base & 0xFFFF, BASE_BITS)
        bw.put(esc_bits - 1, DC_BITS_BITS)
        bw.align()
        self.table.write(bw)
        for co in blocks:
            bw.put(co[0] - dc_base, dc_bits)
            for value in co[1:]:
                sym = value + HUFF_BIAS
                if sym != HUFF_ESCAPE and sym in self.table:
                    self.table.encode(bw, sym)
                else:
                    self.table.encode(bw, HUFF_ESCAPE)
                    bw.put(value - esc_base, esc_bits)
        bw.align()

    def __eq__(self, other):
        return (isinstance(other, HeightBlock)
                and self.samples == other.samples
                and self.table == other.table)

    def __repr__(self):
        return (f"<HeightBlock {min(self.samples)}..{max(self.samples)}, "
                f"{len(self.table)} symbols>")


class StrippedTerrain:
    """One map's Stripped terrain chunk, decoded far enough to rebuild it.

    Field names follow `terrain.Terrain` wherever the two describe the same
    thing, so a reader can put them side by side. The three fields that exist
    only here -- `angle_index`, `tex_f12_index`, `tex_f16_index` -- are stored
    as their byte, because that is the stored form and the float is a function
    of it; `Terrain` has to keep the float because its own chunk keeps the float.
    """

    __slots__ = ("dim_x", "dim_y", "chunk_units", "angle_index", "tex_word",
                 "tex_f12_index", "tex_f16_index", "blocks", "tiles",
                 "table_a", "table_b", "bits", "shadow", "tag3b",
                 "signature", "version")

    def __init__(self, dim_x, dim_y, blocks, tiles, table_a, table_b, bits,
                 shadow=None, chunk_units=8, angle_index=0, tex_word=0,
                 tex_f12_index=0, tex_f16_index=0, tag3b=None,
                 signature=SIGNATURE, version=VERSION):
        self.signature = signature
        self.version = version
        self.dim_x = dim_x
        self.dim_y = dim_y
        self.chunk_units = chunk_units          # tag 0 packed & 0x3F
        self.angle_index = angle_index          # tag 0 byte at +5 of the body
        self.tex_word = tex_word
        self.tex_f12_index = tex_f12_index
        self.tex_f16_index = tex_f16_index
        self.blocks = list(blocks)              # tag 1, one per 32x32 tile
        self.tiles = bytes(tiles)               # tag 2, VERBATIM in the format
        self.table_a = bytes(table_a)           # tag 4
        self.table_b = bytes(table_b)           # tag 5
        self.bits = bytes(bits)                 # tag 3, VERBATIM in the format
        self.shadow = None if shadow is None else list(shadow)   # tag 7
        self.tag3b = tag3b                      # the optional 17 bytes

    # -- derived shape -----------------------------------------------------

    @property
    def cells(self):
        return self.dim_x * self.dim_y

    @property
    def chunks_x(self):
        return self.dim_x // CHUNK_SIZE

    @property
    def chunks_y(self):
        return self.dim_y // CHUNK_SIZE

    @property
    def block_count(self):
        return self.chunks_x * self.chunks_y

    @property
    def chunk_distance(self):
        """Tag 0 +0x08 in the Bloated chunk: whole 32x32 chunks x 3072.0."""
        return self.chunk_units * CHUNK_PITCH

    @property
    def angle(self):
        return ANGLE_TABLE[self.angle_index]

    @property
    def tex_f12(self):
        return TEX_TABLE[self.tex_f12_index]

    @property
    def tex_f16(self):
        return TEX_TABLE[self.tex_f16_index]

    @property
    def heights(self):
        """The height field as float32-exact Python floats, tiled like `Terrain`.

        The blocks are already in tile-row-major order and each holds its tile
        row-major, which is exactly `Terrain.index`'s layout -- so this
        concatenation is comparable to `Terrain.heights` element for element,
        and that comparison is this module's real check.
        """
        out = []
        for block in self.blocks:
            out.extend(float(v) for v in block.samples)
        return out

    # -- decoding ----------------------------------------------------------

    @classmethod
    def from_chunk(cls, blob, chunk_id=STRIPPED_TERRAIN_CHUNK):
        if chunk_id == terrain.TERRAIN_CHUNK:
            raise Undecodable(
                "chunk 0x20000002 is the BLOATED terrain encoding, whose header "
                "is eight bytes and whose records carry a u32 size. Use "
                "terrain.Terrain for it; this module decodes 0x10000002 only.")
        if chunk_id != STRIPPED_TERRAIN_CHUNK:
            raise Undecodable(f"chunk 0x{chunk_id:08X} is not stripped terrain "
                              f"(0x{STRIPPED_TERRAIN_CHUNK:08X})")
        return cls.decode(blob)

    @classmethod
    def decode(cls, blob):
        blob = bytes(blob)
        if len(blob) < HEADER.size:
            raise Undecodable(f"stripped terrain chunk is {len(blob)} bytes, "
                              f"shorter than its {HEADER.size}-byte header")
        signature, version = HEADER.unpack_from(blob, 0)
        if signature != SIGNATURE:
            raise Undecodable(f"stripped terrain signature 0x{signature:08X} "
                              f"!= 0x{SIGNATURE:08X}")
        if version != VERSION:
            raise Undecodable(f"stripped terrain version {version} != {VERSION}")
        p = HEADER.size

        p = _want_tag(blob, p, TAG_DIMS)
        if p + 9 > len(blob):
            raise Undecodable("tag 0 runs off the end of the chunk")
        packed = struct.unpack_from("<I", blob, p)[0]
        marker = packed & DIMS_MARKER_MASK
        if marker != DIMS_MARKER:
            raise Undecodable(f"tag 0's marker bits are 0x{marker:02X}; the "
                              f"client refuses anything but 0x{DIMS_MARKER:02X}")
        pitch = (packed >> 8) & 0xFF
        if pitch != STORED_PITCH:
            raise Undecodable(f"tag 0 stores a cell pitch of {pitch}; the "
                              f"client compares it against {STORED_PITCH}.0 "
                              f"and refuses anything else")
        dim_y = (((packed >> 16) & 0xFF) + 1) * CHUNK_SIZE
        dim_x = ((packed >> 24) + 1) * CHUNK_SIZE
        terrain._gate_dims(dim_x, dim_y)
        chunk_units = packed & DIMS_DISTANCE_MASK
        angle_index = blob[p + 4]
        tex_word = struct.unpack_from("<H", blob, p + 5)[0]
        tex_f12_index = blob[p + 7]
        tex_f16_index = blob[p + 8]
        p += 9
        cells = dim_x * dim_y

        p = _want_tag(blob, p, TAG_HEIGHT)
        br = BitReader(blob, p)
        blocks = [HeightBlock.decode(br)
                  for _ in range((dim_x // CHUNK_SIZE) * (dim_y // CHUNK_SIZE))]
        br.align()
        p += br.consumed()

        p = _want_tag(blob, p, TAG_TILE)
        tiles = _take(blob, p, cells, "tag 2")
        p += cells

        p = _want_tag(blob, p, TAG_TABLE_A)
        table_a, p = _read_table(blob, p, TAG_TABLE_A)
        p = _want_tag(blob, p, TAG_TABLE_B)
        table_b, p = _read_table(blob, p, TAG_TABLE_B)
        if len(table_a) != len(table_b):
            raise Undecodable(f"tag 4 has {len(table_a)} entries and tag 5 has "
                              f"{len(table_b)}; they agree on 349 of 349 maps")

        p = _want_tag(blob, p, TAG_BITS)
        bits = _take(blob, p, cells // 4, "tag 3")
        p += cells // 4

        shadow = None
        if p < len(blob) and blob[p] == TAG_SHADOW:
            p += 1
            shadow, p = _read_shadow(
                blob, p, (dim_x // CHUNK_SIZE) * (dim_y // CHUNK_SIZE))

        tag3b = None
        if p < len(blob) and blob[p] == TAG_BITS:
            p += 1
            tag3b = _take(blob, p, TAG3B_SIZE, "the second tag 3")
            p += TAG3B_SIZE

        p = _want_tag(blob, p, TERMINATOR)
        if p != len(blob):
            raise Undecodable(f"record walk ended at {p} of {len(blob)} bytes")

        return cls(dim_x, dim_y, blocks, tiles, table_a, table_b, bits,
                   shadow=shadow, chunk_units=chunk_units,
                   angle_index=angle_index, tex_word=tex_word,
                   tex_f12_index=tex_f12_index, tex_f16_index=tex_f16_index,
                   tag3b=tag3b, signature=signature, version=version)

    # -- encoding ----------------------------------------------------------

    def validate(self):
        """Everything `encode()` refuses. Empty is good."""
        bad = []
        if self.signature != SIGNATURE:
            bad.append(f"signature 0x{self.signature:08X} != 0x{SIGNATURE:08X}")
        if self.version != VERSION:
            bad.append(f"version {self.version} != {VERSION}")
        try:
            terrain._gate_dims(self.dim_x, self.dim_y)
        except ValueError as exc:
            bad.append(str(exc))
        if not 0 <= self.chunk_units <= DIMS_DISTANCE_MASK:
            bad.append(f"chunk_units {self.chunk_units} does not fit in the "
                       f"six bits tag 0 gives it")
        for name in ("angle_index", "tex_f12_index", "tex_f16_index"):
            v = getattr(self, name)
            if not 0 <= v <= 0xFF:
                bad.append(f"{name} {v} is not a byte")
        if not 0 <= self.tex_word <= 0xFFFF:
            bad.append(f"tex_word {self.tex_word} is not a u16")
        if self.dim_x // CHUNK_SIZE > 0x100 or self.dim_y // CHUNK_SIZE > 0x100:
            bad.append(f"dims {self.dim_x}x{self.dim_y} exceed the 8192 that "
                       f"tag 0's two count bytes can name")
        if len(self.blocks) != self.block_count:
            bad.append(f"{len(self.blocks)} height blocks for "
                       f"{self.block_count} 32x32 tiles")
        if len(self.tiles) != self.cells:
            bad.append(f"{len(self.tiles)} tile indices for {self.cells} cells")
        if len(self.bits) != self.cells // 4:
            bad.append(f"{len(self.bits)} tag-3 bytes for "
                       f"{self.cells // 4} expected")
        if len(self.table_a) != len(self.table_b):
            bad.append(f"tag 4 has {len(self.table_a)} entries and tag 5 has "
                       f"{len(self.table_b)}")
        if len(self.table_a) > 0xFF:
            bad.append(f"tag 4's count {len(self.table_a)} does not fit in a u8")
        for name in ("table_a", "table_b"):
            values = getattr(self, name)
            if values and _table_width(values) > (1 << TABLE_WIDTH_BITS) - 1:
                bad.append(f"{name} needs {_table_width(values)} bits per "
                           f"entry and tag {4 if name == 'table_a' else 5} "
                           f"stores that width in {TABLE_WIDTH_BITS}")
        if self.tiles and self.table_a and max(self.tiles) >= len(self.table_a):
            bad.append(f"tile index {max(self.tiles)} indexes past tag 4's "
                       f"{len(self.table_a)} entries")
        if self.shadow is not None and len(self.shadow) != self.block_count:
            bad.append(f"{len(self.shadow)} tag-7 blocks for "
                       f"{self.block_count} 32x32 tiles")
        if self.tag3b is not None and len(self.tag3b) != TAG3B_SIZE:
            bad.append(f"the second tag 3 is {len(self.tag3b)} bytes, not "
                       f"{TAG3B_SIZE}")
        return bad

    def encode(self):
        """Typed values back to bytes.

        Nothing here consults a stored size, a stored count or a stored coding
        width -- see `census()` for what is reconstructed and what the format
        stores raw.
        """
        bad = self.validate()
        if bad:
            raise ValueError("stripped terrain will not encode:\n  "
                             + "\n  ".join(bad))
        out = bytearray(HEADER.pack(self.signature, self.version))

        out.append(TAG_DIMS)
        packed = (DIMS_MARKER | self.chunk_units
                  | (STORED_PITCH << 8)
                  | ((self.dim_y // CHUNK_SIZE - 1) << 16)
                  | ((self.dim_x // CHUNK_SIZE - 1) << 24))
        out += struct.pack("<IBHBB", packed, self.angle_index, self.tex_word,
                           self.tex_f12_index, self.tex_f16_index)

        out.append(TAG_HEIGHT)
        bw = BitWriter()
        for block in self.blocks:
            block.encode(bw)
        out += bw.bytes()

        out.append(TAG_TILE)
        out += self.tiles

        out.append(TAG_TABLE_A)
        out += _write_table(self.table_a)
        out.append(TAG_TABLE_B)
        out += _write_table(self.table_b)

        out.append(TAG_BITS)
        out += self.bits

        if self.shadow is not None:
            out.append(TAG_SHADOW)
            for block in self.shadow:
                payload = block.payload
                out += struct.pack("<I", len(payload))
                out += payload
                out += block.tail

        if self.tag3b is not None:
            out.append(TAG_BITS)
            out += self.tag3b

        out.append(TERMINATOR)
        return bytes(out)

    def census(self):
        """Bytes this codec RECONSTRUCTS against bytes the format stores raw.

        The honest half of a byte-identical round trip. Tags 2, 3 and the
        optional second tag 3 are carried because the format carries them --
        there is no encoding under them to understand -- and they are the whole
        of the carried side. Tag 7 is counted as reconstructed: it goes through
        `terrain.ShadowBlock`, which rebuilds the payload from a bitmap and
        derives the 128-byte tail.
        """
        total = len(self.encode())
        carried = len(self.tiles) + len(self.bits)
        if self.tag3b is not None:
            carried += 1 + TAG3B_SIZE
        return {"total": total, "carried": carried,
                "reconstructed": total - carried,
                "fraction_reconstructed": (total - carried) / total if total
                                          else 0.0}

    # -- authoring ---------------------------------------------------------

    @classmethod
    def build(cls, dim_x, dim_y, heights, tiles=None, table_a=b"\x00\x01\x02",
              table_b=b"\x01\x01\x01", bits=None, shadow=True,
              chunk_units=8, angle_index=194, tex_word=0,
              tex_f12_index=64, tex_f16_index=75, tag3b=None, snap=True):
        """A whole Stripped terrain chunk from a height field and nothing else.

        `heights` is `dim_x*dim_y` numbers in the SAME tiled order
        `terrain.Terrain.heights` uses -- `Terrain.index` maps a grid cell to
        its slot -- and every one of them must be an exact integer, because the
        codec's coefficients are integers and there is nowhere to put a
        fraction. FINDINGS 19 measured 60,468,224 of 60,468,224 retail samples
        to be exact integers, so this refuses nothing retail contains.

        The default tag 7 is one all-clear shadow tile per 32x32 chunk, which
        `trnshadow` codes as 272 rows of `FF 12` -- k == 544, and 544 is exactly
        the corpus minimum. `shadow=None` omits the record, which the pipeline
        allows.
        """
        terrain._gate_dims(dim_x, dim_y)
        cells = dim_x * dim_y
        if len(heights) != cells:
            raise ValueError(f"{len(heights)} heights for {cells} cells")
        samples = []
        for i, h in enumerate(heights):
            v = int(h)
            if v != h:
                raise ValueError(f"height {h!r} at index {i} is not an exact "
                                 f"integer; this codec has nowhere to put a "
                                 f"fraction")
            samples.append(v)
        blocks = [HeightBlock.from_samples(
            samples[k * TILE_SAMPLES:(k + 1) * TILE_SAMPLES], snap=snap)
            for k in range((dim_x // CHUNK_SIZE) * (dim_y // CHUNK_SIZE))]
        if shadow is True:
            import trnshadow
            shadow = [terrain.ShadowBlock([0] * trnshadow.BLOCK_EDGE)
                      for _ in blocks]
        return cls(dim_x, dim_y, blocks,
                   bytes(cells) if tiles is None else tiles,
                   table_a, table_b,
                   bytes(cells // 4) if bits is None else bits,
                   shadow=shadow, chunk_units=chunk_units,
                   angle_index=angle_index, tex_word=tex_word,
                   tex_f12_index=tex_f12_index, tex_f16_index=tex_f16_index,
                   tag3b=tag3b)

    # -- loading -----------------------------------------------------------

    @classmethod
    def load(cls, map_file_id, archive=None, table=None):
        own = archive is None
        ar = archive or Archive()
        try:
            table = table if table is not None else file_id_table(ar)
            row = table.get(map_file_id)
            if row is None:
                raise KeyError(f"no file id 0x{map_file_id:X} in the archive")
            return cls.from_row(row, ar)
        finally:
            if own:
                ar.close()

    @classmethod
    def from_row(cls, row, archive):
        """Decode the stripped terrain of a map named by its HEAD row.

        A map is two MFT rows and the Stripped stream lives in the partner, so
        this resolves the chain rather than reading the row it was handed. A
        partner row is accepted too, and says so.
        """
        import mapchunks
        entry = next(e for e in archive.entries if e.index == row)
        if mapchunks.is_map_head(entry):
            entry = mapchunks.MapIndex(archive).partner(entry)
        data = archive.read(entry)
        for chunk_id, off, size in ffna_chunks(data):
            if chunk_id == STRIPPED_TERRAIN_CHUNK:
                return cls.from_chunk(bytes(data[off:off + size]), chunk_id)
        raise Undecodable(f"row {entry.index} has no stripped terrain chunk")

    def __repr__(self):
        return (f"<StrippedTerrain {self.dim_x}x{self.dim_y}, "
                f"{len(self.table_a)} tile types, "
                f"{len(self.blocks)} height blocks>")


def _want_tag(blob, p, tag):
    """Stage 1's record header is one byte: 0x0073E410's `stage == 1` arm."""
    if p >= len(blob):
        raise Undecodable(f"expected tag {tag} at {p} but the chunk ends there")
    if blob[p] != tag:
        raise Undecodable(f"expected tag {tag} at {p}, found {blob[p]}; the "
                          f"client's pipeline has no dispatch loop and demands "
                          f"this order")
    return p + 1


def _take(blob, p, n, what):
    if p + n > len(blob):
        raise Undecodable(f"{what} wants {n} bytes at {p} but only "
                          f"{len(blob) - p} remain")
    return blob[p:p + n]


def _table_width(values):
    return max(max(values).bit_length(), 1) if values else 1


def _read_table(blob, p, tag):
    """Tags 4 and 5: 0x00759140 / 0x00758F10."""
    br = BitReader(blob, p)
    n = br.take(TABLE_COUNT_BITS)
    if n == 0:
        # 0x0075919F: the cursor advances by exactly one byte and nothing is
        # emitted beyond the count. No corpus map takes this branch.
        return b"", p + 1
    width = br.take(TABLE_WIDTH_BITS)
    if width == 0:
        # 0x007591FF's arm asserts TrnBitStore:128 on every entry and shifts by
        # 32, which x86 treats as a no-op. It cannot produce a defined value.
        raise Undecodable(f"tag {tag} declares a zero-bit entry width")
    need = (width * n + 0x12) >> 3
    if len(blob) - p < need:
        raise Undecodable(f"tag {tag} needs {need} bytes and {len(blob) - p} "
                          f"remain")
    values = bytes(br.take(width) for _ in range(n))
    br.align()
    if _table_width(values) != width:
        raise Undecodable(f"tag {tag} stores {width} bits per entry but its "
                          f"largest is {max(values)}, which needs "
                          f"{_table_width(values)}")
    return values, p + br.consumed()


def _write_table(values):
    bw = BitWriter()
    bw.put(len(values), TABLE_COUNT_BITS)
    if values:
        width = _table_width(values)
        bw.put(width, TABLE_WIDTH_BITS)
        for v in values:
            bw.put(v, width)
        bw.align()
    else:
        # Match the decoder's one-byte branch: the count alone, no width.
        bw.align()
    return bw.bytes()


def _read_shadow(blob, p, blocks):
    """Tag 7, and it is the Bloated chunk's own per-block record.

    `{u32 k, u8 payload[k], u8 tail[128]}`, decoded through
    `terrain.ShadowBlock` -- so the payload becomes a 272x272 bitmap and the
    stored tail is checked against what that bitmap derives, exactly as the
    Bloated codec does. Carrying the bytes instead would round-trip and prove
    nothing.
    """
    out = []
    for i in range(blocks):
        if p + 4 > len(blob):
            raise Undecodable(f"tag 7 block {i} of {blocks}: the chunk ends "
                              f"after {p} bytes")
        k, = struct.unpack_from("<I", blob, p)
        p += 4
        if p + k + SHADOW_TAIL > len(blob):
            raise Undecodable(
                f"tag 7 block {i} of {blocks} declares {k} bytes plus a "
                f"{SHADOW_TAIL}-byte tail, but only {len(blob) - p} remain")
        try:
            out.append(terrain.ShadowBlock.from_bytes(
                blob[p:p + k], blob[p + k:p + k + SHADOW_TAIL]))
        except ValueError as exc:
            raise Undecodable(f"tag 7 block {i} of {blocks}: {exc}") from exc
        p += k + SHADOW_TAIL
    return out, p


def _main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--file-id", default=None,
                    help="map file id, e.g. 0x345CC (Kamadan, the default)")
    ap.add_argument("--row", type=int, default=None,
                    help="MFT row -- head or partner, either resolves")
    ap.add_argument("--records", action="store_true",
                    help="also print the Bloated chunk's fields beside ours")
    args = ap.parse_args()

    import time
    with Archive(args.dat) as ar:
        t0 = time.perf_counter()
        if args.row is not None:
            st = StrippedTerrain.from_row(args.row, ar)
            who = f"row {args.row}"
        else:
            fid = int(args.file_id, 0) if args.file_id else 0x345CC
            st = StrippedTerrain.load(fid, archive=ar)
            who = f"file id 0x{fid:X}"
        dt = time.perf_counter() - t0

        heights = st.heights
        lo, hi = min(heights), max(heights)
        cen = st.census()
        print(f"{who}: stripped terrain {st.dim_x}x{st.dim_y}, decoded in "
              f"{dt:.2f}s")
        print(f"  extent        {st.dim_x * CELL_PITCH:.0f} x "
              f"{st.dim_y * CELL_PITCH:.0f} world units "
              f"({st.chunks_x}x{st.chunks_y} tiles)")
        print(f"  height        {lo:.0f} .. {hi:.0f}")
        print(f"  tag 0         units {st.chunk_units} "
              f"(= {st.chunk_distance:.0f})  angle idx {st.angle_index} "
              f"-> {st.angle!r}")
        print(f"                u16 {st.tex_word}  f12 idx "
              f"{st.tex_f12_index} -> {st.tex_f12!r}  f16 idx "
              f"{st.tex_f16_index} -> {st.tex_f16!r}")
        print(f"  tile types    {len(st.table_a)}  "
              f"(max index used {max(st.tiles) if st.tiles else '-'})")
        print(f"  tag 7         "
              f"{'absent' if st.shadow is None else f'{len(st.shadow)} blocks'}")
        print(f"  tag 3'        {'absent' if st.tag3b is None else 'present'}")
        syms = sorted(len(b.table) for b in st.blocks)
        print(f"  huffman       {syms[0]}..{syms[-1]} symbols per block")
        print(f"  census        {cen['reconstructed']} B reconstructed "
              f"({100 * cen['fraction_reconstructed']:.2f}%), "
              f"{cen['carried']} B carried of {cen['total']}")
        blob = st.encode()
        print(f"  round trip    {len(blob)} B re-encoded")
        if args.records:
            # The Bloated chunk lives in the HEAD row. `--row` accepts either
            # end of the pair, so a partner has to be walked back or
            # `Terrain.from_row` finds the stripped chunk and refuses -- which
            # is what it did the first time this branch was run.
            import mapchunks
            row = args.row
            if row is None:
                row = file_id_table(ar)[int(args.file_id, 0)
                                        if args.file_id else 0x345CC]
            entry = next(e for e in ar.entries if e.index == row)
            if not mapchunks.is_map_head(entry):
                index = mapchunks.MapIndex(ar)
                row = next(h.index for h, p in index.pairs if p.index == row)
            trn = terrain.Terrain.from_row(row, ar)
            same = sum(1 for a, b in zip(heights, trn.heights) if a == b)
            print(f"  vs BLOATED    heights {same}/{len(trn.heights)}, "
                  f"tiles {st.tiles == trn.tiles}, "
                  f"angle {st.angle == trn.angle}, "
                  f"dist {st.chunk_distance == trn.chunk_distance}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
