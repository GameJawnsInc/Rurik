r"""Archive profiles that are DECLARED, reversible, and identifiable from bytes.

    python toolkit/mapdata/overlay.py --plan   vault/overlays/slowmo.toml
    python toolkit/mapdata/overlay.py --build  vault/overlays/slowmo.toml
    python toolkit/mapdata/overlay.py --status vault/overlays/slowmo.toml
    python toolkit/mapdata/overlay.py --deploy vault/overlays/slowmo.toml --yes
    python toolkit/mapdata/overlay.py --retail vault/overlays/slowmo.toml --yes
    python toolkit/mapdata/overlay.py --verify-after vault/overlays/slowmo.toml

WHY IT EXISTS. Ten staged experiments live under `vault/research/archivewrite/`
as ten hand-written scripts -- `a4stage.py` through `a10stage.py`, 190 KB of
them -- and each one carries its own copy of the same five decisions: which
archive is ACTIVE, which is RETAIL, which rows it owns, what the fingerprint of
a deployed profile is, and how to get back. They agree because they were copied
from each other, which is not the same as agreeing because something checks.
`a9stage.py` and `a10stage.py` differ by 42 KB and neither is derivable from the
other. This module is that shape written once, driven by a manifest, so the next
profile is a TOML file and not a fork.

THE V1 SCOPE IS EDIT-IN-PLACE, AND IT IS A DECISION RATHER THAN A LIMIT.
`datwrite.replace` is the only write verb reachable from here -- including its
`grow_to` grow-back. No `datalloc` creation, no `datmove` relocation: those two
put rows where nothing had them and move rows out from under a client that may
still be holding a stale free list, and both are proven exactly once each in a
stage script. A creation stays in a stage script until a SECOND client-proven
chain shape exists to generalise from; generalising from one is how the ten
scripts happened. A payload that does not fit is REFUSED here and named, with
`datmove.py` given as the manual remedy.

THE ARCHIVE IS ADDRESSED BY FILE ID, NEVER BY ROW NUMBER. A row number is a
position in one archive's table; the file id is what the client asks for, and
the two stop agreeing the moment anything relocates. Every `[[edit]]` names a
file id, and the id is resolved against RETAIL at plan time through the raw
table -- `file_id_table(ar, raw=True)`, what the CLIENT can address, not the
convenience table that would answer for a masked spelling the client would miss.
Two records naming one id are a REFUSAL and not a coin toss: `file_id_table`
takes the first record per id (`setdefault`), so a duplicate would silently pick
one and this walks the records itself to see both.

THE REFINDEX GATE, AND WHY IT IS TIERED. `studies/unitmodels` 3.11 measured six
of seven claimed skeleton-sharing pairs at 0.0000 u per-node distance --
bit-identical rest poses -- so editing one model's rig silently edits every
model wearing it, and nothing warned. `refindex.py` answers "who else reads
this?" and this is the caller that turns an answer into a refusal: an edit whose
file id has co-readers or co-wearers must LIST them in its own
`acknowledge_shared_with`, per edit, in the manifest, the way
`stored_lookalike_ok` is a per-call declaration and not a global flag.

The two halves are NOT gated the same way, and the asymmetry is measured rather
than chosen. A `who_reads` co-reader is a real reference: some head's FA5/FA6/
FA8/FAD/FAE list names this file, and a writer who does not know that is about
to change what that head loads. Those always require acknowledgement. A
`who_shares_skeleton` co-wearer is a bit-identical blk2C base array -- and
applied population-wide that criterion also groups the DEGENERATE arrays, a
whole skeleton of one node at (-0.0, -0.0, -0.0), which every other such head
keys identically to. MEASURED on a 1,500-head sample of `vault/dat_study`: 572
heads sit in ONE such group. Demanding 571 acknowledgements on the first real
edit is not a gate, it is a rubber stamp with a training effect, and the
acknowledgement nobody can read is the one nobody reads. So: a contentless group
(`answer.facts["contentless"]`, a property of the array and not a threshold
anybody chose) prints its note and does not refuse; every other group does.

EVERY ID IS NORMALISED THROUGH `refindex.canonical_id` BEFORE IT IS COMPARED,
both sides, and this is load-bearing. A row carries several file ids -- 38,396
rows on retail, 12,860 of them flags-515 heads, 60% -- so an operator who writes
`acknowledge_shared_with = [0x491C0]` and an index that answers `0x138D1` are
naming ONE row, and a gate comparing the numbers as written would report a
complete declaration as incomplete and send them off to add an id that is
already there. The manifest's own `file_id` goes through it too.

THE FLOOR SENTENCE IS PRINTED VERBATIM. `str(answer)` is `refindex`'s own
sentence naming what the count is a floor OF and which mechanisms it cannot see.
It is not re-composed here into "N co-readers", because the number alone reads
as a census and this index cannot take one. A caller reading the printed line
and a gate reading `answer.facts` must never be looking at two different
stories.

BUILDING AN INDEX OF A REAL ARCHIVE COSTS ~15.5 MINUTES AND ~10 MB SAVED, so the
manifest may name one: `refindex = "slowmo.refindex.json"`. It is loaded
stamp-checked against RETAIL -- `refindex.load(path, ar)`, always with `ar`,
because an index loaded without its archive answers confidently about rows that
have since moved, and "nobody else reads this row" is the one wrong answer this
gate must never repeat. With no path named, one is built from scratch and the
cost is printed BEFORE the wait rather than discovered during it.

AN INDEX THAT COULD NOT SEE IT IS NOT AN INDEX THAT SAW NOTHING, and the stamp
does not cover that. A stamped, current, correctly-loaded index still answers
EMPTY for a row whose only referrers sit in `index.problems` -- a head whose
container would not decode is walked and not indexed, and its FA8 list is
therefore not in the graph. Same for a `partial` index, which walked a named
subset for a spot check and says so in `index.partial`. Both states clear the
stamp and produce exactly the confident empty answer `refindex`'s own docstring
calls its one unacceptable output, so `index_faults` reads all three fields
before any edit is gated:

  * `index.partial` is a HARD refusal. There is no acknowledgement that makes a
    floor computed over twenty of twenty-one thousand heads mean anything.
  * `index.problems` must be DECLARED, by count, as `accept_unread = N` in
    `[overlay]`. A count and not a flag on purpose: a new unreadable head moves
    the number and the refusal comes back, where a `true` would go on covering
    a blind spot as it grew. This is `stored_lookalike_ok`'s shape -- an
    explicit declaration of a measured thing -- with the measurement in it.
  * and the index's own resolution of an edited file id is CROSS-CHECKED
    against the row RETAIL's raw table gave it. `refindex` says outright that
    "this archive does not hold that id" and "nothing here references that row"
    cannot be told apart from an index alone; this caller has already resolved
    the id against the archive, so it can tell them apart and does. A
    disagreement is a refusal: the MFT stamp does not see a file-id table
    edited in place without its row's crc updated, which is precisely the state
    that would make the index answer about a different row than the one being
    written.

WHAT A DEPLOY MAY START FROM IS THREE-VALUED AND CAN FAIL, which is
`a10stage.baseline_premise()`'s shape and its reasoning: the ACTIVE archive is
shared between sessions, so "it is probably retail" is a guess, and a profile
deployed on top of an unknown archive produces a result nobody can score. The
answer is read from the ACTIVE archive's own bytes on the rows this profile
owns: RETAIL on all of them, THIS profile already deployed, or NEITHER -- and
NEITHER is a hard refusal naming `--retail --yes` as the verb that makes the
state known again. `--retail` itself takes NO premise: retail's whole job is to
MAKE the active archive retail again, and measuring the premise beforehand would
refuse the one verb that fixes an unknown archive.

A POST-FLIGHT IS MEASURED AGAINST THE BEFORE-IMAGE THE DEPLOY TOOK, and against
nothing else. `--deploy` writes both halves of that image beside the staged
copy -- `datcheck.write_snapshot` for the MFT and a fingerprint record for the
rows this profile owns -- and `--verify-after` reads BOTH of them back and
refuses if the two do not describe one deploy (the record carries the
snapshot's sha256). The build record is deliberately NOT the comparand: it
describes what was staged, not what was put into the ACTIVE archive, and the
two stop agreeing the moment anything writes to ACTIVE that this tool did not
stage. Measured, with no client anywhere near it: `--build`, `--deploy --yes`,
`--retail --yes`, `--verify-after` reported "the client wrote to a row this
overlay owns" about bytes `--retail` had written thirty seconds earlier. So the
before-image is INVALIDATED by the two verbs that make it untrue -- `--retail`,
which replaces the whole archive, and a successful `--build`, which replaces the
staged copy the image belongs to -- and a post-flight with no before-image
refuses rather than reporting what the archive merely is.

A FINGERPRINT IS COMPUTED FROM THE STORED BYTES, not read out of the MFT. It is
`[size, crc32(stored bytes), compression]` per touched row, and the crc is
recomputed from disk rather than taken from the entry's crc field on purpose: a
payload edited in place without its crc being updated is a state `datcheck
--preflight` cannot see at all (it has no notion of a compression code and does
not re-read payloads), and it is exactly the state a half-finished write leaves.
Comparing the MFT's own field against itself would be a check that cannot fail.

WHAT THIS WRITES, AND WHERE. Everything except the ACTIVE archive the manifest
names lives under the vault: the staged copy at
`vault/exports/overlays/<name>/Gw.<name>.dat`, its journal, its fingerprints,
and the pre-launch snapshot beside it. A staged archive is retail bytes with a
few rows changed -- ArenaNet's bytes verbatim, nearly all of it -- so it lives
where the gitignore can see it or it does not get written. `C:\gw` and
`vault/dat_study` are refused for BOTH the active and the retail path, not just
the written one: `--retail --yes` and `--build` both COPY the retail archive, and
a manifest that names the owner's own install as a participant in a deploy loop
is a manifest one flag away from writing there.

NOTHING HERE LAUNCHES A CLIENT. `a10stage.py`'s separation is kept deliberately:
staging archive bytes is one tool and launching is another, so the launch
re-runs its own gates (`cage.assert_launch_safe`, and `datcheck.assert_archive_safe`
where that exists) rather than trusting that this one already checked. A guard
that only guards one of two doors is the shape of the defect it is there to
prevent.

Exit codes follow `datcheck.py`/`bit31.py`: 0 the verb ran, 1 a mechanical
result that is a finding (`--verify-after` found an integrity fault), 2 refused
or unreadable.
"""

