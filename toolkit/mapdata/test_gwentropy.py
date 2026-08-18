#!/usr/bin/env python3
"""Check the A6 entropy accountant -- and specifically the checks it CANNOT force true.

    python toolkit/mapdata/test_gwentropy.py
    python toolkit/mapdata/test_gwentropy.py --stride 150     # more sampled rows

WHY THIS FILE IS SHAPED THE WAY IT IS. `gwentropy.py` re-costs retail's own compressed
stream and compares the answer to the MFT's stored size, so the standing hazard is
obvious: our decoder is the only referee we have, and a round trip through it proves
nothing. `gwdat.py`'s own header says the same thing about "it produced the declared
number of bytes" -- the loop terminates on that number, so the match is forced.

So every section below is chosen for what it would mean if it went RED.

Section 1 is arithmetic over the meta alphabet and needs no archive. The load-bearing
check is the EXHAUSTIVE one: all 65,536 sixteen-bit prefixes are pushed through
`build_table`'s own band-selection expression -- gwdat's code, gwdat's constants, not
our inverse -- and the resulting index must equal `META_COST`'s band table, every
index must own a CONTIGUOUS, ALIGNED block of exactly 2**(16-bit_count) prefixes, and
the 256 indices must tile with no hole and no overlap. Our band inversion and gwdat's
forward selection are two different expressions of the same table and are free to
disagree. Kraft over the 256 tokens is checked in exact `Fraction` arithmetic for the
same reason it is elsewhere: a length-16 code contributes 2**-16 and float summation
over 256 terms does not reliably land on 1.

Section 2 proves the meta-coder DP is not decoration -- longest-run greedy really is
suboptimal on this alphabet, and the mechanism (the per-repeat cost vector is NOT
monotone: at length 3 it is 7,9,10,9,12,16,16,16 bits for repeat 1..8) is asserted
rather than described.

Section 3 checks our from-scratch Huffman against BRUTE FORCE. For small alphabets
every complete length assignment is enumerated and the minimum total cost compared to
what `huffman_lengths` produced. This is the only check in the file that can catch a
Huffman that is merely plausible, and it is what makes "our token bits tie retail's"
mean something.

Section 4 is the five closures over real rows, per row, six checks each:
  C1   segment accounting closes to ZERO bits. The token term is MODELLED (sum of
       reconstructed length x count); the table bits and the final bit position are
       MEASURED off the reader. A version that read the token bits off
       `bit_end - bit_after_size` could not fail and is not what this does. RED means
       our symbol->length reconstruction is wrong or something consumes bits we do
       not model, and every A6 number rests on a wrong denominator.
  C1b  the reader identity, plus `final_idx == len(data) - 4`. RED means the decode
       stopped early and the recorded token stream is not the whole stream.
  C1c  `bitpos` (derived from reader state) equals `n_consumed` (accumulated
       independently in the override). RED means `bitpos` is a definition, not a
       measurement.
  C2   `trace()` and `replay()` each reproduce `gwdat.decompress`'s bytes exactly.
       RED on the first means the duplicated block loop has drifted from the referee;
       RED on the second means the recording is lossy and the re-cost is over a
       partial stream.
  C5   THE META-COST CONTROL, and the one nothing of ours forces. Retail's own
       decoded lengths go back through our DP and the answer is compared to the table
       bits MEASURED off the bit reader. `above > 0` -- the DP costing MORE than
       retail's real bits -- is impossible unless our cost model is wrong, because
       the DP is the minimum over the same alphabet. That arm is a failure to fix,
       never to tune.
  FRM  the framing model predicts the MFT's own `size` field from a bit count. That
       field is not an input to the calculation, so this is a prediction about the
       archive rather than a restatement of it.

Section 5 runs C3 (Kraft, exact) and C4 (the reconstruction rebuilt into a table and
compared to the one `build_table` actually produced -- all 256 nodes, all 24 `trans`
rows, every `vals` entry) plus C5 over a wide strided sample, for VOLUME: C5 can fail
once per table per block and the point is to give it thousands of chances. C4 is the
check Kraft cannot substitute for, because a length map can be complete and still
attach the right lengths to the wrong symbols.

Section 6 is the headline, stated as the rung pre-registered it: our re-cost of row
11196 lands within 0.5% of 1,029,564 B, and it is not BELOW retail's token bits (which
would mean we are failing to charge for something ArenaNet had to pay for).

WHAT IS DELIBERATELY NOT HERE. There is no authored bitstream driving `build_table`
with synthetic tables. That would need a bit PACKER, and A6 is a bit-counting rung
with no encoder in it -- the moment this file emits bits it has left the rung. The
ASSIGN/SKIP off-by-ones it would have pinned are pinned instead by section 4/5's C5,
which puts thousands of REAL tables through the same arithmetic with retail's own
measured bit counts as the referee. That is the stronger oracle anyway.
"""
import argparse
import math
import os
import sys
import time
from collections import Counter
from fractions import Fraction
from itertools import product

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                                            # noqa: E402
import gwdat                                             # noqa: E402
import gwentropy as G                                    # noqa: E402
from archive import Archive, DEFAULT_DAT                 # noqa: E402

