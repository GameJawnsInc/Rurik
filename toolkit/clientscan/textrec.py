#!/usr/bin/env python3
r"""Resolve a client string id to the text the game displays.

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

  blob -> records            the 6-byte StringHeader, then bytes - 6 of payload.

      MEASURED, and the check is the good kind: with this header, **all 99
      language-0 files tile to exactly 1,024 records and a 2-byte tail**, with
      no file left over and none short — and so do all 1,089 files across all
      eleven languages. Upstream reports "1,024 records then two trailing
      bytes" for every file; this reproduces that independently and says why.

      It was 98 of 99 until gwdat.py's zero-length-code fix landed; the holdout
      was the one file gwdat.py could not decompress at all.

      Reading the length as a u32 instead -- which is what a first pass did --
      walks a plausible-looking distance and then stops dead mid-file. It got 3
      files right out of 99 and looked fine on the ones it got.

THE HEADER IS ArenaNet's OWN, and this file used to guess at two of its three
fields. The decoder is `P:\Code\Engine\Text\TextDecode.cpp` at VA 0x007cb000,
and it opens by asserting `data->bytes >= sizeof(StringHeader)` against a
compare with 6. Reading it settled the layout (see studies/textrec/FINDINGS.md):

      +0  u16 bytes    total record length, header included
      +2  u16 base     base codepoint for the symbol alphabet
      +4  u8  bits     bit width of a packed symbol, 1..0x10
      +5  u8  (zero in all 101,376 language-0 records)

`bits` is what this file used to call `kind`, and calling it a kind was the
mistake that made the census below look like a taxonomy. It is a **bit width**.
The client's own file walker range-checks it -- `cmp byte ptr [edi+4], 0x10;
ja invalid` -- which is a bound that makes sense for a width and none at all
for a type tag. Corroboration our decoder cannot force: the Korean, Japanese
and Chinese files are almost entirely `bits == 0x10` where the English file at
the same index is mostly `bits == 7`, because a wide script needs wide symbols.

A record decodes as: read `bits` bits at a time, LSB-first, then map
symbol 0 to U+0000, symbols 1..31 through a 32-entry table in the image, and
symbols >= 0x20 to `base - 0x20 + symbol`.

BUT ONLY ONE FORM IS READABLE FROM THE ARCHIVE ALONE. The client takes a
verbatim path only when `base == 0 and bits == 0x10`, which is plain UTF-16LE
and is 28% of records. Every other record is **RC4 ciphertext**
(`P:\Code\Base\Crypt\CptRc4.cpp`), decrypted with a key the *caller* supplies
and that is not stored in the record. Payload entropy is 8.000 bits/byte over
4.9 MB, and 17 readings of "the key is a function of the record's identity"
were refuted at scale. Census over language 0:

      bits 0x07  66,330  65.4%   encrypted
      bits 0x10  28,410  28.0%   28,407 plain (base 0); 3 encrypted (base != 0)
      bits 0x06   5,735   5.7%   encrypted
      bits 0x05     879   0.9%   encrypted
      bits 0x08  16   bits 0x0D  4   bits 0x0E  2      all encrypted

This is not a gap in our reading of the format -- the format is now read all
the way down -- it is a key we do not have. `decode()` below implements the
whole codec and will produce the text the moment a key turns up; `get()` still
returns None for encrypted records rather than handing back bytes dressed as a
string. An id that resolves is trustworthy; an id that does not is reported
missing, not invented.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mapdata"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "authsrv"))
from gwpe import PE  # noqa: E402
import pinned  # noqa: E402
from archive import Archive, file_id_table, DEFAULT_DAT  # noqa: E402
# The text records and the game channel use the SAME two primitives. Not a
# guess: the five folded round constants at Gw.exe 0x909db8 are exactly what
# arc4_hash's spec produces (see test_textrec.py section 5), so this import is
# a measured identity, not a convenience. Reusing it also means the cipher on
# this path is one a real client has already accepted during a handshake.
from gwcrypto import arc4_hash, ARC4  # noqa: E402

RECORDS_PER_FILE = 1024
FILES_PER_LANGUAGE = 99
LANGUAGES = 11
POINTER_COUNT = FILES_PER_LANGUAGE * LANGUAGES   # 1089
REF_BIAS = 0x100
REF_STRIDE = 0xFF00
HEADER_SIZE = 6

# The widest symbol the client will accept, from its own range check on the
# file walk at Gw.exe 0x7ca382. A record declaring more is rejected outright
# with "Invalid text string file data at language %u string %u".
MAX_BITS = 0x10
KIND_TEXT = MAX_BITS          # kept: callers predate the bit-width reading

# Symbols below this index come from the escape table; at or above it they are
# `base - ESCAPE_COUNT + symbol`. Both from Gw.exe 0x7cb23a-0x7cb251.
ESCAPE_COUNT = 0x20

# The assert path string the escape table sits directly in front of. An
# assertion-string anchor is the most durable kind against a client update
# (studies/datwrite/FINDINGS.md measured 94.7% survival), which is why the
# table is found this way and not at a build-specific address.
TEXTDECODE_CPP = rb"P:\Code\Engine\Text\TextDecode.cpp"

# WHICH CLIENT. `pinned.py` owns that answer for every static-analysis tool in
# this directory. This module used to name an absolute path into `vault/run/`,
# which was wrong twice over: it hardcoded `C:\gd\Rurik\vault` past
# `vaultpath.py` (so a moved vault or a git worktree resolved to nothing), and
# `run/` is OUR PATCHED copy -- `pinned.py` makes the pristine one canonical
# precisely because a study of the shipped client that reads our own patch is
# reading us. The two differ in nine `.text` bytes and the DH modulus.
find_exe = pinned.find


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
    (bits, base, payload); `tiled` says the walk consumed the blob down to
    exactly the 2-byte (language, file) tail. A short walk is reported, never
    smoothed over -- it means a record is framed in a way we do not know.

    The tuple keeps the shape it had when the first element was called `kind`;
    only the meaning is corrected. See the module docstring.
    """
    recs = []
    p = 0
    end = len(blob)
    while p + HEADER_SIZE <= end:
        length, base, bits = struct.unpack_from("<HHH", blob, p)
        if length < HEADER_SIZE or p + length > end:
            break
        recs.append((bits, base, blob[p + HEADER_SIZE:p + length]))
        p += length
    return recs, blob[p:], len(blob) - p == 2


