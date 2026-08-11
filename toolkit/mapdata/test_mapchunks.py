"""Check the map-container layer against the real archive.

`mapchunks.py` makes four claims, and this file is arranged so that each one can
be refuted by bytes rather than agreed with by us:

  * WHAT A CHUNK ID MEANS. Section 1 runs on nothing but the module, so it runs
    on a bare machine -- but it only proves the algebra is self-consistent.
    Section 6 is the part that could fail: every chunk id in every sampled map
    must decompose with a stage the client names, a chunkType the client names,
    and a baseId inside `s_chunkInfo`'s 23 slots, and none of them may be one of
    the four NULL-load slots. An id outside those is not a parse error in the
    client, it is a call through a null pointer, so "no map does this" is the
    fact an authoring pass depends on.

  * WHAT AN MFT ROW IS. Section 5 is the strongest cheap check here and it costs
    no decompression: 349 heads, 349 partners resolved through `alloc.nextStream`,
    349 distinct, every partner `(alloc.flags 1, alloc.stream 0)`, chain depth
    exactly 1, and ZERO partners named by the file-id table. Every one of those
    is a number the archive chose, not one we did -- a wrong byte split gives a
    different head count, a wrong `nextStream` reading gives collisions or
    misses.

  * WHAT A DEPENDENCY LIST SAYS. Section 7 does the thing a round-trip has to do
    to mean anything: it decodes a REAL Dependencies chunk, throws the bytes
    away, re-encodes, and requires the result to equal what was on disk. It does
    that twice -- once from the stored triples, which checks the framing, and
    once from the file ids alone, which checks the inverse formula no upstream
    states. The second one went red the first time it ran, and the cause is a
    real property of the format rather than a bug: the pair encoding aliases,
    `id0 >= 0xFF00` names the same file as `(id0 - 0xFF00, id1 + 1)`, and
    ArenaNet's writer emits both forms. So the check is now per RECORD and in
    both directions -- a record comes back byte-identical exactly when its
    stored pair is canonical, and comes back CHANGED exactly when it is aliased.
    It is stated that way because the chunk-level version ("this chunk holds an
    aliased pair, so a difference in it is explained") excuses 84 of the 2,252
    chunks wholesale, differences that have nothing to do with aliasing
    included. Every decoded id is also looked up in the archive's file-id table,
    a different structure written by a different subsystem.

  * THAT THE CACHE IS A CACHE AND NOT A SECOND SOURCE OF TRUTH. Section 4 breaks
    the stamp three ways and corrupts the file a fourth, and requires the cache
    to be DROPPED -- rows empty, reason named -- rather than repaired or trusted
    every time; section 8 does the stale-stamp refusal again against the real
    archive and requires a cached index to equal BOTH a fresh `ffna_chunks` walk
    of the same row AND an `index_file` built during this run. The second half is
    not redundant: with a warm cache the cached row is the only thing sections 6
    and 7 read, so an `index_file` broken today would never be executed. Measured
    2026-08-10 -- shifting every chunk offset by 4 left a warm run green at
    64/64 before section 7 and section 8 were made to build their own index.

WHAT IT RUNS AGAINST. Sections 1-4 build their own fixtures and need nothing.
Sections 5-8 need `vault/dat_study/Gw.dat`; the vault is resolved with
`vaultpath.require_dir`, and its refusal -- which names the path it looked at and
the rule that produced it -- is turned into a declared skip rather than an exit,
so a machine without the vault reports what it did not measure instead of
pretending.

COST, MEASURED 2026-08-10. Section 6 runs off the chunk-index cache, so once the
cache is warm `--all` sweeps all 698 files of all 349 pairs in about 3 s and the
whole run takes 12-15 s -- the rest is section 7, which needs payload bytes the
cache deliberately does not hold and so stays on a small sample. Cold, the cache
costs ~11 minutes for all 698 rows; build it once with
`python toolkit/mapdata/mapchunks.py --build --partners`. A default `--sample 25`
run against a cold cache pays ~1.1 s per map read.

    python toolkit/mapdata/test_mapchunks.py
    python toolkit/mapdata/test_mapchunks.py --all        # every map, warm: seconds
    python toolkit/mapdata/test_mapchunks.py --sample 60 --deps-sample 12
"""

import argparse
import os
import shutil
import struct
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, Entry, ffna_chunks, file_id_table  # noqa: E402
import mapchunks  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

