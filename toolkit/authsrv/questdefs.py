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
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "clientscan"))
import codedstr                                             # noqa: E402

# MEASURED, from the live corpus (studies/quests/FINDINGS.md 3.3): the framing
# ArenaNet puts around every literal it substitutes into a coded string.
# The three framing words, with their DECODED archive ids beside them. A word
# and the id it denotes are different numbers -- id = word - 0x100 -- and
# `LITERAL_MARK`'s comment used to read "archive id 263", which is the raw
# word and not the id. That is the rival reading `studies/quests/FINDINGS.md`
# 3.2 spends a section refuting, sitting in a live comment two lines under a
# neighbour that had it right. Both are checked below rather than asserted.
TEMPLATE_STR1 = 0x0BA9      # id 2729, `%str1%`, a plain record
LITERAL_MARK = 0x0107       # id 7, precedes the literal run
LITERAL_END = 0x0001        # terminator (a marker, below WORD_VALUE_BASE)

assert codedstr.decode_id([TEMPLATE_STR1]) == (2729, 1)
assert codedstr.decode_id([LITERAL_MARK]) == (7, 1)
assert LITERAL_END < codedstr.BIAS

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

    MEASURED 2026-08-18 (title_track runs 1-2, studies/character/RUNS.md):
    a literal filling a string16 field EXACTLY to its declared cap was an
    instant client hangup (Code=007, no assert) on 0x00F3's string16(8),
    while 7 of 8 units passed -- the receive check treats the declared
    length as exclusive, or reserves a terminator slot. Callers should pass
    `limit = declared - 1` for any small field; the one field this is
    measured on is 8 units wide, and every previously-working literal in
    this repo sat far below its field's cap, so the general rule is
    plausible and unproven.
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
    elif units and (units[0] & ~codedstr.CONT) < codedstr.BIAS:
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
# CORRECTED 2026-08-16, and the correction is structural: a dialogue option is
# the quest NAME and an ENTRY POINT, not the accept. Selecting it opens a SECOND
# screen carrying the description, the reward and accept/decline. Our server
# collapsed the two, so `SERVICE_OFFER` was misnamed -- code 0x03 means "show me
# this quest", and the accept happens one screen later.
SERVICE_ACCEPT = 0x01
SERVICE_DECLINE = 0x02
SERVICE_SHOW = 0x03         # was SERVICE_OFFER; renamed for what it does
SERVICE_ADVANCE = 0x04
SERVICE_IN_PROGRESS = 0x05
SERVICE_TURN_IN = 0x07

# DECLINE IS NO LONGER NOT_FOUND, and how it hid is worth one sentence: it is
# OFFERED in a 0x007E beside every accept line (11 of 11, same burst, same
# timestamp, same quest id) and was never CLICKED, so a search over what players
# sent could not see it. The OFFER is OBSERVED; the CONSEQUENCE is not -- GWW
# says a declined quest stays available, the wire is silent, and the arm that
# handles it must say so rather than replicate a guess.

# The option KIND is bound to the code ONE-TO-ONE, 41 of 41 across both keyed
# sessions. This is not decoration: our server sent kind 18 with codes 0x01 and
# 0x07, and NEITHER PAIR OCCURS ON ARENANET'S WIRE (0 of 41). Pick the kind from
# the code rather than hardcoding one.
OPTION_KIND = {
    SERVICE_ACCEPT: 16,
    SERVICE_DECLINE: 17,
    SERVICE_SHOW: 18,
    SERVICE_ADVANCE: 21,
    SERVICE_IN_PROGRESS: 22,
    SERVICE_TURN_IN: 23,
}

# Kind 15 exists (n=2, never clicked) and carries tag 0x00000080 -- the 0x800000
# bit CLEAR, so `decode_service_select` refuses it by design and
# `encode_service_select` cannot express it. Do not emit one until 0x003B has a
# non-quest arm; a click on it would hit the None branch.


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


# Field 4, 0xFFFFFFFF in 41 of 41 samples. Never seen taking another value.
#
# IT WAS CALLED OPTION_NO_ICON AND THAT NAME WAS WRONG. The icon does not come
# from this field at all -- it comes from the KIND, measured on screen
# 2026-08-16 (vault/captures/harness/20260816T111948): one option of every kind
# in one window drew six different icons while every field 4 was 0xFFFFFFFF.
# A name invented from "it is always the same value" outlived its evidence by
# three weeks, which is the failure this repo's labelling vocabulary exists to
# prevent.
#
# TWO READINGS SURVIVE and neither is testable from the corpus: the field may be
# an icon OVERRIDE whose 0xFFFFFFFF means "use the kind's own", or it may have
# nothing to do with icons. The name below says only what is known.
OPTION_FIELD4_ALWAYS = 0xFFFFFFFF

