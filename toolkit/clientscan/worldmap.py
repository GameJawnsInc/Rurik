#!/usr/bin/env python3
r"""The world-map ATLAS: which archive file holds each 512x512 tile of a continent.

Python 3 standard library only. Read-only: it opens the client binary and (with
`--resolve`) an archive, never writes to either, and never launches anything.
**No disassembler** -- CLAUDE.md carve-out (1) scopes `capstone` to exactly
`msghandler.py` and `codescan.py`, and this file is neither, so every claim
below is made out of `re.finditer` over `.text` bytes and `struct.unpack_from`.

WHAT THIS IS. The compass, the mission map (U) and the world map (M) are three
crops of ONE per-continent picture (`studies/minimap/FINDINGS.md` sections 3.1
and 3.2) -- a grid of ATEX tiles compiled into the client as three tables of
pointers, one table per zoom TIER. A map file contributes nothing to that
picture. This module walks those tables and answers, for every
`(tier, world, chunk_x, chunk_y)`, which archive file id holds the tile.

THE PREDICTION, and it was stated before this module existed: `studies/minimap/
PLAN.md` rung S3, written 2026-08-14 against a scratch reading -- "409 tile
records over 7 worlds; trailing u32 = 0 on 409/409; >= 401 resolve to `ATEX`;
the 8 that do not are exactly {387674, 387678, 387680, 387682, 387684, 388093,
388095, 388097}, all in worlds 0/1", plus `count == chunkCX * chunkCY` on 7 of
7 tile-bearing worlds and no record at all for worlds 7/8/9.

OUTCOME, measured here on build 38797 -- every clause MET, and two things the
prediction did not contain:

  * **There are THREE tile tables, not two.** The prediction and FINDINGS name
    the chunk tier (`0x00A37390`) and the parchment tier (`0x00A373E8`). The
    getter shape below occurs exactly THREE times and the third is at
    `0x00A37440`, indexing with `worldData+0x18`. That closes an UNVERIFIED
    item: FINDINGS section 3.1 records `satelliteCX/CY` offsets as "approx
    +0x18/+0x1C, third getter not disassembled". They are +0x18/+0x1C, and the
    witness is the client's own `imul edi,[edx+0x18]` sitting in the same
    function as the assert `chunk.x < worldData.satelliteCX`
    (`ConstWorldMap.cpp:1360`).
  * **NOT every tile is 512x512, and FINDINGS says so on a sample of 4.** Over
    all 484 resolvable tiles: 469 are 512x512 and **15 are 256x256** -- four of
    them in the CHUNK tier, and not at an edge (world 3's grid is 4x8 and the
    odd tiles are (1,5), (2,5), (3,5), (3,6)). A renderer that assumes 512 per
    cell (PLAN rung S5) will misplace them.

HOW THE TABLES ARE LOCATED, which is the whole design. Not at a remembered
address: rung S1's lesson is that only the CODE can refute a reading of a table
(`s_worldData` shipped as `20 x 24`, closed perfectly on the correct base, and
was wrong, because 24 divides 48 and no amount of left-edge arithmetic can see
a divisor stride). So each tier's getter is found by its SHAPE, and the shape
carries four facts that have to agree with each other:

    ConstWorldMapGet<Tier>File(world, chunk)          e.g. 0x005A93E0

      83 ff 0a              cmp edi, WORLDS           -> 10, and s_worldData's
                                                         own count must equal it
      ...   assert `world < WORLDS`                      ConstWorldMap.cpp:1313
      8b 0b  3b 4a 04       cmp chunk.x, [edx+CX]     -> the tier's CX offset
      ...   assert `chunk.x < worldData.chunkCX`         :1316 -- and the TIER'S
                                                         NAME is ArenaNet's own
                                                         word, read out of that
                                                         expression, not ours
      8b 43 04  3b 42 08    cmp chunk.y, [edx+CY]     -> CY, which must be CX+4
      be 90 73 a3 00        mov esi, <TILE TABLE>     -> the table's address
      33 c0 39 7e 08 74 12  cmp [esi+8], world; je    -> record+8 is the world
      83 c0 0c 83 c6 0c
      83 f8 54 72 f0        add 12; add 12; cmp 0x54  -> 12-byte records, 7 of
                                                         them (0x54 / 12)
      8b 7b 04
      0f af 7a 04           imul chunk.y, [edx+CX]    -> the SAME CX offset, a
      03 3b                 add chunk.x                  second read of the same
      3b 3e                 cmp offset, [esi+0]       -> record+0 is the count
      ...   assert `offset < files.count`               :1325
      8b 46 04  8b 04 b8    eax = record.array[offset] -> record+4 is the array

`getters()` refuses when the shape occurs NOWHERE, when an occurrence is
missing any of those witnesses, when two occurrences claim the same tier, and
when the CX offset read by the bound check differs from the CX offset used by
the index arithmetic. That last one is the check with teeth: they are two
different instructions reading the same field for two different purposes, and a
mis-parse of either moves one and not the other.

It deliberately does NOT require a particular NUMBER of getters. Three is what
build 38797 has, and a locator that demanded three would refuse the next build
for having a fourth tier -- which is a fact about ArenaNet's art pipeline and
not a defect in this reader. The count is a MEASUREMENT, asserted in
`test_worldmap.py` against a literal for this build, not a precondition here.
(An earlier draft of this docstring claimed a `locate()` that refused unless
the shape occurred exactly three times. There is no such function and there was
no such check: a rule nothing checks is a wish, and one written down beside a
function that does not enforce it is worse, because a reader stops looking.)

WHAT THIS MODULE DOES **NOT** DECIDE, stated because a reader will want it: the
`continent -> world` mapping. FINDINGS section 7 records it as NOT FOUND and
records a containment test that failed as a discriminator. Nothing here closes
it. A `world` below is the client's own world index and is not an area row's
continent field.

WHY THE OUTPUT IS JSON AND NOT A `content/` OVERLAY. This is a
`source = "client-table"` extraction and every emitted row carries the three
things the owner's 2026-08-11 ruling asks for -- the extractor path, the build,
and provenance per row -- so it satisfies `content.py`'s conditions in form.
It is deliberately not written into `vault/content/`: that directory is merged
into `content.load()` for the SERVER, a 492-row table of texture ids is not
world content, and `test_content.py` records what happens when the overlay
grows something the loader was not expecting. Bulk output goes to the vault
either way; `resolve_out()` refuses `C:\gw`, `vault/dat_study`, and EVERY
checkout of this repository.

    python toolkit/clientscan/worldmap.py                     # the tables
    python toolkit/clientscan/worldmap.py --tiles             # every tile
    python toolkit/clientscan/worldmap.py --resolve           # + archive rows
    python toolkit/clientscan/worldmap.py --resolve --out <vault path>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))

import consttable                                             # noqa: E402
import pinned                                                 # noqa: E402
import vaultpath                                              # noqa: E402
from gwpe import PE                                           # noqa: E402
import archive as archive_mod                                 # noqa: E402
import atex                                                   # noqa: E402
import gwdat                                                  # noqa: E402
import mapchunks                                              # noqa: E402

find_exe = pinned.find

REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
LIVE_INSTALL = os.path.normcase(os.path.abspath(r"C:\gw"))

# The world-index table `s_worldData` is located THROUGH consttable, never at an
# address: that module's corpus row carries the accessor witness that settled its
# stride, and a build that moves the table still resolves. Named here so the
# dependency is visible at the top of the file rather than buried in a call.
WORLD_TABLE = "s_worldData"

# The getter's loop, and the tail that follows the `je found`. Written as one
# regex so a partial match is a miss rather than a half-read function.
#
#   group 1  the tile table's VA          (mov esi, imm32)
#   group 2  the linear-search bound      (cmp eax, imm8) -- bytes, /12 = records
#   group 3  the CX offset used to INDEX  (imul edi, [edx+disp8])
GETTER_LOOP = re.compile(
    rb"\xbe(....)"                              # mov esi, <tile table>
    rb"\x33\xc0"                                # xor eax, eax
    rb"\x39\x7e\x08"                            # cmp [esi+8], edi   (world)
    rb"\x74\x12"                                # je found
    rb"\x83\xc0\x0c\x83\xc6\x0c"                # add eax,12; add esi,12
    rb"\x83\xf8(.)"                             # cmp eax, <bound>
    rb"\x72\xf0"                                # jb loop
    rb"\x5f\x5e\x33\xc0\x5b\x5d\xc3"            # not found -> return 0
    rb"\x8b\x7b\x04"                            # mov edi, [ebx+4]   (chunk.y)
    rb"\x0f\xaf\x7a(.)"                         # imul edi, [edx+CX]
    rb"\x03\x3b"                                # add edi, [ebx]     (chunk.x)
    rb"\x3b\x3e",                               # cmp edi, [esi]     (count)
    re.S)

# The two bound checks, searched BACKWARD from the loop inside one function.
CX_BOUND = re.compile(rb"\x8b\x0b\x3b\x4a(.)\x72", re.S)       # cmp chunk.x,[edx+CX]
CY_BOUND = re.compile(rb"\x8b\x43\x04\x3b\x42(.)\x72", re.S)   # cmp chunk.y,[edx+CY]
WORLD_BOUND = re.compile(rb"\x83\xff(.)\x7c\x14", re.S)        # cmp edi, WORLDS
# push <line>; mov edx, <__FILE__>; mov ecx, <expression>
ASSERT_SITE = re.compile(rb"\x68(..)\x00\x00\xba(....)\xb9(....)", re.S)
# ArenaNet's own name for the tier, read out of its own assert expression.
TIER_EXPR = re.compile(r"^chunk\.x < worldData\.([A-Za-z]+)CX$")

# How far back from the loop a getter's prologue may sit. The three on build
# 38797 span 0x70 bytes; 0xC0 leaves room without reaching the previous function
# (the getters are 0xC0 apart, so this is the largest window that cannot).
GETTER_WINDOW = 0xC0

TILE_RECORD_SIZE = 12       # {u32 count, u32 *array, u32 world}
PAIR_RECORD_SIZE = 8        # {u16 id0, u16 id1, u32 0} -- File.cpp's pair form

# `atex.py`'s documented header: magic at +0, fourcc at +4, w/h u16 at +8. Read
# here from a 16-byte PARTIAL decompression (~0.5 ms a row against ~30 ms for a
# whole tile), which is what makes a 492-row sweep cost tenths of a second.
# `atex.parse` is the authority and the test cross-checks this against it.
ATEX_HEAD = 16


class Refusal(Exception):
    """This module never guesses. Every failure below is one of these."""


class TiersNotFound(Refusal):
    pass


class GetterIncoherent(Refusal):
    pass


class SlotUnmapped(Refusal):
    pass


class GridDisagrees(Refusal):
    pass


# --------------------------------------------------------------------------
# reading the image
# --------------------------------------------------------------------------

def _off(pe: PE, va: int):
    """File offset of a VA, or None if it is not backed by file bytes.

    `.data`'s virtual size here is 5.6 MB against 92 KB on disk, so "the address
    is in a section" is nowhere near enough: most of `.data` has no bytes to
    read and `rva_to_off` correctly answers None. Every caller below treats that
    as a refusal rather than reading zeros.
    """
    return pe.rva_to_off(va - pe.image_base)


def _cstring(pe: PE, va: int, limit: int = 256) -> str:
    o = _off(pe, va)
    if o is None:
        return ""
    end = pe.data.find(b"\x00", o, o + limit)
    if end == -1:
        return ""
    return pe.data[o:end].decode("latin-1")


class Getter:
    """One tier's `ConstWorldMapGet<Tier>File`, and everything it witnesses."""

    def __init__(self, tier, loop_va, table_va, records, cx_off, cy_off,
                 worlds, assert_file, assert_line, tier_assert_line):
        self.tier = tier
        self.loop_va = loop_va
        self.table_va = table_va
        self.records = records
        self.cx_off = cx_off
        self.cy_off = cy_off
        self.worlds = worlds
        self.assert_file = assert_file
        self.assert_line = assert_line
        self.tier_assert_line = tier_assert_line

    def as_dict(self):
        return {"tier": self.tier, "loop_va": self.loop_va,
                "table_va": self.table_va, "records": self.records,
                "cx_off": self.cx_off, "cy_off": self.cy_off,
                "worlds": self.worlds,
                "count_assert": f"{self.assert_file}:{self.assert_line}",
                "tier_assert": f"{self.assert_file}:{self.tier_assert_line}"}

    def __repr__(self):
        return (f"<Getter {self.tier} table 0x{self.table_va:08X} "
                f"{self.records} records CX +0x{self.cx_off:02X}>")


