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

# FLOOR: the thirty-four checks below, every one of which runs unconditionally --
# the fixture is built by this file, so there is no corpus to be missing and no
# section that can legitimately not run. Measured from a green run on
# 2026-08-10, and again on 2026-08-12 when section 0b took it from 31 to 34.
# Anything under this means a section stopped executing, and on a file whose
# defects all present as silent success that is exactly the report we must not
# accept.
LEDGER = checks.Ledger("dat writer", floor=34)
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


def main():
    tmp = tempfile.mkdtemp(prefix="rurik-datwrite-")
    print(f"synthetic archive: {FILE_SIZE} B, {ENTRY_COUNT} rows, in {tmp}")
    try:
        sections(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
