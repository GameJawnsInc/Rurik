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

WHAT THE SNAPSHOT HOLDS: that paragraph moved to `datsnapshot.py`'s docstring,
with the three tiers themselves -- `snapshot`, `diff` and the page they print.

    python toolkit/mapdata/datcheck.py --dat DAT --preflight
    python toolkit/mapdata/datcheck.py --dat DAT --snapshot before.json
    python toolkit/mapdata/datcheck.py --dat DAT --diff before.json

AND THE LAUNCH GATE, which is the pre-flight with the two rules it never made.
`assert_archive_safe` is `cage.assert_launch_safe`'s counterpart for the data
side: the cage decides from a binary's bytes whether it may be aimed at a given
server, this decides from an archive's bytes whether a client may open it at
all. It adds the MFT self-crc -- which `preflight()` has never checked, so an
archive failing its own checksum reports 10 of 10 clear -- and the payload CRC
sweep, and it refuses rather than reporting, because the failure modes here are
a silent 4.2 GB rebuild and a whole-chain delete. Every launch site calls it
itself; see the docstring for why that is not redundancy.

    python toolkit/mapdata/datcheck.py --dat DAT --assert-safe
    python toolkit/mapdata/datcheck.py --dat DAT --assert-safe --fingerprints F
    python toolkit/mapdata/datcheck.py --dat DAT --assert-safe --fingerprints F \
                                       --side retail_rows

An `overlay.py` record holds BOTH sides of a profile, so `--side` says which one
the archive in front of you is supposed to match (default `rows`, the profile's
own). A side that is missing or empty REFUSES; it never falls through to the
other one, because that is how a check written to ask "is my overlay deployed"
came back clear on an archive carrying none of it. The record's own three trust
checks -- its digest, its manifest sha and its retail stamp -- are run first, by
`overlay.py`'s own code, so a record `overlay.py --status` will not open cannot
clear this gate either.

ROW NUMBERS, AND WHY EVERY ONE PRINTED HERE CARRIES ITS FILE ID: that paragraph
moved to `datread.py`'s docstring, with `row_identity` and `ROW_CONVENTION`
themselves and with the 71496/71497 afternoon it was written about. The
convention is the raw MFT index -- row 0 the descriptor, 16 the client's
`INDEX_FIRST_FILE` -- both verbs below print `ROW_CONVENTION` above their
numbers, and the numbers in the paragraph after this one are in it.

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
from archive import (Archive, ENTRY_SIZE, MFT_MAGIC, FILE_MAGIC,  # noqa: E402
                     MFT_ROW_OF_ENTRIES_0, row_label,
                     FILE_HEADER_ROW, FILE_ID_TABLE_ROW, MFT_SELF_ROW,
                     FIRST_CLAIMABLE_ROW)
# THE CONSTANTS THAT DESCRIBE AN ARCHIVE'S BYTES MOVED TO `datread.py`, with the
# readers that use them: ROW_CONVENTION, the header offsets, the MFT
# descriptor's two counters, the generation scan chunk, the structural CRC rows,
# the two `alloc.flags` bits and the file-id record struct. `import datwrite` and
# its ten-line comment went with them -- its one code site in this file was
# `self_crc_state`. Re-exported rather than re-declared, because `preflight`,
# `scan` and `assert_archive_safe` below read FLAG_ENTRY_USED,
# DESCRIPTOR_COUNT_OFF and FILE_HEADER_SIZE by bare name, `format_diff` and
# `_main` print ROW_CONVENTION, and `test_datcheck.py` reads
# `datcheck.CRC_STRUCTURAL_ROWS` off this module.
# THAT READER LIST WAS C1'S, AND C2 MOVED TWO OF THE NAMES OUT FROM UNDER
# IT: `scan` and `format_diff` are in `datsnapshot.py` now and import these
# names from `datread.py` themselves. The sentence above is left standing
# rather than reworded. MEASURED off this file's syntax tree after C2: the
# three constants named are read by bare name in `preflight` only, and
# ROW_CONVENTION is printed by `_main` only. DESCRIPTOR_COUNTER_OFF has no
# bare-name reader left in this file at all -- it stays on the list below
# because dropping a re-export drops an attribute from this module, which
# is a behaviour change and not a tidy-up.
from datread import (ROW_CONVENTION, HDR_CRC_SPAN, HDR_CRC_OFF,  # noqa: F401,E402
                     HDR_TIER0_OFF, HDR_TIER0_LEN, HDR_MOD_OFF,
                     DESCRIPTOR_COUNTER_OFF, DESCRIPTOR_COUNT_OFF,
                     GENERATION_SCAN_CHUNK, CRC_STRUCTURAL_ROWS,
                     FLAG_ENTRY_USED, FLAG_FIRST_STREAM, FILE_HEADER_SIZE,
                     FILE_ID_RECORD)

# `SNAPSHOT_VERSION` moved to `datsnapshot.py`, with the three tiers it stamps
# and the loader that refuses a snapshot some other version of them wrote. It is
# re-exported below, at the site the snapshot verbs were cut from.

# Contested between our own documents. See the docstring.
MOD_BIT_FINDINGS_18 = 0x1    # FINDINGS 18.8 / 18.11
MOD_BIT_DISASSEMBLY = 0x2    # FINDINGS 18.4's `test byte [esi+0x1c],2`


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


