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

A MISSING VAULT IS A FAILURE, NOT A SKIP. Sections 0-3 still run and their
checks still print, but a run with no archive has measured nothing about
ArenaNet's format, and the floor turns that into the FAIL it is.

    python toolkit/mapdata/test_props.py
    python toolkit/mapdata/test_props.py --sample 20
    python toolkit/mapdata/test_props.py --all     # 349 maps, 76 checks, ~200 s
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
                   SIGNATURE, VERSION, TERMINATOR, PROP_FIXED, REF_STRIDE,
                   TAG_PROPS, TAG_REFS4, TAG_REFS6)
import checks  # noqa: E402
import vaultpath  # noqa: E402

PROPS_CHUNK = 0x10000004
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

# The 12-byte chunk `minimal()` has to reproduce, and the row that carries it.
MINIMAL_ROW = 46197
MINIMAL_SIZE = 12

# FLOOR: 67, MEASURED from a green default run on 2026-08-12. Sections 0-3c
# score 55 and need no vault, so a vault-less run goes red: a run with no
# archive has checked the codec against chunks this file wrote and nothing at
# all about ArenaNet's format, which is where every claim in props.py lives.
# `--all` adds section 6's nine population checks on top: 76, and the sweep
# was MEASURED at 201 s -- budget for that rather than for a round number.
LEDGER = checks.Ledger("test_props", floor=67)
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
    """Read every picked map ONCE: its props payload and its rect.

    Sections 4, 5 and 7 all want the same bytes, and decompressing 349 maps
    three times cost 15 minutes against the 5 one pass takes. The props chunks
    are ~4 MB in total, so holding them is cheap.
    """
    out = []
    for head in picks:
        m = mfile.MapFile.decode(ar.read(mi.partner(head)), strict=False)
        rect = mapbuild.decode_map_parameters(
            m.find(MAP_PARAMS_CHUNK).payload())[0]
        out.append((mi.partner(head).index, m.find(PROPS_CHUNK).payload(), rect))
    return out


def section4(corpus, complete):
    """The sweep. Byte-identity, plus the population it was measured over."""
    print(f"\n-- 4. {len(corpus)} retail maps: decode, re-encode, compare --")
    same = diff = 0
    n_props = n_out = n_closed = n_r4 = n_r6 = n_tag6 = 0
    max_props = max_r4 = max_r6 = 0
    versions = set()
    words = set()
    for _row, blob, _rect in corpus:
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
    for _row, blob, _rect in corpus:
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
    for _row, blob, rect in corpus:
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

    dat = args.dat
    if dat is None:
        dat = os.path.join(vaultpath.vault_path("dat_study"), "Gw.dat")
    if not os.path.isfile(dat):
        LEDGER.skip("everything that needs the archive (sections 4-8)",
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
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
