"""Read the client's own assertions: file, line, and the expression as written.

    python toolkit/clientscan/asserts.py --file ChCliSkill        # one module
    python toolkit/clientscan/asserts.py --grep skillInstance     # by expression
    python toolkit/clientscan/asserts.py --modules                # what exists
    python toolkit/clientscan/asserts.py --at 0x004e6630 --span 3000

WHY THIS EXISTS. Everything else this project can read out of the client is
shapes: how many bytes, what width, which offset. Shapes do not say what a field
MEANS, and meaning is exactly what the reconstructions disagree about. ArenaNet
compiled its assert expressions into the shipping image as ASCII, and those
expressions are written in ArenaNet's own identifiers -- `skill->skillId`,
`hotKey < arrsize(hotKeyState->hotKey)`, `m_trapezoid->portalLeft <
pathMap.portalCount`. That is the closest thing to source code that exists
outside ArenaNet, and it has now settled three questions in this repository that
data-side reasoning could not.

WHAT AN ASSERT LOOKS LIKE. MSVC compiled every one of them from the same four
operations -- push the line, put the file in edx, the expression in ecx, call --
but **not always in that order and not always contiguously**, and this file
claimed otherwise for its first two weeks. The three shapes build 38797 actually
contains, all MEASURED 2026-08-10 and identical on our patched copy:

    A   push  <line>        6A ll             or  68 ll ll ll ll     19620
        mov   edx, <file>   BA <va of "P:\\Code\\...">
        mov   ecx, <expr>   B9 <va of "skill->skillId != 0">
        call  <assert>      E8 <rel32>

    B   push  <line>        the SAME four operations, ecx before edx      75
        mov   ecx, <expr>   B9 ...
        mov   edx, <file>   BA ...
        call  <assert>      E8 <rel32>

    J   push  <line>        a site that shares another site's tail        63
        mov   ecx, <expr>   B9 ...
        jmp   -> the `mov edx` of a shape-B block                EB rr / E9 rel32

Shape J is what a two-branch check compiles to: `ExeArchive.cpp:1905` and `:1906`
sit at 0x0047CE63 and 0x0047CE74, differ only in the line pushed, and the first
jumps into the second's `mov edx / call`. So one epilogue serves several sites,
and the fixed-pattern scan below sees the fall-through one only.

    0047CE63  push 0x771       <- line 1905, jumps over the block below
    0047CE68  mov  ecx, <expr>
    0047CE6D  jmp  0x47ce7e ---------+
    0047CE74  push 0x772       <- line 1906, falls through
    0047CE79  mov  ecx, <expr>       |
    0047CE7E  mov  edx, <file> <-----+  the shared tail
    0047CE83  call 0x487bc0

**19758 sites, not 19620.** Until 2026-08-10 this scanned shape A alone and
reported its count as the census -- `--file ExeArchive --unique` omitted both
sites above with nothing in the output saying a floor was being printed. That is
the same defect `codescan.py` next door was built to prevent, in the tool
`codescan.py` gets its module bounds FROM: an under-count here silently narrows
every `--in <module>` search there.

All three shapes are still found with no disassembler, because all three are
fixed byte patterns anchored on `BA <va of a string starting "P:\\">`. Shape J is
followed by taking the `jmp` -- a two-byte or five-byte relative, resolved
arithmetically -- and every one of the 63 carries the full `push`/`mov ecx`
preamble, which is what says they are the idiom and not a coincidence.

Every one of the 19758 calls the same routine at VA 0x00487bc0. That unanimity is
the check -- a byte pattern this short would otherwise be expected to collide with
unrelated code, and 19758/19758 agreeing on one callee says the matches are real.
The tool asserts it, so a future build that changes the idiom fails loudly
instead of returning a thinner list that still looks plausible.

WHAT IS STILL NOT COUNTED, and it is printed rather than left for a reader to
discover. Three sites (`Cmd.cpp` twice, `OsLock.cpp` once) are `mov edx, <file>`
straight into the call with ecx loaded somewhere no fixed pattern can see; they
are real asserts whose expression this tool cannot read, so they are reported as
a count and never folded into a module's list. `coverage()` returns that number
alongside the per-shape totals, and `main` prints it under every query. A count
with nothing said about its edges is what "96 sites, 60 lines" was.

WHAT IT CANNOT TELL YOU. An assert names an identifier; it does not define it.
`skill->recharge` proves a member of that name is read at that line -- not what
units it is in, and not that the member at any particular offset is the one being
named. Claims built on this are SOURCED (the client's own words) or INFERRED
(our reading of them), never OBSERVED.

READ ONLY. Opens the exe for reading. Standard library only -- no capstone, no
pefile -- because the byte pattern is fixed and this is the tool you want working
on a bare machine.
"""

