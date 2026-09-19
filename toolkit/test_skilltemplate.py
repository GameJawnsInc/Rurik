"""The skill-template codec, and the client's own rule for a pasted code.

    python toolkit/test_skilltemplate.py

WHY. `studies/templates/FINDINGS.md` settles five claims about the "Load from
Skills Template" window by transcribing `AcctTemplate.cpp`'s encoder and
decoder out of build 38797. A transcription is worth exactly as much as the
thing that can refute it, so this file is built around one check that could
have failed and didn't:

  * **§2 is the load-bearing one. A 22-character code produced by ArenaNet's
    own client re-encodes to itself, byte for byte**, through a format we
    derived from the disassembly and not from any upstream description. That
    single identity pins the field order, all three width rules, the bit
    order, the alphabet and the byte-padding at once -- get any one of them
    wrong and the string differs. It is also the only check here whose input
    we did not manufacture.

  * §1 is the weaker sibling and is labelled as such: our encoder agreeing
    with our decoder proves nothing about the client. It is here to catch
    regressions, not to establish the format.

  * §5 runs the validity conjunction against the client's real tables, one
    clause at a time, and **the control is a bar that PASSES** -- without it a
    validator that refuses everything would score full marks on the failures.

WHAT IT DOES NOT ESTABLISH. That the `<= 13` header path means anything: the
current encoder never writes it, nothing in the corpus exercises it, and it is
transcribed rather than understood. And §2 is n=1 for an exact round trip --
the second real code (§2.2) decodes cleanly and is self-consistent but carries
a skill field WIDER than minimal, so it cannot round-trip and is asserted as a
decode only. `studies/templates/FINDINGS.md` §7.2 records why that is left
open rather than explained away.

Needs the vault for §2's verdicts and §5; §1, §3, §4 and §6 run bare.
Floor 35, ~6 s.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import checks                                                # noqa: E402
import skilltemplate as ST                                   # noqa: E402

# Floor set 2026-09-19 from two real green runs: 51 with the vault, 35
# without. The floor is the BARE number, because section 2's verdicts and all of
# section 5 need the client's tables and declare a skip when they are missing --
# checks.py's own advice is to floor the mandatory core, not the best case.
LEDGER = checks.Ledger("skill template codec", floor=35)
check = checks.adopt(LEDGER)


# The two codes are transcribed from a public forum screenshot of the client's
# own "Load from Skills Template" window -- i.e. the client produced them, not
# us, which is the whole point of section 2.
CODE_LURKER = "OgAAQHIIIJIKIVIAAAAAAA"
CODE_SINGLE = "OQAAQoB/MafqiIC9gRbyZA"


print("\n1. the format round-trips itself across every width regime")
# Weak on purpose (see the docstring): this is a regression net, not evidence.
CASES = [
    # (primary, secondary, attributes, skills, why this row is here)
    (1, 0, [], [0] * 8, "the empty bar: every selector at its floor"),
    (1, 2, [(17, 12), (20, 9)], [1, 2, 3, 0, 0, 0, 0, 0],
     "small ids: 4-bit professions, 4-bit attributes, 8-bit skills"),
    (10, 9, [(35, 0)], [255, 0, 0, 0, 0, 0, 0, 0],
     "skill 255 is the last that fits the 8-bit floor"),
    (10, 9, [(35, 0)], [256, 0, 0, 0, 0, 0, 0, 0],
     "skill 256 must widen the field to 9"),
    (1, 0, [(50, 1)], [2047, 0, 0, 0, 0, 0, 0, 0],
     "attribute 50 is the last id; skill 2047 the last 11-bit one"),
    (1, 0, [], [3442] * 8, "skill 3442 is SKILLS-1, the widest legal id"),
    (15, 15, [], [0] * 8, "profession 15 is the last that fits 4 bits"),
    (16, 0, [], [0] * 8, "profession 16 must widen the field to 6"),
    (1023, 0, [], [0] * 8,
     "profession 1023 is the widest the 2-bit selector can describe"),
]
for primary, secondary, attrs, skills, why in CASES:
    t = ST.Template(primary, secondary, attrs, skills)
    code = ST.encode(t)
    back = ST.decode(code)
    check((back.prof_primary, back.prof_secondary,
           back.attributes, back.skills) == (primary, secondary,
                                             list(map(tuple, attrs)), skills),
          f"round trip -- {why}", f"{code} -> {back!r}")

# The width rules, asserted as VALUES rather than as "it round-tripped", so a
# codec that agreed with itself at the wrong width would still be caught.
check(ST.decode(ST.encode(ST.Template(1, 0, [], [255] + [0] * 7)))
      .widths["skill"] == 8,
      "skill 255 encodes in an 8-bit field")
check(ST.decode(ST.encode(ST.Template(1, 0, [], [256] + [0] * 7)))
      .widths["skill"] == 9,
      "and 256 in a 9-bit one -- the selector is bsr(max)+1-8, floored at 0")
check(ST.decode(ST.encode(ST.Template(15, 0, [], [0] * 8)))
      .widths["prof"] == 4,
      "profession 15 encodes in a 4-bit field")
check(ST.decode(ST.encode(ST.Template(16, 0, [], [0] * 8)))
      .widths["prof"] == 6,
      "and 16 in a 6-bit one -- the selector steps TWO bits at a time")
check(ST.decode(ST.encode(ST.Template(1, 0, [(15, 0)], [0] * 8)))
      .widths["attrib"] == 4
      and ST.decode(ST.encode(ST.Template(1, 0, [(16, 0)], [0] * 8)))
      .widths["attrib"] == 5,
      "the attribute selector steps ONE bit at a time, unlike the profession")


print("\n2. a code the CLIENT produced, re-encoded by us, character for character")
single = ST.decode(CODE_SINGLE)
check(ST.encode(single) == CODE_SINGLE,
      "the client's own 22-character code re-encodes to itself exactly",
      f"{CODE_SINGLE} -> {ST.encode(single)}")
check((single.header, single.prof_primary, single.prof_secondary,
       single.attributes, single.widths["skill"], single.overran)
      == ((0xE, 0x0), 1, 0, [], 12, False),
      "-- and it reads as Warrior/none, no attributes, a 12-bit skill field")
check(single.skills == [104, 831, 2010, 2218, 136, 2109, 1745, 1650],
      "-- with these eight ids", repr(single.skills))

lurker = ST.decode(CODE_LURKER)
check(lurker.skills == [519, 520, 521, 522, 533, 0, 0, 0]
      and lurker.prof_primary == 2 and not lurker.overran,
      "the second code decodes to five ids and three empty slots, Ranger",
      repr(lurker.skills))
# Stated as a KNOWN gap rather than skipped, so it cannot quietly become true.
check(ST.encode(lurker) != CODE_LURKER,
      "-- and does NOT re-encode: its skill field is wider than minimal "
      "(FINDINGS section 7.2), which the decoder accepts and the encoder "
      "would never emit",
      f"{CODE_LURKER} vs {ST.encode(lurker)}")
check(ST.decode(ST.encode(lurker)).skills == lurker.skills,
      "-- the CONTENT survives the narrower re-encode, which is why the "
      "reading above stands either way")


print("\n3. the three ceilings the encoder asserts")


def refused(fn, *a):
    try:
        fn(*a)
    except (ValueError, ST.BadTemplate):
        return True
    except Exception:                                        # noqa: BLE001
        return False
    return False


check(refused(ST.encode, ST.Template(1024, 0, [], [0] * 8)),
      "profession 1024 is refused -- AcctTemplate:406 bitCountEncoding < 4")
check(not refused(ST.encode, ST.Template(1023, 0, [], [0] * 8)),
      "-- and 1023 is not, so the bound is exercised from both sides")
check(refused(ST.encode, ST.Template(1, 0, [(1, 1)] * 16, [0] * 8)),
      "16 attributes are refused -- AcctTemplate:423 attribCount < 16")
check(refused(ST.encode, ST.Template(1, 0, [], [ST.SKILLS] + [0] * 7)),
      f"skill id {ST.SKILLS} is refused -- AcctTemplate:465 skill < SKILLS")
check(not refused(ST.encode, ST.Template(1, 0, [], [ST.SKILLS - 1] + [0] * 7)),
      f"-- and {ST.SKILLS - 1} is not")
check(ST.SKILLS == 3443 and ST.CHAR_ATTRIBS == 51
      and ST.CHAR_PROFESSIONS == 11,
      "the three table sizes are the client's own, not ours",
      "ConstSkill:3833, ConstAttrib 0x33, AcctTemplate:411")


print("\n4. what is not a template code at all")
check(refused(ST.decode, ""), "the empty string is refused")
check(refused(ST.decode, "!!!!"), "a string with no alphabet character is refused")
# 0x0091D268: nibble 0xF is the one header the client rejects outright. 'P' is
# base64 index 15, so its low four bits are 0xF.
check(refused(ST.decode, "PAAAAAAAAAAAAAAAAAAAAA"),
      "header nibble 0xF is refused -- the client's own `test eax, 0xFFFFFFF1`")
check(not refused(ST.decode, CODE_SINGLE),
      "-- control: the real code, one nibble away, is not refused")
truncated = ST.decode(CODE_SINGLE[:8])
check(truncated.overran,
      "a truncated code sets the overrun flag the client's last term reads",
      "0x004C9A20 reads reader+0x00")
check(not ST.decode(CODE_SINGLE).overran,
      "-- and the whole code does not")
# The client's reader stops at the first character outside the alphabet rather
# than refusing (0x0091C385), so a pasted cursor or quote truncates silently.
check(ST.decode(CODE_SINGLE + '"').skills == single.skills,
      "trailing junk is ignored, not refused -- it stops the scan")


print("\n5. the client's validity conjunction, against its own tables")
try:
    TABLES, why = ST._tables_from_vault()
    print(f"   tables: {why}")
except BaseException as exc:                                 # noqa: BLE001
    TABLES = None
    LEDGER.skip("section 5 and section 2's verdicts",
                f"the client's tables are unavailable: {exc}")

if TABLES is not None:
    # THE CONTROL, and it comes first. Build a bar that must pass: a Warrior
    # primary with only loadable Warrior skills and only Warrior attributes.
    # Picked from the tables rather than typed in, so it cannot rot.
    war = [i for i in range(1, ST.SKILLS)
           if (TABLES.skill_row(i) or {}).get("equip_family") == 1
           and (TABLES.skill_row(i) or {}).get("profession") == 1][:8]
    watt = [a for a in range(ST.CHAR_ATTRIBS)
            if TABLES.attrib_profession(a) == 1][:3]
    good = ST.Template(1, 0, [(a, 9) for a in watt], war)
    ok, whys = ST.validate(good, TABLES)
    check(ok, "CONTROL: a legal Warrior bar passes every clause",
          f"skills={war} attributes={watt} -- {whys}")
    check(len(war) == 8 and len(watt) == 3,
          "-- and the control was actually populated from the tables",
          f"{len(war)} skills, {len(watt)} attributes")

    def fails_on(t, needle):
        ok_, why_ = ST.validate(t, TABLES)
        return (not ok_) and any(needle in w for w in why_)

    check(fails_on(ST.Template(0, 0, [], war), "CHAR_PROFESSION_NONE"),
          "profPrimary 0 fails -- the client requires a primary profession")
    check(fails_on(ST.Template(11, 0, [], war), "CHAR_PROFESSIONS"),
          "profPrimary 11 fails -- AcctTemplate:411's bound, in the decoder")
    check(fails_on(ST.Template(1, 0, [(watt[0], 13)], war), "rank 13 > 12"),
          "an attribute rank of 13 fails -- the decoder's own `<= 12`")
    check(fails_on(ST.Template(1, 0, [(a, 9) for a in watt] * 4, war),
                   "attribCount"),
          "twelve attributes fail -- the count bound is `< 12`, not `<= 12`")

    # The two clauses the forum thread is actually about.
    monster = [i for i in range(1, ST.SKILLS)
               if (TABLES.skill_row(i) or {}).get("equip_family") != 1][:1]
    check(fails_on(ST.Template(1, 0, [], monster + [0] * 7), "not loadable"),
          "a skill outside equip_family 1 fails -- the `loadable` clause",
          f"skill {monster[0]}")
    other = [i for i in range(1, ST.SKILLS)
             if (TABLES.skill_row(i) or {}).get("equip_family") == 1
             and (TABLES.skill_row(i) or {}).get("profession") == 4][:1]
    check(fails_on(ST.Template(1, 0, [], other + [0] * 7), "profession 4"),
          "a loadable Necromancer skill on a Warrior template fails")
    check(ST.validate(ST.Template(1, 4, [], other + [0] * 7), TABLES)[0],
          "-- and passes once Necromancer is the SECONDARY, which is the "
          "clause being tested rather than the skill being bad")

    # A primary attribute belongs to the PRIMARY profession only. This is the
    # clause `0x0091CC87` adds on top of the pair membership, and it is the
    # one a validator that only checked the pair would miss.
    prim1 = [a for a in range(ST.CHAR_ATTRIBS)
             if TABLES.attrib_profession(a) == 1
             and TABLES.attrib_is_primary(a) == 1]
    check(len(prim1) == 1, "profession 1 has exactly one primary attribute",
          repr(prim1))
    check(fails_on(ST.Template(4, 1, [(prim1[0], 5)], [0] * 8), "PRIMARY"),
          "Warrior's primary attribute on a Necromancer/Warrior bar fails")
    check(ST.validate(ST.Template(1, 4, [(prim1[0], 5)], [0] * 8), TABLES)[0],
          "-- and passes with Warrior primary; the pair-membership clause "
          "alone would have accepted both")

    # Section 2's codes, now with the verdict the client would reach.
    ok_s, why_s = ST.validate(single, TABLES)
    check((not ok_s) and all("profession" in w for w in why_s)
          and len(why_s) == 5,
          "the Single Lurker code is blanked, and ONLY for profession "
          "mismatches -- every one of its eight skills is loadable",
          repr(why_s))
    ok_l, why_l = ST.validate(lurker, TABLES)
    check((not ok_l) and len(why_l) == 5
          and all("not loadable" in w for w in why_l),
          "the Nature Lurker code is blanked, and ONLY because all five of "
          "its skills are outside equip_family 1",
          repr(why_l))
    check(all((TABLES.skill_row(s) or {}).get("equip_family") == 3
              for s in lurker.skills if s),
          "-- they are all equip_family 3, and none is flagged pvp_only",
          "the thread said 'monster only skill'; family 3 is what that is")


print("\n6. the encoder cannot filter, because it cannot look anything up")
# Not a disassembly assertion -- that lives in the study. This is the
# observable consequence, and it is the arc's headline: the client hands you a
# code it will not read back.
mon = ST.Template(2, 0, [], [519, 520, 521, 522, 533, 0, 0, 0])
emitted = ST.encode(mon)
check(isinstance(emitted, str) and len(emitted) > 8,
      "a bar of monster skills encodes without complaint", emitted)
check(ST.decode(emitted).skills == mon.skills,
      "-- and decodes back to the same ids, so the format is not the refusal")
if TABLES is not None:
    check(not ST.validate(ST.decode(emitted), TABLES)[0],
          "-- yet the client would blank it: the asymmetry IS the mechanism")

sys.exit(LEDGER.verdict())
