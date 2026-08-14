"""Procedural skill icons: 132 distinct 64x64 glyphs, drawn from arithmetic.

Rung M7. A custom profession needs an icon per skill, and profession 8 has 188
skills behind 132 distinct `+0x90` icon rows -- so this module's whole job is to
produce 132 pictures a player can tell apart on a skillbar.

WHY THIS SHAPE, because it is a synthesis and the losers are the argument. Four
vocabularies were built independently and measured by one implementation
(2026-08-14): heraldic emblems, stroke sigils, painterly storm scenes, and n-fold
mandalas. Each hit the weakness it had predicted in advance. Sigil was the most
legible per icon and had the WORST confusability (greyscale minimum 3.54) because
two palettes meant half the set was one rune recoloured; heraldic had the best
confusability (24.07) and read as flat placeholder art; storm looked like a real
skill icon and blurred (greyscale 7.70, a third of its ink outside the safe area);
mandala was the most distinct in greyscale and was 132 flowers. The failures are
complementary, so:

  * SUBJECT   22 stroke runes whose SILHOUETTES differ, as a signed distance
              field so the edges stay clean at 64x64.
  * GROUND    a smooth two-colour field with a directional sweep and a mottle.
              Smooth is what DXT1 keeps.
  * SCHEME    motif = i % 22, palette = i // 22 -- every pair unique, 132 exactly.

THE THREE DISCRIMINATORS, and each exists because the set failed without it:

  polarity = (motif + palette) % 2   light rune on a deep ground, or dark rune on
                                     a lit one. Alternates BY CONSTRUCTION across
                                     a motif's six.
  accent   = (palette // 2) % 3      0, 1, 2 across the three same-polarity
                                     siblings of any motif, so they differ in
                                     SHAPE and not only in colour.
  ground   = (3*motif + 5*palette) % 6

The first version chose the ground as (3*motif + palette) % 11 and split polarity
by index range. Those are six CONSECUTIVE indices for a fixed motif, so all six
landed in one polarity block and polarity never fired for the same-motif pairs it
existed to separate. Measured minimum confusability 10.65, WORSE THAN ALL FOUR
PARENTS. `test_glyphs.py` asserts each of the three invariants directly, because
all three are index arithmetic that fails silently and looks fine.

CONSTRAINTS, all MEASURED on the retail client (studies/texture/FINDINGS.md 9):
a 64x64 DXT1 single-level ATEX is 2,068 B against the 2,560 B reservation every
one of the 132 rows already has; the client stretches the WHOLE texture onto a
fixed screen quad ~57-61 px wide, so a texel is about a screen pixel and detail
under ~2 texels does not read; and the bar's chrome covers a constant 12.5% of
the edge, so content lives inside the central 48x48. Geometry is normalised to
[-1, +1] -- nothing here is a pixel count, and dim=128 renders the same picture.

PROVENANCE: no ArenaNet asset, byte or pixel is read, copied or embedded. Every
image is arithmetic. Standard library only.
"""

import math
import random

COUNT = 132
MOTIFS = 22
ACCENTS = 3
NPALETTE = 6
NGROUND = 6

assert COUNT == MOTIFS * NPALETTE

# TWO CONSTANTS, NOT ONE, and they were one for a while. `_seg_field` came from
# the sigil generator where `_GLOW` was its stroke MARGIN (0.13); `icon` came
# from the synthesis where `_GLOW` was the glow RADIUS (0.15). They lived in
# separate modules and consolidating collapsed them onto one name, which changed
# every icon by a mean of 0.03/255 and a max of 16 -- invisible on screen, caught
# only by comparing bytes against the pre-consolidation renderer.
_FIELD_MARGIN = 0.13   # how far past a stroke `_seg_field` bothers to compute
_GLOW = 0.15           # outer glow radius, normalised units
_LIMIT = 0.75         # safe area as a fraction; chrome eats 12.5% a side
_HALO = 0.26        # dark contact halo, normalised units
_SHADOW = (0.028, -0.028)
_LAT = 16


# --------------------------------------------------------------------------
# palette record

