r"""The reverse-closure index: *who else reads this file?*, asked before a write.

READ ONLY. Nothing here opens an archive for writing.

WHY IT EXISTS. `unitassembly.py` walks FORWARD from one definition -- a 0x0056
shell, its 0x0057 bodies, and everything they reference -- and that is the only
closure this repo could compute. The question a WRITER has is the inverse: if
row N is about to be replaced, who else is reading it? Nothing could answer it,
and the hazard is measured rather than theoretical: `studies/unitmodels`
FINDINGS section 3.11 found six of seven claimed skeleton-sharing pairs at
0.0000 u per-node distance -- bit-identical rest poses, not merely similar ones
-- so editing one model's skeleton silently edits every model wearing it. This
module is that guard's query engine. It does not refuse anything itself;
`overlay.py`'s plan gate is the caller that turns an answer into a refusal.

    idx = build(ar)                        # one pass over every flags-515 head
    who_reads(idx, 116703)                 # [(referrer_fid, 'FA8'), ...]
    who_shares_skeleton(idx, 116228)       # heads with the same blk2C bases
    unreferenced_fa1_heads(idx)            # reached by nothing this index sees

THE FLOOR RULE, and it is the load-bearing design decision. Every answer here
is a LOWER BOUND and says so out loud: `who_reads` returns an `Answer`, which
is a list (index it, iterate it, compare it) whose `str()` is a sentence naming
what the count is a floor of and which mechanisms this index cannot see. That
is not decoration. The index reads FA5/FA6/FA8/FAD/FAE reference lists on
flags-515 head rows, and three things are known to reach a file some other way:
the FA1-only heads that no reference list names at all (`studies/mdlrefs`
FINDINGS section 7 measured that class and left HOW they are reached OPEN); the
mid/tail companion chunk families (0xBB8-0xBC1, 0xFAC and friends), which are
not addressable by file id at all, so a reference through one is not countable
here even in principle; and any head this index could not read, every one of
which is in `index.problems` and none of which is silently dropped. An empty
answer from a bounded index is "nothing I can see", never "nothing" -- and a
caller that reads it as the second is the failure this whole module is here to
prevent, so the sentence travels with the number.

The blind-spot count is COMPUTED, per index, from that index's own heads. The
study's figure for the retail archive is a fact the doc cites; a constant in
here asserting it would be a check that cannot fail on a synthetic and a wrong
number on any archive but one.

EVERY SPELLING OF A ROW ANSWERS THE SAME, WHICH IS WHY THE GRAPH IS KEYED BY
ROW. A file id is archive STATE and a row can carry several ids; the FIRST
version of this module filed edges under whichever spelling the reference list
happened to use, so the same physical row answered two different things
depending on which of its legitimate names you asked with -- and one of the two
answers was the confident empty list this module calls its one unacceptable
output. MEASURED on `vault/dat_study/Gw.dat`, 2026-08-20, by inverting
`file_id_table(ar, raw=True)`: 38,396 rows are named by more than one file id
(every one of them by exactly two), 12,860 of the 21,421 flags-515 heads are
among them (60.0%), and 25,536 of them are NOT heads -- textures and sounds,
which is to say the ordinary FA5/FA6 target. Only nine of the 38,396 involve a
bit-31 spelling at all, so this is the common case and not the rename case.
So: `edges`, `heads` and the sharing groups are keyed by MFT ROW, `fid_row`
carries every spelling of every head row and every referenced row, and each
query resolves its argument through it first. The row is the identity; a file
id is a name for one.

    ROWS ARE INTERNAL, FILE IDS ARE THE API. Every public function takes and
    returns file ids; every structure inside is keyed by row. The two are never
    interchangeable and are never mixed in one parameter, because both are
    small ints and a function that accepted either could not tell them apart --
    which is the shape of `archive.Archive.row` versus `entries[n]`, the trap
    this repo has already paid for more than once.

`canonical_id(index, fid)` is how a CALLER compares ids across that boundary:
a manifest that acknowledges 0x491C0 and an answer that names 0x138D1 are
naming the same row, and a gate comparing the two strings would refuse a
declaration that is in fact complete. Normalise both sides through it.

WHAT A SHARED SKELETON MEANS HERE. Per head carrying an FA1 chunk, the per-node
f32[3] `base` array is packed in node order and sha256'd
(`skelfile.Skeleton.anims()`, the blk2C node-base reader), and a sharing group
is an identical (node count, hash) pair. That is section 3.11's bit-identical
criterion applied to the whole population instead of to three hand-picked
pairs. Node count is part of the key on purpose: the control in that study
(116228 vs the burrowing worm 116366) does not even reach the distance test
because the counts differ, 86 vs 20.

AND THE ANSWER CARRIES THE NODE COUNT, because the criterion is right and the
bare count is not readable. Section 3.11 measured 86-to-105-node skeletons,
where a bit-identical array is a real shared rig. Applied population-wide the
same key also groups the DEGENERATE arrays -- a head whose whole blk2C is one
node at (-0.0, -0.0, -0.0) has a key with no pose in it, and every other such
head keys identically. On retail that is not a corner. MEASURED on a 1,500-head
random sample of `dat_study`: 1,003 of them carry an FA1 and 572 of those --
more than half -- sit in ONE group, keyed on a single all-zero node. Left as a
bare number, a gate built on this would ask an operator to acknowledge 571
unrelated models on the first real edit, and an acknowledgement nobody can read
is one nobody reads. So the answer states the node count and the group size, and says
outright when every base in the key is zero -- `answer.facts` carries the same
three as data (`node_count`, `group_size`, `contentless`) so a caller can TIER
instead of blanket-acknowledging. The criterion did not move; the answer just
stopped hiding the one fact that decides whether it means anything. There is no
threshold anywhere in here: "all bases are zero" is a property of the array,
not a cutoff somebody chose.

m_seqCount IS RECORDED, NOT ENFORCED. The client refuses a linked object whose
`m_seqCount` is zero (`cmp [ecx+0x6C], 0` at 0x00794917); `unitassembly.py`
deliberately does not replicate that gate, and neither does this walk -- an
edge is recorded for every resolvable target and `seq_count` sits on the head
record as a fact, so a caller that wants the client's acceptance semantics can
apply the gate itself. Replicating it here would DROP edges, and an index that
silently drops edges is exactly the wrong direction of error for a tool whose
whole job is to answer "who else".

HEAD_FLAGS LIVES HERE. `[e.index for e in ar.entries if e.flags == 515]` is the
archive-wide model-head enumeration; before this module it was a local constant
and a comprehension copy-pasted in three test files, with no importable home.
This is the home. The copies are not touched -- three independent spellings of
the same filter are three witnesses, and consolidating them is a separate
change from adding the first one that can be imported.

DECODING IS PER CHUNK, not through `mdlrefs.ref_lists()`, and the rule is
`mdlrefs`' either way (`RefList.decode` is the same decoder, and `mdlrefs` still
owns the record rule). The difference is attribution: `ref_lists` decodes all
five lists as one unit, so a malformed FA5 would take a head's FA8 links down
with it and the problem record would name the head rather than the list. Here a
refusal is scoped to the chunk that refused, the head's other lists still index,
and `index.problems` names which list it was.

THE STAMP AND WHAT IT DOES NOT CATCH. A saved index carries the archive's size
on disk and the sha256 of its MFT bytes, and `load(path, ar)` refuses a
mismatch -- a stale index answering for a changed archive is the shape of
failure `vaultpath.require_dir` exists to refuse, arrived at from the other
side. It is an MFT stamp, so it sees every row that moved, resized, or had its
crc rewritten. It does NOT see a payload edited in place without its row's crc
being updated -- that state fails `datcheck --crc-sweep`, which is the tool for
it, and claiming otherwise here would be a check that cannot fail.

COST. A full pass reads and decompresses every flags-515 container -- ~21k of
them on retail -- and decodes an FA1 skeleton for most, so it is minutes, not
seconds. The CLI prints progress every 1,000 rows. `build(ar, rows=[...])`
walks a named subset instead for a spot check; the index it returns is marked
`partial` and every answer off it says so, because a floor computed over 20 of
21,421 heads is a floor of a floor.

    python toolkit/mapdata/refindex.py --dat ARCHIVE --build-json OUT
    python toolkit/mapdata/refindex.py --dat ARCHIVE --json IN --who-reads 0x1C7C3
    python toolkit/mapdata/refindex.py --dat ARCHIVE --json IN --who-shares 116228

Exit codes follow `datcheck.py`/`bit31.py`: 0 the index ran, 2 refused or
unreadable. A query answering "nobody" is a RESULT and exits 0 -- there is no
exit code for it, deliberately, because it is a floor and not a verdict.
"""

