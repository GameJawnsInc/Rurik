"""Check the pathing-chunk codec: decode a retail `0x20000008`, encode it back.

THE HEADLINE IS THE ROUND-TRIP -- 349 of 349 maps byte-identical, sampled by
default and complete under `--all`. Everything else in this file exists because
that number is cheap to fake.

THE FAILURE MODE THIS FILE IS BUILT AROUND. A codec that keeps each record's
declared `size` and each plane header's declared counts, and writes them back,
round-trips every file it can walk while understanding nothing. It would print
349 of 349 and be a memcpy. So sections 2 and 6 do not merely assert that
mutations break a file: they decode a chunk, mutate it IN PLACE until an encoded
payload changes LENGTH, and require the emitted size and count fields to have
moved with it -- read back by a walker written here out of `int.from_bytes`,
which imports nothing from the module under test. Mutating in place rather than
replacing an object is deliberate; `test_mapfile.py` records what the weaker
shape let through.

THE NAMED CONTROL. Tag 11's size field is exactly twice the data that follows it
in 11,795 of 11,795 retail planes. An encoder that "fixes" that to the true
length is the single most likely way to get this module wrong, so it is built
here -- as a rewrite of the emitted bytes, which is the same output an encoder
written that way would produce -- and required to differ from retail, on a
retail chunk as well as on ours. The decoder is required to refuse those bytes
coming back the other way.

CONTROLS RUN ON ARENANET'S BYTES, NOT ONLY OURS. Section 2 runs the controls on
a chunk this file builds from nothing (bare machine, no vault). Section 6 runs
the four that matter again on a retail chunk, because a control that only ever
fires on our own bytes is the weaker half of the pair.

A SECOND WITNESS FOR THE DECODE. Section 5 hands the same retail bytes to
`pathmap.PathingMap.from_chunk`, a different parser in a module this rung does
not own, and requires the trapezoid count and every coordinate to agree.
Section 1 makes the synthetic mesh answer that module too: `minimal()` is
encoded, re-parsed by pathmap, and the trapezoid it built has to be walkable.

A MISSING VAULT IS A FAILURE, NOT A SKIP. Sections 0-2 still run and their
checks are still printed, but a run with no archive has measured nothing about
ArenaNet's format, and the floor turns that into the FAIL it is.

    python toolkit/mapdata/test_pathchunk.py
    python toolkit/mapdata/test_pathchunk.py --sample 20
    python toolkit/mapdata/test_pathchunk.py --all     # 349 maps, ~7 minutes
"""

import argparse
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks  # noqa: E402
from mapchunks import MapIndex  # noqa: E402
from pathmap import PathingMap  # noqa: E402
import pathchunk  # noqa: E402
from pathchunk import (Obstacles, PathChunk, Plane, PATHING_CHUNK,  # noqa: E402
                       StrippedPath, STRIPPED_PATHING_CHUNK,
                       child_kind, child_ref)
import checks  # noqa: E402
import vaultpath  # noqa: E402

# MEASURED on this archive 2026-08-11 by a full 349-map sweep. These are
# population assertions, not decoration: they are what stops a wrong row filter
# or an empty sample from printing "3 of 3" and going green.
CORPUS_MAPS = 349
CORPUS_PLANES = 11795
CORPUS_TRAPS = 1032259
CORPUS_CHILDREN = {"xnode": 4462623, "null": 2784573,
                   "ynode": 2125005, "sink": 1457371}

# The STRIPPED population, MEASURED by a full 349-map sweep 2026-08-12. The
# winding split is the load-bearing one: it refutes the claim that retail has a
# boundary winding convention, which `StrippedPath.rect` asserted before anyone
# measured it. 29 boundaries are degenerate (2 points or fewer) and score zero
# area, which is why the three numbers do not sum the way a reader expects.
STRIPPED_CCW = 169
STRIPPED_CW = 151
STRIPPED_MIN_PTS = 1
STRIPPED_MAX_PTS = 131

# The map that refutes E3's input contract, pinned by file id (row 33833 on this
# archive, reported not required). Its whole Stripped pathing chunk is 27 bytes
# holding the single point (-4380.0, -1860.0); its Bloated partner carries 3,437
# trapezoids over 24 planes. 27 bytes cannot encode that mesh.
DEGENERATE_ID = 0x9F5E
DEGENERATE_BYTES = 27
DEGENERATE_TRAPS = 3437

# Kamadan and the smallest complete map in the archive. File ids are content
# keys and travel between copies of the archive; row numbers do not, so the
# rows below are reported, never required.
KAMADAN_ID = 0x345CC
KAMADAN_ROW = 22371
KAMADAN_BYTES = 199130
KAMADAN_PLANES = 39
KAMADAN_TRAPS = 1270
SMALL_ID = 0x22E2C
SMALL_ROW = 46196
SMALL_BYTES = 419
SMALL_GRID = (3, 3)

# Set from a real green run on 2026-08-11: a default run executes 65 checks. 40
# of those run on a bare machine with no vault at all, which is BELOW this floor
# on purpose -- sections 0-2 measure the codec against bytes this file wrote and
# nothing about ArenaNet's format, so a vault-less run is a failure that names
# its shortfall, not a pass. --all adds three sweep-population checks, for 68.
#
# 65 -> 92 on 2026-08-12 with sections 7-9, the STRIPPED chunk 0x10000008 -- the
# compiler's INPUT side, which rung E3 needs authorable and which nothing in this
# tree could read. Section 7 is 16 checks and needs no vault.
LEDGER = checks.Ledger("pathing chunk codec", floor=93)
check = checks.adopt(LEDGER)


# --------------------------------------------------------------------------
# The independent walker. Imports NOTHING from pathchunk: a codec that agrees
# with itself about its own framing has proved nothing, and every size- and
# count-derivation check below is only evidence because this reads the emitted
# bytes with different code. The element sizes are the format's, written out
# here on purpose rather than imported.

