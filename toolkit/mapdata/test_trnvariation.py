"""Check the per-cell variation reproduction -- and keep its two traps refutable.

    python toolkit/mapdata/test_trnvariation.py

`trnvariation.py` reproduces which 128x128 quadrant of its texture each
terrain cell samples. The per-cell arithmetic is OBSERVED in build 38797; the
whole-map traversal is a RECONSTRUCTION. This file is arranged around the two
places where a plausible "tidying up" would silently desynchronise every cell
after the first, because both are edits a future reader would think were
improvements:

  1. **The generator is not `% 2147483647`.** The client computes the modulo
     with a magic-number division whose quotient is one too high on ~3.8% of
     states, and corrects with `+0x80000000`, which does not cancel it. So
     `rng_next` and the textbook step DISAGREE, and section 1 requires them
     to disagree -- on states found by search, not asserted from memory. A
     run where they agree everywhere means the quirk has been optimised away.
  2. **An authored cell still draws.** Tag 3's override does not skip the
     generator; the client draws, discards, and uses the authored value. So
     forcing ONE cell must leave every other cell of the map untouched.
     Section 3 forces a cell and requires exactly one output byte to move --
     a reproduction that skipped the draw would shift the whole rest of the
     tile and fail by thousands.

NO VAULT, NO ARCHIVE, NO CLIENT. Every check here is arithmetic over values
this file computes, so it runs on a bare machine -- and that is also its
limit, stated rather than left implied: **nothing here can prove the
traversal matches ArenaNet's**, only that our reproduction is internally
exact and that its two known traps are still armed. The claim these checks
support is "deterministic and faithful to the instructions we read", never
"equal to what the client draws".
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import trnvariation as tv  # noqa: E402
import checks  # noqa: E402

# FLOOR: 22, from a real green run 2026-08-14 (0.2 s). Every section is
# arithmetic and none can be skipped, so a short run means a section died
# rather than that the machine lacked a fixture.
FLOOR = 22


def main(argv=None):
    led = checks.Ledger("terrain variation", floor=FLOOR)
    check = checks.adopt(led)
    t0 = time.perf_counter()

    _section1(check)
    _section2(check)
    _section3(check)
    _section4(check)

    print(f"\n({time.perf_counter() - t0:.1f}s)")
    return led.verdict()


# --- 1. the generator, and the quirk that must survive ----------------------

def _section1(check):
    print("\n== 1. the generator is the instruction sequence, not the maths ==")

    # Determinism and range, the cheap invariants first.
    seen = [tv.rng_next(12345) for _ in range(3)]
    check(len(set(seen)) == 1, "rng_next is a pure function of its state",
          f"{seen}")
    state = 1
    lo = hi = None
    zero = 0
    for _ in range(20000):
        state = tv.rng_next(state)
        lo = state if lo is None else min(lo, state)
        hi = state if hi is None else max(hi, state)
        zero += state == 0
    check(zero == 0, "the state is never 0 over 20,000 steps "
          "(the client substitutes DEFAULT_SEED if it would be)")
    check(1 <= lo and hi <= tv.MOD,
          f"every state lands in 1..{tv.MOD}", f"{lo}..{hi}")

    # THE QUIRK. Find the states where the client's magic-number division
    # disagrees with the textbook modulo -- by SEARCH, so the check rests on
    # the arithmetic rather than on a number typed from a report.
    diverge = []
    state = 1
    for _ in range(200000):
        clean = tv.rng_next_clean(state)
        ours = tv.rng_next(state)
        if ours != clean:
            diverge.append((state, ours, clean))
        state = clean or 1
    check(diverge,
          "the port and the textbook Lehmer step DISAGREE somewhere -- the "
          "client's magic-number division is not a clean modulo",
          f"{len(diverge)} of 200,000 states"
          + (f", first {diverge[0]}" if diverge else ""))
    if diverge:
        rate = 100.0 * len(diverge) / 200000
        check(2.0 <= rate <= 6.0,
              "and it disagrees on the MEASURED ~3.8% of states, not on a "
              "handful and not on most", f"{rate:.2f}%")
        off_by_one = all(ours == clean + 1 for _s, ours, clean in diverge)
        check(off_by_one,
              "every disagreement is exactly +1 -- the quotient is one too "
              "high and the +0x80000000 correction does not cancel it",
              f"{len(diverge)} checked")

    # The correction constant itself is the thing most likely to be
    # "corrected" by a later reader. Pin it against the modulus it is NOT.
    check(tv.UNDERFLOW_FIX == 0x80000000 and tv.UNDERFLOW_FIX != tv.MOD,
          "the underflow correction is 0x80000000 and NOT the modulus "
          "0x7FFFFFFF (bytes 81 c1 00 00 00 80 at 0x0046D149)")


# --- 2. the seed ------------------------------------------------------------

def _section2(check):
    print("\n== 2. the seed, and x in the high word ==")
    check(tv.reseed(3, 7) == (3 << 16) ^ 7,
          "seed = (tile.x << 16) ^ tile.y", f"{tv.reseed(3, 7):#x}")
    check(tv.reseed(0, 0) == tv.DEFAULT_SEED,
          "tile (0,0) would seed 0, so the client substitutes DEFAULT_SEED "
          "-- and every map has that tile", f"{tv.reseed(0, 0):#x}")
    # x and y must not be interchangeable, or the axis reading is untested.
    check(tv.reseed(1, 2) != tv.reseed(2, 1),
          "the axes are NOT symmetric -- x goes in the high word, so a "
          "transposed reading gives a different stream")


# --- 3. an authored cell still draws ---------------------------------------

def _section3(check):
    print("\n== 3. tag 3 overrides the VALUE, never the DRAW ==")
    n = tv.TILE * tv.TILE
    base = tv.tile_variation(5, 9)
    check(len(base) == n and set(base) <= {0, 1, 2, 3},
          f"a tile yields {n} values, all in 0..3")

    # Force ONE cell in the middle and require exactly one byte to move.
    # If the draw were skipped on authored cells every later cell would
    # shift, and this would fail by hundreds.
    at = 400
    authored = bytearray(n)
    forced = 1 + (base[at] % 3)          # any value different from the draw
    authored[at] = forced
    got = tv.tile_variation(5, 9, authored)
    moved = [k for k in range(n) if got[k] != base[k]]
    check(got[at] == forced,
          f"the authored cell takes its forced value {forced}", f"{got[at]}")
    check(moved == [at],
          "and EXACTLY ONE cell changed -- the discarded draw keeps every "
          "later cell in place", f"{len(moved)} moved: {moved[:8]}")

    # The rival that this refutes, run live: skipping the draw shifts the tail.
    def skipping(tile_x, tile_y, authored):
        out = bytearray(n)
        state = tv.reseed(tile_x, tile_y)
        for k in range(n):
            if authored[k]:
                out[k] = authored[k]
                continue                  # THE DEFECT: no draw
            state = tv.rng_next(state)
            out[k] = state & 3
        return bytes(out)

    bad = skipping(5, 9, authored)
    bad_moved = sum(1 for k in range(n) if bad[k] != base[k])
    check(bad_moved > 100,
          "CONTROL: a reproduction that skips the draw on authored cells "
          "moves hundreds of cells, so the check above has power",
          f"{bad_moved} of {n} moved")

    # Authored values pass through unmasked: 3 stays 3.
    authored2 = bytearray(n)
    for k in range(0, n, 7):
        authored2[k] = 3
    got2 = tv.tile_variation(5, 9, authored2)
    check(all(got2[k] == 3 for k in range(0, n, 7)),
          "an authored 3 survives -- the mask applies to the DRAW only")


# --- 4. the map traversal, and the span the read left open ------------------

def _section4(check):
    print("\n== 4. the map, and the two readings of the stream span ==")
    dx, dy = 64, 96
    quads = tv.map_variation(dx, dy)
    check(len(quads) == dx * dy, f"a {dx}x{dy} map yields one value per cell")

    hist = [quads.count(k) for k in range(4)]
    n = dx * dy
    worst = max(abs(h / n - 0.25) for h in hist)
    check(worst < 0.02,
          "the four quadrants come out near-uniform, which is what a 2-bit "
          "mask of a Lehmer stream should do",
          ", ".join(f"{k}:{100 * hist[k] / n:.1f}%" for k in range(4)))

    # Neighbouring TILES must differ: same stream, different seed.
    a = quads[0:tv.TILE]
    b = quads[tv.TILE:2 * tv.TILE]
    check(a != b, "adjacent tiles draw different sequences (different seeds)")

    # THE SPAN CONTROL, and it is the open question made refutable. Under the
    # per-row reseed every row of a tile is IDENTICAL -- a stripe. Under the
    # per-tile reading rows agree only by chance, about 1 cell in 4.
    row = tv.map_variation(dx, dy, span="row")
    row_match = sum(1 for j in range(1, tv.TILE) for i in range(dx)
                    if row[j * dx + i] == row[i])
    tile_match = sum(1 for j in range(1, tv.TILE) for i in range(dx)
                     if quads[j * dx + i] == quads[i])
    total = (tv.TILE - 1) * dx
    check(row_match == total,
          "the per-ROW reading makes every row of a tile identical -- a "
          "visible stripe, which is why it is the disfavoured reading",
          f"{row_match}/{total}")
    check(tile_match < total * 0.4,
          "the per-TILE reading (the default) leaves rows independent",
          f"{tile_match}/{total} = {100 * tile_match / total:.1f}%")
    check(tv.STREAM_SPAN == "tile",
          "and the default is the tile reading -- see trnvariation's THE "
          "OPEN QUESTION for what would change it", f"{tv.STREAM_SPAN!r}")

    # Dims must be gated, the same way the client gates them.
    try:
        tv.map_variation(30, 32)
        bad = False
    except ValueError:
        bad = True
    check(bad, "a map whose dims are not multiples of 32 is REFUSED")


if __name__ == "__main__":
    sys.exit(main())