import argparse
import binascii
import hashlib
import json
import os
import re
import shutil
import struct
import sys
import time
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import (Archive, FILE_ID_TABLE_ROW,           # noqa: E402
                     COMPRESSION_STORED, COMPRESSION_HUFFMAN)
import datcheck                                            # noqa: E402
# The write path, the two path refusals and the reservation arithmetic are all
# IMPORTED. `datwrite` owns the grow gate; the 2026-09-11 split moved the other
# two out to `datjournal.Journal` and `datdecl.declaration_fault`, both of which
# `datwrite` still re-exports, so the name you reach here is unchanged;
# a second copy of any of them here is a second thing to keep in agreement with
# the first, and this module's whole argument is that ten copies did not stay
# in agreement.
import datwrite                                            # noqa: E402
from datwrite import reservation_for                       # noqa: E402
import gwenc                                               # noqa: E402
import refindex                                            # noqa: E402
from refindex import canonical_id                          # noqa: E402
import vaultpath                                           # noqa: E402

# FORMAT, FORMAT_VERSION, NAME_RE, EXPORT_PARTS, MANIFEST_KEYS and EDIT_KEYS are
# now toolkit/mapdata/overlaystate.py, verbatim, with the manifest and record
# code that is the only thing that reads the last three. The re-export sits
# HERE, where they were cut from, and not in the import block at the top of the
# file. FORMAT and FORMAT_VERSION are read below by build() and deploy(), and
# from outside by datcheck.py (936/938/942), test_abrun.py (391/392) and
# test_datcheck.py (1224/1225). NAME_RE has no reader at all -- it is named in
# COMMENTS at abrun.py:622 and test_abrun.py:1057 as `overlay.NAME_RE`, and the
# re-export is what keeps those two sentences true.
from overlaystate import (FORMAT, FORMAT_VERSION,          # noqa: F401,E402
                          NAME_RE)

IN_RESERVATION = "in-reservation"
GROW_BACK = "grow-back"
TOO_BIG = "does-not-fit"

STATE_RETAIL = "retail"
STATE_OTHER = "OTHER"

