"""Check the STRIPPED terrain codec: chunk `0x10000002`, decode and encode.

THE HEADLINE IS NOT THE ROUND TRIP. It is section 4: the height field this codec
pulls out of a Huffman-coded bit stream has to equal, sample for sample, the one
`terrain.Terrain` reads out of the BLOATED chunk -- a different encoding, written
by a different subsystem, that this module never looks at. 212,992 float32
samples per map predicted from compressed bits is an oracle a codec cannot force.
The byte-identical re-encode is the weaker claim and is reported beside it.

WHAT A MEMCPY WOULD SCORE. A decoder that stashed the blob and handed it back
from `encode()` prints a perfect round trip on every file it can walk. Section 3
builds exactly that saboteur, runs it, and requires the round-trip checks to go
GREEN for it and the mutation checks to go RED -- so the file states, from a live
measurement rather than a comment, which of its own checks are load-bearing.

THE NAMED CONTROL. `_inverse4`'s matrix has determinant 8, so a 4x4 sample block
is representable only on an index-8^8 sublattice of Z^16. An encoder that
TRUNCATED the inverse instead of refusing would move a height by a fraction of a
unit, encode cleanly, and round-trip -- the byte-identity headline cannot see it,
because such an encoder is only ever run on retail blocks that are already on the
lattice. Section 1 builds the truncating encoder, feeds both it and
`_forward4` an off-lattice block, and requires one to answer and the other to
refuse.

WHAT IS RECONSTRUCTED. Section 8 asserts the split rather than printing it. Every
coding parameter in the file -- both bases, both widths, the count width, the
table widths, the symbol set, every alignment pad -- is re-derived on encode, and
`decode()` REFUSES a file whose stored parameter disagrees with what the samples
need. So 349 green decodes are 349 assertions that the derivation is right, not
349 comparisons of a value with itself. The one carried thing is which code
length each symbol gets, and section 2 says why that cannot be otherwise.

A MISSING VAULT IS A FAILURE, NOT A SKIP. Sections 0-3 still run and are still
printed, but a run with no archive has measured nothing about ArenaNet's format,
and the floor turns that into the FAIL it is.

    python toolkit/mapdata/test_strippedterrain.py
    python toolkit/mapdata/test_strippedterrain.py --sample 20
    python toolkit/mapdata/test_strippedterrain.py --all    # 349 maps
"""

import argparse
import math
import os
import random
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks  # noqa: E402
from mapchunks import MapIndex, is_map_head  # noqa: E402
import strippedterrain as stx  # noqa: E402
from strippedterrain import (BitReader, BitWriter, HeightBlock,  # noqa: E402
                             HuffmanTable, StrippedTerrain, Undecodable,
                             snap_block, _forward4, _inverse4)
import terrain  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

# MEASURED on this archive 2026-08-12 by a full 349-map sweep. Population
# assertions, not decoration: they are what stops an empty sample or a wrong row
# filter from printing "3 of 3" and going green.
CORPUS_MAPS = 349

# The Stripped chunk's front, pinned against the trap. `terrain.py`'s own
# docstring read this as an eight-byte header ("signature, then u16 17, then
# u16 0x6088") and 0x6088 is not a field at all -- it is the first two bytes of
# tag 0's body. Five, one, nine.
HEADER_BYTES = 5
TAG0_BODY = 9
HEIGHT_RECORD_AT = HEADER_BYTES + 1 + TAG0_BODY      # 15

# The client's own gates on tag 0, at 0x00758D02 and 0x00758D30.
DIMS_MARKER = 0x80
STORED_PITCH = 96

# `terrain.py`'s two retired angle formulations, kept here as the controls that
# must FAIL. That file records `float32(b*pi/508)` reproducing 39 of 55 stored
# bit patterns and `float32(1.5707963705062866*b/254)` reproducing 53 of 55; the
# client computes `float32(b * (double)(float)(90pi) / 45720.0)`, which is
# `stx.ANGLE_TABLE`. If any of the three agreed everywhere the correction would
# be empty, so the index counts below are MEASURED and asserted.
RETIRED_ANGLE = [struct.unpack("<f", struct.pack("<f", b * math.pi / 508.0))[0]
                 for b in range(256)]
