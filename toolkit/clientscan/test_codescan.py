#!/usr/bin/env python3
"""Check studies/enemy/PLAN.md §6q against the binary it was read from.

    python toolkit/clientscan/test_codescan.py

§6q says attacking was blocked on a single message, and every load-bearing claim
in it is an address. Addresses rot silently: a build changes, a tool's decoding
changes, and the study becomes a confident description of a binary nobody has
re-read. This makes each claim executable.

Nine of the ten sections can fail for the right reason:

  * §2 pins that `+0xEC` and `+0xF0` have exactly TWO writers each and where
    they are. §6o reported ZERO writers image-wide and that was the finding
    that stalled the arc for a session, so a regression to "none" here is the
    single most valuable failure this file can produce.
  * §3 pins the chain from the message handler to the setter as UNIQUE at every
    hop. "Exactly one caller" is what licenses §6q's flat claim that 0x0035 is
    the only way to set an attack speed; if any hop grows a second caller that
    sentence is no longer true.
  * §4 pins ArenaNet's own words -- the argument names `base` and `modifier`
    and the source path -- which is what makes the naming SOURCED rather than
    ours.
  * §5 pins the prefix-shadow dedup with a field that provably duplicates
    without it: `+0x1B8` reads as 18 instructions undeduped and 11 real ones.
  * §6 cross-checks the OTHER decoder in this directory. `avevents.py` is
    stdlib and hand-rolls x86 instruction lengths, which is what keeps
    studies/skillcast §16 checkable on a bare machine -- and is also exactly
    the kind of table that is subtly wrong for years, because a wrong length
    does not error, it desynchronises. Every boundary it produces is compared
    against capstone's over the same ranges. Verified refutable: setting
    `push imm8` to 3 bytes instead of 2 turns this section red and names 27
    addresses.
  * §7 pins the three under-reporting defects a reservation-safety pass found
    on 2026-08-10, each at a named address with a known-good answer: the disp8
    store at 0x00478FB8 that `--field 0xE --in ExeArchive` could not encode a
    search for, the unaligned xref at 0x00478CF6 that `p % 4 == 0` skipped, and
    the two ExeArchive assert sites compiled into a shared tail block. §2 and
    §6 catch a regression in what the scan finds; §7 catches one in what it
    looks AT, which is the failure mode that produces a confident zero.
  * §8 pins that the assert census names the file it counted. It grouped by
    BASENAME until 2026-08-11, and nine basenames on this build name two source
    files each, so nine rows summed two modules and printed the total under one
    of their paths while the other vanished from the census. Its first check is
    the negative control -- the collision itself -- and it reproduces the old
    grouping inline so 67/19 is a difference between two live answers.
  * §9 pins the same ambiguity one tool downstream: `module_bounds` matches a
    substring, so `--in PrApi` silently WIDENS to 2.4 MB spanning two unrelated
    modules. §7 catches the range being narrowed; §9 catches it being stretched.
  * §10 is §7's defect a third time and from a new direction, found 2026-08-13:
    `--field` searched MEMORY OPERANDS and nothing else, so `--field 0x6bc`
    answered 14 without `0x00813AD1 add ecx, 0x6bc` -- the writer reached from
    GAME_SMSG 0x00B6's handler, i.e. the writer of the field that search was
    run to find. The displacement-only rule is reproduced inline and required
    to reach 14 and to MISS that address, so the 19 beside it is a difference
    between two live answers. Its other half is the controls on the new `A`
    class, because widening `A` is the lazy way to pass.

§1 is a guard, not a check: everything below is measured against one build.

THE VERDICT goes through `toolkit/checks.py` like every other test in CLAUDE.md's
suite, because this file used to print its own `[PASS] all checks passed` banner
and a private banner is exactly what cannot report a section that stopped
running. See the floor comment below for the two numbers and where they came
from.

THE DEPENDENCY, and why a bare machine skips rather than fails. Everything that
disassembles -- §1, §2, §4, §5, §6 and the first half of §3 -- needs capstone and
pefile, the carve-out CLAUDE.md grants this directory. A machine without them is
a degraded environment rather than a defect, so those sections declare
`LEDGER.skip(...)` and the verdict prints what was not measured. What still runs
is the second half of §3: `msgshape.py` reads the client's own dispatch tables
through `gwpe`, stdlib only, no disassembler involved.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import asserts as AZ                                          # noqa: E402
import checks                                                 # noqa: E402
import msgshape as MS                                         # noqa: E402
import pinned                                                 # noqa: E402

# `codescan.py` sys.exit()s at import when capstone or pefile is missing, so the
# question has to be asked BEFORE importing it. Otherwise a bare machine dies on
# an import with a bare process exit that no ledger ever sees, which is the same
# unreported non-result checks.py exists to refuse.
try:
    import capstone                                           # noqa: F401
    import pefile                                             # noqa: F401
    HAVE_CAPSTONE = True
except ImportError:                                           # pragma: no cover
    HAVE_CAPSTONE = False

if HAVE_CAPSTONE:
    import codescan as CS                                     # noqa: E402

NO_CAPSTONE = "needs capstone and pefile: python -m pip install capstone pefile"

BUILD = 38797
EXE_BYTES = 10_483_904

# 106 checks in a green run with capstone present, MEASURED 2026-08-13 against
# the pinned pristine 38797 -- the banner's own total, not a count of `check(`
# lines: 2 in §1, 5 in §2, 9 in §3, 6 in §4, 6 in §5, 3 in §6, 26 in §7, 19 in
# §8, 8 in §9, 22 in §10. None of it is fixture-dependent: every section reads
# that one binary and every loop is over a tuple written into this file, so a
# capstone run scoring fewer has had a section stop executing rather than found
# less data.
#
# Without capstone, §3's stdlib half, §7b's and all of §8: 35 checks, measured
# the same day by blocking the import. UNCHANGED by §10, which needs a
# disassembler for every one of its claims and declares one skip. Hence two
# floors rather than one. A flat 35 would let a capstone run lose the whole of
# §2 -- the two-writers claim, the most valuable failure this file can produce --
# and still print green, which is precisely the partial vacuity checks.py was
# written to name.
#
# The capstone number went up on 2026-08-10 with §7 (3 -> 16 on the stdlib
# side), on 2026-08-11 with §8 and §9, and on 2026-08-13 with §10 plus one check
# added to §5 (83 -> 106). The stdlib floor takes the whole of §8 because
# `asserts.py` is stdlib on purpose: its census is checkable on a bare machine,
# and a wrong census is what §9's bounds are computed from.
FLOOR_WITH_CAPSTONE = 106
FLOOR_STDLIB_ONLY = 35

LEDGER = checks.Ledger(
    "codescan vs studies/enemy §6q",
    floor=FLOOR_WITH_CAPSTONE if HAVE_CAPSTONE else FLOOR_STDLIB_ONLY)

check = checks.adopt(LEDGER)


def eq(got, want, label):
    return check(got == want, label, "" if got == want else f"got {got!r}, want {want!r}")


def section_1(exe, img):
    """The module bounds every field search below is restricted to.

    Returns (lo, hi), or (None, None) when the sections that need them must sit
    this run out.
    """
    print("1. the module bounds the search depends on")
    if img is None:
        LEDGER.skip("1. the AvChar module bounds", NO_CAPSTONE)
        return None, None
    b = CS.module_bounds("AvChar", exe)
    check(b is not None, "AvChar has assert sites to bound it")
    if b is None:
        # §2 and §5 are field searches *inside* these bounds. Without them there
        # is nothing to search, and a declared skip says so rather than a
        # traceback that never reaches the verdict.
        LEDGER.skip("1. the measured AvChar range",
                    "no assert sites found to bound the module")
        return None, None
    lo, hi, _n = b
    check(lo == 0x007F10A5 and hi == 0x007FDF83,
          "AvChar spans the measured range", f"0x{lo:08X}..0x{hi:08X}")
    return lo, hi


def section_2(img, lo, hi):
    """Two writers each, and where. The regression this file most wants to catch."""
    print("\n2. the attack-speed pair: two writers each, and where")
    if img is None:
        LEDGER.skip("2. the attack-speed pair's writers", NO_CAPSTONE)
        return
    if lo is None:
        LEDGER.skip("2. the attack-speed pair's writers",
                    "the AvChar bounds this searches inside were not measured")
        return
    for disp, ctor, setter in ((0xEC, 0x007F1FD2, 0x007FBD88),
                               (0xF0, 0x007F1FE2, 0x007FBD8E)):
        rows = img.field_access(disp, lo, hi)
        writes = sorted(r.va for r in rows if r.is_write)
        # The count that matters. "No mov and no fstp writes either offset by
        # displacement anywhere in the image" was the §6o claim this refutes.
        eq(writes, [ctor, setter], f"+0x{disp:X} is written from exactly two sites")
        # `kind == "R"` and not `not is_write`, since 2026-08-13. An `A` row is
        # not a write either, so the loose form would be satisfied by a field
        # whose address is taken and never loaded -- which is a different and
        # much less interesting shape than the one this line claims.
        check(any(r.kind == "R" for r in rows), f"+0x{disp:X} is also read",
              f"{sum(1 for r in rows if r.kind == 'R')} reads")

    # The constructor writes zero, which is why an untold agent cannot animate.
    ctor = [i for i in img.dis(0x007F1FD0, count=4)]
    check(any(i.mnemonic == "fldz" for i in ctor),
          "the constructor loads 0.0 before storing the pair")


def section_3(exe, img):
    """The chain, then the registration.

    Split down the middle by what each half needs. The uniqueness of every hop is
    a call-graph fact and wants a disassembler; the registration of 0x0035 and its
    field shape are read out of the client's own tables by `msgshape.py`, which is
    stdlib. So the second half is what keeps a bare machine from asserting nothing
    at all, and it is not a consolation prize: it is the half that pins WHICH
    message reaches the chain.
    """
    print("\n3. the chain from the message to the setter is unique at every hop")
    if img is None:
        LEDGER.skip("3a. one caller at every hop", NO_CAPSTONE)
    else:
        chain = [
            (0x007FBD30, 0x007E06CB, "AvChar::SetAttackSpeed <- AvApi"),
            (0x007E0690, 0x0080EA76, "AvApi <- forwarder"),
            (0x0080EA60, 0x0091D829, "forwarder <- the 0x0035 handler"),
        ]
        for target, caller, what in chain:
            calls, data = img.xrefs(target)
            eq([c[0] for c in calls], [caller], f"{what}: one rel32 caller")
            eq(data, [], f"{what}: and no table or callback reaches it")

    hits = MS.Image(exe).lookup(0x0035, "RECV")
    eq(len(hits), 1, "GAME_SMSG 0x0035 is registered exactly once")
    eq(hits[0][3], 0x0091D810, "and dispatches to the handler that calls it")
    eq([repr(f) for f in MS.fields(hits[0][4])], ["agent_id", "u32", "u32"],
       "with the shape the setter needs: an agent and two floats")


def section_4(img):
    """ArenaNet's own words, which is what makes the naming SOURCED."""
    print("\n4. ArenaNet's own words, which is what makes the naming SOURCED")
    if img is None:
        LEDGER.skip("4. ArenaNet's own words", NO_CAPSTONE)
        return
    eq(img.cstr(0x00A93930), r"P:\Code\Gw\AgentView\AvChar.cpp",
       "the source file both asserts name")
    eq(img.cstr(0x00A93F2C), "base", "the setter's first argument is `base`")
    eq(img.cstr(0x00A93F34), "modifier", "and its second is `modifier`")
    eq(img.cstr(0x00A93D14), "m_attackInterval", "the reader asserts m_attackInterval")
    eq(img.cstr(0x00A93D28), "m_attackModifier", "and m_attackModifier")

    # The animation request type that reaches the precondition.
    tbl = img.read(0x007F8BF8, 28 * 4)
    entry3 = int.from_bytes(tbl[12:16], "little")
    eq(entry3, 0x007F8675, "request type 3 is the melee swing")


