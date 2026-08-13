r"""Check the Environment codec: decode a retail `0x10000009`, encode it back.

THE HEADLINE IS 349 OF 349 BYTE-IDENTICAL, and it is the weakest claim here. The
codec keeps each record's raw bytes (the loader itself stores tag0/1/3/5/6/8
records opaquely and decodes none of their interiors), so a codec that kept the
whole blob would round-trip everything and understand nothing. What the codec
must NOT store is the section COUNTS -- every one is re-derived from its record
list on encode, `tag8` has none, and `tag12`'s polygon count is recomputed by
walking. So section 2 BUILDS the saboteur that stashes and replays the counts,
runs it, and requires it to pass the round trip while FAILING the mutation
control that grows a section and demands the emitted count move -- read back by a
walker written here out of `int.from_bytes`.

THE FRAMING CORRECTIONS ARE WHY THIS IS A CODEC AND NOT A HEXDUMP. The header is
8 bytes (a first corpus pass guessed 5); the tag5-width `flag` is the header word
at offset 6, NOT tag0's count (they disagree in 168 of 349 maps); and tag8 is a
real 17-byte section, not part of tag7's tail. Each is a thing a wrong reading
gets wrong on some map, and section 3 runs the whole corpus so it cannot hide.

THE ORACLE COMES FROM A CHUNK THIS CODEC NEVER READS. Every dependency-reference
field -- tag0@8, tag4, tag5's four slots, tag6@53/@55 -- is either 0xFFFF or an
index below the length of the sibling Dependencies chunk `0x11000009`. If the
record framing were off, these would be garbage indices past the end. It is
**0 of 5,897 out of bounds**; the same fields read ONE byte earlier blow the
bound 5,087 times. Section 4 measures both.

A MISSING VAULT IS A FAILURE, NOT A SKIP. Sections 0-2 run without an archive,
but a run with no vault has measured nothing about ArenaNet's bytes, and the
floor turns that into the FAIL it is.

    python toolkit/mapdata/test_envchunk.py
    python toolkit/mapdata/test_envchunk.py --sample 30
    python toolkit/mapdata/test_envchunk.py --all      # all 349 maps
"""

import argparse
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive  # noqa: E402
from mapchunks import MapIndex, decode_dependencies  # noqa: E402
import mapfile as mfile  # noqa: E402
import envchunk as env  # noqa: E402
import strippedterrain as stx  # noqa: E402
from envchunk import (EnvChunk, Section, Undecodable,  # noqa: E402
                      SIGNATURE, VERSION, TERMINATOR, ORDER, GLOBAL_SIZE,
                      TAG_GLOBAL, TAG_FOG, TAG_ZONES, TAG_POLYGONS, TAG_WATER,
                      SELECTOR_TAGS, SUN_TURN)
import checks  # noqa: E402
import vaultpath  # noqa: E402

ENV_CHUNK = 0x10000009
ENV_DEPS_CHUNK = 0x11000009
NONE = 0xFFFF

# MEASURED 2026-08-13 over vault/dat_study/Gw.dat, all 349 maps. Population
# assertions that stop an empty sample or bad row filter from going green.
CORPUS_MAPS = 349
CORPUS_FLAG1 = 257              # tag5 records are 16 B
CORPUS_FLAG0 = 92              # tag5 records are 15 B
CORPUS_TAG12_MAPS = 104        # maps carrying the optional polygon section
CORPUS_ZONES = 2617
CORPUS_FOG = 1745
CORPUS_DEP_REFS = 5897         # dep-reference fields, 0 out of bounds
CORPUS_SHIFT_VIOL = 5087       # same fields read one byte early: violations
# The sun oracle. NEAR is the claim to quote: it is ROUNDING-INDEPENDENT, and
# EXACT is not. `b = 48` maps to exactly 190.5, and two maps carry it -- Python's
# banker's rounding sends that to 190 and round-half-up to 191, and one of the two
# maps really does store 191. So the exact count is 307 under `round()` and 308
# under `floor(x+0.5)`, which is why the test uses the latter (what a C-era
# `(int)(x + 0.5)` does) and states the tie rather than picking a number quietly.
CORPUS_SUN_EXACT = 308         # maps where tag8's sun byte predicts terrain's
CORPUS_SUN_NEAR = 313          # ... within one terrain quantum (0.354 deg)
CORPUS_ZONE_SLOTS = 20936      # zone selector reads, 0 out of bounds

