r"""Render an authored heightfield into a world-map atlas tile. (PLAN A3.)

    python toolkit/mapdata/tilerender.py --area sculpt --preview
    python toolkit/mapdata/tilerender.py --area sculpt --dat <COPY> --out-atex <f>

A1 proved the client draws an atlas tile we wrote; it drew a CHECKERBOARD,
because the point was that the bytes land. This is the other half: make the
picture be OUR MAP -- the compass showing the ridges and valleys the player is
actually standing on.

THREE THINGS THAT ARE MEASURED, NOT CHOSEN, and each is a way to get it wrong:

  * **One texel per terrain cell.** Not a scale we picked -- it is OBSERVED from
    the client's own `add`/`shr 9` and from a five-scale population test where
    the four rivals scored zero (`studies/minimap/FINDINGS.md` 6b.2). So a
    64x64 map renders to exactly 64x64 texels. Any resampling here would be
    inventing a convention the client does not have.

  * **WHERE it lands is derived from the footprint, not from the tile corner.**
    The atlas coordinate is `local + footprint_origin` (`0x008C2782 add edx,eax`)
    before the `shr 9` that picks the tile, so a map's render belongs at
    `origin % 512` inside tile `origin // 512`. For map 143 that is tile (1,0)
    at texel (448, 448) -- the corner, exactly fitting 64x64. Rung A2 settled
    that the ORIGIN is the lever and the rect's SIZE is not; putting the render
    at the tile's own corner instead would be off by 448 texels and would look
    like the renderer failing.

  * **HEIGHTS ARE NEGATED.** In the archive a GREATER stored value is LOWER in
    the world (FINDINGS 25, and `deploy.gen_plaza` writes its rise as
    `base - 8*d` for exactly that reason). Shading the raw numbers inverts every
    slope: ridges read as valleys and the light comes from the wrong side. The
    sign flip is applied once, here, and `--preview` exists so it can be seen.

WHY IT OVERWRITES A SUB-RECTANGLE RATHER THAN THE WHOLE TILE. A1 replaced the
entire 512x512, and a static sweep afterwards found that tile (1,0) is shared by
SIX world-1 area rows (maps 143, 147, 149, 150, 151, 779), so five other maps
silently got our art (6g.4). This starts from ArenaNet's own decoded tile and
paints only the authored map's own cells, so the collateral shrinks from a whole
tile to whatever those maps genuinely overlap. That is a smaller blast radius,
not none -- and the tool prints the overwritten fraction so it is never implicit.

Standard library only. Read-only on every archive it opens; it emits an ATEX
blob and never writes into a `Gw.dat` -- `datmove` is the tool that does that,
deliberately kept separate so the writer stays the one place that can destroy
4 GB.
"""

from __future__ import annotations

import argparse
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))

import archive as archive_mod                                  # noqa: E402
import atex                                                    # noqa: E402
import png                                                     # noqa: E402
import vaultpath                                               # noqa: E402

TILE = 512
CELL = 96.0            # world units per terrain cell; the atlas scale too

# Light from the north-west and fairly high, the cartographic default -- and,
# more usefully here, NOT aligned with our test terrain's own rise, because a
# light running along the slope direction flattens the very feature the render
# is meant to show.
AZIMUTH_DEG = 315.0
ALTITUDE_DEG = 50.0


def tile_and_offset(origin_x, origin_y, dim, tile=TILE):
    """((tx, ty), (ox, oy)) for a render of `dim` cells at a footprint origin.

    Refuses a render that would straddle two tiles: that needs two writes and
    two `datmove`s, and silently truncating it would look like the shading
    being wrong on one edge.
    """
    tx, ty = origin_x // tile, origin_y // tile
    ox, oy = origin_x % tile, origin_y % tile
    if ox + dim > tile or oy + dim > tile:
        raise SystemExit(
            f"a {dim}x{dim} render at origin ({origin_x}, {origin_y}) straddles "
            f"a tile boundary (offset ({ox}, {oy}) + {dim} > {tile}). That needs "
            f"one write per tile; this tool does one.")
    return (tx, ty), (ox, oy)


