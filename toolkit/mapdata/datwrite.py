"""Write to Gw.dat, reversibly, one experiment at a time.

This is the first tool in the project that opens the archive for writing, and
the sentence it exists to falsify is from the skills study: "no tool in our
entire evidence base can write to Gw.dat". datplan.py settled that the edit is
*computable*. Only a running client can settle whether it is *accepted*, and
this is what puts the bytes on disk so that question can be asked.

SAFETY, because this one can destroy 4 GB of somebody's game:

  - It refuses any path under C:\\gw. That install is the owner's and is
    read-only to this project, permanently.
  - Every byte it changes is journalled with its previous value before the
    write, and the record is FSYNCED before the archive is touched, so --revert
    restores the exact prior state without re-copying the archive. A 4.2 GB
    re-cut per arm is otherwise the only way back. A --replace journals its
    row's WHOLE block reservation, not just the bytes it puts there, because a
    shrinking replace frees blocks the client is free to take -- see
    Writer.replace(). The journal is APPEND-ONLY, one record per line, and a
    torn write costs the last record rather than the whole file -- see Journal
    and read_journal(), which reads what a pre-2026-08-19 run wrote too.
  - --verify re-checks all three checksum rules and is the thing to run before
    and after every arm. test_datcrc.py asserts the same rules against the
    corpus; this checks one archive right now.
  - Nothing here relocates. Same offset, same row -- and since 2026-08-19
    `--replace --grow-to N` will also grow a row back INTO ITS OWN freed blocks,
    which is a resize but never a move and never an allocation of anybody else's
    space: the caller states the reservation the row is entitled to, and the
    grow is refused unless the blocks clear claimants, EOF, the live MFT and
    datplan's withheld container runs. Both of the other two verbs are separate
    tools that build on this one's `Writer` and `Journal`: `datmove.py`
    relocates a row, and since 2026-08-15 `datalloc.py` creates rows that did
    not exist and registers them in the file-id table. This sentence used to
    end "a much later problem",
    which stayed true for nine days after it stopped being true of the project.
    Neither of them grows the FILE, which remains unsupported and, because the
    journal has no way to express a truncation, unrevertible if it were.
  - CORRECTION, 2026-09-11: `Journal` and `read_journal()`, named in the two
    bullets above, now live in `datjournal.py`. Both bullets still point at
    something you can reach from here -- this module re-exports the pair under
    their own names, so `datwrite.Journal` and `datwrite.read_journal` are the
    same objects -- but the format, its measured history and the torn-journal
    reader are read over there.

THE THREE CHECKSUM RULES, all MEASURED (see test_datcrc.py):

  entry crc  at entry+0x14  CRC-32/ISO-HDLC over the entry's STORED bytes --
                            the compressed form on disk, not the payload.
  header     at 0x0C        CRC-32 over the file header's first 12 bytes.
  MFT self   row 3's +0x14  CRC-32 over the table from 0x00 to 0x48, continued
                            over 0x60 to the end. The 24 bytes in between are
                            row 3 itself, which cannot cover its own crc field
                            and so is skipped.

    python toolkit/mapdata/datwrite.py --dat DAT --verify
    python toolkit/mapdata/datwrite.py --dat DAT --corrupt-crc 12345
    python toolkit/mapdata/datwrite.py --dat DAT --overwrite 12345 --data new.bin
    python toolkit/mapdata/datwrite.py --dat DAT --verify --replace 12345 --data new.bin
    python toolkit/mapdata/datwrite.py --dat DAT --replace 12345 --data gwenc.bin \
        --compression 8 --expect payload.bin
    python toolkit/mapdata/datwrite.py --dat DAT --replace 12345 --data bigger.bin \
        --grow-to 1029564
    python toolkit/mapdata/datwrite.py --dat DAT --revert journal.json

test_datwrite.py exercises all of the above against a small archive it builds
itself. Run it before trusting a write; it exists because three defects lived
here undetected, and none of the three could fail a checksum.
"""

import argparse
import binascii
import hashlib
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import (Archive, ENTRY_SIZE, file_id_table,  # noqa: E402
                     mft_row_offset, MFT_SELF_ROW, FILE_MAGIC,
                     FILE_ID_HIGH_BIT, FILE_ID_TABLE_ROW,
                     COMPRESSION_STORED, COMPRESSION_HUFFMAN)
# `archive.py` already imports `gwdat` at module level and `Archive.read()`
# dispatches compression 8 through it, so this is not a new dependency in this
# module's chain -- it is the same decoder, named directly because
# `declaration_fault` needs it BEFORE an Archive would ever see the bytes.
# `gwdat` is pure stdlib (`import struct`); the bare-machine rule holds.
import gwdat  # noqa: E402

LIVE_INSTALL = os.path.normcase(os.path.abspath(r"C:\gw"))

# MFT_SELF_ROW (3) is imported from `archive.py`, which owns the row convention.
SELF_ROW_START = MFT_SELF_ROW * ENTRY_SIZE          # 0x48
SELF_ROW_END = SELF_ROW_START + ENTRY_SIZE          # 0x60

ENTRY_SIZE_OFF = 0x08   # u32, the entry's stored length
ENTRY_COMP_OFF = 0x0C   # u16, 0 stored / 8 huffman
ENTRY_CRC = 0x14        # offset of the crc within a 24-byte MFT row
HDR_CRC = 0x0C          # offset of the crc within the 32-byte file header
HDR_MFT_OFFSET = 0x10   # u64, where the master file table lives

# The refusal region: bytes 0x00..0x0D inclusive of the CRC dword, i.e. the
# four fields the client's header gate reads before it will look at anything
# else. A write overlapping ANY of it is refused outright by `Writer.put` --
# see `_refuse_header` for why this one region is unlike every other bad write.
HDR_REFUSE_START = 0x00
HDR_REFUSE_END = HDR_CRC + 4        # 0x10, exclusive
MFT_HDR_COUNT = 0x0C    # u32 inside the MFT's own first row: the entry count


def mft_offset_of(path):
    """The MFT's address, read from the 32-byte file header ALONE.

    Deliberately not `Archive(path).mft_offset`, and the difference is a recovery
    path rather than a style preference. `Archive.__init__` goes on to parse the
    table and REFUSES when `entry_count * 24 != mft_size` (archive.py:320) -- and
    that inequality is exactly the state an interrupted allocation leaves behind,
    because the descriptor's count and the header's declared size are two
    separate 4-byte writes and no ordering makes them one. MEASURED 2026-08-15,
    in both orders: `Archive()` raised and `datwrite --verify` raised with it.

    So the tool that exists to undo a half-finished write could not open the
    archive in precisely the case it exists for. This reads sixteen bytes and
    parses none of the table, which is all `revert()` ever needed.
    """
    with open(path, "rb") as fh:
        head = fh.read(32)
    if len(head) < 32 or head[:4] != FILE_MAGIC:
        raise SystemExit(f"{path} does not begin with a Gw.dat file header "
                         f"(no {FILE_MAGIC!r} magic); refusing to guess where "
                         f"its MFT is")
    return struct.unpack_from("<Q", head, HDR_MFT_OFFSET)[0]


def guard(path):
    """Never the live install. Not a warning; a refusal.

    Shared with `revert()`, which is exactly why `dat_study` is not here -- see
    `guard_source`.
    """
    p = os.path.normcase(os.path.abspath(path))
    if p == LIVE_INSTALL or p.startswith(LIVE_INSTALL + os.sep):
        raise SystemExit(
            f"Refusing to write inside the live install at {LIVE_INSTALL}.\n"
            f"  asked for: {path}\n"
            f"That install is read-only to this project. Point --dat at the "
            f"run-dir or study copy under vault/.")
    return p


def guard_source(path):
    """Never the pristine snapshot either. NEW edits only.

    `vault/dat_study` is the archive every other copy is cut from, and losing it
    means re-extracting from the owner's own install. `rebloat.guard_target()`
    has refused it since that tool existed, and its docstring says it "adds
    dat_study" to what datwrite refuses -- which was never true. This module is
    the one that opens the archive `r+b`, so the gap sat in front of the only
    write path there is. Found 2026-08-12 by an adversarial review of rung E3's
    runsheet, which had told a future operator the check existed.

    It is deliberately NOT in `guard()`, and that distinction is the design:
    `guard()` is also what `revert()` calls, and replaying a journal is the ONE
    legitimate write to `dat_study` -- it is how this mistake gets undone. A
    blanket refusal would close the recovery door behind the accident.

    Worth stating because no checksum catches it: `--replace` fixes the entry
    crc and the MFT self-crc as it goes, so a mutated snapshot passes
    `--verify`, passes `datcheck`, and reads as healthy everywhere.
    """
    parts = os.path.normcase(os.path.abspath(path)).replace("\\", "/").split("/")
    if "dat_study" in parts:
        raise SystemExit(
            f"Refusing to write to {path}\n"
            f"  vault/dat_study is the SOURCE snapshot every other copy is cut "
            f"from, and nothing in this repo can put it back -- losing it means "
            f"re-extracting from the owner's install.\n"
            f"  Point --dat at a copy under vault/run/ or vault/dat_*/ that you "
            f"can throw away.\n"
            f"  (--revert is still allowed there: undoing a mistaken write is "
            f"the one thing that should be.)")
    return path


