"""The Stripped props chunk: read and write `0x10000004`.

The last chunk `stripbuild.py` had to borrow, and the one that matters most,
because props is where OBJECTS live. FINDINGS 34 makes it a hard gate -- no
props object, no navmesh -- so every map this toolkit built up to rung E10
carried ArenaNet's twelve-byte props chunk and could not have a single tree,
wall, door or portal standing on it.

    blob = ...                        # chunk 0x10000004 out of a map's partner row
    sp   = StrippedProps.decode(blob)
    assert sp.encode() == blob        # 349 of 349 retail maps

WHY THE EARLIER SURVEY FOUND NOTHING, because it is the interesting part.
`studies/customarea/PROPS.md` reported 342 distinct sizes over 349 maps and no
framing law: `9 + n*k` and `12 + n*k` fire 0/349 for every stride to 200. Both
of its readings were wrong in the same way -- **the record is VARIABLE LENGTH**,
so no fixed stride could ever have closed, and the count it tested was read one
byte late (a u32 at +5, straddling the tag byte, which is why it came out as
262144 on a chunk holding no props at all).

THE LAYOUT. A tag pipeline, like the terrain and path chunks, but with a COUNT
where terrain has a SIZE, and with a per-tag header width.

    u32 signature 0x39583392
    u8  version 17
    u8 0   u16 n     n prop records, each 20 + 4*points bytes:
                     +0x00 u16 model
                     +0x02 f32 x, y, z             (UNALIGNED -- odd offsets)
                     +0x0E u8  rot[0]              \ INFERRED packed rotation
                     +0x0F u8  rot[1]              |
                     +0x10 u8  rot[2]              /
                     +0x11 u8  scale               INFERRED
                     +0x12 u8  flags
                     +0x13 u8  points
                     (i16 dx, i16 dy) * points -- an outline, PROP-LOCAL
    u8 4   u16 n     n * {u16 value, u16 prop}
    u8 6   u8 zero, u16 n   n * {u16 value, u16 prop}      (optional)
    u8 255           terminator, and the last byte of the chunk

The floats sit at ODD offsets, which is why byte-phase guessing was ambiguous
from a hexdump, and the outline points are offsets from the prop's own
position: the client sign-extends each and adds `x` and `y` back
(`0x0073DF4F`, `0x0073DF67`) before handing the pairs on.

HOW EACH OF THOSE WAS PINNED, because a walk that closes is not by itself an
argument -- a tolerant walk closes on anything.

  * **The stride came from an oracle in another chunk.** Slide a window over
    the raw bytes and keep every offset whose float pair lands inside the map
    RECT, which lives in Map Parameters `0x1000000C` and which nothing here
    reads. The gap histogram over twelve maps is 49.1% gap-4 and 40.9% gap-16,
    alternating -- two in-rect pairs per record, 4 + 16 = **20** -- and the
    first hit is at offset **10** in all twelve, which is what puts a u16 in
    front of the floats.
  * **Tag 6's extra header byte was forced by the data.** Read as
    `{u8 tag, u16 count}` its count came out 0, 256, 512, 768 ... a multiple of
    256 every time, i.e. the low byte was always zero. One more byte moves it
    into place, and that is also exactly what makes the corpus's 16-byte chunk
    close: `06 00 00 00 FF` is tag, word, count 0, terminator.
  * **Tag 6's stride is uniquely determined.** 4 closes 349/349; 1, 2, 6, 8,
    12, 16 and 20 all close 200/349 -- the maps whose tag-6 count is zero, where
    the stride cannot matter. The 149 maps with a non-zero count are the
    measurement.
  * **The alignment is uniquely determined too.** Putting the model u16 at the
    END of the record and giving tag 0 a five-byte header shifts section 0 by
    exactly two bytes and is otherwise self-consistent; it closes for **0 of
    349**. `test_props.py` keeps that rival as a control.
  * **Tags 4 and 6 index the prop array**, and the corpus had 17,002 chances to
    say otherwise: 6,355 tag-4 references and 10,647 tag-6 references all land
    below their map's prop count, none outside. That is why `decode` refuses an
    out-of-range reference instead of carrying it.

THE CLIENT AGREES, and it was read AFTERWARDS, from build 38797. Everything
above came out of the archive alone; the disassembly is a second witness that
could have refuted it and did not. It also settles one thing the corpus cannot
and corrects the chain `studies/customarea/PROPS.md` was following:

  * **PROPS.md traced the wrong reader.** `s_chunkInfo[0x04].load = 0x00712200`
    parses the BLOATED chunk `0x20000004`, whose sections are
    `{u8 tag, u32 size}`. The Stripped chunk is parsed by
    `.bloat = 0x00712280` -> `0x00738AA0` -> **`0x0073E260`**, a different
    pipeline with one-byte tag headers. Following the load path could never have
    produced a framing that fits these bytes.
  * **The two pipelines share one tag reader, `0x0073E410`, and its `fmt`
    argument picks the header width** -- 5 bytes for the Bloated stream, 1 byte
    for the Stripped one (dispatch at `0x0073E433`).
  * **Tag 4's count IS a u16**: `0x0073E1A6 movzx esi, word ptr [eax]`. The
    corpus cannot decide this -- its largest tag-4 table is 81 entries -- so
    `test_props.py` asserts the ambiguity rather than the answer, and this line
    is why the module reads it as a u16 anyway.
  * **Tag 6's second byte must be ZERO**, `0x0073D8D3 cmp byte ptr [eax], 0`.
    It is a validated field, not padding, and `decode` refuses a non-zero one.
  * **The client's version gate accepts 0x11 AND 0x12** (`0x0073E224` /
    `0x0073E228`). The corpus is 0x11 on 349/349 and this module refuses 0x12 --
    deliberately, and see `Undecodable`'s message: no version branch was found
    in the framing, but "probably the same" is a guess and this repository does
    not make those.
  * **Tag 6 is optional because the reader SAVES AND RESTORES the cursor**
    (`0x0073D891` / `0x0073D8A2`). The shared reader advances past the tag byte
    *before* comparing it, so a stage that may not match has to back out by
    hand. That is why the 12-byte chunk parses: `FF` fails tag 6 without
    consuming anything and stage 7 then matches it. `refs6 is None` is that
    branch, and it is read out of the code rather than fitted to the file.
  * **`model` is a filename index into chunk `0x21000004`**, not a global id
    (`0x0073DE0E`) -- which is why it does not index tag 4 and why its range is
    0..439 pooled. Resolving it to an actual model is the same commit-the-id
    pattern CLAUDE.md already requires.
  * **The rotation and scale bytes have formulas**: each angle byte is
    `b * 2*pi/256` and the scale byte is `b * (255/128)/256 + 1/128`, from the
    doubles at `0x00949D00` (256.0), `0x00946E80` (2*pi), `0x00A70340`
    (1.9921875) and `0x00953AB0` (0.0078125). So scale runs [1/128, ~1.992] in
    256 steps. This module stores the BYTES, which is what the file holds; the
    formulas are recorded here so a caller can place a prop at a real angle.

THE CROSS-STREAM ORACLE, which is the strongest single result and belongs to
the client-side read rather than to this module. The BLOATED props record is 48
bytes with an 8-byte ring point (`0x0073D453`, `0x0073D4D9`) where the Stripped
one is 20 and 4, and the compiler derives one from the other. So the Bloated
tag-0 section's declared size is predictable from the STRIPPED input alone:

    bloated_tag0_size == 2 + 48 * props + 8 * outline_points

**349 of 349, zero mismatches.** Neither codec can force that -- it predicts a
u32 in a stream this module never opens.

WHAT IS STILL NOT KNOWN, stated so nobody quotes this module for more than it
did. The three `rot` bytes and `scale` are named from the client's arithmetic --
they are `fild`-scaled and fed to `0x0073B4C0`, which fills two 12-byte vectors
-- and that reading is INFERRED, not measured. Their WIDTHS are measured: four
separate byte reads at four addresses. The corpus agrees with the reading
without confirming it: `scale` is 0x7F on 35,593 of 285,670 props and the rot
bytes are zero on 180,391. The `value` u16 of tags 4 and 6 recurs across maps,
so those are ids rather than per-map hashes -- not measured. The u16 at +0x00 is
NOT an index into tag 4 (measured, both ways: 209,960 of 285,670 land outside).

NOTHING DECLARED IS STORED. Every count and every point total is re-derived on
encode from the length of the list it describes, so a byte-identical re-encode
of 349 maps is 349 assertions about the derivation rather than 349 comparisons
of a replayed number with itself. That distinction is not hypothetical here:
`test_mapfile.py` and `test_pathchunk.py` each caught a memcpy that printed a
perfect headline, and `test_props.py` builds the same saboteur.
"""