PREFERRED_ANGLE = [struct.unpack("<f", struct.pack(
    "<f", 1.5707963705062866 * b / 254.0))[0] for b in range(256)]
RETIRED_DIFFERS = 88            # of 256 indices
PREFERRED_DIFFERS = 3

# A height field authored freely is essentially never on the transform's
# lattice. MEASURED over the fields section 1 builds: the projection moves no
# sample by more than this, against a 96.0-unit cell pitch.
SNAP_WORST = 6

DEFAULT_SAMPLE = 6


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=DEFAULT_SAMPLE)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dat", default=None)
    return ap.parse_args()


# ---------------------------------------------------------------- helpers

class PlainBits:
    """An MSB-first bit reader written here out of `int.from_bytes`.

    It imports nothing from the module under test. Section 3 uses it to read
    back the block header fields that `encode()` emitted, so a claim that a
    width field moved is measured by a second implementation rather than by
    asking the codec to confirm itself.
    """

    def __init__(self, buf, bitpos=0):
        self.buf = buf
        self.pos = bitpos

    def take(self, n):
        first = self.pos >> 3
        span = ((self.pos & 7) + n + 7) >> 3
        word = int.from_bytes(self.buf[first:first + span], "big")
        shift = span * 8 - ((self.pos & 7) + n)
        self.pos += n
        return (word >> shift) & ((1 << n) - 1)


def block_header(blob, at=HEIGHT_RECORD_AT + 1):
    """(dcBase, dcBits, escBase, escBits) of the first block, read independently."""
    br = PlainBits(blob, at * 8)
    dc = br.take(16)
    dc -= 0x10000 if dc >= 0x8000 else 0
    dcb = br.take(4) + 1
    esc = br.take(16)
    esc -= 0x10000 if esc >= 0x8000 else 0
    escb = br.take(4) + 1
    return dc, dcb, esc, escb


class Memcpy(StrippedTerrain):
    """The saboteur: a codec that keeps the bytes it decoded and returns them.

    It round-trips every file it can walk, understands nothing, and section 3
    runs it to show which checks notice.
    """

    _blob = None

    @classmethod
    def decode(cls, blob):
        st = StrippedTerrain.decode(blob)
        out = cls(st.dim_x, st.dim_y, st.blocks, st.tiles, st.table_a,
                  st.table_b, st.bits, shadow=st.shadow,
                  chunk_units=st.chunk_units, angle_index=st.angle_index,
                  tex_word=st.tex_word, tex_f12_index=st.tex_f12_index,
                  tex_f16_index=st.tex_f16_index, tag3b=st.tag3b)
        out._blob = bytes(blob)
        return out

    def encode(self):
        return self._blob


def truncating_forward4(w, x, y, z):
    """`_forward4` with the refusal replaced by a floor. The named control.

    This is what the module would look like if the divisibility guard were a
    `//` instead of a raise: exact on the lattice, quietly wrong off it.
    """
    lo, hi = w + x, y + z
    return (lo + hi) // 4, (hi - lo) // 4, (x - w) // 2, (z - y) // 2


