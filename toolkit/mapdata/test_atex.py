"""Check `atex.py`: where `--make` may write, and what `parse()` really walks.

TWO THINGS BROUGHT THIS FILE INTO EXISTENCE and the first is the embarrassing one.

**`--make OUT` had no write guard at all.** Until 2026-08-13 it was
`with open(a.make, "wb")` reached straight off the command line, in the only
binary writer under `toolkit/mapdata/` without one -- `datwrite`, `rebloat`,
`mapbuild`, `mapexport` and `reskin` all had theirs, and two of those grew
theirs BECAUSE this class of tool had already written into the wrong tree.
`--make C:\\gw\\Gw.dat` would have truncated the owner's 4.2 GB archive to a few
kilobytes of DXT1. Section 2 is the three refusals, each with a POSITIVE
CONTROL that an ordinary scratch path is still allowed, because a guard that
refuses everything protects nothing -- the tool simply never runs, and
`reskin.py`'s first guard did exactly that, refusing the vault while its own
error message told the operator to write there.

**Section 3 is the check that would have caught the original defect**, and it is
not section 2. A guard function can exist, be documented, be greppable, and
never be CALLED -- which from the outside is identical to having no guard. So
section 3 asks the SYNTAX TREE whether every write-mode `open()` in `atex.py`
takes a path that came through `resolve_out`, and it BUILDS AND RUNS two
saboteurs made by one-line edits to the live source: the pre-fix shape
(`open(a.make, "wb")`, guard never called) and the subtler one where the guard
IS called and its result is thrown away. Both must be reported unguarded while
the real file passes.

**`atex.parse()` had no test of any kind.** Sections 4 and 5 are its first, and
the load-bearing claim is not "it parsed". `parse()` does NOT refuse a buffer
whose record walk fails to reach the end -- it returns an `Atex` with
`closes_exactly` False (section 1 pins that, because a test that only asserted
"no exception" would be measuring nothing). So the assertion is that the walk
closes to the EXACT final byte, checked by a walker written in this file out of
`int.from_bytes` that imports nothing from the module under test, and the
controls are the same walk started one byte early, one byte late, and at offset
20 -- the 20-byte header being the reading `atex.py`'s own docstring records as
REFUTED, so it is ArenaNet's bytes refusing a rival rather than our decoder
agreeing with itself. A default run peeks 11,084 MFT rows at stride 16, finds
3,238 ATEX and 106 ATTX among them, and fully parses 400 of the ATEX: **400 of
400 close at 12, and 0 of 400 close at 11, 13 or 20.**

**THE ATTX FINDING, which is the interesting one.** `parse()` raises on 106 of
106 ATTX rows and 0 of the 400 ATEX rows parsed beside them, and the asymmetry
is NOT the magic -- `parse` accepts `ATTX` at +0 and section 1 proves it by
relabelling a synthetic ATEX and watching it close. It is a trailer: an ATTX row
is an ATEX container with a `ffna` type-7 file appended, and the walk runs off
the end of the last level into `ffna` read as a u32 size (1,634,625,126, which
is where the refusal message's absurd number comes from). MEASURED here rather
than assumed:

  * the trailer is **exactly 21,923 bytes on 106 of 106** rows -- a constant
    SIZE;
  * its CONTENTS are **106 distinct sha256s**, so it is a per-texture payload of
    a fixed-size format and not one shared blob. The distinction matters and is
    asserted in both directions, because "constant trailer" read loosely would
    have been recorded as a shared constant and it is not one;
  * and cutting the trailer off leaves a container that parses and closes
    exactly, **106 of 106**. That is the claim that makes this a structural
    finding instead of a crash report.

**AND SINCE 2026-08-14 (rung T1) ATTX IS A CAPABILITY -- but `parse` STILL
REFUSES IT, and that is the design rather than an omission.** Refusing a
container whose walk does not close is what catches damage, and softening it to
accept a trailer would have cost exactly that; so the trailer is split off by a
named function, `atex.split_trailer`, and every check above survives unchanged.

The only thing that matters about that function is WHERE THE BOUNDARY COMES
FROM, and section 1b is about nothing else. It is produced by WALKING the level
records. The two obvious alternatives are built there as LIVE functions and run
on the same bytes, so the result is a difference between three answers rather
than an argument:

  * `data.find(b"ffna")` lands INSIDE level 0's payload, because a compressed
    payload is arbitrary bytes and may contain any sequence;
  * `data.rfind(b"ffna")` lands INSIDE the trailer, which is 21,923 bytes of
    chunked data and may contain it too. `rfind` is not a strawman -- it is what
    the scratch probe that scoped this arc used, and it is right on every row of
    today's corpus, which is the whole reason the fixture is built to separate
    them rather than sampled from the archive;
  * and the measured 21,923 is not used to find anything. A constant nothing
    re-derives is a landmine the day a build ships a different one, so section
    5b asserts the trailer length as a CENSUS -- `{21923: 106}`, one distinct
    value -- where a second one names both instead of reddening with no context.

Two more results earn their lines. `split_trailer` REFUSES a leftover that is
not a container it recognises, because a truncated ATEX also leaves the walk
short and without that check truncation reads as a body that closes exactly plus
a garbage trailer -- and exactly one check in this file stands there. And the
LIMIT of that refusal is asserted rather than left to be discovered: a
truncation removing a WHOLE NUMBER OF RECORDS is invisible to any walk-based
rule, since what remains is indistinguishable from a shorter mip chain. That
one first appeared as a bug in the check above it -- `[:-16]` happened to remove
exactly the final 16-byte record -- and the honest fix was to pin both
behaviours rather than pick a luckier constant.

WHICH OF THESE CHECKS ARE LOAD-BEARING WAS MEASURED, not argued. Four saboteurs
were BUILT AND RUN against a scratch copy of `toolkit/` on 2026-08-13, each one
edit deep, with the unmodified copy scoring 50/50 green (exit 0) as the control:

  A  `atex.py` as it stood at HEAD before the fix -- no guard at all, restored
     verbatim with `git show`. 4 FAILs, exit 1, and it names the write site by
     line: `open(a.make, "wb")` at 329.
  B  the guard present, documented and greppable, with only its CALL SITE
     reverted. 2 FAILs, exit 1 -- and **section 2 stays 8 of 8 green**, which
     is the whole argument for section 3 existing. A file with a perfect set of
     refusals and no call to them is a file that writes wherever it is told.
  C  `HEADER_SIZE = 20`, the refuted reading. 11 FAILs, exit 1, of which 8 are
     on ArenaNet's own bytes.
  D  a `resolve_out` that refuses EVERYTHING. 3 FAILs, exit 1, and they are
     exactly the three positive controls -- a guard nothing can get past is a
     tool nobody can run. D also found a real defect in this file's first
     version and `_out_resolved` carries the story.

Rung T1's own six saboteurs are tabulated at the floor, not here.

A MISSING VAULT IS A FAILURE, NOT A SKIP. Sections 0-3 run and score 45 without
one, against a floor of 68, so a vault-less run goes red on purpose: it has
checked the write guard and buffers this file wrote, and nothing whatever about
ArenaNet's containers, which is where every claim in `atex.py` lives.

    python toolkit/mapdata/test_atex.py               # 68 checks, ~36 s
    python toolkit/mapdata/test_atex.py --stride 48 --sample 200   # quicker
    python toolkit/mapdata/test_atex.py --all                      # every row
"""

