"""The ground itself: read and write a Guild Wars map's Bloated terrain chunk.

A map's shape -- how big the grid is, how high every corner of it sits, which
tile type each cell uses -- lives in chunk `0x20000002`. Reading it is what lets
us describe retail ground in our own terms; WRITING it byte-identically is the
part that matters, because an authoring pipeline that cannot reproduce a retail
chunk exactly has no evidence it understands the format at all. This module is
both halves, sharing one record table so the two cannot drift.

    blob = ...                       # the chunk payload out of an ffna map file
    trn  = Terrain.decode(blob)
    assert trn.encode() == blob      # 349 of 349 retail maps

WHERE THE LAYOUT COMES FROM. `studies/customarea/FINDINGS.md` sections 3, 4,
17.4 and 17.5. Two lineages, and neither is somebody's parser:

  * MEASURED -- the record framing, every size law and every field width was
    walked out of `Gw.dat` itself over all 349 map rows (`alloc.flags == 259`),
    3,165 records, 59,051 tag-7 blocks. The archive is the artifact; a wrong
    width desyncs the walk and the next tag byte lands on garbage.
  * SOURCE-CODE -- the client's own 11-entry step table at `0x00A74F28`
    (build 38797, read out of a disassembly) names the tags, their order, and
    which fields are hard gates. It is ONE build and a disassembly says what the
    code can do, not what it does; every claim it carries below is paired with
    something the archive can refute.

**No upstream code, table or constant was taken.** GuildWarsMapBrowser has a
pattern for this chunk and it is not used here -- see WHERE THE SOURCE IS WRONG
for the one name of theirs this module deliberately contradicts. Nothing in this
file owes a THIRD-PARTY-NOTICES row.

WHAT MAKES IT EVIDENCE ANYWAY. The layout is self-checking in six independent
ways, and all six check out. Every count below was MEASURED on
`vault/dat_study/Gw.dat` on 2026-08-10 by decoding and re-encoding all 349 map
rows through this module, except where a line says otherwise:

  * **Byte-identical round-trip on 349 of 349 maps**, both tag sequences. The
    decoder throws the original bytes away and the encoder rebuilds them from
    typed values. The only bytes carried across verbatim are tags 3, 7 and 9,
    each named and scoped in the next section.
  * The record walk, advancing by `5 + size`, lands on the physical final byte
    of the chunk in 349/349. Two framing controls fail 349/349 (FINDINGS 4; the
    test reproduces both on the reference chunk): reading the record header as
    `{u32 size, u8 tag}`, and starting the walk at +12, which is the PATHING
    chunk's header length -- see the trap below.
  * Five of the nine record lengths are PREDICTED by `dimX`/`dimY`, two u32s
    read out of a different record: `dx*dy*4` for tag 1, `dx*dy` for tags 2 and
    9, `dx*dy//4` for tag 3, and tag 7's block count `(dx//32)*(dy//32)`. All
    349/349. Wrong dims, wrong tiling or a wrong element width desyncs the walk
    and lands the next tag byte on garbage. Tags 4 and 5 are self-describing
    (`u8 n` + n bytes) rather than dims-derived, and are constrained instead by
    having to agree with each other and to bound tag 2.
  * Tag 7's per-block walk (`{u32 k, k bytes, 128 bytes}`) closes on the
    record's declared end using a block count taken from dims and not from the
    file: 59,051 of 59,051 blocks.
  * Cross-record, the file can fail it: `len(table_a) == len(table_b)` on
    349/349, and `max(tiles) <= len(table_a) - 1` on 349/349 with 332 attaining
    equality and 0 exceeding.
  * Cross-CHUNK, the strongest one available and the reason the grid layout is
    not a guess: the Map Parameters chunk `0x2000000C` carries a world rect, and
    `(x1-x0)/dimX` and `(y1-y0)/dimY` give **exactly one distinct pair over all
    349 maps, (96.0, 96.0)**. Two chunks written by different subsystems
    predicting each other; one row of grid error anywhere produces a second
    value. The `(dim-1)` divisor is the negative control and fails visibly --
    99.10 on the 32x32 reference map, and 96.15..96.50 corpus-wide per
    FINDINGS 4.

WHAT THE ROUND-TRIP PROVES, AND WHAT IT DOES NOT. This split is the honest part
and it is not decoration -- a round-trip over opaque blobs proves framing and
nothing else, and calling that a decode would be exactly the check-that-cannot-
fail this repository forbids.

  FULLY SEMANTIC -- the model holds typed values and the encoder reconstructs
  the bytes from them alone:

    tag 0   seven typed fields. Refutable and refuted-nothing: the dims predict
            six other record lengths AND the Map Parameters rect.
    tag 1   `dx*dy` float32 heights. MEASURED over the whole corpus:
            **60,468,224 of 60,468,224 samples are exact integers**, 0 of them
            are NaN or infinite, and the range is -19,632..5,002.
            The non-finite count matters because a signalling NaN is the one
            float32 bit pattern a Python `float` could quiet on the way through;
            no shipped map contains one, and an authoring tool feeding synthetic
            heights should know that is the only unexercised case.
    tag 2   one u8 per cell, an index into tag 4's table, bounded by it.
    tag 4   `u8 n` + n bytes, n in 3..63 -- and 63 is MAP_TILE_MAX_COUNT, which
            the client compares against literally (`cmp esi,0x3f` at 0x00761CD8,
            assert `TrnTexBlendHi:216 count <= MAP_TILE_MAX_COUNT`). The client
            calls the array `tileTypes` (assert `TrnTex:218`, on the pointer
            this record fills). It is the identity permutation on only 252/349
            maps, so it is a real table -- but it is NOT a permutation at all.
            **It is a staircase: `A[0] == 0` and every step is 0 or +1, on
            349/349**, so it is a group index over consecutive slots, and
            `max(A) < len(terrain dependencies)` on 349/349. 97 maps repeat a
            value. What the grouping MEANS is NOT FOUND.
    tag 5   `u8 n` + n bytes, same n as tag 4 on 349/349. **It is a property of
            the TEXTURE, not of the map.** Slot `i` pairs with the map's `i`-th
            Terrain Dependencies file (`0x21000002`), offset by one on the 24
            maps that carry an extra leading dependency, and under that pairing
            the value is a function of the file on **17,083 of 17,089 slot uses
            over 1,648 distinct files** -- 5 files disagree with themselves.
            Null model, shuffling the values within each map: ~6,180. 30 distinct
            values, **bit 0 set in 17,089 of 17,089 and bit 7 in 0**, which is
            why the client's `& 0x7F` is unexercised. What the 7 bits classify
            is NOT FOUND.
    tag 3'  the optional second tag-3 record: `u8` lead + four f32. **The 24 maps
            that carry it are exactly the 24 whose Terrain Dependencies list is
            one longer than n (24/24 both ways), and that extra file is the
            FIRST entry** -- realigning slot `i` to dependency `i+1` on those
            maps makes tag 5's texture function exact there, 880 of 880. So the
            record and the extra texture arrive together; per FINDINGS 17.4 its
            four floats go to TrnTex +0x291C/+0x2920/+0x2928/+0x292C.

  SEMANTIC AS AN ARRAY, MEANING UNKNOWN -- the bytes are unambiguous, what they
  mean is not, so they are carried as `bytes` and no structure is invented:

    tag 9   one full-range u8 per cell. **It is a baked directional lightmap**
            -- identified 2026-08-11, and the evidence is a different record and
            a different chunk, not this codec. Fit `255 * max(0, N.L)` from the
            tag-1 heightfield with `L = (cos t, 0, sin t)`: median Pearson r
            **0.887 over 345 maps**; the elevation `t` that maximises it tracks
            **tag 0's angle field** with Spearman **0.9352**; and the azimuth
            control puts the light on the +x axis with no y component on
            **343 of 345 maps**, which is what the client's own
            `TrnTexIntensity:342 lightDir.y == 0` says. So tag 0 +0x0C is the
            sun's elevation and tag 9 is what it bakes to. The exact transfer
            curve is NOT settled -- 348 of 349 maps saturate at 255 -- so this
            module still stores the bytes and invents no formula.
    tag 3   `dx*dy // 4` bytes, so 2 bits per cell is arithmetically forced and
            that much is proven. **The client's own de-tiler settles the cell
            order and rules out the rival reading.** `0x0074AC50` copies, per
            32x32 tile, 32 iterations of 8 bytes, advancing the destination by
            `dx/4` between them and unpacking to a flat image `dx/4` bytes wide:
            so a byte covers FOUR CONSECUTIVE X CELLS of one row, and the "one
            byte per 2x2 block" reading -- which satisfies the same size law --
            is refuted (it would be 16 rows of 16). **The bit pair's position
            INSIDE the byte is SETTLED as of 2026-08-14 and `bits_at`'s
            `(i & 3) * 2` was already exactly right** -- promoted INFERRED ->
            MEASURED. The old note here said any self-consistent convention
            round-trips so a per-cell decode could not be checked, and that was
            true only while the field had no meaning. It has one now (below),
            so the CLIENT decides: two consumers read the de-tiled buffer with a
            shift counter starting at 0 and stepping `+2 & 7`. The corpus agrees
            independently -- cross-byte co-occurrence collapses onto a monotone
            function of true distance, `C(3->0) = 50.546%` against
            `C(0->3) = 33.770%` (ratio 1.497, z = 31.1), where the reversed
            reading demands the opposite inequality, and a null shuffling byte
            POSITIONS while keeping CONTENTS collapses it to ~1.0.
            **MEANING: the per-cell tile VARIATION selector** (2026-08-14,
            `studies/terrain/FINDINGS.md` §3.2). A terrain texture is a 256x256
            holding FOUR 128x128 variants of one material; variation `v` selects
            quadrant `v`. Zero means "take the PRNG's pick" -- Lehmer/MINSTD
            re-seeded per 32x32 tile with `(tile.x << 16) ^ tile.y`, with BOTH
            branches drawing so the stream position is a pure function of the
            cell index and the ground is deterministic. That is why the value is
            0 on 99.94% of cells and near-uniform over 1/2/3 on the rest: it is a
            sparse authored override, and it can only pin quadrants 1-3 because
            quadrant 0 is reachable only through the draw.
            The four dead hypotheses below are left as recorded; each is still a
            true negative, and none of them was this.
            All-zero on 168 of 349 maps; where it is set at all the median map
            has 0.10% of its bytes non-zero (max 7.5%). Among non-zero cells the
            three values are near-uniform (row 32347: 840/805/816 for 1/2/3),
            which is what a random 3-way choice looks like and not what a flag
            looks like. It does not mark steep ground (mean |grad| 0.9635 on set
            cells against 0.9627 over the map, row 32347), it is not a property
            of the tile type (39 of that map's 58 slots carry some, none above
            15% of its cells), it is not the map edge (set cells sit in interior
            blobs), and it does not follow height. Whatever selects it is not in
            this chunk.

    tag 7   `(dx//32)*(dy//32)` blocks of `{u32 k, u8 payload[k], u8 tail[128]}`,
            and as of 2026-08-11 **DECODED, not carried.** `ShadowBlock` holds a
            272x272 one-bit shadow bitmap; the payload is regenerated by
            `trnshadow.encode_rows` and the 128-byte tail DERIVED by
            `trnshadow.tail_from_rows`, so neither stored field survives the
            decode. Corpus: 59,051/59,051 payloads and 59,051/59,051 tails
            reproduce byte-identically, and the 8x8 and 12x12 window controls
            miss 1,562,798 and 611,928 bits.

            This block used to sit under a heading reading "FRAMING PROVEN,
            CONTENT OPAQUE -- carried verbatim", and it was by a wide margin the
            largest carried thing in the round-trip. That heading is gone with
            the last record under it. The distinction it drew is still the point
            and is kept in `ShadowBlock`'s own docstring: a round-trip over
            carried bytes compares a value with itself.

            The decoder REFUSES a block whose stored tail its own bitmap
            disproves, rather than keeping the stored one -- which would
            re-encode byte-identically and hide the disagreement.

WHERE THE SOURCE IS WRONG. Recorded rather than overwritten; three of these are
corrections to `studies/customarea/FINDINGS.md` itself, made by re-measuring it.

  * **The angle lattice is exact to 1 ULP, not bit-exactly.** FINDINGS 4 and
    17.4 say all 349 corpus angles "land exactly on" the lattice
    `b * 90pi/45720`. MEASURED over the 55 distinct stored bit patterns:
    `float32(b*90pi/45720)` -- which is `float32(b*pi/508)`, the same number --
    reproduces **39 of 55 patterns, 286 of 349 maps**. The best alternative
    formulation, `float32(1.5707963705062866*b/254)`, reproduces **53 of 55,
    347 of 349**. Every miss is exactly 1 ULP; the maximum bit distance over the
    whole corpus is 1. The claim survives as "within 1 ULP of `b*pi/508` for
    integer b in [16, 250]" and dies as a bit-exact identity. **Consequence, and
    it is why `encode()` stores the decoded float32 verbatim: an encoder must
    never recompute the angle from `b`.**

    *The 1-ULP caveat is RETIRED as of 2026-08-12, and only the last sentence of
    it still matters. The client's own expression, at 0x00758D99 in the Stripped
    loader, is `(float)((double)b * 282.74334716796875 / 45720.0)` -- where
    282.74334716796875 is `(double)(float)(90pi)`, a float32 constant promoted,
    so 90pi is rounded ONCE before the divide. That reproduces the stored float
    on 349 of 349 maps. `strippedterrain.ANGLE_TABLE` is that expression and
    `test_strippedterrain.py` runs both formulations above as controls that must
    disagree with it. Nothing changes here: `b` is not in this chunk, so this
    encoder still has nothing to recompute from.*
  * FINDINGS 17.4 says the angle takes "54 distinct" values; FINDINGS 4 says 55
    in the same document. MEASURED: **55** -- 55 distinct bit patterns mapping
    to 55 distinct `b` in [16, 250], injectively.
  * FINDINGS 4's tag-3' row says "the last three floats are byte-identical
    across different maps". REFUTED over all 24 records: **22 distinct 4-tuples
    and 20 distinct last-three tuples**, with 14/18/13/15 distinct values in the
    first, second, third and fourth float. There are repeats; there is nothing
    like identity. Do not build a check on it.
  * FINDINGS 4 says tag 3 is all-zero in "~155" maps. MEASURED: **168 of 349**.
  * The field GuildWarsMapBrowser calls `cellSize` (tag 0, +0x08) is not a cell
    size. It is 24576.0 on 348 maps and 55296.0 on one, constant across 104
    different grid sizes, and the client consumes it as
    `max(3, (int)(v / 3072.0))` -- a distance in whole 32x32 terrain chunks.
    The cell pitch is 96.0 and is a compile-time constant.

TRAPS, ALL OF THEM REAL AND ALL OF THEM PAID FOR ONCE.

  * **The terrain header is 8 bytes; the pathing header is 12.** Do not share a
    constant with `pathmap.py`. Starting the walk at +12 fails 349/349.
  * **The record header is `{u8 tag, u32 size}` and is unaligned by
    construction.** There is no padding anywhere in this chunk.
  * **There are two legal tag sequences.** 325 maps carry
    `0,1,2,4,5,3,9,7,255`; 24 carry `0,1,2,4,5,3,9,7,3,255` with a second
    17-byte tag-3 record. A dict keyed by tag silently drops it -- that exact
    bug produced a false "325/349" in an earlier pass, which is why this module
    keeps `order` and encodes from it.
  * The client has no dispatch loop: its step table demands these tags in this
    order, so `decode()` is a fixed pipeline and an out-of-order tag raises.
  * Per-record `size` is advisory TO THE CLIENT for every tag but 7 -- its
    reader returns `end >= cursor+5+size` and never adds `size` to the cursor.
    We are stricter, which is the right way round: the declared size must equal
    the length the dims-derived reader consumes, and it does on 349/349, so a
    byte-identical re-encode never needs a stored size.
  * `ffna_chunks()` is a GENERATOR. Consuming it twice yields nothing the second
    time; that bug silently zeroed a corpus script's results once already.

SCOPE. Bloated stream only. The Stripped partner's terrain chunk is
`0x10000002` and is a DIFFERENT ENCODING, not a re-framing: a **five-byte**
header (`u32` signature then a `u8` version), one-byte record headers, a
Huffman-coded 4x4-transform height field, and no tag 9 at all -- the client bakes
the lightmap from tag 0's sun elevation. Row 46196's stripped terrain is 2,123
bytes against 7,165 Bloated. `from_chunk()` refuses it loudly rather than
half-parsing it; **`strippedterrain.py` decodes it**, and agrees with this module
on every height sample of every map.

*The two sentences above used to read "signature, then `u16 17`, then
`u16 0x6088`", which is wrong twice: the version is a byte, and 0x6088 is not a
field -- it is the first two bytes of tag 0's body. Reading eight bytes of
header puts the first record three bytes late. Corrected 2026-08-12 by reading
the client's stage-0 handler at 0x00759380, which compares a `u32` and then a
`byte ptr` against 0x11.*

This module produces `bytes`; placing them in an archive is a separate rung
and nothing here opens a file for writing.

    python toolkit/mapdata/terrain.py                        # Kamadan
    python toolkit/mapdata/terrain.py --file-id 0x22E2C      # smallest map
    python toolkit/mapdata/terrain.py --row 7982             # Pre-Searing
    python toolkit/mapdata/terrain.py --row 46196 --records
"""

