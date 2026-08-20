"""Census every row of an archive, and say WHICH CONVENTION counted it.

TWO CENSUSES OF THE SAME ARCHIVE DISAGREED BY SIXTEEN ROWS AND NOBODY COULD SAY
WHY. `studies/archivewrite/FINDINGS.md`'s correction C-8: "Two row censuses
disagree by 16: 138,708 comp-8 rows (Route E) vs 138,692 (Route C skeptic),
against 38,621+12 vs 38,629 comp-0. The sums are 177,341 and 177,321 --
`len(entries)` versus live rows." That is not a rounding argument: the published
"661 of 138,708 compression-8 rows are unwritable stored" carries its own caveat
that the figure rests on the trailing declared size for 138,692 of them, so the
disputed sixteen sit in the denominator of a headline.

The disagreement is not a bug in either walk. It is what happens when two people
count "rows" without saying which rows, and this archive offers at least four
honest answers to that question:

    row_count        the raw MFT, COUNTING the descriptor at row 0
    len(entries)     one less, because `entries` skips the descriptor
    USED rows        the ones the allocator considers live
    USED and >= 16   the ones a writer may actually touch

`archive.py`'s `row_count` docstring already warns about the first two -- it
names the "177,334 vs 177,335" pair a previous study filed as evidence that two
tools numbered rows differently. They did not. Nothing warns about the other two,
and a comp-8-coded row that is USED-clear is counted by one walk and dropped by
the next while both are telling the truth.

So this module refuses to have a favourite. It walks the rows ONCE, gives every
row a CLASS, and reports the count under EVERY convention side by side, with the
difference between each pair DECOMPOSED into the classes that account for it.
"138,708 vs 138,692" stops being a contradiction the moment the sixteen have a
name. **No historical number is hardcoded anywhere below** -- reproducing them,
or failing to, is what a run against the real archive MEASURES, and
`test_datledger.py` section 7a is that run: it holds C-8's two triples as
literals, censuses two real copies, and asserts the decomposition closes.
`test_datledger.py` section 3b enforces the split by walking this file's own
syntax tree -- the figures may appear in the paragraph above, which is the
citation, and in no other literal.

WHAT THAT RUN FOUND, 2026-08-20, and it is the reason to read the conventions
block rather than any single count. MEASURED: the study copy under the `entries`
convention reproduces C-8's larger census EXACTLY, comp-0 and comp-8 and sum, and
its comp-0 figure was already written as a sum ("38,621+12") whose +12 is
precisely the twelve erased structural rows the `used` convention drops. The
pristine install copy under the `used` convention reproduces the smaller SUM
exactly, with the compression split one row from what was reported. So the
twenty rows are SEVEN of archive difference plus THIRTEEN of convention, and the
sixteen comp-8 rows are FIFTEEN of archive difference plus one. RECONSTRUCTION,
labelled as such: that the two routes read those two copies is a hypothesis that
fits every number and is not recorded anywhere -- what is measured is that no
single archive and no single convention produces both censuses, and that the
gap closes when you allow both to differ.

MEASURED 2026-08-20 on `vault/dat_study/Gw.dat`: the whole table censused in
about three seconds, and `--json` of every row is a 29.8 MB artifact. The census
reads the MFT and the file-id table and nothing else -- no payload is touched, so
the cost is the table, not the archive.

    python toolkit/mapdata/datledger.py --dat COPY
    python toolkit/mapdata/datledger.py --dat COPY --summary
    python toolkit/mapdata/datledger.py --dat COPY --json vault/.../ledger.json
    python toolkit/mapdata/datledger.py --dat COPY --reencode 11196 13738

THE CLASSES, in the order the ladder tries them. The order is the design: a row
is placed by what it IS before it is placed by how it is ENCODED, because the
encoding field of a row with no extent describes nothing.

    structural   row < 16 -- the descriptor's neighbours: the file header (1),
                 the file-id table (2), the MFT's own row (3), and the twelve
                 erased rows 4..15 a working allocator declines to use
    spare        USED clear, size 0 -- a genuinely claimable slot
    armed        USED, size 0 -- a live head whose extent was released on
                 purpose, e.g. a map head `deploy.py` arms so the client
                 recompiles it. `datplan.free_rows` tested `size == 0` alone
                 until 2026-08-15 and offered one of these as claimable.
    stored       compression 0
    comp8        compression 8
    other-comp   any other code, with the code reported beside the count

and `renamed` is a FLAG ON TOP OF THE CLASS, not a class: a bit-31 file id
naming the row means its replacement is pending (see `bit31.py`), which is
orthogonal to what the row holds.

A ROW WHOSE RULES DISAGREE IS REPORTED, NEVER SILENTLY BUCKETED. The ladder
always terminates, so every row lands somewhere -- and that is exactly how a
census tells a comfortable lie. A USED-clear row that still declares an extent is
not a spare and not armed; it falls through to `stored`/`comp8` and gets counted
as live by any walk that keys on compression alone. That row is the C-8 mechanism
in one line. So each row also carries `anomalies`: the ways its own fields
contradict the bucket it landed in. They are counted in the summary and printed
on the headline, and `test_datledger.py` plants each one.

WHAT IS NOT COMPUTED HERE. Measured comp-8 headroom -- what a row's payload would
occupy if we re-encoded it with `gwenc` -- is the number an author actually wants
when asking "can I write a bigger file into this row". It is not in the census
because it costs a full decode plus a full encode per row, at roughly 0.19 MB/s;
over a 4.2 GB archive that is not a slow census, it is a census nobody ever runs
to completion. `reencoded_size()` and `--reencode ROW ...` answer it for named
rows, on demand, and print the seconds they took.

THE JSON IS A VAULT ARTIFACT and it is derived from the owner's own archive, so
`--json` refuses the install, `vault/dat_study` and every checkout of this repo
-- `bit31.resolve_out` is imported rather than copied, because that refusal list
is one fact and it has already been reintroduced-as-a-habit once. Every ledger
carries a STAMP (size on disk, MFT offset/size/row count, and the sha256 of the
MFT bytes); `check_stamp()` is what a later consumer calls to find out that the
archive moved under its ledger. The stamp deliberately does NOT compare the path:
a copy under another name is a legitimate thing to census, and refusing it would
make the guard the reason nobody uses the tool.

Exit codes follow `datcheck.py` and `bit31.py`, minus the middle one: 0 the
census ran, 2 refused or unreadable. There is no exit 1 here, because a census is
not a comparison -- nothing this tool prints is a verdict about whether an
archive changed. Ask `datcheck --diff` or `bit31 --diff` that.

EVERY PHASE OF A RUN NAMES ITSELF, and that is a correction rather than a
flourish. A run does up to four separable things -- resolve the `--json`
destination, census, write the ledger, re-encode named rows -- and until
2026-08-20 a failure in ANY of them was printed by one last-resort handler as
"could not census DAT". So `--reencode 9999` printed the whole census, headline
and classes and slack, and then announced that the archive could not be read: a
false statement about the archive, made after the census had already disproved
it, wearing the exit code a script reads as "unreadable file". `_phase()` is the
fix -- each phase labels its own failure, and the last-resort handler no longer
claims to know which one broke. `Refused` is a `SystemExit` rather than an
`Exception`, which is what lets a phase sit inside another phase and still be
the one that reports.

Reads the archive 'rb' through `archive.Archive` and nothing else.
"""

