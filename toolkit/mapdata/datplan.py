"""Plan a write into Gw.dat. Compute every byte that would change; change none.

THIS MODULE NEVER OPENS THE ARCHIVE FOR WRITING. It exists to answer a question
the skills study left open -- "no tool in our entire evidence base can write to
Gw.dat" -- by separating two things that were tangled together in that sentence:
whether the edit is *computable*, and whether the client *accepts* it. The first
is a tooling question and this module settles it. The second is an empirical
question about a running client and no amount of planning answers it.

So a plan is not permission. It is the exact diff you would apply if you decided
to, printed so it can be argued with before anything is at risk.

WHAT A WRITER HAS TO GET RIGHT, all MEASURED (see test_datcrc.py, which asserts
the first three against the corpus rather than trusting this docstring):

  1. Offsets are 512-byte aligned. Every one of 177,329 entries, GCD exactly 512.
  2. Space is reserved in whole blocks -- size rounded up. 176,033 of 177,329
     entries sit exactly that far from their neighbour, so the allocator packs
     to block granularity and the leftover inside the last block is dead space
     that belongs to the entry.
  3. The crc at entry+0x14 is CRC-32/ISO-HDLC over the STORED bytes, the
     compressed form on disk, not the payload. Get this wrong and the archive is
     self-inconsistent even if the client never looks.
  4. A file is only addressable by id if the file-id table at MFT row 2 maps it.
     That table is a stored array of (file_id u32, row u32) pairs.

  5. MFT row 3 describes the table itself, and its crc covers the table with its
     own 24-byte row skipped. An earlier pass of this file claimed that crc was
     "stale by construction" and read the client's tolerance of it as evidence
     that crcs are not checked. That was wrong twice over: the rule exists, and
     no such tolerance was ever demonstrated. See datwrite.py:mft_self_crc.

  6. "Free" is not free. The gap-between-reservations measure counts LIVE
     CONTAINER GENERATIONS as available space, and this file used to place new
     files directly on top of them -- see the block comment on free_runs().

AND THE ONE THAT IS NOT SETTLED: whether the client validates any of it on read,
and whether a modification survives a play session. Both are open, and nothing
here leans either way -- the one piece of evidence this docstring used to cite
for tolerance was a misreading. Read studies/datwrite/FINDINGS.md before acting
on a plan.

    python toolkit/mapdata/datplan.py --insert 4096
    python toolkit/mapdata/datplan.py --overwrite 22371
    python toolkit/mapdata/datplan.py --free
"""

import argparse
import binascii
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import Archive, DEFAULT_DAT, ENTRY_SIZE, MFT_MAGIC  # noqa: E402

# Offsets into the 32-byte file header and the 24-byte MFT header, for the
# fields a growing table forces us to touch.
HDR_MFT_SIZE = 0x18
MFT_HDR_COUNT = 0x0C

# The MFT's own row. Growing the table means restating its size here too, and
# its crc covers the table with this very row skipped -- see datwrite.py.
MFT_SELF_ROW = 3

# Rows 1, 2 and 3 are the file header, the file-id table and the MFT itself.
# Rows 4..15 are erased in BOTH archives on this machine and stayed that way --
# and when the client needed a free slot it took row 35301, the only other erased
# row in the file, reaching past twelve nearer ones. Twelve zeroed rows sitting
# immediately after the three container rows, which a working allocator declines
# to use, are reserved. Claiming one would look fine right up until it did not.
FIRST_CLAIMABLE_ROW = 16

# How many (file_id, row) pairs must all name a live MFT row before we call a
# block the head of a file-id table. MEASURED on vault/dat_study/Gw.dat: at every
# sample size from 4 to 128 pairs this rule selects exactly the two known table
# generations out of 214 runs and nothing else, so the value is not delicately
# tuned. 32 pairs is 256 bytes, which also covers the 24-byte MFT header, so one
# read serves both tests.
CONTAINER_PROBE_PAIRS = 32
CONTAINER_PROBE_BYTES = CONTAINER_PROBE_PAIRS * 8


