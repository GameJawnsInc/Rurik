"""Check the MFT's checksum field and the allocator's rules against real bytes.

studies/mapdata/FORMAT.md recorded the u32 at MFT entry +0x14 as NOT FOUND:
"GWUnpacker calls it CRC, OpenTyria calls it checksum, neither computes or
verifies it, and no polynomial was tested. Do not assume." This test is the
result of finally testing one.

It is CRC-32/ISO-HDLC -- the ordinary zlib polynomial, reflected, init and xorout
0xFFFFFFFF -- computed over the STORED bytes: the compressed form exactly as it
sits on disk, not the decompressed payload. Measured 2026-08-05 across two
independent archives: 177,327 of 177,329 non-empty rows in the run-dir copy and
177,319 of 177,321 in the install copy.

WHY THIS CHECK IS WORTH ANYTHING. The hypothesis has zero free parameters -- no
seed to fit, no offset to slide, no length to choose -- and every row is an
independent 32-bit target. If the polynomial were wrong, essentially every row
would fail rather than a handful. That is the opposite of the decompressor's
declared-length "check", which the decoder forces true by construction.

TWO ROWS DO NOT FOLLOW THAT RULE, AND BOTH ARE EXPLAINED. Neither is an exception
to the archive's integrity; each is protected by a different checksum.

  row 1  is the 32-byte file header. Its MFT crc field is stored as 0 -- but the
         header protects itself, at its own +0x0C, with CRC-32 over its FIRST 12
         BYTES ONLY. Matches on both archives.
  row 3  is the master file table describing ITSELF, and the circularity is broken
         the obvious way: the checksum covers the table with its own 24-byte
         self-entry REMOVED from the stream --
             crc32(mft[0x00:0x48]) continued over mft[0x60 : count*24]
         Matches on both archives, on two different values.

A CORRECTION THIS FILE EXISTS TO RECORD. An earlier version of this test asserted
that row 3 was "stale by construction" and that the client therefore loads an
archive failing its own checksum -- which was offered as evidence that the crc is
not a gate on load. That was wrong. The rule had simply not been found: the search
had tried zeroing row 3's crc field and zeroing the whole row, but never removing
the row from the stream. The assertion passed for the wrong reason, because
"row 3's crc != crc32(the whole table)" is true and means nothing.

The correct position is stronger and less convenient: THE ARCHIVE IS FULLY
SELF-CHECKING. Every row, the file header and the table itself all carry a
checksum that reproduces. A writer must get all three right.

    python toolkit/mapdata/test_datcrc.py
    python toolkit/mapdata/test_datcrc.py --full          # every row, ~4 GB of I/O
    python toolkit/mapdata/test_datcrc.py --dat <path>
"""

import argparse
import binascii
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, DEFAULT_DAT, ENTRY_SIZE  # noqa: E402
import checks  # noqa: E402

# FLOOR: the ten checks in sections 1-6, all of which run unconditionally on any
# archive -- two container invariants, two allocator invariants, two extent
# invariants, the strided crc sweep, the two self-referential rules, and the
# summary. Measured on the run-dir Gw.dat, 2026-08-06: a green run prints exactly
# ten [PASS] lines. --full changes how many ROWS section 4 reads, not how many
# checks the file executes, so the floor is the same either way. If this run
# scores nine, a section stopped running and the remaining passes mean nothing.
LEDGER = checks.Ledger("dat checksums", floor=10)

# The two rows that describe the container rather than living inside it. They are
# excluded from the plain over-the-stored-bytes rule and checked by their own in
# section 5 -- not tolerated, checked.
SELF_REFERENTIAL_ROWS = {1, 3}

# MEASURED on both archives: every entry offset is a multiple of the block size
# declared in the file header, and the GCD over all 177,329 of them is exactly
# 512 -- so 512 is the real granularity, not merely a divisor of it.
EXPECTED_BLOCK_SIZE = 512

# Sampling stride for the default run. Every 9th row is ~19,700 independent
# 32-bit checks, which is already far past the point of coincidence, and it
# turns four gigabytes of reading into a few hundred megabytes.
DEFAULT_STRIDE = 9

READ_CHUNK = 1 << 22