import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archive import (Archive, ffna_chunks, file_id_table,  # noqa: E402
                     DEFAULT_DAT)
import trnshadow  # noqa: E402  -- tag 7's run coding and its 10x10 tail rule

TERRAIN_CHUNK = 0x20000002
STRIPPED_TERRAIN_CHUNK = 0x10000002

# Both MEASURED on 349/349 as well as being the client's two hard gates. The
# version compare is full-width u32 in the client, and the high 16 bits are zero
# on 349/349, so 0x00110000 would be rejected.
SIGNATURE = 0x87821134
VERSION = 17

HEADER = struct.Struct("<II")          # 8 bytes. THE PATHING CHUNK'S IS 12.
RECORD = struct.Struct("<BI")          # 5 bytes, tag first, unaligned
TAG0 = struct.Struct("<IIffHff")       # 26 bytes: 4+4+4+4+2+4+4, no padding
TAG3B = struct.Struct("<B4f")          # 17 bytes: the optional second tag 3
BLOCK_K = struct.Struct("<I")

# The client's CHUNK_SIZE, MEASURED from the binary twice (TrnCodecHeight:166/167
# test against 0x1f; TrnChunkBox:150 compares against 341 = (4**5-1)/3).
CHUNK_SIZE = 32
CELL_PITCH = 96.0                      # world units per cell, a compile-time constant
CHUNK_PITCH = CHUNK_SIZE * CELL_PITCH  # 3072.0
SHADOW_TAIL = 128
CELL_BITS = CHUNK_SIZE * CHUNK_SIZE     # 1,024 tail bits, one per cell
MAX_CELLS = 1 << 24                    # the loader's own area cap, dimX*dimY
ANGLE_MAX = 1.5707963705062866         # the client's gate constant, bit-exact
TABLE_MASK = 0x7F                      # tag 5's bytes are masked & 0x7F