# MEASURED on the study copy, 2026-08-10. The two counts are content facts and
# should survive a different copy of Gw.dat. REFERENCE_ROW is an MFT row index,
# which is per-copy and portable to nothing -- so it is only used to CHOOSE a
# fixture for section 8, is never asserted as an identity, and falls back to the
# first map pair on a copy that does not have it.
MEASURED_MAP_ROWS = 349
REFERENCE_FFNA_TYPE = 3
REFERENCE_ROW = 46196          # the smallest complete map: 8,471 B, 18 chunks

# The seven chunk kinds that ever carry a Dependencies list (FINDINGS §3).
# A map naming an eighth would be news, so this is a census the corpus can break.
DEPENDENCY_KINDS = frozenset({0x02, 0x03, 0x04, 0x06, 0x09, 0x10, 0x12})

# FLOOR: 35 -- the checks that run with no vault at all, plus the section census.
# MEASURED on vault/dat_study/Gw.dat, 2026-08-10: a green default run prints 64,
# and the 29 above the floor are sections 5-8, which need the archive and turn
# into four declared skips when the vault is absent. Everything else here is
# unconditional and fixture-free: 11 in section 1 (the id algebra), 6 in section
# 2 (the alloc byte split), 10 in section 3 (the dependency codec), 7 in section
# 4 (the cache's staleness refusals), and 1 for the section census at the end.
# If a run scores 34, a section stopped executing and the passes above it are not
# evidence of anything.
#
# The floor cannot be set at 63 because sections 5-8 legitimately skip on a
# machine with no vault, and a floor that makes a legitimate skip a failure gets
# lowered in irritation later. What a floor of 35 CANNOT catch is section 6
# quietly dropping out of a run that does have the archive -- so the census check
# at the end does that job instead, comparing every section's executed count
# against what it ran when it was measured.
LEDGER = checks.Ledger("map chunks", floor=35)
check = checks.adopt(LEDGER)

# MEASURED section sizes for the census check at the end. Index 0 is section 1.
SECTION_SIZES_CORE = (11, 6, 10, 7)
SECTION_SIZES_ARCHIVE = (9, 10, 6, 4)


def _entry(index, flags, counter=0):
    """An MFT row with only the fields the alloc accessors read."""
    return Entry(index, 0, 0, 0, flags, counter, 0)


# ------------------------------------------------------------- section 1

def section_ids():
    print("\n1. chunk id algebra")
    check(len(mapchunks.CHUNK_NAMES) == mapchunks.MAX_BASE_ID == 23,
          "s_chunkInfo has 23 named slots",
          f"{len(mapchunks.CHUNK_NAMES)} names, MAX_BASE_ID "
          f"{mapchunks.MAX_BASE_ID}")

    t = mapchunks.decompose(0x20000002)
    check(t.stage == mapchunks.STAGE_BLOATED and t.chunk_type ==
          mapchunks.TYPE_DATA and t.base_id == 0x02 and t.name == "Terrain",
          "0x20000002 is Bloated Data Terrain", str(t))

    d = mapchunks.decompose(0x21000002)
    check(d.chunk_type == mapchunks.TYPE_DEPENDENCIES and d.base_id == 0x02,
          "0x21000002 is the Terrain Dependencies list", str(d))

    s = mapchunks.decompose(0x10000002)
    check(s.stage == mapchunks.STAGE_STRIPPED and s.base_id == 0x02,
          "0x10000002 is Stripped Data Terrain", str(s))

    trips = [(st, ty, b)
             for st in range(len(mapchunks.STAGE_NAMES))
             for ty in range(len(mapchunks.TYPE_NAMES))
             for b in range(mapchunks.MAX_BASE_ID)]
    bad = []
    for st, ty, b in trips:
        v = mapchunks.compose(st, ty, b)
        c = mapchunks.decompose(v)
        if (c.stage, c.chunk_type, c.base_id) != (st, ty, b) or c.value != v:
            bad.append((st, ty, b))
    check(not bad, "compose and decompose invert each other",
          f"{len(trips) - len(bad)}/{len(trips)} triples")

    for label, call, arg in (
            ("compose refuses baseId 23", mapchunks.compose,
             (mapchunks.STAGE_BLOATED, mapchunks.TYPE_DATA,
              mapchunks.MAX_BASE_ID)),
            ("decompose refuses stage 3", mapchunks.decompose, (0x30000002,)),
            ("decompose refuses chunkType 2", mapchunks.decompose,
             (0x22000002,)),
            ("decompose refuses baseId 0x17", mapchunks.decompose,
             (0x20000017,))):
        try:
            call(*arg)
            raised = False
        except ValueError:
            raised = True
        check(raised, label, "raised ValueError" if raised else "RETURNED")

    nulls = set(mapchunks.NULL_LOAD_BASE_IDS)
    agree = all(mapchunks.decompose(
        mapchunks.compose(mapchunks.STAGE_BLOATED, mapchunks.TYPE_DATA, b)
    ).null_load == (b in nulls) for b in range(mapchunks.MAX_BASE_ID))
    check(nulls == {0x01, 0x05, 0x0B, 0x0D} and agree,
          "the four NULL-load slots are named and flagged",
          f"{sorted(hex(n) for n in nulls)}")

    label = mapchunks.chunk_label(0x30000017)
    check("undecodable" in label and not label.startswith("Raw"),
          "chunk_label reports an illegal id instead of raising", label)


