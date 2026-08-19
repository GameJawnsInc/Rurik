"""Move a row somewhere it fits. The verb `datwrite` refuses on purpose.

`datwrite --replace` writes a new payload into a row's EXISTING reservation and
refuses anything larger -- "that is a relocation, not a replacement" -- which is
the right refusal for a tool whose invariant is "same length, same offset, same
row". This module is the other tool, and it exists because that refusal turned
out to be the wall in front of authoring rather than anything about the client.

FINDINGS 38 compiled a navmesh over terrain we wrote, and it ran on a 32x32 map
for one reason: `datwrite` writes UNCOMPRESSED, so an authored stream only fits
where it is SMALLER than what ArenaNet compressed into that row. Map 143's own
64x64 Stripped file is 12,495 B against a 4,608-byte reservation. The first
design of that experiment died on exactly this and is recorded in its
PREDICTION.md. So: either compress the way the archive does, or move the row.
This is the second, and it is the half that can be judged without a client.

    python toolkit/mapdata/datmove.py --dat COPY --row 71497 --data new.bin --plan
    python toolkit/mapdata/datmove.py --dat COPY --row 71497 --data new.bin --move --confirm

WHAT MAKES A MOVE SAFE, and every one of these is a refusal rather than a note:

  * **Placement comes from `datplan.classify_runs`, never from `free_runs`.**
    "Unallocated" means "no MFT row points here", which counts the client's live
    container generations as free space -- 89.6% of the gap measure on this
    machine's study copy. `datplan` withholds those whole, and this module takes
    only what it hands back. That is not a precaution, it is the difference
    between writing into a hole and writing into the MFT the client is about to
    rotate back onto.
  * **Best fit, and the run is taken whole.** `datplan.best_fit` picks the
    smallest run that fits; ties go to the lowest address so the same archive and
    the same request always plan the same way.
  * **A destination overlapping the source is REFUSED.** Growing a row in place
    into adjacent free blocks is legitimate and this declines it, because the
    zeroing step below would then erase part of what was just written and the
    ordering bug would be invisible in a green run. Say no rather than get the
    order right by luck.
  * **The old reservation is zeroed, journalled first.** Same reasoning as
    `datwrite.replace`: the bytes left behind are inside blocks the client's free
    map is now entitled to, and a journal that does not cover them cannot notice
    the client wrote there before a revert. It also leaves nothing to find.
  * **All four MFT fields move together** -- offset, size, compression, crc --
    plus the table's self-crc. Getting three of four right looks exactly like a
    malformed payload from the client's side.
  * **The compression code is DECLARED, and the declaration is checked against
    the bytes.** Default 0, which is what this verb has always written and what
    every existing caller depends on. `--compression 8` requires `--expect`, and
    the bytes are decompressed and compared against it before anything is
    written. Relocating compressed bytes while marking the row stored --
    FINDINGS C-6, a green archive holding an unreadable file -- is now a loud
    refusal instead of a silent success. See `move()` and
    `datwrite.declaration_fault`.

WHAT DOES NOT CHANGE, and it is worth knowing before reaching for this:

  * **The file-id table.** It maps file id -> ROW, and a move does not change a
    row's index, so nothing addressable by id needs touching. That is why this is
    a smaller operation than `datplan.plan_insert`.
  * **`nextStream`.** A map's two rows are chained by row index, not by offset,
    so moving either end leaves the chain intact.
  * **The archive's length.** This never grows the file. When nothing fits, it
    says how short it is and stops.

THE CAPACITY LIMIT IS REAL AND IS REPORTED. `datplan.classify_runs` measured
3,367,936 usable bytes in 208 runs on the study copy, largest **953,856** -- and
176 of the archive's 349 map rows are bigger than that. **For half the maps in
the archive the honest answer to "where does this go" is nowhere**, and a plan
that cannot place a payload prints the largest usable run beside what was asked
for rather than a bare failure.

WHAT THIS DOES NOT ESTABLISH. **No client has ever read a row this module
moved.** Every claim here is about the archive's own rules -- the three checksum
rules, 512-byte alignment, whole-block reservations, and no two rows' extents
overlapping -- which `test_datcrc.py` pins against the corpus and `test_datmove.py`
re-derives independently. Whether the client accepts a relocated row is exactly
the kind of question `datplan`'s docstring separates out and refuses to answer on
paper. It is one caged run away and has not been made.
"""

