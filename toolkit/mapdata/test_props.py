"""Check the Stripped props codec: decode a retail `0x10000004`, encode it back.

THE HEADLINE IS 349 OF 349 BYTE-IDENTICAL, and it is the weakest thing here.
The props record is VARIABLE LENGTH -- 20 bytes plus four per outline point --
so a codec that stored each record's own length, or simply kept the blob, would
round-trip every file it can walk and understand nothing. That is not a
hypothetical failure mode in this repository: `test_mapfile.py` and
`test_pathchunk.py` each caught exactly it behind a perfect headline. So section
2 BUILDS the memcpy saboteur, runs it, and requires it to pass the round trip
while failing the mutation checks -- a file that cannot say which of its own
checks are load-bearing is not measuring anything.

THE MUTATION CONTROLS are the load-bearing half. They decode a chunk, mutate it
IN PLACE until an encoded payload changes LENGTH, and require the emitted count
and point fields to have moved with it -- read back by a walker written in this
file out of `int.from_bytes`, which imports nothing from the module under test.

THE ALIGNMENT CONTROL is what makes the layout a measurement rather than a
choice. Putting the model u16 at the END of the record and giving tag 0 a
five-byte header shifts section 0 by exactly two bytes and is otherwise
self-consistent -- it is the reading a careful person arrives at from a stride-20
hexdump, and `studies/customarea/PROPS.md` was written under a version of it.
It closes for 0 of 349 maps. Section 5 keeps it, on ArenaNet's bytes.

THE ORACLE COMES FROM A CHUNK THIS CODEC NEVER READS. Every prop's (x, y) must
land inside the map rect, which lives in Map Parameters `0x1000000C`. If the
record layout were off by any amount the floats would be garbage. It is
**285,670 of 285,670**, and that is what the layout rests on rather than on the
walk closing.

WHAT THE CORPUS CANNOT DECIDE, asserted rather than glossed. Tag 6's count must
be a u16 because one map carries 611 entries. Tag 4's largest is 81, so
`{u8 tag, u16 count}` and `{u8 tag, u8 count, u8 pad}` fit its bytes equally
well and the corpus cannot separate them -- section 6 asserts BOTH bounds, so
the day an archive holds a map with 256 tag-4 entries this file goes red and
says the ambiguity is gone.

THE CROSS-STREAM ORACLE IS SECTION 9, promoted out of FINDINGS 44's prose:
the Bloated tag-0 section's declared u32 equals 2 + 48*props + 8*points,
PREDICTED from the Stripped chunk alone, and beneath the size the two streams
must agree record for record -- model, position bytes, the scale FORMULA
(exact, which is what took that reading from INFERRED to
compiler-corroborated), flags, point count, and a world-coordinate ring.
`BloatedProps` is read-only by design and section 3d asserts it has no
encode: five of its six sections are opaque, so a round trip could only be a
memcpy. Five rival formulas are kept as controls and must match nothing.

A MISSING VAULT IS A FAILURE, NOT A SKIP. Sections 0-3d still run and their
checks still print, but a run with no archive has measured nothing about
ArenaNet's format, and the floor turns that into the FAIL it is.

    python toolkit/mapdata/test_props.py
    python toolkit/mapdata/test_props.py --sample 20
    python toolkit/mapdata/test_props.py --all     # both streams of all 349
                                                   # maps: 110 checks, 718 s
                                                   # MEASURED 2026-08-12
"""

import argparse
import ast
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive  # noqa: E402
from mapchunks import MapIndex  # noqa: E402
import mapbuild  # noqa: E402
import mapfile as mfile  # noqa: E402
import props as propmod  # noqa: E402
from props import (Prop, PropRef, StrippedProps, Undecodable,  # noqa: E402
                   BloatedProps, SIGNATURE, VERSION, TERMINATOR, PROP_FIXED,
                   REF_STRIDE, TAG_PROPS, TAG_REFS4, TAG_REFS6,
                   BLOATED_PROP_FIXED, BLOATED_RING_STRIDE)
import checks  # noqa: E402
import vaultpath  # noqa: E402

PROPS_CHUNK = 0x10000004
BLOATED_PROPS_CHUNK = 0x20000004
MAP_PARAMS_CHUNK = 0x1000000C

# MEASURED 2026-08-12 by a full 349-map sweep of vault/dat_study/Gw.dat. These
# are population assertions, not decoration: they are what stops a wrong row
# filter or an empty sample from printing "8 of 8" and going green.
CORPUS_MAPS = 349
CORPUS_PROPS = 285670
CORPUS_OUTLINES = 37548
CORPUS_CLOSED = 37505           # 43 outlines do NOT return to their first point
CORPUS_REFS4 = 6355
CORPUS_REFS6 = 10647
CORPUS_TAG6_MAPS = 262          # 87 maps carry no tag-6 section at all
CORPUS_MAX_PROPS = 3776
CORPUS_MAX_REFS4 = 81           # < 256: the tag-4 count width is UNDECIDED
CORPUS_MAX_REFS6 = 611          # > 255: the tag-6 count width IS decided
CORPUS_RING_POINTS = 334725     # outline points, so also Bloated ring points

# The compiler's output for a prop with rot bytes (0,0,0): two basis vectors,
# constant on every such record probed (1,544 of 1,544 over twelve maps;
# asserted corpus-wide by section 9). MEASURED from the archive, and the kind
# of measured fact the provenance gate permits in bulk.
ZERO_ROT_BASIS = struct.pack("<6f", -0.0, -0.0, -1.0, 0.0, 1.0, -0.0)

