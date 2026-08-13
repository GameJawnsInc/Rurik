"""Read the Guild Wars client archive: header, master file table, FFNA chunks.

This is the first part of Rurik that works from PRIMARY EVIDENCE. Everything in
the protocol layer is built on reconstructions with no ground truth to check
against -- studies/movement/FINDINGS.md spends a section on exactly how much of
our reference material is somebody's guess. Here the artifact itself is on disk,
so a claim about the format is falsifiable, and the tests beside this file check
it against real bytes rather than against anyone's source code.

The layout below was measured, not read. Where a field is named, it is because
we watched it hold across 177,342 entries; where it is called unknown, no source
we have explains it and neither do we.

    file header (32 bytes)
        0x00  magic       "3AN\\x1A"  -- on disk in THAT byte order. OpenTyria's
                          constant '\\x1ANA3' is a multi-char literal, which packs
                          high byte first, so little-endian on disk reverses it.
                          A study of ours once "corrected" upstream here and was
                          itself wrong; the bytes settle it.
        0x04  u32         header size, 32
        0x08  u32         block size, 512
        0x0C  u32         CRC-32/ISO-HDLC of this header's first 12 bytes.
        0x10  u32         MFT offset
        0x18  u32         MFT size in bytes

    MFT header (24 bytes, at the MFT offset)
        0x00  magic       "Mft\\x1A"
        0x0C  u32         entry count

    MFT entry (24 bytes each, immediately after the MFT header)
        offset u64, size u32, compression u16, flags u16, counter u32, crc u32

        compression is 0 (stored) or 8 (huffman/LZ77 -- see gwdat.py).
        crc is CRC-32/ISO-HDLC over the entry's stored bytes. GWUnpacker named
        it "CRC" and OpenTyria "checksum"; neither computes or verifies it, so
        that was upstream being right rather than upstream being checked. It is
        checked now -- test_datcrc.py, against real bytes, all three rules.

The header cross-checks itself, which is the cheapest real validation available:
the file header declares the table's size and the table header declares its entry
count, and count * 24 == size only if the 24-byte entry stride is right.

TWO ARCHIVES ARE NOT THE SAME ARCHIVE. A running client writes to the Gw.dat it
was launched from. Our install copy holds 177,335 entries and the copy our
patched client has actually run holds 177,342 -- same allocated size, same MFT
offset, seven more files. File ids are content keys and should survive that; raw
MFT row indices do not. Any row index recorded in a study is only meaningful
against the copy it was measured on, which is why open() below wants an explicit
path rather than guessing one.
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gwdat  # noqa: E402

FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"
FFNA_MAGIC = b"ffna"
ENTRY_SIZE = 24
COMPRESSION_STORED = 0
COMPRESSION_HUFFMAN = 8

# Some file ids are stored in the id table with bit 31 set. See file_id_table().
FILE_ID_HIGH_BIT = 0x80000000

# The study copy, which nothing ever locks. See RUNBOOK.md.
#
# `RURIK_DAT` overrides it, and the reason is a hard constraint rather than a
# convenience: **a running client holds an EXCLUSIVE lock on the archive it was
# launched from**, so the server and the client can never read the same file.
# Any experiment that writes an archive therefore needs TWO copies with the same
# content -- one the client launches from, one the server reads -- and without
# this override the server would go on reading `dat_study` and answer questions
# about a map the client is not looking at. Same shape as `RURIK_VAULT` in
# `toolkit/vaultpath.py`.
#
# Set it to a copy, never to `dat_study` itself (which is the reference every
# measurement in `studies/` was taken against) and never to `C:\gw`.
DEFAULT_DAT = os.environ.get("RURIK_DAT") or r"C:\gd\Rurik\vault\dat_study\Gw.dat"


class Entry:
    __slots__ = ("index", "offset", "size", "compression", "flags",
                 "counter", "crc")

    def __init__(self, index, offset, size, compression, flags, counter, crc):
        self.index = index
        self.offset = offset
        self.size = size
        self.compression = compression
        self.flags = flags
        self.counter = counter
        self.crc = crc

    @property
    def compressed(self):
        return self.compression == COMPRESSION_HUFFMAN

    def __repr__(self):
        return (f"<Entry {self.index} at 0x{self.offset:X} {self.size}B "
                f"comp={self.compression} flags={self.flags}>")


class Archive:
    """A read-only view of Gw.dat. Never opens the file for writing."""

    def __init__(self, path=DEFAULT_DAT):
        self.path = path
        self.fh = open(path, "rb")
        head = self.fh.read(32)
        if head[:4] != FILE_MAGIC:
            raise ValueError(f"not a GW archive: magic {head[:4]!r} "
                             f"(expected {FILE_MAGIC!r})")
        self.header_size = struct.unpack_from("<I", head, 0x04)[0]
        self.block_size = struct.unpack_from("<I", head, 0x08)[0]
        self.unknown_0c = struct.unpack_from("<I", head, 0x0C)[0]
        self.mft_offset = struct.unpack_from("<I", head, 0x10)[0]
        self.mft_size = struct.unpack_from("<I", head, 0x18)[0]

        self.fh.seek(self.mft_offset)
        mft_head = self.fh.read(ENTRY_SIZE)
        if mft_head[:4] != MFT_MAGIC:
            raise ValueError(f"no MFT at 0x{self.mft_offset:X}: "
                             f"magic {mft_head[:4]!r}")
        self.entry_count = struct.unpack_from("<I", mft_head, 0x0C)[0]
        if self.entry_count * ENTRY_SIZE != self.mft_size:
            raise ValueError(
                f"MFT is internally inconsistent: {self.entry_count} entries "
                f"x {ENTRY_SIZE} != declared size {self.mft_size}. Either the "
                f"entry stride is wrong or the file is damaged.")
        self._entries = None

    def close(self):
        self.fh.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def row(self, n):
        """The entry for MFT ROW n, one-based -- the id studies quote.

        USE THIS WHENEVER YOU HAVE A ROW NUMBER. `entries` is a POSITIONAL
        list: `entries[k].index == k + 1`, so `entries[row]` is off by one and
        silently returns a DIFFERENT FILE. That is not hypothetical -- on
        2026-08-13 an archive census mixed `archive.entries[row]` with
        `textrec.TextIndex._rows[row]` (which is keyed by row number, not
        position), silently resolved a text row to a TEXTURE, and nearly filed
        a false refutation of the text-authoring plan off the back of it.

        Most callers in this tree already write `entries[row - 1]` and are
        correct; this exists so the correct thing is also the obvious thing.
        """
        # NOTE THE BOUND, which is its own instance of the confusion above:
        # `entry_count` is mft_size/24 and COUNTS THE HEADER SLOT, while
        # `entries` excludes it. So the last addressable row is
        # entry_count - 1, and bounding on entry_count walks off the end --
        # which is exactly how this was found, by the test written with it.
        last = len(self.entries)
        if not 1 <= n <= last:
            raise IndexError(
                f"MFT row {n} outside 1..{last}. Rows are ONE-based -- row 0 "
                f"does not exist, because the MFT's slot 0 is the header "
                f"rather than a file. (entry_count is {self.entry_count}, "
                f"which COUNTS that header slot and is therefore one more "
                f"than the highest row.)")
        e = self.entries[n - 1]
        # Cheap, and it is the whole point of the method: if the positional
        # convention ever changes, this fires here instead of returning a
        # plausible wrong file to a caller that cannot tell.
        assert e.index == n, f"row {n} resolved to entry {e.index}"
        return e

    @property
    def entries(self):
        """Every MFT row, POSITIONALLY. `entries[k].index == k + 1`.

        NOT keyed by row number -- see `row()`, and use it if you have one.
        """
        if self._entries is None:
            self.fh.seek(self.mft_offset + ENTRY_SIZE)
            blob = self.fh.read(self.mft_size - ENTRY_SIZE)
            out = []
            for i in range(len(blob) // ENTRY_SIZE):
                vals = struct.unpack_from("<QIHHII", blob, i * ENTRY_SIZE)
                out.append(Entry(i + 1, *vals))
            self._entries = out
        return self._entries

    def raw(self, entry):
        """The stored bytes of one entry, exactly as they sit on disk."""
        self.fh.seek(entry.offset)
        return self.fh.read(entry.size)

    def read(self, entry):
        """The entry's contents, decompressed if it needs to be."""
        data = self.raw(entry)
        if entry.compression == COMPRESSION_STORED:
            return data
        if entry.compression == COMPRESSION_HUFFMAN:
            # decompress() returns (payload, declared_size). The declared size is
            # the loop's own termination bound, so it is not a check on anything
            # -- see the caveat in gwdat.py. Take the bytes and drop it.
            payload, _declared = gwdat.decompress(data)
            return payload
        raise ValueError(f"unknown compression {entry.compression} on "
                         f"entry {entry.index}")


