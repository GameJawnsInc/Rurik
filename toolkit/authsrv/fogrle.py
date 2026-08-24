#!/usr/bin/env python3
r"""The fog-of-war RLE stream: decode it the way the client does, and build one.

Python 3 standard library only -- this is on the server path.

WHAT THIS IS. The world map (M) sizes its texture from `charContext + 0x5B4`,
which only the exploration-init pair writes: GAME_SMSG `0x008B`
(MAP_EXPLORATION_INIT_BEGIN: dims.x, dims.y, byteCount) followed by `0x008A`
(MAP_EXPLORATION_INIT_DATA: dwords of an RLE stream). A server that never sends
the pair leaves `mapDims` at 0 and the first M press kills the client on
`GmMapView.cpp(1731) worldMapDims.x == mapDims.x * DXT_BLOCK_SIZE` -- the
matched-pair proof is `studies/minimap/FINDINGS.md` §6f.2, and the operational
history is the RUNBOOK failure table's `key:m` row. This module is the durable
half of that fix: it builds a synthetic all-fogged (or all-revealed) stream so
`authsrv.py` can send the pair at map load without replaying ArenaNet's bytes.

THE FORMAT, read out of the client's own expander rather than reasoned. The
expander is `0x00817550..0x008176F7` on build 38797 (rung S8 named it; the
per-instruction walk for THIS module is studies/minimap/FINDINGS.md §6i), and
every semantic below carries the VA that pins it:

  * `dims.x % 32 == 0` is asserted (`ChCliApi:77`, `test byte [esi+0x50], 0x1f`
    at 0x00817564). The expander then stores `mapDims` (+0x5B4/+0x5B8), sizes
    `mapBits` to `(x*y) >> 5` dwords and MEMSETS IT TO ZERO (0x008175BB) -- so
    every block not reached by a run is fogged, and an empty stream is a valid
    all-fogged one.
  * The stream is a chain of BANDS of 16 block-rows each (`shr eax, 4` on
    dims.y at 0x008175E9). Each band is a little-endian `u16` byte-length
    followed by that many run bytes; the next band's header starts right after
    (offset += 2 + len at 0x00817600..03, clamped to the declared total at
    0x0081760C). The loop continues only while the next header FITS
    (`lea eax, [ecx+2]; cmp eax, edx; jbe` at 0x008176E0..EB), so a chain must
    physically contain every band header it declares bits for.
  * A RUN is a byte count of BITS: bytes are summed, `0xFF` meaning "add 255
    and keep reading" (0x00817679..84). Runs ALTERNATE colour, zero-length
    runs included (`xor [ebp-0xc], 1` at 0x008176C8). Bits are emitted
    LSB-first into a 32-bit accumulator and written only on a full-dword flush
    (0x008176A7); a band's trailing PARTIAL dword is dropped, never written --
    which is why §6f.4 warns off the band tail. dims.x % 32 == 0 makes a
    band's capacity (dims.x * 16 bits) a whole number of dwords, so a stream
    that covers a band exactly loses nothing.

THE STARTING COLOUR IS CONTESTED, and this module says so rather than picking
quietly (studies/minimap/FINDINGS.md §6i has the full record). The instruction
trace reads FOG-first: `mov [ebp-0xc], edx` with edx == 0 at 0x00817655
initialises the colour, and the emit's `neg/sbb/and/or` (0x00817696..9C) sets
bits only when it is non-zero -- raw bytes re-read from the exe, not just the
disassembler. But three OBSERVED client behaviours over ArenaNet's own
replayed payload fit ONLY reveal-first with a straight row-major mapping, out
of the four (colour x mirror) candidate models: block (30, 24) decodes SET and
(26, 22) CLEAR -- both proven by the §6f.4 mark runs, 0 px and 1,059 px --
and the 1,059 px is one-or-few blocks' worth, which fits the reveal-first
neighbourhood (5 of 9 clear) and not the fog-first one. §6f.2's "large
revealed region" on the M press agrees (947 of 1,024 band-1 bits, against 45
under fog-first). Behaviour outranks a one-reader static trace, so
`FIRST_COLOUR = 1` below -- and the arbiter is one screenshot: if a
`--fog-reveal` run ever opens a fully FOGGED map, the static reading was
right and this constant flips to 0 (which also swaps `encode_uniform`'s
revealed shape to lead with a zero-length run). The DEFAULT all-fogged stream
is identical under every model and does not wait on the answer. (One number
from §6f.4 reproduces under NO model: "68 of the footprint's blocks are
clear" -- reveal-first gives 21 drop-included, fog-first 192. Its two
per-block claims are client-corroborated and reproduce; the 68 was
decode-derived only, and should not be quoted until re-derived.)

`decode()` reproduces all of the above, drop included, because a faithful
decoder is the only referee `encode_uniform()` can be tested against that is
not this module agreeing with itself -- `test_fogrle.py` §1 runs it over
ArenaNet's own replayed payload (probes.FOG_INIT_PAYLOAD) and checks the band
chain and the two behaviourally-corroborated blocks of §6f.4.

WHAT THIS MODULE DOES NOT KNOW: the dims. They are CONTINENT-SPECIFIC
(`studies/minimap/FINDINGS.md` §4.2: the grid is continent-absolute), OBSERVED
on the wire only for continent 1 -- (64, 128), 8 of 8 live captures -- and no
formula deriving them from the atlas tables has survived contact with the data
(continent 3's footprint extent alone refutes the obvious one; §6i). So dims
live in `content/fog.toml` as provenanced rows, and a map whose continent has
no row gets NO fog init and a loud log, never a guess.
"""