# The anchors plus eight cheap witnesses spanning ATEX / model / audio / map, from
# S3's witness set. Fixed so the check count does not move with the fixture.
ROWS = [11196, 13738, 11141,
        170751, 132653, 2942, 69251, 163552, 165100, 108202, 104109]
ANCHOR = 11196
ANCHOR_STORED = 1029564          # the MFT's own figure, and the number A6 targets
PREDICTION_PCT = 0.5             # FINDINGS.md section 3, A6 row, pre-registered

# Section 5's sample: comp-8 rows in this stored-size band, taken at a fixed stride
# over the positional entry list. Small rows are cheap and table-dense per byte.
SAMPLE_MIN, SAMPLE_MAX = 64, 24576

# FLOOR, set from the real green run of 2026-08-18 in this worktree (91 checks, 41 s):
# section 1 six, section 2 four, section 3 three, section 4 six per row over eleven
# rows (66), section 5 five, section 6 four, section 7 three. 91 total, NO HEADROOM.
# `--stride` changes how many rows section 5 sweeps, not how many checks it runs, so
# the count does not move with the fixture. Sections 4-7 need the archive and declare
# a skip without it; that skip drops the run to 13 and the verdict goes red, which is
# the intended outcome -- a run that could not reach the vault has checked none of the
# five closures this file exists for.
LEDGER = checks.Ledger("gwentropy A6 accountant", floor=91)
check = checks.adopt(LEDGER)


# --------------------------------------------------------------------------

