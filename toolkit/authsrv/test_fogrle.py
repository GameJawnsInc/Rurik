"""The fog-init pair's synthetic stream, refereed by ArenaNet's own payload.

`fogrle.py` exists so the server can send GAME_SMSG 0x008B + 0x008A at map load
and make the world map openable (without the pair, M kills the client on
GmMapView.cpp(1731) -- studies/minimap/FINDINGS.md 6f.2). A hand-rolled RLE
stream failing is the single most likely way that fix fails for a reason that
has nothing to do with the opcodes, so section 1 is the referee that is not
this module agreeing with itself: the decoder runs over the VERBATIM ArenaNet
payload the probes replay (capture 20260807T143055) and must reproduce the
band accounting rung S8 closed 8/8 AND the two block states the client itself
corroborated behaviourally in FINDINGS 6f.4 (marking (30,24) changed 0 px --
already set; marking (26,22) revealed 1,059 px -- clear). The colour-start
CONTEST (fogrle.py's docstring, FINDINGS 6i) is pinned from both sides: the
behaviour model satisfies both fixtures, the static rival inverts both.

The encoder's own properties follow: the all-fogged default is byte-trivial
(every band an empty header) and means all-fog under EITHER contested model;
the all-revealed stream covers each band exactly, which dims.x % 32 == 0
makes a whole number of dwords, so the client's partial-dword drop cannot
bite. Section 7 packs both messages through the real codec so the wire shape
is checked, not assumed; section 8 joins through `authsrv.fog_init_for_map`
and the content rows, including the refusals for a continent with no observed
dims (refuse-to-guess: a wrong pair is the same crash the pair prevents).

    python toolkit/authsrv/test_fogrle.py
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "schema"))

import checks       # noqa: E402
import fogrle       # noqa: E402
import probes       # noqa: E402
from codec import Codec  # noqa: E402

SCHEMA = os.path.join(HERE, "..", "..", "schema", "messages.json")
DIMS = probes.FOG_INIT_DIMS                    # (64, 128), continent 1


def replayed_stream():
    """The verbatim ArenaNet stream, trimmed to its declared byte count."""
    raw = b"".join(struct.pack("<I", d) for d in probes.FOG_INIT_PAYLOAD)
    return raw[:probes.FOG_INIT_BYTES]


def main():
    led = checks.Ledger("fogrle", floor=41)   # set from the first green run
    data = replayed_stream()
    x, y = DIMS

    # --- 1. the referee: ArenaNet's own payload through our decoder -------
    off, chain = 0, []
    while off + 2 <= len(data):
        h = struct.unpack_from("<H", data, off)[0]
        chain.append(h)
        off += 2 + h
    led.ok(tuple(chain) == (0, 22, 0, 0, 0, 0, 0, 0),
           "band chain is (0, 22, 0, 0, 0, 0, 0, 0)", f"got {tuple(chain)}")
    led.ok(off == probes.FOG_INIT_BYTES,
           "the chain closes at EXACTLY the declared 38 bytes", f"got {off}")

    bits = fogrle.decode(data, DIMS)

    def blk(b, bx, by):
        return b[by * x + bx]

    led.ok(blk(bits, 30, 24) == 1,
           "block (30,24) decodes SET -- the client proved it set "
           "(FINDINGS 6f.4: marking it changed 0 of 2,013,440 px)")
    led.ok(blk(bits, 26, 22) == 0,
           "block (26,22) decodes CLEAR -- the client proved it clear "
           "(FINDINGS 6f.4: marking it revealed 1,059 px)")
    led.ok(sum(bits) == 947,
           "947 bits set: a mostly-revealed band 1, matching 6f.2's "
           "'large revealed region' on the M press", f"got {sum(bits)}")

    # The CONTEST, pinned from the rival's side: the static instruction trace
    # reads colour-start 0, and under it BOTH client-corroborated fixtures
    # invert. If FIRST_COLOUR is ever flipped without new evidence, the two
    # checks above go red; if the static reading somehow wins (a --fog-reveal
    # run opening fully fogged), these two document what must flip with it.
    rival = fogrle.decode(data, DIMS, first_colour=0)
    led.ok(blk(rival, 30, 24) == 0 and blk(rival, 26, 22) == 1,
           "the static rival (first_colour=0) inverts both fixtures -- the "
           "models are distinguishable and the data chose")

    # Band-1 run accounting, independent of colour: byte-sum with 0xFF
    # continuation over the 22 declared bytes.
    p, end, runs = 4, 26, []
    while p < end:
        r = 0
        while p < end:
            b = data[p]
            p += 1
            r += b
            if b != 0xFF:
                break
        runs.append(r)
    led.ok(sum(runs) == 1004,
           "band 1's runs sum to 1,004 bits of its 1,024 -- 6f.4's own "
           "number, the 20-bit tail uncovered", f"got {sum(runs)}")
    led.ok(len(runs) == 21, "21 runs in band 1", f"got {len(runs)}")

    # ...and the partial-dword drop: 1,004 emitted bits flush only to 992, so
    # bits 992..1003 of the band never land even where runs said 1.
    tail = [bits[(16 + 15) * x + bx] for bx in range(32, 44)]
    led.ok(all(v == 0 for v in tail),
           "band-1 bits 992..1003 are dropped (the client writes on full-dword "
           "flush alone, 0x008176A7)")

    # --- 2. the all-fogged default: what the server now sends at load -----
    fogged = fogrle.encode_uniform(DIMS)
    led.ok(fogged == b"\x00\x00" * (y // 16),
           "all-fogged is 8 empty band headers, 16 bytes",
           f"{len(fogged)}B")
    led.ok(set(fogrle.decode(fogged, DIMS)) == {0},
           "it decodes all-fog under the behaviour model")
    led.ok(set(fogrle.decode(fogged, DIMS, first_colour=0)) == {0},
           "...and under the static rival -- the DEFAULT does not wait on the "
           "contest")

    # --- 3. the all-revealed stream (--fog-reveal) ------------------------
    revealed = fogrle.encode_uniform(DIMS, revealed=True)
    led.ok(set(fogrle.decode(revealed, DIMS)) == {1},
           "all-revealed decodes all-one under the behaviour model",
           f"{len(revealed)}B")
    band = fogrle._run_bytes(x * 16)
    led.ok(revealed == (struct.pack("<H", len(band)) + band) * (y // 16),
           "each band is one run covering its full capacity exactly")
    led.ok((x * 16) % 32 == 0,
           "band capacity is a whole number of dwords, so the flush drop "
           "cannot eat the tail")

    # --- 4. run-length bytes: additive 0xFF continuation ------------------
    for n, want in ((0, b"\x00"), (254, b"\xfe"), (255, b"\xff\x00"),
                    (1024, b"\xff\xff\xff\xff\x04")):
        led.ok(fogrle._run_bytes(n) == want,
               f"_run_bytes({n}) == {want.hex()}",
               f"got {fogrle._run_bytes(n).hex()}")
    led.ok(all(b == 0xFF for b in fogrle._run_bytes(5 * 255)[:-1])
           and fogrle._run_bytes(5 * 255)[-1] == 0,
           "a multiple of 255 keeps its explicit terminator byte")

    # --- 5. refusals: the constraints the client would die on -------------
    for bad in ((63, 128), (64, 120), (0, 16), (64, 0), (-32, 16)):
        try:
            fogrle.check_dims(bad)
            led.ok(False, f"dims {bad} refused")
        except fogrle.FogError:
            led.ok(True, f"dims {bad} refused")

    # --- 6. dword packing: OBSERVED against the replayed payload ----------
    chunks = fogrle.payload_dwords(data)
    led.ok(len(chunks) == 1 and len(chunks[0]) == 10,
           "the 38-byte stream packs to one 10-dword message")
    led.ok(chunks[0][:9] == probes.FOG_INIT_PAYLOAD[:9],
           "9 of 10 dwords match ArenaNet's replay bit for bit")
    led.ok(chunks[0][9] == probes.FOG_INIT_PAYLOAD[9] & 0xFFFF,
           "dword 10 matches below the declared count -- the 0xCCCC beyond it "
           "is ArenaNet's padding, ours is zero, and the client copies "
           "min(4*count, declared-offset) so neither lands")
    big = fogrle.encode_uniform((256, 512), revealed=True)
    sizes = [len(c) for c in fogrle.payload_dwords(big)]
    led.ok(sizes == [64, 64, 24],
           "a 608-byte stream chunks to 64+64+24 dwords -- multiple 0x008A, "
           "which the handler accumulates (accumMapInitOffset)", f"{sizes}")

    # --- 7. the wire shape, through the real codec ------------------------
    codec = Codec(SCHEMA)
    begin = codec.encode("GAME_SMSG", 0x008B, [x, y, len(fogged)])
    led.ok(len(begin) == 14,
           "0x008B encodes to its declared 14 bytes", f"got {len(begin)}")
    led.ok(begin[2:] == struct.pack("<III", x, y, len(fogged)),
           "...carrying (dims.x, dims.y, byteCount) as three LE dwords")
    filldw = fogrle.payload_dwords(fogged)[0]
    fill = codec.encode("GAME_SMSG", 0x008A, [filldw])
    led.ok(struct.pack("<4I", *filldw) in fill,
           "0x008A carries the 4 payload dwords contiguously LE",
           f"{len(fill)}B")

    # --- 8. the server join: content rows -> the pair or a refusal --------
    import authsrv
    led.ok(authsrv.FOG_INIT is True,
           "FOG_INIT defaults ON -- the M key is safe on served continent-1 "
           "maps without any flag")
    dims, stream, note = authsrv.fog_init_for_map(148)
    led.ok(dims == DIMS and stream == fogged,
           "map 148 (default map) gets continent 1's observed dims and the "
           "all-fogged stream", f"{dims}, {len(stream) if stream else 0}B")
    dims2, stream2, why = authsrv.fog_init_for_map(449)
    led.ok(stream2 is None and "continent 4" in why,
           "map 449 is refused BY CONTINENT -- no observed dims, no guess",
           why[:60])
    dims3, stream3, why3 = authsrv.fog_init_for_map(999)
    led.ok(stream3 is None and "map 999" in why3,
           "an unserved map is refused BY MAP -- no map_continent row",
           why3[:60])
    dimsr, streamr, noter = authsrv.fog_init_for_map(148, reveal=True)
    led.ok(streamr == revealed and "REVEALED" in noter,
           "reveal=True serves the all-revealed stream and says so")
    for mid in (146, 143, 165, 166):
        d, s, n = authsrv.fog_init_for_map(mid)
        led.ok(s == fogged, f"served continent-1 map {mid} gets the pair")

    return led.verdict()


if __name__ == "__main__":
    sys.exit(main())
