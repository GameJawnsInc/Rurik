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
offset, seven more files. Raw MFT row indices do not survive that. Any row index
recorded in a study is only meaningful against the copy it was measured on,
which is why open() below wants an explicit path rather than guessing one.

**AND NEITHER DO FILE IDS, WHICH THIS USED TO SAY THEY DID.** The sentence above
read "File ids are content keys and should survive that" until 2026-08-13. It is
false, and the correction is the whole of `contentids.py`: bit 31 on a stored id
means `FcArchive` has renamed that row away because it requested a replacement,
and the plain id binds only after `DnArchive` installs it and re-links. So the
same map is `0x8001B97D` in one copy and `0x1B97D` on a different row in another,
and both are right for their own copy. **A file id is archive STATE.**

MEASURED, and it is why `dat_study` is no longer the copy this file once claimed:
`vault/dat_study/Gw.dat` carries 25 bit-31 ids, `vault/run/` carries 29, and
`vault/run-live/` -- a copy a client actually played live from -- carries 9 and
does not bind `0x8001B97D` at all, holding that map on row 177262 under the plain
id instead. A comment here previously described `dat_study` as "a copy of the
run-dir archive"; the two have drifted and it is not.

Because a run uses TWO copies -- the server reads one for the navmesh, the client
opens its own for the geometry -- `toolkit/contentids.py` checks that every id in
`content/maps.toml` names the SAME FILE in both, by size and crc rather than by
row, and `drive_client.assert_safe` refuses a loopback launch when it does not.
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


