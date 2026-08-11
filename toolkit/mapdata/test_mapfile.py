"""Check the whole-map-file codec against the real archive, in both stages.

THE HEADLINE IS THE ROUND-TRIP: decode a retail map file into a typed container,
throw the original bytes away, re-encode, and require the result to be
byte-identical -- on 349 Bloated files AND on 349 Stripped files. Sections 4 and
5 are that, sampled by default and complete with `--all`. Everything else exists
to stop it being the kind of green light this repository refuses.

THE ONE FAILURE MODE THIS FILE IS BUILT AROUND. A container codec that stores
each chunk's declared `size` and writes it back round-trips EVERY file it can
walk, including every chunk kind it understood nothing about -- and `mapfile.py`
carries seventeen of the nineteen kinds as opaque bytes. That codec would print
698 of 698 and would be a memcpy. So section 2 does not merely assert that
mutations break the file; it decodes a file, mutates a decoded chunk until its
encoded payload changes LENGTH, and reads the emitted table's size field back
with a walker written here out of `int.from_bytes`, requiring it to have moved
with the payload. A stored-size encoder fails that check and passes everything
else.

WHAT ELSE IS DELIBERATE.

  * Section 1 builds a whole map file out of nothing -- a `Terrain.blank()`
    chunk, a Dependencies chunk, four opaque ones -- and runs on a bare machine
    with no vault. It goes first so it cannot hide behind a missing archive.
  * Sections 2's controls are run on the SYNTHETIC file (bare machine) and
    section 6 repeats the four that matter on a retail file, because a control
    that only ever fires on our own bytes is weaker than one that fires on
    ArenaNet's.
  * **The population is asserted.** B1 shipped a defect where `ok == len(picks)`
    passed over a row filter whose size nothing checked: a wrong flags constant
    would have selected three rows and printed "3 of 3", green. Here the head
    count, the pair count, the sample size and the per-file chunk counts are all
    checks, and an empty sample cannot pass.
  * Section 5 does not assume the Stripped stream works because the Bloated one
    does. It requires the Stripped terrain chunk `0x10000002` to be CARRIED, and
    requires `terrain.Terrain.from_chunk` to refuse it -- so "the container codec
    does not care about the framing inside a chunk" is measured rather than
    asserted.

MEASURED VALUES ARE THIS ARCHIVE'S. File ids are content keys and travel; MFT
row indices do not, so the row-pinned section declares a skip when the entry
count differs.

A MISSING VAULT IS A FAILURE HERE, NOT A SKIP. Sections 1 and 2 still run and
their checks are still printed, but a run with no archive has measured nothing
about ArenaNet's format, so the floor rule turns them into the FAIL they are.

    python toolkit/mapdata/test_mapfile.py
    python toolkit/mapdata/test_mapfile.py --sample 20
    python toolkit/mapdata/test_mapfile.py --all      # 698 files, ~13 minutes
"""

import argparse
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, FFNA_MAGIC  # noqa: E402
from mapchunks import (MapIndex, compose, encode_dependencies,  # noqa: E402
                       STAGE_BLOATED, STAGE_STRIPPED, TYPE_DATA,
                       TYPE_DEPENDENCIES)
from terrain import Terrain, TERRAIN_CHUNK, STRIPPED_TERRAIN_CHUNK  # noqa: E402
from mapfile import (MapFile, FORM_TERRAIN, FORM_DEPENDENCIES,  # noqa: E402
                     FORM_OPAQUE, byte_census, add_census)
import checks  # noqa: E402
import vaultpath  # noqa: E402

# Corpus constants. MEASURED on this archive 2026-08-11 by a full 698-file
# sweep. CORPUS_MAPS is not decoration -- it is what stops a wrong row filter
# from printing "3 of 3" and going green.
MEASURED_ENTRY_COUNT = 177342
CORPUS_MAPS = 349
CORPUS_CHUNKS_BLOATED = 8047
CORPUS_CHUNKS_STRIPPED = 8047

