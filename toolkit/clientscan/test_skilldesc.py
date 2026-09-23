r"""The skill description templates: which %strN% is which field, and the referee.

    python toolkit/clientscan/test_skilldesc.py

studies/skills/FINDINGS.md 54 (SKILLS-DT). Three claims, each with an arm that
reddens if it is wrong:

  * THE MAPPING. %str1% is the SCALE slot, %str2% the BONUS slot, %str3% the
    DURATION slot -- not the natural order. Under it, of 2,357 slot occurrences
    in build 38797's 1,333-row player corpus, ZERO number an empty field; the
    known-bad arm (`skilldesc.shifted`, either shift) puts 700+ on empty fields
    and a dozen on duration sentinels. Six controls pinned to the wiki by
    `content/world.toml` or FINDINGS 4 land on the field the wiki named.
  * THE LABELS. Our own enum, from the words around a slot. Every slot in the
    corpus gets a label (0 UNPARSED); every comparable hand label agrees with
    the parse -- the one disagreement there was (Battle Rage's `scale_means =
    "Duration"` on a flat 33 that is its movement speed) was a real one and
    world.toml dropped it on 2026-09-23, with Hamstring's label moved to the
    slot the template numbers. The SERVED tier is per (label, INDEX,
    type_code), read off the consumer sites: 341 of 1,265 slot-bearing rows,
    27 % -- the route's half-mark FAILS.
  * THE CENSUS (DESKWORK-Q7). What the server resolves today: 54 modelled, 419
    episodes (+45 refused durations), 815 nothing.

  * THE LABEL TIER (SKILLS-LT, DESKWORK-D4 step 4, 2026-09-23). "Plain" is
    SERVED with none of IF / WHEN / FOR_EACH / WHILE / EXCEPTION / CHANCE: 131
    of the 341. The gate (`build_label_row`) excludes what the server would
    OVER-apply -- a hand row's id, a duration-only row, a percent slot under a
    non-percent label, a condition an episode inflicts later, a pet attack, a
    chain requirement on a non-attack, an at-cast damage or condition whose
    target byte is not a foe's, a heal byte 1 would hand to the selected agent,
    a recipient class the server has no object for (spirits, a corpse,
    fleshiness), a self-targeted heal on a class of recipients -- and marks
    what it would UNDER-apply (area wording, an over-time duration, a dropped
    clause, a bit-clear or indeterminate slot). 47 rows ship on build 38797
    (59 before the fix pass of the same day); every exclusion is counted by
    reason. The overlay is deterministic, carries client-table provenance per
    row and no string outside OVERLAY_VOCABULARY; the known-bad arms force a
    conditional row, a percent slot, an unmodelled class and a chain
    requirement through and the checker names each.

Sections 1 and 1b run on a bare machine; sections 2 and 3 need the pinned exe
and Gw.dat and declare one skip without them. Nothing here quotes a template.
"""
import collections
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))
import checks       # noqa: E402
import effects      # noqa: E402
import skilldesc    # noqa: E402
import skilltable   # noqa: E402
import content as _content   # noqa: E402  (the label marks' closed set, SKILLS-LU fix pass)
from skilldesc import Label, SLOT_FIELD, shifted, referee_slot   # noqa: E402

# Floor from the BARE run, MEASURED with RURIK_VAULT at an empty directory:
# 61 checks, 1 declared skip ("2. the corpus"), rc=0 -- the mandatory core per
# checks.py (2026-09-23, SKILLS-LT: +21 in section 1b, the label tier's gate on
# synthetic rows; 40 on 2026-09-22). A whole green run with the vault is 124.
LEDGER = checks.Ledger("skill description templates", floor=77)   # 77 from the bare run of 2026-09-23 (SKILLS-LU: +5 in 1b; the fix pass before it: +11); 146 with the vault
check = checks.adopt(LEDGER)


def rec(args=0, d=(0, 0), s=(0, 0), b=(0, 0), type_code=5):
    return {"skill_arguments": args, "duration0": d[0], "duration15": d[1],
            "scale0": s[0], "scale15": s[1], "bonus_scale0": b[0],
            "bonus_scale15": b[1], "type_code": type_code}


# ---------------------------------------------------------------- section 1
print("== 1. the mapping, the referee and the labels, on a bare machine ==")
check(SLOT_FIELD == {1: "scale", 2: "bonus_scale", 3: "duration"},
      "str1 -> scale, str2 -> bonus_scale, str3 -> duration (MEASURED, FINDINGS 54)")
check(shifted() == {1: "bonus_scale", 2: "duration", 3: "scale"},
      "the known-bad arm moves every index one field along")
check(shifted(by=2) == {1: "duration", 2: "scale", 3: "bonus_scale"},
      "and by two it is the 'natural' order the measurement refutes")

pa = rec(args=2, s=(10, 40))                       # Power Attack's shape
sa = rec(args=4, b=(5, 25))                        # Sever Artery's shape
check(referee_slot(1, pa) == ("AGREE_PROGRESSION", "scale", 10, 40),
      "bit set, endpoints differ: a progression on the scale slot")
check(referee_slot(2, sa) == ("AGREE_PROGRESSION", "bonus_scale", 5, 25),
      "bonus only: str2 is the progression")
check(referee_slot(1, sa)[0] == "CONFLICT_EMPTY",
      "a slot on a bit-clear 0/0 field is a CONFLICT, never a value")
check(referee_slot(1, rec(args=2, s=(0, 0)))[0] == "CONFLICT_EMPTY",
      "and so is a slot on a bit-SET 0/0 field -- the bit does not conjure a number "
      "(the first version graded it AGREE_FLAT, hiding 33 landings per known-bad arm)")
check(referee_slot(1, rec(s=(25, 25)))[0] == "AGREE_FLAT",
      "bit clear, equal, non-zero: the flat constant (Rush's 25)")
check(referee_slot(1, rec(s=(10, 18)))[0] == "INDETERMINATE",
      "bit clear, endpoints differ: INDETERMINATE, not fitted (FINDINGS 12)")
check(referee_slot(3, rec(args=7, d=(20, 20)))[0] == "AGREE_FLAT",
      "bit set with equal endpoints prints without scaling (Defy Pain's 20)")
check(referee_slot(3, rec(d=(0x20000, 0x20000)))[0] == "CONFLICT_SENTINEL",
      "a duration sentinel reached by a slot is a conflict")
check(referee_slot(4, pa)[0] == "CONFLICT_INDEX", "an index outside 1..3 is a conflict")
check(referee_slot(1, pa, shifted())[0] == "CONFLICT_EMPTY",
      "the known-bad arm sends Power Attack's damage to its empty bonus slot")

norm = skilldesc.normalise('<c=@SkillDull>x</c> second[s] 25%% [pl:"hexes"] %str1%')
check(norm == "x seconds 25% hexes %str1%", "normalise strips the markup and keeps %strN%", repr(norm))
check(skilldesc.normalise("%str1%%% a") == "%str1%% a" and skilldesc.normalise("%str1%% a") == "%str1%% a",
      "a slot's closing % never pairs with the escape after it: the slotted percent survives "
      "under either spelling (the corpus spells it %strN%%%, 250 times)",
      (skilldesc.normalise("%str1%%% a"), skilldesc.normalise("%str1%% a")))
check("LITERAL_PERCENT" in skilldesc.row_flags("a 25% stride") and not skilldesc.row_flags("%str1% and %str2%"),
      "LITERAL_PERCENT is a digit-then-% the text prints, and a bare slot raises no flag "
      "(the first pattern matched the 1% inside %str1% on 1,278 rows)")

C = skilldesc.classify
cases = [
    (("you strike for +", " damage."), (Label.PLUS_DAMAGE, "")),
    (("struck for ", " fire damage"), (Label.FIRE_DAMAGE, "")),
    (("deals +", " lightning damage"), (Label.LIGHTNING_DAMAGE, "plus")),
    (("takes ", " damage"), (Label.DAMAGE, "")),
    (("begins bleeding for ", " seconds"), (Label.CONDITION_DURATION, "Bleeding")),
    (("for ", " seconds, the caster hums a tune"), (Label.DURATION, "")),
    (("you move ", "% faster"), (Label.MOVE_SPEED_UP, "")),
    (("you attack ", "% faster"), (Label.ATTACK_SPEED_UP, "")),
    (("target foe attacks ", "% slower"), (Label.ATTACK_SPEED_DOWN, "")),
    (("you are healed for ", "."), (Label.HEAL, "")),
    (("you gain ", " health"), (Label.HEAL, "")),
    (("you lose ", " health"), (Label.HEALTH, "loss")),
    (("you gain ", " energy"), (Label.ENERGY, "")),
    (("target foe loses ", " energy"), (Label.ENERGY_LOSS, "")),
    (("spells cost ", " less energy"), (Label.ENERGY, "cost")),
    (("suffers -", " health degeneration"), (Label.HEALTH_DEGEN, "")),
    (("you have +", " health regeneration"), (Label.HEALTH_REGEN, "")),
    (("a level ", " spirit"), (Label.LEVEL, "")),
    (("up to ", " foes"), (Label.COUNT, "foes")),
    (("this attack has ", "% armor penetration"), (Label.ARMOR_PENETRATION, "")),
    (("you have a ", "% chance to block"), (Label.BLOCK_CHANCE, "")),
    # the precision cases (ENG-2 / D4-R8): a percent names the thing it is a
    # percent OF, or it is not that label
    (("your attack skills recharge ", "% faster"), (Label.RATE_PERCENT, "recharge")),
    (("hexes on you expire ", "% faster"), (Label.RATE_PERCENT, "expire")),
    (("you gain adrenaline ", "% faster"), (Label.RATE_PERCENT, "adrenaline")),
    (("your allies run ", "% faster"), (Label.MOVE_SPEED_UP, "")),
    (("that foe moves ", "% slower"), (Label.MOVE_SPEED_DOWN, "")),
    (("you steal ", "% of that foe's energy"), (Label.ENERGY_PERCENT, "")),
    (("adjacent foes take ", "% of that damage"), (Label.DAMAGE_PERCENT, "")),
    (("the target is left with ", "% of its maximum health"), (Label.HEALTH_PERCENT, "")),
    (("the hex lasts ", "% longer"), (Label.PERCENT, "duration")),
    (("skills are disabled for ", " seconds"), (Label.DISABLE_DURATION, "")),
    (("this spirit dies after ", " seconds"), (Label.LIFETIME, "")),
    (("the wearer's maximum health is raised by ", "."), (Label.MAX_HEALTH, "")),
    (("you have an additional ", " health"), (Label.MAX_HEALTH, "")),
    (("you take -", " less damage"), (Label.DAMAGE_REDUCTION, "")),
    # the sentence rule: the condition named at the head of the sentence, the
    # slot at its tail (Dismember's shape)
    (("inflict a deep wound, lowering maximum health by 20% for ", " seconds"),
     (Label.CONDITION_DURATION, "Deep Wound")),
    # its guard: the verb before "for" is the thing timed
    (("burning foes are hexed for ", " seconds"), (Label.DURATION, "")),
    # and its bound: a condition in the PREVIOUS sentence is not this slot's
    (("target foe is crippled. for ", " seconds, you move"), (Label.DURATION, "")),
    (("xyzzy ", " qqq"), (Label.UNPARSED, "qqq")),
]
bad = [(b, a, C(b, a), want) for (b, a), want in cases if C(b, a) != want]
check(not bad, f"all {len(cases)} classifier phrases land on their label", bad[:4])

