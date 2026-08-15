"""Which textures a terrain cell blends, and how each one is masked. Rung T6.

Retail ground is not one texture per cell. A cell samples the tile bytes of
its FOUR CORNERS, and where those disagree the client emits up to three
layers -- a base plus overlays whose alpha fades them in only over the
corners they belong to. T5 drew the base alone, which is why its tile
boundaries are hard edges. This module is the selection rule and the mask.

    from trnblend import cell_layers
    layers = cell_layers(corners, tile_types, variation)
    # -> [Layer(tile, quadrant, rotated, coverage), ...], layers[0] is the base

WHERE IT COMES FROM. Build 38797, read 2026-08-14: `TrnTexBlendHi` at
`0x00761800` (selection), `0x00757A80` (the per-layer UV write), and the
16-entry table at `0x00BF78D8`. `studies/terrain/FINDINGS.md` §7.

THE FOUR CORNERS ARE FOUR CELLS, not four stored vertex values -- terrain tag
2 holds one byte per CELL and nothing per vertex. The caller
(`0x0075E08A`..`0x0075E0D1`) fills a 4-dword array from two row cursors, each
read at its position and at position+1:

    corner 0 = this cell        corner 1 = +x
    corner 2 = +y               corner 3 = +x, +y

and those indices are also the VERTEX indices, because `0x00757A80` writes
`V0=(u,v)`, `V1=(u+du,v)`, `V2=(u,v+dv)`, `V3=(u+du,v+dv)`.

GROUPING IS BY TILE **TYPE**, NOT BY TILE. Each corner's raw byte is mapped
through `tileTypes` (terrain tag 4, `terrain+0x80`) and the COMPARISONS use
that -- which is T2's finding from the other side, and it matters: tag 4 is a
staircase, so several raw tiles can share a type and two corners drawn from
one material group produce NO seam and NO extra layer.

**THE MASK IS THE POINT, AND IT IS NOT A GRADIENT WE INVENT.** Each 128x128
quadrant of a terrain texture is an authored ALPHA COVERAGE SHAPE, and the
table at `0x00BF78D8` maps a 4-bit corner mask to the quadrant (plus a
rotation flag, plus optionally a second layer) whose alpha covers exactly
those corners:

    quadrant 0 covers corners {2, 3}      quadrant 2 covers corners {0, 2}
    quadrant 1 covers corner  {1}         quadrant 3 covers corner  {3}

with a 180-degree rotation mapping corner k to 3-k, which reaches the other
four edges and the other two corners. DERIVED here rather than asserted, and
the derivation is refutable and was refuted-nothing:

  * the four cover sets are read off the four table rows that are UNROTATED
    and single-layer (masks 12, 2, 5, 8 -> quadrants 0, 1, 2, 3);
  * **the client's own inverse table at `0x00BF7808` is `{12, 2, 5, 8}`** --
    the same four numbers, from a different array, written for the lo path
    which never reads `0x00BF78D8`. Two independent witnesses;
  * predicting all 16 rows from that model and requiring each row's layers to
    cover exactly its own mask: **15 of 16**. The one miss is mask 0, the
    empty corner set, which the grouping loop below can never emit because a
    group always holds at least one corner;
  * the rotation reading is corroborated by the UV writer, which for a
    rotated layer swaps V0 with V3 and V1 with V2 (`0x00757B4B`) -- exactly
    `k -> 3-k`.

So a consumer does NOT need to author blend weights: bind the layer's own
texture at the named quadrant, let its alpha do the masking, and the seam is
ArenaNet's.

WHAT IS NOT ESTABLISHED, and it changes which tile is the BASE. Each corner
is fetched as `arr[(sel >> 2k) & 3]` where `sel` is a per-cell byte from a
chunk-local array at `chunk+0x2B4` that the builder fills before this loop --
NOT map data, and where it comes from is NOT FOUND. This module assumes the
IDENTITY selection (corner k = arr[k]), which makes corner 0 -- the base --
this cell's own tile, agreeing with T2's separately measured "the raw tile
byte indexes `m_tiles` directly". If that assumption is wrong the SET of
layers is unchanged and which of them is the opaque base can differ.
`SELECTION` is the switch, and `test_trnblend.py` keeps the consequence
visible rather than hiding it in prose.
"""