# Row 46196, the smallest complete map in the archive. The file id is the
# portable key; the row is pinned separately and skipped on a different copy.
SMALL_FILE_ID = 0x22E2C
SMALL_ROW = 46196
SMALL_PARTNER_ROW = 46197
SMALL_BYTES = 8471
SMALL_PARTNER_BYTES = 2951
SMALL_CHUNKS = 18
SMALL_DIMS = (32, 32)
# The Bloated head's chunk table, in file order, as (id, payload size).
SMALL_TABLE = ((0x20000000, 8), (0x2000000C, 41), (0x20000004, 51),
               (0x20000003, 42), (0x2000000E, 9), (0x20000002, 7165),
               (0x21000002, 29), (0x20000007, 69), (0x20000006, 5),
               (0x21000006, 197), (0x20000008, 419), (0x20000009, 178),
               (0x21000009, 11), (0x2000000A, 13), (0x2000000F, 7),
               (0x20000010, 17), (0x20000011, 44), (0x20000012, 17))
SMALL_DEP_REFS = (4, 32, 1)          # Terrain, Water, Environment
SMALL_TERRAIN_DEP = 0x21000002

KAMADAN_ROW = 22371

# Set from a real green run: a default `python toolkit/mapdata/test_mapfile.py`
# on this machine executes 50 checks, 25 of them on a bare machine with no
# vault at all. `--all` adds the two sweep-population checks, for 52.
LEDGER = checks.Ledger("map file codec", floor=50)
check = checks.adopt(LEDGER)


# ---------------------------------------------------------- the independent
# walker. Imports nothing from mapfile: a codec agreeing with itself about its
# own framing proves nothing, and the size-derivation check below is only
# evidence because this reads the emitted table with different code.

def walk_table(data):
    """(chunks, landing, overrun) for an ffna file; chunks is [(id, off, size)].

    Deliberately tolerant where `ffna_chunks` raises -- a control that perturbs
    a size field needs to see WHERE the walk landed, not an exception.
    """
    if data[:4] != b"ffna":
        raise ValueError(f"not ffna: {data[:4]!r}")
    pos, out = 5, []
    while pos + 8 <= len(data):
        cid = int.from_bytes(data[pos:pos + 4], "little")
        size = int.from_bytes(data[pos + 4:pos + 8], "little")
        if pos + 8 + size > len(data):
            return out, pos, size          # overruns: report it, do not raise
        out.append((cid, pos + 8, size))
        pos += 8 + size
    return out, pos, None


def size_field_at(data, index):
    """The `size` u32 of the index-th table entry, read straight out of bytes.

    None when the walk cannot reach that entry, which is what a wrong size
    field upstream of it produces. A control that CRASHES here has still gone
    red, but a control that reports its number is worth more, so this returns a
    value the comparison can simply fail against.
    """
    chunks, _pos, _over = walk_table(data)
    if index >= len(chunks):
        return None
    return int.from_bytes(data[chunks[index][1] - 4:chunks[index][1]], "little")


def entry_offset(data, index):
    """Where the index-th table entry's 8-byte header starts, or None."""
    chunks, _pos, _over = walk_table(data)
    return chunks[index][1] - 8 if index < len(chunks) else None


def set_size_field(data, index, value):
    """Overwrite one table entry's size. For the negative controls only."""
    chunks, _pos, _over = walk_table(data)
    off = chunks[index][1] - 4
    return data[:off] + struct.pack("<I", value) + data[off + 4:]


# --------------------------------------------------- section 1: from nothing

def synthetic_map():
    """A whole map file built out of nothing. ZERO ArenaNet bytes.

    Packed here with `struct`, not by `mapfile`, so section 1 compares the
    module's decode against a file this test wrote rather than against itself.
    """
    trn = Terrain.blank(32, 32, height=0.0, tiles=4)
    deps = encode_dependencies([SMALL_FILE_ID, 0x345CC, 0x1B97D])
    parts = [
        (compose(STAGE_BLOATED, TYPE_DATA, 0x00), bytes(8)),
        (compose(STAGE_BLOATED, TYPE_DATA, 0x0C), bytes(41)),
        (TERRAIN_CHUNK, trn.encode()),
        (compose(STAGE_BLOATED, TYPE_DEPENDENCIES, 0x02), deps),
        (compose(STAGE_BLOATED, TYPE_DATA, 0x08), b"a synthetic path chunk"),
        (compose(STAGE_BLOATED, TYPE_DATA, 0x12), b"\x01\x02\x03"),
    ]
    out = bytearray(b"ffna")
    out.append(3)
    for cid, payload in parts:
        out += struct.pack("<II", cid, len(payload))
        out += payload
    return bytes(out), parts