TAG_DIMS = 0
TAG_HEIGHT = 1
TAG_TILE = 2
TAG_BITS = 3
TAG_TABLE_A = 4
TAG_TABLE_B = 5
TAG_SHADOW = 7
TAG_SHADE = 9
TERMINATOR = 255

# The client's step table, in the client's order. There is no dispatch loop:
# each step demands one tag. The ninth step is the only one that may miss.
REQUIRED_TAGS = (TAG_DIMS, TAG_HEIGHT, TAG_TILE, TAG_TABLE_A, TAG_TABLE_B,
                 TAG_BITS, TAG_SHADE, TAG_SHADOW)
OPTIONAL_TAG = TAG_BITS
SEQUENCE_SHORT = REQUIRED_TAGS + (TERMINATOR,)                 # 325 maps
SEQUENCE_LONG = REQUIRED_TAGS + (OPTIONAL_TAG, TERMINATOR)     # 24 maps


class ShadowBlock:
    """One 32x32 tile's worth of tag-7 data: `{u32 k, k bytes, 128 bytes}`.

    **DECODED, not carried.** The authoritative member is `rows` -- 272 ints,
    bit x of row y being shadow sample (x, y) of a 272x272 bitmap covering this
    tile at 8 samples per cell plus a one-cell skirt. Both stored fields are
    regenerated from it: the payload by `trnshadow.encode_rows` and the 128-byte
    tail by `trnshadow.tail_from_rows`, the latter being 1024 bits MSB-first
    where cell (cx, cy) is set exactly when all 100 samples of its 10x10 window
    are. Corpus: **59,051 of 59,051 payloads and 59,051 of 59,051 tails
    reproduce byte-identically**, and the 8x8 and 12x12 window controls do not
    (they miss 1,562,798 and 611,928 bits).

    This class used to carry both members opaquely, and the docstring said so.
    That made tag 7 the single largest carried block in the round-trip -- so a
    349/349 result was proving the block walk and saying nothing about shadows.
    It is kept in the history because the distinction is the point: a round-trip
    over carried bytes is a comparison of a value with itself.

    `k` ranges 544..13,332 over 4,546 distinct values and is never zero in the
    corpus. A set bit means IN SHADOW -- checked against tag 9's lightmap
    (mean shade 186.0 flagged against 236.6 not), not assumed. What CASTS the
    shadow is NOT established: a terrain-only raycast predicts the flag only
    weakly (41.9% against a 33.6% base rate), which is consistent with props
    being baked in, but that is INFERRED.
    """

    __slots__ = ("rows",)

    def __init__(self, rows):
        self.rows = list(rows)

    @classmethod
    def from_bytes(cls, payload, tail):
        """Decode a stored block, and refuse one whose tail its rows disprove.

        The tail is derivable, so a mismatch means our reading of either the run
        coding or the 10x10 window rule is wrong for this block. Raising is the
        point -- a decoder that quietly kept the stored tail would re-encode
        byte-identically and hide the disagreement, which is exactly the
        carried-bytes trap this class was rewritten to escape.
        """
        rows = trnshadow.decode_rows(payload)
        derived = trnshadow.tail_from_rows(rows)
        if bytes(derived) != bytes(tail):
            # tail_disagreement returns a COUNT of wrong cell bits, not a list.
            # The first version of this line called len() on it and turned a
            # clean refusal into a TypeError -- an error path nothing exercised,
            # which is the whole reason the refusal now has a test.
            wrong = trnshadow.tail_disagreement(rows, tail)
            raise ValueError(f"tag 7 tail disagrees with its own bitmap in "
                             f"{wrong} of {CELL_BITS} cell bits")
        return cls(rows)

    @property
    def payload(self):
        return trnshadow.encode_rows(self.rows)

    @property
    def tail(self):
        return trnshadow.tail_from_rows(self.rows)

    def __len__(self):
        return BLOCK_K.size + len(self.payload) + SHADOW_TAIL

    def __eq__(self, other):
        return isinstance(other, ShadowBlock) and self.rows == other.rows

    def __repr__(self):
        lit = sum(bin(r).count("1") for r in self.rows)
        return f"<ShadowBlock {lit}/{trnshadow.BLOCK_SAMPLES} in shadow>"


