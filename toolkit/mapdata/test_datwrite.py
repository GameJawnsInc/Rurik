"""Check the archive WRITER against an archive we build ourselves.

datwrite.py is the only tool in this project that opens Gw.dat `r+b`, it is the
one that can destroy four gigabytes of somebody's game, and until this file it
had no test. Three defects were sitting in it. All three were found by reading
rather than by running, and all three are the same shape: the tool reports
success for work it did not do.

  1. `--verify --replace ROW --data F` verified, printed "[PASS] all rules hold",
     exited 0, and never constructed the Writer. `--replace` was missing from
     main()'s `mutating` tuple, so the early return for a read-only run swallowed
     it. That is the flag combination the documented procedure leads with,
     because verifying before writing is the obvious habit.
  2. A shrinking replace journalled only the bytes it wrote. put() reads
     len(data) as its `before`, so replacing a 1.96 MB row with 20 KB captured
     20 KB of history. The client rederives its free list from the entry table at
     every open and is OBSERVED relocating live rows during play
     (studies/datwrite/FINDINGS.md section 6), so if it took the freed blocks,
     --revert restored the first 20 KB, reported success, left all three checksum
     rules verifying, and the original payload was gone.
  3. A shrinking replace left the old payload's tail inside the row's own
     reservation, immediately after the authored bytes.

NOT ONE OF THE THREE CAN FAIL A CHECKSUM, which is why none of them showed up in
five months of the archive being fully self-checking. The archive verifies
perfectly in all three cases. So most of what is below is not a checksum check:
it asks whether the bytes on disk are the bytes we asked for, and whether what
the journal holds is enough to put them back. Sections 1 and 4 check the
checksums, and they are the weakest sections here, not the strongest.

WHAT IT RUNS AGAINST. A 4 KB archive this file builds in a temp directory and
deletes afterwards. It never opens vault/dat_study/Gw.dat, it never reads C:\\gw,
and section 0 is the refusal that makes the second of those a refusal rather than
a convention.

The fixture is built from the layout archive.py MEASURED against the shipped
client, and it restates the two self-referential checksum rules longhand from
test_datcrc.py rather than importing datwrite's versions -- so section 1 is an
independent statement that the fixture is a real archive, not datwrite agreeing
with itself. Fournux/Tyria-Extractor's fixture generator (MIT, mirrored under
vault/) was read and nothing is taken from it; it reads the entry fields
differently than we do. No derivation-register row is owed for this file.

    python toolkit/mapdata/test_datwrite.py
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
import datwrite  # noqa: E402
import checks  # noqa: E402

# FLOOR: the sixty-six checks below, every one of which runs unconditionally --
# the fixture is built by this file, so there is no corpus to be missing and no
# section that can legitimately not run. Measured from a green run on
# 2026-08-10, again on 2026-08-12 when section 0b took it from 31 to 34, and
# again on 2026-08-14 when section 7 (--restore) took it from 34 to 66.
# Anything under this means a section stopped executing, and on a file whose
# defects all present as silent success that is exactly the report we must not
# accept.
#
# Section 7's three sabotages are the measurement of which of ITS checks matter,
# and they are run rather than argued: stubbing `claimants()` to [] lets the
# claimed-extent restore through, stubbing `check_identity()` lets a wrong-file
# restore through, and a donor whose compression is flattened to 0 leaves the row
# at 0 while the PAYLOAD stays byte-identical -- the last one is why 7b checks the
# compression field separately, since the stored bytes cannot tell the two apart.
LEDGER = checks.Ledger("dat writer", floor=66)
check = checks.adopt(LEDGER)

FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"
ENTRY_CRC = 0x14        # within a 24-byte MFT row. Restated, not imported: it
                        # belongs to the module under test.

BLOCK = 512
FILE_SIZE = 0x1000
MFT_OFF = 0x0E00
ENTRY_COUNT = 8                       # counts the MFT's own 24-byte header row
MFT_SIZE = ENTRY_COUNT * ENTRY_SIZE   # 192
SLACK = 0xCC            # what fills every byte no row claims. Non-zero on
                        # purpose: it makes "the tail is zeroed" and "revert put
                        # it back" both bite on bytes the old code never touched.

ROW_HEADER, ROW_IDTABLE, ROW_SELF = 1, 2, 3
ROW_SHRINK, ROW_MID, ROW_EXACT, ROW_SMALL = 4, 5, 6, 7

# row -> (offset, size, compression, flags). Hand-laid so that every offset is
# block-aligned and no extent reaches the next row's offset -- which is what
# makes the tail of a row's last block ITS OWN to write, the premise replace()
# now depends on. Rows 1, 2 and 3 keep the meanings they have in the real
# archive; row 3's index in particular is wired into the MFT self-crc rule.
#
# Row 4 is marked compression 8 so a replace has a compression field to move.
# Its bytes are not huffman and nothing here decompresses it -- datwrite only
# ever reads rows through Archive.raw().
ROWS = {
    ROW_HEADER:  (0x0000, 32,       0, 3),   # the file header itself
    ROW_IDTABLE: (0x0200, 16,       0, 3),   # two (file_id, row) pairs
    ROW_SELF:    (MFT_OFF, MFT_SIZE, 0, 3),  # the master file table itself
    ROW_SHRINK:  (0x0400, 1000,     8, 3),   # 1000 B in a 1024 B reservation
    ROW_MID:     (0x0800, 300,      0, 3),
    ROW_EXACT:   (0x0A00, 512,      0, 3),   # 512 B in a 512 B reservation
    ROW_SMALL:   (0x0C00, 100,      0, 3),
}
PAYLOAD_ROWS = (ROW_IDTABLE, ROW_SHRINK, ROW_MID, ROW_EXACT, ROW_SMALL)


def reservation(size):
    """Whole blocks a row of this size owns. Same arithmetic replace() uses."""
    return -(-size // BLOCK) * BLOCK


def pattern(seed, n):
    """Deterministic bytes, none of them 0x00, so a zeroed tail is unambiguous."""
    return bytes(1 + ((i * 37 + seed * 101) % 255) for i in range(n))


def self_crc(mft):
    """Row 3's crc, spelled out from test_datcrc.py's MEASURED rule.

    Deliberately not datwrite.mft_self_crc: a fixture built with the code under
    test agrees with it by construction, and section 1 would be checking nothing.
    """
    acc = binascii.crc32(bytes(mft[0x00:ROW_SELF * ENTRY_SIZE]))
    return binascii.crc32(
        bytes(mft[(ROW_SELF + 1) * ENTRY_SIZE:ENTRY_COUNT * ENTRY_SIZE]), acc)


def build_archive(path):
    """Write a small, complete, fully self-checking archive. Returns its payloads."""
    buf = bytearray(bytes([SLACK]) * FILE_SIZE)

    payloads = {}
    for row in PAYLOAD_ROWS:
        off, size, _comp, _flags = ROWS[row]
        data = (struct.pack("<IIII", 0x1000, ROW_SHRINK, 0x1001, ROW_EXACT)
                if row == ROW_IDTABLE else pattern(row, size))
        buf[off:off + size] = data
        payloads[row] = data

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
        if row == ROW_HEADER:
            crc = 0          # the header protects itself, at its own +0x0C
        elif row == ROW_SELF:
            crc = 0          # patched below, once the rest of the table is final
        else:
            crc = binascii.crc32(bytes(buf[off:off + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         off, size, comp, flags, 0, crc)
    # Row 3's crc field sits inside the 24 bytes the rule skips, so writing it
    # cannot change the value being written. That is the whole point of the skip.
    struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + ENTRY_CRC, self_crc(mft))
    buf[MFT_OFF:MFT_OFF + MFT_SIZE] = mft

    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return payloads


def fresh(tmp, name):
    """A brand-new archive at tmp/name. Every section gets its own copy."""
    path = os.path.join(tmp, name)
    return path, build_archive(path)


def blob(path):
    with open(path, "rb") as fh:
        return fh.read()


def spill(tmp, name, data):
    """A --data file."""
    path = os.path.join(tmp, name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path


@contextlib.contextmanager
def quiet():
    """Swallow the tool's own output.

    datwrite prints in the same two-space `  [PASS]` form the ledger does, and a
    reader counting green lines against the floor must not be counting the
    subject's output as the test's.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


