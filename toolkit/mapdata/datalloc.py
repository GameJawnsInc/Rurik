"""Allocate. Create rows that did not exist, and make the client able to name them.

`datwrite --replace` puts new bytes in a row that already exists. `datmove`
moves such a row somewhere it fits. Both start from a row ArenaNet made, which
means every authored map so far has been installed by DISPLACING one -- map 143,
file id 0x287D3, is a real retail area in the owner's own copy and we still do
not know which one. This module is the third verb, the one that stops requiring
a victim: it appends MFT rows for a file that never existed and registers it in
the file-id table so the client can address it.

    python toolkit/mapdata/datalloc.py --dat COPY --plan --stream head.bin --stream part.bin
    python toolkit/mapdata/datalloc.py --dat COPY --file-id 0x5F100 --map --data stripped.bin --plan
    python toolkit/mapdata/datalloc.py --dat COPY --file-id 0x5F100 --map --data stripped.bin --alloc --confirm
    python toolkit/mapdata/datalloc.py --dat COPY --file-id 0x5F100 --plan --stream head.bin:259 --stream part.gwenc:1:8 --expect part.raw
    python toolkit/mapdata/datalloc.py --dat COPY --next-id

`FILE:FLAGS:EXTRA` is the only way to allocate a COMPRESSED row, and the third
field is not a formality: `extraBytes` 8 is what makes the client decompress the
bytes rather than hand them back, and this module compresses nothing -- the
payload has to be `gwenc` output already. Everything the gate does about that is
at `plan_alloc` below.

`--expect FILE` IS MANDATORY WITH EXTRA 8, and the reason is the whole of
FINDINGS C-6: the entry crc is over the STORED bytes, so a stream that decodes to
the wrong payload -- or to one byte fewer -- passes both crc rules, all ten of
`datcheck`'s open-time rules and `datmove.overlaps`, and the archive is green
while the file is unreadable. The decompress-and-compare is the only refutation
that exists and it is only available before the write.
`datmove --compression 8` has required its own `--expect` since 2026-08-18; this
verb was the last writer of the three without one, and a skeptic drove exactly
that door on 2026-08-19 -- a gwenc stream with a corrupted trailer allocated
through `alloc(confirm=True)` AND through this CLI, `Archive.read()` handed back
8,191 bytes instead of 8,192, and `--verify`, preflight and the overlap sweep
were all green.

WHY THIS IS NOT `datplan.plan_insert` WITH A WRITER BOLTED ON. The planner
computes a single row and stops one field short of a usable file, in three ways
that each look fine on paper:

  * **It plans no `alloc.nextStream`.** A Guild Wars map is TWO rows -- a
    Bloated head (`alloc.flags` 3, stream 1, the u16 259) chained to a Stripped
    partner (`alloc.flags` 1, stream 0) -- and the chain lives at entry +0x10 as
    a ROW INDEX. One row is not a map, and `plan_insert` has no concept of a
    second one; called twice it returns the SAME row index both times, because
    neither call knows about the other.
  * **Its file id is optional and defaults to None**, which emits the note "no
    file id requested; skipping the file-id table edit". That is not a smaller
    version of the operation, it is a self-deleting one. The client's open-time
    reconcile at `0x0047B7D7` -> `0x0047BE50` runs UNCONDITIONALLY -- it is not
    gated by the dirty flag -- and for a USED|FIRST_STREAM row at index >= 16
    with no file-id record it logs "Entry %u exists in mft but not directory",
    FREES THE EXTENT and memsets the 24 bytes. The file works exactly once.
    Here the id is a required argument and its absence is a refusal.
  * **Its erased-slot branch was dangerous until the same day this was written.**
    `datplan.free_rows` tested `size == 0` alone, and an ARMED MAP HEAD has size
    0 by design. On `vault/dat_c2/Gw.dat` it returned `[71496]`, the head of map
    143. Fixed there, and this module additionally refuses to claim any row it
    did not prove is USED-clear.

WHAT MAKES AN ALLOCATION SAFE. Every one of these is a refusal, not a note --
`plan_insert` appends to `plan.blockers` and returns a plan anyway, which is easy
to read past.

  * **The MFT grows only into the slack in its own last block.** This is the
    binding constraint and it is much tighter than it looks. The gap measure says
    the 38833 live archive has 4,266,920 bytes of headroom above the table; the
    honest figure is 424 bytes, because the very next block is either a container
    generation the client is about to rotate onto or -- on that archive -- the
    end of the file, the MFT's reservation ending at EXACTLY EOF. MEASURED
    2026-08-15 across the vault: the slack is 48 B (2 rows) on the dat_study
    family and 424 B (17 rows) on the 38833 copies, and in every case it is
    precisely `512 - (mft_size % 512)`. Seventeen rows is eight authored maps.
  * **The file is never extended.** Growth past EOF is unrevertible in principle,
    not just unimplemented: the journal stores each range's previous bytes, and
    bytes that did not exist have none, so undoing a growth means truncating and
    the format cannot say that. Refused rather than half-supported.
  * **Placement comes from `datplan.classify_runs`, never `free_runs`**, and
    successive streams CONSUME from the usable list, so two rows of one file
    cannot be handed the same run. The reservation must also fall wholly inside
    EOF -- `datcheck` rule 5 tests `offset + size`, not the block-rounded
    reservation, so an overhanging tail run passes preflight and then short-reads
    in `Writer.put`.
  * **Exactly one row carries FIRST_STREAM and exactly that row gets the id.**
    Registering the partner instead is the natural symmetric mistake and no crc
    or preflight rule refuses it; MEASURED on dat_study, the table names 349 map
    heads and zero partners.
  * **The id must be free**, checked in the RAW table -- the form the client can
    address -- as well as the convenience form. Nothing in `datcheck` counts a
    file id twice, so a collision is invisible to every rule we have.

THE WINDOW, stated rather than hidden. Between the descriptor's entry count and
the header's declared MFT size there are two 4-byte writes, and no ordering makes
them one; in between, `entry_count * 24 != mft_size` and `Archive.__init__`
refuses to open the file at all. That is why `datwrite.mft_offset_of` now reads
the header directly and `revert()` uses it: the recovery path must survive the
one state it exists for. Both writes are fsynced, the window is two syscalls
wide, and everything either side of it is openable and diagnosable.

WHAT THIS DOES NOT ESTABLISH, and it is the same sentence `datmove` carries: **no
client has ever read a row this module allocated.** Everything below is about the
archive's own rules -- the three crc rules, 512-byte alignment, whole-block
reservations, non-overlapping extents, the ten open-time rules `datcheck`
enforces, and the reconcile pass that deletes undirectoried rows. Whether the
retail client accepts an MFT row WE appended is exactly the question `datplan`'s
docstring separates out and declines to answer on paper. It is one caged run
away and has not been made.
"""

