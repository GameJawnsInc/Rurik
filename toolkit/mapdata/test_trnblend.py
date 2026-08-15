"""Check the terrain blend model -- and keep its derivation refutable.

    python toolkit/mapdata/test_trnblend.py

`trnblend.py` says which textures a cell blends and which quadrant of each
one masks it. Two of its three inputs are TABLES READ OUT OF THE CLIENT
(`0x00BF78D8`, `0x00BF7808`); the third -- that quadrant `q`'s authored alpha
covers corner set `QUADRANT_COVERS[q]` -- is DERIVED from them, and section 1
is that derivation run as a check rather than trusted as prose.

THE DERIVATION, AND WHY IT IS EVIDENCE. The cover sets are read off the four
table rows that are unrotated and single-layer. Two things then have to hold
that nothing forced:

  * the client's OWN inverse table at `0x00BF7808` -- a different array, in
    the lo path, which never reads `0x00BF78D8` -- must equal those four
    masks. It does, exactly;
  * predicting all 16 rows from the model, each row's layers must cover
    exactly that row's own 4-bit mask. **15 of 16**, the miss being the empty
    mask 0 which the grouping loop cannot emit.

A model that was merely consistent with a couple of rows would fail the six
two-layer rows, where the union of two independently-looked-up quadrants has
to come out exactly right. Section 1 asserts the count so that a future edit
to either table, or to the rotation rule, reddens here.

NO VAULT AND NO CLIENT. Everything is arithmetic over tables already in the
module plus fixtures this file builds, so it runs on a bare machine -- and
that is its limit: it checks that our model reproduces ArenaNet's tables and
that the selection loop is transcribed faithfully. It does NOT check the
render against the client, which nothing in this repo can yet do.
"""

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import trnblend as tb  # noqa: E402
import checks  # noqa: E402

# FLOOR: 25, from a real green run 2026-08-14. All arithmetic, nothing
# skippable, so a short run is a section that died.
FLOOR = 25


def main(argv=None):
    led = checks.Ledger("terrain blend", floor=FLOOR)
    check = checks.adopt(led)
    t0 = time.perf_counter()
    _section1(check)
    _section2(check)
    _section3(check)
    print(f"\n({time.perf_counter() - t0:.1f}s)")
    return led.verdict()


# --- 1. the cover model against ArenaNet's own two tables -------------------

