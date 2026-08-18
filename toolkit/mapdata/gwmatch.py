#!/usr/bin/env python3
"""A7a -- the LZ77 matcher for Gw.dat compression code 8. COSTS TOKENS, WRITES NO BITS.

    python toolkit/mapdata/gwmatch.py                      # row 11196 at the default dial
    python toolkit/mapdata/gwmatch.py --sweep              # the whole quality curve
    python toolkit/mapdata/gwmatch.py --rows 13738 --q 7
    python toolkit/mapdata/gwmatch.py --witness            # other real rows
    python toolkit/mapdata/gwmatch.py --partition-curve    # block size vs total size

WHAT THIS IS FOR, AND WHAT IT DELIBERATELY IS NOT. `studies/archivewrite/FINDINGS.md`
section 10 landed rung A6: re-costing RETAIL'S OWN token stream for row 11196 under our
own canonical Huffman plus this format's meta-coder came out **+8 B**, so the entropy
layer is essentially free. Section 10.7 then says the rest out loud -- *"the LZ77 matcher
is completely untested, and it is where 1.2 puts the whole risk"*. A6 answered "can our
entropy layer match theirs GIVEN tokens we did not have to produce". This module answers
the other half: **can we produce the tokens.**

It is the size-only half of A7. There is **no bitstream writer and no round trip through
`gwdat.decompress`** here, because neither is needed to kill or clear the rung: a token
stream has a cost, the cost model that turns tokens into bytes was validated in A6
against retail's own measured bit positions, and the question A7a asks is whether our
tokens cost more bytes than row 11196's 1,029,632 B reservation. **The moment this file
emits a bit it has left the rung.**

THE BAR, AND ITS DENOMINATION, which section 10.6 records as having gone wrong twice
already. Every byte figure in this module is **TRAILER-INCLUSIVE**, the same convention
`gwentropy.framing_bytes()` uses and the same one the MFT's `size` field uses. So:

    retail's stored row 11196   1,029,564 B   (trailer-inclusive)
    the reservation             1,029,632 B   (trailer-inclusive -- NOT section 1.1's
                                               1,029,628, which is that number less
                                               the 4-byte trailer)
    slack over retail                  68 B

Section 1.1's 1,029,628 is the *trailer-exclusive* form of the same bar and must never
be compared against a number out of this module.

THE COST TERM THAT DECIDES IT -- AND THE ONE THING IN THIS DOCSTRING THAT WAS WRITTEN
BACKWARDS BEFORE IT WAS MEASURED. Row 11196 spends 13,486 bits = **1,686 B** transmitting
Huffman tables, **25x the row's 68 B of slack**, and one extra block costs ~843 bits ~
**105 B**. The obvious inference -- the one this module was specified with, and the one
its first draft implemented -- is that an encoder should MINIMISE its block count, and
that since retail's own partition is `[15 x15, 9]` (already the format's maximum 65,536
tokens per block) there is no partitioning trick retail declined.

**That is false, and it is A7a's largest result.** Table transmission is the price of
ADAPTATION, and on this payload the adaptation is worth far more than the tables cost.
MEASURED on row 11196 at dial q8, uniform partitions, everything else held identical:

    tokens/block   blocks   table bits   token bits    stored B
        65,536         16       13,584    7,877,812   1,029,572   <- retail's own choice
        32,768         32       26,941    7,837,497   1,026,212
        16,384         63       52,190    7,767,971   1,020,692
         8,192        125      101,672    7,689,129   1,017,052   <- best uniform
         4,096        250      206,384    7,594,674   1,018,396

Halving the block size costs ~105 B per new block and buys more than that back until
somewhere around 8,192 tokens, where the curve turns. **Retail left 12,520 B on the
table by taking the maximum block size**, which is 184x the row's entire authoring
budget, and it is why zlib -- whose default 16,384-symbol block buffer lands near the
good part of this curve by accident -- beats ArenaNet on ArenaNet's own payload. So the
partition is not a formality to be minimised; it is the single most valuable decision
this module makes, and `plan_partition()` searches it with a dynamic program rather than
guessing a constant.

DERIVATION AND LICENCE. `PLAN.md` section 6.1 carries this module's row, added
2026-08-18 BEFORE the module existed -- the sibling of `gwentropy.py`'s row and for the
same reason. The split it records:

  * **The search is nobody's.** A hash chain over 3-byte prefixes with lazy matching is
    ordinary published technique, and the design followed is **deflate's** (RFC 1951, and
    the shape -- not the numbers -- of zlib's level table), read as prior art and
    re-implemented from the description. No source was ported and no constant copied:
    `QUALITY` below is our own geometric ladder, and it is documented as such so that a
    later reader does not mistake it for zlib's. The partition DP is not deflate's at
    all -- deflate has no such thing.
  * **The parameters are upstream's, and are already covered.** MIN_MATCH, MAX_MATCH,
    WINDOW, both alphabet sizes and the two extra-bit layouts are not chosen here --
    they are DERIVED at import from `gwdat.LENGTH_BASE`, `LENGTH_EXTRA_BITS`,
    `DISTANCE_BASE` and `DISTANCE_EXTRA_BITS`, which `gwdat.py` derives from
    GuildWarsMapBrowser's `SourceFiles/xentax.cpp`. They are IMPORTED, never
    re-transcribed. `THIRD-PARTY-NOTICES.md`'s GWMB entry names this file.
  * Nobody upstream has a matcher for this format to take: all five mirrored lineages
    declare decode only.

THE PARAMETERS, ALL CONFIRMED AGAINST RETAIL'S OWN EMITTED TOKENS before a line of the
matcher was written -- `gwentropy.trace()` on row 11196, 32,952 real matches:

    first_four              measured 2 (and constant at 2 across 4,000 sampled rows).
                            `count = first_four + LENGTH_BASE[k] + extra + 1`, so
                            first_four raises the floor AND the ceiling together; 2 is
                            what gives min match 3. Fixed, and a knob only in principle.
    MIN_MATCH   3           OBSERVED: shortest match in the row is exactly 3.
    MAX_MATCH   258         OBSERVED: longest is exactly 258, and 915 of them take the
                            k=28 code (LENGTH_BASE 0xFF, zero extra bits) rather than
                            k=27 + 5 extra bits -- so preferring the cheaper of two
                            codes for the same length is what retail does too.
    literal/length 285      OBSERVED: symbol 284 is used; every block declares 285.
    distance 0..29          OBSERVED: symbol 29 is used, 30 is not, every block declares
                            30. DISTANCE_BASE entries 30..45 are a read past the end of
                            the real table and hold garbage -- an encoder that trusts all
                            46 emits nonsense. This module builds its distance map from
                            entries 0..29 ONLY.
    WINDOW      32768       `back = DISTANCE_BASE[29] | extra` maxes at 0x7FFF, and the
                            decoder computes `src = len(out) - (back + 1)`, so the
                            DISTANCE is `back + 1` in 1..32768. OBSERVED distances run
                            1..32,766 and none exceeds the bytes produced so far. The
                            off-by-one here is fatal in both directions and it is
                            checked, not assumed.
    OVERLAP     used        The decoder's copy loop appends one byte at a time from
                            `src`, so a match may read bytes it just produced. OBSERVED:
                            691 of 32,952 matches have distance < length. A matcher that
                            forbade overlap would leave real compression on the table,
                            and this one does not forbid it.
    NO end-of-block symbol  A block is bounded by its declared TOKEN count, not by a
                            terminator. OBSERVED: 15 of 16 blocks emit exactly their
                            declared 65,536 tokens. Nothing is budgeted for a terminator.
    block partition         `block_size = (code + 1) * 4096` TOKENS, code 4 bits. A
                            NON-FINAL block must therefore hold EXACTLY its declared
                            token count -- a short one would have the decoder read the
                            next block's tokens through this block's tables -- while the
                            final block may declare more than it holds, because the
                            decode loop also stops at `out_size`. OBSERVED: 15 blocks of
                            exactly 65,536, then 38,381 tokens declared as code 9 =
                            40,960 (code 8 = 36,864 would not have fitted), i.e. the
                            smallest code that covers the remainder. Both rules are
                            enforced by `validate()`.

WHAT CAN REFUTE THE NUMBERS BELOW. `test_gwmatch.py` runs all of it; the two that carry
the file:

  R1  RECONSTRUCTION. `gwentropy.replay()` -- gwdat's own tables, gwdat's own
      one-byte-at-a-time copy semantics, no Huffman table and no bit reader -- must
      rebuild the input BYTE FOR BYTE from our token arrays alone. A matcher that
      invented a match, or got the distance off by one, or mishandled an overlapping
      copy, produces different bytes and is caught without anything being emitted. Be
      suspicious of a size that beats zlib substantially; this is the check that says
      whether it is real.
  R2  DECODABILITY. Every emitted token independently legal: length 3..258, distance
      1..32768 AND never exceeding the bytes produced so far (the decoder RAISES on
      `back >= len(out)`), literal/length symbol < 285, distance symbol <= 29, every
      extra value inside its own field width, and the two block-length rules above.
      A stream that could not be decoded is not a candidate answer whatever it costs.

`validate()` below is R2 and is a function rather than a test so that `encode()` refuses
to report a size for a stream it has not checked.

WHY THE TOKEN CONTAINER IS `gwentropy`'S AND NOT A NEW ONE. The tokens go into
`gwentropy.BlockTrace` / `StreamTrace` objects with the same field names the tracer
fills, so `gwentropy.segment_bits()`, `gwentropy.replay()` and `gwentropy.framing_bytes()`
all run on our stream unmodified -- which means A7a's cost is computed by the SAME code
A6 validated against retail's measured bit positions, rather than by a second
implementation that could quietly disagree. The two `StreamTrace` slots that have no
meaning for a stream nobody read (`final_idx`, `final_avail`) are set to None rather than
to a plausible number.
"""
import argparse
import os
import sys
import time
from array import array
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gwdat                                               # noqa: E402
import gwentropy as G                                      # noqa: E402
from archive import Archive, DEFAULT_DAT                   # noqa: E402


