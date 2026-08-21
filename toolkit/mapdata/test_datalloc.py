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
# `file_id_table` is the ONE thing this file borrows from `archive` beyond the
# opener: section 13 has to ask "can the CLIENT address the new id", and that is
# `raw=True` specifically -- the convenience default registers a second, masked
# spelling of every bit-31 id and has answered the wrong question three times
# (archive.py's own docstring lists them). The independent readers below still
# unpack the table by hand, so both witnesses are present.
from archive import Archive, ENTRY_SIZE, file_id_table  # noqa: E402
import datalloc  # noqa: E402
import datcheck  # noqa: E402
import datmove  # noqa: E402
import datplan  # noqa: E402
import datwrite  # noqa: E402
import gwdat  # noqa: E402
import gwenc  # noqa: E402
import checks  # noqa: E402

# FLOOR: 203, MEASURED from a green run on 2026-08-20, not guessed. Every section
# builds its own fixture, so there is no corpus to be missing, no vault to
# resolve, and nothing that can legitimately skip. Per section, counted from the
# log rather than predicted: {1: 6, 2: 5, 3: 11, 4: 23, 5: 25, 6: 3, 7: 4, 8: 3,
# 9: 7, 10: 2, 11: 5, 12: 23, 13: 29, 14: 31, 15: 26}. Was 177 before section
# 15's reserve (WORLDMAPS-W5).
#
# THIS NUMBER HAS BEEN WRONG IN THIS COMMENT BEFORE. It read "FLOOR: 98" while
# the `floor=` below said 100, from 2026-08-15 until 2026-08-19 -- a stale figure
# in the one place a reader checks first, in the file whose whole subject is
# writers that agree with themselves. Re-measure both together or neither. (It
# was wrong again on 2026-08-19, from the other side: `TESTS.md` was left saying
# 98 while this comment and `floor=` both said 142.)
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
#
# FOUR MORE, run 2026-08-19 against sections 12 and 13 -- the CLI's third field
# and the end-to-end compressed allocation. Same method: monkeypatched in memory,
# suite run, reds counted, patch reverted. Nothing on disk was edited.
#
#   `datwrite.looks_compressed` always True (the gate stops gating)  11 red
#   the plan's extraBytes zeroed between plan_alloc and the write     5 red
#   the CLI stops refusing an EXTRA the corpus never held             3 red
#   the pre-2026-08-19 splitter: FILE:FLAGS only, no EXTRA            1 red,
#                                                                    then a
#                                                                    hard stop
#
# The splitter one is the reading worth keeping. Restored, it hands `_read` the
# path with `:1` still glued to the end and dies on FileNotFoundError, so the
# checks BEHIND that line never run -- which is why section 12 now checks
# `_split_stream_spec` on its own, before anything opens a file. That check is
# the one red; the hard stop three lines later is loud but nameless, and a test
# that only crashes has told you the machine is unhappy rather than what broke.
#
# SEVEN MORE, run 2026-08-20 against section 14 -- the fidelity gate. Same
# method: monkeypatched in memory, whole suite run, `[FAIL]` lines counted, patch
# reverted. Nothing on disk was edited.
#
#   `datwrite.declaration_fault` always None (the gate stops gating)   12 red
#   `check_declarations` skipped from `plan_alloc` only                 5 red
#   `check_declarations` skipped from `alloc` only                      2 red
#   the mandatory-expect arm dropped (comp-8 with no expect passes)     2 red
#   the plan/stream extraBytes agreement loop deleted from `alloc`
#     (by source surgery, so what is measured is the check's absence
#     and not a reimplementation)                                       2 red
#   `_check_expect_arity` a no-op (the CLI stops enforcing --expect)     3 red
#   the pre-2026-08-20 splitter, which opens a malformed spec as a path  3 red
#
# Two readings worth keeping. The first sabotage is the one section 14 exists
# for, and its 12 reds are the measure of how much of this file was resting on a
# function `datalloc` called ZERO times until 2026-08-20 -- the skeptic's
# sentence, and the count that says it was not a stylistic complaint.
#
# The 5/2 SPLIT is the plan= bypass, stated as a number. The gate lives in two
# places on purpose: `plan_alloc` refuses the planning path and `alloc` refuses
# the writing path, and `alloc(..., plan=P)` runs only the second. Skipping
# either one alone still leaves reds, which is what "binding rather than
# advisory" has to mean -- before this arc `alloc(plan=P)` ran NEITHER, and a
# doctored plan put extraBytes 8 onto plainly stored bytes with every rule in
# this project green.
LEDGER = checks.Ledger("dat alloc", floor=203)
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


def run_cli(argv):
    """`datalloc._main(argv)` with both streams captured. -> (rc, out, err).

    `_main` catches `Refused` itself and prints it to STDERR before returning 1,
    so a test that only redirects stdout reads a refusal as silence.
    """
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = datalloc._main(argv)
    return rc, out.getvalue(), err.getvalue()