class Terrain:
    """One map's terrain grid, decoded far enough to rebuild it byte for byte.

    Field names carry their offsets where the meaning is unknown, because a
    confident name is a claim and three of the tag-0 fields have none we can
    support. See the module docstring for which of these the round-trip is
    actually evidence about.
    """

    __slots__ = ("signature", "version", "dim_x", "dim_y", "chunk_distance",
                 "angle", "tex_word", "tex_f12", "tex_f16", "heights", "tiles",
                 "table_a", "table_b", "bits", "shade", "shadow", "tag3b",
                 "order")

    def __init__(self, dim_x, dim_y, heights, tiles, table_a, table_b, bits,
                 shade, shadow, chunk_distance=8 * CHUNK_PITCH, angle=0.0,
                 tex_word=0, tex_f12=0.5, tex_f16=0.5, tag3b=None,
                 order=SEQUENCE_SHORT, signature=SIGNATURE, version=VERSION):
        self.signature = signature
        self.version = version
        self.dim_x = dim_x
        self.dim_y = dim_y
        self.chunk_distance = chunk_distance   # tag 0 +0x08, in whole chunks
        self.angle = angle                     # tag 0 +0x0C, radians
        self.tex_word = tex_word               # tag 0 +0x10, u16
        self.tex_f12 = tex_f12                 # tag 0 +0x12, unaligned f32
        self.tex_f16 = tex_f16                 # tag 0 +0x16, unaligned f32
        self.heights = heights                 # list[float], dim_x*dim_y
        self.tiles = bytes(tiles)              # u8 per cell, index into table_a
        self.table_a = bytes(table_a)          # tag 4, n entries
        self.table_b = bytes(table_b)          # tag 5, the same n entries
        self.bits = bytes(bits)                # tag 3, 2 bits/cell, opaque order
        self.shade = bytes(shade)              # tag 9, u8 per cell, meaning open
        self.shadow = list(shadow)             # tag 7, list[ShadowBlock]
        self.tag3b = tag3b                     # None, or (u8, (f32,f32,f32,f32))
        self.order = tuple(order)

    # -- derived shape ---------------------------------------------------

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
        """Tag 7's block count, from DIMS -- the file never states it."""
        return self.chunks_x * self.chunks_y

    @property
    def extent(self):
        """World size implied by the grid: `dims * 96.0` on each axis.

        MEASURED against a different chunk: the Map Parameters rect divided by
        these dims gives exactly (96.0, 96.0) on 349/349 maps.
        """
        return self.dim_x * CELL_PITCH, self.dim_y * CELL_PITCH

    @staticmethod
    def index(gx, gy, dim_x):
        """Where cell (gx, gy) sits in tags 1/2/9. Grid row 0 is world maxY.

        MEASURED, but not by this module and not by its test -- the evidence is
        FINDINGS 4's corpus-wide cross-chunk test, which compares prop z from
        chunk `0x20000004` against terrain height aligned by the mapRect. This
        tile-row-major / cell-row-major layout is the argmax on 345 of 346 maps
        with props, median 0.504 of props within 100 units against 0.247 for the
        nearest rival and 0.089 for the flat row-major layout upstream implies;
        the `row0 = maxY` orientation beats its y-flip control on 345 of 346.
        **Nothing in the round-trip touches this function**, so a green codec
        test says nothing about it -- the ordering is invisible to a decoder
        that stores the array as it finds it.

        Do NOT confuse this with the client's in-memory stride, which is
        `(dimX>>5)+1` because the client synthesises a `dims+1` vertex column
        and row by replication. Store `dims x dims` and no more.
        """
        return (((gy >> 5) * (dim_x >> 5) + (gx >> 5)) * 1024
                + (gy & 31) * 32 + (gx & 31))

    def height_at(self, gx, gy):
        return self.heights[self.index(gx, gy, self.dim_x)]

    def tile_at(self, gx, gy):
        return self.tiles[self.index(gx, gy, self.dim_x)]

    def bits_at(self, gx, gy):
        """Tag 3's two bits for one cell: the per-cell tile VARIATION selector.

        The record is exactly `dimX*dimY/4` bytes, so two bits per cell is
        arithmetically forced. That the cells are ordered by the same tiled
        index as tags 1/2/9, and that bit pair `i` sits at `(i & 3) * 2`
        within its byte, was INFERRED while the field had no meaning -- and is
        now MEASURED (`studies/terrain/FINDINGS.md` §3.3, 2026-08-14): the
        client's own de-tiler reads the buffer with a shift counter starting
        at 0 stepping `+2 & 7`, which is exactly this, and the corpus's
        cross-byte co-occurrence agrees against the reversed reading (z=31).

        The value selects a 128x128 quadrant of the cell's 256x256 texture:
        1/2/3 force quadrant 1/2/3, 0 means "take the per-cell PRNG's pick"
        (§3.2). `encode()` still never calls this -- the round-trip carries
        tag 3 verbatim -- so the round-trip stays evidence of framing only.
        """
        i = self.index(gx, gy, self.dim_x)
        return (self.bits[i >> 2] >> ((i & 3) * 2)) & 0x3

    def variation(self):
        """Per-cell variation bytes (0..3), DE-TILED to world row-major.

        `out[gy * dimX + gx]` is `bits_at(gx, gy)`. This is the authored
        override only: 0 (the vast majority of cells -- 99.94% over 24 maps)
        means the client draws a quadrant from its per-cell PRNG, which a
        consumer reproduces at render time rather than reading here.
        """
        return bytes(self.bits_at(gx, gy)
                     for gy in range(self.dim_y)
                     for gx in range(self.dim_x))

    # -- decoding --------------------------------------------------------

    @classmethod
    def from_chunk(cls, blob, chunk_id=TERRAIN_CHUNK):
        """Decode, refusing the Stripped chunk by id before looking at bytes."""
        if chunk_id == STRIPPED_TERRAIN_CHUNK:
            raise ValueError(
                "chunk 0x10000002 is the STRIPPED terrain encoding, which is a "
                "different format and not a re-framing of this one: a FIVE-byte "
                "header (u32 signature, u8 version), one-byte record headers, a "
                "Huffman-coded height field and no tag 9. Use "
                "strippedterrain.StrippedTerrain; this module decodes the "
                "Bloated chunk 0x20000002 only.")
        if chunk_id != TERRAIN_CHUNK:
            raise ValueError(f"chunk 0x{chunk_id:08X} is not terrain "
                             f"(0x{TERRAIN_CHUNK:08X})")
        return cls.decode(blob)

    @classmethod
    def decode(cls, blob):
        """Bytes to typed values. Raises on anything it cannot account for.

        Every refusal here is stricter than the client, which is the right way
        round: the client accepts a too-small `size` on eight of the nine
        records and reads a short tag 7 past its end without a bounds check.
        """
        blob = bytes(blob)
        if len(blob) < HEADER.size:
            raise ValueError(f"terrain chunk is {len(blob)} bytes, shorter "
                             f"than its {HEADER.size}-byte header")
        signature, version = HEADER.unpack_from(blob, 0)
        if signature != SIGNATURE:
            raise ValueError(f"terrain signature 0x{signature:08X} != "
                             f"0x{SIGNATURE:08X}")
        if version != VERSION:
            raise ValueError(f"terrain version {version} != {VERSION} "
                             f"(the client compares the full u32)")

        # -- 1. frame the records -----------------------------------------
        records, p = [], HEADER.size
        while p + RECORD.size <= len(blob):
            tag, size = RECORD.unpack_from(blob, p)
            body = p + RECORD.size
            if body + size > len(blob):
                raise ValueError(
                    f"tag {tag} at {p} declares {size} bytes but only "
                    f"{len(blob) - body} remain")
            records.append((tag, body, size))
            p = body + size
            if tag == TERMINATOR:
                break
        if p != len(blob):
            raise ValueError(f"record walk ended at {p} of {len(blob)} bytes")

        order = tuple(t for t, _b, _s in records)
        if order not in (SEQUENCE_SHORT, SEQUENCE_LONG):
            raise ValueError(
                f"tag sequence {order} is not one of the two the client's step "
                f"table accepts: {SEQUENCE_SHORT} or {SEQUENCE_LONG}")
        term_size = records[-1][2]
        if term_size != 0:
            raise ValueError(f"terminator declares {term_size} bytes; every "
                             f"shipped map declares 0")

        by_tag = {}
        for tag, body, size in records:
            by_tag.setdefault(tag, []).append((body, size))

        def one(tag, nth=0):
            body, size = by_tag[tag][nth]
            return body, size

        def want(tag, size, expect, nth=0):
            if size != expect:
                raise ValueError(
                    f"tag {tag}"
                    + (f" (record {nth + 1})" if nth else "")
                    + f" declares {size} bytes; the dims-derived reader "
                      f"consumes {expect}")

        # -- 2. tag 0: dims and the header fields --------------------------
        body, size = one(TAG_DIMS)
        want(TAG_DIMS, size, TAG0.size)
        (dim_x, dim_y, chunk_distance, angle,
         tex_word, tex_f12, tex_f16) = TAG0.unpack_from(blob, body)
        _gate_dims(dim_x, dim_y)
        # The client's own two gates on these floats. NaN passes both in the
        # client (`test ah,5; jnp` lets unordered through); we refuse it,
        # because a NaN we cannot promise to reproduce is worse than a refusal.
        if not chunk_distance >= 0.0:
            raise ValueError(f"tag 0 +0x08 is {chunk_distance!r}; the client "
                             f"gates it >= 0.0")
        if not (0.0 <= angle <= ANGLE_MAX):
            raise ValueError(f"tag 0 angle {angle!r} is outside the client's "
                             f"gate [0.0, {ANGLE_MAX!r}]")

        cells = dim_x * dim_y

        # -- 3. the dims-driven records ------------------------------------
        body, size = one(TAG_HEIGHT)
        want(TAG_HEIGHT, size, cells * 4)
        heights = list(struct.unpack_from(f"<{cells}f", blob, body))

        body, size = one(TAG_TILE)
        want(TAG_TILE, size, cells)
        tiles = blob[body:body + size]

        body, size = one(TAG_TABLE_A)
        n = blob[body] if size else -1
        want(TAG_TABLE_A, size, 1 + n if n >= 0 else -1)
        table_a = blob[body + 1:body + size]

        body, size = one(TAG_TABLE_B)
        nb = blob[body] if size else -1
        if nb != n:
            raise ValueError(f"tag 5 declares {nb} entries, tag 4 declares {n}; "
                             f"they agree on 349 of 349 shipped maps")
        want(TAG_TABLE_B, size, 1 + nb)
        table_b = blob[body + 1:body + size]

        body, size = one(TAG_BITS)
        want(TAG_BITS, size, cells // 4)
        bits = blob[body:body + size]

        body, size = one(TAG_SHADE)
        want(TAG_SHADE, size, cells)
        shade = blob[body:body + size]

        # -- 4. tag 7: the only walked record ------------------------------
        body, size = one(TAG_SHADOW)
        shadow = _decode_shadow(blob, body, size,
                                (dim_x // CHUNK_SIZE) * (dim_y // CHUNK_SIZE))

        # -- 5. the optional second tag 3 ----------------------------------
        tag3b = None
        if order == SEQUENCE_LONG:
            body, size = one(TAG_BITS, 1)
            want(TAG_BITS, size, TAG3B.size, nth=1)
            vals = TAG3B.unpack_from(blob, body)
            # The lead byte is 0x01 on 24 of 24 maps and the client never reads
            # it; the four floats go to TrnTex +0x291C/+0x2920/+0x2928/+0x292C
            # IN RECORD ORDER (an earlier survey transposed them).
            tag3b = (vals[0], vals[1:])

        return cls(dim_x, dim_y, heights, tiles, table_a, table_b, bits, shade,
                   shadow, chunk_distance=chunk_distance, angle=angle,
                   tex_word=tex_word, tex_f12=tex_f12, tex_f16=tex_f16,
                   tag3b=tag3b, order=order, signature=signature,
                   version=version)

    # -- encoding --------------------------------------------------------

    def validate(self):
        """Everything `encode()` refuses, as a list of reasons. Empty is good.

        These are OUR rules, not all of them the client's. Where the client is
        laxer it is said so at the site: it accepts a too-small declared size on
        eight records and reads a short tag 7 past its end. An authoring tool
        that emits what the client tolerates rather than what retail ships is
        writing bytes no shipped map contains.
        """
        bad = []
        if self.signature != SIGNATURE:
            bad.append(f"signature 0x{self.signature:08X} != 0x{SIGNATURE:08X}")
        if self.version != VERSION:
            bad.append(f"version {self.version} != {VERSION}")
        try:
            _gate_dims(self.dim_x, self.dim_y)
        except ValueError as exc:
            bad.append(str(exc))
        if self.order not in (SEQUENCE_SHORT, SEQUENCE_LONG):
            bad.append(f"tag order {self.order} is not one of the two legal "
                       f"sequences")
        if (self.order == SEQUENCE_LONG) != (self.tag3b is not None):
            bad.append("the tag order and the presence of a second tag-3 "
                       "record disagree")
        cells = self.cells
        if len(self.heights) != cells:
            bad.append(f"{len(self.heights)} heights for {cells} cells")
        if len(self.tiles) != cells:
            bad.append(f"{len(self.tiles)} tile indices for {cells} cells")
        if len(self.shade) != cells:
            bad.append(f"{len(self.shade)} tag-9 bytes for {cells} cells")
        if len(self.bits) != cells // 4:
            bad.append(f"{len(self.bits)} tag-3 bytes for {cells // 4} expected")
        if len(self.table_a) != len(self.table_b):
            bad.append(f"tag 4 has {len(self.table_a)} entries and tag 5 has "
                       f"{len(self.table_b)}; they agree on 349 of 349 maps")
        if len(self.table_a) > 0xFF:
            bad.append(f"tag 4's count {len(self.table_a)} does not fit in a u8")
        # Tag 5's bytes are masked & 0x7F by the client, and bit 7 is set on 0
        # of 17,089 corpus bytes. Emitting one would exercise a path no shipped
        # map exercises, so refuse rather than write it.
        high = [i for i, v in enumerate(self.table_b) if v & ~TABLE_MASK]
        if high:
            bad.append(f"tag 5 byte(s) {high[:4]} have bit 7 set; the client "
                       f"masks it away and 0 of 17,089 corpus bytes set it")
        if self.tiles and self.table_a and max(self.tiles) >= len(self.table_a):
            bad.append(f"tile index {max(self.tiles)} indexes past tag 4's "
                       f"{len(self.table_a)} entries")
        if len(self.shadow) != self.block_count:
            bad.append(f"{len(self.shadow)} tag-7 blocks for "
                       f"{self.block_count} 32x32 tiles")
        # The tail is DERIVED from the bitmap now, so its length cannot be wrong
        # and checking it would be a check that cannot fail. What can be wrong is
        # the bitmap's shape, which is what the codec is entitled to assume.
        wrong_rows = sum(1 for b in self.shadow
                         if len(b.rows) != trnshadow.BLOCK_EDGE)
        if wrong_rows:
            bad.append(f"{wrong_rows} tag-7 block(s) do not hold "
                       f"{trnshadow.BLOCK_EDGE} bitmap rows")
        wide = sum(1 for b in self.shadow
                   for r in b.rows if r >> trnshadow.BLOCK_EDGE)
        if wide:
            bad.append(f"{wide} tag-7 bitmap row(s) carry bits past sample "
                       f"{trnshadow.BLOCK_EDGE - 1}")
        return bad

    def encode(self):
        """Typed values back to bytes. The whole point of this module.

        Every record's declared size is `len(payload)`. Nothing in this chunk
        stores a size a naive encoder would get wrong -- the tag-11 trap in
        `pathmap.py`, where the declared size is twice the data, does not recur
        here. MEASURED: `decode()` refuses any record whose declared size is not
        the length a dims-derived reader consumes, and all 349 maps decode, so
        declared == derived on **3,165 of 3,165 records** (325 maps x 9 records
        plus 24 x 10).
        """
        bad = self.validate()
        if bad:
            raise ValueError("terrain will not encode:\n  " + "\n  ".join(bad))
        out = bytearray(HEADER.pack(self.signature, self.version))
        seen = {}
        for tag in self.order:
            nth = seen.get(tag, 0)
            seen[tag] = nth + 1
            payload = self._payload(tag, nth)
            out += RECORD.pack(tag, len(payload))
            out += payload
        return bytes(out)

    def _payload(self, tag, nth):
        if tag == TAG_DIMS:
            return TAG0.pack(self.dim_x, self.dim_y, self.chunk_distance,
                             self.angle, self.tex_word, self.tex_f12,
                             self.tex_f16)
        if tag == TAG_HEIGHT:
            return struct.pack(f"<{len(self.heights)}f", *self.heights)
        if tag == TAG_TILE:
            return self.tiles
        if tag == TAG_TABLE_A:
            return bytes((len(self.table_a),)) + self.table_a
        if tag == TAG_TABLE_B:
            return bytes((len(self.table_b),)) + self.table_b
        if tag == TAG_BITS:
            if nth == 0:
                return self.bits
            lead, floats = self.tag3b
            return TAG3B.pack(lead, *floats)
        if tag == TAG_SHADE:
            return self.shade
        if tag == TAG_SHADOW:
            # `payload` and `tail` REGENERATE from the bitmap on every access,
            # so bind each once -- the obvious `len(b.payload) ... b.payload`
            # encodes the same block twice.
            out = []
            for b in self.shadow:
                payload = b.payload
                out.append(BLOCK_K.pack(len(payload)) + payload + b.tail)
            return b"".join(out)
        if tag == TERMINATOR:
            return b""
        raise ValueError(f"no encoder for tag {tag}")

    # -- authoring -------------------------------------------------------

    @classmethod
    def blank(cls, dim_x=CHUNK_SIZE, dim_y=CHUNK_SIZE, height=0.0, tiles=3):
        """A flat grid built from nothing, for exercising the encoder.

        What `blank()` is for is the authoring direction of the codec -- encode
        from typed values that never came out of an archive, decode the result
        back, and compare -- which is the one check in this file that needs no
        ArenaNet bytes at all and runs on a bare machine.

        This used to warn that it was NOT CLIENT-LOADABLE because its tag-7
        blocks carried a zero-length payload while `k == 0` occurs in 0 of 59,051
        retail blocks. **That caveat is gone**: the blocks now hold a real
        all-clear shadow bitmap, which the run coder emits as 272 rows of
        `0xFF 0x12` -- `k == 544`, and 544 is exactly the corpus MINIMUM. An
        all-clear tile is what a flat unshadowed grid should have, and retail's
        smallest block agreeing with it to the byte is a pleasant check we did
        not set out to make.

        It is still not a loadable MAP -- that needs the other eighteen chunks --
        but its terrain chunk is no longer the reason.
        """
        _gate_dims(dim_x, dim_y)
        if not 1 <= tiles <= 0xFF:
            raise ValueError(f"tile table of {tiles} entries")
        cells = dim_x * dim_y
        blocks = (dim_x // CHUNK_SIZE) * (dim_y // CHUNK_SIZE)
        return cls(dim_x, dim_y,
                   [float(height)] * cells,
                   bytes(cells),
                   bytes(range(tiles)),
                   bytes(tiles),
                   bytes(cells // 4),
                   bytes(cells),
                   [ShadowBlock([0] * trnshadow.BLOCK_EDGE)
                    for _ in range(blocks)])

    # -- loading ---------------------------------------------------------

    @classmethod
    def load(cls, map_file_id, archive=None, table=None):
        """Open a map's terrain by the file id a server hands the client."""
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
        entry = next(e for e in archive.entries if e.index == row)
        data = archive.read(entry)
        for chunk_id, off, size in ffna_chunks(data):
            if chunk_id in (TERRAIN_CHUNK, STRIPPED_TERRAIN_CHUNK):
                return cls.from_chunk(bytes(data[off:off + size]), chunk_id)
        raise ValueError(f"row {row} has no terrain chunk")

    def __repr__(self):
        return (f"<Terrain {self.dim_x}x{self.dim_y}, "
                f"{len(self.table_a)} tile types, "
                f"{len(self.shadow)} shadow blocks>")


def _gate_dims(dim_x, dim_y):
    """The loader's own two caps. MEASURED: 349/349 satisfy both."""
    if dim_x <= 0 or dim_y <= 0:
        raise ValueError(f"terrain dims {dim_x}x{dim_y}")
    if dim_x % CHUNK_SIZE or dim_y % CHUNK_SIZE:
        raise ValueError(f"terrain dims {dim_x}x{dim_y} are not both multiples "
                         f"of {CHUNK_SIZE}; the client gates on it")
    if dim_x * dim_y > MAX_CELLS:
        raise ValueError(f"terrain area {dim_x * dim_y} exceeds the loader's "
                         f"cap of {MAX_CELLS}")


def _decode_shadow(blob, body, size, blocks):
    """Walk tag 7's blocks. The block count comes from DIMS, not the file.

    The client's loop bounds-checks nothing and reads a short tag 7 past its
    end. This one refuses, and requires the walk to land on the record's
    declared end -- which it does on 59,051 of 59,051 corpus blocks.
    """
    out = []
    p = body
    end = body + size
    for i in range(blocks):
        if p + BLOCK_K.size > end:
            raise ValueError(f"tag 7 block {i} of {blocks}: the record ends "
                             f"after {p - body} of {size} bytes")
        k, = BLOCK_K.unpack_from(blob, p)
        p += BLOCK_K.size
        if p + k + SHADOW_TAIL > end:
            raise ValueError(
                f"tag 7 block {i} of {blocks} declares {k} bytes plus a "
                f"{SHADOW_TAIL}-byte tail, but only {end - p} remain")
        try:
            out.append(ShadowBlock.from_bytes(
                blob[p:p + k], blob[p + k:p + k + SHADOW_TAIL]))
        except ValueError as exc:
            raise ValueError(f"tag 7 block {i} of {blocks}: {exc}") from exc
        p += k + SHADOW_TAIL
    if p != end:
        raise ValueError(f"tag 7 block walk ended at {p - body} of {size} "
                         f"bytes after {blocks} blocks")
    return out


def _main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--file-id", default=None,
                    help="map file id, e.g. 0x345CC (Kamadan, the default)")
    ap.add_argument("--row", type=int, default=None,
                    help="MFT row instead of a file id")
    ap.add_argument("--records", action="store_true",
                    help="list every record with its declared size")
    args = ap.parse_args()

    import time
    with Archive(args.dat) as ar:
        t0 = time.perf_counter()
        if args.row is not None:
            trn = Terrain.from_row(args.row, ar)
            who = f"row {args.row}"
        else:
            fid = int(args.file_id, 0) if args.file_id else 0x345CC
            trn = Terrain.load(fid, archive=ar)
            who = f"file id 0x{fid:X}"
        dt = time.perf_counter() - t0

        ex, ey = trn.extent
        lo, hi = min(trn.heights), max(trn.heights)
        exact = sum(1 for h in trn.heights if h == int(h))
        blank = sum(1 for b in trn.shadow if not b.payload)
        print(f"{who}: terrain {trn.dim_x}x{trn.dim_y} cells, loaded in "
              f"{dt:.2f}s")
        print(f"  extent        {ex:.0f} x {ey:.0f} world units "
              f"({CELL_PITCH:.0f} per cell, {trn.chunks_x}x{trn.chunks_y} "
              f"chunks)")
        print(f"  height        {lo:.0f} .. {hi:.0f}   "
              f"{exact}/{len(trn.heights)} exact integers")
        print(f"  tag 0         +0x08 {trn.chunk_distance:.1f} "
              f"(= {max(3, int(trn.chunk_distance / CHUNK_PITCH))} chunks)  "
              f"angle {trn.angle!r}")
        print(f"                u16 {trn.tex_word}  +0x12 {trn.tex_f12!r}  "
              f"+0x16 {trn.tex_f16!r}")
        print(f"  tile types    {len(trn.table_a)}  "
              f"(max index used {max(trn.tiles) if trn.tiles else '-'})")
        print(f"  tag 3         {len(trn.bits)} bytes, "
              f"{'all zero' if not any(trn.bits) else 'non-zero'}")
        print(f"  tag 7         {len(trn.shadow)} blocks, "
              f"{blank} with an empty payload")
        if trn.tag3b is not None:
            print(f"  tag 3'        lead {trn.tag3b[0]}  floats {trn.tag3b[1]}")
        print(f"  sequence      {trn.order}")
        if args.records:
            seen = {}
            for tag in trn.order:
                nth = seen.get(tag, 0)
                seen[tag] = nth + 1
                print(f"    tag {tag:3d}   "
                      f"{len(trn._payload(tag, nth))} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