# ------------------------------------------------------------- section 2

def section_alloc():
    print("\n2. the MFT alloc bytes, which archive.py packs into one u16")
    check(mapchunks.MAP_HEAD_FLAGS_U16 == 259
          and mapchunks.MAP_PARTNER_FLAGS_U16 == 1,
          "259 and 1 are exactly (flags 3, stream 1) and (flags 1, stream 0)",
          f"head {mapchunks.MAP_HEAD_FLAGS_U16}, "
          f"partner {mapchunks.MAP_PARTNER_FLAGS_U16}")

    head = _entry(10, 259, counter=11)
    part = _entry(11, 1, counter=0)
    check(mapchunks.alloc_flags(head) == 3 and mapchunks.alloc_stream(head) == 1,
          "a head splits into USED|FIRST_STREAM and stream 1")
    check(mapchunks.alloc_flags(part) == 1 and mapchunks.alloc_stream(part) == 0,
          "a partner splits into USED and stream 0")
    check(mapchunks.next_stream(head) == 11 and mapchunks.next_stream(part) == 0,
          "next_stream reads Entry.counter, which is not a counter")
    check(mapchunks.is_map_head(head) and not mapchunks.is_map_head(part),
          "is_map_head accepts the head and refuses the partner")
    # The row that shows why the split matters: 110,852 rows in the archive are
    # USED|FIRST_STREAM at stream 0. Reading `flags` as one number cannot say so.
    check(not mapchunks.is_map_head(_entry(12, 0x0003)),
          "USED|FIRST_STREAM at stream 0 is not a map head",
          "flags 3 as a u16 -- the 110,852-row bucket")


# ------------------------------------------------------------- section 3

def section_dependency_codec():
    print("\n3. the dependency codec, on payloads this file builds")
    id0, id1 = 0x445D, 0x0100
    longhand = (id0 - 0xFF00FF) + id1 * 0xFF00
    check(mapchunks.dependency_file_id(id0, id1) == longhand == 0x435E,
          "the file id formula is (id0 - 0xFF00FF) + id1 * 0xFF00",
          f"(0x{id0:04X}, 0x{id1:04X}) -> 0x{longhand:X}")

    ids = [0x435E, 0x1, 0x345CC, 0x1B97D, 0xFFFF, 0x2FFFFF]
    bad = [i for i in ids
           if mapchunks.dependency_file_id(*mapchunks.dependency_pair(i)) != i]
    check(not bad, "dependency_pair inverts dependency_file_id",
          f"{len(ids) - len(bad)}/{len(ids)} ids")

    pads = [0, 0, 7, 0, 0, 0]      # a non-zero pad, so `pads` is load-bearing
    blob = mapchunks.encode_dependencies(ids, pads=pads)
    got = mapchunks.decode_dependencies(blob)
    check(got.file_ids == ids and got.pads == pads and len(blob) == 5 + 6 * len(ids),
          "encode -> decode round-trips ids and pads",
          f"{len(blob)} bytes, {len(got)} refs")

    def refuses(payload):
        try:
            mapchunks.decode_dependencies(payload)
            return False
        except ValueError:
            return True

    check(refuses(blob + b"\x00"),
          "a payload failing (size - 5) % 6 == 0 is refused")
    check(refuses(b"\x00\x00\x00\x00" + blob[4:]),
          "a wrong dependency signature is refused")
    check(refuses(blob[:4] + b"\x02" + blob[5:]),
          "a wrong dependency version is refused")
    check(refuses(b"\x30\x98"),
          "a payload shorter than the 5-byte header is refused")
    check(struct.unpack_from("<IB", blob, 0)
          == (mapchunks.DEPENDENCY_SIGNATURE, mapchunks.DEPENDENCY_VERSION),
          "the encoder writes the signature and version the client gates on")

    # The aliasing, stated where a bare machine can check it. ArenaNet's writer
    # emits the right-hand form; ours emits the left. Both name the same file.
    alias = (0xFF02, 0x0100)
    canon = (0x0002, 0x0101)
    check(mapchunks.dependency_file_id(*alias)
          == mapchunks.dependency_file_id(*canon)
          and mapchunks.is_canonical_pair(*canon)
          and not mapchunks.is_canonical_pair(*alias),
          "the pair encoding aliases: id0 >= 0xFF00 names an id twice",
          f"{[hex(v) for v in alias]} and {[hex(v) for v in canon]} both give "
          f"0x{mapchunks.dependency_file_id(*alias):X}")
    aliased_blob = mapchunks.encode_dependency_entries([alias + (0,)])
    check(mapchunks.encode_dependencies(
              [mapchunks.dependency_file_id(*alias)]) != aliased_blob
          and mapchunks.decode_dependencies(aliased_blob).entries
              == (alias + (0,),),
          "only encode_dependency_entries can reproduce an aliased chunk",
          "encode_dependencies canonicalises, and says so")