import argparse
import ast
import collections
import hashlib
import os
import struct
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive  # noqa: E402
import atex  # noqa: E402
import checks  # noqa: E402
import gwdat  # noqa: E402
import vaultpath  # noqa: E402

MAGICS = (atex.MAGIC_ATEX, atex.MAGIC_ATTX)

# The peek stride and the parse cap a default run uses. Both are named because
# the population constants below are facts about THIS sample of THIS archive,
# and a run at another stride must not be allowed to assert them.
DEFAULT_STRIDE = 16
DEFAULT_SAMPLE = 400

# MEASURED 2026-08-13 over vault/dat_study/Gw.dat, walking `ar.entries[::16]`
# and reading each row's first 16 bytes (a partial decompression -- gwdat stops
# at `out_size`, so this costs ~5 s rather than a full 4.2 GB pass).
#
# These are population assertions, not decoration. They are what stops a broken
# peek, an empty sample or a different archive from printing "0 of 0" and going
# green, which is the failure `toolkit/checks.py` exists for.
ATEX_AT_STRIDE = 3238
ATTX_AT_STRIDE = 106

# The whole-archive figures, MEASURED 2026-08-13 by a full peek of every row
# (73.5 s). Only ASSERTED under --all, because the full parse that goes with it
# is ESTIMATED -- not measured -- at ~30 minutes from the default run's per-row
# cost, and evidence that takes half an hour is evidence nobody runs by accident.
CORPUS_ROWS = 177341
CORPUS_ATEX = 52274
CORPUS_ATTX = 1648

# The ATTX trailer. MEASURED at 21,923 bytes on 106 of 106 rows.
TRAILER_SIZE = 21923
TRAILER_MAGIC = b"ffna"
TRAILER_FFNA_TYPE = 7

# `ffna` read little-endian as the u32 the record walk mistakes it for. This is
# why the refusal message on an ATTX row quotes a 1.6-billion-byte level.
FFNA_AS_SIZE = int.from_bytes(TRAILER_MAGIC, "little")

# FLOOR: 68, MEASURED from a green default run on 2026-08-14 (--stride 16
# --sample 400; 36 s of archive work). Was 50 before rung T1 added sections 1b
# and 5b. Sections 0-3 score 45 and need no vault (was 33), so a vault-less run
# goes red on purpose.
#
# The check COUNT had to be made independent of where this file is run from.
# Section 2's checkout refusal was one check per working-tree root, which is two
# in a git worktree and one in a plain checkout -- so the floor would have been
# right here and one too high the moment the arc landed on main. It is one
# aggregate check now; see the comment there.
#
# WHICH OF RUNG T1's CHECKS ARE LOAD-BEARING WAS MEASURED, by building six
# one-edit saboteurs of `atex.py` and running this file against each in a
# scratch copy of the whole `toolkit/` tree (a PARTIAL copy is why an earlier
# sabotage harness in this project reported 0 red on all nine -- every run died
# on a missing import, which is a control that proves nothing while looking
# like it proved everything). Run at --stride 64 --sample 120, control 61/61
# green, exit 0:
#
#   A  `rfind(b"ffna")` instead of the walk            5 red
#   B  the measured 21,923 used AS the boundary        4 red
#   C  boundary off by one record header (-8)          7 red
#   D  the non-`ffna` leftover is NOT refused          1 red
#   E  `decode_rgba` does not split (the pre-rung shape) 2 red
#   F  `container_end` stops after the FIRST record    8 red
#
# D is the one worth knowing: exactly ONE check stands between this module and
# silently reporting a TRUNCATED container as a body that closes plus a garbage
# trailer. The two rival controls in 1b redden under none of the six, and that
# is correct rather than a gap -- they are assertions about the RIVALS, which
# are live functions in this file, and their job is to establish that the
# fixture separates the three answers at all.
LEDGER = checks.Ledger("test_atex", floor=68)
check = checks.adopt(LEDGER)


def guarded(fn, *a):
    """Run a section; an exception inside becomes a FAIL, not a traceback."""
    try:
        return fn(*a)
    except Exception as exc:                                 # noqa: BLE001
        check(False, f"section {fn.__name__} ran to completion",
              f"{type(exc).__name__}: {exc}")
        return None


def refuses(fn, *a, **kw):
    """True when `fn` raises ValueError rather than returning."""
    try:
        fn(*a, **kw)
    except (ValueError, struct.error):
        return True
    return False


# --------------------------------------------------------------------------
# An independent record walk. Written out of int.from_bytes, importing nothing
# from atex.py, so the header-size controls below are a second pair of eyes on
# the same bytes rather than the module agreeing with itself.
# --------------------------------------------------------------------------