import struct

BAND_ROWS = 16          # block-rows per band: shr eax, 4 at 0x008175E9
DWORDS_PER_MSG = 64     # 0x008A's array32 capacity (schema GAME_SMSG_0138);
                        # the handler ACCUMULATES across messages
                        # (accumMapInitOffset, 0x00811AA0), so a long stream is
                        # sent as several 0x008A in order.
FIRST_COLOUR = 1        # CONTESTED -- see the docstring. 1 = the behaviour-
                        # corroborated model (reveal-first); the static trace
                        # reads 0. All-fogged streams do not depend on it.


class FogError(ValueError):
    """A dims or stream we refuse to build or read. Refuse-to-guess, not a warning."""


def check_dims(dims):
    """The constraints the CLIENT enforces or assumes, refused at the desk instead.

    x % 32 is ArenaNet's own assert (ChCliApi:77). y % 16 is ours: the band loop
    floors dims.y/16, so a non-multiple leaves rows no stream can ever address --
    a dims we have no evidence the client ever sees (every observed value is
    (64, 128)), so we refuse it rather than define behaviour for it.
    """
    x, y = dims
    if not (isinstance(x, int) and isinstance(y, int)) or x <= 0 or y <= 0:
        raise FogError(f"fog dims must be positive ints, got {dims!r}")
    if x % 32:
        raise FogError(
            f"dims.x = {x} is not a multiple of 32 -- the client asserts this "
            f"(ChCliApi:77, 0x00817564) and would die on receipt.")
    if y % BAND_ROWS:
        raise FogError(
            f"dims.y = {y} is not a multiple of {BAND_ROWS} -- the band loop "
            f"floors y/{BAND_ROWS}, stranding the remainder rows. No observed "
            f"dims does this; refusing rather than guessing what it means.")
    return x, y