def section_5(img, lo, hi):
    """The decoding traps, pinned against a field that exercises both."""
    print("\n5. the decoding traps, pinned against a field that exercises both")
    if img is None:
        LEDGER.skip("5. the decoding traps", NO_CAPSTONE)
        return
    if lo is None:
        LEDGER.skip("5. the decoding traps",
                    "the AvChar bounds this searches inside were not measured")
        return
    rows = img.field_access(0x1B8, lo, hi)
    # Memory rows only. The prefix-shadow claim is about the MEMORY scan, and
    # since 2026-08-13 this field also carries two `add eax, 0x1b8` rows (§10):
    # comparing the whole list to 11 would have made this section fail for a
    # reason that has nothing to do with legacy prefixes.
    mem = [r for r in rows if r.kind != "A"]
    eq(len(mem), 11, "+0x1B8: the prefix-shadow duplicates are dropped")
    check(all("word ptr" in r.text and "dword" not in r.text for r in mem),
          "and every survivor is the 16-bit form the prefix really encodes")
    # And the arithmetic scan did not perturb the dedup it runs beside: same 11
    # memory rows, plus exactly the two address-taking ones, no third copy of
    # anything. The two scans share one `seen` set and one shadow filter, so
    # this is the check that they do not stand on each other.
    eq((len(mem), len(rows) - len(mem)), (11, 2),
       "and the arithmetic rows sit beside them without disturbing the dedup")

    # GWCA's documented offsets for the same pair, six bytes earlier: absent.
    for gone in (0x1B1, 0x1B2):
        eq(img.field_access(gone, lo, hi), [],
           f"nothing in AvChar touches +0x{gone:X} (GWCA's offset, drifted)")

    # x87 stores must be classified as writes: capstone calls them reads.
    fstp = [r for r in img.field_access(0xEC, lo, hi) if r[0] == 0x007FBD88]
    check(fstp and fstp[0][1], "an fstp is classified as a store")