# --------------------------------------------------------------------------
# the format's parameters, DERIVED from gwdat's tables -- never chosen here
# --------------------------------------------------------------------------

FIRST_FOUR = 2                  # measured constant; see the module docstring
N_LENGTH_CODES = len(gwdat.LENGTH_EXTRA_BITS)          # 29
N_DIST_CODES = len(gwdat.DISTANCE_EXTRA_BITS) - 2      # 30, NOT len(DISTANCE_BASE)=46
LIT_ALPHABET = 256 + N_LENGTH_CODES                    # 285


def _build_length_map():
    """base value 0..255 -> (length code k, extra value), preferring FEWER extra bits.

    `count = first_four + (LENGTH_BASE[k] | extra) + 1`, so the encoder's job is to
    split `base = count - first_four - 1` into a code and an extra field. Two facts make
    this a table rather than a search, and both are ASSERTED here rather than assumed:
    every `LENGTH_BASE[k]` is aligned to its own extra-field width (so `|` is `+` and the
    codes tile), and the tiling covers 0..255 with exactly one overlap -- base 255, which
    k=27+extra and k=28 both reach. Retail takes k=28 there 915 times out of 915, which
    is the same preference this builds in.
    """
    out = [None] * 256
    for k in range(N_LENGTH_CODES):
        base = gwdat.LENGTH_BASE[k]
        eb = gwdat.LENGTH_EXTRA_BITS[k]
        if base % (1 << eb):
            raise ValueError(f"LENGTH_BASE[{k}]={base:#x} is not aligned to its "
                             f"{eb}-bit extra field; `base | extra` would not tile")
        for extra in range(1 << eb):
            v = base + extra
            if v > 255:
                raise ValueError(f"length code {k} runs past the 8-bit base range")
            if out[v] is None or eb < gwdat.LENGTH_EXTRA_BITS[out[v][0]]:
                out[v] = (k, extra)
    missing = [v for v, e in enumerate(out) if e is None]
    if missing:
        raise ValueError(f"the length codes do not tile 0..255; missing {missing[:8]}")
    return out


