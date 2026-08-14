"""Check the archive reader against real bytes, not against anyone's source.

This is the test the protocol layer cannot have. Every claim our server makes
about the wire rests on reconstructions, so its tests can only check that we
encode what we intended to encode. Here the artifact is on disk and the format
is falsifiable, so these assertions can fail for the right reason: because the
file says otherwise.

The strongest check is section 3, and it is worth understanding why it is strong.
Decompression cannot be validated by "the output was as long as the header said"
-- the decoder stops at that length by construction, so the match is forced (see
the caveat at the top of gwdat.py). But a map's FFNA chunk table is a completely
independent structure: a walk of (id, size, payload) records either consumes the
decompressed output to the exact final byte or it does not. Wrong decompression
produces garbage sizes and the walk runs off the end. That check has no
circularity in it.

    python toolkit/mapdata/test_archive.py
    python toolkit/mapdata/test_archive.py --dat <path>

ROW INDICES ARE COPY-SPECIFIC. The reference rows below were measured against
the archive our patched client has actually run (177,342 entries). A running
client writes to its own archive, so the install copy has a different entry
count and different row numbers. Against a different copy the reference-row
check is skipped rather than failed -- it is not a defect in the reader.
"""

import argparse
import struct
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import (Archive, ffna_chunks, ffna_type,  # noqa: E402
                     DEFAULT_DAT, file_id_table)
import archive as archive_mod  # noqa: E402
import datcheck  # noqa: E402
import datwrite  # noqa: E402
import checks  # noqa: E402

# Map files carry flags 259. The high byte is the stream (1) and the low byte is
# the entry flags (3). MEASURED: exactly 349 entries in this archive have it, and
# every one sampled decompressed to an ffna type-3 payload.
MAP_FLAGS = 259
EXPECTED_MAP_COUNT = 349
FFNA_TYPE_MAP = 3

# Reference maps, measured on the run-dir archive. The point of pinning exact
# byte counts is that a decompressor regression changes them.
EXPECTED_ENTRY_COUNT = 177342
REFERENCE_MAPS = {7982: (24, 2925270), 20444: (22, 3389269)}

SAMPLE_SIZE = 6

# FLOOR: the nine checks that run against ANY copy of the archive -- the two
# header invariants in section 1, the map-flag count in section 2, and one per
# sampled map in section 3 (SAMPLE_SIZE = 6). Section 4's two reference rows are
# deliberately outside the floor: row indices are copy-specific, so that section
# declares a skip on an archive with a different entry count (see the header).
# Measured on the run-dir Gw.dat, 2026-08-06: a green run prints eleven [PASS]
# lines, nine of them mandatory. Scoring under nine means a map stopped being
# sampled or a section stopped running, and the passes that remain prove nothing.
#
# RAISED 9 -> 14 on 2026-08-13: section 1b adds five more that hold against ANY
# copy (the row/position conventions and the file-id table's row), because
# confusing `entries[row]` with a row NUMBER returns a different file rather
# than an error, and once cost a nearly-filed false refutation.
#
# RAISED 14 -> 31 the same day with section 1c, which is the same confusion one
# level up: `studies/crossbuild/FINDINGS.md` §4b.1 read a positional subscript
# as a row number, concluded that `archive.py` and `datcheck.py` number MFT rows
# differently, and left the repo with "never compare a row number printed by one
# tool against one printed by another". They agree on all 24 bytes of every row
# of the copy a run is pointed at, and 1c measures it in both directions on a
# REAL archive so the claim can go red the day either reader changes. Every one
# of 1c's checks holds against ANY copy -- nothing in it is pinned to a row
# number, and its map pair is selected by FLAGS so the label under test is not
# also the selector.
#
# THE FLOOR IS 31 AND THAT IS THE COPY-INDEPENDENT GREEN RUN, MEASURED. It was
# 26 for one afternoon, against a green run of 29, and the first thing two
# independent reviews did was RUN the sabotage: an early `return` cutting
# section 1c's last three checks -- the partner-role check, the file-id oracle
# and the built one-row-late control, i.e. exactly the three the section's own
# comments call load-bearing -- printed `ALL CHECKS PASSED (26 checks)` and
# exited 0, while cutting a fourth went red. (Both reviews reported that run;
# what is re-measured below is the fix, not the defect, because the 26-floor
# file no longer exists to run.) A floor three under its own green run is a
# floor that permits the silent deletion of exactly the checks that make its
# section a measurement.
#
# The old note argued for 25 in one sentence, 26 in another and "a green run
# prints 29" in a third, having been drafted for an 11-check section that grew a
# twelfth. No arithmetic here now, only counts off real runs, MEASURED 2026-08-14:
#
#   33  green on `vault/dat_study/Gw.dat` and on `vault/dat_c2/Gw.dat`
#       (section 4's two reference rows are pinned to that 177,342-row layout)
#   31  green on `vault/client/2026-04-30_b174de1f2d8d`, on
#       `vault/client/2026-07-29_221c13772c7a` and on `vault/run-live/...`
#       -- three copies, three different row counts, section 4 declaring a skip
#
# So 31: the largest number that cannot be beaten by pointing the run at a
# legitimately different archive. Section 4 stays outside this number for the
# reason the header gives -- row indices are copy-specific -- but it RAISES the
# floor to 33 when it actually runs, because leaving it at 31 on a 177,342-row
# copy would restore two checks of slack, which is the same defect one size
# smaller. The raise is only ever upward and only from the branch that is about
# to spend it. BOTH shapes now have ZERO headroom, and that is re-measured
# rather than reasoned: a `return` cutting ONE check reddens at 32/33 on
# `dat_study` and at 30/31 on `client/2026-04-30`.
LEDGER = checks.Ledger("dat archive", floor=31)
check = checks.adopt(LEDGER)


