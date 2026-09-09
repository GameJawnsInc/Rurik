r"""Score a harness run's frames for the client's floating combat callouts.

    python toolkit/harness/callouts.py 20260820T190917
    python toolkit/harness/callouts.py 20260820T190917 --colour heal --band 900,445,1000,485

WHY THIS EXISTS, and it is a specific failure. On 2026-08-20 a "green-text
scan" over twenty frames of the Healing Signet probe counted 0-8 saturated
green pixels and `studies/skills/FINDINGS.md` 19 recorded "the client draws
no number for a heal". The client had drawn `+46` over the player in three
frames of that run. The number is BLUE -- WIKI (GWW, "Heal", rev. read
2026-09-09): "The healing player and healed player see blue numbers showing
the amount healed" -- and MEASURED off those frames its glyphs sit around
RGB (96-144, 208-224, 224-240), a light cyan a green detector cannot see and
a saturated-blue detector (`B > 170, G < 150`) cannot see either. A scan for
the wrong colour is a null with no power, and it stood for twenty days.

So the colours here are MEASURED, not named: `heal` is the glyph colour read
off `w007.png` of that run; the control frame one second earlier (`w006.png`)
has ZERO pixels in that class inside the number band. Add a colour by
measuring it the same way and saying which frame it came from.

TWO REGIONS, and the difference is the instrument. `--band` restricts the
count to a box (default: where the number floated on those frames); the
Hatcher's cast circle and the player's own sparkle share the colour class,
so a whole-frame count fluctuates 0-326 on frames with no number at all,
while the band reads 0 on every no-number frame and 101/101/24 on the three
heal frames. The band is a screen position, so a run where the camera or the
body moved needs its own; `--bbox` prints the whole-frame bounding box so the
band can be re-aimed instead of guessed.

Standard library only: an 8-bit RGB/RGBA non-interlaced PNG reader (what
`session.py` writes); anything else is refused by name rather than scored.
"""
import argparse
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import vaultpath    # noqa: E402

# (name, predicate) -- MEASURED classes. Keep the measurement note beside each.
COLOURS = {
    # heal callout, `+46` glyphs on 20260820T190917/w007.png: light cyan.
    "heal": lambda r, g, b: b > 190 and g > 180 and r < 160 and b >= g and b - r > 70,
    # the 2026-08-20 scan's class, kept so the two can be scored side by side.
    "green": lambda r, g, b: g > 170 and r < 110 and b < 110 and g - max(r, b) > 60,
}
DEFAULT_BAND = (900, 445, 1000, 485)     # where +46 floated on that run's frames


class PngError(Exception):
    pass


def read_png(path):
    """(width, height, bytes_per_pixel, [row bytes]) for an 8-bit RGB/RGBA PNG."""
    data = open(path, "rb").read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise PngError(f"{path}: not a PNG")
    pos, idat = 8, []
    w = h = depth = ctype = interlace = None
    while pos + 8 <= len(data):
        ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, depth, ctype, _c, _f, interlace = struct.unpack(">IIBBBBB", body)
        elif typ == b"IDAT":
            idat.append(body)
        elif typ == b"IEND":
            break
        pos += 12 + ln
    if depth != 8 or ctype not in (2, 6) or interlace != 0:
        raise PngError(f"{path}: unsupported PNG (depth {depth}, colour type {ctype}, "
                       f"interlace {interlace}) -- this reader does 8-bit RGB/RGBA only")
    bpp = 3 if ctype == 2 else 4
    raw = zlib.decompress(b"".join(idat))
    stride = w * bpp
    if len(raw) != h * (stride + 1):
        raise PngError(f"{path}: {len(raw)} bytes of scanline data, expected {h * (stride + 1)}")
    prev = bytearray(stride)
    rows, off = [], 0
    for _y in range(h):
        f = raw[off]; off += 1
        cur = bytearray(raw[off:off + stride]); off += stride
        if f == 1:
            for i in range(bpp, stride):
                cur[i] = (cur[i] + cur[i - bpp]) & 255
        elif f == 2:
            for i in range(stride):
                cur[i] = (cur[i] + prev[i]) & 255
        elif f == 3:
            for i in range(stride):
                a = cur[i - bpp] if i >= bpp else 0
                cur[i] = (cur[i] + ((a + prev[i]) >> 1)) & 255
        elif f == 4:
            for i in range(stride):
                a = cur[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                cur[i] = (cur[i] + (a if (pa <= pb and pa <= pc) else (b if pb <= pc else c))) & 255
        elif f != 0:
            raise PngError(f"{path}: filter type {f}")
        rows.append(bytes(cur))
        prev = cur
    return w, h, bpp, rows


def write_png(path, w, h, pixels):
    """Write an 8-bit RGB PNG from [(r, g, b)] row-major. For fixtures."""
    raw = b"".join(b"\x00" + bytes(c for px in pixels[y * w:(y + 1) * w] for c in px)
                   for y in range(h))

    def chunk(typ, body):
        return (struct.pack(">I", len(body)) + typ + body
                + struct.pack(">I", zlib.crc32(typ + body) & 0xFFFFFFFF))
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
        fh.write(chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)))
        fh.write(chunk(b"IDAT", zlib.compress(raw)))
        fh.write(chunk(b"IEND", b""))


def count(path, colour="heal", band=None):
    """(pixels in class inside band, whole-frame bounding box of the class or None)."""
    pred = COLOURS[colour]
    w, h, bpp, rows = read_png(path)
    x0, y0, x1, y1 = band or (0, 0, w, h)
    n = 0
    xs, ys = [], []
    for y in range(h):
        r = rows[y]
        in_band_y = y0 <= y < y1
        for x in range(w):
            o = x * bpp
            if pred(r[o], r[o + 1], r[o + 2]):
                xs.append(x); ys.append(y)
                if in_band_y and x0 <= x < x1:
                    n += 1
    box = (min(xs), min(ys), max(xs), max(ys)) if xs else None
    return n, box


def frames(run_dir):
    return sorted(f for f in os.listdir(run_dir)
                  if f.endswith(".png") and f.startswith(("w0", "walk", "hold")))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("run", help="harness run stamp under vault/captures/harness/, or a directory")
    ap.add_argument("--colour", default="heal", choices=sorted(COLOURS))
    ap.add_argument("--band", default=",".join(map(str, DEFAULT_BAND)),
                    help="x0,y0,x1,y1 counted region (default: the 2026-08-20 number band)")
    ap.add_argument("--bbox", action="store_true", help="also print the whole-frame bounding box")
    args = ap.parse_args()
    run_dir = args.run if os.path.isdir(args.run) else \
        vaultpath.require_dir("captures", "harness", args.run, why="callouts scores a harness run")
    band = tuple(int(x) for x in args.band.split(","))
    print(f"{run_dir}  colour={args.colour}  band={band}")
    print(f"{'frame':22s} {'in band':>8s}" + ("  bbox" if args.bbox else ""))
    for f in frames(run_dir):
        n, box = count(os.path.join(run_dir, f), args.colour, band)
        print(f"{f:22s} {n:8d}" + (f"  {box}" if args.bbox else ""))


if __name__ == "__main__":
    main()
