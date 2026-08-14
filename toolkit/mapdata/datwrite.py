"""Write to Gw.dat, reversibly, one experiment at a time.

This is the first tool in the project that opens the archive for writing, and
the sentence it exists to falsify is from the skills study: "no tool in our
entire evidence base can write to Gw.dat". datplan.py settled that the edit is
*computable*. Only a running client can settle whether it is *accepted*, and
this is what puts the bytes on disk so that question can be asked.

SAFETY, because this one can destroy 4 GB of somebody's game:

  - It refuses any path under C:\\gw. That install is the owner's and is
    read-only to this project, permanently.
  - Every byte it changes is journalled with its previous value before the
    write, so --revert restores the exact prior state without re-copying the
    archive. A 4.2 GB re-cut per arm is otherwise the only way back. A
    --replace journals its row's WHOLE block reservation, not just the bytes it
    puts there, because a shrinking replace frees blocks the client is free to
    take -- see Writer.replace().
  - --verify re-checks all three checksum rules and is the thing to run before
    and after every arm. test_datcrc.py asserts the same rules against the
    corpus; this checks one archive right now.
  - Nothing here relocates, resizes, or allocates. Same length, same offset,
    same row. Growing the archive is a different tool and a much later problem.

THE THREE CHECKSUM RULES, all MEASURED (see test_datcrc.py):

  entry crc  at entry+0x14  CRC-32/ISO-HDLC over the entry's STORED bytes --
                            the compressed form on disk, not the payload.
  header     at 0x0C        CRC-32 over the file header's first 12 bytes.
  MFT self   row 3's +0x14  CRC-32 over the table from 0x00 to 0x48, continued
                            over 0x60 to the end. The 24 bytes in between are
                            row 3 itself, which cannot cover its own crc field
                            and so is skipped.

    python toolkit/mapdata/datwrite.py --dat DAT --verify
    python toolkit/mapdata/datwrite.py --dat DAT --corrupt-crc 12345
    python toolkit/mapdata/datwrite.py --dat DAT --overwrite 12345 --data new.bin
    python toolkit/mapdata/datwrite.py --dat DAT --verify --replace 12345 --data new.bin
    python toolkit/mapdata/datwrite.py --dat DAT --revert journal.json

test_datwrite.py exercises all of the above against a small archive it builds
itself. Run it before trusting a write; it exists because three defects lived
here undetected, and none of the three could fail a checksum.
"""

import argparse
import binascii
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import (Archive, ENTRY_SIZE, file_id_table,  # noqa: E402
                     mft_row_offset, MFT_SELF_ROW)

LIVE_INSTALL = os.path.normcase(os.path.abspath(r"C:\gw"))

# MFT_SELF_ROW (3) is imported from `archive.py`, which owns the row convention.
SELF_ROW_START = MFT_SELF_ROW * ENTRY_SIZE          # 0x48
SELF_ROW_END = SELF_ROW_START + ENTRY_SIZE          # 0x60

ENTRY_SIZE_OFF = 0x08   # u32, the entry's stored length
ENTRY_COMP_OFF = 0x0C   # u16, 0 stored / 8 huffman
ENTRY_CRC = 0x14        # offset of the crc within a 24-byte MFT row
HDR_CRC = 0x0C          # offset of the crc within the 32-byte file header


def guard(path):
    """Never the live install. Not a warning; a refusal.

    Shared with `revert()`, which is exactly why `dat_study` is not here -- see
    `guard_source`.
    """
    p = os.path.normcase(os.path.abspath(path))
    if p == LIVE_INSTALL or p.startswith(LIVE_INSTALL + os.sep):
        raise SystemExit(
            f"Refusing to write inside the live install at {LIVE_INSTALL}.\n"
            f"  asked for: {path}\n"
            f"That install is read-only to this project. Point --dat at the "
            f"run-dir or study copy under vault/.")
    return p


def guard_source(path):
    """Never the pristine snapshot either. NEW edits only.

    `vault/dat_study` is the archive every other copy is cut from, and losing it
    means re-extracting from the owner's own install. `rebloat.guard_target()`
    has refused it since that tool existed, and its docstring says it "adds
    dat_study" to what datwrite refuses -- which was never true. This module is
    the one that opens the archive `r+b`, so the gap sat in front of the only
    write path there is. Found 2026-08-12 by an adversarial review of rung E3's
    runsheet, which had told a future operator the check existed.

    It is deliberately NOT in `guard()`, and that distinction is the design:
    `guard()` is also what `revert()` calls, and replaying a journal is the ONE
    legitimate write to `dat_study` -- it is how this mistake gets undone. A
    blanket refusal would close the recovery door behind the accident.

    Worth stating because no checksum catches it: `--replace` fixes the entry
    crc and the MFT self-crc as it goes, so a mutated snapshot passes
    `--verify`, passes `datcheck`, and reads as healthy everywhere.
    """
    parts = os.path.normcase(os.path.abspath(path)).replace("\\", "/").split("/")
    if "dat_study" in parts:
        raise SystemExit(
            f"Refusing to write to {path}\n"
            f"  vault/dat_study is the SOURCE snapshot every other copy is cut "
            f"from, and nothing in this repo can put it back -- losing it means "
            f"re-extracting from the owner's install.\n"
            f"  Point --dat at a copy under vault/run/ or vault/dat_*/ that you "
            f"can throw away.\n"
            f"  (--revert is still allowed there: undoing a mistaken write is "
            f"the one thing that should be.)")
    return path


