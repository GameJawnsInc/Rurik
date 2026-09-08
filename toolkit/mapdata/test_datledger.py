"""Check the row census -- and the counting conventions it refuses to choose between.

WHAT MAKES THIS FILE NECESSARY IS NOT THE COUNTING. "26 rows were censused" is a
number an almost-right census also prints. The thing `datledger` exists to do is
tell two DIFFERENT true counts apart and name what separates them, so the
load-bearing fixture here is a PLANTED DISAGREEMENT: a compression-8 row with
FLAG_ENTRY_USED clear, which the `entries` convention counts and the `used`
convention drops. That is correction C-8's mechanism in one row, and section 3
asserts both counts AND the decomposition that reconciles them.

The second thing it exists to do is refuse to bucket a row it does not
understand. The class ladder always terminates, so every row lands somewhere and
the totals always look tidy -- which is the shape of a check that cannot fail.
Section 5 pokes each contradiction into the MFT of a copy and asserts the row is
REPORTED as well as bucketed, then sabotages the anomaly walk and the class
ladder in memory to measure what those two are worth.

The fixture is a complete archive this file builds in a temp directory, with
every class present at once: fifteen structural rows, two spares (one of them
still named by the file-id table), an armed head, stored rows, real `gwenc`
compression-8 rows, an unknown compression code, a bit-31 renamed row, and the
ghost row above. Its MFT is deliberately not a block multiple, so row 3 carries
real slack and can be checked against `datalloc.mft_slack`.

EVERYTHING IS RE-DERIVED FROM THE FIXTURE TABLE. The expected classes, counts
and slack figures below are written out by hand from `ROWS`, never read back out
of `datledger` -- a test that asks the module under test what it computed can
only discover that it is self-consistent.

The third thing, section 6b, is that a RUN HAS FOUR VERBS AND ONLY ONE OF THEM
IS THE CENSUS. Review found `--reencode 9999` printing the entire census and
then reporting "could not census DAT" with exit 2, the code this directory
spends on an unreadable archive -- a false statement about a file the same run
had just finished reading, and the sort a script believes. 6b holds the census
and the verb apart: the census RAN and its headline is on screen, so whatever
failed after it is not evidence about the archive. The pre-fix module reddens
eight of those eleven checks.

Sections 1-6b need no vault, no client and no socket. Section 7 censuses the
vault's live copies and takes C-8 apart, which is the reason it is a section and
not a smoke test: the twenty rows come apart into SEVEN of archive difference
(the two copies are not the same archive) plus THIRTEEN of convention, and the
sixteen comp-8 rows into fifteen of archive difference plus one row's worth of
where the compression split was drawn. It SKIPS whole without the two live
copies.

AND C-8's ROUTE E IS READ FROM THE ARCHIVE IT WAS MEASURED ON. `vault/dat_study`
is the SERVER'S LIVE reference archive and is resynced when the server's moves
-- 38797 -> 38833 on 2026-08-27 -- so a historical correction read off it
reddens the morning of a resync while saying nothing whatever about C-8. Section
7a therefore keeps only what is generation-independent (the +12 is a CONVENTION,
and the comp-8 count does not move between conventions on EITHER copy), and 7b
reads the exact Route E census from the copy preserved for exactly that,
`vault/dat_study_38797`, degrading to a NAMED skip where it is absent. Route C
never needed the move: `client/` is a dated snapshot directory.

    python toolkit/mapdata/test_datledger.py
"""

import ast
import binascii
import contextlib
import io
import json
import os
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ENTRY_SIZE  # noqa: E402
import datalloc  # noqa: E402
import datledger  # noqa: E402
import gwenc  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

# FLOOR: two shapes, and neither has headroom.
#
# `FLOOR_BARE` is what sections 1-6 run with no vault; `FLOOR_VAULT` is the
# total once section 7 finds real archives, and section 7 RAISES the floor to it
# as its last act. Both MEASURED from a green run on 2026-08-20 -- counted off
# the log, never predicted. The two-shape arrangement is `test_bit31.py`'s, and
# it is here for its reason: a single fixed floor set to the bare number leaves a
# vaulted run carrying slack, and slack in a floor is where a deleted section
# hides.
#
# SABOTAGES, applied one at a time to `datledger` in memory (the vault-less
# shape, so the numbers are the ones a bare machine would see), the whole file
# run, `[FAIL]` lines counted, the patch reverted. Nothing on disk was edited.
# These are counts OBSERVED, not predicted:
#
#   `_ordered` reverted to a comprehension over CLASSES (drops
#     any class the ladder produces that CLASSES omits)            1 red
#   `anomalies_of` returns [] (the anomaly walk stops walking)     9 red
#   `classify` on `size == 0` alone -- the pre-2026-08-15 datplan
#     rule, which called an ARMED head a free slot                 6 red
#   `reservation_for` returns `size` (no block rounding)           7 red
#   `check_stamp` returns without comparing                        3 red
#   `file_id_table(raw=False)` -- the convenience form, which
#     registers a masked alias the client cannot resolve           1 red
#   `_phase` neutered to a nullcontext -- every verb's failure
#     falls back to the last-resort handler                        4 red
#   `reencoded_size` without its row-range refusal, so `ar.row`
#     raises the bare IndexError it used to                        3 red
#   the whole PRE-FIX `_run`/`_main`/`reencoded_size` restored
#     verbatim (the two above at once, plus the old blanket
#     "could not census DAT" message)                              8 red
#
# FOUR READINGS WORTH KEEPING.
#
# The first sabotage is the defect this file FOUND in the module, on 2026-08-20:
# `_by_class` and the slack breakdown were both comprehensions over `CLASSES`,
# so a class added to the ladder and not registered there vanished from every
# total while the totals still added up to something tidy. That is the same
# failure the anomaly walk exists to prevent, one level up, in the code that
# reports it. One red is a thin margin and it is the honest one: exactly one
# check can see it, and it exists because the sabotage was run.
#
# `check_stamp` reddening THREE and not one is the second reading, and it cost a
# test-side fix to get there. With the naive detail expression
# `(msg or "...").splitlines()[1]`, a stamp that does not refuse raised
# IndexError INSIDE the check's own argument list -- the section died, the two
# checks behind it never ran, and the entire evidence for the sabotage was one
# unnamed crash. `line()` exists for that; a test that only crashes has said the
# machine is unhappy rather than what broke.
#
# The `size == 0` sabotage reddens section 5b's OWN sabotage check and its
# control, which is correct and worth stating: 5b measures the anomaly walk
# against a healthy ladder, and with the ladder broken underneath it that
# measurement is void rather than passing.
#
# The fourth is the last row of the table, and it is the one that matters: the
# pre-fix module reddens EIGHT of section 6b's eleven checks, which is what
# makes 6b a red-then-green test of a real defect rather than a description of
# code that already worked. The three it does NOT redden are the three that were
# always true and are there to keep the other eight honest -- exit 2, the census
# printing before the failure (the PREMISE: the lie was provable precisely
# because the census had already succeeded on screen), and the control that a
# genuinely unreadable archive still says "could not census".
FLOOR_BARE = 84
# Two vaulted shapes. FLOOR_VAULT is sections 1..7b with the two LIVE copies;
# FLOOR_VAULT_C8 adds the three checks that C-8's Route E census affords when
# the preserved 38797 study copy is on this machine. Same arrangement as
# test_bit31/test_archive, and for the same reason: one fixed number would let
# a vaulted run carry the whole Route E arm as headroom.
FLOOR_VAULT = 94
FLOOR_VAULT_C8 = 97
LEDGER = checks.Ledger("row census", floor=FLOOR_BARE)
check = checks.adopt(LEDGER)

FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"
ENTRY_CRC = 0x14

BLOCK = 512

ROW_HEADER, ROW_IDTABLE, ROW_SELF = 1, 2, 3
# 4..15 stay erased -- the twelve reserved rows every archive on this machine
# keeps zeroed, and which `datcheck` rule 9 refuses to see touched.
ROW_STORED_A = 16
ROW_STORED_B = 17
ROW_COMP8 = 18
ROW_COMP8_B = 19
ROW_OTHER = 20          # compression 12: a code nothing in this repo has seen
ROW_PARTNER = 21        # flags 1: USED, not FIRST_STREAM
ROW_ARMED = 22          # flags 259, size 0: a LIVE head, not a free slot
ROW_SPARE = 23          # flags 0, size 0: genuinely claimable
ROW_SPARE_NAMED = 24    # flags 0, size 0, and the id table still names it
ROW_GHOST = 25          # flags 0, size 128, compression 8 -- THE PLANT
ROW_RENAMED = 26        # named by a bit-31 id
ENTRY_COUNT = 27        # rows 0..26; row 0 is the descriptor
MFT_SIZE = ENTRY_COUNT * ENTRY_SIZE     # 648, deliberately not a block multiple
MFT_SLACK = -MFT_SIZE % BLOCK           # 376 = 15 rows

SLACK_BYTE = 0xCC


def pattern(seed, n):
    return bytes(1 + ((i * 37 + seed * 101) % 255) for i in range(n))


def comp_payload(n):
    """Bytes a compression-8 stream genuinely has to work for.

    Cribbed from `test_datalloc.py`: long exact repeats so the match coder has
    something to find, interleaved with an LCG's output so the literal coder is
    not idle either. Deterministic by construction -- no `random` seed to drift.
    """
    out = bytearray()
    motif = bytes((i * 7 + 3) % 251 for i in range(64))
    seed = 0x9E3779B9
    while len(out) < n:
        out += motif * 8
        for _ in range(48):
            seed = (seed * 1103515245 + 12345) & 0xFFFFFFFF
            out.append((seed >> 16) & 0xFF)
    return bytes(out[:n])


# The two compression-8 rows carry REAL `gwenc` streams, encoded once at import.
# A fixture that marked pattern bytes as compression 8 would be a fixture whose
# comp-8 rows are not comp-8 rows, and section 6 re-encodes one of them.
PLAIN_COMP8 = comp_payload(2048)
PLAIN_COMP8_B = comp_payload(1024)
STREAM_COMP8 = gwenc.encode(PLAIN_COMP8)
STREAM_COMP8_B = gwenc.encode(PLAIN_COMP8_B)

# (file_id, row) exactly as the client would read it -- no masked aliases.
# 0x80004000 carries bit 31: ROW_RENAMED's replacement is pending.
ID_PAIRS = ((0x1000, ROW_STORED_A), (0x1001, ROW_STORED_B),
            (0x1002, ROW_COMP8), (0x1003, ROW_OTHER),
            (0x2000, ROW_ARMED), (0x3000, ROW_SPARE_NAMED),
            (0x80004000, ROW_RENAMED))
IDTABLE = b"".join(struct.pack("<II", f, r) for f, r in ID_PAIRS)

# (payload, compression, flags) for every row that is not a spare. The OFFSETS
# are computed by `_layout` below rather than written here, because two of these
# payloads are `gwenc` output and their length is not a number this file gets to
# choose.
CONTENT = [
    (ROW_HEADER, b"\x00" * 32, 0, 3),
    (ROW_IDTABLE, IDTABLE, 0, 3),
    (ROW_STORED_A, pattern(ROW_STORED_A, 1000), 0, 3),
    (ROW_STORED_B, pattern(ROW_STORED_B, 300), 0, 3),
    (ROW_COMP8, STREAM_COMP8, 8, 3),
    (ROW_COMP8_B, STREAM_COMP8_B, 8, 1),
    (ROW_OTHER, pattern(ROW_OTHER, 100), 12, 3),
    (ROW_PARTNER, pattern(ROW_PARTNER, 200), 0, 1),
    # Not a real stream: nothing decodes a row the allocator has released, and
    # marking it compression 8 is the point -- an encoding declared over bytes
    # no live row claims.
    (ROW_GHOST, pattern(ROW_GHOST, 128), 8, 0),
    (ROW_RENAMED, pattern(ROW_RENAMED, 64), 0, 3),
]
EMPTY = ((ROW_ARMED, 259), (ROW_SPARE, 0), (ROW_SPARE_NAMED, 0))


def blocks_for(n):
    """Whole blocks, rounded up -- spelled out, not imported. This is the
    arithmetic the ledger's `reservation` is checked against."""
    return -(-n // BLOCK)


def _layout():
    """-> ({row: (offset, size, comp, flags)}, payloads, mft_off, file_size).

    Packs the payload rows into consecutive blocks in row order, then the MFT,
    then rounds the file up to the end of the MFT's own reservation -- the
    38833 archives' actual shape, and the one that makes row 3's slack real.
    """
    rows, payloads, blk = {}, {}, 0
    for row, data, comp, flags in CONTENT:
        rows[row] = (blk * BLOCK, len(data), comp, flags)
        payloads[row] = data
        blk += blocks_for(len(data))
    for row, flags in EMPTY:
        rows[row] = (0, 0, 0, flags)
    mft_off = blk * BLOCK
    rows[ROW_SELF] = (mft_off, MFT_SIZE, 0, 3)
    return rows, payloads, mft_off, mft_off + blocks_for(MFT_SIZE) * BLOCK


ROWS, PAYLOADS, MFT_OFF, FILE_SIZE = _layout()

# What every censused row's class MUST be, written out from the table above.
EXPECT_CLASS = {}
for _r in range(1, ENTRY_COUNT):
    if _r < 16:
        EXPECT_CLASS[_r] = "structural"
    elif _r in (ROW_SPARE, ROW_SPARE_NAMED):
        EXPECT_CLASS[_r] = "spare"
    elif _r == ROW_ARMED:
        EXPECT_CLASS[_r] = "armed"
    elif _r == ROW_OTHER:
        EXPECT_CLASS[_r] = "other-comp"
    elif ROWS[_r][2] == 8:
        EXPECT_CLASS[_r] = "comp8"
    else:
        EXPECT_CLASS[_r] = "stored"

# Hand-counted from EXPECT_CLASS, and stated as literals so the two are
# independent: 15 structural (rows 1..15), 2 spares, 1 armed, 4 stored
# (16, 17, 21, 26), 3 comp8 (18, 19, and the ghost at 25), 1 other-comp.
EXPECT_COUNTS = {"structural": 15, "spare": 2, "armed": 1, "stored": 4,
                 "comp8": 3, "other-comp": 1}

# USED rows: 1, 2, 3 (the containers) and 16..22 and 26. Twelve erased rows,
# two spares and the ghost are USED-clear.
EXPECT_USED = 11
EXPECT_USED_GE_16 = 8

# THE PLANTED DISAGREEMENT, in one line: three compression-8 rows exist, two of
# them are live. A census that answers "how many comp-8 rows" without saying
# which convention it used can say either.
EXPECT_COMP8_ENTRIES = 3
EXPECT_COMP8_USED = 2

# The historical figures C-8 is about. This file asserts they appear in the
# module's DOCSTRING (the citation that says why it exists) and NOWHERE in its
# code -- see section 3.
HISTORICAL = ("138,708", "138708", "138,692", "138692",
              "177,341", "177341", "177,321", "177321",
              "38,621", "38621", "38,629", "38629", "38,633", "38633")

# The two censuses correction C-8 puts against each other, transcribed from
# studies/archivewrite/FINDINGS.md's corrections table: "138,708 comp-8 rows
# (Route E) vs 138,692 (Route C skeptic), against 38,621+12 vs 38,629 comp-0.
# The sums are 177,341 and 177,321." They are literals HERE, in the test, and
# are refused in the module -- section 3b enforces that split, because a tool
# that carries the number it is meant to measure can only agree with itself.
C8_ROUTE_E = {"comp0": 38621 + 12, "comp8": 138708, "sum": 177341}
C8_ROUTE_C = {"comp0": 38629, "comp8": 138692, "sum": 177321}


def self_crc(mft):
    """Row 3's crc: the table, skipping row 3's own 24 bytes."""
    acc = binascii.crc32(bytes(mft[0x00:ROW_SELF * ENTRY_SIZE]))
    return binascii.crc32(
        bytes(mft[(ROW_SELF + 1) * ENTRY_SIZE:ENTRY_COUNT * ENTRY_SIZE]), acc)


def build_archive(path, rows=None):
    """A complete, self-checking archive. `rows` varies per fixture."""
    rows = dict(rows or ROWS)
    buf = bytearray(bytes([SLACK_BYTE]) * FILE_SIZE)
    for row, data in PAYLOADS.items():
        off = rows[row][0]
        buf[off:off + len(data)] = data

    head = bytearray(32)
    head[0:4] = FILE_MAGIC
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<Q", head, 0x10, MFT_OFF)
    struct.pack_into("<I", head, 0x18, MFT_SIZE)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head

    mft = bytearray(MFT_SIZE)
    mft[0:4] = MFT_MAGIC
    struct.pack_into("<I", mft, 0x0C, ENTRY_COUNT)
    for row in range(1, ENTRY_COUNT):
        if row not in rows:
            continue                    # 4..15 stay zero
        off, size, comp, flags = rows[row]
        crc = (binascii.crc32(bytes(buf[off:off + size]))
               if row in PAYLOADS else 0)
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         off, size, comp, flags, 0, crc)
    struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + ENTRY_CRC, self_crc(mft))
    buf[MFT_OFF:MFT_OFF + MFT_SIZE] = mft
    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return path


