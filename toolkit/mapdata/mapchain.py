"""What a file id binds in this archive, and whether WE made it.

TWO QUESTIONS, ONE JOIN. `sibling_of`, `map_chain` and `resolve_rows` answer the
first -- what does this id resolve to, and is the thing it resolves to a
two-row map chain. `alloc_journal_path`, `archive_carries`, `allocation_recorded`
and `created_evidence` answer the second -- is the chain in front of us one
`datalloc` wrote for us, established from BYTES rather than from a filename.
`create_note` says which of the two states a run is in, on every run, install or
not. They are one module because `deploy.resolve_or_create` -- which STAYS in
`deploy.py`, being the decision the command line acts on -- joins them in four
consecutive lines, and splitting the question from its answer is what puts two
modules' worth of import aliases between a caller and the thing it asks.

POINTERS OUT, because several comments below name things that did not move:

  * `MAP_HEAD_FLAGS_U16` / `MAP_PARTNER_FLAGS_U16` are imported here from
    `mapchunks`, which owns them. `deploy.py` keeps its own two alias lines --
    same values, read by `create_streams` and `create_chain`, which stay there.
  * `create_chain`, `create_streams`, `resolve_or_create` and `main` all stay in
    `deploy.py`; where a docstring here says "the caller" or names one of them,
    that is the file to look in.
  * `Refused` is `deploy`'s own, from `deployrefuse.py`, for the reason that
    module's docstring gives: `test_deploy.py` §10(e2) asserts TYPE identity.

Nothing here writes. `create_chain` does the writing, with what these return.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import ENTRY_SIZE, file_id_table, FILE_ID_HIGH_BIT  # noqa: E402
import datwrite  # noqa: E402  -- read_journal, for the allocation journal
import mapchunks  # noqa: E402
from mapchunks import (MAP_HEAD_FLAGS_U16,  # noqa: E402
                       MAP_PARTNER_FLAGS_U16)
from deployrefuse import Refused  # noqa: E402


def sibling_of(file_id):
    """The bit-31 spelling of a plain file id: FcArchive's rename marker."""
    return file_id | FILE_ID_HIGH_BIT