def walk_from(data, base):
    """True only if 8-byte records from `base` close EXACTLY on len(data)."""
    off = base
    if off + 8 > len(data):
        return False
    while off + 8 <= len(data):
        size = int.from_bytes(data[off:off + 4], "little")
        if size <= 8:
            return False
        if off + size > len(data):
            return False
        off += size
        if off == len(data):
            return True
    return False


def walk_end(data, base=12):
    """Where the record walk stops -- the offset it could not continue past.

    On a well-formed ATEX that is len(data). On an ATTX it is the first byte of
    the trailer, which is the whole point of having this separate from
    walk_from: the failure OFFSET is the measurement, not the failure.
    """
    off = base
    while off + 8 <= len(data):
        size = int.from_bytes(data[off:off + 4], "little")
        if size <= 8 or off + size > len(data):
            return off
        off += size
        if off == len(data):
            return off
    return off


# --------------------------------------------------------------------------
# The syntax-tree question section 3 asks, and the saboteurs it asks it of.
# --------------------------------------------------------------------------

def write_opens(src, guard="resolve_out"):
    """[(lineno, rendering, guarded)] for every write-mode `open()` in `src`.

    This is asked of the AST rather than of a grep because the two things a
    grep cannot tell apart are exactly the two failures that matter: a guard
    that is defined and never called, and a guard that is called with its
    result thrown away while the raw path is opened anyway. Both leave the word
    `resolve_out` in the file.

    A path counts as guarded when it is either the guard call itself
    (`open(resolve_out(p), "wb")`) or a Name bound from the guard EARLIER in the
    file (`out = resolve_out(p)` ... `open(out, "wb")`). Anything else --
    an attribute like `a.make`, a literal, a name bound from something else --
    is reported.

    Returning the guarded sites too, rather than only the offenders, is what
    lets the caller ask whether there were any write sites AT ALL: "every write
    is guarded" is satisfied trivially by a file that never writes, and that is
    the shape of vacuity `toolkit/checks.py` exists to refuse.
    """
    tree = ast.parse(src)
    bound = {}                       # name -> lineno of `name = guard(...)`
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        val = node.value
        if not (isinstance(val, ast.Call) and isinstance(val.func, ast.Name)
                and val.func.id == guard):
            continue
        for tgt in node.targets:
            if isinstance(tgt, ast.Name):
                bound.setdefault(tgt.id, node.lineno)

    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "open"):
            continue
        mode = ""
        if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) \
                and isinstance(node.args[1].value, str):
            mode = node.args[1].value
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                mode = str(kw.value.value)
        if not any(c in mode for c in "wa+"):
            continue                                   # a read; not our problem
        if not node.args:
            out.append((node.lineno, "open() with no path argument", False))
            continue
        arg = node.args[0]
        ok = ((isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name)
               and arg.func.id == guard)
              or (isinstance(arg, ast.Name) and arg.id in bound
                  and bound[arg.id] < node.lineno))
        try:
            rendering = ast.unparse(arg)
        except Exception:                                    # noqa: BLE001
            rendering = type(arg).__name__
        out.append((node.lineno, f'open({rendering}, "{mode}")', ok))
    return out


def unguarded_write_opens(src, guard="resolve_out"):
    """Just the offenders -- empty means every write in `src` is guarded."""
    return [(ln, r) for ln, r, ok in write_opens(src, guard) if not ok]


# --------------------------------------------------------------------------
def section0():
    """The container, on bytes this file asked atex.py to write."""
    print("\n-- 0. the format, on our own bytes --")
    data = atex.build(b"DXT1", 128, 128)
    a = atex.parse(data)
    check(a.magic == atex.MAGIC_ATEX and a.fourcc == b"DXT1",
          "build() emits the ATEX magic and the fourcc asked for",
          f"{a.magic!r} {a.fourcc!r}")
    check((a.width, a.height) == (128, 128),
          "and the dimensions round-trip through the u16 pair",
          f"{a.width}x{a.height}")
    check(a.closes_exactly,
          "a built 128x128 chain closes EXACTLY on its last byte",
          f"{len(data)} bytes, {len(a.levels)} levels")
    check(len(a.levels) == atex.full_chain_levels(128, 128) == 8,
          "a full 128x128 chain is 8 levels, 128 down to 1",
          f"{len(a.levels)}")
    bad = [lv.index for lv in a.levels
           if lv.payload_size != atex.level_payload_size(b"DXT1", 128, 128,
                                                         lv.index)]
    check(not bad, "every level's payload matches the block-count formula",
          f"mismatched levels {bad}" if bad else "8 of 8")
    check(all(lv.raw for lv in a.levels),
          "and every level we author carries compression code 0",
          "code 0 is the client's raw path; nothing here is compressed")

    one = atex.parse(atex.build(b"DXTA", 64, 64, levels=1))
    check(len(one.levels) == 1 and one.closes_exactly,
          "a ONE-level file closes too -- the walk ends on the buffer, not on "
          "a mip count",
          "the client's own probe at 0x6c3050 succeeds the instant the running "
          "offset equals the length (atex.py's docstring); a 1x1 requirement "
          "would be a different format")

    ns = atex.parse(atex.build(b"DXT5", 64, 32))
    check(ns.closes_exactly and (ns.width, ns.height) == (64, 32),
          "a NON-SQUARE chain closes",
          f"{len(ns.levels)} levels -- the two dimensions halve and clamp "
          f"independently, which a square-only sample cannot refute")
    check(atex.level_dims(64, 32, 6) == (1, 1),
          "level_dims clamps at 1 rather than reaching 0",
          f"{atex.level_dims(64, 32, 6)}")

    check(refuses(atex.fill_uniform, 6, 0),
          "fill_uniform refuses a byte count that is not whole dwords",
          "its whole job is to make the planar/interleaved question "
          "unobservable, which only works dword-aligned")
    check(refuses(atex.build, b"NOPE", 16, 16),
          "build refuses a fourcc with no bits-per-pixel entry",
          "the bpp table is the client's own at VA 0xa5dd60; guessing one "
          "would author a file of the wrong length")