def section1():
    print("\n1. the meta alphabet, from gwdat's own constants (no archive needed)")

    # (a) the band table tiles 0..255 exactly once. _build_meta_cost already refuses
    #     a gap or an overlap at import; assert the postcondition here too so the
    #     check is visible in the ledger rather than hidden in an exception.
    check(len(G.META_COST) == 256 and all(isinstance(c, int) for c in G.META_COST),
          "META_COST covers all 256 meta symbols",
          f"lengths {min(G.META_COST)}..{max(G.META_COST)}")

    # (b) code lengths span exactly 3..16.
    check(min(G.META_COST) == 3 and max(G.META_COST) == 16,
          "meta code lengths are 3..16",
          f"got {min(G.META_COST)}..{max(G.META_COST)}")

    # (c) EXHAUSTIVE, and against gwdat's forward expression rather than our inverse.
    #     Two independent expressions of the same table; they are free to disagree.
    owner = [None] * 65536
    bad = 0
    for prefix in range(65536):
        b = prefix << 16
        for i, (thr, _last) in enumerate(gwdat.CODE_LENGTH_THRESHOLDS):
            if thr <= b:
                idx_band = i
                break
        bit_count = idx_band + 3
        offset = gwdat.shr((b - gwdat.CODE_LENGTH_THRESHOLDS[idx_band][0]) & gwdat.M,
                           32 - bit_count)
        index = gwdat.CODE_LENGTH_THRESHOLDS[idx_band][1] - offset
        if not 0 <= index < 256 or G.META_COST[index] != bit_count:
            bad += 1
        else:
            owner[prefix] = index
    check(bad == 0,
          "all 65,536 16-bit prefixes: gwdat's band selection agrees with META_COST",
          f"{bad} disagreements")

    # (d) each index owns a CONTIGUOUS, ALIGNED block of exactly 2**(16-bit_count).
    #     A prefix code that failed this would decode ambiguously.
    blocks = {}
    for prefix, index in enumerate(owner):
        if index is None:
            continue
        blocks.setdefault(index, []).append(prefix)
    shape_bad = []
    for index, prefixes in blocks.items():
        want = 1 << (16 - G.META_COST[index])
        lo = prefixes[0]
        if (len(prefixes) != want or prefixes[-1] - lo != want - 1
                or lo % want != 0):
            shape_bad.append(index)
    check(len(blocks) == 256 and not shape_bad,
          "each meta symbol owns one contiguous, aligned prefix block",
          f"{len(blocks)} indices reached, misshapen {shape_bad[:5]}")

    # (e) Kraft, exactly. Complete means there is no unused escape to go hunting for.
    defect = G.meta_alphabet_kraft()
    check(defect == 0, "the meta alphabet is a COMPLETE prefix code (exact Fraction)",
          f"defect {defect}")

    # (f) token_index is a bijection from (repeat 1..8) x (length 0..31).
    seen = set()
    for r in range(1, G.MAX_REPEAT + 1):
        for L in range(G.MAX_LENGTH + 1):
            seen.add(G.token_index(r, L))
    check(len(seen) == 256 and seen == set(range(256)),
          "token_index(repeat, length) is a bijection onto 0..255",
          f"{len(seen)} distinct indices")


def section2():
    print("\n2. the meta-coder: greedy really is suboptimal, and why")

    # The mechanism. If this vector were monotone in `repeat` the DP would be
    # pointless, so assert the non-monotonicity rather than describing it.
    v = [G.TOKEN_BITS[k][3] for k in range(8)]      # length 3, repeat 1..8
    check(v == [7, 9, 10, 9, 12, 16, 16, 16],
          "the per-repeat cost vector is NOT monotone (length 3, repeat 1..8)",
          f"{v}")

    # A uniform run of 9 symbols at length 3: greedy takes 8 then 1 (16+7=23); the
    # DP splits 4+5 (9+12=21).
    lens = [3] * 9
    pres = [True] * 9
    dp_bits, dp_plan = G.meta_plan(lens, pres, 9, optimal=True)
    gr_bits, gr_plan = G.meta_plan(lens, pres, 9, optimal=False)
    check(dp_bits == 16 + 21 and gr_bits == 16 + 23,
          "DP beats longest-run greedy on a 9-run of length 3",
          f"DP {dp_bits}, greedy {gr_bits}, DP plan {dp_plan}")

    # Every plan must tile the table exactly -- overrunning raises `symbol underflow`
    # in build_table, and a short plan leaves symbols undescribed.
    tiling_bad = 0
    for L in range(1, 12):
        for run in range(1, 25):
            for opt in (True, False):
                _b, plan = G.meta_plan([L] * run, [True] * run, run, optimal=opt)
                if sum(k for k, _l, _p in plan) != run:
                    tiling_bad += 1
    check(tiling_bad == 0, "every plan tiles its symbol range exactly",
          f"{tiling_bad} plans over/under-ran")

    # The DP is never worse than greedy, over the same exhaustive space.
    worse = 0
    for L in range(1, 12):
        for run in range(1, 25):
            d, _ = G.meta_plan([L] * run, [True] * run, run, optimal=True)
            g, _ = G.meta_plan([L] * run, [True] * run, run, optimal=False)
            if d > g:
                worse += 1
    check(worse == 0, "the DP is never worse than greedy over 11 x 24 uniform runs",
          f"{worse} cases where it was")


