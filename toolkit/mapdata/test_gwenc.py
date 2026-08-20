#!/usr/bin/env python3
"""Check the A7b bitstream writer -- and specifically WHICH of its checks prove what.

    python toolkit/mapdata/test_gwenc.py
    python toolkit/mapdata/test_gwenc.py --per-band 40 20 15 8 3
    python toolkit/mapdata/test_gwenc.py --quick          # skip the large size bands

THE THREE CHECKS THAT CARRY THIS FILE, IN ORDER OF STRENGTH, AND THE ONE THING THAT
SEPARATES THEM. `gwdat.py` is OUR decoder. Its own docstring (`gwdat.py:81-84`) records
that the check which would settle it -- diffing against `xentax.cpp` on the same input --
HAS NEVER BEEN RUN, and that it has a KNOWN DIVERGENCE from both upstream lineages on the
zero-length code. So a round trip through `gwdat` proves AGREEMENT, NOT CORRECTNESS. Only
one of the three below escapes that.

  B1  BYTE-IDENTICAL RE-EMISSION OF RETAIL'S OWN ROWS -- section 5, and section 7 for the
      anchor. Trace an existing stored row, re-emit from what the trace recorded, and
      require the bytes to equal the row on disk with `crc32 == the MFT's own recorded
      value`. THIS IS THE ONLY CHECK IN THE RUNG THAT DOES NOT DEPEND ON `gwdat` BEING A
      CORRECT DECODER. A wrong bit order, a wrong canonical assignment, a wrong meta-token
      encoding or wrong extra-bit widths cannot accidentally reproduce ArenaNet's bytes --
      a valid-but-different parse would emit a valid-but-different stream. What it does
      NOT cover is the SEMANTIC tables: `LENGTH_BASE`, `DISTANCE_BASE` and the
      `first_four + base + 1` arithmetic are replayed verbatim from the trace, so a wrong
      one of those would yield a wrong payload and a BIT-IDENTICAL stream. Those stay on
      `gwdat`'s standing risk, and the client is the only oracle (rung A8).
  B2  ROUND TRIP ON OUR OWN OUTPUT -- sections 3 and 7. `gwdat.decompress(encode(p)) == p`
      over real rows and over adversarial synthetics. This is the check that says our
      ENCODER works, and it is the one that only proves agreement with our own decoder.
  B3  THE SIZE CLOSURE -- section 4. The writer's ACTUAL emitted bit count against
      `gwmatch`/`gwentropy`'s PREDICTED one. Two independent computations of the same
      quantity: one a cost model summing `length x count` over the symbol counters and
      `meta_plan`'s returned bit total, the other a byte count taken off the bits that
      were really written, driven by the token ARRAYS and by an emit-width table this
      module derives separately from `gwentropy.META_COST`. A disagreement means one of
      them is wrong, and the one that matters is the cost model, because that is what
      says whether an authored payload fits its reservation. It is compared in BITS
      first: the byte figure is a 32-bit-quantised view and a writer 31 bits off the
      model still lands on the same stored size.

WHAT A RED WOULD MEAN, PER SECTION, because this arc has now shipped a check that could
not fail TWICE -- `framing_bytes` in `test_gwentropy.py` (FINDINGS §10.6) and C1 on our
own stream in `test_gwmatch.py` (§12.7). Asked before each verdict line was written:

  §1  bit order.  RED = our `BitWriter` and `gwdat.BitReader` disagree about where a bit
      goes. Refutable, and the three NEGATIVE CONTROLS make that concrete: words stored
      big-endian, bits packed LSB-first inside the word (zlib's order), and MSB-first
      bytewise with no word reversal all produce DIFFERENT bytes, so the passing arm is
      selecting one order out of four rather than confirming a tautology.
  §2  table acceptance.  RED = a table our encoder implies is refused by `build_table`,
      or is accepted and decodes to different code lengths. This is the arm FINDINGS
      §12.6 says is missing -- A7a's tables "hold by luck of the cost path raising, not
      by an explicit arm". It is refutable and the sabotage sub-check proves it: widen
      one meta token by a single bit and the rebuilt lengths stop matching.
  §3  round trip.  RED = our bytes do not decode back to the input. Refutable -- and the
      truncation control in §6 shows the failure is SILENT, which is why this section
      compares payloads rather than trusting an exception.
  §4  size closure.  RED = the writer emitted a different number of bits than the planner
      charged. Refutable: the two sides are computed by different code from different
      inputs (counters and a plan total, versus token arrays and an emit-width table).
      NOT independent of a shared error in the borrowed `CODE_LENGTH_*` tables -- B1 is
      what covers that.
  §5  B1.  RED = we do not hold ArenaNet's format. The strongest arm in the file.
  §6  the deliberate breakages.  Each is asserted to CHANGE the bytes, so a section that
      quietly stopped mattering goes red here. §6(c) is the important one: it flips the
      meta plan from retail's longest-run greedy to our DP and requires the result to be
      a VALID stream that is NOT retail's bytes -- which is what makes A6's "retail's
      table encoder is greedy" load-bearing here rather than decorative.
  §7  the anchor.  RED on the size arm = A7a's 1,011,244 B model number and the writer's
      real byte count have parted company. RED on the crc arm = the size held and the
      BYTES moved, which is the sharper failure: §16.1's client run accepted those exact
      bytes, so a same-size different-stream encoder has lost the only oracle result the
      arc has.
  §8  the envelope.  RED = we emitted a table shape neither retail's archive nor the A8
      run attests -- a declared count under the floor, or a zero-length literal table.
      Refutable, and the sabotage arm plants one fault per rule and requires each to be
      NAMED. The rules are measurements, not taste: `gwentropy.authoring_table` carries
      the census each one comes from.

DELIBERATELY NOT LISTED AS EVIDENCE. `len(out) == gwentropy.framing_bytes(consumed)` is
asserted inside `gwenc.finish` itself and is bookkeeping, not a check -- `finish` computes
the length FROM that formula, so it cannot fail. The refutable form is §4's, which
compares the writer's bit count against a cost model that never saw the writer.

ALL BYTE FIGURES ARE TRAILER-INCLUSIVE, so the bar for row 11196 is 1,029,632 B and not
§1.1's trailer-exclusive 1,029,628.

NOTHING IS WRITTEN. No archive is opened for writing, no file under `vault/` is touched,
no client and no server is launched. Every byte this file produces lives in memory.
"""
import argparse
import os
import random
import struct
import sys
import time
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks                                              # noqa: E402
import gwdat                                               # noqa: E402
import gwentropy as G                                      # noqa: E402
import gwmatch as MM                                       # noqa: E402
import gwenc as E                                          # noqa: E402
from archive import Archive, DEFAULT_DAT                   # noqa: E402