def section1():
    """What parse() refuses -- and the ONE thing it does not."""
    print("\n-- 1. parse refuses rather than guessing, except once --")
    good = atex.build(b"DXT1", 32, 32)
    check(refuses(atex.parse, good[:12]),
          "a buffer too short for one record is refused")
    check(refuses(atex.parse, b"DDS " + good[4:]),
          "a foreign magic is refused",
          "DDS is a real neighbour in this archive -- 223 rows of it")
    short = bytearray(good)
    struct.pack_into("<I", short, 12, 8)
    check(refuses(atex.parse, bytes(short)),
          "a level declaring a size that cannot hold its own header is refused",
          "size <= 8 would make the walk stand still or go backwards")
    over = bytearray(good)
    struct.pack_into("<I", over, 12, len(good) + 4096)
    check(refuses(atex.parse, bytes(over)),
          "a level claiming more bytes than remain is refused")

    # THE NON-REFUSAL, and it is why every real check below is on
    # closes_exactly rather than on "parse returned". A trailing fragment too
    # small to be a record simply ends the walk: parse hands back an Atex that
    # does NOT close. A test asserting "no exception" would measure nothing.
    stub = good + b"\x00\x00\x00"
    a = atex.parse(stub)
    check(a.levels and not a.closes_exactly,
          "a buffer with a trailing fragment PARSES but does not close",
          "so `parse() did not raise` is not a check; `closes_exactly` is")

    # And the control section 5 leans on: the ATTX refusal is NOT about magic.
    relabelled = atex.MAGIC_ATTX + good[4:]
    b = atex.parse(relabelled)
    check(b.magic == atex.MAGIC_ATTX and b.closes_exactly,
          "an ATTX MAGIC on an otherwise ordinary container parses and closes",
          "so when 106 real ATTX rows raise, the magic is not what did it")


def section1b():
    """WHERE THE TRAILER BOUNDARY COMES FROM -- rung T1, and its two rivals.

    Section 5 measures that real ATTX rows carry a trailer. This measures the
    only thing that matters about FINDING it: the boundary is produced by
    WALKING the level records, not by searching for the trailer's magic.

    The two rivals are the obvious implementations and both are built here as
    LIVE functions rather than described, so every number below is a difference
    between three answers to one question. They are given a container designed
    to separate them -- one that a real archive is not obliged to contain --
    because a control that happens to agree on today's corpus proves nothing
    about the one that ships next.
    """
    print("\n-- 1b. the trailer boundary is WALKED, not searched for --")

    # A rival that takes the FIRST occurrence, and one that takes the LAST.
    def split_by_find(data):
        at = data.find(atex.TRAILER_MAGIC)
        return (data, b"") if at < 0 else (data[:at], data[at:])

    def split_by_rfind(data):
        at = data.rfind(atex.TRAILER_MAGIC)
        return (data, b"") if at < 0 else (data[:at], data[at:])

    good = atex.build(b"DXT1", 32, 32)
    body = bytearray(atex.MAGIC_ATTX + good[4:])
    # A compressed level payload is arbitrary bytes and may contain ANY
    # sequence, including this one. Offset 24 is inside level 0's payload
    # (its record is size@12, code@16, payload from 20).
    body[24:28] = atex.TRAILER_MAGIC
    trailer = bytearray(atex.TRAILER_MAGIC + bytes([7]) + b"\x00" * 200)
    # ...and so may the trailer, which is 21,923 bytes of chunked data.
    trailer[100:104] = atex.TRAILER_MAGIC
    data = bytes(body) + bytes(trailer)

    end = atex.container_end(data)
    check(end == len(body),
          "the record walk lands on the trailer's first byte",
          f"{end}, and the container is {len(body)} bytes")
    # THE TWO RIVALS RUN FIRST, and the order is deliberate. They are this
    # section's only independent evidence, and they do not depend on the
    # function under test -- so putting them after it meant a broken
    # `split_trailer` RAISED, `guarded()` turned the whole section into one
    # named failure, and the controls never executed at all. MEASURED: the
    # off-by-one and first-record saboteurs took the section down that way.
    # Neither rival is a strawman -- `rfind` is what the scratch probe that
    # scoped this arc actually used, and it is right on every row of today's
    # corpus.
    fb, _ = split_by_find(data)
    rb, _ = split_by_rfind(data)
    check(len(fb) == 24 and len(fb) != len(body),
          "CONTROL: taking the FIRST `ffna` lands INSIDE level 0's payload",
          f"offset {len(fb)} against the true boundary {len(body)}")
    check(len(rb) == len(body) + 100 and len(rb) != len(body),
          "CONTROL: taking the LAST lands INSIDE the trailer",
          f"offset {len(rb)} against the true boundary {len(body)}")

    try:
        split_body, split_tail = atex.split_trailer(data)
        detail = f"{len(split_body)} + {len(split_tail)} = {len(data)}"
        halves = split_body == bytes(body) and split_tail == bytes(trailer)
    except ValueError as exc:                                  # noqa: BLE001
        split_body, halves = b"", False
        detail = f"{type(exc).__name__}: {exc}"
    check(halves, "so split_trailer recovers BOTH halves byte-for-byte", detail)
    try:
        closes = atex.parse(split_body).closes_exactly
        why = "which is the property the whole rung rests on"
    except ValueError as exc:                                  # noqa: BLE001
        closes, why = False, f"{type(exc).__name__}: {exc}"
    check(closes, "and the body it returns closes exactly", why)

    # THE NO-OP, and it is why callers may split unconditionally.
    plain_body, plain_tail = atex.split_trailer(good)
    check(plain_body == good and plain_tail == b"",
          "a plain ATEX splits to ITSELF and an empty trailer",
          "the walk closes on the last byte, so there is nothing to strip")

    # THE REFUSAL, which is what stops a truncated file being reported as a
    # body that closes plus a garbage trailer -- the failure mode a boundary
    # taken from the walk alone would have.
    check(refuses(atex.split_trailer, bytes(body)[:-6]),
          "a TRUNCATED container is refused, not silently split",
          "its leftover is level data and does not begin with `ffna`")

    # AND THE LIMIT OF THAT REFUSAL, asserted rather than left for someone to
    # discover. A truncation that removes a WHOLE NUMBER OF RECORDS is
    # invisible to any boundary rule built on the walk: the remaining records
    # still close on the last byte, so the file is indistinguishable from a
    # shorter mip chain. This first went red as a bug in the check above --
    # `[:-16]` happened to remove exactly the final 16-byte record -- and the
    # honest fix was to pin both behaviours, not to pick a luckier constant.
    last = atex.parse(bytes(body)).levels[-1]
    lopped = bytes(body)[:last.offset]
    lbody, ltail = atex.split_trailer(lopped)
    check(lbody == lopped and ltail == b"" and atex.parse(lbody).closes_exactly,
          "LIMIT: dropping a WHOLE record is NOT detectable and is not claimed "
          "to be", f"{len(lopped)} bytes still close exactly")
    try:
        got, why = atex.decode_rgba(data)[1] == 32, "the capability rung T1 " \
            "exists to add; parse() itself stays strict"
    except (ValueError, struct.error) as exc:                  # noqa: BLE001
        got, why = False, f"{type(exc).__name__}: {exc}"
    check(got, "and decode_rgba reads an ATTX end to end", why)

    # THE SECOND WITNESS, and the refusal when the two disagree. A real
    # trailer's last 12 bytes declare the head length; a walk that agreed with
    # itself and nothing else could not be refuted, and this can be.
    footed = bytes(body) + bytes(trailer[:-12]) + struct.pack(
        "<II4s", len(body), 0, atex.TRAILER_TAG)
    fb2, ft2 = atex.split_trailer(footed)
    check(atex.trailer_declared_end(ft2) == len(body) == len(fb2),
          "a trailer's footer DECLARES the head length, and it is read",
          f"declared {atex.trailer_declared_end(ft2)}")
    lying = bytes(body) + bytes(trailer[:-12]) + struct.pack(
        "<II4s", len(body) + 8, 0, atex.TRAILER_TAG)
    check(refuses(atex.split_trailer, lying),
          "and a footer DISAGREEING with the walk is refused, not resolved",
          "two witnesses disagreeing is a finding; preferring one silently "
          "is how a wrong boundary would survive")
    unfooted = bytes(body) + bytes(trailer[:-12]) + struct.pack(
        "<II4s", len(body), 0, b"____")
    check(atex.trailer_declared_end(atex.split_trailer(unfooted)[1]) is None,
          "CONTROL: a trailer with no recognisable footer declares NOTHING",
          "None is a real answer -- a plain ATEX has no trailer at all, and "
          "nothing obliges a future one to carry this")