import argparse
import binascii
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import Archive, ENTRY_SIZE  # noqa: E402
import datplan  # noqa: E402
import datwrite  # noqa: E402

ENTRY_OFFSET_OFF = 0x00      # u64 -- the whole point of this module
ENTRY_SIZE_OFF = 0x08        # u32
ENTRY_COMP_OFF = 0x0C        # u16
ENTRY_FLAGS_OFF = 0x0E       # u16
ENTRY_CRC_OFF = 0x14         # u32


class Refused(Exception):
    """A move that will not happen, with the reason a person needs."""


class MovePlan:
    """Where a row would go, and every byte that would change. Nothing written."""

    __slots__ = ("row", "old_offset", "old_size", "old_reservation",
                 "new_offset", "new_size", "new_reservation", "block",
                 "usable_runs", "largest_usable", "excluded")

    def __init__(self, row, old_offset, old_size, old_reservation,
                 new_offset, new_size, new_reservation, block,
                 usable_runs, largest_usable, excluded):
        self.row = row
        self.old_offset = old_offset
        self.old_size = old_size
        self.old_reservation = old_reservation
        self.new_offset = new_offset
        self.new_size = new_size
        self.new_reservation = new_reservation
        self.block = block
        self.usable_runs = usable_runs
        self.largest_usable = largest_usable
        self.excluded = excluded

    def show(self):
        print(f"row {self.row}")
        print(f"  from  0x{self.old_offset:X}  {self.old_size} B "
              f"(reservation {self.old_reservation})")
        print(f"  to    0x{self.new_offset:X}  {self.new_size} B "
              f"(reservation {self.new_reservation})")
        print(f"  frees {self.old_reservation} B at the old address; "
              f"takes {self.new_reservation} B at the new one")
        print(f"  free space: {self.usable_runs} usable run(s), largest "
              f"{self.largest_usable} B; {len(self.excluded)} run(s) withheld "
              f"by datplan (container generations)")