def file_id_table(archive):
    """Map every file id to the MFT row that holds it.

    MFT row 2 is a table of (file_id, row) u32 pairs -- 171,025 of them in this
    archive, 8 bytes each, which is exactly its declared size. Nothing had to be
    decompressed to find this; it is stored.

    This is what makes the archive addressable the way the game addresses it. A
    server hands the client a map_file_id and the client opens that file; with
    this table we can open the same one.

    MEASURED: all six of OpenTyria's map_file_id values resolve through this
    table to rows that carry the map flags -- Kamadan 0x345CC to row 22371,
    Kaineng 0x265F7 to 64474, Lion's Arch 352808 to 157484, Domain of Anguish
    219215 to 102769, Sparkfly 287493 to 126903, Lornar's Pass 46594 to 34466.
    Six for six landing on real map files is strong evidence both for this table
    layout and for upstream's map ids, two of which no source we had could
    previously corroborate.

    TWENTY-FIVE IDS CARRY BIT 31, and an exact-match lookup silently misses
    every one of them. MEASURED on this copy: 25 of the 171,023 ids have
    0x80000000 set, and for none of them is the masked form also present, so the
    two never compete. Two of the 25 land on map-flagged rows -- 0x8001B97D to
    row 7982 and 0x8001C539 to row 20118 -- and those are the Pre-Searing maps.
    Masking the bit is what makes them addressable by the id a server sends, and
    that reading is corroborated by geometry rather than by argument: see
    studies/mapdata/FORMAT.md. This function therefore registers a bit-31 id
    under both its raw and its masked form, plain ids first so that a real id can
    never be shadowed by another entry's masked one.

    Why the bit is set is NOT ESTABLISHED. We have not read the client's own
    lookup path in the binary.

    But "the client masks it" is now FALSIFIED for build 38797, measured by
    handing the client each form: 0x1B97D is refused with `Map file '0x01b97d'
    failed to load` and then an assert, while 0x8001B97D loads Ascalon City
    Pre-Searing. Masking is right HERE, for finding the row; it is wrong on the
    wire. A server must send the id exactly as the archive stores it. See
    studies/mapdata/FORMAT.md.
    """
    blob = archive.read(archive.entries[1])
    out = {}
    high = []
    for i in range(len(blob) // 8):
        file_id, row = struct.unpack_from("<II", blob, i * 8)
        if file_id & FILE_ID_HIGH_BIT:
            high.append((file_id, row))
        else:
            out.setdefault(file_id, row)
    for file_id, row in high:
        out.setdefault(file_id, row)
        out.setdefault(file_id & ~FILE_ID_HIGH_BIT, row)
    return out


def ffna_chunks(data):
    """Walk an FFNA file's chunk table.

    Yields (chunk_id, offset_of_payload, size). The walk is the best validation
    we have of the decompressor: on a real map file the chunk sizes consume the
    decompressed output to the exact byte, and that check does not depend on the
    declared output length the decoder already stops at.

    Raises ValueError if the walk runs off the end, which is what a wrong
    decompression looks like.
    """
    if data[:4] != FFNA_MAGIC:
        raise ValueError(f"not an FFNA file: {data[:4]!r}")
    # magic(4) + type(1), then the chunk table runs to the end of the file.
    pos = 5
    end = len(data)
    while pos + 8 <= end:
        chunk_id, size = struct.unpack_from("<II", data, pos)
        payload = pos + 8
        if payload + size > end:
            raise ValueError(
                f"chunk 0x{chunk_id:08X} at {pos} claims {size} bytes but only "
                f"{end - payload} remain -- decompression is probably wrong")
        yield chunk_id, payload, size
        pos = payload + size
    if pos != end:
        raise ValueError(f"chunk table ended at {pos}, file is {end} bytes")


def ffna_type(data):
    """The type byte after the magic. 3 is a map file."""
    return data[4] if len(data) > 4 else None


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DAT
    with Archive(path) as ar:
        print(f"{os.path.basename(path)}")
        print(f"  size on disk   {os.path.getsize(path)}")
        print(f"  block size     {ar.block_size}")
        print(f"  MFT offset     0x{ar.mft_offset:08X}")
        print(f"  MFT size       {ar.mft_size}")
        print(f"  entries        {ar.entry_count}")
        print(f"  0x0C unknown   0x{ar.unknown_0c:08X}")
        comp = {}
        for e in ar.entries:
            comp[e.compression] = comp.get(e.compression, 0) + 1
        print(f"  compression    {dict(sorted(comp.items()))}")