def section2():
    """Where --make may write, and where it may not."""
    print("\n-- 2. the three refusals, and the controls that keep the tool usable --")
    scratch = os.path.join(tempfile.gettempdir(), "rurik-atex-out.atex")

    check(_out_refused(r"C:\gw\Gw.dat"),
          "writing into the owner's install is REFUSED",
          "--make C:\\gw\\Gw.dat would truncate a 4.2 GB archive to a few "
          "kilobytes of DXT1; C:\\gw is read-only to this project, always")
    check(_out_refused(r"C:\gw\sub\dir\icon.atex"),
          "and so is anything BELOW it",
          "a prefix test, not an equality test")

    dat_study = vaultpath.vault_path("dat_study", "Gw.dat")
    check(_out_refused(dat_study),
          "writing into vault/dat_study is REFUSED",
          f"{dat_study} -- the SOURCE snapshot every other archive is cut "
          f"from, and it sits INSIDE the vault, so the ordering of the two "
          f"tests in resolve_out is load-bearing")

    roots = atex.working_tree_roots()
    check(len(roots) >= 1 and all(os.path.isabs(r) for r in roots),
          f"the checkout refusal covers {len(roots)} root(s), not just this one",
          f"{roots} -- a git worktree's root is NOT the main checkout's, and "
          f"mapbuild.py measured `<main>/toolkit/out.dat` being ALLOWED from a "
          f"worktree before it learned this")
    # ONE check over every root rather than one check per root, deliberately.
    # A worktree resolves two roots and a plain checkout one, so a loop of
    # checks would make this file's check count depend on where it is run from
    # -- and a floor that moves with the environment is a floor that gets
    # lowered in irritation the first time the arc lands on main.
    unrefused = [r for r in roots
                 if not _out_refused(os.path.join(r, "toolkit", "icon.atex"))]
    check(not unrefused,
          f"writing into ANY of the {len(roots)} checkout root(s) is REFUSED",
          f"{unrefused} allowed" if unrefused else
          "an authored ATEX is derived from measured ArenaNet layout and the "
          "provenance gate keeps derived bytes out of the tree")

    # POSITIVE CONTROLS. A guard that refuses everything protects nothing,
    # because then the tool never runs and nobody notices it is broken.
    check(not _out_refused(scratch),
          "while an ordinary scratch path OUTSIDE all of them is ALLOWED",
          f"{scratch}")
    check(_out_resolved(scratch) == os.path.abspath(scratch),
          "and resolve_out hands back the absolute path it approved",
          "so the call site opens the checked path rather than the raw one")
    vault_out = vaultpath.vault_path("builds", "icon.atex")
    check(not _out_refused(vault_out),
          "and the VAULT is allowed even though it sits inside the checkout",
          f"{vault_out} -- it is gitignored, which is exactly why derived "
          f"artifacts live there; reskin.py's first guard refused the vault "
          f"while its own message told the operator to write to it")


def _out_resolved(path):
    """The path resolve_out approved, or None when it refused.

    Every call in this file goes through here, and that is not tidiness.
    `atex.Refused` is a SystemExit and therefore a BaseException, so a bare
    `atex.resolve_out(...)` in a positive control is NOT caught by `guarded`'s
    `except Exception` -- it kills the process mid-section, and the run prints
    a verdict for a test that stopped early. MEASURED: sabotage D below (a
    guard that refuses everything) did exactly that to the first version of
    this file, and the run reported one FAIL and no banner at all. Same trap
    `vaultpath.require_dir` set for `test_stripbuild.py`, whose vault-less
    score was a number nobody had ever actually seen.
    """
    try:
        return atex.resolve_out(path)
    except SystemExit:
        return None


