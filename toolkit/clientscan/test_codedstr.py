#!/usr/bin/env python3
"""Turn `studies/quests/FINDINGS.md` 3.2's 66 of 66 from a paragraph into a check.

    python toolkit/clientscan/test_codedstr.py

WHAT EARNS THIS FILE. Section 7.9 asked for it by name and said why: the coded
string rule was derived in `studies/textrec/FINDINGS.md` 4 from `TextParser.cpp`,
tested in quests 3.2 against 66 slots on ArenaNet's own wire -- a source the
textrec arc never had -- and the resulting "66 of 66, zero mismatches" lived only
in prose. Every authored quest string this repo sends is built on that rule and
every string id it reads out of a capture is decoded with it, so it is
load-bearing in both directions and nothing could turn it red.

THREE SECTIONS, SPLIT BY WHAT THEY NEED.

Section 1 is arithmetic and runs on a BARE MACHINE. It includes the two worked
examples 3.2 states -- 80660 -> `8102 3E14` and 0x3D64 -> 15460 -- which are the
useful kind of fixture: written down in a document BEFORE this module existed,
so they cannot have been back-fitted to the code.

Section 2 is the 66 of 66 itself, against the live corpus. Skips without it.

Section 3 is the check that SPLITS where a wrong reading would not, and it is
the one worth reading. All 66 slots resolving is weak evidence -- a wrong rule
also produces numbers. What is strong is that the numbers partition: slot 0 is
plain 22 of 22, slots 1 and 2 are encrypted 22 of 22, which is `textrec` 4's own
prediction confirmed on a source it never had. Under a wrong reading the plain
share would sit near the archive-wide ~28% rather than partitioning cleanly.

NO ARENANET TEXT IS ASSERTED ANYWHERE HERE, and that is deliberate rather than
incidental. 3.2's discriminator is that id 15460 resolves to a readable record
naming the region every captured session played in, while the rival raw-word
reading's 15716 resolves to an ENCRYPTED record, whose key this repo has not
recovered. The DISCRIMINATING part is the structure -- plain versus encrypted
-- not the word, so section 3 asserts the structure. Committing the word would
put ArenaNet's expression in the repo to prove something the id already proves.
(A first draft asserted the rival record was ABSENT and went red. 3.2 says
"an encrypted record returning nothing" and the nothing is the decoded TEXT --
the assertion was stronger than the evidence, not the document wrong.)
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, os.path.join(TOOLKIT, "authsrv"))
sys.path.insert(0, os.path.join(TOOLKIT, "schema"))

import checks    # noqa: E402
import codedstr  # noqa: E402

# MEASURED: 18 on the first green run with the vault present -- 12 in section 1,
# 2 in section 2, 4 in section 3. The floor is 12, section 1 alone, because
# sections 2 and 3 need the live corpus and the owner's archive; a floor above
# what a bare machine produces would make "the vault is not here"
# indistinguishable from "the codec broke". Both declare a skip, which checks.py
# prints and never scores green.
LEDGER = checks.Ledger("the coded string, and 3.2's 66 of 66", floor=12)
check = checks.adopt(LEDGER)

# The captures 3.2 measured. NAMED rather than globbed: the vault's capture tree
# is append-only and grows while the suite runs, so a glob would silently change
# this file's denominator -- the defect `test_smsgsweep.py` hit on 2026-08-17
# when its canon pin went red at 177 opcodes because two new Factions captures
# landed. A pinned number needs a pinned input set.
STAMPS = ("20260807T143055", "20260810T235916")
QUEST_ADDS = (0x0049, 0x0050)


def corpus_slots():
    """[(slot_index, [words])] for every EncString in every quest add."""
    import cmsgstream
    out = []
    for stamp in STAMPS:
        for _t, _conn, op, vals in cmsgstream.timed(stamp, "s2c", "game"):
            if op not in QUEST_ADDS:
                continue
            # BY TYPE, not by index: 0x0049 carries marker fields before its
            # strings and 0x0050 does not, so a shared index tuple is wrong for
            # one of them -- and wrong in the silent direction, since vals[2] is
            # a real value in both.
            strs = [v for v in vals if isinstance(v, str)]
            for slot, sval in enumerate(strs):
                words = codedstr.from_wire(sval)
                if words:
                    out.append((slot, words))
    return out


def main():
    print("1. the rule, on paper (no vault, no client)")
    # Both stated in FINDINGS 3.2 before this module existed.
    check(codedstr.encode_id(80660) == [0x8102, 0x3E14],
          "80660 encodes to the words ArenaNet sent for quest 1462's name",
          f"{[hex(w) for w in codedstr.encode_id(80660)]} -- 3.2's worked "
          f"example, written down before this code existed")
    check(codedstr.decode_id([0x3D64]) == (15460, 1),
          "and 0x3D64 decodes to 15460, not 15716",
          "the rival reading takes the raw word; section 3 is where that "
          "choice is settled against the archive rather than asserted")

    # 3.2's markup alphabet, all six.
    alphabet = {0x0101: 1, 0x0102: 2, 0x0104: 4, 0x0107: 7,
                0x0BA9: 2729, 0x0A86: 2438}
    bad = {hex(w): codedstr.decode_id([w])[0] for w, sid in alphabet.items()
           if codedstr.decode_id([w])[0] != sid}
    check(not bad, "the six markup ids 3.2 lists all decode",
          f"{bad} -- these resolve to plain, readable records without a key, "
          f"so they are the part of the rule that was already checkable")

    wrong = [n for n in (0, 1, 0xFF, 0x100, BASE - 1, BASE, BASE + 1,
                         BASE * BASE - 1, BASE * BASE, 80660, 15460, 999983)
             if codedstr.decode_id(codedstr.encode_id(n))[0] != n]
    check(not wrong, "encode and decode are inverse across the digit boundaries",
          f"{wrong} -- the interesting values are BASE-1/BASE/BASE+1, where a "
          f"carry that used 0x8000 or 0x100 wrongly shows up")
    widths = {len(codedstr.encode_id(n)) for n in (0, BASE - 1)}
    check(widths == {1}, "a sub-BASE id is ONE word",
          f"{widths} -- an encoder that always emitted two would still "
          f"round-trip and would not match ArenaNet's bytes")
    check(len(codedstr.encode_id(BASE)) == 2,
          "and BASE is the first id that needs two")

    for words, why in (([], "empty"), ([0x8102], "continuation off the end"),
                       ([0x8102, 0x8102], "continuation still set at the end")):
        try:
            codedstr.decode_id(words)
            raised = False
        except ValueError:
            raised = True
        check(raised, f"decode_id refuses {why} rather than guessing",
              "a silently wrong id resolves to a DIFFERENT record and reads as "
              "a plausible answer, which is how the rival reading survived")

    try:
        codedstr.decode_id([0x0053])
        marker_raised = False
    except ValueError:
        marker_raised = True
    check(marker_raised,
          "and refuses a MARKER word, naming WORD_VALUE_BASE",
          "0x53 is 'S'. A 0x004C description beginning with it killed a real "
          "client on TextApi.cpp:585 asserting exactly this bound, so the "
          "distinction is the client's own and not a convention of ours")

    parsed = codedstr.parse_coded([0x0BA9, 0x0107, 0x0053, 0x0001])
    check(parsed == [("id", 2729), ("id", 7), ("marker", 0x53), ("marker", 1)],
          "parse_coded splits a template literal into ids then markers",
          f"{parsed} -- this is `questdefs` template framing, and the two "
          f"leading ids are why it does not trip the assert above")
    check(codedstr.from_wire("㵤") == [0x3D64, 1]
          and codedstr.from_wire([0x3D64, 1]) == [0x3D64, 1],
          "from_wire takes codec.py's str OR a list of ints",
          "codec decodes a string16 to a str; a caller that forgets ord() gets "
          "characters where it wanted numbers -- FINDINGS 3.5's named trap")

    print("\n2. the 66 of 66, against ArenaNet's own words")
    try:
        slots = corpus_slots()
    except Exception as exc:                                    # noqa: BLE001
        slots = None
        LEDGER.skip("the corpus re-encode", f"{type(exc).__name__}: {exc}")
    if slots is not None:
        ok = sum(1 for _s, w in slots
                 if codedstr.encode_id(codedstr.decode_id(w)[0])
                 == w[:codedstr.decode_id(w)[1]])
        check(len(slots) == 66 and ok == 66,
              "every quest EncString's leading id re-encodes byte-identically",
              f"{ok} of {len(slots)} -- 3.2 measured 66 of 66 over the two "
              f"named captures. A different DENOMINATOR means the input set "
              f"moved, not that the codec broke; a different NUMERATOR is the "
              f"codec")

        shapes = collections.Counter(
            (s, "id-only" if codedstr.decode_id(w)[1] == len(w)
             else "id+trailing varint") for s, w in slots)
        check(dict(shapes) == {(0, "id-only"): 22,
                               (1, "id+trailing varint"): 22,
                               (2, "id+trailing varint"): 22},
              "and the per-slot shapes partition exactly as 3.2 recorded",
              f"{dict(shapes)} -- 44 of 44 name/NPC slots parsing as "
              f"`id + one trailing varint` is what closed half of "
              f"studies/textrec/FINDINGS.md:468's standing question")

    print("\n3. the split a wrong reading would not produce")
    ix = None
    if slots is None:
        LEDGER.skip("the plain/encrypted partition", "no corpus")
    else:
        try:
            import textrec
            import vaultpath
            ix = textrec.TextIndex(dat=vaultpath.vault_path("dat_study", "Gw.dat"))
        except Exception as exc:                                # noqa: BLE001
            LEDGER.skip("the plain/encrypted partition",
                        f"{type(exc).__name__}: {exc}")
    if ix is not None:
        try:
            per = collections.defaultdict(collections.Counter)
            for s, w in slots:
                k = ix.needs_key(codedstr.decode_id(w)[0])
                per[s]["absent" if k is None else
                       "encrypted" if k else "plain"] += 1
            check(dict(per[0]) == {"plain": 22},
                  "slot 0 is plain 22 of 22",
                  f"{dict(per[0])} -- textrec 4 predicted a bare string id "
                  f"takes the verbatim path and can only ever have been plain")
            check(dict(per[1]) == {"encrypted": 22}
                  and dict(per[2]) == {"encrypted": 22},
                  "and slots 1 and 2 are encrypted 22 of 22 each",
                  f"{dict(per[1])} / {dict(per[2])} -- the partition is the "
                  f"evidence. Under a wrong reading the plain share would sit "
                  f"near the archive-wide ~28%, not split cleanly by slot")
            absent = sum(c["absent"] for c in per.values())
            check(absent == 0, "and no id is absent from the archive",
                  f"{absent} -- an absent id is what a WRONG id looks like")

            check(ix.needs_key(15460) is False and ix.needs_key(15716) is True,
                  "CONTROL: the rival raw-word reading lands on an ENCRYPTED "
                  "record, ours on a plain one",
                  f"15460 needs_key={ix.needs_key(15460)}, "
                  f"15716 needs_key={ix.needs_key(15716)}. 0x3D64 is 15460 "
                  f"under `word - 0x100` and 15716 under the raw reading; one "
                  f"is readable without a key and the other is not, and this "
                  f"repo has not recovered that key. The rival COULD have won "
                  f"-- had 15716 been plain and readable, both readings would "
                  f"look equally good -- which is what makes this a control "
                  f"rather than a restatement. NOTE the exact claim: 3.2 says "
                  f"the rival resolves to \"an encrypted record returning "
                  f"nothing\", and the nothing is the decoded TEXT, not the "
                  f"record. A first draft of this check asserted `is None` and "
                  f"went red, which is the assertion being stronger than the "
                  f"evidence rather than the document being wrong. The text is "
                  f"never asserted here: the structure discriminates, and the "
                  f"word is ArenaNet's expression")
        finally:
            ix.close()

    return LEDGER.verdict()


BASE = codedstr.BASE

if __name__ == "__main__":
    raise SystemExit(main())