def _build_distance_map():
    """back value 0..WINDOW-1 -> (distance code, extra value).

    Codes 0..29 ONLY. `DISTANCE_BASE` has 46 entries because upstream indexes it by a
    raw symbol; entries 30..45 are a read past the end of the real table and an encoder
    that trusts them emits nonsense. The alignment assertion is the same one the length
    map makes and for the same reason.
    """
    last = N_DIST_CODES - 1
    top = gwdat.DISTANCE_BASE[last] + (1 << gwdat.DISTANCE_EXTRA_BITS[last])
    syms = array('h', [-1]) * top
    exts = array('i', [0]) * top
    for c in range(N_DIST_CODES):
        base = gwdat.DISTANCE_BASE[c]
        eb = gwdat.DISTANCE_EXTRA_BITS[c]
        if base % (1 << eb):
            raise ValueError(f"DISTANCE_BASE[{c}]={base:#x} is not aligned to its "
                             f"{eb}-bit extra field")
        for extra in range(1 << eb):
            v = base + extra
            if syms[v] != -1:
                raise ValueError(f"distance codes overlap at back={v}")
            syms[v] = c
            exts[v] = extra
    if -1 in syms:
        raise ValueError("the distance codes do not tile the window")
    return syms, exts, top


LENGTH_MAP = _build_length_map()
DIST_SYM, DIST_EXTRA, WINDOW = _build_distance_map()

MIN_MATCH = FIRST_FOUR + gwdat.LENGTH_BASE[0] + 1                       # 3
MAX_MATCH = FIRST_FOUR + 255 + 1                                        # 258
BLOCK_UNIT = 4096                       # the granularity of `block_size`
MAX_BLOCK_UNITS = 16                    # the 4-bit size code, so 1..16 units
MAX_BLOCK_TOKENS = MAX_BLOCK_UNITS * BLOCK_UNIT                         # 65,536


# --------------------------------------------------------------------------
# the quality dial -- OURS, a geometric ladder, not zlib's table
# --------------------------------------------------------------------------

class Quality:
    """One point on the matcher's effort curve.

    `max_chain`   how many hash-chain candidates a position may examine.
    `good_length` once a match this long is in hand, the remaining chain budget is cut
                  to a quarter -- the published "we already have enough" heuristic.
    `nice_length` stop searching the moment a match this long is found.
    `max_lazy`    try position i+1 for a longer match before committing the one at i,
                  but only while the match in hand is shorter than this. 0 disables
                  lazy matching entirely, which is the greedy matcher.

    THE NUMBERS ARE OURS. deflate's own level table has a similar shape and that shape
    is the published prior art this follows; the values below are a clean geometric
    ladder chosen here so that no constant is taken from anyone, and so that the sweep
    spans from "obviously too cheap" to "more effort than is affordable in Python".
    """
    __slots__ = ("name", "max_chain", "good_length", "nice_length", "max_lazy")

    def __init__(self, name, max_chain, good_length, nice_length, max_lazy):
        self.name = name
        self.max_chain = max_chain
        self.good_length = good_length
        self.nice_length = nice_length
        self.max_lazy = max_lazy

    def __repr__(self):
        return (f"q{self.name}(chain={self.max_chain}, good={self.good_length}, "
                f"nice={self.nice_length}, lazy={self.max_lazy})")