def comp_payload(n=6144):
    """Bytes a compression-8 stream genuinely has to work for.

    Long exact repeats, so the match coder has something to find, interleaved
    with an LCG's output, so the literal coder is not idle either. A payload of
    one repeated byte would compress beautifully and prove nothing: section 13
    is about a stream carrying a real Huffman table over BOTH alphabets, which
    is the shape `gwdat.decompress` has to walk to give the payload back.

    Deterministic by construction -- no `random` seed to drift -- so a failure
    here is reproducible from the file alone.
    """
    out = bytearray()
    motif = bytes((i * 7 + 3) % 251 for i in range(64))
    seed = 0x9E3779B9
    while len(out) < n:
        out += motif * 8                       # matches: one 64 B motif, eight times
        for _ in range(48):                    # literals: nothing can match these
            seed = (seed * 1103515245 + 12345) & 0xFFFFFFFF
            out.append((seed >> 16) & 0xFF)
    return bytes(out[:n])


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
                      [datalloc.Stream(real, 259, extra_bytes=8,
                                       expect=b"tiny")],
                      0x3000) is None,
              "...and that real stream is ACCEPTED as extraBytes 8, WITH the "
              "payload it must decode to", "expect= is mandatory as of "
              "2026-08-20; section 14 owns that rule")

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
    a.expect, a.stored_lookalike_ok = None, False
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
    check(got[0].extra_bytes == 0,
          "ONE trailing field is FLAGS and never EXTRA -- the older spelling "
          "keeps its old meaning", "extraBytes defaults to 0, stored")

    # FILE:FLAGS:EXTRA, the third field. Until 2026-08-19 there was no CLI path
    # to a compressed row at all: `extra_bytes` was reachable only by importing
    # the module and building `Stream` by hand, which is why the comp-8 gate had
    # never been crossed from a command line.
    #
    # The splitter is checked on its own FIRST, and that ordering is measured
    # rather than tidy: the pre-2026-08-19 splitter, put back as a sabotage,
    # hands `_read` the path with `:1` still glued on and dies on a
    # FileNotFoundError -- a hard stop naming a temp file, with no check red at
    # all. `_split_stream_spec` touches no filesystem, so it fails as three
    # named checks instead.
    check(datalloc._split_stream_spec(data + ":1:8") == (data, 1, 8),
          "_split_stream_spec: two trailing fields are FLAGS then EXTRA")
    check(datalloc._split_stream_spec(data + ":259") == (data, 259, None),
          "one trailing field is FLAGS, and EXTRA stays unset")
    check(datalloc._split_stream_spec(data) == (data, None, None),
          "and an absolute path with no trailing field is left whole",
          "its drive-letter colon is not a field separator")

    a.stream = [data + ":1:8"]
    a.expect = spill(tmp, "cli_arity.raw", b"whatever a reader must get back")
    got = datalloc._streams_from_args(a)
    check(got[0].flags == 1 and got[0].extra_bytes == 8,
          "FILE:FLAGS:EXTRA sets both fields", f"{got[0].flags} / "
          f"{got[0].extra_bytes}")
    check(got[0].data == pattern(31, 900),
          "and the path in front of them is still read whole",
          "the absolute path's own colon survives two rounds of splitting")
    check(got[0].expect == b"whatever a reader must get back",
          "and --expect lands on the COMPRESSED stream, which is the only one "
          "there is anything to check", "section 14 owns what it is checked for")
    a.expect = None
    a.stream = [data]
    check(datalloc._streams_from_args(a)[0].extra_bytes == 0,
          "a bare FILE is stored, as it always was")

    for bad in (4, 1, 16):
        a.stream = [f"{data}:1:{bad}"]
        m = refusal(datalloc._streams_from_args, a)
        check(m and "only 0 and 8" in m and "38682" in m,
              f"EXTRA {bad} is refused at parse time, naming the histogram",
              "{0: 38682, 8: 139058} over 177,740 live rows")
    a.stream = [f"{data}:1:0"]
    check(refusal(datalloc._streams_from_args, a) is None,
          "and an explicit EXTRA 0 is accepted -- the rule is the value, not "
          "the arity")

    # Three specs that used to fall through this function whole and die inside
    # `_read` -- FileNotFoundError on the first two, `OSError [Errno 22]` on the
    # third. Nothing allocated, which is what mattered, but a traceback naming a
    # temp file is not a diagnosis in a tool whose every other bad input is a
    # sentence.
    for bad_spec, why_bad in ((data + ":x:8", "a non-numeric FLAGS field"),
                              (data + ":1:8:0", "a THIRD trailing field"),
                              (data + ":", "an empty trailing field")):
        m = refusal(datalloc._split_stream_spec, bad_spec)
        check(m and "FILE[:FLAGS[:EXTRA]]" in m and "drive letter" in m,
              f"a malformed spec is REFUSED naming the grammar, not opened as a "
              f"filename: {why_bad}",
              (m or "-- it did not refuse").splitlines()[0][:72])

    # The comp-8 gate, reached from a command line rather than from an import.
    cli_head = spill(tmp, "cli_head.bin", b"")
    raw = comp_payload()
    cli_raw = spill(tmp, "cli_part.raw", raw)
    cli_part = spill(tmp, "cli_part.gwenc", gwenc.encode(raw))
    argv = ["--dat", path, "--file-id", "0x3000", "--plan",
            "--expect", cli_raw,
            "--stream", cli_head + ":259", "--stream", cli_part + ":1:8"]
    rc, out, err = run_cli(argv)
    check(rc == 0 and "extraBytes 8" in out,
          "--plan over a real gwenc stream file: accepted, and the plan says "
          "extraBytes 8 out loud", f"rc {rc}")
    stored = spill(tmp, "cli_stored.bin", pattern(41, 900))
    rc, out, err = run_cli(argv[:-1] + [stored + ":1:8"])
    check(rc == 1 and "does not DECODE" in err,
          "CONTROL: the same command over a STORED file is refused by the "
          "decode gate, from the CLI", f"rc {rc}")

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


# ------------------------------- 13. a NEW row that is REALLY compression 8