fl = skilldesc.row_flags("If this attack hits, all adjacent foes take N damage for each hex.")
check(fl >= {"IF", "AREA_ADJACENT", "ALL_FOES", "FOR_EACH"} and "AREA_NEARBY" not in fl,
      "row flags: IF, AREA_ADJACENT, ALL_FOES, FOR_EACH raised and nothing else area-wise", sorted(fl))
check(skilldesc.row_flags("") == frozenset(), "no words, no flags")

labels = [v for k, v in vars(Label).items() if k.isupper()]
check(len(labels) == len(set(labels)), "every Label value is distinct")
check(not (skilldesc.SERVED & skilldesc.RECOGNISED)
      and Label.UNPARSED not in skilldesc.SERVED | skilldesc.RECOGNISED
      and skilldesc.SERVED | skilldesc.RECOGNISED | {Label.UNPARSED} == set(labels),
      "SERVED and RECOGNISED partition the enum, UNPARSED outside both")
check(set(skilldesc.SERVED) == set(skilldesc.CONSUMERS)
      and Label.ENERGY_LOSS in skilldesc.RECOGNISED and Label.HEALTH_PERCENT in skilldesc.RECOGNISED,
      "SERVED is exactly the labels with a consumer; ENERGY_LOSS (the Energy Feast pair) and "
      "HEALTH_PERCENT (the threshold reader, a shape the parse cannot see) are RECOGNISED")
SS = skilldesc.slot_served
check(SS(Label.DURATION, 3, 3) and not SS(Label.DURATION, 3, 15) and not SS(Label.DURATION, 1, 3),
      "DURATION is served at str3 on a Stance (an episode), not on a Shout, and not at str1")
check(SS(Label.FIRE_DAMAGE, 1, 5) and SS(Label.FIRE_DAMAGE, 1, 19)
      and not SS(Label.FIRE_DAMAGE, 1, 4) and not SS(Label.FIRE_DAMAGE, 2, 5),
      "Fire damage is served at str1 on a Spell (skill_damage, at cast) and on a Preparation "
      "(the arrow bonus), not on a Hex (opens an episode; nothing reads its damage) and not at str2")
check(SS(Label.HEAL, 1, 5) and not SS(Label.HEAL, 2, 5) and not SS(Label.HEAL, 1, 6),
      "HEAL: skill_heal reads scale_means at cast -- str1 on a Spell, never str2, not on an Enchantment")
check(SS(Label.CONDITION_DURATION, 1, 14) and SS(Label.CONDITION_DURATION, 2, 5)
      and not SS(Label.CONDITION_DURATION, 3, 5),
      "a condition duration is read from bonus then scale on any type (skill_condition), never duration")
check(SS(Label.ARMOR_PENETRATION, 2, 14) and not SS(Label.ARMOR_PENETRATION, 1, 14),
      "armour penetration is the BONUS slot (combatmath.BASE_PENETRATION_MEANS) and only that")
check(SS(Label.MOVE_SPEED_UP, 1, 3) and SS(Label.MOVE_SPEED_UP, 2, 6) and not SS(Label.MOVE_SPEED_UP, 1, 15)
      and SS(Label.ATTACK_SPEED_UP, 1, 3) and not SS(Label.ATTACK_SPEED_UP, 2, 3),
      "speeds are read off OPEN EPISODES: movement from either slot, attack speed from scale only")
check(SS(Label.ENERGY, 1, 12) and not SS(Label.ENERGY, 1, 5) and not SS(Label.ENERGY, 2, 12),
      "ENERGY is glyph_energy_amount's: str1 on a Glyph and nowhere else")
check(not SS(Label.LEVEL, 1, 5) and skilldesc.served_reason(Label.LEVEL, 1, 5) == "no consumer"
      and skilldesc.served_reason(Label.HEAL, 2, 5) == "wrong slot"
      and skilldesc.served_reason(Label.HEAL, 1, 6) == "episode type"
      and skilldesc.served_reason(Label.DURATION, 3, 15) == "non-episode type"
      and skilldesc.served_reason(Label.ENERGY, 1, 5) == "not a glyph",
      "served_reason names why a slot is not consumed: no consumer / wrong slot / the type")
check(skilldesc.CONDITION_NAMES == tuple(sorted(effects.CONDITION_BY_NAME)),
      "the condition names are effects.CONDITION_BY_NAME's keys -- the join key")

HA = skilldesc.hand_agrees
check(HA(Label.PLUS_DAMAGE, "", "+ Damage") is True
      and HA(Label.LIGHTNING_DAMAGE, "plus", "+ Damage") is True
      and HA(Label.LIGHTNING_DAMAGE, "", "+ Damage") is False,
      "'+ Damage' accepts +N and +N <element>, not standalone element damage")
check(HA(Label.CONDITION_DURATION, "Bleeding", "Bleeding") is True
      and HA(Label.DURATION, "", "Bleeding") is False
      and HA(Label.DURATION, "", "Resurrect") is None,
      "a condition label needs the condition; 'Resurrect' is not comparable")
slots = [(1, Label.PLUS_DAMAGE, ""), (2, Label.CONDITION_DURATION, "Deep Wound")]
hand = {"scale_means": "+ Damage", "bonus_scale_means": "Deep Wound"}
res = skilldesc.referee_hand_row(slots, hand)
check([r[-1] for r in res] == ["AGREE", "AGREE"], "Dismember's shape agrees on both slots", res)
res = skilldesc.referee_hand_row(slots, hand, shifted())
check([r[-1] for r in res] == ["NO_SLOT", "CONFLICT"],
      "under the known-bad mapping the scale field is str3 (no such slot) and the bonus "
      "field is str1, where the template says +damage, not Deep Wound: read from the "
      "TEMPLATE, so the verdicts are NO_SLOT and CONFLICT", res)
check([r[-1] for r in skilldesc.referee_hand_row([], hand, shifted())] == ["NO_SLOT", "NO_SLOT"]
      and [r[-1] for r in skilldesc.referee_hand_row([], hand)] == ["NO_SLOT", "NO_SLOT"],
      "with no slots at all every hand label is NO_SLOT under either mapping -- the verdict "
      "depends on the slots, never on the mapping alone (the vacuous MAPPING_CONFLICT is gone)")
check(skilldesc.referee_hand_row([(1, Label.MOVE_SPEED_UP, "")], {"scale_means": "Duration"})[0][-1]
      == "CONFLICT", "a hand 'Duration' on a movement-speed slot is a CONFLICT")
check(skilldesc.referee_hand_row([(1, Label.DAMAGE, "")], {"bonus_scale_means": "Crippled"})[0][-1]
      == "NO_SLOT", "a hand label on an index the template does not number is NO_SLOT")

# Rush's SHAPE (duration 8..20 on the bit, a flat 25 the text prints) under a
# sentence of our own -- no fixture here is a template (the first version's
# was, to the character, after normalise(): reviewers D4-R2 / ENG-11).
rush = rec(args=1, d=(8, 20), s=(25, 25))
lit = skilldesc.literal_check(rush, "Lasts %str3% seconds; the stride is 25%% quicker.", {3})
check(lit == [(1, "scale", 25, "LITERAL_MATCH")],
      "a flat 25 printed as text is LITERAL_MATCH; the empty bonus is skipped", lit)
check(skilldesc.literal_check(rush, "Lasts %str3% seconds.", {3}) == [(1, "scale", 25, "LITERAL_MISS")],
      "and a constant the text never states is LITERAL_MISS")

# ---------------------------------------------------------------- section 1b
print("\n== 1b. the label tier's gate, on synthetic rows (SKILLS-LT, DESKWORK-D4 step 4) ==")
LT = skilldesc
check(LT.means_for(Label.FIRE_DAMAGE, "") == "Fire damage"
      and LT.means_for(Label.HOLY_DAMAGE, "plus") == "+ Damage"
      and LT.means_for(Label.CONDITION_DURATION, "Crippled") == "Crippled"
      and LT.means_for(Label.CONDITION_DURATION, "") is None
      and LT.means_for(Label.LEVEL, "") is None and LT.means_for(Label.DURATION, "") is None,
      "means_for: our label -> the consumer's own string; +N holy on an attack is the additive "
      "'+ Damage' (Spear of Lightning's precedent); a condition needs its name; DURATION and an "
      "unserved label have none")
check(all(v in LT.OVERLAY_VOCABULARY for v in LT.MEANS_OF.values())
      and all(c in LT.OVERLAY_VOCABULARY for c in LT.CONDITION_NAMES)
      and not {"seconds", "damage", "foe", "target", "for"} & LT.OVERLAY_VOCABULARY
      and LT.text_leak({"a": {"b": ["Heal", "label"], "c": "for 5 seconds"}}) == ["for 5 seconds"]
      and LT.text_leak({"a": {"b": ["Heal", "label"]}}) == []
      and LT.label_detail_vocabulary() == _content.LABEL_DETAILS_KNOWN,
      "OVERLAY_VOCABULARY holds every means and condition name and no template word; text_leak "
      "names a sentence and passes a clean table; and the tier_detail vocabulary EQUALS "
      "content.LABEL_DETAILS_KNOWN (the fix pass: a new mark lands in both files or this reddens, "
      "and an older tree drops the rows that carry it)")


def srow(sid, tc, slots, flags=()):
    return {"id": sid, "type_code": tc, "flags": list(flags), "tier": "SERVED",
            "slots": [{"index": n, "field": SLOT_FIELD[n], "verdict": v, "lo": lo, "hi": hi,
                       "label": lbl, "detail": det} for n, lbl, det, v, lo, hi in slots]}


def srec(target=5, args=2, s=(10, 40), b=(0, 0), d=(0, 0), tc=5):
    r = rec(args=args, s=s, b=b, d=d, type_code=tc)
    r["target"] = target
    return r


G = LT.build_label_row
AP = "AGREE_PROGRESSION"
fire = srow(1, 5, [(1, Label.FIRE_DAMAGE, "", AP, 10, 40)], ["TARGET_FOE"])
why, det, fields, ver = G(fire, srec(5), set())
check(why is None and fields == {"scale_means": "Fire damage"} and det == ["TARGET_FOE"]
      and ver == [{"slot": 1, "field": "scale", "lo": 10, "hi": 40, "verdict": AP, "label": Label.FIRE_DAMAGE}],
      "a plain fire Spell on a foe ships: scale_means = 'Fire damage', the slot's agreement as "
      "numbers and enums, no text", (why, det, fields, ver))