def reservation_for(size, block):
    """Whole blocks, size rounded up. A zero-size row reserves nothing.

    Same expression as `datmove.reservation_for`; not imported, because
    `datmove` imports `datplan` which imports more, and this module is the one
    that must keep working when the rest of the tree does not.
    """
    return -(-size // block) * block


def claimants(ar, lo, hi, exclude):
    """Every OTHER live row whose reservation intersects [lo, hi).

    A row's reservation, not its size: the bytes between `size` and the end of
    the last block belong to that row even though nothing is stored in them, and
    a grow that took them would be corrupting a neighbour that still verifies.
    That is the invariant `test_datmove.py` was written around -- two rows
    sharing blocks is the one thing no checksum sees, because each crc covers
    only its own row's bytes.
    """
    out = []
    for e in ar.entries:
        if e.index == exclude or e.size == 0:
            continue
        o = e.offset
        h = o + reservation_for(e.size, ar.block_size)
        if o < hi and lo < h:
            out.append((o, h, e.index))
    out.sort()
    return out


class DonorRow:
    """What a donor archive says one row should contain. Read-only, always."""

    __slots__ = ("path", "row", "size", "compression", "crc", "flags",
                 "payload", "sha256", "file_ids", "image")

    def __init__(self, path, row, size, compression, crc, flags, payload,
                 file_ids, image):
        self.path, self.row, self.size = path, row, size
        self.compression, self.crc, self.flags = compression, crc, flags
        self.payload, self.file_ids = payload, file_ids
        self.sha256 = hashlib.sha256(payload).hexdigest()
        # The donor's WHOLE reservation, not just its payload. The bytes between
        # `size` and the end of the last block belong to the row, and a restore
        # that zero-filled them would put the row back "correctly" while leaving
        # it bytewise different from every pristine copy -- a difference that no
        # checksum sees and that would show up later as an unexplained diff.
        # Whether anything reads past the size field is UNTESTED (see replace()),
        # which is the argument for reproducing rather than inventing them.
        self.image = image


def read_donor(donor_path, row):
    """Row N's STORED bytes out of a donor archive.

    DELIBERATELY NOT GUARDED, and that is a decision rather than an oversight:
    `guard()` protects the thing being WRITTEN, and the owner's own install at
    C:\\gw is the canonical donor -- reading bytes from it is explicitly
    permitted and refusing it here would make the best source unusable. The
    donor is opened 'rb' and never anything else.

    The donor's own crc is checked against its payload before the caller is
    allowed to trust it. A donor that fails its own checksum is a worse source
    than the armed row it would replace.
    """
    with Archive(donor_path) as ar:
        e = ar.row(row)
        res = reservation_for(e.size, ar.block_size)
        ar.fh.seek(e.offset)
        image = ar.fh.read(res)
        payload = image[:e.size]
        if len(payload) != e.size:
            raise SystemExit(
                f"donor row {row} declares {e.size} bytes and only "
                f"{len(payload)} could be read from {donor_path}")
        if len(image) != res:
            # The last row in a file can end short of its reservation. Pad, and
            # say so, rather than silently restoring fewer bytes than claimed.
            print(f"  note: donor row {row}'s reservation runs {res - len(image)}"
                  f" B past EOF; the tail will be zero-filled")
            image = image + b"\x00" * (res - len(image))
        if e.size and binascii.crc32(payload) != e.crc:
            raise SystemExit(
                f"donor row {row} in {donor_path} FAILS ITS OWN CRC "
                f"(stored 0x{e.crc:08X}, computed "
                f"0x{binascii.crc32(payload):08X}). Refusing to restore from a "
                f"donor that is itself damaged.")
        ids = sorted(f for f, r in file_id_table(ar).items() if r == row)
        return DonorRow(donor_path, row, e.size, e.compression, e.crc, e.flags,
                        payload, ids, image)


def check_identity(target_path, row, donor):
    """The portable key: target row and donor row must NAME THE SAME FILE.

    A row index is a fact about the copy (`mapchunks.py`:117) -- 304 file ids
    changed row across the one update this project has measured. So a donor cut
    from a different build can hold a perfectly valid, perfectly wrong file at
    row N, and every checksum would agree afterwards.

    Refuses only when BOTH rows are addressable and the id sets are disjoint,
    because that is the only case where the archives positively disagree. When
    either row carries no file id the check cannot be made and this says so
    rather than implying it passed -- the alternative is a silent green from a
    check that never ran.
    """
    with Archive(target_path) as ar:
        ids = sorted(f for f, r in file_id_table(ar).items() if r == row)
    if not ids or not donor.file_ids:
        which = "target" if not ids else "donor"
        print(f"  WARNING: the {which} row {row} carries no file id, so the "
              f"identity check COULD NOT RUN. You are trusting the row number.")
        return None
    shared = set(ids) & set(donor.file_ids)
    if not shared:
        raise SystemExit(
            f"row {row} names a DIFFERENT FILE in the two archives:\n"
            f"    target {target_path}: "
            + ", ".join(hex(i) for i in ids) + "\n"
            f"    donor  {donor.path}: "
            + ", ".join(hex(i) for i in donor.file_ids) + "\n"
            f"  A row index is a fact about the copy. Restoring across this "
            f"would write a valid file into the wrong row and every checksum "
            f"would agree afterwards.")
    print(f"  identity: row {row} is file id "
          + ", ".join(hex(i) for i in sorted(shared)) + " in both archives")
    return sorted(shared)


def row_offset(ar, row):
    """Where row N's 24 bytes start. Row N sits at mft_offset + N*24.

    Delegates to `archive.mft_row_offset` so this and `datplan.py` cannot drift:
    the planner carried its own expression with a `- 1` in it and printed three
    wrong addresses for months while this one was right. One function now.
    """
    return mft_row_offset(ar.mft_offset, row)


def mft_self_crc(mft, entry_count):
    """Row 3's crc: the table, with row 3's own 24 bytes skipped.

    A checksum cannot cover the field it is stored in, so the row describing the
    table excludes itself. Reproduces exactly on both archives on this machine.
    """
    acc = binascii.crc32(mft[0x00:SELF_ROW_START])
    return binascii.crc32(mft[SELF_ROW_END:entry_count * ENTRY_SIZE], acc)


def read_mft(ar):
    ar.fh.seek(ar.mft_offset)
    return bytearray(ar.fh.read(ar.mft_size))


class Journal:
    """Every byte this run changes, with what was there before it.

    Written to disk BEFORE the archive is touched and flushed after each write,
    so an interrupted run still leaves a usable way back.

    It records the MFT's offset too, and that is not bookkeeping. Edits are
    stored as ABSOLUTE file offsets, and MEASURED 2026-08-06 the client
    relocates the master file table during ordinary play -- observed moving from
    0xF8FFF000 to 0xF940E200 and back again within one session, which looks like
    a double-buffer it alternates for crash safety. An MFT-field edit journalled
    at one location is meaningless at the other, so replaying it would write four
    bytes into whatever now occupies dead space and report success. Silent, and
    the archive would still verify, because the row it meant to fix was never
    touched. Hence the guard in revert().
    """

    def __init__(self, path, dat, mft_offset):
        self.path = path
        self.dat = dat
        self.mft_offset = mft_offset
        self.entries = []

    def record(self, offset, before, after, what):
        self.entries.append({
            "offset": offset,
            "length": len(before),
            "before": binascii.hexlify(bytes(before)).decode(),
            "after": binascii.hexlify(bytes(after)).decode(),
            "what": what,
        })
        self.flush()

    def flush(self):
        with open(self.path, "w") as fh:
            json.dump({"dat": self.dat, "mft_offset": self.mft_offset,
                       "edits": self.entries}, fh, indent=2)


class Writer:
    """An open archive plus the journal of what has been done to it.

    Constructing one is the statement of intent to write, so both refusals live
    here. `revert()` calls `guard()` directly and deliberately does not come
    through this constructor -- see `guard_source`.
    """

    def __init__(self, path, journal_path):
        guard(path)
        guard_source(path)
        self.path = path
        self.ar = Archive(path)
        self.fh = open(path, "r+b")
        self.journal = Journal(journal_path, os.path.abspath(path),
                               self.ar.mft_offset)

    def close(self):
        self.fh.close()
        self.ar.close()

    def read_mft(self):
        """The table as it stands ON DISK, through the handle that wrote it.

        Deliberately not the module-level read_mft(self.ar). The Archive's handle
        is a separate, buffered, read-only file object opened before any of our
        writes, and a seek back inside its current 8 KB window is answered from
        that buffer instead of from disk. It then hands back a PRE-WRITE copy of
        the table, fix_mft_self_crc() finds the old crc matching the old bytes,
        prints "already correct", and leaves the archive failing its own
        self-checksum with nothing said -- the one outcome this file is supposed
        to make impossible.

        Whether it happens depends on where the buffer window happens to fall: on
        the 4.2 GB archive the MFT is megabytes and misses it, on a small archive
        it does not. MEASURED 2026-08-10 on the synthetic archive in
        test_datwrite.py, where every replace left the self-crc wrong while
        reporting it already correct. A correctness property must not rest on
        which side of a buffer boundary the table happens to fall.
        """
        self.fh.seek(self.ar.mft_offset)
        return bytearray(self.fh.read(self.ar.mft_size))

    def put(self, offset, data, what):
        """One journalled write. Reads the old bytes first, always."""
        self.fh.seek(offset)
        before = self.fh.read(len(data))
        if len(before) != len(data):
            raise SystemExit(f"short read at 0x{offset:X}: wanted {len(data)} "
                             f"bytes, got {len(before)}")
        if before == bytes(data):
            print(f"  (no-op) 0x{offset:012X} +{len(data)} {what}")
            return
        self.journal.record(offset, before, data, what)
        self.fh.seek(offset)
        self.fh.write(bytes(data))
        self.fh.flush()
        os.fsync(self.fh.fileno())
        print(f"  wrote   0x{offset:012X} +{len(data)} {what}")

    def set_entry_crc(self, row, value):
        self.put(row_offset(self.ar, row) + ENTRY_CRC,
                 struct.pack("<I", value), f"MFT row {row} crc")

    def replace(self, row, new):
        """Put different bytes, of a different length, in an existing row.

        The one thing this will not do is relocate. Space is reserved in whole
        512-byte blocks, so a row owns ceil(size/512)*512 bytes whatever its
        size field says; anything that fits there can be written without moving
        a byte of anyone else's data. Anything that does not fit is a
        relocation, which is a different and much more dangerous operation, and
        this refuses it rather than half-doing it.

        Writes four things: the payload, the size field, the compression field
        and the crc. Getting three of four right looks exactly like a malformed
        payload from the client's side, which is why they are done together.

        THE WHOLE RESERVATION IS WRITTEN, not just the payload. That costs a
        multi-megabyte write on a big row and it is not optional, because a
        SHRINKING replace has two hazards that a payload-sized write cannot
        address and that no checksum can catch:

          * The journal would record only what was written. put() reads
            len(data) as its `before`, so replacing a 1.96 MB row with 20 KB
            captured 20 KB of history and no more. The client rederives its free
            list from the entry table at every open, and it is OBSERVED
            relocating and resizing live rows during ordinary play -- 8315 moved
            and grew 92 -> 96 bytes, 8316 moved, in one caged session
            (studies/datwrite/FINDINGS.md section 6). That study narrows it
            honestly: relocation has only ever been watched on the client's own
            scratch rows, never on a content row. It does not narrow it to safe.
            The blocks a shrink frees are blocks the allocator may take, and if
            it does, --revert puts back the first 20 KB, prints "restored",
            leaves all three checksum rules verifying, and the original payload
            is gone with nothing anywhere reporting a loss.
          * The old payload's tail would still be sitting inside this row's own
            reservation, immediately after the authored bytes. Whether any reader
            scans past the size field is UNTESTED, so the honest move is to leave
            nothing there to find.

        One journalled write settles both, and it is the only form in which the
        journal's `after` field can be told the truth: the reservation ends up
        holding exactly the payload followed by zeros, which is knowable before
        the write, so `before` and `after` describe the same range and --revert's
        "the client wrote here" detector covers the whole of it rather than the
        first few kilobytes.

        The tail is ours to write. Every entry offset is block-aligned and no
        extent runs into the next (test_datcrc.py sections 2 and 3), so the next
        row cannot begin before offset + reservation. Past the end of the file it
        is put()'s short-read guard that refuses, not this.
        """
        e = self.ar.row(row)
        block = self.ar.block_size
        reserved = -(-e.size // block) * block
        if len(new) > reserved:
            raise SystemExit(
                f"row {row} reserves {reserved} bytes ({e.size} used, "
                f"{block}-byte blocks) and the new payload is {len(new)}. "
                f"That is a relocation, not a replacement. Pick a row with a "
                f"bigger reservation -- datplan.py --free lists them.")
        image = bytes(new) + b"\x00" * (reserved - len(new))
        print(f"replacing row {row}: {e.size} -> {len(new)} bytes, "
              f"compression {e.compression} -> 0, at 0x{e.offset:X} "
              f"(reservation {reserved}, {reserved - len(new)} B of tail zeroed)")
        self.put(e.offset, image, f"row {row} reservation ({reserved} B)")
        self.put(row_offset(self.ar, row) + ENTRY_SIZE_OFF,
                 struct.pack("<I", len(new)),
                 f"MFT row {row} size {e.size} -> {len(new)}")
        if e.compression != 0:
            self.put(row_offset(self.ar, row) + ENTRY_COMP_OFF,
                     struct.pack("<H", 0),
                     f"MFT row {row} compression {e.compression} -> 0 (stored)")
        self.set_entry_crc(row, binascii.crc32(new))
        self.fix_mft_self_crc()

    def restore(self, row, donor, confirm=False):
        """Put a row back to what a DONOR archive says it should hold.

        THE VERB `datmove.plan_move` NAMES AND REFUSES. Its docstring ends
        "Free a run elsewhere, or write the in-place grow as its own verb with
        its own test"; this is that verb, narrowed to the case where the bytes
        come from another copy of the same archive rather than from a caller.

        WHY --replace CANNOT DO THIS, which is the whole reason it exists:

          * `--replace` writes COMPRESSION 0. An ArenaNet row is usually
            compression 8, and there is no compressor here. This copies the
            donor's STORED bytes verbatim, so the codec is never involved and
            the compression field is restored rather than flattened.
          * `--replace` computes the reservation from the row's CURRENT size, so
            a row that was shrunk can never be grown back -- 2,068 B gives it
            2,560 B of reservation when its original needs 7,680. The blocks were
            never handed to anyone, but `--replace` cannot see that. This
            computes the reservation from the DONOR and checks the difference is
            genuinely unclaimed.
          * `--overwrite` is same-length only.

        AND WHY A JOURNAL IS NOT ENOUGH, which is why the donor is an archive and
        not a `--data` file. `--revert` is the documented way back and it stops
        working for two independent reasons: the client moves the MFT, so MFT
        edits replay into dead space (see `Journal`), and a journal is a file
        somebody has to still have. MEASURED 2026-08-14: three skill-icon rows
        were left armed in `vault/run/reskin-roster/Gw.dat` on the recorded
        understanding that their payloads were "still recoverable from the
        journals' `before` fields", and **no journal for those rows exists in
        the vault**. A pristine copy is a better source than a journal because
        every checkout has one and it cannot go missing without the loss being
        obvious.

        IDENTITY IS BY FILE ID, never by row, because a row index is a fact about
        the copy (`mapchunks.py`:117). If both rows are file-id addressable the
        id sets must intersect or this refuses; a donor from a different build
        where row N is a different file is exactly what that catches.

        THE ONE HAZARD, stated rather than engineered around: an in-place grow
        overwrites the current payload before the size field moves, so an
        interrupted run leaves the row's size describing the old length over the
        new bytes. `datmove` avoids this by writing to a new location first; an
        in-place grow has nowhere else to put them. The journal is the way back
        and it is written before the first byte.
        """
        e = self.ar.row(row)
        block = self.ar.block_size
        old_res = reservation_for(e.size, block)
        new_res = reservation_for(donor.size, block)

        if donor.size == 0:
            raise SystemExit(f"donor row {row} is empty; there is nothing to "
                             f"restore from {donor.path}")
        if e.crc == donor.crc and e.size == donor.size \
                and e.compression == donor.compression:
            print(f"row {row} already matches the donor "
                  f"({donor.size} B, comp {donor.compression}, "
                  f"crc 0x{donor.crc:08X}) -- nothing to do")
            return False

        grow = new_res - old_res
        if grow > 0:
            lo, hi = e.offset + old_res, e.offset + new_res
            taken = claimants(self.ar, lo, hi, exclude=row)
            if taken:
                raise SystemExit(
                    f"row {row} needs to grow from {old_res} to {new_res} B in "
                    f"place, and [0x{lo:X}, 0x{hi:X}) is CLAIMED by "
                    + ", ".join(f"row {i} (0x{o:X}..0x{h:X})"
                                for o, h, i in taken) + ".\n"
                    f"  The blocks this row freed have been taken since. That is "
                    f"a relocation, not an in-place restore -- use datmove.py, "
                    f"which finds a free run and rewrites the offset.")
            print(f"  reclaiming [0x{lo:X}, 0x{hi:X}) = {grow} B, "
                  f"0 other rows claim it")

        if not confirm:
            raise SystemExit(
                f"would restore row {row} from {donor.path}:\n"
                f"    {e.size} B comp {e.compression} crc 0x{e.crc:08X}\n"
                f" -> {donor.size} B comp {donor.compression} "
                f"crc 0x{donor.crc:08X}\n"
                f"    reservation {old_res} -> {new_res} B at 0x{e.offset:X}\n"
                f"  Re-run with --confirm. This overwrites the current payload "
                f"before the size field moves; the journal is the way back.")

        image = donor.image
        print(f"restoring row {row} from {donor.path}: {e.size} -> {donor.size} "
              f"bytes, compression {e.compression} -> {donor.compression}, at "
              f"0x{e.offset:X} (reservation {old_res} -> {new_res})")
        self.put(e.offset, image, f"row {row} reservation ({new_res} B)")
        if e.size != donor.size:
            self.put(row_offset(self.ar, row) + ENTRY_SIZE_OFF,
                     struct.pack("<I", donor.size),
                     f"MFT row {row} size {e.size} -> {donor.size}")
        if e.compression != donor.compression:
            self.put(row_offset(self.ar, row) + ENTRY_COMP_OFF,
                     struct.pack("<H", donor.compression),
                     f"MFT row {row} compression {e.compression} -> "
                     f"{donor.compression}")
        self.set_entry_crc(row, donor.crc)
        self.fix_mft_self_crc()

        # READ BACK THROUGH THE WRITE HANDLE, never through self.ar -- the
        # Archive's buffered read-only handle was opened before any of this and
        # can answer from a pre-write window. Same trap read_mft() documents.
        self.fh.seek(e.offset)
        got = self.fh.read(donor.size)
        if hashlib.sha256(got).hexdigest() != donor.sha256:
            raise SystemExit(
                f"RESTORE VERIFY FAILED on row {row}: the bytes on disk are not "
                f"the donor's. Revert with the journal and do not use this "
                f"archive.")
        print(f"  verified: {donor.size} B read back sha256 {donor.sha256[:16]}")
        return True

    def fix_mft_self_crc(self):
        """Recompute row 3's crc from the table as it now stands on disk.

        Call this after every MFT change, or the table no longer describes
        itself and we have run a different experiment than the one we meant to.
        """
        mft = self.read_mft()
        want = mft_self_crc(mft, self.ar.entry_count)
        have = struct.unpack_from("<I", mft, SELF_ROW_START + ENTRY_CRC)[0]
        if want == have:
            print(f"  MFT self-crc already correct (0x{want:08X})")
            return want
        self.put(row_offset(self.ar, MFT_SELF_ROW) + ENTRY_CRC,
                 struct.pack("<I", want),
                 f"MFT self-crc 0x{have:08X} -> 0x{want:08X}")
        return want


def verify(path):
    """All three rules against one archive, right now. Returns a failure count."""
    bad = 0
    with Archive(path) as ar:
        ar.fh.seek(0)
        head = ar.fh.read(32)
        stored = struct.unpack_from("<I", head, HDR_CRC)[0]
        want = binascii.crc32(head[:12])
        ok = stored == want
        bad += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] file header crc  "
              f"stored 0x{stored:08X} computed 0x{want:08X}")

        mft = read_mft(ar)
        stored = struct.unpack_from("<I", mft, SELF_ROW_START + ENTRY_CRC)[0]
        want = mft_self_crc(mft, ar.entry_count)
        ok = stored == want
        bad += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] MFT self-crc      "
              f"stored 0x{stored:08X} computed 0x{want:08X}")
    return bad


