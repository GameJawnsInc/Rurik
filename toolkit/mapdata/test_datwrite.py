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
import builtins
import contextlib
import io
import json
import os
import random
import shutil
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ENTRY_SIZE  # noqa: E402
import datwrite  # noqa: E402
# Section 12d's sabotage swaps `json.loads` on the module that OWNS
# `read_journal`, and since 2026-09-11 that is `datjournal`, not `datwrite` --
# `datwrite` no longer imports `json` at all, so `datwrite.json` is an
# AttributeError and the `finally:` that restores it would take the section down
# whatever the check's verdict.
import datjournal  # noqa: E402
import datcheck  # noqa: E402
import datmove  # noqa: E402
# `datplan` is imported for section 11h's sabotage and nothing else. `datwrite`
# imports it INSIDE the grow gate rather than at module level -- circularly,
# datmove imports datwrite -- so the stub has to be installed on the module
# object itself, which is the same object sys.modules hands the gate.
import datplan  # noqa: E402
import gwdat  # noqa: E402
import gwenc  # noqa: E402
import checks  # noqa: E402
# Fixture builders borrowed across the module boundary, and each for a stated
# reason rather than for convenience. `test_datcheck`'s archive is the one whose
# payload rows sit at index >= 16, so all TEN of datcheck's open-time rules can
# pass on it -- this file's own fixture is permanently 9/10 because its rows are
# at 4..7 (measured both ways 2026-08-18). `test_datmove`'s archive is the one
# with measured free runs and a planted container generation, which is what a
# relocation needs. `test_unitauthor.py` already does the same thing with the
# first of them.
import test_datcheck as tdc  # noqa: E402
import test_datmove as tdm  # noqa: E402

# FLOOR: the seventy-eight checks below, every one of which runs
# unconditionally -- the fixture is built by this file, so there is no corpus
# to be missing and no section that can legitimately not run. Measured from a
# green run on 2026-08-10, again on 2026-08-12 when section 0b took it from 31
# to 34, again on 2026-08-14 when section 7 (--restore) took it from 34 to 66,
# and again on 2026-08-16 when section 8 (--relink-plain) took it from 66 to
# 78. Anything under this means a section stopped executing, and on a file
# whose defects all present as silent success that is exactly the report we
# must not accept.
#
# Section 7's three sabotages are the measurement of which of ITS checks matter,
# and they are run rather than argued: stubbing `claimants()` to [] lets the
# claimed-extent restore through, stubbing `check_identity()` lets a wrong-file
# restore through, and a donor whose compression is flattened to 0 leaves the row
# at 0 while the PAYLOAD stays byte-identical -- the last one is why 7b checks the
# compression field separately, since the stored bytes cannot tell the two apart.
#
# RAISED 78 -> 87 on 2026-08-17 with the header-refusal section. That region --
# file offsets [0x00,0x10), the magic/headerSize/blockSize/CRC the client's
# header gate reads -- had been protected by ABSENCE: no caller wrote there, so
# nothing could go wrong, so nothing checked. It is the one corruption with no
# recovery path (ArchiveOpen returns 0 with no log line and tail-jumps to
# ArchiveCreate, which overwrites the whole file), so the refusal is tested by
# REACHING FOR IT at every field and at both sides of the 0x0F/0x10 boundary,
# each attempt on its own fresh fixture. MEASURED from a green run: 87.
#
# RAISED 87 -> 136 on 2026-08-18 with sections 9 and 10, the compression-8 write
# verb and the C-6 guard. MEASURED from a green run, not projected: 136. These
# sections cost ~10 s, all of it `gwenc.encode`, and need no vault -- a 2,720 B
# payload compresses in about twenty milliseconds, so the whole pipeline of
# FINDINGS A8 minus the client runs on a bare machine. The load-bearing part of
# the raise is section 9d: it stages FINDINGS C-6 deliberately and MEASURES that
# every rule this project owns stays green over an unreadable file, which is
# what makes every refusal after it worth having rather than decorative.
#
# RAISED 138 -> 199 on 2026-08-19 with sections 11 and 12: the grow-back verb and
# the journal as a durable file. MEASURED from a green run, not projected: 199.
# Both sections are sabotage-first, because that is the only technique in this
# arc that has reliably distinguished a check from a comment (FINDINGS 14.3), and
# two of the four grow-gate conditions cannot be reached on a 4 KB fixture at
# all without one -- row 3 happens to describe the MFT here, and an archive this
# small has no container rotation region. 11e's stub is the one that matters
# most: with the pre-write refusal removed the write LANDS, which is the only
# way `datmove.overlaps` can ever be made to fire. Sections 11 and 12 add no
# vault dependency and cost about a second.
#
# RAISED 199 -> 212 on 2026-08-20 with section 13, the grow gate's TYPED
# refusal. MEASURED from a green run, not projected: 212. The section needs no
# vault and cannot skip -- it builds its own fixtures the way section 11 does.
# The load-bearing checks in it are the two NEGATIVES: an ordinary refusal
# carries no token and is not a `GrowGateRefused`, which is what makes the type
# worth joining on at all. A token on every failure would be worse than none,
# and that is the shape a careless version of this change would have.
LEDGER = checks.Ledger("dat writer", floor=212)
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


def _incompressible(n, seed=20260818):
    """Deterministic PRNG bytes, so `gwenc` output is LARGER than the payload.

    `pattern()` compresses about 12x, which is why a "too big for its reservation"
    fixture built from it silently stopped testing the relocation guard and became a
    duplicate of the C-6 check -- see the comment at the `toobig` case. Anything that
    must exceed a reservation after compression has to be incompressible.
    """
    return random.Random(seed).randbytes(n)


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


def install_rename(path, plain, renamed):
    """Turn the fixture into a mid-replacement archive: rename PLAIN's pair.

    This is the state `FcArchive` leaves behind when it has requested a
    replacement (studies/maprows/FINDINGS.md section 8): the file-id table
    carries `id | 0x80000000` and the plain id stops resolving. Longhand and
    not through datwrite, because the state under test must not be built by
    the code under test.
    """
    off, size, _comp, _flags = ROWS[ROW_IDTABLE]
    with open(path, "r+b") as fh:
        fh.seek(off)
        table = bytearray(fh.read(size))
        hits = [i for i in range(size // 8)
                if struct.unpack_from("<II", table, i * 8)[0] == plain]
        assert len(hits) == 1, hits
        struct.pack_into("<I", table, hits[0] * 8, renamed)
        fh.seek(off)
        fh.write(bytes(table))
        fh.seek(MFT_OFF)
        mft = bytearray(fh.read(MFT_SIZE))
        struct.pack_into("<I", mft, ROW_IDTABLE * ENTRY_SIZE + ENTRY_CRC,
                         binascii.crc32(bytes(table)))
        struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + ENTRY_CRC,
                         self_crc(mft))
        fh.seek(MFT_OFF)
        fh.write(bytes(mft))


def section_relink(tmp):
    """--relink-plain: the DnArchive re-link, minus the download.

    The fixture's pair (0x1000 -> ROW_SHRINK) is renamed to 0x80001000 by
    install_rename, so the pristine fixture IS the correct post-relink state --
    which turns the strongest available assertion into one line: after the
    relink the whole archive must be byte-identical to the file build_archive
    wrote, table dword, entry-2 crc and MFT self-crc all at once.
    """
    plain, renamed = 0x1000, 0x80001000

    print("\n8. --relink-plain undoes the rename exactly")
    t, _ = fresh(tmp, "relink.dat")
    pristine = blob(t)
    install_rename(t, plain, renamed)
    suspended = blob(t)
    check(suspended != pristine, "fixture is in the renamed state")
    code, _ = run_cli("--dat", t, "--verify")
    check(code == 0, "CONTROL: mid-replacement is itself a valid archive -- "
                     "the state is real, not a sabotage")

    j = os.path.join(tmp, "j8.json")
    code, out = run_cli("--dat", t, "--journal", j,
                        "--relink-plain", hex(plain))
    check(code != 0 and blob(t) == suspended,
          "without --confirm the plan is printed and nothing is written")
    with quiet():
        code, _ = run_cli("--dat", t, "--journal", j,
                          "--relink-plain", hex(plain), "--confirm")
    check(code == 0, f"the relink runs (exit {code})")
    check(blob(t) == pristine,
          "the archive is byte-identical to its pre-rename self -- table "
          "dword, entry-2 crc and MFT self-crc, in one comparison")
    code, _ = run_cli("--dat", t, "--verify")
    check(code == 0, "and all three checksum rules hold")

    print("\n8b. the refusals")
    code, out = run_cli("--dat", t, "--journal",
                        os.path.join(tmp, "j8b1.json"),
                        "--relink-plain", hex(plain), "--confirm")
    check(code != 0 and "already binds" in out and blob(t) == pristine,
          "a plain id that already binds is refused, archive untouched")
    code, out = run_cli("--dat", t, "--journal",
                        os.path.join(tmp, "j8b2.json"),
                        "--relink-plain", "0x2000", "--confirm")
    check(code != 0 and blob(t) == pristine,
          "an id present under neither spelling is refused")
    code, out = run_cli("--dat", t, "--journal",
                        os.path.join(tmp, "j8b3.json"),
                        "--relink-plain", hex(renamed), "--confirm")
    check(code != 0 and "PLAIN" in out and blob(t) == pristine,
          "the bit-31 spelling as the ARGUMENT is refused, naming the plain "
          "form")

    print("\n8c. the journal is the way back")
    code, _ = run_cli("--revert", j)
    check(code == 0 and blob(t) == suspended,
          "revert restores the renamed state exactly")
    code, _ = run_cli("--dat", t, "--verify")
    check(code == 0, "and the reverted archive still verifies")

    print("\n8d. a corrupt target row is not made addressable")
    t2, _ = fresh(tmp, "relink-badrow.dat")
    install_rename(t2, plain, renamed)
    with quiet():
        run_cli("--dat", t2, "--journal", os.path.join(tmp, "j8d.json"),
                "--corrupt-crc", str(ROW_SHRINK))
    before = blob(t2)
    code, out = run_cli("--dat", t2, "--journal",
                        os.path.join(tmp, "j8d2.json"),
                        "--relink-plain", hex(plain), "--confirm")
    check(code != 0 and "CRC" in out and blob(t2) == before,
          "a row failing its own crc refuses the relink, archive untouched")


