#!/usr/bin/env python3
"""Check `atex.decode_level` -- the ATEX level codec, solved 2026-08-14.

    python toolkit/mapdata/test_atexlevel.py
    python toolkit/mapdata/test_atexlevel.py --all      # a wider corpus sweep

Kept apart from `test_atex.py`, which owns the CONTAINER (the record walk,
`build`, the write guards). This file owns the CODEC: the bit rack, the run
table, the four run-coded passes, and the planar residual.

WHAT IS NOT EVIDENCE HERE, and it is the first thing to say because it is the
headline a careless version of this file would print. `decode_level`
allocates its output as `blocks * block_dwords` and returns exactly that, so
**"19,175 levels produced the right number of bytes" is TRUE BY
CONSTRUCTION** -- a decoder that returns all zeros passes it, and so does one
that reads the passes wrongly and lets the residual fill the gaps. The size
check is kept (it catches a walk that raises or runs off) but it is scored as
the weak half and every load-bearing claim below is something ArenaNet's own
bytes can refute.

THE LOAD-BEARING CHECK IS SECTION 6, and it is the strongest oracle this
codec admits: **a CODED level sitting next to a RAW one**. A `code == 0`
level needs no pass logic at all -- it is the planar copy -- so it is ground
truth we are confident in independently, and mip level k+1 is a downsample of
level k. Decoding a coded level k and comparing it against its raw
neighbour therefore tests the PASS logic specifically, against data no part
of this decoder produced. 2,657 such pairs exist in the sampled archive.

**THE ORACLE MUST BE FORMAT-AWARE, and that is a measurement this file paid
for.** The first version scored every 8-byte-block format as DXT1-style
colour, and DXTA came back at median 59.19 against a null of 59.88 -- i.e.
indistinguishable from noise, which read as "the decoder is broken for 349 of
1,533 containers". It is not: **DXTA has NO COLOUR HALF** (`s_formatFlags`
0x00A1 fails the 0x210 test), so its 8 bytes are an alpha block and the
oracle was reading alpha as colour. Scored on the channel it actually has,
DXTA is median 2.36 with 472 of 474 under 8. The decoder was right and the
MEASUREMENT was wrong, which is why section 2 pins `has_colour` per format
as its own check -- that fact is load-bearing for anything that consumes a
decoded level.

THE MIP ORACLE'S LIMIT, stated rather than left implicit: a mip level is not
required to be an exact 2x2 box filter of its parent, so the comparison has a
long tail (worst 139 over 2,657 pairs) and the check is on the MEDIAN and the
fraction under a threshold, never on the max. The null -- the same coded
level against a DIFFERENT texture's raw level -- is what gives the median its
meaning: 4.76 against 59.88.

SECTIONS 0-4 NEED NO VAULT. They build containers byte by byte, including
CODED ones, which is what lets the pass logic be checked on a bare machine:
section 3 hand-encodes a flat-colour run through the client's own run table
and requires the exact block `solid_colour_block` computes.

THE SABOTAGE MATRIX, built and run 2026-08-14 (one-edit copies of `atex.py`,
this file run against each at `--rows 1200`):

    sabotage                                   checks reddened
    rack reads LSB-first                             12
    literal cursor not backed up one dword            7
    run pass ignores the flag bit                     6
    run table: every run is 1                         5
    residual not de-interleaved (file order)          4
    two-bit selector ignored (always arm 1)           3
    DXTA given a colour half                          3
    skipped blocks SPEND run                          2   <- see below
    flat colour: naive nearest-565                    2   <- see below

**The last two reddened NOTHING on the first pass and the file was changed
because of it, which is the only reason they are worth listing.**

  * *Skipped blocks spend run* was invisible because the alpha passes run
    FIRST, when the colour bitmap is still empty, so the skip path is dead on
    almost every real level -- code 9 (two colour-side passes) occurs 4 times
    in the whole sampled corpus. No corpus median could ever have caught it.
    Section 3(f) now builds a two-pass level by hand.
  * *Naive nearest-565* was invisible because the tolerance was one full 565
    quantum (8), which admits both quantisers. The client's picks two
    endpoints and an interpolated index and reaches worst-4 where naive is
    worst-7, so the bound is now 4 and the naive version is REPRODUCED as a
    live function and required to miss it.

One sabotage still reddens nothing and it is not a gap: dropping the
transparent pass's marking of the ALPHA bitmap. Bit 0's gate is "has colour
and not alpha", so that store can never be read back. Section 2 asserts the
gate instead, so the day a format makes it reachable this file says so.
"""

import argparse
import collections
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks                                                    # noqa: E402
import atex                                                      # noqa: E402
import dxt1                                                      # noqa: E402