# The 12-byte chunk `minimal()` has to reproduce, and the row that carries it.
MINIMAL_ROW = 46197
MINIMAL_SIZE = 12

# FLOOR: 99, MEASURED from a green default run on 2026-08-12 (was 70 before
# section 3d and section 9 existed). Sections 0-3d score 81 and need no vault,
# so a vault-less run goes red: a run with no archive has checked both readers
# against chunks this file wrote and nothing at all about ArenaNet's format,
# which is where every claim in props.py lives. `--all` adds section 6's nine
# population checks and section 9's two totals: 110, and the sweep now reads
# BOTH streams of every map -- MEASURED 2026-08-12 at 718 s, against the
# 201 s the Stripped-only sweep took. Budget for that, not for a round number.
LEDGER = checks.Ledger("test_props", floor=99)
check = checks.adopt(LEDGER)


def guarded(fn, *a):
    """Run a section; an exception inside becomes a FAIL, not a traceback."""
    try:
        return fn(*a)
    except Exception as exc:                                 # noqa: BLE001
        check(False, f"section {fn.__name__} ran to completion",
              f"{type(exc).__name__}: {exc}")
        return None


def refuses(fn, *a, **kw):
    """True when `fn` raises Undecodable/ValueError rather than returning."""
    try:
        fn(*a, **kw)
    except (Undecodable, ValueError, struct.error):
        return True
    return False


# --------------------------------------------------------------------------
# An independent walker. Written out of int.from_bytes, importing nothing from
# props.py, so the mutation controls read the emitted bytes with a second pair
# of eyes rather than with the encoder's own.
# --------------------------------------------------------------------------

def w16(b, o):
    return int.from_bytes(b[o:o + 2], "little")


def walk_raw(payload):
    """Return {'props': [(off, points)], 'counts': {tag: (off, count)}}.

    Deliberately duplicates the framing rather than importing it. If props.py
    and this walker ever disagree, that disagreement is the finding.
    """
    out = {"props": [], "counts": {}, "end": None}
    off = 5
    while off < len(payload):
        tag = payload[off]
        if tag == TERMINATOR:
            out["end"] = off
            return out
        if tag == TAG_REFS6:
            count = w16(payload, off + 2)
            out["counts"][tag] = (off + 2, count)
            off = off + 4 + count * REF_STRIDE
            continue
        count = w16(payload, off + 1)
        out["counts"][tag] = (off + 1, count)
        off += 3
        if tag == TAG_PROPS:
            for _ in range(count):
                points = payload[off + 19]
                out["props"].append((off, points))
                off += PROP_FIXED + REF_STRIDE * points
        else:
            off += count * REF_STRIDE
    return out


def walk_rival(payload):
    """The rival layout: 5-byte tag-0 header, model u16 at the END of a record.

    Self-consistent, and exactly what a stride-20 hexdump suggests. It closes on
    the terminator for 0 of 349 retail maps, which is what makes the real layout
    a measurement instead of a preference.
    """
    off = 5
    while True:
        if off >= len(payload):
            return False
        tag = payload[off]
        if tag == TERMINATOR:
            return off == len(payload) - 1
        if tag == TAG_PROPS:
            if off + 5 > len(payload):
                return False
            count = int.from_bytes(payload[off + 1:off + 5], "little")
            off += 5
            for _ in range(count):
                if off + PROP_FIXED > len(payload):
                    return False
                off += PROP_FIXED + REF_STRIDE * payload[off + 17]
        elif tag == TAG_REFS4:
            off += 3 + w16(payload, off + 1) * REF_STRIDE
        elif tag == TAG_REFS6:
            off += 4 + w16(payload, off + 2) * REF_STRIDE
        else:
            return False


class MemcpyProps:
    """The saboteur: keep the blob, hand it back. Round-trips everything.

    Built and RUN so this file can show which of its own checks are
    load-bearing. It must pass section 4's headline and fail section 2.
    """

    def __init__(self, blob):
        self._blob = bytes(blob)
        real = StrippedProps.decode(blob)
        self.props = real.props
        self.refs4 = real.refs4
        self.refs6 = real.refs6

    def encode(self):
        return self._blob


# --------------------------------------------------------------------------
def section0():
    """Constants, and the shape of the smallest chunk the format can express."""
    print("\n-- 0. the format, and minimal() --")
    m = StrippedProps.minimal()
    blob = m.encode()
    check(len(blob) == MINIMAL_SIZE,
          f"minimal() is {MINIMAL_SIZE} bytes", f"got {len(blob)}")
    check(int.from_bytes(blob[0:4], "little") == SIGNATURE,
          "minimal() carries the props signature")
    check(blob[4] == VERSION, f"minimal() version is {VERSION}")
    check(blob[-1] == TERMINATOR, "minimal() ends on the terminator")
    check(blob[5] == TAG_PROPS and w16(blob, 6) == 0,
          "minimal() declares tag 0 with a count of zero")
    check(blob[8] == TAG_REFS4 and w16(blob, 9) == 0,
          "minimal() declares tag 4 with a count of zero")
    check(TAG_REFS6 not in walk_raw(blob)["counts"],
          "minimal() emits NO tag-6 section",
          "absent and empty are different files; 87 maps have no tag 6")
    back = StrippedProps.decode(blob)
    check(back.encode() == blob, "minimal() survives a round trip")
    check(len(back.props) == 0 and back.refs6 is None,
          "minimal() decodes to no props and no tag-6 section")
    return m