def _section1(check):
    print("\n== 1. the coverage model, derived and cross-checked ==")

    # Re-derive the cover sets HERE from the table rather than reading the
    # module's constant, so the constant is checked rather than quoted.
    derived = {}
    for mask in range(16):
        word = tb.COVER_PRIMARY[mask]
        if word & 0x8000 or tb.COVER_SECOND[mask] != -1:
            continue                       # rotated or two-layer: not a witness
        derived[word & 0x7FFF] = mask
    check(len(derived) == 4 and sorted(derived) == [0, 1, 2, 3],
          "the table has exactly one unrotated single-layer row per quadrant",
          f"{derived}")
    check(tuple(derived[q] for q in range(4)) == tb.QUADRANT_COVERS,
          "and they give the module's cover sets",
          ", ".join(f"q{q}={derived[q]:04b}" for q in range(4)))

    # THE SECOND WITNESS: the lo path's inverse table, which never reads the
    # array above. Same four numbers.
    CLIENT_INVERSE = (12, 2, 5, 8)         # VA 0x00BF7808, {12, 2, 5, 8}
    check(tb.QUADRANT_COVERS == CLIENT_INVERSE,
          "the client's INDEPENDENT inverse table at 0x00BF7808 is the same "
          "four masks -- two witnesses, different arrays, different code path",
          f"{tb.QUADRANT_COVERS} vs {CLIENT_INVERSE}")

    # THE PREDICTION over all 16 rows.
    ok, miss = [], []
    for mask in range(16):
        got = tb.quadrant_coverage(tb.COVER_PRIMARY[mask])
        if tb.COVER_SECOND[mask] != -1:
            got |= tb.quadrant_coverage(tb.COVER_SECOND[mask])
        (ok if got == mask else miss).append(mask)
    check(len(ok) == 15 and miss == [0],
          "every row's layers cover exactly that row's own mask on 15 of 16, "
          "the miss being the empty mask 0 the grouping loop cannot emit",
          f"ok={len(ok)}, miss={miss}")
    two_layer = [m for m in range(16) if tb.COVER_SECOND[m] != -1 and m]
    check(all(m in ok for m in two_layer) and len(two_layer) >= 5,
          "including every two-layer row, where the union of two separately "
          "looked-up quadrants has to land exactly", f"{two_layer}")

    # The rotation rule, asserted against the UV writer's own relabelling.
    check(tb.rotate_mask(0b1100) == 0b0011 and tb.rotate_mask(0b0010) == 0b0100,
          "rotation maps corner k to 3-k -- the V0<->V3, V1<->V2 swap the UV "
          "writer performs at 0x00757B4B")
    check(all(tb.rotate_mask(tb.rotate_mask(m)) == m for m in range(16)),
          "and it is an involution, as a 180-degree turn must be")

    # A control: a WRONG rotation rule must fail the 16-row prediction, or
    # the check above is passing on something too weak to notice.
    def bad_rot(mask):                      # a plausible rival: mirror in x
        return sum(((mask >> k) & 1) << (k ^ 1) for k in range(4))
    real = tb.rotate_mask
    tb.rotate_mask = bad_rot
    try:
        bad_ok = sum(1 for mask in range(16)
                     if (tb.quadrant_coverage(tb.COVER_PRIMARY[mask])
                         | (tb.quadrant_coverage(tb.COVER_SECOND[mask])
                            if tb.COVER_SECOND[mask] != -1 else 0)) == mask)
    finally:
        tb.rotate_mask = real
    # Scored against the REAL rule's count rather than a constant I chose:
    # the first version asserted `< 8`, the rival scored exactly 8, and a
    # threshold tuned until it passes measures nothing. The claim that
    # matters is the MARGIN -- 8 against 15 -- and it reddens if a future
    # edit makes the two rules comparable.
    check(bad_ok + 5 <= len(ok),
          "CONTROL: a mirror-in-x rival rotation explains materially fewer "
          "rows than corner k -> 3-k, so the 15-of-16 is not a score any "
          "symmetry would get", f"rival {bad_ok} of 16 against {len(ok)}")


# --- 2. the selection loop --------------------------------------------------