import argparse
import binascii
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import (Archive, DEFAULT_DAT, ENTRY_SIZE,  # noqa: E402
                     FILE_ID_HIGH_BIT, FILE_ID_TABLE_ROW, FIRST_CLAIMABLE_ROW,
                     FLAG_ENTRY_USED, FLAG_FIRST_STREAM,
                     MFT_SELF_ROW, file_id_table, mft_row_offset)
import datplan  # noqa: E402
import datwrite  # noqa: E402

# Field offsets inside a 24-byte MFT row, with ArenaNet's own names. `datmove`
# declares the first four; the fifth is why this module exists and neither of the
# other two writers has ever needed it.
ENTRY_OFFSET_OFF = 0x00      # u64 alloc.offset
ENTRY_SIZE_OFF = 0x08        # u32 alloc.size
ENTRY_EXTRA_OFF = 0x0C       # u16 alloc.extraBytes  (archive.py: "compression")
ENTRY_FLAGS_OFF = 0x0E       # u16 alloc.flags       (low byte flags, high stream)
ENTRY_NEXT_OFF = 0x10        # u32 alloc.nextStream  (archive.py: "counter")
ENTRY_CRC_OFF = 0x14         # u32 alloc.crc

HDR_MFT_SIZE = 0x18          # u32 in the 32-byte file header
MFT_HDR_COUNT = 0x0C         # u32 in the MFT's own descriptor row

# A map's two rows, as `mapchunks` names them. Repeated here as defaults only;
# the caller may pass anything and the shape rules below are what is enforced.
MAP_HEAD_FLAGS_U16 = 259     # stream 1, alloc.flags USED|FIRST_STREAM
MAP_PARTNER_FLAGS_U16 = 1    # stream 0, alloc.flags USED


class Refused(Exception):
    """An allocation that will not happen, with the number a person needs."""


class Stream:
    """One row of a new file's chain.

    `data` may be empty. A zero-length row is a legal archive state and for a map
    head it is the documented re-bloat trigger -- `deploy.py` arms the head to
    zero precisely so ArenaNet's own converter rebuilds the Bloated stream from
    the Stripped partner. A zero-length row owns no extent, so it needs no
    placement and takes no free space.

    `expect` IS THE PAYLOAD A READER MUST GET BACK, and it is MANDATORY whenever
    `extra_bytes` is 8. It is not a second copy of `data`: for a compressed row
    `data` is the stream and `expect` is what `gwdat.decompress` has to produce
    from it, and the two being different is the only reason the check has any
    power. For a stored row the bytes ARE the payload, so `expect` is optional
    there and passing it is the caller stating that positively -- the same
    spelling `datmove --compression 0 --expect` has.

    `stored_lookalike_ok` is the C-6 escape hatch and mirrors `datwrite`'s flag of
    the same name. Declaring 0 over bytes that DECODE as a compression-8 stream is
    refused, because that is the green-archive-holding-an-unreadable-file state;
    MEASURED, 4 of 38,621 real stored rows decode anyway, so those four need a way
    through and this is it. Deliberately awkward, and it prints a line naming C-6
    when taken.
    """

    __slots__ = ("data", "flags", "extra_bytes", "expect", "stored_lookalike_ok")

    def __init__(self, data, flags, extra_bytes=0, expect=None,
                 stored_lookalike_ok=False):
        self.data = bytes(data)
        self.flags = int(flags)
        self.extra_bytes = int(extra_bytes)
        self.expect = None if expect is None else bytes(expect)
        self.stored_lookalike_ok = bool(stored_lookalike_ok)

    @property
    def alloc_flags(self):
        return self.flags & 0xFF

    @property
    def is_first(self):
        return bool(self.alloc_flags & FLAG_FIRST_STREAM)


class RowPlan:
    """Where one appended row goes and every field it will carry."""

    __slots__ = ("index", "offset", "size", "reservation", "flags",
                 "extra_bytes", "next_stream", "crc", "reused")

    def __init__(self, index, offset, size, reservation, flags, extra_bytes,
                 next_stream, crc, reused):
        self.index = index
        self.offset = offset
        self.size = size
        self.reservation = reservation
        self.flags = flags
        self.extra_bytes = extra_bytes
        self.next_stream = next_stream
        self.crc = crc
        self.reused = reused

    def show(self):
        how = "reused (USED-clear spare)" if self.reused else "appended"
        where = (f"0x{self.offset:X} +{self.reservation}"
                 if self.size else "no extent (zero length)")
        print(f"  row {self.index} ({how}): {where}, size {self.size}, "
              f"flags 0x{self.flags:04X}, extraBytes {self.extra_bytes}, "
              f"nextStream {self.next_stream}, crc 0x{self.crc:08X}")


class AllocPlan:
    """Every byte that would change. Nothing written."""

    __slots__ = ("rows", "file_id", "id_offset", "id_spare_after",
                 "mft_grow_rows", "mft_slack_before", "old_entry_count",
                 "old_mft_size", "block", "usable_before", "largest_usable")

    def __init__(self, rows, file_id, id_offset, id_spare_after, mft_grow_rows,
                 mft_slack_before, old_entry_count, old_mft_size, block,
                 usable_before, largest_usable):
        self.rows = rows
        self.file_id = file_id
        self.id_offset = id_offset
        self.id_spare_after = id_spare_after
        self.mft_grow_rows = mft_grow_rows
        self.mft_slack_before = mft_slack_before
        self.old_entry_count = old_entry_count
        self.old_mft_size = old_mft_size
        self.block = block
        self.usable_before = usable_before
        self.largest_usable = largest_usable

    @property
    def head(self):
        return self.rows[0]

    @property
    def new_entry_count(self):
        return self.old_entry_count + self.mft_grow_rows

    @property
    def new_mft_size(self):
        return self.old_mft_size + self.mft_grow_rows * ENTRY_SIZE

    def show(self):
        print(f"ALLOCATE {len(self.rows)} row(s) under file id "
              f"0x{self.file_id:X}")
        for r in self.rows:
            r.show()
        print(f"  file-id table: append (0x{self.file_id:X}, "
              f"{self.head.index}) at 0x{self.id_offset:X}; "
              f"{self.id_spare_after} bytes = {self.id_spare_after // 8} pairs "
              f"spare afterwards")
        if self.mft_grow_rows:
            print(f"  MFT grows {self.mft_grow_rows} row(s): entry count "
                  f"{self.old_entry_count} -> {self.new_entry_count}, size "
                  f"{self.old_mft_size} -> {self.new_mft_size}; "
                  f"{self.mft_slack_before} bytes of last-block slack before, "
                  f"{self.mft_slack_before - self.mft_grow_rows * ENTRY_SIZE} "
                  f"after")
        else:
            print(f"  MFT does not grow (every row reused a USED-clear spare)")
        print(f"  free space: {self.usable_before} usable run(s), largest "
              f"{self.largest_usable} B")


# --------------------------------------------------------------- measurement