def section1():
    """Author props from nothing: the derived fields must be derived."""
    print("\n-- 1. authoring, and the derived counts --")
    outline = ((-10, -10), (10, -10), (10, 10), (-10, 10), (-10, -10))
    sp = StrippedProps(
        props=[Prop(7, 100.0, 200.0, -30.5),
               Prop(9, -50.0, 0.0, 12.25, rot=(1, 2, 3), scale=0x7F,
                    flags=1, outline=outline)],
        refs4=[PropRef(0xBEEF, 1)],
        refs6=[PropRef(3, 0)],
        tag6_word=0)
    blob = sp.encode()
    raw = walk_raw(blob)

    check(raw["end"] == len(blob) - 1,
          "an authored chunk closes on its terminator")
    check(raw["counts"][TAG_PROPS][1] == 2, "tag 0's emitted count is 2")
    check(raw["counts"][TAG_REFS4][1] == 1, "tag 4's emitted count is 1")
    check(raw["counts"][TAG_REFS6][1] == 1, "tag 6's emitted count is 1")
    check([p[1] for p in raw["props"]] == [0, 5],
          "the emitted point counts are 0 and 5, derived from the outlines")
    check(sp.props[1].size == PROP_FIXED + REF_STRIDE * 5,
          "a 5-point prop is 20 + 4*5 bytes")
    expect = 5 + 3 + (PROP_FIXED + PROP_FIXED + 20) + 3 + 4 + 4 + 4 + 1
    check(len(blob) == expect,
          f"the whole chunk is {expect} bytes", f"got {len(blob)}")

    back = StrippedProps.decode(blob)
    check(back.encode() == blob, "an authored chunk round-trips")
    check(back.props[1].outline == outline, "the outline survives exactly")
    check(back.props[1].closed, "a ring that returns to its start reads closed")
    check(not back.props[0].closed,
          "a prop with no outline is not reported closed")
    check(back.props[1].rot == (1, 2, 3) and back.props[1].scale == 0x7F
          and back.props[1].flags == 1,
          "rot, scale and flags survive as separate bytes",
          "four byte fields, not one opaque u32: the client reads each at its "
          "own address (0x0073DE88/6D/5D for rot, 0x0073DE2D for scale)")
    bad6 = StrippedProps(props=[Prop(1, 0.0, 0.0, 0.0)], refs4=(), refs6=(),
                         tag6_word=1)
    check(refuses(bad6.encode),
          "a non-zero tag-6 second byte is refused",
          "the client compares it to 0 at 0x0073D8D3; retail is 0 on all 262")
    ok6 = StrippedProps(props=[Prop(1, 0.0, 0.0, 0.0)], refs4=(), refs6=(),
                        tag6_word=0)
    check(not refuses(ok6.encode),
          "POSITIVE CONTROL: a zero tag-6 second byte is accepted")
    tampered = bytearray(ok6.encode())
    tampered[tampered.index(TAG_REFS6, 5) + 1] = 1
    check(refuses(StrippedProps.decode, bytes(tampered)),
          "and decode refuses it too, not just encode")
    check(back.refs4[0] == PropRef(0xBEEF, 1) and back.refs6[0] == PropRef(3, 0),
          "both reference tables survive")

    empty6 = StrippedProps(props=[Prop(1, 0.0, 0.0, 0.0)], refs4=(), refs6=())
    b6 = empty6.encode()
    check(TAG_REFS6 in walk_raw(b6)["counts"],
          "an EMPTY tag-6 section is still emitted",
          "114 retail maps carry tag 6 with a count of 0")
    check(StrippedProps.decode(b6).refs6 == [],
          "an empty tag 6 decodes to [] and not to None")
    check(len(b6) - len(StrippedProps(props=empty6.props).encode()) == 4,
          "an empty tag-6 section costs exactly 4 bytes")
    return sp


def section2(sp):
    """The mutation controls, and the memcpy saboteur that must fail them."""
    print("\n-- 2. mutation controls: what a memcpy cannot do --")
    base = sp.encode()

    # (a) one more outline point must move the prop's point byte AND the length
    grown = StrippedProps.decode(base)
    grown.props[1].outline = grown.props[1].outline + ((0, 0),)
    gb = grown.encode()
    graw = walk_raw(gb)
    check(len(gb) == len(base) + REF_STRIDE,
          "one more outline point grows the chunk by exactly 4 bytes")
    check([p[1] for p in graw["props"]] == [0, 6],
          "the emitted point count moved 5 -> 6")
    check(graw["end"] == len(gb) - 1, "the grown chunk still closes")

    # (b) one more prop must move tag 0's count and the total length
    more = StrippedProps.decode(base)
    more.props.append(Prop(3, 1.0, 2.0, 3.0))
    mb_ = more.encode()
    mraw = walk_raw(mb_)
    check(mraw["counts"][TAG_PROPS][1] == 3, "tag 0's emitted count moved 2 -> 3")
    check(len(mb_) == len(base) + PROP_FIXED,
          "one more prop grows the chunk by exactly 20 bytes")

    # (c) one more reference must move tag 4's count
    ref = StrippedProps.decode(base)
    ref.refs4.append(PropRef(1, 0))
    rb = ref.encode()
    check(walk_raw(rb)["counts"][TAG_REFS4][1] == 2,
          "tag 4's emitted count moved 1 -> 2")
    check(len(rb) == len(base) + REF_STRIDE,
          "one more reference grows the chunk by exactly 4 bytes")

    # (d) THE SABOTEUR. It passes the headline and must fail every check above.
    sab = MemcpyProps(base)
    check(sab.encode() == base,
          "the memcpy saboteur PASSES the byte-identity headline",
          "which is why the headline alone is not the result")
    sab.props[1].outline = sab.props[1].outline + ((0, 0),)
    sab.props.append(Prop(3, 1.0, 2.0, 3.0))
    sab.refs4.append(PropRef(1, 0))
    sb = sab.encode()
    caught = 0
    if len(sb) == len(base):
        caught += 1
    if walk_raw(sb)["counts"][TAG_PROPS][1] == 2:
        caught += 1
    if [p[1] for p in walk_raw(sb)["props"]] == [0, 5]:
        caught += 1
    check(caught == 3,
          "the saboteur FAILS all three mutation controls",
          f"caught by {caught} of 3")


