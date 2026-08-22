"""The chat echo, built entirely from measured bytes.

WHAT THIS IS. `GAME_CMSG 0x0064 CHAT_SEND` was test_dispatch's loudest recorded
drop -- "the whole chat and emote surface", arriving with the typed text and
answered with nothing, so the client showed silence. The reply it needs is now
specified from ArenaNet's own traffic (`studies/chat/FINDINGS.md`): the body
rides `0x005D CHAT_MESSAGE_CORE` as a coded string, split at 121 units per
fragment, and the line renders when a commit tag follows -- `0x0061
CHAT_MESSAGE_LOCAL [sender playerId, channel]` for a player line, `0x005E
CHAT_MESSAGE_SERVER [subject playerId, channel]` for a server-composed one.
This module builds those payloads; the dispatch arm in `authsrv.py` sends them.

EVERY CONSTANT HERE IS A MEASUREMENT, and the trigger context travels with it
(`feedback-observed-context-is-part-of-the-claim`):

- `CHANNEL_ALL = 3` / `CHANNEL_EMOTE = 6`: the channel byte separates by
  CONTENT on the live wire with zero exceptions -- every free-conversation line
  is 3, and the one observed slash-command reply (`/bow`) is 6. GWCA's enum
  agrees (CORROBORATED, consulted after).
- `ALL_BODY_WRAPPER = 0x0108` (string id 8): the leading word on 3 of 3
  observed channel-3 player bodies. What record 8 renders as is ArenaNet's and
  encrypted; the id is the measurement.
- `FRAGMENT_UNITS = 121`: both multi-part lines in the corpus split their coded
  string at exactly 121 units = declared(122) - 1 -- the same exclusive-cap rule
  `charstore` measured on 0x00F3's string16(8). NOT 122, which is what
  OpenTyria uses and what a cap read off the field width would give.
- `BOW_TEMPLATE = 1687` with arg slot 13 = playerId: the observed `/bow` reply,
  51 ms after the typed command -- body `#1687 #13 #<pid>` on `0x005E [pid, 6]`.
  n=1, and the arm that uses it matches the trigger exactly (`/bow`, nothing
  else).

The literal-run framing (`0x0107` opens, `0x0001` terminates) is `questdefs`'s
measured pair, imported rather than re-declared so there is one source.

WHAT IS REFUSED, deliberately. Sigils other than `!` (All) have never been
captured -- no labelled run typed guild/team/trade text -- so `@ # $ % \"` are
reported and dropped rather than guessed at; a trade echo would also need the
`#68606` wrapper whose context (outpost trade channel) our world cannot
produce. Slash commands other than `/bow` echo nothing: retail never echoes
the command text itself, and `/bow` is the only reply we hold.

Standard library only. Read-only on the vault; builds strings, sends nothing.
"""
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clientscan"))
import codedstr                                             # noqa: E402
import questdefs                                            # noqa: E402

# MEASURED -- studies/chat/FINDINGS.md 5 (channels, from content), 8 (wrapper),
# 2 (fragment cap), 7 (the /bow exchange).
CHANNEL_ALL = 3
CHANNEL_EMOTE = 6
# CHANNEL 7 IS THE ON-SCREEN WARNING PANEL, and both halves are measured.
# IMAGE: the GmView frame `0x1000007F` dispatches to 0x004E4EFC, whose first
# instruction is `cmp dword ptr [edi],7` -- channel 7 is the only value that
# body accepts, and the panel it draws is named `TxtError` (UTF-16 at
# 0x0094D83C). WIRE: 40 channel-7 tags in the corpus and every one of them sits
# in a skill-refusal batch, while 96 channel-10 and 1 channel-6 tag in the same
# captures never do. That contrast is the discriminating negative -- a channel
# byte that appeared in both populations would prove nothing.
CHANNEL_WARNING = 7
ALL_BODY_WRAPPER = 0x0108      # string id 8, the All-chat body wrapper word
FRAGMENT_UNITS = 121           # declared(122) - 1, measured on both live splits
BOW_TEMPLATE = 1687            # "%player% bows." -- id measured, text ArenaNet's

