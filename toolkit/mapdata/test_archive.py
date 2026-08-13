"""Check the archive reader against real bytes, not against anyone's source.

This is the test the protocol layer cannot have. Every claim our server makes
about the wire rests on reconstructions, so its tests can only check that we
encode what we intended to encode. Here the artifact is on disk and the format
is falsifiable, so these assertions can fail for the right reason: because the
file says otherwise.

The strongest check is section 3, and it is worth understanding why it is strong.
Decompression cannot be validated by "the output was as long as the header said"
-- the decoder stops at that length by construction, so the match is forced (see
the caveat at the top of gwdat.py). But a map's FFNA chunk table is a completely
independent structure: a walk of (id, size, payload) records either consumes the
decompressed output to the exact final byte or it does not. Wrong decompression
produces garbage sizes and the walk runs off the end. That check has no
circularity in it.

    python toolkit/mapdata/test_archive.py
    python toolkit/mapdata/test_archive.py --dat <path>

ROW INDICES ARE COPY-SPECIFIC. The reference rows below were measured against
the archive our patched client has actually run (177,342 entries). A running
client writes to its own archive, so the install copy has a different entry
count and different row numbers. Against a different copy the reference-row
check is skipped rather than failed -- it is not a defect in the reader.
"""

import argparse
import struct
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, ffna_type, DEFAULT_DAT  # noqa: E402
import checks  # noqa: E402

# Map files carry flags 259. The high byte is the stream (1) and the low byte is
# the entry flags (3). MEASURED: exactly 349 entries in this archive have it, and
# every one sampled decompressed to an ffna type-3 payload.
MAP_FLAGS = 259
EXPECTED_MAP_COUNT = 349
FFNA_TYPE_MAP = 3

# Reference maps, measured on the run-dir archive. The point of pinning exact
# byte counts is that a decompressor regression changes them.
EXPECTED_ENTRY_COUNT = 177342
REFERENCE_MAPS = {7982: (24, 2925270), 20444: (22, 3389269)}

SAMPLE_SIZE = 6