# The Stripped terrain chunk's angle_index sits at a fixed offset: the 5-byte
# header, the tag-0 byte, then 4 into tag 0's body. Computed from the terrain
# module's own constants rather than written as 10, so a header change there
# breaks this loudly instead of silently reading the wrong byte.
TERRAIN_CHUNK = 0x10000002
TERRAIN_ANGLE_OFF = stx.HEADER.size + 1 + 4
# (2*pi/256) / (282.74334716796875/45720) -- the ratio between the two chunks'
# quantisations of the same authored angle. Exactly 127/32.
SUN_RATIO = 127.0 / 32.0

# The dep-reference fields, as (tag, (offsets,)). ALIGNED is the codec's reading;
# SHIFT reads each one byte earlier and must break the bound. tag0@8, tag4@0,
# tag5 slots @1/3/5/7, tag6 @53/55.
ALIGNED_REFS = ((0, (8,)), (4, (0,)), (5, (1, 3, 5, 7)), (6, (53, 55)))
SHIFT_REFS = ((0, (7,)), (4, (0,)), (5, (0, 2, 4, 6)), (6, (52, 54)))

# FLOOR: 25, MEASURED from a green default run 2026-08-13 (which executes 25; a
# --all run executes 33, adding eight corpus-total checks). Sections 0-2 score 15
# and need no vault, so a vault-less run stops at 15 and the floor turns that into
# the FAIL it is. The floor equals what a sampled run produces, which is its
# mandatory core.
LEDGER = checks.Ledger("test_envchunk", floor=25)
check = checks.adopt(LEDGER)


def refuses(blob):
    try:
        EnvChunk.decode(blob)
        return False
    except Undecodable:
        return True
    except Exception:  # noqa: BLE001
        return False


def minimal():
    """The smallest valid env: one record in every mandatory array, no zones.

    Shaped like the 73 retail maps that carry no zones -- every aspect array at
    count 1. Record interiors are zero placeholders; this is a FRAMING fixture,
    not an authored environment.
    """
    secs = []
    sizes = {0: 10, 1: 6, 2: 19, 3: 8, 4: 2, 5: 15, 6: 57, 7: 4, 9: 32, 11: 5}
    for tag in ORDER:
        if tag == TAG_POLYGONS:
            continue
        if tag == TAG_GLOBAL:
            secs.append(Section(TAG_GLOBAL, [bytes(GLOBAL_SIZE)]))
        elif tag == TAG_ZONES:
            secs.append(Section(TAG_ZONES, []))            # no zones
        else:
            secs.append(Section(tag, [bytes(sizes[tag])]))  # one placeholder
    return EnvChunk(VERSION, flag=0, sections=secs)


class Sabotage(EnvChunk):
    """A codec that STORES every section count and replays it. It round-trips
    every real file and only diverges when a record list is mutated -- the
    mutation control below."""

    __slots__ = ("_counts",)

    @classmethod
    def decode(cls, blob):
        base = EnvChunk.decode(blob)
        obj = cls(base.version, base.flag, base.sections)
        obj._counts = {}
        off = 8
        for s in base.sections:
            off += 1
            if s.tag == TAG_GLOBAL:
                off += GLOBAL_SIZE
                continue
            obj._counts[s.tag] = struct.unpack_from("<H", blob, off)[0]
            off += 2 + sum(len(r) for r in s.records)
        return obj

    def encode(self):
        out = bytearray(struct.pack("<IHH", SIGNATURE, self.version, self.flag))
        for s in self.sections:
            out.append(s.tag)
            if s.tag == TAG_GLOBAL:
                out += s.records[0]
                continue
            out += struct.pack("<H", self._counts[s.tag])   # REPLAY, not derive
            for r in s.records:
                out += r
        out.append(TERMINATOR)
        return bytes(out)