def mft_slack(ar):
    """Bytes the table can grow into WITHOUT taking a new 512-byte block.

    This is the real capacity figure and it is not the one `plan_insert` prints.
    That function bounds itself by the next ALLOCATED entry, which on the 38833
    archives is the end of the file and yields "177,788 more rows"; it then
    narrows to a container wall if it finds one. Both are the gap measure, and
    the gap measure counts space the client owns.

    The honest bound needs no scan at all. The MFT's reservation is whole blocks
    like every other row's, so the table may grow to the end of the block it
    already occupies and no further -- the next block is somebody else's by
    definition, whether that somebody is a container generation, an allocated
    entry, or the end of the file. MEASURED across thirteen archive copies: the
    answer is always exactly `-mft_size % 512`, and it ranges from 48 bytes
    (2 rows, the dat_study family) to 424 (17 rows, the 38833 pair).
    """
    return -ar.mft_size % ar.block_size


def id_table_slack(ar):
    """(offset of the first unused pair, spare bytes) in the file-id table.

    The table is stored, not compressed, and its reservation is whole blocks like
    anything else, so the pairs past `size` are inside space it already owns.
    Those bytes are NOT zero -- MEASURED, the padding on the 38833 copies decodes
    to 56 pairs of which one has a plausible row -- so "append where the zeros
    start" would land at an arbitrary offset inside stale data. Append at
    `offset + size`, always.
    """
    tbl = ar.row(FILE_ID_TABLE_ROW)
    reservation = datplan.blocks_for(tbl.size, ar.block_size) * ar.block_size
    return tbl.offset + tbl.size, reservation - tbl.size


def next_free_file_id(ar, start=None):
    """The lowest unused PLAIN file id at or above `start`.

    Read from the RAW table, because that is the form the client can address;
    `file_id_table`'s default also registers the bit-31 spelling of every id as a
    convenience of ours and would make ids look taken that the client cannot
    reach.

    BIT 31 IS EXCLUDED FROM THE SEARCH AND FROM THE MAXIMUM, and the second half
    is what this got wrong. `max(taken) + 1` over the raw table returns a bit-31
    id whenever any renamed id is present -- and `plan_alloc` then REFUSES that
    id, because bit 31 is `FcArchive` announcing a pending replacement. MEASURED
    2026-08-15 over every readable copy in the vault: `--next-id` printed an id
    its own sibling refuses on **9 of 13**, including `dat_study`, the default
    `--dat`. It happened to work on the three 38833 copies, whose highest id is
    the plain 0x5F0AF -- which is why a first smoke test on the live archive
    passed and the defect survived it.

    A renamed id still SPEAKS FOR its plain form -- `0x8001B97D` is Pre-Searing's
    `0x1B97D` with a replacement pending -- so both spellings count as taken.
    """
    raw = set(file_id_table(ar, raw=True))
    taken = set()
    for fid in raw:
        taken.add(fid)
        taken.add(fid & ~FILE_ID_HIGH_BIT)
    plain = [f for f in taken if not f & FILE_ID_HIGH_BIT]
    if start is None:
        start = (max(plain) if plain else 0) + 1
    fid = int(start)
    while fid in taken:
        fid += 1
    if fid & FILE_ID_HIGH_BIT:
        raise Refused(
            f"no free plain file id at or above 0x{int(start):X}: the search "
            f"reached 0x{fid:X}, which sets bit 31 (the FcArchive rename "
            f"marker) and is not an id the client can be given.")
    return fid


# ---------------------------------------------------------------- the plan

def _place(usable, block, need_bytes, filesize):
    """Best fit, CONSUMING the run so the next stream cannot be given it too.

    Returns `(offset, reservation, usable_after)`. `datplan.best_fit` is a pure
    query over a list; calling it twice with the same list is how two rows of one
    file end up at one address. The remainder of a partly-used run is handed back
    so a small second stream can still land in it.
    """
    need = datplan.blocks_for(need_bytes, block)
    fit = datplan.best_fit(usable, need)
    if fit is None:
        largest = max((n for _s, n in usable), default=0) * block
        raise Refused(
            f"nothing fits: {need_bytes} B needs {need} block(s) and the "
            f"largest run datplan will hand over is {largest} B.\n"
            f"  Runs carrying live container generations are withheld whole and "
            f"that is not a limit to work around. This archive cannot take the "
            f"payload without growing, which this module does not do.")
    start, blocks = fit
    offset = start * block
    reservation = need * block
    if offset + reservation > filesize:
        raise Refused(
            f"the best-fit run at 0x{offset:X} reserves {reservation} B and "
            f"runs past the end of the file (0x{filesize:X}).\n"
            f"  `free_runs` rounds the file up to a whole block, so the last run "
            f"can overhang EOF. datcheck rule 5 tests offset+SIZE and would pass "
            f"this; Writer.put would then short-read. Refused here instead.")
    rest = [r for r in usable if r != fit]
    if blocks > need:
        rest.append((start + need, blocks - need))
        rest.sort()
    return offset, reservation, rest


