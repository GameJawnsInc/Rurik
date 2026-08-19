"""Read a `trnblock.dll` capture and test the arg4 != 0 claims offline.

    python studies/terrain/tag3check.py --row 34429 --tile 4 3

WHAT THIS DECIDES. Every client-truth number in FINDINGS 7.11-7.14 comes
from a block where terrain tag 3 is zero on every cell, so two things have
never been tested against the client at all:

  H1  `trnvariation` claim 1 -- "the draw happens either way". An authored
      cell consumes its place in the PRNG stream and ignores what it drew.
      The rival is that an authored cell SKIPS the draw, which shifts every
      later cell in the tile. On the target block the two predict different
      base quadrants on 331 of 1024 cells, so the capture separates them.

  H2  the base quadrant of an AUTHORED cell is the authored value itself.

  H3  7.14's cover-word rule -- mask built from PHYSICAL positions via
      `perm[k]` -- holds unchanged when tag 3 is authored. If it does not,
      the 212/212 was one block's accident.

THE OFFSET TRAP THIS FILE EXISTS TO AVOID. `test_trnblend.py` §5 walks the
capture with `o = 16 + 4*n + 8*n`, which has NO TERM for the 16-byte-per-cell
UV block that `trnlayers.c` (and this hook) write between the rng and window
arrays. Fed a modern capture, that formula misaligns every window by 16 bytes
per record and scores silently wrong -- not a skip and not a crash. The
layout is asserted here from the header rather than assumed.

Python 3 + the toolkit. No client needed; reruns forever from the .bin.
"""

import argparse
import os
import struct
import sys
from collections import Counter

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, "toolkit", "mapdata"))

import archive as ar                      # noqa: E402
import mapexport                          # noqa: E402
import trnblend                           # noqa: E402
import trnvariation                       # noqa: E402
from toolkit import vaultpath             # noqa: E402

TILE = 32