def section_6(img):
    """`avevents.insn_len` vs capstone, over exactly the bytes it decodes.

    THE POINT OF THIS SECTION. `avevents.py` carries a hand-written x86 length
    table because it is stdlib -- that is what keeps studies/skillcast §16's
    claims checkable on a machine with nothing installed, and it is the carve-out
    the owner settled: capstone where the code is unknown, stdlib where the byte
    pattern is fixed. But a hand-rolled length table is precisely the kind of
    thing that is subtly wrong for years, and a wrong length does not error -- it
    desynchronises and then decodes the middle of an immediate as an opcode.
    §10 of that study is the same failure in a different tool.

    So the second decoder is not a second chance to be wrong. Every instruction
    boundary it produces is compared against capstone's, over the SAME ranges it
    actually walks, and any disagreement names the address. `boundaries()` exists
    so this reads what the tool reads rather than something adjacent to it.

    Coverage is reported rather than assumed: a check that walked nothing would
    pass silently, which is the failure mode this whole file is written against.
    """
    print("\n6. the stdlib decoder next door agrees with capstone")
    if img is None:
        # `avevents.py` runs here without capstone; the thing it is being weighed
        # against does not. A one-sided run of this section would compare the
        # stdlib decoder to itself, which is the offline self-agreement CLAUDE.md
        # says proves nothing.
        LEDGER.skip("6. avevents' instruction lengths vs capstone", NO_CAPSTONE)
        return

    import avevents as AV
    import genericvalue as GV

    aimg = AV.Image(img.path)

    # Every function the property chase visits: the case bodies, the AvApi entry
    # points, the AvChar methods, plus the two allocators themselves.
    starts = set(AV.ALLOCATORS)
    for _i, (_w, body) in GV.classify(GV.Image(img.path)).items():
        if body is not None:
            starts.add(body)
    for _i, hits in AV.by_property(aimg).items():
        for _which, _kind, path in hits:
            starts.update(path)

    bad, n_ins, n_fn = [], 0, 0
    for va in sorted(starts):
        rows = aimg.boundaries(va)
        if not rows:
            continue
        n_fn += 1
        want = {a: n for a, n, _op in rows}
        got = {i.address: i.size
               for i in img.md.disasm(img.read(va, sum(want.values()) + 16), va)}
        for a, n in sorted(want.items()):
            n_ins += 1
            if got.get(a) != n:
                bad.append(f"0x{a:08x}: stdlib says {n}, capstone says "
                           f"{got.get(a)}")

    check(n_fn >= 60, "functions cross-checked", f"{n_fn}")
    check(n_ins >= 600, "instructions cross-checked", f"{n_ins}")
    eq(bad, [], "every boundary agrees with capstone")