# MEASURED from green runs, 2026-08-14: 63 with `vault/dat_study/Gw.dat` and
# a client image, 48 with NEITHER (sections 0-4, which build every container
# they use). The floor is the full number on purpose -- the synthetic half
# cannot refute anything about ArenaNet's own bytes, so a vault-less run is
# INCOMPLETE rather than passing, and says so.
LEDGER = checks.Ledger("atex level codec", floor=63)
check = checks.adopt(LEDGER)

#: MEASURED 2026-08-14 over the first 12,000 MFT rows of the study archive.
#: Medians of the coded-vs-raw oracle, per (fourcc, code). Pinned as
#: THRESHOLDS rather than as exact values -- the sample size moves with
#: `--all` and a median is not a count.
ORACLE_MAX_MEDIAN = 8.0
#: The null must be far worse. 59.88 vs 4.76 measured; 3x is a wide margin
#: that still fails instantly if the oracle stops discriminating.
ORACLE_NULL_RATIO = 3.0

#: Per-format block strides, in BYTES. From the client's `s_formatFlags`, and
#: independently confirmed by the corpus (`test_dxt1.py` records the same
#: 8/16 split from payload arithmetic).
STRIDES = {b"DXT1": 8, b"DXT2": 16, b"DXT3": 16, b"DXT4": 16, b"DXT5": 16,
           b"DXTA": 8, b"DXTL": 16, b"DXTN": 16}

#: The formats with NO colour half. This is the fact that fooled this file's
#: own first oracle; see the docstring.
NO_COLOUR = {b"DXTA"}


# ---------------------------------------------------------------- fixtures

class BitWriter:
    """MSB-first into little-endian u32 words -- the `Rack`'s convention.

    Written here rather than imported: a writer built out of the reader's own
    helpers could not catch the reader disagreeing with ArenaNet.
    """

    def __init__(self):
        self.bits = []

    def put(self, value, n):
        for k in range(n - 1, -1, -1):
            self.bits.append((value >> k) & 1)
        return self

    def run(self, length):
        """Encode a run length through the client's 3-symbol prefix code."""
        if length == 1:
            return self.put(1, 1)
        if length == 18:
            return self.put(0b01, 2)
        if not 2 <= length <= 17:
            raise ValueError(f"run {length} is not encodable")
        return self.put(0, 2).put(17 - length, 4)

    def bytes(self):
        bits = list(self.bits) + [0] * ((-len(self.bits)) % 32)
        out = bytearray()
        for i in range(0, len(bits), 32):
            word = 0
            for k in range(32):
                word |= bits[i + k] << (31 - k)
            out += struct.pack("<I", word)
        return bytes(out)


def container(fourcc, width, height, levels):
    """An ATEX container built byte by byte. `levels` is [(code, payload)]."""
    out = bytearray(b"ATEX" + fourcc + struct.pack("<HH", width, height))
    for code, payload in levels:
        out += struct.pack("<II", atex.RECORD_SIZE + len(payload), code)
        out += payload
    return bytes(out)


# --- 0. the run table -----------------------------------------------------

def section_runtable():
    print("\n== 0. the run table at VA 0x00A5E620 ==")
    check(len(atex.RUN_TABLE) == 64,
          "the table has 64 entries, one per 6-bit peek",
          f"{len(atex.RUN_TABLE)}")

    # The three-symbol structure, asserted as the closed form the module
    # documents. If a future build changes the table this goes red and names
    # which arm moved.
    bad = []
    for top6, (code_len, minus_one) in enumerate(atex.RUN_TABLE):
        if top6 < 16:
            want = (6, 16 - top6)
        elif top6 < 32:
            want = (2, 17)
        else:
            want = (1, 0)
        if (code_len, minus_one) != want:
            bad.append((top6, (code_len, minus_one), want))
    check(not bad,
          "every entry matches the closed form: '1' -> run 1, '01' -> run 18, "
          "'00vvvv' -> runs 17 down to 2", f"{bad[:3]}")

    # A PREFIX CODE has to be decodable: no entry's bit pattern may be a
    # prefix of another's. Checked by construction -- the three arms are
    # distinguished by the top bits.
    lengths = {atex.RUN_TABLE[t][0] for t in range(64)}
    check(lengths == {1, 2, 6},
          "only three code lengths occur (1, 2, 6) -- a 3-symbol code",
          f"{sorted(lengths)}")
    runs = {atex.RUN_TABLE[t][1] + 1 for t in range(64)}
    check(min(runs) == 1 and max(runs) == 18 and len(runs) == 18,
          "the runs it can express are exactly 1..18", f"{len(runs)} values")


# --- 1. the bit rack ------------------------------------------------------

