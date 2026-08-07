#!/usr/bin/env python3
"""Check studies/enemy/PLAN.md §6q against the binary it was read from.

    python toolkit/clientscan/test_codescan.py

§6q says attacking was blocked on a single message, and every load-bearing claim
in it is an address. Addresses rot silently: a build changes, a tool's decoding
changes, and the study becomes a confident description of a binary nobody has
re-read. This makes each claim executable.

Five of the six sections can fail for the right reason:

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
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

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

# 30 checks in a green run with capstone present, MEASURED 2026-08-06 against the
# pinned pristine 38797 -- the banner's own total, not a count of `check(` lines:
# 2 in §1, 5 in §2, 9 in §3, 6 in §4, 5 in §5, 3 in §6. None of it is
# fixture-dependent: every section reads that one binary and every loop is over a
# tuple written into this file, so a capstone run scoring fewer has had a section
# stop executing rather than found less data.
#
# Without capstone only §3's stdlib half can run: 3 checks, measured the same day
# by blocking the import. Hence two floors rather than one. A flat 3 would let a
# capstone run lose the whole of §2 -- the two-writers claim, the most valuable
# failure this file can produce -- and still print green, which is precisely the
# partial vacuity checks.py was written to name.
FLOOR_WITH_CAPSTONE = 30
FLOOR_STDLIB_ONLY = 3

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
        writes = sorted(r[0] for r in rows if r[1])
        # The count that matters. "No mov and no fstp writes either offset by
        # displacement anywhere in the image" was the §6o claim this refutes.
        eq(writes, [ctor, setter], f"+0x{disp:X} is written from exactly two sites")
        check(any(not r[1] for r in rows), f"+0x{disp:X} is also read",
              f"{sum(1 for r in rows if not r[1])} reads")

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
    eq(len(rows), 11, "+0x1B8: the prefix-shadow duplicates are dropped")
    check(all("word ptr" in r[4] and "dword" not in r[4] for r in rows),
          "and every survivor is the 16-bit form the prefix really encodes")

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

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
