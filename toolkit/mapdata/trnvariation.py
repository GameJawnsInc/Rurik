"""Reproduce the client's per-cell terrain VARIATION -- which quadrant a cell draws.

A terrain texture is a 256x256 atlas holding FOUR 128x128 variants of one
material (T3). Which variant a cell samples is `variation`, and it comes from
two places: terrain tag 3's 2-bit field when that is non-zero (an authored
override, 0.06% of cells corpus-wide), and otherwise from a per-cell PRNG
draw. Without the draw every cell of a tile type samples quadrant 0 and the
ground repeats visibly -- which is exactly what rung T5 shipped and what this
module fixes.

    from trnvariation import map_variation
    quads = map_variation(dim_x, dim_y, authored)   # world row-major, 0..3

WHERE THIS COMES FROM. Read out of build 38797 by a disassembly agent,
2026-08-14, `studies/terrain/FINDINGS.md` §6. Every numbered claim below is
OBSERVED at the named VA; the ASSEMBLY of them into a whole-map traversal is
a RECONSTRUCTION and is labelled as one, because the one thing the read did
NOT settle is how far a single seed's stream runs (see THE OPEN QUESTION).

  1. **One draw per cell, always** -- `0x007618B3`..`0x007618CE`. The forced
     branch (tag 3 non-zero) calls the generator and THROWS THE RESULT AWAY,
     then uses the raw tag-3 value; the random branch calls it and masks. So
     stream position is a pure function of the cell's index in the traversal,
     and a consumer may not skip the draw on authored cells -- doing so
     desynchronises every later cell in the tile.
  2. **quadrant = draw & 3** on the random branch (`0x007618CB`, a plain
     `and esi, 3` -- not a modulo, not a compare ladder), and the raw
     1/2/3 UNMASKED on the forced branch (`0x007618BD`->`0x007618C2`).
  3. **The primary layer's rotation is always 0.** `and esi,3` clears every
     bit above 1 before the `shl 0x10`, and tag 3 is a 2-bit field, so bit 15
     of the variation word -- the rotation flag tested at `0x00757B43` -- can
     never be set by this path. Rotation belongs to the SECONDARY blend
     layers and is read from a content table at `0x00BF78D8`, never drawn.
  4. **seed = (tile.x << 16) ^ tile.y** -- `0x00761C80`, and `x` is the fast
     axis (field +0, used unmultiplied; field +4 is multiplied by the pitch
     at three independent sites). A seed of 0 becomes `DEFAULT_SEED`
     (`0x0046D2E0`).

THE GENERATOR IS NOT A CLEAN LEHMER STEP, AND THIS IS THE TRAP. It looks like
MINSTD -- `s' = 48271 * s mod (2^31 - 1)` -- and `0x0046D120` computes the
modulo with a MAGIC-NUMBER DIVISION: multiply by `0xBC8F1391`, take the high
dword, shift right 15 (47 bits total), multiply back by `0x7FFFFFFF`,
subtract. That quotient is one too high on about 3.8% of states, and the
client's correction adds `0x80000000` rather than `0x7FFFFFFF`, which does
not cancel it -- so on those states the generator returns
`(48271*s mod 2147483647) + 1` and the streams diverge. Verified by the
reading agent over 500,000 random states.

**So `%` is the wrong operator here and a clean reimplementation silently
drifts on one draw in twenty-six.** `rng_next` below is the instruction
sequence, not the mathematics, and `test_trnvariation.py` pins the
divergence with states that exhibit it -- the check is that our port and the
clean-modulo rival DISAGREE exactly where the client's arithmetic says they
must, so a "tidied up" future edit reddens instead of passing.

THE OPEN QUESTION, stated rather than papered over. `STREAM_SPAN` decides how
far one seed runs: a full 32x32 tile (1,024 draws) or a single row of 32. The
agent that read the loop found a 32-pass loop consuming exactly 8 tag-3 bytes
(= one row, since a tag-3 byte covers four consecutive x cells) and could NOT
find a wrapping outer loop inside `0x0075DD50`; but the same function
unconditionally allocates the whole 4,096-vertex tile buffer on every entry,
which a per-row invocation would stomp 32 times. Those cannot both be true as
read. Until it is settled this module defaults to the TILE reading and says
so in `map_variation`'s report, because the buffer allocation is the harder
fact to explain away -- and because the alternative is visible: a per-row
reseed with the same `(tile.x, tile.y)` would repeat one row's pattern down
all 32 rows of every tile, a stripe a human would notice immediately.
`STREAM_SPAN = "row"` flips it, and `test_trnvariation.py` checks the stripe
consequence so the wrong choice is refutable from a render rather than from
prose.

WHAT THIS MODULE IS NOT. It is not evidence about the client's traversal
ORDER beyond the row (x fast, ascending) that was read. If the y direction is
wrong the DISTRIBUTION of quadrants stays correct and the specific quadrant
of a specific cell does not, so a render looks equally plausible either way --
which is why the honest label on the whole-map assembly is RECONSTRUCTION,
and why nothing downstream may quote it as a measurement of ArenaNet's
output.
"""