M32 = 0xFFFFFFFF

ANCHOR = 11196
ANCHOR_STORED = 1029564
ANCHOR_RESERVATION = 1029632          # TRAILER-INCLUSIVE
ANCHOR_A7A_PREDICTION = 1011244       # FINDINGS.md §12.1, q8 + DP partition

# The crc32 of OUR OWN encoding of the anchor's payload at q8 + DP -- not the MFT's crc
# (that one is over RETAIL's stored bytes and is checked separately above). Measured
# 2026-08-19 in this worktree, and pinned because §16.1's result is about BYTES: the
# retail client read exactly these, so an encoder change that keeps the size while moving
# a bit has left the one row an oracle has accepted. The envelope policy of
# `gwentropy.authoring_table` was landed against this number and did not move it -- the
# anchor's tables declare literal 257..285 and distance 24..30, all already inside the
# floors, so every one of them takes the untouched ordinary-Huffman arm.
ANCHOR_ENCODED_CRC = 0xd03ab671

# Rows carrying the divergent zero-length distance table (`gwdat.py:270-288`), where
# retail skips every symbol and `build_table`'s `total == 0` fallback installs the
# symbol afterwards. Pinned because they are the one table shape that does not
# round-trip naively and the one place we KNOW we differ from both upstream lineages.
ZERO_LEN_ROWS = [8295, 8300, 8302, 8305]

# A row where the meta-coder DP beats retail's longest-run greedy (2 tables, 6 bits).
# Found by sweeping `gwentropy.meta_control(optimal=True)` over a seeded sample; it is
# pinned rather than re-searched so §6(c) costs 0.2 s instead of two minutes.
DP_BEATS_GREEDY_ROW = 150875

# A row where the flag matters on OUR OWN tokens: `gwmatch` plans with `optimal=True`
# and a writer hardcoding greedy emits 9 MORE bits than the planner charged. This is the
# trap the module docstring warns about, and §4 uses it to watch B3 go red -- on most
# rows greedy and the DP agree exactly (measured: row 11196's 218 tables, 0 bits apart),
# so a randomly chosen row would NOT demonstrate the failure.
PLAN_FLAG_ROW = 73015

# Stored-size bands for the B1 draw. Reproducible rule, stated so a re-run is the same
# run: take EVERY compression-8 row of the archive in row order, bucket by stored size
# into these half-open bands, and sample each bucket with `random.Random(SEED)`.
BANDS = [(0, 1024), (1024, 16384), (16384, 131072), (131072, 1048576),
         (1048576, 1 << 62)]
BAND_NAMES = ["<1 KB", "1-16 KB", "16-128 KB", "128 KB-1 MB", ">1 MB"]
PER_BAND = [90, 90, 60, 26, 6]
QUICK_PER_BAND = [40, 30, 12, 4, 1]
SEED = 20260818

# The floor is set at the bottom of main(), from the real green run, because the number
# of sections that execute depends on whether the archive is present.


# --------------------------------------------------------------------------
# synthetics -- the adversarial payload set B2 runs over
# --------------------------------------------------------------------------

def _rand_bytes(n, seed):
    rng = random.Random(seed)
    return bytes(rng.randrange(256) for _ in range(n))


def synthetic_payloads():
    """(name, payload, kwargs) -- each chosen for an arm it is likely to break."""
    rng = random.Random(SEED)
    # distance == exactly MM.WINDOW means the repeat starts WINDOW bytes after the
    # original, so prefix + gap must sum to WINDOW exactly. Off by one in either
    # direction and the edge is never reached (or is unreachable), which is the whole
    # point of the case.
    win_pre = _rand_bytes(64, 101)
    win_mid = _rand_bytes(MM.WINDOW - 64, 102)
    cases = [
        # NO EMPTY PAYLOAD. `encode(b"")` is REFUSED (`gwenc._refuse_zero_block`) because
        # a zero-block stream is a shape no retail comp-8 row has, so the fixture that
        # used to sit here is now section 3's refusal check instead. The shortest thing
        # this corpus can carry is one byte.
        ("one byte", b"A", {}),
        ("two bytes", b"AB", {}),
        ("three bytes, min match", b"aaa", {}),
        # all-zeros: one literal then maximum-length matches at distance 1, i.e. every
        # copy OVERLAPS. Its DISTANCE alphabet is the single symbol 0, the one shape the
        # all-skip trick cannot express (`gwdat.py:265-267` installs `declared - 1` and
        # no other index), so it is the fixture that pays the phantom pair's 1 bit per
        # match: 92 -> 144 B, the largest lift in this corpus.
        ("all zeros 100 KB", b"\x00" * 100000, {}),
        # WHICH FIXTURE REACHES WHICH TABLE SHAPE, RE-MEASURED 2026-08-19 against
        # `gwentropy.authoring_table` -- section 8 sweeps these and would go red if the
        # mapping drifted again (it drifted once, and CORRECTING it by hand is what
        # 2026-08-18's version of this block did):
        #   `empty-all-skip` (declared 5, retail rows 8295..8306's own shape) -- "one
        #      byte", "two bytes", "three bytes", "4096 tokens exactly", "granule
        #      straddle x1" block 0.
        #   `single-all-skip` (declared s+1, the untouched arm) -- "7-byte cycle" at
        #      declared 6 and "granule straddle x1" block 2 at declared 27.
        #   phantom pair (a real 1-bit code + one absent neighbour) -- the LITERAL table
        #      of "one byte" and "three bytes", and the DISTANCE table of "all zeros",
        #      "all 0xFF" and "2-byte cycle".
        #   ordinary Huffman LIFTED to the literal floor -- "two bytes" (natural 67),
        #      "4096 tokens exactly" and "granule straddle x1" (natural 256), all -> 257.
        # `all 0xFF` produces an ordinary 3-symbol Huffman LITERAL table declared 285 --
        # NOT a zero-length literal table, which is a shape our writer no longer emits at
        # all (0 of 32,831 small retail rows have one). `incompressible` has 101 matches
        # and a full 30-symbol distance table, so it reaches no special arm.
        ("all 0xFF 40 KB", b"\xff" * 40000, {}),
        ("incompressible 64 KB", _rand_bytes(65536, 201), {}),
        # run-length and short cycles: dense overlapping matches.
        ("2-byte cycle 60 KB", b"ab" * 30000, {}),
        ("7-byte cycle 70 KB", b"abcdefg" * 10000, {}),
        ("repetitive text", (b"the quick brown fox jumps over the lazy dog. " * 2000), {}),
        # a match at EXACTLY the window edge: distance 32,768, distance symbol 29 with a
        # full extra field. The `back` vs `distance` off-by-one is fatal in both
        # directions and §3 asserts the edge is genuinely reached, not merely survived.
        ("window edge 32768", win_pre + win_mid + win_pre, {"quality": 9}),
        # straddle the 4,096-token granule. `uniform=1` forces EVERY block to be exactly
        # one granule, so the "a non-final block must hold exactly its declared token
        # count" rule is exercised a dozen times instead of never.
        ("granule straddle x1", _rand_bytes(50000, 301), {"uniform": 1}),
        ("granule straddle x2", _rand_bytes(50000, 301), {"uniform": 2}),
        ("4096 tokens exactly", bytes(rng.randrange(256) for _ in range(4096)), {}),
        # mixed structure: compressible islands in noise.
        ("mixed islands", b"".join(
            (_rand_bytes(700, 400 + i) if i % 3 else b"Z" * 700) for i in range(90)), {}),
    ]
    return cases


