#!/usr/bin/env python3
"""A6 -- the entropy accountant for Gw.dat compression code 8. COUNTS BITS, WRITES NONE.

    python toolkit/mapdata/gwentropy.py                 # the three anchors
    python toolkit/mapdata/gwentropy.py --witness       # + S3's 26-row witness set
    python toolkit/mapdata/gwentropy.py --rows 11196    # named rows
    python toolkit/mapdata/gwentropy.py --rows 11196 --literal-only

WHAT THIS IS FOR. `studies/archivewrite/FINDINGS.md` §3 puts rung A7 -- a real
compression-8 encoder -- at 2-3 sessions, and its bar is not "produce a valid stream"
but "MATCH ArenaNet's own compressor on ArenaNet's own data to within 64 bytes", because
row 11196 stores 1,029,564 B inside a 1,029,632 B reservation. A7 has two independent
risks and the scouts kept merging them:

    (i)  can our Huffman + meta-table layer match ArenaNet's, GIVEN tokens we did not
         have to produce?
    (ii) can our LZ77 matcher match zlib's?

This module answers (i) EXACTLY and says nothing whatever about (ii). It instruments a
decode to recover RETAIL'S OWN token stream, then re-costs that identical sequence under
a from-scratch canonical Huffman plus this format's own meta-encoding, keeping RETAIL'S
OWN BLOCK PARTITION so that the only thing varying between the two totals is the entropy
layer. If the re-cost comes out far above retail's stored size, A7 is dead before a
matcher is written.

THERE IS NO ENCODER HERE AND NO BITSTREAM WRITER. Every "cost" below is an integer count
of bits that a conforming stream would have to contain. Nothing is emitted, nothing is
packed, and `gwdat.py` is not modified, hooked or monkey-patched -- see below.

DERIVATION AND LICENCE. `PLAN.md` §6.1 carries this module's row, added 2026-08-18
BEFORE the module existed. What is borrowed is the pair of meta-coder constant tables
`CODE_LENGTH_THRESHOLDS` and `CODE_LENGTH_SYMBOLS`, from GuildWarsMapBrowser's
`SourceFiles/xentax.cpp` (Copyright (c) 2023 Jonathan Bjorn Greve,
https://github.com/Jonathan-Greve/GuildWarsMapBrowser), reached through this repo's own
re-derivation in `toolkit/mapdata/gwdat.py`. This module IMPORTS them from `gwdat` and
re-transcribes nothing; `THIRD-PARTY-NOTICES.md`'s GWMB entry names this file. What is
NOT borrowed is the cost model: all five mirrored lineages (GWMB `xentax.cpp`,
gw-preservation `binutil/huffman.go`, Fournux `gw_dat_decompress.rs`, OpenTyria
`FaCompress.c`, Headquarter `docs/compress.c`) declare DECODE ONLY -- NOT FOUND, nobody
upstream wrote the inverse -- so reading these tables in the encode direction is ours.

WHY THE BLOCK LOOP IS DUPLICATED RATHER THAN HOOKED. `gwdat.py` is imported by twelve
files in `toolkit/`, including `archive.py` and everything above it on the server path. A
kwarg, a callback or a module-global on `decompress` would put tracing machinery in that
dependency chain forever to serve one research rung. So `trace()` re-runs the ~30-line
block loop of `gwdat.decompress` with counters added, and IMPORTS `BitReader`,
`build_table`, `HuffTable`, `Eof` and all six constant tables unchanged. Per-symbol code
lengths are RECONSTRUCTED from the `HuffTable` object `build_table` returned
(`table_lengths`); `build_table` is not re-implemented.

Duplication has an obvious failure mode -- the copy drifts from the referee and its
tokens become fiction -- so `test_gwentropy.py` closes it: `trace(data)[0]` must equal
`gwdat.decompress(data)[0]` byte for byte, and `replay()` must rebuild the same payload
from the recorded token arrays alone, with no Huffman table and no bit reader in the
loop. THE `gwdat.py` DIFF MUST BE EMPTY for that comparison to mean anything.

WHAT CAN REFUTE THE NUMBERS BELOW. Five closures, and each names what its failure would
mean. `test_gwentropy.py` runs all five over every table of every block:

  C1  segment accounting closes to zero: header + tables + size fields + tokens + extras
      == the measured final bit position. The token term is MODELLED (sum of length x
      count over the reconstructed lengths); the table bits and the final position are
      MEASURED from the reader. They are allowed to disagree and do not. A version that
      read the token bits off `bit_end - bit_after_size` could not fail and must not be
      written.
  C1b the reader identity `final_bitpos + 32 + final_avail == 8 * final_idx`, with
      `final_idx == len(data) - 4`. Failure means the decode stopped early and the
      recorded stream is not the whole stream. (Note the reader permanently holds 32
      look-ahead bits it never consumes, so "within one word" is the WRONG form of this
      check -- measured tail slack on real rows is 33..63 bits.)
  C2  byte-for-byte reproduction, twice: tracer vs `gwdat.decompress`, and `replay` vs
      `gwdat.decompress`.
  C3  Kraft equality in exact `fractions.Fraction` arithmetic on every reconstructed
      table. Float summation over 285 terms including 2**-16 does not reliably land on 1.
  C4  the reconstruction rebuilt into a table and compared to the one `build_table`
      actually produced -- all 256 nodes, all 24 `trans` rows, every `vals` entry. Kraft
      cannot catch a length map that is complete but assigns the right lengths to the
      wrong symbols. This can.

  and the one that is not ours to force at all:

  C5  THE META-COST CONTROL. Feed retail's own (lengths, present, symbol_count) to the
      meta-coder DP and compare with the table bits MEASURED off the bit reader. Three
      outcomes, stated before the numbers: equal means the cost model is validated and
      retail's table encoder is optimal; DP BELOW retail means retail's encoder is
      suboptimal and the gap is real headroom; DP ABOVE retail means OUR COST MODEL IS
      WRONG, because the DP is by construction the minimum over the same alphabet and
      retail cannot beat it -- that arm is a failure to be fixed, never tuned.

THE FRAMING MODEL, which is the one place a bit count becomes a byte count. A stored
compression-8 row is `bitstream_bytes + 4`, where the trailing u32 is the uncompressed
size and `bitstream_bytes` is a multiple of 4 (`BitReader.idx` starts at 8 and advances
by 4) large enough to hold the consumed bits PLUS the reader's 32-bit look-ahead:

    bitstream_bytes = 4 * ceil((consumed_bits + 32) / 32)
    stored          = bitstream_bytes + 4

That is `framing_bytes()`. It is the bridge from bits to the byte figure every number
above is quoted in, and it is correct.

WHAT IT IS NOT, because this file said otherwise for the length of one session and the
claim survived into TESTS.md and into the run report. This paragraph used to end: "it is
not a convention we chose -- it PREDICTS the MFT's own `size` field from a bit count, so
it is refutable per row." **That is false, and it is the exact defect CLAUDE.md means by
"a check that cannot fail is not a check."** `ar.raw(e)` slices `data` to `e.size`, so
`len(data) == e.size` BY CONSTRUCTION; C1b already pins `final_idx == len(data) - 4`, and
`avail` is provably in 0..31 after the first consume. The algebra then forces
`framing_bytes(final_bitpos) == e.size` for every stored size divisible by 4 -- and a
census of the study archive puts **138,708 of 138,708 compression-8 rows at
`size % 4 == 0`**. So the "prediction" cannot fail anywhere in the population it is run
over. It is C1b restated in other units: one witness counted twice.

It stays in the test because a bits-to-bytes bridge that silently changed would still be
caught, but it is bookkeeping, NOT independent evidence, and it must never again be
listed beside C1/C4/C5 as something the artifact could refute.
"""
import argparse
import heapq
import os
import struct
import sys
from array import array
from collections import Counter
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gwdat                                             # noqa: E402
from archive import Archive, DEFAULT_DAT                 # noqa: E402