def section3(sp):
    """Refusals, each with a positive control so it is not refuse-everything."""
    print("\n-- 3. refusals --")
    base = bytearray(sp.encode())
    check(not refuses(StrippedProps.decode, bytes(base)),
          "POSITIVE CONTROL: the unmodified chunk is accepted")

    bad = bytearray(base)
    bad[0] ^= 0xFF
    check(refuses(StrippedProps.decode, bytes(bad)),
          "a wrong signature is refused")

    bad = bytearray(base)
    bad[4] = VERSION + 1
    check(refuses(StrippedProps.decode, bytes(bad)),
          "an unknown version is refused",
          "a second version is a second framing, not a detail")

    check(refuses(StrippedProps.decode, bytes(base[:-1])),
          "a chunk with its terminator cut off is refused")
    check(refuses(StrippedProps.decode, bytes(base) + b"\x00"),
          "a byte of tail after the terminator is refused",
          "the terminator is the LAST byte or the walk misread a length")
    check(refuses(StrippedProps.decode, bytes(base[:4])),
          "a chunk too short to hold a header is refused")

    bad = bytearray(base)
    bad[5] = 3
    check(refuses(StrippedProps.decode, bytes(bad)),
          "an unknown tag is refused rather than skipped",
          "the cursor is already lost; the next record would be fiction")

    # order: tag 4 before tag 0
    out_of_order = bytearray(struct.pack("<IB", SIGNATURE, VERSION))
    out_of_order += bytes([TAG_REFS4]) + struct.pack("<H", 0)
    out_of_order += bytes([TAG_PROPS]) + struct.pack("<H", 0)
    out_of_order.append(TERMINATOR)
    check(refuses(StrippedProps.decode, bytes(out_of_order)),
          "sections out of order are refused")
    in_order = bytearray(struct.pack("<IB", SIGNATURE, VERSION))
    in_order += bytes([TAG_PROPS]) + struct.pack("<H", 0)
    in_order += bytes([TAG_REFS4]) + struct.pack("<H", 0)
    in_order.append(TERMINATOR)
    check(not refuses(StrippedProps.decode, bytes(in_order)),
          "POSITIVE CONTROL: the same two sections in order are accepted")

    # a reference past the end of the prop array
    bad_ref = StrippedProps(props=[Prop(1, 0.0, 0.0, 0.0)],
                            refs4=[PropRef(0, 5)])
    check(refuses(bad_ref.encode),
          "a reference naming a prop that does not exist is refused",
          "retail agrees 17,002 times out of 17,002, so this fires only on ours")
    good_ref = StrippedProps(props=[Prop(1, 0.0, 0.0, 0.0)],
                             refs4=[PropRef(0, 0)])
    check(not refuses(good_ref.encode),
          "POSITIVE CONTROL: an in-range reference is accepted")

    # Only tag 6 is optional. A chunk missing tag 0 or tag 4 is one the client
    # refuses -- and refuses SILENTLY, which is why this is a decode error here.
    no0 = bytearray(struct.pack("<IB", SIGNATURE, VERSION))
    no0 += bytes([TAG_REFS4]) + struct.pack("<H", 0)
    no0.append(TERMINATOR)
    check(refuses(StrippedProps.decode, bytes(no0)),
          "a chunk with no tag-0 section is refused",
          "tag 0's stage returns 0 on a mismatch; the parse aborts and the "
          "Path gate at 0x00712678 then kills the navmesh with no assert")
    no4 = bytearray(struct.pack("<IB", SIGNATURE, VERSION))
    no4 += bytes([TAG_PROPS]) + struct.pack("<H", 0)
    no4.append(TERMINATOR)
    check(refuses(StrippedProps.decode, bytes(no4)),
          "a chunk with no tag-4 section is refused")
    check(not refuses(StrippedProps.decode,
                      StrippedProps.minimal().encode()),
          "POSITIVE CONTROL: tag 0 + tag 4 + terminator, with NO tag 6, is "
          "accepted", "87 retail maps ship exactly that")

    huge = StrippedProps(props=[Prop(1, 0.0, 0.0, 0.0,
                                     outline=[(0, 0)] * 256)])
    check(refuses(huge.encode),
          "a 256-point outline is refused; the count is a u8")
    fits = StrippedProps(props=[Prop(1, 0.0, 0.0, 0.0,
                                     outline=[(0, 0)] * 255)])
    check(not refuses(fits.encode),
          "POSITIVE CONTROL: a 255-point outline is accepted")


def section3b(sp):
    """The rival layout must already lose on bytes we wrote ourselves."""
    print("\n-- 3b. the alignment rival, on our own bytes --")
    blob = sp.encode()
    check(walk_raw(blob)["end"] == len(blob) - 1,
          "POSITIVE CONTROL: the real walker closes on our chunk")
    check(not walk_rival(blob),
          "the model-at-the-end rival does NOT close on our chunk")


