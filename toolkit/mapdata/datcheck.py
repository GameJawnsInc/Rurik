"""Pre-flight and post-flight for an archive an experiment is about to hand a client.

`datwrite.py` puts bytes in. `datcheck.py` is the pair of questions around it:
**is this copy one the client will open without repairing it**, and **what did
the client change while it had it**. Both are read-only; nothing here opens an
archive for writing, and nothing here launches anything.

**THE THREE CHECKSUMS CANNOT DETECT WHAT THIS EXISTS TO DETECT.** The client
recomputes the entry CRC from the bytes it just wrote, recomputes the MFT
self-CRC on every flush, and never touches the 12 bytes the header CRC covers.
So a row the client silently RELOCATED is fully self-consistent: every rule in
`datwrite.py --verify` still verifies, `--revert` writes the old payload to an
extent nothing points at and reports success, and nothing anywhere reports a
loss. `--verify` answers "is this archive internally consistent"; only a 24-byte
MFT diff against a snapshot answers "is this the same archive". Run both.
(studies/customarea/FINDINGS.md 16-P2 and 18.5.)

WHAT THE PRE-FLIGHT CHECKS, AND WHY EACH ONE IS THERE. Every item is something
the CLIENT itself does at open, so a copy that fails one does not produce a
clean error -- it produces a repair, a rebuild, a silent delete, or an assert
that kills the process with no useful message. SOURCE-CODE throughout, from
FINDINGS 18.4/18.8/18.11 against build 38797; the addresses are that document's.

  modification-in-progress   A copy taken from a mid-write archive is a booby
  (file offset 0x1C)         trap: `BeginModification` (0x0047B470) is called on
                             the FIRST write of a session and asserts the flag is
                             clear. Asserts terminate the process. `datwrite.py`
                             never touches 0x1C, so it cannot see this.

                             WHICH BIT IS CONTESTED IN OUR OWN DOCUMENTS, and
                             this module refuses to pick. FINDINGS 18.8/18.11 say
                             **bit 0**; FINDINGS 18.4 quotes the instruction as
                             `0x0047B6FB test byte [esi+0x1c],2` and
                             studies/datwrite/FINDINGS.md says **bit 1**. The
                             corpus cannot discriminate -- MEASURED, the dword
                             reads 0x00000000 on every cleanly-closed archive on
                             this machine -- so both are checked, separately, and
                             a run that trips either says which.

  header CRC (0x00..0x0C)    Validated on EVERY open at 0x0047B6D2, and the
                             failure route in `ArchiveOpen` tail-jumps to
                             **ArchiveCreate** (0x004797EC). The risk is not an
                             error dialog; it is the archive being rebuilt.

  extents aligned / in EOF   The open-time walk (0x0047C390-0x0047C3D9) reads
  / non-overlapping          every row's extent. An overlap makes the free-map
                             rebuild refuse (0x0047B45A) and the client goes to
                             "Repairing corrupt archive"; an overlapping FREE is
                             fatal (ExeArchive:420). Overlap is tested on the
                             block-rounded RESERVATION, not on `size`, because
                             that is the span the allocator owns. Alignment is
                             checked even though the rebuild NORMALISES a
                             misaligned offset rather than refusing it -- a
                             normalised offset is a row pointing somewhere else.

  directory invariant,       An open-time reconcile pass (0x0047B7D7 ->
  both ways                  0x0047BE50) runs unconditionally, and it DELETES a
                             USED|FIRST_STREAM row at index >= 16 with no
                             file-id record -- frees the extent, memsets the 24
                             bytes, logs `Entry %u exists in mft but not
                             directory` -- and removes a directory record whose
                             row is not USED. Authoring a row without registering
                             it does not fail loudly; it works once and is gone
                             at the next launch.

  rows 0..15 untouched       `INDEX_FIRST_FILE = 16` (0x0047C3E3). Rows 0..15 are
                             structurally reserved: 0 the descriptor, 1 the file
                             header, 2 the file-id table, 3 the MFT, 4..15 unused
                             and all-zero. They are never spare-listed and never
                             recycled.

  no USED-clear row >= 16    `LoadMft` pushes any such row onto a spare stack and
                             `NewEntry` pops LIFO. A row we leave USED-clear is
                             handed to an unrelated new file at the next launch,
                             extent and all.

WHAT THE SNAPSHOT HOLDS (FINDINGS 18.5):

  Tier 0, 48 bytes           `header[0x10:0x20]` (mftOffset u64, mftSize u32,
                             flags u32) and the MFT descriptor's u32 at +0x04.
                             **Read the header FIRST** -- the MFT itself moves,
                             so a snapshot that seeks to a remembered offset
                             reads the wrong table. That counter is the part
                             carrying the signal; `mftOffset` alone is not a
                             change signal (it was byte-identical across 159
                             flushes in one diffed pair).

  Tier 1                     All 24 bytes of every MFT row. Stored whole, zlib'd
                             and base64'd, because the classification in
                             `diff()` needs the bytes and not a digest.

  Tier 2                     The directory invariant's result, plus a digest of
                             the file-id table -- the only check that catches a
                             reconcile-triggered delete, and the one thing the
                             client ENFORCES rather than repairs past.

    python toolkit/mapdata/datcheck.py --dat DAT --preflight
    python toolkit/mapdata/datcheck.py --dat DAT --snapshot before.json
    python toolkit/mapdata/datcheck.py --dat DAT --diff before.json

ROW NUMBERS, AND WHY EVERY ONE PRINTED HERE CARRIES ITS FILE ID. This tool and
`archive.py` use ONE convention -- the raw MFT index, row 0 the descriptor, 16
the client's `INDEX_FIRST_FILE` -- and they agree on every row of the archive a
run is pointed at (`test_archive.py` §1c, measured over the whole table, both
readings). MEASURED 2026-08-14 on all TEN copies in the vault by hand; §1c
re-measures one per run, which is the copy whose answer matters. That is
worth saying out loud because `studies/crossbuild/FINDINGS.md` §4b.1 concluded
the opposite: `--diff` said "row 71496 changed from 0 B to 6,012 B", `deploy.py`
had said "head 71496, partner 71497", and the pair was read as the client having
eaten an authored map. Both tools were right. 71496 is that map's Bloated HEAD,
which `deploy` arms to zero so the client MUST recompile it; 6,012 B is the
recompile succeeding; the authored bytes are in 71497 and never moved. What
failed was two bare integers being the whole of the evidence. So `row_identity`
gives every row named here the file id and the role that tell it apart from its
neighbour, and both verbs print `ROW_CONVENTION` above their numbers.

ONE CONSEQUENCE WORTH KNOWING BEFORE YOU DIFF TWO OUTPUTS. The `--diff` layout
CHANGED on 2026-08-13: one line per changed row became two (the label, then the
kind), and the corroboration list `[0, 2, 3]` became one labelled line each. So
`vault/dat_durability/diff-38519-to-38797.txt`, which was produced by the old
formatter, is no longer line-comparable with a re-run. Its CONTENT still holds --
40 distinct rows on its `row N` lines, 43 counting the corroboration list -- and
those numbers are in this same convention. Nothing in the tree consumes
`format_diff` programmatically, so nothing else moved.

Exit codes: `--preflight` 0 all clear, 1 something failed. `--diff` 0 the archive
is byte-for-byte the same table it was, 1 something changed (which is a RESULT,
not an error -- "loaded, but the row changed" is a first-class outcome), 2 the
run could not be made.

`test_datcheck.py` builds a synthetic archive and breaks each rule on purpose.
It never touches a real one.
"""