# --------------------------------------------------------- MFT ROW NUMBERS --
#
# THERE IS ONE ROW CONVENTION IN THIS REPO AND IT IS ARENANET'S. A row number
# is the record's index in the RAW table: row 0 is the `Mft\x1a` descriptor,
# row 1 the file header, row 2 the file-id table, row 3 the MFT itself, 4..15
# reserved spares, and `INDEX_FIRST_FILE = 16` -- the client's own constant --
# is the first claimable one.
#
# Every row number this project has ever recorded is in that convention,
# because every one of them came out of a structure that already uses it: the
# file-id table's own `row` column, `alloc.nextStream`, `datcheck.py`'s slice of
# the table, and `Entry.index` below.
#
# AUDITED 2026-08-14, and the counting rule is written down because the first
# version of this paragraph quoted three numbers ("119 distinct constants, 41 of
# them in `diff-38519-to-38797.txt`, six archives in the vault") that nobody
# could reproduce and two of which were simply wrong. RULE: the regex
# `\brows?\s+(\d{1,7})\b`, case-insensitive, over every `.py`/`.md`/`.toml`/
# `.json`/`.txt` under `toolkit/ studies/ content/ schema/ tools/` plus
# `PLAN.md CLAUDE.md HANDOFF.md RUNBOOK.md`. It yields **79 distinct row numbers
# over 536 mentions in 69 files, 65 of them >= 16**; `diff-38519-to-38797.txt`
# names **40** distinct rows on its `row N` lines (43 counting its `[0, 2, 3]`
# corroboration list); and there are **TEN** `Gw.dat` copies in the vault, all
# ten readable on 2026-08-14. The rule is coarse on purpose -- it catches
# `entries[46196]` prose and English like "row 3 is the MFT" alike -- so treat
# the count as a floor, not a census.
#
# The substance is what matters and it is checkable: of those 65, **26 resolve
# to a map-flagged row (259) under `Archive.row(N)` and exactly 1 does under
# `entries[N]`, with ZERO overlap**. Every document that calls a number a map is
# therefore written in the raw-MFT convention and still resolves to what it says.
# Renumbering either reader would silently invalidate all of them, which is why
# everything here is ADDITIVE and nothing below moves a number anyone has
# written down.
#
# THE TRAP IS NOT A SECOND CONVENTION -- EXCEPT WHERE IT WAS. IT IS THAT
# `entries` IS A LIST.
#
# `Archive.entries` is POSITIONAL, and it skips the descriptor: `entries[0]` is
# row 1. So `entries[row]` is off by one and returns a DIFFERENT FILE rather
# than raising. FOUR times so far, and two of the four were written up as facts
# about the format:
#
#   * `vault/dat_durability/ARMED.json` records `entries[46196].offset` as
#     1,132,424,192 against `datwrite`/`datcheck`'s `0x437F6800`, calls the
#     1,024-byte gap a "header or block-base convention" and tells the next
#     operator which pair to trust. RE-MEASURED 2026-08-14:
#     `entries[46195].offset` IS `0x437F6800` exactly and the 25-byte marker
#     `RURIK-DURABILITY-20260813` is in that extent; `entries[46196]` is row
#     46197 -- a different, 584-byte file with no marker that merely happens to
#     sit 1,024 bytes later. A plausible explanation was invented for an
#     off-by-one and written into a live experiment's own metadata as guidance.
#     **STILL STANDING**: the vault is gitignored, so nothing in this commit can
#     amend it. Its advice ("use datwrite/datcheck offsets for this row") is
#     right; its stated REASON is false, and a reader who believes the reason
#     distrusts `archive.py` generally. Amend it by hand.
#   * `studies/crossbuild/FINDINGS.md` §4b.1 read the same subscript as evidence
#     that "the two tools number MFT rows differently, off by exactly one", and
#     quoted `len(entries)` against `datcheck`'s row count as corroboration.
#     Both readings are refuted below and in `test_archive.py` §1c: the tools
#     agree on all 24 bytes of every row of all ten archives in the vault
#     (measured by hand 2026-08-14; §1c re-measures the copy a run is pointed
#     at), and the count they disagree on is `len(entries)` versus `row_count`,
#     not row against row. §4b.1 now carries the retraction and the table.
#   * An archive census mixed `entries[row]` with `textrec.TextIndex._rows[row]`,
#     which IS keyed by row number, resolved a text row to a TEXTURE, and nearly
#     filed a false refutation of the text-authoring plan.
#   * `datplan.py` DID hold a second convention, at three live sites, and the
#     first version of this comment missed it because it audited recorded
#     CONSTANTS and not arithmetic. `plan_overwrite` printed "MFT row 46196:
#     size and crc" against `mft_offset + (46196 - 1) * 24`, i.e. row 46195's
#     bytes; `plan_insert` printed "MFT row 3 (the table describing itself)"
#     against row 2, the FILE-ID TABLE, and "MFT row 2: file-id table size and
#     crc" against row 1, the file header. The planner applies nothing, so those
#     three addresses were handed to a human to apply by hand, to the two most
#     load-bearing rows in the archive. Fixed 2026-08-14 by routing every one of
#     them through `mft_row_offset` below; `test_datplan.py` §8 pins each edit's
#     address against the fixture's own bytes.
#
# USE `Archive.row(n)`. Where a position into `entries` is genuinely wanted, go
# through the two METHODS below so the direction is written at the call site
# instead of living in a `- 1` that reads as a typo. Where a BYTE ADDRESS is
# wanted, `mft_row_offset` is the only correct expression and both `datwrite`
# and `datplan` now call it.

#: The MFT row that `Archive.entries[0]` carries. Not a tunable -- it is the
#: descriptor slot the reader skips -- but naming it is what lets the two
#: conversions below and `test_archive.py` §1c state the same fact once.
MFT_ROW_OF_ENTRIES_0 = 1

# The structural rows, in the convention above. They live HERE, in the module
# that owns the convention, because `datcheck.py` and `datplan.py` each declared
# their own copies and one of the three was then used with the wrong arithmetic
# for months. Both import these now, so the names and the numbers are one fact.
FILE_HEADER_ROW = 1          # the 32-byte file header
FILE_ID_TABLE_ROW = 2        # the stored array of (file_id u32, row u32) pairs
MFT_SELF_ROW = 3             # the table describing itself; its crc skips its own
                             # 24 bytes -- see datwrite.py:mft_self_crc
# INDEX_FIRST_FILE, ArenaNet's own constant. Rows 4..15 are erased in every
# archive on this machine and stayed that way -- and when the client needed a
# free slot it took row 35301, reaching past twelve nearer ones. Twelve zeroed
# rows sitting immediately after the three container rows, which a working
# allocator declines to use, are reserved. Claiming one would look fine right up
# until it did not.
FIRST_CLAIMABLE_ROW = 16

