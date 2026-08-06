#!/usr/bin/env python3
"""Check studies/enemy/PLAN.md §6q against the binary it was read from.

    python toolkit/clientscan/test_codescan.py

§6q says attacking was blocked on a single message, and every load-bearing claim
in it is an address. Addresses rot silently: a build changes, a tool's decoding
changes, and the study becomes a confident description of a binary nobody has
re-read. This makes each claim executable.

Four of the five sections can fail for the right reason:

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
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import codescan as CS                                        # noqa: E402
import msgshape as MS                                        # noqa: E402

BUILD = 38797
EXE_BYTES = 10_483_904

FAILED = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAILED.append(label)
    return ok


def eq(got, want, label):
    return check(got == want, label, "" if got == want else f"got {got!r}, want {want!r}")


def cross_check_avevents(img):
    """`avesents.insn_len` vs capstone, over exactly the bytes it decodes.

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
    # ------------------------------------------------------------ section 1
    exe, why = CS.find_exe()
    print(f"client: {exe}\n        ({why})\n")
    if os.path.getsize(exe) != EXE_BYTES:
        raise SystemExit(f"wrong build: {os.path.getsize(exe)} bytes, "
                         f"expected {EXE_BYTES} for build {BUILD}. Every "
                         f"address below is measured against that one.")
    img = CS.Image(exe)

    print("1. the module bounds the search depends on")
    b = CS.module_bounds("AvChar", exe)
    check(b is not None, "AvChar has assert sites to bound it")
    lo, hi, n = b
    check(lo == 0x007F10A5 and hi == 0x007FDF83,
          "AvChar spans the measured range", f"0x{lo:08X}..0x{hi:08X}")

    # ------------------------------------------------------------ section 2
    print("\n2. the attack-speed pair: two writers each, and where")
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

    # ------------------------------------------------------------ section 3
    print("\n3. the chain from the message to the setter is unique at every hop")
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

    # ------------------------------------------------------------ section 4
    print("\n4. ArenaNet's own words, which is what makes the naming SOURCED")
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

    # ------------------------------------------------------------ section 5
    print("\n5. the decoding traps, pinned against a field that exercises both")
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

    print("\n6. the stdlib decoder next door agrees with capstone")
    cross_check_avevents(img)

    print()
    if FAILED:
        print(f"[FAIL] {len(FAILED)} check(s) failed:")
        for f in FAILED:
            print(f"  - {f}")
        return 1
    print("[PASS] all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