def section1():
    print("\n-- 1. a whole map file built from nothing (no vault needed)")
    blob, parts = synthetic_map()
    mf = MapFile.decode(blob)

    check(mf.encode() == blob,
          "synthetic map round-trips byte-identically",
          f"{len(blob)} bytes, {len(mf)} chunks")
    check(mf.ids == [cid for cid, _p in parts],
          "chunk order is preserved exactly",
          f"{len(mf)} chunks in file order")
    check(mf.ffna_type == 3 and mf.magic == FFNA_MAGIC,
          "magic and type byte survive the round-trip",
          f"{mf.magic!r} type {mf.ffna_type}")

    forms = [c.form for c in mf.chunks]
    check(forms == [FORM_OPAQUE, FORM_OPAQUE, FORM_TERRAIN, FORM_DEPENDENCIES,
                    FORM_OPAQUE, FORM_OPAQUE],
          "dispatch: terrain and dependencies decoded, four kinds carried",
          str(forms))
    trn = mf.terrain()
    check(trn is not None and (trn.dim_x, trn.dim_y) == (32, 32),
          "the terrain chunk came back as a typed Terrain",
          f"{trn.dim_x}x{trn.dim_y}" if trn else "None")
    dep = mf.dependencies()
    check(len(dep) == 1 and len(dep[0][1]) == 3,
          "the dependencies chunk came back as 3 typed references",
          f"{len(dep)} chunk(s)")
    check(not mf.failures(), "no chunk fell back to opaque after a failed decode",
          f"{len(mf.failures())} fallbacks")

    # Every declared size equals what the payload actually measures, read by the
    # walker above rather than by the module.
    emitted = mf.encode()
    table, landing, over = walk_table(emitted)
    check(over is None and landing == len(emitted),
          "the emitted chunk table consumes the file to the exact byte",
          f"landed at {landing} of {len(emitted)}")
    good = sum(1 for (cid, off, size), (_c, p) in zip(table, parts)
               if size == len(p) and emitted[off:off + size] == p)
    check(len(table) == len(parts) and good == len(parts),
          "every emitted size field equals its payload's real length",
          f"{good} of {len(parts)}")

    cen = byte_census(mf)
    check(cen["total"] == len(blob)
          and cen["reconstructed"] + cen["carried"] + cen["framing"] == len(blob),
          "the byte census accounts for every byte of the file",
          f"{cen['reconstructed']} reconstructed, {cen['carried']} carried, "
          f"{cen['framing']} framing")

    for label, bad in (("a non-ffna blob", b"xxxx\x03"),
                       ("a 3-byte blob", b"ffn"),
                       ("an empty blob", b"")):
        try:
            MapFile.decode(bad)
            ok = False
        except ValueError:
            ok = True
        check(ok, f"{label} is refused rather than half-parsed")

    # A chunk whose id says "Dependencies" and whose payload is not one. The
    # default must RAISE -- a codec that silently carried it would report a
    # round-trip over bytes it had refused to read, which is the same defect as
    # a stored size wearing different clothes. The opt-in fallback must both
    # carry it AND name it.
    broken = bytearray(blob)
    dep_off = walk_table(blob)[0][3][1]
    broken[dep_off] ^= 0xFF                 # break the 0x29939830 signature
    broken = bytes(broken)
    try:
        MapFile.decode(broken)
        strict_raised = False
    except ValueError:
        strict_raised = True
    check(strict_raised,
          "a dependencies chunk that will not decode is REFUSED by default")
    loose = MapFile.decode(broken, strict=False)
    fails = loose.failures()
    check(len(fails) == 1 and fails[0].chunk_id == parts[3][0]
          and fails[0].form == FORM_OPAQUE,
          "strict=False carries it, and NAMES it rather than counting it as a"
          " clean round-trip",
          f"{len(fails)} reported: {fails[0].note[:44] if fails else '-'}")
    check(loose.encode() == broken,
          "and the carried-through file still re-encodes byte-identically")


# ----------------------------------------- section 2: the controls, bare metal