# STAMP_FIELDS moved with the record half to toolkit/mapdata/overlaystate.py,
# verbatim with its comment. Nothing in this file reads it any more -- the one
# reader is datcheck.py:999, which walks it to compare a record's retail stamp
# against the archive on disk -- and the re-export at the site it was cut from
# is what keeps `overlay.STAMP_FIELDS` resolving for that caller.
from overlaystate import STAMP_FIELDS                      # noqa: F401,E402


# The manifest, the paths and the records are now
# toolkit/mapdata/overlaystate.py, verbatim: _inside, guard_archive, the six
# path builders, Edit, Manifest, _refuse_manifest, _rel, _read_bytes,
# load_manifest, mft_sha256, archive_identity, id_records, rows_named_by,
# fingerprint_block, looks_like_retail, _body, _self_sha, write_fingerprints,
# _file_sha256, RECORD_KINDS and load_fingerprints. The re-export sits HERE,
# where they were cut from, and not in the import block at the top of the file,
# because what reads these names is (a) plan(), build(), deployed_state(),
# deploy(), restore_retail(), verify_after() and main() below, all by bare name
# at sites that therefore stayed byte-identical; (b) test_overlay.py's sabotage
# ledger, which patches `overlay.looks_like_retail`, `overlay.id_records`,
# `overlay.rows_named_by` and `overlay.load_fingerprints` and needs those
# callers to resolve through THIS module's globals for the patch to land; and
# (c) datcheck.py (945 `_self_sha`, 968 `load_manifest`, 988
# `archive_identity`), abrun.py (586 `load_manifest`, 683 `fingerprints_path`,
# 691 `load_fingerprints`, 837 `fingerprint_block`), test_abrun.py (11
# `load_manifest` sites, `staged_path`, `journal_path`, `write_fingerprints`,
# `fingerprints_path`, `archive_identity`, `fingerprint_block`),
# test_datcheck.py and test_overlay.py (`_inside`, `journal_path`,
# `fingerprints_path`, `staged_path`, the two `prelaunch_*` paths).
#
# `_inside` has NO caller in this file and never had one -- its only reader is
# test_overlay.py:1164, which asserts the staged archive really is under the
# vault. It is re-exported for that test alone; do not go hunting for a
# production call site.
#
# NOT re-exported, because nothing outside overlaystate.py reads them
# (grepped, whole tree, .py and .md): guard_archive, export_root, staged_dir,
# Edit, Manifest, _refuse_manifest, _rel, _read_bytes, mft_sha256, _body,
# EXPORT_PARTS, MANIFEST_KEYS, EDIT_KEYS, RECORD_KINDS.
#
# The four docstring sections that argue this code stayed in this file's
# docstring -- WHAT THIS WRITES AND WHERE, A FINGERPRINT IS COMPUTED FROM THE
# STORED BYTES, A POST-FLIGHT IS MEASURED AGAINST THE BEFORE-IMAGE THE DEPLOY
# TOOK, THE V1 SCOPE IS EDIT-IN-PLACE -- because they are also the verbs'
# refusal reasoning and main()'s --help, and overlaystate.py's header names all
# four by title and by file.
from overlaystate import (_inside, staged_path,            # noqa: F401,E402
                          fingerprints_path, journal_path,
                          prelaunch_snapshot_path,
                          prelaunch_fingerprints_path,
                          load_manifest, archive_identity, id_records,
                          rows_named_by, fingerprint_block,
                          looks_like_retail, _self_sha, write_fingerprints,
                          _file_sha256, load_fingerprints)


# ---------------------------------------------------------------------------
# Fit: what a row can be given without moving anything
# ---------------------------------------------------------------------------

class Fit:
    """Whether `new_len` bytes go into a row, and at what cost. Pure."""

    __slots__ = ("verdict", "cur_res", "want_res", "ceiling", "grow_to")

    def __init__(self, verdict, cur_res, want_res, ceiling, grow_to):
        self.verdict = verdict
        self.cur_res = cur_res
        self.want_res = want_res
        self.ceiling = ceiling
        self.grow_to = grow_to

    def __repr__(self):
        return (f"Fit({self.verdict}, cur_res={self.cur_res}, "
                f"want_res={self.want_res}, ceiling={self.ceiling}, "
                f"grow_to={self.grow_to})")


def fit_of(cur_size, donor_size, new_len, block):
    """Three-valued, and the middle value is the one worth reading about.

    `cur_size` is the row's size in the archive the bytes will land in;
    `donor_size` is the SAME row's size in RETAIL. A row owns whole blocks, so
    its reservation is `ceil(size/block)*block` whatever its size field says.

      in-reservation  the payload fits what the row currently holds. No gate
                      runs; this is `datwrite.replace`'s oldest behaviour and
                      the case nearly every edit is in.
      grow-back       the payload is bigger than the row's CURRENT reservation
                      but no bigger than the reservation RETAIL gave it. The
                      row's own freed blocks are what it grows into, and the
                      `grow_to` handed to `datwrite.replace` is `donor_size` --
                      sourced from the donor row, never invented to make a
                      write fit (`datwrite.replace`'s own hazard note).
      does-not-fit    bigger than retail ever gave this row. Refused, naming
                      `datmove.py`: that is a relocation, which is a different
                      and much more dangerous operation than a replacement.

    ON A FRESH COPY OF RETAIL THE MIDDLE CELL IS UNREACHABLE, and saying so is
    better than pretending otherwise: `cur_size == donor_size` there, so the
    ceiling IS the current reservation and the fit is binary. It exists for the
    archive whose row has already been shrunk -- the authoring loop
    `datwrite.replace`'s `grow_to` was written for, "the second, larger output
    onto a row the first write shrank" -- which is why `apply_edits` recomputes
    the fit against the file it is actually opening rather than trusting the
    plan's numbers from RETAIL.
    """
    cur_res = reservation_for(cur_size, block)
    want_res = reservation_for(new_len, block)
    ceiling = reservation_for(max(cur_size, donor_size), block)
    if want_res <= cur_res:
        return Fit(IN_RESERVATION, cur_res, want_res, ceiling, None)
    if want_res <= ceiling:
        return Fit(GROW_BACK, cur_res, want_res, ceiling, donor_size)
    return Fit(TOO_BIG, cur_res, want_res, ceiling, None)