def getters(pe: PE):
    """Every tile-table getter in `.text`, located by shape. Refuses on doubt.

    Returns them in table order. Raises `TiersNotFound` when the shape does not
    occur at least once, and `GetterIncoherent` when an occurrence's own
    witnesses disagree -- which is the point of collecting four of them.
    """
    text = pe.section(".text")
    if not text:
        raise TiersNotFound("no .text section")
    lo, hi = text["rawptr"], text["rawptr"] + text["rawsize"]

    found = []
    for m in GETTER_LOOP.finditer(pe.data, lo, hi):
        loop_off = m.start()
        loop_va = pe.off_to_rva(loop_off) + pe.image_base
        table_va = struct.unpack("<I", m.group(1))[0]
        bound = m.group(2)[0]
        imul_cx = m.group(3)[0]

        if bound % TILE_RECORD_SIZE:
            raise GetterIncoherent(
                f"getter at 0x{loop_va:08X}: its linear search runs to "
                f"{bound} bytes, which is not a whole number of "
                f"{TILE_RECORD_SIZE}-byte records. Either the record is not "
                f"{{count, array, world}} on this build or this is not the "
                f"loop it looks like. Refusing.")

        window = pe.data[max(lo, loop_off - GETTER_WINDOW):loop_off]

        cx_hits = list(CX_BOUND.finditer(window))
        cy_hits = list(CY_BOUND.finditer(window))
        w_hits = list(WORLD_BOUND.finditer(window))
        if not (cx_hits and cy_hits and w_hits):
            raise GetterIncoherent(
                f"getter at 0x{loop_va:08X}: the {GETTER_WINDOW}-byte window "
                f"before its loop holds "
                f"{len(cx_hits)} chunk.x bound check(s), {len(cy_hits)} "
                f"chunk.y, {len(w_hits)} world. A getter has one of each, and "
                f"without them nothing here knows which s_worldData field this "
                f"tier indexes with. Refusing rather than assuming +0x04.")
        cx_off = cx_hits[-1].group(1)[0]
        cy_off = cy_hits[-1].group(1)[0]
        worlds = w_hits[-1].group(1)[0]

        # THE CHECK WITH TEETH. The bound check and the index arithmetic are
        # different instructions reading the same field for different purposes;
        # a mis-parse of either moves one and not the other.
        if cx_off != imul_cx:
            raise GetterIncoherent(
                f"getter at 0x{loop_va:08X}: its bound check reads "
                f"worldData+0x{cx_off:02X} while its index arithmetic "
                f"multiplies by worldData+0x{imul_cx:02X}. Those are the same "
                f"field read twice and they disagree, so one of the two reads "
                f"is wrong. Refusing.")
        if cy_off != cx_off + 4:
            raise GetterIncoherent(
                f"getter at 0x{loop_va:08X}: CX at +0x{cx_off:02X} and CY at "
                f"+0x{cy_off:02X} are not an adjacent dword pair. Refusing.")

        tiers, afile, aline, tline = [], "", 0, 0
        for a in ASSERT_SITE.finditer(window):
            line = struct.unpack("<H", a.group(1))[0]
            expr = _cstring(pe, struct.unpack("<I", a.group(3))[0])
            hit = TIER_EXPR.match(expr)
            if hit:
                tiers.append(hit.group(1))
                tline = line
                afile = _cstring(pe, struct.unpack("<I", a.group(2))[0])
        if len(tiers) != 1:
            raise GetterIncoherent(
                f"getter at 0x{loop_va:08X}: {len(tiers)} assert expression(s) "
                f"of the form `chunk.x < worldData.<tier>CX` in its window "
                f"({tiers}). The TIER NAME is ArenaNet's own word and this is "
                f"where it comes from -- inventing one would put our label on "
                f"a client fact. Refusing.")

        # The `offset < files.count` assert sits just past the loop and names
        # the line the count bound is on. Purely for provenance.
        tail = pe.data[m.end():m.end() + 32]
        ta = ASSERT_SITE.search(tail)
        if ta:
            aline = struct.unpack("<H", ta.group(1))[0]
            afile = _cstring(pe, struct.unpack("<I", ta.group(2))[0]) or afile

        found.append(Getter(tiers[0], loop_va, table_va,
                            bound // TILE_RECORD_SIZE, cx_off, cy_off, worlds,
                            afile, aline, tline))

    if not found:
        raise TiersNotFound(
            "the world-map tile-table getter shape does not occur in .text. "
            "Every address in this module is derived from it, so there is "
            "nothing to fall back on: re-derive the layout for this build.")
    names = [g.tier for g in found]
    if len(set(names)) != len(names):
        raise GetterIncoherent(
            f"two getters claim the same tier: {names}. A tier is identified by "
            f"ArenaNet's own assert expression, so a duplicate means the window "
            f"search is reaching into a neighbouring function. Refusing.")
    return sorted(found, key=lambda g: g.table_va)