def _run_bytes(nbits):
    """One run of `nbits` bits: 0xFF-continuation bytes summing to nbits.

    Every byte before the last is 0xFF ("add 255, keep reading"); any byte
    below 0xFF terminates, so a multiple of 255 needs its explicit 0x00
    terminator. nbits == 0 is the valid zero-length run (a bare 0x00).
    """
    return b"\xff" * (nbits // 255) + bytes([nbits % 255])


def encode_uniform(dims, revealed=False):
    """The RLE stream for a uniformly fogged (default) or revealed grid.

    Fogged is the trivial chain -- every band an empty u16 header, exactly the
    shape 7 of ArenaNet's own 8 bands already have (§6f.2's replayed payload,
    band lengths (0, 22, 0, 0, 0, 0, 0, 0)) -- and it means all-fog under
    EVERY candidate model, contest or no contest. Revealed encodes one run
    covering the band's full dims.x * 16 bits in the FIRST_COLOUR slot: under
    the behaviour model (FIRST_COLOUR == 1) that is the bare run; under the
    static model it would need a zero-length fog run in front, which is what
    flipping FIRST_COLOUR selects. Either way the run is a whole number of
    dwords (dims.x % 32 == 0), so the client's partial-dword drop never bites.
    """
    x, y = check_dims(dims)
    out = bytearray()
    if not revealed:
        band_data = b""
    else:
        lead = b"" if FIRST_COLOUR else b"\x00"   # a zero-length fogged run
        band_data = lead + _run_bytes(x * BAND_ROWS)
    for _ in range(y // BAND_ROWS):
        out += struct.pack("<H", len(band_data)) + band_data
    return bytes(out)


def decode(data, dims, first_colour=None):
    """The client's expander, reproduced: bytes -> bytearray of x*y block bits.

    Faithful to 0x00817550 including its edges: band lengths clamped to the
    declared total, the loop stopping when the next header no longer fits, a
    run truncated mid-continuation still emitting what it summed, writes
    stopping at band capacity, and the trailing partial dword of a band being
    DROPPED (bits accumulated but never flushed do not land). `data` must be
    exactly the declared byteCount -- the caller trims padding first, the way
    the client trims with `min(4*count, declared - offset)`. `first_colour`
    defaults to the module's FIRST_COLOUR; pass 0 to decode under the static
    reading (the CONTEST in the docstring).
    """
    x, y = check_dims(dims)
    bits = bytearray(x * y)
    total = len(data)
    if total < 2:                      # cmp edx, 2; jb -- an empty stream is all-fog
        return bits
    off = 0
    for band in range(y // BAND_ROWS):
        hdr = struct.unpack_from("<H", data, off)[0]
        start = off + 2
        end = min(start + hdr, total)  # the clamp at 0x0081760C
        off = end
        base = x * BAND_ROWS * band    # dword-aligned: x % 32 == 0
        cap = x * BAND_ROWS
        emitted = 0                    # bits emitted this band, flushed or not
        colour = FIRST_COLOUR if first_colour is None else first_colour
        p = start
        while p < end:
            run = 0
            while p < end:
                b = data[p]
                p += 1
                run += b
                if b != 0xFF:
                    break
            if colour:
                for i in range(emitted, min(emitted + run, cap)):
                    bits[base + i] = 1
            emitted += run
            colour ^= 1
        # the partial-dword drop: bits past the last full dword were only ever
        # in the accumulator (0x008176A7 writes on flush alone)
        flushed = (min(emitted, cap) // 32) * 32
        for i in range(flushed, min(emitted, cap)):
            bits[base + i] = 0
        if off + 2 > total:            # next header does not fit: 0x008176E9
            break
    return bits


def payload_dwords(data):
    """The 0x008A messages for a stream: a list of <=64-dword little-endian chunks.

    The dword packing is OBSERVED, not chosen: probes.FOG_INIT_PAYLOAD[0] ==
    0x00160000, whose LE bytes are exactly the replayed stream's first four --
    band-0 header 0x0000 then band-1 header 0x0016 == 22. The tail pads with
    zeros; the client copies `min(4*count, declared - offset)`, so padding
    beyond the declared byteCount never lands (ArenaNet's own tail padding was
    0xCC bytes, equally ignored).
    """
    padded = data + b"\x00" * (-len(data) % 4)
    dwords = [struct.unpack_from("<I", padded, i)[0] for i in range(0, len(padded), 4)]
    return [dwords[i:i + DWORDS_PER_MSG]
            for i in range(0, len(dwords), DWORDS_PER_MSG)] or [[]]