# The refindex gate is now toolkit/mapdata/overlayrefgate.py, verbatim:
# INDEX_COST, resolve_index, _problem_lines, index_faults, index_row_fault and
# gate_edit. The re-export sits HERE, where they were cut from, and not in the
# import block at the top of the file, because what reads these names is (a)
# `plan()` below, by bare name at four sites that therefore stayed
# byte-identical, and (b) test_overlay.py's sabotage ledger, which patches
# `overlay.gate_edit` / `overlay.index_faults` / `overlay.index_row_fault` and
# needs `plan()` to resolve through THIS module's globals for the patch to
# land. No other file in the tree reads any of these four names. The five
# docstring sections that argue this gate stayed in this file's docstring --
# they are also `plan()`'s refusal reasoning and `main()`'s --help -- and
# overlayrefgate.py's header names all five by title.
from overlayrefgate import (resolve_index, index_faults,   # noqa: F401,E402
                            index_row_fault, gate_edit)


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------

class EditPlan:
    __slots__ = ("edit", "row", "donor_size", "donor_compression", "fit",
                 "co_readers", "co_wearers", "notes", "answers")

    def __init__(self, edit, row, donor_size, donor_compression, fit,
                 co_readers, co_wearers, notes, answers):
        self.edit = edit
        self.row = row
        self.donor_size = donor_size
        self.donor_compression = donor_compression
        self.fit = fit
        self.co_readers = co_readers
        self.co_wearers = co_wearers
        self.notes = notes
        self.answers = answers


class Plan:
    __slots__ = ("manifest", "retail_identity", "block", "edits", "index")

    def __init__(self, manifest, retail_identity, block, edits, index):
        self.manifest = manifest
        self.retail_identity = retail_identity
        self.block = block
        self.edits = edits
        self.index = index

    @property
    def rows(self):
        return [p.row for p in self.edits]


def plan(manifest, index=None, echo=True):
    """Everything that can be refused, decided BEFORE anything is copied.

    Read-only: this opens RETAIL and nothing else. Every gate here runs while
    the archive is untouched and no journal exists, because after a write there
    is nothing left that can tell the difference (`datwrite.replace`'s own
    ordering, for its own reason).
    """
    for role, path in (("active", manifest.active), ("retail", manifest.retail)):
        if not os.path.isfile(path):
            raise SystemExit(
                f"REFUSED: overlay {manifest.name!r} names {path} as its "
                f"{role} archive and there is no file there.\n"
                f"  Both paths are relative to the manifest "
                f"({manifest.dir}), never to the shell.")
    with Archive(manifest.retail) as ar:
        identity = archive_identity(ar)
        block = ar.block_size
        records = id_records(ar)
        rows, per_edit = {}, []
        for i, edit in enumerate(manifest.edits):
            named = rows_named_by(records, edit.file_id)
            if not named:
                raise SystemExit(
                    f"REFUSED: [[edit]] {i} names file id {edit.label} and no "
                    f"record in {manifest.retail}'s file-id table names it.\n"
                    f"  This is an exact 32-bit compare, the one the client "
                    f"does (0x0047AA20): a bit-31 spelling and its plain form "
                    f"are two different ids and only one of them binds.\n"
                    f"  python toolkit/mapdata/bit31.py --dat "
                    f"{manifest.retail}  lists the renamed ones.")
            if len(named) > 1:
                raise SystemExit(
                    f"REFUSED: [[edit]] {i}'s file id {edit.label} is named by "
                    f"{len(named)} records in {manifest.retail}, pointing at "
                    f"rows {named}.\n"
                    f"  `archive.file_id_table` would silently take the first "
                    f"of them and this edit would land on whichever row that "
                    f"happens to be. Which row the client resolves is not "
                    f"something to guess at.\n"
                    f"  python toolkit/mapdata/datcheck.py --dat "
                    f"{manifest.retail} --preflight  reports the table's own "
                    f"invariants.")
            row = named[0]
            if row in rows:
                raise SystemExit(
                    f"REFUSED: [[edit]] {i} ({edit.label}) and [[edit]] "
                    f"{rows[row]} resolve to the SAME row {row}. Two payloads "
                    f"cannot both be what a reader gets back.")
            rows[row] = i
            e = ar.row(row)
            fault = datwrite.declaration_fault(edit.data, edit.compression,
                                               edit.plain)
            if fault:
                raise SystemExit(
                    f"REFUSED: [[edit]] {i} ({edit.label}, row {row}) cannot be "
                    f"written as compression {edit.compression}.\n"
                    f"  {fault}\n"
                    f"  The entry crc is over the STORED bytes, so a row whose "
                    f"payload is wrong passes all three checksum rules and all "
                    f"ten of datcheck --preflight's. This is the only "
                    f"refutation there is.")
            f = fit_of(e.size, e.size, len(edit.data), block)
            if f.verdict == TOO_BIG:
                raise SystemExit(
                    f"REFUSED: [[edit]] {i} ({edit.label}) is {len(edit.data)} "
                    f"B and row {row} was given {f.ceiling} B by RETAIL "
                    f"({e.size} used, {block}-byte blocks).\n"
                    f"  That is a relocation, not a replacement, and this tool "
                    f"does not relocate: v1 is edit-in-place only.\n"
                    f"  Either make the payload fit, or move the row by hand "
                    f"with  python toolkit/mapdata/datmove.py  and re-plan "
                    f"against the moved archive.")
            per_edit.append(EditPlan(edit, row, e.size, e.compression, f,
                                     [], [], [], None))

        idx = resolve_index(manifest, ar, index=index, echo=echo)

    # BEFORE ANY EDIT IS GATED: can this index answer at all? A partial or
    # part-blind index clears the stamp and answers empty, which is the one
    # wrong answer the gate exists to prevent.
    unread = index_faults(idx, manifest)
    if echo and unread:
        print(f"  index: {unread} unreadable container(s)/list(s), declared as "
              f"accept_unread = {unread}")

    refusals = []
    for i, p in enumerate(per_edit):
        fault = index_row_fault(idx, p.edit, p.row)
        if fault:
            raise SystemExit(
                f"REFUSED: the reference index and {manifest.retail} disagree "
                f"about [[edit]] {i} ({p.edit.label}).\n"
                f"  {fault}\n"
                f"  The MFT stamp cannot see this: a file-id table edited in "
                f"place without its row's crc being updated leaves the stamp "
                f"matching while the table says something else "
                f"(refindex.py, 'THE STAMP AND WHAT IT DOES NOT CATCH').\n"
                f"  python toolkit/mapdata/datcheck.py --dat {manifest.retail} "
                f"--crc-sweep   is the tool for that state.\n"
                f"  Then re-build the index:  python toolkit/mapdata/"
                f"refindex.py --dat {manifest.retail} --build-json <vault path>")
        unack, notes, answers = gate_edit(idx, p.edit, row=p.row)
        p.notes[:] = notes
        p.answers = answers
        p.co_readers[:] = sorted({canonical_id(idx, r) for r, _k in answers[0]}
                                 - {canonical_id(idx, p.edit.file_id)})
        p.co_wearers[:] = sorted({canonical_id(idx, f) for f in answers[1]}
                                 - {canonical_id(idx, p.edit.file_id)})
        if unack:
            listed = ", ".join(f"0x{fid:X}" for fid, _why in unack)
            lines = [f"REFUSED: [[edit]] {i} ({p.edit.label}, row {p.row}) has "
                     f"{len(unack)} co-consumer(s) it does not acknowledge.",
                     "", str(answers[0]), "", str(answers[1]), ""]
            for fid, why in unack:
                lines.append(f"  0x{fid:X} ({fid}) {why}")
            lines += [
                "",
                "  Editing this row changes what every one of those reads. "
                "That is not a reason not to do it -- it is a reason to say "
                "out loud that you know, per edit, the way "
                "`stored_lookalike_ok` is a per-call declaration and not a "
                "global flag.",
                "  Add them to THIS edit in the manifest:",
                f"    acknowledge_shared_with = [{listed}]",
                "  Every spelling of a row is accepted: these ids are the ones "
                "the index reports, and your own are normalised through "
                "refindex.canonical_id before they are compared."]
            refusals.append("\n".join(lines))
    if refusals:
        raise SystemExit("\n\n".join(refusals))

    return Plan(manifest, identity, block, per_edit, idx)


