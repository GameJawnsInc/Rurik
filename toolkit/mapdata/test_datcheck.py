"""Check the pre-flight and the detector by breaking every rule they enforce.

`datcheck.py` is a gate, and a gate nobody has watched fail is a wish. Every
check it makes is about a copy of a 4 GB archive that we are about to hand to a
client -- so the only honest way to know the gate works is to build an archive
that violates one rule at a time and require the matching item, and only the
matching item, to go red.

WHAT IT RUNS AGAINST. A 5.5 KB archive this file builds in a temp directory. It
never opens `vault/dat_study/Gw.dat`, never reads `C:\\gw`, never opens anything
for writing except its own fixture, and needs no vault -- so the floor below is
a real floor and not a corpus-shaped hope.

The fixture is laid out with real reserved rows: 0 descriptor, 1 file header, 2
file-id table, 3 the MFT, 4..15 all-zero spares, and FIVE real rows at index
>= 16 including a head/partner pair (`alloc.flags 3 / alloc.stream 1` linked
through `nextStream` to a `flags 1 / stream 0` row). The pair is not decoration:
a non-first stream is the one row shape that legitimately has NO file-id record,
and without one the "USED clear at index >= 16" sabotage could not be isolated
from the directory invariant.

EACH SABOTAGE IS CHECKED TWICE -- the item it targets must fail AND every other
item must still pass. A gate that goes red at everything is as useless as one
that goes red at nothing, and the isolation half is what catches a check whose
predicate is accidentally broad. The fixture's own layout was relaid twice to
make that possible: the past-EOF sabotage needs free space at the END of the
file or it also trips the overlap rule, and the misalignment sabotage needs a
row with a gap after it or it trips the same.

Section 4 is a different thing sharing this file: `archive.py`'s new `RURIK_DAT`
override, which is a lever on the SERVER path. It exists because a running client
holds an exclusive lock on the archive it launched from, so the two sides can
never share one file; C2's server copy is only reachable through it. It is
checked by reloading the module with the variable set and opening `Archive()`
with no path at all -- reading the constant would pass against a module that
never uses it.

    python toolkit/mapdata/test_datcheck.py
"""

import binascii
import importlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import archive as archive_mod  # noqa: E402
import datcheck  # noqa: E402
import checks  # noqa: E402

# FLOOR: measured from a green run on 2026-08-11. Every check below runs
# unconditionally -- the fixture is built by this file and there is no corpus to
# be absent -- so a count under this means a section stopped executing, which on
# a gate is indistinguishable from the gate being removed.
#
# RAISED 69 -> 75 on 2026-08-13 with section 0b, which pins `row_identity` --
# the file id and role every row named by `--diff` now carries. It is six more
# checks on the SAME fixture (no vault, no client), so the floor moves by
# exactly six and the bare-machine property is unchanged.
#
# RAISED 75 -> 83 on 2026-08-14 with section 3b, and that one is the correction:
# 0b pinned the LOGIC and nothing pinned the OUTPUT. `format_diff` -- the only
# thing an operator ever reads -- was referenced by no test in this tree, so a
# sabotage reverting it and the `--preflight` banner to their exact pre-fix bare
# form left this file at 75/75 and `test_archive.py` at 29/29, both exit 0. The
# whole human-facing half of the fix could be deleted green. Eight more checks
# in 3b plus one in §7 -- the `--preflight` banner is a separate `print` in
# `_main` that no function-level check can see, and the revert sabotage's six
# reds did not include it until §7 ran the real CLI. Same fixture, still no
# vault and no client. MEASURED, not counted by hand: a green run prints 84.
LEDGER = checks.Ledger("dat pre-flight and detector", floor=84)
check = checks.adopt(LEDGER)

FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"
ENTRY_SIZE = 24
BLOCK = 512

FILE_SIZE = 0x1600
MFT_OFF = 0x1200
ENTRY_COUNT = 21                       # rows 0..20; row 0 is the descriptor
MFT_SIZE = ENTRY_COUNT * ENTRY_SIZE    # 504, one block
SLACK = 0xCC

ROW_HEADER, ROW_IDTABLE, ROW_SELF = 1, 2, 3
ROW_A, ROW_B, ROW_HEAD, ROW_D, ROW_PARTNER = 16, 17, 18, 19, 20