def run_cli(*argv):
    """Drive datwrite through its real command line. Returns (exit code, output).

    Through main() and argparse on purpose: the missing --replace lived in the
    dispatch, not in Writer, and a test that called Writer.replace() directly
    would have passed against the broken tool.
    """
    buf = io.StringIO()
    saved = sys.argv
    sys.argv = ["datwrite.py", *argv]
    try:
        with contextlib.redirect_stdout(buf):
            code = datwrite.main()
    except SystemExit as exc:
        if isinstance(exc.code, int):
            code = exc.code
        else:
            code = 1
            if exc.code:
                buf.write(str(exc.code) + "\n")   # the refusal text is the point
    finally:
        sys.argv = saved
    return code, buf.getvalue()


def sections(tmp):
    print("\n0. the refusal that is not allowed to be a warning")
    for victim in (r"C:\gw", r"C:\gw\Gw.dat", "C:/GW/gw.dat"):
        try:
            datwrite.guard(victim)
            refused = False
        except SystemExit:
            refused = True
        check(refused, f"guard({victim!r}) refuses the live install")

    print("\n0b. and the SOURCE snapshot is refused on the write path")
    # Added 2026-08-12. `rebloat.guard_target()` had refused vault/dat_study
    # since it existed and its docstring claimed datwrite did too; datwrite did
    # not, and datwrite is the tool that opens the archive r+b. No checksum
    # catches the mistake -- --replace fixes the entry crc and the MFT self-crc
    # as it goes, so a mutated snapshot verifies clean forever.
    study_dir = os.path.join(tmp, "vault", "dat_study")
    os.makedirs(study_dir, exist_ok=True)
    study = os.path.join(study_dir, "Gw.dat")
    build_archive(study)
    try:
        datwrite.Writer(study, os.path.join(tmp, "guard.journal.json")).close()
        refused = False
    except SystemExit:
        refused = True
    check(refused, "Writer() refuses a path under vault/dat_study")

    # The positive control. A guard that refuses everything protects nothing,
    # because the tool never runs.
    ordinary = os.path.join(tmp, "ordinary.dat")
    build_archive(ordinary)
    try:
        datwrite.Writer(ordinary,
                        os.path.join(tmp, "ok.journal.json")).close()
        allowed = True
    except SystemExit:
        allowed = False
    check(allowed, "CONTROL: an ordinary copy is still allowed")

    # The design point, and the check that catches the obvious wrong fix.
    # `revert()` shares `guard()`, and replaying a journal is the ONE
    # legitimate write to dat_study -- it is how the mistake above gets undone.
    # Moving the refusal into guard() would pass both checks above and close the
    # recovery door behind the accident.
    empty = os.path.join(tmp, "empty.journal.json")
    with open(empty, "w") as fh:
        json.dump({"dat": study, "mft_offset": MFT_OFF, "edits": []}, fh)
    try:
        with quiet():
            code = datwrite.revert(empty)
    except SystemExit:
        code = -1
    check(code == 0,
          "but --revert on dat_study is STILL allowed -- the refusal is on "
          "Writer(), not in guard(), which revert shares")

    print("\n1. the fixture is a real archive (or nothing below measures anything)")
    dat, _payloads = fresh(tmp, "fixture.dat")
    with Archive(dat) as ar:
        check(ar.entry_count == ENTRY_COUNT
              and len(ar.entries) == ENTRY_COUNT - 1
              and ar.block_size == BLOCK,
              f"opens: {ar.entry_count} rows x {ENTRY_SIZE} == {ar.mft_size} B, "
              f"block {ar.block_size}")
    with quiet():
        bad = datwrite.verify(dat)
    check(bad == 0, "the file header crc and the MFT self-crc both hold")
    with quiet():
        bad = datwrite.check_rows(dat, list(PAYLOAD_ROWS))
    check(bad == 0,
          f"all {len(PAYLOAD_ROWS)} payload rows' entry crcs hold over their "
          f"stored bytes")

    print("\n2. every flag that writes is classified as one")
    ap = datwrite.build_parser()
    # _actions is private; argparse offers nothing public that enumerates a
    # parser, and the alternative is a hand-kept list that drifts the same way
    # the tuple this checks did.
    dests = {a.dest for a in ap._actions}
    known = set(datwrite.MUTATING_DESTS) | set(datwrite.READONLY_DESTS)
    stray = sorted(dests - known)
    check(not stray,
          "every flag the parser declares is classified mutating or read-only"
          + (f" -- unclassified: {stray}" if stray else ""))
    for flag, extra in (("--corrupt-crc", ["--corrupt-crc", "5"]),
                        ("--overwrite", ["--overwrite", "5"]),
                        ("--replace", ["--replace", "5"]),
                        ("--corrupt-mft-crc", ["--corrupt-mft-crc"])):
        args = ap.parse_args(["--dat", dat] + extra)
        check(datwrite.is_mutating(args), f"{flag} is recognised as a write")
    check(datwrite.is_mutating(ap.parse_args(["--dat", dat, "--corrupt-crc", "0"])),
          "row 0 is a row number, not an absent flag (truthiness would lose it)")
    check(not datwrite.is_mutating(ap.parse_args(["--dat", dat, "--verify"])),
          "--verify on its own is not a write")

    print("\n3. --verify --replace writes (the defect this file was opened for)")
    dat, _payloads = fresh(tmp, "verify-replace.dat")
    journal = dat + ".journal.json"
    small = pattern(99, 20)
    src = spill(tmp, "new20.bin", small)
    code, out = run_cli("--dat", dat, "--journal", journal,
                        "--verify", "--replace", str(ROW_SHRINK), "--data", src)
    check(code == 0, f"--verify --replace exits 0 (got {code})")
    with Archive(dat) as ar:
        e = ar.entries[ROW_SHRINK - 1]
        size_now, stored_now, comp_now = e.size, ar.raw(e), e.compression
    check(size_now == len(small),
          f"the size field is now {len(small)} (got {size_now})")
    check(stored_now == small,
          "the row's stored bytes ARE the new payload -- it did not just verify")
    edits = json.load(open(journal))["edits"] if os.path.exists(journal) else []
    check(bool(edits), f"a journal was written and records {len(edits)} edit(s)")

    print("\n4. the replace round-trips and all three checksum rules land")
    with quiet():
        bad = datwrite.verify(dat)
    check(bad == 0, "the file header crc and the MFT self-crc still hold")
    with quiet():
        bad = datwrite.check_rows(dat, [ROW_SHRINK])
    check(bad == 0,
          f"row {ROW_SHRINK}'s entry crc covers its new stored bytes")
    check(comp_now == 0,
          f"the compression field moved {ROWS[ROW_SHRINK][2]} -> 0 (stored)")

    print("\n5. the reservation is a hard edge, from both sides")
    dat5, _ = fresh(tmp, "oversize.dat")
    j5 = dat5 + ".journal.json"
    untouched = blob(dat5)
    resv_exact = reservation(ROWS[ROW_EXACT][1])
    over = spill(tmp, "over.bin", pattern(11, resv_exact + 1))
    code, out = run_cli("--dat", dat5, "--journal", j5,
                        "--replace", str(ROW_EXACT), "--data", over)
    check(code != 0,
          f"a payload one byte past row {ROW_EXACT}'s {resv_exact}-byte "
          f"reservation is refused (exit {code})")
    check(blob(dat5) == untouched,
          "the archive is byte-identical after the refusal")
    check(not os.path.exists(j5), "and no journal was left behind")

    dat5b, _ = fresh(tmp, "exactfit.dat")
    resv_shrink = reservation(ROWS[ROW_SHRINK][1])
    fits = pattern(13, resv_shrink)
    code, out = run_cli("--dat", dat5b, "--journal", dat5b + ".journal.json",
                        "--replace", str(ROW_SHRINK),
                        "--data", spill(tmp, "fits.bin", fits))
    with Archive(dat5b) as ar:
        got = ar.raw(ar.entries[ROW_SHRINK - 1])
    check(code == 0 and got == fits,
          f"a payload of exactly the {resv_shrink}-byte reservation is accepted")

    print("\n6. a shrink covers the WHOLE reservation, not just what it wrote")
    dat6, _ = fresh(tmp, "shrink.dat")
    j6 = dat6 + ".journal.json"
    original = blob(dat6)
    off, size, _c, _f = ROWS[ROW_SHRINK]
    resv = reservation(size)
    tiny = pattern(17, 20)
    code, out = run_cli("--dat", dat6, "--journal", j6,
                        "--replace", str(ROW_SHRINK),
                        "--data", spill(tmp, "tiny.bin", tiny))
    tail = blob(dat6)[off + len(tiny):off + resv]
    check(code == 0 and tail == b"\x00" * (resv - len(tiny)),
          f"the {resv - len(tiny)}-byte tail of the reservation is zeroed -- no "
          f"fragment of the old payload survives inside the row")
    doc = json.load(open(j6))
    at_payload = [ed for ed in doc["edits"] if ed["offset"] == off]
    check(len(at_payload) == 1 and at_payload[0]["length"] == resv,
          f"the journal's record at 0x{off:X} spans the whole {resv}-byte "
          f"reservation (got "
          f"{at_payload[0]['length'] if len(at_payload) == 1 else at_payload} B)")
    recorded = (binascii.unhexlify(at_payload[0]["before"])
                if len(at_payload) == 1 else b"")
    check(recorded == original[off:off + resv],
          "and holds the reservation's original bytes exactly, slack included")

    print("\n7. --revert puts it back, even after the client takes the freed blocks")
    # The allocator rederives its free list from the entry table at every open,
    # so the bytes this shrink freed are, as far as the client is concerned,
    # available now. Take one whole freed block the way it would.
    with open(dat6, "r+b") as fh:
        fh.seek(off + BLOCK)
        fh.write(b"\xEE" * BLOCK)
    code, out = run_cli("--revert", j6)
    check(code == 0, f"revert exits 0 (got {code})")
    check("CHANGED" in out,
          "revert NOTICES that something other than us wrote inside the row")
    check(blob(dat6) == original,
          "the archive is byte-identical to before the replace -- the whole "
          "reservation came back, not the first 20 bytes")
    with quiet():
        bad = datwrite.verify(dat6) + datwrite.check_rows(dat6, list(PAYLOAD_ROWS))
    check(bad == 0, "and all three checksum rules hold again afterwards")


