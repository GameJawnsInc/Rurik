"""The C-6 oracle -- does this blob look compressed, and does its declaration
match?

Two questions and nothing else. `looks_compressed(data)` answers the first by
DECODING; `declaration_fault(data, compression, expect)` answers the second and
returns the reason as a string rather than raising, which is why `datwrite`
(SystemExit), `datmove` (Refused), `datalloc` and `overlay` can all share one
implementation of the rule. Neither function writes, opens or mutates anything.

THE FAILURE CLASS IS studies/archivewrite/FINDINGS.md C-6: a green archive
holding an unreadable file. The long-form argument for both answers is in the
two docstrings below, verbatim from `datwrite.py`, where this code lived until
2026-09-11.

POINTER, because the text below moved and some of its references name code that
stayed behind: `replace()`, `restore()` and `reservation_for` are all
`datwrite.py`'s. `datwrite.py` re-exports `looks_compressed`,
`declaration_fault` and `HUFFMAN_PROLOGUE_BYTE` under their own names, so
`datwrite.declaration_fault` is this same object. `COMPRESSION_CODES` and
`HUFFMAN_RETAIL_MARKER` moved too and are deliberately NOT re-exported --
measured tree-wide 2026-09-11, neither has a reader outside this file.

AND THE ONE BEHAVIOURAL CONSEQUENCE OF THE MOVE, because a sabotage recipe
depends on it: `declaration_fault` calls `looks_compressed` as a bare name, so
that call now resolves in THIS module's globals. Rebinding
`datwrite.looks_compressed` still reaches `datwrite.py`'s own call site in
`Writer.replace`, but no longer reaches the one inside `declaration_fault`.
Reproducing the measured red-counts at `test_datalloc.py:108` and
`test_authorflow.py:432-436` takes rebinding `datdecl.looks_compressed` as
well; dated corrections sit at both recipe sites.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import COMPRESSION_STORED, COMPRESSION_HUFFMAN  # noqa: E402
# `archive.py` already imports `gwdat` at module level and `Archive.read()`
# dispatches compression 8 through it, so this is not a new dependency in this
# module's chain -- it is the same decoder, named directly because
# `declaration_fault` needs it BEFORE an Archive would ever see the bytes.
# `gwdat` is pure stdlib (`import struct`); the bare-machine rule holds.
import gwdat  # noqa: E402


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

    APPENDED 2026-09-11, ON THE MOVE OUT OF `datwrite.py`, because the
    paragraph above cites a constraint that belongs to a file this one no longer
    is. The docstring it names is `datwrite.reservation_for`'s
    (`datwrite.py:185-192`): it refuses to import `datmove` because `datmove`
    imports `datplan` which imports more, and `datwrite` is the module that must
    keep working when the rest of the tree does not. `datdecl` does not escape
    that constraint, it INHERITS it -- `datwrite` imports this module, so
    anything in this chain is in that one. This chain is `archive` + `gwdat`,
    both of which `datwrite` already carried before the move, so the split added
    nothing to it; and `gwenc`/`gwmatch`/`gwentropy` stay out for exactly the
    reason the paragraph above gives.
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