import argparse
import contextlib
import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import (Archive, COMPRESSION_HUFFMAN,      # noqa: E402
                     COMPRESSION_STORED, FILE_ID_HIGH_BIT,
                     FIRST_CLAIMABLE_ROW, FLAG_ENTRY_USED, FLAG_FIRST_STREAM,
                     MFT_SELF_ROW, file_id_table)
from atex import Refused                                # noqa: E402
from bit31 import resolve_out                           # noqa: E402
# `reservation_for` is IMPORTED, not re-derived. It is four characters of
# arithmetic and it has three homes already (`datmove`, `datwrite`, and
# `datplan.blocks_for`); a fourth copy is how a census and a writer come to
# disagree about what a row was given. `datwrite`'s is the one to take -- it
# imports only `archive` and `gwdat`, where `datmove`'s drags in `datplan`.
from datwrite import reservation_for                    # noqa: E402

FORMAT_VERSION = 1

CLASS_STRUCTURAL = "structural"
CLASS_SPARE = "spare"
CLASS_ARMED = "armed"
CLASS_STORED = "stored"
CLASS_COMP8 = "comp8"
CLASS_OTHER_COMP = "other-comp"

# The ladder's order, published so a reader does not have to infer it from an
# if-chain and so the summary can print classes in a stable order rather than
# whatever order the archive happened to present them in.
CLASSES = (CLASS_STRUCTURAL, CLASS_SPARE, CLASS_ARMED, CLASS_STORED,
           CLASS_COMP8, CLASS_OTHER_COMP)

# Every way a row's own fields can contradict the bucket the ladder gave it,
# with the sentence that says why it matters. The dict is the documentation: a
# new anomaly without a reason here is a name nobody can act on.
ANOMALY_WHY = {
    "used-clear-with-extent":
        "USED is clear but the row still declares an extent -- it is neither a "
        "spare nor armed, so it falls through to stored/comp8 and any walk "
        "keyed on compression alone counts it as live",
    "zero-size-with-compression":
        "size 0 with a non-zero compression code -- an encoding declared for "
        "bytes that do not exist",
    "used-clear-but-named":
        "USED is clear and the file-id table still names this row -- "
        "datcheck's rule 10 refuses this; an allocator claiming it would "
        "silently rebind a live id",
    "unaligned-extent":
        "the extent does not start on a block boundary, so its reservation is "
        "not the block-rounded interval this ledger reports",
    "extent-past-eof":
        "offset + size runs past the end of the file -- the row cannot be read",
    "structural-not-erased":
        "a row in 4..15 is not all-zero; those twelve are reserved and every "
        "archive on this machine keeps them erased",
}

# How many rows a summary names for a thing that could be true of thousands.
# A summary that inlines 138,708 row numbers is a census, not a summary.
LARGEST_SLACK_ROWS = 20
ANOMALY_SAMPLE = 20