def hillshade(heights, dim, azimuth=AZIMUTH_DEG, altitude=ALTITUDE_DEG,
              pitch=CELL, negated=True):
    """(rgb_bytes, stats) -- a shaded-relief image, `dim` x `dim`, row-major.

    `heights` is indexed [gy * dim + gx] in WORLD row-major order, which is the
    order `mapexport` writes its de-tiled sidecar in. `negated=True` applies the
    archive's own sign convention (greater stored value = lower ground).
    """
    z = [(-h if negated else h) for h in heights]
    az = math.radians(azimuth)
    alt = math.radians(altitude)
    lo, hi = min(z), max(z)
    span = (hi - lo) or 1.0

    out = bytearray(dim * dim * 3)
    for gy in range(dim):
        for gx in range(dim):
            # Central differences, clamped at the edges. A one-sided difference
            # at the border is what makes the outer ring shade like its
            # neighbour instead of like a cliff.
            xm, xp = max(gx - 1, 0), min(gx + 1, dim - 1)
            ym, yp = max(gy - 1, 0), min(gy + 1, dim - 1)
            dzdx = (z[gy * dim + xp] - z[gy * dim + xm]) / (((xp - xm) or 1) * pitch)
            dzdy = (z[yp * dim + gx] - z[ym * dim + gx]) / (((yp - ym) or 1) * pitch)
            slope = math.atan(math.hypot(dzdx, dzdy))
            aspect = math.atan2(dzdy, -dzdx)
            shade = (math.cos(alt) * math.cos(slope)
                     + math.sin(alt) * math.sin(slope) * math.cos(az - aspect))
            shade = max(0.0, min(1.0, shade))
            # Hypsometric tint so the picture reads as terrain rather than grey
            # noise at compass size: low ground green, high ground pale.
            t = (z[gy * dim + gx] - lo) / span
            base = (60 + 120 * t, 110 + 110 * t, 55 + 90 * t)
            o = (gy * dim + gx) * 3
            for i in range(3):
                out[o + i] = max(0, min(255, int(base[i] * (0.35 + 0.65 * shade))))
    return bytes(out), {"min": lo, "max": hi, "span": span}


def decode_tile(dat, file_id):
    """(rgb_bytes, mft_row) for ArenaNet's tile, or (None, None).

    RAW lookup on purpose: the client compares 32 bits exactly, so a tile our
    permissive reader can find but the client cannot is not a tile we may build
    on (studies/minimap/FINDINGS.md 6d.3).
    """
    ar = archive_mod.Archive(dat)
    try:
        row = archive_mod.file_id_table(ar, raw=True).get(file_id)
        if row is None:
            return None, None
        data = ar.read(ar.row(row))
    finally:
        ar.close()
    cont = atex.parse(data)
    # decode_rgba returns (rgba, width, height) -- unpacking it matters: the
    # first version indexed the TUPLE as if it were the pixel buffer, which
    # only fails once a real --dat is supplied, i.e. exactly when it counts.
    rgba, w, h = atex.decode_rgba(data, cont, 0)
    if (w, h) != (TILE, TILE):
        raise SystemExit(f"tile decoded {w}x{h}, expected {TILE}x{TILE}")
    rgb = bytearray(TILE * TILE * 3)
    for i in range(TILE * TILE):
        rgb[i * 3:i * 3 + 3] = rgba[i * 4:i * 4 + 3]
    return bytes(rgb), row


def paste(tile_rgb, render, dim, at, tile=TILE):
    """Paint `render` into a copy of `tile_rgb` at texel `at`. Returns bytes."""
    ox, oy = at
    out = bytearray(tile_rgb)
    for gy in range(dim):
        dst = ((oy + gy) * tile + ox) * 3
        src = (gy * dim) * 3
        out[dst:dst + dim * 3] = render[src:src + dim * 3]
    return bytes(out)


