#!/usr/bin/env python3
"""A7b -- the BITSTREAM WRITER for Gw.dat compression code 8. This one emits bytes.

    python toolkit/mapdata/gwenc.py                        # re-emit the three anchors
    python toolkit/mapdata/gwenc.py --reemit --rows 11196  # retail's row, byte for byte
    python toolkit/mapdata/gwenc.py --encode --rows 11196 --q 8
    python toolkit/mapdata/gwenc.py --encode --rows 11196 --sweep

WHAT THIS IS, AND WHAT THE PREVIOUS TWO RUNGS DELIBERATELY WERE NOT. `gwentropy.py`
(A6) counts bits and writes none. `gwmatch.py` (A7a) produces tokens and a block
partition and costs them, and its own docstring says *"the moment this file emits a bit
it has left the rung"*. This is the rung. Nothing here searches for a match or chooses a
block boundary; it takes a `gwentropy.StreamTrace` -- from either source -- and turns it
into the bytes a stored compression-8 row is made of.

It has TWO entry points and they are not equally strong evidence:

  `reemit(data)`   trace an EXISTING retail row and emit the stream that trace
                   describes. When the output is byte-identical to the row on disk and
                   its crc32 equals the MFT's own recorded value, that is the ONLY
                   check in this arc that does not depend on `gwdat.py` being a correct
                   decoder. A wrong bit order, a wrong canonical assignment or a wrong
                   meta-token encoding cannot accidentally reproduce ArenaNet's bytes.
  `encode(payload)` compress a payload of our own: `gwmatch.build_stream` for the
                   tokens and the partition, this writer for the bits. Its check is a
                   round trip through `gwdat.decompress`, which proves AGREEMENT WITH
                   OUR DECODER, NOT CORRECTNESS -- `gwdat.py:81-84` records that the
                   diff against `xentax.cpp` has never been run and that we have a known
                   divergence from both upstream lineages on the zero-length code. The
                   retail client is the only oracle and that is rung A8.

DERIVATION AND LICENCE. `PLAN.md` §6.1 carries this module's row, added 2026-08-18
BEFORE the module existed -- the obligation `studies/archivewrite/FINDINGS.md` §2.2
states in those words, and the third rung in a row to meet it. What is inverted from
`gwdat.py` (which derives it from GuildWarsMapBrowser's `SourceFiles/xentax.cpp`,
Copyright (c) 2023 Jonathan Bjorn Greve) is the FORMAT: the meta-token bands, the
canonical code assignment, and the word/bit order. Every constant is IMPORTED from
`gwdat` or `gwentropy`; nothing is re-transcribed. What is ours is only the direction --
all five mirrored lineages declare decode only, so there is no writer upstream to copy.
Worth saying plainly, because the headline result below is byte-identical re-emission of
ArenaNet's own rows: that result is evidence we hold GWMB'S RECOVERY OF THE FORMAT
correctly. `THIRD-PARTY-NOTICES.md`'s GWMB entry names this file.

--------------------------------------------------------------------------------
THE FORMAT, IN THE WRITE DIRECTION. Four things had to be inverted, and each is
stated here with the decoder line it was inverted from.

(a) BIT ORDER -- `gwdat.BitReader.__init__` loads 32-bit words with `'<I'` and `peek`
    takes them from the TOP of `buf1`. So: bits are MSB-FIRST inside each 32-bit word,
    words are in file order, and each word is stored LITTLE-ENDIAN. Stream bit 0 is bit
    7 of `data[3]`; stream bit 31 is bit 0 of `data[0]`. `BitWriter` below is the whole
    inverse: accumulate MSB-first, flush completed words with `'<I'`.

(b) THE PROLOGUE -- `decompress` does `consume(4)` then `read(4)`, i.e. the high and low
    nibbles of `data[3]`. Retail emits `0000` then `0010`, so `data[3] == 0x02` and the
    minimum match is `first_four + LENGTH_BASE[0] + 1 == 3`. This writer takes both from
    the trace rather than hardcoding them, so a stream with a different header re-emits
    correctly and a census of the population remains a measurement rather than an
    assumption.

(c) THE META TOKENS -- `build_table` picks the first `CODE_LENGTH_THRESHOLDS` row whose
    `thr <= peek(32)`, spends `row_index + 3` bits and lands on `last_index - offset`.
    `META_EMIT` below inverts that to `index -> (bit_count, bit_pattern)`. It is built by
    an INDEPENDENT walk of the same threshold table rather than by reading
    `gwentropy.META_COST`, and `_check_meta_emit()` requires the two to agree on all 256
    widths -- two derivations from one borrowed table, which is corroboration for the
    inversion and NOT independence from the table itself (the standing §2.2 risk).

(d) CANONICAL CODES -- `build_table` starts `next_bits` at 1, walks each length's
    symbols in ascending index order counting DOWN, then doubles-and-adds-one. That is
    `gwentropy.canonical_codes`, imported, not re-implemented.

--------------------------------------------------------------------------------
THE EPILOGUE, WHICH IS WHERE A WRITER SILENTLY LOSES BYTES.

`BitReader` keeps `buf1` permanently full: `consume` refills from `buf2`, which refills
from `data` a whole 32-bit word at a time. So after the LAST token's `consume` the reader
must still be able to load 32 bits beyond the last consumed bit. Writing that as the
condition on `len(data)`: after `C` consumed bits the reader's `idx` reaches
`4 * ceil((C + 32) / 32)`, and anything shorter than that raises.

TWO MEASURED CONSEQUENCES, and the first one corrects the obvious way to state this.
`BitReader` reads over the WHOLE stored row -- it has no idea the last four bytes are the
uncompressed size -- so **the u32 trailer doubles as one word of look-ahead.** Drop the
sentinel word entirely and the payload still decodes IDENTICALLY (measured: rows 11196,
13738, 8282, zero bytes lost). Drop one word beyond that and the decode **TRUNCATES
SILENTLY**: `Eof` fires inside `next_code` after the symbol was found and before `out` is
appended, and `decompress` swallows it. Measured, same three rows: 1,514,850 of
1,514,855 B; 29,798 of 29,802; 2,150,663 of 2,150,664. No raise, no short-read signal --
and the MFT's crc is over the STORED bytes, so such a row passes every checksum rule an
archive applies. `test_gwenc.py` §6(d) keeps both halves as controls.

So, given a final consumed-bit count `C` (prologue included):

    words = ceil((C + 32) / 32)             # >= 2 always, since C >= 8
    pad   = (words - 1) * 32 - C            # == (-C) mod 32, in 0..31
    emit `pad` ZERO bits                    # land on a 32-bit boundary
    emit the 32-bit word 0x80010008         # MSB-first == LE bytes 08 00 01 80
    append struct.pack('<I', uncompressed_size)     # NOT part of the bitstream
    stored = words * 4 + 4                  # == gwentropy.framing_bytes(C)

TWO MEASURED FACTS ABOUT THE TAIL WORD, because a hardcoded constant deserves both.
It is the reader's mandatory 32-bit look-ahead, and `gwdat` NEVER CONSUMES IT: replace
it with `0xDEADBEEF` and the payload decodes identically; omit it and the payload still
decodes identically (the u32 trailer slides into the slot). So our decoder does not need
it. We emit it anyway, and `TAIL_WORD` is not a tunable: every retail comp-8 row sampled
carries exactly `0x80010008` (a widened census puts it at 258,708 of 258,708 rows across
four archives and three client builds), the retail client is the only oracle that has not
been asked, and 4 bytes is not worth the risk. What the value MEANS is **NOT FOUND** --
it is not a decodable block header, since its leading 16 bits would declare
`symbol_count = 0x8001`. What the measurement does establish is the writer's SHAPE:
the word is invariant across all 32 pad widths, so retail flushes its partial word with
zeros and then writes one literal sentinel -- it is not a shifted residue of a register.

Pad bits are all ZERO, measured across all 32 pad widths on real rows, and writing them
as ones changes the bytes while leaving the payload decodable -- so they are genuinely
free and retail genuinely chose zero.

--------------------------------------------------------------------------------
THE TRAP THAT COST REAL TIME, AND IT IS A ONE-WORD BUG.

`gwmatch._fit_table` costs its tables with `optimal=True` (the meta-coder DP).
**Retail's own table encoder is longest-run GREEDY** -- A6 measured that bit-exact on
2,194 of 2,194 tables, and it is why byte-identical re-emission is possible at all. The
two differ by a handful of bits per row. A writer that hardcodes either one silently
disagrees with the other's size model, and on a row with 68 B of reservation slack that
class of drift is exactly what overflows a reservation. So `emit_stream` TAKES THE FLAG
and the caller must pass the one the planner used:

    reemit(data)                      -> optimal=False, because retail is greedy
    encode(payload, optimal=True)     -> optimal=True, matching gwmatch's default

`test_gwenc.py` §4 checks that the writer's own byte count equals the planner's
PREDICTED byte count to the byte, which is the arm that catches the mismatch.

--------------------------------------------------------------------------------
THE ENVELOPE, AND THE ONE GAP LEFT OPEN ON PURPOSE.

Every table this writer emits is a shape retail's own archive or the A8 client run
attests -- `gwentropy.authoring_table` is where that is decided and it carries the
census. `studies/archivewrite/FINDINGS.md` §13.5 named five ways our encoder left
retail's envelope; four are closed here (A, B, the distance half of C, and D -- see
`encode`'s refusal of a zero-byte payload). **E is ACCEPTED, not fixed, and this is the
reason:** we emit a handful of meta indices that sit in the 3-bit-prefix catch-all band,
160 of whose 256 indices retail was never sampled emitting. The band structure is not a
choice we make -- `_build_meta_emit` asserts the bands TILE, so every index is reachable
by exactly one prefix and a "safe" index is not a different mechanism, only a different
run length. Avoiding them would mean rejecting the meta plan the DP chose and re-planning
tables around a list of preferred tokens, which distorts the partition DP's own costs
(the plan cost feeds `_block_cost`, which chooses block boundaries) for no attested
benefit. A8 read 218 of our tables without complaint. If a future client run ever refuses
one, the fix is a constrained `meta_plan`, not a change here.

--------------------------------------------------------------------------------
WHAT THIS MODULE DOES NOT DO, DELIBERATELY.

It has no `datwrite` verb, it opens no archive for writing and it touches no real file.
A7b produces bytes in memory. Deploying them into an archive is a later rung with its
own safety gates, and `FINDINGS.md` §5 is about why. Note the failure mode that makes
that ordering non-negotiable: a writer that miscounts `C` downward does not raise, it
ships a row that decodes a few bytes short and passes every checksum rule, because the
entry CRC is taken over the STORED bytes. Any future deploy path must decode-and-compare
before it writes, which is what `encode(..., verify=True)` does here by default.
"""
import argparse
import os
import struct
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gwdat                                               # noqa: E402
import gwentropy as G                                      # noqa: E402
import gwmatch as MM                                       # noqa: E402
from archive import Archive, DEFAULT_DAT                   # noqa: E402