# --------------------------------------------------------------------------
# section 1 -- the bit order, and the three wrong ones
# --------------------------------------------------------------------------

def _pack_words_be(fields):
    """NEGATIVE CONTROL: MSB-first in the word, words stored BIG-endian."""
    acc = n = 0
    out = bytearray()
    for v, c in fields:
        acc = (acc << c) | v
        n += c
        while n >= 32:
            n -= 32
            out += struct.pack('>I', (acc >> n) & M32)
            acc &= (1 << n) - 1
    if n:
        out += struct.pack('>I', (acc << (32 - n)) & M32)
    return bytes(out)


def _pack_lsb_first(fields):
    """NEGATIVE CONTROL: bits packed LSB-first inside the word -- zlib's order."""
    acc = n = 0
    out = bytearray()
    for v, c in fields:
        acc |= v << n
        n += c
        while n >= 32:
            out += struct.pack('<I', acc & M32)
            acc >>= 32
            n -= 32
    if n:
        out += struct.pack('<I', acc & M32)
    return bytes(out)


def _pack_bytewise(fields):
    """NEGATIVE CONTROL: MSB-first bytewise, with no 32-bit word reversal at all."""
    acc = n = 0
    out = bytearray()
    for v, c in fields:
        acc = (acc << c) | v
        n += c
        while n >= 8:
            n -= 8
            out.append((acc >> n) & 0xFF)
            acc &= (1 << n) - 1
    if n:
        out.append((acc << (8 - n)) & 0xFF)
    while len(out) % 4:
        out.append(0)
    return bytes(out)


def section1(check):
    print("\n[1] BIT ORDER -- our writer against gwdat's own reader, plus three wrong "
          "orders")
    rng = random.Random(SEED)

    trials = 400
    total_bits = 0
    mismatch = None
    for t in range(trials):
        fields = []
        for _ in range(rng.randrange(4, 60)):
            c = rng.randrange(1, 33)
            fields.append((rng.randrange(1 << c), c))
        w = E.BitWriter()
        for v, c in fields:
            w.write(v, c)
        # pad to a word and add two words of look-ahead so the reader never starves
        if w.pending:
            w.write(0, 32 - w.pending)
        w.write(0, 32)
        w.write(0, 32)
        data = w.bytes_so_far()
        r = gwdat.BitReader(data)
        for i, (v, c) in enumerate(fields):
            got = r.read(c)
            total_bits += c
            if got != v and mismatch is None:
                mismatch = (t, i, v, got, c)
    check(mismatch is None,
          f"{trials} random field sequences round-trip through gwdat.BitReader",
          f"{total_bits:,} bits" + (f"; first mismatch {mismatch}" if mismatch else ""))

    # The negative controls. Same fields, three plausible-but-wrong packings; each must
    # produce DIFFERENT bytes from ours, or "our order is right" is not a claim.
    fields = [(rng.randrange(1 << c), c) for c in (5, 13, 1, 32, 7, 21, 9, 3, 17, 11)]
    w = E.BitWriter()
    for v, c in fields:
        w.write(v, c)
    if w.pending:
        w.write(0, 32 - w.pending)
    ours = w.bytes_so_far()
    check(_pack_words_be(fields) != ours,
          "NEGATIVE CONTROL: 32-bit words stored big-endian give different bytes")
    check(_pack_lsb_first(fields) != ours,
          "NEGATIVE CONTROL: bits packed LSB-first in the word (zlib's order) differ")
    check(_pack_bytewise(fields) != ours,
          "NEGATIVE CONTROL: MSB-first bytewise with no word reversal differs")

    # the two preconditions ArenaNet's own writer asserts (CmpIo.cpp:138-139)
    bad = False
    try:
        E.BitWriter().write(4, 2)
    except ValueError:
        bad = True
    check(bad, "write() refuses a value that does not fit its field "
               "(CmpIo.cpp:139's own precondition)")
    bad = False
    try:
        E.BitWriter().write(0, 33)
    except ValueError:
        bad = True
    check(bad, "write() refuses a field wider than 32 bits (CmpIo.cpp:138)")