# `alloc.flags` at +0x0E, with ArenaNet's own bit names -- recovered from its
# assertion strings compiled into the PE, `FLAG_ENTRY_USED` and
# `FLAG_FIRST_STREAM`. They live here for the same reason the rows above do, and
# the cost of them not living here has already been paid once: `datcheck.py` and
# `mapchunks.py` each declared a private copy, and `datplan.free_rows` -- which
# imported neither -- asked `size == 0` on its own and called a live armed map
# head a free slot. See that function; the bug was real and sat in front of the
# only code path that claims a row.
FLAG_ENTRY_USED = 0x01
FLAG_FIRST_STREAM = 0x02


def _as_row(value, what):
    """Refuse anything that is not an int.

    `row_to_position(1.5)` used to return 0.5 and `row_label(1.5)` used to print
    `row 1`, because `%d` truncates. A fractional row number is always a bug
    upstream, and silently renaming it to a DIFFERENT row is the whole failure
    class this section exists for. `bool` is an `int` and `True` really is row 1,
    so it is allowed rather than special-cased.
    """
    if not isinstance(value, int):
        raise TypeError(f"{what} must be an int, got {type(value).__name__} "
                        f"{value!r}: a fractional or textual row number would "
                        f"be truncated into a different, real row")
    return value


def mft_row_offset(mft_offset, row):
    """Byte address of MFT row `row`. `mft_offset + row * 24`, and nothing else.

    THE ONE EXPRESSION. `entries` skips the descriptor and the MFT on disk does
    not, so a `- 1` belongs in a subscript and NEVER in an address -- which is
    exactly the confusion `datplan.py` shipped for months at three sites, two of
    them naming the file-id table and the file header while claiming to name row
    3 and row 2. `datwrite.row_offset` delegates here so the two writers cannot
    drift apart again.
    """
    row = _as_row(row, "row")
    if row < 0:
        raise IndexError(f"MFT row {row} is negative; there is no row before "
                         f"the descriptor at row 0")
    return mft_offset + row * ENTRY_SIZE