M32 = 0xFFFFFFFF

# The reader's mandatory look-ahead word. NOT a tunable -- see the module docstring.
TAIL_WORD = 0x80010008


# --------------------------------------------------------------------------
# (a) the bit order, inverted from gwdat.BitReader
# --------------------------------------------------------------------------

class BitWriter:
    """MSB-first into a 32-bit register, flushed as little-endian words.

    The exact inverse of `gwdat.BitReader`: it loads `struct.unpack('<I')` words and
    `peek(n)` returns the top `n` bits of the current one, so stream bit 0 is bit 7 of
    `data[3]`. `total` is the consumed-bit count `C` the framing rule needs.

    `write` refuses a value that does not fit its field. That is not defensive
    politeness: `base | extra` in the decoder is only `base + extra` while the extra
    value stays inside its own width, and ArenaNet's own writer asserts the same
    precondition (`CmpIo.cpp:139 !(value & ~((1 << bitCount) - 1))`).
    """
    __slots__ = ('_words', '_acc', '_n', 'total')

    def __init__(self):
        self._words = []
        self._acc = 0
        self._n = 0
        self.total = 0

    def write(self, value, count):
        if count == 0:
            return
        if not 0 < count <= 32:
            raise ValueError(f"field width {count} outside 1..32")
        if not 0 <= value < (1 << count):
            raise ValueError(f"value {value} does not fit {count} bits")
        acc = (self._acc << count) | value
        n = self._n + count
        self.total += count
        while n >= 32:
            n -= 32
            self._words.append((acc >> n) & M32)
            acc &= (1 << n) - 1
        self._acc = acc
        self._n = n

    @property
    def pending(self):
        """Bits sitting in the register, not yet in a whole word. 0..31."""
        return self._n

    def bytes_so_far(self):
        """The whole words flushed so far. Never includes a partial word."""
        return struct.pack(f'<{len(self._words)}I', *self._words)