import sys

#: `(rotation << 15) | quadrant` per 4-bit corner mask -- VA 0x00BF78D8,
#: read out of `.data` with a stdlib PE walk. Index 0 is unreachable (see
#: the docstring) and is carried so the table is the archive's, not a
#: subset we curated.
COVER_PRIMARY = (0x8000, 0x8003, 0x0001, 0x8000, 0x8001, 0x0002, 0x8001,
                 0x0002, 0x0003, 0x8003, 0x8002, 0x8000, 0x0000, 0x0000,
                 0x0000, 0x8002)
#: The optional SECOND layer for the same group, or -1. VA 0x00BF78DC,
#: interleaved with the above at stride 8.
COVER_SECOND = (0x0000, -1, -1, -1, -1, -1, 0x0001, 0x0001, -1, 0x0003, -1,
                0x0003, -1, 0x8003, 0x0001, 0x0002)

#: Which corners each quadrant's authored alpha covers. DERIVED (docstring),
#: and equal to the client's own inverse table at 0x00BF7808.
QUADRANT_COVERS = (0b1100, 0b0010, 0b0101, 0b1000)

#: The client asserts `varIndex < arrsize(tileVar)`; three texcoord sets.
MAX_LAYERS = 3

#: How corner k is fetched. "identity" is the assumption above.
SELECTION = "identity"


class Layer:
    """One drawn layer of a cell. `coverage` is a 4-bit corner mask.

    `quadrant` names which 128x128 quarter of `tile`'s 256x256 texture to
    sample; `rotated` turns the quad's UV assignment through 180 degrees.
    The BASE layer (index 0) is opaque and its alpha is not a mask.
    """

    __slots__ = ("tile", "quadrant", "rotated", "coverage", "base")

    def __init__(self, tile, quadrant, rotated, coverage, base=False):
        self.tile = tile
        self.quadrant = quadrant
        self.rotated = bool(rotated)
        self.coverage = coverage
        self.base = base

    def __eq__(self, other):
        return (isinstance(other, Layer) and self.tile == other.tile
                and self.quadrant == other.quadrant
                and self.rotated == other.rotated
                and self.coverage == other.coverage and self.base == other.base)

    def __repr__(self):
        return (f"<Layer tile={self.tile} q={self.quadrant}"
                f"{' ROT' if self.rotated else ''} "
                f"covers={self.coverage:04b}{' BASE' if self.base else ''}>")


def rotate_mask(mask):
    """A 180-degree turn of a corner mask: corner k becomes corner 3-k."""
    return sum(((mask >> k) & 1) << (3 - k) for k in range(4))


def quadrant_coverage(word):
    """The corner mask a packed `(rotation << 15) | quadrant` word covers."""
    quad = word & 0x7FFF
    if quad >= len(QUADRANT_COVERS):
        raise ValueError(f"quadrant {quad} is outside 0..3")
    cover = QUADRANT_COVERS[quad]
    return rotate_mask(cover) if word & 0x8000 else cover


def _emit(out, mask, tile):
    """Append the layer(s) the table gives for one group's corner mask."""
    word = COVER_PRIMARY[mask]
    out.append(Layer(tile, word & 0x7FFF, word & 0x8000,
                     quadrant_coverage(word)))
    second = COVER_SECOND[mask]
    if second != -1:
        out.append(Layer(tile, second & 0x7FFF, second & 0x8000,
                         quadrant_coverage(second)))


