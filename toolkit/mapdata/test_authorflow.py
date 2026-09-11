"""AUTHOR A FILE THAT NEVER EXISTED INTO AN ARCHIVE, AT COMPRESSION 8, AND WALK
IT BACK AGAIN.

Every verb this needs has its own test and all of them are green. What none of
them measures is the SEQUENCE, and the sequence is the deliverable: an author
compresses a payload, allocates a row for it, rewrites that row twice as the
content changes, outgrows the reservation, relocates, and then puts the archive
back the way it was found. Each of those steps hands the next one an archive in a
state its own test never produced -- a row whose reservation is bigger than its
size, a row sitting in a run `datplan` handed out ten seconds ago, a journal
written over an archive a previous journal will be replayed against. A per-verb
suite cannot see a composition defect, and this arc's history is composition
defects: `replace()` could not grow a row it had shrunk itself (FINDINGS 14.4),
and `datmove` marked a relocated compression-8 row stored (FINDINGS C-6). Both
verbs were green in isolation on the day.

    python toolkit/mapdata/test_authorflow.py

THE STORY, one archive from top to bottom, in six steps:

  1. AUTHOR   four revisions of one file we invent, through `gwenc.encode`.
              Three carry both halves of an LZ77 stream; the fourth is RLE,
              which is the shape that declared a 1-symbol distance table until
              the envelope work landed (FINDINGS 13.5 gap A).
  2. CREATE   `datalloc.alloc(confirm=True)` with a partner declaring
              `extraBytes 8` AND the payload a reader must get back -- a file id
              that did not exist, a head, a partner, and the archive handing the
              payload back. The `expect=` is mandatory as of 2026-08-20 and is
              the same declaration steps 3-5 make with `--expect`.
  3. REVISE   `--replace --compression 8` with a SMALLER revision. The row's
              size falls and the reservation `replace` can see falls with it,
              which is the dead end step 4 exists to walk out of.
  4. GROW     `--replace --grow-to` with a bigger one, back into the blocks step
              3 freed. This is the step that was impossible before 2026-08-19,
              and it is the one an authoring loop hits on its second iteration.
  5. OUTGROW  a revision too big for the reservation. `--replace` refuses and
              names the remedy the geometry allows; `datmove.move(compression=8,
              expect=)` relocates the row into a free run.
  6. UNDO     the four journals, replayed newest first, and what they compose to.
              MEASURED rather than assumed -- see `section_undo`.

WHAT IS AND IS NOT NEW HERE. The gates themselves belong to the files that own
them and are not re-litigated: `test_datalloc.py` section 13 owns the comp-8
allocation gate, `test_datwrite.py` sections 9-11 own the C-6 declaration guard
and the grow gate's four conditions, `test_datmove.py` owns best-fit placement,
and `test_gwenc.py` section 8 owns the table envelope. What is new is that they
run ONE AFTER ANOTHER over one archive, and that every step is checked by DECODE
-- `Archive.read()` giving back the exact bytes the author wrote -- rather than
by a checksum. No checksum in this format can tell a compression-8 row holding
the wrong bytes from one holding the right ones: the entry crc covers the STORED
bytes, so it moves with the corruption. That is why the payload comparison is the
headline of every step and the crc rules are the footnote.

THE SABOTAGE, in step 2b. A flow test is the easiest place in the tree to write a
check that cannot fail: if every gate were stubbed out the six steps would still
print six greens, because the archive would still hold what the last write put
there. So the authored stream is corrupted between AUTHOR and CREATE -- three
ways, because as of 2026-08-20 it takes two different gates to catch them -- and
the allocation must not happen. `test_datalloc.py` sections 13 and 14 have the
unit forms of those refusals; this one is here because it is the only thing
standing between this file and a story that proves the tools ran rather than
that they gated.

WHAT IT RUNS AGAINST, and what it borrows. `test_datalloc.py`'s fixture -- 28
blocks in a temp directory, no vault, deleted afterwards. It is the only fixture
in the tree with the three things a CREATE needs: MFT growth slack, headroom in
the file-id table, and free runs of KNOWN sizes with a planted container
generation among them, so "it took the exact fit, and never the run holding a
container generation" is a fact about the placement policy rather than about
whatever this machine's copy of the archive last left free. Three test
modules are imported for helpers, each for a stated reason and none of them doing
any work at import time (checked 2026-08-19):

  * `test_datalloc`  the fixture, its raw-byte readers, and `comp_payload`'s
                     shape. Its readers unpack the MFT by hand and import nothing
                     from `datalloc`, which is what keeps the CREATE checks from
                     being the writer agreeing with itself.
  * `test_datwrite`  `run_cli`, so steps 3-5 drive `datwrite` through argparse
                     and `main()` exactly as its own test does. The defect that
                     test was written for lived in the dispatch, not in `Writer`.
  * `test_gwenc`     `envelope_faults`, so step 1 asks the question that file
                     asks of its corpus -- is every table we emit a shape retail
                     attests -- of the payloads THIS file invents.

RUNTIME is about a second: the payloads are a few KB and `gwenc` turns 12 KB into
1.2 KB in tens of milliseconds. Nothing here needs a vault, a client, or a
network.
"""