check(G(fire, srec(5), {1})[0] == LT.EXCL_HAND_ROW, "a hand-row id is EXCLUDED: the tier sits under it")
check(G(fire, srec(5), set(), {1})[0] == LT.EXCL_SELF_CONFLICT,
      "a row whose parse disagrees with itself (one index, two labels) is EXCLUDED")
check(G(fire, srec(0), set())[0] == LT.EXCL_RECIPIENT_NOT_A_FOE
      and G(fire, srec(4), set())[0] == LT.EXCL_RECIPIENT_NOT_A_FOE
      and G(fire, srec(1), set())[0] == LT.EXCL_RECIPIENT_NOT_A_FOE
      and G(fire, srec(16), set())[0] is None,
      "at-cast damage acts on the cast's target, so the target byte must be a foe (5) or the "
      "burst's aim (16): self (0), the unresolved 1 and other-ally (4) are EXCLUDED -- the server "
      "would hit whatever is selected, at any range")
area = srow(2, 5, [(1, Label.FIRE_DAMAGE, "", AP, 7, 112)], ["ALL_FOES", "AREA_ADJACENT", "TARGET_FOE"])
check(LT.DETAIL_AREA_BURST in G(area, srec(16), set())[1]
      and LT.DETAIL_AREA_ONE_TARGET in G(area, srec(5), set())[1]
      and LT.DETAIL_AREA_ONE_TARGET in G(dict(area, id=3, type_code=7), srec(16), set())[1]
      and LT.DETAIL_AREA_BURST not in G(dict(area, id=3, type_code=7), srec(16), set())[1],
      "area wording: a byte-16 Spell's standalone damage is spell_burst's (AREA_BURST); the same "
      "words on a byte-5 Spell or on a Signet reach ONE target and say so (AREA_ONE_TARGET)")
dur = srow(4, 3, [(3, Label.DURATION, "", AP, 8, 20)])
check(G(dur, srec(0, args=1, d=(8, 20), tc=3), set())[0] == LT.EXCL_DURATION_ONLY,
      "a duration-only Stance has no field to write -- resolve_duration reads the skills table "
      "-- so it is EXCLUDED rather than emitted empty (an empty row would grade 'modelled')")
cond_ep = srow(5, 19, [(2, Label.CONDITION_DURATION, "Poison", AP, 3, 15)])
check(G(cond_ep, srec(0, args=4, b=(3, 15), tc=19), set())[0] == LT.EXCL_CONDITION_ON_EPISODE
      and G(dict(cond_ep, type_code=6), srec(0, args=4, b=(3, 15), tc=6), set())[0] == LT.EXCL_CONDITION_ON_EPISODE,
      "a condition on a Preparation or an Enchantment is what the episode does LATER (poisoned "
      "arrows, bleeding daggers); skill_condition would inflict it at the cast: EXCLUDED -- "
      "A LABEL DOES NOT SAY WHEN")
cond = srow(6, 5, [(1, Label.CONDITION_DURATION, "Poison", AP, 5, 20)], ["TARGET_FOE"])
why, det, fields, ver = G(cond, srec(5), set())
check(why is None and fields == {"scale_means": "Poison"} and ver[0]["detail"] == "Poison",
      "a plain Poison at str1 on a foe Spell ships as scale_means = 'Poison' -- skill_condition's "
      "second slot -- with the condition name in the record", (why, fields, ver))
flat = srow(7, 5, [(1, Label.EARTH_DAMAGE, "", AP, 10, 40),
                   (2, Label.CONDITION_DURATION, "Blind", "AGREE_FLAT", 10, 10)], ["TARGET_FOE"])
why, det, fields, _v = G(flat, srec(5, args=2, b=(10, 10)), set())
check(why is None and fields == {"scale_means": "Earth damage", "bonus_scale_means": "Blind"}
      and LT.DETAIL_CONDITION_BIT_CLEAR in det,
      "a condition on a BIT-CLEAR slot ships labelled and MARKED: skill_scale_value refuses the "
      "slot, so the damage lands and the Blind does not (under-applied, counted)", (det, fields))
indet = srow(8, 10, [(2, Label.CONDITION_DURATION, "Deep Wound", "INDETERMINATE", 5, 20)], ["TARGET_FOE"])
check(LT.DETAIL_INDETERMINATE in G(indet, srec(5, args=2, b=(5, 20), tc=10), set())[1],
      "an INDETERMINATE slot ships MARKED (54.3's contest; the consumer refuses the bit-clear pair)")
two = srow(12, 15, [(2, Label.CONDITION_DURATION, "Bleeding", AP, 5, 15),
                    (1, Label.CONDITION_DURATION, "Crippled", AP, 5, 15)], ["TARGET_FOE"])
check(LT.DETAIL_SECOND_CONDITION in G(two, srec(5, args=6, s=(5, 15), b=(5, 15), tc=15), set())[1],
      "two conditions on one row: skill_condition returns the first, the second is MARKED dropped")
pet = srow(9, 20, [(1, Label.PLUS_DAMAGE, "", AP, 5, 20)])
check(G(pet, srec(0, tc=20), set())[0] == LT.EXCL_PET_ATTACK, "a pet attack is EXCLUDED: no pet is modelled")
heal = srow(10, 5, [(1, Label.HEAL, "", AP, 30, 240)])
check(G(heal, srec(1), set())[0] == LT.EXCL_RECIPIENT_NOT_AN_ALLY
      and G(heal, srec(5), set())[0] == LT.EXCL_RECIPIENT_NOT_AN_ALLY
      and G(heal, srec(3), set())[0] is None and G(heal, srec(0), set())[0] is None
      and G(heal, srec(4), set())[2] == {"scale_means": "Heal"},
      "a heal needs a recipient cast_recipient places on self / ally / other ally (0, 3, 4): "
      "byte 1 or 5 hands it to the SELECTED agent, a foe included -- EXCLUDED")
prep = srow(11, 19, [(3, Label.DURATION, "", AP, 1, 12), (1, Label.PLUS_DAMAGE, "", AP, 1, 8)],
            ["ALL_FOES", "AREA_ADJACENT"])
why, det, fields, ver = G(prep, srec(0, args=3, s=(1, 8), d=(1, 12), tc=19), set())
check(why is None and fields == {"scale_means": "+ Damage"} and LT.DETAIL_AREA_ONE_TARGET in det
      and [v["slot"] for v in ver] == [3, 1],
      "a Preparation's +damage ships: swing_preparation_bonus is its consumer and the target byte "
      "is the caster's own; its adjacency splash is marked under-applied; the duration slot is "
      "recorded, not labelled", (why, det, fields, ver))
# ---- the FIX PASS's rules (2026-09-23, reviewers LT-R1..R10 / ENG-2), each with its arm
pct = srow(13, 5, [(1, Label.HEAL, "", AP, 100, 136)], ["TARGET_ALLY"])
pct["slots"][0]["percent"] = True
spd = srow(14, 3, [(1, Label.MOVE_SPEED_UP, "", AP, 10, 33)])
spd["slots"][0]["percent"] = True
check(G(pct, srec(4), set())[0] == LT.EXCL_PERCENT_SLOT and G(heal, srec(4), set())[0] is None
      and G(spd, srec(0, tc=3), set())[0] is None,
      "a slot printed as a PERCENT under a non-percent label is EXCLUDED (292: 'N% of the amount "
      "you lost' parsed HEAL would heal N Health and charge no sacrifice); the same heal without "
      "the % ships, and a percent under a percent label (movement speed) is what the consumer reads")
chain = srow(15, 5, [(1, Label.CONDITION_DURATION, "Poison", AP, 5, 20)], ["TARGET_FOE"])
r_chain = srec(5)
r_chain["combo_req"] = 2
why_c, det_c, _f, _v = G(chain, r_chain, set())
check(why_c is None and LT.DETAIL_CHAIN_GATED in det_c
      and LT.DETAIL_CHAIN_GATED not in G(dict(chain, type_code=14), dict(r_chain, type_code=14), set())[1]
      and LT.DETAIL_CHAIN_GATED not in G(chain, srec(5), set())[1],
      "SKILLS-LU: combo_req on a NON-attack type SHIPS marked CHAIN_GATED -- the player's E5 judges "
      "it now (784 973 1033; until 2026-09-23 the gate excluded them as CHAIN_REQUIREMENT); the "
      "same requirement on an attack carries no mark (the attack gate is DAGGERS-B5's), nor does a "
      "row with combo_req 0", (why_c, det_c))
step = srow(16, 10, [(1, Label.CONDITION_DURATION, "Crippled", AP, 5, 20)], ["TARGET_FOE"])
r_step = srec(5, tc=10)
r_step["combo"] = 2
step_dmg = srow(16, 10, [(1, Label.EARTH_DAMAGE, "", AP, 5, 20)], ["TARGET_FOE"])
check(LT.DETAIL_CHAIN_STEP_ADVANCES in G(step, r_step, set())[1]
      and LT.DETAIL_CHAIN_STEP_NOT_ADVANCED not in G(step, r_step, set())[1]
      and LT.DETAIL_CHAIN_STEP_NOT_ADVANCED in G(step_dmg, r_step, set())[1]
      and LT.DETAIL_CHAIN_STEP_ADVANCES not in G(step_dmg, r_step, set())[1],
      "'counts as an off-hand attack' on a non-attack WITH a condition ships marked CHAIN_STEP_ADVANCES "
      "(974: the chain moves as the condition lands, SKILLS-LU); with damage alone it is still "
      "CHAIN_STEP_NOT_ADVANCED -- the advance rides the condition's landing")
# SKILLS-LU (A): the caster-centred area -- byte 0, a Spell, a radius, no projectile, foe-area words
c_area = srow(30, 5, [(1, Label.FIRE_DAMAGE, "", AP, 30, 135)], ["ALL_FOES", "AREA_ADJACENT"])
r_c = srec(0)
r_c["aoe_range"] = 156.0
why_a, det_a, f_a, _v = G(c_area, r_c, set())
c_cond = srow(31, 5, [(1, Label.CONDITION_DURATION, "Poison", AP, 5, 15)], ["ALL_FOES", "AREA_ADJACENT"])
r_cd = srec(0, args=3, s=(5, 15), d=(10, 10))
r_cd["aoe_range"] = 156.0
why_b, det_b, f_b, _v = G(c_cond, r_cd, set())
r_noradius = dict(r_c, aoe_range=0.0)
r_proj = dict(r_c, projectile=199)
c_nowords = srow(32, 5, [(1, Label.FIRE_DAMAGE, "", AP, 30, 135)], [])
c_signet = srow(33, 7, [(1, Label.FIRE_DAMAGE, "", AP, 30, 135)], ["ALL_FOES", "AREA_ADJACENT"])
check(why_a is None and f_a == {"scale_means": "Fire damage"} and LT.DETAIL_AREA_CASTER in det_a
      and LT.DETAIL_AREA_ONE_TARGET not in det_a and LT.DETAIL_AREA_BURST not in det_a
      and why_b is None and f_b == {"scale_means": "Poison"} and LT.DETAIL_AREA_CASTER in det_b
      and LT.DETAIL_DURATION_UNMODELLED in det_b,
      "SKILLS-LU: a byte-0 Spell with a radius and 'all adjacent foes' SHIPS marked AREA_CASTER -- "
      "authsrv.caster_area bursts from the caster (183's fire, 840's Poison; 840's flat 10 s is "
      "marked DURATION_UNMODELLED beside it); until 2026-09-23 both were RECIPIENT_NOT_A_FOE",
      (why_a, det_a, why_b, det_b))