def section2():
    print("\n-- 2. negative controls (no vault needed) -- each MUST go red")
    blob, parts = synthetic_map()

    # (a) the LAST chunk's size grows past the end of the file.
    bad = set_size_field(blob, len(parts) - 1, len(parts[-1][1]) + 4)
    try:
        MapFile.decode(bad)
        ok = False
        why = "decoded anyway"
    except ValueError as exc:
        ok = True
        why = str(exc)[:60]
    check(ok, "control: last chunk's size +4 is refused", why)

    # (b) a MIDDLE chunk's size grows, desyncing the walk. Either the walk
    # refuses or the re-encode differs -- both are red, and it must be one.
    bad = set_size_field(blob, 1, len(parts[1][1]) + 4)
    try:
        rt = MapFile.decode(bad).encode() == bad
        why = "round-tripped" if rt else "re-encode differs"
        ok = not rt
    except ValueError as exc:
        ok = True
        why = f"refused: {str(exc)[:50]}"
    check(ok, "control: a middle chunk's size +4 does not round-trip", why)

    # (c) reordering chunks must change the file.
    mf = MapFile.decode(blob)
    mf.chunks[0], mf.chunks[1] = mf.chunks[1], mf.chunks[0]
    check(mf.encode() != blob, "control: two chunks swapped changes the bytes",
          f"{len(mf.encode())} bytes emitted")

    # (d) truncation, four bytes off the tail.
    try:
        MapFile.decode(blob[:-4])
        ok = False
        why = "decoded anyway"
    except ValueError as exc:
        ok = True
        why = str(exc)[:60]
    check(ok, "control: a truncated file is refused", why)

    # (e) THE MEMCPY TRAP. Mutate a decoded chunk so its payload gets LONGER,
    # and require the emitted table's size field to have moved with it. An
    # encoder that replayed a stored size fails here and nowhere else.
    #
    # THE MUTATION IS IN PLACE, and that is the whole design of this control.
    # The first version of it replaced `mf.chunks[idx]` with a freshly built
    # Chunk -- and a sabotaged encoder that stamps a stored size onto each
    # chunk at DECODE time passed the entire section, every check green,
    # because the replacement carried no stored size to go stale. Mutating the
    # object the decoder itself built leaves any stored size exactly where it
    # was. Both stored-size shapes were then sabotaged and both go red here:
    # one size per Chunk, and one list of sizes per MapFile.
    mf = MapFile.decode(blob)
    idx = 3                                   # the Dependencies chunk
    chunk = mf.chunks[idx]
    original = len(chunk.payload())
    chunk.value.entries = chunk.value.entries + ((0x0002, 0x0101, 0),)
    out = mf.encode()
    field = size_field_at(out, idx)
    check(field == original + 6 and field == len(mf.chunks[idx].payload()),
          "the size field is DERIVED: a grown dependencies chunk moves it",
          f"{original} -> {field} bytes for one extra 6-byte reference")
    check(len(out) == len(blob) + 6,
          "and the file grew by exactly that much",
          f"{len(blob)} -> {len(out)}")
    table, landing, over = walk_table(out)
    check(over is None and landing == len(out) and len(table) == len(parts),
          "the mutated file still walks to its exact final byte",
          f"{len(table)} chunks, landed at {landing}")

    # (f) the same trap for a SHRINKING opaque chunk, which is the other side.
    # In place again, for the same reason.
    mf = MapFile.decode(blob)
    idx = 4
    was = len(mf.chunks[idx].payload())
    mf.chunks[idx].value = b"tiny"
    out = mf.encode()
    check(size_field_at(out, idx) == 4 and len(out) == len(blob) - (was - 4),
          "the size field is DERIVED: a shrunk opaque chunk moves it too",
          f"{was} -> {size_field_at(out, idx)}")

    # (g) the positive control for (e) and (f): unmutated, it still matches.
    check(MapFile.decode(blob).encode() == blob,
          "positive control: the unmutated synthetic file still round-trips")


# ------------------------------------------------- sections 3-7: the archive