def _indent(text, pad="    "):
    """Every line, not just the first.

    `str(answer)` is a multi-line sentence -- the floor, its notes and its
    blind spots -- and indenting only its first line is how the blind spots
    end up looking like they belong to the plan rather than to the answer.
    """
    return "\n".join(pad + line for line in str(text).splitlines())


def format_plan(p):
    m = p.manifest
    out = [f"overlay {m.name!r}  ({m.path})",
           f"  active  {m.active}",
           f"  retail  {m.retail}",
           f"          {p.retail_identity['size_on_disk']} B, "
           f"{p.retail_identity['row_count']} rows, MFT sha256 "
           f"{p.retail_identity['mft_sha256'][:16]}",
           f"  staged  {staged_path(m)}",
           f"  {len(p.edits)} edit(s), {m.sha256[:16]} manifest sha256"]
    for i, ep in enumerate(p.edits):
        e = ep.edit
        out.append(f"  [[edit]] {i}: {e.label} -> row {ep.row}")
        out.append(f"    retail row: {ep.donor_size} B, compression "
                   f"{ep.donor_compression}, reservation {ep.fit.ceiling}")
        out.append(f"    payload:    {len(e.plain)} B plain -> "
                   f"{len(e.data)} B stored as compression {e.compression} "
                   f"({ep.fit.verdict}, reservation {ep.fit.want_res})")
        if ep.fit.grow_to is not None:
            out.append(f"    grow_to:    {ep.fit.grow_to} B, from the RETAIL "
                       f"donor row -- never invented to make a write fit")
        out.append(_indent(ep.answers[0]))
        out.append(_indent(ep.answers[1]))
        if ep.edit.acknowledge:
            out.append("    acknowledged: "
                       + ", ".join(f"0x{a:X}" for a in ep.edit.acknowledge))
        for note in ep.notes:
            out.append(_indent(note))
    return out


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def apply_edits(target, plan_, journal, echo=True):
    """Write every edit into `target`, journalled. -> {row: fit verdict}.

    THE FIT IS RECOMPUTED AGAINST `target`, not taken from the plan. The plan's
    numbers are RETAIL's, and the file being written is the one whose row sizes
    decide whether a payload fits -- they are the same file on a fresh copy and
    they are not the same file on a staged copy that has already been written
    once. Trusting a precomputed plan is how `datalloc` got a doctored plan past
    every gate it had (2026-08-19); it re-validates for the same reason.
    """
    w = datwrite.Writer(target, journal)
    verdicts = {}
    try:
        block = w.ar.block_size
        for ep in plan_.edits:
            e = w.ar.row(ep.row)
            f = fit_of(e.size, ep.donor_size, len(ep.edit.data), block)
            if f.verdict == TOO_BIG:
                raise SystemExit(
                    f"REFUSED: {ep.edit.label} is {len(ep.edit.data)} B and "
                    f"row {ep.row} of {target} was given {f.ceiling} B.\n"
                    f"  The plan measured this against {plan_.manifest.retail} "
                    f"and the file being written disagrees, which means the "
                    f"target is not the baseline the plan describes.\n"
                    f"  Re-plan:  python toolkit/mapdata/overlay.py --plan "
                    f"{plan_.manifest.path}")
            if echo:
                print(f"  [[edit]] {ep.edit.label} -> row {ep.row} "
                      f"({f.verdict})")
            w.replace(ep.row, ep.edit.data, compression=ep.edit.compression,
                      expect=ep.edit.plain, grow_to=f.grow_to)
            verdicts[ep.row] = f.verdict
    finally:
        w.close()
    return verdicts


def forget_prelaunch(manifest, why, echo=True):
    """Drop the before-image a deploy took. -> the paths that were removed.

    A before-image belongs to ONE deploy of ONE staged copy, and two verbs make
    it untrue rather than merely old: `--retail`, which replaces the whole
    ACTIVE archive with bytes this profile did not stage, and a successful
    `--build`, which replaces the staged copy the image is an image of. Left in
    place, `--verify-after` compares the live archive against it and attributes
    every difference to the client -- MEASURED with no client involved at all:
    build, deploy, retail, verify-after printed "the client wrote to a row this
    overlay owns" about bytes `--retail` had just written.

    Removing it is what makes the next post-flight REFUSE instead of report,
    and `verify_after`'s own sentence is the argument for that: a post-flight
    without its before-image is not a check.
    """
    gone = []
    for path in (prelaunch_snapshot_path(manifest),
                 prelaunch_fingerprints_path(manifest)):
        if os.path.exists(path):
            os.remove(path)
            gone.append(path)
    if gone and echo:
        print(f"  the pre-launch before-image is now untrue ({why}); removed:")
        for path in gone:
            print(f"    {path}")
        print(f"  --verify-after will refuse until the next --deploy writes a "
              f"new one.")
    return gone


