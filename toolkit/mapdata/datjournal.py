"""The journal format -- an append-only record of what this writer did, and how
a pre-2026-08-19 run's record is read back.

`datwrite.py` still owns the WRITING; this owns the FORMAT. `Journal` is what a
`Writer` opens before it touches the archive, and `read_journal()` is what reads
one back, intact or torn. The REPLAYER is `datwrite.revert()`, which stays over
there because it also calls `guard()` and `mft_offset_of()`: it walks
`doc["edits"]` newest first and writes each record's `before` back at its
`offset`, so the four keys `offset` / `before` / `after` / `what` that
`Journal.record` writes are this module's contract with it.

POINTER, because the text below moved verbatim and three of its forward
references now name code in another file: `revert()`, `put()` and
`mft_offset_of` are all `datwrite.py`'s. `datwrite.py` re-exports `Journal`,
`JOURNAL_CLOSER` and `read_journal` under their own names, so `datwrite.Journal`
and `datwrite.read_journal` are these same objects.
"""

import binascii
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


JOURNAL_CLOSER = b"]}\n"


class Journal:
    """Every byte this run changes, with what was there before it.

    Written to disk BEFORE the archive is touched and FSYNCED after each write,
    so an interrupted run still leaves a usable way back.

    It records the MFT's offset too, and that is not bookkeeping. Edits are
    stored as ABSOLUTE file offsets, and MEASURED 2026-08-06 the client
    relocates the master file table during ordinary play -- observed moving from
    0xF8FFF000 to 0xF940E200 and back again within one session, which looks like
    a double-buffer it alternates for crash safety. An MFT-field edit journalled
    at one location is meaningless at the other, so replaying it would write four
    bytes into whatever now occupies dead space and report success. Silent, and
    the archive would still verify, because the row it meant to fix was never
    touched. Hence the guard in revert().

    APPEND-ONLY, ONE RECORD PER LINE, FSYNCED PER RECORD. Until 2026-08-19 this
    class opened the file `"w"` and re-serialised the WHOLE document after every
    record, with no fsync at all. Three costs, all measured rather than argued:

      * **Write amplification.** A 5-record replace of a 1,029,632 B reservation
        wrote 20,595,001 B to produce a 4,119,275 B journal (5.0x). On the
        largest real artifact, `vault/research/archivewrite/a4run7-flip.journal`,
        60 edits wrote ~533,180,912 B to produce 15,624,042 B -- **34.1x, and
        137x the 3,903,668 B of archive the records actually protect.** It is
        quadratic in record count, so it gets worse exactly where it matters.
      * **A torn flush lost the WHOLE journal, not one record.** `"w"` truncates
        first, so a crash mid-write left invalid JSON and `revert()` died at
        `json.load` with an unhandled `JSONDecodeError` -- a traceback, not a
        diagnosis, on the one tool that exists for the one moment it is needed.
        That is the same class of failure `mft_offset_of` was written for.
      * **No fsync.** `put()` fsyncs the ARCHIVE; the journal that must precede
        it did not, so the stated ordering guarantee above was not enforced
        against the OS cache. On a power loss the archive edit could be durable
        while the record describing it was not.

    THE FORMAT DID NOT MOVE, and that is deliberate: 59 old-format journals sit
    under `vault/` and `test_datalloc.py`'s prefix replay reads one with a plain
    `json.load(fh)["edits"]`. So the file is still a single JSON object with
    `dat`, `mft_offset` and `edits`, and it is a VALID JSON DOCUMENT at every
    fsync boundary -- what changed is how the bytes get there. The header line is
    written once, each record is APPENDED as its own line, and the three-byte
    closer `]}\\n` is rewritten in place behind it. Cumulative bytes are
    final-size + 3 per record instead of N x final-size: MEASURED 4.66x -> 1.00x
    on a 5-record replace of the test fixture.

    One record per LINE is the other half, and it is what makes a torn write cost
    one record instead of all of them: `read_journal()` falls back to parsing
    line by line when the closer is missing, drops the incomplete tail with a
    printed byte count, and replays everything before it.

    Opened LAZILY, on the first record. A refusal that writes nothing must leave
    no journal behind -- `test_datwrite.py` section 5 asserts exactly that -- and
    an empty file on disk is a worse lie than no file.

    FUTURE WORK, deliberately not done here: chunking a large payload `put()`
    into <=1 MB records would bound peak memory and bound torn-write loss (the
    records replay newest-first over disjoint ranges, so revert is unaffected).
    It touches neither the amplification nor the fsync, so it is not part of this
    change. Nor is a binary sidecar for `before`/`after`, which would remove the
    measured 4.00x hex cost and change the format for 59 files and two readers.
    """

    def __init__(self, path, dat, mft_offset):
        self.path = path
        self.dat = dat
        self.mft_offset = mft_offset
        self.entries = []
        self.fh = None
        self._tail = 0          # where JOURNAL_CLOSER currently begins

    def _open(self):
        """The ONE truncating open. Everything after it seeks and appends."""
        head = ('{"dat": %s, "mft_offset": %d, "edits": [\n'
                % (json.dumps(self.dat), self.mft_offset)).encode("utf-8")
        self.fh = open(self.path, "w+b")
        self.fh.write(head + JOURNAL_CLOSER)
        self._tail = len(head)
        self.flush()

    def record(self, offset, before, after, what):
        rec = {
            "offset": offset,
            "length": len(before),
            "before": binascii.hexlify(bytes(before)).decode(),
            "after": binascii.hexlify(bytes(after)).decode(),
            "what": what,
        }
        if self.fh is None:
            self._open()
        # A leading comma on every record but the first, and a newline after
        # each, so the document stays valid JSON AND every record is one line.
        chunk = ((b"," if self.entries else b"")
                 + json.dumps(rec).encode("utf-8") + b"\n")
        self.fh.seek(self._tail)
        self.fh.write(chunk + JOURNAL_CLOSER)
        self._tail += len(chunk)
        self.entries.append(rec)
        self.flush()

    def flush(self):
        """To the platter, not to the page cache. The ordering claim needs it."""
        if self.fh is None:
            return
        self.fh.flush()
        os.fsync(self.fh.fileno())

    def close(self):
        if self.fh is not None:
            self.flush()
            self.fh.close()
            self.fh = None