import argparse
import hashlib
import json
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import (Archive, FILE_ID_HIGH_BIT, ffna_chunks,   # noqa: E402
                     ffna_type, file_id_table)
from atex import Refused                                       # noqa: E402
# The write guard is IMPORTED, not re-typed. `bit31.resolve_out` already
# refuses C:\gw, vault/dat_study and every checkout of this repo, in that
# order, and the comment on it records what the first version of it got wrong.
# A second copy here would be a second thing to keep correct.
from bit31 import resolve_out                                  # noqa: E402
import mdlrefs                                                 # noqa: E402
from mdlrefs import REF_CHUNKS, RefList                        # noqa: E402
import skelfile                                                # noqa: E402
from skelfile import GEOMETRY_CHUNK, SKELETON_CHUNK, Skeleton  # noqa: E402

#: "Addressable model-file head" -- the flags value every archive-wide model
#: sweep in this repo filters on (`studies/unitmodels` section 2.1).
HEAD_FLAGS = 515

MODEL_FFNA_TYPE = mdlrefs.MODEL_FFNA_TYPE
#: 2: the graph is keyed by MFT row and the spelling map is persisted. A
#: version-1 file is refused rather than read -- its edges are keyed by one
#: arbitrary spelling of each target, which is the defect this bump exists for.
FORMAT_VERSION = 2
PROGRESS_EVERY = 1000

#: Chunk id -> the name an answer reports. Derived from `mdlrefs.REF_CHUNKS`
#: rather than written out, so a sixth reference chunk added there arrives here
#: named rather than as a KeyError.
CHUNK_NAMES = {cid: f"{cid:03X}" for cid in REF_CHUNKS}

