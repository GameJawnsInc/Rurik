#!/usr/bin/env python3
r"""Scan Gw.exe for anything that could supply a text record's RC4 key.

    python studies/textrec/tools/keyscan.py            # all three phases
    python studies/textrec/tools/keyscan.py --phase a

studies/textrec/FINDINGS.md §4 left one cheap candidate untested: that a table
in the image pairs an encrypted string id with the 64-bit key that decrypts it.
This is that test, plus two others that the varint finding suggested.

QUESTION    Is the 64-bit key for an encrypted text record anywhere in Gw.exe?

PREDICTION  If a (string_id, u64) table exists it is a RUN: one entry for a
            large share of the 72,969 encrypted slots, at a fixed stride, so
            phase A must show a stride-12 (or -16) run thousands long. If the
            key merely sits beside an id somewhere less regular, phase B must
            find at least one neighbour pair that decrypts its own record into
            something with a natural space frequency. If coded strings carrying
            keys are compiled into the image, phase C must find varint runs.

WATCH       Phase A: run length, against the skill table as a positive control
            -- the scan must rediscover a table we already know is there, or it
            proves nothing when it finds none.
            Phase B: space frequency, against a null built by decrypting the
            WRONG record with the same candidate key.
            Phase C: count of base-0x7F00 varint runs long enough for 64 bits.

Read-only on the vault client and the study archive. Nothing is launched.
"""
import argparse
import collections
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
for p in ("toolkit", "toolkit/mapdata", "toolkit/clientscan", "toolkit/authsrv"):
    sys.path.insert(0, str(ROOT / p))
import textrec                                          # noqa: E402
from gwpe import PE                                     # noqa: E402
from gwcrypto import ARC4                               # noqa: E402

MAXID = textrec.FILES_PER_LANGUAGE * textrec.RECORDS_PER_FILE

# From TextParser.cpp 0x7ccd2a-0x7ccd9b and its own assert
# "(value & ~WORD_BIT_MORE) >= WORD_VALUE_BASE".
WORD_VALUE_BASE = 0x100
WORD_BIT_MORE = 0x8000
VARINT_RADIX = 0x7F00
# 64 bits at log2(0x7F00) = 14.96 bits per word needs 5 words.
VARINT_WORDS_FOR_64 = 5

SPACE_SYMBOL = 27          # escape slot 27 is U+0020; see FINDINGS.md §1
PREFIX_BYTES = 64          # enough symbols to score, cheap enough to do 170k
MIN_SPACES = 4             # see the null in phase B's output


def varint_encode(value: int) -> list[int]:
    """The client's reader, inverted. Only used to state what it expects."""
    digits = []
    while True:
        digits.append(value % VARINT_RADIX)
        value //= VARINT_RADIX
        if not value:
            break
    digits.reverse()
    return [WORD_VALUE_BASE + d + (WORD_BIT_MORE if i < len(digits) - 1 else 0)
            for i, d in enumerate(digits)]


def load(exe):
    pe = PE(exe)
    with textrec.TextIndex(exe) as ix:
        enc, plain = {}, set()
        for fi in range(textrec.FILES_PER_LANGUAGE):
            for ri, rec in enumerate(ix.records(fi)):
                bits, base, payload = rec
                sid = fi * textrec.RECORDS_PER_FILE + ri
                if textrec.is_plain(bits, base):
                    plain.add(sid)
                else:
                    enc[sid] = rec
        escape = ix.escape
    return pe, enc, plain, escape


def aligned_hits(pe, wanted):
    """dword-aligned file offsets whose dword is an id in `wanted`."""
    out = []
    for sec in pe.sections:
        lo = sec["rawptr"] + (-sec["rawptr"]) % 4
        hi = sec["rawptr"] + sec["rawsize"]
        for off in range(lo, hi - 3, 4):
            v = struct.unpack_from("<I", pe.data, off)[0]
            if v < MAXID and v in wanted:
                out.append(off)
    return out