def check_declarations(streams, announce=True):
    """Every stream's DECLARATION checked against its bytes. Raises `Refused`.

    ADDED 2026-08-20, and it closes the last door of FINDINGS C-6 in this trio.
    `plan_alloc`'s own comp-8 gate decides by DECODING (`looks_compressed`), which
    refutes FRAMING damage -- a stream that runs out of input -- and nothing else:
    `gwdat.decompress` takes the output size from the TRAILER and uses it as the
    decode loop's own bound, so a stream whose trailer was corrupted decodes
    happily to a different length and one whose middle was flipped decodes happily
    to different bytes. MEASURED by a skeptic on 2026-08-19 over 528 single-byte
    flips of one real `gwenc` stream: 132 refused, 394 accepted having decoded to
    something else, 2 still decoded to the payload. Two of those 394 were driven
    all the way to disk through `alloc(confirm=True)` and through
    `--stream FILE:1:8`, and every check this project owns stayed green.

    `datwrite.declaration_fault` is the refutation and it already existed -- this
    module simply never called it, which is what made the gate a framing check
    wearing a fidelity check's name. It is called here for EVERY stream, not only
    the compressed ones, because the compression-0 direction is the other half of
    C-6: a genuine `gwenc` stream declared `extraBytes 0` allocates a row the
    client hands back still compressed. `test_datalloc.py` §13 recorded that as an
    OPEN GAP for a day and this is the guard it named.

    THE FALSE-REFUSAL COST IS MEASURED AND IT IS SMALL: 4 of 38,621 real stored
    rows in `dat_study` decode as compression 8 and would be refused here, against
    0 of 1,500 decompressed retail payloads -- the population an authoring caller
    actually hands us. Those four take `stored_lookalike_ok=True`, the same hatch
    `datwrite` gives them.

    AN EMPTY STORED STREAM PASSES THROUGH UNCHANGED, deliberately and not by a
    special case: `declaration_fault(b"", 0, None)` returns None, because
    `looks_compressed(b"")` is False on the length test. The armed map head --
    `Stream(b"", 259)`, the re-bloat trigger `deploy.py` depends on -- is
    therefore untouched. Comp-8 emptiness is NOT special-cased either, in the
    other direction: `declaration_fault` refuses a zero-BLOCK compression-8 stream
    (FINDINGS 13.5 gap D, a 12-byte stream that decompresses to nothing), and that
    refusal has to stay reachable from here.

    `announce` prints the C-6 override line when the hatch is taken, exactly as
    `datwrite.replace` does. It is off when `alloc` runs the gate over streams
    `plan_alloc` is about to run it over again, so the line appears once.
    """
    for i, s in enumerate(streams):
        if s.extra_bytes == 8 and s.expect is None:
            raise Refused(
                f"stream {i} declares extraBytes 8 and no expected payload came "
                f"with it.\n"
                f"  A compression-8 row is the one thing in this archive nothing "
                f"can check afterwards: the entry crc is over the STORED bytes, "
                f"so a stream that decodes to the wrong payload -- or to one byte "
                f"fewer -- passes both crc rules, all ten of datcheck's open-time "
                f"rules and the overlap sweep, and the archive is green while the "
                f"file is unreadable. The decompress-and-compare is the ONLY "
                f"refutation there is and it is only available before the write.\n"
                f"  `datmove --compression 8` has required --expect since "
                f"2026-08-18 and this verb was the last writer of the three "
                f"without one. Pass Stream(..., extra_bytes=8, expect=PAYLOAD), "
                f"or --expect FILE from the command line.")
        code = 8 if s.extra_bytes == 8 else 0
        fault = datwrite.declaration_fault(
            s.data, code, expect=s.expect,
            stored_lookalike_ok=s.stored_lookalike_ok)
        if announce and s.stored_lookalike_ok and code == 0 \
                and datwrite.looks_compressed(s.data):
            # An override that leaves no trace is the same defect as no override.
            print(f"  !! C-6 OVERRIDE TAKEN on stream {i}: these bytes DECODE as "
                  f"a compression-8 stream and are being allocated as extraBytes "
                  f"0 anyway. If that is wrong, the archive will be green and the "
                  f"file unreadable, and nothing we own can detect it afterwards. "
                  f"FINDINGS C-6.")
        if fault:
            raise Refused(
                f"will not allocate stream {i} as compression {code}.\n"
                f"  {fault}")