class Row:
    """One MFT row, as the census sees it. Addressed by RAW one-based index."""

    __slots__ = ("index", "offset", "size", "compression", "flags", "counter",
                 "crc", "reservation", "slack", "file_ids", "renamed", "cls",
                 "anomalies")

    def __init__(self, e, block, archive_bytes, file_ids):
        self.index = e.index
        self.offset = e.offset
        self.size = e.size
        self.compression = e.compression
        self.flags = e.flags
        self.counter = e.counter
        self.crc = e.crc
        self.reservation = reservation_for(e.size, block)
        self.slack = self.reservation - e.size
        self.file_ids = tuple(file_ids)
        self.renamed = any(f & FILE_ID_HIGH_BIT for f in file_ids)
        self.cls = classify(e)
        self.anomalies = tuple(anomalies_of(e, block, archive_bytes, file_ids))

    @property
    def used(self):
        return bool(self.flags & FLAG_ENTRY_USED)

    @property
    def first_stream(self):
        return bool(self.flags & FLAG_FIRST_STREAM)

    def as_dict(self):
        """The JSON form. Empty fields are omitted -- 177,000 `"renamed": false`
        entries are 3 MB of a file saying nothing."""
        out = {"index": self.index, "offset": self.offset, "size": self.size,
               "compression": self.compression, "flags": self.flags,
               "counter": self.counter, "crc": self.crc,
               "reservation": self.reservation, "slack": self.slack,
               "class": self.cls}
        if self.file_ids:
            out["file_ids"] = list(self.file_ids)
        if self.renamed:
            out["renamed"] = True
        if self.anomalies:
            out["anomalies"] = list(self.anomalies)
        return out

    def __repr__(self):
        return (f"<Row {self.index} {self.cls} {self.size}B "
                f"slack {self.slack}>")


def classify(e):
    """The class ladder. Structure first, then liveness, then encoding.

    ORDER IS THE DESIGN, and the middle rung is the one with history: an ARMED
    head (USED set, size 0) and a genuine SPARE (USED clear, size 0) are the same
    row to any test that asks `size == 0` alone, which is exactly what
    `datplan.free_rows` asked until 2026-08-15 -- it offered row 71496 of
    `vault/dat_c2/Gw.dat`, the live head of map 143, as a claimable slot.
    """
    if e.index < FIRST_CLAIMABLE_ROW:
        return CLASS_STRUCTURAL
    if e.size == 0:
        return CLASS_ARMED if e.flags & FLAG_ENTRY_USED else CLASS_SPARE
    if e.compression == COMPRESSION_STORED:
        return CLASS_STORED
    if e.compression == COMPRESSION_HUFFMAN:
        return CLASS_COMP8
    return CLASS_OTHER_COMP


def anomalies_of(e, block, archive_bytes, file_ids):
    """Every way this row's fields contradict the bucket the ladder gave it.

    Read `ANOMALY_WHY` for what each one means. This is the part of the census
    that can say "I put this row somewhere, and I am not confident about it" --
    without it the ladder's total is always tidy and always complete, which is
    the shape of a check that cannot fail.
    """
    used = bool(e.flags & FLAG_ENTRY_USED)
    out = []
    if e.size and not used:
        out.append("used-clear-with-extent")
    if not e.size and e.compression:
        out.append("zero-size-with-compression")
    if not used and file_ids:
        out.append("used-clear-but-named")
    if e.size and block and e.offset % block:
        out.append("unaligned-extent")
    if e.size and e.offset + e.size > archive_bytes:
        out.append("extent-past-eof")
    if (MFT_SELF_ROW < e.index < FIRST_CLAIMABLE_ROW
            and any((e.offset, e.size, e.compression, e.flags, e.counter,
                     e.crc))):
        out.append("structural-not-erased")
    return out


class Ledger:
    """One archive's rows, censused once, plus the identity that dates them.

    NAME COLLISION, STATED RATHER THAN RENAMED: `toolkit/checks.py` also has a
    `Ledger`, and it counts test checks. They meet in `test_datledger.py`, where
    one is `checks.Ledger` and the other is `datledger.census(ar)`. Both names
    are right in their own file and neither is worth bending -- this one is the
    capacity ledger of an archive, which is what the module is called.
    """

    __slots__ = ("archive", "size_on_disk", "block_size", "mft_offset",
                 "mft_size", "mft_sha256", "row_count", "rows", "_by_index")

    def __init__(self, ar, rows):
        self.archive = os.path.abspath(ar.path)
        self.size_on_disk = os.path.getsize(ar.path)
        self.block_size = ar.block_size
        self.mft_offset = ar.mft_offset
        self.mft_size = ar.mft_size
        self.mft_sha256 = mft_sha256(ar)
        self.row_count = ar.row_count
        self.rows = rows
        self._by_index = {r.index: r for r in rows}

    def row(self, n):
        """The censused row `n`, by RAW one-based MFT index.

        Deliberately a lookup and not `rows[n - 1]`: the positional/row-number
        confusion is the whole subject of this module, and it would be absurd
        for the census itself to ship an off-by-one.
        """
        try:
            return self._by_index[n]
        except KeyError:
            raise IndexError(
                f"MFT row {n} was not censused. This ledger holds rows "
                f"1..{self.row_count - 1}; row 0 is the MFT descriptor and is "
                f"counted by `row_count` but is not a file.")

    def __len__(self):
        return len(self.rows)


