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
import genericvalue as GV                                    # noqa: E402
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
    ("ChCliBuff", 235, "!buffTarget->sourceAgent"),
    ("GmEffect", 882, "targetBuff.skill == m_skillId"),
    ("GmEffect", 1252, "m_sourceBuff.buffId"),
    ("AvChar", 4320, "stat == AV_CHAR_STAT_ENERGY"),
    ("ChCliApi", 2112, "sourceAgent < 5"),
    ("PathDir", 1494, "m_trapezoid->portalLeft < pathMap.portalCount"),
]

# The client's own log format strings, at the VAs the study cites them from.
# These are the naming source: an assert bounds a value, but a log line spells
# out what the handler calls its arguments. "Pending skill %u copy %d not
# found" is why section 3 exists, and the six Buff* lines are why section 14
# can name all six EFFECT_* opcodes in ArenaNet's vocabulary.
LOG_STRINGS = [
    (0x00A95C94, "Pending skill %u copy %d not found"),
    (0x00A955A0, "BuffSourceAdd (agent %d, skill %d): "
                 "BuffId exists on agent already"),
    (0x00A95608, "BuffSourceRemove (agent %d, buffId %d): "
                 "No BuffState exists for agent"),
    (0x00A95650, "BuffSourceRemove (agent %d, buffId %d): "
                 "BuffId is not on agent"),
    (0x00A95690, "BuffTargetAdd (agent %d, skill %d, buffId %d): "
                 "BuffId exists on agent already"),
    (0x00A956E0, "BuffTargetExtendTimed (agent %d, buffId %d): "
                 "No BuffState exists for agent"),
    (0x00A95798, "BuffTargetRemove (agent %d, buffId %d): "
                 "No BuffState exists for agent"),
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
    # The buff family, section 14. Note 0x0042 and 0x0043's last field: the
    # descriptor types it as a plain u32 and the HANDLER loads it with fld.
    0x003F: ("RECV", ["dword", "dword", "u16", "u32", "u32"], 20, 20),  # BuffSourceAdd
    0x0040: ("RECV", ["dword", "u32"], 10, 10),                         # BuffSourceRemove
    0x0041: ("RECV", ["dword", "dword", "u16", "u32", "u32"], 20, 20),  # BuffTargetAdd
    0x0042: ("RECV", ["dword", "u16", "u32", "u32", "u32"], 20, 20),    # BuffTargetAdd timed
    0x0043: ("RECV", ["dword", "u32", "u32", "u32"], 18, 18),           # BuffTargetExtendTimed
    0x0044: ("RECV", ["dword", "u32"], 10, 10),                         # BuffTargetRemove
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
    # -- section 14, the buff family ------------------------------------
    (0x0091DA27, "d94014",
     "opcode 66's 5th field is loaded with fld: a float duration"),
    (0x0091DA57, "d94010",
     "opcode 67's 4th field likewise"),
    (0x0081CC57, "8d5804",
     "the SOURCE buff list is at BuffState+0x04 -- lea ebx, [eax+4]"),
    (0x0081CE9A, "8d5814",
     "the TARGET buff list is a different one at BuffState+0x14"),
    (0x0081CD62, "c1e704",
     "a source buff record is 16 bytes -- shl edi, 4"),
    (0x0081CED8, "d9ee",
     "opcode 65 stores duration = 0.0f: an upkeep buff has no timer"),
    (0x0081CEF0, "c7401400000000",
     "and appliedAt = 0 with it"),
    (0x0081CF95, "c7460c00000000",
     "opcode 66 stores sourceAgent = 0: a timed buff has no maintainer"),
    (0x0081CFA7, "894614",
     "and stamps appliedAt with the skill timer instead"),
    (0x0081D051, "837f0c00",
     "which is why ExtendTimed asserts !buffTarget->sourceAgent"),
    # -- section 15, the agent-property dispatchers ---------------------
    (0x008129DA, "899e40060000",
     "property 10 stores the skill id at charContext+0x640"),
    (0x008129E2, "89bea4060000",
     "property 64 stores an AGENT id at charContext+0x6A4"),
    (0x0081311A, "c7874006000000000000",
     "the damage family clears +0x640 after consuming it"),
    (0x008131F4, "c7874006000000000000",
     "and so does the armour-ignoring family"),
    (0x007F78DB, "85f67414",
     "AvChar skips `stat == AV_CHAR_STAT_ENERGY` when stat is 0, so "
     "ENERGY is 0 and the 0/1 flag throughout is energy/health"),
    (0x00812B6C, "535157",
     "property 20 passes (agent, TARGET, value) ..."),
    (0x00812B7E, "535757",
     "... and property 21 passes the agent twice, which is exactly "
     "GWCA's effect_on_target / effect_on_agent"),
    (0x00812D17, "d905ac8d9400",
     "property 35 loads a compiled-in float constant"),
    (0x00813239, "d94514",
     "where property 63 takes its float from the wire -- same callee"),
]


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
    for va, want in LOG_STRINGS:
        eq(az.cstr(va), want, f"log string at 0x{va:08x}")

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
    eq(len(az.direct_callers(0x00821CC0)), 1,
       "opcode 211's write path has exactly one caller (its own handler)")
    eq(len(az.direct_callers(0x00822B80)), 2,
       "the SKILL_ACTIVATE path has two: the handler AND ChCliApiUseSkill")

    print("\n6. The two agent-property dispatchers")
    gimg = GV.Image(exe)
    table = GV.classify(gimg)
    ints = {i for i, (w, _) in table.items() if w == "int"}
    floats = {i for i, (w, _) in table.items() if w == "float"}
    pre = {i for i, (w, _) in table.items() if w == "int-pre"}
    none = {i for i, (w, _) in table.items() if w is None}
    eq(len(table), 67, "the client accepts property ids 0..66")
    check(len(GV.OPENTYRIA) == 66 and 66 not in GV.OPENTYRIA,
          "and OpenTyria's enum stops one short, at 65")
    eq(len(ints), 47, "int dispatcher case bodies")
    eq(len(floats), 14, "float dispatcher case bodies")
    eq(len(pre), 2, "handled only by the int pre-switch")
    eq(sorted(none), [5, 8, 40, 51], "handled by neither")
    both = GV.handled(gimg, GV.INT_SWITCH) & GV.handled(gimg, GV.FLOAT_SWITCH)
    check(not both, "the two switches are DISJOINT", f"overlap {sorted(both)}")
    eq(len(ints | floats | pre | none), 67, "and together they cover every id")
    eq(table[60][0], "int", "60 (skill_activated) is an int property")
    eq(table[63][0], "float", "63 (knocked_down) is a float property")
    eq(table[44][0], "float", "44 (health regen) is a float property")
    check(table[35][1] is not None and table[63][1] is not None,
          "35 and 63 both have case bodies (they share an AvApi callee)")
    # 4, 50 and 60 each have their OWN body in the main int switch, and all
    # three share one body in the pre-switch that runs before it. Both
    # lineages independently call those three "X started/activated"; the
    # binary bucketing exactly those three and no others is the corroboration.
    presw = GV.read_switch(gimg, GV.PRE_SWITCH)
    shared = {i for i, va in presw.items() if va == presw[4]}
    eq(sorted(shared), [4, 50, 60], "the pre-switch groups exactly 4, 50, 60")
    check(presw[4] != GV.PRE_SWITCH["default"],
          "and that group is a real body, not the fall-through")

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