import struct

SIGNATURE = 0x39583392
VERSION = 17

TAG_PROPS = 0
TAG_REFS4 = 4
TAG_REFS6 = 6
TERMINATOR = 0xFF

#: The section order every retail map uses. Tag 6 is optional -- 262 of 349
#: maps carry it -- and the other three are on all 349. Deviations are refused
#: rather than replayed, so decoding all 349 is what proves the order.
#:
#: OPTIONAL MEANS TAG 6 AND NOTHING ELSE, and this cost a correction. Only its
#: stage saves and restores the cursor on a mismatch (0x0073D891 / 0x0073D8A2);
#: tags 0, 4 and 255 return 0, which aborts the parse. The shared reader also
#: advances the cursor BEFORE comparing the tag, so ORDER is forced by the same
#: mechanism as presence. A chunk missing tag 0 or tag 4 fails silently in the
#: worst way -- no props object, and the Path bloat gate at 0x00712678 then
#: emits no navmesh and no assert -- so `decode` refuses it here instead.
ORDER = (TAG_PROPS, TAG_REFS4, TAG_REFS6)

PROP_FIXED = 20                 # model(2) xyz(12) rot(3) scale flags points
REF_STRIDE = 4                  # {u16 value, u16 prop}
MAX_COUNT = 0xFFFF
MAX_POINTS = 0xFF