def plan_alloc(ar, streams, file_id, classified=None):
    """Where a brand-new file's rows would go. Read-only; raises `Refused`.

    `streams` is the file's chain in order. The first carries FIRST_STREAM and is
    the row the file id resolves to; the rest are its continuations, linked by
    `alloc.nextStream`. For a map that is exactly two: an (often zero-length)
    Bloated head and the Stripped partner that holds the geometry.
    """
    block = ar.block_size
    filesize = os.path.getsize(ar.path)

    if not streams:
        raise Refused("no streams: there is nothing to allocate")
    if file_id is None:
        raise Refused(
            "a file id is REQUIRED, and this is the one refusal that is about "
            "the client rather than about us.\n"
            "  The open-time reconcile at 0x0047B7D7 runs unconditionally and "
            "DELETES a USED|FIRST_STREAM row at index >= 16 that no file-id "
            "record names -- it frees the extent and memsets the 24 bytes. An "
            "unregistered row is not a smaller allocation, it is one that "
            "works once and vanishes at the next launch.\n"
            "  `datalloc.py --next-id` prints the lowest id nothing binds.")
    file_id = int(file_id)
    if file_id <= 0 or file_id >= 0x80000000:
        raise Refused(
            f"file id 0x{file_id:X} is out of range: bit 31 is the FcArchive "
            f"rename marker and 0 is the released-record sentinel")

    raw = file_id_table(ar, raw=True)
    if file_id in raw:
        raise Refused(
            f"file id 0x{file_id:X} already binds to row {raw[file_id]} in this "
            f"archive.\n"
            f"  Nothing in datcheck counts a file id twice -- MEASURED, a "
            f"duplicate record passes all ten rules -- so this refusal is the "
            f"only thing between a collision and an archive where one of two "
            f"files is unreachable. Use --next-id.")

    # Shape. Exactly one FIRST_STREAM, and it is the one the id will name.
    for i, s in enumerate(streams):
        if not s.alloc_flags & FLAG_ENTRY_USED:
            raise Refused(
                f"stream {i} has flags 0x{s.flags:04X}, with FLAG_ENTRY_USED "
                f"clear.\n"
                f"  LoadMft pushes every USED-clear row at index >= 16 onto a "
                f"spare stack that NewEntry pops, so the client would hand this "
                f"row to an unrelated file at the next launch.")
        if i == 0 and not s.is_first:
            raise Refused(
                f"the first stream has flags 0x{s.flags:04X}, without "
                f"FLAG_FIRST_STREAM. The head is the row the file id resolves "
                f"to and it is the row the reconcile pass checks.")
        if i and s.is_first:
            raise Refused(
                f"stream {i} carries FLAG_FIRST_STREAM. Only the head may: "
                f"`nextStream` targets are continuations, and MEASURED on "
                f"dat_study the corpus-wide link map is a bijection with no "
                f"target referenced twice.")
        if s.extra_bytes > len(s.data):
            raise Refused(
                f"stream {i} declares extraBytes {s.extra_bytes} > size "
                f"{len(s.data)}; ArenaNet's own assert is `extraBytes <= size` "
                f"at VA 0x93f2fc")
        # `extraBytes <= size` is ArenaNet's rule and it is not enough: it
        # accepts 8 on a plainly stored payload, and NOTHING downstream would
        # notice. The row crc is over the stored bytes and is right either way,
        # `datwrite --verify` reads only the two container checksums, and no
        # datcheck rule looks at +0x0C outside the file-id table row. The archive
        # would be wrong only in the client.
        #
        # So the rule here is positive rather than permissive, and it is
        # MEASURED on vault/run-live/2026-08-13/Gw.dat: across 177,740 live rows
        # +0x0C takes exactly two values, {0: 38682, 8: 139058}, and a payload
        # with 8 carries 0x0102 at bytes 2..4 -- 6,000 of 6,000 sampled, against
        # 0 of 6,000 stored-row controls. A perfect split on 12,000 rows, and a
        # rule the artifact could have refuted at any of them.
        if s.extra_bytes not in (0, 8):
            raise Refused(
                f"stream {i} declares extraBytes {s.extra_bytes}. The corpus "
                f"holds only 0 and 8; anything else is a value we have never "
                f"seen the client produce or read.")
        # CHANGED 2026-08-18: this gate was `s.data[2:4] != b"\x01\x02"`, a two-byte
        # MARKER with no decode, and it is wrong in BOTH directions -- measured.
        #   * It ACCEPTS bytes nothing can read. `b"ab\x01\x02efgh"` carries the
        #     marker and is obviously not a stream, and `test_datalloc.py` asserted
        #     that acceptance as CORRECT, pinning the defect. This is the row
        #     CREATION path, i.e. the one rung A8 will most plausibly use, so it
        #     could mint a brand-new compression-8 row that is green everywhere and
        #     unreadable -- FINDINGS C-6, reached from the other end.
        #   * It REFUSES bytes that are genuinely compressed. `gwenc.encode()` output
        #     from a small payload has `data[2] == 0x00`, so the marker is absent and
        #     real streams were turned away.
        # `looks_compressed` decides by DECODING, which fixes both. Its recall is
        # 600/600 on real comp-8 rows and 92/92 on gwenc streams across 23 sizes,
        # against a marker that misses 41 of those 92 (FINDINGS 14).
        if s.extra_bytes == 8 and not datwrite.looks_compressed(s.data):
            raise Refused(
                f"stream {i} declares extraBytes 8, the compressed framing, but "
                f"its payload does not DECODE as a compression-8 stream.\n"
                f"  This module writes payloads verbatim and compresses nothing, "
                f"so 0 is almost certainly what is meant. Declaring 8 over a "
                f"stored payload produces an archive that is wrong only in the "
                f"client: the row crc still matches, --verify still passes, and "
                f"no datcheck rule looks at this field.")

    # AND THE DECLARATION AGAINST THE BYTES, which the loop above cannot do: it
    # decides whether these bytes ARE a stream, never whether they are the RIGHT
    # one. Runs after the shape loop so a stream that is malformed in both ways is
    # named by the cheaper, sharper refusal first.
    check_declarations(streams)

    # Rows. Reuse genuinely-spare slots before growing the table -- the slack is
    # the scarcest thing in the archive. `free_rows` now tests the USED flag as
    # well as the size, so an armed map head is no longer offered here.
    spares = list(datplan.free_rows(ar))
    for r in spares:
        e = ar.row(r)
        if e.flags & FLAG_ENTRY_USED or e.size:
            raise Refused(
                f"datplan.free_rows offered row {r}, which has size {e.size} "
                f"and flags 0x{e.flags:04X}. A claimable row must be erased AND "
                f"USED-clear; this one is in use.")

    indices, reused = [], []
    grow = 0
    for _ in streams:
        if spares:
            idx = spares.pop(0)
            reused.append(True)
        else:
            idx = ar.row_count + grow
            grow += 1
            reused.append(False)
        indices.append(idx)

    slack = mft_slack(ar)
    if grow * ENTRY_SIZE > slack:
        raise Refused(
            f"the MFT cannot take {grow} more row(s).\n"
            f"  It has {slack} bytes of slack in its own last 512-byte block = "
            f"{slack // ENTRY_SIZE} row(s), and growing past that means taking "
            f"the next block, which is a container generation the client "
            f"rotates onto or the end of the file. On the 38833 archives the "
            f"table's reservation ends at EXACTLY EOF.\n"
            f"  Extending the file is not the fallback: the journal stores each "
            f"range's previous bytes, bytes past EOF have none, and undoing a "
            f"growth would mean a truncation the format cannot express.")

    # Placement, consuming as we go. Zero-length rows own no extent.
    usable, _excluded = classified if classified else datplan.classify_runs(ar)
    usable_before = len(usable)
    largest = max((n for _s, n in usable), default=0) * block
    pool = list(usable)
    rows = []
    for i, s in enumerate(streams):
        if s.data:
            offset, reservation, pool = _place(pool, block, len(s.data),
                                               filesize)
        else:
            offset, reservation = 0, 0
        nxt = indices[i + 1] if i + 1 < len(streams) else 0
        rows.append(RowPlan(indices[i], offset, len(s.data), reservation,
                            s.flags, s.extra_bytes, nxt,
                            binascii.crc32(s.data), reused[i]))

    # Every nextStream target must satisfy the loader: in [16, count) and
    # acyclic. Ours are strictly increasing by construction, so the walk cannot
    # cycle; the range is the half that can actually be got wrong.
    new_count = ar.entry_count + grow
    for r in rows:
        if r.next_stream and not (FIRST_CLAIMABLE_ROW <= r.next_stream
                                  < new_count):
            raise Refused(
                f"row {r.index} would link to {r.next_stream}, outside "
                f"[{FIRST_CLAIMABLE_ROW}, {new_count}). The loader asserts "
                f"`curr->alloc.nextStream < count` at VA 0x93f0b8 and walks the "
                f"chain with a Floyd tortoise/hare.")

    id_offset, spare = id_table_slack(ar)
    if spare < 8:
        raise Refused(
            f"the file-id table has no room for another pair: {spare} bytes "
            f"spare in its reservation.\n"
            f"  Growing it means relocating {ar.row(FILE_ID_TABLE_ROW).size} "
            f"bytes, and the largest usable run in this archive is {largest} B. "
            f"That relocation is not possible today.")

    return AllocPlan(rows, file_id, id_offset, spare - 8, grow, slack,
                     ar.entry_count, ar.mft_size, block, usable_before, largest)


# ---------------------------------------------------------------- the write

