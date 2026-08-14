r"""The world-map ATLAS reader: which archive file holds each tile of a continent.

THE HEADLINE IS THE WEAK HALF AND THIS FILE SAYS SO IN THE CHECK LABELS. "492
tiles were found over three tiers" is close to true by construction: the module
reads a count out of a table, walks that many pointer slots and emits the
non-NULL ones, so the number it prints is the number the table declares. An
all-wrong reader that mis-parses every field still prints 492. So the count is
recorded and labelled WEAK, and the load-bearing checks are the ones that join
two artifacts which have no reason to agree unless the reading is right:

  count == CX x CY    `count` comes from the TILE TABLE (`0x00A37390`) and
                      `CX`/`CY` from `s_worldData` (`0x00A36210`) -- two tables
                      in two translation units, 4 KB apart, that this module
                      never makes equal. 21 of 21 grids agree over three tiers.
                      Asserted on `grids()`, which does NOT refuse a
                      disagreement, precisely so the agreement can go red.
                      The test recomputes `count == cx*cy` ITSELF and requires
                      the module's own `closes` to match, because a `closes`
                      that returns True is a one-character sabotage.

  the resolved rows   Every tile id resolved through the archive's own file-id
                      table must land on a row whose head decompresses to magic
                      `ATEX`. 484 of 484 do, on THREE archives with three
                      different row counts. The client image cannot force that
                      and neither can this reader.

  the exact 8         Eight tile ids resolve on no archive in the vault, and
                      they are the same eight on all three. The set is a
                      LITERAL in this file (`test_agentlife.py`'s lesson: a
                      symbol appearing in a test file is not a check), so the
                      count and the membership both have to hold.

  the dword-early     The control that makes all of the above mean something.
  control             Reading each pair record ONE DWORD EARLY, with a walker
                      written here out of `struct.unpack_from` that shares no
                      code with the module, must COLLAPSE: 0 of 492 resolve and
                      492 of 492 trailers go non-zero, against 484 and 0. A
                      check whose rival has never been run is not a check.

  consttable, not     Section 2 does NOT read `worldmap.WORLD_TABLE` and call it
  an address          proof. It plants a SECOND `s_worldData` in the fixture
                      under a different anchor, points `consttable`'s corpus row
                      at it, and requires the grids' CX/CY to CHANGE. A module
                      carrying a hardcoded base passes a constant-reading check
                      and fails this one. MEASURED: a `world_data()` rewritten
                      to read the table at the literal VA 0x00A36210 reddens 9,
                      two of them here.

  the planted         `SYNTH_TRAILER` plants ONE non-zero trailing u32, because
  counterexample      the client cannot supply one -- all 492 real records carry
                      zero, so "trailing u32 == 0 on 492 of 492" is satisfied by
                      a module that never reads the field. That is not
                      hypothetical: the sabotage was built and scored ALL CHECKS
                      PASSED before this fixture had a counterexample in it.

  the guard, on the   Section 6 reads the syntax tree of the MODULE UNDER TEST
  module under test   (`wm.__file__`), never `HERE/worldmap.py`: those differ
                      under `--module`, which is the mode every red count in the
                      floor comment is measured in, so the old spelling exempted
                      the whole section from the file's own evidence. It asks
                      three things a grep cannot -- that the guard runs before
                      the client is opened, that a NAME is bound to the guard's
                      own answer, and that every WRITE SITE writes that name.
                      The write here is `Path(x).write_text`, so an
                      `open(..., "w")`-only scan sees zero write sites and
                      passes vacuously.

SECTIONS 0-2 AND 6-7 BUILD A PE32 IMAGE BYTE BY BYTE and need no vault, no
archive and no client -- three synthetic getters, three tile tables, planted
slot arrays with planted NULLs, and a planted `s_worldData`. A walk defect is
not a property of any one binary. Sections 3-5 need the vaulted pristine client
and declare skips without it.

WHAT THE FIXTURE IS FOR, beyond a positive control: every refusal in section 1
is a way this module could return a plausible wrong answer instead of stopping
-- a getter whose bound check and index arithmetic read different fields, a
loop bound that is not a whole number of records, two getters claiming one
tier, a grid whose count is not its area, a slot pointing at bytes the file
does not have. Each is planted, each must refuse, and section 0 is the positive
control that a healthy image still resolves (a locator that refuses everything
protects nothing, because nobody runs it).
"""

import importlib.util
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(HERE, "..", "mapdata"))

import archive as archive_mod                                   # noqa: E402
import atex                                                     # noqa: E402
import checks                                                   # noqa: E402
import consttable                                               # noqa: E402
import gwdat                                                    # noqa: E402
import pinned                                                   # noqa: E402
import vaultpath                                                # noqa: E402
from gwpe import PE                                             # noqa: E402