#: The ids a head's SIGNATURE is taken over -- geometry, skeleton, and the five
#: reference lists. `studies/mdlrefs` section 7's "FA1-only class" is a
#: signature of exactly (FA1,) in these terms.
TRACKED_CHUNKS = (GEOMETRY_CHUNK, SKELETON_CHUNK) + REF_CHUNKS

MECHANISM_REFS = ("FA5/FA6/FA8/FAD/FAE reference lists on flags-"
                  f"{HEAD_FLAGS} heads")
MECHANISM_SKEL = ("bit-identical blk2C base arrays -- node count plus sha256 "
                  "-- over the heads carrying an FA1 chunk")

#: Fields of the stamp that decide "is this the same archive?". The path is
#: NOT one of them: `datcheck.diff` gates its row labels on bytes rather than
#: on path strings for the same reason -- a copy at another path with identical
#: bytes IS the same archive, and the same path with different bytes is not.
IDENTITY_FIELDS = ("size_on_disk", "mft_size", "row_count", "mft_sha256")


# ---------------------------------------------------------------------------
# Enumeration and identity
# ---------------------------------------------------------------------------

def head_rows(ar):
    """Every addressable model-file head row, in row order.

    THE importable spelling of the sweep filter. Uses `ar.entries` (positional)
    and reads `e.index` off each entry rather than indexing by row, which is
    the trap `archive.Archive.row` exists for.
    """
    return [e.index for e in ar.entries if e.flags == HEAD_FLAGS]


def display_id(fids):
    """The id a row is REPORTED under when several ids name it.

    A LABEL, not an identity, and the difference is the whole point. Rows named
    by more than one file id are not a corner case: MEASURED on
    `vault/dat_study/Gw.dat` 2026-08-20 by inverting `file_id_table(raw=True)`,
    38,396 rows carry two names -- 12,860 of the 21,421 flags-515 heads (60.0%)
    and 25,536 non-head rows, the textures and sounds an FA5/FA6 list points at.
    Nine of the 38,396 involve a bit-31 spelling; the other 38,387 are two
    perfectly ordinary plain ids, so `min()` over them is an ORDERING
    CONVENTION and nothing more.

    That is exactly the kind of convention this repo has been burned by
    ("last one wins" picked the wrong client build three times), so nothing is
    allowed to rest on it: the graph is keyed by ROW, every query resolves its
    argument through `index.fid_row` before it looks anything up, every record
    carries the full `fids` list, and `canonical_id()` exists so a caller can
    normalise its own ids the same way. Picking the other end of the sort would
    change what these answers are CALLED and not one thing about what they say.

    Plain ids are preferred over bit-31 ones for the label because a bit-31
    spelling means "this row's replacement is pending" (`FcArchive`, 0x007D7B70)
    -- archive state that stops resolving when the replacement lands, while the
    plain name outlives it.
    """
    plain = [f for f in fids if not f & FILE_ID_HIGH_BIT]
    return min(plain) if plain else min(fids)


def stamp_of(ar):
    """The archive's identity: what it is, how big, and its MFT's sha256."""
    ar.fh.seek(ar.mft_offset)
    mft = ar.fh.read(ar.mft_size)
    if len(mft) != ar.mft_size:
        raise Refused(
            f"cannot stamp {ar.path}\n"
            f"  the MFT at 0x{ar.mft_offset:X} is {ar.mft_size} bytes but only "
            f"{len(mft)} could be read. A stamp over a short read would name a "
            f"table that is not there.\n"
            f"  Check the archive first:  python toolkit/mapdata/datcheck.py "
            f"--dat {ar.path} --preflight")
    return {"archive": os.path.abspath(ar.path),
            "size_on_disk": os.path.getsize(ar.path),
            "mft_offset": ar.mft_offset,
            "mft_size": ar.mft_size,
            "row_count": ar.row_count,
            "block_size": ar.block_size,
            "mft_sha256": hashlib.sha256(mft).hexdigest()}


def check_stamp(index, ar, why="answer for"):
    """Refuse to use `index` against an archive it was not built from."""
    now = stamp_of(ar)
    bad = [k for k in IDENTITY_FIELDS if index.stamp.get(k) != now[k]]
    if bad:
        rows = "\n".join(f"    {k}: {index.stamp.get(k)!r} -> {now[k]!r}"
                         for k in bad)
        raise Refused(
            f"REFUSING to {why} {now['archive']} with this index\n"
            f"  It was built from a different archive state:\n{rows}\n"
            f"  A stale index answers 'nobody else reads this row' about rows "
            f"that have since moved, which is the one wrong answer this tool "
            f"must never give.\n"
            f"  Re-build it:  python toolkit/mapdata/refindex.py --dat "
            f"{now['archive']} --build-json <out>")
    if index.stamp.get("archive") != now["archive"]:
        # Legitimate -- two byte-identical copies of the same cut -- but it is
        # said out loud rather than assumed, `bit31.py`'s cross-copy note.
        print(f"  NOTE: this index was built from {index.stamp.get('archive')!r}, "
              f"byte-identical to this one")
    return now


# ---------------------------------------------------------------------------
# The answer type
# ---------------------------------------------------------------------------