def row_label(row, file_ids=(), role=None):
    """`row 71496 [file id 0x287D3; stream head]` -- a row number carrying its
    own identity.

    A BARE ROW NUMBER IS AMBIGUOUS BY CONSTRUCTION and this is the cheapest
    thing that fixes it. On 2026-08-13 `datcheck --diff` reported "row 71496
    changed from 0 B to 6,012 B" while `deploy.py` had just printed "installing
    ... head 71496, partner 71497". Read together those say the client ate our
    authored map. They do not: 71496 is the map's Bloated HEAD, which `deploy`
    arms to zero on purpose so the client is forced to recompile it, and 6,012 B
    is that recompile succeeding. Our bytes went to the partner, 71497, which is
    absent from the diff because nothing touched it. The whole misreading turns
    on the two numbers looking interchangeable in a line of output.

    A file id survives a patch where a row index does not (`contentids.py`), and
    a role says which half of a two-row map you are looking at, so a line
    carrying both cannot be crossed with another tool's by accident. `deploy.py`
    prints its file id on its first line; that is the token to match on.

    Refuses a non-int row: `row_label(1.5)` printed `row 1` before 2026-08-14,
    which is the one thing a labeller must never do -- name a real row that is
    not the row it was handed.
    """
    row = _as_row(row, "row")
    bits = []
    if file_ids:
        bits.append("file id " + ", ".join("0x%X" % f for f in file_ids))
    if role:
        bits.append(role)
    return "row %d%s" % (row, (" [" + "; ".join(bits) + "]") if bits else "")

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

    def position_of_row(self, n):
        """MFT row number -> index into `entries`. Bounded at BOTH ends.

        A METHOD rather than a free function, and that is the correction: the
        first version of this pair was pure -- `row - 1` with a low-end refusal
        -- so it could not see the high end at all, and `position_to_row(
        len(entries))` cheerfully minted row 177,342 on an archive whose highest
        row is 177,341. A conversion between a row number and a position is only
        meaningful against a table of known length, so it now takes one.
        """
        n = _as_row(n, "row")
        last = len(self.entries)
        if not MFT_ROW_OF_ENTRIES_0 <= n <= last:
            raise IndexError(
                f"MFT row {n} has no position in `entries` (rows "
                f"{MFT_ROW_OF_ENTRIES_0}..{last}). Row 0 is the descriptor slot "
                f"the reader skips -- `row - 1` there is -1, the LAST row of the "
                f"table. Use datcheck.row_bytes() to see row 0.")
        return n - MFT_ROW_OF_ENTRIES_0

    def row_of_position(self, k):
        """Index into `entries` -> MFT row number. Same as `entries[k].index`."""
        k = _as_row(k, "position")
        last = len(self.entries) - 1
        if not 0 <= k <= last:
            raise IndexError(
                f"position {k} is outside `entries` (0..{last}). A negative one "
                f"wraps to the END of the table and resolves to a plausible "
                f"wrong file; one past the end names a row that does not exist.")
        return k + MFT_ROW_OF_ENTRIES_0

    @property
    def row_count(self):
        """Rows in the raw MFT, COUNTING the descriptor at row 0.

        Equal to `entry_count`, to the descriptor's own count at +0x0C, and --
        the reason this name exists -- to `datcheck.row_count(mft)`. MEASURED
        2026-08-14 on all TEN archives in the vault (the earlier note said six;
        there are ten and all ten open): equal on every one.

        `len(self.entries)` is one LESS and is NOT a row count; it is the length
        of a list that skips the descriptor. Quoting the two against each other
        is what put "archive.py reports 177,334 rows where datcheck reports
        177,335" into `studies/crossbuild/FINDINGS.md` §4b.1 as evidence that
        the two tools number rows differently. They do not. The highest
        addressable row is `row_count - 1`, which is `len(entries)`, and that
        coincidence is exactly what makes the confusion survive a spot check.
        """
        return self.entry_count

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

    def magic(self, entry, n=4):
        """The first `n` bytes of the entry's contents, without producing the rest.

        WHY THIS EXISTS. Classifying an entry -- "is this an `ffna` model, an `ATEX`
        texture?" -- needs four bytes, and `read()` was being used for it: a full
        huffman decode of a multi-megabyte texture, thrown away after a slice.
        `test_modelexport.py` did it 1,795 times in one section. MEASURED 2026-08-14
        over 120 distinct archive rows: 9.6 s through `read()`, 0.1 s through this,
        **106x**, agreeing on the leading bytes in 40 of 40 spot-checks.

        The saving is real because `decompress()` already takes `out_size` and its
        loop terminates on it -- this is not a new decoder, it is the existing one
        asked to stop early. Note that the DISK read is still whole: `raw()` fetches
        `entry.size` compressed bytes either way, and the win is the decode, which is
        where the time was.

        Returns fewer than `n` bytes when the entry holds fewer -- a short entry is a
        fact about the archive, not an error, and the caller comparing against a
        4-byte magic will simply not match.
        """
        data = self.raw(entry)
        if entry.compression == COMPRESSION_STORED:
            return bytes(data[:n])
        if entry.compression == COMPRESSION_HUFFMAN:
            payload, _declared = gwdat.decompress(data, out_size=n)
            return bytes(payload[:n])
        raise ValueError(f"unknown compression {entry.compression} on "
                         f"entry {entry.index}")

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