class Grid:
    """One (tier, world) tile grid: the tile table's record, joined to s_worldData.

    `count` comes from the TILE TABLE and `cx`/`cy` from `s_worldData` -- two
    different tables in two different translation units. `closes` is that they
    agree, and it is the load-bearing measurement in this module. Nothing here
    forces it: the two numbers are read from bytes 0x1000 apart and are simply
    compared.
    """

    __slots__ = ("tier", "world", "count", "array_va", "cx", "cy",
                 "table_va", "record")

    def __init__(self, tier, world, count, array_va, cx, cy, table_va, record):
        self.tier = tier
        self.world = world
        self.count = count
        self.array_va = array_va
        self.cx = cx
        self.cy = cy
        self.table_va = table_va
        self.record = record

    @property
    def closes(self):
        return self.count == self.cx * self.cy

    def as_dict(self):
        return {"tier": self.tier, "world": self.world, "count": self.count,
                "array_va": self.array_va, "cx": self.cx, "cy": self.cy,
                "closes": self.closes}

    def __repr__(self):
        return (f"<Grid {self.tier} world {self.world} {self.cx}x{self.cy} "
                f"count {self.count}{'' if self.closes else ' DISAGREES'}>")


def world_data(pe: PE):
    """`s_worldData`, located through `consttable`.

    Deliberately a call into that module rather than an address: it carries the
    accessor witness (`cmp esi,0xa` / `lea eax,[esi+esi*2]; shl eax,4`) that
    settled the 10 x 48 shape, and a build that moves the table still resolves.
    Reading `consttable.CORPUS`'s numbers into a literal here would reproduce
    exactly the failure rung S1 fixed.
    """
    return consttable.table_for(pe, WORLD_TABLE)