class Answer(list):
    """A query result that states what it is a floor OF.

    A `list`, so every caller indexes, iterates, sorts and compares it exactly
    as the signature says; `str(answer)` is the sentence, and the CLI prints
    it. Keeping the two together is the point: the number alone reads as a
    census, and this index cannot take a census (see the module docstring).

    `notes` are the sentences specific to THIS answer (what the file id
    resolved to, what the shared key actually is); `facts` is the same material
    as data, for a caller that has to tier rather than print. A gate reading
    `facts` and a human reading `str()` must never be looking at two different
    stories, so both are built in one place, by the query.
    """

    def __init__(self, items, index, noun, mechanism, subject="", notes=(),
                 facts=None):
        super().__init__(items)
        self.index = index
        self.noun = noun
        self.mechanism = mechanism
        self.subject = subject
        self.notes = list(notes)
        self.facts = dict(facts or {})

    def note(self):
        head = f"{self.subject}: " if self.subject else ""
        lines = [f"{head}at least {len(self)} {self.noun}, by the mechanisms "
                 f"this index can see ({self.mechanism})."]
        lines += [f"  NOTE: {n}" for n in self.notes]
        lines += [f"  BLIND SPOT: {b}" for b in self.index.blind_spots()]
        return "\n".join(lines)

    __str__ = note


# ---------------------------------------------------------------------------
# The index
# ---------------------------------------------------------------------------

class Index:
    """One archive's inverted reference graph, plus the facts a query needs.

    Keyed by MFT ROW throughout -- `heads`, `targets`, `edges` and the sharing
    groups. `fid_row` is the only door between a file id and a row, and every
    public query goes through it (module docstring, "EVERY SPELLING OF A ROW
    ANSWERS THE SAME").
    """

    __slots__ = ("stamp", "heads", "targets", "edges", "unresolved",
                 "problems", "partial", "walked", "fid_row", "canon",
                 "groups", "group_zero")

    def __init__(self, stamp, heads, targets, edges, unresolved, problems,
                 partial=False, walked=None):
        self.stamp = stamp
        self.heads = heads              # head ROW -> head record
        self.targets = targets          # referenced ROW -> [every file id]
        self.edges = edges              # target ROW -> [(referrer ROW, kind)]
        self.unresolved = unresolved    # references naming no row at all
        self.problems = problems        # heads/lists this index could not read
        self.partial = partial
        # WALKED IS NOT len(heads), and the difference is the point: a head
        # that would not read is walked and not indexed, so reporting only the
        # second number would quietly shrink the archive.
        self.walked = len(heads) if walked is None else walked
        self.fid_row = {}
        self.canon = {}
        self.groups = {}
        self.group_zero = {}
        # EVERY SPELLING OF EVERY ROW THIS INDEX HOLDS, heads and targets
        # alike. Targets are the half the first version left out, and they are
        # the half that matters most: 25,536 of the multiply-named rows on
        # retail are NOT heads -- they are the textures and sounds an FA5/FA6
        # list names, so a head-only alias map cannot resolve them at all.
        for row, fids in self.targets.items():
            self._register(row, fids)
        for row, rec in self.heads.items():
            self._register(row, rec.get("fids", ()))
            if rec.get("skel"):
                key = (rec["node_count"], rec["skel"])
                self.groups.setdefault(key, []).append(row)
                self.group_zero[key] = bool(rec.get("zero_bases"))
        for group in self.groups.values():
            group.sort()

    def _register(self, row, fids):
        for fid in fids:
            self.fid_row[fid] = row
        if fids:
            self.canon.setdefault(row, display_id(fids))

    # -- resolution ----------------------------------------------------------

    def row_of(self, fid):
        """The row `fid` names, or None if this index holds no such row.

        None is NOT "nothing references it" -- this index records spellings for
        head rows and for referenced rows, so an id naming an ordinary
        unreferenced texture resolves to None too. Every query that gets a None
        says so in its own note rather than answering a bare empty list.
        """
        return self.fid_row.get(fid)

    def fids_of(self, row):
        """Every file id the raw table gave that row, sorted."""
        rec = self.heads.get(row)
        if rec is not None:
            return list(rec.get("fids", ()))
        return list(self.targets.get(row, ()))

    def names_of(self, fid):
        """Every spelling of the row `fid` names, the reported one first."""
        row = self.row_of(fid)
        if row is None:
            return []
        canon = self.canon.get(row)
        return [canon] + [f for f in self.fids_of(row) if f != canon]

    # -- facts ---------------------------------------------------------------

    def _sig(self, row):
        rec = self.heads.get(row)
        if rec is None:
            return None
        present = set(rec["chunks"]) & set(TRACKED_CHUNKS)
        return tuple(c for c in TRACKED_CHUNKS if c in present)

    def signature(self, fid):
        """The head's chunk signature over `TRACKED_CHUNKS`, or None.

        Takes a FILE ID like every other public entry point here; `_sig` is the
        row-keyed one. Row numbers and file ids are both small ints and one
        function that took either could not tell them apart.
        """
        return self._sig(self.row_of(fid))

    def blind_spots(self):
        """The sentences every answer off this index carries. Computed."""
        out = []
        n = len(_unreferenced(self))
        out.append(
            f"{n} FA1-only head(s) here are named by no reference list this "
            f"index read, so something it cannot see reaches them "
            f"(studies/mdlrefs/FINDINGS.md section 7 leaves that OPEN)")
        out.append(
            "mid/tail companion streams (the 0xBB8-0xBC1 and 0xFAC families) "
            "are not addressable by file id, so a reference through one is "
            "not countable here even in principle")
        if self.problems:
            out.append(
                f"{len(self.problems)} container(s) or list(s) would not read "
                f"or decode and were not indexed -- see index.problems")
        if self.partial:
            out.append(
                f"this index walked {self.walked} named head row(s), not the "
                f"whole archive: it is PARTIAL, so every count off it is a "
                f"floor of a floor")
        return out

    # -- persistence ---------------------------------------------------------

    def to_dict(self):
        return {"format_version": FORMAT_VERSION,
                "stamp": self.stamp,
                "partial": self.partial,
                "walked": self.walked,
                "heads": {str(r): rec for r, rec in sorted(self.heads.items())},
                "targets": {str(r): list(f)
                            for r, f in sorted(self.targets.items())},
                "edges": {str(t): [list(e) for e in v]
                          for t, v in sorted(self.edges.items())},
                "unresolved": self.unresolved,
                "problems": self.problems}

    @classmethod
    def from_dict(cls, doc):
        heads = {int(r): rec for r, rec in doc["heads"].items()}
        targets = {int(r): [int(f) for f in v]
                   for r, v in doc["targets"].items()}
        edges = {int(t): [(int(r), str(k)) for r, k in v]
                 for t, v in doc["edges"].items()}
        return cls(doc["stamp"], heads, targets, edges,
                   doc.get("unresolved", []), doc.get("problems", []),
                   bool(doc.get("partial")), doc.get("walked"))