def alloc(path, streams, file_id, journal_path, confirm=False, plan=None):
    """Do it. Returns the AllocPlan that was carried out.

    THE ORDER IS THE DESIGN, and the principle it serves is one sentence: NO
    PREFIX OF THIS MAY LEAVE A USED|FIRST_STREAM ROW THAT THE FILE-ID TABLE DOES
    NOT NAME. That is the state the client actively destroys -- the open-time
    reconcile frees the extent and memsets the row -- so the id record goes live
    BEFORE any row does, never after.

      1. payloads, into their free runs. Nothing points at them yet.
      2. APPENDED rows' 24 bytes each, fully formed. Invisible: they sit past
         the count the descriptor declares, so no reader walks them.
      3. the (file_id, row) pair, at `offset + size` of the table. Invisible for
         the same reason -- past the size row 2 declares.
      4. row 2's size and crc. THE ID IS NOW LIVE, and for a moment it names a
         row that is not: datcheck rule 8 goes red, "1 dangling record". That is
         the milder failure and it is chosen deliberately -- the reconcile DROPS
         a dangling record, where it DELETES an orphan row and frees its extent.
         Losing a name beats losing the bytes.
      5. the descriptor's entry count, then the header's MFT size, then row 3's
         size field. THE WINDOW: between the first two `entry_count * 24 !=
         mft_size` and `Archive()` refuses. Two fsynced 4-byte writes, and
         `datwrite.mft_offset_of` exists so `--revert` works inside it. The
         appended rows are live at the end of this, and already named.
      6. REUSED rows' 24 bytes. LAST, because a reused row's index is ALREADY
         below the count: writing it makes it live that instant, with no
         invisible phase to hide in. It also closes the rule-8 window from 4.
      7. the MFT self-crc, because it covers everything above.

    STEP 6 IS WHY THIS WAS REWRITTEN. The first version wrote every row at step 2
    and called steps 1-3 "invisible", which is true only of APPENDED rows. A
    reused spare is inside the declared table, so that version published a
    USED|FIRST_STREAM head with no id record -- exactly the shape the reconcile
    deletes -- and, when the head was reused and its partner appended, published
    a head whose `nextStream` pointed past the declared count while the loader
    asserts `nextStream < count`. Both were fsynced to disk. Section 11 of
    test_datalloc.py replays every prefix and asserts neither can occur.

    `plan=` USED TO BYPASS EVERY GATE IN `plan_alloc`, and that is why the
    fidelity check below is run HERE as well rather than only there. Demonstrated
    2026-08-19: a plan computed over stored streams, `plan.rows[1].extra_bytes`
    set to 8 by the caller, `alloc(confirm=True, plan=plan)` -- and extraBytes 8
    went onto disk over plainly stored bytes with `Archive.read()` not even
    raising. A gate that only runs when the caller declines to pre-compute is
    advisory, and this verb has no advisory gates. So: the declarations are
    checked over the STREAMS on every path, and a handed-in plan that disagrees
    with the streams about `extra_bytes` is refused outright rather than
    reconciled -- reconciling would mean picking a winner, and the plan is a
    placement, not a second opinion about the payload.
    """
    datwrite.guard(path)
    datwrite.guard_source(path)
    given = plan is not None
    if given:
        if len(plan.rows) != len(streams):
            raise Refused(
                f"the plan handed in describes {len(plan.rows)} row(s) and "
                f"{len(streams)} stream(s) were given. A plan is carried out "
                f"row-by-row against the streams it was computed from; a "
                f"mismatched pair would write one stream's bytes under another "
                f"row's declaration.")
        for i, (s, r) in enumerate(zip(streams, plan.rows)):
            if r.extra_bytes != s.extra_bytes:
                raise Refused(
                    f"the plan handed in gives row {r.index} extraBytes "
                    f"{r.extra_bytes} while stream {i} declares "
                    f"{s.extra_bytes}.\n"
                    f"  The fidelity gate runs over the STREAMS, so a plan that "
                    f"disagrees with them carries a declaration nothing checked "
                    f"onto disk -- MEASURED 2026-08-19, extraBytes 8 written over "
                    f"plainly stored bytes exactly this way, green everywhere. "
                    f"Recompute the plan from these streams.")
    with Archive(path) as probe:
        plan = plan or plan_alloc(probe, streams, file_id)
    # THE FIDELITY GATE, RUN HERE AND UNCONDITIONALLY. When `plan` was computed
    # just now this repeats what `plan_alloc` already did, which costs one decode
    # and is the price of the gate being BINDING on the write path rather than a
    # property of one route to it. Before --confirm, like `datmove.move`, so a
    # dry run reports a bad declaration instead of passing and then failing on the
    # real invocation. After `plan_alloc`, so that a stream which is malformed in
    # both ways is named by this module's own sharper refusal first.
    check_declarations(streams, announce=given)
    if not confirm:
        raise Refused("refusing to write without --confirm")

    w = datwrite.Writer(path, journal_path)
    try:
        # 1. payloads
        for s, r in zip(streams, plan.rows):
            if not r.size:
                continue
            image = s.data + b"\x00" * (r.reservation - r.size)
            w.put(r.offset, image,
                  f"row {r.index} payload ({r.reservation} B reservation)")

        def write_row(r):
            row_bytes = struct.pack("<QIHHII", r.offset, r.size, r.extra_bytes,
                                    r.flags, r.next_stream, r.crc)
            w.put(mft_row_offset(w.ar.mft_offset, r.index), row_bytes,
                  f"MFT row {r.index}: offset 0x{r.offset:X}, size {r.size}, "
                  f"flags 0x{r.flags:04X}, nextStream {r.next_stream}")

        # 2. APPENDED rows only -- past the declared count, and so unread
        for r in plan.rows:
            if not r.reused:
                write_row(r)

        # 3. the file-id record, past the declared table size and so unread
        w.put(plan.id_offset,
              struct.pack("<II", plan.file_id, plan.head.index),
              f"file-id table: (0x{plan.file_id:X}, {plan.head.index})")

        # 4. the table's size and crc: THE ID GOES LIVE HERE, before any row.
        tbl = w.ar.row(FILE_ID_TABLE_ROW)
        w.put(mft_row_offset(w.ar.mft_offset, FILE_ID_TABLE_ROW)
              + ENTRY_SIZE_OFF, struct.pack("<I", tbl.size + 8),
              f"MFT row {FILE_ID_TABLE_ROW} size {tbl.size} -> {tbl.size + 8}")
        w.fh.seek(tbl.offset)
        grown = w.fh.read(tbl.size + 8)
        w.set_entry_crc(FILE_ID_TABLE_ROW, binascii.crc32(grown))

        # 5. THE WINDOW -- the writes that make the appended rows exist
        if plan.mft_grow_rows:
            w.put(w.ar.mft_offset + MFT_HDR_COUNT,
                  struct.pack("<I", plan.new_entry_count),
                  f"MFT descriptor entry count {plan.old_entry_count} -> "
                  f"{plan.new_entry_count}")
            w.put(HDR_MFT_SIZE, struct.pack("<I", plan.new_mft_size),
                  f"file header MFT size {plan.old_mft_size} -> "
                  f"{plan.new_mft_size}")
            # row 3 restates the table's length. datcheck rule 9(d).
            w.put(mft_row_offset(w.ar.mft_offset, MFT_SELF_ROW)
                  + ENTRY_SIZE_OFF, struct.pack("<I", plan.new_mft_size),
                  f"MFT row {MFT_SELF_ROW} size -> {plan.new_mft_size}")
            w.resync("the table grew")

        # 6. REUSED rows LAST -- they are live the instant they are written
        for r in plan.rows:
            if r.reused:
                write_row(r)

        # 7. and the table describes itself again
        w.fix_mft_self_crc()
    finally:
        w.close()
    return plan


# ------------------------------------------------------------------- the CLI

def _read(path):
    with open(path, "rb") as fh:
        return fh.read()