def grids(pe: PE, gets=None, wd=None):
    """Every (tier, world) grid. Does NOT refuse on a grid that fails to close.

    That is deliberate. `count == cx * cy` is the claim this module is FOR, and
    a function that refuses to return a disagreement makes the claim
    unfalsifiable from the outside -- the caller only ever sees rows that agree.
    `tiles()` refuses instead, because a tile's (x, y) is meaningless once the
    grid is in doubt.
    """
    gets = gets if gets is not None else getters(pe)
    wd = wd if wd is not None else world_data(pe)
    out = []
    for g in gets:
        if wd.count != g.worlds:
            raise GetterIncoherent(
                f"{g.tier}: its getter bounds the world index at {g.worlds} "
                f"(`cmp edi, 0x{g.worlds:X}`) while consttable puts "
                f"{wd.count} records in {WORLD_TABLE}. Those are ArenaNet's "
                f"two statements of one number, from different functions, and "
                f"they disagree. Refusing.")
        o = _off(pe, g.table_va)
        if o is None:
            raise SlotUnmapped(
                f"{g.tier}: its tile table at 0x{g.table_va:08X} is not backed "
                f"by file bytes.")
        for k in range(g.records):
            count, array_va, world = struct.unpack_from(
                "<3I", pe.data, o + k * TILE_RECORD_SIZE)
            if world >= wd.count:
                raise GetterIncoherent(
                    f"{g.tier} record {k} names world {world}, outside "
                    f"0..{wd.count - 1}. Refusing.")
            rec = wd.record(pe, world)
            cx, cy = struct.unpack_from("<2I", rec, g.cx_off)
            out.append(Grid(g.tier, world, count, array_va, cx, cy,
                            g.table_va, k))
    return out


