#!/usr/bin/env python3
"""Check the skill-cast reading against the client binary it came from.

    python toolkit/clientscan/test_skillcast.py

Everything asserted here is written up in studies/skillcast/FINDINGS.md. The
point of the file is that the study's claims are executable: if a later pass
changes `asserts.py` or `msgshape.py` and the recovered picture shifts, this
goes red and names the claim that moved, instead of the study quietly becoming
a description of a binary nobody has re-read.

Five sections, and four of them can fail for the right reason:

  * Section 2 requires 19,618+ assert sites to agree on ONE callee. A 15-byte
    byte pattern would ordinarily be expected to collide with unrelated code;
    unanimity is the evidence that it does not.
  * Section 3 is the strongest check here and it is not ours. The four AgMsg
    oracle messages were recovered in studies/msgtable by constant-propagating
    initializer stores and cross-checked against the PE relocation table, a
    method sharing nothing with the byte walk in `msgshape.py`. Their cmds are
    100% zero in the file, so a decoder that skips the recovery gets all four
    wrong -- as this decoder did, on its first draft, silently.
  * Section 4 pins wire shapes that a naive read gets WRONG in a plausible
    direction: 0x00E5 reads as four dwords (18 bytes) if you trust the file
    and is `agent_id, u16, u32, u32` (16 bytes) once the initializers are
    resolved. Both look fine. Only one is what our client parses.
  * Section 5 asserts exact byte strings at exact addresses for the record
    strides and the two compares that define the cast lifecycle. A wrong
    address fails; a build change fails; a rewritten claim fails.

Section 1 is not a check, it is a guard: everything below is measured against
one build, and testing the wrong file would pass or fail for no reason worth
having.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import asserts as A                                          # noqa: E402
import msgshape as MS                                        # noqa: E402
from vaultpath import vault_path, vault_root, vault_why      # noqa: E402

BUILD = 38797
EXE_BYTES = 10_483_904
PINNED = ("run", "2026-07-29_221c13772c7a", "Gw.exe")
FALLBACK_EXE = r"C:\gw\Gw.exe"

FAILED = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAILED.append(label)
    return ok


def eq(got, want, label):
    return check(got == want, label, "" if got == want else f"got {got!r}, want {want!r}")


# ---------------------------------------------------------------- section 1
def find_exe():
    """The pinned snapshot, else the live install. Never silently either."""
    pinned = vault_path(*PINNED)
    if os.path.exists(pinned):
        return pinned, "pinned vault snapshot"
    if os.path.exists(FALLBACK_EXE):
        return FALLBACK_EXE, "live install (pinned snapshot not in the vault)"
    raise SystemExit(
        f"no client to read.\n"
        f"  looked for {pinned}\n"
        f"  vault resolved to {vault_root()} ({vault_why()})\n"
        f"  and for {FALLBACK_EXE}\n"
        f"  Set RURIK_VAULT, or see RUNBOOK.md.")


# ---------------------------------------------------------------- section 2
# (module, line, expression) the study quotes. Each one is a sentence of
# ArenaNet's own source that a claim rests on. PathDir is deliberately from a
# different arc -- it is the assert that settled the navmesh portal pairing,
# and it is here so this test also guards the tool the next study will use.
QUOTED = [
    ("ChCliSkill", 205, "hotKey < arrsize(hotKeyState->hotKey)"),
    ("ChCliSkill", 681, "hotKey < arrsize(hotKeyState->hotKey)"),
    ("ChCliSkill", 955, "pending->refCount"),
    ("ChCliSkill", 1126, "copies"),
    ("ChCliApi", 5613, "hotKey < CHAR_SKILL_HOTKEYS"),
    ("GmSkSlot", 807, "charCliSkillId == m_skillId"),
    ("GmSkSlot", 808, "charCliSkillCopy == m_skillCopy"),
    ("GmSkSlot", 206, "unlockedSkills->BitTest(sourceSkillId)"),
    ("PathDir", 1494, "m_trapezoid->portalLeft < pathMap.portalCount"),
]


# ---------------------------------------------------------------- section 4
# opcode -> (direction, field repr list, min wire, max wire). MEASURED via the
# recovered descriptors. Where this disagrees with schema/messages.json the
# schema is the import of a reconstruction and this is the client.
SHAPES = {
    0x001D: ("RECV", ["array32[128]"], 4, 516),          # PVP_UPDATE_UNLOCKED_SKILLS
    0x00D3: ("RECV", ["array32[128]"], 4, 516),          # unnamed everywhere
    0x00D9: ("RECV", ["dword", "u8", "u16", "u32"], 13, 13),
    0x00DA: ("RECV", ["dword", "array32[8]", "array32[8]", "u8"], 11, 75),
    0x00DB: ("RECV", ["array32[128]"], 4, 516),          # UPDATE_UNLOCKED_SKILLS
    0x00E2: ("RECV", ["dword", "u16", "u32"], 12, 12),   # SKILL_INTERUPTED
    0x00E3: ("RECV", ["dword", "u16", "u32"], 12, 12),   # SKILL_CANCEL/ACTIVATED
    0x00E4: ("RECV", ["dword", "u16", "u32"], 12, 12),   # SKILL_ACTIVATE
    0x00E5: ("RECV", ["dword", "u16", "u32", "u32"], 16, 16),        # SKILL_RECHARGE
    0x00E6: ("RECV", ["dword", "u16", "u32"], 12, 12),   # SKILL_RECHARGED
    0x00E7: ("RECV", ["dword", "u16", "u32"], 12, 12),   # unnamed: disable
    0x00E8: ("RECV", ["dword", "u16", "u32", "u32", "u32"], 20, 20),  # unnamed
    0x0046: ("SEND", ["u32", "u32", "dword", "u8"], 15, 15),          # USE_SKILL
    0x0027: ("SEND", ["dword", "u32", "u32", "u8"], 15, 15),          # unnamed
}


# ---------------------------------------------------------------- section 5
# (VA, bytes, what it proves). Read straight out of the file, no disassembler.
BYTES = [
    (0x00820FBE, "69f8bc000000",
     "HotKeyState record stride is 0xBC (188) -- imul edi, eax, 0xbc"),
    (0x00822BC1, "8d7004",
     "the eight slots begin at record+4 -- lea esi, [eax+4]"),
    (0x00822BC4, "05a4000000",
     "and end at record+0xA4 -- add eax, 0xa4, i.e. 8 * 0x14"),
    (0x00822BDB, "83c614",
     "slot stride is 0x14 (20) -- add esi, 0x14"),
    (0x00822BD1, "397e0c",
     "SKILL_RECHARGE matches slot+0x0C against field 2 (skill id)"),
    (0x00822BD6, "395e10",
     "and slot+0x10 against field 3 -- the field GWCA calls skill_instance"),
    (0x0082124D, "8b4110",
     "the slot getter returns slot+0x0C as its 3rd out-param (skillId)"),
    (0x00821252, "8b4114",
     "and slot+0x10 as its 4th (skillCopy), per GmSkSlot:807-808"),
    (0x00822F2D, "8db0a8000000",
     "the pending-cast array is at record+0xA8 -- GWCA's cast_array offset"),
    (0x00822F33, "c1e310",
     "the pending key is skill_id << 16 ..."),
    (0x00822F36, "035d10",
     "... plus field 3, so field 3 must fit in 16 bits"),
    (0x0082303D, "c744f80401000000",
     "a new pending entry is created with refCount = 1"),
    (0x0082311E, "834704ff",
     "SKILL_INTERUPTED/CANCEL decrements that refCount"),
    (0x008148FC, "e8df8affff",
     "the SKILL_ACTIVATE handler asks for the local player's agent id"),
    (0x00814904, "3bc17412",
     "and returns without doing anything if the message names it"),
    (0x00822C38, "694d14e8030000",
     "SKILL_RECHARGE's 4th field is multiplied by 1000: it is SECONDS"),
    (0x00822CF3, "c7410800000000",
     "SKILL_RECHARGED writes recharge = 0 -- the ready sentinel"),
    (0x00822DC3, "c74608ffffffff",
     "opcode 231 writes recharge = -1 instead -- a different sentinel"),
    (0x0091F707, "d94014",
     "opcode 232's 5th field is loaded with fld: it is an IEEE float"),
]

LOG_STRING_VA = 0x00A95C94
LOG_STRING = "Pending skill %u copy %d not found"


def main():
    exe, why = find_exe()
    size = os.path.getsize(exe)
    print(f"\nclient under test: {exe}\n  ({why})")
    print(f"\n1. Which binary  (build {BUILD})")
    if not eq(size, EXE_BYTES, "file size matches the pinned build"):
        print("\n  Refusing to continue: every address below is build-specific "
              "and\n  measuring a different build proves nothing either way.")
        return 1

    print("\n2. The client's own assertions")
    az = A.Asserts(exe)
    n, ncallee, agreed = az.check()
    check(n >= 19_000, "assert sites found", f"{n}")
    eq(ncallee, 1, "every site calls one routine")
    check(agreed, "and it is the expected assert routine",
          f"0x{A.ASSERT_VA_38797:08x}")
    have = {(a.module, a.line, a.expr) for a in az.items}
    for triple in QUOTED:
        check(triple in have, f"quoted: {triple[0]}:{triple[1]}  {triple[2]}")
    hits = [a for a in az.items if a.expr == LOG_STRING]
    check(not hits, "the log string is not itself an assert expression")

    print("\n3. The descriptor recovery  (the trap this study nearly fell into)")
    img = MS.Image(exe)
    c = img.census()
    for k, v in MS.CENSUS_38797.items():
        eq(c[k], v, f"cmd slot census: {k}")
    for op, ok, got in img.oracle_check():
        check(ok, f"studies/msgtable oracle 0x{op:04X} reproduced",
              "" if ok else f"got {[hex(x) if x else '?' for x in got or []]}")
    bad = img.invariants()
    eq(len(bad), 0, "the client's own descriptor invariants hold")

    print("\n4. Wire shapes of the skill block")
    for op in sorted(SHAPES):
        direction, want_fields, want_lo, want_hi = SHAPES[op]
        hits = img.lookup(op, direction)
        if not check(len(hits) == 1, f"0x{op:04X} {direction} is in exactly "
                                     f"one table", f"{len(hits)} found"):
            continue
        cmds = hits[0][4]
        got = [repr(f) for f in MS.fields(cmds)]
        eq(got, want_fields, f"0x{op:04X} {direction} fields")
        eq((MS.wire_min(cmds), MS.wire_max(cmds)), (want_lo, want_hi),
           f"0x{op:04X} {direction} wire bytes")

    print("\n5. The cast lifecycle, byte for byte")
    d226 = img.lookup(0x00E2, "RECV")[0][3]
    d227 = img.lookup(0x00E3, "RECV")[0][3]
    d228 = img.lookup(0x00E4, "RECV")[0][3]
    check(d226 == d227, "226 and 227 share one dispatch function",
          f"0x{d226:08x}")
    check(d228 != d226, "228 does not", f"0x{d228:08x}")
    for va, hexs, why_ in BYTES:
        off = img.pe.rva_to_off(va - img.base)
        got = img.pe.data[off:off + len(hexs) // 2].hex() if off else None
        eq(got, hexs, f"0x{va:08x}: {why_}")
    s = az.cstr(LOG_STRING_VA)
    eq(s, LOG_STRING, "the client's own name for field 3 is in the image")
    eq(len(az.direct_callers(0x00821CC0)), 1,
       "opcode 211's write path has exactly one caller (its own handler)")
    eq(len(az.direct_callers(0x00822B80)), 2,
       "the SKILL_ACTIVATE path has two: the handler AND ChCliApiUseSkill")

    print()
    if FAILED:
        print(f"[FAIL] {len(FAILED)} check(s) failed:")
        for f in FAILED:
            print(f"   - {f}")
        return 1
    print("[PASS] all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