def section_7(exe, img):
    """The three under-reporting defects, each at its known-good address.

    WHY THIS SECTION EXISTS, and it is the same argument as §2 one level up.
    §2 catches a regression in what the scan FINDS. These catch a regression in
    what the scan LOOKS AT -- and on 2026-08-10 a reservation-safety pass found
    three places where the answer was a clean, confident, wrong zero:

      * `--field 0xE --in ExeArchive` said "0 instructions, 0 stores" with
        `0x00478FB8 mov byte [edi+0xe], al` inside the range, because the scan
        searched the displacement's four bytes and this one is encoded in ONE
        (disp8). Every struct offset under 0x80 was invisible, which is most of
        them, in the flagship entry point.
      * `--xrefs 0x00479280` said "0 data word(s)" because the sweep was guarded
        by `p % 4 == 0` and the only reference in the image -- the immediate of
        `push 0x479280` at 0x00478CF5 -- sits two bytes off aligned.
      * `asserts.py --file ExeArchive` reported 96 sites and omitted the ones
        compiled into a shared tail block. 102 is the real number.

    Each check below pins BOTH the answer and the reason it was missed: the
    disp8 hit is checked to be three bytes long, the xref is checked to be
    unaligned. A regression that re-narrows the scan cannot pass by finding the
    address some other way.

    Split by dependency like §3. The `asserts.py` half is stdlib -- that tool
    takes no disassembler on purpose -- so a bare machine still gets the
    shared-tail regression, which is the one that silently narrows every
    `--in <module>` search on the capstone side.
    """
    print("\n7. the three under-reporting defects, at their known-good addresses")

    # -- 7a. codescan: the encodings and alignments it searches ------------
    if img is None:
        LEDGER.skip("7a. --field's disp8 blind spot and --xrefs' alignment "
                    "filter", NO_CAPSTONE)
    else:
        b = CS.module_bounds("ExeArchive", exe)
        lo, hi = (b[0], b[1]) if b else (None, None)
        check(lo is not None and lo <= 0x00478FB8 <= hi,
              "ExeArchive's range contains the store --field could not see",
              f"0x{lo:08X}..0x{hi:08X}" if b else "no bounds")

        rows = {r[0]: r for r in img.field_access(0xE, lo, hi)}
        check(0x00478FB8 in rows,
              "+0xE in ExeArchive finds 0x00478FB8", f"{len(rows)} row(s)")
        if 0x00478FB8 in rows:
            hit = rows[0x00478FB8]
            check(hit[1], "and classifies `mov byte [edi+0xe], al` as a store")
            # THE REASON IT WAS MISSED: three bytes, so the displacement is one
            # byte. A scan that only knows disp32 cannot match this and cannot
            # say so. If this ever reads 7 bytes the fixture moved, not the bug.
            eq(hit[5], "88470e", "encoded disp8 -- the form the old scan missed")

        searched, blind = CS.Image.field_encodings(0xE)
        eq([n for n, _ in searched], ["disp32", "disp8"],
           "--field 0xE states that it searched both encodings")
        s2, b2 = CS.Image.field_encodings(0x1B8)
        eq([n for n, _ in s2], ["disp32"],
           "--field 0x1B8 states disp32 only -- no disp8 of it can exist")
        check(any(n == "disp8" for n, _ in b2),
              "and names disp8 as unreachable rather than staying quiet")
        _s0, b0 = CS.Image.field_encodings(0x0)
        check(any(n == "no displacement" for n, _ in b0),
              "--field 0x0 declares the mod=00 `[reg]` form it cannot reach")

        calls, words = img.xrefs(0x00479280)
        byva = {w[0]: w for w in words}
        eq(len(calls), 0, "0x00479280 has no rel32 caller -- rel32 alone is a zero")
        check(0x00478CF6 in byva,
              "--xrefs finds the word at 0x00478CF6", f"{len(words)} word(s)")
        if 0x00478CF6 in byva:
            w = byva[0x00478CF6]
            # THE REASON IT WAS MISSED. If this ever reads aligned, the check
            # has stopped exercising the filter it exists to keep deleted.
            check(not w[2], "which is NOT 4-byte aligned", f"+{0x00478CF6 % 4}")
            check(w[3] is not None and w[3][0] == 0x00478CF5,
                  "and names the instruction carrying it",
                  w[3][1] if w[3] else "no carrier decoded")

    # -- 7b. asserts: the shapes it recognises. Stdlib, always runs. -------
    az = AZ.Asserts(exe)
    cov = az.coverage()
    # The three shapes, MEASURED 2026-08-10 on the pinned pristine client and
    # identically on our patched copy. Pinned individually rather than as a
    # total: a build that moved sites between shapes while keeping the sum is a
    # real change in the idiom and should be read, not averaged away.
    eq(cov["shapes"].get(AZ.SHAPE_EDX_FIRST), 19620, "edx-first sites")
    eq(cov["shapes"].get(AZ.SHAPE_ECX_FIRST), 75,
       "ecx-first sites -- invisible until 2026-08-10")
    eq(cov["shapes"].get(AZ.SHAPE_SHARED_TAIL), 63,
       "shared-tail sites -- likewise")
    eq(cov["total"], 19758, "and the census, which used to read 19620")
    eq(cov["unreadable"], 3,
       "3 assert calls remain unreadable, and the tool says so")
    n, ncallee, agreed = az.check()
    check(agreed and ncallee == 1,
          "all three shapes call the one assert routine -- which is what says "
          "the two new ones are the idiom and not a byte coincidence",
          f"{n} sites, {ncallee} callee(s)")

    # The two ExeArchive sites the pass named, and their shapes.
    ea = {a.va: a for a in az.by_module("ExeArchive")}
    eq(len(ea), 102, "ExeArchive has 102 sites, not the 96 it used to report")
    check(0x0047CE63 in ea, "ExeArchive:1905 is at 0x0047CE63")
    if 0x0047CE63 in ea:
        eq(ea[0x0047CE63].line, 1905, "with the line it pushes")
        eq(ea[0x0047CE63].shape, AZ.SHAPE_SHARED_TAIL,
           "reached by a jmp into another site's tail -- why it was omitted")
    check(0x0047CE7E in ea, "and ExeArchive:1906 is the tail it jumps into")
    if 0x0047CE7E in ea:
        eq(ea[0x0047CE7E].line, 1906, "with its own line")
        eq(ea[0x0047CE7E].shape, AZ.SHAPE_ECX_FIRST,
           "and the ecx-first order that hid it from the fixed pattern")

    # The consequence for `codescan --in ExeArchive`: the module's upper bound
    # is one of the recovered sites, so the range every field search there runs
    # inside was short by 0x55 bytes.
    b = CS.module_bounds("ExeArchive", exe) if img is not None else None
    if b is None:
        LEDGER.skip("7b. the widened ExeArchive bound", NO_CAPSTONE)
    else:
        eq(b[1], 0x0047CE7E,
           "ExeArchive's upper bound is a recovered site (was 0x0047CE29)")


