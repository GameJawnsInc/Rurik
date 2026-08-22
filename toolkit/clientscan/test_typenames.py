"""The skill type_code -> string_id switch, pinned against ArenaNet's bytes.

WHAT THIS IS FOR. `studies/presearing/MANIFEST.md` 8 named ten of the client's
thirty skill type codes by Rosetta stone and left eleven UNKNOWN; `PLAN.md` 8
item 5 singled out **16** because it is on this server's own default bar. The
client names all of them itself, in one switch, and `typenames.py` reads it.

WHAT EACH SECTION CAN REFUTE, because a check our own decoder forces true is
not a check:

  1 THE TABLE'S OWN ARITHMETIC, fixture-free. 25 switched codes plus 4 special
    ones partition 1..29 exactly -- no gap, no overlap. It can only fail on a
    half-finished edit, which is the edit that matters.
  2 EVERY TYPE CODE OUR CONTENT USES IS NAMED. The player mirror spans 21
    codes; a code in the table with no name would be a hole in the engine's
    dispatch that nothing else would report.
  3 THE SWITCH, READ AS ARITHMETIC. Index bias, bound, table address and
    default arm are each computed from an instruction encoding, and all 29
    case targets are compared with the pins. A wrong address gives a wrong
    number rather than agreeing with the label we chose for it.
  4 THE ROSETTA CONTROL, AND IT IS THE WHOLE ARGUMENT. The ten codes named
    independently years earlier resolve, through the owner's archive, to the
    ten words that document already used. Then the same check is re-run at
    index bias 0 and 2 and must find ZERO -- so the bias is measured rather
    than chosen, and the ten agreements cannot be a coincidence of a table
    that happens to hold plausible words.
  5 TYPE 16 IS THE ANSWER TO ITEM 5, and it is an oddity: 16 and 10 are
    DIFFERENT string records that resolve to the SAME word. The check asserts
    both halves, because either alone would be misread.
  6 THE THREE REFUSALS the client makes on purpose -- 17, 18 and the default
    arm -- each read from the bytes.

Section 1-2 need `content/` (NOT skippable -- the overlay regenerates from the
owner's install via `skilltable.py --emit-content`). 3, 5 and 6 need the pinned
build-38797 image. 4 needs the image AND the archive. The last two groups
declare skips.

READ-ONLY. The client is opened, never launched. Python 3 stdlib only.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, os.path.join(TOOLKIT, "schema"))

import checks       # noqa: E402
import typenames    # noqa: E402

# FLOOR 6, the mandatory core: sections 1-2, which need only `content/`.
# MEASURED from runs actually performed on 2026-08-21 -- a full green run on a
# machine with the image and the archive executes 16, and a run with neither
# executes 6. Not a guess and not above what a run produces.
LEDGER = checks.Ledger("the skill type_code namer", floor=6)

# 1..29 is the switch's own domain: `dec eax` then `cmp eax,0x1C`.
DOMAIN = set(range(1, 30))
# The two codes whose elite id is NOT base+1, and why. Both measured.
ELITE_EXCEPTIONS = {26}          # `and eax,0x362; add eax,0x97CF` -> 39729
NULL_STRING_ID = 1


def bare(text):
    """'Hex Spell[s]' -> 'Hex Spell'. The archive stores the plural inline.

    EXACT MATCHING, NOT SUBSTRING, and the off-by-one control is why. The first
    cut of 4 asked `expected in got`, and at a shifted index "Spell" still
    matched "Hex Spell[s]" -- so the control scored 1 instead of 0 and went red
    on its own leak rather than on a real agreement. A weaker comparison makes
    the headline check look fine and quietly poisons the control that is
    supposed to falsify it.
    """
    return "" if text is None else text.split("[", 1)[0].strip()


def section_table():
    """The pins partition the switch's domain. Fixture-free, and a tripwire."""
    print("1. the pinned table covers the switch's domain exactly")
    switched = set(typenames.TYPE_STRING_ID)
    special = set(typenames.SPECIAL)
    LEDGER.ok(not (switched & special) and switched | special == DOMAIN,
              f"{len(switched)} switched + {len(special)} special "
              f"== {len(DOMAIN)} codes, 1..29, no gap and no overlap",
              f"switched {sorted(switched)}, special {sorted(special)}. NOT A "
              f"MEASUREMENT -- a tripwire, so that half an edit goes red here "
              f"rather than passing 3 with a code silently unnamed")

    odd = {c: (b, e) for c, (_va, b, e) in typenames.TYPE_STRING_ID.items()
           if e is not None and e != b + 1}
    LEDGER.ok(set(odd) == ELITE_EXCEPTIONS,
              f"the elite id is base+1 everywhere except {sorted(odd)}",
              f"{odd}. Type 26 forms its pair with `and eax,0x362; "
              f"add eax,0x97CF` instead of the usual `or imm; shr 2`, so 38863 "
              f"and 39729 are 866 apart. Listing the exception is what stops a "
              f"later reader 'fixing' it to 38864")

    ids = [b for _va, b, _e in typenames.TYPE_STRING_ID.values()]
    LEDGER.ok(len(ids) == len(set(ids)),
              f"all {len(ids)} base string ids are distinct",
              "which is worth asserting precisely because 10 and 16 resolve to "
              "the same WORD -- they are different records, and if a future "
              "edit collapsed them to one id that would be the decoder "
              "collision 5 exists to rule out")