# THE REFUSAL REASONS. Ids, not words -- the text lives in the owner's archive
# and `textrec.py` resolves it; this is the same "commit the id, resolve the
# string at run time" rule `mapbuild.py` and `typenames.py` follow.
#
# 1960 IS OBSERVED, 39 of 39. Every channel-7 line in the corpus that is not
# the single target-0 case carries coded word 0x8A8, which is exactly
# `codedstr.encode_id(1960)`, and 1960 resolves to the adrenaline refusal.
# Replayed against a pool model with no free parameter it lands on 39 of 39
# pool-short declines and 0 of 4 others.
REFUSE_NOT_ENOUGH_ADRENALINE = 1960
# 1961 IS A RECONSTRUCTION AND MUST NOT BE PROMOTED WITHOUT A RUN. The TEXT is
# observed -- record 937 of file 1, immediately adjacent to 1960's record 936 --
# but THE WIRE HAS ZERO ENERGY REFUSALS: all 43 declines in the corpus are
# 0x0027 attack-skill presses, and 0 of 49 0x0046 casts was ever refused. The
# operator never ran out of energy. So this id rests on the text plus its
# position in the block, and the cheapest thing that settles it is a loopback
# run that reads the sentence off the screen. If the client shows something
# else, this constant is refuted and that is a finding, not a build failure.
REFUSE_NOT_ENOUGH_ENERGY = 1961
PLAYER_ARG_SLOT = 13           # arg slot rendering a playerId as a name (n=2)

assert codedstr.decode_id([ALL_BODY_WRAPPER]) == (8, 1)

# The sigil the client prefixes to All-chat text. The other sigils exist in the
# game but have never been captured here; parse_send names them so the caller
# can refuse each one out loud instead of silently eating it.
SIGIL_ALL = "!"
KNOWN_UNMEASURED_SIGILS = "@#$%\""


def parse_send(text):
    """('all', body) | ('command', name) | ('sigil', text) | ('empty', '').

    The client sends the channel IN the text: `!hello` for All chat, `/bow`
    for a command (studies/cmsg C2/C10 -- typing `rurik one` sends
    `!rurik one`). A bare, unprefixed string has never been captured from a
    real client, so it is classified with the unmeasured sigils rather than
    given a channel it never declared.
    """
    if not text:
        return ("empty", "")
    if text[0] == SIGIL_ALL:
        return ("all", text[1:])
    if text[0] == "/":
        return ("command", text[1:])
    return ("sigil", text)


def all_chat_body(text):
    """The coded-string body for one All-chat line, as codec-ready `str`.

    `[#8, literal-mark] + text + [terminator]` -- the exact framing on 3 of 3
    observed channel-3 player lines. Raises on astral characters for the same
    reason `questdefs.coded_literal` does: the wire field is a u16 array.
    """
    if any(ord(c) > 0xFFFF for c in text):
        raise ValueError("astral characters do not fit one UTF-16 code unit; "
                         "the wire field is a u16 array")
    return (chr(ALL_BODY_WRAPPER) + chr(questdefs.LITERAL_MARK)
            + text + chr(questdefs.LITERAL_END))


def bow_body(player_number):
    """`#1687 #13 #<pid>` -- the observed /bow reply body, for our pid."""
    words = (codedstr.encode_id(BOW_TEMPLATE)
             + codedstr.encode_id(PLAYER_ARG_SLOT)
             + codedstr.encode_id(player_number))
    return "".join(chr(w) for w in words)


def refusal_body(string_id):
    """A bare coded string -- one word, no arguments -- for the warning panel.

    Retail's refusal lines take no substitutions: the whole payload is the
    string id, which is why the observed wire word is a single 0x8A8 rather
    than a template plus argument slots the way `bow_body` builds one.
    """
    return "".join(chr(w) for w in codedstr.encode_id(string_id))


def fragments(body):
    """The body split for `0x005D`, one `str` per fragment, cap 121 units.

    ArenaNet's own splits put 121 units in every non-final fragment and the
    remainder (terminator included) in the last; joining the fragments must
    reproduce the body byte-for-byte, which is what test_chatdefs asserts
    rather than trusting this slicing.
    """
    if not body:
        raise ValueError("an empty coded string is not a chat line; "
                         "refusing to emit a 0x005D with nothing in it")
    return [body[i:i + FRAGMENT_UNITS]
            for i in range(0, len(body), FRAGMENT_UNITS)]