import argparse
import collections
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from gwpe import PE                                          # noqa: E402
import pinned                                                # noqa: E402

# WHICH CLIENT. `pinned.py` owns that answer for every static-analysis tool in
# this directory, and names the copy it returned so a surprising result can be
# diagnosed in one line. This module used to spell it `C:\gw\Gw.exe` -- the
# owner's live install, which auto-updates and is therefore not necessarily the
# build every address in the studies is measured against. Stdlib, like the rest
# of this file: `pinned` imports nothing but hashlib, os and `vaultpath`.
find_exe = pinned.find

# The one routine every assert site on build 38797 calls.
#
# NO LONGER THE LOOKUP -- `studies/crossbuild/PLAN.md` §4. It was used live, so
# on `2026-04-30_b174de1f2d8d` this module reported 19,680 sites with
# `single-routine=False` and a warning, because the callee it was comparing
# against belongs to the newer image. That is not cosmetic: `asserts.py` supplies
# the module ranges `codescan.py --in` narrows searches to, so an under-count
# propagates silently into every search run inside it, and §8/§9 of
# `test_codescan.py` exist because an under-counting assert scan already produced
# two report rows describing no file in the image.
#
# The callee is now DERIVED, two independent ways that must agree (see
# `Asserts._derive_callee`). This constant stays as a class-(c) expectation under
# §6 of that plan: it is checked on the build it was measured on and going red on
# a new build is correct.
ASSERT_VA_38797 = 0x00487BC0

# The assert routine's own body, as a byte shape -- the second witness. Encodes
# only the /GS cookie mix, three register spills and an address-free `call $+5`
# EIP capture:
#
#   33 c5              xor eax,ebp            ; /GS cookie
#   89 45 fc           mov [ebp-4],eax
#   89 55 ec           mov [ebp-0x14],edx     ; the source-file pointer
#   89 4d e0           mov [ebp-0x20],ecx     ; the expression pointer
#   e8 00 00 00 00     call $+5               ; rel32 is literally zero
#   8f 45 f0 / 54 / 8f 45 f4 / 55 / 8f 45 f8  ; pop EIP, ESP, EBP into locals
#
# Not one address and not one build-varying byte in the 27. The bytes that DO
# differ between the builds -- the absolute /GS cookie VA, the default-file
# string VA -- sit outside the pattern, which is why it survived the 90-day gap
# unchanged. MEASURED: one hit in `.text` on both builds, and one whole-file.
ASSERT_SIG = bytes.fromhex(
    "33c58945fc8955ec894de0e8000000008f45f0548f45f4558f45f8")
ASSERT_SIG_DELTA = 11
ASSERT_PROLOGUE = bytes.fromhex("558bec83ec20a1")   # NOT an anchor -- see below

# How unanimous the call sites must be before their modal target is believed.
# Both vaulted builds are 100.0000% -- one distinct callee over 19,758 and
# 19,680 sites -- so this floor has never yet been the thing deciding anything,
# and it is here so that a build where the idiom genuinely splits refuses
# instead of quietly reporting the more popular half.
CONSENSUS_FLOOR = 0.99


class NoAssertRoutine(SystemExit):
    """The assert callee could not be established. Never a silent fallback."""


def find_assert_callee(pe):
    """(entry_va, entry_off) of the assert routine, by byte shape.

    Refuses on 0 or 2+ hits -- `studies/crossbuild/PLAN.md` §7 rule 1.

    The -11 delta is VERIFIED against the routine's prologue rather than
    trusted, and the prologue is deliberately not the anchor: `ASSERT_PROLOGUE`
    occurs 56 times in `.text` on build 38797 and 57 times on the older build, so
    searching on it and taking the first hit resolves the wrong routine in
    silence. That is the negative control `test_codescan.py` pins.
    """
    hits = pe.find(ASSERT_SIG, ".text")
    if not hits:
        raise NoAssertRoutine(
            "the assert routine's signature is not in this client -- it was "
            "recompiled or the idiom changed.")
    if len(hits) > 1:
        raise NoAssertRoutine(
            f"{len(hits)} matches for the assert-routine signature, expected 1; "
            f"refusing to guess which is the real one.")
    off = hits[0] - ASSERT_SIG_DELTA
    if pe.data[off:off + len(ASSERT_PROLOGUE)] != ASSERT_PROLOGUE:
        raise NoAssertRoutine(
            f"the assert signature matched but the entry at {off:#x} is not the "
            f"expected prologue; the signature's offset into the routine moved.")
    return pe.image_base + pe.off_to_rva(off), off