# --------------------------------------------------------------------------
# the meta-coder's cost table, DERIVED from gwdat's constants, never transcribed
# --------------------------------------------------------------------------

def _build_meta_cost():
    """index 0..255 -> the number of bits `build_table`'s walk spends reading it.

    `build_table` picks the first threshold row whose `thr <= peek(32)`, spends
    `row_index + 3` bits, and lands on `last_index - offset` where `offset` is the
    scaled distance above the threshold. Inverting that gives, for each band, a
    CONTIGUOUS block of indices running DOWN from `last_index`, of width
    `(next_higher_threshold - thr) >> (32 - bit_count)`.
    """
    cost = [None] * 256
    hi = 1 << 32
    for i, (thr, last_index) in enumerate(gwdat.CODE_LENGTH_THRESHOLDS):
        bit_count = i + 3
        count = (hi - thr) >> (32 - bit_count)
        for off in range(count):
            idx = last_index - off
            if not 0 <= idx < 256:
                raise ValueError(f"band {i} runs off the alphabet at index {idx}")
            if cost[idx] is not None:
                raise ValueError(f"band {i} overlaps an earlier band at index {idx}")
            cost[idx] = bit_count
        hi = thr
    if any(c is None for c in cost):
        raise ValueError("the threshold table does not cover all 256 meta symbols")
    return cost


META_COST = _build_meta_cost()

# CODE_LENGTH_SYMBOLS maps a meta index to a packed byte; this is the inverse the
# encode direction needs. It is a permutation of 0..255 -- asserted, not assumed.
_INDEX_OF_BYTE = {}
for _i, _b in enumerate(gwdat.CODE_LENGTH_SYMBOLS):
    if _b in _INDEX_OF_BYTE:
        raise ValueError("CODE_LENGTH_SYMBOLS is not a permutation")
    _INDEX_OF_BYTE[_b] = _i
if sorted(_INDEX_OF_BYTE) != list(range(256)):
    raise ValueError("CODE_LENGTH_SYMBOLS does not cover 0..255")

MAX_REPEAT = 8          # (temp >> 5) + 1, and the +1 is in BOTH arms of the walk
MAX_LENGTH = 31         # temp & 0x1F, and follow_root has 32 slots
SYMBOL_COUNT_BITS = 16  # the per-table header build_table reads first


def token_index(repeat, length):
    """(repeat 1..8, length 0..31) -> meta alphabet index."""
    if not 1 <= repeat <= MAX_REPEAT:
        raise ValueError(f"repeat {repeat} outside 1..{MAX_REPEAT}")
    if not 0 <= length <= MAX_LENGTH:
        raise ValueError(f"length {length} outside 0..{MAX_LENGTH}")
    return _INDEX_OF_BYTE[((repeat - 1) << 5) | length]


# cost in bits of describing `repeat` consecutive symbols all of code length `length`
TOKEN_BITS = [[META_COST[token_index(r, L)] for L in range(MAX_LENGTH + 1)]
              for r in range(1, MAX_REPEAT + 1)]


def meta_alphabet_kraft():
    """Fraction: sum(2**-len) over the 256 meta tokens, minus 1. Exactly 0 if complete."""
    return sum((Fraction(1, 1 << c) for c in META_COST), Fraction(0)) - 1


# --------------------------------------------------------------------------
# the meta-coder: what it costs to TRANSMIT one table's code lengths
# --------------------------------------------------------------------------

def _admissible(length, present, n):
    """Can a run of symbols with this (length, present) be described at all?

    `build_table`'s discriminator is NOT `sym_len` alone: the SKIP arm is
    `sym_len == 0 AND symbol_count >= 2`. So with n >= 2 a length of 0 is not
    assignable (a zero-length symbol IS an absent symbol), and with n < 2 a skip
    cannot be expressed (the one token means "one symbol, zero bits").
    """
    if present:
        return not (length == 0 and n >= 2)
    return n >= 2