import sys

#: `s * 48271`, the Lehmer multiplier (`0x0046D12C`, `imul ecx, ..., 0xBC8F`).
MUL = 48271
#: The modulus, 2^31 - 1 (`0x0046D136`, `imul eax, edx, 0x7FFFFFFF`).
MOD = 0x7FFFFFFF
#: The reciprocal used for the magic-number division (`0x0046D124`).
MAGIC = 0xBC8F1391
#: The shift applied to the high dword (`0x0046D133`, `shr edx, 0xF`) -- 47
#: bits in total, counting the 32 the high dword already represents.
MAGIC_SHIFT = 0xF
#: What a zero seed and a zero state both become (`0x0046D156`, `0x0046D2E0`).
DEFAULT_SEED = 0x075BD924
#: The correction the client adds when the subtraction underflows past the
#: modulus (`0x0046D149`, bytes `81 c1 00 00 00 80`). NOT `MOD`, and that is
#: the whole reason this module exists rather than a one-line lambda.
UNDERFLOW_FIX = 0x80000000

#: Cells on a side of one terrain tile. `terrain.CHUNK_SIZE` is the same
#: number for the same reason; imported rather than shared to keep this
#: module standalone for the Blender side, which cannot import toolkit.
TILE = 32

#: How far one seed's stream runs before the next reseed. "tile" = 1,024
#: draws over a whole 32x32 tile; "row" = 32 draws. See THE OPEN QUESTION.
STREAM_SPAN = "tile"

MASK32 = 0xFFFFFFFF


def rng_next(state):
    """One step of the client's generator. `0x0046D120`, instruction for instruction.

    Returns the new state, which is also what the caller reads as the draw.
    Deliberately NOT `(state * 48271) % 2147483647`: see the module docstring
    for the 3.8% of states where those differ and why the difference is the
    client's, not a bug in this port.
    """
    ecx = (state * MUL) & MASK32
    edx = ((MAGIC * state) & 0xFFFFFFFFFFFFFFFF) >> 32
    edx >>= MAGIC_SHIFT
    eax = (edx * MOD) & MASK32
    ecx = (ecx - eax) & MASK32
    if ecx > MOD:
        ecx = (ecx + UNDERFLOW_FIX) & MASK32
    if ecx == 0:
        ecx = DEFAULT_SEED
    return ecx


def rng_next_clean(state):
    """The TEXTBOOK Lehmer step, kept as a live control and never called.

    `test_trnvariation.py` requires this to DISAGREE with `rng_next` on the
    states where the client's magic-number division is off by one. A control
    that agreed everywhere would mean the quirk had been tidied away, which
    is the one edit that would silently desynchronise every reproduction.
    """
    return (state * MUL) % MOD or DEFAULT_SEED


def reseed(tile_x, tile_y):
    """The seed for one tile. `0x00761C80` -> `0x0046D2E0`.

    `x` is the fast axis and goes in the high word. A zero seed -- tile
    (0, 0), which every map has -- becomes `DEFAULT_SEED`, and that is the
    client's own substitution rather than ours.
    """
    seed = ((tile_x << 16) ^ tile_y) & MASK32
    return seed if seed else DEFAULT_SEED


