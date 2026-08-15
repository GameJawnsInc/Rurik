"""Read and AUTHOR the ATEX texture container.

The point of this module is the writer. Reading ATEX is a solved problem in at
least one other project; authoring one that the retail client accepts is not,
and it is the last thing standing between us and a genuinely new skill icon.

WHAT THIS FILE DOES NOT NEED. It does not implement ArenaNet's compressed
sub-codecs, and it never will unless we want to read retail art back out. Every
level we write carries compression code 0, which the client's decoder sends
down a raw path -- so the bitstream is not authored, it is just blocks.

    ATEX file
        +0x00  4  magic "ATEX"        ("ATTX" also parses; it carries a trailer)
        +0x04  4  fourcc              DXT1/DXT2/DXT3/DXT4/DXT5/DXTA/DXTL/DXTN
        +0x08  2  width  u16
        +0x0A  2  height u16
        +0x0C     level records, to the end of the buffer

    level record
        +0x00  4  size u32   -- the record's TOTAL size, its own 8 bytes included
        +0x04  4  code u32   -- compression code; 0 means the payload is raw
        +0x08     payload, size-8 bytes

        The next record begins at this record's offset + size. The walk ends
        when the running offset equals the buffer length EXACTLY.

THE HEADER IS 12 BYTES, NOT 20, and this correction is worth stating plainly
because two of this project's own NOT FOUNDs were made of it. An earlier pass
recorded "+12 u32 == payload_len - 12, a size (150/150)" and "+16 u32 taking
only the values 10 and 4, an unidentified discriminator, specifically NOT a mip
count". Both were level 0's record fields read as if they were header fields:
+12 is level 0's size and +16 is level 0's code. The "150/150" held only on a
sample of single-level files, where level 0 does consume the rest of the buffer;
across the stored population it fails. And +16 takes 0, 1, 2, 4, 8, 9, 10 and 12
in retail, exactly as a compression code would.

HOW MUCH OF THIS IS MEASURED, per CLAUDE.md's labels:

  MEASURED, from the client's own disassembly. The validating probe at VA
  0x6c3050 checks the magic, switches on the fourcc, and walks 8-byte records
  from offset 12, counting them through an out-pointer. Its loop tail at
  0x6c3198 is `cmp esi,ebx / je` -- it succeeds the instant the running offset
  equals the buffer length, with NO requirement that the mip dimensions have
  been exhausted. The dispatcher at 0x679835 passes that count to the decoder,
  whose loop tail at 0x6c3028 is a plain `level < levelCount`. Read twice, by
  two agents working independently, byte for byte.

  MEASURED, from real bytes. The record walk closes to the exact final byte on
  every ATEX file our decompressor can produce. Level sizes match the formula
  below on every level whose own code is 0.

  NOT the same claim: that the client's TEXTURE layer above the codec accepts a
  one-level file. GrTex2d.cpp asserts on a level count and nobody has traced
  which flags the icon path passes. The codec accepts one level; whether an
  icon DRAWS from one is an open question that one launch settles.

  RECONSTRUCTION, and the weakest link here: that a raw level's payload is
  planar -- every block's colour words first, then every block's index words.
  One witness, and it fails silently rather than loudly. fill_uniform() below
  exists to make it unobservable in a first test; see its docstring.

WHERE `--make` MAY WRITE, and why this file needed the rule bolted on late.
Until 2026-08-13 `--make OUT` went straight to `open(OUT, "wb")` with no guard
of any kind -- the only binary writer in `toolkit/mapdata/` without one, while
`datwrite`, `rebloat`, `mapbuild` and `mapexport` all had theirs, and two of
those got theirs BECAUSE this class of tool had already written into the wrong
tree. `--make C:\\gw\\Gw.dat` would have truncated the owner's 4.2 GB archive to
a few kilobytes of texture, and no part of that is recoverable by re-reading a
docstring. `resolve_out()` below refuses three destinations and is called before
anything is built, so a wrong path costs nothing:

  * `C:\\gw`             the owner's own install, read-only to this project.
  * `vault/dat_study`   the SOURCE snapshot every other archive is cut from.
  * EVERY checkout      an authored ATEX is derived from measured ArenaNet
                        layout and belongs nowhere near version control. Note
                        the plural: a git worktree's root is NOT the main
                        checkout's, so `working_tree_roots()` resolves both --
                        `mapbuild.py` learned that the expensive way, having
                        allowed `<main>/toolkit/out.dat` from a worktree.

The vault is allowed BY NAME even though it sits inside the main checkout,
because it is gitignored -- that is the whole reason derived artifacts live
there. `reskin.py`'s first guard refused the vault while its own error message
told the operator to write there, which made the tool unable to do its only job.
A guard that refuses everything protects nothing.

    python toolkit/mapdata/atex.py --dat DAT --row 174086
    python toolkit/mapdata/atex.py --make out.atex --fourcc DXT1 --size 128
"""

import argparse
import binascii
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import dxt1  # noqa: E402
import vaultpath  # noqa: E402

REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
LIVE_INSTALL = os.path.normcase(os.path.abspath(r"C:\gw"))

MAGIC_ATEX = b"ATEX"
MAGIC_ATTX = b"ATTX"
HEADER_SIZE = 12
RECORD_SIZE = 8

# Bits per pixel, from the client's own table at VA 0xa5dd60. A DXT block covers
# 4x4 pixels, so 4 bpp is an 8-byte block and 8 bpp is a 16-byte block.
BITS_PER_PIXEL = {
    b"DXT1": 4,
    b"DXT2": 8,
    b"DXT3": 8,
    b"DXT4": 8,
    b"DXT5": 8,
    b"DXTA": 4,
    b"DXTL": 8,
    b"DXTN": 8,
}

CODE_RAW = 0


class Level:
    __slots__ = ("index", "offset", "size", "code", "width", "height")

    def __init__(self, index, offset, size, code, width, height):
        self.index = index
        self.offset = offset
        self.size = size
        self.code = code
        self.width = width
        self.height = height

    @property
    def payload_size(self):
        return self.size - RECORD_SIZE

    @property
    def raw(self):
        return self.code == CODE_RAW

    def __repr__(self):
        return (f"<Level {self.index} {self.width}x{self.height} "
                f"size={self.size} code={self.code}>")