def _run_key(lens, present, i):
    return (present[i], lens[i] if present[i] else 0)


def meta_plan(lens, present, n, optimal=True):
    """Bits to transmit one table's code lengths, and the token plan that does it.

    `lens[i]` / `present[i]` describe symbols 0..n-1; absent symbols must carry
    length 0. Returns `(bits, plan)` where `plan` is a list of `(repeat, length,
    is_assign)` in EMISSION order -- highest symbol indices first, which is the
    order `build_table`'s downward walk reads them in. `bits` INCLUDES the 16-bit
    `symbol_count` header.

    With `optimal=True` this is a dynamic program over the whole table; with
    `optimal=False` it is longest-admissible-run greedy, which is what retail's own
    encoder does (see `test_gwentropy.py` §5). The DP is worth ~0.002% and exists so
    that "retail's table encoder is optimal" is a MEASURED claim rather than an
    assumption baked into the only estimator we own.
    """
    if n < 1:
        raise ValueError("symbol_count 0 builds a table whose every lookup returns -1 "
                         "(follow[-1] wraps in build_table); an encoder must never emit it")
    if len(lens) < n or len(present) < n:
        raise ValueError("lens/present shorter than symbol_count")

    INF = float("inf")
    if optimal:
        cost = [0] + [INF] * n
        back = [None] * (n + 1)
        for j in range(1, n + 1):
            top = j - 1
            key = _run_key(lens, present, top)
            P, L = key
            if not _admissible(L, P, n):
                continue
            for k in range(1, min(MAX_REPEAT, j) + 1):
                if k > 1 and _run_key(lens, present, top - k + 1) != key:
                    break
                prev = cost[j - k]
                if prev is INF:
                    continue
                c = prev + TOKEN_BITS[k - 1][L]
                if c < cost[j]:
                    cost[j] = c
                    back[j] = (k, L, P)
        if cost[n] is INF:
            raise ValueError("no admissible description for this table "
                             "(a present symbol with length 0 and symbol_count >= 2?)")
        plan = []
        j = n
        while j:
            k, L, P = back[j]
            plan.append((k, L, P))
            j -= k
        return cost[n] + SYMBOL_COUNT_BITS, plan

    plan = []
    bits = SYMBOL_COUNT_BITS
    j = n
    while j:
        top = j - 1
        key = _run_key(lens, present, top)
        P, L = key
        if not _admissible(L, P, n):
            raise ValueError("no admissible description for this table")
        k = 1
        while k < min(MAX_REPEAT, j) and _run_key(lens, present, top - k) == key:
            k += 1
        plan.append((k, L, P))
        bits += TOKEN_BITS[k - 1][L]
        j -= k
    return bits, plan


def lens_to_arrays(lens, symbol_count=None):
    """{symbol: length} -> (lens_list, present_list, n) for `meta_plan`.

    `n` defaults to highest present index + 1, which is what retail does on every one
    of the 13,544 tables S2 measured; anything larger is bits paid for nothing.
    """
    if symbol_count is None:
        symbol_count = (max(lens) + 1) if lens else 1
    out_l = [0] * symbol_count
    out_p = [False] * symbol_count
    for s, L in lens.items():
        if not 0 <= s < symbol_count:
            raise ValueError(f"symbol {s} outside declared count {symbol_count}")
        out_l[s] = L
        out_p[s] = True
    return out_l, out_p, symbol_count


# --------------------------------------------------------------------------
# from-scratch canonical Huffman
# --------------------------------------------------------------------------

def huffman_lengths(counts):
    """{symbol: occurrences>0} -> {symbol: code length}. Ours, from the counts alone.

    A one-symbol alphabet gets length 0, which this format expresses exactly (the
    zero-length code, `gwdat.py:270-288`) and which deflate cannot. Callers that need
    a table rather than a cost want `table_for_counts`, which handles the case where
    the single symbol is not index 0 and the zero-length encoding is unreachable.
    """
    syms = sorted(counts)
    if not syms:
        return {}
    if len(syms) == 1:
        return {syms[0]: 0}
    heap = [(counts[s], i, i) for i, s in enumerate(syms)]
    heapq.heapify(heap)
    parent = [-1] * len(syms)
    order = nxt = len(syms)
    while len(heap) > 1:
        w1, _o1, a = heapq.heappop(heap)
        w2, _o2, b = heapq.heappop(heap)
        parent.append(-1)
        parent[a] = nxt
        parent[b] = nxt
        heapq.heappush(heap, (w1 + w2, order, nxt))
        order += 1
        nxt += 1
    lens = {}
    for i, s in enumerate(syms):
        d = 0
        c = i
        while parent[c] != -1:
            c = parent[c]
            d += 1
        lens[s] = d
    return lens


def table_for_counts(counts):
    """{symbol: count} -> ({symbol: length}, (lens, present, n), note).

    The arrays are what `meta_plan` needs and they are NOT always
    `lens_to_arrays(lens)`, because of the format's one genuinely strange table.
    Three cases the naive Huffman does not cover, all pinned by S2(e) against the
    real `build_table`:

      * NO symbols used at all -- a block with no matches still has to transmit a
        distance table. The cheapest legal one is `symbol_count = 1` described by the
        single token `(repeat=1, length=0)`: 16 + 4 = 20 bits, and the code costs 0
        bits per lookup.
      * ONE symbol used, at index 0. Identical table.
      * ONE symbol used at index s > 0. Now `symbol_count = s+1 >= 2`, and with
        `symbol_count >= 2` a length of 0 is NOT assignable -- `build_table`'s
        discriminator sends `sym_len == 0` to the SKIP arm. The encoding that works is
        to skip EVERYTHING: with no assignment at all, `total == 0` and
        `gwdat.py:265-268` installs `symbol_count - 1` at length zero, which is
        exactly our symbol. So the table is all-skip runs, the symbol is present with
        a zero-bit code, and `present[]` is all False even though a symbol comes out.
        (`gwdat.py`'s own docstring records this fallback as MEASURED on 12 of 1,089
        text files, all distance tables. It is not hypothetical.)
    """
    if not counts:
        return {0: 0}, ([0], [True], 1), "empty"
    if len(counts) == 1:
        s = next(iter(counts))
        if s == 0:
            return {0: 0}, ([0], [True], 1), "single-zero-length"
        n = s + 1
        return {s: 0}, ([0] * n, [False] * n, n), "single-all-skip"
    lens = huffman_lengths(counts)
    deepest = max(lens.values())
    if deepest > MAX_LENGTH:
        raise ValueError(
            f"code length {deepest} exceeds the format's ceiling of {MAX_LENGTH}; "
            "a block holds at most 65,536 tokens so the Katona bound caps natural "
            "Huffman depth at 22 -- this should be unreachable")
    return lens, lens_to_arrays(lens), "huffman"


