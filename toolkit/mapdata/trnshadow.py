"""Terrain tag 7, decoded: the baked shadow bitmap and its per-cell summary.

`terrain.py` carries tag 7 as opaque bytes and says so plainly -- the block WALK
is proven, the contents were not decoded. This module decodes the contents.

    blk  = trn.shadow[k]                  # one 32x32 terrain tile's block
    rows = decode_rows(blk.payload)       # 272 ints, bit x of row y = one sample
    assert encode_rows(rows) == blk.payload
    assert tail_from_rows(rows) == blk.tail

WHAT TAG 7 IS. Per 32x32 terrain tile, `{u32 k, u8 payload[k], u8 tail[128]}`:

  * `payload` is a **272 x 272 one-bit shadow bitmap**, run-length coded one row
    at a time. 272 = (32 + 2) * 8 -- eight samples per terrain cell, over the
    tile's 32 cells plus a one-cell skirt on every side. Sample pitch is
    therefore 96/8 = 12 world units.
  * `tail` is 128 bytes = 1024 bits = **one bit per cell of the 32x32 tile**,
    MSB first, cell index `cy * 32 + cx`. The bit is set exactly when all 100
    samples of the 10x10 window centred on that cell's 8x8 footprint are set --
    a conservative "this whole cell is in shadow" flag. See `tail_from_rows`.

  Set bit means IN SHADOW. MEASURED on Kamadan (row 22371): the 62,610 cells
  whose tail bit is set average 186.0 in tag 9's lightmap against 236.6 for the
  123,758 that are not. Tag 9 is a light intensity (see `terrain.py`'s `shade`),
  so the darker population is the shadowed one.

THE RUN CODING, and it is ArenaNet's own, read out of the image rather than
guessed at. `TrnCodecShadow.cpp` line 245's assert `run` sits at 0x00761220 in
build 38797, inside a 0x79-byte routine that is the run emitter, called from the
row encoder at 0x00761290:

    for each of the 272 rows:
        if the row's first bit is 1: emit a 0x00 byte      (a zero-length run)
        walk the row's bits, counting equal consecutive bits
        emit each run: (run - 1) // 254 copies of 0xFF, then run - 254 * that

  So 0xFF means "254 more, and the run continues"; any other byte ends the run.
  Runs alternate 0, 1, 0, 1 ... and **each row restarts at 0**, which is why a
  row beginning with a set bit needs the leading zero-length run. The value
  0x00 can therefore only appear as the first byte of a row.

  Decoding is the inverse and it is self-checking three ways: every run must
  land inside its row, every row must close on exactly 272 samples, and the
  payload must end on exactly 272 rows.

HOW MUCH OF THIS IS EVIDENCE. Every number below was MEASURED on
`vault/dat_study/Gw.dat` on 2026-08-11, and each is a check the archive could
have refused:

  * **59,051 of 59,051 corpus blocks** decode to 272 rows of 272 samples with
    nothing left over -- all 349 maps, 4,368,829,184 samples, 0 refusals. The
    row-close rule is the load-bearing one: it is 272 independent constraints
    per block and a wrong bitmap width fails on the first row of the first
    block. `k` runs 544..13,332.
  * **59,051 of 59,051 re-encode byte-identically** through `encode_rows`. The
    decoder throws the bytes away; the encoder rebuilds them from the bitmap
    alone, so the escape rule, the leading-zero rule and the exact boundary at
    run == 254 are all pinned against ArenaNet's writer rather than ours.
  * **`tail_from_rows` reproduces every stored tail bit in the corpus:
    60,468,224 of 60,468,224.** The window width is the refutable part and both
    neighbours fail -- an 8x8 window (no skirt) disagrees on 1,562,798 cell bits
    (2.58%) and a 12x12 on 611,928 (1.01%). `tail_disagreement()` exposes that
    control so a test can run it, and `test_trnshadow.py` asserts that the
    controls really do disagree rather than only that our rule agrees.
  * The 0x00 rule holds: over six maps and 1,852,542 payload bytes, **118,922
    zero bytes and 118,922 of them at a row start**. Corpus-wide, 5,510,906 of
    16,061,872 rows (34.3%) begin with a set sample and therefore carry one.
  * 35.1% of all corpus samples are in shadow (1,533,633,078 of
    4,368,829,184); 14.3% of cells carry the tail flag, sampled over 697 blocks.

WHAT THIS DOES NOT ESTABLISH. What CAST the shadow is not settled. A terrain
raycast from the heightmap at tag 0's light elevation predicts the tail only
weakly on Kamadan (41.9% of ray-shadowed cells carry the flag against a 33.6%
base rate), which is what you would expect if the bake includes props -- but
"includes props" is INFERRED and untested. Nothing here reads the prop chunk.

The 8-samples-per-cell reading of 272 is likewise an interpretation. What is
MEASURED is 272 x 272 and the 10x10 tail window; that 272 factors as 34 * 8 and
that the tile is 32 cells wide is arithmetic, not a separate observation.

SCOPE. Bloated terrain only, one block at a time. This module holds no archive
bytes and opens no file; `terrain.py` does the framing and hands the payload in.

    python toolkit/mapdata/trnshadow.py --row 46196
    python toolkit/mapdata/trnshadow.py --file-id 0x345CC --blocks 4
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from archive import DEFAULT_DAT                           # noqa: E402

# This module is the LOW-level half of the pair and must not import `terrain`
# at module scope: `terrain` imports this one to decode tag 7, so a top-level
# `from terrain import ...` here is a circular import that fails at load. The
# two constants below were imported from `terrain` when this module was written
# standalone; they are the client's own CHUNK_SIZE (MEASURED from the binary
# twice, TrnCodecHeight:166/167 and TrnChunkBox:150) and the tail width. They
# are declared here and `terrain` is checked against them by `test_trnshadow`,
# so the two cannot drift apart silently.
CHUNK_SIZE = 32
SHADOW_TAIL = 128

SAMPLES_PER_CELL = 8
BORDER_CELLS = 1
BLOCK_EDGE = (CHUNK_SIZE + 2 * BORDER_CELLS) * SAMPLES_PER_CELL     # 272
BLOCK_SAMPLES = BLOCK_EDGE * BLOCK_EDGE                             # 73,984
CELL_BITS = CHUNK_SIZE * CHUNK_SIZE                                 # 1,024

RLE_CONTINUE = 0xFF
RLE_STEP = 0xFE                     # what one 0xFF byte is worth

ROW_MASK = (1 << BLOCK_EDGE) - 1    # for complementing a row without Python's
                                    # infinite sign extension

# The tail's window: the cell's 8x8 samples plus one sample of skirt on each
# side. MEASURED -- see `tail_disagreement` for the controls that fail.
TAIL_PAD = 1
TAIL_WINDOW = SAMPLES_PER_CELL + 2 * TAIL_PAD                       # 10


def decode_rows(payload):
    """One block's payload -> `BLOCK_EDGE` ints, bit x of row y = sample (x, y).

    Raises on anything that does not close exactly: a run that would overrun its
    row, a row that ends short, or a payload that does not stop on a row
    boundary after `BLOCK_EDGE` rows. The client's own loader does none of this
    -- it copies the bytes and lets the renderer walk them -- so being stricter
    than the client is the point, exactly as it is for the block walk itself.
    """
    rows = []
    row = 0
    col = 0
    value = 0
    run = 0
    for i, byte in enumerate(payload):
        if byte == RLE_CONTINUE:
            run += RLE_STEP
            continue
        run += byte
        if col + run > BLOCK_EDGE:
            raise ValueError(
                f"tag 7 run at byte {i} carries {run} samples but only "
                f"{BLOCK_EDGE - col} remain in row {len(rows)}")
        if value and run:
            row |= ((1 << run) - 1) << col
        col += run
        run = 0
        value ^= 1
        if col == BLOCK_EDGE:
            rows.append(row)
            row = 0
            col = 0
            value = 0
            if len(rows) > BLOCK_EDGE:
                raise ValueError(f"tag 7 payload holds more than {BLOCK_EDGE} "
                                 f"rows of {BLOCK_EDGE} samples")
    if run or col:
        raise ValueError(f"tag 7 payload ends mid-row: {col} of {BLOCK_EDGE} "
                         f"samples into row {len(rows)}")
    if len(rows) != BLOCK_EDGE:
        raise ValueError(f"tag 7 payload decoded {len(rows)} rows, "
                         f"expected {BLOCK_EDGE}")
    return rows


def encode_rows(rows):
    """The inverse, in ArenaNet's canonical form. Reproduces retail bytes.

    The two rules a naive encoder gets wrong, both taken from the client's
    emitter and both exercised by real maps: a row whose first sample is set
    opens with a zero-length run, and a run of exactly 254 is one 0xFE byte
    rather than 0xFF followed by 0.

    This walks RUNS, not samples. The obvious loop over all `BLOCK_EDGE` bits of
    each row costs 73,984 iterations per block and 5.2 ms on a real map, which is
    ~6 minutes of pure encoding across the corpus's 59,051 blocks -- enough to
    make the whole-archive check the kind nobody runs. Shadow rows are long
    uniform stretches, so stepping transition to transition is the natural shape:
    `rem & -rem` isolates the lowest set bit and its `bit_length` is the distance
    to the next transition. Output is byte-for-byte what the sample loop produced.
    """
    if len(rows) != BLOCK_EDGE:
        raise ValueError(f"{len(rows)} rows, expected {BLOCK_EDGE}")
    out = bytearray()
    for y, row in enumerate(rows):
        if row >> BLOCK_EDGE:
            raise ValueError(f"row {y} has bits past sample {BLOCK_EDGE - 1}")
        value = row & 1
        if value:
            out.append(0)                       # a zero-length run of 0s
        inverse = row ^ ROW_MASK
        pos = 0
        while pos < BLOCK_EDGE:
            rest = (inverse if value else row) >> pos
            # the next transition, or the end of the row if there is none
            run = ((rest & -rest).bit_length() - 1) if rest else BLOCK_EDGE - pos
            _emit(out, run)
            pos += run
            value ^= 1
    return bytes(out)


def _emit(out, run):
    if run < 1:
        raise ValueError("a run of zero samples has no encoding except the "
                         "leading one, which encode_rows writes itself")
    escapes = (run - 1) // RLE_STEP
    out += bytes([RLE_CONTINUE]) * escapes
    out.append(run - RLE_STEP * escapes)


def sample_at(rows, sx, sy):
    """One sample. `(0, 0)` is the top-left of the skirt, not of the tile."""
    return (rows[sy] >> sx) & 1


def cell_origin(cx, cy):
    """Where cell `(cx, cy)` of the tile starts in sample coordinates."""
    return ((cx + BORDER_CELLS) * SAMPLES_PER_CELL,
            (cy + BORDER_CELLS) * SAMPLES_PER_CELL)


def tail_from_rows(rows, pad=TAIL_PAD):
    """Derive the block's 128-byte tail from its bitmap.

    Bit `cy * 32 + cx`, MSB first within each byte, set when every sample of the
    `(8 + 2*pad)` square centred on the cell's footprint is set. `pad` is a knob
    only so that a test can run the neighbouring widths as controls; the value
    the archive agrees with is `TAIL_PAD`.
    """
    width = SAMPLES_PER_CELL + 2 * pad
    mask = (1 << width) - 1
    out = bytearray(SHADOW_TAIL)
    for cy in range(CHUNK_SIZE):
        full = [True] * CHUNK_SIZE
        oy = (cy + BORDER_CELLS) * SAMPLES_PER_CELL
        for dy in range(-pad, SAMPLES_PER_CELL + pad):
            row = rows[oy + dy]
            for cx in range(CHUNK_SIZE):
                if full[cx]:
                    ox = (cx + BORDER_CELLS) * SAMPLES_PER_CELL - pad
                    if ((row >> ox) & mask) != mask:
                        full[cx] = False
        for cx in range(CHUNK_SIZE):
            if full[cx]:
                c = cy * CHUNK_SIZE + cx
                out[c >> 3] |= 1 << (7 - (c & 7))
    return bytes(out)


def tail_bit(tail, cx, cy):
    """The stored per-cell flag for cell `(cx, cy)`. Set means fully shadowed."""
    c = cy * CHUNK_SIZE + cx
    return (tail[c >> 3] >> (7 - (c & 7))) & 1


def tail_disagreement(rows, tail, pad=TAIL_PAD):
    """How many of the 1,024 cell bits `tail_from_rows(rows, pad)` gets wrong.

    The control that gives `TAIL_PAD` its force: run it at pad 0 and pad 2 and
    the count stops being zero.
    """
    got = tail_from_rows(rows, pad=pad)
    return sum(bin(a ^ b).count("1") for a, b in zip(got, tail))


def zero_bytes(payload):
    """`(zeros, zeros that open a row)` in a payload.

    A 0x00 is a zero-length run, and the only place the encoder can emit one is
    the start of a row whose first sample is set -- everywhere else a run has at
    least one sample. So the two counts must be equal, and they are: MEASURED
    over six maps, 1,852,542 payload bytes, 118,922 zeros, 118,922 of them at a
    row start. A decoder does not need this rule; it is here because it is a law
    the archive could break and does not, which is what makes the reading of
    0x00 a fact rather than a convention we chose.
    """
    zeros = at_start = 0
    col = run = 0
    start = True
    for byte in payload:
        if byte == 0:
            zeros += 1
            if start:
                at_start += 1
        if byte == RLE_CONTINUE:
            run += RLE_STEP
            start = False
            continue
        col += run + byte
        run = 0
        if col >= BLOCK_EDGE:
            col = 0
            start = True
        else:
            start = False
    return zeros, at_start


def shadow_fraction(rows):
    """Fraction of the block's samples that are in shadow."""
    return sum(bin(r).count("1") for r in rows) / float(BLOCK_SAMPLES)