def crc_of(fh, offset, size):
    """CRC-32 of an entry's stored bytes, read in chunks so a 6 MB row is fine."""
    fh.seek(offset)
    acc = 0
    remaining = size
    while remaining:
        buf = fh.read(min(READ_CHUNK, remaining))
        if not buf:
            return None
        acc = binascii.crc32(buf, acc)
        remaining -= len(buf)
    return acc


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--full", action="store_true",
                    help="check every row instead of a strided sample")
    args = ap.parse_args()

    if not os.path.exists(args.dat):
        print(f"[FAIL] no archive at {args.dat}")
        return 1

    check = checks.adopt(LEDGER)

    with Archive(args.dat) as ar:
        print(f"{os.path.basename(args.dat)}: {ar.entry_count} entries, "
              f"block size {ar.block_size}")
        live = [e for e in ar.entries if e.size]
        filesize = os.path.getsize(args.dat)

        print("\n1. the container describes itself consistently")
        check(ar.block_size == EXPECTED_BLOCK_SIZE,
              f"block size is {EXPECTED_BLOCK_SIZE} (got {ar.block_size})")
        row3 = ar.entries[2]
        check(row3.offset == ar.mft_offset and row3.size == ar.mft_size,
              "row 3 is the MFT itself: its offset and size match the header's")

        print("\n2. entry offsets obey the allocator's alignment")
        misaligned = [e.index for e in live if e.offset % ar.block_size]
        check(not misaligned,
              f"all {len(live)} offsets are {ar.block_size}-byte aligned"
              + (f" (first bad: row {misaligned[0]})" if misaligned else ""))
        gcd = 0
        for e in live:
            a, b = gcd, e.offset
            while b:
                a, b = b, a % b
            gcd = a
        check(gcd == ar.block_size,
              f"GCD of all offsets is exactly the block size (got {gcd})")

        print("\n3. no two entries share storage")
        spans = sorted((e.offset, e.size, e.index) for e in live)
        overlaps = [spans[i + 1][2] for i in range(len(spans) - 1)
                    if spans[i + 1][0] < spans[i][0] + spans[i][1]]
        check(not overlaps,
              f"no entry extent runs into the next"
              + (f" (first bad: row {overlaps[0]})" if overlaps else ""))
        tail = max(e.offset + e.size for e in live)
        check(tail <= filesize,
              f"the last allocated byte (0x{tail:X}) is inside the file")

        print("\n4. the crc field is CRC-32/ISO-HDLC over the stored bytes")
        rows = live if args.full else live[::DEFAULT_STRIDE]
        print(f"  checking {len(rows)} of {len(live)} rows"
              f"{'' if args.full else f' (every {DEFAULT_STRIDE}th; --full for all)'}")
        matched = 0
        unexpected = []
        expected_misses = set()
        for e in rows:
            got = crc_of(ar.fh, e.offset, e.size)
            if got is None:
                unexpected.append((e.index, "unreadable"))
            elif got == e.crc:
                matched += 1
            elif e.index in SELF_REFERENTIAL_ROWS:
                expected_misses.add(e.index)
            else:
                unexpected.append((e.index, f"0x{e.crc:08X} != 0x{got:08X}"))
        check(not unexpected,
              f"{matched} rows match; {len(unexpected)} unexplained mismatch(es)")
        for idx, why in unexpected[:10]:
            print(f"         row {idx}: {why}")

        print("\n5. the two self-referential rows use their own rules")
        # Checked explicitly whether or not the strided sample reached them.
        ar.fh.seek(0)
        head = ar.fh.read(32)
        stored_hdr = struct.unpack_from("<I", head, 0x0C)[0]
        check(binascii.crc32(head[:12]) == stored_hdr,
              f"the file header's +0x0C is CRC-32 of its first 12 bytes "
              f"(0x{stored_hdr:08X})")

        ar.fh.seek(ar.mft_offset)
        mft = ar.fh.read(ar.mft_size)
        acc = binascii.crc32(mft[0x00:0x48])
        acc = binascii.crc32(mft[0x60:ar.entry_count * ENTRY_SIZE], acc)
        check(acc == row3.crc,
              f"row 3 (the MFT) checksums itself with its own self-entry removed "
              f"from the stream (0x{row3.crc:08X})")

        print("\n6. nothing in the archive fails its own checksum")
        check(not unexpected and binascii.crc32(head[:12]) == stored_hdr
              and acc == row3.crc,
              "every row, the header and the table all verify -- a writer must "
              "maintain all three")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
