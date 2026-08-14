"""Encode RGB pixels as DXT1 blocks, in either candidate payload layout.

atex.py builds the container; this builds what goes inside it. Keeping them
apart matters because they have very different evidence behind them: the
container is MEASURED from the client's own record walk, while the layout
question below is the last thing in the texture arc that is still guesswork.

DXT1, for reference, since this is the first place in the repo that needs it.
A block covers 4x4 pixels in 8 bytes:

    u16 color0, u16 color1      RGB565
    u32 indices                 2 bits per pixel, pixel (x,y) at bit 2*(y*4+x)

If color0 > color1 the palette is (c0, c1, 2/3 c0 + 1/3 c1, 1/3 c0 + 2/3 c1)
and every pixel is opaque. Otherwise the fourth entry is transparent black and
the two middles collapse to one. We always emit the opaque form: a skill icon
has no alpha, and the punch-through form would make an accidental colour tie
render as a hole.

THE OPEN QUESTION THIS FILE EXISTS TO SETTLE. A raw (code 0) ATEX level stores
block data, but in which order?

    PLANAR       every block's colour dword, then every block's index dword
    INTERLEAVED  complete 8-byte blocks, back to back

Upstream describes the planar form -- "ATEX stores undecoded block components in
separate planes rather than complete DXT blocks" -- but that is ONE witness, in a
lineage this project has already caught counting itself twice, and it is not a
claim the corpus can settle: both layouts are the same length, so no size check
refutes either. It fails silently too. A wrong layout renders noise, not an
error, which is the worst way for a thing to be wrong.

So it gets tested the only way it can be: encode the SAME image both ways, put
both on the bar in one frame, and see which one is a picture. That is a direct
read-off rather than an inference from garbage -- we are not asking "does this
look broken?", we are asking "which of these two is the image?", and only one
answer is possible.
"""

import struct

PLANAR = "planar"
INTERLEAVED = "interleaved"
LAYOUTS = (PLANAR, INTERLEAVED)


def to565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def from565(c):
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    return (r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2)