def read_once(ar, mi, picks):
    """Read every picked map ONCE: both props payloads and the rect.

    Sections 4, 5, 7 and 9 all want the same bytes, and decompressing 349
    maps repeatedly cost 15 minutes against the one pass takes. Section 9 is
    why the HEAD row is read too: the cross-stream oracle needs the Bloated
    props chunk beside the Stripped one, and the head row is where it lives.
    That read is what the sweep's extra minutes buy.
    """
    out = []
    for head in picks:
        m = mfile.MapFile.decode(ar.read(mi.partner(head)), strict=False)
        rect = mapbuild.decode_map_parameters(
            m.find(MAP_PARAMS_CHUNK).payload())[0]
        bm = mfile.MapFile.decode(ar.read(head), strict=False)
        out.append((mi.partner(head).index, m.find(PROPS_CHUNK).payload(),
                    rect, bm.find(BLOATED_PROPS_CHUNK).payload()))
    return out


def section4(corpus, complete):
    """The sweep. Byte-identity, plus the population it was measured over."""
    print(f"\n-- 4. {len(corpus)} retail maps: decode, re-encode, compare --")
    same = diff = 0
    n_props = n_out = n_closed = n_r4 = n_r6 = n_tag6 = 0
    max_props = max_r4 = max_r6 = 0
    versions = set()
    words = set()
    for _row, blob, _rect, _bl in corpus:
        p = StrippedProps.decode(blob)
        if p.encode() == blob:
            same += 1
        else:
            diff += 1
        versions.add(p.version)
        n_props += len(p.props)
        max_props = max(max_props, len(p.props))
        n_r4 += len(p.refs4)
        max_r4 = max(max_r4, len(p.refs4))
        if p.refs6 is not None:
            n_tag6 += 1
            n_r6 += len(p.refs6)
            max_r6 = max(max_r6, len(p.refs6))
            words.add(p.tag6_word)
        for pr in p.props:
            if pr.points:
                n_out += 1
                n_closed += 1 if pr.closed else 0
    check(diff == 0 and same == len(corpus),
          f"{same} of {len(corpus)} maps re-encode byte-identically",
          f"{diff} differ")
    check(versions == {VERSION},
          f"every map's version byte is {VERSION}", f"saw {sorted(versions)}")
    check(words <= {0},
          "tag 6's second header byte is 0 wherever tag 6 appears",
          f"saw {sorted(words)}; the 349/349 close already proves it is not "
          f"a length")
    if not complete:
        LEDGER.skip("the corpus population assertions (section 6)",
                    f"only {len(corpus)} of {CORPUS_MAPS} maps swept; "
                    f"run with --all for the population numbers")
        return None
    return {"props": n_props, "out": n_out, "closed": n_closed,
            "r4": n_r4, "r6": n_r6, "tag6": n_tag6, "maps": len(corpus),
            "max_props": max_props, "max_r4": max_r4, "max_r6": max_r6}


def section5(corpus):
    """Controls on ARENANET's bytes: the rival, and the tag-6 stride."""
    print(f"\n-- 5. controls on retail bytes ({len(corpus)} maps) --")
    rival_closed = real_closed = 0
    stride_ok = {s: 0 for s in (1, 2, 4, 6, 8, 20)}
    discriminating = 0
    for _row, blob, _rect, _bl in corpus:
        if walk_rival(blob):
            rival_closed += 1
        if walk_raw(blob)["end"] == len(blob) - 1:
            real_closed += 1
        p = StrippedProps.decode(blob)
        if p.refs6:
            discriminating += 1
        for s in stride_ok:
            if walk_stride(blob, s):
                stride_ok[s] += 1
    check(real_closed == len(corpus),
          f"POSITIVE CONTROL: the real walk closes on {len(corpus)} of "
          f"{len(corpus)} retail maps")
    check(rival_closed == 0,
          f"the model-at-the-end rival closes on 0 of {len(corpus)}",
          f"got {rival_closed}")
    check(stride_ok[4] == len(corpus),
          f"tag-6 stride 4 closes on all {len(corpus)} maps")
    check(discriminating > 0,
          "the sample contains at least one map with a non-empty tag 6",
          f"{discriminating} maps; without one the stride sweep is vacuous")
    wrong = [s for s in stride_ok if s != 4 and stride_ok[s] == len(corpus)]
    check(not wrong,
          "no other tag-6 stride closes on every map",
          f"also closed: {wrong}")


def walk_stride(payload, tag6_stride):
    """The real walk with tag 6's stride swapped out. Used only as a control."""
    off = 5
    while True:
        if off >= len(payload):
            return False
        tag = payload[off]
        if tag == TERMINATOR:
            return off == len(payload) - 1
        if tag == TAG_PROPS:
            count = w16(payload, off + 1)
            off += 3
            for _ in range(count):
                if off + PROP_FIXED > len(payload):
                    return False
                off += PROP_FIXED + REF_STRIDE * payload[off + 19]
        elif tag == TAG_REFS4:
            off += 3 + w16(payload, off + 1) * REF_STRIDE
        elif tag == TAG_REFS6:
            off += 4 + w16(payload, off + 2) * tag6_stride
        else:
            return False