# THE READERS ARE `datread.py` NOW -- everything that opens the archive and
# returns a fact, plus the payload CRC sweep and the generation census.
# Re-exported because `preflight`, `generation_checks`, `assert_archive_safe`,
# `scan`, `snapshot`, `diff`, `format_diff` and `_main` below all call them by
# bare name, and because `overlay.py`, `abrun.py`, `datalloc.py`,
# `test_archive.py` and `test_datcheck.py` read them off this module as
# `datcheck.<name>`.
# SAME CORRECTION AS THE SHIM ABOVE, for the same reason: of the callers
# that sentence names, `scan`, `snapshot`, `diff` and `format_diff` left for
# `datsnapshot.py` in C2 and take these readers from `datread.py` directly.
# MEASURED after C2, the callers still reading them by bare name here are
# `preflight`, `generation_checks`, `assert_archive_safe` and `_main`.
from datread import (read_header, read_mft, row_bytes,  # noqa: F401,E402
                     row_fields, row_count, file_id_records,
                     directory_invariant, row_identity, label_row,
                     generations, crc_sweep, self_crc_state)


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

    # THE GENERATION CENSUS IS DELIBERATELY NOT HERE, and it was here for one
    # test run on 2026-08-17 before the fixtures refuted it. Two reasons, both
    # of which say the same thing from different directions:
    #
    #   1. "Has a fallback generation" is a property of an archive's HISTORY,
    #      not of its validity. `build_archive` writes one MFT and is perfectly
    #      healthy; so is any freshly cut copy. Adding the item turned every
    #      synthetic fixture red and broke nine "nothing ELSE goes red"
    #      isolation checks in test_datcheck alone -- which is the fixtures
    #      correctly reporting that the item does not belong in this function.
    #   2. This pre-flight costs 1.7 s on the real 4.2 GB archive BECAUSE it
    #      never reads a payload. The generation scan reads the whole file. The
    #      operating rule that earns this tool its place -- run it before every
    #      single launch, there is no cost argument -- is worth more than
    #      folding one more item in, and a check people skip is a check that
    #      does not exist.
    #
    # `--generations` is its own verb, run before an archive is RISKED rather
    # than before it is opened. studies/archivewrite/FINDINGS.md 5.4/5.6.
    return checks, {"header": header, "rows": n, "invariant": inv,
                    "file_id_sha256": hashlib.sha256(id_blob).hexdigest(),
                    "size_on_disk": size_on_disk}


# `generations()` itself is in `datread.py`; this Check wrapper stays with `Check`.
def generation_checks(path):
    """`generations()` as pass/fail items, for the pre-flight."""
    gens = generations(path)
    ok = [g for g in gens if g["shape_ok"]]
    live = [g for g in gens if g["live"]]
    checks = [
        Check("the header's MFT is one of the candidates", bool(live),
              "header mft_offset 0x%X %s"
              % (read_header(path)["mft_offset"],
                 "found in the scan" if live else
                 "NOT FOUND by the descriptor scan -- the header and the file "
                 "disagree about where the MFT is")),
        Check("a fallback generation exists", len(ok) >= 2,
              "%d candidate(s) pass ScanMft's shape gate%s -- UPPER BOUND, "
              "LoadMft's full validation is not applied here"
              % (len(ok),
                 "" if len(ok) >= 2 else
                 "; a repair triggered by damage to the live MFT would have "
                 "NOTHING to adopt, return 0, and land on ArchiveCreate")),
    ]
    return checks, gens


# `crc_sweep()` is in `datread.py` too -- it returns findings, not refusals.


# -------------------------------------------------------------- launch gate --

class ArchiveUnsafe(SystemExit):
    """Refusing to hand this archive to a client. Never a warning.

    A `SystemExit`, for the same reason `cage.CageError` is one: the caller of a
    launch gate is a launch, and a refusal a caller can carry on past is a log
    line rather than a gate.

    `unreadable` keeps this module's two failure meanings apart at the CLI --
    "this archive has findings" (exit 1) and "this file could not be read far
    enough to have findings" (exit 2) -- which is the same separation `main()`
    already makes for every other verb.
    """

    def __init__(self, message, unreadable=False):
        super().__init__(message)
        self.unreadable = unreadable


# WHERE A FINGERPRINT DOCUMENT KEEPS ITS ROWS. MEASURED on
# `vault/research/archivewrite/a10-fingerprints.json`, whose top level is
# `stage / scale / built / toolkit / head / mft / rows` -- five provenance fields
# and one row block, `{"11115": [94508, "0x592E1A6F", 8], ...}`. `overlay.py`
# writes the same block shape for BOTH sides of a profile, so a document can hold
# more than one row map. This tool never guesses which one the archive in front
# of it is supposed to match: it takes the side it was ASKED for, or the default
# side of a document that names sides, or the only block there is -- and
# otherwise it names the candidates and refuses.
#
# `staged` is here and `rows` is here because they are two spellings of THE SAME
# side, the profile's own. Two of them in one document is an ambiguity and is
# refused (see `_fingerprint_side`); it used to be resolved by tuple order, with
# nothing printed.
FINGERPRINT_ROW_KEYS = ("rows", "staged")

#: THE SIDES OF AN `overlay.py` RECORD, WHICH ARE NOT CANDIDATES TO CHOOSE
#: BETWEEN. `rows` is what the profile puts in the archive, `retail_rows` the
#: baseline it replaced, `staged_rows` (pre-launch record only) what was staged.
#: A document carrying any of these is answering "which side is deployed", and
#: the answer must be the side the caller ASKED for -- never whichever block
#: happened to be the only one left. MEASURED 2026-08-20: deleting `rows` from a
#: build record left `retail_rows` as the single candidate, and the gate cleared
#: a pure-RETAIL archive for a caller who had asked whether its overlay was
#: deployed. That is the exact failure this module's own refusal text names.
OVERLAY_ROW_KEYS = ("rows", "retail_rows", "staged_rows")

#: Every key `side=` will accept, and the order they are reported in.
FINGERPRINT_SIDE_KEYS = ("rows", "staged", "retail_rows", "staged_rows")

#: The side taken when a document names sides and the caller named none. It is a
#: DEFAULT and not a fall-through: if this side is missing or empty the read
#: refuses, rather than answering out of a different block.
DEFAULT_SIDE = "rows"

DOCUMENT_REMEDY = (
    "This is a finding about the DOCUMENT, not about the archive: the archive "
    "was read and is not what failed. Write the record again with `python "
    "toolkit/mapdata/overlay.py --build MANIFEST`, or hand assert_archive_safe "
    "the row mapping itself.")


def _is_row_block(obj):
    """True for a `{row: [size, crc, compression]}` mapping, and only that."""
    if not isinstance(obj, dict) or not obj:
        return False
    for key, val in obj.items():
        try:
            int(key)
        except (TypeError, ValueError):
            return False
        if not isinstance(val, (list, tuple)) or len(val) != 3:
            return False
    return True