QUALITY = {
    0: Quality(0, max_chain=1, good_length=8, nice_length=32, max_lazy=0),
    1: Quality(1, max_chain=4, good_length=8, nice_length=32, max_lazy=0),
    2: Quality(2, max_chain=16, good_length=8, nice_length=64, max_lazy=0),
    3: Quality(3, max_chain=16, good_length=8, nice_length=64, max_lazy=16),
    4: Quality(4, max_chain=32, good_length=8, nice_length=128, max_lazy=32),
    5: Quality(5, max_chain=64, good_length=16, nice_length=128, max_lazy=64),
    6: Quality(6, max_chain=128, good_length=16, nice_length=MAX_MATCH, max_lazy=128),
    7: Quality(7, max_chain=256, good_length=32, nice_length=MAX_MATCH, max_lazy=MAX_MATCH),
    8: Quality(8, max_chain=1024, good_length=32, nice_length=MAX_MATCH, max_lazy=MAX_MATCH),
    9: Quality(9, max_chain=4096, good_length=64, nice_length=MAX_MATCH, max_lazy=MAX_MATCH),
}
DEFAULT_Q = 8

HASH_BITS = 15
HASH_SIZE = 1 << HASH_BITS
HASH_MASK = HASH_SIZE - 1
HASH_SHIFT = (HASH_BITS + MIN_MATCH - 1) // MIN_MATCH    # 5: three shifts cover 15 bits


# --------------------------------------------------------------------------
# the matcher
# --------------------------------------------------------------------------

class Unit:
    """One 4,096-token granule -- the finest partition the 4-bit size code allows.

    Tokenizing straight into granules rather than into blocks is what lets
    `plan_partition` search partitions without re-running the matcher: a legal block is
    exactly 1..16 consecutive granules, so the partition question is a dynamic program
    over granule boundaries and the tokens never move.
    """
    __slots__ = ("lit_syms", "dist_syms", "extra_vals", "lit_counts", "dist_counts",
                 "extra_bits", "n_tokens", "out_bytes")

    def __init__(self):
        self.lit_syms = array('i')
        self.dist_syms = array('i')
        self.extra_vals = array('i')
        self.lit_counts = Counter()
        self.dist_counts = Counter()
        self.extra_bits = 0
        self.n_tokens = 0
        self.out_bytes = 0


class _Emitter:
    __slots__ = ("units", "cur")

    def __init__(self):
        self.units = []
        self.cur = Unit()

    def literal(self, byte):
        u = self.cur
        u.lit_syms.append(byte)
        u.lit_counts[byte] += 1
        u.n_tokens += 1
        u.out_bytes += 1
        if u.n_tokens == BLOCK_UNIT:
            self.units.append(u)
            self.cur = Unit()

    def match(self, length, distance):
        u = self.cur
        k, lex = LENGTH_MAP[length - FIRST_FOUR - 1]
        back = distance - 1
        dsym = DIST_SYM[back]
        u.lit_syms.append(256 + k)
        u.lit_counts[256 + k] += 1
        u.dist_syms.append(dsym)
        u.dist_counts[dsym] += 1
        u.extra_vals.append(lex)
        u.extra_vals.append(DIST_EXTRA[back])
        u.extra_bits += gwdat.LENGTH_EXTRA_BITS[k] + gwdat.DISTANCE_EXTRA_BITS[dsym]
        u.n_tokens += 1
        u.out_bytes += length
        if u.n_tokens == BLOCK_UNIT:
            self.units.append(u)
            self.cur = Unit()

    def finish(self):
        if self.cur.n_tokens:
            self.units.append(self.cur)
        return self.units


def tokenize(payload, q=DEFAULT_Q):
    """LZ77 the payload. -> (list of `Unit`, the `Quality` used).

    Hash chain over 3-byte prefixes plus lazy matching, exactly as the docstring
    describes. `q` is a `Quality` or an index into `QUALITY`. No costs are computed
    here and no block boundaries are chosen -- see `plan_partition`.
    """
    cfg = q if isinstance(q, Quality) else QUALITY[q]
    data = payload if isinstance(payload, bytes) else bytes(payload)
    n = len(data)
    em = _Emitter()
    if n == 0:
        return em.finish(), cfg

    head = [-1] * HASH_SIZE
    prev = array('i', [-1]) * n

    max_chain = cfg.max_chain
    good_length = cfg.good_length
    nice_length = cfg.nice_length
    max_lazy = cfg.max_lazy

    # rolling hash state. After folding data[p+MIN_MATCH-1], `ins_h` is the hash of
    # data[p : p+MIN_MATCH]; `ins_pos` is the next position not yet chained. Insertion
    # is strictly sequential, which is what makes the rolling form legal.
    ins_h = 0
    for j in range(min(MIN_MATCH - 1, n)):
        ins_h = ((ins_h << HASH_SHIFT) ^ data[j]) & HASH_MASK
    ins_pos = 0
    last_hashable = n - MIN_MATCH          # positions past this have no 3-byte prefix

    def insert(p):
        """Chain every position up to and including `p`; return p's chain head.

        The head returned is the one recorded BEFORE p was linked, so a position never
        finds itself -- which would be a zero distance and is not expressible.
        """
        nonlocal ins_h, ins_pos
        h_prev = -1
        while ins_pos <= p:
            if ins_pos <= last_hashable:
                ins_h = ((ins_h << HASH_SHIFT) ^ data[ins_pos + MIN_MATCH - 1]) & HASH_MASK
                h_prev = head[ins_h]
                prev[ins_pos] = h_prev
                head[ins_h] = ins_pos
            else:
                h_prev = -1
            ins_pos += 1
        return h_prev

    def longest(i, cur, floor_len):
        """Best match at `i` strictly longer than `floor_len`. -> (length, position).

        `floor_len` is the length already in hand -- 2 for "nothing yet", since a match
        must reach MIN_MATCH == 3 to be expressible at all. Returns (floor_len, -1) when
        nothing better exists. The chain is bounded below by `i - WINDOW`, so the
        distance can never exceed the format's 32,768, and `cur < i` always, so it can
        never exceed the bytes produced either.
        """
        maxlen = n - i
        if maxlen > MAX_MATCH:
            maxlen = MAX_MATCH
        if floor_len >= maxlen:
            return floor_len, -1
        limit = i - WINDOW
        if limit < 0:
            limit = 0
        chain = max_chain
        best = floor_len
        best_p = -1
        scan_end = data[i + best]
        while cur >= limit and chain:
            chain -= 1
            if data[cur + best] == scan_end:
                L = 0
                while L < maxlen and data[cur + L] == data[i + L]:
                    L += 1
                if L > best:
                    best = L
                    best_p = cur
                    if best >= nice_length or best >= maxlen:
                        break
                    scan_end = data[i + best]
                    if best >= good_length:
                        chain >>= 2
            cur = prev[cur]
        return best, best_p

    i = 0
    pending = None                      # a (length, position) already computed for i
    while i < n:
        if pending is not None:
            best_len, best_p = pending
            pending = None
        else:
            cur = insert(i)
            best_len, best_p = (longest(i, cur, MIN_MATCH - 1)
                                if cur >= 0 else (MIN_MATCH - 1, -1))

        if best_p >= 0:
            if max_lazy and best_len < max_lazy and i + 1 < n:
                nxt = insert(i + 1)
                n_len, n_p = (longest(i + 1, nxt, best_len)
                              if nxt >= 0 else (best_len, -1))
                if n_p >= 0:
                    # i+1 does strictly better: spend this byte as a literal and take
                    # that match on the following pass, without searching for it twice.
                    em.literal(data[i])
                    pending = (n_len, n_p)
                    i += 1
                    continue
            em.match(best_len, i - best_p)
            insert(i + best_len - 1)
            i += best_len
        else:
            em.literal(data[i])
            i += 1

    return em.finish(), cfg