def section6(pop):
    """The population, and the one width the corpus cannot decide."""
    print("\n-- 6. the corpus population --")
    if pop is None:
        return
    check(pop["maps"] == CORPUS_MAPS, f"{CORPUS_MAPS} maps swept",
          f"got {pop['maps']}")
    check(pop["props"] == CORPUS_PROPS,
          f"{CORPUS_PROPS} props decoded", f"got {pop['props']}")
    check(pop["out"] == CORPUS_OUTLINES,
          f"{CORPUS_OUTLINES} props carry an outline", f"got {pop['out']}")
    check(pop["closed"] == CORPUS_CLOSED,
          f"{CORPUS_CLOSED} of those outlines are closed rings",
          f"got {pop['closed']}; {pop['out'] - pop['closed']} are not, and "
          f"that is a fact about retail rather than a rounding error")
    check(pop["r4"] == CORPUS_REFS4 and pop["r6"] == CORPUS_REFS6,
          f"{CORPUS_REFS4} tag-4 and {CORPUS_REFS6} tag-6 references",
          f"got {pop['r4']} and {pop['r6']}")
    check(pop["tag6"] == CORPUS_TAG6_MAPS,
          f"{CORPUS_TAG6_MAPS} maps carry a tag-6 section",
          f"got {pop['tag6']}; the other "
          f"{CORPUS_MAPS - CORPUS_TAG6_MAPS} have none at all")
    check(pop["max_props"] == CORPUS_MAX_PROPS and CORPUS_MAX_PROPS > 0xFF,
          f"the largest map holds {CORPUS_MAX_PROPS} props, so tag 0's count "
          f"MUST be a u16", f"got {pop['max_props']}")
    check(pop["max_r6"] == CORPUS_MAX_REFS6 and CORPUS_MAX_REFS6 > 0xFF,
          f"the largest tag-6 table holds {CORPUS_MAX_REFS6} entries, so its "
          f"count MUST be a u16", f"got {pop['max_r6']}")
    check(pop["max_r4"] == CORPUS_MAX_REFS4 and CORPUS_MAX_REFS4 <= 0xFF,
          f"the largest tag-4 table holds only {CORPUS_MAX_REFS4} entries",
          "so u16-count and u8-count-plus-pad fit its bytes equally well and "
          "the corpus CANNOT decide the width. If this ever goes red the "
          "ambiguity is resolved -- read the new maximum, do not raise it")


def section7(corpus):
    """The oracle: a chunk this codec never opens says where props stand."""
    print(f"\n-- 7. the rect oracle ({len(corpus)} maps) --")
    inside = outside = 0
    for _row, blob, rect, _bl in corpus:
        p = StrippedProps.decode(blob)
        x0, y0, x1, y1 = rect
        for pr in p.props:
            if x0 <= pr.x <= x1 and y0 <= pr.y <= y1:
                inside += 1
            else:
                outside += 1
    check(inside > 0, "the sample actually contains props",
          f"{inside + outside} positions tested")
    check(outside == 0,
          f"{inside} of {inside + outside} prop positions are inside the map "
          f"rect", f"{outside} outside; the rect comes from Map Parameters, "
          f"which props.py never reads")


def section8(ar, mi):
    """minimal() must reproduce ArenaNet's smallest chunk, from nothing."""
    print("\n-- 8. minimal() against the archive --")
    row = [p for _h, p in mi.pairs if p.index == MINIMAL_ROW]
    if not row:
        LEDGER.skip("minimal() vs the archive",
                    f"row {MINIMAL_ROW} is not a map partner in this archive")
        return
    m = mfile.MapFile.decode(ar.read(row[0]), strict=False)
    blob = m.find(PROPS_CHUNK).payload()
    check(len(blob) == MINIMAL_SIZE,
          f"row {MINIMAL_ROW}'s props chunk is {MINIMAL_SIZE} bytes",
          f"got {len(blob)}")
    check(StrippedProps.minimal().encode() == blob,
          "a chunk authored from NOTHING equals ArenaNet's smallest one",
          "no archive, no donor -- which is what makes it a check")


def section3c():
    """Provenance: no borrowed payload may hide in the module.

    props.py is a pure codec -- unlike `mapbuild.py` and `stripbuild.py` it
    borrows nothing at all, so the bar here is simply that it carries no
    ArenaNet bytes and reaches the archive only through `vaultpath` at run time.
    """
    print("\n-- 3c. provenance --")
    path = os.path.join(HERE, "props.py")
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    big = [n for n in ast.walk(tree)
           if isinstance(n, ast.Constant) and isinstance(n.value, bytes)
           and len(n.value) > 2]
    check(not big,
          "no bytes literal over two bytes anywhere in props.py",
          f"found {[b.value[:8] for b in big]}")
    hardcoded = [n.value for n in ast.walk(tree)
                 if isinstance(n, ast.Constant) and isinstance(n.value, str)
                 and (":\\" in n.value or ":/" in n.value)]
    check(not hardcoded,
          "props.py hard-codes no absolute path",
          f"found {hardcoded}")
    check("vaultpath" in src,
          "props.py reaches the archive through vaultpath, at run time")


