#!/usr/bin/env python3
"""Resolve a client string id to the text the game displays.

Python 3 standard library only. Read-only on both the client binary and the
archive; never launches anything.

This is the missing link between the tables baked into `Gw.exe` and the words a
player sees. The skill table, the area table and anything else with a `name_id`
carry an integer, not a string -- the strings live in `Gw.dat`.

THE CHAIN, and what is measured about each step:

  string id -> (file_index, record_index)    file = id // 1024, rec = id % 1024
      CLIENT-DATA. Read out of Fournux/Tyria-Extractor, not re-derived by us.
      What makes it credible here is that it lands on the right words: see the
      oracle in __main__.

  file_index -> a packed file reference        via a 1,089-entry pointer array
      MEASURED. 11 languages x 99 files, ordered [language][file] -- proven by
      the two trailing bytes of each decompressed file, which are
      (language_index, file_index) and agree with the array position. Located
      structurally, never by address, because a build-specific address is not
      part of any format.

  packed reference -> archive file id
      MEASURED, and this is the load-bearing new result. The client stores a
      file reference as one dword holding two 16-bit parts, each biased by
      0x100. Inverting GWCA's `file_id1()`/`file_id2()` accessors gives

          id = (high16 - 0x100) * 0xFF00 + (low16 - 0x100) + 1

      and that resolves **1089 of 1089** entries against the archive's own
      file-id table. Nothing was fitted: the formula came from upstream's
      accessors and the archive either knew the resulting ids or did not.
      Three rival readings of the same dword score 471, 130 and 0.

  archive file id -> MFT row -> decompressed blob    (toolkit/mapdata)

  blob -> records            u16 total_length, u16 aux, u16 kind, then
                             total_length - 6 bytes of payload.

      MEASURED, and the check is the good kind: with this header, **all 99
      language-0 files tile to exactly 1,024 records and a 2-byte tail**, with
      no file left over and none short — and so do all 1,089 files across all
      eleven languages. Upstream reports "1,024 records then two trailing
      bytes" for every file; this reproduces that independently and says why.

      It was 98 of 99 until gwdat.py's zero-length-code fix landed; the holdout
      was the one file gwdat.py could not decompress at all.

      Reading the length as a u32 instead -- which is what a first pass did --
      walks a plausible-looking distance and then stops dead mid-file, because
      the first record of a kind whose `aux` is non-zero turns into an absurd
      length. It got 3 files right out of 99 and looked fine on the ones it
      got.

WHAT A RECORD KIND MEANS is only partly established. Census over language 0:

      kind 0x07  66,330  65.4%  the majority. High-entropy payload, `aux`
                                non-zero and varying -- shaped like a
                                per-record compression with `aux` as the
                                decoded size. NOT ESTABLISHED.
      kind 0x10  28,410  28.0%  plain UTF-16LE. This is what `get()` returns.
      kind 0x06   5,735   5.7%      kind 0x05  879  0.9%
      kind 0x08      16          kind 0x0D    4     kind 0x0E  2

`get()` returns None for any kind it cannot decode, rather than handing back
bytes dressed as a string. An id that resolves is trustworthy; an id that does
not is reported missing, not invented.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mapdata"))
from gwpe import PE  # noqa: E402
from archive import Archive, file_id_table, DEFAULT_DAT  # noqa: E402

RECORDS_PER_FILE = 1024
FILES_PER_LANGUAGE = 99
LANGUAGES = 11
POINTER_COUNT = FILES_PER_LANGUAGE * LANGUAGES   # 1089
REF_BIAS = 0x100
REF_STRIDE = 0xFF00
KIND_TEXT = 0x0010
HEADER_SIZE = 6

DEFAULT_EXE = r"C:\gd\Rurik\vault\run\2026-07-29_221c13772c7a\Gw.exe"


def combine(packed: int) -> int:
    """The client's two-part file reference as one archive file id."""
    return (((packed >> 16) - REF_BIAS) * REF_STRIDE
            + ((packed & 0xFFFF) - REF_BIAS) + 1)


def plausible_ref(packed: int) -> bool:
    """Could this dword be a packed file reference at all?

    Both halves are biased by 0x100, so neither can be below it, and the low
    half indexes within a 0xFF00 stride. Cheap enough to run over every dword
    in the image and tight enough that random data rarely survives it.
    """
    lo, hi = packed & 0xFFFF, packed >> 16
    return REF_BIAS <= lo < REF_BIAS + REF_STRIDE and hi >= REF_BIAS


def find_pointer_table(pe: PE) -> int | None:
    """File offset of the 1,089-entry text-file pointer array.

    Structural, not an address: the array is the longest run of dwords that are
    valid in-image VAs whose targets are an 8-byte `(packed_ref, 0)` record
    with a plausible reference. Nothing here is build-specific.
    """
    d = pe.data
    best = None
    for sec in pe.sections:
        lo, hi = sec["rawptr"], sec["rawptr"] + sec["rawsize"]
        off, run_start, run = lo, None, 0
        while off + 4 <= hi:
            ok = False
            va = struct.unpack_from("<I", d, off)[0]
            if va > pe.image_base:
                t = pe.rva_to_off(va - pe.image_base)
                if t is not None and t + 8 <= len(d):
                    ref, zero = struct.unpack_from("<II", d, t)
                    ok = zero == 0 and plausible_ref(ref)
            if ok:
                if run == 0:
                    run_start = off
                run += 1
            else:
                if run >= POINTER_COUNT and (best is None or run > best[1]):
                    best = (run_start, run)
                run = 0
            off += 4
        if run >= POINTER_COUNT and (best is None or run > best[1]):
            best = (run_start, run)
    return None if best is None else best[0]


