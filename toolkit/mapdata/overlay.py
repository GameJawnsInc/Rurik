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
# IMPORTED. `datwrite` owns the journal, the grow gate and `declaration_fault`;
# a second copy of any of them here is a second thing to keep in agreement with
# the first, and this module's whole argument is that ten copies did not stay
# in agreement.
import datwrite                                            # noqa: E402
from datwrite import reservation_for                       # noqa: E402
import gwenc                                               # noqa: E402
import refindex                                            # noqa: E402
from refindex import canonical_id                          # noqa: E402
import vaultpath                                           # noqa: E402

FORMAT = "rurik-overlay-fingerprints"
FORMAT_VERSION = 1

#: `[a-z0-9-]+`. The name becomes a directory and four filenames, so it is
#: constrained at the door rather than sanitised at every use.
NAME_RE = re.compile(r"^[a-z0-9-]+$")

#: Where staged archives live, under the vault and nowhere else.
EXPORT_PARTS = ("exports", "overlays")

MANIFEST_KEYS = frozenset({"name", "active", "retail", "refindex",
                           "accept_unread"})
EDIT_KEYS = frozenset({"file_id", "compression", "plain", "stored",
                       "acknowledge_shared_with"})

IN_RESERVATION = "in-reservation"
GROW_BACK = "grow-back"
TOO_BIG = "does-not-fit"

STATE_RETAIL = "retail"
STATE_OTHER = "OTHER"

#: Fields of the retail stamp a fingerprints record is matched on. `archive` is
#: recorded and deliberately not compared -- `datledger.STAMP_FIELDS` reasons it
#: out: censusing a byte-identical copy under another name is legitimate, and a
#: guard that refuses it is a guard people route around.
STAMP_FIELDS = ("size_on_disk", "mft_offset", "mft_size", "row_count",
                "mft_sha256")

INDEX_COST = ("a full pass reads and decompresses every flags-515 container "
              "-- about 15.5 minutes and ~10 MB of JSON on a retail archive")


# ---------------------------------------------------------------------------
# Paths, and what may never be one
# ---------------------------------------------------------------------------

def _inside(path, root):
    """True if `path` is `root` or below it. Case-folded, and REALPATH'd.

    The realpath is not decoration: a junction pointing out of the vault
    defeats a plain `abspath` compare, and this guard's job is to keep
    ArenaNet's bytes where the gitignore can see them (`datdelta._inside`).
    """
    path = os.path.normcase(os.path.realpath(path))
    root = os.path.normcase(os.path.realpath(root))
    return path == root or path.startswith(root + os.sep)


def guard_archive(path, role):
    """Neither archive a manifest names may be the install or the snapshot.

    `datwrite.guard` and `guard_source` carry the wording and the reasoning, so
    they are called rather than restated; what is added is WHY a read-only role
    is guarded too. `--retail --yes` copies RETAIL over ACTIVE and `--build`
    copies it into the vault, so a manifest naming `C:\\gw\\Gw.dat` as its
    baseline has put the owner's install inside a deploy loop, one flag away
    from being the destination. `vault/dat_study` is the copy every other
    archive is cut from and nothing in this repo can put it back.
    """
    try:
        datwrite.guard(path)
        datwrite.guard_source(path)
    except SystemExit as exc:
        raise SystemExit(
            f"refusing to use {os.path.abspath(path)} as this overlay's "
            f"{role} archive\n"
            f"{exc}\n"
            f"  Both archives a manifest names take part in whole-file copies, "
            f"so naming either of those two here puts them inside a deploy "
            f"loop -- one flag away from being the destination.\n"
            f"  Point {role} at a copy under vault/run/ or vault/dat_*/ that "
            f"you can throw away.") from None
    return os.path.abspath(path)


def export_root(create=False):
    """`vault/exports/overlays`, and a refusal if the vault is not there."""
    vault = vaultpath.require_dir(
        why="a staged overlay is a retail archive with a few rows changed -- "
            "ArenaNet's bytes verbatim, nearly all of it -- so it lives in the "
            "gitignored vault or it does not get written")
    root = os.path.join(vault, *EXPORT_PARTS)
    if create:
        os.makedirs(root, exist_ok=True)
    return root