def section_header_refusal(tmp):
    """The 32-byte header's first 16 bytes are the one unrecoverable region.

    `Writer.put` refuses any write overlapping [0x00,0x10) -- magic, headerSize,
    blockSize and the CRC that covers them. It is not a warning and there is no
    override flag, because the failure mode has no recovery: the client's header
    gate returns 0 from a tail with NO log call and tail-jumps to ArchiveCreate,
    which writes a fresh empty archive over a 4.2 GB file.

    This module never had a caller that wrote there, so before 2026-08-17 the
    region was protected by ABSENCE. Absence is not protection -- it is luck
    that nobody has added a caller yet -- and it is exactly the shape of hazard
    this repo's own rule ("a rule nothing checks is a wish") is about. So the
    refusal is tested by REACHING FOR IT, at every boundary.
    """
    print("\nheader refusal: the region whose corruption is unrecoverable")

    # EVERY ATTEMPT GETS ITS OWN ARCHIVE. The first draft of this section shared
    # one fixture, and the CONTROL below -- which is SUPPOSED to succeed --
    # wrote eight zero bytes over mftOffset and left the archive unopenable for
    # the next attempt. A permitted write is still a destructive one, and a
    # section whose later checks depend on an earlier check's side effect is
    # measuring the order it happens to run in.
    counter = [0]

    def attempt(offset, n):
        counter[0] += 1
        path, _ = fresh(tmp, f"refuse-{counter[0]}.dat")
        before = blob(path)
        w = datwrite.Writer(path, journal_path=os.path.join(tmp, "refuse.jrnl"))
        try:
            w.put(offset, b"\x00" * n, f"deliberate write at 0x{offset:X}")
            return None, path, before
        except SystemExit as exc:
            return str(exc), path, before
        finally:
            w.close()

    def refused(offset, n):
        msg, path, before = attempt(offset, n)
        # A refusal that still wrote is worse than no refusal, so both halves
        # are asserted together and neither can pass on its own.
        return msg, blob(path) == before

    for off, n, label in ((0x00, 4, "the magic"),
                          (0x04, 4, "headerSize"),
                          (0x08, 4, "blockSize"),
                          (0x0C, 4, "the header CRC itself"),
                          (0x0F, 1, "the CRC's last byte"),
                          (0x00, 32, "the whole header")):
        msg, intact = refused(off, n)
        check(msg is not None and "REFUSED" in msg and intact,
              f"a write over {label} is REFUSED, and nothing was written",
              f"0x{off:X}+{n}: "
              f"{'refused' if msg else 'WENT THROUGH'}, "
              f"archive {'intact' if intact else 'MODIFIED'}")

    # THE BOUNDARY, both sides. A write starting at 0x10 does not overlap
    # [0x00,0x10) and must go through; a write starting at 0x0E does overlap it
    # and must not. This is the pair that catches a half-open interval written
    # as containment -- the single most likely way to get this check wrong.
    msg, path, before = attempt(0x10, 8)
    check(msg is None and blob(path) != before,
          "CONTROL: 0x10 (mftOffset) is OUTSIDE the region and IS written",
          "the refusal is an interval, not a blanket ban on the first block")
    msg, intact = refused(0x0E, 4)
    check(msg is not None and intact,
          "but a write straddling 0x0F/0x10 is refused -- overlap, not "
          "containment")

    msg, _path, _before = attempt(0x00, 4)
    check("ArchiveCreate" in msg and "no log line" in msg,
          "the refusal NAMES the failure mode, so nobody removes it as noise")