def _P(name, sky_hi, sky_lo, glow, land, dark, lite, core, accent):
    return {"name": name, "sky_hi": sky_hi, "sky_lo": sky_lo, "glow": glow,
            "land": land, "dark": dark, "lite": lite, "core": core,
            "accent": accent}

# --------------------------------------------------------------------------
# value noise, for the ground mottle

def _lattice(rnd):
    return [rnd.random() for _ in range(_LAT * _LAT)]

def _latsample(lat, fx, fy):
    x0 = math.floor(fx)
    y0 = math.floor(fy)
    tx = fx - x0
    ty = fy - y0
    tx = tx * tx * (3.0 - 2.0 * tx)
    ty = ty * ty * (3.0 - 2.0 * ty)
    r0 = (int(y0) % _LAT) * _LAT
    r1 = (int(y0 + 1) % _LAT) * _LAT
    a0 = int(x0) % _LAT
    a1 = int(x0 + 1) % _LAT
    v0 = lat[r0 + a0] + (lat[r0 + a1] - lat[r0 + a0]) * tx
    v1 = lat[r1 + a0] + (lat[r1 + a1] - lat[r1 + a0]) * tx
    return v0 + (v1 - v0) * ty

class Noise:
    """A smooth field over [-1, 1]^2, precomputed on a GxG buffer."""

    G = 44

    def __init__(self, rnd, base=1.7):
        lat = _lattice(rnd)
        ox, oy = rnd.random() * 7.0, rnd.random() * 7.0
        G = self.G
        buf = []
        for j in range(G):
            y = -1.0 + 2.0 * j / (G - 1.0)
            for i in range(G):
                x = -1.0 + 2.0 * i / (G - 1.0)
                v = (0.56 * _latsample(lat, ox + x * base, oy + y * base)
                     + 0.28 * _latsample(lat, ox * 2 + x * base * 2.1,
                                         oy * 2 + y * base * 2.1)
                     + 0.16 * _latsample(lat, ox * 3 + x * base * 4.3,
                                         oy * 3 + y * base * 4.3))
                buf.append(v - 0.5)
        self.buf = buf

    def __call__(self, x, y):
        G = self.G
        fx = (x + 1.0) * 0.5 * (G - 1)
        fy = (y + 1.0) * 0.5 * (G - 1)
        if fx < 0.0:
            fx = 0.0
        elif fx > G - 1.001:
            fx = G - 1.001
        if fy < 0.0:
            fy = 0.0
        elif fy > G - 1.001:
            fy = G - 1.001
        i = int(fx)
        j = int(fy)
        tx = fx - i
        ty = fy - j
        b = self.buf
        r0 = j * G
        r1 = r0 + G
        v0 = b[r0 + i] + (b[r0 + i + 1] - b[r0 + i]) * tx
        v1 = b[r1 + i] + (b[r1 + i + 1] - b[r1 + i]) * tx
        return v0 + (v1 - v0) * ty

# --------------------------------------------------------------------------
# stroke primitives -- every motif is built from these

def _arc(cx, cy, r, a0, a1, n=20):
    """Sampled circular arc. Angles in degrees, screen convention (y down)."""
    return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             cy + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]

def _spiral(cx, cy, r0, r1, a0, a1, n=40):
    """Archimedean spiral arm: radius and angle both sweep linearly."""
    out = []
    for i in range(n + 1):
        t = i / n
        r = r0 + (r1 - r0) * t
        a = math.radians(a0 + (a1 - a0) * t)
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out

def _poly(*pts):
    return list(pts)

def _ring(cx, cy, r, n=48):
    return _arc(cx, cy, r, 0.0, 360.0, n)

def _dot(x, y):
    """A degenerate stroke. Rendered as a disc of the stroke's half-width."""
    return [(x, y)]

# --------------------------------------------------------------------------
# the 22 motifs. Silhouettes differ; a rotation of one shape does not count.

def _m_bolt():
    return [(_poly((-0.22, -0.55), (0.16, -0.08), (-0.16, 0.02), (0.24, 0.55)),
             0.075)]

def _m_spiral():
    return [(_spiral(0.0, 0.0, 0.08, 0.57, 0.0, 540.0, 44), 0.065)]

def _m_chevrons():
    out = []
    for y in (-0.30, 0.02, 0.34):
        out.append((_poly((-0.48, y - 0.16), (0.0, y + 0.14), (0.48, y - 0.16)),
                    0.058))
    return out