_ESZ = {11: 8, 1: 8, 2: 44, 4: 16, 5: 12, 6: 4, 10: 4, 9: 9}
_ORDER = (0, 11, 1, 2, 3, 4, 5, 6, 10, 9)


def u16(b, o):
    return int.from_bytes(b[o:o + 2], "little")


def u32(b, o):
    return int.from_bytes(b[o:o + 4], "little")


def walk_chunk(buf):
    """[(tag, size_field_offset, declared, body_offset)], and where it landed.

    Tolerant on purpose -- a control that perturbs a size field needs to see
    WHERE the walk ended up, not an exception.
    """
    out, p = [], 12
    while p + 5 <= len(buf):
        tag = buf[p]
        size = u32(buf, p + 1)
        out.append((tag, p + 1, size, p + 5))
        p += 5 + size
        if tag == 255:
            break
    return out, p


def walk_planes(buf, base, size):
    """Per plane: its eight header counts and its ten framed sub-records.

    Sub-record lengths come from the COUNTS, which is the only way to walk this
    -- tag 11's declared size is double its data. Returns (planes, landing).
    """
    count = u32(buf, base)
    p, planes = base + 4, []
    for _i in range(count):
        counts, recs = None, []
        for want in _ORDER:
            if p + 5 > base + size:
                return planes, p - base
            tag = buf[p]
            declared = u32(buf, p + 1)
            body = p + 5
            if tag != want:
                return planes, p - base
            if want == 0:
                counts = struct.unpack_from("<8I", buf, body)
                length = 32
            elif want == 3:
                length = 1
            else:
                # header order is poly, edge, trap, x, y, sink, portals,
                # portalTraps -- note portals precedes portalTraps.
                slot = {11: 0, 1: 1, 2: 2, 4: 3, 5: 4, 6: 5, 9: 6, 10: 7}[want]
                length = counts[slot] * _ESZ[want]
            recs.append((tag, p + 1, declared, body, length))
            p = body + length
        planes.append((counts, recs))
    return planes, p - base


def tag8_of(buf):
    for tag, _sf, declared, body in walk_chunk(buf)[0]:
        if tag == 8:
            return body, declared
    raise AssertionError("no tag 8 in this chunk")


def plane_record(buf, plane_index, tag):
    """(declared, body offset, true length) for one plane's sub-record."""
    body, size = tag8_of(buf)
    planes, _ = walk_planes(buf, body, size)
    for t, _sf, declared, off, length in planes[plane_index][1]:
        if t == tag:
            return declared, off, length
    raise AssertionError(f"plane {plane_index} has no tag {tag}")


def top_record(buf, tag):
    for t, _sf, declared, body in walk_chunk(buf)[0]:
        if t == tag:
            return declared, body
    raise AssertionError(f"no tag {tag}")


def halve_tag11(buf):
    """What an encoder that wrote tag 11's TRUE data length would emit.

    The named control. Rewrites every plane's tag-11 size field from 2n to n,
    which is byte-for-byte the output of an encoder that "fixed" the doubling.
    """
    out = bytearray(buf)
    body, size = tag8_of(buf)
    planes, _ = walk_planes(buf, body, size)
    n = 0
    for _counts, recs in planes:
        for tag, sf, declared, _off, length in recs:
            if tag == 11:
                out[sf:sf + 4] = length.to_bytes(4, "little")
                n += 1
    return bytes(out), n


def refuses(fn, *a, **kw):
    """True if the call raises ValueError -- a refusal, not a crash."""
    try:
        fn(*a, **kw)
    except ValueError:
        return True
    except Exception:
        return False
    return False


def holds(fn):
    """Evaluate a predicate over possibly-desynced bytes. Never raises.

    The walkers above are tolerant about WHERE they land but they still index,
    and a codec broken in the ways section 2 is about produces bytes that no
    walker can follow. Without this the test dies with a traceback instead of
    printing the failure it just found -- which is how a sabotage run reports
    "crashed" where it should report "[FAIL] the size field is derived".
    """
    try:
        return bool(fn())
    except Exception:
        return False


def guarded(fn, *a):
    """Run a section; an exception inside it becomes a FAIL, not a traceback.

    Same reason as `holds`, one level up: the verdict must still print, and it
    must name the section that could not finish.
    """
    try:
        return fn(*a)
    except Exception as exc:
        check(False, f"section {fn.__name__} ran to completion",
              f"{type(exc).__name__}: {exc}")
        return None


# --------------------------------------------------------------------------
# 0. The DAG child reference tag space. No vault.

def section0():
    print("\n-- 0. the point-location DAG's tagged child references")
    cases = [("null", None, 0xFFFFFFFF), ("xnode", 0, 0x00000000),
             ("xnode", 0x3FFFFFFF, 0x3FFFFFFF), ("ynode", 0, 0x40000000),
             ("ynode", 7, 0x40000007), ("sink", 0, 0x80000000),
             ("sink", 1, 0x80000001)]
    ok = all(child_kind(ref) == (kind, idx) for kind, idx, ref in cases)
    check(ok, "every bucket boundary decodes to the kind the client's code says",
          f"{len(cases)} references")
    round_trip = all(child_ref(kind, 0 if idx is None else idx) == ref
                     for kind, idx, ref in cases)
    check(round_trip, "child_ref is the inverse of child_kind on all four kinds")
    check(refuses(child_ref, "sink", 0x7FFFFFFF),
          "the one sink index that would collide with NULL is refused",
          "0x80000000 + 0x7FFFFFFF is 0xFFFFFFFF")
    check(refuses(child_ref, "xnode", 0x40000000)
          and refuses(child_ref, "ynode", 0x40000000),
          "an index too large for its 30-bit field is refused, not truncated")
    check(refuses(child_ref, "leaf", 0), "an unknown child kind is refused")