def _document_fault(source, reason, remedy=DOCUMENT_REMEDY):
    """Refuse because of the DOCUMENT. Always raises; never returns.

    `unreadable=False`, deliberately and in every case. The flag separates "this
    archive has findings" (exit 1) from "this file could not be read far enough
    to have findings" (exit 2), and a doctored fingerprint document is neither of
    the second: the archive was read, its ten open-time rules passed, its payload
    CRCs were recomputed. MEASURED 2026-08-20, before this existed: five doctored
    shapes -- a crc that is not hex, a size that is a word, a negative row key, a
    document that is not there, truncated JSON -- left `assert_archive_safe` as
    raw `ValueError`/`struct.error`/`FileNotFoundError`/`JSONDecodeError`, past
    every `except ArchiveUnsafe` in the tree, and the CLI's own last-resort
    handler printed them as "the archive could not be read far enough to have
    findings" with exit 2. The archive was fine. The document was the finding.
    """
    raise ArchiveUnsafe(
        "REFUSING to read fingerprints from %s\n  %s\n  %s"
        % (source, reason, remedy), unreadable=False)


def _overlay_module():
    """`overlay`, imported HERE and never at module scope.

    THERE IS A CYCLE AND THIS IS WHICH WAY IT RUNS. `overlay.py:188` imports this
    module at its own top level, so a module-level `import overlay` here would be
    an import cycle that fails on whichever of the two is loaded first. A lazy
    import inside the one function that needs it is the house pattern --
    `datwrite.py` reaches `datmove` and `datplan` exactly this way -- and it also
    keeps `overlay`'s dependency chain (`gwenc`, `refindex`, `vaultpath`) off the
    launch path, which calls this function with no fingerprints and never gets
    here at all.
    """
    import overlay  # noqa: E402,PLC0415  -- see the docstring
    return overlay


def _verify_overlay_record(doc, source):
    """overlay.py's own three refusals, run by overlay.py's own code. -> a note.

    `None` when the document does not declare itself an overlay record, which is
    the a10stage document and the bare mapping a caller hands in.

    WHY THIS IS HERE AT ALL. `overlay.load_fingerprints` (defined in
    `overlaystate.py` since 2026-09-11; `overlay` re-exports the name)
    refuses a record three ways before it reads a row out of it: its own digest,
    the manifest sha, and the RETAIL stamp. MEASURED 2026-08-20: this gate
    honoured none of them, and `--assert-safe --fingerprints F` CLEARED using a
    file `overlay.py --status` refuses to open. A tripwire armed on one of two
    readers is a tripwire on neither.

    WHY IT DOES NOT SIMPLY CALL `load_fingerprints`. That function takes a
    `Manifest` and reads the record at the CANONICAL path derived from it
    (`fingerprints_path`, which needs a vault), so handing it a document at an
    arbitrary path would validate a DIFFERENT file from the one in front of us --
    which is the whole defect, in the other direction. So the three checks are
    made here in overlay's order, and every comparison is overlay's own code:
    `_self_sha` is the digest formula, `load_manifest` reads and shas the
    manifest, `archive_identity` takes the baseline stamp, `STAMP_FIELDS` says
    which fields count. Nothing is re-expressed. `test_datcheck.py` §12e feeds one
    document to BOTH readers and requires the same accept/refuse verdict, because
    the ordering is the one thing that is written twice.
    """
    if not isinstance(doc, dict) or "format" not in doc:
        return None
    overlay = _overlay_module()
    if doc.get("format") != overlay.FORMAT:
        return None
    if doc.get("format_version") != overlay.FORMAT_VERSION:
        _document_fault(
            source,
            "it is format_version %r; overlay.py writes %r"
            % (doc.get("format_version"), overlay.FORMAT_VERSION),
            "Re-build rather than read across formats: `python "
            "toolkit/mapdata/overlay.py --build MANIFEST`.")
    if doc.get("self_sha256") != overlay._self_sha(doc):
        _document_fault(
            source,
            "it does not match its own digest -- something edited this record "
            "after it was written",
            "overlay.py calls this an accident tripwire rather than "
            "cryptography, and refuses to read the record at all; a launch gate "
            "that clears on a file `overlay.py --status` will not open is the "
            "worse of the two answers. Write it again: `python "
            "toolkit/mapdata/overlay.py --build MANIFEST`.")
    mpath = doc.get("manifest")
    if not isinstance(mpath, str) or not mpath:
        _document_fault(source,
                        "it declares itself an overlay record and names no "
                        "manifest (`manifest` is %r)" % (mpath,))
    if not os.path.isfile(mpath):
        _document_fault(
            source,
            "the manifest it was built from is not at %s" % mpath,
            "Every fingerprint in this record is relative to that manifest and "
            "to the retail baseline the manifest names, so neither can be "
            "checked. `overlay.py --status` cannot read it either.")
    try:
        manifest = overlay.load_manifest(mpath)
    except SystemExit as exc:
        _document_fault(
            source,
            "the manifest it names (%s) is not usable: %s"
            % (mpath, str(exc).splitlines()[0]),
            "The record is checked against that manifest and against the retail "
            "archive it names, so a manifest overlay.py refuses is a record "
            "nothing can verify.")
    if doc.get("manifest_sha256") != manifest.sha256:
        _document_fault(
            source,
            "it was built from a DIFFERENT manifest -- record %r, on disk %r"
            % (doc.get("manifest_sha256"), manifest.sha256),
            "The manifest has changed since this profile was staged, so the "
            "rows it owns and the payloads it declares may both have moved. "
            "Write it again: `python toolkit/mapdata/overlay.py --build %s`."
            % manifest.path)
    try:
        with overlay.Archive(manifest.retail) as ar:
            now = overlay.archive_identity(ar)
    except (OSError, ValueError, KeyError, SystemExit, struct.error) as exc:
        _document_fault(
            source,
            "the RETAIL baseline it is relative to (%s) could not be read: "
            "%s: %s" % (manifest.retail, type(exc).__name__, exc),
            "Every fingerprint in this record is relative to that baseline, so "
            "'retail on all touched rows' would be answered about an archive "
            "nobody is holding.")
    have = doc.get("retail")
    have = have if isinstance(have, dict) else {}
    for field in overlay.STAMP_FIELDS:
        if have.get(field) != now.get(field):
            _document_fault(
                source,
                "it was built against a different RETAIL archive -- %s: the "
                "record says %r, %s says %r"
                % (field, have.get(field), manifest.retail, now.get(field)),
                "Every fingerprint in this record is relative to that baseline, "
                "so 'retail on all touched rows' would be answered about an "
                "archive nobody is holding. Write it again: `python "
                "toolkit/mapdata/overlay.py --build %s`." % manifest.path)
    return {"format": doc["format"], "overlay": doc.get("overlay"),
            "manifest": manifest.path, "retail": manifest.retail,
            "checked": ["self digest", "manifest sha256", "retail stamp"]}


