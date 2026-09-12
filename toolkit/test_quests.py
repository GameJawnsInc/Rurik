#!/usr/bin/env python3
"""Check the quest table and the coded string its prose goes on the wire as.

    python toolkit/test_quests.py

WHAT EARNS THIS FILE. `studies/quests/FINDINGS.md` 7.9 asked for it by name and
said why: a quests table with nothing checking it is precisely the "rule nothing
checks is a wish" CLAUDE.md opens with. Every assertion below is one the
ARTIFACT can refute -- a fabricated id, a description that will not fit the
client's field, a framing constant that drifted from the captures it was read
out of.

NO VAULT, NO CLIENT, NO SOCKET -- for sections 0 to 18. Everything there is the
content store and pure arithmetic, so it cannot skip, and that is what lets the
floor be a whole count rather than a guess. Sections 19 and 20 came later and DO
read the client image, so they skip without it; the floor is 0-18's count, not
this file's. See the MEASURED note on the ledger below for the two numbers.

THE ONE THING IT DELIBERATELY DOES NOT ASSERT is which framing is CORRECT.
`bare` and `template` are two spellings of the same sentence and only a client
can say which renders; asserting one here would be this repo's favourite bug --
two of our own components agreeing and calling it evidence.
"""
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "authsrv"))

import checks                                                # noqa: E402
import content                                               # noqa: E402
import questdefs                                             # noqa: E402
import authsrv                                              # noqa: E402