import binascii
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, file_id_table  # noqa: E402
import datalloc  # noqa: E402
import datmove  # noqa: E402
import datwrite  # noqa: E402
import gwdat  # noqa: E402
import gwenc  # noqa: E402
import gwentropy as G  # noqa: E402
import gwmatch  # noqa: E402
import checks  # noqa: E402
import test_datalloc as tda  # noqa: E402
import test_datwrite as tdw  # noqa: E402
import test_gwenc as tge  # noqa: E402

# FLOOR: 59, MEASURED from a green run on 2026-08-20, not projected. Every check
# below runs unconditionally -- the fixture is built here, the payloads are
# generated here, and there is no corpus to be missing and no vault to resolve,
# so a run under the floor means a step stopped executing.
#
# THE FLOOR IS DOING MORE WORK IN THIS FILE THAN IN A UNIT TEST, and it is worth
# saying why. The six steps run over ONE archive and each depends on the last, so
# the cheap way for this file to go quietly wrong is for a step to stop happening
# rather than for a check to go red -- an exception inside a step takes the run
# down loudly, but a step whose refusal moved earlier would leave the later ones
# checking a state nobody authored. The floor is what makes "step 5 did not
# happen" a FAIL instead of a shorter green.
#
# SIX SABOTAGES, applied one at a time in memory against a real run and then
# reverted. Nothing on disk was edited. RE-MEASURED 2026-08-20 after `datalloc`
# gained its fidelity gate, and the first line of the old comment was no longer
# true -- these are the counts OBSERVED, not the ones it used to claim:
#
#   `datwrite.looks_compressed` -> bool(data) (the CREATE FRAMING gate
#     stops gating)                                                        1 red
#   `datwrite.declaration_fault` -> None (the CREATE FIDELITY gate stops
#     gating)                                                              3 red
#   BOTH of the above at once                                              4 red,
#                                                              and the corrupted
#                                                              stream reaches disk
#   `datmove.move` forced back to its `compression=0` default (stages C-6)  2 red
#   `Journal.record` dropping the payload edits, keeping the field ones     5 red
#   largest fit instead of best fit, in `datplan` (so BOTH the allocation
#     and the relocation take it)                                          3 red
#
# THE FIRST THREE ARE THE READING WORTH KEEPING, and they are why step 2b was
# rewritten on 2026-08-20. Until that day ONE stub was the whole sabotage: with
# `looks_compressed` stubbed the corrupted stream allocated and both of this
# file's reds were in 2b. `datalloc` now runs `datwrite.declaration_fault` as
# well, so neither stub alone gets a corrupted stream to disk -- it takes both,
# and 2b now carries the three shapes that say why (a framing break, a trailer
# that does not break the framing at all, and a missing declaration).
#
# A FOURTH READING, kept because it is a real property and not a stub artifact:
# `looks_compressed` stubbed to True for EVERY input -- b"" included -- is a HARD
# STOP with 0 red. The C-6 stored-lookalike arm then refuses the zero-length map
# head as a compressed lookalike and CREATE raises before any check runs. That is
# `declaration_fault` doing exactly what it says over an input no real defect
# produces, and it is the reason the sabotage above is `bool(data)` rather than
# `True`.
#
# Every later step still passes under any of them, because an archive faithfully
# hands back whatever the last write put in it -- that is the shape of a flow
# test that proves nothing, measured rather than feared.
#
# The last is the weakest and is named as such. Three reds for a placement policy
# reversed EVERYWHERE is a fair reading of what this file is: it asserts an
# address at two points -- step 2's exact-fit run and step 5's best-fit
# destination -- and a third check goes with them because the row lands beside a
# different neighbour and `replace`'s refusal picks its other remedy. The rest of
# the story does not care where the bytes sit, as long as the archive hands them
# back. `test_datmove.py` is where placement is adjudicated properly, over four
# checks and against a largest-fit control.
LEDGER = checks.Ledger("author flow", floor=59)
check = checks.adopt(LEDGER)

BLOCK = tda.BLOCK
LARGEST_USABLE = tda.LARGEST_USABLE      # 3072 -- the 6-block run at block 10