def canonical_codes(lens):
    """{symbol: length} -> {symbol: (code, length)} under `build_table`'s own rule.

    Included because "canonical Huffman" has to mean THIS format's assignment, not
    deflate's: `build_table` starts `next_bits` at 1, walks each length's symbols in
    ASCENDING index order counting DOWN, then doubles-and-adds-one between lengths.
    Costs nothing to compute and lets `verify_lengths` check the reconstruction
    against the artifact rather than against itself.
    """
    by_len = {}
    for s, L in lens.items():
        by_len.setdefault(L, []).append(s)
    for v in by_len.values():
        v.sort()
    out = {}
    next_bits = 1
    for L in range(1, MAX_LENGTH + 1):
        for s in by_len.get(L, ()):
            if next_bits >= (1 << L):
                raise ValueError(f"code space exhausted at length {L}")
            out[s] = (next_bits, L)
            next_bits -= 1
        next_bits = (next_bits << 1) + 1
    for s in by_len.get(0, ()):
        out[s] = (0, 0)
    return out


def kraft_defect(lens):
    """Fraction: sum(2**-L) - 1. EXACT rational arithmetic, never float.

    A length-16 code contributes 2**-16 and float summation over 285 such terms does
    not reliably land on 1. Negative means a symbol was dropped; positive means one
    was invented.
    """
    return sum((Fraction(1, 1 << L) for L in lens.values()), Fraction(0)) - 1


# --------------------------------------------------------------------------
# reading code lengths back out of a table `build_table` produced
# --------------------------------------------------------------------------

def table_lengths(t):
    """`gwdat.HuffTable` -> {symbol: code length}. Reconstruction, not a re-decode.

    Short codes (1..8) are read off `nodes`, where a symbol of length L owns
    2**(8-L) consecutive entries. Long codes (9..31) are read off `trans`/`vals`:
    `vals` is appended in ascending length order and `trans[L-9][1]` is the last
    `vals` index belonging to length L, so consecutive `trans` rows bracket each
    length's slice.
    """
    if t.zero_len:
        return {t.nodes[0][1]: 0}
    lens = {}
    for i in range(256):
        enc_len, enc_val = t.nodes[i]
        if enc_len == 0 or enc_len == 0xFFFFFFFF:
            continue
        lens[enc_val] = enc_len
    prev = -1
    for row in t.trans:
        _first_enc, last_index, enc_length = row
        if enc_length == 0:
            continue                       # this row was never written (no long codes)
        for idx in range(prev + 1, last_index + 1):
            lens[t.vals[idx]] = enc_length
        prev = last_index
    return lens


def verify_lengths(t, lens):
    """Rebuild the whole table from `lens` alone; None if identical, else what differs.

    This is C4, and it is the check that keeps `table_lengths` honest. Kraft equality
    proves the length MULTISET is complete; it says nothing about which symbol got
    which length. Rebuilding `nodes`, `trans` and `vals` and comparing to what
    `build_table` actually produced does.
    """
    by_len = {}
    for s, L in lens.items():
        by_len.setdefault(L, []).append(s)
    for v in by_len.values():
        v.sort()

    nodes = [[0, 0] for _ in range(256)]
    trans = [[0, 0, 0] for _ in range(24)]
    vals = []
    next_bits = 1
    in_table = 0
    total = len(lens)
    for enc_len in range(1, 9):
        for cur in by_len.get(enc_len, ()):
            if next_bits >= (1 << enc_len):
                return f"code space exhausted rebuilding length {enc_len}"
            first = next_bits << (8 - enc_len)
            for i in range(first, first + (1 << (8 - enc_len))):
                nodes[i][0] = enc_len
                nodes[i][1] = cur
            in_table += 1
            next_bits -= 1
        next_bits = (next_bits << 1) + 1

    if in_table == 0:
        zeros = by_len.get(0, ())
        if not zeros:
            return "no codes of length 1..8 and none of length 0 either"
        zero_symbol = zeros[-1]
        if not t.zero_len:
            return "rebuilt a zero-length table where build_table did not"
        for i in range(256):
            if t.nodes[i] != [0, zero_symbol]:
                return f"zero-length node {i} is {t.nodes[i]}, expected [0, {zero_symbol}]"
        return None

    if in_table != total:
        for enc_len in range(9, 32):
            for cur in by_len.get(enc_len, ()):
                if next_bits >= (1 << enc_len):
                    return f"code space exhausted rebuilding long length {enc_len}"
                partial = next_bits >> (enc_len - 8)
                nodes[partial][0] = 0xFFFFFFFF
                nodes[partial][1] = 0
                vals.append(cur)
                next_bits -= 1
            first_enc = gwdat.shl((next_bits + 1) & gwdat.M, 32 - enc_len)
            trans[enc_len - 9] = [first_enc, len(vals) - 1, enc_len]
            next_bits = (next_bits << 1) + 1

    if t.zero_len:
        return "build_table produced a zero-length table where the rebuild did not"
    for i in range(256):
        if t.nodes[i] != nodes[i]:
            return f"node {i}: build_table {t.nodes[i]}, rebuild {nodes[i]}"
    for k in range(24):
        if t.trans[k] != trans[k]:
            return f"trans[{k}]: build_table {t.trans[k]}, rebuild {trans[k]}"
    if list(t.vals) != vals:
        return f"vals differ: {len(t.vals)} vs {len(vals)} entries"
    return None