def map_chain(ar, file_id):
    """The (head, partner) entries `file_id` names, or None if nothing names it.

    THE QUESTION IS ASKED OF THE RAW TABLE, and that is not a detail. The
    default `file_id_table` registers a bit-31 id under BOTH spellings as a
    convenience of ours; the client does no such thing and compares 32 bits
    exactly. Here the answer decides CREATE versus INSTALL -- that is, whether
    deploy writes into a row that a pending replacement already names, or
    allocates a fresh one -- so it has to be the client's answer.
    `archive.py`'s own docstring lists three failures from getting this
    backwards; this would have been the fourth.

    A BIT-31 SIBLING IS A REFUSAL EITHER WAY, and this is the known gap in the
    allocator rather than a new rule: `plan_alloc` tests `file_id in raw` and so
    ACCEPTS a plain id whose renamed spelling is already in the table, while
    `next_free_file_id` would never suggest it (studies/archivewrite/FINDINGS.md
    17.5, still open 2026-08-20). Allocating there produces two live
    registrations -- a rename pending and a fresh plain claim -- that no crc
    rule and none of `datcheck`'s ten open-time rules counts. `datalloc` is not
    modified to fix that; the caller refuses to walk into it.

    REFUSES rather than returning None when the id names something that is not a
    two-row map chain. "Nothing binds this id" and "this id binds somebody
    else's file" are different states with different remedies, and only the
    first one may create. The shape is checked positively -- head flags 259, a
    non-zero `nextStream`, a partner carrying flags 1 -- because
    `MapIndex.partner` reads `by_row.get(nextStream)` and `nextStream == 0`
    TERMINATES a chain while row 0 is a real MFT row, so a head with no partner
    resolves to the file header rather than to None.
    """
    raw = file_id_table(ar, raw=True)
    twin = sibling_of(file_id)
    if twin in raw:
        raise Refused(
            f"file id {file_id:#x} has a bit-31 sibling {twin:#x} bound to row "
            f"{raw[twin]} in this archive, and this command will not touch "
            f"either spelling.\n"
            f"  Bit 31 is not a spelling variant: FcArchive binds "
            f"`id | 0x80000000` and deletes the plain name when it has REQUESTED "
            f"A REPLACEMENT, so the sibling is the archive announcing that this "
            f"row is stale and a new file is on its way (content/maps.toml "
            f"[map.148] is the whole story).\n"
            f"  `plan_alloc` would accept the plain id here -- it tests exact "
            f"membership -- and leave two live registrations that nothing we own "
            f"counts (studies/archivewrite/FINDINGS.md 17.5). Choose another id "
            f"with `datalloc.py --next-id`, which skips both spellings.")
    row = raw.get(file_id)
    if row is None:
        return None
    by_row = {e.index: e for e in ar.entries}
    head = by_row.get(row)
    if head is None:
        raise Refused(f"file id {file_id:#x} names row {row}, which is absent")
    if not mapchunks.is_map_head(head):
        raise Refused(
            f"file id {file_id:#x} already binds row {row} in this archive, and "
            f"that row is NOT a Bloated map head: alloc.flags "
            f"0x{mapchunks.alloc_flags(head):02X}, stream "
            f"{mapchunks.alloc_stream(head)}, {head.size} B, compression "
            f"{head.compression}.\n"
            f"  A map head is flags 3 (USED|FIRST_STREAM) on stream 1, the u16 "
            f"259. What sits here is somebody else's file, and the remedy is a "
            f"different id rather than a different flag -- overwriting it would "
            f"make one of two files unreachable, which no rule in datcheck "
            f"counts.")
    nxt = mapchunks.next_stream(head)
    if not nxt:
        raise Refused(
            f"file id {file_id:#x} binds row {row}, a map head whose nextStream "
            f"is 0 -- the chain terminates there, so this file has no Stripped "
            f"partner to install into.\n"
            f"  A map is TWO rows and this is one. Nothing here can repair it: "
            f"`datalloc` creates whole chains and `datwrite` writes rows that "
            f"exist.")
    partner = by_row.get(nxt)
    if partner is None:
        raise Refused(
            f"file id {file_id:#x} binds row {row}, whose nextStream names row "
            f"{nxt}, which is absent from this archive's MFT")
    if partner.flags != MAP_PARTNER_FLAGS_U16:
        raise Refused(
            f"file id {file_id:#x} binds row {row}, chained to row {nxt} with "
            f"flags 0x{partner.flags:04X} rather than the Stripped partner's "
            f"0x{MAP_PARTNER_FLAGS_U16:04X} (stream 0, USED).\n"
            f"  MEASURED corpus-wide, the nextStream link map is a bijection "
            f"and every Bloated head chains to exactly one stream-0 row. This "
            f"chain is a shape we have never seen the client produce, so it is "
            f"named rather than installed into.")
    return head, partner


def alloc_journal_path(here, tag):
    """Where `create_chain` writes an area's allocation journal. ONE expression.

    Named rather than spelled out at each of its three call sites, because the
    three now disagree about what they want from it and would drift: the create
    path REFUSES to write over one (R3), the install path READS one as evidence
    that a chain is ours (R2), and both have to be talking about the same file
    for either to mean anything.
    """
    return os.path.join(here, f"{tag}_alloc.json")


def archive_carries(dat, offset, blob):
    """Is `blob` sitting at `offset` in `dat` RIGHT NOW? -> bool

    Eight bytes and a seek, and it is the whole of what makes an allocation
    journal evidence about the copy in front of us rather than about a filename
    (`allocation_recorded`). Any read failure is a False rather than a raise:
    the caller is deciding whether something is evidence, and an archive it
    cannot read has not shown it anything.

    AN EMPTY `blob` IS A FALSE, not a vacuous True. Every file carries zero
    bytes at every offset, so the one-line version of this would hand a caller a
    check that cannot fail -- which is the failure this pass exists to close,
    one function smaller.
    """
    if not blob:
        return False
    try:
        with open(dat, "rb") as fh:
            fh.seek(offset)
            return fh.read(len(blob)) == blob
    except OSError:
        return False