def walk_count(blob, tag):
    """The u16 count declared for `tag`, read independently of the module."""
    off = 8
    t5 = 16 if struct.unpack_from("<H", blob, 6)[0] >= 1 else 15
    fixed = {0: 10, 1: 6, 2: 19, 3: 8, 4: 2, 6: 57, 7: 4, 9: 32, 11: 5}
    for t in ORDER:
        if off >= len(blob) or blob[off] != t:
            continue
        off += 1
        if t == TAG_GLOBAL:
            off += GLOBAL_SIZE
            continue
        cnt = int.from_bytes(blob[off:off + 2], "little")
        if t == tag:
            return cnt
        off += 2
        if t == TAG_POLYGONS:
            for _ in range(cnt):
                off += 3 + blob[off] * 8
        else:
            off += cnt * (t5 if t == 5 else fixed[t])
    return None


def section0():
    print("\n-- 0. refusals --")
    good = minimal().encode()
    check(EnvChunk.decode(good).flag == 0, "minimal chunk decodes")
    check(refuses(b"\x00\x00\x00\x00" + good[4:]), "bad signature refused")
    check(refuses(good[:-1]), "missing terminator refused")
    # drop a mandatory section (tag2 fog) -> ascending order breaks
    ec = minimal()
    ec.sections = [s for s in ec.sections if s.tag != TAG_FOG]
    check(refuses(ec.encode()), "a missing mandatory section is refused")


def section1():
    print("\n-- 1. authored round trip + typed views --")
    ec = minimal()
    # author a fog record and a zone into the placeholder chunk
    ec.section(TAG_FOG).records = [struct.pack("<BBBIIii", 104, 140, 179,
                                               6200, 22500, 40, -1000)]
    ec.section(TAG_ZONES).records = [struct.pack("<8HiiII", 0, 0, 0, 1, 0, 0, 0,
                                                 0, 9082, -11237, 195, 602)]
    blob = ec.encode()
    back = EnvChunk.decode(blob)
    check(back.encode() == blob, "authored chunk round-trips")
    fog = back.fog()[0]
    check(fog[:3] == (104, 140, 179) and fog[3] < fog[4],
          "fog colour + near<far read back", f"{fog}")
    z = back.zones()[0]
    check(z[0] == (0, 0, 0, 1, 0, 0, 0, 0) and z[1] == 9082,
          "zone sel[8] + position read back", f"{z}")
    check(walk_count(blob, TAG_ZONES) == 1,
          "independent walker reads one zone")
    check(back.global_env() == bytes(GLOBAL_SIZE),
          "tag8 global record is 17 bytes, carried")


def section2():
    print("\n-- 2. saboteur vs mutation control --")
    ec = minimal()
    ec.section(TAG_ZONES).records = [bytes(32), bytes(32)]   # two zones
    blob = ec.encode()

    sab = Sabotage.decode(blob)
    check(sab.encode() == blob, "saboteur passes the round trip (as designed)")

    # grow the zone list; real codec must move the count, saboteur must not
    grow = EnvChunk.decode(blob)
    grow.section(TAG_ZONES).records.append(bytes(32))
    real = grow.encode()
    check(walk_count(real, TAG_ZONES) == 3, "real codec re-derives zone count 3")
    check(len(real) == len(blob) + 32, "real codec grows by one 32-B zone")

    sab_grow = Sabotage.decode(blob)
    sab_grow.section(TAG_ZONES).records.append(bytes(32))
    sab_out = sab_grow.encode()
    check(walk_count(sab_out, TAG_ZONES) == 2,
          "saboteur replays the stale count 2 -- the bug the control exposes")
    check(walk_count(real, TAG_ZONES) != walk_count(sab_out, TAG_ZONES),
          "the mutation control SEPARATES the real codec from the memcpy")
    # tag8 carries no count field at all
    check(walk_count(blob, TAG_GLOBAL) is None,
          "tag8 has no count field to store")