def _out_refused(path):
    return _out_resolved(path) is None


def section3():
    """Is the guard WIRED? Asked of the syntax tree, against two saboteurs."""
    print("\n-- 3. the guard is called, not merely defined --")
    src_path = os.path.join(HERE, "atex.py")
    with open(src_path, "r", encoding="utf-8") as fh:
        src = fh.read()

    live = unguarded_write_opens(src)
    check(not live,
          "every write-mode open() in atex.py takes a resolve_out'd path",
          f"{live}" if live else "0 unguarded write sites")
    sites = write_opens(src)
    check(len(sites) >= 1,
          f"and there were {len(sites)} write site(s) to find in the first place",
          f"{sites} -- a module that never writes satisfies the check above "
          f"vacuously; this is the anti-vacuity half, and it holds on the "
          f"PRE-FIX file too, which had one write and no guard")

    # SABOTEUR 1 -- the pre-fix shape, reproduced by ONE edit to the live
    # source: the guard is never called and the raw argv path is opened. This
    # is literally what shipped until 2026-08-13.
    s1 = src.replace("out_path = resolve_out(a.make)", "out_path = a.make")
    check(s1 != src, "saboteur 1 could be built from the live source",
          "if this fails the call site was renamed and the sabotage below is "
          "measuring nothing")
    found1 = unguarded_write_opens(s1)
    check(len(found1) == 1,
          "SABOTAGE: guard never called -> the unguarded write is REPORTED",
          f"{found1}")

    # SABOTEUR 2 -- the subtler one, and the reason this is an AST question and
    # not a grep: the guard IS called, its result is discarded, and the raw
    # path is opened anyway. `resolve_out` still appears in the file.
    s2 = src.replace('with open(out_path, "wb") as f:',
                     'with open(a.make, "wb") as f:')
    check(s2 != src, "saboteur 2 could be built from the live source")
    found2 = unguarded_write_opens(s2)
    check(len(found2) == 1 and "a.make" in found2[0][1],
          "SABOTAGE: guard called, result discarded -> still REPORTED",
          f"{found2} -- a grep for `resolve_out` passes this file")

    # And the checker must not simply flag everything: a read is not a write.
    ok = 'p = resolve_out(x)\nopen(p, "wb")\nopen("elsewhere", "rb")\n'
    check(not unguarded_write_opens(ok),
          "CONTROL: a guarded write plus an unguarded READ is clean",
          "a checker that reddened at every open() would be noise, and would "
          "have flagged archive.py's read path in any file that has one")
    check(len(unguarded_write_opens('open(x, "wb")\n')) == 1,
          "CONTROL: and a bare unguarded write is still caught",
          "the two controls together are what make the sabotages above a "
          "difference between two live answers")


# --------------------------------------------------------------------------
def peek_magic(ar, entry):
    """The first four bytes of a row, decompressing only what that needs.

    gwdat.decompress stops at `out_size`, so a 16-byte request costs a couple
    of Huffman tables rather than a whole texture -- ~0.5 ms a row against
    ~30 ms for the full thing. That is the difference between a strided sweep
    and one nobody runs.
    """
    if entry.size < 20:
        return None
    ar.fh.seek(entry.offset)
    if entry.compression == 0:
        return ar.fh.read(4)
    head = ar.fh.read(min(entry.size, 4096))
    try:
        return gwdat.decompress(head, out_size=16)[0][:4]
    except Exception:                                        # noqa: BLE001
        return None


def collect(ar, stride):
    """({ATEX rows}, {ATTX rows}) at the given MFT stride."""
    a, t = [], []
    for e in ar.entries[::stride]:
        m = peek_magic(ar, e)
        if m == atex.MAGIC_ATEX:
            a.append(e)
        elif m == atex.MAGIC_ATTX:
            t.append(e)
    return a, t


def section4(ar, rows, found, stride):
    """Real ATEX containers, and the header-size controls.

    `rows` is what gets fully parsed; `found` is how many the peek turned up.
    The two are different numbers on a default run and the population check is
    on `found`, because capping the parse must not be able to move a pinned
    corpus figure.
    """
    print(f"\n-- 4. {len(rows)} real ATEX rows --")
    parsed, closed, walked = 0, 0, 0
    rival = collections.Counter()
    fourccs = collections.Counter()
    level_counts = collections.Counter()
    formula_ok = formula_n = 0
    raised = []
    for e in rows:
        data = ar.read(e)
        try:
            a = atex.parse(data)
        except ValueError as exc:
            raised.append((e.index, str(exc)[:70]))
            continue
        parsed += 1
        if a.closes_exactly:
            closed += 1
        if walk_from(data, atex.HEADER_SIZE):
            walked += 1
        for base in (11, 13, 20):
            if walk_from(data, base):
                rival[base] += 1
        fourccs[a.fourcc] += 1
        level_counts[len(a.levels)] += 1
        for lv in a.levels:
            if lv.raw and a.fourcc in atex.BITS_PER_PIXEL:
                formula_n += 1
                if lv.payload_size == atex.level_payload_size(
                        a.fourcc, a.width, a.height, lv.index):
                    formula_ok += 1

    n = len(rows)
    check(n >= 100,
          f"the ATEX sample is {n} rows, enough to refute something",
          "an empty or tiny sample printing '0 of 0' is the exact failure "
          "toolkit/checks.py exists for")
    check(not raised, f"parse() raises on 0 of {n} ATEX rows",
          f"{raised[:3]}" if raised else "0 refusals")
    check(closed == n,
          f"the record walk closes EXACTLY on {closed} of {n}",
          "to the final byte -- an overshoot or undershoot is the artifact "
          "refuting the layout, which is what makes this a measurement")
    check(walked == n,
          f"and an INDEPENDENT walker agrees on {walked} of {n}",
          "written in this file out of int.from_bytes, importing nothing from "
          "atex.py, so the two are not one witness counted twice")
    check(rival[11] == 0 and rival[13] == 0,
          f"CONTROL: shifted one byte either way it closes {rival[11]} and "
          f"{rival[13]} times",
          "the 12-byte header is a measurement, not a convention")
    check(rival[20] == 0,
          f"CONTROL: the REFUTED 20-byte header closes {rival[20]} of {n}",
          "atex.py's docstring records two of this project's own NOT FOUNDs "
          "as level 0's record fields read as header fields; this is that "
          "reading failing on ArenaNet's bytes rather than on our argument")
    multi = sum(c for k, c in level_counts.items() if k > 1)
    check(multi > n // 2,
          f"{multi} of {n} rows carry more than one level",
          f"{sorted(level_counts.items())} -- on a single-level file 'closes "
          f"exactly' is nearly free, so a sample of those would prove little")
    unknown = [f for f in fourccs if f not in atex.BITS_PER_PIXEL]
    check(not unknown,
          f"every fourcc in the sample is in the client's own bpp table",
          f"{dict(fourccs.most_common())}" if not unknown else f"{unknown}")
    check(formula_n and formula_ok == formula_n,
          f"the block-count formula predicts {formula_ok} of {formula_n} "
          f"code-0 level sizes",
          "compressed levels are excluded by their own code, not by us")

    if stride == DEFAULT_STRIDE:
        # A FLOOR since 2026-08-27. This row says of itself that it is "a
        # population assertion about vault/dat_study/Gw.dat", and that archive
        # was resynced from 38797 to 38833: 3,238 -> 3,240 ATEX at this stride.
        # The findings this file exists for are ratios over whatever it finds
        # (400 of 400 parsed, the block-count formula), and none of them moved.
        check(found >= ATEX_AT_STRIDE,
              f"the default stride finds at least {ATEX_AT_STRIDE} ATEX rows",
              f"{found} -- a population FLOOR for vault/dat_study/Gw.dat; 3,238 "
              f"on 38797 and 3,240 on 38833. A shortfall means the stride walk "
              f"stopped seeing them, which is the defect worth catching")
    else:
        LEDGER.skip("the ATEX population count",
                    f"stride {stride} is not the default {DEFAULT_STRIDE}, so "
                    f"the pinned count does not apply")
    return n