def _m_wheel():
    out = [(_ring(0.0, 0.0, 0.29, 32), 0.055)]
    for k in range(8):
        a = math.radians(22.5 + 45.0 * k)
        out.append((_poly((0.29 * math.cos(a), 0.29 * math.sin(a)),
                          (0.58 * math.cos(a), 0.58 * math.sin(a))), 0.050))
    return out

def _m_crescent():
    return [(_arc(0.0, 0.0, 0.45, 35.0, 325.0, 28), 0.110)]

def _m_trident():
    out = [(_poly((0.0, 0.55), (0.0, -0.12)), 0.060),
           (_poly((-0.40, -0.12), (0.40, -0.12)), 0.055)]
    for x in (-0.40, 0.0, 0.40):
        out.append((_poly((x, -0.12), (x, -0.52)), 0.055))
    return out

def _m_vortex():
    return [(_spiral(0.0, 0.0, 0.15, 0.57, 120.0 * k, 120.0 * k + 115.0, 18),
             0.062) for k in range(3)]

def _m_cross():
    return [(_poly((-0.55, 0.0), (0.55, 0.0)), 0.085),
            (_poly((0.0, -0.55), (0.0, 0.55)), 0.085)]

def _m_wave():
    pts = []
    for i in range(41):
        t = -1.0 + 2.0 * i / 40
        pts.append((0.56 * t, 0.30 * math.sin(2.0 * math.pi * t)))
    return [(pts, 0.075)]

def _m_triangle():
    v = [(0.58 * math.cos(math.radians(a)), 0.58 * math.sin(math.radians(a)))
         for a in (-90.0, 30.0, 150.0)]
    return [(v + [v[0]], 0.070)]

def _m_drop():
    body = _arc(0.0, 0.16, 0.34, -30.0, 210.0, 26)   # the round bottom lobe
    return [(body, 0.065),
            (_poly(body[0], (0.0, -0.56)), 0.065),
            (_poly(body[-1], (0.0, -0.56)), 0.065)]

def _m_starburst():
    out = []
    for k in range(8):
        a = math.radians(45.0 * k)
        r = 0.58 if k % 2 == 0 else 0.36
        out.append((_poly((0.08 * math.cos(a), 0.08 * math.sin(a)),
                          (r * math.cos(a), r * math.sin(a))), 0.055))
    return out

def _m_rhombus():
    v = [(0.0, -0.58), (0.44, 0.0), (0.0, 0.58), (-0.44, 0.0)]
    return [(v + [v[0]], 0.070)]

def _m_hook():
    return [(_poly((0.20, -0.54), (0.20, 0.14)), 0.075),
            (_arc(-0.06, 0.14, 0.26, 0.0, 180.0, 18), 0.075)]

def _m_hourglass():
    return [(_arc(-0.90, 0.0, 0.62, -40.0, 40.0, 18), 0.085),
            (_arc(0.90, 0.0, 0.62, 140.0, 220.0, 18), 0.085)]

def _m_concentric():
    return [(_ring(0.0, 0.0, 0.26, 28), 0.060),
            (_ring(0.0, 0.0, 0.56, 44), 0.055),
            (_dot(0.0, 0.0), 0.085)]

def _m_lens():
    top, bot = [], []
    for i in range(25):
        t = -1.0 + 2.0 * i / 24
        top.append((0.56 * t, -0.30 * (1.0 - t * t)))
        bot.append((0.56 * t, 0.30 * (1.0 - t * t)))
    return [(top, 0.062), (bot, 0.062), (_dot(0.0, 0.0), 0.105)]

def _m_tau():
    return [(_poly((0.0, -0.34), (0.0, 0.56)), 0.075),
            (_poly((-0.50, -0.34), (0.50, -0.34)), 0.075),
            (_poly((-0.50, -0.34), (-0.50, -0.10)), 0.060),
            (_poly((0.50, -0.34), (0.50, -0.10)), 0.060)]

def _m_sigmoid():
    pts = []
    for i in range(37):
        t = -1.0 + 2.0 * i / 36
        pts.append((0.42 * math.sin(math.pi * t), 0.54 * t))
    return [(pts, 0.075)]

