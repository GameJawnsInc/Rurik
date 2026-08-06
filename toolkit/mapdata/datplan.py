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
from archive import Archive, DEFAULT_DAT, ENTRY_SIZE  # noqa: E402

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

    def add(self, offset, length, what, detail=""):
        self.edits.append(Edit(offset, length, what, detail))

    @property
    def bytes_touched(self):
        return sum(e.length for e in self.edits)

    def show(self):
        print(self.summary)
        if self.blockers:
            print("\n  BLOCKED:")
            for b in self.blockers:
                print(f"    - {b}")
            return
        print(f"\n  {len(self.edits)} edit(s), {self.bytes_touched} bytes changed:")
        for e in sorted(self.edits, key=lambda x: x.offset):
            print(f"    0x{e.offset:012X}  +{e.length:<9} {e.what}")
            if e.detail:
                print(f"                              {e.detail}")
        if self.notes:
            print("\n  notes:")
            for n in self.notes:
                print(f"    - {n}")


def free_runs(ar):
    """Runs of unallocated whole blocks, largest first.

    Counted in blocks, not bytes. The byte-level gap between two entries is
    mostly dead space inside the earlier entry's own reservation -- 52.7 MB of
    the archive is exactly that -- and none of it is usable for a new file.
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
    runs.sort(key=lambda r: -r[1])
    return runs


def free_rows(ar, include_reserved=False):
    """MFT rows with size 0 -- erased slots a writer can claim without growing.

    Excludes the reserved low rows by default; see FIRST_CLAIMABLE_ROW.
    """
    return [e.index for e in ar.entries
            if e.size == 0
            and (include_reserved or e.index >= FIRST_CLAIMABLE_ROW)]


def plan_insert(ar, payload_size, flags=3, compression=0, file_id=None):
    """Add a brand-new file. The expensive case, and it is not very expensive."""
    block = ar.block_size
    need = blocks_for(payload_size, block)
    plan = Plan(f"INSERT a new {payload_size}-byte file "
                f"(compression {compression}, flags {flags})")

    runs = free_runs(ar)
    fit = next((r for r in runs if r[1] >= need), None)
    if fit is None:
        plan.blockers.append(
            f"no free run of {need} blocks ({need * block} bytes); "
            f"largest is {runs[0][1]} blocks" if runs else "no free space at all")
        return plan
    at = fit[0] * block
    plan.add(at, need * block, "payload",
             f"{payload_size} bytes + {need * block - payload_size} bytes of "
             f"block padding; run has {fit[1]} blocks, using {need}")

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
        if room < ENTRY_SIZE:
            plan.blockers.append(
                f"the MFT cannot grow in place: only {room} bytes before the "
                f"next allocated entry at 0x{nxt:X}")
        else:
            plan.notes.append(
                f"the MFT can grow in place: {room} bytes = {room // ENTRY_SIZE} "
                f"more rows before the next entry at 0x{nxt:X}")

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

        if args.free or not (args.insert or args.overwrite):
            runs = free_runs(ar)
            block = ar.block_size
            total = sum(n for _, n in runs) * block
            print(f"free space: {total} bytes in {len(runs)} runs of whole blocks")
            big = [r for r in runs if r[1] * block >= 65536]
            print(f"  runs >= 64 KB: {len(big)}, "
                  f"totalling {sum(n for _, n in big) * block} bytes")
            print("  largest:")
            for b, n in runs[:8]:
                where = "after the MFT" if b * block >= ar.mft_offset else "before"
                print(f"    0x{b*block:012X}  {n:>7} blocks  "
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
            plan_insert(ar, args.insert, file_id=args.file_id).show()
        if args.overwrite:
            row = args.overwrite
            size = args.new_size
            if size is None:
                size = ar.entries[row - 1].size if row <= ar.entry_count else 0
            plan_overwrite(ar, row, size).show()
    return 0


if __name__ == "__main__":
    sys.exit(main())