# What each kind DRAWS, measured in one frame with six lines in one window so
# the icons are compared rather than recalled:
#
#   16  accept       green tick
#   17  decline      red prohibition sign
#   18  available    gold '!'        <- the '!' the owner described
#   21  advance      green dot
#   22  in progress  gold '?'        <- and the '?'
#   23  turn in      a bag
#
# So the '!' and the '?' are ONE mechanism: the option kind, which is bound 1:1
# to the 0x003B code. Three runs looked for them over the NPC's head first.
OPTION_ICONS = {16: "green tick", 17: "red prohibition", 18: "gold !",
                21: "green dot", 22: "gold ?", 23: "a bag"}


def option_kind(code):
    """The 0x007E kind that goes with a 0x003B code. Raises on an unknown one.

    Raising rather than defaulting is the point: a default would silently
    reproduce the bug this table was written to fix, where every option went out
    as kind 18 including the two pairings ArenaNet never sends.
    """
    try:
        return OPTION_KIND[code]
    except KeyError:
        raise ValueError(
            f"no observed 0x007E kind for 0x003B code 0x{code:02X}; the corpus "
            f"binds kinds to codes 1:1 in 41 of 41 and this code is not among "
            f"them. Measure one before sending it.")


# THE QUEST-LOG FLAGS WORD -- 0x0049's field 5 and 0x0050's field 2 --
# RANGERPRE-S18 (QUESTFLOW-A1). A PER-QUEST CONSTANT on retail, and it is not
# always 32: OBSERVED on 20260929T150923, 12 accepts, 0 on five (q80 :59969
# 184.441, q90 :53880 772.586, q52 :55934 632.056, q68 :56025 782.141, q75
# :56064 921.161) and 32 on the other seven; the same quest carries the same
# value on every capture that accepts it, and 36 of the tape's 37 0x0050
# replays repeat the accept's value exactly. The 0x20 bit files the quest
# under "Primary Quests" (studies/quests FINDINGS 1.4, seen on screen); what 0
# files under on OUR client is UNVERIFIED. Ours sent 32 for every quest until
# S18, so the DEFAULT stays 32 -- OURS, the value a row that says nothing has
# always carried; a row declares 0 with `quest_log_flags = 0`.
#
# THE LOW TWO BITS ARE PROGRESS, NOT THE QUEST, and a row may not carry them.
# Bit 0 is DESC_FILLED: 0x004C's body sets it and 0x0054's gate reads it
# (0x0080F9CD; complete_objective's comment). Bit 1 follows the quest's 0x004D:
# the tape's 37th replay is q79 at 34 = 32 | 2 (:59427 1216.783), the only one
# after its 0x004D (:53756 1192.658) -- OBSERVED, n = 1. A row that set either
# would declare a quest's progress as its constant, so log_flags refuses them.
QUEST_LOG_FLAGS_DEFAULT = 32
QUEST_LOG_PROGRESS_BITS = 0x03


def log_flags(row):
    """The row's quest-log flags word for 0x0049 / 0x0050, validated.

    `quest_log_flags` when the row has it, QUEST_LOG_FLAGS_DEFAULT (32) when
    not. Refuses a non-int (a bool included), a negative, anything past a u32,
    and any of QUEST_LOG_PROGRESS_BITS -- the reasons are the block above."""
    v = row.get("quest_log_flags", QUEST_LOG_FLAGS_DEFAULT)
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(f"quest_log_flags = {v!r} is not an int")
    if not 0 <= v <= 0xFFFFFFFF:
        raise ValueError(f"quest_log_flags = {v} does not fit the u32 field")
    if v & QUEST_LOG_PROGRESS_BITS:
        raise ValueError(
            f"quest_log_flags = {v} (0x{v:X}) sets bit 0 or 1, which the "
            f"CLIENT's progress owns (0 = description filled by 0x004C, 1 = "
            f"set after the quest's 0x004D) -- a row declaring them would "
            f"send a quest's progress as its constant")
    return v