# --------------------------------------------------------------------------
# costing -- gwentropy's model, unmodified
# --------------------------------------------------------------------------

def _fit_table(counts, optimal=True):
    """Occurrence counts -> (bits, {symbol: length}, symbol_count, is_zero_length).

    This is `gwentropy.table_for_counts` + `kraft_defect` + `meta_plan`, composed from
    the public functions so that the cost this module reports and the cost A6 validated
    are computed by the same code.
    """
    lens, (lens_l, pres_l, count), note = G.table_for_counts(counts)
    defect = G.kraft_defect(lens)
    if defect != 0:
        raise ValueError(f"our own table is not a complete prefix code (defect {defect})")
    bits, _plan = G.meta_plan(lens_l, pres_l, count, optimal=optimal)
    return bits, lens, count, note != "huffman"


def _block_cost(lit_counts, dist_counts, extra_bits, optimal=True):
    """Total bits one block of these tokens costs: both tables + size field + codes."""
    lit_bits, lit_lens, lit_n, lit_zero = _fit_table(lit_counts, optimal)
    dist_bits, dist_lens, dist_n, dist_zero = _fit_table(dist_counts, optimal)
    tok = (sum(lit_lens[s] * c for s, c in lit_counts.items())
           + sum(dist_lens[s] * c for s, c in dist_counts.items()))
    total = lit_bits + dist_bits + 4 + tok + extra_bits
    return total, {
        "lit_bits": lit_bits, "dist_bits": dist_bits, "tok_bits": tok,
        "lit_lens": lit_lens, "dist_lens": dist_lens,
        "lit_n": lit_n, "dist_n": dist_n,
        "lit_zero": lit_zero, "dist_zero": dist_zero,
    }


