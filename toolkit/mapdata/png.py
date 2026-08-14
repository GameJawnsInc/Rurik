"""A PNG writer and reader, out of `zlib` and `struct` and nothing else.

`toolkit/` takes no third-party dependencies (`CLAUDE.md`), and rung M5 has to
put decoded textures somewhere a human and a 3D tool can both open. PNG is the
only lossless, universally-read, compressed raster format reachable from the
standard library, so this is ~120 lines rather than a dependency.

    write(path, rgba, width, height)      # bytes, RGBA8, top row first
    data = encode(rgba, width, height)    # the same, in memory
    rgba, w, h = decode(data)             # back again

SCOPE, and it is deliberately small. 8-bit RGBA (colour type 6) only, one
IDAT, filter type 0 on every row. No interlacing, no palettes, no ancillary
chunks, no 16-bit. A texture exporter needs exactly this and every additional
mode is a branch nothing in this repo would exercise.

WHY THE READER EXISTS. Not for the exporter -- nothing here reads PNGs back in
anger. It exists so `test_png.py` can round-trip without PIL, which is the
only way to check the writer on a bare machine: comparing the writer against
itself proves nothing, and comparing it against PIL makes the test depend on
something the module may not. The reader shares no table and no helper with
the writer beyond `zlib` itself -- notably it recomputes the CRC rather than
trusting the one written, so a writer that emits a wrong CRC is caught here
rather than by a viewer three tools downstream.

FILTERS ON READ, NOT ON WRITE. The writer emits filter 0 (None) on every
scanline because a texture is already going through DEFLATE and the filter
gains are not worth the code. The READER implements all five, because a PNG
this repo did not write is allowed to use them and refusing one would be a
reader bug wearing a scope decision's clothes.
"""

import struct
import zlib

MAGIC = b"\x89PNG\r\n\x1a\n"

#: Colour type 6 is truecolour with alpha; bit depth 8. The only pair written.
COLOUR_RGBA = 6
COLOUR_RGB = 2
BIT_DEPTH = 8

_CHANNELS = {COLOUR_RGB: 3, COLOUR_RGBA: 4}


class BadPNG(ValueError):
    """A PNG that cannot be read, with the reason. Never a silent partial."""


# ------------------------------------------------------------------ writing

def _chunk(tag, payload):
    """One PNG chunk: length, tag, payload, CRC over tag+payload."""
    return (struct.pack(">I", len(payload)) + tag + payload
            + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))


def encode(pixels, width, height, colour=COLOUR_RGBA, level=6):
    """PNG bytes for a raw pixel buffer. Top row first, no padding.

    `pixels` is `width * height * channels` bytes. Refuses a buffer whose
    length disagrees -- a texture exporter handing over a short buffer would
    otherwise write a PNG whose last rows are somebody else's memory.
    """
    if colour not in _CHANNELS:
        raise BadPNG(f"colour type {colour} is not one of "
                     f"{sorted(_CHANNELS)}")
    if width <= 0 or height <= 0:
        raise BadPNG(f"{width}x{height} is not a positive image size")
    ch = _CHANNELS[colour]
    want = width * height * ch
    if len(pixels) != want:
        raise BadPNG(f"{len(pixels)} bytes for a {width}x{height} image with "
                     f"{ch} channels; expected {want}")

    stride = width * ch
    raw = bytearray()
    for y in range(height):
        raw.append(0)                     # filter 0 (None), see the docstring
        raw += pixels[y * stride:(y + 1) * stride]

    ihdr = struct.pack(">IIBBBBB", width, height, BIT_DEPTH, colour, 0, 0, 0)
    return (MAGIC
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(raw), level))
            + _chunk(b"IEND", b""))


def write(path, pixels, width, height, colour=COLOUR_RGBA, level=6):
    """`encode` straight to a file. Returns the number of bytes written."""
    blob = encode(pixels, width, height, colour=colour, level=level)
    with open(path, "wb") as fh:
        fh.write(blob)
    return len(blob)