def staged_dir(manifest, create=False):
    return os.path.join(export_root(create=create), manifest.name)


def staged_path(manifest, create=False):
    d = staged_dir(manifest, create=create)
    if create:
        os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"Gw.{manifest.name}.dat")


def fingerprints_path(manifest):
    return os.path.join(staged_dir(manifest), f"{manifest.name}.fingerprints.json")


def journal_path(manifest):
    return os.path.join(staged_dir(manifest), f"{manifest.name}.journal.json")


def prelaunch_snapshot_path(manifest):
    return os.path.join(staged_dir(manifest),
                        f"{manifest.name}.prelaunch.snapshot.json")


def prelaunch_fingerprints_path(manifest):
    return os.path.join(staged_dir(manifest),
                        f"{manifest.name}.prelaunch.fingerprints.json")


# ---------------------------------------------------------------------------
# The manifest
# ---------------------------------------------------------------------------

class Edit:
    """One row this profile owns, as the manifest declares it.

    `plain` is the payload a READER must get back and is the whole point of the
    field: for a compression-8 edit it is what `datwrite.declaration_fault`
    decodes the stored stream against before a byte is written, which is the
    only refutation that exists -- the entry crc is over the STORED bytes, so a
    compressed row holding the wrong payload passes all three checksum rules and
    all ten of `datcheck --preflight`'s.
    """

    __slots__ = ("file_id", "compression", "plain_path", "stored_path",
                 "acknowledge", "plain", "_data")

    def __init__(self, file_id, compression, plain_path, stored_path,
                 acknowledge, plain):
        self.file_id = file_id
        self.compression = compression
        self.plain_path = plain_path
        self.stored_path = stored_path
        self.acknowledge = list(acknowledge)
        self.plain = plain          # the bytes a reader must get back
        self._data = None           # the bytes that go on disk

    @property
    def data(self):
        """The stored form, computed once and only when something needs it.

        Lazy because `--status` and `--verify-after` do not write anything and
        must not pay for a `gwenc` encode of every compressed edit to answer a
        question about the ACTIVE archive's current bytes.
        """
        if self._data is None:
            if self.compression != COMPRESSION_HUFFMAN:
                self._data = self.plain
            elif self.stored_path:
                self._data = _read_bytes(self.stored_path,
                                         f"{self.label} stored stream")
            else:
                self._data = gwenc.encode(self.plain)
        return self._data

    @property
    def label(self):
        return f"0x{self.file_id:X} ({self.file_id})"


class Manifest:
    __slots__ = ("path", "dir", "name", "active", "retail", "refindex_path",
                 "accept_unread", "edits", "sha256")

    def __init__(self, path, name, active, retail, refindex_path, edits,
                 sha256, accept_unread=None):
        self.path = os.path.abspath(path)
        self.dir = os.path.dirname(self.path)
        self.name = name
        self.active = active
        self.retail = retail
        self.refindex_path = refindex_path
        #: The number of unreadable containers/lists in the gating index this
        #: manifest has LOOKED AT. `None` means "not declared", which is a
        #: different state from "declared zero" and is refused when the index
        #: has any -- see `index_faults`.
        self.accept_unread = accept_unread
        self.edits = edits
        self.sha256 = sha256


def _refuse_manifest(path, why):
    raise SystemExit(
        f"REFUSED: {os.path.abspath(path)} is not a usable overlay manifest\n"
        f"  {why}\n"
        f"  An overlay manifest is:\n"
        f"    [overlay]\n"
        f"    name = \"slowmo\"\n"
        f"    active = \"../run/<build>/Gw.dat\"\n"
        f"    retail = \"../run/<build>/Gw.dat.retail\"\n"
        f"    [[edit]]\n"
        f"    file_id = 0x3AAA\n"
        f"    compression = 0\n"
        f"    plain = \"payloads/x.bin\"\n"
        f"    acknowledge_shared_with = []")


def _rel(manifest_dir, value):
    """A manifest path, resolved against the manifest's OWN directory.

    Never against the working directory: the manifest lives in the vault beside
    its payloads, and a relative path that moved with the shell would name a
    different file from a different terminal.
    """
    return value if os.path.isabs(value) else os.path.join(manifest_dir, value)