def section_8(exe):
    """The census attributes each count to the file it counted.

    THE DEFECT, found 2026-08-11. `Asserts.modules()` grouped by `Assert.module`
    -- the basename with no extension -- and `--modules` printed
    `mods[m][0].file` as the row's path, i.e. whichever colliding file happened
    to hold the lowest VA. Nine basenames on build 38797 name two source files
    each, so nine rows of that report carried a count of one thing under the name
    of another, and the second file never appeared in the census at all.

    It was worst where it was least visible. The top two rows are
    `Base\\rtl\\Array.h` (4431) and `Base\\rtl\\List.h` (3288); both were printed
    under their .cpp siblings' paths at 4433 and 3295, so the two largest numbers
    in the report described no file in the image. And `PrApi` is the one that
    would have produced a wrong FINDING rather than a wrong number: 67 sites in
    `Gw\\Pref\\PrApi.cpp` (the preferences API) and 19 in
    `Engine\\Map\\Props\\PrApi.cpp` (the props API), unrelated modules 2.4 MB
    apart, printed as one row of 86 against the preferences path -- so "the props
    code has no PrApi.cpp" read as absence off a census that had merged it away.
    That is the same shape as §7: a clean, confident, wrong answer.

    THE FIRST CHECK IS THE NEGATIVE CONTROL, and it is checked before anything
    below rests on it. Every check here is worthless if the two files stopped
    colliding, so the collision itself is asserted first -- both paths must still
    reduce to the same `Assert.module`. A regrouping by basename is then run
    inside this file, out of `int`s and `dict`s that import nothing from the tool
    under test, and required to still produce the merged 86: that is the bug,
    reproduced, so the 67/19 below is a difference between two live answers
    rather than a number this file asked the code to confirm about itself.

    Stdlib. `asserts.py` takes no disassembler on purpose, and the census is the
    part of it a bare machine can still check.
    """
    print("\n8. the module census names the file it counted")
    az = AZ.Asserts(exe)

    # The two colliding files, and the counts MEASURED 2026-08-11 on the pinned
    # pristine 38797. Literals, not read back out of the tool: a count computed
    # from the thing under test moves when the thing under test moves.
    PREF = r"P:\Code\Gw\Pref\PrApi.cpp"
    PROPS = r"P:\Code\Engine\Map\Props\PrApi.cpp"
    mods = az.modules()

    # -- 8a. the collision is real, or nothing below means anything ---------
    pref_items = [a for a in az.items if a.file == PREF]
    props_items = [a for a in az.items if a.file == PROPS]
    check(bool(pref_items) and bool(props_items),
          "both PrApi.cpp still exist in the image",
          f"{len(pref_items)} pref, {len(props_items)} props")
    if pref_items and props_items:
        eq(pref_items[0].module, props_items[0].module,
           "and still collide on basename -- which is what this section tests")

    # The bug, reproduced here rather than described. Grouping by basename is
    # four lines, so the merged answer is a live measurement of the old rule and
    # not a number quoted from a commit message.
    merged = {}
    for a in az.items:
        merged.setdefault(a.module, []).append(a)
    eq(len(merged.get("PrApi", [])), 86,
       "grouping by basename merges them into one row of 86 -- the old census")
    eq(merged["PrApi"][0].file, PREF,
       "under the path of whichever file held the lowest VA")

    # -- 8b. and the shipped census does not ------------------------------
    eq(len(mods.get(PREF, [])), 67, "the preferences PrApi.cpp is its own row")
    eq(len(mods.get(PROPS, [])), 19, "the props PrApi.cpp is its own row")
    check(PROPS in mods, "so the props module is IN the census, not absent")

    # They are unrelated code, not one file under two spellings: every props site
    # sits above every preferences site, 2.4 MB up the image.
    if pref_items and props_items:
        check(min(a.va for a in props_items) > max(a.va for a in pref_items),
              "the two modules do not overlap -- 2.4 MB apart",
              f"pref <=0x{max(a.va for a in pref_items):08X}, "
              f"props >=0x{min(a.va for a in props_items):08X}")

    # -- 8c. the two largest rows, which were the two most wrong ----------
    for path, n in ((r"P:\Code\Base\rtl\Array.h", 4431),
                    (r"P:\Code\Base\Rtl\Array.cpp", 2),
                    (r"P:\Code\Base\rtl\List.h", 3288),
                    (r"P:\Code\Base\Rtl\List.cpp", 7)):
        eq(len(mods.get(path, [])), n, f"{path} has {n} sites of its own")

    # -- 8d. nothing was dropped or double-counted by the regrouping ------
    eq(sum(len(v) for v in mods.values()), az.coverage()["total"],
       "every site is in exactly one row")
    eq(len(mods), 864, "864 source files assert on this build")

    # -- 8e. case-only spellings ARE one file, and say so -----------------
    # `Base\Compress\CmpIo.h` and `Base\compress\CmpIo.h` differ only in the case
    # of a directory, and the build was on Windows: one file, two translation
    # units spelling it differently. 65 sites, not a 31 and a 34 -- and the row
    # names both spellings rather than silently picking the one it keyed on,
    # which would be this same defect one level down.
    CMPIO = r"P:\Code\Base\Compress\CmpIo.h"
    eq(len(mods.get(CMPIO, [])), 65, "the two CmpIo.h spellings are one row")
    eq(sorted(az.spellings().get(CMPIO, [])),
       [r"P:\Code\Base\Compress\CmpIo.h", r"P:\Code\Base\compress\CmpIo.h"],
       "and the row names both spellings instead of choosing one")

    # -- 8f. the collisions are reported, because --file still pools them --
    coll = az.collisions()
    eq(len(coll), 9, "nine basenames name more than one file")
    eq(coll.get("prapi"), sorted([PREF, PROPS]), "PrApi is one of them")
    # `coll and` is load-bearing: `all()` over an empty dict is True, so the
    # basename-grouping sabotage that empties `collisions()` passed this check
    # while every check around it went red. A vacuous pass inside a red section
    # is still a check that cannot fail.
    check(coll and all(len(v) == 2 for v in coll.values()),
          "each names exactly two", f"{sorted((k, len(v)) for k, v in coll.items())}")