def find_escape_table(pe: PE) -> int:
    """File offset of the 32-entry symbol escape table.

    Anchored on ArenaNet's own assert path string rather than an address: the
    table is the 64 bytes ending at the last non-zero u16 before
    `P:\\Code\\Engine\\Text\\TextDecode.cpp`, which is the string the module's
    asserts name. That bounds the array on BOTH sides -- padding and a known
    string above it, its own entry 0 below -- so a wrong answer cannot merely
    "look long enough".

    Raises rather than guessing. A silently wrong table would swap characters
    without changing a single length, which is the failure mode that would
    survive every other check in this file.
    """
    hits = pe.find(TEXTDECODE_CPP)
    if len(hits) != 1:
        raise LookupError(
            f"expected exactly one {TEXTDECODE_CPP.decode()} in the image, "
            f"found {len(hits)}; do not fall back to a hardcoded address")
    off = hits[0]
    # Step back over the alignment padding. `off` then sits on the first pad
    # word, one past the last entry, so the table starts a whole table below.
    while off >= 2 and struct.unpack_from("<H", pe.data, off - 2)[0] == 0:
        off -= 2
    start = off - 2 * ESCAPE_COUNT
    if start < 0:
        raise LookupError("escape table runs off the front of the image")
    table = list(struct.unpack_from(f"<{ESCAPE_COUNT}H", pe.data, start))
    # Invariants the artifact can refute: slot 0 is the unused NUL slot (the
    # decoder branches around it), and every other slot is a distinct
    # printable-ASCII character.
    if table[0] != 0:
        raise LookupError(f"escape slot 0 is 0x{table[0]:04x}, expected 0")
    body = table[1:]
    if len(set(body)) != len(body):
        raise LookupError("escape table has duplicate entries")
    if not all(c == 0x0A or 0x20 <= c < 0x7F for c in body):
        raise LookupError("escape table holds a non-printable entry")
    return start


def escape_table(pe: PE) -> list[int]:
    """The 32 escape characters, read out of the image every time.

    Never hardcoded. These are ArenaNet's bytes and the provenance gate is
    absolute -- and a table transcribed into source would also go stale
    silently on the next client build.
    """
    return list(struct.unpack_from(f"<{ESCAPE_COUNT}H", pe.data,
                                   find_escape_table(pe)))


def is_plain(bits: int, base: int) -> bool:
    """Does the client copy this record's payload out verbatim?

    Gw.exe 0x7cb16a-0x7cb173 takes the memcpy path only when the base is zero
    AND the width is 16. Both conditions, which is why 3 records with
    `bits == 0x10` and a non-zero base are NOT plain text.
    """
    return base == 0 and bits == MAX_BITS


def unpack_symbols(bits: int, payload: bytes) -> list[int]:
    """The client's bit reader, Gw.exe 0x7cb1d5-0x7cb230.

    Symbol count is `len(payload) * 8 // bits + 1` -- the client's own
    `shl eax,3; div ecx; inc eax`, so the last symbol may read past the end.
    Past the end the accumulator takes zeroes, exactly as the client's refill
    loop does when its source pointer has reached the terminator.
    """
    if not 1 <= bits <= MAX_BITS:
        raise ValueError(f"bit width {bits} outside the client's own 1..0x10")
    count = (len(payload) * 8) // bits + 1
    mask = (1 << bits) - 1
    acc = avail = pos = 0
    out = []
    for _ in range(count):
        while avail <= 24:                    # cmp eax, 0x18 / jbe
            if pos < len(payload):
                acc |= payload[pos] << avail
            pos += 1
            avail += 8
        out.append(acc & mask)
        acc >>= bits
        avail -= bits
    return out