def _load_module():
    """`--module PATH` swaps in a sabotaged copy. Everything else is unchanged.

    `test_msgmix.py`'s pattern, and the reason it is here rather than in a
    driver script: the floor comment below quotes MEASURED red counts, and a
    number nobody can re-derive is a number that rots. Each sabotage is one
    edit to a scratch copy of `worldmap.py`, run through this flag.
    """
    path = None
    if "--module" in sys.argv:
        path = sys.argv[sys.argv.index("--module") + 1]
    if not path:
        import worldmap
        return worldmap
    spec = importlib.util.spec_from_file_location("worldmap_sab", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["worldmap_sab"] = mod
    spec.loader.exec_module(mod)
    print(f"MODULE UNDER TEST OVERRIDDEN: {path}")
    return mod


wm = _load_module()

# THREE SCORES, each MEASURED from a real run and none of them subtracted from
# another -- this file needs TWO vault artifacts that fail independently, and
# test_glyphs.py / test_emblem.py both record a GUESSED floor going red on a
# healthy tree:
#
#   pinned client + Gw.dat (three in this vault) .............. 78   <- floor
#   the client, no archive ................................... 65
#   neither .................................................. 40
#
# So a vault-less run goes RED and names the sections that did not execute.
# That is deliberate: the synthetic half cannot refute anything about
# ArenaNet's own layout, and a green exit code that measured only the fixtures
# is the exact defect checks.py exists for.
#
# The archive section scores a FIXED count however many archives the vault
# holds -- five checks on the first, then ONE that requires every other to
# agree field for field. Scoring per archive made the floor a function of the
# machine, which is a guessed floor wearing a measurement's clothes.
#
# WHICH CHECKS ARE LOAD-BEARING WAS MEASURED, by building one-edit sabotages
# of worldmap.py as scratch copies and running this file against each through
# `--module`. Nineteen were built and run in the 2026-08-14 audit, and all nineteen redden; these are
# the counts the runs printed, not estimates:
#
#   the world table read at a HARDCODED VA, not via consttable . 9 red (+4 lost)
#   record stride 12 -> 24  `TILE_RECORD_SIZE = 24` ............ 8 red (+57 lost)
#   resolve() joins `ar.entries[row]`, not `ar.row(row)` ....... 5 red
#   resolve_out returns immediately (every refusal dead) ....... 4 red
#   `atex_head` reads w/h at +10 instead of +8 ................. 3 red
#   NULL check removed      `if slot == 0` -> `if False` ....... 3 red (+29 lost)
#   slot walk off by one    `ao + i*4` -> `ao + (i+1)*4` ....... 3 red (+3 lost)
#   main() never calls resolve_out; writes straight to a.out ... 3 red
#   x/y swapped             `i % cx, i // cx` -> swapped ....... 2 red
#   `closes` replayed True  `count == cx*cy` -> `True` ......... 2 red
#   grids() replays cx*cy instead of the table's own `count` ... 2 red
#   the repo-checkout refusal dropped from resolve_out ......... 2 red
#   CX disagreement muted   `if cx_off != imul_cx` -> `if False`  1 red
#   world-bound-vs-s_worldData disagreement muted .............. 1 red
#   the tier-assert requirement muted ......................... 1 red
#   the dat_study refusal dropped ............................. 1 red
#   `_off()` answers 0 instead of None for an unmapped VA ...... 1 red
#   the trailing u32 never read (`trailer = 0`) ................ 1 red
#   the --out write uses `a.out` instead of the guarded path ... 1 red
#
# Several take out whole sections, and `guarded()` is why those are red checks
# with a named exception rather than a traceback and no verdict.
#
# THREE of those rows are the 2026-08-14 audit's findings, and each scored ZERO
# red before the check beside it was added -- with the run printing ALL CHECKS
# PASSED and exit 0:
#
#   * `main()` NEVER CALLING `resolve_out`, writing straight to `a.out`. The
#     section-6 syntax-tree check read `HERE/worldmap.py` instead of the module
#     under test, so it was structurally exempt from `--module` -- the very
#     mode this whole table is measured in. It now reads `wm.__file__`, and a
#     second check requires every WRITE SITE in the module to write the name
#     bound to `resolve_out`'s own answer, because the write here is
#     `Path(x).write_text` and an `open(..., "w")`-only scan finds zero write
#     sites and passes vacuously. `test_atex.py` section 3, one level up.
#   * the TRAILING u32 never read. Every record on build 38797 carries zero
#     there, so `trailer = 0` agrees with the independent walker on all 492 and
#     with the client census. Only `SYNTH_TRAILER`'s planted counterexample can
#     tell a reader from an assumer.
#   * the emitted build stamped from `pinned.BUILD` rather than measured from
#     the image (see section 7's control).
#
# THE ROW THAT EARNS ITS PLACE among the rest is still the one that reddens
# exactly ONE check with nothing else moving. Muting the bound-check-versus-
# index-arithmetic disagreement is invisible everywhere else, because on the
# real image the two reads agree -- only the planted getter in section 1 can
# see it. Without that check the module would accept a build whose two reads of
# the tier's CX field disagree and index with whichever one it happened to
# parse, and every coordinate downstream would be sourced, plausible and wrong.
#
# And note what `x/y swapped` shows about the SYNTHETIC half alone: the fixture
# catches it because parchment's grid is 1x2, not square. A fixture built only
# out of square grids would have scored that sabotage 1 red, on the client
# check alone -- which is why SYNTH_DIMS is deliberately ragged.
LEDGER = checks.Ledger("worldmap", floor=78)

# ---- literals, written HERE and not computed from the module -------------
EXPECT_TIERS = ("chunk", "parchment", "satellite")
EXPECT_TABLE_VA = {"chunk": 0x00A37390, "parchment": 0x00A373E8,
                   "satellite": 0x00A37440}
EXPECT_CX_OFF = {"chunk": 0x04, "parchment": 0x0C, "satellite": 0x18}
EXPECT_TIER_ASSERT_LINE = {"chunk": 1316, "parchment": 1338, "satellite": 1360}
EXPECT_COUNT_ASSERT_LINE = {"chunk": 1325, "parchment": 1347, "satellite": 1369}
EXPECT_TILES = {"chunk": 409, "parchment": 58, "satellite": 25}
EXPECT_TOTAL_TILES = 492
EXPECT_GRIDS = 21
EXPECT_SILENT_WORLDS = [7, 8, 9]
EXPECT_WORLDS = 10
# PLAN.md rung S3's prediction, stated before this module existed.
EXPECT_UNRESOLVED = {387674, 387678, 387680, 387682, 387684,
                     388093, 388095, 388097}
EXPECT_RESOLVED = 484
# The tiles that are NOT 512x512, which FINDINGS section 3.1 records as
# "512x512" off a sample of 4. Named by file id, since a row index is a fact
# about the archive copy and these hold on all three.
EXPECT_256_CHUNK = {338409, 338411, 338413, 338415}
EXPECT_256_TOTAL = 15
# The encoding formula, written out rather than imported: `mapchunks` owns it
# and has its own test, and the point here is that the WALK lands on the right
# eight bytes.
DEP_BIAS, DEP_RADIX = 0xFF00FF, 0xFF00

IMAGE_BASE = 0x00400000
TEXT_RVA, TEXT_OFF, TEXT_SIZE = 0x1000, 0x400, 0x1000
RDATA_RVA, RDATA_OFF, RDATA_SIZE = 0x4000, 0x1400, 0x2000
GETTER_PITCH = 0x100          # > worldmap.GETTER_WINDOW, so windows are disjoint

_TMP = []


# --------------------------------------------------------------------------
# the fixture
# --------------------------------------------------------------------------

def build_image(rdata: bytes, text: bytes) -> str:
    """A minimal PE32 with a .text and a .rdata, written to a temp file.

    `gwpe.PE` reads a real header, so the fixture has to be a real image --
    otherwise the test exercises a different code path from the one that runs
    against the client. Copied in shape from `test_consttable.py`.
    """
    e = 0x80
    hdr = bytearray(b"\x00" * TEXT_OFF)
    hdr[0:2] = b"MZ"
    struct.pack_into("<I", hdr, 0x3C, e)
    hdr[e:e + 4] = b"PE\x00\x00"
    struct.pack_into("<H", hdr, e + 4, 0x014C)       # machine: x86
    struct.pack_into("<H", hdr, e + 6, 2)            # sections
    struct.pack_into("<H", hdr, e + 20, 0xE0)        # optional header size
    struct.pack_into("<H", hdr, e + 24, 0x010B)      # PE32
    struct.pack_into("<I", hdr, e + 52, IMAGE_BASE)
    sec = e + 24 + 0xE0
    for i, (name, vaddr, rawsize, rawptr) in enumerate((
            (b".text", TEXT_RVA, TEXT_SIZE, TEXT_OFF),
            (b".rdata", RDATA_RVA, RDATA_SIZE, RDATA_OFF))):
        o = sec + i * 40
        hdr[o:o + len(name)] = name
        struct.pack_into("<I", hdr, o + 8, rawsize)
        struct.pack_into("<I", hdr, o + 12, vaddr)
        struct.pack_into("<I", hdr, o + 16, rawsize)
        struct.pack_into("<I", hdr, o + 20, rawptr)
    body = bytearray(hdr)
    body += b"\xCC" * TEXT_SIZE
    body[TEXT_OFF:TEXT_OFF + len(text)] = text
    body += b"\x00" * RDATA_SIZE
    body[RDATA_OFF:RDATA_OFF + len(rdata)] = rdata
    fd, path = tempfile.mkstemp(suffix=".exe", prefix="worldmap_")
    os.write(fd, bytes(body))
    os.close(fd)
    _TMP.append(path)
    return path


def rva(off_in_rdata):
    return IMAGE_BASE + RDATA_RVA + off_in_rdata


class Blob:
    """An .rdata under construction: append bytes, get VAs back."""

    def __init__(self):
        self.buf = bytearray()

    def add(self, data, align=4):
        while len(self.buf) % align:
            self.buf.append(0)
        at = len(self.buf)
        self.buf += data
        return rva(at)

    def string(self, text):
        return self.add(text.encode("ascii") + b"\x00", align=1)


def getter_bytes(table_va, records, cx_off, cy_off, imul_cx,
                 file_va, expr_cx_va, expr_count_va, worlds=10,
                 tier_line=1316, count_line=1325, bound=None):
    """One synthetic `ConstWorldMapGet<Tier>File`, byte for byte.

    Deliberately assembled by hand rather than copied out of the client: a
    fixture cut from ArenaNet's bytes would be ArenaNet's bytes in the repo,
    and it would also make the shape unfalsifiable -- the module would be
    matching the very bytes it was written against.
    """
    bound = records * 12 if bound is None else bound
    b = bytearray()
    b += b"\x83\xff" + bytes([worlds]) + b"\x7c\x14"              # cmp edi,W; jl
    b += (b"\x68" + struct.pack("<H", tier_line) + b"\x00\x00"    # push line
          + b"\xba" + struct.pack("<I", file_va)                  # mov edx,FILE
          + b"\xb9" + struct.pack("<I", expr_cx_va))              # mov ecx,EXPR
    b += b"\x8b\x0b\x3b\x4a" + bytes([cx_off]) + b"\x72\x17"      # cmp x,[edx+CX]
    b += b"\x8b\x43\x04\x3b\x42" + bytes([cy_off]) + b"\x72\x17"  # cmp y,[edx+CY]
    b += b"\xbe" + struct.pack("<I", table_va)                    # mov esi,TABLE
    b += b"\x33\xc0\x39\x7e\x08\x74\x12\x83\xc0\x0c\x83\xc6\x0c"
    b += b"\x83\xf8" + bytes([bound]) + b"\x72\xf0"               # cmp eax,bound
    b += b"\x5f\x5e\x33\xc0\x5b\x5d\xc3"
    b += b"\x8b\x7b\x04\x0f\xaf\x7a" + bytes([imul_cx]) + b"\x03\x3b\x3b\x3e"
    b += b"\x72\x14"
    b += (b"\x68" + struct.pack("<H", count_line) + b"\x00\x00"
          + b"\xba" + struct.pack("<I", file_va)
          + b"\xb9" + struct.pack("<I", expr_count_va))
    return bytes(b)


# The planted world: three tiers, seven worlds each, small grids, planted NULLs.
SYNTH_DIMS = {"chunk": (2, 2), "parchment": (1, 2), "satellite": (1, 1)}
SYNTH_NULLS = {("chunk", 0): {0}, ("chunk", 3): {1, 2},
               ("parchment", 5): {1}, ("satellite", 2): {0}}
# ONE planted NON-ZERO trailer, and it is here because the real image cannot
# supply one. "trailing u32 == 0 on 492 of 492" is PLAN rung S3's prediction
# and FINDINGS section 3.1 records it as OBSERVED -- but every record on build
# 38797 really does carry zero there, so a module that never reads the field
# and assigns `trailer = 0` agrees with an independent walker on all 492 and
# passes the whole file. MEASURED: that sabotage scored ALL CHECKS PASSED (76
# checks), exit 0, with the client, the archive and the dword-early control all
# green. Only a fixture that plants a counterexample can tell the two apart.
SYNTH_TRAILER = {("chunk", 1, 0): 0xDEADBEEF}


def synth(tiers=EXPECT_TIERS, cx_offs=None, imul_offs=None, worlds=10,
          bad_grid=None, unmapped_slot=False, drop_tier_assert=None,
          bad_bound=None, duplicate_tier=False, alt_world_table=False):
    """Build the fixture. Returns (path, expected) where `expected` is the map.

    `expected` is `{(tier, world, x, y): file_id}` built here from the planted
    pairs with the encoding written out as a literal -- so the check is on the
    WALK (which slot is which cell, and which eight bytes it points at) and not
    on a formula `mapchunks` already owns a test for.
    """
    cx_offs = dict(cx_offs or EXPECT_CX_OFF)
    imul_offs = dict(imul_offs or cx_offs)
    r = Blob()
    file_va = r.string(r"P:\Code\Gw\Const\ConstWorldMap.cpp")
    expr_count = r.string("offset < files.count")
    expr_cx = {t: r.string(f"chunk.x < worldData.{t}CX") for t in tiers}

    expected, pair_va = {}, {}
    fid = 1000
    for t in tiers:
        for w in range(7):
            cx, cy = SYNTH_DIMS[t]
            for i in range(cx * cy):
                if i in SYNTH_NULLS.get((t, w), ()):
                    continue
                fid += 7
                id1, id0 = divmod(fid + DEP_BIAS, DEP_RADIX)
                trail = SYNTH_TRAILER.get((t, w, i), 0)
                pair_va[(t, w, i)] = r.add(struct.pack("<HHI", id0, id1, trail))
                expected[(t, w, i % cx, i // cx)] = (id0 - DEP_BIAS) + id1 * DEP_RADIX

    array_va = {}
    for t in tiers:
        for w in range(7):
            cx, cy = SYNTH_DIMS[t]
            slots = bytearray()
            for i in range(cx * cy):
                va = pair_va.get((t, w, i), 0)
                if unmapped_slot and (t, w, i) == (tiers[0], 0, 1):
                    va = IMAGE_BASE + 0x900000       # mapped nowhere
                slots += struct.pack("<I", va)
            array_va[(t, w)] = r.add(bytes(slots))

    table_va = {}
    for t in tiers:
        recs = bytearray()
        for w in range(7):
            cx, cy = SYNTH_DIMS[t]
            count = cx * cy
            if bad_grid == (t, w):
                count += 1                            # count != cx * cy
            recs += struct.pack("<3I", count, array_va[(t, w)], w)
        table_va[t] = r.add(bytes(recs))

    def world_table(scale):
        """10 x 48, with each tier's CX/CY at its own offset."""
        out = bytearray()
        for w in range(10):
            rec = bytearray(48)
            for t in tiers:
                cx, cy = SYNTH_DIMS[t]
                struct.pack_into("<2I", rec, cx_offs[t], cx * scale, cy * scale)
            struct.pack_into("<I", rec, 0x14, 512)
            out += rec
        return bytes(out)

    r.add(b"PREVSTRING\x00", align=1)
    r.add(b"\x00" * 4, align=4)                       # the corpus row's pad=4
    wd_base = r.add(world_table(1), align=1)
    r.add(b"P:\\Code\\Gw\\Const\\ConstWorld.cpp\x00", align=1)

    alt_base = None
    if alt_world_table:
        # A SECOND s_worldData under a different anchor, with every dimension
        # doubled. Section 2 points consttable's corpus row at this one and
        # requires the answer to move.
        r.add(b"PREVSTRING2\x00", align=1)
        r.add(b"\x00" * 4, align=4)
        alt_base = r.add(world_table(2), align=1)
        r.add(b"P:\\Code\\Gw\\Const\\ConstWorldAlt.cpp\x00", align=1)

    text = bytearray()
    order = list(tiers) + ([tiers[0]] if duplicate_tier else [])
    for n, t in enumerate(order):
        g = getter_bytes(
            table_va[t], 7, cx_offs[t], cx_offs[t] + 4,
            imul_offs[t], file_va, expr_cx[t], expr_count, worlds=worlds,
            tier_line=EXPECT_TIER_ASSERT_LINE.get(t, 1316),
            count_line=EXPECT_COUNT_ASSERT_LINE.get(t, 1325),
            bound=bad_bound if (bad_bound and n == 0) else None)
        if drop_tier_assert == t:
            g = g.replace(struct.pack("<I", expr_cx[t]),
                          struct.pack("<I", expr_count))
        text += g.ljust(GETTER_PITCH, b"\xCC")
    # The accessor's absolute load, which consttable requires as a witness.
    text += struct.pack("<I", wd_base)
    if alt_base is not None:
        text += struct.pack("<I", alt_base)
    return build_image(bytes(r.buf), bytes(text)), expected


def refuses(fn, kind, needle=""):
    try:
        fn()
    except kind as exc:
        return needle in str(exc)
    except Exception:
        return False
    return False


def guarded(fn, *args):
    """Run a section; turn a crash into a NAMED failing check, never a traceback.

    Measured need, not tidiness: several of the sabotages below make `tiles()`
    raise on the FIRST section, and without this the run dies at check 10 with
    no banner, no ledger and no floor shortfall -- which reads as a broken test
    rather than a caught defect, and makes the declared floor unreachable as a
    guard. `test_marks.py` records the same lesson over 109 sabotages, twelve
    of which died with a traceback.
    """
    try:
        return fn(*args)
    except BaseException as exc:                # SystemExit included, on purpose
        LEDGER.ok(False, f"{fn.__name__} ran to completion",
                  f"{type(exc).__name__}: {str(exc)[:180]}")
        return None


# --------------------------------------------------------------------------

def section_synthetic():
    print("\n0. the positive control: a planted atlas resolves, cell for cell")
    path, expected = synth()
    pe = PE(path)
    gets = wm.getters(pe)

    LEDGER.ok([g.tier for g in gets] == list(EXPECT_TIERS),
              "three getters, named by ArenaNet's own assert expression",
              str([g.tier for g in gets]))
    LEDGER.ok(all(g.table_va and g.records == 7 for g in gets),
              "each carries its tile table's address and a 7-record bound",
              str([(hex(g.table_va), g.records) for g in gets]))
    LEDGER.ok([g.cx_off for g in gets] == [EXPECT_CX_OFF[t] for t in EXPECT_TIERS],
              "and the s_worldData field each tier indexes with",
              str([hex(g.cx_off) for g in gets]))
    LEDGER.ok(all(g.cy_off == g.cx_off + 4 for g in gets),
              "CY is the dword after CX on every tier")
    LEDGER.ok(all(g.worlds == EXPECT_WORLDS for g in gets),
              f"the world bound is {EXPECT_WORLDS} on every tier")

    grids = wm.grids(pe)
    LEDGER.ok(len(grids) == EXPECT_GRIDS,
              f"{EXPECT_GRIDS} grids (3 tiers x 7 worlds)", str(len(grids)))
    # Recomputed HERE, not read off `closes` -- `closes` is one character from
    # `return True` and section 1 is what catches that.
    mine = [g.count == g.cx * g.cy for g in grids]
    LEDGER.ok(all(mine), "every planted grid's count is its area (recomputed here)")
    LEDGER.ok([g.closes for g in grids] == mine,
              "and the module's own `closes` agrees with that recomputation")
    LEDGER.ok(all((g.cx, g.cy) == SYNTH_DIMS[g.tier] for g in grids),
              "each grid's CX/CY are the planted ones for its tier",
              str(sorted({(g.tier, g.cx, g.cy) for g in grids})))

    tiles = wm.tiles(pe)
    got = {t.key(): t.file_id for t in tiles}
    LEDGER.ok(got == expected,
              "EVERY tile lands on its planted cell with its planted file id",
              f"{len(got)} tiles, {len(expected)} planted")
    # The planted counterexample. Not `all(t.trailer == 0)`: on the client that
    # is true of every record, so it is satisfied by a reader that assigns the
    # constant instead of reading the field.
    want_trail = {}
    for (t, w, i), v in SYNTH_TRAILER.items():
        cx, _cy = SYNTH_DIMS[t]
        want_trail[(t, w, i % cx, i // cx)] = v
    got_trail = {k: v for k, v in ((x.key(), x.trailer) for x in tiles) if v}
    LEDGER.ok(got_trail == want_trail,
              "the pair record's trailing u32 is READ, not assumed -- one "
              "planted non-zero comes back and the rest are zero",
              f"{got_trail} vs planted {want_trail}")
    planted_nulls = sum(len(v) for v in SYNTH_NULLS.values())
    slots = sum(g.count for g in grids)
    LEDGER.ok(len(tiles) == slots - planted_nulls,
              "NULL slots are skipped, not emitted",
              f"{len(tiles)} tiles of {slots} slots, {planted_nulls} planted NULL")
    LEDGER.ok(len({t.file_id for t in tiles}) == len(tiles),
              "no file id is emitted twice")


def section_refusals():
    print("\n1. every way this could answer plausibly and wrongly")

    # The check with teeth: two instructions read the tier's CX field for two
    # different purposes, and a mis-parse of either moves one and not the other.
    bad = dict(EXPECT_CX_OFF)
    bad["parchment"] = 0x10
    p, _ = synth(imul_offs=bad)
    LEDGER.ok(refuses(lambda: wm.getters(PE(p)), wm.GetterIncoherent, "disagree"),
              "a getter whose bound check and index arithmetic read different "
              "fields is REFUSED")

    p, _ = synth(drop_tier_assert="parchment")
    LEDGER.ok(refuses(lambda: wm.getters(PE(p)), wm.GetterIncoherent, "TIER NAME"),
              "a getter with no `chunk.x < worldData.<tier>CX` assert is REFUSED "
              "-- the tier name is ArenaNet's word, not ours")

    p, _ = synth(bad_bound=0x50)
    LEDGER.ok(refuses(lambda: wm.getters(PE(p)), wm.GetterIncoherent, "records"),
              "a loop bound that is not a whole number of 12-byte records is "
              "REFUSED")

    p, _ = synth(duplicate_tier=True)
    LEDGER.ok(refuses(lambda: wm.getters(PE(p)), wm.GetterIncoherent, "same tier"),
              "two getters claiming one tier are REFUSED")

    p, _ = synth(worlds=9)
    LEDGER.ok(refuses(lambda: wm.grids(PE(p)), wm.GetterIncoherent, "disagree"),
              "a getter whose world bound disagrees with s_worldData's own "
              "record count is REFUSED")

    # The two-sided design: grids() reports, tiles() refuses.
    p, _ = synth(bad_grid=("chunk", 4))
    pe = PE(p)
    bad_rows = [g for g in wm.grids(pe) if not g.closes]
    LEDGER.ok(len(bad_rows) == 1 and bad_rows[0].world == 4,
              "grids() REPORTS a grid whose count is not its area rather than "
              "refusing -- which is what makes 21 of 21 a measurement",
              str(bad_rows))
    LEDGER.ok(refuses(lambda: wm.tiles(pe), wm.GridDisagrees, "invention"),
              "...and tiles() REFUSES it, because (x, y) = (i % cx, i // cx) is "
              "meaningless once the grid is in doubt")

    p, _ = synth(unmapped_slot=True)
    LEDGER.ok(refuses(lambda: wm.tiles(PE(p)), wm.SlotUnmapped, "file bytes"),
              "a non-NULL slot pointing at bytes the file does not hold is "
              "REFUSED, not read as zeros")

    p, _ = synth()
    pe = PE(p)
    LEDGER.ok(refuses(lambda: wm.tiles(pe, only_tier="nonsense"),
                      wm.TiersNotFound, "no tier named"),
              "--tier naming a tier this build does not have is REFUSED, not "
              "answered with a confident 0 tiles")
    LEDGER.ok(len(wm.tiles(pe, only_tier=EXPECT_TIERS[1])) > 0,
              "...while a real tier still filters (the refusal is not "
              "'refuse everything')",
              str(len(wm.tiles(pe, only_tier=EXPECT_TIERS[1]))))

    empty = build_image(b"\x00" * 64, b"\xCC" * 64)
    LEDGER.ok(refuses(lambda: wm.getters(PE(empty)), wm.TiersNotFound,
                      "does not occur"),
              "an image with no getter shape is REFUSED -- there is no address "
              "here to fall back on")


def section_through_consttable():
    print("\n2. the table is found THROUGH consttable, asserted behaviourally")
    path, _ = synth(alt_world_table=True)
    pe = PE(path)
    before = {(g.tier, g.world): (g.cx, g.cy) for g in wm.grids(pe)}
    LEDGER.ok(all(v == SYNTH_DIMS[k[0]] for k, v in before.items()),
              "baseline: the grids read the planted s_worldData")

    row = consttable.BY_SYMBOL["s_worldData"]
    keep = row["anchor"]
    try:
        # Point consttable at a DIFFERENT s_worldData whose dimensions are all
        # doubled. A module that carried a hardcoded base would not notice.
        row["anchor"] = b"P:\\Code\\Gw\\Const\\ConstWorldAlt.cpp\x00"
        after = {(g.tier, g.world): (g.cx, g.cy) for g in wm.grids(pe)}
    finally:
        row["anchor"] = keep

    LEDGER.ok(after != before,
              "moving consttable's s_worldData row MOVES this module's answer",
              f"{list(before.items())[0]} -> {list(after.items())[0]}")
    LEDGER.ok(all(after[k] == (v[0] * 2, v[1] * 2) for k, v in before.items()),
              "and it moves to exactly the alternate table's dimensions")
    restored = {(g.tier, g.world): (g.cx, g.cy) for g in wm.grids(pe)}
    LEDGER.ok(restored == before,
              "restoring the corpus row restores the answer (the patch is the "
              "only variable)")
    LEDGER.ok(wm.WORLD_TABLE == "s_worldData"
              and wm.WORLD_TABLE in consttable.BY_SYMBOL,
              "the symbol this module asks for is a real consttable corpus row")


def section_client(pe):
    print("\n3. the pinned client: the tables, and what agrees with what")
    gets = wm.getters(pe)
    LEDGER.ok([g.tier for g in gets] == list(EXPECT_TIERS),
              "three tiers, named by the client's own assert expressions",
              str([g.tier for g in gets]))
    LEDGER.ok({g.tier: g.table_va for g in gets} == EXPECT_TABLE_VA,
              "each tile table is at the address this file names as a literal",
              str({g.tier: hex(g.table_va) for g in gets}))
    LEDGER.ok({g.tier: g.cx_off for g in gets} == EXPECT_CX_OFF,
              "and indexes with the s_worldData field this file names -- "
              "satelliteCX at +0x18 was UNVERIFIED in FINDINGS section 3.1",
              str({g.tier: hex(g.cx_off) for g in gets}))
    LEDGER.ok({g.tier: g.tier_assert_line for g in gets}
              == EXPECT_TIER_ASSERT_LINE
              and {g.tier: g.assert_line for g in gets}
              == EXPECT_COUNT_ASSERT_LINE,
              "the two asserts bounding each getter are at the expected lines "
              "of ConstWorldMap.cpp",
              str({g.tier: (g.tier_assert_line, g.assert_line) for g in gets}))
    LEDGER.ok(all(g.assert_file.endswith("ConstWorldMap.cpp") for g in gets),
              "and all three are in one translation unit",
              gets[0].assert_file)

    wd = wm.world_data(pe)
    LEDGER.ok(wd.count == EXPECT_WORLDS and wd.stride == 48,
              f"s_worldData is {EXPECT_WORLDS} x 48 via consttable",
              f"{wd.count} x {wd.stride} at file 0x{wd.base:06X}")
    LEDGER.ok(all(g.worlds == wd.count for g in gets),
              "and the three getters' own `cmp edi, WORLDS` agrees with it -- "
              "ArenaNet's number stated in four functions")

    grids = wm.grids(pe, gets, wd)
    mine = [g.count == g.cx * g.cy for g in grids]
    LEDGER.ok(len(grids) == EXPECT_GRIDS,
              f"{EXPECT_GRIDS} grids", str(len(grids)))
    # THE LOAD-BEARING CHECK. `count` is the tile table's; cx/cy are
    # s_worldData's. Nothing in this module makes them equal.
    LEDGER.ok(all(mine),
              "LOAD-BEARING: count == CX x CY on every grid, from two tables "
              "in two translation units",
              f"{sum(mine)} of {len(mine)}")
    LEDGER.ok([g.closes for g in grids] == mine,
              "and the module's own `closes` agrees with the recomputation here")
    silent = sorted(set(range(wd.count)) - {g.world for g in grids})
    LEDGER.ok(silent == EXPECT_SILENT_WORLDS,
              f"worlds {EXPECT_SILENT_WORLDS} carry no tile record in any tier",
              str(silent))

    tiles = wm.tiles(pe, gets, wd)
    per = {t: sum(1 for x in tiles if x.tier == t) for t in EXPECT_TIERS}
    # WEAK: the module walks `count` slots and emits the non-NULL ones, so this
    # number is close to what the table declares. Recorded, not leaned on.
    LEDGER.ok(per == EXPECT_TILES and len(tiles) == EXPECT_TOTAL_TILES,
              "WEAK HALF: the tile census matches PLAN rung S3's prediction",
              str(per))
    LEDGER.ok(all(t.trailer == 0 for t in tiles),
              f"trailing u32 == 0 on {len(tiles)} of {len(tiles)} pair records")
    LEDGER.ok(len({t.file_id for t in tiles}) == len(tiles),
              "no file id appears in two cells",
              f"{len({t.file_id for t in tiles})} distinct")
    LEDGER.ok(all(0 <= t.x < g.cx and 0 <= t.y < g.cy
                  for g in grids for t in tiles
                  if (t.tier, t.world) == (g.tier, g.world)),
              "every tile's (x, y) is inside its own grid")
    return gets, wd, grids, tiles


def _join(path, tiles):
    """(resolved-fingerprint, mft rows). The facts an archive can refute.

    `one_based` used to be `all(ar.row(r.row).index == r.row ...)`, which is a
    check that CANNOT FAIL: `archive.row()` asserts exactly that internally
    (`archive.py:367`) and would have raised before returning. It counted
    toward the floor and measured nothing. What replaces it is refutable from
    two directions -- the row's MFT size read POSITIONALLY here has to equal
    the `stored` the module reported (an `entries[row]` join reads the next
    row's size, which is iconset.py's scar), and the off-by-one row has to name
    a DIFFERENT file, which is what made that scar invisible in the first place
    and is a fact about this archive rather than about our decoder.
    """
    ar = wm.open_archive(path)
    try:
        got, missing = wm.resolve(ar, tiles)
        table = archive_mod.file_id_table(ar)
        by_row = {row: fid for fid, row in table.items()}
        return {
            "resolved": len(got),
            "unresolved": frozenset(t.file_id for t in missing),
            "all_atex": all(r.is_atex for r in got),
            "dims": frozenset((r.tile.file_id, r.width, r.height) for r in got),
            "sizes": all(ar.entries[r.row - 1].size == r.stored for r in got),
            "scar": sum(1 for r in got
                        if by_row.get(r.row + 1) == r.tile.file_id),
        }, len(ar.entries)
    finally:
        ar.close()


def section_archive(tiles, dats):
    print("\n4. the archive join")
    # A FIXED number of checks whichever archives a vault holds. Scoring
    # per-archive made the floor a function of the machine, which is the same
    # mistake as a guessed floor: it goes red for a reason that is not a defect.
    label, path = dats[0]
    fp, rows = _join(path, tiles)
    LEDGER.ok(fp["resolved"] == EXPECT_RESOLVED
              and fp["unresolved"] == EXPECT_UNRESOLVED,
              f"{label}: {EXPECT_RESOLVED} tiles resolve and the unresolved set "
              f"is EXACTLY the eight this file names as a literal",
              f"{fp['resolved']} resolved, {len(fp['unresolved'])} missing, "
              f"{rows:,} MFT rows")
    LEDGER.ok(fp["all_atex"],
              f"{label}: LOAD-BEARING -- every resolved row's head decompresses "
              f"to magic ATEX, which neither the image nor this reader can force",
              f"{fp['resolved']} of {fp['resolved']}")
    odd = {f for f, w, h in fp["dims"] if (w, h) != (512, 512)}
    LEDGER.ok(len(odd) == EXPECT_256_TOTAL
              and all(w == h and w in (256, 512) for _f, w, h in fp["dims"]),
              f"{label}: {EXPECT_256_TOTAL} tiles are 256x256 and the rest "
              f"512x512 -- FINDINGS section 3.1 says 512x512 off a sample of 4",
              f"{len(odd)} not 512")
    chunk_ids = {t.file_id for t in tiles if t.tier == "chunk"}
    LEDGER.ok(odd & chunk_ids == EXPECT_256_CHUNK,
              f"{label}: and the four CHUNK-tier ones are the file ids named "
              f"here, which a crop renderer (rung S5) must not assume away",
              str(sorted(odd & chunk_ids)))
    LEDGER.ok(fp["sizes"],
              f"{label}: every row's MFT size read POSITIONALLY here equals the "
              f"`stored` the module reported -- an entries[row] join reads the "
              f"NEXT row's, which is iconset.py's scar")
    LEDGER.ok(fp["scar"] == 0,
              f"{label}: and the off-by-one row names a DIFFERENT file on every "
              f"one of them, which is why that scar was invisible without a "
              f"check like this",
              f"{fp['scar']} row(s) would have collided")

    others = dats[1:]
    if others:
        agree, seen = [], []
        for lbl, p in others:
            other_fp, other_rows = _join(p, tiles)
            agree.append(other_fp == fp)
            seen.append(f"{lbl} ({other_rows:,} rows)")
        LEDGER.ok(all(agree) and len(agree) == len(others),
                  f"{len(others)} further archive(s) agree field for field -- "
                  f"same 484, same eight missing, same per-tile dimensions, at "
                  f"different row counts",
                  "; ".join(seen))
    else:
        LEDGER.skip("the second-archive agreement",
                    "only one Gw.dat in the vault; a file id is archive STATE, "
                    "so one copy cannot show the split is a property of the "
                    "atlas rather than of that copy")

    # The cheap 16-byte header reader, pinned against the real parser.
    ar = wm.open_archive(path)
    try:
        table = archive_mod.file_id_table(ar)
        sample = next(t for t in tiles if t.file_id in table)
        entry = ar.row(table[sample.file_id])
        whole = ar.read(entry)
        parsed = atex.parse(whole)
        cheap = wm.atex_head(whole[:wm.ATEX_HEAD])
    finally:
        ar.close()
    LEDGER.ok(cheap == (parsed.magic, parsed.width, parsed.height),
              "atex_head's 16-byte read agrees with atex.parse on a whole tile "
              "-- two readings of one header is what drifts",
              f"{cheap} vs {(parsed.magic, parsed.width, parsed.height)}")
    LEDGER.ok(parsed.width == 512 and len(parsed.levels) > 1,
              "and that tile really is a multi-level 512 ATEX",
              f"{parsed.width}x{parsed.height}, {len(parsed.levels)} levels")


def section_dword_early(pe, tiles, dat):
    print("\n5. the control: the same walk, one dword early, must COLLAPSE")
    ar = wm.open_archive(dat)
    try:
        table = archive_mod.file_id_table(ar)
    finally:
        ar.close()

    def score(shift):
        """A walker written HERE, out of struct. Shares no code with the module."""
        ok = trailers = 0
        for t in tiles:
            o = pe.rva_to_off(t.record_va - pe.image_base) + shift
            id0, id1, trail = struct.unpack_from("<HHI", pe.data, o)
            if trail:
                trailers += 1
            if (id0 - DEP_BIAS) + id1 * DEP_RADIX in table:
                ok += 1
        return ok, trailers

    # The module's OWN three fields against the walker's, value for value.
    # Without this, "trailing u32 == 0 on 492 of 492" is satisfied by a reader
    # that never reads the field: MEASURED -- a worldmap.py unpacking `<HH` and
    # assigning `trailer = 0` scored ALL CHECKS PASSED (69 checks), exit 0,
    # including that very check in two sections. PLAN rung S3 predicted the
    # trailing zero and FINDINGS section 3.1 records it as OBSERVED, so a
    # replayed constant there is a fabricated measurement, not a cosmetic gap.
    mismatched = []
    for t in tiles:
        o = pe.rva_to_off(t.record_va - pe.image_base)
        id0, id1, trail = struct.unpack_from("<HHI", pe.data, o)
        if (t.id0, t.id1, t.trailer) != (id0, id1, trail):
            mismatched.append(t.key())
    LEDGER.ok(not mismatched,
              "the module's own id0/id1/TRAILER are the bytes at the record, "
              "not values it assigned -- a reader that never reads the trailer "
              "passes every other check in this file",
              f"{len(mismatched)} disagree of {len(tiles)}")

    base = score(0)
    early = score(-4)
    late = score(+4)
    LEDGER.ok(base == (EXPECT_RESOLVED, 0),
              "the independent walker reproduces the module's own answer",
              f"{base[0]} resolve, {base[1]} non-zero trailers")
    LEDGER.ok(early[0] == 0 and early[1] == len(tiles),
              "read one dword EARLY it collapses to 0 resolved and every "
              "trailer goes non-zero",
              f"{early[0]} resolve, {early[1]} of {len(tiles)} trailers")
    LEDGER.ok(late[0] == 0 and late[1] == len(tiles),
              "and one dword LATE likewise -- the record boundary is pinned "
              "from both sides",
              f"{late[0]} resolve, {late[1]} of {len(tiles)} trailers")


def section_guards():
    print("\n6. the write guard: four refusals, each with a positive control")
    LEDGER.ok(refuses(lambda: wm.resolve_out(r"C:\gw\atlas.json"),
                      wm.Refused, "owner's own install"),
              "the owner's install at C:\\gw is REFUSED")
    LEDGER.ok(refuses(lambda: wm.resolve_out(
                  vaultpath.vault_path("dat_study", "x.json")),
                  wm.Refused, "SOURCE snapshot"),
              "vault/dat_study is REFUSED even though the vault is allowed "
              "(the order of the tests is what does that)")
    roots = atex.working_tree_roots()
    for root in roots:
        LEDGER.ok(refuses(lambda r=root: wm.resolve_out(
                      os.path.join(r, "toolkit", "atlas.json")),
                      wm.Refused, "checkout of this repository"),
                  f"a write into {'the MAIN checkout' if root != os.path.abspath(wm.REPO_ROOT) else 'this checkout'} is REFUSED",
                  root)
    LEDGER.ok(len(roots) >= 1,
              "working_tree_roots() found at least this tree",
              f"{len(roots)}: {roots}")

    # Positive controls. A guard that refuses everything protects nothing,
    # because the tool then never runs.
    ok = vaultpath.vault_path("exports", "worldmap", "atlas.json")
    LEDGER.ok(wm.resolve_out(ok) == os.path.abspath(ok),
              "a path under the vault is ALLOWED")
    scratch = os.path.join(tempfile.gettempdir(), "rurik_worldmap_atlas.json")
    LEDGER.ok(wm.resolve_out(scratch) == os.path.abspath(scratch),
              "and an ordinary scratch path is ALLOWED")

    # ---- the syntax tree, read off the MODULE UNDER TEST ------------------
    #
    # `wm.__file__`, not `HERE/worldmap.py`. Those are the same file on an
    # ordinary run and DIFFERENT under `--module`, which is the mode the floor
    # comment's whole sabotage table is measured in -- so a section reading
    # HERE is structurally exempt from every sabotage this file claims to have
    # survived, and the exemption is invisible because the run stays green.
    # MEASURED: with the old spelling, a worldmap.py whose main() never calls
    # resolve_out AT ALL and writes straight to `a.out` scored ALL CHECKS
    # PASSED (69 checks), exit 0. That is `test_atex.py` section 3's defect
    # exactly -- a guard that exists, is documented, is greppable, and is never
    # invoked -- reproduced here by the test's own choice of source file.
    import ast
    src = open(wm.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    fn = next(n for n in tree.body
              if isinstance(n, ast.FunctionDef) and n.name == "main")
    calls = {n.func.id: n.lineno for n in ast.walk(fn)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id in ("resolve_out", "PE")}
    LEDGER.ok(len(calls) == 2 and calls["resolve_out"] < calls["PE"],
              "main() resolves --out BEFORE it opens the client, so a refused "
              "path costs nothing", str(calls))

    # `out_path` has to BE the guard's answer, not a name that happens to sit
    # beside a call to it. `resolve_out` returns the resolved path and the
    # write must use THAT.
    guarded_names = {t.id
                     for n in ast.walk(fn) if isinstance(n, ast.Assign)
                     for t in n.targets if isinstance(t, ast.Name)
                     if isinstance(n.value, ast.Call)
                     and isinstance(n.value.func, ast.Name)
                     and n.value.func.id == "resolve_out"}
    guarded_names |= {t.id
                      for n in ast.walk(fn) if isinstance(n, ast.Assign)
                      for t in n.targets if isinstance(t, ast.Name)
                      if isinstance(n.value, ast.IfExp)
                      and isinstance(n.value.body, ast.Call)
                      and isinstance(n.value.body.func, ast.Name)
                      and n.value.body.func.id == "resolve_out"}
    LEDGER.ok(guarded_names, "main() binds a name to resolve_out's own answer",
              str(guarded_names))

    # Every write site in the WHOLE module, and each one's path expression.
    # Not `open(..., "w")` alone: this module writes through
    # `Path(x).write_text`, which an `open`-only scan sees as zero write sites
    # and passes VACUOUSLY -- the shape `test_atex.py` section 3 warns about,
    # one level up.
    WRITE_METHODS = ("write_text", "write_bytes")
    writes = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        if isinstance(n.func, ast.Name) and n.func.id == "open":
            mode = n.args[1] if len(n.args) > 1 else None
            m = mode.value if isinstance(mode, ast.Constant) else ""
            if any(c in str(m) for c in "wax"):
                writes.append((n.lineno, n.args[0] if n.args else None))
        elif isinstance(n.func, ast.Attribute) and n.func.attr in WRITE_METHODS:
            # Path(<expr>).write_text(...)
            recv = n.func.value
            arg = (recv.args[0] if isinstance(recv, ast.Call) and recv.args
                   else recv)
            writes.append((n.lineno, arg))
        elif isinstance(n.func, ast.Attribute) and n.func.attr == "open":
            mode = n.args[0] if n.args else None
            m = mode.value if isinstance(mode, ast.Constant) else ""
            if any(c in str(m) for c in "wax"):
                writes.append((n.lineno, n.func.value))
    unguarded = [(ln, ast.dump(a) if a is not None else "?")
                 for ln, a in writes
                 if not (isinstance(a, ast.Name) and a.id in guarded_names)]
    LEDGER.ok(writes and not unguarded,
              "EVERY write site in the module writes the GUARDED path -- asked "
              "of the syntax tree, because a guard can be called, be greppable "
              "and have its answer thrown away",
              f"{len(writes)} write site(s), unguarded: {unguarded}")

    # Carve-out (1) scopes capstone/pefile to msghandler.py and codescan.py.
    # This is neither, and a bare machine has to be able to run it.
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.module:
            imported.add(n.module.split(".")[0])
    LEDGER.ok(not (imported & {"capstone", "pefile", "PIL", "numpy"}),
              "the module takes NO third-party dependency -- carve-out (1) "
              "names two files and this is not one of them",
              str(sorted(imported)))


def section_emitted(pe, exe, gets, grids, tiles):
    print("\n7. the emitted index: provenance per row, and the two conditions")
    payload = wm.index_payload(pe, exe, tiles, gets, grids)
    rows = payload["tiles"]
    LEDGER.ok(len(rows) == len(tiles), "one row per tile", str(len(rows)))
    LEDGER.ok(payload["build"] == pinned.BUILD == 38797,
              "the build is recorded (content.py's condition 2 for client-table)",
              str(payload["build"]))
    LEDGER.ok(all(r["provenance"]["source"] == "client-table"
                  and r["provenance"]["build"] == pinned.BUILD
                  and r["provenance"]["extractor"]
                  == "toolkit/clientscan/worldmap.py"
                  for r in rows),
              "every row names its source, its extractor and its build "
              "(condition 3 is per-ROW, not per-file)")
    LEDGER.ok(all(r["provenance"]["image"].startswith("pristine")
                  for r in rows),
              "and names WHICH image it read, not just the build -- "
              "`--exe` takes any file and pinned.find() falls back to C:\\gw",
              rows[0]["provenance"]["image"])

    # THE CONTROL, and the reason the build is not `pinned.BUILD` on the row.
    # Stamped from the constant, an index extracted from an unidentified binary
    # -- the live install, a patched copy, a future build -- claims 38797 and
    # nothing downstream can tell. This must NOT claim it.
    unknown = wm.index_payload(pe, os.path.join(HERE, "no_such_client.exe"),
                               tiles[:4], gets, grids)
    LEDGER.ok(unknown["build"] is None
              and all(r["provenance"]["build"] is None
                      for r in unknown["tiles"]),
              "an index built from an UNIDENTIFIED image records build None, "
              "not 38797 -- the build is measured from the file, never taken "
              "from a constant",
              f"{unknown['build']} / {unknown['image']}")
    extractor = os.path.join(os.path.dirname(os.path.dirname(HERE)),
                             "toolkit", "clientscan", "worldmap.py")
    LEDGER.ok(os.path.isfile(extractor),
              "and the extractor it names is in this repo (condition 1)",
              extractor)
    LEDGER.ok(all(f"0x{EXPECT_TABLE_VA[r['tier']]:08X}"
                  in r["provenance"]["note"] for r in rows),
              "each row's note carries the tile table VA it was read from, "
              "which is what makes the row auditable without this session")
    keys = {(r["tier"], r["world"], r["chunk_x"], r["chunk_y"]) for r in rows}
    LEDGER.ok(len(keys) == len(rows),
              "(tier, world, chunk_x, chunk_y) is a key -- no cell is emitted "
              "twice", f"{len(keys)} keys, {len(rows)} rows")
    blob = repr(payload)
    LEDGER.ok("ATEX" not in blob.replace("'magic': 'ATEX'", "")
              and all(isinstance(r["file_id"], int) for r in rows),
              "the payload commits IDS and OFFSETS only -- no ArenaNet bytes "
              "and no authored text")


# --------------------------------------------------------------------------

def main():
    print("worldmap: the per-continent ATEX atlas the compass, mission map "
          "and world map all crop")

    guarded(section_synthetic)
    guarded(section_refusals)
    guarded(section_through_consttable)

    exe = why = None
    what, detail = "unknown", "no client"
    try:
        exe, why = pinned.find()
        what, detail = pinned.identify(exe)
    except SystemExit:
        pass
    # Only the PRISTINE pinned copy. `pinned.find()` falls back to the owner's
    # live install at C:\gw, which auto-updates and may not be 38797 at all --
    # every VA and every line number this file names as a literal is a fact
    # about ONE build, so reading whatever happens to be installed would turn a
    # dozen checks into a claim about an unidentified binary.
    if what != "pristine":
        LEDGER.skip("sections 3-5 and 7 (client)",
                    f"no PRISTINE build {pinned.BUILD} in the vault "
                    f"({exe or 'nothing found'}: {detail}). The synthetic half "
                    f"cannot refute anything about ArenaNet's own layout, so "
                    f"this run goes red and says so.")
        guarded(section_guards)
        return LEDGER.verdict()

    print(f"\nclient: {exe}\n        ({why})")
    LEDGER.ok(what == "pristine",
              "the client read is the PRISTINE pinned copy, not our patched one",
              f"{what}: {detail}")
    pe = PE(exe)
    out = guarded(section_client, pe)
    if out is None:
        LEDGER.skip("sections 4-5 and 7 (archive, index)",
                    "section 3 did not complete, so there are no tiles to join "
                    "or emit")
        guarded(section_guards)
        return LEDGER.verdict()
    gets, wd, grids, tiles = out

    dats = []
    for label, parts in (("dat_study", ("dat_study", "Gw.dat")),
                         ("client/2026-04-30_b174de1f2d8d",
                          ("client", "2026-04-30_b174de1f2d8d", "Gw.dat")),
                         ("client/" + pinned.STAMP,
                          ("client", pinned.STAMP, "Gw.dat"))):
        p = vaultpath.vault_path(*parts)
        if os.path.isfile(p):
            dats.append((label, p))
    if dats:
        guarded(section_archive, tiles, dats)
        guarded(section_dword_early, pe, tiles, dats[0][1])
    else:
        LEDGER.skip("sections 4-5 (archive)",
                    "no Gw.dat in the vault; the tile ids cannot be joined to "
                    "rows, which is where the ATEX magic and the exact "
                    "unresolved set are measured")

    guarded(section_guards)
    guarded(section_emitted, pe, exe, gets, grids, tiles)
    return LEDGER.verdict()


if __name__ == "__main__":
    try:
        code = main()
    finally:
        for p in _TMP:
            try:
                os.unlink(p)
            except OSError:
                pass
    sys.exit(code)