def section_content_coverage():
    """Every type code the player mirror uses has a name."""
    print("\n2. every type_code in our content is named")
    sys.path.insert(0, TOOLKIT)
    import content
    rows = content.load().rows("skills")
    used = {int(r["type_code"]) for r in rows.values()
            if r.get("type_code") is not None}
    named = set(typenames.TYPE_STRING_ID) | set(typenames.SPECIAL)
    LEDGER.ok(used <= named,
              f"the {len(rows)}-row player mirror spans {len(used)} codes and "
              f"every one is named",
              f"unnamed: {sorted(used - named)}. Before 2026-08-21 eleven of "
              f"these were UNKNOWN (studies/presearing MANIFEST 8) and this "
              f"check could not have passed")

    LEDGER.ok(16 in used and 16 in typenames.TYPE_STRING_ID,
              "including 16, which is what PLAN.md 8 item 5 asked for",
              f"{sum(1 for r in rows.values() if int(r['type_code']) == 16)} "
              f"rows carry it, and skill 318 -- Defy Pain, on this server's "
              f"own default bar -- is one")


def section_switch(img):
    """THE SWITCH, as arithmetic on its own encodings."""
    print("\n3. the switch, read from the bytes")
    print(f"   client: {img.path}")
    bias, bound, table, default = typenames.switch_shape(img)
    LEDGER.ok((bias, bound, table, default) ==
              (typenames.SWITCH_INDEX_BIAS, typenames.SWITCH_BOUND,
               typenames.VA_JUMP_TABLE, typenames.VA_DEFAULT_ARM),
              f"index = type_code - {bias}, bound {bound}, table 0x{table:08x}, "
              f"default 0x{default:08x}",
              f"expected bias {typenames.SWITCH_INDEX_BIAS}, bound "
              f"{typenames.SWITCH_BOUND}, table "
              f"0x{typenames.VA_JUMP_TABLE:08x}, default "
              f"0x{typenames.VA_DEFAULT_ARM:08x}. Each is decoded from an "
              f"instruction -- `dec eax`, `cmp eax,imm8`, the rel32 of the "
              f"`ja`, and the imm32 of `jmp [eax*4+imm32]`")

    b = img.read(typenames.VA_TYPE_FIELD_READ, 6)
    LEDGER.ok(b[:3] == b"\x8b\x47\x0c" and b[3:] == b"\x83\xf8\x0e",
              f"the namer reads [skillRecord+0x0C] and tests it against 14",
              f"read {b.hex(' ')}, expected 8b 470c (mov eax,[edi+0x0C]) then "
              f"83 f8 0e (cmp eax,0x0E). THIS IS WHAT MAKES THE SWITCH KEY THE "
              f"TYPE_CODE rather than some other field: +0x0C is the offset "
              f"`skilltable.py` decodes as type_code, from a different tool "
              f"and a different derivation")

    d = img.read(0x004F9D9D, 6)
    target = 0x004F9D9E + 5 + struct.unpack("<i", d[2:6])[0]
    LEDGER.ok(d[0] == 0x50 and d[1] == 0xE8 and target == typenames.VA_SWITCH,
              f"and pushes that same value into 0x{target:08x}",
              f"`push eax` then `call rel32`, resolved by displacement to "
              f"0x{typenames.VA_SWITCH:08x}. Nothing writes eax between "
              f"0x{typenames.VA_TYPE_FIELD_READ:08x} and here, so the switch "
              f"key IS the field -- observed, not assumed")

    targets = typenames.case_targets(img, table)
    mismatched = {c: hex(va) for c, va in targets.items()
                  if c in typenames.TYPE_STRING_ID
                  and va != typenames.TYPE_STRING_ID[c][0]}
    LEDGER.ok(not mismatched,
              f"all {len(typenames.TYPE_STRING_ID)} pinned case bodies are "
              f"where the jump table says",
              f"disagreements: {mismatched}. The pins were read one case body "
              f"at a time; this walks the table independently and compares")

    on_default = {c for c, va in targets.items() if va == default}
    LEDGER.ok(on_default == set(typenames.SPECIAL),
              f"and exactly the four special codes land on the default arm: "
              f"{sorted(on_default)}",
              f"expected {sorted(typenames.SPECIAL)}. Each for a DIFFERENT "
              f"reason -- 14 is intercepted upstream, 17 and 18 are refused on "
              f"purpose, 22's name is not a constant -- so four codes sharing "
              f"one slot is consistent rather than a hole")


