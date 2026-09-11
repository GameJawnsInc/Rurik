"""Reading bytes out of an archive -- the MFT, the header, row identity, the CRC
sweep and the generation counters.

Everything in this module answers a question about what is ON DISK and returns a
fact: a header dict, a row's fields, the directory invariant's counts, the list
of surviving MFT generations, a payload-CRC sweep's findings. There is no
`Check` here and none of the refusal vocabulary -- `datcheck.py` is what turns
these facts into pass/fail items, into `--diff` output and into the launch gate,
and it re-exports every name below, so `datcheck.read_header`,
`datcheck.row_bytes` and `datcheck.row_identity` still resolve for `overlay.py`,
`abrun.py`, `datalloc.py`, `test_archive.py` and `test_datcheck.py`, which read
them off that module.

POINTERS FOR THE COMMENTS BELOW, whose referents stayed in `datcheck.py` and
which are reproduced here word for word rather than reworded. The import
comment's `assert_archive_safe` and `preflight` are both there; so is
`generation_checks`, the `Check` wrapper around `generations()`; and so are the
two verbs the ROW NUMBERS paragraph ends on -- `--preflight` and `--diff` print
`ROW_CONVENTION`, imported from here, above their numbers. "This module" in that
import comment's last sentence was written of `datcheck.py`, which is the file
`datwrite.py` names in prose; there is no cycle from here either, because
`datwrite.py` imports neither of us.

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
"""

import binascii
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import (ENTRY_SIZE, MFT_MAGIC, MFT_ROW_OF_ENTRIES_0,  # noqa: E402
                     row_label, FILE_HEADER_ROW, FILE_ID_TABLE_ROW,
                     MFT_SELF_ROW, FIRST_CLAIMABLE_ROW,
                     FLAG_ENTRY_USED, FLAG_FIRST_STREAM)
# THE MFT SELF-CRC FORMULA LIVES IN `datwrite.py` AND IS NOT COPIED HERE.
# `assert_archive_safe` needs it -- the pre-flight has never checked it, which is
# exactly the hole `datwrite.py:1462-1501` documents (a stale self-crc leaves
# `--preflight` reporting 10 of 10 while the archive fails its own checksum) --
# and a second expression of "the table with row 3's own 24 bytes skipped" is how
# two readers of one field drift apart. Importing the writer opens nothing:
# `datwrite` only ever opens a file inside `Writer`, and its module chain
# (`archive`, `datdecl`, `datjournal`, `gwdat`) is the one this file already
# has plus two leaves `datwrite` itself owns. There is no cycle --
# `datwrite.py` names this module in prose only.
import datwrite  # noqa: E402

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

DESCRIPTOR_COUNTER_OFF = 0x04    # the u32 the flush increments
DESCRIPTOR_COUNT_OFF = 0x0C

# ScanMft reads the file in 1 MiB blocks (the buffer alloc at 0x0047B818, with
# its own `!(bufferSize % blockSize)` assert, ExeArchive:2592). We match the
# size because it is the client's, not because anything depends on it.
GENERATION_SCAN_CHUNK = 1 << 20

# Rows whose stored CRC is not a CRC over a payload: row 1 is the file header's
# own row, row 3 describes the MFT. `build_archive` writes 0 for both, and the
# real archive's are structural too. Excluded BY NAME so the count of exceptions
# is itself assertable -- an unnamed skip is how a sweep quietly measures less
# than it claims.
CRC_STRUCTURAL_ROWS = (1, 3)

# FILE_HEADER_ROW, FILE_ID_TABLE_ROW, MFT_SELF_ROW and FIRST_CLAIMABLE_ROW are
# imported from `archive.py` above rather than restated here. They used to be
# declared in three modules, and `datplan.py`'s copy was then used with the wrong
# arithmetic for months -- see the MFT ROW NUMBERS block in archive.py.
# FLAG_ENTRY_USED and FLAG_FIRST_STREAM are imported from `archive.py` here too,
# which finally closes the private copy that comment is complaining about --
# this module is where `datcheck.py`'s copy of the two used to be declared.
FILE_HEADER_SIZE = 0x20

FILE_ID_RECORD = struct.Struct("<II")


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


# -------------------------------------------------------------- generations --

