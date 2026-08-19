"""Allocate: rows that did not exist, and the file id that names them.

Builds its own archive, so there is no corpus to be missing and no vault to
resolve. The fixture is shaped to carry the three things the real archive has and
`test_datmove.py`'s does not:

  * a MFT whose size is not a block multiple, so it has real growth slack, and
    whose reservation ends at EOF -- the 38833 archives' actual shape;
  * a file-id table with headroom inside its own reservation;
  * an ARMED MAP HEAD -- size 0, flags 259, USED -- beside a genuine USED-clear
    spare, because telling those two apart is the bug this arc found.

EVERYTHING BELOW IS RE-DERIVED FROM THE RAW BYTES. `read_rows`, `read_ids` and
`self_crc_of` open the file and unpack it by hand; they import nothing from
`datalloc`, `datplan` or `archive`. A test that asks the module under test what
it wrote can only discover that it is self-consistent, which is the failure mode
`datwrite`'s own docstring says three defects hid behind.
"""

import binascii
import contextlib
import io
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ENTRY_SIZE  # noqa: E402
import datalloc  # noqa: E402
import datcheck  # noqa: E402
import datmove  # noqa: E402
import datplan  # noqa: E402
import datwrite  # noqa: E402
import gwenc  # noqa: E402
import checks  # noqa: E402

# FLOOR: 98, MEASURED from a green run on 2026-08-15, not guessed. Every section
# builds its own fixture, so there is no corpus to be missing, no vault to
# resolve, and nothing that can legitimately skip.
#
# SABOTAGES, applied one at a time to the modules under test and then reverted.
# Eight were tried and all eight went red. These are the counts OBSERVED, not
# predicted -- a first draft of this comment guessed six numbers and five were
# wrong, so they are re-measured whenever this file changes:
#
#   register the PARTNER in the file-id table, not the head    5 checks red
#   drop the `nextStream` write (write 0)                      4 checks red
#   write REUSED rows at step 2, with the appended ones        3 checks red
#   make the file-id record live AFTER the rows, not before    2 checks red
#   skip the row-2 crc after growing the table                 2 checks red
#   revert free_rows to `size == 0` alone                      2 red, then a
#                                                              crash claiming
#                                                              the armed head
#   place from `free_runs` instead of `classify_runs`          1 check  red
#   skip `Writer.resync` after the table grows                 HARD STOP, 0 red
#
# Four of those readings are worth keeping rather than tidying away.
#
# The two ORDERING sabotages are the reason section 11 exists, and both are real
# defects this file shipped with for an hour. Writing reused rows early publishes
# a USED|FIRST_STREAM head with no id record -- the exact shape the client's
# reconcile frees and memsets -- and, when the head is reused and its partner
# appended, publishes a head whose `nextStream` points past the declared count.
# Section 11 replays every prefix of the write out of the journal and asserts
# neither state exists on disk at any point. Before the fix it reported three
# FAILs against the code that was passing every other check in the file.
#
# The `nextStream` sabotage reddened exactly ONE check in the first version of
# this file, which is a poor showing for the field whose absence makes a head
# nobody can follow. Section 5 now walks the chain three ways -- from raw bytes,
# through `mapchunks.MapIndex`, and against the corpus-wide orphan list.
#
# The `resync` sabotage reddens nothing because it cannot get that far: the guard
# in `fix_mft_self_crc` raises rather than computing a crc over the pre-growth
# extent. Failing closed is the point, so 0 red is the good answer here; section
# 8 is what actually covers it.
#
# The `free_runs` sabotage is the weakest and is worth naming as such: it is
# caught only because the fixture plants a container generation where a best fit
# will reach it. On the real archive the withheld runs are 13 MB and the usable
# ones are small, so the same mistake would be caught by luck.
LEDGER = checks.Ledger("dat alloc", floor=100)
check = checks.adopt(LEDGER)

FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"

BLOCK = 512
NBLOCKS = 28
FILE_SIZE = NBLOCKS * BLOCK          # 14336; the MFT's reservation ends here
MFT_BLOCK = 26
MFT_OFF = MFT_BLOCK * BLOCK
ENTRY_COUNT = 23
MFT_SIZE = ENTRY_COUNT * ENTRY_SIZE  # 552 -- deliberately not a block multiple
MFT_SLACK = -MFT_SIZE % BLOCK        # 472 = 19 rows
SLACK_BYTE = 0xCC

ROW_HEADER, ROW_IDTABLE, ROW_SELF = 1, 2, 3
ROW_A, ROW_B, ROW_C, ROW_D = 16, 17, 18, 19
ROW_PARTNER = 20        # flags 1: USED, not FIRST_STREAM -- correctly unnamed
ROW_ARMED = 21          # flags 259, size 0: an ARMED HEAD, and NOT a free slot
ROW_SPARE = 22          # flags 0, size 0: the only genuinely claimable row