# --------------------------------------------------------------------------
# 1. A chunk built from nothing. No vault.

def section1():
    print("\n-- 1. a pathing chunk authored from nothing")
    pc = PathChunk.minimal(planes=3, rect=(0.0, 0.0, 3072.0, 3072.0))
    blob = pc.encode()
    recs, landing = walk_chunk(blob)

    check(blob[:4] == b"\x4c\x70\xfe\xee" and u32(blob, 4) == 12,
          "the two hard gates: signature 0xEEFE704C and version 12")
    check(holds(lambda: u32(blob, 8) == 0 and top_record(blob, 7)[1] == 17),
          "the header is TWELVE bytes, so the first record body starts at 17",
          "eight is the terrain chunk's header, and using it here desyncs")
    check(tuple(t for t, _s, _d, _b in recs) == (7, 8, 12, 13, 14, 255),
          "the tag sequence is the corpus's and the client's fixed table")
    check(landing == len(blob),
          "the record walk closes on the final byte",
          f"{landing} of {len(blob)}")
    check(holds(lambda: top_record(blob, 7)[0] == 2 + 8 * 4),
          "tag 7 declares 2 + 8*count for its 4 boundary points")
    check(holds(lambda: top_record(blob, 255)[0] == 0),
          "the terminator declares no payload")

    def planes_of(b):
        body, size = tag8_of(b)
        got, landed = walk_planes(b, body, size)
        return got, landed, size

    check(holds(lambda: planes_of(blob)[0] and
                len(planes_of(blob)[0]) == 3
                and planes_of(blob)[1] == planes_of(blob)[2]),
          "three planes, and the plane walk closes on tag 8's final byte")
    check(holds(lambda: planes_of(blob)[0][0][0] == (4, 1, 1, 0, 1, 1, 0, 0)),
          "the plane header counts are what the lists hold",
          "poly/edge/trap/x/y/sink/portal/portalTrap")
    check(holds(lambda: plane_record(blob, 0, 11)[0]
                == 2 * plane_record(blob, 0, 11)[2] == 64),
          "OUR OWN tag 11 declares double its data, as retail does",
          "32 bytes of polyData declared as 64")

    check(holds(lambda: PathChunk.from_chunk(blob).encode() == blob),
          "the authored chunk decodes and re-encodes byte-identically")
    again = PathChunk.from_chunk(blob) if holds(
        lambda: PathChunk.from_chunk(blob)) else PathChunk()
    check(len(again.planes) == 3 and len(again.trapezoids) == 3,
          "three planes carrying one trapezoid each survive the round trip")
    check(again.plane_map == [0, 0, 0] and len(again.obstacles.tiles) == 27,
          "tag 12 takes its n == planeCount form and the 3x3 grid is zeroed")

    one = PathChunk.minimal(planes=1)
    check(holds(lambda: one.plane_map == []
                and top_record(one.encode(), 12)[0] == 2),
          "a one-plane mesh gets the TWO-BYTE tag 12 the three retail "
          "one-plane maps use, not a normalised one")
    check(holds(lambda: PathChunk.from_chunk(one.encode()).encode()
                == one.encode()),
          "the one-plane form round-trips too")

    # The second witness, on a bare machine: a module this rung does not own
    # parses our bytes, and the mesh it gets is walkable where it should be.
    check(holds(lambda: len(PathingMap.from_chunk(one.encode()).trapezoids) == 1
                and len(PathingMap.from_chunk(one.encode()).planes) == 1),
          "pathmap.PathingMap -- a different parser -- accepts the authored chunk")
    check(holds(lambda: PathingMap.from_chunk(one.encode()).walkable(1536.0, 1536.0)
                and not PathingMap.from_chunk(one.encode()).walkable(5000.0, 5000.0)),
          "and the trapezoid it read is walkable inside and not outside")

    check(refuses(PathChunk.minimal, 0), "a mesh with no planes is refused")
    check(refuses(PathChunk.minimal, 1, (0.0, 0.0, 0.0, 100.0)),
          "a rect with no extent is refused")
    check(refuses(Obstacles, 2, 2, b"\x00" * 11),
          "an obstacle grid whose tiles do not match its cell count is refused")
    return pc


# --------------------------------------------------------------------------
# 2. Negative controls on the authored chunk. Every one MUST go red. No vault.

def controls(blob, where):
    """The four that matter, run on `blob`. Returns the number of checks."""
    ran = 0
    bad, n11 = halve_tag11(blob)
    ran += 1
    check(bad != blob and n11 > 0,
          f"[{where}] an encoder writing tag 11's TRUE length differs from "
          f"these bytes", f"{n11} size field(s) rewritten")
    ran += 1
    check(refuses(PathChunk.from_chunk, bad),
          f"[{where}] and the decoder refuses those bytes coming back")

    # Size derivation, the memcpy defence: mutate IN PLACE until an encoded
    # payload changes length, and require the emitted size to have moved.
    # In place, not by replacing the object, because a codec that cached the
    # bytes it decoded would survive the weaker shape (see test_mapfile.py).
    pc = PathChunk.from_chunk(blob)
    before = top_record(blob, 7)[0]
    pc.boundary.append((1.0, 2.0))
    grown = pc.encode()
    ran += 1
    check(holds(lambda: top_record(grown, 7)[0] == before + 8
                and len(grown) == len(blob) + 8),
          f"[{where}] tag 7's size field is DERIVED -- it moved with the payload",
          f"{before} -> {holds(lambda: top_record(grown, 7)[0]) and top_record(grown, 7)[0]}")

    # Count derivation, same shape, on the plane header a memcpy would replay.
    pc = PathChunk.from_chunk(blob)
    pc.planes[0].traps.append(pc.planes[0].traps[0])
    want = len(pc.planes[0].traps)
    grown = pc.encode()

    def counts_moved():
        body, size = tag8_of(grown)
        counts = walk_planes(grown, body, size)[0][0][0]
        return counts[2] == want and plane_record(grown, 0, 2)[0] == 44 * want

    ran += 1
    check(holds(counts_moved),
          f"[{where}] the plane header's trapezoid count is DERIVED too",
          f"the lists say {want} trapezoid(s) after the mutation")
    return ran