def _problem(fid, row, why):
    return {"file_id": fid, "row": row, "why": why}


def build(ar, rows=None, progress=0):
    """Walk every model head once and invert what it references.

    `rows` names a subset of head ROW NUMBERS for a spot check -- row numbers,
    not file ids, because that is what enumeration produces; it is marked
    `partial` and says so in every answer. The default walks `head_rows(ar)`.
    `progress` prints a line every N rows, 0 for silence -- a library call
    should not print, and a twenty-minute CLI run should.
    """
    # THE ROW -> SPELLINGS MAP IS THE INVERSE OF THE SAME TABLE the lookups
    # use, deliberately. `mapchunks.stored_file_ids` reads MFT row 2 as it sits
    # and would answer with a spelling that `file_id_table` binds to some OTHER
    # row (it takes the first record per id); an index whose two directions
    # disagreed would resolve a query to a row nothing was filed under.
    table = file_id_table(ar, raw=True)     # what the CLIENT can address
    by_row = {}
    for fid, row in table.items():
        by_row.setdefault(row, []).append(fid)
    for fids in by_row.values():
        fids.sort()

    walk = head_rows(ar) if rows is None else sorted(set(rows))
    heads_out, targets, edges, unresolved, problems = {}, {}, {}, [], []
    t0 = time.time()

    for n, row in enumerate(walk, 1):
        if progress and n % progress == 0:
            print(f"  {n}/{len(walk)} heads, {len(edges)} row(s) named "
                  f"({time.time() - t0:.0f}s)")
        fids = by_row.get(row, ())
        if not fids:
            # A USED|FIRST_STREAM head no file-id record names is datcheck's
            # rule 7 and the client's own reconcile deletes it. Here it is a
            # problem rather than a skip because nothing it references could
            # be attributed to a referrer the client can address.
            problems.append(_problem(
                None, row, "no file id in the raw table names this head row"))
            continue
        fid = display_id(fids)
        try:
            data = ar.read(ar.row(row))
        except Exception as exc:                            # noqa: BLE001
            # BROAD ON PURPOSE: a decompressor raising struct.error or
            # MemoryError on one damaged row must not end the pass. The row is
            # named in `problems`, which is what the blind-spot note counts.
            problems.append(_problem(
                fid, row, f"unreadable: {type(exc).__name__}: {exc}"))
            continue
        if data[:4] != b"ffna" or ffna_type(data) != MODEL_FFNA_TYPE:
            problems.append(_problem(
                fid, row, f"not an ffna type-{MODEL_FFNA_TYPE} container: "
                          f"magic {bytes(data[:4])!r}, type {ffna_type(data)}"))
            continue
        try:
            chunk_list = list(ffna_chunks(data))
        except ValueError as exc:
            problems.append(_problem(fid, row, f"chunk table: {exc}"))
            continue

        rec = {"fids": list(fids),
               "chunks": sorted({c for c, _, _ in chunk_list}),
               "refs": {}, "seq_count": None,
               "node_count": None, "skel": None, "zero_bases": None}
        heads_out[row] = rec

        for cid, off, size in chunk_list:
            if cid not in REF_CHUNKS:
                continue
            kind = CHUNK_NAMES[cid]
            try:
                rl = RefList.decode(bytes(data[off:off + size]))
            except mdlrefs.Undecodable as exc:
                # An unreadable list is a finding, not an absence (mdlrefs'
                # own posture). The head keeps its other lists.
                problems.append(_problem(fid, row, f"{kind} list: {exc}"))
                continue
            rec["refs"][kind] = len(rl)
            for target in rl.file_ids():
                if target is None:
                    continue                    # a null slot: FA5's, no target
                trow = table.get(target)
                if trow is None:
                    # Under `raw=True` a plain spelling of a renamed row really
                    # does resolve to nothing -- that is what the client sees.
                    unresolved.append({"referrer": fid, "referrer_row": row,
                                       "kind": kind, "file_id": target})
                    continue
                # Filed under the target's ROW, with every spelling of that row
                # recorded, so all of them answer the same question later.
                targets.setdefault(trow, list(by_row.get(trow, (target,))))
                seen = edges.setdefault(trow, [])
                if (row, kind) not in seen:
                    # Deduped: FA8 lists do repeat a target, and the question
                    # is who reads this file, not how many times.
                    seen.append((row, kind))

        if SKELETON_CHUNK in rec["chunks"]:
            try:
                skel = Skeleton.from_container(data)
                nodes = None if skel is None else skel.anims()
            except (skelfile.Undecodable, ValueError, struct.error) as exc:
                problems.append(_problem(
                    fid, row, f"FA1 skeleton: {type(exc).__name__}: {exc}"))
            else:
                if nodes is not None:
                    rec["seq_count"] = skel.seq_count
                    rec["node_count"] = len(nodes)
                    rec["skel"] = hashlib.sha256(b"".join(
                        struct.pack("<3f", *a["base"]) for a in nodes
                    )).hexdigest()
                    # A PROPERTY OF THE ARRAY, not a threshold: an all-zero
                    # base array is a key with no pose in it, and every head
                    # carrying one keys identically to every other. `-0.0 ==
                    # 0.0` is true and is meant to be -- retail's degenerate
                    # node is literally (-0.0, -0.0, -0.0).
                    rec["zero_bases"] = all(
                        v == 0.0 for a in nodes for v in a["base"])

    for v in edges.values():
        v.sort()
    return Index(stamp_of(ar), heads_out, targets, edges, unresolved, problems,
                 partial=rows is not None, walked=len(walk))