def reservation(size):
    """Whole blocks a row of this size owns. The arithmetic every verb uses."""
    return -(-size // BLOCK) * BLOCK


def authored(seed, n):
    """A payload we invent: matches and literals, distinct per `seed`.

    The shape is `test_datalloc.comp_payload`'s -- a 64-byte motif repeated so
    the match coder has something to find, interleaved with an LCG's output so
    the literal coder is not idle -- but the motif and the LCG seed move with
    `seed`, and that is not decoration. Every revision below is written onto the
    SAME row, so a decode-back check that compared against a payload the previous
    revision also contained could pass on a write that never landed. Distinct
    content makes each step's assertion about the write that step performed.

    Deterministic by construction, with no `random` seed to drift, so a red here
    reproduces from this file alone.
    """
    out = bytearray()
    motif = bytes((i * 7 + 3 + seed * 29) % 251 for i in range(64))
    x = (0x9E3779B9 ^ (seed * 2654435761)) & 0xFFFFFFFF
    while len(out) < n:
        out += motif * 8
        for _ in range(48):
            x = (x * 1103515245 + 12345) & 0xFFFFFFFF
            out.append((x >> 16) & 0xFF)
    return bytes(out[:n])


def row_fields(path, row):
    """(offset, size, extraBytes, flags, nextStream, crc), from the raw bytes."""
    return tda.read_rows(path)[row]


def extent(path, off, length):
    return tda.blob(path)[off:off + length]


# --------------------------------------------------------------- 1. author

def section_author():
    """The payloads, and the streams `gwenc` makes of them. No archive yet.

    Everything here is checked BEFORE an archive is opened, and the ordering is
    the point: if the codec cannot give a payload back to itself, every later
    "the row reads back as the payload" check is testing the codec's agreement
    with itself through an archive, and a red would point at the wrong file.

    THE RLE PAYLOAD IS NOT FILLER. Its every match is at distance 1, so its
    distance alphabet is the single symbol 0 -- the shape that took
    `table_for_counts`'s `single-zero-length` arm and declared a symbol count of
    1, which no retail row of any size declares (FINDINGS 13.5 gap A, and
    `gwentropy.authoring_table`'s census). An authoring flow is exactly where
    that payload appears -- a run of one byte is what a first draft of anything
    looks like -- so it is step 3's revision rather than a fixture off to one
    side.
    """
    print("\n1. AUTHOR -- payloads we invent, through our own encoder")

    art = {
        "create": authored(1, 6144),      # the file as first written
        "revise": bytes([0xA5]) * 1200,   # smaller, and RLE: gap A's own shape
        "grow": authored(3, 4096),        # bigger again, still inside the row
        "outgrow": authored(4, 12288),    # too big for the reservation
    }
    for name, raw in list(art.items()):
        art[name + ".c8"] = gwenc.encode(raw)

    rep = gwenc.encode_report(art["create"], verify=False)
    check(rep["matches"] > 0 and rep["literals"] > 0,
          "the first payload exercises BOTH halves of the stream, matches and "
          "literals -- a payload of one repeated byte would compress beautifully "
          "and prove nothing about the match coder",
          f"{len(art['create'])} B -> {len(art['create.c8'])} B, "
          f"{rep['matches']} match token(s), {rep['literals']} literal token(s), "
          f"{rep['blocks']} block(s)")

    faults, tables = [], 0
    for name in ("create", "revise", "grow", "outgrow"):
        st, _cfg = gwmatch.build_stream(art[name])
        faults += [(name,) + f for f in tge.envelope_faults(st.blocks)]
        tables += 2 * len(st.blocks)
        art[name + ".blocks"] = st.blocks
    check(not faults,
          f"all {tables} tables across the four payloads are inside retail's "
          f"attested envelope -- declared counts at or above the measured floors "
          f"(lit {G.LITERAL_FLOOR}, dist {G.DISTANCE_FLOOR}), no zero-length "
          f"literal table, and any zero-length distance table in the all-skip "
          f"shape",
          f"{len(faults)} outside: {faults[:3]}" if faults else
          "the same rule test_gwenc.py section 8 applies to its own corpus")

    # GAP A, on the payload that would have hit it. Both builders are called on
    # the SAME counts, so the contrast is the policy and not two payloads.
    rle_block = art["revise.blocks"][0]
    counts = dict(rle_block.dist_counts)
    was = G.table_for_counts(counts)[1][2]
    now = G.authoring_table(counts, "dist")[1][2]
    check(sorted(counts) == [0],
          "the RLE payload's every match is at distance 1, so its distance "
          "alphabet is the single symbol 0",
          f"dist_counts = {counts}")
    check(was == 1 and now == G.DISTANCE_FLOOR
          and rle_block.dist_symbol_count == G.DISTANCE_FLOOR,
          f"and the writer path lifts it to {G.DISTANCE_FLOOR}, the shape retail "
          f"rows 8295..8306 carry -- the model path still says {was}, which is "
          f"what an archive has never held",
          f"table_for_counts {was}, authoring_table {now}, emitted "
          f"{rle_block.dist_symbol_count}")

    for name in ("create", "revise", "grow", "outgrow"):
        stream = art[name + ".c8"]
        back, declared = gwdat.decompress(stream)
        check(back == art[name] and declared == len(art[name])
              and datwrite.looks_compressed(stream),
              f"the {name} stream decodes back to its exact payload before any "
              f"archive is involved, and datwrite's decode gate calls it "
              f"compression 8",
              f"{len(art[name])} B -> {len(stream)} B stored "
              f"({100 * len(stream) // len(art[name])}%)")

    # An author with nothing to say must not produce a compression-8 row: the
    # 12-byte zero-block stream is FINDINGS 13.5 gap D, and the encoder is the
    # first of the two doors it was closed at.
    try:
        gwenc.encode(b"")
        refused = ""
    except ValueError as exc:
        refused = str(exc)
    check("NO BLOCKS" in refused,
          "and a zero-byte payload is refused at the encoder rather than "
          "becoming a 12-byte comp-8 row with no blocks in it",
          refused.splitlines()[0][:70] if refused else "it did not refuse")

    print(f"   authored: create {len(art['create.c8'])} B "
          f"(reservation {reservation(len(art['create.c8']))}), "
          f"revise {len(art['revise.c8'])} B, grow {len(art['grow.c8'])} B, "
          f"outgrow {len(art['outgrow.c8'])} B")
    return art


# --------------------------------------------------------------- 2. create

def section_create(tmp, art):
    """A file id, a head, a partner declaring extraBytes 8, and a decode back.

    THE FIXTURE'S GEOMETRY IS A CONSTRAINT ON THE PAYLOADS, not the other way
    round, and it is checked rather than assumed: the create stream must want
    exactly two blocks so that step 3 can shrink it to one and step 4 can put
    the second back. If the encoder's tuning ever moves a stream out of its band
    the check below goes red and names the band, which is the honest failure --
    the alternative is a story whose steps quietly stop meaning what they say.
    """
    print("\n2. CREATE -- a row, and a file id, that did not exist")
    path, _payloads = tda.fresh(tmp, "authorflow.dat")
    st = {"path": path, "pristine": tda.blob(path), "journals": []}

    stream = art["create.c8"]
    check(reservation(len(stream)) == 2 * BLOCK,
          f"the create stream wants exactly two blocks, which is the fixture's "
          f"one real constraint on it -- step 3 frees the second and step 4 puts "
          f"it back",
          f"{len(stream)} B -> {reservation(len(stream))} B reserved")

    with Archive(path) as ar:
        fid = datalloc.next_free_file_id(ar)
        before_ids = dict(file_id_table(ar, raw=True))
    check(fid not in before_ids,
          f"the id 0x{fid:X} is free in the RAW table -- the spelling the CLIENT "
          f"can address, not the convenience one",
          f"{len(before_ids)} ids already registered")

    # `expect=` IS THE PAYLOAD A READER MUST GET BACK, and it is mandatory as of
    # 2026-08-20 -- the same declaration steps 3, 4 and 5 make with `--expect`.
    # Until then this call made none, which is why it is the step a skeptic drove
    # a corrupted stream through: `alloc(confirm=True)` wrote it, `Archive.read()`
    # handed back a byte less than the payload, and every rule stayed green.
    streams = [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
               datalloc.Stream(stream, datalloc.MAP_PARTNER_FLAGS_U16,
                               extra_bytes=8, expect=art["create"])]
    journal = os.path.join(tmp, "1-create.journal.json")
    with tda.quiet():
        plan = datalloc.alloc(path, streams, fid, journal, confirm=True)
    st["journals"].append(journal)
    st["head"], st["row"] = plan.head.index, plan.rows[1].index
    st["fid"] = fid
    st["offset"] = plan.rows[1].offset
    st["reservation"] = plan.rows[1].reservation

    fields = row_fields(path, st["row"])
    check(fields[2] == 8 and fields[1] == len(stream),
          f"row {st['row']} records extraBytes 8 over {len(stream)} stored "
          f"bytes, re-derived from the MFT's own bytes",
          f"+0x0C = {fields[2]}, size {fields[1]}")
    check(fields[5] == binascii.crc32(stream)
          and fields[5] != binascii.crc32(art["create"]),
          "its entry crc is over the STORED bytes and not the payload -- which "
          "is why no checksum in this file can see a wrong-payload row and why "
          "every step below is checked by DECODE")
    check(st["reservation"] == 2 * BLOCK and st["offset"] == 7 * BLOCK,
          f"it took the two-block run at block 7 -- the EXACT fit, not the "
          f"6-block run and not the 9-block one carrying a container generation "
          f"`datplan` withholds",
          f"0x{st['offset']:X} +{st['reservation']}")

    with Archive(path) as ar:
        e = ar.row(st["row"])
        got = ar.read(e)
        check(got == art["create"] and e.compression == 8,
              f"and the ARCHIVE hands the {len(art['create'])} B payload back -- "
              f"gwenc -> datalloc -> the file -> unmodified gwdat.decompress",
              f"{len(got)} B, compression {e.compression}")
        ids = file_id_table(ar, raw=True)
        check(ids.get(fid) == st["head"] and st["row"] not in ids.values(),
              f"0x{fid:X} resolves to the HEAD (row {st['head']}) and never to "
              f"the partner -- the registration defect archive.py's docstring "
              f"lists three casualties of",
              f"0x{fid:X} -> row {ids.get(fid)}")
        check(datmove.overlaps(ar) == [], "no two rows share a block")
    check(tda.walk_chain(path, st["head"]) == [st["row"]],
          "an independent walk of nextStream from the raw bytes reaches the "
          "partner and stops there")
    check(tda.datcheck_clear(path),
          "datcheck --preflight is 10 of 10 after the allocation")
    with tda.quiet():
        bad = datwrite.verify(path)
    check(bad == 0 and tda.mft_self_ok(path),
          "and both checksum rules hold over the grown table", f"{bad} bad")
    check(len(tda.blob(path)) == len(st["pristine"]),
          "the file did not change length -- nothing here grows the archive",
          f"{len(st['pristine'])} B")

    st["post_create"] = tda.blob(path)
    return st


def section_sabotage(tmp, art):
    """THE SABOTAGE: the stream corrupted between AUTHOR and CREATE, three ways.

    Not a redundant copy of `test_datalloc.py` sections 13 and 14, and the
    difference is what this file is for. Those prove the predicates; this proves
    they are ON THE PATH THIS STORY WALKS. Every later step in this file stays
    green under any of them, because an archive faithfully hands back whatever
    the last write put in it -- a flow test without this section is a
    demonstration that the tools ran.

    ONE STUB USED TO BE ENOUGH AND IS NOT ANY MORE, and the note is rewritten
    rather than left standing because a sabotage story that is no longer true is
    worse than none. Until 2026-08-20 this section flipped one byte of the first
    Huffman table and `datwrite.looks_compressed` stubbed to True was the whole
    sabotage: the corrupted stream allocated and both reds were here. `datalloc`
    now runs `datwrite.declaration_fault` as well, so MEASURED 2026-08-20 over
    this file:

      `looks_compressed` -> bool(data) alone            1 red -- still refused,
                                                        by declaration_fault
      `declaration_fault` -> None alone                 3 red -- still refused,
                                                        by looks_compressed
      BOTH stubbed                                      4 red, and the corrupted
                                                        stream reaches disk

    CORRECTION, 2026-09-11 -- THE TABLE ABOVE NOW TAKES THREE REBINDS, NOT TWO.
    `looks_compressed` and `declaration_fault` moved out of `datwrite.py` into
    `toolkit/mapdata/datdecl.py`, which re-exports both back, so
    `datwrite.looks_compressed` is still the same object and stubbing it still
    reaches `datalloc`'s calls and `Writer.replace`'s. It does NOT reach
    `declaration_fault`'s own internal call to `looks_compressed`, which
    resolves in `datdecl`'s globals -- so the "`looks_compressed` alone" row
    above is measuring a HALF stub today: one of the two bindings is still live
    inside the other gate. Stub `datdecl.looks_compressed` alongside it to
    reproduce the measured counts. `declaration_fault` keeps its single
    binding: every caller in the tree reaches it as
    `datwrite.declaration_fault`.

    The three shapes below are why it takes both. A flip inside the Huffman table
    breaks the FRAMING and `looks_compressed` catches it; a corrupted TRAILER does
    not break the framing at all -- the stream decodes happily, one byte short,
    and agrees with itself about it -- so only the decompress-and-compare can
    see it. The third is the declaration going missing entirely, which is the
    state this whole step was in until 2026-08-20.
    """
    print("\n2b. SABOTAGE -- the stream corrupted between authoring and writing")
    path, _payloads = tda.fresh(tmp, "sabotage.dat")
    untouched = tda.blob(path)
    payload, good = art["create"], art["create.c8"]
    corrupt = bytearray(good)
    corrupt[6] ^= 0xFF                      # inside the first Huffman table
    corrupt = bytes(corrupt)

    def try_alloc(data, name, **kw):
        return tda.refusal(
            datalloc.alloc, path,
            [datalloc.Stream(b"", datalloc.MAP_HEAD_FLAGS_U16),
             datalloc.Stream(data, datalloc.MAP_PARTNER_FLAGS_U16,
                             extra_bytes=8, **kw)],
            fid, os.path.join(tmp, name), confirm=True)

    with Archive(path) as ar:
        fid = datalloc.next_free_file_id(ar)

    msg = try_alloc(corrupt, "sabotage.journal.json", expect=payload)
    check(msg and "does not DECODE" in msg and "extraBytes 8" in msg,
          "a flip inside the Huffman table is REFUSED, naming the decode rather "
          "than a byte marker -- the corrupted bytes still carry the "
          "compression-8 prologue",
          (msg or "-- it did not refuse").splitlines()[0][:72])

    # The shape the framing gate CANNOT see: the declared output size, minus one.
    short = tda.short_trailer(good)
    check(datwrite.looks_compressed(short),
          "a corrupted TRAILER passes the framing gate outright -- it decodes, "
          "and it agrees with its own trailer about the length it decoded to",
          f"declares {gwdat.decompress(short)[1]} B against a {len(payload)} B "
          f"payload")
    msg = try_alloc(short, "sabotage-short.journal.json", expect=payload)
    check(msg and "trailer declares" in msg,
          "and it is REFUSED anyway, by the decompress-and-compare against "
          "expect= -- this is the stream that reached disk through this exact "
          "call on 2026-08-19, with --verify, preflight and the overlap sweep "
          "all green afterwards",
          (msg or "-- it did not refuse").splitlines()[-1][:72])

    # And the declaration going missing, which is what this step used to do.
    msg = try_alloc(good, "sabotage-noexpect.journal.json")
    check(msg and "no expected payload" in msg and "datmove" in msg,
          "a GOOD stream with no expect= at all is refused too: the declaration "
          "is mandatory, as it has been for `datmove --compression 8` since "
          "2026-08-18",
          (msg or "-- it did not refuse").splitlines()[0][:72])

    check(tda.blob(path) == untouched
          and not any(os.path.exists(os.path.join(tmp, n)) for n in
                      ("sabotage.journal.json", "sabotage-short.journal.json",
                       "sabotage-noexpect.journal.json")),
          "and after all three the archive is untouched with no journal left "
          "behind, so every refusal landed before a Writer existed",
          f"{len(untouched)} B compared")


# --------------------------------------------------------------- 3. revise

def section_revise(tmp, st, art):
    """A SMALLER revision onto the row, through the real command line.

    The row's size falls and its reservation falls with it, which is the state
    step 4 needs and the state no unit test of `replace()` leaves behind for
    another verb to find.
    """
    print("\n3. REVISE -- a smaller revision, in place, at compression 8")
    path, row = st["path"], st["row"]
    stream, payload = art["revise.c8"], art["revise"]
    journal = os.path.join(tmp, "2-revise.journal.json")
    code, out = tdw.run_cli(
        "--dat", path, "--journal", journal, "--replace", str(row),
        "--data", tda.spill(tmp, "revise.c8", stream),
        "--compression", "8",
        "--expect", tda.spill(tmp, "revise.raw", payload))
    st["journals"].append(journal)
    check(code == 0 and "verified before writing" in out,
          "--replace --compression 8 exits 0, having DECOMPRESSED the payload "
          "and compared it against --expect before touching the archive -- the "
          "only refutation available, and only available before the write",
          f"exit {code}")

    fields = row_fields(path, row)
    check(fields[1] == len(stream) and fields[0] == st["offset"]
          and fields[2] == 8,
          f"row {row} is {fields[1]} stored bytes at the same offset, still "
          f"declaring extraBytes 8 -- a replace is not a move",
          f"0x{fields[0]:X}, size {fields[1]}")
    check(reservation(fields[1]) == BLOCK
          and reservation(fields[1]) < st["reservation"],
          f"its reservation fell {st['reservation']} -> {reservation(fields[1])} "
          f"B, and the second block is now free space `replace` cannot see -- "
          f"the state FINDINGS 14.4 is about")
    tail = extent(path, st["offset"] + len(stream),
                  st["reservation"] - len(stream))
    check(tail == b"\x00" * len(tail),
          f"the whole {len(tail)} B tail of the OLD reservation is zeroed -- no "
          f"fragment of the create revision survives inside the row's extent")
    with Archive(path) as ar:
        got = ar.read(ar.row(row))
    check(got == payload,
          f"and the archive hands back the {len(payload)} B RLE revision, not "
          f"the {len(art['create'])} B one it replaced",
          f"{len(got)} B")
    st["post_revise"] = tda.blob(path)


# ----------------------------------------------------------------- 4. grow

def section_grow(tmp, st, art):
    """The second iteration of an authoring loop: a BIGGER revision, in place.

    `--grow-to` is the caller stating the reservation the row was given. The
    number handed in here is the one an author actually holds -- the reservation
    the CREATE plan printed -- and `reservation_for` maps the create revision's
    stored size to the same 1,024 B, so either spelling names one geometry.
    """
    print("\n4. GROW BACK -- a bigger revision, into the blocks step 3 freed")
    path, row = st["path"], st["row"]
    stream, payload = art["grow.c8"], art["grow"]
    data_file = tda.spill(tmp, "grow.c8", stream)
    expect_file = tda.spill(tmp, "grow.raw", payload)
    check(BLOCK < len(stream) <= st["reservation"],
          f"the grow revision needs more than the {BLOCK} B the row now reserves "
          f"and no more than the {st['reservation']} B it was given -- an "
          f"in-place grow, which is the only kind `replace` may do",
          f"{len(stream)} B")

    refused_journal = os.path.join(tmp, "3-refused.journal.json")
    before = tda.blob(path)
    code, out = tdw.run_cli(
        "--dat", path, "--journal", refused_journal, "--replace", str(row),
        "--data", data_file, "--compression", "8", "--expect", expect_file)
    check(code != 0 and tda.blob(path) == before
          and not os.path.exists(refused_journal),
          "without --grow-to it is still refused, archive untouched, no journal "
          "-- every existing caller in the tree and the vault is on that path",
          f"exit {code}")
    check("That is a relocation, not a replacement." in out
          and f"--grow-to {len(stream)}" in out and "claimed by NOBODY" in out,
          "and the refusal names --grow-to rather than a free-run list, because "
          "the blocks it wants are the row's own and no list will ever offer "
          "them to it")

    journal = os.path.join(tmp, "3-grow.journal.json")
    code, out = tdw.run_cli(
        "--dat", path, "--journal", journal, "--replace", str(row),
        "--data", data_file, "--compression", "8", "--expect", expect_file,
        "--grow-to", str(st["reservation"]))
    st["journals"].append(journal)
    check(code == 0 and "verified before writing" in out,
          f"with --grow-to {st['reservation']} the same write exits 0, payload "
          f"verified against --expect first",
          f"exit {code}")
    check(f"annexing [0x{st['offset'] + BLOCK:X}," in out,
          "the tool names the annexation and its exact range as it makes it")

    fields = row_fields(path, row)
    check(fields[1] == len(stream) and fields[0] == st["offset"]
          and fields[2] == 8,
          f"row {row} is {fields[1]} stored bytes, still at 0x{fields[0]:X} and "
          f"still declaring extraBytes 8 -- grown, never moved")
    with Archive(path) as ar:
        got = ar.read(ar.row(row))
        shared = datmove.overlaps(ar)
    check(got == payload,
          f"the archive hands back the {len(payload)} B grow revision, decoded "
          f"out of blocks the row itself freed one step ago",
          f"{len(got)} B")
    check(not shared,
          "and no two rows share a block afterwards -- the invariant no "
          "checksum can see, since each crc covers only its own row's bytes",
          f"{len(shared)} pair(s)")
    with tda.quiet():
        bad = datwrite.verify(path)
    check(bad == 0 and tda.mft_self_ok(path) and tda.datcheck_clear(path),
          "all three checksum rules and all ten open-time rules still hold")
    st["post_grow"] = tda.blob(path)


# -------------------------------------------------------------- 5. outgrow

def section_outgrow(tmp, st, art):
    """The revision that does not fit, and the verb that exists for it.

    The remedy sentence is chosen by the geometry, and here the geometry is the
    OTHER one: the blocks past this row's reservation belong to a live row, so
    `--replace` must NOT offer `--grow-to` -- offering it would send an author to
    annex somebody else's extent. Step 4 checked the same refusal choosing the
    other branch, which is what makes this pair a measurement of the choice
    rather than of one message.
    """
    print("\n5. OUTGROW -- too big for the reservation, so it relocates")
    path, row = st["path"], st["row"]
    stream, payload = art["outgrow.c8"], art["outgrow"]
    need = reservation(len(stream))
    check(need > st["reservation"] and need <= LARGEST_USABLE,
          f"the outgrow revision wants {need} B, past the row's "
          f"{st['reservation']} B and inside the {LARGEST_USABLE} B largest run "
          f"classify_runs will hand over",
          f"{len(stream)} B stored")

    before = tda.blob(path)
    data_file = tda.spill(tmp, "outgrow.c8", stream)
    expect_file = tda.spill(tmp, "outgrow.raw", payload)
    plain_journal = os.path.join(tmp, "4-refused-plain.journal.json")
    code, out = tdw.run_cli(
        "--dat", path, "--journal", plain_journal, "--replace", str(row),
        "--data", data_file, "--compression", "8", "--expect", expect_file)
    check(code != 0 and tda.blob(path) == before
          and not os.path.exists(plain_journal),
          "`replace` refuses the outgrown revision, archive untouched, no "
          "journal", f"exit {code}")
    check("Pick a row with a bigger reservation" in out
          and "--grow-to" not in out,
          f"and this time the refusal does NOT offer --grow-to: the blocks past "
          f"this row belong to a live row, and the remedy sentence is chosen by "
          f"the geometry rather than fixed -- step 4 got the other branch on the "
          f"same code path",
          "the two branches together are the measurement; either alone is one "
          "message")

    dead_journal = os.path.join(tmp, "4-refused.journal.json")
    code, out = tdw.run_cli(
        "--dat", path, "--journal", dead_journal, "--replace", str(row),
        "--data", data_file, "--compression", "8", "--expect", expect_file,
        "--grow-to", str(st["reservation"]))
    check(code != 0 and tda.blob(path) == before
          and not os.path.exists(dead_journal),
          "`replace` REFUSES it even with the row's true entitlement stated, "
          "archive untouched, no journal",
          f"exit {code}")
    check("entitled" in out and "not a request for more" in out,
          "and the refusal says what --grow-to is: a statement about what the "
          "row was GIVEN, not a knob to make a write fit",
          out.strip().splitlines()[-1][:72] if out.strip() else "(silent)")

    with Archive(path) as ar:
        plan = datmove.plan_move(ar, row, len(stream))
    check(plan.new_offset == 10 * BLOCK,
          f"datmove plans the 6-block run at block 10 -- the SMALLEST run that "
          f"fits, not the largest, and not the 9-block one carrying a container "
          f"generation datplan withholds",
          f"0x{plan.new_offset:X} +{plan.new_reservation}")

    journal = os.path.join(tmp, "4-move.journal.json")
    with tda.quiet():
        datmove.move(path, row, stream, journal, confirm=True, compression=8,
                     expect=payload)
    st["journals"].append(journal)

    fields = row_fields(path, row)
    check(fields[0] == plan.new_offset and fields[1] == len(stream)
          and fields[2] == 8,
          f"row {row} now lives at 0x{fields[0]:X} and STILL declares "
          f"extraBytes 8 -- the C-6 case, where a relocation used to leave a "
          f"green archive holding an unreadable file",
          f"size {fields[1]}, +0x0C = {fields[2]}")
    old = extent(path, st["offset"], st["reservation"])
    check(old == b"\x00" * len(old),
          f"its old {st['reservation']} B extent is zeroed, so the free list the "
          f"client rederives at every open finds blocks, not a stale payload")
    with Archive(path) as ar:
        got = ar.read(ar.row(row))
        shared = datmove.overlaps(ar)
        ids = file_id_table(ar, raw=True)
    check(got == payload,
          f"the archive hands back the {len(payload)} B outgrow revision from "
          f"its new home", f"{len(got)} B")
    check(not shared, "no two rows share a block after the relocation",
          f"{len(shared)} pair(s)")
    check(ids.get(st["fid"]) == st["head"]
          and tda.walk_chain(path, st["head"]) == [row],
          f"and 0x{st['fid']:X} still resolves to the head, which still links to "
          f"the partner -- a move rewrites an offset, never a name")
    with tda.quiet():
        bad = datwrite.verify(path)
    check(bad == 0 and tda.mft_self_ok(path) and tda.datcheck_clear(path),
          "all three checksum rules and all ten open-time rules still hold")
    st["post_move"] = tda.blob(path)


# ----------------------------------------------------------------- 6. undo

def section_undo(st):
    """The four journals, replayed newest first, and what they compose to.

    WHAT IS ASSERTED HERE WAS MEASURED, NOT ASSUMED. The question "do these four
    journals compose back to the pristine fixture" has an answer that depends on
    facts no reader should be asked to take on trust -- whether a `before` spans
    the annexed region, whether a move's zeroing is journalled, whether the MFT
    stayed where each journal recorded it. It was run first and it composes ALL
    THE WAY BACK, byte for byte, so that is what is checked; every intermediate
    state is checked too, because a chain that only agreed at the ends could be
    two errors cancelling.

    THE ORDER IS NOT A CONVENIENCE. Each journal's `before` describes the archive
    as that run found it, so replaying them out of order writes a stale region
    over a newer one and the result verifies perfectly -- the same class of
    silent success `Journal`'s MFT-offset guard exists for.
    """
    print("\n6. UNDO -- four journals, newest first")
    path = st["path"]
    stages = [("the relocation", st["post_grow"]),
              ("the grow-back", st["post_revise"]),
              ("the smaller revision", st["post_create"]),
              ("the allocation", st["pristine"])]
    for journal, (what, want) in zip(reversed(st["journals"]), stages):
        with tda.quiet():
            rc = datwrite.revert(journal)
        got = tda.blob(path)
        check(rc == 0 and got == want,
              f"reverting {what} puts the archive back BYTE FOR BYTE to the "
              f"state before it",
              f"exit {rc}, {len(got)} B, "
              f"{'identical' if got == want else 'DIFFERS'}")

    check(tda.blob(path) == st["pristine"],
          "so the whole story composes: four writes and four reverts leave the "
          "fixture bit-identical to the one this run started with",
          f"{len(st['pristine'])} B compared")
    with Archive(path) as ar:
        check(st["fid"] not in file_id_table(ar, raw=True),
              f"the file id 0x{st['fid']:X} is unregistered again -- the row, "
              f"its id and its bytes are all gone, not merely blanked")
    with tda.quiet():
        bad = datwrite.verify(path)
    check(bad == 0 and tda.mft_self_ok(path) and tda.datcheck_clear(path),
          "and the reverted archive passes every rule the pristine one does")


def main():
    tmp = tempfile.mkdtemp(prefix="rurik-authorflow-")
    print(f"synthetic archive: {tda.FILE_SIZE} B, {tda.ENTRY_COUNT} rows, "
          f"in {tmp}")
    try:
        art = section_author()
        st = section_create(tmp, art)
        section_sabotage(tmp, art)
        section_revise(tmp, st, art)
        section_grow(tmp, st, art)
        section_outgrow(tmp, st, art)
        section_undo(st)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