def map_symbols(symbols, base: int, escape) -> str:
    """Symbols to characters, Gw.exe 0x7cb232-0x7cb251."""
    return "".join(
        chr(0 if s == 0 else
            escape[s] if s < ESCAPE_COUNT
            else (base - ESCAPE_COUNT + s) & 0xFFFF)
        for s in symbols)


def record_key(pair) -> bytes:
    """The RC4 key for one record, from the 8-byte pair the caller holds.

    Gw.exe 0x7cb034: the two dwords are hashed as an 8-byte buffer repeated to
    20 bytes, and the result is the ARC4 key. `pair` is (u32, u32).
    """
    raw = struct.pack("<II", pair[0] & 0xFFFFFFFF, pair[1] & 0xFFFFFFFF)
    return arc4_hash(bytes(raw[i % len(raw)] for i in range(20)))


def decode(bits: int, base: int, payload: bytes, escape, key_pair=None):
    """One record to text, or None if it needs a key we were not given.

    This is the whole of `TextDecode.cpp`'s decoder. With `key_pair` it also
    runs the RC4 step the client runs for every non-plain record.
    """
    if is_plain(bits, base):
        try:
            return payload.decode("utf-16-le")
        except UnicodeDecodeError:
            return None
    if key_pair is None:
        return None
    plain = ARC4(record_key(key_pair)).crypt(payload)
    return map_symbols(unpack_symbols(bits, plain), base, escape)


class TextIndex:
    """string id -> text, for one language."""

    def __init__(self, exe=None, dat=DEFAULT_DAT, language=0):
        exe = exe or find_exe()[0]
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
        self.escape = escape_table(self.pe)
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

    def record(self, string_id: int):
        """(bits, base, payload) for a string id, or None if unreachable."""
        recs = self.records(string_id // RECORDS_PER_FILE)
        idx = string_id % RECORDS_PER_FILE
        return recs[idx] if idx < len(recs) else None

    def get(self, string_id: int, key_pair=None):
        """The text for a string id, or None if we could not reach it.

        Without `key_pair` this answers for plain records only, which is every
        string id any table in `Gw.exe` actually points at (MEASURED: 11,208 of
        the 11,217 ids in the skill and area tables, the other 9 belonging to
        three dead skill rows whose every stat is zero). Encrypted records
        return None rather than a plausible-looking string.
        """
        rec = self.record(string_id)
        if rec is None:
            return None
        bits, base, payload = rec
        return decode(bits, base, payload, self.escape, key_pair)

    def needs_key(self, string_id: int):
        """True if this id is RC4-encrypted, False if plain, None if absent."""
        rec = self.record(string_id)
        return None if rec is None else not is_plain(rec[0], rec[1])

    def kind_of(self, string_id: int):
        """The record's `bits` field. Named for callers that predate the
        bit-width reading; `record()` is the honest accessor."""
        rec = self.record(string_id)
        return None if rec is None else rec[0]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", default=None,
                    help="client to read; defaults to the pinned pristine "
                         "build, and the choice is printed")
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--language", type=int, default=0)
    ap.add_argument("ids", nargs="*", help="string ids to resolve")
    args = ap.parse_args()
    args.exe, why = ((args.exe, "given on the command line") if args.exe
                     else find_exe())
    print(f"client: {args.exe}\n        ({why})\n")

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

        print(f"escape table at file 0x{find_escape_table(ix.pe):06x}, "
              f"{ESCAPE_COUNT} entries, anchored on the TextDecode.cpp assert")

        # No ids given: census the language and report coverage honestly.
        widths: dict[tuple, int] = {}
        walked = 0
        for fi in range(FILES_PER_LANGUAGE):
            recs = ix.records(fi)
            if len(recs) == RECORDS_PER_FILE:
                walked += 1
            for bits, base, _p in recs:
                key = (bits, is_plain(bits, base))
                widths[key] = widths.get(key, 0) + 1
        print(f"  {walked} of {FILES_PER_LANGUAGE} files tile to exactly "
              f"{RECORDS_PER_FILE} records and a 2-byte tail")
        short = {k: v for k, v in ix.short_files.items() if v >= 0}
        undec = [k for k, v in ix.short_files.items() if v < 0]
        for k in sorted(short):
            print(f"      file {k:>2} walked short: {short[k]} records")
        if undec:
            print(f"  {len(undec)} would not decompress "
                  f"(gwdat.py's huffman table hole): {sorted(undec)}")
        print("  symbol widths:")
        total_recs = sum(widths.values())
        for k in sorted(widths, key=lambda k: -widths[k]):
            bits, plain = k
            note = "  plain UTF-16" if plain else "  RC4, key not in the record"
            print(f"      {bits:>2} bits  {widths[k]:>6}  "
                  f"{100.0 * widths[k] / total_recs:5.1f}%{note}")
        readable = sum(v for k, v in widths.items() if k[1])
        print(f"  {readable} of {total_recs} records "
              f"({100.0 * readable / total_recs:.1f}%) are readable without a key")
    return 0


if __name__ == "__main__":
    sys.exit(main())