# --------------------------------------------------------------------------
# (c) the meta-token emit table, inverted from build_table's band walk
# --------------------------------------------------------------------------

def _build_meta_emit():
    """index 0..255 -> (bit_count, bit_pattern) that `build_table`'s walk decodes back.

    `build_table` reads `b = peek(32)`, takes the FIRST `CODE_LENGTH_THRESHOLDS` row with
    `thr <= b`, spends `row_index + 3` bits and computes
    `offset = (b - thr) >> (32 - bit_count)`, landing on `last_index - offset`. So to
    emit `index` from band `i` the top `bit_count` bits must be
    `(thr >> (32 - bit_count)) + offset` -- which is a plain integer add only because
    every threshold is aligned to its own band's width. That alignment is ASSERTED here,
    not assumed: if it failed, the bands would not tile and the emitted prefix could land
    in the wrong band.
    """
    out = [None] * 256
    hi = 1 << 32
    for i, (thr, last_index) in enumerate(gwdat.CODE_LENGTH_THRESHOLDS):
        bit_count = i + 3
        width = 1 << (32 - bit_count)
        if thr % width:
            raise ValueError(f"threshold band {i} ({thr:#x}) is not aligned to its "
                             f"{bit_count}-bit prefix; the bands would not tile")
        count = (hi - thr) >> (32 - bit_count)
        base = thr >> (32 - bit_count)
        for off in range(count):
            idx = last_index - off
            if not 0 <= idx < 256:
                raise ValueError(f"band {i} runs off the alphabet at index {idx}")
            if out[idx] is not None:
                raise ValueError(f"band {i} overlaps an earlier band at index {idx}")
            out[idx] = (bit_count, base + off)
        hi = thr
    if any(o is None for o in out):
        raise ValueError("the threshold table does not cover all 256 meta symbols")
    return out


