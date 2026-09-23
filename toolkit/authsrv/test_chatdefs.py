#!/usr/bin/env python3
r"""The chat echo: framing, fragmentation, the dispatch arm, and retail bytes.

    python toolkit/authsrv/test_chatdefs.py

WHAT IS PINNED AND WHY IT CAN FAIL.

1. THE FRAMING IS BYTE-EXACT, proven against ArenaNet rather than against
   ourselves. Section 5 pulls the multi-part advert out of live capture
   20260817T183756, extracts its literal text, re-frames it with OUR builder,
   and requires the result byte-identical to the joined retail body -- offline
   agreement between two of our own components proves nothing, so the referee
   is the wire. It also re-runs the sender cross-check at n=1 as a pinned
   regression (playerId 4 -> a 0x0059 name) so the decode this arm rests on
   cannot silently rot.

2. THE FRAGMENT CAP IS 121, NOT 122. OpenTyria splits at 122 and the field is
   string16(122), so 122 is the number a reasonable edit would "correct" this
   to -- and 121 is what ArenaNet's own splits measure (both of them), matching
   charstore's exclusive-cap rule on 0x00F3. Section 2 pins the boundary from
   both sides and section 5 pins it on the retail fragment itself.

3. THE ARM ECHOES, AND THE REFUSALS REFUSE. _handle_chat_send is called with a
   recording `send`: All chat must produce CORE fragments + LOCAL [pid, 3] in
   that order (the tag renders the line, so a tag-first order would render an
   EMPTY line and look like a client bug); /bow must produce the observed
   #1687 #13 #pid on SERVER [pid, 6]; every other command, sigil and the empty
   string must send NOTHING -- a refusal that quietly echoed would put invented
   bytes on a channel whose grammar we measured.

4. EVERYTHING ENCODES. Section 4 runs every payload this arm can emit through
   the real codec against the real schema -- a string one unit over the field
   cap, or a tag value out of range, dies here and not at a live client.

Needs `vault/captures/live/20260817T183756` for section 5; without the vault
that section is LEDGER.skip'd by name and the floor drops to the offline core.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))

import checks     # noqa: E402
import chatdefs   # noqa: E402
import codedstr   # noqa: E402
import authsrv    # noqa: E402
from codec import Codec  # noqa: E402

# MEASURED from the first green run: 33 checks with the vault, of which 5 are
# section 5's. The floor is the unconditional core (28); section 5 announces
# itself by name when it cannot run rather than shrinking silently. (The first
# draft wrote 26 from a count in my head; the run said 28 -- CLAUDE.md's
# set-the-floor-from-a-green-run rule earning its keep on its own test.)
# 2026-09-23 (DESKWORK-D5 step 7): +12 unconditional (section 6, the refusal block's
# ids and labels) and +4 behind the archive (section 7, declared skip without it);
# 49 with the vault on the green run, floor 28 -> 40. The fix pass the same day:
# +3 unconditional in section 6 (1964 stays RECONSTRUCTION; refusal_body's
# send-path guard, and its plain body); section 7's skip now catches SystemExit,
# so the BARE run is green again -- 43 checks + 2 declared skips, measured with
# RURIK_VAULT at an empty directory; 52 with the vault. Floor 40 -> 43.
LEDGER = checks.Ledger("chat echo: framing, fragments, arm, retail bytes",
                       floor=43)
check = checks.adopt(LEDGER)

CAPTURE = "20260817T183756"   # the multi-part advert, studies/chat 2 and 3


def recording_send():
    sent = []
    return (lambda op, vals, label="", quiet=False:
            sent.append((op, vals, label))), sent


def main():
    print("== 1. the All-chat framing, unit for unit ==")
    body = chatdefs.all_chat_body("hi")
    check([ord(c) for c in body] == [0x0108, 0x0107, 0x68, 0x69, 0x0001],
          "wrapper #8, literal mark, text, terminator -- nothing else",
          f"{[hex(ord(c)) for c in body]}")
    parsed = codedstr.parse_coded(codedstr.from_wire(body))
    check(parsed[0] == ("id", 8) and parsed[1] == ("id", 7)
          and parsed[-1] == ("marker", 1),
          "and the repo's own coded-string parser reads it back",
          f"{parsed}")
    try:
        chatdefs.all_chat_body("a\U0001F600b")
        check(False, "an astral character is refused", "it was accepted")
    except ValueError:
        check(True, "an astral character is refused",
              "the wire field is a u16 array; a surrogate pair would be two "
              "units the client renders as two garbage glyphs")

    print("== 2. fragmentation at 121, from both sides of the boundary ==")
    at_cap = chatdefs.all_chat_body("x" * 118)          # 3 framing + 118 = 121
    check(len(at_cap) == 121 and len(chatdefs.fragments(at_cap)) == 1,
          "a 121-unit body is ONE fragment",
          f"len {len(at_cap)}, {len(chatdefs.fragments(at_cap))} fragment(s)")
    over = chatdefs.all_chat_body("x" * 119)            # 122 units
    fr = chatdefs.fragments(over)
    check([len(f) for f in fr] == [121, 1],
          "one unit over splits 121 + 1 -- the cap is 121, not the field's 122",
          f"{[len(f) for f in fr]}; 122 is what OpenTyria uses and what the "
          f"field width suggests, and ArenaNet's own splits refute it")
    check("".join(fr) == over,
          "and joining the fragments reproduces the body byte-for-byte",
          "the slicing is not trusted, it is checked")
    long_body = chatdefs.all_chat_body("y" * 300)       # 303 units
    fr = chatdefs.fragments(long_body)
    check([len(f) for f in fr] == [121, 121, 61]
          and "".join(fr) == long_body,
          "three fragments: every non-final one is exactly 121",
          f"{[len(f) for f in fr]}")
    try:
        chatdefs.fragments("")
        check(False, "an empty body is refused", "it was accepted")
    except ValueError:
        check(True, "an empty body is refused",
              "a 0x005D with nothing in it is not a chat line")

    print("== 3. the dispatch arm: echoes echo, refusals send nothing ==")
    send, sent = recording_send()
    authsrv._handle_chat_send(send, {}, 0, 0, "!hello")
    check(len(sent) == 2
          and sent[0][0] == authsrv.GAME_SMSG_CHAT_MESSAGE_CORE
          and sent[1][0] == authsrv.GAME_SMSG_CHAT_MESSAGE_LOCAL,
          "!hello -> one CORE fragment then LOCAL, in that order",
          f"{[(hex(op), v) for op, v, _l in sent]} -- the tag commits the "
          f"buffered body, so tag-first would render an empty line")
    check(sent[1][1] == [authsrv.PLAYER_NUMBER, chatdefs.CHANNEL_ALL],
          "and the tag is [PLAYER_NUMBER, channel 3]",
          f"{sent[1][1]} -- 47/47 live 0x0061 words are the sender's playerId "
          f"and every free-conversation line is channel 3")
    check([ord(c) for c in sent[0][1][0]]
          == [0x0108, 0x0107, 0x68, 0x65, 0x6C, 0x6C, 0x6F, 0x0001],
          "and the body is the measured framing around the typed text",
          f"{[hex(ord(c)) for c in sent[0][1][0]]}")

    send, sent = recording_send()
    authsrv._handle_chat_send(send, {}, 0, 0, "!" + "z" * 130)
    check(len(sent) == 3
          and [op for op, _v, _l in sent]
          == [authsrv.GAME_SMSG_CHAT_MESSAGE_CORE,
              authsrv.GAME_SMSG_CHAT_MESSAGE_CORE,
              authsrv.GAME_SMSG_CHAT_MESSAGE_LOCAL],
          "a long line is two CORE fragments then ONE tag",
          f"{[(hex(op), len(v[0]) if isinstance(v[0], str) else v) for op, v, _l in sent]} "
          f"-- ArenaNet commits a multi-part line once per channel, never per "
          f"fragment (both live splits)")
    check(len(sent[0][1][0]) == 121,
          "and the first fragment is exactly the measured 121",
          f"{len(sent[0][1][0])}")

    send, sent = recording_send()
    authsrv._handle_chat_send(send, {}, 0, 100, "/bow")
    check([op for op, _v, _l in sent]
          == [authsrv.GAME_SMSG_CHAT_MESSAGE_CORE,
              authsrv.GAME_SMSG_CHAT_MESSAGE_SERVER],
          "/bow -> CORE then SERVER: the one slash-command reply we hold",
          f"{[(hex(op), v) for op, v, _l in sent]}")
    check([ord(c) for c in sent[0][1][0]]
          == [0x0797, 0x010D, 0x0100 + authsrv.PLAYER_NUMBER],
          "and its body is the observed #1687 #13 #pid, re-encoded",
          f"{[hex(ord(c)) for c in sent[0][1][0]]} against the live exchange "
          f"51 ms after the typed /bow (20260818T132739)")
    check(sent[1][1] == [authsrv.PLAYER_NUMBER, chatdefs.CHANNEL_EMOTE],
          "on the emote channel, subject = our player",
          f"{sent[1][1]}")

    for text, why in (("/dance", "no reply for it in any capture"),
                      ("@guild hello", "guild sigil never captured"),
                      ("#team hello", "team sigil never captured"),
                      ("$wts stuff", "trade sigil never captured"),
                      ("plain no sigil", "a real client always prefixes"),
                      ("", "empty")):
        send, sent = recording_send()
        authsrv._handle_chat_send(send, {}, 0, 0, text)
        check(sent == [],
              f"refused with NOTHING sent: {text!r}",
              f"{why}; a refusal that echoed anyway would put invented bytes "
              f"on a measured channel")

    print("== 4. everything this arm can emit survives the real codec ==")
    codec = Codec()
    for optext, op, vals in (
            ("CORE short", 0x005D, [chatdefs.all_chat_body("hello")]),
            ("CORE at cap", 0x005D, [chatdefs.all_chat_body("x" * 118)]),
            ("CORE bow", 0x005D, [chatdefs.bow_body(1)]),
            ("LOCAL", 0x0061, [1, chatdefs.CHANNEL_ALL]),
            ("SERVER", 0x005E, [1, chatdefs.CHANNEL_EMOTE])):
        blob = codec.encode("GAME_SMSG", op, vals)
        back_op, back_vals, used = codec.decode_one("GAME_SMSG", blob)
        check(back_op == op and used == len(blob)
              and list(back_vals[1:]) == vals,
              f"{optext} encodes and round-trips through the schema",
              f"0x{op:04X}: {len(blob)} bytes, decode consumed {used}")
    hot = chatdefs.fragments(chatdefs.all_chat_body("x" * 119))[0]
    blob = codec.encode("GAME_SMSG", 0x005D, [hot])
    check(len(blob) <= 248,
          "a full 121-unit fragment fits the client's declared 248-byte cap",
          f"{len(blob)} bytes on the wire")

    print("== 5. the retail bytes, if the vault is here ==")
    cap_dir = None
    try:
        import vaultpath
        d = os.path.join(str(vaultpath.require_dir()), "captures", "live",
                         CAPTURE)
        cap_dir = d if os.path.isdir(d) else None
    except (Exception, SystemExit):
        cap_dir = None
    if not cap_dir:
        LEDGER.skip("retail cross-check (5 checks)",
                    f"vault/captures/live/{CAPTURE} not present")
    else:
        import cmsgstream
        rows = cmsgstream.timed(CAPTURE, want_dir="s2c", channel="game")
        perconn = {}
        for t, conn, op, values in rows:
            perconn.setdefault(conn, []).append((op, values))
        # the advert connection: the only one in this capture with 0x005D
        target = [(c, m) for c, m in perconn.items()
                  if any(op == 0x5D for op, _v in m)]
        check(len(target) == 1,
              "exactly one connection in the capture carries chat bodies",
              f"{[c for c, _m in target]}")
        conn, msgs = target[0]
        players = {v[1]: v[7] for op, v in msgs if op == 0x59 and len(v) >= 8}
        lines, pending = [], []
        for op, v in msgs:
            if op == 0x5D:
                pending.append(v[1])
            elif op in (0x5E, 0x5F, 0x61):
                lines.append((op, v[1], v[2], "".join(pending)))
                pending = []
        check([(op, w, ch) for op, w, ch, _b in lines]
              == [(0x61, 4, 12), (0x61, 4, 3)],
              "the two committed lines are 0x0061 [player 4, trade] and "
              "[player 4, All] -- the same advert, two channels",
              f"{[(hex(op), w, ch) for op, w, ch, _b in lines]}")
        check(4 in players,
              "and playerId 4 resolves in this connection's own 0x0059 table",
              f"player table holds {sorted(players)}; the sender/body "
              f"cross-check at n=1, pinned so the decode cannot rot")
        allchat = lines[1][3]
        check(ord(allchat[0]) == 0x0108 and ord(allchat[1]) == 0x0107
              and ord(allchat[-1]) == 0x0001,
              "the retail All-chat body wears exactly our framing",
              f"first two units {hex(ord(allchat[0]))}, "
              f"{hex(ord(allchat[1]))}; last {hex(ord(allchat[-1]))}")
        text = allchat[2:-1]
        rebuilt = chatdefs.all_chat_body(text)
        frags = chatdefs.fragments(rebuilt)
        retail_frags = []
        for op, v in msgs:
            if op == 0x5D:
                retail_frags.append(v[1])
        check(rebuilt == allchat and len(frags) == 2
              and frags[0] in retail_frags and frags[1] in retail_frags,
              "re-framing the extracted text reproduces ArenaNet's bytes, "
              "fragment boundaries included",
              f"rebuilt {len(rebuilt)} units -> fragments "
              f"{[len(f) for f in frags]}; retail fragments "
              f"{[len(f) for f in retail_frags]}")

    # DESKWORK-D5 step 7 (2026-09-23): the refusal block as a table of IDS and
    # OUR labels. Nothing here is text -- a check that compared a sentence
    # would be committing it.
    print("== 6. the refusal block: ids and labels, never text ==")
    lo, hi = chatdefs.REFUSAL_BLOCK
    check((lo, hi) == (1934, 1993) and sorted(chatdefs.REFUSAL_REASONS) == list(range(lo, hi + 1)),
          "the table is exactly the 60 ids 1934..1993, contiguous, none missing",
          f"{len(chatdefs.REFUSAL_REASONS)} ids, {lo}..{hi}")
    check(len(set(chatdefs.REFUSAL_REASONS.values())) == 60
          and all(v.replace("_", "").isalnum() and v == v.lower()
                  for v in chatdefs.REFUSAL_REASONS.values()),
          "60 distinct labels, each a lower-case snake_case word of ours")
    check(chatdefs.REFUSAL_REASONS[chatdefs.REFUSE_NOT_ENOUGH_ADRENALINE] == "not_enough_adrenaline"
          and chatdefs.REFUSAL_REASONS[chatdefs.REFUSE_NOT_ENOUGH_ENERGY] == "not_enough_energy"
          and chatdefs.REFUSAL_REASONS[chatdefs.REFUSE_WEAPON_TYPE] == "skill_needs_different_weapon_type"
          and chatdefs.REFUSE_WEAPON_TYPE == 1985,
          "the three named constants resolve to their labels: 1960, 1961, 1985")
    check(chatdefs.refusal_evidence(1960) == "OBSERVED"
          and chatdefs.refusal_evidence(1961) == "OBSERVED"
          and chatdefs.refusal_evidence(1934) == "OBSERVED"
          and chatdefs.refusal_evidence(1988) == "OBSERVED"
          and chatdefs.REFUSAL_OBSERVED == {1934, 1960, 1961, 1988},
          "exactly four ids are OBSERVED (1960 39 of 39, 1961 on screen and 17x on the wire, "
          "1934 1 of 1, 1988 1 of 1 -- the recharge refusal, fix pass 2026-09-23)")
    check(chatdefs.refusal_evidence(1964) == "RECONSTRUCTION",
          "1964 -- the OTHER id with the recharging sentence -- stays RECONSTRUCTION: never "
          "on any wire held; the id retail sent was 1988")
    check(all(chatdefs.refusal_evidence(i) == "RECONSTRUCTION"
              for i in chatdefs.REFUSAL_REASONS if i not in chatdefs.REFUSAL_OBSERVED),
          "every other id is RECONSTRUCTION -- the label says so at the read")
    try:
        chatdefs.refusal_evidence(1933)
        check(False, "an id outside the block must raise")
    except KeyError:
        check(True, "an id outside the block (1933) raises KeyError")
    check(chatdefs.refusal_reason_id("skill_needs_different_weapon_type") == 1985
          and chatdefs.refusal_reason_id("not_enough_adrenaline") == 1960,
          "a label resolves back to its id")
    for lbl in ("attribute_check_failed", "attribute_check_missed"):
        try:
            chatdefs.refusal_reason_id(lbl)
            check(False, f"the templated {lbl} must be refused")
        except ValueError:
            check(True, f"the templated {lbl} (takes arguments) is refused as a bare body")
    check(chatdefs.REFUSAL_TEMPLATED == {1942, 1943}
          and all(i in chatdefs.REFUSAL_REASONS for i in chatdefs.REFUSAL_TEMPLATED),
          "the two templated ids are in the block and marked")
    # The guard on the SEND path (fix pass): a constant handed straight to
    # refuse_press never passes refusal_reason_id, so refusal_body must refuse
    # a templated id itself -- and still build the plain ones.
    try:
        chatdefs.refusal_body(1942)
        check(False, "refusal_body(1942) must refuse a templated id")
    except ValueError:
        check(True, "refusal_body refuses a templated id on the send path (1942), not only "
                    "refusal_reason_id -- the guard a constant cannot bypass")
    check(len(chatdefs.refusal_body(1988)) == 1 and len(chatdefs.refusal_body(1934)) == 1,
          "and still builds the one-word body for a plain id (1988, 1934)")
    try:
        chatdefs.refusal_reason_id("no_such_label")
        check(False, "an unknown label must raise")
    except KeyError:
        check(True, "an unknown label raises KeyError")
    body = chatdefs.refusal_body(chatdefs.REFUSE_WEAPON_TYPE)
    check(len(body) == 1 and [ord(c) for c in body] == list(codedstr.encode_id(1985)),
          "#1985's body is the one coded word codedstr makes of it (the same shape as "
          "1960's 0x8A8)", f"{[hex(ord(c)) for c in body]}")

    print("== 7. the archive: every id in the block is a PLAIN record; the neighbours "
          "are encrypted (the boundary, not the text) ==")
    try:
        import textrec
        idx = textrec.TextIndex()
    # textrec REFUSES with SystemExit when the pinned build is not in the vault
    # (it will not fall through to C:\gw); `except Exception` alone let that
    # escape and the test died bare with no verdict -- a regression from main
    # the engineering review caught (fix pass 2026-09-23).
    except (Exception, SystemExit) as ex:                          # noqa: BLE001
        LEDGER.skip("refusal block archive check (4 checks)",
                    f"{type(ex).__name__}: {str(ex).splitlines()[0]}")
        idx = None
    if idx is not None:
        with idx:
            plain = {i for i in chatdefs.REFUSAL_REASONS if idx.needs_key(i) is False}
            nonempty = {i for i in plain if idx.get(i)}
            check(plain == set(chatdefs.REFUSAL_REASONS),
                  "all 60 ids resolve to PLAIN records in the owner's archive",
                  f"{len(plain)} plain of {len(chatdefs.REFUSAL_REASONS)}")
            check(nonempty == plain, "and none of them is empty", f"{len(nonempty)}")
            enc = {i for i in chatdefs.REFUSAL_ENCRYPTED_NEIGHBOURS if idx.needs_key(i) is True}
            check(enc == set(chatdefs.REFUSAL_ENCRYPTED_NEIGHBOURS),
                  "the 13 neighbours 1928-1933 and 1994-2000 are ENCRYPTED -- the block's "
                  "edges are where the route's '60 readable, 6 encrypted' put them (1928-1993)",
                  f"{sorted(enc)}")
            check(idx.needs_key(1985) is False and idx.needs_key(1960) is False,
                  "the two ids this server sends are plain (a bare coded word renders them)")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
