#!/usr/bin/env python3
"""Check the A7a LZ77 matcher -- and specifically that its SIZE is not a fiction.

    python toolkit/mapdata/test_gwmatch.py
    python toolkit/mapdata/test_gwmatch.py --rows 11196 13738

WHY THIS FILE IS SHAPED THE WAY IT IS. `gwmatch.py` reports a byte figure for a token
stream nobody ever emitted, and the cheapest way to make that figure look good is to
emit tokens that could not be decoded -- a distance one larger than the window, a match
reaching back further than the bytes produced so far, an overlapping copy the encoder
and the decoder disagree about. Every one of those makes the file SMALLER. So the two
sections that carry this test are the ones that make a small number mean something:

  R1  RECONSTRUCTION, section 3 and section 5. `gwentropy.replay()` rebuilds the payload
      from our token arrays ALONE -- gwdat's own `LENGTH_BASE`/`DISTANCE_BASE`, gwdat's
      own one-byte-at-a-time copy loop so overlapping matches behave exactly as the
      decoder makes them behave, no Huffman table and no bit reader anywhere. If that is
      byte-for-byte equal to the input, the matcher did not invent a match. This is why
      A7a needs no bitstream writer to be believed.
  R2  DECODABILITY, section 3 and section 5. `gwmatch.validate()` re-derives every
      constraint from `gwdat.decompress`'s own arms rather than from the emit path.

and the section that keeps them honest:

  S   SABOTAGE, section 5. Six deliberate corruptions of a real token stream -- an
      off-by-one distance, a bumped length code, a distance past the produced bytes, a
      distance symbol in `DISTANCE_BASE`'s garbage region, a short non-final block, a
      length extra that collides with its base under OR -- each asserted to be CAUGHT.
      A guard nobody has watched fail is what `checks.py` exists to complain about, and
      R1/R2 are the only thing standing between "our encoder is 18 KB better than
      ArenaNet" and a bug.

Section 1 is the format parameters, derived rather than typed, checked EXHAUSTIVELY
against `gwdat`'s own tables: all 32,768 window positions and all 256 length bases must
round-trip through the code/extra split, and the split must never reach a distance
symbol above 29 -- `DISTANCE_BASE[30..45]` is a read past the end of the real table and
an encoder that trusts it emits nonsense.

Section 2 is the degenerate controls, where the right answer is known by hand rather
than by running the thing being tested: an all-zeros buffer has exactly one literal and
then `ceil((n-1)/258)` maximum-length matches at distance 1, and nothing can do better;
an incompressible buffer cannot come out below its own byte count.

Section 4 is real rows, and its load-bearing check is not a size at all -- it is that
**the partition DP is never beaten by any of the 16 uniform partitions**, measured over
all 16. The DP is by construction the minimum over that same space, so a uniform
partition beating it means the DP is wrong. That arm is a failure to fix, never to tune,
and it is the same shape as `test_gwentropy.py`'s C5.

WHAT IS DELIBERATELY NOT HERE. No bitstream, no round trip through `gwdat.decompress`,
no comparison against a size we hope for. A7a is a size-only rung; the moment this file
packs a bit it has left it.
"""
import argparse
import math
import os
import random
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                                              # noqa: E402
import gwdat                                               # noqa: E402
import gwentropy as G                                      # noqa: E402
import gwmatch as M                                        # noqa: E402
from archive import Archive, DEFAULT_DAT                   # noqa: E402

ANCHOR = 11196
ANCHOR_STORED = 1029564
ANCHOR_RESERVATION = 1029632          # TRAILER-INCLUSIVE; see gwmatch's docstring
ROWS = [11196, 13738, 11141, 2942, 8282]

# FLOOR, set from the real green run of 2026-08-18 in this worktree (62 checks, 28 s).
# Sections 1, 2, 3 and 5 need no archive and run 34; section 4 adds 5 per row over the
# 5 rows plus 3 anchor checks, i.e. 28. 62 total, NO HEADROOM. `--rows` changes how many
# rows section 4 sweeps and therefore its check count, so shortening it drops the run
# under the floor and reddens it deliberately. Without the archive at all, section 4
# declares a skip, the run drops to 34 and the verdict goes RED -- which is the intended
# outcome, because a run that never saw a real row has not tested what the rung is about.
LEDGER = checks.Ledger("gwmatch A7a matcher", floor=62)
check = checks.adopt(LEDGER)