# ------------------------------------------------------------- section 4

def section_cache_mechanics():
    print("\n4. the chunk-index cache refuses a stale stamp")
    tmp = tempfile.mkdtemp(prefix="rurik-mapchunks-")
    try:
        path = os.path.join(tmp, "sub", "chunkindex.json")
        stamp = {"format": mapchunks.CACHE_FORMAT, "dat": "X:/fake/Gw.dat",
                 "dat_size": 4198489600, "entry_count": 177342,
                 "mft_offset": 4173266432}
        c = mapchunks.ChunkIndexCache(stamp, path)
        check(not c.load() and c.stale_reason == "no cache file yet",
              "a cache file that does not exist is a clean miss",
              f"{c.stale_reason}")

        c.rows[46196] = mapchunks.RowIndex(
            46196, 3, 8471, [(0x20000000, 13, 8), (0x2000000C, 29, 41)])
        c.dirty = True
        c.save()
        back = mapchunks.ChunkIndexCache(stamp, path)
        check(back.load() and set(back.rows) == {46196}
              and back.rows[46196].chunks == c.rows[46196].chunks
              and back.rows[46196].length == 8471,
              "a matching stamp round-trips rows, order, offsets and sizes",
              f"{len(back.rows)} row(s), {back.rows[46196].chunks}")

        for field, value in (("entry_count", 177343),
                             ("dat_size", 4198489599),
                             ("format", mapchunks.CACHE_FORMAT + 1)):
            other = dict(stamp)
            other[field] = value
            s = mapchunks.ChunkIndexCache(other, path)
            ok = (not s.load()) and not s.rows and field in (s.stale_reason or "")
            check(ok, f"a cache whose {field} disagrees is dropped, not used",
                  f"{len(s.rows)} rows kept, reason: {s.stale_reason}")

        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{not json at all")
        g = mapchunks.ChunkIndexCache(stamp, path)
        check(not g.load() and not g.rows and "unreadable" in (g.stale_reason or ""),
              "an unparseable cache file is dropped, not raised",
              f"{g.stale_reason}")

        lone = mapchunks.ChunkIndexCache(stamp, path)      # archive=None
        try:
            lone.index(46196)
            raised = False
        except ValueError:
            raised = True
        check(raised, "an uncached row with no archive raises rather than "
                      "inventing an index")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------- section 5

def section_rows(ar, mi):
    print("\n5. every map is two MFT rows")
    check(len(mi.heads) == MEASURED_MAP_ROWS, "map head rows",
          f"{len(mi.heads)} rows with (alloc.flags 3, alloc.stream 1)")
    check(not mi.orphans, "every head resolves its nextStream to a real row",
          f"{len(mi.pairs)} pairs, {len(mi.orphans)} orphaned")

    wrong = [(h.index, mapchunks.alloc_flags(p), mapchunks.alloc_stream(p))
             for h, p in mi.pairs
             if (mapchunks.alloc_flags(p), mapchunks.alloc_stream(p))
             != (mapchunks.MAP_PARTNER_ALLOC_FLAGS, mapchunks.MAP_PARTNER_STREAM)]
    check(not wrong, "every partner is (alloc.flags 1, alloc.stream 0)",
          f"{len(mi.pairs) - len(wrong)}/{len(mi.pairs)}")

    prows = [p.index for _h, p in mi.pairs]
    check(len(set(prows)) == len(prows), "no two heads share a partner",
          f"{len(set(prows))} distinct of {len(prows)}")

    deep = [h.index for h, _p in mi.pairs if len(mi.chain(h)) != 1]
    tail = [p.index for _h, p in mi.pairs if mi.chain(p)]
    check(not deep and not tail, "chain depth is exactly 1, never 0 and never 2",
          f"{len(deep)} head(s) off depth 1, {len(tail)} partner(s) continuing")

    named = mapchunks.stored_file_ids(ar)
    named_partners = [r for r in prows if r in named]
    check(not named_partners, "no partner is named by the file-id table",
          f"{len(named_partners)} of {len(prows)}")

    counts = {}
    for h, _p in mi.pairs:
        counts[len(named.get(h.index, ()))] = \
            counts.get(len(named.get(h.index, ())), 0) + 1
    check(set(counts) == {2}, "every head is named by exactly two file ids",
          f"census {dict(sorted(counts.items()))}")

    literal = [e.index for e in ar.entries if e.flags == 259]
    check(literal == [h.index for h in mi.heads],
          "the byte split selects exactly the rows `flags == 259` selects",
          f"{len(literal)} rows")

    heads_set = {h.index for h in mi.heads}
    check(not (heads_set & set(prows)), "no row is both a head and a partner",
          f"{len(heads_set & set(prows))} overlapping")


# ------------------------------------------------------------- section 6

def _kinds(row_index):
    """The (chunkType, baseId) pairs a row carries, stage masked off.

    Skips an id that will not decompose rather than raising: the check that an
    id decomposes at all is a separate one, and it must be allowed to report the
    count instead of being pre-empted by a traceback here.
    """
    out = set()
    for cid, _o, _s in row_index.chunks:
        try:
            c = mapchunks.decompose(cid)
        except ValueError:
            continue
        out.add((c.chunk_type, c.base_id))
    return out


def section_chunk_census(mi, cache, picks):
    print(f"\n6. chunk ids across {len(picks)} of {len(mi.pairs)} maps "
          f"(cache: {len(cache)} rows warm)")
    bad_type = []
    undecodable = []
    wrong_stage = []
    null_load = []
    kinds_seen = set()
    dep_sizes_bad = []
    param_order = []
    subset_bad = []
    dangling = []
    headerless = []
    chunks = files = 0

    for h, p in picks:
        for entry, want_stage in ((h, mapchunks.STAGE_BLOATED),
                                  (p, mapchunks.STAGE_STRIPPED)):
            ri = cache.index(entry.index)
            files += 1
            if ri.ffna_type != REFERENCE_FFNA_TYPE:
                bad_type.append((entry.index, ri.ffna_type))
            data_slots, dep_slots = set(), set()
            for cid, _off, size in ri.chunks:
                chunks += 1
                try:
                    c = mapchunks.decompose(cid)
                except ValueError as exc:
                    undecodable.append((entry.index, cid, str(exc)[:50]))
                    continue
                kinds_seen.add((c.chunk_type, c.base_id))
                (dep_slots if c.chunk_type == mapchunks.TYPE_DEPENDENCIES
                 else data_slots).add(c.base_id)
                if c.stage != want_stage:
                    wrong_stage.append((entry.index, cid))
                if c.null_load:
                    null_load.append((entry.index, cid))
                if (c.chunk_type == mapchunks.TYPE_DEPENDENCIES
                        and (size - 5) % 6 != 0):
                    dep_sizes_bad.append((entry.index, cid, size))
            if not dep_slots <= data_slots:
                dangling.append((entry.index, sorted(dep_slots - data_slots)))
            if mapchunks.BASE_HEADER not in data_slots:
                headerless.append(entry.index)

        hi = cache.index(h.index)
        pos_param = hi.position(mapchunks.compose(
            mapchunks.STAGE_BLOATED, mapchunks.TYPE_DATA,
            mapchunks.BASE_MAP_PARAMETERS))
        pos_terrain = hi.position(mapchunks.compose(
            mapchunks.STAGE_BLOATED, mapchunks.TYPE_DATA,
            mapchunks.BASE_TERRAIN))
        if pos_param != 1 or pos_terrain is None or pos_param >= pos_terrain:
            param_order.append((h.index, pos_param, pos_terrain))

        pi = cache.index(p.index)
        hk = _kinds(hi)
        pk = _kinds(pi)
        if not pk <= hk:
            subset_bad.append((h.index, sorted(pk - hk)))

    bases = {b for _t, b in kinds_seen}
    check(not undecodable,
          "every chunk id decomposes into a stage, a chunkType and a slot",
          f"{chunks - len(undecodable)}/{chunks} ids over {files} files, "
          f"{len(bases)} distinct slots, max 0x{max(bases):02X}")
    for row, cid, why in undecodable[:5]:
        print(f"        row {row} 0x{cid:08X}: {why}")
    check(not bad_type, "every file in a map pair is ffna type 3",
          f"{files - len(bad_type)}/{files}")
    check(not wrong_stage,
          "head ids are all stage Bloated and partner ids all stage Stripped",
          f"{len(wrong_stage)} misfiled")
    check(not null_load,
          "no map carries one of the four NULL-load chunk kinds",
          f"{len(null_load)} occurrences of "
          f"{sorted(hex(n) for n in mapchunks.NULL_LOAD_BASE_IDS)}")
    # Two cross-record claims from FINDINGS §3/§17.5 that the file can break:
    # a Dependencies list whose own Data chunk is absent would be dangling, and
    # Header is the one chunk kind the client cannot default-construct.
    check(not dangling,
          "no Dependencies list names a chunk kind its file does not carry",
          f"{files - len(dangling)}/{files} files")
    for row, extra in dangling[:5]:
        print(f"        row {row}: dependencies with no data chunk {extra}")
    check(not headerless, "every file carries the Header chunk",
          f"{files - len(headerless)}/{files} files")
    check(not dep_sizes_bad, "(size - 5) % 6 == 0 on every Dependencies chunk",
          f"{len(dep_sizes_bad)} violations")
    check(not param_order,
          "Map Parameters is at chunk index 1 and precedes Terrain",
          f"{len(picks) - len(param_order)}/{len(picks)} maps")
    for row, a, b in param_order[:5]:
        print(f"        row {row}: Map Parameters at {a}, Terrain at {b}")
    check(not subset_bad,
          "the Stripped partner carries no chunk kind its Bloated head lacks",
          f"{len(picks) - len(subset_bad)}/{len(picks)} maps")
    for row, extra in subset_bad[:5]:
        print(f"        row {row}: partner-only kinds {extra}")
    deps_kinds = {b for t, b in kinds_seen if t == mapchunks.TYPE_DEPENDENCIES}
    check(deps_kinds <= DEPENDENCY_KINDS,
          "only the seven known chunk kinds carry a Dependencies list",
          f"{sorted(hex(b) for b in deps_kinds)}")


# ------------------------------------------------------------- section 7

def section_dependencies(ar, cache, table, picks):
    print(f"\n7. dependency lists on {len(picks)} maps, against real bytes")
    lists = refs = aliased = aliased_chunks = 0
    bad_header = []
    bad_pad = []
    unresolved = []
    frame_bad = []
    unexplained = []
    id1s = set()

    for h, _p in picks:
        data = ar.read(h)
        # Built here rather than taken from the cache. These maps are
        # decompressed anyway, and reading the offsets out of a warm cache would
        # mean a broken `index_file` could not be refuted by anything below --
        # measured: shifting every offset by 4 left a warm run green at 64/64.
        ri = mapchunks.index_file(h.index, data)
        if h.index not in cache.rows:
            cache.rows[h.index] = ri
            cache.dirty = True
        for cid, off, size in ri.chunks:
            try:
                c = mapchunks.decompose(cid)
            except ValueError:
                continue            # section 6 owns that failure, not this one
            if c.chunk_type != mapchunks.TYPE_DEPENDENCIES:
                continue
            blob = bytes(data[off:off + size])
            try:
                dep = mapchunks.decode_dependencies(blob)
            except ValueError as exc:
                bad_header.append((h.index, cid, str(exc)[:60]))
                continue
            lists += 1
            refs += len(dep)
            bad_pad += [(h.index, cid)] * sum(1 for pd in dep.pads if pd != 0)
            ids = dep.file_ids
            unresolved += [(h.index, i) for i in ids if i not in table]
            id1s.update(b for _a, b, _p in dep.entries)

            # (a) the framing: the stored triples, written back verbatim.
            if mapchunks.encode_dependency_entries(
                    dep.entries, version=dep.version,
                    signature=dep.signature) != blob:
                frame_bad.append((h.index, cid, size))

            # (b) the semantic encode: from the file ids alone. This is the one
            # that found the aliasing -- see the module docstring. The rule is
            # per RECORD and in both directions: a record whose stored pair is
            # canonical must come back byte-identical, and a record whose pair is
            # aliased must come back CHANGED. A chunk-level rule ("this chunk
            # holds an aliased pair, so any difference in it is explained") would
            # excuse 84 of the 2,252 chunks wholesale, including differences that
            # have nothing to do with aliasing.
            again = mapchunks.encode_dependencies(
                ids, version=dep.version, signature=dep.signature,
                pads=dep.pads)
            if len(again) != len(blob) or again[:5] != blob[:5]:
                unexplained.append((h.index, cid, -1))
                continue
            nc = 0
            for i, (a, b, _p) in enumerate(dep.entries):
                lo = 5 + i * mapchunks.DEPENDENCY_ENTRY.size
                same = again[lo:lo + mapchunks.DEPENDENCY_ENTRY.size] == \
                    blob[lo:lo + mapchunks.DEPENDENCY_ENTRY.size]
                # The rule is stated HERE, not asked of the module: `divmod` by
                # 0xFF00 can only produce id0 < 0xFF00, so a stored pair is the
                # canonical one exactly when its id0 is. Delegating to
                # `is_canonical_pair` would ask the same function that produced
                # the re-encode whether the re-encode was right -- measured: an
                # encoder perturbed to emit the aliased form cancels out and
                # scores zero here when the module is the oracle.
                canonical = a < 0xFF00
                if canonical != mapchunks.is_canonical_pair(a, b):
                    unexplained.append((h.index, cid, i))
                if not canonical:
                    nc += 1
                if same != canonical:
                    unexplained.append((h.index, cid, i))
            aliased += nc
            aliased_chunks += 1 if nc else 0

    check(not bad_header,
          "every Dependencies chunk carries signature 0x29939830 version 1",
          f"{lists} lists, {len(bad_header)} refused")
    for row, cid, why in bad_header[:5]:
        print(f"        row {row} 0x{cid:08X}: {why}")
    check(lists > 0 and refs > 0, "the sample actually contained dependencies",
          f"{lists} lists, {refs} references")
    check(not bad_pad, "the third u16 of every entry is 0",
          f"{refs - len(bad_pad)}/{refs} entries")
    check(not unresolved,
          "every referenced file id resolves through the archive's id table",
          f"{refs - len(unresolved)}/{refs} references")
    for row, fid in unresolved[:5]:
        print(f"        row {row}: 0x{fid:X} not in the file-id table")
    check(not frame_bad,
          "the record framing re-emits ArenaNet's bytes exactly",
          f"{lists - len(frame_bad)}/{lists} chunks byte-identical")
    for row, cid, size in frame_bad[:5]:
        print(f"        row {row} 0x{cid:08X}: {size} B")
    check(not unexplained,
          "each record re-encodes byte-identically iff its stored pair is "
          "canonical",
          f"{refs} records, {aliased} aliased entries in {aliased_chunks} "
          f"chunks, {len(unexplained)} records unaccounted for; id1 seen "
          f"{sorted(hex(v) for v in id1s)}")
    for row, cid, i in unexplained[:5]:
        print(f"        row {row} 0x{cid:08X}: "
              + ("header or length differs" if i < 0 else
                 f"record {i} does not follow the aliasing rule"))


# ------------------------------------------------------------- section 8

def section_cache_vs_archive(ar, mi, cache, row):
    print(f"\n8. the cache against a fresh walk of row {row}")
    entry = mi.by_row[row]
    data = ar.read(entry)
    fresh = list(ffna_chunks(data))           # a generator: listed once
    built = mapchunks.index_file(row, data)   # index_file run NOW, not last week
    ri = cache.index(row)
    check(list(ri.chunks) == [(c, o, s) for c, o, s in fresh]
          and list(built.chunks) == [(c, o, s) for c, o, s in fresh]
          and (built.length, built.ffna_type) == (len(data), data[4])
          and ri.length == len(data) and ri.ffna_type == data[4],
          "the cached index equals a freshly built one and a fresh "
          "ffna_chunks walk, in order",
          f"{len(fresh)} chunks, {len(data)} B, ffna type {data[4]}")

    before = cache.misses
    cache.index(row)
    check(cache.misses == before,
          "a second lookup is a hit and decompresses nothing",
          f"{cache.hits} hits, {cache.misses} reads")

    tmp = tempfile.mkdtemp(prefix="rurik-mapchunks-real-")
    try:
        path = os.path.join(tmp, "chunkindex.json")
        mirror = mapchunks.ChunkIndexCache(dict(cache.stamp), path,
                                           archive=ar)
        mirror.rows = dict(cache.rows)
        mirror.dirty = True
        mirror.save()
        back = mapchunks.ChunkIndexCache(mapchunks.archive_stamp(ar), path)
        same = (back.load()
                and set(back.rows) == set(mirror.rows)
                and all(back.rows[r].chunks == mirror.rows[r].chunks
                        and back.rows[r].length == mirror.rows[r].length
                        for r in mirror.rows))
        check(same, "the real index survives a save/load unchanged",
              f"{len(back.rows)} rows")

        stale = mapchunks.archive_stamp(ar)
        stale["entry_count"] += 1
        s = mapchunks.ChunkIndexCache(stale, path)
        check(not s.load() and not s.rows
              and "entry_count" in (s.stale_reason or ""),
              "the same file is refused once the archive's row count moves",
              f"{s.stale_reason}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=None,
                    help="override the archive; default is the vault's copy")
    ap.add_argument("--sample", type=int, default=25,
                    help="maps swept in section 6 (cheap once the cache is warm)")
    ap.add_argument("--deps-sample", type=int, default=6,
                    help="maps decompressed in section 7")
    ap.add_argument("--all", action="store_true",
                    help="sweep every map in section 6")
    args = ap.parse_args()

    t0 = time.perf_counter()
    marks = [LEDGER.ran]
    section_ids()
    marks.append(LEDGER.ran)
    section_alloc()
    marks.append(LEDGER.ran)
    section_dependency_codec()
    marks.append(LEDGER.ran)
    section_cache_mechanics()
    marks.append(LEDGER.ran)

    dat = args.dat
    why = None
    if dat is None:
        try:
            dat = os.path.join(
                vaultpath.require_dir(
                    "dat_study",
                    why="the map container's only real fixture -- sections 5-8 "
                        "read chunk tables and dependency lists out of it"),
                "Gw.dat")
        except SystemExit as exc:
            dat, why = None, str(exc).replace("\n", "; ")
    if dat is not None and not os.path.isfile(dat):
        why = f"{dat} is not a file"
        dat = None

    expected = SECTION_SIZES_CORE
    if dat is None:
        for name in ("5. MFT row structure", "6. chunk id census",
                     "7. dependency lists", "8. cache vs archive"):
            LEDGER.skip(name, why)
    else:
        expected = SECTION_SIZES_CORE + SECTION_SIZES_ARCHIVE
        with Archive(dat) as ar:
            mi = mapchunks.MapIndex(ar)
            table = file_id_table(ar)
            section_rows(ar, mi)
            marks.append(LEDGER.ran)

            cache = mapchunks.ChunkIndexCache.open(ar)
            pairs = mi.pairs
            picks = (pairs if args.all
                     else pairs[::max(1, len(pairs) // max(1, args.sample))])
            section_chunk_census(mi, cache, picks)
            marks.append(LEDGER.ran)

            dep_picks = picks[:max(1, args.deps_sample)]
            section_dependencies(ar, cache, table, dep_picks)
            marks.append(LEDGER.ran)

            row = REFERENCE_ROW if REFERENCE_ROW in mi.by_row else pairs[0][0].index
            section_cache_vs_archive(ar, mi, cache, row)
            marks.append(LEDGER.ran)

            if cache.save():
                print(f"\ncache written: {len(cache)} rows -> {cache.path}")

    print("\n9. the sections all executed")
    sizes = tuple(marks[i + 1] - marks[i] for i in range(len(marks) - 1))
    check(sizes == expected,
          "every section ran the number of checks it ran when it was measured",
          f"{sizes} vs {expected}")

    print(f"\nfinished in {time.perf_counter() - t0:.1f}s")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