def _palette(c0, c1):
    """The four colours a block can use, in index order."""
    a = from565(c0)
    b = from565(c1)
    mid1 = tuple((2 * a[i] + b[i]) // 3 for i in range(3))
    mid2 = tuple((a[i] + 2 * b[i]) // 3 for i in range(3))
    return [a, b, mid1, mid2]


def encode_block(pixels):
    """One 4x4 block, as (color0, color1, indices).

    Endpoints come from the bounding box of the block's colours, which is the
    cheap classic choice: not optimal, entirely adequate for flat UI art, and
    short enough to read. Nothing here needs to compete with a real compressor.
    """
    lo = [min(p[i] for p in pixels) for i in range(3)]
    hi = [max(p[i] for p in pixels) for i in range(3)]
    c0 = to565(*hi)
    c1 = to565(*lo)
    if c0 < c1:
        c0, c1 = c1, c0
    if c0 == c1:
        # A flat block. Keep c0 > c1 so the opaque palette is selected; index 0
        # is c0 either way, so nudging c1 down by one bit costs nothing visible.
        c1 = c0 - 1 if c0 > 0 else 0
        if c0 == c1:
            c0 = c1 + 1
    pal = _palette(c0, c1)
    idx = 0
    for n, p in enumerate(pixels):
        best, bestd = 0, None
        for j, q in enumerate(pal):
            d = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2
            if bestd is None or d < bestd:
                best, bestd = j, d
        idx |= best << (2 * n)
    return c0, c1, idx


def encode(rgb, width, height):
    """Whole image to a list of blocks, left to right then top to bottom.

    rgb is a flat sequence of 3 bytes per pixel. Dimensions must be whole
    blocks; ATEX rounds up to 4 and this refuses rather than pad silently,
    because a silent pad would shift every block after it.
    """
    if width % 4 or height % 4:
        raise ValueError(f"{width}x{height} is not a whole number of 4x4 blocks")
    blocks = []
    for by in range(height // 4):
        for bx in range(width // 4):
            px = []
            for y in range(4):
                row = (by * 4 + y) * width
                for x in range(4):
                    o = (row + bx * 4 + x) * 3
                    px.append((rgb[o], rgb[o + 1], rgb[o + 2]))
            blocks.append(encode_block(px))
    return blocks


def decode_block(c0, c1, idx):
    """One 4x4 block to 16 RGBA tuples, row-major.

    **BOTH palette forms, which the encoder above does not exercise.** When
    `c0 > c1` the block is opaque and the palette has two interpolated
    middles; when `c0 <= c1` DXT1 switches to PUNCH-THROUGH -- one
    interpolated middle and index 3 meaning fully transparent black. Retail
    uses both, and a decoder that knows only the opaque form renders every
    cut-out texture (foliage, fences, grates) as solid black where it should
    be see-through, which is the failure mode that looks like a lighting bug
    rather than a decode bug.

    That asymmetry is why `test_dxt1.py` cannot check this against `encode`
    alone: `encode_block` always emits `c0 > c1` on purpose, so the
    punch-through arm needs a hand-built block or it is never entered.
    """
    a = from565(c0)
    b = from565(c1)
    if c0 > c1:
        pal = [a + (255,), b + (255,),
               tuple((2 * a[i] + b[i]) // 3 for i in range(3)) + (255,),
               tuple((a[i] + 2 * b[i]) // 3 for i in range(3)) + (255,)]
    else:
        pal = [a + (255,), b + (255,),
               tuple((a[i] + b[i]) // 2 for i in range(3)) + (255,),
               (0, 0, 0, 0)]
    return [pal[(idx >> (2 * n)) & 3] for n in range(16)]


def unpack(payload, blocks, layout):
    """Payload bytes back to `(c0, c1, idx)` triples. The inverse of `pack`.

    Refuses a payload whose length is not exactly `8 * blocks`, because both
    layouts are the same size and a truncated one would otherwise decode into
    a plausible image that is silently missing its tail.
    """
    if layout not in LAYOUTS:
        raise ValueError(f"layout {layout!r} is not one of {LAYOUTS}")
    want = 8 * blocks
    if len(payload) != want:
        raise ValueError(f"{len(payload)} bytes for {blocks} DXT1 blocks; "
                         f"expected {want}")
    out = []
    if layout == INTERLEAVED:
        for i in range(blocks):
            c0, c1, idx = struct.unpack_from("<HHI", payload, 8 * i)
            out.append((c0, c1, idx))
        return out
    # PLANAR: every block's colour dword first, then every block's indices.
    # OBSERVED to be retail's order (studies/texture/FINDINGS.md section 4 --
    # the two were put on the bar in one frame and only planar was a picture).
    half = 4 * blocks
    for i in range(blocks):
        c0, c1 = struct.unpack_from("<HH", payload, 4 * i)
        (idx,) = struct.unpack_from("<I", payload, half + 4 * i)
        out.append((c0, c1, idx))
    return out


def decode(payload, width, height, layout=PLANAR):
    """A whole DXT1 level to RGBA bytes, `width * height * 4`, top row first.

    Dimensions must be whole blocks, for the same reason `encode` insists:
    a silent pad shifts every block after it.
    """
    if width % 4 or height % 4:
        raise ValueError(f"{width}x{height} is not a whole number of 4x4 "
                         f"blocks")
    bw, bh = width // 4, height // 4
    blocks = unpack(payload, bw * bh, layout)
    out = bytearray(width * height * 4)
    for by in range(bh):
        for bx in range(bw):
            px = decode_block(*blocks[by * bw + bx])
            for y in range(4):
                row = (by * 4 + y) * width + bx * 4
                for x in range(4):
                    o = (row + x) * 4
                    out[o:o + 4] = bytes(px[y * 4 + x])
    return bytes(out)


def pack(blocks, layout):
    """Blocks to payload bytes, in one of the two candidate orders."""
    if layout == INTERLEAVED:
        out = bytearray()
        for c0, c1, idx in blocks:
            out += struct.pack("<HHI", c0, c1, idx)
        return bytes(out)
    if layout == PLANAR:
        colours = bytearray()
        indices = bytearray()
        for c0, c1, idx in blocks:
            colours += struct.pack("<HH", c0, c1)
            indices += struct.pack("<I", idx)
        return bytes(colours + indices)
    raise ValueError(f"layout must be one of {LAYOUTS}, got {layout!r}")


def mipmap(rgb, width, height):
    """Halve an image by box filter. Returns (rgb, w, h)."""
    w, h = max(width // 2, 1), max(height // 2, 1)
    out = bytearray(w * h * 3)
    for y in range(h):
        for x in range(w):
            acc = [0, 0, 0]
            for dy in range(2):
                for dx in range(2):
                    sx = min(x * 2 + dx, width - 1)
                    sy = min(y * 2 + dy, height - 1)
                    o = (sy * width + sx) * 3
                    for i in range(3):
                        acc[i] += rgb[o + i]
            o = (y * w + x) * 3
            for i in range(3):
                out[o + i] = acc[i] // 4
    return bytes(out), w, h


# --- test patterns -----------------------------------------------------------
#
# Drawn in code so no image file, and certainly no ArenaNet art, ever enters the
# repo. What matters for the layout experiment is VERTICAL ASYMMETRY: under the
# wrong layout the colour and index planes are read as interleaved blocks, so the
# top of the image is built from data that is really all colours and the bottom
# from data that is really all indices. A design whose halves differ makes that
# unmistakable rather than merely ugly.

def pattern_rune(width, height):
    """A bright chevron over a dark field, with a band across the top only.

    Recognisable enough to say "that is the picture" at skillbar size, and
    asymmetric top-to-bottom so a wrong layout cannot masquerade as a bad
    colour choice.
    """
    bg = (18, 24, 58)
    band = (220, 40, 190)
    ink = (255, 214, 96)
    edge = (90, 200, 255)
    out = bytearray(width * height * 3)

    def put(x, y, c):
        if 0 <= x < width and 0 <= y < height:
            o = (y * width + x) * 3
            out[o], out[o + 1], out[o + 2] = c

    for y in range(height):
        for x in range(width):
            put(x, y, bg)
    for y in range(height // 8):
        for x in range(width):
            put(x, y, band)
    # A chevron pointing up, thick enough to survive 4x4 quantisation.
    thick = max(width // 12, 3)
    apex_y = height // 4
    for step in range(height // 2):
        y = apex_y + step
        for t in range(thick):
            put(width // 2 - step - t, y, ink)
            put(width // 2 + step + t, y, ink)
    # A baseline, so the bottom edge is distinct from the top band.
    for y in range(height - height // 10, height):
        for x in range(width):
            put(x, y, edge)
    return bytes(out)


def pattern_calib(width, height):
    """A ruler for the skillbar, because the bar does not draw the whole image.

    OBSERVED 2026-08-06: an authored 128x128 texture rendered on the bar
    "cropped/off-center", so the icon quad samples a sub-rect of the texture
    rather than all of it. Nothing in our evidence base says which sub-rect, and
    guessing it would put authored art in the wrong place forever.

    So: four differently-coloured corners and a set of nested frames at powers of
    two. Whichever corners survive names the crop's position; whichever frames
    survive names its inset; and because all four corners differ, a mirror or a
    rotation cannot masquerade as a crop.

        corners      12x12 blocks  TL red, TR green, BL blue, BR yellow
        frames       2px bands at insets 0, 4, 8, 16, 32
        centre       white cross with a single-pixel gap at the exact middle
    """
    out = bytearray(width * height * 3)
    BG = (24, 24, 28)
    FRAMES = [(0, (255, 0, 0)), (4, (0, 255, 0)), (8, (0, 128, 255)),
              (16, (255, 255, 0)), (32, (255, 0, 255))]
    CORNERS = [((0, 0), (255, 40, 40)), ((1, 0), (40, 255, 40)),
               ((0, 1), (60, 120, 255)), ((1, 1), (255, 220, 40))]

    def put(x, y, c):
        if 0 <= x < width and 0 <= y < height:
            o = (y * width + x) * 3
            out[o], out[o + 1], out[o + 2] = c

    for y in range(height):
        for x in range(width):
            put(x, y, BG)
    for inset, colour in FRAMES:
        if inset * 2 + 2 >= min(width, height):
            continue
        for t in range(2):
            i = inset + t
            for x in range(i, width - i):
                put(x, i, colour)
                put(x, height - 1 - i, colour)
            for y in range(i, height - i):
                put(i, y, colour)
                put(width - 1 - i, y, colour)
    size = 12
    for (cx, cy), colour in CORNERS:
        x0 = 0 if cx == 0 else width - size
        y0 = 0 if cy == 0 else height - size
        for y in range(y0, y0 + size):
            for x in range(x0, x0 + size):
                put(x, y, colour)
    mx, my = width // 2, height // 2
    for d in range(-(width // 4), width // 4):
        if abs(d) > 1:
            put(mx + d, my, (255, 255, 255))
            put(mx, my + d, (255, 255, 255))
    return bytes(out)


def pattern_fine(width, height):
    """A contiguous colour ruler across insets 10..21, to pin the crop.

    The coarse target established that inset 16 survives and inset 8 does not,
    so the edge is somewhere in between. These bands are adjacent rather than
    spread out, which makes the reading a single question -- what is the
    outermost colour you can see -- instead of a list of yes/nos.

        10-11 red   12-13 green  14-15 blue
        16-17 yellow  18-19 cyan  20-21 white
    """
    out = bytearray(width * height * 3)
    BG = (24, 24, 28)
    BANDS = [(10, (255, 0, 0)), (12, (0, 255, 0)), (14, (0, 128, 255)),
             (16, (255, 255, 0)), (18, (0, 255, 255)), (20, (255, 255, 255))]

    def put(x, y, c):
        if 0 <= x < width and 0 <= y < height:
            o = (y * width + x) * 3
            out[o], out[o + 1], out[o + 2] = c

    for y in range(height):
        for x in range(width):
            put(x, y, BG)
    for inset, colour in BANDS:
        for t in range(2):
            i = inset + t
            for x in range(i, width - i):
                put(x, i, colour)
                put(x, height - 1 - i, colour)
            for y in range(i, height - i):
                put(i, y, colour)
                put(width - 1 - i, y, colour)
    mx, my = width // 2, height // 2
    for d in range(-(width // 5), width // 5):
        if abs(d) > 1:
            put(mx + d, my, (255, 255, 255))
            put(mx, my + d, (255, 255, 255))
    return bytes(out)


#: The frame chrome, as a FRACTION of the short side rather than a pixel
#: count. OBSERVED 2026-08-14 (studies/texture/FINDINGS.md section 9): the
#: client stretches the whole texture linearly onto a fixed screen quad -- two
#: landmarks in a 64x64 inset ruler agreed on 0.955 and 0.958 px per texel --
#: so the chrome covers a constant fraction of the TEXTURE, not a constant
#: number of texels. The original 16 px was written for 128x128, which is
#: 12.5%; at 64x64 the same margin is 8 px, and subtracting 16 there threw
#: away a quarter of the picture. Keeping the fraction reproduces the 128x128
#: safe radius of 48.0 exactly.
ICON_MARGIN = 0.125
_SAFE_FRAC = 0.5 - ICON_MARGIN                                    # 0.375

#: The sun disc, as a fraction of the safe radius. Named because MIN_ICON is
#: derived from it -- it is the picture's smallest feature.
ICON_SUN_FRAC = 0.46

#: Smallest short side pattern_icon will draw. DERIVED, not chosen: the sun
#: disc spans 2 * ICON_SUN_FRAC * _SAFE_FRAC == 0.345 of the short side, and
#: below one DXT1 4x4 block across it is not a picture. 4 / 0.345 -> 11.6, so
#: 12. Anything smaller is refused rather than drawn as noise; the old rule
#: raised ZeroDivisionError at exactly 32x32 and produced garbage below ~40.
MIN_ICON = 12


def pattern_icon(width, height):
    """An actual skill icon, drawn entirely inside the safe area.

    The deliverable this whole arc was for: not a test pattern, a picture that
    could plausibly sit on a skillbar. Everything is kept inside a border of
    ICON_MARGIN of the short side because OBSERVED 2026-08-06 the bar does not
    draw the outer edge of the texture -- see pattern_calib -- and OBSERVED
    2026-08-14 that what it eats is a fraction and not a texel count.

    A rising sun over a horizon, in warm colours against a deep sky, with a
    vignette so the crop boundary is not a hard line if the safe area is
    slightly smaller than we think.
    """
    if min(width, height) < MIN_ICON:
        raise ValueError(f"{width}x{height} is too small to draw an icon; "
                         f"the short side must be at least {MIN_ICON}")
    out = bytearray(width * height * 3)
    cx, cy = width / 2.0, height / 2.0
    safe = min(width, height) * _SAFE_FRAC
    horizon = cy + safe * 0.35
    sun_r = safe * ICON_SUN_FRAC

    def put(x, y, c):
        o = (y * width + x) * 3
        out[o], out[o + 1], out[o + 2] = (max(0, min(255, int(v))) for v in c)

    for y in range(height):
        for x in range(width):
            dx, dy = x - cx, y - cy
            d = (dx * dx + dy * dy) ** 0.5
            if d > safe:
                put(x, y, (10, 8, 20))
                continue
            t = d / safe
            if y < horizon:
                sd = ((x - cx) ** 2 + (y - (horizon - sun_r * 0.35)) ** 2) ** 0.5
                if sd < sun_r:
                    k = 1.0 - sd / sun_r
                    c = (255, 190 + 60 * k, 70 + 120 * k)
                else:
                    c = (40 + 150 * (1 - t), 30 + 70 * (1 - t), 80 + 60 * (1 - t))
            else:
                k = (y - horizon) / max(safe, 1)
                c = (90 - 50 * k, 40 - 20 * k, 70 - 40 * k)
                if int(x * 0.7 + y * 1.3) % 11 < 2:
                    c = (c[0] + 40, c[1] + 25, c[2] + 30)
            v = 1.0 - 0.55 * max(0.0, (t - 0.72) / 0.28) ** 2
            put(x, y, (c[0] * v, c[1] * v, c[2] * v))
    return bytes(out)


PATTERNS = {"rune": pattern_rune, "calib": pattern_calib,
            "fine": pattern_fine, "icon": pattern_icon}