def build(manifest, index=None, echo=True):
    """Plan, copy RETAIL, apply, fingerprint. -> the build record.

    The copy is unconditional. A staged archive that was reused across two
    different payloads would carry the older one in every row this manifest
    stopped naming, and nothing downstream could tell -- the fingerprints only
    cover the rows the manifest owns.
    """
    p = plan(manifest, index=index, echo=echo)
    if echo:
        print("\n".join(format_plan(p)))
    stage = staged_path(manifest, create=True)
    if os.path.normcase(os.path.realpath(stage)) == os.path.normcase(
            os.path.realpath(manifest.retail)):
        raise SystemExit(f"REFUSED: the staged copy and RETAIL are the same "
                         f"file ({stage}).")
    jrn = journal_path(manifest)
    if os.path.exists(jrn):
        os.remove(jrn)          # a fresh copy has no history to undo
    if echo:
        print(f"\ncopying {manifest.retail}\n     -> {stage}")
    shutil.copyfile(manifest.retail, stage)

    apply_edits(stage, p, jrn, echo=echo)

    rows = p.rows
    staged_fp = fingerprint_block(stage, rows)
    retail_fp = fingerprint_block(manifest.retail, rows)
    if looks_like_retail(staged_fp, retail_fp):
        raise SystemExit(
            f"REFUSED: overlay {manifest.name!r} built, and every one of its "
            f"{len(rows)} row(s) still carries retail's bytes.\n"
            f"  There is nothing here to deploy, and a build that changed "
            f"nothing looks exactly like a successful one right up until the "
            f"experiment produces a null nobody can explain.\n"
            f"  The staged copy at {stage} is left in place to be looked at.")
    with Archive(stage) as ar:
        staged_identity = archive_identity(ar)
    doc = {"format": FORMAT,
           "format_version": FORMAT_VERSION,
           "overlay": manifest.name,
           "manifest": manifest.path,
           "manifest_sha256": manifest.sha256,
           "built": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "staged": stage,
           "journal": jrn,
           "retail": p.retail_identity,
           "staged_identity": staged_identity,
           "file_ids": {str(ep.row): ep.edit.file_id for ep in p.edits},
           "rows": staged_fp,
           "retail_rows": retail_fp}
    out = write_fingerprints(fingerprints_path(manifest), doc)
    # The staged copy this profile's before-image belongs to has just been
    # replaced, so the image is about a file that no longer exists.
    forget_prelaunch(manifest, "the staged copy was rebuilt", echo=echo)
    if echo:
        print(f"\nstaged  {stage}")
        print(f"journal {jrn}")
        print(f"record  {out}")
        for row in rows:
            print(f"  row {row}: retail {retail_fp[str(row)]} -> staged "
                  f"{staged_fp[str(row)]}")
    return doc


# ---------------------------------------------------------------------------
# The identity oracle
# ---------------------------------------------------------------------------

def deployed_state(manifest, doc=None):
    """What is in the ACTIVE archive right now, on the rows this profile owns.

    Three-valued and it can fail to be either: `"retail"`, the overlay's own
    name, or a string beginning `OTHER` that names the first row that disagrees
    with both. This is what `--status` prints and what a launch-side gate
    consumes as an identity.

    THE FILE IDS ARE RE-RESOLVED FIRST. A row number is a position in one
    archive's table and the client relocates rows during ordinary play, so a
    fingerprint compared by row number alone can be comparing two different
    files. If an id has moved, that IS the answer -- `OTHER` -- rather than a
    fingerprint mismatch reported as if the payload had changed.
    """
    doc = doc or load_fingerprints(manifest, why="report the state of")
    rows = sorted(int(r) for r in doc["rows"])
    with Archive(manifest.active) as ar:
        records = id_records(ar)
        for row_s, fid in sorted(doc["file_ids"].items()):
            named = rows_named_by(records, fid)
            if named != [int(row_s)]:
                return (f"{STATE_OTHER} (file id 0x{fid:X} named row {row_s} in "
                        f"RETAIL and names {named or 'nothing'} in ACTIVE -- "
                        f"the archive has been rearranged under this profile)")
    live = fingerprint_block(manifest.active, rows)
    if all(live.get(k) == v for k, v in doc["retail_rows"].items()):
        return STATE_RETAIL
    if all(live.get(k) == v for k, v in doc["rows"].items()):
        return manifest.name
    for row in rows:
        k = str(row)
        if live.get(k) != doc["retail_rows"].get(k) \
                and live.get(k) != doc["rows"].get(k):
            return (f"{STATE_OTHER} (row {row} is {live.get(k)}, which is "
                    f"neither retail's {doc['retail_rows'].get(k)} nor this "
                    f"overlay's {doc['rows'].get(k)})")
    return (f"{STATE_OTHER} (the touched rows are a MIXTURE of retail and "
            f"{manifest.name!r}: a half-applied deploy)")


# ---------------------------------------------------------------------------
# Deploy, restore, verify
# ---------------------------------------------------------------------------

def _require_yes(yes, verb, manifest):
    if not yes:
        raise SystemExit(
            f"REFUSED: --{verb} writes over {manifest.active}, which is the "
            f"archive a client opens and which other sessions share.\n"
            f"  Nothing has been written. Re-run with --yes when you mean it:\n"
            f"    python toolkit/mapdata/overlay.py --{verb} {manifest.path} "
            f"--yes")


def _require_closed(manifest):
    """The client holds Gw.dat open exclusively while it runs. Probe for it."""
    try:
        open(manifest.active, "r+b").close()
    except PermissionError:
        raise SystemExit(
            f"REFUSED: {manifest.active} cannot be opened for writing.\n"
            f"  The client holds Gw.dat open exclusively while it runs -- "
            f"close the game window first.") from None
    except OSError as exc:
        raise SystemExit(f"REFUSED: {manifest.active}: {exc}") from None


def _banner(manifest, src, label, premise):
    return [
        "",
        "  !! " + "-" * 68,
        f"  !! REPLACING {manifest.active}",
        f"  !!      with {src}",
        f"  !!            ({label})",
        f"  !! the ACTIVE archive is SHARED: another session pointing a client "
        f"at it",
        f"  !! is about to be pointed at this instead.",
        f"  !! baseline premise: {premise}",
        f"  !! what is NOT replaced: nothing. This is a whole-file copy, so "
        f"the client's",
        f"  !! own relocations, its recompiled maps and its file-id table go "
        f"with it.",
        "  !! " + "-" * 68,
        "",
    ]