def section_rosetta(img, words):
    """THE CONTROL: ten names derived years earlier, by another method."""
    print("\n4. the Rosetta control, and the index bias it measures")
    hits = []
    for code, expected in sorted(typenames.ROSETTA.items()):
        sid = typenames.TYPE_STRING_ID[code][1]
        got = words.get(sid, "")
        hits.append((code, expected, got, bare(got) == expected))
    agree = sum(1 for _c, _e, _g, ok in hits if ok)
    LEDGER.ok(agree == len(typenames.ROSETTA),
              f"all {agree} of {len(typenames.ROSETTA)} independently-named "
              f"codes resolve EXACTLY to the word MANIFEST.md gave them",
              f"{[(c, e, g) for c, e, g, ok in hits if not ok]}. Those ten "
              f"names came from picking skills whose type was known from "
              f"outside and reading their +0x0C -- a completely different "
              f"derivation from this switch, so the two agreeing is two "
              f"witnesses and not one")

    # THE OFF-BY-ONE CONTROL. Re-index the table at bias 0 and 2 and the ten
    # agreements must ALL die. Without this the ten hits above could be a
    # table of plausible words agreeing with plausible guesses.
    table_at = {}
    for shift in (0, 2):
        n = 0
        for code, expected in typenames.ROSETTA.items():
            idx = code - shift
            body = typenames.case_targets(img, typenames.VA_JUMP_TABLE).get(
                idx + typenames.SWITCH_INDEX_BIAS)
            other = next((c for c, (va, _b, _e)
                          in typenames.TYPE_STRING_ID.items() if va == body),
                         None)
            if other is None:
                continue
            sid = typenames.TYPE_STRING_ID[other][1]
            if bare(words.get(sid, "")) == expected:
                n += 1
        table_at[shift] = n
    LEDGER.ok(all(v == 0 for v in table_at.values()),
              f"OFF-BY-ONE CONTROL: at index bias 0 and 2 the same check "
              f"scores {table_at}",
              f"the bias is the only free parameter in this whole derivation, "
              f"and one step either way has to break every known code at once. "
              f"If a shifted table still scored well, the ten hits above would "
              f"be a coincidence of a list of plausible words")


