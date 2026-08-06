#!/usr/bin/env python3
"""Check the decompressor, and specifically the zero-length code.

    python toolkit/mapdata/test_gwdat.py
    python toolkit/mapdata/test_gwdat.py --sample 400

gwdat.py's header is careful about what evidence this decoder has, and the
honest summary is that "it produced the declared number of bytes" proves
nothing, because the loop stops at that number by construction. So the checks
here are ones the artifact can refute.

Section 3 is the reason this file exists. Twelve of the archive's text files
used to fail outright with `zero-length code (table hole)`, and the fix is only
believable if the bytes that come out are right rather than merely present. The
referee is the two trailing bytes of every text file, which are
(language_index, file_index): eleven different files must produce eleven
different, predicted tails, and each must sit at the end of exactly 1,024
records that tile the blob with no remainder. A decoder that emitted plausible
garbage would have to land on all of that by accident.

Section 4 guards the property the fix rests on -- that consuming zero bits
really is a no-op -- because if it were not, a zero-length code would silently
corrupt the bit position for everything after it.
"""

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))

import checks                                           # noqa: E402
import gwdat                                            # noqa: E402
from archive import Archive, ffna_chunks, DEFAULT_DAT   # noqa: E402
import textrec                                          # noqa: E402

MAP_FLAGS = 259
ZERO_LEN_FILE_INDEX = 98      # the only text file index that needs the fix
LANGUAGES = 11
RECORDS = 1024
DECOMPRESSED_SIZE = 6146      # text file 98, identical in every language

# The floor counts what a healthy run executes, measured at 15 green: one
# chunk-walk check in section 1, one compressed-entry sweep in section 2, the
# eleven per-language tails plus the guard that the zero-length path was taken
# at all in section 3, and one zero-bit no-op in section 4. --sample changes the
# stride inside section 2, not the number of checks, so the count does not move
# with the fixture; section 3's eleven are fixed by LANGUAGES.
LEDGER = checks.Ledger("gwdat decompressor", floor=15)
check = checks.adopt(LEDGER)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--exe", default=textrec.DEFAULT_EXE)
    ap.add_argument("--sample", type=int, default=200,
                    help="stride over compressed entries in section 2")
    args = ap.parse_args()
    t0 = time.perf_counter()

    with Archive(args.dat) as ar:
        print("\n1. map files still decompress and tile their chunk tables")
        maps = [e for e in ar.entries if e.flags == MAP_FLAGS]
        walked = broke = 0
        for e in maps[::max(1, len(maps) // 12)]:
            try:
                data = ar.read(e)
                for _cid, _off, _size in ffna_chunks(data):
                    pass          # ffna_chunks raises unless it lands exactly
                walked += 1
            except Exception:                               # noqa: BLE001
                broke += 1
        check(broke == 0, "sampled maps decompress and their chunks tile",
              f"{walked} ok, {broke} broken")

        print(f"\n2. every {args.sample}th compressed entry decompresses")
        comp = [e for e in ar.entries if e.compression == 8]
        picks = comp[::args.sample]
        bad = []
        for e in picks:
            try:
                ar.read(e)
            except Exception as exc:                        # noqa: BLE001
                bad.append((e.index, str(exc)[:50]))
        check(not bad, f"{len(picks) - len(bad)} of {len(picks)} decompress")
        for row, why in bad[:6]:
            print(f"        row {row}: {why}")

    print("\n3. the zero-length code, on the files that used to fail")
    seen_zero = 0
    original = gwdat.build_table

    def counting(reader):
        nonlocal seen_zero
        table = original(reader)
        if table.zero_len:
            seen_zero += 1
        return table

    gwdat.build_table = counting
    try:
        for lang in range(LANGUAGES):
            with textrec.TextIndex(args.exe, args.dat, lang) as ix:
                fid = ix.archive_id(ZERO_LEN_FILE_INDEX)
                row = ix.file_ids.get(fid)
                entry = ix._rows[row]
                blob = ix.archive.read(entry)
                recs, tail, tiled = textrec.walk(blob)
                want = bytes([lang, ZERO_LEN_FILE_INDEX])
                ok = (len(blob) == DECOMPRESSED_SIZE and tiled
                      and len(recs) == RECORDS and tail == want)
                check(ok, f"language {lang:>2} tiles and ends where predicted",
                      f"{len(blob)}B, {len(recs)} records, tail {tail.hex()}"
                      f" (want {want.hex()})")
    finally:
        gwdat.build_table = original

    # Without this the section above could pass for the wrong reason -- a
    # future change that never takes the zero-length path at all would look
    # identical from the outside.
    check(seen_zero >= LANGUAGES,
          "the zero-length path was actually exercised",
          f"{seen_zero} zero-length tables built")

    print("\n4. consuming zero bits is a no-op")
    r = gwdat.BitReader(bytes(range(32)))
    before = (r.buf1, r.buf2, r.idx, r.avail)
    r.consume(0)
    check((r.buf1, r.buf2, r.idx, r.avail) == before,
          "bit position and buffers are unchanged")

    dt = time.perf_counter() - t0
    print(f"\nelapsed {dt:.1f}s")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