# --------------------------------------------------------------------------
# section 2 -- every table our encoder implies, THROUGH gwdat.build_table
# --------------------------------------------------------------------------

def _table_bytes(lens, declared, zero_len, optimal, widen=None):
    """Emit ONE table description as a standalone bitstream `build_table` can read.

    `widen` corrupts the n-th emitted meta token to one bit wider than its band, which
    desynchronises everything after it -- the sabotage arm of this section.
    """
    w = E.BitWriter()
    lens_l, pres_l, n = G.retail_arrays(lens, declared, zero_len)
    _bits, plan = G.meta_plan(lens_l, pres_l, n, optimal=optimal)
    w.write(n, G.SYMBOL_COUNT_BITS)
    for i, (repeat, length, _p) in enumerate(plan):
        bit_count, pattern = E.META_EMIT[G.token_index(repeat, length)]
        if widen is not None and i == widen:
            w.write(pattern << 1, bit_count + 1)
        else:
            w.write(pattern, bit_count)
    if w.pending:
        w.write(0, 32 - w.pending)
    for _ in range(4):                 # look-ahead the reader will load but not use
        w.write(0, 32)
    return w.bytes_so_far()


def _rebuild(lens, declared, zero_len, optimal, widen=None):
    """-> the code lengths `gwdat.build_table` reads back, or None if it refused."""
    data = _table_bytes(lens, declared, zero_len, optimal, widen=widen)
    try:
        t = gwdat.build_table(gwdat.BitReader(data))
    except (ValueError, gwdat.Eof, IndexError):
        return None
    return G.table_lengths(t)


def section2(check):
    print("\n[2] TABLE ACCEPTANCE -- the arm FINDINGS §12.6 says A7a never had")
    rng = random.Random(SEED + 1)

    cases = []
    # a spread of alphabets and skewnesses, plus the degenerate shapes both table
    # builders special-case
    for trial in range(160):
        n = rng.choice([2, 3, 5, 9, 17, 30, 64, 128, 256, 285])
        used = rng.randrange(2, n + 1)
        syms = rng.sample(range(n), used)
        counts = {s: rng.choice([1, 1, 2, 5, 40, 900, 60000]) for s in syms}
        cases.append(counts)
    cases.append({})                       # no symbols at all
    cases.append({0: 7})                   # one symbol at index 0
    cases.append({29: 7})                  # one symbol at index 29 -> single-all-skip
    cases.append({284: 3})                 # one symbol at the top of the lit alphabet

    # BOTH builders, because they are now different functions with different jobs:
    # `table_for_counts` is the MODEL path (`recost`, `literal_only`) and
    # `authoring_table` is the WRITER path, and it is the writer's tables that reach an
    # archive. A shape either one implies must be one `build_table` accepts.
    bad = []
    n_tables = 0
    for optimal in (False, True):
        for counts in cases:
            builds = [G.table_for_counts(counts)]
            builds += [G.authoring_table(counts, k, optimal=optimal)
                       for k in ("lit", "dist")]
            for lens, (_l, pres, declared), note in builds:
                got = _rebuild(lens, declared, not any(pres), optimal)
                n_tables += 1
                if got != lens:
                    bad.append((optimal, note, declared, len(counts),
                                "refused" if got is None else "wrong lengths"))
    check(not bad,
          f"{n_tables} encoder tables serialized and rebuilt by gwdat.build_table",
          f"{len(bad)} failed: {bad[:4]}" if bad else
          "0 refusals, 0 length mismatches")

    # The three writer-path shapes named individually, because an aggregate hides which
    # one broke. LABELS RE-MEASURED 2026-08-19: the first two no longer declare 1 -- the
    # envelope policy lifts them to shapes retail attests, and the second cannot use a
    # zero-bit code at all.
    for label, counts, kind in (
            ("empty distance table -> all-skip declared 5, the shape retail rows "
             "8295..8306 carry", {}, "dist"),
            ("single distance symbol at index 0 -> a real 1-bit code plus a phantom "
             "neighbour, declared 5 (the all-skip fallback can only install "
             "declared - 1, gwdat.py:265-267)", {0: 5}, "dist"),
            ("single distance symbol at index 29 -> the all-skip fallback unchanged, "
             "declared 30", {29: 5}, "dist")):
        lens, (_l, pres, declared), note = G.authoring_table(counts, kind)
        got = _rebuild(lens, declared, not any(pres), False)
        check(got == lens, f"{label} rebuilds to the intended lengths",
              f"intended {lens}, got {got}")

    # SABOTAGE: widen one meta token by one bit. If this is not caught, section 2 is
    # not measuring the meta encoding at all.
    caught = 0
    tried = 0
    for counts in cases[:60]:
        lens, (_l, pres, declared), note = G.authoring_table(counts, "lit")
        if len(lens) < 3:
            continue
        tried += 1
        got = _rebuild(lens, declared, not any(pres), False, widen=0)
        if got != lens:
            caught += 1
    check(tried and caught == tried,
          "SABOTAGE: one meta token emitted one bit too wide is caught every time",
          f"{caught}/{tried} rebuilt to different lengths or were refused")


# --------------------------------------------------------------------------
# section 3 -- B2, the round trip, on adversarial synthetics
# --------------------------------------------------------------------------

