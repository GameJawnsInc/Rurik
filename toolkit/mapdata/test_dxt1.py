#!/usr/bin/env python3
"""Check the DXT1 codec -- both directions, and the arm the encoder cannot reach.

    python toolkit/mapdata/test_dxt1.py
    python toolkit/mapdata/test_dxt1.py --all      # + a retail sweep

`dxt1.py` shipped in the texture arc with an ENCODER and no test file at all;
rung M5 added `decode`/`unpack`/`decode_block` because a texture export has to
read ArenaNet's blocks, and this file is the first test either direction has
had.

WHY `decode(encode(x)) ~= x` IS THE WEAK HALF, and it is weaker here than the
usual round-trip complaint. DXT1 is LOSSY, so the check can only be "close",
and a tolerance wide enough to admit real compression error is wide enough to
admit a lot of wrong. Worse, the two directions SHARE `from565` and the
palette arithmetic, so an error in the shared part cancels exactly and the
round trip cannot see it. So:

  * **Section 2 recomputes the palette from the SPEC**, in this file, out of
    integer arithmetic that imports nothing from `dxt1` -- 565 unpacking with
    the low-bit replication, the 2/3 and 1/3 interpolants -- and requires
    `decode_block` to agree exactly. That is the check a shared-helper bug
    cannot survive.
  * **Section 3 exercises the PUNCH-THROUGH palette**, which `encode_block`
    never emits: it always forces `c0 > c1` on purpose, so the `c0 <= c1`
    branch -- one interpolated middle, index 3 fully transparent -- is
    unreachable from any round trip. A decoder missing it renders every
    cut-out texture (foliage, fences, grates) as solid black where it should
    be see-through. Only hand-built blocks reach that arm.
  * **Section 4 pins PLANAR against INTERLEAVED.** The two payloads are the
    same LENGTH, so no size check separates them and a wrong choice yields
    noise rather than an error -- which is why the texture arc had to settle
    it on screen (studies/texture/FINDINGS.md section 4: planar was a picture,
    interleaved was noise). Here it is pinned as a difference between two live
    answers, with the cross-decode required to differ.

SECTION 6 IS pattern_icon, WHICH IS NOT A CODEC AT ALL -- it is the picture
the texture arc exists to put on a skillbar, and it is here because it shipped
with a constant that could not survive being called at any size but the one it
was written for. `safe = min(w,h)/2 - 16` raised ZeroDivisionError at exactly
32x32 and drew nonsense below ~40x40. The 16 is not a pixel count: OBSERVED
2026-08-14 (studies/texture/FINDINGS.md section 9) the client stretches the
whole texture linearly onto a fixed screen quad, so the chrome eats a constant
FRACTION. The retired rule is reproduced IN THIS FILE as a live function, so
"128x128 is unchanged" and "64x64 is not" are both differences between two
live answers rather than arithmetic the test asks the module to confirm about
itself -- and the strongest check is the one the old rule cannot pass at all:
a proportional picture box-filtered 2:1 IS the picture drawn at half size.

SECTION 7 IS THE ONE THAT NEEDS THE VAULT, and it is deliberately not a
round trip: it decodes REAL retail DXT1 levels and asserts only things the
archive can refute -- the payload length equals the block count exactly, and
every decoded level is `w*h*4` bytes with alpha 255 everywhere (DXT1 raw
levels in this corpus are all the opaque form). It also records the finding
that shaped M5's scope: **only 25 of 1,533 ATEX containers have a RAW level
0**, so this decoder alone reaches 1.6% of the corpus and the rest sit behind
ATEX level compression codes that nothing here decodes yet.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks                                                    # noqa: E402
import dxt1                                                      # noqa: E402

# MEASURED from green runs, 2026-08-14: 55 by default, 56 under `--all`
# (which adds the raw-level-0 population check), 52 with no vault at all --
# so a bare machine goes RED here and the retail sweep's declared skip names
# why. That is unchanged in kind by section 6: the floor has always been the
# full default run rather than the mandatory core (it was 32 against a
# vault-less 30), and an earlier version of this comment claimed a bare
# machine "still clears the bar", which it never did.
#
# WHICH OF SECTION 6's 23 CHECKS ARE LOAD-BEARING WAS MEASURED, by building
# seven one-edit sabotages of `dxt1.py` and running this file against each
# (2026-08-14, against a vault-less baseline of 52 and 0 red):
#
#   safe reverted to `min/2 - 16.0`   9 red   the defect itself
#   the refusal deleted                4 red   all four refusals, nothing else
#   MIN_ICON -> 100000                12 red   refuses everything
#   MIN_ICON -> 40                    10 red
#   ICON_MARGIN 0.125 -> 0.25          4 red   incl. the 128x128 byte identity
#   pattern_icon returns zeros         5 red
#   refusal tests max() not min()      1 red   the 64x8 line, ALONE
#
# The last row is why 64x8 is in the list at all, and the zeros row is the
# one that justifies the feature checks: a pattern_icon that returns a field
# of zeros keeps every "NxN is still drawn" length check GREEN and is caught
# only by the corner, the sun, the colour census and the 128x128 identity.
#
# TWO OF THE SEVEN FOUND DEFECTS IN THIS FILE rather than in the module, and
# both are noted at their call sites: MIN_ICON -> 100000 originally HUNG past
# a 600 s timeout printing no verdict (the positive controls drew at
# `dxt1.MIN_ICON`, so the sabotage asked for a 100000x100000 image), and the
# reverted `safe` killed section 6b outright at its sixth check.
LEDGER = checks.Ledger("dxt1 codec", floor=55)
check = checks.adopt(LEDGER)

#: MEASURED 2026-08-13 over the first 6,000 MFT rows of the study archive.
#: Reported by section 5 and quoted in the module docstring; the point of
#: pinning it is that it is the number that bounds what M5 can texture.
RAW_LEVEL0 = 25
ATEX_SEEN = 1533


# --- a palette written from the SPEC, importing nothing from dxt1 ----------

def spec_565(c):
    """RGB565 to 8-bit, with the low-bit replication the format requires."""
    r, g, b = (c >> 11) & 0x1F, (c >> 5) & 0x3F, c & 0x1F
    return ((r << 3) | (r >> 2), (g << 2) | (g >> 4), (b << 3) | (b >> 2))


def spec_palette(c0, c1):
    """The four colours, per the DXT1 specification. Both palette forms."""
    a, b = spec_565(c0), spec_565(c1)
    if c0 > c1:
        return [a + (255,), b + (255,),
                tuple((2 * a[i] + b[i]) // 3 for i in range(3)) + (255,),
                tuple((a[i] + 2 * b[i]) // 3 for i in range(3)) + (255,)]
    return [a + (255,), b + (255,),
            tuple((a[i] + b[i]) // 2 for i in range(3)) + (255,),
            (0, 0, 0, 0)]


def gradient(w, h):
    return bytes(v for y in range(h) for x in range(w)
                 for v in ((x * 16) % 256, (y * 32) % 256, ((x + y) * 8) % 256))


# --- 1. pack/unpack, which is LOSSLESS and therefore assertable exactly ----

def section_packing():
    print("\n== 1. pack / unpack (lossless -- exact equality is fair here) ==")
    w, h = 16, 8
    blocks = dxt1.encode(gradient(w, h), w, h)
    check(len(blocks) == (w // 4) * (h // 4),
          "encode produces one block per 4x4 cell",
          "%d for a %dx%d image" % (len(blocks), w, h))
    for layout in dxt1.LAYOUTS:
        payload = dxt1.pack(blocks, layout)
        check(len(payload) == 8 * len(blocks),
              "%s payload is 8 bytes per block" % layout, "%d" % len(payload))
        check(dxt1.unpack(payload, len(blocks), layout) == blocks,
              "%s: unpack(pack(b)) == b, exactly" % layout)

    # THE LAYOUTS MUST DIFFER. Same length, different bytes -- which is why
    # no size check could ever have settled this and the texture arc had to
    # put both on screen.
    p = dxt1.pack(blocks, dxt1.PLANAR)
    i = dxt1.pack(blocks, dxt1.INTERLEAVED)
    check(len(p) == len(i) and p != i,
          "planar and interleaved are the same LENGTH and different BYTES",
          "%d bytes each" % len(p))
    check(dxt1.unpack(p, len(blocks), dxt1.INTERLEAVED) != blocks,
          "and reading planar bytes as interleaved gives the WRONG blocks -- "
          "so the layout is a real choice, not a formality")


# --- 2. decode_block against the spec, not against the encoder ------------

def section_spec():
    print("\n== 2. decode_block vs a palette computed HERE from the spec ==")
    cases = [(0xFFFF, 0x0000), (0xF800, 0x001F), (0x07E0, 0xF81F),
             (0x1234, 0x4321), (0x0000, 0xFFFF), (0x8000, 0x8000),
             (0x0001, 0x0002)]
    agree = 0
    for c0, c1 in cases:
        want = spec_palette(c0, c1)
        idx = 0b11_10_01_00_11_10_01_00_11_10_01_00_11_10_01_00
        got = dxt1.decode_block(c0, c1, idx)
        expect = [want[(idx >> (2 * n)) & 3] for n in range(16)]
        if got == expect:
            agree += 1
        else:
            print("      MISMATCH c0=%04X c1=%04X: %r vs %r"
                  % (c0, c1, got[:2], expect[:2]))
    check(agree == len(cases),
          "decode_block matches the spec palette on all %d endpoint pairs, "
          "including both palette FORMS" % len(cases),
          "%d/%d" % (agree, len(cases)))

    # Index extraction: pixel n must read bits 2n..2n+1, in row-major order.
    # A transposed or reversed reader passes a uniform block and fails this.
    idx = sum(((n % 4) << (2 * n)) for n in range(16))
    got = dxt1.decode_block(0xFFFF, 0x0000, idx)
    want = spec_palette(0xFFFF, 0x0000)
    check(got == [want[n % 4] for n in range(16)],
          "pixel n takes its 2 bits from bit 2n -- row-major, low bits first")

    # 565 endpoint unpacking must REPLICATE the low bits, so full-scale maps
    # to 255 rather than 248/252. A shift-only reader is dim by ~3%.
    white = dxt1.decode_block(0xFFFF, 0xFFFE, 0)[0]
    check(white == (255, 255, 255, 255),
          "0xFFFF unpacks to pure white -- the low-bit replication is there, "
          "not a bare shift", repr(white))


# --- 3. the punch-through arm the encoder never emits ---------------------

def section_punchthrough():
    print("\n== 3. punch-through (c0 <= c1) -- unreachable from any encode ==")
    # Every block encode_block emits is the opaque form, so this arm has to
    # be built by hand or it is never entered. Prove that premise first.
    for pixels in ([(0, 0, 0)] * 16, [(255, 255, 255)] * 16,
                   [(i * 15, 0, 255 - i * 15) for i in range(16)]):
        c0, c1, _idx = dxt1.encode_block(pixels)
        check(c0 > c1,
              "encode_block emits the OPAQUE form (c0 > c1)",
              "%04X > %04X" % (c0, c1))

    px = dxt1.decode_block(0x0000, 0xFFFF, 0b11_10_01_00)
    check(px[3] == (0, 0, 0, 0),
          "index 3 under c0 <= c1 is FULLY TRANSPARENT -- the cut-out arm",
          repr(px[3]))
    check(px[2][3] == 255 and px[2][:3] == (127, 127, 127),
          "index 2 is the single midpoint, opaque", repr(px[2]))
    opq = dxt1.decode_block(0xFFFF, 0x0000, 0b11_10_01_00)
    check(opq[3] == (85, 85, 85, 255),
          "while under c0 > c1 index 3 is the 1/3 interpolant and OPAQUE -- "
          "the two forms really are different", repr(opq[3]))
    check(all(p[3] == 255 for p in opq),
          "no pixel of an opaque block is transparent")


# --- 4. whole-level decode ------------------------------------------------

def section_level():
    print("\n== 4. decode() over a whole level ==")
    w, h = 16, 8
    rgb = gradient(w, h)
    blocks = dxt1.encode(rgb, w, h)
    rgba = dxt1.decode(dxt1.pack(blocks, dxt1.PLANAR), w, h)
    check(len(rgba) == w * h * 4,
          "decode returns w*h*4 bytes", "%d" % len(rgba))
    check(all(rgba[i * 4 + 3] == 255 for i in range(w * h)),
          "every pixel of an encoder-produced level is opaque")

    # LOSSY, so the claim is a BOUND, and the bound is stated rather than
    # tuned: DXT1 quantises to 565 with four levels per block, so single
    # channel error on a smooth gradient stays well under 64.
    err = [abs(rgba[i * 4 + c] - rgb[i * 3 + c])
           for i in range(w * h) for c in range(3)]
    worst, mean = max(err), sum(err) / len(err)
    print("    round-trip error: max %d, mean %.2f" % (worst, mean))
    check(worst < 64 and mean < 24,
          "round-trip error is within DXT1's quantisation, not garbage",
          "max %d mean %.2f" % (worst, mean))

    # A FLAT image must survive nearly exactly -- one colour needs no
    # interpolation, so a decoder that mixed up the palette order would show
    # up here even though the gradient bound above is loose.
    # The bound is ONE 5-bit quantum and is derived, not tuned: red and blue
    # keep 5 bits, so the representable values are 8 apart and the worst
    # rounding is 7. (200 -> 206 is the case this actually hits: 200>>3 = 25,
    # and 25 replicated back is 206.) An earlier draft asserted 4 and went
    # red at 6 -- the codec was right and the test's arithmetic was wrong.
    flat = bytes((200, 100, 50) * (w * h))
    out = dxt1.decode(dxt1.pack(dxt1.encode(flat, w, h), dxt1.PLANAR), w, h)
    ferr = max(abs(out[i * 4 + c] - flat[i * 3 + c])
               for i in range(w * h) for c in range(3))
    check(ferr <= 7,
          "a FLAT image round-trips to within one 5-bit quantum -- far "
          "tighter than the gradient's %d, which is the point" % worst,
          "max err %d" % ferr)

    # Position: a single bright block in a corner must come back in THAT
    # corner. Catches a transposed block walk, which the flat and gradient
    # checks cannot.
    img = bytearray((0, 0, 0) * (w * h))
    for y in range(4):
        for x in range(4):
            o = (y * w + x) * 3
            img[o:o + 3] = b"\xff\xff\xff"
    out = dxt1.decode(dxt1.pack(dxt1.encode(bytes(img), w, h), dxt1.PLANAR),
                      w, h)
    tl = out[0] > 200
    tr = out[((w - 1)) * 4] > 200
    bl = out[((h - 1) * w) * 4] > 200
    check(tl and not tr and not bl,
          "a white 4x4 block at the top-left decodes at the TOP-LEFT -- the "
          "block walk is not transposed", "tl=%s tr=%s bl=%s" % (tl, tr, bl))


# --- 5. refusals ----------------------------------------------------------

def section_refusals():
    print("\n== 5. refusals ==")

    def refuses(fn, label):
        try:
            fn()
        except ValueError as exc:
            check(True, "refused: %s" % label, str(exc)[:54])
        except Exception as exc:                       # noqa: BLE001
            check(False, "refused: %s" % label,
                  "raised %s" % type(exc).__name__)
        else:
            check(False, "refused: %s" % label, "no refusal")

    refuses(lambda: dxt1.unpack(b"\0" * 7, 1, dxt1.PLANAR),
            "a payload one byte short")
    refuses(lambda: dxt1.unpack(b"\0" * 9, 1, dxt1.PLANAR),
            "a payload one byte long")
    refuses(lambda: dxt1.unpack(b"\0" * 8, 1, "sideways"),
            "an unknown layout name")
    refuses(lambda: dxt1.decode(b"\0" * 8, 5, 4), "a width that is not 4x4")
    refuses(lambda: dxt1.decode(b"\0" * 8, 4, 6), "a height that is not 4x4")
    refuses(lambda: dxt1.encode(b"\0" * 48, 5, 4), "encode of a ragged width")

    # POSITIVE CONTROL: the exact sizes are still accepted. Without this the
    # six lines above are satisfied by a codec that refuses everything.
    ok = dxt1.decode(b"\0" * 8, 4, 4)
    check(len(ok) == 64, "and an exact 4x4 block is still decoded",
          "%d bytes" % len(ok))


# --- 6. pattern_icon: the constant that was a pixel count -----------------

def retired_icon(width, height):
    """`pattern_icon` AS IT SHIPPED, so the fix is a difference not a claim.

    Verbatim except for the one line under test -- `safe` -- which is why the
    dither, the vignette and the palette arithmetic are all copied rather than
    imported. If they were imported, a change to any of them would move both
    answers together and the comparison below would quietly stop separating
    anything.
    """
    out = bytearray(width * height * 3)
    cx, cy = width / 2.0, height / 2.0
    safe = min(width, height) / 2.0 - 16.0                 # <-- THE OLD RULE
    horizon = cy + safe * 0.35
    sun_r = safe * 0.46

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
                sd = ((x - cx) ** 2
                      + (y - (horizon - sun_r * 0.35)) ** 2) ** 0.5
                if sd < sun_r:
                    k = 1.0 - sd / sun_r
                    c = (255, 190 + 60 * k, 70 + 120 * k)
                else:
                    c = (40 + 150 * (1 - t), 30 + 70 * (1 - t),
                         80 + 60 * (1 - t))
            else:
                k = (y - horizon) / max(safe, 1)
                c = (90 - 50 * k, 40 - 20 * k, 70 - 40 * k)
                if int(x * 0.7 + y * 1.3) % 11 < 2:
                    c = (c[0] + 40, c[1] + 25, c[2] + 30)
            v = 1.0 - 0.55 * max(0.0, (t - 0.72) / 0.28) ** 2
            put(x, y, (c[0] * v, c[1] * v, c[2] * v))
    return bytes(out)


def halve(rgb, w, h):
    """A 2:1 box filter, written here out of integer arithmetic."""
    out = bytearray((w // 2) * (h // 2) * 3)
    for y in range(h // 2):
        for x in range(w // 2):
            for c in range(3):
                s = sum(rgb[((2 * y + dy) * w + (2 * x + dx)) * 3 + c]
                        for dy in range(2) for dx in range(2))
                out[(y * (w // 2) + x) * 3 + c] = s // 4
    return bytes(out)


def mae(a, b):
    return sum(abs(a[i] - b[i]) for i in range(len(a))) / len(a)


def sun_pixel(rgb, n):
    """The centre of the sun disc, located from the module's own fractions."""
    safe = n * dxt1._SAFE_FRAC
    y = int(n / 2.0 + safe * 0.35 - safe * dxt1.ICON_SUN_FRAC * 0.35)
    o = (y * n + n // 2) * 3
    return tuple(rgb[o:o + 3])


def section_icon():
    print("\n== 6. pattern_icon -- a FRACTION, not sixteen pixels ==")

    # THE CONSTRAINT: 128x128 must not have moved. Not "the radius agrees" --
    # every byte, against the retired rule running in this process.
    big, obig = dxt1.pattern_icon(128, 128), retired_icon(128, 128)
    check(big == obig,
          "128x128 is BYTE-IDENTICAL to the retired rule -- 128/2 - 16 and "
          "128 * 0.375 are both 48.0, so the fix changed nothing where the "
          "constant was written to work", "%d bytes" % len(big))

    # ...and 64x64 must have. Same two functions, so this is the pair that
    # makes the sentence above a measurement instead of a tautology.
    small, osmall = dxt1.pattern_icon(64, 64), retired_icon(64, 64)
    check(small != osmall,
          "and 64x64 is NOT -- the old rule kept 16.0 of a 32.0 half-side "
          "where the fraction keeps 24.0, throwing away a quarter of the "
          "picture")

    # THE LOAD-BEARING CHECK. A picture defined in proportions is the same
    # picture at every size, so box-filtering the 128 down must land on the
    # direct 64. The old rule composes a DIFFERENT picture at 64 and cannot
    # pass this at any tolerance that means anything -- which is exactly the
    # reason FINDINGS section 9's arm Q had to ship a mipmap of arm S rather
    # than a second call to pattern_icon.
    now = mae(halve(big, 128, 128), small)
    was = mae(halve(obig, 128, 128), osmall)
    print("    mipmap(128) vs direct 64:  fraction %.3f/255   pixels %.3f/255"
          % (now, was))
    check(now < 5.0,
          "a 2:1 box filter of the 128 IS the 64 -- the picture is scale "
          "invariant now", "%.3f/255 mean absolute" % now)
    check(was > 12.0 and was > 3 * now,
          "while under the retired rule the two were different pictures -- "
          "the separation is what makes the check above worth its exit code",
          "%.3f/255, %.1fx" % (was, was / max(now, 1e-9)))
    # The residual is not zero, and it is NOT one thing -- which is worth
    # writing down, because the first draft of this comment said it was the
    # ground dither and that was a guess. MEASURED 2026-08-14 by stubbing the
    # dither out: 2.039 with it, 1.251 without, so the dither indexing
    # ABSOLUTE pixel coordinates (`int(x*0.7 + y*1.3) % 11`) is about 40% of
    # it and the rest is box-filtering itself -- averaging four samples is not
    # the same as evaluating the picture at half resolution, and the sun's
    # rim, the horizon and the vignette all fall between samples.
    check(now > 0.0,
          "and it is not exactly zero -- roughly 40% the ground dither, which "
          "is in absolute pixel coordinates, and the rest the box filter",
          "%.3f/255" % now)

    # 32x32 IS THE SIZE THE OLD RULE DIED AT: 32/2 - 16 == 0.
    try:
        retired_icon(32, 32)
        died = None
    except ZeroDivisionError:
        died = "ZeroDivisionError"
    except Exception as exc:                               # noqa: BLE001
        died = type(exc).__name__
    check(died == "ZeroDivisionError",
          "the retired rule really does divide by zero at 32x32 -- the "
          "defect is reproduced here, not quoted", repr(died))
    try:
        px = dxt1.pattern_icon(32, 32)
    except Exception as exc:                               # noqa: BLE001
        check(False, "and the same call now returns a whole 32x32 image",
              "raised %s" % type(exc).__name__)
    else:
        check(len(px) == 32 * 32 * 3,
              "and the same call now returns a whole 32x32 image",
              "%d bytes" % len(px))


def section_icon_bounds():
    print("\n== 6b. pattern_icon refusals and the picture itself ==")

    # MIN_ICON against a LITERAL written here, because a constant compared to
    # the module's own symbol is free to move and take the test with it.
    check(dxt1.MIN_ICON == 12,
          "MIN_ICON is 12", "%d" % dxt1.MIN_ICON)
    check(dxt1.ICON_MARGIN == 0.125 and dxt1._SAFE_FRAC == 0.375,
          "the margin is 12.5% of the short side and the safe radius 37.5%",
          "%.3f / %.3f" % (dxt1.ICON_MARGIN, dxt1._SAFE_FRAC))

    # ...and DERIVED, not chosen: MIN_ICON is where the sun disc stops
    # covering a whole DXT1 4x4 block. Checking the derivation both ways is
    # what stops 12 being a number somebody liked.
    span = 2 * dxt1.ICON_SUN_FRAC * dxt1._SAFE_FRAC
    check(span * dxt1.MIN_ICON >= 4.0 > span * (dxt1.MIN_ICON - 1),
          "MIN_ICON is the smallest short side whose sun disc spans a DXT1 "
          "block -- 4 / %.3f, so 12 and not 11" % span,
          "%.2f px at %d, %.2f at %d"
          % (span * dxt1.MIN_ICON, dxt1.MIN_ICON,
             span * (dxt1.MIN_ICON - 1), dxt1.MIN_ICON - 1))

    def refuses(w, h, label):
        try:
            dxt1.pattern_icon(w, h)
        except ValueError as exc:
            check(True, "refused: %s" % label, str(exc)[:54])
        except Exception as exc:                           # noqa: BLE001
            check(False, "refused: %s" % label,
                  "raised %s" % type(exc).__name__)
        else:
            check(False, "refused: %s" % label, "no refusal")

    # EVERY SIZE BELOW IS A LITERAL, and that is not a style preference. The
    # first draft passed `dxt1.MIN_ICON` and `dxt1.MIN_ICON - 1` here, so a
    # sabotage setting MIN_ICON to 100000 did not redden -- it asked the test
    # to draw a 100000x100000 image and HUNG for ten minutes, past its own
    # timeout, printing no verdict. A check whose workload is computed from
    # the symbol under test moves with the symbol; the literals plus the
    # MIN_ICON == 12 check above are what pin it in place.
    refuses(8, 8, "8x8 -- too small to be a picture")
    refuses(11, 11, "11x11 -- one below MIN_ICON")
    refuses(64, 8, "64x8 -- the SHORT side is what has to clear the bar")
    refuses(0, 0, "a zero dimension")

    # POSITIVE CONTROLS. Without these, four refusals are satisfied by a
    # pattern_icon that refuses everything -- which protects nothing, because
    # the tool then never draws.
    for n in (12, 16, 32, 64, 128):
        try:
            got = dxt1.pattern_icon(n, n)
        except Exception as exc:                           # noqa: BLE001
            check(False, "%dx%d is still drawn" % (n, n),
                  "raised %s" % type(exc).__name__)
            continue
        check(len(got) == n * n * 3, "%dx%d is still drawn" % (n, n),
              "%d bytes" % len(got))

    # AND IT IS A PICTURE, not a field of zeros -- which is what every length
    # check above is also satisfied by. Two features the composition puts at
    # known places, asserted at every size because both are proportional:
    # the corner always falls outside `safe` (a corner is 0.707 of the short
    # side from centre and `safe` is 0.375, at every n), and the sun disc
    # always sits just above the horizon.
    #
    # The per-size draw is GUARDED. Reverting `safe` to the pixel count makes
    # 32x32 raise, and unguarded that killed this whole section at its sixth
    # check -- the remaining checks never ran and the failure arrived as a
    # traceback rather than as something named.
    corners, suns, drew = 0, 0, 0
    sizes = (12, 16, 32, 40, 64, 128, 256)
    for n in sizes:
        try:
            rgb = dxt1.pattern_icon(n, n)
        except Exception as exc:                           # noqa: BLE001
            print("      %dx%d raised %s" % (n, n, type(exc).__name__))
            continue
        drew += 1
        if tuple(rgb[0:3]) == (10, 8, 20):
            corners += 1
        r, g, b = sun_pixel(rgb, n)
        if r == 255 and g >= 200 and b >= 120:
            suns += 1
    check(drew == len(sizes),
          "every size from %d to %d draws at all" % (sizes[0], sizes[-1]),
          "%d/%d" % (drew, len(sizes)))
    check(corners == len(sizes),
          "the corner is the dark surround at every size -- it is outside "
          "`safe` for any n, which is only true of a proportional radius",
          "%d/%d" % (corners, len(sizes)))
    check(suns == len(sizes),
          "and the sun disc is bright and warm at its predicted centre at "
          "every size -- so the picture composes, it does not just return "
          "bytes", "%d/%d" % (suns, len(sizes)))

    n = 16
    try:
        shades = len(set(bytes(dxt1.pattern_icon(n, n)[i * 3:i * 3 + 3])
                         for i in range(n * n)))
    except Exception as exc:                               # noqa: BLE001
        shades, note = -1, "raised %s" % type(exc).__name__
    else:
        note = "%d distinct colours at %dx%d" % (shades, n, n)
    check(shades >= 20,
          "even the smallest sensible icon has real gradient in it, not a "
          "flat fill", note)


# --- 7. real retail levels ------------------------------------------------

def section_retail(sample):
    print("\n== 7. REAL retail DXT1 levels ==")
    try:
        import vaultpath
        dat = os.path.join(vaultpath.require_dir("dat_study"), "Gw.dat")
    except SystemExit:
        LEDGER.skip("7. retail levels", "no vault/dat_study")
        return
    from archive import Archive
    import atex

    seen = raw0 = decoded = 0
    exact = alpha_ok = 0
    with Archive(dat) as ar:
        for e in ar.entries[:sample]:
            try:
                data = ar.read(e)
            except Exception:                          # noqa: BLE001
                continue
            if data[:4] not in (b"ATEX", b"ATTX"):
                continue
            try:
                a = atex.parse(data)
            except Exception:                          # noqa: BLE001
                continue
            if not a.levels:
                continue
            seen += 1
            lv = a.levels[0]
            if lv.code != 0:
                continue
            raw0 += 1
            if a.fourcc != b"DXT1" or a.width % 4 or a.height % 4:
                continue
            pay = data[lv.offset + atex.RECORD_SIZE:lv.offset + lv.size]
            if len(pay) != (a.width // 4) * (a.height // 4) * 8:
                continue
            exact += 1
            out = dxt1.decode(pay, a.width, a.height)
            decoded += 1
            if len(out) == a.width * a.height * 4 and all(
                    out[i * 4 + 3] == 255
                    for i in range(0, a.width * a.height, 97)):
                alpha_ok += 1

    print("    %d ATEX containers, %d with a RAW level 0, %d DXT1 decoded"
          % (seen, raw0, decoded))
    check(seen > 100, "the sweep found ATEX containers to read",
          "%d" % seen)
    check(decoded > 0 and decoded == exact,
          "every raw DXT1 level whose payload matches its block count "
          "decodes", "%d/%d" % (decoded, exact))
    check(alpha_ok == decoded,
          "and every one comes back fully opaque -- retail's raw DXT1 levels "
          "are all the c0 > c1 form", "%d/%d" % (alpha_ok, decoded))

    # THE SCOPE FINDING, pinned so a future run that changes it is visible.
    # This is the number that bounds what rung M5 can texture.
    if sample >= 6000:
        check(abs(seen - ATEX_SEEN) <= 2 and abs(raw0 - RAW_LEVEL0) <= 2,
              "the raw-level-0 population is %d of %d containers (1.6%%) -- "
              "the rest sit behind ATEX compression codes"
              % (RAW_LEVEL0, ATEX_SEEN), "%d of %d" % (raw0, seen))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="sweep 6,000 archive rows instead of 1,500")
    args = ap.parse_args()
    print("=" * 70)
    print("DXT1 -- encode, decode, and the layout the texture arc settled")
    print("=" * 70)
    for fn in (section_packing, section_spec, section_punchthrough,
               section_level, section_refusals, section_icon,
               section_icon_bounds):
        try:
            fn()
        except Exception as exc:                       # noqa: BLE001
            check(False, "section %s completed" % fn.__name__,
                  "%s: %s" % (type(exc).__name__, exc))
    try:
        section_retail(6000 if args.all else 1500)
    except Exception as exc:                           # noqa: BLE001
        check(False, "section section_retail completed",
              "%s: %s" % (type(exc).__name__, exc))
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
