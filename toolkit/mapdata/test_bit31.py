"""Check the bit-31 census -- the rows whose replacement the client is waiting for.

WHAT MAKES THIS FILE NECESSARY IS NOT THE COUNTING. "29 bit-31 ids were found"
is a number an almost-right census also prints, and the tool's whole job is to
be believed when it says NOTHING CHANGED. A 900 s loopback session on
2026-08-14 reported "29 -> 29" and that reading is only worth anything because
the two SETS were compared: four ids clearing while four others are newly set
leaves the count identical and describes a different archive. So the
load-bearing section here is 3, and its control is the count-comparing diff
REPRODUCED INLINE as a live function that must MISS what the real one catches.

The fixture is a complete archive this file builds in a temp directory, laid out
so every shape the census must distinguish is present at once: a plain id, a
bit-31 id on a MAP-flagged row, two ids aliasing ONE row, a bit-31 id whose
masked form ALSO binds, and a bit-31 id naming a row this archive does not have.
The last two are there because they are the cases `archive.py` makes a claim
about -- "for none of them is the masked form also present" -- and a census that
could not report them could never refute it.

Sections 0-6 need no vault, no client and no socket. Section 7 reproduces the
cross-copy population from real archives and SKIPS whole without them.

    python toolkit/mapdata/test_bit31.py
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
import bit31  # noqa: E402
import checks  # noqa: E402
import vaultpath  # noqa: E402

# FLOOR: two shapes, and BOTH have zero headroom.
#
# `FLOOR_BARE` is what sections 0-6 run with no vault, MEASURED by running with
# RURIK_VAULT pointed at a directory that does not exist -- never counted by
# hand, because the first version of this line guessed 47 and was wrong by
# eight, the same mistake test_glyphs.py and test_emblem.py both shipped hours
# apart. `FLOOR_VAULT` is the vaulted total, and section 7 RAISES the floor to
# it as its last act.
#
# The two-shape arrangement is the point: a single fixed 55 left a vaulted run
# carrying eight checks of slack, and an auditor showed on 2026-08-14 that the
# whole load-bearing sabotage section plus three of section 2's checks could be
# deleted with the run still printing ALL CHECKS PASSED. That is `test_archive`'s
# shape, and it is here for the same reason.
FLOOR_BARE = 76
FLOOR_VAULT = 86
LEDGER = checks.Ledger("bit-31 census", floor=FLOOR_BARE)
check = checks.adopt(LEDGER)

FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"
ENTRY_CRC = 0x14
MAP_FLAGS = 259        # restated, not imported: it belongs to the code under test

BLOCK = 512
FILE_SIZE = 0x1000
MFT_OFF = 0x0E00
ENTRY_COUNT = 8
MFT_SIZE = ENTRY_COUNT * ENTRY_SIZE
SLACK = 0xCC

ROW_HEADER, ROW_IDTABLE, ROW_SELF = 1, 2, 3
ROW_PLAIN, ROW_MAP, ROW_ALIAS, ROW_COMPETE = 4, 5, 6, 7
ROW_ABSENT = 999       # named by an id, not present in the table

# (file_id, row). The shapes, in one table:
#   0x1000      -> 4   an ordinary plain id, which must NOT be censused
#   0x80002000  -> 5   bit 31, on a MAP-flagged row
#   0x80003000  -> 6   bit 31 \  two ids aliasing ONE row, the shape datwrite
#   0x80004000  -> 6   bit 31 /  calls "the alias it saw zeroed"
#   0x80005000  -> 7   bit 31 \  masked form ALSO binds -- archive.py:475 says
#   0x00005000  -> 7   plain  /  this never happens; the census must be able to say
#   0x80009999  -> 999 bit 31, naming a row this archive does not have
PAIRS = [(0x1000, ROW_PLAIN), (0x80002000, ROW_MAP), (0x80003000, ROW_ALIAS),
         (0x80004000, ROW_ALIAS), (0x80005000, ROW_COMPETE),
         (0x00005000, ROW_COMPETE), (0x80009999, ROW_ABSENT)]
IDTABLE = b"".join(struct.pack("<II", f, r) for f, r in PAIRS)

ROWS = {
    ROW_HEADER:  (0x0000, 32,            0, 3),
    ROW_IDTABLE: (0x0200, len(IDTABLE),  0, 3),
    ROW_SELF:    (MFT_OFF, MFT_SIZE,     0, 3),
    ROW_PLAIN:   (0x0400, 100,           0, 3),
    ROW_MAP:     (0x0600, 200,           0, MAP_FLAGS),
    ROW_ALIAS:   (0x0800, 300,           0, 3),
    ROW_COMPETE: (0x0A00, 400,           0, 3),
}
PAYLOAD_ROWS = (ROW_IDTABLE, ROW_PLAIN, ROW_MAP, ROW_ALIAS, ROW_COMPETE)


def K(file_id):
    """The census keys bit31 by str(int). Computed, never a decimal literal:
    the first version hand-converted four ids and got two of them wrong."""
    return str(file_id)


def pattern(seed, n):
    return bytes(1 + ((i * 37 + seed * 101) % 255) for i in range(n))


def self_crc(mft):
    """Row 3's crc, spelled out from test_datcrc.py's MEASURED rule."""
    acc = binascii.crc32(bytes(mft[0x00:ROW_SELF * ENTRY_SIZE]))
    return binascii.crc32(
        bytes(mft[(ROW_SELF + 1) * ENTRY_SIZE:ENTRY_COUNT * ENTRY_SIZE]), acc)


def build_archive(path, idtable=IDTABLE, mft_off=MFT_OFF, rows=None):
    """A complete, self-checking archive. `idtable`/`mft_off` vary per fixture."""
    rows = dict(rows or ROWS)
    rows[ROW_IDTABLE] = (rows[ROW_IDTABLE][0], len(idtable),
                         rows[ROW_IDTABLE][2], rows[ROW_IDTABLE][3])
    rows[ROW_SELF] = (mft_off, MFT_SIZE, 0, 3)
    buf = bytearray(bytes([SLACK]) * FILE_SIZE)
    for row in PAYLOAD_ROWS:
        off, size, _c, _f = rows[row]
        data = idtable if row == ROW_IDTABLE else pattern(row, size)
        buf[off:off + size] = data

    head = bytearray(32)
    head[0:4] = FILE_MAGIC
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<I", head, 0x10, mft_off)
    struct.pack_into("<I", head, 0x18, MFT_SIZE)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head

    mft = bytearray(MFT_SIZE)
    mft[0:4] = MFT_MAGIC
    struct.pack_into("<I", mft, 0x0C, ENTRY_COUNT)
    for row in range(1, ENTRY_COUNT):
        off, size, comp, flags = rows[row]
        crc = 0 if row in (ROW_HEADER, ROW_SELF) else \
            binascii.crc32(bytes(buf[off:off + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         off, size, comp, flags, 0, crc)
    struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + ENTRY_CRC, self_crc(mft))
    buf[mft_off:mft_off + MFT_SIZE] = mft
    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return path


def fresh(tmp, name, **kw):
    return build_archive(os.path.join(tmp, name), **kw)


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


def run_cli(*argv):
    """Through _main and argparse, because the exit codes are the contract."""
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            code = bit31._main(list(argv))
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
    return code, buf.getvalue()


# ---------------------------------------------------------------- the sections

def section_shapes(tmp):
    print("\n0. every shape the census must tell apart, in one table")
    dat = fresh(tmp, "base.dat")
    cen = bit31.census(dat)
    ids = {int(f) for f in cen["bit31"]}
    check(ids == {0x80002000, 0x80003000, 0x80004000, 0x80005000, 0x80009999},
          f"the five bit-31 ids are censused and the two PLAIN ids are not "
          f"(got {sorted(hex(i) for i in ids)})")
    check(cen["file_id_pairs"] == len(PAIRS),
          f"and all {len(PAIRS)} pairs were walked (got {cen['file_id_pairs']})")
    check(cen["bit31"][K(0x80002000)]["masked"] == 0x2000,
          "the masked form is recorded beside the raw id")

    print("\n0a. aliases: two ids, one row")
    al = bit31.aliases(cen)
    check(al == {ROW_ALIAS: [0x80003000, 0x80004000]},
          f"row {ROW_ALIAS} is reported as named by exactly two ids (got {al})")
    check(ROW_MAP not in al and ROW_COMPETE not in al,
          "and a row named by one bit-31 id is NOT reported as an alias -- "
          "the plain id beside 0x80005000 must not be counted as a second name")

    print("\n0b. the map-flagged row")
    check(bit31.map_rows(cen) == [0x80002000],
          f"exactly the id on flags {MAP_FLAGS} is flagged as a map row")
    check(cen["bit31"][K(0x80002000)]["is_map_row"] is True
          and cen["bit31"][K(0x80004000)]["is_map_row"] is False,
          "and the flag is per row, not per census")

    print("\n0c. the claim archive.py makes, and the census can refute")
    check(cen["bit31"][K(0x80005000)]["masked_also_binds"] is True,
          "0x80005000's masked form 0x5000 IS separately present, and the "
          "census says so -- archive.py:475 records that this never happens on "
          "retail, so a census that could not report it could not check it")
    check(all(not cen["bit31"][str(f)]["masked_also_binds"]
              for f in (0x80002000, 0x80003000, 0x80004000)),
          "CONTROL: the other ids report False, so the field is a measurement "
          "and not a constant")

    print("\n0d. an id naming a row this archive does not have")
    rec = cen["bit31"][K(0x80009999)]
    check("unresolved" in rec and "size" not in rec,
          "is REPORTED as unresolved rather than raising -- the tool describes "
          "copies we did not make, and a census that dies on one is useless")
    check(len(cen["bit31"]) == 5,
          "and it is still counted in the population")


def section_output(tmp):
    print("\n1. the page an operator actually reads")
    dat = fresh(tmp, "out.dat")
    cen = bit31.census(dat)
    lines = bit31.format_census(cen)
    body = [ln for ln in lines if "-> row" in ln]
    check(len(body) == 5, f"one line per bit-31 id (got {len(body)})")
    check(all("0x" in ln for ln in body),
          "every line names its file id in hex")
    check(any("MAP ROW" in ln for ln in lines)
          and sum("MAP ROW" in ln for ln in lines) == 1,
          "the map row is called out, exactly once")
    check(any("masked ALSO binds" in ln for ln in lines),
          "and so is the competing masked form")
    check(any("UNRESOLVED" in ln for ln in lines),
          "and the unresolvable id says so on its own line")

    print("\n1a. and the diff page names the id on EVERY line")
    other = fresh(tmp, "out2.dat", idtable=b"".join(
        struct.pack("<II", f, r) for f, r in PAIRS[:-1]))
    changes = bit31.diff(cen, bit31.census(other))
    page = bit31.format_diff(changes)
    check(len(page) == len(changes),
          f"one line per change, no change silently dropped "
          f"(got {len(page)} for {len(changes)})")
    # Every line must be attributable, and the two kinds are attributable
    # DIFFERENTLY: a row line has to name its file id, a scalar line has to name
    # its field. The first version of this check demanded a file id on every
    # line and went red on `file_id_pairs: 7 -> 6`, which is a fact about the
    # archive and has no id to name -- the check was wrong, not the page.
    scalar_fields = set(bit31.SCALARS)
    for line, chg in zip(page, changes):
        if chg["kind"] == "scalar":
            check(chg["field"] in scalar_fields and chg["field"] in line,
                  f"the scalar line names its field ({chg['field']})")
        else:
            check(f"{chg['file_id']:#010x}" in line,
                  f"the line for {chg['file_id']:#010x} names that id -- "
                  f"'row 18 relocated' is what test_datcheck had to fix")
    check(bit31.format_diff([]) == [
        "  NO CHANGE: same bit-31 ids, same rows, same bytes"],
        "and an empty diff says NO CHANGE in words, not as a blank page")


def section_setnotcount(tmp):
    """3. THE LOAD-BEARING ONE. Equal count, different set."""
    print("\n2. SETS, NOT COUNTS -- the check the whole tool rests on")
    before = bit31.census(fresh(tmp, "sc-before.dat"))
    # Clear two ids and set two others. The COUNT is unchanged.
    swapped = [(0x1000, ROW_PLAIN), (0x80002000, ROW_MAP),
               (0x80007000, ROW_ALIAS), (0x80008000, ROW_ALIAS),
               (0x80005000, ROW_COMPETE), (0x00005000, ROW_COMPETE),
               (0x80009999, ROW_ABSENT)]
    after = bit31.census(fresh(tmp, "sc-after.dat", idtable=b"".join(
        struct.pack("<II", f, r) for f, r in swapped)))
    check(len(before["bit31"]) == len(after["bit31"]) == 5,
          "the two censuses hold the SAME NUMBER of bit-31 ids")
    changes = bit31.diff(before, after)
    kinds = [c["kind"] for c in changes]
    check(kinds.count("cleared") == 2 and kinds.count("newly_set") == 2,
          f"and the diff still reports 2 cleared and 2 newly set "
          f"(got {kinds})")
    check(bit31.changed(before, after),
          "changed() is True on an archive whose bit-31 COUNT did not move")

    # The control: the count-comparing reading, reproduced as a live function.
    def count_diff(a, b):
        return len(a["bit31"]) != len(b["bit31"])
    check(count_diff(before, after) is False,
          "CONTROL: comparing COUNTS answers 'no change' on the same pair -- "
          "which is what the 2026-08-14 session's '29 -> 29' would have meant "
          "if the sets had not been compared")
    check(count_diff(before, before) is False and not bit31.changed(before, before),
          "and both agree when nothing moved, so the control is not simply "
          "always-wrong")

    print("\n2a. and no scalar can stand in for it either")
    for field in bit31.SCALARS:
        check(before.get(field) == after.get(field),
              f"{field} is IDENTICAL across the swap, so it could not have "
              f"carried the signal")


# Offsets within a 24-byte MFT row, from the `<QIHHII` the fixture packs.
# Restated here, not imported, because they belong to the format under test.
F_OFFSET, F_SIZE, F_COMP, F_FLAGS, F_COUNTER, F_CRC = (0x00, 0x08, 0x0C, 0x0E,
                                                       0x10, 0x14)


def patch_mft(src, dst, row, field_off, fmt, value):
    """Copy `src` to `dst`, change ONE MFT field, fix the self-crc.

    The fixture's own writer, deliberately not bit31's: a control built with the
    code under test agrees with it by construction.
    """
    shutil.copyfile(src, dst)
    with open(dst, "r+b") as fh:
        fh.seek(MFT_OFF)
        mft = bytearray(fh.read(MFT_SIZE))
        struct.pack_into(fmt, mft, row * ENTRY_SIZE + field_off, value)
        struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + ENTRY_CRC, 0)
        struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + ENTRY_CRC,
                         self_crc(mft))
        fh.seek(MFT_OFF)
        fh.write(bytes(mft))
    return dst


def rowfield_fixtures(tmp):
    """One archive per ROW_FIELDS entry, each differing from base by that field.

    Returns {field: (path, isolated)}. `isolated` is False where the edit
    CANNOT move that field alone, and those two are named rather than faked:
    `size` co-varies with `sha256` because a shorter read is a different hash,
    and `unresolved` appearing means every other field disappears with it.
    """
    base = fresh(tmp, "rf-base.dat")
    out = {}

    # row: repoint the id at another row, through the id table. NOT isolated,
    # and it cannot be: pointing an id at a DIFFERENT row necessarily brings
    # that row's offset, size, crc, flags and hash with it. Isolating it would
    # need two rows identical in every field but their offset, which is not a
    # state an archive can be in.
    out["row"] = (fresh(tmp, "rf-row.dat", idtable=b"".join(
        struct.pack("<II", f, ROW_PLAIN if f == 0x80002000 else r)
        for f, r in PAIRS)), False)

    # slots: same pairs, different order.
    out["slots"] = (fresh(tmp, "rf-slots.dat", idtable=b"".join(
        struct.pack("<II", f, r) for f, r in reversed(PAIRS))), True)

    # offset: move ROW_MAP's payload bytes AND its offset. Same content, so
    # size, crc and sha256 are all unmoved -- this is a ROW RELOCATION, which is
    # what datmove.py performs and what the client does unprompted (FINDINGS 4c).
    reloc = os.path.join(tmp, "rf-offset.dat")
    shutil.copyfile(base, reloc)
    body = pattern(ROW_MAP, ROWS[ROW_MAP][1])
    with open(reloc, "r+b") as fh:
        fh.seek(0x0C00)
        fh.write(body)
    patch_mft(reloc, reloc + ".2", ROW_MAP, F_OFFSET, "<Q", 0x0C00)
    os.replace(reloc + ".2", reloc)
    out["offset"] = (reloc, True)

    # size: shrink the declared length. NOT isolated -- the hash is over `size`
    # bytes, so sha256 necessarily moves with it.
    out["size"] = (patch_mft(base, os.path.join(tmp, "rf-size.dat"),
                             ROW_MAP, F_SIZE, "<I", 150), False)
    # crc: the STORED checksum only. The payload is untouched, so sha256 holds --
    # which is the state a half-finished write leaves.
    out["crc"] = (patch_mft(base, os.path.join(tmp, "rf-crc.dat"),
                            ROW_MAP, F_CRC, "<I", 0xDEADBEEF), True)
    out["compression"] = (patch_mft(base, os.path.join(tmp, "rf-comp.dat"),
                                    ROW_MAP, F_COMP, "<H", 8), True)
    out["flags"] = (patch_mft(base, os.path.join(tmp, "rf-flags.dat"),
                              ROW_MAP, F_FLAGS, "<H", 3), True)
    # counter is alloc.nextStream, the SIBLING LINK. A relink leaves the
    # payload, the size and the crc untouched -- so without this field a map
    # row's partner being repointed prints "NO CHANGE". It was censused and not
    # diffed until an audit on 2026-08-14.
    out["counter"] = (patch_mft(base, os.path.join(tmp, "rf-counter.dat"),
                                ROW_MAP, F_COUNTER, "<I", 4242), True)

    # sha256: one payload byte, crc left alone.
    touched = os.path.join(tmp, "rf-sha.dat")
    shutil.copyfile(base, touched)
    with open(touched, "r+b") as fh:
        fh.seek(ROWS[ROW_MAP][0])
        fh.write(b"\x00")
    out["sha256"] = (touched, True)

    # masked_also_binds: drop the competing PLAIN id. The pair count is
    # unchanged (it is replaced, not removed), so every scalar holds.
    out["masked_also_binds"] = (fresh(tmp, "rf-mask.dat", idtable=b"".join(
        struct.pack("<II", 0x00006000 if f == 0x00005000 else f, r)
        for f, r in PAIRS)), True)

    # unresolved: push the extent past EOF. NOT isolated -- every other field
    # vanishes when a row stops resolving.
    out["unresolved"] = (patch_mft(base, os.path.join(tmp, "rf-unres.dat"),
                                   ROW_MAP, F_OFFSET, "<Q", 0x0FF0), False)
    return base, out


def section_rowfields(tmp):
    print("\n3. EVERY field a surviving id can change under")
    base, fx = rowfield_fixtures(tmp)
    before = bit31.census(base)

    # COMPLETENESS, and this is the check that would have caught `counter`:
    # every key a census record carries must be diffed or explicitly derived.
    keys = set()
    for rec in before["bit31"].values():
        keys |= set(rec)
    stray = keys - set(bit31.ROW_FIELDS) - set(bit31.DERIVED)
    check(not stray,
          f"every key a census record carries is in ROW_FIELDS or DERIVED "
          f"(stray: {sorted(stray)}) -- a field censused and forgotten is "
          f"invisible to every diff, which is what `counter` was")
    check(set(bit31.DERIVED) <= keys,
          f"and DERIVED names only keys that really occur (got "
          f"{bit31.DERIVED})")
    check(set(fx) == set(bit31.ROW_FIELDS),
          f"this section has a fixture for EVERY ROW_FIELDS entry -- missing: "
          f"{sorted(set(bit31.ROW_FIELDS) - set(fx))}, extra: "
          f"{sorted(set(fx) - set(bit31.ROW_FIELDS))}")

    for field, (path, isolated) in sorted(fx.items()):
        changes = bit31.diff(before, bit31.census(path))
        fields = {c.get("field") for c in changes if c["kind"] == "row_field"}
        check(field in fields,
              f"a change to {field!r} is REPORTED (fields seen: "
              f"{sorted(f for f in fields if f)})")
        if isolated:
            check(fields == {field},
                  f"and {field!r} moved ALONE, so the check below can prove it "
                  f"is load-bearing (got {sorted(fields)})")

    print("\n3a. and dropping any of them from ROW_FIELDS goes BLIND")
    # THE MEASUREMENT the first version of this file did not make: seven of ten
    # fields could be deleted from ROW_FIELDS with every check still green,
    # including `offset` -- a row relocation reporting "NO CHANGE".
    real = bit31.ROW_FIELDS
    blind = []
    try:
        for field, (path, isolated) in sorted(fx.items()):
            if not isolated:
                continue
            bit31.ROW_FIELDS = tuple(f for f in real if f != field)
            if not bit31.diff(before, bit31.census(path)):
                blind.append(field)
    finally:
        bit31.ROW_FIELDS = real
    want = sorted(f for f, (_p, iso) in fx.items() if iso)
    check(blind == want,
          f"dropping each isolated field in turn makes its own fixture read "
          f"NO CHANGE -- all {len(want)} of them, so none is decoration "
          f"(blind: {blind}, expected: {want})")
    check(bit31.ROW_FIELDS == real and not bit31.diff(before, bit31.census(base)),
          "CONTROL: ROW_FIELDS is restored and an unchanged archive still "
          "diffs empty")

    print("\n3b. and the MFT moving is a scalar, not a row field")
    elsewhere = fresh(tmp, "rf-mft.dat", mft_off=0x0D00)
    got = [c for c in bit31.diff(before, bit31.census(elsewhere))
           if c["kind"] == "scalar" and c["field"] == "mft_offset"]
    check(len(got) == 1,
          "a moved MFT is reported as a scalar change -- the alternation "
          "FINDINGS 4c measured, seen from here")


def section_cli(tmp):
    print("\n4. the exit codes, which datcheck shares and which get confused")
    dat = fresh(tmp, "cli.dat")
    base = os.path.join(tmp, "cli-before.json")
    code, out = run_cli("--dat", dat, "--json", base)
    check(code == 0, f"a plain census exits 0 (got {code})")
    check(os.path.isfile(base), "and wrote the census where it was told to")

    code, out = run_cli("--dat", dat, "--diff", base)
    check(code == 0, f"--diff against an unchanged archive exits 0 (got {code})")
    check("NO CHANGE" in out, "and says so")

    changed = fresh(tmp, "cli2.dat", idtable=b"".join(
        struct.pack("<II", f, r) for f, r in PAIRS[:-1]))
    code, out = run_cli("--dat", changed, "--diff", base)
    check(code == 1, f"--diff on a CHANGED archive exits 1 (got {code})")
    check("CLEARED" in out, "and names what cleared")

    code, out = run_cli("--dat", os.path.join(tmp, "nope.dat"), "--diff", base)
    check(code == 2,
          f"an unreadable archive exits 2, NOT 1 (got {code}) -- 1 means "
          f"'it changed', and a census that could not be taken must never be "
          f"read as a result")
    check("REFUSED" in out, "and says REFUSED rather than printing a traceback")

    stale = os.path.join(tmp, "stale.json")
    doc = json.load(open(base, encoding="utf-8"))
    doc["format_version"] = 99
    json.dump(doc, open(stale, "w", encoding="utf-8"))
    code, out = run_cli("--dat", dat, "--diff", stale)
    check(code == 2 and "format_version" in out,
          f"a baseline from another format exits 2 and names the field "
          f"(got {code})")

    broken = fresh(tmp, "broken.dat", idtable=IDTABLE + b"\x00\x00\x00")
    code, out = run_cli("--dat", broken)
    check(code == 2 and "8-byte" in out,
          f"an id table that is not a whole number of pairs is REFUSED, rather "
          f"than walked to a confident wrong census (got {code})")


def section_guard(tmp):
    print("\n5. --json may not write into a checkout")
    repo = os.path.dirname(HERE)                    # <tree>/toolkit
    refused = 0
    for victim in (os.path.join(repo, "census.json"),
                   os.path.join(os.path.dirname(repo), "census.json")):
        try:
            bit31.resolve_out(victim)
        except bit31.Refused:
            refused += 1
    check(refused == 2,
          f"both a toolkit/ and a repo-root path are refused (got {refused})")

    ok = os.path.join(tmp, "census.json")
    try:
        allowed = bit31.resolve_out(ok) == os.path.abspath(ok)
    except bit31.Refused:
        allowed = False
    check(allowed,
          "CONTROL: a scratch path is allowed -- a guard that refuses "
          "everything protects nothing, because the tool never runs")

    try:
        vault = vaultpath.require_dir()
    except SystemExit:
        LEDGER.skip("the vault path is allowed", "no vault on this machine")
    else:
        try:
            bit31.resolve_out(os.path.join(vault, "b31.json"))
            vault_allowed = True
        except bit31.Refused:
            vault_allowed = False
        check(vault_allowed,
              "and the REAL vault is allowed BY NAME, though it sits inside "
              "the main checkout -- it is gitignored and is where derived data "
              "goes")
        try:
            bit31.resolve_out(os.path.join(vault, "dat_study", "Gw.dat"))
            study_allowed = True
        except bit31.Refused:
            study_allowed = False
        check(not study_allowed,
              "but vault/dat_study is refused INSIDE it -- the source snapshot "
              "every other copy is cut from, and the allow must not swallow it")

    print("\n5a. and the two paths a census must never truncate")
    for victim, why in ((r"C:\gw\Gw.dat", "the owner's own install"),
                        (r"C:\gw", "the install directory")):
        try:
            bit31.resolve_out(victim)
            refused_live = False
        except bit31.Refused:
            refused_live = True
        check(refused_live,
              f"--json {victim} is refused ({why}) -- open(out, 'w') would "
              f"TRUNCATE it, which is the defect atex.py shipped with")

    code, out = run_cli("--dat", fresh(tmp, "g.dat"), "--json",
                        os.path.join(repo, "nope.json"))
    check(code == 2 and "REFUSED" in out,
          f"and the CLI turns that into exit 2, not a traceback (got {code})")
    check(not os.path.isfile(os.path.join(repo, "nope.json")),
          "and nothing was written")


def section_sabotage(tmp):
    print("\n6. WHICH CHECKS ARE LOAD-BEARING, measured by sabotage")
    before = bit31.census(fresh(tmp, "sb-before.dat"))
    swapped = [(0x80007000, ROW_ALIAS) if p == (0x80003000, ROW_ALIAS) else p
               for p in PAIRS]
    after = bit31.census(fresh(tmp, "sb-after.dat", idtable=b"".join(
        struct.pack("<II", f, r) for f, r in swapped)))

    real_fields = bit31.ROW_FIELDS
    try:
        bit31.ROW_FIELDS = ("row", "size")     # drop sha256 and slot
        touched = os.path.join(tmp, "sb-touch.dat")
        shutil.copyfile(os.path.join(tmp, "sb-before.dat"), touched)
        with open(touched, "r+b") as fh:
            fh.seek(ROWS[ROW_MAP][0])
            fh.write(b"\x00")
        check(not bit31.diff(before, bit31.census(touched)),
              "SABOTAGE: with sha256 out of ROW_FIELDS a flipped payload byte "
              "goes UNSEEN -- so section 3's hash check is load-bearing")
    finally:
        bit31.ROW_FIELDS = real_fields

    check(bit31.diff(before, bit31.census(
        os.path.join(tmp, "sb-before.dat"))) == [],
        "CONTROL: with ROW_FIELDS restored, an unchanged archive still diffs "
        "empty -- the sabotage was undone rather than left in place")

    real_high = bit31.FILE_ID_HIGH_BIT
    try:
        bit31.FILE_ID_HIGH_BIT = 0x40000000    # the wrong bit
        cen = bit31.census(os.path.join(tmp, "sb-before.dat"))
        check(len(cen["bit31"]) == 0,
              "SABOTAGE: censusing on the wrong high bit finds NOTHING, and "
              "prints a clean confident zero -- which is why section 0 asserts "
              "the exact id SET and not a count")
    finally:
        bit31.FILE_ID_HIGH_BIT = real_high

    check(len(bit31.census(os.path.join(tmp, "sb-before.dat"))["bit31"]) == 5,
          "CONTROL: and five again once it is restored")
    check(len(bit31.diff(before, after)) == 2,
          "the real diff reports the one cleared and the one newly set")


def section_vault():
    print("\n7. the cross-copy population, on real archives")
    try:
        root = vaultpath.require_dir()
    except SystemExit:
        # require_dir, not vault_root: vault_root() NEVER raises, so the arm
        # below was dead code and the skip could not print. A fixture that
        # silently resolves to nothing turns every assertion behind it into a
        # no-op, which is the whole reason require_dir exists.
        LEDGER.skip("the cross-copy population", "no vault on this machine")
        return
    copies = {
        "install": os.path.join(root, "client", "2026-07-29_221c13772c7a",
                                "Gw.dat"),
        "study": os.path.join(root, "dat_study", "Gw.dat"),
        "live": os.path.join(root, "run-live", "2026-07-29_221c13772c7a",
                             "Gw.dat"),
    }
    missing = [k for k, p in copies.items() if not os.path.isfile(p)]
    if missing:
        LEDGER.skip("the cross-copy population",
                    f"absent from this vault: {', '.join(missing)}")
        return

    cen = {k: bit31.census(p) for k, p in copies.items()}
    check(len(cen["install"]["bit31"]) == 29,
          f"the pristine install carries 29 bit-31 ids "
          f"(got {len(cen['install']['bit31'])})")
    check(len(cen["study"]["bit31"]) == 25,
          f"the study copy carries 25 (got {len(cen['study']['bit31'])})")
    check(len(cen["live"]["bit31"]) == 9,
          f"and run-live, the copy with a real content source, carries 9 "
          f"(got {len(cen['live']['bit31'])})")

    cleared = [c for c in bit31.diff(cen["install"], cen["study"])
               if c["kind"] == "cleared"]
    check(len(cleared) == 4,
          f"install -> study clears exactly 4 ids (got {len(cleared)})")
    check(len({c["row"] for c in cleared}) == 2,
          "over exactly TWO rows -- 'two in place and two aliases', which is "
          "what datwrite/FINDINGS.md:589 recorded and this reproduces from "
          "the bytes")
    check(not any(c["is_map_row"] for c in cleared),
          "and NEITHER is a map row: what a loopback history resolves and what "
          "a live one resolves are different populations")

    live_cleared = [c for c in bit31.diff(cen["install"], cen["live"])
                    if c["kind"] == "cleared"]
    check(any(c["row"] == 7982 for c in live_cleared),
          "while install -> run-live DOES clear row 7982 -- the donor_row every "
          "content/areas.toml row borrows from")
    # NO SLACK ON THE VAULTED SHAPE either. With a fixed floor of 55 a vaulted
    # run carried eight checks of headroom, and an auditor showed the whole
    # sabotage section could be deleted with the run still green.
    LEDGER.floor = FLOOR_VAULT
    check(bit31.map_rows(cen["install"]) and
          len(bit31.map_rows(cen["install"])) == 4,
          f"four bit-31 ids sit on map-flagged rows in the install copy "
          f"(got {len(bit31.map_rows(cen['install']))}) -- corroborating "
          f"customarea/FINDINGS.md:967's correction of 'two' to four, from an "
          f"archive that file never read")


def guarded(fn, *args):
    """Run a section; turn a crash into a NAMED failing check.

    Without this a defect anywhere raises, main() never reaches its verdict, and
    the run prints no banner, no ledger and no floor shortfall -- which reads as
    a broken test rather than a caught defect, and makes the floor unreachable
    as a guard. test_marks.py earned this the same way: of 109 sabotages against
    its unguarded version, twelve died mid-file and four hung.
    """
    try:
        fn(*args)
    except KeyboardInterrupt:
        raise
    except BaseException as exc:                               # noqa: BLE001
        # BaseException, not Exception: `bit31.Refused` subclasses SystemExit,
        # and so does `vaultpath.require_dir`'s failure. With the narrow catch a
        # refusal anywhere in a section killed the whole run -- no banner, no
        # ledger, no floor shortfall -- which is the trap this repo has recorded
        # for test_stripbuild.py and test_content.py and which an auditor
        # reproduced here on 2026-08-14.
        import traceback
        traceback.print_exc()
        check(False, f"section {fn.__name__} ran to completion "
                     f"({type(exc).__name__}: {exc})")


def main():
    tmp = tempfile.mkdtemp(prefix="rurik-bit31-")
    print(f"synthetic archive: {FILE_SIZE} B, {ENTRY_COUNT} rows, in {tmp}")
    try:
        for fn in (section_shapes, section_output, section_setnotcount,
                   section_rowfields, section_cli, section_guard,
                   section_sabotage):
            guarded(fn, tmp)
        guarded(section_vault)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