def section3(check):
    print("\n[3] B2 ROUND TRIP -- gwdat.decompress(encode(p)) == p, on synthetics")
    print("    (proves agreement with OUR decoder, not correctness -- gwdat.py:81-84)")
    results = []
    for name, payload, kw in synthetic_payloads():
        t0 = time.perf_counter()
        try:
            data = E.encode(payload, verify=False, **kw)
            back, declared = gwdat.decompress(data)
            ok = back == payload and declared == len(payload)
            note = (f"{len(payload):,} B -> {len(data):,} B" if ok else
                    f"{len(payload):,} B in, {len(back):,} B back, "
                    f"declared {declared:,}")
        except Exception as exc:                          # noqa: BLE001
            ok, note, data = False, f"raised {type(exc).__name__}: {exc}", None
        dt = time.perf_counter() - t0
        check(ok, f"round trip: {name}", note + f"  {dt:.1f}s")
        results.append((name, payload, kw, data))

    # The fixture that used to sit at the top of the corpus is now a REFUSAL. A
    # zero-byte payload tokenizes to no granules, so `build_stream` emits no blocks and
    # the writer produces 12 B of prologue and epilogue -- a shape no retail comp-8 row
    # has (the smallest is 56 B and holds a block), and one `datwrite.declaration_fault`
    # accepts today, so it can reach an archive. A refusal check is its own witness: it
    # needs no sabotage twin, because the thing it asserts is that a call FAILS.
    refused = None
    try:
        E.encode(b"")
    except ValueError as exc:
        refused = str(exc)
    check(refused is not None and "zero-byte" in refused,
          "encode(b'') is REFUSED, naming why -- gap D of FINDINGS §13.5",
          refused.split(":")[0] if refused else "it returned bytes instead")

    # The window edge must be REACHED, not merely survived: a matcher that never emits
    # distance 32,768 leaves this section testing nothing about the format's edge.
    payload = {n: p for n, p, _k in synthetic_payloads()}["window edge 32768"]
    st, _cfg = MM.build_stream(payload, q=9)
    best = 0
    for b in st.blocks:
        di = ei = 0
        for code in b.lit_syms:
            if code < 256:
                continue
            dsym = b.dist_syms[di]
            best = max(best, (gwdat.DISTANCE_BASE[dsym] | b.extra_vals[ei + 1]) + 1)
            di += 1
            ei += 2
    check(best == MM.WINDOW,
          f"the window-edge payload really does emit a distance of {MM.WINDOW}",
          f"largest distance emitted {best}")
    return results


# --------------------------------------------------------------------------
# section 4 -- B3, the size closure
# --------------------------------------------------------------------------

def section4(check, rows_data, ar=None):
    print("\n[4] B3 SIZE CLOSURE -- the writer's real bit count against the cost model")
    worst = None
    n = 0
    bad = []
    for name, payload, kw in synthetic_payloads():
        q = kw.get("quality", MM.DEFAULT_Q)
        st, _cfg = MM.build_stream(payload, q=q, uniform=kw.get("uniform"))
        data, consumed = E.emit_stream_counted(st, optimal=True)
        n += 1
        d_bits = consumed - st.final_bitpos
        d_bytes = len(data) - G.framing_bytes(st.final_bitpos)
        if d_bits or d_bytes:
            bad.append((name, d_bits, d_bytes))
        if worst is None or abs(d_bits) > abs(worst[1]):
            worst = (name, d_bits)
    check(not bad, f"our own encoder: emitted bits == predicted bits on {n} synthetics",
          f"worst delta {worst[1]:+} bits ({worst[0]})" if not bad else str(bad[:4]))

    if not rows_data:
        return
    bad = []
    for row, data in rows_data:
        _payload, st = G.trace(data, keep_streams=True)
        out, consumed = E.emit_stream_counted(st, optimal=False)
        if consumed != st.final_bitpos or len(out) != G.framing_bytes(st.final_bitpos):
            bad.append((row, consumed - st.final_bitpos,
                        len(out) - G.framing_bytes(st.final_bitpos)))
    check(not bad,
          f"re-emission: emitted bits == the traced bit position on {len(rows_data)} "
          "real rows", f"{len(bad)} disagree: {bad[:4]}" if bad else "all 0")

    if ar is None:
        return
    # SABOTAGE, and it is the trap gwenc's docstring is about. `gwmatch` plans with the
    # meta DP; a writer hardcoding retail's greedy emits MORE bits than the planner
    # charged, and the stream stays perfectly decodable -- so nothing except this
    # comparison notices. Most rows would not demonstrate it: greedy and the DP agree
    # exactly on row 11196's 218 tables. PLAN_FLAG_ROW is pinned because it does not.
    payload = ar.read(ar.row(PLAN_FLAG_ROW))
    st, _cfg = MM.build_stream(payload, q=8, optimal=True)
    _right, c_right = E.emit_stream_counted(st, optimal=True)
    wrong, c_wrong = E.emit_stream_counted(st, optimal=False)
    back, _d = gwdat.decompress(wrong)
    check(c_right == st.final_bitpos and c_wrong > st.final_bitpos and back == payload,
          f"SABOTAGE: on row {PLAN_FLAG_ROW} a writer using the WRONG meta plan emits "
          "more bits than the planner charged, and B3 is the only thing that sees it",
          f"correct flag {c_right - st.final_bitpos:+} bits, wrong flag "
          f"{c_wrong - st.final_bitpos:+} bits, wrong-flag stream still decodes: "
          f"{back == payload}")


# --------------------------------------------------------------------------
# section 5 -- B1, byte-identical re-emission over a drawn population
# --------------------------------------------------------------------------

def draw_rows(ar, per_band, seed=SEED):
    """The stated, reproducible B1 rule. -> (list of rows, per-band lists).

    Walk EVERY row of the archive in row order (`ar.row(n)`, never `ar.entries[n]` --
    correction C-8), keep the compression-8 ones, bucket them by stored size into
    `BANDS`, and sample each bucket with `random.Random(seed)`. Then add the pinned
    sets: the three anchors, `gwentropy.WITNESS`, and the four zero-length-table rows.
    De-duplicated, so the reported count is DISTINCT rows.
    """
    buckets = [[] for _ in BANDS]
    for i in range(1, ar.row_count):
        e = ar.row(i)
        if e.compression != 8 or e.size < 8:
            continue
        for bi, (lo, hi) in enumerate(BANDS):
            if lo <= e.size < hi:
                buckets[bi].append(i)
                break
    rng = random.Random(seed)
    per = []
    for bi, b in enumerate(buckets):
        k = min(per_band[bi], len(b))
        per.append(sorted(rng.sample(b, k)) if k else [])
    pinned = sorted(set(G.ANCHORS) | set(G.WITNESS) | set(ZERO_LEN_ROWS))
    seen = set()
    out = []
    for group in per + [pinned]:
        for r in group:
            if r not in seen:
                seen.add(r)
                out.append(r)
    return out, per, pinned


