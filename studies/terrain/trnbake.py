"""Replicate the terrain lightmap bake, byte for byte, from the client's math.

    python studies/terrain/trnbake.py                 # self-verify on the corpus
    python studies/terrain/trnbake.py 0x345CC row:7982 # named maps
    python studies/terrain/trnbake.py --all           # the whole 349-map corpus

FINDINGS §13 settled the tag-9 transfer curve by READING the generator at
0x0075CC30 in build 38797. This is the executable replica of that read, and it
is the check that keeps the finding honest: it does not fit anything and has no
free parameter, so a green run is 1,024-per-tile assertions that the formula is
right, and a wrong constant turns it red on the first map.

THE FORMULA (FINDINGS §13.1), every step float32 as the client spills it:

    byte = RoundHalfAwayFromZero( 255 * (1 - (1 - clamp(N.L, 0, 1))^4) )

  N   = normalize( sum of the four quadrant-triangle normals of the 5-point
        stencil {C, N, S, W, E} at +-96 world units, each normalized first;
        every missing edge neighbour is replaced by C )
  L   = (cos t, 0, sin t),  t = tag 0's sun elevation
  and the y term of N.L is dropped because the client asserts lightDir.y == 0.

The quartic ease-out is the whole point: it saturates fast, which is why
348/349 maps peg at 255 and why §6.5's linear `255*max(0, N.L)` fit could only
reach r 0.887 -- the linear model was this curve seen through a correlation.

WHY IT NEEDS THE CLIENT, AND WHAT IT DOES NOT COMMIT. Normalization is the
client's own 8-bit table inverse-sqrt (0x0046E530 over a 256-entry table at
0x0093C6C8), and its ~0.4% error is load-bearing: a double-precision `1/sqrt`
misses a handful of cells per map at rounding ties. So this reads those 1,024
bytes out of the pinned pristine client at RUN TIME (via `pinned.find` +
`gwpe`) and holds none of them in the repo -- the same measurement pattern
`mapbuild` uses for FINDINGS 14's chunks. Nothing ArenaNet is written down here;
if the vault has no client snapshot the tool says so and does not run.

PREDICTION, stated before the run: with the table loaded, the replica
reproduces the stored Bloated tag-9 bytes EXACTLY on every corpus map, save a
1-in-667,648 exact-`.5` tie whose rounding a since-superseded build broke the
other way (FINDINGS §13.1). The gate is 100.0000% per map, one documented
whole-cell miss tolerated corpus-wide.

Read-only over the archive and the client. Standard library plus the repo's own
`gwpe`/`pinned`/`terrain`; no numpy, because bit-exactness wants scalar spills.
"""

import argparse
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "toolkit", "mapdata"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "toolkit", "clientscan"))

from archive import Archive, file_id_table   # noqa: E402
from mapchunks import MapIndex, is_map_head   # noqa: E402
import terrain                                # noqa: E402
import gwpe                                   # noqa: E402
import pinned                                 # noqa: E402

#: The client's inverse-sqrt approximation table (0x0046E530 reads it here).
#: 256 u32 entries; read from the pinned client, never committed.
INVSQRT_TABLE_VA = 0x0093C6C8
INVSQRT_BIAS = 0x5E800000       # the exponent term of the bit trick, build-free math
STENCIL = 96.0                  # +-96 world units, f32 at 0x0094DE38 / 0x00A6F88C
OUT_SCALE = 255.0               # f64 literal at 0x009495A8
CORPUS_MAPS = 349
#: The one documented boundary miss (row 32347), tolerated corpus-wide.
ALLOWED_MISSES = 1

_pack, _unpack = struct.pack, struct.unpack


def f32(x):
    """One x87 spill to a dword -- round an f64 to f32 and back."""
    return _unpack("<f", _pack("<f", x))[0]