# (offset, size, extraBytes, flags, nextStream)
ROWS = {
    ROW_HEADER:  (0 * BLOCK, 32, 0, 3, 0),
    ROW_IDTABLE: (1 * BLOCK, 40, 0, 3, 0),
    ROW_SELF:    (MFT_OFF, MFT_SIZE, 0, 3, 0),
    ROW_A:       (2 * BLOCK, 1000, 0, 3, 0),
    ROW_B:       (4 * BLOCK, 300, 0, 3, 0),
    ROW_C:       (6 * BLOCK, 512, 0, 3, 0),
    ROW_D:       (9 * BLOCK, 100, 0, 3, 0),
    ROW_PARTNER: (16 * BLOCK, 200, 0, 1, 0),
    ROW_ARMED:   (25 * BLOCK, 0, 0, 259, ROW_PARTNER),
    ROW_SPARE:   (0, 0, 0, 0, 0),
}
PAYLOAD_ROWS = (ROW_IDTABLE, ROW_A, ROW_B, ROW_C, ROW_D, ROW_PARTNER)

# Every USED|FIRST row >= 16 must be named or datcheck rule 7 refuses -- and the
# client deletes it. ROW_PARTNER is flags 1 and is correctly absent.
ID_PAIRS = ((0x1000, ROW_A), (0x1001, ROW_B), (0x1002, ROW_C),
            (0x1003, ROW_D), (0x2000, ROW_ARMED))

CONTAINER_BLOCK = 17
LARGEST_USABLE = 6 * BLOCK           # blocks 10-15; 17-25 is withheld


def pattern(seed, n):
    return bytes(1 + ((i * 37 + seed * 101) % 255) for i in range(n))


def self_crc_of(mft, count):
    acc = binascii.crc32(bytes(mft[0x00:ROW_SELF * ENTRY_SIZE]))
    return binascii.crc32(
        bytes(mft[(ROW_SELF + 1) * ENTRY_SIZE:count * ENTRY_SIZE]), acc)