def section5(check, ar, per_band):
    print("\n[5] B1 BYTE-IDENTICAL RE-EMISSION OF RETAIL'S OWN ROWS")
    print("    The only check here that does not assume gwdat is a correct decoder.")
    rows, per, pinned = draw_rows(ar, per_band)
    print(f"    rule: every comp-8 row, bucketed by stored size, sampled with "
          f"random.Random({SEED}); + anchors + WITNESS + the zero-length rows")

    results = {}
    failures = []
    total_bytes = 0
    t0 = time.perf_counter()
    for row in rows:
        e = ar.row(row)
        data = ar.raw(e)
        try:
            out, _st, _bits = E.reemit(data)
            same = out == data
            crc_ok = (zlib.crc32(out) & M32) == e.crc
            cls = "ok" if (same and crc_ok) else (
                "bytes differ" if not same else "crc differs")
        except Exception as exc:                          # noqa: BLE001
            same = crc_ok = False
            cls = f"raised {type(exc).__name__}"
        results[row] = (same and crc_ok, cls, e.size)
        total_bytes += e.size
        if not (same and crc_ok):
            failures.append((row, e.size, cls))
    dt = time.perf_counter() - t0

    for bi, group in enumerate(per):
        if not group:
            continue
        bad = [r for r in group if not results[r][0]]
        check(not bad, f"band {BAND_NAMES[bi]}: {len(group)} rows byte-identical",
              f"FAILED {bad[:6]}" if bad else "")
    bad = [r for r in pinned if not results[r][0]]
    check(not bad,
          f"pinned set (anchors + WITNESS + zero-length rows): {len(pinned)} rows",
          f"FAILED {bad[:6]}" if bad else "")
    bad = [r for r in ZERO_LEN_ROWS if not results[r][0]]
    check(not bad,
          "the four rows carrying the divergent zero-length distance table re-emit "
          "byte-identically", f"FAILED {bad}" if bad else str(ZERO_LEN_ROWS))
    check(not failures,
          f"TOTAL: {len(rows)} distinct rows, {total_bytes:,} B, byte-identical with "
          f"crc32 == the MFT's own value",
          f"{len(failures)} FAILED, by class: "
          f"{sorted(set(c for _r, _s, c in failures))}" if failures else f"{dt:.0f}s")
    check(len(rows) >= 150,
          "the drawn population is large enough to be evidence",
          f"{len(rows)} rows (--per-band moves this; --quick shrinks it on purpose)")
    return rows, failures


# --------------------------------------------------------------------------
# section 6 -- the deliberate breakages
# --------------------------------------------------------------------------

def section6(check, ar):
    print("\n[6] CONTROLS -- each of these MUST change the bytes, or the section above "
          "is not measuring what it claims")
    e = ar.row(13738)                # the shell row: small enough to break six ways fast
    disk = ar.raw(e)
    payload = ar.read(e)

    # (a) the tail word. gwdat never consumes it, so the payload survives -- which is
    # exactly why byte-identity and not decodability is what pins it.
    out, _st, _b = E.reemit(disk, tail_word=0xDEADBEEF)
    back, _d = gwdat.decompress(out)
    check(out != disk, "(a) tail word 0xDEADBEEF instead of 0x80010008 changes the bytes")
    check(back == payload,
          "(a) ... and the payload still decodes identically -- gwdat NEVER consumes "
          "the look-ahead word, so it is pinned by retail's bytes and nothing else")

    # (b) the pad bits. Free bits that retail chose to be zero.
    out, _st, _b = E.reemit(disk, pad_bit=1)
    back, _d = gwdat.decompress(out)
    check(out != disk, "(b) pad bits written as ones changes the bytes")
    check(back == payload, "(b) ... and the payload still decodes identically")

    # (c) THE IMPORTANT ONE. Retail's table encoder is longest-run greedy (A6, bit-exact
    # on 2,194/2,194 tables). Our DP is a legal, SMALLER, different stream.
    d2 = ar.raw(ar.row(DP_BEATS_GREEDY_ROW))
    p2 = ar.read(ar.row(DP_BEATS_GREEDY_ROW))
    greedy, _st, _b = E.reemit(d2, optimal=False)
    dp, _st, _b = E.reemit(d2, optimal=True)
    back, _d = gwdat.decompress(dp)
    check(greedy == d2, f"(c) row {DP_BEATS_GREEDY_ROW}: greedy meta plan IS retail's "
                        f"bytes", f"{len(d2):,} B")
    check(dp != d2,
          "(c) the OPTIMAL meta plan is NOT retail's bytes -- A6's 'retail's table "
          "encoder is greedy' is load-bearing here",
          f"DP {len(dp):,} B vs retail {len(d2):,} B")
    check(back == p2,
          "(c) ... and the DP stream is still a VALID stream, so this is a real "
          "valid-but-different parse and not a corruption")

    # (d) THE FRAMING, and it took two attempts to state correctly. `BitReader` reads
    # over the WHOLE stored row, trailer included -- it has no idea the last four bytes
    # are the uncompressed size. So dropping the sentinel word alone does not starve it:
    # the u32 trailer slides into the look-ahead slot and the payload is unaffected.
    # Truncation begins one word LATER, and when it does it is silent.
    good, _st, _b = E.reemit(disk)
    no_tail = good[:-8] + good[-4:]                # sentinel word gone, trailer kept
    back, _d = gwdat.decompress(no_tail)
    check(back == payload,
          "(d1) dropping the look-ahead word ENTIRELY still decodes -- the u32 trailer "
          "slides into the slot, so gwdat does not need the sentinel at all",
          f"{len(no_tail):,} B vs {len(good):,} B, payload identical")
    starved = good[:-12] + good[-4:]               # one word short even counting that
    back, _d = gwdat.decompress(starved)
    check(back != payload and len(back) < len(payload),
          "(d2) one word shorter again and the decode TRUNCATES SILENTLY -- no raise, "
          "no short-read signal, just fewer bytes and a row that passes every "
          "checksum rule",
          f"{len(back):,} of {len(payload):,} B, {len(payload) - len(back)} lost")


# --------------------------------------------------------------------------
# section 7 -- the anchor, row 11196
# --------------------------------------------------------------------------