def allocation_recorded(journal, dat, file_id, head_row, partner_row):
    """Does `journal` record US allocating THIS chain in THIS archive? -> bool

    READ STRUCTURALLY, NOT AS PROSE, and that is deliberate after the grow
    gate's four-sentence join (see `grow_gate_refusal`). `datalloc.alloc` writes
    the journal's `what` strings for a human; what is checked here is BYTES:

      * one edit's `after` is exactly `<II` (file_id, head_row) -- the file-id
        record going live, which is step 4 of the allocation and the moment the
        chain acquires its name;
      * the edit at `mft_offset + head_row * 24` writes a 24-byte row whose
        flags are the map head's and whose `nextStream` is `partner_row`;
      * the edit at `mft_offset + partner_row * 24` writes the partner's flags;
      * and the archive in front of us is the archive that file-id record went
        into.

    All four together say "this file recorded binding this id to this head,
    chained to this partner, in this archive". `mft_offset` is read from the
    JOURNAL rather than from the archive on purpose: the client relocates the
    master file table during ordinary play (`datwrite.Journal` records it for
    exactly that reason), so an offset compared against today's table would
    stop matching for a reason that says nothing about who made the rows.

    THE LAST CONJUNCT IS NOT A PATH COMPARE ANY MORE, and the fix is the same
    lesson as the one above it. `datalloc` records an ABSOLUTE path, and
    archives in this project are COPIED WHOLE as a matter of routine --
    `overlay.py` copies manifest archives with `shutil.copyfile`,
    `make_run_dir.py` stages one per run directory, and RUNBOOK's own procedure
    copies `run-live/<build>/Gw.dat` over `run/<build>/Gw.dat`. A copy that
    carries its journal beside it is OUR chain, described byte-exactly, and the
    path compare refused it -- with a closing remedy ("allocate under a fresh
    id") that is actively wrong advice in exactly that state. So the archive is
    asked DIRECTLY instead: does it carry, at the offset the journal recorded,
    the file-id record the journal says it wrote there? That survives a copy, a
    rename, an `--out` that moved the build products, and a later relocation of
    the partner. The path compare is KEPT as the FIRST route, cheap and not
    weaker than it was, for the archive that stayed where it was while the
    client rewrote the id table underneath it.

    THE ROWS ARE THE CALLER'S CURRENT ONES, and that is what keeps this from
    degenerating into "a journal exists": `resolve_or_create` reads
    `head_row`/`partner_row` out of the archive in front of it, so a journal
    describing some other allocation fails the `<II` conjunct before the archive
    is opened at all.

    A journal that will not parse is not evidence and is not an error here --
    `datwrite.read_journal` refuses an empty or malformed one by name, and the
    caller's job is to say what IS there rather than to re-raise.
    """
    try:
        doc, _dropped = datwrite.read_journal(journal)
    except (SystemExit, OSError, ValueError):
        return False
    if not isinstance(doc, dict):
        return False
    mft = doc.get("mft_offset")
    if not isinstance(mft, int):
        return False
    named = struct.pack("<II", file_id, head_row)
    rows_seen = {}
    id_offsets = []
    for ed in doc.get("edits", []):
        try:
            after = bytes.fromhex(ed.get("after", ""))
            off = int(ed["offset"])
        except (KeyError, TypeError, ValueError):
            continue
        if after == named:
            id_offsets.append(off)
        if len(after) != ENTRY_SIZE:
            continue
        for row in (head_row, partner_row):
            if off == mft + row * ENTRY_SIZE:
                rows_seen[row] = struct.unpack("<QIHHII", after)
    head = rows_seen.get(head_row)
    partner = rows_seen.get(partner_row)
    if not (id_offsets
            and head is not None and partner is not None
            and head[3] == MAP_HEAD_FLAGS_U16 and head[4] == partner_row
            and partner[3] == MAP_PARTNER_FLAGS_U16):
        return False
    # The binding, either way round: the name it was written under, or the
    # bytes it was written as. The second is the one that survives a copy.
    named_path = os.path.normcase(os.path.abspath(str(doc.get("dat", ""))))
    if named_path == os.path.normcase(os.path.abspath(dat)):
        return True
    return any(archive_carries(dat, off, named) for off in id_offsets)