MFT_ENTRY = struct.Struct("<QIHHII")


def row_or_none(ar, n):
    """`Archive.row(n)`, or None if it refuses its own resolution.

    `row()` asserts that the row it resolved is the row it was asked for, which
    is the right thing for a caller and the wrong thing for a test: an
    AssertionError escapes to the top and the run dies with a traceback instead
    of a verdict, a floor and a ledger. MEASURED on the sabotage that sets
    `Entry.index = k`.
    """
    try:
        return ar.row(n)
    except (AssertionError, IndexError):
        return None


def read_row(mft, row):
    """The 24 bytes of one raw MFT row, unpacked HERE.

    Written out of `struct` on purpose: it shares no code with either reader,
    so section 1c's agreement is between two implementations rather than
    between a module and itself.
    """
    return MFT_ENTRY.unpack_from(mft, row * 24)


def bytes_at(path, offset, n):
    """`n` bytes read straight off disk. Nothing from either reader involved."""
    with open(path, "rb") as fh:
        fh.seek(offset)
        return fh.read(n)


def datcheck_read_row(mft, row):
    """The same 24 bytes, through DATCHECK'S OWN ACCESSOR.

    This exists because the headline check did not measure what its wording
    said. `agreement()` compared `Archive.entries` against `read_row` above -- a
    struct walker written in this file -- so the phrase "== datcheck row k+1"
    never touched `datcheck.row_bytes`, and a review that flipped `row_bytes` to
    `mft[(index+1)*24:...]` watched the headline print "0 mismatches over
    177,341 rows" and pass. The line a reader quotes as proof of agreement has
    to run the accessor it names, so the sweep is run twice: once against the
    independent walker (which is what makes it two implementations) and once
    against datcheck itself (which is what makes it about datcheck).

    Returns None rather than raising when the slice is not 24 bytes. MEASURED on
    that same sabotage: a shifted `row_bytes` runs off the end of the table at
    the LAST row, `struct.error` escapes to the top, and the run dies with a
    traceback and no verdict, no floor and no ledger -- the one failure
    `checks.py` cannot see. A wrong reader has to score as WRONG, not as absent.
    """
    try:
        return MFT_ENTRY.unpack(datcheck.row_bytes(mft, row))
    except struct.error:
        return None