def mft_sha256(ar):
    """The hash of the MFT bytes -- the thing that makes a ledger stale.

    Not the whole file: a 4.2 GB sha256 is seconds rather than milliseconds, and
    every fact in this ledger comes from the table. A payload byte changing under
    a row whose MFT entry did not move is invisible to this hash BY DESIGN -- the
    entry crc is what covers that, and `datcheck --crc-sweep` is what checks it.
    """
    ar.fh.seek(ar.mft_offset)
    blob = ar.fh.read(ar.mft_size)
    if len(blob) != ar.mft_size:
        raise Refused(
            f"{ar.path}: the MFT declares {ar.mft_size} B at "
            f"0x{ar.mft_offset:X} and only {len(blob)} could be read.\n"
            f"  A ledger stamped with a short read would compare equal to "
            f"nothing and unequal to everything.\n"
            f"  Run `python toolkit/mapdata/datcheck.py --dat {ar.path} "
            f"--preflight` to see what is wrong with the file.")
    return hashlib.sha256(blob).hexdigest()


def identity(ar):
    """The stamp: everything a later reader needs to know the ledger is stale."""
    return {"archive": os.path.abspath(ar.path),
            "size_on_disk": os.path.getsize(ar.path),
            "mft_offset": ar.mft_offset,
            "mft_size": ar.mft_size,
            "row_count": ar.row_count,
            "mft_sha256": mft_sha256(ar)}


# The stamp fields a mismatch REFUSES on. `archive` is recorded and deliberately
# absent: censusing a copy under another name is a legitimate thing to do (it is
# how the cross-copy tables in `bit31.py` were measured), and a guard that
# refuses it is a guard people route around.
STAMP_FIELDS = ("size_on_disk", "mft_offset", "mft_size", "row_count",
                "mft_sha256")


def stamp(led):
    """The stamp of an in-memory ledger, in the same shape `identity` returns."""
    return {"archive": led.archive, "size_on_disk": led.size_on_disk,
            "mft_offset": led.mft_offset, "mft_size": led.mft_size,
            "row_count": led.row_count, "mft_sha256": led.mft_sha256}


def check_stamp(doc, ar):
    """Refuse if `doc` (a loaded ledger, or a stamp) is stale against `ar`.

    THE CONSUMER'S ENTRY POINT, and the reason it is not a CLI verb: this tool's
    exit codes are 0 and 2, and "the archive moved under the ledger" is neither
    "it ran" nor "it could not be read". A ledger is read by a later tool that
    is about to act on it -- and that tool is where the refusal belongs, in the
    shape `vaultpath.require_dir` uses: raise, rather than hand back a fixture
    that silently answers for the wrong archive.
    """
    have = doc.get("stamp", doc)
    now = identity(ar)
    for field in STAMP_FIELDS:
        if have.get(field) != now[field]:
            raise Refused(
                f"this ledger is stale against {ar.path}\n"
                f"  {field}: ledger says {have.get(field)!r}, the archive says "
                f"{now[field]!r}\n"
                f"  The ledger was taken from {have.get('archive')!r}"
                + (" (the same path)"
                   if have.get("archive") == now["archive"] else "") + ".\n"
                f"  Re-take it: python toolkit/mapdata/datledger.py --dat "
                f"{ar.path} --json <out>")
    return now


def census(ar):
    """Walk every row of `ar` once. -> `Ledger`.

    ROWS 1..row_count-1, THROUGH `ar.row(i)`. Not `for e in ar.entries`, which
    is the walk every other tool in this directory uses and which is correct --
    but this module's entire subject is that `len(entries)` and `row_count` are
    different numbers, so it addresses rows the way the repo says to address
    rows and derives the count from the header rather than from a list length.
    `ar.row()` asserts `e.index == n` on every lookup, which makes the walk its
    own witness that the two conventions line up the way this docstring claims.

    The file-id table is read RAW (`file_id_table(ar, raw=True)`) -- the form the
    CLIENT can address. The convenience form registers a masked alias for every
    bit-31 id, and a census built on it would report a renamed row as carrying
    two names, one of which the client cannot resolve.
    """
    try:
        table = file_id_table(ar, raw=True)
    except Exception as exc:                                   # noqa: BLE001
        raise Refused(
            f"{ar.path}: the file-id table (MFT row 2) could not be read: "
            f"{type(exc).__name__}: {exc}\n"
            f"  Without it every row would be censused as unnamed and the "
            f"`renamed` flag would read false everywhere, which is a confident "
            f"wrong answer rather than a missing one.\n"
            f"  Run `python toolkit/mapdata/datcheck.py --dat {ar.path} "
            f"--preflight` first.")
    by_row = {}
    for fid, row in table.items():
        by_row.setdefault(row, []).append(fid)
    for ids in by_row.values():
        ids.sort()

    block = ar.block_size
    archive_bytes = os.path.getsize(ar.path)
    empty = ()
    rows = [Row(ar.row(i), block, archive_bytes, by_row.get(i, empty))
            for i in range(1, ar.row_count)]
    return Ledger(ar, rows)