def deploy(manifest, yes=False, echo=True):
    """Put the staged copy into the ACTIVE archive. -> the premise that held."""
    _require_yes(yes, "deploy", manifest)
    doc = load_fingerprints(manifest, why="deploy")
    stage = doc["staged"]
    if not os.path.isfile(stage):
        raise SystemExit(
            f"REFUSED: the build record names {stage} and there is no file "
            f"there. Re-build:  python toolkit/mapdata/overlay.py --build "
            f"{manifest.path}")
    rows = sorted(int(r) for r in doc["rows"])
    now = fingerprint_block(stage, rows)
    for k, v in doc["rows"].items():
        if now.get(k) != v:
            raise SystemExit(
                f"REFUSED: the staged copy at {stage} is not what the build "
                f"record describes.\n"
                f"  row {k}: record says {v}, the file says {now.get(k)}\n"
                f"  Something has written to the staged archive since it was "
                f"built. Re-build rather than deploy bytes nobody planned.")
    if looks_like_retail(now, doc["retail_rows"]):
        raise SystemExit(
            f"REFUSED: every row of the staged copy still carries retail's "
            f"bytes. Deploying it would succeed and change nothing, which is "
            f"the one failure that looks exactly like success.")

    premise = deployed_state(manifest, doc)
    if premise.startswith(STATE_OTHER):
        raise SystemExit(
            f"REFUSED: {manifest.active} is neither retail nor "
            f"{manifest.name!r} on the rows this profile owns.\n"
            f"  {premise}\n"
            f"  Something else is deployed, and an arm recorded on top of it "
            f"is unscoreable -- there would be no way afterwards to say what "
            f"the archive was during the run.\n"
            f"  Make the state known first:\n"
            f"    python toolkit/mapdata/overlay.py --retail {manifest.path} "
            f"--yes")
    _require_closed(manifest)
    if echo:
        print("\n".join(_banner(manifest, stage, f"overlay {manifest.name!r}",
                                premise)))
    shutil.copyfile(stage, manifest.active)
    snap = prelaunch_snapshot_path(manifest)
    datcheck.write_snapshot(manifest.active, snap)
    pre = {"format": FORMAT,
           "format_version": FORMAT_VERSION,
           "overlay": manifest.name,
           "manifest": manifest.path,
           "manifest_sha256": manifest.sha256,
           "deployed": time.strftime("%Y-%m-%dT%H:%M:%S"),
           "active": manifest.active,
           "premise": premise,
           "snapshot": snap,
           # THE TWO HALVES OF THE BEFORE-IMAGE ARE TIED TOGETHER. The MFT
           # snapshot and these row fingerprints are two files written one
           # after the other and read back together; a post-flight run against
           # one half of one deploy and one half of another would compare the
           # live archive to a moment that never existed.
           "snapshot_sha256": _file_sha256(snap),
           "retail": doc["retail"],
           "staged": doc["staged"],
           "staged_rows": doc["rows"],
           "file_ids": doc["file_ids"],
           # WHAT THE ARCHIVE WAS, READ BACK OFF THE ARCHIVE, after the copy
           # and never from the build record -- the build record describes what
           # was staged, and only this describes what was deployed.
           "rows": fingerprint_block(manifest.active, rows),
           "retail_rows": doc["retail_rows"]}
    write_fingerprints(prelaunch_fingerprints_path(manifest), pre)
    if echo:
        print(f"deployed. pre-launch snapshot {snap}")
        print(f"          pre-launch rows     "
              f"{prelaunch_fingerprints_path(manifest)}")
    return premise


def restore_retail(manifest, yes=False, echo=True):
    """Copy RETAIL over ACTIVE. NO premise check, and that is deliberate.

    `a10stage.swap`'s reasoning, kept: only --deploy needs the premise, because
    measuring it beforehand would refuse the one verb that fixes an unknown
    archive. This verb's whole job is to MAKE the state known.

    It does discard whatever the client wrote -- its recompiled maps, its
    relocated file-id table -- because it is a whole-file copy. That is stated
    in the banner rather than guarded against.
    """
    _require_yes(yes, "retail", manifest)
    _require_closed(manifest)
    if echo:
        print("\n".join(_banner(manifest, manifest.retail, "the RETAIL "
                                "baseline", "(not measured: --retail)")))
    shutil.copyfile(manifest.retail, manifest.active)
    # THE BEFORE-IMAGE IS NOW A LIE, and it is the one this verb tells. Every
    # touched row just changed, and a post-flight left holding the deploy's
    # image would read those changes back as "the client wrote to a row this
    # overlay owns" -- measured, with no client running.
    forget_prelaunch(manifest, "--retail replaced the whole ACTIVE archive",
                     echo=echo)
    if echo:
        print(f"restored. {manifest.active} is the retail baseline again.")
    return STATE_RETAIL