# The three shapes, named so a row can say how it was found. See the docstring.
SHAPE_EDX_FIRST = "edx-first"      # push / mov edx / mov ecx / call
SHAPE_ECX_FIRST = "ecx-first"      # push / mov ecx / mov edx / call
SHAPE_SHARED_TAIL = "shared-tail"  # push / mov ecx / jmp -> another site's tail


class Assert:
    __slots__ = ("va", "file", "line", "expr", "callee", "shape")

    def __init__(self, va, file, line, expr, callee, shape=SHAPE_EDX_FIRST):
        self.va, self.file, self.line = va, file, line
        self.expr, self.callee, self.shape = expr, callee, shape

    @property
    def module(self):
        """Basename without extension: ChCliSkill, AgMsg, PathDir.

        A LABEL, NOT AN IDENTITY. Nine basenames on build 38797 name two
        different source files each -- `PrApi` is both `Gw\\Pref\\PrApi.cpp` and
        `Engine\\Map\\Props\\PrApi.cpp` -- so this is safe to PRINT beside a line
        number and an expression, and unsafe to GROUP or COUNT by. `modules()`
        keys on `.file` for exactly that reason; `Asserts.collisions()` names the
        nine.
        """
        return self.file.rsplit("\\", 1)[-1].rsplit(".", 1)[0]

    def __repr__(self):
        line = self.line if self.line is not None else "?"
        return f"{self.module}:{line}  {self.expr}"