META_EMIT = _build_meta_emit()


def _check_meta_emit():
    """The emit widths must equal `gwentropy`'s independently derived cost widths.

    Two walks of the same borrowed table. Agreement is corroboration for the INVERSION
    and says nothing about the table itself -- a shared error in
    `CODE_LENGTH_THRESHOLDS` / `CODE_LENGTH_SYMBOLS` is invisible to it, which is the
    standing `gwdat.py:81-84` risk. Byte-identical re-emission is what covers that.
    """
    bad = [i for i in range(256) if META_EMIT[i][0] != G.META_COST[i]]
    if bad:
        raise ValueError(f"emit widths disagree with gwentropy.META_COST at {bad[:8]}")


_check_meta_emit()


# --------------------------------------------------------------------------
# the writer
# --------------------------------------------------------------------------

def _emit_table(w, lens, declared, zero_len, optimal):
    """One Huffman table: the 16-bit symbol count then the meta tokens describing it.

    `gwentropy.retail_arrays` recovers the `(lens, present, n)` description a decoded
    table must have been transmitted as, and it is the same call for our own tables and
    for retail's -- the all-skip case (`zero_len` with `declared >= 2`, where the symbol
    was installed by `build_table`'s `total == 0` fallback rather than assigned) is the
    one that does not round-trip naively, and both sources reach it the same way.

    WHAT THE ALL-SKIP CASE CANNOT DO, because a caller reaching for it to satisfy a
    declared-count floor would corrupt the stream silently: the fallback installs
    `symbol_count - 1` AND NO OTHER INDEX (`gwdat.py:265-267`). So a lone symbol at
    index `s` can take this shape only by declaring exactly `s + 1`; declaring anything
    larger decodes to a different symbol, which for a distance table means a different
    `DISTANCE_BASE` and a payload of garbage. Lifting such a table to a floor therefore
    costs a real code and a phantom partner -- `gwentropy._phantom_pair` -- and there is
    no cheaper legal route. `declared > max(lens) + 1` is fine for an ORDINARY table
    (retail declares 285 with far fewer present on nearly every row); the meta-coder
    describes the absent tail with skip runs and nothing here needs to know.

    Returns the meta_plan's own predicted bit count, so the caller can compare it with
    what the writer actually emitted.
    """
    lens_l, pres_l, n = G.retail_arrays(lens, declared, zero_len)
    bits, plan = G.meta_plan(lens_l, pres_l, n, optimal=optimal)
    w.write(n, G.SYMBOL_COUNT_BITS)
    for repeat, length, _present in plan:
        bit_count, pattern = META_EMIT[G.token_index(repeat, length)]
        w.write(pattern, bit_count)
    return bits


