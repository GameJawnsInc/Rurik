"""The relocation verb, against an archive this file builds.

WHY A FIXTURE AND NEVER A REAL ARCHIVE. Every question here is about free space
and where a writer is allowed to put things, and a real archive's free space is
whatever the client last left behind. A hand-laid one has runs of KNOWN sizes
with a KNOWN container generation in one of them, so "it took the 2-block run and
not the 6-block one" is a fact about the policy rather than about this machine's
copy. It also means this test needs no vault and runs on a bare machine.

THE LAYOUT, in 512-byte blocks. The gaps are the point:

    b0   row 1  file header
    b1   row 2  file-id table
    b2-3 row 4  1000 B, compression 8
    b4   row 5  300 B
    b5          FREE, 1 block
    b6   row 6  512 B  -- an exact fit, so it can never need moving
    b7-8        FREE, 2 blocks      <- best fit for a 2-block need
    b9   row 7  100 B
    b10-15      FREE, 6 blocks      <- the largest USABLE run
    b16  row 8  200 B
    b17-24      FREE, 8 blocks      <- carries an Mft magic: WITHHELD by datplan
    b25  row 9  400 B
    b26  row 3  the master file table itself

So the largest run in the archive is the one a writer may not have, which is the
shape the real archive has (89.6% of its gap-measured free space is container
generations) and is what makes the refusal in section 4 bite.

WHAT THE HEADLINE IS, and it is not "the payload came back". A relocation can
break one invariant that no checksum sees: two rows sharing blocks. All three crc
rules verify perfectly across an overlap, because each is computed over its own
row's bytes. So the load-bearing check is that after a move, NO two rows' whole-
block reservations intersect and EVERY other row still reads back byte-identical
-- and section 6 proves that check can fail, by corrupting an offset by hand and
requiring the walker to catch it. A "0 overlaps" that has never been shown to
report anything else is not a check.

The overlap walker in this file is written out of `int.from_bytes` and shares no
code with `datmove.overlaps`, for the same reason `test_datwrite.py` spells out
the self-crc rule instead of importing it.

    python toolkit/mapdata/test_datmove.py
"""

import binascii
import contextlib
import io
import os
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ENTRY_SIZE  # noqa: E402
import datmove  # noqa: E402
import datwrite  # noqa: E402
import checks  # noqa: E402

# FLOOR: 46, MEASURED from a green run on 2026-08-12, not guessed. Every section
# runs unconditionally -- the fixture is built here, so there is no corpus to be
# missing and nothing that can legitimately skip, and no vault is needed.
#
# Five sabotages were built and run against the module to find out which of these
# checks are load-bearing, and all five reddened: placing from `free_runs` instead
# of `classify_runs` (3 checks, all in section 4), largest fit instead of best fit
# (4), skipping the old-reservation zeroing (1 -- and only that one, which is why
# it is worth having), dropping the offset write (7) and dropping the entry crc
# (3).
LEDGER = checks.Ledger("dat move", floor=46)
check = checks.adopt(LEDGER)

FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"
ENTRY_CRC = 0x14

BLOCK = 512
NBLOCKS = 27
FILE_SIZE = NBLOCKS * BLOCK
MFT_BLOCK = 26
MFT_OFF = MFT_BLOCK * BLOCK
ENTRY_COUNT = 10
MFT_SIZE = ENTRY_COUNT * ENTRY_SIZE
SLACK = 0xCC

ROW_HEADER, ROW_IDTABLE, ROW_SELF = 1, 2, 3
ROW_BIG, ROW_MOVER, ROW_EXACT, ROW_SMALL, ROW_TINY, ROW_LAST = 4, 5, 6, 7, 8, 9