_HDR = struct.Struct("<IB")
_PROP = struct.Struct("<HfffBBBBBB")   # model, xyz, rot[3], scale, flags, n
_REF = struct.Struct("<HH")


class Undecodable(ValueError):
    """The bytes are not a props chunk we understand.

    Raised rather than resynced. An unknown tag in a tag pipeline is not a
    recoverable hiccup -- the cursor is already somewhere arbitrary, and the
    next plausible-looking record is fiction.
    """


class Prop:
    """One placed object: where it stands, what model, and its footprint."""

    __slots__ = ("model", "x", "y", "z", "rot", "scale", "flags", "outline")

    def __init__(self, model, x, y, z, rot=(0, 0, 0), scale=0x7F, flags=0,
                 outline=()):
        self.model = model
        self.x = x
        self.y = y
        self.z = z
        self.rot = tuple(int(v) for v in rot)
        self.scale = scale
        self.flags = flags
        self.outline = tuple((int(a), int(b)) for a, b in outline)
        if len(self.rot) != 3:
            raise ValueError(f"rot is three bytes, got {len(self.rot)}")

    @property
    def points(self):
        """Derived, never stored. The file's count is checked against this."""
        return len(self.outline)

    @property
    def size(self):
        return PROP_FIXED + REF_STRIDE * self.points

    @property
    def closed(self):
        """Does the outline come back to its first point?

        True for 37,505 of the 37,548 retail props that have one. The 43 that
        do not are real and are reported by `test_props.py` rather than being
        rounded away -- an invariant with counterexamples is not an invariant.
        """
        return bool(self.outline) and self.outline[0] == self.outline[-1]

    def __repr__(self):
        return (f"Prop(model={self.model}, at=({self.x:.1f}, {self.y:.1f}, "
                f"{self.z:.1f}), rot={self.rot}, scale={self.scale}, "
                f"flags={self.flags:#04x}, points={self.points})")


class PropRef:
    """A `{u16 value, u16 prop}` entry of tag 4 or tag 6.

    `prop` indexes the prop array; `value` is an id whose meaning is UNVERIFIED.
    """

    __slots__ = ("value", "prop")

    def __init__(self, value, prop):
        self.value = value
        self.prop = prop

    def __eq__(self, other):
        return (isinstance(other, PropRef) and self.value == other.value
                and self.prop == other.prop)

    def __repr__(self):
        return f"PropRef(value={self.value}, prop={self.prop})"