def verify_after(manifest, echo=True):
    """Post-flight: what did the client do to the archive? -> a dict.

    Mechanical only. It re-runs the ten open-time rules, re-checks every USED
    row's crc against its stored bytes, and diffs the MFT against the snapshot
    `--deploy` took, then says which of THIS profile's rows moved or changed.
    Nothing here is a verdict about the experiment.

    THE COMPARAND IS THE DEPLOY'S BEFORE-IMAGE, NOT THE BUILD RECORD. Both are
    fingerprint records of the same rows and they say different things: the
    build record is what was STAGED, the pre-launch record is what the ACTIVE
    archive WAS when the copy landed. Reading the first one here attributes
    every difference to the client, including the differences this tool's own
    other verbs made -- MEASURED, no client involved: build, deploy,
    `--retail --yes`, verify-after, and the post-flight named a row `--retail`
    had rewritten seconds earlier as one "the client wrote to". Both halves of
    the image are read back and required to describe ONE deploy; the verbs that
    make the image untrue delete it (`forget_prelaunch`), so the failure mode
    here is a refusal rather than a confident wrong attribution.
    """
    snap = prelaunch_snapshot_path(manifest)
    if not os.path.isfile(snap):
        raise SystemExit(
            f"REFUSED: there is no pre-launch snapshot at {snap}.\n"
            f"  A post-flight without its before-image is not a check -- it "
            f"can only report what the archive is, never what it became.\n"
            f"  It is written by:  python toolkit/mapdata/overlay.py --deploy "
            f"{manifest.path} --yes")
    doc = load_fingerprints(manifest, why="verify", kind="prelaunch")
    got = _file_sha256(snap)
    if doc.get("snapshot_sha256") != got:
        raise SystemExit(
            f"REFUSED: the two halves of the before-image do not describe one "
            f"deploy.\n"
            f"  {prelaunch_fingerprints_path(manifest)} names a snapshot with "
            f"sha256 {doc.get('snapshot_sha256')}\n"
            f"  {snap} is {got}\n"
            f"  One of them has been replaced since the deploy, so a diff "
            f"across the pair would compare the live archive against a moment "
            f"that never existed.\n"
            f"  Deploy again to take a fresh pair:  python toolkit/mapdata/"
            f"overlay.py --deploy {manifest.path} --yes")
    rows = sorted(int(r) for r in doc["rows"])
    try:
        checks, _facts = datcheck.preflight(manifest.active)
        sweep = datcheck.crc_sweep(manifest.active)
        before = datcheck.load_snapshot(snap)
        d = datcheck.diff(before, path=manifest.active)
    except (ValueError, OSError, KeyError, struct.error) as exc:
        raise SystemExit(f"REFUSED: cannot read {manifest.active} far enough "
                         f"to have findings at all: "
                         f"{type(exc).__name__}: {exc}") from None
    live = fingerprint_block(manifest.active, rows)
    touched = []
    for row in rows:
        k = str(row)
        if live.get(k) != doc["rows"].get(k):
            touched.append({"row": row, "was": doc["rows"].get(k),
                            "now": live.get(k)})
    moved = [rec for rec in d["changes"] if rec["row"] in set(rows)]
    out = {"preflight": [c.to_json() for c in checks],
           "preflight_failed": [c.name for c in checks if not c.ok],
           "crc_bad": len(sweep["bad"]),
           "crc_checked": sweep["checked"],
           "unchanged": d["unchanged"],
           "changed_rows": len(d["changes"]),
           "our_rows_changed": touched,
           "our_rows_in_diff": [rec["row"] for rec in moved],
           # WHICH MOMENT THIS IS MEASURED AGAINST, in the machine-readable
           # half too: a differential that does not name its before-image is a
           # number a reader will attach to whichever deploy they had in mind.
           "before_image": prelaunch_fingerprints_path(manifest),
           "deployed": doc.get("deployed"),
           "premise": doc.get("premise"),
           "growth": d["growth"]}
    if echo:
        print(f"post-flight on {manifest.active}")
        print(f"  against the before-image the deploy of "
              f"{doc.get('deployed')} took, and against nothing else -- the "
              f"build record describes what was STAGED, which is a different "
              f"question")
        for c in checks:
            print(f"  {c.line()}")
        print(f"  crc sweep: {sweep['checked']} row(s) checked, "
              f"{len(sweep['bad'])} bad, {sweep['skipped']} skipped")
        print(f"  MFT diff vs {snap}: "
              + ("byte for byte unchanged" if d["unchanged"]
                 else f"{len(d['changes'])} changed row(s), "
                      f"{len(d['corroboration'])} corroboration row(s)"))
        if d["growth"]:
            print(f"  the file GREW: {d['growth']}")
        if touched:
            for rec in touched:
                print(f"  row {rec['row']} was {rec['was']} and is now "
                      f"{rec['now']} -- something wrote to a row this overlay "
                      f"owns since the deploy. On a run that is the client; "
                      f"this tool's own verbs delete the before-image rather "
                      f"than let their writes be read as one")
        else:
            print(f"  none of this overlay's {len(rows)} row(s) changed "
                  f"fingerprint")
        print("  NOTHING GUARANTEED EITHER WAY about asserts: Gw.log does not "
              "record them, so a quiet log is not evidence of a quiet client. "
              "crash-dialog.txt is the only machine-readable assert there is.")
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

VERBS = ("plan", "build", "deploy", "retail", "status", "verify_after")


def _run(args):
    chosen = [v for v in VERBS if getattr(args, v)]
    if len(chosen) != 1:
        raise SystemExit(
            "REFUSED: pick exactly one verb.\n"
            "  --plan / --build / --status / --verify-after are read-only-ish;\n"
            "  --deploy and --retail write over the ACTIVE archive and need "
            "--yes.\n"
            "  Running two in one invocation would make the second one's "
            "premise depend on the first, which is the thing --status exists "
            "to measure independently.")
    verb = chosen[0]
    manifest = load_manifest(getattr(args, verb), echo=True)
    if verb == "plan":
        print("\n".join(format_plan(plan(manifest, echo=True))))
    elif verb == "build":
        build(manifest, echo=True)
    elif verb == "deploy":
        deploy(manifest, yes=args.yes, echo=True)
    elif verb == "retail":
        restore_retail(manifest, yes=args.yes, echo=True)
    elif verb == "status":
        state = deployed_state(manifest)
        print(f"overlay {manifest.name!r}: {manifest.active}")
        print(f"  deployed state: {state}")
    else:
        out = verify_after(manifest, echo=True)
        if out["preflight_failed"] or out["crc_bad"]:
            return 1
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    for verb, helptext in (
            ("plan", "resolve, fit and gate every edit. Writes nothing."),
            ("build", "plan, then stage a copy of RETAIL with the edits in it"),
            ("deploy", "put the staged copy into the ACTIVE archive"),
            ("retail", "put the RETAIL baseline back into the ACTIVE archive"),
            ("status", "what is deployed right now, read from ACTIVE's bytes"),
            ("verify-after", "post-flight against the deploy's snapshot")):
        ap.add_argument(f"--{verb}", metavar="MANIFEST", help=helptext)
    ap.add_argument("--yes", action="store_true",
                    help="required by --deploy and --retail; consent is a flag "
                         "because these scripts run non-interactive")
    args = ap.parse_args(argv)
    try:
        return _run(args)
    except SystemExit as exc:
        if isinstance(exc.code, int):
            return exc.code
        print(str(exc.code))
        return 2
    except Exception as exc:                                   # noqa: BLE001
        # Broad for `bit31.py`'s reason: an unreadable archive must never leave
        # by the interpreter's own exit code and be read as a result.
        print(f"REFUSED: {type(exc).__name__}: {exc}")
        return 2


if __name__ == "__main__":
    sys.exit(main())
