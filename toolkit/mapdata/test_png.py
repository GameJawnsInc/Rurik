#!/usr/bin/env python3
"""Check the stdlib PNG codec that rung M5's texture export writes through.

    python toolkit/mapdata/test_png.py

NO VAULT, NO ARCHIVE, NO CLIENT, and no PIL -- every image here is built in
this file out of `bytes`, which is what lets the whole run happen on a bare
machine. That is not a convenience: `png.py` exists precisely so the texture
path takes no third-party dependency, so a test that needed one to check it
would defeat the module's only reason to exist.

WHAT IS AND IS NOT EVIDENCE HERE, because this is a codec and the trap is the
usual one. `decode(encode(x)) == x` is the WEAK half: a pair of functions that
agree with each other prove they are inverses and nothing about whether either
one is PNG. Two things are done about that.

  * **Section 2 reads the bytes the writer emitted with a walker written HERE**
    out of `struct` and `zlib` -- signature, chunk order, IHDR fields, the CRC
    recomputed independently -- so the file is checked against the FORMAT
    rather than against its own reader.
  * **Section 3 feeds the reader images the writer cannot produce.** The writer
    only ever emits filter 0; the reader claims all five. So the test BUILDS a
    PNG for each filter type by hand and requires the reader to recover the
    same pixels from all five, with filter 5 refused. Without this, four of the
    reader's five branches are dead code that no run ever enters.

THE SABOTAGES THAT SHAPED THE FLOOR. Each is a one-edit copy of `png.py`
that the test was then run against; the counts are MEASURED 2026-08-13, not
predicted -- an earlier draft of this table carried guessed numbers and four
of the six were wrong.

    sabotage                                    checks reddened
    writer emits a zero CRC                      8
    writer forgets the per-row filter byte       4
    writer swaps width/height in IHDR            2   (see below)
    reader trusts the stored CRC                 1   (section 4's tamper)
    reader's Paeth predictor uses `b` for `c`    2   (section 3, filter 4)
    encode() drops its length check              2   (section 5)

Two rows are worth reading rather than counting.

**The Paeth row** is the argument for section 3: a wrong predictor is
invisible to every round trip in this file, because the writer never emits
filter 4. Only the hand-built images reach it.

**The width/height swap reddens only 2**, and the reason is not that the
check is weak -- it is that a transposed IHDR gives the reader the wrong
stride, so it REFUSES, and section 1 aborts into a single named failure
rather than reporting each size separately. That is `main()`'s guard doing
its job (a dead section becomes a named check, never a bare traceback), and
it means a low count here is not evidence of low coverage. The number is
reported as measured rather than tuned, because tuning it would mean weakening
the reader.

**The CRC row is the sharpest**: exactly ONE check stands between this codec
and a reader that parses without verifying, and it is section 4's tamper.

REFUSALS ARE CHECKED AS `BadPNG`, NOT AS "raises". A truncated file left as
`struct.error` in the first version of `png.py` -- caught by this file's
section 5 -- and the difference matters to a caller: `BadPNG` is a refusal it
can act on, an unhandled `struct.error` reads as a crash in the exporter. The
same shape `vaultpath.require_dir` set for `test_stripbuild.py`.
"""

import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks                                                    # noqa: E402
import png                                                       # noqa: E402

# MEASURED from a green run, 2026-08-13. Every check is synthetic, so this is
# the score on ANY machine -- there is no vault-less variant to declare.
LEDGER = checks.Ledger("png codec", floor=45)
check = checks.adopt(LEDGER)


def ramp(width, height, channels):
    """A deterministic image with structure in both axes.

    Not random and not flat: a constant image survives a transposed IHDR and
    several filter bugs, and random data makes a failure hard to read.
    """
    return bytes(((x * 37 + y * 101 + c * 7) & 0xFF)
                 for y in range(height) for x in range(width)
                 for c in range(channels))


# --- 1. round trips -------------------------------------------------------