def _m_crown():
    bowl = _arc(0.0, -0.06, 0.44, 15.0, 165.0, 22)
    return [(bowl, 0.060),
            (_poly((0.42, 0.05), (0.30, -0.48)), 0.060),
            (_poly((0.0, 0.38), (0.0, -0.56)), 0.060),
            (_poly((-0.42, 0.05), (-0.30, -0.48)), 0.060)]

def _m_funnel():
    return [(_poly((-0.52, -0.50), (0.52, -0.50)), 0.055),
            (_poly((-0.50, -0.48), (-0.16, 0.10), (0.02, 0.42)), 0.065),
            (_poly((0.50, -0.48), (0.28, 0.10), (0.30, 0.42)), 0.065),
            (_arc(0.16, 0.42, 0.15, -90.0, 120.0, 14), 0.055)]

def _m_arrow():
    return [(_poly((0.0, 0.56), (0.0, -0.20)), 0.085),
            (_poly((-0.40, 0.08), (0.0, -0.56), (0.40, 0.08)), 0.085)]

_MOTIFS = (
    _m_bolt,
    _m_spiral,
    _m_chevrons,
    _m_wheel,
    _m_crescent,
    _m_trident,
    _m_vortex,
    _m_cross,
    _m_wave,
    _m_triangle,
    _m_drop,
    _m_starburst,
    _m_rhombus,
    _m_hook,
    _m_hourglass,
    _m_concentric,
    _m_lens,
    _m_tau,
    _m_sigmoid,
    _m_crown,
    _m_funnel,
    _m_arrow,
)
assert len(_MOTIFS) == MOTIFS

# --------------------------------------------------------------------------
# accent frames, OUTSIDE the motif so they alter the outline

def _a_ring():
    return [(_ring(0.0, 0.0, 0.685, 56), 0.048)]

def _a_triad():
    out = []
    for a in (270.0, 30.0, 150.0):
        r = math.radians(a)
        out.append((_dot(0.685 * math.cos(r), 0.685 * math.sin(r)), 0.095))
    return out

def _a_plinth():
    return [(_poly((-0.58, 0.665), (0.58, 0.665)), 0.050),
            (_poly((-0.58, 0.665), (-0.58, 0.48)), 0.050),
            (_poly((0.58, 0.665), (0.58, 0.48)), 0.050),
            (_arc(0.0, -0.62, 0.30, 200.0, 340.0, 16), 0.048)]

_ACCENTS = (_a_ring, _a_triad, _a_plinth)
assert len(_ACCENTS) == ACCENTS

# --------------------------------------------------------------------------
# signed distance field

def _seg_field(buf, dim, strokes):
    """Min-accumulate `distance - half_width` for every stroke into `buf`.

    Walked per SEGMENT over that segment's own bounding box rather than per
    pixel over every segment: a spiral is 44 short segments and each touches a
    handful of texels, so this is roughly thirty times less arithmetic than the
    naive loop and gives bit-identical answers.
    """
    half = dim * 0.5
    for pts, hw in strokes:
        margin = hw + _FIELD_MARGIN
        n = len(pts)
        pairs = ([(pts[0], pts[0])] if n == 1
                 else [(pts[i], pts[i + 1]) for i in range(n - 1)])
        for (ax, ay), (bx, by) in pairs:
            x0 = int(math.floor((min(ax, bx) - margin + 1.0) * half))
            x1 = int(math.ceil((max(ax, bx) + margin + 1.0) * half))
            y0 = int(math.floor((min(ay, by) - margin + 1.0) * half))
            y1 = int(math.ceil((max(ay, by) + margin + 1.0) * half))
            x0 = 0 if x0 < 0 else x0
            y0 = 0 if y0 < 0 else y0
            x1 = dim if x1 > dim else x1
            y1 = dim if y1 > dim else y1
            dx, dy = bx - ax, by - ay
            den = dx * dx + dy * dy
            for py in range(y0, y1):
                v = (py + 0.5) / half - 1.0
                row = py * dim
                wy = v - ay
                for px in range(x0, x1):
                    u = (px + 0.5) / half - 1.0
                    wx = u - ax
                    if den > 0.0:
                        t = (wx * dx + wy * dy) / den
                        if t < 0.0:
                            t = 0.0
                        elif t > 1.0:
                            t = 1.0
                        ex = wx - t * dx
                        ey = wy - t * dy
                    else:
                        ex, ey = wx, wy
                    d = math.sqrt(ex * ex + ey * ey) - hw
                    o = row + px
                    if d < buf[o]:
                        buf[o] = d