def fresh(tmp, name, **kw):
    return build_archive(os.path.join(tmp, name), **kw)


def poke(path, row, field, fmt, value):
    """Write one MFT field of one row, in place. -> path.

    The row crcs and the MFT self-crc go stale, and that is fine: this is a
    census, not a checker. `datcheck --preflight` is what reads those, and it is
    not the module under test.
    """
    with open(path, "r+b") as fh:
        fh.seek(MFT_OFF + row * ENTRY_SIZE + field)
        fh.write(struct.pack(fmt, value))
    return path


def censused(path):
    """Census one archive and hand back (ledger, summary)."""
    with Archive(path) as ar:
        led = datledger.census(ar)
        return led, datledger.summary(led)


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


def run_cli(*argv):
    """Through `_main` and argparse, because the exit codes are the contract."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = datledger._main(list(argv))
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    return code, buf.getvalue()


def refusal(fn, *a, **kw):
    """Run and return the Refused message, or None if it did not refuse."""
    try:
        with quiet():
            fn(*a, **kw)
    except datledger.Refused as exc:
        return str(exc)
    return None


def raised(fn, *a, **kw):
    """-> (Refused message or None, other exception's text or None).

    `refusal()` catches only `Refused`, so the case section 6b is about -- a
    bare `IndexError` escaping where a house-style refusal belongs -- would fly
    straight past it, out through the section, and be reported by `guarded()` as
    one unnamed crash that also took every check behind it. This one names what
    came out instead, which is the difference between "the machine is unhappy"
    and "this call raises IndexError where it should refuse".
    """
    try:
        with quiet():
            fn(*a, **kw)
    except datledger.Refused as exc:
        return str(exc), None
    except Exception as exc:                                   # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"
    return None, None


def refused_line(out):
    """The REFUSED line of a CLI run's output. Never raises -- see `line()`."""
    for ln in out.splitlines():
        if "REFUSED" in ln:
            return ln.strip()[:78]
    return "-- no REFUSED line was printed"


def line(msg, n=0):
    """The n'th line of a refusal, for a check's detail. Never raises.

    MEASURED, not stylistic. The obvious spelling is
    `(msg or "...").splitlines()[n]`, and with the `check_stamp` sabotage
    applied (see the floor comment) it raised IndexError INSIDE the detail
    argument -- so the check that was supposed to catch the sabotage never ran,
    the section died, and the whole run's evidence was one crash with no name on
    it. A detail expression must not be able to take down the check it decorates.
    """
    lines = (msg or "-- it did not refuse").splitlines()
    if not lines:
        return "-- it refused with an empty message"
    return lines[n if n < len(lines) else -1][:78]


# ------------------------------------------------------- 1. the class ladder

def section_classes(tmp):
    print("\n1. every class the ladder must tell apart, in one archive")
    path = fresh(tmp, "base.dat")
    with Archive(path) as ar:
        check(ar.row_count == ENTRY_COUNT,
              f"the fixture opens with {ENTRY_COUNT} raw rows",
              f"row_count {ar.row_count}, block {ar.block_size}")
        led = datledger.census(ar)
        sm = datledger.summary(led)
        check(len(led) == ENTRY_COUNT - 1 == len(ar.entries),
              f"and censuses {ENTRY_COUNT - 1} of them -- row_count minus the "
              f"descriptor, which is exactly len(entries)",
              f"censused {len(led)}, entries {len(ar.entries)}")

    got = {r.index: r.cls for r in led.rows}
    check(got == EXPECT_CLASS,
          "every row lands in the class the fixture designed for it",
          f"{sum(1 for k in got if got[k] != EXPECT_CLASS.get(k))} disagreement(s)")
    check(sm["classes"] == EXPECT_COUNTS,
          f"and the counts are {EXPECT_COUNTS}", f"got {sm['classes']}")
    check(sum(sm["classes"].values()) == len(led)
          and set(sm["classes"]) <= set(datledger.CLASSES),
          "the classes partition the census, and every name the ladder "
          "produced is one the module PUBLISHES -- an unpublished class is a "
          "row nobody reading CLASSES knows to look for",
          f"{sum(sm['classes'].values())} of {len(led)}: "
          f"{sorted(set(sm['classes']) - set(datledger.CLASSES))} unpublished")

    check(led.row(ROW_ARMED).cls == "armed"
          and led.row(ROW_SPARE).cls == "spare",
          "the ARMED head (USED, size 0) and the SPARE (USED clear, size 0) "
          "are told apart -- `size == 0` alone offered a live map head as "
          "claimable until datplan was fixed on 2026-08-15",
          f"row {ROW_ARMED} flags {led.row(ROW_ARMED).flags}, "
          f"row {ROW_SPARE} flags {led.row(ROW_SPARE).flags}")
    check(led.row(ROW_OTHER).cls == "other-comp"
          and sm["other_comp_codes"] == {"12": 1},
          "an unknown compression code gets its own class AND keeps its code "
          "in the summary -- `other-comp` on its own names nothing",
          f"codes {sm['other_comp_codes']}")

    print("\n1a. renamed is a FLAG on top of the class, not a class")
    ren = led.row(ROW_RENAMED)
    check(ren.cls == "stored" and ren.renamed,
          "the bit-31 row is stored AND renamed, not 'renamed' instead of a "
          "class",
          f"class {ren.cls}, ids {[hex(f) for f in ren.file_ids]}")
    check(ren.file_ids == (0x80004000,),
          "and it carries the RAW id -- the masked alias file_id_table() "
          "registers by default is what the client cannot resolve",
          f"{[hex(f) for f in ren.file_ids]}")
    check(sm["renamed_rows"] == 1 and sm["named_rows"] == len(ID_PAIRS),
          f"{len(ID_PAIRS)} rows are named, 1 of them by a bit-31 id",
          f"named {sm['named_rows']}, renamed {sm['renamed_rows']}")
    check(all(not r.renamed for r in led.rows if r.index != ROW_RENAMED),
          "and no other row is flagged renamed")


# ------------------------------------------------------ 2. slack arithmetic

def section_slack(tmp):
    print("\n2. reservation and slack, against arithmetic done here")
    led, sm = censused(fresh(tmp, "slack.dat"))

    wrong = [r.index for r in led.rows
             if r.reservation != blocks_for(r.size) * BLOCK
             or r.slack != blocks_for(r.size) * BLOCK - r.size]
    check(not wrong,
          "every row's reservation is its size rounded up to whole blocks, and "
          "its slack is the difference -- computed here, not asked of the "
          "module",
          f"{len(wrong)} row(s) disagree: {wrong[:8]}")

    check(led.row(ROW_STORED_A).slack == 24
          and led.row(ROW_STORED_B).slack == 212,
          "the two hand-computed cases: 1,000 B in 1,024 leaves 24; 300 B in "
          "512 leaves 212",
          f"{led.row(ROW_STORED_A).slack}, {led.row(ROW_STORED_B).slack}")
    check(led.row(ROW_SPARE).reservation == 0
          and led.row(ROW_SPARE).slack == 0,
          "a zero-size row reserves nothing and therefore has no slack -- it "
          "is capacity, but it is not SLACK, and adding it to the total would "
          "double-count the free run it sits in")

    hand = sum(blocks_for(ROWS[r][1]) * BLOCK - ROWS[r][1]
               for r in range(1, ENTRY_COUNT) if r in ROWS)
    check(sm["slack"]["total"] == hand,
          f"the total is {hand:,} B, summed independently from the fixture "
          f"table", f"ledger says {sm['slack']['total']:,}")
    check(sum(sm["slack"]["by_class"].values()) == sm["slack"]["total"],
          "and the per-class breakdown adds back up to it")

    print("\n2a. the MFT's own row, against datalloc's honest capacity bound")
    with Archive(os.path.join(tmp, "slack.dat")) as ar:
        bound = datalloc.mft_slack(ar)
    check(led.row(ROW_SELF).slack == bound == MFT_SLACK,
          f"row 3's slack IS mft_slack() -- {MFT_SLACK} B, or "
          f"{MFT_SLACK // ENTRY_SIZE} rows of table growth. Two modules, one "
          f"number, neither importing the other's",
          f"ledger {led.row(ROW_SELF).slack}, datalloc {bound}")

    top = sm["largest_slack"]
    check(top and all(top[i]["slack"] >= top[i + 1]["slack"]
                      for i in range(len(top) - 1)),
          "the largest-slack table is ordered", f"{len(top)} row(s)")
    check(all(r["slack"] > 0 for r in top),
          "and holds no zero-slack rows -- 177,000 rows tied at zero would be "
          "the whole table")
    check(top and top[0]["index"] == ROW_HEADER
          and top[0]["slack"] == BLOCK - 32,
          f"the fattest row here is the 32-byte file header in its own block "
          f"({BLOCK - 32} B)",
          f"row {top[0]['index']}, {top[0]['slack']} B" if top
          else "-- the table is EMPTY")


# ------------------------------------------------- 3. the C-8 reconciliation

def section_conventions(tmp):
    print("\n3. how many rows? -- one answer per convention, and the difference "
          "named")
    led, sm = censused(fresh(tmp, "conv.dat"))
    con = sm["conventions"]

    check(con["raw_rows"]["count"] == ENTRY_COUNT
          and con["entries"]["count"] == ENTRY_COUNT - 1,
          "raw_rows counts the descriptor at row 0 and `entries` does not -- "
          "the pair archive.py's docstring says produced '177,334 vs 177,335' "
          "in a study as evidence two tools numbered rows differently",
          f"{con['raw_rows']['count']} vs {con['entries']['count']}")
    check(con["raw_rows"]["by_compression"] == con["entries"]["by_compression"],
          "and they differ by ONE ROW and by ZERO in every compression bucket, "
          "because the descriptor holds no payload",
          f"{con['entries']['by_compression']}")
    check(con["used"]["count"] == EXPECT_USED
          and con["used_ge_16"]["count"] == EXPECT_USED_GE_16,
          f"USED rows are {EXPECT_USED} and USED-at-or-above-16 are "
          f"{EXPECT_USED_GE_16}",
          f"got {con['used']['count']} and {con['used_ge_16']['count']}")

    print("\n3a. THE PLANT: one comp-8 row, USED-clear, counted by one "
          "convention and dropped by the next")
    check(con["entries"]["by_compression"]["8"] == EXPECT_COMP8_ENTRIES,
          f"the `entries` convention finds {EXPECT_COMP8_ENTRIES} "
          f"compression-8 rows",
          f"got {con['entries']['by_compression']['8']}")
    check(con["used"]["by_compression"]["8"] == EXPECT_COMP8_USED,
          f"the `used` convention finds {EXPECT_COMP8_USED} -- both are true "
          f"and the bare question 'how many comp-8 rows' has no answer",
          f"got {con['used']['by_compression']['8']}")

    deltas = {(d["from"], d["to"]): d for d in sm["deltas"]}
    d1 = deltas[("entries", "used")]
    check(d1["rows"] == (ENTRY_COUNT - 1) - EXPECT_USED
          and con["entries"]["count"] - d1["rows"] == con["used"]["count"],
          "the two counts differ by exactly the rows the delta names -- the "
          "decomposition adds up rather than merely reading plausibly",
          f"{con['entries']['count']} - {d1['rows']} = {con['used']['count']}")
    check(d1["by_class"] == {"structural": 12, "spare": 2, "comp8": 1},
          "and it is decomposed into CLASSES: twelve erased structural rows, "
          "two spares, and one comp-8 row that is not live. 'The sixteen' "
          "stops being a contradiction the moment it has a name",
          f"{d1['by_class']}")
    check(d1["by_compression"] == {"0": 14, "8": 1},
          "the same difference by compression code, which is where the comp-8 "
          "disagreement itself lands", f"{d1['by_compression']}")

    d2 = deltas[("used", "used_ge_16")]
    check(d2["rows"] == 3 and d2["by_class"] == {"structural": 3},
          "and USED -> USED>=16 drops exactly the three container rows (the "
          "file header, the file-id table, and the MFT's own row)",
          f"{d2['rows']} row(s): {d2['by_class']}")
    check(deltas[("raw_rows", "entries")]["rows"] == 1,
          "while raw_rows -> entries drops one row and names it the descriptor")

    print("\n3b. and no historical figure is wired into the code")
    src = open(datledger.__file__, encoding="utf-8").read()
    tree = ast.parse(src)
    doc = tree.body[0].value if (
        tree.body and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)) else None
    check(doc is not None and any(h in doc.value for h in HISTORICAL),
          "CONTROL: the module's own docstring DOES quote C-8's figures -- "
          "otherwise the check below passes vacuously on a module that never "
          "heard of the correction")
    leaked = sorted({h for node in ast.walk(tree)
                     if isinstance(node, ast.Constant) and node is not doc
                     for h in HISTORICAL if h in str(node.value)})
    check(not leaked,
          "and they appear in NO other literal: the numbers a real run must "
          "measure are not sitting in the code that would report them",
          f"leaked: {leaked}")


