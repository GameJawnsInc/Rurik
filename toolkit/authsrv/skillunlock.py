r"""The unlocked-skill bitmaps -- and there are TWO of them, on two scopes.

THE FIRST LINE OF THIS FILE USED TO READ "which skills the account may
equip", describing 0x00DB. That was wrong on both halves and is corrected
here rather than left for the next reader to trip over (SKILLS-LIB,
2026-09-15, studies/skills/FINDINGS.md §47):

  * 0x00DB UPDATE_UNLOCKED_SKILLS is the CHARACTER's learned set, not the
    account's. It fills charCtx[+0x2C]+0x710 and the Skills-and-Attributes
    panel enumerates it.
  * 0x001D PVP_UPDATE_UNLOCKED_SKILLS is the ACCOUNT's. It fills a separate
    AcctCliUnlock container at acctCtx[+0x28]+0x124 -- different context
    member, different displacement, its own event id -- and it is the one
    GmSkSlot bit-tests when the player DRAGS a skill into a bar slot
    (`unlockedSkills->BitTest(sourceSkillId)`, GmSkSlot.cpp:206). So the
    account set is what gates EQUIPPING, while §9 measured that neither set
    gates DRAWING.
  * Neither contains the other. OBSERVED, capture 20260817T231139: 21
    character ids against 19 account ids, two of the character's in no
    account set.

This module builds the bitmap for either scope; `resolve_library` is what
chooses, per half, between the persisted store and the --unlocks flag.

0x00DB (GAME_SMSG_UPDATE_UNLOCKED_SKILLS) carries 128 dwords of unlock bits, and
everything in this file exists because two of those bits were wrong for months in
ways that cost client sessions rather than assertions. Bit 0 set asserts `*skill`
in the client's own Skills panel the moment it opens; unlocking a row past the end
of the build's skill table asserts in ChCliSkill.cpp the same way; and unlocking
every row asserts `fileId` at File.cpp:367 on the icons. The three arms here --
`all`, `corpus`, and an explicit id list -- are the three answers, and
`refuse_skill_zero` is the startup guard that makes the first of them impossible
to ship unnoticed.

WHAT STAYED IN `authsrv.py`, because the comments below name them. `UNLOCKED` and
`UNLOCK_LABEL` are the module-level pair `main()` rebinds with `global` from
`build_unlock_bitmap`'s return, so they stay where the `global` can reach them;
`SKILLBAR`, `TEST_SKILLBAR` and `SKILLBAR_SLOTS` stay for the same reason (the bar
is rebindable from `--skills`, and `test_pools.py` patches `authsrv.SKILLBAR`
directly). `build_unlock_bitmap`'s `'bar'` arm therefore takes the bar as an
argument -- `authsrv.py`'s wrapper reads `SKILLBAR` at call time and passes it, so
a patched bar is seen.

`unlock_corpus_words` imports `pinned` and `skilltable` INSIDE the function on
purpose; that is the bare-machine rule and it is explained at the call site.

Standard library only, and no import of the server.
"""
import os
import sys

# 128 dwords = 4,096 bits, comfortably covering the 0..3442 id space this build
# actually has. Blanket-unlocking everything is deliberate: whether the client
# REFUSES to draw a bar skill that is not unlocked is NOT FOUND in every source
# we have, so we remove the variable rather than guess at it. The Go server does
# the same thing.
UNLOCK_WORDS = 128
UNLOCK_ALL_WORD = 0xFFFFFFFF
# Bit n of word n/32 means skill n is unlocked. UPSTREAM describes the layout;
# OpenTyria's own bit helpers are too broken to copy (its set_bit assigns instead
# of OR-ing, destroying 31 bits at a time), so this is written from the
# description rather than from its code.
# The message carries 4096 bits and build 38797's skill table holds 3443 rows,
# so 653 of those bits name skills that do not exist. Setting them CRASHES the
# client -- MEASURED, twice:
#
#     Assertion: *skill
#     P:\Code\Gw\Char\Cli\ChCliSkill.cpp(1022)
#
# The Skills and Attributes panel walks the unlocked ids and dereferences each
# one, so a bit past the end of the table is a null deref. The crash was first
# blamed on a corrupt texture we had planted in the same session; it reproduced
# with a clean archive and a stock binary, and disappeared the moment the bitmap
# was clamped. "all" therefore means all REAL skills, not all bits.
#
# MEASURED against build 38797. A different build has a different row count, and
# this number is not read from the binary -- if the client starts asserting in
# ChCliSkill.cpp again, re-derive it with repoint_skill.py --show.
SKILL_TABLE_ROWS = 3443