def section_rack():
    print("\n== 1. the CmpIo bit rack ==")
    # 0x12345678 little-endian; MSB-first reading takes 0x1, then 0x2, ...
    words = list(struct.unpack("<2I", struct.pack("<2I", 0x12345678,
                                                  0x9ABCDEF0)))
    rack = atex.Rack(words)
    got = [rack.read(4) for _ in range(8)]
    check(got == [1, 2, 3, 4, 5, 6, 7, 8],
          "reads MSB-first WITHIN a little-endian dword", f"{got}")
    more = [rack.read(4) for _ in range(8)]
    check(more == [9, 0xA, 0xB, 0xC, 0xD, 0xE, 0xF, 0],
          "and continues into the next word without losing a bit", f"{more}")

    rack = atex.Rack([0xFFFFFFFF])
    check(rack.peek6() == 0x3F, "peek6 returns the top six bits",
          f"{rack.peek6():#x}")
    rack.read(30)
    # Two ones survive at the top and the refill brought in zeros, so the
    # six-bit window is 0b110000. (0b111100 would mean the rack invented two
    # more set bits past the end of its only word.)
    check(rack.peek6() == 0x30,
          "peek6 tracks consumption (30 bits in, 2 ones left at the top)",
          f"{rack.peek6():#x}")

    # PAST THE END the client reads ZEROS rather than raising, and `dry`
    # counts it. Several real levels finish with a run still nominally in
    # progress, so a raising reader would refuse valid data.
    #
    # `dry` counts REFILL ATTEMPTS, not bad values: the constructor primes
    # `hi` from word 0, so a rack that consumes its only word has already
    # tried once to refill and reports 1 while every bit it returned was
    # real. That distinction is worth pinning -- a caller using `dry` as
    # "this level was starved" must allow one.
    rack = atex.Rack([0xFFFFFFFF])
    got = rack.read(32)
    check(got == 0xFFFFFFFF and rack.dry == 1,
          "consuming the only word returns REAL bits and counts one refill "
          "attempt -- dry is attempts, not bad reads",
          f"{got:#x}, dry={rack.dry}")
    tail = [rack.read(8) for _ in range(3)]
    check(tail == [0, 0, 0] and rack.dry == 4,
          "and reading past the end yields zeros, one count each",
          f"{tail}, dry={rack.dry}")

    check(atex.Rack([]).read(8) == 0,
          "an empty rack reads zero rather than raising")

    # The run reader consumes exactly what the table says.
    rack = atex.Rack(BitWriter().run(1).run(18).run(5).put(0, 8).bytes()
                     and list(struct.unpack(
                         "<%dI" % (len(BitWriter().run(1).run(18).run(5)
                                       .put(0, 8).bytes()) // 4),
                         BitWriter().run(1).run(18).run(5).put(0, 8).bytes())))
    got = [rack.run(), rack.run(), rack.run()]
    check(got == [1, 18, 5],
          "run() round-trips the three encodable shapes", f"{got}")


# --- 2. per-format block layout -------------------------------------------

def section_layout():
    print("\n== 2. block layout per format ==")
    for fourcc, want in sorted(STRIDES.items()):
        block_dw, _off, _ha, _hc, _fmt = atex.block_layout(fourcc)
        check(block_dw * 4 == want,
              f"{fourcc.decode()} is {want} bytes per 4x4 block",
              f"{block_dw * 4}")

    # THE FACT THAT FOOLED THIS FILE'S OWN FIRST ORACLE. DXTA carries an
    # alpha block and NO colour half, so a consumer that assumes "8 bytes per
    # block means DXT1" reads its alpha as colour and gets noise.
    for fourcc in sorted(STRIDES):
        _bd, _off, _ha, has_colour, _fmt = atex.block_layout(fourcc)
        want = fourcc not in NO_COLOUR
        check(has_colour == want,
              f"{fourcc.decode()} has_colour is {want}",
              f"{has_colour}")

    # THE GATE THAT MAKES ONE STORE INERT, stated rather than left implicit.
    # The transparent pass marks BOTH coverage bitmaps, but its gate is
    # "has colour and NOT alpha", so the alpha bitmap it marks can never be
    # read back -- a sabotage dropping that store reddens nothing, and the
    # reason is this invariant rather than a hole in the tests. If a future
    # build lets bit 0 reach an alpha-carrying format, this goes red and the
    # store stops being dead.
    reachable = [fc for fc in sorted(STRIDES)
                 if atex.block_layout(fc)[3]           # has_colour
                 and not atex.block_layout(fc)[2]      # not has_alpha
                 and atex.block_layout(fc)[4] != 0x15]
    check(reachable == [b"DXT1"],
          "the transparent pass (bit 0) is reachable by DXT1 ALONE, which is "
          "why its alpha-bitmap marking is inert",
          f"{[f.decode() for f in reachable]}")

    try:
        atex.block_layout(b"NOPE")
        check(False, "an unknown fourcc is refused")
    except ValueError as exc:
        check("not an ATEX format" in str(exc),
              "an unknown fourcc is refused by name", str(exc)[:48])


# --- 3. synthetic CODED levels, on a bare machine -------------------------

def section_synthetic():
    print("\n== 3. hand-built levels -- coded and raw, no vault ==")

    # (a) code 0: the planar residual. One 8x4 DXT1 level is two blocks, so
    # the payload is [colour0][colour1][index0][index1] and the decode must
    # INTERLEAVE them back. A memcpy would return them in file order.
    payload = struct.pack("<4I", 0x11111111, 0x22222222, 0xAAAAAAAA,
                          0xBBBBBBBB)
    data = container(b"DXT1", 8, 4, [(0, payload)])
    blocks, stride = atex.decode_level(data, atex.parse(data), 0)
    got = struct.unpack("<4I", blocks)
    check(got == (0x11111111, 0xAAAAAAAA, 0x22222222, 0xBBBBBBBB)
          and stride == 8,
          "code 0 DE-INTERLEAVES two planes into per-block pairs",
          f"{[hex(v) for v in got]}")
    check(got != struct.unpack("<4I", payload),
          "and the result is NOT the payload in file order -- which is what "
          "a memcpy would return")

    # (b) code 8: the flat-colour pass. Hand-encode 24 bits of colour, then a
    # run of 1 with the flag set, and require the exact block the client's
    # own quantiser computes. This exercises the rack, the run table and the
    # pass without touching the archive.
    colour = 0x3366CC
    body = BitWriter().put(colour, 24).run(1).put(1, 1).bytes()
    data = container(b"DXT1", 4, 4, [(atex.PASS_FLAT_COLOUR, body)])
    blocks, _stride = atex.decode_level(data, atex.parse(data), 0)
    want = atex.solid_colour_block(0xFF000000 | colour, True)
    check(struct.unpack("<2I", blocks) == want,
          "code 8 stamps exactly the block solid_colour_block computes",
          f"{[hex(v) for v in struct.unpack('<2I', blocks)]}")

    # The colour really is the one asked for: decode the block and compare.
    c0, c1 = struct.unpack_from("<HH", blocks, 0)
    idx, = struct.unpack_from("<I", blocks, 4)
    texel = dxt1.decode_block(c0, c1, idx)[0]
    err = max(abs(texel[0] - 0x33), abs(texel[1] - 0x66), abs(texel[2] - 0xCC))
    check(err <= 8,
          "and that block really renders the requested colour (within one "
          "565 quantum)", f"max channel error {err}")

    # (c) code 8 with the flag CLEAR: the block falls through to the residual
    # instead. This is the arm that makes the pass a SELECTION rather than a
    # blanket fill, and a decoder ignoring the flag bit fails it.
    body = BitWriter().put(colour, 24).run(1).put(0, 1).bytes()
    literal = struct.pack("<2I", 0x0BADF00D, 0xFEEDFACE)
    data = container(b"DXT1", 4, 4, [(atex.PASS_FLAT_COLOUR, body + literal)])
    blocks, _stride = atex.decode_level(data, atex.parse(data), 0)
    got = struct.unpack("<2I", blocks)
    check(got == (0x0BADF00D, 0xFEEDFACE),
          "with the flag CLEAR the block comes from the literal residual, "
          "not from the flat colour", f"{[hex(v) for v in got]}")

    # (d) a MIXED level: two blocks, the first flat and the second literal.
    # Catches a pass that fills the whole grid regardless of run length.
    body = BitWriter().put(colour, 24).run(1).put(1, 1).run(1).put(0, 1)
    data = container(b"DXT1", 8, 4,
                     [(atex.PASS_FLAT_COLOUR,
                       body.bytes() + struct.pack("<2I", 0xC0FFEE00,
                                                  0x12345678))])
    blocks, _stride = atex.decode_level(data, atex.parse(data), 0)
    got = struct.unpack("<4I", blocks)
    check(got[:2] == want and got[2:] == (0xC0FFEE00, 0x12345678),
          "a run of 1 claims exactly ONE block and the next falls through",
          f"{[hex(v) for v in got]}")

    # (e) code 4: the 8-bit flat-alpha pass on a DXT5 level. Its flag is
    # TWO-BIT -- after the set flag a second bit SELECTS between two
    # references, and the arms are not interchangeable:
    #   selector 0 -> (0, 0)          fully TRANSPARENT
    #   selector 1 -> (a|a<<8, 0)     the flat alpha value
    # Both are exercised, because a decoder that ignored the second bit would
    # satisfy either one alone.
    literal = struct.pack("<2I", 0x0C0C0C0C, 0x0D0D0D0D)
    body = BitWriter().put(0x7F, 8).run(1).put(1, 1).put(1, 1)
    data = container(b"DXT5", 4, 4, [(atex.PASS_ALPHA8,
                                      body.bytes() + literal)])
    blocks, stride = atex.decode_level(data, atex.parse(data), 0)
    got = struct.unpack("<4I", blocks)
    check(stride == 16 and got[0] == 0x00007F7F and got[1] == 0,
          "code 4 selector 1 stamps a flat 8-bit alpha block "
          "(a0 = a1 = the value)", f"{[hex(v) for v in got[:2]]}")
    check(got[2:] == (0x0C0C0C0C, 0x0D0D0D0D),
          "and the COLOUR half of the same block still comes from the "
          "residual -- the halves are claimed independently",
          f"{[hex(v) for v in got[2:]]}")

    body = BitWriter().put(0x7F, 8).run(1).put(1, 1).put(0, 1)
    data = container(b"DXT5", 4, 4, [(atex.PASS_ALPHA8,
                                      body.bytes() + literal)])
    blocks, _stride = atex.decode_level(data, atex.parse(data), 0)
    got = struct.unpack("<4I", blocks)
    check(got[0] == 0 and got[1] == 0,
          "while selector 0 stamps FULLY TRANSPARENT -- the second bit is a "
          "real selection, not padding", f"{[hex(v) for v in got[:2]]}")

    # (f) TWO PASSES ON ONE LEVEL, which is the interaction no single-pass
    # fixture and no corpus median can reach. code 9 = bit 0 | bit 3: the
    # transparent pass marks BOTH bitmaps, then the flat-colour pass runs and
    # must SKIP those blocks WITHOUT SPENDING RUN.
    #
    # This exists because a sabotage that makes skipped blocks spend run
    # reddened NOTHING before it: the alpha passes run first, when the colour
    # bitmap is still empty, so the skip path is dead on almost every real
    # level -- code 9 occurs 4 times in the whole sampled corpus. A rule the
    # corpus cannot exercise has to be exercised synthetically or not at all.
    body = (BitWriter()
            .run(1).put(1, 1)        # bit 0: block 0 transparent
            .run(2).put(0, 1)        # bit 0: blocks 1-2 left alone
            .put(colour, 24)         # bit 3: the flat colour
            .run(2).put(1, 1))       # bit 3: run of 2 over the UNCLAIMED
    data = container(b"DXT1", 12, 4,
                     [(atex.PASS_TRANSPARENT | atex.PASS_FLAT_COLOUR,
                       body.bytes())])
    blocks, _stride = atex.decode_level(data, atex.parse(data), 0)
    got = struct.unpack("<6I", blocks)
    check(got[0:2] == (0xFFFFFFFE, 0xFFFFFFFF),
          "two passes: block 0 keeps the TRANSPARENT block the first pass "
          "stamped", f"{[hex(v) for v in got[0:2]]}")
    check(got[2:4] == want and got[4:6] == want,
          "and the second pass's run of 2 lands on blocks 1 and 2 -- the "
          "already-claimed block did not SPEND run",
          f"{[hex(v) for v in got[2:]]}")

    # (g) refusals
    data = container(b"DXT1", 4, 4, [(0, struct.pack("<2I", 0, 0))])
    parsed = atex.parse(data)
    for index in (-1, 1, 99):
        try:
            atex.decode_level(data, parsed, index)
            check(False, f"level index {index} is refused")
        except ValueError:
            check(True, f"level index {index} is refused")


# --- 4. solid_colour_block ------------------------------------------------

def naive_565_block(rgb):
    """The OBVIOUS quantiser -- nearest 565, both endpoints equal.

    Reproduced here as a live function, the pattern this repo uses for a
    retired rule, because the claim "the client's quantiser is worth
    transcribing" is only a measurement if the obvious alternative is
    computed rather than asserted to be worse.
    """
    blue, green, red = rgb & 0xFF, (rgb >> 8) & 0xFF, (rgb >> 16) & 0xFF
    packed = ((red >> 3) << 11) | ((green >> 2) << 5) | (blue >> 3)
    return ((packed * 0x10001) & 0xFFFFFFFF, 0)


def _round_trip_error(block, rgb):
    lo, hi = block
    texel = dxt1.decode_block(lo & 0xFFFF, (lo >> 16) & 0xFFFF, hi)[0]
    want = ((rgb >> 16) & 0xFF, (rgb >> 8) & 0xFF, rgb & 0xFF)
    return max(abs(texel[k] - want[k]) for k in range(3))


def section_solid():
    print("\n== 4. the client's flat-colour quantiser ==")
    # A deterministic spread, not a handful of round numbers: 0x808080 and
    # 0xFFFFFF are exactly representable and would pass under any quantiser.
    colours = [(i * 2654435761) & 0xFFFFFF for i in range(400)]
    worst_client = max(_round_trip_error(
        atex.solid_colour_block(0xFF000000 | c, True), c) for c in colours)
    worst_naive = max(_round_trip_error(naive_565_block(c), c)
                      for c in colours)
    better = sum(1 for c in colours
                 if _round_trip_error(atex.solid_colour_block(
                     0xFF000000 | c, True), c)
                 < _round_trip_error(naive_565_block(c), c))
    print(f"    worst channel error: client {worst_client}, naive "
          f"{worst_naive}; client better on {better}/{len(colours)}")

    # THE BOUND IS THE DISCRIMINATOR. The client's quantiser picks two
    # endpoints and an interpolated index, so it reaches colours a
    # nearest-565 cannot: worst 4 against 7 over this set. A tolerance of one
    # full quantum (8) would admit BOTH and the check would not be able to
    # fail -- measured, by running the naive version as a sabotage and
    # watching it pass.
    check(worst_client <= 4,
          "every colour round-trips within 4 -- tighter than a 565 quantum, "
          "which is what the interpolated index buys",
          f"worst {worst_client}")
    check(worst_naive > 4,
          "and the naive nearest-565 does NOT meet that bound -- so the "
          "check above can fail", f"worst {worst_naive}")
    check(better > len(colours) // 2,
          "the client's quantiser beats naive on a majority of colours",
          f"{better}/{len(colours)}")

    # All sixteen texels of a flat block must be the SAME colour -- the
    # index word is one value repeated, and a quantiser that emitted a
    # gradient would still pass the check above on texel 0 alone.
    lo, hi = atex.solid_colour_block(0xFF3366CC, True)
    texels = dxt1.decode_block(lo & 0xFFFF, (lo >> 16) & 0xFFFF, hi)
    check(len(set(texels)) == 1,
          "and all sixteen texels of the block are identical",
          f"{len(set(texels))} distinct")


# --- 5-6. the retail corpus ----------------------------------------------

def block_colours(blocks, stride, count, colour_off):
    out = []
    for i in range(count):
        base = i * stride + colour_off
        c0, c1 = struct.unpack_from("<HH", blocks, base)
        idx, = struct.unpack_from("<I", blocks, base + 4)
        texels = dxt1.decode_block(c0, c1, idx)
        out.append(tuple(sum(t[k] for t in texels) / 16 for k in range(3)))
    return out


def block_alphas(blocks, stride, count):
    out = []
    for i in range(count):
        base = i * stride
        a0, a1 = blocks[base], blocks[base + 1]
        bits = int.from_bytes(blocks[base + 2:base + 8], "little")
        if a0 > a1:
            table = [a0, a1] + [((7 - k) * a0 + k * a1) // 7
                                for k in range(1, 7)]
        else:
            table = ([a0, a1] + [((5 - k) * a0 + k * a1) // 5
                                 for k in range(1, 5)] + [0, 255])
        out.append(sum(table[(bits >> (3 * n)) & 7] for n in range(16)) / 16)
    return out


def downsample_error(big, small, bw, bh, sw, sh, scalar=False):
    total = 0.0
    n = 0
    for y in range(sh):
        for x in range(sw):
            acc = 0.0 if scalar else [0.0, 0.0, 0.0]
            k = 0
            for dy in (0, 1):
                for dx in (0, 1):
                    by, bx = y * 2 + dy, x * 2 + dx
                    if by < bh and bx < bw:
                        v = big[by * bw + bx]
                        if scalar:
                            acc += v
                        else:
                            acc = [acc[t] + v[t] for t in range(3)]
                        k += 1
            if not k:
                continue
            got = small[y * sw + x]
            if scalar:
                total += abs(acc / k - got)
            else:
                total += sum(abs(acc[t] / k - got[t]) for t in range(3)) / 3
            n += 1
    return (total / n if n else None), n


def sweep(rows):
    """Decode every level of every ATEX row, and collect oracle pairs."""
    import vaultpath
    from archive import Archive

    census = collections.Counter()
    pairs = collections.defaultdict(list)
    pool = collections.defaultdict(list)
    dat = os.path.join(vaultpath.require_dir("dat_study"), "Gw.dat")
    with Archive(dat) as ar:
        for entry in ar.entries[:rows]:
            try:
                data = ar.read(entry)
            except Exception:                          # noqa: BLE001
                continue
            if data[:4] not in (b"ATEX", b"ATTX"):
                continue
            try:
                parsed = atex.parse(data)
            except Exception:                          # noqa: BLE001
                continue
            fourcc = bytes(parsed.fourcc)
            if fourcc not in atex.FORMAT_ENUM:
                continue
            census["containers"] += 1
            stride = STRIDES[fourcc]
            decoded = []
            for i, level in enumerate(parsed.levels):
                w, h = atex.level_dims(parsed.width, parsed.height, i)
                count = max(1, (w + 3) // 4) * max(1, (h + 3) // 4)
                try:
                    blocks, got_stride = atex.decode_level(data, parsed, i)
                except Exception:                      # noqa: BLE001
                    census["errors"] += 1
                    decoded.append(None)
                    continue
                census["levels"] += 1
                census["code_%d" % level.code] += 1
                if got_stride == stride and len(blocks) == count * stride:
                    census["exact"] += 1
                decoded.append((blocks, got_stride, count, w, h))

            # The oracle: a CODED level whose next level is RAW.
            for i in range(len(parsed.levels) - 1):
                hi, lo = parsed.levels[i], parsed.levels[i + 1]
                if hi.code == 0 or lo.code != 0:
                    continue
                if decoded[i] is None or decoded[i + 1] is None:
                    continue
                big, _s, nb, w, h = decoded[i]
                small, _s2, nb2, w2, h2 = decoded[i + 1]
                if w < 16 or w2 * 2 != w or h2 * 2 != h:
                    continue
                bw, bh = max(1, w // 4), max(1, h // 4)
                sw, sh = max(1, w2 // 4), max(1, h2 // 4)
                _bd, colour_off, _ha, has_colour, _f = atex.block_layout(
                    fourcc)
                if has_colour:
                    a = block_colours(big, stride, nb, colour_off * 4)
                    b = block_colours(small, stride, nb2, colour_off * 4)
                    scalar = False
                else:
                    a = block_alphas(big, stride, nb)
                    b = block_alphas(small, stride, nb2)
                    scalar = True
                err, n = downsample_error(a, b, bw, bh, sw, sh, scalar)
                if err is None:
                    continue
                key = "alpha" if scalar else "colour"
                pairs[key].append(err)
                pool[key].append((a, bw, bh, b, sw, sh, scalar))
                break
    return census, pairs, pool


def section_corpus(rows):
    print("\n== 5. every retail level decodes (the WEAK half) ==")
    try:
        census, pairs, pool = sweep(rows)
    except SystemExit:
        LEDGER.skip("5-6. retail corpus", "no vault/dat_study")
        return None, None
    print(f"    {census['containers']} containers, {census['levels']} levels, "
          f"{census['errors']} errors")
    codes = {k[5:]: v for k, v in census.items() if k.startswith("code_")}
    print(f"    codes seen: {dict(sorted(codes.items(), key=lambda kv: -kv[1]))}")

    check(census["containers"] > 100 and census["levels"] > 1000,
          "the sweep found enough ATEX containers to say anything",
          f"{census['containers']} / {census['levels']}")
    check(census["errors"] == 0,
          "no level raises -- the walk survives every code in the corpus",
          f"{census['errors']} errors")
    check(census["exact"] == census["levels"],
          "every level yields exactly blocks*stride bytes -- NECESSARY but "
          "forced by construction; see the docstring",
          f"{census['exact']}/{census['levels']}")
    check(len(codes) >= 6,
          "and the sweep actually exercised the coded paths, not just code 0",
          f"{len(codes)} distinct codes")
    check(int(codes.get("0", 0)) < census["levels"],
          "with a real population of NON-zero codes -- the control that keeps "
          "the line above from passing on raw levels alone",
          f"{census['levels'] - int(codes.get('0', 0))} coded levels")
    return pairs, pool


def section_oracle(pairs, pool):
    print("\n== 6. THE ORACLE: a coded level against its RAW neighbour ==")
    if pairs is None:
        return
    for key in ("colour", "alpha"):
        values = sorted(pairs.get(key, []))
        if len(values) < 20:
            LEDGER.skip(f"6. {key} oracle", f"only {len(values)} pairs")
            continue
        median = values[len(values) // 2]
        under = sum(1 for v in values if v < ORACLE_MAX_MEDIAN)
        print(f"    {key:6}: n={len(values)}  median {median:.2f}  "
              f"under {ORACLE_MAX_MEDIAN} {under}/{len(values)}")
        check(median < ORACLE_MAX_MEDIAN,
              f"{key}: a coded level downsamples onto its RAW neighbour "
              f"(median under {ORACLE_MAX_MEDIAN})", f"{median:.2f}")

        # THE NULL. Same coded levels, a DIFFERENT texture's raw level. If
        # this does not collapse, the median above is measuring "images are
        # smooth" rather than "this decode is right".
        null = []
        entries = pool[key]
        for i, (a, bw, bh, _b, sw, sh, scalar) in enumerate(entries):
            other = entries[(i + 1) % len(entries)]
            if other[4] != sw or other[5] != sh:
                continue
            err, _n = downsample_error(a, other[3], bw, bh, sw, sh, scalar)
            if err is not None:
                null.append(err)
        null.sort()
        if len(null) < 10:
            LEDGER.skip(f"6. {key} null", f"only {len(null)} null pairs")
            continue
        null_median = null[len(null) // 2]
        print(f"    {key:6}: NULL median {null_median:.2f}")
        check(null_median > median * ORACLE_NULL_RATIO,
              f"{key}: and the NULL collapses -- the same coded level against "
              f"a DIFFERENT texture's raw one is at least "
              f"{ORACLE_NULL_RATIO:g}x worse",
              f"{null_median:.2f} vs {median:.2f}")


# --- 7. the client tables, pinned to ArenaNet's bytes ---------------------

def section_tables():
    print("\n== 7. the two client tables vs the vaulted image ==")
    # WHICH IMAGE, and this section read the WRONG ONE from 2026-08-14 until
    # 2026-08-15. It used to walk `sorted(os.listdir(root))` and keep the LAST
    # candidate -- a `sorted(...)[-1]` written as a loop with no `break`, which
    # is the same defect `CLAUDE.md` names by name and the FOURTH file to carry
    # it. It was harmless while the vault held one usable build. The day 38833
    # was snapshotted, `2026-08-13_64fae3b1369b` began sorting last, and this
    # section silently started asserting literals MEASURED ON 38797 against
    # 38833's bytes. It passed -- MEASURED, those two tables did not move in
    # that update -- so the defect produced no red and would have been found
    # only by a future build moving them, at which point the failure reads as
    # "atex is broken" rather than "you are reading the wrong client".
    #
    # Resolved through `pinned` now, which is the module built to answer this:
    # it selects the build by REGISTRY rather than by filename order, verifies
    # the sha256 of what it hands back, and refuses the auto-updating live
    # install. The build is then PRINTED, because a section that reads a client
    # and does not say which one is one rename away from this bug again.
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
        import pinned
        exe, why = pinned.find(atex.TABLES_BUILD)
    except SystemExit as exc:
        LEDGER.skip("7. client tables", f"no pinned client: {exc}")
        return
    print(f"    image: build {atex.TABLES_BUILD} -- {why}")
    with open(exe, "rb") as fh:
        image = fh.read()

    # The test's OWN PE walk -- the module's literals are pinned to
    # ArenaNet's bytes rather than to a transcription of them.
    lfanew, = struct.unpack_from("<I", image, 0x3C)
    sections, = struct.unpack_from("<H", image, lfanew + 6)
    opt_size, = struct.unpack_from("<H", image, lfanew + 20)
    base, = struct.unpack_from("<I", image, lfanew + 24 + 28)
    table = lfanew + 24 + opt_size

    def file_offset(va):
        rva = va - base
        for i in range(sections):
            off = table + i * 40
            vsize, vaddr, _rsize, raw = struct.unpack_from("<4I", image,
                                                           off + 8)
            if vaddr <= rva < vaddr + vsize:
                return raw + (rva - vaddr)
        return None

    off = file_offset(atex.FORMAT_FLAGS_VA)
    check(off is not None, "the format-flags VA resolves into a section")
    if off is not None:
        got = struct.unpack_from("<27I", image, off)
        check(got == atex.FORMAT_FLAGS,
              "FORMAT_FLAGS matches the 27 dwords at 0x%08X"
              % atex.FORMAT_FLAGS_VA,
              f"{[hex(v) for v in got[:4]]}...")
        # A read four bytes early must NOT match -- otherwise the check above
        # would pass against any run of plausible dwords.
        near = struct.unpack_from("<27I", image, off - 4)
        check(near != atex.FORMAT_FLAGS,
              "and a read four bytes early does NOT match -- the address is "
              "load-bearing")

    off = file_offset(atex.RUN_TABLE_VA)
    check(off is not None, "the run-table VA resolves into a section")
    if off is not None:
        raw = image[off:off + 128]
        got = tuple((raw[2 * i], raw[2 * i + 1]) for i in range(64))
        check(got == atex.RUN_TABLE,
              "RUN_TABLE matches the 64 pairs at 0x%08X" % atex.RUN_TABLE_VA,
              f"{got[:3]}...")
        near = tuple((raw[2 * i + 1], raw[2 * i + 2]) for i in range(63))
        check(near != atex.RUN_TABLE[:63],
              "and a read one byte early does NOT match")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="sweep 12,000 archive rows instead of 4,000")
    ap.add_argument("--rows", type=int, default=None,
                    help="explicit archive-row budget for the sweep. Exists "
                         "so the sabotage matrix in the docstring is "
                         "affordable to RE-RUN -- at the default row count "
                         "ten sabotages take over ten minutes, which in "
                         "practice means nobody re-measures them.")
    args = ap.parse_args()
    print("=" * 70)
    print("ATEX LEVEL CODEC -- the passes, the rack, and the planar residual")
    print("=" * 70)

    pairs = pool = None
    for fn in (section_runtable, section_rack, section_layout,
               section_synthetic, section_solid):
        try:
            fn()
        except Exception as exc:                       # noqa: BLE001
            check(False, f"section {fn.__name__} completed",
                  f"{type(exc).__name__}: {exc}")
    try:
        pairs, pool = section_corpus(
            args.rows or (12000 if args.all else 4000))
    except Exception as exc:                           # noqa: BLE001
        check(False, "section section_corpus completed",
              f"{type(exc).__name__}: {exc}")
    for fn, arg in ((section_oracle, (pairs, pool)), (section_tables, ())):
        try:
            fn(*arg)
        except Exception as exc:                       # noqa: BLE001
            check(False, f"section {fn.__name__} completed",
                  f"{type(exc).__name__}: {exc}")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