def read_journal(path):
    """Parse a journal, INTACT or TORN. -> (doc, bytes dropped from the tail).

    TWO FORMATS, and the second is a superset of the first. A journal written
    before 2026-08-19 is one pretty-printed JSON object; one written after is the
    same object with the records laid out one per line and appended in place.
    Both are valid JSON, so the intact path is one `json.loads` and 59 old
    journals under `vault/` -- plus `test_datalloc.py`'s prefix replay, which
    reads a journal with a plain `json.load(fh)["edits"]` -- keep working
    unchanged. That compatibility is not optional: those files are the A8 and
    run-7 evidence and nothing regenerates them.

    THE RECOVERY PATH is what the format change bought. `Journal` never rewrites
    a record once written, so a torn write can only damage the LAST line and the
    three-byte closer behind it. When the document does not parse, this reads the
    header line, then every record line, and stops at the first that does not --
    reporting how many bytes it dropped rather than swallowing them, because a
    silent partial revert is the same defect as a silent partial write. Before
    the change the whole journal was lost to an unhandled `JSONDecodeError` out
    of `revert()`: a traceback, not a diagnosis, on the one tool that exists for
    the one moment it is needed. Same class as `mft_offset_of`.

    A file whose header line does not parse is REFUSED BY NAME, not by
    traceback. An old-format journal torn mid-document is in that class -- its
    records span many lines and none of them stands alone -- which is a property
    of the format it was written in and not something this can recover.
    """
    with open(path, "rb") as fh:
        raw = fh.read()
    if not raw.strip():
        raise SystemExit(
            f"REFUSED: {path} is empty ({len(raw)} bytes). There is nothing to "
            f"replay, and an empty journal is not the same statement as a "
            f"journal with no edits -- a Writer opens the file lazily, on its "
            f"first record, so a zero-byte one means the write never got that "
            f"far or the file was truncated to nothing.")
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        doc = None
    if isinstance(doc, dict) and "edits" in doc:
        return doc, 0
    if doc is not None:
        raise SystemExit(
            f"REFUSED: {path} parses as JSON but is not a journal -- it has no "
            f"`edits` key. Refusing to guess what it is.")

    pieces = raw.split(b"\n")
    head, edits, dropped, pos = None, [], 0, 0
    for i, line in enumerate(pieces):
        start = pos
        pos += len(line) + (1 if i < len(pieces) - 1 else 0)
        s = line.strip()
        if i == 0:
            # The header line ends with an open `[`; close it to parse it alone.
            try:
                head = json.loads((s + b"]}").decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                head = None
            if not isinstance(head, dict) or "edits" not in head:
                raise SystemExit(
                    f"REFUSED: {path} is neither an intact JSON document nor a "
                    f"recoverable append-only journal -- its first line does "
                    f"not parse as a journal header.\n"
                    f"  Nothing has been written and no archive was opened. If "
                    f"this is an old-format journal that was torn mid-write, "
                    f"its records span several lines each and none of them "
                    f"stands alone; there is nothing here to replay.")
            continue
        if not s or s == JOURNAL_CLOSER.strip():
            continue
        if s.startswith(b","):
            s = s[1:]
        try:
            rec = json.loads(s.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            rec = None
        if not isinstance(rec, dict) or "offset" not in rec:
            dropped = len(raw) - start
            break
        edits.append(rec)
    head["edits"] = edits
    return head, dropped
