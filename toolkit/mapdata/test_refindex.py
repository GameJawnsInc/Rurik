r"""The reverse-closure index: a planted reference must be found before any
absence is believed.

    python toolkit/mapdata/test_refindex.py

Builds its own archives, so there is no corpus to be missing and no vault to
resolve. Every fixture below is written from ITS OWN byte literals -- the
container framing, the reference-list record rule, the FA1 blk2C layout and the
MFT itself -- and imports nothing from `refindex` to build them. A test that
asks the module under test to construct its own input can only discover that
the module agrees with itself, which is the failure mode `datwrite.py`'s
docstring says three defects hid behind.

THE POSITIVE CONTROL IS THE FIRST SECTION AND IT IS NOT A FORMALITY. This index
answers "who else reads this row", and its answers are floors: an empty one is
"nothing I can see". A tool that answers a bounded question wrongly answers it
EMPTY, and an empty answer is the one shape that looks like success. So section
1 plants an FA8 link from two heads to a third and requires both to come back,
named and kinded, before any section here reads anything into an absence
(MEMORY: "a negative needs a positive control").

SECTION 3 IS THE SAME FAILURE FROM ITS OTHER SIDE, and it is here because the
first version of this module shipped it: a row can carry several file ids, and
edges filed under whichever spelling a reference list happened to use made the
same physical row answer two different things depending on which of its own
names you asked with -- one of them the confident empty list. So every spelling
of every referenced row is asked, including the spellings of a row that is NOT
a head (the ordinary FA5 texture target, which no head-only alias map can
resolve at all), and the three queries are cross-checked against each other for
the contradiction that defect produced.

SECTION 4 CARRIES THE NODE COUNT for the same reason. Bit-identical blk2C bases
are the right criterion and it does not move here; what moves is what the
answer SAYS, because the population contains degenerate keys -- a whole
skeleton of one node at (-0.0, -0.0, -0.0) -- and heads that group on one of
those have not been shown to share anything. The contentless pair is planted
and the answer must say so, while the real pair's answer must NOT carry that
sentence.

THE SABOTAGE is section 5's: the planted FA8 record's terminator is cut, and
the build must land the head in `problems` at `mdlrefs`' own gate and DROP that
referrer -- not invent one, and not take the head's other lists down with it.
The referrer that is still intact must still be reported, because a refusal
scoped to a whole head instead of the list that refused would look identical on
a green run and hide a real reference on a damaged archive.
"""

import binascii
import contextlib
import io
import json
import os
import struct
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive                                  # noqa: E402
from atex import Refused                                     # noqa: E402
from mapchunks import dependency_pair                        # noqa: E402
import refindex                                              # noqa: E402
from refindex import (build, canonical_id, head_rows, load,   # noqa: E402
                      save, stamp_of, unreferenced_fa1_heads,
                      who_reads, who_shares_skeleton)
import checks                                                # noqa: E402

# FLOOR: 92, MEASURED from a real green run on 2026-08-20, not guessed. Every
# section builds its own archive in a tempdir, so there is no corpus to be
# missing, no vault to resolve, and nothing that can legitimately skip. Per
# section, counted from the log rather than predicted:
# {0: 6, 1: 8, 2: 11, 3: 13, 4: 16, 5: 9, 6: 7, 7: 14, 8: 8}.
#
# SABOTAGES, applied one at a time as in-memory patches to a name the real code
# path resolves through, then reverted. Nothing on disk was edited, and these
# are the reds OBSERVED, not predicted:
#
#   who_reads goes back to a direct hit on the id it was handed        19 red
#   a multi-named row reported under its LAST id (the sorted[-1] shape) 12 red
#   only the reported spelling of a row resolves, the others do not    11 red
#   the spelling map covers HEADS only, leaving targets out             8 red
#   the sharing answer stops carrying node count / group size           7 red
#   answers stop carrying their blind spots                             5 red
#   the unreferenced-FA1 census always answers empty                    5 red
#   `zero_bases` is never computed, so no key is ever contentless       4 red
#   the head filter becomes `flags & 3 == 3`                            3 red
#   check_stamp stops gating (returns the new stamp)                    2 red
#   a malformed reference list loads EMPTY instead of refusing          1 red
#
# Four readings worth keeping rather than tidying away.
#
# THE TOP FOUR ARE ONE DEFECT, and it is not hypothetical -- it is what this
# module shipped and what section 3 exists to keep out. Filing an edge under
# whichever spelling a reference list happened to use made `who_reads(0x138D1)`
# and `who_reads(0x491C0)` -- two legitimate names for ONE retail row --
# answer differently, 558 times out of 558 on a 1,500-head subset of
# `vault/dat_study/Gw.dat`, and one of the two answers was empty. The
# `heads-only` patch is that exact shape: an alias map over head rows only,
# which cannot resolve a texture at all. THE SAME PROBE, same seed and the same
# 558 rows, re-run against the fixed module: 0 disagree, 558 agree -- including
# its own example, row 8350, where `0x138D1` and `0x491C0` now both answer
# [(8502, 'FA6'), (8932, 'FA6')] instead of one of them answering nothing.
#
# The LAST sabotage is the thin one and it is named as thin: one red, from
# section 5's terminator check, because loading a malformed list as empty is
# what the CLIENT does (`mdlrefs` error path 0x00794C27, no assert) and every
# other check in this file looks identical either way. That single check is the
# whole difference between "no reference" and "a reference we could not read",
# which is the distinction this index exists to keep, so it is load-bearing far
# out of proportion to its count.
#
# Three of them started as HARD STOPS -- an IndexError into an emptied
# blind-spot list, a KeyError on a head filed under an unexpected id, and a
# KeyError into an emptied `facts` that ended the run at check 47 -- and a test
# that only crashes has said the machine is unhappy rather than what broke.
# `first_spot()`, `head()` and `fact()` exist to turn all three into named
# reds; that is the entire reason those three helpers read defensively.
#
# The head-filter sabotage under-counted at 1 until the runner patched the
# name in BOTH modules: this file imports `head_rows` directly, so patching
# only `refindex.head_rows` left section 0 measuring the real function. The
# number moved 1 -> 3. A sabotage that measures the wrong binding under-reports
# coverage, which is a way to conclude a check is weak when it is fine.
LEDGER = checks.Ledger("reverse-closure index", floor=92)
check = checks.adopt(LEDGER)