# ------------------------------------------------------------------ reading

def _unfilter(raw, width, height, ch):
    """Undo the per-scanline filters. All five, see the module docstring."""
    stride = width * ch
    out = bytearray(stride * height)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        if pos >= len(raw):
            raise BadPNG(f"pixel data ends at row {y} of {height}")
        ftype = raw[pos]
        pos += 1
        line = bytearray(raw[pos:pos + stride])
        if len(line) != stride:
            raise BadPNG(f"row {y} is {len(line)} bytes, expected {stride}")
        pos += stride
        if ftype == 0:
            pass
        elif ftype == 1:                                          # Sub
            for i in range(ch, stride):
                line[i] = (line[i] + line[i - ch]) & 0xFF
        elif ftype == 2:                                          # Up
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ftype == 3:                                          # Average
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ftype == 4:                                          # Paeth
            for i in range(stride):
                a = line[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pred = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pred) & 0xFF
        else:
            raise BadPNG(f"row {y} uses filter type {ftype}, which is not "
                         f"one of 0..4")
        out[y * stride:(y + 1) * stride] = line
        prev = line
    return bytes(out)


def decode(data):
    """`(pixels, width, height, colour)` from PNG bytes.

    Verifies the signature and EVERY chunk's CRC -- recomputed here rather
    than trusted, which is what lets this catch a writer that emits a bad one.
    """
    if not data.startswith(MAGIC):
        raise BadPNG("not a PNG (signature does not match)")
    pos = len(MAGIC)
    width = height = colour = None
    idat = bytearray()
    seen_end = False
    while pos + 8 <= len(data):
        (length,) = struct.unpack_from(">I", data, pos)
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        if len(body) != length:
            raise BadPNG(f"chunk {tag!r} claims {length} bytes, "
                         f"{len(body)} present")
        # The CRC's own four bytes must be checked for BEFORE unpacking them.
        # Without this a truncated file leaves as struct.error rather than
        # BadPNG, which reads to a caller as a crash rather than as the
        # refusal it is -- the failure mode this repo keeps re-finding.
        if pos + 12 + length > len(data):
            raise BadPNG(f"chunk {tag!r} is truncated: its CRC runs past the "
                         f"end of the file")
        (stored,) = struct.unpack_from(">I", data, pos + 8 + length)
        actual = zlib.crc32(tag + body) & 0xFFFFFFFF
        if stored != actual:
            raise BadPNG(f"chunk {tag!r} CRC 0x{stored:08X} != "
                         f"computed 0x{actual:08X}")
        pos += 12 + length
        if tag == b"IHDR":
            width, height, depth, colour, comp, filt, inter = \
                struct.unpack(">IIBBBBB", body)
            if depth != BIT_DEPTH:
                raise BadPNG(f"bit depth {depth}; this reader is 8-bit only")
            if colour not in _CHANNELS:
                raise BadPNG(f"colour type {colour}; this reader handles "
                             f"{sorted(_CHANNELS)}")
            if comp != 0 or filt != 0:
                raise BadPNG(f"compression {comp}/filter {filt} are not the "
                             f"only defined values (0/0)")
            if inter != 0:
                raise BadPNG("interlaced PNGs are not supported")
        elif tag == b"IDAT":
            idat += body
        elif tag == b"IEND":
            seen_end = True
            break
    if width is None:
        raise BadPNG("no IHDR chunk")
    if not seen_end:
        raise BadPNG("no IEND chunk; the file is truncated")
    if not idat:
        raise BadPNG("no IDAT chunk")
    raw = zlib.decompress(bytes(idat))
    return _unfilter(raw, width, height, _CHANNELS[colour]), width, height, \
        colour


def read(path):
    """`decode` from a file."""
    with open(path, "rb") as fh:
        return decode(fh.read())