def section_roundtrip():
    print("\n== 1. round trips (the WEAK half -- see the docstring) ==")
    for w, h in ((1, 1), (7, 5), (16, 16), (64, 3), (3, 64)):
        px = ramp(w, h, 4)
        back, bw, bh, colour = png.decode(png.encode(px, w, h))
        check(back == px and (bw, bh) == (w, h)
              and colour == png.COLOUR_RGBA,
              "RGBA %dx%d round-trips byte-identically" % (w, h),
              "%dx%d colour=%s" % (bw, bh, colour))

    px = ramp(9, 4, 3)
    back, bw, bh, colour = png.decode(png.encode(px, 9, 4,
                                                 colour=png.COLOUR_RGB))
    check(back == px and (bw, bh) == (9, 4) and colour == png.COLOUR_RGB,
          "RGB (colour type 2) round-trips too, and reports its own type")

    # An ASYMMETRIC image, because w==h hides a transposed IHDR and every
    # size above except the two deliberate ones is square or nearly so.
    px = ramp(13, 5, 4)
    back, bw, bh, _c = png.decode(png.encode(px, 13, 5))
    check(back == px and (bw, bh) == (13, 5),
          "a 13x5 image comes back 13x5 -- a transposed IHDR would not",
          "%dx%d" % (bw, bh))

    # Compression level must not change the PIXELS. A writer that fed the
    # level through to the wrong place would still round-trip at its default.
    px = ramp(20, 20, 4)
    outs = [png.decode(png.encode(px, 20, 20, level=lv))[0] for lv in (0, 1, 9)]
    check(all(o == px for o in outs),
          "levels 0, 1 and 9 all round-trip to the same pixels")
    sizes = [len(png.encode(px, 20, 20, level=lv)) for lv in (0, 9)]
    check(sizes[0] > sizes[1],
          "and level 0 really is bigger than level 9 -- the level reaches "
          "zlib rather than being accepted and dropped",
          "%d vs %d bytes" % tuple(sizes))


# --- 2. the emitted bytes, read by a walker written HERE -------------------

def section_format():
    print("\n== 2. the FORMAT, checked without png.decode ==")
    w, h = 11, 6
    blob = png.encode(ramp(w, h, 4), w, h)

    check(blob[:8] == b"\x89PNG\r\n\x1a\x1a"[:8].replace(b"\x1a\x1a", b"\x1a\n")
          or blob[:8] == bytes([137, 80, 78, 71, 13, 10, 26, 10]),
          "the file opens with the PNG signature",
          repr(blob[:8]))

    # Walk the chunks out of struct, recomputing every CRC. Shares nothing
    # with png.decode.
    pos, order, ihdr, idat = 8, [], None, bytearray()
    while pos + 12 <= len(blob):
        (length,) = struct.unpack_from(">I", blob, pos)
        tag = blob[pos + 4:pos + 8]
        body = blob[pos + 8:pos + 8 + length]
        (stored,) = struct.unpack_from(">I", blob, pos + 8 + length)
        check(stored == (zlib.crc32(tag + body) & 0xFFFFFFFF),
              "chunk %r carries a correct CRC (recomputed here)"
              % tag.decode("ascii", "replace"))
        order.append(tag)
        if tag == b"IHDR":
            ihdr = body
        elif tag == b"IDAT":
            idat += body
        pos += 12 + length
    check(pos == len(blob),
          "the chunk walk consumes the file to its exact final byte",
          "%d of %d" % (pos, len(blob)))
    check(order == [b"IHDR", b"IDAT", b"IEND"],
          "chunks are IHDR, IDAT, IEND in that order",
          repr([t.decode() for t in order]))

    gw, gh, depth, colour, comp, filt, inter = struct.unpack(">IIBBBBB", ihdr)
    check((gw, gh) == (w, h),
          "IHDR names the size we asked for, width FIRST",
          "%dx%d" % (gw, gh))
    check(depth == 8 and colour == 6,
          "IHDR says 8-bit truecolour-with-alpha", "%d/%d" % (depth, colour))
    check((comp, filt, inter) == (0, 0, 0),
          "IHDR's compression, filter and interlace are the defined zeros")

    raw = zlib.decompress(bytes(idat))
    check(len(raw) == h * (1 + w * 4),
          "the decompressed stream is exactly h*(1 + w*4) bytes -- one filter "
          "byte per row and no padding",
          "%d, expected %d" % (len(raw), h * (1 + w * 4)))
    filters = {raw[y * (1 + w * 4)] for y in range(h)}
    check(filters == {0},
          "every scanline uses filter 0, which is what the writer claims",
          repr(sorted(filters)))