# ---------------------------------------------------------------------------
# Fixture literals. Nothing below is imported from the module under test.
# ---------------------------------------------------------------------------

BLOCK = 512
ENTRY_SIZE = 24
ENTRY_CRC = 0x14
FILE_MAGIC = b"3AN\x1a"
MFT_MAGIC = b"Mft\x1a"
ROW_HEADER, ROW_IDTABLE, ROW_SELF = 1, 2, 3
FIRST_ROW = 16                   # rows 0..15 are structural (datcheck rule 9)

HEAD = 515                       # "addressable model-file head"
NOT_A_HEAD = 1                   # USED, no FIRST_STREAM: a companion stream
PLAIN_FILE = 3                   # USED|FIRST_STREAM: a texture, not a model

GEOMETRY, SKELETON = 0xFA0, 0xFA1
FA5, FA6, FA8 = 0xFA5, 0xFA6, 0xFA8
SKEL_VERSION = 0x26              # 0x0079495D  cmp dword ptr [ecx], 0x26

FID_A, FID_B = 120001, 120002
FID_B_PENDING = 0x80000000 | FID_B      # the same row, rename pending
FID_C, FID_D = 130003, 140004
FID_T, FID_T2 = 150005, 250010          # ONE head row, two PLAIN spellings
FID_E, FID_X, FID_U, FID_SIDE = 160006, 170007, 180008, 190009
FID_Z1, FID_Z2, FID_Z3, FID_Z4 = 200011, 200012, 200013, 200014
FID_TEX, FID_TEX_ALT = 210015, 310020   # ONE non-head row, two PLAIN spellings
FID_ABSENT = 999999              # U's FA8 names it; no row does
FID_NOWHERE = 424242             # nothing anywhere mentions it

BASES1 = ((1.0, 2.0, 3.0), (4.5, -5.25, 6.125))
BASES2 = ((7.0, 8.0, 9.0), (0.5, 0.25, 0.125))
BASES3 = ((-1.0, 0.0, 11.5), (2.75, 2.75, 2.75))
BASES4 = ((3.5, 3.5, 3.5), (-9.0, -9.0, -9.0))
#: The degenerate key, in retail's own spelling: one node, every component
#: NEGATIVE zero. `-0.0 == 0.0` is true, so it is contentless; its BYTES are
#: not +0.0's, so it is a different group, and both of those are on purpose.
BASES_ZERO = ((-0.0, -0.0, -0.0),)
BASES_ZERO_POS = ((0.0, 0.0, 0.0),)

ROW_A, ROW_B, ROW_C, ROW_D = 16, 17, 18, 19
ROW_T, ROW_E, ROW_X, ROW_U = 20, 21, 22, 23
ROW_Z1, ROW_Z2, ROW_Z3, ROW_Z4 = 24, 25, 26, 27
ROW_NAMELESS, ROW_TEX, ROW_SIDE = 28, 29, 30

WALKED = ROW_NAMELESS - ROW_A + 1        # every flags-515 row
INDEXED = WALKED - 2                     # minus the non-ffna and the nameless


def container(*chunks):
    """An ffna type-2 container: magic, type byte, then (id, size, payload)."""
    out = bytearray(b"ffna" + bytes([2]))
    for cid, payload in chunks:
        out += struct.pack("<II", cid, len(payload)) + payload
    return bytes(out)


def reflist(*fids):
    """A reference-list chunk payload, by its own arithmetic.

    u32 count, then one record per id: the two-wchar file-id spelling followed
    by an explicit zero terminator word. `None` is a NULL SLOT -- the
    terminator alone -- which is the shape that separates the record rule from
    the fixed-6-byte rival (`test_mdlrefs.py` section 0).
    """
    out = bytearray(struct.pack("<I", len(fids)))
    for fid in fids:
        if fid is not None:
            out += struct.pack("<HH", *dependency_pair(fid))
        out += b"\x00\x00"
    return bytes(out)


def fa1(bases, seq_count=0, node_flags=0):
    """A minimal 0xFA1 skeleton payload with the given per-node blk2C bases.

    Header, then the fixed 16-byte blk2C record per node (f32[3] base + u32
    flags), then one 6-byte {w0,w2,w4} sub-header per node with every channel
    empty, then the n18 sequence records. It closes on the exact final byte,
    which is `skelfile`'s own assertion and not the client's.
    """
    h = bytearray(0x58)
    struct.pack_into("<I", h, 0x00, SKEL_VERSION)
    struct.pack_into("<I", h, 0x18, seq_count)      # n18 = m_seqCount
    struct.pack_into("<I", h, 0x2C, len(bases))     # n2C = node count
    out = bytearray(h)
    for base in bases:
        out += struct.pack("<3f", *base) + struct.pack("<I", node_flags)
    out += b"\x00\x00\x00\x00\x00\x00" * len(bases)
    out += bytes(0x17 * seq_count)
    return bytes(out)