def generations(path, block=None):
    """Every surviving MFT generation in the file, newest first.

    WHY THIS EXISTS, and it is the one pre-flight question nothing else asks.
    The client's repair (ExeArchive ScanMft) does NOT rebuild an MFT. It reads
    the whole file at `blockSize` stride hunting the descriptor magic, hands
    each hit to LoadMft, and adopts the candidate whose +0x04 flush counter is
    strictly highest. **If no candidate validates it returns 0, and that zero
    funnels into ArchiveCreate, which writes a fresh empty archive over yours.**
    So "is a botched write recoverable" is a countable fact about the file: how
    many older generations are there to fall back to? Before 2026-08-17 nothing
    in this repo could answer it, and the answer for `dat_study` turned out to
    be six. studies/archivewrite/FINDINGS.md 5.4.

    THIS IS AN UPPER BOUND, and saying so is the whole honesty of the check.
    It applies ScanMft's *shape* gate -- magic, +0x08 == 0, count >= 16, extent
    inside EOF -- and NOT LoadMft's full validation (self-CRC, every offset
    aligned and in range, every nextStream in [16,count) and acyclic). A
    candidate counted here may still be rejected by the client. A count of 1 is
    therefore a hard finding; a count of 6 is an encouraging one.

    The rows a generation declares are also the reason `datplan`/`datalloc` may
    not allocate into the tail: a writer that overwrites the shadow rotation
    region destroys the client's own recovery material.
    """
    size = os.path.getsize(path)
    header = read_header(path)
    block = block or header["block_size"] or 512
    live = header["mft_offset"]
    found = []
    with open(path, "rb") as fh:
        pos = 0
        while True:
            buf = fh.read(GENERATION_SCAN_CHUNK)
            if not buf:
                break
            for off in range(0, len(buf) - ENTRY_SIZE + 1, block):
                if buf[off:off + 4] != MFT_MAGIC:
                    continue
                counter, zero, count = struct.unpack_from(
                    "<III", buf, off + DESCRIPTOR_COUNTER_OFF)
                at = pos + off
                found.append({
                    "offset": at,
                    "counter": counter,
                    "rows": count,
                    "live": at == live,
                    # ScanMft's own acceptance shape, and nothing more.
                    "shape_ok": (zero == 0 and count >= 16
                                 and at + count * ENTRY_SIZE <= size),
                    "reserved_bytes": count * ENTRY_SIZE,
                })
            pos += len(buf)
    found.sort(key=lambda g: -g["counter"])
    return found


# --------------------------------------------------------------- crc sweep --

def crc_sweep(path, limit=None):
    """Every USED row's payload CRC, recomputed from the bytes on disk.

    WHAT THIS CATCHES THAT THE PRE-FLIGHT CANNOT, and it is why it is worth a
    whole-file read. The client's repair phase 2 (ScanFiles) CRCs every payload
    and, on a mismatch, walks the nextStream chain back to its FLAG_FIRST_STREAM
    head and DELETES THE WHOLE CHAIN -- extents freed, MFT rows memset, file-id
    record dropped. So one stale CRC costs an entire file, and it costs it the
    moment repair fires **for an unrelated reason**. A stale CRC is silent until
    then: all ten open-time rules pass, because none of them reads a payload.

    It is also the only check that can see studies/archivewrite's C-6. Relocate
    a compression-8 row with `datmove` and the row is marked stored while its
    bytes are still compressed; the CRC is over the stored bytes and does not
    move, so every checksum rule and every open-time rule still passes and the
    file is simply unreadable. This sweep does not catch that by CRC either --
    it catches it by reporting the compression code beside the row, which is the
    only place in this module that has ever looked at one.

    Cost is a full read. Measured 2,487 MB/s on this machine, so ~3 s for 4.2 GB.
    """
    header = read_header(path)
    mft = read_mft(path, header)
    n = row_count(mft)
    size = os.path.getsize(path)
    bad, checked, skipped = [], 0, []
    with open(path, "rb") as fh:
        for i in range(n):
            if limit is not None and checked >= limit:
                break
            r = row_fields(row_bytes(mft, i))
            if not (r["alloc_flags"] & FLAG_ENTRY_USED) or not r["size"]:
                continue
            if i in CRC_STRUCTURAL_ROWS:
                # Row 1 is the file header's own row and row 3 describes the
                # MFT; their stored CRCs are not payload CRCs and comparing
                # them would make this check permanently red. Named, not
                # silently skipped -- a skip nobody prints is a check nobody has.
                skipped.append(i)
                continue
            if r["offset"] + r["size"] > size:
                bad.append((i, r, None, "extent past EOF"))
                continue
            fh.seek(r["offset"])
            got = binascii.crc32(fh.read(r["size"])) & 0xFFFFFFFF
            checked += 1
            if got != r["crc"]:
                bad.append((i, r, got, "stored 0x%08X computed 0x%08X"
                            % (r["crc"], got)))
    return {"rows": n, "checked": checked, "skipped": skipped,
            "bad": bad, "size_on_disk": size}


# -------------------------------------------------------------- self-crc --

def self_crc_state(path, header=None, mft=None):
    """(stored, computed) for row 3's own crc -- the MFT's self-checksum.

    THE ONE CHECK `preflight()` DOES NOT MAKE, and the one whose absence is
    written up as a real defect shape rather than a theoretical one: a `Writer`
    that grows a row without `resync()` computes the self-crc over the stale
    pre-growth extent, prints a confident `fixed` line, and leaves an archive
    that fails its own checksum while `--preflight` still answers 10 of 10
    (`datwrite.py:755-781`). Only `datwrite --verify` has ever looked, and
    `--verify` is not a thing anyone runs before a launch.

    The formula is `datwrite.mft_self_crc`, imported. See the import comment.
    """
    header = header or read_header(path)
    mft = read_mft(path, header) if mft is None else mft
    n = row_count(mft)
    stored = struct.unpack_from(
        "<I", mft, MFT_SELF_ROW * ENTRY_SIZE + datwrite.ENTRY_CRC)[0]
    return stored, datwrite.mft_self_crc(mft, n)