def _load_fingerprint_doc(fingerprints):
    """(the parsed document, a string naming where it came from)."""
    if isinstance(fingerprints, dict):
        return fingerprints, "a caller-supplied mapping"
    if not isinstance(fingerprints, (str, bytes, os.PathLike)):
        _document_fault("a caller-supplied %s" % type(fingerprints).__name__,
                        "fingerprints must be a row mapping, a fingerprint "
                        "document, or a path to one")
    source = str(fingerprints)
    try:
        with open(fingerprints, "r", encoding="utf-8") as fh:
            return json.load(fh), source
    except OSError as exc:
        _document_fault(source, "%s: %s" % (type(exc).__name__, exc))
    except ValueError as exc:            # json.JSONDecodeError is a ValueError
        _document_fault(source, "it is not readable JSON: %s: %s"
                        % (type(exc).__name__, exc))


def _shape_of(doc, key):
    """What `doc[key]` IS, for a refusal that has to say why it is not a block."""
    if key not in doc:
        return "ABSENT"
    val = doc[key]
    if isinstance(val, dict) and not val:
        return "an EMPTY object"
    return ("a %s, not a {row: [size, crc, compression]} block"
            % type(val).__name__)


def _fingerprint_side(doc, source, side=None):
    """(the row block, a string naming where it came from). Never positional.

    THE RULE, IN ONE SENTENCE: a document that names SIDES is read at the side
    that was asked for, or at `rows`, and nowhere else.
    """
    if _is_row_block(doc):
        if side is not None:
            _document_fault(
                source,
                "side %r was asked for and this document IS a bare row block, "
                "with no sides in it" % side,
                "Drop the side, or hand a document that names one of %s."
                % ", ".join(repr(k) for k in FINGERPRINT_SIDE_KEYS))
        return doc, source
    if not isinstance(doc, dict):
        _document_fault(source, "its top level is a %s, not an object"
                        % type(doc).__name__)
    blocks = sorted(k for k, v in doc.items() if _is_row_block(v))
    # A SIDE IS A KEY HOLDING A ROW BLOCK, not merely a key with that name.
    # `overlay.build` writes `"staged": "<path to the staged archive>"` -- a
    # string -- into the same document, and counting it here would put a file
    # path in a list of sides in the refusal text.
    present = [k for k in FINGERPRINT_SIDE_KEYS if _is_row_block(doc.get(k))]
    if side is not None:
        if not _is_row_block(doc.get(side)):
            _document_fault(
                source,
                "side %r is %s" % (side, _shape_of(doc, side)),
                "The row block(s) this document does hold: %s."
                % (", ".join(repr(k) for k in blocks) or "none at all"))
        return doc[side], "%s[%r]" % (source, side)
    if present:
        same = [k for k in FINGERPRINT_ROW_KEYS if _is_row_block(doc.get(k))]
        if len(same) > 1:
            _document_fault(
                source,
                "it holds %s, and those are two names for THE SAME side of a "
                "profile" % " and ".join(repr(k) for k in same),
                "Which one the archive is supposed to match is a GUESS -- and a "
                "fingerprint check run against the wrong side of a profile "
                "passes on the archive it was meant to refuse. Say which: "
                "assert_archive_safe(..., side=%r) or --side %s."
                % (same[0], same[0]))
        chosen = same[0] if (same and DEFAULT_SIDE not in present) else DEFAULT_SIDE
        if not _is_row_block(doc.get(chosen)):
            _document_fault(
                source,
                "this document names sides (%s) and the %r side is %s"
                % (", ".join(repr(k) for k in present), chosen,
                   _shape_of(doc, chosen)),
                "There is NO fall-through to another side. The caller asked "
                "whether the %r side is what is deployed, and answering out of "
                "a different block clears the archive this check exists to "
                "refuse. Row block(s) actually present: %s. Ask for one by name "
                "with side=/--side, or write the record again."
                % (chosen, ", ".join(repr(k) for k in blocks) or "none at all"))
        return doc[chosen], "%s[%r]" % (source, chosen)
    if len(blocks) == 1:
        return doc[blocks[0]], "%s[%r]" % (source, blocks[0])
    _document_fault(
        source,
        "this document holds %d row block(s) %s and none of them is named %s"
        % (len(blocks), blocks or "",
           " or ".join(repr(k) for k in FINGERPRINT_SIDE_KEYS)),
        "Which one the archive is supposed to match is a GUESS -- and a "
        "fingerprint check run against the wrong side of a profile passes on the "
        "archive it was meant to refuse. Name the block with side=, or hand "
        "assert_archive_safe the mapping itself.")


def _fingerprint_file_ids(doc, where):
    """{row: file_id} out of the document's `file_ids` block, or `{}`.

    THE ADDRESSING UNIT, and the reason the identity tier has one. A row number
    is a position in ONE archive's table; `overlay.deployed_state` re-resolves
    every file id before it compares a single fingerprint and says why in its own
    docstring, in the paragraph headed THE FILE IDS ARE RE-RESOLVED FIRST:
    "the client relocates rows during ordinary
    play, so a fingerprint compared by row number alone can be comparing two
    different files." MEASURED 2026-08-20 on one archive with its two file-id
    records swapped and every row still carrying its own bytes: `overlay.py
    --status` answered OTHER ("the archive has been rearranged under this
    profile") and this gate CLEARED it -- while its own refusal text sends the
    operator to that same authority. `datwrite.check_identity` had the rule
    already: a row index is a fact about the copy.
    """
    raw = doc.get("file_ids") if isinstance(doc, dict) else None
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        _document_fault(where, "its `file_ids` block is a %s, not a mapping of "
                               "row to file id" % type(raw).__name__)
    out = {}
    for key, val in raw.items():
        try:
            row, fid = int(key), int(val)
        except (TypeError, ValueError):
            _document_fault(where, "its `file_ids` block maps %r -> %r, which is "
                                   "not row -> file id" % (key, val))
        if row < 0 or fid < 0:
            _document_fault(where, "its `file_ids` block maps row %r to file id "
                                   "%r, and neither may be negative"
                                   % (key, val))
        out[row] = fid
    return out