def section2(pc):
    print("\n-- 2. controls on the authored chunk (each MUST go red)")
    blob = pc.encode()
    controls(blob, "authored")

    check(PathChunk.from_chunk(blob).encode() == blob,
          "the unsabotaged chunk still round-trips, so the controls above "
          "are the difference and not a broken baseline")

    flipped = PathChunk.from_chunk(blob)
    flipped.planes[0].traps[0].y_top += 1.0
    check(flipped.encode() != blob,
          "one changed height in one trapezoid changes the bytes")

    print("   refusals:")
    bad_sig = b"\x00" + blob[1:]
    check(refuses(PathChunk.from_chunk, bad_sig),
          "a wrong signature is refused (the client's first hard gate)")
    bad_ver = blob[:4] + (11).to_bytes(4, "little") + blob[8:]
    check(refuses(PathChunk.from_chunk, bad_ver),
          "version 11 is refused (the client's second hard gate)")
    check(refuses(PathChunk.from_chunk, blob[:8] + blob[12:]),
          "an EIGHT-byte header -- the terrain chunk's -- is refused")
    check(refuses(PathChunk.from_chunk, blob[:-1]),
          "a truncated chunk is refused")
    check(refuses(PathChunk.from_chunk, blob + b"\x00"),
          "a trailing byte after the terminator is refused")
    term = len(blob) - 5
    check(refuses(PathChunk.from_chunk,
                  blob[:term + 1] + (4).to_bytes(4, "little") + b"\x00" * 4),
          "a terminator declaring a payload is refused")
    swapped = bytearray(blob)
    o12 = next(sf - 1 for t, sf, _d, _b in walk_chunk(blob)[0] if t == 12)
    swapped[o12] = 13
    check(refuses(PathChunk.from_chunk, bytes(swapped)),
          "a record out of the client's fixed order is refused")
    # tag 7's size field lying about its own count
    o7 = next(sf for t, sf, _d, _b in walk_chunk(blob)[0] if t == 7)
    lied = bytearray(blob)
    lied[o7:o7 + 4] = (2 + 8 * 3).to_bytes(4, "little")
    check(refuses(PathChunk.from_chunk, bytes(lied)),
          "tag 7 whose size is not 2 + 8*count is refused")
    # a plane header record that is not 32 bytes
    body, _size = tag8_of(blob)
    p0hdr = body + 4 + 1
    hdrlie = bytearray(blob)
    hdrlie[p0hdr:p0hdr + 4] = (36).to_bytes(4, "little")
    check(refuses(PathChunk.from_chunk, bytes(hdrlie)),
          "a plane header record that is not 32 bytes is refused")
    # a sub-record whose declared size is not count x element size
    d1, _o, _l = plane_record(blob, 0, 1)
    sf1 = next(sf for tag, sf, _d, _b, _l in
               walk_planes(blob, *tag8_of(blob))[0][0][1] if tag == 1)
    sublie = bytearray(blob)
    sublie[sf1:sf1 + 4] = (d1 + 8).to_bytes(4, "little")
    check(refuses(PathChunk.from_chunk, bytes(sublie)),
          "a sub-record declaring more than count x element size is refused")


# --------------------------------------------------------------------------
# 3-4. The archive.

class Sweep:
    def __init__(self):
        self.files = self.ok = self.planes = self.traps = 0
        self.children = {"xnode": 0, "ynode": 0, "sink": 0, "null": 0}
        self.problems = []
        self.laws = {"tag_order": 0, "tag11": 0, "subsize": 0, "hdr32": 0,
                     "root1": 0, "tag3": 0, "term0": 0, "tag7_is_poly0": 0,
                     "tag12": 0, "tag13": 0, "sink_lt_traps": 0, "child_ok": 0}
        self.planes_seen = 0


def path_blob(ar, entry):
    data = ar.read(entry)
    for cid, off, size in ffna_chunks(data):
        if cid == PATHING_CHUNK:
            return bytes(data[off:off + size])
    return None


def measure_laws(blob, pc, s):
    """Re-measure the corpus laws on one chunk, with the independent walker."""
    recs, landing = walk_chunk(blob)
    if (tuple(t for t, _sf, _d, _b in recs) == (7, 8, 12, 13, 14, 255)
            and landing == len(blob)):
        s.laws["tag_order"] += 1
    if top_record(blob, 255)[0] == 0:
        s.laws["term0"] += 1
    body, size = tag8_of(blob)
    planes, _ = walk_planes(blob, body, size)
    for counts, prs in planes:
        s.planes_seen += 1
        good_sub = good11 = True
        for tag, _sf, declared, _off, length in prs:
            if tag == 0:
                s.laws["hdr32"] += 1 if declared == 32 else 0
            elif tag == 3:
                s.laws["tag3"] += 1 if declared == 1 else 0
            elif tag == 11:
                good11 = declared == 2 * length
            else:
                good_sub = good_sub and declared == length
        s.laws["tag11"] += 1 if good11 else 0
        s.laws["subsize"] += 1 if good_sub else 0
    # Tag 7 is a byte-identical copy of plane 0's polyData, 349/349.
    if pc.boundary == pc.planes[0].poly:
        s.laws["tag7_is_poly0"] += 1
    n = len(pc.plane_map)
    if n == len(pc.planes) or (n == 0 and len(pc.planes) == 1):
        s.laws["tag12"] += 1
    ob = pc.obstacles
    if top_record(blob, 13)[0] == 6 + 3 * ob.width * ob.height + 12 * len(ob.records):
        s.laws["tag13"] += 1
    ok_sink = ok_child = True
    for pl in pc.planes:
        ok_sink = ok_sink and all(v < len(pl.traps) for v in pl.sinks)
        limits = {"xnode": len(pl.x_nodes), "ynode": len(pl.y_nodes),
                  "sink": len(pl.sinks)}
        refs = [c for nd in pl.x_nodes for c in nd[2:]]
        refs += [c for nd in pl.y_nodes for c in nd[1:]]
        for r in refs:
            kind, idx = child_kind(r)
            s.children[kind] += 1
            if kind != "null" and idx >= limits[kind]:
                ok_child = False
    s.laws["root1"] += sum(1 for pl in pc.planes if pl.root_type == 1)
    s.laws["sink_lt_traps"] += 1 if ok_sink else 0
    s.laws["child_ok"] += 1 if ok_child else 0