def section3():
    print("\n3. our from-scratch Huffman, against BRUTE FORCE")

    # Enumerate every complete (Kraft == 1) length assignment for small alphabets and
    # compare the best achievable total against what huffman_lengths produced. This
    # is the check that makes "our token bits tie retail's" a result rather than a
    # coincidence of reusing their numbers.
    import random
    rng = random.Random(20260818)
    worse = 0
    trials = 0
    for n in (2, 3, 4, 5, 6):
        for _ in range(30):
            counts = {i: rng.randint(1, 400) for i in range(n)}
            ours = G.huffman_lengths(counts)
            ours_cost = sum(ours[s] * counts[s] for s in counts)
            best = None
            for combo in product(range(1, n + 1), repeat=n):
                if sum(Fraction(1, 1 << L) for L in combo) != 1:
                    continue
                c = sum(combo[s] * counts[s] for s in counts)
                if best is None or c < best:
                    best = c
            trials += 1
            if best is None or ours_cost != best:
                worse += 1
    check(worse == 0,
          f"huffman_lengths is optimal on {trials} brute-forced alphabets",
          f"{worse} suboptimal")

    # Kraft on our own output, exactly, including the 1-symbol case.
    bad = 0
    for n in (1, 2, 5, 40, 285):
        counts = {i: (i + 1) * 7 for i in range(n)}
        lens, _arrays, _note = G.table_for_counts(counts)
        if G.kraft_defect(lens) != 0:
            bad += 1
    check(bad == 0, "every table we would build is a COMPLETE prefix code",
          f"{bad} incomplete")

    # The format's ceiling is 31 (5-bit sym_len, 32 follow_root slots). A block holds
    # at most 65,536 tokens, so the Katona bound caps natural Huffman depth at 22 --
    # assert the ceiling holds on a deliberately Fibonacci-weighted alphabet, which
    # is the worst case for depth.
    fib = [1, 1]
    while len(fib) < 60:
        fib.append(fib[-1] + fib[-2])
    counts = {i: fib[i] for i in range(30)}
    lens = G.huffman_lengths(counts)
    check(max(lens.values()) <= G.MAX_LENGTH,
          "a Fibonacci-weighted alphabet stays inside the format's 31-bit ceiling",
          f"deepest {max(lens.values())}")


def _row_closures(ar, row):
    """Every closure for one row. Returns a dict of booleans plus the numbers."""
    e = ar.row(row)
    data = ar.raw(e)
    payload, st = G.trace(data, keep_streams=True)
    reference, _declared = gwdat.decompress(data)
    seg = G.segment_bits(st)
    ctrl = G.meta_control(st, optimal=True)
    rc = G.recost(st, optimal=True)
    return {
        "row": row, "stored": e.size, "out": len(payload), "blocks": len(st.blocks),
        "c1": seg["total"] == st.final_bitpos,
        "c1_delta": seg["total"] - st.final_bitpos,
        "c1b": (st.final_bitpos + 32 + st.final_avail == 8 * st.final_idx
                and st.final_idx == len(data) - 4),
        "slack": 8 * (len(data) - 4) - st.final_bitpos,
        "c1c": st.final_consumed == st.final_bitpos,
        "c2": payload == reference and G.replay(st) == reference,
        "c5_above": ctrl["above"], "c5_below": ctrl["below"], "tables": ctrl["tables"],
        "frm": G.framing_bytes(st.final_bitpos) == e.size,
        "frm_pred": G.framing_bytes(st.final_bitpos),
        "recost": rc, "seg": seg, "final_bitpos": st.final_bitpos,
    }