def walk(blob: bytes):
    """Split a decompressed text file into records.

    Returns (records, trailing, tiled). `records` is a list of
    (kind, aux, payload); `tiled` says the walk consumed the blob down to
    exactly the 2-byte (language, file) tail. A short walk is reported, never
    smoothed over -- it means a record kind is framed in a way we do not know.
    """
    recs = []
    p = 0
    end = len(blob)
    while p + HEADER_SIZE <= end:
        length, aux, kind = struct.unpack_from("<HHH", blob, p)
        if length < HEADER_SIZE or p + length > end:
            break
        recs.append((kind, aux, blob[p + HEADER_SIZE:p + length]))
        p += length
    return recs, blob[p:], len(blob) - p == 2


class TextIndex:
    """string id -> text, for one language."""

    def __init__(self, exe=DEFAULT_EXE, dat=DEFAULT_DAT, language=0):
        self.pe = PE(exe)
        self.language = language
        table = find_pointer_table(self.pe)
        if table is None:
            raise LookupError(
                "no 1,089-entry text pointer array found. Either the client "
                "changed shape or the reference encoding did; do not fall back "
                "to a hardcoded address.")
        self.table_off = table
        self.table_va = self.pe.off_to_rva(table) + self.pe.image_base
        self.archive = Archive(dat)
        self.file_ids = file_id_table(self.archive)
        self._rows = {e.index: e for e in self.archive.entries}
        self._cache: dict[int, list] = {}
        self.short_files: dict[int, int] = {}

    def close(self):
        self.archive.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def archive_id(self, file_index: int) -> int:
        slot = self.language * FILES_PER_LANGUAGE + file_index
        va = struct.unpack_from("<I", self.pe.data,
                                self.table_off + slot * 4)[0]
        off = self.pe.rva_to_off(va - self.pe.image_base)
        return combine(struct.unpack_from("<I", self.pe.data, off)[0])

    def records(self, file_index: int):
        if file_index not in self._cache:
            if not 0 <= file_index < FILES_PER_LANGUAGE:
                self._cache[file_index] = []
                return []
            row = self.file_ids.get(self.archive_id(file_index))
            if row is None:
                self._cache[file_index] = []
                return []
            try:
                blob = self.archive.read(self._rows[row])
            except Exception:                                   # noqa: BLE001
                # gwdat.py's known huffman table hole. A file we cannot
                # decompress is a file we have no strings for -- say so.
                self._cache[file_index] = []
                self.short_files[file_index] = -1
                return []
            recs, _tail, tiled = walk(blob)
            if not tiled or len(recs) != RECORDS_PER_FILE:
                self.short_files[file_index] = len(recs)
            self._cache[file_index] = recs
        return self._cache[file_index]

    def get(self, string_id: int):
        """The text for a string id, or None if we could not reach it."""
        recs = self.records(string_id // RECORDS_PER_FILE)
        idx = string_id % RECORDS_PER_FILE
        if idx >= len(recs):
            return None
        kind, _aux, payload = recs[idx]
        if kind != KIND_TEXT:
            return None
        try:
            return payload.decode("utf-16-le")
        except UnicodeDecodeError:
            return None

    def kind_of(self, string_id: int):
        """The record kind behind a string id, or None if unreachable."""
        recs = self.records(string_id // RECORDS_PER_FILE)
        idx = string_id % RECORDS_PER_FILE
        return recs[idx][0] if idx < len(recs) else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", default=DEFAULT_EXE)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--language", type=int, default=0)
    ap.add_argument("ids", nargs="*", help="string ids to resolve")
    args = ap.parse_args()

    with TextIndex(args.exe, args.dat, args.language) as ix:
        print(f"pointer array at VA 0x{ix.table_va:08x} "
              f"(file 0x{ix.table_off:06x}), located structurally")
        if args.ids:
            for raw in args.ids:
                sid = int(raw, 0)
                print(f"  {sid:>8}  file {sid // RECORDS_PER_FILE:>2} "
                      f"record {sid % RECORDS_PER_FILE:>4}  "
                      f"{ix.get(sid)!r}")
            return 0

        # No ids given: census the language and report coverage honestly.
        kinds: dict[int, int] = {}
        walked = 0
        for fi in range(FILES_PER_LANGUAGE):
            recs = ix.records(fi)
            if len(recs) == RECORDS_PER_FILE:
                walked += 1
            for k, _aux, _p in recs:
                kinds[k] = kinds.get(k, 0) + 1
        print(f"  {walked} of {FILES_PER_LANGUAGE} files tile to exactly "
              f"{RECORDS_PER_FILE} records and a 2-byte tail")
        short = {k: v for k, v in ix.short_files.items() if v >= 0}
        undec = [k for k, v in ix.short_files.items() if v < 0]
        for k in sorted(short):
            print(f"      file {k:>2} walked short: {short[k]} records")
        if undec:
            print(f"  {len(undec)} would not decompress "
                  f"(gwdat.py's huffman table hole): {sorted(undec)}")
        print("  record kinds:")
        total_recs = sum(kinds.values())
        for k in sorted(kinds, key=lambda k: -kinds[k]):
            note = "  plain UTF-16" if k == KIND_TEXT else ""
            print(f"      0x{k:02x}  {kinds[k]:>6}  "
                  f"{100.0 * kinds[k] / total_recs:5.1f}%{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
