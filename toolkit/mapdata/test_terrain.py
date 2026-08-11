"""Check the terrain codec against the real archive, in both directions.

THE HEADLINE IS THE ROUND-TRIP: decode a retail terrain chunk into typed values,
throw the original bytes away, re-encode from the values alone, and require the
result to be byte-identical. That is section 7, it runs over a sample of the 349
map rows by default and over all of them with `--all`, and everything else here
exists to stop it being the kind of green light this repository refuses.

  * It is not "our encoder reproduced our decoder". The comparison is against
    bytes out of `Gw.dat`, which nothing of ours produced.
  * It can fail, and section 6 proves it can: one byte of a real chunk is
    perturbed and the re-encode is required to stop matching the original.
    Twelve more controls flip a signature, a version, a tag order, a record
    framing, a table count, a dimension and a tag-7 length, and every one of the
    twelve must RAISE rather than shrug.
  * The size laws are re-derived in section 3 by a walker written here, using
    `int.from_bytes` rather than `struct`, which never consults `terrain.py`.
    A decoder agreeing with itself about its own framing proves nothing.
  * Section 4 is the strongest check available and it crosses chunks: the Map
    Parameters rect divided by the terrain dims must be exactly 96.0 on both
    axes. Two chunks written by different subsystems predicting each other. The
    `(dim-1)` divisor is shipped alongside as a negative control and must NOT
    produce 96.0.
  * Section 1 builds a 32x32 map out of nothing and reads it back. It touches no
    ArenaNet bytes at all and runs on a bare machine, which is why it goes first
    -- put after the archive, it would hide behind a missing vault.

WHAT THE ROUND-TRIP DOES NOT PROVE, restated here because the count is
impressive and the claim it supports is narrower than it looks: framing
everywhere, field typing for tags 0/1/2/4/5 and the optional second tag 3, and
NOTHING about the content of tags 3, 7 and 9. Tag 7's block walk is real
evidence; its shadow payload and 128-byte tail are opaque bytes carried
verbatim. See `terrain.py`'s docstring for the full split.

MEASURED VALUES ARE THIS ARCHIVE'S. File ids are content keys and travel; MFT
row indices do not, so every row-index check is conditional on the entry count
and declares a skip otherwise -- the same shape as `test_pathmap.py` section 6.

A MISSING VAULT IS A FAILURE HERE, NOT A SKIP. Section 1 still runs and its six
checks are still printed, and the missing fixture is declared as a skip naming
the path -- but a run with no archive has measured nothing about the FORMAT, so
the floor rule turns those six into the FAIL they are (6 of a floor of 49).

    python toolkit/mapdata/test_terrain.py
    python toolkit/mapdata/test_terrain.py --sample 60
    python toolkit/mapdata/test_terrain.py --all      # every map, ~7 minutes
"""

import argparse
import math
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, file_id_table, ffna_type  # noqa: E402
from terrain import (Terrain, ShadowBlock, TERRAIN_CHUNK,  # noqa: E402
                     STRIPPED_TERRAIN_CHUNK, SIGNATURE, VERSION, CELL_PITCH,
                     CHUNK_SIZE, SHADOW_TAIL, SEQUENCE_SHORT, SEQUENCE_LONG)
import checks  # noqa: E402
import vaultpath  # noqa: E402

MAP_FLAGS = 259
MAP_PARAMS_CHUNK = 0x2000000C
MAP_PARAMS_SIG = 0x5943EEEF
MEASURED_ENTRY_COUNT = 177342

# Row 46196, the smallest complete map in the archive and this file's primary
# fixture. The file id is the portable key; the row is pinned separately.
SMALL_FILE_ID = 0x22E2C
SMALL_ROW = 46196
SMALL_CHUNKS = 18
SMALL_CHUNK_INDEX = 5
SMALL_TERRAIN_BYTES = 7165
SMALL_DIMS = (32, 32)
SMALL_RECORDS = ((0, 26), (1, 4096), (2, 1024), (4, 5), (5, 5), (3, 256),
                 (9, 1024), (7, 676), (255, 0))
SMALL_RECT = (-0.0, -0.0, 3072.0, 3072.0)
SMALL_ANGLE = 1.199742078781128
SMALL_TAG0_08 = 24576.0
SMALL_TEX_WORD = 8421