# --------------------------------------------------------------------------
# the tracer
# --------------------------------------------------------------------------

class TracedBitReader(gwdat.BitReader):
    """`gwdat.BitReader` plus an INDEPENDENT consumed-bit counter.

    `bitpos` is derived from the reader's own state (`idx*8 - 32 - avail`); `n_consumed`
    is accumulated in the override. Nothing forces them equal -- `test_gwentropy.py`
    asserts they are, which is what makes `bitpos` evidence rather than a definition.
    """
    __slots__ = ('n_consumed',)

    def __init__(self, data):
        gwdat.BitReader.__init__(self, data)
        self.n_consumed = 0

    @property
    def bitpos(self):
        return self.idx * 8 - 32 - self.avail

    def consume(self, count):
        gwdat.BitReader.consume(self, count)
        self.n_consumed += count


class BlockTrace:
    __slots__ = ('index', 'bit_start', 'bit_lit_table', 'bit_dist_table',
                 'bit_after_size', 'bit_end', 'lit_symbol_count', 'dist_symbol_count',
                 'lit_lens', 'dist_lens', 'lit_zero', 'dist_zero',
                 'size_code', 'block_size', 'n_tokens',
                 'out_bytes', 'lit_counts', 'dist_counts', 'extra_bits',
                 'lit_syms', 'dist_syms', 'extra_vals',
                 'lit_table', 'dist_table')

    @property
    def lit_table_bits(self):
        return self.bit_lit_table - self.bit_start

    @property
    def dist_table_bits(self):
        return self.bit_dist_table - self.bit_lit_table

    @property
    def token_bits(self):
        """MODELLED, not measured: sum of code length x occurrences."""
        return (sum(self.lit_lens[s] * c for s, c in self.lit_counts.items())
                + sum(self.dist_lens[s] * c for s, c in self.dist_counts.items()))


class StreamTrace:
    __slots__ = ('stored_size', 'out_size', 'lead_bits', 'first_four', 'header_bits',
                 'blocks', 'final_bitpos', 'final_idx', 'final_avail',
                 'final_consumed', 'eof')