def section_9(exe, img):
    """The same ambiguity one tool downstream: `codescan --in <name>`.

    `module_bounds` takes min and max VA over a SUBSTRING match, so the collision
    the census used to hide is a silent widening here: `--in PrApi` bounds
    0x00499B01..0x0073943A and every `--field` run inside it is drawn from 2.4 MB
    of mostly unrelated .text while the header says it searched one module. That
    is the opposite direction from §7's shared-tail under-count -- which narrowed
    the same ranges -- and it fails the same way, by answering confidently.

    Not resolved, reported: `--in Rtl` meaning a whole subsystem is a legitimate
    query, so the caller is told what its name caught. Which means the check that
    matters is that the note distinguishes the two shapes of multi-file match --
    `AvChar` also catches `AvCharAnim.cpp`, immediately adjacent, and that one is
    the harmless widening `module_bounds` documents. A note that read the same
    for both would be noise, and noise gets ignored.
    """
    print("\n9. and the module bounds downstream say what they bounded")
    if img is None:
        LEDGER.skip("9. --in's multi-file bounds", NO_CAPSTONE)
        return

    files = CS.module_files("PrApi", exe)
    eq(len(files), 2, "`--in PrApi` bounds two source files")
    eq({f: files[f][0] for f in files},
       {r"P:\Code\Gw\Pref\PrApi.cpp": 67,
        r"P:\Code\Engine\Map\Props\PrApi.cpp": 19},
       "with the counts the census now reports")
    lo, hi, n = CS.module_bounds("PrApi", exe)
    eq((lo, hi, n), (0x00499B01, 0x0073943A, 86),
       "and the pooled range really is their union -- 2.4 MB of it")

    note = CS.bounds_note("PrApi", exe)
    check(note and "matched 2 source files" in note[0],
          "the CLI warns rather than printing the union unremarked")
    check(any("0x00738AC1" in ln for ln in note),
          "and prints each file's OWN span, not just its name")

    # The two shapes of multi-file match, kept apart. AvCharAnim's two sites are
    # 0x17F0 below AvChar.cpp's first: adjacent code, the harmless widening.
    av = CS.module_files("AvChar", exe)
    eq(sorted(av), [r"P:\Code\Gw\AgentView\AvChar.cpp",
                    r"P:\Code\Gw\AgentView\AvCharAnim.cpp"],
       "`--in AvChar` catches AvCharAnim.cpp too, by substring")
    eq(av[r"P:\Code\Gw\AgentView\AvChar.cpp"][1], 0x007F215F,
       "AvChar.cpp's own sites start above the pinned §1 lower bound, which is "
       "AvCharAnim's")

    # The control: a name that catches ONE file prints nothing at all.
    eq(CS.bounds_note("ExeArchive", exe), [],
       "and a name matching one file warns about nothing")