def section_compressed(tmp):
    """A row THIS PROJECT COMPRESSED, written into an archive and read back.

    This is the pipeline of studies/archivewrite/FINDINGS.md A8 minus the client:
    payload -> `gwenc.encode` -> `Writer.replace(compression=8)` -> the archive ->
    `Archive.read()` -> `gwdat.decompress` -> the payload again. Everything in it
    is synthetic; `gwenc` turns a 2,720-byte payload into 120 stored bytes in
    about twenty milliseconds, so no vault archive is needed and the floor stays
    a real floor on a bare machine.

    WHY THE FIXTURE COMES FROM `test_datcheck`. This file's own archive puts its
    payload rows at indices 4..7, below `INDEX_FIRST_FILE = 16`, so
    `datcheck.preflight`'s "no row below index 16 touched" rule is PERMANENTLY
    red on it -- 9 of 10, before anything is written. A section claiming ten
    open-time rules pass has to run on an archive where ten can. Measured both
    ways 2026-08-18: this file's fixture 9/10, `test_datcheck`'s 10/10.
    `test_unitauthor.py` already imports that builder across the module boundary
    for the same reason.

    THE HARD PART IS NOT THE WRITE, IT IS KNOWING THE WRITE WAS RIGHT. The entry
    CRC is over the STORED bytes, so a compression-8 row holding a wrong payload
    satisfies all three checksum rules; `datcheck.py` contains zero references to
    compression codes, so none of its ten open-time rules can see it either.
    Part E below MEASURES that blind spot rather than asserting it -- it stages
    FINDINGS C-6 on purpose and shows the resulting archive is fully green while
    the file is unreadable. Every refusal check after it is calibrated against
    that: a guard whose failure mode is invisible has to be tested by reaching
    for it, and the corruptions in part F are EARNED -- a real compressed payload
    with one bit flipped, and a real one with its mandatory tail word removed
    (FINDINGS 13.3's measured silent-short-decode), not a staged blob of noise.
    """
    print("\n9. a row THIS PROJECT COMPRESSED, written and read back")

    def fresh10(name):
        """A fixture on which all TEN open-time rules can pass. See above."""
        path = os.path.join(tmp, name)
        tdc.build_archive(path)
        return path

    def clear(path):
        items, _info = datcheck.preflight(path)
        return sum(1 for c in items if c.ok), [c.name for c in items if not c.ok]

    payload = (b"ffna" + bytes(range(64))) * 40           # 2,720 B, structured
    stored = gwenc.encode(payload)                        # verify=True by default

    base = fresh10("comp-baseline.dat")
    ok, red = clear(base)
    check(ok == 10 and not red,
          "the fixture starts 10 of 10 clear on datcheck's open-time rules",
          f"{ok}/10, red: {red}")
    resv = reservation(tdc.ROWS[tdc.ROW_B][1])
    check(len(stored) < resv,
          f"gwenc turns the {len(payload)} B payload into {len(stored)} stored "
          f"bytes, inside row {tdc.ROW_B}'s {resv}-byte reservation -- so this "
          f"section tests an IN-PLACE compressed write, not a relocation")
    check(len(stored) > 3 and stored[3] == datwrite.HUFFMAN_PROLOGUE_BYTE,
          f"and they carry the measured compression-8 prologue "
          f"(byte 3 == 0x{datwrite.HUFFMAN_PROLOGUE_BYTE:02X}, 258,708 rows, "
          f"FINDINGS 13.3)",
          f"byte 3 is 0x{stored[3]:02X}")

    print("\n9a. END TO END -- the headline, through the real command line")
    dat = fresh10("comp-e2e.dat")
    journal = dat + ".journal.json"
    code, out = run_cli("--dat", dat, "--journal", journal,
                        "--verify", "--replace", str(tdc.ROW_B),
                        "--data", spill(tmp, "c8.bin", stored),
                        "--compression", "8",
                        "--expect", spill(tmp, "c8.payload", payload))
    check(code == 0, f"--verify --replace --compression 8 exits 0 (got {code})")

    # A FRESH Archive, never the Writer's -- read_mft()'s documented trap. A
    # handle opened before the write can answer a seek from a pre-write buffer
    # window, and on an archive this small the window covers the whole file.
    with Archive(dat) as ar:
        e = ar.row(tdc.ROW_B)
        size_now, comp_now, crc_now = e.size, e.compression, e.crc
        raw_now = ar.raw(e)
        read_back = ar.read(e)
    check(read_back == payload,
          f"THE ROW READS BACK AS THE ORIGINAL {len(payload)} B PAYLOAD -- "
          f"gwenc -> the archive -> unmodified gwdat.decompress",
          f"got {len(read_back)} B, "
          f"{'identical' if read_back == payload else 'DIFFERENT'}")
    check(comp_now == 8,
          f"the compression field says 8 and was NOT flattened to 0 "
          f"(got {comp_now})")
    check(size_now == len(stored),
          f"the size field is the STORED length {len(stored)}, not the "
          f"{len(payload)}-byte payload length (got {size_now})")
    check(raw_now == stored,
          "the bytes on disk are exactly the bytes gwenc emitted")
    check(binascii.crc32(raw_now) == crc_now,
          f"the entry crc covers the STORED bytes "
          f"(0x{crc_now:08X}) -- the domain FINDINGS 1.1 measured on retail's "
          f"own compression-8 rows, confirmed again here read-only")
    off = tdc.ROWS[tdc.ROW_B][0]
    tail = blob(dat)[off + len(stored):off + resv]
    check(tail == b"\x00" * (resv - len(stored)),
          f"the {resv - len(stored)}-byte tail of the reservation is zeroed -- "
          f"replace()'s whole-reservation write survives the compressed path")

    print("\n9b. and the archive's own rules all still hold")
    ok, red = clear(dat)
    check(ok == 10 and not red,
          "all TEN of datcheck's open-time rules pass afterwards",
          f"{ok}/10, red: {red}")
    sweep = datcheck.crc_sweep(dat)
    check(not sweep["bad"],
          f"datcheck --crc-sweep finds 0 bad payload crcs across "
          f"{sweep['checked']} rows",
          f"bad: {sweep['bad']}")
    with quiet():
        bad = datwrite.verify(dat)
    check(bad == 0, "the file header crc and the MFT self-crc still hold")
    with quiet():
        bad = datwrite.check_rows(dat, [tdc.ROW_B])
    check(bad == 0, f"and row {tdc.ROW_B}'s own entry crc rule holds")

    print("\n9c. the compression field MOVES 0 -> 8, and --revert moves it back")
    # Row B was already compression 8, so its field never had to change there.
    # Row A is compression 0, which is the case that exercises the field write
    # AND the revert of it -- and the case a donor restore could never reach.
    dat = fresh10("comp-field.dat")
    original = blob(dat)
    journal = dat + ".journal.json"
    code, out = run_cli("--dat", dat, "--journal", journal,
                        "--replace", str(tdc.ROW_A),
                        "--data", spill(tmp, "c8a.bin", stored),
                        "--compression", "8",
                        "--expect", spill(tmp, "c8a.payload", payload))
    with Archive(dat) as ar:
        e = ar.row(tdc.ROW_A)
        check(code == 0 and e.compression == 8 and ar.read(e) == payload,
              f"row {tdc.ROW_A} goes compression 0 -> 8 and reads back as the "
              f"payload",
              f"exit {code}, compression {e.compression}")
    edits = json.load(open(journal))["edits"]
    comp_off = datwrite.row_offset(Archive(dat), tdc.ROW_A) \
        + datwrite.ENTRY_COMP_OFF
    check(any(ed["offset"] == comp_off for ed in edits),
          "the journal records the compression field's own two bytes, so the "
          "one field no checksum can see is revertible")
    code, out = run_cli("--revert", journal)
    check(code == 0 and blob(dat) == original,
          "--revert puts the archive back BYTE FOR BYTE, compression field "
          "included",
          f"exit {code}, "
          f"{'identical' if blob(dat) == original else 'DIFFERS'}")

    print("\n9d. THE BLIND SPOT, measured rather than asserted (FINDINGS C-6)")
    # Stage the exact state `datmove` used to produce: correct compressed bytes,
    # correct crc, correct size -- and the compression code saying 0. It has to
    # be poked in, because the verb now refuses to create it, which is the whole
    # point of the rung. The self-crc is fixed afterwards so the archive is as
    # green as C-6 leaves it, not merely as green as a sloppy sabotage leaves it.
    dat = fresh10("comp-c6.dat")
    w = datwrite.Writer(dat, dat + ".journal.json")
    try:
        with quiet():
            w.replace(tdc.ROW_B, stored, compression=8, expect=payload)
    finally:
        w.close()
    tdc.poke_row(dat, tdc.ROW_B, extra=0)
    w = datwrite.Writer(dat, dat + ".journal2.json")
    try:
        with quiet():
            w.fix_mft_self_crc()
    finally:
        w.close()
    ok, red = clear(dat)
    sweep = datcheck.crc_sweep(dat)
    with quiet():
        bad = datwrite.verify(dat)
    with Archive(dat) as ar:
        e = ar.row(tdc.ROW_B)
        wrong = ar.read(e)
    check(ok == 10 and not sweep["bad"] and bad == 0,
          "a row marked STORED whose bytes are still compressed passes ALL TEN "
          "open-time rules, the crc sweep and all three checksum rules",
          f"{ok}/10, {len(sweep['bad'])} bad crcs, {bad} checksum failures")
    check(wrong != payload,
          "...while the file is UNREADABLE -- a green archive holding a broken "
          "file, and nothing we own can refute it by inspection",
          f"read() returned {len(wrong)} B, payload is {len(payload)} B")
    check(binascii.crc32(wrong) == e.crc,
          "the crc still matches, because it was always over the STORED bytes "
          "and those did not change -- which is exactly why the check has to "
          "happen BEFORE the write")

    print("\n9e. the verify arm fires, on EARNED corruption")

    def refuse_replace(name, row, data, **kw):
        """Try a replace on a fresh fixture. -> (message or None, intact, journal)."""
        path = os.path.join(tmp, f"refuse-c8-{name}.dat")
        tdc.build_archive(path)
        before = blob(path)
        jrnl = path + ".journal.json"
        w = datwrite.Writer(path, jrnl)
        msg = None
        try:
            with quiet():
                w.replace(row, data, **kw)
        except SystemExit as exc:
            msg = str(exc)
        finally:
            w.close()
        return msg, blob(path) == before, os.path.exists(jrnl)

    flipped = bytearray(stored)
    flipped[len(flipped) // 2] ^= 0x01
    msg, intact, jrnl = refuse_replace("flip", tdc.ROW_B, bytes(flipped),
                                       compression=8, expect=payload)
    check(msg is not None and intact and not jrnl,
          "ONE FLIPPED BIT inside a real compressed payload is REFUSED, nothing "
          "is written and no journal is left -- and note the corrupt stream "
          "decodes to the right LENGTH without raising, so only the byte "
          "comparison can see it",
          f"{'refused' if msg else 'WENT THROUGH'}, "
          f"archive {'intact' if intact else 'MODIFIED'}")
    check(msg is not None and "NOT the expected payload" in msg,
          "and the refusal says what is wrong, not merely that something is")

    msg, intact, jrnl = refuse_replace("short", tdc.ROW_B, stored[:-4],
                                       compression=8, expect=payload)
    check(msg is not None and intact and not jrnl,
          "a real payload with its mandatory tail word REMOVED is refused -- "
          "FINDINGS 13.3's measured silent short decode, the corruption that "
          "raises nothing and passes every checksum",
          f"{'refused' if msg else 'WENT THROUGH'}")

    for name, why, row, data, kw in (
            ("noexpect", "compression 8 with no declared payload",
             tdc.ROW_B, stored, dict(compression=8)),
            ("empty", "a zero-length compression-8 row",
             tdc.ROW_B, b"", dict(compression=8, expect=b"")),
            ("plain8", "plaintext declared as compression 8 (the shape "
                       "cross-check, byte 3)",
             tdc.ROW_B, b"ffna" * 20, dict(compression=8, expect=b"ffna" * 20)),
            ("code3", "a compression code that is neither 0 nor 8",
             tdc.ROW_B, stored, dict(compression=3, expect=payload)),
            ("c6", "compressed bytes declared as compression 0 -- C-6 itself",
             tdc.ROW_B, stored, {}),
            ("c6small", "compressed bytes from a payload too SMALL to carry "
                        "retail's 0x01 0x02 marker -- the case a byte-marker "
                        "guard misses and a decoding one does not",
             tdc.ROW_B, gwenc.encode(b"tiny"), {}),
            ("mismatch", "a stored write whose declared payload is not its bytes",
             tdc.ROW_B, b"aaaa", dict(expect=b"bbbb")),
            # CORRECTED 2026-08-18. This case was labelled "a compressed payload past
            # the reservation (still a relocation, and still refused)" and it was NOT
            # testing that: `pattern(3, 40000)` compresses ~12x, to 484 stored bytes
            # against ROW_A's 512-byte reservation, so it never reached the relocation
            # guard at all -- it was a second copy of the C-6 check wearing a false
            # label, and a skeptic proved it by disabling ONLY the C-6 arm and watching
            # this line go red. "A compressed payload too big for its reservation is
            # refused" was therefore UNTESTED.
            #
            # The trap was caught 40 lines below (`section_c6_guard` switched to a PRNG
            # payload for exactly this reason) and missed here. Fourth recurrence of
            # the FINDINGS 10.6 / 12.7 / 13.6 pattern in this arc: a check whose label
            # claims more than the artifact does.
            #
            # Incompressible bytes make the stored form BIGGER than the payload, so
            # this now genuinely exceeds the reservation and genuinely reaches the
            # relocation refusal, with `expect` supplied so the C-6 arm cannot be what
            # fires.
            ("toobig", "a compressed payload past the reservation -- a "
                       "relocation, refused BEFORE the declaration is consulted",
             tdc.ROW_A, gwenc.encode(_incompressible(4000)),
             dict(compression=8, expect=_incompressible(4000))),
    ):
        msg, intact, jrnl = refuse_replace(name, row, data, **kw)
        check(msg is not None and intact and not jrnl,
              f"REFUSED: {why}",
              f"{'refused' if msg else 'WENT THROUGH'}, "
              f"archive {'intact' if intact else 'MODIFIED'}, "
              f"journal {'left' if jrnl else 'absent'}")

    msg, intact, _j = refuse_replace("hdr", tdc.ROW_HEADER, stored,
                                     compression=8, expect=payload)
    check(msg is not None and "ArchiveCreate" in msg and intact,
          "and the compressed path INHERITS the header refusal: a row at offset "
          "0 is refused by _refuse_header, naming the silent wipe")

    print("\n9f. and the controls, so none of that is a blanket ban")
    msg, intact, _j = refuse_replace("ctl8", tdc.ROW_B, stored,
                                     compression=8, expect=payload)
    check(msg is None and not intact,
          "CONTROL: the same fixture, the same bytes, a correct declaration -- "
          "the write GOES THROUGH")
    msg, intact, _j = refuse_replace("ctl0", tdc.ROW_B, b"plain payload bytes")
    check(msg is None and not intact,
          "CONTROL: the plain path with no keyword at all is untouched -- "
          "exactly what every existing caller passes")
    with Archive(os.path.join(tmp, "refuse-c8-ctl0.dat")) as ar:
        e = ar.row(tdc.ROW_B)
        check(e.compression == 0 and ar.raw(e) == b"plain payload bytes",
              "...and it still marks the row STORED, which is what iconset, "
              "rebloat, textwrite and the six a4stage scripts depend on")
    marked = b"\xAA\xBB\x01\x02" + b"not actually compressed"
    check(not datwrite.looks_compressed(marked),
          "CONTROL: bytes that merely CARRY the 0x01 0x02 marker but do not "
          "decode are not treated as compressed -- the guard decides by "
          "decoding, so it does not refuse plaintext for a two-byte coincidence")
    msg, intact, _j = refuse_replace("hatch", tdc.ROW_B, marked)
    check(msg is None and not intact,
          "...and such a payload writes stored with no keyword at all")

    # THE DANGEROUS HALF OF THE HATCH, added 2026-08-18 after a skeptic drove C-6
    # straight through it. The control above uses bytes that do NOT decode, so it
    # only ever exercised the harmless half. `expect == data` is trivially true for
    # ANY bytes, so when the C-6 arm was gated on `expect is None`, pointing
    # --expect at the same file as --data waived it:
    #
    #     datwrite.py --dat X --replace N --data s.bin --compression 0 --expect s.bin
    #
    # Exit 0, preflight 10 of 10, sweep 0 bad, log line indistinguishable from an
    # ordinary stored replace, and the file unreadable. The arm now consults the
    # decode whether or not `expect` was given, and the override is a separate
    # awkward argument that announces itself.
    msg, intact, _j = refuse_replace("hatch_real", tdc.ROW_B, stored,
                                     expect=stored)
    check(msg is not None and "C-6" in msg and intact,
          "THE HATCH IS CLOSED: genuine compressed bytes declared compression 0 "
          "with expect=data -- the shape that reached the archive through the "
          "documented CLI -- are REFUSED, naming C-6, with nothing written")
    msg, intact, _j = refuse_replace("hatch_override", tdc.ROW_B, stored,
                                     expect=stored, stored_lookalike_ok=True)
    check(msg is None and not intact,
          "...and the deliberate override still lets a caller through, so this "
          "is a gate rather than a ban -- the 4 of 38,621 real stored rows that "
          "genuinely decode still have a route")

    # THE RECALL AND THE FALSE-POSITIVE RATE, both measured here rather than
    # taken from the docstring. A guard against a silent whole-file corruption
    # is only worth what its miss rate is, and the byte-marker version of this
    # missed six of eighteen gwenc outputs -- every one of them a small payload.
    # 0 is NOT in this list any more, and its absence is checked rather than
    # assumed: `gwenc.encode(b"")` refuses as of 2026-08-19 (a zero-block stream
    # is a shape no retail comp-8 row has), so asking for one here would raise
    # out of the test rather than measure recall. Section 11 covers that refusal
    # from both sides.
    sizes = (1, 4, 64, 100, 256, 1000, 4000)
    fails = [n for n in sizes
             if not datwrite.looks_compressed(
                 gwenc.encode(random.Random(n).randbytes(n)))]
    check(not fails,
          f"every one of {len(sizes)} gwenc streams across the whole size range "
          f"is recognised as compressed, INCLUDING the sub-256-byte payloads a "
          f"byte marker misses",
          f"missed: {fails}")
    plains = [pattern(s, 300) for s in range(200)] \
        + [random.Random(s).randbytes(64) for s in range(200)] \
        + [b"ffna" + bytes(range(200)), b"\x00" * 1000, bytes(range(256)) * 4]
    fp = sum(1 for p in plains if datwrite.looks_compressed(p))
    check(fp == 0,
          f"and 0 of {len(plains)} plaintext payloads are mistaken for "
          f"compressed ones, so the guard is not a tax on the stored path",
          f"{fp} false positive(s)")
    # WHAT THE TRAILER HALF OF THE TEST ACTUALLY BUYS, isolated. `declared ==
    # len(back)` is true by construction whenever the decode loop terminates
    # normally -- the declared size IS the loop's bound -- so it refutes exactly
    # one thing: a stream that runs out of input first. That is FINDINGS 13.3's
    # measured silent short decode, and this is the check that shows the clause
    # is not decoration. It is a small claim, made small on purpose.
    check(not datwrite.looks_compressed(stored[:-4]),
          "a compressed stream missing its mandatory tail word is NOT accepted "
          "as compressed -- the one thing the trailer-agreement clause can "
          "refute, since the declared size is otherwise the decoder's own "
          "termination bound")


def section_c6_guard(tmp):
    """`datmove` relocating compressed bytes: the trap, now a refusal.

    Separate section and a separate fixture because a MOVE needs free space to
    move into, and `test_datmove`'s archive is the one built with measured free
    runs and a planted container generation. The guard itself is shared code
    (`datwrite.declaration_fault`), so what is tested here is the wiring and the
    fact that the module's default path did not change -- `textwrite.py`,
    `deploy.py`'s subprocess and the six `a4stage*.py` scripts under
    `vault/research/archivewrite/` all call `move()` for its unconditional
    compression 0 and none of them was edited.
    """
    print("\n10. datmove: no more silent relocation of compressed rows")

    # DELIBERATELY INCOMPRESSIBLE, and it has to be. `pattern()` compresses ~12x,
    # which puts the stored form back inside the row's own reservation and
    # `plan_move` correctly refuses it as "it fits where it is" -- a move that
    # never happens tests nothing. A deterministic PRNG payload encodes to
    # slightly MORE than it started as (2,000 -> 2,080 B here; gwenc's framing
    # costs 80 B it cannot win back), which is the only way to get a compressed
    # payload that genuinely needs to relocate on a fixture this size.
    payload = random.Random(20260818).randbytes(2000)
    stored = gwenc.encode(payload)

    def attempt(name, data, **kw):
        path = os.path.join(tmp, f"move-{name}.dat")
        tdm.build_archive(path)
        before = blob(path)
        jrnl = path + ".journal.json"
        msg = None
        try:
            with quiet():
                datmove.move(path, tdm.ROW_BIG, data, jrnl, confirm=True, **kw)
        except datmove.Refused as exc:
            msg = str(exc)
        return msg, path, blob(path) == before

    old_res = tdm.reservation(tdm.ROWS[tdm.ROW_BIG][1])
    check(len(stored) > old_res,
          f"the compressed payload is {len(stored)} B against row "
          f"{tdm.ROW_BIG}'s {old_res}-byte reservation, so this really is a "
          f"MOVE and not a replace in disguise")

    msg, _path, intact = attempt("c6", stored)
    check(msg is not None and intact,
          "C-6 FIRES: handing move() a compression-8 payload while leaving the "
          "code at its default 0 is REFUSED, and nothing is written",
          f"{'refused' if msg else 'WENT THROUGH'}, "
          f"archive {'intact' if intact else 'MODIFIED'}")
    check(msg is not None and "compression=8" in msg and "C-6" in msg,
          "and the refusal names the fix and the finding, so it is actionable "
          "rather than merely obstructive")

    msg, _path, intact = attempt("noexpect", stored, compression=8)
    check(msg is not None and intact,
          "declaring compression 8 without the payload a reader must get back "
          "is refused too -- the declaration is not a way to switch the check "
          "off")

    msg, path, intact = attempt("ok8", stored, compression=8, expect=payload)
    check(msg is None and not intact,
          "THE SAFE RELOCATION VERB EXISTS: compression 8 with a verified "
          "payload moves the row",
          f"{msg or 'moved'}")
    with Archive(path) as ar:
        e = ar.row(tdm.ROW_BIG)
        moved_ok = (e.compression == 8 and e.size == len(stored)
                    and binascii.crc32(ar.raw(e)) == e.crc
                    and ar.read(e) == payload)
        new_off = e.offset
    check(moved_ok,
          f"...at its new address 0x{new_off:X}, still marked compression 8, "
          f"crc over the stored bytes, and reading back as the original "
          f"{len(payload)} B payload")
    with Archive(path) as ar:
        bad = datmove.overlaps(ar)
    check(not bad, f"and no two rows share a block afterwards ({len(bad)} pairs)")

    plain = pattern(29, 2000)
    msg, path, intact = attempt("plain", plain)
    check(msg is None and not intact,
          "CONTROL: a plaintext move with no keyword at all still succeeds -- "
          "the six a4stage scripts and deploy.py's subprocess are unaffected")
    with Archive(path) as ar:
        e = ar.row(tdm.ROW_BIG)
        check(e.compression == 0 and ar.raw(e) == plain
              and binascii.crc32(ar.raw(e)) == e.crc,
              "...and it still marks the moved row STORED, byte for byte, with "
              "its crc over what was written")


def journal_lines(path):
    """A journal's raw lines. The format is one record per line -- see Journal."""
    with open(path, "rb") as fh:
        return fh.read().split(b"\n")


def section_growback(tmp):
    """11. THE GROW-BACK: a row put back into blocks it freed itself.

    `replace()` derived its ceiling from `e.size`, the row's CURRENT size, so
    after any shrink the row's own freed blocks became unreachable to it. That is
    the whole of it -- one expression -- and it is fatal for the authoring loop
    this module exists for, because "iterate the encoder, rewrite the row" means
    the SECOND write onto a row the first one shrank. Reproduced below on the
    fixture (1000 B -> 100 B, and a 1000 B payload refused with 1,024 B of the
    row's own extent standing free and claimed by nobody) and priced on the real
    archive at 1,025,536 B for row 11196.

    THE FIX IS AN EXPLICIT CEILING, NOT A GREEDY MAXIMUM, and `11c` is where that
    choice is checked rather than argued: with `grow_to` unset the refusal is
    unchanged, so every caller in the tree and the vault is on the old path.

    WHAT THE GATE HAS TO SEE is four separate conditions, and `claimants()` --
    the only one `restore()` had -- is one of them. Each of the four gets its own
    fixture below, and the two that cannot be reached on this archive without
    help (the live MFT, because row 3 happens to describe it here; and the
    container exclusion, because a 4 KB fixture has no rotation region) are
    reached by SABOTAGE, which is also what proves they are load-bearing.
    """
    print("\n11. the grow-back: a row put back into the blocks it freed")
    dat, _ = fresh(tmp, "grow.dat")
    off = ROWS[ROW_SHRINK][0]
    pristine_res = reservation(ROWS[ROW_SHRINK][1])          # 1024

    small = spill(tmp, "g-small.bin", pattern(9, 100))
    with quiet():
        code, _ = run_cli("--dat", dat, "--journal", os.path.join(tmp, "g1.json"),
                          "--replace", str(ROW_SHRINK), "--data", small)
    _o, size, comp, _c = row_entry_of(dat, ROW_SHRINK)
    check(code == 0 and size == 100 and reservation(size) == 512,
          f"setup: the shrink took row {ROW_SHRINK} to {size} B, and its "
          f"reservation with it -- {pristine_res} -> {reservation(size)} B, with "
          f"{pristine_res - reservation(size)} B of its own extent now outside "
          f"what --replace can see")

    # THE CLIENT'S OWN ALLOCATOR IS ENTITLED TO THESE BLOCKS, so put something
    # there that is neither zero nor ours. It makes the journal's `before` bite
    # over the annexed range instead of being trivially a field of zeros.
    with open(dat, "r+b") as fh:
        fh.seek(off + 512)
        fh.write(b"\xEE" * 512)
    after_shrink = blob(dat)

    with Archive(dat) as ar:
        free = datwrite.claimants(ar, off + 512, off + pristine_res,
                                  exclude=ROW_SHRINK)
    check(not free,
          f"and [0x{off + 512:X}, 0x{off + pristine_res:X}) is claimed by NOBODY "
          f"-- the information needed to allow the write was already computable, "
          f"by a helper in the same file",
          f"claimants: {free}")

    print("\n11a. REFUSED without grow_to -- and the refusal names the remedy")
    big = spill(tmp, "g-big.bin", pattern(77, 1000))
    j2 = os.path.join(tmp, "g2.json")
    code, out = run_cli("--dat", dat, "--journal", j2,
                        "--replace", str(ROW_SHRINK), "--data", big)
    check(code != 0 and blob(dat) == after_shrink and not os.path.exists(j2),
          "a 1000 B payload onto the shrunk row is still refused by default, "
          "archive untouched, no journal left -- every existing caller is on "
          "this path and none of them changes behaviour",
          f"exit {code}")
    check("That is a relocation, not a replacement." in out,
          "the refusal's first sentence is unchanged, because that is the "
          "sentence readers and greps already know")
    check("--grow-to 1000" in out and "claimed by NOBODY" in out,
          "...and because the blocks ARE free, it now names --grow-to rather "
          "than sending the reader to a free-run list that will never offer "
          "this row its own extent back")

    print("\n11b. --grow-to writes AUTHORED bytes into the freed blocks")
    j3 = os.path.join(tmp, "g3.json")
    code, out = run_cli("--dat", dat, "--journal", j3,
                        "--replace", str(ROW_SHRINK), "--data", big,
                        "--grow-to", "1000")
    check(code == 0, f"the same write with --grow-to 1000 exits 0 (got {code})")
    _o2, size2, _c2, crc2 = row_entry_of(dat, ROW_SHRINK)
    body = row_bytes(dat, ROW_SHRINK, 1000)
    check(size2 == 1000 and body == pattern(77, 1000),
          f"row {ROW_SHRINK} is {size2} B and holds the AUTHORED payload -- not "
          f"a donor's, which is the one thing --restore can never do",
          f"{'identical' if body == pattern(77, 1000) else 'DIFFERENT'}")
    check(crc2 == binascii.crc32(pattern(77, 1000)),
          "and its entry crc covers the new stored bytes")
    tail = blob(dat)[off + 1000:off + pristine_res]
    check(tail == b"\x00" * (pristine_res - 1000),
          f"the {pristine_res - 1000} B tail of the GROWN reservation is zeroed "
          f"-- no fragment of what was in the annexed blocks survives")
    with Archive(dat) as ar:
        shared = datmove.overlaps(ar)
    check(not shared,
          f"and no two rows share a block after the grow ({len(shared)} pairs) "
          f"-- the invariant no checksum can see, since each crc covers only "
          f"its own row's bytes")
    with quiet():
        bad = datwrite.verify(dat) + datwrite.check_rows(dat, list(PAYLOAD_ROWS))
    check(bad == 0, "all three checksum rules hold afterwards")
    check("annexing [0x%X,0x%X)" % (off + 512, off + pristine_res) in out,
          "the tool NAMES the annexation and its range as it makes it")
    check("verified" in out and "read back" in out,
          "and it read the payload back through the write handle and said so")

    print("\n11c. the journal covers the ANNEXED region, and --revert proves it")
    doc = json.load(open(j3))
    at_payload = [ed for ed in doc["edits"] if ed["offset"] == off]
    check(len(at_payload) == 1 and at_payload[0]["length"] == pristine_res,
          f"the record at 0x{off:X} spans the whole NEW {pristine_res}-byte "
          f"reservation, not the {512}-byte one the row had",
          f"{at_payload[0]['length'] if len(at_payload) == 1 else at_payload} B")
    check(len(at_payload) == 1
          and binascii.unhexlify(at_payload[0]["before"])
          == after_shrink[off:off + pristine_res],
          "and its `before` holds the annexed blocks' contents exactly, the "
          "0xEE the allocator's stand-in wrote included")
    check(len(at_payload) == 1
          and "annexing" in at_payload[0]["what"],
          "and the `what` string names the annexation, which --revert prints")
    code, out = run_cli("--revert", j3)
    check(code == 0 and blob(dat) == after_shrink,
          "--revert puts the archive back BYTE FOR BYTE, the annexed region "
          "included",
          f"exit {code}, "
          f"{'identical' if blob(dat) == after_shrink else 'DIFFERS'}")

    print("\n11d. grow_to is a STATEMENT, not a request for more")
    dat4, _ = fresh(tmp, "grow-over.dat")
    with quiet():
        run_cli("--dat", dat4, "--journal", os.path.join(tmp, "g4.json"),
                "--replace", str(ROW_SHRINK), "--data", small)
    before4 = blob(dat4)
    j5 = os.path.join(tmp, "g5.json")
    # 512, not 600: the ceiling is a RESERVATION, so `--grow-to 600` and
    # `--grow-to 1000` are the same statement on a 512-byte-block archive and a
    # check written against 600 would test nothing.
    code, out = run_cli("--dat", dat4, "--journal", j5,
                        "--replace", str(ROW_SHRINK), "--data", big,
                        "--grow-to", "512")
    check(code != 0 and blob(dat4) == before4 and not os.path.exists(j5),
          "a payload past the reservation the caller STATED is refused, even "
          "though the geometry would allow it -- a greedy verb would take it "
          "and a shrunk NEIGHBOUR would have no way to say the blocks are its",
          f"exit {code}")
    check("entitled" in out,
          "and the refusal says the number is a claim about what the row was "
          "GIVEN, not a knob to make a write fit")
    code, _ = run_cli("--dat", dat4, "--grow-to", "1000")
    check(code == 2,
          f"--grow-to without --replace exits 2 -- it names no row (got {code})")
    ap = datwrite.build_parser()
    check(not datwrite.is_mutating(
              ap.parse_args(["--dat", dat4, "--verify", "--grow-to", "99"])),
          "and --grow-to is classified read-only: it writes nothing on its own, "
          "so it must not construct a Writer that has nothing to do")

    print("\n11e. the gate: CLAIMANTS, and the post-write assertion behind it")
    dat6, _ = fresh(tmp, "grow-claimed.dat")
    with quiet():
        run_cli("--dat", dat6, "--journal", os.path.join(tmp, "g6.json"),
                "--replace", str(ROW_SHRINK), "--data", small)
    stolen = off + 512
    body7 = row_bytes(dat6, ROW_SMALL, ROWS[ROW_SMALL][1])
    with open(dat6, "r+b") as fh:
        fh.seek(stolen)
        fh.write(body7)
    mft_field(dat6, ROW_SMALL, 0x00, "<Q", stolen)
    before6 = blob(dat6)
    j7 = os.path.join(tmp, "g7.json")
    code, out = run_cli("--dat", dat6, "--journal", j7,
                        "--replace", str(ROW_SHRINK), "--data", big,
                        "--grow-to", "1000")
    check(code != 0 and blob(dat6) == before6 and not os.path.exists(j7),
          f"a grow into blocks row {ROW_SMALL} now owns is REFUSED BEFORE the "
          f"write, archive untouched, no journal",
          f"exit {code}")
    check("CLAIMED" in out and f"row {ROW_SMALL}" in out and "datmove" in out,
          f"and the refusal names row {ROW_SMALL} as the claimant and points at "
          f"datmove.py, rather than saying the archive is full")
    check("--grow-to" not in out,
          "...and does NOT offer --grow-to here, because the blocks are not "
          "this row's to take -- the remedy sentence is chosen by the geometry")

    # SABOTAGE, extending test 7i's established stub to the grow path. With the
    # pre-write refusal gone the write LANDS, and the only thing left standing
    # between the archive and two rows sharing blocks is the post-write
    # `datmove.overlaps` assertion -- which is the whole reason it is there, and
    # the only way it can ever be made to fire.
    real_claimants = datwrite.claimants
    try:
        datwrite.claimants = lambda ar, lo, hi, exclude: []
        code, out = run_cli("--dat", dat6, "--journal",
                            os.path.join(tmp, "g8.json"),
                            "--replace", str(ROW_SHRINK), "--data", big,
                            "--grow-to", "1000")
    finally:
        datwrite.claimants = real_claimants
    check(blob(dat6) != before6,
          "SABOTAGE: with claimants() stubbed to [], the pre-write refusal is "
          "gone and the grow LANDS -- so 11e is load-bearing and not decorative")
    check(code != 0 and "GROW VERIFY FAILED" in out
          and f"rows {ROW_SHRINK} and {ROW_SMALL}" in out,
          "...and the post-write overlap assertion catches it, naming both "
          "rows and telling the operator to revert -- a check that could not "
          "otherwise be made to fire at all",
          f"exit {code}")

    print("\n11f. the gate: EOF, which claimants cannot see at all")
    dat9, _ = fresh(tmp, "grow-eof.dat")
    mft_field(dat9, ROW_SMALL, 0x00, "<Q", FILE_SIZE)
    before9 = blob(dat9)
    mid = spill(tmp, "g-mid.bin", pattern(31, 600))
    j9 = os.path.join(tmp, "g9.json")
    code, out = run_cli("--dat", dat9, "--journal", j9,
                        "--replace", str(ROW_SMALL), "--data", mid,
                        "--grow-to", "600")
    check(code != 0 and blob(dat9) == before9 and not os.path.exists(j9),
          "a grow whose rounded reservation runs past EOF is REFUSED before "
          "the write -- put()'s short-read guard catches it AFTER the decision, "
          "which is a crash rather than a refusal",
          f"exit {code}")
    check("PAST THE END" in out and "4096" in out,
          "and the refusal names the overhang and the file size, the way "
          "datalloc._place does; datcheck rule 5 cannot catch this because it "
          "tests offset + size, not the rounded reservation")

    print("\n11g. the gate: the LIVE MFT, checked independently of row 3")
    dat10, _ = fresh(tmp, "grow-mft.dat")
    before10 = blob(dat10)
    code, out = run_cli("--dat", dat10, "--journal", os.path.join(tmp, "g10.json"),
                        "--replace", str(ROW_SMALL), "--data", mid,
                        "--grow-to", "600")
    check(code != 0 and blob(dat10) == before10,
          f"CONTROL: growing row {ROW_SMALL} into the table's block is refused "
          f"on THIS archive by claimants, because row 3 happens to describe the "
          f"MFT here",
          f"exit {code}")
    check("CLAIMED by row 3" in out, "...and says so, naming row 3")
    # Nothing enforces that row 3 describes the table -- free_runs protects the
    # MFT with its own bitmap rather than by trusting a row, and the client
    # relocates the table during ordinary play. Take row 3 out of the picture
    # and the extent must still be refused, or the protection was incidental.
    try:
        datwrite.claimants = lambda ar, lo, hi, exclude: []
        code, out = run_cli("--dat", dat10, "--journal",
                            os.path.join(tmp, "g11.json"),
                            "--replace", str(ROW_SMALL), "--data", mid,
                            "--grow-to", "600")
    finally:
        datwrite.claimants = real_claimants
    check(code != 0 and blob(dat10) == before10
          and "LIVE MASTER FILE TABLE" in out,
          "SABOTAGE: with claimants() stubbed out the extent is STILL refused, "
          "against the file header's own mft_offset/mft_size -- so the MFT is "
          "protected by a check of its own and not by row 3 happening to exist",
          f"exit {code}")

    print("\n11h. the gate: datplan's WITHHELD container runs")
    # The largest new risk in the whole verb: `replace()` never needed to know
    # about the client's rotation region because it never allocated. Four bytes
    # of setup make the freed run carry an MFT generation head -- datplan's own
    # container_signature, and self-describing, so the entry count at +0x0C says
    # how far it reaches.
    dat11, _ = fresh(tmp, "grow-withheld.dat")
    with quiet():
        run_cli("--dat", dat11, "--journal", os.path.join(tmp, "g12.json"),
                "--replace", str(ROW_SHRINK), "--data", small)
    with open(dat11, "r+b") as fh:
        fh.seek(off + 512)
        fh.write(MFT_MAGIC + b"\x00" * 8 + struct.pack("<I", ENTRY_COUNT))
    before11 = blob(dat11)
    with Archive(dat11) as ar:
        usable, excluded = datplan.classify_runs(ar)
    check(not usable and len(excluded) == 1
          and excluded[0].start_block == (off + 512) // BLOCK,
          f"setup: datplan withholds the freed run at 0x{off + 512:X} -- it "
          f"carries a master file table generation and reads as free only "
          f"because no MFT row points at it",
          f"usable {usable}, excluded {excluded}")
    j13 = os.path.join(tmp, "g13.json")
    code, out = run_cli("--dat", dat11, "--journal", j13,
                        "--replace", str(ROW_SHRINK), "--data", big,
                        "--grow-to", "1000")
    check(code != 0 and blob(dat11) == before11 and not os.path.exists(j13),
          "a grow into a WITHHELD run is refused, archive untouched -- "
          "'unallocated' counts the client's live container generations as free "
          "space, 89.6% of the gap measure on this machine's study copy",
          f"exit {code}")
    check("WITHHOLDS" in out and "master file table" in out,
          "and the refusal quotes Exclusion.why(), so the operator sees WHAT "
          "is in those blocks rather than only that they are off limits")

    real_classify = datplan.classify_runs
    try:
        datplan.classify_runs = lambda ar, runs=None: (
            datplan.free_runs(ar) if runs is None else runs, [])
        code, out = run_cli("--dat", dat11, "--journal",
                            os.path.join(tmp, "g14.json"),
                            "--replace", str(ROW_SHRINK), "--data", big,
                            "--grow-to", "1000")
    finally:
        datplan.classify_runs = real_classify
    check(code == 0 and blob(dat11) != before11,
          "SABOTAGE: with classify_runs stubbed to 'everything usable' the same "
          "grow is ACCEPTED -- so 11h is the check doing the work, and the "
          "difference between free_runs and classify_runs is the difference "
          "between writing into a hole and writing into the MFT the client is "
          "about to rotate back onto",
          f"exit {code}")

    print("\n11i. restore() inherited the three conditions it never had")
    # The factoring is the point: restore() has been run on real 4.2 GB copies
    # with claimants() as its whole gate, so these were live gaps.
    src = ast.parse(open(datwrite.__file__, encoding="utf-8").read())
    fns = {n.name: n for n in ast.walk(src) if isinstance(n, ast.FunctionDef)}

    def calls(node):
        return {c.func.attr for c in ast.walk(node)
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute)}
    check("_grow_gate" in calls(fns["restore"])
          and "_grow_gate" in calls(fns["replace"]),
          "both verbs call the SAME _grow_gate, on the syntax tree -- one copy, "
          "the way row_offset delegates to archive.mft_row_offset after the "
          "planner's private copy printed three wrong addresses for months")
    check("claimants" not in {c.func.id for c in ast.walk(fns["restore"])
                              if isinstance(c, ast.Call)
                              and isinstance(c.func, ast.Name)},
          "and restore() no longer carries its own claimants() call, so the "
          "two gates cannot drift apart")

    donor, _ = fresh(tmp, "grow-donor.dat")
    t12, _ = fresh(tmp, "grow-restore.dat")
    with quiet():
        run_cli("--dat", t12, "--journal", os.path.join(tmp, "g15.json"),
                "--replace", str(ROW_SHRINK), "--data", small)
    with open(t12, "r+b") as fh:
        fh.seek(off + 512)
        fh.write(MFT_MAGIC + b"\x00" * 8 + struct.pack("<I", ENTRY_COUNT))
    before12 = blob(t12)
    code, out = run_cli("--dat", t12, "--journal", os.path.join(tmp, "g16.json"),
                        "--restore", str(ROW_SHRINK), "--from", donor,
                        "--confirm")
    check(code != 0 and "WITHHOLDS" in out and blob(t12) == before12,
          "--restore into a withheld container run is now REFUSED too, which "
          "it was not before the gate was shared -- and --restore is the verb "
          "that has already been used on real 4.2 GB copies")

    print("\n11j. the ZERO-BLOCK stream, refused on the archive side (gap D)")
    # The encoder refuses to MAKE one as of 2026-08-19. This is the other door:
    # the guard has to hold whether or not the bytes came from our encoder, and
    # `gwenc._refuse_zero_block` is stubbed here only to obtain the artifact.
    raised = None
    try:
        gwenc.encode(b"")
    except Exception as exc:                                  # noqa: BLE001
        raised = exc
    check(raised is not None and "NO BLOCKS" in str(raised),
          "CONTROL: gwenc.encode(b'') refuses -- the encoder-side door")
    real_zero = gwenc._refuse_zero_block
    try:
        gwenc._refuse_zero_block = lambda payload: None
        zero_block = gwenc.encode(b"")
    finally:
        gwenc._refuse_zero_block = real_zero
    back, declared = gwdat.decompress(zero_block)
    check(len(zero_block) == 12 and back == b"" and declared == 0
          and zero_block[3] == datwrite.HUFFMAN_PROLOGUE_BYTE,
          f"the artifact is real and every OTHER arm agrees with it: {len(zero_block)} B, "
          f"byte 3 is 0x{zero_block[3]:02X}, it decompresses without raising, "
          f"and its trailer declares {declared} B against a {len(b'')} B "
          f"expectation -- so nothing below the new arm could refuse it")
    fault = datwrite.declaration_fault(zero_block, 8, b"")
    check(fault is not None and "56 B" in fault,
          "declaration_fault REFUSES it, naming retail's measured floor -- the "
          "smallest comp-8 row in dat_study is 56 B and holds a block")
    check(datwrite.declaration_fault(zero_block, 8, None) is not None,
          "and a comp-8 write with NO declared payload is still refused for its "
          "own reason (FINDINGS 14.2 hole 1), which this arm must not displace")
    msg, intact, jrnl = None, None, None
    path = os.path.join(tmp, "zeroblock.dat")
    tdc.build_archive(path)
    was = blob(path)
    w = datwrite.Writer(path, path + ".journal.json")
    try:
        with quiet():
            w.replace(tdc.ROW_B, zero_block, compression=8, expect=b"")
    except SystemExit as exc:
        msg = str(exc)
    finally:
        w.close()
    intact = blob(path) == was
    jrnl = os.path.exists(path + ".journal.json")
    check(msg is not None and intact and not jrnl,
          "and the verb refuses it end to end, nothing written, no journal",
          f"{'refused' if msg else 'WENT THROUGH'}, "
          f"archive {'intact' if intact else 'MODIFIED'}")
    check(datwrite.looks_compressed(zero_block)
          and datwrite.declaration_fault(zero_block, 0, zero_block) is not None,
          "...and the C-6 arm still sees the same bytes as a decodable "
          "compression-8 stream when they are declared STORED, so the two "
          "guards cover the two directions rather than one shadowing the other")