def build_archive(path):
    buf = bytearray(bytes([SLACK_BYTE]) * FILE_SIZE)
    payloads = {}
    for row in PAYLOAD_ROWS:
        off, size, _e, _f, _n = ROWS[row]
        data = (b"".join(struct.pack("<II", i, r) for i, r in ID_PAIRS)
                if row == ROW_IDTABLE else pattern(row, size))
        buf[off:off + size] = data
        payloads[row] = data

    # The withheld run: datplan's container_signature names an MFT magic at a
    # block boundary. Planted so the placement refusals are about the rule.
    struct.pack_into("<I", buf, CONTAINER_BLOCK * BLOCK + 0x0C, ENTRY_COUNT)
    buf[CONTAINER_BLOCK * BLOCK:CONTAINER_BLOCK * BLOCK + 4] = MFT_MAGIC

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
    for row, (off, size, extra, flags, nxt) in ROWS.items():
        crc = 0 if row in (ROW_HEADER, ROW_SELF) else binascii.crc32(
            bytes(buf[off:off + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         off, size, extra, flags, nxt, crc)
    struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + datwrite.ENTRY_CRC,
                     self_crc_of(mft, ENTRY_COUNT))
    buf[MFT_OFF:MFT_OFF + MFT_SIZE] = mft

    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return payloads


def fresh(tmp, name):
    path = os.path.join(tmp, name)
    return path, build_archive(path)


def blob(path):
    with open(path, "rb") as fh:
        return fh.read()


def spill(tmp, name, data):
    path = os.path.join(tmp, name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


# -- the independent readers. Nothing below imports from datalloc. -----------

def read_rows(path):
    """{row: (offset, size, extra, flags, nextStream, crc)} straight from bytes."""
    raw = blob(path)
    mft_off = int.from_bytes(raw[0x10:0x18], "little")
    mft_size = int.from_bytes(raw[0x18:0x1C], "little")
    mft = raw[mft_off:mft_off + mft_size]
    count = int.from_bytes(mft[0x0C:0x10], "little")
    out = {}
    for i in range(1, count):
        out[i] = struct.unpack_from("<QIHHII", mft, i * ENTRY_SIZE)
    return out


def read_counts(path):
    """(descriptor count, header mft_size, row 3's size field, mft_offset)."""
    raw = blob(path)
    mft_off = int.from_bytes(raw[0x10:0x18], "little")
    hdr_size = int.from_bytes(raw[0x18:0x1C], "little")
    count = int.from_bytes(raw[mft_off + 0x0C:mft_off + 0x10], "little")
    r3 = mft_off + ROW_SELF * ENTRY_SIZE
    return count, hdr_size, int.from_bytes(raw[r3 + 8:r3 + 12], "little"), mft_off


def read_ids(path):
    """[(file_id, row)] from the table row 2 declares. Raw, as the client sees."""
    rows = read_rows(path)
    off, size = rows[ROW_IDTABLE][0], rows[ROW_IDTABLE][1]
    raw = blob(path)[off:off + size]
    return [struct.unpack_from("<II", raw, i * 8) for i in range(len(raw) // 8)]


def payload_of(path, row):
    rows = read_rows(path)
    off, size = rows[row][0], rows[row][1]
    return blob(path)[off:off + size]


def walk_chain(path, start):
    """The loader's own walk: follow +0x10 from `start`, refusing to cycle.

    Spelled out from the bytes rather than borrowed from `mapchunks`, so that the
    two are independent witnesses to the same link.
    """
    rows = read_rows(path)
    out, seen, cur = [], {start}, start
    while True:
        nxt = rows[cur][4]
        if nxt == 0 or nxt in seen or nxt not in rows:
            return out
        out.append(nxt)
        seen.add(nxt)
        cur = nxt


def mft_self_ok(path):
    raw = blob(path)
    mft_off = int.from_bytes(raw[0x10:0x18], "little")
    mft_size = int.from_bytes(raw[0x18:0x1C], "little")
    mft = raw[mft_off:mft_off + mft_size]
    count = int.from_bytes(mft[0x0C:0x10], "little")
    stored = int.from_bytes(
        mft[ROW_SELF * ENTRY_SIZE + 0x14:ROW_SELF * ENTRY_SIZE + 0x18], "little")
    return stored == self_crc_of(mft, count)


def map_streams(partner, head=b""):
    return [datalloc.Stream(head, datalloc.MAP_HEAD_FLAGS_U16),
            datalloc.Stream(partner, datalloc.MAP_PARTNER_FLAGS_U16)]


def refusal(fn, *a, **kw):
    """Run and return the Refused message, or None if it did not refuse."""
    try:
        with quiet():
            fn(*a, **kw)
    except datalloc.Refused as exc:
        return str(exc)
    return None


# --------------------------------------------------------------- 1. fixture

def section_fixture(tmp):
    print("\n1. the fixture is the archive we think it is")
    path, _ = fresh(tmp, "fixture.dat")
    with Archive(path) as ar:
        check(ar.block_size == BLOCK and ar.entry_count == ENTRY_COUNT,
              "opens with the declared block size and entry count",
              f"block {ar.block_size}, {ar.entry_count} entries")
        check(datalloc.mft_slack(ar) == MFT_SLACK,
              f"MFT slack is {MFT_SLACK} B = {MFT_SLACK // ENTRY_SIZE} rows",
              f"mft_size {ar.mft_size}, {ar.mft_size % BLOCK} into its last block")
        check(ar.mft_offset + datplan.blocks_for(ar.mft_size, BLOCK) * BLOCK
              == FILE_SIZE,
              "the MFT's reservation ends at EOF, as it does on 38833",
              f"0x{FILE_SIZE:X}")
        id_off, spare = datalloc.id_table_slack(ar)
        check(id_off == BLOCK + 8 * len(ID_PAIRS) and spare == BLOCK - 40,
              "the file-id table has headroom inside its own reservation",
              f"append at 0x{id_off:X}, {spare} B = {spare // 8} pairs")
        usable, excluded = datplan.classify_runs(ar)
        largest = max(n for _s, n in usable) * BLOCK
        check(largest == LARGEST_USABLE and len(excluded) == 1,
              "one run is withheld as a container generation",
              f"largest usable {largest} B, {len(excluded)} withheld")
    check(datcheck_clear(path), "datcheck --preflight is 10 of 10 on the fixture")


def datcheck_clear(path):
    with quiet():
        got, _meta = datcheck.preflight(path)
    bad = [c.name for c in got if not c.ok]
    if bad:
        print(f"      preflight failures: {bad}")
    return len(got) == 10 and not bad


# ------------------------------------------------- 2. the armed-head defect

def section_armed_head(tmp):
    print("\n2. an armed map head is not a free slot")
    path, _ = fresh(tmp, "armed.dat")
    rows = read_rows(path)
    off, size, _e, flags, nxt, _c = rows[ROW_ARMED]
    check(size == 0 and flags == 259 and flags & 1,
          "the fixture's armed head is size 0 AND USED, read from raw bytes",
          f"row {ROW_ARMED}: size {size}, flags 0x{flags:04X}")
    check(nxt == ROW_PARTNER,
          "and it still points at the partner holding the geometry",
          f"nextStream {nxt}")

    with Archive(path) as ar:
        free = datplan.free_rows(ar)
    check(free == [ROW_SPARE],
          "free_rows offers ONLY the USED-clear spare",
          f"{free}")
    check(ROW_ARMED not in free,
          "and never the armed head -- the dat_c2 defect, in a fixture",
          f"before the 2026-08-15 fix this returned [{ROW_ARMED}, {ROW_SPARE}]")

    # The old rule, spelled out here so the regression is stated and not implied.
    old_rule = sorted(r for r, v in rows.items()
                      if v[1] == 0 and r >= 16)
    check(old_rule == [ROW_ARMED, ROW_SPARE],
          "the size==0 rule alone would have offered the head FIRST",
          f"{old_rule}; plan_insert takes erased[0]")


# ------------------------------------------------------------- 3. the plan

def section_plan(tmp):
    print("\n3. what a map allocation plans")
    path, _ = fresh(tmp, "plan.dat")
    partner = pattern(99, 1500)
    with Archive(path) as ar:
        with quiet():
            plan = datalloc.plan_alloc(ar, map_streams(partner), 0x3000)
    head, part = plan.rows
    check(len(plan.rows) == 2, "two rows for a map, not one")
    check(head.index == ROW_SPARE and part.index == ENTRY_COUNT,
          "the spare is claimed first, then the table grows by one",
          f"rows {head.index} and {part.index}")
    check(plan.mft_grow_rows == 1,
          "only ONE row of growth, because the spare cost none",
          f"grow {plan.mft_grow_rows}")
    check(head.flags == 259 and part.flags == 1,
          "head carries FIRST_STREAM, partner does not",
          f"0x{head.flags:04X} / 0x{part.flags:04X}")
    check(head.next_stream == part.index and part.next_stream == 0,
          "the chain is head -> partner -> 0",
          f"{head.next_stream} then {part.next_stream}")
    check(head.size == 0 and head.reservation == 0,
          "a zero-length head takes no free space at all")
    check(part.reservation == 1536 and part.offset % BLOCK == 0,
          "the partner gets whole aligned blocks",
          f"0x{part.offset:X} +{part.reservation}")
    check(part.crc == binascii.crc32(partner),
          "and its crc is over the payload we handed in")
    check(plan.head is head, "the id will name the head")

    # Best fit, consuming: two streams must never be handed the same run.
    with Archive(path) as ar:
        with quiet():
            two = datalloc.plan_alloc(
                ar, [datalloc.Stream(pattern(1, 600), 259),
                     datalloc.Stream(pattern(2, 600), 1)], 0x3001)
    a, b = two.rows
    check(a.offset != b.offset,
          "two payloads in one allocation get different addresses",
          f"0x{a.offset:X} and 0x{b.offset:X}")
    check(not (a.offset < b.offset + b.reservation
               and b.offset < a.offset + a.reservation),
          "and their reservations do not overlap")


# --------------------------------------------------------- 4. the refusals

def section_refusals(tmp):
    print("\n4. every way this says no")
    path, _ = fresh(tmp, "refuse.dat")
    good = map_streams(pattern(7, 800))
    with Archive(path) as ar:
        def why(streams, fid):
            return refusal(datalloc.plan_alloc, ar, streams, fid)

        m = why(good, None)
        check(m and "reconcile" in m and "vanishes" in m,
              "no file id: refused, naming the reconcile that deletes the row")
        m = why(good, 0x1000)
        check(m and "already binds" in m and str(ROW_A) in m,
              "an id already in the table: refused, naming the row it binds")
        check(why(good, 0x80000000), "bit 31 set: refused")
        check(why(good, 0), "id zero: refused")
        check(why([], 0x3000), "no streams at all: refused")

        m = why([datalloc.Stream(b"x", 1), datalloc.Stream(b"y", 1)], 0x3000)
        check(m and "FIRST_STREAM" in m,
              "a head without FIRST_STREAM: refused")
        m = why([datalloc.Stream(b"x", 259), datalloc.Stream(b"y", 259)], 0x3000)
        check(m and "Only the head" in m,
              "a second row claiming FIRST_STREAM: refused")
        m = why([datalloc.Stream(b"x", 259), datalloc.Stream(b"y", 0)], 0x3000)
        check(m and "spare stack" in m,
              "a row with USED clear: refused, naming NewEntry")
        m = why([datalloc.Stream(b"xy", 259, extra_bytes=9)], 0x3000)
        check(m and "extraBytes" in m,
              "extraBytes greater than size: refused, ArenaNet's own assert")
        m = why([datalloc.Stream(b"abcdef", 259, extra_bytes=4)], 0x3000)
        check(m and "only 0 and 8" in m,
              "an extraBytes the corpus has never held: refused",
              "the histogram is {0, 8} over 177,740 rows")
        m = why([datalloc.Stream(b"abcdefgh", 259, extra_bytes=8)], 0x3000)
        check(m and "does not DECODE" in m,
              "extraBytes 8 over a plainly stored payload: refused",
              "the gate decodes rather than matching a two-byte marker")
        # CORRECTED 2026-08-18. This used to assert that `b"ab\x01\x02efgh"` is
        # ACCEPTED "because it carries the marker" -- a test pinning a defect as
        # correct. Those eight bytes decode as nothing, so accepting them mints a
        # green, unreadable compression-8 row from the CREATION path, which is the
        # one A8 will use. The marker was never evidence of anything; it was a
        # correlate that happens to hold on large payloads.
        m = why([datalloc.Stream(b"ab\x01\x02efgh", 259, extra_bytes=8)], 0x3000)
        check(m and "does not DECODE" in m,
              "AND a payload that merely CARRIES the marker without decoding is "
              "refused too -- the marker is a correlate, not evidence")
        real = gwenc.encode(b"tiny")
        check(not datwrite.looks_compressed(b"ab\x01\x02efgh")
              and datwrite.looks_compressed(real),
              "CONTROL, both directions: the marker-carrying fake does not "
              "decode, and a REAL gwenc stream too small to carry the marker "
              "does -- the case the old gate wrongly refused",
              f"gwenc.encode(b'tiny') is {len(real)} B, data[2]="
              f"0x{real[2]:02X}")
        check(refusal(datalloc.plan_alloc, ar,
                      [datalloc.Stream(real, 259, extra_bytes=8)],
                      0x3000) is None,
              "...and that real stream is ACCEPTED as extraBytes 8")

        # Growth past the MFT's own last block.
        many = [datalloc.Stream(b"", 259)] + [
            datalloc.Stream(b"", 1) for _ in range(MFT_SLACK // ENTRY_SIZE + 1)]
        m = why(many, 0x3000)
        check(m and "last 512-byte block" in m,
              f"more rows than the {MFT_SLACK // ENTRY_SIZE} of slack: refused",
              f"asked for {len(many)}")
        check(m and "truncation the format cannot express" in m,
              "and it says why extending the file is not the fallback")

        # Nothing large enough to place.
        m = why([datalloc.Stream(pattern(3, LARGEST_USABLE + 1), 259)], 0x3000)
        check(m and "nothing fits" in m and "withheld whole" in m,
              "a payload bigger than the largest usable run: refused",
              f"largest usable {LARGEST_USABLE} B")
        check(refusal(datalloc.plan_alloc, ar,
                      [datalloc.Stream(pattern(3, 4 * BLOCK), 259)], 0x3000)
              is None,
              "but one that fits is not refused -- the rule is size, not fear")

    # A full file-id table.
    full, _ = fresh(tmp, "fullids.dat")
    with open(full, "r+b") as fh:                 # row 2 size -> its whole block
        rows = read_rows(full)
        fh.seek(MFT_OFF + ROW_IDTABLE * ENTRY_SIZE + 8)
        fh.write(struct.pack("<I", BLOCK))
    with Archive(full) as ar:
        m = refusal(datalloc.plan_alloc, ar, good, 0x3000)
    check(m and "no room for another pair" in m,
          "a file-id table with no spare: refused, not silently relocated")

    # And the write refuses without --confirm.
    m = refusal(datalloc.alloc, path, good, 0x3000,
                os.path.join(tmp, "j.json"), confirm=False)
    check(m and "--confirm" in m, "alloc without --confirm: refused")

    # The journal, which is the one refusal about a SECOND run rather than this
    # one. datwrite defaults this name and datmove keys it on the row; both
    # would let run two truncate run one's only way back.
    class A:
        journal = None
    m = refusal(datalloc._journal_path, A())
    check(m and "needs --journal" in m,
          "--alloc with no --journal: refused, not defaulted")
    A.journal = spill(tmp, "taken.journal.json", b"{}")
    m = refusal(datalloc._journal_path, A())
    check(m and "already exists" in m and "restored none of them" in m,
          "and a journal that already exists is never written over",
          "the second run's revert would report success having undone nothing")
    A.journal = os.path.join(tmp, "unused.journal.json")
    check(refusal(datalloc._journal_path, A()) is None,
          "a fresh journal path is accepted")


# -------------------------------------------------------------- 5. the write

def section_write(tmp):
    print("\n5. the bytes it actually puts down")
    path, _ = fresh(tmp, "write.dat")
    before = blob(path)
    partner = pattern(11, 2000)
    journal = os.path.join(tmp, "write.journal.json")
    with quiet():
        plan = datalloc.alloc(path, map_streams(partner), 0x3000, journal,
                              confirm=True)

    rows = read_rows(path)
    hi, pi = plan.head.index, plan.rows[1].index
    check(hi in rows and pi in rows, "both rows are readable from the raw MFT",
          f"rows {hi} and {pi}")
    check(rows[hi][3] == 259 and rows[hi][1] == 0,
          "the head is a zero-length map head", f"flags 0x{rows[hi][3]:04X}")
    check(rows[hi][4] == pi, "and it links to the partner", f"nextStream {pi}")
    check(rows[pi][3] == 1 and rows[pi][4] == 0,
          "the partner is USED, not FIRST_STREAM, and ends the chain")
    check(payload_of(path, pi) == partner,
          "the partner's bytes are on disk, exactly as handed in",
          f"{len(partner)} B")
    check(rows[pi][5] == binascii.crc32(partner),
          "its entry crc is over those bytes")
    check(rows[pi][0] % BLOCK == 0, "its offset is block aligned",
          f"0x{rows[pi][0]:X}")

    count, hdr_size, r3_size, _off = read_counts(path)
    check(count == ENTRY_COUNT + plan.mft_grow_rows,
          "the descriptor's entry count grew", f"{ENTRY_COUNT} -> {count}")
    check(hdr_size == count * ENTRY_SIZE,
          "the header's MFT size agrees with the count", f"{hdr_size}")
    check(r3_size == hdr_size,
          "and row 3 restates the same number -- datcheck rule 9(d)")

    ids = read_ids(path)
    check((0x3000, hi) in ids, "the file id names the HEAD", f"row {hi}")
    check(not any(i == 0x3000 and r == pi for i, r in ids),
          "and never the partner")
    check(len(ids) == len(ID_PAIRS) + 1, "exactly one pair was appended",
          f"{len(ID_PAIRS)} -> {len(ids)}")
    tbl_off, tbl_size = rows[ROW_IDTABLE][0], rows[ROW_IDTABLE][1]
    check(tbl_size == 8 * len(ids), "row 2's size field grew with it")
    check(rows[ROW_IDTABLE][5]
          == binascii.crc32(blob(path)[tbl_off:tbl_off + tbl_size]),
          "and row 2's crc covers the grown table")

    # The chain, walked three ways. One check on `nextStream` is not enough for
    # the field whose absence produces a head nobody can follow: MEASURED, a
    # sabotage that wrote 0 there reddened exactly one check until these landed.
    check(walk_chain(path, hi) == [pi],
          "an independent Floyd walk from raw bytes reaches the partner and stops",
          f"{walk_chain(path, hi)}")
    with Archive(path) as ar:
        import mapchunks
        mi = mapchunks.MapIndex(ar)
        head_entry = ar.row(hi)
        check(mapchunks.is_map_head(head_entry),
              "mapchunks agrees the head is a map head",
              f"alloc_flags {mapchunks.alloc_flags(head_entry)}, "
              f"stream {mapchunks.alloc_stream(head_entry)}")
        partner = mi.partner(head_entry)
        check(partner is not None and partner.index == pi,
              "and MapIndex -- a module that knows nothing of datalloc -- "
              "resolves the pair")
        check(head_entry not in mi.orphans,
              "the new head is not an orphan in the corpus-wide index",
              f"{len(mi.orphans)} orphan(s) in the whole archive")

    check(mft_self_ok(path),
          "the MFT self-crc is right FOR THE GROWN TABLE",
          "the stale-snapshot bug would land here")
    with quiet():
        bad_rows = datwrite.check_rows(path, [ROW_IDTABLE, pi])
    check(bad_rows == 0,
          "the entry crcs of the grown table and the new payload both hold",
          f"{bad_rows} bad")
    check(len(blob(path)) == len(before),
          "the file did not change length", f"{len(before)} B")
    check(datcheck_clear(path),
          "datcheck --preflight is 10 of 10 after the allocation")
    with quiet():
        bad_crc = datwrite.verify(path)
    check(bad_crc == 0, "datwrite --verify: both crc rules hold", f"{bad_crc} bad")
    with Archive(path) as ar:
        check(datmove.overlaps(ar) == [], "no two rows share storage")


# ------------------------------------------------------------- 6. the revert

def section_revert(tmp):
    print("\n6. and all of it comes back")
    path, _ = fresh(tmp, "revert.dat")
    before = blob(path)
    journal = os.path.join(tmp, "revert.journal.json")
    with quiet():
        datalloc.alloc(path, map_streams(pattern(13, 900)), 0x3000, journal,
                       confirm=True)
    check(blob(path) != before, "the archive did change")
    with quiet():
        datwrite.revert(journal)
    check(blob(path) == before,
          "revert restores the archive BYTE FOR BYTE",
          f"{len(before)} B compared")
    check(datcheck_clear(path), "and it is clear again afterwards")


# ---------------------------------------------- 7. an interrupted allocation

def section_interrupted(tmp):
    print("\n7. an interrupted allocation can still be undone")
    path, _ = fresh(tmp, "torn.dat")
    before = blob(path)
    journal = os.path.join(tmp, "torn.journal.json")

    # Bump the descriptor count WITHOUT the header size: the exact state the two
    # unavoidable 4-byte writes pass through, and the one Archive() refuses.
    w = datwrite.Writer(path, journal)
    try:
        with quiet():
            w.put(w.ar.mft_offset + datalloc.MFT_HDR_COUNT,
                  struct.pack("<I", ENTRY_COUNT + 1), "count only, torn")
    finally:
        w.close()

    opened = True
    try:
        Archive(path).close()
    except ValueError:
        opened = False
    check(not opened,
          "Archive() refuses the torn archive -- entry_count * 24 != mft_size",
          "archive.py:320")

    check(datwrite.mft_offset_of(path) == MFT_OFF,
          "but mft_offset_of reads the header alone and still answers",
          f"0x{MFT_OFF:X}")
    with quiet():
        rc = datwrite.revert(journal)
    check(rc == 0 and blob(path) == before,
          "so --revert works in exactly the state it exists for")
    check(datcheck_clear(path), "and the archive is clear again")


# ------------------------------------------------ 8. the stale-snapshot guard

def section_stale_guard(tmp):
    print("\n8. a stale Writer refuses rather than writing a wrong crc")
    path, _ = fresh(tmp, "stale.dat")
    journal = os.path.join(tmp, "stale.journal.json")
    w = datwrite.Writer(path, journal)
    raised = None
    try:
        with quiet():
            # Grow the table behind the Writer's back, as an allocate does.
            w.put(w.ar.mft_offset + datalloc.MFT_HDR_COUNT,
                  struct.pack("<I", ENTRY_COUNT + 1), "count")
            w.put(datalloc.HDR_MFT_SIZE,
                  struct.pack("<I", MFT_SIZE + ENTRY_SIZE), "header size")
            try:
                w.fix_mft_self_crc()
            except SystemExit as exc:
                raised = str(exc)
    finally:
        w.close()
    check(raised is not None,
          "fix_mft_self_crc REFUSES when the table grew under it")
    check(raised and "stale view" in raised and "resync" in raised,
          "and the message names the fix", (raised or "").splitlines()[0][:60])

    # With the resync it computes the right thing.
    path2, _ = fresh(tmp, "resync.dat")
    w = datwrite.Writer(path2, os.path.join(tmp, "resync.journal.json"))
    try:
        with quiet():
            w.put(w.ar.mft_offset + ENTRY_COUNT * ENTRY_SIZE,
                  struct.pack("<QIHHII", 0, 0, 0, 0, 0, 0), "the new row")
            w.put(w.ar.mft_offset + datalloc.MFT_HDR_COUNT,
                  struct.pack("<I", ENTRY_COUNT + 1), "count")
            w.put(datalloc.HDR_MFT_SIZE,
                  struct.pack("<I", MFT_SIZE + ENTRY_SIZE), "header size")
            w.put(w.ar.mft_offset + ROW_SELF * ENTRY_SIZE + 8,
                  struct.pack("<I", MFT_SIZE + ENTRY_SIZE), "row 3 size")
            w.resync("grown")
            w.fix_mft_self_crc()
    finally:
        w.close()
    check(mft_self_ok(path2),
          "after resync the self-crc covers the GROWN table",
          "re-derived from the raw bytes")


# ------------------------------------------------------------- 9. reuse only

def section_reuse(tmp):
    print("\n9. claiming a spare costs no slack")
    path, _ = fresh(tmp, "reuse.dat")
    journal = os.path.join(tmp, "reuse.journal.json")
    with quiet():
        plan = datalloc.alloc(path, [datalloc.Stream(pattern(5, 700), 259)],
                              0x4000, journal, confirm=True)
    check(plan.rows[0].index == ROW_SPARE,
          "a single-stream file takes the USED-clear spare", f"row {ROW_SPARE}")
    check(plan.mft_grow_rows == 0, "and the table does not grow at all")
    count, hdr_size, _r3, _o = read_counts(path)
    check(count == ENTRY_COUNT and hdr_size == MFT_SIZE,
          "the descriptor count and header size are untouched",
          f"{count} entries, {hdr_size} B")
    rows = read_rows(path)
    check(rows[ROW_SPARE][3] == 259 and rows[ROW_SPARE][1] == 700,
          "the claimed row is now USED|FIRST and holds the payload")
    check((0x4000, ROW_SPARE) in read_ids(path), "and the id names it")
    check(mft_self_ok(path) and datcheck_clear(path),
          "self-crc right, preflight 10 of 10")
    with quiet():
        datwrite.revert(journal)
    check(datcheck_clear(path), "and this path reverts clean too")


# ------------------------------------------------------- 10. the next free id

def section_next_id(tmp):
    print("\n10. choosing an id nothing binds")
    path, _ = fresh(tmp, "ids.dat")
    with Archive(path) as ar:
        nxt = datalloc.next_free_file_id(ar)
        low = datalloc.next_free_file_id(ar, start=0x1000)
    taken = {i for i, _r in ID_PAIRS}
    check(nxt not in taken and nxt == max(taken) + 1,
          "the default is one past the highest id present", f"0x{nxt:X}")
    check(low == 0x1004,
          "and from a start it walks up past the ones that are taken",
          f"0x{low:X}")


# ----------------------------------------------- 11. the order, step by step

def section_order(tmp):
    """Replay alloc()'s writes one at a time and check EVERY prefix.

    The property is one sentence and it is the reason the order was rewritten:
    no prefix may leave a USED|FIRST_STREAM row at index >= 16 that the file-id
    table does not name. That is the state the client's reconcile DELETES --
    it frees the extent and memsets the row -- so it must never exist on disk,
    not even for one fsync.
    """
    print("\n11. no prefix of the write publishes an unnamed head")
    path, _ = fresh(tmp, "order.dat")
    journal = os.path.join(tmp, "order.journal.json")
    with quiet():
        # head REUSES the spare, partner is APPENDED -- the mix that broke it.
        datalloc.alloc(path, map_streams(pattern(21, 700)), 0x3000, journal,
                       confirm=True)
    with open(journal) as fh:
        edits = json.load(fh)["edits"]
    check(len(edits) >= 7, f"the journal recorded {len(edits)} ranges")

    base = blob(path)
    # Rebuild the archive at every prefix by undoing the edits after it.
    worst_orphan, worst_dangling, steps = None, 0, 0
    scratch = os.path.join(tmp, "prefix.dat")
    for k in range(len(edits) + 1):
        buf = bytearray(base)
        for ed in reversed(edits[k:]):
            off = ed["offset"]
            buf[off:off + ed["length"]] = binascii.unhexlify(ed["before"])
        with open(scratch, "wb") as fh:
            fh.write(bytes(buf))
        try:
            rows = read_rows(scratch)
            ids = {r for _i, r in read_ids(scratch)}
        except Exception:
            continue                 # the torn-count window; section 7 owns it
        steps += 1
        for idx, v in rows.items():
            if idx < 16:
                continue
            first = (v[3] & 3) == 3
            if first and idx not in ids:
                worst_orphan = (k, idx)
        worst_dangling += sum(1 for r in ids
                              if r in rows and not rows[r][3] & 1)
    check(steps >= len(edits) - 1,
          f"{steps} of {len(edits) + 1} prefixes were openable",
          "the unopenable ones are the two-write count window")
    check(worst_orphan is None,
          "NO prefix leaves a USED|FIRST row that no file-id record names",
          "the state the reconcile frees and memsets")
    check(worst_dangling > 0,
          "a dangling record DOES appear, which is the trade taken on purpose",
          f"{worst_dangling} prefix-row(s); the client drops a name, "
          f"it does not free bytes")

    # And the chain is never published pointing past the declared count.
    bad_link = None
    for k in range(len(edits) + 1):
        buf = bytearray(base)
        for ed in reversed(edits[k:]):
            off = ed["offset"]
            buf[off:off + ed["length"]] = binascii.unhexlify(ed["before"])
        with open(scratch, "wb") as fh:
            fh.write(bytes(buf))
        try:
            rows = read_rows(scratch)
        except Exception:
            continue
        cnt = max(rows) + 1
        for idx, v in rows.items():
            if idx >= 16 and v[3] & 1 and v[4] and v[4] >= cnt:
                bad_link = (k, idx, v[4])
    check(bad_link is None,
          "and no prefix publishes a nextStream past the declared count",
          "the loader asserts `curr->alloc.nextStream < count` at 0x93f0b8")


# ------------------------------------------------------- 12. the CLI surface

def section_cli(tmp):
    print("\n12. the command line")
    path, _ = fresh(tmp, "cli.dat")
    data = spill(tmp, "part.bin", pattern(31, 900))

    class A:
        pass
    a = A()
    a.map, a.data, a.head, a.stream = True, data, None, None
    got = datalloc._streams_from_args(a)
    check(len(got) == 2 and got[0].flags == 259 and got[1].flags == 1,
          "--map builds a head/partner pair")

    # An absolute Windows path contains a colon and used to die here.
    a.map, a.data, a.stream = False, None, [data]
    got = datalloc._streams_from_args(a)
    check(len(got) == 1 and got[0].data == pattern(31, 900),
          "--stream reads an ABSOLUTE Windows path",
          f"{data} -- rpartition(':') split the drive letter")
    a.stream = [data + ":0x0103"]
    got = datalloc._streams_from_args(a)
    check(got[0].flags == 0x0103, "and FILE:FLAGS still overrides the flags")

    # --next-id must never hand back an id plan_alloc refuses.
    with Archive(path) as ar:
        nxt = datalloc.next_free_file_id(ar)
        check(not nxt & 0x80000000,
              "--next-id never returns a bit-31 id", f"0x{nxt:X}")
        check(refusal(datalloc.plan_alloc, ar, map_streams(b"z"), nxt) is None,
              "and the id it returns is one plan_alloc accepts")

    # A renamed id still speaks for its plain form.
    ren, _ = fresh(tmp, "renamed.dat")
    with open(ren, "r+b") as fh:
        fh.seek(BLOCK)
        fh.write(struct.pack("<II", 0x80001000 | 0x2000, ROW_A))
    with Archive(ren) as ar:
        n2 = datalloc.next_free_file_id(ar)
        check(not n2 & 0x80000000,
              "a bit-31 id in the table does not drag --next-id above bit 31",
              f"0x{n2:X}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        section_fixture(tmp)
        section_armed_head(tmp)
        section_plan(tmp)
        section_refusals(tmp)
        section_write(tmp)
        section_revert(tmp)
        section_interrupted(tmp)
        section_stale_guard(tmp)
        section_reuse(tmp)
        section_next_id(tmp)
        section_order(tmp)
        section_cli(tmp)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