def _read_bytes(path, what):
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError as exc:
        raise SystemExit(f"REFUSED: cannot read the {what} at "
                         f"{os.path.abspath(path)}: {exc}") from None


def load_manifest(path, echo=False):
    """Parse and validate a manifest. Nothing is read off any archive here."""
    raw = _read_bytes(path, "manifest")
    try:
        doc = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        _refuse_manifest(path, f"it is not readable TOML: {exc}")

    head = doc.get("overlay")
    if not isinstance(head, dict):
        _refuse_manifest(path, "there is no [overlay] table in it")
    unknown = sorted(set(head) - MANIFEST_KEYS)
    if unknown:
        # A TYPO IS SILENT IN THE DANGEROUS DIRECTION. `refindx = "..."` would
        # leave the manifest naming no index and this tool would go and build
        # one for fifteen minutes; a misspelled key is refused rather than
        # ignored.
        _refuse_manifest(path, f"[overlay] carries unknown key(s) {unknown}; "
                               f"known keys are {sorted(MANIFEST_KEYS)}")
    name = head.get("name")
    if not isinstance(name, str) or not NAME_RE.match(name):
        _refuse_manifest(path, f"overlay.name is {name!r}; it must match "
                               f"[a-z0-9-]+ (it becomes a directory name and "
                               f"four filenames)")
    for key in ("active", "retail"):
        if not isinstance(head.get(key), str) or not head[key].strip():
            _refuse_manifest(path, f"overlay.{key} is missing. Both archives "
                                   f"are named EXPLICITLY and neither is ever "
                                   f"inferred from the other.")
    mdir = os.path.dirname(os.path.abspath(path))
    active = guard_archive(_rel(mdir, head["active"]), "active")
    retail = guard_archive(_rel(mdir, head["retail"]), "retail")
    if os.path.normcase(active) == os.path.normcase(retail):
        _refuse_manifest(
            path, f"overlay.active and overlay.retail name the SAME file "
                  f"({active}). The baseline is what a deploy is measured "
                  f"against and what --retail restores from; if it is also the "
                  f"deploy target then the first deploy destroys it.")
    ridx = head.get("refindex")
    if ridx is not None and (not isinstance(ridx, str) or not ridx.strip()):
        _refuse_manifest(path, f"overlay.refindex is {ridx!r}; it names a "
                               f"saved refindex JSON or is absent")
    ridx = _rel(mdir, ridx) if ridx else None
    unread = head.get("accept_unread")
    if unread is not None and (not isinstance(unread, int)
                               or isinstance(unread, bool) or unread < 0):
        _refuse_manifest(
            path, f"overlay.accept_unread is {unread!r}; it is a COUNT -- the "
                  f"number of containers or reference lists the gating index "
                  f"could not read, which you have looked at. A flag would go "
                  f"on covering a blind spot as it grew; a count moves when "
                  f"the blind spot does.")

    rows = doc.get("edit")
    if not isinstance(rows, list) or not rows:
        _refuse_manifest(path, "there is not one [[edit]] in it. An overlay "
                               "that edits nothing has nothing to deploy.")
    edits, seen = [], {}
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            _refuse_manifest(path, f"[[edit]] {i} is a {type(row).__name__}")
        unknown = sorted(set(row) - EDIT_KEYS)
        if unknown:
            _refuse_manifest(path, f"[[edit]] {i} carries unknown key(s) "
                                   f"{unknown}; known keys are "
                                   f"{sorted(EDIT_KEYS)}")
        fid = row.get("file_id")
        if not isinstance(fid, int) or isinstance(fid, bool) or fid <= 0:
            _refuse_manifest(path, f"[[edit]] {i} has file_id {fid!r}; it must "
                                   f"be a positive integer (0x hex is fine)")
        if fid in seen:
            _refuse_manifest(
                path, f"file id 0x{fid:X} is named by [[edit]] {seen[fid]} AND "
                      f"[[edit]] {i}. Two edits of one row cannot both be the "
                      f"payload a reader gets back, and which one won would "
                      f"depend on the order they happen to sit in.")
        seen[fid] = i
        comp = row.get("compression")
        if comp not in (COMPRESSION_STORED, COMPRESSION_HUFFMAN):
            _refuse_manifest(path, f"[[edit]] {i} has compression {comp!r}; the "
                                   f"archive knows {COMPRESSION_STORED} "
                                   f"(stored) and {COMPRESSION_HUFFMAN} "
                                   f"(huffman) and nothing else")
        plain_rel = row.get("plain")
        if not isinstance(plain_rel, str) or not plain_rel.strip():
            _refuse_manifest(path, f"[[edit]] {i} has no `plain`. It is the "
                                   f"payload a reader must get back and it is "
                                   f"mandatory for both compression codes.")
        stored_rel = row.get("stored")
        if stored_rel is not None and (not isinstance(stored_rel, str)
                                       or not stored_rel.strip()):
            _refuse_manifest(path, f"[[edit]] {i} has stored {stored_rel!r}")
        if stored_rel and comp == COMPRESSION_STORED:
            _refuse_manifest(
                path, f"[[edit]] {i} is compression 0 and also names a "
                      f"`stored` stream. For a stored row the payload IS the "
                      f"bytes on disk; naming two files invites them to differ "
                      f"and only one of them can be written.")
        ack = row.get("acknowledge_shared_with", [])
        if not isinstance(ack, list) or any(
                not isinstance(a, int) or isinstance(a, bool) for a in ack):
            _refuse_manifest(path, f"[[edit]] {i}'s acknowledge_shared_with is "
                                   f"{ack!r}; it is a list of file ids")

        plain_path = _rel(mdir, plain_rel)
        plain = _read_bytes(plain_path, f"[[edit]] {i} payload")
        if not plain:
            _refuse_manifest(path, f"[[edit]] {i}'s payload {plain_path} is "
                                   f"empty; an empty declaration cannot be "
                                   f"checked against anything")
        stored_path = _rel(mdir, stored_rel) if stored_rel else None
        if stored_path and not os.path.isfile(stored_path):
            _refuse_manifest(path, f"[[edit]] {i} names a stored stream at "
                                   f"{stored_path} and there is no file there")
        if echo and comp == COMPRESSION_HUFFMAN and not stored_path:
            print(f"  [[edit]] {i} 0x{fid:X}: {len(plain)} B will be encoded to "
                  f"compression 8 by gwenc when a verb needs the bytes")
        edits.append(Edit(fid, comp, plain_path, stored_path, ack, plain))

    return Manifest(path, name, active, retail, ridx, edits,
                    hashlib.sha256(raw).hexdigest(), accept_unread=unread)