def reservation_for(size, block):
    """Whole blocks, size rounded up. A zero-size row reserves nothing.

    Same expression as `datmove.reservation_for`; not imported, because
    `datmove` imports `datplan` which imports more, and this module is the one
    that must keep working when the rest of the tree does not.
    """
    return -(-size // block) * block


def claimants(ar, lo, hi, exclude):
    """Every OTHER live row whose reservation intersects [lo, hi).

    A row's reservation, not its size: the bytes between `size` and the end of
    the last block belong to that row even though nothing is stored in them, and
    a grow that took them would be corrupting a neighbour that still verifies.
    That is the invariant `test_datmove.py` was written around -- two rows
    sharing blocks is the one thing no checksum sees, because each crc covers
    only its own row's bytes.
    """
    out = []
    for e in ar.entries:
        if e.index == exclude or e.size == 0:
            continue
        o = e.offset
        h = o + reservation_for(e.size, ar.block_size)
        if o < hi and lo < h:
            out.append((o, h, e.index))
    out.sort()
    return out


COMPRESSION_CODES = (COMPRESSION_STORED, COMPRESSION_HUFFMAN)

# The compression-8 prologue, MEASURED. `data[3] == 0x02` -- four zero lead bits
# then `first_four = 2` -- holds on 138,708 of 138,708 comp-8 rows in dat_study,
# widened to 258,708 rows across four archives and three client builds
# (studies/archivewrite/FINDINGS.md 13.3). ONE value, no exceptions.
#
# `data[2]` is the top of the declared literal count and is 0x01 on every RETAIL
# row, but NOT on every stream `gwenc` produces: measured 2026-08-18, five of
# nineteen gwenc outputs (all the incompressible ones, where the literal count is
# small) carry `data[2] == 0x00`. So the two-byte marker is the right test for
# "are these bytes RETAIL-SHAPED compressed data" and the WRONG test for "did our
# own encoder make this". The two directions below use different tests for that
# reason, and each uses the tightest one that does not fire on its own legitimate
# population.
#
# THIS COMMENT USED TO END "`datalloc.py:432` still uses the two-byte form as a
# comp-8 GATE and will refuse legitimate gwenc output; that is recorded, not fixed
# here." BOTH SENTENCES WERE FALSE, and the second outlived the first: `datalloc`
# stopped using the marker on 2026-08-18 and decides by DECODING through
# `looks_compressed` (`datalloc.py:560`), so it refuses no legitimate gwenc output
# and there is nothing left to fix. As of 2026-08-20 it also runs
# `declaration_fault` over every stream it is handed (`datalloc.check_declarations`)
# -- the framing test and the fidelity test, in that order, which is the same pair
# `replace()` runs below.
HUFFMAN_PROLOGUE_BYTE = 0x02
HUFFMAN_RETAIL_MARKER = b"\x01\x02"


def looks_compressed(data):
    """Are these bytes a compression-8 stream? -> bool. Decides by DECODING.

    Used in exactly one direction -- to refuse a STORED write of bytes that are
    actually compressed, FINDINGS C-6 -- and never to infer a code. A caller
    always declares; this only ever contradicts a declaration.

    THE BYTE MARKER ALONE IS NOT ENOUGH, and the measurement is why. `data[2:4]
    == 0x01 0x02` holds on every retail row, and the obvious cheap test is to
    compare those two bytes. Measured against `gwenc` output 2026-08-18 it MISSES
    six of eighteen cases -- `random 0/1/4/16/64` and `pattern 100`, every one of
    them a payload under ~256 bytes, where the declared literal count is small
    enough that `data[2]` falls to 0x00. Twelve of eighteen hit, and the twelve
    are every payload of 256 B or more. A guard against a silent, permanent,
    whole-file corruption with a measured one-in-three miss rate on small
    payloads is not a guard, so the marker is demoted to a PREFILTER and the
    decoder makes the decision.

    `data[3] == 0x02` is the prefilter: 258,708 of 258,708 comp-8 rows carry it
    (FINDINGS 13.3) and it is 18 of 18 on our own encoder, so nothing compressed
    gets past it, while it keeps the decode attempt off 255 of every 256 stored
    writes. `textwrite`, `iconset`, `rebloat` and the six `a4stage*.py` scripts
    pay nothing.

    The decision is then: it decompresses without raising, AND the trailer's
    declared size equals the number of bytes that came out.

    BE HONEST ABOUT HOW STRONG THAT SECOND HALF IS, because it is weaker than it
    reads and this file has a rule about checks that cannot fail.
    `gwdat.decompress` takes the declared size FROM the trailer and uses it as
    the decode loop's own termination bound (`gwdat.py:349-350`, `:356`), so
    `declared == len(back)` is TRUE by construction whenever the loop terminates
    normally. It refutes exactly one thing: a stream that runs OUT of input
    first, which is the failure FINDINGS 13.3 measured -- one word short decodes
    silently and lands with a nonsense declared size (2,147,549,192 against 2,722
    bytes out). That is worth having and it is not a general validity check.

    SO THE MEASURED RATES, both taken 2026-08-18 rather than argued:

      * RECALL, on what a caller would actually mis-declare: **20 of 20** `gwenc`
        streams across payloads from 0 to 9,000 B, and **10 of 10** real
        compression-8 rows sampled from `vault/dat_study/Gw.dat`. Nothing that is
        genuinely compressed got past it.
      * FALSE REFUSALS: **4 of 38,621** real STORED rows in the same archive --
        177242, 177264, 177332, 177333 (all flags 0xFF03, at the very end of the
        table; 177334 clears the prefilter and is correctly not flagged). Their
        bytes decode to exactly `size - 12` under our decoder, but they do NOT
        re-emit byte-identically through `gwenc.reemit` the way 3,051 genuine
        comp-8 rows do (FINDINGS 13.1), so the reading is that these are genuine
        false positives rather than retail's own C-6 -- CONTESTED, and not
        settled from here. Also 0 of 6,005 synthetic plaintext payloads.

    Re-emission was tried as a confirming test and REJECTED on measurement: it
    reproduces retail's streams but **0 of 15** of our own encoder's, so it would
    have thrown away the entire population this guard exists for. It would also
    have put `gwenc`/`gwmatch`/`gwentropy` in this module's import chain, which
    `reservation_for`'s docstring exists to keep out.

    KEEPING IT AT 4 IN 38,621 IS THE DELIBERATE CALL, and the asymmetry is why. A
    false refusal is LOUD, changes nothing on disk, and costs one re-run with
    `expect=data` -- a caller stating that the stored bytes are the payload,
    which is what a stored row IS, so it is a statement rather than a switch. A
    MISS is silent, passes every rule this project owns, and costs the whole file
    plus its entire nextStream chain, permanently, the first time the client
    repairs for any unrelated reason (FINDINGS 5.1). That is not the direction to
    economise in.
    """
    data = bytes(data)
    if len(data) < 4 or data[3] != HUFFMAN_PROLOGUE_BYTE:
        return False
    try:
        back, declared = gwdat.decompress(data)
    except Exception:                                        # noqa: BLE001
        return False
    return declared == len(back)


def declaration_fault(data, compression, expect, stored_lookalike_ok=False):
    """Is it safe to mark `data` with this compression code? -> None, or the reason.

    Never writes, never raises, never opens anything. Returns a string a caller
    can put in its own exception type, which is why `datwrite` (SystemExit) and
    `datmove` (Refused) can share one implementation of the rule.

    THE FAILURE CLASS THIS EXISTS FOR is studies/archivewrite/FINDINGS.md C-6,
    and it is the sharpest trap in that dossier: **a green archive holding an
    unreadable file.** The entry CRC is over the STORED bytes, so a row whose
    compression code disagrees with its bytes passes all three checksum rules and
    all ten of `datcheck --preflight`'s open-time rules. `datcheck.py` contains
    ZERO references to compression codes, so NOTHING WE OWN can refute a
    conforming-but-wrong compressed payload by inspection. The only way to know a
    compression-8 row is readable is to DECOMPRESS IT, and the only moment that
    is cheap is before the write.

    So the contract is: the caller declares BOTH the code and the payload a
    reader must get back, and this checks the declaration against the bytes
    before any of them reach the archive. For compression 8 the expected payload
    is MANDATORY, not optional -- an unverifiable compressed write is exactly the
    thing this rung exists to make impossible.

    WHAT IT CANNOT CATCH, and this belongs in the open where a caller sees it:

      * The round trip is through `gwdat.decompress`, which is OUR decoder. It
        proves agreement with our reader, NOT correctness against the client's.
        FINDINGS 13.5 gap A -- a declared `symbol_count == 1`, which our encoder
        emits and retail never does -- is precisely the shape that would pass
        here and could still be refused by the client. **A8 is the only oracle.**
      * A caller that hands plaintext with `compression=0` and gets the shape
        check's silence has proved nothing; only the explicit code is doing work
        there. The shape tests below are a CROSS-CHECK on the declaration, not a
        classifier, and they are deliberately never used to INFER a code.

    The two shape rules, both refutable and each measured against the population
    it has to survive:

      * `compression=8` with `data[3] != 0x02` is refused. 258,708-row witness,
        and it does not fire on any of nineteen measured `gwenc` outputs.
      * `compression=8` declaring a ZERO-BYTE payload is refused, whether the
        stream is empty or merely decompresses to nothing. See the two arms
        below; this is FINDINGS gap D from the archive side.
      * `compression=0` with bytes that DECODE as a compression-8 stream is
        refused, naming compression 8. This is the arm that catches C-6. It
        decides by decoding rather than by a byte marker, because the marker
        measurably misses small payloads -- see `looks_compressed`. Overriding
        it takes `stored_lookalike_ok=True`, which is deliberately awkward and
        prints a line naming C-6 when taken; `expect=data` used to waive it and
        that was a hole, not a hatch -- see the comment on the arm itself.
    """
    data = bytes(data)
    if compression not in COMPRESSION_CODES:
        return (f"compression {compression} is not a code this archive uses. "
                f"Measured across every live row of every vault archive the "
                f"field takes only {{0, 8}}; refusing to invent a third.")

    if compression == COMPRESSION_HUFFMAN:
        if not data:
            return ("a zero-length compression-8 row is a shape nothing in the "
                    "corpus witnesses -- retail's smallest comp-8 row is 56 B "
                    "and holds a block. `replace(row, b\"\")` is the documented "
                    "re-bloat trigger and means STORED; refusing to overload it.")
        if expect is None:
            return ("a compression-8 write must declare the payload a reader "
                    "must get back, and none was given.\n"
                    "  Nothing else can check it afterwards: the entry CRC is "
                    "over the STORED bytes, so a wrong payload passes every "
                    "checksum rule and all ten open-time rules, and datcheck "
                    "has no notion of a compression code at all. The "
                    "decompress-and-compare below is the ONLY refutation "
                    "available, and it is only available before the write.")
        if not bytes(expect):
            # GAP D, THE ARCHIVE-SIDE DOOR. The arm above refuses an EMPTY
            # stream; this refuses a stream whose PAYLOAD is empty, which is a
            # different shape and reaches the archive by a different route.
            # `gwenc.encode(b"")` emits a well-formed 12-byte compression-8
            # stream today: byte 3 is 0x02, it decompresses without raising, its
            # trailer declares 0 B, and 0 == len(b"") -- so every arm below
            # agrees and the write is accepted. The row then reads back as
            # nothing at all, which is indistinguishable from an unreadable row
            # and green on all three checksum rules.
            #
            # The floor is measured, not argued: retail's smallest compression-8
            # row is 56 B and it holds a whole block. A zero-block comp-8 stream
            # is a shape nothing in the corpus witnesses. The encoder is being
            # taught to refuse it too; this is the door on the writer's side, so
            # neither one is the only thing standing between the archive and it.
            return ("a compression-8 write declaring a ZERO-BYTE payload is a "
                    "shape nothing in the corpus witnesses -- retail's smallest "
                    "comp-8 row is 56 B and holds a whole block, and a stream "
                    "that decompresses to nothing would leave the row reading "
                    "back as nothing while every checksum rule stayed green.\n"
                    "  `replace(row, b\"\")` is the documented re-bloat trigger "
                    "and means STORED; a zero-block compressed stream is not a "
                    "second spelling of it.")
        if len(data) < 4 or data[3] != HUFFMAN_PROLOGUE_BYTE:
            got = data[3] if len(data) > 3 else None
            return (f"these bytes are not shaped like a compression-8 stream: "
                    f"byte 3 is "
                    + ("absent" if got is None else f"0x{got:02X}")
                    + f", and every one of 258,708 comp-8 rows measured across "
                      f"four archives and three client builds has 0x"
                      f"{HUFFMAN_PROLOGUE_BYTE:02X} there (four zero lead bits "
                      f"then first_four = 2). FINDINGS 13.3.")
        try:
            back, declared = gwdat.decompress(data)
        except Exception as exc:                              # noqa: BLE001
            return (f"the bytes do not decompress at all "
                    f"({type(exc).__name__}: {exc}). A row marked compression 8 "
                    f"whose payload the decoder rejects is a file the client "
                    f"deletes -- with its whole nextStream chain -- the next "
                    f"time repair fires for any reason (FINDINGS 5.1).")
        expect = bytes(expect)
        if declared != len(expect):
            return (f"the stream's trailer declares {declared} B and the "
                    f"expected payload is {len(expect)} B. A stream one word "
                    f"short does NOT raise -- it decodes silently short "
                    f"(FINDINGS 13.3, measured on our own decoder), which is "
                    f"exactly the corruption no checksum can see.")
        if back != expect:
            where = next((i for i, (a, b) in enumerate(zip(back, expect))
                          if a != b), min(len(back), len(expect)))
            return (f"the bytes decompress to {len(back)} B that are NOT the "
                    f"expected payload ({len(expect)} B); first difference at "
                    f"offset {where}. The archive would be green and the file "
                    f"unreadable.")
        return None

    # compression == 0. The stored bytes ARE the payload, by definition.
    if expect is not None and bytes(expect) != data:
        return (f"a stored row's bytes ARE its payload, and the {len(data)} B "
                f"being written differ from the {len(bytes(expect))} B declared "
                f"as expected. One of the two is wrong.")
    if looks_compressed(data) and not stored_lookalike_ok:
        # CORRECTED 2026-08-18, and this arm used to read `if expect is None and
        # looks_compressed(data)`. A skeptic drove C-6 straight through the gap:
        #
        #     datwrite.py --dat X --replace N --data s.bin --compression 0 --expect s.bin
        #
        # with `s.bin` genuine `gwenc` output. `expect == data` is trivially true for
        # ANY bytes, so pointing --expect at the same file waived the only check that
        # could see the problem. Exit 0, preflight 10 of 10, crc sweep 0 bad, and the
        # log line INDISTINGUISHABLE from an ordinary stored replace -- the exact
        # green-archive-holding-an-unreadable-file state this function exists to
        # prevent, reached through the documented CLI with no warning to find later.
        #
        # `expect=data` was described here as "a statement rather than an override".
        # It is not: it is an override that costs nothing to type by accident. The
        # real statement is now a separate, deliberately awkward argument, and the
        # decode is consulted whether or not `expect` was given.
        #
        # Refusing outright is nearly free, and both halves are measured: of 38,621
        # real stored rows only 4 look compressed (177242/177264/177332/177333, all
        # flags 0xFF03), and of 1,500 DECOMPRESSED retail payloads -- the population
        # every authoring caller actually hands us -- exactly 0 do.
        return ("these bytes are a decodable compression-8 stream and the "
                "write declares compression 0.\n"
                "  That is studies/archivewrite/FINDINGS.md C-6: the row would "
                "be marked STORED while its bytes are still compressed, the CRC "
                "is over the stored bytes and does not move, so all three "
                "checksum rules and all ten open-time rules would still pass "
                "and the file would simply be unreadable. Nothing we own can "
                "detect it afterwards.\n"
                "  If these really are compressed bytes, pass compression=8 "
                "with the payload they decompress to. If they really are "
                "plaintext that merely decodes -- 4 of 38,621 real stored rows "
                "do, and 0 of 1,500 decompressed retail payloads -- pass "
                "stored_lookalike_ok=True (`--stored-lookalike-ok`), which is "
                "deliberately awkward because it is an override rather than a "
                "statement, and it prints a line naming C-6 when taken.")
    return None


class DonorRow:
    """What a donor archive says one row should contain. Read-only, always."""

    __slots__ = ("path", "row", "size", "compression", "crc", "flags",
                 "payload", "sha256", "file_ids", "image")

    def __init__(self, path, row, size, compression, crc, flags, payload,
                 file_ids, image):
        self.path, self.row, self.size = path, row, size
        self.compression, self.crc, self.flags = compression, crc, flags
        self.payload, self.file_ids = payload, file_ids
        self.sha256 = hashlib.sha256(payload).hexdigest()
        # The donor's WHOLE reservation, not just its payload. The bytes between
        # `size` and the end of the last block belong to the row, and a restore
        # that zero-filled them would put the row back "correctly" while leaving
        # it bytewise different from every pristine copy -- a difference that no
        # checksum sees and that would show up later as an unexplained diff.
        # Whether anything reads past the size field is UNTESTED (see replace()),
        # which is the argument for reproducing rather than inventing them.
        self.image = image


def read_donor(donor_path, row):
    """Row N's STORED bytes out of a donor archive.

    DELIBERATELY NOT GUARDED, and that is a decision rather than an oversight:
    `guard()` protects the thing being WRITTEN, and the owner's own install at
    C:\\gw is the canonical donor -- reading bytes from it is explicitly
    permitted and refusing it here would make the best source unusable. The
    donor is opened 'rb' and never anything else.

    The donor's own crc is checked against its payload before the caller is
    allowed to trust it. A donor that fails its own checksum is a worse source
    than the armed row it would replace.
    """
    with Archive(donor_path) as ar:
        e = ar.row(row)
        res = reservation_for(e.size, ar.block_size)
        ar.fh.seek(e.offset)
        image = ar.fh.read(res)
        payload = image[:e.size]
        if len(payload) != e.size:
            raise SystemExit(
                f"donor row {row} declares {e.size} bytes and only "
                f"{len(payload)} could be read from {donor_path}")
        if len(image) != res:
            # The last row in a file can end short of its reservation. Pad, and
            # say so, rather than silently restoring fewer bytes than claimed.
            print(f"  note: donor row {row}'s reservation runs {res - len(image)}"
                  f" B past EOF; the tail will be zero-filled")
            image = image + b"\x00" * (res - len(image))
        if e.size and binascii.crc32(payload) != e.crc:
            raise SystemExit(
                f"donor row {row} in {donor_path} FAILS ITS OWN CRC "
                f"(stored 0x{e.crc:08X}, computed "
                f"0x{binascii.crc32(payload):08X}). Refusing to restore from a "
                f"donor that is itself damaged.")
        ids = sorted(f for f, r in file_id_table(ar).items() if r == row)
        return DonorRow(donor_path, row, e.size, e.compression, e.crc, e.flags,
                        payload, ids, image)


def check_identity(target_path, row, donor):
    """The portable key: target row and donor row must NAME THE SAME FILE.

    A row index is a fact about the copy (`mapchunks.py`:117) -- 304 file ids
    changed row across the one update this project has measured. So a donor cut
    from a different build can hold a perfectly valid, perfectly wrong file at
    row N, and every checksum would agree afterwards.

    Refuses only when BOTH rows are addressable and the id sets are disjoint,
    because that is the only case where the archives positively disagree. When
    either row carries no file id the check cannot be made and this says so
    rather than implying it passed -- the alternative is a silent green from a
    check that never ran.
    """
    with Archive(target_path) as ar:
        ids = sorted(f for f, r in file_id_table(ar).items() if r == row)
    if not ids or not donor.file_ids:
        which = "target" if not ids else "donor"
        print(f"  WARNING: the {which} row {row} carries no file id, so the "
              f"identity check COULD NOT RUN. You are trusting the row number.")
        return None
    shared = set(ids) & set(donor.file_ids)
    if not shared:
        raise SystemExit(
            f"row {row} names a DIFFERENT FILE in the two archives:\n"
            f"    target {target_path}: "
            + ", ".join(hex(i) for i in ids) + "\n"
            f"    donor  {donor.path}: "
            + ", ".join(hex(i) for i in donor.file_ids) + "\n"
            f"  A row index is a fact about the copy. Restoring across this "
            f"would write a valid file into the wrong row and every checksum "
            f"would agree afterwards.")
    print(f"  identity: row {row} is file id "
          + ", ".join(hex(i) for i in sorted(shared)) + " in both archives")
    return sorted(shared)


def row_offset(ar, row):
    """Where row N's 24 bytes start. Row N sits at mft_offset + N*24.

    Delegates to `archive.mft_row_offset` so this and `datplan.py` cannot drift:
    the planner carried its own expression with a `- 1` in it and printed three
    wrong addresses for months while this one was right. One function now.
    """
    return mft_row_offset(ar.mft_offset, row)


def mft_self_crc(mft, entry_count):
    """Row 3's crc: the table, with row 3's own 24 bytes skipped.

    A checksum cannot cover the field it is stored in, so the row describing the
    table excludes itself. Reproduces exactly on both archives on this machine.
    """
    acc = binascii.crc32(mft[0x00:SELF_ROW_START])
    return binascii.crc32(mft[SELF_ROW_END:entry_count * ENTRY_SIZE], acc)


def read_mft(ar):
    ar.fh.seek(ar.mft_offset)
    return bytearray(ar.fh.read(ar.mft_size))


# The journal format lives in `datjournal.py` since 2026-09-11. Re-exported
# here under its own names: `Writer.__init__` below constructs `Journal(...)`
# and `revert()` calls `read_journal(...)` as bare names, `test_datwrite.py`
# patches `datwrite.Journal.flush`, and `deploy.py` calls
# `datwrite.read_journal`.
from datjournal import JOURNAL_CLOSER, Journal  # noqa: F401,E402


#: The one word a reader joins on to say "the GROW GATE refused this, and not
#: something else". It is deliberately not a sentence: sentences get reworded.
GROW_GATE_TOKEN = "GROW-GATE-REFUSED"

#: The four conditions `_grow_gate` enforces, in its own order, as the names the
#: typed refusal carries. Stable identifiers rather than prose.
GROW_GATE_CONDITIONS = ("claimants", "eof", "live-mft", "withheld-run")


class GrowGateRefused(SystemExit):
    """A grow the four-condition gate refused -- BY CONDITION, not by wording.

    A SUBCLASS OF `SystemExit`, AND THAT IS THE WHOLE COMPATIBILITY ARGUMENT.
    Every existing caller catches `SystemExit` (or lets it exit the process),
    every message below is byte-for-byte what it was, and the exit code is
    unchanged -- what is added is a `condition` a caller can branch on instead of
    reading English. `overlay.py` and `deploy.py` both drive `replace(grow_to=)`
    and both have to tell "another row took these blocks" apart from "these
    bytes are not what you declared", because only the first may be followed by
    a relocation.

    WHY A TOKEN AS WELL AS A CLASS. `deploy.py` runs this module as a SUBPROCESS
    -- an exception does not cross that boundary, and until 2026-08-20 it joined
    on four fixed fragments of the gate's own sentences (`deploy.GROW_GATE_
    MARKERS`). That join fails SAFE if the wording moves, which is the right
    direction and still a join on prose. So `main()` prints one machine-readable
    line naming the condition, and the wording becomes the fallback rather than
    the contract. The line is ADDED beside the refusal, never inside it: the
    refusal text is what readers and greps already know (test_datwrite 11a pins
    its first sentence verbatim for exactly that reason).

    `condition` is one of `GROW_GATE_CONDITIONS`, in the gate's own order.
    """

    def __init__(self, condition, message):
        if condition not in GROW_GATE_CONDITIONS:
            # A typo here would produce a refusal no consumer recognises, which
            # is the failure this class exists to remove. Cheap, and it can only
            # fire on a source edit.
            raise ValueError(f"{condition!r} is not one of "
                             f"{GROW_GATE_CONDITIONS}")
        super().__init__(message)
        self.condition = condition

    @property
    def marker(self):
        """The one line a subprocess reader joins on. Never inside the message."""
        return f"  {GROW_GATE_TOKEN} condition={self.condition}"


class Writer:
    """An open archive plus the journal of what has been done to it.

    Constructing one is the statement of intent to write, so both refusals live
    here. `revert()` calls `guard()` directly and deliberately does not come
    through this constructor -- see `guard_source`.
    """

    def __init__(self, path, journal_path):
        guard(path)
        guard_source(path)
        self.path = path
        self.ar = Archive(path)
        self.fh = open(path, "r+b")
        self.journal = Journal(journal_path, os.path.abspath(path),
                               self.ar.mft_offset)

    def close(self):
        self.fh.close()
        self.ar.close()
        self.journal.close()

    def resync(self, why):
        """Re-parse the archive header. Call after any STRUCTURAL change.

        `self.ar` is parsed once, in `__init__`, and two of its fields stop being
        true the moment a row is appended: `mft_size`, which `read_mft()` sizes
        its read from, and `entry_count`, which `mft_self_crc()` slices with.
        Neither is refreshed anywhere, because until 2026-08-15 nothing in this
        file could change them -- `replace` and `restore` keep the table exactly
        the size they found it.

        The failure that made this necessary is silent in the worst direction.
        `fix_mft_self_crc()` on a stale view computes the crc over the
        PRE-GROWTH extent, writes it into row 3, and prints a confident
        before/after -- and the archive is left failing its own self-checksum
        with a green line on the screen. `datcheck --preflight` still returns 10
        of 10 clear, because datcheck does not check the self-crc at all; only
        `datwrite --verify` does, and that is a separate command a person has to
        remember to run. Three independent readers found this the same day.

        Reopening rather than patching the three fields is deliberate: the point
        is to believe the DISK, and every write here is fsynced before this runs.
        """
        self.ar.close()
        self.ar = Archive(self.path)
        print(f"  resync  ({why}): entry_count {self.ar.entry_count}, "
              f"mft_size {self.ar.mft_size}")
        return self.ar

    def read_mft(self):
        """The table as it stands ON DISK, through the handle that wrote it.

        Deliberately not the module-level read_mft(self.ar). The Archive's handle
        is a separate, buffered, read-only file object opened before any of our
        writes, and a seek back inside its current 8 KB window is answered from
        that buffer instead of from disk. It then hands back a PRE-WRITE copy of
        the table, fix_mft_self_crc() finds the old crc matching the old bytes,
        prints "already correct", and leaves the archive failing its own
        self-checksum with nothing said -- the one outcome this file is supposed
        to make impossible.

        Whether it happens depends on where the buffer window happens to fall: on
        the 4.2 GB archive the MFT is megabytes and misses it, on a small archive
        it does not. MEASURED 2026-08-10 on the synthetic archive in
        test_datwrite.py, where every replace left the self-crc wrong while
        reporting it already correct. A correctness property must not rest on
        which side of a buffer boundary the table happens to fall.
        """
        self.fh.seek(self.ar.mft_offset)
        return bytearray(self.fh.read(self.ar.mft_size))

    def _refuse_header(self, offset, length, what):
        """The 32-byte file header's first 13 bytes are the one region whose
        corruption is UNRECOVERABLE, and this refuses to touch them.

        Not a warning. A refusal, and it is deliberately not overridable.

        WHY THIS IS DIFFERENT FROM EVERY OTHER BAD WRITE. Damage anywhere else
        sends the client into its repair path, which is destructive but at
        least announces itself (`Repairing corrupt archive`) and can adopt an
        older MFT generation. Damage to bytes 0x00..0x0C -- the magic, the
        header size, the block size, and the CRC at +0x0C that covers the first
        twelve -- fails the header gate at 0x0047B6DD, returns 0 from a
        six-instruction tail at 0x0047BE38 that contains NO LOGGING CALL AT
        ALL, and that zero tail-jumps to ArchiveCreate (0x004797EC), which
        writes a fresh empty 16-row archive over a 4.2 GB file. Silently. No
        tool in this repo can recover from it and no MFT generation helps,
        because the header is what says where the MFT is.

        This module never had a reason to write here, so the region was
        protected by absence -- which is not protection, it is luck that nobody
        has yet added a caller. studies/archivewrite/FINDINGS.md 5.2/5.6 rule 2.
        """
        lo, hi = offset, offset + length
        if lo < HDR_REFUSE_END and hi > HDR_REFUSE_START:
            raise SystemExit(
                f"REFUSED: {what}\n"
                f"  the write [0x{lo:X},0x{hi:X}) overlaps the file header's "
                f"bytes [0x{HDR_REFUSE_START:X},0x{HDR_REFUSE_END:X}) -- magic, "
                f"headerSize, blockSize and the CRC that covers them.\n"
                f"  Corrupting that region does not produce an error or a "
                f"repair. The client's ArchiveOpen returns 0 with no log line "
                f"and tail-jumps to ArchiveCreate, which OVERWRITES THE WHOLE "
                f"ARCHIVE with a fresh empty one.\n"
                f"  There is no recovery path for this in this repo and no MFT "
                f"generation can help, because the header is what locates the "
                f"MFT. If you genuinely mean to rewrite a header, do it on a "
                f"copy with a tool that is not this one.")

    def put(self, offset, data, what):
        """One journalled write. Reads the old bytes first, always."""
        self._refuse_header(offset, len(data), what)
        self.fh.seek(offset)
        before = self.fh.read(len(data))
        if len(before) != len(data):
            raise SystemExit(f"short read at 0x{offset:X}: wanted {len(data)} "
                             f"bytes, got {len(before)}")
        if before == bytes(data):
            print(f"  (no-op) 0x{offset:012X} +{len(data)} {what}")
            return
        self.journal.record(offset, before, data, what)
        self.fh.seek(offset)
        self.fh.write(bytes(data))
        self.fh.flush()
        os.fsync(self.fh.fileno())
        print(f"  wrote   0x{offset:012X} +{len(data)} {what}")

    def set_entry_crc(self, row, value):
        self.put(row_offset(self.ar, row) + ENTRY_CRC,
                 struct.pack("<I", value), f"MFT row {row} crc")

    def _grow_gate(self, row, e, cur_res, want_res):
        """Every condition an IN-PLACE GROW must clear, before the first put().

        Shared by `replace(grow_to=...)` and `restore()`, and factored rather
        than copied because this module has already paid for the alternative:
        `row_offset` delegates to `archive.mft_row_offset` because the planner
        carried its own expression with a `- 1` in it and printed three wrong
        addresses for months. `restore()` held the only copy of this gate until
        2026-08-19, and it was the only working grow path in the file.

        A ROW'S TRUE RESERVATION IS NOT RECORDED ANYWHERE. The 24-byte MFT row is
        `offset u64 / size u32 / extraBytes u16 / flags u16 / nextStream u32 /
        crc u32` (`datalloc.py:127-132`, ArenaNet's own field names) -- there is
        no allocation-length field, so once a shrink lands, "what this row was
        given" survives only in a donor archive, in a journal's `before`, or in
        the caller's head. The bound therefore has to come from GEOMETRY, and
        `claimants()` is only the first of four conditions:

          1. no OTHER live row's reservation intersects the annexed range
             (`claimants`, which already uses reservations rather than sizes);
          2. the grown extent lies wholly inside EOF -- `datalloc._place` refuses
             the same overhang at `datalloc.py:374-380`, and `datcheck` rule 5
             will not catch it because it tests `offset + size`, not the rounded
             reservation. `put()`'s short-read guard catches it AFTER the
             decision, which is a crash rather than a refusal;
          3. the grown extent does not overlap the LIVE MFT, checked against the
             header's own `mft_offset`/`mft_size` and NOT via row 3. On
             `dat_study` row 3's offset and size happen to equal the MFT's, so
             `claimants` sees it -- but nothing enforces that, the client
             relocates the table during play, and `datplan.free_runs` protects
             it with an explicit bitmap rather than by trusting a row;
          4. no annexed block falls inside a `datplan.classify_runs` exclusion --
             the container/MFT-shadow rotation region. This is NEW CAPABILITY
             rather than preserved capability, and it is the single largest new
             risk in the grow verb: `replace()` never needed it because it never
             allocated. `datmove.py:22-28` states in one paragraph why this must
             consult `classify_runs` and not `free_runs`: "unallocated" counts
             the client's live container generations as free space, 89.6% of the
             gap measure on this machine's study copy.

        `datplan` is imported HERE rather than at module level, and that is the
        same decision `reservation_for`'s docstring records: this module is the
        one that must keep working when the rest of the tree does not, and
        `datmove` imports `datwrite`, so a module-level import would also be
        circular. Only the grow path pays for it.

        EVERY REFUSAL HERE IS A `GrowGateRefused`, which is a `SystemExit` with
        a `condition` on it. The type is the change and the LOGIC IS NOT: the
        four tests, their order and their four sentences are byte-for-byte what
        they were. What it buys is a caller that can tell "another row took
        these blocks" from "these bytes are not what you declared" without
        reading English -- see the class, and `deploy.grow_gate_refusal`, which
        was joining on four fixed fragments of the sentences below and would
        have gone silently unrecognising the day one of them was reworded.

        A KNOWN LIMIT, stated rather than engineered around: all four conditions
        read `self.ar`, the snapshot taken in `__init__`, so a Writer that has
        already written in this run judges the grow against the pre-run table.
        Every caller here runs the gate before its own first `put()`, and
        `claimants` has always had the same property.
        """
        block = self.ar.block_size
        lo, hi = e.offset + cur_res, e.offset + want_res

        taken = claimants(self.ar, lo, hi, exclude=row)
        if taken:
            raise GrowGateRefused(
                "claimants",
                f"row {row} needs to grow from {cur_res} to {want_res} B in "
                f"place, and [0x{lo:X}, 0x{hi:X}) is CLAIMED by "
                + ", ".join(f"row {i} (0x{o:X}..0x{h:X})"
                            for o, h, i in taken) + ".\n"
                f"  The blocks this row freed have been taken since. That is "
                f"a relocation, not an in-place restore -- use datmove.py, "
                f"which finds a free run and rewrites the offset.")

        filesize = os.path.getsize(self.path)
        if hi > filesize:
            raise GrowGateRefused(
                "eof",
                f"row {row} would grow to [0x{e.offset:X}, 0x{hi:X}), which "
                f"runs {hi - filesize} B PAST THE END of a {filesize} B "
                f"archive.\n"
                f"  Nothing here grows the file: the journal has no way to "
                f"express a truncation, so a growth that failed could not be "
                f"undone. datcheck's rule 5 would not catch this either -- it "
                f"tests offset + size, not the rounded reservation.")

        mlo, mhi = self.ar.mft_offset, self.ar.mft_offset + self.ar.mft_size
        if lo < mhi and mlo < hi:
            raise GrowGateRefused(
                "live-mft",
                f"row {row} would grow into the LIVE MASTER FILE TABLE: "
                f"[0x{lo:X}, 0x{hi:X}) overlaps [0x{mlo:X}, 0x{mhi:X}).\n"
                f"  Checked against the file header's own mft_offset/mft_size, "
                f"not against row 3 -- row 3 describes the table on the copies "
                f"we have measured, but nothing enforces that and the client "
                f"relocates the table during ordinary play.")

        import datplan
        _usable, excluded = datplan.classify_runs(self.ar)
        for ex in excluded:
            xlo = ex.start_block * block
            xhi = xlo + ex.blocks * block
            if lo < xhi and xlo < hi:
                raise GrowGateRefused(
                    "withheld-run",
                    f"row {row} would grow into blocks datplan WITHHOLDS: "
                    f"[0x{lo:X}, 0x{hi:X}) overlaps the free run at "
                    f"[0x{xlo:X}, 0x{xhi:X}), which carries "
                    + ex.why() + ".\n"
                    f"  Those blocks read as unallocated because no MFT row "
                    f"points at them, and they are not free: they are a "
                    f"container generation the client is about to rotate back "
                    f"onto. A run is withheld WHOLE, never carved around.")

        print(f"  reclaiming [0x{lo:X}, 0x{hi:X}) = {hi - lo} B, "
              f"0 other rows claim it")

    def replace(self, row, new, *, compression=COMPRESSION_STORED, expect=None,
                stored_lookalike_ok=False, grow_to=None):
        """Put different bytes, of a different length, in an existing row.

        THE COMPRESSION CODE IS AN ARGUMENT, and its default reproduces this
        verb's behaviour byte for byte from the day it was written. Every caller
        in the tree -- `iconset`, `rebloat`, `textwrite`, the `--replace` CLI --
        hands plaintext and relies on "it marks the row stored", and so do the
        six staging scripts under `vault/research/archivewrite/` that nothing in
        this tree can re-derive. None of them is edited and none of them changes
        behaviour.

        WHAT compression=8 ADDS, and why it needed a rung of its own. Until
        2026-08-18 nothing in this project could produce compression-8 bytes, so
        the field was hardcoded to 0 (its own docstring said so, and `restore`'s
        first bullet still explains why that made a donor archive the only way to
        put a compressed row back). `gwenc.py` produces them now. Marking a row
        compression 8 is four writes and three of them are the same three this
        verb already did -- the difference is entirely in what can go wrong.

        THE VERIFY-BEFORE-COMMIT ARM. `expect` is the payload a reader must get
        back, and for a compressed write it is MANDATORY. The bytes are
        decompressed and compared against it before the first byte reaches the
        archive; a mismatch is a loud refusal at the call site and nothing is
        written. That is not belt-and-braces, it is the only refutation that
        exists: the entry CRC is over the STORED bytes, so a compression-8 row
        holding a wrong payload passes all three checksum rules and all ten of
        `datcheck --preflight`'s open-time rules, and `datcheck.py` has no notion
        of a compression code at all. See `declaration_fault`, which also states
        plainly what this CANNOT catch -- the round trip is through our own
        decoder, and only the client can settle that.

        The one thing this will not do is relocate. Space is reserved in whole
        512-byte blocks, so a row owns ceil(size/512)*512 bytes whatever its
        size field says; anything that fits there can be written without moving
        a byte of anyone else's data. Anything that does not fit is a
        relocation, which is a different and much more dangerous operation, and
        this refuses it rather than half-doing it.

        `grow_to` IS THE GROW-BACK, and it exists because the sentence above used
        to be enforced against the row's CURRENT size, which is not a statement
        about how much space the row may use. After any shrink the row's own
        freed blocks became unreachable to this verb: REPRODUCED on the test
        fixture (row 4, 1000 B -> 100 B, and the original 1000 B refused as "a
        relocation" with 1,024 B of the row's own extent standing free and
        claimed by nobody), and priced on the real archive (row 11196 shrunk to
        4 KB loses 1,025,536 B of its own space). That is fatal for the authoring
        loop this arc is about -- iterate the encoder, rewrite the row -- because
        the second, larger output onto a row the first write shrank is exactly
        the case. `restore()` is a grow today and can only ever write a DONOR's
        bytes (`Writer.restore(self, row, donor, confirm)` takes no payload), so
        it is an undo, not a workaround.

          * `grow_to=None`, the default, is byte-for-byte the old behaviour and
            every caller in the tree and the vault is on it. When the payload
            fits the current reservation NO new check runs at all.
          * `grow_to=N` is the caller STATING the reservation it believes the
            row is entitled to. The ceiling becomes
            `reservation_for(max(e.size, N), block)` and the grow must then clear
            `_grow_gate` -- claimants, EOF, the live MFT, and datplan's withheld
            container runs.

        A GREEDY "TAKE EVERYTHING GEOMETRY ALLOWS" DEFAULT IS REJECTED, and the
        argument is one line: `claimants()` computes each NEIGHBOUR's reservation
        from that neighbour's current size too, so a shrunk neighbour's claim is
        under-computed by exactly the same defect. Geometry cannot distinguish a
        free block from a shrunk neighbour's freed-but-wanted-back block. A verb
        whose default silently annexes free space is an allocator wearing
        `replace()`'s name; `grow_to` makes the annexation something a caller
        said out loud. `read_donor` already produces the number
        (`DonorRow.size`), and a caller holding its own journal has it in the
        `before` length.

        THE ONE HAZARD OF A GROW, stated rather than engineered around, exactly
        as `restore()` states it: the payload write covers the whole new
        reservation and lands BEFORE the size field moves, so an interrupted run
        leaves the row's size describing the old length over the new bytes.
        `datmove` avoids this by writing to a new location first; an in-place
        grow has nowhere else to put them. The journal is the way back and it is
        written, and fsynced, before the first byte.

        Writes four things: the payload, the size field, the compression field
        and the crc. Getting three of four right looks exactly like a malformed
        payload from the client's side, which is why they are done together.

        THE WHOLE RESERVATION IS WRITTEN, not just the payload. That costs a
        multi-megabyte write on a big row and it is not optional, because a
        SHRINKING replace has two hazards that a payload-sized write cannot
        address and that no checksum can catch:

          * The journal would record only what was written. put() reads
            len(data) as its `before`, so replacing a 1.96 MB row with 20 KB
            captured 20 KB of history and no more. The client rederives its free
            list from the entry table at every open, and it is OBSERVED
            relocating and resizing live rows during ordinary play -- 8315 moved
            and grew 92 -> 96 bytes, 8316 moved, in one caged session
            (studies/datwrite/FINDINGS.md section 6). That study narrows it
            honestly: relocation has only ever been watched on the client's own
            scratch rows, never on a content row. It does not narrow it to safe.
            The blocks a shrink frees are blocks the allocator may take, and if
            it does, --revert puts back the first 20 KB, prints "restored",
            leaves all three checksum rules verifying, and the original payload
            is gone with nothing anywhere reporting a loss.
          * The old payload's tail would still be sitting inside this row's own
            reservation, immediately after the authored bytes. Whether any reader
            scans past the size field is UNTESTED, so the honest move is to leave
            nothing there to find.

        One journalled write settles both, and it is the only form in which the
        journal's `after` field can be told the truth: the reservation ends up
        holding exactly the payload followed by zeros, which is knowable before
        the write, so `before` and `after` describe the same range and --revert's
        "the client wrote here" detector covers the whole of it rather than the
        first few kilobytes.

        The tail is ours to write. Every entry offset is block-aligned and no
        extent runs into the next (test_datcrc.py sections 2 and 3), so the next
        row cannot begin before offset + reservation. Past the end of the file it
        is put()'s short-read guard that refuses, not this.
        """
        new = bytes(new)
        e = self.ar.row(row)
        block = self.ar.block_size
        # `reservation_for`, not a fourth inline copy of its expression. The
        # value is identical; what changes is that this verb now spells the
        # concept through the module's single definition of it.
        cur_res = reservation_for(e.size, block)
        want_res = reservation_for(len(new), block)
        reserved, annexed = cur_res, 0
        if want_res > cur_res:
            if grow_to is None:
                # THE REFUSAL NAMES THE REMEDY THAT FITS THE CASE. "Pick a row
                # with a bigger reservation" is advice for an authoring caller
                # who has outgrown a PRISTINE row. For a grow-back the blocks are
                # right there, claimed by nobody, and a free-run list will not
                # contain them as a candidate for this row -- so the reader is
                # sent somewhere that cannot help. Which sentence follows is
                # decided by the geometry, not by a guess.
                free = not claimants(self.ar, e.offset + cur_res,
                                     e.offset + want_res, exclude=row)
                remedy = (
                    f"Those blocks are claimed by NOBODY: if this row was "
                    f"shrunk and you are putting its own space back, say so "
                    f"with grow_to={len(new)} (--grow-to {len(new)}), which "
                    f"runs the full grow gate -- claimants, EOF, the live MFT "
                    f"and datplan's withheld container runs."
                    if free else
                    "Pick a row with a bigger reservation -- datplan.py --free "
                    "lists them.")
                raise SystemExit(
                    f"row {row} reserves {cur_res} bytes ({e.size} used, "
                    f"{block}-byte blocks) and the new payload is {len(new)}. "
                    f"That is a relocation, not a replacement. " + remedy)
            # max(e.size, grow_to): a stated entitlement BELOW what the row
            # already holds is not a shrink request, it is a caller reading the
            # wrong number, and the ceiling must not fall under the row's own
            # current reservation just because it was passed one.
            stated = reservation_for(max(e.size, grow_to), block)
            if want_res > stated:
                raise SystemExit(
                    f"row {row} was declared entitled to {grow_to} B "
                    f"(reservation {stated}) and the new payload is "
                    f"{len(new)} B (reservation {want_res}). A grow_to is a "
                    f"statement about what this row was GIVEN, not a request "
                    f"for more; raise it only from a donor's size or a "
                    f"journal's `before` length, never to make a write fit.")
            self._grow_gate(row, e, cur_res, want_res)
            reserved, annexed = want_res, want_res - cur_res
        # BEFORE THE FIRST put(). Every refusal in here has to land while the
        # archive is still untouched and no journal exists, because after the
        # write there is nothing left that can tell the difference -- see
        # `declaration_fault`.
        fault = declaration_fault(new, compression, expect, stored_lookalike_ok)
        if stored_lookalike_ok and looks_compressed(new):
            # An override that leaves no trace is the same defect as no override.
            print(f"  !! C-6 OVERRIDE TAKEN on row {row}: these bytes DECODE as a "
                  f"compression-8 stream and are being written as compression "
                  f"{compression} anyway. If that is wrong, the archive will be "
                  f"green and the file unreadable, and nothing we own can detect "
                  f"it afterwards. FINDINGS C-6.")
        if fault:
            raise SystemExit(
                f"REFUSED: will not write row {row} as compression "
                f"{compression}.\n  {fault}")
        image = new + b"\x00" * (reserved - len(new))
        print(f"replacing row {row}: {e.size} -> {len(new)} bytes, "
              f"compression {e.compression} -> {compression}, at 0x{e.offset:X} "
              f"(reservation {reserved}, {reserved - len(new)} B of tail zeroed)")
        if compression == COMPRESSION_HUFFMAN:
            print(f"  verified before writing: {len(new)} B decompress to the "
                  f"{len(bytes(expect))} B declared (our decoder; only the "
                  f"client can settle the rest)")
        # THE `what` STRING NAMES THE ANNEXATION AND ITS RANGE. `before` and
        # `after` already describe the whole NEW reservation, which is what lets
        # --revert put the annexed region back and what makes revert's "the
        # client wrote here" detector cover it rather than stopping at the old
        # reservation. `what` is free text and revert() prints it, so no journal
        # schema moves -- 59 existing journals under vault/ parse on these keys.
        what = (f"row {row} reservation ({reserved} B)" if not annexed else
                f"row {row} reservation ({cur_res} -> {want_res} B, annexing "
                f"[0x{e.offset + cur_res:X},0x{e.offset + want_res:X}))")
        self.put(e.offset, image, what)
        self.put(row_offset(self.ar, row) + ENTRY_SIZE_OFF,
                 struct.pack("<I", len(new)),
                 f"MFT row {row} size {e.size} -> {len(new)}")
        if e.compression != compression:
            self.put(row_offset(self.ar, row) + ENTRY_COMP_OFF,
                     struct.pack("<H", compression),
                     f"MFT row {row} compression {e.compression} -> "
                     f"{compression}")
        self.set_entry_crc(row, binascii.crc32(new))
        self.fix_mft_self_crc()

        if annexed:
            # TWO POST-WRITE ASSERTIONS THE ARTIFACT CAN REFUTE, and both are on
            # the grow path only because a grow is the first thing this verb can
            # do that CREATES an overlap. `datalloc.py:1127-1134` says it in as
            # many words: datmove runs `overlaps` after every move and no other
            # writer runs it at all.
            self.resync(f"row {row} grew {cur_res} -> {want_res} B")
            import datmove
            bad = datmove.overlaps(self.ar)
            if bad:
                raise SystemExit(
                    f"GROW VERIFY FAILED on row {row}: two rows now share "
                    f"blocks -- "
                    + ", ".join(f"rows {a} and {b} at 0x{o:X}"
                                for a, b, o in bad) + ".\n"
                    f"  No checksum can see this: each crc covers only its own "
                    f"row's bytes. Revert with the journal and do not use this "
                    f"archive.")
            # Read back through the WRITE handle, never through self.ar -- the
            # Archive's buffered read-only handle can answer a seek from a
            # pre-write window. Same trap read_mft() documents, same discipline
            # restore() follows.
            self.fh.seek(e.offset)
            got = self.fh.read(len(new))
            if got != new:
                raise SystemExit(
                    f"GROW VERIFY FAILED on row {row}: the {len(new)} B on disk "
                    f"are not the payload that was written. Revert with the "
                    f"journal and do not use this archive.")
            print(f"  verified: {len(new)} B read back sha256 "
                  f"{hashlib.sha256(got).hexdigest()[:16]}, {annexed} B "
                  f"annexed, no two rows share a block")

    def restore(self, row, donor, confirm=False):
        """Put a row back to what a DONOR archive says it should hold.

        THE VERB `datmove.plan_move` NAMES AND REFUSES. Its docstring ends
        "Free a run elsewhere, or write the in-place grow as its own verb with
        its own test"; this is that verb, narrowed to the case where the bytes
        come from another copy of the same archive rather than from a caller.

        WHY --replace CANNOT DO THIS, which is the whole reason it exists:

          * `--replace` writes COMPRESSION 0. An ArenaNet row is usually
            compression 8, and there is no compressor here. This copies the
            donor's STORED bytes verbatim, so the codec is never involved and
            the compression field is restored rather than flattened.
          * `--replace` writes bytes a CALLER hands it and this writes a DONOR's,
            which is the difference that survives 2026-08-19. `--replace` used to
            compute its reservation from the row's CURRENT size, so a shrunk row
            could never be grown back by that path either -- 2,068 B gives it
            2,560 B of reservation when its original needs 7,680; it now takes
            `grow_to`, states the entitlement, and runs the SAME gate this does.
            What it still cannot do is know what the original was, which is what
            a donor archive is for.
          * `--overwrite` is same-length only.

        THE GROW GATE IS NOW SHARED, `Writer._grow_gate`, and this verb GAINED
        three conditions by the factoring: an EOF bound, a live-MFT check made
        against the file header rather than against row 3, and `classify_runs`'s
        withheld container runs. This gate was `claimants()` alone from the day
        it was written, and `restore()` is the verb that has already been run on
        real 4.2 GB copies -- so those were live gaps, not hypothetical ones.

        AND WHY A JOURNAL IS NOT ENOUGH, which is why the donor is an archive and
        not a `--data` file. `--revert` is the documented way back and it stops
        working for two independent reasons: the client moves the MFT, so MFT
        edits replay into dead space (see `Journal`), and a journal is a file
        somebody has to still have. MEASURED 2026-08-14: three skill-icon rows
        were left armed in `vault/run/reskin-roster/Gw.dat` on the recorded
        understanding that their payloads were "still recoverable from the
        journals' `before` fields", and **no journal for those rows exists in
        the vault**. A pristine copy is a better source than a journal because
        every checkout has one and it cannot go missing without the loss being
        obvious.

        IDENTITY IS BY FILE ID, never by row, because a row index is a fact about
        the copy (`mapchunks.py`:117). If both rows are file-id addressable the
        id sets must intersect or this refuses; a donor from a different build
        where row N is a different file is exactly what that catches.

        THE ONE HAZARD, stated rather than engineered around: an in-place grow
        overwrites the current payload before the size field moves, so an
        interrupted run leaves the row's size describing the old length over the
        new bytes. `datmove` avoids this by writing to a new location first; an
        in-place grow has nowhere else to put them. The journal is the way back
        and it is written before the first byte.
        """
        e = self.ar.row(row)
        block = self.ar.block_size
        old_res = reservation_for(e.size, block)
        new_res = reservation_for(donor.size, block)

        if donor.size == 0:
            raise SystemExit(f"donor row {row} is empty; there is nothing to "
                             f"restore from {donor.path}")
        if e.crc == donor.crc and e.size == donor.size \
                and e.compression == donor.compression:
            print(f"row {row} already matches the donor "
                  f"({donor.size} B, comp {donor.compression}, "
                  f"crc 0x{donor.crc:08X}) -- nothing to do")
            return False

        if new_res > old_res:
            self._grow_gate(row, e, old_res, new_res)

        if not confirm:
            raise SystemExit(
                f"would restore row {row} from {donor.path}:\n"
                f"    {e.size} B comp {e.compression} crc 0x{e.crc:08X}\n"
                f" -> {donor.size} B comp {donor.compression} "
                f"crc 0x{donor.crc:08X}\n"
                f"    reservation {old_res} -> {new_res} B at 0x{e.offset:X}\n"
                f"  Re-run with --confirm. This overwrites the current payload "
                f"before the size field moves; the journal is the way back.")

        image = donor.image
        print(f"restoring row {row} from {donor.path}: {e.size} -> {donor.size} "
              f"bytes, compression {e.compression} -> {donor.compression}, at "
              f"0x{e.offset:X} (reservation {old_res} -> {new_res})")
        self.put(e.offset, image, f"row {row} reservation ({new_res} B)")
        if e.size != donor.size:
            self.put(row_offset(self.ar, row) + ENTRY_SIZE_OFF,
                     struct.pack("<I", donor.size),
                     f"MFT row {row} size {e.size} -> {donor.size}")
        if e.compression != donor.compression:
            self.put(row_offset(self.ar, row) + ENTRY_COMP_OFF,
                     struct.pack("<H", donor.compression),
                     f"MFT row {row} compression {e.compression} -> "
                     f"{donor.compression}")
        self.set_entry_crc(row, donor.crc)
        self.fix_mft_self_crc()

        # READ BACK THROUGH THE WRITE HANDLE, never through self.ar -- the
        # Archive's buffered read-only handle was opened before any of this and
        # can answer from a pre-write window. Same trap read_mft() documents.
        self.fh.seek(e.offset)
        got = self.fh.read(donor.size)
        if hashlib.sha256(got).hexdigest() != donor.sha256:
            raise SystemExit(
                f"RESTORE VERIFY FAILED on row {row}: the bytes on disk are not "
                f"the donor's. Revert with the journal and do not use this "
                f"archive.")
        print(f"  verified: {donor.size} B read back sha256 {donor.sha256[:16]}")
        return True

    def relink_plain(self, plain_id, confirm=False):
        """Re-link a bit-31 renamed file id back to its PLAIN spelling, in place.

        `FcArchive` renames a row to `id | 0x80000000` when it has requested a
        replacement, and the plain id genuinely stops resolving until
        `DnArchive` installs one and re-links it (studies/maprows/FINDINGS.md
        section 8 -- the lookup is an exact 32-bit compare, no masking). On a
        caged loopback copy no replacement is ever coming: the cage has no file
        server and the updater is dead, so a copy caught mid-replacement stays
        that way forever and every id it renamed is a map the client cannot
        load. `contentids.preflight` refuses to launch at exactly that state.

        This is the DnArchive step with no download. The original row is still
        intact under the renamed spelling, so re-linking the plain id to THAT
        row restores exactly what the rename suspended: ONE dword changes in
        the file-id table (entry 2), and the row, its bytes and its crc are
        untouched. The directory invariant holds on both sides -- the row keeps
        a file-id record throughout, and no record is orphaned.

        The argument is the PLAIN id, the one that should start resolving.

        An interrupted run leaves entry 2's crc stale over the patched table,
        which the client detects at open ("Repairing corrupt archive"); the
        journal is the way back, and the write order puts the payload dword
        first so the journal always covers it.
        """
        if plain_id & FILE_ID_HIGH_BIT:
            raise SystemExit(
                f"--relink-plain takes the PLAIN id, and 0x{plain_id:X} has "
                f"bit 31 set. The plain spelling is 0x{plain_id & ~FILE_ID_HIGH_BIT:X}"
                f" -- pass that: the renamed form is what gets REPLACED, not "
                f"what gets linked.")
        if plain_id == 0:
            raise SystemExit("file id 0 is never valid input -- FcArchive's own "
                             "assert is `(int) fileId > 0`.")
        renamed = plain_id | FILE_ID_HIGH_BIT

        e2 = self.ar.row(FILE_ID_TABLE_ROW)
        if e2.compression != 0 or e2.size % 8:
            raise SystemExit(
                f"entry {FILE_ID_TABLE_ROW} does not look like the file-id "
                f"table ({e2.size} B, compression {e2.compression}); refusing "
                f"to edit a table I cannot read whole.")
        self.fh.seek(e2.offset)
        table = bytearray(self.fh.read(e2.size))
        if len(table) != e2.size:
            raise SystemExit(f"short read of the file-id table: "
                             f"{len(table)} of {e2.size} bytes")

        plain_slots, renamed_slots = [], []
        for i in range(len(table) // 8):
            fid, row = struct.unpack_from("<II", table, i * 8)
            if fid == plain_id:
                plain_slots.append((i, row))
            elif fid == renamed:
                renamed_slots.append((i, row))

        if plain_slots:
            also = (f" (the renamed 0x{renamed:X} is ALSO present, which is a "
                    f"state this tool must not have created -- look before "
                    f"touching anything)" if renamed_slots else "")
            raise SystemExit(
                f"0x{plain_id:X} already binds, to row "
                f"{plain_slots[0][1]}{also}. Nothing to relink.")
        if not renamed_slots:
            raise SystemExit(
                f"neither 0x{plain_id:X} nor 0x{renamed:X} is in this "
                f"archive's file-id table. There is no rename to undo.")
        if len(renamed_slots) > 1:
            raise SystemExit(
                f"0x{renamed:X} appears in {len(renamed_slots)} table slots "
                f"({', '.join(str(s) for s, _ in renamed_slots)}). Nothing "
                f"says that cannot happen, but nothing here knows what it "
                f"means either. Refusing.")

        slot, row = renamed_slots[0]
        try:
            e = self.ar.row(row)
        except Exception as exc:                              # noqa: BLE001
            raise SystemExit(
                f"0x{renamed:X} names row {row}, which this archive cannot "
                f"read ({type(exc).__name__}: {exc}). Re-linking the plain id "
                f"would make a broken row addressable.")
        if e.flags & 3 != 3:
            raise SystemExit(
                f"row {row} has flags {e.flags} -- not USED|FIRST_STREAM. A "
                f"file-id record must name a first-stream row (the directory "
                f"invariant, studies/customarea/FINDINGS.md 18.5 Tier 2).")
        if e.size == 0:
            raise SystemExit(
                f"row {row} is zero-length; re-linking would make an id "
                f"resolve to nothing and hand the client the re-bloat path.")
        if e.crc:
            self.fh.seek(e.offset)
            stored = self.fh.read(e.size)
            got = binascii.crc32(stored)
            if got != e.crc:
                raise SystemExit(
                    f"row {row} FAILS ITS OWN CRC (stored 0x{e.crc:08X}, "
                    f"computed 0x{got:08X}). Refusing to make a corrupt row "
                    f"addressable.")
            crc_note = f"crc verified 0x{e.crc:08X}"
        else:
            crc_note = "crc 0 (the archive's own check is disabled for it)"

        print(f"relink 0x{renamed:X} -> 0x{plain_id:X}, table slot {slot}, "
              f"row {row}: {e.size:,} B, flags {e.flags}, {crc_note}")
        if not confirm:
            raise SystemExit(
                f"would rewrite one dword of the file-id table at "
                f"0x{e2.offset + slot * 8:X}, then entry {FILE_ID_TABLE_ROW}'s "
                f"crc and the MFT self-crc. The row's own bytes are not "
                f"touched.\n  Re-run with --confirm.")

        struct.pack_into("<I", table, slot * 8, plain_id)
        self.put(e2.offset + slot * 8, struct.pack("<I", plain_id),
                 f"file-id table slot {slot}: 0x{renamed:X} -> 0x{plain_id:X} "
                 f"(row {row})")
        self.set_entry_crc(FILE_ID_TABLE_ROW, binascii.crc32(bytes(table)))
        self.fix_mft_self_crc()

        # Read back through the write handle -- same trap read_mft() documents.
        self.fh.seek(e2.offset)
        got = self.fh.read(e2.size)
        if got != bytes(table):
            raise SystemExit(
                f"RELINK VERIFY FAILED: the file-id table on disk is not what "
                f"was written. Revert with the journal and do not use this "
                f"archive.")
        print(f"  verified: 0x{plain_id:X} now binds row {row}")
        return True

    def fix_mft_self_crc(self):
        """Recompute row 3's crc from the table as it now stands on disk.

        Call this after every MFT change, or the table no longer describes
        itself and we have run a different experiment than the one we meant to.

        REFUSES on a stale view rather than computing a wrong crc. `self.ar` is
        a snapshot taken in `__init__`, and a caller that grows the table without
        calling `resync()` would otherwise get a crc over the pre-growth extent
        -- silently, and with datcheck still reporting 10 of 10. The check is the
        cheapest one available and it is an equality the artifact can refute: the
        descriptor's own count word, re-read from disk right now, against the
        count this object thinks it has. A check that cannot fail is not a check;
        this one fails on exactly the mistake it was written for.
        """
        self.fh.seek(self.ar.mft_offset)
        head = self.fh.read(ENTRY_SIZE)
        on_disk = struct.unpack_from("<I", head, MFT_HDR_COUNT)[0]
        if on_disk != self.ar.entry_count:
            raise SystemExit(
                f"refusing to compute the MFT self-crc from a stale view of the "
                f"table.\n"
                f"  this Writer was opened when the table held "
                f"{self.ar.entry_count} entries\n"
                f"  the descriptor on disk now says {on_disk}\n"
                f"The crc would be computed over "
                f"{self.ar.entry_count * ENTRY_SIZE} bytes instead of "
                f"{on_disk * ENTRY_SIZE}, and the archive would fail its own "
                f"self-checksum while this printed a confident before/after. "
                f"Call Writer.resync() after growing the table.")
        mft = self.read_mft()
        want = mft_self_crc(mft, self.ar.entry_count)
        have = struct.unpack_from("<I", mft, SELF_ROW_START + ENTRY_CRC)[0]
        if want == have:
            print(f"  MFT self-crc already correct (0x{want:08X})")
            return want
        self.put(row_offset(self.ar, MFT_SELF_ROW) + ENTRY_CRC,
                 struct.pack("<I", want),
                 f"MFT self-crc 0x{have:08X} -> 0x{want:08X}")
        return want


def verify(path):
    """All three rules against one archive, right now. Returns a failure count."""
    bad = 0
    with Archive(path) as ar:
        ar.fh.seek(0)
        head = ar.fh.read(32)
        stored = struct.unpack_from("<I", head, HDR_CRC)[0]
        want = binascii.crc32(head[:12])
        ok = stored == want
        bad += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] file header crc  "
              f"stored 0x{stored:08X} computed 0x{want:08X}")

        mft = read_mft(ar)
        stored = struct.unpack_from("<I", mft, SELF_ROW_START + ENTRY_CRC)[0]
        want = mft_self_crc(mft, ar.entry_count)
        ok = stored == want
        bad += not ok
        print(f"  [{'PASS' if ok else 'FAIL'}] MFT self-crc      "
              f"stored 0x{stored:08X} computed 0x{want:08X}")
    return bad