def read_corpus(ar, mi, picks):
    """Each map ONCE: the env payload, its dep count, and the terrain angle byte.

    The terrain byte is read raw rather than decoded -- `StrippedTerrain.decode`
    would huffman-decode the whole height field for one byte, turning a 30 s
    sweep into a 20 minute one, and section 5 only needs the byte.
    """
    out = []
    for head in picks:
        m = mfile.MapFile.decode(ar.read(mi.partner(head)), strict=False)
        d = m.find(ENV_DEPS_CHUNK)
        ndeps = len(list(decode_dependencies(d.payload()).file_ids)) if d else 0
        t = m.find(TERRAIN_CHUNK)
        angle = t.payload()[TERRAIN_ANGLE_OFF] if t else None
        out.append((mi.partner(head).index, m.find(ENV_CHUNK).payload(),
                    ndeps, angle))
    return out


def refs(ec, spec):
    out = []
    for tag, offs in spec:
        s = ec.section(tag)
        if not s:
            continue
        for r in s.records:
            for o in offs:
                if o + 2 <= len(r):
                    out.append(struct.unpack_from("<H", r, o)[0])
    return out


def section3(corpus):
    print(f"\n-- 3. {len(corpus)} retail maps: decode, re-encode, compare --")
    same = diff = 0
    flag1 = fog = zones = tag12 = 0
    versions = set()
    global_ok = True
    for _row, blob, _n, _a in corpus:
        ec = EnvChunk.decode(blob)
        if ec.encode() == blob:
            same += 1
        else:
            diff += 1
        versions.add(ec.version)
        flag1 += 1 if ec.flag >= 1 else 0
        for f in ec.fog():
            fog += 1
        zones += len(ec.zones())
        if ec.section(TAG_POLYGONS) is not None:
            tag12 += 1
        g = ec.global_env()
        if g is None or len(g) != GLOBAL_SIZE:
            global_ok = False
    check(diff == 0, f"{same} of {len(corpus)} re-encode byte-identically",
          f"{diff} differ")
    check(versions == {VERSION}, "every version is 16", f"{sorted(versions)}")
    check(global_ok, "every map's tag8 global record is exactly 17 bytes")
    complete = len(corpus) == CORPUS_MAPS
    if complete:
        check(flag1 == CORPUS_FLAG1,
              f"{CORPUS_FLAG1} maps have flag>=1 (16-B tag5)", f"{flag1}")
        check(zones == CORPUS_ZONES, f"corpus zone total == {CORPUS_ZONES}",
              f"{zones}")
        check(tag12 == CORPUS_TAG12_MAPS,
              f"{CORPUS_TAG12_MAPS} maps carry the polygon section", f"{tag12}")
    else:
        LEDGER.skip("corpus population totals",
                    f"sample of {len(corpus)} < {CORPUS_MAPS}; run --all")
    return complete


def section4(corpus, complete):
    print("\n-- 4. cross-chunk oracle: dep references bounded by 0x11000009 --")
    tot = viol = s_tot = s_viol = 0
    for _row, blob, ndeps, _a in corpus:
        ec = EnvChunk.decode(blob)
        for v in refs(ec, ALIGNED_REFS):
            tot += 1
            if v != NONE and v >= ndeps:
                viol += 1
        for v in refs(ec, SHIFT_REFS):
            s_tot += 1
            if v != NONE and v >= ndeps:
                s_viol += 1
    if tot == 0:
        LEDGER.skip("dep-reference oracle", "no references in this sample")
        return
    check(viol == 0,
          f"{tot} dep references, 0 out of bounds of the sibling dep list",
          f"{viol} violations")
    check(s_viol > viol,
          "the same fields read one byte early blow the bound -- the framing "
          "is measured, not chosen", f"shifted {s_viol} vs aligned {viol}")
    if complete:
        check(tot == CORPUS_DEP_REFS,
              f"corpus dep-reference total == {CORPUS_DEP_REFS}", f"{tot}")
        check(s_viol == CORPUS_SHIFT_VIOL,
              f"shifted-read violations == {CORPUS_SHIFT_VIOL}", f"{s_viol}")