def created_evidence(dat, here, tag, file_id, head_row, partner_row):
    """The journal proving we made this chain, or None. -> path|None

    Looks BESIDE THE ARCHIVE as well as in `here`, because those are the same
    directory on every default invocation and differ only when `--out` moves the
    build products somewhere else. Widening the search does not weaken the
    check: whichever file is found still has to describe this id and these two
    rows AND be bound to this archive by one of `allocation_recorded`'s two
    routes, so a journal from another area is not evidence about this one.

    A COPY OF THE ARCHIVE IS FOUND BY WHICHEVER JOURNAL TRAVELLED WITH IT. That
    is the case this pair exists to serve and the case the path compare used to
    refuse: copy `Gw.dat` and `<area>_alloc.json` into a fresh run directory --
    which is what `make_run_dir.py` and RUNBOOK's `Copy-Item` step do -- and the
    chain is still ours, because the copy carries the file-id record the journal
    recorded. What does NOT travel is nothing: a journal left behind is a
    refusal, and its remedy is to bring it along rather than to allocate again.
    """
    if not here or not tag:
        return None
    seen, out = set(), []
    for d in (here, os.path.dirname(os.path.abspath(dat))):
        if not d:
            continue
        p = os.path.abspath(alloc_journal_path(d, tag))
        if os.path.normcase(p) not in seen:
            seen.add(os.path.normcase(p))
            out.append(p)
    for p in out:
        if os.path.isfile(p) and allocation_recorded(p, dat, file_id, head_row,
                                                     partner_row):
            return p
    return None


def create_note(file_id, size, bound, created, install):
    """What this run says about the ROW the stream is going into. -> str|None

    ASKED ON EVERY RUN, INSTALL OR NOT, and that is the whole reason it is a
    function rather than a line under `if create:`. The decision to allocate is
    computed only under `--install`, correctly -- deciding costs a refusal and a
    build-only run must not refuse -- so a build-only run printed the two sizes
    and stopped, and a dry run against an id NOTHING binds was indistinguishable
    from a dry run against an id everything binds.

    THAT IS NOT COSMETIC, and it was found the way these things are found: by
    running the command. WORLDMAPS-W4's step 1 is a build-only run whose output
    the operator compares against a prediction registered beforehand, and the
    prediction that matters at that step is that the create branch WILL fire --
    that the area -> map row -> file id join lands on a row carrying
    `created = true` whose id binds nothing in this archive. A run that cannot
    say so leaves a correct dry run reading as a refutation of the join, which is
    the same defect as a check that cannot fail, from the other side.

    `bound` IS THE RAW TABLE'S ANSWER, or None: the row the CLIENT's own lookup
    would find (`map_chain`'s docstring has the three failures that come from
    asking the convenience form instead). It is asked here without the shape
    checks that can refuse, because a preview that refuses is not a preview --
    the shape is `map_chain`'s question and it is asked on the install path,
    where a refusal is the correct outcome.

    Returns None when the id binds something: `verify` has already said what that
    row's reservation does with these bytes, and two lines about one row is how
    they drift apart.
    """
    if bound is not None:
        return None
    if created and install:
        return (f"no reservation to judge: file id {file_id:#x} binds nothing "
                f"in this archive, so the {size} B stream will be given a row "
                f"of its own rather than fitted into one")
    if created:
        return (f"no reservation to judge: file id {file_id:#x} binds nothing "
                f"in this archive, so --install would CREATE the chain rather "
                f"than fit the {size} B stream into a row")
    return (f"file id {file_id:#x} binds nothing in this archive and this "
            f"area's map row does not carry `created = true`, so --install "
            f"would REFUSE here rather than allocate -- an id that resolves "
            f"nowhere is also what a WRONG id looks like")


def resolve_rows(archive, file_id):
    """(head row, partner row, partner reservation). By FILE ID, never remembered."""
    row = file_id_table(archive).get(file_id)
    if row is None:
        raise Refused(f"file id {file_id:#x} does not resolve in this archive")
    head = next((e for e in archive.entries if e.index == row), None)
    if head is None:
        raise Refused(f"file id {file_id:#x} names row {row}, which is absent")
    mi = mapchunks.MapIndex(archive)
    partner = mi.partner(head)
    reservation = ((partner.size + 511) // 512) * 512
    return head.index, partner.index, reservation