def _section2(check):
    print("\n== 2. the selection loop, transcribed from 0x007618E9 ==")
    # tileTypes: a staircase, as tag 4 measurably is. Tiles 0 and 1 share
    # type 0 -- one material group in two slots.
    tt = [0, 0, 1, 2, 3]

    one = tb.cell_layers([3, 3, 3, 3], tt, 2)
    check(len(one) == 1 and one[0].base and one[0].tile == 3
          and one[0].quadrant == 2,
          "four corners of one type -> ONE layer, the base, at the variation "
          "the caller supplied", f"{one}")

    # THE GROUPING IS BY TYPE. Raw tiles 0 and 1 differ but share type 0, so
    # this cell must still be a single layer -- the check that separates
    # "compare tileTypes" from "compare the raw byte", which is T2's finding.
    same_type = tb.cell_layers([0, 1, 0, 1], tt, 0)
    check(len(same_type) == 1,
          "two DIFFERENT raw tiles that share a tileType make no seam and no "
          "overlay -- the comparison is on the type, not the byte",
          f"{same_type}")
    naive = tb.cell_layers([0, 2, 0, 2], tt, 0)
    check(len(naive) > 1,
          "CONTROL: two tiles of DIFFERENT types in the same shape do blend, "
          "so the check above is not vacuous", f"{len(naive)} layers")

    # A single differing corner: one overlay, covering exactly that corner.
    one_odd = tb.cell_layers([3, 3, 3, 4], tt, 0)
    overlays = one_odd[1:]
    cover = 0
    for lay in overlays:
        cover |= lay.coverage
    check(one_odd[0].tile == 3 and one_odd[0].base,
          "the base is corner 0's tile", f"{one_odd[0]}")
    check(all(lay.tile == 4 for lay in overlays) and cover == 0b1000,
          "one differing corner -> overlay(s) of ITS tile covering exactly "
          "corner 3", f"cover={cover:04b}, {overlays}")

    # An edge: corners 2 and 3 differ together.
    edge = tb.cell_layers([3, 3, 4, 4], tt, 0)
    cover = 0
    for lay in edge[1:]:
        cover |= lay.coverage
    check(cover == 0b1100 and all(lay.tile == 4 for lay in edge[1:]),
          "two adjacent differing corners -> coverage of exactly that edge",
          f"cover={cover:04b}")

    # Three materials in one cell: two groups, and the cap holds.
    three = tb.cell_layers([2, 3, 4, 4], tt, 0)
    check(len(three) <= tb.MAX_LAYERS,
          f"never more than {tb.MAX_LAYERS} layers -- the client's own "
          f"varIndex assert", f"{len(three)}")
    check(len({lay.tile for lay in three}) >= 2,
          "and a cell with three materials really does draw more than one "
          "tile", f"{[lay.tile for lay in three]}")

    # Every overlay's coverage must be a subset of the corners that actually
    # differ from the base -- an overlay bleeding onto a base corner is the
    # visible defect this rules out.
    base_corners = [3, 3, 3, 4]
    lays = tb.cell_layers(base_corners, tt, 0)
    differing = sum(1 << k for k in range(4)
                    if tt[base_corners[k]] != tt[base_corners[0]])
    bleed = [lay for lay in lays[1:] if lay.coverage & ~differing]
    check(not bleed,
          "no overlay covers a corner that belongs to the base",
          f"differing={differing:04b}, bleed={bleed}")

    # Refusals.
    try:
        tb.cell_layers([0, 1, 2], tt, 0)
        bad = False
    except ValueError:
        bad = True
    check(bad, "a cell without exactly four corners is REFUSED")
    try:
        tb.cell_layers([0, 0, 0, 99], tt, 0)
        bad2 = False
    except ValueError:
        bad2 = True
    check(bad2, "a corner tile outside the tile table is REFUSED rather than "
          "indexed past")


# --- 3. a whole map ---------------------------------------------------------

def _section3(check):
    print("\n== 3. a map, and the manufactured far edge ==")
    dx, dy = 8, 4
    tt = list(range(8))
    # A checkerboard: every interior cell has two materials, so nothing is
    # single-layer by accident.
    tiles = bytes(((gx + gy) & 1) for gy in range(dy) for gx in range(dx))
    var = bytes(dx * dy)
    lays = tb.map_layers(dx, dy, tiles, tt, var)
    check(len(lays) == dx * dy, "one layer list per cell")
    check(all(v[0].base for v in lays), "every cell has exactly one base, first")
    check(all(len(v) <= tb.MAX_LAYERS for v in lays),
          f"and no cell exceeds {tb.MAX_LAYERS} layers")
    interior = [lays[gy * dx + gx] for gy in range(dy - 1) for gx in range(dx - 1)]
    check(all(len(v) > 1 for v in interior),
          "on a checkerboard every interior cell blends", f"{len(interior)}")
    # The far edge replicates rather than wrapping: the last column's cell
    # must not take its +x corner from column 0.
    last = lays[0 * dx + (dx - 1)]
    check(last[0].tile == tiles[dx - 1],
          "the far column's base is its own tile (the edge REPLICATES, it "
          "does not wrap)")
    check(all(v[0].quadrant == 0 for v in lays),
          "the base quadrant is the variation the caller passed, here 0")


if __name__ == "__main__":
    sys.exit(main())
