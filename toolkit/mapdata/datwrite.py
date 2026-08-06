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
    archive. A 4.2 GB re-cut per arm is otherwise the only way back.
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
    python toolkit/mapdata/datwrite.py --dat DAT --revert journal.json
"""

import argparse
import binascii
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import Archive, ENTRY_SIZE  # noqa: E402

LIVE_INSTALL = os.path.normcase(os.path.abspath(r"C:\gw"))

MFT_SELF_ROW = 3
SELF_ROW_START = MFT_SELF_ROW * ENTRY_SIZE          # 0x48
SELF_ROW_END = SELF_ROW_START + ENTRY_SIZE          # 0x60

ENTRY_SIZE_OFF = 0x08   # u32, the entry's stored length
ENTRY_COMP_OFF = 0x0C   # u16, 0 stored / 8 huffman
ENTRY_CRC = 0x14        # offset of the crc within a 24-byte MFT row
HDR_CRC = 0x0C          # offset of the crc within the 32-byte file header


def guard(path):
    """Never the live install. Not a warning; a refusal."""
    p = os.path.normcase(os.path.abspath(path))
    if p == LIVE_INSTALL or p.startswith(LIVE_INSTALL + os.sep):
        raise SystemExit(
            f"Refusing to write inside the live install at {LIVE_INSTALL}.\n"
            f"  asked for: {path}\n"
            f"That install is read-only to this project. Point --dat at the "
            f"run-dir or study copy under vault/.")
    return p


def row_offset(ar, row):
    """Where row N's 24 bytes start. Row N sits at mft_offset + N*24."""
    return ar.mft_offset + row * ENTRY_SIZE


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
    """An open archive plus the journal of what has been done to it."""

    def __init__(self, path, journal_path):
        guard(path)
        self.path = path
        self.ar = Archive(path)
        self.fh = open(path, "r+b")
        self.journal = Journal(journal_path, os.path.abspath(path),
                               self.ar.mft_offset)

    def close(self):
        self.fh.close()
        self.ar.close()

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
        """
        e = self.ar.entries[row - 1]
        block = self.ar.block_size
        reserved = -(-e.size // block) * block
        if len(new) > reserved:
            raise SystemExit(
                f"row {row} reserves {reserved} bytes ({e.size} used, "
                f"{block}-byte blocks) and the new payload is {len(new)}. "
                f"That is a relocation, not a replacement. Pick a row with a "
                f"bigger reservation -- datplan.py --free lists them.")
        print(f"replacing row {row}: {e.size} -> {len(new)} bytes, "
              f"compression {e.compression} -> 0, at 0x{e.offset:X} "
              f"(reservation {reserved})")
        self.put(e.offset, new, f"row {row} payload")
        self.put(row_offset(self.ar, row) + ENTRY_SIZE_OFF,
                 struct.pack("<I", len(new)),
                 f"MFT row {row} size {e.size} -> {len(new)}")
        if e.compression != 0:
            self.put(row_offset(self.ar, row) + ENTRY_COMP_OFF,
                     struct.pack("<H", 0),
                     f"MFT row {row} compression {e.compression} -> 0 (stored)")
        self.set_entry_crc(row, binascii.crc32(new))
        self.fix_mft_self_crc()

    def fix_mft_self_crc(self):
        """Recompute row 3's crc from the table as it now stands on disk.

        Call this after every MFT change, or the table no longer describes
        itself and we have run a different experiment than the one we meant to.
        """
        mft = read_mft(self.ar)
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
            e = ar.entries[row - 1]
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


def main():
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
    ap.add_argument("--revert", metavar="JOURNAL",
                    help="undo every edit recorded in a journal")
    ap.add_argument("--force", action="store_true",
                    help="with --revert, replay MFT edits even if the "
                         "table has moved. Almost always wrong.")
    args = ap.parse_args()

    if args.revert:
        return revert(args.revert, args.force)
    if not args.dat:
        ap.error("--dat is required")

    if args.verify or args.check_rows:
        print(f"{args.dat}")
        bad = 0
        if args.verify:
            bad += verify(args.dat)
        if args.check_rows:
            bad += check_rows(args.dat, args.check_rows)
        mutating = (args.corrupt_crc or args.overwrite or args.corrupt_mft_crc)
        if not mutating:
            print("\n[FAIL] %d rule(s) failed" % bad if bad else "\n[PASS] all rules hold")
            return 1 if bad else 0

    journal = args.journal or (args.dat + ".journal.json")
    w = Writer(args.dat, journal)
    try:
        if args.corrupt_crc is not None:
            row = args.corrupt_crc
            e = w.ar.entries[row - 1]
            print(f"corrupting the crc of row {row} "
                  f"({e.size} B, comp={e.compression}, flags={e.flags})")
            print("  content is NOT touched -- this isolates the crc as a gate")
            w.set_entry_crc(row, e.crc ^ 1)
            w.fix_mft_self_crc()

        if args.overwrite is not None:
            if not args.data:
                raise SystemExit("--overwrite needs --data")
            row = args.overwrite
            e = w.ar.entries[row - 1]
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

        if args.corrupt_mft_crc:
            mft = read_mft(w.ar)
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