def sweep(ar, entries):
    s = Sweep()
    for e in entries:
        blob = path_blob(ar, e)
        if blob is None:
            s.problems.append(f"row {e.index}: no pathing chunk")
            continue
        s.files += 1
        try:
            pc = PathChunk.from_chunk(blob)
            out = pc.encode()
        except Exception as exc:
            s.problems.append(f"row {e.index}: {type(exc).__name__}: {exc}")
            continue
        if out == blob:
            s.ok += 1
        else:
            k = min(len(out), len(blob))
            first = next((i for i in range(k) if out[i] != blob[i]), k)
            s.problems.append(f"row {e.index}: differs at byte {first} "
                              f"({len(out)} vs {len(blob)} bytes)")
        s.planes += len(pc.planes)
        s.traps += len(pc.trapezoids)
        measure_laws(blob, pc, s)
    for line in s.problems[:8]:
        print(f"      ! {line}")
    if len(s.problems) > 8:
        print(f"      ! ... and {len(s.problems) - 8} more")
    return s


def section34(ar, mi, picks, want_all):
    print(f"\n-- 3. the round trip over {len(picks)} retail maps")
    check(len(mi.heads) == len(mi.pairs),
          "every map head has a Stripped partner -- the structural claim, and "
          "it does not depend on the count",
          f"{len(mi.heads)} map heads, {len(mi.pairs)} with a Stripped partner")
    check(len(mi.pairs) >= CORPUS_MAPS,
          f"and the population is at least {CORPUS_MAPS}",
          f"{len(mi.pairs)} in this archive (349 on 38797, 361 on 38833)")
    check(0 < len(picks) <= len(mi.pairs),
          "the sample is non-empty and drawn from that population",
          f"{len(picks)} of {len(mi.pairs)}")

    t0 = time.perf_counter()
    s = sweep(ar, picks)
    dt = time.perf_counter() - t0
    check(s.files == len(picks) and s.ok == s.files and s.files > 0,
          "retail pathing chunks re-encode BYTE-IDENTICALLY",
          f"{s.ok} of {s.files} in {dt:.0f}s")

    if want_all:
        check(s.files == len(mi.pairs) and s.files >= CORPUS_MAPS,
              "--all really did sweep every map that has a pathing chunk",
              f"{s.files} of {len(mi.pairs)} (at least {CORPUS_MAPS})")
        check(s.planes == CORPUS_PLANES and s.traps == CORPUS_TRAPS,
              "the corpus population is the one this study reports",
              f"{s.planes} planes (want {CORPUS_PLANES}), "
              f"{s.traps} trapezoids (want {CORPUS_TRAPS})")
        check(s.children == CORPUS_CHILDREN,
              "and the DAG child references split into FINDINGS 17.4's buckets",
              f"{s.children}")
    else:
        LEDGER.skip("the full 349-map sweep and its population figures",
                    f"sampled {s.files}; run with --all (~7 minutes)")

    print(f"\n-- 4. the framing laws, re-measured over those {s.files} maps")
    n, p = s.files, s.planes_seen
    check(p == s.planes and p > 0,
          "the independent walker found the same plane count the codec did",
          f"{p} planes")
    check(s.laws["tag_order"] == n,
          "the tag sequence is (7, 8, 12, 13, 14, 255) and the walk closes",
          f"{s.laws['tag_order']} of {n}")
    check(s.laws["tag11"] == p,
          "TAG 11 DECLARES EXACTLY TWICE ITS DATA, in every plane",
          f"{s.laws['tag11']} of {p}")
    check(s.laws["subsize"] == p,
          "every other sub-record declares exactly count x element size",
          f"{s.laws['subsize']} of {p}")
    check(s.laws["hdr32"] == p and s.laws["tag3"] == p,
          "the plane header is 32 bytes and the root-type record is 1",
          f"{s.laws['hdr32']} and {s.laws['tag3']} of {p}")
    check(s.laws["root1"] == p,
          "rootType is 1 -- a y node -- on every plane, as minimal() emits",
          f"{s.laws['root1']} of {p}")
    check(s.laws["term0"] == n, "the terminator carries no payload",
          f"{s.laws['term0']} of {n}")
    check(s.laws["tag7_is_poly0"] == n,
          "tag 7 is a copy of plane 0's polyData -- recorded, not enforced",
          f"{s.laws['tag7_is_poly0']} of {n}")
    check(s.laws["tag12"] == n,
          "tag 12 is n == planeCount, or n == 0 on a one-plane map",
          f"{s.laws['tag12']} of {n}")
    check(s.laws["tag13"] == n,
          "tag 13 is 6 + 3wh + 12m",
          f"{s.laws['tag13']} of {n}")
    check(s.laws["sink_lt_traps"] == n,
          "every sink node names a trapezoid of its own plane",
          f"{s.laws['sink_lt_traps']} of {n}")
    check(s.laws["child_ok"] == n and sum(s.children.values()) > 0,
          "every tagged child reference indexes inside its own array",
          f"{s.laws['child_ok']} of {n}, {sum(s.children.values())} references")
    return s