class _Fingerprints:
    """One fingerprint document, read and checked -- what the identity tier compares.

    `rows` is `{row: (size, crc, compression)}`, `where` names the block it came
    from, `file_ids` is `{row: file_id}` (possibly empty) and `record` is the
    overlay note from `_verify_overlay_record` (or None).
    """

    __slots__ = ("rows", "where", "file_ids", "record")

    def __init__(self, rows, where, file_ids, record):
        self.rows = rows
        self.where = where
        self.file_ids = file_ids
        self.record = record


def _fingerprint_rows(fingerprints, side=None):
    """Read a fingerprint document. -> `_Fingerprints`. Refuses, never raises raw.

    Accepts the row mapping itself, or a path to a fingerprint document. The crc
    may be written either way round (`"0x592E1A6F"` as a10stage writes it, a bare
    lowercase `"58efe7e6"` as overlay writes it, or a plain int) because the file
    is JSON and every spelling survives a round trip; every other field is an int
    and is required to be one.

    EVERY FAULT IN THE DOCUMENT COMES OUT AS `ArchiveUnsafe(unreadable=False)`.
    See `_document_fault` for the five that used to escape raw.
    """
    doc, source = _load_fingerprint_doc(fingerprints)
    record = _verify_overlay_record(doc, source)
    block, where = _fingerprint_side(doc, source, side)
    out = {}
    for key, val in block.items():
        try:
            row = int(key)
            size, crc, comp = val
            crc = int(crc, 16) if isinstance(crc, str) else int(crc)
            size, comp = int(size), int(comp)
        except (TypeError, ValueError) as exc:
            _document_fault(where,
                            "row %r's fingerprint %r is not (size, crc, "
                            "compression): %s: %s"
                            % (key, val, type(exc).__name__, exc))
        if row < 0:
            _document_fault(
                where,
                "it fingerprints row %r, and a row number is an index into the "
                "MFT -- there is no negative one" % key,
                "Left to run, this reads an empty slice out of the table and "
                "fails an unpack; it is a fault in the document and is named as "
                "one. " + DOCUMENT_REMEDY)
        out[row] = (size, crc & 0xFFFFFFFF, comp)
    return _Fingerprints(out, where, _fingerprint_file_ids(doc, where), record)


# `self_crc_state()` is in `datread.py`, with the `datwrite` import it needs.


UNREADABLE_REMEDY = ("The archive could not be read far enough to have findings, "
                     "which is not permission to open it with a client.")

# THE ONE UNREADABLE CAUSE THAT IS NOT DAMAGE. A running client holds an
# EXCLUSIVE lock on the archive it was launched from: while `Gw.exe` is up that
# file cannot be opened even for reading, and Python raises `PermissionError`,
# not a partial read (RUNBOOK, "The third copy of Gw.dat, and why it exists").
# Left generic, the refusal above reads as corruption on a 4.2 GB copy and names
# no action -- so the errno gets the sentence it earns. The launch sites also
# order themselves around this (livesession.preflight runs its client census
# BEFORE the gate, so a left-open client hits the refusal written for it), and
# this line is what covers the sites that have no census to run.
LOCKED_REMEDY = ("A client already running holds this archive open -- close every "
                 "Gw.exe and re-run. That is a lock, not damage: only if nothing "
                 "is running does this reading mean the file itself.")


def _unreadable_remedy(exc):
    """The remedy line for a refusal that could not read the archive at all."""
    if isinstance(exc, PermissionError):
        return LOCKED_REMEDY + " " + UNREADABLE_REMEDY
    return UNREADABLE_REMEDY