# row -> (offset, size, extraBytes, flags16, nextStream)
# flags16 is `alloc.flags | alloc.stream << 8`, the two bytes archive.py reads as
# one u16. Reservations, in order: 0x0000-0x0200 header, 0x0200-0x0400 id table,
# 0x0400-0x0600 A, 0x0600-0x0A00 B, 0x0A00-0x0C00 head, 0x0C00-0x0E00 D,
# 0x0E00-0x1000 partner, 0x1000-0x1200 FREE, 0x1200-0x1400 MFT,
# 0x1400-0x1600 FREE. The two holes are what let a misalignment and a past-EOF
# extent be sabotaged one at a time.
ROWS = {
    ROW_HEADER:  (0x0000, 32, 0, 0x0003, 0),
    ROW_IDTABLE: (0x0200, 40, 0, 0x0003, 0),
    ROW_SELF:    (MFT_OFF, MFT_SIZE, 0, 0x0003, 0),
    ROW_A:       (0x0400, 300, 0, 0x0003, 0),
    ROW_B:       (0x0600, 900, 8, 0x0003, 0),
    ROW_HEAD:    (0x0A00, 500, 8, 0x0103, ROW_PARTNER),
    ROW_D:       (0x0C00, 100, 0, 0x0003, 0),
    ROW_PARTNER: (0x0E00, 200, 8, 0x0001, 0),
}
PAYLOAD_ROWS = (ROW_IDTABLE, ROW_A, ROW_B, ROW_HEAD, ROW_D, ROW_PARTNER)

# (file_id, row). Row 20 is deliberately absent: it is a non-first stream and is
# reached through nextStream, never through the directory. The (0, 0) record is
# a RELEASED slot -- three of them exist in the real archive and the invariant
# must count them rather than call them dangling.
ID_RECORDS = [(0x1000, ROW_A), (0x1001, ROW_B), (0x1002, ROW_HEAD),
              (0x1003, ROW_D), (0, 0)]

ALL_ITEMS = ["0x1C bit 0 clear", "0x1C bit 1 clear", "header CRC over 0x00..0x0C",
             "every extent 512-aligned", "every extent inside EOF",
             "no overlapping reservations",
             "every USED|FIRST row >= 16 is named",
             "every file-id record names a USED row",
             "no row below index 16 touched",
             "no USED-clear row that something points at"]


def pattern(seed, n):
    return bytes(1 + ((i * 37 + seed * 101) % 255) for i in range(n))


def role_of(ident, row):
    """`ident[row]["role"]`, or a string saying the row is absent.

    NEVER a bare `ident[row]`. A `row_identity` that has LOST a row -- which is
    exactly what a reader changing convention produces -- raises KeyError here
    and kills the run before `LEDGER.verdict()`: no banner, no floor, no ledger,
    the one failure `checks.py` cannot see. MEASURED on the
    consistent-renumber sabotage: four [FAIL] lines had already printed and the
    run then died at the fifth check with a traceback. A broken module has to
    score as WRONG, not as absent.
    """
    rec = ident.get(row)
    return "NO SUCH ROW %d in the identity map" % row if rec is None         else rec["role"]


def ids_of(ident, row):
    """`ident[row]["file_ids"]`, or None if the row is absent. See `role_of`."""
    rec = ident.get(row)
    return None if rec is None else rec["file_ids"]