class Tile:
    """One tile: a grid cell, the pair record it points at, and the file id."""

    __slots__ = ("tier", "world", "x", "y", "file_id", "id0", "id1",
                 "trailer", "slot_va", "record_va")

    def __init__(self, tier, world, x, y, file_id, id0, id1, trailer,
                 slot_va, record_va):
        self.tier = tier
        self.world = world
        self.x = x
        self.y = y
        self.file_id = file_id
        self.id0 = id0
        self.id1 = id1
        self.trailer = trailer
        self.slot_va = slot_va
        self.record_va = record_va

    def key(self):
        return (self.tier, self.world, self.x, self.y)

    def as_dict(self):
        return {"tier": self.tier, "world": self.world,
                "chunk_x": self.x, "chunk_y": self.y,
                "file_id": self.file_id, "id0": self.id0, "id1": self.id1,
                "trailer": self.trailer, "record_va": self.record_va}

    def __repr__(self):
        return (f"<Tile {self.tier} w{self.world} ({self.x},{self.y}) "
                f"file {self.file_id}>")


def tiles(pe: PE, gets=None, wd=None, only_tier=None):
    """Every non-NULL tile, in table order.

    A NULL slot is a grid cell with no art and is SKIPPED, not an error --
    1,232 of the 1,232 slots on build 38797 are addressable and 492 are
    non-NULL. A non-NULL slot that is not file-backed IS an error: reading
    zeros there would mint file id -255 and resolve to nothing, which reads as
    "the tile is missing" rather than "this module cannot see the bytes".
    """
    gets = gets if gets is not None else getters(pe)
    wd = wd if wd is not None else world_data(pe)
    if only_tier is not None and only_tier not in {g.tier for g in gets}:
        # A confident zero for a tier that does not exist reads as "that tier
        # has no art", which is a fact about the client rather than a typo.
        raise TiersNotFound(
            f"no tier named {only_tier!r}; this build has "
            f"{sorted(g.tier for g in gets)}. The names are ArenaNet's own, "
            f"read out of each getter's `chunk.x < worldData.<tier>CX` assert.")
    bad = [g for g in grids(pe, gets, wd) if not g.closes]
    if bad:
        raise GridDisagrees(
            f"{len(bad)} grid(s) whose tile count is not chunkCX x chunkCY, "
            f"first {bad[0]!r}. A tile's (x, y) is `i % cx, i // cx`, so once "
            f"the grid is in doubt every coordinate this would emit is an "
            f"invention. Refusing. (`grids()` returns them without refusing, "
            f"which is what makes that agreement a measurement.)")
    out = []
    for g in grids(pe, gets, wd):
        if only_tier and g.tier != only_tier:
            continue
        ao = _off(pe, g.array_va)
        if ao is None:
            raise SlotUnmapped(
                f"{g.tier} world {g.world}: its slot array at "
                f"0x{g.array_va:08X} is not backed by file bytes.")
        for i in range(g.count):
            slot = struct.unpack_from("<I", pe.data, ao + i * 4)[0]
            if slot == 0:
                continue
            ro = _off(pe, slot)
            if ro is None:
                raise SlotUnmapped(
                    f"{g.tier} world {g.world} slot {i} points at "
                    f"0x{slot:08X}, which is not backed by file bytes. Reading "
                    f"zeros there would mint a plausible wrong file id.")
            id0, id1, trailer = struct.unpack_from("<HHI", pe.data, ro)
            out.append(Tile(g.tier, g.world, i % g.cx, i // g.cx,
                            mapchunks.dependency_file_id(id0, id1),
                            id0, id1, trailer, g.array_va + i * 4, slot))
    return out