import argparse
import base64
import binascii
import hashlib
import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import (Archive, ENTRY_SIZE, MFT_MAGIC,  # noqa: E402
                     MFT_ROW_OF_ENTRIES_0, row_label,
                     FILE_HEADER_ROW, FILE_ID_TABLE_ROW, MFT_SELF_ROW,
                     FIRST_CLAIMABLE_ROW)

SNAPSHOT_VERSION = 1

# Printed above any list of row numbers this tool produces. It is three lines of
# output against the afternoon it cost: `studies/crossbuild/FINDINGS.md` §4b.1
# is a written-up conclusion that this tool and `archive.py` number rows
# differently, drawn from a `deploy.py` line and a `--diff` line that were in
# fact naming the SAME row correctly. They agree -- `test_archive.py` §1c
# measures it over every row of the copy it is pointed at -- and the number
# that differs is `len(archive.entries)`, which is a list length rather than a
# row count. Naming the convention costs nothing and removes the question.
ROW_CONVENTION = (
    "rows are RAW MFT indices: 0 is the Mft descriptor, %d is entries[0], "
    "16 is INDEX_FIRST_FILE. archive.Archive.row(n) resolves the same n; "
    "archive.Archive.entries is POSITIONAL and entries[n] is a DIFFERENT row."
    % MFT_ROW_OF_ENTRIES_0)

HDR_CRC_SPAN = 0x0C          # the header CRC covers exactly bytes 0x00..0x0C
HDR_CRC_OFF = 0x0C
HDR_TIER0_OFF = 0x10         # mftOffset u64, mftSize u32, flags u32
HDR_TIER0_LEN = 0x10
HDR_MOD_OFF = 0x1C

# Contested between our own documents. See the docstring.
MOD_BIT_FINDINGS_18 = 0x1    # FINDINGS 18.8 / 18.11
MOD_BIT_DISASSEMBLY = 0x2    # FINDINGS 18.4's `test byte [esi+0x1c],2`

DESCRIPTOR_COUNTER_OFF = 0x04    # the u32 the flush increments
DESCRIPTOR_COUNT_OFF = 0x0C

# FILE_HEADER_ROW, FILE_ID_TABLE_ROW, MFT_SELF_ROW and FIRST_CLAIMABLE_ROW are
# imported from `archive.py` above rather than restated here. They used to be
# declared in three modules, and `datplan.py`'s copy was then used with the wrong
# arithmetic for months -- see the MFT ROW NUMBERS block in archive.py.
FLAG_ENTRY_USED = 0x01
FLAG_FIRST_STREAM = 0x02
FILE_HEADER_SIZE = 0x20

FILE_ID_RECORD = struct.Struct("<II")


# ---------------------------------------------------------------- results --

class Check:
    """One pre-flight item. `ok` is the verdict; `detail` is what was measured."""

    __slots__ = ("name", "ok", "detail")

    def __init__(self, name, ok, detail):
        self.name = name
        self.ok = bool(ok)
        self.detail = detail

    def line(self):
        return "[%s] %-34s %s" % ("PASS" if self.ok else "FAIL", self.name,
                                  self.detail)

    def to_json(self):
        return {"name": self.name, "ok": self.ok, "detail": self.detail}

    def __repr__(self):
        return "<Check %s %s>" % (self.name, "ok" if self.ok else "FAILED")


# ------------------------------------------------------------------ reading --

