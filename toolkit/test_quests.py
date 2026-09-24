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
LEDGER = checks.Ledger("the quest table and its coded strings", floor=130)   # SLICE-B1 +6 (sec 21), B4 +5 (sec 22), B5 +9 (sec 23), the kill quest +8 (sec 24); 117 -> 130 on 2026-09-14 when secs 19/19b/19c/20 went per build (38888); from the green run
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
    # Filtered on 1463 since the kill quest (1464) joined the same giver: these
    # checks are about the ERRAND's three states, and section 24 is where the
    # two-quest menu is measured.
    check([c for q, c, _r in lines if q == 1463] == [questdefs.SERVICE_SHOW],
          "before accepting, the giver offers SHOW (code 0x03, kind 18, '!')",
          str(lines))

    st["quests"] = {1463}
    lines = authsrv._quest_lines(st)
    check([c for q, c, _r in lines if q == 1463] == [questdefs.SERVICE_IN_PROGRESS],
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
    check([c for q, c, _r in lines if q == 1463] == [questdefs.SERVICE_TURN_IN],
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
    # BOTH quests held from here: the kill quest (1464) shares this giver, and
    # an unheld second quest keeps its '!' on him -- the highest-wins rule
    # `_quest_markers` documents, OURS and measured by nothing, and checked
    # below so it is a stated rule rather than a surprise. These three checks
    # are about the ERRAND's states, so the other quest is taken out of play
    # by holding it.
    m = marks(held=[1463])
    check(m.get(giver) == authsrv.QUEST_MARKER_OFFER,
          "the errand held ALONE leaves '!' on the giver: the bandits quest is "
          "still on offer from the same body (highest wins -- ours)", dict(m))
    m = marks(held=[1463, 1464])
    check(m.get(giver) is None
          and m.get(objective) == authsrv.QUEST_MARKER_TURN_IN,
          "ACCEPTED (both held): the giver's mark clears AND the arrow moves "
          "to the objective",
          "both halves -- a test that only checked the new arrow would pass "
          "with the giver still marked, which is exactly the bug")
    m = marks(held=[1463, 1464], done=[1463])
    check(m.get(objective) is None
          and m.get(giver) == authsrv.QUEST_MARKER_TURN_IN,
          "objective met: the arrow comes back to the giver")
    check(marks(held=[1463, 1464]).get(giver) is None,
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

    print("\n19. the map count is re-derived PER BUILD, not trusted")
    # REWRITTEN 2026-09-14. Until then this section derived ONE number off the
    # pinned image and checked the server's one literal against it -- and the
    # literal was right for 38797 through 38849 and wrong for 38888, which
    # stores 897 (nine maps added). §19b below is what caught it. The server's
    # constant is now a TABLE, one row per vaulted build, and this section
    # re-derives EVERY row through areatable's own selection rule: the base
    # both locators agree on, then `extent` walking records until the pattern
    # breaks. Two locators disagreeing is areatable's finding to report, not a
    # number to pick a winner from here, so agreement is required per build.
    #
    # That makes two witnesses per row that do not share a method: this
    # section reads the TABLE's length, §19b reads the client's own STORE of the
    # sentinel (`mov [reg+0x134], imm32`, five sites). 883 / 888 / 888 / 888 /
    # 897 on both, 2026-09-14.
    derived = {}
    try:
        sys.path.insert(0, os.path.join(HERE, "clientscan"))
        import areatable, pinned as _pinned19, vaultpath as _vp19
        from gwpe import PE
        for b in _pinned19.BUILDS:
            path = os.path.join(_vp19.vault_root(), "client", b.stamp, "Gw.exe")
            if not os.path.exists(path):
                continue
            pe = PE(path)
            hits = areatable.locate_structural(pe)
            code = areatable.locate_from_code(pe)
            agreed = sorted({h["va"] for h in hits} & set(code))
            if not agreed:
                LEDGER.skip(f"areatable on build {b.number}",
                            "its two locators disagree on this image -- "
                            "areatable's finding to report, not ours to pick from")
                continue
            base_off = pe.rva_to_off(agreed[0] - pe.image_base)
            derived[b.number] = areatable.extent(pe.data, base_off)
    # SystemExit EXPLICITLY, and it is the whole reason this section could not
    # skip. `pinned.find()` reports a missing build by raising SystemExit, which
    # is a BaseException and sails straight through `except Exception`.
    # MEASURED 2026-08-18: with no vault this section did not declare a skip, it
    # killed the run at section 19 of 20, so the floor was unreachable even
    # once the import was fixed. A skip that cannot be reached is the same
    # defect as no skip at all.
    except (Exception, SystemExit) as exc:                      # noqa: BLE001
        derived = {}
        LEDGER.skip("the map count against areatable", f"{type(exc).__name__}: {exc}")
    if derived:
        check(len(derived) >= 2, "at least two builds derive",
              f"{sorted(derived)} -- with one, 'per build' has nothing to vary over")
        wrong = {n: (v, authsrv.MAP_ID_COUNT_BY_BUILD.get(n))
                 for n, v in derived.items()
                 if authsrv.MAP_ID_COUNT_BY_BUILD.get(n) != v}
        check(not wrong,
              f"areatable's map count IS the table's row on every readable build "
              f"({', '.join(f'{n}: {v}' for n, v in sorted(derived.items()))})",
              f"derived vs pinned: {wrong}. FINDINGS 2.3 says derive it rather "
              f"than pin it; the server path may not import a vault reader at "
              f"startup, so it is pinned there and re-derived here")
        check(all(n in authsrv.MAP_ID_COUNT_BY_BUILD for n in derived),
              "and every vaulted build HAS a row",
              f"missing: {sorted(set(derived) - set(authsrv.MAP_ID_COUNT_BY_BUILD))}"
              f" -- a new snapshot with no row is the next 38888: the server "
              f"would send the previous build's count to it")
        # THE DEFAULT IS THE PIN, NOT THE NEWEST -- corrected the same day it
        # was written. "Newest" reasoned from the owner's install, which this
        # server never serves; what it serves is a loopback client, and every
        # loopback run dir but one is the pin's generation (vault/run/slice is
        # build 38797 by its own getter). Harness 20260914T111021/T111122
        # measured both arms. The harness passes the exe's build itself
        # (runargs.resolve_client_build); the default is for the hand loop.
        check(authsrv.CLIENT_BUILD == _pinned19.BUILD
              and authsrv.CLIENT_BUILD in derived,
              f"the DEFAULT --client-build is the pin ({authsrv.CLIENT_BUILD}), "
              f"the generation the loopback run dirs are cut from",
              f"pin {_pinned19.BUILD}, derived builds {sorted(derived)}")
    check(authsrv.MAP_ID_COUNT == authsrv.MAP_ID_COUNT_BY_BUILD[authsrv.CLIENT_BUILD],
          "the constant the server SENDS is the default build's row",
          f"MAP_ID_COUNT {authsrv.MAP_ID_COUNT}, row "
          f"{authsrv.MAP_ID_COUNT_BY_BUILD[authsrv.CLIENT_BUILD]}")
    # AND THE MANIFEST SENTINEL, which is the same quantity and was NOT covered
    # here until 2026-08-27. MAP_ID_COUNT was 877 -- OpenTyria's enum end --
    # while this section re-derived 888 for NO_MARKER_MAP twenty lines away in
    # the same file and stayed green the whole time, because it only ever scored
    # one of the two names. 877 is a real map row (`Forsaken Tunnels: Level 2`),
    # so the server's "no destination" sentinel named an actual dungeon on every
    # login burst.
    check(authsrv.MAP_ID_COUNT == authsrv.NO_MARKER_MAP,
          "the two names are ONE quantity, expressed once",
          f"MAP_ID_COUNT {authsrv.MAP_ID_COUNT}, NO_MARKER_MAP "
          f"{authsrv.NO_MARKER_MAP} -- two literals for 'one past the last "
          f"map' is what let them drift apart for weeks. If a future build "
          f"genuinely separates them, split them WITH a measurement rather "
          f"than by editing one number")

    # 19b. THE SENTINEL MOVES WITH THE MAP TABLE, and 877 is nowhere.
    #
    # Section 19 above proves each row equals THAT build's table length. That
    # alone does not show the field at context+0x134 IS the table's size -- any
    # number that happens to match once would pass it. This scans every vaulted
    # client for the store itself and reads the immediate out: five sites per
    # build, every build, and the value tracks the table across two patches
    # that added maps (883 -> 888 -> 897). That is the field being the size
    # rather than coinciding with it.
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
        check(all(set(v[0]) == {authsrv.MAP_ID_COUNT_BY_BUILD.get(n)}
                  for n, v in seen.items()),
              "every build stores ITS OWN row's value, and only that",
              "; ".join(f"{n}: {sorted(set(v[0]))} x{len(v[0])} (row "
                        f"{authsrv.MAP_ID_COUNT_BY_BUILD.get(n)})"
                        for n, v in sorted(seen.items())))
        check(all(len(v[0]) == 5 for v in seen.values()),
              "five stores per build, every build -- the same shape",
              "; ".join(f"{n}: x{len(v[0])}" for n, v in sorted(seen.items()))
              + " -- a build with a different count is a different store "
                "layout and the scan needs re-reading, not the table")
        distinct = {authsrv.MAP_ID_COUNT_BY_BUILD[n] for n in seen
                    if n in authsrv.MAP_ID_COUNT_BY_BUILD}
        check(len(distinct) >= 2,
              "and the value is NOT a constant across builds",
              f"{sorted(distinct)} -- 38519 reads 883, 38797..38849 888, 38888 "
              f"897. Without this the check above could be true of any constant "
              f"in the image")
        check(all(v[1] == 0 for v in seen.values()),
              "CONTROL: 877 is a bound on NO build",
              "877-as-a-bound counts "
              + ", ".join(f"{n}: {v[1]}" for n, v in sorted(seen.items()))
              + " -- 877 came from OpenTyria's enum and names a real map row "
                "(Forsaken Tunnels: Level 2). If this ever reads nonzero, the "
                "constant has a client witness after all and this whole section "
                "needs re-reading")

    # 19c. THE WIRE'S OWN WITNESS. The server cannot read the build off the
    # wire before the manifest burst, so `--client-build` picks the sentinel
    # and the client's mission mask (0x0092) is what contradicts it: one bit
    # per map id in whole dwords. MEASURED on four live tapes, 2026-09-14
    # (`cmsgstream`, game c2s): 20260913T210901 and 20260914T005758 (both
    # 38888) 116 bytes, 10 of 10 and 12 of 12; 20260821T205552 and
    # 20260824T074002 (38833/38849) 112 bytes, 11 of 11 each. The formula has
    # no free parameter, which is why it is pinned to the tapes here rather
    # than to itself.
    check(authsrv.mission_mask_bytes(888) == 112
          and authsrv.mission_mask_bytes(897) == 116,
          "the mask width the tapes carry is ceil(count/32)*4: 112 for 888, "
          "116 for 897",
          f"{authsrv.mission_mask_bytes(888)}, {authsrv.mission_mask_bytes(897)}")
    check(authsrv.build_of_mission_mask(116) == [38888]
          and 38888 not in authsrv.build_of_mission_mask(112),
          "so a 116-byte mask names 38888 and only 38888, and a 112-byte one "
          "cannot",
          f"116 -> {authsrv.build_of_mission_mask(116)}, "
          f"112 -> {authsrv.build_of_mission_mask(112)}")
    check(authsrv.build_of_mission_mask(120) == [],
          "and a width no build sends names nobody rather than the nearest",
          f"{authsrv.build_of_mission_mask(120)}")

    print("\n20. every cited site, re-checked on the build the owner RUNS")
    # WHY THIS SECTION EXISTS. FINDINGS 7.9's last bullet said every binary
    # claim in the arc was build 38797 and none had been re-checked against
    # 38833, which is what the owner's install runs -- and closed with "probably
    # did not move" is what the VA-drift rule exists to refuse. This measures it
    # instead, and it keeps measuring it: a third build lands in BUILDS and this
    # section covers it without an edit.
    #
    # AND IT WENT RED ON 2026-09-14, as designed: build 38888 is the first
    # image since the pin whose size changed, and all twelve sites moved. Each
    # site now carries a VA per BUILD FAMILY -- 38797's, which 38833 and 38849
    # share byte for byte, and 38888's, MEASURED by a masked byte search from
    # the pin's bytes (operands that are an absolute address or a rel32
    # wildcarded) and then read back. Two claims replace the old one:
    #   (a) within the 38797 family the sites are byte-IDENTICAL (the strong
    #       form -- the same code, not merely something at that address);
    #   (b) on 38888 they are identical once address OPERANDS are masked, and
    #       the sites whose raw bytes differ are exactly the four that carry
    #       an address: the memmove's rel32, the two `fld` of the +inf
    #       constant (0x00948654 -> 0x0094966C), and Find's `mov edx, imm32`.
    # The length of each site is the instruction it names.
    F797, F888 = 38797, 38888
    SITES = [
        ({F797: 0x0080F7C2, F888: 0x0080FC22}, 3, "2.2 imul edi, ecx, 0x34 (the log's 52-byte stride)"),
        ({F797: 0x0080F84D, F888: 0x0080FCAD}, 5, "2.2 the tail memmove"),
        ({F797: 0x0080F855, F888: 0x0080FCB5}, 6, "2.2 dec [ebx+0x534] (the log count)"),
        ({F797: 0x0080F85B, F888: 0x0080FCBB}, 7, "2.2 imul esi, [ebx+0x534], 0x34"),
        ({F797: 0x0080F20B, F888: 0x0080F66B}, 6, "2.3 0x0049 writes charContext+0x528 (the ACTIVE quest)"),
        ({F797: 0x0080F574, F888: 0x0080F9D4}, 6, "2.3 0x0050 loads the +inf marker constant"),
        ({F797: 0x0080F600, F888: 0x0080FA60}, 6, "2.3 ...and again"),
        ({F797: 0x0080F9CD, F888: 0x0080FE2D}, 6, "Q3  the description-filled gate on 0x0054"),
        ({F797: 0x0080DDA7, F888: 0x0080E217}, 5, "2.2 challengeSortArray.Find (ChCliApi:4237; 4281 on 38888)"),
        ({F797: 0x00633D70, F888: 0x006341A0}, 8, "1.6 the frame-bus POST helper"),
        ({F797: 0x00633BD0, F888: 0x00634000}, 8, "1.6 the frame-bus SUBSCRIBE helper"),
        ({F797: 0x00948654, F888: 0x0094966C}, 4, "2.3 the +inf constant itself, in .rdata"),
    ]
    FAMILY = {38797: F797, 38833: F797, 38849: F797, 38888: F888}
    ADDRESS_OPERAND_SITES = {0x0080F84D, 0x0080F574, 0x0080F600, 0x0080DDA7}
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
    # it. On 38519 -- roughly ninety days older than the pin -- every one of
    # these sites reads different bytes and the frame-bus scan finds NOTHING in
    # any quest body. So the claim is not "these addresses are stable"; it is
    # "they did not move across 38797 -> 38849, and moved by a measured amount
    # on 38888", which is a much smaller claim and the true one.
    #
    # 38519 then does the job a synthetic control would do worse: it proves the
    # equality below is a measurement rather than a tautology. A first draft
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

    def va_span(*ims):
        """[lowest section VA, highest section end) over the images given --
        the address range an operand can point into, read from the PE headers
        rather than typed. A literal bound was the first draft, and it stopped
        at .text: Find's `mov edx, imm32` names a .data address above it and
        went red as 'a different instruction'."""
        lo = min(sva for im in ims for sva, _sz, _ro in im.sections)
        hi = max(sva + sz for im in ims for sva, sz, _ro in im.sections)
        return lo, hi

    def masked(bs, span):
        """`bs` with every 4-byte address operand replaced by `????`: a rel32
        after E8/E9, or a value inside `span` (the image's VA range). What is
        left is the opcode and the non-address immediates, which is what 'the
        same instruction' means across a relink."""
        if bs is None:
            return None
        out = bytearray(bs)
        i = 0
        while i + 4 <= len(out):
            v = struct.unpack_from("<I", bs, i)[0]
            if (i and bs[i - 1] in (0xE8, 0xE9)) or span[0] <= v < span[1]:
                out[i:i + 4] = b"????"
                i += 4
            else:
                i += 1
        return bytes(out)

    PIN = 38797
    by_num = dict(imgs)
    fam797 = [(n, im) for n, im in imgs if FAMILY.get(n) == F797]
    fam888 = [(n, im) for n, im in imgs if FAMILY.get(n) == F888]
    older = [(n, im) for n, im in imgs if n < PIN]
    if len(fam797) < 2:
        LEDGER.skip("the 38797-family site check",
                    f"needs two builds of the family; have {[n for n, _ in fam797]}")
    else:
        names = ", ".join(str(n) for n, _ in fam797)
        drift = [(va[F797], what) for va, n, what in SITES
                 if len({window(im, va[F797], n) for _x, im in fam797}) != 1
                 or window(fam797[0][1], va[F797], n) is None]
        check(not drift,
              f"(a) all {len(SITES)} cited sites are byte-identical across {names}",
              f"DRIFTED: {[(hex(v), w) for v, w in drift]} -- a citation whose "
              f"bytes differ between the pin and a build the owner ran is "
              f"reading different code than it was measured on, which is the "
              f"failure studies/pvpui/FINDINGS.md 4 and 15.0 each paid for once")
    if not fam888 or PIN not in by_num:
        LEDGER.skip("the 38888 site check",
                    f"needs the pin and a 38888 image; have {sorted(by_num)}")
    else:
        pin_im = by_num[PIN]
        for n888, im888 in fam888:
            span = va_span(pin_im, im888)
            diff = [(hex(va[F888]), what) for va, n, what in SITES
                    if masked(window(pin_im, va[F797], n), span)
                    != masked(window(im888, va[F888], n), span)]
            check(not diff,
                  f"(b) all {len(SITES)} sites read the SAME INSTRUCTION on "
                  f"{n888} at their relocated VAs, address operands masked",
                  f"differ: {diff} -- a relocated VA that lands on different "
                  f"opcode bytes is not the site, it is a coincidence of the "
                  f"search")
            raw_differ = {va[F797] for va, n, what in SITES
                          if window(pin_im, va[F797], n) != window(im888, va[F888], n)}
            check(raw_differ == ADDRESS_OPERAND_SITES,
                  "and the sites whose RAW bytes changed are exactly the four "
                  "that carry an address operand",
                  f"raw-different {sorted(hex(v) for v in raw_differ)} vs the "
                  f"four with an address {sorted(hex(v) for v in ADDRESS_OPERAND_SITES)}"
                  f" -- a fifth means an immediate changed, which is a claim "
                  f"about the code and not about the relink")
            unmasked_same = [what for va, n, what in SITES
                             if va[F797] not in ADDRESS_OPERAND_SITES
                             and window(pin_im, va[F797], n) == window(im888, va[F888], n)]
            check(len(unmasked_same) == len(SITES) - len(ADDRESS_OPERAND_SITES),
                  "CONTROL: the eight address-free sites match UNMASKED too, so "
                  "the mask is not what makes (b) true",
                  f"{len(unmasked_same)} of {len(SITES) - len(ADDRESS_OPERAND_SITES)}")

    tabled = [(n, im) for n, im in imgs if framebus.tables_for(n) is not None]
    if len(tabled) < 2:
        LEDGER.skip("the frame-bus pairing per build",
                    f"needs two builds with a framebus table; have {[n for n, _ in tabled]}")
    else:
        want = {o: sorted(v) for o, v in framebus.QUEST_EXPECTED.items()}
        bad = {n: g for n, g in ((n, framebus.quest_family(im))
                                 for n, im in tabled) if g != want}
        check(not bad,
              f"and the frame-bus pairing holds on every build with a table "
              f"({', '.join(str(n) for n, _ in tabled)})",
              f"{bad} -- 11 of 11 bodies posting the recorded frame id is what "
              f"twelve names in overrides.json rest on, and it is worth knowing "
              f"on the build the owner actually runs, not only on the pin")
        cwant = {o: sorted(v) for o, v in framebus.COMPLETION_EXPECTED.items()}
        cbad = {n: g for n, g in ((n, framebus.completion_family(im))
                                  for n, im in tabled) if g != cwant}
        check(not cbad,
              "and so does the completion family's -- which was NEVER in the "
              "twelve sites and had moved on 38833 and 38849 unnoticed until "
              "2026-09-14",
              f"{cbad} -- 0x0096/0x0097/0x00FB sit 0x160 lower on 38833 and "
              f"0x100 lower on 38849 than on the pin; framebus.TABLES carries "
              f"each build's own bounds")
        check(authsrv.CLIENT_BUILD in dict(tabled),
              f"and the default --client-build ({authsrv.CLIENT_BUILD}) is one "
              f"of them",
              f"tabled: {[n for n, _ in tabled]} -- the build the server serves "
              f"by default has to be one whose quest handlers were read")

    if not older:
        LEDGER.skip("the older-build control",
                    f"no vaulted build before {PIN} to drift against")
    else:
        num, im = older[0]
        ref = by_num.get(PIN) or imgs[-1][1]
        same = [hex(va[F797]) for va, n, _w in SITES
                if window(im, va[F797], n) is not None
                and window(im, va[F797], n) == window(ref, va[F797], n)]
        check(len(same) < len(SITES) // 2,
              f"CONTROL: on build {num} most of these sites read DIFFERENTLY",
              f"{len(same)} of {len(SITES)} still match ({same}). Build {num} is "
              f"~90 days older and everything moved; the frame-bus scan finds "
              f"nothing in any quest body there. Without this, 'byte-identical' "
              f"above could be true of a reader that never opened a file")
        check(framebus.tables_for(num) is None
              and framebus.quest_family(im) != {o: sorted(v) for o, v
                                                 in framebus.QUEST_EXPECTED.items()},
              f"and {num} has no framebus table, and the pin's VAs scanned over "
              f"its bytes do NOT reproduce the pairing",
              "a pairing that held on a build nobody measured would mean the "
              "scan is not reading the bytes")

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

    # DESKWORK-D9: reward_gold IS granted now, as a 0x0140 credit AFTER the
    # experience 0x00EE -- the tape's order (8 single-quest hand-ins).
    _GOLD = authsrv.merchant.GAME_SMSG_GOLD_CREDIT
    paid, sent, _st = _grant({"reward_experience": 100, "reward_gold": 10})
    ops = [op for op, _v, _l in sent]
    gold = [v for op, v, _l in sent if op == _GOLD]
    check(paid == 100 and gold == [[authsrv.PLAYER_INVENTORY_KEY, 10]]
          and _st.get("purse") == 10,
          "reward_gold = 10 is GRANTED as 0x0140 [key, 10] and the purse holds "
          "it (DESKWORK-D9, OBSERVED: gold rides the hand-in frame)",
          f"gold={gold} purse={_st.get('purse')} ops={[hex(o) for o in ops]}")
    check(_GOLD in ops and _OP_XP in ops
          and ops.index(_GOLD) > ops.index(_OP_XP),
          "and the gold 0x0140 comes AFTER the experience 0x00EE -- the tape's "
          "order (0x00EE[0,xp] then 0x0140[key,gold]); a balance sent before "
          "the xp would be the known-bad arm",
          f"{[hex(o) for o in ops]}")
    # The revert arm: --no-quest-gold pays no gold, and the experience still is.
    _saved_gold_flag = authsrv.QUEST_GOLD_ENABLED
    authsrv.QUEST_GOLD_ENABLED = False
    try:
        paid, sent, _st = _grant({"reward_experience": 100, "reward_gold": 10})
    finally:
        authsrv.QUEST_GOLD_ENABLED = _saved_gold_flag
    check(paid == 100 and _GOLD not in [op for op, _v, _l in sent]
          and _st.get("purse") is None,
          "--no-quest-gold reverts: no 0x0140 and no purse move, the experience "
          "still paid (the pre-DESKWORK-D9 behaviour)",
          f"{[hex(op) for op, _v, _l in sent]} purse={_st.get('purse')}")
    # A row with gold but NO experience still pays the gold (the early-return
    # must not swallow it).
    paid, sent, _st = _grant({"reward_gold": 7})
    check(paid == 0 and [v for op, v, _l in sent if op == _GOLD]
          == [[authsrv.PLAYER_INVENTORY_KEY, 7]] and _st.get("purse") == 7,
          "a gold-only reward pays the gold although there is no experience",
          f"{[hex(op) for op, _v, _l in sent]} purse={_st.get('purse')}")

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
    check(1463 not in [q for q, _c, _r in authsrv._quest_lines(st)],
          "a COMPLETED quest is not offered again by its giver -- before B5 the "
          "'!' came straight back the moment the reward window closed (the "
          "same giver's OTHER quest, 1464, is still on the menu)")
    # 1464 held-and-undone here so the giver's only possible mark is the
    # errand's: a kill quest in progress marks nobody (section 24).
    m = authsrv._quest_markers({"quests": {1464}, "objectives_done": set(),
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

    print("\n24. the SHIPPED kill quest: Bandits on the Road (1464) reaches B4's verb")
    rows = questdefs.load()
    check(1464 in rows and rows[1464].get("objective_kill") == "corridor_boss"
          and rows[1464].get("giver_spawn") == "errand_giver",
          "quest 1464 is a kill quest bound by SPAWN KEY to the corridor's boss "
          "and given by the errand's giver", str({k: rows[1464].get(k) for k in
                                                   ("objective_kill", "giver_spawn")}))
    boss = authsrv.agents.WORLD.get("spawn", "corridor_boss")
    check(int(boss["agent_id"]) == 94 and boss.get("glow") == 5,
          "the boss row is the glowing raider, agent 94", dict(boss))
    from questdefs import codedstr                          # noqa: E402
    sid, used = codedstr.decode_id(list(rows[1464]["enc_name"]))
    check(sid == 100553 and used == 2,
          "its name is record 201 of our text file 98 -- the record after the "
          "errand's -- so compose.toml derives it and the slice archive carries it",
          sid)
    st = {"quests": {1464}, "objectives_done": set(), "desc_sent": {1464},
          "quests_completed": set(), "agents": {}, "agent_pos": {}}
    sent = []
    authsrv.kill_completes_objective(
        lambda op, vals, label="", **kw: sent.append((op, list(vals), label)),
        st, 94, 0)
    check(1464 in st["objectives_done"] and sent,
          "killing agent 94 with 1464 held meets the objective -- B4's verb on "
          "SHIPPED content, which the archive's second name unblocked",
          f"done {st['objectives_done']}, {len(sent)} message(s)")
    st["interacting"] = authsrv.quest_agent(rows[1464], "giver")
    lines = {q: c for q, c, _r in authsrv._quest_lines(st)}
    check(lines.get(1464) == questdefs.SERVICE_TURN_IN
          and lines.get(1463) == questdefs.SERVICE_SHOW,
          "back at Fisk: 1464 is offered as TURN_IN and the unheld errand as "
          "SHOW -- one giver, two quests, two screens", lines)
    st2 = {"quests": set(), "objectives_done": set(), "quests_completed": set(),
           "interacting": st["interacting"]}
    check(sorted(q for q, _c, _r in authsrv._quest_lines(st2)) == [1463, 1464],
          "with neither held the giver offers BOTH")
    # Both quests held, so the errand cannot put its own '!' on the shared
    # giver (section 15's highest-wins note); what is left is the kill quest's.
    m = authsrv._quest_markers({"quests": {1463, 1464}, "objectives_done": set(),
                                "quests_completed": set()})
    giver = authsrv.quest_agent(rows[1464], "giver")
    check(m.get(giver) is None and 94 not in m,
          "held and undone, a kill quest marks NOBODY: no objective NPC, and the "
          "boss is not an arrow", dict(m))
    m = authsrv._quest_markers({"quests": {1463, 1464}, "objectives_done": {1464},
                                "quests_completed": set()})
    check(m.get(giver) == authsrv.QUEST_MARKER_TURN_IN,
          "and once the boss is dead the giver's arrow comes back")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
