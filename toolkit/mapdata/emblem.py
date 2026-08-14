r"""The Stormcaller profession emblem: two 32x32 BGRA cells, drawn from arithmetic.

The profession glyph sheet (Gw.dat file id 152638, MFT row 12032) is a 256x128
32bpp DDS of 8x4 cells at 32x32. Each profession owns an adjacent LIT/DIM pair,
and profession 8 -- Ritualist, our reskin host -- is frames 14/15, i.e. cells
(col 6, row 1) and (col 7, row 1). See studies/profession/RESKIN.md section 22.

WHAT IS MEASURED AND WHAT IS OURS, because this writes into a sheet whose other
ten cells are ArenaNet's.

  MEASURED from the sheet, and these are geometry and ratios -- facts, which the
  provenance gate permits:
    * the cell is 32x32 BGRA, dword order B,G,R,A
    * the alpha channel is a filled disc: of 1,024 texels, 725 are fully opaque,
      131 partial and 168 clear. That is a radius near 15.2 with a soft edge.
    * the dim frame is a darkened copy of the lit one, luma ratio 0.687-0.788
      across all eleven pairs (11 of 11).

  OURS, drawn here and copied from nothing:
    * every pixel. The disc, its rim light, the recess shading and the bolt are
      arithmetic. NO byte of ArenaNet's art is read, sampled or averaged --
      not even the socket colour, which would have been the easy shortcut and
      is exactly the kind of borrowing the gate is about.

The emblem is a forked bolt over a swept arc -- storm, for a profession whose
attributes are Tempest, Galecraft, Windward, Thunderhead and Storm Calling.
At 32x32 with ~15 usable radius, only a bold silhouette survives, so it is one
shape with one accent and nothing finer than 2 texels.
"""

import math

CELL = 32
R_OPAQUE = 15.2          # MEASURED: 725 fully opaque texels of 1,024
R_EDGE = 16.0            # where alpha reaches 0
DIM = 0.72               # MEASURED band 0.687-0.788; the middle of it


def _clamp(v, a=0.0, b=1.0):
    return a if v < a else (b if v > b else v)


def _mix(c, d, t):
    return tuple(c[i] + (d[i] - c[i]) * t for i in range(3))


def _disc_alpha(x, y):
    """Filled disc, soft edge. Matches the sheet's own alpha profile."""
    d = math.hypot(x, y)
    if d <= R_OPAQUE:
        return 1.0
    if d >= R_EDGE:
        return 0.0
    return 1.0 - (d - R_OPAQUE) / (R_EDGE - R_OPAQUE)


# A recessed socket: dark at the top-left where the rim casts in, warmer and
# lighter at the bottom-right. Our browns, not theirs.
SOCKET_LO = (0.24, 0.19, 0.13)
SOCKET_HI = (0.47, 0.39, 0.28)
RIM_LIGHT = (0.82, 0.79, 0.72)
RIM_DARK = (0.16, 0.13, 0.10)

# Stormcaller: the violet of the `tempest` palette in glyphs.py, with a hot core.
BOLT_CORE = (1.00, 0.98, 1.00)
BOLT_MID = (0.78, 0.66, 1.00)
BOLT_EDGE = (0.42, 0.30, 0.78)
ARC_COL = (0.55, 0.78, 1.00)


def _bolt_distance(x, y):
    """Distance to a forked bolt polyline, in texels."""
    pts = [(-3.0, -9.2), (1.3, -2.6), (-1.7, -0.8), (3.4, 8.8)]
    best = 1e9
    for i in range(len(pts) - 1):
        ax, ay = pts[i]
        bx, by = pts[i + 1]
        dx, dy = bx - ax, by - ay
        den = dx * dx + dy * dy
        t = _clamp(((x - ax) * dx + (y - ay) * dy) / den) if den else 0.0
        best = min(best, math.hypot(x - (ax + t * dx), y - (ay + t * dy)))
    return best


def _arc_distance(x, y):
    """Distance to a swept wind arc behind the bolt."""
    d = math.hypot(x, y)
    ring = abs(d - 9.6)
    ang = math.degrees(math.atan2(y, x))
    if not (-170.0 <= ang <= -25.0):
        return 1e9
    return ring