def pinned(ar, mi):
    print("\n-- 3. the pinned map, row 46196 (smallest complete map)")
    if ar.entry_count != MEASURED_ENTRY_COUNT:
        LEDGER.skip("row-pinned checks",
                    f"archive has {ar.entry_count} rows, these values were "
                    f"measured on {MEASURED_ENTRY_COUNT}; file ids travel, "
                    f"row indices do not")
        return
    head = mi.by_row[SMALL_ROW]
    partner = mi.partner(head)
    check(partner is not None and partner.index == SMALL_PARTNER_ROW,
          "the map's Stripped partner is the row nextStream names",
          f"row {partner.index if partner else '-'}")

    data = ar.read(head)
    mf = MapFile.decode(data)
    check(len(data) == SMALL_BYTES and len(mf) == SMALL_CHUNKS,
          "the Bloated head is the file we measured",
          f"{len(data)} bytes, {len(mf)} chunks")
    table = tuple((c.chunk_id, len(c.payload())) for c in mf.chunks)
    check(table == SMALL_TABLE,
          "every chunk id and size matches, in file order",
          f"{sum(1 for a, b in zip(table, SMALL_TABLE) if a == b)} of "
          f"{len(SMALL_TABLE)} entries agree")
    trn = mf.terrain()
    check(trn is not None and (trn.dim_x, trn.dim_y) == SMALL_DIMS,
          "its terrain decoded to the dims the terrain codec measured",
          f"{trn.dim_x}x{trn.dim_y}" if trn else "no terrain chunk")
    refs = tuple(len(d) for _cid, d in mf.dependencies())
    check(refs == SMALL_DEP_REFS,
          "its three Dependencies chunks hold the reference counts we measured",
          f"{refs}")
    check(mf.encode() == data,
          "and the whole file re-encodes byte-identically")

    pdata = ar.read(partner)
    pmf = MapFile.decode(pdata)
    check(len(pdata) == SMALL_PARTNER_BYTES and len(pmf) == SMALL_CHUNKS,
          "the Stripped partner is the file we measured",
          f"{len(pdata)} bytes, {len(pmf)} chunks")
    check(pmf.encode() == pdata,
          "and it re-encodes byte-identically through the same code")


class Sweep:
    """What one pass over a set of map files measured. One decode per file.

    Every count here is a population the checks below can refuse -- the point
    of carrying `files` and `chunks` rather than just `ok` is that `ok ==
    len(entries)` over an empty or wrongly-filtered selection is exactly the
    defect B1 shipped.
    """

    def __init__(self):
        self.files = 0
        self.ok = 0
        self.chunks = 0
        self.census = {}
        self.right_stage = 0            # files whose ids all carry the stage
        self.terrain_carried = 0        # files where 0x10000002 is opaque
        self.bad_dispatch = []          # form disagreeing with the id's type
        self.problems = []


def corpus(ar, entries, stage_nibble):
    """Decode, re-encode and audit a set of files. Returns a Sweep."""
    s = Sweep()
    for e in entries:
        data = ar.read(e)
        s.files += 1
        try:
            mf = MapFile.decode(data)
            out = mf.encode()
        except Exception as exc:                            # noqa: BLE001
            s.problems.append(f"row {e.index}: {type(exc).__name__}: {exc}")
            continue
        if out == data:
            s.ok += 1
        else:
            k = min(len(out), len(data))
            first = next((i for i in range(k) if out[i] != data[i]), k)
            s.problems.append(f"row {e.index}: differs at byte {first} "
                              f"({len(out)} vs {len(data)} bytes)")
        s.chunks += len(mf)
        add_census(s.census, byte_census(mf))
        for c in mf.failures():
            s.problems.append(f"row {e.index} chunk 0x{c.chunk_id:08X}: {c.note}")

        if all((c.chunk_id >> 28) == stage_nibble for c in mf.chunks):
            s.right_stage += 1
        t = mf.find(STRIPPED_TERRAIN_CHUNK)
        if t is not None and t.form == FORM_OPAQUE:
            s.terrain_carried += 1
        # The dispatch invariant, checked against the id rather than against
        # the function that produced the form: a Dependencies chunk is exactly
        # a chunkType-1 id, terrain is exactly 0x20000002, and nothing else may
        # claim to have been reconstructed.
        for c in mf.chunks:
            ctype = (c.chunk_id >> 24) & 0xF
            want = (FORM_DEPENDENCIES if ctype == TYPE_DEPENDENCIES
                    else FORM_TERRAIN if c.chunk_id == TERRAIN_CHUNK
                    else FORM_OPAQUE)
            if c.form != want:
                s.bad_dispatch.append(
                    f"row {e.index} 0x{c.chunk_id:08X}: {c.form} not {want}")
    for line in s.problems[:8]:
        print(f"      ! {line}")
    if len(s.problems) > 8:
        print(f"      ! ... and {len(s.problems) - 8} more")
    return s