# -------------------------------------------------------------- 4. the stamp

def section_stamp(tmp):
    print("\n4. the stamp, which is how a stale ledger is caught")
    path = fresh(tmp, "stamp.dat")
    led, sm = censused(path)
    out = os.path.join(tmp, "stamp.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(datledger.to_json(led, sm), fh)
    doc = datledger.load(out)

    with Archive(path) as ar:
        check(datledger.check_stamp(doc, ar) is not None,
              "CONTROL: the ledger clears its own archive -- a stamp that "
              "refuses everything protects nothing, because nobody uses it")
    check(doc["stamp"]["mft_sha256"] == led.mft_sha256
          and doc["stamp"]["size_on_disk"] == FILE_SIZE,
          "and the stamp on disk is the one the census took",
          f"{doc['stamp']['mft_sha256'][:16]}..., {FILE_SIZE} B")
    check(len(doc["rows"]) == ENTRY_COUNT - 1
          and doc["rows"][0]["index"] == 1,
          "the JSON carries every censused row, first one first",
          f"{len(doc['rows'])} rows")

    moved = shutil.copyfile(path, os.path.join(tmp, "stamp-moved.dat"))
    with Archive(moved) as ar:
        check(refusal(datledger.check_stamp, doc, ar) is None,
              "a byte-identical COPY under another name still clears -- the "
              "stamp deliberately does not compare the path, because "
              "censusing a copy is how the cross-copy tables were measured")

    touched = shutil.copyfile(path, os.path.join(tmp, "stamp-touched.dat"))
    poke(touched, ROW_STORED_B, 0x08, "<I", 301)          # one size field
    with Archive(touched) as ar:
        msg = refusal(datledger.check_stamp, doc, ar)
    check(msg and "mft_sha256" in msg,
          "one changed MFT field is caught, and the refusal NAMES the field",
          line(msg, 1))
    check(msg and "datledger.py --dat" in msg,
          "and names the remedy: re-take the ledger")

    grown = shutil.copyfile(path, os.path.join(tmp, "stamp-grown.dat"))
    with open(grown, "ab") as fh:
        fh.write(b"\x00" * BLOCK)
    with Archive(grown) as ar:
        msg = refusal(datledger.check_stamp, doc, ar)
    check(msg and "size_on_disk" in msg,
          "and a file that GREW while its MFT stayed put is caught too -- the "
          "one change no row-by-row comparison can see",
          line(msg, 1))

    print("\n4a. and load() refuses anything that is not a ledger")
    bad = os.path.join(tmp, "bad.json")
    for mutate, why in (
            (lambda d: d.update(format_version=99), "format_version"),
            (lambda d: d.pop("stamp"), "stamp"),
            (lambda d: d["stamp"].pop("mft_sha256"), "mft_sha256"),
            (lambda d: d.pop("rows"), "rows")):
        doc2 = json.loads(json.dumps(doc))
        mutate(doc2)
        with open(bad, "w", encoding="utf-8") as fh:
            json.dump(doc2, fh)
        msg = refusal(datledger.load, bad)
        check(msg and why in msg,
              f"a ledger missing/mangling {why!r} is refused by name",
              (msg or "-- it did not refuse")[:78])
    with open(bad, "w", encoding="utf-8") as fh:
        fh.write("[]")
    check(refusal(datledger.load, bad), "and a JSON array is not a ledger")


# ------------------------------------- 5. rows whose own rules disagree

def section_anomalies(tmp):
    print("\n5. a row whose rules disagree is REPORTED, not silently bucketed")
    led, sm = censused(fresh(tmp, "anom.dat"))
    check(sorted(sm["anomalies"]) == ["used-clear-but-named",
                                      "used-clear-with-extent"],
          "the base fixture carries exactly the two anomalies it plants",
          f"{sorted(sm['anomalies'])}")
    ghost = led.row(ROW_GHOST)
    check(ghost.cls == "comp8" and "used-clear-with-extent" in ghost.anomalies,
          "the ghost row is bucketed AND flagged: the ladder always "
          "terminates, so without the flag it would be an ordinary comp-8 row "
          "in every total",
          f"class {ghost.cls}, {list(ghost.anomalies)}")
    # `.get`, not `[...]`: with the anomaly walk sabotaged this key is absent,
    # and a KeyError inside the check's own expression kills the section and
    # every check behind it instead of going red by name.
    rec = sm["anomalies"].get("used-clear-with-extent", {})
    check(rec.get("first") == [ROW_GHOST] and rec.get("why"),
          "and the summary names the row and says why it is an anomaly",
          f"{rec.get('first')}")
    check(led.row(ROW_SPARE_NAMED).cls == "spare"
          and "used-clear-but-named" in led.row(ROW_SPARE_NAMED).anomalies
          and not led.row(ROW_SPARE).anomalies,
          "a spare the file-id table still names is flagged; the unnamed spare "
          "beside it is not -- a spare with nothing pointing at it is normal, "
          "which is the correction datcheck rule 10 took on 2026-08-13")

    print("\n5a. one poked field per anomaly, into a copy's MFT")
    cases = (
        (ROW_ARMED, 0x0C, "<H", 8, "zero-size-with-compression", "armed"),
        (ROW_STORED_A, 0x00, "<Q", ROWS[ROW_STORED_A][0] + 1,
         "unaligned-extent", "stored"),
        (ROW_STORED_B, 0x08, "<I", FILE_SIZE, "extent-past-eof", "stored"),
        (7, 0x08, "<I", 64, "structural-not-erased", "structural"),
    )
    for row, field, fmt, value, name, cls in cases:
        p = poke(fresh(tmp, f"anom-{name}.dat"), row, field, fmt, value)
        led2, sm2 = censused(p)
        r = led2.row(row)
        check(name in r.anomalies and r.cls == cls
              and sm2["anomalies"].get(name, {}).get("rows") == 1,
              f"{name}: row {row} is still classed '{cls}' and is reported",
              f"class {r.cls}, {list(r.anomalies)}")

    print("\n5b. SABOTAGE: what the anomaly walk and the ladder are worth")
    real = datledger.anomalies_of
    try:
        datledger.anomalies_of = lambda *a, **kw: []
        _led3, sm3 = censused(os.path.join(tmp, "anom.dat"))
        check(not sm3["anomalies"] and sm3["classes"] == EXPECT_COUNTS,
              "SABOTAGE: with the anomaly walk stubbed out the census prints "
              "the SAME tidy class totals and reports nothing wrong -- which "
              "is what a class ladder alone buys you",
              f"anomalies {sm3['anomalies']}, classes unchanged")
    finally:
        datledger.anomalies_of = real
    _led4, sm4 = censused(os.path.join(tmp, "anom.dat"))
    check(len(sm4["anomalies"]) == 2,
          "CONTROL: and both are back once the sabotage is undone rather than "
          "left in place")

    real_classify = datledger.classify
    try:
        # The pre-2026-08-15 datplan rule, restored on purpose: `size == 0`
        # alone, with no look at FLAG_ENTRY_USED.
        def naive(e):
            if e.index < 16:
                return "structural"
            if e.size == 0:
                return "spare"
            return real_classify(e)
        datledger.classify = naive
        led5, sm5 = censused(os.path.join(tmp, "anom.dat"))
        check(led5.row(ROW_ARMED).cls == "spare"
              and sm5["classes"].get("armed") is None,
              "SABOTAGE: classing on `size == 0` alone files the ARMED head as "
              "a claimable spare and the archive reports zero armed rows -- "
              "the exact reading that offered row 71496 of dat_c2 as free")
    finally:
        datledger.classify = real_classify
    check(censused(os.path.join(tmp, "anom.dat"))[0].row(ROW_ARMED).cls
          == "armed",
          "CONTROL: armed again with the real ladder restored")

    try:
        # A class the module does not publish in CLASSES. The natural spelling
        # of the summary -- a comprehension over CLASSES -- drops it, and every
        # total stays tidy while a row goes missing from all of them.
        datledger.classify = lambda e: ("mystery" if e.index == ROW_GHOST
                                        else real_classify(e))
        led6, sm6 = censused(os.path.join(tmp, "anom.dat"))
        check(sm6["classes"].get("mystery") == 1
              and sum(sm6["classes"].values()) == len(led6)
              and "mystery" in sm6["slack"]["by_class"],
              "a class the module does not publish is COUNTED anyway, in the "
              "class census AND the slack breakdown -- the totals cannot be "
              "made tidy by losing a row",
              f"{sm6['classes']}")
    finally:
        datledger.classify = real_classify


# ---------------------------------------------------------------- 6. the CLI

def section_cli(tmp):
    print("\n6. the CLI, its two exit codes, and the slow verb")
    dat = fresh(tmp, "cli.dat")
    code, out = run_cli("--dat", dat)
    check(code == 0, f"a plain census exits 0 (got {code})")
    check("raw rows (row_count)" in out and "censused" in out,
          "and the headline states BOTH counts rather than picking one",
          out.splitlines()[1].strip()[:78] if len(out.splitlines()) > 1 else "")
    check("classes:" in out and "structural" in out,
          "and prints the class census")

    code, out = run_cli("--dat", dat, "--summary")
    check(code == 0 and "one answer per convention" in out,
          f"--summary prints the conventions block (got {code})")
    check("entries -> used" in out and "by class:" in out,
          "including the delta that decomposes the disagreement")

    out_json = os.path.join(tmp, "cli.json")
    code, txt = run_cli("--dat", dat, "--json", out_json)
    check(code == 0 and os.path.isfile(out_json),
          f"--json writes where it was told (got {code})")
    check(datledger.load(out_json)["stamp"]["row_count"] == ENTRY_COUNT,
          "and what it wrote loads back as a stamped ledger")

    repo = os.path.dirname(HERE)                       # <tree>/toolkit
    victim = os.path.join(repo, "nope-ledger.json")
    code, txt = run_cli("--dat", dat, "--json", victim)
    check(code == 2 and "REFUSED" in txt,
          f"--json into a checkout is refused with exit 2, not a traceback "
          f"(got {code})")
    check(not os.path.isfile(victim), "and nothing was written there")

    code, txt = run_cli("--dat", os.path.join(tmp, "nope.dat"))
    check(code == 2 and "REFUSED" in txt,
          f"an unreadable archive exits 2 (got {code}) -- there is no exit 1 "
          f"here, because a census is not a comparison")

    print("\n6a. --reencode, the verb that is not a column")
    code, txt = run_cli("--dat", dat, "--reencode", str(ROW_COMP8))
    check(code == 0 and "re-encoded" in txt,
          f"--reencode measures a comp-8 row (got {code})")
    with Archive(dat) as ar:
        rec = datledger.reencoded_size(ar, ROW_COMP8)
        stored_msg = refusal(datledger.reencoded_size, ar, ROW_STORED_A)
    # The armed head marked compression 8 -- section 5a's anomaly, asked the
    # question that anomaly makes unanswerable. A copy, because the poke leaves
    # the row crcs stale and the other checks here read the healthy fixture.
    zero = poke(fresh(tmp, "cli-zero.dat"), ROW_ARMED, 0x0C, "<H", 8)
    with Archive(zero) as ar:
        armed_msg = refusal(datledger.reencoded_size, ar, ROW_ARMED)
    check(rec["plain"] == len(PLAIN_COMP8) and rec["declared_agrees"],
          f"the decode gives back the {len(PLAIN_COMP8):,} B payload the "
          f"fixture encoded", f"{rec['plain']} B, declared {rec['declared']}")
    check(rec["encoded"] == len(STREAM_COMP8) == rec["stored"],
          "and the re-encode is byte-for-byte the same length as the stream on "
          "disk -- which proves the loop is closed, and proves nothing about "
          "what the retail client would accept",
          f"{rec['encoded']} B vs {rec['stored']} B stored")
    check(rec["headroom"] == rec["reservation"] - rec["encoded"]
          and rec["reservation"] == BLOCK,
          f"headroom is measured against the RESERVATION, not the size "
          f"({rec['reservation']} B - {rec['encoded']} B = {rec['headroom']} B)")
    check(stored_msg and "not 8" in stored_msg,
          "a stored row is refused -- there is nothing to re-encode",
          line(stored_msg))
    check(armed_msg and "size 0" in armed_msg,
          "and so is a zero-size row, naming the anomaly the census records "
          "for it")


# --------------------------------- 6b. WHICH verb failed, and which did not

def section_attribution(tmp):
    """A failing verb must not blame the archive the census just read fine.

    THE DEFECT THIS SECTION EXISTS FOR, found by review on 2026-08-20: `_run`
    did four separable things inside one try, and `_main`'s last-resort handler
    labelled every failure "could not census DAT". So `--reencode 9999` printed
    the whole census -- headline, classes, slack -- and then announced that the
    archive could not be read, under exit 2, whose entire meaning in this
    directory is "unreadable archive". A script reading only the code would file
    a healthy 4.2 GB archive as damaged because somebody mistyped a row number.

    A wrong message is not a cosmetic fault when the message is the product. So
    the checks below are about ATTRIBUTION and nothing else: the census ran (and
    the output proves it), and the refusal names the verb that did not.
    """
    print("\n6b. a verb that fails must not blame the archive")
    dat = fresh(tmp, "attrib.dat")

    with Archive(dat) as ar:
        got = {row: raised(datledger.reencoded_size, ar, row)
               for row in (ENTRY_COUNT + 9973, 0, -1)}
    bad = ", ".join(f"row {r}: {other or 'it did not refuse at all'}"
                    for r, (msg, other) in got.items() if not msg)
    check(all(msg for msg, _ in got.values()),
          "a row this archive does not have is REFUSED by name -- the third of "
          "reencoded_size's three operator errors, and the likeliest: the "
          "other two (not comp-8, size 0) were house-style from the start "
          "while this one fell out of ar.row() as a bare IndexError",
          bad or "all three refused")
    check(all(msg and f"1..{ENTRY_COUNT - 1}" in msg
              for msg, _ in got.values()),
          f"and each states the rows this archive actually HAS "
          f"(1..{ENTRY_COUNT - 1}), which is the bound archive.py writes -- not "
          f"a second copy of the arithmetic this module exists to be careful "
          f"about",
          line(got[0][0], 1))
    check(got[0][0] and "--summary" in got[0][0],
          "and names the remedy, the way every other refusal here does",
          line(got[0][0], 3))

    print("\n6b-i. and the CLI names the VERB, having already printed the "
          "census")
    code, out = run_cli("--dat", dat, "--reencode", str(ENTRY_COUNT + 9973))
    check(code == 2 and "REFUSED" in out,
          f"a mistyped --reencode row exits 2 (got {code})", refused_line(out))
    check("raw rows (row_count)" in out and "classes:" in out,
          "the census RAN and printed first -- which is what makes the old "
          "message a provable lie and not a wording quibble",
          out.splitlines()[0][:78] if out.splitlines() else "-- no output")
    check("could not census" not in out and str(ENTRY_COUNT + 9973) in out,
          "so the refusal names the ROW, not the archive: three lines above it "
          "the same run reported that archive's block size, MFT and class "
          "census",
          refused_line(out))

    broken = fresh(tmp, "attrib-broken.dat")
    with open(broken, "r+b") as fh:
        fh.seek(ROWS[ROW_COMP8][0] + 8)
        fh.write(b"\xff" * 64)              # a stream that will not round-trip
    code, out = run_cli("--dat", broken, "--reencode", str(ROW_COMP8))
    check(code == 2 and f"re-encode row {ROW_COMP8}" in out
          and "could not census" not in out,
          f"and an unexpected failure INSIDE the slow verb -- a comp-8 stream "
          f"that will not round-trip -- is reported as a failure to re-encode "
          f"row {ROW_COMP8}, not as a failure to read the file (got {code})",
          refused_line(out))

    code, out = run_cli("--dat", dat, "--json",
                        os.path.join(tmp, "no-such-dir", "out.json"))
    check(code == 2 and "write the ledger" in out
          and "could not census" not in out,
          f"the same for --json: a destination that cannot be opened is a "
          f"failure to WRITE, named as one (got {code})",
          refused_line(out))

    code, out = run_cli("--dat", os.path.join(tmp, "gone.dat"))
    check(code == 2 and "could not census" in out,
          "CONTROL: an archive that genuinely cannot be read DOES say 'could "
          "not census' -- without this the three checks above would pass on a "
          "tool that had simply stopped using the phrase",
          refused_line(out))

    print("\n6b-ii. SABOTAGE: with the phase labels removed, the blanket "
          "handler admits it does not know")
    real_phase = datledger._phase
    try:
        datledger._phase = lambda *a, **kw: contextlib.nullcontext()
        code, out = run_cli("--dat", broken, "--reencode", str(ROW_COMP8))
        check(code == 2 and f"re-encode row {ROW_COMP8}" not in out
              and "datledger failed on" in out,
              "SABOTAGE: neutered, the same run falls back to the last-resort "
              "handler -- which says only that datledger failed, because "
              "without the phases it genuinely does not know which verb did. "
              "That is the honest vague message; 'could not census' was the "
              "confident wrong one",
              refused_line(out))
    finally:
        datledger._phase = real_phase
    code, out = run_cli("--dat", broken, "--reencode", str(ROW_COMP8))
    check(f"re-encode row {ROW_COMP8}" in out,
          "CONTROL: and the verb is named again once the sabotage is undone",
          refused_line(out))


# ------------------------------------------------------- 7. a real archive

def section_vault():
    print("\n7. two real archives, and correction C-8 taken apart on them")
    try:
        root = vaultpath.require_dir()
    except SystemExit:
        # require_dir, not vault_root: vault_root() never raises, so a fixture
        # built on it silently resolves to nothing and turns every assertion
        # behind it into a no-op.
        LEDGER.skip("the real-archive census", "no vault on this machine")
        return
    copies = {"study": os.path.join(root, "dat_study", "Gw.dat"),
              "install": os.path.join(root, "client",
                                      "2026-07-29_221c13772c7a", "Gw.dat")}
    # The archive correction C-8's Route E census was MEASURED ON, kept out of
    # `copies` because section 7b degrades to a named skip without it while
    # the two above are what the section skips whole for.
    c8_study = os.path.join(root, "dat_study_38797", "Gw.dat")
    missing = [k for k, p in copies.items() if not os.path.isfile(p)]
    if missing:
        LEDGER.skip("the real-archive census",
                    f"absent from this vault: {', '.join(missing)}")
        return

    dat = copies["study"]
    led, sm = censused(dat)
    print("\n".join(datledger.format_headline(led, sm)))
    print("\n".join(datledger.format_summary(sm)))
    con = sm["conventions"]
    check(con["raw_rows"]["count"] == con["entries"]["count"] + 1
          == led.row_count,
          f"raw_rows {con['raw_rows']['count']:,} is entries "
          f"{con['entries']['count']:,} plus the descriptor")
    check(con["used"]["count"] <= con["entries"]["count"]
          and con["used_ge_16"]["count"] <= con["used"]["count"],
          "the conventions are nested: every USED>=16 row is USED, every USED "
          "row is censused",
          f"{con['entries']['count']:,} >= {con['used']['count']:,} >= "
          f"{con['used_ge_16']['count']:,}")
    check(sum(d["rows"] for d in sm["deltas"]) + con["used_ge_16"]["count"]
          == led.row_count,
          "and the three deltas plus the narrowest convention account for "
          "every raw row -- the reconciliation closes on a real archive",
          f"{sum(d['rows'] for d in sm['deltas']):,} dropped + "
          f"{con['used_ge_16']['count']:,} kept = {led.row_count:,}")
    check(sm["slack"]["total"] > 0 and sm["classes"].get("comp8", 0) > 0,
          f"a real archive has {sm['slack']['total']:,} B of slack across "
          f"{sm['classes'].get('comp8', 0):,} comp-8 rows -- the numbers the "
          f"C-8 note is written from")

    print("\n7a. the counting CONVENTIONS, on whatever copies this vault holds")
    ins_led, ins_sm = censused(copies["install"])
    ins = ins_sm["conventions"]
    study_entries, study_used = con["entries"], con["used"]
    ins_entries, ins_used = ins["entries"], ins["used"]
    print(f"    study   entries {study_entries['count']:,} "
          f"(0={study_entries['by_compression']['0']:,}, "
          f"8={study_entries['by_compression']['8']:,})")
    print(f"    install used    {ins_used['count']:,} "
          f"(0={ins_used['by_compression']['0']:,}, "
          f"8={ins_used['by_compression']['8']:,})")

    # THE +12 IS A CONVENTION, NOT A GENERATION -- and this check used to read
    # the historical LITERAL where it meant the live census. While
    # `vault/dat_study` WAS the archive C-8 was measured on the two were equal
    # and the defect was invisible; the 2026-08-27 resync to 38833 reddened it
    # while the convention itself had not moved an inch (entries-comp0 minus
    # used-comp0 is 12 on 38797 AND on 38833, over the same twelve rows). Both
    # sides are measured now, so the claim is generation-independent.
    ent_used = [d for d in sm["deltas"] if d["to"] == "used"][0]
    comp0_gap = (study_entries["by_compression"]["0"]
                 - study_used["by_compression"]["0"])
    check(comp0_gap == 12 and ent_used["by_class"] == {"structural": 12},
          "C-8's comp-0 figure is written '38,621+12' and the +12 IS the "
          "twelve erased structural rows 4..15 that the USED convention "
          "drops -- measured here as entries-comp0 minus used-comp0 on the "
          "copy actually read. That was always a convention, spelled out in "
          "the number itself",
          f"{study_entries['by_compression']['0']:,} - "
          f"{study_used['by_compression']['0']:,} = {comp0_gap}, "
          f"{ent_used['by_class']}")

    # A GUARD THAT WAS POINTED ONE WAY. The old check asserted comp-8
    # convention-invariance on the INSTALL copy while its own message claimed
    # it "on either copy", and bundled it with a `== 15` that is pure archive
    # difference. Split: the invariant is measured on BOTH copies here, and 15
    # is a fact about one pair of archives and lives in 7b with the rest of
    # C-8's arithmetic.
    check(study_entries["by_compression"]["8"]
          == study_used["by_compression"]["8"]
          and ins_entries["by_compression"]["8"]
          == ins_used["by_compression"]["8"],
          "and the comp-8 count does not move BETWEEN conventions on EITHER "
          "copy -- which is what makes a comp-8 disagreement between two "
          "censuses archive difference and never counting",
          f"study {study_entries['by_compression']['8']:,} == "
          f"{study_used['by_compression']['8']:,}, install "
          f"{ins_entries['by_compression']['8']:,} == "
          f"{ins_used['by_compression']['8']:,}")

    # AND THE CONVENTION TERM IS A NAMED POPULATION. `archive_gap +
    # convention_gap == 20` TELESCOPED: both gaps are taken against
    # ins_entries, so their sum is identically study_entries - ins_used, which
    # is exactly what 7b's two exact checks already assert. It could not fail
    # on its own and it was not a second witness to anything. What is NOT a
    # tautology is that the convention half equals the rows the install copy's
    # own entries->used delta drops, by class.
    ins_ent_used = [d for d in ins_sm["deltas"] if d["to"] == "used"][0]
    convention_gap = ins_entries["count"] - ins_used["count"]
    check(convention_gap == ins_ent_used["rows"]
          and ins_ent_used["by_class"] == {"structural": 12, "spare": 1},
          f"and the CONVENTION half of a two-copy disagreement is a named "
          f"population rather than a subtraction: {convention_gap} rows on "
          f"the install copy, which its own entries->used delta names as "
          f"{ins_ent_used['by_class']}",
          f"{convention_gap} == {ins_ent_used['rows']}")

    print("\n7b. C-8's two censuses, each on the archive it was measured on")
    check(ins_used["count"] == C8_ROUTE_C["sum"],
          f"the INSTALL copy under the `used` convention reproduces C-8's "
          f"smaller SUM exactly: {C8_ROUTE_C['sum']:,}",
          f"got {ins_used['count']:,}")
    off_by = abs(ins_used["by_compression"]["8"] - C8_ROUTE_C["comp8"])
    check(off_by == 1
          and ins_used["by_compression"]["0"] + ins_used["by_compression"]["8"]
          == C8_ROUTE_C["sum"],
          f"with the compression split ONE row from C-8's "
          f"({ins_used['by_compression']['0']:,}/"
          f"{ins_used['by_compression']['8']:,} against "
          f"{C8_ROUTE_C['comp0']:,}/{C8_ROUTE_C['comp8']:,}, same total) -- so "
          f"the 16-row comp-8 gap is one row, not sixteen",
          f"off by {off_by}")
    # NO SLACK ON THE VAULTED SHAPE: with one fixed floor a vaulted run would
    # carry the whole reconciliation as headroom, and headroom in a floor is
    # where a deleted section hides.
    LEDGER.floor = FLOOR_VAULT
    check(not ins_sm["anomalies"] and not sm["anomalies"],
          "and neither real archive carries a single anomaly -- every row's "
          "fields agree with its class, which is what makes the counts above "
          "worth quoting")

    # ROUTE E IS A 38797-PINNED MEASUREMENT, so it is read from the copy that
    # was preserved to serve exactly that (`51797ca`: "every 38797-pinned
    # measurement ... RURIK_DAT at it reproduces an old number"). It used to
    # be read off `vault/dat_study`, which is the SERVER'S LIVE reference
    # archive and is resynced when the server's moves -- 38797 -> 38833 on
    # 2026-08-27 -- so a historical correction was being taken off a moving
    # target and reddened the morning of a resync while saying nothing
    # whatever about C-8. Route C never needed this: `client/` is a dated
    # snapshot directory and does not move.
    if not os.path.isfile(c8_study):
        LEDGER.skip("C-8's Route E census and the 20-row closure",
                    "vault/dat_study_38797 is absent from this vault")
        return
    # THE FLOOR RISES WITH THE SUBJECT: three more checks are available when
    # the Route E archive is here, so requiring them is what stops a machine
    # that has it from quietly losing them.
    LEDGER.floor = FLOOR_VAULT_C8
    c8_led, c8_sm = censused(c8_study)
    c8e = c8_sm["conventions"]["entries"]
    print(f"    38797   entries {c8e['count']:,} "
          f"(0={c8e['by_compression']['0']:,}, "
          f"8={c8e['by_compression']['8']:,})")
    check(c8e["count"] == C8_ROUTE_E["sum"]
          and c8e["by_compression"]["0"] == C8_ROUTE_E["comp0"]
          and c8e["by_compression"]["8"] == C8_ROUTE_E["comp8"],
          f"the 38797 STUDY copy under the `entries` convention reproduces "
          f"C-8's larger census exactly: {C8_ROUTE_E['comp0']:,} comp-0, "
          f"{C8_ROUTE_E['comp8']:,} comp-8, sum {C8_ROUTE_E['sum']:,}",
          f"got {c8e['by_compression']}")
    archive_gap = c8e["count"] - ins_entries["count"]
    check(archive_gap + convention_gap == C8_ROUTE_E["sum"] - C8_ROUTE_C["sum"],
          f"and the 20-row disagreement CLOSES: {archive_gap} rows of archive "
          f"difference (the two copies have {c8_led.row_count:,} and "
          f"{ins_led.row_count:,} raw rows) plus {convention_gap} rows of "
          f"convention (entries vs USED on the install copy) = "
          f"{C8_ROUTE_E['sum'] - C8_ROUTE_C['sum']}",
          f"{archive_gap} + {convention_gap}")
    c8_gap = c8e["by_compression"]["8"] - ins_entries["by_compression"]["8"]
    check(c8_gap == 15,
          "and 15 of the 16 comp-8 rows are archive difference, not counting "
          "-- 7a measured the comp-8 count to be convention-invariant on both "
          "copies, so every row of this gap has to be archive",
          f"38797 {c8e['by_compression']['8']:,} - install "
          f"{ins_entries['by_compression']['8']:,} = {c8_gap}")


def guarded(fn, *args):
    """Run a section; turn a crash into a NAMED failing check.

    Without this a defect anywhere raises, main() never reaches its verdict, and
    the run prints no banner, no ledger and no floor shortfall -- which reads as
    a broken test rather than a caught defect.
    """
    try:
        fn(*args)
    except KeyboardInterrupt:
        raise
    except BaseException as exc:                               # noqa: BLE001
        # BaseException, not Exception: `datledger.Refused` subclasses
        # SystemExit, and so does `vaultpath.require_dir`'s failure. With the
        # narrow catch a refusal anywhere kills the whole run silently.
        import traceback
        traceback.print_exc()
        check(False, f"section {fn.__name__} ran to completion "
                     f"({type(exc).__name__}: {exc})")


def main():
    tmp = tempfile.mkdtemp(prefix="rurik-datledger-")
    print(f"synthetic archive: {FILE_SIZE:,} B, {ENTRY_COUNT} rows, MFT at "
          f"0x{MFT_OFF:X}, in {tmp}")
    try:
        for fn in (section_classes, section_slack, section_conventions,
                   section_stamp, section_anomalies, section_cli,
                   section_attribution):
            guarded(fn, tmp)
        guarded(section_vault)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