def mft_field(path, row, off, fmt, value):
    """Hand-edit one MFT field and fix the self-crc. The fixture's own writer.

    Deliberately not datwrite's: a control built with the code under test agrees
    with it by construction, and the refusals below would be checking nothing.
    """
    with open(path, "r+b") as fh:
        fh.seek(MFT_OFF)
        mft = bytearray(fh.read(MFT_SIZE))
        struct.pack_into(fmt, mft, row * ENTRY_SIZE + off, value)
        struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + ENTRY_CRC, 0)
        struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + ENTRY_CRC,
                         self_crc(mft))
        fh.seek(MFT_OFF)
        fh.write(bytes(mft))


def row_bytes(path, row, n):
    """`n` bytes at row `row`'s offset, read straight off disk."""
    with Archive(path) as ar:
        e = ar.row(row)
    with open(path, "rb") as fh:
        fh.seek(e.offset)
        return fh.read(n)


def row_entry_of(path, row):
    with Archive(path) as ar:
        e = ar.row(row)
        return e.offset, e.size, e.compression, e.crc


def section_restore(tmp):
    """7. --restore: the in-place grow datmove.plan_move names and refuses.

    Every check here is about something --replace and --revert cannot do, and
    the section exists because the alternative was measured: three skill-icon
    rows were left armed in vault/run/reskin-roster on the recorded
    understanding that their originals were "recoverable from the journals'
    before fields", and NO JOURNAL FOR THOSE ROWS EXISTS ANYWHERE IN THE VAULT
    (grepped whole, 2026-08-14). A pristine copy is the source that cannot go
    missing.
    """
    print("\n7. --restore, from a donor archive")
    donor, _ = fresh(tmp, "donor.dat")
    target, payloads = fresh(tmp, "restore-target.dat")
    original = row_bytes(donor, ROW_SHRINK, reservation(1000))

    # Shrink it the way the icon arms did: --replace, which writes compression 0
    # and leaves the row unable to grow back under its own rules.
    small = spill(tmp, "small.bin", pattern(9, 100))
    with quiet():
        run_cli("--dat", target, "--journal", os.path.join(tmp, "j7a.json"),
                "--replace", str(ROW_SHRINK), "--data", small)
    off, size, comp, _crc = row_entry_of(target, ROW_SHRINK)
    check(size == 100 and comp == 0,
          f"setup: --replace left row {ROW_SHRINK} at {size} B compression "
          f"{comp} -- 1000 B compression 8 is what has to come back")
    check(reservation(size) < reservation(1000),
          f"and its reservation shrank {reservation(1000)} -> "
          f"{reservation(size)} B, so restoring it is a GROW: this is exactly "
          f"the case datmove.plan_move refuses and names")

    print("\n7a. the dry run writes nothing")
    before = blob(target)
    code, out = run_cli("--dat", target, "--restore", str(ROW_SHRINK),
                        "--from", donor)
    check(code != 0, f"without --confirm it exits non-zero (got {code})")
    check("would restore" in out, "and says 'would restore' rather than doing it")
    check(blob(target) == before, "and the archive is byte-for-byte untouched")

    print("\n7b. --confirm puts the row back, compression and all")
    code, out = run_cli("--dat", target, "--journal",
                        os.path.join(tmp, "j7b.json"),
                        "--restore", str(ROW_SHRINK), "--from", donor,
                        "--confirm")
    check(code == 0, f"exits 0 (got {code})")
    off2, size2, comp2, crc2 = row_entry_of(target, ROW_SHRINK)
    dcrc = row_entry_of(donor, ROW_SHRINK)[3]
    check(size2 == 1000, f"size is back to 1000 (got {size2})")
    check(comp2 == 8,
          f"COMPRESSION is back to 8 (got {comp2}) -- the field --replace "
          f"flattens to 0 and has no compressor to restore")
    check(crc2 == dcrc,
          f"and the crc is the donor's 0x{dcrc:08X} (got 0x{crc2:08X})")
    check(off2 == off, "the row did not move; this is an in-place grow")
    check(row_bytes(target, ROW_SHRINK, reservation(1000)) == original,
          "the WHOLE reservation is byte-identical to the donor's, tail "
          "included -- a zero-filled tail would verify and still differ from "
          "every pristine copy")
    with quiet():
        bad = datwrite.verify(target) + datwrite.check_rows(
            target, list(PAYLOAD_ROWS))
    check(bad == 0, "and all three checksum rules hold afterwards")
    check("verified" in out, "the tool read the bytes back and said so")

    print("\n7c. it is idempotent, and the journal still works")
    code, out = run_cli("--dat", target, "--journal",
                        os.path.join(tmp, "j7c.json"),
                        "--restore", str(ROW_SHRINK), "--from", donor,
                        "--confirm")
    check(code == 0 and "nothing to do" in out,
          "a second restore is a no-op that says so")
    code, _ = run_cli("--revert", os.path.join(tmp, "j7b.json"))
    _, size3, comp3, _ = row_entry_of(target, ROW_SHRINK)
    check(code == 0 and size3 == 100 and comp3 == 0,
          f"and --revert of the restore returns the armed state "
          f"({size3} B comp {comp3})")

    print("\n7d. REFUSED: the row names a different file in the two archives")
    t2, _ = fresh(tmp, "restore-ident.dat")
    with quiet():
        run_cli("--dat", t2, "--journal", os.path.join(tmp, "j7d.json"),
                "--replace", str(ROW_SHRINK), "--data", small)
    code, out = run_cli("--dat", t2, "--journal", os.path.join(tmp, "j7dz.json"),
                        "--restore", str(ROW_SHRINK), "--from", donor,
                        "--confirm")
    check(code == 0, "CONTROL: with matching file ids the restore is allowed")
    # Now repoint the TARGET's id table so row 4 is a different file.
    t3, _ = fresh(tmp, "restore-ident2.dat")
    with open(t3, "r+b") as fh:
        fh.seek(ROWS[ROW_IDTABLE][0])
        fh.write(struct.pack("<II", 0x2000, ROW_SHRINK))
    with Archive(t3) as ar:
        e = ar.row(ROW_IDTABLE)
        with open(t3, "rb") as fh:
            fh.seek(e.offset)
            idb = fh.read(e.size)
    mft_field(t3, ROW_IDTABLE, ENTRY_CRC, "<I", binascii.crc32(idb))
    code, out = run_cli("--dat", t3, "--journal", os.path.join(tmp, "j7d2.json"),
                        "--restore", str(ROW_SHRINK), "--from", donor,
                        "--confirm")
    check(code != 0 and "DIFFERENT FILE" in out,
          "a donor whose row 4 is file 0x1000 is REFUSED against a target "
          "whose row 4 is file 0x2000")
    check("0x2000" in out and "0x1000" in out,
          "and the refusal names BOTH ids, so the operator can tell which copy "
          "is the odd one")

    print("\n7e. REFUSED: the freed blocks have been taken since")
    t4, _ = fresh(tmp, "restore-claimed.dat")
    with quiet():
        run_cli("--dat", t4, "--journal", os.path.join(tmp, "j7e.json"),
                "--replace", str(ROW_SHRINK), "--data", small)
    code, _ = run_cli("--dat", t4, "--journal", os.path.join(tmp, "j7e0.json"),
                      "--restore", str(ROW_SHRINK), "--from", donor, "--confirm")
    check(code == 0, "CONTROL: with the blocks free the restore is allowed")
    # Move ROW_SMALL into the extent row 4 gave up, the way the client's own
    # allocator would. Its payload moves too, so its crc still holds.
    t5, _ = fresh(tmp, "restore-claimed2.dat")
    with quiet():
        run_cli("--dat", t5, "--journal", os.path.join(tmp, "j7e1.json"),
                "--replace", str(ROW_SHRINK), "--data", small)
    stolen = ROWS[ROW_SHRINK][0] + reservation(100)
    body = row_bytes(t5, ROW_SMALL, ROWS[ROW_SMALL][1])
    with open(t5, "r+b") as fh:
        fh.seek(stolen)
        fh.write(body)
    mft_field(t5, ROW_SMALL, 0x00, "<Q", stolen)
    code, out = run_cli("--dat", t5, "--journal", os.path.join(tmp, "j7e2.json"),
                        "--restore", str(ROW_SHRINK), "--from", donor,
                        "--confirm")
    check(code != 0 and "CLAIMED" in out,
          "a grow into blocks another row now owns is REFUSED")
    check(f"row {ROW_SMALL}" in out,
          f"and the refusal NAMES row {ROW_SMALL} as the claimant, rather than "
          f"saying the archive is full")
    check("datmove" in out,
          "and points at datmove.py, which is the tool that can relocate")

    print("\n7f. REFUSED: a donor that fails its own checksum")
    bad_donor, _ = fresh(tmp, "donor-bad.dat")
    with open(bad_donor, "r+b") as fh:
        fh.seek(ROWS[ROW_SHRINK][0])
        fh.write(b"\x00")               # payload changed, crc left alone
    t6, _ = fresh(tmp, "restore-baddonor.dat")
    with quiet():
        run_cli("--dat", t6, "--journal", os.path.join(tmp, "j7f.json"),
                "--replace", str(ROW_SHRINK), "--data", small)
    code, out = run_cli("--dat", t6, "--journal", os.path.join(tmp, "j7f2.json"),
                        "--restore", str(ROW_SHRINK), "--from", bad_donor,
                        "--confirm")
    check(code != 0 and "FAILS ITS OWN CRC" in out,
          "a donor row that does not match its own crc is REFUSED -- it is a "
          "worse source than the armed row it would replace")

    print("\n7g. the donor is READ-ONLY, so the write guards must not apply to it")
    # vault/dat_study is refused as a TARGET by guard_source and is exactly the
    # archive an operator would reach for as a DONOR. If read_donor were guarded,
    # the best source in the vault would be unusable.
    study = os.path.join(tmp, "vault", "dat_study", "Gw.dat")
    t7, _ = fresh(tmp, "restore-fromstudy.dat")
    with quiet():
        run_cli("--dat", t7, "--journal", os.path.join(tmp, "j7g.json"),
                "--replace", str(ROW_SHRINK), "--data", small)
    code, out = run_cli("--dat", t7, "--journal", os.path.join(tmp, "j7g2.json"),
                        "--restore", str(ROW_SHRINK), "--from", study,
                        "--confirm")
    check(code == 0,
          "restoring FROM vault/dat_study is allowed, though writing TO it is "
          "refused")
    code, out = run_cli("--dat", study, "--journal",
                        os.path.join(tmp, "j7g3.json"),
                        "--restore", str(ROW_SHRINK), "--from", donor,
                        "--confirm")
    check(code != 0,
          "and the same path as the TARGET is still refused -- the asymmetry is "
          "the point, not an oversight")
    # And on the syntax tree, because "it happened not to be guarded" and "it is
    # deliberately not guarded" look identical from the outside.
    tree = ast.parse(open(datwrite.__file__, encoding="utf-8").read())
    fns = {n.name: n for n in ast.walk(tree)
           if isinstance(n, ast.FunctionDef)}
    def calls(node):
        return {c.func.id for c in ast.walk(node)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)}
    check(not ({"guard", "guard_source"} & calls(fns["read_donor"])),
          "read_donor calls neither guard nor guard_source, on the syntax tree")
    check({"guard", "guard_source"} <= calls(fns["__init__"]),
          "CONTROL: Writer.__init__ calls both -- so the absence above is a "
          "decision about the donor and not a missing guard everywhere")

    print("\n7h. the parser refuses half a command")
    code, _ = run_cli("--dat", target, "--restore", str(ROW_SHRINK))
    check(code == 2, f"--restore without --from exits 2 (got {code})")
    code, _ = run_cli("--dat", target, "--from", donor)
    check(code == 2, f"--from without --restore exits 2 (got {code})")

    print("\n7i. WHICH CHECKS ARE LOAD-BEARING, measured by sabotage")
    # Three one-binding edits to the LIVE module, each run against the fixtures
    # above. A check nobody can redden is floor, not coverage.
    real_claimants, real_identity, real_donor = (
        datwrite.claimants, datwrite.check_identity, datwrite.read_donor)
    try:
        datwrite.claimants = lambda ar, lo, hi, exclude: []
        code, _ = run_cli("--dat", t5, "--journal",
                          os.path.join(tmp, "j7i1.json"),
                          "--restore", str(ROW_SHRINK), "--from", donor,
                          "--confirm")
        check(code == 0,
              "SABOTAGE: with claimants() stubbed to [], the claimed-extent "
              "refusal passes -- so 7e is load-bearing and not decorative")
    finally:
        datwrite.claimants = real_claimants

    try:
        datwrite.check_identity = lambda *a, **k: None
        code, _ = run_cli("--dat", t3, "--journal",
                          os.path.join(tmp, "j7i2.json"),
                          "--restore", str(ROW_SHRINK), "--from", donor,
                          "--confirm")
        check(code == 0,
              "SABOTAGE: with check_identity() stubbed out, the wrong-file "
              "restore goes through -- so 7d is load-bearing")
    finally:
        datwrite.check_identity = real_identity

    t8, _ = fresh(tmp, "restore-nocomp.dat")
    with quiet():
        run_cli("--dat", t8, "--journal", os.path.join(tmp, "j7i3.json"),
                "--replace", str(ROW_SHRINK), "--data", small)
    try:
        def flatten(path, row):
            d = real_donor(path, row)
            d.compression = 0           # the --replace defect, reintroduced
            return d
        datwrite.read_donor = flatten
        with quiet():
            run_cli("--dat", t8, "--journal", os.path.join(tmp, "j7i4.json"),
                    "--restore", str(ROW_SHRINK), "--from", donor, "--confirm")
    finally:
        datwrite.read_donor = real_donor
    check(row_entry_of(t8, ROW_SHRINK)[2] == 0,
          "SABOTAGE: a restore that carries compression 0 leaves the row at 0 "
          "-- which is what 7b's compression check catches and byte-identity "
          "of the payload does NOT, because the stored bytes are the same")


def main():
    tmp = tempfile.mkdtemp(prefix="rurik-datwrite-")
    print(f"synthetic archive: {FILE_SIZE} B, {ENTRY_COUNT} rows, in {tmp}")
    try:
        sections(tmp)
        section_restore(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