def check_rows(path, rows):
    """The entry crc of specific rows, over their stored bytes."""
    bad = 0
    with Archive(path) as ar:
        for row in rows:
            e = ar.row(row)
            want = binascii.crc32(ar.raw(e))
            ok = want == e.crc
            bad += not ok
            print(f"  [{'PASS' if ok else 'FAIL'}] row {row:<7} crc      "
                  f"stored 0x{e.crc:08X} computed 0x{want:08X}  "
                  f"({e.size} B, comp={e.compression}, flags={e.flags})")
    return bad


# Moved to `datjournal.py` on 2026-09-11 with `Journal`; re-exported here
# because `revert()` below calls it as a bare name and `deploy.py:1508` reads it
# off this module.
from datjournal import read_journal  # noqa: F401,E402


def revert(journal_path, force=False):
    """Undo every edit in a journal, newest first.

    Returns 0 on a complete replay and NON-ZERO when the journal was torn and
    only part of it could be read. Both are printed; neither is a traceback.
    """
    doc, dropped = read_journal(journal_path)
    path = doc["dat"]
    guard(path)
    edits = doc["edits"]
    if dropped:
        print(f"INCOMPLETE JOURNAL: {journal_path} ends in a record that was "
              f"never finished -- {dropped} byte(s) at the tail could not be "
              f"parsed and are being DROPPED.\n"
              f"  {len(edits)} complete record(s) before it WILL be replayed. "
              f"The run that wrote this was interrupted mid-record, so the "
              f"archive edit that record describes may or may not have landed; "
              f"--verify afterwards and compare against a donor. This exit code "
              f"is non-zero to say the revert is PARTIAL by construction.")
    if not edits:
        print("journal is empty; nothing to revert")
        return 1 if dropped else 0

    # See Journal's docstring: the client moves the MFT, and a stale MFT edit
    # replayed at its old address is a silent no-op that still verifies.
    was = doc.get("mft_offset")
    now = mft_offset_of(path)          # header only -- see mft_offset_of
    if was is None:
        print(f"WARNING: this journal predates MFT-offset recording. If it "
              f"contains MFT edits and the table has moved since, reverting "
              f"them writes into dead space. The MFT is at 0x{now:X} now.")
    elif was != now:
        msg = (f"The MFT has MOVED since this journal was written:\n"
               f"    journalled at 0x{was:X}\n"
               f"    archive now   0x{now:X}\n"
               f"Every MFT edit here names an address that is no longer the "
               f"table. Replaying them would write into dead space, restore "
               f"nothing, and still leave the archive verifying -- so the "
               f"failure would be invisible. Restore the affected rows' size, "
               f"compression and crc explicitly instead, then recompute the "
               f"self-crc.")
        if not force:
            raise SystemExit(msg + "\n(--force to replay anyway; payload edits "
                                   "are unaffected and safe.)")
        print("WARNING, --force given:\n" + msg)
    print(f"reverting {len(edits)} edit(s) in {path}")
    restored = 0
    with open(path, "r+b") as fh:
        for ed in reversed(edits):
            want_now = binascii.unhexlify(ed["after"])
            back = binascii.unhexlify(ed["before"])
            fh.seek(ed["offset"])
            actual = fh.read(len(back))
            if actual == back:
                print(f"  (already) 0x{ed['offset']:012X} {ed['what']}")
                continue
            if actual != want_now:
                # Something other than us changed these bytes -- most likely the
                # client itself, which is exactly what a durability test is
                # looking for. Say so loudly and put ours back anyway.
                print(f"  CHANGED   0x{ed['offset']:012X} {ed['what']}\n"
                      f"            on disk {binascii.hexlify(actual).decode()} "
                      f"is neither ours nor the original -- the client wrote here")
            fh.seek(ed["offset"])
            fh.write(back)
            restored += 1
            print(f"  restored  0x{ed['offset']:012X} +{len(back)} {ed['what']}")
        fh.flush()
        os.fsync(fh.fileno())
    print(f"{restored} range(s) restored")
    return 1 if dropped else 0


