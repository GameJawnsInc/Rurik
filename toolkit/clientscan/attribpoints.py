#!/usr/bin/env python3
"""Read `s_attribPoints` -- and its `arrsize` -- out of Gw.exe, structurally.

    python toolkit/clientscan/attribpoints.py
    python toolkit/clientscan/attribpoints.py --all-builds
    python toolkit/clientscan/attribpoints.py --exe <path>

Python 3 standard library only. `attribtable.py` next door is the model this
copies: locate by a CONJUNCTION of structural facts, never by an address, so
the answer survives an ArenaNet build. No disassembler either -- every pattern
here is fixed bytes, which keeps this tool working on a bare machine per
CLAUDE.md carve-out (1)'s scope.

WHAT THIS SETTLES, and it started as a crash. A loopback harness session on
build 38833 killed the client with

    Assertion: level < arrsize(s_attribPoints)
    P:\\Code\\Gw\\Char\\CharData.cpp(202)

`arrsize` was the number nobody had. `consttable.py` carried this table as
**14 x 4** with `pad=None` -- no left-edge witness -- and its own note flagged
the leading `5` as looking like "dead data". It is not dead data and the count
is not 14: **`arrsize(s_attribPoints)` is 13**, the client says so in its own
bound check, and the `5` belongs to the array next door. §"THE OFF-BY-ONE"
below. `consttable.py`'s row is corrected to 13 and now cites this module.

THE TABLE. 13 dwords, and only the first twelve are values:

    s_attribPoints = { 1, 2, 3, 4, 5, 6, 7, 9, 11, 13, 16, 20, -1 }

Indexed by an attribute's RANK, not by a character level, despite ArenaNet
naming the parameter `level`. `s_attribPoints[r]` is the cost in attribute
points of raising an attribute from rank `r` to rank `r+1`; the `-1` at [12]
says rank 12 is the last one. The twelve values are the game's published
per-rank costs (UPSTREAM, and `consttable.py`'s row records the same
corroboration independently) and they sum to 97, retail's cost of a rank-12
attribute.

TWO ACCESSORS, and the difference between them is the whole trick:

    0x0091D560  CharData:202   level ? s_attribPoints[level - 1] : 0
    0x0091D5A0  CharData:208   s_attribPoints[level]

both `cmp esi, 0Dh; jb` first -- that `0Dh` IS `arrsize`, compiled in. MSVC
folded the `- 1` of the first one into the displacement, so it addresses
`[esi*4 + base - 4]` and its instruction encodes an address FOUR BYTES BELOW
the array. Read that displacement as the base -- which is the obvious thing to
do, and what the recon behind `consttable.py`'s row effectively did -- and you
get a table that starts one element early and has to be 14 long to reach its
anchor. Both readings close on the anchor string, so closure cannot separate
them; the bound check can, and so can the neighbour.

THE OFF-BY-ONE, refuted three independent ways. Any one could be a coincidence:

  1. **The client's own `arrsize`.** Both accessors compare against 13 before
     the lookup, and the assert expression at that exact site is literally
     `level < arrsize(s_attribPoints)`. A 14-element array whose every accessor
     rejects index 13 is not a 14-element array.
  2. **The unbiased accessor.** `CharData:208` applies no `- 1`, so its
     displacement is the base with nothing folded into it -- and it sits
     exactly 4 above `CharData:202`'s.
  3. **The neighbour's right edge.** `s_appearanceSlot` is located here by the
     same method (its own asserts at `CharData:165/178`, its own `cmp esi, 8`,
     and the `lea edi,[esi+esi*2]` that makes its stride 12). Its 8 records of
     12 bytes end at exactly the base this module reports, so the dword the old
     reading absorbed is that table's last column, not a stray `5`.

and then the CONTENT agrees: on the 13-element reading the array is a strictly
increasing run of twelve terminated by `-1`, which is what a cost table looks
like. On the 14-element reading it opens with a `5` that breaks the run.

REFUTABILITY. Every leg above is asserted, so this module goes red rather than
drifting: if a build moves the two accessors apart, changes the bound, breaks
the `base + 13*4 == anchor` closure, or moves `s_appearanceSlot`'s right edge
off the base, it FAILS and names which leg. `test_attribpoints.py` runs it over
every build in `pinned.BUILDS` -- three ArenaNet builds, so the structural
claim is checked out of sample rather than on the one image it was written for.

READ ONLY. Opens the client for reading and does nothing else. The install at
`C:\\gw` is the owner's own and is never written, patched or launched.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import pinned                                                    # noqa: E402
from gwpe import PE                                              # noqa: E402

find_exe = pinned.find

# ArenaNet's own strings, used as ANCHORS the way `asserts.py` and
# `consttable.py` use them -- we search for them, we do not reproduce them as
# data. The file path is also the array's right-edge anchor: MSVC emits a
# translation unit's static data then its string literals in source order.
FILE_ANCHOR = b"P:\\Code\\Gw\\Char\\CharData.cpp\x00"
EXPR_POINTS = b"level < arrsize(s_attribPoints)\x00"
EXPR_SLOT = b"slot < arrsize(s_appearanceSlot)\x00"

EXPECTED_ARRSIZE = 13            # what build 38519/38797/38833 all compile in
EXPECTED_SLOTS = 8               # arrsize(s_appearanceSlot)
SLOT_STRIDE = 12                 # 3 columns x 4, from `lea edi,[esi+esi*2]`
SENTINEL = -1


class NotFound(Exception):
    """A structural leg did not hold. Never fall back to an address."""


# --------------------------------------------------------------- PE helpers

class Image:
    def __init__(self, path):
        self.path = str(path)
        self.pe = PE(self.path)
        self.d = self.pe.data
        self.base = self.pe.image_base

    def off(self, va):
        return self.pe.rva_to_off(va - self.base)

    def va(self, off):
        rva = self.pe.off_to_rva(off)
        return None if rva is None else self.base + rva

    def u32(self, va):
        o = self.off(va)
        if o is None:
            return None
        return struct.unpack_from("<I", self.d, o)[0]

    def i32(self, va):
        v = self.u32(va)
        return None if v is None else struct.unpack("<i", struct.pack("<I", v))[0]

    def find_string(self, needle):
        """VA of a string that occurs EXACTLY once. Ambiguity is a refusal."""
        hits, at = [], -1
        while True:
            at = self.d.find(needle, at + 1)
            if at < 0:
                break
            va = self.va(at)
            if va is not None:
                hits.append(va)
        if not hits:
            raise NotFound(f"anchor {needle[:40]!r} is not in this image")
        if len(hits) > 1:
            raise NotFound(f"anchor {needle[:40]!r} occurs {len(hits)} times; "
                           "refusing to guess which one anchors the table")
        return hits[0]

    def text_span(self):
        s = self.pe.section(".text")
        return s["rawptr"], s["rawptr"] + s["rawsize"]

    def sites_loading(self, va):
        """Every `mov ecx, imm32` (B9) in .text whose immediate is `va`.

        That is the assert-expression load of MSVC's shape A/B, the same
        anchor `asserts.py` scans on. Fixed bytes, no disassembler.
        """
        pat = b"\xb9" + struct.pack("<I", va)
        lo, hi = self.text_span()
        out, at = [], lo - 1
        while True:
            at = self.d.find(pat, at + 1, hi)
            if at < 0:
                return out
            out.append(self.va(at))


# ------------------------------------------------------ the two accessors

def _bound_before(img, site_va, window=0x30):
    """The `cmp esi, imm8` / `jb` guarding an assert site, as (imm, va).

    Searched backwards over a short window rather than assumed at a fixed
    offset, because the `push <line>` before the assert is 2 bytes for a line
    under 128 and 5 bytes above it -- CharData:202 is 0xCA and CharData:165 is
    0xA5, so both encodings occur in this one file.
    """
    for back in range(6, window):
        va = site_va - back
        o = img.off(va)
        if o is None:
            continue
        if img.d[o] == 0x83 and img.d[o + 1] == 0xFE and img.d[o + 3] == 0x72:
            return img.d[o + 2], va
    raise NotFound(f"no `cmp esi, imm8; jb` within {window} bytes before "
                   f"0x{site_va:08X} -- the guard shape moved")


def _index_disp_after(img, site_va, window=0x40, sib=0xB5):
    """The `mov eax, [esi*4 + disp32]` after an assert site, as (disp, va).

    `8B 04 B5` is `mov eax, [esi*4 + disp32]` (SIB 0xB5 = scale 4, index esi,
    no base). The default is that; `sib` lets the caller ask for another index
    register -- 0xBD is edi*4, which is what `s_appearanceSlot` uses.
    """
    for fwd in range(0, window):
        va = site_va + fwd
        o = img.off(va)
        if o is None:
            continue
        if img.d[o] == 0x8B and img.d[o + 1] == 0x04 and img.d[o + 2] == sib:
            return struct.unpack_from("<I", img.d, o + 3)[0], va
    raise NotFound(f"no scaled-index load within {window} bytes after "
                   f"0x{site_va:08X} -- the lookup shape moved")


def locate(img):
    """Everything this module claims about `s_attribPoints`, or raise.

    The return dict carries the WITNESSES as well as the answer, because a
    number with no witness is what produced the 14 this corrects.
    """
    expr = img.find_string(EXPR_POINTS)
    anchor = img.find_string(FILE_ANCHOR)
    sites = img.sites_loading(expr)
    if len(sites) != 2:
        raise NotFound(
            f"expected exactly 2 assert sites naming s_attribPoints, found "
            f"{len(sites)}: {[hex(s) for s in sites]}. Both accessors are "
            f"needed -- the biased/unbiased PAIR is what fixes the base.")

    bounds, disps = [], []
    for s in sorted(sites):
        imm, cmp_va = _bound_before(img, s)
        disp, ld_va = _index_disp_after(img, s)
        bounds.append((imm, cmp_va))
        disps.append((disp, ld_va))

    if bounds[0][0] != bounds[1][0]:
        raise NotFound(f"the two accessors disagree about arrsize: "
                       f"{bounds[0][0]} vs {bounds[1][0]}")
    arrsize = bounds[0][0]

    lo, hi = sorted(d for d, _ in disps)
    if hi - lo != 4:
        raise NotFound(
            f"the two lookup displacements are 0x{lo:08X} and 0x{hi:08X}, "
            f"{hi - lo} bytes apart. Exactly 4 is the whole claim: one "
            f"accessor is `[level - 1]` with the -1 folded into the "
            f"displacement, the other is `[level]` and is the true base.")
    base = hi

    # Leg 1: MSVC source-order closure. The array's last byte must abut the
    # translation unit's own __FILE__ string.
    end = base + arrsize * 4
    if end != anchor:
        raise NotFound(
            f"base 0x{base:08X} + {arrsize} x 4 = 0x{end:08X}, but the "
            f"CharData.cpp anchor is at 0x{anchor:08X}. The table does not "
            f"close on its own source path.")

    values = [img.i32(base + 4 * i) for i in range(arrsize)]
    if values[-1] != SENTINEL:
        raise NotFound(f"last element is {values[-1]}, not {SENTINEL} -- the "
                       f"terminator this table is supposed to end on")
    run = values[:-1]
    if any(b <= a for a, b in zip(run, run[1:])):
        raise NotFound(f"the {len(run)} values before the sentinel are not "
                       f"strictly increasing: {run}. A cost table is.")

    # Leg 3: the neighbour's right edge, derived by the same method.
    #
    # This REFUSES rather than reporting a flag, and the difference is the
    # whole reason this module exists. `consttable.py` carried this table as
    # 14 x 4 with a left edge it could not check, and nothing went red -- a
    # corroboration that cannot fail corroborates nothing. So the leg either
    # holds or the answer is withheld.
    slot = locate_appearance_slot(img)
    slot_end = slot["base"] + slot["count"] * SLOT_STRIDE
    if slot_end != base:
        raise NotFound(
            f"s_appearanceSlot ends at 0x{slot_end:08X} "
            f"({slot['count']} x {SLOT_STRIDE} from 0x{slot['base']:08X}) but "
            f"s_attribPoints starts at 0x{base:08X}. The left-edge witness "
            f"disagrees with the accessor, so the base is not settled. If a "
            f"build ever 8-aligns this table the gap will be exactly +4 and "
            f"benign -- but that is a NEW measurement to make deliberately, "
            f"not a tolerance to widen here; consttable.py's `pad` is a "
            f"declared number for the same reason.")

    return {
        "arrsize": arrsize,
        "base": base,
        "values": values,
        "costs": run,
        "total_to_max": sum(run),
        "anchor": anchor,
        "expr_string": expr,
        "sites": {"biased": min(sites), "unbiased": max(sites)},
        "biased_disp": lo,
        "neighbour": slot,
        "neighbour_end": slot_end,
        "neighbour_abuts": slot_end == base,
    }


def locate_appearance_slot(img):
    """`s_appearanceSlot`, needed only as the left-edge witness.

    Same three moves: find the assert expression, read the `cmp esi, imm8`
    that guards it, read the scaled load after it. The stride is 12 rather
    than 4 because the index is tripled first -- `lea edi, [esi + esi*2]`,
    bytes `8D 3C 76` -- and that byte pattern is CHECKED rather than assumed,
    since the stride is what turns 8 records into a right edge.
    """
    expr = img.find_string(EXPR_SLOT)
    sites = img.sites_loading(expr)
    if not sites:
        raise NotFound("no assert site names s_appearanceSlot")
    imm, _ = _bound_before(img, sites[0])

    # The x3 must be present between the guard and the lookup, or `stride 12`
    # is an assumption rather than a reading.
    lo = img.off(sites[0])
    if img.d.find(b"\x8d\x3c\x76", lo, lo + 0x40) < 0:
        raise NotFound("no `lea edi,[esi+esi*2]` after the s_appearanceSlot "
                       "guard -- the x3 that makes the stride 12 is gone")

    # Its columns are read through edi*4 (SIB 0xBD). Collect every column
    # displacement in the function and take the lowest as the base.
    cols = set()
    at = lo
    end = lo + 0x120
    while at < end:
        # `8B 0C BD d32` mov ecx,[edi*4+d]  /  `39 34 BD d32` cmp [edi*4+d],esi
        for pre in (b"\x8b\x0c\xbd", b"\x39\x34\xbd", b"\x8b\x04\xbd"):
            if img.d[at:at + 3] == pre:
                cols.add(struct.unpack_from("<I", img.d, at + 3)[0])
        at += 1
    if not cols:
        raise NotFound("found no edi*4 column loads for s_appearanceSlot")
    return {"base": min(cols), "count": imm, "columns": sorted(cols)}


# ---------------------------------------------------------------- reporting

def describe(img, r) -> str:
    out = [
        f"s_attribPoints   base 0x{r['base']:08X}   arrsize {r['arrsize']}"
        f"   ({r['arrsize'] * 4} bytes)",
        f"  values           {r['values']}",
        f"  costs (rank 1..{len(r['costs'])})  {r['costs']}"
        f"   sum {r['total_to_max']}",
        "",
        "  witnesses:",
        f"    bound check      cmp esi, {r['arrsize']}  in BOTH accessors"
        f"  (0x{r['sites']['biased']:08X}, 0x{r['sites']['unbiased']:08X})",
        f"    unbiased load    [esi*4 + 0x{r['base']:08X}]   CharData:208",
        f"    biased load      [esi*4 + 0x{r['biased_disp']:08X}]"
        f"   CharData:202, the -1 folded in",
        f"    right edge       0x{r['base']:08X} + {r['arrsize']}*4"
        f" = 0x{r['anchor']:08X}, the CharData.cpp path",
        f"    left edge        s_appearanceSlot 0x{r['neighbour']['base']:08X}"
        f" + {r['neighbour']['count']}*{SLOT_STRIDE}"
        f" = 0x{r['neighbour_end']:08X}"
        + ("  == base" if r["neighbour_abuts"] else "  != base  <-- BROKEN"),
    ]
    return "\n".join(out)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--exe", default=None,
                   help="client binary to read (read-only); defaults to the "
                        "pinned pristine build")
    p.add_argument("--all-builds", action="store_true",
                   help="run over every build in pinned.BUILDS -- the "
                        "out-of-sample check that this is structural")
    p.add_argument("--json", action="store_true")
    a = p.parse_args(argv)

    targets = []
    if a.all_builds:
        for b in pinned.BUILDS:
            try:
                exe, why = pinned.find(build=b.number)
            except SystemExit as exc:
                print(f"build {b.number}: {exc}", file=sys.stderr)
                continue
            targets.append((exe, f"build {b.number} -- {why}"))
    else:
        exe, why = (a.exe, "given on the command line") if a.exe else find_exe()
        targets.append((exe, why))

    payload, bad = [], 0
    for exe, why in targets:
        print(f"client: {exe}\n        ({why})", file=sys.stderr)
        img = Image(exe)
        try:
            r = locate(img)
        except NotFound as exc:
            bad += 1
            print(f"REFUSED: {exc}\n", file=sys.stderr)
            continue
        if not a.json:
            print(describe(img, r))
            print()
        payload.append({"exe": str(exe), **{k: v for k, v in r.items()}})

    if a.json:
        print(json.dumps(payload, indent=1))
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