def build_archive(path):
    """A small, complete, self-consistent archive. Returns nothing it needs back."""
    buf = bytearray(bytes([SLACK]) * FILE_SIZE)

    for row in PAYLOAD_ROWS:
        off, size, _extra, _flags, _nxt = ROWS[row]
        if row == ROW_IDTABLE:
            data = b"".join(struct.pack("<II", i, r) for i, r in ID_RECORDS)
            assert len(data) == size, (len(data), size)
        else:
            data = pattern(row, size)
        buf[off:off + size] = data

    head = bytearray(32)
    head[0:4] = FILE_MAGIC
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<Q", head, 0x10, MFT_OFF)
    struct.pack_into("<I", head, 0x18, MFT_SIZE)
    struct.pack_into("<I", head, 0x1C, 0)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head

    mft = bytearray(MFT_SIZE)
    mft[0:4] = MFT_MAGIC
    struct.pack_into("<I", mft, 0x04, 7)              # the flush counter
    struct.pack_into("<I", mft, 0x0C, ENTRY_COUNT)
    for row, (off, size, extra, flags, nxt) in ROWS.items():
        crc = 0 if row in (ROW_HEADER, ROW_SELF) else \
            binascii.crc32(bytes(buf[off:off + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         off, size, extra, flags, nxt, crc)
    buf[MFT_OFF:MFT_OFF + MFT_SIZE] = mft

    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return path


# ---------------------------------------------------------------- surgery --

def poke(path, offset, data):
    """Change bytes in the fixture. Only ever the fixture."""
    with open(path, "r+b") as fh:
        fh.seek(offset)
        fh.write(data)


def poke_row(path, row, **fields):
    """Rewrite one MFT row's fields in place."""
    with open(path, "r+b") as fh:
        fh.seek(MFT_OFF + row * ENTRY_SIZE)
        cur = fh.read(ENTRY_SIZE)
        off, size, extra, flags, nxt, crc = struct.unpack("<QIHHII", cur)
        vals = {"offset": off, "size": size, "extra": extra, "flags": flags,
                "nxt": nxt, "crc": crc}
        vals.update(fields)
        fh.seek(MFT_OFF + row * ENTRY_SIZE)
        fh.write(struct.pack("<QIHHII", vals["offset"], vals["size"],
                             vals["extra"], vals["flags"], vals["nxt"],
                             vals["crc"]))


def verdicts(path):
    """name -> ok, for one pre-flight run."""
    got, _facts = datcheck.preflight(path)
    return {c.name: c.ok for c in got}


def expect_only(path, label, failing):
    """The named item fails and every other item still passes."""
    v = verdicts(path)
    missing = [n for n in ALL_ITEMS if n not in v]
    check(not missing, f"{label}: pre-flight still reports every item",
          f"missing {missing}" if missing else f"{len(v)} items")
    check(v.get(failing) is False, f"{label}: '{failing}' goes RED")
    others = [n for n, ok in v.items() if n != failing and not ok]
    check(not others, f"{label}: nothing else goes red",
          f"also red: {others}" if others else "isolated")


# ------------------------------------------------------------------ main --

def main():
    tmp = tempfile.mkdtemp(prefix="rurik-datcheck-")
    try:
        run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return LEDGER.verdict()


def fresh(tmp, name):
    return build_archive(os.path.join(tmp, name))


def run(tmp):
    print("\n0. the fixture is a healthy archive")
    good = fresh(tmp, "good.dat")
    got, facts = datcheck.preflight(good)
    for c in got:
        if not c.ok:
            print("   unexpected: " + c.line())
    check(len(got) == len(ALL_ITEMS), "the pre-flight makes every declared item",
          f"{len(got)} of {len(ALL_ITEMS)}")
    check(all(c.ok for c in got), "a clean fixture passes every item",
          f"{sum(1 for c in got if c.ok)}/{len(got)}")
    inv = facts["invariant"]
    check(inv["first_stream_rows"] == 4 and inv["rows_named"] == 4,
          "the directory invariant counts the four head rows",
          f"first_stream={inv['first_stream_rows']} named={inv['rows_named']}")
    check(inv["released_records"] == 1,
          "a (0, 0) record is counted as RELEASED, not dangling",
          f"released={inv['released_records']} dangling={len(inv['dangling_records'])}")
    # The partner is the row shape that proves the invariant is not simply
    # "every USED row is named": it is USED, it is >= 16, and it has no record.
    check(not inv["orphan_rows"],
          "a USED non-first stream needs no file-id record",
          f"orphans={inv['orphan_rows']}")

    print("\n0b. every row this tool names carries its own identity")
    # WHY THIS IS HERE AND NOT ONLY IN test_archive. `row_identity` exists
    # because two bare integers were the whole of the evidence in
    # `studies/crossbuild/FINDINGS.md` §4b.1: `--diff` said row 71496 changed
    # and `deploy.py` said "head 71496, partner 71497", and the pair was read as
    # the client having eaten an authored map. It had not -- 71496 is the
    # Bloated HEAD that `deploy` arms to zero on purpose, and the re-bloat is
    # the experiment working. `test_archive.py` §1c checks the labels against a
    # 4 GB archive; this checks the LOGIC on a 5.5 KB fixture whose head,
    # partner, spare and reserved rows are known by construction, so it runs on
    # a bare machine and can be wrong for exactly one reason.
    mft = datcheck.read_mft(good)
    records, _blob = datcheck.file_id_records(good, mft,
                                              datcheck.read_header(good))
    ident = datcheck.row_identity(mft, records)
    check(role_of(ident, ROW_HEAD) == "stream head"
          and ids_of(ident, ROW_HEAD) == [0x1002],
          "the head row is a stream head and carries its file id",
          f"{role_of(ident, ROW_HEAD)!r} {ids_of(ident, ROW_HEAD)}")
    # The partner is the whole point: it is USED, it has NO file-id record, and
    # `alloc.nextStream` is the only thing in the archive that names it. A
    # labeller reading the directory alone would call it anonymous, which is
    # precisely the row a reader most needs told apart from its head.
    check(role_of(ident, ROW_PARTNER) == f"stream partner of row {ROW_HEAD}"
          and not ids_of(ident, ROW_PARTNER),
          "the partner names the head that points at it, from nextStream alone",
          f"{role_of(ident, ROW_PARTNER)!r} {ids_of(ident, ROW_PARTNER)}")
    check(role_of(ident, 0) == "MFT descriptor"
          and role_of(ident, datcheck.MFT_SELF_ROW) == "the MFT itself"
          and role_of(ident, datcheck.FILE_ID_TABLE_ROW) == "file-id table"
          and role_of(ident, 7) == "reserved spare",
          "rows 0..15 get the client's own structural names",
          f"0={role_of(ident, 0)!r} 7={role_of(ident, 7)!r}")
    # A (0, 0) record is a RELEASED slot. Filing it under row 0 would put file
    # id 0 on the MFT descriptor and make the descriptor read as a file.
    check(ids_of(ident, 0) == [],
          "the released (0, 0) record does not name row 0",
          f"{ids_of(ident, 0)}")
    check(datcheck.label_row(ident, ROW_HEAD)
          == f"row {ROW_HEAD} [file id 0x1002; stream head]"
          and datcheck.label_row(None, ROW_HEAD) == f"row {ROW_HEAD}",
          "label_row prints the identity, and a BARE row when it has none",
          datcheck.label_row(ident, ROW_HEAD))
    # A spare and a row something still points at are the two USED-clear shapes,
    # and the pre-flight treats them differently -- one is the allocator working
    # (row 35301 in the owner's own install), one is corruption. The label must
    # separate them too, or a diff line contradicts the gate above it.
    spare = fresh(tmp, "ident_spare.dat")
    poke_row(spare, ROW_D, flags=0x0002)         # USED clear, nothing points here
    s_mft = datcheck.read_mft(spare)
    s_ident = datcheck.row_identity(
        s_mft, datcheck.file_id_records(spare, s_mft,
                                        datcheck.read_header(spare))[0])
    lost = fresh(tmp, "ident_lost.dat")
    poke_row(lost, ROW_PARTNER, flags=0x0000)    # USED clear, the head points here
    l_mft = datcheck.read_mft(lost)
    l_ident = datcheck.row_identity(
        l_mft, datcheck.file_id_records(lost, l_mft,
                                        datcheck.read_header(lost))[0])
    check(role_of(s_ident, ROW_D) == "free spare"
          and role_of(l_ident, ROW_PARTNER)
          == f"USED CLEAR but row {ROW_HEAD} points here",
          "a free spare and a referenced row that lost USED are labelled apart",
          f"{role_of(s_ident, ROW_D)!r} vs {role_of(l_ident, ROW_PARTNER)!r}")

    print("\n1. every pre-flight item goes red on its own")

    p = fresh(tmp, "mod0.dat")
    poke(p, 0x1C, struct.pack("<I", 1))
    expect_only(p, "0x1C bit 0 set", "0x1C bit 0 clear")

    p = fresh(tmp, "mod1.dat")
    poke(p, 0x1C, struct.pack("<I", 2))
    expect_only(p, "0x1C bit 1 set", "0x1C bit 1 clear")

    p = fresh(tmp, "hdrcrc.dat")
    poke(p, 0x0C, struct.pack("<I", 0xDEADBEEF))
    expect_only(p, "header CRC corrupted", "header CRC over 0x00..0x0C")

    p = fresh(tmp, "misalign.dat")
    poke_row(p, ROW_PARTNER, offset=0x0E04)
    expect_only(p, "one extent misaligned by 4", "every extent 512-aligned")

    p = fresh(tmp, "eof.dat")
    poke_row(p, ROW_D, offset=0x1400, size=0x300)
    expect_only(p, "one extent past EOF", "every extent inside EOF")

    p = fresh(tmp, "overlap.dat")
    poke_row(p, ROW_HEAD, offset=0x0800)
    expect_only(p, "two extents overlapping", "no overlapping reservations")

    p = fresh(tmp, "orphan.dat")
    # The record that named row 18 now names row 19 twice: row 18 keeps its
    # USED|FIRST flags and loses its directory record, which is exactly the row
    # the client's reconcile pass DELETES by name at the next open.
    poke(p, ROWS[ROW_IDTABLE][0] + 2 * 8, struct.pack("<II", 0x1002, ROW_D))
    expect_only(p, "a USED|FIRST row with no record",
                "every USED|FIRST row >= 16 is named")

    p = fresh(tmp, "dangling.dat")
    # The released (0, 0) slot becomes a record naming an all-zero reserved row.
    poke(p, ROWS[ROW_IDTABLE][0] + 4 * 8, struct.pack("<II", 0x1004, 7))
    expect_only(p, "a record naming a non-USED row",
                "every file-id record names a USED row")

    p = fresh(tmp, "lowrow.dat")
    # Four bytes in row 7's crc field, and nothing else. Its flags stay clear so
    # the row is not USED and the extent items cannot see it -- writing 24 bytes
    # of 0x11 sets FLAG_ENTRY_USED and trips the alignment and EOF items too,
    # which is a broader sabotage than the item being isolated.
    poke(p, MFT_OFF + 7 * ENTRY_SIZE + 0x14, struct.pack("<I", 0x11223344))
    expect_only(p, "a reserved row below 16 written",
                "no row below index 16 touched")

    # A PARTNER losing USED is corruption: nothing but `alloc.nextStream` reaches
    # it, so the file-id record item cannot see it and this is the only item that
    # can. It must still go red, alone.
    p = fresh(tmp, "unused.dat")
    poke_row(p, ROW_PARTNER, flags=0x0000)
    expect_only(p, "a referenced partner left USED-clear",
                "no USED-clear row that something points at")

    # THE CONTROL, and the reason this item was rewritten on 2026-08-13: a row that
    # NOTHING points at is a SPARE, and refusing it refused ArenaNet's own shipped
    # archive. The owner's install carries exactly one (row 35301, which `datplan`
    # already records the client CLAIMING when it wanted a slot) and pre-flight
    # answered REFUSE, 9 of 10, on a file the retail client opens every day. A gate
    # that reddens on the real target is not a gate, it is a tool nobody can run.
    #
    # It is the SAME ROW in the SAME state as the sabotage above -- USED clear, on
    # row 20 -- and the only difference is that the head no longer points at it. So
    # this pair isolates the reference and nothing else: if the item ever goes back
    # to reading the flag alone, exactly one of these two goes the wrong way.
    p = fresh(tmp, "spare.dat")
    poke_row(p, ROW_PARTNER, flags=0x0000)
    poke_row(p, ROW_HEAD, nxt=0)
    got, _facts = datcheck.preflight(p)
    bad = [c.name for c in got if not c.ok]
    check(not bad, "CONTROL: the same row, unreferenced, is a SPARE and not a fault",
          "red: %s" % (bad or "none -- as on the owner's own install"))
    item = [c for c in got
            if c.name == "no USED-clear row that something points at"][0]
    check("spare" in item.detail and str(ROW_PARTNER) in item.detail,
          "and the spare is REPORTED rather than dropped", item.detail[:78])

    print("\n2. the baseline check compares the reserved rows byte for byte")
    base = fresh(tmp, "base.dat")
    snap = datcheck.snapshot(base)
    label = "reserved rows 1, 4..15 identical to the baseline"

    # Row 1's nextStream: a field the structural item does not look at, on a row
    # nothing should ever touch. This is the gap the baseline exists to close.
    moved = fresh(tmp, "moved.dat")
    poke_row(moved, ROW_HEADER, nxt=0x1234)
    v = {c.name: c.ok for c in datcheck.preflight(moved, baseline=snap)[0]}
    check(label in v, "a baseline adds the exact reserved-rows item")
    check(v.get(label) is False,
          "a changed reserved row is caught by the baseline",
          "row 1's nextStream moved and the structural item cannot see it")
    check(v.get("no row below index 16 touched") is True,
          "and the structural item alone would have passed it",
          "which is why the baseline item exists")

    # ...and a container row moving must NOT redden it. `datwrite.py` rewrites
    # row 3's self-crc after every --replace, so an item that went red on that
    # would be red after every legitimate write and would stop being read.
    flushed = fresh(tmp, "flushed.dat")
    poke_row(flushed, ROW_SELF, crc=0x99999999)
    poke(flushed, MFT_OFF + 0x04, struct.pack("<I", 8))
    v = {c.name: c.ok for c in datcheck.preflight(flushed, baseline=snap)[0]}
    check(v.get(label) is True,
          "but rows 0/2/3 moving does not redden it -- they move on any write",
          "the containers are reported beside the verdict instead")

    print("\n3. the detector classifies what the checksums cannot see")
    before_path = fresh(tmp, "before.dat")
    before = datcheck.snapshot(before_path)

    same = datcheck.diff(before, path=before_path)
    check(same["unchanged"] and not same["changes"],
          "an untouched archive diffs to no change", f"{same['counts']}")

    p = fresh(tmp, "reloc.dat")
    poke_row(p, ROW_A, offset=0x1000, size=310, crc=0xAABBCCDD)
    d = datcheck.diff(before, path=p)
    kinds = {r["row"]: r["kind"] for r in d["changes"]}
    check(kinds.get(ROW_A) == datcheck.RELOCATED,
          "a new extent on a stable identity is a RELOCATION", f"{kinds}")
    check(not d["unchanged"] and d["counts"].get(datcheck.RELOCATED) == 1,
          "and it is the only change reported", f"{d['counts']}")

    p = fresh(tmp, "recycle.dat")
    poke_row(p, ROW_B, flags=0x0C01, offset=0x1000, crc=0x1)
    d = datcheck.diff(before, path=p)
    kinds = {r["row"]: r["kind"] for r in d["changes"]}
    check(kinds.get(ROW_B) == datcheck.RECYCLED,
          "a changed +0x0E/+0x0F is a RECYCLED row", f"{kinds}")

    p = fresh(tmp, "delete.dat")
    poke(p, MFT_OFF + ROW_D * ENTRY_SIZE, b"\x00" * ENTRY_SIZE)
    d = datcheck.diff(before, path=p)
    kinds = {r["row"]: r["kind"] for r in d["changes"]}
    check(kinds.get(ROW_D) == datcheck.DELETED,
          "an all-zero row is a DELETE", f"{kinds}")

    p = fresh(tmp, "relink.dat")
    poke_row(p, ROW_A, nxt=ROW_PARTNER)
    d = datcheck.diff(before, path=p)
    kinds = {r["row"]: r["kind"] for r in d["changes"]}
    check(kinds.get(ROW_A) == datcheck.RELINKED,
          "a lone +0x10 change is a sibling RELINK", f"{kinds}")

    p = fresh(tmp, "weird.dat")
    poke_row(p, ROW_A, offset=0x1000, nxt=ROW_PARTNER)
    d = datcheck.diff(before, path=p)
    kinds = {r["row"]: r["kind"] for r in d["changes"]}
    check(kinds.get(ROW_A) == datcheck.UNCLASSIFIED,
          "a shape the table does not name is reported, not dropped", f"{kinds}")

    p = fresh(tmp, "counter.dat")
    poke(p, MFT_OFF + 0x04, struct.pack("<I", 8))
    d = datcheck.diff(before, path=p)
    check("descriptor_counter" in d["tier0"] and not d["changes"],
          "TIER 0: the descriptor counter alone is a change signal",
          f"{d['tier0']}")

    p = fresh(tmp, "dir.dat")
    poke(p, ROWS[ROW_IDTABLE][0], struct.pack("<II", 0x9999, ROW_A))
    d = datcheck.diff(before, path=p)
    check("file_id_sha256" in d["tier2"],
          "TIER 2: a rewritten directory is caught by its digest",
          f"{sorted(d['tier2'])}")
    check(not d["changes"] and not d["tier0"],
          "and it is invisible to TIER 0 and TIER 1", f"{d['counts']}")

    # Rows 0, 2 and 3 change on every flush. They must be separated out rather
    # than counted, or every post-flight would report three findings it cannot
    # act on.
    p = fresh(tmp, "flush.dat")
    poke_row(p, ROW_SELF, crc=0x55555555)
    d = datcheck.diff(before, path=p)
    check(not d["changes"] and [r["row"] for r in d["corroboration"]] == [ROW_SELF],
          "rows 0/2/3 are corroboration, not findings",
          f"changes={d['counts']} corroboration={[r['row'] for r in d['corroboration']]}")
    check(not d["unchanged"],
          "but a corroboration-only diff is still not 'unchanged'")

    print("\n3b. the OUTPUT a human reads, which nothing was checking")
    # THE HALF THAT PREVENTS THE MISTAKE IS THE HALF THAT GETS PRINTED, and it
    # had zero checks on it. `row_identity` was pinned in §0b, `label_row` too,
    # and `format_diff` -- which is the only thing an operator ever sees -- was
    # referenced by no test in the tree. MEASURED: a sabotage that reverted
    # `format_diff` and the `--preflight` banner to the exact pre-fix bare
    # output (no convention line, no NOT IDENTIFIED banner, `row %-7d`, a bare
    # `[0, 2, 3]` corroboration list) left this file at 75/75 and
    # `test_archive.py` at 29/29, both exit 0. A straight revert of the fix was
    # green in both directions, which means the fix was documentation.
    p = fresh(tmp, "fmt.dat")
    poke_row(p, ROW_HEAD, offset=0x1600, size=6012, crc=0xAABBCCDD)
    poke_row(p, ROW_SELF, crc=0x55555555)          # a corroboration row too
    text = datcheck.format_diff(datcheck.diff(before, path=p))
    check(datcheck.ROW_CONVENTION in text,
          "--diff names the row convention above its numbers",
          text.splitlines()[1][:72] + "...")
    # The changed row must arrive WEARING its identity. `ROW_HEAD` is the
    # fixture's map head and 0x1002 is its file id -- the two tokens `deploy.py`
    # prints on its own first line, which is what makes the two outputs
    # matchable at all.
    check(f"row {ROW_HEAD} [file id 0x1002; stream head]" in text,
          "and the changed row carries its file id and role, not a bare number",
          [ln.strip() for ln in text.splitlines()
           if str(ROW_HEAD) in ln][:1])
    # ...and NO row line anywhere in the output may be bare. Asserted over every
    # `row N` line rather than over the one row this fixture changed, because
    # the pre-fix formatter printed `   row 18      relocated` -- which contains
    # the substring `row 18` and would satisfy a check written the obvious way.
    # A label is a claim about identity; a padded integer is the thing that cost
    # the afternoon.
    row_lines = [ln for ln in text.splitlines()
                 if re.match(r"^\s+row \d+", ln)]
    check(len(row_lines) >= 2 and all("[" in ln for ln in row_lines),
          f"and EVERY row line in the output is labelled ({len(row_lines)} "
          f"lines, changed and corroboration alike) -- none is the bare padded "
          f"integer the pre-fix formatter printed",
          [ln.strip() for ln in row_lines if "[" not in ln][:2])
    check(f"row {datcheck.MFT_SELF_ROW} [" in text
          and "[0, 2, 3]" not in text and "[3]" not in text,
          "and the corroboration rows are labelled too, not printed as a list "
          "of integers")
    check("NOT IDENTIFIED" not in text,
          "a diff taken against a live archive does NOT wear the banner")

    # THE TWO-SNAPSHOT CASE, which is the one that has no archive behind it.
    two = datcheck.diff(before, after=datcheck.snapshot(p))
    two_text = datcheck.format_diff(two)
    check(not two["identified"] and "NOT IDENTIFIED" in two_text
          and f"row {ROW_HEAD} [" not in two_text,
          "two snapshots compared: NOT IDENTIFIED, and no row invents an "
          "identity it does not have", f"identified={two['identified']}")

    # THE TRAP THE FIX INTRODUCED. `diff(before, path=X, after=<snapshot of Y>)`
    # took its ROWS from Y and its IDENTITY from X and reported identified=True.
    # On a measured pair of vault archives 308 of 343 labels named a file the
    # after-image does not hold -- the exact "a label that names the wrong file
    # reads as identification" failure this whole change exists to prevent. No
    # shipped caller reaches it, which is why it survived review.
    #
    # The guard is the MFT ITSELF, byte for byte, so the POSITIVE CONTROL is not
    # optional: `other` is a DIFFERENT archive, and `p` is the SAME one, and the
    # gate has to tell them apart from the bytes rather than from the path.
    other = fresh(tmp, "fmt-other.dat")
    poke_row(other, ROW_A, offset=0x1000, size=310, crc=0x11223344)
    crossed = datcheck.diff(before, path=p, after=datcheck.snapshot(other))
    check(not crossed["identified"] and crossed["identity_note"]
          and "NOT IDENTIFIED" in datcheck.format_diff(crossed)
          and not any("file id" in r["label"] for r in crossed["changes"]),
          "an `after` from a DIFFERENT archive than `path` is refused a label, "
          "and the banner says which archive disagreed",
          (crossed["identity_note"] or "")[:60] + "...")
    same_again = datcheck.diff(before, path=p, after=datcheck.snapshot(p))
    check(same_again["identified"] and same_again["identity_note"] is None
          and any("file id 0x1002" in r["label"]
                  for r in same_again["changes"]),
          "and the SAME archive passed both ways still labels -- a gate that "
          "refused every explicit `after` would protect nothing")

    print("\n4. the snapshot is a real record, and it refuses a stale one")
    snap = datcheck.snapshot(before_path)
    mft = datcheck._snapshot_mft(snap)
    check(len(mft) == MFT_SIZE and mft[:4] == MFT_MAGIC,
          "TIER 1 holds the whole table, all 24 bytes of every row",
          f"{len(mft)} B, {snap['tier1']['rows']} rows")
    check(snap["tier0"]["descriptor_counter"] == 7
          and snap["tier0"]["mft_offset"] == MFT_OFF,
          "TIER 0 holds the counter and the MFT's location", f"{snap['tier0']}")
    stale = dict(snap)
    stale["snapshot_version"] = 999
    stale_path = os.path.join(tmp, "stale.json")
    with open(stale_path, "w", encoding="utf-8") as fh:
        json.dump(stale, fh)
    try:
        datcheck.load_snapshot(stale_path)
        refused = False
    except ValueError:
        refused = True
    check(refused, "a snapshot from another version is refused, not read")

    torn = json.loads(json.dumps(snap))
    torn["tier1"]["mft_sha256"] = "0" * 64
    try:
        datcheck._snapshot_mft(torn)
        caught = False
    except ValueError:
        caught = True
    check(caught, "a snapshot whose MFT does not match its own digest is refused")

    print("\n5. the MFT is located from a header read in the same call")
    # The MFT moves. A reader that seeks to a remembered offset reads the wrong
    # table and diffs it against itself; this is the one property of the whole
    # module that a wrong answer looks identical to a right one.
    p = fresh(tmp, "moved-mft.dat")
    with open(p, "r+b") as fh:
        fh.seek(MFT_OFF)
        table = fh.read(MFT_SIZE)
        fh.seek(0x1000)
        fh.write(table)
        fh.seek(MFT_OFF)
        fh.write(b"\xEE" * MFT_SIZE)
        fh.seek(0x10)
        fh.write(struct.pack("<Q", 0x1000))
    poke_row(p, ROW_SELF, offset=0x1000)
    hdr = datcheck.read_header(p)
    check(hdr["mft_offset"] == 0x1000,
          "the header is re-read, so a moved MFT is found where it now is")
    moved_mft = datcheck.read_mft(p)
    check(moved_mft[:4] == MFT_MAGIC and len(moved_mft) == MFT_SIZE,
          "and the table read from the new location is the table")
    d = datcheck.diff(before, path=p)
    check(d["tier0"].get("mft_offset", {}).get("after") == 0x1000,
          "TIER 0 reports the move", f"{sorted(d['tier0'])}")

    print("\n6. archive.py honours RURIK_DAT")
    saved = os.environ.get("RURIK_DAT")
    try:
        os.environ.pop("RURIK_DAT", None)
        mod = importlib.reload(archive_mod)
        check(mod.DEFAULT_DAT.lower().endswith("dat_study\\gw.dat")
              or mod.DEFAULT_DAT.lower().endswith("dat_study/gw.dat"),
              "with the variable unset, DEFAULT_DAT is the study copy",
              mod.DEFAULT_DAT)
        os.environ["RURIK_DAT"] = before_path
        mod = importlib.reload(archive_mod)
        check(mod.DEFAULT_DAT == before_path,
              "with it set, DEFAULT_DAT follows it", mod.DEFAULT_DAT)
        with mod.Archive() as ar:
            check(ar.entry_count == ENTRY_COUNT and ar.path == before_path,
                  "and Archive() with NO path opens that archive",
                  f"{ar.entry_count} entries from {os.path.basename(ar.path)}")
        # The lever has to be a lever, not a constant nobody reads: point it at
        # a file that is not an archive and the default open must fail there.
        notdat = os.path.join(tmp, "not-an-archive.bin")
        with open(notdat, "wb") as fh:
            fh.write(b"nope" * 16)
        os.environ["RURIK_DAT"] = notdat
        mod = importlib.reload(archive_mod)
        try:
            mod.Archive().close()
            refused = False
        except ValueError:
            refused = True
        check(refused, "and a bad RURIK_DAT fails at the override, not silently "
                       "at the old default")
    finally:
        if saved is None:
            os.environ.pop("RURIK_DAT", None)
        else:
            os.environ["RURIK_DAT"] = saved
        importlib.reload(archive_mod)

    print("\n7. the three exit codes stay apart")
    # `--diff` exits 1 to mean "the archive CHANGED", which is a result. If an
    # archive this tool cannot read exited 1 as well, anything reading the code
    # would report a crash as that result -- so unreadable is its own code, and
    # the run sheet's "exit 1 means something changed" only holds because of it.
    tool = os.path.join(HERE, "datcheck.py")
    clean = fresh(tmp, "exit-clean.dat")
    snap_path = os.path.join(tmp, "exit.json")
    datcheck.write_snapshot(clean, snap_path)

    def run_cli(*argv):
        return subprocess.run([sys.executable, tool] + list(argv),
                              capture_output=True, text=True)

    def cli(*argv):
        return run_cli(*argv).returncode

    # BOTH VERBS, THROUGH THE REAL CLI. §3b checks `format_diff` as a function;
    # this is the only place the `--preflight` banner is reached at all, and it
    # is a separate `print` in `_main` that the function-level checks cannot
    # see -- the revert sabotage deleted it and §3b's six reds did not include
    # it. A convention line nobody prints is a convention line nobody reads.
    banner_dat = fresh(tmp, "exit-banner.dat")
    poke_row(banner_dat, ROW_A, offset=0x1000)
    pre_out = run_cli("--dat", clean, "--preflight").stdout
    diff_out = run_cli("--dat", banner_dat, "--diff", snap_path).stdout
    check(datcheck.ROW_CONVENTION in pre_out
          and datcheck.ROW_CONVENTION in diff_out,
          "both verbs print the row convention through the real CLI, not just "
          "through format_diff()",
          f"preflight={datcheck.ROW_CONVENTION in pre_out} "
          f"diff={datcheck.ROW_CONVENTION in diff_out}")

    check(cli("--dat", clean, "--preflight") == 0,
          "a clean archive exits 0", "--preflight")
    check(cli("--dat", clean, "--diff", snap_path) == 0,
          "an unchanged archive exits 0", "--diff")
    changed = fresh(tmp, "exit-changed.dat")
    poke_row(changed, ROW_A, offset=0x1000)
    check(cli("--dat", changed, "--diff", snap_path) == 1,
          "a changed archive exits 1 -- a RESULT, not an error", "--diff")
    broken = fresh(tmp, "exit-broken.dat")
    poke(broken, MFT_OFF, b"XXXX")           # no MFT where the header says
    check(cli("--dat", broken, "--preflight") == 2,
          "an archive that cannot be read exits 2, not 1", "--preflight")
    check(cli("--dat", broken, "--diff", snap_path) == 2,
          "and 2 from --diff too, so a crash is never read as 'it changed'",
          "--diff")


if __name__ == "__main__":
    sys.exit(main())