class Atex:
    def __init__(self, magic, fourcc, width, height, levels, length):
        self.magic = magic
        self.fourcc = fourcc
        self.width = width
        self.height = height
        self.levels = levels
        self.length = length

    @property
    def closes_exactly(self):
        """Did the record walk consume the buffer to the byte?

        This is the check worth having: it is the artifact refuting us, not our
        parser forcing a result. A wrong record layout overshoots or undershoots.
        """
        if not self.levels:
            return False
        last = self.levels[-1]
        return last.offset + last.size == self.length


def level_dims(width, height, level):
    """Dimensions at a mip level. Halve, floor, clamp at 1."""
    return max(width >> level, 1), max(height >> level, 1)


def level_payload_size(fourcc, width, height, level):
    """Bytes of block data at one level.

    Rounds each dimension up to a whole 4x4 block, which is why a 1x1 level
    still costs a full block. MEASURED against every raw level in the corpus.
    """
    bpp = BITS_PER_PIXEL.get(fourcc)
    if bpp is None:
        raise ValueError(f"unknown fourcc {fourcc!r}")
    w, h = level_dims(width, height, level)
    w = (w + 3) & ~3
    h = (h + 3) & ~3
    return w * h * bpp // 8


def full_chain_levels(width, height):
    """How many levels a complete chain has, down to and including 1x1."""
    n = 1
    while max(width >> (n - 1), 1) > 1 or max(height >> (n - 1), 1) > 1:
        n += 1
    return n


def parse(data):
    """Walk an ATEX buffer. Raises ValueError rather than guessing past damage."""
    if len(data) < HEADER_SIZE + RECORD_SIZE:
        raise ValueError(f"too short to be ATEX: {len(data)} bytes")
    magic = data[0:4]
    if magic not in (MAGIC_ATEX, MAGIC_ATTX):
        raise ValueError(f"not an ATEX container: magic {magic!r}")
    fourcc = data[4:8]
    width, height = struct.unpack_from("<HH", data, 8)

    levels = []
    off = HEADER_SIZE
    n = 0
    while off + RECORD_SIZE <= len(data):
        size, code = struct.unpack_from("<II", data, off)
        if size <= RECORD_SIZE:
            raise ValueError(f"level {n} at {off} declares size {size}, "
                             f"which cannot hold its own {RECORD_SIZE}-byte header")
        if off + size > len(data):
            raise ValueError(f"level {n} at {off} claims {size} bytes but only "
                             f"{len(data) - off} remain")
        w, h = level_dims(width, height, n)
        levels.append(Level(n, off, size, code, w, h))
        off += size
        n += 1
        if off == len(data):
            break
    return Atex(magic, fourcc, width, height, levels, len(data))


#: An ATTX row's trailer is an `ffna` container -- the same magic the map files
#: use, at a different type. MEASURED at 21,923 bytes on 106 of 106 rows by
#: `test_atex.py`, and on 51 of 51 terrain textures by a second population.
#: **That size is deliberately NOT used to find the trailer**; see
#: `split_trailer`.
TRAILER_MAGIC = b"ffna"

#: The last 12 bytes of an ATTX row: `{u32 head length, u32 0, b"XTTA"}` --
#: the ATTX magic byte-reversed. MEASURED on **1,648 of 1,648** ATTX rows in
#: the archive (the whole population, not a sample), and CORROBORATED from the
#: client's own writer at VA 0x007582A0, which appends exactly this after the
#: `ffna` riff it builds.
#:
#: **This is an independent witness for the boundary**, which is what makes it
#: worth reading: ArenaNet declares where her container ends, so our walk can
#: be REFUTED by her number rather than merely agreeing with itself. The
#: controls are 0 of 1,648 -- the word equals neither the total length nor the
#: head minus 12 -- and the head length is not a constant to begin with (578
#: distinct values from 368 to 68,156), so the agreement is not free.
TRAILER_FOOTER = struct.Struct("<II4s")
TRAILER_TAG = b"XTTA"


def trailer_declared_end(trailer):
    """The head length a trailer DECLARES, or None if it carries no footer.

    None is a real answer: a plain ATEX has no trailer at all, and nothing
    obliges a future one to carry this footer.
    """
    if len(trailer) < TRAILER_FOOTER.size:
        return None
    declared, zero, tag = TRAILER_FOOTER.unpack_from(
        trailer, len(trailer) - TRAILER_FOOTER.size)
    if tag != TRAILER_TAG or zero != 0:
        return None
    return declared


def container_end(data):
    """The first byte the level-record walk does NOT account for.

    On a well-formed ATEX that is `len(data)`. On an ATTX it is the first byte
    of the trailer. Separated from `parse` because on an ATTX the OFFSET is the
    measurement and the refusal is not: `parse` can only say the walk died,
    while this says where.

    Shares its rule with `parse` and nothing else -- a record's `size` counts
    its own 8-byte header, and the next record begins `size` bytes on.
    """
    off = HEADER_SIZE
    while off + RECORD_SIZE <= len(data):
        size, = struct.unpack_from("<I", data, off)
        if size <= RECORD_SIZE or off + size > len(data):
            return off
        off += size
        if off == len(data):
            return off
    return off