def phase_a(pe, enc, plain):
    print("\nPHASE A -- is there a (string_id, key) table?")
    for label, wanted in (("plain ids (POSITIVE CONTROL)", plain),
                          ("encrypted ids", set(enc))):
        hits = aligned_hits(pe, wanted)
        hs = set(hits)
        best = []
        for stride in range(4, 260, 4):
            longest = start = 0
            for o in hits:
                if o - stride in hs:
                    continue
                n = 1
                while o + n * stride in hs:
                    n += 1
                if n > longest:
                    longest, start = n, o
            best.append((longest, stride, start))
        best.sort(reverse=True)
        print(f"  {label}: {len(hits):,} aligned hits")
        for n, stride, o in best[:4]:
            rva = pe.off_to_rva(o)
            va = (rva + pe.image_base) if rva is not None else 0
            print(f"      {n:5} at stride {stride:3}  VA 0x{va:08x}")
    print("  A (string_id, u64) table would be stride 12 or 16 and thousands"
          " long.")


def score(rec, key64, escape):
    """Space frequency of the decode. Natural text runs 0.15-0.18; noise 0.008."""
    bits, base, payload = rec
    kdf = textrec.record_key((key64 & 0xFFFFFFFF, (key64 >> 32) & 0xFFFFFFFF))
    clear = ARC4(kdf).crypt(payload[:PREFIX_BYTES])
    syms = textrec.unpack_symbols(bits, clear)
    n = sum(1 for s in syms if s == SPACE_SYMBOL)
    return n, len(syms)