def read_header(path):
    """The 32-byte file header, read fresh. Always the first thing read."""
    with open(path, "rb") as fh:
        head = fh.read(32)
    if len(head) < 32:
        raise ValueError("%s is %d bytes; not an archive" % (path, len(head)))
    mft_offset, = struct.unpack_from("<Q", head, 0x10)
    mft_size, = struct.unpack_from("<I", head, 0x18)
    return {
        "raw": head,
        "header_size": struct.unpack_from("<I", head, 0x04)[0],
        "block_size": struct.unpack_from("<I", head, 0x08)[0],
        "crc_stored": struct.unpack_from("<I", head, HDR_CRC_OFF)[0],
        "crc_computed": binascii.crc32(head[:HDR_CRC_SPAN]) & 0xFFFFFFFF,
        "mft_offset": mft_offset,
        "mft_size": mft_size,
        "mod_flags": struct.unpack_from("<I", head, HDR_MOD_OFF)[0],
        "tier0": head[HDR_TIER0_OFF:HDR_TIER0_OFF + HDR_TIER0_LEN],
    }


def read_mft(path, header=None):
    """The whole master file table, located from a header read in this call.

    The MFT moves. Nothing here may seek to a remembered offset.
    """
    header = header or read_header(path)
    with open(path, "rb") as fh:
        fh.seek(header["mft_offset"])
        mft = fh.read(header["mft_size"])
    if len(mft) != header["mft_size"]:
        raise ValueError("MFT at 0x%X is short: %d of %d bytes"
                         % (header["mft_offset"], len(mft), header["mft_size"]))
    if mft[:4] != MFT_MAGIC:
        raise ValueError("no MFT at 0x%X: magic %r"
                         % (header["mft_offset"], mft[:4]))
    return mft


def row_bytes(mft, index):
    return mft[index * ENTRY_SIZE:(index + 1) * ENTRY_SIZE]


def row_fields(row):
    """(offset, size, extra_bytes, alloc_flags, alloc_stream, next_stream, crc)."""
    offset, size, extra, flags16, nxt, crc = struct.unpack("<QIHHII", row)
    return {"offset": offset, "size": size, "extra_bytes": extra,
            "alloc_flags": flags16 & 0xFF, "alloc_stream": (flags16 >> 8) & 0xFF,
            "next_stream": nxt, "crc": crc}


def row_count(mft):
    return len(mft) // ENTRY_SIZE