def _by_compression(rows):
    """{compression code as a string: count}. The code is the key, not a name --
    `other-comp` collapses every unknown code into one class, and this is where
    the codes themselves survive."""
    out = {}
    for r in rows:
        k = str(r.compression)
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))


def _ordered(counts):
    """`CLASSES` first for a stable report, then ANYTHING ELSE. Never dropped.

    The obvious spelling is a comprehension over `CLASSES`, and it is wrong in
    the one way this module is about: a class somebody adds to the ladder and
    forgets to register here would vanish from the totals -- silently, while
    every total still added up to something tidy. That is the same shape as the
    row the ladder buckets without a word. Unknown names sort to the end, where
    they are visible.
    """
    out = {c: counts[c] for c in CLASSES if c in counts}
    out.update(sorted((k, v) for k, v in counts.items() if k not in out))
    return out


def _by_class(rows):
    out = {}
    for r in rows:
        out[r.cls] = out.get(r.cls, 0) + 1
    return _ordered(out)


def _delta(name_from, rows_from, name_to, rows_to, why):
    """What the second convention drops, decomposed into classes and codes.

    This is the C-8 answer in one object: "the sixteen" stop being a
    contradiction the moment they are `{"spare": 14, "armed": 2}`.
    """
    keep = {r.index for r in rows_to}
    dropped = [r for r in rows_from if r.index not in keep]
    return {"from": name_from, "to": name_to, "rows": len(dropped), "why": why,
            "by_class": _by_class(dropped),
            "by_compression": _by_compression(dropped)}


def summary(led):
    """The counts, the slack, and the conventions block. -> dict.

    NOTHING HERE IS A VERDICT. Every number is reported under the name of the
    rule that produced it, and where two rules disagree the difference is
    itemised rather than resolved -- resolving it is a judgement about what
    somebody meant by "rows", and this tool does not have that information.
    """
    rows = led.rows
    used_rows = [r for r in rows if r.used]
    used16_rows = [r for r in used_rows if r.index >= FIRST_CLAIMABLE_ROW]

    other_codes = {}
    for r in rows:
        if r.cls == CLASS_OTHER_COMP:
            k = str(r.compression)
            other_codes[k] = other_codes.get(k, 0) + 1

    slack_by_class = {}
    for r in rows:
        slack_by_class[r.cls] = slack_by_class.get(r.cls, 0) + r.slack
    slack_by_class = _ordered(slack_by_class)

    largest = sorted(rows, key=lambda r: (-r.slack, r.index))
    largest = [r for r in largest if r.slack][:LARGEST_SLACK_ROWS]

    anomalies = {}
    for r in rows:
        for a in r.anomalies:
            rec = anomalies.setdefault(a, {"rows": 0, "first": [],
                                           "why": ANOMALY_WHY.get(a, "?")})
            rec["rows"] += 1
            if len(rec["first"]) < ANOMALY_SAMPLE:
                rec["first"].append(r.index)

    conventions = {
        "raw_rows": {
            "count": led.row_count,
            "by_compression": _by_compression(rows),
            "note": "the raw MFT, counting the descriptor at row 0. The +1 "
                    "over `entries` IS that descriptor: it holds no payload, "
                    "so it lands in no compression bucket and the two "
                    "conventions differ by one row and by zero in every code."},
        "entries": {
            "count": len(rows),
            "by_compression": _by_compression(rows),
            "note": "rows 1..row_count-1, which is what `len(archive.entries)` "
                    "returns and what a `for e in ar.entries` walk counts."},
        "used": {
            "count": len(used_rows),
            "by_compression": _by_compression(used_rows),
            "note": "FLAG_ENTRY_USED set. Spares and released rows drop out "
                    "here, INCLUDING any that still declare a compression "
                    "code."},
        "used_ge_16": {
            "count": len(used16_rows),
            "by_compression": _by_compression(used16_rows),
            "note": "USED and at or above FIRST_CLAIMABLE_ROW -- the rows a "
                    "writer may touch. Drops the three container rows and any "
                    "of 4..15 that are not erased."},
    }
    deltas = [
        # COMPUTED, not the literal 1 it always is today: the whole point of
        # this block is that a count somebody was sure about turned out to be a
        # convention, and writing `1` here would put this module's own walk
        # beyond the reach of its own arithmetic.
        {"from": "raw_rows", "to": "entries", "rows": led.row_count - len(rows),
         "why": "the MFT descriptor at row 0, which is a table header and not "
                "a file, so it is counted by `row_count` and censused by "
                "nothing",
         "by_class": {}, "by_compression": {}},
        _delta("entries", rows, "used", used_rows,
               "rows with FLAG_ENTRY_USED clear"),
        _delta("used", used_rows, "used_ge_16", used16_rows,
               "USED rows below FIRST_CLAIMABLE_ROW (16)"),
    ]

    return {
        "classes": _by_class(rows),
        "other_comp_codes": dict(sorted(other_codes.items(),
                                        key=lambda kv: int(kv[0]))),
        "renamed_rows": sum(1 for r in rows if r.renamed),
        "named_rows": sum(1 for r in rows if r.file_ids),
        "slack": {"total": sum(r.slack for r in rows),
                  "by_class": slack_by_class},
        "largest_slack": [{"index": r.index, "class": r.cls, "size": r.size,
                           "reservation": r.reservation, "slack": r.slack}
                          for r in largest],
        "anomalies": anomalies,
        "anomaly_rows": sum(1 for r in rows if r.anomalies),
        "conventions": conventions,
        "deltas": deltas,
    }


