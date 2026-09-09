r"""callouts.py: the floating-number scanner, with a positive control it cannot fake.

What this proves: (1) the stdlib PNG reader round-trips every filter type on
a fixture it wrote itself, and refuses what it cannot read by name; (2) the
`heal` colour class counts a block of the MEASURED glyph colour and counts
nothing on a frame of saturated green -- the mistake the 2026-08-20 scan
made, reproduced as a check that can go red; (3) on the 2026-08-20 run in the
vault, the three frames ~1.2 s after a heal send carry the number in the band
and the frame before each does not (`studies/skills/FINDINGS.md` 42).

FLOOR: 12, MEASURED from a green run 2026-09-09 (9 synthetic + 3 vault).
"""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks       # noqa: E402
import callouts     # noqa: E402
import vaultpath    # noqa: E402

LEDGER = checks.Ledger("floating callouts", floor=12)
check = checks.adopt(LEDGER)

GLYPH = (112, 208, 224)        # measured off w007.png, inside the class
GREEN = (40, 220, 40)          # the colour the old scan looked for
GRASS = (110, 120, 60)

print("== 1. the PNG reader, on fixtures it wrote ==")
tmp = tempfile.mkdtemp(prefix="callouts-")
W, H = 40, 30
px = [GRASS] * (W * H)
for y in range(10, 20):
    for x in range(5, 15):
        px[y * W + x] = GLYPH
for y in range(10, 20):
    for x in range(25, 35):
        px[y * W + x] = GREEN
pos = os.path.join(tmp, "pos.png")
callouts.write_png(pos, W, H, px)
w, h, bpp, rows = callouts.read_png(pos)
check((w, h, bpp) == (W, H, 3), "read_png: header round-trips", str((w, h, bpp)))
check(rows[12][7 * 3:7 * 3 + 3] == bytes(GLYPH), "read_png: a glyph pixel reads back exactly")
check(rows[12][30 * 3:30 * 3 + 3] == bytes(GREEN), "read_png: a green pixel reads back exactly")

# every filter type, by hand-encoding one row each -- the decoder must invert all five
import struct, zlib  # noqa: E402


def encode_filtered(path, w, h, pixels, filters):
    def sub(cur, prev, bpp):
        return bytes((cur[i] - (cur[i - bpp] if i >= bpp else 0)) & 255 for i in range(len(cur)))

    def up(cur, prev, bpp):
        return bytes((cur[i] - prev[i]) & 255 for i in range(len(cur)))

    def avg(cur, prev, bpp):
        return bytes((cur[i] - (((cur[i - bpp] if i >= bpp else 0) + prev[i]) >> 1)) & 255
                     for i in range(len(cur)))

    def paeth(cur, prev, bpp):
        out = bytearray()
        for i in range(len(cur)):
            a = cur[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            p = a + b - c
            pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
            pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
            out.append((cur[i] - pr) & 255)
        return bytes(out)
    enc = {0: lambda c, p, b: bytes(c), 1: sub, 2: up, 3: avg, 4: paeth}
    prev = bytes(w * 3)
    raw = b""
    for y in range(h):
        cur = bytes(c for pxl in pixels[y * w:(y + 1) * w] for c in pxl)
        f = filters[y % len(filters)]
        raw += bytes([f]) + enc[f](cur, prev, 3)
        prev = cur

    def chunk(typ, body):
        return struct.pack(">I", len(body)) + typ + body + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
        fh.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        fh.write(chunk(b"IDAT", zlib.compress(raw)))
        fh.write(chunk(b"IEND", b""))


filt = os.path.join(tmp, "filtered.png")
encode_filtered(filt, W, H, px, [0, 1, 2, 3, 4])
_w, _h, _b, rows2 = callouts.read_png(filt)
check(rows2 == rows, "read_png: all five filter types decode to the same pixels as filter 0")

bad = os.path.join(tmp, "bad.png")
with open(bad, "wb") as fh:
    fh.write(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
             + struct.pack(">IIBBBBB", 4, 4, 16, 2, 0, 0, 0) + b"\0\0\0\0")
try:
    callouts.read_png(bad)
    check(False, "read_png: a 16-bit PNG is refused")
except callouts.PngError as exc:
    check("depth 16" in str(exc), "read_png: a 16-bit PNG is refused by name", str(exc))

print("== 2. the colour classes, positive and negative control ==")
n, box = callouts.count(pos, "heal")
check(n == 100, "heal class: the 10x10 glyph-colour block counts 100 and the green block 0", str(n))
check(box == (5, 10, 14, 19), "heal class: the bounding box is the glyph block", str(box))
n_band, _ = callouts.count(pos, "heal", band=(25, 0, 40, 30))
check(n_band == 0, "heal class: the band restricts the count (green side of the frame reads 0)")
g, _ = callouts.count(pos, "green")
check(g == 100, "green class: sees the green block and NOT the glyph -- the 2026-08-20 blind spot", str(g))

print("== 3. the 2026-08-20 run: the number is there, one frame after each heal ==")
try:
    run = vaultpath.require_dir("captures", "harness", "20260820T190917",
                                why="the frames FINDINGS 42 scored")
    for hit, ctrl in (("w007.png", "w006.png"), ("w014.png", "w013.png"), ("w022.png", "w020.png")):
        a, _ = callouts.count(os.path.join(run, hit), "heal", callouts.DEFAULT_BAND)
        b, _ = callouts.count(os.path.join(run, ctrl), "heal", callouts.DEFAULT_BAND)
        check(a > 0 and b == 0, f"{hit} carries the callout in the band and {ctrl} does not",
              f"{a} vs {b}")
except (Exception, SystemExit) as exc:  # noqa: BLE001 -- a bare machine has no vault
    LEDGER.skip("section 3 (vault frames)", f"{type(exc).__name__}: {exc}")

sys.exit(LEDGER.verdict())
