r"""A hero's usable skill library, and what may be dropped into a bar slot.

THE UNION IS THE FINDING, and it was measured rather than taken from GWW.
Capture `20260914T005758`, connection :51659, carries the whole thing on one
frame: `0x0073 HERO_INFO` declares Koss's own skills as
`[322, 382, 348, 1, 385, 2]`, and the `0x00DA` addressed to his agent (117)
carries `[322, 382, 348, 1, 385, 346, 0, 2]`. The one id on the bar that is
NOT his own is **346**, and 346 is:

  * IN the account's `0x001D` set on that same connection, and
  * NOT in the character's `0x00DB` set.

So a hero's usable library is **(the hero's own skills) UNION (the ACCOUNT's
unlocks)** -- and specifically NOT the character's learned set, which is the
plausible wrong answer and the one a reader would reach for, since the hero
belongs to the character. The character's learned set is what the PLAYER's own
bar draws on; the hero's is the account's.

WHY THE FIRST PASS GOT A DIFFERENT ANSWER, recorded because the wrong answer
looked stronger than the right one. A first census joined bars to heroes by
"shares at least one skill id", which on the eight connections of
`20260817T231139` labelled the PLAYER's bar as a hero's and reported the two
extras as coming from the CHARACTER set -- agreeing with itself on all eight.
The strict join (HERO_INFO's list must be a SUBSET of the bar) identifies a
hero's bar on three connections only, all via `0x0072 HERO_ACTIVATE`, and
gives the union above. Eight consistent readings of a bad join are not eight
witnesses.

Standard library only; no import of the server, no content, no sockets, so the
whole of it is exercisable with no vault and no client.
"""

# 0x00DA's array is eight wide and the client asserts
# `hotKey < arrsize(hotKeyState->hotKey)` (ChCliSkill.cpp:681) past it.
BAR_SLOTS = 8


def hero_library(own_skills, account_unlocked):
    """The set of ids this hero may equip: its own, plus the account's.

    Both arguments may be None, and they mean different things:
      * `own_skills` None -- this hero has no authored skill list, so its
        library is the account's alone.
      * `account_unlocked` None -- the account library is not authored and the
        server's --unlocks flag is answering for it. The caller passes the ids
        that flag is actually sending, NOT None, when it wants them counted;
        None here means "nothing known", not "everything".
    """
    return set(int(s) for s in (own_skills or ())) | \
        set(int(s) for s in (account_unlocked or ()))


def refuse_bar_slot(slot, skill_id, library):
    """Why this slot write must not be honoured, or None if it may be.

    A REASON STRING, NEVER A BOOL, and callers print it -- the same discipline
    `attribspend.refuse_increase` follows. The client has ALREADY drawn the
    drag on its own bar by the time this is asked, so a silent drop leaves the
    two of us disagreeing with the client believing itself. Every caller must
    answer, refusal or not.
    """
    slot = int(slot)
    if not 0 <= slot < BAR_SLOTS:
        return (f"slot {slot} is outside 0..{BAR_SLOTS - 1}; the client's own "
                f"guard is `hotKey < arrsize(hotKeyState->hotKey)` "
                f"(ChCliSkill.cpp:681)")
    skill_id = int(skill_id)
    if skill_id == 0:
        # Clearing a slot is legal and is how retail spells an empty one.
        return None
    if skill_id < 0:
        return f"skill id {skill_id} is negative; 0 clears a slot, ids start at 1"
    if library is not None and skill_id not in library:
        return (f"skill {skill_id} is not in this body's library "
                f"({len(library)} id(s)) -- neither its own skills nor the "
                f"account's unlocks. GmSkSlot bit-tests the ACCOUNT container "
                f"before an equip (`unlockedSkills->BitTest(sourceSkillId)`, "
                f"GmSkSlot.cpp:206), so honouring this would put the client "
                f"one drag away from that assert")
    return None


def apply_bar_slot(bar, slot, skill_id):
    """The bar after writing one slot, padded to eight. Pure; no validation.

    Returns a NEW list -- callers hold the old one to report the change, and a
    mutation in place made the before/after log print the same value twice.
    """
    out = [int(s) for s in (bar or ())][:BAR_SLOTS]
    out += [0] * (BAR_SLOTS - len(out))
    out[int(slot)] = int(skill_id)
    return out


def refuse_bar_swap(bar, source_skill, target_skill):
    """Why this swap must not be honoured, or None if it may be.

    0x005E [agent, sourceSkill, sourceCopy, targetSkill, targetCopy] --
    SKILL-KEYED at both ends (RUN-HEROLIB-C), field 1 the skill the operator
    PICKED UP and field 3 the skill in the slot it was DROPPED ON
    (RUN-HEROLIB-D: two pre-registered drags on the two end slots gave
    [281, 0, 256, 0] then [256, 0, 281, 0], exact mirror images, with the
    outcome confirmed on screen before the second). A swap only rearranges
    skills already on the bar, so the library is not consulted: both ids
    passed refuse_bar_slot on their way in.
    """
    bar = [int(s) for s in (bar or ())]
    src, tgt = int(source_skill), int(target_skill)
    if src == tgt:
        return (f"source and target are the same skill {src}; the client's "
                f"own guard is `targetSkill != sourceSkill` "
                f"(ChCliSkill.cpp:515)")
    for label, sid in (("source", src), ("target", tgt)):
        if sid <= 0:
            return f"{label} skill id {sid} is not a skill; a swap names two"
        n = bar.count(sid)
        if n == 0:
            return (f"{label} skill {sid} is not on this bar {bar}; a swap "
                    f"exchanges two slots that are both occupied")
        if n > 1:
            return (f"{label} skill {sid} sits in {n} slots of {bar}; the "
                    f"server never holds one skill twice, so this bar is "
                    f"already wrong")
    return None


def apply_bar_swap(bar, source_skill, target_skill):
    """The bar after exchanging the two skills' slots. Pure; no validation.

    Returns a NEW list, padded to eight, like apply_bar_slot.
    """
    out = [int(s) for s in (bar or ())][:BAR_SLOTS]
    out += [0] * (BAR_SLOTS - len(out))
    i, j = out.index(int(source_skill)), out.index(int(target_skill))
    out[i], out[j] = out[j], out[i]
    return out


def duplicate_of(bar, slot, skill_id):
    """Which OTHER slot already holds this skill, or None.

    The client's own equip guard is `targetSkill != sourceSkill`
    (ChCliSkill.cpp:515), and retail's UI SWAPS rather than duplicating when
    you drag a skill onto a bar that already has it. What this returns is the
    fact; what to do about it is the caller's, and it is recorded as UNVERIFIED
    in studies/heroes/FINDINGS.md rather than guessed at here -- the corpus has
    no capture of a duplicate drag.
    """
    if not skill_id:
        return None
    for i, s in enumerate(bar or ()):
        if s == int(skill_id) and i != int(slot):
            return i
    return None
