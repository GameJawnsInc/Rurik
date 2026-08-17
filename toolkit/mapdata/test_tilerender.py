#!/usr/bin/env python3
r"""Check the atlas-tile renderer: right shape, right place, right way up.

    python toolkit/mapdata/test_tilerender.py

WHAT EARNS THIS FILE. `tilerender.py` produces a picture, and a picture is the
easiest thing in this repo to be wrong about confidently -- it looks like
terrain either way. Three of its decisions are silent failures if inverted:

  * **The sign flip.** Archive heights are NEGATED (greater stored = lower
    ground). Shade the raw numbers and you get a plausible relief map with every
    ridge as a valley. Section 2 asserts BOTH directions: with the flip the
    high side is brighter, and with `negated=False` the relationship INVERTS.
    A one-directional check here would pass on a renderer that ignored the flag.

  * **Where the render lands.** The atlas coordinate is
    `local + footprint_origin`, so map 143's 64x64 belongs at texel (448, 448)
    of tile (1, 0) -- not at the tile's corner. Section 1 derives that from the
    real table and section 4 proves `paste` puts the pixels exactly there and
    touches nothing else.

  * **That it is OUR terrain and not just any terrain.** Section 3 is the one
    that makes this more than "an image appeared": `deploy.gen_plaza` puts a
    cliff at `gx == mid` and a rise on the +x side, and the render must show its
    strongest seam at that column. The generator is the oracle.

Section 3's bound is a WINDOW, not an equality, and the reason is measured: the
raw heightfield's largest column step is at gx=33 -- `gen_plaza`'s own
`elif gx > mid` boundary, dominating the next by far more than 3x -- while the
SHADED gradient peaks within one column either side, because a 3-tap central
difference smears a step. An earlier draft asserted the heightfield stepped at
"exactly one" column; that was read off a top-4 printout and is simply false,
since `gen_plaza` is a gradient on both sides of the plaza. It went red on its
own terrain, which is the check working.

No client run, no archive write. Reads the pinned client for the footprint.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))

import checks                                                  # noqa: E402
import tilerender                                              # noqa: E402
import atex                                                    # noqa: E402

# MEASURED from the green run of 2026-08-17: 17, which is every check in the
# file. Not a "mandatory core" floor, because there is no optional section here
# -- the only skip path is `content.load()` failing, and that is a genuine red
# rather than a degraded run. Note the shared-vault hazard: another session's
# half-written `vault/content/` row makes `content.load()` raise, and this file
# will go red naming it. That is the provenance gate working, not this test.
FLOOR = 17
LEDGER = checks.Ledger("atlas tile renderer (PLAN A3)", floor=FLOOR)
check = checks.adopt(LEDGER)

# Stated as literals so the test carries its own expectation. Map 143's
# footprint origin is (960, 448); 960 = 512 + 448 and 448 = 0 + 448.
MAP = 143
WANT_TILE = (1, 0)
WANT_AT = (448, 448)


def luma(rgb, dim, x0, x1):
    tot = n = 0
    for gy in range(dim):
        for gx in range(x0, x1):
            o = (gy * dim + gx) * 3
            tot += 0.299 * rgb[o] + 0.587 * rgb[o + 1] + 0.114 * rgb[o + 2]
            n += 1
    return tot / max(n, 1)


def main():
    # -- 1. the placement, derived from the real table -----------------------
    print("1. where the render belongs")
    tile, at = tilerender.tile_and_offset(960, 448, 64)
    check(tile == WANT_TILE, f"map {MAP}'s origin lands in tile {WANT_TILE}", str(tile))
    check(at == WANT_AT, f"at texel {WANT_AT} -- NOT the tile corner",
          f"{at}; the corner would be off by 448 and read as a broken renderer")
    check(at[0] + 64 == tilerender.TILE and at[1] + 64 == tilerender.TILE,
          "and 64x64 fits exactly to the tile edge", f"{at[0] + 64}")
    straddled = False
    try:
        tilerender.tile_and_offset(1000, 448, 64)      # 1000 % 512 = 488, +64 > 512
    except SystemExit:
        straddled = True
    check(straddled, "a render that would straddle two tiles is REFUSED",
          "silently truncating it looks like the shading being wrong on one edge")

    try:
        import content
        row = content.load().get("area", "sculpt")
    except Exception as exc:
        LEDGER.skip("everything from section 2", f"content unavailable: {exc}")
        return LEDGER.verdict()
    heights, dim = tilerender.authored_heights(row)
    mid = dim // 2
    check(dim == 64, "the sculpt area is 64x64 cells", str(dim))
    check(len(heights) == dim * dim, "and its heightfield is complete",
          str(len(heights)))

    # -- 2. the sign flip, BOTH directions -----------------------------------
    print("\n2. heights are negated, and the flip is load-bearing")
    lit, _ = tilerender.hillshade(heights, dim, negated=True)
    raw, _ = tilerender.hillshade(heights, dim, negated=False)
    d_lit, r_lit = luma(lit, dim, 0, mid), luma(lit, dim, mid + 1, dim)
    d_raw, r_raw = luma(raw, dim, 0, mid), luma(raw, dim, mid + 1, dim)
    check(r_lit > d_lit + 20,
          "flipped: the RISE side (+x) is brighter than the dip",
          f"rise {r_lit:.1f} vs dip {d_lit:.1f} -- gen_plaza puts the rise at gx > mid")
    check(r_raw < d_raw - 20,
          "UNflipped: the relationship INVERTS -- the control",
          f"rise {r_raw:.1f} vs dip {d_raw:.1f}; a renderer ignoring `negated` "
          f"would pass the check above and fail this one")

    # -- 3. it is OUR terrain: the generator is the oracle --------------------
    print("\n3. the cliff is where gen_plaza put it")
    # gen_plaza is a GRADIENT either side of the plaza, so almost every column
    # differs from its neighbour. The cliff is the LARGEST step, not the only
    # one -- the first version of this section asserted "exactly one" off a
    # top-4 printout and went red on its own terrain.
    rawstep = [sum(abs(heights[gy * dim + gx] - heights[gy * dim + gx - 1])
                   for gy in range(dim)) for gx in range(1, dim)]
    order = sorted(range(1, dim), key=lambda gx: -rawstep[gx - 1])
    biggest, runner = order[0], order[1]
    check(biggest == mid + 1,
          f"the heightfield's LARGEST column step is at gx={mid + 1}",
          f"{biggest} -- gen_plaza's `elif gx > mid` boundary")
    check(rawstep[biggest - 1] > 3 * rawstep[runner - 1],
          "and it dominates the next by more than 3x -- a cliff, not a slope",
          f"{rawstep[biggest - 1]} vs {rawstep[runner - 1]} at gx={runner}")
    grad = [sum(abs(lit[(gy * dim + gx) * 3 + 1] - lit[(gy * dim + gx - 1) * 3 + 1])
                for gy in range(dim)) for gx in range(1, dim)]
    peak = max(range(1, dim), key=lambda gx: grad[gx - 1])
    check(peak in (mid, mid + 1, mid + 2),
          "and the SHADED seam peaks within one column of that cliff",
          f"peak at gx={peak}; a 3-tap central difference smears a step by one "
          f"either side, so the bound is a window rather than an equality")

    # -- 4. paste lands where it is told and touches nothing else ------------
    print("\n4. the paste is contained")
    base = bytes(tilerender.TILE * tilerender.TILE * 3)
    out = tilerender.paste(base, lit, dim, WANT_AT)
    check(len(out) == len(base), "the tile keeps its size", str(len(out)))
    changed = [i for i in range(0, len(out), 3) if out[i:i + 3] != base[i:i + 3]]
    inside = 0
    for i in changed:
        px = (i // 3) % tilerender.TILE
        py = (i // 3) // tilerender.TILE
        if WANT_AT[0] <= px < WANT_AT[0] + dim and WANT_AT[1] <= py < WANT_AT[1] + dim:
            inside += 1
    check(inside == len(changed),
          "every changed texel is inside the intended rectangle",
          f"{len(changed) - inside} stray")
    check(len(changed) <= dim * dim,
          f"and at most {dim * dim:,} texels changed",
          f"{len(changed):,} of {tilerender.TILE ** 2:,} "
          f"({100 * len(changed) / tilerender.TILE ** 2:.2f}% of the tile)")

    # -- 5. the container the client will actually open ----------------------
    print("\n5. it builds a tile the ATEX reader accepts")
    blob = atex.build_image(out, tilerender.TILE, tilerender.TILE)
    cont = atex.parse(blob)
    check(len(cont.levels) == 10, "10 mip levels, like ArenaNet's own tiles",
          str(len(cont.levels)))
    back, bw, bh = atex.decode_rgba(blob, cont, 0)
    check((bw, bh) == (tilerender.TILE, tilerender.TILE),
          "and decodes back at full size", f"{bw}x{bh}")
    o = ((WANT_AT[1] + 1) * tilerender.TILE + WANT_AT[0] + 1)
    src = o * 3
    near = max(abs(back[o * 4 + i] - out[src + i]) for i in range(3))
    check(near < 60, "and a pasted texel survives the DXT1 round trip",
          f"worst channel delta {near} (DXT1 is lossy; this is a structural check)")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
