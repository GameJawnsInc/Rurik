"""Quest rows out of content/, and the coded string a quest field goes on as.

    python toolkit/authsrv/questdefs.py          # what the content store holds

WHY THIS IS ITS OWN MODULE. The server needs two things to answer GAME_CMSG
0x0012 REQUEST_QUEST_INFO: which quest a u32 names, and what bytes our prose
becomes. The second is the interesting half and it is testable with no socket,
no client and no vault, so it lives where a test can reach it rather than
inline in a dispatch arm.

THE CODED STRING, AND WHY A BARE SENTENCE IS NOT ONE. `studies/textrec/
FINDINGS.md` 4 derived the rule from the client's own TextParser.cpp and
`studies/quests/FINDINGS.md` 3.2 confirmed it against ArenaNet's wire, 66 of 66
byte-identical: in a coded string, a word **< 0x100 is a MARKER** and a word
**>= 0x100 is a 0x100-biased varint** naming an archive string id. Our own
prose is ASCII, so every code unit in it is below 0x100 -- which means a
sentence sent verbatim is not text to this parser at all, it is a run of
markers.

ArenaNet never sends one bare. Every literal in the live corpus arrives framed:

    0x0BA9  the `%str1%` template id (archive id 2729, a PLAIN record)
    0x0107  the marker that precedes the literal run
    <the UTF-16 code units>
    0x0001  terminator

OBSERVED, in the 0x004C for quest 80 and in the 0x0080 dialog text, where the
substituted literal is the player's own character name.

**Both spellings are offered and NEITHER is asserted correct**, because no
string we built has ever been sent to a client -- `probes.py`'s Q0 sent a bare
string ID (which needs no framing, being >= 0x100) and that is a different
question from a literal. `content/quests.toml` carries `wire_framing` per row
so one run can tell them apart. When the run has spoken, delete the loser here
and say so in FINDINGS -- do not leave both and call it flexibility.

PROVENANCE. Nothing here reads ArenaNet's text. `0x0BA9`, `0x0107` and `0x0001`
are three MEASURED constants -- a template id, a marker and a terminator, read
off our own captures -- and the words they wrap are ours.

Standard library only.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import content                                              # noqa: E402

# MEASURED, from the live corpus (studies/quests/FINDINGS.md 3.3): the framing
# ArenaNet puts around every literal it substitutes into a coded string.
TEMPLATE_STR1 = 0x0BA9      # archive id 2729, `%str1%`, a plain record
LITERAL_MARK = 0x0107       # archive id 263, precedes the literal run
LITERAL_END = 0x0001        # terminator

# The client's own field width for both 0x004C slots, from its RECV descriptor
# (msgshape.py 0x004C -> string16(128)) and from schema/messages.json, which
# agree. 128 CODE UNITS, and the framing spends 3 of them.
FIELD_UNITS = 128

# GAME_SMSG 0x0080, the NPC dialog line, is NARROWER -- string16(122) in both
# the client's own RECV descriptor and schema/messages.json. Six units less than
# 0x004C's, which is exactly the kind of difference that would be found on
# screen rather than in code if the two shared one constant.
DIALOG_UNITS = 122

FRAMINGS = ("bare", "template")


def coded_literal(text, framing="template", limit=FIELD_UNITS):
    """Our prose as the code-unit string `codec.encode` wants for a string16.

    Returns a `str`, not a list: `codec.py` takes a `str` and encodes it as
    UTF-16 code units, so the caller must hand it characters. That conversion
    is the trap `studies/quests/FINDINGS.md` 3.5 names.

    Raises ValueError rather than truncating when the result will not fit the
    field. A silently clipped description would render as a half sentence and
    read as a client-side failure, which is the shape of bug this project keeps
    paying for -- the server would look correct and the screen would not.
    """
    if framing not in FRAMINGS:
        raise ValueError(f"unknown wire_framing {framing!r}; "
                         f"expected one of {FRAMINGS}")
    units = [ord(c) for c in text]
    if any(u > 0xFFFF for u in units):
        raise ValueError("astral characters do not fit one UTF-16 code unit; "
                         "the wire field is a u16 array")
    if framing == "template":
        units = [TEMPLATE_STR1, LITERAL_MARK] + units + [LITERAL_END]
    elif units and (units[0] & ~0x8000) < 0x100:
        # MEASURED 2026-08-15, by doing it: a 0x004C whose description began
        # `0x53` ('S') killed a real client on its own bound check --
        #     Assertion: (codedString[0] & ~WORD_BIT_MORE) >= WORD_VALUE_BASE
        #     P:\Code\Engine\Text\TextApi.cpp(585)          build 38833
        # -- and `asserts.py --grep WORD_VALUE_BASE` finds that same expression
        # at 0x007c9b1d, with five more sites across TextParser and TextEncode.
        # The crash stack carried our sentence verbatim as UTF-16, so the bytes
        # arrived intact and the FIRST WORD is what it refused.
        #
        # That is studies/textrec's marker/varint rule confirmed by the client's
        # own assert, naming both constants. So this is not a style preference:
        # a literal run MUST be introduced by a word >= WORD_VALUE_BASE, which
        # is what `template` framing's 0x0BA9 does. Refused here rather than on
        # the wire, because the failure mode is a CRASH DIALOG, not a bad glyph.
        raise ValueError(
            f"bare framing would put 0x{units[0]:04X} first, which is below "
            f"WORD_VALUE_BASE (0x100). The client asserts on exactly this "
            f"(TextApi.cpp:585) and dies -- MEASURED, not predicted. Use "
            f"wire_framing = \"template\"; `bare` is only for a payload that "
            f"already starts with a string id.")
    if len(units) > limit:
        raise ValueError(
            f"{len(units)} code units exceeds the client's {limit}-unit "
            f"field ({framing} framing spends "
            f"{3 if framing == 'template' else 0} on the framing itself). "
            f"Shorten the text; do not truncate it here.")
    return "".join(chr(u) for u in units)


def enc_string(units):
    """A list of wire code units (an `enc_*` column) as a `str` for the codec."""
    return "".join(chr(int(u)) for u in units)


# GAME_CMSG 0x003B packs its whole meaning into one dword. OBSERVED, 22 of 22
# samples in the live corpus, every one with high byte 0x00 -- the quest-dialog
# family. studies/quests/FINDINGS.md 2.4.
SERVICE_TAG_BIT = 0x800000

# The codes, derived from CONSEQUENCE rather than from any name in the client:
# 0x01 draws GAME_SMSG 0x0049 within 30-55 ms in 5 of 5, and 0x07 draws
# 0x0052 x2 + 0x004A in 3 of 3, across five independent quest ids. The English
# words are OURS -- RECONSTRUCTION on top of an OBSERVED consequence.
SERVICE_OFFER = 0x03        # opens the offer; no quest-family reply, 2 of 2
SERVICE_ACCEPT = 0x01
SERVICE_STEP = 0x04         # objectives update + marker move, n=1
SERVICE_TURN_IN = 0x07
# NOT FOUND: a DECLINE code. No 0x003B value in the corpus produces a refusal,
# because the operator never declined. Do not invent one.


def decode_service_select(value):
    """(quest_id, code) out of GAME_CMSG 0x003B's dword, or None.

    None rather than a guess when the tag bit is clear or the high byte is set:
    those are the OTHER service families -- overrides.json names 8 callers
    across GmNpc, VnLearnSkill, VnUnlockSkill, VnUnlockItem and VnUnlockHero --
    and all 22 captured selects are high-byte 0x00. A decoder that returned a
    quest id for a merchant purchase would be inventing one.
    """
    if not isinstance(value, int) or value < 0:
        return None
    if (value >> 24) != 0 or not (value & SERVICE_TAG_BIT):
        return None
    return ((value & 0x7FFFFF) >> 8, value & 0xFF)


def encode_service_select(quest_id, code):
    """The inverse, for tests. A decoder with no encoder is hard to refute."""
    if not (0 <= quest_id <= 0x7FFF) or not (0 <= code <= 0xFF):
        raise ValueError(f"quest {quest_id} / code {code} does not fit the tag")
    return SERVICE_TAG_BIT | (quest_id << 8) | code


# GAME_SMSG 0x007E's first field, an option KIND. It takes 15, 16, 17, 18, 21,
# 22 and 23 across the corpus and none of them is named anywhere; 18 is what
# every quest offer uses, which is the only reason this constant has a value.
OPTION_KIND_QUEST = 18
# Field 4, 0xFFFFFFFF in 37 of 37 samples. Never seen taking another value, so
# what it MEANS is UNVERIFIED -- this name says where it came from, not what it
# does.
OPTION_NO_ICON = 0xFFFFFFFF


def load(world=None):
    """{quest_id: row} for every content quest row.

    Keyed by the u32 the WIRE uses, not by the TOML section name, because that
    is what arrives in GAME_CMSG 0x0012 and what the server has to look up.
    """
    world = world or content.load()
    out = {}
    for name, row in world.rows("quest").items():
        qid = row.get("quest_id")
        if qid is None:
            raise ValueError(f"content quest row {name!r} has no quest_id")
        if qid in out:
            raise ValueError(
                f"two content quest rows claim quest_id {qid}: "
                f"{out[qid]['_name']!r} and {name!r}. The id is the client's "
                f"only handle on a quest, so a duplicate is a row that can "
                f"never be addressed.")
        row = dict(row)
        row["_name"] = name
        out[qid] = row
    return out


def description_fields(row):
    """(description, objectives) as codec-ready strings for GAME_SMSG 0x004C."""
    framing = row.get("wire_framing", "template")
    return (coded_literal(row.get("description", ""), framing),
            coded_literal(row.get("objectives", ""), framing))


def dialogue_field(row):
    """The giver's spoken line, for GAME_SMSG 0x0080 -- or None if the row has none.

    A NARROWER field than the description's, and the width is checked against
    0x0080's own 122 rather than 0x004C's 128. Sharing one constant between the
    two would put a six-unit error where only a screen could find it.
    """
    text = row.get("giver_dialogue")
    if not text:
        return None
    return coded_literal(text, row.get("wire_framing", "template"),
                         limit=DIALOG_UNITS)


def main():
    quests = load()
    if not quests:
        print("no quest rows in content/")
        return 0
    print(f"{len(quests)} quest row(s):\n")
    for qid in sorted(quests):
        row = quests[qid]
        desc, obj = description_fields(row)
        print(f"  {qid:>5}  {row['_name']}")
        print(f"         enc_name    {row.get('enc_name')}")
        print(f"         framing     {row.get('wire_framing', 'template')}")
        print(f"         description {len(desc)} code units, "
              f"first: {[hex(ord(c)) for c in desc[:4]]}")
        print(f"         objectives  {len(obj)} code units")
    return 0


if __name__ == "__main__":
    sys.exit(main())