# THE QUEST-LOG STRING SLOTS -- 0x0049's s1, s2, s3 and 0x0050's, RANGERLOOP-F5.
# s1 IS THE HEADING'S ARGUMENT, and it is a REGION, not the quest's name.
#
# OBSERVED, static (build 38797, codescan): the 0x0049 dispatcher (0x0091DB70)
# hands the handler 0x0080F0A0 the message's first string slot as [ebp+0x18],
# and the handler copies it into the log record's +0x08 (0x0080F0E2..F130; s2
# -> +0x0C, s3 -> +0x10). 0x0050's pair (0x0091DC70 -> 0x0080F470) does the
# same with its first slot (0x0080F4FA). The log's heading formatter (0x0057DC60)
# reads the record through 0x0080DB40 -- out[0] = +0x08, out[2] = the flags
# word at +0x04 -- and picks its sort code off the flags: 0x10 -> 0, 0x20 -> 1
# (id 1124, no argument -- "Primary Quests", what a flags-32 row has always
# drawn), 0x40 -> 2 (id 71800), none -> 3 (jump table 0x0057DDA8). Arm 3
# (0x0057DD77) formats id 1125 with +0x08 as its one argument (marker 0x0A) --
# so a flags-0 quest is filed under "<s1> Quests".
#
# CORROBORATED, the live corpus (2026-10-07, 137 0x0049 / 0x0050 rows, 24
# quests, 47 with flags 0 or 2): s1 is exactly ONE unit on 137 of 137, never
# equal to s2, and a function of the home map -- 146, 148 and 160 carry
# 0x3D64 (string 15460), 212 / 238 / 242 carry 0x617D (24701), 280 0x0E63
# (3427), 449 0x6185 (24709); textrec reads each as a region's name. Ours sent
# the quest's own name in all three slots, so a flags-0 quest was filed under
# its own name plus the suffix (RANGERLOOP-F5, seen on our client 2026-09-30).
#
# s2 IS READ AS THE NAME: one value per quest and 24 distinct values for the
# corpus's 24 quests (CORROBORATED by that alone). Which slot the tracker and
# the 'Quest Added' toast draw is UNVERIFIED -- every run of ours sent the
# name in all three. s3's meaning is NOT FOUND: retail's is 4-5 units, never
# equal to s2, one value per quest and shared by up to 3 quests (15 values
# for 24). Ours keeps the name in s2 and s3, as before.
def region_units(row):
    """The row's `enc_region` as [unit], validated, or None when absent.

    ONE coded unit, because s1 is one unit on 137 of 137 retail rows: a list
    holding a single int in 0x0100..0xFFFF with the continuation bit
    (codedstr.CONT) clear -- a complete one-word string id, never a marker
    (< 0x100, the TextApi.cpp:585 assert coded_literal's note is about), never
    the first word of a longer id. Raises ValueError otherwise."""
    v = row.get("enc_region")
    if v is None:
        return None
    if not isinstance(v, (list, tuple)) or len(v) != 1:
        raise ValueError(
            f"enc_region = {v!r} is not ONE coded unit -- retail's s1 is a "
            f"single unit on 137 of 137 quest-log rows")
    u = v[0]
    if isinstance(u, bool) or not isinstance(u, int):
        raise ValueError(f"enc_region holds {u!r}, not a code unit")
    if not codedstr.BIAS <= u <= 0xFFFF or u & codedstr.CONT:
        raise ValueError(
            f"enc_region = [0x{u:X}] is not a one-word string id: a unit "
            f"below 0x100 is a MARKER and the continuation bit 0x8000 opens a "
            f"multi-unit id")
    return [u]


def log_strings(row, region=True):
    """(s1, s2, s3) for 0x0049 / 0x0050, as codec-ready strs.

    s1 is the row's enc_region when it has one and `region` is set; else the
    name, which is what every slot carried before RANGERLOOP-F5 (and what
    --no-quest-region sends). s2 and s3 are the name."""
    nm = enc_string(row.get("enc_name") or [])
    reg = region_units(row) if region else None
    return (enc_string(reg) if reg is not None else nm), nm, nm