def check_rows(path, rows):
    """The entry crc of specific rows, over their stored bytes."""
    bad = 0
    with Archive(path) as ar:
        for row in rows:
            e = ar.row(row)
            want = binascii.crc32(ar.raw(e))
            ok = want == e.crc
            bad += not ok
            print(f"  [{'PASS' if ok else 'FAIL'}] row {row:<7} crc      "
                  f"stored 0x{e.crc:08X} computed 0x{want:08X}  "
                  f"({e.size} B, comp={e.compression}, flags={e.flags})")
    return bad


def revert(journal_path, force=False):
    """Undo every edit in a journal, newest first."""
    with open(journal_path) as fh:
        doc = json.load(fh)
    path = doc["dat"]
    guard(path)
    edits = doc["edits"]
    if not edits:
        print("journal is empty; nothing to revert")
        return 0

    # See Journal's docstring: the client moves the MFT, and a stale MFT edit
    # replayed at its old address is a silent no-op that still verifies.
    was = doc.get("mft_offset")
    with Archive(path) as ar:
        now = ar.mft_offset
    if was is None:
        print(f"WARNING: this journal predates MFT-offset recording. If it "
              f"contains MFT edits and the table has moved since, reverting "
              f"them writes into dead space. The MFT is at 0x{now:X} now.")
    elif was != now:
        msg = (f"The MFT has MOVED since this journal was written:\n"
               f"    journalled at 0x{was:X}\n"
               f"    archive now   0x{now:X}\n"
               f"Every MFT edit here names an address that is no longer the "
               f"table. Replaying them would write into dead space, restore "
               f"nothing, and still leave the archive verifying -- so the "
               f"failure would be invisible. Restore the affected rows' size, "
               f"compression and crc explicitly instead, then recompute the "
               f"self-crc.")
        if not force:
            raise SystemExit(msg + "\n(--force to replay anyway; payload edits "
                                   "are unaffected and safe.)")
        print("WARNING, --force given:\n" + msg)
    print(f"reverting {len(edits)} edit(s) in {path}")
    restored = 0
    with open(path, "r+b") as fh:
        for ed in reversed(edits):
            want_now = binascii.unhexlify(ed["after"])
            back = binascii.unhexlify(ed["before"])
            fh.seek(ed["offset"])
            actual = fh.read(len(back))
            if actual == back:
                print(f"  (already) 0x{ed['offset']:012X} {ed['what']}")
                continue
            if actual != want_now:
                # Something other than us changed these bytes -- most likely the
                # client itself, which is exactly what a durability test is
                # looking for. Say so loudly and put ours back anyway.
                print(f"  CHANGED   0x{ed['offset']:012X} {ed['what']}\n"
                      f"            on disk {binascii.hexlify(actual).decode()} "
                      f"is neither ours nor the original -- the client wrote here")
            fh.seek(ed["offset"])
            fh.write(back)
            restored += 1
            print(f"  restored  0x{ed['offset']:012X} +{len(back)} {ed['what']}")
        fh.flush()
        os.fsync(fh.fileno())
    print(f"{restored} range(s) restored")
    return 0