# --------------------------------------------------------------------------
# 5-6. A second witness, and the controls again on ArenaNet's bytes.

def section56(ar, mi, picks):
    print("\n-- 5. pathmap.PathingMap, a different parser, on the same bytes")
    agreed = compared = 0
    for e in picks[:4]:
        blob = path_blob(ar, e)
        pm = PathingMap.from_chunk(blob)
        pc = PathChunk.from_chunk(blob)
        mine = pc.trapezoids
        compared += 1
        same = len(mine) == len(pm.trapezoids) and all(
            (a.plane, a.index, a.y_top, a.y_bottom, a.x_top_left, a.x_top_right,
             a.x_bottom_left, a.x_bottom_right, tuple(a.neighbours),
             a.portal_left, a.portal_right)
            == (b.plane, b.index, b.y_top, b.y_bottom, b.x_top_left,
                b.x_top_right, b.x_bottom_left, b.x_bottom_right,
                tuple(b.neighbours), b.portal_left, b.portal_right)
            for a, b in zip(mine, pm.trapezoids))
        agreed += 1 if same else 0
    check(compared > 0 and agreed == compared,
          "both parsers read the same trapezoids, field for field",
          f"{agreed} of {compared} maps")

    print("\n-- 6. the same controls, on ArenaNet's bytes")
    blob = path_blob(ar, picks[0])
    ran = controls(blob, f"row {picks[0].index}")
    check(ran == 4, "all four controls ran on a retail chunk", f"{ran} of 4")


def pinned(ar, mi):
    """Two maps by file id, reported with their rows but not requiring them."""
    print("\n-- 3a. two maps pinned by file id")
    by_id = {}
    from archive import file_id_table
    table = file_id_table(ar)
    for name, fid in (("Kamadan", KAMADAN_ID), ("row-46196", SMALL_ID)):
        row = table.get(fid)
        by_id[name] = next((e for e in ar.entries if e.index == row), None)
    kam, small = by_id["Kamadan"], by_id["row-46196"]
    if kam is None or small is None:
        LEDGER.skip("the two pinned maps",
                    "this archive does not carry both file ids")
        return
    kb = path_blob(ar, kam)
    pc = PathChunk.from_chunk(kb)
    check(len(kb) == KAMADAN_BYTES and len(pc.planes) == KAMADAN_PLANES
          and len(pc.trapezoids) == KAMADAN_TRAPS and pc.encode() == kb,
          f"Kamadan (row {kam.index}) is the chunk this study describes, "
          f"and round-trips",
          f"{len(kb)} B, {len(pc.planes)} planes, {len(pc.trapezoids)} traps")
    sb = path_blob(ar, small)
    sc = PathChunk.from_chunk(sb)
    check(len(sb) == SMALL_BYTES and sc.encode() == sb,
          f"row {small.index} -- the ladder's template -- round-trips",
          f"{len(sb)} bytes")
    check(len(sc.planes) == 1 and sc.plane_map == []
          and (sc.obstacles.width, sc.obstacles.height) == SMALL_GRID
          and not sc.obstacles.records and set(sc.obstacles.tiles) == {0},
          "and it is one plane, the two-byte tag 12, a zeroed 3x3 grid",
          f"{len(sc.planes)} plane(s), tag 12 n={len(sc.plane_map)}, "
          f"{sc.obstacles!r}")
    # The builder's default reproduces that map's shape without reading it.
    built = PathChunk.minimal(planes=1, rect=(0.0, 0.0, 3072.0, 3072.0))
    check((built.obstacles.width, built.obstacles.height) == SMALL_GRID
          and built.plane_map == sc.plane_map
          and built.obstacles.tiles == sc.obstacles.tiles
          and len(built.planes) == len(sc.planes),
          "minimal() lands on that map's plane count, tag 12 form and grid",
          "from the rect alone -- no archive consulted")