def section7(check, ar):
    print(f"\n[7] THE ANCHOR -- row {ANCHOR}, the row the whole arc is about")
    e = ar.row(ANCHOR)
    disk = ar.raw(e)
    payload = ar.read(e)

    t0 = time.perf_counter()
    out, st, consumed = E.reemit(disk)
    t_re = time.perf_counter() - t0
    check(out == disk,
          f"B1: row {ANCHOR} re-emitted BYTE-IDENTICALLY from its own trace",
          f"{len(out):,} B in {t_re:.1f}s")
    check((zlib.crc32(out) & M32) == e.crc,
          "B1: crc32 of our bytes == the MFT's own recorded crc",
          f"{zlib.crc32(out) & M32:#010x} vs {e.crc:#010x}")
    check(consumed == st.final_bitpos,
          "B3: the writer consumed exactly the traced bit count",
          f"{consumed:,} vs {st.final_bitpos:,}")

    t0 = time.perf_counter()
    r = E.encode_report(payload, quality=8, optimal=True, verify=True)
    t_enc = time.perf_counter() - t0
    check(r["round_trip"] is True,
          f"B2: our own encoder's {r['stored']:,} B round-trips through "
          f"gwdat.decompress", f"{len(payload):,} B payload, {t_enc:.1f}s")
    check(r["stored"] == r["predicted"],
          "B3: the writer's byte count == gwmatch/gwentropy's predicted byte count",
          f"{r['stored']:,} vs {r['predicted']:,}  delta "
          f"{r['stored'] - r['predicted']:+}")
    check(r["stored"] == ANCHOR_A7A_PREDICTION,
          f"the emitted size is A7a's modelled {ANCHOR_A7A_PREDICTION:,} B TO THE BYTE",
          f"got {r['stored']:,}  ({r['blocks']} blocks, "
          f"{2 * r['blocks']} tables through build_table)")
    check(r["crc32"] == ANCHOR_ENCODED_CRC,
          "and they are the SAME BYTES the client accepted -- crc32 pinned, not just "
          "the size",
          f"{r['crc32']:#010x} vs the pinned {ANCHOR_ENCODED_CRC:#010x}")
    check(r["stored"] <= ANCHOR_RESERVATION,
          f"and it fits the {ANCHOR_RESERVATION:,} B reservation "
          f"(TRAILER-INCLUSIVE)",
          f"{ANCHOR_RESERVATION - r['stored']:,} B of slack, against retail's 68 B")


# --------------------------------------------------------------------------
# section 8 -- the envelope: only shapes retail's own archive attests
# --------------------------------------------------------------------------

def envelope_faults(blocks):
    """Every way a stream's emitted tables leave retail's attested envelope.

    -> list of `(block index, kind, complaint, declared)`; empty is clean. The four
    rules, each with the population that attests it (`gwentropy.authoring_table` carries
    the census, `studies/archivewrite/FINDINGS.md` §13.5 the gaps they close):

      * declared >= 2 -- gap A. 0 of 138,708 retail rows declare fewer.
      * declared >= the kind's floor -- distance 5 (min over 32,831 comp-8 rows of
        <= 2,048 B), literal 257 (the minimum of the 218 tables in the row the retail
        client read in A8, §16.2).
      * no zero-length LITERAL table -- gap B. 0 of those 32,831 rows has one.
      * a zero-length DISTANCE table must be the ALL-SKIP shape, `{declared - 1: 0}`.
        That is the only thing `gwdat.py:265-267`'s `total == 0` fallback can install,
        and it is bit-for-bit what rows 8295..8306 carry. A zero-length table naming any
        other symbol is a writer and a decoder that disagree.

    This reads the BLOCK FIELDS the writer emits from (`gwenc.py:367-368`), not
    `authoring_table`'s return value, so a fault between the table BUILDER and the
    block is in range. It is not a whole-pipeline check: it reads upstream of the
    bit-packing, and an emission bug below that is caught by the round-trip checks
    rather than by this sweep.
    """
    out = []
    for b in blocks:
        for kind, lens, declared, zero in (
                ("lit", b.lit_lens, b.lit_symbol_count, b.lit_zero),
                ("dist", b.dist_lens, b.dist_symbol_count, b.dist_zero)):
            floor = G.LITERAL_FLOOR if kind == "lit" else G.DISTANCE_FLOOR
            if declared < 2:
                out.append((b.index, kind, "declared < 2, which no retail row is",
                            declared))
            elif declared < floor:
                out.append((b.index, kind,
                            f"declared under the attested {kind} floor of {floor}",
                            declared))
            if zero and kind != "dist":
                out.append((b.index, kind,
                            "a zero-length LITERAL table, 0 of 32,831 retail rows",
                            declared))
            elif zero and sorted(lens.items()) != [(declared - 1, 0)]:
                out.append((b.index, kind,
                            f"zero-length but not the all-skip shape {{{declared - 1}: "
                            f"0}} -- {sorted(lens.items())}", declared))
    return out


def _fake_block(index, lit_n, dist_n, lit_zero=False, dist_zero=False,
                lit_lens=None, dist_lens=None):
    """A BlockTrace carrying nothing but the six fields `envelope_faults` reads."""
    b = G.BlockTrace()
    b.index = index
    b.lit_symbol_count = lit_n
    b.dist_symbol_count = dist_n
    b.lit_zero = lit_zero
    b.dist_zero = dist_zero
    b.lit_lens = lit_lens if lit_lens is not None else {0: 1, 1: 1}
    b.dist_lens = dist_lens if dist_lens is not None else {0: 1, 1: 1}
    return b