def section_compressed(tmp):
    """A brand-new row carrying a real `gwenc` stream, allocated and read back.

    Section 5 writes a map and re-derives every field of it, but its partner is
    STORED -- `Stream`'s `extra_bytes` defaults to 0 -- so until this section the
    only payload ever pushed through `alloc(confirm=True)` was one the archive
    treats as opaque bytes. The comp-8 gate at `datalloc.py:560` was exercised by
    `plan_alloc` alone (section 4), which is the DRY RUN: nothing had allocated a
    compressed row and then asked the archive to hand the payload back.

    NOTHING HERE PINS A SIZE OR A TABLE SHAPE, deliberately. `gwenc`'s framing is
    under active work, and a byte count of its output would be a test of the
    encoder's current tuning wearing this module's name -- green until somebody
    improves the compressor, then red for a reason that has nothing to do with
    allocation. What is asserted is IDENTITY (`Archive.read()` returns the exact
    bytes that went in), STRUCTURE (the row records extraBytes 8; its crc is over
    the STORED bytes and not the payload) and the fixture's one real constraint
    (the stream fits the largest run `classify_runs` will hand over).

    THE SABOTAGE IS AT THE BOTTOM and it is the point of the section as much as
    the success is: one byte of the stream flipped, and the gate must refuse on
    THIS path -- `plan_alloc` inside `alloc`, before a Writer exists -- rather
    than only in section 4's unit checks over hand-typed bytes.
    """
    print("\n13. a brand-new row carrying a real compression-8 stream")
    path, _ = fresh(tmp, "comp.dat")
    before = blob(path)
    raw = comp_payload()
    stream = gwenc.encode(raw)
    rep = gwenc.encode_report(raw, verify=False)

    check(rep["matches"] > 0 and rep["literals"] > 0,
          "the payload exercises BOTH halves of the stream, matches and literals",
          f"{len(raw)} B -> {len(stream)} B, {rep['matches']} match token(s), "
          f"{rep['literals']} literal token(s), {rep['blocks']} block(s)")
    check(len(stream) < len(raw),
          "the stream is genuinely smaller than what it encodes",
          f"{100 * len(stream) // len(raw)}% of the payload")
    check(datwrite.looks_compressed(stream),
          "and datwrite's decode gate agrees these bytes ARE compression 8")
    check(len(stream) <= LARGEST_USABLE,
          "it fits the largest run classify_runs will hand over -- the fixture's "
          "one real constraint on this payload",
          f"{len(stream)} B into {LARGEST_USABLE} B; a stream that outgrew this "
          f"would be refused by _place, not by the gate")

    # A map's own shape: an armed zero-length head chained to the partner that
    # holds the bytes. The head is stored and takes no extent; the partner is the
    # compressed one, which is the split retail uses.
    streams = [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
               datalloc.Stream(stream, datalloc.MAP_PARTNER_FLAGS_U16,
                               extra_bytes=8, expect=raw)]
    journal = os.path.join(tmp, "comp.journal.json")
    with quiet() as printed:
        plan = datalloc.alloc(path, streams, 0x3000, journal, confirm=True)
        plan.show()
    hi, pi = plan.head.index, plan.rows[1].index
    check("extraBytes 8" in printed.getvalue(),
          "the plan it carried out prints the declaration a reader has to check",
          f"rows {hi} (head) and {pi} (partner)")

    rows = read_rows(path)
    check(rows[pi][2] == 8,
          "the MFT row records extraBytes 8, re-derived from the raw bytes",
          f"row {pi}, +0x0C = {rows[pi][2]}")
    check(rows[hi][2] == 0 and rows[hi][1] == 0,
          "and the zero-length head beside it is untouched at extraBytes 0",
          "a head is not compressed because its partner is")
    check(payload_of(path, pi) == stream,
          "the bytes on disk are the STREAM, byte for byte -- this module "
          "compresses nothing and stores what it is handed", f"{len(stream)} B")
    check(rows[pi][5] == binascii.crc32(stream)
          and rows[pi][5] != binascii.crc32(raw),
          "the entry crc is over the STORED bytes and not the payload",
          "the archive checksums what it holds; the payload never touches disk")
    check(rows[pi][0] % BLOCK == 0
          and plan.rows[1].reservation % BLOCK == 0,
          "the reservation is whole aligned blocks, as for any other row",
          f"0x{rows[pi][0]:X} +{plan.rows[1].reservation}")

    with Archive(path) as ar:
        e = ar.row(pi)
        check(e.compression == 8 and e.compressed,
              "Archive -- which knows nothing of datalloc -- calls the new row "
              "compressed", f"compression {e.compression}")
        got = ar.read(e)
        check(got == raw,
              "and Archive.read() decodes it back to the EXACT payload",
              f"{len(got)} B out of a {len(raw)} B input")
        check(ar.raw(e) == stream,
              "while .raw() still hands back the compressed bytes -- the two "
              "readers disagree, which is what compression 8 MEANS")
        ids = file_id_table(ar, raw=True)
        check(ids.get(0x3000) == hi,
              "the file-id table resolves the new id to the HEAD in the RAW "
              "table -- the form the CLIENT can address",
              f"0x3000 -> row {ids.get(0x3000)}")
    check((0x3000, hi) in read_ids(path),
          "and the same pair is there in the table's own bytes, unpacked by hand",
          "two witnesses, one of which imports nothing")

    check(mft_self_ok(path),
          "the MFT self-crc is right for the grown table")
    check(datcheck_clear(path),
          "datcheck --preflight is 10 of 10 after a COMPRESSED allocation")
    with quiet():
        bad_crc = datwrite.verify(path)
    check(bad_crc == 0, "datwrite --verify: both crc rules hold", f"{bad_crc} bad")
    with Archive(path) as ar:
        check(datmove.overlaps(ar) == [], "no two rows share storage")
    check(len(blob(path)) == len(before),
          "and the file did not change length", f"{len(before)} B")

    with quiet():
        rc = datwrite.revert(journal)
    check(rc == 0 and blob(path) == before,
          "the journal reverts the whole allocation BYTE FOR BYTE",
          f"{len(before)} B compared")
    check(datcheck_clear(path), "and the archive is clear again afterwards")

    # ----------------------------------------------------------- the sabotage
    #
    # One byte of the stream, flipped, and the allocation must not happen. This
    # is the check that says the gate is on THIS path: section 4 refuses
    # `b"abcdefgh"`, bytes no encoder made, so it can only prove the predicate.
    # Here the bytes came out of `gwenc` and were accepted twenty lines above.
    corrupt = bytearray(stream)
    corrupt[6] ^= 0xFF
    corrupt = bytes(corrupt)
    survived = [i for i in range(16)
                if datwrite.looks_compressed(
                    stream[:i] + bytes([stream[i] ^ 0xFF]) + stream[i + 1:])]
    check(survived == [],
          "every single-byte flip in the stream's first 16 bytes is refused -- "
          "that region is the Huffman table and nothing decodes without it",
          "16 of 16, and 16 of 16 at each of five payload sizes when measured "
          "2026-08-19")

    fresh_path, _ = fresh(tmp, "sabotage.dat")
    untouched = blob(fresh_path)
    bad_streams = [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
                   datalloc.Stream(corrupt, datalloc.MAP_PARTNER_FLAGS_U16,
                                   extra_bytes=8)]
    with Archive(fresh_path) as ar:
        m = refusal(datalloc.plan_alloc, ar, bad_streams, 0x3000)
    check(m and "does not DECODE" in m and "extraBytes 8" in m,
          "plan_alloc REFUSES the corrupted stream, naming the decode",
          (m or "-- it did not refuse").splitlines()[0][:72])
    bad_journal = os.path.join(tmp, "sabotage.journal.json")
    m = refusal(datalloc.alloc, fresh_path, bad_streams, 0x3000, bad_journal,
                confirm=True)
    check(m and "does not DECODE" in m,
          "and so does alloc --confirm, which is the call that would write")
    check(blob(fresh_path) == untouched and not os.path.exists(bad_journal),
          "the archive is byte-identical and no journal was even opened",
          "alloc plans before it constructs a Writer")

    # WHERE THE GATE IS, stated because the answer is not "on the bytes". It is
    # on the DECLARATION: the same corrupted bytes offered as extraBytes 0 are
    # accepted, because a stored row is bytes and these are bytes.
    ok_streams = [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
                  datalloc.Stream(corrupt, datalloc.MAP_PARTNER_FLAGS_U16)]
    with Archive(fresh_path) as ar:
        check(refusal(datalloc.plan_alloc, ar, ok_streams, 0x3000) is None,
              "the gate is on the DECLARATION: the same bytes as extraBytes 0 "
              "are accepted", "declaring stored is a claim about the row, not "
              "about the bytes")
        # AND THE OTHER DIRECTION WAS AN OPEN GAP UNTIL 2026-08-20, recorded here
        # rather than in prose nobody greps: a GENUINE gwenc stream declared 0
        # allocated cleanly and the client handed the compressed bytes back to
        # whatever asked for the file. The comment then said "if this check ever
        # goes red because that guard landed here, the guard is the improvement
        # and this check is the thing to rewrite". It landed, and this is the
        # rewrite -- section 14 owns the rule and its escape hatch.
        m = refusal(datalloc.plan_alloc, ar,
                    [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
                     datalloc.Stream(stream, datalloc.MAP_PARTNER_FLAGS_U16)],
                    0x3000)
        check(m and "C-6" in m,
              "GAP CLOSED: a real compressed stream declared extraBytes 0 is now "
              "refused as a stored lookalike, naming C-6",
              (m or "-- it did not refuse").splitlines()[0][:72])

    # HOW STRONG THE GATE IS, measured rather than assumed. It refutes FRAMING
    # damage, not content damage: `gwdat.decompress` takes the output size from
    # the trailer and uses it as the loop's own bound, so a stream that still
    # terminates normally passes whatever it decoded to. Sampled every 4th byte
    # to keep the section under a second.
    refused = decoded_wrong = 0
    for i in range(0, len(stream), 4):
        flip = stream[:i] + bytes([stream[i] ^ 0xFF]) + stream[i + 1:]
        if not datwrite.looks_compressed(flip):
            refused += 1
            continue
        try:
            back, _declared = gwdat.decompress(flip)
        except Exception:                                    # noqa: BLE001
            continue
        decoded_wrong += back != raw
    check(refused > 0 and decoded_wrong > 0,
          "and THIS gate is a FRAMING check, not a fidelity one: some flips run "
          "out of input and are caught, others decode to the wrong bytes and "
          "are not -- which is why section 14 exists",
          f"{refused} refused, {decoded_wrong} decoded to something else, of "
          f"{len(range(0, len(stream), 4))} sampled flips")