# ---------------------------------------------------------------------------
# Queries. Every one of them answers with a floor.
# ---------------------------------------------------------------------------

def canonical_id(index, fid):
    """The id this index REPORTS `fid`'s row under; `fid` itself if unknown.

    For a caller comparing its own ids against an answer -- an overlay
    manifest's `acknowledge_shared_with` against `who_reads`, say. Both sides
    must be normalised through here: 0x138D1 and 0x491C0 are one row on retail,
    and a gate comparing the two numbers would report a complete declaration as
    incomplete. Unknown ids come back unchanged rather than as None, so a
    caller can normalise a whole list without special-casing.
    """
    row = index.row_of(fid)
    return fid if row is None else index.canon.get(row, fid)


def _unknown_note(index, fid):
    return (f"no head row and no referenced row in this index is named by "
            f"{fid} (0x{fid:X}). This index records every spelling of every "
            f"head row and of every row a reference list names, so that is "
            f"either an id this archive does not hold or a row nothing here "
            f"references -- resolve it against the archive to tell them apart")


def _alias_note(index, fid, names):
    others = ", ".join(f"0x{f:X}" for f in names if f != fid)
    return (f"0x{fid:X} names row {index.row_of(fid)}, which is also named "
            f"{others}. This answer is about the ROW, so every spelling of it "
            f"gives the same one")


def who_reads(index, fid):
    """Heads whose reference lists name `fid`: [(referrer_fid, kind), ...].

    A floor, and the `Answer` says which mechanisms it is a floor of. An empty
    result means "no mechanism this index can see reaches it" -- which is a
    real and interesting state (it is how `unreferenced_fa1_heads` is built)
    and is NOT a licence to overwrite the row.

    Resolves `fid` to a ROW first, so every spelling of a multiply-named row
    answers identically. `facts`: resolved, row, names.
    """
    row = index.row_of(fid)
    names = index.names_of(fid)
    items = sorted((index.canon.get(r, r), kind)
                   for r, kind in index.edges.get(row, ()))
    notes = []
    if row is None:
        notes.append(_unknown_note(index, fid))
    elif len(names) > 1:
        notes.append(_alias_note(index, fid, names))
    return Answer(items, index, "referrer(s)", MECHANISM_REFS,
                  subject=f"who reads {fid} (0x{fid:X})", notes=notes,
                  facts={"resolved": row is not None, "row": row,
                         "names": names})


