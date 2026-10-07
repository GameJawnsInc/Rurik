r"""The primary attributes' passive rules: what a rank buys without a skill.

studies/skills/FINDINGS.md section 66 (SKILLS-EX) is the record; this file is
the arithmetic and the scope predicates, pure, so the press path, the hostile
and hero cast paths and the test all read ONE copy.

WHERE THE RULES COME FROM -- three layers, labelled per studies/method:

  * THE CLIENT'S OWN DESCRIPTION of each primary attribute (OBSERVED, build
    38797). `attribtable.py` reads the `s_attrib` row (+0x0C is the
    description string id) and `textrec` resolves it from the owner's own
    archive. What is committed is the ID and a hand-typed NUMBER, never the
    sentence (CLAUDE.md, the provenance gate: measurement, not expression);
    `test_attribpassive.py` resolves each id at run time and checks the number
    we typed occurs in it, so a number that drifts from the client's text
    reddens there. `PRIMARY_DESCRIPTION_IDS` below is the ten.
  * THE WIRE (OBSERVED, n small): the only primary with a paid spend on tape
    at a nonzero rank is Expertise -- six property-62 spends by the Ranger at
    Expertise 1 on 20260914T005758 :56011 (SKILLS-EX1). That is what decides
    the ROUNDING, which the description does not state.
  * RECONSTRUCTION: everything the two above do not reach -- named at the
    function that assumes it.

Standard library only, and it imports nothing from this directory: a leaf
never imports its origin (CLAUDE.md "Leaf modules"), so the rank, the
Weakness cut and the skill row are the CALLER's to read and pass in.
"""

# ---- the ten primaries' description ids (OBSERVED, s_attrib +0x0C, 38797) --
#
# attribute id -> the client's description string id. The ids are a
# measurement; the text is resolved at run time and never committed. A newer
# build may renumber the strings -- `test_attribpassive` re-reads the table
# from the pinned exe when one is present, so drift reddens rather than lies.
PRIMARY_DESCRIPTION_IDS = {
    0: 2079,        # Fast Casting (Mesmer)
    6: 2093,        # Soul Reaping (Necromancer)
    12: 2099,       # Energy Storage (Elementalist)
    16: 2105,       # Divine Favor (Monk)
    17: 2113,       # Strength (Warrior)
    23: 2131,       # Expertise (Ranger)
    35: 2137,       # Critical Strikes (Assassin)
    36: 2147,       # Spawning Power (Ritualist)
    40: 36916,      # Leadership (Paragon)
    44: 36922,      # Mysticism (Dervish)
}
# The numbers this repo types for each, which the description must CONTAIN as
# a numeral (the test's check -- a typed number the client's own sentence does
# not carry is a recalled number, and that is what this table exists to stop).
# Paraphrase of what each number means lives in the study, section 66.2.
PRIMARY_DESCRIPTION_NUMERALS = {
    0: ("3",),                  # PvE: Mesmer-spell recharge -3 % a rank
    6: ("1", "3", "15"),        # +1 energy a rank, at most 3 times per 15 s
    12: ("3",),                 # +3 maximum energy a rank
    16: ("3.2",),               # +3.2 health a rank on a Monk spell's ally
    17: ("1",),                 # 1 % armour penetration a rank (attack skills)
    23: ("4",),                 # -4 % energy cost a rank (the scope below)
    35: ("1", "3", "8", "13"),  # +1 % crit a rank; 1/2/3 energy at 3/8/13
    36: ("4",),                 # +4 % creature health / weapon-spell duration
    40: ("2",),                 # +2 energy an ally, cap 1 per 2 ranks
    44: ("4", "1"),             # -4 % Dervish enchantment cost; PvE +1 armour
}

ATTACK_TYPE_CODE = 14           # s_skill +0x0C; authsrv.ATTACK_TYPE_CODE's value

# ---- EXPERTISE (attribute 23) ----------------------------------------------
#
# THE RULE, two halves with different labels:
#   * the SLOPE, 4 % of the cost a rank, and the SCOPE sentence: OBSERVED, the
#     client's description 2131 (build 38797). The description states no
#     rounding.
#   * the ROUNDING: OBSERVED on the wire, n = 6, one connection
#     (20260914T005758 :56011, the Ranger at Expertise 1): 392 (15) paid 14,
#     394 (10) paid 10 twice, 455 (10) paid 10, 433 (5) and 446 (5) paid 5.
#     ROUND-to-nearest predicts 6 of 6. FLOOR (what test_pools' comment
#     carried as WIKI, "floored") predicts 1 of 6 -- it charges 9 for a 10
#     and 4 for a 5 -- and CEIL (equivalently "floor the discount") predicts
#     5 of 6, missing 392. Only 392 shows a discount at all; the other five
#     are what refute floor. Ties cannot occur: cost x (25 - rank) / 25 has
#     an integer numerator, so it never lands on a half.
#
# THE SCOPE SHIPPED IS NARROWER THAN THE CLIENT'S SENTENCE, on purpose. 2131
# names attacks, Rituals, touch skills and Ranger skills. Attacks are type 14
# (the client's own namer, studies/skills 35) and Ranger skills are profession
# 2 -- both columns the server already reads. "Rituals" and "touch skills" are
# OPEN: a Ranger's nature rituals are Ranger skills and are covered, but a
# Ritualist binding ritual's type and whether the table's `touch_range` bit
# (DESKWORK-D8, an UPSTREAM-named flag) is what the sentence calls a touch
# skill are reads not done. Nothing on tape witnesses the boundary either way:
# no out-of-scope paid skill by an agent at Expertise > 0 exists in the
# corpus (section 66.1), so a wrong scope would be invisible to the tape and
# the scope rests on the description alone.
EXPERTISE_ATTRIBUTE = 23
EXPERTISE_DESCRIPTION_ID = 2131
EXPERTISE_PERCENT_PER_RANK = 4
EXPERTISE_PROFESSION = 2        # Ranger