def section5(ar, rows, stride):
    """The ATTX asymmetry: an ATEX container with a fixed-size ffna trailer."""
    print(f"\n-- 5. {len(rows)} real ATTX rows --")
    n = len(rows)
    if not n:
        LEDGER.skip("the ATTX asymmetry",
                    "no ATTX rows in this sample; nothing to measure")
        return
    refused = trailer_size = trailer_ffna = head_closes = 0
    wrong_size = []
    digests = set()
    messages = collections.Counter()
    for e in rows:
        data = ar.read(e)
        try:
            atex.parse(data)
        except ValueError as exc:
            refused += 1
            messages[str(FFNA_AS_SIZE) in str(exc)] += 1
        end = walk_end(data, atex.HEADER_SIZE)
        tail = data[end:]
        if len(tail) == TRAILER_SIZE:
            trailer_size += 1
        else:
            wrong_size.append((e.index, len(tail)))
        if tail[:4] == TRAILER_MAGIC and len(tail) > 4 \
                and tail[4] == TRAILER_FFNA_TYPE:
            trailer_ffna += 1
        digests.add(hashlib.sha256(tail).hexdigest())
        try:
            head = atex.parse(data[:end])
            if head.closes_exactly and head.magic == atex.MAGIC_ATTX:
                head_closes += 1
        except ValueError:
            pass

    check(refused == n,
          f"parse() raises on {refused} of {n} ATTX rows",
          "the asymmetry against 0 of the ATEX sample is the finding; it is "
          "pinned so the day someone teaches parse() about ATTX this file "
          "says exactly what changed")
    check(messages[True] == refused,
          f"and every refusal quotes {FFNA_AS_SIZE} as the level size",
          "which is `ffna` read little-endian as a u32 -- naming WHERE the "
          "walk died, not merely that it did")
    check(trailer_size == n and not wrong_size,
          f"the trailer is exactly {TRAILER_SIZE} bytes on {trailer_size} of {n}",
          f"{wrong_size[:3]}" if wrong_size else "a constant SIZE")
    check(trailer_ffna == n,
          f"and it is an `ffna` type-{TRAILER_FFNA_TYPE} file on "
          f"{trailer_ffna} of {n}",
          "the same container magic the map files use, at a different type")
    check(len(digests) == n,
          f"its CONTENTS differ on all {len(digests)} of {n}",
          "so it is a per-texture payload of a fixed-size format, NOT one "
          "shared blob -- 'constant trailer' read loosely would have filed "
          "this as a shared constant, and it is not one")
    check(head_closes == n,
          f"cut the trailer off and the container closes exactly, "
          f"{head_closes} of {n}",
          "which is what makes ATTX a structural finding -- an ATEX plus a "
          "trailer -- rather than a crash report")

    if stride == DEFAULT_STRIDE:
        # A FLOOR, same reason as the ATEX count above: 106 on 38797, 107 on
        # 38833. THE ATTX FINDING IS UNTOUCHED BY THIS -- it is that parse()
        # raises on every ATTX row and none of the ATEX beside them, and that
        # the trailer is a constant size with distinct contents. Those are all
        # "n of n" over whatever population exists and are asserted separately.
        check(n >= ATTX_AT_STRIDE,
              f"the default stride finds at least {ATTX_AT_STRIDE} ATTX rows",
              f"{n} -- a population FLOOR; 106 on 38797 and 107 on 38833")
    else:
        LEDGER.skip("the ATTX population count",
                    f"stride {stride} is not the default {DEFAULT_STRIDE}")