KAMADAN_FILE_ID = 0x345CC
KAMADAN_ROW = 22371
KAMADAN_CHUNK_INDEX = 8
KAMADAN_TERRAIN_BYTES = 1376949
KAMADAN_DIMS = (416, 448)
KAMADAN_RECT = (-18432.0, -21504.0, 21504.0, 21504.0)

PRESEARING_FILE_ID = 0x1B97D
PRESEARING_ROW = 7982
PRESEARING_CHUNK_INDEX = 7
PRESEARING_TERRAIN_BYTES = 1735664
PRESEARING_DIMS = (416, 512)

# The smallest of the 24 maps that carry a second, 17-byte tag-3 record. Pinned
# by row because it has no distinguished file id; the shape is what matters.
LONG_SEQ_ROW = 65158
LONG_SEQ_DIMS = (288, 192)
LONG_SEQ_TERRAIN_BYTES = 415499
LONG_SEQ_SIZES = (26, 221184, 55296, 61, 61, 13824, 55296, 69676, 17, 0)

# Corpus constants. MEASURED on this archive 2026-08-10 by a full 349-map sweep;
# the sampled sections check the proportion they can see, not these totals.
CORPUS_MAPS = 349
CORPUS_SEQ_SHORT = 325
CORPUS_SEQ_LONG = 24

# tag 0's angle lattice. The client quantises over [0, pi/2] in 254 steps, so
# the step is pi/508. FINDINGS 4 and 17.4 claim the corpus lands EXACTLY on it;
# that is refuted (see terrain.py) and the surviving claim is 1 ULP, which is
# what section 7 asserts, with the exact-match count reported beside it.
ANGLE_STEP = math.pi / 508.0
ANGLE_B_RANGE = (16, 250)

# FLOOR: 49 -- the checks that run on any Gw.dat, whatever --sample or --all is
# asked for. MEASURED on C:\gd\Rurik\vault\dat_study\Gw.dat, 2026-08-10: a green
# default run prints 57 and `--all` prints 58, and everything above the floor is
# conditional on the archive being the one these numbers were measured on --
# because MFT row indices and corpus totals are per-copy where file ids are
# content keys. Those eight are the three "row is the measured one" checks
# (sections 2 and 5), the four in section 5's ten-record map, which has no
# distinguished file id and can only be reached by row, and section 7's map-row
# population; all eight turn into declared skips on an archive with a different
# entry count. The 325/24 sequence split is a ninth, and needs `--all` as well.
# Everything else is unconditional: 6 in section 1, 11 in section 2, 8 in
# section 3, 3 in section 4, 10 in section 5, 4 in section 6, and 7 in section 7
# -- the --sample size changes how many maps those last seven walk, not how many
# checks run. If a run scores 48, a section stopped executing and the passes
# above it are not evidence of anything; if it scores 6, the vault was missing
# and only the offline section ran.
LEDGER = checks.Ledger("terrain codec", floor=49)
check = checks.adopt(LEDGER)


# -- a second framer, deliberately not the one under test --------------------

def walk_records(blob, start=8):
    """Frame the chunk with `int.from_bytes`, importing nothing from terrain.py.

    Same argument as test_archive.py's chunk-table walk: an independent
    structure that either consumes the block exactly or does not. Raises if the
    walk misses the final byte.

    `start` is the header length, and it is a parameter so the wrong one can be
    tried: 8 is terrain's and 12 is the PATHING chunk's, and FINDINGS measured
    the 12 control failing on 349 of 349 maps.
    """
    if len(blob) < start:
        raise ValueError(f"shorter than a {start}-byte header")
    sig = int.from_bytes(blob[0:4], "little")
    ver = int.from_bytes(blob[4:8], "little")
    out, p = [], start
    while p + 5 <= len(blob):
        tag = blob[p]
        size = int.from_bytes(blob[p + 1:p + 5], "little")
        out.append((tag, p + 5, size))
        p += 5 + size
        if tag == 255:
            break
    if p != len(blob):
        raise ValueError(f"walk ended at {p} of {len(blob)}")
    return sig, ver, out