def cell_layers(corners, tile_types, variation, max_layers=MAX_LAYERS):
    """The ordered layers for one cell. `layers[0]` is the opaque base.

    `corners` is the four corner tile bytes in the order (this, +x, +y, +xy);
    `tile_types` is terrain tag 4 (a raw tile byte indexes it to a type, and
    the grouping compares TYPES); `variation` is the base layer's quadrant
    0..3, which the caller gets from `trnvariation` -- tag 3's override or
    the per-cell draw.

    Transcribed from `0x007618E9`..`0x007619E8`. The dedup loop skips leading
    corners whose TYPE equals corner 0's; the grouping loop then walks the
    rest, merging equal types into one mask and flushing a layer whenever the
    type changes. A cell whose four corners share one type gets ONE layer,
    which is 81.8% of Kamadan and 44.3% of Lornar's Pass.
    """
    if len(corners) != 4:
        raise ValueError(f"{len(corners)} corners, need exactly 4")
    types = []
    for c in corners:
        if c >= len(tile_types):
            raise ValueError(
                f"corner tile {c} is outside the {len(tile_types)}-entry tile "
                f"table; the client indexes tileTypes with the raw byte and "
                f"max(tiles) < len(table_a) holds on 349 of 349 retail maps")
        types.append(tile_types[c])

    out = [Layer(corners[0], variation, False, 0b1111, base=True)]

    k = 1
    while k <= 3 and types[k] == types[0]:
        k += 1
    if k > 3:
        return out                       # one material: no seam, no overlay

    mask = 1 << k
    group_type = types[k]
    repr_tile = corners[k]
    for j in range(k + 1, 4):
        if types[j] == group_type:
            mask |= 1 << j
        else:
            _emit(out, mask, repr_tile)
            mask = 1 << j
            group_type = types[j]
            repr_tile = corners[j]
    _emit(out, mask, repr_tile)

    # The client's own cap, asserted rather than silently exceeded: three
    # texcoord sets, so three layers. A group that would overflow is dropped
    # here the way the assert would stop the client.
    return out[:max_layers]


def map_layers(dim_x, dim_y, tiles, tile_types, variation):
    """`cell_layers` for every cell of a map, world row-major.

    The far column and far row have no `+x` / `+y` neighbour, so they
    REPLICATE the last real one -- the same manufactured edge the height
    lattice uses (`mapexport`'s convention 2), and for the same reason: the
    file stores `dimX * dimY` and the mesh needs one more of each.
    """
    out = []
    for gy in range(dim_y):
        gy1 = min(gy + 1, dim_y - 1)
        for gx in range(dim_x):
            gx1 = min(gx + 1, dim_x - 1)
            corners = (tiles[gy * dim_x + gx], tiles[gy * dim_x + gx1],
                       tiles[gy1 * dim_x + gx], tiles[gy1 * dim_x + gx1])
            out.append(cell_layers(corners, tile_types,
                                   variation[gy * dim_x + gx]))
    return out


def _main(argv=None):
    import argparse
    import collections
    import json
    import os
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export", help="a <name>.gwmap.json")
    args = ap.parse_args(argv)

    HERE = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, HERE)
    from mapexport import load_export           # noqa: E402
    import trnvariation                          # noqa: E402

    exp = load_export(args.export)
    table_a = exp.meta["tile_table_a"]
    var = trnvariation.map_variation(exp.dim_x, exp.dim_y, exp.variation)
    layers = map_layers(exp.dim_x, exp.dim_y, exp.tiles, table_a, var)

    hist = collections.Counter(len(v) for v in layers)
    n = len(layers)
    print(f"{exp.meta['name']}: {exp.dim_x}x{exp.dim_y} = {n} cells")
    for k in sorted(hist):
        print(f"  {k} layer(s): {hist[k]:8d}  {100 * hist[k] / n:5.2f}%")
    extra = sum(len(v) - 1 for v in layers)
    print(f"  overlay quads to draw: {extra} "
          f"({100 * extra / n:.1f}% of the cell count)")
    quads = collections.Counter(v[0].quadrant for v in layers)
    print(f"  base quadrants: "
          + ", ".join(f"{k}:{100 * quads[k] / n:.1f}%" for k in sorted(quads)))
    return 0


if __name__ == "__main__":
    sys.exit(_main())