# Every flag that WRITES, named in one place. --verify short-circuits and returns
# before the Writer is ever constructed unless one of these is present, so a write
# flag missing from this tuple turns `--verify --thatflag` into "[PASS] all rules
# hold", exit 0, and nothing written at all -- a silent no-op wearing a green
# banner, which is the exact failure mode toolkit/checks.py exists to refuse.
#
# That is not hypothetical. `--replace` was absent here from the day it was added,
# and `--verify --replace ROW --data F` is the combination the documented procedure
# leads with, because verifying before writing is the obvious habit. It printed
# "[PASS] all rules hold" and did nothing, for as long as the flag existed.
#
# test_datwrite.py section 2 checks these two tuples against the parser's own
# actions, so a flag added below and forgotten here goes red instead of going quiet.
MUTATING_DESTS = ("corrupt_crc", "overwrite", "replace", "corrupt_mft_crc",
                  "restore", "relink_plain")

# The rest: reads, or arguments to something else. Listed only so the drift check
# can tell "deliberately read-only" from "somebody forgot".
#
# `grow_to` is HERE and not above, for the same reason `compression` and `expect`
# are: it writes nothing on its own, it is an argument to `--replace`, and
# `--grow-to` without `--replace` is an ap.error() in main() before anything
# opens. Putting it in MUTATING_DESTS would make `--verify --grow-to N` construct
# a Writer that has nothing to do -- the mirror of the defect the tuple above was
# written for, not another instance of it.
READONLY_DESTS = ("help", "dat", "journal", "verify", "check_rows", "data",
                  "revert", "force", "from_dat", "confirm", "compression",
                  "expect", "stored_lookalike_ok", "grow_to")