def emit_stream(st, optimal=True):
    """`emit_stream_counted` without the bit count. -> bytes."""
    return emit_stream_counted(st, optimal=optimal)[0]


def emit_stream_counted(st, optimal=True, tail_word=None, pad_bit=0):
    """`gwentropy.StreamTrace` -> (stored bytes, consumed bits BEFORE the epilogue).

    The bit count is returned because the byte count is a 32-bit-quantised view of it:
    a writer 31 bits off the cost model still lands on the same stored size. `C` against
    `st.final_bitpos` is the sharp form of that comparison and the test uses it.

    Works on a trace of retail's stream and on one `gwmatch.build_stream` produced; the
    field names are the same by design (`gwmatch`'s docstring, "why the token container
    is gwentropy's").

    `optimal` selects the META-CODER plan and MUST match whatever costed the stream:
    False (longest-run greedy) is what retail's own table encoder does and is what
    byte-identical re-emission needs; True is `gwmatch`'s default. Getting it wrong does
    not corrupt the stream -- it just makes the bytes differ from retail's and the size
    differ from the planner's prediction, which is why §4 of the test checks the second.

    `tail_word` and `pad_bit` exist ONLY so `test_gwenc.py` §6 can break the epilogue on
    purpose and watch byte-identity go red. A caller with a real archive in mind must
    never pass them; the defaults are what every retail row carries.
    """
    w = BitWriter()
    w.write(st.lead_bits, 4)
    w.write(st.first_four, 4)

    LEB = gwdat.LENGTH_EXTRA_BITS
    DEB = gwdat.DISTANCE_EXTRA_BITS

    for b in st.blocks:
        if b.lit_syms is None:
            raise ValueError(f"block {b.index} has no token array; "
                             "trace with keep_streams=True")
        _emit_table(w, b.lit_lens, b.lit_symbol_count, b.lit_zero, optimal)
        _emit_table(w, b.dist_lens, b.dist_symbol_count, b.dist_zero, optimal)
        w.write(b.size_code, 4)

        lit_codes = G.canonical_codes(b.lit_lens)
        dist_codes = G.canonical_codes(b.dist_lens)
        dist_syms = b.dist_syms
        extra_vals = b.extra_vals
        di = ei = 0
        for code in b.lit_syms:
            c, L = lit_codes[code]
            if L:
                w.write(c, L)
            if code < 0x100:
                continue
            k = code - 0x100
            nb = LEB[k]
            if nb:
                w.write(extra_vals[ei], nb)
            dsym = dist_syms[di]
            dc, dL = dist_codes[dsym]
            if dL:
                w.write(dc, dL)
            nb = DEB[dsym]
            if nb:
                w.write(extra_vals[ei + 1], nb)
            di += 1
            ei += 2
        if di != len(dist_syms) or ei != len(extra_vals):
            raise ValueError(f"block {b.index}: {len(dist_syms) - di} distance symbols "
                             f"and {len(extra_vals) - ei} extra values were never "
                             "emitted -- the token arrays are out of step")

    consumed = w.total
    return finish(w, st.out_size, tail_word=tail_word, pad_bit=pad_bit), consumed