def tile_variation(tile_x, tile_y, authored=None, span=None):
    """The variation 0..3 for every cell of one 32x32 tile, row-major.

    `authored[j * TILE + i]` is that cell's tag-3 value (0 = let the draw
    decide); None means all zero. Returns a `bytes` of `TILE * TILE`.

    THE DRAW HAPPENS EITHER WAY (claim 1). An authored cell consumes its
    place in the stream and then ignores what it drew, so a consumer that
    skips the draw shifts every later cell in the tile.
    """
    span = STREAM_SPAN if span is None else span
    out = bytearray(TILE * TILE)
    state = reseed(tile_x, tile_y)
    for j in range(TILE):
        if span == "row":
            # The rival reading: one seed per row. Kept live rather than
            # described, because the two are one constant apart and the
            # difference is visible (see THE OPEN QUESTION).
            state = reseed(tile_x, tile_y)
        for i in range(TILE):
            k = j * TILE + i
            state = rng_next(state)
            forced = 0 if authored is None else authored[k]
            out[k] = forced if forced else (state & 3)
    return bytes(out)


def map_variation(dim_x, dim_y, authored=None, span=None):
    """Every cell's variation for a whole map, world row-major.

    `authored` is the export's `.variation.u8` (world row-major, 0..3) or
    None. The map is walked tile by tile, `x` fast, because that is the axis
    order the seed formula and three independent call sites agree on.

    RECONSTRUCTION, and the label is the point: the per-cell arithmetic is
    OBSERVED but the traversal that threads it across a map is assembled from
    it. See the module docstring for exactly which part is which.
    """
    if dim_x % TILE or dim_y % TILE:
        raise ValueError(
            f"dims {dim_x}x{dim_y} are not both multiples of {TILE}; the "
            f"client gates on it and the tiling below assumes it")
    if authored is not None and len(authored) != dim_x * dim_y:
        raise ValueError(f"{len(authored)} authored values for a "
                         f"{dim_x}x{dim_y} grid ({dim_x * dim_y} cells)")
    out = bytearray(dim_x * dim_y)
    for ty in range(dim_y // TILE):
        for tx in range(dim_x // TILE):
            sub = None
            if authored is not None:
                sub = bytearray(TILE * TILE)
                for j in range(TILE):
                    src = (ty * TILE + j) * dim_x + tx * TILE
                    sub[j * TILE:(j + 1) * TILE] = authored[src:src + TILE]
            got = tile_variation(tx, ty, sub, span=span)
            for j in range(TILE):
                dst = (ty * TILE + j) * dim_x + tx * TILE
                out[dst:dst + TILE] = got[j * TILE:(j + 1) * TILE]
    return bytes(out)


def _main(argv=None):
    import argparse
    import collections
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dims", default="64x64", help="e.g. 416x448")
    ap.add_argument("--span", default=None, choices=("tile", "row"))
    args = ap.parse_args(argv)
    dx, dy = (int(v) for v in args.dims.lower().split("x"))
    quads = map_variation(dx, dy, span=args.span)
    hist = collections.Counter(quads)
    n = len(quads)
    print(f"{dx}x{dy} = {n} cells, span={args.span or STREAM_SPAN}")
    for k in range(4):
        print(f"  quadrant {k}: {hist[k]:8d}  {100 * hist[k] / n:5.2f}%")
    # The stripe test, printed rather than asserted: under the "row" reading
    # every row of a tile is identical, which is what makes the two readings
    # distinguishable by eye as well as by test.
    same = sum(1 for j in range(1, TILE)
               for i in range(dx)
               if quads[j * dx + i] == quads[i])
    print(f"  row 0 vs rows 1..{TILE - 1}: {same} of {(TILE - 1) * dx} cells "
          f"match ({100 * same / ((TILE - 1) * dx):.1f}%) -- ~25% is "
          f"independent rows, ~100% is the per-row reseed's stripe")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