# --------------------------------------------------------------------------

def section1():
    print("\n1. the format's parameters, DERIVED from gwdat's tables (no archive)")

    check((M.MIN_MATCH, M.MAX_MATCH, M.WINDOW) == (3, 258, 32768),
          "min match 3, max match 258, window 32,768 -- all derived, none typed",
          f"got {M.MIN_MATCH}, {M.MAX_MATCH}, {M.WINDOW}")

    check(M.LIT_ALPHABET == 285 and M.N_DIST_CODES == 30,
          "alphabets are 285 literal/length and 30 distance",
          f"got {M.LIT_ALPHABET} and {M.N_DIST_CODES}")

    # EXHAUSTIVE: every match length the format can express must survive the round trip
    # through the code/extra split, using gwdat's own reconstruction arithmetic.
    bad = []
    for count in range(M.MIN_MATCH, M.MAX_MATCH + 1):
        k, extra = M.LENGTH_MAP[count - M.FIRST_FOUR - 1]
        if not 0 <= k < M.N_LENGTH_CODES or extra >= (1 << gwdat.LENGTH_EXTRA_BITS[k]):
            bad.append(count)
            continue
        if M.FIRST_FOUR + (gwdat.LENGTH_BASE[k] | extra) + 1 != count:
            bad.append(count)
    check(not bad,
          f"all {M.MAX_MATCH - M.MIN_MATCH + 1} match lengths round-trip through the "
          f"length code/extra split",
          f"{len(bad)} failed, first {bad[:5]}")

    # EXHAUSTIVE over the whole window, and the arm that matters: no distance may ever
    # reach a symbol above 29, because DISTANCE_BASE[30..45] is off the end of the real
    # table and holds garbage.
    bad = []
    over29 = 0
    for back in range(M.WINDOW):
        c = M.DIST_SYM[back]
        extra = M.DIST_EXTRA[back]
        if c > 29:
            over29 += 1
        if extra >= (1 << gwdat.DISTANCE_EXTRA_BITS[c]) or (gwdat.DISTANCE_BASE[c] | extra) != back:
            bad.append(back)
    check(not bad and over29 == 0,
          f"all {M.WINDOW:,} window positions round-trip, and NONE reaches a distance "
          f"symbol above 29",
          f"{len(bad)} failed, {over29} reached the garbage region")

    # The off-by-one that is fatal in both directions. `src = len(out) - (back + 1)`.
    top = M.WINDOW - 1
    check(M.DIST_SYM[top] == 29 and top + 1 == 32768,
          "the largest expressible back value is 32,767, i.e. a DISTANCE of 32,768",
          f"symbol {M.DIST_SYM[top]}, distance {top + 1}")

    # The one length that two codes reach. Retail takes the cheaper one 915/915 times.
    k28, e28 = M.LENGTH_MAP[255]
    check(k28 == 28 and gwdat.LENGTH_EXTRA_BITS[28] == 0,
          "length 258 takes the zero-extra-bit code 28, not code 27 + 5 extra bits",
          f"got k={k28}, extra={e28}")


def _stream(payload, q=8, uniform=None):
    st, cfg = M.build_stream(payload, q=q, uniform=uniform)
    return st


def _r1r2(payload, label, q=8, uniform=None):
    """R1 + R2 on one payload. Two checks."""
    st = _stream(payload, q=q, uniform=uniform)
    bad = M.validate(st)
    check(not bad, f"R2 {label}: every token decodable",
          f"{len(bad)} complaint(s); first: {bad[0] if bad else '-'}")
    rebuilt = G.replay(st)
    ok = rebuilt == bytes(payload)
    where = "-"
    if not ok:
        where = f"len {len(rebuilt)} vs {len(payload)}"
        for i, (a, b) in enumerate(zip(rebuilt, payload)):
            if a != b:
                where = f"first difference at byte {i}"
                break
    check(ok, f"R1 {label}: replay() rebuilds the input byte for byte", where)
    return st