# MEASURED 2026-08-27: 83 with the vault present, 73 without. (It read "77
# with the vault present" from 2026-08-17 until section 19 grew the manifest
# sentinel's checks and section 19b's cross-build census.) Sections 19, 19b
# and 20 read the client image -- 888's re-derivation, the sentinel's
# per-build immediate, and the cross-build site check -- and declare skips
# without it; 20 also skips if fewer than two builds at or after the pin are
# vaulted. The floor is 73 -- what ONE quest row runs on a bare machine.
#
# THE PREVIOUS DERIVATION WAS STALE AND SAID SO CONFIDENTLY: "13 checks are
# row-count independent and each quest row adds 4, so 17 is what the
# smallest table that can exist executes." That was true when written and
# the file has since grown to 74 against the same one-row table, so the
# floor sat at 17 while a healthy run did four times that -- a floor that
# far below its run would not notice three whole sections going missing,
# which is the exact failure checks.py exists to refuse. Recomputed from a
# real green run rather than re-derived on paper.
#
# Adding quest rows only raises the count, so the floor stays valid; an
# EMPTY table is caught by section 0 before the count matters.
LEDGER = checks.Ledger("the quest table and its coded strings", floor=103)   # SLICE-B1 +6 (sec 21), B4 +5 (sec 22), B5 +9 (sec 23); from the green run
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

    print("\n7. the giver's line is checked against 0x0080's OWN width")
    # 0x0080 is string16(122) and 0x004C is string16(128). Six units apart, and
    # a shared constant would put that error somewhere only a screen could find.
    check(questdefs.DIALOG_UNITS == 122 and questdefs.FIELD_UNITS == 128,
          "the two field widths are distinct constants",
          f"dialog {questdefs.DIALOG_UNITS}, description "
          f"{questdefs.FIELD_UNITS} -- from the client's own RECV descriptors")
    check(refused(questdefs.coded_literal, "x" * 124, "template",
                  questdefs.DIALOG_UNITS),
          "a line that fits the DESCRIPTION field is refused for the DIALOG one",
          "124 + 3 framing units fits 128 and does not fit 122; this is the "
          "check that a shared constant would silently pass")
    for qid, row in sorted(rows.items()):
        line = questdefs.dialogue_field(row)
        if line is None:
            LEDGER.skip(f"quest {qid}'s giver line",
                        "the row carries no giver_dialogue")
            continue
        check(ord(line[0]) >= 0x100 and len(line) <= questdefs.DIALOG_UNITS,
              f"quest {qid}'s giver line is framed and fits 0x0080",
              f"{len(line)} of {questdefs.DIALOG_UNITS} code units")

    print("\n8. the 0x003B service tag decodes, and refuses what is not ours")
    check(questdefs.decode_service_select(0x805003) == (80, 0x03)
          and questdefs.decode_service_select(0x805001) == (80, 0x01)
          and questdefs.decode_service_select(0x85B601) == (1462, 0x01),
          "three raw dwords off ArenaNet's wire decode to their known pairs",
          "0x805003 -> quest 80 code 3, 0x805001 -> 80/1, 0x85B601 -> 1462/1")
    check(questdefs.encode_service_select(80, 0x01) == 0x805001,
          "and the encoder is the exact inverse",
          "a decoder with no encoder is hard to refute")
    for qid in (1, 80, 218, 1462, 0x7FFF):
        for code in (0x01, 0x03, 0x07, 0xFF):
            got = questdefs.decode_service_select(
                questdefs.encode_service_select(qid, code))
            if got != (qid, code):
                break
        else:
            continue
        break
    check(got == (qid, code), "round trip holds across the id and code range",
          f"last: quest {qid} code 0x{code:02X} -> {got}")
    check(questdefs.decode_service_select(0x005001) is None,
          "a dword with the TAG BIT CLEAR is refused, not decoded",
          "0x800000 is what says 'quest family'")
    check(questdefs.decode_service_select(0x01805001) is None,
          "and one with a HIGH BYTE set is refused",
          "all 22 captured selects are high-byte 0x00; the other four service "
          "families would decode to a fictional quest id")

    print("\n9. option KIND is bound to the 0x003B code, one to one")
    # The pairing our server shipped for a day -- kind 18 with codes 0x01 and
    # 0x07 -- occurs 0 times in 41 samples on ArenaNet's wire. These checks are
    # what stop it coming back.
    check(questdefs.option_kind(questdefs.SERVICE_ACCEPT) == 16
          and questdefs.option_kind(questdefs.SERVICE_DECLINE) == 17
          and questdefs.option_kind(questdefs.SERVICE_SHOW) == 18
          and questdefs.option_kind(questdefs.SERVICE_TURN_IN) == 23,
          "accept/decline/show/turn-in map to kinds 16/17/18/23",
          "measured 41 of 41 across both keyed sessions")
    check(len(set(questdefs.OPTION_KIND.values()))
          == len(questdefs.OPTION_KIND),
          "the mapping is injective -- no two codes share a kind",
          "a shared kind would mean the client cannot tell two options apart")
    bad = False
    try:
        questdefs.option_kind(0x99)
    except ValueError:
        bad = True
    check(bad, "an unmeasured code RAISES rather than defaulting to 18",
          "a default is what silently reproduced the wrong pairing")

    print("\n10. decline is a real code, and only half of it is known")
    check(questdefs.SERVICE_DECLINE == 0x02,
          "decline is 0x02", "kind 17, offered beside every accept, 11 of 11")
    check(questdefs.encode_service_select(1463, questdefs.SERVICE_DECLINE)
          == 0x85B702,
          "and it encodes into the tag like any other code")
    # The honest half: the offer is observed, the consequence is not. This check
    # asserts the DOCUMENTATION says so, because that is the only thing standing
    # between a future session and an invented refusal behaviour.
    src = open(os.path.join(HERE, "authsrv", "questdefs.py"),
               encoding="utf-8").read()
    check("CONSEQUENCE is not" in src or "consequence is still unmeasured" in src
          or "the CONSEQUENCE is not" in src,
          "and questdefs says the CONSEQUENCE is unmeasured",
          "0 of 11 offers were ever clicked; GWW says declined quests stay "
          "available and the wire cannot confirm it")

    print("\n11. the reward block, and which slot is which")
    run = questdefs.reward_run(111, 222)
    words = [ord(c) for c in run]
    check(len(words) == 19, "the reward run is 19 code units", str(len(words)))
    check(words[:5] == [0x0002, 0x2AE8, 0xE7D4, 0xE5CC, 0x3672],
          "it opens with the separator and ref 10728, the Reward: header")
    check(words[10] == 0x0101 and words[11] == 0x100 + 111,
          "slot A's numeric argument is 0x100-biased",
          "111 -> 0x016F; MEASURED on screen as '111 Experience'")
    check(words[17] == 0x0101 and words[18] == 0x100 + 222,
          "and slot B's likewise",
          "222 -> 0x01DE; MEASURED on screen as '222 Gold'")
    # OBSERVED 2026-08-16 (vault/captures/harness/20260816T103824): fed 111 and
    # 222, the pane rendered '111 Experience' and '222 Gold'. Before that run
    # this was a magnitude argument and could have come out reversed.
    check(questdefs.REWARD_SLOT_NAMES[0].startswith("experience")
          and questdefs.REWARD_SLOT_NAMES[1].startswith("gold"),
          "and the slots are NAMED, because a probe measured them",
          "ref 10730 = experience, ref 10732 = gold")
    for bad_n in (-1, 0x10000, 0xFF00, "x"):
        raised = False
        try:
            questdefs.reward_run(bad_n, 1)
        except (ValueError, TypeError):
            raised = True
        check(raised, f"a slot value of {bad_n!r} is refused",
              "it would not survive the 0x100 bias in one u16")

    print("\n12. the reward block is a PARAGRAPH away from the description")
    joined = questdefs.with_reward("Hello.", 1, 2, "template")
    body = questdefs.coded_literal("Hello.", "template")
    check(joined[:len(body)] == body, "the description is carried verbatim")
    check([ord(c) for c in joined[len(body):len(body) + 4]]
          == [0x0002, 0x0102, 0x0002, 0x0102],
          "and TWO 0x0002 0x0102 paragraph breaks -- a blank line, the owner's "
          "reading of stock (2026-09-12) -- separate it from the reward, each "
          "its own run so the codec never sees two ids in one",
          "without it the pane renders '...return to me.Reward:' welded "
          "together -- MEASURED, and the reason this check exists")
    over = False
    try:
        questdefs.with_reward("x" * 120, 1, 2, "template",
                              limit=questdefs.DIALOG_UNITS)
    except ValueError:
        over = True
    check(over,
          "and the length check runs AFTER the append, not before",
          "120 units of text passes on its own and overflows once the "
          "21-unit block is on; checking first would ship the overflow")

    print("\n13. every kind we can send has a measured icon")
    # MEASURED 2026-08-16 (vault/captures/harness/20260816T111948): one option
    # of every kind in one window drew six distinct icons. The '?' the owner
    # described is kind 22 and the '!' is kind 18 -- one mechanism, not two,
    # and neither of them is over the NPC's head where three runs looked first.
    check(questdefs.OPTION_ICONS[18] == "gold !"
          and questdefs.OPTION_ICONS[22] == "gold ?",
          "kind 18 is the '!' and kind 22 is the '?'",
          "the pair the owner described, and they are option KINDS")
    check(set(questdefs.OPTION_ICONS) == set(questdefs.OPTION_KIND.values()),
          "and every kind the code can emit has an icon recorded",
          "a kind we can send with no measured icon is one whose meaning on "
          "screen nobody has looked at")
    check(len(set(questdefs.OPTION_ICONS.values()))
          == len(questdefs.OPTION_ICONS),
          "the six icons are distinct",
          "two kinds sharing an icon would be indistinguishable to a player, "
          "which is what the property-11 sweep kept producing")

    print("\n14. the objective state machine, driven through a whole quest")
    # WHY THIS IS A UNIT TEST AND NOT A CLIENT RUN. Kind 22's RENDERING is
    # already measured -- dialog_icons put one option of every kind in one
    # window and 22 drew the gold '?'. What was unverified is that our server
    # ever EMITS it, and that is pure logic over quest state. Driving it here is
    # refutable in milliseconds; driving it on screen needs a five-click
    # sequence against two NPCs whose screen positions the harness cannot
    # reliably hit, which cost three runs and produced no interaction at all.
    sys.path.insert(0, os.path.join(HERE, "authsrv"))
    sys.path.insert(0, os.path.join(HERE, "schema"))
    import authsrv                                          # noqa: E402

    row = questdefs.load()[1463]
    giver, guard = row["giver_agent"], row["objective_agent"]
    check(giver != guard,
          "the giver and the objective NPC are different agents",
          "one NPC that both gives and completes cannot show an in-progress "
          "state at all -- it is the two-NPC walk that makes kind 22 reachable")

    st = {"interacting": giver}
    lines = authsrv._quest_lines(st)
    check([c for _q, c, _r in lines] == [questdefs.SERVICE_SHOW],
          "before accepting, the giver offers SHOW (code 0x03, kind 18, '!')",
          str(lines))

    st["quests"] = {1463}
    lines = authsrv._quest_lines(st)
    check([c for _q, c, _r in lines] == [questdefs.SERVICE_IN_PROGRESS],
          "once held and the objective unmet, it offers IN_PROGRESS "
          "(0x05, kind 22, the gold '?')",
          "THE STATE THAT DID NOT EXIST: before this, a held quest returned "
          "TURN_IN immediately and kind 22 was unreachable")
    check(questdefs.option_kind(lines[0][1]) == 22
          and questdefs.OPTION_ICONS[22] == "gold ?",
          "and that code really does select the '?' icon",
          "joins the state machine to the measured icon table")

    check(authsrv._objective_quests(st, guard) == [(1463, row)]
          or [q for q, _r in authsrv._objective_quests(st, guard)] == [1463],
          "the gate guard is the agent that completes it")
    check(authsrv._objective_quests(st, giver) == [],
          "and the GIVER does not complete its own objective",
          "otherwise accepting and finishing would coincide again and the "
          "middle state would collapse back to nothing")

    st["objectives_done"] = {1463}
    lines = authsrv._quest_lines(st)
    check([c for _q, c, _r in lines] == [questdefs.SERVICE_TURN_IN],
          "with the objective met, the giver offers TURN_IN (0x07, kind 23)",
          str(lines))
    check(authsrv._objective_quests(st, guard) == [],
          "and the guard has nothing left to complete",
          "a second visit must not re-fire the objective")

    st["interacting"] = guard
    check(authsrv._quest_lines(st) == [],
          "the gate guard never OFFERS the quest, whatever the state",
          "it is an objective, not a second giver -- talking to it is an "
          "event, not a menu")

    print("\n15. the marker MOVES to the objective, and off the giver")
    # The defect this pins, in the owner's words: "the giver tells you to talk
    # to the giver." The mark stayed on the giver after accept, so a quest that
    # sends you elsewhere pointed back at whoever had just spoken, and the NPC
    # the quest is actually about wore nothing at all.
    import authsrv                                          # noqa: E402
    grow = questdefs.load()[1463]
    giver, objective = grow.get("giver_agent"), grow.get("objective_agent")
    check(giver is not None and objective is not None and giver != objective,
          "the row binds TWO different agents",
          f"giver {giver}, objective {objective} -- one agent for both is the "
          f"nonsense case, not a simplification")

    def marks(held=(), done=()):
        return authsrv._quest_markers({"quests": set(held),
                                       "objectives_done": set(done)})

    m = marks()
    check(m.get(giver) == authsrv.QUEST_MARKER_OFFER
          and m.get(objective) is None,
          "unheld: the giver offers, the objective is bare")
    m = marks(held=[1463])
    check(m.get(giver) is None
          and m.get(objective) == authsrv.QUEST_MARKER_TURN_IN,
          "ACCEPTED: the giver's mark clears AND the arrow moves to the objective",
          "both halves -- a test that only checked the new arrow would pass "
          "with the giver still marked, which is exactly the bug")
    m = marks(held=[1463], done=[1463])
    check(m.get(objective) is None
          and m.get(giver) == authsrv.QUEST_MARKER_TURN_IN,
          "objective met: the arrow comes back to the giver")
    check(marks(held=[1463]).get(giver) is None,
          "a cleared mark is None, never 0",
          "no property-11 value removes a marker -- the clear is property 12, "
          "and [11, agent, 0] would invent a value that never occurs")

    print("\n16. the enc_* columns are WIRE code units, not archive string ids")
    # The trap FINDINGS 3.5 names: 0x3D64 on the wire denotes archive id 15460.
    # Conflating them resolves to 15716, an encrypted record returning None.
    for qid, row in sorted(rows.items()):
        enc = row.get("enc_name") or []
        check(all(int(u) >= 0x100 for u in enc),
              f"quest {qid}'s enc_name words are all >= 0x100",
              "a sub-0x100 word in an id slot is a marker, not a string id")

    print("\n17. rung Q6: the instance-load replay")
    # A recording `send`, so the ORDER is assertable and not just the contents.
    # Order is the whole rung: 0x0054 before 0x004C is a silent no-op, and
    # 0x0049 in place of 0x0050 changes which quest is active without any
    # visible sign.
    def replay(held, done=()):
        sent = []
        st = {"map_id": 148, "quests": set(held), "objectives_done": set(done)}
        authsrv._replay_quests(lambda op, vals, label="": sent.append((op, vals)), st)
        return sent, st

    sent, _st = replay([])
    check(sent == [], "no held quests sends NOTHING at all",
          f"{sent} -- a fresh character must not get an empty quest burst; an "
          f"0x0050 for a quest nobody holds would put a blank row in the log")

    sent, _st = replay([1463])
    ops = [op for op, _v in sent]
    check(authsrv.GAME_SMSG_QUEST_ADD not in ops,
          "the replay uses 0x0050, NEVER 0x0049",
          f"{[hex(o) for o in ops]} -- 0x0049's body writes charContext+0x528 "
          f"(0x0080F20B), so a bulk restore with it silently makes the LAST "
          f"quest pushed the active one. This is the red the ladder named for "
          f"this rung, and it is invisible on a one-row table -- which is "
          f"exactly why it is asserted rather than eyeballed")
    check(authsrv.GAME_SMSG_QUEST_ADD_NO_MARKER in ops,
          "and does send the add", f"{[hex(o) for o in ops]}")

    desc_at = ops.index(authsrv.GAME_SMSG_QUEST_DESCRIPTION)
    obj_at = ops.index(authsrv.GAME_SMSG_QUEST_OBJECTIVES_UPDATE)
    check(desc_at < obj_at,
          "0x004C precedes 0x0054, which is NOT ArenaNet's order",
          f"description at {desc_at}, objectives at {obj_at}. The client gates "
          f"0x0054 on the description-filled flag (body tests it at "
          f"0x0080F9CD) and ArenaNet trips its own gate twice in the corpus. "
          f"Copying the observed order verbatim would reproduce a bug we can "
          f"see, and it fails INVISIBLY -- an empty objective reads as the "
          f"client ignoring us")
    check(ops.index(authsrv.GAME_SMSG_QUEST_ADD_NO_MARKER) < desc_at,
          "and the add precedes both",
          "a description for a quest the client has not been given has nothing "
          "to attach to")

    clears = [v for op, v in sent if op == authsrv.GAME_SMSG_QUEST_MOVE_MARKER]
    check(len(clears) == 1 and clears[0][1] == authsrv.NO_MARKER_POS
          and clears[0][3] == authsrv.NO_MARKER_MAP,
          "the stale-marker clear is (+inf, +inf) / 888, never (0, 0)",
          f"{clears} -- (0,0) is a real coordinate and drops a marker at the "
          f"map origin, which looks like a bug in the marker code rather than "
          f"in the clear")

    sent2, _ = replay([1463], done=[1463])
    objs = [v for op, v in sent2 if op == authsrv.GAME_SMSG_QUEST_OBJECTIVES_UPDATE]
    objs_undone = [v for op, v in sent if op == authsrv.GAME_SMSG_QUEST_OBJECTIVES_UPDATE]
    check(objs and objs_undone and objs[0][1] != objs_undone[0][1],
          "a completed objective replays its DONE text, not the original",
          "restoring the pre-objective line would silently roll the player's "
          "progress back on every map transition")

    act = []
    st = {"map_id": 148, "quests": {1463}, "objectives_done": set()}
    authsrv._restore_active_marker(
        lambda op, vals, label="": act.append((op, vals)), st)
    check(len(act) == 1 and act[0][0] == authsrv.GAME_SMSG_QUEST_SET_ACTIVE_MARKER,
          "exactly one 0x0053 re-arms the active quest",
          f"{act} -- ArenaNet sends one, late (t=66.737, after c2s 0x0090). "
          f"WHICH quest is active on a fresh load is RECONSTRUCTION: we take "
          f"the lowest held id and the code says so")

    print("\n18. the progress carrier, and what it deliberately does not carry")
    saved = (set(authsrv.QUEST_PROGRESS["quests"]),
             set(authsrv.QUEST_PROGRESS["objectives_done"]))
    try:
        authsrv.QUEST_PROGRESS["quests"].clear()
        authsrv.QUEST_PROGRESS["objectives_done"].clear()
        one = authsrv.bind_progress({})
        one["quests"].add(1463)
        one["desc_sent"] = {1463}
        two = authsrv.bind_progress({})
        check(1463 in two["quests"],
              "a held quest survives into the next connection",
              "this is the rung: state is created fresh per connection, so "
              "before the carrier the log emptied at every map transition")
        check("desc_sent" not in two,
              "but `desc_sent` does NOT survive, and that is the load-bearing half",
              "a carried-over desc_sent makes _replay_quests skip the 0x004C "
              "that sets the description-filled flag, so every objectives line "
              "after it is a silent no-op -- appearing only on the SECOND map")
        check(one["quests"] is two["quests"],
              "and both connections share the SAME set object",
              "copies would work until a fourth call site forgot the copy-back")
    finally:
        authsrv.QUEST_PROGRESS["quests"].clear()
        authsrv.QUEST_PROGRESS["quests"].update(saved[0])
        authsrv.QUEST_PROGRESS["objectives_done"].clear()
        authsrv.QUEST_PROGRESS["objectives_done"].update(saved[1])

    print("\n19. 888 is re-derived, not trusted")
    try:
        sys.path.insert(0, os.path.join(HERE, "clientscan"))
        import areatable, srctree
        from gwpe import PE
        pe = PE(srctree.default_exe())
        # areatable's OWN selection rule, not a re-invention of it: the base is
        # the VA both locators agree on, and only the structural one's first hit
        # if they do not. Two methods disagreeing is the finding there, so the
        # agreement is required here rather than worked around.
        hits = areatable.locate_structural(pe)
        code = areatable.locate_from_code(pe)
        agreed = sorted({h["va"] for h in hits} & set(code))
        assert agreed, ("areatable's two locators disagree on this image -- "
                        "that is areatable's finding to report, not a number "
                        "to pick a winner from here")
        base_off = pe.rva_to_off(agreed[0] - pe.image_base)
        # `extent` walks records until the pattern breaks: the same "888
        # consecutive valid records" the CLI prints, reached by calling the
        # module rather than by parsing its output.
        n = areatable.extent(pe.data, base_off)
    # SystemExit EXPLICITLY, and it is the whole reason this section could not
    # skip. `pinned.find()` -- reached through `srctree.default_exe()` -- reports
    # a missing build by raising SystemExit, which is a BaseException and sails
    # straight through `except Exception`. MEASURED 2026-08-18: with no vault this
    # section did not declare a skip, it killed the run at section 19 of 20, so
    # the floor of 73 was unreachable even once the import was fixed. A skip that
    # cannot be reached is the same defect as no skip at all.
    except (Exception, SystemExit) as exc:                      # noqa: BLE001
        LEDGER.skip("the no-marker sentinel against areatable",
                    f"{type(exc).__name__}: {exc}")
    else:
        check(n == authsrv.NO_MARKER_MAP,
              "areatable's map count IS the no-marker sentinel",
              f"areatable says {n}, authsrv pins {authsrv.NO_MARKER_MAP}. "
              f"FINDINGS 2.3 says derive it rather than pin it; the server path "
              f"may not import a vault reader at startup, so it is pinned there "
              f"and re-derived here")
        # AND THE MANIFEST SENTINEL, which is the same quantity and was NOT
        # covered here until 2026-08-27. MAP_ID_COUNT was 877 -- OpenTyria's
        # enum end -- while this section re-derived 888 for NO_MARKER_MAP twenty
        # lines away in the same file and stayed green the whole time, because it
        # only ever scored one of the two names. 877 is a real map row
        # (`Forsaken Tunnels: Level 2`), so the server's "no destination"
        # sentinel named an actual dungeon on every login burst.
        check(n == authsrv.MAP_ID_COUNT,
              "and it is the MANIFEST sentinel too",
              f"areatable says {n}, authsrv pins {authsrv.MAP_ID_COUNT}. This is "
              f"the value the first MANIFEST_DONE carries as 'no map'; the "
              f"client stores it at context+0x134 and writes 0x378 there itself "
              f"in its own reset path")
        check(authsrv.MAP_ID_COUNT == authsrv.NO_MARKER_MAP,
              "the two names are ONE quantity, expressed once",
              f"MAP_ID_COUNT {authsrv.MAP_ID_COUNT}, NO_MARKER_MAP "
              f"{authsrv.NO_MARKER_MAP} -- two literals for 'one past the last "
              f"map' is what let them drift apart for weeks. If a future build "
              f"genuinely separates them, split them WITH a measurement rather "
              f"than by editing one number")

    # 19b. THE SENTINEL MOVES WITH THE MAP TABLE, and 877 is nowhere.
    #
    # Section 19 above proves our constant equals THIS build's map count. That
    # alone does not show the field at context+0x134 IS the table's size -- any
    # number that happens to match once would pass it. This scans every vaulted
    # client for the store itself and reads the immediate out: five sites per
    # build, every build, and the value tracks the table across a patch that
    # added five maps. That is the field being the size rather than coinciding
    # with it.
    #
    # THE CONTROL IS THE HALF THAT MATTERS. The same scan looks for 877 as a
    # compare bound and must find it ZERO times on every build -- because 877 was
    # OpenTyria's enum end, not any client's constant, and it is what this
    # server sent as "no map" until 2026-08-27 while naming a real dungeon row.
    # A scan that found 888 but was never asked about 877 would have left the
    # old value looking merely un-preferred instead of absent.
    STORE_0x134 = re.compile(rb"\xc7[\x80-\x87]\x34\x01\x00\x00(....)", re.S)
    CMP_877 = re.compile(rb"\x81\xff\x6d\x03\x00\x00|\x3d\x6d\x03\x00\x00")
    try:
        sys.path.insert(0, os.path.join(HERE, "clientscan"))
        import pinned as _pinned
        import vaultpath as _vp
        seen = {}
        for b in _pinned.BUILDS:
            path = os.path.join(_vp.vault_root(), "client", b.stamp, "Gw.exe")
            if not os.path.exists(path):
                continue
            blob = open(path, "rb").read()
            imms = [struct.unpack("<I", m.group(1))[0]
                    for m in STORE_0x134.finditer(blob)]
            sized = [v for v in imms if 500 < v < 5000]
            seen[b.number] = (sized, len(CMP_877.findall(blob)))
    except (Exception, SystemExit) as exc:                      # noqa: BLE001
        seen = {}
        LEDGER.skip("the sentinel's cross-build census",
                    f"{type(exc).__name__}: {exc}")
    if seen:
        check(len(seen) >= 3, "at least three builds are readable",
              f"{sorted(seen)} -- with fewer, 'it moves with the table' has no "
              f"span to move across")
        current = {n: v for n, v in seen.items() if n >= 38797}
        check(current and all(set(v[0]) == {authsrv.MAP_ID_COUNT}
                              for v in current.values()),
              f"every build from 38797 on stores {authsrv.MAP_ID_COUNT}, and "
              f"only that",
              "; ".join(f"{n}: {sorted(set(v[0]))} x{len(v[0])}"
                        for n, v in sorted(current.items())))
        old = {n: v for n, v in seen.items() if n < 38797}
        if old:
            check(all(set(v[0]) and set(v[0]) != {authsrv.MAP_ID_COUNT}
                      for v in old.values()),
                  "and an older build stores a DIFFERENT one",
                  "; ".join(f"{n}: {sorted(set(v[0]))}"
                            for n, v in sorted(old.items()))
                  + " -- 38519 reads 883, five maps fewer. Without this the "
                    "check above could be true of any constant in the image")
        else:
            LEDGER.skip("the older-build contrast",
                        "no pre-38797 client in the vault to contrast against")
        check(all(v[1] == 0 for v in seen.values()),
              "CONTROL: 877 is a bound on NO build",
              "877-as-a-bound counts "
              + ", ".join(f"{n}: {v[1]}" for n, v in sorted(seen.items()))
              + " -- 877 came from OpenTyria's enum and names a real map row "
                "(Forsaken Tunnels: Level 2). If this ever reads nonzero, the "
                "constant has a client witness after all and this whole section "
                "needs re-reading")

    print("\n20. every cited site, re-checked on the build the owner RUNS")
    # WHY THIS SECTION EXISTS. FINDINGS 7.9's last bullet said every binary
    # claim in the arc was build 38797 and none had been re-checked against
    # 38833, which is what the owner's install runs -- and closed with "probably
    # did not move" is what the VA-drift rule exists to refuse. This measures it
    # instead, and it keeps measuring it: a third build lands in BUILDS and this
    # section covers it without an edit.
    #
    # The sites are the arc's own citations, each with the length of the
    # instruction it names. Byte-identical across builds is the strong form --
    # it says the citation reads the same code, not merely that something lives
    # at that address.
    SITES = [
        (0x0080F7C2, 3, "2.2 imul edi, ecx, 0x34 (the log's 52-byte stride)"),
        (0x0080F84D, 5, "2.2 the tail memmove"),
        (0x0080F855, 6, "2.2 dec [ebx+0x534] (the log count)"),
        (0x0080F85B, 7, "2.2 imul esi, [ebx+0x534], 0x34"),
        (0x0080F20B, 6, "2.3 0x0049 writes charContext+0x528 (the ACTIVE quest)"),
        (0x0080F574, 6, "2.3 0x0050 loads the +inf marker constant"),
        (0x0080F600, 6, "2.3 ...and again"),
        (0x0080F9CD, 6, "Q3  the description-filled gate on 0x0054"),
        (0x0080DDA7, 5, "2.2 challengeSortArray.Find (ChCliApi:4237)"),
        (0x00633D70, 8, "1.6 the frame-bus POST helper"),
        (0x00633BD0, 8, "1.6 the frame-bus SUBSCRIBE helper"),
        (0x00948654, 4, "2.3 the +inf constant itself, in .rdata"),
    ]
    try:
        sys.path.insert(0, os.path.join(HERE, "clientscan"))
        import framebus, pinned, vaultpath
        imgs = []
        for b in pinned.BUILDS:
            path = os.path.join(vaultpath.vault_root(), "client", b.stamp, "Gw.exe")
            if os.path.exists(path):
                imgs.append((b.number, framebus.Image(path)))
    except (Exception, SystemExit) as exc:                      # noqa: BLE001
        imgs = []
        LEDGER.skip("the cross-build site check", f"{type(exc).__name__}: {exc}")
    # THE SPLIT IS THE FINDING, and the first draft of this section did not have
    # it. The vault holds THREE builds and the arc's citations hold on two of
    # them: 38797 (the pin) and 38833 (what the owner's install runs). On 38519
    # -- roughly ninety days older -- every one of these sites reads different
    # bytes and the frame-bus scan finds NOTHING in any quest body. So the claim
    # is not "these addresses are stable"; it is "they did not move across the
    # 15-day 38797->38833 patch", which is a much smaller claim and the true one.
    #
    # 38519 then does the job a synthetic control would do worse: it proves the
    # equality above is a measurement rather than a tautology. A first draft
    # asserted identity across ALL vaulted builds and went red on exactly this,
    # which is the check reporting a fact rather than a defect.
    def window(im, va, n):
        """`n` bytes at `va`, or None if this image does not map it.

        None rather than a raise: an older build legitimately may not have
        that address, and "absent" is a real answer here, not an error.
        """
        try:
            o = im.offset(va)
        except ValueError:
            return None
        return None if o is None else im.blob[o:o + n]

    PIN = 38797
    recent = [(n, im) for n, im in imgs if n >= PIN]
    older = [(n, im) for n, im in imgs if n < PIN]
    if len(recent) < 2:
        LEDGER.skip("the cross-build site check",
                    f"needs two builds at or after {PIN}; have "
                    f"{[n for n, _ in recent]}")
    else:
        names = ", ".join(str(n) for n, _ in recent)

        drift = [(va, what) for va, n, what in SITES
                 if len({window(im, va, n) for _x, im in recent}) != 1
                 or window(recent[0][1], va, n) is None]
        check(not drift,
              f"all {len(SITES)} cited sites are byte-identical across {names}",
              f"DRIFTED: {[(hex(v), w) for v, w in drift]} -- a citation whose "
              f"bytes differ between the pin and the build the owner RUNS is "
              f"reading different code than it was measured on, which is the "
              f"failure studies/pvpui/FINDINGS.md 4 and 15.0 each paid for once")

        want = {o: sorted(v) for o, v in framebus.QUEST_EXPECTED.items()}
        bad = {n: g for n, g in ((n, framebus.quest_family(im))
                                 for n, im in recent) if g != want}
        check(not bad,
              f"and the frame-bus pairing holds on every one of them",
              f"{bad} -- 11 of 11 bodies posting the recorded frame id is what "
              f"twelve names in overrides.json rest on, and it is worth knowing "
              f"on the build the owner actually runs, not only on the pin")

    if not older:
        LEDGER.skip("the older-build control",
                    f"no vaulted build before {PIN} to drift against")
    else:
        num, im = older[0]
        ref = recent[0][1] if recent else imgs[-1][1]
        same = [hex(va) for va, n, _w in SITES
                if window(im, va, n) is not None
                and window(im, va, n) == window(ref, va, n)]
        check(len(same) < len(SITES) // 2,
              f"CONTROL: on build {num} most of these sites read DIFFERENTLY",
              f"{len(same)} of {len(SITES)} still match ({same}). Build {num} is "
              f"~90 days older and everything moved; the frame-bus scan finds "
              f"nothing in any quest body there. Without this, 'byte-identical' "
              f"above could be true of a reader that never opened a file")

    print("\n21. SLICE-B1: the quest binds to a SPAWN ROW, not to a bare number")
    _row = authsrv.quest_rows()[1463]
    check(authsrv.quest_agent(_row, "giver") == 99
          and authsrv.quest_agent(_row, "objective") == 98,
          "the shipped row resolves its giver and objective through its spawn "
          "keys", f"{authsrv.quest_agent(_row, 'giver')}/"
                  f"{authsrv.quest_agent(_row, 'objective')}")
    # THE MIGRATION INVARIANT, and it is the check worth having: the row carries
    # BOTH a key and a number, and they must name the same body or the probe
    # world and the authored world are quietly testing different things.
    check(authsrv.quest_agent(_row, "giver") == _row.get("giver_agent")
          and authsrv.quest_agent(_row, "objective")
          == _row.get("objective_agent"),
          "and the key and the surviving NUMBER agree, so probequest.py's "
          "hand-built world and the authored one bind the same bodies",
          f"key {authsrv.quest_agent(_row, 'giver')} vs number "
          f"{_row.get('giver_agent')}")
    check(authsrv.quest_agent(dict(_row, giver_spawn="errand_scout"), "giver")
          == 98,
          "the KEY wins over the number where they disagree -- the number is "
          "the legacy column, not the authority")
    check(authsrv.quest_agent({"giver_agent": 7}, "giver") == 7
          and authsrv.quest_agent({}, "giver") is None,
          "a row with only a number still resolves (the probe path), and a row "
          "with neither is None rather than an error")
    try:
        authsrv.quest_agent(dict(_row, giver_spawn="no_such_row"), "giver")
        _raised = False
    except ValueError:
        _raised = True
    check(_raised,
          "and a key naming NO spawn row RAISES rather than falling back to "
          "the number -- the fallback would leave the quest working in the "
          "probe and dead in the world, invisible from either side alone")
    # The two NPC templates the spawn rows name have to be in TRACKED content,
    # not the vault overlay, or the rows above load here and fail on a bare
    # machine. That is the defect class, checked rather than trusted.
    _repo = content.load(vault_dir="")
    check("errand_giver" in _repo.rows("spawn")
          and _repo.rows("npc").get("lieutenant_fisk") is not None
          and _repo.rows("npc").get("ascalonian_townsfolk") is not None,
          "the errand's spawn rows AND the templates they name are in tracked "
          "content -- loaded here with the vault overlay switched off, which "
          "is the bare machine the suite never otherwise exercises",
          f"npcs={sorted(_repo.rows('npc'))}")

    print("\n22. SLICE-B4: a KILL meets an objective (the manifest's kill-count verb)")
    # A SYNTHETIC quest row, not a shipped one. Wiring this to real content
    # needs a second quest NAME, which needs a record in our own archive --
    # SLICE-B9's job. What is testable now is the verb itself.
    _kq = {"objectives": "Kill it.", "objectives_done": "Killed.",
           "wire_framing": "template", "objective_kill": "errand_scout"}
    _saved_rows = authsrv.quest_rows

    def _fake_rows(_cache={7001: _kq}):
        return _cache

    def _fire(dead, held=(7001,), done=()):
        sent = []
        st = {"quests": set(held), "objectives_done": set(done),
              "desc_sent": {7001}, "agent_pos": {}, "agents": {}}
        authsrv.kill_completes_objective(
            lambda op, vals, label="", **kw: sent.append((op, vals, label)),
            st, dead, 0)
        return st, sent

    try:
        authsrv.quest_rows = _fake_rows
        st, sent = _fire(98)
        check(7001 in st["objectives_done"] and sent,
              "killing the agent the row names meets the objective, and an "
              "0x0054 goes out", f"done={st['objectives_done']} sent={len(sent)}")
        st, sent = _fire(99)
        check(7001 not in st["objectives_done"] and not sent,
              "killing a DIFFERENT agent does not -- the binding is to one "
              "body, not to any death")
        st, sent = _fire(98, held=())
        check(7001 not in st["objectives_done"] and not sent,
              "and a quest the player does not HOLD is untouched, so a kill "
              "cannot complete an objective for a quest never accepted")
        st, sent = _fire(98, done=(7001,))
        check(not sent,
              "an objective already met is not met again -- no second 0x0054 "
              "and no second marker batch for the same kill")
        _kq["objective_kill"] = "no_such_spawn"
        try:
            _fire(98)
            _raised = False
        except ValueError:
            _raised = True
        check(_raised,
              "and a key naming NO spawn row RAISES: a kill objective that can "
              "never fire looks exactly like a player who has not killed the "
              "right thing, which is indistinguishable from the outside")
        _kq["objective_kill"] = "errand_scout"
    finally:
        authsrv.quest_rows = _saved_rows

    print("\n23. SLICE-B5: the reward is GRANTED at turn-in, and it is ours")
    # The completion family is 0 of 22,524 in the corpus, so this section
    # checks OUR mechanism: the kill's own 0x00EE delta carrying the row's
    # promised number, the same consequences a kill has, and the state that
    # stops a turned-in quest coming back.
    _OP_XP = authsrv.GAME_SMSG_AGENT_KILL_REWARD
    _saved_persist = authsrv.PERSIST

    def _grant(row, persist=False, store=None):
        sent = []
        st = {"quests": set(), "objectives_done": set(),
              "quests_completed": set(), "agents": {},
              "char_uuid": "u1"}
        if store is not None:
            st["charstore_game"] = store
        authsrv.PERSIST = persist
        try:
            paid = authsrv.grant_quest_reward(
                lambda op, vals, label="", **kw: sent.append((op, list(vals), label)),
                st, 1463, row, 0)
        finally:
            authsrv.PERSIST = _saved_persist
        return paid, sent, st

    paid, sent, _st = _grant({"reward_experience": 100})
    xp = [v for op, v, _l in sent if op == _OP_XP]
    check(paid == 100 and xp == [[authsrv.KILL_REWARD_ATTR, 100]],
          "reward_experience = 100 goes out as ONE 0x00EE [0, 100] -- the "
          "kill's own delta, which the client is proven to apply +=",
          f"{xp} of {len(sent)} message(s)")
    check(all(op in (_OP_XP, authsrv.GAME_SMSG_PLAYER_ATTR_UPDATE,
                     authsrv.GAME_SMSG_AGENT_MORALE) for op, _v, _l in sent),
          "and nothing from the completion family is sent -- 0x004E and its "
          "kin are 0 of 22,524 in the corpus and are not invented here",
          f"{[hex(op) for op, _v, _l in sent]}")

    paid, sent, _st = _grant({"objectives": "x"})
    check(paid == 0 and not sent,
          "a row with no reward_experience grants nothing and sends nothing")

    paid, sent, _st = _grant({"reward_experience": 100, "reward_gold": 10})
    check(paid == 100 and [v for op, v, _l in sent if op == _OP_XP]
          == [[authsrv.KILL_REWARD_ATTR, 100]] and len(sent) == 1,
          "reward_gold is NOT GRANTED -- no gold message is identified -- and "
          "the experience still is: one message, not two",
          f"{[hex(op) for op, _v, _l in sent]}")

    class _Store:
        def __init__(self):
            self.rows = {"u1": {"xp": 5}}
            self.saved = 0

        def character_by_uuid(self, u):
            return self.rows.get(u)

        def save(self):
            self.saved += 1

    store = _Store()
    _grant({"reward_experience": 100}, persist=False, store=store)
    check(store.rows["u1"]["xp"] == 5 and store.saved == 0,
          "without --persist the store is untouched -- the wire delta is the "
          "whole grant, exactly as a kill's is", f"{store.rows} saved {store.saved}")
    _grant({"reward_experience": 100}, persist=True, store=store)
    check(store.rows["u1"]["xp"] == 105 and store.saved == 1,
          "under --persist the sheet accrues the same 100 and is saved once",
          f"{store.rows} saved {store.saved}")

    # THE FOURTH STATE: turned in. The giver stops offering; both marks clear.
    st = {"quests": set(), "objectives_done": {1463}, "quests_completed": {1463},
          "interacting": authsrv.quest_agent(questdefs.load()[1463], "giver")}
    check(authsrv._quest_lines(st) == [],
          "a COMPLETED quest is not offered again by its giver -- before B5 the "
          "'!' came straight back the moment the reward window closed")
    m = authsrv._quest_markers({"quests": set(), "objectives_done": set(),
                                "quests_completed": {1463}})
    giver = authsrv.quest_agent(questdefs.load()[1463], "giver")
    objective = authsrv.quest_agent(questdefs.load()[1463], "objective")
    check(giver in m and objective in m and m[giver] is None
          and m[objective] is None,
          "and both of its agents are in the marker pass with NO mark -- named, "
          "so the clear is sent, and clear")
    check("quests_completed" in authsrv.QUEST_PROGRESS
          and isinstance(authsrv.QUEST_PROGRESS["quests_completed"], set),
          "the completed set rides the process-wide progress carrier, so it "
          "survives a reconnect the way held quests do")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