check(G(c_area, r_noradius, set())[0] == LT.EXCL_RECIPIENT_NOT_A_FOE
      and G(c_area, r_proj, set())[0] == LT.EXCL_RECIPIENT_NOT_A_FOE
      and G(c_nowords, r_c, set())[0] == LT.EXCL_RECIPIENT_NOT_A_FOE
      and G(c_signet, dict(r_c, type_code=7), set())[0] == LT.EXCL_RECIPIENT_NOT_A_FOE
      and G(dict(c_area, flags=["ALL_FOES", "AREA_ADJACENT", "UNMODELLED_CLASS"]), r_c, set())[0]
      == LT.EXCL_UNMODELLED_CLASS,
      "KNOWN-BAD ARMS: the same byte-0 row with NO radius (1364's self Bleeding), with a projectile "
      "of its own, with no area words, or on a Signet stays RECIPIENT_NOT_A_FOE -- the caster arm "
      "is a Spell with a radius and foe-area words, nothing looser; a corpse-centred one (97) falls "
      "to UNMODELLED_CLASS")
# SKILLS-LU (B): the party heal -- byte 0, a Spell, a radius, party words AND a read INCLUDES_CASTER
# template whose sha256[:16] matches (CLASS_HEAL_READINGS); the synthetic row borrows 287's reading
p_heal = srow(287, 5, [(1, Label.HEAL, "", AP, 30, 75)], ["ALL_ALLIES"])
p_heal["template_sha16"] = LT.CLASS_HEAL_READINGS[287][1]
r_p = srec(0, s=(30, 75))
r_p["aoe_range"] = 5000.0
why_p, det_p, f_p, _v = G(p_heal, r_p, set())
p_wrongsha = dict(p_heal, template_sha16="0" * 16)
p_unread = dict(p_heal, id=289)
p_cond = dict(p_heal, id=943, template_sha16=LT.CLASS_HEAL_READINGS[943][1])
p_excl = dict(p_heal, id=1262, template_sha16=LT.CLASS_HEAL_READINGS[1262][1], flags=["AREA_ADJACENT"])
check(why_p is None and f_p == {"scale_means": "Heal"} and LT.DETAIL_HEAL_PARTY in det_p
      and LT.DETAIL_AREA_ONE_TARGET not in det_p,
      "SKILLS-LU: a byte-0 party heal whose template a person read as INCLUDES_CASTER (287, the "
      "digest matching) SHIPS marked HEAL_PARTY -- authsrv.party_heal_radius heals the caster and "
      "its allies within the record's radius", (why_p, det_p))
check(G(p_wrongsha, r_p, set())[0] == LT.EXCL_HEAL_RECIPIENT_CLASS
      and G(p_unread, r_p, set())[0] == LT.EXCL_HEAL_RECIPIENT_CLASS
      and G(p_cond, r_p, set())[0] == LT.EXCL_HEAL_RECIPIENT_CLASS
      and G(p_excl, dict(r_p, aoe_range=156.0), set())[0] == LT.EXCL_HEAL_RECIPIENT_CLASS
      and G(p_heal, dict(r_p, aoe_range=0.0), set())[0] == LT.EXCL_HEAL_RECIPIENT_CLASS,
      "KNOWN-BAD ARMS: the same row with a DIFFERENT template digest (the text changed: the reading "
      "is void), an id nobody read, 943's CONDITIONED reading, 1262's EXCLUDES_CASTER reading, or no "
      "radius each stay HEAL_RECIPIENT_CLASS -- Refuse to guess, per row")
check(LT.template_sha16("abc") == LT.template_sha16("abc") and LT.template_sha16("abc") != LT.template_sha16("abd")
      and len(LT.template_sha16("")) == 16 and LT.template_sha16(None) == LT.template_sha16("")
      and all(len(v[1]) == 16 and v[0] in (LT.CLASS_HEAL_INCLUDES_CASTER, LT.CLASS_HEAL_EXCLUDES_CASTER,
                                            LT.CLASS_HEAL_CONDITIONED) for v in LT.CLASS_HEAL_READINGS.values())
      and sorted(LT.CLASS_HEAL_READINGS) == [287, 943, 1262, 2221],
      "template_sha16 is a 16-hex measurement of one template, sensitive to one character; the "
      "readings register holds the four class heals of 55.2, each an enum and a digest")
uncls = srow(17, 5, [(1, Label.HEAL, "", AP, 60, 92)], ["UNMODELLED_CLASS"])
check(G(uncls, srec(0), set())[0] == LT.EXCL_UNMODELLED_CLASS,
      "a recipient class or prerequisite the server has no object for is EXCLUDED: the spirits "
      "2051 and 2100 heal, 96's corpse, 106's fleshiness")
cls = srow(18, 5, [(1, Label.HEAL, "", AP, 30, 150)], ["AREA_ADJACENT"])
party = srow(19, 5, [(1, Label.HEAL, "", AP, 30, 150)], ["ALL_ALLIES"])
check(G(cls, srec(0), set())[0] == LT.EXCL_HEAL_RECIPIENT_CLASS
      and G(party, srec(0), set())[0] == LT.EXCL_HEAL_RECIPIENT_CLASS
      and G(heal, srec(0), set())[0] is None
      and G(party, srec(3), set())[0] is None and LT.DETAIL_AREA_ONE_TARGET in G(party, srec(3), set())[1],
      "a SELF-targeted heal on a CLASS of recipients is EXCLUDED unless a person read its template "
      "(1262 excludes the caster, 943 heals only the members relieved of Burning; an UNREAD row "
      "falls to the same rule -- the parse cannot tell them apart); a plain self heal ships, and a "
      "party heal aimed at an ally (byte 3) ships marked ONE_TARGET")
r_dur = srec(16, d=(9, 9))
r_proj = srec(16)
r_proj["projectile"] = 199
check(LT.DETAIL_AREA_ONE_TARGET in G(area, r_dur, set())[1] and LT.DETAIL_AREA_BURST not in G(area, r_dur, set())[1]
      and LT.DETAIL_DURATION_UNMODELLED in G(area, r_dur, set())[1]
      and LT.DETAIL_AREA_ONE_TARGET in G(area, r_proj, set())[1] and LT.DETAIL_AREA_BURST not in G(area, r_proj, set())[1],
      "spell_burst's WHOLE predicate: a byte-16 Spell with a duration is an area over time the "
      "server delivers once to one target (192, 197: ONE_TARGET + DURATION_UNMODELLED), and one "
      "with its own projectile flies instead of bursting")
cl = srow(20, 5, [(1, Label.FIRE_DAMAGE, "", AP, 10, 40)],
          ["TARGET_FOE", "CLAUSE_KNOCKDOWN", "CLAUSE_INTERRUPT", "LITERAL_PERCENT"])
cl["conditions_named"] = ["Cracked Armor"]
det = G(cl, srec(5), set())[1]
check({"CLAUSE_KNOCKDOWN", "CLAUSE_INTERRUPT", LT.DETAIL_LITERAL_DROPPED, LT.DETAIL_CONDITION_UNNUMBERED} <= set(det)
      and all(d in LT.DETAILS for d in det if d not in ("TARGET_FOE",)),
      "the clauses a label DROPS are named in tier_detail, every token from DETAILS: a knock-down, "
      "an interrupt, a literal constant (25% armor penetration), a condition the text names and "
      "no slot numbers (228's Cracked Armor)", det)
mv = srow(21, 4, [(1, Label.ATTACK_SPEED_DOWN, "", AP, 10, 33)], ["TARGET_FOE", "SPEED_MOVE", "CLAUSE_CAST_SPEED"])
mv2 = srow(22, 4, [(1, Label.MOVE_SPEED_DOWN, "", AP, 10, 33)], ["TARGET_FOE", "SPEED_MOVE"])
check(LT.DETAIL_CLAUSE_MOVE_SPEED in G(mv, srec(5, tc=4), set())[1]
      and "CLAUSE_CAST_SPEED" in G(mv, srec(5, tc=4), set())[1]
      and LT.DETAIL_CLAUSE_MOVE_SPEED not in G(mv2, srec(5, tc=4), set())[1],
      "a move-speed clause with no MOVE_SPEED label is a dropped clause (1996 slows movement, "
      "attacks and casting under ONE slot; only the attack speed is read); a labelled snare is not")
rf = LT.row_flags
check("CLAUSE_KNOCKDOWN" in rf("the foe is knocked down") and "CLAUSE_SHADOW_STEP" in rf("shadow step to the foe")
      and "CLAUSE_INTERRUPT" in rf("struck foes are interrupted")
      and "CLAUSE_INTERRUPT" not in rf("this spell is easily interrupted")
      and "UNMODELLED_CLASS" in rf("all spirits you control") and "UNMODELLED_CLASS" not in rf("all non-spirit foes")
      and "UNMODELLED_CLASS" in rf("exploit nearest corpse") and "UNMODELLED_CLASS" in rf("target fleshy foe")
      and "AREA_NEAR" in rf("up to two other foes near your target") and "AREA_NEAR" in LT.AREA_FLAGS
      and "CLAUSE_RANGE" in rf("half the normal range")
      and "CLAUSE_REMOVAL" in rf("remove one condition and one hex")
      and "CLAUSE_ALSO_CASTER" in rf("you and that ally are healed")
      and "CLAUSE_DOUBLE_DAMAGE" in rf("you take double damage") and "CLAUSE_DISABLE" in rf("your skills are disabled")
      and "CLAUSE_CAST_SPEED" in rf("casts spells 33% slower") and "SPEED_MOVE" in rf("moves, attacks, and casts 25% slower")
      and "CLAUSE_REMOVAL" in rf("the allies are relieved of bleeding") and "CLAUSE_REVEAL" in rf("any hidden objects show up")
      and "CLAUSE_REVEAL" in rf("secret doors are revealed")
      and "CLAUSE_ALSO_CASTER" in rf("you and all nearby foes are dazed") and "CLAUSE_REVEAL" in LT.DETAILS
      and not rf("target foe is struck for 30 fire damage") & (LT.CLAUSE_FLAGS | {"UNMODELLED_CLASS", "AREA_NEAR", "SPEED_MOVE"})
      and not (LT.CLAUSE_FLAGS | {"UNMODELLED_CLASS", "AREA_NEAR", "SPEED_MOVE"}) & LT.COMPOUND_FLAGS,
      "the fix pass's flags on OUR OWN phrases: each raised where its wording is, quiet on 'easily "
      "interrupted', 'non-spirit' and a plain sentence -- and none of them is a COMPOUND flag, so "
      "the owner's 131 stay 131")