def assert_archive_safe(dat, fingerprints=None, deep=False, why="launch",
                        side=None):
    """Refuse unless this archive is one a client may be handed. Read-only.

    THE INVARIANT, in one sentence: **an archive a client opens must be one the
    client will not REPAIR.** `cage.assert_launch_safe` decides from a binary's
    bytes whether it may be aimed at a given server; this decides from an
    archive's bytes whether it may be opened at all, and it is the same shape of
    answer -- read the verdict from what is on disk, refuse with a message
    naming the remedy, and return a dict describing what was cleared so the
    caller can log what it let through rather than merely that it let something
    through.

    IT FAILS CLOSED ON EVERYTHING, and unlike the cage there is no cell where
    that is the wrong default. The cage's stock-at-live cell proceeds through an
    undeterminable firewall because the risk there is a STALL. Here every
    uncertainty is on the same side: the client's repair phase 2 walks a bad
    payload CRC back to its `FLAG_FIRST_STREAM` head and DELETES THE WHOLE
    CHAIN, and a header whose CRC does not verify tail-jumps `ArchiveOpen` into
    **ArchiveCreate**, which writes a fresh empty archive over 4.2 GB with no
    logged error and no recovery path. There is nothing on the other side of the
    scale to weigh those against, so a suspect archive never meets a client.

    THE TIERS:

      integrity (always)   the file header's magic and its CRC over 0x00..0x0C;
                           `preflight()`'s ten open-time rules; the MFT self-crc
                           (`self_crc_state`, the one rule the pre-flight has
                           never made); and `crc_sweep`, the only tier that can
                           see a stale payload CRC at all.

                           MEASURED 2026-08-20 over all EIGHT 4.2 GB archives in
                           the vault -- `dat_study`, five `run/` copies and two
                           `run-live/` copies: every one CLEARS, in 6.0 to 7.1 s
                           end to end. Both halves of that matter. The seconds
                           are what make "run it before every single launch"
                           affordable, and the eight clears are the positive
                           control a fail-closed gate needs before it is wired
                           into a launch path: a gate that reddens on the real
                           target is not a gate, it is a tool nobody can run,
                           which is exactly how one of the ten rules below had
                           to be corrected on 2026-08-13.

      deep=True            adds `generation_checks`: how many older MFT
                           generations a repair would have to fall back on.
                           OPT-IN, because it is a second whole-file read and
                           because one generation is a fact about an archive's
                           HISTORY -- a freshly cut copy has exactly one and is
                           perfectly healthy. Run it before an archive is
                           RISKED, not before every open.

      identity (opt-in)    with `fingerprints`, every named row's (size, crc,
                           compression) must match. This is what answers "is the
                           profile I built the profile that is deployed", and it
                           is NOT run on the live path.

                           ADDRESSED BY FILE ID WHERE THE DOCUMENT HAS ONE. A row
                           number is a position in one archive's table and the
                           client relocates rows during ordinary play, so a
                           document carrying a `file_ids` block has each of those
                           ids re-resolved against the archive's own table BEFORE
                           any fingerprint is compared -- the check
                           `overlay.deployed_state` makes, for the reason its
                           docstring gives. A document with no `file_ids` is read
                           by row number and the receipt SAYS SO, in the one line
                           a caller prints; `datwrite.check_identity` set that
                           precedent ("You are trusting the row number").

                           AND THE SIDE IS ASKED FOR, NOT GUESSED. An overlay
                           record holds `rows`, `retail_rows` and sometimes
                           `staged_rows`; `side=` chooses, `rows` is the default,
                           and a side that is missing or empty REFUSES rather than
                           falling through to whichever block is left.
                           `overlay.load_fingerprints`'s three trust checks --
                           self digest, manifest sha, retail stamp -- are run
                           first, by overlay's own code, on any document that
                           declares itself an overlay record.

    ON THE LIVE PATH THIS VERIFIES AND NEVER MODIFIES, and it takes no
    fingerprints there: `vault/run-live/`'s archive has its updater LIVE by
    design and streams new content into itself during a real session, so it
    legitimately drifts and a fingerprint check against it would refuse the one
    configuration that works (RUNBOOK, "a live run writes new content into its
    own Gw.dat"). Nothing in this module opens a file for writing.

    EACH LAUNCH SITE CALLS THIS ITSELF rather than trusting an upstream caller,
    which is `session.py`'s own rule about the cage and is quoted here because
    it is the same rule: "A guard that only guards one of two doors is the shape
    of the defect it is here to prevent -- vault/run held two patched binaries
    and one was caged." There are FOUR of those doors, not two:
    `session.run_client`, `drive_client.main`, `livesession.preflight` and
    `deploy.launch`, and `test_datcheck.py` §12d holds that list against a census
    of the harness files that hand an exe to `Popen`, because an enumerated list
    of launch paths is only as good as its own census of them.

    AND A SITE WITH A CLIENT CENSUS RUNS THAT FIRST. A running client holds an
    EXCLUSIVE lock on the archive it was launched from, so while one is up this
    function cannot read the file at all and answers `unreadable` -- a true
    statement that names no action. Where a caller already knows how to say "a
    client is running, close it" (`livesession.preflight`), that refusal must be
    reached BEFORE this one; where it does not, `LOCKED_REMEDY` says it here.
    """
    path = os.path.abspath(dat)

    def refuse(reason, remedy, unreadable=False):
        raise ArchiveUnsafe(
            "REFUSING to %s from %s\n  %s\n  %s" % (why, path, reason, remedy),
            unreadable=unreadable)

    try:
        size_on_disk = os.path.getsize(path)
        header = read_header(path)
    except (OSError, ValueError, struct.error) as exc:
        refuse("%s: %s" % (type(exc).__name__, exc),
               _unreadable_remedy(exc), unreadable=True)

    if header["raw"][:4] != FILE_MAGIC:
        refuse("the file header's magic is %r, not %r"
               % (header["raw"][:4], FILE_MAGIC),
               "ArchiveOpen validates this before anything else; a copy that "
               "fails it is REBUILT, not rejected.")
    if header["crc_stored"] != header["crc_computed"]:
        refuse("the header CRC over 0x00..0x0C is stored 0x%08X, computed 0x%08X"
               % (header["crc_stored"], header["crc_computed"]),
               "Validated at 0x0047B6D2 on EVERY open, and the failure route "
               "tail-jumps to ArchiveCreate (0x004797EC), which overwrites the "
               "whole archive with a fresh empty one. Restore this copy from its "
               "donor; do not launch anything at it.")

    try:
        checks, facts = preflight(path)
        mft = read_mft(path, header)
        stored, computed = self_crc_state(path, header, mft)
        sweep = crc_sweep(path)
    except (OSError, ValueError, KeyError, struct.error) as exc:
        refuse("%s: %s" % (type(exc).__name__, exc),
               _unreadable_remedy(exc), unreadable=True)

    failed = [c for c in checks if not c.ok]
    if failed:
        refuse("%d of %d open-time rules FAILED:\n    %s"
               % (len(failed), len(checks),
                  "\n    ".join(c.line() for c in failed)),
               "Every one of these is something the CLIENT does at open, so a "
               "copy that fails one produces a repair, a silent delete or an "
               "assert -- never a clean error. "
               "python toolkit/mapdata/datcheck.py --dat %s --preflight" % path)

    if stored != computed:
        refuse("the MFT self-crc is stored 0x%08X, computed 0x%08X" % (stored,
                                                                       computed),
               "LoadMft checks this and the pre-flight does not, so an archive "
               "in this state reports 10 of 10 clear and is still rejected by "
               "the client. It is the shape a grow-without-resync leaves "
               "(datwrite.py:755-781). Fix it with "
               "`python toolkit/mapdata/datwrite.py --dat %s --verify` and the "
               "journal that wrote it." % path)

    if sweep["bad"]:
        rows = ", ".join(
            "%s (%s)" % (row_label(i), whyrow) for i, _r, _g, whyrow
            in sweep["bad"][:6])
        refuse("%d row(s) whose payload does not match its stored CRC: %s%s"
               % (len(sweep["bad"]), rows,
                  " ..." if len(sweep["bad"]) > 6 else ""),
               "The client's repair phase 2 walks each of these back to its "
               "FLAG_FIRST_STREAM head and deletes the WHOLE chain -- extents "
               "freed, rows memset, file-id record dropped -- the moment repair "
               "fires for any reason at all.")

    gens = None
    if deep:
        try:
            gen_checks, gens = generation_checks(path)
        except (OSError, ValueError, struct.error) as exc:
            refuse("the generation scan could not run: %s: %s"
                   % (type(exc).__name__, exc),
                   "A deep gate that cannot read the file is not a pass.",
                   unreadable=True)
        gen_failed = [c for c in gen_checks if not c.ok]
        if gen_failed:
            refuse("the generation census FAILED:\n    %s"
                   % "\n    ".join(c.line() for c in gen_failed),
                   "This is an UPPER BOUND -- ScanMft's shape gate only, not "
                   "LoadMft's full validation -- so a census this thin is worse "
                   "than it looks. Take a fresh copy from the donor before "
                   "risking this one, or drop deep=True if history is not what "
                   "you are gating on.")

    identity = None
    if fingerprints is not None:
        # THE DOCUMENT IS READ INSIDE THE REFUSAL BOUNDARY. Everything
        # `_fingerprint_rows` can find is a fault in the DOCUMENT and comes back
        # as `ArchiveUnsafe(unreadable=False)`; the bare `Exception` arm is the
        # net under that promise, because the failure it replaces was five
        # exception types nobody had enumerated escaping a launch gate past every
        # `except ArchiveUnsafe` in the tree. A refusal naming the type is the
        # fail-closed answer; a traceback out of a gate is not an answer at all.
        try:
            fp = _fingerprint_rows(fingerprints, side=side)
        except ArchiveUnsafe:
            raise
        except Exception as exc:                                # noqa: BLE001
            _document_fault(
                "a caller-supplied mapping" if isinstance(fingerprints, dict)
                else str(fingerprints),
                "%s: %s" % (type(exc).__name__, exc))
        want, where, file_ids = fp.rows, fp.where, fp.file_ids
        n = row_count(mft)

        # THE FILE IDS FIRST, AND THAT ORDER IS THE POINT. If an id has moved,
        # that IS the answer -- rather than a fingerprint mismatch reported as if
        # a payload had changed, or (worse) a clear, which is what a row-number
        # compare gives on an archive whose two id records were swapped.
        by_id = sorted(row for row in want if row in file_ids)
        by_row = sorted(row for row in want if row not in file_ids)
        if by_id:
            try:
                records, _idblob = file_id_records(path, mft, header)
            except (OSError, ValueError, struct.error) as exc:
                refuse("the file-id table could not be read, so the rows %s "
                       "names cannot be resolved by id: %s: %s"
                       % (where, type(exc).__name__, exc),
                       _unreadable_remedy(exc), unreadable=True)
            for row in by_id:
                fid = file_ids[row]
                named = sorted({r for f, r in records if f == fid})
                if named != [row]:
                    refuse("file id 0x%X named row %d when %s was written and "
                           "names %s in this archive"
                           % (fid, row, where, named or "nothing"),
                           "The archive has been REARRANGED under this profile: "
                           "a row number is a position in one archive's table "
                           "and the client relocates rows during ordinary play, "
                           "so comparing row %d's fingerprint here would be "
                           "comparing two different files. This is the state "
                           "`overlay.py --status MANIFEST` calls OTHER; ask it "
                           "what IS deployed rather than launching at this."
                           % row)

        for row in sorted(want):
            size, crc, comp = want[row]
            if row >= n:
                refuse("fingerprinted row %d does not exist in this archive "
                       "(%d rows)" % (row, n),
                       "The fingerprints in %s were taken from a DIFFERENT "
                       "archive. Ask which profile is deployed with "
                       "`overlay.py --status`." % where)
            got = row_fields(row_bytes(mft, row))
            have = (got["size"], got["crc"], got["extra_bytes"])
            if have != (size, crc, comp):
                refuse("%s does not match its fingerprint:\n"
                       "    want size %d crc 0x%08X compression %d\n"
                       "    have size %d crc 0x%08X compression %d"
                       % (row_label(row), size, crc, comp, *have),
                       "This archive is not the one %s describes. Ask what IS "
                       "deployed with `overlay.py --status MANIFEST` rather "
                       "than launching at it." % where)
        # WHAT WAS TRUSTED, IN THE ONE LINE A CALLER PRINTS. `check_identity`'s
        # precedent (datwrite.py:554-588): a check that could not be made says so
        # rather than implying it passed, because the alternative is a silent
        # green from a check that never ran.
        if by_id and not by_row:
            addressing = "resolved by FILE ID"
        elif by_row and not by_id:
            addressing = ("BY ROW NUMBER -- this document carries no file_ids, "
                          "so you are trusting the row numbers")
        else:
            addressing = ("%d by FILE ID, %d TRUSTING ROW NUMBERS"
                          % (len(by_id), len(by_row)))
        identity = {"source": where, "rows": len(want),
                    "addressing": addressing,
                    "by_file_id": by_id, "by_row_number": by_row,
                    "record": fp.record}

    cleared = {
        "dat": path,
        "why": why,
        "size_on_disk": size_on_disk,
        "rows": row_count(mft),
        "mft_offset": header["mft_offset"],
        "mft_sha256": hashlib.sha256(mft).hexdigest(),
        "header_crc": header["crc_stored"],
        "preflight": [c.name for c in checks],
        "self_crc": stored,
        "crc_sweep": {"checked": sweep["checked"], "skipped": sweep["skipped"]},
        "deep": bool(deep),
        "generations": None if gens is None else
                       sum(1 for g in gens if g["shape_ok"]),
        "identity": identity,
        "file_id_sha256": facts["file_id_sha256"],
    }
    cleared["summary"] = (
        "%s: %d rows, %d B, %d of %d open-time rules, self-crc 0x%08X, "
        "%d payload CRC(s) recomputed, MFT sha256 %s%s%s"
        % (os.path.basename(path), cleared["rows"], size_on_disk,
           len(checks), len(checks), stored, sweep["checked"],
           cleared["mft_sha256"][:16],
           "" if gens is None else
           ", %d MFT generation(s)" % cleared["generations"],
           "" if identity is None else
           ", %d row(s) match %s, %s" % (identity["rows"], identity["source"],
                                         identity["addressing"])))
    return cleared