def load_capture(path):
    """`(base, [record dicts])`, with the layout checked against the file."""
    blob = open(path, "rb").read()
    n, lo, win_len, base = struct.unpack_from("<IIII", blob, 0)
    head = 16
    want = head + n * (4 + 8 + 16 + win_len)
    if len(blob) != want:
        raise SystemExit(
            f"[FAIL] {os.path.basename(path)} is {len(blob)} bytes; a "
            f"{n}-record file with win_len {win_len} and a UV block is "
            f"{want}. If it is {want - 16 * n}, the hook was built without "
            f"the UV block and every window read below would be 16 bytes "
            f"per record out -- the test_trnblend §5 trap.")
    ebp_at = head
    rng_at = ebp_at + 4 * n
    uv_at = rng_at + 8 * n
    win_at = uv_at + 16 * n
    recs = []
    for i in range(n):
        seed, stream = struct.unpack_from("<II", blob, rng_at + 8 * i)
        w = blob[win_at + i * win_len: win_at + (i + 1) * win_len]

        def dw(off):                      # off is relative to ebp
            return struct.unpack_from("<I", w, off + lo)[0]

        recs.append({
            "seed": seed, "stream": stream,
            "types": [dw(-0x34) & 0xFF, dw(-0x30) & 0xFF,
                      dw(-0x2C) & 0xFF, dw(-0x28) & 0xFF],
            "slots": [dw(-0x10), dw(-0x0C), dw(-0x08)],
            "sel": dw(0x10) & 0xFF,
            "arg4": dw(0x14) & 3,
        })
    return base, recs


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--row", type=int, required=True, help="the map's MFT row")
    ap.add_argument("--tile", nargs=2, type=int, required=True,
                    metavar=("TX", "TY"))
    ap.add_argument("--capture", default="layers_block.bin")
    args = ap.parse_args(argv)
    tx, ty = args.tile

    path = os.path.join(vaultpath.require_dir("research", "terrain"),
                        args.capture)
    if not os.path.exists(path):
        raise SystemExit(f"[FAIL] no capture at {path}")
    base, recs = load_capture(path)
    print(f"[ok] {len(recs)} records from {os.path.basename(path)}")

    seeds = Counter(r["seed"] for r in recs)
    want_seed = trnvariation.reseed(tx, ty)
    print(f"[ok] block seeds present: "
          f"{ {hex(k): v for k, v in seeds.items()} }")
    if list(seeds) != [want_seed]:
        raise SystemExit(f"[FAIL] capture is not purely block ({tx},{ty}) "
                         f"= {hex(want_seed)}")
    print(f"[PASS] every record is block ({tx},{ty}) = {hex(want_seed)}")

    arg4 = Counter(r["arg4"] for r in recs)
    print(f"[ok] arg4 histogram: {dict(sorted(arg4.items()))}")
    if len(arg4) == 1 and 0 in arg4:
        raise SystemExit("[FAIL] arg4 is 0 on every cell -- this capture "
                         "cannot test anything 7.13's caveat is about")
    print(f"[PASS] the capture carries AUTHORED tag 3: "
          f"{sum(v for k, v in arg4.items() if k)} of {len(recs)} cells")

    # --- the offline model, from the archive -------------------------------
    mf = mapexport.MapFile.from_row(args.row, ar.Archive())
    trn = mf.terrain()
    dim_x, dim_y = trn.dim_x, trn.dim_y
    tiles = mapexport.detile(trn.tiles, dim_x, dim_y)
    authored = trn.variation()
    table_a = trn.table_a

    def var_map(consume):
        """Base quadrants for the whole map. `consume` is H1."""
        out = bytearray(dim_x * dim_y)
        for by in range(dim_y // TILE):
            for bx in range(dim_x // TILE):
                state = trnvariation.reseed(bx, by)
                for j in range(TILE):
                    for i in range(TILE):
                        k = (by * TILE + j) * dim_x + bx * TILE + i
                        a = authored[k]
                        if consume or not a:
                            state = trnvariation.rng_next(state)
                        out[k] = a if a else (state & 3)
        return bytes(out)

    var_consume, var_skip = var_map(True), var_map(False)

    # The capture is one block in build order; index it the way the client
    # walks it. Cell (cx, cy) within the block, x fast -- the same order
    # `trnvariation` walks and the reseed convention already confirmed.
    hits = {"H1_consume": 0, "H1_skip": 0, "H2": 0, "H2_n": 0,
            "H3": 0, "H3_n": 0}
    for idx, r in enumerate(recs):
        if idx >= TILE * TILE:
            break
        cx, cy = idx % TILE, idx // TILE
        gx, gy = tx * TILE + cx, ty * TILE + cy
        k = gy * dim_x + gx
        base_q = (r["slots"][0] >> 16) & 0x7FFF
        hits["H1_consume"] += (base_q == var_consume[k])
        hits["H1_skip"] += (base_q == var_skip[k])
        if r["arg4"]:
            hits["H2_n"] += 1
            hits["H2"] += (base_q == r["arg4"])

        gx1, gy1 = min(gx + 1, dim_x - 1), min(gy + 1, dim_y - 1)
        corners = (tiles[gy * dim_x + gx], tiles[gy * dim_x + gx1],
                   tiles[gy1 * dim_x + gx], tiles[gy1 * dim_x + gx1])
        sel = trnblend.corner_selector(tuple(table_a[c] for c in corners))
        perm = tuple((sel >> (2 * kk)) & 3 for kk in range(4))
        lays = trnblend.cell_layers(tuple(corners[p] for p in perm), table_a,
                                    base_q, perm=perm)
        ours = [((0x8000 if L.rotated else 0) | (L.quadrant & 3))
                for L in lays[1:]]
        theirs = [(s >> 16) & 0xFFFF for s in r["slots"][1:] if s != 0xFFFFFFFF
                  and ((s >> 16) & 0xFFFF) != 0xFFFF]
        if theirs:
            hits["H3_n"] += 1
            hits["H3"] += (ours == theirs)

    n = min(len(recs), TILE * TILE)
    print()
    print(f"H1  base quadrant == draw-CONSUMED model : {hits['H1_consume']}/{n}"
          f" = {hits['H1_consume']/n:.1%}")
    print(f"H1  base quadrant == draw-SKIPPED model  : {hits['H1_skip']}/{n}"
          f" = {hits['H1_skip']/n:.1%}")
    print(f"H2  authored cell draws its authored value: {hits['H2']}/"
          f"{hits['H2_n']}")
    print(f"H3  our cover words == the client's       : {hits['H3']}/"
          f"{hits['H3_n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