def phase_b(pe, enc, escape):
    print("\nPHASE B -- does a key sit beside an id anywhere at all?")
    hits = aligned_hits(pe, set(enc))
    usable = [o for o in hits
              if len(enc[struct.unpack_from("<I", pe.data, o)[0]][2]) >= 24]
    print(f"  {len(usable):,} aligned hits whose record is long enough to score")

    def dw(o):
        if 0 <= o <= len(pe.data) - 4:
            return struct.unpack_from("<I", pe.data, o)[0]
        return 0

    layouts = {
        "id,lo,hi":  lambda o: dw(o + 4) | (dw(o + 8) << 32),
        "id,hi,lo":  lambda o: dw(o + 8) | (dw(o + 4) << 32),
        "lo,hi,id":  lambda o: dw(o - 8) | (dw(o - 4) << 32),
        "hi,lo,id":  lambda o: dw(o - 4) | (dw(o - 8) << 32),
        "id,u32":    lambda o: dw(o + 4),
        "u32,id":    lambda o: dw(o - 4),
    }
    ids = [struct.unpack_from("<I", pe.data, o)[0] for o in usable]
    shifted = ids[len(ids) // 2:] + ids[:len(ids) // 2]   # the null pairing

    for name, fn in layouts.items():
        # Count DISTINCT (sid, key) pairs, not offsets. A dword value repeated
        # at 165 addresses is one test repeated, not 165 observations -- and
        # counting offsets made this layout look like a 6x excess over the null
        # until the flagged set turned out to be 31 sids and one key.
        real, null = set(), set()
        best = (0, None)
        for o, sid, wrong in zip(usable, ids, shifted):
            k = fn(o)
            n, total = score(enc[sid], k, escape)
            if n >= MIN_SPACES:
                real.add((sid, k))
            if n > best[0]:
                best = (n, (o, sid, k, total))
            m, _ = score(enc[wrong], k, escape)
            if m >= MIN_SPACES:
                null.add((wrong, k))
        print(f"  {name:11} >= {MIN_SPACES} spaces, distinct (id,key) pairs: "
              f"real {len(real):5}   null {len(null):5}   "
              f"best {best[0]} spaces")
        if best[1] and best[0] >= MIN_SPACES:
            o, sid, k, total = best[1]
            rva = pe.off_to_rva(o)
            va = (rva + pe.image_base) if rva is not None else 0
            bits, base, payload = enc[sid]
            full = ARC4(textrec.record_key(
                (k & 0xFFFFFFFF, (k >> 32) & 0xFFFFFFFF))).crypt(payload)
            text = textrec.map_symbols(
                textrec.unpack_symbols(bits, full), base, escape)
            print(f"      strongest: sid {sid} at VA 0x{va:08x}, "
                  f"{best[0]}/{total} -> {text[:70]!r}")
    print("  'real' must exceed 'null' by a lot, or this found nothing.")


def phase_c(pe):
    print("\nPHASE C -- are coded strings carrying 64-bit values in the image?")
    print(f"  a 64-bit key needs {VARINT_WORDS_FOR_64} words; "
          f"e.g. 0xDEADBEEFCAFE encodes to "
          f"{[hex(w) for w in varint_encode(0xDEADBEEFCAFE)]}")
    runs = collections.Counter()
    d = pe.data
    for sec in pe.sections:
        lo = sec["rawptr"] + (-sec["rawptr"]) % 2
        hi = sec["rawptr"] + sec["rawsize"]
        off = lo
        length = 0
        while off < hi - 1:
            w = struct.unpack_from("<H", d, off)[0]
            if (w & WORD_BIT_MORE) and (w & ~WORD_BIT_MORE) >= WORD_VALUE_BASE:
                length += 1
            else:
                if length:
                    # a terminator must itself be a legal value word
                    if w >= WORD_VALUE_BASE:
                        runs[length] += 1
                    length = 0
            off += 2
    total = sum(runs.values())
    need = VARINT_WORDS_FOR_64 - 1
    long_enough = sum(v for k, v in runs.items() if k >= need)
    print(f"  {total:,} terminated varint runs; "
          f"{long_enough:,} long enough to hold 64 bits")
    for k in sorted(runs)[:8]:
        print(f"      {k} continuation word(s): {runs[k]:,}")

    # THE FILTER HAS ALMOST NO SPECIFICITY, and saying so is the result.
    # A uniformly random u16 is a continuation word whenever bit 15 is set and
    # the low 15 bits are >= 0x100, so the per-word hit rate is about
    # 0.5 * (0x8000 - 0x100) / 0x8000 -- and a run of N is that to the Nth.
    p = 0.5 * (0x8000 - WORD_VALUE_BASE) / 0x8000
    words = sum(s["rawsize"] for s in pe.sections) // 2
    expect = words * (p ** need) * (1 - p)
    print(f"  expected from uniform noise at the same length: ~{expect:,.0f}")
    print("  So this phase found NOTHING: the observed count is of the same "
          "order as chance.\n  It cannot distinguish a compiled coded string "
          "from arbitrary bytes, and is reported\n  rather than dropped so "
          "nobody runs it again expecting an answer.")


def phase_d(exe):
    print("\nPHASE D -- is a key-bearing coded string hiding in a PLAIN record?")
    print("  Plain records we can read. If the coded strings that carry keys "
          "live in the\n  archive itself, they must be here -- nothing else in "
          "the archive is readable.")
    with textrec.TextIndex(exe) as ix:
        total = empty = ctrl = varint = 0
        for fi in range(textrec.FILES_PER_LANGUAGE):
            for bits, base, p in ix.records(fi):
                if not textrec.is_plain(bits, base):
                    continue
                total += 1
                if not p:
                    empty += 1
                    continue
                words = struct.unpack_from(f"<{len(p) // 2}H", p, 0)
                if any(0 < w < 0x20 for w in words):
                    ctrl += 1
                run = 0
                for w in words:
                    if (w & WORD_BIT_MORE) and (w & ~WORD_BIT_MORE) >= WORD_VALUE_BASE:
                        run += 1
                    else:
                        if run >= 3 and w >= WORD_VALUE_BASE:
                            varint += 1
                        run = 0
    print(f"  {total:,} plain records ({empty:,} empty)")
    print(f"      with a control word below 0x20: {ctrl}  "
          f"(embedded newlines in ordinary prose)")
    print(f"      with a >=3-word varint run:     {varint}")
    print("  Zero means every plain record is literal text, and no key rides "
          "in the archive.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--exe", default=textrec.DEFAULT_EXE)
    ap.add_argument("--phase", default="abcd")
    args = ap.parse_args()

    pe, enc, plain, escape = load(args.exe)
    print(f"{len(enc):,} encrypted ids, {len(plain):,} plain, "
          f"id space 0..{MAXID - 1}")
    print(f"  {100 * len(enc) / MAXID:.0f}% of the id range is encrypted, so "
          f"'this dword is an encrypted id' is weak on its own -- every phase "
          f"below is scored on decoding, not membership.")
    if "a" in args.phase:
        phase_a(pe, enc, plain)
    if "b" in args.phase:
        phase_b(pe, enc, escape)
    if "c" in args.phase:
        phase_c(pe)
    if "d" in args.phase:
        phase_d(args.exe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
