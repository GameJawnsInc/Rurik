"""Check the archive PLANNER's placement policy against an archive we build.

datplan.py applies nothing, so its defects cost nothing until somebody follows a
plan. This one was worth catching before that: for any payload smaller than the
largest free run, `plan_insert` placed the new file at the start of the largest
run -- and on vault/dat_study/Gw.dat the largest run is 14,718,976 bytes at
0xF8FFF000 holding a complete master file table, one of the slots the client
rotates its containers through. The five largest runs, 88.5% of all "free" space,
each begin with a live container generation.

Two things were wrong and this file checks both.

  1. ORDERING WAS POLICY. free_runs() sorted largest-first and plan_insert() took
     the first qualifying run, so the sort decided the allocation and no line of
     code said so. It is best fit now -- smallest qualifying run -- which is also
     what the client's own allocator does.
  2. "FREE" WAS THE GAP BETWEEN RESERVATIONS. A previous container generation is
     pointed at by no MFT row, so it reads as free by that measure. It is not: it
     is the copy the client is about to rotate back onto.

THE HEAD OF A RUN IS NOT ENOUGH, which is why section 2 is the section that
matters. MEASURED on the real archive, the run at 0xF6772800 is 428 blocks of
ordinary stale data followed by a file-id table generation -- a head-only test
calls it clean. So the fixture below hides its second container six blocks into a
run, and check 6 asserts a head test really would miss it before check 8 asserts
the scan catches it anyway.

Section 4 is the one that could have gone red against the old code and is the
reason to trust the rest: it reimplements the old largest-first line and asserts
its choice lands inside a run the new classifier withholds.

WHAT IT RUNS AGAINST. A 32.5 KB archive this file builds in a temp directory and
deletes afterwards. It never opens vault/dat_study/Gw.dat and never reads C:\\gw,
so it needs no vault and passes on a bare machine. The fixture is built from the
layout archive.py MEASURED against the shipped client; the numbers quoted above
from the real archive are context, not fixtures. Nothing is taken from any
upstream and no derivation-register row is owed.

    python toolkit/mapdata/test_datplan.py
"""

import binascii
import contextlib
import io
import os
import re
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ENTRY_SIZE  # noqa: E402
import datplan  # noqa: E402
import checks  # noqa: E402

# FLOOR: the checks below. Every one runs unconditionally -- this file builds its
# own fixture, so there is no corpus to be missing and no section that can
# legitimately not run. Measured from a green run on 2026-08-10, not counted by
# hand: the first version of this line said 24 because that is what counting the
# call sites in the editor produced.
#
# RAISED 30 -> 38 on 2026-08-14 with section 8, and the eight are an indictment
# of the thirty. This file asserted the placement POLICY exhaustively and never
# once asked where an edit POINTED, so `datplan` printed three wrong MFT
# addresses -- row N-1 for "MFT row N", the file-id table for "MFT row 3", the
# file header for "MFT row 2" -- and was green here the whole time, on a tool
# whose output a human applies by hand. Same fixture, no vault, no client.
#
# RAISED 38 -> 44 on 2026-08-17 with section 9, the declared-extent projection.
# The thirty-eight above all rest on a MARK -- the block a container signature
# sits on -- and none of them asked how far the table that signature declares
# actually REACHES. A generation whose extent runs off the end of its own free
# run leaves the next run with no magic at any boundary, so it scored usable and
# best_fit would place a payload inside a live table. Four of the six new checks
# are CONTROLS (runs past the extent still usable, the run before it untouched,
# the untouched fixture unchanged), because a projection that swallowed
# everything downstream would withhold the archive and protect nothing.
LEDGER = checks.Ledger("dat planner", floor=44)
check = checks.adopt(LEDGER)

FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"

BLOCK = 512
SLACK = 0xCC            # fills every byte no row claims. Non-zero on purpose,
                        # and as a (file_id, row) pair it decodes to row
                        # 0xCCCCCCCC -- far past any live row, so ordinary slack
                        # can never be mistaken for a file-id table.