check(LT.template_digest({1: "a", 2: "b"}) == LT.template_digest({2: "b", 1: "a"})
      and LT.template_digest({1: "a", 2: "b"}) != LT.template_digest({1: "a", 2: "c"})
      and len(LT.template_digest({})) == 64,
      "template_digest: order-free over ids, sensitive to one character, a sha256 hex")
rep_fake = {"rows": {1: fire, 2: dict(fire, id=2, flags=["IF", "TARGET_FOE"]),
                     3: dict(dur, tier="RECOGNISED"), 4: dict(fire, id=4, flags=["WHILE"]),
                     5: pct, 6: uncls, 7: dict(fire, id=7)},
            "self_conflicts": []}
check(LT.plain_served(rep_fake) == [1, 5, 6, 7] and LT.conditional_served(rep_fake) == [2, 4],
      "plain = SERVED with none of the six flags (the percent, unmodelled-class and chain rows are "
      "PLAIN -- the gate, not the definition, is what refuses them); conditional = SERVED with one; "
      "RECOGNISED is neither")
rows = {1: {"fields": {"scale_means": "Fire damage"}, "type_code": 5, "tier": "label",
            "tier_detail": ["TARGET_FOE"], "verified": [{"slot": 1, "label": Label.FIRE_DAMAGE}]}}
check(LT.check_label_rows(rows, rep_fake, set()) == [], "a clean row set passes its own checker")
bad = dict(rows)
bad[2] = dict(rows[1])
bad[4] = dict(rows[1], fields={"scale_means": "Fire damage to all nearby foes"})
faults = LT.check_label_rows(bad, rep_fake, {1})
check(any("conditional wording IF" in x for x in faults) and any("WHILE" in x for x in faults)
      and any("hand row" in x for x in faults) and any("vocabulary" in x for x in faults)
      and len(faults) == 4,
      "KNOWN-BAD ARM: a conditional row forced in (IF; WHILE), a hand-row id and a means outside "
      "the vocabulary are each NAMED by the checker", faults)
bad2 = {5: dict(rows[1], fields={"scale_means": "Heal"}), 6: dict(rows[1]), 7: dict(rows[1])}
faults2 = LT.check_label_rows(bad2, rep_fake, set(), records={7: {"combo_req": 2}})
check(len(faults2) == 3 and any("percent slot str1" in x for x in faults2)
      and any("recipient class" in x for x in faults2) and any("chain requirement 2" in x for x in faults2)
      and LT.check_label_rows({7: dict(rows[1])}, rep_fake, set(), records={7: {"combo_req": 2, "type_code": 14}}) != []
      and LT.check_label_rows({7: dict(rows[1])}, rep_fake, set(), records={7: {"combo_req": 0}}) == [],
      "KNOWN-BAD ARM (the fix pass): a percent slot under HEAL, an unmodelled recipient class and a "
      "chain requirement on a non-attack, each forced in, are each NAMED by the checker; the same "
      "row with combo_req 0 passes", faults2)
import tempfile   # noqa: E402
import tomllib    # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    p = os.path.join(tmp, "x.toml")
    LT.emit_labels(rows, [(9, LT.EXCL_PET_ATTACK)], 38797, "exe", p, plain=[1, 9],
                   dat="the.dat", digest="ab" * 32)
    with open(p, "rb") as fh:
        table = tomllib.load(fh)
    text = open(p, encoding="utf-8").read()
    check(table["skill_effect"]["1"]["tier"] == "label"
          and table["skill_effect"]["1"]["scale_means"] == "Fire damage"
          and table["skill_effect"]["1"]["provenance"] == {
              "source": "client-table", "extractor": "toolkit/clientscan/skilldesc.py",
              "build": 38797, "verified": [{"slot": 1, "label": Label.FIRE_DAMAGE}]}
          and LT.text_leak(table) == [] and "# excluded PET_ATTACK (1): 9" in text
          and "# rows: 1 label-tier" in text
          and "# dat: the.dat" in text and ("# templates_sha256: " + "ab" * 32) in text
          and not os.path.exists(p + ".tmp"),
          "emit_labels writes a TOML tomllib reads back: the means, tier, client-table provenance "
          "with the build, the slot record; no text; the exclusions, the dat and the templates' "
          "sha256 in the header; the temp file it renamed into place is gone", table)
    try:
        LT.emit_labels({1: dict(rows[1], fields={"scale_means": "Fire\ndamage"})}, [], 38797, "exe", p)
        raised = False
    except ValueError:
        raised = True
    check(raised, "the writer refuses a value that is not a plain token (a newline inside a string)")

# ---------------------------------------------------------------- section 2
print("\n== 2. the corpus (pinned exe + Gw.dat) ==")
try:
    records, texts, ix, exe, why = skilldesc.load_corpus()
except SystemExit as ex:
    # pinned.find's refusal, and ONLY that: no vault, or the build not in it.
    # Anything else (a loader defect, a missing Gw.dat beside a present exe)
    # must redden the run, not pass it at the bare floor (ENG-4).
    records = None
    LEDGER.skip("2. the corpus", f"{type(ex).__name__}: {str(ex).splitlines()[0]}")