def file_id_records(path, mft, header):
    """The (file_id, row) pairs of MFT row 2, read straight off the disk.

    Deliberately not `archive.file_id_table()`: that registers a bit-31 id under
    both its raw and its masked form, which is right for lookup and wrong for an
    invariant about what the table STORES.
    """
    rec = row_fields(row_bytes(mft, FILE_ID_TABLE_ROW))
    if rec["extra_bytes"] != 0:
        raise ValueError("the file-id table declares extraBytes %d; the client "
                         "requires 0" % rec["extra_bytes"])
    with open(path, "rb") as fh:
        fh.seek(rec["offset"])
        blob = fh.read(rec["size"])
    if len(blob) != rec["size"]:
        raise ValueError("file-id table is short: %d of %d bytes"
                         % (len(blob), rec["size"]))
    out = []
    for i in range(len(blob) // FILE_ID_RECORD.size):
        out.append(FILE_ID_RECORD.unpack_from(blob, i * FILE_ID_RECORD.size))
    return out, blob


def directory_invariant(mft, records):
    """Both directions of FINDINGS 18.5's Tier 2. Returns a dict of counts.

    A record of `(0, 0)` is a RELEASED slot, not a violation -- MEASURED, 3 of
    171,025 on this machine's copies -- and is counted rather than dropped, so
    the number is visible instead of being hidden inside an exclusion.
    """
    n = row_count(mft)
    used = bytearray(n)
    first = bytearray(n)
    for i in range(n):
        flags = mft[i * ENTRY_SIZE + 0x0E]
        used[i] = flags & FLAG_ENTRY_USED
        first[i] = (flags & (FLAG_ENTRY_USED | FLAG_FIRST_STREAM)) == \
            (FLAG_ENTRY_USED | FLAG_FIRST_STREAM)
    named = set()
    released = 0
    dangling = []          # records naming a row that is missing or not USED
    for file_id, row in records:
        if file_id == 0 and row == 0:
            released += 1
            continue
        if row >= n or not used[row]:
            dangling.append((file_id, row))
        else:
            named.add(row)
    orphans = [i for i in range(FIRST_CLAIMABLE_ROW, n)
               if first[i] and i not in named]
    # Every row a LIVE row points at through alloc.nextStream. A map is two rows and
    # the archive says so only here -- no partner is ever named by the file-id table
    # (test_mapchunks: 349 partners, 0 named) -- so without this set a partner is
    # indistinguishable from a row nothing references at all, and that difference is
    # the whole of the spare-row rule below.
    chained = set()
    for i in range(n):
        if used[i]:
            nxt = struct.unpack_from("<I", mft, i * ENTRY_SIZE + 0x10)[0]
            if nxt:
                chained.add(nxt)
    unused_high = [i for i in range(FIRST_CLAIMABLE_ROW, n) if not used[i]]
    return {
        "records": len(records),
        "released_records": released,
        "first_stream_rows": sum(1 for i in range(FIRST_CLAIMABLE_ROW, n)
                                 if first[i]),
        "rows_named": len(named),
        "orphan_rows": orphans,
        "dangling_records": dangling,
        # USED clear AND something still points here: a partner or a record lost its
        # row. That is corruption. USED clear and nothing points here is a SPARE.
        "unused_referenced": [i for i in unused_high
                              if i in chained or i in named],
        "unused_spares": [i for i in unused_high
                          if i not in chained and i not in named],
    }


def row_identity(mft, records):
    """row -> {"file_ids": [...], "role": str}, for every row worth naming.

    WHY A DIFF LINE NEEDS MORE THAN A NUMBER. On 2026-08-13 `--diff` reported
    "row 71496 changed from 0 B to 6,012 B" while `deploy.py` had printed
    "installing ... head 71496, partner 71497", and the pair was read as the
    client having overwritten an authored map. It had not: 71496 is the map's
    Bloated HEAD, which `deploy` arms to zero length precisely so the client is
    forced to recompile it, and 6,012 B is that recompile working. The authored
    bytes are in the partner, 71497, which does not appear in the diff at all
    because nothing touched it. Both tools were right and the reader had two
    bare integers to tell them apart with.

    So each row this tool names now carries the two things that disambiguate it:
    the FILE ID, which survives a patch where a row index does not
    (`toolkit/contentids.py`, `studies/maprows/FINDINGS.md` §8) and which
    `deploy.py` prints on its own first line, and the ROLE, which says which
    half of a two-row map you are looking at.

    A row may carry SEVERAL file ids: `archive.file_id_table` registers a bit-31
    id under both forms for lookup, but this reads the table's raw records, so
    what comes back is what the archive actually stores -- both ids where the
    archive really stores both, and never a masked form we invented.

    Roles below index 16 are the client's own structural assignment
    (`INDEX_FIRST_FILE`); above it they are read from the flags and from
    `alloc.nextStream`, which is the only thing that names a partner -- no
    partner is ever named by the file-id table (test_mapchunks: 349 of 349).
    """
    n = row_count(mft)
    ids = {}
    for file_id, row in records:
        if file_id == 0 and row == 0:
            continue                      # a RELEASED slot, not a name
        ids.setdefault(row, []).append(file_id)

    used = bytearray(n)
    first = bytearray(n)
    for i in range(n):
        flags = mft[i * ENTRY_SIZE + 0x0E]
        used[i] = flags & FLAG_ENTRY_USED
        first[i] = (flags & (FLAG_ENTRY_USED | FLAG_FIRST_STREAM)) == \
            (FLAG_ENTRY_USED | FLAG_FIRST_STREAM)
    points_at = {}                        # partner row -> the row pointing at it
    for i in range(n):
        if used[i]:
            nxt = struct.unpack_from("<I", mft, i * ENTRY_SIZE + 0x10)[0]
            if nxt:
                points_at.setdefault(nxt, i)

    fixed = {0: "MFT descriptor", FILE_HEADER_ROW: "file header",
             FILE_ID_TABLE_ROW: "file-id table", MFT_SELF_ROW: "the MFT itself"}
    out = {}
    for i in range(n):
        if i in fixed:
            role = fixed[i]
        elif i < FIRST_CLAIMABLE_ROW:
            role = "reserved spare"
        elif not used[i]:
            role = ("USED CLEAR but row %d points here" % points_at[i]
                    if i in points_at else "free spare")
        elif first[i]:
            role = "stream head" if i in ids else "stream head, UNNAMED"
        elif i in points_at:
            role = "stream partner of row %d" % points_at[i]
        else:
            role = "used, no first-stream flag and nothing points here"
        out[i] = {"file_ids": ids.get(i, []), "role": role}
    return out


def label_row(identity, row):
    """`row_label` over a `row_identity` map, tolerant of not having one.

    Returns a bare `row N` when identity is unavailable rather than inventing
    one, because `diff()` can be handed two snapshots with no archive behind
    them and a confident label there would be a guess.
    """
    if not identity or row not in identity:
        return row_label(row)
    return row_label(row, identity[row]["file_ids"], identity[row]["role"])


# --------------------------------------------------------------- pre-flight --

def preflight(path, baseline=None):
    """Every item of FINDINGS 18.11, each its own pass/fail. Never raises for a
    finding -- a finding is a failed `Check`. It raises only when the archive
    cannot be read far enough to have findings at all.
    """
    checks = []
    size_on_disk = os.path.getsize(path)
    header = read_header(path)

    mod = header["mod_flags"]
    checks.append(Check(
        "0x1C bit 0 clear",
        not (mod & MOD_BIT_FINDINGS_18),
        "0x%08X (FINDINGS 18.8/18.11's reading of the "
        "modification-in-progress flag)" % mod))
    checks.append(Check(
        "0x1C bit 1 clear",
        not (mod & MOD_BIT_DISASSEMBLY),
        "0x%08X (FINDINGS 18.4's `test byte [esi+0x1c],2`, and "
        "studies/datwrite's reading)" % mod))

    checks.append(Check(
        "header CRC over 0x00..0x0C",
        header["crc_stored"] == header["crc_computed"],
        "stored 0x%08X computed 0x%08X" % (header["crc_stored"],
                                           header["crc_computed"])))

    mft = read_mft(path, header)
    n = row_count(mft)
    block = header["block_size"] or 512

    rows = [row_fields(row_bytes(mft, i)) for i in range(n)]
    live = [(i, r) for i, r in enumerate(rows)
            if i > 0 and (r["alloc_flags"] & FLAG_ENTRY_USED) and r["size"]]

    misaligned = [i for i, r in live if r["offset"] % block]
    checks.append(Check("every extent %d-aligned" % block, not misaligned,
                        "%d of %d live rows misaligned%s"
                        % (len(misaligned), len(live),
                           "" if not misaligned else " " + str(misaligned[:8]))))

    past = [i for i, r in live if r["offset"] + r["size"] > size_on_disk]
    checks.append(Check("every extent inside EOF", not past,
                        "%d of %d live rows run past %d bytes%s"
                        % (len(past), len(live), size_on_disk,
                           "" if not past else " " + str(past[:8]))))

    spans = sorted(((r["offset"], -(-r["size"] // block) * block, i)
                    for i, r in live))
    overlaps = []
    for a, b in zip(spans, spans[1:]):
        if a[0] + a[1] > b[0]:
            overlaps.append((a[2], b[2]))
    checks.append(Check("no overlapping reservations", not overlaps,
                        "%d overlapping pairs over %d live rows%s"
                        % (len(overlaps), len(live),
                           "" if not overlaps else " " + str(overlaps[:4]))))

    records, id_blob = file_id_records(path, mft, header)
    inv = directory_invariant(mft, records)
    checks.append(Check(
        "every USED|FIRST row >= 16 is named", not inv["orphan_rows"],
        "%d orphan(s) of %d USED|FIRST rows%s"
        % (len(inv["orphan_rows"]), inv["first_stream_rows"],
           "" if not inv["orphan_rows"] else " " + str(inv["orphan_rows"][:8]))))
    checks.append(Check(
        "every file-id record names a USED row", not inv["dangling_records"],
        "%d dangling of %d records (%d released (0,0))"
        % (len(inv["dangling_records"]), inv["records"],
           inv["released_records"])))

    # Rows 0..15. Structurally, and byte-exactly when a baseline is supplied.
    reserved_problems = []
    desc = row_bytes(mft, 0)
    if desc[:4] != MFT_MAGIC:
        reserved_problems.append("row 0 magic %r" % desc[:4])
    if struct.unpack_from("<I", desc, DESCRIPTOR_COUNT_OFF)[0] != n:
        reserved_problems.append(
            "row 0 count %d != %d rows"
            % (struct.unpack_from("<I", desc, DESCRIPTOR_COUNT_OFF)[0], n))
    hdr_row = rows[FILE_HEADER_ROW]
    if hdr_row["offset"] != 0 or hdr_row["size"] != FILE_HEADER_SIZE:
        reserved_problems.append("row 1 is not (offset 0, size 32)")
    mft_row = rows[MFT_SELF_ROW]
    if (mft_row["offset"] != header["mft_offset"]
            or mft_row["size"] != header["mft_size"]):
        reserved_problems.append("row 3 does not describe the MFT the header names")
    for i in (FILE_HEADER_ROW, FILE_ID_TABLE_ROW, MFT_SELF_ROW):
        if not rows[i]["alloc_flags"] & FLAG_ENTRY_USED:
            reserved_problems.append("row %d is not USED" % i)
    nonzero = [i for i in range(4, FIRST_CLAIMABLE_ROW)
               if row_bytes(mft, i) != b"\x00" * ENTRY_SIZE]
    if nonzero:
        reserved_problems.append("rows %s are not all-zero" % nonzero)
    checks.append(Check("no row below index 16 touched", not reserved_problems,
                        "; ".join(reserved_problems) or
                        "descriptor, header row, id table, MFT row and 12 "
                        "all-zero spares as the client requires"))

    # A USED-CLEAR ROW IS ONLY A FAULT IF SOMETHING STILL POINTS AT IT.
    #
    # This item used to refuse ANY row >= 16 with USED clear, and CORRECTED
    # 2026-08-13 because it refuses ArenaNet's own shipped archive: `C:\gw\Gw.dat`,
    # the owner's install, untouched by anything here and opened by the retail client
    # every day, carries exactly one -- row 35301 -- and pre-flight called it
    # REFUSE, 9 of 10. So the rule was stricter than the client's, which is the one
    # direction a pre-flight gate must not be: a gate that reddens on the real target
    # stops the tool running at all.
    #
    # It is not even an anomaly, it is the mechanism: `datplan.FIRST_CLAIMABLE_ROW`
    # already records that when the client needed a free slot it TOOK row 35301,
    # reaching past twelve nearer ones. A spare row is what the allocator consumes.
    # `vault/dat_study/Gw.dat` has zero of them and passes 10 of 10, so the two
    # copies differ by exactly this row and neither is broken.
    #
    # What the item still catches is what its own sabotage in `test_datcheck` builds:
    # a row that something REFERENCES losing its USED flag. A partner is reachable
    # only through `alloc.nextStream` and is never named by the file-id table, so
    # "the file-id record check would have caught it" is false -- it would not, and
    # that is why this item exists at all.
    referenced = inv["unused_referenced"]
    spares = inv["unused_spares"]
    checks.append(Check(
        "no USED-clear row that something points at", not referenced,
        "%d referenced row(s) lost USED%s; %d unreferenced spare(s)%s"
        % (len(referenced),
           "" if not referenced else " " + str(referenced[:8]),
           len(spares),
           "" if not spares else " " + str(spares[:8])
           + " -- normal, the client's allocator claims these")))

    if baseline is not None:
        base_mft = _snapshot_mft(baseline)
        # Rows 0, 2 and 3 are the archive's own containers -- the descriptor
        # (whose +0x04 counter increments on every flush), the file-id table and
        # the MFT -- and they change on ANY write, ours included: `datwrite.py`
        # rewrites row 3's self-crc after every `--replace`. Comparing them
        # exactly would make this item red after every legitimate write, which
        # is how a gate gets ignored. They are reported beside the verdict
        # instead, the same separation FINDINGS 18.5's Tier 1 makes.
        compared = [i for i in range(FIRST_CLAIMABLE_ROW)
                    if i not in CORROBORATION_ROWS]
        changed = [i for i in compared
                   if row_bytes(base_mft, i) != row_bytes(mft, i)]
        moved_containers = [i for i in CORROBORATION_ROWS
                            if row_bytes(base_mft, i) != row_bytes(mft, i)]
        checks.append(Check(
            "reserved rows 1, 4..15 identical to the baseline",
            not changed,
            "rows changed: %s (containers 0/2/3 changed: %s -- expected after "
            "any write)" % (changed or "none", moved_containers or "none")))

    return checks, {"header": header, "rows": n, "invariant": inv,
                    "file_id_sha256": hashlib.sha256(id_blob).hexdigest(),
                    "size_on_disk": size_on_disk}


# ----------------------------------------------------------------- snapshot --

def scan(path):
    """(header, mft, records, id_blob) -- every raw structure, read ONCE.

    Extracted 2026-08-14 because `diff()` needs the file-id RECORDS to label its
    rows and `snapshot()` had already parsed them in the same call.

    WHAT LABELLING COSTS, MEASURED on `vault/dat_study/Gw.dat` (4.2 GB, 177,342
    rows), best of two runs each, `tracemalloc` peak:

        1.51 s /  36.9 MB   no labels at all (the pre-2026-08-13 diff)
        3.77 s / 117.3 MB   labels, re-reading and re-parsing the id table
        3.06 s / 121.4 MB   labels, sharing this one scan

    So the duplicate read was ~0.7 s of the 2.3 s and this removes it. The rest
    is `row_identity` itself, and the memory is nearly all of it: a dict of
    177,342 dicts. Both are RECORDED rather than optimised away, because `--diff`
    is the verb run around a timed client session and the next person to wonder
    should find a number instead of a shrug. Making the identity map lazy would
    buy the memory back and is not worth doing until something needs it.
    """
    header = read_header(path)
    mft = read_mft(path, header)
    records, id_blob = file_id_records(path, mft, header)
    return header, mft, records, id_blob


def snapshot(path, scanned=None):
    """Tier 0 + Tier 1 + Tier 2, with the header read before the MFT.

    `scanned` is a `scan()` result a caller already paid for. It is never a
    DIFFERENT archive's -- `diff()` is the only caller that passes one and it
    passes the one it just took from `path`.
    """
    header, mft, records, id_blob = scanned if scanned else scan(path)
    inv = directory_invariant(mft, records)
    desc = row_bytes(mft, 0)
    return {
        "snapshot_version": SNAPSHOT_VERSION,
        "dat": os.path.abspath(path),
        "size_on_disk": os.path.getsize(path),
        "tier0": {
            "header_0x10_0x20": header["tier0"].hex(),
            "mft_offset": header["mft_offset"],
            "mft_size": header["mft_size"],
            "header_flags_0x1C": header["mod_flags"],
            "descriptor_counter": struct.unpack_from(
                "<I", desc, DESCRIPTOR_COUNTER_OFF)[0],
            "descriptor_count": struct.unpack_from(
                "<I", desc, DESCRIPTOR_COUNT_OFF)[0],
        },
        "tier1": {
            "rows": row_count(mft),
            "encoding": "zlib+base64",
            "mft": base64.b64encode(zlib.compress(mft, 6)).decode("ascii"),
            "mft_sha256": hashlib.sha256(mft).hexdigest(),
        },
        "tier2": {
            "records": inv["records"],
            "released_records": inv["released_records"],
            "first_stream_rows": inv["first_stream_rows"],
            "rows_named": inv["rows_named"],
            "orphan_rows": inv["orphan_rows"][:64],
            "orphan_count": len(inv["orphan_rows"]),
            "dangling_count": len(inv["dangling_records"]),
            "file_id_sha256": hashlib.sha256(id_blob).hexdigest(),
        },
    }


def write_snapshot(path, out_path):
    snap = snapshot(path)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(snap, fh, indent=1)
    return snap


def load_snapshot(out_path):
    with open(out_path, "r", encoding="utf-8") as fh:
        snap = json.load(fh)
    if snap.get("snapshot_version") != SNAPSHOT_VERSION:
        raise ValueError("snapshot version %r; this tool writes %d"
                         % (snap.get("snapshot_version"), SNAPSHOT_VERSION))
    return snap


def _snapshot_mft(snap):
    mft = zlib.decompress(base64.b64decode(snap["tier1"]["mft"]))
    if hashlib.sha256(mft).hexdigest() != snap["tier1"]["mft_sha256"]:
        raise ValueError("snapshot MFT does not match its own digest")
    return mft


# --------------------------------------------------------------------- diff --

RELOCATED = "new extent (silent relocation)"
RECYCLED = "row recycled"
DELETED = "deleted"
RELINKED = "sibling relinked"
UNCLASSIFIED = "changed, unclassified"
ADDED = "row added"
REMOVED = "row removed"

_ZERO_ROW = b"\x00" * ENTRY_SIZE
CORROBORATION_ROWS = (0, FILE_ID_TABLE_ROW, MFT_SELF_ROW)


def classify_row(before, after):
    """FINDINGS 18.5's Tier 1 table, in the order the shapes exclude each other.

    Never returns None for a changed row. A shape the table does not name is
    `UNCLASSIFIED` and is reported -- dropping it is how a relocation gets
    called a no-op.
    """
    if before == after:
        return None
    if after == _ZERO_ROW:
        return DELETED
    identity_changed = before[0x0E:0x10] != after[0x0E:0x10]
    if identity_changed:
        return RECYCLED
    link_changed = before[0x10:0x14] != after[0x10:0x14]
    extent_changed = (before[0x00:0x0E] != after[0x00:0x0E]
                      or before[0x14:0x18] != after[0x14:0x18])
    if link_changed and not extent_changed:
        return RELINKED
    if extent_changed and not link_changed:
        return RELOCATED
    return UNCLASSIFIED


def diff(before, path=None, after=None):
    """Compare a live archive (or a second snapshot) against a snapshot.

    Returns a dict. `changes` is one record per changed row, classified; rows 0,
    2 and 3 change on any flush and are separated out as corroboration rather
    than counted as findings.

    Every changed row is labelled by `row_identity` when `path` is given -- read
    from the LIVE archive rather than from the snapshot, because a snapshot
    carries only a digest of the file-id table and not its pairs. Comparing two
    snapshots is still allowed and still works; it reports `identified: False`
    and the formatter says so, rather than printing a row number that looks
    identified and is not.

    AND THE LABELS ARE GATED ON THE ARCHIVE BEING THE ONE `after` DESCRIBES.
    The sentence above was false for one parameter combination when it was
    written: `diff(before, path=X, after=<snapshot of Y>)` took its ROWS from Y
    and its IDENTITY from X and reported `identified: True`. MEASURED 2026-08-14
    with X = `vault/dat_study` and Y = `vault/client/2026-04-30_b174de1f2d8d`:
    **308 of 315 changed rows carried a label naming a file the after-image does
    not hold** -- row 3721 labelled `file id 0x5EE9A, 0x2D459` where the
    after-image's own table says `0x2D451, 0x5E503`. Guarded, the same call now
    reports `identified: False` and 0 labels carry a file id at all.
    No shipped caller reaches it -- `_main` never passes `after` -- which
    is exactly why it survived review: it is a latent trap in a public function,
    and it is the precise failure `row_label`'s own docstring exists to prevent.
    The gate is the MFT ITSELF, byte for byte, not a comparison of path strings:
    a stale snapshot of the very same path is the same defect wearing the right
    name, and the archive is the only thing that can refute it.
    """
    scanned = None
    if after is None:
        scanned = scan(path)
        after = snapshot(path, scanned)
    b_mft = _snapshot_mft(before)
    a_mft = _snapshot_mft(after)
    nb, na = row_count(b_mft), row_count(a_mft)

    identity = None
    identity_note = None
    if path is not None:
        if scanned is None:
            scanned = scan(path)
        _hdr, live_mft, records, _blob = scanned
        if bytes(live_mft) == bytes(a_mft):
            identity = row_identity(live_mft, records)
        else:
            identity_note = (
                "the archive at %s is NOT the one `after` describes -- its MFT "
                "differs (%d rows on disk, %d in the snapshot) -- so no row "
                "below carries a file id or a role. Labelling from the wrong "
                "archive is worse than a bare number: it reads as "
                "identification." % (path, row_count(live_mft), na))

    tier0 = {}
    for key in ("mft_offset", "mft_size", "header_flags_0x1C",
                "descriptor_counter", "descriptor_count"):
        bv, av = before["tier0"][key], after["tier0"][key]
        if bv != av:
            tier0[key] = {"before": bv, "after": av}

    changes, corroboration = [], []
    for i in range(min(nb, na)):
        rb, ra = row_bytes(b_mft, i), row_bytes(a_mft, i)
        kind = classify_row(rb, ra)
        if kind is None:
            continue
        rec = {"row": i, "kind": kind, "label": label_row(identity, i),
               "before": row_fields(rb), "after": row_fields(ra),
               "before_hex": rb.hex(), "after_hex": ra.hex()}
        (corroboration if i in CORROBORATION_ROWS else changes).append(rec)
    for i in range(na, nb):
        # A REMOVED row is gone from the after-image, so it has no identity
        # there. Labelling it from the before-image would be the one place this
        # could print a file id that no longer resolves.
        changes.append({"row": i, "kind": REMOVED, "label": row_label(i),
                        "before": row_fields(row_bytes(b_mft, i)), "after": None,
                        "before_hex": row_bytes(b_mft, i).hex(), "after_hex": None})
    for i in range(nb, na):
        changes.append({"row": i, "kind": ADDED, "label": label_row(identity, i),
                        "before": None,
                        "after": row_fields(row_bytes(a_mft, i)),
                        "before_hex": None, "after_hex": row_bytes(a_mft, i).hex()})

    counts = {}
    for rec in changes:
        counts[rec["kind"]] = counts.get(rec["kind"], 0) + 1

    tier2 = {}
    for key in ("records", "released_records", "first_stream_rows", "rows_named",
                "orphan_count", "dangling_count", "file_id_sha256"):
        bv, av = before["tier2"][key], after["tier2"][key]
        if bv != av:
            tier2[key] = {"before": bv, "after": av}

    return {
        "before": before.get("dat"), "after": after.get("dat"),
        "rows_before": nb, "rows_after": na,
        "identified": identity is not None,
        "identity_note": identity_note,
        "tier0": tier0, "tier2": tier2,
        "changes": changes, "counts": counts,
        "corroboration": corroboration,
        # `unchanged` means the table is byte for byte what it was, and rows 0,
        # 2 and 3 count towards that. They are separated out of `changes`
        # because they move on ANY flush and a post-flight that reported them as
        # findings would report three every time -- but "the client flushed" is
        # itself a fact about the run, so it may not be rounded down to nothing.
        "unchanged": not (tier0 or tier2 or changes or corroboration),
    }


def format_diff(d):
    out = []
    out.append("rows %d -> %d" % (d["rows_before"], d["rows_after"]))
    out.append("(%s)" % ROW_CONVENTION)
    if not d.get("identified"):
        out.append("NOT IDENTIFIED: %s Match these numbers against another "
                   "tool's with care."
                   % (d.get("identity_note")
                      or "two snapshots were compared with no archive behind "
                         "them, so no row below carries its file id or role."))
    if d["tier0"]:
        out.append("TIER 0 changed:")
        for k, v in sorted(d["tier0"].items()):
            out.append("   %-20s %r -> %r" % (k, v["before"], v["after"]))
    else:
        out.append("TIER 0 unchanged (mftOffset alone is not a change signal; "
                   "the descriptor counter is)")
    if not d["changes"]:
        out.append("TIER 1: no row outside 0/2/3 changed")
    else:
        out.append("TIER 1: %d changed row(s) %s"
                   % (len(d["changes"]), d["counts"]))
        for rec in d["changes"][:40]:
            out.append("   %s" % rec.get("label", row_label(rec["row"])))
            out.append("      %s" % rec["kind"])
            if rec["before"] and rec["after"]:
                out.append("      before 0x%X %dB extra=%d flags=%d/%d next=%d "
                           "crc=0x%08X"
                           % (rec["before"]["offset"], rec["before"]["size"],
                              rec["before"]["extra_bytes"],
                              rec["before"]["alloc_flags"],
                              rec["before"]["alloc_stream"],
                              rec["before"]["next_stream"], rec["before"]["crc"]))
                out.append("      after  0x%X %dB extra=%d flags=%d/%d next=%d "
                           "crc=0x%08X"
                           % (rec["after"]["offset"], rec["after"]["size"],
                              rec["after"]["extra_bytes"],
                              rec["after"]["alloc_flags"],
                              rec["after"]["alloc_stream"],
                              rec["after"]["next_stream"], rec["after"]["crc"]))
        if len(d["changes"]) > 40:
            out.append("   ... %d more" % (len(d["changes"]) - 40))
    if d["corroboration"]:
        out.append("corroboration only (rows 0/2/3 change on any flush):")
        for r in d["corroboration"]:
            out.append("   %s" % r.get("label", row_label(r["row"])))
    if d["tier2"]:
        out.append("TIER 2 changed:")
        for k, v in sorted(d["tier2"].items()):
            out.append("   %-20s %r -> %r" % (k, v["before"], v["after"]))
    else:
        out.append("TIER 2 unchanged (the directory invariant, both ways)")
    out.append("")
    out.append("REMINDER: the entry CRC, the MFT self-CRC and the header CRC "
               "all still verify across a relocation. They are not detectors.")
    return "\n".join(out)


# ---------------------------------------------------------------------- CLI --

def main(argv=None):
    """Exit 0 clear / 1 a finding / 2 the run could not be made.

    The three are kept apart on purpose. `--diff` exits 1 to mean "the archive
    changed", which is a RESULT, and an unreadable archive exiting 1 as well
    would be reported as that result by anything reading the code -- so an
    archive this tool cannot read far enough to have findings about exits 2 with
    one line, rather than raising an exit-1 traceback.
    """
    try:
        return _main(argv)
    except (ValueError, OSError, KeyError, struct.error) as exc:
        print("CANNOT RUN: %s: %s" % (type(exc).__name__, exc), file=sys.stderr)
        print("  This is not a finding. The archive could not be read far "
              "enough to have findings.", file=sys.stderr)
        return 2


def _main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dat", required=True, help="the archive to read ('rb')")
    ap.add_argument("--preflight", action="store_true",
                    help="every open-time rule the client itself applies")
    ap.add_argument("--baseline", help="a snapshot; adds an exact rows-0..15 check")
    ap.add_argument("--snapshot", metavar="FILE", help="write a snapshot here")
    ap.add_argument("--diff", metavar="BEFORE",
                    help="compare --dat against this snapshot")
    ap.add_argument("--json", metavar="FILE", help="also write the result as JSON")
    args = ap.parse_args(argv)

    if not (args.preflight or args.snapshot or args.diff):
        ap.error("nothing to do: pass --preflight, --snapshot or --diff")

    rc = 0
    payload = {}

    if args.preflight:
        baseline = load_snapshot(args.baseline) if args.baseline else None
        checks, facts = preflight(args.dat, baseline=baseline)
        print("pre-flight: %s" % args.dat)
        print("  %d rows, %d bytes on disk, MFT at 0x%X"
              % (facts["rows"], facts["size_on_disk"],
                 facts["header"]["mft_offset"]))
        print("  %s" % ROW_CONVENTION)
        for c in checks:
            print("  " + c.line())
        bad = [c for c in checks if not c.ok]
        print("  %d of %d clear" % (len(checks) - len(bad), len(checks)))
        if bad:
            print("  REFUSE: %s" % ", ".join(c.name for c in bad))
            rc = 1
        payload["preflight"] = [c.to_json() for c in checks]

    if args.snapshot:
        snap = write_snapshot(args.dat, args.snapshot)
        print("snapshot -> %s" % args.snapshot)
        print("  rows %d, descriptor counter %d, MFT sha256 %s"
              % (snap["tier1"]["rows"], snap["tier0"]["descriptor_counter"],
                 snap["tier1"]["mft_sha256"][:16]))
        payload["snapshot"] = args.snapshot

    if args.diff:
        d = diff(load_snapshot(args.diff), path=args.dat)
        print(format_diff(d))
        payload["diff"] = dict(d)      # changes AND corroboration, whole
        if not d["unchanged"]:
            rc = max(rc, 1)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        print("json -> %s" % args.json)
    return rc


if __name__ == "__main__":
    sys.exit(main())