# The layout, in blocks. Hand-laid so the free runs come out at known sizes and
# the largest of them is a container -- which is exactly the shape of the real
# archive, and the shape that made the old policy wrong.
#
#   blk  0   row 1  file header
#   blk  1   row 2  file-id table (the live one)
#   blk  2   row 4
#   blk  3.. 4      FREE,  2 blocks
#   blk  5   row 5
#   blk  6..13      FREE,  8 blocks
#   blk 14   row 3  the MFT itself
#   blk 15..38      FREE, 24 blocks  <- LARGEST. Mft shadow at its head, and it
#   blk 39   row 6                      sits directly after the MFT, so it is
#   blk 40..43      FREE,  4 blocks     also the wall the table grows into.
#   blk 44   row 7
#   blk 45..56      FREE, 12 blocks  <- id-table shadow SIX BLOCKS IN
#   blk 57   row 8
#   blk 58          FREE,  1 block
#   blk 59   row 9
#   blk 60..63      FREE,  4 blocks  <- ties the run at blk 40: tie-break
#   blk 64   row 10
#   EOF at block 65
#
# SIZE ORDER AND ADDRESS ORDER DISAGREE ON PURPOSE -- 2, 8, 24, 4, 12, 1, 4 down
# the file. The first version of this fixture laid the runs out largest-first by
# address, which happens to be what the broken code produced, so the check that
# free_runs answers in address order could not fail. It passed against the old
# planner. A check that cannot fail is not a check, and that one was not.
MFT_BLOCK = 14
FILE_SIZE = 65 * BLOCK

RUN_BIG, RUN_MID = 15, 45           # the two container runs, by start block
RUN_8, RUN_4A, RUN_4B, RUN_2, RUN_1 = 6, 40, 60, 3, 58
DESIGNED_RUNS = [(RUN_2, 2), (RUN_8, 8), (RUN_BIG, 24), (RUN_4A, 4),
                 (RUN_MID, 12), (RUN_1, 1), (RUN_4B, 4)]
USABLE_RUNS = [(RUN_2, 2), (RUN_8, 8), (RUN_4A, 4), (RUN_1, 1), (RUN_4B, 4)]

SHADOW_MFT_COUNT = 18               # a plausible earlier generation
SHADOW_TBL_BLOCK = RUN_MID + 6      # six blocks into the run, not at its head
SHADOW_TBL_BLOCKS = 2

ROW_HEADER, ROW_IDTABLE, ROW_SELF = 1, 2, 3
NEXT_ROW_AFTER_MFT = 6              # row 6 at blk 39, the next ALLOCATED entry
ROWS = {                            # past the table -- and 24 blocks of shadow
    ROW_HEADER:  (0, 32),           # MFT lie between the two.
    ROW_IDTABLE: (1, 16),           # two (file_id, row) pairs
    ROW_SELF:    (MFT_BLOCK, None),  # size filled in per fixture
    4:  (2, BLOCK),
    5:  (5, BLOCK),
    6:  (39, BLOCK),
    7:  (44, BLOCK),
    8:  (57, BLOCK),
    9:  (59, BLOCK),
    10: (64, BLOCK),
}
LAST_USED_ROW = 10

# Two fixtures, identical on disk except for the MFT's declared length.
#   A: 20 rows, so rows 11..19 are erased and an insert reuses row 16.
#   B: 11 rows, no erased row at all, so an insert appends and has to reason
#      about how far the table can grow -- which is the gap measure again.
COUNT_ERASED, COUNT_FULL = 20, 11


def pattern(seed, n):
    """Deterministic bytes, none of them 0x00."""
    return bytes(1 + ((i * 37 + seed * 101) % 255) for i in range(n))