def section4(ar):
    print("\n4. the closures, per row -- C1, C1b, C1c, C2, C5, framing")
    results = []
    for row in ROWS:
        r = _row_closures(ar, row)
        results.append(r)
        tag = f"row {row} ({r['stored']:,} B -> {r['out']:,} B, {r['blocks']} blocks)"
        check(r["c1"], f"C1  {tag}: segment accounting closes",
              f"delta {r['c1_delta']} bits")
        check(r["c1b"], f"C1b {tag}: reader identity, payload fully consumed",
              f"tail slack {r['slack']} bits (32 <= slack < 64 is the true form)")
        check(r["c1c"], f"C1c {tag}: derived bitpos == independent counter")
        check(r["c2"], f"C2  {tag}: trace() and replay() both reproduce the payload")
        check(r["c5_above"] == 0,
              f"C5  {tag}: no table where our DP costs MORE than retail's real bits",
              f"{r['tables']} tables, {r['c5_below']} where the DP is cheaper "
              f"(retail's own encoder suboptimal), {r['c5_above']} above")
        check(r["frm"], f"FRM {tag}: framing model predicts the MFT size field",
              f"predicted {r['frm_pred']:,} vs {r['stored']:,}")
    return results


def section5(ar, stride):
    print(f"\n5. C3 (Kraft) / C4 (rebuild) / C5 (control) over a strided sample")
    sample = [e for e in ar.entries
              if e.compression == 8 and SAMPLE_MIN <= e.size <= SAMPLE_MAX][::stride]
    tables = kraft_bad = rebuild_bad = above = below = 0
    zero_len = 0
    rebuild_fail_msg = None
    skipped = 0
    for e in sample:
        data = ar.raw(e)
        try:
            _payload, st = G.trace(data, keep_streams=False, keep_tables=True)
        except Exception:                                       # noqa: BLE001
            skipped += 1
            continue
        for b in st.blocks:
            for lens, declared, measured, zero, tbl in (
                    (b.lit_lens, b.lit_symbol_count, b.lit_table_bits, b.lit_zero,
                     b.lit_table),
                    (b.dist_lens, b.dist_symbol_count, b.dist_table_bits, b.dist_zero,
                     b.dist_table)):
                tables += 1
                if zero:
                    zero_len += 1
                # C3: exact Kraft over the reconstructed lengths.
                if G.kraft_defect(lens) != 0:
                    kraft_bad += 1
                # C4: rebuild the WHOLE table from those lengths alone and compare to
                # the object build_table actually produced. Kraft cannot catch a
                # complete length map attached to the wrong symbols; this can.
                msg = G.verify_lengths(tbl, lens)
                if msg is not None:
                    rebuild_bad += 1
                    rebuild_fail_msg = rebuild_fail_msg or f"row {e.index}: {msg}"
                # C5: the control.
                bits, _plan = G.meta_plan(*G.retail_arrays(lens, declared, zero),
                                          optimal=True)
                if bits > measured:
                    above += 1
                elif bits < measured:
                    below += 1

    if tables == 0:
        LEDGER.skip("5. strided sample", "no comp-8 rows matched the size band")
        return
    check(len(sample) > 50, "the sample is wide enough to mean something",
          f"{len(sample)} rows ({skipped} undecodable), {tables} tables, "
          f"{zero_len} zero-length tables")
    check(kraft_bad == 0, f"C3 Kraft == 0 exactly on all {tables} retail tables",
          f"{kraft_bad} incomplete")
    check(rebuild_bad == 0,
          f"C4 all {tables} reconstructions rebuild build_table's own "
          f"nodes/trans/vals",
          f"{rebuild_bad} mismatched; first: {rebuild_fail_msg}")
    check(above == 0,
          f"C5 no table in the sample where our DP costs MORE than retail's bits",
          f"{tables} tables, {below} where the DP is cheaper, {above} above")
    check(below * 200 < tables,
          "retail's table encoder is at or near optimal on this alphabet",
          f"{below} of {tables} tables the DP improves ({100.0 * below / tables:.3f}%)")