# Every flag that WRITES, named in one place. --verify short-circuits and returns
# before the Writer is ever constructed unless one of these is present, so a write
# flag missing from this tuple turns `--verify --thatflag` into "[PASS] all rules
# hold", exit 0, and nothing written at all -- a silent no-op wearing a green
# banner, which is the exact failure mode toolkit/checks.py exists to refuse.
#
# That is not hypothetical. `--replace` was absent here from the day it was added,
# and `--verify --replace ROW --data F` is the combination the documented procedure
# leads with, because verifying before writing is the obvious habit. It printed
# "[PASS] all rules hold" and did nothing, for as long as the flag existed.
#
# test_datwrite.py section 2 checks these two tuples against the parser's own
# actions, so a flag added below and forgotten here goes red instead of going quiet.
MUTATING_DESTS = ("corrupt_crc", "overwrite", "replace", "corrupt_mft_crc",
                  "restore")

# The rest: reads, or arguments to something else. Listed only so the drift check
# can tell "deliberately read-only" from "somebody forgot".
READONLY_DESTS = ("help", "dat", "journal", "verify", "check_rows", "data",
                  "revert", "force", "from_dat", "confirm")


def is_mutating(args):
    """Does this run intend to write? None and False both mean 'not given'.

    Identity comparisons, not truthiness: a row number of 0 is a value, and
    `if args.corrupt_crc` would read it as absent. That is the same bug as the
    missing --replace, just waiting on a different input.
    """
    return any(v is not None and v is not False
               for v in (getattr(args, d) for d in MUTATING_DESTS))


