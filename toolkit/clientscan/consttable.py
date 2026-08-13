#!/usr/bin/env python3
r"""Locate any `Gw\Const\*.cpp` static table by the string the compiler left after it.

Python 3 standard library only. Read-only: it opens the client binary, never
writes to it, and never launches it. **No disassembler** -- carve-out (1) in
CLAUDE.md scopes `capstone` to exactly `msghandler.py` and `codescan.py`, and
this file is neither, so every claim below is made out of `bytes.find` and
`struct.unpack_from`.

WHY THIS EXISTS. The client-table backlog was being tracked as ~19 separate
extractions, each "find the address of s_<something>". It is one mechanism.
MSVC emits a translation unit's static data and its string literals into
`.rdata` in source order, and every one of these tables is followed immediately
by a string -- either the `__FILE__` path the assert macro needs, or the assert
expression itself. So the table's END is nailed to a byte pattern that survives
a rebuild, and

    base + count * stride  ==  the anchor string's first byte

is a prediction about a build, not an address remembered from one. `reskin.py`
already uses this for `s_charProfession` and `s_attrib`; it does not claim it
generalises, and this module is the claim plus its evidence.

WHAT IS AND IS NOT MEASURED HERE. The anchor pins the table's RIGHT edge. That
alone gives neither the base nor the count, so one more witness is needed, and
which one it is per table is recorded rather than assumed:

  index column   Six of these tables carry their own row index in a fixed
                 dword of the record. Read the LAST record -- the `stride`
                 bytes immediately left of the anchor -- take its index `i`,
                 predict `count = i + 1`, place the base, then require EVERY
                 record's index to equal its position. `s_effect` agreeing on
                 2,076 of 2,077 rows is not something a wrong stride survives.
                 This is the strong form: self-contained, no code scan.

  left edge      Otherwise the table is bounded on the left by the previous
                 emitted datum -- the preceding NUL-terminated string, rounded
                 up to 4. `count` is then the exact division of the gap, and
                 the closure is that it IS exact.

  code reference In both cases, independently: the client's own accessor loads
                 the table with an absolute address, so `VA(base)` occurs as a
                 little-endian dword somewhere in `.text`. That witness shares
                 no method with the anchor arithmetic and it is the one that
                 settled the two non-closures below.

REFUSALS, because an ambiguous match that quietly returns the wrong table is
the failure mode that matters here -- every value downstream would be sourced,
plausible and wrong:

  * an anchor occurring 0 or 2+ times                     `AnchorNotUnique`
  * a base outside the anchor's own PE section            `BaseOutOfSection`
  * an index column that is not 0..count-1                `ShapeDisagrees`
  * a left-edge gap that does not divide by the stride    `NoClosure`
  * a pad that is not the declared number                 `NoClosure`
  * a base the client's own code never references         `NoClosure`

THE MEASURED RESULT ON BUILD 38797, re-derived here and not copied: **24 of 24
corpus tables close.** 17 sit flush against their left neighbour; 4
(`s_titleClientData`, `s_heroClientData`, `s_worldData`, `s_streakClass`) sit
exactly +4 above a 4-aligned left edge because MSVC 8-aligned those arrays; 3
have no string neighbour at all and take their count from another witness.

THAT +4 IS WHY `pad` IS A DECLARED NUMBER AND NOT A TOLERANCE. "Within 4 bytes"
would accept a base that is 4 bytes wrong for any other reason, and 4 bytes is
one record for the eight tables here whose stride is 4. So each deviation is
declared per row and asserted exactly; a build that changes one goes red and
names itself.

A CORRECTION TO THE RECON THIS IMPLEMENTS, which expected two non-closures and
explained one of them as a `-1` sentinel. There are four, and all four are
alignment. No table in this corpus has a sentinel between its last record and
its anchor: `s_attribPoints`'s `FF FF FF FF` is the fourteenth ELEMENT of the
array (`arrsize` counts it, and 14 x 4 lands on the anchor), and
`s_energyTable`'s is likewise its own last element. What the sentinels really
cause is the THIRD shape -- a table whose left neighbour is not a string.
`s_skill` sits directly after `s_energyTable`, and the first version of this
module happily found a "previous string" 233 KB deep INSIDE the skill table:
eight printable bytes that occur by chance in 3,443 x 164 bytes of records. It
reported a base off by 233 KB with a straight face. A left-edge witness is only
as good as the claim that the bytes before the table are a string, so rows that
cannot make that claim declare `pad=None` and say why.

THE BLIND SPOT, measured rather than papered over. The left-edge derivation
fixes the BASE, not the stride: a stride that DIVIDES the true stride puts the
base in the same place and closes with a multiple of the true count. `s_eula`
read at stride 4 closes with 99 records instead of 33. Nothing in the left-edge
path can see that -- only an index column can, and rows without one carry
`stride_from` naming what fixed the stride. `test_consttable.py` pins the blind
spot as a check so that closing it later reddens something.

Output is JSON on stdout or to --out. Never write extracted client values into
the repo: the provenance gate is absolute and bulk extraction goes to `vault/`.

    python toolkit/clientscan/consttable.py --verify
    python toolkit/clientscan/consttable.py --table s_effect
    python toolkit/clientscan/consttable.py --find "index < arrsize(s_glow)" --stride 44
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gwpe import PE                                              # noqa: E402
import pinned                                                    # noqa: E402

find_exe = pinned.find

# A string literal the compiler emitted. Six characters is enough to exclude
# most record data and short enough to catch `id < 8`-sized assert expressions
# when one is used as an anchor.
MIN_STRING = 6
EDGE_ALIGN = 4


class Refusal(Exception):
    """This module never guesses. Every failure below is one of these."""


class AnchorNotUnique(Refusal):
    pass


class BaseOutOfSection(Refusal):
    pass


class ShapeDisagrees(Refusal):
    pass


class NoClosure(Refusal):
    pass


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


def refs_to(pe: PE, va: int) -> int:
    """How many little-endian dwords in `.text` equal `va`.

    The accessor's own load of the table base. Deliberately unaligned and
    instruction-blind: this module may not take a disassembler, and a raw byte
    search cannot be fooled by an addressing mode it does not know about --
    which is the defect `test_codescan.py` section 10 exists for, three times
    over.
    """
    text = pe.section(".text")
    if not text:
        return 0
    lo, hi = text["rawptr"], text["rawptr"] + text["rawsize"]
    needle = struct.pack("<I", va)
    n, i = 0, pe.data.find(needle, lo, hi)
    while i != -1:
        n += 1
        i = pe.data.find(needle, i + 1, hi)
    return n


def previous_string(pe: PE, off: int):
    """(end, text) of the string ADJACENT to `off`, i.e. the datum just left of it.

    `end` is the offset one past that string's NUL, so `align_up(end, 4)` is the
    first place the compiler could have started the next datum. Only zero pad
    bytes may sit between; anything else means the left neighbour is not a
    string and the answer is (None, None) -- a real answer, not a failure.
    `s_skill`'s left neighbour is `s_energyTable`, a `-1`-terminated integer
    array, and `s_missionClientData`'s is another table.
    """
    data = pe.data
    i = off - 1
    if i < 0 or data[i] != 0:
        return None, None
    # Several NULs may pad the gap; the string's own terminator is the last one.
    while i > 0 and data[i - 1] == 0:
        i -= 1
    end = i + 1
    j = i - 1
    n = 0
    while j >= 0 and 0x20 <= data[j] < 0x7F:
        j -= 1
        n += 1
    if n < MIN_STRING:
        return None, None
    return end, data[j + 1:i]


def string_end_before(pe: PE, off: int, limit: int, floor: int = 0):
    """(end, text) of the last string ending anywhere in [max(floor, off-limit), off).

    Used only when there is no other witness for the count: it walks back
    THROUGH the table looking for its left neighbour. That walk is the one
    genuinely unsafe step in this module, because record data can spell a
    printable run by chance -- eight bytes of `iDr4iDr4` sit 233 KB inside
    `s_skill`, and the first version of this file reported them as the table's
    left edge with a straight face. `limit` is what keeps the damage local, and
    the divisibility check below is what catches it when it happens anyway.

    `floor` is the anchor's own section start, and it is not decoration: the PE
    section table itself holds `.rdata\\0`, which is a NUL-terminated printable
    run of exactly the shape this looks for. A search that walked out of the
    section found it and reported the section header as a table's left
    neighbour -- caught by `test_consttable.py` section 4 on a 2 KB fixture,
    where the whole image fits inside one search window.
    """
    data = pe.data
    lo = max(0, floor, off - limit)
    i = off - 1
    while i > lo:
        if data[i] == 0 and i - 1 >= lo and 0x20 <= data[i - 1] < 0x7F:
            j, n = i - 1, 0
            while j >= lo and 0x20 <= data[j] < 0x7F:
                j -= 1
                n += 1
            if n >= MIN_STRING:
                return i + 1, data[j + 1:i]
            i = j
            continue
        i -= 1
    return None, None


def align_up(value: int, to: int) -> int:
    return (value + to - 1) // to * to


class Table:
    """One located table. Every field is either measured or refused."""

    def __init__(self, symbol, anchor, anchor_off, base, count, stride,
                 count_from, stride_from, edge, edge_text, pad, refs,
                 exceptions, note, index_off=None):
        self.symbol = symbol
        self.anchor = anchor
        self.anchor_off = anchor_off
        self.base = base
        self.count = count
        self.stride = stride
        self.count_from = count_from
        self.stride_from = stride_from
        self.edge = edge
        self.edge_text = edge_text
        self.pad = pad
        self.refs = refs
        self.exceptions = exceptions
        self.note = note
        self.index_off = index_off

    @property
    def end(self):
        return self.base + self.count * self.stride

    @property
    def closes(self):
        """base + count*stride lands exactly on the anchor's first byte."""
        return self.end == self.anchor_off

    @property
    def witnesses(self):
        """What corroborates this row, other than the anchor arithmetic itself.

        The distinction the report exists to keep visible: a row whose count
        came from the LEFT EDGE and whose only other witness is the code
        reference has ONE independent witness, and a row whose count came from
        its INDEX COLUMN and whose base also lands on the left edge has two.
        Both are useful; conflating them would let the corpus look stronger
        than it is.
        """
        got = []
        if self.count_from.startswith("index"):
            got.append("index column")
        if self.edge is not None:
            got.append(f"left edge (pad {self.pad:+d})")
        if self.refs:
            got.append(f"{self.refs} code ref(s)")
        return got

    def as_dict(self):
        return {
            "symbol": self.symbol,
            "anchor": self.anchor.rstrip(b"\x00").decode("ascii", "replace"),
            "anchor_off": self.anchor_off,
            "base": self.base,
            "count": self.count,
            "stride": self.stride,
            "bytes": self.count * self.stride,
            "count_from": self.count_from,
            "stride_from": self.stride_from,
            "left_edge": self.edge,
            "left_neighbour": (self.edge_text or b"").decode("ascii", "replace"),
            "pad": self.pad,
            "base_refs": self.refs,
            "index_exceptions": self.exceptions,
            "closes": self.closes,
            "witnesses": self.witnesses,
            "note": self.note,
        }

    def rival_strides(self, pe: PE, cap=256):
        """Other strides that would ALSO close on this base, and survive the shape.

        The measured blind spot, printed rather than argued about. A stride that
        DIVIDES the true one puts the base in the same place and closes with a
        multiple of the true count -- `s_eula` read at 4 closes with 99 records
        instead of 33, and nothing in the left-edge path can see it. An index
        column can: it refuted this module's own first reading of `s_glow`,
        which was entered as 2 x 44 (it closed) and is 11 x 8.

        So a row with an index column normally reports zero rivals and a row
        without reports several. That difference is the point.
        """
        span = self.anchor_off - self.base
        out = []
        for s in range(4, min(span, cap) + 1, 4):
            if s == self.stride or span % s or span // s < 2:
                # `s == span` is not a rival reading, it is a one-record table,
                # and the anchor arithmetic is trivially true for it -- an index
                # column of one entry always "ascends". Reporting it would put a
                # meaningless entry on half the corpus rows and bury the four
                # real ones.
                continue
            if self.index_off is not None:
                if self.index_off + 4 > s:
                    continue
                n = span // s
                if all(u32(pe.data, self.base + i * s + self.index_off) == i
                       for i in range(min(n, 64))):
                    out.append(s)
            else:
                out.append(s)
        return out

    def record(self, pe: PE, i: int) -> bytes:
        if not 0 <= i < self.count:
            raise IndexError(f"{self.symbol}: row {i} outside 0..{self.count - 1}")
        o = self.base + i * self.stride
        return pe.data[o:o + self.stride]