if records is not None:
    print(f"   {exe}\n   ({why})")
    hand_rows = skilldesc.hand_rows()
    rep = skilldesc.analyse(records, texts, hand_rows)
    check(rep["n_rows"] == 1333, "the player corpus is 1,333 rows (build 38797)", rep["n_rows"])
    check(rep["n_with_slot"] == 1265, "1,265 of them carry a %strN% slot (the probe, reproduced)",
          rep["n_with_slot"])
    check(rep["n_slot_occurrences"] == 2357, "2,357 slot occurrences", rep["n_slot_occurrences"])
    check(rep["n_unreadable"] == 0 and "UNREADABLE" not in rep["tiers"],
          "0 descriptions the archive cannot resolve (counted, never folded into 'no slot')",
          rep["n_unreadable"])
    ix_counts = collections.Counter()
    for r in rep["rows"].values():
        for s in r["slots"]:
            ix_counts[s["index"]] += 1
    check(dict(ix_counts) == {1: 1090, 2: 582, 3: 685},
          "str1 1,090 / str2 582 / str3 685 -- the orchestrator's counts to the row", dict(ix_counts))

    v = rep["verdicts"]
    check(not (set(v) & skilldesc.CONFLICTS),
          "THE THEOREM: under the measured mapping no slot numbers an empty field, "
          "a sentinel or a bad index", v)
    check(v.get("AGREE_PROGRESSION") == 1698 and v.get("AGREE_FLAT") == 481
          and v.get("INDETERMINATE") == 141,
          "1,698 progressions, 481 flat constants, 141 indeterminate (bit clear, differing)", v)
    check(len(rep["hidden_progressions"]) == 21,
          "21 enabled progressions the template never numbers", len(rep["hidden_progressions"]))
    for by in (1, 2):
        bad_rep = skilldesc.analyse(records, texts, hand_rows, shifted(by=by))
        bv = bad_rep["verdicts"]
        check(bv.get("CONFLICT_EMPTY", 0) >= 750 and bv.get("CONFLICT_SENTINEL", 0) >= 10,
              f"KNOWN-BAD ARM shift {by}: 750+ distinct slots on 0/0 fields (762 / 763 measured, "
              f"33 of them bit-set) and some on sentinels",
              {k: bv.get(k, 0) for k in skilldesc.CONFLICTS})
        bh = bad_rep["hand_summary"]
        check(bh.get("AGREE", 0) <= 5 and bh.get("CONFLICT", 0) >= 15
              and "MAPPING_CONFLICT" not in bh,
              f"  and the hand rows' 51 AGREE collapse to <= 5 with 15+ CONFLICT at shift {by} "
              f"-- read from the templates, a witness the arm can fail", bh)
        check(len(bad_rep["hidden_progressions"]) >= 800,
              f"  and the hidden-progression count explodes at shift {by}",
              len(bad_rep["hidden_progressions"]))

    # THE CONTROLS -- each pinned to the wiki by world.toml or FINDINGS 4.
    def slot(sid, n):
        return next(s for s in rep["rows"][sid]["slots"] if s["index"] == n)

    def has_index(sid, n):
        return any(s["index"] == n for s in rep["rows"][sid]["slots"])

    s = slot(382, 2)
    check(s["field"] == "bonus_scale" and (s["lo"], s["hi"]) == (5, 25)
          and s["verdict"] == "AGREE_PROGRESSION"
          and (s["label"], s["detail"]) == (Label.CONDITION_DURATION, "Bleeding")
          and not has_index(382, 1) and not has_index(382, 3),
          "Sever Artery (382): its ONE slot is str2 = bonus 5..25 = Bleeding's duration", s)
    s3, s2 = slot(135, 3), slot(135, 2)
    check(s3["field"] == "duration" and (s3["lo"], s3["hi"]) == (3, 16) and s3["label"] == Label.DURATION
          and s2["field"] == "bonus_scale" and (s2["lo"], s2["hi"]) == (0, 3) and s2["label"] == Label.HEALTH_DEGEN
          and not has_index(135, 1),
          "Faintheartedness (135): str3 = duration 3..16, str2 = bonus 0..3 degeneration, no str1",
          (s3, s2))
    check(rep["rows"][135]["literals"] == [(1, "scale", 50, "LITERAL_MATCH")],
          "  and its flat 50 (attack 50% slower) is printed as text", rep["rows"][135]["literals"])
    s1, s2, s3 = slot(318, 1), slot(318, 2), slot(318, 3)
    check((s1["lo"], s1["hi"], s1["label"]) == (90, 300, Label.MAX_HEALTH)
          and (s2["lo"], s2["hi"], s2["label"]) == (1, 10, Label.DAMAGE_REDUCTION)
          and (s3["lo"], s3["hi"], s3["verdict"], s3["label"]) == (20, 20, "AGREE_FLAT", Label.DURATION),
          "Defy Pain (318): str1 scale 90..300 max health, str2 bonus 1..10 reduction, str3 flat 20 s",
          (s1, s2, s3))
    s3 = slot(319, 3)
    check((s3["lo"], s3["hi"], s3["label"]) == (8, 20, Label.DURATION) and not has_index(319, 1)
          and rep["rows"][319]["literals"] == [(1, "scale", 25, "LITERAL_MATCH")],
          "Rush (319): str3 = duration 8..20; the 25 is literal text over a flat scale slot",
          (s3, rep["rows"][319]["literals"]))
    s1 = slot(322, 1)
    check((s1["field"], s1["lo"], s1["hi"], s1["label"]) == ("scale", 10, 40, Label.PLUS_DAMAGE)
          and len(rep["rows"][322]["slots"]) == 1,
          "Power Attack (322): its one slot is str1 = scale 10..40 = +damage", s1)
    s1, s2, s3 = slot(316, 1), slot(316, 2), slot(316, 3)
    check((s1["lo"], s1["hi"], s1["label"]) == (10, 60, Label.MAX_HEALTH)
          and (s2["lo"], s2["hi"], s2["label"]) == (1, 6, Label.COUNT)
          and (s3["lo"], s3["hi"], s3["label"]) == (10, 20, Label.DURATION),
          "\"To the Limit!\" (316): three slots, three fields, the wiki's three variables",
          (s1, s2, s3))
    s1 = slot(234, 1)
    check((s1["lo"], s1["hi"], s1["label"]) == (10, 85, Label.COLD_DAMAGE)
          and (2, "bonus_scale", 66, "LITERAL_MATCH") in rep["rows"][234]["literals"]
          and "LITERAL_PERCENT" in rep["rows"][234]["flags"]
          and rep["rows"][234]["tier"] == "RECOGNISED" and rep["rows"][234]["type_code"] == 4,
          "Deep Freeze (234, a consistency row, not wiki-pinned): str1 cold damage 10..85; its 66% "
          "is literal text over bonus 66/66; and it is RECOGNISED, not served -- a Hex opens an "
          "episode and skill_damage resolves nothing at its cast", (s1, rep["rows"][234]["literals"]))
    check(rep["rows"][322]["tier"] == "SERVED" and rep["rows"][382]["tier"] == "SERVED"
          and rep["rows"][319]["tier"] == "SERVED",
          "Power Attack (+damage at str1 on an attack), Sever Artery (Bleeding at str2) and Rush "
          "(duration at str3 on a Stance) are SERVED: the consumer that reads each exists")

    # THE HAND ROWS. Content-side counts are derived from the rows loaded, not
    # pinned as literals, so a new [skill_effect.*] row does not redden a
    # clientscan test (ENG-7); the CLIENT-side facts below stay exact.
    n_hand = sum(1 for sid in hand_rows if sid in records)
    n_means = sum(1 for sid in hand_rows if sid in records
                  for k in ("scale_means", "bonus_scale_means") if hand_rows[sid].get(k))
    hs = rep["hand_summary"]
    check(sum(hs.values()) == n_means and hs.get("AGREE", 0) >= n_means - 17 and hs.get("AGREE", 0) >= 50,
          f"every one of the {n_means} hand labels gets a verdict and at least {max(50, n_means - 17)} AGREE "
          f"(51 of 68 on 2026-09-22)", hs)
    conflicts = [r for r in rep["hand"] if r[-1] == "CONFLICT"]
    check(conflicts == [],
          "no hand label conflicts with the parse. Battle Rage 317's `scale_means = "
          "\"Duration\"` on the flat 33 that is its movement speed (the duration is str3) "
          "was the one conflict until 2026-09-23; world.toml dropped it with Scourge "
          "Sacrifice 253's, and test_skilldamage.py's pins moved in the same commit "
          "(SKILLS-LT)", conflicts)
    no_slot = [r for r in rep["hand"] if r[-1] == "NO_SLOT"]
    unmatched = []
    for sid, key, index, _means, _lbl, _v in no_slot:
        field = SLOT_FIELD[index]
        if not any(l[1] == field and l[3] == "LITERAL_MATCH" for l in rep["rows"][sid]["literals"]):
            unmatched.append(sid)
    check(len(no_slot) >= 10 and unmatched == [],
          "every unshown hand slot is a flat constant printed as text. Until 2026-09-23 two were "
          "not: Hamstring's (320) 0/0 scale (a label on the wrong slot -- now `bonus_scale_means = "
          "\"Crippled\"`, the slot %str2% numbers) and Scourge Sacrifice's (253) flat 100 the text "
          "never states (labelled 'Duration', which is str3 -- dropped)", (len(no_slot), unmatched))
    h320 = [r for r in rep["hand"] if r[0] == 320]
    check(h320 == [(320, "bonus_scale_means", 2, "Crippled", f"{Label.CONDITION_DURATION}:Crippled", "AGREE")],
          "Hamstring's hand label now AGREES with the template at str2", h320)
    check(records[253]["scale0"] == 100 and records[253]["skill_arguments"] == 1
          and slot(253, 3)["field"] == "duration",
          "Scourge Sacrifice (253): args = duration only, str3 is the duration; the scale slot's "
          "100 is an engine constant with no slot and no literal", records[253]["scale0"])
    check(records[320]["scale0"] == 0 and records[320]["skill_arguments"] == 4
          and (slot(320, 2)["label"], slot(320, 2)["detail"]) == (Label.CONDITION_DURATION, "Crippled"),
          "Hamstring (320): the client's Crippled duration is str2 = BONUS 3..15 (args = bonus only), "
          "not the scale slot the hand row names", slot(320, 2))

    sc = rep["self_conflicts"]
    check(len(sc) == 18 and (476, 3, [Label.DURATION, Label.LIFETIME]) in sc
          and any(s[0] == 951 and set(s[2]) == {Label.MOVE_SPEED_DOWN, Label.MOVE_SPEED_UP} for s in sc),
          "18 templates give one index two labels -- listed as the classifier disagreeing with "
          "itself (476's str3 DURATION vs LIFETIME, 951's up vs down), never fitted", sc[:6])

    t = rep["tiers"]
    check("UNPARSED" not in t, "every slot in the corpus gets a label (0 UNPARSED rows)", t)
    check(t.get("NO_SLOT") == 68 and sum(t.values()) == 1333, "68 rows have no slot; the tiers sum to 1,333", t)
    check(t.get("SERVED", 0) == 341 and t.get("SERVED", 0) * 2 < 1265,
          "SERVED -- every slot read by a consumer for its label, index AND type -- is 341 of 1,265 "
          "slot-bearing rows (27 %): the route's own half-mark is NOT met, and not nearly "
          "(the label-only tier said 583 / 46 %; the bound here is below the half-mark, ENG-6)", t)
    lbl = rep["label_by_index"]
    check(all(lbl.get(f"str1:{e}", 0) >= 25 for e in
              (Label.FIRE_DAMAGE, Label.COLD_DAMAGE, Label.LIGHTNING_DAMAGE, Label.EARTH_DAMAGE, Label.HOLY_DAMAGE))
          and lbl.get(f"str1:{Label.HEAL}", 0) >= 100 and lbl.get(f"str3:{Label.DURATION}", 0) >= 570
          and rep["labels"].get(Label.CONDITION_DURATION, 0) >= 200,
          "vacuity guard: each elemental damage >= 25 at str1, HEAL >= 100, DURATION >= 570, "
          "condition durations >= 200")
    check(rep["labels"].get(Label.RATE_PERCENT, 0) >= 30 and rep["labels"].get(Label.MOVE_SPEED_UP, 0) >= 30
          and rep["labels"].get(Label.HEALTH_PERCENT, 0) >= 20,
          "the precision split has both sides populated: RATE_PERCENT >= 30 (33: recharge 23, expiry 8, "
          "adrenaline 2), MOVE_SPEED_UP >= 30 (33), HEALTH_PERCENT >= 20 (21)",
          {k: rep["labels"].get(k) for k in (Label.RATE_PERCENT, Label.MOVE_SPEED_UP, Label.HEALTH_PERCENT)})
    conds = collections.Counter(s["detail"] for r in rep["rows"].values() for s in r["slots"]
                                if s["label"] == Label.CONDITION_DURATION)
    check(set(conds) == set(skilldesc.CONDITION_NAMES),
          "all ten conditions have a numbered duration somewhere in the corpus", dict(conds))
    check(rep["literals"] == {"LITERAL_MATCH": 255, "LITERAL_MISS": 103},
          "unshown flat constants: 255 printed as text, 103 the text never states", rep["literals"])
    fg = rep["flags"]
    check(fg.get("IF", 0) == 468 and fg.get("AREA_ADJACENT", 0) == 138 and fg.get("AREA_NEARBY", 0) == 94
          and fg.get("AREA_IN_THE_AREA", 0) == 53 and fg.get("AREA_EARSHOT", 0) == 84,
          "the classifier flags: IF 468, adjacent 138, nearby 94, in the area 53, earshot 84", fg)
    check(fg.get("LITERAL_PERCENT", 0) == 166,
          "LITERAL_PERCENT: 166 rows print a literal percent (of the 372 carrying a %%, 250 "
          "occurrences are a slot's own percent sign); it was raised on all 1,278 slot-bearing rows",
          fg.get("LITERAL_PERCENT"))
    blocking = rep["blocking"]
    check(blocking.get("DURATION str3: non-episode type", 0) >= 180
          and blocking.get(f"{Label.DAMAGE} str1: no consumer", 0) >= 80
          and blocking.get(f"{Label.ENERGY} str2: wrong slot", 0) >= 55
          and blocking.get(f"{Label.HEAL} str2: wrong slot", 0) >= 40
          and blocking.get(f"{Label.HEAL} str1: episode type", 0) >= 25,
          "what keeps rows out of SERVED, per (label, slot, reason): a duration on a non-episode "
          "type 186, untyped damage 84, ENERGY at str2 61 (glyph reads scale), HEAL at str2 47 and "
          "HEAL on an episode type 28 (skill_heal reads scale at cast)",
          {k: blocking[k] for k in sorted(blocking, key=lambda k: -blocking[k])[:6]})

    # THE PvP / PvE JOIN, over the FULL table.
    data = ix.pe.data
    base, count, _ = skilltable.locate_table(data)
    full = [skilltable.parse_record(data, base, i) for i in range(count)]
    corpus = set(records)
    into = [r for r in full if r["id"] and r["linked_id"] in corpus]
    check(len(into) == 177 and all(r["pvp_only"] and r["equip_family"] == 0 for r in into),
          "177 PvP-only family-0 rows link INTO the corpus, none of them in it", len(into))
    shared = sum(1 for r in into if r["description_id"] == records[r["linked_id"]]["description_id"])
    check(shared == 0, "and 0 of 177 share their PvE original's template -- the join is id to own record", shared)
    out = sum(1 for r in records.values() if r["linked_id"] != count)
    check(out == 156, "156 corpus rows link out to a twin; the rest carry the table's 'none'", out)

    # THE CENSUS (DESKWORK-Q7). The client + effects facts are exact; the
    # content-side split is derived from the hand rows loaded (ENG-7).
    grades = skilldesc.census(records, hand_rows)
    g = collections.Counter(grades.values())
    n_ep = sum(1 for r in records.values() if effects.applies_effect(r))
    check(g["modelled"] == n_hand and sum(g.values()) == 1333
          and g["episode-only"] + g["episode-refused"] + sum(1 for sid in hand_rows if sid in records
                                                              and effects.applies_effect(records[sid])) == n_ep
          and g["episode-refused"] >= 40 and g["nothing"] >= 800,
          f"what the server resolves today: {n_hand} carry a row (54 on 2026-09-22, at least 4 of them "
          f"inert), every EFFECT_TYPES row not in hand is an episode or a refusal (419 + 45 that day), "
          f"the rest nothing (815)", dict(g))
    cbt = skilldesc.census_by_type(records, grades, rep)
    n_hand_14 = sum(1 for sid in hand_rows if sid in records and int(records[sid]["type_code"]) == 14)
    check(cbt[5]["n"] == 287 and cbt[5]["nothing"] >= 270 and cbt[14]["modelled"] == n_hand_14
          and cbt[6]["episode-only"] + cbt[6]["episode-refused"] + sum(
              1 for sid in hand_rows if sid in records and int(records[sid]["type_code"]) == 6) == 227,
          "by type: 270+ of 287 Spells resolve nothing; the type-14 modelled count is the hand rows' "
          "own; every one of the 227 enchantments is an episode, a refusal or a hand row",
          {k: dict(v) for k, v in cbt.items() if k in (5, 6, 14)})
    check(all(grades[sid] == "modelled" for sid in hand_rows if sid in records) and n_hand >= 50,
          f"every hand row is a corpus row and grades modelled ({n_hand} rows)")

    # ---------------------------------------------------------- section 3
    # THE LABEL TIER (SKILLS-LT, DESKWORK-D4 step 4, the owner's 2026-09-23
    # decision): the plain SERVED rows as generated rows. Client-side counts are
    # exact; the hand-row count is derived from the rows loaded (ENG-7).
    print("\n== 3. the label tier: the plain SERVED set, the gate, the emitted overlay ==")
    plain = skilldesc.plain_served(rep)
    cond = skilldesc.conditional_served(rep)
    check(len(plain) == 131 and len(cond) == 210 and len(plain) + len(cond) == t["SERVED"],
          "341 SERVED = 131 PLAIN (no IF / WHEN / FOR_EACH / WHILE / EXCEPTION / CHANCE) + 210 "
          "conditional -- the orchestrator's count, reproduced", (len(plain), len(cond)))
    cf = collections.Counter(f for sid in cond for f in rep["rows"][sid]["flags"]
                             if f in skilldesc.COMPOUND_FLAGS)
    check(cf == {"IF": 154, "WHEN": 37, "FOR_EACH": 17, "WHILE": 9, "CHANCE": 7, "EXCEPTION": 6},
          "the 210 held back, by the wording a label would drop: IF 154, WHEN 37, FOR_EACH 17, "
          "WHILE 9, CHANCE 7, EXCEPTION 6", dict(cf))
    hand_ids = set(hand_rows)
    lrows, excluded, _p = skilldesc.label_rows(rep, records, hand_ids)
    tally = collections.Counter(w for _s, w in excluded)
    by_reason = {w: sorted(s for s, ww in excluded if ww == w) for w in tally}
    n_hand_plain = sum(1 for sid in plain if sid in hand_ids)
    check(tally.get("HAND_ROW", 0) == n_hand_plain and n_hand_plain >= 10
          and all(w in skilldesc.EXCLUSIONS for w in tally),
          f"the plain rows a hand row already covers are excluded as HAND_ROW ({n_hand_plain}; 10 "
          f"on 2026-09-23), every reason from the enum", dict(tally))
    check(tally.get("DURATION_ONLY") == 41
          and by_reason.get("CONDITION_ON_EPISODE") == [113, 435, 926, 1041, 1997, 2136]
          and by_reason.get("PET_ATTACK") == [441]
          and by_reason.get("RECIPIENT_NOT_A_FOE") == [769, 770, 917, 1364, 1468]
          and by_reason.get("RECIPIENT_NOT_AN_ALLY") == [918, 1032, 1354],
          "THE EXCLUSIONS, client-side: 41 duration-only; 6 conditions an episode inflicts later "
          "(113, 435, 926, 1041, 1997, 2136); the pet attack 441; 5 at-cast damages / conditions "
          "whose target byte is unresolved (769 917 1468), another ally (770) or self with no area "
          "words and no radius (1364) -- SKILLS-LU moved 183 188 840 1113 2212 to the caster arm "
          "and 97 to UNMODELLED_CLASS; 3 heals byte 1 would hand to the selected agent (918 1032 "
          "1354)", by_reason)
    check(by_reason.get("PERCENT_SLOT") == [292]
          and "CHAIN_REQUIREMENT" not in by_reason
          and by_reason.get("UNMODELLED_CLASS") == [96, 97, 106, 2051, 2100]
          and by_reason.get("HEAL_RECIPIENT_CLASS") == [943, 1262]
          and "SELF_CONFLICT" not in by_reason,
          "THE FIX PASS's EXCLUSIONS after SKILLS-LU (skills 59): 292's percent slot; NO chain "
          "requirement (784 973 1033 ship CHAIN_GATED); 96's corpse, 97's corpse-centred area, 106's "
          "fleshiness, the spirits of 2051 and 2100; the two class heals a person read as NOT "
          "including the caster -- 1262 excludes it, 943 heals only the relieved (287 and 2221 ship "
          "HEAL_PARTY)", by_reason)
    check(len(lrows) == 131 - n_hand_plain - 64 and len(lrows) + len(excluded) == 131,
          f"THE SET: {len(lrows)} label-tier rows = 131 plain - {n_hand_plain} hand - 64 excluded "
          f"(57 on 2026-09-23 after SKILLS-LU's three consumers; 47 after the fix pass, 59 before "
          f"it); nothing shrinks silently", (len(lrows), len(excluded)))
    check(not (set(lrows) & hand_ids) and skilldesc.check_label_rows(lrows, rep, hand_ids, records) == [],
          "no emitted row keys a hand-row id, and the set passes its own checker (records included)")
    arms = {}
    for sid, want in ((292, "percent slot"), (96, "recipient class")):
        why, det, fields, ver = skilldesc.build_label_row(rep["rows"][sid], records[sid], hand_ids)
        forced_rows = {sid: {"fields": fields or {"scale_means": "Heal"}, "type_code": rep["rows"][sid]["type_code"],
                             "tier": "label", "tier_detail": det, "verified": ver}}
        arms[sid] = (why, skilldesc.check_label_rows(forced_rows, rep, hand_ids, records), want)
    check(arms[292][0] == "PERCENT_SLOT" and arms[96][0] == "UNMODELLED_CLASS"
          and all(len(f) == 1 and want in f[0] and str(sid) in f[0] for sid, (_w, f, want) in arms.items()),
          "KNOWN-BAD ARMS (the fix pass): 292 and 96 forced through the gate are each the ONE "
          "fault the checker names -- a percent slot, a recipient class",
          {s: a[1] for s, a in arms.items()})
    # SKILLS-LU: the three consumers' rows carry their marks; each mark STRIPPED is the one fault
    stripped = {}
    for sid, mark, want in ((784, "CHAIN_GATED", "chain requirement"),
                            (183, "AREA_CASTER", "caster-centred area"),
                            (287, "HEAL_PARTY", "INCLUDES_CASTER")):
        r = dict(lrows[sid])
        r["tier_detail"] = [d for d in r["tier_detail"] if d != mark]
        stripped[sid] = (mark in lrows[sid]["tier_detail"],
                         skilldesc.check_label_rows({sid: r}, rep, hand_ids, records), want)
    check(all(had and len(f) == 1 and want in f[0] and str(sid) in f[0]
              for sid, (had, f, want) in stripped.items()),
          "KNOWN-BAD ARMS (SKILLS-LU): 784, 183 and 287 ship WITH their consumer's mark, and each "
          "with the mark stripped is the ONE fault the checker names -- a chain requirement with no "
          "gate, a byte-0 damage outside the caster arm, a class heal without its reading",
          {s: a[1] for s, a in stripped.items()})
    r97 = dict(lrows[183], tier_detail=["ALL_FOES", "AREA_NEARBY", "AREA_CASTER"])
    f97 = skilldesc.check_label_rows({97: r97}, rep, hand_ids, records)
    r1262 = {"fields": {"scale_means": "Heal"}, "type_code": 5, "tier": "label",
             "tier_detail": ["AREA_ADJACENT", "HEAL_PARTY"], "verified": [{"slot": 1}]}
    f1262 = skilldesc.check_label_rows({1262: r1262}, rep, hand_ids, records)
    check(len(f97) == 1 and "recipient class" in f97[0]
          and len(f1262) == 1 and "INCLUDES_CASTER" in f1262[0],
          "KNOWN-BAD ARMS (SKILLS-LU): 97 forced in with the AREA_CASTER mark is still named for its "
          "corpse (the class fault); 1262 forced in with HEAL_PARTY is named for its EXCLUDES_CASTER "
          "reading", (f97, f1262))
    forced = None
    for sid in cond:
        why, det, fields, ver = skilldesc.build_label_row(rep["rows"][sid], records[sid], hand_ids)
        if why is None:
            forced = sid
            break
    bad = dict(lrows)
    bad[forced] = {"fields": fields, "type_code": rep["rows"][forced]["type_code"],
                   "tier": "label", "tier_detail": det, "verified": ver}
    faults = skilldesc.check_label_rows(bad, rep, hand_ids)
    check(forced is not None and len(faults) == 1 and str(forced) in faults[0]
          and "conditional wording" in faults[0],
          f"KNOWN-BAD ARM: a conditional SERVED row ({forced}) forced through the gate is the one "
          f"fault the checker names", faults)
    dt = collections.Counter(d for r in lrows.values() for d in r["tier_detail"] if d in skilldesc.DETAILS)
    check(dt == {"AREA_BURST": 3, "AREA_CASTER": 5, "HEAL_PARTY": 2, "CHAIN_GATED": 3,
                 "CHAIN_STEP_ADVANCES": 1, "AREA_ONE_TARGET": 21, "CONDITION_BIT_CLEAR_REFUSED": 2,
                 "INDETERMINATE_SLOT": 1, "DURATION_UNMODELLED": 10, "CONDITION_UNNUMBERED": 2,
                 "LITERAL_DROPPED": 5, "CLAUSE_MOVE_SPEED": 1, "CLAUSE_KNOCKDOWN": 7,
                 "CLAUSE_SHADOW_STEP": 4, "CLAUSE_INTERRUPT": 2, "CLAUSE_REMOVAL": 3,
                 "CLAUSE_ALSO_CASTER": 3, "CLAUSE_DISABLE": 1, "CLAUSE_DOUBLE_DAMAGE": 1,
                 "CLAUSE_CAST_SPEED": 1, "CLAUSE_RANGE": 4, "CLAUSE_REVEAL": 1},
          "MARKED, counted: 3 bursts spell_burst covers (187 189 1086), 5 caster-centred areas "
          "(183 188 840 1113 2212), 2 party heals (287 2221), 3 chain-gated non-attacks (784 973 "
          "1033), 974's chain step now ADVANCING, 21 area wordings the server reaches one recipient "
          "of (973's adjacent Blind joined), 2 bit-clear conditions (167, 1033's Deep Wound -- also "
          "the 1 INDETERMINATE slot), 10 non-episode durations the at-cast path never runs (840 1033 "
          "1113 joined 167 192 197 and the rest), 2 unnumbered conditions (228's Cracked Armor, "
          "2221's Burning), 5 literal constants, and the dropped clauses by kind: 7 knock-downs "
          "(784 joined), 4 shadow steps, 2 interrupts, 3 removals (2221's 'relieved of'), 3 'you "
          "and' (840's 'you and all'), a disable, a double damage, 1996's cast and move slows, 4 half "
          "ranges, 2212's compass reveal", dict(dt))
    under = sorted(s for s in lrows if set(lrows[s]["tier_detail"]) & set(skilldesc.DETAILS))
    check(len(under) == 46
          and sorted(set(lrows) - set(under)) == [117, 191, 220, 286, 293, 959, 1043, 1120, 1404, 1686, 1762]
          and [s for s in sorted(lrows) if "AREA_BURST" in lrows[s]["tier_detail"]] == [187, 189, 1086]
          and [s for s in sorted(lrows) if "AREA_CASTER" in lrows[s]["tier_detail"]] == [183, 188, 840, 1113, 2212]
          and [s for s in sorted(lrows) if "HEAL_PARTY" in lrows[s]["tier_detail"]] == [287, 2221]
          and [s for s in sorted(lrows) if "CHAIN_GATED" in lrows[s]["tier_detail"]] == [784, 973, 1033]
          and {"AREA_ONE_TARGET", "DURATION_UNMODELLED"} <= set(lrows[192]["tier_detail"])
          and {"AREA_ONE_TARGET", "DURATION_UNMODELLED"} <= set(lrows[197]["tier_detail"]),
          "46 of 57 rows carry a mark; the eleven without one are the same single-clause templates "
          "as before SKILLS-LU (every new row rides a consumer that is named); AREA_BURST is exactly "
          "187 189 1086, AREA_CASTER 183 188 840 1113 2212, HEAL_PARTY 287 2221, CHAIN_GATED 784 973 "
          "1033; the areas over time 192 and 197 that spell_burst refuses say ONE_TARGET + "
          "DURATION_UNMODELLED (ENG-2, LT-R7)", sorted(set(lrows) - set(under)))
    check(lrows[187]["fields"] == {"scale_means": "Fire damage"} and "AREA_BURST" in lrows[187]["tier_detail"]
          and lrows[220]["fields"] == {"bonus_scale_means": "Blind"}
          and lrows[831]["fields"] == {"scale_means": "Attack speed increase",
                                       "bonus_scale_means": "Movement speed increase"}
          and "CLAUSE_DOUBLE_DAMAGE" in lrows[831]["tier_detail"]
          and lrows[434]["fields"] == {"scale_means": "+ Damage"} and lrows[434]["type_code"] == 19
          and lrows[3425]["fields"] == {"scale_means": "+ Damage"}
          and lrows[167]["fields"] == {"scale_means": "Earth damage", "bonus_scale_means": "Blind"}
          and {"AREA_NEAR", "AREA_ONE_TARGET", "CONDITION_BIT_CLEAR_REFUSED", "DURATION_UNMODELLED"}
          <= set(lrows[167]["tier_detail"])
          and {"CLAUSE_MOVE_SPEED", "CLAUSE_CAST_SPEED"} <= set(lrows[1996]["tier_detail"])
          and "CHAIN_STEP_ADVANCES" in lrows[974]["tier_detail"]
          and "CHAIN_STEP_NOT_ADVANCED" not in lrows[974]["tier_detail"],
          "spot rows: 187 fire (burst), 220 Blind at str2, 831 both speeds + its double damage named, "
          "434 a preparation's +damage, 3425's +holy is the additive '+ Damage', 167 earth + a "
          "bit-clear Blind over an area near a location for 5 s, 1996's dropped slows, 974's chain "
          "step ADVANCES (SKILLS-LU)")
    # SKILLS-LU's rows, read off the corpus: the record each consumer keys on
    check(lrows[183]["fields"] == {"scale_means": "Fire damage"} and lrows[183]["type_code"] == 5
          and records[183]["target"] == 0 and records[183]["aoe_range"] == 156.0
          and lrows[840]["fields"] == {"scale_means": "Poison"}
          and {"AREA_CASTER", "DURATION_UNMODELLED", "CLAUSE_ALSO_CASTER"} <= set(lrows[840]["tier_detail"])
          and records[840]["duration0"] == 10
          and {"AREA_CASTER", "CLAUSE_REVEAL"} <= set(lrows[2212]["tier_detail"]) and records[2212]["aoe_range"] == 312.0
          and lrows[287]["fields"] == {"scale_means": "Heal"} and records[287]["aoe_range"] == 5000.0
          and records[2221]["aoe_range"] == 5000.0
          and {"HEAL_PARTY", "CLAUSE_REMOVAL", "CONDITION_UNNUMBERED"} <= set(lrows[2221]["tier_detail"])
          and lrows[784]["fields"] == {"scale_means": "Poison"} and records[784]["combo_req"] == 2
          and {"CHAIN_GATED", "CLAUSE_KNOCKDOWN"} <= set(lrows[784]["tier_detail"])
          and records[973]["combo_req"] == 4 and {"CHAIN_GATED", "AREA_ONE_TARGET"} <= set(lrows[973]["tier_detail"])
          and records[1033]["combo_req"] == 1 and lrows[1033]["type_code"] == 10
          and {"CHAIN_GATED", "INDETERMINATE_SLOT", "CONDITION_BIT_CLEAR_REFUSED"} <= set(lrows[1033]["tier_detail"])
          and records[974]["combo"] == 2
          and rep["rows"][287]["template_sha16"] == skilldesc.CLASS_HEAL_READINGS[287][1]
          and rep["rows"][2221]["template_sha16"] == skilldesc.CLASS_HEAL_READINGS[2221][1]
          and rep["rows"][943]["template_sha16"] == skilldesc.CLASS_HEAL_READINGS[943][1]
          and rep["rows"][1262]["template_sha16"] == skilldesc.CLASS_HEAL_READINGS[1262][1],
          "SKILLS-LU's rows against the records: 183 fire from a byte-0 Spell over 156; 840's Poison "
          "with its flat 10 s and its 'you and' marked; 2212 over 312 with its compass clause marked; "
          "287 and 2221 heal over 5000 (2221's cure of Burning marked twice); 784 must follow a lead "
          "(2), 973 an off-hand (4), 1033 a dual (1) -- each CHAIN_GATED; 974 counts as an off-hand "
          "(combo 2); and the four class-heal READINGS still match their templates' digests on this "
          "build (a changed template voids the reading and the row falls back to the exclusion)")
    types = collections.Counter(r["type_code"] for r in lrows.values())
    check(set(types) <= {3, 4, 5, 7, 10, 14, 19} and types[5] >= 20,
          "the shipped types: Stances, Hexes, Spells (20+), Signets, Skills, attacks, a Preparation "
          "-- no Enchantment, no Shout, no pet attack, no Glyph", dict(types))
    build = skilltable.build_of(data)
    check(build == 38797, "the build stamp is derived from the image's bytes: 38797", build)
    with tempfile.TemporaryDirectory() as tmp:
        import textrec
        p1, p2 = os.path.join(tmp, "a.toml"), os.path.join(tmp, "b.toml")
        digest = skilldesc.template_digest(texts)
        skilldesc.emit_labels(lrows, excluded, build, exe, p1, plain, dat=textrec.DEFAULT_DAT, digest=digest)
        skilldesc.emit_labels(lrows, excluded, build, exe, p2, plain, dat=textrec.DEFAULT_DAT, digest=digest)
        b1, b2 = open(p1, "rb").read(), open(p2, "rb").read()
        with open(p1, "rb") as fh:
            table = tomllib.load(fh)
        se = table["skill_effect"]
        check(b1 == b2 and len(se) == len(lrows) and set(map(int, se)) == set(lrows),
              "the overlay is DETERMINISTIC (two emits, identical bytes) and holds exactly the set")
        check(all(r["provenance"]["source"] == "client-table"
                  and r["provenance"]["extractor"] == "toolkit/clientscan/skilldesc.py"
                  and r["provenance"]["build"] == 38797 and r["tier"] == "label"
                  and r["provenance"]["verified"] for r in se.values()),
              "every row: source client-table, the extractor, build 38797, tier label, a slot record")
        strings = skilldesc.overlay_strings(table)
        check(skilldesc.text_leak(table) == []
              and max(len(s) for s in strings) <= skilldesc.OVERLAY_MAX_STRING,
              f"NO TEXT: all {len(strings)} string values are in OVERLAY_VOCABULARY and none is "
              f"longer than its longest token ({skilldesc.OVERLAY_MAX_STRING})",
              skilldesc.text_leak(table)[:5])
        import content
        w = content.load(vault_dir=tmp)
        lab = skilldesc.loaded_label_rows(w)
        hnd = skilldesc.hand_rows(w)
        check(set(lab) == set(lrows) and set(hnd) == hand_ids
              and all(w.rows("skill_effect")[str(s)]["tier"] == "label" for s in lrows),
              "content.load takes the overlay as the vault: the label rows load under the hand "
              "rows, and hand_rows() / loaded_label_rows() split them by tier")
        g2 = skilldesc.census(records, hnd, labels=lab)
        c2 = collections.Counter(g2.values())
        check(c2["label-only"] == len(lrows) and c2["modelled"] == g["modelled"]
              and all(g2[s] == grades[s] for s in records if s not in lab),
              "the census grades a label row 'label-only', never 'modelled', and nothing else moves",
              dict(c2))
        # The overlay on disk must equal a fresh emit. DEFAULT: the vault's own file --
        # the one every server on this machine loads. On a BRANCH whose gate has moved
        # (SKILLS-LU) the vault is stale until the merge regenerates it, so the check may
        # be pointed at an explicit emit with RURIK_SKILL_LABELS=<path>; it names which
        # file it read, and the default stays the vault, never a branch's scratch copy.
        explicit = os.environ.get("RURIK_SKILL_LABELS", "").strip()
        disk = Path(explicit) if explicit else skilldesc.default_labels_path()
        where = "RURIK_SKILL_LABELS" if explicit else "the vault"
        if disk.is_file():
            check(disk.read_bytes() == b1,
                  f"the overlay ON DISK ({where}: {disk}) is byte-identical to a fresh emit -- "
                  f"regenerated, not hand-edited; a mismatch means `python toolkit/clientscan/"
                  f"skilldesc.py --emit-labels` is owed (at the merge, into the vault)")
        elif explicit:
            # the fix pass (ENG-D4C-9): a mistyped explicit path is a FAIL, not a
            # declared skip -- the skip is for the vault's file being absent only
            check(False, f"RURIK_SKILL_LABELS names {disk}, which is not a file -- the explicit "
                         f"path exists to make the on-disk check bite on a branch, so its "
                         f"absence is a failure, never a skip")
        else:
            LEDGER.skip("the overlay on disk (1 check)",
                        f"{disk} absent -- `python toolkit/clientscan/skilldesc.py --emit-labels`")
    ix.close()

sys.exit(LEDGER.verdict())