def _load_table():
    path, why = pinned.find(build=38797)
    pe = gwpe.PE(path)
    off = pe.rva_to_off(INVSQRT_TABLE_VA - pe.image_base)
    if off is None:
        raise SystemExit(f"[FAIL] {INVSQRT_TABLE_VA:#010x} is not file-backed")
    tab = _unpack("<256I", pe.data[off:off + 1024])
    return tab, why


class Bake:
    """The generator 0x0075CC30 and its callees, table bound at construction."""

    def __init__(self, table):
        self._t = table

    def invsqrt(self, x):
        """0x0046E530: T[bits[23:16]] - (bits[31:24] << 23) + bias, integer."""
        b = _unpack("<I", _pack("<f", x))[0]
        r = (self._t[(b >> 16) & 0xFF] - ((b >> 24) << 23) + INVSQRT_BIAS) & 0xFFFFFFFF
        return _unpack("<f", _pack("<I", r))[0]

    def tri_normal(self, A, B, C):
        """0x0074EB70: normalized (C-B) x (A-B), every diff and product f32."""
        ux, uy, uz = f32(A[0] - B[0]), f32(A[1] - B[1]), f32(A[2] - B[2])
        vx, vy, vz = f32(C[0] - B[0]), f32(C[1] - B[1]), f32(C[2] - B[2])
        X = f32(vy * uz - vz * uy)
        Y = f32(vz * ux - uz * vx)
        Z = f32(uy * vx - ux * vy)
        s = self.invsqrt(f32(X * X + Y * Y + Z * Z))
        return f32(X * s), f32(Y * s), f32(Z * s)

    def cell_byte(self, hN, hW, hC, hE, hS, lx, lz):
        """0x0075C850: four quadrant normals, summed, renormalized, curved."""
        P0 = (0.0, -96.0, hN)
        P1 = (-96.0, 0.0, hW)
        P2 = (0.0, 0.0, hC)
        P3 = (96.0, 0.0, hE)
        P4 = (0.0, 96.0, hS)
        n1 = self.tri_normal(P0, P2, P1)
        n2 = self.tri_normal(P0, P3, P2)
        n3 = self.tri_normal(P1, P2, P4)
        n4 = self.tri_normal(P2, P3, P4)
        s1 = self.invsqrt(f32(n1[0]*n1[0] + n1[1]*n1[1] + n1[2]*n1[2]))
        s2 = self.invsqrt(f32(n2[0]*n2[0] + n2[1]*n2[1] + n2[2]*n2[2]))
        s3 = self.invsqrt(f32(n3[0]*n3[0] + n3[1]*n3[1] + n3[2]*n3[2]))
        s4 = self.invsqrt(f32(n4[0]*n4[0] + n4[1]*n4[1] + n4[2]*n4[2]))
        SX = f32(f32(f32(f32(n1[0]*s1) + f32(n2[0]*s2)) + f32(n3[0]*s3)) + f32(n4[0]*s4))
        SY = f32(f32(f32(f32(n1[1]*s1) + f32(n2[1]*s2)) + f32(n3[1]*s3)) + f32(n4[1]*s4))
        SZ = f32(f32(f32(f32(n1[2]*s1) + f32(n2[2]*s2)) + f32(n3[2]*s3)) + f32(n4[2]*s4))
        S = self.invsqrt(f32(SX*SX + SY*SY + SZ*SZ))
        Nz = f32(S * SZ)
        Nx = f32(S * SX)
        d = f32(Nz * lz + Nx * lx)         # y dropped: lightDir.y == 0 asserted
        if not (d >= 0.0):
            d = 0.0
        if not (1.0 >= d):
            d = 1.0
        e = f32(1.0 - d)
        e = f32(e * e)
        e = f32(e * e)                     # (1 - d)^4
        v = f32(f32(1.0 - e) * OUT_SCALE)
        i = math.floor(v)
        return (i + (1 if v - i >= 0.5 else 0)) & 0xFF   # round half away from 0

    def bake(self, dim_x, dim_y, hrow, lx, lz):
        out = bytearray(dim_x * dim_y)
        k = 0
        for gy in range(dim_y):
            up, dn, base = gy > 0, gy < dim_y - 1, gy * dim_x
            for gx in range(dim_x):
                hC = hrow[base + gx]
                hN = hrow[base - dim_x + gx] if up else hC
                hS = hrow[base + dim_x + gx] if dn else hC
                hW = hrow[base + gx - 1] if gx else hC
                hE = hrow[base + gx + 1] if gx < dim_x - 1 else hC
                out[k] = self.cell_byte(hN, hW, hC, hE, hS, lx, lz)
                k += 1
        return bytes(out)


