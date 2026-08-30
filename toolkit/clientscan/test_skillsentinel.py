r"""The duration-slot sentinel 0x20000 is ENERGY UPKEEP, in ArenaNet's own word.

    python toolkit/clientscan/test_skillsentinel.py

studies/skills 13 found that the skill record's duration slot (+0x44) holds
sentinels above 0x10000 for skills with no timed duration, and left "what the
enum means" NOT FOUND. This pins the answer (13.1, 2026-08-22) against the
client's own bytes so it cannot drift:

  * `effects.sentinel_name` names 0x20000 and only 0x20000 -- no vault needed.
  * STATIC (needs the pinned exe): the client reads +0x44 and exact-compares
    0x20000 in GmCtlSkCard.cpp, whose branch asserts `hasEnergyUpkeep`
    (ArenaNet's word); every skill in the full table carrying 0x20000 is an
    Enchantment; 0x30000 is not read at this slot and is not an upkeep flavor.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
import checks       # noqa: E402
import effects      # noqa: E402

# Floor from a real green run (11 checks, 2026-08-22) -- and 11 was the WHOLE
# run, not the mandatory core, which is the defect `checks.py` warns about in
# "HOW TO SET A FLOOR HONESTLY". Everything below §1 needs the pinned exe and
# declares one skip; §1 alone is what a machine without the vault can run.
#
# MEASURED 2026-08-30 rather than reasoned: `RURIK_VAULT` pointed at an empty
# directory gives **4 checks, 1 declared skip ("static witnesses")**. Against
# floor 11 that printed `ONLY 4 OF A DECLARED FLOOR OF 11 CHECKS RAN -- 7 did
# not execute, so this run is incomplete rather than passing`, which names the
# wrong thing: nothing failed to execute, a section declared itself absent.
# So the floor drops to the core, 4, per `checks.py`'s own guidance -- the same
# correction `test_compositetrap.py` took, 80 -> 78. It loses
# nothing that was being enforced, because the skip is printed either way.
#
# Before that day the bare run gave rc=1 and NO verdict: `pinned.find()` raises
# `SystemExit`, which the `except Exception` below did not catch, so the skip
# was unreachable and this whole paragraph had never been walked.
LEDGER = checks.Ledger("skill duration sentinel", floor=4)
check = checks.adopt(LEDGER)

ENCHANTMENT_TYPE = 6
UPKEEP = 0x20000

# ---------------------------------------------------------------- section 1
print("== 1. the name, server-side (no vault) ==")
check(effects.DURATION_ENERGY_UPKEEP == UPKEEP,
      "the named constant is 0x20000")
check(effects.sentinel_name(UPKEEP).startswith("energy upkeep"),
      "0x20000 is named 'energy upkeep (maintained enchantment)'",
      effects.sentinel_name(UPKEEP))
check(effects.sentinel_name(0x30000) == "no fixed duration"
      and effects.sentinel_name(999999) == "no fixed duration",
      "0x30000 and 999999 stay generic -- only 0x20000 has a client name")
# The refusal still fires, and now names upkeep.
try:
    effects.resolve_duration(
        {"duration0": UPKEEP, "duration15": UPKEEP, "skill_arguments": 0}, 12)
    check(False, "an upkeep sentinel must still refuse as a duration")
except effects.EffectError as ex:
    check("upkeep" in str(ex).lower(),
          "resolve_duration refuses the upkeep sentinel and names it",
          str(ex)[:60])

# ---------------------------------------------------------------- the exe
try:
    import pinned
    exe, _why = pinned.find()
except (Exception, SystemExit) as exc:                      # noqa: BLE001
    # SystemExit, and it has to be named: `pinned.find()` RAISES one when the
    # build is not in the vault, and `Exception` does not catch it -- so on a
    # machine without the vault this file printed section 1's four PASSes and
    # then died with rc=1 and no verdict, instead of declaring this skip.
    LEDGER.skip("static witnesses", f"pinned client unavailable: {exc}")
    sys.exit(LEDGER.verdict())

# ---------------------------------------------------------------- section 2
print("== 2. ArenaNet's own word: hasEnergyUpkeep in the skill card ==")
import asserts   # noqa: E402
A = asserts.Asserts(exe)
upkeep_asserts = [a for a in A.items if "hasEnergyUpkeep" in (a.expr or "")]
check(upkeep_asserts,
      "the image asserts `hasEnergyUpkeep` -- ArenaNet names the concept",
      f"{len(upkeep_asserts)} site(s)")
files = {a.module for a in upkeep_asserts}
check("GmCtlSkCard" in files,
      "and it is in GmCtlSkCard.cpp -- the skill-card tooltip",
      f"{sorted(files)}")
card = next((a for a in upkeep_asserts if a.module == "GmCtlSkCard"), None)
check(card is not None and "healthSacrifice" in card.expr,
      "the full assert is `!(hasEnergyUpkeep && skillData.healthSacrifice)`",
      card.expr if card else None)

# ---------------------------------------------------------------- section 3
print("== 3. the client exact-compares 0x20000 against a +0x44 read ==")
# A tiny targeted disasm: near the assert, the code must `cmp <reg>, 0x20000`
# on a value loaded from [reg+0x44]. Read the bytes around the card assert.
import struct
data = open(exe, "rb").read()
pe = struct.unpack_from("<I", data, 0x3C)[0]
nsec = struct.unpack_from("<H", data, pe + 6)[0]
osz = struct.unpack_from("<H", data, pe + 20)[0]
s0 = pe + 24 + osz
secs = []
for i in range(nsec):
    o = s0 + i * 40
    vs, va, rs, raw = struct.unpack_from("<IIII", data, o + 8)
    secs.append((va, max(vs, rs), rs, raw))


def read_va(va, n):
    rva = va - 0x400000
    for sva, size, rs, raw in secs:
        if sva <= rva < sva + size:
            o = rva - sva
            return data[raw + o:raw + min(rs, o + n)]
    return b""


# The card assert is at GmCtlSkCard:462; the +0x44 read + cmp 0x20000 sit just
# before it. Scan a 64-byte window ending at the assert site for the two
# encodings: `8B 46 44` (mov eax,[esi+0x44]) and `3D 00 00 02 00` (cmp eax,0x20000).
window = read_va(card.va - 0x40, 0x60)
check(b"\x8b\x46\x44" in window,
      "a `mov eax,[esi+0x44]` (read the duration slot) sits by the assert",
      "esi is a skill record -- the same function tests its flags at +0x10")
check(b"\x3d\x00\x00\x02\x00" in window,
      "and a `cmp eax, 0x20000` -- an EXACT compare, not a bit test",
      "so 0x30000 does not match this branch")

# ---------------------------------------------------------------- section 4
print("== 4. every 0x20000 skill is an Enchantment; 0x30000 is not this ==")
import skilltable   # noqa: E402
base, count, _score = skilltable.locate_table(data)
rows = [skilltable.parse_record(data, base, i) for i in range(count)]
upkeep = [r for r in rows if r["duration0"] == UPKEEP]
check(upkeep and all(r["type_code"] == ENCHANTMENT_TYPE for r in upkeep),
      "all skills carrying 0x20000 are type 6 (Enchantment Spell)",
      f"n={len(upkeep)}, types={sorted({r['type_code'] for r in upkeep})}")
other = [r for r in rows if r["duration0"] == 0x30000]
check(len({r["type_code"] for r in other}) > 3,
      "0x30000 spans MANY skill types -- it is a no-duration default, not an "
      "upkeep marker", f"n={len(other)}, "
      f"{len({r['type_code'] for r in other})} distinct types")

sys.exit(LEDGER.verdict())