# --- 3. the reader's other four filters, which the writer never emits ------

def section_filters():
    print("\n== 3. all five filters, on images the WRITER cannot produce ==")
    w, h, ch = 9, 6, 4
    px = ramp(w, h, ch)
    stride = w * ch

    def build(filter_of_row):
        """A PNG carrying `px`, filtered per row by the caller's choice."""
        raw = bytearray()
        prev = bytearray(stride)
        for y in range(h):
            line = bytearray(px[y * stride:(y + 1) * stride])
            ft = filter_of_row(y)
            enc = bytearray(stride)
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                if ft == 0:
                    enc[i] = line[i]
                elif ft == 1:
                    enc[i] = (line[i] - a) & 0xFF
                elif ft == 2:
                    enc[i] = (line[i] - b) & 0xFF
                elif ft == 3:
                    enc[i] = (line[i] - ((a + b) >> 1)) & 0xFF
                elif ft == 4:
                    p = a + b - c
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                    pred = a if (pa <= pb and pa <= pc) else (
                        b if pb <= pc else c)
                    enc[i] = (line[i] - pred) & 0xFF
            raw.append(ft)
            raw += enc
            prev = line
        ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
        return (png.MAGIC + png._chunk(b"IHDR", ihdr)
                + png._chunk(b"IDAT", zlib.compress(bytes(raw)))
                + png._chunk(b"IEND", b""))

    for ft in range(5):
        got, gw, gh, _c = png.decode(build(lambda _y, f=ft: f))
        check(got == px and (gw, gh) == (w, h),
              "filter %d decodes to the original pixels -- a branch the "
              "writer never exercises" % ft,
              "%d bytes" % len(got))

    # MIXED filters down one image, which is what a real encoder emits and
    # what catches a reader that keeps the wrong `prev` row.
    got, _gw, _gh, _c = png.decode(build(lambda y: y % 5))
    check(got == px,
          "a single image using a DIFFERENT filter on each row decodes -- "
          "this is what catches a stale `prev` scanline")

    # And an undefined filter must be refused rather than guessed at.
    try:
        png.decode(build(lambda _y: 5))
        check(False, "filter type 5 is refused")
    except png.BadPNG as exc:
        check("filter type 5" in str(exc),
              "filter type 5 is refused, and the message names it",
              str(exc)[:52])


# --- 4. refusals, each as BadPNG ------------------------------------------