def finish(w, out_size, tail_word=None, pad_bit=0):
    """Pad to a word, write the look-ahead sentinel, append the u32 size. -> bytes.

    The whole epilogue rule, in one place, so that nothing else in the repo has to know
    it. See the module docstring for why each of the three parts is there and which of
    them `gwdat` actually needs -- measured: it needs the pad (for length) and it does
    NOT need the sentinel at all, because the u32 trailer covers that word. We emit it
    because every retail row has it and the client has not been asked.
    """
    if tail_word is None:
        tail_word = TAIL_WORD
    consumed = w.total
    words = max(2, -(-(consumed + 32) // 32))
    pad = (words - 1) * 32 - consumed
    fill = M32 if pad_bit else 0
    while pad:
        take = pad if pad < 32 else 32
        w.write(fill >> (32 - take), take)
        pad -= take
    w.write(tail_word, 32)
    if w.pending:
        raise ValueError(f"{w.pending} bits left in the register after the epilogue")
    out = w.bytes_so_far() + struct.pack('<I', out_size)
    expect = G.framing_bytes(consumed)
    if len(out) != expect:
        raise ValueError(f"emitted {len(out)} B against the framing rule's {expect} B "
                         f"for {consumed} consumed bits")
    return out


# --------------------------------------------------------------------------
# the two entry points
# --------------------------------------------------------------------------

def _refuse_zero_block(payload):
    """A zero-byte payload has no blocks, and a zero-block row is not this format.

    `gwmatch._Emitter.finish` never appends an empty granule (`gwmatch.py:365-369`) and
    `plan_partition` returns `[]` for no granules (`gwmatch.py:562-564`), so `encode(b"")`
    would emit the 8-bit prologue and the epilogue and nothing between them: 12 bytes,
    which `gwdat.decompress` reads back as `(b"", 0)`. NO RETAIL COMP-8 ROW IS SHAPED
    THAT WAY -- the smallest in `dat_study/Gw.dat` is 56 B and holds a block -- so it is
    a stream whose acceptance nothing witnesses, and it is the whole of
    `studies/archivewrite/FINDINGS.md` §13.5's gap D.

    Refused HERE rather than caught downstream because downstream does not catch it:
    `datwrite.declaration_fault(encode(b""), 8, expect=b"")` returns None today. Its
    zero-length guard tests the STORED bytes (12, so it passes) and its mandatory-expect
    guard tests `expect is None` (`b""` passes), so those bytes can reach an archive.
    A zero-byte file is STORED, not compressed; that decision belongs to the caller.
    """
    if not payload:
        raise ValueError(
            "refusing to compress a zero-byte payload: it produces a stream with NO "
            "BLOCKS (12 B of prologue and epilogue), a shape no retail compression-8 "
            "row has -- the smallest is 56 B and holds a block. Store a zero-byte "
            "file uncompressed instead.")


def reemit(data, out_size=None, tail_word=None, pad_bit=0, optimal=False):
    """Re-emit an EXISTING stored row from its own trace. -> (bytes, trace, bits).

    THE STRONGEST CHECK IN THIS ARC, and the only one that does not assume `gwdat` is a
    correct decoder: if these bytes equal the row on disk, then our bit order, our
    canonical assignment, our meta-token encoding, our extra-bit widths and our framing
    are ArenaNet's, because a valid-but-different parse could not reproduce their bytes.

    The `optimal=False` default is not a tuning choice. Retail's table encoder is
    longest-run greedy (A6, bit-exact on 2,194 of 2,194 tables) and the DP beats it on
    ~1.2% of tables, so the DP would emit a smaller, still-decodable, DIFFERENT stream.
    The keyword is here so `test_gwenc.py` §6 can flip it and watch byte-identity go red;
    that control is what makes "retail is greedy" load-bearing rather than decorative.
    """
    _payload, st = G.trace(data, out_size=out_size, keep_streams=True)
    out, bits = emit_stream_counted(st, optimal=optimal, tail_word=tail_word,
                                    pad_bit=pad_bit)
    return out, st, bits


def encode(payload, quality=MM.DEFAULT_Q, optimal=True, uniform=None, units=None,
           verify=True):
    """Compress a payload into stored compression-8 bytes. -> bytes.

    Tokens and block partition from `gwmatch.build_stream`; bits from this module. With
    `verify=True` (the default) the result is decoded by `gwdat.decompress` and compared
    to the input before it is returned.

    That default is deliberate and the reason is a measured failure mode, not caution:
    a stream whose framing is one word short does NOT raise -- it decodes a few bytes
    short, silently, and still passes every checksum rule an archive applies, because the
    MFT's crc is over the stored bytes. `verify=False` exists for sweeps that are only
    after a size.

    Round-tripping through `gwdat` proves AGREEMENT WITH OUR DECODER, NOT CORRECTNESS.

    A zero-byte payload is REFUSED -- `_refuse_zero_block` says why.
    """
    payload = bytes(payload)
    _refuse_zero_block(payload)
    st, cfg = MM.build_stream(payload, q=quality, optimal=optimal, uniform=uniform,
                              units=units)
    data = emit_stream(st, optimal=optimal)
    if verify:
        back, declared = gwdat.decompress(data)
        if declared != len(payload):
            raise ValueError(f"trailer declares {declared} B, payload is {len(payload)}")
        if back != payload:
            raise ValueError(f"round trip FAILED: {len(back)} B back from "
                             f"{len(payload)} B in"
                             + ("" if len(back) != len(payload) else ", same length"))
    return data


def encode_report(payload, quality=MM.DEFAULT_Q, optimal=True, uniform=None, units=None,
                  verify=True):
    """`encode` plus the planner's own numbers, for callers that want both. -> dict.

    `predicted` is `gwmatch`/`gwentropy`'s cost model; `stored` is `len(bytes)`. Two
    independent computations of one quantity -- a cost model and a byte count -- so a
    disagreement means one of them is wrong. `test_gwenc.py` §4 is that comparison.

    Refuses a zero-byte payload for the same reason `encode` does.
    """
    payload = bytes(payload)
    _refuse_zero_block(payload)
    st, cfg = MM.build_stream(payload, q=quality, optimal=optimal, uniform=uniform,
                              units=units)
    data = emit_stream(st, optimal=optimal)
    ok = None
    if verify:
        back, _declared = gwdat.decompress(data)
        ok = back == payload
    summary = MM.summarize(st, cfg)
    summary.update({
        "bytes": data,
        "stored": len(data),
        "predicted": G.framing_bytes(st.final_bitpos),
        "predicted_bits": st.final_bitpos,
        "round_trip": ok,
        "crc32": zlib.crc32(data) & M32,
    })
    return summary


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

ANCHORS = [11196, 13738, 11141]
ANCHOR = 11196
ANCHOR_STORED = 1029564
ANCHOR_RESERVATION = 1029632            # TRAILER-INCLUSIVE, as every byte here is


def _fmt(n):
    return f"{n:,}"


def do_reemit(ar, rows):
    print(f"{'row':>7} {'stored B':>12} {'emitted B':>12} {'identical':>10} "
          f"{'crc == MFT':>11} {'secs':>7}")
    bad = []
    for row in rows:
        e = ar.row(row)
        if e.compression != 8:
            raise ValueError(f"row {row} is compression {e.compression}, not 8")
        data = ar.raw(e)
        t0 = time.perf_counter()
        out, _st, _bits = reemit(data)
        dt = time.perf_counter() - t0
        same = out == data
        crc_ok = (zlib.crc32(out) & M32) == e.crc
        if not (same and crc_ok):
            bad.append(row)
        print(f"{row:>7} {e.size:>12,} {len(out):>12,} {str(same):>10} "
              f"{str(crc_ok):>11} {dt:>6.1f}s")
    print(f"\nbyte-identical: {len(rows) - len(bad)}/{len(rows)}"
          + (f"  FAILED {bad}" if bad else ""))
    return bad


def do_encode(ar, rows, qs, optimal=True, uniform=None):
    bad = []
    for row in rows:
        e = ar.row(row)
        payload = ar.read(e)
        reservation = ANCHOR_RESERVATION if row == ANCHOR else None
        print(f"\nrow {row}: retail stored {_fmt(e.size)} B -> payload "
              f"{_fmt(len(payload))} B"
              + (f", reservation {_fmt(reservation)} B" if reservation else ""))
        print(f"{'dial':<4} {'ours B':>12} {'predicted':>12} {'delta':>6} "
              f"{'vs retail':>10} " + (f"{'bar':>6} " if reservation else "")
              + f"{'blk':>5} {'round trip':>11} {'secs':>7}")
        for qi in qs:
            t0 = time.perf_counter()
            r = encode_report(payload, quality=qi, optimal=optimal, uniform=uniform)
            dt = time.perf_counter() - t0
            delta = r["stored"] - r["predicted"]
            if delta or r["round_trip"] is False:
                bad.append((row, qi))
            barcol = ""
            if reservation:
                barcol = f" {'FITS' if r['stored'] <= reservation else 'OVER':>6}"
            print(f"q{r['quality']:<3} {r['stored']:>12,} {r['predicted']:>12,} "
                  f"{delta:>+6} {r['stored'] - e.size:>+10,}{barcol} "
                  f"{r['blocks']:>5} {str(r['round_trip']):>11} {dt:>6.1f}s")
    if bad:
        print(f"\nFAILED (size closure or round trip): {bad}")
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--rows", type=int, nargs="*", default=None)
    ap.add_argument("--reemit", action="store_true",
                    help="re-emit retail's own rows and diff against the disk bytes")
    ap.add_argument("--encode", action="store_true",
                    help="compress the row's payload with our own encoder")
    ap.add_argument("--q", type=int, nargs="*", default=None)
    ap.add_argument("--sweep", action="store_true", help="the whole quality curve")
    ap.add_argument("--uniform", type=int, default=None)
    ap.add_argument("--greedy-meta", action="store_true",
                    help="plan tables with longest-run greedy (retail's own algorithm)")
    args = ap.parse_args()

    rows = args.rows if args.rows else ANCHORS
    qs = args.q if args.q else (sorted(MM.QUALITY) if args.sweep else [MM.DEFAULT_Q])
    optimal = not args.greedy_meta
    do_both = not (args.reemit or args.encode)

    print(f"A7b bitstream writer -- all bytes TRAILER-INCLUSIVE, tail word "
          f"{TAIL_WORD:#010x}")
    bad = []
    with Archive(args.dat) as ar:
        if args.reemit or do_both:
            print("\nRE-EMISSION of retail's own rows (meta plan: greedy, retail's own)")
            bad += do_reemit(ar, rows)
        if args.encode or do_both:
            print(f"\nOUR OWN ENCODER (meta plan: "
                  f"{'greedy' if args.greedy_meta else 'optimal DP'}, partition "
                  f"{'uniform ' + str(args.uniform) if args.uniform else 'DP'})")
            bad += do_encode(ar, rows, qs, optimal=optimal, uniform=args.uniform)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