def section2():
    print("\n2. degenerate controls -- the answer is known by hand, not by running this")

    # All zeros. The only sequence of tokens that can do better than "one literal then
    # maximum-length matches at distance 1" would need a match longer than 258, which
    # the format cannot express. So the token count is FORCED and can be computed here.
    n = 100000
    zeros = bytes(n)
    st = _r1r2(zeros, f"{n:,} zero bytes")
    tokens = sum(b.n_tokens for b in st.blocks)
    want = 1 + -(-(n - 1) // M.MAX_MATCH)
    check(tokens == want,
          f"all-zeros is exactly 1 literal + ceil((n-1)/258) matches",
          f"{tokens} tokens, hand-computed optimum {want}")
    dists = set()
    lens = Counter()
    for b in st.blocks:
        ei = 0
        for code in b.lit_syms:
            if code < 256:
                continue
            k = code - 256
            lens[M.FIRST_FOUR + (gwdat.LENGTH_BASE[k] | b.extra_vals[ei]) + 1] += 1
            d = b.dist_syms[(ei // 2)]
            dists.add(gwdat.DISTANCE_BASE[d] + 1)
            ei += 2
    check(dists == {1} and max(lens) == M.MAX_MATCH,
          "and every one of those matches is distance 1, i.e. an OVERLAPPING copy",
          f"distances {sorted(dists)}, longest match {max(lens)}")

    # A two-byte cycle: same argument, distance 2.
    per = b"\x41\x42" * 20000
    st = _r1r2(per, "a 2-byte cycle x 20,000")
    tokens = sum(b.n_tokens for b in st.blocks)
    want = 2 + -(-(len(per) - 2) // M.MAX_MATCH)
    check(tokens == want, "a 2-byte cycle is 2 literals + ceil((n-2)/258) matches",
          f"{tokens} tokens, hand-computed optimum {want}")

    # Incompressible. Huffman over ~uniform bytes cannot beat 8 bits per byte, so the
    # stored size cannot come out below the payload. A matcher inventing matches would.
    rng = random.Random(20260818)
    noise = bytes(rng.randrange(256) for _ in range(60000))
    st = _r1r2(noise, "60,000 incompressible bytes")
    res = M.summarize(st)
    check(res["stored"] >= len(noise),
          "an incompressible payload does not come out SMALLER than itself",
          f"stored {res['stored']:,} B for {len(noise):,} B of noise "
          f"({res['matches']:,} matches found)")


def section3():
    print("\n3. R1/R2 on inputs built to stress the edges")

    rng = random.Random(4242)

    # Exactly the window. A match at distance 32,768 is legal; 32,769 is not, and the
    # matcher must not reach for it.
    tail = bytes(rng.randrange(256) for _ in range(64))
    pre = bytes(rng.randrange(256) for _ in range(M.WINDOW - 64))
    at_window = tail + pre + tail            # the second `tail` is 32,768 back
    st = _r1r2(at_window, "a match at exactly distance 32,768")
    seen = []
    for b in st.blocks:
        for i, d in enumerate(b.dist_syms):
            seen.append(gwdat.DISTANCE_BASE[d] + (b.extra_vals[2 * i + 1]
                                                  if gwdat.DISTANCE_EXTRA_BITS[d] else 0) + 1)
    check(seen and max(seen) <= M.WINDOW,
          "no emitted distance exceeds the 32,768 window",
          f"{len(seen)} matches, longest distance {max(seen) if seen else 0}")

    # Past the window: the repeat is now unreachable and must come out as literals
    # rather than as an illegal distance.
    far = tail + bytes(rng.randrange(256) for _ in range(M.WINDOW + 4096)) + tail
    st = _r1r2(far, "a repeat 36,928 back, i.e. OUTSIDE the window")

    # Overlap at every scale, and a run whose length is not a multiple of 258.
    _r1r2(b"\x00" * 3 + b"\xff" * 517 + b"ab" * 300 + b"\x00" * 7, "mixed overlap runs")

    # Text, which is where lazy matching earns its keep.
    text = (b"the quick brown fox jumps over the lazy dog. " * 900
            + bytes(rng.randrange(256) for _ in range(5000)))
    _r1r2(text, "repetitive text + noise tail")

    # Tiny payloads, where the block and table edge cases live (a block with no matches
    # still transmits a distance table; a one-symbol table is a zero-length code).
    bad = 0
    for n in range(0, 40):
        p = bytes(rng.randrange(4) for _ in range(n))
        s = _stream(p, q=6)
        if M.validate(s) or G.replay(s) != p:
            bad += 1
    check(bad == 0, "R1+R2 hold on all 40 payloads of length 0..39",
          f"{bad} failed")

    # Every dial setting on the same payload must be decodable and rebuild the input.
    mixed = (b"\x00" * 900 + text[:20000] + b"\xa5" * 400)
    bad = []
    sizes = {}
    for q in sorted(M.QUALITY):
        s = _stream(mixed, q=q)
        if M.validate(s) or G.replay(s) != mixed:
            bad.append(q)
        sizes[q] = M.summarize(s)["stored"]
    check(not bad, "R1+R2 hold at every one of the 10 quality dial settings",
          f"failed at {bad}; sizes {min(sizes.values()):,}..{max(sizes.values()):,} B")


def section4(ar, rows):
    print("\n4. real rows -- and the DP partition against all 16 uniform ones")
    anchor_res = None
    for row in rows:
        e = ar.row(row)
        payload = ar.read(e)
        t0 = time.perf_counter()
        units, cfg = M.tokenize(payload, M.DEFAULT_Q)
        st, _ = M.build_stream(payload, q=cfg, units=units)
        res = M.summarize(st, cfg)
        tag = f"row {row} ({e.size:,} B -> {len(payload):,} B)"

        bad = M.validate(st)
        check(not bad, f"R2 {tag}: every token decodable",
              f"{len(bad)} complaint(s); first: {bad[0] if bad else '-'}")
        check(G.replay(st) == payload,
              f"R1 {tag}: replay() rebuilds retail's payload byte for byte",
              f"{res['tokens']:,} tokens, {res['matches']:,} matches, "
              f"{res['blocks']} blocks")

        # BOOKKEEPING, NOT EVIDENCE -- and this comment is the correction. On RETAIL's
        # stream C1 is a real closure: the token term is modelled from reconstructed
        # lengths and the final position is MEASURED off the bit reader, so they are
        # free to disagree. On OUR stream both sides come from the same place --
        # `build_stream` sets the cursors from the same `token_bits` formula
        # `segment_bits` re-sums -- so it cannot fail. Kept because a partition bug
        # would still desynchronise the cursors, but it is not independent evidence
        # and must never be listed beside R1/R2 as though it were. This is the second
        # time this defect class has been caught in two rungs; see FINDINGS 10.6 on
        # `framing_bytes`, and CLAUDE.md on why a check that cannot fail is not a check.
        seg = G.segment_bits(st)
        check(seg["total"] == st.final_bitpos,
              f"C1 {tag}: segment cursors stay consistent (bookkeeping, forced on our "
              f"own stream -- see the comment)",
              f"delta {seg['total'] - st.final_bitpos}")

        # THE CHECK NOTHING OF OURS FORCES. The DP is the minimum over exactly the space
        # the uniform partitions live in, so a uniform beating it means the DP is wrong.
        uni = {}
        for g in range(1, M.MAX_BLOCK_UNITS + 1):
            u_st, _ = M.build_stream(payload, q=cfg, uniform=g, units=units)
            uni[g] = u_st.stored_size
        best_g = min(uni, key=lambda g: uni[g])
        check(res["stored"] <= uni[best_g],
              f"DP {tag}: no uniform partition beats the DP",
              f"DP {res['stored']:,} B, best uniform {uni[best_g]:,} B at "
              f"{best_g * M.BLOCK_UNIT:,} tokens/block "
              f"({res['stored'] - uni[best_g]:+,})")

        # Huffman's own bound, per block, on the token term: at or above the block's
        # zeroth-order entropy and within one bit per token of it. A theorem about
        # Huffman, not a property of our code.
        ent = 0.0
        ntok = 0
        for b in st.blocks:
            for counts in (b.lit_counts, b.dist_counts):
                tot = sum(counts.values())
                if tot < 2:
                    continue
                ntok += tot
                for v in counts.values():
                    ent -= v * math.log2(v / tot)
        tok_bits = seg["tokens"]
        check(ent - 1e-6 <= tok_bits <= ent + ntok + 1e-6,
              f"HUF {tag}: token bits bracketed by Shannon entropy and entropy+n",
              f"{tok_bits:,} in [{ent:,.0f}, {ent + ntok:,.0f}] over {ntok:,} symbols")

        print(f"    {tag}: ours {res['stored']:,} B "
              f"({res['stored'] - e.size:+,} vs retail), {res['blocks']} blocks, "
              f"{res['tokens']:,} tokens, {time.perf_counter() - t0:.1f}s")
        if row == ANCHOR:
            anchor_res = res

    if anchor_res is None:
        LEDGER.skip("4b. the anchor", f"row {ANCHOR} was not in {rows}")
        return
    print(f"\n  ROW {ANCHOR}, TRAILER-INCLUSIVE: retail {ANCHOR_STORED:,} B, "
          f"reservation {ANCHOR_RESERVATION:,} B, ours {anchor_res['stored']:,} B")
    check(ar.row(ANCHOR).size == ANCHOR_STORED,
          f"row {ANCHOR}'s stored size is still {ANCHOR_STORED:,} B",
          f"MFT says {ar.row(ANCHOR).size:,}")
    check(anchor_res["stored"] <= ANCHOR_RESERVATION,
          f"THE BAR: row {ANCHOR} fits its {ANCHOR_RESERVATION:,} B reservation",
          f"ours {anchor_res['stored']:,} B, "
          f"{ANCHOR_RESERVATION - anchor_res['stored']:+,} B of slack")
    # The suspicious direction, and the reason R1 is mandatory. A size far below what a
    # mature deflate reaches on this payload is the signature of an undecodable stream,
    # so it is named as a bound rather than left implicit.
    check(anchor_res["stored"] >= 900000,
          "and it is not implausibly small (R1 already passed, but say the bound "
          "out loud)",
          f"ours {anchor_res['stored']:,} B against zlib's best 1,017,638 B")


def _corrupt(payload, mutate):
    """Build a stream, apply `mutate`, and report what R1/R2 said about it."""
    st, _ = M.build_stream(payload, q=6)
    mutate(st)
    bad = M.validate(st)
    try:
        rebuilt = G.replay(st)
    except Exception as exc:                                    # noqa: BLE001
        return bad, f"replay raised {type(exc).__name__}"
    return bad, ("replay differs" if rebuilt != payload else "replay AGREED")


def section5():
    print("\n5. SABOTAGE -- six corruptions, each asserted to be CAUGHT")
    rng = random.Random(99)
    payload = (b"the quick brown fox " * 700
               + bytes(rng.randrange(256) for _ in range(9000))
               + b"\x00" * 1200)

    def pick_match(st, want):
        """The first match token satisfying `want(block, token_index, match_index)`.

        `want` is also handed the bytes produced so far, because sabotages (a) and (b)
        are about corruptions that stay perfectly LEGAL -- one that also trips R2 would
        not isolate R1, and a distance nudged upward at the very start of the stream
        would trip it.
        """
        for b in st.blocks:
            j = 0
            produced = 0
            for i, code in enumerate(b.lit_syms):
                if code < 256:
                    produced += 1
                    continue
                k = code - 256
                back = gwdat.DISTANCE_BASE[b.dist_syms[j]]
                if gwdat.DISTANCE_EXTRA_BITS[b.dist_syms[j]]:
                    back |= b.extra_vals[2 * j + 1]
                if want(b, i, j, produced, back):
                    return b, i, j
                produced += (M.FIRST_FOUR + (gwdat.LENGTH_BASE[k]
                                             | (b.extra_vals[2 * j]
                                                if gwdat.LENGTH_EXTRA_BITS[k] else 0)) + 1)
                j += 1
        raise AssertionError("the sabotage fixture has no suitable match to corrupt")

    # (a) the off-by-one every LZ77 encoder gets wrong once, chosen so the resulting
    #     token is still entirely LEGAL -- right alphabet, extra inside its field, back
    #     well under the bytes produced. validate() therefore has nothing to say, and
    #     R1 is the only thing standing there. This is the whole argument for why a
    #     size-only rung still needs a reconstruction.
    def bump_distance(st):
        def legal(b, i, j, produced, back):
            eb = gwdat.DISTANCE_EXTRA_BITS[b.dist_syms[j]]
            return (eb > 0 and b.extra_vals[2 * j + 1] + 1 < (1 << eb)
                    and back + 1 < produced)
        b, _i, j = pick_match(st, legal)
        b.extra_vals[2 * j + 1] += 1
    bad, r1 = _corrupt(payload, bump_distance)
    check(not bad and r1 == "replay differs",
          "(a) distance off by one, token still legal -> R2 sees NOTHING and R1 "
          "catches it alone",
          f"R2 said {len(bad)} complaint(s), R1 said {r1}")

    # (b) the same shape on the length side: length codes 0..6 carry no extra bits, so
    #     bumping one moves the reconstructed length by exactly one and leaves the token
    #     legal. Again R2 has nothing to say.
    def bump_length(st):
        def zero_extra(b, i, j, produced, back):
            k = b.lit_syms[i] - 256
            return k <= 6 and gwdat.LENGTH_EXTRA_BITS[k] == 0
        b, i, _j = pick_match(st, zero_extra)
        b.lit_syms[i] += 1
    bad, r1 = _corrupt(payload, bump_length)
    check(r1 == "replay differs" and len(bad) == 1
          and "the tokens produce" in bad[0],
          "(b) match one byte longer than it really is -> every PER-TOKEN arm of R2 "
          "stays silent; R1 and R2's global byte count are what catch it",
          f"R2 said {bad}, R1 said {r1}")

    # (c) a distance reaching back further than the bytes produced so far. This is what
    #     `gwdat.decompress` RAISES on, and it is the corruption that makes a file
    #     smaller, so R2 must name it.
    def far_distance(st):
        b = st.blocks[0]
        b.dist_syms[0] = 29
        b.extra_vals[1] = (1 << gwdat.DISTANCE_EXTRA_BITS[29]) - 1
    bad, r1 = _corrupt(payload, far_distance)
    check(any("produced so far" in m for m in bad),
          "(c) distance past the bytes produced -> R2 names it",
          f"{bad[:1]}")

    # (d) a distance symbol in DISTANCE_BASE's garbage region.
    def garbage_symbol(st):
        st.blocks[0].dist_syms[0] = 30
    bad, _r1 = _corrupt(payload, garbage_symbol)
    check(any("distance symbol 30" in m for m in bad),
          "(d) distance symbol 30 (off the end of the real table) -> R2 names it",
          f"{bad[:1]}")

    # (e) a non-final block that does not fill its declared size. The decoder would read
    #     the NEXT block's tokens through this block's tables, and nothing about the
    #     tokens themselves is wrong -- only the partition is.
    def short_block(st):
        if len(st.blocks) < 2:
            raise AssertionError("the sabotage fixture needs at least two blocks")
        st.blocks[0].block_size += M.BLOCK_UNIT
        st.blocks[0].size_code += 1
    big = payload * 6                       # enough tokens for two blocks
    bad, _r1 = _corrupt(big, short_block)
    check(any("is not final and holds" in m for m in bad),
          "(e) a short non-final block -> R2 names it",
          f"{bad[:1]}")

    # (f) a length extra one bit wider than its own field. `base | extra` equals
    #     `base + extra` only because every LENGTH_BASE is aligned to its extra width;
    #     an overflowing extra silently ORs into the base and the decoder reconstructs
    #     a different length from the same bits than the encoder intended.
    def overflow_extra(st):
        def has_extra(b, i, j, produced, back):
            return gwdat.LENGTH_EXTRA_BITS[b.lit_syms[i] - 256] > 0
        b, i, j = pick_match(st, has_extra)
        b.extra_vals[2 * j] = 1 << gwdat.LENGTH_EXTRA_BITS[b.lit_syms[i] - 256]
    bad, r1 = _corrupt(payload, overflow_extra)
    check(any("length extra" in m and "outside" in m for m in bad),
          "(f) a length extra one bit wider than its field -> R2 names it",
          f"{bad[:1]}, R1 said {r1}")

    # And the control the five above need: the UNCORRUPTED fixture is clean, so the
    # reddening is caused by the sabotage and not by the fixture.
    st, _ = M.build_stream(payload, q=6)
    check(not M.validate(st) and G.replay(st) == payload,
          "CONTROL: the same fixture with no sabotage passes R1 and R2",
          "if this is red the five above prove nothing")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--rows", type=int, nargs="*", default=ROWS)
    args = ap.parse_args()
    t0 = time.perf_counter()

    section1()
    section2()
    section3()
    section5()

    if not os.path.isfile(args.dat):
        LEDGER.skip("4. real rows",
                    f"no archive at {args.dat}; synthetic payloads cannot substitute "
                    f"for the row the rung is about")
    else:
        with Archive(args.dat) as ar:
            section4(ar, args.rows)

    print(f"\n({time.perf_counter() - t0:.1f}s)")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