def who_shares_skeleton(index, fid):
    """Heads whose blk2C base array is bit-identical to `fid`'s, excluding it.

    Same (node count, sha256-of-bases) group. A floor for a different reason
    from `who_reads`: a head this index could not decode carries no hash, so it
    joins no group, and a skeleton that is nearly identical is not in the group
    either -- this criterion is bit-identity, not similarity.

    The answer carries the key's node count, the group size, and whether every
    base in it is zero, in the sentence AND in `facts` -- see the module
    docstring. A caller tiering on a contentless key is reading the same fact
    the printed answer states.
    """
    row = index.row_of(fid)
    rec = index.heads.get(row)
    items, notes = [], []
    facts = {"resolved": row is not None, "row": row, "node_count": None,
             "group_size": 0, "contentless": None}
    if row is None:
        notes.append(_unknown_note(index, fid))
    elif rec is None:
        # True of an ordinary texture AND of a head that would not read, so it
        # says both rather than asserting which -- the second is in problems.
        notes.append(f"0x{fid:X} names row {row}, which this index holds only "
                     f"as a reference TARGET and not among the heads it "
                     f"indexed, so it wears no skeleton here; a head that "
                     f"would not read is in index.problems")
    elif not rec.get("skel"):
        notes.append("this head carries no FA1 chunk in this index, so it "
                     "wears no skeleton -- an empty answer for a reason other "
                     "than 'nobody else wears it'")
    else:
        key = (rec["node_count"], rec["skel"])
        group = index.groups.get(key, ())
        items = sorted(index.canon.get(r, r) for r in group if r != row)
        facts.update(node_count=rec["node_count"], group_size=len(group),
                     contentless=bool(rec.get("zero_bases")))
        notes.append(f"the shared key is {rec['node_count']} blk2C node(s) and "
                     f"the group holds {len(group)} head(s) counting this one")
        if rec.get("zero_bases"):
            notes.append(
                "EVERY base in that array is zero, so the key carries no pose: "
                "these heads group because none of them carries one, not "
                "because they share one. studies/unitmodels 3.11 measured the "
                "bit-identical criterion on 86-to-105-node skeletons -- tier "
                "on node_count/contentless rather than treating this like one "
                "of those")
    if row is not None and len(index.names_of(fid)) > 1:
        notes.append(_alias_note(index, fid, index.names_of(fid)))
    return Answer(items, index, "co-wearer(s) of this skeleton",
                  MECHANISM_SKEL,
                  subject=f"who shares {fid} (0x{fid:X})'s skeleton",
                  notes=notes, facts=facts)


def _unreferenced(index):
    """The plain list behind `unreferenced_fa1_heads` (no Answer, no recursion
    -- `Answer.note` asks for this count, so it must not build an Answer).

    Reads `index.edges` by ROW, which is what makes it spelling-proof: a head
    named by both a plain and a bit-31 id is reachable under either, and the
    first version of this module had to check every spelling by hand here while
    `who_reads` checked only one -- two answers about one row, and they
    disagreed. Keying on the row is the structural fix, not a second habit.
    """
    out = []
    for row, rec in index.heads.items():
        if index._sig(row) != (SKELETON_CHUNK,):
            continue
        if row not in index.edges:
            out.append(index.canon.get(row, row))
    return sorted(out)


def unreferenced_fa1_heads(index):
    """FA1-only heads that no reference list in this index names.

    "FA1-only" is the chunk signature `studies/mdlrefs` section 7 uses: over
    the tracked ids (FA0/FA1 and the five lists) the head carries FA1 and
    nothing else. That study measured the class on retail, found most of it to
    be FA8 targets, and left the remainder OPEN -- "reached some other way".
    This function computes THIS archive's remainder rather than asserting that
    study's count, which is what makes it a measurement here and a citation
    there.

    Every id here is the REPORTED spelling of its row, as in the other two
    queries; run a caller's own ids through `canonical_id` before comparing
    against this list rather than matching the numbers as strings.
    """
    return Answer(_unreferenced(index), index,
                  "FA1-only head(s) nothing here names",
                  MECHANISM_REFS, subject="reached by no mechanism this index "
                                          "can see")


# ---------------------------------------------------------------------------
# Persistence. A vault artifact: an index of retail rows describes retail.
# ---------------------------------------------------------------------------

def _out_path(path):
    try:
        return resolve_out(path)
    except Refused as exc:
        raise Refused(f"refusing to write a reference index to "
                      f"{os.path.abspath(path)}\n  {exc}")


def save(index, path):
    """Write the index as JSON. Refuses the install, dat_study and checkouts."""
    out = _out_path(path)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(index.to_dict(), fh, indent=1)
    return out


def load(path, ar=None):
    """Read an index back. With `ar`, refuses one built from another archive.

    Every shape check here is one an answer depends on. A half-validated index
    reaching `who_reads` answers "nobody" by KeyError-free accident, and this
    module's one unacceptable output is a confident empty list.
    """
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise Refused(f"could not read the index {path}: "
                      f"{type(exc).__name__}: {exc}")
    if not isinstance(doc, dict):
        raise Refused(f"{path} is a {type(doc).__name__}, not an index object")
    if doc.get("format_version") != FORMAT_VERSION:
        raise Refused(
            f"{path} is format_version {doc.get('format_version')!r}, this "
            f"tool writes {FORMAT_VERSION}. Re-build the index rather than "
            f"read one across formats:  python toolkit/mapdata/refindex.py "
            f"--dat <archive> --build-json {path}")
    for key, kind in (("stamp", dict), ("heads", dict), ("edges", dict),
                      ("targets", dict)):
        if not isinstance(doc.get(key), kind):
            raise Refused(f"{path} has no {key!r} object; it is not an index")
    for key in IDENTITY_FIELDS:
        if key not in doc["stamp"]:
            raise Refused(
                f"{path}'s stamp is missing {key!r}, so it cannot be matched "
                f"against an archive. Re-build it.")
    try:
        index = Index.from_dict(doc)
    except (TypeError, ValueError, KeyError) as exc:
        raise Refused(f"{path} is malformed: {type(exc).__name__}: {exc}")
    if ar is not None:
        check_stamp(index, ar, why="answer for")
    return index


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_fid(text):
    """A file id from the command line: decimal, or 0x-prefixed hex."""
    t = text.strip()
    try:
        return int(t, 16) if t.lower().startswith("0x") else int(t, 10)
    except ValueError:
        raise Refused(f"{text!r} is not a file id. Give a decimal number or "
                      f"an 0x-prefixed hex one.")