# ---------------------------------------------------------------------------
# Identity and fingerprints
# ---------------------------------------------------------------------------

def mft_sha256(ar):
    ar.fh.seek(ar.mft_offset)
    blob = ar.fh.read(ar.mft_size)
    if len(blob) != ar.mft_size:
        raise SystemExit(
            f"REFUSED: {ar.path} declares {ar.mft_size} B of MFT at "
            f"0x{ar.mft_offset:X} and only {len(blob)} could be read.\n"
            f"  An identity taken over a short read compares equal to nothing "
            f"and unequal to everything.\n"
            f"  python toolkit/mapdata/datcheck.py --dat {ar.path} --preflight")
    return hashlib.sha256(blob).hexdigest()


def archive_identity(ar):
    """What this archive IS, in `datledger.identity`'s shape."""
    return {"archive": os.path.abspath(ar.path),
            "size_on_disk": os.path.getsize(ar.path),
            "mft_offset": ar.mft_offset,
            "mft_size": ar.mft_size,
            "row_count": ar.row_count,
            "mft_sha256": mft_sha256(ar)}


def id_records(ar):
    """Every (file_id, row) pair in MFT row 2, in table order.

    Deliberately NOT `file_id_table`: that helper takes the first record per id
    (`setdefault`), so two records naming one id would silently resolve to one
    of them. This module refuses that state and therefore has to be able to see
    it -- `bit31.census` walks the table with its own loop for the same reason.
    """
    blob = ar.read(ar.row(FILE_ID_TABLE_ROW))
    return [struct.unpack_from("<II", blob, i * 8)
            for i in range(len(blob) // 8)]


def rows_named_by(records, file_id):
    """Every DISTINCT row a file id names, sorted. Exact 32-bit compare.

    No masking: `archive.file_id_table(raw=True)`'s rule, because this answers
    what the CLIENT can address and the client's lookup is an exact compare
    with no retry (0x0047AA20).
    """
    return sorted({row for fid, row in records if fid == file_id})


def fingerprint_block(path, rows):
    """{row: [size, crc32(stored bytes) hex, compression]} for `rows`.

    THE CRC IS RECOMPUTED FROM DISK, not read out of the entry's crc field, and
    that is the difference between a check and a tautology. A payload edited in
    place without its crc updated is a state `datcheck --preflight` cannot see
    -- it does not re-read payloads and has no notion of a compression code --
    and it is exactly what a half-finished write leaves behind. Comparing the
    MFT's own field with itself could not fail.
    """
    out = {}
    with Archive(path) as ar:
        for row in rows:
            e = ar.row(row)
            data = ar.raw(e)
            if len(data) != e.size:
                raise SystemExit(
                    f"REFUSED: row {row} of {path} declares {e.size} B at "
                    f"0x{e.offset:X} and only {len(data)} could be read.\n"
                    f"  A fingerprint over a short read would compare unequal "
                    f"to everything, including to itself.")
            out[str(row)] = [e.size, f"{binascii.crc32(data) & 0xFFFFFFFF:08x}",
                             e.compression]
    return out


def looks_like_retail(staged, retail):
    """True iff every touched row still carries retail's bytes.

    `a10stage.looks_like_retail`'s guard, and its sentence: a build that
    changed nothing looks exactly like a successful build, right up until the
    experiment produces a null nobody can explain.
    """
    return all(staged.get(k) == v for k, v in retail.items())


def _body(doc):
    return {k: v for k, v in doc.items() if k != "self_sha256"}


def _self_sha(doc):
    blob = json.dumps(_body(doc), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def write_fingerprints(path, doc):
    doc = dict(doc)
    doc["self_sha256"] = _self_sha(doc)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)
    return path


def _file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


#: The two records this module writes, and the verb that writes each. Both go
#: through `load_fingerprints`, because both are read as the truth about what
#: some archive was at some moment and both can be stale, doctored, or about a
#: different manifest.
RECORD_KINDS = {
    "build": (fingerprints_path, "build record", "--build {path}"),
    "prelaunch": (prelaunch_fingerprints_path, "pre-launch record",
                  "--deploy {path} --yes"),
}


def load_fingerprints(manifest, why="read", kind="build"):
    """A written record, refused unless it describes THIS manifest and baseline.

    Three separate things can be wrong with it and each has its own sentence:
    it can be a record of a DIFFERENT manifest (the manifest sha), a record
    taken against a DIFFERENT retail baseline (the stamp), or hand-edited (the
    self sha). The last one is an accident tripwire and is named as one -- a
    doctored file whose author also recomputed the digest passes, and there is
    no cryptography here to say otherwise.

    `kind` selects which of the two records is being read. They carry the same
    fields and mean different things: the BUILD record says what was staged,
    the PRE-LAUNCH record says what the ACTIVE archive was at the moment of a
    deploy. Only the second one is a before-image, and `--verify-after` reads
    only the second one -- see the module docstring.
    """
    where, what, remedy = RECORD_KINDS[kind]
    path = where(manifest)
    remedy = "python toolkit/mapdata/overlay.py " + remedy.format(
        path=manifest.path)
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise SystemExit(
            f"REFUSED: cannot {why} overlay {manifest.name!r}: its {what} "
            f"at {path} is not readable ({type(exc).__name__}: {exc}).\n"
            f"  Write it first:  {remedy}") from None
    got = doc.get("format") if isinstance(doc, dict) else type(doc).__name__
    if not isinstance(doc, dict) or got != FORMAT:
        raise SystemExit(f"REFUSED: {path} is not an overlay {what}: "
                         f"its format is {got!r}, not {FORMAT!r}")
    if doc.get("format_version") != FORMAT_VERSION:
        raise SystemExit(
            f"REFUSED: {path} is format_version "
            f"{doc.get('format_version')!r}; this tool writes "
            f"{FORMAT_VERSION}. Re-build rather than read across formats.")
    if doc.get("self_sha256") != _self_sha(doc):
        raise SystemExit(
            f"REFUSED: {path} does not match its own digest.\n"
            f"  Something edited this record after it was written, and the "
            f"rows in it are what --status, --deploy and --verify-after read "
            f"an archive's identity out of. A {what} that can be hand-"
            f"adjusted to say a deploy is what it is not is worse than none.\n"
            f"  Write it again:  {remedy}")
    if doc.get("manifest_sha256") != manifest.sha256:
        raise SystemExit(
            f"REFUSED: {path} was built from a DIFFERENT manifest\n"
            f"  record: {doc.get('manifest_sha256')}\n"
            f"  on disk: {manifest.sha256}\n"
            f"  The manifest has changed since this profile was staged, so the "
            f"rows it owns and the payloads it declares may both have moved.\n"
            f"  Write it again:  {remedy}")
    with Archive(manifest.retail) as ar:
        now = archive_identity(ar)
    have = doc.get("retail", {})
    for field in STAMP_FIELDS:
        if have.get(field) != now[field]:
            raise SystemExit(
                f"REFUSED: {path} was built against a different RETAIL "
                f"archive\n"
                f"  {field}: the record says {have.get(field)!r}, "
                f"{manifest.retail} says {now[field]!r}\n"
                f"  Every fingerprint in this record is relative to that "
                f"baseline, so 'retail on all touched rows' would be answered "
                f"about an archive nobody is holding.\n"
                f"  Write it again:  {remedy}")
    return doc


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


# ---------------------------------------------------------------------------
# The refindex gate
# ---------------------------------------------------------------------------

def resolve_index(manifest, ar, index=None, echo=True):
    """The reference index this plan is gated on: handed in, named, or built.

    `refindex.load(path, ar)` is ALWAYS called with the archive. An index
    loaded without one answers confidently for rows that have since moved, and
    "nobody else reads this row" is the single wrong answer the gate exists to
    prevent -- the same shape `vaultpath.require_dir` refuses from the other
    side.
    """
    if index is not None:
        refindex.check_stamp(index, ar, why="gate an overlay against")
        return index
    if manifest.refindex_path:
        if echo:
            print(f"  refindex <- {manifest.refindex_path}")
        return refindex.load(manifest.refindex_path, ar)
    if echo:
        # THE COST IS PRINTED BEFORE THE WAIT, not discovered during it.
        print(f"  the manifest names no refindex, so one is being BUILT from "
              f"{manifest.retail}.\n"
              f"  {INDEX_COST}. Build it once and name it:\n"
              f"    python toolkit/mapdata/refindex.py --dat {manifest.retail} "
              f"--build-json <vault path>\n"
              f"    refindex = \"<that path>\"      # in [overlay]")
    t0 = time.time()
    index = refindex.build(ar, progress=refindex.PROGRESS_EVERY if echo else 0)
    if echo:
        print(f"  refindex built in {time.time() - t0:.0f}s")
    return index


def _problem_lines(index, limit=6):
    out = []
    for rec in index.problems[:limit]:
        fid = rec.get("file_id")
        name = f"0x{fid:X}" if isinstance(fid, int) else "(no file id)"
        out.append(f"    row {rec.get('row')} {name}: {rec.get('why')}")
    if len(index.problems) > limit:
        out.append(f"    ... and {len(index.problems) - limit} more "
                   f"(index.problems carries all of them)")
    return out


def index_faults(index, manifest):
    """Refuse an index that could not SEE what this gate is about to trust.

    THE STAMP IS NOT THIS CHECK. `refindex.check_stamp` answers "is this index
    about this archive?"; these two fields answer "did it read the archive?",
    and an index can pass the first while failing the second. A head whose
    container would not decode is WALKED and not INDEXED -- `index.walked` and
    `len(index.heads)` differ for exactly that reason -- so its FA8 list is not
    in the graph, and a row that list names comes back with no referrers. That
    is the confident empty answer, arrived at with every other guard green.

    MEASURED, on this module's own fixture: two heads carrying real FA8 lists
    naming an edited row, with their container magic damaged to `ffnX`. The
    archive is healthy (`preflight` clean, `crc_sweep` clean), the index builds,
    `problems` names both rows, and `who_reads` on the edited row answers `[]`.
    Before this function the plan cleared the gate and the build ran.

    `partial` is refused outright and `problems` is refused unless the manifest
    declares the count. The asymmetry is the same one the skeleton tier rests
    on: a partial index has no honest reading, while an unreadable container is
    a real and bounded thing an operator can go and look at.
    """
    if index.partial:
        raise SystemExit(
            f"REFUSED: the reference index gating overlay {manifest.name!r} is "
            f"PARTIAL.\n"
            f"  It walked {index.walked} named head row(s), not the archive, so "
            f"every count off it is a floor of a floor: any head it did not "
            f"walk could be reading the row this manifest edits, and the index "
            f"has no way to say so.\n"
            f"  There is no acknowledgement for this one -- a subset was a spot "
            f"check and a gate is not.\n"
            f"  Build a whole one, once:\n"
            f"    python toolkit/mapdata/refindex.py --dat {manifest.retail} "
            f"--build-json <vault path>\n"
            f"    refindex = \"<that path>\"      # in [overlay]")
    n = len(index.problems)
    declared = manifest.accept_unread
    if n and declared is None:
        raise SystemExit(
            "\n".join([
                f"REFUSED: the reference index gating overlay "
                f"{manifest.name!r} could not read {n} container(s) or "
                f"list(s), and this manifest does not say so.",
                *_problem_lines(index),
                f"  Every one of those is a reference list this index did NOT "
                f"read. A head among them can name the row this manifest edits "
                f"and the answer still comes back empty -- an index that could "
                f"not see it is not an index that saw nothing, and this gate's "
                f"whole job is to tell those two apart.",
                f"  Look at them, then declare the number you looked at, in "
                f"[overlay]:",
                f"    accept_unread = {n}",
                f"  A count and not a flag: a new unreadable head moves the "
                f"number and this refusal comes back, where a `true` would go "
                f"on covering a blind spot as it grew.",
                f"  python toolkit/mapdata/refindex.py --dat {manifest.retail} "
                f"--build-json <vault path>   prints them under BLIND SPOT."]))
    if declared is not None and declared != n:
        raise SystemExit(
            "\n".join([
                f"REFUSED: overlay {manifest.name!r} declares accept_unread = "
                f"{declared} and this index could not read {n}.",
                *_problem_lines(index),
                f"  The number moved, which means the set of things this gate "
                f"cannot see is not the set that was looked at. Look again, "
                f"then write the new number:",
                f"    accept_unread = {n}      # in [overlay]"]))
    return n


def index_row_fault(index, edit, row):
    """Does the index agree with the ARCHIVE about which row this id names?

    -> a reason string, or None.

    `refindex.who_reads` resolves its argument to a row through the index's own
    spelling map and answers about THAT row. This caller has already resolved
    the same id against RETAIL's raw table, so the two resolutions can be
    compared -- and they are the one pair of facts that can catch a file-id
    table edited in place without its row's crc being updated, which is a state
    the MFT stamp cannot see (`refindex`'s own "THE STAMP AND WHAT IT DOES NOT
    CATCH"). An index answering about a different row than the one being
    written would answer "nobody" perfectly confidently.
    """
    seen = index.row_of(edit.file_id)
    if seen is not None and seen != row:
        return (f"the index resolves {edit.label} to row {seen}; the archive's "
                f"own file-id table resolves it to row {row}. Every answer "
                f"about this edit would be an answer about the wrong row.")
    if seen is None and (row in index.heads or row in index.targets):
        return (f"the index holds row {row}, but under none of {edit.label}'s "
                f"spellings, so a query with this id resolves to no row at all "
                f"and answers empty for a reason that is not 'nobody reads it'.")
    return None


def gate_edit(index, edit, row=None):
    """Who else consumes this file id, and is every one of them acknowledged?

    -> (unacknowledged, notes, answers). `unacknowledged` is the list of
    `(canonical_id, why)` pairs a refusal must name; empty means this edit
    clears the gate.

    `row` is the row the ARCHIVE resolved this id to. When it is given and the
    index holds no record of that row at all, the empty answer is annotated
    with what it is empty OF -- "no indexed reference list named row N", which
    is a fact, rather than a bare list a reader can take for a census.

    BOTH SIDES ARE NORMALISED THROUGH `canonical_id`, always. A row carries
    several file ids and an operator who wrote one spelling while the index
    reports another has made a COMPLETE declaration -- refusing it would send
    them off to add an id that is already there, and a gate that refuses
    correct declarations is a gate that gets a `--force` bolted on.

    THE TIER: co-readers always count; co-wearers count unless the shared key
    is contentless. See the module docstring -- 572 heads in one all-zero group
    on retail, and an acknowledgement of 571 unrelated models is a rubber
    stamp.
    """
    own = canonical_id(index, edit.file_id)
    ack = {canonical_id(index, a) for a in edit.acknowledge}

    reads = refindex.who_reads(index, edit.file_id)
    shares = refindex.who_shares_skeleton(index, edit.file_id)

    kinds = {}
    for referrer, kind in reads:
        kinds.setdefault(canonical_id(index, referrer), set()).add(kind)
    co_readers = sorted(k for k in kinds if k != own)
    co_wearers = sorted({canonical_id(index, f) for f in shares} - {own})

    contentless = shares.facts.get("contentless") is True

    notes, unack = [], []
    for fid in co_readers:
        if fid not in ack:
            unack.append((fid, "reads it via "
                               + "/".join(sorted(kinds[fid]))))
    if contentless and co_wearers:
        # A NOTE, NOT A REFUSAL. The group is real and the criterion did not
        # move; what the answer says is that the key carries no pose, so these
        # heads group because none of them has one.
        notes.append(str(shares))
        notes.append(
            f"  the {len(co_wearers)} co-wearer(s) above are NOT required in "
            f"acknowledge_shared_with: the shared key is contentless "
            f"(node_count {shares.facts.get('node_count')}), so it groups "
            f"heads that carry no pose rather than heads that share one.")
    else:
        for fid in co_wearers:
            if fid not in ack:
                unack.append((fid, "wears the same blk2C base array "
                                   f"({shares.facts.get('node_count')} node(s))"))

    blind = [p for p in index.problems if p.get("row") == row]
    if row is not None and blind:
        # THE SHARPEST CASE OF THE SAME THING. `accept_unread` counts this row;
        # this names it. An unreadable head carries no skeleton hash, so it
        # joins no sharing group, so the co-wearer answer below is empty for a
        # reason that is not "nobody else wears it" -- which is what
        # `refindex.who_shares_skeleton` says from its own side.
        notes.append(
            f"  row {row} is ITSELF one of the {len(index.problems)} thing(s) "
            f"this index could not read ({blind[0].get('why')}). It carries no "
            f"skeleton hash here and joins no sharing group, so an empty "
            f"co-wearer answer for it means 'not indexed', never 'nobody else "
            f"wears it'")
    if row is not None and reads.facts.get("resolved") is not True:
        # THE EMPTY ANSWER, NAMED. `refindex` cannot tell "an id this archive
        # does not hold" from "a row nothing here references" -- it says so --
        # but this caller resolved the id against the archive first, so it can,
        # and an unqualified empty list is the shape that reads as a census.
        notes.append(
            f"  this index holds no record of row {row}: it is not among the "
            f"heads it indexed and no reference list it read names it. The "
            f"empty answer above is therefore 'no list this index read names "
            f"row {row}', not 'this id is unknown' -- and what it could not "
            f"read is accounted for separately, by accept_unread")

    stale = sorted(a for a in ack
                   if a not in set(co_readers) | set(co_wearers))
    if stale:
        notes.append(
            "  acknowledged but not a co-consumer this index can see: "
            + ", ".join(f"0x{a:X}" for a in stale)
            + " -- harmless, and worth checking the id was not mistyped")
    return unack, notes, (reads, shares)


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