def to_json(led, sm=None):
    """The ledger as one JSON-able document, stamped."""
    return {"format_version": FORMAT_VERSION,
            "stamp": stamp(led),
            "block_size": led.block_size,
            "summary": sm if sm is not None else summary(led),
            "rows": [r.as_dict() for r in led.rows]}


def load(path):
    """A ledger read back off disk, shape-checked. -> dict, or `Refused`.

    Every check here is one a consumer would otherwise discover as a `KeyError`
    three calls later, pointing at its own code rather than at the stale file.
    Pair it with `check_stamp(doc, ar)`: this proves the document is a ledger,
    that proves it is a ledger about the archive in your hand.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise Refused(f"could not read {path}: {type(exc).__name__}: {exc}")
    if not isinstance(doc, dict):
        raise Refused(f"{path} is a {type(doc).__name__}, not a ledger object")
    if doc.get("format_version") != FORMAT_VERSION:
        raise Refused(
            f"{path} is format_version {doc.get('format_version')!r}, this "
            f"tool writes {FORMAT_VERSION}. Re-take the ledger rather than "
            f"read across formats.")
    st = doc.get("stamp")
    if not isinstance(st, dict):
        raise Refused(f"{path} has no 'stamp' object; it is not a ledger")
    for field in STAMP_FIELDS:
        if field not in st:
            raise Refused(f"{path}: the stamp is missing {field!r}, so nothing "
                          f"can tell whether it is stale")
    if not isinstance(doc.get("rows"), list):
        raise Refused(f"{path} has no 'rows' array; it is not a ledger")
    return doc


def reencoded_size(ar, row):
    """What row `row`'s payload would occupy re-encoded by `gwenc`. -> dict.

    ON DEMAND, NEVER IN BULK. Measured at roughly 0.19 MB/s, so this is the one
    question about an archive that cannot be a column in a 177,000-row census:
    the seconds are reported for every call precisely because the cost is the
    reason it lives out here.

    RETURNS A DICT, NOT THE BARE NUMBER ITS NAME PROMISES, and that is
    deliberate: `encoded` alone answers nothing. The question behind it is always
    "does it still fit", and that needs the row's reservation, which needs the
    block size -- a caller re-deriving that gets the rounding wrong, which is
    the whole reason `reservation_for` is imported at the top of this file.

    PROVES AGREEMENT WITH OUR ENCODER, NOT WITH ARENANET'S. `gwenc.encode`
    verifies its own output through `gwdat.decompress`; that both of ours agree
    is not evidence that the retail client would accept the stream. A8 is the
    only oracle (`datwrite.py`'s declaration_fault carries the same caveat).

    `declared_agrees` is worth reading and is not decoration. `gwdat.decompress`
    takes its output length from the stream's own trailer, so a stream that
    decodes SHORT does not raise -- it hands back fewer bytes and the row's crc,
    which is over the STORED bytes, still passes. That is FINDINGS C-6's shape,
    and this is the one place in a census where it becomes visible.

    THE THREE REFUSALS ARE ONE FAMILY, and the third was missing until
    2026-08-20: a row that is not compression 8, a row of size 0, and a row this
    archive does not have. The first two were house-style `Refused`; the third
    fell out of `ar.row()` as a bare `IndexError` and was printed by the CLI as
    "could not census". A mistyped row number is the likeliest of the three, so
    it now refuses in the same shape as its siblings -- carrying `archive.py`'s
    own bounds sentence rather than a second copy of the arithmetic, because
    "1..row_count-1" is exactly the confusion this module exists about and a
    duplicated bound is how the two would come to disagree.
    """
    import gwdat                                        # noqa: E402
    import gwenc                                        # noqa: E402

    try:
        e = ar.row(row)
    except IndexError as exc:
        raise Refused(
            f"row {row} is not a row of {ar.path}.\n"
            f"  This archive holds rows 1..{ar.row_count - 1}; row 0 is the "
            f"MFT descriptor, which `row_count` counts and which is not a "
            f"file.\n"
            f"  {exc}\n"
            f"  Run `python toolkit/mapdata/datledger.py --dat {ar.path} "
            f"--summary` to see which rows this archive has, and which of them "
            f"are compression 8.")
    if e.compression != COMPRESSION_HUFFMAN:
        raise Refused(
            f"row {row} is compression {e.compression}, not "
            f"{COMPRESSION_HUFFMAN}.\n"
            f"  There is nothing to re-encode: a stored row's payload IS its "
            f"stored bytes.\n"
            f"  Ask the ledger for its class -- this row is "
            f"'{classify(e)}'.")
    if e.size == 0:
        raise Refused(
            f"row {row} declares compression {COMPRESSION_HUFFMAN} and size 0, "
            f"so there are no bytes to decode.\n"
            f"  The census records this as the anomaly "
            f"'zero-size-with-compression'.")
    stored = ar.raw(e)
    if len(stored) != e.size:
        raise Refused(
            f"row {row} declares {e.size} B at 0x{e.offset:X} and only "
            f"{len(stored)} could be read.")
    # The clock covers the DECODE as well as the encode, because both are what
    # the caller pays for one answer -- timing only the half that is slower
    # would understate the verb and is how a cost gets argued down.
    t0 = time.perf_counter()
    plain, declared = gwdat.decompress(stored)
    data = gwenc.encode(plain)
    seconds = time.perf_counter() - t0
    res = reservation_for(e.size, ar.block_size)
    return {"row": row, "stored": e.size, "plain": len(plain),
            "declared": declared, "declared_agrees": declared == len(plain),
            "encoded": len(data), "reservation": res,
            "headroom": res - len(data), "delta": len(data) - e.size,
            "seconds": seconds}


# ------------------------------------------------------------------ reporting

def _n(x):
    return f"{x:,}"


def format_headline(led, sm):
    """The lines every run prints. Counts, slack, and what did not add up."""
    lines = [led.archive,
             f"  {_n(led.row_count)} raw rows (row_count), "
             f"{_n(len(led.rows))} censused (rows 1..{_n(led.row_count - 1)})",
             f"  block {_n(led.block_size)} B, MFT {_n(led.mft_size)} B at "
             f"0x{led.mft_offset:X}, {_n(led.size_on_disk)} B on disk",
             f"  mft sha256 {led.mft_sha256[:16]}..."]
    lines.append("  classes: " + ", ".join(
        f"{c} {_n(n)}" for c, n in sm["classes"].items()))
    if sm["other_comp_codes"]:
        lines.append("    other-comp codes: " + ", ".join(
            f"{k} x{_n(v)}" for k, v in sm["other_comp_codes"].items()))
    lines.append(f"  {_n(sm['named_rows'])} row(s) named by a file id, "
                 f"{_n(sm['renamed_rows'])} of them by a bit-31 (renamed) id")
    lines.append(f"  slack {_n(sm['slack']['total'])} B total: " + ", ".join(
        f"{c} {_n(n)}" for c, n in sm["slack"]["by_class"].items()))
    if sm["anomaly_rows"]:
        lines.append(f"  ANOMALIES on {_n(sm['anomaly_rows'])} row(s): "
                     + ", ".join(f"{k} {_n(v['rows'])}"
                                 for k, v in sorted(sm["anomalies"].items())))
    else:
        lines.append("  no anomalies: every row's fields agree with its class")
    return lines


def format_summary(sm):
    """The conventions block -- the part C-8 is about."""
    lines = ["", "  how many rows? -- one answer per convention"]
    for name, con in sm["conventions"].items():
        lines.append(f"    {name:<12} {_n(con['count']):>12}   by code: "
                     + ", ".join(f"{k}={_n(v)}"
                                 for k, v in con["by_compression"].items()))
        lines.append(f"                 {con['note']}")
    lines.append("")
    lines.append("  and what each convention drops relative to the one above")
    for d in sm["deltas"]:
        lines.append(f"    {d['from']} -> {d['to']}: {_n(d['rows'])} row(s) "
                     f"-- {d['why']}")
        if d["by_class"]:
            lines.append("      by class: " + ", ".join(
                f"{k} {_n(v)}" for k, v in d["by_class"].items()))
        if d["by_compression"]:
            lines.append("      by code:  " + ", ".join(
                f"{k}={_n(v)}" for k, v in d["by_compression"].items()))
    if sm["anomalies"]:
        lines.append("")
        lines.append("  anomalies, and why each one is one")
        for name, rec in sorted(sm["anomalies"].items()):
            lines.append(f"    {name} on {_n(rec['rows'])} row(s), first "
                         f"{rec['first']}")
            lines.append(f"      {rec['why']}")
    lines.append("")
    lines.append(f"  the {len(sm['largest_slack'])} row(s) with the most slack")
    for r in sm["largest_slack"]:
        lines.append(f"    row {r['index']:>8}  {r['class']:<11} "
                     f"{_n(r['size']):>12} B of {_n(r['reservation']):>12} B "
                     f"-> {_n(r['slack']):>8} B free")
    return lines


def format_reencode(rec):
    fit = "fits" if rec["headroom"] >= 0 else "OVERFLOWS"
    return [f"  row {rec['row']}: {_n(rec['stored'])} B stored -> "
            f"{_n(rec['plain'])} B plain -> {_n(rec['encoded'])} B re-encoded "
            f"({rec['seconds']:.1f}s)",
            f"    reservation {_n(rec['reservation'])} B: {fit}, "
            f"{_n(rec['headroom'])} B headroom; "
            f"{rec['delta']:+,} B against the stored bytes"
            + ("" if rec["declared_agrees"]
               else f"  WARNING: the trailer declares {_n(rec['declared'])} B, "
                    f"the decode produced {_n(rec['plain'])}")]


@contextlib.contextmanager
def _phase(what, remedy=""):
    """Label an unexpected failure with WHAT WAS BEING DONE when it happened.

    A run does up to four separable things, and only one of them is the census.
    Until 2026-08-20 a failure in any of them was printed by `_main`'s
    last-resort handler as "could not census DAT", which for three of the four
    is a false statement about the archive -- and `--reencode 9999` made that
    plain by printing the entire census first and THEN saying the file could not
    be read, under an exit code whose whole meaning is "unreadable archive".

    `Refused` is a `SystemExit`, not an `Exception`, so a phase nested inside
    another phase reports its own name and the outer one never sees it. That is
    also why a well-written refusal from inside `fn` -- `reencoded_size`'s
    three, `resolve_out`'s four -- passes through this wrapper untouched instead
    of being re-wrapped in a vaguer sentence.
    """
    try:
        yield
    except Exception as exc:                                   # noqa: BLE001
        raise Refused(f"could not {what}: {type(exc).__name__}: {exc}"
                      + (f"\n  {remedy}" if remedy else ""))


def _run(args):
    """The body, every refusal raised as `Refused`. Returns 0."""
    # THE WRITE DESTINATION IS DECIDED BEFORE THE ARCHIVE IS OPENED, which is
    # `bit31.py`'s correction and worth inheriting: a run that refuses --json
    # after a three-second census has spent the census, and one that refuses it
    # after opening the file has already been given the chance to truncate it.
    out = None
    if args.json:
        with _phase(f"resolve the --json destination {args.json}"):
            out = resolve_out(args.json)

    # The census phase covers the open, the walk and the headline -- everything
    # whose failure IS a fact about the archive.
    with _phase(f"census {args.dat}",
                remedy=f"Run `python toolkit/mapdata/datcheck.py --dat "
                       f"{args.dat} --preflight` to see what is wrong with the "
                       f"file."), Archive(args.dat) as ar:
        led = census(ar)
        sm = summary(led)
        print("\n".join(format_headline(led, sm)))
        if args.summary:
            print("\n".join(format_summary(sm)))

        # PAST THIS LINE THE CENSUS HAS RUN AND PRINTED, so nothing that fails
        # below is evidence about whether the archive is readable. Each verb
        # names itself.
        if out:
            with _phase(f"write the ledger to {out}",
                        remedy=f"The census itself was fine -- the headline "
                               f"above is it. If anything is left at {out} it "
                               f"is half-written; delete it rather than "
                               f"reading it."):
                with open(out, "w", encoding="utf-8") as fh:
                    json.dump(to_json(led, sm), fh, separators=(",", ":"))
                print(f"ledger -> {out} ({_n(os.path.getsize(out))} B)")
        if args.reencode:
            print(f"\nre-encoding {len(args.reencode)} row(s) with gwenc "
                  f"(~0.19 MB/s -- this is the slow verb)")
            for row in args.reencode:
                with _phase(f"re-encode row {row} of {args.dat}",
                            remedy=f"The census above ran; this is the row's "
                                   f"stream, not the archive. Check the row "
                                   f"with `python toolkit/mapdata/datcheck.py "
                                   f"--dat {args.dat} --crc-sweep`."):
                    print("\n".join(format_reencode(reencoded_size(ar, row))))
    return 0


def _main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", required=True, help="the archive to read ('rb')")
    ap.add_argument("--json", metavar="FILE",
                    help="write the ledger here (never inside a checkout)")
    ap.add_argument("--summary", action="store_true",
                    help="also print the conventions block, the deltas between "
                         "them, and the rows with the most slack")
    ap.add_argument("--reencode", metavar="ROW", nargs="+", type=int,
                    default=[],
                    help="measure what these comp-8 rows would occupy "
                         "re-encoded. On demand only: ~0.19 MB/s")
    args = ap.parse_args(argv)
    try:
        return _run(args)
    except Refused as exc:
        print(f"REFUSED: {exc}")
        return 2
    except Exception as exc:                                   # noqa: BLE001
        # BROAD ON PURPOSE, for `bit31.py`'s reason turned around: an
        # uncaught struct.error or MemoryError exits 1, and every sibling tool
        # in this directory spends exit 1 on "something CHANGED". A census that
        # could not be taken must not be readable as a result by a script that
        # only looks at the code.
        #
        # AND DELIBERATELY VAGUE ABOUT WHAT FAILED. This used to say "could not
        # census {dat}" for everything, including a mistyped `--reencode` row --
        # printed after the census had already run and printed, telling an
        # operator the archive was unreadable when the headline above said
        # otherwise. Every phase of `_run` now names itself through `_phase`, so
        # anything that reaches here happened outside all of them and this
        # handler genuinely does not know which verb broke. It says so.
        print(f"REFUSED: datledger failed on {args.dat}: "
              f"{type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(_main())