def file_id_table(archive, raw=False):
    """Map every file id to the MFT row that holds it.

    **`raw=True` DISABLES the dual registration described below, and any caller
    asking "what will the CLIENT do?" must pass it.** The default answers for
    *our* reader, which registers a bit-31 id under both spellings so a row is
    easy to find; the client does no such thing (see THE CLIENT DOES NOT MASK
    below). Getting that backwards has now cost this repo three separate
    failures, so the two questions are now two different calls:

        file_id_table(ar)             # what OUR tools can find      (convenience)
        file_id_table(ar, raw=True)   # what the CLIENT can address  (the truth)

    The three, recorded because the pattern is what matters and not the count:
    `content/maps.toml` carried the renamed `0x8001B97D` as if it were the map's
    name; `toolkit/contentids.py` cleared a client/server pair that then died at
    `Code=007` with the client hanging up right after `0x0199`; and the minimap
    arc's rung S9 concluded "all four of map 148's tiles are present in the
    archive the client opened" -- they were present as ROWS and unaddressable by
    the plain id, which is why every compass frame in the vault was the NULL
    fallback and why it took four rungs to find (studies/minimap/FINDINGS.md 6e).
    In all three the helper answered a true thing about the wrong question.

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
    every one of them. MEASURED on this copy: 25 of the 171,025 ids have
    0x80000000 set, and for none of them is the masked form also present, so the
    two never compete. Two of the 25 land on map-flagged rows -- 0x8001B97D to
    row 7982 and 0x8001C539 to row 20118 -- and those are the Pre-Searing maps.
    Masking the bit is what makes them addressable by the id a server sends, and
    that reading is corroborated by geometry rather than by argument: see
    studies/mapdata/FORMAT.md. This function therefore registers a bit-31 id
    under both its raw and its masked form, plain ids first so that a real id can
    never be shadowed by another entry's masked one.

    WHY THE BIT IS SET -- ANSWERED 2026-08-13, by reading the client's own
    lookup path. **It is a RENAME, not a spelling.** `FcArchive` binds
    `id | 0x80000000` to the row and deletes the plain name when it has requested
    a replacement (Gw.exe 0x007D7B70, twelve instructions); `DnArchive` re-links
    the plain id once the replacement is installed (0x004766F0). So a bit-31 id
    means "this row's replacement is pending", and the plain id genuinely stops
    resolving until it lands. The count moves with play: 25 in `dat_study`, 29 in
    the owner's live install, **9** in `vault/run-live/`, the copy a live client
    actually played from -- where `0x1B97D` binds PLAINLY, to a different row.

    **THE CLIENT DOES NOT MASK.** The index it builds from this table stores the
    id verbatim (0x0047C027) and the lookup is an exact 32-bit compare
    (0x0047AA20), with no retry on the map path. So the dual registration below
    is OUR convenience for finding a row, and it is NOT a model of the client:
    it will answer `0x1B97D` where the client would miss. That difference is not
    hypothetical -- it put a wrong MFT row into a study draft, because the id was
    resolved here against an archive the client was never reading.

    "The client masks it" was FALSIFIED for build 38797 by handing the client each
    form, and the falsification stands; the RULE drawn from it did not. A server
    should send the **plain logical id** and serve from an archive that binds it.
    `0x8001B97D` works against `dat_study` only because that copy has the map
    renamed away. **A file id recorded anywhere is archive STATE, not a property
    of the map.** See studies/maprows/FINDINGS.md §8 and studies/mapdata/FORMAT.md.
    """
    blob = archive.read(archive.row(FILE_ID_TABLE_ROW))
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
        # THE MASKED ALIAS IS THE CONVENIENCE, AND IT IS WHAT `raw` TURNS OFF.
        # Registering it is what lets our tools find a renamed row by the id a
        # server sends; it is also exactly what the client will NOT do.
        if not raw:
            out.setdefault(file_id & ~FILE_ID_HIGH_BIT, row)
    return out


def binds_plainly(archive, file_id):
    """Would the CLIENT find `file_id` in this archive? (row, or None.)

    The client's index stores the id verbatim (0x0047C027) and its lookup is an
    exact 32-bit compare (0x0047AA20) with no retry on the map path, so this is
    a raw-table hit and nothing else. Use it for any launch-time question about
    what the client can open; `file_id_table(ar)` answers about our own reader
    and will say yes where the client says no.
    """
    return file_id_table(archive, raw=True).get(file_id)


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
        # BOTH numbers, labelled, because printing one of them under the word
        # "entries" is how they came to be quoted against each other. The row
        # count is the one another tool can be compared with.
        print(f"  MFT rows       {ar.row_count}  (rows 0..{ar.row_count - 1}; "
              f"row 0 is the descriptor)")
        print(f"  len(entries)   {len(ar.entries)}  (positional; entries[0] is "
              f"row {MFT_ROW_OF_ENTRIES_0} -- NOT a row count)")
        print(f"  0x0C unknown   0x{ar.unknown_0c:08X}")
        comp = {}
        for e in ar.entries:
            comp[e.compression] = comp.get(e.compression, 0) + 1
        print(f"  compression    {dict(sorted(comp.items()))}")