def locate(pe: PE, anchor: bytes, stride: int, *, symbol=None, index_off=None,
           count=None, pad=0, max_span=8192, stride_from="declared",
           note="", require_refs=True) -> Table:
    r"""Find the table whose last byte is the byte before `anchor`.

    `index_off`  the record offset of the table's own ascending row index, if it
                 has one. The strongest witness and the ONLY one here that can
                 refute a stride -- see the blind spot in the module docstring.
    `count`      declared, when the table has no index column and the count came
                 from somewhere this module cannot re-derive (`maprows.py` reads
                 `s_missionClientData`'s 888 out of the client's own bound
                 check). Still checked against the left edge and the code ref.
    `pad`        bytes between the 4-aligned end of the table's left neighbour
                 and the base. `0` -- the default -- is the strict claim that
                 the table butts against the previous string, and it is what
                 makes the closure a PREDICTION rather than a definition. A
                 non-zero value is a MEASURED deviation, asserted exactly, never
                 a tolerance: `s_titleClientData` and `s_heroClientData` are +4
                 because MSVC 8-aligned them, and a "+/- 4" tolerance would have
                 accepted a base that is wrong for any other reason too.
                 `None` measures without asserting -- for exploring a new table,
                 not for a corpus row.
    `max_span`   how far back the left-edge search may walk when it is the only
                 witness for the count.

    Neither `base` nor `count` is an input, so `base + count*stride == anchor`
    is not by itself informative -- what makes it a closure is that `count` and
    `base` come from DIFFERENT witnesses and have to meet on the same byte.
    """
    if stride <= 0:
        raise ValueError("stride must be positive")
    data = pe.data
    hits = data.count(anchor)
    if hits != 1:
        raise AnchorNotUnique(
            f"{symbol or 'table'}: its anchor occurs {hits} time(s), expected "
            f"exactly 1. Refusing to guess which occurrence names the table -- "
            f"re-derive the layout for this build before trusting anything here.")
    anchor_off = data.find(anchor)
    sec = pe.section_of_rva(pe.off_to_rva(anchor_off))

    exceptions = []
    if index_off is not None:
        if index_off + 4 > stride:
            raise ValueError(f"index column at +0x{index_off:X} outside a "
                             f"{stride}-byte record")
        count = u32(data, anchor_off - stride + index_off) + 1
        count_from = f"index column at record+0x{index_off:02X}"
    elif count is not None:
        count_from = "declared"
    else:
        # No count witness: the previous string bounds the table on the left,
        # the gap must divide by the stride, and the quotient is the count.
        e, _txt = string_end_before(pe, anchor_off, max_span,
                                    floor=sec["rawptr"] if sec else 0)
        if e is None:
            raise NoClosure(
                f"{symbol or 'table'}: no index column, no declared count, and no "
                f"string within {max_span} bytes below the anchor to bound the "
                f"table on the left. Nothing here can produce a count, so this "
                f"module refuses rather than inventing one.")
        cand = align_up(e, EDGE_ALIGN) + (pad or 0)
        span = anchor_off - cand
        if span <= 0:
            raise NoClosure(
                f"{symbol or 'table'}: the left edge 0x{cand:X} is not below the "
                f"anchor 0x{anchor_off:X}. The 'previous string' is inside the "
                f"table, which is what a chance printable run in record data "
                f"looks like. Refusing.")
        count, residual = divmod(span, stride)
        if residual:
            raise NoClosure(
                f"{symbol or 'table'}: the gap from the left edge 0x{cand:X} to "
                f"the anchor 0x{anchor_off:X} is {span} bytes, not a multiple of "
                f"stride {stride} (residual {residual}). base + count*stride does "
                f"not land on the anchor, so either the stride is wrong or that "
                f"string is not the table's left neighbour.")
        count_from = "left edge"

    if count < 1:
        raise NoClosure(f"{symbol or 'table'}: derived count {count} is not positive")
    base = anchor_off - count * stride
    if base < 0 or pe.off_to_rva(base) is None:
        raise BaseOutOfSection(
            f"{symbol or 'table'}: count {count} x stride {stride} puts the "
            f"base at file offset {base:+d} relative to 0, which is not a "
            f"mapped offset. Printed signed on purpose -- a negative base "
            f"formatted as hex reads as a plausible address")
    base_sec = pe.section_of_rva(pe.off_to_rva(base))
    if sec is None or base_sec is not sec:
        raise BaseOutOfSection(
            f"{symbol or 'table'}: base 0x{base:X} lands in "
            f"{base_sec['name'] if base_sec else 'nothing'} while its anchor is in "
            f"{sec['name'] if sec else 'nothing'}. A table cannot straddle a "
            f"section boundary.")

    if index_off is not None:
        for i in range(count):
            got = u32(data, base + i * stride + index_off)
            if got != i:
                exceptions.append((i, got))
        # A handful of holes is a fact about the table -- `s_effect` has exactly
        # one, at row 2036. A column that disagrees everywhere is a wrong stride
        # wearing a plausible count, and it is the whole reason this exists.
        if len(exceptions) > max(4, count // 100):
            raise ShapeDisagrees(
                f"{symbol or 'table'}: {len(exceptions)} of {count} records carry "
                f"an index column that is not their own position (first: "
                f"{exceptions[0]}). The anchor and the shape disagree, so one of "
                f"the two assumptions is wrong for this build. Refusing.")

    # The left edge, re-derived from the BASE. This is the second witness and it
    # is measured, not assumed: a base that is 4 bytes off reports a different
    # pad, which is exactly how the two 8-aligned tables were found.
    edge, edge_text = previous_string(pe, base)
    measured_pad = None if edge is None else base - align_up(edge, EDGE_ALIGN)
    if pad is not None and measured_pad != pad:
        if measured_pad is None:
            raise NoClosure(
                f"{symbol or 'table'}: a pad of {pad} was declared, but the bytes "
                f"before base 0x{base:X} are not a NUL-terminated string -- this "
                f"table's left neighbour is not a string, so it has no left-edge "
                f"witness at all. Declare pad=None and say so in the note.")
        raise NoClosure(
            f"{symbol or 'table'}: {measured_pad} pad byte(s) between the "
            f"4-aligned end of {bytes(edge_text or b'')[-40:]!r} and base "
            f"0x{base:X}, but {pad} declared. A pad is a MEASUREMENT here, not a "
            f"tolerance -- four tables in this corpus are +4 because MSVC "
            f"8-aligned them, and a tolerance would accept a base that is 4 "
            f"bytes wrong for any other reason too, which for the eight "
            f"stride-4 tables here is a whole record.")

    refs = refs_to(pe, pe.off_to_rva(base) + pe.image_base)
    if require_refs and refs == 0:
        raise NoClosure(
            f"{symbol or 'table'}: the client's own code never loads "
            f"0x{pe.off_to_rva(base) + pe.image_base:08X}, the address this "
            f"anchor arithmetic produced. The accessor's absolute load is the "
            f"one witness here that shares no method with the anchor, so a base "
            f"it does not corroborate is refused.")

    return Table(symbol or "?", anchor, anchor_off, base, count, stride,
                 count_from, stride_from, edge, edge_text, measured_pad, refs,
                 exceptions, note, index_off)


# --------------------------------------------------------------------------
# the corpus
#
# Every row was RE-DERIVED here on build 38797 -- none is copied from a document.
# `anchor` is the string the compiler emitted immediately after the table, which
# is the source path for a file's first table and the assert expression for the
# rest. `stride_from` records what fixed the stride, because the left-edge path
# cannot refute one (see the module docstring's blind spot).
# --------------------------------------------------------------------------

CONST = b"P:\\Code\\Gw\\Const\\"

CORPUS = [
    dict(symbol="s_skill", anchor=CONST + b"ConstSkill.cpp\x00", stride=0xA4,
         index_off=0, pad=None, stride_from="skilltable.py",
         note="no left-edge witness: the neighbour is s_energyTable, an integer "
              "array with an FF FF FF FF terminator, not a string"),
    dict(symbol="s_attrib", anchor=CONST + b"ConstAttrib.cpp\x00", stride=20,
         index_off=4, stride_from="reskin.py",
         note="owner, id, name, desc, primary"),
    dict(symbol="s_titleClientData", anchor=CONST + b"ConstTitle.cpp\x00",
         stride=12, index_off=4, pad=4, stride_from="index column",
         note="+4: MSVC 8-aligned this array"),
    dict(symbol="s_heroClientData", anchor=CONST + b"ConstHero.cpp\x00",
         stride=24, index_off=0, pad=4, stride_from="index column",
         note="+4: MSVC 8-aligned this array"),
    dict(symbol="s_effect", anchor=CONST + b"ConstEffect.cpp\x00", stride=16,
         index_off=0, stride_from="index column",
         note="one index hole at row 2036, which holds 2077"),
    dict(symbol="s_aura", anchor=CONST + b"ConstAura.cpp\x00", stride=12,
         index_off=0, stride_from="index column"),
    dict(symbol="s_npcBang", anchor=CONST + b"ConstNpcBang.cpp\x00", stride=16,
         index_off=0, stride_from="index column"),
    dict(symbol="s_missionClientData", anchor=CONST + b"ConstMission.cpp\x00",
         stride=124, count=888, pad=None,
         stride_from="maprows.py, off the client's own `imul eax, esi, 0x7c` "
                     "and `cmp esi, 0x378` at 0x005A8580",
         note="the 888x124 table maprows.py joins map footprints from. Both its "
              "numbers are ArenaNet's, and the base they produce is the one the "
              "client's own code loads -- neighbouring counts 884..892 are "
              "referenced 0 times each"),
    dict(symbol="s_glow", anchor=CONST + b"ConstGlow.cpp\x00", stride=8,
         index_off=0, stride_from="index column",
         note="entered here first as 2 x 44 -- which CLOSED, on the correct base, "
              "with a plausible-looking record -- and the index column refuted it. "
              "It is (id, colour) pairs: 11 x 8"),
    dict(symbol="s_worldData", anchor=CONST + b"ConstWorld.cpp\x00", stride=24,
         pad=4, stride_from="record shape, UNSETTLED -- see the rival strides",
         note="+4 (MSVC 8-aligned). No index column, so nothing here can choose "
              "between 24 and its rivals; the base is the one the client loads "
              "either way, and only the count is in question"),
    dict(symbol="s_dayStr", anchor=CONST + b"Programmer\\ConstTime.cpp\x00",
         stride=4, stride_from="u32 string-id array",
         note="7 rows, and there are 7 days"),
    dict(symbol="s_charCondition",
         anchor=b"condition < arrsize(s_charCondition)\x00", stride=4,
         stride_from="u32 string-id array"),
    dict(symbol="s_charDamage", anchor=b"damage < arrsize(s_charDamage)\x00",
         stride=4, stride_from="u32 string-id array"),
    dict(symbol="s_charFaction", anchor=b"faction < arrsize(s_charFaction)\x00",
         stride=4, stride_from="u32 string-id array"),
    dict(symbol="s_charKind", anchor=b"kind < arrsize(s_charKind)\x00",
         stride=4, stride_from="u32 string-id array"),
    dict(symbol="s_charKindSlaying",
         anchor=b"kind < arrsize(s_charKindSlaying)\x00", stride=4,
         stride_from="u32 string-id array"),
    dict(symbol="s_charMissionMedal",
         anchor=b"missionMedal != CHAR_MISSION_MEDAL_NONE\x00", stride=4,
         stride_from="u32 string-id array",
         note="its `arrsize` assert is NOT the anchor -- a second assert string "
              "sits between, so the anchor is the one that really follows the "
              "table. Anchor choice is per table and is not guessable"),
    dict(symbol="s_charProfession",
         anchor=b"profession < arrsize(s_charProfession)\x00", stride=4,
         stride_from="reskin.py"),
    dict(symbol="s_charProfessionAbbrev",
         anchor=b"profession < arrsize(s_charProfessionAbbrev)\x00", stride=4,
         stride_from="reskin.py"),
    dict(symbol="s_eula", anchor=CONST + b"ConstEula.cpp\x00", stride=12,
         stride_from="record shape: 3 dwords"),
    dict(symbol="s_streakClass",
         anchor=CONST + b"Programmer\\ConstStreak.cpp\x00", stride=16, pad=4,
         stride_from="record shape: u32, f32, u32, u32",
         note="+4 (MSVC 8-aligned)"),
    dict(symbol="s_ticketName",
         anchor=CONST + b"Programmer\\ConstTournament.cpp\x00", stride=4,
         stride_from="u32 string-id array"),
    dict(symbol="s_categoryName",
         anchor=CONST + b"Programmer\\ConstObserve.cpp\x00", stride=4,
         stride_from="u32 string-id array"),
    # Not a Gw\Const table, and kept for exactly that reason: the idiom is a
    # property of how MSVC lays out a translation unit, not of that directory.
    dict(symbol="s_attribPoints", anchor=b"P:\\Code\\Gw\\Char\\CharData.cpp\x00",
         stride=4, count=14, pad=None, stride_from="u32 array",
         note="14 dwords: 5, then 1 2 3 4 5 6 7 9 11 13 16 20, then FF FF FF FF. "
              "MEASURED: the 12-value run is strictly increasing and the leading "
              "5 breaks that, which is what `dead data` looks like from the "
              "outside. UPSTREAM: the same 12 values are the game's published "
              "per-rank attribute-point costs, so index 0 is not rank 0's cost"),
]

BY_SYMBOL = {row["symbol"]: row for row in CORPUS}


def verify(pe: PE):
    """Locate every corpus row. Returns (tables, refusals)."""
    tables, refusals = [], []
    for row in CORPUS:
        try:
            tables.append(locate(pe, **row))
        except Refusal as exc:
            refusals.append((row["symbol"], exc))
    return tables, refusals


def table_for(pe: PE, symbol: str) -> Table:
    if symbol not in BY_SYMBOL:
        raise SystemExit(
            f"no corpus row {symbol!r}. Known: {', '.join(sorted(BY_SYMBOL))}")
    return locate(pe, **BY_SYMBOL[symbol])


# --------------------------------------------------------------------------
# s_effect, decoded
# --------------------------------------------------------------------------

def effect_rows(pe: PE, table: Table):
    """The 16-byte record, field by field.

    MEASURED over all 2,077 records on build 38797:
      +0x00 u32  the effect id, equal to the row index on 2,076 of 2,077
      +0x04 u32  a string id -- 1,996 distinct, one zero (row 2036's hole)
      +0x08 u32  zero on 2,071 rows, a second string id on 6
      +0x0C u32  0x64000000 on every row without exception
    The last one is reported as `tag` rather than named: a constant column tells
    you it is constant and nothing else, and inferring a name from a value is
    the mistake `test_envchunk.py` records for tag6.
    """
    out = []
    for i in range(table.count):
        rec = table.record(pe, i)
        eid, name_id, alt_id, tag = struct.unpack("<4I", rec)
        out.append({"row": i, "id": eid, "name_id": name_id,
                    "alt_id": alt_id, "tag": tag})
    return out


def effect_toml(pe: PE, table: Table, exe_path: str) -> str:
    """`vault/content/effects.toml`: one row per effect, provenance per row.

    Condition 3 of the owner's 2026-08-11 ruling is per-row provenance, and it
    is the one `content.py` cannot enforce -- so it is spelled out on every row
    rather than hoisted to a header comment that a merge could drop.

    The row commits the STRING ID and not the string. That is the same
    "commit the id, resolve the string at run time" pattern `mapbuild.py` uses,
    and it is what keeps ArenaNet's authored text out of a file that will be
    merged into a running server.
    """
    prov = ('{ source = "client-table", '
            'extractor = "toolkit/clientscan/consttable.py", '
            f'build = {pinned.BUILD}, '
            f'note = "s_effect[%d]; table at file 0x{table.base:06X}, stride '
            f'{table.stride}, {table.count} records, located by the anchor '
            f'\\"ConstEffect.cpp\\" at file 0x{table.anchor_off:06X}" }}')
    lines = [
        "# s_effect, read out of the pinned client's own static table.",
        "#",
        f"#   client   {exe_path}",
        f"#   build    {pinned.BUILD}",
        f"#   table    file 0x{table.base:06X} .. 0x{table.end:06X}, "
        f"{table.count} x {table.stride} B",
        f"#   anchor   file 0x{table.anchor_off:06X}, "
        f"{table.anchor.rstrip(chr(0).encode()).decode()}",
        f"#   witness  count from the {table.count_from}; "
        f"{table.refs} code reference(s) to the base",
        "#",
        "# Every value here is a MEASUREMENT -- ids and offsets. No ArenaNet",
        "# text: `name_id` is a string id the client resolves from the owner's",
        "# own archive at run time.",
        "",
    ]
    # Keyed by the ARRAY INDEX, not by the id column. The client's own assert is
    # `index < arrsize(s_effect)`, so the index is what identifies a row; the id
    # column merely happens to equal it on 2,076 of 2,077 records, and keying by
    # the one that does not would silently drop row 2036 and mint a row 2077.
    for row in effect_rows(pe, table):
        lines.append(f"[effect.{row['row']}]")
        lines.append(f"id = {row['id']}")
        lines.append(f"name_id = {row['name_id']}")
        if row["alt_id"]:
            lines.append(f"alt_id = {row['alt_id']}")
        lines.append(f"tag = {row['tag']}")
        lines.append("provenance = " + (prov % row["row"]))
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------

def _print_table(t: Table, pe: PE = None):
    mark = "" if t.closes else "  <- DOES NOT CLOSE"
    pad = "-" if t.pad is None else f"{t.pad:+d}"
    print(f"  {t.symbol:24s} file 0x{t.base:06X}..0x{t.end:06X} "
          f"{t.count:6d} x {t.stride:4d}  pad {pad:>3s}  refs {t.refs:3d}  "
          f"{t.count_from}{mark}")
    if t.exceptions:
        print(f"  {'':24s}   index exceptions: {t.exceptions[:4]}")
    if pe is not None:
        rivals = t.rival_strides(pe)
        if rivals:
            print(f"  {'':24s}   rival strides that also close: {rivals}")
    if t.note:
        print(f"  {'':24s}   {t.note}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", help="client to read; defaults to the pinned "
                                  "pristine build, and the choice is printed")
    ap.add_argument("--verify", action="store_true",
                    help="locate the whole corpus and print the closure table")
    ap.add_argument("--table", metavar="SYMBOL",
                    help="locate one corpus table and print its rows")
    ap.add_argument("--rows", type=int, default=8,
                    help="how many records to print with --table")
    ap.add_argument("--find", metavar="ANCHOR",
                    help="locate a table not in the corpus by its anchor string")
    ap.add_argument("--stride", type=int, help="record size, with --find")
    ap.add_argument("--index-off", type=int, default=None,
                    help="record offset of the row-index column, with --find")
    ap.add_argument("--count", type=int, default=None,
                    help="declared record count, with --find")
    ap.add_argument("--emit-effect", action="store_true",
                    help="write s_effect as a content overlay (TOML)")
    ap.add_argument("--out", help="where to write; keep it out of the repo")
    a = ap.parse_args(argv)

    exe, why = ((a.exe, "given on the command line") if a.exe else find_exe())
    pe = PE(exe)
    print(f"client: {exe}\n        ({why})")

    # A refusal is a RESULT, not a crash. Exit 2 with the reason printed: a
    # traceback is a wall of frames around a sentence the operator needs, and
    # `test_datcheck.py` records the same lesson from the other side -- an
    # uncaught traceback exited 1, which that CLI already uses to mean "the
    # archive changed", so a crash read as a finding.
    try:
        if a.find:
            anchor = a.find.encode("ascii") + b"\x00"
            if not a.stride:
                raise SystemExit("--find needs --stride")
            # `pad=None` for exploration: measure the left edge, do not assert
            # it. A new table's alignment is exactly what is not known yet, and
            # a refusal on it would hide the base the operator wants to see.
            t = locate(pe, anchor, a.stride, symbol=a.find,
                       index_off=a.index_off, count=a.count, pad=None,
                       stride_from="given on the command line")
            _print_table(t, pe)
            print(f"  witnesses: {', '.join(t.witnesses) or 'NONE'}")
            return 0

        if a.emit_effect:
            t = table_for(pe, "s_effect")
            text = effect_toml(pe, t, exe)
            if not a.out:
                raise SystemExit(
                    "--emit-effect needs --out. This writes extracted client "
                    "values, which never go into the repo -- send it to "
                    "vault/content/.")
            Path(a.out).write_text(text, encoding="utf-8")
            print(f"wrote {a.out}: {t.count} effect rows, "
                  f"{len(text):,} bytes, provenance per row")
            return 0

        if a.table:
            t = table_for(pe, a.table)
            _print_table(t, pe)
            print()
            for i in range(min(a.rows, t.count)):
                rec = t.record(pe, i)
                words = struct.unpack_from("<" + "I" * (t.stride // 4), rec)
                print(f"  [{i:5d}] " + " ".join(f"{w:10d}" for w in words))
            return 0
    except Refusal as exc:
        print(f"\nREFUSED: {exc}")
        return 2

    tables, refusals = verify(pe)
    print(f"\ncorpus: {len(CORPUS)} tables\n")
    for t in tables:
        _print_table(t, pe)
    if refusals:
        print("\nREFUSED:")
        for sym, exc in refusals:
            print(f"  {sym}: {exc}")
    closed = sum(1 for t in tables if t.closes)
    snug = [t for t in tables if t.pad == 0]
    padded = [t for t in tables if t.pad not in (None, 0)]
    noedge = [t for t in tables if t.pad is None]
    indexed = [t for t in tables if t.index_off is not None]
    print(f"\n{closed} of {len(CORPUS)} close on base + count*stride == anchor; "
          f"{len(tables) - closed} located but not closing; "
          f"{len(refusals)} refused")
    print(f"  left edge: {len(snug)} snug against the previous string (pad 0), "
          f"{len(padded)} at a declared pad "
          f"{sorted({t.pad for t in padded})} (MSVC 8-alignment), "
          f"{len(noedge)} with no string neighbour at all")
    print(f"  {len(indexed)} carry an index column, which is the only witness "
          f"here that can refute a stride")
    print(f"  every located base is loaded by the client's own code: "
          f"{sum(t.refs for t in tables)} reference(s) over {len(tables)} tables, "
          f"minimum {min((t.refs for t in tables), default=0)}")
    if a.out:
        payload = {"exe": exe, "build": pinned.BUILD,
                   "tables": [t.as_dict() for t in tables],
                   "refused": {s: str(e) for s, e in refusals}}
        Path(a.out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"wrote {a.out}")
    return 1 if refusals else 0


if __name__ == "__main__":
    sys.exit(main())
