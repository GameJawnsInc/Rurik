"""What this row is entitled to, what will occupy it, and what the run says.

FOUR ANSWERS ABOUT ONE ROW, in the order `main` asks them. `area_reserve` says
what the row is ENTITLED to -- the number `content/areas.toml` declares, and the
place a bad one is refused. `install_bytes` says what will actually OCCUPY it --
the compression-8 stream, measured every run rather than assumed.
`spill_stream` says where those bytes are written down beside the archive, on
the one path where they are otherwise unrecoverable. `budget_note` JUDGES the
first against the second and says which verb the install will pick.

THEY ARE ONE MODULE BECAUSE THEY ARE ONE SENTENCE. `main` runs `area_reserve`,
then `install_bytes`, then `budget_note` over a single row: `install_bytes`
PRODUCES the byte count that `budget_note` JUDGES against the reservation
`area_reserve` validated. Splitting the producer from the judge would put a
module boundary through the middle of one arithmetic comparison, and the note
that comes out of it is the line an operator reads to predict the install.

POINTERS OUT, because several comments below name things that did not move:

  * `install_partner`, `create_chain`, `verify` and `main` all STAY in
    `deploy.py`. `spill_stream`'s docstring contrasts the first two -- the
    writer's arm has to spill and the create path does not -- and
    `budget_note`'s explains why it is printed from `main` rather than folded
    into `verify`. Those four are the files to look in; none of them is here.
  * `Refused` is `deploy`'s own, from `deployrefuse.py`, for the reason that
    module's docstring gives: `test_deploy.py` §10(e2) asserts TYPE identity,
    so `area_reserve`'s two refusals must raise that class and not a new one.
  * The measured 32x32 / 64x64 / 96x96 table in `install_bytes`' docstring is
    reproduced to the byte by `mapscale.py`'s capacity ladder, which calls
    `deploy.install_bytes` -- through the re-export, so the function this
    module defines is the one that ladder measures.

Nothing here touches the archive. `install_partner` and `create_chain` do the
writing, with what these return.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import COMPRESSION_HUFFMAN, COMPRESSION_STORED  # noqa: E402
import gwenc  # noqa: E402  -- the compression-8 encoder
from deployrefuse import Refused  # noqa: E402


def area_reserve(area):
    """The area row's `reserve_bytes`, or 0. -> int

    WHERE CONTENT BECOMES A NUMBER, which is the place to refuse a bad one. The
    field is optional and absent means 0 -- every area row said that before
    WORLDMAPS-W5 and three of them still do. What it may NOT be is almost a
    number: TOML will hand back `2048.5` or `-512` as happily as `8192`, and
    both of those travel a long way before anything notices. `int()` on the
    first truncates silently, so the run would reserve 2,048 while the row says
    2,048.5; the second is falsely truthy and would print "past the -512 B this
    area declares".

    `datalloc.Stream` refuses both, but only on the CREATE path -- the install
    path never builds a Stream, so a fraction there would reach `--grow-to` as
    an argparse type error out of a subprocess. Asking here covers both
    directions and names the file the operator has to edit.
    """
    raw = area.get("reserve_bytes", 0)
    if raw is None:
        return 0
    # BOOLS BOTH WAYS. `True` is an int in Python and would sail through as a
    # 1-byte budget; refusing only that one would leave `false` meaning 0, which
    # is a second spelling of absent and one more thing to read.
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise Refused(
            f"this area's `reserve_bytes` is {raw!r}, which is not a whole "
            f"number of bytes.\n"
            f"  A reservation is counted in bytes and rounded up to whole "
            f"512-byte blocks by the allocator. Edit the row in "
            f"content/areas.toml, or drop the field to state no budget.")
    if raw < 0:
        raise Refused(
            f"this area's `reserve_bytes` is {raw}, and a negative reservation "
            f"is not a budget.\n"
            f"  Drop the field from the row in content/areas.toml to state no "
            f"budget: absent is 0, which is the behaviour every area row had "
            f"before WORLDMAPS-W5.")
    return raw


def install_bytes(blob, stored=False):
    """The bytes that will actually OCCUPY the row. -> (stream, code, note).

    RETAIL'S OWN STRIPPED PARTNERS ARE COMPRESSION 8. Ours were stored, and that
    was the deviation rather than the shape -- readable (FINDINGS 35-58 are all
    on stored partners) but not what the client is shipped. It was also the
    ceiling: `datwrite --replace` fits a payload into the row's existing
    whole-block reservation or refuses, so an authored map had to be smaller
    UNCOMPRESSED than whatever ArenaNet had compressed into the same row. That
    is what capped every map this toolkit built at 32x32.

    THE GAIN IS MEASURED, EVERY RUN, AND NEVER ASSUMED. It is not a constant of
    the format: only tag 1 of the terrain chunk is entropy-coded, and the rest of
    an authored map -- tile indices, the bit field, the two tables, props, path
    and both deps chunks -- is raw and, on a generated shape, extremely
    repetitive. MEASURED on `gen_plaza` against build 38797's donors, 2026-08-20:

        32x32   3,941 B -> 1,316 B   (33.4%)
        64x64  10,654 B -> 2,012 B   (18.9%)
        96x96  21,786 B -> 2,828 B   (13.0%)

    against map 143's 4,608 B partner reservation -- so 96x96 now REPLACES in
    place where 32x32 was previously the largest that fit at all. Those are
    figures for one generator on one donor, which is why the note is printed
    rather than the numbers being relied upon.

    `gwenc.encode` keeps its `verify=True` default: it round-trips the stream
    through `gwdat.decompress` and raises before returning if the result is not
    the input. That is the same "refuse before the archive is touched" the whole
    command is built on, and the failure it catches is silent -- a stream one
    word short decodes SHORT rather than raising, and every checksum an archive
    applies is over the stored bytes.
    """
    if stored:
        return blob, COMPRESSION_STORED, (
            f"stored install: {len(blob)} B uncompressed, no gwenc -- the shape "
            f"every map this command installed before 2026-08-20")
    stream = gwenc.encode(blob)
    return stream, COMPRESSION_HUFFMAN, (
        f"compressed install: {len(blob)} B authored -> {len(stream)} B "
        f"compression 8 ({100.0 * len(stream) / len(blob):.1f}% of stored, "
        f"{len(blob) - len(stream)} B saved)")


def spill_stream(here, tag, stream, compression):
    """Write the exact bytes the ROW will hold, beside the archive. -> path|None

    `install_partner` HAS to: `datwrite` and `datmove` take `--data FILE` and a
    compressed stream exists only in memory until something writes it down.
    `create_chain` does NOT -- it hands `datalloc` the bytes directly -- and that
    asymmetry is why this is a function rather than four lines inside the writer's
    arm. It spilled on one path and not the other, so `<area>.c8.bin` existed
    after an install and not after a create, which is backwards: THE CREATE PATH
    IS THE ONE WHERE THESE BYTES ARE OTHERWISE UNRECOVERABLE. After an install
    the row can be read back and decompressed at any time; a created chain that
    the client then rewrites, deletes or refuses leaves no copy of the stream
    `gwenc` produced from this run's blob, and a red arm in WORLDMAPS-W4 has to
    be able to point at exactly what was handed over.

    A STORED WRITE SPILLS NOTHING, on purpose. For compression 0 the stream IS
    the plain payload, already written to `<area>.bin`; a second identical file
    beside it is one more thing that can drift out of step with the first.
    """
    if compression == COMPRESSION_STORED:
        return None
    path = os.path.join(here, f"{tag}.c8.bin")
    with open(path, "wb") as fh:
        fh.write(stream)
    print(f"  wrote {path}")
    return path


def budget_note(size, reservation, reserve, created=False):
    """What a DECLARED budget does to the verb `verify` just predicted. -> str|None

    `verify` compares the stream against the row's CURRENT reservation and says
    "fits" or "will RELOCATE", which is the whole truth for a row with no
    declared entitlement. For a row that has one, the middle case exists and the
    two lines would otherwise contradict each other: the preview would announce
    a relocation and the install would grow the row back in place.

    Printed from `main` rather than folded into `verify`, deliberately. `verify`
    is about the map -- does it round-trip, does the seed stand up, does it fit
    -- and the budget is about the archive; a run that prints one line about the
    map and one about the row can be read against a prediction, where a single
    sentence hedged three ways cannot.

    `created` MIRRORS `install_partner`'S OWN GATE and defaults to False for the
    same reason it does there: a budget is only spent on a row this toolkit
    allocated. A preview that promised a grow for a displaced retail row would
    be predicting a verb the install will not pick, which is worse than saying
    nothing.
    """
    if not reserve:
        return None
    if not created:
        return (f"budget: {reserve} B declared, but this area's map row does "
                f"not carry `created = true` -- the budget is only spent on a "
                f"row this toolkit allocated, so an install here fits or "
                f"RELOCATES exactly as it did before the field existed")
    if reservation is None:
        return (f"budget: this area declares {reserve} B of reservation, which "
                f"the CREATE path will ask the allocator for")
    if size <= reservation:
        return (f"budget: {reserve} B declared, and the row's current "
                f"{reservation} B already holds this stream -- the budget is "
                f"not needed on this install")
    if size <= reserve:
        return (f"budget: {reserve} B declared, so the install will ask "
                f"datwrite to GROW the row back to its stated entitlement "
                f"rather than relocate it -- subject to the grow gate "
                f"(claimants, EOF, the live MFT, datplan's withheld runs)")
    return (f"budget: {reserve} B declared and this stream is {size} B, which "
            f"is past it -- the budget cannot help and the row RELOCATES")