def blocks_for(size, block):
    return -(-size // block)


class Edit:
    """One contiguous byte range that would change, and why."""

    __slots__ = ("offset", "length", "what", "detail")

    def __init__(self, offset, length, what, detail=""):
        self.offset = offset
        self.length = length
        self.what = what
        self.detail = detail

    def __repr__(self):
        return f"<Edit 0x{self.offset:X} +{self.length} {self.what}>"


class Plan:
    def __init__(self, summary):
        self.summary = summary
        self.edits = []
        self.notes = []
        self.blockers = []
        self.excluded = []      # [Exclusion], the runs this plan refused to use

    def add(self, offset, length, what, detail=""):
        self.edits.append(Edit(offset, length, what, detail))

    @property
    def bytes_touched(self):
        return sum(e.length for e in self.edits)

    def show_excluded(self, block):
        """Name every run the container rule withheld. Never silent.

        A planner that quietly dropped 88.5% of the space it was asked about
        would be reporting a different archive than the one on disk.
        """
        if not self.excluded:
            return
        held = sum(x.blocks for x in self.excluded) * block
        print(f"\n  withheld {len(self.excluded)} run(s), {held} bytes, as live "
              f"container generations:")
        for x in sorted(self.excluded, key=lambda r: r.start_block):
            print(f"    0x{x.start_block * block:012X}  {x.blocks * block:>11} "
                  f"bytes  {x.why()}")

    def show(self, block=512):
        print(self.summary)
        if self.blockers:
            print("\n  BLOCKED:")
            for b in self.blockers:
                print(f"    - {b}")
            self.show_excluded(block)
            return
        print(f"\n  {len(self.edits)} edit(s), {self.bytes_touched} bytes changed:")
        for e in sorted(self.edits, key=lambda x: x.offset):
            print(f"    0x{e.offset:012X}  +{e.length:<9} {e.what}")
            if e.detail:
                print(f"                              {e.detail}")
        self.show_excluded(block)
        if self.notes:
            print("\n  notes:")
            for n in self.notes:
                print(f"    - {n}")


def free_runs(ar):
    """Runs of unallocated whole blocks, IN ADDRESS ORDER.

    Counted in blocks, not bytes. The byte-level gap between two entries is
    mostly dead space inside the earlier entry's own reservation -- 52.7 MB of
    the archive is exactly that -- and none of it is usable for a new file.

    "Unallocated" here means exactly one thing: no MFT row points at it. That is
    a weaker statement than "free", and the gap between the two is where this
    module's worst bug lived. See classify_runs().

    ADDRESS ORDER IS DELIBERATE, and this function used to sort largest-first.
    That ordering was not a presentation choice -- plan_insert() took the first
    qualifying run, so the sort WAS the allocation policy, and no line of code
    said so. Callers that want an order now ask for one where the decision is
    visible: best_fit() to place a file, sorted(..., key=size) to print a report.
    """
    block = ar.block_size
    filesize = os.path.getsize(ar.path)
    nblocks = (filesize + block - 1) // block
    bitmap = bytearray(nblocks)
    bitmap[0] = 1
    for e in ar.entries:
        if not e.size:
            continue
        for b in range(e.offset // block, (e.offset + e.size - 1) // block + 1):
            if b < nblocks:
                bitmap[b] = 1
    for b in range(ar.mft_offset // block,
                   (ar.mft_offset + ar.mft_size - 1) // block + 1):
        if b < nblocks:
            bitmap[b] = 1
    runs = []
    run = 0
    for b in range(nblocks):
        if bitmap[b]:
            if run:
                runs.append((b - run, run))
            run = 0
        else:
            run += 1
    if run:
        runs.append((nblocks - run, run))
    return runs


class Exclusion:
    """One free run a writer may not have, and the evidence for saying so."""

    __slots__ = ("start_block", "blocks", "marks")

    def __init__(self, start_block, blocks, marks):
        self.start_block = start_block
        self.blocks = blocks
        self.marks = marks          # [(block_within_run, kind, detail)]

    def why(self):
        kinds = sorted({k for _, k, _ in self.marks})
        first = self.marks[0]
        where = "at its head" if first[0] == 0 else f"{first[0]} blocks in"
        return (f"{' and '.join(kinds)} ({len(self.marks)} marked block(s), "
                f"first {where}: {first[2]})")

    def __repr__(self):
        return f"<Exclusion 0x{self.start_block:X} +{self.blocks}blk>"


def container_signature(buf, entry_count):
    """Name the container generation starting at this block boundary, or None.

    Two signatures, both cheap and both refutable against the artifact:

      * `Mft\\x1a`, the master file table's own magic. Self-describing: the entry
        count at +0x0C says how far the table reaches.
      * A run of (file_id u32, row u32) pairs whose every row names a live MFT
        row. The file-id table is stored, not compressed, so its structure is
        visible on disk with nothing decoded.

    THE ID-TABLE TEST IS A HEURISTIC and is applied only to a sample at the head
    of a block, never to a whole table -- the live table itself carries three
    (0, 0) pairs deeper in, which the rule would reject. What earns it a place is
    that it is measurably not trigger-happy: over the 214 free runs of
    vault/dat_study/Gw.dat it fires on the two known table generations and on
    nothing else, at every sample size from 4 pairs to 128.
    """
    if len(buf) < CONTAINER_PROBE_BYTES:
        return None
    if buf[:4] == MFT_MAGIC:
        count = struct.unpack_from("<I", buf, MFT_HDR_COUNT)[0]
        return ("master file table",
                f"declares {count} entries = {count * ENTRY_SIZE} bytes")
    for i in range(CONTAINER_PROBE_PAIRS):
        _file_id, row = struct.unpack_from("<II", buf, i * 8)
        if not 1 <= row <= entry_count:
            return None
    return ("file-id table",
            f"{CONTAINER_PROBE_PAIRS} consecutive (file_id, row) pairs, every "
            f"row in 1..{entry_count}")


def scan_run(ar, start_block, nblocks):
    """Every block boundary inside one run that carries a container signature.

    EVERY boundary, not just the first. A head-only test is the obvious cheap
    version and it is not enough: MEASURED on vault/dat_study/Gw.dat, the run at
    0xF6772800 (374,784 bytes) begins with 428 blocks of ordinary stale data and
    only then a file-id table generation, so a head test calls it clean and a
    writer walks straight into the table.
    """
    block = ar.block_size
    per_chunk = max(1, (1 << 20) // block)
    marks = []
    pos = 0
    while pos < nblocks:
        n = min(per_chunk, nblocks - pos)
        ar.fh.seek((start_block + pos) * block)
        data = ar.fh.read(n * block)
        for k in range(len(data) // block):
            head = data[k * block:k * block + CONTAINER_PROBE_BYTES]
            sig = container_signature(head, ar.entry_count)
            if sig:
                marks.append((pos + k, sig[0], sig[1]))
        pos += n
    return marks


def classify_runs(ar, runs=None):
    """Split free runs into the ones a writer may use and the ones it may not.

    Returns (usable, excluded): a list of (start_block, blocks) in address order,
    and a list of Exclusion.

    WHY THIS EXISTS. "Unallocated" is measured as the gap between MFT
    reservations, and the client's containers do not live in that measure. It
    rotates its MFT and its file-id table between a small set of recurring slots,
    writing the new generation into one and leaving the previous generation
    intact in the other -- and the previous generation is pointed at by no MFT
    row, so it reads as free. It is not free: it is the copy the client is about
    to rotate back onto, and on this machine one of those slots is where the LIVE
    MFT sits in a different copy of the archive (0xF8FFF000 in
    vault/run/2026-07-29_221c13772c7a-probe/Gw.dat).

    MEASURED on vault/dat_study/Gw.dat. Six of 214 runs carry a container
    signature and they hold 29,160,448 of the 32,528,384 bytes the gap measure
    calls free -- 89.6%. The largest, 14,718,976 bytes at 0xF8FFF000, is three
    whole MFT generations laid end to end followed by file-id table generations,
    and the tiling is exact rather than approximate: each header declares 177,342
    entries, which is 8,313 blocks, and the next header sits at exactly +8313,
    the third at +16626, and the id-table stretch begins at +24939 = 3 x 8313.
    Three predictions that could each have missed and did not.

    What is genuinely unclaimed is 3,367,936 bytes in 208 runs, largest 953,856.
    That is the number that changes what a writer can plan: the median reservation
    of the 349 map-flagged rows is 961,536, just above it, and 176 of those 349
    are larger than the largest run left. For half the maps in the archive the
    answer to "where does this go" is now nowhere, which is a true answer and was
    not available while the largest hole looked like 14 MB.

    A RUN IS WITHHELD WHOLE, never carved around. The tail of 0xF8FFF000 past the
    generations it currently holds is precisely the space the next, larger
    generation grows into, and "the container is only in the first 27,611 blocks"
    is an argument for writing exactly where the client is about to write.
    """
    if runs is None:
        runs = free_runs(ar)
    usable, excluded = [], []
    for start, n in runs:
        marks = scan_run(ar, start, n)
        if marks:
            excluded.append(Exclusion(start, n, marks))
        else:
            usable.append((start, n))
    return usable, excluded


def best_fit(runs, need):
    """The smallest run of at least `need` blocks. Ties go to the lowest address.

    SMALLEST, not largest, and the difference is the whole point. Taking the
    first run of a largest-first list puts every new file at the head of the
    biggest hole in the archive, which is exactly where the client parks its
    container generations -- so the old policy did not merely fragment badly, it
    aimed at the one region that must not be touched.

    Best fit is also reported to be what the client's own allocator does -- the
    reservation-safety pass read it at 0x00478C50, with a comparator at 0x00479280
    seeded 0xFFFFFFFF that keeps only an exact fit or the smallest strictly-larger
    run. UNVERIFIED HERE: nothing in this module re-derived that, and no test
    covers it. It is the reason best fit was chosen over worst fit rather than a
    property anything depends on -- the container rule in classify_runs() is what
    actually makes a plan safe, and it holds whichever fit policy is in force.

    The address tie-break carries no claim at all -- it is here so the same
    archive and the same request always produce the same plan.
    """
    fits = [r for r in runs if r[1] >= need]
    if not fits:
        return None
    return min(fits, key=lambda r: (r[1], r[0]))


def free_rows(ar, include_reserved=False):
    """MFT rows with size 0 -- erased slots a writer can claim without growing.

    Excludes the reserved low rows by default; see FIRST_CLAIMABLE_ROW.
    """
    return [e.index for e in ar.entries
            if e.size == 0
            and (include_reserved or e.index >= FIRST_CLAIMABLE_ROW)]


def plan_insert(ar, payload_size, flags=3, compression=0, file_id=None,
                classified=None):
    """Add a brand-new file. The expensive case, and it is not very expensive.

    `classified` is the (usable, excluded) pair from classify_runs(), so a caller
    making several plans pays for the scan once.
    """
    block = ar.block_size
    need = blocks_for(payload_size, block)
    plan = Plan(f"INSERT a new {payload_size}-byte file "
                f"(compression {compression}, flags {flags})")

    usable, excluded = classified if classified else classify_runs(ar)
    plan.excluded = excluded
    fit = best_fit(usable, need)
    if fit is None:
        if not usable:
            plan.blockers.append(
                f"no usable free space at all for {need} blocks "
                f"({need * block} bytes)")
        else:
            plan.blockers.append(
                f"no usable free run of {need} blocks ({need * block} bytes); "
                f"the largest that is not a container generation is "
                f"{max(n for _, n in usable)} blocks")
        withheld = [x for x in excluded if x.blocks >= need]
        if withheld:
            plan.blockers.append(
                f"{len(withheld)} withheld run(s) WOULD have fit -- largest "
                f"{max(x.blocks for x in withheld) * block} bytes. Placing the "
                f"file there is what this planner used to do; see classify_runs")
        return plan
    at = fit[0] * block
    plan.add(at, need * block, "payload",
             f"{payload_size} bytes + {need * block - payload_size} bytes of "
             f"block padding; best fit of {sum(1 for r in usable if r[1] >= need)} "
             f"usable run(s) -- run has {fit[1]} blocks, using {need}")

    # The MFT row. Reuse an erased slot if one exists, else append.
    erased = free_rows(ar)
    if erased:
        row = erased[0]
        row_off = ar.mft_offset + row * ENTRY_SIZE
        plan.add(row_off, ENTRY_SIZE, f"MFT row {row} (reusing an erased slot)",
                 f"{len(erased)} erased rows available; no table growth needed")
    else:
        row = ar.entry_count
        row_off = ar.mft_offset + row * ENTRY_SIZE
        plan.add(row_off, ENTRY_SIZE, f"MFT row {row} (appended)")
        plan.add(ar.mft_offset + MFT_HDR_COUNT, 4, "MFT header entry count",
                 f"{ar.entry_count} -> {ar.entry_count + 1}")
        plan.add(HDR_MFT_SIZE, 4, "file header: MFT size",
                 f"{ar.mft_size} -> {ar.mft_size + ENTRY_SIZE}")
        self_row = ar.entries[MFT_SELF_ROW - 1]
        plan.add(ar.mft_offset + (MFT_SELF_ROW - 1) * ENTRY_SIZE, ENTRY_SIZE,
                 f"MFT row {MFT_SELF_ROW} (the table describing itself)",
                 "its size field must restate the new table size")
        # Does the table have room to grow where it sits?
        mft_end = ar.mft_offset + ar.mft_size
        nxt = min((e.offset for e in ar.entries if e.size and e.offset >= mft_end),
                  default=os.path.getsize(ar.path))
        room = nxt - mft_end
        # ...and `nxt` is the gap measure a third time. The bytes past the table
        # belong to no MFT row, so they read as headroom; on this archive the
        # first 14 MB of that headroom is the container arena the table itself
        # rotates through, and the honest figure is two rows, not 613,292.
        walls = [x.start_block * block + mk[0] * block
                 for x in excluded for mk in x.marks
                 if x.start_block * block + mk[0] * block >= mft_end]
        wall = min(walls, default=None)
        clear = room if wall is None else min(room, wall - mft_end)
        if room < ENTRY_SIZE:
            plan.blockers.append(
                f"the MFT cannot grow in place: only {room} bytes before the "
                f"next allocated entry at 0x{nxt:X}")
        elif clear < ENTRY_SIZE:
            plan.blockers.append(
                f"the MFT cannot grow in place: {room} bytes before the next "
                f"allocated entry at 0x{nxt:X}, but only {clear} before the "
                f"container generation at 0x{wall:X}, which no MFT row points "
                f"at and which the gap measure therefore counts as free")
        else:
            note = (f"the MFT can grow in place: {clear} bytes = "
                    f"{clear // ENTRY_SIZE} more rows")
            if wall is not None and clear < room:
                note += (f" before the container generation at 0x{wall:X} "
                         f"(the next ALLOCATED entry is far past it, at "
                         f"0x{nxt:X} -- {room} bytes of apparent headroom, "
                         f"which is the same gap measure that made this "
                         f"planner place files on top of live containers)")
            else:
                note += f" before the next entry at 0x{nxt:X}"
            plan.notes.append(note)

    # The file-id table, so the client can address it at all.
    tbl = ar.entries[1]
    tbl_reserved = blocks_for(tbl.size, block) * block
    if file_id is None:
        plan.notes.append("no file id requested; skipping the file-id table edit")
    elif tbl.size + 8 <= tbl_reserved:
        plan.add(tbl.offset + tbl.size, 8,
                 f"file-id table: append (id {file_id}, row {row})",
                 f"fits in the table's existing reservation "
                 f"({tbl_reserved - tbl.size} bytes spare = "
                 f"{(tbl_reserved - tbl.size) // 8} pairs)")
        plan.add(ar.mft_offset + 1 * ENTRY_SIZE, ENTRY_SIZE,
                 "MFT row 2: file-id table size and crc",
                 f"{tbl.size} -> {tbl.size + 8}")
    else:
        plan.blockers.append(
            f"the file-id table has no room in its reservation "
            f"({tbl.size} of {tbl_reserved} used); it would have to be relocated, "
            f"which means finding {blocks_for(tbl.size + 8, block)} free blocks "
            f"and moving {tbl.size} bytes")

    plan.notes.append(
        "every touched entry's crc must be recomputed as CRC-32/ISO-HDLC over its "
        "stored bytes, and MFT row 3's own crc must be recomputed over the table "
        "skipping its own 24-byte row -- see datwrite.py:mft_self_crc")
    return plan


def plan_overwrite(ar, row_index, new_size):
    """Replace an existing file's contents. The cheap case."""
    block = ar.block_size
    try:
        e = ar.entries[row_index - 1]
    except IndexError:
        plan = Plan(f"OVERWRITE row {row_index}")
        plan.blockers.append(f"no such row (archive has {ar.entry_count})")
        return plan
    reserved = blocks_for(e.size, block) * block
    plan = Plan(f"OVERWRITE row {row_index}: {e.size} -> {new_size} bytes "
                f"(reservation {reserved})")
    if new_size > reserved:
        plan.blockers.append(
            f"{new_size} bytes will not fit the {reserved}-byte reservation; "
            f"this becomes a relocation, not an overwrite")
        plan.notes.append("plan an insert instead, then repoint the file-id table")
        return plan
    plan.add(e.offset, new_size, f"payload of row {row_index}",
             f"in place; {reserved - new_size} bytes of the reservation unused")
    plan.add(ar.mft_offset + (row_index - 1) * ENTRY_SIZE, ENTRY_SIZE,
             f"MFT row {row_index}: size and crc",
             f"crc = CRC-32 of the new stored bytes")
    plan.notes.append(
        "nothing else moves: no table growth, no file-id change, no relocation. "
        "This is the cheapest possible modification of the archive.")
    return plan


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--insert", type=int, metavar="BYTES",
                    help="plan inserting a new file of this stored size")
    ap.add_argument("--file-id", type=int, default=None,
                    help="with --insert, also plan the file-id table entry")
    ap.add_argument("--overwrite", type=int, metavar="ROW",
                    help="plan replacing an existing row's contents")
    ap.add_argument("--new-size", type=int, default=None,
                    help="with --overwrite, the new stored size (default: same)")
    ap.add_argument("--free", action="store_true", help="report free space only")
    args = ap.parse_args()

    with Archive(args.dat) as ar:
        print(f"{os.path.basename(args.dat)}: {ar.entry_count} entries, "
              f"block size {ar.block_size}")
        print("READ-ONLY. This tool computes plans and applies none of them.\n")

        block = ar.block_size
        classified = None

        if args.free or args.insert:
            classified = classify_runs(ar)

        if args.free or not (args.insert or args.overwrite):
            if classified is None:
                classified = classify_runs(ar)
            usable, excluded = classified
            gap = sum(n for _, n in usable) * block
            held = sum(x.blocks for x in excluded) * block
            print(f"unallocated by the gap measure: {gap + held} bytes in "
                  f"{len(usable) + len(excluded)} runs of whole blocks")
            print(f"  withheld as live container generations: {held} bytes in "
                  f"{len(excluded)} run(s)")
            for x in sorted(excluded, key=lambda r: -r.blocks):
                print(f"    0x{x.start_block*block:012X}  {x.blocks:>7} blocks  "
                      f"{x.blocks*block:>11} bytes  {x.why()}")
            print(f"  usable: {gap} bytes in {len(usable)} runs")
            big = [r for r in usable if r[1] * block >= 65536]
            print(f"    runs >= 64 KB: {len(big)}, "
                  f"totalling {sum(n for _, n in big) * block} bytes")
            print("    largest usable:")
            for b, n in sorted(usable, key=lambda r: -r[1])[:8]:
                where = "after the MFT" if b * block >= ar.mft_offset else "before"
                print(f"      0x{b*block:012X}  {n:>7} blocks  "
                      f"{n*block:>11} bytes  ({where})")
            erased = free_rows(ar)
            reserved = [r for r in free_rows(ar, include_reserved=True)
                        if r < FIRST_CLAIMABLE_ROW]
            print(f"\nerased MFT rows (size 0): "
                  f"{len(erased)} claimable, {len(reserved)} reserved")
            if erased:
                print(f"  claimable: {erased[:12]}"
                      f"{' ...' if len(erased) > 12 else ''}")
            if reserved:
                print(f"  reserved (rows < {FIRST_CLAIMABLE_ROW}, never used by "
                      f"the client): {reserved}")
            tbl = ar.entries[1]
            spare = blocks_for(tbl.size, block) * block - tbl.size
            print(f"\nfile-id table: {tbl.size // 8} pairs, {spare} bytes spare "
                  f"in its reservation = {spare // 8} more pairs in place")
            if not (args.insert or args.overwrite):
                return 0

        if args.insert:
            plan_insert(ar, args.insert, file_id=args.file_id,
                        classified=classified).show(block)
        if args.overwrite:
            row = args.overwrite
            size = args.new_size
            if size is None:
                size = ar.entries[row - 1].size if row <= ar.entry_count else 0
            plan_overwrite(ar, row, size).show(block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