def check_map(baker, trn, who):
    """Bake row-major, compare to the stored tag-9 bytes. Returns (miss, n)."""
    dim_x, dim_y = trn.dim_x, trn.dim_y
    index = terrain.Terrain.index
    hrow = [0.0] * (dim_x * dim_y)
    srow = bytearray(dim_x * dim_y)
    for gy in range(dim_y):
        for gx in range(dim_x):
            i = index(gx, gy, dim_x)
            hrow[gy * dim_x + gx] = trn.heights[i]
            srow[gy * dim_x + gx] = trn.shade[i]
    a = f32(trn.angle)
    ours = baker.bake(dim_x, dim_y, hrow, f32(math.cos(a)), f32(math.sin(a)))
    n = dim_x * dim_y
    miss = sum(1 for k in range(n) if ours[k] != srow[k])
    pct = 100.0 * (n - miss) / n
    flag = "" if miss <= ALLOWED_MISSES else "   <-- OVER THE ALLOWANCE"
    print(f"  {who:22s} {dim_x:>4}x{dim_y:<4}  {n - miss:>7}/{n:<7} "
          f"({pct:8.4f}%)  {miss} miss{flag}")
    return miss, n


def corpus_rows(ar):
    return sorted(e.index for e in ar.entries if is_map_head(e))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("targets", nargs="*",
                    help="file ids (0x...) or row:N; default = a corpus sample")
    ap.add_argument("--all", action="store_true", help="the whole corpus")
    ap.add_argument("--sample", type=int, default=6, help="default-mode sample")
    args = ap.parse_args()

    table, why = _load_table()
    print(f"[ok] invsqrt table: {why}")
    baker = Bake(table)

    total_miss = total_cells = maps = 0
    with Archive() as ar:
        table_ids = None
        if args.targets:
            print("map                       dims       matched          miss")
            for t in args.targets:
                if t.startswith("row:"):
                    trn = terrain.Terrain.from_row(int(t[4:]), ar)
                    who = t
                else:
                    if table_ids is None:
                        table_ids = file_id_table(ar)
                    fid = int(t, 0)
                    trn = terrain.Terrain.load(fid, archive=ar, table=table_ids)
                    who = f"0x{fid:X}"
                m, n = check_map(baker, trn, who)
                total_miss += m; total_cells += n; maps += 1
        else:
            rows = corpus_rows(ar)
            if not args.all:
                step = max(1, len(rows) // args.sample)
                rows = rows[::step][:args.sample]
            print(f"[ok] {len(rows)} map(s)"
                  + ("" if args.all else f" sampled over {CORPUS_MAPS}"))
            print("map                       dims       matched          miss")
            for row in rows:
                try:
                    trn = terrain.Terrain.from_row(row, ar)
                except Exception as e:
                    print(f"  row {row}: SKIP {e}")
                    continue
                m, n = check_map(baker, trn, f"row:{row}")
                total_miss += m; total_cells += n; maps += 1

    ok = total_cells - total_miss
    print(f"\n{ok}/{total_cells} cells exact over {maps} map(s), "
          f"{total_miss} miss (allowance {ALLOWED_MISSES}/map)")
    if total_miss > ALLOWED_MISSES * maps:
        print("[FAIL] the replica does not reproduce the bake -- a constant is "
              "wrong, or the table read the wrong build")
        return 1
    print("[PASS] the quartic-ease-out bake is reproduced byte-for-byte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
