r"""What declares an overlay, where it lives on disk, and the records that identify it.

The manifest half and the record half of `overlay.py`, lifted VERBATIM so that
file is about plans, the fit arithmetic and the six verbs, and this one is about
the declaration and the documents:

    FORMAT/FORMAT_VERSION  what a fingerprints record says it is
    NAME_RE, EXPORT_PARTS  the one legal profile name shape, and the vault root
    MANIFEST_KEYS          the closed key sets a manifest is refused against
    EDIT_KEYS
    STAMP_FIELDS           the retail-stamp fields a record is matched on
    _inside, guard_archive where the bytes may and may never go
    export_root ..         the six path builders, all under the vault
      prelaunch_fingerprints_path
    Edit, Manifest         one declared row, and the profile that declares them
    load_manifest          the TOML door, and its twenty refusals
    mft_sha256 ..          identity, fingerprints, and the two written records
      load_fingerprints

THESE TWO HALVES ARE ONE FILE AND NOT TWO. `RECORD_KINDS` is built from
`fingerprints_path` and `prelaunch_fingerprints_path`, so the record half cannot
exist without the path half; splitting them would have bought one more module
and one more import edge for nothing.

`RECORD_KINDS` STORES THE PATH FUNCTIONS, NOT THEIR RESULTS, and that is load
bearing rather than a style: `export_root` calls `vaultpath.require_dir()`, so
computing the paths at module level would move a vault requirement from run time
to IMPORT time, and every importer of this module -- `overlay.py` itself,
`datcheck.py`'s lazy import, `abrun.py` -- would need a vault to exist before it
could be read. Nothing in the tree guards that property; it is preserved by
construction and named here so it is not "simplified" away.

WHERE THE REASONING IS. Four sections of `overlay.py`'s module docstring argue
this code and they STAYED there, because they are also the verbs' refusal
reasoning and `main()`'s `--help`. Read them in
`toolkit/mapdata/overlay.py`, by title:

  * WHAT THIS WRITES, AND WHERE -- why everything except the ACTIVE archive
    lives under the vault, and why `C:\gw` and `vault/dat_study` are refused for
    BOTH the active and the retail path rather than only the written one. That
    is `guard_archive` and the six path builders below.
  * A FINGERPRINT IS COMPUTED FROM THE STORED BYTES -- `[size, crc32(stored
    bytes), compression]` per touched row, recomputed from disk rather than
    taken from the entry's crc field, because comparing the MFT's own field
    against itself is a check that cannot fail. That is `fingerprint_block`.
  * A POST-FLIGHT IS MEASURED AGAINST THE BEFORE-IMAGE THE DEPLOY TOOK -- the
    BUILD record describes what was staged and the PRE-LAUNCH record describes
    what ACTIVE was at the moment of a deploy, and only the second is a
    before-image. That is `load_fingerprints`.
  * THE V1 SCOPE IS EDIT-IN-PLACE -- why an `Edit` names a file id and a payload
    and never a new row.

TWO POINTERS BELOW MEAN `overlay.py`, and they travelled without a word changed,
because rewording a moved comment is how a comment stops being evidence:
`load_fingerprints`'s "see the module docstring" means `overlay.py`'s, the
POST-FLIGHT section named above; and `Edit`'s and `load_manifest`'s references
to `datcheck --preflight`'s ten rules are about `datcheck.py`, which this module
does not import and must not.

Nothing here imports `overlay`. `overlay.py` runs as `python
toolkit/mapdata/overlay.py`, so a leaf importing it back would load a second
copy under a second name, with a second `Manifest` class no `isinstance` in the
tree would accept. Every one of these names that `overlay.py` still reads
reaches it through a re-export at the site it was cut from.

standard library only, plus this package's own `archive`, `datwrite`, `gwenc`
and `vaultpath`.
"""

import binascii
import hashlib
import json
import os
import re
import struct
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import (Archive, FILE_ID_TABLE_ROW,           # noqa: E402
                     COMPRESSION_STORED, COMPRESSION_HUFFMAN)
import datwrite                                            # noqa: E402
import gwenc                                               # noqa: E402
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

#: Fields of the retail stamp a fingerprints record is matched on. `archive` is
#: recorded and deliberately not compared -- `datledger.STAMP_FIELDS` reasons it
#: out: censusing a byte-identical copy under another name is legitimate, and a
#: guard that refuses it is a guard people route around.
STAMP_FIELDS = ("size_on_disk", "mft_offset", "mft_size", "row_count",
                "mft_sha256")


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