def largest_group(index):
    """(members, node_count, contentless) of the biggest sharing group, or None.

    Reported because the headline "N groups are shared" is not readable on its
    own: on retail the biggest group is hundreds of heads keyed on a single
    all-zero node, and a summary that did not say so would make a degenerate
    key look like a rig hundreds of models wear.
    """
    if not index.groups:
        return None
    # Ties broken by the lowest member row, so the same index always reports
    # the same group -- including after a JSON round trip.
    key, rows = max(index.groups.items(),
                    key=lambda kv: (len(kv[1]), -kv[1][0]))
    return (len(rows), key[0], index.group_zero.get(key, False))


def format_summary(index):
    shared = {k: v for k, v in index.groups.items() if len(v) > 1}
    zero_shared = {k: v for k, v in shared.items() if index.group_zero.get(k)}
    lines = [f"{index.stamp['archive']}",
             f"  {index.stamp['row_count']} rows, MFT at "
             f"0x{index.stamp['mft_offset']:X}, "
             f"{index.stamp['size_on_disk']} bytes on disk",
             f"  {index.walked} head row(s) walked, {len(index.heads)} indexed"
             + (" (PARTIAL: a named subset)" if index.partial else ""),
             # The second half of this line is the population the row keying
             # exists for: every one of those rows answers to two names, and
             # each of them has to give the same answer.
             f"  {len(index.edges)} row(s) are named by at least one reference "
             f"list, {sum(1 for r in index.edges if len(index.fids_of(r)) > 1)}"
             f" of them under more than one file id",
             f"  {len(index.groups)} skeleton group(s), {len(shared)} of them "
             f"worn by more than one head"]
    big = largest_group(index)
    if big:
        lines.append(f"    largest: {big[0]} head(s) sharing a {big[1]}-node "
                     f"array" + (" whose bases are ALL ZERO -- a contentless "
                                 "key" if big[2] else ""))
    if zero_shared:
        lines.append(f"    {len(zero_shared)} shared group(s) key on an "
                     f"all-zero base array, holding "
                     f"{sum(len(v) for v in zero_shared.values())} head(s)")
    lines.append(f"  {len(index.problems)} problem(s), "
                 f"{len(index.unresolved)} reference(s) naming no row")
    for b in index.blind_spots():
        lines.append(f"  BLIND SPOT: {b}")
    return lines


def _describe(index, fid):
    names = index.names_of(fid)
    if len(names) > 1:
        return (f"  0x{fid:X} is row {index.row_of(fid)}, named "
                + ", ".join(f"0x{f:X}" for f in names))
    return ""


def _run(args):
    if args.json and args.build_json and os.path.abspath(
            args.json) == os.path.abspath(args.build_json):
        raise Refused(
            f"--json and --build-json name the same file "
            f"({os.path.abspath(args.json)}). Reading an index and then "
            f"writing over it makes the stamp check answer about the file it "
            f"just wrote.")
    want_reads = parse_fid(args.who_reads) if args.who_reads else None
    want_shares = parse_fid(args.who_shares) if args.who_shares else None
    # EVERY REFUSAL DECIDED BEFORE THE TWENTY-MINUTE PASS, and before anything
    # is written: `bit31.py` shipped the other order and refused the baseline
    # after it had already replaced the output file.
    if args.build_json:
        _out_path(args.build_json)

    with Archive(args.dat) as ar:
        if args.json:
            index = load(args.json, ar)
            print(f"index <- {args.json}")
        else:
            index = build(ar, progress=PROGRESS_EVERY)
    print("\n".join(format_summary(index)))
    if args.build_json:
        print(f"index -> {save(index, args.build_json)}")

    if want_reads is not None:
        print()
        answer = who_reads(index, want_reads)
        print(answer)
        line = _describe(index, want_reads)
        if line:
            print(line)
        for referrer, kind in answer:
            print(f"  {referrer} (0x{referrer:X}) via {kind}, row "
                  f"{index.row_of(referrer)}")
    if want_shares is not None:
        print()
        answer = who_shares_skeleton(index, want_shares)
        print(answer)
        line = _describe(index, want_shares)
        if line:
            print(line)
        for other in answer:
            print(f"  {other} (0x{other:X}), row {index.row_of(other)}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", required=True, help="the archive to read ('rb')")
    ap.add_argument("--build-json", metavar="OUT",
                    help="write the index here (vault or scratch, never a "
                         "checkout)")
    ap.add_argument("--json", metavar="IN",
                    help="use this saved index instead of building one; "
                         "refused if it was built from another archive")
    ap.add_argument("--who-reads", metavar="FID",
                    help="which heads name this file id (decimal or 0x hex)")
    ap.add_argument("--who-shares", metavar="FID",
                    help="which heads wear this file id's skeleton")
    args = ap.parse_args(argv)
    try:
        return _run(args)
    except Refused as exc:
        print(f"REFUSED: {exc}")
        return 2
    except Exception as exc:                                   # noqa: BLE001
        # Broad for `bit31.py`'s reason: an unreadable archive must never leave
        # by the interpreter's own exit code and be read as a result.
        print(f"REFUSED: could not index {args.dat}: "
              f"{type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
