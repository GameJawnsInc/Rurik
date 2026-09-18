"""test_weapons.py -- WEAPONS-W1: one weapon table, a row and an item per type.

The three item-type dicts in authsrv.py (attribute, rates key, weapon_req bit) were
literals with four rows; they are built from content [weapon_type.*] now. This test
holds the KNOWN-GOOD ARM still -- the four melee rows read exactly what the literals
said -- and then checks what the new rows claim against things that can refute them:
the skill table's own weapon_req -> attribute column, the rates table, the item rows'
modifier words, and the character the server actually builds when it is handed each
weapon. No vault: everything here is content and code.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks  # noqa: E402
import agents  # noqa: E402
import authsrv  # noqa: E402
import combatmath  # noqa: E402

LEDGER = checks.Ledger("weapons: one table, a row and an item per type", floor=19)   # the BARE-MACHINE number: 19 without the vault's full skills table (section 2 skips), 20 with it; from green runs
check = LEDGER.ok

LEGACY_ATTRIBUTE = {15: 19, 27: 20, 2: 18, 32: 29}
LEGACY_RATE = {15: "hammer", 27: "sword", 2: "axe", 32: "daggers"}
LEGACY_REQ_BIT = {2: 0x01, 32: 0x08, 15: 0x10, 27: 0x80}
NEW_ITEMS = {"starter_axe": 2, "starter_bow": 5, "starter_wand": 22,
             "starter_scythe": 35, "starter_spear": 36, "starter_focus": 12}


def section_table():
    print("\n1. the table")
    rows = agents.WORLD.rows("weapon_type")
    check({k: v for k, v in authsrv.WEAPON_TYPE_ATTRIBUTE.items() if k in LEGACY_ATTRIBUTE}
          == LEGACY_ATTRIBUTE
          and {k: v for k, v in authsrv.WEAPON_TYPE_RATE.items() if k in LEGACY_RATE}
          == LEGACY_RATE
          and {k: v for k, v in authsrv.WEAPON_TYPE_REQ_BIT.items() if k in LEGACY_REQ_BIT}
          == LEGACY_REQ_BIT,
          "the KNOWN-GOOD arm: hammer, sword, axe and daggers read exactly what the three "
          "literals said before WEAPONS-W1")
    check(set(authsrv.WEAPON_TYPE_ROW) == {int(r["item_type"]) for r in rows.values()}
          and len(authsrv.WEAPON_TYPE_ROW) == len(rows) >= 11,
          "one row per item type, none shared", str(sorted(authsrv.WEAPON_TYPE_ROW)))
    check(1 not in authsrv.WEAPON_TYPE_ROW and 28 not in authsrv.WEAPON_TYPE_ROW,
          "the hostile-only types 1 and 28 are NOT player weapon rows (WEAPONS-C2)")
    bits = list(authsrv.WEAPON_TYPE_REQ_BIT.values())
    check(len(set(bits)) == len(bits) and all(b and b & (b - 1) == 0 for b in bits)
          and sum(bits) == 0xFB,
          "every weapon_req bit is ONE bit, none shared, and together they are the mask's "
          "seven named bits (0x01 0x02 0x08 0x10 0x20 0x40 0x80)", hex(sum(bits)))
    check(all(authsrv.WEAPON_TYPE_RATE[t] in agents.ATTACK_SPEED
              for t in authsrv.WEAPON_TYPE_RATE)
          and {t: agents.ATTACK_SPEED[k] for t, k in authsrv.WEAPON_TYPE_RATE.items()}
          == {2: 1.33, 27: 1.33, 32: 1.33, 15: 1.75, 22: 1.75, 26: 1.75,
              35: 1.5, 36: 1.5, 5: 2.475},
          "every rate is an [attack_speed.rates] key -- 1.33 / 1.75 / 2.475 are the numbers "
          "retail's 0x0035 sent while the type was held (test_weaponcensus), 1.5 is WIKI's")
    check(22 not in authsrv.WEAPON_TYPE_ATTRIBUTE and 26 not in authsrv.WEAPON_TYPE_ATTRIBUTE
          and 22 not in authsrv.WEAPON_TYPE_REQ_BIT,
          "a caster weapon has no mastery and no weapon_req bit: attribute 0 and req_bit 0 "
          "stay OUT of the dicts, so .get() means what it meant")
    by_delivery = {}
    for typ, row in authsrv.WEAPON_TYPE_ROW.items():
        by_delivery.setdefault(row["delivery"], set()).add(typ)
    check(by_delivery == {"melee": {2, 27, 32, 15, 35}, "projectile": {36, 5, 22, 26},
                          "none": {24, 12}},
          "delivery: five melee types, four projectile types, two off-hand items",
          str(by_delivery))
    hands = {t: r["hands"] for t, r in authsrv.WEAPON_TYPE_ROW.items()}
    check({t for t, h in hands.items() if h == "two"} == {32, 15, 35, 5, 26}
          and {t for t, h in hands.items() if h == "off"} == {24, 12},
          "hands: daggers, hammer, scythe, bow and staff take both", str(hands))
    try:
        authsrv.weapon_type_tables({"a": {"item_type": 2, "rate": "axe"},
                                    "b": {"item_type": 2, "rate": "axe"}})
        refused = False
    except SystemExit:
        refused = True
    try:
        authsrv.weapon_type_tables({"a": {"item_type": 2, "rate": "no_such_rate"}})
        refused_rate = False
    except SystemExit:
        refused_rate = True
    check(refused and refused_rate,
          "the loader REFUSES two rows on one item type and a rate that is no rates key")


def section_skills():
    print("\n2. the req bits against the skill table's own attribute column")
    skills = agents.WORLD.rows("skills")
    if sum(1 for r in skills.values() if r.get("weapon_req")) < 100:
        # the tracked content carries a few dozen skills; the full table is the
        # vault's extraction, and a column needs the whole table to be a column
        LEDGER.skip("section 2", "the full skills table (vault/content) is absent -- 1 check")
        return
    agree = {}
    for typ, bit in authsrv.WEAPON_TYPE_REQ_BIT.items():
        attrs = [r.get("attribute") for r in skills.values() if r.get("weapon_req") == bit]
        want = authsrv.WEAPON_TYPE_ATTRIBUTE[typ]
        agree[typ] = (sum(1 for a in attrs if a == want), len(attrs))
    check(all(n >= 10 and hit > n / 2 for hit, n in agree.values()),
          "for every type, MOST skill rows whose weapon_req is exactly its bit carry its "
          "attribute -- the table's two columns are one fact, read off the client",
          str(agree))


def section_items():
    print("\n3. an item per type, and the required weapon's range word")
    ok = {}
    for key, typ in NEW_ITEMS.items():
        it = agents.item_template(key)
        ok[key] = (int(it["item_type"]) == typ and typ in authsrv.WEAPON_TYPE_ROW)
    check(all(ok.values()), "six new item rows, each of a type the table names", str(ok))
    ranges = {k: authsrv.weapon_damage_range(agents.item_template(k)) for k in NEW_ITEMS}
    check(ranges == {"starter_axe": (8, 28), "starter_bow": (5, 9), "starter_wand": (3, 5),
                     "starter_scythe": (4, 7), "starter_spear": (5, 7), "starter_focus": None},
          "each weapon's own 584 word is its range; a focus has none", str(ranges))
    required = {"modifiers": [0x27981909, 0x24B80100, 0xA7A81C0F]}     # 633 (25, 9), 587, 634 (28, 15)
    plain = {"modifiers": [0x24B80100, 0xA4881C0F]}
    check(combatmath.weapon_damage_range(required) == (15, 28)
          == combatmath.weapon_damage_range(plain),
          "WEAPONS-C7: a weapon WITH a requirement carries its range as 634, and reads the "
          "same 15-28 as the 584 form", str(combatmath.weapon_damage_range(required)))
    check(all(agents.item_template(v) for v in authsrv.PARTY_WEAPON_ITEMS.values())
          and all(k in agents.ATTACK_SPEED for k in authsrv.PARTY_WEAPON_ITEMS),
          "every party weapon class is a rates key and resolves to an item row")
    proj = {k: [(w >> 20) & 0x3FF for w in agents.item_template(k)["modifiers"]]
            for k in ("starter_bow", "starter_wand")}
    check(617 not in proj["starter_bow"] and 617 in proj["starter_wand"]
          and authsrv.WEAPON_TYPE_ROW[5].get("projectile") == 143,
          "the bow carries no 617 and the table's default 143 stands in; the wand carries "
          "its own (WEAPONS-C3 -- what W2 will send in 0x00A4 field 5)")


def section_character():
    print("\n4. the character the server builds around each weapon")
    saved = (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
             authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE)
    try:
        got = {}
        for key in ("starter_axe", "starter_bow", "starter_wand", "starter_scythe",
                    "starter_spear", "starter_daggers"):
            authsrv.apply_party_character({"player_weapon": key})
            got[key] = (authsrv.ATTACK_INTERVAL, authsrv.PLAYER_SWING_DAMAGE)
        check(got == {"starter_axe": (1.33, (8, 28)), "starter_bow": (2.475, (5, 9)),
                      "starter_wand": (1.75, (3, 5)), "starter_scythe": (1.5, (4, 7)),
                      "starter_spear": (1.5, (5, 7)), "starter_daggers": (1.33, (1, 3))},
              "each weapon sets ITS interval and ITS range", str(got))
        authsrv.apply_party_character({"player_weapon": "starter_sword",
                                       "player_offhand": "starter_shield"})
        one_handed = bool(agents.PLAYER_OFFHAND)
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        check(one_handed and agents.PLAYER_OFFHAND is None,
              "a sword keeps its shield; taking up a TWO-HANDED bow empties the off hand "
              "(retail names offhand 0 beside every bow, hammer, staff and dagger pair)")
        authsrv.apply_party_character({"player_weapon": "starter_spear",
                                       "player_offhand": "starter_shield"})
        check(bool(agents.PLAYER_OFFHAND) and authsrv.holds_shield({}, authsrv.PLAYER_AGENT_ID),
              "a one-handed spear holds a shield beside it")
        rank = authsrv.WEAPON_TYPE_ATTRIBUTE.get(int(agents.PLAYER_WEAPON["item_type"]))
        authsrv.apply_party_character({"player_weapon": "starter_wand",
                                       "player_offhand": "starter_focus"})
        check(rank == 37 and authsrv.player_weapon_rank({}) is None
              and not authsrv.holds_shield({}, authsrv.PLAYER_AGENT_ID),
              "the spear scales on attribute 37; a wand names NO mastery, so the swing's "
              "rank is None and hit_enemy takes its existing raw-range fallback; a focus is not a shield")
    finally:
        (agents.PLAYER_WEAPON, agents.PLAYER_OFFHAND, authsrv.ATTACK_INTERVAL,
         authsrv.WEAPON_ATTACK_SPEED, authsrv.PLAYER_SWING_DAMAGE) = saved
    src = open(os.path.join(HERE, "serverargs.py"), encoding="utf-8").read()
    check('"--player-weapon"' in src and '"--player-offhand"' in src,
          "--player-weapon / --player-offhand exist: any item row in the player's hands")


def main():
    section_table()
    section_skills()
    section_items()
    section_character()
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