# --------------------------------------------------------------------------
# joining to the archive
# --------------------------------------------------------------------------

def atex_head(blob: bytes):
    """(magic, width, height) from the first 16 bytes of an ATEX container.

    The cheap reader. `atex.parse` is the authority and needs the whole file;
    this reads the same three fields out of a 16-byte partial decompression so
    a 492-row sweep costs tenths of a second instead of tens of them. The test
    pins it against `atex.parse` on a fully decompressed tile, because two
    readings of one header is exactly the kind of duplication that drifts.
    """
    if len(blob) < 12:
        return b"", 0, 0
    return blob[0:4], *struct.unpack_from("<2H", blob, 8)


class Resolved:
    """A tile joined to an archive: the row, and what the row actually holds."""

    __slots__ = ("tile", "row", "magic", "width", "height", "stored")

    def __init__(self, tile, row, magic, width, height, stored):
        self.tile = tile
        self.row = row
        self.magic = magic
        self.width = width
        self.height = height
        self.stored = stored

    @property
    def is_atex(self):
        return self.magic == atex.MAGIC_ATEX

    def as_dict(self):
        return {"row": self.row,
                "magic": self.magic.decode("latin-1") if self.magic else None,
                "width": self.width, "height": self.height,
                "stored": self.stored}


def resolve(ar, tile_rows, file_ids=None):
    """(resolved, unresolved). `unresolved` is the tiles whose id has no row.

    Eight of them on every archive in the vault, and that is a RESULT rather
    than a defect -- the same eight file ids on three copies with three
    different row counts (`studies/minimap/FINDINGS.md` section 3.1).

    A row is identified by FILE ID through the archive's own file-id table, and
    then read: a row index is a fact about the copy, so nothing here may carry
    one. `archive.row()` is one-based and `entries` is positional -- the trap
    `iconset.py` fell into and `datwrite` caught.
    """
    table = file_ids if file_ids is not None else archive_mod.file_id_table(ar)
    got, missing = [], []
    for t in tile_rows:
        row = table.get(t.file_id)
        if row is None:
            missing.append(t)
            continue
        entry = ar.row(row)
        raw = ar.raw(entry)
        if entry.compression == 0:
            head = raw[:ATEX_HEAD]
        else:
            head = gwdat.decompress(raw, out_size=ATEX_HEAD)[0]
        magic, w, h = atex_head(head)
        got.append(Resolved(t, row, magic, w, h, entry.size))
    return got, missing


def open_archive(path=None):
    """The archive to join against, READ-ONLY. `vault/dat_study/Gw.dat` default.

    `resolve_out` refuses that path as a WRITE target and this opens it as a
    read source, which is not a contradiction -- it is the split `datwrite
    --restore` settled: a guard protects what is written, and the pristine
    snapshot is exactly what you want as a source.
    """
    return archive_mod.Archive(
        path or vaultpath.vault_path("dat_study", "Gw.dat"))


# --------------------------------------------------------------------------
# the write guard, following toolkit/mapdata/atex.py's resolve_out
# --------------------------------------------------------------------------

class Refused(SystemExit):
    """A write guard said no. Always names the path and the rule it broke."""


def _inside(path, root):
    """True if `path` is `root` or below it. Case-folded: this is Windows."""
    path = os.path.normcase(os.path.abspath(path))
    root = os.path.normcase(os.path.abspath(root))
    return path == root or path.startswith(root + os.sep)