def build_parser():
    """The command line, factored out so a test can enumerate it."""
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", help="the archive to operate on (never C:\\gw)")
    ap.add_argument("--journal", default=None,
                    help="where to record what changed (default: DAT.journal.json)")
    ap.add_argument("--verify", action="store_true",
                    help="check the header and MFT self checksums")
    ap.add_argument("--check-rows", type=int, nargs="+", metavar="ROW",
                    help="check specific entry crcs over their stored bytes")
    ap.add_argument("--corrupt-crc", type=int, metavar="ROW",
                    help="flip a row's stored crc, leaving its CONTENT untouched")
    ap.add_argument("--overwrite", type=int, metavar="ROW",
                    help="replace a row's stored bytes, same length, in place")
    ap.add_argument("--data", metavar="FILE",
                    help="with --overwrite, the replacement bytes")
    ap.add_argument("--replace", type=int, metavar="ROW",
                    help="replace a row's contents with a DIFFERENT-length "
                         "payload, writing it stored: payload, size field, "
                         "compression field and crc. Refuses to relocate.")
    ap.add_argument("--corrupt-mft-crc", action="store_true",
                    help="flip the MFT self-crc (Arm C -- expect a full rescan)")
    ap.add_argument("--restore", type=int, metavar="ROW",
                    help="put ROW back to what --from says it should hold, "
                         "compression and all. Grows in place if the blocks it "
                         "freed are still unclaimed, and refuses naming the "
                         "claimant if they are not")
    ap.add_argument("--from", dest="from_dat", metavar="DONOR",
                    help="a pristine archive to read the original from "
                         "(read-only; C:\\gw is allowed here and nowhere else)")
    ap.add_argument("--confirm", action="store_true",
                    help="actually perform a --restore; without it the plan is "
                         "printed and nothing is written")
    ap.add_argument("--revert", metavar="JOURNAL",
                    help="undo every edit recorded in a journal")
    ap.add_argument("--force", action="store_true",
                    help="with --revert, replay MFT edits even if the "
                         "table has moved. Almost always wrong.")
    return ap