def reservation_for(size, block):
    """Whole blocks, size rounded up. A zero-size row reserves nothing."""
    return -(-size // block) * block


def row_entry(ar, row):
    for e in ar.entries:
        if e.index == row:
            return e
    raise Refused(f"no MFT row {row} in this archive")


def plan_move(ar, row, payload_size):
    """Where row `row` would go to hold `payload_size` bytes. Read-only.

    Raises `Refused` for every case a move must not happen in, and each refusal
    names the number that would let the caller fix it.
    """
    block = ar.block_size
    e = row_entry(ar, row)
    old_res = reservation_for(e.size, block)
    new_res = reservation_for(payload_size, block)

    if payload_size <= old_res:
        raise Refused(
            f"row {row} already reserves {old_res} B and the payload is "
            f"{payload_size} B, so it fits where it is.\n"
            f"  Use `datwrite.py --replace {row}` -- it writes in place, moves "
            f"nothing, and is the tested path. Relocating a row that does not "
            f"need to move takes free space for no reason.")
    if payload_size == 0:
        raise Refused("a zero-length payload reserves nothing; there is nothing "
                      "to move it to")

    usable, excluded = datplan.classify_runs(ar)
    need_blocks = new_res // block
    pick = datplan.best_fit(usable, need_blocks)
    largest = max((n for _s, n in usable), default=0) * block
    if pick is None:
        raise Refused(
            f"nothing fits. Row {row} needs {new_res} B ({need_blocks} blocks) "
            f"and the largest run datplan will hand over is {largest} B.\n"
            f"  {len(excluded)} run(s) are withheld whole because they carry "
            f"live container generations; that is not a limit to work around.\n"
            f"  This archive cannot take the payload without growing, which "
            f"this module does not do.")

    start_block, _run_blocks = pick
    new_offset = start_block * block

    old_lo, old_hi = e.offset, e.offset + old_res
    new_lo, new_hi = new_offset, new_offset + new_res
    if new_lo < old_hi and old_lo < new_hi:
        raise Refused(
            f"the best-fit run at 0x{new_offset:X} overlaps row {row}'s own "
            f"reservation at 0x{e.offset:X}..0x{old_hi:X}.\n"
            f"  Growing a row in place into adjacent free blocks is a real and "
            f"reasonable thing to want; this refuses it rather than get the "
            f"write-then-zero ordering right by luck. Free a run elsewhere, or "
            f"write the in-place grow as its own verb with its own test.")

    return MovePlan(row, e.offset, e.size, old_res, new_offset, payload_size,
                    new_res, block, len(usable), largest, excluded)


def move(path, row, data, journal_path, confirm=False, plan=None,
         compression=0, expect=None, stored_lookalike_ok=False):
    """Do it. Returns the MovePlan that was carried out.

    Order is deliberate and is the one thing a reader should check: the payload
    goes to its new home FIRST, then the MFT is pointed at it, then the old
    reservation is zeroed. An interrupted run therefore leaves the row pointing
    at either the old bytes or the new ones and never at a hole.

    THE COMPRESSION CODE IS AN ARGUMENT AS OF 2026-08-18, and its default is the
    behaviour every existing caller depends on. This verb wrote `compression -> 0`
    UNCONDITIONALLY for its whole life, which is *coherent* for its designed use
    -- you hand it plaintext, it marks the row stored -- and is what
    `textwrite.py`, `deploy.py`'s subprocess and the six `a4stage*.py` staging
    scripts under `vault/research/archivewrite/` all rely on. None of them is
    edited. `a4stage5` drove eleven real rows through this path on a real 4.2 GB
    copy that the owner then launched.

    WHAT CHANGED IS THAT THE SILENT CASE IS NOW LOUD. Hand this a compression-8
    row's stored bytes to relocate them and, until today, it produced a **green
    archive holding an unreadable file**: the row is marked stored while its
    bytes are still compressed, the entry CRC is over the stored bytes and does
    not move, so all three checksum rules and all ten open-time rules still pass.
    That is studies/archivewrite/FINDINGS.md **C-6**, and the honest statement of
    it was always *"no safe relocation verb exists for compressed rows"* rather
    than *"datmove corrupts archives today"*. Nobody could reach it, because
    until `gwenc.py` existed nothing in this project could produce compression-8
    bytes. Now they can, so both halves are closed here: the declaration is
    checked against the bytes (`datwrite.declaration_fault`), and the safe
    relocation verb is `compression=8` with the payload it must decompress to.

    The check runs before `Refused("refusing to write without --confirm")` on
    purpose: a `--plan` run should report a bad declaration rather than pass and
    then fail on the real invocation.
    """
    datwrite.guard(path)
    datwrite.guard_source(path)
    data = bytes(data)
    fault = datwrite.declaration_fault(data, compression, expect,
                                       stored_lookalike_ok)
    if fault:
        raise Refused(f"will not move row {row} as compression {compression}.\n"
                      f"  {fault}")
    with Archive(path) as probe:
        plan = plan or plan_move(probe, row, len(data))
    if not confirm:
        raise Refused("refusing to write without --confirm")

    w = datwrite.Writer(path, journal_path)
    try:
        image = data + b"\x00" * (plan.new_reservation - len(data))
        w.put(plan.new_offset, image,
              f"row {row} payload at its new home "
              f"({plan.new_reservation} B reservation)")
        base = datwrite.row_offset(w.ar, row)
        w.put(base + ENTRY_OFFSET_OFF, struct.pack("<Q", plan.new_offset),
              f"MFT row {row} offset 0x{plan.old_offset:X} -> "
              f"0x{plan.new_offset:X}")
        w.put(base + ENTRY_SIZE_OFF, struct.pack("<I", len(data)),
              f"MFT row {row} size {plan.old_size} -> {len(data)}")
        w.put(base + ENTRY_COMP_OFF, struct.pack("<H", compression),
              f"MFT row {row} compression -> {compression}"
              + (" (stored)" if compression == 0 else ""))
        w.set_entry_crc(row, binascii.crc32(data))
        # LAST, and only now that nothing points at it any more.
        w.put(plan.old_offset, b"\x00" * plan.old_reservation,
              f"row {row}'s old reservation ({plan.old_reservation} B), freed")
        w.fix_mft_self_crc()
    finally:
        w.close()
    return plan


def overlaps(ar):
    """Every pair of rows whose whole-block reservations intersect.

    The invariant a relocation can break and no checksum can see: the three crc
    rules all still verify across two rows sharing blocks. `test_datcrc.py`
    measures that no shipped row overlaps another; this is the same rule applied
    to an archive we just wrote to.

    Returns [(row_a, row_b, first_shared_offset)] in address order.
    """
    block = ar.block_size
    live = sorted(((e.offset, e.offset + reservation_for(e.size, block), e.index)
                   for e in ar.entries if e.size),
                  key=lambda t: t[0])
    bad = []
    for i in range(1, len(live)):
        plo, phi, prow = live[i - 1]
        lo, _hi, rowi = live[i]
        if lo < phi:
            bad.append((prow, rowi, lo))
    return bad


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", required=True, help="the archive COPY to work on")
    ap.add_argument("--row", type=int, required=True)
    ap.add_argument("--data", help="file holding the new payload")
    ap.add_argument("--plan", action="store_true", help="read-only")
    ap.add_argument("--move", action="store_true")
    ap.add_argument("--confirm", action="store_true",
                    help="required by --move; it writes to the archive")
    ap.add_argument("--journal", default=None)
    ap.add_argument("--compression", type=int, choices=(0, 8), default=0,
                    help="the compression code to MARK the moved row with "
                         "(default 0, stored -- what every caller of this tool "
                         "has always got). 8 requires --expect.")
    ap.add_argument("--expect", metavar="FILE",
                    help="the payload a reader must get back. MANDATORY with "
                         "--compression 8: the entry crc is over the STORED "
                         "bytes, so nothing can check a compressed row after "
                         "the move.")
    ap.add_argument("--check-overlaps", action="store_true",
                    help="read-only: no two rows may share a block")
    a = ap.parse_args(argv)

    if a.check_overlaps:
        with Archive(a.dat) as ar:
            bad = overlaps(ar)
        for pr, row, off in bad:
            print(f"  [FAIL] rows {pr} and {row} share blocks from 0x{off:X}")
        print(f"\n[{'FAIL' if bad else 'PASS'}] "
              f"{len(bad)} overlapping row pair(s)")
        return 1 if bad else 0

    if not a.data:
        ap.error("--data is required")
    if a.compression == 8 and not a.expect:
        ap.error("--compression 8 needs --expect FILE (the payload a reader "
                 "must get back). See datwrite.declaration_fault.")
    # --expect with --compression 0 is permitted and means something: for a
    # stored row the bytes ARE the payload, so passing it is the caller stating
    # that positively rather than switching a check off.
    with open(a.data, "rb") as fh:
        payload = fh.read()
    want = None
    if a.expect:
        with open(a.expect, "rb") as fh:
            want = fh.read()

    try:
        if a.plan or not a.move:
            fault = datwrite.declaration_fault(payload, a.compression, want)
            if fault:
                raise Refused(f"will not move row {a.row} as compression "
                              f"{a.compression}.\n  {fault}")
            with Archive(a.dat) as ar:
                plan_move(ar, a.row, len(payload)).show()
            print("\nnothing was written. Add --move --confirm to do it.")
            return 0
        journal = a.journal or (a.dat + f".move{a.row}.journal.json")
        plan = move(a.dat, a.row, payload, journal, confirm=a.confirm,
                    compression=a.compression, expect=want)
        print(f"\nmoved. journal: {journal}")
        print(f"revert with:\n  python toolkit/mapdata/datwrite.py "
              f"--revert {journal}")
        with Archive(a.dat) as ar:
            bad = overlaps(ar)
        print(f"[{'FAIL' if bad else 'PASS'}] "
              f"{len(bad)} overlapping row pair(s) afterwards")
        return 1 if bad else 0
    except Refused as exc:
        print(f"REFUSED: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(_main())