def check_accept_grants(row, item_rows):
    """Refuse a row's accept-time grants unless each resolves (RANGERPRE-S18,
    QUESTFLOW-A3): `accept_items` a list of content/items.toml keys present
    in `item_rows`, `accept_skills` a list of non-negative ints. Either may be
    absent. Raises ValueError naming the bad entry; returns None."""
    items = row.get("accept_items")
    if items is not None:
        if not isinstance(items, (list, tuple)):
            raise ValueError(f"accept_items = {items!r} is not a list of item keys")
        for key in items:
            if not isinstance(key, str) or key not in item_rows:
                raise ValueError(
                    f"accept_items names {key!r}, which is not a content item "
                    f"row -- the accept would grant nothing the client can be "
                    f"sent, so the loader refuses it now")
    skills = row.get("accept_skills")
    if skills is not None:
        if not isinstance(skills, (list, tuple)):
            raise ValueError(f"accept_skills = {skills!r} is not a list of skill ids")
        for sid in skills:
            if isinstance(sid, bool) or not isinstance(sid, int) or sid < 0:
                raise ValueError(f"accept_skills holds {sid!r}, not a skill id")


def check_handin_items(row, item_rows):
    """Refuse a row's hand-in item columns unless each resolves (RANGERPRE-S20,
    QUESTFLOW-H4): `handin_items` (what the hand-in takes back) and
    `reward_items` (what it grants) are lists of content/items.toml keys
    present in `item_rows`. Either may be absent. Raises ValueError naming
    the bad entry; returns None."""
    for column in ("handin_items", "reward_items"):
        keys = row.get(column)
        if keys is None:
            continue
        if not isinstance(keys, (list, tuple)):
            raise ValueError(f"{column} = {keys!r} is not a list of item keys")
        for key in keys:
            if not isinstance(key, str) or key not in item_rows:
                raise ValueError(
                    f"{column} names {key!r}, which is not a content item "
                    f"row -- the hand-in could neither find nor declare it, "
                    f"so the loader refuses it now")