def trace(data, out_size=None, keep_streams=True, keep_tables=False):
    """Mirror of `gwdat.decompress` with recording. -> (payload, StreamTrace).

    Same `out_size` semantics as `gwdat.decompress`: None takes the trailing u32.
    `keep_streams=False` drops the per-token arrays (counts and bit positions are
    kept), which is what a size-only sweep wants; `replay()` then refuses.
    `keep_tables=True` also holds on to the `HuffTable` objects `build_table`
    returned, which is what C4 (`verify_lengths`) needs as its referee.
    """
    if out_size is None:
        out_size = struct.unpack_from('<I', data, (len(data) // 4) * 4 - 4)[0]
    r = TracedBitReader(data)
    out = bytearray()

    st = StreamTrace()
    st.stored_size = len(data)
    st.out_size = out_size
    st.blocks = []
    st.eof = False
    st.lead_bits = r.peek(4)
    r.consume(4)
    st.first_four = r.read(4)
    st.header_bits = 8

    LEB = gwdat.LENGTH_EXTRA_BITS
    LB = gwdat.LENGTH_BASE
    DEB = gwdat.DISTANCE_EXTRA_BITS
    DB = gwdat.DISTANCE_BASE
    first_four = st.first_four

    try:
        while r.idx < len(data) and len(out) < out_size:
            bt = BlockTrace()
            bt.index = len(st.blocks)
            bt.bit_start = r.bitpos
            bt.lit_symbol_count = r.peek(16)
            lit = gwdat.build_table(r)
            bt.bit_lit_table = r.bitpos
            bt.dist_symbol_count = r.peek(16)
            dist = gwdat.build_table(r)
            bt.bit_dist_table = r.bitpos
            bt.size_code = r.read(4)
            bt.block_size = (bt.size_code + 1) * 4096
            bt.bit_after_size = r.bitpos
            bt.lit_lens = table_lengths(lit)
            bt.dist_lens = table_lengths(dist)
            bt.lit_zero = lit.zero_len
            bt.dist_zero = dist.zero_len
            bt.lit_table = lit if keep_tables else None
            bt.dist_table = dist if keep_tables else None

            lit_counts = Counter()
            dist_counts = Counter()
            lit_syms = array('i') if keep_streams else None
            dist_syms = array('i') if keep_streams else None
            extra_vals = array('i') if keep_streams else None
            extra = 0
            ntok = 0
            start_out = len(out)

            for _ in range(bt.block_size):
                if len(out) >= out_size:
                    break
                code = lit.next_code(r)
                ntok += 1
                lit_counts[code] += 1
                if keep_streams:
                    lit_syms.append(code)
                if code < 0x100:
                    out.append(code)
                else:
                    k = code - 256
                    blen = LEB[k]
                    base = LB[k]
                    ev = 0
                    if blen:
                        ev = r.read(blen)
                        base |= ev
                        extra += blen
                    count = first_four + base + 1
                    dcode = dist.next_code(r)
                    dist_counts[dcode] += 1
                    dblen = DEB[dcode]
                    back = DB[dcode]
                    dv = 0
                    if dblen:
                        dv = r.read(dblen)
                        back |= dv
                        extra += dblen
                    if back >= len(out):
                        raise ValueError('backtrack %d >= produced %d' % (back, len(out)))
                    src = len(out) - (back + 1)
                    for j in range(src, src + count):
                        out.append(out[j])
                    if keep_streams:
                        dist_syms.append(dcode)
                        extra_vals.append(ev)
                        extra_vals.append(dv)

            bt.bit_end = r.bitpos
            bt.n_tokens = ntok
            bt.out_bytes = len(out) - start_out
            bt.lit_counts = lit_counts
            bt.dist_counts = dist_counts
            bt.extra_bits = extra
            bt.lit_syms = lit_syms
            bt.dist_syms = dist_syms
            bt.extra_vals = extra_vals
            st.blocks.append(bt)
    except gwdat.Eof:
        st.eof = True

    st.final_bitpos = r.bitpos
    st.final_idx = r.idx
    st.final_avail = r.avail
    # The independent counter. `bitpos` is DERIVED from the reader's own state and
    # `final_consumed` is ACCUMULATED in the override; nothing forces them equal.
    st.final_consumed = r.n_consumed
    return bytes(out), st


def replay(st):
    """Rebuild the payload from the recorded token arrays ALONE. -> bytes.

    No Huffman table, no bit reader, no `data`. If this reproduces the payload then
    the recording is lossless and every re-cost below is over the whole stream rather
    than a lossy summary of it. Requires `keep_streams=True`.
    """
    LEB = gwdat.LENGTH_EXTRA_BITS
    LB = gwdat.LENGTH_BASE
    DEB = gwdat.DISTANCE_EXTRA_BITS
    DB = gwdat.DISTANCE_BASE
    out = bytearray()
    first_four = st.first_four
    for bt in st.blocks:
        if bt.lit_syms is None:
            raise ValueError("replay needs keep_streams=True")
        di = 0
        ei = 0
        for code in bt.lit_syms:
            if code < 0x100:
                out.append(code)
                continue
            k = code - 256
            base = LB[k]
            ev = bt.extra_vals[ei]
            if LEB[k]:
                base |= ev
            count = first_four + base + 1
            dcode = bt.dist_syms[di]
            back = DB[dcode]
            dv = bt.extra_vals[ei + 1]
            if DEB[dcode]:
                back |= dv
            di += 1
            ei += 2
            src = len(out) - (back + 1)
            for j in range(src, src + count):
                out.append(out[j])
    return bytes(out)


def segment_bits(st):
    """The measured stream, split into the segments an encoder has to pay for.

    `tokens` is MODELLED from lengths x counts. Everything else is measured off the
    bit reader. C1 asserts the sum equals `final_bitpos`.
    """
    lit_tables = sum(b.lit_table_bits for b in st.blocks)
    dist_tables = sum(b.dist_table_bits for b in st.blocks)
    size_fields = 4 * len(st.blocks)
    tokens = sum(b.token_bits for b in st.blocks)
    extras = sum(b.extra_bits for b in st.blocks)
    return {
        "header": st.header_bits,
        "lit_tables": lit_tables,
        "dist_tables": dist_tables,
        "size_fields": size_fields,
        "tokens": tokens,
        "extras": extras,
        "total": st.header_bits + lit_tables + dist_tables + size_fields + tokens + extras,
    }


def framing_bytes(bits):
    """Consumed bits -> the stored row size those bits imply, trailer included.

    `BitReader.idx` starts at 8 and advances 4 at a time, and the reader permanently
    holds 32 look-ahead bits it never consumes, so the bitstream region is a multiple
    of 4 bytes covering `bits + 32`. The trailing u32 (uncompressed size) is 4 more.

    NOT a prediction of the MFT `size` field, though this docstring claimed to be one:
    `len(data) == e.size` by construction and C1b pins the final index, so agreement is
    forced for every stored size divisible by 4 (138,708 of 138,708 comp-8 rows). See the
    module docstring -- it is bookkeeping, not evidence.
    """
    words = max(2, -(-(bits + 32) // 32))
    return words * 4 + 4


# --------------------------------------------------------------------------
# the re-cost: retail's tokens, our entropy layer, retail's block partition
# --------------------------------------------------------------------------

def _cost_table(counts, optimal=True):
    """Our cost, in bits, to transmit a table for these symbol occurrences."""
    lens, (lens_l, pres_l, n), note = table_for_counts(counts)
    k = kraft_defect(lens)
    if k != 0:
        raise ValueError(f"our own table is not a complete prefix code (Kraft defect {k}); "
                         "build_table will not refuse it, a lookup will")
    bits, _plan = meta_plan(lens_l, pres_l, n, optimal=optimal)
    return bits, lens, note


def recost(st, optimal=True):
    """Re-cost `st`'s token stream under our own Huffman + meta-coder.

    RETAIL'S BLOCK PARTITION IS KEPT. Choosing our own block boundaries would fold a
    segmentation search into the answer and stop this from isolating the entropy
    layer, which is the whole point of the rung. The extra bits and the block_size
    fields are literally retail's, because they are a function of the tokens and not
    of the code assignment.
    """
    ours_lit = ours_dist = ours_tokens = 0
    retail_lit = retail_dist = retail_tokens = 0
    notes = Counter()
    per_block = []
    for b in st.blocks:
        lit_bits, lit_lens, lit_note = _cost_table(b.lit_counts, optimal)
        dist_bits, dist_lens, dist_note = _cost_table(b.dist_counts, optimal)
        notes[("lit", lit_note)] += 1
        notes[("dist", dist_note)] += 1
        tok = (sum(lit_lens[s] * c for s, c in b.lit_counts.items())
               + sum(dist_lens.get(s, 0) * c for s, c in b.dist_counts.items()))
        ours_lit += lit_bits
        ours_dist += dist_bits
        ours_tokens += tok
        retail_lit += b.lit_table_bits
        retail_dist += b.dist_table_bits
        retail_tokens += b.token_bits
        per_block.append({
            "index": b.index, "tokens": b.n_tokens, "out_bytes": b.out_bytes,
            "retail_lit": b.lit_table_bits, "ours_lit": lit_bits,
            "retail_dist": b.dist_table_bits, "ours_dist": dist_bits,
            "retail_tok": b.token_bits, "ours_tok": tok,
        })

    size_fields = 4 * len(st.blocks)
    extras = sum(b.extra_bits for b in st.blocks)
    ours_total = st.header_bits + ours_lit + ours_dist + size_fields + ours_tokens + extras
    retail_total = (st.header_bits + retail_lit + retail_dist + size_fields
                    + retail_tokens + extras)
    return {
        "blocks": len(st.blocks),
        "header_bits": st.header_bits,
        "size_field_bits": size_fields,
        "extra_bits": extras,
        "retail": {"lit_tables": retail_lit, "dist_tables": retail_dist,
                   "tokens": retail_tokens, "total_bits": retail_total,
                   "stored": framing_bytes(retail_total)},
        "ours": {"lit_tables": ours_lit, "dist_tables": ours_dist,
                 "tokens": ours_tokens, "total_bits": ours_total,
                 "stored": framing_bytes(ours_total)},
        "table_notes": notes,
        "per_block": per_block,
    }


def retail_arrays(lens, declared, zero_len):
    """Retail's decoded table -> the (lens, present, n) its own walk must have described.

    One case does not round-trip naively. If `zero_len` is set with `declared >= 2`,
    the stream did NOT assign a length-0 code -- it skipped every symbol, and
    `gwdat.py:265-268`'s `total == 0` fallback installed `declared - 1` at length
    zero afterwards. So the description is all-skip and `present` is all False, even
    though `table_lengths` reports a symbol. Feeding that back as "one present symbol
    with length 0" would be inadmissible under `symbol_count >= 2` and the control
    would throw where retail has a perfectly legal stream.
    """
    if zero_len and declared >= 2:
        return [0] * declared, [False] * declared, declared
    return lens_to_arrays(lens, declared)


def meta_control(st, optimal=True):
    """C5. Our meta-cost model against retail's MEASURED table bits, per table.

    Feeds retail's own decoded (lengths, present, symbol_count) back through the DP.
    `above` must be 0: the DP is the minimum over the same alphabet, so retail beating
    it means our cost model is wrong, not that retail is clever.
    """
    equal = below = above = 0
    retail_bits = model_bits = 0
    worst = None
    for b in st.blocks:
        for lens, declared, measured, zero in (
                (b.lit_lens, b.lit_symbol_count, b.lit_table_bits, b.lit_zero),
                (b.dist_lens, b.dist_symbol_count, b.dist_table_bits, b.dist_zero)):
            lens_l, pres_l, n = retail_arrays(lens, declared, zero)
            bits, _plan = meta_plan(lens_l, pres_l, n, optimal=optimal)
            retail_bits += measured
            model_bits += bits
            d = bits - measured
            if d == 0:
                equal += 1
            elif d < 0:
                below += 1
            else:
                above += 1
                if worst is None or d > worst[0]:
                    worst = (d, b.index, declared, measured, bits)
    return {"tables": equal + below + above, "equal": equal, "below": below,
            "above": above, "retail_bits": retail_bits, "model_bits": model_bits,
            "worst_above": worst}


# --------------------------------------------------------------------------
# the literal-only number (FINDINGS.md 4.5 asked for it; here it is)
# --------------------------------------------------------------------------

LITERAL_BLOCK_TOKENS = 16 * 4096          # (15 + 1) * 4096, the largest block_size


def literal_only(payload, block_tokens=LITERAL_BLOCK_TOKENS, optimal=True):
    """Cost this payload as Huffman literals with NO LZ77 AT ALL. -> dict.

    `studies/archivewrite/FINDINGS.md` §4.5: "A literal-only Huffman encoder (no LZ77
    matcher) was never costed for ratio... Nobody has a number for it on this payload.
    Fold it into A6." This is that fold.

    Every output byte becomes one literal token, so the block partition is forced:
    `block_size` counts TOKENS (measured, not assumed -- 15 of row 11196's 16 blocks
    emit exactly their declared 65,536 tokens while producing 70,398..128,141 bytes),
    so a literal-only stream needs ceil(len/65536) blocks. Each still transmits a
    distance table, and the cheapest legal one is a single symbol at length 0: 16 + 4
    bits. No extra bits are spent, because extra bits belong to matches.
    """
    if block_tokens > LITERAL_BLOCK_TOKENS:
        raise ValueError("block_size cannot exceed (15+1)*4096 tokens")
    n = len(payload)
    nblocks = max(1, -(-n // block_tokens))
    lit_bits = dist_bits = tok_bits = 0
    size_bits = 4 * nblocks
    for i in range(nblocks):
        chunk = payload[i * block_tokens:(i + 1) * block_tokens]
        counts = Counter(chunk)
        lb, lens, _note = _cost_table(counts, optimal)
        db, _dl, _dn = _cost_table(Counter(), optimal)
        lit_bits += lb
        dist_bits += db
        tok_bits += sum(lens[s] * c for s, c in counts.items())
    total = 8 + lit_bits + dist_bits + size_bits + tok_bits
    return {"payload": n, "blocks": nblocks, "header_bits": 8,
            "lit_tables": lit_bits, "dist_tables": dist_bits,
            "size_field_bits": size_bits, "tokens": tok_bits,
            "total_bits": total, "stored": framing_bytes(total)}


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

ANCHORS = [11196, 13738, 11141]

# S3's witness set: 3 anchors + 23 picks spanning kind (ATEX, model container, audio,
# map, DDS, MZ, unclassified) and stored size 88 B .. 6,247,580 B. The rule that
# produced it is in that pass's report; the rows are pinned here so a run is
# reproducible without re-deriving the census.
WITNESS = [170751, 132653, 2942, 69251, 163552, 13738, 165100, 32341, 93673, 63085,
           173856, 7866, 24996, 11196, 18092, 11141, 151790, 108202, 104109, 8282,
           131910, 15850, 173887, 77177, 128756, 35300]


def _fmt(n):
    return f"{n:,}"


def report_row(ar, row, want_literal=False, optimal=True, verbose=False):
    e = ar.row(row)
    if e.compression != 8:
        raise ValueError(f"row {row} is compression {e.compression}, not 8")
    data = ar.raw(e)
    payload, st = trace(data, keep_streams=want_literal)
    seg = segment_bits(st)
    rc = recost(st, optimal=optimal)
    ctrl = meta_control(st, optimal=optimal)
    out = {
        "row": row, "stored": e.size, "decompressed": len(payload),
        "blocks": len(st.blocks), "seg": seg, "recost": rc, "control": ctrl,
        "closes": seg["total"] == st.final_bitpos,
        "framing_ok": framing_bytes(st.final_bitpos) == e.size,
    }
    if want_literal:
        out["literal_only"] = literal_only(payload, optimal=optimal)
    if verbose:
        print(f"\nrow {row}: stored {_fmt(e.size)} B -> {_fmt(len(payload))} B, "
              f"{len(st.blocks)} blocks, first_four={st.first_four}, "
              f"lead_bits={st.lead_bits}")
        print(f"  segments (bits): header {seg['header']}, lit tables "
              f"{_fmt(seg['lit_tables'])}, dist tables {_fmt(seg['dist_tables'])}, "
              f"size fields {seg['size_fields']}, tokens {_fmt(seg['tokens'])}, "
              f"extras {_fmt(seg['extras'])}")
        print(f"  C1 accounting: modelled {_fmt(seg['total'])} vs measured "
              f"{_fmt(st.final_bitpos)}  delta {seg['total'] - st.final_bitpos}")
        print(f"  framing: predicted stored {_fmt(framing_bytes(st.final_bitpos))} B "
              f"vs MFT {_fmt(e.size)} B")
        print(f"  C5 meta control: {ctrl['tables']} tables, {ctrl['equal']} equal, "
              f"{ctrl['below']} DP-below-retail, {ctrl['above']} DP-ABOVE-retail; "
              f"retail {_fmt(ctrl['retail_bits'])} bits vs DP "
              f"{_fmt(ctrl['model_bits'])} ({ctrl['model_bits'] - ctrl['retail_bits']:+})"
              + (f"  worst {ctrl['worst_above']}" if ctrl["above"] else ""))
    return out


def _print_table(results):
    hdr = (f"{'row':>7} {'retail B':>12} {'ours B':>12} {'delta B':>9} {'delta %':>9} "
           f"{'tbl retail':>11} {'tbl ours':>10} {'tok retail':>12} {'tok ours':>12} "
           f"{'C1':>3} {'frm':>4} {'C5>':>4}")
    print(hdr)
    print("-" * len(hdr))
    for r in results:
        rt, ou = r["recost"]["retail"], r["recost"]["ours"]
        d = ou["stored"] - r["stored"]
        pct = 100.0 * d / r["stored"] if r["stored"] else 0.0
        print(f"{r['row']:>7} {r['stored']:>12,} {ou['stored']:>12,} {d:>9,} "
              f"{pct:>8.4f}% "
              f"{rt['lit_tables'] + rt['dist_tables']:>11,} "
              f"{ou['lit_tables'] + ou['dist_tables']:>10,} "
              f"{rt['tokens']:>12,} {ou['tokens']:>12,} "
              f"{'ok' if r['closes'] else 'BAD':>3} "
              f"{'ok' if r['framing_ok'] else 'BAD':>4} "
              f"{r['control']['above']:>4}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--rows", type=int, nargs="*", default=None)
    ap.add_argument("--witness", action="store_true",
                    help="run S3's 26-row witness set (slow: ~43 MB decompressed)")
    ap.add_argument("--literal-only", action="store_true",
                    help="also cost every payload as Huffman literals with no LZ77")
    ap.add_argument("--greedy", action="store_true",
                    help="cost tables with longest-run greedy (what retail's own "
                         "encoder does) instead of the optimal DP")
    args = ap.parse_args()

    rows = args.rows if args.rows else (WITNESS if args.witness else ANCHORS)
    optimal = not args.greedy
    results = []
    with Archive(args.dat) as ar:
        for row in rows:
            results.append(report_row(ar, row, want_literal=args.literal_only,
                                      optimal=optimal, verbose=True))

    print("\n" + ("=" * 78))
    print(f"re-cost of RETAIL'S OWN tokens under OUR entropy layer "
          f"({'optimal DP' if optimal else 'greedy'} meta-coder), "
          f"retail's block partition kept")
    print("=" * 78)
    _print_table(results)

    bad_c1 = [r["row"] for r in results if not r["closes"]]
    bad_fr = [r["row"] for r in results if not r["framing_ok"]]
    bad_c5 = [r["row"] for r in results if r["control"]["above"]]
    print(f"\nC1 (segment accounting closes): {len(results) - len(bad_c1)}/{len(results)}"
          + (f"  FAILED {bad_c1}" if bad_c1 else ""))
    print(f"framing model predicts MFT size: {len(results) - len(bad_fr)}/{len(results)}"
          + (f"  FAILED {bad_fr}" if bad_fr else ""))
    print(f"C5 (no table where DP beats retail): {len(results) - len(bad_c5)}/{len(results)}"
          + (f"  FAILED {bad_c5}" if bad_c5 else ""))

    if args.literal_only:
        print("\nliteral-only (Huffman, NO LZ77 -- FINDINGS.md 4.5)")
        print(f"{'row':>7} {'payload B':>12} {'lit-only B':>12} {'retail B':>12} "
              f"{'x retail':>9} {'ratio':>8}")
        for r in results:
            lo = r["literal_only"]
            print(f"{r['row']:>7} {lo['payload']:>12,} {lo['stored']:>12,} "
                  f"{r['stored']:>12,} {lo['stored'] / r['stored']:>9.4f} "
                  f"{lo['stored'] / lo['payload']:>8.4f}")

    return 1 if (bad_c1 or bad_c5) else 0


if __name__ == "__main__":
    sys.exit(main())