def expertise_applies(row):
    """Does Expertise cheapen this skill? `row` is the skill's `skills` row
    (type_code, profession). True for an attack skill or a Ranger skill; False
    for anything else, including a row that does not say -- a skill whose type
    we cannot read is charged its table cost, which is what every cast cost
    before this rule existed."""
    if not row:
        return False
    try:
        type_code = int(row.get("type_code", -1))
        profession = int(row.get("profession", -1))
    except (TypeError, ValueError):
        return False
    return type_code == ATTACK_TYPE_CODE or profession == EXPERTISE_PROFESSION


def expertise_cost(base, rank):
    """`base` energy at Expertise `rank`: round(base x (1 - 0.04 x rank)),
    never below 0.

    Integer arithmetic, half-up -- and no half is reachable (the module note).
    A rank of 0 or less, or a base of 0 or less, returns `base` unchanged: a
    free skill stays free and a negative rank (none exists; Weakness floors at
    0) is not a surcharge. A rank of 25 or more prices everything at 0, which
    no character reaches (a rank-12 attribute with every bonus is in the
    teens) and which the caller treats as FREE: no property 62, no gate."""
    base, rank = int(base), int(rank or 0)
    if base <= 0 or rank <= 0:
        return base
    keep = 100 - EXPERTISE_PERCENT_PER_RANK * rank
    if keep <= 0:
        return 0
    return (2 * base * keep + 100) // 200


# ---- DIVINE FAVOR (attribute 16) -------------------------------------------
#
# THE RULE, and where each half comes from (studies/skills 66.4):
#   * the SLOPE, 3.2 health a rank, and "allies ... whenever you cast Monk
#     spells on them": OBSERVED, the client's description 2105 (38797). No
#     rounding is stated.
#   * the SHAPE, OBSERVED over 28 casters on three tapes: its OWN property-55
#     word [55, recipient, caster, bonus / max] in the cast's completion batch,
#     AFTER the spell's own heal word on the same recipient whenever there is
#     one (147 of 147 where the pool is unambiguous), and alone for a spell
#     with no heal of its own.
#   * the ROUNDING, from the values alone: the constants on tape are 3, 42 and
#     58 (the last via Healing Touch's 116). round(3.2 r) reaches all three;
#     floor(3.2 r) never makes 42 or 58 and ceil(3.2 r) never makes 3. The
#     casters' ranks (1, 13, 18) are then INFERRED -- none is on the wire.
#   * the SCOPE, OBSERVED per skill, generalised by RECONSTRUCTION: a Monk spell
#     or enchantment cast on an ally (the client's target byte 3 or 4) carries
#     it 360 of 364 (the other 4 batches carry no property 55 at all); so does
#     a self-cast enchantment (type 6, byte 0: 271, 22 of 23); a hex on a foe
#     (251, 14) and a resurrection (314, 2) never do. Heal Area (a spell,
#     byte 0) was seen once without it from a caster whose rank no tape shows:
#     the byte-0 SPELL exclusion is RECONSTRUCTION, n = 1. A signet is not a
#     spell (the description's word); no Monk signet completion is on tape.
#   * HEALING TOUCH (313) DOUBLES the ROUNDED bonus: 84 = 2 x 42 on the
#     level-20 Monks, 116 = 2 x 58 on a town caster; round(6.4 r) makes neither.
#     OBSERVED, two kinds of caster.
DIVINE_FAVOR_ATTRIBUTE = 16
DIVINE_FAVOR_DESCRIPTION_ID = 2105
DIVINE_FAVOR_TENTHS_PER_RANK = 32       # 3.2 health a rank, in tenths
DIVINE_FAVOR_PROFESSION = 3             # Monk
DIVINE_FAVOR_SPELL_TYPES = (5, 6)       # Spell, Enchantment Spell (studies/skills 35)
DIVINE_FAVOR_ALLY_TARGETS = (3, 4)      # the client's target byte: ally, other ally
DIVINE_FAVOR_SELF_ENCHANTMENT = (6, 0)  # (type, target byte): an enchantment on yourself
DIVINE_FAVOR_MULTIPLIER = {313: 2}      # Healing Touch (OBSERVED, above)


def divine_favor_applies(row):
    """Does casting this skill give its recipient the Divine Favor heal? `row`
    is the skill's `skills` row (profession, type_code, target). False for a
    row that cannot say."""
    if not row:
        return False
    try:
        profession = int(row.get("profession", -1))
        type_code = int(row.get("type_code", -1))
        target = int(row.get("target", -1))
    except (TypeError, ValueError):
        return False
    if profession != DIVINE_FAVOR_PROFESSION or type_code not in DIVINE_FAVOR_SPELL_TYPES:
        return False
    return (target in DIVINE_FAVOR_ALLY_TARGETS
            or (type_code, target) == DIVINE_FAVOR_SELF_ENCHANTMENT)


def divine_favor_bonus(rank, skill_id=None):
    """The heal at Divine Favor `rank`: round(3.2 x rank), integer arithmetic
    (32 r is even, so its last digit is never 5 and no half is reachable),
    times the skill's multiplier (Healing Touch's 2). 0 at rank 0 or below."""
    rank = int(rank or 0)
    if rank <= 0:
        return 0
    bonus = (DIVINE_FAVOR_TENTHS_PER_RANK * rank + 5) // 10
    return bonus * DIVINE_FAVOR_MULTIPLIER.get(int(skill_id) if skill_id is not None else -1, 1)