def agreement(entries, mft, row_of_position, read=read_row):
    """How many positions disagree with the row `row_of_position` sends them to.

    The rival readings are passed IN rather than hard-coded so the correct one
    and the off-by-one are two live answers from one body of code. That is the
    only way the control below can mean anything: a check that has only ever
    been run on the right answer is a check that has never been shown to fail.

    `read` is the row reader, for the same reason: the independent walker and
    `datcheck.row_bytes` are two live answers too.
    """
    n = len(mft) // 24
    bad = 0
    agree_rows = []
    for k, e in enumerate(entries):
        try:
            row = row_of_position(k)
        except (IndexError, TypeError):
            bad += 1
            continue
        if not 0 <= row < n:
            bad += 1
            continue
        if read(mft, row) == (e.offset, e.size, e.compression, e.flags,
                              e.counter, e.crc):
            agree_rows.append(row)
        else:
            bad += 1
    return bad, agree_rows


def section_1c(ar, path):
    """ONE convention, measured across the two readers on a REAL archive.

    THIS SECTION EXISTS BECAUSE THE OPPOSITE WAS WRITTEN DOWN AND BELIEVED.
    `studies/crossbuild/FINDINGS.md` §4b.1 concluded that "the two tools number
    MFT rows differently, off by exactly one", labelled the cause CORROBORATED,
    and ended "never compare a row number printed by one tool against one
    printed by another". Every fact it cites is true and the conclusion drawn
    from them is false, which is the hardest kind to catch:

      * `archive.py[71495]` really is bit for bit what `datcheck` calls row
        71496 -- because `entries` is a POSITIONAL list and `entries[71495]` is
        row 71496 in both tools' numbering. A list subscript was read as a row
        number.
      * `archive.py` really does "report 177,334 rows where datcheck reports
        177,335" -- because that is `len(entries)` against a row count.
        `Archive.row_count` is the comparable number and it is equal.
      * `archive.py[2]` really is the MFT row -- and so is `datcheck`'s row 3
        and `archive.row(3)`. Same row, and `MFT_SELF_ROW = 3` says so.

    MEASURED 2026-08-14 across all TEN archives in the vault (an earlier note
    said six; there are ten and all ten open): `entries[k]` and datcheck row
    `k + 1` agree on all 24 bytes, 0 mismatches over 177,341 rows on `dat_study`
    and over the whole table of each of the other nine. This section re-measures
    ONE of them per run -- the copy `--dat` names -- which is the copy whose
    answer matters to the run that follows.

    The cost of believing §4b.1 was not academic. `deploy.py` prints "head
    71496, partner 71497" and `--diff` reported 71496 changed; read as a
    numbering disagreement, that says the client overwrote our authored map.
    Read correctly it says the client re-bloated the head we armed to zero,
    which is the experiment working. The check below is what makes the next
    such claim testable instead of arguable.

    WHAT IS AND IS NOT LOAD-BEARING HERE. The 0-mismatch headline is the weak
    half: it is what a reader that agreed with itself would print too. The
    control is the strong half -- the SAME comparison under the off-by-one
    reading must fail, and it must fail everywhere except where the archive
    genuinely cannot tell the two apart. That exception is not a fudge, it is
    structural: rows 4..15 are all-zero spares the client requires, so a shifted
    read of rows 4..14 lands on an identical all-zero row. Exactly 11, on every
    copy measured, and the check requires both the count AND that every one of
    them is an all-zero pair -- either alone would be satisfied by the wrong
    thing.

    AND THE ROW COUNTS. `datcheck.row_count == Archive.row_count` reads like a
    cross-tool measurement and is very nearly a tautology: `Archive.__init__`
    refuses to open a file unless `entry_count * 24 == mft_size`, and
    `datcheck.row_count` is `len(mft) // 24` over exactly `mft_size` bytes. No
    archive on disk can redden it. It is kept because it CAN fail on a code
    change -- and it did, under a full renumbering of datcheck -- but it is
    labelled here so nobody quotes it as evidence about an archive.
    """
    mft = datcheck.read_mft(path)
    n_dc = datcheck.row_count(mft)

    check(n_dc == ar.row_count,
          f"datcheck.row_count ({n_dc:,}) == Archive.row_count "
          f"({ar.row_count:,}) -- one number (but see the docstring: this can "
          f"only fail on a CODE change, never on an archive)")
    check(len(ar.entries) == ar.row_count - 1 and len(ar.entries) != n_dc,
          f"and len(entries) is {len(ar.entries):,}, one less -- a list length, "
          f"NOT a row count; quoting it against datcheck's is what produced "
          f"the '177,334 vs 177,335' reading in crossbuild FINDINGS 4b.1")

    bad, agree = agreement(ar.entries, mft, ar.row_of_position)
    check(bad == 0,
          f"entries[k] == raw MFT row k+1 on all 24 bytes, read by a struct "
          f"walker written in this file: {bad} mismatches over "
          f"{len(ar.entries):,} rows")

    # ...and the SAME sweep through datcheck's own accessor, which is what the
    # line above claims and did not do. See `datcheck_read_row`.
    bad_dc, _ = agreement(ar.entries, mft, ar.row_of_position,
                          read=datcheck_read_row)
    check(bad_dc == 0,
          f"and through datcheck.row_bytes ITSELF -- not a walker written here: "
          f"{bad_dc} mismatches over {len(ar.entries):,} rows, so a datcheck "
          f"that changed convention reddens this line and not only its neighbours")

    # THE CONTROL. The off-by-one reading -- the one FINDINGS 4b.1 describes as
    # datcheck's -- must NOT agree, except on the all-zero reserved spares.
    bad_off, agree_off = agreement(ar.entries, mft, lambda k: k)
    zeros = [r for r in agree_off if read_row(mft, r) == (0, 0, 0, 0, 0, 0)]
    check(bad_off == len(ar.entries) - 11 and len(agree_off) == 11
          and len(zeros) == 11,
          f"and the off-by-one reading agrees on only {len(agree_off)} rows, "
          f"all {len(zeros)} of them all-zero reserved spares (rows "
          f"{min(agree_off) if agree_off else '-'}..{max(agree_off) if agree_off else '-'}) "
          f"-- {bad_off:,} disagree, so the two readings are distinguishable")

    check(all(ar.row_of_position(k) == ar.entries[k].index
              and ar.position_of_row(ar.entries[k].index) == k
              for k in (0, 1, 15, len(ar.entries) - 1)),
          "row_of_position and position_of_row round-trip and both agree with "
          "Entry.index at both ends")

    # BOTH ENDS, and the high end is the one that shipped open. The first
    # version of this pair was two PURE functions -- `row - 1` with a low-end
    # refusal -- which cannot see the top of the table at all: a review measured
    # `position_to_row(len(entries))` handing back row 177,342 on an archive
    # whose highest row is 177,341, and `row_label` printing it without a
    # complaint. They are Archive METHODS now, so the bound exists.
    last_pos = len(ar.entries) - 1
    bounds = ((ar.position_of_row, 0), (ar.position_of_row, -1),
              (ar.position_of_row, ar.row_count),
              (ar.row_of_position, -1), (ar.row_of_position, last_pos + 1))
    refused = 0
    for call, arg in bounds:
        try:
            call(arg)
        except IndexError:
            refused += 1
    check(refused == len(bounds),
          f"both conversions refuse BOTH ends ({refused}/{len(bounds)}): rows "
          f"0/-1 and {ar.row_count:,}, positions -1 and {last_pos + 1:,} -- the "
          f"low ones resolve to a real row at the far END of the table, the high "
          f"ones MINT a row number the archive does not have")

    # A fractional row number is always a bug upstream, and `%d` renames it to a
    # DIFFERENT, real row rather than complaining: `row_label(1.5)` printed
    # `row 1`. Measured before the guard existed.
    typed = 0
    for call, arg in ((ar.position_of_row, 1.5), (ar.row_of_position, 1.5),
                      (archive_mod.row_label, 1.5),
                      (archive_mod.mft_row_offset, None)):
        try:
            call(arg) if call is not archive_mod.mft_row_offset else call(0, 1.5)
        except TypeError:
            typed += 1
    check(typed == 4,
          f"and all four refuse a non-int row ({typed}/4) -- `row_label(1.5)` "
          f"printed `row 1`, which is the one thing a labeller must never do")

    # THE BYTE ADDRESS, which is the other half of the convention and the half
    # that was actually wrong in shipped code. `datplan.py` computed
    # `mft_offset + (row - 1) * 24` at three sites while printing "MFT row N",
    # so the control is that exact expression: it must land on the PREVIOUS
    # row's bytes for every row tested, or the two are indistinguishable here.
    probe = [datcheck.MFT_SELF_ROW, datcheck.FILE_ID_TABLE_ROW,
             archive_mod.FIRST_CLAIMABLE_ROW, len(ar.entries)]
    right = sum(1 for r in probe
                if bytes_at(path, archive_mod.mft_row_offset(ar.mft_offset, r),
                            24) == datcheck.row_bytes(mft, r))
    wrong = sum(1 for r in probe
                if bytes_at(path, ar.mft_offset + (r - 1) * 24, 24)
                == datcheck.row_bytes(mft, r - 1))
    check(right == len(probe) and wrong == len(probe),
          f"mft_row_offset lands on row N's own 24 bytes for rows {probe} "
          f"({right}/{len(probe)}), and the `- 1` expression datplan shipped "
          f"lands on row N-1's ({wrong}/{len(probe)}) -- the two are "
          f"distinguishable, which is why the planner's three sites were silent")
    check(datwrite.row_offset(ar, datcheck.MFT_SELF_ROW)
          == archive_mod.mft_row_offset(ar.mft_offset, datcheck.MFT_SELF_ROW),
          "and datwrite.row_offset is that same function, not a second copy of "
          "the expression")

    # datcheck's named reserved rows, resolved through archive.row(). Two
    # assertions the archive itself can refute: the MFT row must describe the
    # table the HEADER names, and the id-table row must parse as (id, row) pairs.
    mft_row = row_or_none(ar, datcheck.MFT_SELF_ROW)
    check(mft_row is not None and mft_row.offset == ar.mft_offset
          and mft_row.size == ar.mft_size,
          f"archive.row(datcheck.MFT_SELF_ROW={datcheck.MFT_SELF_ROW}) is the "
          f"MFT the header names "
          f"({'refused' if mft_row is None else f'0x{mft_row.offset:X}, {mft_row.size:,} B'})")
    id_row = row_or_none(ar, datcheck.FILE_ID_TABLE_ROW)
    check(id_row is not None and id_row.size % 8 == 0
          and id_row.size // 8 > 100000,
          f"archive.row(datcheck.FILE_ID_TABLE_ROW="
          f"{datcheck.FILE_ID_TABLE_ROW}) is the file-id table "
          f"({'refused' if id_row is None else f'{id_row.size // 8:,} pairs'})")

    # ------------------------------------------------ the labelled identity --
    # Selected by FLAGS, never by a row constant, so this runs on any copy and
    # the thing under test is not also the selector.
    records, _blob = datcheck.file_id_records(path, mft, datcheck.read_header(path))
    ident = datcheck.row_identity(mft, records)
    head = next(e for e in ar.entries if e.flags == MAP_FLAGS)
    partner_row = read_row(mft, head.index)[4]        # alloc.nextStream at +0x10
    check(ident[head.index]["role"] == "stream head"
          and ident[head.index]["file_ids"],
          f"row_identity names {archive_mod.row_label(head.index, ident[head.index]['file_ids'], ident[head.index]['role'])}"
          f" -- a map head selected by flags {MAP_FLAGS} alone")
    check(ident[partner_row]["role"] == f"stream partner of row {head.index}",
          f"and its partner is {archive_mod.row_label(partner_row, ident[partner_row]['file_ids'], ident[partner_row]['role'])}"
          f" -- the pair a bare row number cannot tell apart")

    # THE FILE ID IS THE LABEL'S LOAD-BEARING HALF, so it gets the oracle. The
    # role above is checked against a strong predicate and the id was checked
    # only for being non-empty -- which a `row_identity` reading the id column
    # one row late SURVIVES, measured, with every other check in this section
    # green. That is the exact defect class this file exists for, so the id is
    # now resolved BACK through `archive.file_id_table`: a different
    # implementation on a different read path (the Archive decompressor, versus
    # the raw seek `file_id_records` does), which must send every id to the row
    # `row_identity` filed it under. A label that names the wrong file is worse
    # than a bare number, because it reads as identification.
    tbl = file_id_table(ar)
    labelled = [r for r in ident if ident[r]["file_ids"]]
    n_ids = sum(len(ident[r]["file_ids"]) for r in labelled)
    astray = [(r, f) for r in labelled for f in ident[r]["file_ids"]
              if tbl.get(f) != r]
    check(not astray and n_ids > 100000,
          f"every one of {n_ids:,} file ids over {len(labelled):,} labelled rows "
          f"resolves back to its own row through archive.file_id_table -- "
          f"{len(astray)} astray{'' if not astray else ' ' + str(astray[:4])}")

    # THE SABOTAGE, built and run: an identity map read one row late. It is the
    # exact defect this section is about, applied to the labels rather than to
    # the entries, and it must move BOTH answers above. Without it, "the head is
    # labelled a head" is satisfied by any archive where heads outnumber
    # everything else.
    shifted = {r: ident[r + 1] for r in ident if r + 1 in ident}
    shifted_astray = sum(1 for r in labelled if r in shifted
                         for f in shifted[r]["file_ids"] if tbl.get(f) != r)
    check(shifted_astray > 1000
          and (shifted.get(partner_row, {}).get("role")
               != f"stream partner of row {head.index}"),
          f"and an identity map read one row late sends {shifted_astray:,} ids "
          f"to the wrong row and mislabels the pair -- so the two checks above "
          f"are facts about these rows, not about the population")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dat", default=DEFAULT_DAT)
    args = ap.parse_args()

    if not os.path.exists(args.dat):
        print(f"no archive at {args.dat}")
        print("See RUNBOOK.md for how the study copy is made.")
        return 1

    print(f"archive: {args.dat}")
    with Archive(args.dat) as ar:
        print("\n1. the header cross-checks itself")
        # Archive() already raises if count * 24 != mft_size, so reaching here
        # is the check. Restate it so a reader sees the arithmetic.
        check(ar.entry_count * 24 == ar.mft_size,
              f"{ar.entry_count} entries x 24 == declared MFT size "
              f"{ar.mft_size}")
        check(ar.block_size == 512, f"block size is 512 (got {ar.block_size})")

        # ROW NUMBER vs POSITION. `entries` is positional and `row()` is
        # one-based, and confusing them returns a DIFFERENT FILE rather than an
        # error -- on 2026-08-13 that silently resolved a text row to a texture
        # and nearly produced a false refutation. Both conventions are pinned
        # here so neither can drift into the other.
        print("\n1b. row numbers are one-based; entries is positional")
        check(ar.entries[0].index == 1 and ar.entries[9].index == 10,
              "entries[k].index == k + 1 -- the list is POSITIONAL")
        last = len(ar.entries)
        # `row()` carries its own assert that the row it resolved is the row it
        # was asked for, and an AssertionError here is a BaseException-adjacent
        # exit: it kills the run before `LEDGER.verdict()` and prints no banner,
        # no floor and no ledger. MEASURED -- the sabotage that sets
        # `Entry.index = k` reddens this line and the process then dies on the
        # next `row()` call with a traceback, which is the one failure
        # `checks.py` cannot see. Caught, so a broken reader still gets a
        # verdict; the same trap `vaultpath.require_dir` set for
        # `test_stripbuild.py`.
        try:
            row_n_ok = (ar.row(1).index == 1 and ar.row(10).index == 10
                        and ar.row(last).index == last)
        except AssertionError as exc:
            row_n_ok = False
            print(f"   row() refused its own resolution: {exc}")
        check(row_n_ok, f"row(n).index == n at both ends (1..{last:,})")
        check(last == ar.entry_count - 1,
              f"and entry_count ({ar.entry_count:,}) COUNTS the MFT header "
              f"slot, so the highest row is one less ({last:,}) -- bounding on "
              f"entry_count walks off the end, which is how this was found")
        try:
            same_object = ar.row(2) is ar.entries[1]
        except AssertionError:
            same_object = False
        check(same_object,
              "row(n) and entries[n - 1] are the SAME object -- the existing "
              "call sites that write entries[row - 1] are correct")
        refused = 0
        for bad in (0, -1, last + 1):
            try:
                ar.row(bad)
            except IndexError:
                refused += 1
        check(refused == 3,
              f"row(0), row(-1) and row(last + 1) are all refused ({refused}/3) "
              f"-- a negative index would otherwise wrap to the END of the table")
        # The file-id table's row, MEASURED rather than assumed: it is the only
        # row whose payload parses wholly as (file_id, row) pairs.
        idtable = row_or_none(ar, 2)
        blob = ar.read(idtable) if idtable is not None else b""
        pairs = len(blob) // 8
        good = sum(1 for i in range(min(pairs, 4000))
                   if 0 < struct.unpack_from("<II", blob, i * 8)[1] <= last)
        check(pairs > 100000 and good == min(pairs, 4000),
              f"MFT row 2 is the file-id table: {pairs:,} pairs, "
              f"{good}/{min(pairs, 4000)} rows in range")

        print("\n1c. datcheck.py numbers rows the SAME way, over the whole table")
        section_1c(ar, args.dat)

        print("\n2. map files are identifiable by flags alone")
        maps = [e for e in ar.entries if e.flags == MAP_FLAGS]
        check(len(maps) == EXPECTED_MAP_COUNT,
              f"exactly {EXPECTED_MAP_COUNT} entries carry flags "
              f"{MAP_FLAGS} (got {len(maps)})")
        if not maps:
            print("\nno map entries; nothing further to check")
            return LEDGER.verdict()

        print("\n3. every sampled map decompresses and tiles its chunk table")
        print("   (independent of the declared output length -- see the header)")
        t0 = time.time()
        walked = 0
        for e in maps[:SAMPLE_SIZE]:
            try:
                data = ar.read(e)
            except Exception as exc:
                check(False, f"row {e.index}: read raised {type(exc).__name__}")
                continue
            if bytes(data[:4]) != b"ffna":
                check(False, f"row {e.index}: magic {bytes(data[:4])!r}, "
                             f"expected b'ffna'")
                continue
            if ffna_type(data) != FFNA_TYPE_MAP:
                check(False, f"row {e.index}: ffna type {ffna_type(data)}, "
                             f"expected {FFNA_TYPE_MAP}")
                continue
            try:
                chunks = list(ffna_chunks(data))
            except ValueError as exc:
                check(False, f"row {e.index}: chunk walk failed -- {exc}")
                continue
            walked += 1
            check(True, f"row {e.index}: {len(chunks)} chunks tiling "
                        f"{len(data)} bytes exactly")
        print(f"   {walked}/{min(SAMPLE_SIZE, len(maps))} maps in "
              f"{time.time() - t0:.0f}s")

        print("\n4. reference maps reproduce byte for byte")
        if ar.entry_count != EXPECTED_ENTRY_COUNT:
            LEDGER.skip("reference maps",
                        f"this archive has {ar.entry_count} entries, not "
                        f"{EXPECTED_ENTRY_COUNT}; row indices differ between "
                        "copies")
        else:
            # RAISE the floor by what this section is about to contribute. Only
            # ever upward, and only when the section can actually run: the
            # module-level floor is 31 because that is what a run on ANY copy
            # scores, and leaving it there on a 177,342-row copy would hand
            # `dat_study` two checks of slack -- room for exactly the silent
            # deletion the 26 -> 31 raise was made to close, one size smaller.
            LEDGER.floor += len(REFERENCE_MAPS)
            by_index = {e.index: e for e in maps}
            for row, (want_chunks, want_bytes) in REFERENCE_MAPS.items():
                e = by_index.get(row)
                if e is None:
                    check(False, f"row {row} is not a map entry in this archive")
                    continue
                data = ar.read(e)
                chunks = list(ffna_chunks(data))
                check(len(data) == want_bytes and len(chunks) == want_chunks,
                      f"row {row}: {len(chunks)} chunks, {len(data)} bytes "
                      f"(expected {want_chunks}, {want_bytes})")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