class StrippedProps:
    """A decoded `0x10000004` payload.

    `refs6 is None` means the map carries no tag-6 section at all, which is a
    different file from one carrying an empty tag 6: 87 maps have no tag 6 and
    114 have it with a count of zero. Collapsing the two would lose four bytes
    on the re-encode of 114 maps, so the distinction is kept.
    """

    __slots__ = ("props", "refs4", "refs6", "tag6_word", "version", "signature")

    def __init__(self, props=(), refs4=(), refs6=None, tag6_word=0,
                 version=VERSION, signature=SIGNATURE):
        self.props = list(props)
        self.refs4 = list(refs4)
        self.refs6 = None if refs6 is None else list(refs6)
        self.tag6_word = tag6_word
        self.version = version
        self.signature = signature

    # -- decode --------------------------------------------------------------

    @classmethod
    def decode(cls, payload):
        payload = bytes(payload)
        if len(payload) < _HDR.size + 1:
            raise Undecodable(
                f"props chunk is {len(payload)} bytes, too short to hold a "
                f"header and a terminator")
        signature, version = _HDR.unpack_from(payload, 0)
        if signature != SIGNATURE:
            raise Undecodable(
                f"props signature is 0x{signature:08X}, not 0x{SIGNATURE:08X}")
        if version != VERSION:
            raise Undecodable(
                f"props version is {version}, not {VERSION}. The client's own "
                f"gate accepts 0x11 AND 0x12 (0x0073E224 / 0x0073E228) and the "
                f"corpus is 0x11 on 349 of 349, so 0x12 is a version we have "
                f"never seen. No version branch was found in the framing, but "
                f"'probably the same' is a guess -- refusing is the honest "
                f"answer until a 0x12 file exists to measure.")

        props, refs4, refs6, tag6_word = [], [], None, 0
        seen = []
        off = _HDR.size
        while True:
            if off >= len(payload):
                raise Undecodable(
                    f"ran off the end at {off} without a 0x{TERMINATOR:02X} "
                    f"terminator")
            tag = payload[off]
            if tag == TERMINATOR:
                if off != len(payload) - 1:
                    raise Undecodable(
                        f"terminator at {off} but the chunk is "
                        f"{len(payload)} bytes: {len(payload) - 1 - off} "
                        f"bytes of tail nobody accounted for")
                break
            if tag not in ORDER:
                raise Undecodable(
                    f"unknown props tag {tag} at {off}; known tags are "
                    f"{ORDER} and the walk cannot resync past one")
            if seen and ORDER.index(tag) <= ORDER.index(seen[-1]):
                raise Undecodable(
                    f"props tag {tag} at {off} follows tag {seen[-1]}; the "
                    f"order is {ORDER}")
            seen.append(tag)

            if tag == TAG_REFS6:
                if off + 4 > len(payload):
                    raise Undecodable(f"truncated tag-6 header at {off}")
                tag6_word = payload[off + 1]
                if tag6_word != 0:
                    raise Undecodable(
                        f"tag 6's second byte is {tag6_word} at {off + 1}, and "
                        f"the client requires 0 (`cmp byte ptr [eax], 0` at "
                        f"0x0073D8D3). Retail is 0 on all 262 maps that carry "
                        f"the section.")
                count = struct.unpack_from("<H", payload, off + 2)[0]
                off += 4
            else:
                if off + 3 > len(payload):
                    raise Undecodable(f"truncated tag-{tag} header at {off}")
                count = struct.unpack_from("<H", payload, off + 1)[0]
                off += 3

            if tag == TAG_PROPS:
                for i in range(count):
                    if off + PROP_FIXED > len(payload):
                        raise Undecodable(
                            f"prop {i} of {count} runs off the end at {off}")
                    (model, x, y, z, r0, r1, r2, scale, flags,
                     points) = _PROP.unpack_from(payload, off)
                    end = off + PROP_FIXED + REF_STRIDE * points
                    if end > len(payload):
                        raise Undecodable(
                            f"prop {i}'s {points}-point outline runs off the "
                            f"end at {off}")
                    outline = []
                    for p in range(points):
                        outline.append(struct.unpack_from(
                            "<hh", payload, off + PROP_FIXED + REF_STRIDE * p))
                    props.append(Prop(model, x, y, z, (r0, r1, r2), scale,
                                      flags, outline))
                    off = end
            else:
                end = off + REF_STRIDE * count
                if end > len(payload):
                    raise Undecodable(
                        f"tag-{tag} table of {count} entries runs off the end "
                        f"at {off}")
                table = [PropRef(*_REF.unpack_from(payload, off + i * REF_STRIDE))
                         for i in range(count)]
                if tag == TAG_REFS4:
                    refs4 = table
                else:
                    refs6 = table
                off = end

        missing = [t for t in (TAG_PROPS, TAG_REFS4) if t not in seen]
        if missing:
            raise Undecodable(
                f"props chunk is missing mandatory tag(s) {missing}. Only tag "
                f"6 is optional -- it alone saves and restores the cursor on a "
                f"mismatch (0x0073D891 / 0x0073D8A2). Tags 0 and 4 return 0, "
                f"which aborts the whole parse, so no props object is built "
                f"and the Path bloat gate at 0x00712678 then kills the navmesh "
                f"WITH NO ASSERT. Retail carries both on 349 of 349.")

        self = cls(props, refs4, refs6, tag6_word, version, signature)
        self.check_references()
        return self

    # -- invariants ----------------------------------------------------------

    def check_references(self):
        """Every reference must name a prop that exists.

        Retail agrees 17,002 times out of 17,002 -- 6,355 tag-4 entries and
        10,647 tag-6 -- so this cannot fire on ArenaNet's own files. It fires on
        OURS, which is the point: a table pointing past the array is the easiest
        mistake to make when authoring and the hardest to see in a hexdump.
        """
        n = len(self.props)
        for tag, table in ((TAG_REFS4, self.refs4), (TAG_REFS6, self.refs6)):
            for i, ref in enumerate(table or ()):
                if not 0 <= ref.prop < n:
                    raise Undecodable(
                        f"tag-{tag} entry {i} names prop {ref.prop}, but the "
                        f"chunk holds {n} props")

    # -- encode --------------------------------------------------------------

    def encode(self):
        """Rebuild the payload. Every count is re-derived, never replayed."""
        self.check_references()
        out = bytearray(_HDR.pack(self.signature, self.version))

        if len(self.props) > MAX_COUNT:
            raise ValueError(
                f"{len(self.props)} props will not fit a u16 count "
                f"(max {MAX_COUNT})")
        out.append(TAG_PROPS)
        out += struct.pack("<H", len(self.props))
        for i, p in enumerate(self.props):
            if p.points > MAX_POINTS:
                raise ValueError(
                    f"prop {i} has {p.points} outline points; the count is a "
                    f"u8, so {MAX_POINTS} is the ceiling")
            out += _PROP.pack(p.model, p.x, p.y, p.z, p.rot[0], p.rot[1],
                              p.rot[2], p.scale, p.flags, p.points)
            for dx, dy in p.outline:
                out += struct.pack("<hh", dx, dy)

        out.append(TAG_REFS4)
        out += struct.pack("<H", len(self.refs4))
        for ref in self.refs4:
            out += _REF.pack(ref.value, ref.prop)

        if self.refs6 is not None:
            if self.tag6_word != 0:
                raise ValueError(
                    f"tag 6's second byte must be 0, not {self.tag6_word}; the "
                    f"client compares it at 0x0073D8D3")
            out.append(TAG_REFS6)
            out.append(self.tag6_word)
            out += struct.pack("<H", len(self.refs6))
            for ref in self.refs6:
                out += _REF.pack(ref.value, ref.prop)

        out.append(TERMINATOR)
        return bytes(out)

    # -- authoring -----------------------------------------------------------

    @classmethod
    def minimal(cls):
        """The smallest props chunk the format can express: no props at all.

        Twelve bytes, and byte-identical to the smallest chunk in the archive
        (row 46197). Authored from nothing -- no archive, no donor -- which is
        what makes it a check rather than a copy.
        """
        return cls(props=(), refs4=(), refs6=None)

    def __len__(self):
        return len(self.props)

    def __repr__(self):
        six = "none" if self.refs6 is None else f"{len(self.refs6)}"
        return (f"StrippedProps({len(self.props)} props, refs4="
                f"{len(self.refs4)}, refs6={six})")