def author(dim_x=32, dim_y=32, seed=11, amp=400):
    """A representable map built from nothing. No vault, no archive."""
    rng = random.Random(seed)
    cells = dim_x * dim_y
    heights = [float(int(amp * math.sin(i / 37.0)
                         + (amp // 3) * math.cos(i / 13.0)))
               for i in range(cells)]
    tiles = bytes(rng.randrange(3) for _ in range(cells))
    return StrippedTerrain.build(dim_x, dim_y, heights, tiles=tiles,
                                 table_a=b"\x00\x01\x02",
                                 table_b=b"\x01\x03\x05")


def corpus(ar):
    mi = MapIndex(ar)
    return sorted((e.index, mi.partner(e).index)
                  for e in ar.entries if is_map_head(e))


def chunks_for(ar, head, partner):
    he = next(x for x in ar.entries if x.index == head)
    pe = next(x for x in ar.entries if x.index == partner)
    bloated = stripped = None
    data = ar.read(pe)
    for cid, off, size in ffna_chunks(data):
        if cid == stx.STRIPPED_TERRAIN_CHUNK:
            stripped = bytes(data[off:off + size])
    data = ar.read(he)
    for cid, off, size in ffna_chunks(data):
        if cid == terrain.TERRAIN_CHUNK:
            bloated = bytes(data[off:off + size])
    return stripped, bloated


# ---------------------------------------------------------------- sections

def section0(check):
    print("\n-- 0. the bit reader and writer (TrnBitStore.h) ------------------")
    bw = BitWriter()
    bw.put(0b101, 3)
    bw.put(0x2A, 8)
    bw.put(0b11111, 5)
    got = bw.bytes()
    # 101 00101010 11111 -> 1010 0101 0101 1111 -> A5 5F. Written out by hand.
    check(got == bytes([0xA5, 0x5F]), "writer packs MSB-first",
          f"{got.hex()} want a55f")
    br = BitReader(got)
    check((br.take(3), br.take(8), br.take(5)) == (0b101, 0x2A, 0b11111),
          "reader is the writer's inverse")
    check(br.consumed() == 2, "consumed() rounds up to whole bytes",
          f"{br.consumed()}")

    br = BitReader(bytes(8))
    try:
        br.take(32)
        ok = False
    except Undecodable:
        ok = True
    check(ok, "a 32-bit read is refused (TrnBitStore.h:52 bitCount < 32)")

    br = BitReader(bytes([0xFF, 0x00]))
    br.take(3)
    try:
        br.align()
        ok = False
    except Undecodable:
        ok = True
    check(ok, "a non-zero alignment pad is refused")

    br = BitReader(bytes([0xE0, 0x00]))
    br.take(3)
    br.align()
    check(br.pos == 8, "a zero pad aligns to the next byte", f"pos {br.pos}")

    br = BitReader(bytes([0xFF]))
    try:
        br.take(9)
        ok = False
    except Undecodable:
        ok = True
    check(ok, "a read past the record end is refused")

    bw = BitWriter()
    try:
        bw.put(4, 2)
        ok = False
    except ValueError:
        ok = True
    check(ok, "the writer refuses a value that overflows its width")

    bw = BitWriter()
    bw.put(1, 1)
    try:
        bw.bytes()
        ok = False
    except ValueError:
        ok = True
    check(ok, "the writer refuses to emit an unaligned stream")


def section1(check):
    print("\n-- 1. the 4x4 transform, and the truncation control --------------")
    rng = random.Random(3)
    bad = 0
    for _ in range(400):
        co = [rng.randint(-900, 900) for _ in range(4)]
        fin = _inverse4(*co)
        if list(_forward4(*fin)) != co:
            bad += 1
    check(bad == 0, "forward4 inverts inverse4 over 400 random coefficient sets",
          f"{bad} disagreements")

    off = (0, 1, 0, 0)          # w != x mod 2, so not on the lattice
    try:
        _forward4(*off)
        refused = False
    except ValueError:
        refused = True
    check(refused, "forward4 REFUSES a four-vector off the lattice")
    trunc = truncating_forward4(*off)
    check(list(_inverse4(*trunc)) != list(off),
          "the truncating encoder would silently move the samples",
          f"{off} -> {_inverse4(*trunc)}")

    onlat = _inverse4(7, -3, 11, 2)
    check(truncating_forward4(*onlat) == _forward4(*onlat),
          "the two agree exactly ON the lattice, which is why byte-identity "
          "cannot see the difference")

    flat = [0] * 1024
    snapped, worst = snap_block(flat)
    check(snapped == flat and worst == 0, "snap_block is the identity on a flat "
          "field")

    # A whole tile built the way the DECODER builds one, then run back through
    # `_coefficients`. This is the block-level round trip, and it is what makes
    # the 2-D claim (columns then rows, and the inverse in the other order) a
    # check rather than an assumption.
    want = [[rng.randint(-400, 400) for _ in range(16)] for _ in range(64)]
    samples = [0] * 1024
    for k, co in enumerate(want):
        by, bx = divmod(k, 8)
        mid = [0] * 16
        for i in range(4):
            (mid[i], mid[i + 4], mid[i + 8],
             mid[i + 12]) = _inverse4(co[i], co[i + 4], co[i + 8], co[i + 12])
        for r in range(4):
            row = _inverse4(*mid[4 * r:4 * r + 4])
            off = (by * 4 + r) * 32 + bx * 4
            samples[off:off + 4] = row
    got = HeightBlock(samples, None)._coefficients()
    check(got == want,
          "a whole 32x32 tile of transform outputs gives its 64x16 coefficients "
          "back exactly", f"{sum(1 for a, b in zip(got, want) if a != b)} "
          f"sub-blocks disagree")

    rough = [rng.randint(-3000, 3000) for _ in range(1024)]
    snapped, worst = snap_block(rough)
    check(snapped != rough, "snap_block moves an off-lattice field")
    check(worst <= SNAP_WORST, f"snap_block's worst move is <= {SNAP_WORST} "
          f"world units against a 96.0 cell pitch", f"{worst}")
    again, worst2 = snap_block(snapped)
    check(again == snapped and worst2 == 0,
          "snapping a snapped field changes nothing")
    HeightBlock(snapped, None)._coefficients()
    check(True, "a snapped field is exactly representable")


def section2(check):
    print("\n-- 2. the canonical Huffman table --------------------------------")
    table = HuffmanTable([0, 0, 2, 2] + [0] * 15, [5, 9, 300, 1023])
    check(table.count_width == 2, "count width is re-derived from the counts",
          f"{table.count_width}")
    bw = BitWriter()
    table.write(bw)
    bw.align()
    br = BitReader(bw.bytes())
    back = HuffmanTable.read(br)
    check(back == table, "the table survives its own bit encoding")

    bw = BitWriter()
    for sym in (1023, 5, 300, 9, 5):
        table.encode(bw, sym)
    bw.align()
    br = BitReader(bw.bytes())
    got = [table.decode(br) for _ in range(5)]
    check(got == [1023, 5, 300, 9, 5], "codes round-trip through the reader",
          f"{got}")

    bw = BitWriter()
    bw.put(1, 8)                    # count width 2, and 2 is what the counts need
    for length in range(1, 19):
        bw.put(2 if length == 2 else 0, 2)
    bw.put(7, 10)
    bw.put(7, 10)                   # the same symbol twice
    bw.align()
    try:
        HuffmanTable.read(BitReader(bw.bytes()))
        ok = False
    except Undecodable:
        ok = True
    check(ok, "a symbol list that repeats a symbol is refused on read")

    bw = BitWriter()
    bw.put(1, 8)                    # claim a count width of 2 ...
    for length in range(1, 19):
        bw.put(1 if length == 2 else 0, 2)   # ... whose largest count needs 1
    bw.put(7, 10)
    bw.align()
    try:
        HuffmanTable.read(BitReader(bw.bytes()))
        ok = False
    except Undecodable:
        ok = True
    check(ok, "a stored count width its own counts contradict is refused")

    freq = {5: 40, 9: 20, 300: 3, 1023: 1}
    built = HuffmanTable.for_frequencies(freq)
    check(set(built.symbols) == set(freq),
          "for_frequencies covers exactly the symbols it was given")
    lens = {s: built._code[s][1] for s in freq}
    check(lens[5] <= lens[300] and lens[9] <= lens[300],
          "a frequent symbol never gets a longer code than a rare one", str(lens))
    check(sum(2.0 ** -lens[s] for s in freq) <= 1.0 + 1e-9,
          "the built code satisfies Kraft")
    # `for_frequencies` is OURS, not ArenaNet's, so the round trip must not be
    # secretly a claim about it. Asked of the SYNTAX TREE rather than of a
    # comment: nothing on the decode/encode path may reach it. A grep would
    # match the definition and the docstrings too.
    import ast
    tree = ast.parse(open(stx.__file__, encoding="utf-8").read())
    callers = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for inner in ast.walk(node):
                if (isinstance(inner, ast.Attribute)
                        and inner.attr == "for_frequencies"):
                    callers.add(node.name)
    check(callers == {"from_samples"},
          "for_frequencies is reached from from_samples and nowhere else, so "
          "neither decode() nor encode() is a claim about our Huffman "
          "construction", f"callers: {sorted(callers)}")

    nret = sum(1 for b in range(256) if RETIRED_ANGLE[b] != stx.ANGLE_TABLE[b])
    npre = sum(1 for b in range(256) if PREFERRED_ANGLE[b] != stx.ANGLE_TABLE[b])
    check(nret == RETIRED_DIFFERS,
          f"the client's angle expression differs from float32(b*pi/508) at "
          f"{RETIRED_DIFFERS} of 256 indices", f"{nret}")
    check(npre == PREFERRED_DIFFERS,
          f"and from terrain.py's preferred float32(1.5707963705062866*b/254) "
          f"at {PREFERRED_DIFFERS}", f"{npre}")


def section3(check):
    print("\n-- 3. a chunk authored from nothing, and the memcpy saboteur ------")
    st = author()
    blob = st.encode()
    back = StrippedTerrain.decode(blob)
    check(back.encode() == blob, "an authored chunk round-trips byte-identically")
    check(back.heights == st.heights, "and its height field survives",
          f"{len(st.heights)} samples")
    check(back.tiles == st.tiles and back.table_a == st.table_a
          and back.table_b == st.table_b and back.bits == st.bits,
          "and its tiles, tables and tag-3 bits survive")
    check(back.dim_x == 32 and back.dim_y == 32
          and back.chunk_distance == st.chunk_distance
          and back.angle == st.angle, "and its tag-0 fields survive")

    # The front, read with literal offsets by this file rather than the module.
    sig, ver = struct.unpack_from("<IB", blob, 0)
    check(sig == 0x87821134 and ver == 0x11,
          f"the header is {HEADER_BYTES} bytes: u32 signature then a u8 version")
    check(blob[HEADER_BYTES] == 0, "tag 0's record header is ONE byte")
    packed = struct.unpack_from("<I", blob, HEADER_BYTES + 1)[0]
    check(packed & 0xC0 == DIMS_MARKER, "tag 0 carries the 0x80 marker bits")
    check((packed >> 8) & 0xFF == STORED_PITCH,
          "tag 0 stores the cell pitch, and it is 96")
    check(blob[HEIGHT_RECORD_AT] == 1,
          f"the height record starts at byte {HEIGHT_RECORD_AT}; an eight-byte "
          f"header would put it three bytes late")

    # -- the mutation control -------------------------------------------
    # Two magnitudes, because they catch different things. One sample moved is
    # the smallest edit the format can express and must survive the whole
    # Huffman path; a whole sub-block dropped moves the block header's own
    # dcBase and dcBits, which is the field a size-replaying encoder would get
    # wrong. A version with only the first passes an encoder that stores the
    # header it decoded -- so both are here on purpose.
    base_dc, base_bits, _, _ = block_header(blob)
    st2 = StrippedTerrain.decode(blob)
    one = list(st2.blocks[0].samples)
    one[500] += 4000
    st2.blocks[0].samples = snap_block(one)[0]
    st2.blocks[0].table = HeightBlock.from_samples(
        st2.blocks[0].samples, snap=False).table
    moved = st2.encode()
    check(moved != blob, "moving one sample by 4000 changes the emitted bytes")
    reread = StrippedTerrain.decode(moved)
    check(reread.blocks[0].samples == st2.blocks[0].samples,
          "and the moved field decodes back to the moved values")

    st4 = StrippedTerrain.decode(blob)
    deep = list(st4.blocks[0].samples)
    for r in range(4):
        for c in range(4):
            deep[r * 32 + c] -= 8000
    st4.blocks[0].samples = snap_block(deep)[0]
    st4.blocks[0].table = HeightBlock.from_samples(
        st4.blocks[0].samples, snap=False).table
    dropped = st4.encode()
    d_dc, d_bits, _, _ = block_header(dropped)
    check(d_dc < base_dc and d_bits > base_bits,
          "dropping one 4x4 sub-block by 8000 moves the block's own dcBase and "
          "widens dcBits, read back by this file's bit reader",
          f"{(base_dc, base_bits)} -> {(d_dc, d_bits)}")
    check(StrippedTerrain.decode(dropped).blocks[0].samples
          == st4.blocks[0].samples, "and that field decodes back too")

    # a coefficient that cannot be a symbol has to take the escape
    st3 = StrippedTerrain.build(32, 32, [float(40000 * (i % 2))
                                         for i in range(1024)])
    big = st3.encode()
    check(StrippedTerrain.decode(big).heights == st3.heights,
          "a field whose coefficients overflow the alphabet escapes and "
          "survives")

    # -- the saboteur ---------------------------------------------------
    sab = Memcpy.decode(blob)
    check(sab.encode() == blob,
          "SABOTEUR: a codec that returns the bytes it read passes the round "
          "trip")
    sab.blocks[0].samples = st4.blocks[0].samples
    sab.blocks[0].table = st4.blocks[0].table
    check(sab.encode() == blob,
          "SABOTEUR: and it is INSENSITIVE to the dropped sub-block -- which is "
          "the check that catches it")
    check(block_header(sab.encode()) == block_header(blob),
          "SABOTEUR: its block header never moves")

    # -- refusals -------------------------------------------------------
    def refuses(mutate, label):
        b = bytearray(blob)
        mutate(b)
        try:
            StrippedTerrain.decode(bytes(b))
            ok = False
        except (Undecodable, ValueError):
            ok = True
        check(ok, f"refused: {label}")

    refuses(lambda b: b.__setitem__(0, 0x00), "a wrong signature")
    refuses(lambda b: b.__setitem__(4, 0x10), "a wrong version")
    refuses(lambda b: b.__setitem__(HEADER_BYTES, 1), "a wrong first tag")
    refuses(lambda b: b.__setitem__(HEADER_BYTES + 1,
                                    b[HEADER_BYTES + 1] & 0x3F),
            "tag 0's marker bits cleared")
    refuses(lambda b: b.__setitem__(HEADER_BYTES + 2, 95),
            "a cell pitch that is not 96")
    refuses(lambda b: b.__setitem__(len(b) - 1, 0xFE), "a missing terminator")
    refuses(lambda b: b.__delitem__(slice(len(b) - 40, len(b))),
            "a truncated chunk")

    try:
        StrippedTerrain.from_chunk(blob, terrain.TERRAIN_CHUNK)
        ok = False
    except Undecodable:
        ok = True
    check(ok, "refused: the BLOATED chunk id")
    try:
        terrain.Terrain.decode(blob)
        ok = False
    except ValueError:
        ok = True
    check(ok, "refused: terrain.Terrain will not decode these bytes")

    cen = st.census()
    check(cen["reconstructed"] + cen["carried"] == cen["total"],
          "the census accounts for every byte", str(cen))


def section4to8(check, led, args, dat):
    missing = rt_ok = 0
    height_ok = field_ok = shadow_ok = 0
    angle_ok = 0
    retired_seen = retired_wrong = 0
    shade_absent = 0
    carried = total = 0
    n = 0
    t0 = time.perf_counter()
    with Archive(dat) as ar:
        rows = corpus(ar)
        led.ok(len(rows) == CORPUS_MAPS,
               f"the archive holds {CORPUS_MAPS} map pairs", f"{len(rows)}")
        sel = rows if args.all else rows[::max(1, len(rows) //
                                               max(1, args.sample))][:args.sample]
        for head, partner in sel:
            sblob, bblob = chunks_for(ar, head, partner)
            if sblob is None or bblob is None:
                # Never silently: a map whose chunk we could not find would
                # shrink the denominator and make every ratio below read n/n.
                missing += 1
                continue
            n += 1
            st = StrippedTerrain.decode(sblob)
            rt_ok += st.encode() == sblob
            trn = terrain.Terrain.decode(bblob)
            height_ok += st.heights == trn.heights
            field_ok += (st.tiles == trn.tiles and st.table_a == trn.table_a
                         and st.table_b == trn.table_b and st.bits == trn.bits
                         and st.dim_x == trn.dim_x and st.dim_y == trn.dim_y
                         and st.chunk_distance == trn.chunk_distance
                         and st.tex_word == trn.tex_word
                         and st.tex_f12 == trn.tex_f12
                         and st.tex_f16 == trn.tex_f16)
            shadow_ok += (st.shadow is not None
                          and [b.rows for b in st.shadow]
                          == [b.rows for b in trn.shadow])
            angle_ok += st.angle == trn.angle
            if RETIRED_ANGLE[st.angle_index] != stx.ANGLE_TABLE[st.angle_index]:
                retired_seen += 1
                retired_wrong += RETIRED_ANGLE[st.angle_index] != trn.angle
            shade_absent += bytes(trn.shade) not in sblob
            c = st.census()
            carried += c["carried"]
            total += c["total"]
    dt = time.perf_counter() - t0

    print(f"\n-- 4. the oracle: {n} maps against the BLOATED chunk ({dt:.0f}s) --")
    check(n > 0 and missing == 0,
          "every map in the sample carried both chunks, so no ratio below is "
          "over a shrunken denominator", f"{n} maps, {missing} missing")
    check(height_ok == n,
          "every height field equals the one terrain.Terrain reads out of "
          "0x20000002", f"{height_ok}/{n}")
    check(field_ok == n,
          "and so do dims, tiles, both tile tables, tag 3, the chunk distance "
          "and the three texture fields", f"{field_ok}/{n}")
    check(shadow_ok == n,
          "and tag 7 decodes to the same 272x272 bitmaps", f"{shadow_ok}/{n}")

    print("\n-- 5. the round trip ---------------------------------------------")
    check(rt_ok == n, "every stripped chunk re-encodes byte-identically",
          f"{rt_ok}/{n}")

    print("\n-- 6. the sun angle, and terrain.py's retired formula -------------")
    check(angle_ok == n,
          "ANGLE_TABLE reproduces the BLOATED chunk's stored float",
          f"{angle_ok}/{n}")
    if retired_seen:
        check(retired_wrong == retired_seen,
              "CONTROL: on every sampled map whose angle index distinguishes "
              "them, float32(b*pi/508) does NOT -- which is what makes the "
              "correction a correction",
              f"{retired_wrong}/{retired_seen} distinguishing maps")
    else:
        led.skip("the angle control on the corpus",
                 f"none of the {n} sampled maps carries one of the "
                 f"{RETIRED_DIFFERS} distinguishing angle indices; the "
                 f"index-space check in section 2 still ran")

    print("\n-- 7. tag 9 is not in the stripped stream ------------------------")
    check(shade_absent == n,
          "the BLOATED lightmap's bytes do not occur in the stripped chunk at "
          "all; the client bakes it from tag 0's sun elevation",
          f"{shade_absent}/{n}")

    print("\n-- 8. what is reconstructed and what the format stores raw --------")
    frac = 100.0 * (total - carried) / total if total else 0.0
    check(total > 0 and frac > 30.0,
          "over 30% of every stripped chunk is rebuilt rather than carried; "
          "the rest is tags 2 and 3, which the format stores raw",
          f"{total - carried}/{total} = {frac:.2f}%")
    return n


def main():
    args = parse_args()
    print("stripped terrain codec -- chunk 0x10000002")
    led = checks.Ledger("stripped terrain", floor=FLOOR)
    check = checks.adopt(led)

    section0(check)
    section1(check)
    section2(check)
    section3(check)

    dat = args.dat
    if dat is None:
        try:
            dat = os.path.join(str(vaultpath.require_dir("dat_study")), "Gw.dat")
        except (SystemExit, Exception) as exc:
            # require_dir raises SystemExit, which is a BaseException -- catching
            # only Exception here loses the verdict banner entirely and the run
            # exits 1 with no ledger, which reads as a crash rather than as the
            # declared failure it is.
            dat = None
            led.skip("sections 4-8 (the corpus)",
                     f"no vault archive: {str(exc).splitlines()[0]}")
    if dat and os.path.exists(dat):
        section4to8(check, led, args, dat)
    elif dat:
        led.skip("sections 4-8 (the corpus)", f"{dat} does not exist")

    return led.verdict()


# Set from a real green run; see the module docstring. Sections 0-3 alone score
# VAULTLESS, which is under the floor -- a run with no archive has measured
# nothing about ArenaNet's format and must go red.
FLOOR = 66
VAULTLESS = 57

if __name__ == "__main__":
    sys.exit(main())