# --------------------------------------------------------------------------
# the set

PALETTES = (
    _P("tempest",   (0.38, 0.30, 0.62), (0.10, 0.07, 0.20), (0.72, 0.58, 1.00),
          (0.13, 0.10, 0.22), (0.05, 0.04, 0.10), (0.97, 0.95, 1.00),
          (0.85, 0.78, 1.00), (0.62, 0.48, 0.95)),
    _P("galecraft", (0.26, 0.42, 0.58), (0.06, 0.12, 0.20), (0.58, 0.86, 1.00),
          (0.09, 0.15, 0.22), (0.03, 0.06, 0.10), (0.95, 0.99, 1.00),
          (0.74, 0.92, 1.00), (0.40, 0.74, 0.98)),
    _P("windward",  (0.24, 0.46, 0.44), (0.05, 0.14, 0.14), (0.56, 0.98, 0.88),
          (0.08, 0.17, 0.16), (0.03, 0.07, 0.07), (0.95, 1.00, 0.99),
          (0.72, 0.99, 0.92), (0.36, 0.86, 0.76)),
    # ORDER MATTERS: polarity is (motif + palette) % 2, so the palettes that can
    # share a polarity for one motif are {0,2,4} and {1,3,5}. Those two sets must
    # each be hue-distant or the same-motif same-polarity pairs collapse.
    # even = violet / teal / grey, odd = blue / magenta / amber. The first
    # ordering put grey in the ODD set beside blue and the two collided:
    # 26 & 114 (galecraft vs neutral) was the worst pair in the whole set.
    _P("stormcall", (0.44, 0.24, 0.46), (0.14, 0.05, 0.16), (1.00, 0.60, 0.92),
          (0.17, 0.08, 0.18), (0.06, 0.03, 0.07), (1.00, 0.96, 0.99),
          (1.00, 0.80, 0.96), (0.94, 0.44, 0.84)),
    _P("neutral",   (0.30, 0.34, 0.40), (0.08, 0.10, 0.13), (0.80, 0.88, 0.98),
          (0.11, 0.13, 0.16), (0.04, 0.05, 0.06), (0.97, 0.98, 1.00),
          (0.86, 0.91, 0.98), (0.60, 0.70, 0.86)),
    _P("thunderhead", (0.30, 0.30, 0.34), (0.07, 0.07, 0.09), (1.00, 0.82, 0.44),
          (0.12, 0.11, 0.12), (0.04, 0.04, 0.05), (1.00, 0.98, 0.93),
          (1.00, 0.90, 0.66), (0.96, 0.72, 0.28)),
)
assert len(PALETTES) == NPALETTE