def _split_stream_spec(spec):
    """`FILE[:FLAGS[:EXTRA]]` -> `(path, flags or None, extra or None)`.

    Split from the RIGHT, and only when the tail parses as an integer AND
    something is left in front of it. An absolute Windows path carries a colon
    of its own: a bare `rpartition(":")` split `C:\\x\\y.bin` into its drive
    letter and the rest, then died on `int()` with an unhandled ValueError, so
    every absolute path was unusable. Two rounds of the same conditional split
    take EXTRA and then FLAGS, and `C:\\x\\y.bin` still parses as a bare path
    because `\\x\\y.bin` is not an integer.

    The count of trailing fields is what decides their meaning, so the two older
    spellings keep their old meaning exactly: no field is the defaults, ONE field
    is FLAGS (never EXTRA), two are FLAGS then EXTRA.

    WHAT IS LEFT OVER MUST BE A PATH, and that is checked rather than handed to
    `open()`. Until 2026-08-20 a malformed spec fell through this function whole
    and died inside `_read` -- `FILE:x:8` and `FILE:1:8:0` on FileNotFoundError,
    `FILE:` on `OSError [Errno 22]` -- a traceback naming a temp file, in a tool
    whose every other bad input is a sentence. Nothing allocated, which is what
    matters, but "the machine is unhappy" is not a diagnosis. The one colon a path
    may still carry is a DRIVE LETTER's: index 1, one letter in front of it, a
    separator behind it. `C:\\x\\y.bin` is the shape this whole function exists
    for and it survives; `a:b` does not, and an NTFS alternate-data-stream path is
    not a thing this CLI has ever been asked to take.
    """
    original = spec
    fields = []
    while len(fields) < 2:
        head, sep, tail = spec.rpartition(":")
        if not (sep and head):
            break
        try:
            fields.append(int(tail, 0))
        except ValueError:
            break
        spec = head
    drive = (len(spec) > 2 and spec[0].isalpha() and spec[1] == ":"
             and spec[2] in "\\/")
    if ":" in (spec[2:] if drive else spec):
        raise Refused(
            f"--stream {original} is not a spec this grammar can read: the path "
            f"it leaves in front of the trailing field(s) is {spec!r}, and that "
            f"still carries a colon.\n"
            f"  The grammar is FILE[:FLAGS[:EXTRA]] and both trailing fields are "
            f"INTEGERS -- one field is FLAGS and never EXTRA, two are FLAGS then "
            f"EXTRA. A non-numeric field (`FILE:x:8`), a third one "
            f"(`FILE:1:8:0`) and an empty one (`FILE:`) all land here rather than "
            f"being opened as a filename.\n"
            f"  The only colon a PATH may carry is a drive letter's: one letter, "
            f"a colon, then a separator, as in C:\\maps\\part.gwenc.")
    if len(fields) == 2:
        return spec, fields[1], fields[0]
    if len(fields) == 1:
        return spec, fields[0], None
    return spec, None, None


def _streams_from_args(args):
    """`--map DATA` is the shape this exists for; `--stream` is the general one.

    `--map` writes STORED rows and has no EXTRA of its own. A map's Stripped
    partner is compression 8 in retail, so that is a gap rather than a rule --
    but it is one this CLI cannot close by adding a flag, because the caller
    would still have to hand in bytes `gwenc` produced. `--stream` is the form
    that takes them.
    """
    if args.map:
        if not args.data:
            raise Refused("--map needs --data, the Stripped partner's bytes")
        # `--map` writes two STORED rows and has no EXTRA of its own, so an
        # --expect here has nothing to be checked against and is refused rather
        # than ignored -- see `_check_expect_arity`.
        _check_expect_arity([0, 0], args)
        head = _read(args.head) if args.head else b""
        return _attach_expect([Stream(head, MAP_HEAD_FLAGS_U16),
                               Stream(_read(args.data),
                                      MAP_PARTNER_FLAGS_U16)], args)
    if not args.stream:
        raise Refused("nothing to allocate: pass --map --data FILE, or "
                      "--stream FILE at least once")
    specs = []
    for i, spec in enumerate(args.stream):
        path, flags, extra = _split_stream_spec(spec)
        if flags is None:
            flags = MAP_HEAD_FLAGS_U16 if i == 0 else MAP_PARTNER_FLAGS_U16
        if extra is None:
            extra = 0
        if extra not in (0, 8):
            # `plan_alloc` holds this same rule and is the binding gate; this is
            # a better message in front of it, refused before a file is read and
            # before an archive is opened, and it names the field rather than a
            # stream index the caller has to count out.
            raise Refused(
                f"--stream {spec} declares extraBytes {extra}; only 0 and 8 are "
                f"accepted.\n"
                f"  8 is the compressed framing and it is not a label: "
                f"`plan_alloc` refuses it unless the payload DECODES as a "
                f"compression-8 stream, so declaring it commits the row to being "
                f"one. 0 is stored, which is what this module writes unless you "
                f"compressed the bytes yourself with `gwenc`.\n"
                f"  Anything else is a declaration nothing has tested. MEASURED "
                f"on vault/run-live/2026-08-13/Gw.dat, +0x0C takes exactly two "
                f"values across 177,740 rows -- {{0: 38682, 8: 139058}} -- and no "
                f"third value has ever been seen written or read.")
        specs.append((path, flags, extra))
    # BEFORE A FILE IS OPENED, like the EXTRA rule above it. `--expect` is the
    # difference between a compressed row that was checked and one that was not,
    # so getting it wrong should cost a sentence rather than a traceback out of
    # `_read`.
    _check_expect_arity([e for _p, _f, e in specs], args)
    return _attach_expect([Stream(_read(p), f, e) for p, f, e in specs], args)


def _check_expect_arity(extras, args):
    """`--expect` against the EXTRA fields, before anything is read. -> None.

    Three rules and each is a refusal:

      * EXTRA 8 anywhere REQUIRES --expect. `plan_alloc` holds the binding form
        of this (`check_declarations`); this is the better message in front of it.
      * --expect with no EXTRA 8 is refused rather than ignored. For a STORED row
        the bytes ARE the payload, so a stored --expect is a tautology a caller
        can only have typed by mistake -- and the mistake it most plausibly IS
        is a forgotten `:8`, which would otherwise allocate a compression-8
        stream as opaque bytes with the declaration silently dropped.
      * At most ONE EXTRA 8 per invocation, because there is one --expect and no
        way to say which stream it belongs to. A chain with two compressed rows
        is a real shape and the API takes it -- `Stream(..., extra_bytes=8,
        expect=...)` per row -- so this is a limit on the flag, not on the verb.
    """
    comp = [i for i, e in enumerate(extras) if e == 8]
    if len(comp) > 1:
        raise Refused(
            f"streams {', '.join(str(i) for i in comp)} all declare EXTRA 8, and "
            f"--expect names ONE payload.\n"
            f"  There is no spelling on this command line that says which "
            f"compressed stream a given --expect belongs to, and guessing is the "
            f"one thing a fidelity check may not do. Allocate a chain with more "
            f"than one compressed row from the API, where every Stream carries "
            f"its own: `Stream(data, flags, extra_bytes=8, expect=payload)`.")
    if comp and not args.expect:
        raise Refused(
            f"--stream {args.stream[comp[0]]} declares EXTRA 8 and there is no "
            f"--expect FILE.\n"
            f"  8 commits the row to being a compression-8 stream, and the entry "
            f"crc is over the STORED bytes -- so after the write nothing can tell "
            f"a stream that decodes to the right payload from one that decodes to "
            f"the wrong bytes, or to one byte fewer. Both crc rules, all ten "
            f"open-time rules and the overlap sweep pass either way.\n"
            f"  Pass --expect FILE, the payload a reader must get back. "
            f"`datmove --compression 8` has required the same since 2026-08-18.")
    if args.expect and not comp:
        raise Refused(
            "--expect FILE was given and no --stream declares EXTRA 8.\n"
            "  A stored row's bytes ARE its payload, so there is nothing here for "
            "an expected payload to be checked against. The likeliest reading is "
            "a missing `:8` on the stream that holds gwenc output -- which would "
            "have allocated it as opaque bytes -- so this refuses rather than "
            "ignoring the flag.")