# THE POST-FLIGHT HALF IS `datsnapshot.py` NOW -- take a snapshot, diff two of
# them, and say what changed in the client's own terms. Re-exported because
# `preflight` above reads `_snapshot_mft` and `CORROBORATION_ROWS` by bare name,
# `_main` below calls `write_snapshot`, `load_snapshot`, `diff` and
# `format_diff`, and because `overlay.py`, `test_overlay.py` and
# `test_datcheck.py` read them off this module as `datcheck.<name>`.
from datsnapshot import (SNAPSHOT_VERSION, RELOCATED, RECYCLED,  # noqa: F401,E402
                         DELETED, RELINKED, UNCLASSIFIED, ADDED, REMOVED,
                         CORROBORATION_ROWS, scan, snapshot, write_snapshot,
                         load_snapshot, _snapshot_mft, classify_row, diff,
                         format_diff)


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
    ap.add_argument("--generations", action="store_true",
                    help="every surviving MFT generation -- what a repair "
                         "would have to adopt (UPPER BOUND; shape gate only)")
    ap.add_argument("--crc-sweep", action="store_true",
                    help="recompute every USED row's payload CRC from disk. "
                         "Reads the whole file (~3 s for 4.2 GB)")
    ap.add_argument("--assert-safe", action="store_true",
                    help="the launch gate: header, the ten open-time rules, the "
                         "MFT self-crc and every payload CRC, as one verdict")
    ap.add_argument("--fingerprints", metavar="FILE",
                    help="with --assert-safe: an overlay fingerprint document; "
                         "every row it names must still match")
    ap.add_argument("--side", choices=list(FINGERPRINT_SIDE_KEYS),
                    help="with --fingerprints: WHICH side of the document the "
                         "archive is supposed to match. Default 'rows'. A side "
                         "that is missing or empty refuses; there is no "
                         "fall-through to another block")
    ap.add_argument("--deep", action="store_true",
                    help="with --assert-safe: add the MFT generation census "
                         "(a second whole-file read)")
    ap.add_argument("--json", metavar="FILE", help="also write the result as JSON")
    args = ap.parse_args(argv)

    if not (args.preflight or args.snapshot or args.diff
            or args.generations or args.crc_sweep or args.assert_safe):
        ap.error("nothing to do: pass --preflight, --snapshot, --diff, "
                 "--generations, --crc-sweep or --assert-safe")

    # AN ARGUMENT THAT DID NOTHING IS A PASS ON THE WRONG ARCHIVE. The check
    # above covers "nothing to do"; this covers the other shape, and it is the
    # one an operator reaches by typo. MEASURED 2026-08-20: `--preflight
    # --fingerprints F` on an archive the document does not describe exited 0
    # with the identity check never run and nothing said about it. The
    # dependency was stated in help text only, which is a rule nothing checks.
    dependent = [name for name, on in (("--fingerprints", args.fingerprints),
                                       ("--deep", args.deep),
                                       ("--side", args.side)) if on]
    if dependent and not args.assert_safe:
        ap.error("%s only mean(s) anything with --assert-safe, and passing it "
                 "without would run the check you asked for NOT AT ALL while "
                 "exiting 0" % ", ".join(dependent))
    if args.side and not args.fingerprints:
        ap.error("--side chooses which block of --fingerprints to compare "
                 "against, so it needs one")

    rc = 0
    payload = {}

    # THE GATE ANSWERS FIRST AND ALONE. A refusal returns here rather than
    # falling through to the other verbs, because printing a row table out of an
    # archive this tool has just refused to let near a client is how a refusal
    # gets read as a report.
    if args.assert_safe:
        try:
            cleared = assert_archive_safe(args.dat, fingerprints=args.fingerprints,
                                          deep=args.deep, why="launch",
                                          side=args.side)
        except ArchiveUnsafe as exc:
            print(str(exc))
            return 2 if exc.unreadable else 1
        print("archive gate: %s" % cleared["summary"])
        print("  %s" % ROW_CONVENTION)
        print("  cleared: %s" % ", ".join(cleared["preflight"]))
        payload["assert_safe"] = cleared
        if not (args.preflight or args.snapshot or args.diff
                or args.generations or args.crc_sweep):
            if args.json:
                with open(args.json, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, indent=1)
                print("json -> %s" % args.json)
            return 0

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

    if args.generations:
        gens = generations(args.dat)
        ok = [g for g in gens if g["shape_ok"]]
        print("MFT generations: %s" % args.dat)
        print("  %14s %14s %10s %8s %s"
              % ("offset", "flush counter", "rows", "shape", ""))
        for g in gens:
            print("  0x%012X %14d %10d %8s %s"
                  % (g["offset"], g["counter"], g["rows"],
                     "ok" if g["shape_ok"] else "no",
                     "LIVE" if g["live"] else ""))
        print("  %d candidate(s), %d passing ScanMft's shape gate"
              % (len(gens), len(ok)))
        print("  UPPER BOUND: LoadMft's full validation (self-CRC, alignment, "
              "nextStream range and acyclicity) is NOT applied here.")
        if len(ok) < 2:
            print("  REFUSE: no fallback generation. A repair triggered by "
                  "damage to the live MFT would have nothing to adopt, return "
                  "0, and land on ArchiveCreate.")
            rc = max(rc, 1)
        payload["generations"] = gens

    if args.crc_sweep:
        sw = crc_sweep(args.dat)
        print("crc sweep: %s" % args.dat)
        print("  %d row(s), %d payload CRCs recomputed, %d structural row(s) "
              "skipped by name %s"
              % (sw["rows"], sw["checked"], len(sw["skipped"]), sw["skipped"]))
        for i, r, got, why in sw["bad"][:20]:
            print("  [FAIL] row %-7d off 0x%012X size %-10d %s"
                  % (i, r["offset"], r["size"], why))
        if sw["bad"]:
            print("  REFUSE: %d row(s) whose payload does not match its stored "
                  "CRC. The client's repair deletes the WHOLE nextStream chain "
                  "of each, the moment it fires for any reason." % len(sw["bad"]))
            rc = max(rc, 1)
        else:
            print("  every payload CRC matches")
        payload["crc_sweep"] = {
            "rows": sw["rows"], "checked": sw["checked"],
            "skipped": sw["skipped"],
            "bad": [{"row": i, "offset": r["offset"], "size": r["size"],
                     "detail": why} for i, r, _g, why in sw["bad"]]}

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