def section45(ar, mi, picks, want_all):
    heads = [h for h, _p in picks]
    partners = [p for _h, p in picks]

    print(f"\n-- 4. Bloated round-trip over {len(heads)} maps")
    check(len(mi.heads) == CORPUS_MAPS and len(mi.pairs) == CORPUS_MAPS,
          "the population is what it should be before anything is measured",
          f"{len(mi.heads)} map heads, {len(mi.pairs)} with a Stripped partner")
    check(len(picks) > 0 and len(picks) <= len(mi.pairs),
          "the sample is non-empty and drawn from that population",
          f"{len(picks)} of {len(mi.pairs)}")

    t0 = time.perf_counter()
    sb = corpus(ar, heads, STAGE_BLOATED)
    dt = time.perf_counter() - t0
    check(sb.files == len(heads) and sb.ok == sb.files,
          "Bloated map files re-encode byte-identically",
          f"{sb.ok} of {sb.files} in {dt:.0f}s")
    check(sb.files > 0 and sb.right_stage == sb.files and not sb.bad_dispatch,
          "every Bloated chunk id carries stage 2 and dispatched by its type",
          f"{sb.right_stage} of {sb.files} files, "
          f"{len(sb.bad_dispatch)} misdispatched chunks")
    if want_all:
        check(sb.files == CORPUS_MAPS and sb.chunks == CORPUS_CHUNKS_BLOATED,
              "--all really did sweep all 349 Bloated files",
              f"{sb.files} files, {sb.chunks} chunks "
              f"(expected {CORPUS_CHUNKS_BLOATED})")
    else:
        LEDGER.skip("the full 349-file Bloated sweep",
                    f"sampled {sb.files}; run with --all")

    print(f"\n-- 5. Stripped round-trip over {len(partners)} maps")
    t0 = time.perf_counter()
    ss = corpus(ar, partners, STAGE_STRIPPED)
    dt = time.perf_counter() - t0
    check(ss.files == len(partners) and ss.ok == ss.files,
          "Stripped map files re-encode byte-identically",
          f"{ss.ok} of {ss.files} in {dt:.0f}s")
    if want_all:
        check(ss.files == CORPUS_MAPS and ss.chunks == CORPUS_CHUNKS_STRIPPED,
              "--all really did sweep all 349 Stripped files",
              f"{ss.files} files, {ss.chunks} chunks "
              f"(expected {CORPUS_CHUNKS_STRIPPED})")
    else:
        LEDGER.skip("the full 349-file Stripped sweep",
                    f"sampled {ss.files}; run with --all")

    # The Stripped stage is not assumed to work because the Bloated one did.
    check(ss.files > 0 and ss.right_stage == ss.files and not ss.bad_dispatch,
          "every chunk id in every Stripped file carries stage nibble 1",
          f"{ss.right_stage} of {ss.files} files, "
          f"{len(ss.bad_dispatch)} misdispatched chunks")
    check(ss.files > 0 and ss.terrain_carried == ss.files,
          "the Stripped terrain chunk 0x10000002 is CARRIED, not mis-parsed",
          f"{ss.terrain_carried} of {ss.files} files")
    check(sb.terrain_carried == 0,
          "and no BLOATED file was found carrying it, so that is a real split",
          f"{sb.terrain_carried} of {sb.files} Bloated files")
    try:
        Terrain.from_chunk(b"\x00" * 64, STRIPPED_TERRAIN_CHUNK)
        refused = False
    except ValueError:
        refused = True
    check(refused,
          "and the terrain codec refuses it by id, so carrying it is deliberate")
    return sb.census, ss.census


