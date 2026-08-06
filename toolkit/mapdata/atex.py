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


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", help="archive to read a row or file id out of")
    ap.add_argument("--row", type=int, help="MFT row to parse")
    ap.add_argument("--file-id", type=int, help="file id to parse")
    ap.add_argument("--make", metavar="OUT", help="author a file")
    ap.add_argument("--fourcc", default="DXT1")
    ap.add_argument("--size", type=int, default=128, help="square dimension")
    ap.add_argument("--width", type=int)
    ap.add_argument("--height", type=int)
    ap.add_argument("--levels", type=int, default=None,
                    help="level count; default is a full chain")
    ap.add_argument("--code", type=lambda s: int(s, 0), default=CODE_RAW)
    ap.add_argument("--fill", type=lambda s: int(s, 0), default=0,
                    help="the dword repeated through every payload")
    a = ap.parse_args()

    if a.make:
        w = a.width or a.size
        h = a.height or a.size
        data = build(a.fourcc.encode(), w, h, a.levels, a.code, a.fill)
        with open(a.make, "wb") as f:
            f.write(data)
        print(f"wrote {a.make}  ({len(data)} bytes)")
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
        e = ar.entries[row - 1]
        data = ar.read(e)
        print(f"row {row}  stored {e.size} B comp={e.compression} "
              f"flags={e.flags} -> {len(data)} B")
        describe(parse(data), "  ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