def resolve_out(path):
    """Where the extracted index may be written. Raises `Refused` otherwise.

    Called BEFORE the sweep runs, so a refused path costs nothing. Order is
    load-bearing exactly as in `atex.resolve_out`: `vault/dat_study` sits
    INSIDE the vault and the vault is an intended destination, so the snapshot
    has to be refused first or the allow swallows it.

    `working_tree_roots()` is imported from `atex` rather than copied: inside a
    git worktree `REPO_ROOT` is not the main checkout, the worktree's `.git` is
    a file pointing at `<main>/.git/worktrees/<name>`, and a refusal that tests
    only this tree lets a write straight into the other one. That discovery is
    subtle enough that a second copy of it would be a second thing to get wrong.
    """
    full = os.path.abspath(path)
    parts = os.path.normcase(full).replace("\\", "/").split("/")
    if "dat_study" in parts:
        raise Refused(
            f"refusing to write to {full}\n"
            f"  vault/dat_study is the SOURCE snapshot every other archive in "
            f"the vault is cut from, and every measurement in studies/ was "
            f"taken against it. Write elsewhere under "
            f"{vaultpath.vault_path('exports')}.")
    if _inside(full, LIVE_INSTALL):
        raise Refused(
            f"refusing to write to {full}\n"
            f"  That is the owner's own install at {LIVE_INSTALL} and it is "
            f"read-only to this project, permanently (CLAUDE.md).")
    try:
        if _inside(full, vaultpath.vault_root()):
            return full
    except SystemExit:
        pass                            # no vault resolvable; fall through
    for root in atex.working_tree_roots():
        if _inside(full, root):
            raise Refused(
                f"refusing to write an extracted client table into a checkout "
                f"of this repository: {full}\n"
                f"  That tree is {root}"
                + (" -- the MAIN checkout, which this worktree shares a "
                   "repository with.\n" if root != os.path.abspath(REPO_ROOT)
                   else "\n")
                + f"  CLAUDE.md's provenance gate keeps bulk extraction out of "
                f"the tree, permanently. Write under "
                f"{vaultpath.vault_path('exports')} or to a scratch directory "
                f"outside every checkout.")
    return full


# --------------------------------------------------------------------------
# the extraction
# --------------------------------------------------------------------------

def image_build(exe_path):
    """(build, image) for the binary actually read. Never a constant.

    Condition 2 of the owner's 2026-08-11 ruling is that the row records THE
    BUILD, and the obvious spelling -- writing `pinned.BUILD` on every row --
    records a constant instead: `--exe` takes any file, and the one path
    `pinned.find()` falls back to is the owner's live install at `C:\\gw`, which
    auto-updates and is therefore not necessarily 38797 at all. Stamping 38797
    on rows read out of an unidentified image is a provenance MISREPORT, which
    is the one class of error this repository cannot retrofit away, and
    `pinned.py`'s own docstring is about exactly that failure.

    So the build comes from `pinned.identify()`, which decides by size and
    sha256 and knows three answers. `unknown` yields a build of None -- the row
    then says it does not know, which a reader can act on, rather than saying
    38797, which a reader cannot.
    """
    kind, detail = pinned.identify(exe_path)
    build = pinned.BUILD if kind in ("pristine", "patched") else None
    return build, f"{kind}: {detail}"


def index_payload(pe, exe_path, tile_rows, gets, grid_rows, resolved=None,
                  missing=(), dat_path=None):
    """The emitted index: one row per tile, provenance per row.

    Condition 3 of the owner's 2026-08-11 ruling is per-row provenance, and it
    is the one nothing can enforce -- so it is spelled out on every row rather
    than hoisted into a header a merge could drop. The row commits IDS and
    OFFSETS, which is what that ruling permits in bulk; no ArenaNet bytes and
    no authored text appear anywhere in it.

    The build and the image identity are MEASURED from `exe_path` (see
    `image_build`), never taken from `pinned.BUILD`.
    """
    build, image = image_build(exe_path)
    by_tier = {g.tier: g for g in gets}
    got = {r.tile.key(): r for r in (resolved or [])}
    rows = []
    for t in tile_rows:
        g = by_tier[t.tier]
        row = t.as_dict()
        row["provenance"] = {
            "source": "client-table",
            "extractor": "toolkit/clientscan/worldmap.py",
            "build": build,
            "image": image,
            "note": (
                f"{t.tier} tile table at VA 0x{g.table_va:08X}, "
                f"{{u32 count, u32 *array, u32 world}} x {g.records}; slot at "
                f"VA 0x{t.slot_va:08X} -> pair record at VA "
                f"0x{t.record_va:08X}; grid dims from {WORLD_TABLE}"
                f"[{t.world}]+0x{g.cx_off:02X}; located by the getter loop at "
                f"VA 0x{g.loop_va:08X}, whose bound is asserted at "
                f"{g.assert_file}:{g.assert_line}"),
        }
        r = got.get(t.key())
        if r is not None:
            row["archive"] = r.as_dict()
        rows.append(row)
    return {
        "exe": exe_path,
        "build": build,
        "image": image,
        "archive": dat_path,
        "getters": [g.as_dict() for g in gets],
        "grids": [g.as_dict() for g in grid_rows],
        "tiles": rows,
        "unresolved": sorted({t.file_id for t in missing}),
    }