def plan_partition(units, optimal=True, uniform=None):
    """Choose block boundaries. -> list of granule counts, one per block.

    A block is 1..16 consecutive 4,096-token granules, so this is a shortest-path
    problem over granule boundaries and the DP below is EXACT for the tokens it is
    given -- not a heuristic. Cost per candidate block is both Huffman tables, the
    4-bit size field, the token code bits under those tables and the extra bits.

    `uniform=g` skips the search and returns a fixed g-granule partition, which is what
    the module docstring's measured table was produced with and what makes "the DP is
    at least as good as every uniform partition" a check the artifact can refute rather
    than an assertion.

    THE CONSTRAINT THAT MAKES THIS LEGAL AT ALL: a non-final block must hold EXACTLY
    its declared token count, because the decoder's inner loop runs `block_size` times
    and a short block would decode the next block's tokens through this block's tables.
    Every granule except the last holds exactly 4,096 tokens, so any group not
    containing the last granule is exactly `g * 4096` -- and the group that does contain
    it is the final block, where a declared size larger than the content is fine because
    the decode loop also stops at `out_size`.
    """
    n = len(units)
    if n == 0:
        return []
    if uniform is not None:
        if not 1 <= uniform <= MAX_BLOCK_UNITS:
            raise ValueError(f"a block is 1..{MAX_BLOCK_UNITS} granules, not {uniform}")
        out = [uniform] * (n // uniform)
        if n % uniform:
            out.append(n % uniform)
        return out

    INF = float("inf")
    cost = [0.0] + [INF] * n
    back = [0] * (n + 1)
    for s in range(n):
        if cost[s] is INF:
            continue
        lit = Counter()
        dist = Counter()
        extra = 0
        for g in range(1, MAX_BLOCK_UNITS + 1):
            e = s + g
            if e > n:
                break
            u = units[e - 1]
            lit.update(u.lit_counts)
            dist.update(u.dist_counts)
            extra += u.extra_bits
            c, _info = _block_cost(lit, dist, extra, optimal)
            if cost[s] + c < cost[e]:
                cost[e] = cost[s] + c
                back[e] = g
    plan = []
    j = n
    while j:
        g = back[j]
        plan.append(g)
        j -= g
    plan.reverse()
    return plan


def _merge(units, s, e):
    """Granules [s, e) -> one `gwentropy.BlockTrace` with the tokens concatenated."""
    b = G.BlockTrace()
    b.lit_syms = array('i')
    b.dist_syms = array('i')
    b.extra_vals = array('i')
    b.lit_counts = Counter()
    b.dist_counts = Counter()
    b.extra_bits = 0
    b.n_tokens = 0
    b.out_bytes = 0
    for u in units[s:e]:
        b.lit_syms.extend(u.lit_syms)
        b.dist_syms.extend(u.dist_syms)
        b.extra_vals.extend(u.extra_vals)
        b.lit_counts.update(u.lit_counts)
        b.dist_counts.update(u.dist_counts)
        b.extra_bits += u.extra_bits
        b.n_tokens += u.n_tokens
        b.out_bytes += u.out_bytes
    return b


def build_stream(payload, q=DEFAULT_Q, optimal=True, first_four=FIRST_FOUR,
                 uniform=None, units=None):
    """Tokenize, partition and cost. -> (`gwentropy.StreamTrace`, cfg).

    Fills the same `BlockTrace` fields the A6 tracer fills, including the bit cursors,
    so `gwentropy.segment_bits()` and `gwentropy.replay()` run on the result unchanged.
    The cursors are a running cost, which is what a real encoder's bit position WOULD be
    -- nothing is packed. Pass `units` to re-partition a token stream without paying for
    the match search again.
    """
    if units is None:
        units, cfg = tokenize(payload, q)
    else:
        cfg = q if isinstance(q, Quality) else QUALITY[q]
    plan = plan_partition(units, optimal=optimal, uniform=uniform)

    st = G.StreamTrace()
    st.out_size = len(payload)
    st.first_four = first_four
    st.lead_bits = 0
    st.header_bits = 8                  # 4 discarded lead bits + the 4 first_four bits
    st.blocks = []
    st.eof = False
    st.final_idx = None                 # reader state; this stream was never read
    st.final_avail = None

    pos = st.header_bits
    s = 0
    for i, g in enumerate(plan):
        b = _merge(units, s, s + g)
        s += g
        b.index = i
        _c, info = _block_cost(b.lit_counts, b.dist_counts, b.extra_bits, optimal)
        b.lit_lens = info["lit_lens"]
        b.dist_lens = info["dist_lens"]
        b.lit_symbol_count = info["lit_n"]
        b.dist_symbol_count = info["dist_n"]
        b.lit_zero = info["lit_zero"]
        b.dist_zero = info["dist_zero"]
        b.lit_table = None
        b.dist_table = None
        # The smallest legal declared size that covers this block's tokens. For every
        # block but the last that is exactly g granules; retail's own final block does
        # the same thing (38,381 tokens -> code 9 = 40,960).
        code = max(0, -(-b.n_tokens // BLOCK_UNIT) - 1)
        if code > MAX_BLOCK_UNITS - 1:
            raise ValueError(f"block {i} holds {b.n_tokens} tokens, over the format's "
                             f"{MAX_BLOCK_TOKENS}")
        b.size_code = code
        b.block_size = (code + 1) * BLOCK_UNIT
        b.bit_start = pos
        b.bit_lit_table = pos + info["lit_bits"]
        b.bit_dist_table = b.bit_lit_table + info["dist_bits"]
        b.bit_after_size = b.bit_dist_table + 4
        pos = b.bit_after_size + b.token_bits + b.extra_bits
        b.bit_end = pos
        st.blocks.append(b)
    st.final_bitpos = pos
    st.final_consumed = pos
    st.stored_size = G.framing_bytes(pos)
    return st, cfg


def summarize(st, cfg=None):
    """The numbers a run reports. All bytes TRAILER-INCLUSIVE.

    `segment_bits` re-derives the total by summing the segments; the cursor in
    `build_stream` accumulates it block by block. They are allowed to disagree, and a
    partition bug is the way they would.
    """
    seg = G.segment_bits(st)
    if seg["total"] != st.final_bitpos:
        raise ValueError(f"segment accounting does not close: {seg['total']} vs "
                         f"{st.final_bitpos}")
    n_tokens = sum(b.n_tokens for b in st.blocks)
    n_match = sum(sum(c for s, c in b.lit_counts.items() if s >= 256) for b in st.blocks)
    return {
        "quality": cfg.name if cfg is not None else None,
        "payload": st.out_size,
        "blocks": len(st.blocks),
        "tokens": n_tokens,
        "literals": n_tokens - n_match,
        "matches": n_match,
        "table_bits": seg["lit_tables"] + seg["dist_tables"],
        "token_bits": seg["tokens"],
        "extra_bits": seg["extras"],
        "total_bits": st.final_bitpos,
        "stored": st.stored_size,
        "size_codes": [b.size_code for b in st.blocks],
    }


# --------------------------------------------------------------------------
# R2 -- decodability. A stream that could not be decoded is not an answer.
# --------------------------------------------------------------------------

def validate(st):
    """Every legality constraint the decoder enforces. -> list of complaints (empty=ok).

    Deliberately re-derived from `gwdat.decompress`'s own arms rather than from this
    module's emit path, so an encoder bug does not get to define what is legal:

      * `lit.next_code` can only return a symbol the table holds, so the literal/length
        symbol must be < 285 and the distance symbol <= 29.
      * `count = first_four + (LENGTH_BASE[k] | extra) + 1` must land in 3..258, and the
        extra value must fit its field -- if `extra` overflowed, `|` would not be `+`
        and the decoder would reconstruct a different length.
      * `if back >= len(out): raise` -- the distance must never exceed the bytes
        produced SO FAR, which is the constraint an encoder is most likely to get off
        by one, so it is checked against a running output length rather than against
        the payload size.
      * a non-final block's declared `block_size` must EQUAL its token count and the
        final one's must COVER it; the first is the rule a partition search is most
        likely to break, and breaking it silently corrupts every following block.
    """
    bad = []
    LEB, LB = gwdat.LENGTH_EXTRA_BITS, gwdat.LENGTH_BASE
    DEB, DB = gwdat.DISTANCE_EXTRA_BITS, gwdat.DISTANCE_BASE
    produced = 0
    last = len(st.blocks) - 1
    for b in st.blocks:
        if not 0 <= b.size_code <= MAX_BLOCK_UNITS - 1:
            bad.append(f"block {b.index}: size_code {b.size_code} is not 4 bits")
        if b.index != last and b.n_tokens != b.block_size:
            bad.append(f"block {b.index} is not final and holds {b.n_tokens} tokens "
                       f"against a declared {b.block_size} -- the decoder would read "
                       f"the next block's tokens through this block's tables")
        if b.n_tokens > b.block_size:
            bad.append(f"block {b.index}: {b.n_tokens} tokens over declared "
                       f"{b.block_size}")
        di = ei = 0
        for code in b.lit_syms:
            if not 0 <= code < LIT_ALPHABET:
                bad.append(f"block {b.index}: literal/length symbol {code} outside "
                           f"0..{LIT_ALPHABET - 1}")
                break
            if code < 256:
                produced += 1
                continue
            k = code - 256
            lex = b.extra_vals[ei]
            if not 0 <= lex < (1 << LEB[k]):
                bad.append(f"block {b.index}: length extra {lex} outside {LEB[k]} bits")
            base = LB[k] | lex
            if base != LB[k] + lex:
                bad.append(f"block {b.index}: length extra {lex} collides with base "
                           f"{LB[k]:#x} under OR")
            count = st.first_four + base + 1
            if not MIN_MATCH <= count <= MAX_MATCH:
                bad.append(f"block {b.index}: match length {count} outside "
                           f"{MIN_MATCH}..{MAX_MATCH}")
            dsym = b.dist_syms[di]
            if not 0 <= dsym < N_DIST_CODES:
                bad.append(f"block {b.index}: distance symbol {dsym} outside "
                           f"0..{N_DIST_CODES - 1}")
                break
            dex = b.extra_vals[ei + 1]
            if not 0 <= dex < (1 << DEB[dsym]):
                bad.append(f"block {b.index}: distance extra {dex} outside "
                           f"{DEB[dsym]} bits")
            back = DB[dsym] | dex
            if back != DB[dsym] + dex:
                bad.append(f"block {b.index}: distance extra {dex} collides with base "
                           f"{DB[dsym]:#x} under OR")
            if back >= produced:
                bad.append(f"block {b.index}: distance {back + 1} exceeds the "
                           f"{produced} bytes produced so far -- gwdat raises here")
            if not 1 <= back + 1 <= WINDOW:
                bad.append(f"block {b.index}: distance {back + 1} outside 1..{WINDOW}")
            di += 1
            ei += 2
            produced += count
            if len(bad) > 20:
                return bad
        if di != len(b.dist_syms) or ei != len(b.extra_vals):
            bad.append(f"block {b.index}: {len(b.dist_syms) - di} unconsumed distance "
                       f"symbols / {len(b.extra_vals) - ei} unconsumed extras")
    if produced != st.out_size:
        bad.append(f"the tokens produce {produced} B, payload is {st.out_size} B")
    return bad


def encode(payload, q=DEFAULT_Q, optimal=True, check=True, uniform=None, units=None):
    """The whole size-only path: tokenize, partition, cost, validate, reconstruct.

    With `check=True` (the default, and what the CLI uses) this refuses to report a size
    for a stream that does not pass R2 and R1. A number from an undecodable stream is
    worse than no number.
    """
    st, cfg = build_stream(payload, q=q, optimal=optimal, uniform=uniform, units=units)
    if check:
        bad = validate(st)
        if bad:
            raise ValueError("R2 decodability FAILED: " + "; ".join(bad[:5]))
        if G.replay(st) != bytes(payload):
            raise ValueError("R1 reconstruction FAILED: replaying the tokens does not "
                             "rebuild the input")
    out = summarize(st, cfg)
    out["checked"] = check
    return out


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

ANCHOR = 11196
ANCHOR_STORED = 1029564
ANCHOR_RESERVATION = 1029632            # TRAILER-INCLUSIVE. See the module docstring.

# Real rows spanning stored size and content kind, from `gwentropy.WITNESS`. The two
# largest are dropped: this is a Python matcher and a 6 MB payload is minutes per dial
# setting, which buys nothing the mid-sized rows do not already say.
WITNESS = [170751, 2942, 69251, 163552, 13738, 165100, 32341, 93673,
           7866, 24996, 18092, 11141, 108202, 104109, 8282, 15850]


def _fmt(n):
    return f"{n:,}"


def run_row(ar, row, qs, optimal=True, uniform=None):
    e = ar.row(row)
    if e.compression != 8:
        raise ValueError(f"row {row} is compression {e.compression}, not 8")
    payload = ar.read(e)
    reservation = ANCHOR_RESERVATION if row == ANCHOR else None
    print(f"\nrow {row}: retail stored {_fmt(e.size)} B -> payload {_fmt(len(payload))} B"
          + (f", reservation {_fmt(reservation)} B" if reservation else ""))
    print(f"{'dial':<4} {'ours B':>12} {'vs retail':>10} "
          + (f"{'bar':>6} " if reservation else "")
          + f"{'tokens':>11} {'blk':>5} {'tbl bits':>9} {'matches':>9} {'time':>8}")
    out = []
    for qi in qs:
        t0 = time.perf_counter()
        res = encode(payload, q=qi, optimal=optimal, uniform=uniform)
        dt = time.perf_counter() - t0
        res["row"] = row
        res["secs"] = dt
        out.append(res)
        bar = ""
        if reservation:
            bar = f" {'FITS' if res['stored'] <= reservation else 'OVER':>6}"
        print(f"q{res['quality']:<3} {res['stored']:>12,} {res['stored'] - e.size:>+10,}"
              f"{bar} {res['tokens']:>11,} {res['blocks']:>5} {res['table_bits']:>9,} "
              f"{res['matches']:>9,} {dt:>7.1f}s")
    return out


def partition_curve(ar, row, q=DEFAULT_Q, optimal=True):
    """Every uniform partition plus the DP, on ONE token stream. The docstring's table.

    The matcher runs once and every row below re-partitions the same tokens, so the
    only thing varying down the column is the block boundary choice.
    """
    e = ar.row(row)
    payload = ar.read(e)
    units, cfg = tokenize(payload, q)
    print(f"\nrow {row} at {cfg!r}: one token stream, {len(units)} granules, "
          f"re-partitioned")
    print(f"{'tokens/block':>13} {'blocks':>7} {'table bits':>11} {'token bits':>12} "
          f"{'stored B':>12} {'vs retail':>10}")
    best = None
    for g in range(1, MAX_BLOCK_UNITS + 1):
        res = encode(payload, q=cfg, optimal=optimal, uniform=g, units=units)
        if best is None or res["stored"] < best[0]:
            best = (res["stored"], g)
        print(f"{g * BLOCK_UNIT:>13,} {res['blocks']:>7} {res['table_bits']:>11,} "
              f"{res['token_bits']:>12,} {res['stored']:>12,} "
              f"{res['stored'] - e.size:>+10,}")
    res = encode(payload, q=cfg, optimal=optimal, units=units)
    print(f"{'DP':>13} {res['blocks']:>7} {res['table_bits']:>11,} "
          f"{res['token_bits']:>12,} {res['stored']:>12,} "
          f"{res['stored'] - e.size:>+10,}")
    print(f"  best uniform was {best[1] * BLOCK_UNIT:,} tokens/block at "
          f"{best[0]:,} B; the DP is {res['stored'] - best[0]:+,} B against it")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--rows", type=int, nargs="*", default=None)
    ap.add_argument("--q", type=int, nargs="*", default=None,
                    help=f"quality dial settings (default {DEFAULT_Q})")
    ap.add_argument("--sweep", action="store_true", help="the whole quality curve")
    ap.add_argument("--witness", action="store_true", help="a set of other real rows")
    ap.add_argument("--partition-curve", action="store_true",
                    help="every uniform block size plus the DP, on one token stream")
    ap.add_argument("--uniform", type=int, default=None,
                    help="force a uniform partition of N granules instead of the DP")
    ap.add_argument("--greedy-meta", action="store_true",
                    help="cost tables with longest-run greedy (what retail's own "
                         "encoder does) instead of the optimal DP")
    args = ap.parse_args()

    qs = args.q if args.q else (sorted(QUALITY) if args.sweep else [DEFAULT_Q])
    rows = args.rows if args.rows else (WITNESS if args.witness else [ANCHOR])
    optimal = not args.greedy_meta

    print(f"A7a size-only matcher -- all bytes TRAILER-INCLUSIVE, "
          f"meta-coder {'greedy' if args.greedy_meta else 'optimal DP'}, "
          f"partition {'uniform ' + str(args.uniform) if args.uniform else 'DP'}")
    with Archive(args.dat) as ar:
        for row in rows:
            if args.partition_curve:
                partition_curve(ar, row, q=qs[0], optimal=optimal)
            else:
                run_row(ar, row, qs, optimal=optimal, uniform=args.uniform)
    return 0


if __name__ == "__main__":
    sys.exit(main())