def self_crc_of(mft, count):
    """Row 3's own crc: the table either side of row 3's 24 bytes."""
    acc = binascii.crc32(bytes(mft[0x00:ROW_SELF * ENTRY_SIZE]))
    return binascii.crc32(
        bytes(mft[(ROW_SELF + 1) * ENTRY_SIZE:count * ENTRY_SIZE]), acc)


def build_archive(path, rows):
    """An archive whose data rows are `rows` = [(file_ids, payload, flags)].

    Row 1 is the file header, row 2 the file-id table, row 3 the MFT's own
    row; 4..15 stay zero; the data rows start at 16 in the order given. Every
    payload gets whole blocks, so no two reservations overlap.
    """
    entry_count = FIRST_ROW + len(rows)
    mft_size = entry_count * ENTRY_SIZE
    idtable = b"".join(
        struct.pack("<II", fid, FIRST_ROW + i)
        for i, (fids, _p, _f) in enumerate(rows) for fid in fids)

    extents = {ROW_HEADER: (0, 32), ROW_IDTABLE: (BLOCK, len(idtable))}
    payloads = {ROW_IDTABLE: idtable}
    off = BLOCK + max(1, -(-len(idtable) // BLOCK)) * BLOCK
    for i, (_fids, payload, _flags) in enumerate(rows):
        extents[FIRST_ROW + i] = (off, len(payload))
        payloads[FIRST_ROW + i] = payload
        off += max(1, -(-len(payload) // BLOCK)) * BLOCK
    mft_off = off
    buf = bytearray(mft_off + mft_size)

    head = bytearray(32)
    head[0:4] = FILE_MAGIC
    struct.pack_into("<I", head, 0x04, 32)
    struct.pack_into("<I", head, 0x08, BLOCK)
    struct.pack_into("<Q", head, 0x10, mft_off)
    struct.pack_into("<I", head, 0x18, mft_size)
    struct.pack_into("<I", head, 0x0C, binascii.crc32(bytes(head[:12])))
    buf[0:32] = head
    for row, payload in payloads.items():
        o = extents[row][0]
        buf[o:o + len(payload)] = payload

    fields = {ROW_HEADER: (0, 32, 3), ROW_IDTABLE: (BLOCK, len(idtable), 3),
              ROW_SELF: (mft_off, mft_size, 3)}
    for i, (_fids, payload, flags) in enumerate(rows):
        fields[FIRST_ROW + i] = (extents[FIRST_ROW + i][0], len(payload), flags)

    mft = bytearray(mft_size)
    mft[0:4] = MFT_MAGIC
    struct.pack_into("<I", mft, 0x0C, entry_count)
    for row, (o, size, flags) in fields.items():
        crc = 0 if row in (ROW_HEADER, ROW_SELF) else binascii.crc32(
            bytes(buf[o:o + size]))
        struct.pack_into("<QIHHII", mft, row * ENTRY_SIZE,
                         o, size, 0, flags, 0, crc)
    struct.pack_into("<I", mft, ROW_SELF * ENTRY_SIZE + ENTRY_CRC,
                     self_crc_of(mft, entry_count))
    buf[mft_off:mft_off + mft_size] = mft

    with open(path, "wb") as fh:
        fh.write(bytes(buf))
    return path


def rows_spec(a_fa8=None, d_bases=BASES2 + ((1.0, 1.0, 1.0),)):
    """The population every section reads, with two knobs for the variants.

    A and B both link to C (the planted reference); A also names T through
    FA5 and B through FA6, so the KIND is not a constant. T carries TWO plain
    file ids and so does the texture row A's FA5 names -- which is not a head
    at all, and is the case a head-only alias map cannot resolve. E names B,
    whose row also answers to a bit-31 rename spelling. Z1..Z3 wear the
    degenerate all-zero skeleton and Z4 wears its positive-zero twin. X is not
    an ffna file, the nameless head is named by no file id, U links to an id no
    row holds, and the last row is flags-1 -- a companion stream, not a head.
    """
    return [
        ([FID_A], container((FA8, reflist(FID_C, FID_C) if a_fa8 is None
                             else a_fa8),
                            (FA5, reflist(FID_T, None, FID_TEX)),
                            (SKELETON, fa1(BASES1, seq_count=3))), HEAD),
        ([FID_B, FID_B_PENDING],
         container((FA8, reflist(FID_C)), (FA6, reflist(FID_T)),
                   (SKELETON, fa1(BASES1, seq_count=1))), HEAD),
        ([FID_C], container((SKELETON, fa1(BASES2))), HEAD),
        ([FID_D], container((SKELETON, fa1(d_bases))), HEAD),
        ([FID_T, FID_T2], container((GEOMETRY, b"\xAA" * 8),
                                    (SKELETON, fa1(BASES3))), HEAD),
        ([FID_E], container((GEOMETRY, b"\xBB" * 8), (FA8, reflist(FID_B)),
                            (SKELETON, fa1(BASES4))), HEAD),
        ([FID_X], bytes(28), HEAD),                  # the row-8316 shape
        ([FID_U], container((FA8, reflist(FID_ABSENT))), HEAD),
        ([FID_Z1], container((GEOMETRY, b"\xCC" * 8),
                             (SKELETON, fa1(BASES_ZERO))), HEAD),
        ([FID_Z2], container((GEOMETRY, b"\xCC" * 8),
                             (SKELETON, fa1(BASES_ZERO))), HEAD),
        ([FID_Z3], container((GEOMETRY, b"\xCC" * 8),
                             (SKELETON, fa1(BASES_ZERO))), HEAD),
        ([FID_Z4], container((GEOMETRY, b"\xCC" * 8),
                             (SKELETON, fa1(BASES_ZERO_POS))), HEAD),
        ([], container((FA8, reflist(FID_C))), HEAD),
        ([FID_TEX, FID_TEX_ALT], b"ATEX-ish bytes, not a model", PLAIN_FILE),
        ([FID_SIDE], container((FA8, reflist(FID_C))), NOT_A_HEAD),
    ]


@contextlib.contextmanager
def quiet():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        yield buf


def refuses(fn, *a, **kw):
    """True if the call refuses. Returns the message so it can be read."""
    try:
        fn(*a, **kw)
    except Refused as exc:
        return str(exc)
    return ""


def first_spot(index):
    """The first blind-spot sentence, or "" if the index reports none.

    Indexed defensively on purpose: a sabotage that empties `blind_spots`
    crashed this file with an IndexError before, and a test that only crashes
    has said the machine is unhappy rather than what broke (test_datalloc.py's
    reading of its own splitter sabotage).
    """
    return (index.blind_spots() or [""])[0]


def head(index, fid, key):
    """One fact off the head `fid` names, through the index's own row map.

    Same reason as `first_spot`: an index that files a head under an
    unexpected row should redden the ONE check about filing, not crash every
    check that reads a fact off it.
    """
    return index.heads.get(index.row_of(fid), {}).get(key)


def fact(answer, key):
    """One entry of an answer's `facts`, or None if it does not carry it.

    Third helper for the same reason, and it earned its place the same way: a
    sabotage that emptied `facts` raised KeyError here and stopped the run at
    47 checks, so the ONE thing that broke was invisible behind a traceback.
    """
    return getattr(answer, "facts", {}).get(key)


# ---------------------------------------------------------------------------

def section0(tmp):
    print("\n== section 0: the shared constants and the fixture's own bytes ==")
    check(refindex.HEAD_FLAGS == HEAD,
          f"HEAD_FLAGS is {HEAD} -- the value every archive-wide model sweep "
          "in this repo filters on, now with an importable home",
          f"got {refindex.HEAD_FLAGS}")
    check(sorted(refindex.CHUNK_NAMES.values())
          == ["FA5", "FA6", "FA8", "FAD", "FAE"],
          "the five reference lists are named FA5/FA6/FA8/FAD/FAE, derived "
          "from mdlrefs.REF_CHUNKS rather than written out again",
          f"got {sorted(refindex.CHUNK_NAMES.values())}")
    check(refindex.parse_fid("130003") == 130003
          and refindex.parse_fid("0x1FBD3") == 0x1FBD3
          and refindex.parse_fid(" 0X1FBD3 ") == 0x1FBD3,
          "a file id on the command line is decimal or 0x hex")
    check("not a file id" in refuses(refindex.parse_fid, "banana"),
          "and anything else is refused rather than guessed at")

    # The fixture must be readable by the ordinary opener before anything
    # measured off it means a thing.
    path = build_archive(os.path.join(tmp, "fix.dat"), rows_spec())
    with Archive(path) as ar:
        check(head_rows(ar) == list(range(ROW_A, ROW_NAMELESS + 1)),
              f"head_rows finds rows {ROW_A}..{ROW_NAMELESS} and excludes both "
              f"the flags-{PLAIN_FILE} texture row {ROW_TEX} and the "
              f"flags-{NOT_A_HEAD} companion row {ROW_SIDE}",
              f"got {head_rows(ar)}")
        check(len(ar.entries) == ar.row_count - 1
              and ar.row(ROW_C).flags == HEAD,
              "the fixture's MFT is internally consistent and row addressing "
              "resolves through Archive.row, not a position")
    return path


def section1(path):
    print("\n== section 1: THE POSITIVE CONTROL -- a planted FA8 link ==")
    with Archive(path) as ar:
        idx = build(ar)

    answer = who_reads(idx, FID_C)
    check(list(answer) == [(FID_A, "FA8"), (FID_B, "FA8")],
          f"both heads that link to {FID_C} come back, kinded FA8 -- the "
          "planted reference is FOUND before any absence below is believed",
          f"got {list(answer)}")
    check(isinstance(answer, list) and answer == [(FID_A, "FA8"),
                                                  (FID_B, "FA8")],
          "the answer IS a list: callers index, iterate and compare it")
    note = str(answer)
    check("at least 2 referrer" in note,
          "and str(answer) reports the count as a FLOOR, not a census",
          note.splitlines()[0])
    check("FA5/FA6/FA8/FAD/FAE" in note and "flags-515 heads" in note,
          "the sentence names the mechanisms the count is a floor OF")
    check("BLIND SPOT" in note and "FA1-only" in note
          and "not addressable by file id" in note,
          "and names the blind spots: the FA1-only heads nothing reaches, and "
          "the mid/tail streams no file id can address")
    check(first_spot(idx).startswith("1 FA1-only"),
          "the FA1-only count is COMPUTED from this index, not a constant "
          "carried over from the retail measurement", first_spot(idx))

    empty = who_reads(idx, FID_NOWHERE)
    check(list(empty) == [] and "at least 0 referrer" in str(empty),
          "a query for a file id this archive never mentions answers empty "
          "WITH the floor sentence, and does not crash")
    check(list(who_reads(idx, FID_E)) == [],
          f"{FID_E} is a real head nothing names: also empty, and the note "
          "above is what stops that being read as 'safe to overwrite'")
    return idx


def section2(idx):
    print("\n== section 2: what an edge is, and what is not one ==")
    check(list(who_reads(idx, FID_T)) == [(FID_A, "FA5"), (FID_B, "FA6")],
          "the KIND is the chunk that named it: A reaches T through FA5, B "
          "through FA6", f"got {list(who_reads(idx, FID_T))}")
    check(len(who_reads(idx, FID_C)) == 2,
          "A's FA8 names C TWICE and it is one referrer -- the question is "
          "who reads this file, not how many times")
    check(idx.edges.get(ROW_C) == [(ROW_A, "FA8"), (ROW_B, "FA8")],
          "the graph itself is keyed by MFT ROW, both ends: a file id is a "
          "name for a row and never the identity of one",
          f"got {idx.edges.get(ROW_C)}")
    check(head(idx, FID_A, "refs") == {"FA8": 2, "FA5": 3},
          "the record COUNTS are kept per list, so the duplicate and the null "
          "slot are still visible on the head",
          f"got {head(idx, FID_A, 'refs')}")
    fa5_from_a = sorted(t for t, v in idx.edges.items() if (ROW_A, "FA5") in v)
    check(fa5_from_a == [ROW_T, ROW_TEX],
          "A's FA5 holds three records and exactly TWO of them are edges: the "
          "null slot names no file, so it names no reader either",
          f"got {fa5_from_a}")
    check([u["file_id"] for u in idx.unresolved] == [FID_ABSENT]
          and idx.unresolved[0]["referrer"] == FID_U
          and idx.unresolved[0]["referrer_row"] == ROW_U,
          f"U's FA8 names {FID_ABSENT}, which no row holds: recorded in "
          "index.unresolved, never silently dropped",
          f"got {idx.unresolved}")
    check(idx.row_of(FID_ABSENT) is None,
          "and an unresolvable target is not filed as if it were a real file")

    check(idx.row_of(FID_B_PENDING) == ROW_B
          and head(idx, FID_B, "fids") == [FID_B, FID_B_PENDING],
          "a row named by two spellings is ONE head, holding both names, and "
          "both resolve to the row", f"got {head(idx, FID_B, 'fids')}")
    check(all(r != FID_B_PENDING for r, _k in who_reads(idx, FID_C)),
          "so B is counted as one referrer, not two")
    check(head(idx, FID_A, "seq_count") == 3
          and head(idx, FID_B, "seq_count") == 1
          and head(idx, FID_C, "seq_count") == 0,
          "m_seqCount is RECORDED as a fact per head (the client gates links "
          "on it at 0x00794917; this walk does not, so no edge is dropped)")
    check(idx.row_of(FID_SIDE) is None
          and all(r != ROW_SIDE for v in idx.edges.values() for r, _k in v),
          f"the flags-{NOT_A_HEAD} companion row links to C and is NOT walked "
          "-- the enumeration boundary is a real filter, not a formality")


def section3(idx):
    print("\n== section 3: every spelling of a row answers the same ==")
    # POSITIVE FIRST, as everywhere in this file: the texture must be found
    # under the name its referrer used before its other name means anything.
    tex = who_reads(idx, FID_TEX)
    check(list(tex) == [(FID_A, "FA5")],
          f"the texture row {ROW_TEX} is reached: A's FA5 names {FID_TEX}",
          f"got {list(tex)}")
    alt = who_reads(idx, FID_TEX_ALT)
    check(list(alt) == list(tex),
          f"and {FID_TEX_ALT}, the SAME row's other spelling, answers "
          "identically -- the answer is about the row, not the name it was "
          "asked under", f"{list(alt)} vs {list(tex)}")
    check(fact(tex, "row") == ROW_TEX and fact(alt, "row") == ROW_TEX
          and fact(tex, "names") == [FID_TEX, FID_TEX_ALT],
          "both resolve to one row and both report every name it has",
          f"got {fact(tex, 'names')} / row {fact(alt, 'row')}")
    check(idx.row_of(FID_TEX_ALT) == ROW_TEX and ROW_TEX not in idx.heads,
          f"and row {ROW_TEX} is NOT a head -- a head-only alias map could not "
          "resolve it at all, which is the half of the population an FA5 "
          "target usually falls in")
    check(f"0x{FID_TEX_ALT:X}" in str(tex)
          and "also named" in str(tex) and "about the ROW" in str(tex),
          "the answer NAMES the other spelling, so a caller comparing ids "
          "against its own list can see it needs to normalise",
          str(tex).splitlines()[1] if len(str(tex).splitlines()) > 1 else "")

    check(list(who_reads(idx, FID_T2)) == list(who_reads(idx, FID_T))
          == [(FID_A, "FA5"), (FID_B, "FA6")],
          "same for a HEAD row with two plain spellings, and the two kinds "
          "survive the resolution", f"got {list(who_reads(idx, FID_T2))}")
    check(list(who_reads(idx, FID_B_PENDING)) == list(who_reads(idx, FID_B))
          == [(FID_E, "FA8")],
          "and for the bit-31 rename spelling of B, which E's FA8 reaches "
          "under the plain one", f"got {list(who_reads(idx, FID_B_PENDING))}")

    check(canonical_id(idx, FID_T2) == FID_T
          and canonical_id(idx, FID_TEX_ALT) == FID_TEX
          and canonical_id(idx, FID_B_PENDING) == FID_B,
          "canonical_id normalises every spelling to the one answers report, "
          "which is what a gate must run its own id list through")
    check(canonical_id(idx, FID_NOWHERE) == FID_NOWHERE,
          "an id this index does not hold comes back unchanged, so a caller "
          "can normalise a whole list without special-casing")

    # THE CONTRADICTION CHECK. The shipped defect was not that one query was
    # wrong -- it was that two queries about the SAME row disagreed, and each
    # looked fine alone. This compares them.
    disagree = [(fid, spell)
                for row, rec in idx.heads.items()
                for fid in rec["fids"] for spell in rec["fids"]
                if list(who_reads(idx, fid)) != list(who_reads(idx, spell))]
    check(not disagree,
          "NO TWO SPELLINGS OF ANY HEAD DISAGREE, over every head in the "
          f"index ({sum(len(r['fids']) for r in idx.heads.values())} names)",
          f"disagreeing: {disagree}")
    unref = set(unreferenced_fa1_heads(idx))
    contradiction = [fid for row, rec in idx.heads.items()
                     for fid in rec["fids"]
                     if (canonical_id(idx, fid) in unref)
                     and who_reads(idx, fid)]
    check(not contradiction,
          "and no head the FA1-only census calls unreached answers who_reads "
          "with a referrer under ANY of its names -- the two queries are "
          "consistent, which is exactly what the row keying buys",
          f"contradicting: {contradiction}")

    nowhere = who_reads(idx, FID_NOWHERE)
    check(fact(nowhere, "resolved") is False
          and "no head row and no referenced row" in str(nowhere),
          "an id naming nothing here says so, rather than answering a bare "
          "empty list that reads like 'nobody reads it'")
    real = who_reads(idx, FID_D)
    check(fact(real, "resolved") is True and list(real) == []
          and "no head row and no referenced row" not in str(real),
          "while a real head nothing references is EMPTY AND RESOLVED -- two "
          "different states, and a gate can tell them apart")


def section4(idx):
    print("\n== section 4: shared skeletons, by bit-identical blk2C bases ==")
    a = who_shares_skeleton(idx, FID_A)
    check(list(a) == [FID_B],
          "A and B carry bit-identical blk2C base arrays and are paired",
          f"got {list(a)}")
    check(list(who_shares_skeleton(idx, FID_B)) == [FID_A],
          "and the relation is symmetric, each excluding itself")
    check(list(who_shares_skeleton(idx, FID_C)) == [],
          "C has the SAME node count and different bases: excluded. Bit "
          "identity is the criterion, not similarity")
    check(list(who_shares_skeleton(idx, FID_D)) == []
          and (head(idx, FID_D, "node_count")
               != head(idx, FID_C, "node_count")),
          "D's array starts with C's and has a third node: a different node "
          "count is a different group (studies/unitmodels 3.11's own control, "
          "86 nodes vs 20)")
    check(head(idx, FID_A, "skel") == head(idx, FID_B, "skel")
          and head(idx, FID_A, "skel") != head(idx, FID_C, "skel"),
          "the group key is (node count, sha256 of the packed f32[3] bases)")
    check(list(who_shares_skeleton(idx, FID_B_PENDING)) == [FID_A]
          and list(who_shares_skeleton(idx, FID_T2)) == [],
          "the query resolves an alias spelling to the head it names, plain "
          "or bit-31")
    check(list(who_shares_skeleton(idx, FID_U)) == []
          and "at least 0 co-wearer" in str(who_shares_skeleton(idx, FID_U))
          and "no FA1 chunk" in str(who_shares_skeleton(idx, FID_U)),
          "a head with no FA1 chunk wears no skeleton, the empty answer still "
          "says what it is a floor of, and it says WHY it is empty")
    check("blk2C" in str(a),
          "the sharing answer names ITS mechanism, which is not the reference "
          "mechanism the who_reads answer names")

    # THE FACTS THAT DECIDE WHETHER THE NUMBER MEANS ANYTHING. On retail the
    # largest group is hundreds of heads keyed on one all-zero node; a bare
    # count would send an operator off to acknowledge every one of them.
    check("2 blk2C node(s)" in str(a) and "group holds 2 head(s)" in str(a),
          "the answer states the node count of the key and the size of the "
          "group, in the sentence a caller copies",
          str(a).splitlines()[1] if len(str(a).splitlines()) > 1 else "")
    check(fact(a, "node_count") == 2 and fact(a, "group_size") == 2
          and fact(a, "contentless") is False,
          "and as DATA, so a gate tiers on the same three facts the sentence "
          "states rather than parsing prose", f"got {getattr(a, 'facts', None)}")
    z = who_shares_skeleton(idx, FID_Z1)
    check(list(z) == [FID_Z2, FID_Z3],
          "the three heads wearing the degenerate one-node skeleton do group "
          "-- the bit-identity criterion is NOT weakened here", f"got {list(z)}")
    check(fact(z, "contentless") is True and fact(z, "node_count") == 1
          and fact(z, "group_size") == 3
          and "EVERY base in that array is zero" in str(z),
          "but the answer says outright that the key carries no pose, which "
          "is the difference between a shared rig and two models that both "
          "have nothing", f"got {getattr(z, 'facts', None)}")
    check("EVERY base in that array is zero" not in str(a),
          "and the real pair's answer does NOT carry that sentence, so it is "
          "a finding and not decoration on every answer")
    check(head(idx, FID_Z1, "zero_bases") is True
          and head(idx, FID_A, "zero_bases") is False,
          "-0.0 counts as zero -- retail's degenerate node is literally "
          "(-0.0, -0.0, -0.0) -- and a real base array does not")
    check(list(who_shares_skeleton(idx, FID_Z4)) == []
          and fact(who_shares_skeleton(idx, FID_Z4), "contentless") is True,
          "Z4's +0.0 array is contentless too and still does NOT join the "
          "-0.0 group: 'contentless' is a REPORT on the key, and the grouping "
          "is bit-identity, unmoved")
    tex = who_shares_skeleton(idx, FID_TEX)
    check(list(tex) == [] and "only as a reference TARGET" in str(tex),
          "asking a texture row what wears its skeleton answers empty and "
          "says the row is a reference target, not one of the heads indexed")


def section5(tmp, idx):
    print("\n== section 5: problems, and the terminator sabotage ==")
    by_row = {p["row"]: p for p in idx.problems}
    check(set(by_row) == {ROW_X, ROW_NAMELESS},
          "the two unindexable heads are BOTH reported: the non-ffna row and "
          "the row no file id names", f"got {sorted(by_row)}")
    check("not an ffna type-2" in by_row[ROW_X]["why"]
          and by_row[ROW_X]["file_id"] == FID_X,
          "the non-ffna head names its file id and what refused")
    check(by_row[ROW_NAMELESS]["file_id"] is None
          and "no file id" in by_row[ROW_NAMELESS]["why"],
          "the nameless head is a problem, not a skip: nothing it references "
          "could be attributed to an id the client can address")
    check(all(r not in (ROW_X, ROW_NAMELESS)
              for v in idx.edges.values() for r, _k in v),
          "and neither contributes an edge")
    check(idx.walked == WALKED and len(idx.heads) == INDEXED,
          "the index reports how many head rows it WALKED separately from how "
          "many it indexed, so two unreadable heads do not quietly shrink the "
          "archive", f"walked {idx.walked}, indexed {len(idx.heads)}")

    # THE SABOTAGE: cut the terminator off the planted FA8 record.
    cut = build_archive(os.path.join(tmp, "cut.dat"),
                        rows_spec(a_fa8=reflist(FID_C, FID_C)[:-2]))
    with Archive(cut) as ar:
        bad = build(ar)
    fa8_problems = [p for p in bad.problems if p["file_id"] == FID_A]
    check(len(fa8_problems) == 1
          and "FA8 list" in fa8_problems[0]["why"]
          and "G01_terminator" in fa8_problems[0]["why"],
          "SABOTAGE: A's FA8 record loses its terminator and the build records "
          "the problem at mdlrefs' own gate",
          f"got {fa8_problems}")
    check(list(who_reads(bad, FID_C)) == [(FID_B, "FA8")],
          "A's link is DROPPED rather than invented, and B's -- which is "
          "intact -- is still reported")
    check(list(who_reads(bad, FID_T)) == [(FID_A, "FA5"), (FID_B, "FA6")],
          "A's FA5 list still indexes: the refusal is scoped to the list that "
          "refused, not to the whole head")
    check(len(bad.heads) == len(idx.heads)
          and "would not read or decode" in "\n".join(bad.blind_spots()),
          "the build COMPLETES over the rest of the archive, and the extra "
          "problem is named in every answer's blind spots")


def section6(tmp, idx):
    print("\n== section 6: the FA1-only heads nothing reaches ==")
    unref = unreferenced_fa1_heads(idx)
    check(list(unref) == [FID_D],
          f"exactly {FID_D} -- FA1-only and named by no reference list here",
          f"got {list(unref)}")
    check(FID_C not in unref,
          "C is FA1-only too and IS an FA8 target, so it is explained")
    check(FID_E not in unref and FID_Z1 not in unref,
          "E and Z1 are unreferenced but carry FA0: the signature is the "
          "study's (FA1 and nothing else over the tracked ids), not 'has a "
          "skeleton'")
    check("at least 1 FA1-only head" in str(unref),
          "the list is itself a floor and says so")

    with Archive(os.path.join(tmp, "fix.dat")) as ar:
        part = build(ar, rows=[ROW_A, ROW_C])
    check(part.partial and len(part.heads) == 2
          and list(who_reads(part, FID_C)) == [(FID_A, "FA8")],
          "a subset build answers only about what it walked")
    check("PARTIAL" in str(who_reads(part, FID_C))
          and "floor of a floor" in str(who_reads(part, FID_C)),
          f"and every answer off it says so -- a floor computed over 2 of "
          f"{WALKED} heads is a floor of a floor")
    check(first_spot(part).startswith("0 FA1-only")
          and first_spot(idx).startswith("1 FA1-only"),
          "the blind-spot count is COMPUTED per index and not a constant: the "
          "same archive gives 1 over every head and 0 over these two, because "
          "the FA1-only head D is not in the subset")


def section7(tmp, path, idx):
    print("\n== section 7: the stamp, and what a stale index must not do ==")
    out = os.path.join(tmp, "index.json")
    save(idx, out)
    back = load(out)
    check(list(who_reads(back, FID_C)) == [(FID_A, "FA8"), (FID_B, "FA8")]
          and list(who_shares_skeleton(back, FID_A)) == [FID_B]
          and list(unreferenced_fa1_heads(back)) == [FID_D],
          "a saved index answers identically after a JSON round trip")
    check(list(who_reads(back, FID_TEX_ALT)) == [(FID_A, "FA5")]
          and back.row_of(FID_TEX_ALT) == ROW_TEX
          and canonical_id(back, FID_TEX_ALT) == FID_TEX,
          "including under the other spelling of a NON-head row: the spelling "
          "map is persisted, not rebuilt from heads",
          f"got {list(who_reads(back, FID_TEX_ALT))}")
    check(str(who_reads(back, FID_C)) == str(who_reads(idx, FID_C))
          and str(who_shares_skeleton(back, FID_Z1))
          == str(who_shares_skeleton(idx, FID_Z1)),
          "including the floor sentence and the skeleton facts, which are "
          "rebuilt from the loaded index rather than stored")

    with Archive(path) as ar:
        check(load(out, ar) is not None,
              "and it loads against the archive it was built from")

    # One byte of payload, same lengths: size_on_disk and row_count are
    # UNCHANGED, so only the MFT sha256 can catch it.
    moved = build_archive(os.path.join(tmp, "moved.dat"),
                          rows_spec(d_bases=BASES2 + ((1.0, 1.0, 2.0),)))
    with Archive(moved) as ar2:
        now = stamp_of(ar2)
        check(now["size_on_disk"] == idx.stamp["size_on_disk"]
              and now["row_count"] == idx.stamp["row_count"]
              and now["mft_sha256"] != idx.stamp["mft_sha256"],
              "the edited archive is the same SIZE with the same row count -- "
              "so this next refusal is the sha256 term doing the work")
        msg = refuses(load, out, ar2)
        check("REFUSING" in msg and "mft_sha256" in msg,
              "loading it against a changed archive is refused, naming the "
              "field that differs", msg.splitlines()[0] if msg else "accepted")
        check("--build-json" in msg,
              "and the refusal names the remedy that fixes it")

    doctored = os.path.join(tmp, "doctored.json")

    def spill(mutate):
        with open(out, encoding="utf-8") as fh:
            doc = json.load(fh)
        mutate(doc)
        with open(doctored, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        return doctored

    def bump(d):
        d["format_version"] = 99

    def strip_stamp(d):
        d["stamp"].pop("mft_sha256")

    def drop_heads(d):
        d.pop("heads")

    def drop_targets(d):
        d.pop("targets")

    check("format_version" in refuses(load, spill(bump)),
          "an index written by another format version is refused, not read")
    check("mft_sha256" in refuses(load, spill(strip_stamp)),
          "a stamp missing an identity field is refused -- it could never be "
          "matched against an archive")
    check("not an index" in refuses(load, spill(drop_heads)),
          "and a document with no heads object is refused before any query")
    check("'targets'" in refuses(load, spill(drop_targets)),
          "so is one with no targets object: without the spelling map, half "
          "the referenced rows would answer only to one of their names")
    with open(doctored, "w", encoding="utf-8") as fh:
        json.dump([1, 2, 3], fh)
    check("not an index object" in refuses(load, doctored),
          "a JSON list is refused by shape")
    check("could not read" in refuses(load, os.path.join(tmp, "nope.json")),
          "and so is a file that is not there")

    into_repo = os.path.join(HERE, "refindex-test-must-not-write.json")
    msg = refuses(save, idx, into_repo)
    check("refusing to write a reference index" in msg
          and not os.path.exists(into_repo),
          "saving into a checkout of this repo is refused, and nothing is "
          "written -- an index of retail rows describes retail",
          msg.splitlines()[0] if msg else "IT WROTE THE FILE")


def section8(tmp, path):
    print("\n== section 8: the CLI ==")
    with quiet() as buf:
        rc = refindex.main(["--dat", path, "--who-reads", str(FID_C)])
    out = buf.getvalue()
    check(rc == 0 and "at least 2 referrer" in out,
          "--who-reads prints the answer with its floor sentence", f"rc {rc}")
    check(f"{FID_A} (0x{FID_A:X}) via FA8" in out,
          "and one line per referrer, naming the kind and the row")
    check(f"largest: 3 head(s) sharing a 1-node array" in out
          and "ALL ZERO" in out,
          "the summary names the biggest sharing group AND says its key is "
          "contentless, so a degenerate group cannot read as a shared rig",
          [ln for ln in out.splitlines() if "largest" in ln])
    with quiet() as buf:
        rc = refindex.main(["--dat", path, "--who-reads", str(FID_TEX_ALT)])
    out = buf.getvalue()
    check(rc == 0 and "at least 1 referrer" in out
          and f"0x{FID_TEX:X}" in out and f"is row {ROW_TEX}" in out,
          "a query under a row's other spelling answers the same and prints "
          "which row it resolved to and every name that row has", f"rc {rc}")

    with quiet() as buf:
        rc = refindex.main(["--dat", path, "--who-shares", f"0x{FID_A:X}"])
    check(rc == 0 and "at least 1 co-wearer" in buf.getvalue()
          and "2 blk2C node(s)" in buf.getvalue(),
          "--who-shares takes an 0x file id and answers with its own floor "
          "and the node count of the key", f"rc {rc}")

    j = os.path.join(tmp, "cli.json")
    with quiet():
        rc = refindex.main(["--dat", path, "--build-json", j])
    check(rc == 0 and os.path.exists(j),
          "--build-json writes the index where it is allowed to")
    with quiet() as buf:
        rc = refindex.main(["--dat", path, "--json", j, "--build-json", j])
    check(rc == 2 and "same file" in buf.getvalue(),
          "reading and writing the same index file is refused (bit31's "
          "lesson: it would check the stamp of what it just wrote)", f"rc {rc}")
    with quiet() as buf:
        rc = refindex.main(["--dat", os.path.join(tmp, "no-such.dat")])
    check(rc == 2 and "REFUSED" in buf.getvalue(),
          "an unreadable archive exits 2, never 0 with an empty index",
          f"rc {rc}")


def main():
    with tempfile.TemporaryDirectory() as tmp:
        path = section0(tmp)
        idx = section1(path)
        section2(idx)
        section3(idx)
        section4(idx)
        section5(tmp, idx)
        section6(tmp, idx)
        section7(tmp, path, idx)
        section8(tmp, path)
    sys.exit(LEDGER.verdict())


if __name__ == "__main__":
    main()