def section5b(ar, rows):
    """ATTX as a CAPABILITY -- rung T1, on ArenaNet's own rows.

    Section 5 above is unchanged and still asserts that `parse` REFUSES all of
    them, because that refusal is correct and is what catches damage. What
    changed is that the trailer can now be split off by a named function, and
    the split is measured against this file's OWN `walk_end` -- two
    implementations, no shared code, one answer per row.
    """
    print(f"\n-- 5b. splitting the trailer on {len(rows)} real ATTX rows --")
    if not rows:
        LEDGER.skip("the ATTX capability",
                    "no ATTX rows in this sample; nothing to measure")
        return
    n = len(rows)
    agree = decoded = closes = 0
    lengths = collections.Counter()
    bad = []
    for e in rows:
        data = ar.read(e)
        try:
            body, tail = atex.split_trailer(data)
        except ValueError as exc:                              # noqa: BLE001
            bad.append((e.index, f"{type(exc).__name__}: {exc}"))
            continue
        lengths[len(tail)] += 1
        if len(body) == walk_end(data, atex.HEADER_SIZE):
            agree += 1
        container = atex.parse(body)
        if container.closes_exactly:
            closes += 1
        try:
            rgba, w, h = atex.decode_rgba(data)
            if len(rgba) == w * h * 4 and (w, h) == (container.width,
                                                     container.height):
                decoded += 1
        except Exception as exc:                               # noqa: BLE001
            bad.append((e.index, f"decode {type(exc).__name__}: {exc}"))

    check(agree == n,
          f"split_trailer's boundary equals this file's own walk on "
          f"{agree} of {n}",
          "two implementations sharing no code -- walk_end is written here "
          "out of int.from_bytes and imports nothing from atex.py")
    check(closes == n,
          f"and the body it hands back closes exactly on {closes} of {n}",
          "the artifact refuting the boundary, not our parser forcing it")
    check(decoded == n and not bad,
          f"decode_rgba reads {decoded} of {n} ATTX rows END TO END",
          f"{bad[:2]}" if bad else "at the container's own declared "
          "dimensions -- the capability this rung exists to add")

    # THE TRAILER LENGTH IS A CENSUS, NOT A CONSTANT. Section 5 asserts the
    # 21,923 above; what this adds is the DISTRIBUTION, so the day a build
    # ships a second length this names both instead of reddening with one
    # number and no context. A constant nothing re-derives is a landmine, and
    # `split_trailer` deliberately does not use this value to find anything.
    check(len(lengths) == 1,
          f"the trailer takes exactly {len(lengths)} distinct length over "
          f"{n} rows",
          f"{dict(lengths)}")

    # THE SECOND WITNESS ON REAL BYTES. The head length is NOT a constant --
    # MEASURED at 578 distinct values from 368 to 68,156 over the whole 1,648
    # -- so this agreement is not free, and the two controls are what say so.
    declared = same = 0
    rival_total = rival_short = 0
    for e in rows:
        data = ar.read(e)
        body, tail = atex.split_trailer(data)
        d = atex.trailer_declared_end(tail)
        if d is None:
            continue
        declared += 1
        same += 1 if d == len(body) else 0
        rival_total += 1 if d == len(data) else 0
        rival_short += 1 if d == len(body) - 12 else 0
    check(declared == n and same == n,
          f"ArenaNet's own footer declares the boundary our walk found, "
          f"{same} of {n}",
          "an INDEPENDENT witness -- the walk can now be refuted by her "
          "number rather than only agreeing with itself, and the client's "
          "writer at VA 0x007582A0 appends exactly this")
    check(rival_total == 0 and rival_short == 0,
          f"CONTROLS: it is neither the total length ({rival_total} of {n}) "
          f"nor head-12 ({rival_short} of {n})",
          "so the agreement above is to the head length specifically")


def section6(ar, atex_rows, attx_rows):
    """The whole-archive census. --all only: a full peek is ~74 s."""
    print("\n-- 6. the whole archive --")
    check(len(ar.entries) == CORPUS_ROWS,
          f"the archive holds {CORPUS_ROWS} MFT rows", f"{len(ar.entries)}")
    check(len(atex_rows) == CORPUS_ATEX,
          f"{CORPUS_ATEX} rows decompress to the ATEX magic",
          f"{len(atex_rows)}")
    check(len(attx_rows) == CORPUS_ATTX,
          f"{CORPUS_ATTX} rows decompress to the ATTX magic",
          f"{len(attx_rows)} -- ATTX is 3.1% of the two put together, which "
          f"is why the strided default parses every one it finds")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.strip().splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dat", default=None)
    ap.add_argument("--stride", type=int, default=DEFAULT_STRIDE,
                    help="MFT peek stride; every row at this stride is looked "
                         "at, and every ATTX one found is parsed")
    ap.add_argument("--sample", type=int, default=DEFAULT_SAMPLE,
                    help="how many of the ATEX rows found are fully parsed")
    ap.add_argument("--all", action="store_true",
                    help="every row and every ATEX -- ~30 minutes")
    args = ap.parse_args(argv)

    print(__doc__.strip().splitlines()[0])
    guarded(section0)
    guarded(section1)
    guarded(section1b)
    guarded(section2)
    guarded(section3)

    dat = args.dat
    if dat is None:
        dat = os.path.join(vaultpath.vault_path("dat_study"), "Gw.dat")
    if not os.path.isfile(dat):
        LEDGER.skip("everything that needs the archive (sections 4-6)",
                    f"no Gw.dat at {dat}; vault resolved to "
                    f"{vaultpath.vault_root()} ({vaultpath.vault_why()}). "
                    f"Sections 0-3 measured the write guard and buffers this "
                    f"file wrote, and NOTHING about ArenaNet's containers.")
        return LEDGER.verdict()

    stride = 1 if args.all else args.stride
    sample = 10 ** 9 if args.all else args.sample
    t0 = time.time()
    with Archive(dat) as ar:
        atex_rows, attx_rows = collect(ar, stride)
        print(f"\npeeked {len(ar.entries[::stride])} rows at stride {stride} "
              f"in {time.time() - t0:.1f}s: {len(atex_rows)} ATEX, "
              f"{len(attx_rows)} ATTX")
        if args.all:
            guarded(section6, ar, atex_rows, attx_rows)
        step = max(1, len(atex_rows) // sample)
        picks = atex_rows[::step][:sample]
        guarded(section4, ar, picks, len(atex_rows), stride)
        guarded(section5, ar, attx_rows, stride)
        guarded(section5b, ar, attx_rows)
    print(f"\n{time.time() - t0:.1f}s of archive work")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