# --------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", help="client to read; defaults to the pinned "
                                  "pristine build, and the choice is printed")
    ap.add_argument("--dat", help="archive to join against; defaults to "
                                  "vault/dat_study/Gw.dat")
    ap.add_argument("--tiles", action="store_true", help="print every tile")
    ap.add_argument("--tier", help="restrict --tiles to one tier")
    ap.add_argument("--resolve", action="store_true",
                    help="join every tile to an archive row and read its head")
    ap.add_argument("--rows", type=int, default=12,
                    help="how many tiles to print with --tiles")
    ap.add_argument("--out", help="write the index as JSON; the vault, never "
                                  "the repo (see resolve_out)")
    a = ap.parse_args(argv)

    # BEFORE the sweep, not after: a refused path should cost nothing.
    out_path = resolve_out(a.out) if a.out else None

    exe, why = ((a.exe, "given on the command line") if a.exe else find_exe())
    pe = PE(exe)
    print(f"client: {exe}\n        ({why})")

    try:
        gets = getters(pe)
        wd = world_data(pe)
        print(f"\n{WORLD_TABLE}: file 0x{wd.base:06X}, {wd.count} x "
              f"{wd.stride} B  (via consttable, {wd.count_from})")
        print(f"\n{len(gets)} tile tier(s), located by the getter's shape:\n")
        for g in gets:
            print(f"  {g.tier:12s} table 0x{g.table_va:08X}  "
                  f"{g.records} x {TILE_RECORD_SIZE} B  "
                  f"CX/CY at {WORLD_TABLE}+0x{g.cx_off:02X}/+0x{g.cy_off:02X}  "
                  f"getter 0x{g.loop_va:08X}")
            print(f"  {'':12s} {g.assert_file}:{g.tier_assert_line} "
                  f"`chunk.x < worldData.{g.tier}CX`, "
                  f":{g.assert_line} `offset < files.count`")

        grid_rows = grids(pe, gets, wd)
        closed = sum(1 for g in grid_rows if g.closes)
        print(f"\ngrids: {closed} of {len(grid_rows)} have "
              f"count == CX x CY")
        for g in grid_rows:
            mark = "" if g.closes else "   <- DISAGREES"
            print(f"  {g.tier:12s} world {g.world}  {g.cx:3d} x {g.cy:3d} = "
                  f"{g.cx * g.cy:5d}   count {g.count:5d}   array "
                  f"0x{g.array_va:08X}{mark}")
        silent = sorted(set(range(wd.count))
                        - {g.world for g in grid_rows})
        print(f"  worlds with no tile record in any tier: {silent}")

        tile_rows = tiles(pe, gets, wd, only_tier=a.tier)
        slots = sum(g.count for g in grid_rows
                    if not a.tier or g.tier == a.tier)
        nonzero = sum(1 for t in tile_rows if t.trailer)
        print(f"\ntiles: {len(tile_rows)} non-NULL of {slots} slots; "
              f"{len(set(t.file_id for t in tile_rows))} distinct file ids; "
              f"trailing u32 non-zero on {nonzero}")
        for tier in sorted({t.tier for t in tile_rows}):
            print(f"  {tier:12s} {sum(1 for t in tile_rows if t.tier == tier)}")
    except Refusal as exc:
        print(f"\nREFUSED: {exc}")
        return 2

    resolved, missing, dat = [], [], None
    if a.resolve or out_path:
        dat = a.dat or vaultpath.vault_path("dat_study", "Gw.dat")
        if not os.path.isfile(dat):
            print(f"\nno archive at {dat} -- skipping the join. "
                  f"(RURIK_VAULT / --dat)")
            dat = None
        else:
            ar = open_archive(dat)
            try:
                resolved, missing = resolve(ar, tile_rows)
            finally:
                ar.close()
            dims = {}
            for r in resolved:
                k = (r.tile.tier, r.magic, r.width, r.height)
                dims[k] = dims.get(k, 0) + 1
            print(f"\narchive: {dat}")
            print(f"  {len(resolved)} of {len(tile_rows)} tiles resolve to a "
                  f"row; {len(missing)} do not")
            print(f"  unresolved file ids: "
                  f"{sorted({t.file_id for t in missing})}")
            print(f"  stored bytes: "
                  f"{sum(r.stored for r in resolved):,}")
            for k in sorted(dims, key=lambda k: (k[0], -dims[k])):
                tier, magic, w, h = k
                print(f"  {tier:12s} {magic.decode('latin-1'):6s} "
                      f"{w:4d} x {h:4d}   {dims[k]:4d}")

    if out_path:
        payload = index_payload(pe, exe, tile_rows, gets, grid_rows,
                                resolved, missing, dat)
        Path(out_path).write_text(json.dumps(payload, indent=1),
                                  encoding="utf-8")
        print(f"\nwrote {out_path}: {len(tile_rows)} tiles, provenance per row")

    if a.tiles:
        print()
        for t in tile_rows[:a.rows]:
            print(f"  {t.tier:12s} world {t.world}  ({t.x:3d},{t.y:3d})  "
                  f"pair ({t.id0},{t.id1})  file id {t.file_id}")
        if len(tile_rows) > a.rows:
            print(f"  ... {len(tile_rows) - a.rows} more (--rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