# ------------------------------------------ 14. the fidelity gate, and expect=

def silent_flip(stream, raw, limit=240):
    """A single-byte flip the FRAMING gate cannot see. -> (bytes, index).

    The shape section 13's sweep counts in bulk and this section needs one of:
    the flipped stream still passes `looks_compressed`, still decodes without
    raising, still declares EXACTLY `len(raw)` -- and gives back different bytes.
    Nothing about the archive can refute that afterwards, because the entry crc is
    over the stored bytes and moves with the corruption.

    Searched rather than hard-coded, because a hard-coded index would be a fact
    about one build of `gwenc` wearing this module's name. `(None, None)` if the
    first `limit` positions hold no such flip, and the caller checks for it -- if
    that ever happens the interesting thing is that it happened.
    """
    for i in range(min(limit, len(stream))):
        flip = stream[:i] + bytes([stream[i] ^ 0xFF]) + stream[i + 1:]
        if not datwrite.looks_compressed(flip):
            continue
        try:
            back, declared = gwdat.decompress(flip)
        except Exception:                                        # noqa: BLE001
            continue
        if declared == len(raw) and back != raw:
            return flip, i
    return None, None


def short_trailer(stream):
    """The declared output size, minus one. The whole corruption.

    `gwdat.decompress` reads the payload length from the LAST u32 word
    (`gwdat.py:349-350`) and then uses it as the decode loop's own termination
    bound (`gwdat.py:356`), so `declared == len(back)` -- the second half of
    `looks_compressed` -- is TRUE BY CONSTRUCTION here: the stream decodes one
    byte short and cheerfully agrees with itself about it. `looks_compressed`
    says yes and the archive gets a row holding a payload nobody asked for.
    """
    at = (len(stream) // 4) * 4 - 4
    declared = struct.unpack_from("<I", stream, at)[0]
    return stream[:at] + struct.pack("<I", declared - 1) + stream[at + 4:]


def section_fidelity(tmp):
    """The DECLARATION checked against the bytes, which framing cannot do.

    WHY THIS SECTION EXISTS, in one sentence a skeptic wrote on 2026-08-19: a
    `gwenc` stream whose trailer is corrupted was NOT refused -- `alloc(confirm=
    True)` and `--stream FILE:1:8` both wrote it, `Archive.read()` handed back
    8,191 bytes instead of 8,192, and `--verify`, `datcheck --preflight` and the
    overlap sweep were all green -- while `datwrite.declaration_fault` refused the
    identical bytes and `datmove --compression 8` had made `--expect` mandatory
    the day before. `datalloc` was the only writer of the three that committed a
    compression-8 payload with no declaration of what a reader must get back, and
    the string `declaration_fault` appeared in it zero times.

    The five shapes below are that skeptic's own repros, plus the two directions
    section 13 could only record. THE SABOTAGE AT THE BOTTOM is what makes them
    checks rather than descriptions: with `declaration_fault` stubbed to return
    None the trailer-corrupted stream allocates again, and the archive hands back
    the wrong payload with every rule this project owns still green.
    """
    print("\n14. the declaration checked against the bytes")
    raw = comp_payload()
    stream = gwenc.encode(raw)

    # (i) THE TRAILER. Decodes SHORT, and the framing gate cannot see it.
    short = short_trailer(stream)
    check(datwrite.looks_compressed(short),
          "the FRAMING gate still calls a trailer-corrupted stream compression 8 "
          "-- it decodes, and it agrees with its own trailer about the length",
          f"declared {gwdat.decompress(short)[1]} B against a {len(raw)} B "
          f"payload")

    path, _ = fresh(tmp, "fid_short.dat")
    untouched = blob(path)
    journal = os.path.join(tmp, "fid_short.journal.json")
    bad = [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
           datalloc.Stream(short, datalloc.MAP_PARTNER_FLAGS_U16,
                           extra_bytes=8, expect=raw)]
    with Archive(path) as ar:
        m = refusal(datalloc.plan_alloc, ar, bad, 0x3000)
    check(m and "trailer declares" in m and str(len(raw) - 1) in m
          and str(len(raw)) in m,
          "plan_alloc REFUSES it, naming the trailer and BOTH lengths",
          (m or "-- it did not refuse").splitlines()[-1][:72])
    m = refusal(datalloc.alloc, path, bad, 0x3000, journal, confirm=True)
    check(m and "trailer declares" in m,
          "and so does alloc --confirm, which is the call that wrote it before")
    check(blob(path) == untouched and not os.path.exists(journal),
          "archive byte-identical, no journal opened",
          f"{len(untouched)} B compared")

    # ...and from the command line, which is the door this arc opened.
    cli_dat, _ = fresh(tmp, "fid_cli.dat")
    cli_before = blob(cli_dat)
    head_f = spill(tmp, "fid_head.bin", b"")
    short_f = spill(tmp, "fid_short.gwenc", short)
    raw_f = spill(tmp, "fid_payload.raw", raw)
    good_f = spill(tmp, "fid_good.gwenc", stream)
    cli_journal = os.path.join(tmp, "fid_cli.journal.json")
    rc, out, err = run_cli(["--dat", cli_dat, "--file-id", "0x3000", "--alloc",
                            "--confirm", "--journal", cli_journal,
                            "--expect", raw_f, "--stream", head_f + ":259",
                            "--stream", short_f + ":1:8"])
    check(rc == 1 and "trailer declares" in err,
          "the CLI refuses it too -- `--stream FILE:1:8 --alloc --confirm` "
          "returned rc 0 and wrote row 23 before this landed", f"rc {rc}")
    check(blob(cli_dat) == cli_before and not os.path.exists(cli_journal),
          "and that archive is untouched with no journal either")

    # (ii) THE HARDER SHAPE: same declared length, different content.
    flip, at = silent_flip(stream, raw)
    check(flip is not None,
          "a single-byte flip exists that decodes to the RIGHT LENGTH and the "
          "WRONG BYTES -- the corruption no length check can see",
          f"byte {at}" if flip else "none found in the first 240 bytes")
    if flip is not None:
        check(datwrite.looks_compressed(flip),
              "the framing gate calls it compression 8 as well",
              f"{len(gwdat.decompress(flip)[0])} B out, not the payload")
        fpath, _ = fresh(tmp, "fid_flip.dat")
        fbefore = blob(fpath)
        fstreams = [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
                    datalloc.Stream(flip, datalloc.MAP_PARTNER_FLAGS_U16,
                                    extra_bytes=8, expect=raw)]
        m = refusal(datalloc.alloc, fpath, fstreams, 0x3000,
                    os.path.join(tmp, "fid_flip.journal.json"), confirm=True)
        check(m and "NOT the expected payload" in m and "first difference" in m,
              "and it is REFUSED, naming the first byte that differs -- the only "
              "refutation there is, and only available before the write",
              (m or "-- it did not refuse").splitlines()[-1][:72])
        check(blob(fpath) == fbefore, "archive byte-identical")

    # (iii) NO expect AT ALL. The rule datmove has had since 2026-08-18.
    npath, _ = fresh(tmp, "fid_noexpect.dat")
    nstreams = [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
                datalloc.Stream(stream, datalloc.MAP_PARTNER_FLAGS_U16,
                                extra_bytes=8)]
    with Archive(npath) as ar:
        m = refusal(datalloc.plan_alloc, ar, nstreams, 0x3000)
    check(m and "no expected payload" in m and "datmove" in m,
          "extraBytes 8 with no expect= is refused, naming datmove's precedent",
          (m or "-- it did not refuse").splitlines()[0][:72])
    m = refusal(datalloc.alloc, npath, nstreams, 0x3000,
                os.path.join(tmp, "fid_noexpect.journal.json"), confirm=True)
    check(m and "no expected payload" in m,
          "and alloc --confirm refuses the same way -- the declaration is "
          "mandatory on the write path, not advisory on the planning one")

    # (iv) THE PLAN= BYPASS. A plan is a placement, not a second opinion.
    ppath, _ = fresh(tmp, "fid_plan.dat")
    pbefore = blob(ppath)
    stored = [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
              datalloc.Stream(pattern(19, 900), datalloc.MAP_PARTNER_FLAGS_U16)]
    with Archive(ppath) as ar:
        doctored = datalloc.plan_alloc(ar, stored, 0x3000)
    doctored.rows[1].extra_bytes = 8            # what the caller can reach
    m = refusal(datalloc.alloc, ppath, stored, 0x3000,
                os.path.join(tmp, "fid_plan.journal.json"), confirm=True,
                plan=doctored)
    check(m and "extraBytes 8 while stream 1 declares 0" in m,
          "a doctored plan that disagrees with its streams about extraBytes is "
          "REFUSED -- alloc(plan=P) wrote 8 over plainly stored bytes before "
          "this, with Archive.read() not even raising",
          (m or "-- it did not refuse").splitlines()[0][:72])
    check(blob(ppath) == pbefore, "archive byte-identical")

    # ...and the fidelity gate runs on the plan= path too, not only the shape
    # check above it. Same plan, a stream whose bytes were swapped for corrupted
    # ones after it was computed. Its own fixture, because a sabotage that lets
    # the doctored write land registers 0x3000 in `ppath` and everything after it
    # would refuse on the id rather than on the thing being measured.
    p2, _ = fresh(tmp, "fid_plan2.dat")
    p2before = blob(p2)
    with Archive(p2) as ar:
        good_plan = datalloc.plan_alloc(
            ar, [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
                 datalloc.Stream(stream, datalloc.MAP_PARTNER_FLAGS_U16,
                                 extra_bytes=8, expect=raw)], 0x3000)
    m = refusal(datalloc.alloc, p2,
                [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
                 datalloc.Stream(short, datalloc.MAP_PARTNER_FLAGS_U16,
                                 extra_bytes=8, expect=raw)],
                0x3000, os.path.join(tmp, "fid_plan2.journal.json"),
                confirm=True, plan=good_plan)
    check(m and "trailer declares" in m,
          "and a handed-in plan does NOT skip the decode-and-compare -- the gate "
          "is binding on the write path, not a property of one route to it")
    check(blob(p2) == p2before, "that archive is byte-identical too")

    # (v) THE OTHER DIRECTION: C-6, and the hatch its 4-in-38,621 need.
    lpath, _ = fresh(tmp, "fid_lookalike.dat")
    look = [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
            datalloc.Stream(stream, datalloc.MAP_PARTNER_FLAGS_U16)]
    with Archive(lpath) as ar:
        m = refusal(datalloc.plan_alloc, ar, look, 0x3000)
    check(m and "C-6" in m and "compression 0" in m,
          "a REAL gwenc stream declared extraBytes 0 is refused as a stored "
          "lookalike, naming C-6 -- section 13 recorded this as an OPEN GAP",
          (m or "-- it did not refuse").splitlines()[0][:72])
    hatch = [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
             datalloc.Stream(stream, datalloc.MAP_PARTNER_FLAGS_U16,
                             stored_lookalike_ok=True)]
    with Archive(lpath) as ar:
        # NOT through `refusal()` here: it swallows stdout into its own buffer,
        # and the override LINE is half of what this pair is checking.
        with quiet() as printed:
            try:
                datalloc.plan_alloc(ar, hatch, 0x3000)
                hatch_msg = None
            except datalloc.Refused as exc:
                hatch_msg = str(exc)
        check(hatch_msg is None,
              "and stored_lookalike_ok=True lets it through -- MEASURED, 4 of "
              "38,621 real stored rows decode as compression 8 and would be "
              "refused for it",
              hatch_msg.splitlines()[0][:72] if hatch_msg else
              "against 0 of 1,500 decompressed retail payloads")
        check("C-6 OVERRIDE TAKEN" in printed.getvalue(),
              "the hatch prints a line naming C-6 when taken, as datwrite's does "
              "-- an override that leaves no trace is the same defect as no "
              "override",
              printed.getvalue().strip().splitlines()[0][:72]
              if printed.getvalue().strip() else "(silent)")
        check(refusal(datalloc.plan_alloc, ar,
                      [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
                       datalloc.Stream(pattern(23, 700),
                                       datalloc.MAP_PARTNER_FLAGS_U16)],
                      0x3000) is None,
              "CONTROL: ordinary stored bytes need no hatch -- the rule fires on "
              "the DECODE, not on the declaration alone")

    # The armed head, which must survive all of this untouched.
    apath, _ = fresh(tmp, "fid_armed.dat")
    ajournal = os.path.join(tmp, "fid_armed.journal.json")
    with quiet():
        aplan = datalloc.alloc(apath, map_streams(pattern(29, 1200)), 0x3000,
                               ajournal, confirm=True)
    check(read_rows(apath)[aplan.head.index][1] == 0,
          "the ARMED ZERO-LENGTH HEAD still allocates -- declaration_fault(b\"\", "
          "0, None) is None, so deploy.py's re-bloat trigger needed no special "
          "case", "an empty stored stream is not a compressed one")

    # (vi) AND THE HAPPY PATH, end to end, with the declaration.
    hpath, _ = fresh(tmp, "fid_happy.dat")
    hjournal = os.path.join(tmp, "fid_happy.journal.json")
    good = [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
            datalloc.Stream(stream, datalloc.MAP_PARTNER_FLAGS_U16,
                            extra_bytes=8, expect=raw)]
    with quiet():
        hplan = datalloc.alloc(hpath, good, 0x3000, hjournal, confirm=True)
    with Archive(hpath) as ar:
        got = ar.read(ar.row(hplan.rows[1].index))
    check(got == raw and read_rows(hpath)[hplan.rows[1].index][2] == 8,
          "a stream that IS its declaration allocates and reads back exactly -- "
          "the gate refuses wrong payloads, never right ones",
          f"{len(got)} B back, +0x0C = 8")
    check(datcheck_clear(hpath), "datcheck --preflight is 10 of 10 afterwards")

    # ...and the same thing from the command line, with --expect.
    hcli, _ = fresh(tmp, "fid_happy_cli.dat")
    hcli_journal = os.path.join(tmp, "fid_happy_cli.journal.json")
    rc, out, err = run_cli(["--dat", hcli, "--file-id", "0x3000", "--alloc",
                            "--confirm", "--journal", hcli_journal,
                            "--expect", raw_f, "--stream", head_f + ":259",
                            "--stream", good_f + ":1:8"])
    check(rc == 0 and "extraBytes 8" in out,
          "and the CLI does it with --expect, self-check green", f"rc {rc}")
    with Archive(hcli) as ar:
        rows = [e.index for e in ar.entries if e.compression == 8 and e.size]
        cli_got = ar.read(ar.row(rows[-1])) if rows else b""
    check(cli_got == raw,
          "the row the CLI wrote decodes back to the payload --expect named",
          f"{len(cli_got)} B")

    # THE CLI's THREE ARITY RULES, each refused before a file is opened.
    rc, out, err = run_cli(["--dat", hcli, "--file-id", "0x3001", "--plan",
                            "--stream", head_f + ":259",
                            "--stream", good_f + ":1:8"])
    check(rc == 1 and "no --expect" in err and "datmove" in err,
          "EXTRA 8 with no --expect: refused from the command line, naming "
          "datmove's precedent", f"rc {rc}")
    rc, out, err = run_cli(["--dat", hcli, "--file-id", "0x3001", "--plan",
                            "--expect", raw_f,
                            "--stream", head_f + ":259",
                            "--stream", good_f + ":1:0"])
    check(rc == 1 and "no --stream declares EXTRA 8" in err,
          "--expect with nothing to check it against: refused rather than "
          "ignored -- the likeliest reading is a missing `:8`", f"rc {rc}")
    rc, out, err = run_cli(["--dat", hcli, "--file-id", "0x3001", "--plan",
                            "--expect", raw_f, "--stream", good_f + ":259:8",
                            "--stream", good_f + ":1:8"])
    check(rc == 1 and "--expect names ONE payload" in err,
          "two compressed streams and one --expect: refused, naming the API for "
          "the general case", f"rc {rc}")

    # ------------------------------------------------------------ the sabotage
    #
    # `datwrite.declaration_fault` stubbed to return None -- the exact state this
    # module was in until 2026-08-20, when it called the function zero times --
    # and the trailer-corrupted stream must then reach disk. In memory, one
    # archive, restored in a `finally`. If this ever stops writing the row, the
    # gate has moved somewhere else and the checks above have stopped measuring
    # what they say they measure.
    spath, _ = fresh(tmp, "fid_sabotage.dat")
    sjournal = os.path.join(tmp, "fid_sabotage.journal.json")
    real_fault = datwrite.declaration_fault
    try:
        datwrite.declaration_fault = lambda *a, **kw: None
        with quiet():
            splan = datalloc.alloc(spath, bad, 0x3000, sjournal, confirm=True)
        with Archive(spath) as ar:
            sgot = ar.read(ar.row(splan.rows[1].index))
            sbad_crc = 0
        with quiet():
            sbad_crc = datwrite.verify(spath)
    finally:
        datwrite.declaration_fault = real_fault
    check(len(sgot) == len(raw) - 1 and sgot != raw,
          "SABOTAGE: with declaration_fault stubbed out the corrupted stream "
          "allocates and the archive hands back the WRONG payload -- so the gate "
          "is what refuses it, not the framing check and not luck",
          f"{len(sgot)} B back where the payload is {len(raw)} B")
    check(sbad_crc == 0 and datcheck_clear(spath),
          "and that archive is GREEN: both crc rules and all ten open-time rules "
          "pass over a row nobody can read", "which is FINDINGS C-6 exactly")
    # And the gate is LIVE again, asked rather than asserted: the same bytes that
    # just allocated are refused once more. A `finally` that restored the wrong
    # thing would leave every check after this one measuring the stub.
    rpath, _ = fresh(tmp, "fid_restored.dat")
    m = refusal(datalloc.alloc, rpath, bad, 0x3000,
                os.path.join(tmp, "fid_restored.journal.json"), confirm=True)
    check(m and "trailer declares" in m,
          "the stub is gone and the refusal is back -- checked by re-running the "
          "sabotage's own input, not by comparing a function object",
          (m or "-- it did not refuse").splitlines()[-1][:72])


# ------------------------------------------------------ 15. the reserve
#
# WORLDMAPS-W5. Until 2026-08-20 a created row's reservation was exactly
# `blocks_for(len(data))` -- zero headroom by construction -- so a created
# chain's SECOND, larger install was already past a ceiling nobody had chosen
# and fell through to a relocation. `Stream(reserve=N)` is the caller stating
# what the row is entitled to, once, at creation.
#
# THE WHOLE RISK OF THIS FIELD IS THAT IT LEAKS. `size` is what the client
# reads; `reserve` is a private statement about how far the row may grow later.
# So every check below asks the same question twice -- that the RESERVATION
# moved, and that the size, the crc and the declaration did NOT.


def section_reserve(tmp):
    print("\n15. reserve: headroom the row is GIVEN, not bytes it HOLDS")
    partner = pattern(31, 900)
    # 900 B is 2 blocks; 2560 is 5. The fixture's usable runs are 1 block at 5,
    # 2 at 7-8 and 6 at 10-15, so the two cases land in DIFFERENT runs and the
    # control below differs in offset as well as in reservation.
    budget = 5 * BLOCK

    path, _ = fresh(tmp, "reserve.dat")
    with Archive(path) as ar:
        with quiet():
            plan = datalloc.plan_alloc(
                ar, [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
                     datalloc.Stream(partner, datalloc.MAP_PARTNER_FLAGS_U16,
                                     reserve=budget)], 0x3000)
            bare = datalloc.plan_alloc(ar, map_streams(partner), 0x3001)
    part, control = plan.rows[1], bare.rows[1]
    check(part.reservation == budget,
          "a stream carrying reserve=2560 is placed in 2560 B of blocks",
          f"{part.reservation} B for a {len(partner)} B payload")
    check(control.reservation == 1024 and part.reservation != control.reservation,
          "CONTROL: the same 900 B payload with no reserve gets 1024 B -- the "
          "reservation moved because of the budget, not because of the bytes",
          f"{control.reservation} B without, {part.reservation} B with")
    check(part.size == len(partner) and control.size == part.size,
          "and `size` is the PAYLOAD either way -- the client reads this field "
          "and knows nothing about our budget", f"{part.size} B")
    check(part.crc == binascii.crc32(partner) == control.crc,
          "so is the crc: it is over the bytes, never over the reservation")
    check(plan.rows[0].reservation == 0 and plan.rows[0].size == 0,
          "and the armed head is untouched -- zero length, no extent, the "
          "re-bloat trigger exactly as before")

    with quiet() as out:
        part.show()
    said = out.getvalue()
    check(f"+{budget}" in said and f"{budget - len(partner)} B of headroom" in said,
          "the plan STATES the headroom it is buying rather than leaving the "
          "reader to subtract -- a budget nobody prints is a budget nobody "
          "checks against the row that asked for it", said.strip()[:96])

    # Placement CONSUMES the reserved blocks, which is the property that makes
    # the budget worth anything: a second row handed the tail of this run would
    # be sitting in the space the first one was promised.
    with Archive(path) as ar:
        with quiet():
            two = datalloc.plan_alloc(
                ar, [datalloc.Stream(partner, 259, reserve=budget),
                     datalloc.Stream(pattern(32, 600), 1)], 0x3002)
    a, b = two.rows
    check(not (a.offset < b.offset + b.reservation
               and b.offset < a.offset + a.reservation),
          "a second stream in the same allocation is placed OUTSIDE the "
          "reserved extent, not inside its unused tail",
          f"0x{a.offset:X} +{a.reservation} and 0x{b.offset:X} +{b.reservation}")

    # THE REFUSALS.
    with Archive(path) as ar:
        def why(streams):
            return refusal(datalloc.plan_alloc, ar, streams, 0x3000)

        m = refusal(datalloc.Stream, b"", datalloc.MAP_HEAD_FLAGS_U16,
                    reserve=1024)
        check(m and "owns NO EXTENT" in m and "PARTNER" in m,
              "a reserve on a ZERO-LENGTH stream is refused, naming the partner "
              "as the row that grows -- an armed head has no offset to reserve "
              "blocks at, so a budget there would be accepted and do nothing",
              (m or "-- accepted").splitlines()[0])
        check(refusal(datalloc.Stream, b"", datalloc.MAP_HEAD_FLAGS_U16) is None,
              "CONTROL: the same empty head with NO reserve still constructs -- "
              "the refusal is about the budget, not about emptiness")
        m = refusal(datalloc.Stream, partner, 1, reserve=len(partner) - 1)
        check(m and "smaller than" in m and "wrong row" in m,
              "a reserve UNDER its own payload is refused rather than clamped -- "
              "max() would paper over it and report headroom nobody has",
              (m or "-- accepted").splitlines()[0])
        check(refusal(datalloc.Stream, partner, 1,
                      reserve=len(partner)) is None,
              "CONTROL: a reserve exactly equal to the payload is legal -- the "
              "rule is `>= len(data)`, and a row entitled to just itself is a "
              "statement, not an error")
        for bad in (1024.5, "1024", None, True):
            m = refusal(datalloc.Stream, partner, 1, reserve=bad)
            check(m and "not a whole number of bytes" in m,
                  f"reserve={bad!r} is refused: a reservation is counted in "
                  f"bytes", (m or "-- accepted").splitlines()[0][:64])
        m = refusal(datalloc.Stream, partner, 1, reserve=-512)
        check(m and "not a whole number of bytes" in m,
              "and so is a negative one")

        # The budget is judged by the same placement rule the payload is: a
        # reserve nothing can hold is "nothing fits", not a silent shrink.
        m = why([datalloc.Stream(pattern(33, 300), 259,
                                 reserve=LARGEST_USABLE + BLOCK)])
        check(m and "nothing fits" in m,
              "a budget larger than the largest usable run is refused by the "
              "ordinary placement rule -- a reserve buys real blocks or it "
              "buys nothing", f"largest usable {LARGEST_USABLE} B")

    # THE HANDED-IN PLAN, mirroring section 14's extraBytes discipline. The
    # write carries `r.reservation` out verbatim, and the archive has no
    # entitlement field, so a row given less than its budget is indistinguishable
    # afterwards from a row that never had one.
    ppath, _ = fresh(tmp, "reserve_plan.dat")
    pbefore = blob(ppath)
    budgeted = [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
                datalloc.Stream(partner, datalloc.MAP_PARTNER_FLAGS_U16,
                                reserve=budget)]
    with Archive(ppath) as ar:
        with quiet():
            stale = datalloc.plan_alloc(ar, map_streams(partner), 0x3000)
    m = refusal(datalloc.alloc, ppath, budgeted, 0x3000,
                os.path.join(tmp, "reserve_plan.journal.json"), confirm=True,
                plan=stale)
    check(m and "reserves 1024 B" in m and f"asks for {budget} B" in m,
          "a plan computed BEFORE the reserve was set is refused rather than "
          "carried out -- it would give the row what the payload needs while "
          "the caller believed it bought headroom",
          (m or "-- accepted").splitlines()[0])
    check(blob(ppath) == pbefore, "and the archive is byte-identical")
    with Archive(ppath) as ar:
        with quiet():
            fat = datalloc.plan_alloc(ar, budgeted, 0x3000)
    m = refusal(datalloc.alloc, ppath, map_streams(partner), 0x3000,
                os.path.join(tmp, "reserve_plan2.journal.json"), confirm=True,
                plan=fat)
    check(m and f"reserves {budget} B" in m and "asks for 1024 B" in m,
          "and the OTHER direction too: a plan reserving blocks no stream asked "
          "for is the same disagreement seen from the other side",
          (m or "-- accepted").splitlines()[0])

    # AND THE WRITE. The reservation is the one number here that cannot be
    # re-derived from the archive afterwards, so the evidence has to be the
    # BYTES: the payload where it belongs, zeroes across the whole budget, and
    # nothing else claiming any of it.
    wpath, _ = fresh(tmp, "reserve_write.dat")
    wbefore = blob(wpath)
    with quiet():
        wplan = datalloc.alloc(wpath, budgeted, 0x3000,
                               os.path.join(tmp, "reserve_write.journal.json"),
                               confirm=True)
    pi = wplan.rows[1].index
    rows = read_rows(wpath)
    off = rows[pi][0]
    check(rows[pi][1] == len(partner) and rows[pi][5] == binascii.crc32(partner),
          "the written row declares the PAYLOAD's size and crc, not the "
          "budget's", f"size {rows[pi][1]}, crc 0x{rows[pi][5]:08X}")
    check(payload_of(wpath, pi) == partner,
          "and holds exactly the bytes handed in", f"{len(partner)} B")
    tail = blob(wpath)[off + len(partner):off + budget]
    check(len(tail) == budget - len(partner) and set(tail) == {0},
          "the reserved tail is ZEROED across the whole budget -- the fixture "
          "fills free space with 0xCC, so this is the reservation being real "
          "rather than the padding a 2-block row would have had",
          f"{len(tail)} B of zeroes past the payload")
    check(len(blob(wpath)) == len(wbefore),
          "the file did not change length", f"{len(wbefore)} B")
    check(datcheck_clear(wpath),
          "datcheck --preflight is 10 of 10 over an archive with a reserved row")
    with Archive(wpath) as ar:
        check(datmove.overlaps(ar) == [],
              "and no two rows share storage -- the reserved blocks are the new "
              "row's and nobody else's")


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
        section_compressed(tmp)
        section_fidelity(tmp)
        section_reserve(tmp)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