def section7():
    """The STRIPPED codec against bytes this file wrote. No vault.

    Everything here is ours against ours and it is the cheap half; section 8 is
    where ArenaNet's archive gets a say. What this section IS good for is the
    framing, because the Stripped and Bloated chunks share a signature and a tag
    vocabulary and differ in their framing, so the failure mode is a plausible
    desync rather than an error.
    """
    print("\n-- 7. the Stripped pathing chunk, 0x10000008 (no vault)")
    sp = StrippedPath.rect(rect=(-3072.0, -1024.0, 3072.0, 5120.0), sequence=7,
                           sync_hash=0xDEADBEEF)
    blob = sp.encode()

    # Against the LITERAL 51, not against `encoded_size`, which is the property
    # under test -- and `encoded_size` is then required to agree with the bytes.
    check(len(blob) == 51 and sp.encoded_size == 51,
          "a 4-point boundary encodes to 19 + 8*4 = 51 bytes",
          f"{len(blob)} B, encoded_size says {sp.encoded_size}")
    back = StrippedPath.from_chunk(blob)
    check(back.encode() == blob and back.boundary == sp.boundary
          and back.sequence == 7 and back.sync_hash == 0xDEADBEEF,
          "and it decodes back to the same values and re-encodes identically")

    # THE HEADER IS NINE BYTES, NOT TWELVE, and the version is a BYTE. Asserted
    # against literals read off the wire rather than through the module's own
    # Structs, because a test that packed with `_STRIPPED_HEADER` would agree
    # with any header the module chose to write.
    check(blob[:4] == b"\x4c\x70\xfe\xee",
          "the signature is 0xEEFE704C, little-endian, at offset 0",
          blob[:4].hex())
    check(blob[4] == 12 and blob[5:9] == b"\x07\x00\x00\x00",
          "the version is the single BYTE 12, and the u32 sequence follows it "
          "at offset 5 -- NOT the Bloated chunk's u32 version",
          blob[4:9].hex())
    check(blob[9] == 7 and blob[10:12] == b"\x04\x00",
          "tag 7 is followed IMMEDIATELY by its u16 count -- there is no u32 "
          "size field, which is the Bloated framing and would desync here",
          blob[9:12].hex())
    check(blob[-1] == 255 and blob[-7] == 14,
          "and the tail is tag 14's six bytes then the 255 terminator",
          blob[-7:].hex())

    # THE MUTATION CONTROL. An encoder that replayed a decoded count instead of
    # re-deriving it round-trips every file it can walk, so the only thing that
    # can catch it is changing the payload's length in place and requiring the
    # emitted count to move with it. Same shape as test_mapfile's stored-size
    # control, and it exists for the same reason.
    grown = StrippedPath.from_chunk(blob)
    grown.boundary.append((99.0, -99.0))
    out = grown.encode()
    check(len(out) == len(blob) + 8 and out[10:12] == b"\x05\x00",
          "MUTATION CONTROL: appending one point grows the file by 8 AND moves "
          "the emitted count to 5 -- a replayed count fails only here",
          f"{len(out)} B, count field {out[10:12].hex()}")
    shrunk = StrippedPath.from_chunk(blob)
    del shrunk.boundary[0]
    out = shrunk.encode()
    check(len(out) == len(blob) - 8 and out[10:12] == b"\x03\x00",
          "MUTATION CONTROL: and removing one shrinks it and moves the count "
          "down", f"{len(out)} B, count field {out[10:12].hex()}")

    # THE CROSS-FRAMING CONTROL, both directions. Neither codec may accept the
    # other's bytes: they share a signature, so a reader that only gated on that
    # would happily produce nonsense.
    check(refuses(PathChunk.from_chunk, blob),
          "the BLOATED codec refuses a Stripped chunk (it shares the signature "
          "-- only the framing differs)")
    bloated = PathChunk.minimal(rect=(0.0, 0.0, 3072.0, 3072.0)).encode()
    check(refuses(StrippedPath.from_chunk, bloated),
          "and the STRIPPED codec refuses a Bloated one")

    # The refusals, each a thing stage 0 of the bloat pipeline hard-gates.
    bad_sig = bytearray(blob)
    bad_sig[0] ^= 0xFF
    check(refuses(StrippedPath.from_chunk, bytes(bad_sig)),
          "a wrong signature is refused")
    bad_ver = bytearray(blob)
    bad_ver[4] = 11
    check(refuses(StrippedPath.from_chunk, bytes(bad_ver)),
          "a wrong version byte is refused")
    bad_tag = bytearray(blob)
    bad_tag[9] = 8
    check(refuses(StrippedPath.from_chunk, bytes(bad_tag)),
          "a wrong first tag is refused")
    check(refuses(StrippedPath.from_chunk, blob + b"\x00"),
          "a trailing byte is refused -- the walk must close on the exact end")
    check(refuses(StrippedPath.from_chunk, blob[:-1]),
          "and a truncated chunk is refused rather than half-decoded")
    over = bytearray(blob)
    over[10:12] = b"\xff\x00"
    check(refuses(StrippedPath.from_chunk, bytes(over)),
          "a count larger than the bytes present is refused, not trusted",
          "255 points declared in a 51-byte chunk")
    return sp


