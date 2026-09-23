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
    corpus gets a label (0 UNPARSED); the 54 hand rows agree on 51 of the 52
    comparable slots and the one disagreement is a real one (Battle Rage's
    `scale_means = "Duration"` on a flat 33 that is its movement speed).
  * THE CENSUS (DESKWORK-Q7). What the server resolves today: 54 modelled, 419
    episodes (+45 refused durations), 815 nothing.

Section 1 runs on a bare machine; section 2 needs the pinned exe and Gw.dat
and declares one skip without them. Nothing here quotes a template.
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "authsrv"))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "mapdata"))
import checks       # noqa: E402
import effects      # noqa: E402
import skilldesc    # noqa: E402
import skilltable   # noqa: E402
from skilldesc import Label, SLOT_FIELD, shifted, referee_slot   # noqa: E402

# Floor from the BARE run, MEASURED 2026-09-22 with RURIK_VAULT at an empty
# directory: 31 checks, 1 declared skip ("2. the corpus"), rc=0 -- the
# mandatory core per checks.py. A whole green run with the vault is 73.
LEDGER = checks.Ledger("skill description templates", floor=31)
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
check(skilldesc.slot_served(Label.DURATION, 3) and not skilldesc.slot_served(Label.DURATION, 15),
      "DURATION is served on a Stance (an episode) and not on a Shout")
check(skilldesc.slot_served(Label.FIRE_DAMAGE, 19) and not skilldesc.slot_served(Label.LEVEL, 5),
      "Fire damage is served whatever the type; LEVEL has no consumer")
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
          and "LITERAL_PERCENT" in rep["rows"][234]["flags"],
          "Deep Freeze (234): str1 cold damage 10..85; its 66% is literal text over bonus 66/66",
          (s1, rep["rows"][234]["literals"]))

    hs = rep["hand_summary"]
    check(hs == {"AGREE": 51, "CONFLICT": 1, "NOT_COMPARABLE": 2, "NO_SLOT": 14},
          "the 54 hand rows: 51 agree, 1 conflict, 2 not comparable, 14 name an unshown slot", hs)
    conflicts = [r for r in rep["hand"] if r[-1] == "CONFLICT"]
    check(conflicts == [(317, "scale_means", 1, "Duration", Label.MOVE_SPEED_UP, "CONFLICT")],
          "the one conflict is Battle Rage: `scale_means = \"Duration\"` on the flat 33 that is "
          "its movement speed (the duration is str3)", conflicts)
    no_slot = [r for r in rep["hand"] if r[-1] == "NO_SLOT"]
    lit_ok = 0
    for sid, key, index, _means, _lbl, _v in no_slot:
        field = SLOT_FIELD[index]
        lit_ok += any(l[1] == field and l[3] == "LITERAL_MATCH" for l in rep["rows"][sid]["literals"])
    check(lit_ok == 12 and len(no_slot) == 14,
          "12 of the 14 unshown hand slots are flat constants printed as text; the other two are "
          "Hamstring's (320) 0/0 scale (a label on the wrong slot) and Scourge Sacrifice's (253) "
          "flat 100 the text never states (labelled 'Duration', which is str3)", (lit_ok, len(no_slot)))
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
    check(t.get("SERVED", 0) >= 560 and t.get("SERVED", 0) < 1265 // 2 + 60,
          "SERVED (every slot in the server's current vocabulary) is ~46% of slot-bearing rows: "
          "the route's own half-mark, measured, is NOT met on the served tier", t)
    lbl = rep["label_by_index"]
    check(all(lbl.get(f"str1:{e}", 0) >= 25 for e in
              (Label.FIRE_DAMAGE, Label.COLD_DAMAGE, Label.LIGHTNING_DAMAGE, Label.EARTH_DAMAGE, Label.HOLY_DAMAGE))
          and lbl.get(f"str1:{Label.HEAL}", 0) >= 100 and lbl.get(f"str3:{Label.DURATION}", 0) >= 570
          and rep["labels"].get(Label.CONDITION_DURATION, 0) >= 200,
          "vacuity guard: each elemental damage >= 25 at str1, HEAL >= 100, DURATION >= 570, "
          "condition durations >= 200")
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
    blocking = rep["blocking"]
    check(blocking.get("DURATION (non-episode type)", 0) >= 180 and blocking.get(Label.DAMAGE, 0) >= 120,
          "the two labels blocking most RECOGNISED rows: a duration on a non-episode type, and "
          "untyped damage", {k: blocking[k] for k in sorted(blocking, key=lambda k: -blocking[k])[:4]})

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

    # THE CENSUS (DESKWORK-Q7).
    grades = skilldesc.census(records, hand_rows)
    g = collections.Counter(grades.values())
    check(g == {"modelled": 54, "episode-only": 419, "episode-refused": 45, "nothing": 815},
          "what the server resolves today: 54 modelled, 419 episodes, 45 refused durations, 815 nothing",
          dict(g))
    cbt = skilldesc.census_by_type(records, grades, rep)
    check(cbt[5]["nothing"] == 276 and cbt[5]["n"] == 287 and cbt[14]["modelled"] == 23
          and cbt[6]["episode-only"] == 192 and cbt[6]["episode-refused"] == 32,
          "by type: 276 of 287 Spells resolve nothing; 23 of the 54 hand rows are type-14 attacks; "
          "192 + 32 enchantments", {k: dict(v) for k, v in cbt.items() if k in (5, 6, 14)})
    check(all(grades[sid] == "modelled" for sid in hand_rows if sid in records)
          and sum(1 for sid in hand_rows if sid in records) == 54,
          "every hand row is a corpus row and grades modelled")
    ix.close()

sys.exit(LEDGER.verdict())