def _main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--file-id", default=None)
    ap.add_argument("--row", type=int, default=None)
    ap.add_argument("--blocks", type=int, default=3)
    args = ap.parse_args()

    # Imported HERE, not at module scope: `terrain` imports this module, so a
    # top-level import would be circular. The CLI is the only thing that needs it.
    from archive import Archive
    from terrain import Terrain

    if args.row is not None:
        with Archive(args.dat) as ar:
            trn = Terrain.from_row(args.row, ar)
    else:
        fid = int(args.file_id, 0) if args.file_id else 0x345CC
        with Archive(args.dat) as ar:
            trn = Terrain.load(fid, archive=ar)

    print(trn)
    for i, blk in enumerate(trn.shadow[:args.blocks]):
        rows = decode_rows(blk.payload)
        ok = encode_rows(rows) == blk.payload
        bad = tail_disagreement(rows, blk.tail)
        print(f"  block {i}: k={len(blk.payload)} "
              f"shadow={shadow_fraction(rows) * 100:.1f}% "
              f"re-encode={'exact' if ok else 'DIFFERS'} "
              f"tail mismatches={bad} "
              f"(pad 0: {tail_disagreement(rows, blk.tail, pad=0)}, "
              f"pad 2: {tail_disagreement(rows, blk.tail, pad=2)})")


if __name__ == "__main__":
    _main()