def authored_heights(area_row):
    """The area's heightfield in WORLD row-major order.

    `deploy`'s generators write through `Terrain.index`, which is the archive's
    TILED order; the shader wants row-major, the same order `mapexport`'s
    sidecar uses. Converting here keeps that one convention in one place.
    """
    import deploy
    import terrain as trn_mod
    dim, dim_y = deploy.area_dims(area_row)
    if dim_y != dim:
        raise SystemExit(f"tilerender draws a SQUARE footprint; this area is "
                         f"{dim}x{dim_y} (SLICE-B6's corridor is the first "
                         f"rectangle, and its atlas tile is unbuilt)")
    tiled = deploy.GENERATORS[area_row.get("heights", "flat")](dim)
    return [tiled[trn_mod.Terrain.index(gx, gy, dim)]
            for gy in range(dim) for gx in range(dim)], dim


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--area", default="sculpt", help="authored area to render")
    ap.add_argument("--map", type=lambda s: int(s, 0), default=None,
                    help="area row whose footprint origin to place at "
                         "(default: the area's own map_id)")
    ap.add_argument("--exe", help="client to read the footprint from")
    ap.add_argument("--dat", help="archive to take the ORIGINAL tile from; "
                                  "without it the rest of the tile is blanked")
    ap.add_argument("--out-atex", help="write the ATEX blob here")
    ap.add_argument("--preview", action="store_true",
                    help="also write PNGs of the render and the composed tile")
    a = ap.parse_args(argv)

    import content
    world = content.load()
    # `world.get(kind, key)` is the accessor `deploy.py` uses; reaching into a
    # raw dict would bypass content.py's provenance checks, which is the one
    # thing every consumer of content/ must not do.
    try:
        row = world.get("area", a.area)
    except Exception as exc:
        raise SystemExit(f"no area {a.area!r} in content/areas.toml: {exc}")
    heights, dim = authored_heights(row)
    map_id = a.map if a.map is not None else int(row["map_id"])

    import consttable, maprows, pinned, worldmap
    pe = maprows.PE(a.exe or pinned.find()[0])
    t = consttable.table_for(pe, "s_missionClientData")
    rec = t.record(pe, map_id)
    x0, y0, x1, y1 = struct.unpack_from("<4i", rec, 0x48)
    world_idx = struct.unpack_from("<I", rec, 0x04)[0]
    print(f"area {a.area}: {dim}x{dim} cells, map {map_id}, world {world_idx}")
    print(f"  footprint origin ({x0}, {y0})  size {x1 - x0} x {y1 - y0}")

    (tx, ty), at = tile_and_offset(x0, y0, dim)
    print(f"  -> tile ({tx}, {ty}) at texel {at}  (one texel per cell)")

    tiles = {(q.x, q.y): q.file_id for q in worldmap.tiles(pe)
             if q.world == world_idx and q.tier == "chunk" and q.file_id}
    fid = tiles.get((tx, ty))
    print(f"  atlas file id: {fid}")

    render, stats = hillshade(heights, dim)
    print(f"  heights {stats['min']:.0f}..{stats['max']:.0f} after the sign "
          f"flip (greater stored = lower ground)")

    if a.dat and fid:
        base_rgb, arow = decode_tile(a.dat, fid)
        if base_rgb is None:
            raise SystemExit(f"file id {fid} does not bind RAW in {a.dat} -- "
                             f"the client could not address it either.")
        print(f"  original tile from row {arow}: overwriting "
              f"{dim * dim:,} of {TILE * TILE:,} texels "
              f"({100 * dim * dim / (TILE * TILE):.2f}%)")
    else:
        base_rgb = bytes(TILE * TILE * 3)
        print("  no --dat: the rest of the tile is BLANK, which would black out "
              "every neighbouring map that shares it")

    composed = paste(base_rgb, render, dim, at)
    blob = atex.build_image(composed, TILE, TILE)
    print(f"  ATEX: {len(blob):,} bytes, {len(atex.parse(blob).levels)} levels")

    out_dir = os.path.join(vaultpath.vault_root(), "exports", "worldmap")
    os.makedirs(out_dir, exist_ok=True)
    if a.preview:
        png.write(os.path.join(out_dir, f"a3_{a.area}_render.png"),
                  render, dim, dim, colour=png.COLOUR_RGB)
        png.write(os.path.join(out_dir, f"a3_{a.area}_tile.png"),
                  composed, TILE, TILE, colour=png.COLOUR_RGB)
        print(f"  preview: a3_{a.area}_render.png, a3_{a.area}_tile.png")
    if a.out_atex:
        with open(a.out_atex, "wb") as f:
            f.write(blob)
        print(f"  wrote {a.out_atex}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