def section_10(exe, img):
    """The THIRD under-reporting defect: `--field` knew memory operands only.

    THE DEFECT, found 2026-08-13 by studies/profession/RUNS.md §13. `--field
    0x6bc` reported **14 instructions** over the whole image and `0x00813AD1
    add ecx, 0x6bc` was not among them -- the writer reached from GAME_SMSG
    0x00B6's handler, i.e. the writer of the very field that search was run to
    find. Five sites were missing, a quarter of the answer, and the footer
    disclaimed the disp8 and disp16 encodings and nothing else, so the report
    read as complete.

    It is the same shape as §7 twice over: a clean, confident, wrong count. What
    makes it a THIRD instance rather than a repeat is where the constant lives.
    §7's disp8 miss was a displacement in an encoding the scan did not search;
    this one is not a displacement at all. `81 c1 bc 06 00 00` carries 0x6BC in
    its IMMEDIATE field, and an anchored scan that accepts a candidate only when
    capstone's encoding record puts a DISPLACEMENT on the bytes it found cannot
    match it however many widths it knows.

    THE OLD RULE IS REPRODUCED HERE, not described -- the §8 pattern. Eighteen
    lines of `capstone` that import nothing from the tool under test re-run the
    displacement-only acceptance rule over the same anchors, and are required to
    reach 14 and to MISS 0x00813AD1. So the 19 below is a difference between two
    live answers, and the miss is a measurement of the old rule rather than a
    number quoted from a study.

    THE CONTROLS THAT KEEP `A` HONEST. Address-taking is a new class and the
    lazy way to pass this section is to widen it -- so a real load and a real
    store at the same displacement are required to stay `R` and `W`, every `A`
    row is required to have `is_write` false (§2's two-writers claim reads
    `is_write`, and an inflated `A` must not be able to reach it), and the
    narrow-destination exclusion is checked against an instruction proved to
    exist first.
    """
    print("\n10. the arithmetic form: an address taken, not a displacement")
    if img is None:
        LEDGER.skip("10. --field's address-arithmetic blind spot", NO_CAPSTONE)
        return

    DISP = 0x6BC
    WRITER = 0x00813AD1          # add ecx, 0x6bc -- GAME_SMSG 0x00B6's chain
    rows = {r.va: r for r in img.field_access(DISP)}

    # -- 10a. the address, and the reason it was missed --------------------
    check(WRITER in rows,
          "--field 0x6bc finds 0x00813AD1, GAME_SMSG 0x00B6's writer",
          f"{len(rows)} row(s)")
    if WRITER in rows:
        hit = rows[WRITER]
        eq(hit.hexbytes, "81c1bc060000",
           "encoded `add r/m32, imm32` -- the form the old scan missed")
        eq(hit.kind, "A", "and is classified address-taking, not a read")
        eq(hit.text, "add ecx, 0x6bc", "with the instruction spelled out")

    # THE REASON, read off the bytes by capstone directly. `disp_size == 0` is
    # what says no displacement-anchored rule could ever have matched this, and
    # it is a fact about the encoding rather than an answer from the scanner.
    ins = next(iter(img.md.disasm(img.read(WRITER, 16), WRITER, 1)), None)
    check(ins is not None and ins.encoding.disp_size == 0,
          "0x00813AD1 carries NO displacement field at all",
          f"disp_size={ins.encoding.disp_size}" if ins else "did not decode")
    check(ins is not None and ins.encoding.imm_size == 4
          and ins.encoding.imm_offset == 2,
          "it carries 0x6BC as a 4-byte IMMEDIATE, two bytes in",
          f"imm_size={ins.encoding.imm_size}, off={ins.encoding.imm_offset}"
          if ins else "did not decode")

    # -- 10b. the old rule, reproduced, and required to miss it ------------
    # Displacement-only acceptance over the same anchor, written out of
    # `capstone` and `struct` so its 14 is an independent answer.
    old, blob, tva = set(), img.tdata, img.tva
    needle = struct.pack("<I", DISP)
    p = blob.find(needle)
    while p != -1:
        for back in range(1, 12):
            start = p - back
            if start < 0:
                continue
            i2 = next(iter(img.md.disasm(blob[start:start + 24],
                                         tva + start, 1)), None)
            if i2 is None or i2.encoding.disp_size != 4:
                continue
            if start + i2.encoding.disp_offset != p:
                continue
            if any(o.type == capstone.x86.X86_OP_MEM and o.mem.disp == DISP
                   for o in i2.operands):
                old.add(i2.address)
        p = blob.find(needle, p + 1)
    eq(len(old), 14, "the displacement-only rule reaches 14 -- the old answer")
    check(WRITER not in old,
          "and cannot reach 0x00813AD1, whatever width it searches")
    eq(len(rows), 19, "searching both, the real count is 19")
    eq(sorted(set(rows) - old), [WRITER, 0x00816D1E, 0x00816D3E, 0x00816D5E,
                                0x00819ED1],
       "and the five it adds are exactly the register-arithmetic sites")

    # -- 10c. `A` is a class, not a bucket everything falls into -----------
    for va, kind, why in ((0x0041806F, "A", "lea takes the address, reads no "
                                            "memory, and used to read as R"),
                          (0x004184DC, "R", "a real load is still a read"),
                          (0x00418763, "W", "a real store is still a write")):
        got = rows.get(va)
        eq(got.kind if got else None, kind, f"0x{va:08X} is {kind}: {why}")
    check(all(not r.is_write for r in rows.values() if r.kind == "A"),
          "no address-taking row claims to be a store",
          f"{sum(1 for r in rows.values() if r.kind == 'A')} A row(s)")

    # -- 10d. and the scope statement says both halves ---------------------
    asearched, ablind = CS.Image.address_forms(DISP)
    names = [n for n, _ in asearched]
    check("add r32, imm32" in names and "sub r32, -imm32" in names,
          "--field states that it searched the arithmetic forms", f"{names}")
    check(any(n == "the constant held in a register" for n, _ in ablind),
          "and names the form it provably cannot reach")

    # -- 10e. the `sub` spelling, against real bytes -----------------------
    # Not hypothetical and not free: -0x19 is different bytes from 0x19, so this
    # form costs the one extra sweep `field_access` documents. A scan that
    # skipped it would answer confidently again.
    subrows = {r.va: r for r in img.field_access(0x19)}
    check(0x00622199 in subrows,
          "--field 0x19 finds `sub ecx, -0x19` at 0x00622199",
          f"{len(subrows)} row(s)")
    if 0x00622199 in subrows:
        eq(subrows[0x00622199].hexbytes, "83e9e7",
           "whose immediate byte is 0xE7 -- -0x19, not 0x19, hence its own anchor")
        eq(subrows[0x00622199].kind, "A", "and it is address-taking too")

    # -- 10f. the narrow-destination exclusion, proved to be excluding -----
    # `add al, 0xe` cannot be an address in 32-bit code. It is dropped, which is
    # a filter -- so the instruction is decoded here FIRST, and the check is
    # that a real instruction is being excluded rather than an address that was
    # never there.
    narrow = next(iter(img.md.disasm(img.read(0x00479BC8, 8), 0x00479BC8, 1)),
                  None)
    eq(f"{narrow.mnemonic} {narrow.op_str}" if narrow else None, "add al, 0xe",
       "0x00479BC8 really is `add al, 0xe`")
    b = CS.module_bounds("ExeArchive", exe)
    ea = {r.va: r for r in img.field_access(0xE, b[0], b[1])}
    check(0x00479BC8 not in ea,
          "and --field 0xE --in ExeArchive drops it: al is not an address")
    check(any(r.kind == "A" for r in ea.values()),
          "while the range's real address-taking rows survive the filter",
          f"{sum(1 for r in ea.values() if r.kind == 'A')} A row(s)")


def main():
    # The build guard. `pinned` is stdlib -- `CS.find_exe` is literally
    # `pinned.find` -- so which client we are reading gets said out loud even on a
    # machine that cannot disassemble it.
    exe, why = pinned.find()
    print(f"client: {exe}\n        ({why})\n")
    if os.path.getsize(exe) != EXE_BYTES:
        raise SystemExit(f"wrong build: {os.path.getsize(exe)} bytes, "
                         f"expected {EXE_BYTES} for build {BUILD}. Every "
                         f"address below is measured against that one.")
    if not HAVE_CAPSTONE:
        print(f"{NO_CAPSTONE}\n-- the disassembling sections will declare skips\n")

    img = CS.Image(exe) if HAVE_CAPSTONE else None

    lo, hi = section_1(exe, img)
    section_2(img, lo, hi)
    section_3(exe, img)
    section_4(img)
    section_5(img, lo, hi)
    section_6(img)
    section_7(exe, img)
    section_8(exe)
    section_9(exe, img)
    section_10(exe, img)

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