def cell(lit=True):
    """One 32x32 cell as BGRA bytes, len == 4096."""
    out = bytearray(CELL * CELL * 4)
    c = (CELL - 1) / 2.0
    for py in range(CELL):
        for px in range(CELL):
            x, y = px - c, py - c
            a = _disc_alpha(x, y)
            if a <= 0.0:
                continue
            d = math.hypot(x, y)

            # socket: lit from the lower right, so the upper left reads recessed
            g = _clamp((x + y) / 30.0 + 0.5)
            col = _mix(SOCKET_LO, SOCKET_HI, g)
            # inner shadow just inside the rim
            col = _mix(col, RIM_DARK, _clamp((d - 9.0) / 7.0) ** 2 * 0.55)
            # the rim itself, brightest at the top-left
            rim = _clamp((d - 12.9) / 2.3)
            if rim > 0.0:
                lightness = _clamp(0.5 - (x + y) / 26.0)
                col = _mix(col, _mix(RIM_DARK, RIM_LIGHT, lightness), rim * 0.92)

            # wind arc, behind
            ad = _arc_distance(x, y)
            if ad < 2.4:
                col = _mix(col, ARC_COL, (1.0 - ad / 2.4) ** 2 * 0.55)

            # the bolt
            bd = _bolt_distance(x, y)
            if bd < 3.6:
                col = _mix(col, BOLT_EDGE, _clamp((3.6 - bd) / 2.3) * 0.85)
            if bd < 2.0:
                col = _mix(col, BOLT_MID, _clamp((2.0 - bd) / 1.2))
            if bd < 1.05:
                col = _mix(col, BOLT_CORE, _clamp((1.05 - bd) / 0.8))

            if not lit:
                col = tuple(v * DIM for v in col)

            o = (py * CELL + px) * 4
            out[o + 0] = int(_clamp(col[2]) * 255 + 0.5)   # B
            out[o + 1] = int(_clamp(col[1]) * 255 + 0.5)   # G
            out[o + 2] = int(_clamp(col[0]) * 255 + 0.5)   # R
            out[o + 3] = int(_clamp(a) * 255 + 0.5)        # A
    return bytes(out)


def pair():
    return cell(True), cell(False)


if __name__ == "__main__":
    import os
    import sys
    sys.path.insert(0, r"C:\gd\Rurik\.claude\worktrees\sweet-euler-697883\toolkit")
    from mapdata import png
    lit, dim = pair()
    al = [lit[k + 3] for k in range(0, len(lit), 4)]
    print("alpha  opaque %d  partial %d  clear %d   (sheet: 725 / 131 / 168)"
          % (sum(1 for v in al if v == 255),
             sum(1 for v in al if 0 < v < 255),
             sum(1 for v in al if v == 0)))

    def luma(c):
        s = 0.0
        for k in range(0, len(c), 4):
            b, g, r, a = c[k:k + 4]
            s += (0.299 * r + 0.587 * g + 0.114 * b) * (a / 255.0)
        return s / (CELL * CELL)
    print("luma lit %.2f dim %.2f  ratio %.3f   (sheet band 0.687-0.788)"
          % (luma(lit), luma(dim), luma(dim) / luma(lit)))

    Z = 10
    W, H = CELL * Z * 2, CELL * Z
    img = bytearray(W * H * 4)
    for n, c in enumerate((lit, dim)):
        for y in range(CELL * Z):
            for x in range(CELL * Z):
                s = ((y // Z) * CELL + (x // Z)) * 4
                b, g, r, a = c[s:s + 4]
                t = a / 255.0
                d = (y * W + n * CELL * Z + x) * 4
                img[d + 0] = int(r * t + 0x60 * (1 - t))
                img[d + 1] = int(g * t + 0x60 * (1 - t))
                img[d + 2] = int(b * t + 0x60 * (1 - t))
                img[d + 3] = 255
    png.write(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "emblem.png"), bytes(img), W, H)
    print("wrote emblem.png")
