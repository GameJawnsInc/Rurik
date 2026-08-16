#!/usr/bin/env python3
"""Check the quest table and the coded string its prose goes on the wire as.

    python toolkit/test_quests.py

WHAT EARNS THIS FILE. `studies/quests/FINDINGS.md` 7.9 asked for it by name and
said why: a quests table with nothing checking it is precisely the "rule nothing
checks is a wish" CLAUDE.md opens with. Every assertion below is one the
ARTIFACT can refute -- a fabricated id, a description that will not fit the
client's field, a framing constant that drifted from the captures it was read
out of.

NO VAULT, NO CLIENT, NO SOCKET. Everything here is the content store and pure
arithmetic, so it cannot skip and its floor is its whole count.

THE ONE THING IT DELIBERATELY DOES NOT ASSERT is which framing is CORRECT.
`bare` and `template` are two spellings of the same sentence and only a client
can say which renders; asserting one here would be this repo's favourite bug --
two of our own components agreeing and calling it evidence.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "authsrv"))

import checks                                                # noqa: E402
import content                                               # noqa: E402
import questdefs                                             # noqa: E402

# MEASURED: 21 against today's two-row table. The floor is 17, not 21, and the
# derivation matters -- per checks.py's own rule, pin it to the mandatory core.
# Sections 0 (2), 2 (2), 4 (4), 5 (2) and 6 (3) are row-count INDEPENDENT = 13.
# Sections 1, 3 and 7 add 4 per quest row. So one row is the smallest table that
# can exist at all, and 13 + 4 = 17 is what it executes. Pinning 21 would turn
# "somebody retired a quest row" into a red suite, which is the failure mode
# checks.py names; section 0's first check already catches an EMPTY table.
LEDGER = checks.Ledger("the quest table and its coded strings", floor=17)
check = checks.adopt(LEDGER)

# MEASURED, build 38797: UiCtlWebLink.cpp:576 asserts `challengeId < CHALLENGES`
# and compiles to `cmp edi, 0x5b9`. There is no high band to author into -- the
# corpus maximum is 1462, so 1463 and 1464 are the only free ids beneath it.
CHALLENGES = 1465
# Quest ids seen on ArenaNet's own wire in vault/captures/live/.
OBSERVED_IDS = {62, 80, 82, 86, 218, 222, 1462}


def main():
    world = content.load()
    rows = questdefs.load(world)

    print("0. the table loads at all")
    check(bool(rows), "content/ holds at least one quest row", f"{len(rows)}")
    check(all(isinstance(q, int) for q in rows),
          "every row is keyed by an integer quest id the wire could carry")

    print("\n1. ids are inside the client's own bound, and are ours")
    for qid, row in sorted(rows.items()):
        check(qid < CHALLENGES,
              f"quest {qid} ({row['_name']}) is under CHALLENGES={CHALLENGES}",
              "UiCtlWebLink.cpp:576 -- a higher id trips a retail assert")
        check(qid not in OBSERVED_IDS,
              f"quest {qid} does not collide with an id ArenaNet uses",
              "authoring over a real id would make our quest and theirs "
              "indistinguishable in any future capture")

    print("\n2. provenance is ENFORCED on a quest row, not merely present")
    # `rows()` returns the row with provenance already stripped -- content.py
    # validates it at load and does not retain it -- so "the row has a source"
    # is not a question this API can be asked. The question that matters is
    # whether the LOADER would refuse a quest row that lacked one, and the only
    # way to ask it is to write one and try.
    #
    # This is the difference between a check and a decoration: reading a field
    # back out of a dict we just built proves nothing about the gate.
    good = ('[quest.t]\nquest_id = 1463\ndescription = "d"\n'
            'objectives = "o"\nwire_framing = "bare"\n'
            '[quest.t.provenance]\nsource = "invented"\n')
    bad = ('[quest.t]\nquest_id = 1463\ndescription = "d"\n'
           'objectives = "o"\nwire_framing = "bare"\n')
    tmp = os.path.join(HERE, "_quests_provenance_probe")
    try:
        os.makedirs(tmp, exist_ok=True)
        path = os.path.join(tmp, "quests.toml")

        def loads(text):
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            try:
                w = content.load(repo_dir=tmp)
                return len(w.rows("quest")) == 1
            except Exception:
                return False

        check(loads(good),
              "a quest row WITH a provenance source loads",
              "the positive control -- a gate that refuses everything would "
              "pass the next check while being useless")
        check(not loads(bad),
              "and one WITHOUT is REFUSED by the loader",
              "content.py:194-201; this is what makes `source = \"invented\"` "
              "an obligation rather than a comment")
    finally:
        for f in os.listdir(tmp) if os.path.isdir(tmp) else []:
            os.remove(os.path.join(tmp, f))
        if os.path.isdir(tmp):
            os.rmdir(tmp)

    print("\n3. the prose fits the client's field, framing included")
    for qid, row in sorted(rows.items()):
        desc, obj = questdefs.description_fields(row)
        check(0 < len(desc) <= questdefs.FIELD_UNITS
              and len(obj) <= questdefs.FIELD_UNITS,
              f"quest {qid}'s description and objectives fit "
              f"{questdefs.FIELD_UNITS} code units",
              f"description {len(desc)}, objectives {len(obj)}")

    print("\n4. the framing is the one the captures show, and it is REVERSIBLE")
    # The refutable half. `template` must add exactly the three measured words
    # and change nothing else; strip them and the bare form must come back
    # character for character. A framing that mangled the payload would still
    # "fit the field" and still look fine in section 3.
    text = "Speak to the gate guard, then return to me."
    framed = questdefs.coded_literal(text, "template")
    check([ord(c) for c in framed[:2]]
          == [questdefs.TEMPLATE_STR1, questdefs.LITERAL_MARK]
          and ord(framed[-1]) == questdefs.LITERAL_END,
          "template framing is 0x0BA9 0x0107 <text> 0x0001",
          "the three constants measured off ArenaNet's own 0x004C")
    check(framed[2:-1] == text,
          "and stripping the framing returns the text exactly",
          "a framing that reordered or dropped a code unit would still fit "
          "the field and still pass section 3")
    check(len(framed) == len(text) + 3,
          "template costs exactly three code units of the 128")
    check(ord(framed[0]) >= 0x100,
          "and the FIRST word is >= 0x100, which is the whole point",
          "TextApi.cpp:585 asserts exactly this and the client dies otherwise")

    print("\n5. why bare cannot carry prose -- MEASURED, not predicted")
    # On 2026-08-15 a 0x004C whose description began 0x53 ('S') killed a real
    # client: `(codedString[0] & ~WORD_BIT_MORE) >= WORD_VALUE_BASE`,
    # TextApi.cpp:585, build 38833, with the sentence verbatim in the crash
    # stack. These two checks are why that can no longer reach a client.
    check(all(ord(c) < 0x100 for c in text),
          "every code unit of our prose is below 0x100",
          "so it cannot introduce a literal run -- the coded-string rule reads "
          "each one as a marker")
    check(questdefs.TEMPLATE_STR1 >= 0x100,
          "while the template id is above it, and so is a varint")
    # `bare` is still legitimate for a payload that ALREADY starts with an id,
    # which is what Q0 sent. The guard must not have thrown that away.
    with_id = questdefs.coded_literal(chr(0x3D64) + "x", "bare")
    check(with_id == chr(0x3D64) + "x",
          "bare still passes a payload that already starts with a string id",
          "Q0's own shape -- a guard that refused this would have broken the "
          "one string path already proven to render")

    print("\n6. the refusals -- a guard that cannot fire is not a guard")
    def refused(fn, *a):
        try:
            fn(*a)
            return False
        except ValueError:
            return True
    check(refused(questdefs.coded_literal, "x", "no-such-framing"),
          "an unknown wire_framing is refused, not defaulted")
    check(refused(questdefs.coded_literal, "Speak to the guard.", "bare"),
          "A BARE LITERAL STARTING BELOW 0x100 IS REFUSED BEFORE THE WIRE",
          "this exact payload crashed a real client on TextApi.cpp:585 -- the "
          "guard turns a measured crash into a refusal, and the failure mode "
          "it prevents is a crash DIALOG, not a bad glyph")
    check(refused(questdefs.coded_literal, "x" * 200, "template"),
          "prose past the field width is REFUSED rather than truncated",
          "a clipped description renders as half a sentence and reads as a "
          "client fault")
    check(refused(questdefs.coded_literal, "x" * 126, "template"),
          "and the framing's own three units count against the limit",
          "126 fits bare and does not fit template -- an off-by-three here "
          "would only ever show up on screen")

    print("\n7. the enc_* columns are WIRE code units, not archive string ids")
    # The trap FINDINGS 3.5 names: 0x3D64 on the wire denotes archive id 15460.
    # Conflating them resolves to 15716, an encrypted record returning None.
    for qid, row in sorted(rows.items()):
        enc = row.get("enc_name") or []
        check(all(int(u) >= 0x100 for u in enc),
              f"quest {qid}'s enc_name words are all >= 0x100",
              "a sub-0x100 word in an id slot is a marker, not a string id")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