def decode(payload):
    return StrippedProps.decode(payload)


def _main(argv=None):
    import argparse
    import os
    import sys

    sys.path.insert(0, os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")))
    from toolkit.mapdata import archive as ar
    from toolkit.mapdata import mapchunks as mc
    from toolkit.mapdata import mapfile as mfile
    from toolkit import vaultpath

    ap = argparse.ArgumentParser(description="Read a map's Stripped props.")
    ap.add_argument("--dat", default=None)
    ap.add_argument("--row", type=int, default=None)
    ap.add_argument("--limit", type=int, default=8)
    args = ap.parse_args(argv)

    dat = args.dat or os.path.join(vaultpath.require_dir("dat_study"), "Gw.dat")
    a = ar.Archive(dat)
    idx = mc.MapIndex(a)
    pairs = sorted(idx.pairs, key=lambda hp: hp[0].index)
    if args.row is not None:
        pairs = [hp for hp in pairs if hp[1].index == args.row]
    ok = bad = 0
    for _head, partner in pairs[:args.limit or None]:
        try:
            m = mfile.MapFile.decode(a.read(partner), strict=False)
            ch = m.find(0x10000004)
            blob = ch.payload()
            sp = StrippedProps.decode(blob)
        except Exception as exc:                             # noqa: BLE001
            print(f"row {partner.index:6d}  {type(exc).__name__}: {exc}")
            bad += 1
            continue
        same = sp.encode() == blob
        ok += 1 if same else 0
        bad += 0 if same else 1
        poly = sum(1 for p in sp.props if p.points)
        print(f"row {partner.index:6d} {len(blob):7d}B  {sp}  "
              f"outlines {poly:5d}  re-encode "
              f"{'IDENTICAL' if same else 'DIFFERS'}")
    print(f"{ok} identical, {bad} not")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_main())