def section9(corpus, complete):
    """The cross-stream oracle, on retail: the compiler's own output agrees.

    The strongest check in the arc (FINDINGS 44), promoted out of prose. The
    prediction is computed from the STRIPPED chunk alone; the number it
    predicts is a u32 the COMPILER wrote into the Bloated stream. Beneath the
    size, `corresponds()` requires record-for-record agreement -- model,
    position bytes, scale formula, flags, point count, world-coordinate ring
    -- which is the read-back rung e10d will use on a map WE author.
    """
    print(f"\n-- 9. the cross-stream oracle ({len(corpus)} maps) --")
    oracle_hit = oracle_miss = 0
    clean = dirty = 0
    n_records = n_ring = 0
    zero_rot = zero_rot_basis = 0
    tag6_agree = tag6_disagree = 0
    discriminating = 0
    rival_hits = {k: 0 for k in ("fixed 47", "fixed 49", "ring 4", "ring 12",
                                 "no count word")}
    for row, blob, _rect, bloated in corpus:
        sp = StrippedProps.decode(blob)
        bp = BloatedProps.decode(bloated)
        n = len(sp.props)
        pts = sum(p.points for p in sp.props)
        want = sp.predicted_bloated_tag0_size()
        if bp.tag0_size == want:
            oracle_hit += 1
        else:
            oracle_miss += 1
        mism = bp.corresponds(sp)
        if mism:
            dirty += 1
            print(f"   row {row}: {mism[:3]}")
        else:
            clean += 1
        n_records += len(bp.records)
        n_ring += sum(r.points for r in bp.records)
        if (bp.sections.get(6) is None) == (sp.refs6 is None):
            tag6_agree += 1
        else:
            tag6_disagree += 1
        for rec, spr in zip(bp.records, sp.props):
            if spr.rot == (0, 0, 0):
                zero_rot += 1
                if struct.pack("<6f", *rec.basis) == ZERO_ROT_BASIS:
                    zero_rot_basis += 1
        if n > 0 and pts > 0:
            discriminating += 1
            rivals = {"fixed 47": 2 + 47 * n + 8 * pts,
                      "fixed 49": 2 + 49 * n + 8 * pts,
                      "ring 4": 2 + 48 * n + 4 * pts,
                      "ring 12": 2 + 48 * n + 12 * pts,
                      "no count word": 48 * n + 8 * pts}
            for k, v in rivals.items():
                if v == bp.tag0_size:
                    rival_hits[k] += 1

    check(oracle_miss == 0 and oracle_hit == len(corpus),
          f"the oracle: {oracle_hit} of {len(corpus)} Bloated tag-0 sizes "
          f"equal 2 + 48*props + 8*points, predicted from the Stripped "
          f"chunk alone", f"{oracle_miss} miss")
    check(dirty == 0 and clean == len(corpus),
          f"corresponds(): {clean} of {len(corpus)} maps agree record for "
          f"record across the two streams", f"{dirty} do not")
    check(tag6_disagree == 0,
          "tag-6 presence agrees between the streams on every map",
          f"{tag6_disagree} disagree")
    check(discriminating > 0,
          "the sample contains a map with props AND outline points",
          f"{discriminating} such maps; without one the oracle and its "
          f"rivals are vacuous")
    wrong = [k for k, v in rival_hits.items() if v]
    check(not wrong,
          f"no rival formula matches any of the {discriminating} "
          f"discriminating maps", f"also matched: {wrong}")
    check(zero_rot > 0 and zero_rot_basis == zero_rot,
          f"all {zero_rot} zero-rot records carry the constant basis pair",
          f"{zero_rot_basis} of {zero_rot}; a rot=(0,0,0) prop compiles to "
          f"(-0,-0,-1),(0,1,-0) on every record probed")
    if complete:
        check(n_records == CORPUS_PROPS,
              f"{CORPUS_PROPS} Bloated records over the corpus, equal to the "
              f"Stripped prop population", f"got {n_records}")
        check(n_ring == CORPUS_RING_POINTS,
              f"{CORPUS_RING_POINTS} ring points over the corpus, equal to "
              f"the Stripped outline-point population", f"got {n_ring}")
    else:
        LEDGER.skip("the Bloated population totals (section 9)",
                    f"only {len(corpus)} of {CORPUS_MAPS} maps swept; "
                    f"run with --all for the corpus numbers")


def synth_bloated(points=2, tag6=True, scale_byte=0x7F):
    """A Bloated props chunk built by hand, out of struct.pack.

    Written here, not by props.py, so section 3d's refusal checks are against
    bytes the module under test had no hand in framing.
    """
    ring = [(100.0 + d, 200.0 + d) for d in range(points)]
    body = struct.pack("<H", 1)
    body += struct.pack("<H", 5)                       # model
    body += struct.pack("<fff", 100.0, 200.0, -13.0)   # xyz
    body += ZERO_ROT_BASIS                             # basis vectors
    body += struct.pack("<f", scale_byte * (255 / 128) / 256 + 1 / 128)
    body += b"\x00" * 4                                # the NOT-FOUND tail
    body += bytes([0, points])                         # flags, points
    for x, y in ring:
        body += struct.pack("<ff", x, y)
    out = struct.pack("<IB", SIGNATURE, VERSION)
    for tag in (0, 1, 2, 3, 4) + ((6,) if tag6 else ()):
        sec = body if tag == 0 else b""
        out += struct.pack("<BI", tag, len(sec)) + sec
    out += struct.pack("<BI", TERMINATOR, 0)
    return out