def _attach_expect(streams, args):
    """Hang `--expect` on the compressed stream and `--stored-lookalike-ok` on all.

    `_check_expect_arity` has already established that there is at most one
    compressed stream and that --expect is present exactly when there is one, so
    the placement here is not a guess.
    """
    if args.expect:
        want = _read(args.expect)
        for s in streams:
            if s.extra_bytes == 8:
                s.expect = want
    if args.stored_lookalike_ok:
        for s in streams:
            s.stored_lookalike_ok = True
    return streams


def _journal_path(args):
    """`--alloc` REQUIRES `--journal`, and will not write over an existing one.

    `datwrite` and `datmove` both default the journal to a name derived from the
    target -- `DAT.journal.json` and `DAT.row-N.journal.json` -- and for a verb
    that can run twice with the same arguments that default is worse than no
    journal at all. Sequence, all of it reachable: run one allocates and writes
    the journal; run two allocates a SECOND file and truncates the same file at
    its first write; the tool then prints the path it just destroyed as the way
    back. Reverting it restores the archive to its post-run-one state, prints
    "N range(s) restored", exits 0, and passes `--verify` -- because post-run-one
    was internally consistent. Run one's row, payload and file-id record persist
    while the tool reports a clean revert.

    So this refuses, which is what the repo's other two journalling writers
    already do -- `iconset.py:213` and `textwrite.py:283` both make `--journal`
    mandatory rather than clever. `datwrite`'s silent default is the outlier
    among its own callers, and an allocation is the worst verb to inherit it.
    """
    if not args.journal:
        raise Refused(
            "--alloc needs --journal PATH.\n"
            "  An allocation is not revertible without one, and unlike a "
            "replace it can be run twice with identical arguments -- so a "
            "default name derived from --dat would let the second run truncate "
            "the first run's undo record and then print that file as the way "
            "back. Name the journal per run.")
    if os.path.exists(args.journal):
        raise Refused(
            f"{args.journal} already exists, and this will not write over it.\n"
            f"  A journal is the only way back from an allocation. Overwriting "
            f"one leaves the edits it recorded applied forever, and a later "
            f"--revert of the new file would report success having restored "
            f"none of them.")
    return args.journal


def build_parser():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--file-id", type=lambda s: int(s, 0),
                    help="the id the client will address this file by; required "
                         "to allocate, because an unregistered row is deleted")
    ap.add_argument("--next-id", action="store_true",
                    help="print the lowest file id nothing binds, and stop")
    ap.add_argument("--map", action="store_true",
                    help="allocate a map: a head (259) chained to a partner (1)")
    ap.add_argument("--data", help="with --map, the Stripped partner's bytes")
    ap.add_argument("--head", help="with --map, the Bloated head's bytes; "
                                   "omitted means a zero-length armed head")
    ap.add_argument("--stream", action="append", metavar="FILE[:FLAGS[:EXTRA]]",
                    help="general form: one per row of the chain, in order. "
                         "EXTRA is alloc.extraBytes -- 0 (stored, the default) "
                         "or 8 (compression 8, and the bytes must DECODE as "
                         "one; this module compresses nothing, so pass "
                         "gwenc output). EXTRA 8 requires --expect.")
    ap.add_argument("--expect", metavar="FILE",
                    help="the payload a reader must get back. MANDATORY with a "
                         "--stream declaring EXTRA 8: the entry crc is over the "
                         "STORED bytes, so nothing can check a compressed row "
                         "after the allocation. One compressed stream per "
                         "invocation; use the API for a chain with more.")
    ap.add_argument("--stored-lookalike-ok", action="store_true",
                    help="allocate bytes that DECODE as compression 8 with "
                         "EXTRA 0 anyway. FINDINGS C-6 override, not a switch: "
                         "4 of 38,621 real stored rows need it and 0 of 1,500 "
                         "decompressed payloads do. Prints a line when taken.")
    ap.add_argument("--plan", action="store_true", help="compute and print only")
    ap.add_argument("--alloc", action="store_true", help="write it")
    ap.add_argument("--confirm", action="store_true")
    ap.add_argument("--journal", default=None)
    return ap


def _main(argv=None):
    args = build_parser().parse_args(argv)

    if args.next_id:
        with Archive(args.dat) as ar:
            print(f"0x{next_free_file_id(ar):X}")
        return 0
    if not (args.plan or args.alloc):
        print("nothing to do: pass --plan or --alloc", file=sys.stderr)
        return 2

    try:
        streams = _streams_from_args(args)
        if args.alloc:
            journal = _journal_path(args)
            plan = alloc(args.dat, streams, args.file_id, journal,
                         confirm=args.confirm)
            plan.show()
            print(f"\njournal: {journal}")
            print(f"revert with: python toolkit/mapdata/datwrite.py "
                  f"--dat {args.dat} --revert {journal}")
            print("\nverifying:")
            bad = datwrite.verify(args.dat)
            bad += len(datmove_overlaps(args.dat))
            # And the ten OPEN-TIME rules, which is the set that matters
            # here. The two checksums above cannot see the three things an
            # allocation is uniquely able to break: an orphan row (rule 7),
            # a dangling record (rule 8), and the three length restatements
            # (rule 9). Running two of ten and calling it verified is how
            # the interesting half goes unchecked.
            bad += preflight_after(args.dat)
            return 1 if bad else 0
        with Archive(args.dat) as ar:
            plan_alloc(ar, streams, args.file_id).show()
        return 0
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


def preflight_after(path):
    """`datcheck`'s ten open-time rules, run automatically after a write.

    Rules 7, 8 and 9 are the ones an allocation can break and the two checksum
    rules cannot see: a USED|FIRST row no record names, a record naming a row
    that is not USED, and the three length restatements that must move together.
    Returns the number of failed items.
    """
    import datcheck
    got, _meta = datcheck.preflight(path)
    bad = [c for c in got if not c.ok]
    for c in bad:
        print("  [FAIL] %s  %s" % (c.name, c.detail))
    print("  [%s] datcheck preflight: %d of %d clear"
          % ("PASS" if not bad else "FAIL", len(got) - len(bad), len(got)))
    return len(bad)


def datmove_overlaps(path):
    """The reservation-overlap sweep, run automatically after a write.

    `datmove` runs it after every move and no other writer runs it at all --
    `datwrite.verify` checks the two checksums and neither covers two rows
    sharing blocks. An allocation places payloads, so it is exactly the verb that
    can create one.
    """
    import datmove
    with Archive(path) as ar:
        bad = datmove.overlaps(ar)
    for a, b, at in bad:
        print(f"  [FAIL] rows {a} and {b} share storage from 0x{at:X}")
    if not bad:
        print(f"  [PASS] no overlapping reservations")
    return bad


if __name__ == "__main__":
    sys.exit(_main())