# FLOOR: the nine checks that run against ANY copy of the archive -- the two
# header invariants in section 1, the map-flag count in section 2, and one per
# sampled map in section 3 (SAMPLE_SIZE = 6). Section 4's two reference rows are
# deliberately outside the floor: row indices are copy-specific, so that section
# declares a skip on an archive with a different entry count (see the header).
# Measured on the run-dir Gw.dat, 2026-08-06: a green run prints eleven [PASS]
# lines, nine of them mandatory. Scoring under nine means a map stopped being
# sampled or a section stopped running, and the passes that remain prove nothing.
#
# RAISED 9 -> 14 on 2026-08-13: section 1b adds five more that hold against ANY
# copy (the row/position conventions and the file-id table's row), because
# confusing `entries[row]` with a row NUMBER returns a different file rather
# than an error, and once cost a nearly-filed false refutation.
LEDGER = checks.Ledger("dat archive", floor=14)
check = checks.adopt(LEDGER)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dat", default=DEFAULT_DAT)
    args = ap.parse_args()

    if not os.path.exists(args.dat):
        print(f"no archive at {args.dat}")
        print("See RUNBOOK.md for how the study copy is made.")
        return 1

    print(f"archive: {args.dat}")
    with Archive(args.dat) as ar:
        print("\n1. the header cross-checks itself")
        # Archive() already raises if count * 24 != mft_size, so reaching here
        # is the check. Restate it so a reader sees the arithmetic.
        check(ar.entry_count * 24 == ar.mft_size,
              f"{ar.entry_count} entries x 24 == declared MFT size "
              f"{ar.mft_size}")
        check(ar.block_size == 512, f"block size is 512 (got {ar.block_size})")

        # ROW NUMBER vs POSITION. `entries` is positional and `row()` is
        # one-based, and confusing them returns a DIFFERENT FILE rather than an
        # error -- on 2026-08-13 that silently resolved a text row to a texture
        # and nearly produced a false refutation. Both conventions are pinned
        # here so neither can drift into the other.
        print("\n1b. row numbers are one-based; entries is positional")
        check(ar.entries[0].index == 1 and ar.entries[9].index == 10,
              "entries[k].index == k + 1 -- the list is POSITIONAL")
        last = len(ar.entries)
        check(ar.row(1).index == 1 and ar.row(10).index == 10
              and ar.row(last).index == last,
              f"row(n).index == n at both ends (1..{last:,})")
        check(last == ar.entry_count - 1,
              f"and entry_count ({ar.entry_count:,}) COUNTS the MFT header "
              f"slot, so the highest row is one less ({last:,}) -- bounding on "
              f"entry_count walks off the end, which is how this was found")
        check(ar.row(2) is ar.entries[1],
              "row(n) and entries[n - 1] are the SAME object -- the existing "
              "call sites that write entries[row - 1] are correct")
        refused = 0
        for bad in (0, -1, last + 1):
            try:
                ar.row(bad)
            except IndexError:
                refused += 1
        check(refused == 3,
              f"row(0), row(-1) and row(last + 1) are all refused ({refused}/3) "
              f"-- a negative index would otherwise wrap to the END of the table")
        # The file-id table's row, MEASURED rather than assumed: it is the only
        # row whose payload parses wholly as (file_id, row) pairs.
        idtable = ar.row(2)
        blob = ar.read(idtable)
        pairs = len(blob) // 8
        good = sum(1 for i in range(min(pairs, 4000))
                   if 0 < struct.unpack_from("<II", blob, i * 8)[1] <= last)
        check(pairs > 100000 and good == min(pairs, 4000),
              f"MFT row 2 is the file-id table: {pairs:,} pairs, "
              f"{good}/{min(pairs, 4000)} rows in range")

        print("\n2. map files are identifiable by flags alone")
        maps = [e for e in ar.entries if e.flags == MAP_FLAGS]
        check(len(maps) == EXPECTED_MAP_COUNT,
              f"exactly {EXPECTED_MAP_COUNT} entries carry flags "
              f"{MAP_FLAGS} (got {len(maps)})")
        if not maps:
            print("\nno map entries; nothing further to check")
            return LEDGER.verdict()

        print("\n3. every sampled map decompresses and tiles its chunk table")
        print("   (independent of the declared output length -- see the header)")
        t0 = time.time()
        walked = 0
        for e in maps[:SAMPLE_SIZE]:
            try:
                data = ar.read(e)
            except Exception as exc:
                check(False, f"row {e.index}: read raised {type(exc).__name__}")
                continue
            if bytes(data[:4]) != b"ffna":
                check(False, f"row {e.index}: magic {bytes(data[:4])!r}, "
                             f"expected b'ffna'")
                continue
            if ffna_type(data) != FFNA_TYPE_MAP:
                check(False, f"row {e.index}: ffna type {ffna_type(data)}, "
                             f"expected {FFNA_TYPE_MAP}")
                continue
            try:
                chunks = list(ffna_chunks(data))
            except ValueError as exc:
                check(False, f"row {e.index}: chunk walk failed -- {exc}")
                continue
            walked += 1
            check(True, f"row {e.index}: {len(chunks)} chunks tiling "
                        f"{len(data)} bytes exactly")
        print(f"   {walked}/{min(SAMPLE_SIZE, len(maps))} maps in "
              f"{time.time() - t0:.0f}s")

        print("\n4. reference maps reproduce byte for byte")
        if ar.entry_count != EXPECTED_ENTRY_COUNT:
            LEDGER.skip("reference maps",
                        f"this archive has {ar.entry_count} entries, not "
                        f"{EXPECTED_ENTRY_COUNT}; row indices differ between "
                        "copies")
        else:
            by_index = {e.index: e for e in maps}
            for row, (want_chunks, want_bytes) in REFERENCE_MAPS.items():
                e = by_index.get(row)
                if e is None:
                    check(False, f"row {row} is not a map entry in this archive")
                    continue
                data = ar.read(e)
                chunks = list(ffna_chunks(data))
                check(len(data) == want_bytes and len(chunks) == want_chunks,
                      f"row {row}: {len(chunks)} chunks, {len(data)} bytes "
                      f"(expected {want_chunks}, {want_bytes})")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