ROWS = {
    ROW_HEADER:  (0 * BLOCK, 32, 0, 3),
    ROW_IDTABLE: (1 * BLOCK, 16, 0, 3),
    ROW_SELF:    (MFT_OFF, MFT_SIZE, 0, 3),
    ROW_BIG:     (2 * BLOCK, 1000, 8, 3),
    ROW_MOVER:   (4 * BLOCK, 300, 0, 3),
    ROW_EXACT:   (6 * BLOCK, 512, 0, 3),
    ROW_SMALL:   (9 * BLOCK, 100, 0, 3),
    ROW_TINY:    (16 * BLOCK, 200, 0, 3),
    ROW_LAST:    (25 * BLOCK, 400, 0, 3),
}
PAYLOAD_ROWS = (ROW_IDTABLE, ROW_BIG, ROW_MOVER, ROW_EXACT, ROW_SMALL,
                ROW_TINY, ROW_LAST)

CONTAINER_BLOCK = 17          # where the fake Mft generation is planted
FREE_RUNS = {5: 1, 7: 2, 10: 6, 17: 8}
LARGEST_USABLE = 6 * BLOCK    # 3072 -- the 8-block run is withheld


def reservation(size):
    return -(-size // BLOCK) * BLOCK


def pattern(seed, n):
    return bytes(1 + ((i * 37 + seed * 101) % 255) for i in range(n))


def self_crc(mft):
    """Row 3's crc, spelled out rather than imported."""
    acc = binascii.crc32(bytes(mft[0x00:ROW_SELF * ENTRY_SIZE]))
    return binascii.crc32(
        bytes(mft[(ROW_SELF + 1) * ENTRY_SIZE:ENTRY_COUNT * ENTRY_SIZE]), acc)


def build_archive(path):
    buf = bytearray(bytes([SLACK]) * FILE_SIZE)
    payloads = {}
    for row in PAYLOAD_ROWS:
        off, size, _c, _f = ROWS[row]
        data = (struct.pack("<IIII", 0x1000, ROW_BIG, 0x1001, ROW_EXACT)
                if row == ROW_IDTABLE else pattern(row, size))
        buf[off:off + size] = data
        payloads[row] = data

    # The withheld run: an MFT magic at a block boundary is what datplan's
    # container_signature names. Planted deliberately so section 4's refusal is
    # about the rule and not about the archive being full.
    struct.pack_into("<I", buf, CONTAINER_BLOCK * BLOCK + 0x0C, ENTRY_COUNT)
    buf[CONTAINER_BLOCK * BLOCK:CONTAINER_BLOCK * BLOCK + 4] = MFT_MAGIC

    head = bytearray(32)
    head[0:4] = FILE_MAGIC
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<I", head, 0x10, MFT_OFF)
    struct.pack_into("<I", head, 0x18, MFT_SIZE)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head

    mft = bytearray(MFT_SIZE)
    mft[0:4] = MFT_MAGIC
    struct.pack_into("<I", mft, 0x0C, ENTRY_COUNT)
    for row in range(1, ENTRY_COUNT):
        off, size, comp, flags = ROWS[row]
        crc = 0 if row in (ROW_HEADER, ROW_SELF) else binascii.crc32(
            bytes(buf[off:off + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         off, size, comp, flags, 0, crc)
    struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + ENTRY_CRC, self_crc(mft))
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


# -- the independent readers. Nothing below imports from datmove. -----------

def read_mft_rows(path):
    """Every live row as (row, offset, size, comp, flags, crc), from the bytes."""
    raw = blob(path)
    mft_off = int.from_bytes(raw[0x10:0x14], "little")
    mft_size = int.from_bytes(raw[0x18:0x1C], "little")
    mft = raw[mft_off:mft_off + mft_size]
    count = int.from_bytes(mft[0x0C:0x10], "little")
    out = {}
    for row in range(1, count):
        b = mft[row * ENTRY_SIZE:(row + 1) * ENTRY_SIZE]
        out[row] = (int.from_bytes(b[0:8], "little"),
                    int.from_bytes(b[8:12], "little"),
                    int.from_bytes(b[12:14], "little"),
                    int.from_bytes(b[14:16], "little"),
                    int.from_bytes(b[20:24], "little"))
    return out


def overlapping_pairs(path):
    """Rows whose whole-block reservations intersect. Written from scratch."""
    rows = read_mft_rows(path)
    live = sorted((off, off + reservation(size), row)
                  for row, (off, size, _c, _f, _crc) in rows.items() if size)
    bad = []
    for i in range(1, len(live)):
        if live[i][0] < live[i - 1][1]:
            bad.append((live[i - 1][2], live[i][2]))
    return bad


def payload_of(path, row):
    raw = blob(path)
    off, size, _c, _f, _crc = read_mft_rows(path)[row]
    return raw[off:off + size]


def sections(tmp):
    print("\n0. the guards, both of them, and a control")
    for victim in (r"C:\gw\Gw.dat", os.path.join("x", "vault", "dat_study",
                                                 "Gw.dat")):
        ok, data = os.path.join(tmp, "g.dat"), b"x" * 4096
        build_archive(ok)
        try:
            datmove.move(victim, ROW_MOVER, data,
                         os.path.join(tmp, "g.json"), confirm=True)
            refused = False
        except SystemExit:
            refused = True
        except Exception:
            refused = False
        check(refused, f"move() refuses {victim}")

    dat0, _p = fresh(tmp, "confirm.dat")
    before0 = blob(dat0)
    try:
        with quiet():
            datmove.move(dat0, ROW_MOVER, b"z" * 2500,
                         os.path.join(tmp, "c.json"), confirm=False)
        refused = False
    except datmove.Refused:
        refused = True
    check(refused, "and refuses to write without --confirm")
    check(blob(dat0) == before0,
          "CONTROL: a refused move wrote nothing at all")

    print("\n1. the fixture is a real archive, with the free runs it claims")
    dat, payloads = fresh(tmp, "fixture.dat")
    with quiet():
        bad = datwrite.verify(dat) + datwrite.check_rows(dat, list(PAYLOAD_ROWS))
    check(bad == 0, "all three checksum rules hold on the fixture")
    check(overlapping_pairs(dat) == [],
          "and no two rows overlap to begin with")
    with Archive(dat) as ar:
        import datplan
        runs = dict(datplan.free_runs(ar))
        usable, excluded = datplan.classify_runs(ar)
    check(runs == FREE_RUNS,
          f"free runs are exactly as laid out  {runs} == {FREE_RUNS}")
    check(len(excluded) == 1 and excluded[0].start_block == CONTAINER_BLOCK,
          f"and datplan withholds the {FREE_RUNS[CONTAINER_BLOCK]}-block run "
          f"carrying the container generation")
    check(max(n for _s, n in usable) * BLOCK == LARGEST_USABLE,
          f"so the largest run a writer may have is {LARGEST_USABLE} B, not the "
          f"{FREE_RUNS[CONTAINER_BLOCK] * BLOCK} B the gap measure sees")

    print("\n2. the refusals that are not about space")
    with Archive(dat) as ar:
        try:
            datmove.plan_move(ar, ROW_EXACT, 400)
            refused, msg = False, ""
        except datmove.Refused as exc:
            refused, msg = True, str(exc)
    check(refused and "--replace" in msg,
          "a payload that fits the existing reservation is refused, and the "
          "message names datwrite --replace")
    with Archive(dat) as ar:
        try:
            datmove.plan_move(ar, 999, 4096)
            refused = False
        except datmove.Refused:
            refused = True
    check(refused, "an MFT row that does not exist is refused")

    print("\n3. best fit: the SMALLEST run that fits, not the biggest")
    with Archive(dat) as ar:
        plan = datmove.plan_move(ar, ROW_SMALL, 900)
    check(plan.new_reservation == 1024,
          f"900 B needs a 1024 B reservation  {plan.new_reservation}")
    check(plan.new_offset == 7 * BLOCK,
          f"and lands on the 2-block run at 0x{7 * BLOCK:X}, not the 6-block "
          f"one at 0x{10 * BLOCK:X}  (got 0x{plan.new_offset:X})")
    with Archive(dat) as ar:
        plan6 = datmove.plan_move(ar, ROW_MOVER, 2500)
    check(plan6.new_offset == 10 * BLOCK,
          f"a 6-block need takes the 6-block run  0x{plan6.new_offset:X}")

    print("\n4. the withheld run is not available, and that is the whole point")
    with Archive(dat) as ar:
        try:
            datmove.plan_move(ar, ROW_MOVER, 3500)
            refused, msg = False, ""
        except datmove.Refused as exc:
            refused, msg = True, str(exc)
    check(refused,
          "a payload needing 8 blocks is REFUSED even though an 8-block run "
          "exists -- it carries a container generation")
    check(str(LARGEST_USABLE) in msg,
          f"and the refusal states the largest run it may have ({LARGEST_USABLE})")
    check("container" in msg,
          "and says why the bigger one is off limits")
    with Archive(dat) as ar:
        try:
            datmove.plan_move(ar, ROW_MOVER, 60000)
            refused2 = False
        except datmove.Refused:
            refused2 = True
    check(refused2, "and a payload larger than the archive is refused too")

    print("\n5. the move itself")
    dat2, payloads2 = fresh(tmp, "move.dat")
    before = blob(dat2)
    new_payload = pattern(77, 900)
    jrnl = os.path.join(tmp, "move.journal.json")
    with quiet():
        done = datmove.move(dat2, ROW_SMALL, new_payload, jrnl, confirm=True)
    check(done.new_offset == 7 * BLOCK, "it went where the plan said")
    check(len(blob(dat2)) == FILE_SIZE, "the archive did not grow")

    rows_after = read_mft_rows(dat2)
    off, size, comp, flags, crc = rows_after[ROW_SMALL]
    check(off == 7 * BLOCK and size == 900,
          f"the MFT row now says 0x{off:X} / {size} B")
    check(off % BLOCK == 0, "and the new offset is block-aligned")
    check(comp == 0, "compression moved to 0 (stored) with it")
    check(crc == binascii.crc32(new_payload),
          "and the entry crc is over the new stored bytes")
    check(flags == ROWS[ROW_SMALL][3], "flags were left alone")
    check(payload_of(dat2, ROW_SMALL) == new_payload,
          "the payload reads back byte-identically at its new home")

    with quiet():
        bad = datwrite.verify(dat2) + datwrite.check_rows(
            dat2, [r for r in PAYLOAD_ROWS])
    check(bad == 0, "all three checksum rules still hold afterwards")

    tail = blob(dat2)[7 * BLOCK + 900:8 * BLOCK + 512]
    check(set(tail) == {0}, "the unused tail of the new reservation is zeroed")
    old = blob(dat2)[9 * BLOCK:9 * BLOCK + BLOCK]
    check(set(old) == {0},
          "and the whole OLD reservation is zeroed -- nothing left to find")

    print("\n6. the invariant no checksum sees, and proof the check can fail")
    check(overlapping_pairs(dat2) == [],
          "no two rows' reservations intersect after the move")
    survivors = [r for r in PAYLOAD_ROWS if r != ROW_SMALL]
    intact = [r for r in survivors if payload_of(dat2, r) == payloads2[r]]
    check(len(intact) == len(survivors),
          f"and every other row still reads back its own bytes  "
          f"{len(intact)}/{len(survivors)}")

    # The negative control. Point ROW_TINY at ROW_LAST's block by hand; the
    # crcs still all verify, and only the walker can tell.
    sab = os.path.join(tmp, "overlap.dat")
    shutil.copyfile(dat2, sab)
    raw = bytearray(blob(sab))
    struct.pack_into("<Q", raw, MFT_OFF + ROW_TINY * ENTRY_SIZE, 25 * BLOCK)
    with open(sab, "wb") as fh:
        fh.write(bytes(raw))
    check(overlapping_pairs(sab) != [],
          "CONTROL: an overlap planted by hand IS caught -- so the pass above "
          "is a measurement and not a tautology")

    print("\n7. revert puts the archive back exactly")
    with quiet():
        code = datwrite.revert(jrnl)
    check(code == 0, f"revert exits 0 (got {code})")
    check(blob(dat2) == before,
          "and the archive is byte-identical to before the move -- payload, "
          "old reservation, MFT and self-crc")

    print("\n8. a second move, on top of the first, still lands legally")
    dat3, payloads3 = fresh(tmp, "twice.dat")
    with quiet():
        datmove.move(dat3, ROW_SMALL, pattern(11, 900),
                     os.path.join(tmp, "m1.json"), confirm=True)
        datmove.move(dat3, ROW_MOVER, pattern(12, 2500),
                     os.path.join(tmp, "m2.json"), confirm=True)
    check(overlapping_pairs(dat3) == [],
          "two moves in a row leave no overlap")
    with quiet():
        bad = datwrite.verify(dat3) + datwrite.check_rows(dat3,
                                                          list(PAYLOAD_ROWS))
    check(bad == 0, "and all three checksum rules still hold")
    check(payload_of(dat3, ROW_SMALL) == pattern(11, 900)
          and payload_of(dat3, ROW_MOVER) == pattern(12, 2500),
          "both moved payloads read back")
    untouched = [r for r in PAYLOAD_ROWS if r not in (ROW_SMALL, ROW_MOVER)]
    check(all(payload_of(dat3, r) == payloads3[r] for r in untouched),
          f"and the {len(untouched)} rows that did not move are unchanged")
    check(read_mft_rows(dat3)[ROW_IDTABLE][0] == ROWS[ROW_IDTABLE][0],
          "the file-id table never moved: a row keeps its INDEX, so nothing "
          "addressable by file id needed touching")

    print("\n9. the CLI, and its exit codes")
    dat4, _p4 = fresh(tmp, "cli.dat")
    src = spill(tmp, "payload.bin", pattern(5, 900))
    with quiet() as out:
        rc = datmove._main(["--dat", dat4, "--row", str(ROW_SMALL),
                            "--data", src, "--plan"])
    check(rc == 0 and "nothing was written" in out.getvalue(),
          "--plan exits 0 and says it wrote nothing")
    check(blob(dat4) == blob(os.path.join(tmp, "fixture.dat")),
          "CONTROL: and really did not write -- byte-identical to a fresh one")
    # 400 B, not the 900 B above: ROW_EXACT reserves 512, so only a payload
    # that FITS makes this the fits-in-place refusal. The first version reused
    # the 900 B file, which legitimately needs moving, and the check failed for
    # the right reason on the wrong input.
    small = spill(tmp, "small.bin", pattern(6, 400))
    with quiet() as out:
        rc = datmove._main(["--dat", dat4, "--row", str(ROW_EXACT),
                            "--data", small, "--plan"])
    check(rc == 2 and "--replace" in out.getvalue(),
          f"a refusal exits 2, not 1 and not 0 (got {rc})")
    with quiet():
        rc = datmove._main(["--dat", dat4, "--row", str(ROW_SMALL),
                            "--data", src, "--move", "--confirm",
                            "--journal", os.path.join(tmp, "cli.json")])
    check(rc == 0, "--move --confirm exits 0")
    check(payload_of(dat4, ROW_SMALL) == pattern(5, 900),
          "and the payload is there")
    with quiet() as out:
        rc = datmove._main(["--dat", dat4, "--row", str(ROW_SMALL),
                            "--check-overlaps"])
    check(rc == 0 and "0 overlapping" in out.getvalue(),
          "--check-overlaps reports a clean archive")
    with quiet() as out:
        rc = datmove._main(["--dat", sab, "--row", str(ROW_SMALL),
                            "--check-overlaps"])
    check(rc == 1 and "0 overlapping" not in out.getvalue(),
          "CONTROL: and reports the planted one, exiting 1")


def main():
    tmp = tempfile.mkdtemp(prefix="rurik-datmove-")
    print(f"synthetic archive: {FILE_SIZE} B, {ENTRY_COUNT} rows, "
          f"free runs {FREE_RUNS}, in {tmp}")
    try:
        sections(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