def load(world=None):
    """{quest_id: row} for every content quest row.

    Keyed by the u32 the WIRE uses, not by the TOML section name, because that
    is what arrives in GAME_CMSG 0x0012 and what the server has to look up.

    A row's `quest_log_flags`, its `enc_region` (RANGERLOOP-F5), its
    accept-time grants and (RANGERPRE-S20) its hand-in items are validated
    HERE (RANGERPRE-S18), so a bad one stops the server at startup rather
    than at the first accept or hand-in.
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
        try:
            log_flags(row)
            region_units(row)
            if row.get("accept_items") is not None \
                    or row.get("accept_skills") is not None:
                check_accept_grants(row, world.rows("item"))
            if row.get("handin_items") is not None \
                    or row.get("reward_items") is not None:
                check_handin_items(row, world.rows("item"))
        except ValueError as exc:
            raise ValueError(f"content quest row {name!r}: {exc}") from None
        row = dict(row)
        row["_name"] = name
        out[qid] = row
    return out


def description_fields(row):
    """(description, objectives) as codec-ready strings for GAME_SMSG 0x004C."""
    framing = row.get("wire_framing", "template")
    return (coded_literal(row.get("description", ""), framing),
            coded_literal(row.get("objectives", ""), framing))


# THE REWARD BLOCK. There is no reward message and no reward string: the reward
# is a 19-code-unit SUFFIX inside the same coded string as the description,
# byte-identical between the 0x0080 dialog line and 0x004C's description slot in
# 17 of 17 (screen, quest) pairs. So a reward costs us three of ArenaNet's
# generic string ids and two numbers of our own, and no authored text from
# either side -- CLAUDE.md's "commit the id, resolve the string at run time"
# exactly.
#
# All three ids are needs_key = True: ArenaNet's own encrypted generics, shared
# by every quest. We cannot read them and do not need to.
REWARD_HEADER = (0x2AE8, 0xE7D4, 0xE5CC, 0x3672)    # ref 10728
REWARD_SLOT_A = (0x2AEA, 0x8C3F, 0xB519, 0x6611)    # ref 10730, one numeric arg
REWARD_SLOT_B = (0x2AEC, 0xDAC7, 0x81AE, 0x3482)    # ref 10732, one numeric arg
RUN_SEPARATOR = 0x0002
NUMERIC_ARG = 0x0101
# Separator + `\n[b]` (archive id 2). A run separator alone joins; this breaks.
PARAGRAPH_BREAK = chr(0x0002) + chr(0x0102)

# WHICH SLOT IS WHICH -- OBSERVED 2026-08-16, and it had to be a probe.
# The magnitudes across seven quests fit "A is experience, B is gold"
# -- (100,10), (250,25), (500,25), (500,100) -- but both templates are
# encrypted and the RC4 key is NOT FOUND, so neither the wire nor the archive
# could settle it and a plausibility argument is not a measurement.
# `probes.py --probe quest_reward` fed slot A 111 and slot B 222, values outside
# every observed number so no reading could be ambiguous, and the rendered pane
# read "111 Experience" / "222 Gold" in BOTH the quest log and the dialog
# window. vault/captures/harness/20260816T103824.
REWARD_SLOT_NAMES = ("experience (ref 10730)", "gold (ref 10732)")


def reward_run(slot_a, slot_b=None):
    """The reward suffix, as a codec-ready str. 19 code units, or 12 with no B.

    `0101 <word>` is a numeric argument whose value is `word - 0x100`
    (CORROBORATED: quest 62's fourth run feeds the PLAIN template 2438,
    `%str1%: %num1%`, exactly `0101 0104`). So each number is bounded by what
    fits one u16 after the bias.

    `slot_b=None` OMITS the second line entirely, which is what a quest with no
    gold needs -- ArenaNet's own "A Personal Vault" renders `Reward: / 500
    Experience` and nothing else. Emitting a zero would draw a line reading
    zero, which is worse than drawing none.

    SLOT A IS EXPERIENCE, promoted from the seven-quest magnitude argument to
    CORROBORATED 2026-08-16: a live client showed `Reward: 500 Experience` for a
    stock quest, and 500 is exactly what slot A carries for quests 82, 86 and
    1462. The rival assignment would have put 500 in the gold line. SLOT B IS
    GOLD: OBSERVED on screen the same day (the quest_reward probe above rendered
    "222 Gold" for slot B -- this docstring used to say "still RECONSTRUCTION",
    stale against its own module) and CORROBORATED on the wire by the D9 fix
    pass, 2026-09-24: in 7 of 7 hand-in batches carrying the 0x004C re-send,
    the description's two reward numerics equal [the batch's 0x00EE xp, the
    batch's 0x0140 gold] -- [100, 10], [250, 25], [1000, 10] and their repeats
    (studies/quests/FINDINGS.md §12.1).
    """
    slots = [slot_a] if slot_b is None else [slot_a, slot_b]
    for n in slots:
        if not isinstance(n, int) or not (0 <= n <= 0xFFFF - 0x100):
            raise ValueError(
                f"reward slot {n!r} does not fit a 0x100-biased u16 argument; "
                f"the range is 0..{0xFFFF - 0x100}")
    units = ([RUN_SEPARATOR] + list(REWARD_HEADER)
             + [RUN_SEPARATOR] + list(REWARD_SLOT_A)
             + [NUMERIC_ARG, 0x100 + slot_a])
    if slot_b is not None:
        units += ([RUN_SEPARATOR] + list(REWARD_SLOT_B)
                  + [NUMERIC_ARG, 0x100 + slot_b])
    return "".join(chr(u) for u in units)


# THE REWARD ITEM LINE -- RANGERPRE-S20 (QUESTFLOW-H4). A quest that hands
# over an item draws it as one more run after slot B, inside the same coded
# string. OBSERVED byte for byte on 21 strings across 5 captures (15 0x004C
# descriptions of quest 62, 6 0x0080 dialog lines; every one q62's shield,
# "Armor 4"), e.g. the turn-in screen 20260929T150923 :53880 726.6797 and that
# hand-in's 0x004C re-send at 727.4875:
#
#   0002 | 2AEF F690 D06E 4C53 | 010A <the item's name units> 0001 |
#          010B 0A86 010A 0A44 0001 0101 0104 0001
#
# -- ref 10735 (needs_key, like the three reward refs above) with two
# arguments: 0x010A introduces the item's NAME, and it is byte-identical to the
# name units of the 0x0161 that hand-in delivered (item 1607, 727.4875); 0x010B
# introduces its STAT LINE, template 2438 `%str1%: %num1%` fed label 2372 and a
# 0x100-biased numeric -- exactly the pair clientscan/itemmods.py records for
# the armour-rating modifier 572's handler, and the numeric (4) equals the
# delivered shield's own 572 argument (0xA3C80400; CORROBORATED, n = 1). What
# 0x010A / 0x010B MEAN is RECONSTRUCTION (str1 / str2 argument markers, by
# position); the words are OBSERVED.
#
# A SHIELD'S LINE ONLY. A weapon's line swaps the stat for template 2441 with
# label 2382 and a DAMAGE-TYPE string id (0x08DE at :53880 771.875, 0x08E4 at
# :55934 631.202), and the table from 587's argument to that id is NOT FOUND in
# this repo -- so a weapon reward is granted but not drawn (authsrv's
# quest_item_lines says so). A name-only item line (ref 10733, 20260819T132414
# :52606 q440, a type-30 item) exists too; no content row asks for it yet.
REWARD_ITEM_REF = (0x2AEF, 0xF690, 0xD06E, 0x4C53)  # ref 10735
ITEM_NAME_ARG = 0x010A        # precedes the name (RECONSTRUCTION: %str1%)
ITEM_STAT_ARG = 0x010B        # precedes the stat line (RECONSTRUCTION: %str2%)
STAT_LINE_TEMPLATE = 0x0A86   # id 2438, `%str1%: %num1%` (itemmods, 572)
ARMOUR_LABEL = 0x0A44         # id 2372, 572's label (drawn "Armor" on screen)
ARG_END = 0x0001              # closes an argument (below WORD_VALUE_BASE)

assert codedstr.decode_id([STAT_LINE_TEMPLATE]) == (2438, 1)
assert codedstr.decode_id([ARMOUR_LABEL]) == (2372, 1)
assert codedstr.decode_id(list(REWARD_ITEM_REF))[0] == 10735


def reward_item_run(name_units, armour):
    """One reward item's line, as a codec-ready str: 15 units plus the name.

    `name_units` are the item's own name code units -- the SAME units its
    0x0161 declares (agents.named_item sends the row's enc_name), because the
    tape's line and its delivered item agree on them. `armour` is its 572
    argument, the number drawn after the label. Refuses an empty name, a
    name unit that is a marker (< 0x100: a name must open with a string id,
    the rule coded_literal's TextApi.cpp:585 note is about) or past a u16,
    and an armour that does not survive the 0x100 bias in one u16."""
    name = [int(u) for u in name_units]
    if not name or not all(0x100 <= u <= 0xFFFF for u in name):
        raise ValueError(
            f"item name units {name!r} are not a coded string id (each "
            f"0x0100..0xFFFF, at least one)")
    if isinstance(armour, bool) or not isinstance(armour, int) \
            or not (0 <= armour <= 0xFFFF - 0x100):
        raise ValueError(
            f"armour {armour!r} does not fit a 0x100-biased u16 argument; "
            f"the range is 0..{0xFFFF - 0x100}")
    units = ([RUN_SEPARATOR] + list(REWARD_ITEM_REF)
             + [ITEM_NAME_ARG] + name + [ARG_END]
             + [ITEM_STAT_ARG, STAT_LINE_TEMPLATE,
                ITEM_NAME_ARG, ARMOUR_LABEL, ARG_END,
                NUMERIC_ARG, 0x100 + armour, ARG_END])
    return "".join(chr(u) for u in units)


def with_reward(text, slot_a, slot_b=None, framing="template",
                limit=FIELD_UNITS, items=()):
    """A description with its reward block appended, length-checked AFTER.

    The order matters and is the whole reason this is not two calls at the call
    site: the reward costs 19 units, so a description that passes a 122-unit
    check on its own can overflow once the block is on. Check the total.

    `items` (RANGERPRE-S20) is [(name units, armour)], one reward_item_run
    each, appended AFTER slot B -- quest 62's order on every string that
    carries one -- and counted in the same check.
    """
    # THE PARAGRAPH BREAK IS NOT COSMETIC, and the first run without it proved
    # so on screen: the pane read "...then return to me.Reward:" with our last
    # sentence and ArenaNet's reward header welded together. The reward run
    # opens with a bare 0x0002 SEPARATOR, which joins runs without starting a
    # line; 0x0102 is archive id 2, `\n[b]`, and is what actually breaks one.
    # MEASURED 2026-08-16, vault/captures/harness/20260816T103824.
    body = coded_literal(text, framing, limit=limit)
    # TWO BREAKS, not one. The owner, after the first hand-driven turn-in
    # (2026-09-12): "there should be 2 line breaks between the quest dialogue
    # and the reward" -- stock draws a BLANK LINE before `Reward:`, and one
    # 0x0102 draws a line end. Each break is its own run (separator + id 2),
    # never two ids in one run, which the codec would read as an argument.
    out = body + PARAGRAPH_BREAK + PARAGRAPH_BREAK + reward_run(slot_a, slot_b)
    for name_units, armour in items:
        out += reward_item_run(name_units, armour)
    if len(out) > limit:
        raise ValueError(
            f"{len(body)} units of text plus a {len(out) - len(body)}-unit "
            f"reward block is {len(out)}, over the {limit}-unit field. Shorten "
            f"the text.")
    return out


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