def section_refusals():
    print("\n== 4. refusals -- BadPNG, not a traceback ==")
    w, h = 8, 4
    good = png.encode(ramp(w, h, 4), w, h)

    def refuses(fn, label, want=None):
        try:
            fn()
        except png.BadPNG as exc:
            ok = want is None or want in str(exc)
            check(ok, "refused: %s" % label, str(exc)[:56])
            return
        except Exception as exc:                       # noqa: BLE001
            check(False, "refused: %s" % label,
                  "raised %s, not BadPNG" % type(exc).__name__)
            return
        check(False, "refused: %s" % label, "no refusal")

    refuses(lambda: png.decode(b"not a png at all"), "a file with no "
            "signature", "not a PNG")
    # Truncation reaches TWO different guards depending on where the cut
    # lands, and both are exercised on purpose. A cut at the very end leaves
    # a chunk header intact and is caught by the CRC-bounds check; a cut in
    # the middle of a chunk body is caught by the body-length check first.
    # Only the first has a determinate message, so only the first asserts one
    # -- pinning a specific wording on the second would be a test of the
    # phrasing rather than of the refusal.
    refuses(lambda: png.decode(good[:-1]), "a file truncated by one byte",
            "truncated")
    refuses(lambda: png.decode(good[:20]), "a file cut mid-chunk")
    refuses(lambda: png.decode(png.MAGIC), "a signature with no IHDR",
            "no IHDR")

    # THE CRC TAMPER. This is the check that distinguishes a reader which
    # verifies from one which merely parses -- and a reader that trusts the
    # stored CRC reddens here and NOWHERE else in this file.
    for off in (20, 40):
        bad = bytearray(good)
        bad[off] ^= 0xFF
        refuses(lambda b=bytes(bad): png.decode(b),
                "one flipped byte at offset %d" % off)

    # An IEND that never arrives: every chunk is individually well formed, so
    # only the end-of-file rule catches it.
    ihdr = struct.pack(">IIBBBBB", 4, 4, 8, 6, 0, 0, 0)
    headless = png.MAGIC + png._chunk(b"IHDR", ihdr) + png._chunk(
        b"IDAT", zlib.compress(b"\0" * (4 * (1 + 16))))
    refuses(lambda: png.decode(headless),
            "a stream with no IEND, every chunk otherwise valid", "IEND")

    # Modes this reader does not implement must REFUSE rather than produce
    # wrong pixels quietly.
    for field, value, label in ((2, 16, "16-bit depth"),
                                (3, 3, "a palette colour type"),
                                (6, 1, "an interlaced image")):
        body = bytearray(struct.pack(">IIBBBBB", 4, 4, 8, 6, 0, 0, 0))
        body[field + 6] = value
        blob = png.MAGIC + png._chunk(b"IHDR", bytes(body)) + png._chunk(
            b"IDAT", zlib.compress(b"\0" * 20)) + png._chunk(b"IEND", b"")
        refuses(lambda b=blob: png.decode(b), label)


# --- 5. the writer's own guards -------------------------------------------

def section_writer_guards():
    print("\n== 5. what the WRITER refuses ==")

    def refuses(fn, label):
        try:
            fn()
        except png.BadPNG as exc:
            check(True, "refused: %s" % label, str(exc)[:56])
            return
        except Exception as exc:                       # noqa: BLE001
            check(False, "refused: %s" % label,
                  "raised %s, not BadPNG" % type(exc).__name__)
            return
        check(False, "refused: %s" % label, "no refusal")

    # A SHORT buffer is the one that matters: without the length check the
    # writer emits a PNG whose last rows are whatever followed the buffer.
    refuses(lambda: png.encode(b"\0" * 15, 2, 2), "16 bytes wanted, 15 given")
    refuses(lambda: png.encode(b"\0" * 17, 2, 2), "16 bytes wanted, 17 given")
    refuses(lambda: png.encode(b"", 0, 4), "a zero width")
    refuses(lambda: png.encode(b"", 4, 0), "a zero height")
    refuses(lambda: png.encode(b"\0" * 48, 4, 4, colour=3),
            "a colour type this writer does not implement")

    # The POSITIVE control: the exact-length buffer is still accepted. A
    # guard that refused everything would pass every line above while making
    # the module useless.
    blob = png.encode(b"\x7f" * 16, 2, 2)
    got, gw, gh, _c = png.decode(blob)
    check(got == b"\x7f" * 16 and (gw, gh) == (2, 2),
          "and an exactly-sized buffer is still written and read back")

    # write() to a real file, since encode() is what every check above used.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "t.png")
        n = png.write(path, ramp(5, 5, 4), 5, 5)
        check(n == os.path.getsize(path) > 0,
              "write() reports the byte count it actually wrote",
              "%d" % n)
        got, gw, gh, _c = png.read(path)
        check(got == ramp(5, 5, 4) and (gw, gh) == (5, 5),
              "and read() recovers it from disk")


def main():
    print("=" * 70)
    print("PNG CODEC -- the texture export's only image writer")
    print("=" * 70)
    for fn in (section_roundtrip, section_format, section_filters,
               section_refusals, section_writer_guards):
        try:
            fn()
        except Exception as exc:                       # noqa: BLE001
            # A section that dies must become a NAMED failing check, not a
            # bare traceback with no verdict and no floor line.
            check(False, "section %s completed" % fn.__name__,
                  "%s: %s" % (type(exc).__name__, exc))
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