def size_law(tag, nth, dx, dy, n, blob=None, body=None, size=None):
    """What a dims-derived reader consumes for one record. None = walked."""
    cells = dx * dy
    if tag == 0:
        return 26
    if tag == 1:
        return cells * 4
    if tag in (2, 9):
        return cells
    if tag in (4, 5):
        return 1 + n
    if tag == 3:
        return cells // 4 if nth == 0 else 17
    if tag == 255:
        return 0
    if tag == 7:
        blocks = (dx // 32) * (dy // 32)
        p, end = body, body + size
        for _ in range(blocks):
            k = int.from_bytes(blob[p:p + 4], "little")
            p += 4 + k + 128
            if p > end:
                return -1
        return p - body
    raise ValueError(f"no size law for tag {tag}")


def terrain_blob(archive, row, entry=None):
    """(chunk index, payload bytes, chunk count, ffna type, map rect)."""
    if entry is None:
        entry = next(e for e in archive.entries if e.index == row)
    data = archive.read(entry)
    blob = idx = rect = params_idx = None
    total = 0
    for i, (cid, off, size) in enumerate(ffna_chunks(data)):
        total += 1
        if cid == TERRAIN_CHUNK and blob is None:
            blob, idx = bytes(data[off:off + size]), i
        if cid == MAP_PARAMS_CHUNK and rect is None:
            if int.from_bytes(data[off:off + 4], "little") == MAP_PARAMS_SIG \
                    and data[off + 4] == 2:
                rect = struct.unpack_from("<4f", data, off + 5)
                params_idx = i
    return idx, blob, total, ffna_type(data), rect, params_idx


def raises(fn, *a, **kw):
    """True if `fn` refuses. A silent shrug is the failure this catches."""
    try:
        fn(*a, **kw)
    except Exception:                                          # noqa: BLE001
        return True
    return False


def reframe_size_first(blob):
    """The same records written `{u32 size, u8 tag}`. Must not decode."""
    _sig, _ver, recs = walk_records(blob)
    out = bytearray(blob[:8])
    for tag, body, size in recs:
        out += size.to_bytes(4, "little") + bytes((tag,)) + blob[body:body + size]
    return bytes(out)


def angle_b(angle):
    """The lattice index `b` nearest this angle, and the float32 bit distance."""
    b = int(round(angle / ANGLE_STEP))
    ref = struct.unpack("<f", struct.pack("<f", b * ANGLE_STEP))[0]
    ia = struct.unpack("<I", struct.pack("<f", angle))[0]
    ib = struct.unpack("<I", struct.pack("<f", ref))[0]
    return b, abs(ia - ib)


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=None,
                    help="archive to read; defaults to the vault's study copy")
    ap.add_argument("--sample", type=int, default=25,
                    help="how many maps section 7 round-trips")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    t0 = time.perf_counter()

    # -- 1. the codec with no ArenaNet bytes at all ----------------------
    # First, because it is the only section that runs on a bare machine, and
    # putting it after the archive would hide it behind a missing vault.
    print("\n1. A 32x32 map built from nothing, encoded and read back")
    made = Terrain.blank(32, 32, height=-13.0, tiles=3)
    raw = made.encode()
    back = Terrain.decode(raw)
    check(back.encode() == raw, "synthesised chunk survives its own round-trip",
          f"{len(raw)} bytes")
    check((back.dim_x, back.dim_y) == (32, 32), "dims survive",
          f"{back.dim_x}x{back.dim_y}")
    check(len(back.heights) == 1024 and set(back.heights) == {-13.0},
          "all 1024 heights come back as the value written")
    _sig, _ver, recs = walk_records(raw)
    check([t for t, _b, _s in recs] == list(SEQUENCE_SHORT),
          "the nine records are emitted in the client's order",
          f"{[t for t, _b, _s in recs]}")
    check(all(s == size_law(t, 0, 32, 32, 3, raw, b, s)
              for t, b, s in recs),
          "every emitted size obeys the dims-derived law")
    bigger = Terrain.blank(64, 96)
    check(len(bigger.shadow) == 2 * 3,
          "tag 7 gets one block per 32x32 tile", f"{len(bigger.shadow)} blocks")

    # -- resolve the archive ---------------------------------------------
    dat = args.dat
    if dat is None:
        try:
            dat = os.path.join(
                vaultpath.require_dir(
                    "dat_study", why="the terrain codec's only real fixture"),
                "Gw.dat")
        except SystemExit as exc:
            LEDGER.skip("every archive-backed section", str(exc).replace("\n", " | "))
            return LEDGER.verdict()

    with Archive(dat) as ar:
        table = file_id_table(ar)
        pinned_rows = ar.entry_count == MEASURED_ENTRY_COUNT

        def pin_row(label, got, want):
            if pinned_rows:
                check(got == want, f"{label} row is the measured one", f"{got}")
            else:
                LEDGER.skip(f"{label} row index",
                            f"archive has {ar.entry_count} entries, measured "
                            f"on {MEASURED_ENTRY_COUNT}")

        # -- 2. the reference chunk -------------------------------------
        print("\n2. Row 46196, the smallest complete map")
        row = table.get(SMALL_FILE_ID)
        check(row is not None, "the small map's file id resolves",
              f"0x{SMALL_FILE_ID:X} -> {row}")
        pin_row("small map", row, SMALL_ROW)
        entry = next(e for e in ar.entries if e.index == row)
        check(entry.flags == MAP_FLAGS, "the row carries map flags",
              f"flags {entry.flags}")
        idx, blob, total, ftype, rect, params_idx = terrain_blob(ar, row)
        check(ftype == 3, "the file is an ffna type 3 map", f"type {ftype}")
        check(total == SMALL_CHUNKS, "chunk count is the measured one",
              f"{total} chunks")
        check(idx == SMALL_CHUNK_INDEX, "terrain sits at the measured chunk "
              "index", f"index {idx}")
        check(len(blob) == SMALL_TERRAIN_BYTES, "terrain chunk is the measured "
              "size", f"{len(blob)} bytes")
        sig, ver, recs = walk_records(blob)
        check(sig == SIGNATURE and ver == VERSION,
              "signature and version", f"0x{sig:08X} v{ver}")
        trn = Terrain.decode(blob)
        check((trn.dim_x, trn.dim_y) == SMALL_DIMS, "dims",
              f"{trn.dim_x}x{trn.dim_y}")
        check(tuple((t, s) for t, _b, s in recs) == SMALL_RECORDS,
              "the nine records and their declared sizes are the measured ones")
        check(trn.chunk_distance == SMALL_TAG0_08 and trn.angle == SMALL_ANGLE
              and trn.tex_word == SMALL_TEX_WORD,
              "tag 0's non-dimension fields",
              f"+0x08 {trn.chunk_distance} angle {trn.angle} u16 {trn.tex_word}")
        check(trn.encode() == blob,
              "THE ROUND-TRIP: re-encode is byte-identical to the archive's "
              "bytes", f"{len(blob)} bytes")

        # -- 3. the size laws, re-derived here ---------------------------
        # Every one is refutable: wrong dims, wrong tiling or a wrong element
        # width desyncs the walk and lands the next tag byte on garbage.
        print("\n3. Five record lengths predicted by two u32s in tag 0, and "
              "the two tables that must agree")
        dx, dy = trn.dim_x, trn.dim_y
        n = len(trn.table_a)
        seen = {}
        laws = {}
        for tag, body, size in recs:
            nth = seen.get(tag, 0)
            seen[tag] = nth + 1
            laws[(tag, nth)] = (size, size_law(tag, nth, dx, dy, n,
                                               blob, body, size))
        for tag, label in ((1, "tag 1 is dx*dy float32 heights"),
                           (2, "tag 2 is one u8 per cell"),
                           (9, "tag 9 is one u8 per cell"),
                           (3, "tag 3 is dx*dy/4 bytes, 2 bits per cell"),
                           (7, "tag 7's block walk closes on the declared end")):
            got, want = laws[(tag, 0)]
            check(got == want, label, f"declared {got}, derived {want}")
        check(laws[(4, 0)][0] == laws[(5, 0)][0],
              "tag 4 and tag 5 declare the same length",
              f"{laws[(4, 0)][0]} bytes each")
        check(len(trn.shadow) == (dx // CHUNK_SIZE) * (dy // CHUNK_SIZE),
              "tag 7's block count came from dims, not from the file",
              f"{len(trn.shadow)} block(s)")
        check(trn.tiles and max(trn.tiles) <= n - 1,
              "every tile index is inside tag 4's table",
              f"max {max(trn.tiles)} of {n} entries")

        # -- 4. the cross-chunk check ------------------------------------
        print("\n4. Map Parameters and Terrain predicting each other")
        check(rect is not None and params_idx < idx,
              "Map Parameters is present and precedes Terrain",
              f"chunk index {params_idx} < {idx}")
        # Compared as BITS. `-0.0 == 0.0` is True in Python, so an equality
        # test here could not see the negative zero it claims to be checking --
        # and that negative zero is the one FINDINGS 17.4 cites as the proof
        # that the client's own rect formula is what wrote this file.
        check(struct.pack("<4f", *rect) == struct.pack("<4f", *SMALL_RECT)
              and math.copysign(1.0, rect[0]) < 0.0,
              "the rect is the measured one, negative zero included",
              f"{rect}")
        pitch = ((rect[2] - rect[0]) / dx, (rect[3] - rect[1]) / dy)
        wrong = ((rect[2] - rect[0]) / (dx - 1), (rect[3] - rect[1]) / (dy - 1))
        check(pitch == (CELL_PITCH, CELL_PITCH)
              and wrong != (CELL_PITCH, CELL_PITCH),
              "rect/dims is exactly 96.0 and the (dim-1) control is not",
              f"{pitch} vs control {wrong[0]:.2f}")

        # -- 5. the three larger fixtures --------------------------------
        print("\n5. Kamadan, Pre-Searing, and a map with the long sequence")
        for label, fid, want_row, want_idx, want_bytes, want_dims in (
                ("Kamadan", KAMADAN_FILE_ID, KAMADAN_ROW, KAMADAN_CHUNK_INDEX,
                 KAMADAN_TERRAIN_BYTES, KAMADAN_DIMS),
                ("Pre-Searing", PRESEARING_FILE_ID, PRESEARING_ROW,
                 PRESEARING_CHUNK_INDEX, PRESEARING_TERRAIN_BYTES,
                 PRESEARING_DIMS)):
            r = table.get(fid)
            check(r is not None, f"{label} file id resolves", f"0x{fid:X} -> {r}")
            pin_row(label, r, want_row)
            i2, b2, _t2, _f2, r2, p2 = terrain_blob(ar, r)
            m = Terrain.decode(b2)
            check(i2 == want_idx and len(b2) == want_bytes,
                  f"{label} terrain chunk index and size",
                  f"index {i2}, {len(b2)} bytes")
            check((m.dim_x, m.dim_y) == want_dims, f"{label} dims",
                  f"{m.dim_x}x{m.dim_y}")
            check(m.encode() == b2, f"{label} round-trips byte-identically",
                  f"{len(b2)} bytes")
            check(p2 < i2 and (r2[2] - r2[0]) / m.dim_x == CELL_PITCH
                  and (r2[3] - r2[1]) / m.dim_y == CELL_PITCH,
                  f"{label} rect/dims is 96.0 on both axes", f"{r2}")

        if not pinned_rows:
            LEDGER.skip("the ten-record map",
                        f"row {LONG_SEQ_ROW} is pinned by index -- it has no "
                        f"distinguished file id -- and this archive has "
                        f"{ar.entry_count} entries, measured on "
                        f"{MEASURED_ENTRY_COUNT}")
        else:
            _i3, b3, _t3, _f3, _r3, _p3 = terrain_blob(ar, LONG_SEQ_ROW)
            long_map = Terrain.decode(b3)
            _s3, _v3, recs3 = walk_records(b3)
            check(long_map.order == SEQUENCE_LONG,
                  "a second tag-3 record is decoded, not dropped",
                  f"{long_map.order}")
            check(tuple(s for _t, _b, s in recs3) == LONG_SEQ_SIZES,
                  "its ten declared sizes are the measured ones")
            check(long_map.tag3b is not None and long_map.tag3b[0] == 1
                  and len(long_map.tag3b[1]) == 4,
                  "tag 3' is a u8 lead plus four f32",
                  f"lead {long_map.tag3b[0]}")
            check(long_map.encode() == b3,
                  "the ten-record map round-trips byte-identically",
                  f"{len(b3)} bytes")

        # -- 6. the controls that must go red ----------------------------
        # Without these the headline check is unfalsifiable.
        print("\n6. Negative controls")
        # (a) content sensitivity: perturb one byte of a real chunk.
        h_off = next(b for t, b, _s in recs if t == 1)
        bent = bytearray(blob)
        bent[h_off] ^= 0x01
        bent = bytes(bent)
        rebuilt = Terrain.decode(bent).encode()
        check(rebuilt == bent and rebuilt != blob,
              "one flipped height byte changes the re-encode",
              "the round-trip tracks content, not just framing")
        # (b) a mutated semantic field must not silently re-emit the original.
        mutated = Terrain.decode(blob)
        mutated.dim_x += CHUNK_SIZE
        check(raises(mutated.encode),
              "dims + 32 is refused rather than encoded",
              f"{len(mutated.validate())} reason(s) reported")
        # (c) framing and gate controls, each of which must RAISE.
        def bytes_with(off, value):
            b = bytearray(blob)
            b[off:off + len(value)] = value
            return bytes(b)

        # A tag 7 one byte short, with its declared size adjusted to match, so
        # the outer framing still walks perfectly and only the block walk can
        # notice. This is the case the CLIENT reads past the end of without a
        # bounds check; our walker has to be the stricter one.
        s7_body = next(b for t, b, _s in recs if t == 7)
        s7_size = next(s for t, _b, s in recs if t == 7)
        short7 = (blob[:s7_body - 4] + (s7_size - 1).to_bytes(4, "little")
                  + blob[s7_body:s7_body + s7_size - 1]
                  + blob[s7_body + s7_size:])

        controls = [
            ("a flipped signature byte",
             lambda: Terrain.decode(bytes_with(0, b"\x35"))),
            ("version 0x00110000 (the client compares the full u32)",
             lambda: Terrain.decode(bytes_with(4, b"\x00\x00\x11\x00"))),
            ("a tag 7 one byte short of its block walk",
             lambda: Terrain.decode(short7)),
            ("tag 5 declaring a different n than tag 4",
             lambda: Terrain.decode(bytes_with(
                 next(b for t, b, _s in recs if t == 5), b"\x02"))),
            ("an out-of-order tag",
             lambda: Terrain.decode(bytes_with(
                 next(b for t, b, _s in recs if t == 2) - 5, b"\x09"))),
            ("the {u32 size, u8 tag} framing",
             lambda: Terrain.decode(reframe_size_first(blob))),
            ("a walk started at +12, the PATHING chunk's header length",
             lambda: walk_records(blob, 12)),
            ("the STRIPPED chunk id 0x10000002",
             lambda: Terrain.from_chunk(blob, STRIPPED_TERRAIN_CHUNK)),
        ]
        shrugged = [name for name, fn in controls if not raises(fn)]
        check(not shrugged, "every framing and gate control is refused",
              f"{len(controls) - len(shrugged)}/{len(controls)}"
              + ("; shrugged at " + ", ".join(shrugged) if shrugged else ""))
        # (d) the encoder's own refusals, on values the corpus never contains.
        t5 = Terrain.decode(blob)
        t5.table_b = bytes((0x80,)) + t5.table_b[1:]
        t6 = Terrain.decode(blob)
        t6.tiles = bytes((len(t6.table_a),)) + t6.tiles[1:]
        t7 = Terrain.decode(blob)
        t7.shadow = t7.shadow + [ShadowBlock(b"", bytes(SHADOW_TAIL))]
        check(raises(t5.encode) and raises(t6.encode) and raises(t7.encode),
              "a bit-7 tag-5 byte, an out-of-range tile and a spare tag-7 "
              "block are all refused",
              "0 of 17,089 corpus tag-5 bytes set bit 7")

        # -- 7. the corpus -----------------------------------------------
        rows = [e for e in ar.entries if e.flags == MAP_FLAGS]
        # "349 of 349" is only a number about the corpus if the corpus size is
        # asserted somewhere. Without this, a wrong MAP_FLAGS would select three
        # rows and the headline below would print "3 of 3" and go green -- the
        # test_codec.py glob-matching-nothing failure at one remove.
        if pinned_rows:
            check(len(rows) == CORPUS_MAPS,
                  "the map-row population is the measured one",
                  f"{len(rows)} rows with flags {MAP_FLAGS}")
        else:
            LEDGER.skip("the map-row population",
                        f"{len(rows)} rows with flags {MAP_FLAGS}; measured "
                        f"{CORPUS_MAPS} on an archive of "
                        f"{MEASURED_ENTRY_COUNT} entries")
        picks = rows if args.all else rows[::max(1, len(rows) // args.sample)]
        print(f"\n7. Round-trip across {len(picks)} of {len(rows)} maps")
        ok = 0
        broke = []
        seq = {}
        blocks = tails = 0
        pitch_pairs = {}
        tag5_high = tag2_over = tag2_eq = 0
        ang_ok = ang_exact = ang_seen = 0
        h_exact = h_total = 0
        for e in picks:
            try:
                i4, b4, _t4, _f4, r4, p4 = terrain_blob(ar, e.index, entry=e)
                if b4 is None:
                    broke.append((e.index, "no terrain chunk"))
                    continue
                m = Terrain.decode(b4)
                if m.encode() == b4:
                    ok += 1
                else:
                    broke.append((e.index, "re-encode differs"))
                seq[m.order] = seq.get(m.order, 0) + 1
                blocks += len(m.shadow)
                tails += sum(1 for s in m.shadow if len(s.tail) == SHADOW_TAIL)
                if r4 is not None and p4 < i4:
                    pitch_pairs[((r4[2] - r4[0]) / m.dim_x,
                                 (r4[3] - r4[1]) / m.dim_y)] = 1
                tag5_high += sum(1 for v in m.table_b if v & 0x80)
                hi = max(m.tiles)
                tag2_over += hi > len(m.table_a) - 1
                tag2_eq += hi == len(m.table_a) - 1
                b, dist = angle_b(m.angle)
                ang_seen += 1
                ang_ok += (ANGLE_B_RANGE[0] <= b <= ANGLE_B_RANGE[1]
                           and dist <= 1)
                ang_exact += dist == 0
                h_total += len(m.heights)
                h_exact += sum(1 for h in m.heights
                               if h == h and -math.inf < h < math.inf
                               and h == int(h))
            except Exception as exc:                           # noqa: BLE001
                broke.append((e.index, str(exc)[:70]))
        check(not broke and picks and ok == len(picks),
              "EVERY sampled map round-trips byte-identically",
              f"{ok} of {len(picks)}")
        for r_i, why in broke[:6]:
            print(f"        row {r_i}: {why}")
        check(set(seq) <= {SEQUENCE_SHORT, SEQUENCE_LONG}
              and seq.get(SEQUENCE_SHORT, 0) > 0,
              "only the two legal tag sequences occur",
              " ".join(f"{len(k)} records x{v}" for k, v in sorted(
                  seq.items(), key=lambda kv: len(kv[0]))))
        # The 325/24 split is a corpus fact and only a full sweep can see it. A
        # sampled run declares the skip rather than leaving the two constants
        # sitting in the header looking like they were checked.
        if args.all and pinned_rows:
            check(seq.get(SEQUENCE_SHORT, 0) == CORPUS_SEQ_SHORT
                  and seq.get(SEQUENCE_LONG, 0) == CORPUS_SEQ_LONG,
                  "the corpus splits into the measured 325 nine-record and 24 "
                  "ten-record maps",
                  f"{seq.get(SEQUENCE_SHORT, 0)} / {seq.get(SEQUENCE_LONG, 0)}")
        else:
            LEDGER.skip("the 325/24 sequence split",
                        "only --all on the measured archive walks every map")
        check(blocks > 0 and tails == blocks,
              "every tag-7 block walked carries a 128-byte tail",
              f"{blocks} blocks")
        check(set(pitch_pairs) == {(CELL_PITCH, CELL_PITCH)},
              "rect/dims is 96.0 and nothing else, across the sample",
              f"{len(pitch_pairs)} distinct pitch pair(s)")
        check(tag5_high == 0 and tag2_over == 0 and tag2_eq > 0,
              "tag 5 never sets bit 7 and no tile index escapes tag 4",
              f"{tag2_eq} maps attain max == n-1, {tag2_over} exceed")
        check(ang_seen and ang_ok == ang_seen,
              "every angle is within 1 ULP of b*pi/508, b in [16, 250] "
              "(NOT bit-exact -- see terrain.py)",
              f"{ang_ok}/{ang_seen} within 1 ULP, {ang_exact} bit-exact")
        # Not a codec property, and it is the check most likely to go red for
        # an honest reason on some future archive -- but a NaN height is the one
        # float32 bit pattern this module could fail to reproduce, so if the
        # corpus ever grows one we want to hear about it here rather than in a
        # silent mismatch.
        check(h_total > 0 and h_exact == h_total,
              "every height sample is finite AND an exact integer",
              f"{h_exact} of {h_total}")

    print(f"\nwalked the archive in {time.perf_counter() - t0:.1f}s")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