def unlock_all_words():
    """Every real skill id -- 1..SKILL_TABLE_ROWS-1. NOT id 0, and that is the
    whole of studies/profession's six-session crash.

    THE BIT THAT COST SIX CLIENT SESSIONS. This used to be
    `range(SKILL_TABLE_ROWS)`, starting at 0, so every 0x00DB this server ever
    sent carried bit 0 -- 242 of 242 sends across every capture in the vault,
    all beginning `db 00 80 00 ff ff ff ff`. Skill id 0 is not a skill.

    WHAT THE CLIENT DOES WITH IT (OBSERVED, build 38797, disassembly):
    0x00DB's handler routes the payload to a bitmap container at
    ctx[0x2c]+0x710, and the Skills-and-Attributes panel enumerates that
    container with a find-next-set-bit iterator (0x00821790). The iterator
    forms `id = (word << 5) + bit` and asserts the id is NON-ZERO --
    `*skill`, ChCliSkill.cpp:1022. Bit 0 set means the first id enumerated is
    0, so the panel asserts the instant it opens. Nothing is null: the assert
    is a ZERO VALUE test, which is why studies/profession/RUNS.md's "null
    lookup" reading was wrong for four documents.

    The walk is PROFESSION-BLIND -- no profession value branches anything
    between the panel's entry and the assert -- so this fired at every
    profession we ever tried, and the arc's "profession 3 opens" premise was
    an artifact of a misattributed crash. Six sessions were spent inventing
    and refuting profession stories for a crash with no profession in it.

    The explicit-list arm of build_unlock_bitmap has skipped id 0 since it was
    written (`if sid <= 0: continue`); only this arm did not. Pinned by
    test_agentlife.py's unlock-bitmap section, which reproduces the old
    version as a negative control.
    """
    words = [0] * UNLOCK_WORDS
    for sid in range(1, SKILL_TABLE_ROWS):
        words[sid // 32] |= 1 << (sid % 32)
    return words


def unlock_corpus_words():
    """Only the ids the client will draw a skill ICON for.

    RUNS.md §11: with all 3,442 rows unlocked the panel gets past the skill
    walk and then asserts `fileId` at File.cpp:367 loading an icon. Only
    **1,333** of those rows are player-usable skills (`equip_family == 1`,
    PvP flag clear -- the rule SKILL_EXTRACTION.md §4 established); the rest
    are weapon modifiers and other non-player definitions that share the
    table and have no skill icon.

    DERIVED AT RUN TIME FROM THE OWNER'S OWN CLIENT, never committed. That is
    the pattern `mapbuild.py` already proves for FINDINGS 14's constants: the
    extractor is in this repo (`skilltable.py`), the build is recorded in the
    label this returns, and no ArenaNet bytes enter the tree. Reading it costs
    one pass over the table at startup.

    Imported INSIDE the function on purpose: the default `--unlocks all` path
    must keep working on a machine with no vault and no client, which is the
    bare-machine rule the fixed-byte-pattern tools live under.
    """
    sys.path.insert(0, os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "clientscan"))
    import pinned                                              # noqa: E402
    import skilltable                                          # noqa: E402

    try:
        path, why = pinned.find()
    except SystemExit as ex:
        raise SystemExit(
            f"{ex}\n"
            f"  --unlocks corpus derives the player-usable skill ids from the "
            f"client itself, so it needs one to read.\n"
            f"  With no client: `--unlocks bar` sends exactly the --skills ids "
            f"and is what the panel was first opened with.\n"
            f"  `--unlocks all` is REFUSED in spirit but not in code -- it "
            f"asserts fileId (File.cpp:367) the moment the Skills panel opens.")
    data = open(path, "rb").read()
    base, count, _score = skilltable.locate_table(data)
    rows = [skilltable.parse_record(data, base, i) for i in range(count)]
    ids = [i for i in skilltable.player_corpus(rows) if i > 0]
    words = [0] * UNLOCK_WORDS
    for sid in ids:
        if sid < UNLOCK_WORDS * 32:
            words[sid // 32] |= 1 << (sid % 32)
    return words, (f"corpus ({len(ids)} player-usable of {count} rows, "
                   f"build {pinned.BUILD}, {why})")


def refuse_skill_zero(words, spec):
    """Bit 0 set means the client asserts the moment the Skills panel opens.

    A HARD REFUSAL AT STARTUP, because the alternative is a crash twelve
    seconds into a client session that costs a launch, a login and a map load
    to observe -- and it has already cost seven of them (RUNS.md §10). The
    client's panel enumerates this bitmap with a find-next-set-bit iterator,
    forms `id = (word << 5) + bit`, and asserts the id NON-ZERO at
    ChCliSkill.cpp:1022. Skill id 0 is not a skill, so bit 0 is never
    legitimate on this wire.

    It refuses rather than silently clearing the bit: a server that quietly
    repaired its own payload would hide a regression in whatever produced it,
    and the point is to make the next one impossible to ship unnoticed.
    """
    if words and words[0] & 1:
        raise SystemExit(
            f"--unlocks {spec!r} produced a bitmap with BIT 0 SET (skill id 0). "
            f"Refusing to send it: the client's Skills panel enumerates this "
            f"bitmap and asserts `*skill` at ChCliSkill.cpp:1022 on a zero id, "
            f"so the session would die the moment the panel opens. Skill ids "
            f"start at 1. See studies/profession/RUNS.md §10.")
    return words


def words_from_ids(ids, why="ids"):
    """An explicit id list -> the guarded 128-word bitmap.

    THE SINGLE PLACE the two client-killing rules are enforced, which is why
    it is a function rather than a loop inside `build_unlock_bitmap`: the
    persisted skill library (charstore's account `unlocked_skills` and
    per-character `learned_skills`) has to pass the SAME gate the --unlocks
    flag passes, and a second copy of `sid >= SKILL_TABLE_ROWS` is a second
    copy to forget to update when the build moves.

    Ids <= 0 are SKIPPED rather than refused, preserving what the explicit
    arm has always done; `refuse_skill_zero` is still the backstop, and
    charstore refuses a stored 0 at load as well.
    """
    words = [0] * UNLOCK_WORDS
    for sid in ids:
        sid = int(sid)
        if sid <= 0:
            continue
        w, b = divmod(sid, 32)
        if w >= UNLOCK_WORDS:
            raise SystemExit(f"skill id {sid} needs word {w}, past the "
                             f"{UNLOCK_WORDS}-word message ({why})")
        if sid >= SKILL_TABLE_ROWS:
            raise SystemExit(
                f"skill id {sid} is past the end of this build's skill table "
                f"({SKILL_TABLE_ROWS} rows). Unlocking it asserts in the "
                f"client's ChCliSkill.cpp the moment the Skills panel opens "
                f"({why}).")
        words[w] |= 1 << b
    return refuse_skill_zero(words, why)


def ids_from_words(words):
    """The inverse of words_from_ids: a bitmap back to sorted skill ids.

    Exists for the persisted library's SEED path. When the store holds no
    list yet, the server has to hand the store the set that is currently in
    force -- which it holds as a bitmap, not as ids -- so that the first
    in-game unlock records the whole library rather than truncating it to
    one skill. See charstore.Store.unlock_account_skill.
    """
    out = []
    for wi, w in enumerate(words):
        w = int(w)
        b = 0
        while w:
            if w & 1:
                out.append(wi * 32 + b)
            w >>= 1
            b += 1
    return out


def resolve_library(store, uuid_hex, fallback_words, fallback_label):
    """The two libraries the instance-load burst sends, as wire bitmaps.

    Returns (account_words, account_label, character_words, character_label).

    THE TWO SETS ARE RETAIL'S, and this function exists so the choice between
    store and flag is testable without standing up a connection -- it used to
    be inline in handle_request_game_instance, where nothing could reach it.

      * account -> 0x001D PVP_UPDATE_UNLOCKED_SKILLS. OBSERVED byte-identical
        on every connection of one account across the live corpus, whichever
        character and whichever map.
      * character -> 0x00DB UPDATE_UNLOCKED_SKILLS. OBSERVED on capture
        20260817T231139 as 21 ids where the same account's 0x001D carried 19,
        two of them (364, 384) in no account set. Neither contains the other,
        which is why one bitmap cannot serve both and why this returns two.

    `store` is a charstore.Store or None; it is duck-typed on purpose so this
    leaf does not import a sibling. Each half falls back INDEPENDENTLY: an
    absent list means the operator has not authored that half and the
    --unlocks flag still answers for it, which is what keeps every run that
    predates the store byte-identical. An EMPTY list is an authored answer
    and is sent as an empty bitmap.
    """
    acct_ids = None if store is None else store.account_unlocked_skills()
    char_ids = (None if store is None
                else store.character_learned_skills(uuid_hex))
    if acct_ids is None:
        acct_words, acct_label = fallback_words, f"{fallback_label}, --unlocks"
    else:
        acct_words = words_from_ids(acct_ids, "account unlocked_skills")
        acct_label = f"{len(acct_ids)} stored, account-wide"
    if char_ids is None:
        char_words, char_label = fallback_words, f"{fallback_label}, --unlocks"
    else:
        char_words = words_from_ids(char_ids, "character learned_skills")
        char_label = f"{len(char_ids)} stored, this character"
    return acct_words, acct_label, char_words, char_label


def build_unlock_bitmap(spec, SKILLBAR):
    """--unlocks: 'all', 'none', 'bar', or an explicit comma-separated id list."""
    if spec == "corpus":
        words, label = unlock_corpus_words()
        return refuse_skill_zero(words, spec), label
    if spec == "all":
        return (refuse_skill_zero(unlock_all_words(), spec),
                f"all ({SKILL_TABLE_ROWS - 1} real skills, ids 1..{SKILL_TABLE_ROWS - 1})")
    if spec == "none":
        return [0] * UNLOCK_WORDS, "none"
    ids = SKILLBAR if spec == "bar" else [int(s, 0) for s in spec.split(",")
                                          if s.strip() != ""]
    return words_from_ids(ids, spec), ",".join(str(i) for i in ids)