class Asserts:
    """Every assert in the image, indexed by module and by call site."""

    def __init__(self, path=None):
        path = path or find_exe()[0]
        self.pe = PE(path)
        self.base = self.pe.image_base
        self.items = list(self._scan())
        self.items.sort(key=lambda a: a.va)
        self._by_va = [a.va for a in self.items]
        self.callee_distinct = 0
        self.callee_share = 0.0
        self.callee_witness = "not searched"
        self.assert_va = self._derive_callee()

    # -- string reading -------------------------------------------------
    def cstr(self, va, cap=400):
        off = self.pe.rva_to_off(va - self.base)
        if off is None:
            return None
        blob = self.pe.data[off:off + cap]
        z = blob.find(b"\0")
        if z < 0:
            return None
        blob = blob[:z]
        if not blob or not all(32 <= c < 127 for c in blob):
            return None
        return blob.decode("ascii")

    # -- the scan -------------------------------------------------------
    def _scan(self):
        """Every assert site, in all three shapes. See the docstring.

        Two passes, because shape J cannot be recognised until the shape-B
        epilogues it branches into are known.
        """
        sec = self.pe.section(".text")
        if sec is None:
            raise ValueError("no .text section")
        data = self.pe.data
        lo, hi = sec["rawptr"], sec["rawptr"] + sec["rawsize"]

        out = []
        self.shapes = {SHAPE_EDX_FIRST: 0, SHAPE_ECX_FIRST: 0,
                       SHAPE_SHARED_TAIL: 0}
        # Real assert calls whose expression pointer no fixed pattern reaches,
        # and `mov edx, <P:\...>` sites that are not the assert idiom at all.
        # Both are counted so that "not in the list" never has to mean "we did
        # not look" -- the whole reason this scan was rewritten.
        self.unreadable = []
        self.unmatched = 0
        epilogues = {}                # VA of a shape-B `mov edx` -> (file, callee)

        i = lo
        while True:
            i = data.find(b"\xba", i, hi)
            if i == -1:
                break
            if i + 10 > hi:
                i += 1
                continue
            fname = self.cstr(struct.unpack_from("<I", data, i + 1)[0])
            if not (fname and fname.startswith("P:\\")):
                i += 1
                continue
            va = self.pe.off_to_rva(i) + self.base

            if i + 15 <= hi and data[i + 5] == 0xB9 and data[i + 10] == 0xE8:
                expr = self.cstr(struct.unpack_from("<I", data, i + 6)[0])
                if expr is not None:
                    rel = struct.unpack_from("<i", data, i + 11)[0]
                    line, _push = self._push_before(data, i)
                    out.append(Assert(va, fname, line, expr, va + 15 + rel,
                                      SHAPE_EDX_FIRST))
                    self.shapes[SHAPE_EDX_FIRST] += 1
                else:
                    self.unmatched += 1
            elif data[i + 5] == 0xE8 and i - 5 >= lo and data[i - 5] == 0xB9:
                expr = self.cstr(struct.unpack_from("<I", data, i - 4)[0])
                if expr is not None:
                    rel = struct.unpack_from("<i", data, i + 6)[0]
                    callee = va + 10 + rel
                    line, _push = self._push_before(data, i - 5)
                    out.append(Assert(va, fname, line, expr, callee,
                                      SHAPE_ECX_FIRST))
                    self.shapes[SHAPE_ECX_FIRST] += 1
                    epilogues[va] = (fname, callee)
                else:
                    self.unmatched += 1
            elif data[i + 5] == 0xE8:
                # `mov edx, <file>` straight into the call: a real assert whose
                # expression was loaded out of reach of any fixed pattern.
                rel = struct.unpack_from("<i", data, i + 6)[0]
                self.unreadable.append((va, fname, va + 10 + rel))
            else:
                self.unmatched += 1
            i += 1

        # Pass two: the sites that jump into an epilogue found above instead of
        # falling into it. Anchored on the full preamble -- `push <line>` then
        # `mov ecx, <expr>` then the branch -- which is what separates the
        # idiom from a byte that merely decodes as a `jmp` in the middle of
        # some other instruction. All 63 on build 38797 carry it.
        for opcode, size in ((0xEB, 2), (0xE9, 5)):
            j = lo
            while True:
                j = data.find(bytes([opcode]), j, hi)
                if j == -1:
                    break
                if j + size > hi or j - 5 < lo or data[j - 5] != 0xB9:
                    j += 1
                    continue
                rel = struct.unpack_from("<b" if size == 2 else "<i",
                                         data, j + 1)[0]
                jva = self.pe.off_to_rva(j) + self.base
                target = jva + size + rel
                if target in epilogues:
                    expr = self.cstr(struct.unpack_from("<I", data, j - 4)[0])
                    line, push = self._push_before(data, j - 5)
                    if expr is not None:
                        fname, callee = epilogues[target]
                        # The site IS the push -- there is no `mov edx` of its
                        # own to name it by, and the push is where a reader
                        # looking at the function will find it.
                        site = (self.pe.off_to_rva(push if push is not None
                                                   else j - 5) + self.base)
                        out.append(Assert(site, fname, line, expr, callee,
                                          SHAPE_SHARED_TAIL))
                        self.shapes[SHAPE_SHARED_TAIL] += 1
                j += 1
        return out

    @staticmethod
    def _push_before(data, i):
        """(line, raw offset of the push) for the `push <line>` ahead of `i`.

        The line is None rather than guessed when the bytes before are not a
        push: some sites reuse a register or hoist the push, and a wrong line
        number is worse than no line number when the point of this tool is to
        quote the client accurately.
        """
        if i >= 2 and data[i - 2] == 0x6A:
            return data[i - 1], i - 2
        if i >= 5 and data[i - 5] == 0x68:
            return struct.unpack_from("<I", data, i - 4)[0], i - 5
        return None, None

    # -- the callee, derived ---------------------------------------------
    def _derive_callee(self):
        """The assert routine, from this image, by two independent routes.

        ROUTE 1, and it is the whole answer on its own: every assert site is a
        call, so the modal target of ~19,700 of them IS the assert routine. No
        address is involved. MEASURED on both vaulted builds: exactly ONE
        distinct target, 100.0000% -- 0x00487BC0 on 38797, 0x00487A80 on
        2026-04-30_b174de1f2d8d.

        ROUTE 2 is `find_assert_callee`, a byte shape. It is a CROSS-CHECK: if
        it resolves and disagrees with the consensus, this refuses rather than
        picking one, because two witnesses disagreeing is a fact about the build
        that a caller must not be handed a number past. If the shape is simply
        absent on some future build the consensus still stands and says so --
        the sites voting is a stronger witness than a pattern, and making the
        pattern mandatory would break a working tool for tidiness.
        """
        if not self.items:
            raise NoAssertRoutine(
                f"{self.path}: no assert sites were found at all, so there is no "
                f"callee to derive.\n"
                f"  The three call shapes all missed, which means the idiom "
                f"changed. Re-derive it before\n"
                f"  trusting any 'no assert names X' claim against this build.")
        tally = collections.Counter(a.callee for a in self.items)
        va, n = tally.most_common(1)[0]
        self.callee_distinct = len(tally)
        self.callee_share = n / len(self.items)
        if self.callee_share < CONSENSUS_FLOOR:
            raise NoAssertRoutine(
                f"{self.path}: the assert sites do not agree on one callee -- "
                f"{len(tally)} distinct targets, the most popular holding only "
                f"{self.callee_share:.2%} of {len(self.items)} sites.\n"
                f"  Refusing to report the majority as 'the assert routine'.")
        try:
            sig_va, _ = find_assert_callee(self.pe)
        except NoAssertRoutine as exc:
            self.callee_witness = f"consensus only ({exc})"
            return va
        if sig_va != va:
            raise NoAssertRoutine(
                f"{self.path}: the two derivations disagree -- {len(self.items)} "
                f"call sites point at 0x{va:08X}, the byte signature resolves "
                f"0x{sig_va:08X}.\n"
                f"  One of them is reading the wrong routine and the bytes "
                f"cannot say which, so this is REFUSED.")
        self.callee_witness = "consensus and signature agree"
        return va

    # -- queries --------------------------------------------------------
    def check(self, expect_callee=None):
        """(n_sites, n_distinct_callees, agreed). See the docstring.

        `expect_callee` defaults to the callee DERIVED from this image, so
        `agreed` now answers "do all sites call one routine" on any build. It
        used to default to build 38797's address, which made the answer False on
        every other build for a reason unrelated to the sites.
        """
        if expect_callee is None:
            expect_callee = self.assert_va
        callees = {a.callee for a in self.items}
        return len(self.items), len(callees), callees == {expect_callee}

    def call_sites(self, callee=None):
        """Every `call rel32` in .text that lands on the assert routine.

        THE INDEPENDENT CENSUS, added 2026-08-11, and it exists because
        `unreadable` was wrong by two orders of magnitude. That counter reports
        only the ONE miss the pattern scan can recognise (`mov edx, <file>`
        straight into the call). It said 3. This sweep says the scan is short
        by 370.

        The cause is that all three shapes are CONTIGUOUS byte patterns, so
        anything the compiler schedules between the operand loads and the call
        breaks them. `0x006029BC` is a worked example: it is AgAgent:2366,
        the AGENT_MIN_MOVE_SPEED bound `test_smsgnames.py` quotes, and it carries
        an `fstp st(0)` between the operand loads and the call. Its twin 2367 at
        `0x006029D4` IS read, so the two sit three instructions apart with one
        visible and one invisible -- which is why the shortfall was never noticed.

        This sweep cannot read a single expression, which is exactly the point:
        it does not need to. It counts CALLS, so it is a hard bound the pattern
        scan can be measured against, and it cannot desync because a call to a
        known address is self-anchoring. What it buys is that "no assert names
        X" is now a claim with a stated shortfall instead of a census.
        """
        if callee is None:
            callee = self.assert_va
        # Cached: coverage_lines() runs under every query, and the suite builds
        # this object dozens of times. Sweeping 5.4 MB per call took the whole
        # test run past ten minutes.
        cached = getattr(self, "_call_sites", None)
        if cached is not None and cached[0] == callee:
            return cached[1]
        sec = self.pe.section(".text")
        data = self.pe.data
        lo, hi = sec["rawptr"], sec["rawptr"] + sec["rawsize"]
        out = []
        p = lo
        while True:
            p = data.find(b"\xe8", p, hi - 5)
            if p == -1:
                break
            rel = struct.unpack_from("<i", data, p + 1)[0]
            va = self.base + sec["vaddr"] + (p - lo)
            if (va + 5 + rel) & 0xFFFFFFFF == callee:
                out.append(va)
            p += 1
        self._call_sites = (callee, out)
        return out

    def coverage(self):
        """What the scan found, per shape, and what it knows it could not read.

        The point of returning this rather than just a total: a caller printing
        "96 sites" cannot tell a census from a floor, and for two weeks this
        tool printed a floor. Anything non-zero in `unreadable` means the list
        is short by that much and the shortfall has a name.

        `missed` is the honest version of that. `unreadable` counted only the
        misses the pattern scan can SEE, and a scanner's own estimate of what
        it missed is worth nothing -- `call_sites()` measures against the image
        instead, which is what turned a self-reported 3 into a real 370.
        """
        sites = len(self.call_sites())
        return {"shapes": dict(self.shapes),
                "total": len(self.items),
                "unreadable": len(self.unreadable),
                "unmatched": self.unmatched,
                "call_sites": sites,
                "missed": max(0, sites - len(self.items) - len(self.unreadable))}

    def coverage_lines(self):
        """`coverage()` as the lines every entry point prints under its count."""
        cov = self.coverage()
        out = ["scanned: " + ", ".join(f"{k} {v}" for k, v in cov["shapes"].items())
               + f"  = {cov['total']} sites"]
        if cov["unreadable"]:
            out.append(
                f"NOT counted: {cov['unreadable']} site(s) call the assert "
                f"routine with the expression pointer loaded out of reach of a "
                f"fixed pattern. They are real asserts this tool cannot read, "
                f"so every module list below is short by however many of them "
                f"fall in it. `--unreadable` lists them.")
        if cov["missed"]:
            out.append(
                f"AND SHORT BY {cov['missed']} MORE: an independent sweep finds "
                f"{cov['call_sites']} `call rel32` sites landing on the assert "
                f"routine, against {cov['total']} read + {cov['unreadable']} "
                f"named unreadable. The shapes are contiguous byte patterns and "
                f"the compiler schedules other instructions into them (e.g. an "
                f"`fstp` at 0x006029BC, which is AgAgent:2366). SO EVERY "
                f"\"no assert names X\" ANSWER FROM THIS TOOL IS A FLOOR, NOT A "
                f"CENSUS -- including the module counts below, and including "
                f"`codescan.py --in <module>`, which takes its bounds from here.")
        return out

    def _grouped(self):
        """(rows, spellings) keyed by source FILE. Both queries below use it."""
        cached = getattr(self, "_groups", None)
        if cached is None:
            rows, spell, canon = {}, {}, {}
            for a in self.items:
                key = canon.setdefault(a.file.casefold(), a.file)
                rows.setdefault(key, []).append(a)
                seen = spell.setdefault(key, [])
                if a.file not in seen:
                    seen.append(a.file)
            cached = self._groups = (rows, spell)
        return cached

    def modules(self):
        """Assert sites grouped by SOURCE FILE: {full path: [Assert, ...]}.

        THE FULL PATH, NEVER THE BASENAME, and that is the whole point of this
        method. It grouped by `Assert.module` until 2026-08-11 and the census it
        fed was wrong wherever two source files share one basename. Build 38797
        has nine such collisions and the two largest are the top two rows of the
        report: `Base\\Rtl\\Array.cpp` (2 sites) and `Base\\rtl\\Array.h` (4431)
        were summed into a single row of 4433 printed under the .cpp's path, and
        `List.cpp`/`List.h` into one of 3295. Neither number described any file.

        The small ones are the dangerous ones, because they are plausible.
        `Gw\\Pref\\PrApi.cpp` is the preferences API, 67 sites around 0x00499xxx;
        `Engine\\Map\\Props\\PrApi.cpp` is the props API, 19 sites around
        0x00738xxx. Unrelated modules in unrelated subsystems, 2.4 MB apart. The
        census printed ONE row -- `86  P:\\Code\\Gw\\Pref\\PrApi.cpp` -- so a
        reader asking what the client asserts about props found no such module
        and would have read that as absence. The representative path was
        `mods[m][0].file`, i.e. whichever colliding file happened to hold the
        lowest VA, so which of the two names a row was decided by layout.

        CASE-ONLY SPELLINGS ARE MERGED, and named rather than picked. The image
        contains both `Base\\Compress\\CmpIo.h` and `Base\\compress\\CmpIo.h`:
        the build was on Windows, whose paths are case-insensitive, so that is
        one file reached by two translation units spelling a directory
        differently -- 65 sites, not 31 and 34. Merging it is a fact about the
        filesystem and not a guess. But silently choosing one of the two
        spellings to print is the same defect one level down, so every spelling
        seen is kept and `spellings()` returns them. The key is the first in VA
        order; 864 rows, 19758 sites, on build 38797.
        """
        return self._grouped()[0]

    def spellings(self):
        """{key path: [every spelling of it in the image]} for `modules()`."""
        return self._grouped()[1]

    def collisions(self):
        """{basename: [the source files sharing it]}, for the >1 cases only.

        Printed under `--modules` because the collision does not stop mattering
        once the census is right: `--file` and `codescan.py --in` take a NAME and
        match it as a SUBSTRING, so a reader who reads `PrApi` off the census and
        types it gets both modules pooled. `by_module` at least sorts them apart
        under `--file`; `codescan.module_bounds` takes min and max VA and returns
        0x00499B01..0x0073943A, 2.4 MB of mostly unrelated .text, which is a
        silent WIDENING of every field search run inside it. Nine on build 38797.
        """
        by = {}
        for path in self.modules():
            name = path.rsplit("\\", 1)[-1].rsplit(".", 1)[0]
            by.setdefault(name.lower(), []).append(path)
        return {k: sorted(v) for k, v in by.items() if len(v) > 1}

    def by_module(self, name):
        name = name.lower()
        return [a for a in self.items
                if name in a.module.lower() or name in a.file.lower()]

    def grep(self, pattern):
        rx = re.compile(pattern, re.I)
        return [a for a in self.items if rx.search(a.expr)]

    def direct_callers(self, target):
        """Every `call rel32` in .text that lands on `target`.

        Lives here because it is the question you ask immediately after an
        assert names something: who reaches this code? It is at its most
        useful in the negative -- opcode 211's write path has exactly ONE
        caller, its own message handler, which is how we know nothing else
        fills the array it writes. Direct calls only; an indirect call through
        a vtable or function-pointer table will not appear, so an empty result
        is "no direct caller", not "no caller".
        """
        sec = self.pe.section(".text")
        if sec is None:
            return []
        lo, size = sec["rawptr"], sec["rawsize"]
        blob = self.pe.data[lo:lo + size]
        base = self.base + sec["vaddr"]
        out = []
        # `- 4`, not `- 5`: a `call rel32` at the last legal offset needs bytes
        # i..i+4, so `range(len - 5)` stopped one window early and could not
        # see a call in the final five bytes of .text.
        for i in range(len(blob) - 4):
            if blob[i] == 0xE8:
                rel = struct.unpack_from("<i", blob, i + 1)[0]
                va = base + i
                if va + 5 + rel == target:
                    out.append(va)
        return out

    def near(self, va, span=2000):
        """Asserts whose call site lies in [va, va+span).

        The cheapest way to ask "what does this function think it is doing":
        an assert inside it names the file it was compiled from and usually a
        member of the struct it is walking.
        """
        import bisect
        lo = bisect.bisect_left(self._by_va, va)
        hi = bisect.bisect_left(self._by_va, va + span)
        return self.items[lo:hi]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", default=None,
                    help="client to read; defaults to the pinned pristine "
                         "build, and the choice is printed")
    ap.add_argument("--file", help="module substring, e.g. ChCliSkill")
    ap.add_argument("--grep", help="regex over the assert expression")
    ap.add_argument("--at", help="VA; show asserts inside the function there")
    ap.add_argument("--span", type=lambda s: int(s, 0), default=2000)
    ap.add_argument("--modules", action="store_true",
                    help="every source module that asserts, by count")
    ap.add_argument("--callers", help="VA; every direct call site")
    ap.add_argument("--unique", action="store_true",
                    help="collapse repeated expressions")
    ap.add_argument("--unreadable", action="store_true",
                    help="the assert calls whose expression this tool cannot "
                         "read, which is what the site counts are short by")
    a = ap.parse_args()

    exe, why = ((a.exe, "given on the command line") if a.exe else find_exe())
    if not os.path.exists(exe):
        sys.exit(f"no such file: {exe}")
    print(f"client: {exe}\n        ({why})\n")
    az = Asserts(exe)
    n, ncallee, agreed = az.check()
    print(f"{exe}: {n} assert sites, {ncallee} distinct callee(s), "
          f"single-routine={agreed}")
    print(f"  assert routine 0x{az.assert_va:08X}, derived -- "
          f"{az.callee_witness}, {az.callee_share:.4%} of sites")
    # The pinned constant, demoted to a cross-check and scoped by hash so it is
    # only asserted against the build it was measured on.
    what, _ = pinned.identify(exe, build=pinned.BUILD)
    if what in ("pristine", "patched"):
        same = az.assert_va == ASSERT_VA_38797
        print(f"  cross-check vs the pinned build-{pinned.BUILD} address "
              f"0x{ASSERT_VA_38797:08X}: {'agrees' if same else 'DISAGREES'}")
    for line in az.coverage_lines():
        print(f"  {line}")
    if not agreed:
        print("  WARNING: the idiom moved on this build; treat results as partial")

    if a.unreadable:
        print(f"\n{len(az.unreadable)} assert call(s) with an unreadable "
              f"expression -- real sites, absent from every list above:")
        for va, fname, callee in az.unreadable:
            print(f"  0x{va:08x}  {fname}  -> 0x{callee:08x}")
        return 0

    if a.modules:
        # One row per source FILE. The count and the path on a row are now
        # necessarily about the same file; see `Asserts.modules()` for the nine
        # basenames that made that false, and why the biggest row of the old
        # report described no file at all.
        mods, spell = az.modules(), az.spellings()
        for m in sorted(mods, key=lambda k: (-len(mods[k]), k.lower())):
            alt = [s for s in spell[m] if s != m]
            also = f"   (also spelled {', '.join(alt)})" if alt else ""
            print(f"{len(mods[m]):5}  {m}{also}")
        print(f"\n{len(mods)} source file(s), {sum(len(v) for v in mods.values())} "
              f"site(s) -- one row per file, keyed on the full path")
        coll = az.collisions()
        if coll:
            # Not a leftover of the bug: `--file` and `codescan.py --in` still
            # take a substring, so naming one of these bounds two modules.
            print(f"\n{len(coll)} basename(s) below name more than one file, so "
                  f"`--file <name>` and `codescan.py --in <name>` pool them:")
            for name in sorted(coll):
                for p in coll[name]:
                    print(f"  {len(mods[p]):5}  {p}")
        return 0

    if a.callers:
        target = int(a.callers, 0)
        sites = az.direct_callers(target)
        print(f"{len(sites)} direct caller(s) of 0x{target:08x}")
        for s in sites:
            ctx = az.near(s - 3000, 3000)
            where = f"  (nearest earlier assert: {ctx[-1]})" if ctx else ""
            print(f"  0x{s:08x}{where}")
        return 0

    if a.at is not None:
        hits = az.near(int(a.at, 0), a.span)
    elif a.file:
        hits = az.by_module(a.file)
    elif a.grep:
        hits = az.grep(a.grep)
    else:
        ap.error("give --file, --grep, --at or --modules")

    seen = set()
    shown = 0
    for h in sorted(hits, key=lambda x: (x.file, x.line or 0, x.va)):
        if a.unique:
            k = (h.file, h.expr)
            if k in seen:
                continue
            seen.add(k)
        shown += 1
        ln = f"{h.line}" if h.line is not None else "?"
        tail = "" if h.shape == SHAPE_EDX_FIRST else f"   [{h.shape}]"
        print(f"0x{h.va:08x}  {h.module}:{ln:<6} {h.expr}{tail}")

    # The count, and what it is a count OF. `--file ExeArchive --unique` used to
    # end at "96 site(s)" while omitting every shared-tail site in the module,
    # which reads as a census and was a floor.
    by_shape = {}
    for h in hits:
        by_shape[h.shape] = by_shape.get(h.shape, 0) + 1
    print(f"\n{len(hits)} site(s)"
          + (f", {shown} shown after --unique" if a.unique else "")
          + (" -- " + ", ".join(f"{k} {v}" for k, v in sorted(by_shape.items()))
             if by_shape else ""))
    # WHICH FILES that count is over. `--file` matches a substring against the
    # basename AND the full path, so one name can pool two modules: `--file
    # PrApi` prints 86 sites drawn from a preferences module and a props module
    # 2.4 MB apart, every row labelled `PrApi:<line>` because the label is the
    # basename. The rows were always sorted by path so they printed contiguously,
    # but the total underneath them said nothing, and the total is what gets
    # quoted. Only printed when there is more than one, so the common case is
    # unchanged.
    files = {h.file for h in hits}
    if len(files) > 1:
        per = {}
        for h in hits:
            per[h.file] = per.get(h.file, 0) + 1
        why = f" -- `{a.file}` matched each as a substring" if a.file else ""
        print(f"across {len(files)} source file(s){why}:")
        for path in sorted(per, key=lambda p: -per[p]):
            print(f"  {per[path]:5}  {path}")
    missing = [u for u in az.unreadable if u[1] in files]
    if missing:
        print(f"and {len(missing)} further assert call(s) in these files whose "
              f"expression is unreadable, so this count is short by that much:")
        for va, fname, _callee in missing:
            print(f"  0x{va:08x}  {fname}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