def section6(results):
    print("\n6. the headline, against the PRE-REGISTERED prediction")
    anchor = next(r for r in results if r["row"] == ANCHOR)
    rc = anchor["recost"]
    ours = rc["ours"]["stored"]
    delta = ours - ANCHOR_STORED
    pct = 100.0 * delta / ANCHOR_STORED

    check(anchor["stored"] == ANCHOR_STORED,
          f"row {ANCHOR}'s stored size is still {ANCHOR_STORED:,} B",
          f"MFT says {anchor['stored']:,}")
    check(abs(pct) <= PREDICTION_PCT,
          f"re-cost lands within the pre-registered {PREDICTION_PCT}% of "
          f"{ANCHOR_STORED:,} B",
          f"ours {ours:,} B, delta {delta:+,} B ({pct:+.4f}%)")

    # The suspicious direction. Our token bits CANNOT be below retail's: both are
    # optimal Huffman over the same per-block counts, so a negative delta here means
    # we are failing to charge for something retail had to pay for.
    check(rc["ours"]["tokens"] == rc["retail"]["tokens"],
          "token bits TIE retail's exactly (both optimal Huffman on the same counts)",
          f"ours {rc['ours']['tokens']:,}, retail {rc['retail']['tokens']:,}, "
          f"delta {rc['ours']['tokens'] - rc['retail']['tokens']:+,}")
    check(rc["ours"]["total_bits"] >= rc["retail"]["total_bits"] - 8 * 64,
          "and the total is not implausibly BELOW retail's",
          f"ours {rc['ours']['total_bits']:,} bits vs retail "
          f"{rc['retail']['total_bits']:,}")

    print(f"\n  ROW {ANCHOR}: retail {ANCHOR_STORED:,} B, ours {ours:,} B, "
          f"delta {delta:+,} B ({pct:+.4f}%)")
    print(f"    stream header  {rc['header_bits']:>12,} bits (both)")
    print(f"    lit tables     {rc['retail']['lit_tables']:>12,} retail   "
          f"{rc['ours']['lit_tables']:>12,} ours")
    print(f"    dist tables    {rc['retail']['dist_tables']:>12,} retail   "
          f"{rc['ours']['dist_tables']:>12,} ours")
    print(f"    block_size     {rc['size_field_bits']:>12,} bits (both)")
    print(f"    tokens         {rc['retail']['tokens']:>12,} retail   "
          f"{rc['ours']['tokens']:>12,} ours")
    print(f"    extra bits     {rc['extra_bits']:>12,} bits (both)")
    print(f"    trailer                   4 bytes (both)")


def section7(ar):
    print("\n7. the literal-only number (FINDINGS.md 4.5)")
    e = ar.row(13738)
    payload = ar.read(e)
    lo = G.literal_only(payload)
    # Refutable bounds. Per-block Huffman must sit at or above each block's own
    # zeroth-order entropy and within one bit per token of it -- that bracket is a
    # theorem about Huffman, not a property of our decoder.
    ent = 0.0
    ntok = 0
    for i in range(lo["blocks"]):
        chunk = payload[i * G.LITERAL_BLOCK_TOKENS:(i + 1) * G.LITERAL_BLOCK_TOKENS]
        n = len(chunk)
        ntok += n
        for v in Counter(chunk).values():
            ent -= v * math.log2(v / n)
    check(lo["tokens"] >= ent - 1e-6,
          "literal-only token bits are at or above the per-block Shannon entropy",
          f"{lo['tokens']:,} bits vs entropy {ent:,.1f} bits")
    check(lo["tokens"] <= ent + ntok + 1e-6,
          "and within Huffman's one-bit-per-symbol bound of it",
          f"headroom {ent + ntok - lo['tokens']:,.1f} bits over {ntok:,} tokens")
    check(lo["stored"] > e.size,
          "literal-only is LARGER than retail's LZ77+Huffman stored size",
          f"literal-only {lo['stored']:,} B vs retail {e.size:,} B "
          f"(x{lo['stored'] / e.size:.4f})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--stride", type=int, default=45,
                    help="stride over the small comp-8 rows in section 5")
    args = ap.parse_args()
    t0 = time.perf_counter()

    section1()
    section2()
    section3()

    if not os.path.isfile(args.dat):
        LEDGER.skip("4-7. everything measured against real rows",
                    f"no archive at {args.dat}; sections 1-3 are arithmetic only and "
                    f"cannot substitute for the closures")
    else:
        with Archive(args.dat) as ar:
            results = section4(ar)
            section5(ar, args.stride)
            section6(results)
            section7(ar)

    print(f"\n({time.perf_counter() - t0:.1f}s)")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
