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
        e = ar.entries[row - 1]
        data = ar.read(e)
        print(f"row {row}  stored {e.size} B comp={e.compression} "
              f"flags={e.flags} -> {len(data)} B")
        describe(parse(data), "  ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