def section_journal(tmp):
    """12. The journal as a DURABLE FILE, not only as a revert mechanism.

    Everything above exercises the journal by reverting it. Nothing exercised it
    as a file that has to survive the crash it exists for, and the three defects
    that left were all in that half:

      * `flush()` opened `"w"` -- truncate -- and re-serialised the whole
        document after EVERY record. MEASURED 4.66x on a 5-record replace of this
        fixture, 5.0x on a 1,029,632 B reservation, and **34.1x / 533 MB** on
        `vault/research/archivewrite/a4run7-flip.journal`, which is 137x the
        3.9 MB of archive its 60 records protect. Quadratic in record count.
      * A torn flush therefore lost the WHOLE journal, not one record, and
        `revert()` died at `json.load` with an unhandled `JSONDecodeError` --
        a traceback rather than a diagnosis, on the tool that exists for exactly
        that moment.
      * No fsync anywhere. `put()` fsyncs the archive; the record that must
        precede it did not.

    The format did NOT move -- 59 old journals under `vault/` and
    `test_datalloc.py`'s prefix replay all read it with a plain `json.load` --
    so `12d` synthesises an old-format journal in the temp directory and replays
    it. Synthesised rather than borrowed on purpose: this file never opens the
    vault (see the module docstring), and that boundary is worth more than the
    realism.
    """
    print("\n12. the journal as a durable file")
    dat, _ = fresh(tmp, "jr.json.dat")
    jrnl = os.path.join(tmp, "jr.journal.json")
    payload = pattern(41, 900)

    real_open = builtins.open
    real_fsync = os.fsync
    modes, wrote, synced = [], [0], []

    class Counting:
        """A file object that reports how many bytes went through it."""

        def __init__(self, fh):
            self._fh = fh

        def write(self, b):
            wrote[0] += len(b)
            return self._fh.write(b)

        def __getattr__(self, name):
            return getattr(self._fh, name)

        def __enter__(self):
            self._fh.__enter__()
            return self

        def __exit__(self, *a):
            return self._fh.__exit__(*a)

    def spy_open(path, mode="r", *a, **k):
        fh = real_open(path, mode, *a, **k)
        try:
            mine = os.path.abspath(path) == os.path.abspath(jrnl)
        except Exception:                                     # noqa: BLE001
            mine = False
        if not mine:
            return fh
        modes.append(mode)
        return Counting(fh)

    builtins.open = spy_open
    os.fsync = lambda fd: (synced.append(fd), real_fsync(fd))[1]
    try:
        w = datwrite.Writer(dat, jrnl)
        try:
            with quiet():
                w.replace(ROW_SHRINK, payload)
            jfd = w.journal.fh.fileno()
            records = len(w.journal.entries)
        finally:
            w.close()
    finally:
        builtins.open = real_open
        os.fsync = real_fsync

    final = os.path.getsize(jrnl)
    check(records == 5,
          f"a replace of row {ROW_SHRINK} journals 5 records -- payload, size, "
          f"compression, entry crc, MFT self-crc",
          f"{records} record(s)")

    print("\n12a. one truncating open, and no rewrite of what is already there")
    truncating = [m for m in modes if "w" in m or "x" in m]
    check(len(truncating) == 1,
          f"the journal path is opened with a truncating mode EXACTLY ONCE "
          f"across {records} records (it was once per record: {records})",
          f"modes: {modes}")
    check(wrote[0] < final * 1.5,
          f"and cumulative bytes written, {wrote[0]}, is under 1.5x the "
          f"{final} B final file -- MEASURED {wrote[0] / final:.2f}x, against "
          f"4.66x on this same fixture before the change",
          f"{wrote[0]} B written for a {final} B journal")

    print("\n12b. every record is fsynced, and that is what the ordering claims")
    journal_syncs = sum(1 for fd in synced if fd == jfd)
    # HONEST LIMIT, stated because this file has a rule about checks that cannot
    # fail: this proves the CALL was made, not that bytes reached the platter.
    # Same class of claim as declaration_fault proving agreement with our own
    # decoder rather than correctness against the client's.
    check(journal_syncs >= records,
          f"os.fsync was called on the journal's own descriptor at least once "
          f"per record ({journal_syncs} for {records}) -- put() fsyncs the "
          f"archive, and the record that must PRECEDE it now does too",
          f"{journal_syncs} sync(s) on fd {jfd}, "
          f"{len(synced)} across all descriptors")

    real_flush = datwrite.Journal.flush
    try:
        def no_fsync(self):
            if self.fh is not None:
                self.fh.flush()
        datwrite.Journal.flush = no_fsync
        synced2, jrnl2 = [], os.path.join(tmp, "jr2.journal.json")
        os.fsync = lambda fd: (synced2.append(fd), real_fsync(fd))[1]
        dat2, _ = fresh(tmp, "jr2.dat")
        w = datwrite.Writer(dat2, jrnl2)
        try:
            with quiet():
                w.replace(ROW_SHRINK, payload)
            jfd2 = w.journal.fh.fileno()
        finally:
            w.close()
    finally:
        os.fsync = real_fsync
        datwrite.Journal.flush = real_flush
    check(sum(1 for fd in synced2 if fd == jfd2) == 0,
          "SABOTAGE: with the fsync taken out of Journal.flush the count for "
          "the journal's descriptor falls to zero -- so 12b is measuring the "
          "call and not the file object's own buffering")

    print("\n12c. a TORN journal costs the last record, not all of them")
    dat3, _ = fresh(tmp, "torn.dat")
    j3 = os.path.join(tmp, "torn.journal.json")
    with quiet():
        run_cli("--dat", dat3, "--journal", j3,
                "--replace", str(ROW_SHRINK), "--data",
                spill(tmp, "torn.bin", payload))
    written_state = blob(dat3)
    full = json.load(open(j3))
    check(len(full["edits"]) == 5,
          f"the intact journal reads with a plain json.load and holds "
          f"{len(full['edits'])} edits -- the format did NOT move, and 59 "
          f"journals under vault/ plus test_datalloc.py's prefix replay depend "
          f"on that")
    lines = journal_lines(j3)
    check(len(lines) == 5 + 3,
          f"and it is one record per LINE: {len(lines)} pieces for 5 records -- "
          f"a header line, five record lines, the closer, and the empty piece "
          f"after the final newline",
          f"lines: {[len(x) for x in lines]}")

    raw = blob(j3)
    # Cut through the MIDDLE of the LAST RECORD line, which is what an
    # interrupted append actually leaves behind: every earlier record is already
    # complete and already fsynced. lines[-1] is the empty piece past the final
    # newline and lines[-2] is the closer, so the last record is lines[-3].
    starts, pos = [], 0
    for piece in lines:
        starts.append(pos)
        pos += len(piece) + 1
    cut = starts[-3] + len(lines[-3]) // 2
    torn = os.path.join(tmp, "torn-mid.journal.json")
    with open(torn, "wb") as fh:
        fh.write(raw[:cut])
    doc, dropped = datwrite.read_journal(torn)
    check(len(doc["edits"]) == 4 and dropped > 0,
          f"read_journal recovers the 4 complete records and reports "
          f"{dropped} dropped byte(s) rather than swallowing them",
          f"{len(doc['edits'])} recovered, {dropped} B dropped")
    expect = bytearray(written_state)
    for ed in reversed(doc["edits"]):
        expect[ed["offset"]:ed["offset"] + ed["length"]] = \
            binascii.unhexlify(ed["before"])
    code, out = run_cli("--revert", torn)
    check(code != 0 and "INCOMPLETE JOURNAL" in out,
          f"--revert on it exits NON-ZERO with a named diagnosis -- it raised "
          f"JSONDecodeError out of revert() before the change",
          f"exit {code}")
    check(str(dropped) in out,
          "and the message names how many bytes it dropped; silence there is "
          "the same defect as the missing count")
    check(blob(dat3) == bytes(expect) and blob(dat3) != written_state,
          "and every COMPLETE record replayed, so the loss is one record and "
          "not the whole file")

    # 50%, the recon's own cut. It lands inside the FIRST record here, because
    # the payload record is 1024 B of archive against four 4-byte ones, so
    # nothing is recoverable -- and that must still be a named refusal.
    dat4, _ = fresh(tmp, "torn2.dat")
    j4 = os.path.join(tmp, "torn2.journal.json")
    with quiet():
        run_cli("--dat", dat4, "--journal", j4,
                "--replace", str(ROW_SHRINK), "--data",
                spill(tmp, "torn2.bin", payload))
    state4 = blob(dat4)
    half = os.path.join(tmp, "torn-half.journal.json")
    raw4 = blob(j4)
    with open(half, "wb") as fh:
        fh.write(raw4[:len(raw4) // 2])
    code, out = run_cli("--revert", half)
    check(code != 0 and "INCOMPLETE JOURNAL" in out and blob(dat4) == state4,
          "a journal truncated at 50% -- mid first record -- is a named "
          "refusal with nothing replayed and nothing written, not a traceback",
          f"exit {code}")
    junk = os.path.join(tmp, "junk.journal.json")
    with open(junk, "wb") as fh:
        fh.write(b"\x00\xFF" * 64)
    code, out = run_cli("--revert", junk)
    check(code != 0 and "REFUSED" in out and "header" in out,
          "and a file that is not a journal at all is refused by NAME, without "
          "opening any archive",
          f"exit {code}")

    print("\n12d. the OLD format still replays, byte for byte")
    # Synthesised, never borrowed: `json.dump({...}, indent=2)` IS what flush()
    # wrote until 2026-08-19, so re-serialising a real journal that way produces
    # exactly the artifact 59 files under vault/ are in. This file never opens
    # the vault.
    dat5, _ = fresh(tmp, "oldfmt.dat")
    j5 = os.path.join(tmp, "oldfmt.journal.json")
    original5 = blob(dat5)
    with quiet():
        run_cli("--dat", dat5, "--journal", j5,
                "--replace", str(ROW_SHRINK), "--data",
                spill(tmp, "oldfmt.bin", payload))
    old = os.path.join(tmp, "synth-old.journal.json")
    doc5 = json.load(open(j5))
    with open(old, "w") as fh:
        json.dump(doc5, fh, indent=2)
    check(blob(old) != blob(j5) and len(journal_lines(old)) > 7,
          f"the synthesised old-format journal is a DIFFERENT artifact -- one "
          f"pretty-printed document over {len(journal_lines(old))} lines, not "
          f"one record per line",
          f"{len(blob(old))} B vs {len(blob(j5))} B")
    code, out = run_cli("--revert", old)
    check(code == 0 and blob(dat5) == original5,
          "replaying it puts the archive back BYTE FOR BYTE",
          f"exit {code}, "
          f"{'identical' if blob(dat5) == original5 else 'DIFFERS'}")

    # SABOTAGE: drop the intact-document branch. read_journal's FIRST json.loads
    # is that branch, so making it raise is exactly "the old-format path was
    # removed" -- and the pretty-printed journal has no line that stands alone.
    def drop_intact_branch():
        state = {"n": 0}
        real_loads = json.loads

        def once(s, *a, **k):
            state["n"] += 1
            if state["n"] == 1:
                raise ValueError("sabotage: the intact-document branch is gone")
            return real_loads(s, *a, **k)
        return real_loads, once

    real_loads, once = drop_intact_branch()
    try:
        datjournal.json.loads = once
        code, out = run_cli("--revert", old)
    finally:
        datjournal.json.loads = real_loads
    check(code != 0 and "REFUSED" in out,
          "SABOTAGE: with that branch removed the old-format journal is "
          "unreadable -- so 12d is the check keeping 59 vault journals alive")

    # And the other half of what the line-per-record layout bought: the SAME
    # sabotage over a NEW-format journal is survivable, because every record
    # stands alone.
    dat6, _ = fresh(tmp, "newfmt.dat")
    j6 = os.path.join(tmp, "newfmt.journal.json")
    original6 = blob(dat6)
    with quiet():
        run_cli("--dat", dat6, "--journal", j6,
                "--replace", str(ROW_SHRINK), "--data",
                spill(tmp, "newfmt.bin", payload))
    real_loads, once = drop_intact_branch()
    try:
        datjournal.json.loads = once
        code, out = run_cli("--revert", j6)
    finally:
        datjournal.json.loads = real_loads
    check(code == 0 and blob(dat6) == original6,
          "CONTROL: the same sabotage over a NEW-format journal reverts byte "
          "for byte from the line parser alone -- which is the whole of what "
          "one-record-per-line buys when a write is torn")


def section_grow_typed(tmp):
    """13. THE GROW GATE'S REFUSAL HAS A TYPE, and the four conditions a name.

    WHAT THIS IS FOR, and it is a defect in a CONSUMER rather than in this file.
    `deploy.py` drives `--replace --grow-to` as a subprocess and has to tell two
    non-zero exits apart, because only one of them may be followed by a
    relocation: the gate refusing (another row took the blocks this one freed --
    a fact about the archive that a silent datmove would erase) and every
    ordinary refusal (a bad declaration, a missing file, a refused archive).
    Until 2026-08-20 it told them apart by looking for four fixed fragments of
    the sentences below -- "is CLAIMED by", "PAST THE END", "LIVE MASTER FILE
    TABLE", "datplan WITHHOLDS". That join fails safe if this module rewords
    anything, which is the right direction and is still a join on prose.

    So the refusal now carries its own name: `GrowGateRefused`, a `SystemExit`
    subclass with a `condition`, and one machine-readable line printed beside
    (never inside) the message. THE LOGIC DID NOT MOVE -- this section's job is
    to prove that twice over: every sentence is still the sentence, and an
    ordinary refusal still carries no token at all. That last one is the check
    that matters, because a token on everything would be worse than no token.
    """
    print("\n13. the grow gate refuses BY NAME, not by wording")
    off = ROWS[ROW_SHRINK][0]
    pristine_res = reservation(ROWS[ROW_SHRINK][1])           # 1024
    small = spill(tmp, "t-small.bin", pattern(9, 100))
    big = spill(tmp, "t-big.bin", pattern(77, 1000))
    mid = spill(tmp, "t-mid.bin", pattern(31, 600))

    check(issubclass(datwrite.GrowGateRefused, SystemExit),
          "GrowGateRefused is a SystemExit -- every caller in the tree and the "
          "vault catches that or lets it exit, so the type is ADDED and nothing "
          "existing has to learn about it",
          f"{datwrite.GrowGateRefused.__mro__[1].__name__}")
    check(datwrite.GROW_GATE_CONDITIONS
          == ("claimants", "eof", "live-mft", "withheld-run"),
          "and the four conditions are named in the gate's own order",
          f"{datwrite.GROW_GATE_CONDITIONS}")

    def shrunk(name):
        """A fresh archive whose ROW_SHRINK has been taken to 100 B. -> path."""
        path, _ = fresh(tmp, name)
        with quiet():
            run_cli("--dat", path, "--journal",
                    os.path.join(tmp, f"{name}.j0.json"),
                    "--replace", str(ROW_SHRINK), "--data", small)
        return path

    def grow(path, row, data, to, stub_claimants=False):
        """One in-process grow. -> the exception it raised, or None."""
        real = datwrite.claimants
        if stub_claimants:
            datwrite.claimants = lambda ar, lo, hi, exclude: []
        w = datwrite.Writer(path, os.path.join(tmp, "t-unused.json"))
        try:
            with quiet():
                w.replace(row, open(data, "rb").read(), grow_to=to)
            return None
        except SystemExit as exc:
            return exc
        finally:
            w.close()
            datwrite.claimants = real

    # (a) CONDITION 1, claimants. The same shape 11e drives through the CLI,
    # asked in-process so the TYPE is what is read rather than the output.
    p = shrunk("typed-claimed.dat")
    body = row_bytes(p, ROW_SMALL, ROWS[ROW_SMALL][1])
    with open(p, "r+b") as fh:
        fh.seek(off + 512)
        fh.write(body)
    mft_field(p, ROW_SMALL, 0x00, "<Q", off + 512)
    exc = grow(p, ROW_SHRINK, big, 1000)
    check(isinstance(exc, datwrite.GrowGateRefused)
          and exc.condition == "claimants",
          "a grow into blocks another row now owns raises GrowGateRefused with "
          "condition 'claimants' -- the one refusal a caller MAY follow with a "
          "relocation, and the only one that is a fact about the archive",
          f"{type(exc).__name__}, condition "
          f"{getattr(exc, 'condition', None)!r}")
    check(exc is not None and "is CLAIMED by" in str(exc)
          and "datmove" in str(exc),
          "and its sentence is unchanged, datmove remedy and all -- the type is "
          "the change and the message is not",
          str(exc).splitlines()[0][:90] if exc else "nothing raised")
    check(exc is not None and datwrite.GROW_GATE_TOKEN not in str(exc),
          "and the machine-readable token is NOT inside the message: the "
          "refusal text is what readers and greps already know, so the token "
          "goes beside it")

    # (b) CONDITION 2, EOF. Row 7 moved to the last byte of the file, exactly
    # 11f's setup -- reached without any stub, since claimants cannot see EOF.
    p, _ = fresh(tmp, "typed-eof.dat")
    mft_field(p, ROW_SMALL, 0x00, "<Q", FILE_SIZE)
    exc = grow(p, ROW_SMALL, mid, 600)
    check(isinstance(exc, datwrite.GrowGateRefused) and exc.condition == "eof"
          and "PAST THE END" in str(exc),
          "a grow past EOF raises condition 'eof', message unchanged -- and it "
          "is reached with claimants intact, which is the point of it being a "
          "separate condition at all",
          f"{type(exc).__name__}, {getattr(exc, 'condition', None)!r}")

    # (c) CONDITION 3, the live MFT. Needs 11g's stub: on this fixture row 3
    # happens to describe the table, so claimants refuses first.
    p, _ = fresh(tmp, "typed-mft.dat")
    exc = grow(p, ROW_SMALL, mid, 600, stub_claimants=True)
    check(isinstance(exc, datwrite.GrowGateRefused)
          and exc.condition == "live-mft"
          and "LIVE MASTER FILE TABLE" in str(exc),
          "with claimants stubbed out the MFT check still names itself: "
          "condition 'live-mft', message unchanged",
          f"{type(exc).__name__}, {getattr(exc, 'condition', None)!r}")

    # (d) CONDITION 4, a withheld container run. 11h's four bytes of setup.
    p = shrunk("typed-withheld.dat")
    with open(p, "r+b") as fh:
        fh.seek(off + 512)
        fh.write(MFT_MAGIC + b"\x00" * 8 + struct.pack("<I", ENTRY_COUNT))
    exc = grow(p, ROW_SHRINK, big, 1000)
    check(isinstance(exc, datwrite.GrowGateRefused)
          and exc.condition == "withheld-run"
          and "datplan WITHHOLDS" in str(exc),
          "and a grow into a run datplan withholds raises condition "
          "'withheld-run', message unchanged",
          f"{type(exc).__name__}, {getattr(exc, 'condition', None)!r}")

    # (e) THE NEGATIVE CONTROL, AND IT IS THE CHECK. Two refusals the gate did
    # not give: the stated-entitlement ceiling (which is `replace`'s own rule,
    # decided before the gate runs) and a plain SystemExit out of the CLI. A
    # consumer that treated either as a gate refusal would relocate around a
    # caller error -- which is exactly what "these bytes are not what you
    # declared, so datmove them instead" looks like.
    p = shrunk("typed-ceiling.dat")
    exc = grow(p, ROW_SHRINK, big, 512)
    check(exc is not None and not isinstance(exc, datwrite.GrowGateRefused)
          and "entitled" in str(exc),
          "a payload past the entitlement the CALLER stated is an ordinary "
          "SystemExit, NOT a GrowGateRefused -- it is replace()'s own ceiling "
          "and the gate never ran",
          f"{type(exc).__name__}")

    # (f) AND THE CLI PRINTS THE TOKEN, which is the half that crosses a
    # subprocess boundary -- `deploy.py` reads bytes, not exceptions.
    p = shrunk("typed-cli.dat")
    body = row_bytes(p, ROW_SMALL, ROWS[ROW_SMALL][1])
    with open(p, "r+b") as fh:
        fh.seek(off + 512)
        fh.write(body)
    mft_field(p, ROW_SMALL, 0x00, "<Q", off + 512)
    before = blob(p)
    code, out = run_cli("--dat", p, "--journal", os.path.join(tmp, "t1.json"),
                        "--replace", str(ROW_SHRINK), "--data", big,
                        "--grow-to", "1000")
    check(code != 0 and blob(p) == before
          and f"{datwrite.GROW_GATE_TOKEN} condition=claimants" in out,
          "the command line prints one machine-readable line naming the "
          "condition, and still refuses with nothing written -- an exception "
          "class does not cross a subprocess boundary and bytes do",
          next((ln.strip() for ln in out.splitlines()
                if datwrite.GROW_GATE_TOKEN in ln), "said nothing"))
    check("is CLAIMED by" in out,
          "and the human sentence is still there beside it, unchanged -- the "
          "token is an ADDITION, so a reader who never learns about it loses "
          "nothing")
    p = shrunk("typed-cli-ceiling.dat")
    code, out = run_cli("--dat", p, "--journal", os.path.join(tmp, "t2.json"),
                        "--replace", str(ROW_SHRINK), "--data", big,
                        "--grow-to", "512")
    check(code != 0 and datwrite.GROW_GATE_TOKEN not in out,
          "CONTROL: the ordinary refusal prints NO token, so a consumer joining "
          "on it cannot mistake a caller error for a claimant conflict -- a "
          "token on every failure would be worse than no token",
          f"exit {code}")
    code, out = run_cli("--dat", p, "--journal", os.path.join(tmp, "t3.json"),
                        "--replace", str(ROW_SHRINK))
    check(code != 0 and datwrite.GROW_GATE_TOKEN not in out,
          "and neither does --replace with no --data, which is the other shape "
          "of non-zero exit a subprocess caller sees", f"exit {code}")


def main():
    tmp = tempfile.mkdtemp(prefix="rurik-datwrite-")
    print(f"synthetic archive: {FILE_SIZE} B, {ENTRY_COUNT} rows, in {tmp}")
    try:
        sections(tmp)
        section_restore(tmp)
        section_relink(tmp)
        section_header_refusal(tmp)
        section_compressed(tmp)
        section_c6_guard(tmp)
        section_growback(tmp)
        section_journal(tmp)
        section_grow_typed(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