def build_archive(path, entry_count):
    """Write a small, complete, self-checking archive with two shadow containers."""
    buf = bytearray(bytes([SLACK]) * FILE_SIZE)
    mft_size = entry_count * ENTRY_SIZE

    for row, (blk, size) in ROWS.items():
        if row in (ROW_HEADER, ROW_SELF):
            continue
        off = blk * BLOCK
        data = (struct.pack("<IIII", 0x1000, 4, 0x1001, 5)
                if row == ROW_IDTABLE else pattern(row, size))
        buf[off:off + size] = data

    # The shadow master file table, at the head of the largest run.
    off = RUN_BIG * BLOCK
    buf[off:off + 4] = MFT_MAGIC
    struct.pack_into("<I", buf, off + 0x0C, SHADOW_MFT_COUNT)

    # The shadow file-id table, deliberately NOT at its run's head. Every row it
    # names is <= LAST_USED_ROW, so it reads as a live table to both fixtures.
    off = SHADOW_TBL_BLOCK * BLOCK
    for i in range((SHADOW_TBL_BLOCKS * BLOCK) // 8):
        struct.pack_into("<II", buf, off + i * 8,
                         0x2000 + i * 3, 1 + (i % LAST_USED_ROW))

    head = bytearray(32)
    head[0:4] = FILE_MAGIC
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<I", head, 0x10, MFT_BLOCK * BLOCK)
    struct.pack_into("<I", head, 0x18, mft_size)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head

    mft = bytearray(mft_size)
    mft[0:4] = MFT_MAGIC
    struct.pack_into("<I", mft, 0x0C, entry_count)
    for row in range(1, entry_count):
        if row not in ROWS:
            continue                       # erased slot: 24 zero bytes
        blk, size = ROWS[row]
        size = mft_size if row == ROW_SELF else size
        off = blk * BLOCK
        crc = 0 if row in (ROW_HEADER, ROW_SELF) else \
            binascii.crc32(bytes(buf[off:off + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         off, size, 0, 3, 0, crc)
    buf[MFT_BLOCK * BLOCK:MFT_BLOCK * BLOCK + mft_size] = mft

    with open(path, "wb") as fh:
        fh.write(bytes(buf))


def fresh(tmp, name, entry_count):
    path = os.path.join(tmp, name)
    build_archive(path, entry_count)
    return path


def rendered(plan):
    """plan.show()'s output as text. What a human actually reads."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        plan.show(BLOCK)
    return buf.getvalue()


def old_policy(runs, need):
    """The line this file exists to refute, restated exactly.

        runs.sort(key=lambda r: -r[1])
        fit = next((r for r in runs if r[1] >= need), None)

    Kept here rather than in datplan so the comparison is against what the old
    code did, not against whatever the new code has been refactored into.
    """
    ordered = sorted(runs, key=lambda r: -r[1])
    return next((r for r in ordered if r[1] >= need), None)


def sections(tmp):
    dat = fresh(tmp, "planner-a.dat", COUNT_ERASED)

    print("\n0. the fixture is a real archive (or nothing below measures anything)")
    with Archive(dat) as ar:
        check(ar.entry_count == COUNT_ERASED and ar.block_size == BLOCK
              and ar.mft_offset == MFT_BLOCK * BLOCK,
              f"opens: {ar.entry_count} rows, block {ar.block_size}, "
              f"MFT at 0x{ar.mft_offset:X}")
        runs = datplan.free_runs(ar)
        check(runs == DESIGNED_RUNS,
              f"free_runs finds the {len(DESIGNED_RUNS)} designed runs IN ADDRESS "
              f"ORDER", f"got {runs}")
        check(sum(n for _, n in runs) * BLOCK == 28160,
              f"28160 bytes unallocated by the gap measure "
              f"(got {sum(n for _, n in runs) * BLOCK})")

        print("\n1. the two container signatures, and what must NOT trip them")
        def head(blk):
            ar.fh.seek(blk * BLOCK)
            return ar.fh.read(datplan.CONTAINER_PROBE_BYTES)
        sig = datplan.container_signature(head(RUN_BIG), ar.entry_count)
        check(sig is not None and sig[0] == "master file table"
              and str(SHADOW_MFT_COUNT) in sig[1],
              f"Mft magic at the largest run's head is named", f"{sig}")
        sig = datplan.container_signature(head(SHADOW_TBL_BLOCK), ar.entry_count)
        check(sig is not None and sig[0] == "file-id table",
              f"a stretch of (file_id, row) pairs is named", f"{sig}")
        check(datplan.container_signature(head(RUN_8), ar.entry_count) is None,
              "ordinary slack is not a container")
        check(datplan.container_signature(head(RUN_MID), ar.entry_count) is None,
              "the mid-run container's OWN run reads clean at its head -- a "
              "head-only test would hand this run to a writer")

        print("\n2. classification withholds both runs, head or not")
        usable, excluded = datplan.classify_runs(ar)
        by_start = {x.start_block: x for x in excluded}
        # marks_of, not by_start[...], in the DETAIL strings: a detail is built
        # before check() is called, so indexing a key the subject failed to
        # produce kills the run instead of reporting it. That is the failure mode
        # checks.py exists to refuse, and the first version of this file had it --
        # against the old planner it raised KeyError rather than printing [FAIL].
        def marks_of(start):
            x = by_start.get(start)
            return [m[0] for m in x.marks] if x else "run not withheld at all"
        check(sorted(by_start) == [RUN_BIG, RUN_MID],
              f"exactly the two container runs are withheld",
              f"got {sorted(by_start)}")
        check(RUN_BIG in by_start and by_start[RUN_BIG].marks[0][0] == 0,
              "the largest run is withheld on a mark at its head",
              f"marks at blocks {marks_of(RUN_BIG)}")
        check(RUN_MID in by_start and by_start[RUN_MID].marks[0][0] == 6,
              "the 12-block run is withheld on a mark 6 blocks in -- the case a "
              "head test misses",
              f"marks at blocks {marks_of(RUN_MID)}")
        check(usable == USABLE_RUNS,
              f"the {len(USABLE_RUNS)} remaining runs are usable, still in "
              f"address order", f"got {usable}")
        withheld_b = sum(x.blocks for x in excluded) * BLOCK
        usable_b = sum(n for _, n in usable) * BLOCK
        check(withheld_b == 36 * BLOCK and usable_b == 19 * BLOCK
              and withheld_b + usable_b == 28160,
              f"accounting closes: {withheld_b} withheld + {usable_b} usable "
              f"= 28160")

        print("\n3. placement is best fit, not first fit of a largest-first list")
        plan = datplan.plan_insert(ar, 1200, classified=(usable, excluded))
        payload = [e for e in plan.edits if e.what == "payload"]
        check(len(payload) == 1 and payload[0].offset == RUN_4A * BLOCK,
              f"a 3-block payload goes to the SMALLEST qualifying run "
              f"(0x{RUN_4A * BLOCK:X}, 4 blocks), not the 8-block one",
              f"got 0x{payload[0].offset:X}" if payload else "no payload edit")
        plan = datplan.plan_insert(ar, 1024, classified=(usable, excluded))
        payload = [e for e in plan.edits if e.what == "payload"]
        check(len(payload) == 1 and payload[0].offset == RUN_2 * BLOCK,
              f"a 2-block payload takes the exact fit at 0x{RUN_2 * BLOCK:X}",
              f"got 0x{payload[0].offset:X}" if payload else "no payload edit")
        plan = datplan.plan_insert(ar, 100, classified=(usable, excluded))
        payload = [e for e in plan.edits if e.what == "payload"]
        check(len(payload) == 1 and payload[0].offset == RUN_1 * BLOCK,
              f"a 1-block payload takes the 1-block run at 0x{RUN_1 * BLOCK:X}",
              f"got 0x{payload[0].offset:X}" if payload else "no payload edit")
        check(datplan.best_fit([(RUN_4B, 4), (RUN_4A, 4)], 3) == (RUN_4A, 4),
              "equal-sized runs tie-break to the lower address, whatever order "
              "they arrive in")

        print("\n4. the old policy picked a container -- the refutation")
        need = datplan.blocks_for(1200, BLOCK)
        old = old_policy(runs, need)
        check(old == (RUN_BIG, 24),
              f"largest-first + first-fit chooses the 24-block run at "
              f"0x{RUN_BIG * BLOCK:X}", f"got {old}")
        check(old is not None and old[0] in by_start,
              "and that run is one the classifier withholds -- so this test goes "
              "red against the planner as it stood")
        check(max(n for _, n in runs) > max(n for _, n in usable),
              f"the largest run in the archive ({max(n for _, n in runs)} blocks) "
              f"is bigger than the largest usable one "
              f"({max(n for _, n in usable)}), which is what made first-fit-of-"
              f"largest aim at the container every time")

        print("\n5. the plan says what it withheld")
        plan = datplan.plan_insert(ar, 1200, classified=(usable, excluded))
        check(len(plan.excluded) == 2,
              f"the plan carries both withheld runs ({len(plan.excluded)})")
        text = rendered(plan)
        check("withheld 2 run(s)" in text and f"{36 * BLOCK} bytes" in text,
              "show() reports the count and the byte total it refused to use")
        check(f"0x{RUN_BIG * BLOCK:012X}" in text
              and f"0x{RUN_MID * BLOCK:012X}" in text,
              "and names both runs by offset")
        check("master file table" in text and "file-id table" in text
              and "at its head" in text and "6 blocks in" in text,
              "with what was found in each and where")

        print("\n6. nothing fits: blocked, not quietly placed in a container")
        plan = datplan.plan_insert(ar, 5000, classified=(usable, excluded))
        check(bool(plan.blockers) and not plan.edits,
              f"a 10-block payload is BLOCKED and plans no edits "
              f"({len(plan.edits)} edit(s))")
        check(any("WOULD have fit" in b for b in plan.blockers),
              "the blocker says withheld runs would have taken it",
              "; ".join(plan.blockers))
        check("withheld 2 run(s)" in rendered(plan),
              "and the blocked plan still prints them -- the exclusions are "
              "exactly what a reader needs when the answer is 'no'")

    print("\n7. the MFT's headroom is the gap measure too (no erased rows)")
    dat_b = fresh(tmp, "planner-b.dat", COUNT_FULL)
    with Archive(dat_b) as ar:
        check(datplan.free_rows(ar) == [],
              "fixture B has no claimable erased row, so an insert must append")
        plan = datplan.plan_insert(ar, 1200)
        appended = [e for e in plan.edits if "appended" in e.what]
        check(len(appended) == 1, "the plan appends a row rather than reusing one")
        mft_end = ar.mft_offset + ar.mft_size
        wall = RUN_BIG * BLOCK
        note = " ".join(plan.notes)
        check(f"{(wall - mft_end) // ENTRY_SIZE} more rows" in note
              and f"0x{wall:X}" in note,
              f"growth is measured to the container at 0x{wall:X} "
              f"({(wall - mft_end) // ENTRY_SIZE} rows), not to the next "
              f"allocated entry", note)
        gap_rows = (ROWS[NEXT_ROW_AFTER_MFT][0] * BLOCK - mft_end) // ENTRY_SIZE
        check(f"{gap_rows} more rows" not in note,
              f"and NOT the {gap_rows} rows the gap-between-reservations measure "
              f"claims by counting the shadow generation as headroom")

    print("\n8. every 'MFT row N' edit lands on row N -- three of four did not")
    # THE DEFECT THIS SECTION EXISTS FOR, in a tool whose entire output is bytes
    # a human applies BY HAND. `datplan` carried its own row arithmetic and got
    # it wrong at three of its four MFT sites:
    #
    #   plan_overwrite  mft_offset + (row - 1) * 24  -> row N-1, printed on the
    #                                                   line AFTER a payload
    #                                                   edit that named row N
    #                                                   correctly
    #   plan_insert     (MFT_SELF_ROW - 1) * 24      -> row 2, the FILE-ID
    #                                                   TABLE, labelled "row 3"
    #   plan_insert     1 * ENTRY_SIZE               -> row 1, the FILE HEADER,
    #                                                   labelled "row 2"
    #
    # MEASURED on the real 4.2 GB archive before the fix: `--overwrite 46196`
    # put its MFT edit at 0xF8CFE8C8 where `datwrite.row_offset` says
    # 0xF8CFE8E0, and `--insert` aimed its "row 3" edit at 0xF8BEFE30 where row
    # 3 is at 0xF8BEFE48. Nothing errored, the two conventions appeared in one
    # plan with nothing to tell them apart, and this file was GREEN at 30
    # checks -- because it asserted the placement POLICY and never once asked
    # where an edit pointed.
    #
    # The claim is deliberately NOT "the arithmetic matches `mft_row_offset`",
    # which would only compare the module against the function it now calls.
    # Every address is resolved to the 24 BYTES THE FIXTURE WROTE THERE, by a
    # reader written in this file, over every plan the module can produce.
    def rows_at(dat, mft_offset, offset):
        """Which row(s) of the raw table carry the 24 bytes sitting at `offset`."""
        with open(dat, "rb") as fh:
            fh.seek(offset)
            want = fh.read(ENTRY_SIZE)
            fh.seek(mft_offset)
            table = fh.read(os.path.getsize(dat) - mft_offset)
        return [i for i in range(len(table) // ENTRY_SIZE)
                if table[i * ENTRY_SIZE:(i + 1) * ENTRY_SIZE] == want]

    def mft_edits(plan):
        """(row, offset) for every edit whose own label names an MFT row."""
        return [(int(m.group(1)), e.offset) for e in plan.edits
                for m in [re.match(r"MFT row (\d+)\b", e.what)] if m]

    for label, path, count in (("A (reuses an erased row)", dat, COUNT_ERASED),
                               ("B (appends a row)", dat_b, COUNT_FULL)):
        with Archive(path) as ar:
            plans = [datplan.plan_insert(ar, 1200, file_id=0x3000),
                     datplan.plan_overwrite(ar, LAST_USED_ROW, 100),
                     datplan.plan_overwrite(ar, ROW_IDTABLE, 8)]
            edits = [pair for p in plans for pair in mft_edits(p)]
            named = sorted({r for r, _ in edits})
            wrong = [(r, off) for r, off in edits
                     if off != ar.mft_offset + r * ENTRY_SIZE]
            check(len(edits) >= 4 and not wrong,
                  f"fixture {label}: all {len(edits)} 'MFT row N' edits, over "
                  f"rows {named}, land at mft_offset + N*24",
                  f"wrong: {[(r, hex(o)) for r, o in wrong]}")

            # IDENTITY, not arithmetic. A row the fixture actually WROTE is
            # unique in the table, so matching its 24 bytes pins the row without
            # asking either module where it thinks the row is. Appended and
            # erased rows are all-zero and match in many places, so they are
            # left to the arithmetic check above and said so here.
            real = [(r, off) for r, off in edits if r in ROWS and r <= count - 1]
            landed = [(r, rows_at(path, ar.mft_offset, off)) for r, off in real]
            check(real and all(hits == [r] for r, hits in landed),
                  f"and each of the {len(real)} edits naming a row the fixture "
                  f"WROTE finds exactly that row's bytes there",
                  f"{[(r, h) for r, h in landed if h != [r]]}")

            # THE CONTROL: the expression datplan shipped. It has to land on a
            # DIFFERENT row for every one of them, or the right answer and the
            # wrong one are indistinguishable here and the section proves
            # nothing.
            shifted = [(r, rows_at(path, ar.mft_offset,
                                   ar.mft_offset + (r - 1) * ENTRY_SIZE))
                       for r, _ in real]
            check(shifted and all(hits == [r - 1] for r, hits in shifted),
                  f"while the `(row - 1) * 24` datplan shipped finds row N-1's "
                  f"bytes for all {len(shifted)} of them -- the file-id table "
                  f"where it said the MFT, the file header where it said the "
                  f"table", f"{[(r, h) for r, h in shifted if h != [r - 1]]}")

    # And the bound at both ends. `plan_overwrite(ar, 0, ...)` reached
    # `entries[-1]` and planned a real overwrite of the LAST row of the table;
    # the CLI's own `row <= entry_count` was one too loose at the other end,
    # since `entry_count` counts the descriptor.
    with Archive(dat) as ar:
        refused = [datplan.plan_overwrite(ar, r, 8)
                   for r in (0, -1, ar.row_count, ar.row_count + 1)]
        # "no such row", not merely "some blocker". Under the pre-fix code row 0
        # reached `entries[-1]` -- an ERASED slot with a 0-byte reservation --
        # and was refused for not FITTING it, which produces a blocker and no
        # edits and satisfies the obvious predicate. That was this check's first
        # version and the sabotage passed it, 0 red. The bound has to be refused
        # AS a bound, or a fixture whose last row happened to be roomy would let
        # a write to it straight through.
        check(all(p.blockers and not p.edits
                  and any("no such row" in b for b in p.blockers)
                  for p in refused),
              f"rows 0, -1, {ar.row_count} and {ar.row_count + 1} are refused "
              f"AS OUT OF RANGE with no edits -- row 0 used to reach "
              f"entries[-1] and address the LAST row of the table",
              f"{[(len(p.edits), p.blockers[0][:30]) for p in refused]}")
        ok = datplan.plan_overwrite(ar, LAST_USED_ROW, 8)
        check(bool(ok.edits) and not ok.blockers,
              f"and row {LAST_USED_ROW} is still planned -- a bound that "
              f"refused everything would protect nothing, because the tool "
              f"would then never run")


def section_extent_projection(tmp):
    """A generation's DECLARED EXTENT crosses run boundaries. The mark does not.

    `scan_run` finds the block a signature SITS on. An MFT header then says how
    far the table REACHES, at +0x0C. If it reaches past the end of the free run
    it started in, the next run along is the MIDDLE of that table: no magic at
    any of its own block boundaries, so a signature-only classifier scores it
    usable and `best_fit` hands a writer the inside of a live generation.

    studies/archivewrite/FINDINGS.md 1.5 measured exactly this on the 38833
    study copy -- a 2,892,800-byte run lying 100.0% inside a stale generation's
    declared extent, accepted by `plan_move`. That archive is a different build
    pin and is not a fixture this suite may depend on, so the case is built
    here instead, on the bare-machine fixture: it is a property of the
    classifier, not of one copy of the game.
    """
    print("\n9. a declared extent is projected across run boundaries")
    path = fresh(tmp, "projection.dat", COUNT_ERASED)

    # RUN_8 is 8 blocks at block 6 and reads clean today. Plant an MFT header
    # at its LAST block declaring a table far longer than the run it sits in,
    # so the extent runs off the end of RUN_8 and over RUN_4A at block 40.
    last = RUN_8 + 7
    reach_blocks = (RUN_4A + 2) - last            # past RUN_4A's head
    count = reach_blocks * BLOCK // ENTRY_SIZE
    desc = bytearray(BLOCK)
    desc[0:4] = datplan.MFT_MAGIC
    struct.pack_into("<I", desc, datplan.MFT_HDR_COUNT, count)
    with open(path, "r+b") as fh:
        fh.seek(last * BLOCK)
        fh.write(bytes(desc))

    with Archive(path) as ar:
        usable, excluded = datplan.classify_runs(ar)
        starts = sorted(x.start_block for x in excluded)
        usable_starts = [s for s, _n in usable]

        check(RUN_8 in starts,
              "the run CARRYING the header is withheld, as it always was",
              f"withheld {starts}")
        check(RUN_4A not in usable_starts,
              "and the NEXT run is withheld too, though it carries no "
              "signature of its own -- this is the whole fix",
              f"usable {usable_starts}")

        by_start = {x.start_block: x for x in excluded}
        reached = by_start.get(RUN_4A)
        check(reached is not None
              and "no signature here" in reached.marks[0][2],
              "and its exclusion SAYS it was reached rather than marked",
              reached.marks[0][2][:60] if reached else "not withheld")

        # The controls. A projection that swallowed everything downstream would
        # protect nothing, so the runs BEYOND the extent must survive, and the
        # run BEFORE it must too -- the claim is one-directional.
        check(RUN_4B in usable_starts and RUN_1 in usable_starts,
              "CONTROL: runs past the declared extent are still usable",
              f"usable {usable_starts}")
        check(RUN_2 in usable_starts,
              "CONTROL: a run BEFORE the header is untouched -- a table is "
              "claimed forward from its header, never backward")

    # And the classifier must not have changed on the untouched fixture: the
    # projection may only ever ADD exclusions that a real extent justifies.
    clean = fresh(tmp, "projection-control.dat", COUNT_ERASED)
    with Archive(clean) as ar:
        usable, _exc = datplan.classify_runs(ar)
        check(usable == USABLE_RUNS,
              "CONTROL: with no crossing extent the classification is "
              "unchanged", f"got {usable}")


def main():
    tmp = tempfile.mkdtemp(prefix="rurik-datplan-")
    print(f"synthetic archive: {FILE_SIZE} B, {len(DESIGNED_RUNS)} free runs, "
          f"2 shadow containers, in {tmp}")
    try:
        sections(tmp)
        section_extent_projection(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