def is_mutating(args):
    """Does this run intend to write? None and False both mean 'not given'.

    Identity comparisons, not truthiness: a row number of 0 is a value, and
    `if args.corrupt_crc` would read it as absent. That is the same bug as the
    missing --replace, just waiting on a different input.
    """
    return any(v is not None and v is not False
               for v in (getattr(args, d) for d in MUTATING_DESTS))


def build_parser():
    """The command line, factored out so a test can enumerate it."""
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", help="the archive to operate on (never C:\\gw)")
    ap.add_argument("--journal", default=None,
                    help="where to record what changed (default: DAT.journal.json)")
    ap.add_argument("--verify", action="store_true",
                    help="check the header and MFT self checksums")
    ap.add_argument("--check-rows", type=int, nargs="+", metavar="ROW",
                    help="check specific entry crcs over their stored bytes")
    ap.add_argument("--corrupt-crc", type=int, metavar="ROW",
                    help="flip a row's stored crc, leaving its CONTENT untouched")
    ap.add_argument("--stored-lookalike-ok", action="store_true",
                    help="override the C-6 refusal when plaintext happens to "
                         "decode as a compression-8 stream. Deliberately "
                         "awkward: 4 of 38,621 real stored rows need it and 0 "
                         "of 1,500 decompressed retail payloads do, so if you "
                         "are reaching for it on authored content, the bytes "
                         "are probably genuinely compressed")
    ap.add_argument("--overwrite", type=int, metavar="ROW",
                    help="replace a row's stored bytes, same length, in place")
    ap.add_argument("--data", metavar="FILE",
                    help="with --overwrite, the replacement bytes")
    ap.add_argument("--replace", type=int, metavar="ROW",
                    help="replace a row's contents with a DIFFERENT-length "
                         "payload: payload, size field, compression field and "
                         "crc. Stored by default. Refuses to relocate.")
    ap.add_argument("--compression", type=int, choices=(COMPRESSION_STORED,
                                                        COMPRESSION_HUFFMAN),
                    default=COMPRESSION_STORED,
                    help="with --replace, the compression code to MARK the row "
                         "with (default 0, stored). 8 requires --expect and the "
                         "bytes are decompressed and compared against it before "
                         "anything is written.")
    ap.add_argument("--grow-to", type=int, metavar="BYTES", default=None,
                    help="with --replace, the reservation you STATE this row is "
                         "entitled to -- the size it had before something shrank "
                         "it. Without it a payload past the row's current "
                         "reservation is refused as a relocation, which is why "
                         "a row could never be grown back into its own freed "
                         "blocks. Take the number from a donor archive's size or "
                         "a journal's `before` length; the grow still has to "
                         "clear claimants, EOF, the live MFT and datplan's "
                         "withheld container runs.")
    ap.add_argument("--expect", metavar="FILE",
                    help="with --replace, the payload a reader must get back. "
                         "MANDATORY for --compression 8; for a stored write it "
                         "must equal --data, which is what makes it a statement "
                         "rather than an override.")
    ap.add_argument("--corrupt-mft-crc", action="store_true",
                    help="flip the MFT self-crc (Arm C -- expect a full rescan)")
    ap.add_argument("--restore", type=int, metavar="ROW",
                    help="put ROW back to what --from says it should hold, "
                         "compression and all. Grows in place if the blocks it "
                         "freed are still unclaimed, and refuses naming the "
                         "claimant if they are not")
    ap.add_argument("--from", dest="from_dat", metavar="DONOR",
                    help="a pristine archive to read the original from "
                         "(read-only; C:\\gw is allowed here and nowhere else)")
    ap.add_argument("--relink-plain", metavar="FILE_ID",
                    type=lambda s: int(s, 0),
                    help="re-link FILE_ID's plain spelling to the row its "
                         "bit-31 rename (FILE_ID|0x80000000) names, in place: "
                         "the DnArchive step for a copy whose replacement is "
                         "never coming. One dword of the file-id table; the "
                         "row's bytes are untouched. Plan only without "
                         "--confirm.")
    ap.add_argument("--confirm", action="store_true",
                    help="actually perform a --restore or --relink-plain; "
                         "without it the plan is printed and nothing is "
                         "written")
    ap.add_argument("--revert", metavar="JOURNAL",
                    help="undo every edit recorded in a journal")
    ap.add_argument("--force", action="store_true",
                    help="with --revert, replay MFT edits even if the "
                         "table has moved. Almost always wrong.")
    return ap