# ground -> (polarity, tilt, tightness, mottle)
#
# POLARITY IS THE WHOLE IDEA AND IT REPLACED A WORSE ONE. The first version of
# this file pulled storm's `mk_sky`/`mk_aerial` in as the ground and drew a
# near-white rune on top. That scored well and LOOKED WORSE THAN BOTH PARENTS:
# storm's appeal was in its SCENES, not its sky, so subtracting the subject left
# a blur, and forcing every rune to near-white bought the greyscale margin by
# throwing away all the colour character sigil had. Rendered, it read as a
# generic mystical symbol set.
#
# So the ground went back to a smooth two-colour field -- which is what DXT1
# keeps best anyway -- and the luma separation comes from POLARITY instead:
# grounds 0-5 are dark with a light rune, 6-10 are light with a dark rune. Two
# icons sharing a motif across those halves are near-inverses of each other, so
# they are maximally far apart in greyscale WITHOUT either one being colourless.
# (tilt, tightness, mottle, lift). `lift` moves the ground's VALUE within its own
# polarity block, so the three same-polarity icons of a motif are separated in
# luma as well as hue.
#
# THE INDEXING IS THE FIX AND IT IS WORTH READING. The first version chose the
# ground as `(3*motif + palette) % 11` and split polarity by index range. Those
# are six CONSECUTIVE indices for a fixed motif, so all six landed in one
# polarity block -- polarity never fired for the pairs it existed to separate,
# which are exactly the same-motif pairs. Measured: minimum confusability 10.65,
# WORSE THAN ALL FOUR PARENTS, and greyscale 3.05. Polarity is now
# `(motif + palette) % 2`, which alternates by construction.
# The LIFTS are spread WITHIN each index parity, not across the six. For a fixed
# motif the three same-polarity grounds are g, g+2, g+4 (mod 6) -- always one
# parity class -- so lifts that merely alternate would give those three nearly
# the same value. {g0,g2,g4} and {g1,g3,g5} each span the full range instead.
GROUNDS = (
    (118.0, 1.00, 0.16, -0.22),
    ( 22.0, 0.86, 0.22,  0.18),
    (205.0, 1.12, 0.13,  0.00),
    (300.0, 0.94, 0.19, -0.20),
    ( 68.0, 1.06, 0.25,  0.22),
    (160.0, 0.90, 0.15,  0.02),
)
assert len(GROUNDS) == NGROUND

_LIMIT = 0.75          # the safe area, as a fraction -- chrome eats 12.5% a side
_GLOW = 0.15           # outer glow radius, normalised units
_HALO = 0.26           # dark contact halo, normalised units
_SHADOW = (0.028, -0.028)


def _translate(strokes, dx, dy):
    return [([(x + dx, y + dy) for x, y in pts], hw) for pts, hw in strokes]


def _clamp(v, a=0.0, b=1.0):
    return a if v < a else (b if v > b else v)


def _mix(c, d, t):
    return (c[0] + (d[0] - c[0]) * t,
            c[1] + (d[1] - c[1]) * t,
            c[2] + (d[2] - c[2]) * t)


def describe(i):
    m, p = i % MOTIFS, i // MOTIFS
    g = (3 * m + 5 * p) % NGROUND
    return (f"i={i:>3} motif={m:>2} palette={PALETTES[p]['name']:<11} "
            f"ground={g} polarity={(m + p) % 2} accent={(p // 2) % 3}")