def split_trailer(data):
    """`(body, trailer)` -- the ATEX container, and whatever follows it.

    **The boundary is found by WALKING, never by searching.** Two rejected
    alternatives, because both look reasonable and both are wrong:

      - `data.rfind(b"ffna")` finds the LAST occurrence, and compressed level
        payloads are arbitrary bytes that may contain that sequence. A search
        can only ever be right by luck; the container already knows where it
        ends.
      - the measured 21,923 is a fact about the rows measured so far, and a
        constant nothing re-derives is a landmine the day a build ships a
        different one. It is asserted as a CENSUS in the test instead, where a
        second value is a finding rather than a crash.

    A plain ATEX comes back unchanged with an empty trailer, because its walk
    closes on the last byte -- so callers may split unconditionally.

    Raises ValueError when the leftover is not a container we recognise. That
    refusal is the point: a TRUNCATED ATEX also leaves the walk short, and its
    leftover is level data, so without this check truncation would be silently
    reported as a body that closes exactly plus a garbage trailer.
    """
    end = container_end(data)
    trailer = data[end:]
    if trailer and trailer[:4] != TRAILER_MAGIC:
        raise ValueError(
            f"the record walk stopped at {end} with {len(trailer)} bytes left "
            f"over, and they do not begin with {TRAILER_MAGIC!r} "
            f"({bytes(trailer[:4])!r}) -- this is a damaged or truncated "
            f"container, not one carrying a trailer")
    # AND THE SECOND WITNESS. The walk LOCATES the boundary; the footer is
    # ArenaNet's own statement of where it is, so a disagreement means one of
    # the two is wrong and neither may be preferred silently.
    declared = trailer_declared_end(trailer)
    if declared is not None and declared != end:
        raise ValueError(
            f"the record walk stopped at {end} but the trailer's footer "
            f"declares the container is {declared} bytes -- two witnesses "
            f"disagreeing, which is a finding and not something to resolve "
            f"by preferring one of them")
    return data[:end], trailer