def section6(ar, mi):
    print("\n-- 6. the same controls on ArenaNet's bytes, row 46196")
    if ar.entry_count != MEASURED_ENTRY_COUNT:
        LEDGER.skip("retail negative controls",
                    f"pinned to row {SMALL_ROW} on a {MEASURED_ENTRY_COUNT}-row "
                    f"archive; this one has {ar.entry_count}")
        return
    data = ar.read(mi.by_row[SMALL_ROW])

    bad = set_size_field(data, len(SMALL_TABLE) - 1, SMALL_TABLE[-1][1] + 4)
    try:
        MapFile.decode(bad)
        ok = False
    except ValueError:
        ok = True
    check(ok, "control: a retail file's last size field +4 is refused")

    try:
        MapFile.decode(data[:-4])
        ok = False
    except ValueError:
        ok = True
    check(ok, "control: a truncated retail file is refused")

    mf = MapFile.decode(data)
    mf.chunks.insert(0, mf.chunks.pop(5))         # move terrain to the front
    check(mf.encode() != data,
          "control: reordering a retail file's chunks changes its bytes")

    # The memcpy trap on ArenaNet's own bytes: drop one reference from a real
    # Dependencies chunk and require the emitted size field to shrink by 6.
    # Mutated IN PLACE -- see section 2 (e) for why a replacement is too weak.
    mf = MapFile.decode(data)
    idx = next(i for i, c in enumerate(mf.chunks)
               if c.chunk_id == SMALL_TERRAIN_DEP)
    chunk = mf.chunks[idx]
    was = len(chunk.payload())
    chunk.value.entries = chunk.value.entries[:-1]
    out = mf.encode()
    check(size_field_at(out, idx) == was - 6 and len(out) == len(data) - 6,
          "the size field is DERIVED on retail bytes too",
          f"chunk {was} -> {size_field_at(out, idx)} B, "
          f"file {len(data)} -> {len(out)} B")
    head_end = entry_offset(out, idx)              # start of the mutated entry
    check(head_end is not None and head_end > 0
          and out[:head_end] == data[:head_end],
          "and every byte before the mutated chunk's table entry is untouched",
          f"{head_end} bytes identical, then the size field moves")


def section7(cen_b, cen_s, n_maps):
    print("\n-- 7. what the round-trip is actually evidence about")
    both = add_census(dict(cen_b), cen_s)
    tot = both["total"]
    check(tot > 0 and both["reconstructed"] + both["carried"] + both["framing"]
          == tot,
          "the byte census accounts for every byte of every file swept",
          f"{tot} bytes over {n_maps} maps, both stages")
    for name, cen in (("Bloated", cen_b), ("Stripped", cen_s)):
        t = cen["total"] or 1
        print(f"    {name:<9} {cen['total']:>12} B   "
              f"reconstructed {100.0*cen['reconstructed']/t:5.2f}%   "
              f"carried {100.0*cen['carried']/t:5.2f}%   "
              f"framing {100.0*cen['framing']/t:5.2f}%")
        for key in ("terrain_reconstructed", "terrain_carried",
                    "dependencies", "opaque", "framing"):
            print(f"      {key:<24} {cen[key]:>12} B  "
                  f"{100.0*cen[key]/t:6.2f}%")
    # A claim about TODAY'S codec, not a law. If a later rung decodes Props or
    # Path and flips it, this check goes red on purpose: the number in
    # mapfile.py's docstring has to be re-measured in the same change.
    check(both["carried"] > both["reconstructed"],
          "MOST OF THE CORPUS BY WEIGHT IS CARRIED, and this says so",
          f"{100.0*both['carried']/tot:.2f}% carried against "
          f"{100.0*both['reconstructed']/tot:.2f}% reconstructed")
    check(cen_s["terrain_reconstructed"] == 0 and cen_s["terrain_carried"] == 0
          and cen_b["terrain_reconstructed"] > 0,
          "the Stripped stream reconstructs no terrain at all, and says so",
          f"Bloated {cen_b['terrain_reconstructed']} B through terrain.py, "
          f"Stripped 0 B")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=None)
    ap.add_argument("--sample", type=int, default=6,
                    help="how many maps to sweep by default")
    ap.add_argument("--all", action="store_true",
                    help="every map, both stages -- 698 files, ~13 minutes")
    args = ap.parse_args(argv)

    print(__doc__.strip().splitlines()[0])
    section1()
    section2()

    dat = args.dat
    if dat is None:
        root = vaultpath.vault_path("dat_study")
        dat = os.path.join(root, "Gw.dat")
    if not os.path.isfile(dat):
        LEDGER.skip("everything that needs the archive (sections 3-7)",
                    f"no Gw.dat at {dat}; vault resolved to "
                    f"{vaultpath.vault_root()} ({vaultpath.vault_why()}). "
                    f"Sections 1-2 measured the codec against files this test "
                    f"wrote and NOTHING about ArenaNet's format.")
        return LEDGER.verdict()

    with Archive(dat) as ar:
        mi = MapIndex(ar)
        pinned(ar, mi)
        if args.all:
            picks = list(mi.pairs)
        else:
            step = max(1, len(mi.pairs) // max(1, args.sample))
            picks = list(mi.pairs)[::step][:args.sample]
        cen_b, cen_s = section45(ar, mi, picks, args.all)
        section6(ar, mi)
        section7(cen_b, cen_s, len(picks))
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