def section3d():
    """The Bloated reader, on bytes this file wrote: parse and refusals."""
    print("\n-- 3d. the Bloated reader, on our own bytes --")
    blob = synth_bloated()
    bp = BloatedProps.decode(blob)
    check(bp.count == 1 and len(bp.records) == 1,
          "POSITIVE CONTROL: the synthetic Bloated chunk decodes")
    rec = bp.records[0]
    check(rec.model == 5 and (rec.x, rec.y, rec.z) == (100.0, 200.0, -13.0),
          "model and position parse from their measured offsets")
    check(rec.points == 2 and rec.ring[0] == (100.0, 200.0),
          "the ring parses at 8 bytes per point after the 48-byte record")
    check(struct.pack("<6f", *rec.basis) == ZERO_ROT_BASIS,
          "the basis vectors parse from +14")
    check(6 in bp.sections and bp.sections[6] == b"",
          "an empty tag-6 section is kept, and kept apart from absence")

    sp = StrippedProps(
        props=[Prop(5, 100.0, 200.0, -13.0, scale=0x7F,
                    outline=((0, 0), (1, 1)))],
        refs4=(), refs6=())
    check(sp.predicted_bloated_tag0_size()
          == 2 + BLOATED_PROP_FIXED + 2 * BLOATED_RING_STRIDE,
          "the oracle formula: 2 + 48*1 + 8*2 for one prop, two points")
    check(bp.tag0_size == sp.predicted_bloated_tag0_size(),
          "the synthetic pair agrees with the oracle")
    check(bp.corresponds(sp) == [],
          "corresponds() returns no mismatches on the matching pair")

    # every way corresponds() must be able to disagree
    wrong_model = StrippedProps(
        props=[Prop(6, 100.0, 200.0, -13.0, scale=0x7F,
                    outline=((0, 0), (1, 1)))], refs4=(), refs6=())
    check(any("model" in m for m in bp.corresponds(wrong_model)),
          "corresponds() names a wrong model")
    wrong_ring = StrippedProps(
        props=[Prop(5, 100.0, 200.0, -13.0, scale=0x7F,
                    outline=((0, 0), (2, 1)))], refs4=(), refs6=())
    check(any("ring" in m for m in bp.corresponds(wrong_ring)),
          "corresponds() names a moved ring point")
    fewer = StrippedProps(props=(), refs4=(), refs6=())
    check(any("count" in m for m in bp.corresponds(fewer)),
          "corresponds() names a count mismatch")
    no6 = StrippedProps(
        props=[Prop(5, 100.0, 200.0, -13.0, scale=0x7F,
                    outline=((0, 0), (1, 1)))], refs4=(), refs6=None)
    check(any("tag-6" in m for m in bp.corresponds(no6)),
          "corresponds() names a tag-6 presence mismatch")

    # refusals, each one byte from the accepted control above
    bad = bytearray(blob)
    bad[0] ^= 0xFF
    check(refuses(BloatedProps.decode, bytes(bad)),
          "a wrong Bloated signature is refused")
    bad = bytearray(blob)
    bad[4] = VERSION + 1
    check(refuses(BloatedProps.decode, bytes(bad)),
          "an unknown Bloated version is refused")
    bad = bytearray(blob)
    bad[5] = 5
    check(refuses(BloatedProps.decode, bytes(bad)),
          "an unknown Bloated tag is refused")
    check(refuses(BloatedProps.decode, blob[:-5]),
          "a chunk with its terminator section cut off is refused")
    check(refuses(BloatedProps.decode, blob + b"\x00"),
          "a byte of tail after the terminator section is refused")
    bad = bytearray(blob)
    bad[-4] = 1                       # terminator's size u32, low byte
    check(refuses(BloatedProps.decode, bytes(bad)),
          "a terminator declaring a non-zero size is refused")
    bad = bytearray(blob)
    bad[6] += 1                       # tag 0's declared size, low byte
    check(refuses(BloatedProps.decode, bytes(bad)),
          "a tag-0 size the record walk cannot close on is refused")
    bad = bytearray(blob)
    ring_off = 10 + 2 + 47            # header + count + points byte
    bad[ring_off] = 3                 # claim 3 ring points, carry 2
    check(refuses(BloatedProps.decode, bytes(bad)),
          "a ring running off its section end is refused")
    no2 = synth_bloated()
    # rebuild without tag 2 by hand: drop its 5-byte empty section
    i = no2.index(struct.pack("<BI", 2, 0))
    check(refuses(BloatedProps.decode, no2[:i] + no2[i + 5:]),
          "a chunk missing one mandatory section is refused")
    swapped = bytearray(blob)
    i1 = swapped.index(struct.pack("<BI", 1, 0))
    i2 = swapped.index(struct.pack("<BI", 2, 0))
    swapped[i1], swapped[i2] = swapped[i2], swapped[i1]
    check(refuses(BloatedProps.decode, bytes(swapped)),
          "sections out of order are refused")
    check(not hasattr(BloatedProps, "encode"),
          "BloatedProps has NO encode",
          "read-only is the design: five of six sections are opaque, so an "
          "encode could only be a memcpy wearing a round-trip headline")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.strip().splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=None)
    ap.add_argument("--sample", type=int, default=8)
    ap.add_argument("--all", action="store_true",
                    help="every map -- 349, ~4 minutes")
    args = ap.parse_args(argv)

    print(__doc__.strip().splitlines()[0])
    guarded(section0)
    sp = guarded(section1)
    if sp is not None:
        guarded(section2, sp)
        guarded(section3, sp)
        guarded(section3b, sp)
    guarded(section3c)
    guarded(section3d)

    dat = args.dat
    if dat is None:
        dat = os.path.join(vaultpath.vault_path("dat_study"), "Gw.dat")
    if not os.path.isfile(dat):
        LEDGER.skip("everything that needs the archive (sections 4-9)",
                    f"no Gw.dat at {dat}; vault resolved to "
                    f"{vaultpath.vault_root()} ({vaultpath.vault_why()}). "
                    f"Sections 0-3 measured the codec against chunks this "
                    f"test wrote and NOTHING about ArenaNet's format.")
        return LEDGER.verdict()

    with Archive(dat) as ar:
        mi = MapIndex(ar)
        heads = [h for h, _p in mi.pairs]
        if args.all:
            picks = heads
        else:
            step = max(1, len(heads) // max(1, args.sample))
            picks = heads[::step][:args.sample]
        corpus = read_once(ar, mi, picks)
        pop = guarded(section4, corpus, args.all)
        guarded(section5, corpus)
        guarded(section6, pop)
        guarded(section7, corpus)
        guarded(section8, ar, mi)
        guarded(section9, corpus, args.all)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