def main():
    ap = build_parser()
    args = ap.parse_args()

    if args.revert:
        return revert(args.revert, args.force)
    if not args.dat:
        ap.error("--dat is required")

    # Before the Writer, so a command that cannot run never opens the archive
    # 'r+b'. --restore without --from would otherwise reach read_donor(None) and
    # die inside the try/finally with the file already open for writing.
    if args.restore is not None and not args.from_dat:
        ap.error("--restore needs --from DONOR (a pristine archive to read the "
                 "original out of)")
    if args.from_dat is not None and args.restore is None:
        ap.error("--from is only meaningful with --restore")
    if args.replace is None and (args.expect
                                 or args.compression != COMPRESSION_STORED):
        ap.error("--compression and --expect are only meaningful with --replace")
    if args.replace is None and args.grow_to is not None:
        ap.error("--grow-to is only meaningful with --replace: it states the "
                 "reservation ONE row is entitled to, and --replace is what "
                 "names that row.")
    if args.compression == COMPRESSION_HUFFMAN and not args.expect:
        ap.error("--compression 8 needs --expect FILE: the payload a reader "
                 "must get back. Nothing can check a compressed row after the "
                 "write -- the entry crc is over the STORED bytes and datcheck "
                 "has no notion of a compression code.")

    if args.verify or args.check_rows:
        print(f"{args.dat}")
        bad = 0
        if args.verify:
            bad += verify(args.dat)
        if args.check_rows:
            bad += check_rows(args.dat, args.check_rows)
        if not is_mutating(args):
            print("\n[FAIL] %d rule(s) failed" % bad if bad else "\n[PASS] all rules hold")
            return 1 if bad else 0
        if bad:
            # Don't drop the number on the floor on the way to the Writer: this
            # archive was already failing its own checksums before we touched it,
            # and whatever the write produces afterwards will not be attributable.
            print(f"\n[WARN] {bad} rule(s) ALREADY failing before this write; "
                  f"continuing because a write flag was given")

    journal = args.journal or (args.dat + ".journal.json")
    w = Writer(args.dat, journal)
    try:
        if args.corrupt_crc is not None:
            row = args.corrupt_crc
            e = w.ar.row(row)
            print(f"corrupting the crc of row {row} "
                  f"({e.size} B, comp={e.compression}, flags={e.flags})")
            print("  content is NOT touched -- this isolates the crc as a gate")
            w.set_entry_crc(row, e.crc ^ 1)
            w.fix_mft_self_crc()

        if args.overwrite is not None:
            if not args.data:
                raise SystemExit("--overwrite needs --data")
            row = args.overwrite
            e = w.ar.row(row)
            new = open(args.data, "rb").read()
            want_overwrite = None
            if args.expect:
                with open(args.expect, "rb") as fh:
                    want_overwrite = fh.read()
            if len(new) != e.size:
                raise SystemExit(
                    f"--overwrite is same-length only: row {row} stores "
                    f"{e.size} bytes, {args.data} has {len(new)}. Changing the "
                    f"size means a size field, possibly a relocation, and a "
                    f"different experiment.")
            # `--overwrite` NEVER touches ENTRY_COMP_OFF -- the row keeps whatever
            # code it had -- so it is the one mutating verb in this file that can put
            # bytes under a compression code without ever stating one. A skeptic drove
            # C-6's MIRROR through it end to end: make a row legitimately compression 8,
            # then overwrite its stored bytes with same-length PLAINTEXT. Accepted, CRC
            # recomputed, `verify` 0 failures, preflight 10 of 10, crc sweep 0 bad --
            # and `Archive.read()` returns ZERO BYTES with no exception. Green archive,
            # unreadable file, and our own reader gives no refutation at all.
            #
            # Pre-existing rather than introduced here, but this rung's whole purpose is
            # closing that class in this module, and the sibling verb was left open
            # while it became reachable for the first time.
            fault = declaration_fault(new, e.compression, want_overwrite,
                                      args.stored_lookalike_ok)
            if fault:
                raise SystemExit(
                    f"refusing to overwrite row {row} under its existing "
                    f"compression {e.compression}: {fault}")
            print(f"overwriting row {row}: {e.size} bytes at 0x{e.offset:X} "
                  f"(compression {e.compression}, unchanged)")
            w.put(e.offset, new, f"row {row} stored bytes")
            w.set_entry_crc(row, binascii.crc32(new))
            w.fix_mft_self_crc()

        if args.replace is not None:
            if not args.data:
                raise SystemExit("--replace needs --data")
            payload = open(args.data, "rb").read()
            want = None
            if args.expect:
                with open(args.expect, "rb") as fh:
                    want = fh.read()
            w.replace(args.replace, payload,
                      compression=args.compression, expect=want,
                      stored_lookalike_ok=args.stored_lookalike_ok,
                      grow_to=args.grow_to)

        if args.restore is not None:
            row = args.restore
            donor = read_donor(args.from_dat, row)
            print(f"donor {args.from_dat} row {row}: {donor.size} B, "
                  f"compression {donor.compression}, crc 0x{donor.crc:08X}, "
                  f"sha256 {donor.sha256[:16]}")
            check_identity(args.dat, row, donor)
            w.restore(row, donor, confirm=args.confirm)

        if args.relink_plain is not None:
            w.relink_plain(args.relink_plain, confirm=args.confirm)

        if args.corrupt_mft_crc:
            # w.read_mft(), not read_mft(w.ar): combined with another write flag
            # this runs AFTER that flag's edits, and the Archive handle would hand
            # back the pre-write table -- corrupting a value that is already stale.
            mft = w.read_mft()
            have = struct.unpack_from("<I", mft, SELF_ROW_START + ENTRY_CRC)[0]
            print("corrupting the MFT self-crc -- Arm C. Expect a full rescan.")
            w.put(row_offset(w.ar, MFT_SELF_ROW) + ENTRY_CRC,
                  struct.pack("<I", have ^ 1), "MFT self-crc (deliberately wrong)")
    except GrowGateRefused as exc:
        # THE TYPED REFUSAL, CARRIED ACROSS A PROCESS BOUNDARY. `deploy.py`
        # drives this module as a subprocess, where an exception class is not
        # available and only bytes are; without this line the only thing a
        # caller could join on is the wording of the refusal itself. Printed
        # BESIDE the message and never inside it, so the refusal text stays
        # byte-for-byte what readers and greps already know, and re-raised
        # unchanged so the exit code and the message are untouched.
        print(exc.marker)
        raise
    finally:
        w.close()

    print(f"\njournal: {journal}")
    print(f"revert with:\n  python {os.path.relpath(__file__)} --revert {journal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