def fill_uniform(n_bytes, dword):
    """n_bytes of one repeated dword.

    This exists to neutralise the one RECONSTRUCTION in this module. Whether a
    raw level is planar (all colour words, then all index words) or block
    interleaved is attested by a single witness, and getting it wrong renders
    noise rather than an error -- a silent failure, the worst kind to debug.

    If every dword in the payload is identical, the two layouts produce
    byte-identical files. So a first test using this fill cannot be confounded
    by the ordering question at all: it tests the header, the framing, the size
    formula and the raw path, and nothing else. Establish those, then vary the
    payload to settle the ordering separately.
    """
    if n_bytes % 4:
        raise ValueError(f"{n_bytes} is not a whole number of dwords")
    return struct.pack("<I", dword) * (n_bytes // 4)


def build(fourcc, width, height, levels=None, code=CODE_RAW, fill=0):
    """Author an ATEX file. Our bytes, start to finish.

    levels=None builds a complete mip chain; levels=1 builds only the base
    level. Both are attested shapes in retail, though a one-level file has only
    ever been seen at a DXTA fourcc.
    """
    if fourcc not in BITS_PER_PIXEL:
        raise ValueError(f"unknown fourcc {fourcc!r}")
    if levels is None:
        levels = full_chain_levels(width, height)
    out = bytearray()
    out += MAGIC_ATEX
    out += fourcc
    out += struct.pack("<HH", width, height)
    for lv in range(levels):
        payload = level_payload_size(fourcc, width, height, lv)
        out += struct.pack("<II", payload + RECORD_SIZE, code)
        out += fill_uniform(payload, fill)
    return bytes(out)


def build_image(rgb, width, height, levels=None, layout=dxt1.PLANAR):
    """Author a DXT1 ATEX from real pixels, mipmapping down as needed.

    Every level carries code 0, so nothing here is compressed in the ATEX sense
    -- the blocks go in raw and the client reads them raw.
    """
    if levels is None:
        levels = full_chain_levels(width, height)
    out = bytearray()
    out += MAGIC_ATEX + b"DXT1" + struct.pack("<HH", width, height)
    img, w, h = rgb, width, height
    for lv in range(levels):
        # ATEX rounds each level up to whole 4x4 blocks; below 4 pixels the
        # image is smaller than one block, so pad by repeating the last row and
        # column rather than inventing black, which would show as a dark 1x1.
        pw, ph = max(w, 4), max(h, 4)
        if (pw, ph) != (w, h):
            padded = bytearray(pw * ph * 3)
            for y in range(ph):
                sy = min(y, h - 1)
                for x in range(pw):
                    sx = min(x, w - 1)
                    s = (sy * w + sx) * 3
                    d = (y * pw + x) * 3
                    padded[d:d + 3] = img[s:s + 3]
            blocks = dxt1.encode(bytes(padded), pw, ph)
        else:
            blocks = dxt1.encode(img, w, h)
        payload = dxt1.pack(blocks, layout)
        want = level_payload_size(b"DXT1", width, height, lv)
        if len(payload) != want:
            raise ValueError(f"level {lv} encoded to {len(payload)} bytes, "
                             f"the container expects {want}")
        out += struct.pack("<II", len(payload) + RECORD_SIZE, CODE_RAW)
        out += payload
        if lv + 1 < levels:
            img, w, h = dxt1.mipmap(img, w, h)
    return bytes(out)


def describe(a, name=""):
    ok = "closes exactly" if a.closes_exactly else "DOES NOT CLOSE"
    print(f"{name}{a.magic.decode()} {a.fourcc.decode()} "
          f"{a.width}x{a.height}  {a.length} bytes  "
          f"{len(a.levels)} level(s)  {ok}")
    for lv in a.levels:
        want = level_payload_size(a.fourcc, a.width, a.height, lv.index)
        agree = "==" if want == lv.payload_size else "!="
        note = "" if lv.raw else "  (compressed, formula does not apply)"
        print(f"    L{lv.index} {lv.width:>4}x{lv.height:<4} "
              f"at 0x{lv.offset:<6X} size {lv.size:<7} code {lv.code:<3} "
              f"payload {lv.payload_size:<7} {agree} predicted {want}{note}")


# ------------------------------------------------------------ writing output

# =========================================================================
# THE LEVEL CODEC (2026-08-14). A level's `code` is NOT a compression method.
# =========================================================================
#
# It is a **5-BIT MASK OF OPTIONAL DECODE PASSES** over the level's 4x4 block
# grid, which is why the client's own validator gates it with
# `test dword ptr [eax+4], 0xffffffe0` at `0x006C3187` -- five bits is the
# whole field. Each set bit runs one run-length-coded pass that stamps a
# single precomputed reference block into a subset of blocks and marks them;
# **everything no pass claimed is then copied VERBATIM from the tail of the
# same payload**, de-interleaved into three sequential planes. So a level is:
#
#     [bit stream: which blocks are one flat colour / flat alpha / transparent]
#     [raw DXT bytes for every other block, planar]
#
# `code == 0` means no pass ran and the whole level is that planar copy --
# which is why 25 of 1,533 containers looked "raw" and the other 98.4% did
# not. The decoder is ArenaNet's `P:\Code\Engine\Gr\Img\ImgAtex.cpp` at
# `0x006C2B70`, reached only as a handler pointer installed by the two
# callers of the validator. There is no jump table and no per-code routine.
#
# **THE PLANAR SPLIT WAS MEASURED FROM THE CORPUS FIRST AND THE CLIENT
# AGREED**, which is the shape worth trusting: mip-consistency scoring over
# raw levels put DXT5's colour endpoints at `8*nb` (11.02 against 60.16 for
# colour-first) and its alpha as whole 8-byte blocks (1.76 against 51.56 for
# a split alpha plane), and DXT3's order at `aci` (10.80 against 39-65 for
# five rivals) -- before any of this code was read. The client's residual
# loop below is exactly that: an alpha PAIR plane, then a colour-word plane,
# then an index-word plane.
#
# Provenance: the two tables are ArenaNet's and are carried as LITERALS with
# their addresses, the pattern `modelfile.py` set for the FVF stride tables --
# the module then works on a bare machine and `test_atexlevel.py` §7 re-reads
# them out of the vaulted image to pin the literals to ArenaNet's own bytes.
# (That sentence said `test_atex.py` until 2026-08-15; the check has never
# lived there, and a pointer at the wrong test is how a section stops being
# run without anyone noticing.)
#
# AND THE ADDRESSES BELOW ARE A FACT ABOUT ONE BUILD, which is why the number
# is now written down beside them rather than left to be inferred. `atex.py`
# named neither build nor date -- the exact shape `studies/crossbuild/PLAN.md`
# §6's class (b) calls the defect: "a bare VA with no build is the defect, not
# the VA". It cost something real: §7's re-read picked its image by directory
# order, and with nothing here saying WHICH build these came from there was no
# way for that section, or its reader, to notice it had switched.
TABLES_BUILD = 38797

#: `s_formatFlags`, 27 u32 at VA 0x00A5DEA8 (accessor 0x006AE830, whose assert
#: `format < GR_FORMATS` with `cmp esi, 0x1b` is what fixes the count at 27).
#: Indexed by the validator's format enum. Bit 0x210 means "has a colour
#: half", 0x280 "has an alpha half" -- and the block sizes those two bits
#: imply (8 bytes for DXT1/DXTA, 16 for the rest) are independently confirmed
#: by the corpus, so the table is corroborated rather than trusted.
FORMAT_FLAGS_VA = 0x00A5DEA8
FORMAT_FLAGS = (
    0x00B2, 0x0012, 0x00B2, 0x0072, 0x0012, 0x0012, 0x0012, 0x0100,
    0x01A4, 0x01A4, 0x01A4, 0x0104, 0x00A2, 0x0078, 0x0400, 0x0071,
    0x00B1, 0x00B1, 0x00B1, 0x00B1, 0x00A1, 0x0011, 0x0201, 0x0100,
    0x08B2, 0x0812, 0x0400)

#: The run-length table: 64 x {u8 codeLen, u8 runLength-1} at VA 0x00A5E620,
#: indexed by the TOP SIX BITS of the rack. A 3-symbol prefix code, and the
#: closed form is CONFIRMED against the bytes rather than assumed:
#:     top6 0..15  -> 6 bits, run 17 down to 2
#:     top6 16..31 -> 2 bits, run 18 (the maximum; repeat for longer runs)
#:     top6 32..63 -> 1 bit,  run 1
RUN_TABLE_VA = 0x00A5E620
RUN_TABLE = tuple([(6, 16 - i) for i in range(16)]
                  + [(2, 17)] * 16 + [(1, 0)] * 32)

#: The validator's format enum (`GrFormat`), written by `0x006C3050`.
FORMAT_ENUM = {b"DXT1": 0x0F, b"DXT2": 0x10, b"DXT3": 0x11, b"DXT4": 0x12,
               b"DXT5": 0x13, b"DXTA": 0x14, b"DXTL": 0x15, b"DXTN": 0x16}

#: Which pass each code bit selects, and the formats it is gated to.
PASS_TRANSPARENT = 0x01     # DXT1 punch-through blocks
PASS_ALPHA4 = 0x02          # DXT2/DXT3 explicit-alpha flat blocks
PASS_ALPHA8 = 0x04          # DXT4/5/A/L interpolated-alpha flat blocks
PASS_FLAT_COLOUR = 0x08     # one 24-bit colour for the whole level
PASS_TERRAIN_BORDERS = 0x10  # 256x256 DXT2/DXT3 mirrored-edge regeneration


class Rack:
    """ArenaNet's `Base\\compress\\CmpIo.h` bit rack: MSB-first within
    little-endian u32 words, a 32-bit window plus a spill register.

    Reading past the end yields ZEROS rather than raising, which is the
    client's behaviour and is load-bearing -- several real levels end with
    the last run still nominally in progress. `dry` counts those over-reads
    so a caller can tell a clean finish from a starved one.
    """

    __slots__ = ("words", "i", "hi", "lo", "count", "dry")

    def __init__(self, words):
        self.words = words
        self.hi = words[0] if words else 0
        self.i = 1
        self.lo = 0
        self.count = 0
        self.dry = 0

    def peek6(self):
        return self.hi >> 26

    def read(self, n):
        hi, lo, count = self.hi, self.lo, self.count
        value = hi >> (32 - n)
        shifted = ((hi << n) | (lo >> (32 - n))) & 0xFFFFFFFF
        if count >= n:
            self.hi, self.lo, self.count = (shifted, (lo << n) & 0xFFFFFFFF,
                                            count - n)
        elif self.i < len(self.words):
            word = self.words[self.i]
            self.i += 1
            self.hi = shifted | (word >> (count + 32 - n))
            self.lo = (word << (n - count)) & 0xFFFFFFFF
            self.count = count + 32 - n
        else:
            self.hi, self.lo, self.count = shifted, 0, 0
            self.dry += 1
        return value

    def run(self):
        """One run length, via the client's 6-bit lookup."""
        code_len, minus_one = RUN_TABLE[self.peek6()]
        if code_len:
            self.read(code_len)
        return minus_one + 1


def block_layout(fourcc):
    """`(block_dwords, colour_offset, has_alpha, has_colour, fmt)`.

    The stride the client computes at `0x006C2BA1`-`0x006C2BDE` from the
    format flags: 8 bytes for DXT1/DXTA, 16 for everything else here.
    """
    fmt = FORMAT_ENUM.get(bytes(fourcc))
    if fmt is None:
        raise ValueError(f"fourcc {bytes(fourcc)!r} is not an ATEX format")
    flags = FORMAT_FLAGS[fmt]
    alpha = 2 if flags & 0x280 else 0
    extra = 2 if fmt == 0x15 else 0          # DXTL carries a third pair
    colour = 2 if flags & 0x210 else 0
    return alpha + extra + colour, alpha + extra, bool(alpha or extra), \
        bool(colour), fmt


def solid_colour_block(rgb, is_dxt1):
    """The 2-dword DXT1 block for one solid colour (`0x006CB060`).

    Quantises to 565 with the client's own rounding -- `(x - (x>>5)) >> 3`
    for the 5-bit channels and `(x - (x>>6)) >> 2` for green -- then picks
    endpoints and a repeated index so the block reproduces the colour as
    closely as the format allows. Transcribed rather than reinvented: a
    "nearest 565" of our own lands on a different block for many colours and
    would make every flat-colour region subtly wrong.
    """
    blue, green, red = rgb & 0xFF, (rgb >> 8) & 0xFF, (rgb >> 16) & 0xFF
    quant = [(blue - (blue >> 5)) >> 3, (green - (green >> 6)) >> 2,
             (red - (red >> 5)) >> 3]
    source = [blue, green, red]

    def expand(channel, value):
        return value * 4 + (value >> 4) if channel == 1 else \
            value * 8 + (value >> 2)

    fracs = []
    for k in range(3):
        low, high = expand(k, quant[k]), expand(k, quant[k] + 1)
        span = high - low
        fracs.append((source[k] - low) * 12 // span if span else 0)
    end0, end1 = [0, 0, 0], [0, 0, 0]
    for k in range(3):
        f = fracs[k]
        end0[k] = quant[k] + (1 if 6 <= f < 10 else 0)
        end1[k] = quant[k] + (1 if (2 <= f < 6) or f >= 10 else 0)
    c0 = (end0[2] << 11) | (end0[1] << 5) | end0[0]
    c1 = (end1[2] << 11) | (end1[1] << 5) | end1[0]

    used, total = 0, 0
    for k in range(3):
        if end0[k] != end1[k]:
            total += fracs[k] if end0[k] == quant[k] else 12 - fracs[k]
            used += 1
    frac = (total + used // 2) // used if used else 0
    alt = 1 if (is_dxt1 and (frac in (5, 6) or used == 0)) else 0
    if used == 0 and not alt:
        if c1 != 0xFFFF:
            frac, c1 = 0, c1 + 1
        else:
            frac, c0 = 12, c0 - 1
    if alt != (0 if c1 < c0 else 1):
        c0, c1 = c1, c0
        frac = 12 - frac
    if alt:
        index = 2
    elif frac < 2:
        index = 0
    elif frac < 6:
        index = 2
    elif frac < 10:
        index = 3
    else:
        index = 1
    nibble = index | (index << 2)
    nibble |= nibble << 4
    word = nibble | (nibble << 8)
    return (((c1 << 16) | c0) & 0xFFFFFFFF, (word | (word << 16)) & 0xFFFFFFFF)


def _run_pass(rack, out, block_dw, offset, blocks, skip, mark, two_bit,
              reference):
    """One run-coded pass. Blocks an EARLIER pass claimed do not spend run."""
    i = 0
    while i < blocks:
        length = rack.run()
        flag = rack.read(1)
        selector = (1 + rack.read(1)) if (flag and two_bit) else (1 if flag
                                                                  else 0)
        while length > 0 and i < blocks:
            if not skip[i]:
                if flag:
                    lo, hi = reference(selector)
                    out[i * block_dw + offset] = lo
                    out[i * block_dw + offset + 1] = hi
                    for bitmap in mark:
                        bitmap[i] = 1
                length -= 1
            i += 1
        while i < blocks and skip[i]:
            i += 1


def decode_level(data, container, index):
    """One mip level's DXT blocks, in D3D order, ready for a block decoder.

    `data` is the whole ATEX container and `container` the `Atex` from
    `parse`. Returns `(blocks, block_bytes)` -- the raw DXT payload for that
    level exactly as the GPU would receive it, and the per-block stride.

    THE ORDER OF WORK, and every step is the client's:
      1. `PASS_TERRAIN_BORDERS` pre-marks the border blocks (256x256 DXT2/3
         only).

         **CORRECTED 2026-08-14, and the reason is the lesson.** This line
         used to read "0 of 49,800 sampled levels actually use it", which was
         true of the sample and false of the archive: **51 of 51** of one
         map's terrain textures carry the bit at level 0, and so does every
         ATTX row. The sample could not have contained one -- `parse` RAISED
         on all 1,648 ATTX rows until `split_trailer` landed, so the only
         files that use the pass named for terrain were exactly the files the
         parser refused. A population measured through a filter that excludes
         the phenomenon reports zero and looks like evidence.
      2. The four run-coded passes run IN BIT ORDER, sharing one rack.
      3. The literal cursor backs up ONE DWORD from wherever the rack
         stopped (`0x006C2E73`) and the record end is rounded DOWN so the
         residual is a whole number of dwords.
      4. The residual fills every unclaimed block from three sequential
         planes: the alpha pair, then colour words, then index words.
    """
    block_dw, colour_off, has_alpha, has_colour, fmt = block_layout(
        container.fourcc)
    if not 0 <= index < len(container.levels):
        raise ValueError(f"level {index} of {len(container.levels)}")
    level = container.levels[index]
    width, height = level_dims(container.width, container.height, index)
    blocks = max(1, (width + 3) >> 2) * max(1, (height + 3) >> 2)
    out = [0] * (blocks * block_dw)
    seen_alpha = bytearray(blocks)
    seen_colour = bytearray(blocks)

    payload_at = level.offset + RECORD_SIZE
    end = level.offset + level.size
    literal_at = payload_at

    if level.code:
        body = data[payload_at:end]
        words = list(struct.unpack_from(f"<{len(body) // 4}I", body, 0)) \
            if len(body) >= 4 else []
        rack = Rack(words)

        if (level.code & PASS_TERRAIN_BORDERS and width == 256
                and height == 256 and fmt in (0x10, 0x11)):
            for i in range(blocks):
                if (i & 31) in (0, 1, 30, 31) or ((i >> 6) & 31) in (0, 1, 30,
                                                                     31):
                    seen_alpha[i] = seen_colour[i] = 1

        if (level.code & PASS_TRANSPARENT and has_colour and not has_alpha
                and fmt != 0x15):
            # A DXT1 block in 1-bit-alpha mode with all sixteen texels on
            # index 3: fully transparent. It carries no payload value at all.
            _run_pass(rack, out, block_dw, colour_off, blocks, seen_colour,
                      (seen_alpha, seen_colour), False,
                      lambda _s: (0xFFFFFFFE, 0xFFFFFFFF))

        if level.code & PASS_ALPHA4 and fmt in (0x10, 0x11):
            nibble = rack.read(4) * 0x11
            nibble |= nibble << 8
            nibble = (nibble | (nibble << 16)) & 0xFFFFFFFF
            _run_pass(rack, out, block_dw, 0, blocks, seen_colour,
                      (seen_alpha,), True,
                      lambda s, v=nibble: (0, 0) if s == 1 else (v, v))

        if level.code & PASS_ALPHA8 and fmt in (0x12, 0x13, 0x14, 0x15):
            alpha = rack.read(8)
            pair = (alpha | (alpha << 8)) & 0xFFFFFFFF
            _run_pass(rack, out, block_dw, 0, blocks, seen_colour,
                      (seen_alpha,), True,
                      lambda s, v=pair: (0, 0) if s == 1 else (v, 0))

        if level.code & PASS_FLAT_COLOUR and has_colour:
            block = solid_colour_block(rack.read(24), fmt == 0x0F)
            _run_pass(rack, out, block_dw, colour_off, blocks, seen_colour,
                      (seen_colour,), False, lambda _s, b=block: b)

        literal_at = payload_at + (rack.i - 1) * 4

    literal_end = end - ((end - literal_at) & 3)
    cursor = [literal_at]

    def next_dword():
        if cursor[0] >= literal_end:
            return 0                       # the client reads past end as zero
        value, = struct.unpack_from("<I", data, cursor[0])
        cursor[0] += 4
        return value

    if has_alpha:
        for i in range(blocks):
            if not seen_alpha[i]:
                out[i * block_dw] = next_dword()
                out[i * block_dw + 1] = next_dword()
    if has_colour:
        for i in range(blocks):
            if not seen_colour[i]:
                out[i * block_dw + colour_off] = next_dword()
        for i in range(blocks):
            if not seen_colour[i]:
                out[i * block_dw + colour_off + 1] = next_dword()

    return struct.pack(f"<{len(out)}I", *out), block_dw * 4


class Refused(SystemExit):
    """A write guard said no. Always names the path and the rule it broke."""


def _inside(path, root):
    """True if `path` is `root` or below it. Case-folded: this is Windows."""
    path = os.path.normcase(os.path.abspath(path))
    root = os.path.normcase(os.path.abspath(root))
    return path == root or path.startswith(root + os.sep)


def working_tree_roots():
    """Every checkout of this repository a write could land in.

    `REPO_ROOT` is the tree THIS file sits in, and inside a git worktree that is
    not the main checkout: the worktree's `.git` is a FILE reading
    `gitdir: <main>/.git/worktrees/<name>`, and the main checkout -- tracked
    files and all -- lives somewhere else entirely. A refusal that tested only
    `REPO_ROOT` therefore allows a write straight into the other tree of the
    same repository, which is the provenance gate failing in exactly the
    environment this module is being written in. `mapbuild.py` measured that:
    from the worktree, `<main>/toolkit/out.dat` was ALLOWED.

    Returns absolute paths, most specific first. Never raises -- an unreadable
    or unusual `.git` yields the roots we could establish, and the caller still
    refuses `REPO_ROOT`.
    """
    roots = [os.path.abspath(REPO_ROOT)]
    dotgit = os.path.join(REPO_ROOT, ".git")
    if not os.path.isfile(dotgit):
        return roots                            # a normal checkout, or no git
    try:
        with open(dotgit, "r", encoding="utf-8", errors="replace") as fh:
            line = fh.read().strip()
    except OSError:
        return roots
    if not line.startswith("gitdir:"):
        return roots
    gitdir = line.split(":", 1)[1].strip()
    if not os.path.isabs(gitdir):
        gitdir = os.path.join(REPO_ROOT, gitdir)
    # <main>/.git/worktrees/<name>  ->  <main>
    node = os.path.abspath(gitdir)
    while os.path.basename(node) != ".git":
        parent = os.path.dirname(node)
        if parent == node:
            return roots
        node = parent
    main_root = os.path.dirname(node)
    if main_root and not _inside(main_root, roots[0]):
        roots.append(main_root)
    return roots


def resolve_out(path):
    """Where an authored ATEX may be written. Raises `Refused` otherwise.

    Called BEFORE the file is built, not just before it is opened: refusing
    early means a long build never runs against a path the write would reject,
    which is the ordering `rebloat.guard_target` settled on for the same reason.

    The order of the tests is load-bearing. `vault/dat_study` is INSIDE the
    vault and the vault is allowed, so the snapshot has to be refused first or
    the allow would swallow it.
    """
    full = os.path.abspath(path)
    parts = os.path.normcase(full).replace("\\", "/").split("/")
    if "dat_study" in parts:
        raise Refused(
            f"refusing to write to {full}\n"
            f"  vault/dat_study is the SOURCE snapshot every other archive in "
            f"the vault is cut from, and every measurement in studies/ was "
            f"taken against it. Write to a scratch directory or under "
            f"{vaultpath.vault_path('builds')}.")
    if _inside(full, LIVE_INSTALL):
        raise Refused(
            f"refusing to write to {full}\n"
            f"  That is the owner's own install at {LIVE_INSTALL} and it is "
            f"read-only to this project, permanently (CLAUDE.md). Pointing "
            f"--make at Gw.dat there would TRUNCATE a 4.2 GB archive.")
    # THE VAULT IS AN INTENDED DESTINATION and it sits inside the main
    # checkout, so it is allowed by name before the tree test below. It is
    # gitignored, which is precisely why derived artifacts live in it.
    try:
        if _inside(full, vaultpath.vault_root()):
            return full
    except SystemExit:
        pass                        # no vault resolvable; fall through
    for root in working_tree_roots():
        if _inside(full, root):
            raise Refused(
                f"refusing to write an authored ATEX into a checkout of this "
                f"repository: {full}\n"
                f"  That tree is {root}"
                + (" -- the MAIN checkout, which this worktree shares a "
                   "repository with.\n" if root != os.path.abspath(REPO_ROOT)
                   else "\n")
                + f"  Its layout is derived from ArenaNet's format and "
                f"CLAUDE.md's provenance gate keeps derived bytes out of the "
                f"tree, permanently. Write under "
                f"{vaultpath.vault_path('builds')} or to a scratch directory "
                f"outside every checkout.")
    return full


# --------------------------------------------------------------------------
# Blocks to pixels. `decode_level` hands back DXT BLOCKS; this turns them
# into RGBA8, which is what an exporter and an image writer both want.
# --------------------------------------------------------------------------

def _alpha_table(a0, a1):
    """BC3/BC4's eight-entry alpha ramp. The `a0 > a1` branch is the one with
    six interpolants; the other reserves indices 6 and 7 for 0 and 255."""
    if a0 > a1:
        return [a0, a1] + [((7 - k) * a0 + k * a1) // 7 for k in range(1, 7)]
    return ([a0, a1] + [((5 - k) * a0 + k * a1) // 5 for k in range(1, 5)]
            + [0, 255])


def blocks_to_rgba(blocks, stride, fourcc, width, height):
    """RGBA8 pixels, top row first, from one decoded level's blocks.

    The per-format layout comes from `block_layout` rather than from the
    stride, which is what stops DXTA -- 8 bytes a block, like DXT1, and NO
    COLOUR HALF -- being read as colour. That mistake is recorded in
    `test_atexlevel.py`: it scored DXTA at the noise floor and read as a
    broken decoder when the decoder was right.

    DXT2/DXT4 carry PREMULTIPLIED alpha and are returned as stored, i.e. NOT
    un-premultiplied, because whether a consumer wants that is its decision
    and undoing it is lossy. They are 2 of 1,533 sampled containers.
    """
    _block_dw, colour_off, has_alpha, has_colour, fmt = block_layout(fourcc)
    bw = max(1, (width + 3) // 4)
    bh = max(1, (height + 3) // 4)
    out = bytearray(width * height * 4)
    colour_byte = colour_off * 4
    explicit = fourcc in (b"DXT2", b"DXT3")
    for index in range(bw * bh):
        base = index * stride
        if has_colour:
            c0, c1 = struct.unpack_from("<HH", blocks, base + colour_byte)
            bits, = struct.unpack_from("<I", blocks, base + colour_byte + 4)
            texels = dxt1.decode_block(c0, c1, bits)
        else:
            texels = [(255, 255, 255, 255)] * 16
        if has_alpha and fmt != 0x15:
            if explicit:
                # BC2: four bits per texel, no ramp.
                raw = int.from_bytes(blocks[base:base + 8], "little")
                alpha = [((raw >> (4 * n)) & 0xF) * 17 for n in range(16)]
            else:
                ramp = _alpha_table(blocks[base], blocks[base + 1])
                raw = int.from_bytes(blocks[base + 2:base + 8], "little")
                alpha = [ramp[(raw >> (3 * n)) & 7] for n in range(16)]
        else:
            alpha = [t[3] for t in texels]
        by, bx = divmod(index, bw)
        by = index // bw
        for n in range(16):
            x = bx * 4 + (n % 4)
            y = by * 4 + (n // 4)
            if x >= width or y >= height:
                continue
            r, g, b, _a = texels[n]
            at = (y * width + x) * 4
            out[at] = r
            out[at + 1] = g
            out[at + 2] = b
            out[at + 3] = alpha[n]
    return bytes(out)


#: A 256x256 terrain tile is FOUR 128x128 variants, and each variant is a
#: 112x112 image inside an 8-pixel border band. `PASS_TERRAIN_BORDERS` marks
#: those band blocks as claimed so the payload never stores them -- and the
#: client then REGENERATES them by mirroring the interior about the tile edge
#: (VA 0x006C2FA5 -> 0x006C22A0, source block `(x^3, y^3)` per border axis
#: plus an in-block reversal).
#:
#: Leaving them zero, which this module did until 2026-08-14, is not a
#: cosmetic gap: it puts a black 8-pixel cross through every terrain texture
#: and it fooled this session's own measurement, which reported the band's
#: alpha as "a hard zero at the rim" when the zero was OURS.
TILE_SIDE = 128
TILE_BAND = 8


def mirror_borders(rgba, width, height, side=TILE_SIDE, band=TILE_BAND):
    """Fill each tile's unstored border band by reflecting its interior.

    Reflection is about the tile edge: within a tile, column `band-1-k` takes
    column `band+k`, so the band is a mirror of the first `band` real columns.
    Applied per axis, so a corner mirrors in both.
    """
    out = bytearray(rgba)

    def src(v):
        local = v % side
        if local < band:
            return v - local + (2 * band - 1 - local)
        if local >= side - band:
            return v - local + (2 * (side - band) - 1 - local)
        return v

    for y in range(height):
        sy = src(y)
        for x in range(width):
            sx = src(x)
            if sx == x and sy == y:
                continue
            d, s = (y * width + x) * 4, (sy * width + sx) * 4
            out[d:d + 4] = rgba[s:s + 4]
    return bytes(out)


def decode_rgba(data, container=None, level=0):
    """One ATEX level straight to `(rgba, width, height)`.

    **ATTX is accepted here, and this is the only place it is.** `parse` stays
    strict on purpose -- refusing a container whose walk does not close is what
    catches damage, and softening it would cost that -- so the trailer is split
    off first. On a plain ATEX the split is a no-op, so this costs nothing and
    branches on nothing.
    """
    data, _trailer = split_trailer(data)
    if container is None:
        container = parse(data)
    blocks, stride = decode_level(data, container, level)
    width, height = level_dims(container.width, container.height, level)
    rgba = blocks_to_rgba(blocks, stride, bytes(container.fourcc),
                          width, height)
    # The border pass claims those blocks so the payload never stores them.
    # The client regenerates them; so must we, or the image has a black cross
    # through it. Gated on exactly the pass's own condition, so a level that
    # did not use it is untouched.
    if container.levels[level].code & PASS_TERRAIN_BORDERS \
            and width == height == 256 \
            and FORMAT_ENUM.get(bytes(container.fourcc)) in (0x10, 0x11):
        rgba = mirror_borders(rgba, width, height)
    return rgba, width, height


#: The one uncompressed DDS shape the prop corpus uses. MEASURED: of 1,795
#: texture references on the two reference maps, 10 are DDS and all ten name
#: the SAME file -- 128x128 A8R8G8B8 with 8 mip levels.
DDS_MAGIC = b"DDS "


def dds_rgba(data):
    """`(rgba, width, height)` for an uncompressed 32-bit DDS, or None.

    Deliberately narrow: this exists because ten prop texture references are
    DDS rather than ATEX, and returning None for anything else keeps the
    exporter honest about what it skipped instead of guessing at a format.
    """
    if len(data) < 128 or data[:4] != DDS_MAGIC:
        return None
    height, width = struct.unpack_from("<2I", data, 12)
    pf_flags, = struct.unpack_from("<I", data, 80)
    fourcc = data[84:88]
    bit_count, = struct.unpack_from("<I", data, 88)
    masks = struct.unpack_from("<4I", data, 92)
    if pf_flags & 0x4 and fourcc != b"\0\0\0\0":
        return None                       # a compressed DDS; not handled
    if bit_count != 32:
        return None
    need = width * height * 4
    body = data[128:128 + need]
    if len(body) < need:
        return None
    r_mask, g_mask, b_mask, a_mask = masks

    def shift_of(mask):
        if not mask:
            return None
        s = 0
        while not (mask >> s) & 1:
            s += 1
        return s

    rs, gs, bs, a_s = (shift_of(m) for m in (r_mask, g_mask, b_mask, a_mask))
    out = bytearray(need)
    for i in range(width * height):
        pixel, = struct.unpack_from("<I", body, i * 4)
        out[i * 4] = (pixel & r_mask) >> rs if rs is not None else 0
        out[i * 4 + 1] = (pixel & g_mask) >> gs if gs is not None else 0
        out[i * 4 + 2] = (pixel & b_mask) >> bs if bs is not None else 0
        out[i * 4 + 3] = ((pixel & a_mask) >> a_s) if a_s is not None else 255
    return bytes(out), width, height


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", help="archive to read a row or file id out of")
    ap.add_argument("--row", type=int, help="MFT row to parse")
    ap.add_argument("--file-id", type=int, help="file id to parse")
    ap.add_argument("--make", metavar="OUT",
                    help="author a file. C:\\gw, vault/dat_study and every "
                         "checkout of this repo are refused; see resolve_out")
    ap.add_argument("--fourcc", default="DXT1")
    ap.add_argument("--size", type=int, default=128, help="square dimension")
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--levels", type=int, default=None,
                    help="level count; default is a full chain")
    ap.add_argument("--code", type=lambda s: int(s, 0), default=CODE_RAW)
    ap.add_argument("--fill", type=lambda s: int(s, 0), default=0,
                    help="the dword repeated through every payload")
    ap.add_argument("--pattern", choices=sorted(dxt1.PATTERNS),
                    help="author real DXT1 art instead of a uniform fill")
    ap.add_argument("--layout", choices=dxt1.LAYOUTS, default=dxt1.PLANAR,
                    help="payload order for --pattern. The whole point of "
                         "having both is that only a running client can say "
                         "which is right; see dxt1.py.")
    a = ap.parse_args()

    if a.make:
        # The guard runs FIRST, before a single byte is encoded. See
        # resolve_out(): a refusal costs nothing here and everything after the
        # open() call, which until 2026-08-13 was unguarded entirely.
        out_path = resolve_out(a.make)
        w = a.width or a.size
        h = a.height or a.size
        if a.pattern:
            data = build_image(dxt1.PATTERNS[a.pattern](w, h), w, h,
                               a.levels, a.layout)
        else:
            data = build(a.fourcc.encode(), w, h, a.levels, a.code, a.fill)
        with open(out_path, "wb") as f:
            f.write(data)
        print(f"wrote {out_path}  ({len(data)} bytes)")
        # Parse our own output rather than trusting the builder.
        describe(parse(data), "  ")
        print(f"  crc32 0x{binascii.crc32(data):08X}")
        return 0

    if not a.dat or (a.row is None and a.file_id is None):
        ap.error("need --make, or --dat with --row/--file-id")

    from archive import Archive, file_id_table  # noqa: E402
    with Archive(a.dat) as ar:
        row = a.row
        if row is None:
            row = file_id_table(ar).get(a.file_id)
            if row is None:
                raise SystemExit(f"file id {a.file_id} is not in the table")
        e = ar.row(row)
        data = ar.read(e)
        print(f"row {row}  stored {e.size} B comp={e.compression} "
              f"flags={e.flags} -> {len(data)} B")
        describe(parse(data), "  ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