def icon(i, dim=64):
    """Icon `i` (0..131) as RGB bytes, len == dim*dim*3. Pure and deterministic."""
    if not isinstance(i, int) or not 0 <= i < COUNT:
        raise ValueError(f"icon index {i!r} outside 0..{COUNT - 1}")
    if dim < 8 or dim % 4:
        raise ValueError(f"dim {dim} must be a multiple of 4 and >= 8")

    motif = i % MOTIFS
    pal = i // MOTIFS
    polarity = (motif + pal) % 2
    gidx = (3 * motif + 5 * pal) % NGROUND

    P = PALETTES[pal]
    tilt, tight, mottle, lift = GROUNDS[gidx]

    # A subtle mottle, seeded off the GROUND rather than off i, so a motif's six
    # variants do not each invent new weather -- that would add distinctness the
    # metrics reward and the eye reads as noise.
    nz = Noise(random.Random(0x5700 + gidx * 104729), base=1.6)

    # ACCENT: the floor of this whole set is the closest SAME-MOTIF pair, and
    # those differ only in palette and ground -- i.e. in COLOUR. `pal // 2` is 0,
    # 1, 2 across the three same-polarity siblings of any motif, so each of them
    # gets a different frame and the pair differs in SHAPE as well. The frames
    # are sigil's own, and they sit OUTSIDE the motif so they alter the outline
    # rather than the glyph.
    accent = (pal // 2) % ACCENTS
    strokes = _MOTIFS[motif]()
    inf = 1e9
    n = dim * dim
    dm = [inf] * n
    ds = [inf] * n
    da = [inf] * n
    _seg_field(dm, dim, strokes)
    _seg_field(ds, dim, _translate(strokes, *_SHADOW))
    _seg_field(da, dim, _ACCENTS[accent]())

    lite, glow, dark = P["lite"], P["glow"], P["dark"]
    deep = _mix(P["sky_lo"], dark, 0.55)
    pale = _mix(P["lite"], P["accent"], 0.30)

    if polarity == 0:                      # light rune on a deep ground
        g_in, g_out = _mix(P["sky_hi"], deep, 0.35), deep
        ink_hi, ink_lo = pale, _mix(pale, P["accent"], 0.55)
        halo_c, halo_k = dark, 0.50
    else:
        # Dark rune on a LIT ground -- a flash behind the glyph, not a pastel
        # tile. The first version made `g_out` a saturated pale and the whole
        # half read as app icons: lavender, mint, peach. A bright desaturated
        # core falling to a deep saturated rim is the same polarity and reads
        # as weather.
        g_in = _mix(P["lite"], P["accent"], 0.14)
        g_out = _mix(P["accent"], dark, 0.42)
        ink_hi, ink_lo = _mix(deep, P["accent"], 0.22), dark
        halo_c, halo_k = P["lite"], 0.46

    if lift > 0.0:
        g_in, g_out = _mix(g_in, P["lite"], lift * 0.55), _mix(g_out, P["lite"], lift * 0.40)
    elif lift < 0.0:
        g_in, g_out = _mix(g_in, dark, -lift * 0.55), _mix(g_out, dark, -lift * 0.40)

    ta = math.radians(tilt)
    lx, ly = math.cos(ta), math.sin(ta)

    aa = 1.0 / dim
    half = dim * 0.5
    out = bytearray(n * 3)
    o = 0
    for py in range(dim):
        v = (py + 0.5) / half - 1.0
        # Top-lit rune: the one cue that keeps a flat silhouette from reading as
        # a sticker. Kept, because it survived the first version's failure.
        core = _mix(ink_lo, ink_hi, _clamp((v + 0.70) / 1.40))
        row = py * dim
        for px in range(dim):
            u = (px + 0.5) / half - 1.0

            # Ground: a smooth radial field with a directional sweep. Smooth is
            # what DXT1 keeps; the sweep is what stops 132 vignettes looking
            # like one vignette.
            r = _clamp(math.sqrt(u * u + v * v) / (1.24 * tight))
            col = _mix(g_in, g_out, r * r * (3.0 - 2.0 * r))
            sweep = 0.5 + 0.5 * (u * lx + v * ly)
            col = _mix(col, g_in, 0.16 * sweep)
            col = _mix(col, g_out, 0.10 * (1.0 - sweep))
            m = 1.0 + mottle * nz(u * 1.25, v * 1.25)
            col = (col[0] * m, col[1] * m, col[2] * m)

            idx = row + px

            # 0. Accent frame, under the rune.
            dacc = da[idx]
            if dacc < _GLOW:
                if dacc > 0.0:
                    f = 1.0 - dacc / _GLOW
                    col = _mix(col, glow, 0.30 * f * f)
                else:
                    col = _mix(col, glow, 0.30)
                col = _mix(col, ink_hi, _clamp((aa - dacc) / (2.0 * aa)) * 0.85)

            # 1. Contact halo, in whichever direction the polarity needs, so the
            #    rune separates from its own ground without a hard outline.
            d = dm[idx]
            if d < _HALO:
                t = 1.0 - _clamp(d / _HALO) if d > 0.0 else 1.0
                col = _mix(col, halo_c, halo_k * t * t)

            # 2. Offset shadow -- depth without a second light source.
            d2 = ds[idx]
            if d2 < aa:
                col = _mix(col, halo_c, 0.45 * _clamp((aa - d2) / (2.0 * aa)))

            # 3. Outer glow, only where the rune is the lit thing.
            if polarity == 0 and 0.0 < d < _GLOW:
                f = 1.0 - d / _GLOW
                col = _mix(col, glow, 0.55 * f * f)

            # 4. The rune itself, antialiased over one texel.
            cov = _clamp((aa - d) / (2.0 * aa))
            if cov > 0.0:
                col = _mix(col, core, cov)

            out[o] = int(_clamp(col[0]) * 255.0 + 0.5)
            out[o + 1] = int(_clamp(col[1]) * 255.0 + 0.5)
            out[o + 2] = int(_clamp(col[2]) * 255.0 + 0.5)
            o += 3
    return bytes(out)