def section8(check):
    print("\n[8] THE ENVELOPE -- every table we emit is a shape retail's archive or the "
          "A8 client run attests")
    print("    (closes FINDINGS §13.5 gaps A, B and the distance half of C; E is "
          "accepted, gwenc's docstring says why)")

    faults = []
    n_tables = 0
    n_blocks = 0
    for name, payload, kw in synthetic_payloads():
        st, _cfg = MM.build_stream(payload, q=kw.get("quality", MM.DEFAULT_Q),
                                   uniform=kw.get("uniform"))
        for f in envelope_faults(st.blocks):
            faults.append((name,) + f)
        n_blocks += len(st.blocks)
        n_tables += 2 * len(st.blocks)
    check(not faults,
          f"{n_tables} tables over the whole synthetic corpus are inside the envelope",
          f"{len(faults)} outside: {faults[:4]}" if faults else
          f"{n_blocks} blocks, declared lit >= {G.LITERAL_FLOOR}, dist >= "
          f"{G.DISTANCE_FLOOR}, no zero-length literal table")
    # `--per-band` cannot shrink this one, but a corpus that stopped building streams
    # would sweep nothing and pass. The count is the check that refuses that.
    check(n_tables >= 60,
          "the sweep really inspected the corpus rather than an empty list",
          f"{n_tables} tables from {n_blocks} blocks")

    # SABOTAGE. Four planted faults, one per rule, each of which MUST be named -- and a
    # clean block alongside them, so "flags everything" cannot pass either.
    planted = [
        ("declared 1", _fake_block(0, 257, 1)),
        ("distance declared 3", _fake_block(1, 257, 3)),
        ("literal declared 200", _fake_block(2, 200, 5)),
        ("zero-length LITERAL table", _fake_block(3, 257, 5, lit_zero=True,
                                                  lit_lens={256: 0})),
        ("zero-length distance table naming the wrong symbol",
         _fake_block(4, 257, 5, dist_zero=True, dist_lens={2: 0})),
    ]
    missed = [label for label, b in planted if not envelope_faults([b])]
    clean = _fake_block(9, 257, 5)
    check(not missed and not envelope_faults([clean]),
          f"SABOTAGE: {len(planted)} planted envelope faults are each flagged, and a "
          "clean block is not",
          f"missed {missed}" if missed else
          f"flagged {len(planted)}/{len(planted)}, clean block 0 faults")

    # SABOTAGE, second arm, and it is the one that matters: the check above proves the
    # CHECKER can fail when handed a bad block, not that the sweep is WIRED to the real
    # encoder. So put the pre-envelope builder back -- `table_for_counts`, which is what
    # `gwmatch._fit_table` called until 2026-08-19 -- for one fixture, in memory, and
    # require the sweep to name the gaps it reintroduces. `b"A"` reached three at once:
    # a distance table declared 1 (gap A), a literal table declared 66 (gap C) and
    # that literal table being zero-length (gap B).
    real = G.authoring_table
    try:
        G.authoring_table = (lambda counts, kind, optimal=True:
                             G.table_for_counts(counts))
        st, _cfg = MM.build_stream(b"A")
        regressed = envelope_faults(st.blocks)
    finally:
        G.authoring_table = real
    kinds = {(f[1], f[2].split(",")[0]) for f in regressed}
    check(any(f[3] < 2 for f in regressed) and len(kinds) >= 3,
          "SABOTAGE: with the pre-envelope table builder restored the sweep goes RED, "
          "so it is measuring the encoder and not only itself",
          f"{len(regressed)} faults on b'A': {sorted(kinds)}")


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--per-band", type=int, nargs=5, default=None,
                    help=f"rows sampled per stored-size band (default {PER_BAND})")
    ap.add_argument("--quick", action="store_true",
                    help="a much smaller B1 draw; reddens the population check on "
                         "purpose")
    args = ap.parse_args()
    per_band = args.per_band or (QUICK_PER_BAND if args.quick else PER_BAND)

    # FLOOR 60, set from the real green run of 2026-08-19 in this worktree, ZERO
    # HEADROOM. Sections 1, 2, 3, 8 and section 4's synthetic arm need no archive and run
    # 6 + 5 + 16 + 4 + 1 = 32; with the archive, section 5 adds 9, section 4's real-row
    # and sabotage arms 2, section 6 adds 9 and section 7 adds 8.
    #
    # It was 55 until the envelope work of 2026-08-19: section 8 is new (4), section 7
    # gained the pinned crc32 of our own anchor bytes (1), and section 3 held its count
    # because the `empty` fixture became the refusal check that replaced it.
    #
    # ONE floor, not two, so a bare run goes RED rather than green-with-a-skip. That is
    # deliberate and it is the same verdict `test_gwentropy.py` and `test_gwmatch.py`
    # give: without the archive, B1 -- the only check in this file that does not assume
    # `gwdat` is a correct decoder -- never runs, and a run reporting ALL CHECKS PASSED
    # on the strength of the checks that DO assume it is exactly the "converts we do not
    # know into we verified" failure `checks.py` exists to refuse.
    #
    # `--per-band` and `--quick` move how many ROWS section 5 re-emits and NOT how many
    # checks it runs, which is the shape that let `test_movement_fidelity.py` go green
    # on n=2. So the row count is itself the last check of section 5, and `--quick`
    # reddens it on purpose: a shrunk B1 draw is a weaker run and must not report as a
    # full one.
    have_dat = os.path.exists(args.dat)
    led = checks.Ledger("gwenc -- the A7b bitstream writer", floor=60)
    check = checks.adopt(led)

    print(f"A7b bitstream writer. TRAILER-INCLUSIVE bytes; tail word "
          f"{E.TAIL_WORD:#010x}; gwdat is OUR decoder (gwdat.py:81-84).")

    section1(check)
    section2(check)
    section3(check)
    section8(check)

    if not have_dat:
        led.skip("sections 4 (real rows), 5, 6 and 7",
                 f"no archive at {args.dat}; B1 -- the only check that does not assume "
                 "gwdat is correct -- cannot run, so this run proves much less")
        section4(check, [])
        return led.verdict()

    with Archive(args.dat) as ar:
        rows, _failures = section5(check, ar, per_band)
        # section 4's real-row arm reuses a slice of section 5's draw rather than
        # re-drawing, so the two sections cannot disagree about the population
        sample = [r for r in rows if ar.row(r).size < 200000][:60]
        section4(check, [(r, ar.raw(ar.row(r))) for r in sample], ar=ar)
        section6(check, ar)
        section7(check, ar)

    return led.verdict()


if __name__ == "__main__":
    sys.exit(main())