def main():
    ap = build_parser()
    args = ap.parse_args()

    if args.revert:
        return revert(args.revert, args.force)
    if not args.dat:
        ap.error("--dat is required")

    # Before the Writer, so a command that cannot run never opens the archive
    # 'r+b'. --restore without --from would otherwise reach read_donor(None) and
    # die inside the try/finally with the file already open for writing.
    if args.restore is not None and not args.from_dat:
        ap.error("--restore needs --from DONOR (a pristine archive to read the "
                 "original out of)")
    if args.from_dat is not None and args.restore is None:
        ap.error("--from is only meaningful with --restore")

    if args.verify or args.check_rows:
        print(f"{args.dat}")
        bad = 0
        if args.verify:
            bad += verify(args.dat)
        if args.check_rows:
            bad += check_rows(args.dat, args.check_rows)
        if not is_mutating(args):
            print("\n[FAIL] %d rule(s) failed" % bad if bad else "\n[PASS] all rules hold")
            return 1 if bad else 0
        if bad:
            # Don't drop the number on the floor on the way to the Writer: this
            # archive was already failing its own checksums before we touched it,
            # and whatever the write produces afterwards will not be attributable.
            print(f"\n[WARN] {bad} rule(s) ALREADY failing before this write; "
                  f"continuing because a write flag was given")

    journal = args.journal or (args.dat + ".journal.json")
    w = Writer(args.dat, journal)
    try:
        if args.corrupt_crc is not None:
            row = args.corrupt_crc
            e = w.ar.row(row)
            print(f"corrupting the crc of row {row} "
                  f"({e.size} B, comp={e.compression}, flags={e.flags})")
            print("  content is NOT touched -- this isolates the crc as a gate")
            w.set_entry_crc(row, e.crc ^ 1)
            w.fix_mft_self_crc()

        if args.overwrite is not None:
            if not args.data:
                raise SystemExit("--overwrite needs --data")
            row = args.overwrite
            e = w.ar.row(row)
            new = open(args.data, "rb").read()
            if len(new) != e.size:
                raise SystemExit(
                    f"--overwrite is same-length only: row {row} stores "
                    f"{e.size} bytes, {args.data} has {len(new)}. Changing the "
                    f"size means a size field, possibly a relocation, and a "
                    f"different experiment.")
            print(f"overwriting row {row}: {e.size} bytes at 0x{e.offset:X}")
            w.put(e.offset, new, f"row {row} stored bytes")
            w.set_entry_crc(row, binascii.crc32(new))
            w.fix_mft_self_crc()

        if args.replace is not None:
            if not args.data:
                raise SystemExit("--replace needs --data")
            w.replace(args.replace, open(args.data, "rb").read())

        if args.restore is not None:
            row = args.restore
            donor = read_donor(args.from_dat, row)
            print(f"donor {args.from_dat} row {row}: {donor.size} B, "
                  f"compression {donor.compression}, crc 0x{donor.crc:08X}, "
                  f"sha256 {donor.sha256[:16]}")
            check_identity(args.dat, row, donor)
            w.restore(row, donor, confirm=args.confirm)

        if args.corrupt_mft_crc:
            # w.read_mft(), not read_mft(w.ar): combined with another write flag
            # this runs AFTER that flag's edits, and the Archive handle would hand
            # back the pre-write table -- corrupting a value that is already stale.
            mft = w.read_mft()
            have = struct.unpack_from("<I", mft, SELF_ROW_START + ENTRY_CRC)[0]
            print("corrupting the MFT self-crc -- Arm C. Expect a full rescan.")
            w.put(row_offset(w.ar, MFT_SELF_ROW) + ENTRY_CRC,
                  struct.pack("<I", have ^ 1), "MFT self-crc (deliberately wrong)")
    finally:
        w.close()

    print(f"\njournal: {journal}")
    print(f"revert with:\n  python {os.path.relpath(__file__)} --revert {journal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