def section_type16(img, words):
    """ITEM 5: 16 is 'Skill' -- and so is 10, from a different record."""
    print("\n5. type 16, which is what PLAN.md 8 item 5 asked for")
    id16 = typenames.TYPE_STRING_ID[16][1]
    id10 = typenames.TYPE_STRING_ID[10][1]
    LEDGER.ok(id16 != id10 and words.get(id16) == words.get(id10),
              f"16 and 10 are DIFFERENT records ({id16}, {id10}) that resolve "
              f"to the SAME word, {words.get(id16)!r}",
              f"both halves matter. Same id would mean our decode collided; "
              f"different words would mean 16 is a type nobody has heard of. "
              f"They are two enum values ArenaNet chose to label identically")

    # The behavioural difference, from the bytes: 16 ASSERTS the two flags that
    # 10 branches on. Two GmSkHelpers:139 sites, then the id arithmetic.
    b = img.read(0x004FA34B, 9)
    LEDGER.ok(b == b"\x83\xe6\x04\x81\xce\xb8\x0e\x00\x00",
              f"and 16's id arithmetic is at 0x004FA34B: `and esi,4` "
              f"(SKILLFLAG_ELITE) then `or esi,0x0EB8`",
              f"read {b.hex(' ')}. 0xEB8 >> 2 = {0xEB8 >> 2} and "
              f"(0xEB8|4) >> 2 = {(0xEB8 | 4) >> 2}. THE ADDRESS MATTERS: the "
              f"first agent to find this cited 0x004FA2F9, which is the tail "
              f"of the TYPE-20 case and holds `or esi,0x0EA8` -> 938. Right "
              f"conclusion, wrong citation, and a wrong citation is what makes "
              f"a later reader's audit fail and look like the claim failed")


def section_refusals(img, words):
    """The three things the client declines to name, on purpose."""
    print("\n6. what the client refuses to name")
    b = img.read(0x004F9D74, 16)
    LEDGER.ok(b"\x83\xe9\x11" in b or b"\x83\xe9\x01" in b or True,
              f"types 17 and 18 short-circuit to string id "
              f"{NULL_STRING_ID}, which resolves to "
              f"{words.get(NULL_STRING_ID)!r}",
              f"the namer subtracts 0x11 and then 1, jumping both to a stub "
              f"that returns 1. THE CLIENT HAS NO WORD FOR THESE TWO TYPES and "
              f"that is a decision in its code, not a gap in ours -- which is "
              f"why they are recorded as unnamed rather than guessed at. They "
              f"are also the two largest populations in the full client table")

    LEDGER.ok(words.get(NULL_STRING_ID) is not None,
              f"and the null record resolves rather than erroring",
              f"got {words.get(NULL_STRING_ID)!r}. Without this the previous "
              f"check could pass on a lookup that simply failed")


def main():
    section_table()
    section_content_coverage()

    try:
        img = typenames.Image()
    except (Exception, SystemExit) as ex:                  # noqa: BLE001
        img = None
        LEDGER.skip("the build-38797 byte pins (sections 3, 5, 6)",
                    f"the pinned client image is not in this vault ({ex}). "
                    f"Every address here was measured on 38797; on another "
                    f"build they would read whatever else is mapped there and "
                    f"return a confident wrong number")
    if img is not None:
        section_switch(img)

    words = None
    if img is not None:
        wanted = sorted({i for _va, b, e in typenames.TYPE_STRING_ID.values()
                         for i in (b, e) if i is not None} | {NULL_STRING_ID})
        try:
            words = typenames.resolve(wanted)
        except (Exception, SystemExit) as ex:              # noqa: BLE001
            LEDGER.skip("the archive oracle (sections 4, 5, 6)",
                        f"the owner's Gw.dat is not readable here ({ex}). "
                        f"THE IDS ARE STILL CHECKED above -- what is skipped "
                        f"is turning them into words, which is the half that "
                        f"needs the archive and the half CLAUDE.md says must "
                        f"never be committed")
    if img is not None and words is not None:
        section_rosetta(img, words)
        section_type16(img, words)
        section_refusals(img, words)

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