def section8(ar, mi, picks, want_all):
    """The Stripped codec against ArenaNet's archive, and what it revealed."""
    print(f"\n-- 8. the Stripped chunk over {len(picks)} retail maps")
    ok = files = 0
    npts, areas, flags, hashes = [], [], {}, set()
    law = carried = seq_same = 0
    degenerate_traps = []
    t0 = time.perf_counter()
    for head in picks:
        partner = mi.partner(head)
        if partner is None:
            continue
        data = ar.read(partner)
        found = [bytes(data[o:o + s]) for c, o, s in ffna_chunks(data)
                 if c == STRIPPED_PATHING_CHUNK]
        if not found:
            continue
        files += 1
        blob = found[0]
        sp = StrippedPath.from_chunk(blob)
        if sp.encode() == blob:
            ok += 1
        if len(blob) == 19 + 8 * len(sp.boundary):
            law += 1
        npts.append(len(sp.boundary))
        areas.append(sp.signed_area())
        flags[sp.sync_flag] = flags.get(sp.sync_flag, 0) + 1
        hashes.add(sp.sync_hash)
        # THE ORACLE FOR SECTION 9: the same polygon out of the OTHER stream.
        pc = PathChunk.from_map(ar.read(head))
        if sp.boundary == pc.boundary:
            carried += 1
        if sp.sequence == pc.sequence:
            seq_same += 1
        if len(sp.boundary) <= 2:
            degenerate_traps.append(len(pc.trapezoids))
    dt = time.perf_counter() - t0

    check(files == len(picks) and files > 0,
          "every sampled map has a Stripped pathing chunk",
          f"{files} of {len(picks)}")
    check(ok == files and files > 0,
          "retail Stripped pathing chunks re-encode BYTE-IDENTICALLY",
          f"{ok} of {files} in {dt:.0f}s")
    check(law == files,
          "and every one of them is exactly 19 + 8n bytes",
          f"{law} of {files}")
    check(set(flags) == {0},
          "sync_flag is 0 in every map -- so the one carried byte we do not "
          "understand is at least constant", f"{flags}")
    check(len(hashes) == files,
          "and sync_hash is DISTINCT in every map, which is what a per-map "
          "hash looks like and why it is carried rather than derived",
          f"{len(hashes)} distinct over {files}")

    # THE WINDING, measured rather than assumed. `StrippedPath.rect`'s docstring
    # first claimed retail had a convention here; it does not, and this is the
    # check that keeps that correction from drifting back.
    pos = sum(1 for a in areas if a > 0)
    neg = sum(1 for a in areas if a < 0)
    check(pos > 0 and neg > 0,
          "retail uses BOTH windings, so the one we author is OURS and not a "
          "convention copied from ArenaNet",
          f"{pos} counter-clockwise, {neg} clockwise, "
          f"{len(areas) - pos - neg} degenerate")

    if want_all:
        check(files == len(mi.pairs) and files >= CORPUS_MAPS,
              "--all really did sweep every map",
              f"{files} of {len(mi.pairs)} (at least {CORPUS_MAPS})")
        check(pos == STRIPPED_CCW and neg == STRIPPED_CW,
              "and the winding split is the measured population",
              f"{pos}/{neg}, want {STRIPPED_CCW}/{STRIPPED_CW}")
        check(sorted(npts)[0] == STRIPPED_MIN_PTS
              and sorted(npts)[-1] == STRIPPED_MAX_PTS,
              "and the boundary sizes span the measured range",
              f"{min(npts)}..{max(npts)}, want {STRIPPED_MIN_PTS}.."
              f"{STRIPPED_MAX_PTS}")
    else:
        LEDGER.skip("the full 349-map Stripped population figures",
                    f"sampled {files}; run with --all")

    # ---- 9. THE CORRECTION, and it is the reason this rung got built --------
    print("\n-- 9. is the boundary polygon COMPILED, or just carried?")
    check(carried == files and files > 0,
          "the Stripped boundary is IDENTICAL to the Bloated one, point for "
          "point, in every map", f"{carried} of {files}")
    check(seq_same == files,
          "and so is the sequence number", f"{seq_same} of {files}")
    # THE DECISIVE CASE, PINNED BY FILE ID so it runs in a DEFAULT run. The
    # first version of this section only had the sweep, and a default sample of
    # 8 contains no degenerate boundary -- so the one finding the whole rung
    # exists for was reachable only under --all. Evidence that skips by default
    # is evidence nobody sees. File ids travel between copies of the archive;
    # rows do not, so the row is reported and never required.
    from archive import file_id_table
    row = file_id_table(ar).get(DEGENERATE_ID)
    head = next((e for e in ar.entries if e.index == row), None)
    if head is None:
        LEDGER.skip("the pinned degenerate boundary",
                    f"this archive does not carry file id 0x{DEGENERATE_ID:X}")
    else:
        partner = mi.partner(head)
        sdata = ar.read(partner)
        sblob = [bytes(sdata[o:o + s]) for c, o, s in ffna_chunks(sdata)
                 if c == STRIPPED_PATHING_CHUNK][0]
        sp = StrippedPath.from_chunk(sblob)
        pc = PathChunk.from_map(ar.read(head))
        check(len(sblob) == DEGENERATE_BYTES and len(sp.boundary) == 1,
              f"file id 0x{DEGENERATE_ID:X} (row {row}) ships a "
              f"{DEGENERATE_BYTES}-byte Stripped pathing chunk holding ONE "
              f"point", f"{len(sblob)} B, {len(sp.boundary)} point(s), "
                        f"{sp.boundary}")
        check(len(pc.trapezoids) == DEGENERATE_TRAPS,
              "and its Bloated partner carries a navmesh of "
              f"{DEGENERATE_TRAPS} trapezoids",
              f"{len(pc.trapezoids)} trapezoids over {len(pc.planes)} planes")
        check(sp.boundary == pc.boundary,
              "THE POLYGON IS CARRIED, NOT COMPILED: 27 bytes cannot encode "
              f"{DEGENERATE_TRAPS} trapezoids, and the one point arrives in the "
              "Bloated chunk unchanged. Whatever the compiler builds the mesh "
              "from, it is NOT tag 7 -- which is what FINDINGS 17.2's E3 input "
              "contract assumed", f"{sp.boundary} vs {pc.boundary}")

    if degenerate_traps:
        check(max(degenerate_traps) > 100,
              "and the same holds across the sweep: a boundary of 2 points or "
              "fewer coexists with hundreds of trapezoids",
              f"{len(degenerate_traps)} degenerate boundaries, up to "
              f"{max(degenerate_traps)} trapezoids")
    else:
        LEDGER.skip("the degenerate boundary ACROSS THE SWEEP",
                    f"no map in this sample of {files} has a boundary of 2 "
                    f"points or fewer; 28 of the 349 do -- run with --all. The "
                    f"pinned case above carries the finding either way.")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.strip().splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=None)
    ap.add_argument("--sample", type=int, default=8,
                    help="how many maps to sweep by default")
    ap.add_argument("--all", action="store_true",
                    help="every map with a pathing chunk -- 349, ~7 minutes")
    args = ap.parse_args(argv)

    print(__doc__.strip().splitlines()[0])
    guarded(section0)
    pc = guarded(section1) or PathChunk.minimal(planes=3)
    guarded(section2, pc)
    guarded(section7)

    dat = args.dat
    if dat is None:
        dat = os.path.join(vaultpath.vault_path("dat_study"), "Gw.dat")
    if not os.path.isfile(dat):
        LEDGER.skip("everything that needs the archive (sections 3-6 and 8-9)",
                    f"no Gw.dat at {dat}; vault resolved to "
                    f"{vaultpath.vault_root()} ({vaultpath.vault_why()}). "
                    f"Sections 0-2 and 7 measured both codecs against chunks "
                    f"this test wrote and NOTHING about ArenaNet's format.")
        return LEDGER.verdict()

    with Archive(dat) as ar:
        mi = MapIndex(ar)
        guarded(pinned, ar, mi)
        heads = [h for h, _p in mi.pairs]
        if args.all:
            picks = heads
        else:
            step = max(1, len(heads) // max(1, args.sample))
            picks = heads[::step][:args.sample]
        guarded(section34, ar, mi, picks, args.all)
        guarded(section56, ar, mi, picks)
        guarded(section8, ar, mi, picks, args.all)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