def section5(corpus, complete):
    """The selector tuples resolve, and the sun byte predicts the OTHER chunk."""
    print("\n-- 5. selector tuples, and the sun byte vs the terrain chunk --")
    slots = bad_slots = 0
    rot_bad = 0
    for _row, blob, _n, _a in corpus:
        ec = EnvChunk.decode(blob)
        counts = [len(ec.section(t).records) if ec.section(t) else 0
                  for t in SELECTOR_TAGS]
        tuples = [ec.default_selectors()] + [z[0] for z in ec.zones()]
        for sel in tuples:
            for i, v in enumerate(sel):
                slots += 1
                if v >= counts[i]:
                    bad_slots += 1
                # control: the slot-to-array assignment rotated by one
                if v >= counts[(i + 1) % len(counts)]:
                    rot_bad += 1
    check(bad_slots == 0,
          f"{slots} selector reads (tag8 + every zone), 0 index past their array",
          f"{bad_slots} out of bounds")
    check(rot_bad > bad_slots,
          "rotating the slot-to-array assignment by one puts selectors out of "
          "bounds -- the mapping is measured, not chosen",
          f"rotated {rot_bad} vs aligned {bad_slots}")

    # every map's default tuple must resolve to a full environment
    resolved = 0
    for _row, blob, _n, _a in corpus:
        ec = EnvChunk.decode(blob)
        got = ec.resolve(ec.default_selectors())
        if len(got) == len(SELECTOR_TAGS):
            resolved += 1
    check(resolved == len(corpus),
          f"{resolved} of {len(corpus)} default tuples resolve to all "
          f"{len(SELECTOR_TAGS)} aspects")

    # THE ORACLE: tag8's sun byte predicts the terrain chunk's own angle index
    exact = near = have = shifted = 0
    for _row, blob, _n, angle in corpus:
        if angle is None:
            continue
        have += 1
        g = EnvChunk.decode(blob).global_env()
        pred = math.floor(g[16] * SUN_RATIO + 0.5)      # round half UP; see above
        if pred == angle:
            exact += 1
        if abs(pred - angle) <= 1:
            near += 1
        # control: the byte beside the sun byte, scaled the same way
        if abs(math.floor(g[15] * SUN_RATIO + 0.5) - angle) <= 1:
            shifted += 1
    if have == 0:
        LEDGER.skip("sun-angle oracle", "no terrain chunks in this sample")
        return
    check(near > have * 0.8,
          f"tag8's sun byte predicts the TERRAIN chunk's angle_index to within "
          f"one quantum on {near} of {have} maps -- two chunks, one authored "
          f"angle", f"exact: {exact}")
    check(shifted < near // 4,
          "the neighbouring byte scaled identically predicts almost nothing "
          "-- it is this byte, not any byte", f"neighbour {shifted} vs sun {near}")
    if complete:
        check(exact == CORPUS_SUN_EXACT,
              f"corpus exact agreement == {CORPUS_SUN_EXACT}", f"{exact}")
        check(near == CORPUS_SUN_NEAR,
              f"corpus within-one-quantum agreement == {CORPUS_SUN_NEAR}",
              f"{near}")
        check(slots == CORPUS_ZONE_SLOTS + CORPUS_MAPS * len(SELECTOR_TAGS),
              "selector-read total matches the measured zone population",
              f"{slots}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=30)
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    section0()
    section1()
    section2()

    try:
        dat = os.path.join(vaultpath.require_dir("dat_study"), "Gw.dat")
    except SystemExit:
        LEDGER.skip("corpus sweep + oracle",
                    "no vault/dat_study/Gw.dat; the floor turns this into a FAIL")
        return LEDGER.verdict()

    with Archive(dat) as ar:
        mi = MapIndex(ar)
        heads = [h for h, _p in mi.pairs]
        picks = heads if args.all else heads[::max(1, len(heads) // args.sample)]
        corpus = read_corpus(ar, mi, picks)
    complete = section3(corpus)
    section4(corpus, complete)
    section5(corpus, complete)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
